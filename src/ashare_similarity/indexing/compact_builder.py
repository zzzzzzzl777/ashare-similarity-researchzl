from __future__ import annotations

import json
import gc
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ashare_similarity.data.base import Frequency
from ashare_similarity.features.rolling import time_column_for_frequency
from ashare_similarity.schemas import BuildSummary


COMPACT_STORAGE_FORMAT = "compact-recall-v1"
COMPACT_RECALL_PROJECTION = "path-geometry-liquidity-env-v1"


@dataclass(slots=True)
class _SymbolBatch:
    recall_matrix: np.ndarray
    metadata_rows: list[dict[str, Any]]
    component_slices: dict[str, tuple[int, int]]
    full_vector_dim: int
    latest_data_at: pd.Timestamp | None
    symbol: str


def project_recall_vector(
    vector: np.ndarray,
    component_slices: dict[str, tuple[int, int]],
) -> np.ndarray:
    """Project a full explanation vector into a compact ANN recall vector."""

    values = np.asarray(vector, dtype=np.float32).reshape(-1)
    price = _slice(values, component_slices, "price_path")
    candle = _slice(values, component_slices, "candle_geometry")
    volume = _slice(values, component_slices, "volume_liquidity")
    environment = _slice(values, component_slices, "environment")

    parts = [
        price,
        candle,
        _component_summary(volume, groups=3),
        _component_summary(environment, groups=5),
    ]
    projected = np.concatenate([part for part in parts if part.size]).astype(np.float32, copy=False)
    return np.nan_to_num(projected, nan=0.0, posinf=0.0, neginf=0.0)


def build_compact_index(
    *,
    config,
    store,
    feature_service,
    frequency: Frequency,
    window_size: int,
    symbols: list[str],
    metadata_batch_size: int = 10_000,
) -> BuildSummary:
    """Build a disk-friendly all-market index without persisting full raw vectors.

    The compact index keeps a standardized recall matrix on disk and reconstructs
    full candidate vectors from cached bars during the reranking phase.
    """

    directory = store.feature_dir(frequency, window_size)
    directory.mkdir(parents=True, exist_ok=True)
    build_id = uuid4().hex
    staged_dir = directory / f".compact-build-{build_id}"
    staged_dir.mkdir(parents=True, exist_ok=True)

    metadata_tmp = staged_dir / "metadata.parquet"
    search_matrix_tmp = staged_dir / "ann_search_matrix.npy"
    manifest_tmp = staged_dir / "manifest.json"
    backend_tmp = staged_dir / "backend.json"

    try:
        input_snapshot = _input_snapshot(store, frequency, symbols)
        stats = _single_pass(
            feature_service=feature_service,
            frequency=frequency,
            window_size=window_size,
            symbols=symbols,
            metadata_path=metadata_tmp,
            matrix_path=search_matrix_tmp,
            metadata_batch_size=metadata_batch_size,
        )
        if stats["row_count"] <= 0:
            raise ValueError("No valid feature windows were generated for compact index build.")
        _assert_input_snapshot_unchanged(
            input_snapshot,
            _input_snapshot(store, frequency, symbols),
            phase="after compact index build pass",
        )
        gc.collect()
        mean = np.zeros(int(stats["recall_dim"]), dtype=np.float32)
        scale = np.ones(int(stats["recall_dim"]), dtype=np.float32)

        manifest = {
            "frequency": frequency,
            "window_size": window_size,
            "storage_format": COMPACT_STORAGE_FORMAT,
            "recall_projection": COMPACT_RECALL_PROJECTION,
            "vector_dim": int(stats["full_vector_dim"]),
            "recall_vector_dim": int(stats["recall_dim"]),
            "row_count": int(stats["row_count"]),
            "symbol_count": int(len(stats["symbols_seen"])),
            "component_slices": stats["component_slices"],
            "built_from": {
                "start_date": None,
                "end_date": None,
                "symbols_count": len(symbols),
                "latest_data_at": stats["latest_data_at"].isoformat() if stats["latest_data_at"] is not None else None,
            },
            "built_at": datetime.now(timezone.utc).isoformat(),
            "metadata_columns": _metadata_columns(),
            "matrix_storage": "reconstructed_on_demand",
            "output_paths": {
                "metadata": str(directory / "metadata.parquet"),
                "manifest": str(directory / "manifest.json"),
                "ann_search_matrix": str(directory / "ann_search_matrix.npy"),
                "backend": str(directory / "backend.json"),
            },
            "backend": COMPACT_STORAGE_FORMAT,
            "input_snapshot": {
                "fingerprint": _snapshot_fingerprint(input_snapshot),
                "items": len(input_snapshot),
            },
        }
        backend_payload = {
            "backend": COMPACT_STORAGE_FORMAT,
            "active_backend_at_build": "compact-standardized-recall",
            "dimension": int(stats["recall_dim"]),
            "vector_count": int(stats["row_count"]),
            "mean": mean.astype(np.float32).tolist(),
            "scale": scale.astype(np.float32).tolist(),
            "device": "cpu",
            "device_name": None,
            "backend_details": {
                "preferred_backend": "torch-cuda-bruteforce",
                "storage_format": COMPACT_STORAGE_FORMAT,
                "recall_projection": COMPACT_RECALL_PROJECTION,
            },
            "ann_search_matrix_encoding": "raw_float16",
            "ann_search_matrix_shape": [int(stats["row_count"]), int(stats["recall_dim"])],
            "ann_search_matrix_dtype": "float16",
        }
        manifest_tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        backend_tmp.write_text(json.dumps(backend_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        _commit_compact_artifacts(
            directory=directory,
            staged_files={
                directory / "metadata.parquet": metadata_tmp,
                directory / "manifest.json": manifest_tmp,
                directory / "ann_search_matrix.npy": search_matrix_tmp,
                directory / "backend.json": backend_tmp,
            },
            stale_targets=[
                directory / "matrix.npy",
                directory / "ann_matrix.npy",
                directory / "ann_index.faiss",
            ],
        )

        if hasattr(store, "record_build"):
            store.record_build(
                frequency=frequency,
                window_size=window_size,
                backend=COMPACT_STORAGE_FORMAT,
                rows_count=int(stats["row_count"]),
                metadata_json=manifest,
            )

        return BuildSummary(
            frequency=frequency,
            window_size=window_size,
            symbols_processed=int(len(stats["symbols_seen"])),
            windows_created=int(stats["row_count"]),
            index_backend=COMPACT_STORAGE_FORMAT,
            output_paths={key: str(path) for key, path in manifest["output_paths"].items()},
        )
    finally:
        _cleanup_tree(staged_dir)


def _single_pass(
    *,
    feature_service,
    frequency: Frequency,
    window_size: int,
    symbols: list[str],
    metadata_path: Path,
    matrix_path: Path,
    metadata_batch_size: int,
) -> dict[str, Any]:
    writer: pq.ParquetWriter | None = None
    metadata_batch: list[dict[str, Any]] = []
    row_count = 0
    recall_dim: int | None = None
    full_vector_dim: int | None = None
    component_slices: dict[str, tuple[int, int]] | None = None
    symbols_seen: set[str] = set()
    latest_data_at: pd.Timestamp | None = None
    matrix_path.parent.mkdir(parents=True, exist_ok=True)

    with matrix_path.open("wb") as matrix_handle:
        try:
            for batch in _iter_symbol_batches(feature_service, frequency, window_size, symbols, phase="build"):
                if batch.recall_matrix.size == 0:
                    continue
                recall = batch.recall_matrix.astype(np.float32, copy=False)
                if recall_dim is None:
                    recall_dim = int(recall.shape[1])
                    full_vector_dim = int(batch.full_vector_dim)
                    component_slices = dict(batch.component_slices)
                elif recall.shape[1] != recall_dim:
                    raise RuntimeError("Compact recall projection produced inconsistent dimensions.")

                np.nan_to_num(recall, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float16).tofile(matrix_handle)
                row_count += int(recall.shape[0])
                symbols_seen.add(batch.symbol)
                if batch.latest_data_at is not None and (latest_data_at is None or batch.latest_data_at > latest_data_at):
                    latest_data_at = batch.latest_data_at

                metadata_batch.extend(batch.metadata_rows)
                if len(metadata_batch) >= metadata_batch_size:
                    writer = _write_metadata_batch(writer, metadata_path, metadata_batch)
                    metadata_batch = []
                del recall
                gc.collect()

            if metadata_batch:
                writer = _write_metadata_batch(writer, metadata_path, metadata_batch)
        finally:
            if writer is not None:
                writer.close()

    return {
        "row_count": row_count,
        "recall_dim": int(recall_dim or 0),
        "full_vector_dim": int(full_vector_dim or 0),
        "component_slices": component_slices or {},
        "symbols_seen": symbols_seen,
        "latest_data_at": latest_data_at,
    }


def _iter_symbol_batches(
    feature_service,
    frequency: Frequency,
    window_size: int,
    symbols: list[str],
    *,
    phase: str,
) -> Iterator[_WindowRecord]:
    total = len(symbols)
    for position, symbol in enumerate(symbols, start=1):
        if position == 1 or position % 100 == 0 or position == total:
            print(
                f"[compact-index] {frequency} window {window_size} {phase}: "
                f"{position}/{total} symbols",
                flush=True,
            )
        batch = _build_symbol_batch(feature_service, frequency, window_size, symbol)
        if batch is not None:
            yield batch


def _build_symbol_batch(
    feature_service,
    frequency: Frequency,
    window_size: int,
    symbol: str,
) -> _SymbolBatch | None:
    time_col = time_column_for_frequency(frequency)
    bars = feature_service._load_bars(  # noqa: SLF001 - compact builder is an internal pipeline.
        symbol=symbol,
        frequency=frequency,
        ensure_remote=False,
    )
    if bars.empty or len(bars.index) < window_size:
        return None
    bars[time_col] = pd.to_datetime(bars[time_col])
    bars = bars.sort_values(time_col).reset_index(drop=True)
    symbol_latest = pd.to_datetime(bars[time_col]).max()
    profile = feature_service._get_profile(symbol, bars)  # noqa: SLF001
    listing_days = feature_service._get_listing_days(symbol, bars, None)  # noqa: SLF001
    enriched = feature_service._enrich_with_context(bars, profile.industry, frequency)  # noqa: SLF001
    enriched[time_col] = pd.to_datetime(enriched[time_col])
    enriched = enriched.sort_values(time_col).reset_index(drop=True)

    valid_mask = _window_quality_mask(enriched, window_size, feature_service.config)
    if not valid_mask.any():
        return None

    recall_matrix = _build_recall_matrix(enriched, window_size)[valid_mask]
    starts = np.nonzero(valid_mask)[0]
    ends = starts + window_size - 1
    dates = pd.to_datetime(enriched[time_col])
    name = profile.name or getattr(feature_service.data_service, "get_symbol_name", lambda _: None)(symbol)
    metadata_rows = [
        {
            "symbol": symbol,
            "name": name,
            "industry": profile.industry,
            "listing_days": listing_days,
            "frequency": frequency,
            "start_idx": int(start_idx),
            "end_idx": int(end_idx),
            "start_date": pd.Timestamp(dates.iloc[start_idx]).isoformat(),
            "end_date": pd.Timestamp(dates.iloc[end_idx]).isoformat(),
            "window_length": int(window_size),
            "window_id": "|".join(
                [
                    str(symbol),
                    str(frequency),
                    pd.Timestamp(dates.iloc[start_idx]).isoformat(),
                    pd.Timestamp(dates.iloc[end_idx]).isoformat(),
                    str(int(start_idx)),
                ]
            ),
        }
        for start_idx, end_idx in zip(starts, ends, strict=False)
    ]
    component_slices = _component_slices(window_size)
    return _SymbolBatch(
        recall_matrix=recall_matrix,
        metadata_rows=metadata_rows,
        component_slices=component_slices,
        full_vector_dim=13 * window_size,
        latest_data_at=symbol_latest,
        symbol=symbol,
    )


def _build_recall_matrix(frame: pd.DataFrame, window_size: int) -> np.ndarray:
    open_w = _rolling_windows(_series(frame, "open"), window_size)
    high_w = _rolling_windows(_series(frame, "high"), window_size)
    low_w = _rolling_windows(_series(frame, "low"), window_size)
    close_w = _rolling_windows(_series(frame, "close"), window_size)
    volume_w = _rolling_windows(_series(frame, "volume", fillna=0.0), window_size)
    turnover_w = _rolling_windows(_series(frame, "turnover", fillna=0.0), window_size)
    amplitude_w = _rolling_windows(_series(frame, "amplitude", fillna=0.0), window_size)

    base_close = _safe_denominator(close_w[:, [0]])
    price_level = close_w / base_close - 1.0
    price_return = np.zeros_like(close_w, dtype=np.float32)
    price_return[:, 1:] = np.diff(close_w, axis=1) / _safe_denominator(close_w[:, :-1])
    price_path = np.concatenate([price_level, price_return], axis=1)

    spread = _safe_denominator(high_w - low_w)
    candle_geometry = np.concatenate(
        [
            (close_w - open_w) / spread,
            (high_w - np.maximum(open_w, close_w)) / spread,
            (np.minimum(open_w, close_w) - low_w) / spread,
        ],
        axis=1,
    )

    volume_summary = np.concatenate(
        [
            _zscore_summary(np.log1p(np.maximum(volume_w, 0.0))),
            _zscore_summary(turnover_w),
            _zscore_summary(amplitude_w),
        ],
        axis=1,
    )

    env_columns = [
        "market_return_mean",
        "market_trend_5",
        "market_volatility_5",
        "industry_return_mean",
        "industry_return_trend_5",
    ]
    environment_summary = np.concatenate(
        [_raw_summary(_rolling_windows(_series(frame, column, fillna=0.0), window_size)) for column in env_columns],
        axis=1,
    )

    return np.nan_to_num(
        np.concatenate([price_path, candle_geometry, volume_summary, environment_summary], axis=1),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    ).astype(np.float32, copy=False)


def _window_quality_mask(frame: pd.DataFrame, window_size: int, config) -> np.ndarray:
    required = ["open", "high", "low", "close", "volume"]
    non_null = np.column_stack([frame[column].notna().to_numpy(dtype=np.int8) for column in required]).sum(axis=1)
    non_null_count = _rolling_sum(non_null.astype(np.float32), window_size)
    non_null_ratio = non_null_count / float(window_size * len(required))

    volume = _series(frame, "volume", fillna=0.0)
    zero_volume_count = _rolling_sum((volume <= 0).astype(np.float32), window_size)
    zero_volume_ratio = zero_volume_count / float(window_size)

    open_ = _series(frame, "open")
    high = _series(frame, "high")
    low = _series(frame, "low")
    close = _series(frame, "close")
    finite_price = np.isfinite(np.column_stack([open_, high, low, close])).all(axis=1)
    finite_count = _rolling_sum(finite_price.astype(np.float32), window_size)

    high_invalid = high < np.maximum.reduce([open_, close, low])
    low_invalid = low > np.minimum.reduce([open_, close, high])
    high_invalid_count = _rolling_sum(high_invalid.astype(np.float32), window_size)
    low_invalid_count = _rolling_sum(low_invalid.astype(np.float32), window_size)

    return (
        (non_null_ratio >= float(config.quality.min_non_null_ratio))
        & (zero_volume_ratio <= float(config.quality.max_zero_volume_ratio))
        & (finite_count == window_size)
        & (high_invalid_count == 0)
        & (low_invalid_count == 0)
    )


def _series(frame: pd.DataFrame, column: str, *, fillna: float | None = None) -> np.ndarray:
    if column in frame.columns:
        series = frame[column]
    else:
        series = pd.Series(np.zeros(len(frame.index), dtype=np.float32))
    if fillna is not None:
        series = series.fillna(fillna)
    return series.to_numpy(dtype=np.float32, copy=False)


def _rolling_windows(values: np.ndarray, window_size: int) -> np.ndarray:
    if values.size < window_size:
        return np.zeros((0, window_size), dtype=np.float32)
    return np.lib.stride_tricks.sliding_window_view(values, window_size).astype(np.float32, copy=False)


def _rolling_sum(values: np.ndarray, window_size: int) -> np.ndarray:
    if values.size < window_size:
        return np.zeros((0,), dtype=np.float32)
    cumulative = np.concatenate([[0.0], np.cumsum(values, dtype=np.float64)])
    return (cumulative[window_size:] - cumulative[:-window_size]).astype(np.float32)


def _safe_denominator(values: np.ndarray) -> np.ndarray:
    return np.where(np.abs(values) < 1e-9, 1.0, values).astype(np.float32, copy=False)


def _zscore_summary(windows: np.ndarray) -> np.ndarray:
    mean = windows.mean(axis=1, dtype=np.float32)
    std = windows.std(axis=1, dtype=np.float32)
    safe_std = np.where(std < 1e-9, 1.0, std).astype(np.float32)
    first = (windows[:, 0] - mean) / safe_std
    last = (windows[:, -1] - mean) / safe_std
    normalized_std = np.where(std < 1e-9, 0.0, 1.0).astype(np.float32)
    zeros = np.zeros_like(first, dtype=np.float32)
    return np.column_stack([zeros, normalized_std, first, last]).astype(np.float32, copy=False)


def _raw_summary(windows: np.ndarray) -> np.ndarray:
    return np.column_stack(
        [
            windows.mean(axis=1, dtype=np.float32),
            windows.std(axis=1, dtype=np.float32),
            windows[:, 0],
            windows[:, -1],
        ]
    ).astype(np.float32, copy=False)


def _component_slices(window_size: int) -> dict[str, tuple[int, int]]:
    return {
        "price_path": (0, 2 * window_size),
        "candle_geometry": (2 * window_size, 5 * window_size),
        "volume_liquidity": (5 * window_size, 8 * window_size),
        "environment": (8 * window_size, 13 * window_size),
    }


def _slice(values: np.ndarray, slices: dict[str, tuple[int, int]], name: str) -> np.ndarray:
    start, end = slices.get(name, (0, 0))
    return values[start:end].astype(np.float32, copy=False)


def _component_summary(values: np.ndarray, *, groups: int) -> np.ndarray:
    if values.size == 0:
        return np.zeros(0, dtype=np.float32)
    chunks = np.array_split(values.astype(np.float32, copy=False), max(1, groups))
    summary: list[float] = []
    for chunk in chunks:
        if chunk.size == 0:
            summary.extend([0.0, 0.0, 0.0, 0.0])
            continue
        summary.extend(
            [
                float(np.mean(chunk, dtype=np.float32)),
                float(np.std(chunk, dtype=np.float32)),
                float(chunk[0]),
                float(chunk[-1]),
            ]
        )
    return np.asarray(summary, dtype=np.float32)


def _metadata_columns() -> list[str]:
    return [
        "symbol",
        "name",
        "industry",
        "listing_days",
        "frequency",
        "start_idx",
        "end_idx",
        "start_date",
        "end_date",
        "window_length",
        "window_id",
    ]


def _write_metadata_batch(
    writer: pq.ParquetWriter | None,
    metadata_path: Path,
    rows: list[dict[str, Any]],
) -> pq.ParquetWriter:
    table = pa.Table.from_pylist(rows, schema=_metadata_schema()).select(_metadata_columns())
    if writer is None:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        writer = pq.ParquetWriter(metadata_path, table.schema, compression="zstd")
    writer.write_table(table)
    return writer


def _metadata_schema() -> pa.Schema:
    return pa.schema(
        [
            ("symbol", pa.string()),
            ("name", pa.string()),
            ("industry", pa.string()),
            ("listing_days", pa.int64()),
            ("frequency", pa.string()),
            ("start_idx", pa.int64()),
            ("end_idx", pa.int64()),
            ("start_date", pa.string()),
            ("end_date", pa.string()),
            ("window_length", pa.int64()),
            ("window_id", pa.string()),
        ]
    )


def _commit_compact_artifacts(
    *,
    directory: Path,
    staged_files: dict[Path, Path],
    stale_targets: list[Path],
) -> None:
    backups: dict[Path, Path] = {}
    committed: list[Path] = []
    targets = list(staged_files.keys())
    try:
        for target in targets:
            if target.exists():
                backup = target.with_name(f".{target.name}.{uuid4().hex}.bak")
                os.replace(target, backup)
                backups[target] = backup
        for target, source in staged_files.items():
            os.replace(source, target)
            committed.append(target)
        for stale in stale_targets:
            if stale.exists():
                backup = stale.with_name(f".{stale.name}.{uuid4().hex}.bak")
                os.replace(stale, backup)
                backups[stale] = backup
    except Exception:
        for target in reversed(committed):
            _cleanup_file(target)
        for target, backup in reversed(list(backups.items())):
            if backup.exists():
                os.replace(backup, target)
        raise
    finally:
        for backup in backups.values():
            _cleanup_file(backup)


def _input_snapshot(store, frequency: Frequency, symbols: list[str]) -> dict[str, tuple[int, int]]:
    paths: list[Path] = []
    for symbol in symbols:
        path = store.bars_path(symbol, frequency)
        if path.exists():
            paths.append(path)
    for attr in ("market_context_path", "industry_context_path"):
        getter = getattr(store, attr, None)
        if callable(getter):
            path = getter()
            if path.exists():
                paths.append(path)
    snapshot: dict[str, tuple[int, int]] = {}
    for path in paths:
        stat = path.stat()
        snapshot[str(path)] = (int(stat.st_size), int(stat.st_mtime_ns))
    return snapshot


def _snapshot_fingerprint(snapshot: dict[str, tuple[int, int]]) -> str:
    import hashlib

    digest = hashlib.sha256()
    for path, token in sorted(snapshot.items()):
        digest.update(path.encode("utf-8", errors="replace"))
        digest.update(str(token[0]).encode("ascii"))
        digest.update(str(token[1]).encode("ascii"))
    return digest.hexdigest()


def _assert_input_snapshot_unchanged(
    before: dict[str, tuple[int, int]],
    after: dict[str, tuple[int, int]],
    *,
    phase: str,
) -> None:
    if before == after:
        return
    raise RuntimeError(
        "Input cached bars or context changed during compact index build "
        f"({phase}). Stop writers/backfill and rebuild again."
    )


def _cleanup_tree(path: Path) -> None:
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if child.is_file() or child.is_symlink():
            _cleanup_file(child)
        elif child.is_dir():
            try:
                child.rmdir()
            except OSError:
                pass
    try:
        path.rmdir()
    except OSError:
        pass


def _cleanup_file(path: Path | None) -> None:
    if path is None:
        return
    for attempt in range(5):
        try:
            path.unlink(missing_ok=True)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if attempt < 4:
                time.sleep(0.2)
                continue
            return

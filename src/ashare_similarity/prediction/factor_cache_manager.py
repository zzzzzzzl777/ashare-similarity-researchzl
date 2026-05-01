from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class FactorFrame:
    name: str
    frame: pd.DataFrame
    columns: tuple[str, ...]
    source: str
    asof_time: str
    lag_rule: str
    join_keys: tuple[str, ...] = ("symbol", "date")


@dataclass(frozen=True, slots=True)
class FactorCoverage:
    name: str
    source: str
    asof_time: str
    lag_rule: str
    rows: int
    coverage_rate: float
    columns: tuple[str, ...]
    fingerprint: str
    content_hash: str
    date_min: str | None
    date_max: str | None
    null_rates: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FactorCacheManager:
    """Cache and merge free external factors with explicit coverage metadata."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def cache_paths(self, name: str, fingerprint: str) -> dict[str, Path]:
        safe_name = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in name)
        stem = f"{safe_name}_{fingerprint}"
        return {
            "data": self.cache_dir / f"{stem}.parquet",
            "metadata": self.cache_dir / f"{stem}.json",
        }

    def write_factor(self, factor: FactorFrame) -> FactorCoverage:
        metadata = factor_coverage(factor, base_rows=len(factor.frame))
        paths = self.cache_paths(factor.name, metadata.fingerprint)
        factor.frame.to_parquet(paths["data"], index=False)
        _atomic_write_json(paths["metadata"], metadata.to_dict())
        return metadata


def merge_factor_frames(
    base: pd.DataFrame,
    factors: Iterable[FactorFrame],
    *,
    date_columns: tuple[str, ...] = ("date",),
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    merged = base.copy()
    for column in date_columns:
        if column in merged.columns:
            merged[column] = pd.to_datetime(merged[column], errors="coerce")
    reports: list[dict[str, Any]] = []
    for factor in factors:
        frame = factor.frame.copy()
        for key in factor.join_keys:
            if key in date_columns and key in frame.columns:
                frame[key] = pd.to_datetime(frame[key], errors="coerce")
        missing = [column for column in [*factor.join_keys, *factor.columns] if column not in frame.columns]
        if missing:
            raise ValueError(f"Factor `{factor.name}` missing columns: {missing}")
        value_columns = list(dict.fromkeys(factor.columns))
        before_columns = set(merged.columns)
        merged = merged.merge(frame[[*factor.join_keys, *value_columns]], how="left", on=list(factor.join_keys))
        availability = {}
        for column in value_columns:
            available_column = f"{column}_available"
            availability[available_column] = merged[column].notna().astype(np.float32)
            if pd.api.types.is_numeric_dtype(merged[column]):
                merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0.0)
        if availability:
            availability_frame = pd.DataFrame(availability, index=merged.index)
            existing = [column for column in availability_frame.columns if column in merged.columns]
            new_columns = [column for column in availability_frame.columns if column not in merged.columns]
            if existing:
                merged.loc[:, existing] = availability_frame[existing]
            if new_columns:
                merged = pd.concat([merged, availability_frame[new_columns]], axis=1).copy()
        coverage = {
            "name": factor.name,
            "source": factor.source,
            "asof_time": factor.asof_time,
            "lag_rule": factor.lag_rule,
            "rows": int(len(merged)),
            "coverage_rate": float(
                merged[[f"{column}_available" for column in value_columns]].mean(axis=1).mean()
                if len(merged)
                else 0.0
            ),
            "columns": value_columns,
            "availability_columns": [
                column for column in merged.columns if column.endswith("_available") and column not in before_columns
            ],
            "fingerprint": factor_fingerprint(factor),
            "content_hash": factor_content_hash(factor),
            "date_min": _factor_date_bound(factor.frame, factor.join_keys, which="min"),
            "date_max": _factor_date_bound(factor.frame, factor.join_keys, which="max"),
            "null_rates": _factor_null_rates(factor),
        }
        reports.append(coverage)
    return merged, reports


def factor_coverage(factor: FactorFrame, *, base_rows: int) -> FactorCoverage:
    coverage_values = []
    for column in factor.columns:
        if column not in factor.frame.columns:
            coverage_values.append(0.0)
        elif base_rows <= 0:
            coverage_values.append(0.0)
        else:
            coverage_values.append(float(factor.frame[column].notna().sum() / base_rows))
    coverage_rate = float(np.mean(coverage_values)) if coverage_values else 0.0
    return FactorCoverage(
        name=factor.name,
        source=factor.source,
        asof_time=factor.asof_time,
        lag_rule=factor.lag_rule,
        rows=int(len(factor.frame)),
        coverage_rate=coverage_rate,
        columns=factor.columns,
        fingerprint=factor_fingerprint(factor),
        content_hash=factor_content_hash(factor),
        date_min=_factor_date_bound(factor.frame, factor.join_keys, which="min"),
        date_max=_factor_date_bound(factor.frame, factor.join_keys, which="max"),
        null_rates=_factor_null_rates(factor),
    )


def factor_fingerprint(factor: FactorFrame) -> str:
    schema = {
        "name": factor.name,
        "columns": factor.columns,
        "source": factor.source,
        "asof_time": factor.asof_time,
        "lag_rule": factor.lag_rule,
        "join_keys": factor.join_keys,
        "rows": int(len(factor.frame)),
        "content_hash": factor_content_hash(factor),
        "date_min": _factor_date_bound(factor.frame, factor.join_keys, which="min"),
        "date_max": _factor_date_bound(factor.frame, factor.join_keys, which="max"),
        "null_rates": _factor_null_rates(factor),
    }
    raw = json.dumps(schema, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def factor_content_hash(factor: FactorFrame) -> str:
    columns = [column for column in [*factor.join_keys, *factor.columns] if column in factor.frame.columns]
    if not columns:
        return "empty"
    frame = factor.frame.loc[:, columns].copy()
    for column in frame.columns:
        if pd.api.types.is_datetime64_any_dtype(frame[column]):
            frame[column] = pd.to_datetime(frame[column], errors="coerce").astype("datetime64[ns]")
    frame = frame.sort_values(columns).reset_index(drop=True)
    hashed = pd.util.hash_pandas_object(frame, index=False).to_numpy(dtype=np.uint64)
    return hashlib.sha256(hashed.tobytes()).hexdigest()[:16]


def _factor_date_bound(frame: pd.DataFrame, join_keys: tuple[str, ...], *, which: str) -> str | None:
    date_columns = [column for column in join_keys if column in frame.columns and "date" in column]
    if not date_columns:
        date_columns = [column for column in frame.columns if column == "date" or column.endswith("_date")]
    if not date_columns:
        return None
    values = pd.to_datetime(frame[date_columns[0]], errors="coerce")
    value = values.min() if which == "min" else values.max()
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def _factor_null_rates(factor: FactorFrame) -> dict[str, float]:
    rates: dict[str, float] = {}
    row_count = len(factor.frame)
    for column in factor.columns:
        if column not in factor.frame.columns or row_count <= 0:
            rates[column] = 1.0
        else:
            rates[column] = float(factor.frame[column].isna().mean())
    return rates


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp_path.replace(path)

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
        for column in value_columns:
            available_column = f"{column}_available"
            merged[available_column] = merged[column].notna().astype(np.float32)
            if pd.api.types.is_numeric_dtype(merged[column]):
                merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0.0)
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
    }
    raw = json.dumps(schema, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp_path.replace(path)

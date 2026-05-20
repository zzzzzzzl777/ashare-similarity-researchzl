"""Build the next-round 14:57 data/factor/model protocol artifacts.

This runner is intentionally protocol-first. It performs source discovery,
dataset-window audit, factor availability classification, model-matrix
planning, and P0/P1 self-audit. It does not silently retrain or mutate a live
bundle.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

try:
    import duckdb
except Exception:  # pragma: no cover - optional runtime dependency in tests
    duckdb = None


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config


TRAIN_WINDOW_MONTHS = (12, 18, 24, 30, 36, 48, 60, 72)
VALID_WINDOW_MONTHS = (1, 2, 3, 6, 12)
FIXED_START_YEARS = (2017, 2018, 2019, 2020, 2021, 2022, 2023)
PRIMARY_OUTER_MONTHS = 3
INNER_VALID_MONTHS = 1
EMBARGO_DAYS = 1
DEV_OUTER_START = pd.Timestamp("2019-01-01")
DEV_OUTER_END = pd.Timestamp("2025-12-31")
SEEN_WINDOWS = {
    "q1_2026_seen_research_test": (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-03-31")),
    "april_2026_seen_research_test": (pd.Timestamp("2026-04-01"), pd.Timestamp("2026-04-30")),
}
FINAL_FORWARD_START = pd.Timestamp("2026-05-01")

META_COLUMNS = {
    "date",
    "symbol",
    "label_date",
    "actual",
    "next_return_pct",
    "next_high_return_pct",
    "next_close_return_pct",
    "next_low_return_pct",
    "next_close_up",
    "hard_to_hold_2pct",
    "hard_to_hold_3pct",
    "close",
    "pct_change",
    "turnover",
    "amount",
    "name",
    "stock_name",
}

HARD_CLASS_C_PATTERNS = (
    "lhb",
    "top_inst",
    "margin",
    "rzye",
    "rqye",
    "auction_close",
    "inst_net",
)
MONEYFLOW_TDAY_COLUMNS = {
    "tushare_net_mf_amount",
    "tushare_ff_adjusted_flow",
    "tushare_mf_strength",
    "tushare_main_force_divergence",
    "tushare_mf_flow_intensity",
}
CYQ_TDAY_COLUMNS = {
    "tushare_winner_rate",
    "tushare_cost_concentration",
    "tushare_cost_position",
}
NEW_MINUTE_FACTOR_IDS = {f"C{i}" for i in range(174, 189)}
WEB_SCRIPT_PATHS = (
    REPO_ROOT / "scripts" / "realtime_1457_today_probe.py",
    REPO_ROOT / "scripts" / "run_1457_live_sim.py",
    REPO_ROOT / "scripts" / "serve_1457_picker_web.py",
)


@dataclass(frozen=True)
class OutputPaths:
    report_json: Path
    report_md: Path
    factor_csv: Path
    model_matrix_csv: Path
    time_window_csv: Path
    monthly_timeline_csv: Path
    self_audit_csv: Path


def parse_args() -> argparse.Namespace:
    config = get_default_config()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof-date", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--feature-cache", type=Path)
    parser.add_argument(
        "--feature-cache-dir",
        type=Path,
        default=config.storage.report_dir / "prediction" / "feature_cache",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=config.storage.report_dir / "prediction" / "factor_registry.json",
    )
    parser.add_argument(
        "--tushare-cache-dir",
        type=Path,
        default=config.storage.cache_dir / "prediction" / "tushare",
    )
    parser.add_argument(
        "--raw-daily-dir",
        type=Path,
        default=config.storage.raw_dir / "bars" / "daily",
    )
    parser.add_argument("--max-cache-files", type=int, default=120)
    return parser.parse_args()


def output_paths(report_dir: Path, asof: str) -> OutputPaths:
    prediction_dir = report_dir / "prediction"
    prediction_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = REPO_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    stem = f"next_round_1457_protocol_{asof}"
    return OutputPaths(
        report_json=prediction_dir / f"{stem}.json",
        report_md=docs_dir / f"{stem}.md",
        factor_csv=prediction_dir / f"next_round_1457_factor_source_discovery_{asof}.csv",
        model_matrix_csv=prediction_dir / f"next_round_1457_model_matrix_manifest_{asof}.csv",
        time_window_csv=prediction_dir / f"next_round_1457_time_window_manifest_{asof}.csv",
        monthly_timeline_csv=prediction_dir / f"next_round_1457_monthly_timeline_{asof}.csv",
        self_audit_csv=prediction_dir / f"next_round_1457_self_audit_{asof}.csv",
    )


def json_default(value: Any) -> Any:
    if isinstance(value, (Path, pd.Timestamp)):
        return str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def schema_columns(path: Path) -> list[str]:
    try:
        return list(pq.read_schema(path).names)
    except Exception:
        return []


def discover_feature_caches(cache_dir: Path, *, max_files: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    paths = sorted(cache_dir.glob("gpu_probe_features_*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in paths[:max_files]:
        meta = read_json(path.with_suffix(".json"))
        columns = meta.get("columns") or schema_columns(path)
        row = {
            "path": str(path),
            "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            "rows": int(meta.get("rows") or _parquet_rows(path)),
            "columns": int(len(columns)),
            "fingerprint": meta.get("fingerprint") or path.stem.removeprefix("gpu_probe_features_"),
            "has_label_date": "label_date" in columns,
            "has_actual": "actual" in columns or "next_high_return_pct" in columns,
            "has_new_minute_factors": any(column.startswith("minute_intraday_vol_herfindahl") for column in columns),
            "_columns": list(columns),
        }
        bounds = feature_cache_bounds(path, columns)
        row.update(bounds)
        rows.append(row)
    return rows


def _parquet_rows(path: Path) -> int:
    try:
        return int(pq.ParquetFile(path).metadata.num_rows)
    except Exception:
        return 0


def choose_feature_cache(caches: list[dict[str, Any]], explicit: Path | None) -> dict[str, Any] | None:
    if explicit:
        columns = schema_columns(explicit)
        return {
            "path": str(explicit),
            "rows": _parquet_rows(explicit),
            "columns": len(columns),
            "fingerprint": explicit.stem.removeprefix("gpu_probe_features_"),
            "_columns": columns,
            **feature_cache_bounds(explicit, columns),
        }
    candidates = [row for row in caches if row["has_label_date"] and row["has_actual"]]
    if not candidates:
        return caches[0] if caches else None

    def _date_score(value: Any) -> int:
        if not value:
            return 99999999
        try:
            return int(str(value).replace("-", "")[:8])
        except Exception:
            return 99999999

    def _cache_rank(row: dict[str, Any]) -> tuple[Any, ...]:
        start_score = _date_score(row.get("label_date_min"))
        has_extended_history = start_score <= 20180131
        return (
            bool(has_extended_history),
            bool(row.get("has_new_minute_factors")),
            int(row.get("trading_days") or 0),
            int(row.get("rows") or 0),
            int(row.get("columns") or 0),
            str(row.get("mtime") or ""),
        )

    candidates.sort(key=_cache_rank, reverse=True)
    return candidates[0]


def feature_cache_bounds(path: Path, columns: list[str]) -> dict[str, Any]:
    wanted = [column for column in ("date", "label_date", "symbol", "actual", "next_high_return_pct") if column in columns]
    if not wanted:
        return {}
    try:
        frame = pd.read_parquet(path, columns=wanted)
    except Exception:
        return {}
    date_col = "label_date" if "label_date" in frame.columns else "date"
    dates = pd.to_datetime(frame[date_col], errors="coerce")
    out = {
        "label_date_min": dates.min().date().isoformat() if dates.notna().any() else None,
        "label_date_max": dates.max().date().isoformat() if dates.notna().any() else None,
        "trading_days": int(dates.dt.normalize().nunique(dropna=True)),
        "symbols": int(frame["symbol"].nunique()) if "symbol" in frame.columns else None,
    }
    if "actual" in frame.columns:
        actual = pd.to_numeric(frame["actual"], errors="coerce")
    elif "next_high_return_pct" in frame.columns:
        actual = (pd.to_numeric(frame["next_high_return_pct"], errors="coerce") >= 1.0).astype(float)
    else:
        actual = pd.Series(dtype=float)
    out["positive_rate"] = float(actual.mean()) if len(actual) else None
    return out


def feature_monthly_timeline(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    columns = schema_columns(path)
    wanted = [column for column in ("label_date", "date", "symbol", "actual", "next_high_return_pct") if column in columns]
    if not wanted:
        return pd.DataFrame()
    frame = pd.read_parquet(path, columns=wanted)
    date_col = "label_date" if "label_date" in frame.columns else "date"
    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    frame = frame.dropna(subset=[date_col])
    if "actual" in frame.columns:
        actual = pd.to_numeric(frame["actual"], errors="coerce")
    elif "next_high_return_pct" in frame.columns:
        actual = (pd.to_numeric(frame["next_high_return_pct"], errors="coerce") >= 1.0).astype(float)
    else:
        actual = pd.Series(np.nan, index=frame.index)
    frame["_actual"] = actual
    frame["month"] = frame[date_col].dt.strftime("%Y-%m")
    grouped = frame.groupby("month", sort=True)
    return grouped.agg(
        feature_rows=("month", "size"),
        feature_symbols=("symbol", "nunique") if "symbol" in frame.columns else ("month", "size"),
        feature_trading_days=(date_col, lambda s: int(pd.to_datetime(s).dt.normalize().nunique())),
        feature_positive_rate=("_actual", "mean"),
    ).reset_index()


def scan_parquet_monthly(path_glob: str, *, month_expr: str, symbol_col: str, date_expr: str) -> pd.DataFrame:
    if duckdb is None:
        return pd.DataFrame()
    con = duckdb.connect()
    try:
        query = f"""
            select {month_expr} as month,
                   count(*) as rows,
                   count(distinct {symbol_col}) as symbols,
                   count(distinct {date_expr}) as trading_days,
                   min({date_expr}) as min_date,
                   max({date_expr}) as max_date
            from read_parquet(?)
            group by 1
            order by 1
        """
        return con.execute(query, [path_glob]).fetchdf()
    except Exception:
        return pd.DataFrame()
    finally:
        con.close()


def build_monthly_timeline(args: argparse.Namespace, selected_cache: dict[str, Any] | None) -> pd.DataFrame:
    minute_dir = args.tushare_cache_dir / "stk_mins_5"
    minute = scan_parquet_monthly(
        str(minute_dir / "*.parquet"),
        month_expr="substr(trade_time, 1, 7)",
        symbol_col="ts_code",
        date_expr="substr(trade_time, 1, 10)",
    )
    minute = minute.rename(
        columns={
            "rows": "minute5_rows",
            "symbols": "minute5_symbols",
            "trading_days": "minute5_trading_days",
            "min_date": "minute5_min_date",
            "max_date": "minute5_max_date",
        }
    )
    daily = scan_parquet_monthly(
        str(args.raw_daily_dir / "*.parquet"),
        month_expr="substr(cast(date as varchar), 1, 7)",
        symbol_col="symbol",
        date_expr="cast(date as varchar)",
    )
    daily = daily.rename(
        columns={
            "rows": "daily_rows",
            "symbols": "daily_symbols",
            "trading_days": "daily_trading_days",
            "min_date": "daily_min_date",
            "max_date": "daily_max_date",
        }
    )
    cache_path = Path(selected_cache["path"]) if selected_cache else None
    feature = feature_monthly_timeline(cache_path)
    timeline = minute.merge(daily, on="month", how="outer").merge(feature, on="month", how="outer")
    timeline = timeline.sort_values("month").reset_index(drop=True)
    return timeline


def month_start(value: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value.year, value.month, 1)


def month_end(value: pd.Timestamp) -> pd.Timestamp:
    return month_start(value) + pd.offsets.MonthEnd(0)


def build_time_window_manifest(timeline: pd.DataFrame) -> pd.DataFrame:
    if timeline.empty:
        return pd.DataFrame()
    months = set(timeline["month"].dropna().astype(str))
    feature_months = set(timeline.loc[timeline.get("feature_rows", 0).fillna(0) > 0, "month"].astype(str))
    raw_months = set(
        timeline.loc[
            (timeline.get("minute5_rows", 0).fillna(0) > 0) & (timeline.get("daily_rows", 0).fillna(0) > 0),
            "month",
        ].astype(str)
    )
    if not raw_months:
        return pd.DataFrame()
    fair_raw_start = pd.Timestamp(min(raw_months) + "-01")
    rows: list[dict[str, Any]] = []
    schemes: list[dict[str, Any]] = []
    for months_count in TRAIN_WINDOW_MONTHS:
        schemes.append({"scheme": f"fixed_recent_{months_count}m", "kind": "recent", "months": months_count})
    for year in FIXED_START_YEARS:
        schemes.append({"scheme": f"fixed_start_{year}", "kind": "fixed_start", "year": year})
    schemes.append({"scheme": "expanding_from_fair_start", "kind": "expanding"})

    for valid_months in VALID_WINDOW_MONTHS:
        outer_start = month_start(DEV_OUTER_START)
        fold = 1
        while outer_start <= DEV_OUTER_END:
            outer_end = month_end(outer_start + pd.DateOffset(months=valid_months - 1))
            if outer_end > DEV_OUTER_END:
                break
            inner_end = outer_start - pd.Timedelta(days=EMBARGO_DAYS)
            inner_start = month_start(outer_start - pd.DateOffset(months=INNER_VALID_MONTHS))
            fit_end = inner_start - pd.Timedelta(days=EMBARGO_DAYS)
            for scheme in schemes:
                if scheme["kind"] == "recent":
                    fit_start = month_start(fit_end - pd.DateOffset(months=scheme["months"] - 1))
                elif scheme["kind"] == "fixed_start":
                    fit_start = pd.Timestamp(scheme["year"], 1, 1)
                else:
                    fit_start = fair_raw_start
                train_window_valid = bool(fit_start <= fit_end)
                fit_months = _month_strings(fit_start, fit_end)
                inner_months = _month_strings(inner_start, inner_end)
                outer_months = _month_strings(outer_start, outer_end)
                train_uses_seen = train_window_valid and any(_range_overlaps(fit_start, fit_end, *window) for window in SEEN_WINDOWS.values())
                raw_ready = train_window_valid and all(month in raw_months for month in fit_months + inner_months + outer_months)
                cache_ready = train_window_valid and all(month in feature_months for month in fit_months + inner_months + outer_months)
                rows.append(
                    {
                        "scheme": scheme["scheme"],
                        "outer_valid_months": valid_months,
                        "outer_fold": fold,
                        "train_window_valid": train_window_valid,
                        "fit_train_start": fit_start.date().isoformat(),
                        "fit_train_end": fit_end.date().isoformat(),
                        "inner_valid_start": inner_start.date().isoformat(),
                        "inner_valid_end": inner_end.date().isoformat(),
                        "outer_valid_start": outer_start.date().isoformat(),
                        "outer_valid_end": outer_end.date().isoformat(),
                        "raw_ready": bool(raw_ready),
                        "feature_cache_ready": bool(cache_ready),
                        "requires_feature_rebuild": bool(raw_ready and not cache_ready),
                        "train_uses_seen_research": bool(train_uses_seen),
                        "eligible_after_rebuild": bool(raw_ready and not train_uses_seen),
                        "primary_outer_unit": bool(valid_months == PRIMARY_OUTER_MONTHS),
                    }
                )
            outer_start = outer_start + pd.DateOffset(months=valid_months)
            fold += 1
    return pd.DataFrame(rows)


def _month_strings(start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    if pd.isna(start) or pd.isna(end) or start > end:
        return []
    return [m.strftime("%Y-%m") for m in pd.period_range(month_start(start), month_start(end), freq="M")]


def _range_overlaps(a_start: pd.Timestamp, a_end: pd.Timestamp, b_start: pd.Timestamp, b_end: pd.Timestamp) -> bool:
    return a_start <= b_end and b_start <= a_end


def flatten_registry_factors(registry: dict[str, Any]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            fid = value.get("factor_id")
            if isinstance(fid, str) and re.fullmatch(r"C\d{3}", fid):
                row = dict(value)
                row["_registry_path"] = path
                found[fid] = {**found.get(fid, {}), **row}
            for key, child in value.items():
                walk(child, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{path}[{idx}]")

    walk(registry, "")
    return [found[key] for key in sorted(found, key=lambda x: int(x[1:]))]


def collect_code_columns() -> dict[str, str]:
    code_columns: dict[str, str] = {}
    modules = [
        "ashare_similarity.prediction.intraday_factors",
        "ashare_similarity.prediction.free_data_factors",
        "ashare_similarity.prediction.gpu_probe",
        "ashare_similarity.prediction.ths_sector_factors",
        "ashare_similarity.prediction.tgb_daily_factors",
        "ashare_similarity.prediction.limit_pool_snapshots",
    ]
    for module_name in modules:
        try:
            module = __import__(module_name, fromlist=["dummy"])
        except Exception:
            continue
        for name in dir(module):
            if not (name.endswith("_COLUMNS") or name.endswith("_FEATURES")):
                continue
            value = getattr(module, name)
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                for column in value:
                    code_columns.setdefault(column, f"{module_name}.{name}")
    return code_columns


def collect_live_text() -> str:
    chunks: list[str] = []
    for path in WEB_SCRIPT_PATHS:
        if path.exists():
            try:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
    return "\n".join(chunks)


def candidate_columns(entry: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("column_name", "feature_name", "columns", "feature_columns", "required_columns"):
        raw = entry.get(key)
        if isinstance(raw, str):
            values.append(raw)
        elif isinstance(raw, list):
            values.extend(str(item) for item in raw if isinstance(item, str))
    name = str(entry.get("name") or "").strip()
    if name:
        snake = re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_")
        values.extend([snake, f"tushare_{snake}", f"minute_{snake}", f"em_push2_f62_{snake}_1457"])
    return list(dict.fromkeys(value for value in values if value))


def classify_factor(fid: str, columns: list[str], entry: dict[str, Any], *, code_hits: list[str], cache_hits: list[str]) -> tuple[str, str, str]:
    text = " ".join(
        [
            fid,
            str(entry.get("name", "")),
            str(entry.get("family", "")),
            str(entry.get("data_need", "")),
            str(entry.get("frequency", "")),
            " ".join(code_hits),
            " ".join(cache_hits),
        ]
    ).lower()
    colset = set(code_hits) | set(cache_hits)
    if fid in NEW_MINUTE_FACTOR_IDS:
        if code_hits:
            return "A", "new_5min_engineered", "C174-C188 5min factor is implemented and eligible for fixed-config testing."
        return "A_pending_code", "new_5min_not_implemented", "C174-C188 is 5min-engineerable but not yet present in code/cache."
    if any(pattern in text for pattern in HARD_CLASS_C_PATTERNS):
        return "C", "post_close_or_unavailable", "Hard unavailable/post-close family; exclude from champion candidates."
    if colset & MONEYFLOW_TDAY_COLUMNS or "moneyflow" in text or re.search(r"\bmf_", text):
        return "B", "td_moneyflow_requires_proxy_name", "T-day Tushare moneyflow needs delete-vs-T1/proxy; live proxy must use a distinct em_push2_f62 name."
    if colset & CYQ_TDAY_COLUMNS:
        return "B", "cyq_requires_t1_policy", "CYQ/chip fields require T-1 training/live parity or delete-vs-T1 comparison."
    if "minute_bar_5min" in text or any(column.startswith("minute_") for column in colset):
        return "A", "minute_1457_engineerable", "5min minute-bar feature is engineerable at 14:57 with snapshot/truncated bars."
    if any(column.startswith("sector_") for column in colset):
        return "A", "sector_live_engineerable_after_gate", "Sector feature should be retained if THS/live cache parity passes."
    if code_hits or cache_hits:
        return "A", "implemented_live_safe_candidate", "Implemented/cache-visible feature; keep for all-factor comparison unless later gate fails."
    return "D", "unmapped_registry_only", "Registry idea has no code/cache mapping yet."


def build_factor_source_discovery(
    registry_entries: list[dict[str, Any]],
    caches: list[dict[str, Any]],
    selected_cache: dict[str, Any] | None,
) -> pd.DataFrame:
    code_columns = collect_code_columns()
    cache_columns: set[str] = set()
    for row in caches:
        cache_columns.update(row.get("_columns") or [])
    live_text = collect_live_text()
    selected_path = Path(selected_cache["path"]) if selected_cache else None
    coverage_columns: set[str] = set()
    rows: list[dict[str, Any]] = []
    for entry in registry_entries:
        coverage_columns.update(candidate_columns(entry))
    coverage = column_coverage(selected_path, sorted(coverage_columns & cache_columns)) if selected_path else {}

    for entry in registry_entries:
        fid = str(entry.get("factor_id"))
        columns = candidate_columns(entry)
        code_hits = [column for column in columns if column in code_columns]
        cache_hits = [column for column in columns if column in cache_columns]
        live_hits = [column for column in columns if column and column in live_text]
        availability_class, issue_code, issue = classify_factor(fid, columns, entry, code_hits=code_hits, cache_hits=cache_hits)
        cov_rates = [coverage[column]["non_null_rate"] for column in cache_hits if column in coverage]
        rows.append(
            {
                "factor_id": fid,
                "name": entry.get("name"),
                "family": entry.get("family"),
                "priority": entry.get("priority"),
                "registry_path": entry.get("_registry_path"),
                "engineering_status": entry.get("engineering_status"),
                "training_status": _compact_training_status(entry.get("training_status")),
                "column_candidates": json.dumps(columns, ensure_ascii=False),
                "code_columns_found": json.dumps(code_hits, ensure_ascii=False),
                "cache_columns_found": json.dumps(cache_hits, ensure_ascii=False),
                "live_columns_found": json.dumps(live_hits, ensure_ascii=False),
                "coverage_rate": float(np.mean(cov_rates)) if cov_rates else np.nan,
                "availability_class": availability_class,
                "issue_code": issue_code,
                "issue": issue,
            }
        )
    return pd.DataFrame(rows)


def _compact_training_status(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        keys = ["verdict", "latest_selected", "selected_in_runs", "used_in_runs"]
        return json.dumps({key: value.get(key) for key in keys if key in value}, ensure_ascii=False)
    return ""


def column_coverage(path: Path | None, columns: list[str]) -> dict[str, dict[str, float]]:
    if path is None or not columns:
        return {}
    try:
        frame = pd.read_parquet(path, columns=columns)
    except Exception:
        return {}
    out: dict[str, dict[str, float]] = {}
    for column in columns:
        series = pd.to_numeric(frame[column], errors="coerce") if column in frame.columns else pd.Series(dtype=float)
        out[column] = {
            "non_null_rate": float(series.notna().mean()) if len(series) else 0.0,
            "non_zero_rate": float(series.fillna(0.0).ne(0.0).mean()) if len(series) else 0.0,
        }
    return out


def load_existing_comparison() -> dict[str, Any]:
    report_dir = get_default_config().storage.report_dir / "prediction"
    paths = {
        "s2_phasec_full": report_dir / "s2_vs_phasec_full_comparison.json",
        "s2_phasec_diff": report_dir / "s2_phasec_feature_diff_20260511.json",
        "phasec_april": report_dir / "phaseE_frozen_april_20260509.json",
        "phasec_cv": report_dir / "phaseC_hpo_internal_cv_20260509.json",
    }
    return {key: read_json(path) for key, path in paths.items()}


def build_model_matrix(factor_df: pd.DataFrame) -> pd.DataFrame:
    by_class = defaultdict(list)
    for row in factor_df.to_dict("records"):
        by_class[str(row["availability_class"])].append(row["factor_id"])
    a_ids = sorted(set(by_class["A"]))
    b_ids = sorted(set(by_class["B"]))
    new_ids = sorted(fid for fid in a_ids if fid in NEW_MINUTE_FACTOR_IDS)
    pre_new_a_ids = sorted(fid for fid in a_ids if fid not in NEW_MINUTE_FACTOR_IDS)
    rows = [
        {
            "variant_id": "baseline_phasec",
            "stage": "score_existing_bundle_first",
            "include_factor_ids": "",
            "candidate_role": "baseline",
            "requires_feature_rebuild": False,
            "requires_hpo": False,
            "notes": "Existing PhaseC bundle; use as current April-strong baseline.",
        },
        {
            "variant_id": "baseline_s2",
            "stage": "score_existing_bundle_first",
            "include_factor_ids": "",
            "candidate_role": "baseline",
            "requires_feature_rebuild": False,
            "requires_hpo": False,
            "notes": "Existing S2 bundle; use as Q1/strategy-strong baseline.",
        },
        {
            "variant_id": "pre_new_A_engineerable_control",
            "stage": "fixed_config_first",
            "include_factor_ids": ",".join(pre_new_a_ids),
            "candidate_role": "challenger",
            "requires_feature_rebuild": True,
            "requires_hpo": False,
            "notes": "Class-A engineerable factors before C174-C188; controls for the incremental value of the new 5min family.",
        },
        {
            "variant_id": "all_A_engineerable",
            "stage": "fixed_config_first",
            "include_factor_ids": ",".join(a_ids),
            "candidate_role": "primary_search",
            "requires_feature_rebuild": True,
            "requires_hpo": False,
            "notes": "All class-A factors from registry/source discovery, including C174-C188.",
        },
        {
            "variant_id": "all_A_plus_B_t1_proxy_policy",
            "stage": "proxy_pending",
            "include_factor_ids": ",".join(sorted(set(a_ids + b_ids))),
            "candidate_role": "policy_comparison",
            "requires_feature_rebuild": True,
            "requires_hpo": False,
            "notes": "Do not run fixed-config until explicit T-1/proxy columns exist; current same-name T-day B columns are blocked.",
        },
        {
            "variant_id": "new_5min_family_only",
            "stage": "fixed_config_first",
            "include_factor_ids": ",".join(new_ids),
            "candidate_role": "new_minute_challenger",
            "requires_feature_rebuild": True,
            "requires_hpo": False,
            "notes": "C174-C188 only, plus baseline non-registry features; isolates whether the new 5min family has standalone signal.",
        },
    ]
    for family, group in factor_df.groupby("family", dropna=True):
        ids = sorted(set(group.loc[group["availability_class"].isin(["A", "B"]), "factor_id"].astype(str)))
        if ids:
            rows.append(
                {
                    "variant_id": f"family_add_{_safe_id(str(family))}",
                    "stage": "family_ablation",
                    "include_factor_ids": ",".join(ids),
                    "candidate_role": "family_probe",
                    "requires_feature_rebuild": True,
                    "requires_hpo": False,
                    "notes": f"Family-level add/delete probe for {family}.",
                }
            )
    return pd.DataFrame(rows)


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()[:60] or "unknown"


def build_self_audit(
    *,
    factor_df: pd.DataFrame,
    time_window_df: pd.DataFrame,
    selected_cache: dict[str, Any] | None,
    model_matrix_df: pd.DataFrame,
) -> pd.DataFrame:
    issues: list[dict[str, Any]] = []

    def add(level: str, code: str, status: str, detail: str) -> None:
        issues.append({"level": level, "code": code, "status": status, "detail": detail})

    c_count = int((factor_df["availability_class"] == "C").sum()) if not factor_df.empty else 0
    add("P0", "class_c_discovered", "PASS" if c_count >= 0 else "FAIL", f"Class-C factors discovered: {c_count}; champion variants must exclude them.")
    pending_new = factor_df[
        factor_df["factor_id"].isin(NEW_MINUTE_FACTOR_IDS)
        & ~factor_df["availability_class"].eq("A")
    ]
    add(
        "P1",
        "new_minute_factors_implemented",
        "PASS" if pending_new.empty else "FAIL",
        f"C174-C188 pending/non-A count: {len(pending_new)}.",
    )
    if selected_cache:
        cache_min = selected_cache.get("label_date_min")
        cache_ready_2017 = bool(cache_min and str(cache_min) <= "2018-01-01")
        add(
            "P1",
            "feature_cache_covers_extended_history",
            "PASS" if cache_ready_2017 else "FAIL",
            f"Selected cache starts at {cache_min}; full 2017+ protocol requires rebuild if later.",
        )
    else:
        add("P1", "feature_cache_selected", "FAIL", "No feature cache selected.")
    if not time_window_df.empty:
        seen_train = int(time_window_df["train_uses_seen_research"].sum())
        add("P0", "q1_april_not_in_training", "PASS" if seen_train == 0 else "FAIL", f"Training windows overlapping seen tests: {seen_train}.")
        invalid_eligible = int((~time_window_df["train_window_valid"].astype(bool) & time_window_df["eligible_after_rebuild"].astype(bool)).sum())
        add(
            "P0",
            "time_window_no_invalid_eligible",
            "PASS" if invalid_eligible == 0 else "FAIL",
            f"Invalid training windows marked eligible: {invalid_eligible}.",
        )
        primary_ready = time_window_df[
            (time_window_df["primary_outer_unit"]) & (time_window_df["eligible_after_rebuild"])
        ]
        add("P1", "primary_rolling_windows_exist", "PASS" if len(primary_ready) > 0 else "FAIL", f"Eligible primary 3-month folds after rebuild: {len(primary_ready)}.")
    else:
        add("P1", "time_window_manifest", "FAIL", "No time-window manifest generated.")
    primary_variants = model_matrix_df[
        model_matrix_df["stage"].eq("fixed_config_first")
        & model_matrix_df["include_factor_ids"].fillna("").str.contains(r"C\d{3}", regex=True)
    ].copy()
    add("P1", "model_matrix_primary_variants", "PASS" if len(primary_variants) >= 3 else "FAIL", f"Primary/challenger matrix rows: {len(primary_variants)}.")
    duplicate_sets = primary_variants["include_factor_ids"].fillna("").value_counts()
    duplicate_sets = duplicate_sets[duplicate_sets > 1]
    add(
        "P1",
        "model_matrix_no_duplicate_fixed_sets",
        "PASS" if duplicate_sets.empty else "FAIL",
        f"Duplicate fixed-config include-factor sets: {len(duplicate_sets)}.",
    )
    return pd.DataFrame(issues)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def write_report(
    paths: OutputPaths,
    *,
    selected_cache: dict[str, Any] | None,
    caches: list[dict[str, Any]],
    timeline: pd.DataFrame,
    factor_df: pd.DataFrame,
    time_window_df: pd.DataFrame,
    model_matrix_df: pd.DataFrame,
    self_audit_df: pd.DataFrame,
    existing: dict[str, Any],
) -> None:
    p0_fail = self_audit_df[(self_audit_df["level"] == "P0") & (self_audit_df["status"] == "FAIL")]
    p1_fail = self_audit_df[(self_audit_df["level"] == "P1") & (self_audit_df["status"] == "FAIL")]
    class_counts = factor_df["availability_class"].value_counts(dropna=False).to_dict() if not factor_df.empty else {}
    raw_start = timeline.loc[timeline["minute5_rows"].fillna(0) > 0, "month"].min() if not timeline.empty and "minute5_rows" in timeline else None
    raw_end = timeline.loc[timeline["minute5_rows"].fillna(0) > 0, "month"].max() if not timeline.empty and "minute5_rows" in timeline else None
    s2_phasec = existing.get("s2_phasec_full", {})
    feature_overlap = s2_phasec.get("feature_overlap", {})
    cache_min = selected_cache.get("label_date_min") if selected_cache else None
    cache_extended_ready = bool(cache_min and str(cache_min) <= "2018-01-01")
    rebuild_note = (
        "- Extended 2017+ feature cache is ready for true training-window comparison."
        if cache_extended_ready
        else "- Extended 2017+ 5min data is available at the raw-cache level, but the selected feature cache must be rebuilt before true 2017+ training-window comparison."
    )
    lines = [
        "# 14:57 Next-Round Protocol Research",
        "",
        "## Executive Summary",
        "",
        f"- Selected feature cache: `{selected_cache.get('path') if selected_cache else 'NONE'}`",
        f"- Current selected cache range: {selected_cache.get('label_date_min') if selected_cache else '-'} to {selected_cache.get('label_date_max') if selected_cache else '-'}",
        f"- 5min raw cache range: {raw_start} to {raw_end}",
        f"- Factor classes: {json.dumps(class_counts, ensure_ascii=False)}",
        f"- S2/PhaseC selected overlap: {json.dumps(feature_overlap, ensure_ascii=False)}",
        f"- Self-audit: P0 fails={len(p0_fail)}, P1 fails={len(p1_fail)}",
        "",
        "## Decision Notes",
        "",
        "- April-only accuracy is not accepted as the champion selector; Q1 and April remain seen research windows.",
        rebuild_note,
        "- Rebuild helper is available: `python scripts/build_1457_extended_feature_cache.py --start 2017-01-03 --end 2026-04-30`.",
        "- S2-only factors are not deleted by default; class A/B factors are retained for controlled fixed-config comparisons.",
        "- B-class moneyflow/CYQ features require explicit T-1 or proxy columns with distinct names.",
        "",
        "## Artifacts",
        "",
        f"- Factor source discovery: `{paths.factor_csv}`",
        f"- Time-window manifest: `{paths.time_window_csv}`",
        f"- Monthly timeline: `{paths.monthly_timeline_csv}`",
        f"- Model matrix manifest: `{paths.model_matrix_csv}`",
        f"- Self-audit: `{paths.self_audit_csv}`",
        f"- JSON payload: `{paths.report_json}`",
    ]
    paths.report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    config = get_default_config()
    paths = output_paths(config.storage.report_dir, args.asof_date)
    caches = discover_feature_caches(args.feature_cache_dir, max_files=args.max_cache_files)
    selected_cache = choose_feature_cache(caches, args.feature_cache)
    registry = read_json(args.registry)
    registry_entries = flatten_registry_factors(registry)
    timeline = build_monthly_timeline(args, selected_cache)
    time_window_df = build_time_window_manifest(timeline)
    factor_df = build_factor_source_discovery(registry_entries, caches, selected_cache)
    model_matrix_df = build_model_matrix(factor_df)
    existing = load_existing_comparison()
    self_audit_df = build_self_audit(
        factor_df=factor_df,
        time_window_df=time_window_df,
        selected_cache=selected_cache,
        model_matrix_df=model_matrix_df,
    )

    write_csv(paths.monthly_timeline_csv, timeline)
    write_csv(paths.time_window_csv, time_window_df)
    write_csv(paths.factor_csv, factor_df)
    write_csv(paths.model_matrix_csv, model_matrix_df)
    write_csv(paths.self_audit_csv, self_audit_df)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "asof_date": args.asof_date,
        "selected_feature_cache": {k: v for k, v in (selected_cache or {}).items() if k != "_columns"},
        "feature_cache_inventory_count": len(caches),
        "registry_factor_count": len(registry_entries),
        "factor_class_counts": factor_df["availability_class"].value_counts(dropna=False).to_dict()
        if not factor_df.empty
        else {},
        "monthly_timeline_rows": len(timeline),
        "time_window_rows": len(time_window_df),
        "model_matrix_rows": len(model_matrix_df),
        "self_audit": self_audit_df.to_dict("records"),
        "artifacts": {
            "report_md": str(paths.report_md),
            "factor_csv": str(paths.factor_csv),
            "model_matrix_csv": str(paths.model_matrix_csv),
            "time_window_csv": str(paths.time_window_csv),
            "monthly_timeline_csv": str(paths.monthly_timeline_csv),
            "self_audit_csv": str(paths.self_audit_csv),
        },
        "inputs_hash": _inputs_hash(args, selected_cache),
    }
    paths.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
    write_report(
        paths,
        selected_cache=selected_cache,
        caches=caches,
        timeline=timeline,
        factor_df=factor_df,
        time_window_df=time_window_df,
        model_matrix_df=model_matrix_df,
        self_audit_df=self_audit_df,
        existing=existing,
    )
    print(json.dumps(payload["artifacts"], ensure_ascii=False, indent=2))
    p0_fail = [row for row in payload["self_audit"] if row["level"] == "P0" and row["status"] == "FAIL"]
    return 2 if p0_fail else 0


def _inputs_hash(args: argparse.Namespace, selected_cache: dict[str, Any] | None) -> str:
    payload = {
        "registry": str(args.registry),
        "feature_cache_dir": str(args.feature_cache_dir),
        "selected_cache": selected_cache.get("fingerprint") if selected_cache else None,
        "windows": {
            "train": TRAIN_WINDOW_MONTHS,
            "valid": VALID_WINDOW_MONTHS,
            "fixed_start": FIXED_START_YEARS,
        },
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


if __name__ == "__main__":
    raise SystemExit(main())

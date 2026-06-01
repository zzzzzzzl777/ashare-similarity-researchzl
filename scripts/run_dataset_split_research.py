"""Research the data window and split protocol for the 14:57 T+1 project.

This script is intentionally data-protocol only. It does not train a model, it
does not change the target, and it does not mutate live inference settings.

Outputs:
  - docs/dataset_split_research_report_<YYYYMMDD>.md
  - <report_dir>/prediction/dataset_split_research_<YYYYMMDD>.json
  - <report_dir>/prediction/dataset_split_manifest_<YYYYMMDD>.csv
  - <report_dir>/prediction/dataset_monthly_timeline_<YYYYMMDD>.csv
  - <report_dir>/prediction/dataset_feature_cache_inventory_<YYYYMMDD>.csv
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config


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

CLASS_C_COLUMNS = {
    "tushare_lg_buy_sell_ratio",
    "tushare_lg_buy_sell_ratio_available",
    "tushare_elg_buy_sell_ratio",
    "tushare_elg_buy_sell_ratio_available",
    "tushare_mf_strength",
    "tushare_mf_strength_available",
    "tushare_sm_sell_pressure",
    "tushare_sm_sell_pressure_available",
    "tushare_main_force_divergence",
    "tushare_main_force_divergence_available",
    "tushare_lhb_net_buy",
    "tushare_lhb_net_buy_available",
    "tushare_lhb_net_rate",
    "tushare_lhb_net_rate_available",
    "tushare_inst_buy_count",
    "tushare_inst_buy_count_available",
    "tushare_lhb_appeared",
    "tushare_lhb_appeared_available",
    "tushare_inst_net_buy",
    "tushare_inst_net_buy_available",
    "tushare_rzye",
    "tushare_rzye_available",
    "tushare_rzye_delta_pct",
    "tushare_rzye_delta_pct_available",
    "tushare_rzmre_ratio",
    "tushare_rzmre_ratio_available",
    "tushare_margin_net",
    "tushare_margin_net_available",
    "tushare_rqye_ratio",
    "tushare_rqye_ratio_available",
    "tushare_auction_close_vwap_ratio",
    "tushare_auction_close_vwap_ratio_available",
    "tushare_auction_close_vol",
    "tushare_auction_close_vol_available",
    "tushare_float_relative_impact",
    "tushare_float_relative_impact_available",
}

P0_CANONICAL_COLUMNS = {
    "sector_climax_signal",
    "sector_climax_signal_available",
    "sector_divergence",
    "sector_divergence_available",
    "sector_duration_days",
    "sector_duration_days_available",
    "sector_limit_up_count",
    "sector_limit_up_count_available",
    "sector_pct_change_best",
    "sector_pct_change_best_available",
    "sector_strength_rank",
    "sector_strength_rank_available",
    "tushare_cost_concentration",
    "tushare_cost_concentration_available",
    "tushare_cost_position",
    "tushare_cost_position_available",
    "tushare_winner_rate",
    "tushare_winner_rate_available",
    "tushare_net_mf_amount",
    "tushare_net_mf_amount_available",
    "tushare_ff_adjusted_flow",
    "tushare_ff_adjusted_flow_available",
}

FORBIDDEN_COLUMNS = CLASS_C_COLUMNS | P0_CANONICAL_COLUMNS

TRAIN_WINDOW_MONTHS = (12, 18, 24, 30, 36, 48, 60, 72)
VALID_WINDOW_MONTHS = (1, 2, 3, 6, 12)
FIXED_START_YEARS = (2017, 2018, 2019, 2020, 2021, 2022, 2023)
DEV_OUTER_START = pd.Timestamp("2024-01-01")
DEV_OUTER_END = pd.Timestamp("2025-12-31")
SEEN_RESEARCH_WINDOWS = (
    ("q1_2026_seen_research_test", pd.Timestamp("2026-01-01"), pd.Timestamp("2026-03-31")),
    ("april_2026_seen_research_test", pd.Timestamp("2026-04-01"), pd.Timestamp("2026-04-30")),
)
FINAL_FORWARD_START = pd.Timestamp("2026-05-01")
MIN_FIT_ROWS = 20_000
MIN_INNER_ROWS = 3_000
MIN_OUTER_ROWS = 3_000
DEFAULT_EMBARGO_DAYS = 1


@dataclass(frozen=True)
class OutputPaths:
    report_json: Path
    report_md: Path
    split_manifest_csv: Path
    monthly_timeline_csv: Path
    feature_cache_inventory_csv: Path
    raw_monthly_timeline_csv: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dataset split research artifacts for the A-share 14:57 T+1 project."
    )
    parser.add_argument("--feature-cache", type=Path, help="Use a specific feature cache parquet file.")
    parser.add_argument("--feature-cache-dir", type=Path, help="Override feature cache directory.")
    parser.add_argument("--raw-bars-dir", type=Path, help="Override raw daily bars directory.")
    parser.add_argument("--skip-raw-scan", action="store_true", help="Skip raw daily bars monthly audit.")
    parser.add_argument(
        "--max-raw-files",
        type=int,
        default=0,
        help="Optional cap for raw daily parquet files scanned; 0 means all files.",
    )
    parser.add_argument("--asof-date", default=None, help="YYYYMMDD suffix for output names; default today.")
    parser.add_argument("--embargo-days", type=int, default=DEFAULT_EMBARGO_DAYS)
    return parser.parse_args()


def json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        if math.isnan(float(value)):
            return None
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def month_floor(ts: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(year=ts.year, month=ts.month, day=1)


def month_end(ts: pd.Timestamp) -> pd.Timestamp:
    return month_floor(ts) + pd.offsets.MonthEnd(0)


def add_months(ts: pd.Timestamp, months: int) -> pd.Timestamp:
    return ts + pd.DateOffset(months=months)


def fmt_date(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(pd.Timestamp(value).date())


def ensure_outputs(config_report_dir: Path, asof: str) -> OutputPaths:
    prediction_dir = config_report_dir / "prediction"
    prediction_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = REPO_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    return OutputPaths(
        report_json=prediction_dir / f"dataset_split_research_{asof}.json",
        report_md=docs_dir / f"dataset_split_research_report_{asof}.md",
        split_manifest_csv=prediction_dir / f"dataset_split_manifest_{asof}.csv",
        monthly_timeline_csv=prediction_dir / f"dataset_monthly_timeline_{asof}.csv",
        feature_cache_inventory_csv=prediction_dir / f"dataset_feature_cache_inventory_{asof}.csv",
        raw_monthly_timeline_csv=prediction_dir / f"dataset_raw_daily_monthly_timeline_{asof}.csv",
    )


def read_schema_columns(path: Path) -> list[str]:
    return list(pq.read_schema(path).names)


def read_optional_columns(path: Path, wanted: list[str]) -> pd.DataFrame:
    schema = set(read_schema_columns(path))
    columns = [column for column in wanted if column in schema]
    if not columns:
        return pd.DataFrame()
    return pd.read_parquet(path, columns=columns)


def load_json_sidecar(path: Path) -> dict[str, Any]:
    sidecar = path.with_suffix(".json")
    if not sidecar.exists() and path.name.endswith("_t1shifted.parquet"):
        sidecar = path.with_name(path.name.replace("_t1shifted.parquet", "_t1shifted.json"))
    if not sidecar.exists():
        return {}
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception:
        return {}


def summarize_feature_cache(path: Path) -> dict[str, Any]:
    schema = read_schema_columns(path)
    meta = load_json_sidecar(path)
    probe = read_optional_columns(
        path,
        ["symbol", "date", "label_date", "actual", "next_high_return_pct", "limit_up_like"],
    )
    for column in ("date", "label_date"):
        if column in probe.columns:
            probe[column] = pd.to_datetime(probe[column], errors="coerce")
    if "actual" not in probe.columns and "next_high_return_pct" in probe.columns:
        probe["actual"] = (pd.to_numeric(probe["next_high_return_pct"], errors="coerce") >= 1.0).astype(float)
    if "limit_up_like" in probe.columns:
        pass_mask = pd.to_numeric(probe["limit_up_like"], errors="coerce").fillna(0.0) <= 0.5
    else:
        pass_mask = pd.Series(True, index=probe.index)

    feature_columns = [column for column in schema if column not in META_COLUMNS]
    forbidden_present = sorted(set(schema) & FORBIDDEN_COLUMNS)
    date_col = probe["date"] if "date" in probe.columns else pd.Series(dtype="datetime64[ns]")
    label_col = probe["label_date"] if "label_date" in probe.columns else pd.Series(dtype="datetime64[ns]")
    summary = {
        "path": str(path),
        "name": path.name,
        "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "bytes": int(path.stat().st_size),
        "rows": int(len(probe)) if len(probe) else int(meta.get("rows") or 0),
        "schema_columns": int(len(schema)),
        "feature_columns": int(len(feature_columns)),
        "date_min": fmt_date(date_col.min()) if len(date_col) else "",
        "date_max": fmt_date(date_col.max()) if len(date_col) else "",
        "label_min": fmt_date(label_col.min()) if len(label_col) else "",
        "label_max": fmt_date(label_col.max()) if len(label_col) else "",
        "symbols": int(probe["symbol"].nunique()) if "symbol" in probe.columns else 0,
        "filtered_rows": int(pass_mask.sum()) if len(probe) else 0,
        "positive_rate": float(pd.to_numeric(probe["actual"], errors="coerce").mean())
        if "actual" in probe.columns and len(probe)
        else None,
        "t1_shifted": "_t1shifted" in path.stem or bool(meta.get("source_cache")),
        "fingerprint": str(meta.get("fingerprint") or path.stem.replace("gpu_probe_features_", "")),
        "forbidden_present_count": len(forbidden_present),
        "forbidden_present_sample": forbidden_present[:20],
        "sidecar_json": str(path.with_suffix(".json")) if path.with_suffix(".json").exists() else "",
    }
    return summary


def discover_feature_caches(feature_cache_dir: Path) -> list[dict[str, Any]]:
    paths = sorted(feature_cache_dir.glob("*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True)
    candidates = [
        path
        for path in paths
        if path.name.startswith(("gpu_probe_features_", "pretrain_", "jan_2023"))
        and "realtime_1457" not in path.name
    ]
    summaries: list[dict[str, Any]] = []
    for path in candidates:
        try:
            summaries.append(summarize_feature_cache(path))
        except Exception as exc:
            summaries.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "error": str(exc),
                    "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                }
            )
    return summaries


def choose_analysis_cache(inventory: list[dict[str, Any]], explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.exists():
            raise FileNotFoundError(f"Feature cache does not exist: {explicit}")
        return explicit

    usable = [item for item in inventory if item.get("rows") and item.get("date_max")]
    if not usable:
        raise FileNotFoundError("No usable feature cache parquet files found.")

    def score(item: dict[str, Any]) -> tuple[int, str, int, str]:
        date_max = str(item.get("date_max") or "")
        label_max = str(item.get("label_max") or "")
        covers_april = int(date_max >= "2026-04-29" or label_max >= "2026-04-30")
        t1 = int(bool(item.get("t1_shifted")))
        cols = int(item.get("schema_columns") or 0)
        mtime = str(item.get("mtime") or "")
        return (covers_april * 10_000 + t1 * 1_000 + cols, date_max, int(item.get("rows") or 0), mtime)

    return Path(max(usable, key=score)["path"])


def load_protocol_frame(path: Path) -> pd.DataFrame:
    columns = ["symbol", "date", "label_date", "actual", "next_high_return_pct", "limit_up_like"]
    frame = read_optional_columns(path, columns)
    if frame.empty:
        raise ValueError(f"Feature cache has no protocol columns: {path}")
    for column in ("date", "label_date"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    frame = frame.dropna(subset=["date", "label_date", "symbol"]).copy()
    frame = frame.sort_values(["symbol", "date", "label_date"]).drop_duplicates(["symbol", "date"], keep="first")
    if "actual" not in frame.columns and "next_high_return_pct" in frame.columns:
        frame["actual"] = (pd.to_numeric(frame["next_high_return_pct"], errors="coerce") >= 1.0).astype(float)
    if "limit_up_like" not in frame.columns:
        frame["limit_up_like"] = 0.0
    frame["_filter_pass"] = pd.to_numeric(frame["limit_up_like"], errors="coerce").fillna(0.0) <= 0.5
    frame["_actual"] = pd.to_numeric(frame["actual"], errors="coerce") if "actual" in frame.columns else np.nan
    frame["_label_month"] = frame["label_date"].dt.to_period("M").astype(str)
    frame["_event_month"] = frame["date"].dt.to_period("M").astype(str)
    return frame


def monthly_feature_timeline(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month, group in frame.groupby("_label_month", sort=True):
        filtered = group[group["_filter_pass"]]
        rows.append(
            {
                "month": month,
                "role_hint": role_for_month(month),
                "rows": int(len(group)),
                "filtered_rows": int(len(filtered)),
                "filtered_pct": round(float(len(filtered) / len(group)), 6) if len(group) else 0.0,
                "event_days": int(group["date"].nunique()),
                "label_days": int(group["label_date"].nunique()),
                "symbols": int(group["symbol"].nunique()),
                "positive_rate": round(float(group["_actual"].mean()), 6)
                if group["_actual"].notna().any()
                else None,
                "filtered_positive_rate": round(float(filtered["_actual"].mean()), 6)
                if len(filtered) and filtered["_actual"].notna().any()
                else None,
                "event_date_min": fmt_date(group["date"].min()),
                "event_date_max": fmt_date(group["date"].max()),
                "label_date_min": fmt_date(group["label_date"].min()),
                "label_date_max": fmt_date(group["label_date"].max()),
            }
        )
    return pd.DataFrame(rows)


def role_for_month(month: str) -> str:
    ts = pd.Timestamp(f"{month}-01")
    if ts <= DEV_OUTER_END:
        return "dev_pool_candidate"
    if pd.Timestamp("2026-01-01") <= ts <= pd.Timestamp("2026-04-01"):
        return "seen_research_test"
    if ts >= FINAL_FORWARD_START:
        return "final_forward_future"
    return "gap_or_unknown"


def scan_raw_daily_bars(raw_dir: Path, max_files: int = 0) -> tuple[pd.DataFrame, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"raw_rows": 0, "symbols": set(), "days": set()})
    paths = sorted(raw_dir.glob("*.parquet"))
    if max_files > 0:
        paths = paths[:max_files]
    errors = []
    for idx, path in enumerate(paths, start=1):
        try:
            schema = set(read_schema_columns(path))
            columns = [column for column in ("date", "symbol") if column in schema]
            if "date" not in columns:
                continue
            frame = pd.read_parquet(path, columns=columns)
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
            frame = frame.dropna(subset=["date"])
            frame = frame[(frame["date"] >= "2020-01-01") & (frame["date"] <= "2026-04-30")]
            if frame.empty:
                continue
            if "symbol" not in frame.columns:
                frame["symbol"] = path.stem
            frame["_month"] = frame["date"].dt.to_period("M").astype(str)
            for month, group in frame.groupby("_month"):
                bucket = stats[month]
                bucket["raw_rows"] += int(len(group))
                bucket["symbols"].update(str(value) for value in group["symbol"].dropna().unique())
                bucket["days"].update(str(value.date()) for value in group["date"].dropna().unique())
        except Exception as exc:
            if len(errors) < 20:
                errors.append({"path": str(path), "error": str(exc)})
        if idx % 500 == 0:
            print(f"  raw scan: {idx:,}/{len(paths):,} files")

    rows = []
    for month in sorted(stats):
        bucket = stats[month]
        rows.append(
            {
                "month": month,
                "raw_rows": int(bucket["raw_rows"]),
                "raw_symbols": int(len(bucket["symbols"])),
                "raw_days": int(len(bucket["days"])),
            }
        )
    meta = {"raw_dir": str(raw_dir), "files_scanned": len(paths), "errors": errors}
    return pd.DataFrame(rows), meta


def infer_max_lookback_days(feature_columns: list[str]) -> dict[str, Any]:
    pattern_values: list[int] = []
    examples: dict[int, str] = {}
    patterns = [
        re.compile(r"(?:^|_)(\d+)(?:d|D)(?:_|$)"),
        re.compile(r"(?:^|_)(\d+)$"),
    ]
    ignore_names = {"day_of_week_sin", "day_of_week_cos"}
    for column in feature_columns:
        if column in ignore_names or column.endswith("_available"):
            continue
        for pattern in patterns:
            for match in pattern.finditer(column):
                value = int(match.group(1))
                if 2 <= value <= 250:
                    pattern_values.append(value)
                    examples.setdefault(value, column)
    max_value = max(pattern_values) if pattern_values else 0
    return {
        "max_lookback_hint": max_value,
        "max_lookback_example": examples.get(max_value, ""),
        "lookback_values": sorted(set(pattern_values)),
        "note": "Regex-based hint from feature names; confirm with feature builders before rebuilding older caches.",
    }


def segment_stats(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    if start is None or end is None or pd.isna(start) or pd.isna(end) or start > end:
        return empty_segment_stats()
    mask = (frame["label_date"] >= start) & (frame["label_date"] <= end)
    group = frame[mask]
    filtered = group[group["_filter_pass"]]
    return {
        "rows": int(len(group)),
        "filtered_rows": int(len(filtered)),
        "label_days": int(group["label_date"].nunique()),
        "event_days": int(group["date"].nunique()),
        "symbols": int(group["symbol"].nunique()),
        "positive_rate": round(float(group["_actual"].mean()), 6)
        if len(group) and group["_actual"].notna().any()
        else None,
        "filtered_positive_rate": round(float(filtered["_actual"].mean()), 6)
        if len(filtered) and filtered["_actual"].notna().any()
        else None,
    }


def empty_segment_stats() -> dict[str, Any]:
    return {
        "rows": 0,
        "filtered_rows": 0,
        "label_days": 0,
        "event_days": 0,
        "symbols": 0,
        "positive_rate": None,
        "filtered_positive_rate": None,
    }


def split_windows(start: pd.Timestamp, end: pd.Timestamp, months: int) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    windows = []
    cursor = month_floor(start)
    while cursor <= end:
        valid_end = min(add_months(cursor, months) - pd.Timedelta(days=1), end)
        windows.append((cursor, valid_end))
        cursor = add_months(cursor, months)
    return windows


def build_split_manifest(
    frame: pd.DataFrame,
    fair_start: pd.Timestamp,
    *,
    embargo_days: int,
) -> pd.DataFrame:
    rows = []
    available_min = pd.Timestamp(frame["label_date"].min()).normalize()
    available_max = pd.Timestamp(frame["label_date"].max()).normalize()

    schemes: list[dict[str, Any]] = []
    for months in TRAIN_WINDOW_MONTHS:
        schemes.append({"scheme": f"fixed_recent_{months}m", "kind": "fixed_recent", "months": months})
    schemes.append({"scheme": "expanding_from_fair_start", "kind": "expanding", "months": None})
    for year in FIXED_START_YEARS:
        schemes.append({"scheme": f"fixed_start_{year}", "kind": "fixed_start", "year": year})

    for valid_months in VALID_WINDOW_MONTHS:
        inner_months = min(3, max(1, valid_months))
        for outer_idx, (outer_start, outer_end) in enumerate(split_windows(DEV_OUTER_START, DEV_OUTER_END, valid_months), start=1):
            if outer_start > available_max:
                continue
            outer_end = min(outer_end, available_max, DEV_OUTER_END)
            outer_pre_start = outer_start - pd.Timedelta(days=embargo_days)
            inner_valid_end = outer_pre_start
            inner_valid_start = add_months(month_floor(outer_start), -inner_months)
            fit_train_end = inner_valid_start - pd.Timedelta(days=embargo_days)

            for scheme in schemes:
                if scheme["kind"] == "fixed_recent":
                    requested_dev_start = add_months(month_floor(outer_start), -int(scheme["months"]))
                elif scheme["kind"] == "fixed_start":
                    requested_dev_start = pd.Timestamp(f"{scheme['year']}-01-01")
                else:
                    requested_dev_start = fair_start
                effective_dev_start = max(requested_dev_start, fair_start, available_min)
                history_truncated = effective_dev_start > requested_dev_start
                fit_train_start = effective_dev_start

                fit_stats = segment_stats(frame, fit_train_start, fit_train_end)
                inner_stats = segment_stats(frame, inner_valid_start, inner_valid_end)
                outer_stats = segment_stats(frame, outer_start, outer_end)
                eligible = (
                    fit_stats["filtered_rows"] >= MIN_FIT_ROWS
                    and inner_stats["filtered_rows"] >= MIN_INNER_ROWS
                    and outer_stats["filtered_rows"] >= MIN_OUTER_ROWS
                    and fit_train_start <= fit_train_end
                    and inner_valid_start <= inner_valid_end
                    and outer_start <= outer_end
                    and not history_truncated
                )
                reason = []
                if history_truncated:
                    reason.append("requested_history_before_cache_start")
                if fit_stats["filtered_rows"] < MIN_FIT_ROWS:
                    reason.append("fit_rows_below_min")
                if inner_stats["filtered_rows"] < MIN_INNER_ROWS:
                    reason.append("inner_rows_below_min")
                if outer_stats["filtered_rows"] < MIN_OUTER_ROWS:
                    reason.append("outer_rows_below_min")
                if fit_train_start > fit_train_end:
                    reason.append("fit_window_empty")
                if inner_valid_start > inner_valid_end:
                    reason.append("inner_window_empty")

                rows.append(
                    {
                        "scheme": scheme["scheme"],
                        "scheme_kind": scheme["kind"],
                        "train_window_months": scheme.get("months"),
                        "outer_valid_months": valid_months,
                        "inner_valid_months": inner_months,
                        "outer_fold": outer_idx,
                        "requested_dev_start": fmt_date(requested_dev_start),
                        "effective_dev_start": fmt_date(effective_dev_start),
                        "history_truncated_by_cache": bool(history_truncated),
                        "fit_train_start": fmt_date(fit_train_start),
                        "fit_train_end": fmt_date(fit_train_end),
                        "inner_valid_start": fmt_date(inner_valid_start),
                        "inner_valid_end": fmt_date(inner_valid_end),
                        "outer_valid_start": fmt_date(outer_start),
                        "outer_valid_end": fmt_date(outer_end),
                        "embargo_days": embargo_days,
                        "fit_rows": fit_stats["rows"],
                        "fit_filtered_rows": fit_stats["filtered_rows"],
                        "fit_label_days": fit_stats["label_days"],
                        "fit_symbols": fit_stats["symbols"],
                        "fit_positive_rate": fit_stats["filtered_positive_rate"],
                        "inner_rows": inner_stats["rows"],
                        "inner_filtered_rows": inner_stats["filtered_rows"],
                        "inner_label_days": inner_stats["label_days"],
                        "inner_symbols": inner_stats["symbols"],
                        "inner_positive_rate": inner_stats["filtered_positive_rate"],
                        "outer_rows": outer_stats["rows"],
                        "outer_filtered_rows": outer_stats["filtered_rows"],
                        "outer_label_days": outer_stats["label_days"],
                        "outer_symbols": outer_stats["symbols"],
                        "outer_positive_rate": outer_stats["filtered_positive_rate"],
                        "eligible_for_protocol": bool(eligible),
                        "ineligibility_reason": ";".join(reason),
                    }
                )
    return pd.DataFrame(rows)


def build_role_manifest(frame: pd.DataFrame) -> list[dict[str, Any]]:
    roles = []
    dev_pool = segment_stats(frame, pd.Timestamp("1900-01-01"), DEV_OUTER_END)
    roles.append(
        {
            "role": "development_pool",
            "start": fmt_date(frame["label_date"].min()),
            "end": fmt_date(min(pd.Timestamp(frame["label_date"].max()), DEV_OUTER_END)),
            **dev_pool,
            "usage": "fit_train, inner_valid, and outer_valid candidates only.",
        }
    )
    for role, start, end in SEEN_RESEARCH_WINDOWS:
        roles.append(
            {
                "role": role,
                "start": fmt_date(start),
                "end": fmt_date(end),
                **segment_stats(frame, start, end),
                "usage": "Seen research test only; never final acceptance.",
            }
        )
    roles.append(
        {
            "role": "final_forward",
            "start": fmt_date(FINAL_FORWARD_START),
            "end": "",
            **empty_segment_stats(),
            "usage": "Future unseen months after protocol freeze.",
        }
    )
    return roles


def current_protocol_summary(frame: pd.DataFrame) -> dict[str, Any]:
    fit = segment_stats(frame, pd.Timestamp("1900-01-01"), pd.Timestamp("2025-06-30"))
    valid = segment_stats(frame, pd.Timestamp("2025-07-01"), pd.Timestamp("2025-12-31"))
    q1 = segment_stats(frame, pd.Timestamp("2026-01-01"), pd.Timestamp("2026-03-31"))
    april = segment_stats(frame, pd.Timestamp("2026-04-01"), pd.Timestamp("2026-04-30"))
    return {
        "current_official_shape": "fit through 2025-06-30, dev_valid 2025-07-01 to 2025-12-31, Q1/April seen research.",
        "fit_train_to_2025_06": fit,
        "dev_valid_2025_h2": valid,
        "q1_2026_seen": q1,
        "april_2026_seen": april,
        "risk": "A single 2025H2 tail validation has many rows but only one contiguous market regime.",
    }


def load_existing_result_context(report_dir: Path) -> dict[str, Any]:
    prediction_dir = report_dir / "prediction"

    def read_json(name: str) -> dict[str, Any]:
        path = prediction_dir / name
        if not path.exists():
            return {"path": str(path), "exists": False}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"path": str(path), "exists": True, "error": str(exc)}
        payload["_path"] = str(path)
        return payload

    phase_c = read_json("phaseC_hpo_internal_cv_20260509.json")
    u95_rolling = read_json("u95_live_strict_optuna_rolling_summary_20260508.json")
    phase_e = read_json("phaseE_frozen_april_20260509.json")
    rebuild = read_json("u95_live_strict_rebuild_final_decision_20260509.json")

    phase_c_summary: dict[str, Any] = {"source": phase_c.get("_path") or phase_c.get("path"), "exists": bool(phase_c.get("_path"))}
    if phase_c_summary["exists"]:
        winner = phase_c.get("hpo_winner") or {}
        variants = phase_c.get("variants") or []
        winner_variant = next((item for item in variants if item.get("variant_name") == winner.get("config")), {})
        q1 = phase_c.get("q1_report_winner_only") or {}
        phase_c_summary.update(
            {
                "methodology": phase_c.get("methodology"),
                "folds": phase_c.get("cv_folds"),
                "winner": winner,
                "winner_fold_w95s": winner_variant.get("fold_w95s"),
                "winner_min_cv_w95": winner_variant.get("min_cv_w95"),
                "q1_winner_seen_w95": q1.get("q1_wilson_95"),
                "q1_winner_seen_count": q1.get("q1_hc_count"),
            }
        )

    u95_summary: dict[str, Any] = {
        "source": u95_rolling.get("_path") or u95_rolling.get("path"),
        "exists": bool(u95_rolling.get("_path")),
    }
    if u95_summary["exists"]:
        rolling = u95_rolling.get("rolling_cv_metrics") or {}
        u95_summary.update(
            {
                "conclusion": u95_rolling.get("conclusion"),
                "rolling_w95_per_fold": rolling.get("wilson_075_per_fold"),
                "rolling_w95_min": rolling.get("wilson_075_min"),
                "rolling_w95_std": rolling.get("wilson_075_std"),
                "q1_external": u95_rolling.get("q1_external_validation"),
                "april_holdout": u95_rolling.get("april_holdout"),
            }
        )

    phase_e_summary: dict[str, Any] = {"source": phase_e.get("_path") or phase_e.get("path"), "exists": bool(phase_e.get("_path"))}
    if phase_e_summary["exists"]:
        april = phase_e.get("april_holdout") or {}
        threshold_rows = april.get("multi_threshold_results") or []
        p075 = next((item for item in threshold_rows if float(item.get("threshold", -1)) == 0.75), None)
        phase_e_summary.update(
            {
                "methodology": phase_e.get("methodology"),
                "stability_grade": phase_e.get("stability_grade"),
                "bundle_threshold_result": april.get("bundle_threshold_result"),
                "p075_april_result": p075,
                "final_decision": phase_e.get("final_decision"),
            }
        )

    rebuild_summary: dict[str, Any] = {"source": rebuild.get("_path") or rebuild.get("path"), "exists": bool(rebuild.get("_path"))}
    if rebuild_summary["exists"]:
        rebuild_summary.update(
            {
                "verdict": rebuild.get("verdict"),
                "candidate_bundle": rebuild.get("candidate_bundle"),
                "external_validation": rebuild.get("external_validation"),
            }
        )

    return {
        "phase_c_internal_cv": phase_c_summary,
        "u95_rolling_cv": u95_summary,
        "phase_e_april": phase_e_summary,
        "u95_rebuild_external": rebuild_summary,
        "interpretation": [
            "Phase C half-year folds and U95 bimonthly folds both show large fold-to-fold variation.",
            "Q1 and April results are useful consistency checks, but both are now seen research windows.",
            "Internal split selection should be decided before looking at new final_forward months.",
        ],
    }


def metric_contract() -> dict[str, Any]:
    return {
        "primary": ["wilson_95_lower_at_p075", "accuracy_at_p075", "count_at_p075", "coverage_at_p075"],
        "trading": ["daily_top3_wilson", "daily_top5_wilson", "daily_top10_wilson", "active_days", "max_single_day_share"],
        "stability": ["min_outer_window_w95", "outer_window_std", "worst_window", "q1_april_decay_seen_only"],
        "calibration": ["brier", "probability_bucket_monotonicity", "raw_vs_isotonic_unique_score_count"],
        "engineering": ["selected_feature_forbidden_count", "selected_feature_live_available_count", "schema_match"],
        "note": "These metrics are the contract for the optional fixed-model split comparison stage.",
    }


def summarize_manifest(manifest: pd.DataFrame) -> dict[str, Any]:
    if manifest.empty:
        return {}
    grouped = (
        manifest.groupby(["scheme", "outer_valid_months"], dropna=False)
        .agg(
            folds=("outer_fold", "count"),
            eligible_folds=("eligible_for_protocol", "sum"),
            min_fit_rows=("fit_filtered_rows", "min"),
            median_fit_rows=("fit_filtered_rows", "median"),
            min_outer_rows=("outer_filtered_rows", "min"),
            median_outer_rows=("outer_filtered_rows", "median"),
            min_inner_rows=("inner_filtered_rows", "min"),
            median_inner_rows=("inner_filtered_rows", "median"),
        )
        .reset_index()
    )
    full = grouped[grouped["folds"] == grouped["eligible_folds"]].copy()
    partial = grouped[(grouped["eligible_folds"] > 0) & (grouped["folds"] != grouped["eligible_folds"])].copy()
    return {
        "total_candidate_rows": int(len(manifest)),
        "eligible_candidate_rows": int(manifest["eligible_for_protocol"].sum()),
        "fully_eligible_scheme_lengths": full.to_dict(orient="records"),
        "partially_eligible_scheme_lengths": partial.to_dict(orient="records"),
    }


def recommendations(
    frame: pd.DataFrame,
    manifest_summary: dict[str, Any],
    lookback: dict[str, Any],
) -> list[str]:
    fair_start = fmt_date(frame["label_date"].min())
    label_max = fmt_date(frame["label_date"].max())
    fully = manifest_summary.get("fully_eligible_scheme_lengths") or []
    full_names = {(item["scheme"], int(item["outer_valid_months"])) for item in fully}
    recs = [
        f"Current complete feature evidence starts at label_date {fair_start} and ends at {label_max}.",
        "Use nested time splits: fit_train -> inner_valid -> outer_valid; never calibrate on outer_valid.",
        "Use 3-month outer validation as the main comparison unit; keep 1/2-month windows as drift diagnostics and 6/12-month windows as stability summaries.",
        "Keep Q1 2026 and April 2026 as seen_research_test only; the next clean final_forward must start after the data protocol is frozen.",
    ]
    if ("expanding_from_fair_start", 3) in full_names:
        recs.append("With the current cache, the fully fair quarterly protocol is expanding-from-current-cache-start.")
    if ("fixed_recent_24m", 3) in full_names or ("fixed_recent_30m", 3) in full_names:
        recs.append("With the current cache, 24m/30m recent-window quarterly CV is directly testable across all folds.")
    else:
        recs.append("The current cache is too short for a clean 24m/30m quarterly protocol across all 2024-2025 folds; rebuild older features before judging longer windows.")
    if not any(str(item.get("scheme", "")).startswith("fixed_start_2022") for item in fully):
        recs.append("Do not claim 2022/2021/2020 start windows are better until a same-schema historical feature cache is rebuilt and audited.")
    if int(lookback.get("max_lookback_hint") or 0) >= 120:
        recs.append("Historical rebuilds should include at least 120 trading days of warmup before the first intended train label month.")
    return recs


def write_report(
    paths: OutputPaths,
    payload: dict[str, Any],
    monthly: pd.DataFrame,
    manifest: pd.DataFrame,
    cache_inventory: pd.DataFrame,
) -> None:
    selected = payload["selected_feature_cache"]
    current = payload["current_protocol_summary"]
    manifest_summary = payload["split_manifest_summary"]
    recs = payload["recommendations"]
    roles = payload["role_manifest"]

    lines: list[str] = []
    lines.append(f"# Dataset Split Research Report - {payload['asof']}")
    lines.append("")
    lines.append("## Executive Decision")
    lines.append("")
    for rec in recs:
        lines.append(f"- {rec}")
    lines.append("")
    lines.append("## Selected Evidence Cache")
    lines.append("")
    lines.append(f"- Cache: `{selected['path']}`")
    lines.append(f"- Rows: {selected['rows']:,}; columns: {selected['schema_columns']:,}; features: {selected['feature_columns']:,}")
    lines.append(f"- Event dates: {selected['date_min']} to {selected['date_max']}")
    lines.append(f"- Label dates: {selected['label_min']} to {selected['label_max']}")
    lines.append(f"- T-1 shifted: {selected['t1_shifted']}")
    lines.append(f"- Forbidden/P0/Class-C columns present in superset: {selected['forbidden_present_count']} (must be excluded during training)")
    lines.append("")
    lines.append("## Current Protocol Check")
    lines.append("")
    lines.append(f"- Current shape: {current['current_official_shape']}")
    lines.append(f"- Fit to 2025-06 filtered rows: {current['fit_train_to_2025_06']['filtered_rows']:,}")
    lines.append(f"- 2025H2 dev_valid filtered rows: {current['dev_valid_2025_h2']['filtered_rows']:,}")
    lines.append(f"- Q1 2026 seen filtered rows: {current['q1_2026_seen']['filtered_rows']:,}")
    lines.append(f"- April 2026 seen filtered rows: {current['april_2026_seen']['filtered_rows']:,}")
    lines.append(f"- Risk: {current['risk']}")
    lines.append("")
    lines.append("## Existing Result Context")
    lines.append("")
    context = payload.get("existing_result_context") or {}
    phase_c = context.get("phase_c_internal_cv") or {}
    if phase_c.get("exists"):
        lines.append(
            f"- Phase C internal CV winner: {phase_c.get('winner', {}).get('config')} "
            f"with fold W95s {phase_c.get('winner_fold_w95s')}."
        )
        lines.append(
            f"- Phase C Q1 winner-only seen report: W95={phase_c.get('q1_winner_seen_w95')}, "
            f"count={phase_c.get('q1_winner_seen_count')}."
        )
    u95 = context.get("u95_rolling_cv") or {}
    if u95.get("exists"):
        lines.append(
            f"- U95 rolling CV W95 folds: {u95.get('rolling_w95_per_fold')} "
            f"(min={u95.get('rolling_w95_min')}, std={u95.get('rolling_w95_std')})."
        )
    phase_e = context.get("phase_e_april") or {}
    if phase_e.get("exists"):
        p075 = phase_e.get("p075_april_result") or {}
        if p075:
            lines.append(
                f"- Phase E frozen April p>=0.75: W95={p075.get('wilson_95')}, "
                f"accuracy={p075.get('accuracy')}, count={p075.get('count')}."
            )
    rebuild = context.get("u95_rebuild_external") or {}
    if rebuild.get("exists"):
        external = rebuild.get("external_validation") or {}
        q1 = ((external.get("q1_2026") or {}).get("rebuild_t22") or {})
        apr = ((external.get("april_2026") or {}).get("rebuild_t22") or {})
        if q1 or apr:
            lines.append(
                f"- U95 rebuild seen checks: Q1 W95={q1.get('wilson_075')}, "
                f"April W95={apr.get('wilson_075')}; still not final-unseen."
            )
    for item in context.get("interpretation") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Metric Contract")
    lines.append("")
    metrics = payload.get("metric_contract") or {}
    lines.append(f"- Primary: {', '.join(metrics.get('primary') or [])}")
    lines.append(f"- Trading: {', '.join(metrics.get('trading') or [])}")
    lines.append(f"- Stability: {', '.join(metrics.get('stability') or [])}")
    lines.append(f"- Calibration: {', '.join(metrics.get('calibration') or [])}")
    lines.append(f"- Engineering: {', '.join(metrics.get('engineering') or [])}")
    lines.append("")
    lines.append("## Data Roles")
    lines.append("")
    lines.append("| Role | Start | End | Filtered Rows | Usage |")
    lines.append("|---|---:|---:|---:|---|")
    for role in roles:
        lines.append(
            f"| {role['role']} | {role['start']} | {role['end']} | {role['filtered_rows']:,} | {role['usage']} |"
        )
    lines.append("")
    lines.append("## Split Manifest Summary")
    lines.append("")
    lines.append(f"- Candidate split rows: {manifest_summary.get('total_candidate_rows', 0):,}")
    lines.append(f"- Eligible split rows: {manifest_summary.get('eligible_candidate_rows', 0):,}")
    full = pd.DataFrame(manifest_summary.get("fully_eligible_scheme_lengths") or [])
    if not full.empty:
        lines.append("")
        lines.append("Fully eligible scheme/outer-window pairs under the current cache:")
        lines.append("")
        lines.append("| Scheme | Outer Valid Months | Folds | Min Fit Rows | Min Inner Rows | Min Outer Rows |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for _, row in full.sort_values(["outer_valid_months", "scheme"]).iterrows():
            lines.append(
                f"| {row['scheme']} | {int(row['outer_valid_months'])} | {int(row['folds'])} | "
                f"{int(row['min_fit_rows']):,} | {int(row['min_inner_rows']):,} | {int(row['min_outer_rows']):,} |"
            )
    partial = pd.DataFrame(manifest_summary.get("partially_eligible_scheme_lengths") or [])
    if not partial.empty:
        lines.append("")
        lines.append("Partially eligible pairs are useful diagnostics only; they cannot prove the full requested window.")
        lines.append("")
        lines.append("| Scheme | Outer Valid Months | Eligible Folds | Total Folds |")
        lines.append("|---|---:|---:|---:|")
        for _, row in partial.sort_values(["outer_valid_months", "scheme"]).iterrows():
            lines.append(
                f"| {row['scheme']} | {int(row['outer_valid_months'])} | "
                f"{int(row['eligible_folds'])} | {int(row['folds'])} |"
            )
    lines.append("")
    lines.append("## Monthly Timeline Snapshot")
    lines.append("")
    tail = monthly.tail(10)
    lines.append("| Month | Role | Filtered Rows | Label Days | Symbols | Filtered Positive Rate |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for _, row in tail.iterrows():
        pos = "" if pd.isna(row["filtered_positive_rate"]) else f"{float(row['filtered_positive_rate']):.4f}"
        lines.append(
            f"| {row['month']} | {row['role_hint']} | {int(row['filtered_rows']):,} | "
            f"{int(row['label_days'])} | {int(row['symbols']):,} | {pos} |"
        )
    lines.append("")
    lines.append("## Lookback / Rebuild Note")
    lines.append("")
    lookback = payload["lookback_hint"]
    lines.append(
        f"- Max feature-name lookback hint: {lookback['max_lookback_hint']} "
        f"from `{lookback['max_lookback_example']}`."
    )
    lines.append("- This is a regex hint, not a substitute for auditing each feature builder.")
    lines.append("- If researching 2022/2021/2020 starts, rebuild the feature cache with the same 14:57-safe schema and enough warmup before the first label month.")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- JSON: `{paths.report_json}`")
    lines.append(f"- Split manifest CSV: `{paths.split_manifest_csv}`")
    lines.append(f"- Monthly timeline CSV: `{paths.monthly_timeline_csv}`")
    lines.append(f"- Feature cache inventory CSV: `{paths.feature_cache_inventory_csv}`")
    if paths.raw_monthly_timeline_csv.exists():
        lines.append(f"- Raw daily monthly timeline CSV: `{paths.raw_monthly_timeline_csv}`")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- No model training was run by this script.")
    lines.append("- No target definition or live interface was changed.")
    lines.append("- Q1/April are recorded as seen research only.")

    paths.report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    config = get_default_config()
    asof = args.asof_date or datetime.now().strftime("%Y%m%d")
    feature_cache_dir = args.feature_cache_dir or (config.storage.report_dir / "prediction" / "feature_cache")
    raw_bars_dir = args.raw_bars_dir or (config.storage.raw_dir / "bars" / "daily")
    paths = ensure_outputs(config.storage.report_dir, asof)

    print(f"Discovering feature caches in {feature_cache_dir}")
    inventory = discover_feature_caches(feature_cache_dir)
    cache_inventory = pd.DataFrame(inventory)
    cache_inventory.to_csv(paths.feature_cache_inventory_csv, index=False, encoding="utf-8-sig")

    analysis_cache = choose_analysis_cache(inventory, args.feature_cache)
    print(f"Selected analysis cache: {analysis_cache}")
    selected_summary = summarize_feature_cache(analysis_cache)
    frame = load_protocol_frame(analysis_cache)
    print(f"Protocol frame: {len(frame):,} rows after symbol/date dedup")

    monthly = monthly_feature_timeline(frame)
    monthly.to_csv(paths.monthly_timeline_csv, index=False, encoding="utf-8-sig")

    raw_meta: dict[str, Any] = {"skipped": True}
    raw_monthly = pd.DataFrame()
    if not args.skip_raw_scan:
        print(f"Scanning raw daily bars in {raw_bars_dir}")
        raw_monthly, raw_meta = scan_raw_daily_bars(raw_bars_dir, args.max_raw_files)
        raw_monthly.to_csv(paths.raw_monthly_timeline_csv, index=False, encoding="utf-8-sig")

    schema_columns = read_schema_columns(analysis_cache)
    feature_columns = [column for column in schema_columns if column not in META_COLUMNS]
    fair_start = pd.Timestamp(frame["label_date"].min()).normalize()
    manifest = build_split_manifest(frame, fair_start, embargo_days=max(0, int(args.embargo_days)))
    manifest.to_csv(paths.split_manifest_csv, index=False, encoding="utf-8-sig")

    lookback = infer_max_lookback_days(feature_columns)
    manifest_summary = summarize_manifest(manifest)
    payload = {
        "asof": asof,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "dataset_split_protocol_research_for_1457_t1_high_confidence_signals",
        "selected_feature_cache": selected_summary,
        "feature_cache_inventory_rows": len(cache_inventory),
        "monthly_timeline_rows": len(monthly),
        "raw_daily_scan": raw_meta,
        "raw_monthly_timeline_rows": len(raw_monthly),
        "role_manifest": build_role_manifest(frame),
        "current_protocol_summary": current_protocol_summary(frame),
        "existing_result_context": load_existing_result_context(config.storage.report_dir),
        "metric_contract": metric_contract(),
        "lookback_hint": lookback,
        "split_manifest_summary": manifest_summary,
        "recommendations": recommendations(frame, manifest_summary, lookback),
        "output_paths": {
            "report_md": str(paths.report_md),
            "report_json": str(paths.report_json),
            "split_manifest_csv": str(paths.split_manifest_csv),
            "monthly_timeline_csv": str(paths.monthly_timeline_csv),
            "feature_cache_inventory_csv": str(paths.feature_cache_inventory_csv),
            "raw_monthly_timeline_csv": str(paths.raw_monthly_timeline_csv),
        },
        "guardrails": {
            "model_training_run": False,
            "target_definition_changed": False,
            "live_interface_changed": False,
            "q1_april_role": "seen_research_test",
            "split_key": "label_date",
            "random_split_allowed": False,
        },
    }

    paths.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
    write_report(paths, payload, monthly, manifest, cache_inventory)

    print(f"Wrote report: {paths.report_md}")
    print(f"Wrote JSON: {paths.report_json}")
    print(f"Wrote split manifest: {paths.split_manifest_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

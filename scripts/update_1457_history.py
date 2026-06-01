#!/usr/bin/env python
"""Update rolling 14:57 post-close candidate history.

This script keeps the dashboard history current after each trading day:

1. Start from the reviewed baseline history CSV.
2. Add the latest saved valid post-close selector CSV for each trading day.
   If a day has no valid post-close selector, fall back to its saved valid
   formal 14:57 selector.
3. Recompute next-trading-day verification from daily bars when available.
4. Write one rolling CSV that the Web UI can read.

It intentionally ignores test/replay outputs. Post-close rows take precedence
over formal rows for the same day.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


RUNTIME_ROOT = Path(
    os.environ.get(
        "ASHARE_SIMILARITY_RUNTIME_DATA",
        os.environ.get("ASHARE_SIMILARITY_DATA", "E:/ashare_similarity_runtime/data"),
    )
).resolve()
PREDICTION_DIR = RUNTIME_ROOT / "reports" / "prediction"
HISTORY_DIR = PREDICTION_DIR / "historical_validation"
BASELINE_CSV = HISTORY_DIR / "phasec_precise_202604_history.csv"
FALLBACK_BASELINE_CSV = PREDICTION_DIR / "batch_postclose_all_candidates.csv"
ROLLING_CSV = HISTORY_DIR / "phasec_rolling_history.csv"
DAILY_BARS_DIR = RUNTIME_ROOT / "raw" / "bars" / "daily"
MARKET_INDEX_PATH = RUNTIME_ROOT / "cache" / "market" / "daily" / "sh000001.parquet"
TUSHARE_STK_FACTOR_DIR = RUNTIME_ROOT / "cache" / "prediction" / "tushare" / "stk_factor_pro"
REALTIME_OUTPUT_DIR = (
    Path(os.environ.get("ASHARE_REALTIME_DESKTOP", Path.home() / "Desktop")).resolve()
    / "realtime_1457_outputs"
)
LEGACY_POSTCLOSE_FILES = [
    {
        "date": date(2026, 5, 6),
        "path": REALTIME_OUTPUT_DIR / "realtime_1457_candidates_20260506_tushare_full.csv",
        "run_id": "20260506_tushare_full",
        "output_grade": "legacy_tushare_postclose_full",
    },
    {
        "date": date(2026, 5, 7),
        "path": REALTIME_OUTPUT_DIR / "realtime_1457_candidates_20260507_postclose.csv",
        "run_id": "20260507_postclose",
        "output_grade": "legacy_postclose_snapshot",
    },
    {
        "date": date(2026, 5, 8),
        "path": REALTIME_OUTPUT_DIR / "realtime_1457_m1457_selector_top6_20260508_181051.csv",
        "run_id": "20260508_181051",
        "output_grade": "legacy_afterclose_top6_ties",
    },
]


OUTPUT_COLUMNS = [
    "date",
    "label_date",
    "symbol",
    "name",
    "probability",
    "hit",
    "next_high_return_pct",
    "next_close_return_pct",
    "close",
    "换手",
    "source",
    "run_id",
    "output_grade",
]


def _fmt_date(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return str(value)
    return f"{ts.year}/{ts.month}/{ts.day}"


def _date_key(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return str(value or "")
    return ts.strftime("%Y-%m-%d")


def _load_calendar_next_day() -> dict[date, date]:
    dates: set[date] = set()
    if MARKET_INDEX_PATH.exists():
        cal = pd.read_parquet(MARKET_INDEX_PATH, columns=["date"])
        dates.update(pd.to_datetime(cal["date"], errors="coerce").dropna().dt.date.tolist())
    if TUSHARE_STK_FACTOR_DIR.exists():
        for path in TUSHARE_STK_FACTOR_DIR.glob("*.parquet"):
            ts = pd.to_datetime(path.stem, format="%Y%m%d", errors="coerce")
            if pd.notna(ts):
                dates.add(ts.date())
    for path in REALTIME_OUTPUT_DIR.glob("sina_snapshot_postclose_*.parquet"):
        snapshot_date = _postclose_snapshot_date_from_name(path)
        if snapshot_date is not None and _is_valid_postclose_snapshot(path, snapshot_date):
            dates.add(snapshot_date)
    cal_dates = sorted(dates)
    return {cal_dates[i]: cal_dates[i + 1] for i in range(len(cal_dates) - 1)}


def _load_base_history() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    sources = [
        (FALLBACK_BASELINE_CSV, "baseline_batch"),
        (BASELINE_CSV, "baseline_precise_202604"),
    ]
    for path, source_name in sources:
        if not path.exists():
            continue
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
        if "turnover" in df.columns and "换手" not in df.columns:
            df = df.rename(columns={"turnover": "换手"})
        if "source" in df.columns:
            df["source"] = df["source"].fillna(source_name)
        else:
            df["source"] = source_name
        df["run_id"] = df.get("run_id", "")
        df["output_grade"] = df.get("output_grade", "")
        for col in OUTPUT_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        frames.append(df[OUTPUT_COLUMNS].copy())
    if not frames:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    base = pd.concat(frames, ignore_index=True)
    precise_dates = set(
        base.loc[base["source"].astype(str) == "baseline_precise_202604", "date"].map(_date_key)
    )
    if precise_dates:
        base = base[
            ~(
                (base["source"].astype(str) == "baseline_batch")
                & (base["date"].map(_date_key).isin(precise_dates))
            )
        ].copy()
    return base


def _load_symbol_daily(symbol: str) -> pd.DataFrame | None:
    path = DAILY_BARS_DIR / f"{symbol}.parquet"
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path, columns=["date", "high", "close"])
    except Exception:
        return None


_POSTCLOSE_SNAPSHOT_CACHE: dict[date, pd.DataFrame | None] = {}
_POSTCLOSE_SNAPSHOT_VALID_CACHE: dict[Path, bool] = {}


def _postclose_snapshot_date_from_name(path: Path) -> date | None:
    parts = path.stem.split("_")
    if len(parts) < 4:
        return None
    ts = pd.to_datetime(parts[3], format="%Y%m%d", errors="coerce")
    return ts.date() if pd.notna(ts) else None


def _is_valid_postclose_snapshot(path: Path, expected_date: date) -> bool:
    if path in _POSTCLOSE_SNAPSHOT_VALID_CACHE:
        return _POSTCLOSE_SNAPSHOT_VALID_CACHE[path]
    try:
        meta = pd.read_parquet(path, columns=["quote_date", "quote_time"])
    except Exception:
        _POSTCLOSE_SNAPSHOT_VALID_CACHE[path] = False
        return False
    quote_dates = pd.to_datetime(meta.get("quote_date"), errors="coerce").dropna().dt.date
    if quote_dates.empty or set(quote_dates.unique().tolist()) != {expected_date}:
        _POSTCLOSE_SNAPSHOT_VALID_CACHE[path] = False
        return False
    quote_times = meta.get("quote_time")
    if quote_times is None:
        _POSTCLOSE_SNAPSHOT_VALID_CACHE[path] = False
        return False
    latest_quote_time = quote_times.astype(str).str.slice(0, 8).max()
    valid = latest_quote_time >= "14:59:00"
    _POSTCLOSE_SNAPSHOT_VALID_CACHE[path] = valid
    return valid


def _postclose_snapshot_path(label_date: date) -> Path | None:
    paths = sorted(
        (
            path
            for path in REALTIME_OUTPUT_DIR.glob(f"sina_snapshot_postclose_{label_date:%Y%m%d}_*.parquet")
            if _is_valid_postclose_snapshot(path, label_date)
        ),
        key=lambda p: (p.stat().st_mtime, p.name),
    )
    return paths[-1] if paths else None


def _load_postclose_snapshot(label_date: date) -> pd.DataFrame | None:
    if label_date in _POSTCLOSE_SNAPSHOT_CACHE:
        return _POSTCLOSE_SNAPSHOT_CACHE[label_date]
    path = _postclose_snapshot_path(label_date)
    if path is None:
        _POSTCLOSE_SNAPSHOT_CACHE[label_date] = None
        return None
    try:
        snapshot = pd.read_parquet(path, columns=["symbol", "high", "latest_price"])
    except Exception:
        try:
            snapshot = pd.read_parquet(path)
        except Exception:
            _POSTCLOSE_SNAPSHOT_CACHE[label_date] = None
            return None
    if "symbol" not in snapshot.columns:
        _POSTCLOSE_SNAPSHOT_CACHE[label_date] = None
        return None
    snapshot = snapshot.copy()
    snapshot["symbol"] = snapshot["symbol"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    _POSTCLOSE_SNAPSHOT_CACHE[label_date] = snapshot
    return snapshot


def _infer_next_symbol_date(symbol: str, signal_date: date) -> date | None:
    df = _load_symbol_daily(symbol)
    if df is None or df.empty:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna().dt.date
    after_dates = sorted([d for d in dates.unique().tolist() if d > signal_date])
    return after_dates[0] if after_dates else None


def _load_next_day_record(symbol: str, label_date: date | None) -> tuple[float | None, float | None]:
    if label_date is None:
        return None, None
    df = _load_symbol_daily(symbol)
    if df is not None:
        dates = pd.to_datetime(df["date"], errors="coerce").dt.date
        match = df.loc[dates == label_date]
        if not match.empty:
            row = match.iloc[-1]
            high = pd.to_numeric(row.get("high"), errors="coerce")
            close = pd.to_numeric(row.get("close"), errors="coerce")
            return (
                float(high) if pd.notna(high) else None,
                float(close) if pd.notna(close) else None,
            )
    high = pd.NA
    close = pd.NA
    path = TUSHARE_STK_FACTOR_DIR / f"{label_date:%Y%m%d}.parquet"
    if path.exists():
        try:
            ts_df = pd.read_parquet(path, columns=["ts_code", "high", "close"])
            match = ts_df.loc[ts_df["ts_code"].astype(str).str.slice(0, 6) == symbol]
            if not match.empty:
                row = match.iloc[-1]
                high = pd.to_numeric(row.get("high"), errors="coerce")
                close = pd.to_numeric(row.get("close"), errors="coerce")
        except Exception:
            pass
    if pd.notna(high) and pd.notna(close):
        return float(high), float(close)
    snapshot = _load_postclose_snapshot(label_date)
    if snapshot is None or snapshot.empty:
        return (
            float(high) if pd.notna(high) else None,
            float(close) if pd.notna(close) else None,
        )
    snap_match = snapshot.loc[snapshot["symbol"].astype(str).str.zfill(6) == symbol]
    if snap_match.empty:
        return (
            float(high) if pd.notna(high) else None,
            float(close) if pd.notna(close) else None,
        )
    snap_row = snap_match.iloc[-1]
    snap_high = pd.to_numeric(snap_row.get("high"), errors="coerce")
    snap_close = pd.to_numeric(snap_row.get("latest_price"), errors="coerce")
    return (
        float(snap_high) if pd.notna(snap_high) else (float(high) if pd.notna(high) else None),
        float(snap_close) if pd.notna(snap_close) else (float(close) if pd.notna(close) else None),
    )


def _verified_returns(symbol: str, label_date: date | None, entry_price: float | None) -> tuple[str, float | None, float | None]:
    if entry_price is None or not np.isfinite(entry_price) or entry_price <= 0:
        return "", None, None
    next_high, next_close = _load_next_day_record(symbol, label_date)
    if next_high is None or next_close is None:
        return "", None, None
    high_ret = round((next_high / entry_price - 1.0) * 100.0, 6)
    close_ret = round((next_close / entry_price - 1.0) * 100.0, 6)
    return ("hit" if high_ret >= 1.0 else "miss"), high_ret, close_ret


def _coerce_symbol(value: Any) -> str:
    text = str(value or "").strip()
    if "." in text:
        text = text.split(".")[0]
    text = text.replace(".0", "")
    return text.zfill(6) if text else ""


def _first_numeric(row: pd.Series, columns: list[str]) -> float | None:
    for col in columns:
        if col not in row.index:
            continue
        value = pd.to_numeric(row.get(col), errors="coerce")
        if pd.notna(value):
            return float(value)
    return None


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _legacy_postclose_rows(next_day_map: dict[date, date]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for spec in LEGACY_POSTCLOSE_FILES:
        path = Path(spec["path"])
        if not path.exists():
            continue
        try:
            cands = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
        except Exception:
            continue
        signal_date = spec["date"]
        for _, row in cands.iterrows():
            symbol = _coerce_symbol(row.get("symbol") or row.get("code") or row.get("ts_code"))
            if not symbol:
                continue
            probability = _first_numeric(row, ["probability", "calibrated_prob", "prob"])
            if probability is None or probability < 0.75:
                continue
            if "is_candidate" in row.index and not _truthy(row.get("is_candidate")):
                continue
            entry_price = _first_numeric(row, ["latest_price", "current_price", "close"])
            turnover = _first_numeric(row, ["turnover_today", "turnover", "换手", "鎹㈡墜"])
            label_date = next_day_map.get(signal_date) or _infer_next_symbol_date(symbol, signal_date)
            hit, high_ret, close_ret = _verified_returns(symbol, label_date, entry_price)
            rows.append({
                "date": _fmt_date(signal_date),
                "label_date": _fmt_date(label_date),
                "symbol": symbol,
                "name": row.get("name", ""),
                "probability": round(float(probability), 8),
                "hit": hit,
                "next_high_return_pct": high_ret if high_ret is not None else "",
                "next_close_return_pct": close_ret if close_ret is not None else "",
                "close": round(float(entry_price), 2) if entry_price is not None else "",
                "换手": round(float(turnover), 6) if turnover is not None else "",
                "source": "legacy_postclose_1457",
                "run_id": spec["run_id"],
                "output_grade": spec["output_grade"],
            })
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _iter_valid_postclose_timings() -> list[Path]:
    by_date: dict[date, Path] = {}
    for path in sorted(REALTIME_OUTPUT_DIR.glob("realtime_1457_m1457_timing_*.json")):
        try:
            timing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        live = timing.get("live_results") or {}
        if (timing.get("run_mode") or live.get("run_mode")) != "postclose":
            continue
        if timing.get("test_mode"):
            continue
        if live.get("status") != "ok":
            continue
        if live.get("is_postclose_complete") is not True:
            continue
        if live.get("output_grade") != "postclose_full_data":
            continue
        target_ts = pd.to_datetime(timing.get("target_date") or live.get("target_date"), errors="coerce")
        if pd.isna(target_ts):
            continue
        selector = timing.get("selector") or {}
        selector_csv = selector.get("selector_csv") or (timing.get("paths") or {}).get("selector_csv")
        if not selector_csv or not Path(selector_csv).exists():
            continue
        target_date = target_ts.date()
        previous = by_date.get(target_date)
        if previous is None or path.stat().st_mtime > previous.stat().st_mtime:
            by_date[target_date] = path
    return [by_date[d] for d in sorted(by_date)]


def _postclose_rows(next_day_map: dict[date, date]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for timing_path in _iter_valid_postclose_timings():
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        live = timing.get("live_results") or {}
        selector = timing.get("selector") or {}
        selector_csv = Path(selector.get("selector_csv") or (timing.get("paths") or {}).get("selector_csv"))
        target_ts = pd.to_datetime(timing.get("target_date") or live.get("target_date"), errors="coerce")
        if pd.isna(target_ts):
            continue
        signal_date = target_ts.date()
        try:
            cands = pd.read_csv(selector_csv, encoding="utf-8-sig", dtype=str)
        except Exception:
            continue
        run_id = timing_path.stem.replace("realtime_1457_m1457_timing_", "")
        output_grade = str(live.get("output_grade") or "")
        for _, row in cands.iterrows():
            symbol = str(row.get("symbol", "")).replace(".0", "").zfill(6)
            probability = pd.to_numeric(row.get("probability"), errors="coerce")
            entry_price = pd.to_numeric(row.get("latest_price"), errors="coerce")
            turnover = pd.to_numeric(row.get("turnover_today"), errors="coerce")
            label_date = next_day_map.get(signal_date) or _infer_next_symbol_date(symbol, signal_date)
            hit, high_ret, close_ret = _verified_returns(
                symbol,
                label_date,
                float(entry_price) if pd.notna(entry_price) else None,
            )
            rows.append({
                "date": _fmt_date(signal_date),
                "label_date": _fmt_date(label_date),
                "symbol": symbol,
                "name": row.get("name", ""),
                "probability": round(float(probability), 8) if pd.notna(probability) else "",
                "hit": hit,
                "next_high_return_pct": high_ret if high_ret is not None else "",
                "next_close_return_pct": close_ret if close_ret is not None else "",
                "close": round(float(entry_price), 2) if pd.notna(entry_price) else "",
                "换手": round(float(turnover), 6) if pd.notna(turnover) else "",
                "source": "postclose_1457",
                "run_id": run_id,
                "output_grade": output_grade,
            })
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _iter_valid_formal_timings() -> list[Path]:
    by_date: dict[date, Path] = {}
    for path in sorted(REALTIME_OUTPUT_DIR.glob("realtime_1457_m1457_timing_*.json")):
        try:
            timing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        live = timing.get("live_results") or {}
        if (timing.get("run_mode") or live.get("run_mode")) != "formal":
            continue
        if timing.get("test_mode"):
            continue
        if live.get("status") != "ok":
            continue
        if live.get("is_formal_valid") is not True:
            continue
        if live.get("snapshot_time_status") not in {None, "verified"}:
            continue
        selector = timing.get("selector") or {}
        selector_csv = selector.get("selector_csv") or (timing.get("paths") or {}).get("selector_csv")
        if not selector_csv or not Path(selector_csv).exists():
            continue
        target_ts = pd.to_datetime(timing.get("target_date") or live.get("target_date"), errors="coerce")
        if pd.isna(target_ts):
            continue
        target_date = target_ts.date()
        previous = by_date.get(target_date)
        if previous is None or path.stat().st_mtime > previous.stat().st_mtime:
            by_date[target_date] = path
    return [by_date[d] for d in sorted(by_date)]


def _formal_rows(next_day_map: dict[date, date], exclude_date_keys: set[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for timing_path in _iter_valid_formal_timings():
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        live = timing.get("live_results") or {}
        selector = timing.get("selector") or {}
        selector_csv = Path(selector.get("selector_csv") or (timing.get("paths") or {}).get("selector_csv"))
        target_ts = pd.to_datetime(timing.get("target_date") or live.get("target_date"), errors="coerce")
        if pd.isna(target_ts):
            continue
        signal_date = target_ts.date()
        if _date_key(signal_date) in exclude_date_keys:
            continue
        try:
            cands = pd.read_csv(selector_csv, encoding="utf-8-sig", dtype=str)
        except Exception:
            continue
        run_id = timing_path.stem.replace("realtime_1457_m1457_timing_", "")
        output_grade = str(live.get("output_grade") or "")
        for _, row in cands.iterrows():
            symbol = str(row.get("symbol", "")).replace(".0", "").zfill(6)
            probability = pd.to_numeric(row.get("probability"), errors="coerce")
            entry_price = pd.to_numeric(row.get("latest_price"), errors="coerce")
            turnover = pd.to_numeric(row.get("turnover_today"), errors="coerce")
            label_date = next_day_map.get(signal_date) or _infer_next_symbol_date(symbol, signal_date)
            hit, high_ret, close_ret = _verified_returns(
                symbol,
                label_date,
                float(entry_price) if pd.notna(entry_price) else None,
            )
            rows.append({
                "date": _fmt_date(signal_date),
                "label_date": _fmt_date(label_date),
                "symbol": symbol,
                "name": row.get("name", ""),
                "probability": round(float(probability), 8) if pd.notna(probability) else "",
                "hit": hit,
                "next_high_return_pct": high_ret if high_ret is not None else "",
                "next_close_return_pct": close_ret if close_ret is not None else "",
                "close": round(float(entry_price), 2) if pd.notna(entry_price) else "",
                "鎹㈡墜": round(float(turnover), 6) if pd.notna(turnover) else "",
                "source": "formal_1457",
                "run_id": run_id,
                "output_grade": output_grade,
            })
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def update_history() -> pd.DataFrame:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    next_day_map = _load_calendar_next_day()
    base = _load_base_history()
    legacy = _legacy_postclose_rows(next_day_map)
    live = _postclose_rows(next_day_map)
    live_date_keys = set(live["date"].map(_date_key).tolist()) if not live.empty else set()
    formal = _formal_rows(next_day_map, live_date_keys)
    combined = pd.concat([base, legacy, formal, live], ignore_index=True)
    if combined.empty:
        combined = pd.DataFrame(columns=OUTPUT_COLUMNS)
    for col in OUTPUT_COLUMNS:
        if col not in combined.columns:
            combined[col] = ""
    combined["_date_key"] = combined["date"].map(_date_key)
    combined["_symbol_key"] = combined["symbol"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    source_rank = {
        "baseline_batch": 0,
        "baseline_precise_202604": 1,
        "legacy_postclose_1457": 2,
        "formal_1457": 2,
        "postclose_1457": 3,
    }
    combined["_source_rank"] = combined["source"].map(lambda x: source_rank.get(str(x), 0))
    combined["_prob"] = pd.to_numeric(combined["probability"], errors="coerce").fillna(-1.0)
    combined = combined.sort_values(
        ["_date_key", "_source_rank", "_prob", "_symbol_key"],
        ascending=[True, False, False, True],
    )
    combined = combined.drop_duplicates(["_date_key", "_symbol_key"], keep="first")
    combined = combined.sort_values(["_date_key", "_prob"], ascending=[True, False])
    combined = combined.drop(columns=["_date_key", "_symbol_key", "_source_rank", "_prob"])
    combined = combined[OUTPUT_COLUMNS]
    combined.to_csv(ROLLING_CSV, index=False, encoding="utf-8-sig")
    return combined


def main() -> int:
    global ROLLING_CSV
    parser = argparse.ArgumentParser(description="Update rolling 14:57 post-close candidate history CSV")
    parser.add_argument("--output", type=Path, default=ROLLING_CSV)
    args = parser.parse_args()
    ROLLING_CSV = args.output
    df = update_history()
    dates = sorted(df["date"].dropna().unique().tolist(), key=_date_key) if not df.empty else []
    verified = df[df["hit"].isin(["hit", "miss"])] if "hit" in df.columns else pd.DataFrame()
    hits = int((verified["hit"] == "hit").sum()) if not verified.empty else 0
    print(f"wrote: {ROLLING_CSV}")
    print(f"rows: {len(df)}, dates: {len(dates)}")
    if dates:
        print(f"date range: {dates[0]} -> {dates[-1]}")
    if not verified.empty:
        print(f"verified: {len(verified)}, hits: {hits}, hit_rate: {hits / len(verified) * 100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

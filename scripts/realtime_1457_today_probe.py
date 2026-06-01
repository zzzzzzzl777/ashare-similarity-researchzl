#!/usr/bin/env python
"""14:57 Live Engineering Test — 2026-05-07

Minimal live test: real-time snapshot at 14:57, feature construction, bundle inference.
NOT a production system. NOT claimed as passed/final_unseen/tradeable.

Phases:
  warmup  — load bundle, bars, pre-compute THS/TGB/limit_pool (run BEFORE 14:57)
  live    — grab snapshot, build features, infer (run AT 14:57)
  report  — output CSV + timing

Usage:
    python scripts/realtime_1457_today_probe.py --phase warmup
    python scripts/realtime_1457_today_probe.py --phase live
    python scripts/realtime_1457_today_probe.py --phase all  (warmup then wait for 14:57)
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SUBAGENT_ROOT = Path(os.environ.get("ASHARE_SUBAGENT_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(SUBAGENT_ROOT / "src"))
DESKTOP_DIR = Path(os.environ.get("ASHARE_REALTIME_DESKTOP", Path.home() / "Desktop")).resolve()
REALTIME_OUTPUT_DIR = DESKTOP_DIR / "realtime_1457_outputs"

RUNTIME_ROOT = Path(
    os.environ.get(
        "ASHARE_SIMILARITY_RUNTIME_DATA",
        os.environ.get("ASHARE_SIMILARITY_DATA", "E:/ashare_similarity_runtime/data"),
    )
).resolve()
DAILY_BARS_DIR = RUNTIME_ROOT / "raw" / "bars" / "daily"
MARKET_INDEX_DIR = RUNTIME_ROOT / "cache" / "market" / "daily"
TUSHARE_DIR = RUNTIME_ROOT / "cache" / "prediction" / "tushare"
LIMIT_POOL_DIR = RUNTIME_ROOT / "cache" / "prediction" / "limit_pool_snapshots"
FEATURE_CACHE_PATH = (
    RUNTIME_ROOT / "reports" / "prediction" / "feature_cache"
    / "gpu_probe_features_665406333a7e545d.parquet"
)
THS_FACTOR_CACHE_PATH = (
    RUNTIME_ROOT / "reports" / "prediction" / "feature_cache"
    / "realtime_1457_ths_sector_factor.parquet"
)
BUNDLE_PATH = (
    RUNTIME_ROOT / "reports" / "prediction" / "runs"
    / "gpu_probe_20260509T105830Z_12605e2b" / "model_bundle.pt"
)

OUTPUT_CSV = REALTIME_OUTPUT_DIR / "realtime_1457_candidates_20260507_live.csv"
REPORT_PATH = SUBAGENT_ROOT / "docs" / "realtime_1457_live_test_20260507.md"
NAME_CACHE_PATH = SUBAGENT_ROOT / "scripts" / "_symbol_name_cache.json"

TODAY = date(2026, 5, 7)
TODAY_STR = "2026-05-07"

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

# Feature availability at 14:57:
# - EXACT (realtime): price-derived, cross-section, volume-based (~249/260)
# - PROXY (realtime push2 f62): tushare_net_mf_amount, tushare_ff_adjusted_flow
# - T-1 TUSHARE (cannot compute realtime): moneyflow breakdown ratios (5 features)
# - T-1 STABLE: stk_limit distances, volume_ratio basis
# See MONEYFLOW_BREAKDOWN_FEATURES in fetch_realtime_moneyflow.py for detail.

# ---------------------------------------------------------------------------
# Imports from project
# ---------------------------------------------------------------------------
from ashare_similarity.prediction.gpu_probe import (
    GPU_PROBE_ALL_FEATURES,
    GPU_PROBE_CROSS_MARKET_FEATURES,
    GPU_PROBE_INTRADAY_FACTOR_FEATURES,
    GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES,
    GPU_PROBE_MARKET_INDEX_SYMBOLS,
    GPU_PROBE_TGB_FACTOR_FEATURES,
    GPU_PROBE_THS_SECTOR_FEATURES,
    GPU_PROBE_TUSHARE_FACTOR_FEATURES,
    GpuProbeConfig,
    _add_cross_section_features,
    _attach_free_factor_features,
    _attach_tgb_factor_features,
    _daily_context_slice,
    _ensure_feature_columns,
    _symbol_feature_frame,
)
from ashare_similarity.prediction.free_data_factors import (
    build_cross_market_return_factor,
)
from fetch_realtime_moneyflow import (
    fetch_net_mf_batch,
    MONEYFLOW_BREAKDOWN_FEATURES,
    MONEYFLOW_NET_FEATURES,
)
from ashare_similarity.prediction.ths_sector_factors import (
    THS_SECTOR_COLUMNS,
    build_ths_sector_factors,
)
from ashare_similarity.prediction.factor_cache_manager import FactorFrame, merge_factor_frames
from ashare_similarity.prediction.limit_pool_snapshots import (
    build_limit_pool_snapshot_factors,
    fetch_limit_pool_snapshots,
    load_snapshot_bundles,
)


LIVE_LIMIT_POOL_KINDS = (
    "zt_pool",
    "zbgc_pool",
    "dtgc_pool",
    "strong_pool",
    "zt_pool_previous",
)

LIVE_TUSHARE_LIMIT_COLUMNS = (
    "tushare_seal_ratio",
    "tushare_open_times",
    "tushare_first_time_minutes",
    "tushare_up_stat_days",
    "tushare_limit_type",
    "tushare_limit_turnover",
)
LIVE_TUSHARE_LIMIT_FEATURES = set(LIVE_TUSHARE_LIMIT_COLUMNS) | {
    f"{column}_available" for column in LIVE_TUSHARE_LIMIT_COLUMNS
}

LIVE_CHIP_T1_COLUMNS = (
    "tushare_winner_rate",
    "tushare_cost_concentration",
    "tushare_cost_position",
)
LIVE_INTRADAY_MINUTE_COLUMNS = (
    "tushare_last_30min_return",
)
LIVE_INTRADAY_SNAPSHOT_COLUMNS = (
    "tushare_vwap_deviation",
    "tushare_close_vs_vwap",
)
LIVE_DAILY_DERIVED_COLUMNS = (
    "tushare_price_vs_cost_20d",
    "tushare_abnormal_3d_deviation",
    "tushare_vol_gain_20d",
    "tushare_inv_t_20d",
    "tushare_asr_60d",
    "tushare_illiq_classic_20d",
    "tushare_ato_120d",
    "tushare_prev_top20_chase_mean",
    "tushare_volume_sufficiency_ratio",
    "tushare_anti_drop_strength_20d",
    "tushare_multi_wave_count_60d",
)
LIVE_RUNTIME_VALUE_COLUMNS = (
    *LIVE_CHIP_T1_COLUMNS,
    *LIVE_INTRADAY_MINUTE_COLUMNS,
    *LIVE_INTRADAY_SNAPSHOT_COLUMNS,
    *LIVE_DAILY_DERIVED_COLUMNS,
)
LIVE_RUNTIME_HARD_GATE_COLUMNS = (
    *LIVE_CHIP_T1_COLUMNS,
    *LIVE_INTRADAY_MINUTE_COLUMNS,
    *LIVE_INTRADAY_SNAPSHOT_COLUMNS,
)

POST_CLOSE_DELETE_COLUMNS = {
    "tushare_lhb_net_buy",
    "tushare_lhb_net_rate",
    "tushare_inst_buy_count",
    "tushare_lhb_appeared",
    "tushare_inst_net_buy",
    "tushare_rzye_delta_pct",
    "tushare_rzye",
    "tushare_rzmre_ratio",
    "tushare_margin_net",
    "tushare_rqye_ratio",
    "tushare_auction_close_vwap_ratio",
    "tushare_auction_close_vol",
    "tushare_float_relative_impact",
}
POST_CLOSE_DELETE_FEATURES = POST_CLOSE_DELETE_COLUMNS | {
    f"{column}_available" for column in POST_CLOSE_DELETE_COLUMNS
}
STRICT_FORBIDDEN_SELECTED_FEATURES = (
    POST_CLOSE_DELETE_FEATURES
    | set(GPU_PROBE_THS_SECTOR_FEATURES)
    | {f"{column}_available" for column in GPU_PROBE_THS_SECTOR_FEATURES}
)


# ---------------------------------------------------------------------------
# Bundle loading + inference (from predict_with_saved_bundle.py)
# ---------------------------------------------------------------------------
def load_bundle(path: Path, device: str = "cpu") -> dict:
    import torch
    bundle = torch.load(path, map_location=device, weights_only=False)
    members = []
    for m in bundle["members"]:
        model = pickle.loads(m["model_bytes"])
        members.append({"model": model, "model_name": m["model_name"],
                        "model_kind": m["model_kind"]})
    iso_model = pickle.loads(bundle["iso_model_bytes"]) if bundle.get("iso_model_bytes") else None
    return {
        "model_kind": bundle["model_kind"],
        "model_name": bundle["model_name"],
        "member_names": bundle["member_names"],
        "members": members,
        "mean": bundle["mean"],
        "std": bundle["std"],
        "selected_indices": bundle["selected_indices"],
        "feature_names": bundle["feature_names"],
        "selected_feature_names": bundle["selected_feature_names"],
        "iso_model": iso_model,
        "calibration_used": bundle["calibration_used"],
        "threshold": bundle["threshold"],
        "confidence_band": bundle.get("confidence_band"),
    }


def run_inference(bundle: dict, raw_features: np.ndarray, device: str = "cpu") -> np.ndarray:
    import torch
    x = torch.as_tensor(raw_features, dtype=torch.float32, device=device)
    mean = bundle["mean"].to(device)
    std = bundle["std"].to(device)
    std_safe = std.clone()
    std_safe[std_safe == 0] = 1.0
    x = (x - mean) / std_safe
    if bundle["selected_indices"] is not None:
        x = x[:, bundle["selected_indices"].to(device)]
    x_np = x.detach().cpu().numpy()
    probs = np.stack([m["model"].predict_proba(x_np)[:, 1].astype(np.float32)
                      for m in bundle["members"]], axis=0)
    prob = probs.mean(axis=0)
    if bundle["calibration_used"] == "isotonic" and bundle["iso_model"] is not None:
        prob = bundle["iso_model"].predict(prob.astype(np.float64)).astype(np.float32)
    return prob


# ---------------------------------------------------------------------------
# Real-time snapshot from 东方财富 push2
# ---------------------------------------------------------------------------
def fetch_realtime_snapshot(universe: list[str] | None = None) -> pd.DataFrame:
    """Fetch A-share snapshot from Sina finance API (batch, fast, reliable).

    Falls back to 东方财富 push2 if Sina fails.
    Sina: ~0.1s for 700 symbols. push2: ~3s but currently unreliable (502).
    """
    session = requests.Session()
    session.trust_env = False
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}

    # Convert to Sina symbol format
    if universe:
        sina_symbols = []
        for sym in universe:
            if sym.startswith("6"):
                sina_symbols.append(f"sh{sym}")
            else:
                sina_symbols.append(f"sz{sym}")
    else:
        return pd.DataFrame()

    all_data = []
    batch_size = 400
    for i in range(0, len(sina_symbols), batch_size):
        batch = sina_symbols[i:i + batch_size]
        url = f"http://hq.sinajs.cn/list={','.join(batch)}"
        r = session.get(url, headers=headers, timeout=15, proxies=PROXY)
        if r.status_code != 200:
            continue
        lines = [l.strip() for l in r.text.strip().split(";") if l.strip() and "=" in l]
        for line in lines:
            parts = line.split("=", 1)
            code_part = parts[0].replace("var hq_str_", "").strip()
            data_part = parts[1].strip('"').strip()
            if not data_part:
                continue
            fields = data_part.split(",")
            if len(fields) < 10:
                continue
            sym6 = code_part[2:]
            try:
                row_dict = {
                    "symbol": sym6,
                    "name": fields[0],
                    "open": float(fields[1]) if fields[1] else np.nan,
                    "prev_close": float(fields[2]) if fields[2] else np.nan,
                    "latest_price": float(fields[3]) if fields[3] else np.nan,
                    "high": float(fields[4]) if fields[4] else np.nan,
                    "low": float(fields[5]) if fields[5] else np.nan,
                    "volume": float(fields[8]) if fields[8] else np.nan,
                    "amount": float(fields[9]) if fields[9] else np.nan,
                }
                if len(fields) > 31:
                    row_dict["quote_date"] = fields[30] if fields[30] else ""
                    row_dict["quote_time"] = fields[31] if fields[31] else ""
                else:
                    row_dict["quote_date"] = ""
                    row_dict["quote_time"] = ""
                all_data.append(row_dict)
            except (ValueError, IndexError):
                continue

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df["pct_change"] = ((df["latest_price"] - df["prev_close"]) / df["prev_close"] * 100).round(2)
    # Turnover not directly available from Sina; will use NaN
    df["turnover"] = np.nan
    df["captured_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df["snapshot_source"] = "sina"
    return df


def validate_snapshot_time(
    snapshot: pd.DataFrame,
    expected_date: date,
    *,
    min_hhmmss: tuple[int, int, int] = (14, 56, 30),
    max_hhmmss: tuple[int, int, int] = (14, 58, 30),
    run_mode: str = "formal",
    require_captured_at: bool = False,
) -> dict[str, Any]:
    """Validate that snapshot quote_time falls within the expected window.

    Default formal window: 14:56:30 to 14:58:30 (seconds-level).
    require_captured_at: if True, snapshot MUST contain captured_at and
        snapshot_source columns or validation fails (use for saved snapshots).
    Returns dict with keys: valid, reason, status, quote_time_counts.
    """
    result: dict[str, Any] = {"valid": False, "reason": "", "status": "unknown", "quote_time_counts": {}}

    if require_captured_at:
        missing = []
        for col in ("quote_date", "quote_time", "captured_at", "snapshot_source"):
            if col not in snapshot.columns:
                missing.append(col)
        if missing:
            result["reason"] = f"saved snapshot missing required columns: {missing}"
            result["status"] = "saved_snapshot_unverified"
            return result

    if "quote_time" not in snapshot.columns or "quote_date" not in snapshot.columns:
        result["reason"] = "snapshot missing quote_time/quote_date columns"
        result["status"] = "saved_snapshot_unverified"
        return result

    qt = snapshot["quote_time"].astype(str).str.strip()
    qd = snapshot["quote_date"].astype(str).str.strip()

    valid_rows = qt.str.fullmatch(r"\d{2}:\d{2}:\d{2}") & (qd != "")
    if valid_rows.sum() == 0:
        result["reason"] = "no rows with parseable quote_time"
        result["status"] = "saved_snapshot_unverified"
        return result

    hh = qt[valid_rows].str[:2].astype(int)
    mm = qt[valid_rows].str[3:5].astype(int)
    ss = qt[valid_rows].str[6:8].astype(int)
    total_sec = hh * 3600 + mm * 60 + ss

    min_sec = min_hhmmss[0] * 3600 + min_hhmmss[1] * 60 + min_hhmmss[2]
    max_sec = max_hhmmss[0] * 3600 + max_hhmmss[1] * 60 + max_hhmmss[2]

    in_window = (total_sec >= min_sec) & (total_sec <= max_sec)
    pct_in_window = in_window.sum() / len(in_window)

    date_match = qd[valid_rows] == expected_date.strftime("%Y-%m-%d")
    pct_date_match = date_match.sum() / len(date_match)

    qt_sorted = qt[valid_rows].sort_values()
    result["quote_time_counts"] = {
        "total": int(len(snapshot)),
        "parseable": int(valid_rows.sum()),
        "in_window": int(in_window.sum()),
        "pct_in_window": round(float(pct_in_window), 4),
        "date_match": int(date_match.sum()),
        "pct_date_match": round(float(pct_date_match), 4),
        "quote_time_min": str(qt_sorted.iloc[0]) if len(qt_sorted) > 0 else "",
        "quote_time_max": str(qt_sorted.iloc[-1]) if len(qt_sorted) > 0 else "",
    }

    if pct_date_match < 0.9:
        result["reason"] = f"quote_date mismatch: only {pct_date_match:.1%} match {expected_date}"
        result["status"] = "quote_date_mismatch"
        return result
    if pct_in_window < 0.9:
        result["reason"] = (
            f"quote_time outside [{min_hhmmss[0]:02d}:{min_hhmmss[1]:02d}:{min_hhmmss[2]:02d}-"
            f"{max_hhmmss[0]:02d}:{max_hhmmss[1]:02d}:{max_hhmmss[2]:02d}]: "
            f"only {pct_in_window:.1%} in window"
        )
        result["status"] = "snapshot_time_invalid"
        return result

    # Also validate captured_at for formal
    if run_mode == "formal" and "captured_at" in snapshot.columns:
        cap = snapshot["captured_at"].astype(str).str.strip().iloc[0] if len(snapshot) > 0 else ""
        if cap and len(cap) >= 19:
            try:
                cap_dt = datetime.strptime(cap[:19], "%Y-%m-%d %H:%M:%S")
                cap_sec = cap_dt.hour * 3600 + cap_dt.minute * 60 + cap_dt.second
                if not (min_sec <= cap_sec <= max_sec):
                    result["reason"] = f"captured_at {cap} outside formal window"
                    result["status"] = "captured_at_outside_formal_window"
                    return result
            except ValueError:
                pass

    result["valid"] = True
    result["reason"] = "ok"
    result["status"] = "verified"
    return result


# ---------------------------------------------------------------------------
# Universe determination
# ---------------------------------------------------------------------------
def get_universe_from_cache() -> list[str]:
    """Get active universe from feature cache latest dates (fallback only)."""
    df = pd.read_parquet(FEATURE_CACHE_PATH, columns=["date", "symbol"])
    dates = sorted(df["date"].unique())
    recent = df[df["date"] >= dates[-5]]
    counts = recent.groupby("symbol").size()
    return sorted(counts[counts >= 3].index.tolist())


def _is_main_board(symbol: str) -> bool:
    s = str(symbol).strip().zfill(6)
    return s.startswith(("600", "601", "603", "605", "000", "001", "002", "003"))


def is_trading_day(target_date: date) -> bool:
    """Check if target_date is an A-share trading day.

    Strategy: (1) local daily bar data, (2) Sina realtime quote_date probe, (3) weekday heuristic.
    """
    if target_date.weekday() >= 5:
        return False

    # 1. Check local daily bar parquets
    sample_syms = ["000001", "600000", "000002"]
    for sym in sample_syms:
        path = DAILY_BARS_DIR / f"{sym}.parquet"
        if path.exists():
            try:
                df = pd.read_parquet(path, columns=["date"])
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                dates = set(df["date"].dt.date.dropna())
                if target_date in dates:
                    return True
                future = [d for d in dates if d > target_date]
                if future:
                    return False
            except Exception:
                continue

    # 2. If target_date is today, probe Sina for a realtime quote_date
    if target_date == date.today():
        try:
            snap = fetch_realtime_snapshot(universe=["000001"])
            if not snap.empty and "quote_date" in snap.columns:
                qd = str(snap["quote_date"].iloc[0]).strip()
                if qd == target_date.strftime("%Y-%m-%d"):
                    return True
                elif qd and qd != "":
                    return False
        except Exception:
            pass

    # 3. Weekday heuristic (already checked >= 5 above)
    return True


def _dyn_rolling_mean(s: pd.Series, window: int) -> pd.Series:
    first = s.iloc[0] if len(s) > 0 else 0.0
    padded = pd.concat([pd.Series([first] * (window - 1)), s.reset_index(drop=True)], ignore_index=True)
    return padded.rolling(window).mean().iloc[window - 1:].reset_index(drop=True)


def _dyn_rolling_std(s: pd.Series, window: int) -> pd.Series:
    first = s.iloc[0] if len(s) > 0 else 0.0
    padded = pd.concat([pd.Series([first] * (window - 1)), s.reset_index(drop=True)], ignore_index=True)
    return padded.rolling(window).std(ddof=0).iloc[window - 1:].reset_index(drop=True)


def _dyn_rolling_sum(s: pd.Series, window: int) -> pd.Series:
    first = s.iloc[0] if len(s) > 0 else 0.0
    padded = pd.concat([pd.Series([first] * (window - 1)), s.reset_index(drop=True)], ignore_index=True)
    return padded.rolling(window).sum().iloc[window - 1:].reset_index(drop=True)


def _dyn_rolling_zscore(s: pd.Series, window: int) -> pd.Series:
    mean = _dyn_rolling_mean(s, window)
    std = _dyn_rolling_std(s, window).clip(lower=1e-6)
    return (s.reset_index(drop=True) - mean) / std


def _dyn_check_short_gate(df: pd.DataFrame) -> bool:
    """Check if a symbol passes the short_only gate on its last row.

    Matches training logic: min_turnover=3.0, min_amount=200M, min_amount_z=1.0,
    min_range_pct=3.0, min_volatility_pct=2.5, min_phase_days_3=1, min_abnormal_flags=2.
    """
    if len(df) < 20:
        return False

    close = df["close"].reset_index(drop=True).astype(float)
    high = df["high"].reset_index(drop=True).astype(float)
    low = df["low"].reset_index(drop=True).astype(float)
    volume = df["volume"].reset_index(drop=True).astype(float)
    amount = df["amount"].reset_index(drop=True).astype(float)
    turnover = df["turnover"].reset_index(drop=True).astype(float)

    volume_log = np.log1p(volume.clip(lower=0))
    amount_log = np.log1p(amount.clip(lower=0))

    amount_z_20 = _dyn_rolling_zscore(amount_log, 20)
    volume_z_20 = _dyn_rolling_zscore(volume_log, 20)
    turnover_z_20 = _dyn_rolling_zscore(turnover, 20)

    range_pct = (high - low) / close.clip(lower=1e-6) * 100.0

    prev_close = close.shift(1).fillna(close.iloc[0])
    one_day_return = (close / prev_close.clip(lower=1e-6) - 1.0) * 100.0
    ret_std_10 = _dyn_rolling_std(one_day_return, 10)

    true_range = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr_14_pct = _dyn_rolling_mean(true_range, 14) / close.clip(lower=1e-6) * 100.0

    direction = np.sign(close - prev_close)
    obv = (direction * volume).cumsum()
    obv_lag5 = obv.shift(5).fillna(obv.iloc[0])
    rolling_vol_sum_5 = _dyn_rolling_sum(volume.abs(), 5).clip(lower=1e-6)
    obv_trend_5 = (obv - obv_lag5) / rolling_vol_sum_5

    volume_to_mean_20 = volume / _dyn_rolling_mean(volume, 20).clip(lower=1e-6)
    amount_to_mean_20 = amount / _dyn_rolling_mean(amount, 20).clip(lower=1e-6)

    money_flow_fire = (
        amount_z_20.clip(lower=0) * 0.35
        + volume_z_20.clip(lower=0) * 0.25
        + turnover_z_20.clip(lower=0) * 0.20
        + range_pct.clip(lower=0) / 10.0
        + obv_trend_5.clip(lower=0) * 0.15
    )

    turnover_gate = turnover >= 3.0
    liquidity_gate = (amount >= 200_000_000.0) | (amount_z_20 >= 1.0)
    volatility_gate = (range_pct >= 3.0) | (ret_std_10 >= 2.5) | (atr_14_pct >= 2.5)

    phase_day_flag = (turnover_gate & liquidity_gate & volatility_gate).astype(float)
    short_phase_days_3 = _dyn_rolling_sum(phase_day_flag, 3)

    abnormal_flags = (
        turnover_gate.astype(int)
        + liquidity_gate.astype(int)
        + (volume_z_20 >= 1.0).astype(int)
        + volatility_gate.astype(int)
        + (money_flow_fire >= 1.5).astype(int)
        + (volume_to_mean_20 >= 1.5).astype(int)
        + (amount_to_mean_20 >= 1.5).astype(int)
    )

    idx = len(df) - 1
    return bool(
        turnover_gate.iloc[idx]
        and liquidity_gate.iloc[idx]
        and volatility_gate.iloc[idx]
        and short_phase_days_3.iloc[idx] >= 1
        and abnormal_flags.iloc[idx] >= 2
    )


def get_universe_dynamic(target_date: date) -> list[str]:
    """Dynamically screen short-term active stocks from daily bars, matching training gate."""
    all_parquets = list(DAILY_BARS_DIR.glob("*.parquet"))
    main_board = [p.stem for p in all_parquets if len(p.stem) == 6 and p.stem.isdigit() and _is_main_board(p.stem)]
    print(f"    Dynamic gate: scanning {len(main_board)} main-board symbols...")

    gate_cols = ["date", "open", "high", "low", "close", "volume", "amount", "turnover"]
    passed: list[str] = []
    errors = 0

    def _check_one(sym: str) -> tuple[str, bool]:
        try:
            path = DAILY_BARS_DIR / f"{sym}.parquet"
            df = pd.read_parquet(path, columns=gate_cols)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df[df["date"].dt.date < target_date]
            df = df.sort_values("date").tail(30).reset_index(drop=True)
            if len(df) < 20:
                return sym, False
            return sym, _dyn_check_short_gate(df)
        except Exception:
            return sym, False

    workers = min(16, max(4, (os.cpu_count() or 4)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_check_one, sym) for sym in main_board]
        for fut in as_completed(futures):
            sym, ok = fut.result()
            if ok:
                passed.append(sym)

    passed.sort()
    print(f"    Dynamic gate result: {len(passed)}/{len(main_board)} passed")

    if len(passed) < 50:
        print(f"    WARNING: dynamic gate returned only {len(passed)} symbols, falling back to cache")
        return get_universe_from_cache()

    return passed


# ---------------------------------------------------------------------------
# Build GpuProbeConfig for today
# ---------------------------------------------------------------------------
def build_config() -> GpuProbeConfig:
    lookback_start = TODAY - timedelta(days=400)
    end_date = TODAY + timedelta(days=5)
    return GpuProbeConfig(
        start=lookback_start,
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=end_date,
        min_phase_days_3=1,  # Must match training: requires >= 1 day in phase 3
        short_only=True,
        exclude_event_limit_up=False,  # Post-hoc filter — declared in report
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_set="research",
    )


def apply_realtime_gate(
    snapshot: pd.DataFrame,
    historical_bars: dict[str, pd.DataFrame],
    turnover_map: dict[str, float],
) -> list[str]:
    """Re-run the short_only gate using today's realtime snapshot as the last row.

    This catches stocks that became active TODAY but weren't in yesterday's gate.
    """
    passed = []
    for _, row in snapshot.iterrows():
        sym = str(row["symbol"]).zfill(6)
        hist = historical_bars.get(sym)
        if hist is None or len(hist) < 19:
            continue

        today_turnover = turnover_map.get(sym, np.nan)
        today_amount = row.get("amount", np.nan)
        today_volume = row.get("volume", np.nan)
        today_open = row.get("open", np.nan)
        today_high = row.get("high", np.nan)
        today_low = row.get("low", np.nan)
        today_close = row.get("latest_price", np.nan)

        if any(pd.isna(v) or v <= 0 for v in [today_close, today_volume, today_amount]):
            continue
        if pd.isna(today_turnover) or today_turnover <= 0:
            continue

        today_row = pd.DataFrame([{
            "date": pd.Timestamp(TODAY),
            "open": float(today_open),
            "high": float(today_high),
            "low": float(today_low),
            "close": float(today_close),
            "volume": float(today_volume),
            "amount": float(today_amount),
            "turnover": float(today_turnover),
        }])
        combined = pd.concat([
            hist[["date", "open", "high", "low", "close", "volume", "amount", "turnover"]].tail(29),
            today_row,
        ], ignore_index=True)
        if _dyn_check_short_gate(combined):
            passed.append(sym)

    passed.sort()
    return passed


# ---------------------------------------------------------------------------
# Load daily bars
# ---------------------------------------------------------------------------
def load_daily_bars(symbols: list[str], start: date, end: date) -> dict[str, pd.DataFrame]:
    bars = {}
    for sym in symbols:
        path = DAILY_BARS_DIR / f"{sym}.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        if "date" not in df.columns:
            continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
        df = df[mask].reset_index(drop=True)
        if not df.empty:
            bars[sym] = df
    return bars


# ---------------------------------------------------------------------------
# Inject live snapshot as today's bar
# ---------------------------------------------------------------------------
def inject_snapshot_bar(
    bars: dict[str, pd.DataFrame],
    snapshot: pd.DataFrame,
    target_date: date,
    turnover_map: dict[str, float] | None = None,
    require_realtime_turnover: bool = False,
) -> dict[str, pd.DataFrame]:
    """Append today's snapshot as a synthetic daily bar + dummy T+1 bar.

    _symbol_feature_frame excludes the LAST row (can't compute T+1 label).
    We must append a dummy T+1 bar so target_date is NOT the last row.

    turnover_map: if provided, use real-time turnover from snapshot volume/float_share.
                  In executable live mode, missing turnover skips the symbol.
    """
    snap_map = snapshot.set_index("symbol")
    dummy_date = target_date + timedelta(days=1)
    injected_count = 0
    for sym, df in bars.items():
        if sym not in snap_map.index:
            continue
        row = snap_map.loc[sym]
        if pd.isna(row.get("latest_price")) or row.get("latest_price", 0) <= 0:
            continue
        if (df["date"].dt.date == target_date).any():
            continue
        price = row.get("latest_price", np.nan)
        if turnover_map and sym in turnover_map:
            turnover_val = turnover_map[sym]
        elif require_realtime_turnover:
            continue
        elif "turnover" in df.columns and not df["turnover"].dropna().empty:
            turnover_val = df["turnover"].dropna().iloc[-1]
        else:
            turnover_val = np.nan
        prev_close = row.get("prev_close", np.nan)
        pct_change = (
            (price / prev_close - 1.0) * 100.0
            if pd.notna(price) and pd.notna(prev_close) and prev_close > 0
            else np.nan
        )
        today_row = {
            "date": pd.Timestamp(target_date),
            "symbol": sym,
            "open": row.get("open", np.nan),
            "high": row.get("high", np.nan),
            "low": row.get("low", np.nan),
            "close": price,
            "volume": row.get("volume", np.nan),
            "amount": row.get("amount", np.nan),
            "turnover": turnover_val,
            "pct_change": pct_change,
        }
        # Dummy T+1 bar (minimal, just so target_date isn't excluded)
        dummy_row = {
            "date": pd.Timestamp(dummy_date),
            "symbol": sym,
            "open": price, "high": price, "low": price, "close": price,
            "volume": 0.0, "amount": 0.0, "turnover": 0.0, "pct_change": 0.0,
        }
        new_df = pd.concat([df, pd.DataFrame([today_row, dummy_row])], ignore_index=True)
        bars[sym] = new_df
        injected_count += 1
    return bars


# ---------------------------------------------------------------------------
# Build features
# ---------------------------------------------------------------------------
def build_symbol_features(
    all_bars: dict[str, pd.DataFrame],
    config: GpuProbeConfig,
    target_date: date,
    max_symbols: int | None = None,
) -> tuple[pd.DataFrame, list[pd.DataFrame], dict[str, float]]:
    import torch
    device = torch.device("cpu")
    examples = []
    context_frames = []
    timing = {}

    symbols = list(all_bars.keys())
    if max_symbols and len(symbols) > max_symbols:
        symbols = symbols[:max_symbols]

    t0 = time.perf_counter()
    total = len(symbols)
    for idx, sym in enumerate(symbols, 1):
        bars_df = all_bars[sym]
        ctx = _daily_context_slice(bars_df, symbol=sym, start=config.start, end=config.end)
        if not ctx.empty:
            context_frames.append(ctx)
        frame = _symbol_feature_frame(
            bars_df, symbol=sym, start=config.start, end=config.end,
            device=device, config=config,
        )
        if not frame.empty:
            target_rows = frame[frame["date"].dt.date == target_date]
            if not target_rows.empty:
                examples.append(target_rows)
        if idx == 1 or idx % 200 == 0 or idx == total:
            elapsed = time.perf_counter() - t0
            print(
                f"  [symbol_features] {idx}/{total} accepted={len(examples)} "
                f"elapsed={elapsed:.1f}s",
                flush=True,
            )
    timing["symbol_features_sec"] = time.perf_counter() - t0

    if not examples:
        return pd.DataFrame(), context_frames, timing
    data = pd.concat(examples, ignore_index=True)
    return data, context_frames, timing


def _latest_parquet_mtime(paths: list[Path]) -> float:
    existing = [p for p in paths if p.exists()]
    if not existing:
        return 0.0
    return max(p.stat().st_mtime for p in existing)


def _ths_source_mtime(tushare_dir: Path) -> float:
    paths: list[Path] = []
    member_path = tushare_dir / "ths_member" / "all_members.parquet"
    if member_path.exists():
        paths.append(member_path)
    for subdir in ("ths_daily", "limit_list_d"):
        root = tushare_dir / subdir
        if root.exists():
            paths.extend(p for p in root.iterdir() if p.suffix == ".parquet" and not p.name.startswith("_"))
    return _latest_parquet_mtime(paths)


def _make_ths_factor(frame: pd.DataFrame) -> FactorFrame:
    return FactorFrame(
        name="ths_sector_daily",
        frame=frame,
        columns=tuple(THS_SECTOR_COLUMNS),
        source="tushare_ths_cached",
        asof_time="after_close",
        lag_rule="T day THS concept data; use for T+1 prediction only",
        join_keys=("symbol", "date"),
    )


def empty_ths_live_factor() -> FactorFrame:
    """Empty THS factor for executable 14:57 runs.

    Tushare THS daily rows are not a guaranteed 14:57 data source. We do not
    preload target-day THS rows here, even if a post-close cache happens to
    exist during a later replay.
    """
    frame = pd.DataFrame(columns=["symbol", "date", *THS_SECTOR_COLUMNS])
    return _make_ths_factor(frame)


def load_or_build_ths_sector_factor(tushare_dir: Path) -> FactorFrame:
    """Load cached THS sector factor when source parquet files have not changed."""
    source_mtime = _ths_source_mtime(tushare_dir)
    if THS_FACTOR_CACHE_PATH.exists() and THS_FACTOR_CACHE_PATH.stat().st_mtime >= source_mtime:
        frame = pd.read_parquet(THS_FACTOR_CACHE_PATH)
        return _make_ths_factor(frame)

    factor = build_ths_sector_factors(tushare_dir)
    THS_FACTOR_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    factor.frame.to_parquet(THS_FACTOR_CACHE_PATH, index=False)
    meta_path = THS_FACTOR_CACHE_PATH.with_suffix(".json")
    meta = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "rows": int(len(factor.frame)),
        "source_mtime": source_mtime,
        "cache_path": str(THS_FACTOR_CACHE_PATH),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return factor


def narrow_ths_factor_for_live(
    factor: FactorFrame | None,
    *,
    symbols: list[str],
    target_date: date,
) -> FactorFrame | None:
    """Keep only rows that can join to the live inference frame.

    The full THS factor cache is millions of rows. Live scoring has one date and
    a few hundred symbols, so narrowing here preserves merge semantics while
    avoiding a large left join at 14:57.

    This helper is retained for diagnostics only. Production executable 14:57
    runs use empty_ths_live_factor() to avoid accidental target-day THS leakage.
    """
    if factor is None or factor.frame.empty:
        return factor
    frame = factor.frame
    if "symbol" not in frame.columns or "date" not in frame.columns:
        return factor
    date_values = pd.to_datetime(frame["date"], errors="coerce").dt.date
    symbol_values = frame["symbol"].astype(str).str.zfill(6)
    symbol_set = set(str(s).zfill(6) for s in symbols)
    mask = date_values.eq(target_date) & symbol_values.isin(symbol_set)
    narrowed = frame.loc[mask, ["symbol", "date", *factor.columns]].copy()
    return FactorFrame(
        name=factor.name,
        frame=narrowed,
        columns=factor.columns,
        source=factor.source,
        asof_time=factor.asof_time,
        lag_rule=factor.lag_rule,
        join_keys=factor.join_keys,
    )


def selected_needs_live_limit_pool(selected_features: set[str]) -> bool:
    limit_features = set(GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES)
    return bool(selected_features & (limit_features | LIVE_TUSHARE_LIMIT_FEATURES))


def fetch_live_limit_pool_bundle(
    target_date: date,
    *,
    selected_features: set[str],
) -> tuple[list[FactorFrame], dict[str, Any]]:
    """Fetch the executable live limit/failed-board pools for target_date."""
    need_live_pool = selected_needs_live_limit_pool(selected_features)
    meta: dict[str, Any] = {
        "required": need_live_pool,
        "kinds": list(LIVE_LIMIT_POOL_KINDS),
        "status": "skipped",
        "counts": {},
        "factor_names": [],
        "tushare_compat_rows": 0,
    }
    if not need_live_pool:
        return [], meta

    started = time.perf_counter()
    try:
        frames = fetch_limit_pool_snapshots(target_date, kinds=LIVE_LIMIT_POOL_KINDS)
    except Exception as exc:
        meta.update(
            {
                "status": "failed_fetch",
                "error": str(exc),
                "elapsed_sec": round(time.perf_counter() - started, 3),
            }
        )
        return [], meta

    meta["captured_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta["counts"] = {kind: int(len(frame)) for kind, frame in frames.items()}
    meta["total_rows"] = int(sum(meta["counts"].values()))

    factors: list[FactorFrame] = []
    try:
        factors.extend(build_limit_pool_snapshot_factors(frames))
        compat = build_live_tushare_limit_factor(frames, target_date=target_date)
        if compat is not None:
            factors.append(compat)
            meta["tushare_compat_rows"] = int(len(compat.frame))
    except Exception as exc:
        meta.update(
            {
                "status": "failed_build",
                "error": str(exc),
                "elapsed_sec": round(time.perf_counter() - started, 3),
            }
        )
        return [], meta

    meta["factor_names"] = [factor.name for factor in factors]
    meta["status"] = "available" if factors else "empty"
    meta["elapsed_sec"] = round(time.perf_counter() - started, 3)
    return factors, meta


def build_live_tushare_limit_factor(
    frames: dict[str, pd.DataFrame],
    *,
    target_date: date,
) -> FactorFrame | None:
    """Map live AkShare limit pools into the historical Tushare limit_list_d names.

    The model was trained with Tushare limit_list_d columns. For executable
    14:57 scoring, the equivalent source is the live Eastmoney limit pool:
    zt_pool for sealed boards, zbgc_pool for failed boards, dtgc_pool for
    limit-down pressure. This keeps column names aligned without post-close
    Tushare leakage.
    """
    pieces: list[pd.DataFrame] = []
    kind_priority = {"zt_pool": 0, "zbgc_pool": 1, "dtgc_pool": 2}
    limit_type = {"zt_pool": 1.0, "zbgc_pool": 0.0, "dtgc_pool": -1.0}

    for kind in ("zt_pool", "zbgc_pool", "dtgc_pool"):
        frame = frames.get(kind)
        if frame is None or frame.empty:
            continue
        work = frame.copy()
        if "symbol" not in work.columns:
            continue
        work["symbol"] = work["symbol"].astype(str).str.extract(r"(\d{6})", expand=False).fillna("").str.zfill(6)
        work = work[work["symbol"].str.fullmatch(r"\d{6}").fillna(False)].copy()
        if work.empty:
            continue

        amount = pd.to_numeric(work.get("amount"), errors="coerce")
        float_mv = pd.to_numeric(work.get("float_market_cap"), errors="coerce")
        seal_amount = pd.to_numeric(work.get("seal_amount"), errors="coerce")
        open_times = pd.to_numeric(work.get("open_board_count"), errors="coerce")
        if kind == "zbgc_pool":
            open_times = open_times.fillna(1.0).clip(lower=1.0)
            seal_amount = seal_amount.fillna(0.0)
        else:
            open_times = open_times.fillna(0.0)

        out = pd.DataFrame(
            {
                "symbol": work["symbol"].values,
                "date": pd.Timestamp(target_date),
                "tushare_seal_ratio": (
                    seal_amount / np.maximum(float_mv, 1.0)
                ).replace([np.inf, -np.inf], np.nan).fillna(0.0),
                "tushare_open_times": open_times,
                "tushare_first_time_minutes": pd.to_numeric(
                    work.get("first_seal_minutes"), errors="coerce"
                ),
                "tushare_up_stat_days": pd.to_numeric(
                    work.get("board_count"), errors="coerce"
                ).fillna(0.0),
                "tushare_limit_type": limit_type[kind],
                "tushare_limit_turnover": (
                    amount / np.maximum(float_mv, 1.0)
                ).replace([np.inf, -np.inf], np.nan).fillna(0.0),
                "_priority": kind_priority[kind],
            }
        )
        pieces.append(out)

    if not pieces:
        return None

    merged = pd.concat(pieces, ignore_index=True)
    merged = (
        merged.sort_values(["symbol", "_priority"], kind="stable")
        .drop_duplicates(["symbol", "date"], keep="first")
        .drop(columns=["_priority"])
        .reset_index(drop=True)
    )
    return FactorFrame(
        name="live_tushare_limit_compat",
        frame=merged[["symbol", "date", *LIVE_TUSHARE_LIMIT_COLUMNS]].copy(),
        columns=LIVE_TUSHARE_LIMIT_COLUMNS,
        source="akshare_live_limit_pool",
        asof_time="live_snapshot_1457",
        lag_rule="T-day live limit/failed-board pool captured at scoring time; no post-close Tushare leakage.",
        join_keys=("symbol", "date"),
    )


def _symbol_to_ts_code(symbol: str) -> str:
    sym = str(symbol).zfill(6)
    if sym.startswith(("6", "9")):
        return f"{sym}.SH"
    if sym.startswith(("4", "8")):
        return f"{sym}.BJ"
    return f"{sym}.SZ"


def _previous_trading_date_from_bars(
    bars: dict[str, pd.DataFrame],
    target_date: date,
) -> date | None:
    dates: list[date] = []
    for df in bars.values():
        if df is None or df.empty or "date" not in df.columns:
            continue
        values = pd.to_datetime(df["date"], errors="coerce").dropna().dt.date
        values = values[values < target_date]
        if not values.empty:
            dates.append(values.max())
    return max(dates) if dates else None


def _fetch_tushare_cyq_perf_day(trade_day: date) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load or pull one full-market cyq_perf day for strict T-1 chip features."""
    trade_date = trade_day.strftime("%Y%m%d")
    cache_path = TUSHARE_DIR / "cyq_perf" / f"_live_daily_{trade_date}.parquet"
    meta: dict[str, Any] = {
        "trade_date": trade_date,
        "cache_path": str(cache_path),
        "source": "cache",
    }
    if cache_path.exists():
        try:
            df = pd.read_parquet(cache_path)
            meta["rows"] = int(len(df))
            if not df.empty:
                return df, meta
        except Exception as exc:
            meta["cache_error"] = str(exc)

    try:
        import tushare as ts

        token = (os.environ.get("TUSHARE_TOKEN") or os.environ.get("TSY_TUSHARE_TOKEN") or "").strip()
        if not token:
            raise RuntimeError("Missing TUSHARE_TOKEN or TSY_TUSHARE_TOKEN")
        ts.set_token(token)
        pro = ts.pro_api()
        pro._DataApi__http_url = os.environ.get("TUSHARE_HTTP_URL", "http://tsy.xiaodefa.cn")
        pro._DataApi__timeout = 120
        started = time.perf_counter()
        df = pro.cyq_perf(trade_date=trade_date)
        meta["source"] = "tushare_api"
        meta["pull_sec"] = round(time.perf_counter() - started, 3)
        meta["rows"] = int(len(df)) if df is not None else 0
        if df is not None and not df.empty:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(cache_path, index=False)
            return df, meta
    except Exception as exc:
        meta["source"] = "failed"
        meta["error"] = str(exc)
    return pd.DataFrame(), meta


def attach_live_chip_t1_features(
    data: pd.DataFrame,
    historical_bars: dict[str, pd.DataFrame],
    target_date: date,
    selected_features: set[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    needed = bool(selected_features & (set(LIVE_CHIP_T1_COLUMNS) | {f"{c}_available" for c in LIVE_CHIP_T1_COLUMNS}))
    meta: dict[str, Any] = {"required": needed, "status": "skipped"}
    if not needed:
        return data, meta

    prev_trade_day = _previous_trading_date_from_bars(historical_bars, target_date)
    if prev_trade_day is None:
        meta.update({"status": "missing_previous_trade_day"})
        return data, meta

    cyq, pull_meta = _fetch_tushare_cyq_perf_day(prev_trade_day)
    meta.update(pull_meta)
    if cyq.empty:
        meta.update({"status": "missing_cyq_perf"})
        return data, meta

    work = cyq.copy()
    work["symbol"] = work["ts_code"].astype(str).str.split(".").str[0].str.zfill(6)
    work["_date"] = pd.to_datetime(work["trade_date"].astype(str), format="%Y%m%d", errors="coerce").dt.date
    work = work[work["_date"] == prev_trade_day].copy()
    if work.empty:
        meta.update({"status": "wrong_cyq_date", "rows_for_date": 0})
        return data, meta

    for col in ("winner_rate", "cost_85pct", "cost_15pct", "cost_50pct", "weight_avg"):
        work[col] = pd.to_numeric(work.get(col), errors="coerce")
    cost_15 = work["cost_15pct"].abs().clip(lower=0.01)
    cost_50 = work["cost_50pct"].abs().clip(lower=0.01)
    feature_frame = pd.DataFrame(
        {
            "symbol": work["symbol"],
            "tushare_winner_rate": work["winner_rate"],
            "tushare_cost_concentration": work["cost_85pct"] / cost_15,
            "tushare_cost_position": (work["weight_avg"] - work["cost_50pct"]) / cost_50,
        }
    ).drop_duplicates("symbol", keep="last")
    feature_frame = feature_frame.set_index("symbol")

    symbols = data["symbol"].astype(str).str.zfill(6)
    for col in LIVE_CHIP_T1_COLUMNS:
        values = symbols.map(feature_frame[col])
        data[col] = values.astype(float)
        data[f"{col}_available"] = values.notna().astype(np.float32)

    coverage = float(symbols.isin(feature_frame.index).mean()) if len(symbols) else 0.0
    meta.update(
        {
            "status": "available",
            "previous_trade_date": prev_trade_day.isoformat(),
            "rows_for_date": int(len(feature_frame)),
            "coverage": round(coverage, 6),
        }
    )
    return data, meta


def attach_live_intraday_snapshot_features(
    data: pd.DataFrame,
    snapshot: pd.DataFrame,
    selected_features: set[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    needed = bool(selected_features & set(LIVE_INTRADAY_SNAPSHOT_COLUMNS))
    meta: dict[str, Any] = {"required": needed, "status": "skipped"}
    if not needed:
        return data, meta
    if snapshot.empty:
        meta["status"] = "missing_snapshot"
        return data, meta

    snap = snapshot.copy()
    snap["symbol"] = snap["symbol"].astype(str).str.zfill(6)
    for col in ("latest_price", "volume", "amount"):
        snap[col] = pd.to_numeric(snap.get(col), errors="coerce")
    volume = snap["volume"].where(snap["volume"] > 0)
    amount = snap["amount"].where(snap["amount"] > 0)
    vwap = amount / volume
    lot_volume_mask = (
        vwap.notna()
        & snap["latest_price"].notna()
        & (snap["latest_price"] > 0)
        & (vwap > snap["latest_price"] * 20.0)
    )
    if lot_volume_mask.any():
        vwap.loc[lot_volume_mask] = amount.loc[lot_volume_mask] / (volume.loc[lot_volume_mask] * 100.0)
    snap["tushare_vwap_deviation"] = (
        (snap["latest_price"] - vwap) / np.maximum(np.abs(vwap), 0.01)
    )
    snap["tushare_close_vs_vwap"] = snap["latest_price"] / np.maximum(vwap, 0.01) - 1.0
    snap = snap.set_index("symbol")

    symbols = data["symbol"].astype(str).str.zfill(6)
    for col in LIVE_INTRADAY_SNAPSHOT_COLUMNS:
        values = symbols.map(snap[col])
        data[col] = values.astype(float)
        data[f"{col}_available"] = values.notna().astype(np.float32)
    meta.update(
        {
            "status": "available",
            "rows": int(len(snap)),
            "coverage": round(float(symbols.isin(snap.index).mean()) if len(symbols) else 0.0, 6),
        }
    )
    return data, meta


def _sina_minute_symbol(symbol: str) -> str:
    sym = str(symbol).zfill(6)
    if sym.startswith("6"):
        return f"sh{sym}"
    if sym.startswith(("4", "8", "9")):
        return f"bj{sym}"
    return f"sz{sym}"


def _symbol_to_tscode(symbol: str) -> str:
    """Convert plain 6-digit symbol to tushare ts_code format (e.g. 000001.SZ)."""
    sym = str(symbol).zfill(6)
    if sym.startswith("6"):
        return f"{sym}.SH"
    if sym.startswith(("4", "8", "9")):
        return f"{sym}.BJ"
    return f"{sym}.SZ"


def _last30_return_from_5min_bars(
    bars: pd.DataFrame,
    target_date: date,
    time_col: str,
    open_col: str,
    close_col: str,
) -> tuple[float | None, str | None]:
    if bars is None or bars.empty:
        return None, "empty"
    work = bars.copy()
    work[time_col] = pd.to_datetime(work[time_col], errors="coerce")
    work[open_col] = pd.to_numeric(work[open_col], errors="coerce")
    work[close_col] = pd.to_numeric(work[close_col], errors="coerce")
    day_start = pd.Timestamp(f"{target_date.isoformat()} 00:00:00")
    day_end = pd.Timestamp(f"{target_date.isoformat()} 23:59:59")
    day_bars = work[
        (work[time_col] >= day_start)
        & (work[time_col] <= day_end)
    ].dropna(subset=[open_col, close_col]).sort_values(time_col)
    if len(day_bars) < 6:
        return None, "not_enough_tail_bars"
    last_6 = day_bars.tail(6)
    first_open = float(last_6[open_col].iloc[0])
    last_close = float(last_6[close_col].iloc[-1])
    if first_open <= 0:
        return None, "bad_open"
    return last_close / first_open - 1.0, None


def _fetch_one_5min_last30(symbol: str, target_date: date, *, max_retries: int = 3) -> tuple[str, float | None, str | None]:
    last_err: str | None = None
    for attempt in range(max_retries):
        if attempt > 0:
            time.sleep(0.5 * attempt)
        try:
            import akshare as ak

            try:
                bars = ak.stock_zh_a_minute(
                    symbol=_sina_minute_symbol(symbol),
                    period="5",
                    adjust="",
                )
                value, err = _last30_return_from_5min_bars(
                    bars,
                    target_date,
                    "day",
                    "open",
                    "close",
                )
                if value is not None:
                    return symbol, value, None
            except Exception:
                pass

            start = f"{target_date.isoformat()} 09:30:00"
            end = f"{target_date.isoformat()} 15:00:00"
            bars = ak.stock_zh_a_hist_min_em(
                symbol=str(symbol).zfill(6),
                start_date=start,
                end_date=end,
                period="5",
                adjust="",
            )
            value, err = _last30_return_from_5min_bars(
                bars,
                target_date,
                "时间",
                "开盘",
                "收盘",
            )
            if value is not None:
                return symbol, value, None
            last_err = err
        except Exception as exc:
            last_err = str(exc)[:160]
    return symbol, None, last_err


def capture_price_snapshot_1430(universe: list[str]) -> dict[str, float]:
    """Fetch current prices from Sina and return as {symbol: price} dict.

    Called during the wait period at ~14:30 to cache prices for last_30min_return.
    """
    snapshot = fetch_realtime_snapshot(universe=universe)
    if snapshot.empty:
        return {}
    result = {}
    for _, row in snapshot.iterrows():
        sym = str(row["symbol"]).zfill(6)
        price = row.get("latest_price")
        if pd.notna(price) and float(price) > 0:
            result[sym] = float(price)
    return result


def attach_live_minute_features(
    data: pd.DataFrame,
    target_date: date,
    selected_features: set[str],
    *,
    price_cache_1430: dict[str, float] | None = None,
    snapshot_prices: dict[str, float] | None = None,
    run_mode: str = "formal",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    needed = bool(selected_features & set(LIVE_INTRADAY_MINUTE_COLUMNS))
    meta: dict[str, Any] = {"required": needed, "status": "skipped"}
    if not needed:
        return data, meta

    now = datetime.now()

    # Path 1: Sina 14:30 cache + snapshot prices (best, no AkShare needed)
    if price_cache_1430 and snapshot_prices:
        symbols = data["symbol"].astype(str).str.zfill(6)
        values = {}
        for sym in symbols.unique():
            p1430 = price_cache_1430.get(sym)
            p1457 = snapshot_prices.get(sym)
            if p1430 and p1457 and p1430 > 0:
                values[sym] = p1457 / p1430 - 1.0
        mapped = symbols.map(values)
        data["tushare_last_30min_return"] = mapped.astype(float)
        data["tushare_last_30min_return_available"] = mapped.notna().astype(np.float32)
        coverage = len(values) / max(len(symbols.unique()), 1)
        meta.update({
            "status": "available",
            "method": "sina_1430_cache",
            "rows": int(len(values)),
            "coverage": round(coverage, 6),
        })
        return data, meta

    # Path 2 (test mode only): zero-fill is allowed
    if run_mode == "test":
        if now.date() == target_date and (now.hour, now.minute) < (14, 55):
            print(
                f"WARNING: 5-minute intraday bars not yet mature (now={now.strftime('%H:%M:%S')}, need>=14:55). "
                f"Filling tushare_last_30min_return with 0.0 (training default); results are approximate."
            )
            data["tushare_last_30min_return"] = 0.0
            data["tushare_last_30min_return_available"] = 1.0
            meta.update({
                "status": "approximate",
                "method": "zero_fill_early",
                "warning": "tushare_last_30min_return filled with 0.0 (test mode, 5-min bars immature)",
                "now": now.strftime("%H:%M:%S"),
            })
            return data, meta

        print(
            f"WARNING [test mode]: No 14:30 price cache available. "
            f"Filling tushare_last_30min_return with 0.0; results are approximate."
        )
        data["tushare_last_30min_return"] = 0.0
        data["tushare_last_30min_return_available"] = 1.0
        meta.update({
            "status": "approximate",
            "method": "zero_fill_no_cache",
            "warning": "No 14:30 price cache; filled with 0.0 (test mode only)",
            "now": now.strftime("%H:%M:%S"),
        })
        return data, meta

    # Path 3 (formal / postclose): NO zero-fill allowed.
    # Use small parallel pool for postclose (4 workers, tested stable).
    # Formal uses 2 workers (rarely hits this path — only when 14:30 cache is missing).
    if now.date() == target_date and (now.hour, now.minute) < (14, 55):
        print(
            f"FATAL: formal/postclose mode requires real last_30min_return, "
            f"but 5-min bars not yet mature (now={now.strftime('%H:%M:%S')}, need>=14:55) "
            f"and no 14:30 price cache."
        )
        meta.update({
            "status": "too_early",
            "method": "blocked",
            "now": now.strftime("%H:%M:%S"),
        })
        return data, meta

    # Path 3a: Check for cached AkShare-derived last_30min_return from a previous run
    REALTIME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _akshare_cache_path = REALTIME_OUTPUT_DIR / f"last30min_cache_{target_date.strftime('%Y%m%d')}.json"
    if _akshare_cache_path.exists():
        try:
            with _akshare_cache_path.open("r", encoding="utf-8") as _cf:
                _cached = json.load(_cf)
            cached_values = _cached.get("values", {})
            cached_coverage = _cached.get("coverage", 0)
            if cached_coverage >= 0.95 and len(cached_values) > 500:
                print(f"  Reusing cached last_30min_return: {len(cached_values)} symbols "
                      f"(coverage={cached_coverage:.1%}, from {_cached.get('created_at', '?')})")
                symbols = data["symbol"].astype(str).str.zfill(6)
                mapped = symbols.map(cached_values)
                data["tushare_last_30min_return"] = mapped.astype(float)
                data["tushare_last_30min_return_available"] = mapped.notna().astype(np.float32)
                meta.update({
                    "status": "available",
                    "method": "akshare_cached",
                    "rows": int(mapped.notna().sum()),
                    "coverage": round(float(mapped.notna().mean()), 6),
                    "cache_source": str(_akshare_cache_path),
                })
                return data, meta
        except Exception as exc:
            print(f"  Warning: failed to load cached last_30min_return: {exc}")

    # Path 3b: Local stk_mins_5 parquet cache (fastest path)
    symbols = data["symbol"].astype(str).str.zfill(6)
    unique_syms = list(symbols.unique())
    values: dict[str, float] = {}
    local_miss_syms: list[str] = []

    _LOCAL_5MIN_DIR = TUSHARE_DIR / "stk_mins_5"
    t0_local = time.perf_counter()
    print(f"  [Local 5min cache] Checking {len(unique_syms)} symbols...", flush=True)

    for sym in unique_syms:
        ts_code = _symbol_to_tscode(sym)
        local_path = _LOCAL_5MIN_DIR / f"{ts_code}.parquet"
        if not local_path.exists():
            local_miss_syms.append(sym)
            continue
        try:
            bars = pd.read_parquet(local_path, columns=["trade_time", "open", "close"])
            val, _ = _last30_return_from_5min_bars(bars, target_date, "trade_time", "open", "close")
            if val is not None:
                values[sym] = val
            else:
                local_miss_syms.append(sym)
        except Exception:
            local_miss_syms.append(sym)

    local_elapsed = time.perf_counter() - t0_local
    local_coverage = len(values) / max(len(unique_syms), 1)
    print(f"  [Local 5min cache] {len(values)}/{len(unique_syms)} "
          f"({local_coverage:.1%} coverage, {local_elapsed:.1f}s, "
          f"{len(local_miss_syms)} miss)", flush=True)

    if local_coverage >= 0.95:
        mapped = symbols.map(values)
        data["tushare_last_30min_return"] = mapped.astype(float)
        data["tushare_last_30min_return_available"] = mapped.notna().astype(np.float32)
        try:
            cache_payload = {
                "target_date": target_date.isoformat(),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "count": len(values),
                "total": len(unique_syms),
                "coverage": round(local_coverage, 6),
                "failed": local_miss_syms,
                "values": values,
                "source": "local_5min_cache",
            }
            with _akshare_cache_path.open("w", encoding="utf-8") as _cf:
                json.dump(cache_payload, _cf)
            print(f"  Cached last_30min_return (source=local_5min_cache, "
                  f"{len(values)} symbols, coverage={local_coverage:.1%})")
        except Exception as exc:
            print(f"  Warning: failed to write cache: {exc}")
        meta.update({
            "status": "available",
            "method": "local_5min_cache",
            "rows": int(len(values)),
            "errors": len(local_miss_syms),
            "coverage": round(local_coverage, 6),
            "elapsed_sec": round(local_elapsed, 2),
        })
        return data, meta

    # Path 3c: Tushare stk_mins (paid proxy) — only for symbols local cache missed
    remaining_after_local = local_miss_syms if local_miss_syms else unique_syms
    tushare_failed_syms: list[str] = []
    tushare_errors: list[str] = []

    try:
        from ashare_similarity.data.tushare_proxy_client import (
            TsyTushareProxyClient,
            TsyTushareProxyConfig,
        )
        _ts_token = (os.environ.get("TSY_TUSHARE_TOKEN") or os.environ.get("TUSHARE_TOKEN") or "").strip()
        if not _ts_token:
            raise RuntimeError("Missing TSY_TUSHARE_TOKEN or TUSHARE_TOKEN")
        _ts_config = TsyTushareProxyConfig(
            token=_ts_token,
            base_url=os.environ.get("TUSHARE_PROXY_BASE_URL", "http://124.220.22.110:8020/"),
            calls_per_minute=150,
        )
        _ts_client = TsyTushareProxyClient(_ts_config)
        _ts_start = datetime.combine(target_date, datetime.strptime("14:30", "%H:%M").time())
        _ts_end = datetime.combine(target_date, datetime.strptime("15:00", "%H:%M").time())
        t0_ts = time.perf_counter()
        _ts_workers = 6
        print(f"  [Tushare stk_mins] Fetching {len(remaining_after_local)} remaining symbols "
              f"({_ts_workers} threads, 150/min)...", flush=True)

        def _fetch_one_tushare(sym: str) -> tuple[str, float | None, str]:
            ts_code = _symbol_to_tscode(sym)
            try:
                bars = _ts_client.fetch_stock_mins(
                    ts_code=ts_code,
                    freq="5min",
                    start_date=_ts_start,
                    end_date=_ts_end,
                )
                val, _ = _last30_return_from_5min_bars(
                    bars, target_date, "trade_time", "open", "close",
                )
                return sym, val, "" if val is not None else "no_bars_in_window"
            except Exception as exc:
                return sym, None, str(exc)[:120]

        done_count = 0
        with ThreadPoolExecutor(max_workers=_ts_workers) as pool:
            futures = {pool.submit(_fetch_one_tushare, sym): sym for sym in remaining_after_local}
            for future in as_completed(futures):
                sym, val, err_msg = future.result()
                if val is not None:
                    values[sym] = val
                else:
                    tushare_failed_syms.append(sym)
                    if err_msg:
                        tushare_errors.append(f"{sym}: {err_msg}")
                done_count += 1
                if done_count % 100 == 0 or done_count == len(remaining_after_local):
                    elapsed_ts = time.perf_counter() - t0_ts
                    print(f"    [{done_count}/{len(remaining_after_local)}] "
                          f"{len(values)} ok total, "
                          f"{len(tushare_failed_syms)} err ({elapsed_ts:.1f}s)", flush=True)

        ts_elapsed = time.perf_counter() - t0_ts
        total_coverage = len(values) / max(len(unique_syms), 1)
        print(f"  [Tushare stk_mins] Done: +{done_count - len(tushare_failed_syms)} new, "
              f"total {len(values)}/{len(unique_syms)} ({total_coverage:.1%}, {ts_elapsed:.1f}s)",
              flush=True)

        if tushare_errors:
            n_show = min(5, len(tushare_errors))
            print(f"  [Tushare errors] {len(tushare_errors)} failures (showing {n_show}):")
            for err_line in tushare_errors[:n_show]:
                print(f"    {err_line}")

        # Checkpoint: save partial results so next run can skip already-fetched symbols
        if total_coverage >= 0.95:
            mapped = symbols.map(values)
            data["tushare_last_30min_return"] = mapped.astype(float)
            data["tushare_last_30min_return_available"] = mapped.notna().astype(np.float32)
            try:
                cache_payload = {
                    "target_date": target_date.isoformat(),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "count": len(values),
                    "total": len(unique_syms),
                    "coverage": round(total_coverage, 6),
                    "failed": tushare_failed_syms,
                    "values": values,
                    "source": "local_5min_cache+tushare",
                }
                with _akshare_cache_path.open("w", encoding="utf-8") as _cf:
                    json.dump(cache_payload, _cf)
                print(f"  Cached last_30min_return (source=local+tushare, "
                      f"{len(values)} symbols, coverage={total_coverage:.1%})")
            except Exception as exc:
                print(f"  Warning: failed to write cache: {exc}")
            meta.update({
                "status": "available",
                "method": "local_5min_cache+tushare",
                "rows": int(len(values)),
                "errors": len(tushare_failed_syms),
                "coverage": round(total_coverage, 6),
                "elapsed_sec": round(local_elapsed + ts_elapsed, 2),
            })
            return data, meta
        else:
            print(f"  [Tushare] Coverage {total_coverage:.1%} < 95%, "
                  f"falling through to AkShare for {len(tushare_failed_syms)} remaining...")
    except Exception as exc:
        print(f"  [Tushare stk_mins] Init/fetch failed: {exc}")
        print(f"  Falling through to AkShare...")

    # Path 3d: AkShare serial fetch (final fallback for remaining symbols)
    failed_syms: list[str] = []
    t0 = time.perf_counter()
    remaining_syms = tushare_failed_syms if tushare_failed_syms else local_miss_syms
    print(f"  [AkShare fallback] Fetching {len(remaining_syms)} remaining symbols (serial)...",
          flush=True)

    def _do_fetch(syms: list[str], pass_label: str) -> list[str]:
        still_failed: list[str] = []
        for i, sym in enumerate(syms):
            _, val, err = _fetch_one_5min_last30(sym, target_date)
            if val is not None:
                values[sym] = val
            else:
                still_failed.append(sym)
            if (i + 1) % 100 == 0 or (i + 1) == len(syms):
                elapsed = time.perf_counter() - t0
                print(f"    [{pass_label}] {i + 1}/{len(syms)} done, "
                      f"{len(values)} ok total, {len(still_failed)} err ({elapsed:.1f}s)")
        return still_failed

    failed_syms = _do_fetch(remaining_syms, "pass1")

    if failed_syms:
        print(f"  Retrying {len(failed_syms)} failed symbols (pass 2)...")
        time.sleep(2)
        failed_syms = _do_fetch(failed_syms, "pass2")

    if failed_syms:
        print(f"  Retrying {len(failed_syms)} failed symbols (pass 3, last)...")
        time.sleep(3)
        failed_syms = _do_fetch(failed_syms, "pass3")

    total_elapsed = time.perf_counter() - t0_local
    mapped = symbols.map(values)
    data["tushare_last_30min_return"] = mapped.astype(float)
    data["tushare_last_30min_return_available"] = mapped.notna().astype(np.float32)
    coverage = len(values) / max(len(unique_syms), 1)

    if failed_syms and len(failed_syms) <= 10:
        for sym in failed_syms:
            print(f"  [5min final fail] {sym}")
    elif failed_syms:
        print(f"  [5min final fails] {len(failed_syms)} total (showing first 5):")
        for sym in failed_syms[:5]:
            print(f"    {sym}")

    if coverage >= 0.95:
        try:
            cache_payload = {
                "target_date": target_date.isoformat(),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "count": len(values),
                "total": len(unique_syms),
                "coverage": round(coverage, 6),
                "failed": failed_syms,
                "values": values,
                "source": "local+tushare+akshare",
            }
            with _akshare_cache_path.open("w", encoding="utf-8") as _cf:
                json.dump(cache_payload, _cf)
            print(f"  Cached last_30min_return (source=local+tushare+akshare, "
                  f"{len(values)} symbols, coverage={coverage:.1%})")
        except Exception as exc:
            print(f"  Warning: failed to write cache: {exc}")

    meta.update({
        "status": "available" if coverage > 0.95 else "low_coverage",
        "method": "local+tushare+akshare",
        "rows": int(len(values)),
        "errors": len(failed_syms),
        "coverage": round(coverage, 6),
        "elapsed_sec": round(total_elapsed, 2),
    })
    print(f"  5-min fetch complete: {len(values)}/{len(unique_syms)} "
          f"({coverage:.1%} coverage, {total_elapsed:.1f}s)")
    return data, meta


def _live_daily_frame_for_symbol(
    symbol: str,
    df: pd.DataFrame,
    target_date: date,
) -> pd.DataFrame | None:
    work = df.copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    work = work[work["date"].dt.date <= target_date].copy()
    if len(work) < 120:
        return None
    work["symbol"] = str(symbol).zfill(6)
    for col in ("close", "volume", "amount", "turnover", "pct_change"):
        if col not in work.columns:
            work[col] = np.nan
        work[col] = pd.to_numeric(work[col], errors="coerce")
    computed_pct = (work["close"] / work["close"].shift(1) - 1.0) * 100.0
    work["pct_change"] = work["pct_change"].where(work["pct_change"].notna(), computed_pct)

    vwap_20 = (
        work["amount"].rolling(20, min_periods=15).sum()
        / work["volume"].rolling(20, min_periods=15).sum().clip(lower=1)
    )
    c154 = (work["close"] - vwap_20) / vwap_20.clip(lower=0.01)
    c156 = work["pct_change"].rolling(3, min_periods=3).sum()
    up_mask = work["pct_change"] > 0
    down_mask = work["pct_change"] <= 0
    turnover = work["turnover"]
    up_to_mean = turnover.where(up_mask).rolling(20, min_periods=5).mean()
    dn_to_mean = turnover.where(down_mask).rolling(20, min_periods=5).mean()
    c157 = up_to_mean / dn_to_mean.clip(lower=0.001)
    signed_vol = np.sign(work["pct_change"]) * work["volume"]
    c158 = -signed_vol.rolling(20, min_periods=15).sum() / work["volume"].rolling(20, min_periods=15).sum().clip(lower=1)
    p90 = work["close"].rolling(60, min_periods=40).quantile(0.9)
    p10 = work["close"].rolling(60, min_periods=40).quantile(0.1)
    c159 = (p90 - p10) / work["close"].clip(lower=0.01)
    abs_ret_over_amount = (work["pct_change"].abs() / 100.0) / work["amount"].clip(lower=1) * 1e10
    c161 = abs_ret_over_amount.rolling(20, min_periods=15).mean()
    to_20 = turnover.rolling(20, min_periods=15).mean()
    to_120 = turnover.rolling(120, min_periods=80).mean()
    to_120_std = turnover.rolling(120, min_periods=80).std()
    c162 = (to_20 - to_120) / to_120_std.clip(lower=0.001)

    out = pd.DataFrame(
        {
            "symbol": work["symbol"],
            "date": work["date"],
            "tushare_price_vs_cost_20d": c154.clip(-50, 50),
            "tushare_abnormal_3d_deviation": c156.clip(-30, 30),
            "tushare_vol_gain_20d": c157.clip(-50, 50),
            "tushare_inv_t_20d": c158.clip(-50, 50),
            "tushare_asr_60d": c159.clip(-50, 50),
            "tushare_illiq_classic_20d": c161.clip(-50, 50),
            "tushare_ato_120d": c162.clip(-50, 50),
        }
    )
    return out[out["date"].dt.date == target_date].tail(1)


def build_live_daily_derived_factor(
    bars_with_today: dict[str, pd.DataFrame],
    target_date: date,
    symbols: set[str],
) -> pd.DataFrame:
    symbol_chunks: list[pd.DataFrame] = []
    market_chunks: list[pd.DataFrame] = []
    for sym, df in bars_with_today.items():
        if df is None or df.empty:
            continue
        work = df.copy()
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        work = work.dropna(subset=["date"])
        work = work[work["date"].dt.date <= target_date].copy()
        if work.empty:
            continue
        work["symbol"] = str(sym).zfill(6)
        for col in ("pct_change", "turnover", "close"):
            if col not in work.columns:
                work[col] = np.nan
            work[col] = pd.to_numeric(work[col], errors="coerce")
        computed_pct = (pd.to_numeric(work["close"], errors="coerce") / pd.to_numeric(work["close"], errors="coerce").shift(1) - 1.0) * 100.0
        work["pct_change"] = work["pct_change"].where(work["pct_change"].notna(), computed_pct)
        market_chunks.append(work[["date", "symbol", "pct_change", "turnover", "close"]].copy())

        if str(sym).zfill(6) in symbols:
            one = _live_daily_frame_for_symbol(str(sym).zfill(6), df, target_date)
            if one is not None and not one.empty:
                symbol_chunks.append(one)

    if not symbol_chunks:
        return pd.DataFrame()
    result = pd.concat(symbol_chunks, ignore_index=True)

    if market_chunks:
        big = pd.concat(market_chunks, ignore_index=True)
        big = big.sort_values(["date", "symbol"]).reset_index(drop=True)
        market_mean_ret = big.groupby("date")["pct_change"].mean()
        big["prev_pct"] = big.groupby("symbol")["pct_change"].shift(1)
        rank_desc = big.groupby("date")["prev_pct"].rank(ascending=False, method="first")
        big["_top20"] = rank_desc <= 20
        top20_sum = big.loc[big["_top20"]].groupby("date")["pct_change"].agg(["sum", "count"])
        top20_sum["mean"] = np.where(top20_sum["count"] >= 20, top20_sum["sum"] / top20_sum["count"], np.nan)
        top20_map = top20_sum["mean"].to_dict()
        big["prev_turnover"] = big.groupby("symbol")["turnover"].shift(1)
        big["tushare_volume_sufficiency_ratio"] = (big["turnover"] / big["prev_turnover"].clip(lower=0.01)).clip(0, 20)
        big["market_ret"] = big["date"].map(market_mean_ret)
        big["down_day"] = big["market_ret"] < -0.5
        big["cond_ratio"] = np.where(
            big["down_day"],
            big["pct_change"] / big["market_ret"].clip(upper=-0.01),
            np.nan,
        )
        big["tushare_anti_drop_strength_20d"] = (
            big.groupby("symbol")["cond_ratio"]
            .transform(lambda x: x.rolling(20, min_periods=3).mean())
            .clip(-10, 10)
        )
        big["rise_flag"] = (big["close"] > big.groupby("symbol")["close"].shift(5)).astype(float)
        big["tushare_multi_wave_count_60d"] = (
            big.groupby("symbol")["rise_flag"]
            .transform(lambda x: (x.diff() == 1).rolling(60, min_periods=20).sum())
            .clip(0, 30)
        )
        merge_cols = big[big["date"].dt.date == target_date][
            [
                "symbol",
                "date",
                "tushare_volume_sufficiency_ratio",
                "tushare_anti_drop_strength_20d",
                "tushare_multi_wave_count_60d",
            ]
        ].copy()
        result["tushare_prev_top20_chase_mean"] = result["date"].map(top20_map).astype(float).clip(-20, 20)
        result = result.merge(merge_cols, on=["symbol", "date"], how="left")

    for col in LIVE_DAILY_DERIVED_COLUMNS:
        if col not in result.columns:
            result[col] = np.nan
    return result[["symbol", "date", *LIVE_DAILY_DERIVED_COLUMNS]].copy()


def attach_live_daily_derived_features(
    data: pd.DataFrame,
    bars_with_today: dict[str, pd.DataFrame],
    target_date: date,
    selected_features: set[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    needed = bool(selected_features & set(LIVE_DAILY_DERIVED_COLUMNS))
    meta: dict[str, Any] = {"required": needed, "status": "skipped"}
    if not needed:
        return data, meta

    started = time.perf_counter()
    symbols = set(data["symbol"].astype(str).str.zfill(6).tolist())
    factor = build_live_daily_derived_factor(bars_with_today, target_date, symbols)
    if factor.empty:
        meta.update({"status": "missing", "elapsed_sec": round(time.perf_counter() - started, 3)})
        return data, meta

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    factor["date"] = pd.to_datetime(factor["date"], errors="coerce")
    data = data.merge(factor, on=["symbol", "date"], how="left")
    for col in LIVE_DAILY_DERIVED_COLUMNS:
        data[f"{col}_available"] = data[col].notna().astype(np.float32)
    meta.update(
        {
            "status": "available",
            "rows": int(len(factor)),
            "coverage": round(float(data["symbol"].isin(factor["symbol"]).mean()) if len(data) else 0.0, 6),
            "elapsed_sec": round(time.perf_counter() - started, 3),
        }
    )
    return data, meta


def apply_runtime_selected_feature_gate(
    data: pd.DataFrame,
    selected_features: set[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Drop rows only for selected live inputs whose absence cannot match training.

    Daily-derived runtime factors can be structurally NaN (for example C151 when
    the rolling window has too few market-down samples). Training keeps those
    rows and `_ensure_feature_columns` fills NaN with 0.0, so live inference must
    do the same instead of using these columns as a hard row filter.
    """
    hard_gate_columns = [
        col for col in LIVE_RUNTIME_HARD_GATE_COLUMNS
        if col in selected_features
    ]
    training_fill_columns = [
        col for col in LIVE_DAILY_DERIVED_COLUMNS
        if col in selected_features
    ]
    runtime_columns = [
        col for col in LIVE_RUNTIME_VALUE_COLUMNS
        if col in selected_features
    ]
    report: dict[str, Any] = {
        "gate_columns": hard_gate_columns,
        "runtime_columns": runtime_columns,
        "hard_gate_columns": hard_gate_columns,
        "training_fill_columns": training_fill_columns,
        "before": int(len(data)),
        "dropped_by_feature": {},
        "training_fill_missing_by_feature": {},
        "mode": "hard_gate_live_inputs_training_fill_daily_derived",
    }
    out = data
    for col in hard_gate_columns:
        if col not in out.columns:
            report["dropped_by_feature"][col] = "missing_column"
            out = out.iloc[0:0].copy()
            break
        avail_col = f"{col}_available"
        if avail_col in out.columns:
            available = pd.to_numeric(out[avail_col], errors="coerce").fillna(0) > 0
        else:
            available = pd.to_numeric(out[col], errors="coerce").notna()
        before = len(out)
        out = out.loc[available].copy()
        report["dropped_by_feature"][col] = int(before - len(out))
    for col in training_fill_columns:
        if col not in data.columns:
            report["training_fill_missing_by_feature"][col] = "missing_column"
            continue
        avail_col = f"{col}_available"
        if avail_col in data.columns:
            available = pd.to_numeric(data[avail_col], errors="coerce").fillna(0) > 0
        else:
            available = pd.to_numeric(data[col], errors="coerce").notna()
        report["training_fill_missing_by_feature"][col] = int((~available).sum())
    report["after"] = int(len(out))
    report["dropped_total"] = int(report["before"] - report["after"])
    return out, report


def attach_all_factors(
    data: pd.DataFrame,
    context_frames: list[pd.DataFrame],
    config: GpuProbeConfig,
    precomputed: dict | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Attach THS, TGB, limit_pool, cross-market, cross-section, free factors."""
    timing = {}

    # Cross-section
    t0 = time.perf_counter()
    data = _add_cross_section_features(data)
    timing["cross_section_sec"] = time.perf_counter() - t0

    # Free factors
    t0 = time.perf_counter()
    data, _ = _attach_free_factor_features(data, daily_context_frames=context_frames)
    timing["free_factors_sec"] = time.perf_counter() - t0

    # Cross-market index
    t0 = time.perf_counter()
    index_frames = {}
    for symbol in GPU_PROBE_MARKET_INDEX_SYMBOLS:
        path = MARKET_INDEX_DIR / f"{symbol}.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        if "date" not in df.columns or "close" not in df.columns:
            continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        mask = (df["date"].dt.date >= config.start) & (df["date"].dt.date <= config.end)
        df = df[mask].reset_index(drop=True)
        if not df.empty:
            index_frames[symbol] = df
    if index_frames:
        factor = build_cross_market_return_factor(index_frames)
        data, _ = merge_factor_frames(data, [factor])
    else:
        for col in GPU_PROBE_CROSS_MARKET_FEATURES:
            data[col] = 0.0
            data[f"{col}_available"] = 0.0
    timing["cross_market_sec"] = time.perf_counter() - t0

    # TGB factors
    t0 = time.perf_counter()
    data, _ = _attach_tgb_factor_features(data, daily_context_frames=context_frames)
    timing["tgb_factors_sec"] = time.perf_counter() - t0

    # THS sector
    t0 = time.perf_counter()
    if precomputed and "ths_factor" in precomputed:
        ths_factor = precomputed["ths_factor"]
        if ths_factor is not None and not ths_factor.frame.empty:
            data, _ = merge_factor_frames(data, [ths_factor])
        else:
            for col in GPU_PROBE_THS_SECTOR_FEATURES:
                data[col] = 0.0
    elif TUSHARE_DIR.is_dir():
        try:
            factor = build_ths_sector_factors(TUSHARE_DIR)
            if not factor.frame.empty:
                data, _ = merge_factor_frames(data, [factor])
            else:
                for col in GPU_PROBE_THS_SECTOR_FEATURES:
                    data[col] = 0.0
        except Exception:
            for col in GPU_PROBE_THS_SECTOR_FEATURES:
                data[col] = 0.0
    else:
        for col in GPU_PROBE_THS_SECTOR_FEATURES:
            data[col] = 0.0
    timing["ths_sector_sec"] = time.perf_counter() - t0

    # Limit pool
    t0 = time.perf_counter()
    if precomputed and "limit_pool_factors" in precomputed:
        factors = precomputed.get("limit_pool_factors") or []
        if factors:
            data, _ = merge_factor_frames(data, factors)
        else:
            for col in GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES:
                data[col] = 0.0
    elif LIMIT_POOL_DIR.is_dir():
        try:
            frames = load_snapshot_bundles(LIMIT_POOL_DIR)
            factors = build_limit_pool_snapshot_factors(frames)
            if factors:
                data, _ = merge_factor_frames(data, factors)
            else:
                for col in GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES:
                    data[col] = 0.0
        except Exception:
            for col in GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES:
                data[col] = 0.0
    else:
        for col in GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES:
            data[col] = 0.0
    timing["limit_pool_sec"] = time.perf_counter() - t0

    return data, timing


# ---------------------------------------------------------------------------
# Feature alignment
# ---------------------------------------------------------------------------
def align_features(
    data: pd.DataFrame, bundle: dict
) -> tuple[np.ndarray, dict[str, int]]:
    """Align data columns to bundle's expected feature_names order.
    Returns raw feature matrix and gap statistics."""
    feature_names = bundle["feature_names"]
    unavailable = 0
    approximated = 0
    fallback = 0

    # Only truly post-close-only factors are "unavailable"
    post_close_only = set()  # None — all handled via T-1 proxy or realtime
    ths_features = set(GPU_PROBE_THS_SECTOR_FEATURES)
    limit_pool_features = set(GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES)

    for fname in feature_names:
        if fname not in data.columns:
            data[fname] = 0.0
            fallback += 1
        elif fname in post_close_only:
            unavailable += 1
        elif fname in ths_features or fname in limit_pool_features:
            approximated += 1
        else:
            approximated += 1

    raw = data[list(feature_names)].to_numpy(dtype=np.float32)
    stats = {
        "unavailable_feature_count": unavailable,
        "approximated_feature_count": approximated,
        "fallback_feature_count": fallback,
    }
    return raw, stats


# ---------------------------------------------------------------------------
# Main phases
# ---------------------------------------------------------------------------
class WarmupState:
    bundle: dict = None
    universe: list[str] = None
    all_main_board: list[str] = None
    all_bars: dict[str, pd.DataFrame] = None
    config: GpuProbeConfig = None
    ths_factor: Any = None
    name_map: dict = None
    price_cache_1430: dict[str, float] = None
    timing: dict = {}


def phase_warmup(state: WarmupState) -> dict:
    """Pre-14:57 warmup: load everything heavy."""
    timing = {}
    print("=" * 60)
    print("PHASE: WARMUP (pre-14:57)")
    print("=" * 60)

    # 1. Load bundle
    t0 = time.perf_counter()
    state.bundle = load_bundle(BUNDLE_PATH)
    timing["bundle_load_sec"] = time.perf_counter() - t0
    print(f"[1] Bundle loaded: {timing['bundle_load_sec']:.3f}s")
    print(f"    Features: {len(state.bundle['feature_names'])} total, "
          f"{len(state.bundle['selected_feature_names'])} selected")
    print(f"    Threshold: {state.bundle['threshold']:.4f}")

    # 2. Discover all main-board symbols and pre-screen with historical gate
    t0 = time.perf_counter()
    all_main_board = sorted(
        p.stem for p in DAILY_BARS_DIR.glob("*.parquet")
        if len(p.stem) == 6 and p.stem.isdigit() and _is_main_board(p.stem)
    )
    state.all_main_board = all_main_board
    state.universe = get_universe_dynamic(TODAY)
    timing["universe_sec"] = time.perf_counter() - t0
    print(f"[2] Universe (historical gate): {len(state.universe)}/{len(all_main_board)} main-board "
          f"({timing['universe_sec']:.2f}s)")
    print(f"    Final gate will re-run at 14:57 with today's realtime data")

    # 3. Load daily bars for ALL main-board (so newly active stocks aren't missed)
    state.config = build_config()
    t0 = time.perf_counter()
    state.all_bars = load_daily_bars(
        all_main_board, state.config.start, TODAY - timedelta(days=1)
    )
    timing["load_bars_sec"] = time.perf_counter() - t0
    print(f"[3] Daily bars loaded: {len(state.all_bars)} symbols ({timing['load_bars_sec']:.1f}s)")

    # 4. THS sector factor gate.
    # T-day Tushare THS daily rows are not a guaranteed 14:57 source, so the
    # executable live path never preloads them. Selected THS features are zero
    # filled by attach_all_factors instead of using post-close data.
    t0 = time.perf_counter()
    state.ths_factor = empty_ths_live_factor()
    selected_features = set(state.bundle.get("selected_feature_names", []))
    if selected_features & set(GPU_PROBE_THS_SECTOR_FEATURES):
        ths_status = "FORBIDDEN if selected; live phase will fail instead of zero-fill"
    else:
        ths_status = "not selected by live-strict bundle"
    timing["ths_precompute_sec"] = time.perf_counter() - t0
    print(f"[4] THS sector pre-compute: {ths_status} ({timing['ths_precompute_sec']:.1f}s)")

    # 5. Load name map
    state.name_map = {}
    if NAME_CACHE_PATH.exists():
        with open(NAME_CACHE_PATH, "r", encoding="utf-8") as f:
            state.name_map = json.load(f)
    print(f"[5] Name map: {len(state.name_map)} entries")

    # 6. Test snapshot connectivity (Sina API)
    t0 = time.perf_counter()
    try:
        session = requests.Session()
        session.trust_env = False
        test_syms = state.universe[:5]
        sina_test = [f"sh{s}" if s.startswith("6") else f"sz{s}" for s in test_syms]
        url = f"http://hq.sinajs.cn/list={','.join(sina_test)}"
        r = session.get(url, timeout=10, proxies=PROXY,
                        headers={"User-Agent": "Mozilla/5.0",
                                 "Referer": "https://finance.sina.com.cn/"})
        snap_ok = r.status_code == 200 and len(r.content) > 50
        timing["snapshot_test_sec"] = time.perf_counter() - t0
        print(f"[6] Snapshot test (Sina): {'OK' if snap_ok else 'FAIL'} "
              f"({timing['snapshot_test_sec']:.2f}s)")
        if snap_ok:
            lines = [l for l in r.text.strip().split(";") if "=" in l and l.strip()]
            print(f"    Sample lines: {len(lines)}")
    except Exception as e:
        timing["snapshot_test_sec"] = time.perf_counter() - t0
        print(f"[6] Snapshot test FAILED: {e}")
        snap_ok = False

    state.timing = timing
    total_warmup = sum(timing.values())
    print(f"\nWARMUP TOTAL: {total_warmup:.1f}s")
    print(f"Current time: {datetime.now().strftime('%H:%M:%S')}")

    return timing


def phase_live(state: WarmupState, *, run_mode: str = "formal") -> dict:
    """At 14:57: grab snapshot, build features, infer."""
    timing = {}
    results: dict = {
        "is_formal_valid": False,
        "output_grade": "invalid",
        "is_postclose_complete": False,
    }
    print("\n" + "=" * 60)
    print("PHASE: LIVE (14:57 snapshot)")
    print("=" * 60)
    t_total_start = time.perf_counter()
    asof_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results["asof_time"] = asof_time
    results["run_mode"] = run_mode
    print(f"Snapshot time: {asof_time} (run_mode={run_mode})")

    # P0-4: Trading day validation for formal mode
    if run_mode == "formal" and not is_trading_day(TODAY):
        print(f"FATAL: formal target_date {TODAY} is not a trading day")
        results["status"] = "non_trading_day"
        results["timing"] = timing
        return results

    # Override config to ensure alignment with training
    state.config = build_config()
    selected_features = set(state.bundle["selected_feature_names"])
    forbidden_selected = sorted(selected_features & STRICT_FORBIDDEN_SELECTED_FEATURES)
    if forbidden_selected:
        print("FATAL: selected features include fields that this live path will not fake-fill:")
        for feat in forbidden_selected:
            print(f"  - {feat}")
        results["status"] = "forbidden_selected_features"
        results["forbidden_selected_features"] = forbidden_selected
        return results
    needs_realtime_turnover = any("turnover" in feat for feat in selected_features)
    needs_realtime_net_mf = any(
        feat in selected_features
        for feat in (*MONEYFLOW_NET_FEATURES, "tushare_ff_adjusted_flow")
    )
    needs_live_limit_pool = selected_needs_live_limit_pool(selected_features)

    # 1. Fetch real-time snapshot (Sina API, for ALL main-board stocks)
    #    For formal runs: save snapshot to disk so it can be reused after 15:00.
    #    After 15:00 in formal mode: load saved 14:57 snapshot instead of fetching
    #    (Sina returns closing prices after 15:00, NOT 14:57 prices).
    SNAPSHOT_SAVE_DIR = REALTIME_OUTPUT_DIR
    SNAPSHOT_SAVE_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_save_path = SNAPSHOT_SAVE_DIR / f"sina_snapshot_1457_{TODAY_STR.replace('-', '')}.parquet"

    t0 = time.perf_counter()
    now_hm = datetime.now()

    # Validate snapshot file: only trust if contains valid quote_time in formal window
    snapshot_valid = False
    snapshot_validation_detail: dict[str, Any] = {}
    if snapshot_save_path.exists():
        try:
            saved_snap = pd.read_parquet(snapshot_save_path)

            if run_mode == "formal":
                vresult = validate_snapshot_time(
                    saved_snap, TODAY, run_mode="formal", require_captured_at=True,
                )
                snapshot_validation_detail = vresult
                snapshot_valid = vresult["valid"]
                if not snapshot_valid:
                    print(f"    WARNING: saved snapshot failed formal validation: {vresult['reason']}")
            else:
                has_qt = "quote_time" in saved_snap.columns and "quote_date" in saved_snap.columns
                if has_qt:
                    vresult = validate_snapshot_time(saved_snap, TODAY, run_mode=run_mode)
                    snapshot_validation_detail = vresult
                    snapshot_valid = vresult.get("quote_time_counts", {}).get("pct_date_match", 0) >= 0.9
                    if not snapshot_valid:
                        print(f"    WARNING: saved snapshot failed date validation: {vresult['reason']}")
                else:
                    snapshot_validation_detail = {
                        "valid": False,
                        "reason": "missing quote_time/quote_date columns",
                        "status": "saved_snapshot_unverified",
                    }
                    snapshot_valid = False
                    print("    WARNING: saved snapshot missing quote_time columns")
        except Exception as exc:
            snapshot_validation_detail = {"valid": False, "reason": f"error: {exc}", "status": "error"}
    results["snapshot_validation"] = snapshot_validation_detail

    use_saved = (
        run_mode == "formal"
        and now_hm.hour >= 15
        and snapshot_valid
    )

    if use_saved:
        snapshot = pd.read_parquet(snapshot_save_path)
        timing["snapshot_fetch_sec"] = time.perf_counter() - t0
        print(f"[1] Loaded SAVED 14:57 snapshot: {len(snapshot)} stocks "
              f"({timing['snapshot_fetch_sec']:.1f}s) — formal mode uses 14:57 data, not closing prices")
    else:
        snapshot = fetch_realtime_snapshot(universe=state.all_main_board)
        timing["snapshot_fetch_sec"] = time.perf_counter() - t0
        print(f"[1] Snapshot fetched: {len(snapshot)} stocks ({timing['snapshot_fetch_sec']:.1f}s)")

        # Formal mode: validate live-fetched snapshot time is within 14:56:30-14:58:30
        if run_mode == "formal" and not snapshot.empty:
            live_vresult = validate_snapshot_time(snapshot, TODAY, run_mode="formal")
            results["live_snapshot_validation"] = live_vresult
            if not live_vresult["valid"]:
                print(f"    FATAL: live snapshot failed formal time validation: {live_vresult['reason']}")
                results["status"] = live_vresult.get("status", "snapshot_time_invalid")
                results["timing"] = timing
                return results

        # Save snapshot to disk for formal runs ONLY within the formal window
        if run_mode == "formal" and not snapshot.empty:
            now_sec = now_hm.hour * 3600 + now_hm.minute * 60 + now_hm.second
            formal_save_ok = (14 * 3600 + 56 * 60 + 30) <= now_sec <= (14 * 3600 + 58 * 60 + 30)
            if formal_save_ok:
                try:
                    snapshot.to_parquet(snapshot_save_path, index=False)
                    print(f"    Snapshot saved to {snapshot_save_path}")
                except Exception as exc:
                    print(f"    WARNING: failed to save snapshot: {exc}")
            else:
                print(f"    Snapshot NOT saved (current time {now_hm:%H:%M:%S} outside formal save window)")
        elif run_mode != "formal" and not snapshot.empty:
            _nonf_snap_name = f"sina_snapshot_{run_mode}_{TODAY_STR.replace('-', '')}_{now_hm.strftime('%H%M%S')}.parquet"
            _nonf_snap_path = SNAPSHOT_SAVE_DIR / _nonf_snap_name
            try:
                snapshot.to_parquet(_nonf_snap_path, index=False)
                print(f"    Snapshot saved ({run_mode}) to {_nonf_snap_path}")
            except Exception as exc:
                print(f"    WARNING: failed to save {run_mode} snapshot: {exc}")

        # For formal mode after 15:00 with no saved snapshot: REFUSE
        if run_mode == "formal" and now_hm.hour >= 15 and not use_saved:
            print(
                "FATAL: formal mode after 15:00 but no saved 14:57 snapshot found. "
                "Sina returns closing prices after 15:00, which cannot be used for formal 14:57 output. "
                "Please ensure the server is running before 14:57 so the auto-run captures the snapshot."
            )
            results["status"] = "no_saved_1457_snapshot"
            results["timing"] = timing
            return results

    if snapshot.empty:
        print("FATAL: Empty snapshot. Aborting.")
        results["status"] = "snapshot_empty"
        results["timing"] = timing
        return results

    # Postclose snapshot validation: quote_date must match today, key fields non-null
    if run_mode == "postclose" and not snapshot.empty:
        postclose_checks: dict[str, Any] = {"data_fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        results["postclose_checks"] = postclose_checks
        # Validate quote_date
        if "quote_date" in snapshot.columns:
            qd = snapshot["quote_date"].astype(str).str.strip()
            qd_match = (qd == TODAY_STR).sum()
            qd_total = len(qd[qd != ""])
            postclose_checks["quote_date_match"] = int(qd_match)
            postclose_checks["quote_date_total"] = int(qd_total)
            postclose_checks["quote_date_pct"] = round(qd_match / max(qd_total, 1), 4)
            if qd_match < qd_total * 0.90:
                print(f"FATAL: postclose snapshot quote_date mismatch: "
                      f"{qd_match}/{qd_total} match {TODAY_STR}")
                results["status"] = "postclose_quote_date_mismatch"
                results["timing"] = timing
                return results
        else:
            print("FATAL: postclose snapshot missing quote_date column")
            results["status"] = "postclose_snapshot_no_quote_date"
            results["timing"] = timing
            return results
        # Validate quote_time near 15:00 (allow 14:59:00 - 15:01:00)
        if "quote_time" in snapshot.columns:
            qt = snapshot["quote_time"].astype(str).str.strip()
            qt_valid = qt[qt.str.fullmatch(r"\d{2}:\d{2}:\d{2}")]
            if len(qt_valid) > 0:
                postclose_checks["quote_time_min"] = qt_valid.min()
                postclose_checks["quote_time_max"] = qt_valid.max()
            else:
                postclose_checks["quote_time_min"] = None
                postclose_checks["quote_time_max"] = None
        # Validate key field coverage
        key_fields = ["latest_price", "open", "high", "low", "volume", "amount"]
        for fld in key_fields:
            if fld in snapshot.columns:
                valid_count = pd.to_numeric(snapshot[fld], errors="coerce").notna().sum()
                postclose_checks[f"{fld}_coverage"] = round(int(valid_count) / max(len(snapshot), 1), 4)
            else:
                postclose_checks[f"{fld}_coverage"] = 0.0
        price_coverage = postclose_checks.get("latest_price_coverage", 0)
        if price_coverage < 0.90:
            print(f"FATAL: postclose snapshot latest_price coverage too low: {price_coverage:.1%}")
            results["status"] = "postclose_snapshot_low_coverage"
            results["timing"] = timing
            return results
        print(f"    Postclose snapshot validated: quote_date_match={postclose_checks['quote_date_pct']:.1%}, "
              f"price_coverage={price_coverage:.1%}")

    # Record snapshot provenance metadata
    if use_saved:
        results["snapshot_source"] = "saved_parquet"
    else:
        results["snapshot_source"] = "live_sina"
    if "captured_at" in snapshot.columns:
        captured_vals = snapshot["captured_at"].dropna().unique()
        results["snapshot_captured_at"] = str(captured_vals[0]) if len(captured_vals) > 0 else "unknown"
    if "quote_time" in snapshot.columns:
        qt_vals = snapshot["quote_time"].astype(str).str.strip()
        qt_nonempty = qt_vals[qt_vals != ""]
        if len(qt_nonempty) > 0:
            results["snapshot_quote_time_sample"] = qt_nonempty.iloc[0]

    # 2. Compute turnover for gate (needs float_share, fast)
    t0 = time.perf_counter()
    free_share_map = {}
    float_share_map = {}
    db_dir = TUSHARE_DIR / "daily_basic"
    if db_dir.is_dir():
        db_files = sorted(db_dir.glob("*.parquet"))
        for f in db_files[-3:]:
            try:
                dbdf = pd.read_parquet(f, columns=["ts_code", "free_share"])
                for _, r in dbdf.iterrows():
                    sym = str(r["ts_code"]).split(".")[0]
                    fs = r.get("free_share")
                    if pd.notna(fs) and fs > 0:
                        free_share_map[sym] = float(fs)
            except Exception:
                pass
        needed_symbols = set(state.all_main_board)
        for f in reversed(db_files):
            try:
                dbdf = pd.read_parquet(f, columns=["ts_code", "float_share"])
                for _, r in dbdf.iterrows():
                    sym = str(r["ts_code"]).split(".")[0]
                    if sym in float_share_map:
                        continue
                    fs = r.get("float_share")
                    if pd.notna(fs) and fs > 0:
                        float_share_map[sym] = float(fs)
            except Exception:
                continue
            if needed_symbols:
                covered = len(needed_symbols.intersection(float_share_map))
                if covered >= max(1, int(len(needed_symbols) * 0.98)):
                    break

    # Compute normal turnover from snapshot volume / float_share
    # turnover_pct = realtime_volume / (float_share * 10000) * 100
    # float_share unit: 万股; volume unit: 股
    turnover_map = {}
    turnover_source = "volume/float_share"
    if not snapshot.empty and float_share_map:
        for _, row in snapshot.iterrows():
            sym = row.get("symbol", "")
            vol = row.get("volume")
            if sym and pd.notna(vol) and vol > 0 and sym in float_share_map:
                fs = float_share_map[sym]
                turnover_map[sym] = vol / (fs * 10000.0) * 100.0

    timing["turnover_sec"] = time.perf_counter() - t0
    print(f"    Turnover ({turnover_source}): {len(turnover_map)}/{len(state.all_main_board)} stocks "
          f"(float_share_cache={len(float_share_map)}, free_share_cache={len(free_share_map)}) "
          f"({timing['turnover_sec']:.1f}s)")

    # 2b. Fetch live limit-up / failed-board pools at scoring time.
    #     For formal mode: save to disk at 14:57, reload from disk after 15:00.
    t0 = time.perf_counter()
    LIMIT_POOL_SAVE_DIR = REALTIME_OUTPUT_DIR
    LIMIT_POOL_SAVE_DIR.mkdir(parents=True, exist_ok=True)
    limit_pool_save_path = LIMIT_POOL_SAVE_DIR / f"limit_pool_1457_{TODAY_STR.replace('-', '')}.pkl"

    now_sec_lp = now_hm.hour * 3600 + now_hm.minute * 60 + now_hm.second
    use_saved_limit_pool = (
        run_mode == "formal"
        and now_sec_lp >= 15 * 3600
        and limit_pool_save_path.exists()
    )

    if use_saved_limit_pool:
        import pickle as _pkl
        with open(limit_pool_save_path, "rb") as _f:
            _saved_lp = _pkl.load(_f)
        limit_pool_factors = _saved_lp["factors"]
        limit_pool_meta = _saved_lp["meta"]
        print(f"[2b] Loaded SAVED 14:57 limit pool: {limit_pool_meta.get('counts')} "
              f"(captured_at={limit_pool_meta.get('captured_at')})")
    else:
        limit_pool_factors, limit_pool_meta = fetch_live_limit_pool_bundle(
            TODAY, selected_features=selected_features
        )
        # Save limit pool in formal window for later replay
        if run_mode == "formal" and limit_pool_meta.get("status") == "available":
            lp_cap_str = limit_pool_meta.get("captured_at", "")
            try:
                _lp_cap_dt = datetime.strptime(lp_cap_str, "%Y-%m-%d %H:%M:%S")
                _lp_cap_sec = _lp_cap_dt.hour * 3600 + _lp_cap_dt.minute * 60 + _lp_cap_dt.second
                if (14 * 3600 + 56 * 60 + 30) <= _lp_cap_sec <= (14 * 3600 + 58 * 60 + 30):
                    import pickle as _pkl
                    with open(limit_pool_save_path, "wb") as _f:
                        _pkl.dump({"factors": limit_pool_factors, "meta": limit_pool_meta}, _f)
                    print(f"    Limit pool saved to {limit_pool_save_path}")
            except (ValueError, TypeError):
                pass

    timing["limit_pool_live_sec"] = time.perf_counter() - t0
    results["limit_pool_live"] = limit_pool_meta
    if needs_live_limit_pool:
        print(
            "    Live limit pool: "
            f"status={limit_pool_meta.get('status')}, "
            f"counts={limit_pool_meta.get('counts')}, "
            f"compat_rows={limit_pool_meta.get('tushare_compat_rows')}"
        )
        if limit_pool_meta.get("status") != "available" or not limit_pool_factors:
            print("FATAL: selected features require live limit/failed-board pool, but it was not available.")
            if limit_pool_meta.get("error"):
                print(f"    Error: {limit_pool_meta.get('error')}")
            results["status"] = "live_limit_pool_missing"
            results["timing"] = timing
            return results
        if selected_features & LIVE_TUSHARE_LIMIT_FEATURES and limit_pool_meta.get("tushare_compat_rows", 0) <= 0:
            print("FATAL: selected Tushare limit-list features require live pool compatibility rows.")
            results["status"] = "live_tushare_limit_compat_missing"
            results["timing"] = timing
            return results

    # P0-5: Validate limit pool captured_at for formal mode
    if run_mode == "formal" and needs_live_limit_pool:
        lp_captured = limit_pool_meta.get("captured_at")
        if not lp_captured:
            print("FATAL: formal limit pool has no captured_at timestamp")
            results["status"] = "live_limit_pool_unverified"
            results["limit_pool_time_status"] = "missing_captured_at"
            results["timing"] = timing
            return results
        try:
            lp_cap = datetime.strptime(lp_captured, "%Y-%m-%d %H:%M:%S")
            lp_sec = lp_cap.hour * 3600 + lp_cap.minute * 60 + lp_cap.second
            lp_window_start = 14 * 3600 + 56 * 60 + 30  # 14:56:30
            lp_window_end = 14 * 3600 + 58 * 60 + 30    # 14:58:30
            if lp_window_start <= lp_sec <= lp_window_end:
                results["limit_pool_time_status"] = "verified"
            elif use_saved_limit_pool:
                results["limit_pool_time_status"] = "verified"
            else:
                print(f"FATAL: formal limit pool captured_at {lp_captured} "
                      f"outside allowed window 14:56:30-14:58:30 and no saved 14:57 pool available")
                results["status"] = "limit_pool_time_invalid"
                results["limit_pool_time_status"] = "outside_formal_window"
                results["timing"] = timing
                return results
        except (ValueError, TypeError):
            print(f"FATAL: cannot parse limit pool captured_at: {lp_captured}")
            results["status"] = "live_limit_pool_unverified"
            results["limit_pool_time_status"] = "parse_error"
            results["timing"] = timing
            return results

    # 3. Apply realtime short_only gate using today's snapshot data
    t0 = time.perf_counter()
    required_snapshot_cols = ["open", "high", "low", "latest_price", "volume", "amount"]
    valid_realtime = snapshot["latest_price"] > 0
    for col in required_snapshot_cols:
        valid_realtime &= pd.to_numeric(snapshot[col], errors="coerce").notna()
    valid_realtime &= pd.to_numeric(snapshot["volume"], errors="coerce") > 0
    valid_realtime &= pd.to_numeric(snapshot["amount"], errors="coerce") > 0
    valid_snapshot = snapshot[valid_realtime].copy()

    # Exclude ST stocks — training excludes ST (exclude_st=True in QualityConfig),
    # so scoring ST stocks produces meaningless probabilities.
    if "name" in valid_snapshot.columns:
        st_mask = valid_snapshot["name"].astype(str).str.contains("ST|退", regex=True, na=False)
        n_st_excluded = st_mask.sum()
        valid_snapshot = valid_snapshot[~st_mask].copy()
        if n_st_excluded:
            print(f"    ST excluded from snapshot: {n_st_excluded} stocks")

    realtime_universe = apply_realtime_gate(valid_snapshot, state.all_bars, turnover_map)
    historical_only = set(state.universe) - set(realtime_universe)
    new_today = set(realtime_universe) - set(state.universe)
    if run_mode == "formal":
        state.universe = sorted(realtime_universe)
    else:
        state.universe = sorted(set(state.universe) | set(realtime_universe))
    timing["realtime_gate_sec"] = time.perf_counter() - t0
    print(f"[3] Realtime gate: {len(realtime_universe)} passed today "
          f"(+{len(new_today)} new, -{len(historical_only)} dropped from historical) "
          f"→ final universe {len(state.universe)} ({timing['realtime_gate_sec']:.1f}s)")

    # 3b. Filter snap_universe to final gated universe
    snap_universe = valid_snapshot[valid_snapshot["symbol"].isin(state.universe)].copy()
    if needs_realtime_turnover:
        before_turnover_gate = len(snap_universe)
        snap_universe = snap_universe[snap_universe["symbol"].isin(turnover_map)].copy()
        dropped_turnover = before_turnover_gate - len(snap_universe)
        if dropped_turnover:
            print(f"    Strict turnover gate dropped {dropped_turnover} stocks without realtime turnover.")
        if snap_universe.empty:
            print("FATAL: selected features require realtime turnover, but no stocks have it.")
            results["status"] = "realtime_turnover_missing"
            results["timing"] = timing
            return results
    print(f"    Valid stocks with snapshot: {len(snap_universe)}/{len(state.universe)}")

    # 3c. Now fetch net_mf only for the gated universe — skip entirely if not needed
    t0 = time.perf_counter()
    net_mf_map: dict[str, float] = {}
    if needs_realtime_net_mf:
        net_mf_map = fetch_net_mf_batch(state.universe)
        timing["net_mf_fetch_sec"] = time.perf_counter() - t0
        print(f"[3c] Net MF (f62): {len(net_mf_map)}/{len(state.universe)} stocks "
              f"({timing['net_mf_fetch_sec']:.1f}s)")
        if len(net_mf_map) == 0:
            print("    WARNING: push2 returned no net_mf (normal if market closed)")
            print("FATAL: selected features require realtime net_mf, but push2 returned no data.")
            results["status"] = "realtime_net_mf_missing"
            results["timing"] = timing
            return results
    else:
        timing["net_mf_fetch_sec"] = 0.0
        print("[3c] Net MF (f62): SKIPPED (not in selected features)")

    # 4. Inject today's bar from snapshot (only for gated universe)
    t0 = time.perf_counter()
    gated_set = set(state.universe)
    gated_bars = {sym: df for sym, df in state.all_bars.items() if sym in gated_set}
    bars_with_today = inject_snapshot_bar(
        gated_bars, snap_universe, TODAY,
        turnover_map=turnover_map if turnover_map else None,
        require_realtime_turnover=needs_realtime_turnover,
    )
    injected = sum(1 for sym in bars_with_today
                   if (bars_with_today[sym]["date"].dt.date == TODAY).any())
    timing["inject_bar_sec"] = time.perf_counter() - t0
    print(f"[4] Injected today's bar: {injected} stocks ({timing['inject_bar_sec']:.2f}s)")
    if turnover_map:
        print(f"    Real turnover injected: {sum(1 for s in bars_with_today if s in turnover_map)}")

    # 4b. Build full-market context: inject 14:57 snapshot into ALL main-board bars,
    #     then build context frames. Training uses ~3063 symbols for market/emotion
    #     factors — live must match. scoring_bars (step 4) only covers gated universe;
    #     market_context_bars covers everyone.
    t0_ctx = time.perf_counter()
    non_gated_syms = [s for s in state.all_bars if s not in gated_set]
    market_context_bars = {sym: state.all_bars[sym].copy() for sym in non_gated_syms}
    market_context_bars = inject_snapshot_bar(
        market_context_bars, valid_snapshot, TODAY,
        turnover_map=turnover_map if turnover_map else None,
        require_realtime_turnover=False,
    )
    market_ctx_injected = sum(
        1 for sym in market_context_bars
        if (market_context_bars[sym]["date"].dt.date == TODAY).any()
    )
    full_market_context_frames: list[pd.DataFrame] = []
    for sym in non_gated_syms:
        if sym in market_context_bars:
            bars_df = market_context_bars[sym]
        else:
            bars_df = state.all_bars[sym]
        ctx = _daily_context_slice(bars_df, symbol=sym, start=state.config.start, end=state.config.end)
        if not ctx.empty:
            full_market_context_frames.append(ctx)
    timing["full_market_context_sec"] = time.perf_counter() - t0_ctx
    results["market_context_symbols"] = len(non_gated_syms)
    results["market_context_injected"] = market_ctx_injected
    results["market_context_frames"] = len(full_market_context_frames)
    print(f"[4b] Full market context: {len(non_gated_syms)} non-gated symbols, "
          f"{market_ctx_injected} injected with today's snapshot → "
          f"{len(full_market_context_frames)} context frames ({timing['full_market_context_sec']:.1f}s)")

    # 5. Build symbol features (the main bottleneck)
    print("[5] Building symbol features...")
    data, context_frames, sym_timing = build_symbol_features(
        bars_with_today, state.config, TODAY
    )
    # Merge full market context into context_frames for emotion/market factors
    context_frames = context_frames + full_market_context_frames
    timing.update(sym_timing)
    print(f"    Result: {len(data)} rows, {data.shape[1] if not data.empty else 0} columns")

    if data.empty:
        print("FATAL: No features computed. Aborting.")
        results["status"] = "no_features"
        results["timing"] = timing
        return results

    # 6. Attach factors
    print("[6] Attaching factors...")
    precomputed = {
        "ths_factor": state.ths_factor,
        "limit_pool_factors": limit_pool_factors,
    }
    data, factor_timing = attach_all_factors(
        data, context_frames, state.config, precomputed=precomputed
    )
    timing.update(factor_timing)
    print(f"    After factors: {data.shape[1]} columns")

    # 7. Attach moneyflow breakdown ratios from T-1 tushare cache
    #    These features CANNOT be computed from push2 realtime data.
    #    Only load if any of these columns are in selected_features.
    t0 = time.perf_counter()
    mf_ratio_columns = {
        "tushare_net_mf_amount", "tushare_lg_buy_sell_ratio",
        "tushare_elg_buy_sell_ratio", "tushare_mf_strength",
        "tushare_sm_sell_pressure", "tushare_main_force_divergence",
        "tushare_mf_flow_intensity",
    }
    needs_mf_ratios = bool(selected_features & mf_ratio_columns)
    mf_dir = TUSHARE_DIR / "moneyflow"
    mf_ratio_count = 0
    if needs_mf_ratios and mf_dir.is_dir() and "symbol" in data.columns:
        mf_files = sorted(mf_dir.glob("*.parquet"))[-3:]
        mf_dfs = []
        for f in mf_files:
            try:
                mf_dfs.append(pd.read_parquet(f))
            except Exception:
                pass
        if mf_dfs:
            mf_df = pd.concat(mf_dfs, ignore_index=True)
            mf_df["symbol"] = mf_df["ts_code"].str.split(".").str[0]
            # Keep only latest date per symbol
            mf_df["_date"] = pd.to_datetime(mf_df["trade_date"], format="%Y%m%d", errors="coerce")
            mf_df = mf_df.sort_values("_date").drop_duplicates("symbol", keep="last")

            for col in ("net_mf_amount", "buy_lg_amount", "sell_lg_amount",
                        "buy_elg_amount", "sell_elg_amount", "buy_sm_amount",
                        "sell_sm_amount", "buy_md_amount", "sell_md_amount"):
                mf_df[col] = pd.to_numeric(mf_df.get(col), errors="coerce").fillna(0.0)

            # Compute ratios
            big_buy = mf_df["buy_lg_amount"] + mf_df["buy_elg_amount"]
            big_sell = mf_df["sell_lg_amount"] + mf_df["sell_elg_amount"]
            lg_ratio = (mf_df["buy_lg_amount"] / np.maximum(mf_df["sell_lg_amount"], 100.0)).clip(upper=50.0)
            elg_ratio = (mf_df["buy_elg_amount"] / np.maximum(mf_df["sell_elg_amount"], 100.0)).clip(upper=50.0)
            total_buy = mf_df["buy_sm_amount"] + mf_df["buy_md_amount"] + mf_df["buy_lg_amount"] + mf_df["buy_elg_amount"]

            mf_ratios = pd.DataFrame({
                "symbol": mf_df["symbol"].values,
                "tushare_net_mf_amount": mf_df["net_mf_amount"].values,
                "tushare_lg_buy_sell_ratio": lg_ratio.values,
                "tushare_elg_buy_sell_ratio": elg_ratio.values,
                "tushare_mf_strength": ((big_buy - big_sell) / np.maximum(big_buy + big_sell, 1.0)).values,
                "tushare_sm_sell_pressure": (mf_df["sell_sm_amount"] / np.maximum(mf_df["buy_sm_amount"] + mf_df["sell_sm_amount"], 1.0)).values,
                "tushare_main_force_divergence": (lg_ratio - elg_ratio).abs().values,
                "tushare_mf_flow_intensity": (mf_df["net_mf_amount"] / np.maximum(total_buy, 1.0)).values,
            }).set_index("symbol")

            # Assign to data by symbol (no date join — T-1 lag is declared)
            sym_col = data["symbol"]
            for col in mf_ratios.columns:
                if col in data.columns:
                    mask = sym_col.isin(mf_ratios.index)
                    data.loc[mask, col] = sym_col[mask].map(mf_ratios[col]).values
                    mf_ratio_count += int(mask.sum())
                else:
                    data[col] = sym_col.map(mf_ratios[col]).fillna(0.0).values
                    mf_ratio_count += int(sym_col.isin(mf_ratios.index).sum())

    timing["tushare_mf_ratios_sec"] = time.perf_counter() - t0
    if needs_mf_ratios:
        print(f"[7] Moneyflow ratios (T-1 tushare): {mf_ratio_count} cells assigned "
              f"({timing['tushare_mf_ratios_sec']:.1f}s)")
    else:
        print(f"[7] Moneyflow ratios: SKIPPED (not in selected features)")

    # 8. Override with real-time data where available
    t0 = time.perf_counter()
    mf_overridden = 0
    # Override net_mf_amount with today's real-time push2 f62
    if net_mf_map and "symbol" in data.columns:
        sym_col = data["symbol"]
        for sym, net_yuan in net_mf_map.items():
            mask = sym_col == sym
            if mask.any():
                data.loc[mask, "tushare_net_mf_amount"] = net_yuan / 10000.0
                mf_overridden += 1

    # Override tushare_volume_ratio with today's volume / historical avg
    vol_ratio_count = 0
    if "symbol" in data.columns:
        for idx, row in data.iterrows():
            sym = row["symbol"]
            if sym in bars_with_today:
                bdf = bars_with_today[sym]
                vols = bdf["volume"].dropna()
                if len(vols) >= 6:
                    today_vol = vols.iloc[-2]
                    avg_vol = vols.iloc[-7:-2].mean()
                    if avg_vol > 0:
                        data.at[idx, "tushare_volume_ratio"] = today_vol / avg_vol
                        vol_ratio_count += 1

    # Override tushare_up/down_limit_distance from stk_limit cache (T-1, stable)
    limit_count = 0
    if "symbol" in data.columns:
        stk_limit_dir = TUSHARE_DIR / "stk_limit"
        limit_price_map = {}
        if stk_limit_dir.is_dir():
            stk_files = sorted(stk_limit_dir.glob("*.parquet"))[-3:]
            for f in stk_files:
                try:
                    ldf = pd.read_parquet(f, columns=["ts_code", "up_limit", "down_limit"])
                    for _, r in ldf.iterrows():
                        sym = str(r["ts_code"]).split(".")[0]
                        up = pd.to_numeric(r.get("up_limit"), errors="coerce")
                        dn = pd.to_numeric(r.get("down_limit"), errors="coerce")
                        if pd.notna(up) and pd.notna(dn) and up > 0:
                            limit_price_map[sym] = (float(up), float(dn))
                except Exception:
                    pass
        if limit_price_map:
            for idx, row in data.iterrows():
                sym = row["symbol"]
                if sym in limit_price_map:
                    up_lim, dn_lim = limit_price_map[sym]
                    implied = (up_lim + dn_lim) / 2.0
                    if implied > 0.01:
                        data.at[idx, "tushare_up_limit_distance"] = (up_lim - implied) / implied
                        data.at[idx, "tushare_down_limit_distance"] = (implied - dn_lim) / implied
                        data.at[idx, "tushare_limit_range"] = (up_lim - dn_lim) / implied
                        limit_count += 1

    # Recompute ff_adjusted_flow with real-time net_mf
    if free_share_map and "symbol" in data.columns:
        sym_col = data["symbol"]
        data["tushare_free_share"] = sym_col.map(free_share_map)
        if "tushare_net_mf_amount" in data.columns:
            fs = data["tushare_free_share"].fillna(0)
            close_vals = data.get("close", pd.Series(0, index=data.index))
            denom = np.maximum(fs * close_vals.fillna(0), 1.0)
            data["tushare_ff_adjusted_flow"] = (
                data["tushare_net_mf_amount"].fillna(0) / denom
            ).clip(-10.0, 10.0)

    timing["realtime_override_sec"] = time.perf_counter() - t0
    print(f"[8] Real-time override: net_mf={mf_overridden}, vol_ratio={vol_ratio_count}, "
          f"limit={limit_count} ({timing['realtime_override_sec']:.2f}s)")

    # 8b. Attach selected live-strict Tushare-compatible features.
    t0 = time.perf_counter()
    strict_live_meta: dict[str, Any] = {}
    data, chip_meta = attach_live_chip_t1_features(
        data, state.all_bars, TODAY, selected_features
    )
    strict_live_meta["chip_t1"] = chip_meta
    if chip_meta.get("required") and chip_meta.get("status") != "available":
        print(f"FATAL: selected chip T-1 features unavailable: {chip_meta}")
        results["status"] = "chip_t1_missing"
        results["timing"] = timing
        results["strict_live_factors"] = strict_live_meta
        return results

    data, snap_factor_meta = attach_live_intraday_snapshot_features(
        data, snap_universe, selected_features
    )
    strict_live_meta["intraday_snapshot"] = snap_factor_meta
    if snap_factor_meta.get("required") and snap_factor_meta.get("status") != "available":
        print(f"FATAL: selected realtime VWAP features unavailable: {snap_factor_meta}")
        results["status"] = "intraday_snapshot_missing"
        results["timing"] = timing
        results["strict_live_factors"] = strict_live_meta
        return results

    snapshot_prices = {}
    for _, row in snap_universe.iterrows():
        sym = str(row["symbol"]).zfill(6)
        price = row.get("latest_price")
        if pd.notna(price) and float(price) > 0:
            snapshot_prices[sym] = float(price)

    data, minute_meta = attach_live_minute_features(
        data, TODAY, selected_features,
        price_cache_1430=state.price_cache_1430,
        snapshot_prices=snapshot_prices,
        run_mode=run_mode,
    )
    strict_live_meta["intraday_minute"] = minute_meta
    if run_mode == "formal":
        if minute_meta.get("required") and minute_meta.get("status") != "available":
            print(f"FATAL: formal mode requires available (not approximate) 5-min data: {minute_meta}")
            results["status"] = "intraday_minute_missing"
            results["timing"] = timing
            results["strict_live_factors"] = strict_live_meta
            return results
        if minute_meta.get("required") and minute_meta.get("coverage", 0) < 0.95:
            print(f"FATAL: formal last_30min coverage too low: {minute_meta.get('coverage')}")
            results["status"] = "formal_last30min_low_coverage"
            results["timing"] = timing
            results["strict_live_factors"] = strict_live_meta
            return results
    elif run_mode == "postclose":
        if minute_meta.get("required") and minute_meta.get("status") != "available":
            print(f"FATAL: postclose requires available last_30min data: {minute_meta}")
            results["status"] = "intraday_minute_missing"
            results["timing"] = timing
            results["strict_live_factors"] = strict_live_meta
            return results
        if minute_meta.get("required") and minute_meta.get("coverage", 0) < 0.95:
            print(f"FATAL: postclose last_30min coverage too low: {minute_meta.get('coverage')}")
            results["status"] = "postclose_last30min_low_coverage"
            results["timing"] = timing
            results["strict_live_factors"] = strict_live_meta
            return results
    else:
        if minute_meta.get("required") and minute_meta.get("status") not in ("available", "approximate"):
            print(f"FATAL: selected 5-minute intraday features unavailable: {minute_meta}")
            results["status"] = "intraday_minute_missing"
            results["timing"] = timing
            results["strict_live_factors"] = strict_live_meta
            return results

    data, daily_meta = attach_live_daily_derived_features(
        data, bars_with_today, TODAY, selected_features
    )
    strict_live_meta["daily_derived"] = daily_meta
    if daily_meta.get("required") and daily_meta.get("status") != "available":
        print(f"FATAL: selected live daily-derived features unavailable: {daily_meta}")
        results["status"] = "daily_derived_missing"
        results["timing"] = timing
        results["strict_live_factors"] = strict_live_meta
        return results

    data, runtime_gate = apply_runtime_selected_feature_gate(data, selected_features)
    strict_live_meta["runtime_gate"] = runtime_gate
    timing["strict_live_selected_features_sec"] = time.perf_counter() - t0
    results["strict_live_factors"] = strict_live_meta
    print(
        "[8b] Strict live selected factors: "
        f"chip={chip_meta.get('status')} "
        f"minute={minute_meta.get('status')} "
        f"vwap={snap_factor_meta.get('status')} "
        f"daily={daily_meta.get('status')} "
        f"gate {runtime_gate.get('before')}->{runtime_gate.get('after')} "
        f"({timing['strict_live_selected_features_sec']:.1f}s)"
    )
    if data.empty:
        print(f"FATAL: runtime selected-feature gate dropped all rows: {runtime_gate}")
        results["status"] = "runtime_selected_feature_gate_empty"
        results["timing"] = timing
        return results

    # 9. Ensure all feature columns exist
    t0 = time.perf_counter()
    columns_before_ensure = set(data.columns)
    allowed_missing_selected: set[str] = set()
    missing_selected_before_ensure = sorted(
        feat for feat in selected_features
        if feat not in columns_before_ensure and feat not in allowed_missing_selected
    )
    if missing_selected_before_ensure:
        print("FATAL: selected features would be zero-filled by _ensure_feature_columns:")
        for feat in missing_selected_before_ensure[:40]:
            print(f"  - {feat}")
        if len(missing_selected_before_ensure) > 40:
            print(f"  ... {len(missing_selected_before_ensure) - 40} more")
        results["status"] = "selected_feature_missing_before_ensure"
        results["timing"] = timing
        results["missing_selected_features"] = missing_selected_before_ensure
        return results
    data = _ensure_feature_columns(data)
    timing["ensure_cols_sec"] = time.perf_counter() - t0

    # 10. Exclude limit-up stocks
    if "limit_up_like" in data.columns:
        before = len(data)
        data = data[data["limit_up_like"] != 1].copy()
        print(f"[10] Limit-up filter: {before} -> {len(data)} stocks")
    else:
        print(f"[10] No limit_up_like column, keeping all {len(data)} stocks")

    # 11. Align features to bundle expectations
    t0 = time.perf_counter()
    raw_features, gap_stats = align_features(data, state.bundle)
    timing["align_features_sec"] = time.perf_counter() - t0
    print(f"[11] Feature alignment: {raw_features.shape}")
    print(f"    unavailable: {gap_stats['unavailable_feature_count']}")
    print(f"    approximated: {gap_stats['approximated_feature_count']}")
    print(f"    fallback: {gap_stats['fallback_feature_count']}")

    # 11. Check alignment
    expected_features = len(state.bundle["feature_names"])
    actual_features = raw_features.shape[1]
    if actual_features != expected_features:
        print(f"FATAL: Feature count mismatch: {actual_features} != {expected_features}")
        results["status"] = "feature_mismatch"
        results["timing"] = timing
        results["gap_stats"] = gap_stats
        return results

    # 12. Run inference
    t0 = time.perf_counter()
    prob = run_inference(state.bundle, raw_features)
    timing["inference_sec"] = time.perf_counter() - t0
    print(f"[12] Inference: {len(prob)} predictions ({timing['inference_sec']:.2f}s)")

    total_time = time.perf_counter() - t_total_start
    timing["total_live_sec"] = total_time
    print(f"\nLIVE TOTAL: {total_time:.1f}s {'<180s OK' if total_time < 180 else '>180s OVER'}")

    # 13. Build output with tradability gates
    symbols = data["symbol"].values if "symbol" in data.columns else np.array([""] * len(data))
    snap_lookup = snap_universe.set_index("symbol")

    # Get names from snapshot (has current ST markers) + name_map fallback
    snap_names = {}
    for _, r in snap_universe.iterrows():
        snap_names[r["symbol"]] = r.get("name", "")
    names = [snap_names.get(s, state.name_map.get(s, "")) for s in symbols]

    out_df = pd.DataFrame({
        "symbol": symbols,
        "name": names,
        "probability": prob,
        "asof_time": asof_time,
        "latest_price": [snap_lookup.loc[s, "latest_price"] if s in snap_lookup.index else np.nan
                         for s in symbols],
        "prev_close": [snap_lookup.loc[s, "prev_close"] if s in snap_lookup.index else np.nan
                       for s in symbols],
        "pct_change": [snap_lookup.loc[s, "pct_change"] if s in snap_lookup.index else np.nan
                       for s in symbols],
        "turnover_today": [turnover_map.get(s, np.nan) for s in symbols],
        "net_mf_available": [1 if s in net_mf_map else 0 for s in symbols],
    })

    # --- TRADABILITY GATES ---
    def _limit_pct(sym, name):
        s = str(sym).zfill(6)
        is_st = bool(pd.notna(name) and ("ST" in str(name).upper() or "退" in str(name)))
        if s.startswith(("300", "301", "688")):
            return 20.0
        elif s.startswith(("8", "4")):
            return 30.0
        else:
            return 5.0 if is_st else 10.0

    out_df["is_st"] = out_df["name"].apply(
        lambda n: bool(pd.notna(n) and ("ST" in str(n).upper() or "退" in str(n)))
    )
    out_df["board_limit_pct"] = [_limit_pct(s, n) for s, n in zip(out_df["symbol"], out_df["name"])]
    out_df["up_limit_price"] = (out_df["prev_close"] * (1 + out_df["board_limit_pct"] / 100)).round(2)
    out_df["down_limit_price"] = (out_df["prev_close"] * (1 - out_df["board_limit_pct"] / 100)).round(2)
    out_df["is_limit_up"] = (out_df["latest_price"] >= out_df["up_limit_price"] * 0.995)
    out_df["is_limit_down"] = (out_df["latest_price"] <= out_df["down_limit_price"] * 1.005)
    out_df["is_suspended"] = (out_df["latest_price"].isna()) | (out_df["latest_price"] <= 0)

    out_df["tradable"] = ~(
        out_df["is_st"] | out_df["is_limit_up"] | out_df["is_limit_down"] | out_df["is_suspended"]
    )

    # Final candidates = above threshold AND tradable
    threshold = state.bundle["threshold"]
    out_df["is_candidate"] = out_df["tradable"] & (out_df["probability"] >= threshold)

    out_df = out_df.sort_values("probability", ascending=False).reset_index(drop=True)
    out_df.insert(0, "rank", np.arange(1, len(out_df) + 1))

    # Gate summary
    n_st = out_df["is_st"].sum()
    n_limit_up = out_df["is_limit_up"].sum()
    n_limit_down = out_df["is_limit_down"].sum()
    n_candidates = out_df["is_candidate"].sum()
    print(f"\n=== TRADABILITY GATES ===")
    print(f"  Total scored: {len(out_df)}")
    print(f"  ST/退市: {n_st} (excluded)")
    print(f"  涨停: {n_limit_up} (excluded)")
    print(f"  跌停: {n_limit_down} (excluded)")
    print(f"  Above threshold: {(out_df['probability'] >= threshold).sum()}")
    print(f"  Final candidates (tradable + above threshold): {n_candidates}")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\nCSV saved: {OUTPUT_CSV}")
    print(f"  Top probability: {out_df['probability'].max():.4f}")

    results["status"] = "ok"
    results["timing"] = timing
    results["gap_stats"] = gap_stats
    results["total_stocks"] = len(out_df)
    results["above_threshold"] = int((out_df["probability"] >= threshold).sum())
    results["candidates"] = int(n_candidates)
    results["top_probability"] = float(out_df["probability"].max())
    results["within_180s"] = total_time < 180
    results["net_mf_available"] = len(net_mf_map) > 0
    results["turnover_available"] = len(turnover_map) > 0

    # --- Feature availability classification ---
    selected_features = list(state.bundle["selected_feature_names"])
    feature_status = {}  # feature_name -> exact/proxy/T-1/zero-fill/missing

    for feat in selected_features:
        if feat in MONEYFLOW_BREAKDOWN_FEATURES:
            # These need buy/sell split — push2 CANNOT provide
            # T-1 tushare values are used (loaded in step 7)
            feature_status[feat] = "T-1_tushare_proxy"
        elif feat in LIVE_CHIP_T1_COLUMNS:
            feature_status[feat] = "T-1_tushare_chip_declared"
        elif feat in LIVE_INTRADAY_MINUTE_COLUMNS:
            feature_status[feat] = "realtime_5min_intraday"
        elif feat in LIVE_INTRADAY_SNAPSHOT_COLUMNS:
            feature_status[feat] = "realtime_snapshot"
        elif feat in LIVE_DAILY_DERIVED_COLUMNS:
            feature_status[feat] = "realtime_1457_daily_derived"
        elif feat in LIVE_TUSHARE_LIMIT_FEATURES or feat in LIVE_TUSHARE_LIMIT_COLUMNS:
            feature_status[feat] = "realtime_limit_pool"
        elif feat in GPU_PROBE_THS_SECTOR_FEATURES:
            feature_status[feat] = "zero_fill_no_1457_source"
        elif feat in MONEYFLOW_NET_FEATURES:
            feature_status[feat] = "proxy_realtime_push2" if net_mf_map else "T-1_tushare"
        elif feat == "tushare_ff_adjusted_flow":
            feature_status[feat] = "proxy_realtime_push2" if net_mf_map else "T-1_tushare"
        elif feat == "tushare_volume_ratio":
            feature_status[feat] = "proxy_realtime_computed"
        elif feat in ("tushare_up_limit_distance", "tushare_down_limit_distance", "tushare_limit_range"):
            feature_status[feat] = "exact_T-1_stk_limit"
        elif feat.startswith("tushare_"):
            feature_status[feat] = "T-1_tushare"
        else:
            feature_status[feat] = "exact"

    n_exact = sum(1 for v in feature_status.values() if v == "exact")
    n_proxy = sum(1 for v in feature_status.values() if "proxy" in v)
    n_t1 = sum(1 for v in feature_status.values() if "T-1" in v)
    n_missing = sum(1 for v in feature_status.values() if v in {"missing", "zero_fill_no_1457_source"})

    results["feature_availability"] = {
        "exact": n_exact,
        "proxy_realtime": n_proxy,
        "T-1_tushare": n_t1,
        "missing": n_missing,
        "total_selected": len(selected_features),
        "detail": feature_status,
    }

    # Determine output grade
    if n_missing == 0 and n_proxy == 0 and n_t1 == 0:
        output_grade = "strict_1457"
    elif n_missing == 0 and all(
        status in {
            "exact",
            "realtime_5min_intraday",
            "realtime_snapshot",
            "realtime_1457_daily_derived",
            "realtime_limit_pool",
            "T-1_tushare_chip_declared",
        }
        for status in feature_status.values()
    ):
        output_grade = "strict_1457_with_declared_t1_chip"
    elif n_missing == 0:
        output_grade = "approximated_1457"
    else:
        output_grade = "not_strict_1457_executable_yet"

    # Since moneyflow breakdown features cannot be computed from push2,
    # we always have T-1 proxies → grade is at best approximated_1457
    results["output_grade"] = output_grade
    results["output_grade_reason"] = (
        "Selected runtime factors are computed from the live snapshot, live 5-minute bars, "
        "live limit/failed-board pool, or the explicitly declared T-1 chip/cost source. "
        "Forbidden post-close and THS sector features are rejected if selected."
    )

    # P1-12: Summary metadata for formal validation
    sv = results.get("snapshot_validation", {})
    lsv = results.get("live_snapshot_validation", {})
    active_sv = lsv if lsv else sv
    is_formal_valid = (
        run_mode == "formal"
        and results.get("status") == "ok"
        and active_sv.get("valid", False)
    )
    results["is_formal_valid"] = is_formal_valid
    if not is_formal_valid and run_mode == "formal":
        reasons = []
        if results.get("status") != "ok":
            reasons.append(f"status={results.get('status')}")
        if not active_sv.get("valid", False):
            reasons.append(f"snapshot_validation={active_sv.get('reason', 'unknown')}")
        results["formal_valid_reason"] = "; ".join(reasons) if reasons else "unknown"
    results["snapshot_time_status"] = active_sv.get("status", "not_checked")
    qt_counts = active_sv.get("quote_time_counts", {})
    results["snapshot_quote_min"] = qt_counts.get("quote_time_min")
    results["snapshot_quote_max"] = qt_counts.get("quote_time_max")
    results["universe_counts"] = {
        "gated": len(state.universe),
        "all_main_board": len(state.all_main_board) if state.all_main_board else 0,
        "market_context_injected": results.get("market_context_injected", 0),
    }

    # Postclose completeness validation
    if run_mode == "postclose":
        postclose_issues: list[str] = []
        # Check snapshot coverage
        pc = results.get("postclose_checks", {})
        if pc.get("latest_price_coverage", 0) < 0.95:
            postclose_issues.append(f"snapshot_price_coverage={pc.get('latest_price_coverage')}")
        # Check last_30min
        slm = results.get("strict_live_factors", {})
        min_meta = slm.get("intraday_minute", {})
        if min_meta.get("required"):
            min_cov = min_meta.get("coverage", 0)
            if min_cov < 0.95:
                postclose_issues.append(f"last_30min_coverage={min_cov}")
        # Check limit pool
        lp_meta = results.get("limit_pool_live", {})
        if needs_live_limit_pool and lp_meta.get("status") != "available":
            postclose_issues.append(f"limit_pool={lp_meta.get('status')}")
        # Check runtime gate didn't drop too many
        rg = slm.get("runtime_gate", {})
        if rg.get("before") and rg.get("after"):
            gate_pct = rg["after"] / max(rg["before"], 1)
            if gate_pct < 0.90:
                postclose_issues.append(f"runtime_gate_retained={gate_pct:.1%}")

        is_postclose_complete = (
            results.get("status") == "ok"
            and len(postclose_issues) == 0
        )
        results["is_postclose_complete"] = is_postclose_complete
        if is_postclose_complete:
            results["output_grade"] = "postclose_full_data"
        else:
            results["output_grade"] = "postclose_incomplete"
            results["postclose_incomplete_reasons"] = postclose_issues
        results["postclose_data_fetch_time"] = pc.get("data_fetch_time")
        results["postclose_snapshot_source"] = results.get("snapshot_source")
        print(f"\n  Postclose complete: {is_postclose_complete}")
        if postclose_issues:
            print(f"  Issues: {postclose_issues}")

    print(f"\n=== OUTPUT GRADE: {results['output_grade']} ===")
    print(f"  exact: {n_exact}/{len(selected_features)}")
    print(f"  proxy (realtime): {n_proxy}")
    print(f"  T-1 tushare: {n_t1}")
    print(f"  missing: {n_missing}")
    print(f"  Reason: {results['output_grade_reason']}")
    print(f"\n  Paper-trading selector still applies tradability gates.")

    return results


def write_report(warmup_timing: dict, live_results: dict, state: WarmupState):
    """Write engineering test report with honest feature availability grading."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = live_results.get("status", "unknown")
    timing = live_results.get("timing", {})
    gap = live_results.get("gap_stats", {})
    feat_avail = live_results.get("feature_availability", {})
    output_grade = live_results.get("output_grade", "unknown")
    grade_reason = live_results.get("output_grade_reason", "")
    threshold_text = f"{state.bundle['threshold']:.4f}" if state.bundle else "N/A"
    top_prob_text = f"{live_results['top_probability']:.4f}" if live_results.get("top_probability") else "N/A"

    # Build feature detail table
    feat_detail = feat_avail.get("detail", {})
    feat_table_rows = ""
    for feat_name in sorted(feat_detail.keys()):
        feat_table_rows += f"| {feat_name} | {feat_detail[feat_name]} |\n"

    report = f"""# 14:57 Live Engineering Test — {TODAY_STR}

Generated: {now}

## Output Grade

**{output_grade}**

- NOT claimed as: strict_1457 / production_ready / tradeable
- This output is: **diagnostic_only**
- Reason: {grade_reason}

## Status

| Item | Value |
|------|-------|
| Pipeline status | {status} |
| Output grade | {output_grade} |
| Asof time | {live_results.get('asof_time', 'N/A')} |
| Within 180s | {'YES' if live_results.get('within_180s') else 'NO'} |
| Universe | {len(state.universe) if state.universe else 0} stocks |
| Scored | {live_results.get('total_stocks', 0)} |
| Above threshold ({threshold_text}) | {live_results.get('above_threshold', 0)} |
| Candidates (tradable+threshold) | {live_results.get('candidates', 0)} |
| Top probability | {top_prob_text} |

## Feature Availability ({len(state.bundle.get('selected_feature_names', [])) if state.bundle else '?'} selected features)

| Category | Count | Description |
|----------|-------|-------------|
| exact | {feat_avail.get('exact', 0)} | Computed from realtime data, same semantics as training |
| proxy_realtime | {feat_avail.get('proxy_realtime', 0)} | Approximated from realtime source (e.g. push2 f62 for net_mf) |
| T-1_tushare | {feat_avail.get('T-1_tushare', 0)} | Using previous day's tushare cache (ratios, breakdown) |
| missing | {feat_avail.get('missing', 0)} | No data source available |

### Moneyflow breakdown features (CANNOT compute at 14:57)

These 5+1 selected features require buy/sell order-size split that push2 batch endpoints
do NOT provide reliably. Values come from T-1 tushare moneyflow cache:

- tushare_lg_buy_sell_ratio (T-1 proxy)
- tushare_elg_buy_sell_ratio (T-1 proxy)
- tushare_mf_strength (T-1 proxy)
- tushare_sm_sell_pressure (T-1 proxy)
- tushare_main_force_divergence (T-1 proxy)
- tushare_mf_flow_intensity (T-1 proxy if net_mf unavailable)

### What IS realtime at 14:57

- Snapshot prices (Sina hq.sinajs.cn): OHLCV, prev_close, pct_change
- push2 f62: net main force inflow → tushare_net_mf_amount (proxy)
- Turnover: volume / float_share (computed, float_share from T-1 cache)
- Volume ratio: today_volume / avg_5d_volume (computed)
- All price-derived features (MA, returns, etc.): exact from snapshot bar

## Config Alignment

| Parameter | Training | Probe | Match |
|-----------|----------|-------|-------|
| min_phase_days_3 | 1 | 1 | YES |
| short_only | True | True | YES |
| exclude_event_limit_up | True | False (post-hoc filter) | DECLARED |
| feature_set | research | research | YES |
| label_target | next_high_from_close | N/A (inference only) | N/A |

**Note on exclude_event_limit_up**: Training excludes limit-up stocks during feature
construction. Probe does NOT exclude during construction (needs all stocks scored)
but applies strict post-hoc filter: ST, suspended, limit-up, limit-down all excluded
from candidate output.

## Tradability Gates Applied

- ST / 退市: excluded
- 涨停 (>= 99.5% of board limit): excluded
- 跌停 (<= 100.5% of down limit): excluded
- Suspended (price=0 or NaN): excluded

## Timing

### Warmup (pre-14:57)

| Step | Time (s) |
|------|----------|
| Bundle load | {warmup_timing.get('bundle_load_sec', 0):.3f} |
| Universe | {warmup_timing.get('universe_sec', 0):.2f} |
| Daily bars | {warmup_timing.get('load_bars_sec', 0):.1f} |
| THS sector | {warmup_timing.get('ths_precompute_sec', 0):.1f} |
| **Warmup total** | **{sum(warmup_timing.values()):.1f}** |

### Live (at 14:57)

| Step | Time (s) |
|------|----------|
| Snapshot | {timing.get('snapshot_fetch_sec', 0):.1f} |
| Net MF fetch | {timing.get('net_mf_fetch_sec', 0):.1f} |
| Turnover | {timing.get('turnover_sec', 0):.1f} |
| Inject bar | {timing.get('inject_bar_sec', 0):.2f} |
| Symbol features | {timing.get('symbol_features_sec', 0):.1f} |
| Factors attach | {timing.get('cross_section_sec', 0) + timing.get('free_factors_sec', 0) + timing.get('cross_market_sec', 0) + timing.get('tgb_factors_sec', 0) + timing.get('ths_sector_sec', 0) + timing.get('limit_pool_sec', 0):.1f} |
| Tushare T-1 | {timing.get('tushare_factors_sec', 0):.1f} |
| Realtime override | {timing.get('realtime_override_sec', 0):.2f} |
| Feature alignment | {timing.get('align_features_sec', 0):.2f} |
| Inference | {timing.get('inference_sec', 0):.2f} |
| **Live total** | **{timing.get('total_live_sec', 0):.1f}** |

## Model

- Bundle: {Path(BUNDLE_PATH).parent.name}
- Model: {state.bundle['model_name'] if state.bundle else 'N/A'}
- Members: {str(state.bundle['member_names']) if state.bundle else 'N/A'}
- Selected features: {len(state.bundle.get('selected_feature_names', [])) if state.bundle else 'N/A'} / {len(state.bundle.get('feature_names', [])) if state.bundle else 'N/A'} total
- Calibration: isotonic
- Threshold: {threshold_text}

## Data Sources

| Source | Used for | Availability |
|--------|----------|--------------|
| Sina hq.sinajs.cn | Snapshot OHLCV | Realtime |
| push2.eastmoney.com f62 | net_mf_amount | Realtime (unstable, 502s) |
| push2 f135-f142 | buy/sell breakdown | **NOT USABLE** (batch returns garbage) |
| tushare moneyflow parquet | lg/elg/sm ratios | T-1 cache |
| tushare daily_basic | float_share/free_share, turnover_rate | T-1 cache |
| tushare stk_limit | up/down limit prices | T-1 cache |
| Daily bars parquet | Historical OHLCV | Disk cache |

## Conclusion

Output grade: **{output_grade}**
{'Cannot claim strict_1457 because moneyflow breakdown features (5/260) use T-1 proxy.' if output_grade != 'strict_1457' else ''}
Diagnostic CSV saved for review. NOT production candidates.
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\nReport saved: {REPORT_PATH}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="14:57 Live Engineering Test")
    parser.add_argument("--phase", choices=["warmup", "live", "all"], default="all")
    parser.add_argument("--no-wait", action="store_true",
                        help="Don't wait for 14:57, run live immediately (for testing)")
    args = parser.parse_args()

    if args.phase == "live":
        raise SystemExit(
            "ERROR: --phase live is not supported when running this script directly.\n"
            "This script lacks 14:30 price cache, P0 feature checks, run_mode validation,\n"
            "selector output, and all_main_board initialization.\n"
            "Please use: python scripts/run_1457_live_sim.py --phase all [--no-wait] [--run-mode formal|postclose|test]"
        )

    print(
        "WARNING: Running realtime_1457_today_probe.py directly is for diagnostics only.\n"
        "For formal/postclose runs, use run_1457_live_sim.py (wrapper with selector,\n"
        "14:30 price cache, P0 feature checks, and timing JSON output)."
    )

    state = WarmupState()

    if args.phase in ("warmup", "all"):
        warmup_timing = phase_warmup(state)
    else:
        # For live-only, still need to load bundle
        warmup_timing = {}
        state.bundle = load_bundle(BUNDLE_PATH)
        state.universe = get_universe_from_cache()
        state.config = build_config()
        state.all_bars = load_daily_bars(state.universe, state.config.start, TODAY - timedelta(days=1))
        state.ths_factor = empty_ths_live_factor()
        state.name_map = {}
        if NAME_CACHE_PATH.exists():
            with open(NAME_CACHE_PATH, "r", encoding="utf-8") as f:
                state.name_map = json.load(f)

    if args.phase in ("live", "all"):
        if args.phase == "all" and not args.no_wait:
            now = datetime.now()
            target = now.replace(hour=14, minute=57, second=0, microsecond=0)
            if now < target:
                wait = (target - now).total_seconds()
                print(f"\nWaiting {wait:.0f}s until 14:57...")
                print(f"(Use --no-wait to skip waiting)")
                time.sleep(wait)
            elif now > target.replace(minute=59):
                print("\nWARNING: Past 14:59, market may be closed. Running anyway.")

        live_results = phase_live(state)
        write_report(warmup_timing, live_results, state)
    else:
        print("\n[Warmup complete. Run with --phase live at 14:57]")


if __name__ == "__main__":
    main()

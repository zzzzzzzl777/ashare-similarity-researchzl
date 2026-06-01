"""Robust PhaseC strategy search across long history and recent forward windows.

This is a read-only research script. It scores the saved PhaseC bundle from
feature caches and searches fixed daily selection policies. The selection
objective is intentionally not pure total return: it also rewards recent
2026 behavior, daily win rate, high+1 hit rate, month consistency, and penalizes
drawdown and weak forward windows.
"""

from __future__ import annotations

import heapq
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
sys.path.insert(0, str(ROOT))

import scripts.run_dual_model_strategy_search as base


BUNDLE_PATH = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt"
)
CACHE_LONG = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_550a77f54882058f.parquet"
)
CACHE_LATEST = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_10c11fc874db003c.parquet"
)
OUT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
RUN_TAG = "phasec_strategy_robust_full_20260520"

SCORE_COLS = ["raw_prob", "iso_prob"]
THRESHOLDS = [round(x / 100.0, 2) for x in range(55, 83)]
TOP_NS = [1, 2, 3, 4, 5, 6]

EXIT_MODES = [
    ("close", None, None),
    ("sl1", -1.0, None),
    ("sl2", -2.0, None),
    ("sl3", -3.0, None),
    ("tp2", None, 2.0),
    ("tp3", None, 3.0),
    ("tp5", None, 5.0),
    ("tp7", None, 7.0),
    ("tp10", None, 10.0),
    ("sl1_tp3", -1.0, 3.0),
    ("sl1_tp5", -1.0, 5.0),
    ("sl2_tp5", -2.0, 5.0),
    ("sl2_tp7", -2.0, 7.0),
    ("sl3_tp7", -3.0, 7.0),
    ("sl3_tp10", -3.0, 10.0),
]

RANK_RECIPES = [
    "prob_desc",
    "prob_then_rsi6_low",
    "rsi6_low",
    "prob_then_turnover_high",
    "turnover_high",
    "volume_z_high",
    "amount_z_high",
    "activity_z_high",
    "prob_x_activity",
    "prob_x_volume",
    "prob_x_amount",
    "prob_x_turnover",
    "low_price_prob",
    "close_position_high",
    "lower_shadow_high",
    "sector_strength",
    "sector_hot",
]

PERIODS = [
    ("stress_2017_2022", "2017-01-01", "2022-12-31"),
    ("dev_2023_2025", "2023-01-01", "2025-12-31"),
    ("q1_2026", "2026-01-01", "2026-03-31"),
    ("apr_2026", "2026-04-01", "2026-04-30"),
    ("may_2026_partial", "2026-05-01", "2026-05-31"),
]


def pct_prod(arr: np.ndarray) -> float:
    if arr.size == 0:
        return 0.0
    clipped = np.clip(arr / 100.0, -0.95, 10.0)
    return float((np.prod(1.0 + clipped) - 1.0) * 100.0)


def safe_num(df: pd.DataFrame, col: str, fill: float = 0.0) -> np.ndarray:
    if col not in df.columns:
        return np.full(len(df), fill, dtype=np.float64)
    return pd.to_numeric(df[col], errors="coerce").fillna(fill).to_numpy(dtype=np.float64)


def compute_exit_arrays(df: pd.DataFrame) -> dict[str, np.ndarray]:
    close_ret = safe_num(df, "next_close_return_pct", 0.0)
    high_ret = safe_num(df, "next_high_return_pct", np.nan)
    low_ret = safe_num(df, "next_low_return_pct", np.nan)
    high_ret = np.where(np.isnan(high_ret), close_ret, high_ret)
    low_ret = np.where(np.isnan(low_ret), close_ret, low_ret)

    out: dict[str, np.ndarray] = {}
    for name, sl, tp in EXIT_MODES:
        if sl is None and tp is None:
            out[name] = close_ret.copy()
        elif sl is not None and tp is None:
            out[name] = np.where(low_ret <= sl, sl, close_ret)
        elif sl is None and tp is not None:
            out[name] = np.where(high_ret >= tp, tp, close_ret)
        else:
            sl_hit = low_ret <= sl
            tp_hit = high_ret >= tp
            r = close_ret.copy()
            r[tp_hit & ~sl_hit] = tp
            r[sl_hit] = sl
            out[name] = r
    return out


def load_pool(bundle: dict) -> pd.DataFrame:
    long_df = base.load_scoring_frame(CACHE_LONG, bundle, "2017-01-01", "2026-03-31", "long_2017_202603")
    latest_df = base.load_scoring_frame(CACHE_LATEST, bundle, "2026-04-01", "2026-05-31", "latest_202604_202605")
    df = pd.concat([long_df, latest_df], ignore_index=True, sort=False)
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    df = df.sort_values(["date", "symbol", "window"]).drop_duplicates(["date", "symbol"], keep="last").copy()

    raw, iso = base.predict_raw_and_iso(bundle, df)
    df["raw_prob"] = raw.astype(np.float64)
    df["iso_prob"] = iso.astype(np.float64)

    needed = ["actual", "next_high_return_pct", "next_close_return_pct", "next_low_return_pct"]
    before = len(df)
    for col in needed:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=needed).copy()
    df["actual"] = (df["actual"].astype(float) > 0.5).astype(float)
    df["date_key"] = df["date"].dt.strftime("%Y-%m-%d")
    df["month"] = df["date"].dt.strftime("%Y-%m")
    print(
        f"Pool: {len(df):,}/{before:,} rows, {df['date_key'].nunique()} days, "
        f"{df['date'].min().date()}..{df['date'].max().date()}",
        flush=True,
    )
    return df.reset_index(drop=True)


def build_filters(df: pd.DataFrame) -> list[tuple[str, str, np.ndarray]]:
    n = len(df)
    close = safe_num(df, "close")
    turnover = safe_num(df, "turnover")
    vz = safe_num(df, "volume_z_20")
    az = safe_num(df, "amount_z_20")
    tz = safe_num(df, "turnover_z_20")
    rsi6 = safe_num(df, "rsi_6", 50.0)
    rng = safe_num(df, "range_pct")
    cp = safe_num(df, "close_position", 0.5)
    lower = safe_num(df, "lower_shadow_pct")
    sec_rank = safe_num(df, "sector_strength_rank", 999.0)
    sec_lu = safe_num(df, "sector_limit_up_count")
    sec_days = safe_num(df, "sector_duration_days")

    specs: list[tuple[str, str, np.ndarray]] = [
        ("none", "safe", np.ones(n, dtype=bool)),
        ("turnover>=3", "safe", turnover >= 3),
        ("turnover>=5", "safe", turnover >= 5),
        ("turnover>=8", "safe", turnover >= 8),
        ("turnover_3_20", "safe", (turnover >= 3) & (turnover <= 20)),
        ("turnover_5_20", "safe", (turnover >= 5) & (turnover <= 20)),
        ("turnover_5_30", "safe", (turnover >= 5) & (turnover <= 30)),
        ("turnover_8_30", "safe", (turnover >= 8) & (turnover <= 30)),
        ("close_3_60", "safe", (close >= 3) & (close <= 60)),
        ("close_5_60", "safe", (close >= 5) & (close <= 60)),
        ("close_5_100", "safe", (close >= 5) & (close <= 100)),
        ("close_10_80", "safe", (close >= 10) & (close <= 80)),
        ("volume_z>=0", "safe", vz >= 0),
        ("volume_z>=0.5", "safe", vz >= 0.5),
        ("amount_z>=0", "safe", az >= 0),
        ("amount_z>=0.5", "safe", az >= 0.5),
        ("turnover_z>=0", "safe", tz >= 0),
        ("rsi6<=45", "safe", rsi6 <= 45),
        ("rsi6<=55", "safe", rsi6 <= 55),
        ("range>=2", "safe", rng >= 2),
        ("close_pos>=0.55", "safe", cp >= 0.55),
        ("lower_shadow>=1", "safe", lower >= 1),
        ("t5_20_close5_80", "safe", (turnover >= 5) & (turnover <= 20) & (close >= 5) & (close <= 80)),
        ("t5_30_vz0", "safe", (turnover >= 5) & (turnover <= 30) & (vz >= 0)),
        ("t5_30_az0", "safe", (turnover >= 5) & (turnover <= 30) & (az >= 0)),
        ("t5_30_rsi55", "safe", (turnover >= 5) & (turnover <= 30) & (rsi6 <= 55)),
        ("t5_30_vz0_rsi55", "safe", (turnover >= 5) & (turnover <= 30) & (vz >= 0) & (rsi6 <= 55)),
        ("t5_30_az0_rsi55", "safe", (turnover >= 5) & (turnover <= 30) & (az >= 0) & (rsi6 <= 55)),
        ("t5_30_vz0_cp55", "safe", (turnover >= 5) & (turnover <= 30) & (vz >= 0) & (cp >= 0.55)),
        ("t5_30_az0_cp55", "safe", (turnover >= 5) & (turnover <= 30) & (az >= 0) & (cp >= 0.55)),
        ("sector_rank<=80", "sector_proxy", sec_rank <= 80),
        ("sector_lu>=1", "sector_proxy", sec_lu >= 1),
        ("sector_days>=2", "sector_proxy", sec_days >= 2),
        ("t5_sector_rank<=80", "sector_proxy", (turnover >= 5) & (sec_rank <= 80)),
        ("t5_sector_lu>=1", "sector_proxy", (turnover >= 5) & (sec_lu >= 1)),
        ("t5_sector_days>=2", "sector_proxy", (turnover >= 5) & (sec_days >= 2)),
    ]
    return [(name, kind, mask.astype(bool)) for name, kind, mask in specs]


def sort_key(df: pd.DataFrame, score_col: str, recipe: str) -> np.ndarray:
    prob = safe_num(df, score_col)
    turnover = safe_num(df, "turnover")
    tz = safe_num(df, "turnover_z_20")
    vz = safe_num(df, "volume_z_20")
    az = safe_num(df, "amount_z_20")
    rng = safe_num(df, "range_pct")
    rsi6 = safe_num(df, "rsi_6", 50.0)
    close = safe_num(df, "close")
    cp = safe_num(df, "close_position", 0.5)
    lower = safe_num(df, "lower_shadow_pct")
    sec_rank = safe_num(df, "sector_strength_rank", 999.0)
    sec_lu = safe_num(df, "sector_limit_up_count")
    sec_days = safe_num(df, "sector_duration_days")

    if recipe == "prob_desc":
        return prob
    if recipe == "prob_then_rsi6_low":
        return prob * 1000.0 - rsi6
    if recipe == "rsi6_low":
        return -rsi6 * 1000.0 + prob
    if recipe == "prob_then_turnover_high":
        return prob * 1000.0 + turnover / 100.0
    if recipe == "turnover_high":
        return turnover * 1000.0 + prob
    if recipe == "volume_z_high":
        return vz * 1000.0 + prob
    if recipe == "amount_z_high":
        return az * 1000.0 + prob
    if recipe == "activity_z_high":
        return (np.clip(vz, -3, 3) + np.clip(az, -3, 3) + np.clip(tz, -3, 3)) * 1000.0 + prob
    if recipe == "prob_x_activity":
        return prob * (1.0 + 0.12 * (np.clip(vz, -3, 3) + np.clip(az, -3, 3)))
    if recipe == "prob_x_volume":
        return prob * (1.0 + 0.2 * np.clip(vz, 0, 3))
    if recipe == "prob_x_amount":
        return prob * (1.0 + 0.2 * np.clip(az, 0, 3))
    if recipe == "prob_x_turnover":
        return prob * (1.0 + 0.15 * np.clip(tz, 0, 3))
    if recipe == "low_price_prob":
        return prob * 1000.0 - close / 10.0
    if recipe == "close_position_high":
        return cp * 1000.0 + prob
    if recipe == "lower_shadow_high":
        return lower * 1000.0 + prob
    if recipe == "sector_strength":
        return -sec_rank * 1000.0 + prob
    if recipe == "sector_hot":
        return (sec_lu * 10.0 + sec_days) * 1000.0 + prob
    raise ValueError(recipe)


def build_cube(
    df: pd.DataFrame,
    score_col: str,
    recipe: str,
    filter_mask: np.ndarray,
    thresholds: list[float],
    day_indices: list[np.ndarray],
    max_top: int,
) -> np.ndarray:
    score = safe_num(df, score_col)
    key = sort_key(df, score_col, recipe)
    cube = np.full((len(thresholds), len(day_indices), max_top), -1, dtype=np.int32)
    for d, didx in enumerate(day_indices):
        idx = didx[filter_mask[didx]]
        if idx.size == 0:
            continue
        idx = idx[np.argsort(-key[idx], kind="mergesort")]
        ds = score[idx]
        for ti, thr in enumerate(thresholds):
            sel = idx[ds >= thr][:max_top]
            if sel.size:
                cube[ti, d, : sel.size] = sel
    return cube


def daily_returns_for(cube_thr: np.ndarray, exit_arr: np.ndarray, actual: np.ndarray, top_n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    idx = cube_thr[:, :top_n]
    valid = idx >= 0
    counts = valid.sum(axis=1)
    active = counts > 0
    safe_idx = np.where(valid, idx, 0)
    returns = np.where(valid, exit_arr[safe_idx], 0.0)
    daily = np.zeros(len(counts), dtype=np.float64)
    daily[active] = returns.sum(axis=1)[active] / counts[active]
    hits = np.where(valid, actual[safe_idx], 0.0)
    return daily, counts, hits


def metrics_from_daily(daily: np.ndarray, counts: np.ndarray, hits: np.ndarray, active_mask: np.ndarray) -> dict:
    active = active_mask & (counts > 0)
    dr = daily[active]
    cnt = counts[active]
    if dr.size == 0:
        return {
            "days": 0,
            "tickets": 0,
            "return_pct": 0.0,
            "daily_win": 0.0,
            "high1": 0.0,
            "avg_daily": 0.0,
            "max_loss": 0.0,
            "sharpe": None,
        }
    valid_hits = hits[active]
    tickets = int(cnt.sum())
    flat_hits = float(valid_hits.sum())
    std = float(dr.std(ddof=1)) if dr.size >= 3 else 0.0
    return {
        "days": int(dr.size),
        "tickets": tickets,
        "return_pct": round(pct_prod(dr), 2),
        "daily_win": round(float((dr > 0).mean()), 4),
        "high1": round(float(flat_hits / tickets), 4) if tickets else 0.0,
        "avg_daily": round(float(dr.mean()), 4),
        "max_loss": round(float(dr.min()), 2),
        "sharpe": round(float(dr.mean() / std * math.sqrt(252)), 2) if std > 0 else None,
    }


def compute_drawdown(daily: np.ndarray, counts: np.ndarray) -> float:
    active = counts > 0
    dr = daily[active]
    if dr.size == 0:
        return 0.0
    eq = np.cumprod(1.0 + np.clip(dr / 100.0, -0.95, 10.0))
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak * 100.0
    return round(float(dd.min()), 2)


def robust_score(rec: dict) -> float:
    def period(name: str, key: str, default=0.0):
        return rec["periods"].get(name, {}).get(key, default)

    stress = period("stress_2017_2022", "return_pct")
    dev = period("dev_2023_2025", "return_pct")
    q1 = period("q1_2026", "return_pct")
    apr = period("apr_2026", "return_pct")
    may = period("may_2026_partial", "return_pct")
    q1_win = period("q1_2026", "daily_win")
    apr_win = period("apr_2026", "daily_win")
    may_win = period("may_2026_partial", "daily_win")
    total_win = rec["overall"]["daily_win"]
    high1 = rec["overall"]["high1"]

    def log_ret(x: float) -> float:
        return math.copysign(math.log1p(abs(x) / 100.0), x)

    monthly = rec["monthly"]
    neg_months = sum(1 for m in monthly if m["return_pct"] < 0)
    mdd = abs(rec["max_drawdown_pct"])
    enough_recent = min(period("q1_2026", "days"), 45) / 45.0 + min(period("apr_2026", "days"), 15) / 15.0

    score = 0.0
    score += 1.0 * log_ret(stress)
    score += 0.8 * log_ret(dev)
    score += 3.0 * log_ret(q1)
    score += 3.0 * log_ret(apr)
    score += 1.0 * log_ret(may)
    score += 3.0 * total_win
    score += 2.0 * high1
    score += 1.2 * q1_win + 1.2 * apr_win + 0.5 * may_win
    score += 0.8 * enough_recent
    score -= 0.09 * neg_months
    score -= 0.015 * mdd

    if q1 <= 0:
        score -= 2.0
    if apr <= 0:
        score -= 2.5
    if may < -8:
        score -= 1.0
    if total_win < 0.55:
        score -= 1.0
    if high1 < 0.75:
        score -= 1.0
    if rec["overall"]["days"] < 150:
        score -= 1.0
    return float(score)


class TopK:
    def __init__(self, n: int, key: str):
        self.n = n
        self.key = key
        self.heap: list[tuple[float, int, dict]] = []
        self.seq = 0

    def push(self, rec: dict) -> None:
        val = rec.get(self.key)
        if val is None:
            return
        item = (float(val), self.seq, rec.copy())
        self.seq += 1
        if len(self.heap) < self.n:
            heapq.heappush(self.heap, item)
        elif item[0] > self.heap[0][0]:
            heapq.heapreplace(self.heap, item)

    def top(self) -> list[dict]:
        return [item[2] for item in sorted(self.heap, key=lambda x: x[0], reverse=True)]


def evaluate_record(
    rec_base: dict,
    cube_thr: np.ndarray,
    exit_arr: np.ndarray,
    actual: np.ndarray,
    top_n: int,
    day_dates: np.ndarray,
    months: np.ndarray,
    period_masks: dict[str, np.ndarray],
) -> dict | None:
    daily, counts, hits = daily_returns_for(cube_thr, exit_arr, actual, top_n)
    if int((counts > 0).sum()) < 20:
        return None
    overall = metrics_from_daily(daily, counts, hits, np.ones(len(day_dates), dtype=bool))
    if overall["tickets"] < 20:
        return None
    periods = {name: metrics_from_daily(daily, counts, hits, mask) for name, mask in period_masks.items()}

    monthly = []
    for m in sorted(set(months[counts > 0])):
        mask = months == m
        met = metrics_from_daily(daily, counts, hits, mask)
        if met["days"] > 0:
            monthly.append({"month": str(m), **met})

    rec = dict(rec_base)
    rec["overall"] = overall
    rec["periods"] = periods
    rec["monthly"] = monthly
    rec["max_drawdown_pct"] = compute_drawdown(daily, counts)
    rec["negative_months"] = sum(1 for m in monthly if m["return_pct"] < 0)
    rec["positive_months"] = sum(1 for m in monthly if m["return_pct"] > 0)
    rec["months_total"] = len(monthly)
    rec["robust_score"] = round(robust_score(rec), 6)
    rec["q1_return_pct"] = periods["q1_2026"]["return_pct"]
    rec["apr_return_pct"] = periods["apr_2026"]["return_pct"]
    rec["may_return_pct"] = periods["may_2026_partial"]["return_pct"]
    rec["stress_return_pct"] = periods["stress_2017_2022"]["return_pct"]
    rec["dev_return_pct"] = periods["dev_2023_2025"]["return_pct"]
    rec["total_return_pct"] = overall["return_pct"]
    rec["daily_win"] = overall["daily_win"]
    rec["high1"] = overall["high1"]
    return rec


def slim_record(rec: dict) -> dict:
    out = {k: v for k, v in rec.items() if k not in {"monthly", "periods"}}
    for name, met in rec["periods"].items():
        out[f"{name}_return"] = met["return_pct"]
        out[f"{name}_days"] = met["days"]
        out[f"{name}_win"] = met["daily_win"]
        out[f"{name}_high1"] = met["high1"]
    return out


def main() -> None:
    start = time.time()
    print("=" * 80)
    print("PhaseC robust full-history strategy search")
    print("=" * 80)
    bundle = base.load_bundle(BUNDLE_PATH)
    print(
        f"Bundle: {bundle.get('model_name')} kind={bundle.get('model_kind')} "
        f"features={len(bundle.get('feature_names', []))} selected={len(bundle.get('selected_indices', []))}",
        flush=True,
    )

    df = load_pool(bundle)
    actual = safe_num(df, "actual")
    exits = compute_exit_arrays(df)
    day_codes, day_values = pd.factorize(df["date"], sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    day_dates = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m-%d").to_numpy()
    months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()
    period_masks = {
        name: (day_dates >= start_s) & (day_dates <= end_s)
        for name, start_s, end_s in PERIODS
    }

    filters = build_filters(df)
    max_top = max(TOP_NS)
    print(
        f"Grid: scores={len(SCORE_COLS)} filters={len(filters)} recipes={len(RANK_RECIPES)} "
        f"thresholds={len(THRESHOLDS)} topN={len(TOP_NS)} exits={len(EXIT_MODES)}",
        flush=True,
    )

    top_robust = TopK(500, "robust_score")
    top_apr = TopK(200, "apr_return_pct")
    top_recent = TopK(300, "q1_return_pct")
    top_total = TopK(200, "total_return_pct")
    all_keep: list[dict] = []

    total_eval = 0
    kept = 0
    t0 = time.time()
    for score_col in SCORE_COLS:
        for filter_name, filter_kind, filter_mask in filters:
            for recipe in RANK_RECIPES:
                if recipe.startswith("sector_") and filter_kind != "sector_proxy":
                    continue
                cube = build_cube(df, score_col, recipe, filter_mask, THRESHOLDS, day_indices, max_top)
                for ti, thr in enumerate(THRESHOLDS):
                    cube_thr = cube[ti]
                    if int((cube_thr >= 0).sum()) < 20:
                        total_eval += len(TOP_NS) * len(EXIT_MODES)
                        continue
                    for top_n in TOP_NS:
                        if int((cube_thr[:, :top_n] >= 0).sum()) < 20:
                            total_eval += len(EXIT_MODES)
                            continue
                        for exit_name, _, _ in EXIT_MODES:
                            total_eval += 1
                            rec = evaluate_record(
                                {
                                    "score_col": score_col,
                                    "threshold": thr,
                                    "top_n": top_n,
                                    "filter_name": filter_name,
                                    "filter_kind": filter_kind,
                                    "rank_recipe": recipe,
                                    "exit_mode": exit_name,
                                },
                                cube_thr,
                                exits[exit_name],
                                actual,
                                top_n,
                                day_dates,
                                months,
                                period_masks,
                            )
                            if rec is None:
                                continue
                            # Keep reasonably active strategies only. This avoids a tiny sample
                            # looking great due to a few lucky days.
                            if rec["periods"]["dev_2023_2025"]["days"] < 250:
                                continue
                            if rec["periods"]["q1_2026"]["days"] < 20:
                                continue
                            if rec["periods"]["apr_2026"]["days"] < 8:
                                continue
                            kept += 1
                            if kept <= 10000 or rec["robust_score"] > 4.0:
                                all_keep.append(slim_record(rec))
                            top_robust.push(rec)
                            top_apr.push(rec)
                            top_recent.push(rec)
                            top_total.push(rec)
                elapsed = time.time() - t0
                print(
                    f"{score_col:8s} {filter_name:22s} {recipe:22s} "
                    f"eval={total_eval:>9,} kept={kept:>7,} {elapsed:>7.0f}s {total_eval/max(elapsed,1):>7,.0f}/s",
                    flush=True,
                )

    by_robust = top_robust.top()
    by_apr = top_apr.top()
    by_recent = top_recent.top()
    by_total = top_total.top()

    def dump(label: str, rows: list[dict], n: int = 10) -> None:
        print("\n" + "=" * 80)
        print(label)
        print("=" * 80)
        for i, r in enumerate(rows[:n], 1):
            print(
                f"#{i} score={r['robust_score']:.3f} {r['score_col']}>={r['threshold']:.2f} "
                f"top{r['top_n']} {r['filter_name']} {r['rank_recipe']} {r['exit_mode']} "
                f"total={r['overall']['return_pct']:.1f}% win={r['overall']['daily_win']:.1%} "
                f"h1={r['overall']['high1']:.1%} mdd={r['max_drawdown_pct']:.1f}% negM={r['negative_months']}/{r['months_total']}"
            )
            for pn in ["stress_2017_2022", "dev_2023_2025", "q1_2026", "apr_2026", "may_2026_partial"]:
                p = r["periods"][pn]
                print(
                    f"   {pn}: ret={p['return_pct']:>8.2f}% days={p['days']:>4} "
                    f"win={p['daily_win']:.1%} h1={p['high1']:.1%}"
                )

    dump("TOP BY ROBUST SCORE", by_robust)
    dump("TOP BY APRIL 2026 RETURN", by_apr, 5)
    dump("TOP BY Q1 2026 RETURN", by_recent, 5)
    dump("TOP BY TOTAL RETURN", by_total, 5)

    best = by_robust[0] if by_robust else (by_total[0] if by_total else None)
    if best is None:
        raise RuntimeError("No strategy candidates survived the activity gates")

    print("\n" + "=" * 80)
    print("RECOMMENDED MONTHLY BREAKDOWN")
    print("=" * 80)
    print(
        f"{best['score_col']}>={best['threshold']:.2f} | {best['filter_name']} | "
        f"{best['rank_recipe']} | top{best['top_n']} | {best['exit_mode']}"
    )
    for m in best["monthly"]:
        print(
            f"{m['month']}: ret={m['return_pct']:>8.2f}% days={m['days']:>3} "
            f"win={m['daily_win']:.1%} h1={m['high1']:.1%} maxLoss={m['max_loss']:.2f}%"
        )

    payload = {
        "run_tag": RUN_TAG,
        "created_at": pd.Timestamp.now().isoformat(),
        "bundle": str(BUNDLE_PATH),
        "cache_long": str(CACHE_LONG),
        "cache_latest": str(CACHE_LATEST),
        "rows": int(len(df)),
        "days": int(df["date_key"].nunique()),
        "date_min": str(df["date"].min().date()),
        "date_max": str(df["date"].max().date()),
        "total_eval": total_eval,
        "kept": kept,
        "elapsed_s": round(time.time() - start, 1),
        "recommended": best,
        "top_robust": by_robust[:50],
        "top_apr": by_apr[:20],
        "top_recent": by_recent[:20],
        "top_total": by_total[:20],
    }
    out_json = OUT_DIR / f"{RUN_TAG}.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    pd.DataFrame([slim_record(r) for r in by_robust[:300]]).to_csv(
        OUT_DIR / f"{RUN_TAG}_top_robust.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(all_keep).to_parquet(OUT_DIR / f"{RUN_TAG}_kept.parquet", index=False)
    print(f"\nWrote {out_json}")
    print(f"Wrote {OUT_DIR / f'{RUN_TAG}_top_robust.csv'}")
    print(f"Wrote {OUT_DIR / f'{RUN_TAG}_kept.parquet'}")
    print(f"Elapsed {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()

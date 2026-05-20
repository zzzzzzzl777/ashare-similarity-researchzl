"""PhaseC candidate surge analysis.

This is a read-only research runner. It keeps PhaseC as the first-stage stock
candidate model, then studies which 14:57-engineerable candidate features are
associated with next-day large intraday high returns.
"""

from __future__ import annotations

import json
import math
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scripts.run_dual_model_strategy_search as base

try:
    from lightgbm import LGBMClassifier, LGBMRegressor
except Exception as exc:  # pragma: no cover
    raise RuntimeError("lightgbm is required for surge analysis") from exc


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
DOC_DIR = ROOT / "docs"
RUN_TAG = "phasec_surge_analysis_20260520"


META_COLS = [
    "date",
    "label_date",
    "symbol",
    "name",
    "actual",
    "close",
    "next_high_return_pct",
    "next_close_return_pct",
    "next_low_return_pct",
    "limit_up_like",
    "short_phase_days_3",
]

LIVE_SAFE_FEATURES = [
    "raw_prob",
    "iso_prob",
    "close",
    "turnover",
    "turnover_z_20",
    "turnover_mean_3",
    "turnover_mean_5",
    "turnover_chg_1",
    "turnover_chg_5",
    "turnover_to_max_20",
    "volume_z_5",
    "volume_z_10",
    "volume_z_20",
    "amount_z_20",
    "range_pct",
    "range_mean_3",
    "body_pct",
    "upper_shadow_pct",
    "lower_shadow_pct",
    "close_position",
    "gap_pct",
    "overnight_return",
    "intraday_return",
    "ret_1",
    "ret_3",
    "ret_5",
    "rsi_6",
    "rsi_14",
    "ma_gap_5",
    "ma_gap_10",
    "ma_gap_20",
    "atr_14_pct",
    "up_count_3",
    "up_count_5",
    "down_count_3",
    "down_count_5",
    "turnover_sum_5",
    "turnover_sum_10",
    "turnover_sum_20",
    "turnover_accel_5_20",
    "active_turnover_freq_60",
    "limit_up_freq_60",
    "near_limit_freq_60",
    "failed_limit_freq_60",
    "range_lag_0",
    "range_lag_1",
    "range_lag_2",
    "range_lag_3",
    "range_lag_4",
    "volume_z_lag_0",
    "volume_z_lag_1",
    "volume_z_lag_2",
    "volume_z_lag_3",
    "volume_z_lag_4",
    "amount_z_lag_0",
    "amount_z_lag_1",
    "amount_z_lag_2",
    "amount_z_lag_3",
    "amount_z_lag_4",
    "ret1_x_volume_z5",
    "ret5_x_volume_z10",
    "ret1_x_close_position",
    "range_x_volume_z5",
    "turnover_x_range",
    "amount_z_x_range",
    "upper_shadow_x_volume_z",
    "lower_shadow_x_volume_z",
    "cs_turnover_rank",
    "cs_amount_z_rank",
    "cs_volume_z_rank",
    "cs_range_rank",
    "cs_market_mean_range",
    "cs_active_turnover_amount_rank",
    "cs_active_rank_x_close_position",
    "rel_range_to_market",
    "volume_z_x_cs_ret_rank",
    "close_pos_x_cs_range_rank",
]

# These can be useful in diagnostics, but only if the web path computes a
# 14:57-compatible proxy. They are not used by the primary live-safe scorer.
SECTOR_PROXY_FEATURES = [
    "sector_pct_change_best",
    "sector_strength_rank",
    "sector_limit_up_count",
    "sector_duration_days",
    "sector_divergence",
    "sector_climax_signal",
]

FORBIDDEN_PATTERNS = [
    "tushare_net_mf",
    "tushare_mf_",
    "tushare_ff_adjusted_flow",
    "minute_last_30min",
    "minute_vwap",
    "tushare_last_30min",
    "tushare_vwap",
    "tushare_close_vs_vwap",
    "auction_close",
    "close_auction",
]

PERIODS = [
    ("stress_2017_2022", "2017-01-01", "2022-12-31"),
    ("dev_2023_2025", "2023-01-01", "2025-12-31"),
    ("q1_2026", "2026-01-01", "2026-03-31"),
    ("apr_2026", "2026-04-01", "2026-04-30"),
    ("may_2026_partial", "2026-05-01", "2026-05-31"),
]


def parquet_columns(path: Path) -> list[str]:
    return list(pq.ParquetFile(path).schema.names)


def is_forbidden_feature(name: str) -> bool:
    low = name.lower()
    return any(pattern in low for pattern in FORBIDDEN_PATTERNS)


def unique_existing(path: Path, cols: list[str]) -> list[str]:
    available = set(parquet_columns(path))
    out: list[str] = []
    for col in cols:
        if col in available and col not in out:
            out.append(col)
    return out


def read_part(path: Path, bundle: dict, start: str, end: str, label: str) -> pd.DataFrame:
    wanted = META_COLS + LIVE_SAFE_FEATURES + SECTOR_PROXY_FEATURES + list(bundle["feature_names"])
    cols = unique_existing(path, wanted)
    print(f"Reading {label}: {path.name}, cols={len(cols)}", flush=True)
    df = pd.read_parquet(
        path,
        columns=cols,
        filters=[("date", ">=", pd.Timestamp(start)), ("date", "<=", pd.Timestamp(end))],
    )
    df["source_cache"] = label
    return df


def score_phasec(df: pd.DataFrame, bundle: dict) -> pd.DataFrame:
    raw_prob, iso_prob = base.predict_raw_and_iso(bundle, df)
    df["raw_prob"] = raw_prob.astype(np.float64)
    df["iso_prob"] = iso_prob.astype(np.float64)
    return df


def load_scored_frame() -> tuple[pd.DataFrame, dict]:
    bundle = base.load_bundle(BUNDLE_PATH)
    print(
        "Bundle:",
        bundle.get("model_name"),
        "features",
        len(bundle["feature_names"]),
        "calibration",
        bundle.get("calibration_used"),
        flush=True,
    )
    long_df = read_part(CACHE_LONG, bundle, "2017-01-01", "2026-03-31", "long_2017_202603")
    latest_df = read_part(CACHE_LATEST, bundle, "2026-04-01", "2026-05-31", "latest_202604_202605")
    df = pd.concat([long_df, latest_df], ignore_index=True, sort=False)
    df["date"] = pd.to_datetime(df["date"])
    df["label_date"] = pd.to_datetime(df["label_date"], errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    df = df.sort_values(["date", "symbol", "source_cache"]).drop_duplicates(["date", "symbol"], keep="last")

    if "limit_up_like" in df.columns:
        df = df[df["limit_up_like"].fillna(0) != 1].copy()
    if "short_phase_days_3" in df.columns:
        df = df[df["short_phase_days_3"].fillna(0) >= 1].copy()

    for col in META_COLS:
        if col in df.columns and col not in {"date", "label_date", "symbol", "name"}:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    needed = ["actual", "next_high_return_pct", "next_close_return_pct", "next_low_return_pct"]
    before = len(df)
    df = df.dropna(subset=[c for c in needed if c in df.columns]).copy()
    df["actual"] = (df["actual"].astype(float) > 0.5).astype(int)
    df = score_phasec(df, bundle)
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["date_key"] = df["date"].dt.strftime("%Y-%m-%d")
    print(
        f"Scored frame: {len(df):,}/{before:,} rows, "
        f"{df['date_key'].nunique()} days, {df['date'].min().date()}..{df['date'].max().date()}",
        flush=True,
    )
    return df.reset_index(drop=True), bundle


def pct_prod(returns_pct: np.ndarray) -> float:
    if len(returns_pct) == 0:
        return 0.0
    clipped = np.clip(np.asarray(returns_pct, dtype=float) / 100.0, -0.95, 10.0)
    return float((np.prod(1.0 + clipped) - 1.0) * 100.0)


def safe_array(df: pd.DataFrame, col: str, fill: float = 0.0) -> np.ndarray:
    if col not in df.columns:
        return np.full(len(df), fill, dtype=np.float64)
    return pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(fill).to_numpy(dtype=np.float64)


def make_candidate_pool(df: pd.DataFrame, min_prob: float = 0.55) -> pd.DataFrame:
    mask = (df["raw_prob"] >= min_prob) | (df["iso_prob"] >= min_prob)
    out = df[mask].copy()
    print(
        f"Candidate pool >= {min_prob}: {len(out):,} rows, "
        f"{out['date_key'].nunique()} days",
        flush=True,
    )
    return out.reset_index(drop=True)


def period_mask(df: pd.DataFrame, start: str, end: str) -> np.ndarray:
    d = pd.to_datetime(df["date"])
    return ((d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))).to_numpy()


def choose_features(pool: pd.DataFrame, include_sector: bool = False) -> list[str]:
    base_cols = LIVE_SAFE_FEATURES + (SECTOR_PROXY_FEATURES if include_sector else [])
    cols: list[str] = []
    for col in base_cols:
        if col in pool.columns and col not in cols and not is_forbidden_feature(col):
            vals = pd.to_numeric(pool[col], errors="coerce")
            if vals.notna().mean() >= 0.60 and vals.nunique(dropna=True) >= 3:
                cols.append(col)
    return cols


def fit_surge_models(pool: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, dict]:
    train_mask = period_mask(pool, "2023-01-01", "2025-12-31")
    val_mask = period_mask(pool, "2025-01-01", "2025-12-31")
    if train_mask.sum() < 500:
        raise RuntimeError("Not enough train candidates for surge model")

    x = pool[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32)
    y5 = (pool["next_high_return_pct"].astype(float) >= 5.0).astype(int)
    y10 = (pool["next_high_return_pct"].astype(float) >= 9.8).astype(int)
    yh = pool["next_high_return_pct"].astype(float).clip(-20, 20)

    clf5 = LGBMClassifier(
        n_estimators=450,
        learning_rate=0.035,
        num_leaves=31,
        min_child_samples=120,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=6.0,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
        verbose=-1,
    )
    clf10 = LGBMClassifier(
        n_estimators=420,
        learning_rate=0.035,
        num_leaves=23,
        min_child_samples=140,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=8.0,
        random_state=43,
        n_jobs=-1,
        class_weight="balanced",
        verbose=-1,
    )
    reg = LGBMRegressor(
        n_estimators=420,
        learning_rate=0.035,
        num_leaves=31,
        min_child_samples=120,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=6.0,
        random_state=44,
        n_jobs=-1,
        verbose=-1,
    )

    print(f"Training surge models on {train_mask.sum():,} candidates, features={len(feature_cols)}", flush=True)
    clf5.fit(x.loc[train_mask], y5.loc[train_mask])
    clf10.fit(x.loc[train_mask], y10.loc[train_mask])
    reg.fit(x.loc[train_mask], yh.loc[train_mask])

    pool = pool.copy()
    pool["surge5_score"] = clf5.predict_proba(x)[:, 1]
    pool["limit10_score"] = clf10.predict_proba(x)[:, 1]
    pred_high = reg.predict(x)
    pool["pred_high_pct"] = np.clip(pred_high, -5, 12)
    high_scaled = (pool["pred_high_pct"] - pool["pred_high_pct"].quantile(0.05)) / (
        pool["pred_high_pct"].quantile(0.95) - pool["pred_high_pct"].quantile(0.05) + 1e-9
    )
    pool["surge_combo_score"] = (
        0.45 * pool["raw_prob"]
        + 0.25 * pool["surge5_score"]
        + 0.20 * pool["limit10_score"]
        + 0.10 * np.clip(high_scaled, 0, 1)
    )

    importance = pd.DataFrame(
        {
            "feature": feature_cols,
            "surge5_importance": clf5.feature_importances_,
            "limit10_importance": clf10.feature_importances_,
            "high_reg_importance": reg.feature_importances_,
        }
    )
    importance["total_importance"] = (
        importance["surge5_importance"] + importance["limit10_importance"] + importance["high_reg_importance"]
    )
    importance = importance.sort_values("total_importance", ascending=False).reset_index(drop=True)

    diag = {
        "train_candidates": int(train_mask.sum()),
        "validation_2025_candidates": int(val_mask.sum()),
        "features": len(feature_cols),
        "top_features": importance.head(20).to_dict("records"),
    }
    return pool, {"importance": importance, "diag": diag}


def eval_selection_from_ranked(sel_top: pd.DataFrame, top_n: int, exit_mode: str, min_days: int = 5) -> dict | None:
    sel = sel_top[sel_top["daily_rank"] <= top_n].copy()
    if sel.empty:
        return None

    close_ret = sel["next_close_return_pct"].astype(float).to_numpy()
    high_ret = sel["next_high_return_pct"].astype(float).to_numpy()
    low_ret = sel["next_low_return_pct"].astype(float).to_numpy()
    if exit_mode == "close":
        realized = close_ret
    elif exit_mode.startswith("tp"):
        tp = float(exit_mode[2:])
        realized = np.where(high_ret >= tp, tp, close_ret)
    elif "_tp" in exit_mode:
        left, right = exit_mode.split("_")
        sl = -float(left[2:])
        tp = float(right[2:])
        sl_hit = low_ret <= sl
        tp_hit = high_ret >= tp
        realized = close_ret.copy()
        realized[tp_hit & ~sl_hit] = tp
        realized[sl_hit] = sl
    elif exit_mode.startswith("sl"):
        sl = -float(exit_mode[2:])
        realized = np.where(low_ret <= sl, sl, close_ret)
    else:
        raise ValueError(exit_mode)
    sel["realized_return_pct"] = realized

    daily = sel.groupby("date_key")["realized_return_pct"].mean().to_numpy()
    tickets = len(sel)
    if len(daily) < min_days or tickets < min_days:
        return None
    high1 = float((sel["next_high_return_pct"] >= 1.0).mean())
    high3 = float((sel["next_high_return_pct"] >= 3.0).mean())
    high5 = float((sel["next_high_return_pct"] >= 5.0).mean())
    high7 = float((sel["next_high_return_pct"] >= 7.0).mean())
    lim10 = float((sel["next_high_return_pct"] >= 9.8).mean())
    std = float(np.std(daily, ddof=1)) if len(daily) > 2 else 0.0
    sharpe = float(np.mean(daily) / std * math.sqrt(252)) if std > 0 else None
    return {
        "signal_days": int(len(daily)),
        "tickets": int(tickets),
        "total_return_pct": round(pct_prod(daily), 2),
        "avg_daily_return_pct": round(float(np.mean(daily)), 3),
        "daily_win_rate": round(float((daily > 0).mean()), 4),
        "ticket_win_rate": round(float((realized > 0).mean()), 4),
        "high1_rate": round(high1, 4),
        "high3_rate": round(high3, 4),
        "high5_rate": round(high5, 4),
        "high7_rate": round(high7, 4),
        "limit10_rate": round(lim10, 4),
        "sharpe": round(sharpe, 2) if sharpe is not None else None,
        "max_daily_loss_pct": round(float(np.min(daily)), 2),
        "max_daily_gain_pct": round(float(np.max(daily)), 2),
    }


def build_rule_masks(df: pd.DataFrame) -> list[tuple[str, np.ndarray]]:
    n = len(df)
    raw = safe_array(df, "raw_prob")
    iso = safe_array(df, "iso_prob")
    surge = safe_array(df, "surge_combo_score")
    turnover = safe_array(df, "turnover")
    close = safe_array(df, "close")
    rsi6 = safe_array(df, "rsi_6", 50.0)
    vol = safe_array(df, "volume_z_20")
    amt = safe_array(df, "amount_z_20")
    rng = safe_array(df, "range_pct")
    cp = safe_array(df, "close_position", 0.5)

    masks: list[tuple[str, np.ndarray]] = []
    for thr in [0.65, 0.70, 0.73, 0.75, 0.78]:
        masks.append((f"raw>={thr:.2f}", raw >= thr))
        masks.append((f"iso>={thr:.2f}", iso >= thr))
    for q in [0.70, 0.80, 0.90]:
        val = float(np.nanquantile(surge, q))
        masks.append((f"surge_q{int(q*100)}>={val:.3f}", surge >= val))

    refiners = [
        ("none", np.ones(n, dtype=bool)),
        ("turnover_3_20", (turnover >= 3) & (turnover <= 20)),
        ("turnover_5_30", (turnover >= 5) & (turnover <= 30)),
        ("close_3_80", (close >= 3) & (close <= 80)),
        ("rsi6<=55", rsi6 <= 55),
        ("rsi6<=45", rsi6 <= 45),
        ("volume_z>=0", vol >= 0),
        ("amount_z>=0", amt >= 0),
        ("t3_20_rsi55", (turnover >= 3) & (turnover <= 20) & (rsi6 <= 55)),
        ("t5_30_vol0", (turnover >= 5) & (turnover <= 30) & (vol >= 0)),
        ("t5_30_amt0", (turnover >= 5) & (turnover <= 30) & (amt >= 0)),
        ("vol0_rsi55", (vol >= 0) & (rsi6 <= 55)),
        ("amt0_rsi55", (amt >= 0) & (rsi6 <= 55)),
    ]
    combined: list[tuple[str, np.ndarray]] = []
    for mname, mmask in masks:
        for rname, rmask in refiners:
            combined.append((mname if rname == "none" else f"{mname}|{rname}", (mmask & rmask).astype(bool)))
    return combined


def search_rules(pool: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    rank_cols = ["raw_prob", "iso_prob", "surge5_score", "surge_combo_score"]
    top_ns = [1, 2, 3, 5]
    exits = ["close", "tp5", "tp7", "tp10", "sl2_tp5"]
    masks = build_rule_masks(pool)
    max_top_n = max(top_ns)

    all_rows: list[dict] = []
    print(f"Searching rules: masks={len(masks)}, rank_cols={rank_cols}", flush=True)
    t0 = time.time()
    for mi, (mask_name, base_mask) in enumerate(masks, 1):
        if base_mask.sum() < 20:
            continue
        for rank_col in rank_cols:
            need_cols = [
                "date",
                "date_key",
                "raw_prob",
                rank_col,
                "next_close_return_pct",
                "next_high_return_pct",
                "next_low_return_pct",
            ]
            need_cols = list(dict.fromkeys([c for c in need_cols if c in pool.columns]))
            ranked = pool.loc[base_mask, need_cols].copy()
            if ranked.empty:
                continue
            ranked[rank_col] = pd.to_numeric(ranked[rank_col], errors="coerce").fillna(-1e9)
            ranked["raw_prob"] = pd.to_numeric(ranked["raw_prob"], errors="coerce").fillna(-1e9)
            ranked = ranked.sort_values(["date_key", rank_col, "raw_prob"], ascending=[True, False, False])
            ranked["daily_rank"] = ranked.groupby("date_key").cumcount() + 1
            ranked = ranked[ranked["daily_rank"] <= max_top_n].copy()
            if len(ranked) < 20:
                continue
            for top_n in top_ns:
                for exit_mode in exits:
                    row = {
                        "mask": mask_name,
                        "rank_col": rank_col,
                        "top_n": top_n,
                        "exit_mode": exit_mode,
                    }
                    ok = True
                    for period, start, end in PERIODS:
                        pm = (ranked["date"] >= pd.Timestamp(start)) & (ranked["date"] <= pd.Timestamp(end))
                        min_days = 2 if period == "may_2026_partial" else 5
                        ev = eval_selection_from_ranked(ranked[pm], top_n, exit_mode, min_days=min_days)
                        if ev is None:
                            ok = False
                            break
                        row[period] = ev
                    if ok:
                        all_rows.append(row)
        if mi % 10 == 0:
            print(
                f"  masks {mi}/{len(masks)} checked, kept={len(all_rows)}, elapsed={time.time()-t0:.0f}s",
                flush=True,
            )

    def score_row(row: dict) -> float:
        dev = row["dev_2023_2025"]
        q1 = row["q1_2026"]
        apr = row["apr_2026"]
        may = row["may_2026_partial"]
        stress = row["stress_2017_2022"]
        # Favor robust recent behavior and surge quality, but penalize weak daily
        # win and large losses to avoid pure overfit-to-total-return choices.
        score = 0.0
        score += 0.20 * min(dev["total_return_pct"], 600)
        score += 0.25 * min(q1["total_return_pct"], 250)
        score += 0.25 * min(apr["total_return_pct"], 180)
        score += 0.10 * min(may["total_return_pct"], 120)
        score += 0.10 * min(stress["total_return_pct"], 500)
        score += 120 * (min(q1["daily_win_rate"], apr["daily_win_rate"], may["daily_win_rate"]) - 0.50)
        score += 80 * (min(q1["high5_rate"], apr["high5_rate"], may["high5_rate"]) - 0.20)
        score += 40 * (min(q1["limit10_rate"], apr["limit10_rate"], may["limit10_rate"]) - 0.05)
        score += 2.5 * min(q1["max_daily_loss_pct"], apr["max_daily_loss_pct"], may["max_daily_loss_pct"], 0)
        if q1["signal_days"] < 10 or apr["signal_days"] < 8:
            score -= 60
        if apr["total_return_pct"] < 0 or q1["total_return_pct"] < 0:
            score -= 90
        return float(score)

    for row in all_rows:
        row["robust_score"] = round(score_row(row), 4)
    top_rows = sorted(all_rows, key=lambda r: r["robust_score"], reverse=True)[:50]
    return top_rows, all_rows


def bucket_lift(pool: pd.DataFrame, feature_cols: list[str], importance: pd.DataFrame) -> list[dict]:
    cols = [c for c in importance["feature"].head(18).tolist() if c in feature_cols]
    rows: list[dict] = []
    eval_mask = period_mask(pool, "2026-01-01", "2026-05-31")
    eval_df = pool[eval_mask].copy()
    for col in cols:
        vals = pd.to_numeric(eval_df[col], errors="coerce")
        if vals.notna().sum() < 100 or vals.nunique(dropna=True) < 5:
            continue
        try:
            bins = pd.qcut(vals.rank(method="first"), 5, labels=False, duplicates="drop")
        except Exception:
            continue
        for b in sorted(pd.Series(bins).dropna().unique()):
            sub = eval_df[pd.Series(bins, index=eval_df.index) == b]
            if len(sub) < 20:
                continue
            rows.append(
                {
                    "feature": col,
                    "bucket": int(b),
                    "count": int(len(sub)),
                    "value_min": round(float(pd.to_numeric(sub[col], errors="coerce").min()), 4),
                    "value_max": round(float(pd.to_numeric(sub[col], errors="coerce").max()), 4),
                    "avg_next_high": round(float(sub["next_high_return_pct"].mean()), 3),
                    "surge3_rate": round(float((sub["next_high_return_pct"] >= 3).mean()), 4),
                    "surge5_rate": round(float((sub["next_high_return_pct"] >= 5).mean()), 4),
                    "limit10_rate": round(float((sub["next_high_return_pct"] >= 9.8).mean()), 4),
                    "high1_rate": round(float((sub["next_high_return_pct"] >= 1).mean()), 4),
                }
            )
    return rows


def summarize_thresholds(pool: pd.DataFrame) -> list[dict]:
    rows = []
    for score_col in ["raw_prob", "iso_prob", "surge_combo_score"]:
        for thr in [0.60, 0.65, 0.70, 0.73, 0.75, 0.78, 0.80]:
            sub = pool[pool[score_col] >= thr]
            if sub.empty:
                continue
            rows.append(
                {
                    "score_col": score_col,
                    "threshold": thr,
                    "tickets": int(len(sub)),
                    "days": int(sub["date_key"].nunique()),
                    "high1_rate": round(float((sub["next_high_return_pct"] >= 1).mean()), 4),
                    "surge3_rate": round(float((sub["next_high_return_pct"] >= 3).mean()), 4),
                    "surge5_rate": round(float((sub["next_high_return_pct"] >= 5).mean()), 4),
                    "limit10_rate": round(float((sub["next_high_return_pct"] >= 9.8).mean()), 4),
                    "avg_next_high": round(float(sub["next_high_return_pct"].mean()), 3),
                }
            )
    return rows


def write_outputs(
    pool: pd.DataFrame,
    feature_cols: list[str],
    model_diag: dict,
    top_rules: list[dict],
    all_rules: list[dict],
    lift_rows: list[dict],
    threshold_rows: list[dict],
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / f"{RUN_TAG}.json"
    top_csv = OUT_DIR / f"{RUN_TAG}_top_rules.csv"
    lift_csv = OUT_DIR / f"{RUN_TAG}_feature_lift.csv"
    thresh_csv = OUT_DIR / f"{RUN_TAG}_thresholds.csv"
    scored_path = OUT_DIR / f"{RUN_TAG}_scored_candidates.parquet"
    md_path = DOC_DIR / f"{RUN_TAG}.md"

    pd.DataFrame(top_rules).to_csv(top_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(lift_rows).to_csv(lift_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(threshold_rows).to_csv(thresh_csv, index=False, encoding="utf-8-sig")
    keep_cols = [
        "date",
        "label_date",
        "symbol",
        "name",
        "raw_prob",
        "iso_prob",
        "surge5_score",
        "limit10_score",
        "pred_high_pct",
        "surge_combo_score",
        "actual",
        "next_high_return_pct",
        "next_close_return_pct",
        "next_low_return_pct",
    ] + [c for c in feature_cols if c in pool.columns]
    keep_cols = list(dict.fromkeys([c for c in keep_cols if c in pool.columns]))
    pool[keep_cols].to_parquet(scored_path, index=False)

    payload = {
        "run_tag": RUN_TAG,
        "generated_at": pd.Timestamp.now().isoformat(),
        "bundle_path": str(BUNDLE_PATH),
        "cache_long": str(CACHE_LONG),
        "cache_latest": str(CACHE_LATEST),
        "candidate_rows": int(len(pool)),
        "candidate_days": int(pool["date_key"].nunique()),
        "feature_cols": feature_cols,
        "model_diag": model_diag,
        "top_rules": top_rules[:20],
        "thresholds": threshold_rows,
        "output_files": {
            "json": str(json_path),
            "top_rules_csv": str(top_csv),
            "feature_lift_csv": str(lift_csv),
            "threshold_csv": str(thresh_csv),
            "scored_candidates": str(scored_path),
            "md": str(md_path),
        },
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    best = top_rules[0] if top_rules else None
    lines = [
        f"# PhaseC Surge Analysis - {RUN_TAG}",
        "",
        "## Guardrails",
        "",
        "- PhaseC remains first-stage model; this run does not retrain PhaseC.",
        "- Primary surge scorer excludes hard moneyflow/post-close/minute full-day features.",
        "- 2026 windows are reported separately; the result is not marked production-ready without web/live parity.",
        "",
        "## Data",
        "",
        f"- Candidate rows: {len(pool):,}",
        f"- Candidate days: {pool['date_key'].nunique():,}",
        f"- Feature count used by surge model: {len(feature_cols)}",
        "",
        "## Top Surge Features",
        "",
    ]
    for row in model_diag["top_features"][:15]:
        lines.append(
            f"- {row['feature']}: total={row['total_importance']}, "
            f"surge5={row['surge5_importance']}, limit10={row['limit10_importance']}"
        )
    lines.extend(["", "## Best Robust Rule", ""])
    if best:
        lines.extend(
            [
                f"- mask: `{best['mask']}`",
                f"- rank_col: `{best['rank_col']}`",
                f"- top_n: `{best['top_n']}`",
                f"- exit_mode: `{best['exit_mode']}`",
                f"- robust_score: `{best['robust_score']}`",
                "",
            ]
        )
        for period, *_ in PERIODS:
            ev = best[period]
            lines.append(
                f"- {period}: return={ev['total_return_pct']}%, days={ev['signal_days']}, "
                f"daily_win={ev['daily_win_rate']}, high5={ev['high5_rate']}, limit10={ev['limit10_rate']}, "
                f"max_loss={ev['max_daily_loss_pct']}%"
            )
    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- JSON: `{json_path}`",
            f"- Top rules CSV: `{top_csv}`",
            f"- Feature lift CSV: `{lift_csv}`",
            f"- Threshold CSV: `{thresh_csv}`",
            f"- Scored candidates: `{scored_path}`",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {md_path}", flush=True)


def main() -> None:
    t0 = time.time()
    df, _bundle = load_scored_frame()
    pool = make_candidate_pool(df, 0.55)
    feature_cols = choose_features(pool, include_sector=False)
    forbidden = [c for c in feature_cols if is_forbidden_feature(c)]
    if forbidden:
        raise RuntimeError(f"Forbidden features leaked into primary surge model: {forbidden}")
    pool, model_info = fit_surge_models(pool, feature_cols)
    importance = model_info["importance"]
    model_diag = model_info["diag"]
    lift_rows = bucket_lift(pool, feature_cols, importance)
    threshold_rows = summarize_thresholds(pool)
    top_rules, all_rules = search_rules(pool)
    write_outputs(pool, feature_cols, model_diag, top_rules, all_rules, lift_rows, threshold_rows)
    print(f"Done in {(time.time() - t0) / 60.0:.1f} min", flush=True)
    if top_rules:
        print("Best rule:", json.dumps(top_rules[0], ensure_ascii=False)[:2000], flush=True)


if __name__ == "__main__":
    main()

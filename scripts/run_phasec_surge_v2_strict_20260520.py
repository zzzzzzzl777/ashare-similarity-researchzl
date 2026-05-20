"""PhaseC Surge Scorer v2 - Strict (high-minus-2 oriented).

Built on top of codex's `run_phasec_live_safe_surge_optimizer_20260520.py`.
Adds the rigour gaps identified vs the project methodology:

1. **5-seed ensemble** for OOF and forward - final probability = mean over seeds.
2. **high-minus-2 regression head** - target = min(next_high_pct, 20) - 2.0
   (matches the user's execution: sells 2pp below intraday high).
3. **AND acceptance gate** (no weighted scoring) on development OOF window.
   Pass requires: daily_win >= 60%, ticket_win >= 55%, monthly_pos_ratio >= 75%,
   sharpe >= 1.5, max_drawdown >= -15%, high5_rate >= 30%, high10_rate >= 12%.
   Project methodology: at least 4/5 seeds must individually pass the AND gate.
4. **Cross-year feature importance stability** - train once per year on prior
   data, record per-year top-30. Keep only features that land in top-30 in
   every year (>= 4 of 5 years). This filter runs BEFORE the final ensemble.

Lockbox split (current default):
  Rule selection: 2023-05-01 to 2025-12-31 OOF only.
  Final-unseen: 2026-01 to 2026-05 (report only, never used for rule selection).

Inputs (reused from codex without recomputation):
  E:/.../phasec_surge_analysis_20260520_scored_candidates.parquet  (88 cols, 645k rows)

Outputs:
  E:/.../phasec_surge_v2_strict_20260520_scored.parquet           (full pool + new scores)
  E:/.../phasec_surge_v2_strict_20260520_models.pkl               (5-seed ensemble bundle)
  E:/.../phasec_surge_v2_strict_20260520_acceptance.json          (AND gate verdict)
  E:/.../phasec_surge_v2_strict_20260520_daily_picks_2026.csv     (daily top-K picks)
  E:/.../phasec_surge_v2_strict_20260520_feature_stability.csv    (per-year importance)
"""

from __future__ import annotations

import io
import json
import math
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

try:
    from lightgbm import LGBMClassifier, LGBMRegressor
except Exception as exc:
    raise RuntimeError("lightgbm is required") from exc


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
OUT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
RUN_TAG = "phasec_surge_v2_strict_20260520"
INPUT_SCORED = OUT_DIR / "phasec_surge_analysis_20260520_scored_candidates.parquet"

SEEDS = [42, 1729, 8675309, 31337, 271828]
HIGH2_CAP = 20.0
HC_THR = 0.61

# Lockbox split:
#   Dev/rule selection: 2023-05-01 .. 2025-12-31, using OOF scores only.
#   Final-unseen: 2026-01-01 .. 2026-05-31, report only.
TRAIN_END = "2025-12-31"
DEV_START = "2023-05-01"
DEV_END = "2025-12-31"
FORWARD_START = "2026-01-01"
FORWARD_END = "2026-05-31"

# Per-year importance stability years (rolling: train on prior, score that year, record importance)
STABILITY_YEARS = [2021, 2022, 2023, 2024, 2025]
TOP_K_FEAT = 30  # feature must land in top-30 importance every year to survive

# AND acceptance gate thresholds (per-seed; 4/5 seeds must pass)
GATE = {
    "daily_win": 0.60,
    "ticket_win": 0.55,
    "monthly_pos_ratio": 0.75,
    "sharpe": 1.5,
    "max_drawdown_pct": -15.0,
    "high5_rate": 0.30,
    "high10_rate": 0.12,
    "min_signal_days": 60,  # final-unseen window needs >=60 days
}

FORBIDDEN_PATTERNS = [
    "tushare_net_mf", "tushare_mf_", "tushare_ff_adjusted_flow",
    "minute_last_30min", "minute_vwap", "tushare_last_30min",
    "tushare_vwap", "tushare_close_vs_vwap",
    "auction_close", "close_auction", "post_close", "postclose",
]

META_AND_TARGET_COLS = {
    "date", "label_date", "date_key", "month", "symbol", "name", "actual",
    "next_high_return_pct", "next_close_return_pct", "next_low_return_pct",
    "source_cache",
    "surge5_score", "limit10_score", "pred_high_pct", "surge_combo_score",
    "safe_surge5_score", "safe_limit10_score", "safe_pred_high_pct",
    "safe_combo_score", "safe_high2_pred", "score_source",
}


def is_forbidden(name: str) -> bool:
    low = name.lower()
    return any(p in low for p in FORBIDDEN_PATTERNS)


def choose_live_safe_features(df: pd.DataFrame) -> list[str]:
    cols = []
    for col in df.columns:
        if col in META_AND_TARGET_COLS or is_forbidden(col):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            vals = pd.to_numeric(df[col], errors="coerce")
            if vals.notna().mean() >= 0.70 and vals.nunique(dropna=True) >= 5:
                cols.append(col)
    for must in ["raw_prob", "iso_prob"]:
        if must in df.columns and must not in cols:
            cols.insert(0, must)
    return cols


def lgb_params(seed: int, target: str, n_est: int = 360) -> dict:
    common = {
        "n_estimators": n_est,
        "learning_rate": 0.035,
        "num_leaves": 31,
        "max_depth": -1,
        "min_child_samples": 120,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "reg_lambda": 8.0,
        "random_state": seed,
        "n_jobs": -1,
        "verbose": -1,
    }
    if target == "limit10":
        common.update({"num_leaves": 23, "min_child_samples": 150, "reg_lambda": 10.0})
    if target == "high2_reg":
        common.update({"num_leaves": 27, "reg_lambda": 6.0})
    return common


def make_targets(train_df: pd.DataFrame) -> dict[str, np.ndarray]:
    high = train_df["next_high_return_pct"].astype(float).to_numpy()
    return {
        "surge5": (high >= 5.0).astype(int),
        "limit10": (high >= 9.8).astype(int),
        "high_reg": np.clip(high, -20, 20),
        "high2_reg": np.clip(np.minimum(high, HIGH2_CAP) - 2.0, -22, HIGH2_CAP - 2.0),
    }


def fit_four_heads(x_train: pd.DataFrame, train_df: pd.DataFrame, seed: int):
    targets = make_targets(train_df)
    clf5 = LGBMClassifier(**lgb_params(seed, "surge5"), class_weight="balanced")
    clf10 = LGBMClassifier(**lgb_params(seed + 100, "limit10"), class_weight="balanced")
    reg_h = LGBMRegressor(**lgb_params(seed + 200, "high_reg"))
    reg_h2 = LGBMRegressor(**lgb_params(seed + 300, "high2_reg"))
    clf5.fit(x_train, targets["surge5"])
    clf10.fit(x_train, targets["limit10"])
    reg_h.fit(x_train, targets["high_reg"])
    reg_h2.fit(x_train, targets["high2_reg"])
    return clf5, clf10, reg_h, reg_h2


def predict_four_heads(models, x_pred: pd.DataFrame) -> dict[str, np.ndarray]:
    clf5, clf10, reg_h, reg_h2 = models
    return {
        "surge5_prob": clf5.predict_proba(x_pred)[:, 1],
        "limit10_prob": clf10.predict_proba(x_pred)[:, 1],
        "pred_high": np.clip(reg_h.predict(x_pred), -10, 20),
        "pred_high2": np.clip(reg_h2.predict(x_pred), -10, HIGH2_CAP - 2.0),
    }


def cross_year_feature_stability(
    df: pd.DataFrame, x_full: pd.DataFrame, all_features: list[str]
) -> tuple[list[str], pd.DataFrame]:
    """Train one model per year on prior data; record top-K features each year.
    Keep features that appear in top-K in >= 4 of len(STABILITY_YEARS) years."""
    rows = []
    feat_count = {f: 0 for f in all_features}

    for year in STABILITY_YEARS:
        train_idx = df.index[df["date"] < pd.Timestamp(f"{year}-01-01")].to_numpy()
        if len(train_idx) < 20_000:
            print(f"  stability fold {year}: skip (train={len(train_idx)})", flush=True)
            continue
        sub = df.loc[train_idx]
        targets = make_targets(sub)
        # Use surge5 as the importance proxy (binary, fast, well-defined)
        clf = LGBMClassifier(**lgb_params(42, "surge5", n_est=200), class_weight="balanced")
        clf.fit(x_full.loc[train_idx], targets["surge5"])
        imp = clf.feature_importances_
        order = np.argsort(-imp)[:TOP_K_FEAT]
        top_feats = [all_features[i] for i in order]
        for f in top_feats:
            feat_count[f] += 1
        for rank, idx_f in enumerate(order):
            rows.append({
                "year": year,
                "rank": rank + 1,
                "feature": all_features[idx_f],
                "importance": int(imp[idx_f]),
            })
        print(f"  stability fold {year}: train={len(train_idx):,}, top-{TOP_K_FEAT} recorded", flush=True)

    stab_df = pd.DataFrame(rows)
    n_years = len(STABILITY_YEARS)
    threshold = max(4, int(round(n_years * 0.8)))  # >= 4 of 5 years
    stable = sorted([f for f, c in feat_count.items() if c >= threshold])

    # Always keep the two PhaseC outputs even if they don't make top-30 every year
    for must in ["raw_prob", "iso_prob"]:
        if must in all_features and must not in stable:
            stable.append(must)

    print(f"  stable features (top-{TOP_K_FEAT} in >={threshold}/{n_years} years): {len(stable)}", flush=True)
    return stable, stab_df


def metrics_per_seed(
    df: pd.DataFrame, score_col: str, top_n: int = 3,
    start: str = DEV_START, end: str = DEV_END, source_filter=None,
) -> dict:
    """Daily top-K selection by score_col, realized = min(high,20)-2.
    Returns AND gate inputs for one window."""
    sub = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))].copy()
    if source_filter is not None and "score_source" in sub.columns:
        if isinstance(source_filter, (list, tuple, set)):
            sub = sub[sub["score_source"].isin(source_filter)]
        else:
            sub = sub[sub["score_source"] == source_filter]
    if sub.empty:
        return {"signal_days": 0, "start": start, "end": end, "source_filter": source_filter}
    sub = sub.sort_values(["date", score_col], ascending=[True, False])
    sub["rk"] = sub.groupby("date").cumcount() + 1
    pick = sub[sub["rk"] <= top_n].copy()
    if pick.empty:
        return {"signal_days": 0}
    high = pd.to_numeric(pick["next_high_return_pct"], errors="coerce").clip(-30, HIGH2_CAP)
    pick["realized"] = high - 2.0
    pick["high"] = high

    daily = pick.groupby("date")["realized"].mean().sort_index()
    # Monthly compound from daily means (NOT ticket compound, which inflates)
    daily_idx = pd.to_datetime(daily.index)
    monthly = daily.groupby(daily_idx.strftime("%Y-%m")).apply(
        lambda x: float((np.prod(1 + x.to_numpy() / 100.0) - 1) * 100)
    )
    sd = float(daily.std(ddof=0))
    sharpe = float(daily.mean() / sd * math.sqrt(252)) if sd > 0 else 0.0
    cum = np.cumprod(1.0 + np.clip(daily.to_numpy() / 100, -0.95, 10.0))
    peak = np.maximum.accumulate(cum)
    mdd = float((cum / peak - 1).min() * 100) if cum.size else 0.0

    return {
        "start": start,
        "end": end,
        "source_filter": list(source_filter) if isinstance(source_filter, (list, tuple, set)) else source_filter,
        "signal_days": int(daily.shape[0]),
        "tickets": int(pick.shape[0]),
        "total_return_pct": round(float((np.prod(1 + daily / 100.0) - 1) * 100), 2),
        "avg_daily_return_pct": round(float(daily.mean()), 3),
        "daily_win_rate": round(float((daily > 0).mean()), 4),
        "ticket_win_rate": round(float((pick["realized"] > 0).mean()), 4),
        "monthly_pos_ratio": round(float((monthly > 0).mean()), 4),
        "sharpe": round(sharpe, 2),
        "max_drawdown_pct": round(mdd, 2),
        "high3_rate": round(float((pick["high"] >= 3).mean()), 4),
        "high5_rate": round(float((pick["high"] >= 5).mean()), 4),
        "high10_rate": round(float((pick["high"] >= 10).mean()), 4),
        "monthly_returns": {m: round(float(v), 2) for m, v in monthly.items()},
    }


def passes_and_gate(m: dict) -> tuple[bool, list[str]]:
    fails = []
    if m.get("signal_days", 0) < GATE["min_signal_days"]:
        fails.append(f"signal_days {m.get('signal_days')} < {GATE['min_signal_days']}")
    if m.get("daily_win_rate", 0) < GATE["daily_win"]:
        fails.append(f"daily_win {m.get('daily_win_rate'):.3f} < {GATE['daily_win']}")
    if m.get("ticket_win_rate", 0) < GATE["ticket_win"]:
        fails.append(f"ticket_win {m.get('ticket_win_rate'):.3f} < {GATE['ticket_win']}")
    if m.get("monthly_pos_ratio", 0) < GATE["monthly_pos_ratio"]:
        fails.append(f"monthly_pos {m.get('monthly_pos_ratio'):.3f} < {GATE['monthly_pos_ratio']}")
    if m.get("sharpe", 0) < GATE["sharpe"]:
        fails.append(f"sharpe {m.get('sharpe')} < {GATE['sharpe']}")
    if m.get("max_drawdown_pct", -100) < GATE["max_drawdown_pct"]:
        fails.append(f"mdd {m.get('max_drawdown_pct')} < {GATE['max_drawdown_pct']}")
    if m.get("high5_rate", 0) < GATE["high5_rate"]:
        fails.append(f"high5 {m.get('high5_rate'):.3f} < {GATE['high5_rate']}")
    if m.get("high10_rate", 0) < GATE["high10_rate"]:
        fails.append(f"high10 {m.get('high10_rate'):.3f} < {GATE['high10_rate']}")
    return (len(fails) == 0, fails)


def main():
    t0 = time.time()
    print("=" * 78)
    print(f"  PhaseC Surge Scorer v2 (Strict) - high-minus-2 oriented")
    print(f"  Lockbox: train<={TRAIN_END} | dev={DEV_START}..{DEV_END} | "
          f"final_unseen={FORWARD_START}..{FORWARD_END}")
    print(f"  Seeds: {SEEDS}")
    print("=" * 78)

    # Load codex's pre-scored pool (no recompute of PhaseC)
    print(f"\n[Phase 1] Load scored pool: {INPUT_SCORED.name}")
    df = pd.read_parquet(INPUT_SCORED)
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    df = df.sort_values(["date", "symbol"]).drop_duplicates(["date", "symbol"], keep="last")
    df = df[df["iso_prob"] >= HC_THR].copy().reset_index(drop=True)
    df["date_key"] = df["date"].dt.strftime("%Y-%m-%d")
    print(f"  HC pool: {len(df):,} rows | {df['date_key'].nunique()} days | "
          f"{df['date'].min().date()}..{df['date'].max().date()}")

    # Choose live-safe features
    print(f"\n[Phase 2] Select live-safe features")
    feat_all = choose_live_safe_features(df)
    print(f"  live-safe features: {len(feat_all)}")
    x_all = df[feat_all].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32)

    # Cross-year feature stability filter (uses surge5 as importance proxy)
    print(f"\n[Phase 3] Cross-year feature stability")
    stable_feats, stab_df = cross_year_feature_stability(df, x_all, feat_all)
    stab_df.to_csv(OUT_DIR / f"{RUN_TAG}_feature_stability.csv", index=False, encoding="utf-8-sig")
    print(f"  stable features kept: {len(stable_feats)}")
    print(f"  stable_features={stable_feats}")
    x_stable = df[stable_feats].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32)

    # 5-seed ensemble: rolling OOF (2021-2025) + final forward (2026)
    print(f"\n[Phase 4] 5-seed ensemble training")
    score_keys = ["surge5_prob", "limit10_prob", "pred_high", "pred_high2"]
    # Per-seed score columns + ensemble means
    for k in score_keys:
        df[f"v2_{k}_mean"] = np.nan
        for s in SEEDS:
            df[f"v2_{k}_s{s}"] = np.nan
    df["score_source"] = "unscored"

    final_models_per_seed = {}
    fold_meta = []

    train_end_ts = pd.Timestamp(TRAIN_END)
    dev_start_ts = pd.Timestamp(DEV_START)
    dev_end_ts = pd.Timestamp(DEV_END)
    fwd_start_ts = pd.Timestamp(FORWARD_START)

    # OOF folds: for each year in STABILITY_YEARS, train on data < year, predict that year
    # This produces honest OOF probabilities for 2021-2025 (allowing dev metrics on 2025)
    for year in STABILITY_YEARS:
        train_idx = df.index[df["date"] < pd.Timestamp(f"{year}-01-01")].to_numpy()
        valid_idx = df.index[
            (df["date"] >= pd.Timestamp(f"{year}-01-01"))
            & (df["date"] <= pd.Timestamp(f"{year}-12-31"))
        ].to_numpy()
        if len(train_idx) < 20_000 or len(valid_idx) == 0:
            continue
        print(f"  OOF fold {year}: train={len(train_idx):,}, valid={len(valid_idx):,}")
        sub_train = df.loc[train_idx]
        x_tr = x_stable.loc[train_idx]
        x_va = x_stable.loc[valid_idx]

        seed_preds = {k: [] for k in score_keys}
        for seed in SEEDS:
            models = fit_four_heads(x_tr, sub_train, seed=seed + year)
            preds = predict_four_heads(models, x_va)
            for k in score_keys:
                df.loc[valid_idx, f"v2_{k}_s{seed}"] = preds[k]
                seed_preds[k].append(preds[k])
        for k in score_keys:
            df.loc[valid_idx, f"v2_{k}_mean"] = np.mean(seed_preds[k], axis=0)
        df.loc[valid_idx, "score_source"] = "oof"
        fold_meta.append({"valid_year": year, "train_rows": int(len(train_idx)), "valid_rows": int(len(valid_idx))})

    # Final forward training: train on everything < 2026-01-01, score 2026
    final_train_idx = df.index[df["date"] < fwd_start_ts].to_numpy()
    forward_idx = df.index[df["date"] >= fwd_start_ts].to_numpy()
    print(f"  Final forward: train={len(final_train_idx):,}, forward={len(forward_idx):,}")
    sub_final = df.loc[final_train_idx]
    x_tr_final = x_stable.loc[final_train_idx]
    x_fwd = x_stable.loc[forward_idx]

    seed_preds_fwd = {k: [] for k in score_keys}
    for seed in SEEDS:
        models = fit_four_heads(x_tr_final, sub_final, seed=seed)
        final_models_per_seed[seed] = models
        preds = predict_four_heads(models, x_fwd)
        for k in score_keys:
            df.loc[forward_idx, f"v2_{k}_s{seed}"] = preds[k]
            seed_preds_fwd[k].append(preds[k])
    for k in score_keys:
        df.loc[forward_idx, f"v2_{k}_mean"] = np.mean(seed_preds_fwd[k], axis=0)
    df.loc[forward_idx, "score_source"] = "forward_final"

    # Composite score (matches codex's formula but uses our 5-seed means)
    df["v2_combo"] = (
        0.40 * df["raw_prob"].astype(float)
        + 0.25 * df["iso_prob"].astype(float)
        + 0.20 * df["v2_surge5_prob_mean"].fillna(0)
        + 0.10 * df["v2_limit10_prob_mean"].fillna(0)
        + 0.05 * np.clip((df["v2_pred_high2_mean"].fillna(0) + 4) / 16.0, 0, 1)
    )

    # -- Phase 5: AND acceptance gate on DEV OOF only --
    print(f"\n[Phase 5] AND acceptance gate (dev OOF={DEV_START}..{DEV_END})")
    print(f"  Forward {FORWARD_START}..{FORWARD_END} is report-only; never used for winner selection.")
    print(f"  Gate thresholds: {GATE}")

    # Score columns to evaluate (rank candidates by these)
    rank_cols_to_test = [
        ("v2_pred_high2_mean", 1), ("v2_pred_high2_mean", 2), ("v2_pred_high2_mean", 3),
        ("v2_combo", 1), ("v2_combo", 2), ("v2_combo", 3),
        ("v2_surge5_prob_mean", 1), ("v2_surge5_prob_mean", 2), ("v2_surge5_prob_mean", 3),
        ("raw_prob", 1), ("raw_prob", 3),  # baselines
        ("iso_prob", 1), ("iso_prob", 3),
    ]

    print(f"\n  --- Per-seed AND gate (4/5 must pass) ---")
    acceptance_per_config = []
    for rank_col, top_n in rank_cols_to_test:
        # Mean-ensemble metrics for rule selection are DEV OOF only.
        mean_metrics = metrics_per_seed(
            df, rank_col, top_n=top_n,
            start=DEV_START, end=DEV_END, source_filter="oof",
        )
        mean_pass, mean_fails = passes_and_gate(mean_metrics)
        forward_metrics = metrics_per_seed(
            df, rank_col, top_n=top_n,
            start=FORWARD_START, end=FORWARD_END, source_filter="forward_final",
        )

        # Per-seed metrics for stability check
        seed_passes = 0
        seed_results = []
        if rank_col.endswith("_mean"):
            base_key = rank_col.replace("_mean", "")
            for seed in SEEDS:
                seed_col = f"{base_key}_s{seed}"
                if seed_col in df.columns:
                    sm = metrics_per_seed(
                        df, seed_col, top_n=top_n,
                        start=DEV_START, end=DEV_END, source_filter="oof",
                    )
                    sp, sf = passes_and_gate(sm)
                    seed_results.append({"seed": seed, "passes": sp, "fails": sf, "metrics": sm})
                    if sp:
                        seed_passes += 1
            stability_pass = seed_passes >= 4
        else:
            stability_pass = mean_pass  # baseline: only one model

        verdict = "PASS" if (mean_pass and stability_pass) else "BLOCKED"
        acceptance_per_config.append({
            "rank_col": rank_col,
            "top_n": top_n,
            "mean_metrics": mean_metrics,
            "forward_metrics": forward_metrics,
            "mean_passes_gate": mean_pass,
            "mean_fails": mean_fails,
            "seeds_pass_count": seed_passes,
            "seeds_pass_threshold": 4,
            "stability_pass": stability_pass,
            "verdict": verdict,
            "seed_results": seed_results,
        })

        marker = "[PASS]" if verdict == "PASS" else "[FAIL]"
        sd = mean_metrics.get("signal_days", 0)
        tr = mean_metrics.get("total_return_pct", "n/a")
        dw = mean_metrics.get("daily_win_rate", 0)
        sh = mean_metrics.get("sharpe", 0)
        h5 = mean_metrics.get("high5_rate", 0)
        mdd = mean_metrics.get("max_drawdown_pct", "n/a")
        ftr = forward_metrics.get("total_return_pct", "n/a")
        fdw = forward_metrics.get("daily_win_rate", 0)
        try:
            print(f"  {marker} {rank_col:30s} top{top_n} | dev_days={sd} dev_tr={tr}% "
                  f"dev_dw={dw:.1%} sh={sh} h5={h5:.1%} mdd={mdd}% | "
                  f"fwd_tr={ftr}% fwd_dw={fdw:.1%} | seeds={seed_passes}/5 -> {verdict}")
            if mean_fails:
                print(f"    fails: {mean_fails[:3]}")
        except Exception as e:
            sys.stderr.write(f"  [print fallback] {rank_col} top{top_n} verdict={verdict} err={e}\n")

    # Eager-save scored parquet & acceptance BEFORE building daily picks,
    # so even if downstream crashes the AND gate output is preserved.
    print(f"\n[Phase 5b] Eager-save scored parquet & acceptance (crash-safe)")
    df.to_parquet(OUT_DIR / f"{RUN_TAG}_scored.parquet", index=False)
    eager_acceptance = {
        "run_tag": RUN_TAG,
        "generated_at": pd.Timestamp.now().isoformat(),
        "lockbox": {"train_end": TRAIN_END, "dev_range": [DEV_START, DEV_END],
                    "forward_range": [FORWARD_START, FORWARD_END]},
        "methodology": {
            "rule_selection": "dev OOF only",
            "forward_2026": "report only; excluded from winner selection",
        },
        "seeds": SEEDS,
        "stable_features_count": len(stable_feats),
        "stable_features": stable_feats,
        "gate": GATE,
        "configurations": [
            {k: v for k, v in c.items() if k != "seed_results"}
            for c in acceptance_per_config
        ],
        "any_config_passes": any(c["verdict"] == "PASS" for c in acceptance_per_config),
        "passing_configs_count": sum(1 for c in acceptance_per_config if c["verdict"] == "PASS"),
    }
    with (OUT_DIR / f"{RUN_TAG}_acceptance.json").open("w", encoding="utf-8") as f:
        json.dump(eager_acceptance, f, ensure_ascii=False, indent=2, default=str)
    print(f"  saved scored.parquet and acceptance.json")

    # -- Phase 6: Build daily picker for forward report window --
    print(f"\n[Phase 6] Daily picker (top-K per day on forward report window)")
    forward_df = df[df["date"] >= fwd_start_ts].copy()
    # Pick the best PASSING config by DEV OOF only (or best-by-dev-return if none pass).
    passing = [c for c in acceptance_per_config if c["verdict"] == "PASS"]
    if passing:
        best_cfg = max(passing, key=lambda c: c["mean_metrics"].get("total_return_pct", -1e9))
        print(f"  Best PASS config by dev OOF: {best_cfg['rank_col']} top{best_cfg['top_n']}")
    else:
        best_cfg = max(acceptance_per_config, key=lambda c: c["mean_metrics"].get("total_return_pct", -1e9))
        print(f"  No config PASSES the AND gate. Best-by-dev-return for diagnostic only:"
              f" {best_cfg['rank_col']} top{best_cfg['top_n']}")

    rc = best_cfg["rank_col"]
    tn = best_cfg["top_n"]
    forward_df = forward_df.sort_values(["date", rc], ascending=[True, False])
    forward_df["daily_rank"] = forward_df.groupby("date").cumcount() + 1
    picks = forward_df[forward_df["daily_rank"] <= tn].copy()
    picks_out = picks[[
        "date", "symbol", "raw_prob", "iso_prob",
        "v2_surge5_prob_mean", "v2_limit10_prob_mean",
        "v2_pred_high_mean", "v2_pred_high2_mean", "v2_combo",
        "next_high_return_pct", "next_close_return_pct", "daily_rank",
    ]].copy()
    picks_out["realized_high_minus_2"] = (
        pd.to_numeric(picks_out["next_high_return_pct"], errors="coerce").clip(-30, HIGH2_CAP) - 2.0
    )
    picks_out.to_csv(OUT_DIR / f"{RUN_TAG}_daily_picks_2026.csv",
                     index=False, encoding="utf-8-sig")

    # -- Phase 7: Persist artifacts --
    print(f"\n[Phase 7] Persisting models and final acceptance")

    # scored parquet already saved in Phase 5b

    # Save 5-seed final models
    bundle = {
        "run_tag": RUN_TAG,
        "seeds": SEEDS,
        "stable_features": stable_feats,
        "all_features": feat_all,
        "final_models_per_seed": final_models_per_seed,
        "fold_meta": fold_meta,
        "lockbox": {
            "train_end": TRAIN_END,
            "dev_range": [DEV_START, DEV_END],
            "forward_range": [FORWARD_START, FORWARD_END],
        },
        "gate": GATE,
    }
    with (OUT_DIR / f"{RUN_TAG}_models.pkl").open("wb") as f:
        pickle.dump(bundle, f)
    print(f"  models pkl: {OUT_DIR / f'{RUN_TAG}_models.pkl'}")

    # Re-save acceptance JSON with best_config + elapsed (replaces 5b eager copy)
    acceptance = {
        "run_tag": RUN_TAG,
        "generated_at": pd.Timestamp.now().isoformat(),
        "lockbox": bundle["lockbox"],
        "methodology": {
            "rule_selection": "dev OOF only",
            "forward_2026": "report only; excluded from winner selection",
        },
        "seeds": SEEDS,
        "stable_features_count": len(stable_feats),
        "stable_features": stable_feats,
        "gate": GATE,
        "configurations": [
            {k: v for k, v in c.items() if k != "seed_results"}
            for c in acceptance_per_config
        ],
        "best_config": {k: v for k, v in best_cfg.items() if k != "seed_results"},
        "any_config_passes": any(c["verdict"] == "PASS" for c in acceptance_per_config),
        "passing_configs_count": sum(1 for c in acceptance_per_config if c["verdict"] == "PASS"),
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    with (OUT_DIR / f"{RUN_TAG}_acceptance.json").open("w", encoding="utf-8") as f:
        json.dump(acceptance, f, ensure_ascii=False, indent=2, default=str)
    print(f"  acceptance json: {OUT_DIR / f'{RUN_TAG}_acceptance.json'}")
    print(f"  daily picks: {OUT_DIR / f'{RUN_TAG}_daily_picks_2026.csv'}")

    # Final summary
    print("\n" + "=" * 78)
    print(f"  SUMMARY")
    print("=" * 78)
    print(f"  Total time: {time.time()-t0:.0f}s")
    print(f"  Configs PASSING AND gate: {acceptance['passing_configs_count']}/{len(acceptance_per_config)}")
    if acceptance["any_config_passes"]:
        print(f"  Best PASS: {best_cfg['rank_col']} top{best_cfg['top_n']}")
        dm = best_cfg["mean_metrics"]
        fm = best_cfg["forward_metrics"]
        print(f"    dev_oof: total={dm.get('total_return_pct')}% sharpe={dm.get('sharpe')} "
              f"dw={dm.get('daily_win_rate'):.1%} h5={dm.get('high5_rate'):.1%} "
              f"mdd={dm.get('max_drawdown_pct')}% seeds={best_cfg['seeds_pass_count']}/5")
        print(f"    forward_report: total={fm.get('total_return_pct')}% sharpe={fm.get('sharpe')} "
              f"dw={fm.get('daily_win_rate'):.1%} h5={fm.get('high5_rate'):.1%} "
              f"mdd={fm.get('max_drawdown_pct')}%")
    else:
        print(f"  *** NO CONFIG PASSES AND GATE ***")
        print(f"  Best diagnostic only: {best_cfg['rank_col']} top{best_cfg['top_n']}")
        print(f"    fails: {best_cfg['mean_fails']}")
        fm = best_cfg["forward_metrics"]
        print(f"    forward_report: total={fm.get('total_return_pct')}% sharpe={fm.get('sharpe')} "
              f"dw={fm.get('daily_win_rate'):.1%} h5={fm.get('high5_rate'):.1%} "
              f"mdd={fm.get('max_drawdown_pct')}%")


if __name__ == "__main__":
    main()

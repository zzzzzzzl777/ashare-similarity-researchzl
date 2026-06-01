"""Surge Scorer: predict which HC candidates will surge highest next day.

Target: next_high_return_pct >= 5% (binary classification).
Features: 200 PhaseC selected features + raw_prob + iso_prob.
Train 2017-2024, Valid 2025H1, Test 2025H2-2026.
"""

from __future__ import annotations

import math
import pickle
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scripts.run_dual_model_strategy_search as base

PC_BUNDLE = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt"
)
CACHE_FULL = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_550a77f54882058f.parquet"
)

MODEL_OUT = ROOT / "models" / "surge_scorer_lgb.pkl"
OUT_DIR = Path(r"C:\Users\zzzzzzl\Desktop")

SURGE5_THR = 5.0
SURGE10_THR = 9.5


def pct_prod(arr):
    if len(arr) == 0:
        return 0.0
    v = np.clip(arr / 100.0, -0.95, 10.0)
    return float((np.prod(1.0 + v) - 1.0) * 100.0)


def main():
    t0 = time.time()
    print("=" * 70)
    print("  SURGE SCORER - LightGBM Training & Evaluation")
    print("=" * 70)

    # ── Phase 1: Load data & PhaseC scoring ──
    print("\n[Phase 1] Loading data & scoring...")
    bundle = base.load_bundle(PC_BUNDLE)
    feature_names = bundle["feature_names"]
    selected_idx = bundle["selected_indices"]
    selected_features = [feature_names[i] for i in selected_idx]

    df = base.load_scoring_frame(CACHE_FULL, bundle, "2017-01-01", "2026-05-31", "full")
    raw, iso = base.predict_raw_and_iso(bundle, df)
    df["raw_prob"] = raw
    df["iso_prob"] = iso

    hc = df[df["iso_prob"] >= 0.61].copy().reset_index(drop=True)
    hc["next_high_ret"] = hc["next_high_return_pct"].fillna(0)
    hc["surge5"] = (hc["next_high_ret"] >= SURGE5_THR).astype(int)
    hc["surge10"] = (hc["next_high_ret"] >= SURGE10_THR).astype(int)
    hc["date_str"] = hc["date"].astype(str).str[:10]

    print(f"  HC pool: {len(hc):,} rows, {hc['date_str'].nunique()} days")
    print(f"  surge5 rate: {hc['surge5'].mean():.1%}, surge10 rate: {hc['surge10'].mean():.1%}")

    # ── Phase 2: Feature matrix & time split ──
    print("\n[Phase 2] Building feature matrix & time split...")
    feat_cols = [f for f in selected_features if f in hc.columns] + ["raw_prob", "iso_prob"]
    print(f"  Feature columns: {len(feat_cols)}")

    X = hc[feat_cols].fillna(0).to_numpy(dtype=np.float32)
    y5 = hc["surge5"].to_numpy()
    dates = hc["date_str"].to_numpy()

    train_mask = dates < "2025-01-01"
    valid_mask = (dates >= "2025-01-01") & (dates < "2025-07-01")
    test_mask = dates >= "2025-07-01"

    X_train, y_train = X[train_mask], y5[train_mask]
    X_valid, y_valid = X[valid_mask], y5[valid_mask]
    X_test, y_test = X[test_mask], y5[test_mask]

    print(f"  Train: {len(X_train):,} ({y_train.mean():.1%} pos)")
    print(f"  Valid: {len(X_valid):,} ({y_valid.mean():.1%} pos)")
    print(f"  Test:  {len(X_test):,} ({y_test.mean():.1%} pos)")

    # ── Phase 3: Train LightGBM ──
    print("\n[Phase 3] Training LightGBM (surge5 target)...")
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    spw = neg_count / pos_count

    params = {
        "objective": "binary",
        "metric": "auc",
        "max_depth": 6,
        "num_leaves": 31,
        "n_estimators": 800,
        "learning_rate": 0.05,
        "min_child_samples": 100,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": spw,
        "verbosity": -1,
        "n_jobs": -1,
        "random_state": 42,
    }

    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_valid, y_valid)],
        callbacks=[
            lgb.early_stopping(50, verbose=True),
            lgb.log_evaluation(50),
        ],
    )

    best_iter = model.best_iteration_
    print(f"  Best iteration: {best_iter}")

    # Also train surge10 model
    print("\n  Training surge10 model...")
    y10_train = hc["surge10"].to_numpy()[train_mask]
    y10_valid = hc["surge10"].to_numpy()[valid_mask]
    spw10 = (y10_train == 0).sum() / max((y10_train == 1).sum(), 1)
    params10 = params.copy()
    params10["scale_pos_weight"] = spw10
    model10 = lgb.LGBMClassifier(**params10)
    model10.fit(
        X_train, y10_train,
        eval_set=[(X_valid, y10_valid)],
        callbacks=[
            lgb.early_stopping(50, verbose=True),
            lgb.log_evaluation(50),
        ],
    )
    print(f"  surge10 best iteration: {model10.best_iteration_}")

    # Also train regression model
    print("\n  Training regression model (target = next_high_ret)...")
    y_reg_train = hc["next_high_ret"].to_numpy()[train_mask].astype(np.float32)
    y_reg_valid = hc["next_high_ret"].to_numpy()[valid_mask].astype(np.float32)
    params_reg = {
        "objective": "regression",
        "metric": "rmse",
        "max_depth": 6,
        "num_leaves": 31,
        "n_estimators": 800,
        "learning_rate": 0.05,
        "min_child_samples": 100,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "verbosity": -1,
        "n_jobs": -1,
        "random_state": 42,
    }
    model_reg = lgb.LGBMRegressor(**params_reg)
    model_reg.fit(
        X_train, y_reg_train,
        eval_set=[(X_valid, y_reg_valid)],
        callbacks=[
            lgb.early_stopping(50, verbose=True),
            lgb.log_evaluation(50),
        ],
    )
    print(f"  Regression best iteration: {model_reg.best_iteration_}")

    # Save models
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_OUT, "wb") as f:
        pickle.dump({
            "model_surge5": model,
            "model_surge10": model10,
            "model_reg": model_reg,
            "feature_cols": feat_cols,
            "train_end": "2024-12-31",
            "valid_end": "2025-06-30",
        }, f)
    print(f"\n  Models saved: {MODEL_OUT}")

    # ── Phase 4: OOS Evaluation ──
    print("\n" + "=" * 70)
    print("  [Phase 4] OOS EVALUATION (2025-07 ~ 2026-05)")
    print("=" * 70)

    test_df = hc[test_mask].copy()
    surge5_prob = model.predict_proba(X_test)[:, 1]
    surge10_prob = model10.predict_proba(X_test)[:, 1]
    reg_pred = model_reg.predict(X_test)
    test_df["surge5_prob"] = surge5_prob
    test_df["surge10_prob"] = surge10_prob
    test_df["reg_pred"] = reg_pred

    # Decile analysis for each model
    for label, col in [("surge5_prob", "surge5_prob"),
                        ("surge10_prob", "surge10_prob"),
                        ("reg_pred", "reg_pred"),
                        ("iso_prob (baseline)", "iso_prob")]:
        print(f"\n  --- Decile analysis: {label} ---")
        vals = test_df[col].to_numpy()
        print(f"  {'Decile':<8} {'N':>6} {'big5%':>7} {'big10%':>7} {'avgH':>7} {'avgH_med':>8}")
        for d in range(10):
            lo = np.percentile(vals, d * 10)
            hi = np.percentile(vals, (d + 1) * 10)
            if d == 9:
                mask_d = vals >= lo
            else:
                mask_d = (vals >= lo) & (vals < hi)
            sub = test_df[mask_d]
            if len(sub) == 0:
                continue
            b5 = sub["surge5"].mean()
            b10 = sub["surge10"].mean()
            ah = sub["next_high_ret"].mean()
            ahm = sub["next_high_ret"].median()
            print(f"  D{d+1:<7} {len(sub):>6} {b5:>6.1%} {b10:>6.1%} {ah:>6.2f}% {ahm:>7.2f}%")

    # Top-K daily analysis
    print(f"\n  --- Daily Top-K analysis (surge5_prob) ---")
    print(f"  {'TopK':<6} {'Days':>5} {'Tix':>6} {'big5%':>7} {'big10%':>7} {'avgH':>7} {'avgH_med':>8}")
    for topk in [1, 2, 3, 5, 10]:
        daily_rows = []
        for d, grp in test_df.groupby("date_str"):
            top = grp.nlargest(topk, "surge5_prob")
            daily_rows.append(top)
        topk_df = pd.concat(daily_rows)
        n_days = test_df["date_str"].nunique()
        b5 = topk_df["surge5"].mean()
        b10 = topk_df["surge10"].mean()
        ah = topk_df["next_high_ret"].mean()
        ahm = topk_df["next_high_ret"].median()
        print(f"  Top{topk:<4} {n_days:>5} {len(topk_df):>6} {b5:>6.1%} {b10:>6.1%} {ah:>6.2f}% {ahm:>7.2f}%")

    # Same for regression model
    print(f"\n  --- Daily Top-K analysis (reg_pred) ---")
    print(f"  {'TopK':<6} {'Days':>5} {'Tix':>6} {'big5%':>7} {'big10%':>7} {'avgH':>7} {'avgH_med':>8}")
    for topk in [1, 2, 3, 5, 10]:
        daily_rows = []
        for d, grp in test_df.groupby("date_str"):
            top = grp.nlargest(topk, "reg_pred")
            daily_rows.append(top)
        topk_df = pd.concat(daily_rows)
        n_days = test_df["date_str"].nunique()
        b5 = topk_df["surge5"].mean()
        b10 = topk_df["surge10"].mean()
        ah = topk_df["next_high_ret"].mean()
        ahm = topk_df["next_high_ret"].median()
        print(f"  Top{topk:<4} {n_days:>5} {len(topk_df):>6} {b5:>6.1%} {b10:>6.1%} {ah:>6.2f}% {ahm:>7.2f}%")

    # Same for iso_prob baseline
    print(f"\n  --- Daily Top-K analysis (iso_prob baseline) ---")
    print(f"  {'TopK':<6} {'Days':>5} {'Tix':>6} {'big5%':>7} {'big10%':>7} {'avgH':>7} {'avgH_med':>8}")
    for topk in [1, 2, 3, 5, 10]:
        daily_rows = []
        for d, grp in test_df.groupby("date_str"):
            top = grp.nlargest(topk, "iso_prob")
            daily_rows.append(top)
        topk_df = pd.concat(daily_rows)
        n_days = test_df["date_str"].nunique()
        b5 = topk_df["surge5"].mean()
        b10 = topk_df["surge10"].mean()
        ah = topk_df["next_high_ret"].mean()
        ahm = topk_df["next_high_ret"].median()
        print(f"  Top{topk:<4} {n_days:>5} {len(topk_df):>6} {b5:>6.1%} {b10:>6.1%} {ah:>6.2f}% {ahm:>7.2f}%")

    # Feature importance
    print(f"\n  --- Feature Importance (surge5 model, top 25) ---")
    imp = model.feature_importances_
    idx_sort = np.argsort(imp)[::-1]
    for i in range(min(25, len(feat_cols))):
        fi = idx_sort[i]
        print(f"  {i+1:>3}. {feat_cols[fi]:45s} importance={imp[fi]:>6}")

    # Year-by-year stability
    print(f"\n  --- Year-by-Year Top Decile Performance (surge5_prob) ---")
    hc_all = hc.copy()
    surge5_all = model.predict_proba(X)[:, 1]
    hc_all["surge5_prob"] = surge5_all

    print(f"  {'Year':<6} {'N_HC':>7} {'TopDec_N':>8} {'big5%':>7} {'big10%':>7} {'avgH':>7}")
    for year in sorted(hc_all["date_str"].str[:4].unique()):
        yr = hc_all[hc_all["date_str"].str[:4] == year]
        if len(yr) < 500:
            continue
        p90 = np.percentile(yr["surge5_prob"], 90)
        top_dec = yr[yr["surge5_prob"] >= p90]
        b5 = top_dec["surge5"].mean()
        b10 = top_dec["surge10"].mean()
        ah = top_dec["next_high_ret"].mean()
        is_oos = " *OOS*" if year >= "2025" else ""
        print(f"  {year:<6} {len(yr):>7} {len(top_dec):>8} {b5:>6.1%} {b10:>6.1%} {ah:>6.2f}%{is_oos}")

    # ── Phase 5: Backtest ──
    print("\n" + "=" * 70)
    print("  [Phase 5] BACKTEST - Monthly Returns")
    print("=" * 70)

    # Use surge5_prob to pick daily top1/3/5
    test_df["month"] = test_df["date_str"].str[:7]
    close_ret = test_df["next_close_return_pct"].fillna(0).to_numpy()
    high_ret = test_df["next_high_ret"].to_numpy()
    low_ret = test_df["next_low_return_pct"].fillna(0).to_numpy()

    for topk in [1, 3, 5]:
        for tp_val in [5, 7, 10]:
            label = f"surge5_prob top{topk} tp{tp_val}"
            daily_rets = []
            daily_dates = []

            for d, grp in test_df.groupby("date_str"):
                top = grp.nlargest(topk, "surge5_prob")
                hr_top = top["next_high_ret"].to_numpy()
                cr_top = top["next_close_return_pct"].fillna(0).to_numpy()
                ret = np.where(hr_top >= tp_val, tp_val, cr_top)
                daily_rets.append(ret.mean())
                daily_dates.append(d)

            daily_rets = np.array(daily_rets)
            daily_dates = np.array(daily_dates)
            months = np.array([d[:7] for d in daily_dates])

            total_ret = pct_prod(daily_rets)
            dw = (daily_rets > 0).mean()
            sh_std = daily_rets.std(ddof=1)
            sharpe = daily_rets.mean() / sh_std * math.sqrt(252) if sh_std > 0 else 0

            print(f"\n  {label}: total={total_ret:.1f}% dw={dw:.1%} sharpe={sharpe:.2f}")
            print(f"  {'Month':<8} {'Days':>5} {'Return':>9} {'AvgD':>8} {'DWin':>6}")
            for m in sorted(set(months)):
                mm = months == m
                md = daily_rets[mm]
                mret = pct_prod(md)
                print(f"  {m:<8} {len(md):>5} {mret:>8.2f}% {md.mean():>7.3f}% {(md>0).mean():>5.1%}")

    # Also show regression model backtest for comparison
    print(f"\n  --- REGRESSION model backtest (top3 tp7) ---")
    daily_rets_reg = []
    daily_dates_reg = []
    for d, grp in test_df.groupby("date_str"):
        top = grp.nlargest(3, "reg_pred")
        hr_top = top["next_high_ret"].to_numpy()
        cr_top = top["next_close_return_pct"].fillna(0).to_numpy()
        ret = np.where(hr_top >= 7, 7, cr_top)
        daily_rets_reg.append(ret.mean())
        daily_dates_reg.append(d)
    daily_rets_reg = np.array(daily_rets_reg)
    daily_dates_reg = np.array(daily_dates_reg)
    months_reg = np.array([d[:7] for d in daily_dates_reg])
    total_reg = pct_prod(daily_rets_reg)
    dw_reg = (daily_rets_reg > 0).mean()
    sh_reg = daily_rets_reg.mean() / daily_rets_reg.std(ddof=1) * math.sqrt(252) if daily_rets_reg.std(ddof=1) > 0 else 0
    print(f"  reg top3 tp7: total={total_reg:.1f}% dw={dw_reg:.1%} sharpe={sh_reg:.2f}")
    for m in sorted(set(months_reg)):
        mm = months_reg == m
        md = daily_rets_reg[mm]
        mret = pct_prod(md)
        print(f"  {m:<8} {len(md):>5} {mret:>8.2f}% {md.mean():>7.3f}% {(md>0).mean():>5.1%}")

    # iso_prob baseline backtest
    print(f"\n  --- ISO_PROB baseline backtest (top3 tp7) ---")
    daily_rets_iso = []
    daily_dates_iso = []
    for d, grp in test_df.groupby("date_str"):
        top = grp.nlargest(3, "iso_prob")
        hr_top = top["next_high_ret"].to_numpy()
        cr_top = top["next_close_return_pct"].fillna(0).to_numpy()
        ret = np.where(hr_top >= 7, 7, cr_top)
        daily_rets_iso.append(ret.mean())
        daily_dates_iso.append(d)
    daily_rets_iso = np.array(daily_rets_iso)
    daily_dates_iso = np.array(daily_dates_iso)
    months_iso = np.array([d[:7] for d in daily_dates_iso])
    total_iso = pct_prod(daily_rets_iso)
    dw_iso = (daily_rets_iso > 0).mean()
    sh_iso = daily_rets_iso.mean() / daily_rets_iso.std(ddof=1) * math.sqrt(252) if daily_rets_iso.std(ddof=1) > 0 else 0
    print(f"  iso top3 tp7: total={total_iso:.1f}% dw={dw_iso:.1%} sharpe={sh_iso:.2f}")
    for m in sorted(set(months_iso)):
        mm = months_iso == m
        md = daily_rets_iso[mm]
        mret = pct_prod(md)
        print(f"  {m:<8} {len(md):>5} {mret:>8.2f}% {md.mean():>7.3f}% {(md>0).mean():>5.1%}")

    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  Total time: {time.time()-t0:.0f}s")
    print(f"  Model saved: {MODEL_OUT}")


if __name__ == "__main__":
    main()

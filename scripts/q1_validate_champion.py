"""Q1 External Validation for Phase 1 Champion (Trial #33).

Freezes the champion config from rolling CV Phase 1 and validates on Q1 2026.
Per Section 十六: train on full 2023-2025, predict Q1 2026.
"""
from __future__ import annotations

import json
import sys
import time
import math
import numpy as np
import pandas as pd
from datetime import date, datetime
from pathlib import Path

_SRC_DIR = Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_u95_optuna_rolling import (
    load_feature_cache, apply_limit_up_filter, get_feature_columns,
    select_features_stable_tail, apply_calibration, wilson_lower_95,
    audit_p0_exclusions, SEED, META_COLUMNS,
)

REPORT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")

# Frozen champion params from Trial #33
CHAMPION = {
    "trial_number": 33,
    "model_family": "lightgbm",
    "max_selected_features": 480,
    "calibration": "none",
    "num_leaves": 76,
    "max_depth": -1,
    "learning_rate": 0.027096358071349746,
    "n_estimators": 593,
    "min_child_samples": 254,
    "feature_fraction": 0.9349275185717871,
    "bagging_fraction": 0.6120965549608609,
    "bagging_freq": 6,
    "lambda_l1": 25.57722105581909,
    "lambda_l2": 27.99298067566846,
    "min_gain_to_split": 1.4493314584024874,
}

# U95 reference (Q1)
U95_REF = {
    "hc_accuracy": 0.754243,
    "wilson_lower_95": 0.746116,
    "hc_count": 11019,
    "hc_coverage": 0.256107,
    "brier": 0.219497,
}


def main():
    print("=" * 70)
    print("Q1 EXTERNAL VALIDATION - Phase 1 Champion (Trial #33)")
    print("=" * 70)
    print(f"Model: {CHAMPION['model_family']}")
    print(f"Features: {CHAMPION['max_selected_features']}")
    print(f"Calibration: {CHAMPION['calibration']}")
    print()

    # Load data
    print("Loading data...")
    df = load_feature_cache()
    df = apply_limit_up_filter(df)
    feature_cols = get_feature_columns(df)
    print(f"Features: {len(feature_cols)}, Rows: {len(df):,}")

    # Split: train = full 2023-2025, test = Q1 2026
    train_end = pd.Timestamp("2025-12-31")
    test_start = pd.Timestamp("2026-01-01")
    test_end = pd.Timestamp("2026-03-31")

    train_df = df[df["label_date"] <= train_end].copy()
    test_df = df[(df["date"] >= test_start) & (df["date"] <= test_end)].copy()

    print(f"Train: {len(train_df):,} rows (up to {train_end.date()})")
    print(f"Test:  {len(test_df):,} rows (Q1 2026: {test_start.date()} - {test_end.date()})")
    print(f"Train positive rate: {train_df['actual'].mean():.4f}")
    print(f"Test positive rate:  {test_df['actual'].mean():.4f}")

    # Extract features
    x_train_raw = train_df[feature_cols].to_numpy(dtype=np.float32)
    y_train = train_df["actual"].to_numpy(dtype=np.float32)
    x_test_raw = test_df[feature_cols].to_numpy(dtype=np.float32)
    y_test = test_df["actual"].to_numpy(dtype=np.float32)

    # Standardize (train stats only)
    train_mean = np.nanmean(x_train_raw, axis=0, keepdims=True)
    train_std = np.nanstd(x_train_raw, axis=0, keepdims=True)
    train_std = np.where(train_std < 1e-6, 1.0, train_std)
    x_train_std = np.nan_to_num((x_train_raw - train_mean) / train_std, nan=0.0, posinf=0.0, neginf=0.0)
    x_test_std = np.nan_to_num((x_test_raw - train_mean) / train_std, nan=0.0, posinf=0.0, neginf=0.0)

    # Feature selection on full train (stable_tail, 480 features)
    print(f"\nFeature selection (stable_tail, max={CHAMPION['max_selected_features']})...")
    t0 = time.time()
    selected_idx = select_features_stable_tail(
        x_train_std, y_train, feature_cols,
        max_features=CHAMPION["max_selected_features"]
    )
    selected_features = [feature_cols[i] for i in selected_idx]
    print(f"  Selected {len(selected_idx)} features in {time.time()-t0:.1f}s")

    # P0 audit
    violations = audit_p0_exclusions(selected_features)
    if violations:
        print(f"CRITICAL: P0 violations: {violations}")
        sys.exit(1)
    print("  P0 audit: PASS")

    x_train_sel = x_train_std[:, selected_idx]
    x_test_sel = x_test_std[:, selected_idx]

    # ES split for early stopping (80/20 by date)
    train_dates = train_df["label_date"].values
    sorted_dates = np.sort(np.unique(train_dates))
    split_point = int(len(sorted_dates) * 0.80)
    es_cutoff = sorted_dates[min(split_point, len(sorted_dates) - 1)]
    es_train_mask = train_dates <= es_cutoff
    es_valid_mask = train_dates > es_cutoff

    x_es_train = x_train_sel[es_train_mask]
    y_es_train = y_train[es_train_mask]
    x_es_valid = x_train_sel[es_valid_mask]
    y_es_valid = y_train[es_valid_mask]
    print(f"  ES split: train={len(x_es_train):,}, valid={len(x_es_valid):,}")

    # Train LightGBM with champion params
    import lightgbm as lgb
    print(f"\nTraining LightGBM...")
    t0 = time.time()
    model = lgb.LGBMClassifier(
        objective="binary",
        metric="binary_logloss",
        verbosity=-1,
        device="gpu",
        seed=SEED,
        num_leaves=CHAMPION["num_leaves"],
        max_depth=CHAMPION["max_depth"],
        learning_rate=CHAMPION["learning_rate"],
        n_estimators=CHAMPION["n_estimators"],
        min_child_samples=CHAMPION["min_child_samples"],
        feature_fraction=CHAMPION["feature_fraction"],
        bagging_fraction=CHAMPION["bagging_fraction"],
        bagging_freq=CHAMPION["bagging_freq"],
        lambda_l1=CHAMPION["lambda_l1"],
        lambda_l2=CHAMPION["lambda_l2"],
        min_gain_to_split=CHAMPION["min_gain_to_split"],
    )
    model.fit(
        x_es_train, y_es_train,
        eval_set=[(x_es_valid, y_es_valid)],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50, verbose=False),
            lgb.log_evaluation(period=0),
        ],
    )
    print(f"  Trained in {time.time()-t0:.1f}s, best_iteration={model.best_iteration_}")

    # Predict on Q1 test
    probs = model.predict_proba(x_test_sel)[:, 1]
    print(f"\nProbability distribution on Q1:")
    print(f"  min={probs.min():.4f}  p25={np.percentile(probs,25):.4f}  "
          f"p50={np.percentile(probs,50):.4f}  p75={np.percentile(probs,75):.4f}  "
          f"p95={np.percentile(probs,95):.4f}  max={probs.max():.4f}")

    # Compute metrics at various thresholds
    print(f"\n{'='*70}")
    print(f"Q1 2026 METRICS")
    print(f"{'='*70}")
    print(f"{'Threshold':>10} {'Count':>8} {'Correct':>8} {'Accuracy':>10} {'Wilson95':>10} {'Coverage':>10}")
    print(f"{'-'*60}")

    for thresh in [0.50, 0.55, 0.60, 0.65, 0.70, 0.72, 0.75, 0.78, 0.80, 0.82, 0.85]:
        mask = probs >= thresh
        count = int(mask.sum())
        if count > 0:
            correct = int(y_test[mask].sum())
            acc = correct / count
            wilson = wilson_lower_95(correct, count)
            coverage = count / len(y_test)
        else:
            correct = 0
            acc = 0.0
            wilson = 0.0
            coverage = 0.0
        print(f"{thresh:>10.2f} {count:>8} {correct:>8} {acc:>10.4f} {wilson:>10.4f} {coverage:>10.4f}")

    # Main comparison: prob>=0.75
    mask_075 = probs >= 0.75
    count_075 = int(mask_075.sum())
    if count_075 > 0:
        correct_075 = int(y_test[mask_075].sum())
        acc_075 = correct_075 / count_075
        wilson_075 = wilson_lower_95(correct_075, count_075)
        coverage_075 = count_075 / len(y_test)
    else:
        correct_075 = 0
        acc_075 = 0.0
        wilson_075 = 0.0
        coverage_075 = 0.0

    # Brier score
    brier = float(np.mean((probs - y_test) ** 2))

    # Overall HC (top 10%)
    n_top = max(1, int(len(probs) * 0.10))
    top_idx = np.argsort(probs)[-n_top:]
    top_correct = int(y_test[top_idx].sum())
    overall_hc_wilson = wilson_lower_95(top_correct, n_top)

    print(f"\n{'='*70}")
    print(f"CHAMPION vs U95 (Q1 2026)")
    print(f"{'='*70}")
    print(f"{'Metric':<25} {'Champion':>12} {'U95':>12} {'Delta':>12}")
    print(f"{'-'*60}")
    print(f"{'HC Accuracy (p>=0.75)':<25} {acc_075:>12.4f} {U95_REF['hc_accuracy']:>12.4f} {(acc_075-U95_REF['hc_accuracy'])*100:>+10.2f}pp")
    print(f"{'Wilson@0.75':<25} {wilson_075:>12.4f} {U95_REF['wilson_lower_95']:>12.4f} {(wilson_075-U95_REF['wilson_lower_95'])*100:>+10.2f}pp")
    print(f"{'Count@0.75':<25} {count_075:>12} {U95_REF['hc_count']:>12} {count_075-U95_REF['hc_count']:>+12}")
    print(f"{'Coverage@0.75':<25} {coverage_075:>12.4f} {U95_REF['hc_coverage']:>12.4f} {(coverage_075-U95_REF['hc_coverage'])*100:>+10.2f}pp")
    print(f"{'Brier':<25} {brier:>12.4f} {U95_REF['brier']:>12.4f} {(brier-U95_REF['brier'])*100:>+10.2f}pp")
    print(f"{'Overall HC Wilson (top10%)':<25} {overall_hc_wilson:>12.4f}")

    # Pass/Fail decision (Section 十七)
    print(f"\n{'='*70}")
    print("Q1 GATE DECISION (Section 十七)")
    print(f"{'='*70}")
    delta_wilson = (wilson_075 - U95_REF["wilson_lower_95"]) * 100
    if delta_wilson < -1.0:
        print(f"FAIL: Champion Wilson@0.75 = {wilson_075:.4f} is {abs(delta_wilson):.2f}pp below U95 ({U95_REF['wilson_lower_95']:.4f})")
        print("Decision: Retain U95 as production baseline.")
    elif delta_wilson < 1.0:
        print(f"BORDERLINE: Champion Wilson@0.75 = {wilson_075:.4f} is within ±1pp of U95 ({U95_REF['wilson_lower_95']:.4f})")
        print(f"Delta: {delta_wilson:+.2f}pp - Not significantly better, classify as research candidate only.")
    else:
        print(f"PASS: Champion Wilson@0.75 = {wilson_075:.4f} is {delta_wilson:.2f}pp above U95 ({U95_REF['wilson_lower_95']:.4f})")
        print("Decision: Proceed to April known holdout validation.")

    # Daily top-K analysis
    print(f"\n{'='*70}")
    print("DAILY SELECTOR ANALYSIS (Q1 2026)")
    print(f"{'='*70}")
    test_df_copy = test_df.copy()
    test_df_copy["prob"] = probs
    test_df_copy["actual_int"] = y_test.astype(int)

    for topk in [3, 5, 6, 8, 10]:
        daily_top = test_df_copy.groupby("date").apply(
            lambda g: g.nlargest(topk, "prob") if len(g) >= topk else g.nlargest(min(len(g), topk), "prob"),
            include_groups=False
        )
        if len(daily_top) > 0:
            dtk_count = len(daily_top)
            dtk_correct = int(daily_top["actual_int"].sum())
            dtk_wilson = wilson_lower_95(dtk_correct, dtk_count)
            dtk_acc = dtk_correct / dtk_count
            trading_days = test_df_copy["date"].nunique()
            covered_days = daily_top.index.get_level_values(0).nunique() if isinstance(daily_top.index, pd.MultiIndex) else test_df_copy["date"].nunique()
            print(f"  daily_top{topk}: count={dtk_count}, acc={dtk_acc:.4f}, wilson={dtk_wilson:.4f}, days={trading_days}")

    # Save result
    result = {
        "timestamp": datetime.now().isoformat(),
        "champion_trial": CHAMPION["trial_number"],
        "champion_params": CHAMPION,
        "q1_metrics": {
            "wilson_075": wilson_075,
            "accuracy_075": acc_075,
            "count_075": count_075,
            "coverage_075": coverage_075,
            "brier": brier,
            "overall_hc_wilson": overall_hc_wilson,
        },
        "u95_reference": U95_REF,
        "delta_wilson_pp": delta_wilson,
        "selected_feature_count": len(selected_idx),
        "train_rows": len(train_df),
        "test_rows": len(test_df),
    }

    out_path = REPORT_DIR / "q1_validation_champion_trial33.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResult saved: {out_path}")


if __name__ == "__main__":
    main()

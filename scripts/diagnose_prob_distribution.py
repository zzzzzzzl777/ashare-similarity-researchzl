"""Diagnose probability distribution from single models on one fold.
Answers: can a single LGB/XGB/CatBoost produce prob>=0.75?
"""
from __future__ import annotations
import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path

_SRC_DIR = Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_u95_optuna_rolling import (
    load_feature_cache, apply_limit_up_filter, get_feature_columns,
    prepare_fold_data, select_features_stable_tail, apply_calibration,
    ROLLING_FOLDS, SEED, META_COLUMNS,
)


def run_diagnostic():
    print("Loading data...")
    df = load_feature_cache()
    df = apply_limit_up_filter(df)
    feature_cols = get_feature_columns(df)
    print(f"Features: {len(feature_cols)}, Rows: {len(df):,}")
    print(f"META_COLUMNS excluded: {sorted(META_COLUMNS)}")
    # Verify no label leakage
    for c in feature_cols:
        if 'next_' in c and ('return' in c or 'close' in c):
            print(f"  WARNING: potential label leakage: {c}")
    for c in ['next_high_return_pct', 'next_close_return_pct', 'next_close_up', 'next_low_return_pct', 'hard_to_hold_2pct', 'hard_to_hold_3pct']:
        if c in feature_cols:
            print(f"  CRITICAL LEAKAGE: {c} is in feature_cols!")
            sys.exit(1)
    print("  No label leakage detected.")

    # Use fold 3 (middle fold, decent train size)
    fold = ROLLING_FOLDS[2]
    print(f"\nFold: train_end={fold['train_end']}, val={fold['val_start']}~{fold['val_end']}")

    train_df, valid_df = prepare_fold_data(df, fold, embargo_days=1)
    print(f"Train: {len(train_df):,}, Valid: {len(valid_df):,}")
    print(f"Train positive rate: {train_df['actual'].mean():.4f}")
    print(f"Valid positive rate: {valid_df['actual'].mean():.4f}")

    x_train_raw = train_df[feature_cols].to_numpy(dtype=np.float32)
    y_train = train_df["actual"].to_numpy(dtype=np.float32)
    x_valid_raw = valid_df[feature_cols].to_numpy(dtype=np.float32)
    y_valid = valid_df["actual"].to_numpy(dtype=np.float32)

    # Standardize
    train_mean = np.nanmean(x_train_raw, axis=0, keepdims=True)
    train_std = np.nanstd(x_train_raw, axis=0, keepdims=True)
    train_std = np.where(train_std < 1e-6, 1.0, train_std)
    x_train_std = np.nan_to_num((x_train_raw - train_mean) / train_std, nan=0.0, posinf=0.0, neginf=0.0)
    x_valid_std = np.nan_to_num((x_valid_raw - train_mean) / train_std, nan=0.0, posinf=0.0, neginf=0.0)

    # Feature selection (260 features, same as U95)
    print("\nRunning feature selection (260 features)...")
    t0 = time.time()
    selected_idx = select_features_stable_tail(x_train_std, y_train, feature_cols, max_features=260)
    print(f"  Selected {len(selected_idx)} features in {time.time()-t0:.1f}s")

    x_train_sel = x_train_std[:, selected_idx]
    x_valid_sel = x_valid_std[:, selected_idx]

    # ES split (80/20 by date)
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
    print(f"ES split: train={len(x_es_train):,}, valid={len(x_es_valid):,}")

    def print_prob_stats(probs, label, y=None):
        print(f"\n  [{label}]")
        print(f"    min={probs.min():.4f}  p5={np.percentile(probs,5):.4f}  p25={np.percentile(probs,25):.4f}  "
              f"p50={np.percentile(probs,50):.4f}  p75={np.percentile(probs,75):.4f}  "
              f"p90={np.percentile(probs,90):.4f}  p95={np.percentile(probs,95):.4f}  "
              f"p99={np.percentile(probs,99):.4f}  max={probs.max():.4f}")
        for thresh in [0.60, 0.65, 0.70, 0.75, 0.80, 0.85]:
            count = (probs >= thresh).sum()
            if count > 0 and y is not None:
                acc = y[probs >= thresh].mean()
                print(f"    >= {thresh:.2f}: count={count:>5}, acc={acc:.4f}")
            else:
                print(f"    >= {thresh:.2f}: count={count:>5}")

    # ---- LightGBM ----
    print("\n" + "="*60)
    print("LightGBM (depth=6, lr=0.03, n_est=1000)")
    print("="*60)
    import lightgbm as lgb
    lgb_model = lgb.LGBMClassifier(
        objective="binary", metric="binary_logloss", verbosity=-1, device="gpu",
        seed=SEED, num_leaves=63, max_depth=6, learning_rate=0.03,
        n_estimators=1000, min_child_samples=100, feature_fraction=0.7,
        bagging_fraction=0.8, bagging_freq=5, lambda_l1=1.0, lambda_l2=10.0,
        min_gain_to_split=0.5,
    )
    lgb_model.fit(x_es_train, y_es_train, eval_set=[(x_es_valid, y_es_valid)],
                  callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)])
    probs_lgb = lgb_model.predict_proba(x_valid_sel)[:, 1]
    print_prob_stats(probs_lgb, "LGB raw", y_valid)

    # Calibrate with isotonic
    probs_es = lgb_model.predict_proba(x_es_valid)[:, 1]
    probs_lgb_iso = apply_calibration(probs_es, y_es_valid, probs_lgb, "isotonic")
    print_prob_stats(probs_lgb_iso, "LGB isotonic", y_valid)

    probs_lgb_sig = apply_calibration(probs_es, y_es_valid, probs_lgb, "sigmoid")
    print_prob_stats(probs_lgb_sig, "LGB sigmoid", y_valid)

    # ---- XGBoost ----
    print("\n" + "="*60)
    print("XGBoost (depth=4, lr=0.03, n_est=1000)")
    print("="*60)
    import xgboost as xgb
    xgb_model = xgb.XGBClassifier(
        objective="binary:logistic", eval_metric="logloss", verbosity=0,
        tree_method="hist", device="cuda", seed=SEED,
        max_depth=4, learning_rate=0.03, n_estimators=1000,
        min_child_weight=20, subsample=0.8, colsample_bytree=0.7,
        reg_lambda=10.0, reg_alpha=1.0, gamma=1.0, early_stopping_rounds=50,
    )
    xgb_model.fit(x_es_train, y_es_train, eval_set=[(x_es_valid, y_es_valid)], verbose=False)
    probs_xgb = xgb_model.predict_proba(x_valid_sel)[:, 1]
    print_prob_stats(probs_xgb, "XGB raw", y_valid)

    probs_es_xgb = xgb_model.predict_proba(x_es_valid)[:, 1]
    probs_xgb_iso = apply_calibration(probs_es_xgb, y_es_valid, probs_xgb, "isotonic")
    print_prob_stats(probs_xgb_iso, "XGB isotonic", y_valid)

    # ---- CatBoost ----
    print("\n" + "="*60)
    print("CatBoost (depth=6, lr=0.03, iter=1000)")
    print("="*60)
    from catboost import CatBoostClassifier
    cb_model = CatBoostClassifier(
        loss_function="Logloss", eval_metric="Logloss", verbose=0,
        task_type="GPU", random_seed=SEED,
        depth=6, learning_rate=0.03, iterations=1000,
        l2_leaf_reg=10.0, random_strength=1.0, bagging_temperature=1.0,
        border_count=128,
    )
    cb_model.fit(x_es_train, y_es_train, eval_set=(x_es_valid, y_es_valid),
                 early_stopping_rounds=50, verbose=False)
    probs_cb = cb_model.predict_proba(x_valid_sel)[:, 1]
    print_prob_stats(probs_cb, "CatBoost raw", y_valid)

    probs_es_cb = cb_model.predict_proba(x_es_valid)[:, 1]
    probs_cb_iso = apply_calibration(probs_es_cb, y_es_valid, probs_cb, "isotonic")
    print_prob_stats(probs_cb_iso, "CatBoost isotonic", y_valid)

    print("\n" + "="*60)
    print("DIAGNOSIS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    run_diagnostic()

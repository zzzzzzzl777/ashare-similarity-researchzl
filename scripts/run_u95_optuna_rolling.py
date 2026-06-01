"""
Optuna hyperparameter optimization for A-share T+1 prediction (U95 rolling CV).

Usage:
    python scripts/run_u95_optuna_rolling.py smoke              # 3-5 quick trials
    python scripts/run_u95_optuna_rolling.py phase1 --trials 60 # full phase 1
    python scripts/run_u95_optuna_rolling.py phase2 --trials 100 --study-name <name>

CatBoost trials run in a subprocess to avoid GPU memory leaks.
"""
from __future__ import annotations

import argparse
import gc
import json
import logging
import math
import os
import subprocess
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SRC_DIR = Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FEATURE_CACHE_PATH = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_29fad3014f118dc1_t1shifted.parquet"
)
OPTUNA_DB_PATH = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\optuna_u95_rolling.db"
)
LEDGER_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")

SEED = 42
LABEL_TARGET = "next_high_from_close"
TARGET_HIGH_RETURN_PCT = 1.0

# P0 exclusion list (58 features)
_P0_HARD_MONEYFLOW = [
    "tushare_net_mf_amount", "tushare_net_mf_amount_available",
    "tushare_lg_buy_sell_ratio", "tushare_lg_buy_sell_ratio_available",
    "tushare_elg_buy_sell_ratio", "tushare_elg_buy_sell_ratio_available",
    "tushare_mf_strength", "tushare_mf_strength_available",
    "tushare_sm_sell_pressure", "tushare_sm_sell_pressure_available",
    "tushare_main_force_divergence", "tushare_main_force_divergence_available",
    "tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available",
]
_P0_POST_CLOSE = [
    "tushare_lhb_net_buy", "tushare_lhb_net_buy_available",
    "tushare_lhb_net_rate", "tushare_lhb_net_rate_available",
    "tushare_inst_buy_count", "tushare_inst_buy_count_available",
    "tushare_lhb_appeared", "tushare_lhb_appeared_available",
    "tushare_inst_net_buy", "tushare_inst_net_buy_available",
    "tushare_rzye_delta_pct", "tushare_rzye_delta_pct_available",
    "tushare_rzye", "tushare_rzye_available",
    "tushare_rzmre_ratio", "tushare_rzmre_ratio_available",
    "tushare_margin_net", "tushare_margin_net_available",
    "tushare_rqye_ratio", "tushare_rqye_ratio_available",
    "tushare_auction_close_vwap_ratio", "tushare_auction_close_vwap_ratio_available",
    "tushare_auction_close_vol", "tushare_auction_close_vol_available",
    "tushare_float_relative_impact", "tushare_float_relative_impact_available",
]
_P0_THS_SECTOR = [
    "sector_pct_change_best", "sector_pct_change_best_available", "sector_pct_change_best_available_available",
    "sector_strength_rank", "sector_strength_rank_available", "sector_strength_rank_available_available",
    "sector_limit_up_count", "sector_limit_up_count_available", "sector_limit_up_count_available_available",
    "sector_divergence", "sector_divergence_available", "sector_divergence_available_available",
    "sector_duration_days", "sector_duration_days_available", "sector_duration_days_available_available",
    "sector_climax_signal", "sector_climax_signal_available", "sector_climax_signal_available_available",
]
P0_EXCLUDED_FEATURES: set[str] = set(_P0_HARD_MONEYFLOW + _P0_POST_CLOSE + _P0_THS_SECTOR)

# Meta columns (not features) — includes all label/outcome columns stored in cache
META_COLUMNS = {
    "date", "symbol", "label_date", "actual", "next_return_pct", "limit_up_like",
    "next_high_return_pct", "next_close_return_pct", "next_close_up", "next_low_return_pct",
    "hard_to_hold_2pct", "hard_to_hold_3pct", "close", "pct_change", "turnover",
    "amount", "name", "stock_name",
}

# Rolling CV folds (expanding window, bimonthly validation)
ROLLING_FOLDS = [
    {"train_end": "2024-12-31", "val_start": "2025-01-01", "val_end": "2025-02-28"},
    {"train_end": "2025-02-28", "val_start": "2025-03-01", "val_end": "2025-04-30"},
    {"train_end": "2025-04-30", "val_start": "2025-05-01", "val_end": "2025-06-30"},
    {"train_end": "2025-06-30", "val_start": "2025-07-01", "val_end": "2025-08-31"},
    {"train_end": "2025-08-31", "val_start": "2025-09-01", "val_end": "2025-10-31"},
    {"train_end": "2025-10-31", "val_start": "2025-11-01", "val_end": "2025-12-31"},
]

# U95 baseline reference
U95_BRIER_BASELINE = 0.2195

# High confidence thresholds for multi-threshold Wilson
HC_THRESHOLDS = [0.75, 0.78, 0.80, 0.82, 0.85]

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("optuna_u95_rolling")


# ===========================================================================
# Wilson lower 95% confidence bound
# ===========================================================================
def wilson_lower_95(correct: int, total: int) -> float:
    """Compute Wilson score interval lower bound at 95% confidence."""
    if total == 0:
        return 0.0
    z = 1.96
    p_hat = correct / total
    denom = 1 + z ** 2 / total
    center = (p_hat + z ** 2 / (2 * total)) / denom
    margin = z * math.sqrt(p_hat * (1 - p_hat) / total + z ** 2 / (4 * total ** 2)) / denom
    return center - margin


# ===========================================================================
# Feature exclusion helpers
# ===========================================================================
def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Get all feature columns (exclude meta + P0 exclusions + cross_ prefix)."""
    all_cols = [c for c in df.columns if c not in META_COLUMNS]
    filtered = []
    for c in all_cols:
        if c in P0_EXCLUDED_FEATURES:
            continue
        if c.startswith("cross_"):
            continue
        filtered.append(c)
    return filtered


def audit_p0_exclusions(selected_features: list[str]) -> list[str]:
    """Verify no P0-excluded feature leaked into selection. Returns violations."""
    violations = []
    for f in selected_features:
        if f in P0_EXCLUDED_FEATURES or f.startswith("cross_"):
            violations.append(f)
    return violations


# ===========================================================================
# Data loading and preparation
# ===========================================================================
def load_feature_cache() -> pd.DataFrame:
    """Load the pre-built T-1 shifted feature cache."""
    logger.info(f"Loading feature cache from {FEATURE_CACHE_PATH}")
    if not FEATURE_CACHE_PATH.exists():
        raise FileNotFoundError(f"Feature cache not found: {FEATURE_CACHE_PATH}")
    df = pd.read_parquet(FEATURE_CACHE_PATH)
    logger.info(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    # Parse date columns
    for col in ["date", "label_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def apply_limit_up_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Remove limit-up event day samples (non-executable)."""
    if "limit_up_like" not in df.columns:
        logger.warning("limit_up_like column missing - cannot filter limit-up events")
        return df
    mask = pd.to_numeric(df["limit_up_like"], errors="coerce").fillna(0.0) > 0.5
    filtered = df[~mask].copy()
    logger.info(f"  Limit-up filter: {mask.sum():,} rows dropped, {len(filtered):,} remain")
    return filtered


def prepare_fold_data(
    df: pd.DataFrame,
    fold: dict[str, str],
    embargo_days: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split data into train and validation for a given fold."""
    train_end = pd.Timestamp(fold["train_end"])
    val_start = pd.Timestamp(fold["val_start"])
    val_end = pd.Timestamp(fold["val_end"])

    # Train: label_date <= train_end
    train = df[df["label_date"] <= train_end].copy()
    # Validation: date >= val_start AND date <= val_end
    valid = df[(df["date"] >= val_start) & (df["date"] <= val_end)].copy()

    # Apply embargo: remove train rows where label_date is within embargo_days of val_start
    if embargo_days > 0:
        embargo_cutoff = val_start - pd.Timedelta(days=embargo_days)
        train = train[train["label_date"] <= embargo_cutoff].copy()

    return train, valid


# ===========================================================================
# Feature selection (reuses gpu_probe logic with torch)
# ===========================================================================
def select_features_stable_tail(
    x_train_np: np.ndarray,
    y_train_np: np.ndarray,
    feature_names: list[str],
    max_features: int,
) -> list[int]:
    """
    Perform stable_tail feature selection on standardized training data.
    Returns indices of selected features.
    """
    import torch

    from ashare_similarity.prediction.gpu_probe import _select_training_feature_indices

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    x_train_t = torch.as_tensor(x_train_np, dtype=torch.float32, device=device)
    y_train_t = torch.as_tensor(y_train_np, dtype=torch.float32, device=device)

    result = _select_training_feature_indices(
        x_train_t,
        y_train_t,
        tuple(feature_names),
        max_features=max_features,
        method="stable_tail",
    )

    indices = result.get("_indices")
    if indices is not None:
        selected_idx = indices.detach().cpu().tolist()
    else:
        # No reduction needed
        selected_idx = list(range(len(feature_names)))

    # Clean up GPU
    del x_train_t, y_train_t
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return selected_idx


# ===========================================================================
# Model training
# ===========================================================================
def train_lightgbm(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
    params: dict[str, Any],
) -> Any:
    """Train LightGBM with early stopping."""
    import lightgbm as lgb

    lgb_params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "verbosity": -1,
        "device": "gpu",
        "seed": SEED,
        "num_leaves": params["num_leaves"],
        "max_depth": params["max_depth"],
        "learning_rate": params["learning_rate"],
        "n_estimators": params["n_estimators"],
        "min_child_samples": params["min_child_samples"],
        "feature_fraction": params["feature_fraction"],
        "bagging_fraction": params["bagging_fraction"],
        "bagging_freq": params["bagging_freq"],
        "lambda_l1": params["lambda_l1"],
        "lambda_l2": params["lambda_l2"],
        "min_gain_to_split": params["min_gain_to_split"],
    }

    model = lgb.LGBMClassifier(**lgb_params)
    model.fit(
        x_train, y_train,
        eval_set=[(x_valid, y_valid)],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50, verbose=False),
            lgb.log_evaluation(period=0),
        ],
    )
    return model


def train_xgboost(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
    params: dict[str, Any],
) -> Any:
    """Train XGBoost with early stopping."""
    import xgboost as xgb

    xgb_params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "verbosity": 0,
        "tree_method": "hist",
        "device": "cuda",
        "seed": SEED,
        "max_depth": params["max_depth"],
        "learning_rate": params["learning_rate"],
        "n_estimators": params["n_estimators"],
        "min_child_weight": params["min_child_weight"],
        "subsample": params["subsample"],
        "colsample_bytree": params["colsample_bytree"],
        "reg_lambda": params["reg_lambda"],
        "reg_alpha": params["reg_alpha"],
        "gamma": params["gamma"],
        "early_stopping_rounds": 50,
    }

    model = xgb.XGBClassifier(**xgb_params)
    model.fit(
        x_train, y_train,
        eval_set=[(x_valid, y_valid)],
        verbose=False,
    )
    return model


def train_catboost(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
    params: dict[str, Any],
) -> Any:
    """Train CatBoost with early stopping (GPU)."""
    from catboost import CatBoostClassifier

    cb_params = {
        "loss_function": "Logloss",
        "eval_metric": "Logloss",
        "verbose": 0,
        "task_type": "GPU",
        "random_seed": SEED,
        "depth": params["depth"],
        "learning_rate": params["learning_rate"],
        "iterations": params["iterations"],
        "l2_leaf_reg": params["l2_leaf_reg"],
        "random_strength": params["random_strength"],
        "bagging_temperature": params["bagging_temperature"],
        "border_count": params["border_count"],
    }

    model = CatBoostClassifier(**cb_params)
    model.fit(
        x_train, y_train,
        eval_set=(x_valid, y_valid),
        early_stopping_rounds=50,
        verbose=False,
    )
    return model


# ===========================================================================
# Calibration
# ===========================================================================
def apply_calibration(
    probs_calib_train: np.ndarray,
    y_calib_train: np.ndarray,
    probs_test: np.ndarray,
    method: str,
) -> np.ndarray:
    """Apply calibration to probabilities."""
    if method == "none":
        return probs_test

    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.base import BaseEstimator, ClassifierMixin

    class _PrecomputedClassifier(BaseEstimator, ClassifierMixin):
        """Dummy classifier that returns precomputed probabilities."""
        def __init__(self):
            self.classes_ = np.array([0, 1])

        def fit(self, X, y):
            return self

        def predict_proba(self, X):
            return np.column_stack([1 - X[:, 0], X[:, 0]])

    # Use isotonic or sigmoid calibration via sklearn
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    if method == "isotonic":
        ir = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        ir.fit(probs_calib_train, y_calib_train)
        calibrated = ir.predict(probs_test)
    elif method == "sigmoid":
        # Platt scaling
        lr = LogisticRegression(C=1e10, solver="lbfgs", max_iter=1000)
        lr.fit(probs_calib_train.reshape(-1, 1), y_calib_train)
        calibrated = lr.predict_proba(probs_test.reshape(-1, 1))[:, 1]
    else:
        raise ValueError(f"Unknown calibration method: {method}")

    return np.clip(calibrated, 0.0, 1.0)


# ===========================================================================
# Scoring metrics
# ===========================================================================
def compute_fold_metrics(
    y_true: np.ndarray,
    probs: np.ndarray,
) -> dict[str, Any]:
    """Compute all metrics for a single fold."""
    metrics: dict[str, Any] = {}

    # Wilson at prob >= 0.75 threshold
    mask_075 = probs >= 0.75
    count_075 = int(mask_075.sum())
    if count_075 > 0:
        correct_075 = int(y_true[mask_075].sum())
        wilson_075 = wilson_lower_95(correct_075, count_075)
        hc_075 = correct_075 / count_075
    else:
        wilson_075 = 0.0
        hc_075 = 0.0

    metrics["prob_075_wilson"] = wilson_075
    metrics["prob_075_hc"] = hc_075
    metrics["prob_075_count"] = count_075
    metrics["prob_075_correct"] = int(y_true[mask_075].sum()) if count_075 > 0 else 0

    # High-confidence Wilson at multiple thresholds
    hc_wilsons = []
    for thresh in HC_THRESHOLDS:
        mask = probs >= thresh
        count = int(mask.sum())
        if count > 0:
            correct = int(y_true[mask].sum())
            w = wilson_lower_95(correct, count)
        else:
            w = 0.0
        metrics[f"wilson_at_{thresh:.2f}"] = w
        metrics[f"count_at_{thresh:.2f}"] = count
        hc_wilsons.append(w)

    metrics["high_conf_wilson_mean"] = float(np.mean(hc_wilsons)) if hc_wilsons else 0.0

    # Overall HC Wilson (model's own band - top 10% by probability)
    n_top = max(1, int(len(probs) * 0.10))
    top_idx = np.argsort(probs)[-n_top:]
    top_correct = int(y_true[top_idx].sum())
    metrics["overall_hc_wilson"] = wilson_lower_95(top_correct, n_top)

    # Brier score
    metrics["brier"] = float(np.mean((probs - y_true) ** 2))

    # Unique probabilities in top candidates (for tie penalty)
    if count_075 > 0:
        top_probs = probs[mask_075]
        metrics["unique_probs_top"] = int(len(np.unique(np.round(top_probs, 6))))
    else:
        metrics["unique_probs_top"] = 0

    return metrics


def compute_objective_score(fold_metrics_list: list[dict[str, Any]]) -> float:
    """
    Compute the composite objective score from all fold metrics.

    score = (
        0.45 * mean(prob>=0.75_wilson across folds)
      + 0.20 * min(prob>=0.75_wilson across folds)
      + 0.15 * mean(high_conf_wilson across folds)
      + 0.10 * mean(overall_hc_wilson across folds)
      - 0.20 * std(prob>=0.75_wilson across folds)
      - brier_penalty
      - sparse_penalty
      - tie_penalty
    )
    """
    wilson_075_values = [m["prob_075_wilson"] for m in fold_metrics_list]
    hc_wilson_means = [m["high_conf_wilson_mean"] for m in fold_metrics_list]
    overall_hc_wilsons = [m["overall_hc_wilson"] for m in fold_metrics_list]
    brier_values = [m["brier"] for m in fold_metrics_list]
    counts_075 = [m["prob_075_count"] for m in fold_metrics_list]
    unique_probs = [m["unique_probs_top"] for m in fold_metrics_list]

    # Main components
    mean_wilson_075 = float(np.mean(wilson_075_values))
    min_wilson_075 = float(np.min(wilson_075_values))
    mean_hc_wilson = float(np.mean(hc_wilson_means))
    mean_overall_hc = float(np.mean(overall_hc_wilsons))
    std_wilson_075 = float(np.std(wilson_075_values))

    score = (
        0.45 * mean_wilson_075
        + 0.20 * min_wilson_075
        + 0.15 * mean_hc_wilson
        + 0.10 * mean_overall_hc
        - 0.20 * std_wilson_075
    )

    # Brier penalty: max(0, avg_brier - 0.2195) * 5.0
    avg_brier = float(np.mean(brier_values))
    brier_penalty = max(0.0, avg_brier - U95_BRIER_BASELINE) * 5.0
    score -= brier_penalty

    # Sparse penalty: if avg count at prob>=0.75 < 50 per fold
    avg_count = float(np.mean(counts_075))
    if avg_count < 50:
        sparse_penalty = (50 - avg_count) * 0.002
        score -= sparse_penalty
    else:
        sparse_penalty = 0.0

    # Tie penalty: if unique probabilities < 100 in top candidates
    avg_unique = float(np.mean(unique_probs))
    if avg_unique < 100:
        tie_penalty = (100 - avg_unique) * 0.001
        score -= tie_penalty
    else:
        tie_penalty = 0.0

    return score


# ===========================================================================
# Single fold evaluation
# ===========================================================================
def evaluate_fold(
    df: pd.DataFrame,
    fold: dict[str, str],
    feature_cols: list[str],
    params: dict[str, Any],
    fold_index: int,
) -> dict[str, Any]:
    """Train and evaluate one fold. Returns metrics dict."""
    import torch

    model_family = params["model_family"]
    calibration = params["calibration"]
    max_selected_features = params["max_selected_features"]

    # Split data
    train_df, valid_df = prepare_fold_data(df, fold, embargo_days=1)
    if len(train_df) < 100 or len(valid_df) < 10:
        logger.warning(f"  Fold {fold_index}: insufficient data (train={len(train_df)}, valid={len(valid_df)})")
        return {"prob_075_wilson": 0.0, "prob_075_count": 0, "high_conf_wilson_mean": 0.0,
                "overall_hc_wilson": 0.0, "brier": 0.30, "unique_probs_top": 0, "prob_075_hc": 0.0,
                "prob_075_correct": 0, "fold_index": fold_index, "status": "insufficient_data"}

    # Extract features and labels
    x_train_raw = train_df[feature_cols].to_numpy(dtype=np.float32)
    y_train_all = train_df["actual"].to_numpy(dtype=np.float32)
    x_valid_raw = valid_df[feature_cols].to_numpy(dtype=np.float32)
    y_valid_all = valid_df["actual"].to_numpy(dtype=np.float32)

    # Standardize (train stats only)
    train_mean = np.nanmean(x_train_raw, axis=0, keepdims=True)
    train_std = np.nanstd(x_train_raw, axis=0, keepdims=True)
    train_std = np.where(train_std < 1e-6, 1.0, train_std)

    x_train_std = (x_train_raw - train_mean) / train_std
    x_valid_std = (x_valid_raw - train_mean) / train_std

    # Replace NaN/inf
    x_train_std = np.nan_to_num(x_train_std, nan=0.0, posinf=0.0, neginf=0.0)
    x_valid_std = np.nan_to_num(x_valid_std, nan=0.0, posinf=0.0, neginf=0.0)

    # Feature selection on train only (stable_tail)
    selected_idx = select_features_stable_tail(
        x_train_std, y_train_all, feature_cols, max_features=max_selected_features
    )
    selected_features = [feature_cols[i] for i in selected_idx]

    # P0 audit
    violations = audit_p0_exclusions(selected_features)
    if violations:
        raise RuntimeError(f"P0 AUDIT FAILURE: excluded features in selection: {violations}")

    x_train_sel = x_train_std[:, selected_idx]
    x_valid_sel = x_valid_std[:, selected_idx]

    # Early-stopping split from train (20% purged by date)
    n_train = len(train_df)
    train_dates = train_df["label_date"].values
    sorted_dates = np.sort(np.unique(train_dates))
    split_point = int(len(sorted_dates) * 0.80)
    if split_point < 1:
        split_point = 1
    es_cutoff = sorted_dates[min(split_point, len(sorted_dates) - 1)]

    es_train_mask = train_dates <= es_cutoff
    es_valid_mask = train_dates > es_cutoff

    # Apply 1-day embargo between es_train and es_valid
    if es_valid_mask.sum() > 0:
        es_valid_start = train_dates[es_valid_mask].min()
        embargo_cutoff = es_valid_start - np.timedelta64(1, "D")
        es_train_mask = es_train_mask & (train_dates <= embargo_cutoff)

    x_es_train = x_train_sel[es_train_mask]
    y_es_train = y_train_all[es_train_mask]
    x_es_valid = x_train_sel[es_valid_mask]
    y_es_valid = y_train_all[es_valid_mask]

    if len(x_es_train) < 50 or len(x_es_valid) < 10:
        logger.warning(f"  Fold {fold_index}: insufficient ES split")
        return {"prob_075_wilson": 0.0, "prob_075_count": 0, "high_conf_wilson_mean": 0.0,
                "overall_hc_wilson": 0.0, "brier": 0.30, "unique_probs_top": 0, "prob_075_hc": 0.0,
                "prob_075_correct": 0, "fold_index": fold_index, "status": "insufficient_es_split"}

    # Train model
    if model_family == "lightgbm":
        model = train_lightgbm(x_es_train, y_es_train, x_es_valid, y_es_valid, params)
    elif model_family == "xgboost":
        model = train_xgboost(x_es_train, y_es_train, x_es_valid, y_es_valid, params)
    elif model_family == "catboost":
        model = train_catboost(x_es_train, y_es_train, x_es_valid, y_es_valid, params)
    else:
        raise ValueError(f"Unknown model family: {model_family}")

    # Predict on validation fold
    probs_valid = model.predict_proba(x_valid_sel)[:, 1]

    # Apply calibration
    if calibration != "none":
        # Calibration trained on ES validation set
        probs_calib_train = model.predict_proba(x_es_valid)[:, 1]
        probs_valid = apply_calibration(probs_calib_train, y_es_valid, probs_valid, calibration)

    # Compute metrics
    metrics = compute_fold_metrics(y_valid_all, probs_valid)
    metrics["fold_index"] = fold_index
    metrics["train_rows"] = int(len(train_df))
    metrics["valid_rows"] = int(len(valid_df))
    metrics["selected_feature_count"] = len(selected_idx)
    metrics["status"] = "ok"

    # Cleanup
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return metrics


# ===========================================================================
# CatBoost subprocess worker
# ===========================================================================
def _catboost_worker_main(params_json: str) -> None:
    """
    Subprocess entry point for CatBoost trials.
    Receives params as JSON, runs all folds, prints result JSON to stdout.
    """
    params = json.loads(params_json)

    # Load data
    df = load_feature_cache()
    df = apply_limit_up_filter(df)
    feature_cols = get_feature_columns(df)

    fold_metrics = []
    for fold_index, fold in enumerate(ROLLING_FOLDS):
        try:
            metrics = evaluate_fold(df, fold, feature_cols, params, fold_index)
            fold_metrics.append(metrics)
        except Exception as e:
            fold_metrics.append({
                "prob_075_wilson": 0.0, "prob_075_count": 0,
                "high_conf_wilson_mean": 0.0, "overall_hc_wilson": 0.0,
                "brier": 0.30, "unique_probs_top": 0, "prob_075_hc": 0.0,
                "prob_075_correct": 0, "fold_index": fold_index,
                "status": f"error: {str(e)}",
            })

    score = compute_objective_score(fold_metrics)
    result = {"score": score, "fold_metrics": fold_metrics, "status": "ok"}
    # Print result as JSON to stdout (last line)
    print(f"__RESULT__{json.dumps(result)}__END_RESULT__")


def run_catboost_in_subprocess(params: dict[str, Any]) -> dict[str, Any]:
    """Run CatBoost trial in a subprocess to avoid GPU memory leak."""
    params_json = json.dumps(params)
    cmd = [sys.executable, __file__, "_catboost_worker", params_json]

    logger.info("  Launching CatBoost subprocess worker...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,  # 10 minute timeout per trial
    )

    if result.returncode != 0:
        logger.error(f"  CatBoost worker failed:\n{result.stderr[-2000:]}")
        return {"score": -1.0, "fold_metrics": [], "status": f"subprocess_error: {result.stderr[-500:]}"}

    # Parse result from stdout
    stdout = result.stdout
    marker_start = "__RESULT__"
    marker_end = "__END_RESULT__"
    idx_start = stdout.rfind(marker_start)
    idx_end = stdout.rfind(marker_end)

    if idx_start < 0 or idx_end < 0:
        logger.error(f"  CatBoost worker output parsing failed. stdout tail: {stdout[-1000:]}")
        return {"score": -1.0, "fold_metrics": [], "status": "parse_error"}

    json_str = stdout[idx_start + len(marker_start):idx_end]
    return json.loads(json_str)


# ===========================================================================
# Optuna objective
# ===========================================================================
def create_objective(df: pd.DataFrame, feature_cols: list[str]):
    """Create the Optuna objective function (closure over data)."""
    import optuna

    def objective(trial: optuna.Trial) -> float:
        # Shared hyperparameters
        max_selected_features = trial.suggest_categorical(
            "max_selected_features", [120, 160, 200, 220, 260, 300, 320, 360, 400, 480]
        )
        model_family = trial.suggest_categorical(
            "model_family", ["lightgbm", "catboost", "xgboost"]
        )
        calibration = trial.suggest_categorical(
            "calibration", ["none", "sigmoid", "isotonic"]
        )

        # Model-specific hyperparameters
        params: dict[str, Any] = {
            "max_selected_features": max_selected_features,
            "model_family": model_family,
            "calibration": calibration,
        }

        if model_family == "lightgbm":
            params["num_leaves"] = trial.suggest_int("lgb_num_leaves", 7, 127)
            # max_depth: 20% chance of -1 (unlimited)
            if trial.suggest_float("lgb_max_depth_unlimited_prob", 0.0, 1.0) < 0.20:
                params["max_depth"] = -1
            else:
                params["max_depth"] = trial.suggest_int("lgb_max_depth", 2, 8)
            params["learning_rate"] = trial.suggest_float("lgb_learning_rate", 0.005, 0.08, log=True)
            params["n_estimators"] = trial.suggest_int("lgb_n_estimators", 400, 2000)
            params["min_child_samples"] = trial.suggest_int("lgb_min_child_samples", 40, 400)
            params["feature_fraction"] = trial.suggest_float("lgb_feature_fraction", 0.45, 0.95)
            params["bagging_fraction"] = trial.suggest_float("lgb_bagging_fraction", 0.55, 0.95)
            params["bagging_freq"] = trial.suggest_int("lgb_bagging_freq", 1, 10)
            params["lambda_l1"] = trial.suggest_float("lgb_lambda_l1", 0.0, 30.0)
            params["lambda_l2"] = trial.suggest_float("lgb_lambda_l2", 1.0, 80.0, log=True)
            params["min_gain_to_split"] = trial.suggest_float("lgb_min_gain_to_split", 0.0, 2.0)

        elif model_family == "catboost":
            params["depth"] = trial.suggest_int("cb_depth", 3, 8)
            params["learning_rate"] = trial.suggest_float("cb_learning_rate", 0.005, 0.08, log=True)
            params["iterations"] = trial.suggest_int("cb_iterations", 400, 1800)
            params["l2_leaf_reg"] = trial.suggest_float("cb_l2_leaf_reg", 2.0, 80.0, log=True)
            params["random_strength"] = trial.suggest_float("cb_random_strength", 0.0, 10.0)
            params["bagging_temperature"] = trial.suggest_float("cb_bagging_temperature", 0.0, 5.0)
            params["border_count"] = trial.suggest_categorical("cb_border_count", [64, 128, 254])

        elif model_family == "xgboost":
            params["max_depth"] = trial.suggest_int("xgb_max_depth", 2, 6)
            params["learning_rate"] = trial.suggest_float("xgb_learning_rate", 0.005, 0.08, log=True)
            params["n_estimators"] = trial.suggest_int("xgb_n_estimators", 400, 1800)
            params["min_child_weight"] = trial.suggest_int("xgb_min_child_weight", 3, 80)
            params["subsample"] = trial.suggest_float("xgb_subsample", 0.55, 0.95)
            params["colsample_bytree"] = trial.suggest_float("xgb_colsample_bytree", 0.45, 0.95)
            params["reg_lambda"] = trial.suggest_float("xgb_reg_lambda", 1.0, 80.0, log=True)
            params["reg_alpha"] = trial.suggest_float("xgb_reg_alpha", 0.0, 30.0)
            params["gamma"] = trial.suggest_float("xgb_gamma", 0.0, 5.0)

        # --- CatBoost runs in subprocess ---
        if model_family == "catboost":
            result = run_catboost_in_subprocess(params)
            if result["status"] != "ok":
                logger.warning(f"  CatBoost subprocess failed: {result.get('status')}")
                return -1.0
            fold_metrics = result["fold_metrics"]
            score = result["score"]
        else:
            # Run folds in-process for LightGBM and XGBoost
            fold_metrics = []
            for fold_index, fold in enumerate(ROLLING_FOLDS):
                try:
                    metrics = evaluate_fold(df, fold, feature_cols, params, fold_index)
                    fold_metrics.append(metrics)
                except Exception as e:
                    logger.error(f"  Fold {fold_index} error: {e}")
                    fold_metrics.append({
                        "prob_075_wilson": 0.0, "prob_075_count": 0,
                        "high_conf_wilson_mean": 0.0, "overall_hc_wilson": 0.0,
                        "brier": 0.30, "unique_probs_top": 0, "prob_075_hc": 0.0,
                        "prob_075_correct": 0, "fold_index": fold_index,
                        "status": f"error: {str(e)}",
                    })

                # Pruning: check after at least 2 folds
                if fold_index >= 1:
                    partial_score = compute_objective_score(fold_metrics)
                    trial.report(partial_score, fold_index)
                    if trial.should_prune():
                        logger.info(f"  Trial pruned at fold {fold_index}")
                        raise optuna.TrialPruned()

            score = compute_objective_score(fold_metrics)

        # Log trial summary
        wilson_values = [m["prob_075_wilson"] for m in fold_metrics]
        count_values = [m["prob_075_count"] for m in fold_metrics]
        logger.info(
            f"  Trial {trial.number}: score={score:.5f} | "
            f"wilson_075 mean={np.mean(wilson_values):.4f} min={np.min(wilson_values):.4f} "
            f"std={np.std(wilson_values):.4f} | "
            f"avg_count={np.mean(count_values):.0f} | "
            f"model={model_family} | feats={max_selected_features} | cal={calibration}"
        )

        # Write to JSONL ledger
        _write_ledger_entry(trial, params, fold_metrics, score)

        return score

    return objective


# ===========================================================================
# Ledger logging
# ===========================================================================
def _get_ledger_path() -> Path:
    today = datetime.now().strftime("%Y%m%d")
    return LEDGER_DIR / f"experiment_ledger_{today}_u95_optuna_rolling.jsonl"


def _write_ledger_entry(
    trial,
    params: dict[str, Any],
    fold_metrics: list[dict[str, Any]],
    score: float,
) -> None:
    """Append trial result to JSONL ledger."""
    ledger_path = _get_ledger_path()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "trial_number": trial.number,
        "study_name": trial.study.study_name if trial.study else "unknown",
        "score": score,
        "params": params,
        "fold_metrics": fold_metrics,
        "wilson_075_values": [m["prob_075_wilson"] for m in fold_metrics],
        "brier_values": [m["brier"] for m in fold_metrics],
        "counts_075": [m["prob_075_count"] for m in fold_metrics],
    }

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


# ===========================================================================
# Study management
# ===========================================================================
def create_or_load_study(study_name: str, n_trials: int) -> "optuna.Study":
    """Create or load an Optuna study with SQLite storage."""
    import optuna

    OPTUNA_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    storage = f"sqlite:///{OPTUNA_DB_PATH.as_posix()}"

    pruner = optuna.pruners.MedianPruner(
        n_startup_trials=3,
        n_warmup_steps=1,  # At least 2 folds before pruning (step 0 and 1)
        interval_steps=1,
    )

    sampler = optuna.samplers.TPESampler(
        seed=SEED,
        n_startup_trials=10,
        multivariate=True,
    )

    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        direction="maximize",
        pruner=pruner,
        sampler=sampler,
        load_if_exists=True,
    )

    return study


def run_study(study_name: str, n_trials: int) -> None:
    """Main entry: load data, create study, run optimization."""
    import optuna

    logger.info("=" * 70)
    logger.info(f"U95 Optuna Rolling CV Hyperparameter Optimization")
    logger.info(f"  Study: {study_name}")
    logger.info(f"  Trials: {n_trials}")
    logger.info(f"  DB: {OPTUNA_DB_PATH}")
    logger.info(f"  Folds: {len(ROLLING_FOLDS)} bimonthly expanding-window")
    logger.info("=" * 70)

    # Load data once (for in-process trials)
    df = load_feature_cache()
    df = apply_limit_up_filter(df)
    feature_cols = get_feature_columns(df)

    logger.info(f"  Feature columns: {len(feature_cols)} (after P0 exclusions)")
    logger.info(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    logger.info(f"  Rows: {len(df):,}")

    # Create study
    study = create_or_load_study(study_name, n_trials)
    existing_trials = len(study.trials)
    if existing_trials > 0:
        logger.info(f"  Resuming study with {existing_trials} existing trials")

    # Create objective
    objective = create_objective(df, feature_cols)

    # Run optimization
    study.optimize(
        objective,
        n_trials=n_trials,
        show_progress_bar=True,
        gc_after_trial=True,
    )

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("OPTIMIZATION COMPLETE")
    logger.info("=" * 70)

    completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    pruned_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]
    failed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.FAIL]

    logger.info(f"  Completed: {len(completed_trials)}")
    logger.info(f"  Pruned:    {len(pruned_trials)}")
    logger.info(f"  Failed:    {len(failed_trials)}")

    if completed_trials:
        logger.info(f"\n  Best trial: #{study.best_trial.number}")
        logger.info(f"  Best score: {study.best_value:.5f}")
        logger.info(f"  Best params:")
        for key, value in study.best_params.items():
            logger.info(f"    {key}: {value}")

        # Top 5 trials
        sorted_trials = sorted(completed_trials, key=lambda t: t.value or -999, reverse=True)
        logger.info(f"\n  Top 5 trials:")
        for i, t in enumerate(sorted_trials[:5]):
            model = t.params.get("model_family", "?")
            feats = t.params.get("max_selected_features", "?")
            cal = t.params.get("calibration", "?")
            logger.info(f"    #{t.number}: score={t.value:.5f} | {model} | feats={feats} | cal={cal}")

    logger.info(f"\n  Ledger: {_get_ledger_path()}")
    logger.info(f"  DB:     {OPTUNA_DB_PATH}")


# ===========================================================================
# CLI
# ===========================================================================
def main():
    # Handle subprocess worker mode
    if len(sys.argv) >= 3 and sys.argv[1] == "_catboost_worker":
        _catboost_worker_main(sys.argv[2])
        return

    parser = argparse.ArgumentParser(description="U95 Optuna Rolling CV Optimization")
    subparsers = parser.add_subparsers(dest="mode", help="Execution mode")

    # smoke test
    smoke_parser = subparsers.add_parser("smoke", help="Quick smoke test (3-5 trials)")
    smoke_parser.add_argument("--trials", type=int, default=5, help="Number of trials")

    # phase1
    phase1_parser = subparsers.add_parser("phase1", help="Phase 1 optimization")
    phase1_parser.add_argument("--trials", type=int, default=60, help="Number of trials")
    phase1_parser.add_argument("--study-name", type=str, default=None, help="Study name override")

    # phase2
    phase2_parser = subparsers.add_parser("phase2", help="Phase 2 continuation")
    phase2_parser.add_argument("--trials", type=int, default=100, help="Number of trials")
    phase2_parser.add_argument("--study-name", type=str, required=True, help="Existing study name to continue")

    args = parser.parse_args()

    if args.mode is None:
        parser.print_help()
        sys.exit(1)

    if args.mode == "smoke":
        study_name = f"u95_rolling_smoke_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        n_trials = args.trials
    elif args.mode == "phase1":
        study_name = args.study_name or f"u95_rolling_phase1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        n_trials = args.trials
    elif args.mode == "phase2":
        study_name = args.study_name
        n_trials = args.trials
    else:
        parser.print_help()
        sys.exit(1)

    logger.info(f"Mode: {args.mode} | Study: {study_name} | Trials: {n_trials}")
    run_study(study_name, n_trials)


if __name__ == "__main__":
    main()

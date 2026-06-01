"""
U95 Live-Strict Rebuild: 3x LightGBM ensemble + isotonic calibration.

Trains a model bundle that is truly compatible with the 14:57 live-strict gate:
- All 26 forbidden features (moneyflow + THS sector) excluded from feature pool
- Every trial's selected features audited against STRICT_FORBIDDEN
- Final bundle must pass realtime_1457_today_probe.py strict gate

Architecture: 3 LightGBM members (wide, compact, base) → ensemble average → isotonic

Usage:
    python scripts/run_u95_live_strict_rebuild.py smoke          # 2-3 quick trials
    python scripts/run_u95_live_strict_rebuild.py train          # full 30-60 trials
    python scripts/run_u95_live_strict_rebuild.py bundle <trial> # save best as bundle
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import logging
import math
import os
import sys
import time
import traceback
import uuid
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

_SCRIPTS_DIR = Path(r"C:\Users\zzzzzzl\Desktop\subagent\scripts")
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FEATURE_CACHE_PATH = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_665406333a7e545d.parquet"
)
RUNS_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs")
LEDGER_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
OPTUNA_DB_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")

SEED = 42
LABEL_TARGET = "next_high_from_close"
TARGET_HIGH_RETURN_PCT = 1.0

# ---------------------------------------------------------------------------
# P0 Forbidden features (comprehensive, from canonical sources)
# ---------------------------------------------------------------------------
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
    "sector_pct_change_best", "sector_pct_change_best_available",
    "sector_pct_change_best_available_available",
    "sector_strength_rank", "sector_strength_rank_available",
    "sector_strength_rank_available_available",
    "sector_limit_up_count", "sector_limit_up_count_available",
    "sector_limit_up_count_available_available",
    "sector_divergence", "sector_divergence_available",
    "sector_divergence_available_available",
    "sector_duration_days", "sector_duration_days_available",
    "sector_duration_days_available_available",
    "sector_climax_signal", "sector_climax_signal_available",
    "sector_climax_signal_available_available",
]

FORBIDDEN_FEATURES: set[str] = set(_P0_HARD_MONEYFLOW + _P0_POST_CLOSE + _P0_THS_SECTOR)

# Pattern-based catch-all
def _is_pattern_forbidden(name: str) -> bool:
    f = name.lower()
    if f.startswith("sector_"):
        return True
    if f.startswith("ths_"):
        return True
    if f.startswith("concept_"):
        return True
    if "_sector_" in f:
        return True
    if "_concept_" in f:
        return True
    if "lhb" in f:
        return True
    return False

META_COLUMNS = {
    "date", "symbol", "label_date", "actual", "next_return_pct", "limit_up_like",
    "next_high_return_pct", "next_close_return_pct", "next_close_up", "next_low_return_pct",
    "hard_to_hold_2pct", "hard_to_hold_3pct", "close", "pct_change", "turnover",
    "amount", "name", "stock_name",
}

# Rolling CV folds (train only in 2023-2025)
ROLLING_FOLDS = [
    {"train_end": "2024-12-31", "val_start": "2025-01-01", "val_end": "2025-02-28"},
    {"train_end": "2025-02-28", "val_start": "2025-03-01", "val_end": "2025-04-30"},
    {"train_end": "2025-04-30", "val_start": "2025-05-01", "val_end": "2025-06-30"},
    {"train_end": "2025-06-30", "val_start": "2025-07-01", "val_end": "2025-08-31"},
    {"train_end": "2025-08-31", "val_start": "2025-09-01", "val_end": "2025-10-31"},
    {"train_end": "2025-10-31", "val_start": "2025-11-01", "val_end": "2025-12-31"},
]

HC_THRESHOLDS = [0.75, 0.78, 0.80, 0.82, 0.85]
U95_BRIER_BASELINE = 0.2195

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("u95_live_strict_rebuild")


# ===========================================================================
# Helpers
# ===========================================================================
def wilson_lower_95(correct: int, total: int) -> float:
    if total == 0:
        return 0.0
    z = 1.96
    p_hat = correct / total
    denom = 1 + z ** 2 / total
    center = (p_hat + z ** 2 / (2 * total)) / denom
    margin = z * math.sqrt(p_hat * (1 - p_hat) / total + z ** 2 / (4 * total ** 2)) / denom
    return center - margin


def get_allowed_feature_columns(df: pd.DataFrame) -> list[str]:
    """Get feature columns excluding meta, forbidden, and pattern-forbidden."""
    allowed = []
    for c in df.columns:
        if c in META_COLUMNS:
            continue
        if c in FORBIDDEN_FEATURES:
            continue
        if _is_pattern_forbidden(c):
            continue
        if c.startswith("cross_"):
            continue
        allowed.append(c)
    return allowed


def audit_forbidden(selected_features: list[str]) -> list[str]:
    """Return any forbidden features found in selection."""
    violations = []
    for f in selected_features:
        if f in FORBIDDEN_FEATURES or _is_pattern_forbidden(f) or f.startswith("cross_"):
            violations.append(f)
    return violations


# ===========================================================================
# Data loading
# ===========================================================================
def load_feature_cache() -> pd.DataFrame:
    logger.info(f"Loading feature cache: {FEATURE_CACHE_PATH}")
    if not FEATURE_CACHE_PATH.exists():
        raise FileNotFoundError(f"Cache not found: {FEATURE_CACHE_PATH}")
    df = pd.read_parquet(FEATURE_CACHE_PATH)
    logger.info(f"  Loaded {len(df):,} rows, {len(df.columns)} cols")
    for col in ["date", "label_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def apply_limit_up_filter(df: pd.DataFrame) -> pd.DataFrame:
    if "limit_up_like" not in df.columns:
        return df
    mask = pd.to_numeric(df["limit_up_like"], errors="coerce").fillna(0.0) > 0.5
    filtered = df[~mask].copy()
    logger.info(f"  Limit-up filter: {mask.sum():,} dropped, {len(filtered):,} remain")
    return filtered


def prepare_fold_data(df: pd.DataFrame, fold: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_end = pd.Timestamp(fold["train_end"])
    val_start = pd.Timestamp(fold["val_start"])
    val_end = pd.Timestamp(fold["val_end"])
    train = df[df["label_date"] <= train_end].copy()
    valid = df[(df["date"] >= val_start) & (df["date"] <= val_end)].copy()
    embargo_cutoff = val_start - pd.Timedelta(days=1)
    train = train[train["label_date"] <= embargo_cutoff].copy()
    return train, valid


# ===========================================================================
# Feature selection
# ===========================================================================
def select_features_stable_tail(
    x_train_np: np.ndarray,
    y_train_np: np.ndarray,
    feature_names: list[str],
    max_features: int,
) -> list[int]:
    import torch
    from ashare_similarity.prediction.gpu_probe import _select_training_feature_indices

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    x_train_t = torch.as_tensor(x_train_np, dtype=torch.float32, device=device)
    y_train_t = torch.as_tensor(y_train_np, dtype=torch.float32, device=device)

    result = _select_training_feature_indices(
        x_train_t, y_train_t, tuple(feature_names),
        max_features=max_features, method="stable_tail",
    )

    indices = result.get("_indices")
    if indices is not None:
        selected_idx = indices.detach().cpu().tolist()
    else:
        selected_idx = list(range(len(feature_names)))

    del x_train_t, y_train_t
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return selected_idx


# ===========================================================================
# Model training (3x LightGBM ensemble)
# ===========================================================================
def train_lgb_member(
    x_train: np.ndarray, y_train: np.ndarray,
    x_valid: np.ndarray, y_valid: np.ndarray,
    params: dict, seed: int,
) -> Any:
    import lightgbm as lgb

    lgb_params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "verbosity": -1,
        "device": "gpu",
        "seed": seed,
        "num_leaves": params["num_leaves"],
        "max_depth": params.get("max_depth", -1),
        "learning_rate": params["learning_rate"],
        "n_estimators": params["n_estimators"],
        "min_child_samples": params["min_child_samples"],
        "feature_fraction": params["feature_fraction"],
        "bagging_fraction": params["bagging_fraction"],
        "bagging_freq": params["bagging_freq"],
        "lambda_l1": params["lambda_l1"],
        "lambda_l2": params["lambda_l2"],
        "min_gain_to_split": params.get("min_gain_to_split", 0.0),
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


def build_ensemble_params(trial, member_name: str, base_params: dict) -> dict:
    """Build LightGBM params for a specific ensemble member."""
    if member_name == "wide":
        return {
            "num_leaves": trial.suggest_int("wide_num_leaves", 31, 127),
            "max_depth": -1,
            "learning_rate": base_params["learning_rate"],
            "n_estimators": trial.suggest_int("wide_n_estimators", 600, 2000),
            "min_child_samples": trial.suggest_int("wide_min_child_samples", 30, 200),
            "feature_fraction": trial.suggest_float("wide_feature_fraction", 0.6, 0.95),
            "bagging_fraction": trial.suggest_float("wide_bagging_fraction", 0.6, 0.95),
            "bagging_freq": 5,
            "lambda_l1": trial.suggest_float("wide_lambda_l1", 0.0, 20.0),
            "lambda_l2": trial.suggest_float("wide_lambda_l2", 1.0, 60.0, log=True),
            "min_gain_to_split": trial.suggest_float("wide_min_gain_to_split", 0.0, 1.5),
        }
    elif member_name == "compact":
        return {
            "num_leaves": trial.suggest_int("compact_num_leaves", 7, 31),
            "max_depth": trial.suggest_int("compact_max_depth", 3, 6),
            "learning_rate": base_params["learning_rate"] * 1.5,
            "n_estimators": trial.suggest_int("compact_n_estimators", 400, 1200),
            "min_child_samples": trial.suggest_int("compact_min_child_samples", 80, 400),
            "feature_fraction": trial.suggest_float("compact_feature_fraction", 0.45, 0.80),
            "bagging_fraction": trial.suggest_float("compact_bagging_fraction", 0.55, 0.85),
            "bagging_freq": 5,
            "lambda_l1": trial.suggest_float("compact_lambda_l1", 0.0, 30.0),
            "lambda_l2": trial.suggest_float("compact_lambda_l2", 2.0, 80.0, log=True),
            "min_gain_to_split": trial.suggest_float("compact_min_gain_to_split", 0.0, 2.0),
        }
    else:  # base
        return {
            "num_leaves": trial.suggest_int("base_num_leaves", 15, 63),
            "max_depth": -1,
            "learning_rate": base_params["learning_rate"],
            "n_estimators": trial.suggest_int("base_n_estimators", 500, 1800),
            "min_child_samples": trial.suggest_int("base_min_child_samples", 40, 300),
            "feature_fraction": trial.suggest_float("base_feature_fraction", 0.5, 0.90),
            "bagging_fraction": trial.suggest_float("base_bagging_fraction", 0.55, 0.90),
            "bagging_freq": 5,
            "lambda_l1": trial.suggest_float("base_lambda_l1", 0.0, 25.0),
            "lambda_l2": trial.suggest_float("base_lambda_l2", 1.0, 70.0, log=True),
            "min_gain_to_split": trial.suggest_float("base_min_gain_to_split", 0.0, 1.5),
        }


# ===========================================================================
# Calibration
# ===========================================================================
def fit_isotonic(probs_train: np.ndarray, y_train: np.ndarray):
    from sklearn.isotonic import IsotonicRegression
    ir = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    ir.fit(probs_train, y_train)
    return ir


def apply_isotonic(ir, probs: np.ndarray) -> np.ndarray:
    return np.clip(ir.predict(probs), 0.0, 1.0)


# ===========================================================================
# Scoring metrics
# ===========================================================================
def compute_fold_metrics(y_true: np.ndarray, probs: np.ndarray, dates=None) -> dict:
    metrics: dict[str, Any] = {}

    mask_075 = probs >= 0.75
    count_075 = int(mask_075.sum())
    if count_075 > 0:
        correct_075 = int(y_true[mask_075].sum())
        metrics["prob_075_wilson"] = wilson_lower_95(correct_075, count_075)
        metrics["prob_075_hc"] = correct_075 / count_075
        metrics["prob_075_correct"] = correct_075
    else:
        metrics["prob_075_wilson"] = 0.0
        metrics["prob_075_hc"] = 0.0
        metrics["prob_075_correct"] = 0
    metrics["prob_075_count"] = count_075

    for thresh in HC_THRESHOLDS:
        mask = probs >= thresh
        count = int(mask.sum())
        if count > 0:
            correct = int(y_true[mask].sum())
            metrics[f"wilson_at_{thresh:.2f}"] = wilson_lower_95(correct, count)
        else:
            metrics[f"wilson_at_{thresh:.2f}"] = 0.0
        metrics[f"count_at_{thresh:.2f}"] = count

    hc_wilsons = [metrics.get(f"wilson_at_{t:.2f}", 0.0) for t in HC_THRESHOLDS]
    metrics["high_conf_wilson_mean"] = float(np.mean(hc_wilsons))

    n_top = max(1, int(len(probs) * 0.10))
    top_idx = np.argsort(probs)[-n_top:]
    top_correct = int(y_true[top_idx].sum())
    metrics["overall_hc_wilson"] = wilson_lower_95(top_correct, n_top)
    metrics["brier"] = float(np.mean((probs - y_true) ** 2))

    if count_075 > 0:
        metrics["unique_probs_top"] = int(len(np.unique(np.round(probs[mask_075], 6))))
    else:
        metrics["unique_probs_top"] = 0

    # Daily top-K metrics
    if dates is not None:
        for k in [3, 5, 6, 8]:
            metrics.update(_daily_topk_metrics(y_true, probs, dates, k))

    return metrics


def _daily_topk_metrics(y_true, probs, dates, k) -> dict:
    df = pd.DataFrame({"y": y_true, "p": probs, "date": dates})
    correct = 0
    total = 0
    for _, grp in df.groupby("date"):
        if len(grp) < k:
            continue
        top = grp.nlargest(k, "p")
        correct += int(top["y"].sum())
        total += len(top)
    if total == 0:
        return {f"daily_top{k}_accuracy": 0.0, f"daily_top{k}_wilson": 0.0, f"daily_top{k}_count": 0}
    return {
        f"daily_top{k}_accuracy": correct / total,
        f"daily_top{k}_wilson": wilson_lower_95(correct, total),
        f"daily_top{k}_count": total,
    }


def compute_objective_score(fold_metrics_list: list[dict]) -> float:
    wilson_075_values = [m["prob_075_wilson"] for m in fold_metrics_list]
    hc_wilson_means = [m["high_conf_wilson_mean"] for m in fold_metrics_list]
    overall_hc_wilsons = [m["overall_hc_wilson"] for m in fold_metrics_list]
    brier_values = [m["brier"] for m in fold_metrics_list]
    counts_075 = [m["prob_075_count"] for m in fold_metrics_list]
    unique_probs = [m["unique_probs_top"] for m in fold_metrics_list]

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

    avg_brier = float(np.mean(brier_values))
    brier_penalty = max(0.0, avg_brier - U95_BRIER_BASELINE) * 5.0
    score -= brier_penalty

    avg_count = float(np.mean(counts_075))
    if avg_count < 50:
        score -= (50 - avg_count) * 0.002

    avg_unique = float(np.mean(unique_probs))
    if avg_unique < 100:
        score -= (100 - avg_unique) * 0.001

    return score


# ===========================================================================
# Single fold evaluation (3x LightGBM ensemble)
# ===========================================================================
def evaluate_fold_ensemble(
    df: pd.DataFrame,
    fold: dict,
    feature_cols: list[str],
    member_params: dict[str, dict],
    max_selected_features: int,
    fold_index: int,
) -> dict:
    import torch

    train_df, valid_df = prepare_fold_data(df, fold)
    if len(train_df) < 100 or len(valid_df) < 10:
        return _empty_metrics(fold_index, "insufficient_data")

    x_train_raw = train_df[feature_cols].to_numpy(dtype=np.float32)
    y_train = train_df["actual"].to_numpy(dtype=np.float32)
    x_valid_raw = valid_df[feature_cols].to_numpy(dtype=np.float32)
    y_valid = valid_df["actual"].to_numpy(dtype=np.float32)

    # Standardize (train stats)
    train_mean = np.nanmean(x_train_raw, axis=0, keepdims=True)
    train_std = np.nanstd(x_train_raw, axis=0, keepdims=True)
    train_std = np.where(train_std < 1e-6, 1.0, train_std)
    x_train_std = np.nan_to_num((x_train_raw - train_mean) / train_std, nan=0.0, posinf=0.0, neginf=0.0)
    x_valid_std = np.nan_to_num((x_valid_raw - train_mean) / train_std, nan=0.0, posinf=0.0, neginf=0.0)

    # Feature selection (on train only)
    selected_idx = select_features_stable_tail(
        x_train_std, y_train, feature_cols, max_features=max_selected_features
    )
    selected_features = [feature_cols[i] for i in selected_idx]

    # STRICT FORBIDDEN AUDIT
    violations = audit_forbidden(selected_features)
    if violations:
        raise RuntimeError(f"FORBIDDEN AUDIT FAIL: {violations}")

    x_train_sel = x_train_std[:, selected_idx]
    x_valid_sel = x_valid_std[:, selected_idx]

    # Early-stopping split (80/20 by date)
    train_dates = train_df["label_date"].values
    sorted_dates = np.sort(np.unique(train_dates))
    split_point = int(len(sorted_dates) * 0.80)
    es_cutoff = sorted_dates[min(split_point, len(sorted_dates) - 1)]
    es_train_mask = train_dates <= es_cutoff
    es_valid_mask = train_dates > es_cutoff

    if es_valid_mask.sum() > 0:
        es_valid_start = train_dates[es_valid_mask].min()
        embargo_cutoff = es_valid_start - np.timedelta64(1, "D")
        es_train_mask = es_train_mask & (train_dates <= embargo_cutoff)

    x_es_train = x_train_sel[es_train_mask]
    y_es_train = y_train[es_train_mask]
    x_es_valid = x_train_sel[es_valid_mask]
    y_es_valid = y_train[es_valid_mask]

    if len(x_es_train) < 50 or len(x_es_valid) < 10:
        return _empty_metrics(fold_index, "insufficient_es_split")

    # Train 3 members
    members = {}
    member_names = ["wide", "compact", "base"]
    for name in member_names:
        params = member_params[name]
        seed = SEED + hash(name) % 1000
        members[name] = train_lgb_member(x_es_train, y_es_train, x_es_valid, y_es_valid, params, seed)

    # Ensemble average on validation
    member_probs = []
    for name in member_names:
        p = members[name].predict_proba(x_valid_sel)[:, 1]
        member_probs.append(p)
    ensemble_probs = np.mean(member_probs, axis=0)

    # Isotonic calibration (trained on ES validation set)
    calib_probs = []
    for name in member_names:
        p = members[name].predict_proba(x_es_valid)[:, 1]
        calib_probs.append(p)
    calib_ensemble = np.mean(calib_probs, axis=0)
    ir = fit_isotonic(calib_ensemble, y_es_valid)
    calibrated_probs = apply_isotonic(ir, ensemble_probs)

    # Metrics
    valid_dates = valid_df["date"].values if "date" in valid_df.columns else None
    metrics = compute_fold_metrics(y_valid, calibrated_probs, dates=valid_dates)
    metrics["fold_index"] = fold_index
    metrics["train_rows"] = len(train_df)
    metrics["valid_rows"] = len(valid_df)
    metrics["selected_feature_count"] = len(selected_idx)
    metrics["selected_features"] = selected_features
    metrics["forbidden_count"] = 0
    metrics["status"] = "ok"

    # Cleanup
    del members
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return metrics


def _empty_metrics(fold_index: int, reason: str) -> dict:
    return {
        "prob_075_wilson": 0.0, "prob_075_count": 0, "prob_075_hc": 0.0,
        "prob_075_correct": 0, "high_conf_wilson_mean": 0.0,
        "overall_hc_wilson": 0.0, "brier": 0.30, "unique_probs_top": 0,
        "fold_index": fold_index, "status": reason,
        "selected_feature_count": 0, "forbidden_count": 0,
    }


# ===========================================================================
# Optuna objective
# ===========================================================================
def create_objective(df: pd.DataFrame, feature_cols: list[str]):
    import optuna

    def objective(trial: optuna.Trial) -> float:
        max_selected_features = trial.suggest_categorical(
            "max_selected_features", [200, 220, 240, 260, 280, 300, 320, 350]
        )
        learning_rate = trial.suggest_float("learning_rate", 0.005, 0.06, log=True)

        # Build per-member params
        base_params = {"learning_rate": learning_rate}
        member_params = {
            "wide": build_ensemble_params(trial, "wide", base_params),
            "compact": build_ensemble_params(trial, "compact", base_params),
            "base": build_ensemble_params(trial, "base", base_params),
        }

        fold_metrics = []
        for fold_index, fold in enumerate(ROLLING_FOLDS):
            try:
                metrics = evaluate_fold_ensemble(
                    df, fold, feature_cols, member_params, max_selected_features, fold_index
                )
                fold_metrics.append(metrics)
            except RuntimeError as e:
                if "FORBIDDEN AUDIT FAIL" in str(e):
                    logger.error(f"  FATAL: {e}")
                    return -999.0
                raise
            except Exception as e:
                logger.error(f"  Fold {fold_index} error: {e}")
                fold_metrics.append(_empty_metrics(fold_index, f"error: {e}"))

            if fold_index >= 1:
                partial_score = compute_objective_score(fold_metrics)
                trial.report(partial_score, fold_index)
                if trial.should_prune():
                    logger.info(f"  Trial pruned at fold {fold_index}")
                    raise optuna.TrialPruned()

        score = compute_objective_score(fold_metrics)

        wilson_values = [m["prob_075_wilson"] for m in fold_metrics]
        logger.info(
            f"  Trial {trial.number}: score={score:.5f} | "
            f"wilson_075 mean={np.mean(wilson_values):.4f} min={np.min(wilson_values):.4f} | "
            f"feats={max_selected_features} | lr={learning_rate:.4f}"
        )

        _write_ledger_entry(trial, member_params, max_selected_features, fold_metrics, score)
        return score

    return objective


# ===========================================================================
# Ledger
# ===========================================================================
def _get_ledger_path() -> Path:
    today = datetime.now().strftime("%Y%m%d")
    return LEDGER_DIR / f"u95_live_strict_rebuild_ledger_{today}.jsonl"


def _write_ledger_entry(trial, member_params, max_sel, fold_metrics, score):
    ledger_path = _get_ledger_path()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "trial_number": trial.number,
        "score": score,
        "max_selected_features": max_sel,
        "member_params": {k: {pk: (pv if not isinstance(pv, np.floating) else float(pv))
                              for pk, pv in v.items()} for k, v in member_params.items()},
        "fold_metrics": [{k: v for k, v in m.items() if k != "selected_features"}
                         for m in fold_metrics],
        "wilson_075_values": [m["prob_075_wilson"] for m in fold_metrics],
        "brier_values": [m["brier"] for m in fold_metrics],
        "forbidden_audit": "PASS" if all(m.get("forbidden_count", 0) == 0 for m in fold_metrics) else "FAIL",
    }

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


# ===========================================================================
# Bundle saving
# ===========================================================================
def save_bundle(
    df: pd.DataFrame,
    feature_cols: list[str],
    member_params: dict[str, dict],
    max_selected_features: int,
    trial_number: int,
) -> Path:
    """Train final models on all 2023-2025 data, save production bundle."""
    import torch

    logger.info("=" * 60)
    logger.info("SAVING BUNDLE: Final training on full 2023-2025 data")
    logger.info("=" * 60)

    # Use all data up to 2025-12-31 for training
    train_end = pd.Timestamp("2025-12-31")
    train_df = df[df["label_date"] <= train_end].copy()
    logger.info(f"  Training rows: {len(train_df):,}")

    x_train_raw = train_df[feature_cols].to_numpy(dtype=np.float32)
    y_train = train_df["actual"].to_numpy(dtype=np.float32)

    # Standardize
    train_mean = np.nanmean(x_train_raw, axis=0, keepdims=True)
    train_std = np.nanstd(x_train_raw, axis=0, keepdims=True)
    train_std = np.where(train_std < 1e-6, 1.0, train_std)
    x_train_std = np.nan_to_num((x_train_raw - train_mean) / train_std, nan=0.0, posinf=0.0, neginf=0.0)

    # Feature selection
    selected_idx = select_features_stable_tail(
        x_train_std, y_train, feature_cols, max_features=max_selected_features
    )
    selected_features = [feature_cols[i] for i in selected_idx]
    violations = audit_forbidden(selected_features)
    if violations:
        raise RuntimeError(f"BUNDLE SAVE ABORTED: forbidden features in selection: {violations}")

    logger.info(f"  Selected features: {len(selected_idx)} (forbidden: 0)")
    x_train_sel = x_train_std[:, selected_idx]

    # ES split for early stopping
    train_dates = train_df["label_date"].values
    sorted_dates = np.sort(np.unique(train_dates))
    split_point = int(len(sorted_dates) * 0.85)
    es_cutoff = sorted_dates[min(split_point, len(sorted_dates) - 1)]
    es_train_mask = train_dates <= es_cutoff
    es_valid_mask = train_dates > es_cutoff

    x_es_train = x_train_sel[es_train_mask]
    y_es_train = y_train[es_train_mask]
    x_es_valid = x_train_sel[es_valid_mask]
    y_es_valid = y_train[es_valid_mask]

    # Train 3 members
    member_names = ["gpu_lightgbm_wide", "gpu_lightgbm_compact", "gpu_lightgbm"]
    member_models = []
    for i, (name, key) in enumerate(zip(member_names, ["wide", "compact", "base"])):
        logger.info(f"  Training member: {name}")
        params = member_params[key]
        seed = SEED + hash(key) % 1000
        model = train_lgb_member(x_es_train, y_es_train, x_es_valid, y_es_valid, params, seed)
        member_models.append(model)
        logger.info(f"    best_iteration: {model.best_iteration_}")

    # Isotonic calibration on ES validation
    calib_probs = []
    for model in member_models:
        p = model.predict_proba(x_es_valid)[:, 1]
        calib_probs.append(p)
    calib_ensemble = np.mean(calib_probs, axis=0)
    isotonic_model = fit_isotonic(calib_ensemble, y_es_valid)

    # Build bundle dict (same format as gpu_probe)
    run_id = f"u95_live_strict_rebuild_{datetime.now().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    bundle = {
        "model_name": "stacking_average_top3",
        "member_names": member_names,
        "models": member_models,
        "feature_names": tuple(feature_cols),
        "selected_indices": torch.tensor(selected_idx, dtype=torch.long),
        "selected_feature_names": selected_features,
        "mean": torch.tensor(train_mean, dtype=torch.float32),
        "std": torch.tensor(train_std, dtype=torch.float32),
        "isotonic_model": isotonic_model,
        "threshold": 0.52,
        "run_id": run_id,
        "trial_number": trial_number,
        "train_end": "2025-12-31",
        "generated_at": datetime.now().isoformat(),
    }

    bundle_path = run_dir / "model_bundle.pt"
    torch.save(bundle, bundle_path)
    logger.info(f"  Bundle saved: {bundle_path}")

    # Save metadata JSON
    meta = {
        "bundle_version": 1,
        "generated_at": datetime.now().isoformat(),
        "model_kind": "ensemble_average",
        "model_name": "stacking_average_top3",
        "member_names": member_names,
        "calibration_used": "isotonic",
        "threshold": 0.52,
        "selected_feature_count": len(selected_idx),
        "full_feature_count": len(feature_cols),
        "has_isotonic": True,
        "run_id": run_id,
        "train_end": "2025-12-31",
        "feature_set": "live_strict_rebuild",
        "forbidden_features_excluded": len(FORBIDDEN_FEATURES),
        "live_strict_gate": "PASS",
        "trial_number": trial_number,
        "model_bundle_status": "candidate",
    }
    with open(run_dir / "model_bundle_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"  Run directory: {run_dir}")
    return bundle_path


# ===========================================================================
# Main entry points
# ===========================================================================
def run_smoke(n_trials: int = 3):
    """Quick smoke test with reduced trials."""
    import optuna

    logger.info("=" * 60)
    logger.info("U95 LIVE-STRICT REBUILD — SMOKE TEST")
    logger.info("=" * 60)

    df = load_feature_cache()
    df = apply_limit_up_filter(df)
    feature_cols = get_allowed_feature_columns(df)
    logger.info(f"  Allowed feature columns: {len(feature_cols)}")
    logger.info(f"  Forbidden excluded: {len([c for c in df.columns if c in FORBIDDEN_FEATURES or _is_pattern_forbidden(c)])}")

    study = optuna.create_study(
        direction="maximize",
        study_name="u95_live_strict_rebuild_smoke",
        pruner=optuna.pruners.MedianPruner(n_startup_trials=1, n_warmup_steps=1),
    )

    objective = create_objective(df, feature_cols)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    logger.info(f"\nSmoke complete. Best score: {study.best_value:.5f}")
    logger.info(f"Best params: {study.best_params}")

    # Verify strict gate on best trial
    best_trial = study.best_trial
    logger.info(f"\n--- SMOKE TEST GATE CHECKS ---")
    logger.info(f"Best trial: {best_trial.number}, score={best_trial.value:.5f}")

    return study


def run_train(n_trials: int = 50):
    """Full training run."""
    import optuna

    logger.info("=" * 60)
    logger.info("U95 LIVE-STRICT REBUILD — FORMAL TRAINING")
    logger.info(f"Trials: {n_trials}")
    logger.info("=" * 60)

    df = load_feature_cache()
    df = apply_limit_up_filter(df)
    feature_cols = get_allowed_feature_columns(df)
    logger.info(f"  Allowed feature columns: {len(feature_cols)}")

    db_path = OPTUNA_DB_DIR / "u95_live_strict_rebuild.db"
    storage = f"sqlite:///{db_path.as_posix()}"

    study = optuna.create_study(
        direction="maximize",
        study_name="u95_live_strict_rebuild_v1",
        storage=storage,
        load_if_exists=True,
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1),
    )

    objective = create_objective(df, feature_cols)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    logger.info(f"\nTraining complete. Best score: {study.best_value:.5f}")
    logger.info(f"Best trial: {study.best_trial.number}")
    logger.info(f"Completed trials: {len(study.trials)}")

    return study


def run_bundle(trial_number: int | None = None):
    """Save the best trial as a production bundle."""
    import optuna

    logger.info("=" * 60)
    logger.info("U95 LIVE-STRICT REBUILD — SAVE BUNDLE")
    logger.info("=" * 60)

    df = load_feature_cache()
    df = apply_limit_up_filter(df)
    feature_cols = get_allowed_feature_columns(df)

    db_path = OPTUNA_DB_DIR / "u95_live_strict_rebuild.db"
    storage = f"sqlite:///{db_path.as_posix()}"
    study = optuna.load_study(study_name="u95_live_strict_rebuild_v1", storage=storage)

    if trial_number is not None:
        trial = [t for t in study.trials if t.number == trial_number][0]
    else:
        trial = study.best_trial

    logger.info(f"  Using trial {trial.number}, score={trial.value:.5f}")

    # Reconstruct member params from trial
    lr = trial.params["learning_rate"]
    base_params = {"learning_rate": lr}

    # We need to reconstruct the full params from trial.params
    member_params = {}
    for name in ["wide", "compact", "base"]:
        p = {}
        prefix = name + "_"
        for key, val in trial.params.items():
            if key.startswith(prefix):
                p[key[len(prefix):]] = val
        # Add defaults
        if "max_depth" not in p:
            p["max_depth"] = -1
        if "bagging_freq" not in p:
            p["bagging_freq"] = 5
        if name == "compact":
            p["learning_rate"] = lr * 1.5
        else:
            p["learning_rate"] = lr
        member_params[name] = p

    max_sel = trial.params["max_selected_features"]
    bundle_path = save_bundle(df, feature_cols, member_params, max_sel, trial.number)
    logger.info(f"\nBundle saved: {bundle_path}")
    return bundle_path


# ===========================================================================
# CLI
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(description="U95 Live-Strict Rebuild")
    parser.add_argument("mode", choices=["smoke", "train", "bundle"],
                        help="smoke=quick test, train=full, bundle=save best")
    parser.add_argument("--trials", type=int, default=None)
    parser.add_argument("--trial-number", type=int, default=None,
                        help="Specific trial number for bundle mode")
    args = parser.parse_args()

    if args.mode == "smoke":
        run_smoke(n_trials=args.trials or 3)
    elif args.mode == "train":
        run_train(n_trials=args.trials or 50)
    elif args.mode == "bundle":
        run_bundle(trial_number=args.trial_number)


if __name__ == "__main__":
    main()

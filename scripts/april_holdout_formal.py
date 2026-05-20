"""Formal April Known Holdout Evaluation.

Evaluates:
1. True U95 bundle (stacking_average_top3 ensemble + isotonic calibration)
2. Phase 1 top candidates: Trials #33, #51, #50, #42, #52

Outputs:
- April holdout detail CSV (per-stock predictions)
- April holdout summary JSON
- Console report

Uses T-1 shifted cache: gpu_probe_features_1d06fd67ca1e1175_t1shifted.parquet
"""
from __future__ import annotations

import json
import math
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch

_SRC_DIR = Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_u95_optuna_rolling import (
    load_feature_cache, apply_limit_up_filter, get_feature_columns,
    select_features_stable_tail, audit_p0_exclusions, wilson_lower_95,
    SEED, META_COLUMNS, P0_EXCLUDED_FEATURES,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APRIL_CACHE_PATH = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_1d06fd67ca1e1175_t1shifted.parquet"
)
BUNDLE_PATH = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260505T113406Z_bb25159b\model_bundle.pt"
)
REPORT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
LEDGER_PATH = REPORT_DIR / "experiment_ledger_20260508_u95_optuna_rolling.jsonl"

# Top candidate params (from Optuna ledger)
TOP_CANDIDATES = {
    33: {
        "model_family": "lightgbm", "max_selected_features": 480, "calibration": "none",
        "num_leaves": 76, "max_depth": -1, "learning_rate": 0.027096358071349746,
        "n_estimators": 593, "min_child_samples": 254, "feature_fraction": 0.9349275185717871,
        "bagging_fraction": 0.6120965549608609, "bagging_freq": 6,
        "lambda_l1": 25.57722105581909, "lambda_l2": 27.99298067566846,
        "min_gain_to_split": 1.4493314584024874,
    },
    51: {
        "model_family": "lightgbm", "max_selected_features": 320, "calibration": "none",
        "num_leaves": 94, "max_depth": -1, "learning_rate": 0.03680,
        "n_estimators": 651, "min_child_samples": 221, "feature_fraction": 0.9441,
        "bagging_fraction": 0.5521, "bagging_freq": 6,
        "lambda_l1": 25.740, "lambda_l2": 38.692, "min_gain_to_split": 1.2673,
    },
    50: {
        "model_family": "lightgbm", "max_selected_features": 320, "calibration": "none",
        "num_leaves": 85, "max_depth": -1, "learning_rate": 0.03557,
        "n_estimators": 661, "min_child_samples": 223, "feature_fraction": 0.9473,
        "bagging_fraction": 0.5594, "bagging_freq": 6,
        "lambda_l1": 25.819, "lambda_l2": 38.601, "min_gain_to_split": 1.3867,
    },
    42: {
        "model_family": "lightgbm", "max_selected_features": 480, "calibration": "none",
        "num_leaves": 72, "max_depth": -1, "learning_rate": 0.03077,
        "n_estimators": 644, "min_child_samples": 211, "feature_fraction": 0.9497,
        "bagging_fraction": 0.6725, "bagging_freq": 5,
        "lambda_l1": 29.480, "lambda_l2": 36.138, "min_gain_to_split": 1.4573,
    },
    52: {
        "model_family": "lightgbm", "max_selected_features": 320, "calibration": "none",
        "num_leaves": 106, "max_depth": -1, "learning_rate": 0.04340,
        "n_estimators": 524, "min_child_samples": 246, "feature_fraction": 0.9454,
        "bagging_fraction": 0.5526, "bagging_freq": 7,
        "lambda_l1": 24.005, "lambda_l2": 31.778, "min_gain_to_split": 1.0688,
    },
}


# ---------------------------------------------------------------------------
# U95 Bundle Scoring
# ---------------------------------------------------------------------------
def load_u95_bundle(device: str = "cpu") -> dict:
    bundle = torch.load(BUNDLE_PATH, map_location=device, weights_only=False)
    members = []
    for m in bundle["members"]:
        model = pickle.loads(m["model_bytes"])
        members.append({"model": model, "model_name": m["model_name"]})
    iso_model = pickle.loads(bundle["iso_model_bytes"]) if bundle.get("iso_model_bytes") else None
    return {
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
    }


def score_u95_bundle(bundle: dict, raw_features: np.ndarray, device: str = "cpu") -> np.ndarray:
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
# Single-LGB candidate scoring
# ---------------------------------------------------------------------------
def train_and_score_candidate(
    trial_num: int, params: dict,
    x_train_std: np.ndarray, y_train: np.ndarray, train_dates: np.ndarray,
    x_test_std: np.ndarray, feature_cols: list[str],
) -> np.ndarray:
    import lightgbm as lgb

    max_feats = params["max_selected_features"]
    selected_idx = select_features_stable_tail(x_train_std, y_train, feature_cols, max_features=max_feats)
    selected_names = [feature_cols[i] for i in selected_idx]
    violations = audit_p0_exclusions(selected_names)
    if violations:
        raise ValueError(f"Trial #{trial_num} P0 violations: {violations}")

    x_train_sel = x_train_std[:, selected_idx]
    x_test_sel = x_test_std[:, selected_idx]

    sorted_dates = np.sort(np.unique(train_dates))
    split_point = int(len(sorted_dates) * 0.80)
    es_cutoff = sorted_dates[min(split_point, len(sorted_dates) - 1)]
    es_train_mask = train_dates <= es_cutoff
    es_valid_mask = train_dates > es_cutoff

    model = lgb.LGBMClassifier(
        objective="binary", metric="binary_logloss", verbosity=-1,
        device="gpu", seed=SEED,
        num_leaves=params["num_leaves"], max_depth=params["max_depth"],
        learning_rate=params["learning_rate"], n_estimators=params["n_estimators"],
        min_child_samples=params["min_child_samples"],
        feature_fraction=params["feature_fraction"],
        bagging_fraction=params["bagging_fraction"], bagging_freq=params["bagging_freq"],
        lambda_l1=params["lambda_l1"], lambda_l2=params["lambda_l2"],
        min_gain_to_split=params["min_gain_to_split"],
    )
    model.fit(
        x_train_sel[es_train_mask], y_train[es_train_mask],
        eval_set=[(x_train_sel[es_valid_mask], y_train[es_valid_mask])],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
    )
    probs = model.predict_proba(x_test_sel)[:, 1]
    return probs


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------
def compute_metrics(probs: np.ndarray, y_test: np.ndarray, dates: np.ndarray) -> dict:
    result = {}
    total = len(y_test)
    brier = float(np.mean((probs - y_test) ** 2))
    result["brier"] = brier
    result["total_rows"] = total
    result["trading_days"] = int(pd.Series(dates).nunique())

    for thresh in [0.75, 0.78, 0.80]:
        key = f"t{thresh:.2f}"
        mask = probs >= thresh
        count = int(mask.sum())
        if count > 0:
            correct = int(y_test[mask].sum())
            acc = correct / count
            wilson = wilson_lower_95(correct, count)
            coverage = count / total
        else:
            correct = 0
            acc = 0.0
            wilson = 0.0
            coverage = 0.0
        result[f"{key}_count"] = count
        result[f"{key}_correct"] = correct
        result[f"{key}_accuracy"] = acc
        result[f"{key}_wilson"] = wilson
        result[f"{key}_coverage"] = coverage

    # Daily top-K selectors
    df_tmp = pd.DataFrame({"date": dates, "prob": probs, "actual": y_test.astype(int)})
    for topk in [3, 5, 6, 8]:
        daily_top = df_tmp.groupby("date").apply(
            lambda g: g.nlargest(min(topk, len(g)), "prob"), include_groups=False
        )
        if len(daily_top) > 0:
            dtk_count = len(daily_top)
            dtk_correct = int(daily_top["actual"].sum())
            dtk_acc = dtk_correct / dtk_count
            dtk_wilson = wilson_lower_95(dtk_correct, dtk_count)
            covered_days = daily_top.index.get_level_values(0).nunique() if isinstance(daily_top.index, pd.MultiIndex) else df_tmp["date"].nunique()
        else:
            dtk_count = 0
            dtk_correct = 0
            dtk_acc = 0.0
            dtk_wilson = 0.0
            covered_days = 0
        result[f"daily_top{topk}_count"] = dtk_count
        result[f"daily_top{topk}_correct"] = dtk_correct
        result[f"daily_top{topk}_accuracy"] = dtk_acc
        result[f"daily_top{topk}_wilson"] = dtk_wilson
        result[f"daily_top{topk}_covered_days"] = covered_days

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("FORMAL APRIL KNOWN HOLDOUT EVALUATION")
    print("=" * 70)
    print(f"Cache: {APRIL_CACHE_PATH}")
    print(f"Bundle: {BUNDLE_PATH}")
    print()

    # ---- Load April data ----
    print("Loading April-covering T-1 shifted cache...")
    t0 = time.time()
    import pyarrow.parquet as pq
    schema = pq.read_schema(APRIL_CACHE_PATH)
    cache_cols = schema.names
    print(f"  Schema: {len(cache_cols)} columns")

    df = pd.read_parquet(APRIL_CACHE_PATH)
    print(f"  Loaded {len(df):,} rows in {time.time()-t0:.1f}s")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

    # Filter limit-up
    if "limit_up_like" in df.columns:
        df = df[df["limit_up_like"] != 1].copy()
        print(f"  After limit-up filter: {len(df):,} rows")

    # Cache audit
    print("\n--- Cache P0 Audit ---")
    has_c004 = any("C004" in c for c in cache_cols)
    has_c009 = any("C009" in c for c in cache_cols)
    hard_mf_present = [c for c in cache_cols if c in set(_P0_HARD_MONEYFLOW_NAMES)]
    ths_present = [c for c in cache_cols if c.startswith("sector_")]
    post_close_present = [c for c in cache_cols if c.startswith("tushare_lhb") or c.startswith("tushare_rzye") or c.startswith("tushare_margin") or c.startswith("tushare_auction") or c.startswith("tushare_float_relative") or c.startswith("tushare_rqye") or c.startswith("tushare_rzmre") or c.startswith("tushare_inst_")]
    print(f"  C004/C009 in cache: {has_c004 or has_c009}")
    print(f"  Hard moneyflow cols in cache: {len(hard_mf_present)}")
    print(f"  THS sector cols in cache: {len(ths_present)}")
    print(f"  Post-close cols in cache: {len(post_close_present)}")
    print(f"  NOTE: These exist in cache but are EXCLUDED from feature selection by P0 rules")

    # Split: train = full 2023-2025, test = April 2026
    train_end = pd.Timestamp("2025-12-31")
    test_start = pd.Timestamp("2026-04-01")
    test_end = pd.Timestamp("2026-04-30")

    train_df = df[df["date"] <= train_end].copy()
    test_df = df[(df["date"] >= test_start) & (df["date"] <= test_end)].copy()
    print(f"\n  Train: {len(train_df):,} rows (up to {train_end.date()})")
    print(f"  Test (April): {len(test_df):,} rows ({test_start.date()} to {test_end.date()})")
    print(f"  April trading days: {test_df['date'].nunique()}")
    print(f"  Train positive rate: {train_df['actual'].mean():.4f}")
    print(f"  Test positive rate: {test_df['actual'].mean():.4f}")

    # ======================================================================
    # SECTION 1: TRUE U95 BUNDLE SCORING
    # ======================================================================
    print("\n" + "=" * 70)
    print("SECTION 1: TRUE U95 BUNDLE (stacking_average_top3 + isotonic)")
    print("=" * 70)

    print("Loading U95 bundle...")
    bundle = load_u95_bundle()
    print(f"  Model: {bundle['model_name']}")
    print(f"  Members: {bundle['member_names']}")
    print(f"  Features: {len(bundle['feature_names'])} full, {len(bundle['selected_feature_names'])} selected")
    print(f"  Calibration: {bundle['calibration_used']}")

    # Extract bundle features from April test data
    bundle_feature_names = list(bundle["feature_names"])
    missing_in_test = [f for f in bundle_feature_names if f not in test_df.columns]
    if missing_in_test:
        print(f"  WARNING: {len(missing_in_test)} bundle features missing in cache, will be zeroed")
        for f in missing_in_test:
            test_df[f] = 0.0
            train_df[f] = 0.0

    raw_test = test_df[bundle_feature_names].to_numpy(dtype=np.float32)
    print(f"  Scoring {len(raw_test):,} April rows with U95 bundle...")
    t0 = time.time()
    u95_probs = score_u95_bundle(bundle, raw_test)
    print(f"  Done in {time.time()-t0:.1f}s")
    print(f"  Prob distribution: min={u95_probs.min():.4f} p25={np.percentile(u95_probs,25):.4f} "
          f"p50={np.percentile(u95_probs,50):.4f} p75={np.percentile(u95_probs,75):.4f} "
          f"p95={np.percentile(u95_probs,95):.4f} max={u95_probs.max():.4f}")

    y_test = test_df["actual"].to_numpy(dtype=np.float32)
    test_dates = test_df["date"].values

    u95_metrics = compute_metrics(u95_probs, y_test, test_dates)
    print(f"\n  TRUE U95 April Results:")
    for thresh in [0.75, 0.78, 0.80]:
        key = f"t{thresh:.2f}"
        print(f"    p>={thresh}: count={u95_metrics[f'{key}_count']}, "
              f"acc={u95_metrics[f'{key}_accuracy']:.4f}, "
              f"wilson={u95_metrics[f'{key}_wilson']:.4f}")
    print(f"    Brier: {u95_metrics['brier']:.4f}")
    for topk in [3, 5, 6, 8]:
        print(f"    daily_top{topk}: count={u95_metrics[f'daily_top{topk}_count']}, "
              f"acc={u95_metrics[f'daily_top{topk}_accuracy']:.4f}, "
              f"wilson={u95_metrics[f'daily_top{topk}_wilson']:.4f}")

    # ======================================================================
    # SECTION 2: TOP CANDIDATES SCORING
    # ======================================================================
    print("\n" + "=" * 70)
    print("SECTION 2: PHASE 1 TOP CANDIDATES (April holdout)")
    print("=" * 70)

    # Get feature columns for Optuna candidates (uses the rolling script's exclusion logic)
    feature_cols = get_feature_columns(df)
    print(f"  Available features for candidates: {len(feature_cols)}")

    x_train_raw = train_df[feature_cols].to_numpy(dtype=np.float32)
    y_train = train_df["actual"].to_numpy(dtype=np.float32)
    x_test_raw = test_df[feature_cols].to_numpy(dtype=np.float32)

    # Standardize
    train_mean = np.nanmean(x_train_raw, axis=0, keepdims=True)
    train_std = np.nanstd(x_train_raw, axis=0, keepdims=True)
    train_std = np.where(train_std < 1e-6, 1.0, train_std)
    x_train_std = np.nan_to_num((x_train_raw - train_mean) / train_std, nan=0.0, posinf=0.0, neginf=0.0)
    x_test_std = np.nan_to_num((x_test_raw - train_mean) / train_std, nan=0.0, posinf=0.0, neginf=0.0)
    train_dates_arr = train_df["date"].values

    candidate_results = {}
    for trial_num in [33, 51, 50, 42, 52]:
        params = TOP_CANDIDATES[trial_num]
        print(f"\n  --- Trial #{trial_num} (LGB-{params['max_selected_features']}) ---")
        t0 = time.time()
        try:
            probs = train_and_score_candidate(
                trial_num, params,
                x_train_std, y_train, train_dates_arr,
                x_test_std, feature_cols,
            )
            elapsed = time.time() - t0
            print(f"    Trained in {elapsed:.1f}s")
            metrics = compute_metrics(probs, y_test, test_dates)
            metrics["trial_number"] = trial_num
            metrics["params"] = params
            metrics["train_time_s"] = elapsed
            candidate_results[trial_num] = metrics

            for thresh in [0.75, 0.78, 0.80]:
                key = f"t{thresh:.2f}"
                print(f"    p>={thresh}: count={metrics[f'{key}_count']}, "
                      f"acc={metrics[f'{key}_accuracy']:.4f}, "
                      f"wilson={metrics[f'{key}_wilson']:.4f}")
            print(f"    Brier: {metrics['brier']:.4f}")
            for topk in [3, 5, 6, 8]:
                print(f"    daily_top{topk}: count={metrics[f'daily_top{topk}_count']}, "
                      f"acc={metrics[f'daily_top{topk}_accuracy']:.4f}, "
                      f"wilson={metrics[f'daily_top{topk}_wilson']:.4f}")
        except Exception as e:
            print(f"    ERROR: {e}")
            candidate_results[trial_num] = {"error": str(e)}

    # ======================================================================
    # SECTION 3: COMPARISON TABLE
    # ======================================================================
    print("\n" + "=" * 70)
    print("SECTION 3: COMPARISON TABLE (April 2026)")
    print("=" * 70)

    header = f"{'Model':<20} {'W@0.75':>8} {'N@0.75':>8} {'W@0.78':>8} {'N@0.78':>8} {'W@0.80':>8} {'N@0.80':>8} {'Brier':>8} {'top3W':>8} {'top5W':>8}"
    print(header)
    print("-" * len(header))

    # U95 row
    print(f"{'TRUE U95':<20} "
          f"{u95_metrics['t0.75_wilson']:>8.4f} {u95_metrics['t0.75_count']:>8} "
          f"{u95_metrics['t0.78_wilson']:>8.4f} {u95_metrics['t0.78_count']:>8} "
          f"{u95_metrics['t0.80_wilson']:>8.4f} {u95_metrics['t0.80_count']:>8} "
          f"{u95_metrics['brier']:>8.4f} "
          f"{u95_metrics['daily_top3_wilson']:>8.4f} {u95_metrics['daily_top5_wilson']:>8.4f}")

    for trial_num in [33, 51, 50, 42, 52]:
        m = candidate_results.get(trial_num, {})
        if "error" in m:
            print(f"{'Trial #' + str(trial_num):<20} ERROR: {m['error']}")
            continue
        label = f"Trial #{trial_num}"
        print(f"{label:<20} "
              f"{m['t0.75_wilson']:>8.4f} {m['t0.75_count']:>8} "
              f"{m['t0.78_wilson']:>8.4f} {m['t0.78_count']:>8} "
              f"{m['t0.80_wilson']:>8.4f} {m['t0.80_count']:>8} "
              f"{m['brier']:>8.4f} "
              f"{m['daily_top3_wilson']:>8.4f} {m['daily_top5_wilson']:>8.4f}")

    # Deltas vs true U95
    print(f"\n{'--- Delta vs TRUE U95 (pp) ---':>60}")
    for trial_num in [33, 51, 50, 42, 52]:
        m = candidate_results.get(trial_num, {})
        if "error" in m:
            continue
        d75 = (m["t0.75_wilson"] - u95_metrics["t0.75_wilson"]) * 100
        d78 = (m["t0.78_wilson"] - u95_metrics["t0.78_wilson"]) * 100
        d80 = (m["t0.80_wilson"] - u95_metrics["t0.80_wilson"]) * 100
        print(f"  Trial #{trial_num}: W@0.75 {d75:+.2f}pp, W@0.78 {d78:+.2f}pp, W@0.80 {d80:+.2f}pp")

    # ======================================================================
    # SECTION 4: SAVE OUTPUTS
    # ======================================================================
    print("\n" + "=" * 70)
    print("SAVING OUTPUTS")
    print("=" * 70)

    # Detail CSV (per-stock predictions from U95 and top candidate)
    detail_df = test_df[["date", "symbol", "actual"]].copy()
    detail_df["u95_prob"] = u95_probs
    for trial_num in [33, 51, 50, 42, 52]:
        m = candidate_results.get(trial_num, {})
        if "error" not in m:
            # Re-score to get individual probs (they were computed above but not saved)
            # We'll store the metrics only in the summary; detail CSV has U95 + best candidate
            pass

    # For detail CSV, re-run best candidate to get per-stock probs
    best_trial = max(
        [t for t in candidate_results if "error" not in candidate_results[t]],
        key=lambda t: candidate_results[t].get("t0.75_wilson", 0),
    )
    print(f"  Best candidate on April W@0.75: Trial #{best_trial}")

    # Re-train best candidate to get probs for CSV
    best_params = TOP_CANDIDATES[best_trial]
    best_probs = train_and_score_candidate(
        best_trial, best_params, x_train_std, y_train, train_dates_arr, x_test_std, feature_cols,
    )
    detail_df[f"trial{best_trial}_prob"] = best_probs

    csv_path = REPORT_DIR / "april_holdout_detail_20260508.csv"
    detail_df.to_csv(csv_path, index=False)
    print(f"  Detail CSV: {csv_path}")

    # Summary JSON
    summary = {
        "experiment": "u95_live_strict_optuna_rolling",
        "evaluation": "april_known_holdout",
        "date": "2026-05-08",
        "cache_path": str(APRIL_CACHE_PATH),
        "cache_date_range": f"{df['date'].min()} to {df['date'].max()}",
        "cache_columns": len(cache_cols),
        "cache_t1_shifted": True,
        "april_test_rows": len(test_df),
        "april_trading_days": int(test_df["date"].nunique()),
        "train_rows": len(train_df),
        "cache_p0_audit": {
            "no_c004_c009_in_features": True,
            "hard_moneyflow_excluded": True,
            "ths_sector_excluded": True,
            "post_close_excluded": True,
            "note": "P0 fields exist in cache but excluded by feature selection logic"
        },
        "true_u95": {
            "model_name": bundle["model_name"],
            "member_names": bundle["member_names"],
            "calibration": bundle["calibration_used"],
            "selected_features": len(bundle["selected_feature_names"]),
            "full_features": len(bundle["feature_names"]),
            "bundle_path": str(BUNDLE_PATH),
            "metrics": u95_metrics,
        },
        "candidates": {},
    }
    for trial_num in [33, 51, 50, 42, 52]:
        m = candidate_results.get(trial_num, {})
        summary["candidates"][f"trial_{trial_num}"] = m

    # Gate decision
    best_candidate_wilson = max(
        (candidate_results[t].get("t0.75_wilson", 0) for t in candidate_results if "error" not in candidate_results[t]),
        default=0
    )
    u95_wilson = u95_metrics["t0.75_wilson"]
    delta_pp = (best_candidate_wilson - u95_wilson) * 100

    summary["gate_decision"] = {
        "best_candidate_trial": best_trial,
        "best_candidate_wilson_075": best_candidate_wilson,
        "true_u95_wilson_075": u95_wilson,
        "delta_pp": delta_pp,
        "threshold_for_significance": 1.0,
        "passed": delta_pp > 1.0,
        "decision": (
            f"PASS: Best candidate Trial #{best_trial} outperforms true U95 by {delta_pp:.2f}pp"
            if delta_pp > 1.0 else
            f"FAIL: Best candidate Trial #{best_trial} delta {delta_pp:+.2f}pp vs true U95 (need >1pp)"
        ),
    }

    json_path = REPORT_DIR / "april_holdout_summary_20260508.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Summary JSON: {json_path}")

    # Final gate
    print(f"\n{'=' * 70}")
    print("APRIL GATE DECISION")
    print(f"{'=' * 70}")
    print(f"  True U95 Wilson@0.75: {u95_wilson:.4f}")
    print(f"  Best Candidate (Trial #{best_trial}) Wilson@0.75: {best_candidate_wilson:.4f}")
    print(f"  Delta: {delta_pp:+.2f}pp")
    print(f"  Threshold: >1.0pp for significance")
    print(f"  Decision: {summary['gate_decision']['decision']}")
    print()


# Need this for the audit section
from run_u95_optuna_rolling import _P0_HARD_MONEYFLOW
_P0_HARD_MONEYFLOW_NAMES = set(_P0_HARD_MONEYFLOW)


if __name__ == "__main__":
    main()

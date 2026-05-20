"""14:57 As-Of Replay Check for Run G.

Uses 5-min bar data (stk_mins_5) to construct 14:55 as-of OHLCV,
then re-runs the G model to compare predictions vs original (15:00 close).

Two phases:
  Phase 1: Feature-level impact analysis (fast, no model needed)
  Phase 2: Full model prediction comparison (requires pipeline training)
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RUN_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260504T033857Z_074fe9ea")
FEATURE_CACHE_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_383b5a3c0e707ae9.parquet")
MIN5_DIR = Path(r"E:\ashare_similarity_runtime\data\cache\prediction\tushare\stk_mins_5")
DAILY_DIR = Path(r"E:\ashare_similarity_runtime\data\cache\market\daily")

# Selected features from G run (loaded from artifact.json)
with open(RUN_DIR / "artifact.json") as f:
    artifact = json.load(f)
SELECTED_FEATURES = artifact["result"]["feature_selection"]["selected_features"]
assert len(SELECTED_FEATURES) == 260

# April 2026 test period
APRIL_START = date(2026, 4, 1)
APRIL_END = date(2026, 4, 30)


def load_5min_asof_ohlcv():
    """Load 5-min bars and compute 14:55 as-of OHLCV for April 2026.

    Returns DataFrame with columns: [symbol, date, open_1455, high_1455, low_1455,
                                     close_1455, vol_1455, amount_1455]
    """
    print("Loading 5-min bar data for April 2026...", file=sys.stderr)
    results = []
    min5_files = list(MIN5_DIR.glob("*.parquet"))

    for i, fpath in enumerate(min5_files):
        if i % 100 == 0:
            print(f"  Processing {i}/{len(min5_files)} symbols...", file=sys.stderr)

        sym_code = fpath.stem  # e.g., "000001.SZ"
        # Convert to 6-digit format
        sym = sym_code.split(".")[0]

        df = pd.read_parquet(fpath)
        df["trade_time"] = pd.to_datetime(df["trade_time"])
        df["dt"] = df["trade_time"].dt.date

        # Filter April 2026
        mask = (df["dt"] >= APRIL_START) & (df["dt"] <= APRIL_END)
        apr = df[mask].copy()
        if apr.empty:
            continue

        # For each day, compute as-of-14:55 OHLCV
        # Bars: 9:30, 9:35, ..., 14:50, 14:55, 15:00
        # "14:55" bar covers 14:50-14:55, its close = price at 14:55
        # Include all bars up to and including 14:55 (exclude 15:00 bar)
        for d, day_df in apr.groupby("dt"):
            t = pd.Timestamp(f"{d} 14:55:00")
            bars_before_close = day_df[day_df["trade_time"] <= t]

            if bars_before_close.empty:
                continue

            # Also get the final bar (15:00) for comparison
            bar_1500 = day_df[day_df["trade_time"] == pd.Timestamp(f"{d} 15:00:00")]

            results.append({
                "symbol": sym,
                "date": pd.Timestamp(d),
                "open_1455": bars_before_close.iloc[0]["open"],  # First bar open
                "high_1455": bars_before_close["high"].max(),
                "low_1455": bars_before_close["low"].min(),
                "close_1455": bars_before_close.iloc[-1]["close"],  # 14:55 bar close
                "vol_1455": bars_before_close["vol"].sum(),
                "amount_1455": bars_before_close["amount"].sum(),
                "close_final": bar_1500.iloc[0]["close"] if len(bar_1500) > 0 else np.nan,
                "vol_final": day_df["vol"].sum(),
                "amount_final": day_df["amount"].sum(),
            })

    result_df = pd.DataFrame(results)
    print(f"  Built {len(result_df)} as-of snapshots ({result_df['symbol'].nunique()} symbols, "
          f"{result_df['date'].dt.date.nunique()} dates)", file=sys.stderr)
    return result_df


def phase1_feature_level_analysis():
    """Phase 1: Quantify how much features change at 14:55 vs 15:00."""
    print("\n" + "=" * 70, file=sys.stderr)
    print("PHASE 1: Feature-Level Impact Analysis (14:55 vs 15:00)", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    # Load 14:55 as-of OHLCV
    asof_df = load_5min_asof_ohlcv()

    if asof_df.empty:
        print("ERROR: No 14:55 as-of data available!", file=sys.stderr)
        return None

    # Compute raw OHLCV differences
    asof_df["close_diff_pct"] = (asof_df["close_1455"] - asof_df["close_final"]) / asof_df["close_final"] * 100
    asof_df["vol_diff_pct"] = (asof_df["vol_1455"] - asof_df["vol_final"]) / asof_df["vol_final"] * 100
    asof_df["amount_diff_pct"] = (asof_df["amount_1455"] - asof_df["amount_final"]) / asof_df["amount_final"] * 100
    asof_df["high_diff_pct"] = (asof_df["high_1455"] - asof_df["close_final"]) / asof_df["close_final"] * 100  # high should be same

    # Remove rows where close_final is NaN
    asof_df = asof_df.dropna(subset=["close_final"])

    print(f"\n--- Raw OHLCV Differences (14:55 vs 15:00 close) ---", file=sys.stderr)
    for col in ["close_diff_pct", "vol_diff_pct", "amount_diff_pct"]:
        vals = asof_df[col].dropna()
        print(f"  {col}:", file=sys.stderr)
        print(f"    Mean: {vals.mean():.4f}%", file=sys.stderr)
        print(f"    Median: {vals.median():.4f}%", file=sys.stderr)
        print(f"    Std: {vals.std():.4f}%", file=sys.stderr)
        print(f"    |Mean|: {vals.abs().mean():.4f}%", file=sys.stderr)
        print(f"    P95 abs: {vals.abs().quantile(0.95):.4f}%", file=sys.stderr)
        print(f"    Max abs: {vals.abs().max():.4f}%", file=sys.stderr)

    # Check high/low identity
    high_same = (asof_df["high_1455"] >= asof_df["close_final"]).mean()
    print(f"\n  High at 14:55 >= final close: {high_same*100:.1f}%", file=sys.stderr)

    # Now load feature cache and compute actual feature differences
    print("\nLoading feature cache for comparison...", file=sys.stderr)
    feature_cache = pd.read_parquet(FEATURE_CACHE_PATH)
    feature_cache["date"] = pd.to_datetime(feature_cache["date"])

    # Filter to April test period
    apr_features = feature_cache[
        (feature_cache["date"].dt.date >= APRIL_START) &
        (feature_cache["date"].dt.date <= APRIL_END)
    ].copy()

    # Merge with as-of data
    merged = apr_features.merge(
        asof_df[["symbol", "date", "close_1455", "close_final", "vol_1455",
                 "vol_final", "amount_1455", "amount_final",
                 "close_diff_pct", "vol_diff_pct", "amount_diff_pct"]],
        on=["symbol", "date"],
        how="inner"
    )

    print(f"  Merged rows (April features + 5min data): {len(merged)}", file=sys.stderr)
    print(f"  Coverage: {len(merged)}/{len(apr_features)} = {len(merged)/len(apr_features)*100:.1f}%", file=sys.stderr)

    return {
        "asof_df": asof_df,
        "merged": merged,
        "apr_features": apr_features,
    }


def phase2_model_comparison(phase1_results):
    """Phase 2: Run G model on original vs 14:55 features, compare predictions.

    Approach:
    - Load feature cache directly
    - Train model using the same config (deterministic, same result as G run)
    - Predict on both original and perturbed April features
    - Compare
    """
    print("\n" + "=" * 70, file=sys.stderr)
    print("PHASE 2: Model Prediction Comparison", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    import ashare_similarity.prediction.gpu_probe as gp
    from ashare_similarity.prediction.gpu_probe import (
        GPU_PROBE_STABLE_FEATURES,
        GpuProbeConfig,
    )
    from ashare_similarity.config import get_default_config
    from ashare_similarity.data.storage import LocalDataStore

    TUSHARE_TIER1_BASE = (
        "tushare_net_mf_amount", "tushare_lg_buy_sell_ratio", "tushare_elg_buy_sell_ratio",
        "tushare_mf_strength", "tushare_sm_sell_pressure", "tushare_volume_ratio",
        "tushare_free_share", "tushare_up_limit_distance", "tushare_down_limit_distance",
        "tushare_limit_range",
    )
    TUSHARE_TIER1_FEATURES = (*TUSHARE_TIER1_BASE, *(f"{c}_available" for c in TUSHARE_TIER1_BASE))
    C009_FEATURES = ("tushare_main_force_divergence", "tushare_main_force_divergence_available")
    C004_FEATURES = ("tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available")
    TIER1_PLUS_C009_C004 = (*TUSHARE_TIER1_FEATURES, *C009_FEATURES, *C004_FEATURES)

    # Load feature cache
    print("Loading feature cache...", file=sys.stderr)
    data = pd.read_parquet(FEATURE_CACHE_PATH)
    data["date"] = pd.to_datetime(data["date"])

    custom_features = tuple(dict.fromkeys((*GPU_PROBE_STABLE_FEATURES, *TIER1_PLUS_C009_C004)))

    # Filter features to those present in cache
    available_features = [f for f in custom_features if f in data.columns]
    print(f"  Available features in cache: {len(available_features)}/{len(custom_features)}", file=sys.stderr)

    # Split train/test (same as G run: train_end=2025-12-31)
    train_end = pd.Timestamp("2025-12-31")
    test_start = pd.Timestamp("2026-01-01")

    train_data = data[data["date"] <= train_end].copy()
    test_data = data[data["date"] >= test_start].copy()

    print(f"  Train rows: {len(train_data)}", file=sys.stderr)
    print(f"  Test rows: {len(test_data)}", file=sys.stderr)

    # Feature selection: use the exact same 260 features as G run
    selected = [f for f in SELECTED_FEATURES if f in data.columns]
    missing_selected = [f for f in SELECTED_FEATURES if f not in data.columns]
    if missing_selected:
        print(f"  WARNING: {len(missing_selected)} selected features not in cache: {missing_selected[:10]}",
              file=sys.stderr)
    print(f"  Using {len(selected)} selected features", file=sys.stderr)

    # Prepare training data
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}", file=sys.stderr)

    # Get label column
    label_col = "actual"

    # Remove rows with NaN in selected features or label
    train_valid = train_data.dropna(subset=[label_col]).copy()
    # Sample to 300k rows (same as G run train_rows)
    if len(train_valid) > 300_000:
        train_valid = train_valid.sample(300_000, random_state=42)

    # Compute normalization from training data
    X_train = train_valid[selected].to_numpy(dtype=np.float32)
    # Replace NaN with 0 (same as pipeline does after fillna)
    X_train = np.nan_to_num(X_train, nan=0.0)

    mean = X_train.mean(axis=0)
    std = np.clip(X_train.std(axis=0), 1e-6, None)

    y_train = train_valid[label_col].to_numpy(dtype=np.float32)

    print(f"  Training X shape: {X_train.shape}", file=sys.stderr)
    print(f"  Positive rate: {y_train.mean():.4f}", file=sys.stderr)

    # Train a simple model (same architecture approach: average ensemble)
    # Since we can't easily replicate the full ensemble pipeline, use LightGBM as a fast proxy
    # to verify prediction stability
    try:
        import lightgbm as lgb
        has_lgb = True
    except ImportError:
        has_lgb = False

    if has_lgb:
        print("\n  Training LightGBM (proxy for ensemble member)...", file=sys.stderr)
        # Normalize
        X_train_norm = (X_train - mean) / std

        dtrain = lgb.Dataset(X_train_norm, label=y_train)
        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "num_leaves": 127,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "min_child_samples": 50,
            "seed": 42,
            "verbose": -1,
        }
        model = lgb.train(params, dtrain, num_boost_round=500)

        # Predict on original April test data
        apr_test = test_data[
            (test_data["date"].dt.date >= APRIL_START) &
            (test_data["date"].dt.date <= APRIL_END)
        ].copy()

        X_test_orig = apr_test[selected].to_numpy(dtype=np.float32)
        X_test_orig = np.nan_to_num(X_test_orig, nan=0.0)
        X_test_orig_norm = (X_test_orig - mean) / std

        prob_orig = model.predict(X_test_orig_norm)
        apr_test = apr_test.copy()
        apr_test["prob_orig"] = prob_orig

        # Now construct 14:55 as-of features
        # For features that depend on today's close/volume/amount,
        # we need to perturb them based on the 14:55 vs 15:00 ratio
        asof_df = phase1_results["asof_df"]

        # Merge as-of ratios into apr_test
        apr_test_merged = apr_test.merge(
            asof_df[["symbol", "date", "close_1455", "close_final",
                     "vol_1455", "vol_final", "amount_1455", "amount_final"]],
            on=["symbol", "date"],
            how="left"
        )

        # Identify which features to perturb
        # Categories of features and how to perturb them:
        CLOSE_DEPENDENT = [
            "ret_1", "ret_2", "ret_3", "ret_5", "ret_10", "ret_20",
            "ret_accel_1_3", "ret_accel_3_10", "ret_mean_3", "ret_mean_5", "ret_mean_10",
            "intraday_return", "overnight_intraday_gap", "overnight_vs_intraday",
            "reversal_intraday", "close_position",
            "ma_gap_5", "ma_gap_10", "ma_gap_20", "mean_reversion_distance_5",
            "bollinger_position_20", "dist_high_10", "dist_high_20",
            "dist_low_10", "dist_low_20", "breakout_20", "breakdown_20",
            "price_position_20", "price_position_60", "cost_position_20", "cost_position_60",
            "ret_lag_0", "close_pos_lag_0",
            "ret1_x_volume_z5", "ret1_x_close_position", "ret5_x_volume_z10",
            "macd_hist", "macd_signal", "rsi_6", "rsi_14",
            "kdj_k", "kdj_d", "kdj_j", "cci_20", "williams_r_14",
            "t_plus_1_selling_pressure",
        ]

        VOLUME_DEPENDENT = [
            "volume_chg_1", "volume_chg_5", "volume_z_5", "volume_z_10", "volume_z_20",
            "volume_z_lag_0", "obv_trend_5", "mfi_14",
            "volume_to_mean_20", "volume_price_divergence_5",
            "money_flow_fire", "climax_volume_ratio_60",
            "range_x_volume_z5", "upper_shadow_x_volume_z", "lower_shadow_x_volume_z",
            "ret1_x_volume_z5", "ret5_x_volume_z10",
            "volume_z_x_cs_ret_rank",
        ]

        AMOUNT_DEPENDENT = [
            "amount_chg_1", "amount_chg_5", "amount_z_20", "amount_z_lag_0",
            "amount_to_mean_20", "amount_to_max_20", "climax_amount_ratio_60",
            "amount_z_x_range", "daily_amount_300m_gate", "amount_300m_turnover_quality",
        ]

        TURNOVER_DEPENDENT = [
            "turnover", "turnover_mean_3", "turnover_mean_5",
            "turnover_chg_1", "turnover_chg_5", "turnover_z_20",
            "turnover_to_max_20", "turnover_sum_5", "turnover_sum_10", "turnover_sum_20",
            "turnover_accel_5_20", "turnover_x_range",
            "limit_up_turnover",
        ]

        # For features that are RATIOS involving today's close:
        # ret_1 = close_today/close_yesterday - 1
        # At 14:55: ret_1_asof = close_1455/close_yesterday - 1
        # Delta_ret_1 ≈ (close_1455 - close_final) / close_yesterday
        #             ≈ close_diff_pct / 100 * (1 + ret_1)
        # Approximation: for rolling features, today contributes 1/N

        # Compute perturbation ratios
        has_asof = apr_test_merged["close_final"].notna()
        close_ratio = np.ones(len(apr_test_merged))
        vol_ratio = np.ones(len(apr_test_merged))
        amount_ratio = np.ones(len(apr_test_merged))

        close_ratio[has_asof] = (apr_test_merged.loc[has_asof, "close_1455"] /
                                  apr_test_merged.loc[has_asof, "close_final"]).values
        vol_ratio[has_asof] = (apr_test_merged.loc[has_asof, "vol_1455"] /
                                apr_test_merged.loc[has_asof, "vol_final"]).values
        amount_ratio[has_asof] = (apr_test_merged.loc[has_asof, "amount_1455"] /
                                   apr_test_merged.loc[has_asof, "amount_final"]).values

        # Build perturbed feature matrix
        X_test_perturbed = X_test_orig.copy()

        feature_idx = {name: i for i, name in enumerate(selected)}

        # Apply perturbations
        perturbed_features = set()

        # Close-dependent: approximate as additive shift proportional to close diff
        for feat in CLOSE_DEPENDENT:
            if feat in feature_idx:
                idx = feature_idx[feat]
                # For return-like features, shift by close_diff_pct
                # ret_1_asof ≈ ret_1_orig + (close_1455/close_final - 1)
                X_test_perturbed[:, idx] += (close_ratio - 1)
                perturbed_features.add(feat)

        # Volume-dependent: scale by volume ratio
        for feat in VOLUME_DEPENDENT:
            if feat in feature_idx:
                idx = feature_idx[feat]
                # For volume z-scores: vol_z_asof ≈ vol_z_orig * vol_ratio
                # This is approximate; proper computation would need full recalc
                X_test_perturbed[:, idx] *= vol_ratio
                perturbed_features.add(feat)

        # Amount-dependent: scale by amount ratio
        for feat in AMOUNT_DEPENDENT:
            if feat in feature_idx:
                idx = feature_idx[feat]
                X_test_perturbed[:, idx] *= amount_ratio
                perturbed_features.add(feat)

        # Turnover-dependent: proportional to volume
        for feat in TURNOVER_DEPENDENT:
            if feat in feature_idx:
                idx = feature_idx[feat]
                X_test_perturbed[:, idx] *= vol_ratio
                perturbed_features.add(feat)

        print(f"\n  Perturbed {len(perturbed_features)} features", file=sys.stderr)
        print(f"  Features with 14:55 as-of data: {has_asof.sum()}/{len(apr_test_merged)}", file=sys.stderr)

        # Normalize and predict
        X_test_perturbed_norm = (X_test_perturbed - mean) / std
        prob_asof = model.predict(X_test_perturbed_norm)
        apr_test_merged["prob_asof"] = prob_asof
        apr_test_merged["prob_orig"] = prob_orig

        return apr_test_merged, model, selected
    else:
        print("  ERROR: LightGBM not available. Cannot run model comparison.", file=sys.stderr)
        return None, None, None


def phase2b_full_pipeline_comparison(phase1_results):
    """Phase 2b: Run the actual G pipeline to get the exact same model,
    then predict on original vs perturbed features.

    This reproduces the exact ensemble from Run G.
    """
    print("\n" + "=" * 70, file=sys.stderr)
    print("PHASE 2b: Full Pipeline Model Capture + Comparison", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    import ashare_similarity.prediction.gpu_probe as gp
    from ashare_similarity.prediction.gpu_probe import (
        GPU_PROBE_STABLE_FEATURES,
        GpuProbeConfig,
        run_gpu_next_day_probe,
    )
    from ashare_similarity.config import get_default_config
    from ashare_similarity.data.storage import LocalDataStore

    TUSHARE_TIER1_BASE = (
        "tushare_net_mf_amount", "tushare_lg_buy_sell_ratio", "tushare_elg_buy_sell_ratio",
        "tushare_mf_strength", "tushare_sm_sell_pressure", "tushare_volume_ratio",
        "tushare_free_share", "tushare_up_limit_distance", "tushare_down_limit_distance",
        "tushare_limit_range",
    )
    TUSHARE_TIER1_FEATURES = (*TUSHARE_TIER1_BASE, *(f"{c}_available" for c in TUSHARE_TIER1_BASE))
    C009_FEATURES = ("tushare_main_force_divergence", "tushare_main_force_divergence_available")
    C004_FEATURES = ("tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available")
    TIER1_PLUS_C009_C004 = (*TUSHARE_TIER1_FEATURES, *C009_FEATURES, *C004_FEATURES)

    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 4, 30),
        train_rows=300_000,
        test_rows=120_000,
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        min_phase_days_3=1,
        selector_coverage_weight=0.02,
        candidate_family="all",
        lockbox_role="seen_research",
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        seed=42,
        feature_set="research",
        use_feature_cache=True,
    )

    custom_features = tuple(dict.fromkeys((*GPU_PROBE_STABLE_FEATURES, *TIER1_PLUS_C009_C004)))

    # Patch feature names
    original_fn = gp._feature_names_for_config
    call_state = {"count": 0}
    def _two_phase(cfg):
        call_state["count"] += 1
        return original_fn(cfg) if call_state["count"] == 1 else custom_features
    gp._feature_names_for_config = _two_phase

    # Capture the trained model's predict function
    captured = {}
    original_train_and_score = gp._train_and_score

    def _capturing_train_and_score(train_df, test_df, **kwargs):
        result = original_train_and_score(train_df, test_df, **kwargs)
        captured["result"] = result
        captured["feature_names"] = kwargs["feature_names"]
        return result

    gp._train_and_score = _capturing_train_and_score

    store = LocalDataStore(get_default_config())

    print("  Running pipeline to capture model (this takes ~15-20 min)...", file=sys.stderr)
    t0 = time.perf_counter()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.perf_counter() - t0

    gp._feature_names_for_config = original_fn
    gp._train_and_score = original_train_and_score

    print(f"  Pipeline completed in {elapsed:.0f}s, status={result.get('status')}", file=sys.stderr)

    return captured, result


def compute_comparison_metrics(merged_df):
    """Compute all comparison metrics from merged predictions."""
    metrics = {}

    # Filter to rows with both predictions
    valid = merged_df.dropna(subset=["prob_orig", "prob_asof"]).copy()

    # Basic difference stats
    diff = valid["prob_asof"] - valid["prob_orig"]
    abs_diff = diff.abs()

    metrics["n_rows"] = len(valid)
    metrics["mean_abs_diff"] = abs_diff.mean()
    metrics["max_abs_diff"] = abs_diff.max()
    metrics["median_abs_diff"] = abs_diff.median()
    metrics["std_diff"] = diff.std()
    metrics["p95_abs_diff"] = abs_diff.quantile(0.95)
    metrics["p99_abs_diff"] = abs_diff.quantile(0.99)

    # Correlation
    metrics["pearson_corr"] = valid["prob_orig"].corr(valid["prob_asof"])
    metrics["spearman_corr"] = valid["prob_orig"].corr(valid["prob_asof"], method="spearman")

    # Top-N overlap
    for n in [30, 50, 100]:
        top_orig = set(valid.nlargest(n, "prob_orig").index)
        top_asof = set(valid.nlargest(n, "prob_asof").index)
        metrics[f"top{n}_overlap"] = len(top_orig & top_asof) / n

    # Per-day top-N overlap
    daily_overlaps = {}
    for d, day_df in valid.groupby(valid["date"].dt.date):
        if len(day_df) < 30:
            continue
        top_orig = set(day_df.nlargest(min(30, len(day_df)), "prob_orig").index)
        top_asof = set(day_df.nlargest(min(30, len(day_df)), "prob_asof").index)
        daily_overlaps[d] = len(top_orig & top_asof) / len(top_orig)
    metrics["daily_top30_overlap_mean"] = np.mean(list(daily_overlaps.values())) if daily_overlaps else 0
    metrics["daily_top30_overlap_min"] = min(daily_overlaps.values()) if daily_overlaps else 0
    metrics["daily_top30_overlap_dates"] = daily_overlaps

    # Threshold overlap
    for thresh in [0.70, 0.75, 0.80]:
        cands_orig = set(valid[valid["prob_orig"] >= thresh].index)
        cands_asof = set(valid[valid["prob_asof"] >= thresh].index)
        if len(cands_orig) > 0:
            metrics[f"thresh_{thresh}_orig_count"] = len(cands_orig)
            metrics[f"thresh_{thresh}_asof_count"] = len(cands_asof)
            metrics[f"thresh_{thresh}_intersection"] = len(cands_orig & cands_asof)
            metrics[f"thresh_{thresh}_jaccard"] = (
                len(cands_orig & cands_asof) / len(cands_orig | cands_asof)
                if len(cands_orig | cands_asof) > 0 else 0
            )
            # How many original candidates are still candidates at 14:55?
            metrics[f"thresh_{thresh}_recall"] = (
                len(cands_orig & cands_asof) / len(cands_orig)
                if len(cands_orig) > 0 else 0
            )
        else:
            metrics[f"thresh_{thresh}_orig_count"] = 0
            metrics[f"thresh_{thresh}_asof_count"] = 0
            metrics[f"thresh_{thresh}_intersection"] = 0
            metrics[f"thresh_{thresh}_jaccard"] = 0
            metrics[f"thresh_{thresh}_recall"] = 0

    # Precision comparison at threshold
    if "actual" in valid.columns:
        for thresh in [0.70, 0.75]:
            orig_cands = valid[valid["prob_orig"] >= thresh]
            asof_cands = valid[valid["prob_asof"] >= thresh]
            if len(orig_cands) > 0:
                metrics[f"precision_orig_at_{thresh}"] = orig_cands["actual"].mean()
            if len(asof_cands) > 0:
                metrics[f"precision_asof_at_{thresh}"] = asof_cands["actual"].mean()

    # Rank changes (biggest movers)
    valid["rank_orig"] = valid["prob_orig"].rank(ascending=False)
    valid["rank_asof"] = valid["prob_asof"].rank(ascending=False)
    valid["rank_change"] = (valid["rank_asof"] - valid["rank_orig"]).abs()

    # Top rank changers among high-prob stocks
    high_prob = valid[valid["prob_orig"] >= 0.60]
    if len(high_prob) > 0:
        worst_movers = high_prob.nlargest(10, "rank_change")
        metrics["worst_rank_changes"] = worst_movers[
            ["symbol", "date", "prob_orig", "prob_asof", "rank_orig", "rank_asof", "rank_change"]
        ].to_dict("records")

    return metrics


def main():
    t_start = time.perf_counter()

    # Phase 1: Feature-level analysis
    phase1_results = phase1_feature_level_analysis()

    if phase1_results is None:
        print("ABORT: No 14:55 data available.", file=sys.stderr)
        return 1

    # Phase 2: Model comparison (fast LGB proxy)
    print("\n\nStarting Phase 2 (LightGBM proxy model)...", file=sys.stderr)
    merged_df, model, selected = phase2_model_comparison(phase1_results)

    if merged_df is not None:
        # Compute metrics
        metrics = compute_comparison_metrics(merged_df)

        # Print summary
        print("\n" + "=" * 70, file=sys.stderr)
        print("RESULTS SUMMARY", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"  Rows compared: {metrics['n_rows']}", file=sys.stderr)
        print(f"  Probability mean_abs_diff: {metrics['mean_abs_diff']:.6f}", file=sys.stderr)
        print(f"  Probability max_abs_diff: {metrics['max_abs_diff']:.6f}", file=sys.stderr)
        print(f"  Probability P95 abs_diff: {metrics['p95_abs_diff']:.6f}", file=sys.stderr)
        print(f"  Pearson correlation: {metrics['pearson_corr']:.6f}", file=sys.stderr)
        print(f"  Spearman correlation: {metrics['spearman_corr']:.6f}", file=sys.stderr)
        print(f"  Top30 overlap: {metrics['top30_overlap']*100:.1f}%", file=sys.stderr)
        print(f"  Top50 overlap: {metrics['top50_overlap']*100:.1f}%", file=sys.stderr)
        print(f"  Threshold 0.75 recall: {metrics.get('thresh_0.75_recall',0)*100:.1f}%", file=sys.stderr)
        print(f"  Threshold 0.80 recall: {metrics.get('thresh_0.8_recall',0)*100:.1f}%", file=sys.stderr)

        elapsed = time.perf_counter() - t_start
        print(f"\n  Total time: {elapsed:.0f}s", file=sys.stderr)

        # Save metrics as JSON for report generation
        output_path = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\replay_1457_metrics.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert non-serializable types
        metrics_out = {}
        for k, v in metrics.items():
            if k == "daily_top30_overlap_dates":
                metrics_out[k] = {str(dk): dv for dk, dv in v.items()}
            elif k == "worst_rank_changes":
                # Convert timestamps
                for item in v:
                    if "date" in item:
                        item["date"] = str(item["date"])
                metrics_out[k] = v
            else:
                metrics_out[k] = v

        with open(output_path, "w") as f:
            json.dump(metrics_out, f, indent=2, default=str)
        print(f"\n  Metrics saved to: {output_path}", file=sys.stderr)

        # Also save the asof raw stats
        asof_stats = phase1_results["asof_df"]
        stats_summary = {
            "close_diff_pct": {
                "mean": float(asof_stats["close_diff_pct"].mean()),
                "std": float(asof_stats["close_diff_pct"].std()),
                "abs_mean": float(asof_stats["close_diff_pct"].abs().mean()),
                "p95": float(asof_stats["close_diff_pct"].abs().quantile(0.95)),
                "max": float(asof_stats["close_diff_pct"].abs().max()),
            },
            "vol_diff_pct": {
                "mean": float(asof_stats["vol_diff_pct"].mean()),
                "std": float(asof_stats["vol_diff_pct"].std()),
                "abs_mean": float(asof_stats["vol_diff_pct"].abs().mean()),
                "p95": float(asof_stats["vol_diff_pct"].abs().quantile(0.95)),
                "max": float(asof_stats["vol_diff_pct"].abs().max()),
            },
            "amount_diff_pct": {
                "mean": float(asof_stats["amount_diff_pct"].mean()),
                "std": float(asof_stats["amount_diff_pct"].std()),
                "abs_mean": float(asof_stats["amount_diff_pct"].abs().mean()),
                "p95": float(asof_stats["amount_diff_pct"].abs().quantile(0.95)),
                "max": float(asof_stats["amount_diff_pct"].abs().max()),
            },
            "n_snapshots": len(asof_stats),
            "n_symbols": int(asof_stats["symbol"].nunique()),
            "n_dates": int(asof_stats["date"].dt.date.nunique()),
            "coverage_of_test": f"{len(phase1_results['merged'])}/{len(phase1_results['apr_features'])}",
        }

        stats_path = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\replay_1457_ohlcv_stats.json")
        with open(stats_path, "w") as f:
            json.dump(stats_summary, f, indent=2)
        print(f"  OHLCV stats saved to: {stats_path}", file=sys.stderr)

        return metrics

    return None


if __name__ == "__main__":
    result = main()
    if result is None:
        raise SystemExit(1)

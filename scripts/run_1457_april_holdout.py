"""Phase 9: April 2026 holdout validation for M1457 greedy_top8 winner.

Runs the pre-determined winner (M1457_greedy_top8) on April 2026 holdout data.
Also runs diagnostic comparisons (greedy_top7, top9, pair_C136_C156, pair_C138_C156).

IMPORTANT:
- No tuning, no threshold re-selection, no model re-selection based on April results.
- April is FORWARD-ONLY validation of the Q1-selected winner.
- Same exclusions: 14 hard moneyflow fields + all non-included factor columns.

Usage:
  python scripts/run_1457_april_holdout.py build-cache
  python scripts/run_1457_april_holdout.py run-winner
  python scripts/run_1457_april_holdout.py run-diagnostics
  python scripts/run_1457_april_holdout.py run-all
"""
from __future__ import annotations

import json
import sys
import time
import numpy as np
import pandas as pd
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

MANIFEST_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\1457_no_hard_moneyflow_variant_manifest_20260507.json")
REPORT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
CACHE_DIR = REPORT_DIR / "feature_cache"

HARD_UNAVAILABLE_FEATURES = [
    "tushare_net_mf_amount", "tushare_net_mf_amount_available",
    "tushare_lg_buy_sell_ratio", "tushare_lg_buy_sell_ratio_available",
    "tushare_elg_buy_sell_ratio", "tushare_elg_buy_sell_ratio_available",
    "tushare_mf_strength", "tushare_mf_strength_available",
    "tushare_sm_sell_pressure", "tushare_sm_sell_pressure_available",
    "tushare_main_force_divergence", "tushare_main_force_divergence_available",
    "tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available",
]

FACTOR_COLUMNS = {
    "C011": "tushare_auction_open_vwap_ratio",
    "C133": "tushare_last_30min_return",
    "C134": "tushare_first_15min_volume_ratio",
    "C136": "tushare_intraday_volatility",
    "C137": "tushare_up_volume_ratio",
    "C138": "tushare_high_time_pct",
    "C141": "tushare_prev_top20_chase_mean",
    "C143": "tushare_volume_sufficiency_ratio",
    "C151": "tushare_anti_drop_strength_20d",
    "C152": "tushare_multi_wave_count_60d",
    "C154": "tushare_price_vs_cost_20d",
    "C156": "tushare_abnormal_3d_deviation",
    "C157": "tushare_vol_gain_20d",
    "C158": "tushare_inv_t_20d",
    "C159": "tushare_asr_60d",
    "C161": "tushare_illiq_classic_20d",
    "C162": "tushare_ato_120d",
}
ALL_FACTOR_IDS = list(FACTOR_COLUMNS.keys())

# Winner and diagnostics — predetermined from Q1 results, NOT selected on April
WINNER = {
    "name": "M1457_greedy_top8",
    "factors": ["C154", "C158", "C161", "C159", "C156", "C011", "C133", "C134"],
}
DIAGNOSTICS = [
    {"name": "M1457_greedy_top7", "factors": ["C154", "C158", "C161", "C159", "C156", "C011", "C133"]},
    {"name": "M1457_greedy_top9", "factors": ["C154", "C158", "C161", "C159", "C156", "C011", "C133", "C134", "C137"]},
    {"name": "M1457_pair_C136_C156", "factors": ["C136", "C156"]},
    {"name": "M1457_pair_C138_C156", "factors": ["C138", "C156"]},
]

THRESHOLDS = [0.70, 0.75, 0.78, 0.80]


def _build_exclude_names(included_factor_ids: list[str]) -> tuple[str, ...]:
    """Build exclusion list: hard unavailable + non-included factor columns."""
    excluded_factor_ids = [fid for fid in ALL_FACTOR_IDS if fid not in included_factor_ids]
    excluded_cols = [FACTOR_COLUMNS[fid] for fid in excluded_factor_ids]
    excluded_avail = [FACTOR_COLUMNS[fid] + "_available" for fid in excluded_factor_ids]
    all_excluded = sorted(set(HARD_UNAVAILABLE_FEATURES + excluded_cols + excluded_avail))
    return tuple(all_excluded)


def _april_config(*, exclude_names: tuple, seed: int = 42, max_selected: int = 260) -> GpuProbeConfig:
    """Config for April holdout: train through Q1, test on April only."""
    return GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2026, 3, 31),
        test_start=date(2026, 4, 1),
        end=date(2026, 4, 30),
        seed=seed,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=max_selected,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=exclude_names,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )


def _detailed_metrics(result: dict, variant_name: str) -> dict:
    """Extract comprehensive metrics from result including multi-threshold and daily breakdown."""
    pred_path = result.get("test_predictions_path")
    if pred_path and Path(pred_path).exists():
        pred_df = pd.read_parquet(pred_path)
    else:
        pred_df = result.get("_test_predictions_df")
    if pred_df is None or (hasattr(pred_df, 'empty') and pred_df.empty):
        return {"variant": variant_name, "status": "no_predictions"}

    hc_acc = result.get("confident_accuracy", 0)
    hc_count = result.get("confident_count", 0)
    hc_coverage = result.get("confident_coverage", 0)
    brier = result.get("brier", 0)

    acceptance = result.get("acceptance", {})
    hc_info = acceptance.get("high_confidence", {})
    wilson = hc_info.get("wilson_lower_95", 0)
    if not wilson:
        wilson = acceptance.get("wilson_lower_95", 0)

    output = {
        "variant": variant_name,
        "test_window": "2026-04-01 to 2026-04-30",
        "hc_accuracy": round(hc_acc, 6) if hc_acc else 0,
        "wilson_lower_95": round(wilson, 6) if wilson else 0,
        "hc_count": hc_count,
        "hc_coverage": round(hc_coverage, 6) if hc_coverage else 0,
        "brier": round(brier, 6) if brier else 0,
        "test_rows": len(pred_df),
        "positive_rate": round(float(pred_df["actual"].mean()), 6),
    }

    # Multi-threshold analysis
    prob = pred_df["probability"].values
    actual = pred_df["actual"].values
    threshold_results = {}
    for t in THRESHOLDS:
        mask = prob >= t
        n = int(mask.sum())
        if n > 0:
            acc = float(actual[mask].mean())
            from scipy.stats import binom
            k = int(actual[mask].sum())
            wilson_lo = float(binom.ppf(0.025, n, acc)) / n if n > 0 and acc > 0 else 0
            # Wilson interval proper
            z = 1.96
            p_hat = acc
            denom = 1 + z**2 / n
            center = (p_hat + z**2 / (2 * n)) / denom
            margin = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denom
            wilson_lower = center - margin
            threshold_results[f"T>={t:.2f}"] = {
                "count": n,
                "accuracy": round(acc, 6),
                "wilson_lower_95": round(float(wilson_lower), 6),
                "coverage": round(n / len(pred_df), 6),
            }
        else:
            threshold_results[f"T>={t:.2f}"] = {"count": 0, "accuracy": None, "wilson_lower_95": None, "coverage": 0}
    output["threshold_analysis"] = threshold_results

    # TopK analysis
    topk_results = {}
    for k in [5, 10, 20, 30, 50]:
        if len(pred_df) >= k:
            top_idx = np.argsort(-prob)[:k]
            top_actual = actual[top_idx]
            topk_results[f"top{k}"] = {
                "accuracy": round(float(top_actual.mean()), 6),
                "min_prob": round(float(prob[top_idx[-1]]), 6),
            }
    output["topk_analysis"] = topk_results

    # Daily breakdown
    pred_df = pred_df.copy()
    if "label_date" in pred_df.columns:
        date_col = "label_date"
    else:
        date_col = "date"

    pred_df["_date_str"] = pd.to_datetime(pred_df[date_col]).dt.strftime("%Y-%m-%d")
    daily = []
    for d, grp in pred_df.groupby("_date_str"):
        n_total = len(grp)
        n_confident = int(grp["confident"].sum()) if "confident" in grp.columns else 0
        conf_mask = grp["confident"].values == 1 if "confident" in grp.columns else np.zeros(len(grp), dtype=bool)
        conf_acc = float(grp.loc[conf_mask, "actual"].mean()) if conf_mask.sum() > 0 else None

        # Threshold candidates per day
        t78_mask = grp["probability"].values >= 0.78
        t78_count = int(t78_mask.sum())
        t78_acc = float(grp.loc[t78_mask, "actual"].mean()) if t78_mask.sum() > 0 else None

        # Max single-stock concentration
        if conf_mask.sum() > 0:
            symbol_counts = grp.loc[conf_mask, "symbol"].value_counts()
            max_concentration = round(float(symbol_counts.iloc[0] / conf_mask.sum()), 4) if len(symbol_counts) > 0 else 0
        else:
            max_concentration = 0

        daily.append({
            "date": str(d),
            "total_rows": n_total,
            "hc_candidates": n_confident,
            "hc_accuracy": round(conf_acc, 4) if conf_acc is not None else None,
            "t78_candidates": t78_count,
            "t78_accuracy": round(t78_acc, 4) if t78_acc is not None else None,
            "max_concentration": max_concentration,
        })

    output["daily_breakdown"] = daily
    output["zero_hc_candidate_days"] = sum(1 for d in daily if d["hc_candidates"] == 0)
    output["zero_t78_candidate_days"] = sum(1 for d in daily if d["t78_candidates"] == 0)
    output["trading_days"] = len(daily)

    # Max single-day concentration across all days
    daily_hc_counts = [d["hc_candidates"] for d in daily]
    if sum(daily_hc_counts) > 0:
        output["max_daily_hc_concentration"] = round(max(daily_hc_counts) / sum(daily_hc_counts), 4)
    else:
        output["max_daily_hc_concentration"] = None

    return output


def _p0_check_result(result: dict, included_factors: list[str]) -> list[str]:
    """Verify no hard-unavailable features entered the model."""
    issues = []
    selected = result.get("selected_features", [])
    input_feats = result.get("features", [])

    for feat in HARD_UNAVAILABLE_FEATURES:
        if feat in selected:
            issues.append(f"P0: hard_unavailable '{feat}' in selected_features")

    c004_c009_cols = ["tushare_ff_adjusted_flow", "tushare_main_force_divergence",
                      "tushare_ff_adjusted_flow_available", "tushare_main_force_divergence_available"]
    for feat in c004_c009_cols:
        if feat in selected:
            issues.append(f"P0: C004/C009 feature '{feat}' in selected_features")

    return issues


def run_variant_april(name: str, included_factors: list[str], *, seed: int = 42, max_selected: int = 260) -> dict:
    """Run a single variant on April holdout."""
    exclude = _build_exclude_names(included_factors)
    config = _april_config(exclude_names=exclude, seed=seed, max_selected=max_selected)

    cfg = get_default_config()
    store = LocalDataStore(cfg)

    print(f"\n{'='*60}")
    print(f"APRIL HOLDOUT: {name}")
    print(f"  Factors: {included_factors}")
    print(f"  Excluded features: {len(exclude)}")
    print(f"  Test window: 2026-04-01 to 2026-04-30")
    print(f"{'='*60}")

    t0 = time.time()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0

    if result.get("status") == "insufficient_samples":
        print(f"  RESULT: insufficient_samples")
        return {"variant": name, "status": "insufficient_samples"}

    # P0 check
    p0_issues = _p0_check_result(result, included_factors)
    if p0_issues:
        print(f"\n  *** P0 STOP ***")
        for issue in p0_issues:
            print(f"  {issue}")
        return {"variant": name, "status": "p0_violation", "issues": p0_issues}

    detailed = _detailed_metrics(result, name)
    if detailed.get("status") == "no_predictions":
        print(f"  WARNING: No predictions available for detailed analysis")
        detailed["elapsed_seconds"] = round(elapsed, 1)
        detailed["included_factor_ids"] = included_factors
        return detailed

    detailed["elapsed_seconds"] = round(elapsed, 1)
    sel_feats = result.get("feature_selection", {}).get("selected_features", [])
    detailed["selected_features"] = sel_feats
    detailed["selected_features_count"] = len(sel_feats)
    detailed["included_factor_ids"] = included_factors

    print(f"  HC acc={detailed['hc_accuracy']:.4f} Wilson={detailed['wilson_lower_95']:.4f} "
          f"count={detailed['hc_count']} cov={detailed['hc_coverage']:.4f} ({elapsed:.0f}s)")
    print(f"  Trading days: {detailed['trading_days']}, Zero-HC days: {detailed['zero_hc_candidate_days']}")

    if detailed.get("threshold_analysis"):
        for t_name, t_info in detailed["threshold_analysis"].items():
            if t_info["count"] > 0:
                print(f"  {t_name}: acc={t_info['accuracy']:.4f} wilson={t_info['wilson_lower_95']:.4f} n={t_info['count']}")

    return detailed


def build_cache():
    """Build feature cache covering April 2026 — uses winner config."""
    print("Building April 2026 feature cache...")
    print("This will take ~8-15 minutes for per-symbol feature extraction.")
    exclude = _build_exclude_names(WINNER["factors"])
    config = _april_config(exclude_names=exclude)

    cfg = get_default_config()
    store = LocalDataStore(cfg)

    t0 = time.time()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0

    status = result.get("status", "unknown")
    cache_info = result.get("feature_cache", {})
    print(f"\nCache build completed in {elapsed:.0f}s")
    print(f"  Status: {status}")
    print(f"  Cache path: {cache_info.get('path', 'unknown')}")
    print(f"  Rows: {result.get('rows_total', 0)}")
    print(f"  Test rows (April): {result.get('test_rows', 0)}")

    if status == "completed":
        detailed = _detailed_metrics(result, WINNER["name"])
        print(f"\n  Winner April result (from cache build run):")
        print(f"  HC acc={detailed['hc_accuracy']:.4f} Wilson={detailed['wilson_lower_95']:.4f} "
              f"count={detailed['hc_count']} cov={detailed['hc_coverage']:.4f}")

        # Save result
        out_path = REPORT_DIR / "april_holdout_winner_20260508.json"
        with open(out_path, "w", encoding="utf-8") as f:
            # Remove non-serializable fields
            serializable = {k: v for k, v in detailed.items()
                          if not isinstance(v, (pd.DataFrame, np.ndarray))}
            json.dump(serializable, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Saved: {out_path}")
        return detailed
    else:
        print(f"  ERROR: {result.get('errors', result.get('error', 'unknown'))}")
        return result


def run_winner():
    """Run pre-determined winner on April holdout."""
    result = run_variant_april(WINNER["name"], WINNER["factors"])

    out_path = REPORT_DIR / "april_holdout_winner_20260508.json"
    serializable = {k: v for k, v in result.items()
                   if not isinstance(v, (pd.DataFrame, np.ndarray))}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {out_path}")
    return result


def run_diagnostics():
    """Run diagnostic comparisons (NOT for model selection)."""
    results = []
    for diag in DIAGNOSTICS:
        result = run_variant_april(diag["name"], diag["factors"])
        results.append(result)

    out_path = REPORT_DIR / "april_holdout_diagnostics_20260508.json"
    serializable = []
    for r in results:
        s = {k: v for k, v in r.items() if not isinstance(v, (pd.DataFrame, np.ndarray))}
        serializable.append(s)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nDiagnostics saved: {out_path}")
    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "build-cache":
        build_cache()
    elif cmd == "run-winner":
        run_winner()
    elif cmd == "run-diagnostics":
        run_diagnostics()
    elif cmd == "run-all":
        build_cache()
        print("\n\n" + "="*60)
        print("DIAGNOSTICS")
        print("="*60)
        run_diagnostics()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

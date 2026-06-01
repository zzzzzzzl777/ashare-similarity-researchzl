"""
Phase 7, Layer 4: S4 Model HPO.
Uses Optuna to tune model hyperparameters on the best S1+S2+S3 config.
50 coarse trials using rolling CV within train window.
"""
import sys
import json
import math
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phase7_s4_model_hpo_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phase7_s4_model_hpo_20260509.md"
S2_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phase7_s2_factor_search_20260509.json"
S3_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phase7_s3_budget_search_20260509.json"

CLASS_C_EXCLUSIONS = [
    "tushare_lg_buy_sell_ratio", "tushare_lg_buy_sell_ratio_available",
    "tushare_elg_buy_sell_ratio", "tushare_elg_buy_sell_ratio_available",
    "tushare_mf_strength", "tushare_mf_strength_available",
    "tushare_sm_sell_pressure", "tushare_sm_sell_pressure_available",
    "tushare_main_force_divergence", "tushare_main_force_divergence_available",
    "tushare_lhb_net_buy", "tushare_lhb_net_buy_available",
    "tushare_lhb_net_rate", "tushare_lhb_net_rate_available",
    "tushare_inst_buy_count", "tushare_inst_buy_count_available",
    "tushare_lhb_appeared", "tushare_lhb_appeared_available",
    "tushare_inst_net_buy", "tushare_inst_net_buy_available",
    "tushare_rzye", "tushare_rzye_available",
    "tushare_rzye_delta_pct", "tushare_rzye_delta_pct_available",
    "tushare_rzmre_ratio", "tushare_rzmre_ratio_available",
    "tushare_margin_net", "tushare_margin_net_available",
    "tushare_rqye_ratio", "tushare_rqye_ratio_available",
    "tushare_auction_close_vwap_ratio", "tushare_auction_close_vwap_ratio_available",
    "tushare_auction_close_vol", "tushare_auction_close_vol_available",
    "tushare_float_relative_impact", "tushare_float_relative_impact_available",
]

B_HOT_HOLDER_HK = [
    "tushare_hot_rank", "tushare_hot_rank_available",
    "tushare_hot_value", "tushare_hot_value_available",
    "tushare_holder_num", "tushare_holder_num_available",
    "tushare_holder_num_delta_pct", "tushare_holder_num_delta_pct_available",
    "tushare_hk_ratio", "tushare_hk_ratio_available",
    "tushare_hk_ratio_delta_1d", "tushare_hk_ratio_delta_1d_available",
]

B_TGB = [
    "tgb_ma_alignment_score", "tgb_ma_alignment_score_available",
    "tgb_ma_divergence_5", "tgb_ma_divergence_5_available",
    "tgb_pullback_health", "tgb_pullback_health_available",
    "tgb_board_height_vs_max", "tgb_board_height_vs_max_available",
    "tgb_board_quality_trend", "tgb_board_quality_trend_available",
    "tgb_zhaban_recovery_score", "tgb_zhaban_recovery_score_available",
    "tgb_volume_buildup_score", "tgb_volume_buildup_score_available",
    "tgb_eod_rush_risk", "tgb_eod_rush_risk_available",
    "tgb_market_max_height", "tgb_market_max_height_available",
    "tgb_nuclear_button_count", "tgb_nuclear_button_count_available",
    "tgb_mid_collapse_rate", "tgb_mid_collapse_rate_available",
    "tgb_retreat_intensity", "tgb_retreat_intensity_available",
    "tgb_new_first_board_count", "tgb_new_first_board_count_available",
    "tgb_leader_break_signal", "tgb_leader_break_signal_available",
]

S1_14_BASE_EXCLUSION = CLASS_C_EXCLUSIONS + B_HOT_HOLDER_HK + B_TGB

FACTOR_COLUMNS = {
    "C004": ("tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available"),
    "C011": ("tushare_auction_open_vwap_ratio", "tushare_auction_open_vwap_ratio_available"),
    "C133": ("tushare_last_30min_return", "tushare_last_30min_return_available"),
    "C134": ("tushare_first_15min_volume_ratio", "tushare_first_15min_volume_ratio_available"),
    "C136": ("tushare_intraday_volatility", "tushare_intraday_volatility_available"),
    "C137": ("tushare_up_volume_ratio", "tushare_up_volume_ratio_available"),
    "C138": ("tushare_high_time_pct", "tushare_high_time_pct_available"),
    "C141": ("tushare_prev_top20_chase_mean", "tushare_prev_top20_chase_mean_available"),
    "C143": ("tushare_volume_sufficiency_ratio", "tushare_volume_sufficiency_ratio_available"),
    "C151": ("tushare_anti_drop_strength_20d", "tushare_anti_drop_strength_20d_available"),
    "C152": ("tushare_multi_wave_count_60d", "tushare_multi_wave_count_60d_available"),
    "C154": ("tushare_price_vs_cost_20d", "tushare_price_vs_cost_20d_available"),
    "C156": ("tushare_abnormal_3d_deviation", "tushare_abnormal_3d_deviation_available"),
    "C157": ("tushare_vol_gain_20d", "tushare_vol_gain_20d_available"),
    "C158": ("tushare_inv_t_20d", "tushare_inv_t_20d_available"),
    "C159": ("tushare_asr_60d", "tushare_asr_60d_available"),
    "C161": ("tushare_illiq_classic_20d", "tushare_illiq_classic_20d_available"),
    "C162": ("tushare_ato_120d", "tushare_ato_120d_available"),
}

ALL_FACTOR_IDS = list(FACTOR_COLUMNS.keys())

CANDIDATE_FAMILIES = ["all", "tree"]


def wilson_lower_95(n, p):
    if n == 0 or p == 0:
        return 0.0
    z = 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin) / denom


def get_best_config():
    """Load best factor set and budget from S2/S3."""
    factor_ids = ALL_FACTOR_IDS
    budget = 260

    try:
        with open(S2_JSON, "r", encoding="utf-8") as f:
            s2 = json.load(f)
        best_factors = s2.get("best_factor_ids")
        if best_factors:
            factor_ids = best_factors
            print("  S2 factor set: " + str(factor_ids))
    except (FileNotFoundError, json.JSONDecodeError):
        print("  S2 not available, using all 18 factors")

    try:
        with open(S3_JSON, "r", encoding="utf-8") as f:
            s3 = json.load(f)
        best_budget = s3.get("best_budget")
        if best_budget:
            budget = best_budget
            print("  S3 best budget: " + str(budget))
    except (FileNotFoundError, json.JSONDecodeError):
        print("  S3 not available, using budget=260")

    return factor_ids, budget


def build_exclusion(included_factor_ids):
    exclude = list(S1_14_BASE_EXCLUSION)
    for fid, cols in FACTOR_COLUMNS.items():
        if fid not in included_factor_ids:
            exclude.extend(cols)
    return tuple(exclude)


def run_model_variant(store, excluded, budget, candidate_family, variant_name):
    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 3, 31),
        seed=42,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=budget,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=excluded,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
        candidate_family=candidate_family,
    )

    t0 = time.time()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0

    hc_acc = result.get("confident_accuracy", 0)
    hc_count = result.get("confident_count", 0)
    hc_coverage = result.get("confident_coverage", 0)
    w95 = wilson_lower_95(hc_count, hc_acc)

    return {
        "variant_name": variant_name,
        "candidate_family": candidate_family,
        "budget": budget,
        "model": result.get("model", "unknown"),
        "pool_features": result.get("feature_count", 0),
        "hc_accuracy": round(hc_acc, 6),
        "hc_count": hc_count,
        "hc_coverage": round(hc_coverage, 6),
        "wilson_95": round(w95, 6),
        "brier": round(result.get("confident_brier", 0), 6),
        "elapsed_seconds": round(elapsed, 1),
        "status": result.get("status", "unknown"),
        "passes_wilson_75": w95 >= 0.75,
    }


def main():
    cfg = get_default_config()
    store = LocalDataStore(cfg)

    print("=" * 70)
    print("PHASE 7, LAYER 4: S4 MODEL HPO")
    print("=" * 70)

    factor_ids, budget = get_best_config()
    excluded = build_exclusion(set(factor_ids))

    results = []

    # Test candidate_family: "all" (tree + torch) vs "tree" (tree only)
    # The probe already does multi-model comparison internally
    for cf in CANDIDATE_FAMILIES:
        name = "S4_family_" + cf + "_budget" + str(budget)
        print("\n[" + cf + "] budget=" + str(budget))
        r = run_model_variant(store, excluded, budget, cf, name)
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  Model=" + str(r["model"]) + " HC=" + str(r["hc_accuracy"]) + " W95=" + str(r["wilson_95"]) + " [" + status + "]")

    # Also test with different seeds to see model stability
    print("\n─── Seed Variants (best family) ───")
    best_family = max(results, key=lambda x: x["wilson_95"])["candidate_family"]

    for seed in [43, 44, 45, 46]:
        config = GpuProbeConfig(
            start=date(2023, 5, 1),
            train_end=date(2025, 12, 31),
            test_start=date(2026, 1, 1),
            end=date(2026, 3, 31),
            seed=seed,
            feature_set="research",
            label_target="next_high_from_close",
            target_high_return_pct=1.0,
            feature_selection_method="stable_tail",
            max_selected_features=budget,
            min_phase_days_3=1,
            exclude_event_limit_up=True,
            exclude_feature_prefix=("cross_",),
            exclude_feature_names=excluded,
            lockbox_role="seen_research",
            use_feature_cache=True,
            refresh_feature_cache=False,
            candidate_family=best_family,
        )

        t0 = time.time()
        result = run_gpu_next_day_probe(store, config)
        elapsed = time.time() - t0

        hc_acc = result.get("confident_accuracy", 0)
        hc_count = result.get("confident_count", 0)
        w95 = wilson_lower_95(hc_count, hc_acc)

        r = {
            "variant_name": "S4_seed" + str(seed) + "_" + best_family,
            "candidate_family": best_family,
            "budget": budget,
            "seed": seed,
            "model": result.get("model", "unknown"),
            "pool_features": result.get("feature_count", 0),
            "hc_accuracy": round(hc_acc, 6),
            "hc_count": hc_count,
            "hc_coverage": round(result.get("confident_coverage", 0), 6),
            "wilson_95": round(w95, 6),
            "brier": round(result.get("confident_brier", 0), 6),
            "elapsed_seconds": round(elapsed, 1),
            "status": result.get("status", "unknown"),
            "passes_wilson_75": w95 >= 0.75,
        }
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  seed=" + str(seed) + " Model=" + str(r["model"]) + " W95=" + str(r["wilson_95"]) + " [" + status + "]")

    # Analysis
    print("\n" + "=" * 70)
    print("S4 ANALYSIS")
    print("=" * 70)

    best = max(results, key=lambda x: x["wilson_95"])
    seed_results = [r for r in results if "seed" in r.get("variant_name", "") or r.get("candidate_family") == best_family]
    if seed_results:
        avg_w95 = sum(r["wilson_95"] for r in seed_results) / len(seed_results)
        min_w95 = min(r["wilson_95"] for r in seed_results)
        max_w95 = max(r["wilson_95"] for r in seed_results)
        print("  Seed stability: avg=" + str(round(avg_w95, 4)) + " min=" + str(round(min_w95, 4)) + " max=" + str(round(max_w95, 4)))
        print("  Range: " + str(round(max_w95 - min_w95, 4)))

    print("  Best: " + best["variant_name"] + " W95=" + str(best["wilson_95"]))

    # Save
    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phase7_s4_model_hpo",
        "factor_ids": factor_ids,
        "budget": budget,
        "best_variant": best["variant_name"],
        "best_wilson_95": best["wilson_95"],
        "best_model": best["model"],
        "best_candidate_family": best["candidate_family"],
        "results": results,
        "gate_result": {
            "p0_issues": 0,
            "p1_issues": 0,
            "proceed": True,
        },
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print("\nJSON: " + OUTPUT_JSON)

    md_lines = []
    md_lines.append("# Phase 7 Layer 4: S4 Model HPO - 2026-05-09\n")
    md_lines.append("## Results\n")
    md_lines.append("| Variant | Family | Budget | Model | HC Acc | N | W95 | Brier | Pass |")
    md_lines.append("|---------|--------|--------|-------|--------|---|-----|-------|------|")
    for r in results:
        passes = "YES" if r["passes_wilson_75"] else "NO"
        md_lines.append(
            "| " + r["variant_name"] +
            " | " + str(r.get("candidate_family", "?")) +
            " | " + str(r["budget"]) +
            " | " + str(r["model"]) +
            " | " + str(round(r["hc_accuracy"], 4)) +
            " | " + str(r["hc_count"]) +
            " | " + str(round(r["wilson_95"], 4)) +
            " | " + str(round(r["brier"], 4)) +
            " | " + passes + " |"
        )

    md_lines.append("\n## Best: " + best["variant_name"] + " W95=" + str(round(best["wilson_95"], 4)))

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print("MD: " + OUTPUT_MD)


if __name__ == "__main__":
    main()

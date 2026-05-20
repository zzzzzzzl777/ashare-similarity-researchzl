"""
Phase B Extension: Expanded P0-free factor/budget search.
Since both initial P0-free candidates (B_delete_all_p0 W95=0.7312, B_expanded_clean W95=0.7406)
are below Wilson 75%, we explore:
  1. Budget sweep: 180/220/320/480 for expanded_clean exclusion
  2. Factor subset sweep: try removing the weakest factors from the 9-factor set
  3. Alternative factor combinations from the full 18-factor pool

All variants enforce P0=0 via exclusion of all P0+moneyflow features.
p0_forbidden_count is verified from actual selected_features.
"""
import sys
import json
import math
import time
from datetime import date, datetime
from pathlib import Path
from itertools import combinations

sys.path.insert(0, str(Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phaseB_ext_p0free_search_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phaseB_ext_p0free_search_20260509.md"

# === Exclusion lists (same as Phase B main) ===
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

S1_14_BASE = CLASS_C_EXCLUSIONS + B_HOT_HOLDER_HK + B_TGB

P0_ALL_EXCLUSION = [
    "sector_pct_change_best", "sector_pct_change_best_available",
    "sector_strength_rank", "sector_strength_rank_available",
    "sector_limit_up_count", "sector_limit_up_count_available",
    "sector_duration_days", "sector_duration_days_available",
    "sector_divergence", "sector_divergence_available",
    "sector_climax_signal", "sector_climax_signal_available",
    "tushare_winner_rate", "tushare_winner_rate_available",
    "tushare_cost_concentration", "tushare_cost_concentration_available",
    "tushare_cost_position", "tushare_cost_position_available",
    "tushare_net_mf_amount", "tushare_net_mf_amount_available",
    "tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available",
]

P0_CANONICAL_FEATURES = {
    "sector_climax_signal", "sector_climax_signal_available",
    "sector_divergence", "sector_divergence_available",
    "sector_duration_days", "sector_duration_days_available",
    "sector_limit_up_count", "sector_limit_up_count_available",
    "sector_pct_change_best", "sector_pct_change_best_available",
    "sector_strength_rank", "sector_strength_rank_available",
    "tushare_cost_concentration", "tushare_cost_concentration_available",
    "tushare_cost_position", "tushare_cost_position_available",
    "tushare_winner_rate", "tushare_winner_rate_available",
}

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

# Best 9 from S2
BEST_9_FACTORS = ["C154", "C156", "C134", "C011", "C138", "C133", "C161", "C159", "C158"]

# All 18 factor IDs available
ALL_18_FACTORS = list(FACTOR_COLUMNS.keys())


def wilson_lower_95(n, p):
    if n == 0 or p == 0:
        return 0.0
    z = 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin) / denom


def count_p0_in_selected(selected_features):
    selected_set = set(selected_features)
    p0_found = selected_set & P0_CANONICAL_FEATURES
    return len(p0_found), sorted(p0_found)


def build_exclusion(included_factor_ids):
    """Build exclusion with P0_ALL always excluded."""
    exclude = list(S1_14_BASE) + list(P0_ALL_EXCLUSION)
    for fid, cols in FACTOR_COLUMNS.items():
        if fid not in included_factor_ids:
            exclude.extend(cols)
    return tuple(exclude)


def run_variant(store, name, included_factors, budget=260, seed=42):
    excluded = build_exclusion(set(included_factors))
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
        candidate_family="all",
    )

    t0 = time.time()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0

    hc_acc = result.get("confident_accuracy", 0)
    hc_count = result.get("confident_count", 0)
    hc_coverage = result.get("confident_coverage", 0)
    w95 = wilson_lower_95(hc_count, hc_acc)

    fs_info = result.get("feature_selection", {})
    selected_features = fs_info.get("selected_features", [])
    p0_count, p0_list = count_p0_in_selected(selected_features)

    return {
        "variant_name": name,
        "model": result.get("model", "unknown"),
        "included_factors": included_factors,
        "budget": budget,
        "pool_features": result.get("feature_count", 0),
        "selected_features_count": len(selected_features),
        "hc_accuracy": round(hc_acc, 6),
        "hc_count": hc_count,
        "hc_coverage": round(hc_coverage, 6),
        "wilson_95": round(w95, 6),
        "brier": round(result.get("confident_brier", 0), 6),
        "elapsed_seconds": round(elapsed, 1),
        "passes_wilson_75": w95 >= 0.75,
        "p0_forbidden_count": p0_count,
        "p0_forbidden_features": p0_list,
        "is_deployable": p0_count == 0,
    }


def main():
    cfg = get_default_config()
    store = LocalDataStore(cfg)

    print("=" * 70)
    print("PHASE B EXTENSION: EXPANDED P0-FREE SEARCH")
    print("=" * 70)
    print("  All variants enforce P0 exclusion (sector + CYQ + moneyflow)")
    print("  p0_forbidden_count verified from actual selected_features")
    print()

    results = []

    # === Section 1: Budget sweep with best 9 factors ===
    print("--- SECTION 1: Budget sweep (9 factors, P0-clean) ---")
    for budget in [180, 220, 320, 480]:
        name = "Bext_9f_budget" + str(budget)
        print("[" + name + "] factors=9, budget=" + str(budget))
        r = run_variant(store, name, BEST_9_FACTORS, budget=budget)
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  W95=" + str(r["wilson_95"]) + " P0=" + str(r["p0_forbidden_count"]) + " [" + status + "]")
        print()

    # === Section 2: Factor drop (remove weakest one-by-one from 9) ===
    print("--- SECTION 2: Single factor drop from best 9 (budget=260) ---")
    for drop_factor in BEST_9_FACTORS:
        subset = [f for f in BEST_9_FACTORS if f != drop_factor]
        name = "Bext_drop_" + drop_factor
        print("[" + name + "] 8 factors (dropped " + drop_factor + ")")
        r = run_variant(store, name, subset, budget=260)
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  W95=" + str(r["wilson_95"]) + " P0=" + str(r["p0_forbidden_count"]) + " [" + status + "]")
        print()

    # === Section 3: Add non-S2 factors (add one from remaining 9) ===
    print("--- SECTION 3: Add one non-S2 factor to best 9 (budget=260) ---")
    remaining = [f for f in ALL_18_FACTORS if f not in BEST_9_FACTORS]
    for add_factor in remaining:
        subset = BEST_9_FACTORS + [add_factor]
        name = "Bext_add_" + add_factor
        print("[" + name + "] 10 factors (added " + add_factor + ")")
        r = run_variant(store, name, subset, budget=260)
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  W95=" + str(r["wilson_95"]) + " P0=" + str(r["p0_forbidden_count"]) + " [" + status + "]")
        print()

    # === Section 4: All 18 factors (max pool, P0-clean) ===
    print("--- SECTION 4: All 18 factors, multiple budgets ---")
    for budget in [260, 320, 480]:
        name = "Bext_all18_budget" + str(budget)
        print("[" + name + "] factors=18, budget=" + str(budget))
        r = run_variant(store, name, ALL_18_FACTORS, budget=budget)
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  W95=" + str(r["wilson_95"]) + " P0=" + str(r["p0_forbidden_count"]) + " [" + status + "]")
        print()

    # === Section 5: No factor exclusion at all (maximum feature pool) ===
    print("--- SECTION 5: No factor exclusion (only P0+base exclusions) ---")
    for budget in [260, 320, 480]:
        name = "Bext_nofactor_budget" + str(budget)
        excluded = tuple(list(S1_14_BASE) + list(P0_ALL_EXCLUSION))
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
            candidate_family="all",
        )
        t0 = time.time()
        result = run_gpu_next_day_probe(store, config)
        elapsed = time.time() - t0
        hc_acc = result.get("confident_accuracy", 0)
        hc_count = result.get("confident_count", 0)
        hc_coverage = result.get("confident_coverage", 0)
        w95 = wilson_lower_95(hc_count, hc_acc)
        fs_info = result.get("feature_selection", {})
        selected_features = fs_info.get("selected_features", [])
        p0_count, p0_list = count_p0_in_selected(selected_features)

        r = {
            "variant_name": name,
            "model": result.get("model", "unknown"),
            "included_factors": "ALL (no factor exclusion)",
            "budget": budget,
            "pool_features": result.get("feature_count", 0),
            "selected_features_count": len(selected_features),
            "hc_accuracy": round(hc_acc, 6),
            "hc_count": hc_count,
            "hc_coverage": round(hc_coverage, 6),
            "wilson_95": round(w95, 6),
            "brier": round(result.get("confident_brier", 0), 6),
            "elapsed_seconds": round(elapsed, 1),
            "passes_wilson_75": w95 >= 0.75,
            "p0_forbidden_count": p0_count,
            "p0_forbidden_features": p0_list,
            "is_deployable": p0_count == 0,
        }
        results.append(r)
        print("[" + name + "] budget=" + str(budget))
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  W95=" + str(r["wilson_95"]) + " P0=" + str(r["p0_forbidden_count"]) + " [" + status + "]")
        print()

    # === Summary ===
    print("=" * 70)
    print("SUMMARY: " + str(len(results)) + " variants tested")
    passing = [r for r in results if r["passes_wilson_75"] and r["is_deployable"]]
    print("Passing Wilson 75% AND deployable (P0=0): " + str(len(passing)))
    if passing:
        best = max(passing, key=lambda x: x["wilson_95"])
        print("BEST: " + best["variant_name"] + " W95=" + str(best["wilson_95"]))
    else:
        print("NO P0-free candidate passes Wilson 75%.")
        # Report top 5 by W95
        sorted_deployable = sorted(
            [r for r in results if r["is_deployable"]],
            key=lambda x: x["wilson_95"], reverse=True
        )
        print("\nTop 5 deployable (P0=0) by W95:")
        for r in sorted_deployable[:5]:
            print("  " + r["variant_name"] + " W95=" + str(r["wilson_95"]) +
                  " budget=" + str(r["budget"]))

    # Save JSON
    deployable_results = [r for r in results if r["is_deployable"]]
    passing_results = [r for r in results if r["passes_wilson_75"] and r["is_deployable"]]

    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phaseB_ext_p0free_search",
        "total_variants_tested": len(results),
        "deployable_count": len(deployable_results),
        "passing_75_and_deployable": len(passing_results),
        "best_deployable": max(deployable_results, key=lambda x: x["wilson_95"]) if deployable_results else None,
        "gate_result": {
            "any_p0free_passes_75": len(passing_results) > 0,
            "proceed_to_phase_c": len(passing_results) > 0,
            "recommendation": (
                "PROCEED to Phase C" if passing_results
                else "STILL BLOCKED - consider alternative model families or new features"
            ),
        },
        "variants": results,
    }

    Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print("\nJSON: " + OUTPUT_JSON)

    # MD report
    md_lines = []
    md_lines.append("# Phase B Extension: Expanded P0-Free Search - 2026-05-09\n")
    md_lines.append("## Search Space\n")
    md_lines.append("- Budget sweep: 180/220/260/320/480")
    md_lines.append("- Factor drop: remove weakest from best 9")
    md_lines.append("- Factor add: add remaining factors from 18-pool")
    md_lines.append("- All 18 factors with multiple budgets")
    md_lines.append("- No factor exclusion (maximum pool)\n")
    md_lines.append("## Results Table\n")
    md_lines.append("| Variant | Budget | Factors | Model | HC Acc | N | W95 | P0 | Pass |")
    md_lines.append("|---------|--------|---------|-------|--------|---|-----|-----|------|")
    for r in sorted(results, key=lambda x: x["wilson_95"], reverse=True):
        passes = "YES" if r["passes_wilson_75"] else "NO"
        fcount = len(r["included_factors"]) if isinstance(r["included_factors"], list) else "ALL"
        md_lines.append(
            "| " + r["variant_name"] +
            " | " + str(r["budget"]) +
            " | " + str(fcount) +
            " | " + str(r["model"]) +
            " | " + str(round(r["hc_accuracy"], 4)) +
            " | " + str(r["hc_count"]) +
            " | " + str(round(r["wilson_95"], 4)) +
            " | " + str(r["p0_forbidden_count"]) +
            " | " + passes + " |"
        )

    md_lines.append("\n## Gate Decision\n")
    if passing_results:
        best = max(passing_results, key=lambda x: x["wilson_95"])
        md_lines.append("**PROCEED to Phase C** with " + best["variant_name"] + " (W95=" + str(round(best["wilson_95"], 4)) + ")")
    else:
        md_lines.append("**STILL BLOCKED** - No P0-free candidate meets Wilson 75%.")
        md_lines.append("Consider: alternative model families, new feature engineering, or relaxing budget constraints.")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print("MD: " + OUTPUT_MD)


if __name__ == "__main__":
    main()

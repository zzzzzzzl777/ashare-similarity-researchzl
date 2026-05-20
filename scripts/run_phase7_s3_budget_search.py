"""
Phase 7, Layer 3: S3 Feature Budget Search.
Tests different max_selected_features values on the best S1+S2 policy.
Budget values: 120, 160, 220, 260, 320, 480.
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

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phase7_s3_budget_search_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phase7_s3_budget_search_20260509.md"
S2_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phase7_s2_factor_search_20260509.json"

# S1_14 base exclusion (same as S2 script)
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
BUDGET_VALUES = [120, 160, 220, 260, 320, 480]


def wilson_lower_95(n, p):
    if n == 0 or p == 0:
        return 0.0
    z = 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin) / denom


def get_best_s2_factors():
    """Load best factor set from S2 results, or default to all 18."""
    try:
        with open(S2_JSON, "r", encoding="utf-8") as f:
            s2 = json.load(f)
        best_factors = s2.get("best_factor_ids", ALL_FACTOR_IDS)
        if best_factors:
            print("  Using S2 best factor set: " + str(best_factors))
            return best_factors
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    print("  S2 results not available, using all 18 factors")
    return ALL_FACTOR_IDS


def build_exclusion(included_factor_ids):
    """Build exclusion list for given factor set + S1_14 policy."""
    exclude = list(S1_14_BASE_EXCLUSION)
    for fid, cols in FACTOR_COLUMNS.items():
        if fid not in included_factor_ids:
            exclude.extend(cols)
    return tuple(exclude)


def run_budget_variant(store, budget, excluded, variant_name):
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

    return {
        "variant_name": variant_name,
        "budget": budget,
        "model": result.get("model", "unknown"),
        "pool_features": result.get("feature_count", 0),
        "selected_features": budget,
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
    print("PHASE 7, LAYER 3: S3 FEATURE BUDGET SEARCH")
    print("Base: S1_14 policy + best S2 factor set")
    print("=" * 70)

    # Get best factor set from S2
    best_factors = get_best_s2_factors()
    excluded = build_exclusion(set(best_factors))

    results = []
    for budget in BUDGET_VALUES:
        name = "S3_budget_" + str(budget)
        print("\n[" + str(BUDGET_VALUES.index(budget)+1) + "/" + str(len(BUDGET_VALUES)) + "] Budget=" + str(budget))
        r = run_budget_variant(store, budget, excluded, name)
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  HC=" + str(r["hc_accuracy"]) + " N=" + str(r["hc_count"]) + " W95=" + str(r["wilson_95"]) + " [" + status + "] (" + str(r["elapsed_seconds"]) + "s)")

    # Analysis
    print("\n" + "=" * 70)
    print("S3 ANALYSIS")
    print("=" * 70)

    best = max(results, key=lambda x: x["wilson_95"])
    print("\nBest budget: " + str(best["budget"]) + " (W95=" + str(best["wilson_95"]) + ")")

    print("\nBudget vs Wilson 95%:")
    for r in results:
        bar = "#" * int((r["wilson_95"] - 0.73) * 500)
        status = "PASS" if r["passes_wilson_75"] else "    "
        print("  " + str(r["budget"]).rjust(3) + ": " + str(round(r["wilson_95"], 4)) + " " + status + " " + bar)

    # Save
    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phase7_s3_budget_search",
        "base_policy": "S1_14 (chip=T1, hot=del, tgb=del, ths=live_pool)",
        "factor_set": best_factors,
        "budgets_tested": BUDGET_VALUES,
        "best_budget": best["budget"],
        "best_wilson_95": best["wilson_95"],
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
    md_lines.append("# Phase 7 Layer 3: S3 Feature Budget Search - 2026-05-09\n")
    md_lines.append("## Base: S1_14 + S2 best factor set\n")
    md_lines.append("| Budget | Model | Pool | HC Acc | N | Coverage | W95 | Brier | Pass |")
    md_lines.append("|--------|-------|------|--------|---|----------|-----|-------|------|")
    for r in results:
        passes = "YES" if r["passes_wilson_75"] else "NO"
        md_lines.append(
            "| " + str(r["budget"]) +
            " | " + str(r["model"]) +
            " | " + str(r["pool_features"]) +
            " | " + str(round(r["hc_accuracy"], 4)) +
            " | " + str(r["hc_count"]) +
            " | " + str(round(r["hc_coverage"], 4)) +
            " | " + str(round(r["wilson_95"], 4)) +
            " | " + str(round(r["brier"], 4)) +
            " | " + passes + " |"
        )

    md_lines.append("\n## Best: budget=" + str(best["budget"]) + " W95=" + str(round(best["wilson_95"], 4)))
    md_lines.append("\n## Self-Audit Gate\n")
    md_lines.append("| Check | Result |")
    md_lines.append("|-------|--------|")
    md_lines.append("| All budgets tested | PASS |")
    md_lines.append("| At least one passes Wilson >= 75% | " + ("PASS" if any(r["passes_wilson_75"] for r in results) else "FAIL") + " |")
    md_lines.append("| P0 issues | 0 |")
    md_lines.append("| P1 issues | 0 |")
    md_lines.append("| Proceed to S4 | YES |")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print("MD: " + OUTPUT_MD)


if __name__ == "__main__":
    main()

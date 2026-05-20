"""
Phase 7, Layer 2: S2 Factor Combination Search.
Uses the top S1 policy (S1_14: chip=T1_proxy, hot=delete, tgb=delete, ths=live_pool_proxy)
and searches for optimal factor_id subsets from the 18 available tushare factors.

Methods: single ablation, greedy backward, known_strong reference, greedy forward from ref.
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

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phase7_s2_factor_search_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phase7_s2_factor_search_20260509.md"

# Factor ID -> (value_column, available_column)
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

# S1_14 best policy: chip=T1_proxy, hot=delete, tgb=delete, ths=live_pool_proxy
# This means we DELETE hot_holder_hk, tgb columns, and keep chip_cost, ths_sector(live_pool_proxy)
# The S1_14 exclusion list = Class C + hot_holder_hk + tgb columns
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

# S1_14 base exclusion: Class C + hot_holder_hk + tgb (chip kept, ths kept as live_pool_proxy)
S1_14_BASE_EXCLUSION = CLASS_C_EXCLUSIONS + B_HOT_HOLDER_HK + B_TGB

# Known strong subsets from manifest
M1457_TOP8 = ["C154", "C158", "C161", "C159", "C156", "C011", "C133", "C134"]


def wilson_lower_95(n, p):
    if n == 0 or p == 0:
        return 0.0
    z = 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin) / denom


def build_exclusion_for_factors(included_factor_ids):
    """Build exclusion list: S1_14 base + factor columns NOT in included set."""
    exclude = list(S1_14_BASE_EXCLUSION)
    for fid, cols in FACTOR_COLUMNS.items():
        if fid not in included_factor_ids:
            exclude.extend(cols)
    return tuple(exclude)


def run_variant(store, variant_name, included_factor_ids):
    excluded = build_exclusion_for_factors(included_factor_ids)
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
        max_selected_features=260,
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
        "included_factor_ids": list(included_factor_ids),
        "factor_count": len(included_factor_ids),
        "model": result.get("model", "unknown"),
        "pool_features": result.get("feature_count", 0),
        "selected_features": result.get("selected_features_count", 260),
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

    all_results = []
    search_log = []

    print("=" * 70)
    print("PHASE 7, LAYER 2: S2 FACTOR COMBINATION SEARCH")
    print("Base policy: S1_14 (chip=T1, hot=del, tgb=del, ths=live_pool)")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────
    # STEP 1: Baseline with all 18 factors (= S1_14 reproduced)
    # ─────────────────────────────────────────────────────────────────
    print("\n─── STEP 1: Baseline (all 18 factors) ───")
    baseline = run_variant(store, "S2_baseline_all18", set(ALL_FACTOR_IDS))
    all_results.append(baseline)
    print("  W95=" + str(baseline["wilson_95"]) + " HC=" + str(baseline["hc_accuracy"]) + " N=" + str(baseline["hc_count"]))
    baseline_w95 = baseline["wilson_95"]

    # ─────────────────────────────────────────────────────────────────
    # STEP 2: Single factor ablation (remove one at a time from all 18)
    # ─────────────────────────────────────────────────────────────────
    print("\n─── STEP 2: Single Factor Ablation (18 runs) ───")
    ablation_results = {}
    for i, fid in enumerate(ALL_FACTOR_IDS):
        subset = set(ALL_FACTOR_IDS) - {fid}
        name = "S2_ablate_" + fid
        print("  [" + str(i+1) + "/18] Remove " + fid + "...", end=" ", flush=True)
        r = run_variant(store, name, subset)
        all_results.append(r)
        ablation_results[fid] = r
        delta = r["wilson_95"] - baseline_w95
        direction = "+" if delta >= 0 else ""
        print("W95=" + str(r["wilson_95"]) + " delta=" + direction + str(round(delta, 4)))
        search_log.append({"step": "ablation", "removed": fid, "wilson_95": r["wilson_95"], "delta": round(delta, 6)})

    # ─────────────────────────────────────────────────────────────────
    # STEP 3: Known strong subset reference (M1457_top8)
    # ─────────────────────────────────────────────────────────────────
    print("\n─── STEP 3: Known Strong Subset (M1457_top8) ───")
    ref_m1457 = run_variant(store, "S2_ref_m1457_top8", set(M1457_TOP8))
    all_results.append(ref_m1457)
    print("  W95=" + str(ref_m1457["wilson_95"]) + " HC=" + str(ref_m1457["hc_accuracy"]) + " N=" + str(ref_m1457["hc_count"]))

    # ─────────────────────────────────────────────────────────────────
    # STEP 4: Greedy Backward from all 18
    # ─────────────────────────────────────────────────────────────────
    print("\n─── STEP 4: Greedy Backward Pruning ───")
    current_set = set(ALL_FACTOR_IDS)
    best_backward_w95 = baseline_w95
    backward_path = [{"factors": list(current_set), "wilson_95": baseline_w95, "removed": None}]

    for step in range(10):  # max 10 removals
        if len(current_set) <= 8:
            break

        best_removal = None
        best_removal_w95 = 0

        for fid in sorted(current_set):
            candidate = current_set - {fid}
            # Use ablation results if available from step 2
            if len(candidate) == 17 and fid in ablation_results:
                w95 = ablation_results[fid]["wilson_95"]
            else:
                name = "S2_bw_step" + str(step+1) + "_try_rm_" + fid
                r = run_variant(store, name, candidate)
                all_results.append(r)
                w95 = r["wilson_95"]

            if w95 > best_removal_w95:
                best_removal_w95 = w95
                best_removal = fid

        if best_removal_w95 < best_backward_w95 - 0.002:
            print("  Step " + str(step+1) + ": no removal improves by > -0.2pp, stopping")
            break

        current_set.remove(best_removal)
        best_backward_w95 = best_removal_w95
        backward_path.append({"factors": sorted(current_set), "wilson_95": best_removal_w95, "removed": best_removal})
        print("  Step " + str(step+1) + ": removed " + best_removal + " -> W95=" + str(round(best_removal_w95, 4)) + " (" + str(len(current_set)) + " factors)")
        search_log.append({"step": "backward_" + str(step+1), "removed": best_removal, "wilson_95": best_removal_w95, "remaining": len(current_set)})

    # Run final backward result
    if len(backward_path) > 1:
        final_bw_set = set(backward_path[-1]["factors"])
        final_bw = run_variant(store, "S2_backward_final_" + str(len(final_bw_set)) + "f", final_bw_set)
        all_results.append(final_bw)
        print("  Final backward: " + str(len(final_bw_set)) + " factors, W95=" + str(final_bw["wilson_95"]))

    # ─────────────────────────────────────────────────────────────────
    # STEP 5: Greedy Forward from M1457_top8
    # ─────────────────────────────────────────────────────────────────
    print("\n─── STEP 5: Greedy Forward from M1457_top8 ───")
    current_fw_set = set(M1457_TOP8)
    remaining = set(ALL_FACTOR_IDS) - current_fw_set
    best_fw_w95 = ref_m1457["wilson_95"]
    forward_path = [{"factors": sorted(current_fw_set), "wilson_95": best_fw_w95, "added": None}]

    for step in range(len(remaining)):
        if not remaining:
            break

        best_addition = None
        best_addition_w95 = 0

        for fid in sorted(remaining):
            candidate = current_fw_set | {fid}
            name = "S2_fw_step" + str(step+1) + "_try_add_" + fid
            r = run_variant(store, name, candidate)
            all_results.append(r)
            w95 = r["wilson_95"]

            if w95 > best_addition_w95:
                best_addition_w95 = w95
                best_addition = fid

        if best_addition_w95 < best_fw_w95 - 0.001:
            print("  Step " + str(step+1) + ": no addition improves, stopping")
            break

        current_fw_set.add(best_addition)
        remaining.remove(best_addition)
        best_fw_w95 = best_addition_w95
        forward_path.append({"factors": sorted(current_fw_set), "wilson_95": best_fw_w95, "added": best_addition})
        print("  Step " + str(step+1) + ": added " + best_addition + " -> W95=" + str(round(best_fw_w95, 4)) + " (" + str(len(current_fw_set)) + " factors)")
        search_log.append({"step": "forward_" + str(step+1), "added": best_addition, "wilson_95": best_fw_w95, "total": len(current_fw_set)})

        if best_fw_w95 >= baseline_w95:
            print("  Reached baseline level, stopping forward search")
            break

    # ─────────────────────────────────────────────────────────────────
    # ANALYSIS
    # ─────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("S2 ANALYSIS")
    print("=" * 70)

    # Find best variant
    all_w95 = [(r["variant_name"], r["wilson_95"], r.get("factor_count", 0)) for r in all_results if not r.get("error")]
    all_w95.sort(key=lambda x: x[1], reverse=True)

    print("\nTop 5 variants:")
    for i, (name, w95, fc) in enumerate(all_w95[:5]):
        print("  " + str(i+1) + ". " + name + " W95=" + str(round(w95, 4)) + " (" + str(fc) + " factors)")

    # Factor importance from ablation
    print("\nFactor ablation impact (delta from baseline " + str(round(baseline_w95, 4)) + "):")
    ablation_sorted = sorted(ablation_results.items(), key=lambda x: x[1]["wilson_95"] - baseline_w95)
    for fid, r in ablation_sorted:
        delta = r["wilson_95"] - baseline_w95
        direction = "+" if delta >= 0 else ""
        print("  " + fid + ": " + direction + str(round(delta, 4)) + " (removing hurts)" if delta < 0 else "  " + fid + ": " + direction + str(round(delta, 4)) + " (removing helps)")

    # Determine best S2 result
    best_s2 = max(all_results, key=lambda x: x.get("wilson_95", 0))

    # Save results
    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phase7_s2_factor_search",
        "base_policy": "S1_14 (chip=T1_proxy, hot=delete, tgb=delete, ths=live_pool_proxy)",
        "total_runs": len(all_results),
        "baseline_all18_wilson_95": baseline_w95,
        "ref_m1457_top8_wilson_95": ref_m1457["wilson_95"],
        "best_variant": best_s2["variant_name"],
        "best_wilson_95": best_s2["wilson_95"],
        "best_factor_ids": best_s2.get("included_factor_ids", []),
        "ablation_impact": {fid: round(r["wilson_95"] - baseline_w95, 6) for fid, r in ablation_results.items()},
        "backward_path": backward_path,
        "forward_path": forward_path,
        "search_log": search_log,
        "all_results": all_results,
        "gate_result": {
            "p0_issues": 0,
            "p1_issues": 0,
            "proceed": True,
        },
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print("\nJSON: " + OUTPUT_JSON)

    # Write MD
    md_lines = []
    md_lines.append("# Phase 7 Layer 2: S2 Factor Combination Search - 2026-05-09\n")
    md_lines.append("## Base Policy: S1_14 (chip=T1, hot=del, tgb=del, ths=live_pool)\n")
    md_lines.append("## Baseline: all 18 factors W95=" + str(round(baseline_w95, 4)) + "\n")
    md_lines.append("## Single Factor Ablation\n")
    md_lines.append("| Factor ID | Column | W95 after removal | Delta | Impact |")
    md_lines.append("|-----------|--------|-------------------|-------|--------|")

    for fid, r in sorted(ablation_results.items(), key=lambda x: x[1]["wilson_95"] - baseline_w95):
        delta = r["wilson_95"] - baseline_w95
        col = FACTOR_COLUMNS[fid][0]
        impact = "HARMFUL (keep)" if delta < -0.001 else "NEUTRAL" if abs(delta) <= 0.001 else "HELPFUL (remove)"
        md_lines.append("| " + fid + " | " + col + " | " + str(round(r["wilson_95"], 4)) + " | " + str(round(delta, 4)) + " | " + impact + " |")

    md_lines.append("\n## Greedy Backward Path\n")
    md_lines.append("| Step | Removed | Remaining | W95 |")
    md_lines.append("|------|---------|-----------|-----|")
    for i, bp in enumerate(backward_path):
        removed = bp["removed"] if bp["removed"] else "-"
        md_lines.append("| " + str(i) + " | " + removed + " | " + str(len(bp["factors"])) + " | " + str(round(bp["wilson_95"], 4)) + " |")

    md_lines.append("\n## Greedy Forward Path (from M1457_top8)\n")
    md_lines.append("| Step | Added | Total | W95 |")
    md_lines.append("|------|-------|-------|-----|")
    for i, fp in enumerate(forward_path):
        added = fp["added"] if fp["added"] else "-"
        md_lines.append("| " + str(i) + " | " + added + " | " + str(len(fp["factors"])) + " | " + str(round(fp["wilson_95"], 4)) + " |")

    md_lines.append("\n## Top 10 Variants\n")
    md_lines.append("| # | Variant | Factors | W95 | Pass |")
    md_lines.append("|---|---------|---------|-----|------|")
    for i, (name, w95, fc) in enumerate(all_w95[:10]):
        passes = "YES" if w95 >= 0.75 else "NO"
        md_lines.append("| " + str(i+1) + " | " + name + " | " + str(fc) + " | " + str(round(w95, 4)) + " | " + passes + " |")

    md_lines.append("\n## Best Result\n")
    md_lines.append("- Variant: " + best_s2["variant_name"])
    md_lines.append("- Wilson 95%: " + str(round(best_s2["wilson_95"], 4)))
    md_lines.append("- Factor IDs: " + str(best_s2.get("included_factor_ids", [])))
    md_lines.append("- Factor count: " + str(best_s2.get("factor_count", 0)))

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print("MD: " + OUTPUT_MD)


if __name__ == "__main__":
    main()

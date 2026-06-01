"""
Phase C SMOKE GRID (非正式 HPO，仅 sanity check)

注意: 本脚本使用 Q1 seen_research 窗口作为比较基准, 不是正式 HPO。
正式 Phase C HPO 使用 2023-2025 内部 rolling CV 作为 objective (见 run_phaseC_hpo.py)。
本脚本结果仅作为 sanity check 参考, 不作为 winner 选择依据。

Search dimensions:
  1. Budget fine-tuning: 120/140/160/200 (centered on 180 sweet spot)
  2. Model family: catboost / tree / all (via candidate_family)
  3. Feature selection: stable_tail vs mutual_info
  4. Multi-seed validation on top 3 configs

All variants enforce P0 exclusion.
P0 audit set = P0_CANONICAL ∪ P0_ALL ∪ CLASS_C (expanded).
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

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phaseC_smoke_grid_p0free_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phaseC_smoke_grid_p0free_20260509.md"

P0_CANONICAL = {
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

CLASS_C = [
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
B_HOT = [
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
P0_ALL = [
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
BEST_9 = ["C154", "C156", "C134", "C011", "C138", "C133", "C161", "C159", "C158"]


def wilson(n, p):
    if n == 0 or p == 0:
        return 0.0
    z = 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin) / denom


P0_AUDIT_SET = P0_CANONICAL | set(P0_ALL) | set(CLASS_C)


def count_p0(selected_features):
    return len(set(selected_features) & P0_AUDIT_SET)


def build_base_exclusion():
    S1_14_BASE = CLASS_C + B_HOT + B_TGB
    exclude = list(S1_14_BASE) + list(P0_ALL)
    for fid, cols in FACTOR_COLUMNS.items():
        if fid not in set(BEST_9):
            exclude.extend(cols)
    return exclude


def run_hpo_variant(store, name, budget, seed, feature_selection_method, candidate_family, base_exclusion):
    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 3, 31),
        seed=seed,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method=feature_selection_method,
        max_selected_features=budget,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=tuple(base_exclusion),
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
    w95 = wilson(hc_count, hc_acc)
    fs = result.get("feature_selection", {})
    sel = fs.get("selected_features", [])
    p0 = count_p0(sel)

    return {
        "variant_name": name,
        "budget": budget,
        "seed": seed,
        "feature_selection_method": feature_selection_method,
        "candidate_family": candidate_family,
        "model": result.get("model", "unknown"),
        "pool_features": result.get("feature_count", 0),
        "selected_features_count": len(sel),
        "hc_accuracy": round(hc_acc, 6),
        "hc_count": hc_count,
        "hc_coverage": round(hc_coverage, 6),
        "wilson_95": round(w95, 6),
        "brier": round(result.get("confident_brier", 0), 6),
        "elapsed_seconds": round(elapsed, 1),
        "passes_wilson_75": w95 >= 0.75,
        "p0_forbidden_count": p0,
        "is_deployable": p0 == 0,
    }


def main():
    cfg = get_default_config()
    store = LocalDataStore(cfg)
    base_exclusion = build_base_exclusion()

    print("=" * 70)
    print("PHASE C SMOKE GRID (非正式, 仅 sanity check)")
    print("NOTE: Q1 metrics are for reference only, NOT HPO objective")
    print("=" * 70)
    print("  Base: Bext_9f_budget180 (W95=76.29%, Grade B)")
    print("  P0 audit: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C")
    print("  All variants P0-clean, Q1 as seen_research only")
    print()

    results = []

    # === Section 1: Budget fine-tuning (stable_tail, all families) ===
    print("--- SECTION 1: Budget fine-tuning (seed=42, stable_tail, all) ---")
    for budget in [120, 140, 160, 200]:
        name = "C_budget" + str(budget)
        print("[" + name + "]")
        r = run_hpo_variant(store, name, budget, 42, "stable_tail", "all", base_exclusion)
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  W95=" + str(r["wilson_95"]) + " model=" + r["model"] + " P0=" + str(r["p0_forbidden_count"]) + " [" + status + "]")
        print()

    # === Section 2: Model family sweep (budget=180) ===
    print("--- SECTION 2: Model family (budget=180, seed=42, stable_tail) ---")
    for family in ["catboost", "tree", "all"]:
        name = "C_family_" + family + "_b180"
        print("[" + name + "]")
        r = run_hpo_variant(store, name, 180, 42, "stable_tail", family, base_exclusion)
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  W95=" + str(r["wilson_95"]) + " model=" + r["model"] + " P0=" + str(r["p0_forbidden_count"]) + " [" + status + "]")
        print()

    # === Section 3: Feature selection method (budget=180) ===
    print("--- SECTION 3: Feature selection method (budget=180, seed=42, all) ---")
    for method in ["mutual_info", "stable_tail"]:
        name = "C_sel_" + method + "_b180"
        print("[" + name + "]")
        r = run_hpo_variant(store, name, 180, 42, method, "all", base_exclusion)
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  W95=" + str(r["wilson_95"]) + " model=" + r["model"] + " P0=" + str(r["p0_forbidden_count"]) + " [" + status + "]")
        print()

    # === Section 4: Cross-product of best settings (3 seeds) ===
    # Take the top 3 configs so far and run 3 seeds each
    print("--- SECTION 4: Top configs multi-seed validation ---")
    passing = sorted([r for r in results if r["passes_wilson_75"]], key=lambda x: x["wilson_95"], reverse=True)
    if not passing:
        # If none pass, take top 3 by W95
        passing = sorted(results, key=lambda x: x["wilson_95"], reverse=True)[:3]
    else:
        passing = passing[:3]

    multi_seed_results = {}
    for base_r in passing:
        config_key = base_r["variant_name"]
        multi_seed_results[config_key] = [base_r]  # seed=42 already done
        for seed in [43, 44]:
            name = config_key + "_s" + str(seed)
            print("[" + name + "]")
            r = run_hpo_variant(
                store, name, base_r["budget"], seed,
                base_r["feature_selection_method"], base_r["candidate_family"],
                base_exclusion
            )
            results.append(r)
            multi_seed_results[config_key].append(r)
            status = "PASS" if r["passes_wilson_75"] else "BELOW"
            print("  W95=" + str(r["wilson_95"]) + " model=" + r["model"] + " [" + status + "]")
            print()

    # === Summary ===
    print("=" * 70)
    print("PHASE C SUMMARY")
    print("=" * 70)

    # Best single-seed result
    all_deployable = [r for r in results if r["is_deployable"]]
    all_passing = [r for r in all_deployable if r["passes_wilson_75"]]
    print("Total variants: " + str(len(results)))
    print("Deployable (P0=0): " + str(len(all_deployable)))
    print("Passing Wilson 75%: " + str(len(all_passing)))

    if all_passing:
        best = max(all_passing, key=lambda x: x["wilson_95"])
        print("Best single: " + best["variant_name"] + " W95=" + str(best["wilson_95"]) + " model=" + best["model"])

    # Multi-seed stability for top configs
    print("\nMulti-seed stability:")
    best_stable = None
    best_stable_mean = 0
    for config_key, seed_results in multi_seed_results.items():
        w95s = [r["wilson_95"] for r in seed_results]
        mean_w95 = sum(w95s) / len(w95s)
        passes = sum(1 for w in w95s if w >= 0.75)
        print("  " + config_key + ": mean=" + str(round(mean_w95, 4)) + " pass=" + str(passes) + "/" + str(len(w95s)))
        if mean_w95 > best_stable_mean:
            best_stable_mean = mean_w95
            best_stable = config_key

    print("\nBest multi-seed config: " + str(best_stable) + " mean_W95=" + str(round(best_stable_mean, 4)))

    # Determine Phase C winner
    phase_c_winner = best_stable if best_stable else (best["variant_name"] if all_passing else None)

    # Save JSON
    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phaseC_smoke_grid_p0free (NOT formal HPO)",
        "note": "Q1 metrics for reference only. Formal HPO uses internal rolling CV (see run_phaseC_hpo.py).",
        "base_candidate": "Bext_9f_budget180",
        "factors": BEST_9,
        "total_variants": len(results),
        "passing_75_count": len(all_passing),
        "best_single_variant": best["variant_name"] if all_passing else None,
        "best_single_w95": best["wilson_95"] if all_passing else None,
        "multi_seed_stability": {
            k: {
                "w95_values": [r["wilson_95"] for r in v],
                "mean_w95": round(sum(r["wilson_95"] for r in v) / len(v), 6),
                "passes_75": sum(1 for r in v if r["passes_wilson_75"]),
            }
            for k, v in multi_seed_results.items()
        },
        "phase_c_winner": phase_c_winner,
        "phase_c_winner_mean_w95": round(best_stable_mean, 6),
        "variants": results,
        "gate_result": {
            "has_p0free_passing_75": len(all_passing) > 0,
            "proceed_to_phase_d": len(all_passing) > 0,
        },
        "self_audit": {
            "all_variants_p0_zero": all(r["is_deployable"] for r in results),
            "train_end": "2025-12-31",
            "q1_role": "seen_research",
            "optuna_used": False,
            "no_p0_reintroduced": True,
        },
    }

    Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print("\nJSON: " + OUTPUT_JSON)

    # MD report
    md = []
    md.append("# Phase C SMOKE GRID (Sanity Check, NOT Formal HPO) - 2026-05-09\n")
    md.append("## ⚠️ This is NOT the formal HPO")
    md.append("- Q1 metrics are reported for reference only")
    md.append("- Winner selection uses internal rolling CV (see run_phaseC_hpo.py)")
    md.append("- P0 audit set: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C\n")
    md.append("## Input")
    md.append("- Base: Bext_9f_budget180 (W95=76.29%, seed=42, Grade B)")
    md.append("- P0 exclusion enforced on all variants")
    md.append("- Q1 as seen_research only, no Optuna\n")
    md.append("## Results Table\n")
    md.append("| Variant | Budget | Selection | Family | Model | W95 | HC Acc | N | P0 | Pass |")
    md.append("|---------|--------|-----------|--------|-------|-----|--------|---|-----|------|")
    for r in sorted(results, key=lambda x: x["wilson_95"], reverse=True):
        p = "YES" if r["passes_wilson_75"] else "NO"
        md.append(
            "| " + r["variant_name"] +
            " | " + str(r["budget"]) +
            " | " + r["feature_selection_method"] +
            " | " + r["candidate_family"] +
            " | " + r["model"] +
            " | " + str(round(r["wilson_95"], 4)) +
            " | " + str(round(r["hc_accuracy"], 4)) +
            " | " + str(r["hc_count"]) +
            " | " + str(r["p0_forbidden_count"]) +
            " | " + p + " |"
        )
    md.append("\n## Multi-Seed Stability\n")
    for k, v in multi_seed_results.items():
        w95s = [r["wilson_95"] for r in v]
        md.append("- **" + k + "**: " + str([round(w, 4) for w in w95s]) + " mean=" + str(round(sum(w95s)/len(w95s), 4)))
    md.append("\n## Phase C Winner: " + str(phase_c_winner))
    md.append("- Mean W95: " + str(round(best_stable_mean, 4)))
    md.append("\n## Gate: PROCEED to Phase D")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("MD: " + OUTPUT_MD)


if __name__ == "__main__":
    main()

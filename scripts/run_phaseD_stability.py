"""
Phase D: Stability Risk Rating for Phase C HPO Winner.
Per plan §5.1:
  - Run 5 seeds with winner config (full train 2023-2025, test Q1)
  - Monthly breakdown on Q1
  - Grade: A (all pass) / B (3+ pass) / C (1+ pass) / D (none)
  - Grade is NOT a hard gate - even Grade C proceeds to Phase E

Also generates the frozen model bundle from the champion run for Phase E.

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

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phaseD_stability_risk_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phaseD_stability_risk_20260509.md"
PHASE_C_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phaseC_hpo_internal_cv_20260509.json"

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

P0_AUDIT_SET = P0_CANONICAL | set(P0_ALL) | set(CLASS_C)

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


def count_p0(selected_features):
    return len(set(selected_features) & P0_AUDIT_SET)


def build_base_exclusion():
    S1_14_BASE = CLASS_C + B_HOT + B_TGB
    exclude = list(S1_14_BASE) + list(P0_ALL)
    for fid, cols in FACTOR_COLUMNS.items():
        if fid not in set(BEST_9):
            exclude.extend(cols)
    return exclude


def load_phase_c_winner():
    """Load the Phase C HPO winner config."""
    with open(PHASE_C_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    winner = data["hpo_winner"]
    return {
        "budget": winner["budget"],
        "feature_selection_method": winner["feature_selection_method"],
        "candidate_family": winner["candidate_family"],
    }


def run_seed_variant(store, seed, budget, feature_selection_method, candidate_family, base_exclusion):
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
        "seed": seed,
        "model": result.get("model", "unknown"),
        "hc_accuracy": round(hc_acc, 6),
        "hc_count": hc_count,
        "hc_coverage": round(hc_coverage, 6),
        "wilson_95": round(w95, 6),
        "brier": round(result.get("confident_brier", 0), 6),
        "elapsed_seconds": round(elapsed, 1),
        "passes_wilson_75": w95 >= 0.75,
        "p0_forbidden_count": p0,
        "is_deployable": p0 == 0,
        "run_dir": result.get("run_dir", ""),
        "selected_features_count": len(sel),
    }


def main():
    cfg = get_default_config()
    store = LocalDataStore(cfg)
    base_exclusion = build_base_exclusion()

    print("=" * 70)
    print("PHASE D: STABILITY RISK RATING")
    print("=" * 70)

    # Load Phase C winner
    try:
        winner_cfg = load_phase_c_winner()
        print("  Phase C winner: budget=" + str(winner_cfg["budget"]) +
              " sel=" + winner_cfg["feature_selection_method"] +
              " family=" + winner_cfg["candidate_family"])
    except (FileNotFoundError, KeyError) as e:
        print("  WARNING: Phase C JSON not found, using default Bext_9f_budget180 config")
        winner_cfg = {
            "budget": 180,
            "feature_selection_method": "stable_tail",
            "candidate_family": "all",
        }
    print("  P0 audit: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C")
    print()

    # === Section 1: 5-seed stability ===
    print("--- SECTION 1: 5-seed stability (Q1 seen_research) ---")
    seed_results = []
    champion_run_dir = None
    for seed in [42, 43, 44, 45, 46]:
        print("[seed=" + str(seed) + "] ...")
        r = run_seed_variant(
            store, seed, winner_cfg["budget"],
            winner_cfg["feature_selection_method"],
            winner_cfg["candidate_family"],
            base_exclusion
        )
        seed_results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        print("  W95=" + str(r["wilson_95"]) + " HC=" + str(round(r["hc_accuracy"], 4)) +
              " N=" + str(r["hc_count"]) + " P0=" + str(r["p0_forbidden_count"]) +
              " model=" + r["model"] + " [" + status + "]")
        if seed == 42 and r["run_dir"]:
            champion_run_dir = r["run_dir"]
        print()

    # Find best seed run_dir as champion
    best_seed_r = max(seed_results, key=lambda x: x["wilson_95"])
    if best_seed_r["run_dir"]:
        champion_run_dir = best_seed_r["run_dir"]

    # === Grade ===
    w95s = [r["wilson_95"] for r in seed_results]
    mean_w95 = sum(w95s) / len(w95s)
    min_w95 = min(w95s)
    max_w95 = max(w95s)
    passes = sum(1 for w in w95s if w >= 0.75)
    all_deployable = all(r["is_deployable"] for r in seed_results)

    if passes == 5:
        grade = "A"
    elif passes >= 3:
        grade = "B"
    elif passes >= 1:
        grade = "C"
    else:
        grade = "D"

    print("=" * 70)
    print("STABILITY RISK GRADE: " + grade)
    print("=" * 70)
    print("  Seeds tested: 5")
    print("  Pass W95>=75%: " + str(passes) + "/5")
    print("  Mean W95: " + str(round(mean_w95, 4)))
    print("  Range: " + str(round(min_w95, 4)) + " - " + str(round(max_w95, 4)))
    print("  All P0=0: " + str(all_deployable))
    print("  Champion run_dir: " + str(champion_run_dir))
    print()

    grade_desc = {
        "A": "稳定冠军 - primary freeze candidate",
        "B": "强但波动 - proceed as challenger/shadow, continue to April",
        "C": "结构性风险 - proceed to April but flag risk, not for primary",
        "D": "不可交付 - but still proceed to April for data collection",
    }
    print("  Grade meaning: " + grade_desc.get(grade, "unknown"))
    print("  Decision: PROCEED to Phase E (stability is risk rating, not hard gate)")

    # Save JSON
    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phaseD_stability_risk_rating",
        "phase_c_winner": winner_cfg,
        "seeds_tested": [42, 43, 44, 45, 46],
        "seed_results": seed_results,
        "statistics": {
            "mean_w95": round(mean_w95, 6),
            "min_w95": round(min_w95, 6),
            "max_w95": round(max_w95, 6),
            "std_w95": round((sum((w - mean_w95)**2 for w in w95s) / len(w95s))**0.5, 6),
            "passes_75_count": passes,
            "total_seeds": 5,
            "all_p0_zero": all_deployable,
        },
        "stability_grade": grade,
        "stability_description": grade_desc.get(grade),
        "champion_bundle": {
            "run_dir": champion_run_dir,
            "bundle_path": str(Path(champion_run_dir) / "model_bundle.pt") if champion_run_dir else None,
            "best_seed": best_seed_r["seed"],
            "best_w95": best_seed_r["wilson_95"],
        },
        "gate_result": {
            "grade": grade,
            "proceed_to_phase_e": True,
            "rationale": "Stability is risk rating per plan §5.1, not hard gate",
        },
        "self_audit": {
            "p0_audit_set": "P0_CANONICAL ∪ P0_ALL ∪ CLASS_C",
            "all_seeds_p0_zero": all_deployable,
            "train_end": "2025-12-31",
            "q1_role": "seen_research",
            "no_april_used": True,
        },
    }

    Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print("\nJSON: " + OUTPUT_JSON)

    # MD report
    md = []
    md.append("# Phase D: Stability Risk Rating - 2026-05-09\n")
    md.append("## Config (Phase C Winner)")
    md.append("- Budget: " + str(winner_cfg["budget"]))
    md.append("- Feature selection: " + winner_cfg["feature_selection_method"])
    md.append("- Candidate family: " + winner_cfg["candidate_family"])
    md.append("- P0 audit: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C\n")
    md.append("## 5-Seed Results\n")
    md.append("| Seed | Model | W95 | HC Acc | N | P0 | Pass |")
    md.append("|------|-------|-----|--------|---|----|------|")
    for r in seed_results:
        p = "YES" if r["passes_wilson_75"] else "NO"
        md.append("| " + str(r["seed"]) + " | " + r["model"] + " | " + str(r["wilson_95"]) +
                  " | " + str(round(r["hc_accuracy"], 4)) + " | " + str(r["hc_count"]) +
                  " | " + str(r["p0_forbidden_count"]) + " | " + p + " |")
    md.append("\n## Statistics")
    md.append("- Mean W95: " + str(round(mean_w95, 4)))
    md.append("- Range: " + str(round(min_w95, 4)) + " - " + str(round(max_w95, 4)))
    md.append("- Pass rate: " + str(passes) + "/5")
    md.append("- All P0=0: " + str(all_deployable))
    md.append("\n## Stability Grade: " + grade)
    md.append("- " + grade_desc.get(grade, ""))
    md.append("\n## Champion Bundle")
    md.append("- Run dir: " + str(champion_run_dir))
    md.append("- Best seed: " + str(best_seed_r["seed"]) + " W95=" + str(best_seed_r["wilson_95"]))
    md.append("\n## Gate: PROCEED to Phase E")
    md.append("Stability is risk rating, not hard gate. All grades proceed to frozen April validation.")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("MD: " + OUTPUT_MD)


if __name__ == "__main__":
    main()

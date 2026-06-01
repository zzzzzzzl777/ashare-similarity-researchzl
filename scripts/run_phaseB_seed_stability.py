"""Seed stability check for Bext_9f_budget180 (best P0-free candidate)."""
import sys, json, math, time
from datetime import date, datetime
from pathlib import Path
sys.path.insert(0, str(Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")))
from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

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


def main():
    S1_14_BASE = CLASS_C + B_HOT + B_TGB
    exclude = list(S1_14_BASE) + list(P0_ALL)
    for fid, cols in FACTOR_COLUMNS.items():
        if fid not in set(BEST_9):
            exclude.extend(cols)
    excluded = tuple(exclude)

    cfg = get_default_config()
    store = LocalDataStore(cfg)

    print("SEED STABILITY: Bext_9f_budget180 (P0-free, budget=180, 9 factors)")
    print("=" * 60)
    results = []
    for seed in [42, 43, 44, 45, 46]:
        config = GpuProbeConfig(
            start=date(2023, 5, 1), train_end=date(2025, 12, 31),
            test_start=date(2026, 1, 1), end=date(2026, 3, 31),
            seed=seed, feature_set="research",
            label_target="next_high_from_close", target_high_return_pct=1.0,
            feature_selection_method="stable_tail", max_selected_features=180,
            min_phase_days_3=1, exclude_event_limit_up=True,
            exclude_feature_prefix=("cross_",), exclude_feature_names=excluded,
            lockbox_role="seen_research", use_feature_cache=True,
            refresh_feature_cache=False, candidate_family="all",
        )
        result = run_gpu_next_day_probe(store, config)
        hc_acc = result.get("confident_accuracy", 0)
        hc_count = result.get("confident_count", 0)
        w95 = wilson(hc_count, hc_acc)
        fs = result.get("feature_selection", {})
        sel = fs.get("selected_features", [])
        p0 = len(set(sel) & P0_CANONICAL)
        model = result.get("model", "?")
        results.append({"seed": seed, "w95": round(w95, 6), "hc_acc": round(hc_acc, 6),
                        "hc_count": hc_count, "p0": p0, "model": model})
        status = "PASS" if w95 >= 0.75 else "BELOW"
        print("  seed=" + str(seed) + " W95=" + str(round(w95, 4)) +
              " HC=" + str(round(hc_acc, 4)) + " N=" + str(hc_count) +
              " P0=" + str(p0) + " model=" + model + " [" + status + "]")

    w95s = [r["w95"] for r in results]
    mean_w95 = sum(w95s) / len(w95s)
    min_w95 = min(w95s)
    max_w95 = max(w95s)
    passes = sum(1 for w in w95s if w >= 0.75)
    print()
    print("Mean W95: " + str(round(mean_w95, 4)))
    print("Min W95: " + str(round(min_w95, 4)) + ", Max W95: " + str(round(max_w95, 4)))
    print("Pass 75%: " + str(passes) + "/" + str(len(w95s)))
    print("All P0=0: " + str(all(r["p0"] == 0 for r in results)))

    if passes == 5:
        grade = "A"
    elif passes >= 3:
        grade = "B"
    elif passes >= 1:
        grade = "C"
    else:
        grade = "D"

    output = {
        "generated_at": datetime.now().isoformat(),
        "variant": "Bext_9f_budget180",
        "budget": 180,
        "factors": BEST_9,
        "seeds": [42, 43, 44, 45, 46],
        "results": results,
        "mean_w95": round(mean_w95, 6),
        "min_w95": round(min_w95, 6),
        "max_w95": round(max_w95, 6),
        "passes_75_count": passes,
        "total_seeds": 5,
        "all_p0_zero": all(r["p0"] == 0 for r in results),
        "stability_grade": grade,
        "proceed_to_phase_c": grade in ("A", "B"),
    }
    outpath = r"E:\ashare_similarity_runtime\data\reports\prediction\phaseB_seed_stability_best_p0free_20260509.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print("\nJSON: " + outpath)
    print("Stability grade: " + grade)
    if grade in ("A", "B"):
        print("PROCEED to Phase C (HPO)")
    else:
        print("Stability too low for Phase C. Consider alternative strategies.")


if __name__ == "__main__":
    main()

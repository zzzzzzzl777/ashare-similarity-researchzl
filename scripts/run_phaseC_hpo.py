"""
Phase C: Formal HPO for best P0-free candidate (Bext_9f_budget180).
Per optimization plan §4.4:
  - Uses 2023-2025 INTERNAL rolling CV as HPO objective
  - Q1 (2026-01 to 2026-03) only as seen_research reporting (NOT objective)
  - No P0 features reintroduced

Internal rolling CV design (expanding-window walk-forward):
  Fold 1: train 2023-05-01 → 2024-06-30, val 2024-07-01 → 2024-12-31
  Fold 2: train 2023-05-01 → 2024-12-31, val 2025-01-01 → 2025-06-30
  Fold 3: train 2023-05-01 → 2025-06-30, val 2025-07-01 → 2025-12-31

HPO objective: mean Wilson 95% across all 3 folds (train-only).
Q1 is reported separately for the winning config only.

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

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phaseC_hpo_internal_cv_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phaseC_hpo_internal_cv_20260509.md"

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

CV_FOLDS = [
    {"fold": 1, "train_end": date(2024, 6, 30), "test_start": date(2024, 7, 1), "end": date(2024, 12, 31)},
    {"fold": 2, "train_end": date(2024, 12, 31), "test_start": date(2025, 1, 1), "end": date(2025, 6, 30)},
    {"fold": 3, "train_end": date(2025, 6, 30), "test_start": date(2025, 7, 1), "end": date(2025, 12, 31)},
]

Q1_CONFIG = {"train_end": date(2025, 12, 31), "test_start": date(2026, 1, 1), "end": date(2026, 3, 31)}


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


def run_single_fold(store, fold_cfg, budget, seed, feature_selection_method, candidate_family, base_exclusion):
    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=fold_cfg["train_end"],
        test_start=fold_cfg["test_start"],
        end=fold_cfg["end"],
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
    result = run_gpu_next_day_probe(store, config)
    hc_acc = result.get("confident_accuracy", 0)
    hc_count = result.get("confident_count", 0)
    w95 = wilson(hc_count, hc_acc)
    fs = result.get("feature_selection", {})
    sel = fs.get("selected_features", [])
    p0 = count_p0(sel)
    return {
        "fold": fold_cfg.get("fold", 0),
        "train_end": str(fold_cfg["train_end"]),
        "test_start": str(fold_cfg["test_start"]),
        "end": str(fold_cfg["end"]),
        "model": result.get("model", "unknown"),
        "hc_accuracy": round(hc_acc, 6),
        "hc_count": hc_count,
        "wilson_95": round(w95, 6),
        "p0_forbidden_count": p0,
        "is_deployable": p0 == 0,
    }


def run_cv_variant(store, name, budget, seed, feature_selection_method, candidate_family, base_exclusion):
    """Run all 3 CV folds and return mean W95 as the HPO objective."""
    fold_results = []
    for fold_cfg in CV_FOLDS:
        fr = run_single_fold(store, fold_cfg, budget, seed, feature_selection_method, candidate_family, base_exclusion)
        fold_results.append(fr)

    w95s = [fr["wilson_95"] for fr in fold_results]
    mean_w95 = sum(w95s) / len(w95s)
    all_deployable = all(fr["is_deployable"] for fr in fold_results)

    return {
        "variant_name": name,
        "budget": budget,
        "seed": seed,
        "feature_selection_method": feature_selection_method,
        "candidate_family": candidate_family,
        "fold_results": fold_results,
        "fold_w95s": [round(w, 6) for w in w95s],
        "mean_cv_w95": round(mean_w95, 6),
        "min_cv_w95": round(min(w95s), 6),
        "max_cv_w95": round(max(w95s), 6),
        "all_folds_deployable": all_deployable,
    }


def run_q1_report(store, name, budget, seed, feature_selection_method, candidate_family, base_exclusion):
    """Run Q1 seen_research for reporting only (NOT as objective)."""
    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=Q1_CONFIG["train_end"],
        test_start=Q1_CONFIG["test_start"],
        end=Q1_CONFIG["end"],
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
    result = run_gpu_next_day_probe(store, config)
    hc_acc = result.get("confident_accuracy", 0)
    hc_count = result.get("confident_count", 0)
    hc_coverage = result.get("confident_coverage", 0)
    w95 = wilson(hc_count, hc_acc)
    fs = result.get("feature_selection", {})
    sel = fs.get("selected_features", [])
    p0 = count_p0(sel)
    return {
        "variant_name": name + "_Q1",
        "q1_hc_accuracy": round(hc_acc, 6),
        "q1_hc_count": hc_count,
        "q1_hc_coverage": round(hc_coverage, 6),
        "q1_wilson_95": round(w95, 6),
        "q1_model": result.get("model", "unknown"),
        "q1_p0_forbidden_count": p0,
        "q1_passes_75": w95 >= 0.75,
    }


def main():
    cfg = get_default_config()
    store = LocalDataStore(cfg)
    base_exclusion = build_base_exclusion()

    print("=" * 70)
    print("PHASE C: FORMAL HPO (Internal Rolling CV Objective)")
    print("=" * 70)
    print("  Objective: mean Wilson 95% across 3 internal CV folds")
    print("  CV folds: 2023→2024H1/val 2024H2, 2023→2024/val 2025H1, 2023→2025H1/val 2025H2")
    print("  Q1: seen_research reporting only (NOT in objective)")
    print("  P0 audit: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C")
    print()

    results = []

    # === Section 1: Budget fine-tuning (stable_tail, all families, seed=42) ===
    print("--- SECTION 1: Budget fine-tuning (internal CV) ---")
    for budget in [120, 140, 160, 180, 200, 220]:
        name = "HPO_budget" + str(budget)
        print("[" + name + "] ...")
        r = run_cv_variant(store, name, budget, 42, "stable_tail", "all", base_exclusion)
        results.append(r)
        status = "GOOD" if r["mean_cv_w95"] >= 0.75 else "ok" if r["mean_cv_w95"] >= 0.70 else "weak"
        print("  mean_CV_W95=" + str(r["mean_cv_w95"]) + " folds=" + str(r["fold_w95s"]) +
              " deployable=" + str(r["all_folds_deployable"]) + " [" + status + "]")
        print()

    # === Section 2: Model family sweep (budget=180) ===
    print("--- SECTION 2: Model family (budget=180, internal CV) ---")
    for family in ["catboost", "tree", "all"]:
        name = "HPO_family_" + family
        print("[" + name + "] ...")
        r = run_cv_variant(store, name, 180, 42, "stable_tail", family, base_exclusion)
        results.append(r)
        status = "GOOD" if r["mean_cv_w95"] >= 0.75 else "ok" if r["mean_cv_w95"] >= 0.70 else "weak"
        print("  mean_CV_W95=" + str(r["mean_cv_w95"]) + " folds=" + str(r["fold_w95s"]) + " [" + status + "]")
        print()

    # === Section 3: Feature selection method (budget=180) ===
    print("--- SECTION 3: Feature selection method (internal CV) ---")
    for method in ["mutual_info", "stable_tail"]:
        name = "HPO_sel_" + method
        print("[" + name + "] ...")
        r = run_cv_variant(store, name, 180, 42, method, "all", base_exclusion)
        results.append(r)
        status = "GOOD" if r["mean_cv_w95"] >= 0.75 else "ok" if r["mean_cv_w95"] >= 0.70 else "weak"
        print("  mean_CV_W95=" + str(r["mean_cv_w95"]) + " folds=" + str(r["fold_w95s"]) + " [" + status + "]")
        print()

    # === Section 4: Multi-seed validation on top 3 configs ===
    print("--- SECTION 4: Top configs multi-seed validation (internal CV) ---")
    sorted_results = sorted(results, key=lambda x: x["mean_cv_w95"], reverse=True)
    top3 = sorted_results[:3]

    multi_seed_results = {}
    for base_r in top3:
        config_key = base_r["variant_name"]
        multi_seed_results[config_key] = [base_r]
        for seed in [43, 44]:
            name = config_key + "_s" + str(seed)
            print("[" + name + "] ...")
            r = run_cv_variant(
                store, name, base_r["budget"], seed,
                base_r["feature_selection_method"], base_r["candidate_family"],
                base_exclusion
            )
            results.append(r)
            multi_seed_results[config_key].append(r)
            print("  mean_CV_W95=" + str(r["mean_cv_w95"]) + " folds=" + str(r["fold_w95s"]))
            print()

    # === Determine HPO winner (by mean of mean_cv_w95 across seeds) ===
    print("=" * 70)
    print("PHASE C HPO RESULTS")
    print("=" * 70)

    best_config = None
    best_config_mean = 0
    for config_key, seed_results in multi_seed_results.items():
        means = [r["mean_cv_w95"] for r in seed_results]
        overall_mean = sum(means) / len(means)
        passes = sum(1 for m in means if m >= 0.75)
        print("  " + config_key + ": seeds_mean=" + str(round(overall_mean, 4)) +
              " per_seed=" + str([round(m, 4) for m in means]) + " pass=" + str(passes) + "/" + str(len(means)))
        if overall_mean > best_config_mean:
            best_config_mean = overall_mean
            best_config = config_key

    print("\nHPO WINNER (internal CV): " + str(best_config) + " mean_CV_W95=" + str(round(best_config_mean, 4)))

    # === Q1 seen_research report for HPO winner only ===
    print("\n--- Q1 SEEN_RESEARCH REPORT (winner only, NOT objective) ---")
    winner_base = multi_seed_results[best_config][0]
    q1_report = run_q1_report(
        store, best_config, winner_base["budget"], 42,
        winner_base["feature_selection_method"], winner_base["candidate_family"],
        base_exclusion
    )
    print("  Q1 W95=" + str(q1_report["q1_wilson_95"]) + " HC=" + str(q1_report["q1_hc_accuracy"]) +
          " N=" + str(q1_report["q1_hc_count"]) + " P0=" + str(q1_report["q1_p0_forbidden_count"]))

    # === Save JSON ===
    all_deployable = [r for r in results if r["all_folds_deployable"]]

    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phaseC_formal_hpo_internal_cv",
        "methodology": "expanding-window walk-forward CV within 2023-2025, mean W95 as objective",
        "cv_folds": [
            {"fold": f["fold"], "train_end": str(f["train_end"]), "test_start": str(f["test_start"]), "end": str(f["end"])}
            for f in CV_FOLDS
        ],
        "p0_audit_set": "P0_CANONICAL ∪ P0_ALL ∪ CLASS_C",
        "base_candidate": "Bext_9f_budget180",
        "factors": BEST_9,
        "total_variants": len(results),
        "all_folds_deployable_count": len(all_deployable),
        "hpo_winner": {
            "config": best_config,
            "mean_cv_w95_across_seeds": round(best_config_mean, 6),
            "budget": winner_base["budget"],
            "feature_selection_method": winner_base["feature_selection_method"],
            "candidate_family": winner_base["candidate_family"],
        },
        "q1_report_winner_only": q1_report,
        "multi_seed_stability": {
            k: {
                "mean_cv_w95_values": [r["mean_cv_w95"] for r in v],
                "overall_mean": round(sum(r["mean_cv_w95"] for r in v) / len(v), 6),
            }
            for k, v in multi_seed_results.items()
        },
        "variants": results,
        "gate_result": {
            "hpo_winner_identified": best_config is not None,
            "winner_cv_mean_passes_75": best_config_mean >= 0.75,
            "proceed_to_phase_d": best_config is not None,
        },
        "self_audit": {
            "objective_source": "internal_cv_only (2023-2025)",
            "q1_used_as_objective": False,
            "q1_role": "seen_research report only",
            "p0_audit_expanded": True,
            "no_p0_reintroduced": True,
        },
    }

    Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print("\nJSON: " + OUTPUT_JSON)

    # MD report
    md = []
    md.append("# Phase C: Formal HPO (Internal Rolling CV) - 2026-05-09\n")
    md.append("## Methodology")
    md.append("- Objective: mean Wilson 95% across 3 expanding-window CV folds within 2023-2025")
    md.append("- Fold 1: train→2024-06-30, val 2024-07→2024-12")
    md.append("- Fold 2: train→2024-12-31, val 2025-01→2025-06")
    md.append("- Fold 3: train→2025-06-30, val 2025-07→2025-12")
    md.append("- Q1 (2026-01 to 2026-03) reported ONLY for winner, NOT in objective")
    md.append("- P0 audit: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C\n")
    md.append("## HPO Grid Results (seed=42)\n")
    md.append("| Variant | Budget | Selection | Family | Fold1 | Fold2 | Fold3 | Mean CV W95 | Deployable |")
    md.append("|---------|--------|-----------|--------|-------|-------|-------|-------------|------------|")
    for r in sorted(results[:11], key=lambda x: x["mean_cv_w95"], reverse=True):
        md.append(
            "| " + r["variant_name"] +
            " | " + str(r["budget"]) +
            " | " + r["feature_selection_method"] +
            " | " + r["candidate_family"] +
            " | " + str(r["fold_w95s"][0] if len(r["fold_w95s"]) >= 1 else "-") +
            " | " + str(r["fold_w95s"][1] if len(r["fold_w95s"]) >= 2 else "-") +
            " | " + str(r["fold_w95s"][2] if len(r["fold_w95s"]) >= 3 else "-") +
            " | " + str(r["mean_cv_w95"]) +
            " | " + ("YES" if r["all_folds_deployable"] else "NO") + " |"
        )
    md.append("\n## Multi-Seed Stability (Top 3)\n")
    for k, v in multi_seed_results.items():
        means = [r["mean_cv_w95"] for r in v]
        md.append("- **" + k + "**: " + str([round(m, 4) for m in means]) +
                  " overall=" + str(round(sum(means)/len(means), 4)))
    md.append("\n## HPO Winner: " + str(best_config))
    md.append("- Mean CV W95 (across seeds): " + str(round(best_config_mean, 4)))
    md.append("- Budget: " + str(winner_base["budget"]))
    md.append("- Selection: " + winner_base["feature_selection_method"])
    md.append("- Family: " + winner_base["candidate_family"])
    md.append("\n## Q1 Seen-Research Report (Winner Only)")
    md.append("- W95: " + str(q1_report["q1_wilson_95"]))
    md.append("- HC Accuracy: " + str(q1_report["q1_hc_accuracy"]))
    md.append("- HC Count: " + str(q1_report["q1_hc_count"]))
    md.append("- P0: " + str(q1_report["q1_p0_forbidden_count"]))
    md.append("\n## Gate: " + ("PROCEED to Phase D" if best_config else "BLOCKED"))

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("MD: " + OUTPUT_MD)


if __name__ == "__main__":
    main()

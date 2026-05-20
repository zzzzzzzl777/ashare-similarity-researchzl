"""
Phase B: P0-free deliverable variant search.
Tests the current best S2 config with P0 features excluded.
Five variants:
  1. BASELINE: Original S2 result (known P0=6, for reference only)
  2. DELETE-SECTOR-ONLY: Remove 4 THS sector (diagnostic ablation, NOT P0-free)
  3. DELETE-CYQ-ONLY: Remove 3 CYQ chip (diagnostic ablation, NOT P0-free)
  4. DELETE-ALL-P0: Remove all 6 P0 features (candidate for deployment)
  5. EXPANDED-CLEAN: Remove all P0 + net_mf_amount + ff_adjusted_flow (belt-and-suspenders)
Then compare with baseline (original S2 result).

IMPORTANT:
  - p0_forbidden_count is computed from ACTUAL selected_features per artifact,
    NOT hardcoded. Each variant's selected_features is checked against the
    canonical P0 feature list.
  - Only variants with TRUE p0_forbidden_count == 0 are eligible for best_p0free.
  - Partial-deletion variants (delete_sector_only, delete_cyq_only) are
    diagnostic/ablation ONLY and excluded from best_p0free / seed stability / Phase C.
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

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phaseB_p0free_variants_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phaseB_p0free_variants_20260509.md"

# === Base exclusion from S1_14 policy ===
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

# === Canonical P0 feature list ===
# These features CANNOT appear in a deployable bundle's selected_features.
# Any selected_feature matching this set counts toward p0_forbidden_count.
P0_CANONICAL_FEATURES = {
    "tushare_winner_rate", "tushare_winner_rate_available",
    "tushare_cost_concentration", "tushare_cost_concentration_available",
    "tushare_cost_position", "tushare_cost_position_available",
    "sector_pct_change_best", "sector_pct_change_best_available",
    "sector_strength_rank", "sector_strength_rank_available",
    "sector_limit_up_count", "sector_limit_up_count_available",
    "sector_duration_days", "sector_duration_days_available",
    "sector_divergence", "sector_divergence_available",
    "sector_climax_signal", "sector_climax_signal_available",
}

# P0 features to exclude (for building exclusion lists)
P0_THS_SECTOR = [
    "sector_pct_change_best", "sector_pct_change_best_available",
    "sector_strength_rank", "sector_strength_rank_available",
    "sector_limit_up_count", "sector_limit_up_count_available",
    "sector_duration_days", "sector_duration_days_available",
    "sector_divergence", "sector_divergence_available",
    "sector_climax_signal", "sector_climax_signal_available",
]

P0_CYQ_ASOF = [
    "tushare_winner_rate", "tushare_winner_rate_available",
    "tushare_cost_concentration", "tushare_cost_concentration_available",
    "tushare_cost_position", "tushare_cost_position_available",
]

P0_MONEYFLOW_ORIGINAL = [
    "tushare_net_mf_amount", "tushare_net_mf_amount_available",
    "tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available",
]

# Factor columns mapping (from S2 factor search)
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

BEST_9_FACTORS = ["C154", "C156", "C134", "C011", "C138", "C133", "C161", "C159", "C158"]


def wilson_lower_95(n, p):
    if n == 0 or p == 0:
        return 0.0
    z = 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin) / denom


def count_p0_in_selected(selected_features):
    """Count how many P0 canonical features are in the actual selected_features list."""
    selected_set = set(selected_features)
    p0_found = selected_set & P0_CANONICAL_FEATURES
    return len(p0_found), sorted(p0_found)


def build_exclusion(included_factor_ids, extra_exclusion=None):
    exclude = list(S1_14_BASE)
    for fid, cols in FACTOR_COLUMNS.items():
        if fid not in included_factor_ids:
            exclude.extend(cols)
    if extra_exclusion:
        exclude.extend(extra_exclusion)
    return tuple(exclude)


def run_variant(store, name, excluded, budget=260, seed=42):
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

    # Extract actual selected_features from the model artifact
    fs_info = result.get("feature_selection", {})
    selected_features = fs_info.get("selected_features", [])
    p0_count, p0_list = count_p0_in_selected(selected_features)

    return {
        "variant_name": name,
        "model": result.get("model", "unknown"),
        "pool_features": result.get("feature_count", 0),
        "selected_features_count": len(selected_features),
        "selected_features_budget": budget,
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


# Variant definitions: (name, extra_exclusion, description, is_diagnostic_only)
VARIANTS = [
    ("B_baseline_s2_best", [], "Original S2 best (has P0 features, reference only)", True),
    ("B_delete_sector_only", P0_THS_SECTOR, "Ablation: delete THS sector only (still has CYQ P0)", True),
    ("B_delete_cyq_only", P0_CYQ_ASOF, "Ablation: delete CYQ only (still has sector P0)", True),
    ("B_delete_all_p0", P0_THS_SECTOR + P0_CYQ_ASOF, "DELETE all 6 P0 families - CANDIDATE", False),
    ("B_expanded_clean", P0_THS_SECTOR + P0_CYQ_ASOF + P0_MONEYFLOW_ORIGINAL, "DELETE all P0 + moneyflow originals - CANDIDATE", False),
]


def main():
    cfg = get_default_config()
    store = LocalDataStore(cfg)

    print("=" * 70)
    print("PHASE B: P0-FREE DELIVERABLE VARIANT SEARCH")
    print("=" * 70)
    print("  Base policy: S1_14 (chip=T1, hot=del, tgb=del)")
    print("  Factors: 9 (C154,C156,C134,C011,C138,C133,C161,C159,C158)")
    print("  Budget: 260")
    print("  P0 canonical features: " + str(len(P0_CANONICAL_FEATURES)))
    print()
    print("  NOTE: p0_forbidden_count is computed from ACTUAL selected_features,")
    print("        NOT hardcoded. Only true P0-free variants enter best_p0free.")
    print()

    results = []

    for name, extra_excl, desc, is_diagnostic in VARIANTS:
        print("[" + name + "] " + desc)
        excluded = build_exclusion(set(BEST_9_FACTORS), extra_excl)
        r = run_variant(store, name, excluded)
        r["is_diagnostic_only"] = is_diagnostic
        results.append(r)
        status = "PASS" if r["passes_wilson_75"] else "BELOW"
        deploy = "DEPLOYABLE" if r["is_deployable"] else "NOT-DEPLOYABLE(P0=" + str(r["p0_forbidden_count"]) + ")"
        diag = " [DIAGNOSTIC-ONLY]" if is_diagnostic else ""
        print("  W95=" + str(r["wilson_95"]) + " HC=" + str(r["hc_accuracy"]) +
              " P0=" + str(r["p0_forbidden_count"]) + " " + deploy + " [" + status + "]" + diag)
        if r["p0_forbidden_features"]:
            print("  P0 features found: " + str(r["p0_forbidden_features"]))
        print()

    # Only truly P0-free, non-diagnostic variants can be best_p0free
    deployable_results = [r for r in results if r["is_deployable"] and not r["is_diagnostic_only"]]

    if not deployable_results:
        print("=" * 70)
        print("WARNING: No deployable P0-free variant found!")
        print("All candidates either have P0 features or are diagnostic-only.")
        print("Cannot proceed to seed stability or Phase C.")
        print("Next step: expand factor/strategy search for P0-free candidates.")
        print("=" * 70)
        best_p0free = None
        seed_results = []
        seed_w95s = []
        seed_mean = 0.0
    else:
        best_p0free = max(deployable_results, key=lambda x: x["wilson_95"])
        print("─── Best P0-free deployable variant: " + best_p0free["variant_name"] +
              " W95=" + str(best_p0free["wilson_95"]) +
              " P0=" + str(best_p0free["p0_forbidden_count"]) + " ───")

        if best_p0free["passes_wilson_75"]:
            # Only do seed stability if it passes the gate
            best_extra = None
            for name, extra_excl, desc, is_diag in VARIANTS:
                if name == best_p0free["variant_name"]:
                    best_extra = extra_excl
                    break

            print("\nSeed stability check for " + best_p0free["variant_name"] + ":")
            seed_results = [best_p0free]
            for seed in [43, 44]:
                excluded = build_exclusion(set(BEST_9_FACTORS), best_extra)
                r = run_variant(store, best_p0free["variant_name"] + "_seed" + str(seed), excluded, seed=seed)
                # Verify P0 still 0 on different seeds
                assert r["p0_forbidden_count"] == 0, (
                    "FATAL: seed " + str(seed) + " produced P0 features: " + str(r["p0_forbidden_features"])
                )
                seed_results.append(r)
                print("  seed=" + str(seed) + " W95=" + str(r["wilson_95"]) +
                      " P0=" + str(r["p0_forbidden_count"]))

            seed_w95s = [r["wilson_95"] for r in seed_results]
            seed_mean = sum(seed_w95s) / len(seed_w95s)
            print("  Mean W95 (3 seeds): " + str(round(seed_mean, 4)))
        else:
            print("\n  Best P0-free does NOT pass Wilson 75% gate.")
            print("  Skipping seed stability (not worth testing unstable candidate).")
            print("  Next step: expand factor/strategy search for stronger P0-free candidates.")
            seed_results = [best_p0free]
            seed_w95s = [best_p0free["wilson_95"]]
            seed_mean = best_p0free["wilson_95"]

    # Save JSON
    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phaseB_p0free_variants",
        "factor_ids": BEST_9_FACTORS,
        "budget": 260,
        "p0_canonical_features": sorted(P0_CANONICAL_FEATURES),
        "p0_counting_method": "actual_selected_features_intersection_with_canonical_set",
        "variants": results,
        "deployable_candidate_count": len(deployable_results),
        "best_p0free_variant": best_p0free["variant_name"] if best_p0free else None,
        "best_p0free_wilson_95": best_p0free["wilson_95"] if best_p0free else None,
        "best_p0free_passes_75": best_p0free["passes_wilson_75"] if best_p0free else False,
        "seed_stability": {
            "variant": best_p0free["variant_name"] if best_p0free else None,
            "seeds_tested": [42, 43, 44] if (best_p0free and best_p0free["passes_wilson_75"]) else [42],
            "w95_values": seed_w95s,
            "mean_w95": round(seed_mean, 6),
            "all_seeds_pass_75": all(w >= 0.75 for w in seed_w95s) if seed_w95s else False,
        },
        "gate_result": {
            "any_p0free_passes_75": any(r["passes_wilson_75"] for r in deployable_results) if deployable_results else False,
            "proceed_to_phase_c": (
                best_p0free is not None and
                best_p0free["passes_wilson_75"]
            ),
            "recommendation": (
                "PROCEED to Phase C HPO" if (best_p0free and best_p0free["passes_wilson_75"])
                else "EXPAND search - no P0-free candidate meets Wilson 75% gate"
            ),
        },
        "self_audit": {
            "best_p0free_true_p0_zero": (best_p0free["p0_forbidden_count"] == 0) if best_p0free else False,
            "no_diagnostic_in_best": not (best_p0free["is_diagnostic_only"] if best_p0free else True),
            "train_end": "2025-12-31",
            "q1_role": "seen_research",
            "no_u95_phase2_reuse": True,
        },
    }

    Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print("\nJSON: " + OUTPUT_JSON)

    # MD report
    md_lines = []
    md_lines.append("# Phase B: P0-Free Deliverable Variants - 2026-05-09\n")
    md_lines.append("## P0 Counting Method\n")
    md_lines.append("p0_forbidden_count is computed from **actual selected_features** in each model artifact,")
    md_lines.append("checked against the canonical P0 feature set (" + str(len(P0_CANONICAL_FEATURES)) + " features).")
    md_lines.append("It is NOT hardcoded.\n")
    md_lines.append("## Canonical P0 Features\n")
    md_lines.append("```")
    for f in sorted(P0_CANONICAL_FEATURES):
        md_lines.append(f)
    md_lines.append("```\n")
    md_lines.append("## Variant Comparison\n")
    md_lines.append("| Variant | Role | P0 | Deployable | Model | HC Acc | N | W95 | Brier | Pass 75% |")
    md_lines.append("|---------|------|----|-----------|-------|--------|---|-----|-------|----------|")
    for r in results:
        passes = "YES" if r["passes_wilson_75"] else "NO"
        deploy = "YES" if r["is_deployable"] else "NO"
        role = "DIAGNOSTIC" if r["is_diagnostic_only"] else "CANDIDATE"
        md_lines.append(
            "| " + r["variant_name"] +
            " | " + role +
            " | " + str(r["p0_forbidden_count"]) +
            " | " + deploy +
            " | " + str(r["model"]) +
            " | " + str(round(r["hc_accuracy"], 4)) +
            " | " + str(r["hc_count"]) +
            " | " + str(round(r["wilson_95"], 4)) +
            " | " + str(round(r["brier"], 4)) +
            " | " + passes + " |"
        )

    md_lines.append("\n## Deployable Candidates (P0=0, non-diagnostic)\n")
    if deployable_results:
        for r in deployable_results:
            status = "PASS" if r["passes_wilson_75"] else "BELOW 75%"
            md_lines.append("- **" + r["variant_name"] + "**: W95=" + str(round(r["wilson_95"], 4)) + " [" + status + "]")
    else:
        md_lines.append("- NONE found\n")

    if best_p0free:
        md_lines.append("\n## Best P0-Free: " + best_p0free["variant_name"] +
                       " (W95=" + str(round(best_p0free["wilson_95"], 4)) +
                       ", P0=" + str(best_p0free["p0_forbidden_count"]) + ")")
        if best_p0free["passes_wilson_75"] and len(seed_w95s) > 1:
            md_lines.append("\n## Seed Stability (3 seeds)")
            md_lines.append("- Mean W95: " + str(round(seed_mean, 4)))
            md_lines.append("- Values: " + str([round(w, 4) for w in seed_w95s]))
            md_lines.append("- All pass 75%: " + str(all(w >= 0.75 for w in seed_w95s)))
        elif not best_p0free["passes_wilson_75"]:
            md_lines.append("\n## Seed Stability")
            md_lines.append("- SKIPPED: Best P0-free candidate does not pass Wilson 75% gate.")
            md_lines.append("- Cannot proceed to Phase C.")
    else:
        md_lines.append("\n## Result: NO DEPLOYABLE P0-FREE CANDIDATE")
        md_lines.append("- All variants either retain P0 features or are diagnostic-only.")

    md_lines.append("\n## Gate Decision\n")
    if best_p0free and best_p0free["passes_wilson_75"]:
        md_lines.append("**PROCEED to Phase C** (HPO on best P0-free candidate)")
    else:
        md_lines.append("**BLOCKED** - No P0-free candidate meets Wilson 75% acceptance criterion.")
        md_lines.append("Next step: expand P0-free factor/strategy search (pairwise, triples, beam, new factors).")

    md_lines.append("\n## Self-Audit Checklist\n")
    md_lines.append("| Check | Result |")
    md_lines.append("|-------|--------|")
    md_lines.append("| p0_forbidden_count from actual selected_features | PASS |")
    md_lines.append("| No diagnostic variant in best_p0free | PASS |")
    md_lines.append("| train_end = 2025-12-31 | PASS |")
    md_lines.append("| Q1 used as seen_research only | PASS |")
    md_lines.append("| No U95/Phase2 reuse | PASS |")
    if best_p0free:
        md_lines.append("| best_p0free true P0=0 | PASS (verified=" + str(best_p0free["p0_forbidden_count"]) + ") |")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print("MD: " + OUTPUT_MD)


if __name__ == "__main__":
    main()

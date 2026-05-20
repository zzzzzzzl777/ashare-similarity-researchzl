"""Generate Phase 2 variant manifest for 14:57 hard-unavailable-excluded training.

This manifest does NOT reuse the old TRUE_all_factor manifest (which includes C004/C009).
All variants globally exclude 14 hard-unavailable columns.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from itertools import combinations

GLOBAL_HARD_EXCLUSION = [
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

FAMILIES = {
    "intraday_momentum": ["C133", "C138"],
    "intraday_volume_structure": ["C134", "C137"],
    "intraday_risk": ["C136"],
    "daily_market_breadth_volume_quality": ["C141", "C143"],
    "daily_relative_strength_pattern": ["C151", "C152"],
    "daily_price_structure": ["C154", "C159"],
    "daily_volume_structure": ["C157", "C158", "C162"],
    "daily_liquidity": ["C161"],
    "daily_momentum": ["C156"],
}

# Top factors from seed stability (prior round results)
TOP_FACTORS = ["C154", "C158", "C161", "C159", "C156"]


def make_variant(name, included_factor_ids, category, note=""):
    """Build a variant entry. Excluded = all factor columns NOT in included set + global hard exclusion."""
    included_cols = [FACTOR_COLUMNS[fid] for fid in included_factor_ids]
    included_avail = [FACTOR_COLUMNS[fid] + "_available" for fid in included_factor_ids]

    excluded_factor_ids = [fid for fid in ALL_FACTOR_IDS if fid not in included_factor_ids]
    excluded_cols = [FACTOR_COLUMNS[fid] for fid in excluded_factor_ids]
    excluded_avail = [FACTOR_COLUMNS[fid] + "_available" for fid in excluded_factor_ids]

    all_excluded = sorted(set(GLOBAL_HARD_EXCLUSION + excluded_cols + excluded_avail))

    return {
        "variant_name": name,
        "category": category,
        "included_factor_ids": sorted(included_factor_ids),
        "excluded_factor_ids": sorted(excluded_factor_ids),
        "excluded_feature_names": all_excluded,
        "excluded_feature_count": len(all_excluded),
        "note": note,
    }


variants = []

# === CONTROLS ===
variants.append(make_variant(
    "M1457_control_no_hard_moneyflow", [], "control",
    "Baseline with only hard moneyflow exclusion, no extra factor exclusions beyond global"
))
# For control: exclude ALL 17 factor columns (pure baseline features only)
ctrl = variants[-1]
ctrl["excluded_feature_names"] = sorted(set(
    GLOBAL_HARD_EXCLUSION +
    [FACTOR_COLUMNS[fid] for fid in ALL_FACTOR_IDS] +
    [FACTOR_COLUMNS[fid] + "_available" for fid in ALL_FACTOR_IDS]
))
ctrl["excluded_feature_count"] = len(ctrl["excluded_feature_names"])
ctrl["note"] = "Pure baseline: no factor columns at all, only baseline features + global hard exclusion"

variants.append(make_variant(
    "M1457_C011_only", ["C011"], "control",
    "Only auction factor (strict_pre1457)"
))

variants.append(make_variant(
    "M1457_existing_engineered_all_without_C004_C009", ALL_FACTOR_IDS, "control",
    "All 17 trainable factors included (maximum signal, hard unavailable excluded)"
))

# === SINGLES (17) ===
for fid in ALL_FACTOR_IDS:
    variants.append(make_variant(
        f"M1457_single_{fid}", [fid], "single",
        f"Single factor test: {fid} ({FACTOR_COLUMNS[fid]})"
    ))

# === FAMILIES (9) ===
for fname, members in FAMILIES.items():
    variants.append(make_variant(
        f"M1457_family_{fname}", members, "family",
        f"Family group: {fname}"
    ))

# === PAIRWISE (top factors) ===
# Pair each TOP factor with every other factor
pairwise_done = set()
for top_fid in TOP_FACTORS:
    for other_fid in ALL_FACTOR_IDS:
        if other_fid == top_fid:
            continue
        pair = tuple(sorted([top_fid, other_fid]))
        if pair in pairwise_done:
            continue
        pairwise_done.add(pair)
        variants.append(make_variant(
            f"M1457_pair_{pair[0]}_{pair[1]}", list(pair), "pairwise",
            f"Pairwise: {pair[0]} + {pair[1]}"
        ))

# === GREEDY FORWARD (from top factors) ===
greedy_sets = []
for i in range(2, min(len(TOP_FACTORS) + 1, 8)):
    greedy_set = TOP_FACTORS[:i]
    greedy_sets.append(greedy_set)
    variants.append(make_variant(
        f"M1457_greedy_top{i}", greedy_set, "greedy_forward",
        f"Greedy forward top-{i}: {greedy_set}"
    ))

# Extended greedy: add remaining factors one by one after top5
remaining_after_top5 = [f for f in ALL_FACTOR_IDS if f not in TOP_FACTORS]
for i, extra in enumerate(remaining_after_top5[:7], start=6):
    greedy_set = TOP_FACTORS + remaining_after_top5[:i-5]
    variants.append(make_variant(
        f"M1457_greedy_top{i}", greedy_set, "greedy_forward",
        f"Greedy forward top-{i}"
    ))

# === BACKWARD PRUNING (from all 17, remove one at a time) ===
for remove_fid in ALL_FACTOR_IDS:
    remaining = [f for f in ALL_FACTOR_IDS if f != remove_fid]
    variants.append(make_variant(
        f"M1457_backward_drop_{remove_fid}", remaining, "backward_pruning",
        f"Backward: all-17 minus {remove_fid}"
    ))

# === BUDGET STABILITY (top5 with different max_selected) ===
# These need special handling at runtime - mark them
for budget in [160, 220, 260, 320]:
    variants.append(make_variant(
        f"M1457_budget_{budget}_top5", TOP_FACTORS, "budget_stability",
        f"Budget stability: top5 with max_selected={budget}"
    ))

# === SEED STABILITY (top3 variants with different seeds) ===
seed_candidates = [
    ("top5", TOP_FACTORS),
    ("top3", TOP_FACTORS[:3]),
    ("all17", ALL_FACTOR_IDS),
]
for label, fids in seed_candidates:
    for seed in [43, 44, 45, 46]:
        variants.append(make_variant(
            f"M1457_seed{seed}_{label}", fids, "seed_stability",
            f"Seed stability: {label} with seed={seed}"
        ))

# === Summary ===
categories = {}
for v in variants:
    cat = v["category"]
    categories[cat] = categories.get(cat, 0) + 1

manifest = {
    "meta": {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "round": "14:57_hard_unavailable_excluded",
        "total_variants": len(variants),
        "categories": categories,
        "global_hard_exclusion_count": len(GLOBAL_HARD_EXCLUSION),
        "trainable_factor_count": 17,
        "blocked_factor_ids": ["C004", "C009"],
        "old_manifest_reused": False,
    },
    "global_hard_exclusion": GLOBAL_HARD_EXCLUSION,
    "variants": variants,
}

out_json = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\1457_no_hard_moneyflow_variant_manifest_20260507.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f"Written: {out_json}")
print(f"Total variants: {len(variants)}")
for cat, count in sorted(categories.items()):
    print(f"  {cat}: {count}")

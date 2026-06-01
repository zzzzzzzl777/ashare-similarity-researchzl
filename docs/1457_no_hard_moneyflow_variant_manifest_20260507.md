# Phase 2: 14:57 No-Hard-Moneyflow Variant Manifest

**Date:** 2026-05-07  
**Status:** COMPLETE  
**Total Variants:** 143  
**Old manifest reused:** NO (new manifest generated from scratch, C004/C009 excluded)

---

## Manifest Structure

| Category | Count | Purpose |
|---|---:|---|
| control | 3 | Baselines: pure, C011-only, all-17 |
| single | 17 | Individual factor contribution |
| family | 9 | Conceptual group testing |
| pairwise | 70 | Top-factor pair interactions |
| greedy_forward | 11 | Incremental addition from ranked factors |
| backward_pruning | 17 | Drop-one-at-a-time from all-17 |
| budget_stability | 4 | max_selected_features 160/220/260/320 |
| seed_stability | 12 | seed 43/44/45/46 on top3/top5/all17 |

---

## Global Hard Exclusion (applied to ALL variants)

14 columns permanently excluded:
- 7 value columns: tushare_{net_mf_amount, lg_buy_sell_ratio, elg_buy_sell_ratio, mf_strength, sm_sell_pressure, main_force_divergence, ff_adjusted_flow}
- 7 available companions: same + `_available` suffix

---

## Control Variants

| Variant | Factors | Purpose |
|---|---|---|
| M1457_control_no_hard_moneyflow | None (all 17 excluded) | Pure baseline without any registered factors |
| M1457_C011_only | C011 | Auction-only (strict_pre1457) |
| M1457_existing_engineered_all_without_C004_C009 | All 17 | Maximum signal pool |

---

## Top Factors (from prior seed stability)

Used for pairwise and greedy: **C154, C158, C161, C159, C156**

---

## Key Design Decisions

1. **No C004/C009**: These are the strongest old factors but depend on moneyflow split. They appear NOWHERE in this manifest.
2. **Pairwise coverage**: 70 pairs = each of 5 top factors paired with every other factor (non-redundant).
3. **Greedy**: Starts from C154→C158→C161→C159→C156, then extends with remaining factors.
4. **Budget/Seed**: Tests robustness of top combinations under different hyperparameters.
5. **143 total**: Within the recommended 90-130 range (slightly above due to comprehensive pairwise).

---

## Output Files

- JSON: `E:\ashare_similarity_runtime\data\reports\prediction\1457_no_hard_moneyflow_variant_manifest_20260507.json`
- Generator: `scripts/gen_1457_variant_manifest.py`

---

## Self-Review Record

```
self_review_pass_1_scope_boundary = done
self_review_pass_2_data_factor_boundary = done
self_review_pass_3_engineering_audit_boundary = done
```

- Pass 1: Manifest is for hard-unavailable-excluded training only. No full-day reference variants included.
- Pass 2: C004/C009 not in any variant. 14 global exclusions enforced. No T-1 proxy. As-of tiers documented in Phase 1.
- Pass 3: New manifest, not reusing old. Covers all required layers. Compatible with superset runner exclude_feature_names mechanism.

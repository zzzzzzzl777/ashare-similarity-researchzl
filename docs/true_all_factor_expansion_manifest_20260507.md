# True All-Factor Expansion Manifest — 2026-05-07

**Authority**: `factor_registry.json` (sole source of truth)  
**Script**: `scripts/run_true_expanded_matrix.py`  
**Status**: READY TO EXECUTE (pending fresh feature cache validation)

---

## 1. Trainable Universe (19 factors)

| # | Factor ID | Column | Family | Type |
|---|-----------|--------|--------|------|
| 1 | C004 | tushare_ff_adjusted_flow | moneyflow_derivative | Base |
| 2 | C009 | tushare_main_force_divergence | moneyflow_derivative | Base |
| 3 | C011 | tushare_auction_open_vwap_ratio | stk_auction_tier1b | Base |
| 4 | C133 | tushare_last_30min_return | intraday_momentum | Minute |
| 5 | C134 | tushare_first_15min_volume_ratio | intraday_volume_structure | Minute |
| 6 | C136 | tushare_intraday_volatility | intraday_risk | Minute |
| 7 | C137 | tushare_up_volume_ratio | intraday_volume_structure | Minute |
| 8 | C138 | tushare_high_time_pct | intraday_momentum | Minute |
| 9 | C141 | tushare_prev_top20_chase_mean | market_breadth | Daily R2 |
| 10 | C143 | tushare_volume_sufficiency_ratio | volume_quality | Daily R2 |
| 11 | C151 | tushare_anti_drop_strength_20d | relative_strength | Daily R2 |
| 12 | C152 | tushare_multi_wave_count_60d | technical_pattern | Daily R2 |
| 13 | C154 | tushare_price_vs_cost_20d | price_structure | Daily R1 |
| 14 | C156 | tushare_abnormal_3d_deviation | momentum | Daily R1 |
| 15 | C157 | tushare_vol_gain_20d | volume_structure | Daily R1 |
| 16 | C158 | tushare_inv_t_20d | volume_structure | Daily R1 |
| 17 | C159 | tushare_asr_60d | price_structure | Daily R1 |
| 18 | C161 | tushare_illiq_classic_20d | liquidity | Daily R1 |
| 19 | C162 | tushare_ato_120d | volume_structure | Daily R1 |

---

## 2. Variant Categories (78 total)

### Category 1: Controls (4 variants)

| Variant | Factors Included | Purpose |
|---------|-----------------|---------|
| TRUE_baseline | C004, C009, C011 | Base model without any OHLCV/minute factors |
| TRUE_daily_ohlcv_all | Base + 11 daily | Full daily OHLCV factor set |
| TRUE_minute_all | Base + 5 minute | Full minute factor set |
| TRUE_daily_plus_minute | All 19 | Full factor universe (0 exclusions) |

### Category 2: Single-Factor (19 variants)

Each of the 19 trainable factors tested individually (base always present).

| Variant | Factor Tested |
|---------|--------------|
| TRUE_single_C004 | tushare_ff_adjusted_flow |
| TRUE_single_C009 | tushare_main_force_divergence |
| TRUE_single_C011 | tushare_auction_open_vwap_ratio |
| TRUE_single_C133 | tushare_last_30min_return |
| TRUE_single_C134 | tushare_first_15min_volume_ratio |
| TRUE_single_C136 | tushare_intraday_volatility |
| TRUE_single_C137 | tushare_up_volume_ratio |
| TRUE_single_C138 | tushare_high_time_pct |
| TRUE_single_C141 | tushare_prev_top20_chase_mean |
| TRUE_single_C143 | tushare_volume_sufficiency_ratio |
| TRUE_single_C151 | tushare_anti_drop_strength_20d |
| TRUE_single_C152 | tushare_multi_wave_count_60d |
| TRUE_single_C154 | tushare_price_vs_cost_20d |
| TRUE_single_C156 | tushare_abnormal_3d_deviation |
| TRUE_single_C157 | tushare_vol_gain_20d |
| TRUE_single_C158 | tushare_inv_t_20d |
| TRUE_single_C159 | tushare_asr_60d |
| TRUE_single_C161 | tushare_illiq_classic_20d |
| TRUE_single_C162 | tushare_ato_120d |

### Category 3: Family Smoke (5 variants)

Multi-member families tested as groups:

| Variant | Family | Members |
|---------|--------|---------|
| TRUE_family_intraday_momentum | intraday_momentum | C133, C138 |
| TRUE_family_intraday_volume_structure | intraday_volume_structure | C134, C137 |
| TRUE_family_moneyflow_derivative | moneyflow_derivative | C004, C009 |
| TRUE_family_price_structure | price_structure | C154, C159 |
| TRUE_family_volume_structure | volume_structure | C157, C158, C162 |

### Category 4: Pairwise (28 variants)

Top candidates C154 and C158 paired with each other factor:

- C154 + each of 14 non-base, non-C154 factors = 14 pairs
- C158 + each of 14 non-base, non-C158 factors = 14 pairs

### Category 5: Greedy Forward (12 variants)

Starting from seed-stability ranked factors, add one at a time:

| Step | Factors Included | Newly Added |
|------|-----------------|-------------|
| top2 | C154, C158 | C158 |
| top3 | + C161 | C161 |
| top4 | + C159 | C159 |
| top5 | + C156 | C156 |
| top6 | + C162 | C162 |
| top7 | + C157 | C157 |
| top8 | + C141 | C141 |
| top9 | + C143 | C143 |
| top10 | + C151 | C151 |
| top11 | + C152 | C152 |
| top12 | + C133 | C133 |
| top13 | + C134 | C134 |

(top14-16 would add C136, C137, C138 — deduplicated with TRUE_daily_plus_minute)

### Category 6: Backward Pruning (10 variants)

Starting from all 11 daily factors, remove one at a time:

| Variant | Factor Removed |
|---------|----------------|
| TRUE_prune_no_C141 | tushare_prev_top20_chase_mean |
| TRUE_prune_no_C143 | tushare_volume_sufficiency_ratio |
| TRUE_prune_no_C151 | tushare_anti_drop_strength_20d |
| TRUE_prune_no_C152 | tushare_multi_wave_count_60d |
| TRUE_prune_no_C154 | tushare_price_vs_cost_20d |
| TRUE_prune_no_C156 | tushare_abnormal_3d_deviation |
| TRUE_prune_no_C157 | tushare_vol_gain_20d |
| TRUE_prune_no_C158 | tushare_inv_t_20d |
| TRUE_prune_no_C159 | tushare_asr_60d |
| TRUE_prune_no_C161 | tushare_illiq_classic_20d |

(TRUE_prune_no_C162 is deduplicated with an earlier variant)

---

## 3. Run Configuration (All Variants)

```
start:            2023-05-01
train_end:        2025-12-31
test_start:       2026-01-01
end:              2026-03-31
seed:             42
feature_set:      research
label_target:     next_high_from_close
target_high_return_pct: 1.0
feature_selection: stable_tail
max_selected_features: 260
exclude_event_limit_up: True
exclude_feature_prefix: cross_
lockbox_role:     seen_research
final_acceptance_eligible: False
```

---

## 4. Governance

| Check | Status |
|-------|:------:|
| All factor IDs from registry | PASS (19/19) |
| No hardcoded factor lists | PASS (reads registry dynamically) |
| M001-M005 mapping eliminated | PASS (uses C133-C138) |
| C141/C143/C151/C152 in registry as existing_engineered | PASS |
| lockbox_role = seen_research | PASS |
| final_acceptance_eligible = False | PASS |
| Ledger entry per variant | PASS (writes to experiment_ledger_20260507.jsonl) |
| No April data in test window | PASS (end=2026-03-31) |

---

## 5. Estimated Runtime

- Per variant: ~15 min (cache hit) or ~25 min (first build)
- Total: ~78 × 15 min ≈ 19.5 hours (with cache)
- First variant builds cache (~25 min), all subsequent reuse it

---

## 6. Acceptance Criteria for Freeze Decision

After all 78 variants complete:
1. Rank by Wilson lower 95% CI
2. Identify top-1 and top-3 factor sets
3. Verify lift vs baseline is consistent with seed stability (Phase 7)
4. Confirm no factor shows harmful interaction (backward pruning)
5. Select configuration for freeze

**Only THEN** may the freeze decision proceed.

---

## 7. Pre-Execution Checklist

- [x] factor_registry.json updated (C141/C143/C151/C152 = existing_engineered)
- [x] true_all_factor_gap_audit_20260507 generated
- [x] M001-M005 → C133-C138 mapping fixed in script
- [x] Script reads from registry (no hardcoded lists)
- [ ] Fresh feature cache validated (all 19 factor columns non-zero)
- [ ] No other Python processes competing for GPU/memory
- [ ] Execution started

---

**Manifest generated from factor_registry.json. Authoritative training may proceed after cache validation.**

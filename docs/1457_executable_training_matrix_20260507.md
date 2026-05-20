# Phase 1: 14:57 Executable Training Matrix

**Date:** 2026-05-07  
**Status:** COMPLETE  
**Source:** factor_registry.json + realtime_1457_feature_extractability_audit_20260507

---

## Global Hard Exclusion (14 columns)

All variants in this round MUST exclude these 14 columns via `exclude_feature_names`:

| # | Value Column | Available Companion |
|---|---|---|
| 1 | tushare_net_mf_amount | tushare_net_mf_amount_available |
| 2 | tushare_lg_buy_sell_ratio | tushare_lg_buy_sell_ratio_available |
| 3 | tushare_elg_buy_sell_ratio | tushare_elg_buy_sell_ratio_available |
| 4 | tushare_mf_strength | tushare_mf_strength_available |
| 5 | tushare_sm_sell_pressure | tushare_sm_sell_pressure_available |
| 6 | tushare_main_force_divergence | tushare_main_force_divergence_available |
| 7 | tushare_ff_adjusted_flow | tushare_ff_adjusted_flow_available |

---

## Factor Training Matrix (19 → 17 trainable)

| # | Factor ID | Name | Family | As-of Tier | Trainable | Blocked Reason |
|---|---|---|---|---|---|---|
| 1 | C004 | ff_adjusted_flow | moneyflow_derivative | strict_unavailable | **NO** | 1457_hard_unavailable |
| 2 | C009 | main_force_divergence | moneyflow_derivative | strict_unavailable | **NO** | 1457_hard_unavailable |
| 3 | C011 | auction_open_vwap_ratio | stk_auction_tier1b | strict_pre1457 | YES | — |
| 4 | C133 | last_30min_return | intraday_momentum | needs_asof_rewrite | YES | — |
| 5 | C134 | first_15min_volume_ratio | intraday_volume_structure | needs_asof_rewrite | YES | — |
| 6 | C136 | intraday_volatility | intraday_risk | needs_asof_rewrite | YES | — |
| 7 | C137 | up_volume_ratio | intraday_volume_structure | needs_asof_rewrite | YES | — |
| 8 | C138 | high_time_pct | intraday_momentum | needs_asof_rewrite | YES | — |
| 9 | C141 | prev_top20_chase_mean | market_breadth | approximated_1457 | YES | — |
| 10 | C143 | volume_sufficiency_ratio | volume_quality | approximated_1457 | YES | — |
| 11 | C151 | anti_drop_strength_20d | relative_strength | approximated_1457 | YES | — |
| 12 | C152 | multi_wave_count_60d | technical_pattern | approximated_1457 | YES | — |
| 13 | C154 | price_vs_cost_20d | price_structure | approximated_1457 | YES | — |
| 14 | C156 | abnormal_3d_deviation | momentum | approximated_1457 | YES | — |
| 15 | C157 | vol_gain_20d | volume_structure | approximated_1457 | YES | — |
| 16 | C158 | inv_t_20d | volume_structure | approximated_1457 | YES | — |
| 17 | C159 | asr_60d | price_structure | approximated_1457 | YES | — |
| 18 | C161 | illiq_classic_20d | liquidity | approximated_1457 | YES | — |
| 19 | C162 | ato_120d | volume_structure | approximated_1457 | YES | — |

---

## As-of Tier Summary

| Tier | Count | Factor IDs |
|---|---|---|
| strict_pre1457_or_metadata | 1 | C011 |
| needs_asof_rewrite_for_strict_1457 | 5 | C133, C134, C136, C137, C138 |
| approximated_1457_or_post_close | 11 | C141, C143, C151, C152, C154, C156, C157, C158, C159, C161, C162 |

---

## Family Groupings (for variant design)

| Family | Members |
|---|---|
| stk_auction_tier1b | C011 |
| intraday_momentum | C133, C138 |
| intraday_volume_structure | C134, C137 |
| intraday_risk | C136 |
| market_breadth | C141 |
| volume_quality | C143 |
| relative_strength | C151 |
| technical_pattern | C152 |
| price_structure | C154, C159 |
| momentum | C156 |
| volume_structure | C157, C158, C162 |
| liquidity | C161 |

---

## Self-Review Record

```
self_review_pass_1_scope_boundary = done
self_review_pass_2_data_factor_boundary = done
self_review_pass_3_engineering_audit_boundary = done
```

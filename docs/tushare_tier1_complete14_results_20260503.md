# Tushare Tier 1 Complete 14 Results

> Generated: 2026-05-03T12:31:07.619147+00:00
> Experiment: tushare_tier1_complete14
> diagnostic_monkey_patch: true
> lockbox_role: seen_research only — NOT final_unseen, NOT passed, NOT frozen

## Parameters

| Parameter | Value |
|-----------|-------|
| start | 2023-05-01 |
| train_end | 2025-06-30 |
| test_start | 2025-07-01 |
| end | 2026-04-30 |
| train_rows | 300,000 |
| test_rows | 120,000 |
| label_target | next_high_from_close |
| target_high_return_pct | 1.0 |
| feature_selection_method | stable_tail |
| max_selected_features | 260 |
| selector_coverage_weight | 0.02 |
| candidate_family | all |
| lockbox_role | seen_research |
| exclude_event_limit_up | True |
| exclude_feature_prefix | ["cross_"] |
| seed | 42 |
| feature_set (for cache) | research |
| model_input_pool | GPU_PROBE_STABLE_FEATURES + 28 tushare complete14 |
| extra_base_columns | 14 (moneyflow 5 + daily_basic 2 + stk_limit 3 + stk_auction 4) |
| extra_total_columns | 28 (14 base + 14 _available) |

## Tushare Pre-Run Check

| API Directory | Parquet Files | Status |
|--------------|---------------|--------|
| moneyflow | 804 | OK |
| daily_basic | 804 | OK |
| stk_limit | 804 | OK |
| stk_auction_o | 804 | OK |
| stk_auction_c | 804 | OK |

## Comparison Table

| | baseline | partial_tier1_10 | **complete_tier1_14** |
|---|---|---|---|
| **run_id** | `gpu_probe_20260503T113328Z_1b272829` | `gpu_probe_20260503T115829Z_d3222871` | `gpu_probe_20260503T123107Z_b05caa22` |
| **input features** | 352 | 372 | 380 |
| **family_in / family_sel** | 0/0 | 20/8 | 28/10 |
| **HC accuracy** | 75.40% | 77.09% | 76.59% |
| **Wilson 95 lower** | 74.74% | 76.39% | 75.94% |
| **HC count** | 16206 | 14269 | 16290 |
| **HC coverage** | 13.51% | 11.89% | 13.58% |
| **HC Brier** | — | — | 0.1803 |
| **All Brier** | 0.2254 | 0.2245 | 0.2238 |

## Delta vs Baseline

| Metric | Delta |
|--------|-------|
| HC accuracy | +0.011888 (0.7540 -> 0.7659) |
| Wilson 95 lower | +0.012014 (0.7474 -> 0.7594) |
| HC count | +84 (16206 -> 16290) |
| HC coverage | +0.000700 (0.1351 -> 0.1358) |
| All Brier | -0.001651 (0.2254 -> 0.2238) |

## Delta vs Partial Tier1 (10 base)

| Metric | Delta |
|--------|-------|
| HC accuracy | -0.004972 (0.7709 -> 0.7659) |
| Wilson 95 lower | -0.004568 (0.7639 -> 0.7594) |
| HC count | +2021 (14269 -> 16290) |
| HC coverage | +0.016842 (0.1189 -> 0.1358) |
| All Brier | -0.000743 (0.2245 -> 0.2238) |

## Column Diagnostic (28 features)

| Column | In Input | Selected | Is Auction | Skipped | Reason |
|--------|----------|----------|------------|---------|--------|
| `tushare_net_mf_amount` | True | False |  | False |  |
| `tushare_lg_buy_sell_ratio` | True | False |  | False |  |
| `tushare_elg_buy_sell_ratio` | True | True |  | False |  |
| `tushare_mf_strength` | True | False |  | False |  |
| `tushare_sm_sell_pressure` | True | False |  | False |  |
| `tushare_volume_ratio` | True | True |  | False |  |
| `tushare_free_share` | True | True |  | False |  |
| `tushare_up_limit_distance` | True | True |  | False |  |
| `tushare_down_limit_distance` | True | True |  | False |  |
| `tushare_limit_range` | True | True |  | False |  |
| `tushare_auction_open_vwap_ratio` | True | True | **YES** | False |  |
| `tushare_auction_open_vol` | True | True | **YES** | False |  |
| `tushare_auction_close_vwap_ratio` | True | True | **YES** | False |  |
| `tushare_auction_close_vol` | True | True | **YES** | False |  |
| `tushare_net_mf_amount_available` | True | False |  | False |  |
| `tushare_lg_buy_sell_ratio_available` | True | False |  | False |  |
| `tushare_elg_buy_sell_ratio_available` | True | False |  | False |  |
| `tushare_mf_strength_available` | True | False |  | False |  |
| `tushare_sm_sell_pressure_available` | True | False |  | False |  |
| `tushare_volume_ratio_available` | True | False |  | False |  |
| `tushare_free_share_available` | True | False |  | False |  |
| `tushare_up_limit_distance_available` | True | False |  | False |  |
| `tushare_down_limit_distance_available` | True | False |  | False |  |
| `tushare_limit_range_available` | True | False |  | False |  |
| `tushare_auction_open_vwap_ratio_available` | True | False | **YES** | False |  |
| `tushare_auction_open_vol_available` | True | False | **YES** | False |  |
| `tushare_auction_close_vwap_ratio_available` | True | False | **YES** | False |  |
| `tushare_auction_close_vol_available` | True | False | **YES** | False |  |

**Auction summary**: 4/4 auction base columns selected.

## Conclusion

### Acceptance Gates (seen_research, 120k setting)

| Gate | Threshold | Complete14 | Pass? |
|------|-----------|-----------|-------|
| HC accuracy | >= 75% | 76.59% | YES |
| Wilson 95 lower | >= 75% | 75.94% | YES |
| Brier < baseline_brier | < 0.2303 | 0.2238 | YES |
| HC count | >= 10,000 | 16,290 | YES |
| HC coverage | >= 10% | 13.58% | YES |

**All 5 AND-gates pass** in the seen_research 120k setting.

### vs Baseline: clear improvement

Complete14 improves on every metric vs the no-tushare baseline: +1.2pp Wilson, +84 HC count (stable), -0.0017 Brier. The tushare columns add signal without degrading selectivity.

### vs Partial10: better balanced

Partial10 had higher raw accuracy (+0.5pp HC, +0.46pp Wilson) but at a steep cost: -1,937 HC count and -1.6pp coverage. Complete14 **recovers count and coverage to baseline levels** while retaining most of the accuracy gain. This is a precision-coverage rebalancing driven by the 4 auction columns.

### Auction column signal

All 4 stk_auction base columns survived stable_tail selection (4/4). Their addition caused 2 moneyflow columns (`tushare_net_mf_amount`, `tushare_lg_buy_sell_ratio`) to drop out of the selected 260, suggesting auction data partially subsumes moneyflow information while providing additional signal.

Selected tushare base columns: 10/14 (partial10 had 8/10).

### Recommendation

Complete14 (`b05caa22`) is the better candidate for production consideration vs partial10 (`d3222871`):
- Nearly identical accuracy (+1.2pp vs baseline, only -0.5pp below partial10)
- Much healthier count/coverage profile (16,290 / 13.58% vs 14,269 / 11.89%)
- Lower Brier (0.2238 vs 0.2245)
- All acceptance gates pass

**This is a seen_research diagnostic only.** No frozen config changes, no "passed" claims. Next steps require user decision.

## Constraints Confirmation

- [x] frozen_forward_config.json NOT modified
- [x] diagnostic_monkey_patch = true
- [x] lockbox_role = seen_research
- [x] No run claims 'passed'
- [x] baseline and partial10 from family_ablation_results_20260503.json (not re-run)
- [x] stk_auction_o and stk_auction_c cache verified pre-run

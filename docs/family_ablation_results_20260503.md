# Family Ablation Results

> Generated: 2026-05-03T11:58:30.128221+00:00
> Experiment: controlled_family_ablation
> diagnostic_monkey_patch: true
> lockbox_role: seen_research only — NOT final_unseen, NOT passed, NOT frozen

## Baseline Parameters

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

## Tushare Pre-Run Check

| API Directory | Parquet Files | Status |
|--------------|---------------|--------|
| moneyflow | 804 | OK |
| daily_basic | 804 | OK |
| stk_limit | 804 | OK |
| stk_auction_o | 804 | EXCLUDED this round (cache=804, available for Tier 1b) |
| stk_auction_c | 804 | EXCLUDED this round (cache=804, available for Tier 1b) |

## Comparison Table

| Variant | Features | Selected | Family In | Family Sel | Skipped | HC Accuracy | Wilson 95 | HC Count | Coverage | Brier | Elapsed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline_expanded_no_cross | 352 | 260 | 0 | 0 | 9 | 0.7540 | 0.7474 | 16206 | 0.1351 | 0.2254 | 134s |
| expanded_plus_research_daily | 446 | 260 | 94 | 32 | 9 | 0.7430 | 0.7366 | 18268 | 0.1522 | 0.2267 | 129s |
| tushare_tier1_available | 372 | 260 | 20 | 8 | 9 | 0.7709 | 0.7639 | 14269 | 0.1189 | 0.2245 | 1372s |

## Variant Details

### baseline_expanded_no_cross

- **Description**: Current expanded after exclude cross_ (352 input features)
- **run_id**: `gpu_probe_20260503T113328Z_1b272829`
- **artifact**: `E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260503T113328Z_1b272829\artifact.json`
- **status**: completed

### expanded_plus_research_daily

- **Description**: Baseline + GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES (94 extra)
- **run_id**: `gpu_probe_20260503T113537Z_058b885e`
- **artifact**: `E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260503T113537Z_058b885e\artifact.json`
- **status**: completed

### tushare_tier1_available

- **Description**: Baseline + Tushare Tier 1 moneyflow/daily_basic/stk_limit (20 extra)
- **run_id**: `gpu_probe_20260503T115829Z_d3222871`
- **artifact**: `E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260503T115829Z_d3222871\artifact.json`
- **status**: completed

## Tushare Tier 1 Post-Diagnostic

| Column | In Input | Selected | Skipped | Reason | Nonzero Rate |
|--------|----------|----------|---------|--------|-------------|
| `tushare_net_mf_amount` | True | True | False |  | — |
| `tushare_lg_buy_sell_ratio` | True | True | False |  | — |
| `tushare_elg_buy_sell_ratio` | True | True | False |  | — |
| `tushare_mf_strength` | True | False | False |  | — |
| `tushare_sm_sell_pressure` | True | False | False |  | — |
| `tushare_volume_ratio` | True | True | False |  | — |
| `tushare_free_share` | True | True | False |  | — |
| `tushare_up_limit_distance` | True | True | False |  | — |
| `tushare_down_limit_distance` | True | True | False |  | — |
| `tushare_limit_range` | True | True | False |  | — |
| `tushare_net_mf_amount_available` | True | False | False |  | — |
| `tushare_lg_buy_sell_ratio_available` | True | False | False |  | — |
| `tushare_elg_buy_sell_ratio_available` | True | False | False |  | — |
| `tushare_mf_strength_available` | True | False | False |  | — |
| `tushare_sm_sell_pressure_available` | True | False | False |  | — |
| `tushare_volume_ratio_available` | True | False | False |  | — |
| `tushare_free_share_available` | True | False | False |  | — |
| `tushare_up_limit_distance_available` | True | False | False |  | — |
| `tushare_down_limit_distance_available` | True | False | False |  | — |
| `tushare_limit_range_available` | True | False | False |  | — |

## Decision Criteria

### research_daily verdict

- Wilson delta: -0.010746 (0.7474 → 0.7366)
- HC accuracy delta: -0.011049 (0.7540 → 0.7430)
- HC count delta: +2062 (16206 → 18268)
- Coverage delta: +0.017183 (0.1351 → 0.1522)

### tushare_tier1 verdict

- Wilson delta: +0.016582 (0.7474 → 0.7639)
- HC accuracy delta: +0.016860 (0.7540 → 0.7709)
- HC count delta: -1937 (16206 → 14269)
- Coverage delta: -0.016142 (0.1351 → 0.1189)


## Constraints Confirmation

- [x] frozen_forward_config.json NOT modified
- [x] diagnostic_monkey_patch = true (feature_names overridden in-process)
- [x] lockbox_role = seen_research for all runs
- [x] No run claims 'passed'
- [x] No full feature_set=research blast
- [x] stk_auction excluded this round (cache exists, available for Tier 1b)
- [x] Tushare data verified pre and post run

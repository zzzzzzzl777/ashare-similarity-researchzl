# Family Ablation Results

> Generated: 2026-05-04T03:38:57.403092+00:00
> Experiment: controlled_family_ablation
> diagnostic_monkey_patch: true
> lockbox_role: seen_research only — NOT final_unseen, NOT passed, NOT frozen

## Baseline Parameters

| Parameter | Value |
|-----------|-------|
| start | 2023-05-01 |
| train_end | 2025-12-31 |
| test_start | 2026-01-01 |
| end | 2026-03-31 |
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
| tier1_plus_c009_c004 | 376 | 260 | 24 | 11 | 9 | 0.7302 | 0.7228 | 14309 | 0.2503 | 0.2208 | 1690s |

## Variant Details

### tier1_plus_c009_c004

- **Description**: Tier1 + C009 + C004 (two-factor interaction without C011)
- **run_id**: `gpu_probe_20260504T033857Z_074fe9ea`
- **artifact**: `E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260504T033857Z_074fe9ea\artifact.json`
- **status**: completed


## Decision Criteria


## Constraints Confirmation

- [x] frozen_forward_config.json NOT modified
- [x] diagnostic_monkey_patch = true (feature_names overridden in-process)
- [x] lockbox_role = seen_research for all runs
- [x] No run claims 'passed'
- [x] No full feature_set=research blast
- [x] stk_auction excluded this round (cache exists, available for Tier 1b)
- [x] Tushare data verified pre and post run

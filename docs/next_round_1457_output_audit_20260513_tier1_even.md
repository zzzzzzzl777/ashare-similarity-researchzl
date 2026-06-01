# 14:57 Next-Round Output Audit (20260513_tier1_even)

- Created at: 2026-05-13T02:14:41.554567+00:00
- Protocol asof: `20260513`
- Matrix rows: 36
- P0 fails: 0
- P1 fails: 0
- WIP rows: 0

## Issues

| level | code | status | detail |
|---|---|---|---|
| P0 | protocol_self_audit_clean | PASS | Protocol non-PASS rows: 0. |
| P1 | fixed_matrix_summary_readable | PASS | Read E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_summary_20260513_tier1_even.json. |
| P1 | fixed_matrix_fold_rows | PASS | Fold rows 36/36. |
| P0 | fixed_matrix_no_error_rows | PASS | ERROR rows: 0. |
| P0 | fixed_matrix_no_p0_selected | PASS | P0 selected rows: 0. |
| P1 | fixed_matrix_no_duplicate_keys | PASS | Duplicate keys: 0. |
| P1 | fixed_matrix_variant_coverage | PASS | Variants 3/3. |
| P1 | fixed_matrix_scheme_coverage | PASS | Schemes 6/6. |

## Leaderboard Preview

| variant | scheme | folds | mean_wilson_95 | min_wilson_95 | mean_accuracy | candidates | p0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| all_A_engineerable | expanding_from_fair_start | 2 | 0.800317 | 0.776661 | 0.816801 | 4495 | 0 |
| pre_new_A_engineerable_control | fixed_start_2018 | 2 | 0.798616 | 0.780175 | 0.815284 | 4438 | 0 |
| pre_new_A_engineerable_control | expanding_from_fair_start | 2 | 0.798472 | 0.780341 | 0.815228 | 4397 | 0 |
| new_5min_family_only | expanding_from_fair_start | 2 | 0.798467 | 0.769641 | 0.814302 | 4906 | 0 |
| new_5min_family_only | fixed_start_2018 | 2 | 0.796796 | 0.770368 | 0.812796 | 4835 | 0 |
| all_A_engineerable | fixed_start_2018 | 2 | 0.795435 | 0.778225 | 0.811840 | 4632 | 0 |
| pre_new_A_engineerable_control | fixed_start_2020 | 2 | 0.783650 | 0.778579 | 0.801964 | 3928 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 2 | 0.781576 | 0.774594 | 0.799975 | 3935 | 0 |
| new_5min_family_only | fixed_recent_36m | 2 | 0.780712 | 0.773620 | 0.799280 | 3864 | 0 |
| new_5min_family_only | fixed_start_2020 | 2 | 0.780574 | 0.774845 | 0.798940 | 4014 | 0 |

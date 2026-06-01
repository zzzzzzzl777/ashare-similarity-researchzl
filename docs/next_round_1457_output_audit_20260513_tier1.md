# 14:57 Next-Round Output Audit (20260513_tier1)

- Created at: 2026-05-12T23:55:18.045751+00:00
- Protocol asof: `20260513`
- Matrix rows: 3
- P0 fails: 0
- P1 fails: 0
- WIP rows: 3

## Issues

| level | code | status | detail |
|---|---|---|---|
| P0 | protocol_self_audit_clean | PASS | Protocol non-PASS rows: 0. |
| P1 | fixed_matrix_summary_readable | PASS | Read E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_summary_20260513_tier1.json. |
| P1 | fixed_matrix_fold_rows | WIP | Fold rows 3/48. |
| P0 | fixed_matrix_no_error_rows | PASS | ERROR rows: 0. |
| P0 | fixed_matrix_no_p0_selected | PASS | P0 selected rows: 0. |
| P1 | fixed_matrix_no_duplicate_keys | PASS | Duplicate keys: 0. |
| P1 | fixed_matrix_variant_coverage | WIP | Variants 1/4. |
| P1 | fixed_matrix_scheme_coverage | WIP | Schemes 2/6. |

## Leaderboard Preview

| variant | scheme | folds | mean_wilson_95 | min_wilson_95 | mean_accuracy | candidates | p0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| pre_new_A_engineerable_control | expanding_from_fair_start | 2 | 0.782504 | 0.747951 | 0.797300 | 6137 | 0 |
| pre_new_A_engineerable_control | fixed_recent_24m | 1 | 0.744864 | 0.744864 | 0.759130 | 3587 | 0 |

# 14:57 Next-Round Output Audit (20260513_tier6_top2_full36_seed7_gpu_v1)

- Created at: 2026-05-14T06:37:49.972156+00:00
- Protocol asof: `20260513`
- Matrix rows: 46
- P0 fails: 0
- P1 fails: 0
- WIP rows: 0

## Issues

| level | code | status | detail |
|---|---|---|---|
| P0 | protocol_self_audit_clean | PASS | Protocol non-PASS rows: 0. |
| P1 | fixed_matrix_summary_readable | PASS | Read E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_summary_20260513_tier6_top2_full36_seed7_gpu_v1.json. |
| P1 | fixed_matrix_fold_rows | PASS | Fold rows 46/46. |
| P0 | fixed_matrix_no_error_rows | PASS | ERROR rows: 0. |
| P0 | fixed_matrix_no_p0_selected | PASS | P0 selected rows: 0. |
| P1 | fixed_matrix_no_duplicate_keys | PASS | Duplicate keys: 0. |
| P0 | fixed_matrix_single_compute_backend | PASS | Backends: ['gpu']; expected: gpu. |
| P0 | fixed_matrix_single_python_env | PASS | Python envs: ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains: .venv5090. |
| P1 | fixed_matrix_variant_coverage | PASS | Variants 2/2. |
| P1 | fixed_matrix_scheme_coverage | PASS | Schemes 1/1. |

## Leaderboard Preview

| variant | scheme | folds | mean_wilson_95 | min_wilson_95 | mean_accuracy | candidates | p0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| family_drop_intraday_volume_structure | fixed_recent_36m | 23 | 0.784021 | 0.717696 | 0.805002 | 53506 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 23 | 0.782304 | 0.713268 | 0.803163 | 54670 | 0 |

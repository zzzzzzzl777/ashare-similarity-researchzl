# 14:57 Next-Round Output Audit (20260513_tier2_gpu_canary_v3)

- Created at: 2026-05-13T06:08:04.748140+00:00
- Protocol asof: `20260513`
- Matrix rows: 1
- P0 fails: 0
- P1 fails: 0
- WIP rows: 0

## Issues

| level | code | status | detail |
|---|---|---|---|
| P0 | protocol_self_audit_clean | PASS | Protocol non-PASS rows: 0. |
| P1 | fixed_matrix_summary_readable | PASS | Read E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_summary_20260513_tier2_gpu_canary_v3.json. |
| P1 | fixed_matrix_fold_rows | PASS | Fold rows 1/1. |
| P0 | fixed_matrix_no_error_rows | PASS | ERROR rows: 0. |
| P0 | fixed_matrix_no_p0_selected | PASS | P0 selected rows: 0. |
| P1 | fixed_matrix_no_duplicate_keys | PASS | Duplicate keys: 0. |
| P0 | fixed_matrix_single_compute_backend | PASS | Backends: ['gpu']; expected: gpu. |
| P0 | fixed_matrix_single_python_env | PASS | Python envs: ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains: .venv5090. |
| P1 | fixed_matrix_variant_coverage | PASS | Variants 1/1. |
| P1 | fixed_matrix_scheme_coverage | PASS | Schemes 1/1. |

## Leaderboard Preview

| variant | scheme | folds | mean_wilson_95 | min_wilson_95 | mean_accuracy | candidates | p0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| pre_new_A_engineerable_control | expanding_from_fair_start | 1 | 0.781390 | 0.781390 | 0.798193 | 2324 | 0 |

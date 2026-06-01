# 14:57 Next-Round Output Audit (20260513_tier2_even4_gpu_repro_v3)

- Created at: 2026-05-13T09:38:51.223854+00:00
- Protocol asof: `20260513`
- Matrix rows: 48
- P0 fails: 0
- P1 fails: 0
- WIP rows: 0

## Issues

| level | code | status | detail |
|---|---|---|---|
| P0 | protocol_self_audit_clean | PASS | Protocol non-PASS rows: 0. |
| P1 | fixed_matrix_summary_readable | PASS | Read E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_summary_20260513_tier2_even4_gpu_repro_v3.json. |
| P1 | fixed_matrix_fold_rows | PASS | Fold rows 48/48. |
| P0 | fixed_matrix_no_error_rows | PASS | ERROR rows: 0. |
| P0 | fixed_matrix_no_p0_selected | PASS | P0 selected rows: 0. |
| P1 | fixed_matrix_no_duplicate_keys | PASS | Duplicate keys: 0. |
| P0 | fixed_matrix_single_compute_backend | PASS | Backends: ['gpu']; expected: gpu. |
| P0 | fixed_matrix_single_python_env | PASS | Python envs: ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains: .venv5090. |
| P1 | fixed_matrix_variant_coverage | PASS | Variants 3/3. |
| P1 | fixed_matrix_scheme_coverage | PASS | Schemes 4/4. |

## Leaderboard Preview

| variant | scheme | folds | mean_wilson_95 | min_wilson_95 | mean_accuracy | candidates | p0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| pre_new_A_engineerable_control | fixed_recent_36m | 4 | 0.800130 | 0.780099 | 0.814980 | 13868 | 0 |
| new_5min_family_only | fixed_recent_36m | 4 | 0.799649 | 0.786867 | 0.814804 | 13459 | 0 |
| all_A_engineerable | fixed_recent_36m | 4 | 0.796810 | 0.774112 | 0.811561 | 14052 | 0 |
| new_5min_family_only | fixed_start_2020 | 4 | 0.790366 | 0.737628 | 0.816511 | 11385 | 0 |
| all_A_engineerable | expanding_from_fair_start | 4 | 0.789758 | 0.727409 | 0.810444 | 6821 | 0 |
| all_A_engineerable | fixed_start_2020 | 4 | 0.787553 | 0.734405 | 0.809345 | 12089 | 0 |
| pre_new_A_engineerable_control | expanding_from_fair_start | 4 | 0.785881 | 0.717729 | 0.807141 | 6734 | 0 |
| pre_new_A_engineerable_control | fixed_start_2018 | 4 | 0.784264 | 0.721163 | 0.810326 | 5332 | 0 |
| new_5min_family_only | expanding_from_fair_start | 4 | 0.783170 | 0.712348 | 0.803831 | 7098 | 0 |
| new_5min_family_only | fixed_start_2018 | 4 | 0.782089 | 0.723416 | 0.806743 | 5448 | 0 |

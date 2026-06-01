# 14:57 Next-Round Output Audit (20260513_tier3_full36_gpu_v1)

- Created at: 2026-05-15T08:52:26.452073+00:00
- Protocol asof: `20260513`
- Matrix rows: 69
- P0 fails: 1
- P1 fails: 0
- WIP rows: 0

## Issues

| level | code | status | detail |
|---|---|---|---|
| P0 | protocol_self_audit_clean | PASS | Protocol non-PASS rows: 0. |
| P1 | fixed_matrix_summary_readable | PASS | Read E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_summary_20260513_tier3_full36_gpu_v1.json. |
| P1 | fixed_matrix_fold_rows | PASS | Fold rows 69/69. |
| P0 | fixed_matrix_no_error_rows | PASS | ERROR rows: 0. |
| P0 | fixed_matrix_no_p0_selected | PASS | P0 selected rows: 0. |
| P0 | fixed_matrix_no_strict_p0_selected_recomputed | FAIL | Recomputed strict P0 rows: 69; sample run=gpu_probe_20260513T094645Z_f089f98e, features=['tushare_auction_close_vol', 'tushare_auction_close_vwap_ratio', 'tushare_float_relative_impact', 'tushare_lhb_net_rate', 'tushare_margin_net_available', 'tushare_net_mf_amount', 'tushare_rqye_ratio', 'tushare_rqye_ratio_available']. |
| P1 | fixed_matrix_no_duplicate_keys | PASS | Duplicate keys: 0. |
| P0 | fixed_matrix_single_compute_backend | PASS | Backends: ['gpu']; expected: gpu. |
| P0 | fixed_matrix_single_python_env | PASS | Python envs: ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains: .venv5090. |
| P1 | fixed_matrix_variant_coverage | PASS | Variants 3/3. |
| P1 | fixed_matrix_scheme_coverage | PASS | Schemes 1/1. |

## Leaderboard Preview

| variant | scheme | folds | mean_wilson_95 | min_wilson_95 | mean_accuracy | candidates | p0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| all_A_engineerable | fixed_recent_36m | 23 | 0.784178 | 0.695688 | 0.805330 | 53843 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 23 | 0.783150 | 0.717784 | 0.803986 | 54180 | 0 |
| new_5min_family_only | fixed_recent_36m | 23 | 0.781391 | 0.694700 | 0.802489 | 53881 | 0 |

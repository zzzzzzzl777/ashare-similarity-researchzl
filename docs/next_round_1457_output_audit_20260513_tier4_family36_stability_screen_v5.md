# 14:57 Next-Round Output Audit (20260513_tier4_family36_stability_screen_v5)

- Created at: 2026-05-13T18:49:19.313499+00:00
- Protocol asof: `20260513`
- Matrix rows: 60
- P0 fails: 0
- P1 fails: 0
- WIP rows: 0

## Issues

| level | code | status | detail |
|---|---|---|---|
| P0 | protocol_self_audit_clean | PASS | Protocol non-PASS rows: 0. |
| P1 | fixed_matrix_summary_readable | PASS | Read E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_summary_20260513_tier4_family36_stability_screen_v5.json. |
| P1 | fixed_matrix_fold_rows | PASS | Fold rows 60/60. |
| P0 | fixed_matrix_no_error_rows | PASS | ERROR rows: 0. |
| P0 | fixed_matrix_no_p0_selected | PASS | P0 selected rows: 0. |
| P1 | fixed_matrix_no_duplicate_keys | PASS | Duplicate keys: 0. |
| P0 | fixed_matrix_single_compute_backend | PASS | Backends: ['gpu']; expected: gpu. |
| P0 | fixed_matrix_single_python_env | PASS | Python envs: ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains: .venv5090. |
| P1 | fixed_matrix_variant_coverage | PASS | Variants 15/15. |
| P1 | fixed_matrix_scheme_coverage | PASS | Schemes 1/1. |

## Leaderboard Preview

| variant | scheme | folds | mean_wilson_95 | min_wilson_95 | mean_accuracy | candidates | p0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| family_drop_intraday_volume_structure | fixed_recent_36m | 4 | 0.746333 | 0.719004 | 0.766550 | 8487 | 0 |
| family_drop_technical_pattern | fixed_recent_36m | 4 | 0.745869 | 0.714124 | 0.766621 | 8058 | 0 |
| family_drop_relative_strength | fixed_recent_36m | 4 | 0.744570 | 0.714124 | 0.765266 | 8228 | 0 |
| family_drop_market_breadth | fixed_recent_36m | 4 | 0.742310 | 0.714124 | 0.763228 | 8395 | 0 |
| family_drop_momentum | fixed_recent_36m | 4 | 0.740033 | 0.706932 | 0.760281 | 8454 | 0 |
| family_drop_intraday_momentum | fixed_recent_36m | 4 | 0.738988 | 0.709356 | 0.759522 | 8649 | 0 |
| family_drop_intraday_price_structure | fixed_recent_36m | 4 | 0.738360 | 0.706984 | 0.758794 | 8295 | 0 |
| family_drop_volume_quality | fixed_recent_36m | 4 | 0.738197 | 0.698280 | 0.758807 | 8284 | 0 |
| family_drop_liquidity | fixed_recent_36m | 4 | 0.737478 | 0.698280 | 0.758110 | 8277 | 0 |
| family_drop_intraday_risk | fixed_recent_36m | 4 | 0.737291 | 0.697531 | 0.758177 | 8219 | 0 |

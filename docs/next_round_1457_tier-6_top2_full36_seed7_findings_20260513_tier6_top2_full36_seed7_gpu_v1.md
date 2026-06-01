# 14:57 Next-Round Tier-6 Top2 Full36 Seed7 Findings (20260513_tier6_top2_full36_seed7_gpu_v1)

- Created at: 2026-05-14T06:38:15.540894+00:00
- Completed matrix rows: 46
- Source CSV: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_results_20260513_tier6_top2_full36_seed7_gpu_v1.csv`
- External audit: P0=0, P1=0, WIP=0

## Decision Snapshot

- Matrix leader: `family_drop_intraday_volume_structure + fixed_recent_36m`; mean Wilson95=0.784021, worst=0.717696.
- Best variant family: `family_drop_intraday_volume_structure`.
- Best time-window scheme: `fixed_recent_36m`.
- Stable window candidate: `family_drop_intraday_volume_structure + fixed_recent_36m`.
- Formal strict-GPU full 23-fold seed=7 validation for the stable baseline and drop-intraday-volume challenger; Q1/April excluded.

## Self Audit

| level | code | status | detail |
|---|---|---|---|
| P1 | expected_fold_rows | PASS | Completed fold rows 46/46. |
| P0 | no_p0_selected | PASS | P0 selected total 0. |
| P0 | single_expected_backend | PASS | Backends ['gpu']; expected gpu. |
| P0 | single_expected_python | PASS | Python envs ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains .venv5090. |
| P1 | bundle_validation_passed | PASS | Rows with failed bundle validation 0. |

## Combo Leaderboard

| variant_id | scheme | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|---|
| family_drop_intraday_volume_structure | fixed_recent_36m | 23 | 0.784021 | 0.717696 | 0.036301 | 0.805002 | 53506 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 23 | 0.782304 | 0.713268 | 0.035127 | 0.803163 | 54670 | 0 |

## Variant Aggregate

| variant_id | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| family_drop_intraday_volume_structure | 23 | 0.784021 | 0.717696 | 0.036301 | 0.805002 | 53506 | 0 |
| pre_new_A_engineerable_control | 23 | 0.782304 | 0.713268 | 0.035127 | 0.803163 | 54670 | 0 |

## Time-Window Aggregate

| scheme | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| fixed_recent_36m | 46 | 0.783162 | 0.713268 | 0.035330 | 0.804082 | 108176 | 0 |

## Worst Rows

| variant_id | scheme | outer_fold | outer_valid_start | outer_valid_end | wilson_95 | confident_accuracy | confident_count | p0_selected_count |
|---|---|---|---|---|---|---|---|---|
| pre_new_A_engineerable_control | fixed_recent_36m | 14 | 2022-04-01 | 2022-06-30 | 0.713268 | 0.732487 | 2127 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 14 | 2022-04-01 | 2022-06-30 | 0.717696 | 0.735401 | 2483 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 19 | 2023-07-01 | 2023-09-30 | 0.724517 | 0.756793 | 736 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 19 | 2023-07-01 | 2023-09-30 | 0.724777 | 0.756614 | 756 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 18 | 2023-04-01 | 2023-06-30 | 0.732868 | 0.753557 | 1757 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 18 | 2023-04-01 | 2023-06-30 | 0.733481 | 0.754108 | 1765 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 25 | 2025-01-01 | 2025-03-31 | 0.739484 | 0.762170 | 1438 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 22 | 2024-04-01 | 2024-06-30 | 0.742612 | 0.764946 | 1472 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 22 | 2024-04-01 | 2024-06-30 | 0.743418 | 0.765161 | 1550 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 17 | 2023-01-01 | 2023-03-31 | 0.745408 | 0.778443 | 668 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 25 | 2025-01-01 | 2025-03-31 | 0.758760 | 0.782071 | 1294 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 20 | 2023-10-01 | 2023-12-31 | 0.760563 | 0.791165 | 747 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 20 | 2023-10-01 | 2023-12-31 | 0.760563 | 0.791165 | 747 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 24 | 2024-10-01 | 2024-12-31 | 0.768362 | 0.777298 | 8563 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 16 | 2022-10-01 | 2022-12-31 | 0.768650 | 0.790883 | 1382 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 23 | 2024-07-01 | 2024-09-30 | 0.770061 | 0.816456 | 316 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 16 | 2022-10-01 | 2022-12-31 | 0.770380 | 0.791779 | 1484 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 17 | 2023-01-01 | 2023-03-31 | 0.771961 | 0.801849 | 757 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 24 | 2024-10-01 | 2024-12-31 | 0.776942 | 0.786161 | 7833 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 23 | 2024-07-01 | 2024-09-30 | 0.780544 | 0.822888 | 367 | 0 |

## Interpretation

- Do not use 2026-04 single-month accuracy as the champion selector; it is only a seen-research stress window.
- Prefer candidates that keep the worst rolling fold high while preserving enough candidates for daily topK use.
- Treat `new_5min_family_only` as evidence that the C174-C188 family has standalone signal; final selection still needs add/delete against the full A matrix.
- Continue with explicit B-proxy feature columns before any B-policy champion attempt; do not reuse same-name T-day moneyflow/CYQ fields.

## Next Actions

1. Expand the leading combos to full rolling folds and multi-seed/HPO only after this audit is clean.
2. Run family add/delete and beam search on all engineerable factors, including C174-C188.
3. Freeze 1-3 champion/challenger bundles and score Q1/April as seen-research only.
4. Use future post-freeze months as the only final-forward gate.

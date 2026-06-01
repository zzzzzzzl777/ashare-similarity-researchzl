# 14:57 Next-Round Tier-7 Top2 Full36 Seed2026 Findings (20260514_tier7_top2_full36_seed2026_gpu_v1)

- Created at: 2026-05-14T09:24:26.610328+00:00
- Completed matrix rows: 46
- Source CSV: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_results_20260514_tier7_top2_full36_seed2026_gpu_v1.csv`
- External audit: P0=0, P1=0, WIP=0

## Decision Snapshot

- Matrix leader: `family_drop_intraday_volume_structure + fixed_recent_36m`; mean Wilson95=0.782645, worst=0.698737.
- Best variant family: `family_drop_intraday_volume_structure`.
- Best time-window scheme: `fixed_recent_36m`.
- Stable window candidate: `pre_new_A_engineerable_control + fixed_recent_36m`.
- Formal strict-GPU full 23-fold seed=2026 validation for the stable baseline and drop-intraday-volume challenger; Q1/April excluded.

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
| family_drop_intraday_volume_structure | fixed_recent_36m | 23 | 0.782645 | 0.698737 | 0.036620 | 0.803434 | 55635 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 23 | 0.781205 | 0.715592 | 0.035905 | 0.802377 | 54756 | 0 |

## Variant Aggregate

| variant_id | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| family_drop_intraday_volume_structure | 23 | 0.782645 | 0.698737 | 0.036620 | 0.803434 | 55635 | 0 |
| pre_new_A_engineerable_control | 23 | 0.781205 | 0.715592 | 0.035905 | 0.802377 | 54756 | 0 |

## Time-Window Aggregate

| scheme | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| fixed_recent_36m | 46 | 0.781925 | 0.698737 | 0.035866 | 0.802905 | 110391 | 0 |

## Worst Rows

| variant_id | scheme | outer_fold | outer_valid_start | outer_valid_end | wilson_95 | confident_accuracy | confident_count | p0_selected_count |
|---|---|---|---|---|---|---|---|---|
| family_drop_intraday_volume_structure | fixed_recent_36m | 19 | 2023-07-01 | 2023-09-30 | 0.698737 | 0.730159 | 819 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 14 | 2022-04-01 | 2022-06-30 | 0.715592 | 0.734354 | 2221 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 19 | 2023-07-01 | 2023-09-30 | 0.715607 | 0.746617 | 813 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 18 | 2023-04-01 | 2023-06-30 | 0.726779 | 0.747145 | 1839 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 18 | 2023-04-01 | 2023-06-30 | 0.729887 | 0.751549 | 1614 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 14 | 2022-04-01 | 2022-06-30 | 0.731291 | 0.749352 | 2314 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 22 | 2024-04-01 | 2024-06-30 | 0.734512 | 0.755375 | 1721 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 22 | 2024-04-01 | 2024-06-30 | 0.734708 | 0.758516 | 1321 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 17 | 2023-01-01 | 2023-03-31 | 0.754308 | 0.784695 | 771 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 25 | 2025-01-01 | 2025-03-31 | 0.755536 | 0.777476 | 1474 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 24 | 2024-10-01 | 2024-12-31 | 0.756515 | 0.765402 | 8960 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 20 | 2023-10-01 | 2023-12-31 | 0.761277 | 0.792857 | 700 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 20 | 2023-10-01 | 2023-12-31 | 0.761277 | 0.792857 | 700 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 24 | 2024-10-01 | 2024-12-31 | 0.761902 | 0.770382 | 9690 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 25 | 2025-01-01 | 2025-03-31 | 0.765323 | 0.788567 | 1277 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 16 | 2022-10-01 | 2022-12-31 | 0.765381 | 0.785978 | 1626 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 16 | 2022-10-01 | 2022-12-31 | 0.769631 | 0.790519 | 1561 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 17 | 2023-01-01 | 2023-03-31 | 0.769703 | 0.799479 | 768 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 23 | 2024-07-01 | 2024-09-30 | 0.774745 | 0.821782 | 303 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 6 | 2020-04-01 | 2020-06-30 | 0.775122 | 0.795611 | 1595 | 0 |

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

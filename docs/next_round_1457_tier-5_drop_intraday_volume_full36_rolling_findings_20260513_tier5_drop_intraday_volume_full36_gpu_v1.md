# 14:57 Next-Round Tier-5 Drop Intraday Volume Full36 Rolling Findings (20260513_tier5_drop_intraday_volume_full36_gpu_v1)

- Created at: 2026-05-13T20:31:12.049424+00:00
- Completed matrix rows: 23
- Source CSV: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_results_20260513_tier5_drop_intraday_volume_full36_gpu_v1.csv`
- External audit: P0=0, P1=0, WIP=0

## Decision Snapshot

- Matrix leader: `family_drop_intraday_volume_structure + fixed_recent_36m`; mean Wilson95=0.782395, worst=0.719004.
- Best variant family: `family_drop_intraday_volume_structure`.
- Best time-window scheme: `fixed_recent_36m`.
- Stable window candidate: `family_drop_intraday_volume_structure + fixed_recent_36m`.
- Formal strict-GPU full 23-fold rolling validation for the Tier-4 stability-screen candidate; this is challenger validation, not a champion freeze.

## Self Audit

| level | code | status | detail |
|---|---|---|---|
| P1 | expected_fold_rows | PASS | Completed fold rows 23/23. |
| P0 | no_p0_selected | PASS | P0 selected total 0. |
| P0 | single_expected_backend | PASS | Backends ['gpu']; expected gpu. |
| P0 | single_expected_python | PASS | Python envs ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains .venv5090. |
| P1 | bundle_validation_passed | PASS | Rows with failed bundle validation 0. |

## Combo Leaderboard

| variant_id | scheme | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|---|
| family_drop_intraday_volume_structure | fixed_recent_36m | 23 | 0.782395 | 0.719004 | 0.031859 | 0.802969 | 55558 | 0 |

## Variant Aggregate

| variant_id | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| family_drop_intraday_volume_structure | 23 | 0.782395 | 0.719004 | 0.031859 | 0.802969 | 55558 | 0 |

## Time-Window Aggregate

| scheme | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| fixed_recent_36m | 23 | 0.782395 | 0.719004 | 0.031859 | 0.802969 | 55558 | 0 |

## Worst Rows

| variant_id | scheme | outer_fold | outer_valid_start | outer_valid_end | wilson_95 | confident_accuracy | confident_count | p0_selected_count |
|---|---|---|---|---|---|---|---|---|
| family_drop_intraday_volume_structure | fixed_recent_36m | 19 | 2023-07-01 | 2023-09-30 | 0.719004 | 0.748337 | 902 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 14 | 2022-04-01 | 2022-06-30 | 0.730774 | 0.748277 | 2467 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 18 | 2023-04-01 | 2023-06-30 | 0.735568 | 0.756016 | 1787 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 22 | 2024-04-01 | 2024-06-30 | 0.746314 | 0.767601 | 1605 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 25 | 2025-01-01 | 2025-03-31 | 0.749834 | 0.770255 | 1728 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 20 | 2023-10-01 | 2023-12-31 | 0.754507 | 0.784537 | 789 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 24 | 2024-10-01 | 2024-12-31 | 0.765075 | 0.774261 | 8182 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 17 | 2023-01-01 | 2023-03-31 | 0.768564 | 0.798200 | 778 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 16 | 2022-10-01 | 2022-12-31 | 0.775086 | 0.794279 | 1818 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 23 | 2024-07-01 | 2024-09-30 | 0.777578 | 0.821023 | 352 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 6 | 2020-04-01 | 2020-06-30 | 0.782211 | 0.801610 | 1739 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 12 | 2021-10-01 | 2021-12-31 | 0.788986 | 0.802809 | 3347 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 7 | 2020-07-01 | 2020-09-30 | 0.792027 | 0.804411 | 4126 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 27 | 2025-07-01 | 2025-09-30 | 0.792813 | 0.814619 | 1327 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 28 | 2025-10-01 | 2025-12-31 | 0.799985 | 0.813569 | 3331 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 21 | 2024-01-01 | 2024-03-31 | 0.803729 | 0.813182 | 6782 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 11 | 2021-07-01 | 2021-09-30 | 0.805383 | 0.816335 | 5020 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 9 | 2021-01-01 | 2021-03-31 | 0.805760 | 0.819907 | 3004 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 13 | 2022-01-01 | 2022-03-31 | 0.809330 | 0.826520 | 2006 | 0 |
| family_drop_intraday_volume_structure | fixed_recent_36m | 10 | 2021-04-01 | 2021-06-30 | 0.814951 | 0.838678 | 1029 | 0 |

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

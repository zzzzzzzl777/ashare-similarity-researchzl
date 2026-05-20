# 14:57 Top2 Multi-Seed Stability Report (tier6_top2_seed42_seed7_stability)

- Created at: 2026-05-14T06:38:15.557439+00:00
- Scheme: `fixed_recent_36m`
- Expected seeds: `2`; expected folds per seed: `23`.
- Selection policy: full rolling, multi-seed, stability first; Q1/April are excluded from selection.

## Decision Snapshot

- Stability-first leader: `family_drop_intraday_volume_structure`; seeds=7,42; min=0.717696, mean=0.783208, std=0.033781.
- Mean-first leader: `family_drop_intraday_volume_structure`; mean=0.783208, min=0.717696.

## Self Audit

| level | code | status | detail |
|---|---|---|---|
| P1 | expected_rows_per_variant | PASS | Expected 46 rows per variant; incomplete variants []. |
| P1 | expected_seed_count | PASS | Seed counts [2]; expected 2. |
| P1 | same_fold_set | PASS | Fold sets {'pre_new_A_engineerable_control': [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28], 'family_drop_intraday_volume_structure': [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]}. |
| P0 | no_p0_selected | PASS | P0 selected total 0. |
| P0 | single_expected_backend | PASS | Backends ['gpu']; expected gpu. |
| P0 | single_expected_python | PASS | Python envs ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains .venv5090. |

## Stability-First Leaderboard

| role | variant_id | seeds | fold_runs | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | mean_coverage | p0_selected_total |
|---|---|---|---|---|---|---|---|---|---|---|
| challenger | family_drop_intraday_volume_structure | 7,42 | 46 | 0.783208 | 0.717696 | 0.033781 | 0.803985 | 109064 | 0.095371 | 0 |
| baseline | pre_new_A_engineerable_control | 7,42 | 46 | 0.782727 | 0.713268 | 0.033691 | 0.803575 | 108850 | 0.094562 | 0 |

## Worst-Window Rows

| role | variant_id | seed | outer_fold | outer_valid_start | outer_valid_end | wilson_95 | confident_accuracy | confident_count | p0_selected_count |
|---|---|---|---|---|---|---|---|---|---|
| baseline | pre_new_A_engineerable_control | 7 | 14 | 2022-04-01 | 2022-06-30 | 0.713268 | 0.732487 | 2127 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 14 | 2022-04-01 | 2022-06-30 | 0.717696 | 0.735401 | 2483 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 14 | 2022-04-01 | 2022-06-30 | 0.717784 | 0.735889 | 2374 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 19 | 2023-07-01 | 2023-09-30 | 0.719004 | 0.748337 | 902 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 19 | 2023-07-01 | 2023-09-30 | 0.724517 | 0.756793 | 736 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 19 | 2023-07-01 | 2023-09-30 | 0.724777 | 0.756614 | 756 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 14 | 2022-04-01 | 2022-06-30 | 0.730774 | 0.748277 | 2467 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 18 | 2023-04-01 | 2023-06-30 | 0.732868 | 0.753557 | 1757 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 19 | 2023-07-01 | 2023-09-30 | 0.732874 | 0.762813 | 839 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 18 | 2023-04-01 | 2023-06-30 | 0.733481 | 0.754108 | 1765 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 18 | 2023-04-01 | 2023-06-30 | 0.735568 | 0.756016 | 1787 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 18 | 2023-04-01 | 2023-06-30 | 0.737522 | 0.758166 | 1745 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 25 | 2025-01-01 | 2025-03-31 | 0.739484 | 0.762170 | 1438 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 22 | 2024-04-01 | 2024-06-30 | 0.742612 | 0.764946 | 1472 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 22 | 2024-04-01 | 2024-06-30 | 0.743418 | 0.765161 | 1550 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 17 | 2023-01-01 | 2023-03-31 | 0.745408 | 0.778443 | 668 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 22 | 2024-04-01 | 2024-06-30 | 0.746314 | 0.767601 | 1605 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 25 | 2025-01-01 | 2025-03-31 | 0.749834 | 0.770255 | 1728 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 22 | 2024-04-01 | 2024-06-30 | 0.752154 | 0.773732 | 1538 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 20 | 2023-10-01 | 2023-12-31 | 0.754507 | 0.784537 | 789 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 20 | 2023-10-01 | 2023-12-31 | 0.754507 | 0.784537 | 789 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 17 | 2023-01-01 | 2023-03-31 | 0.756088 | 0.787176 | 733 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 25 | 2025-01-01 | 2025-03-31 | 0.758760 | 0.782071 | 1294 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 20 | 2023-10-01 | 2023-12-31 | 0.760563 | 0.791165 | 747 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 20 | 2023-10-01 | 2023-12-31 | 0.760563 | 0.791165 | 747 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 25 | 2025-01-01 | 2025-03-31 | 0.764415 | 0.787736 | 1272 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 24 | 2024-10-01 | 2024-12-31 | 0.765075 | 0.774261 | 8182 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 24 | 2024-10-01 | 2024-12-31 | 0.765849 | 0.774819 | 8562 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 24 | 2024-10-01 | 2024-12-31 | 0.768362 | 0.777298 | 8563 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 17 | 2023-01-01 | 2023-03-31 | 0.768564 | 0.798200 | 778 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 16 | 2022-10-01 | 2022-12-31 | 0.768650 | 0.790883 | 1382 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 23 | 2024-07-01 | 2024-09-30 | 0.770061 | 0.816456 | 316 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 16 | 2022-10-01 | 2022-12-31 | 0.770377 | 0.792253 | 1420 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 16 | 2022-10-01 | 2022-12-31 | 0.770380 | 0.791779 | 1484 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 17 | 2023-01-01 | 2023-03-31 | 0.771961 | 0.801849 | 757 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 16 | 2022-10-01 | 2022-12-31 | 0.775086 | 0.794279 | 1818 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 24 | 2024-10-01 | 2024-12-31 | 0.776942 | 0.786161 | 7833 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 23 | 2024-07-01 | 2024-09-30 | 0.777555 | 0.821958 | 337 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 23 | 2024-07-01 | 2024-09-30 | 0.777578 | 0.821023 | 352 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 6 | 2020-04-01 | 2020-06-30 | 0.780099 | 0.799881 | 1684 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 23 | 2024-07-01 | 2024-09-30 | 0.780544 | 0.822888 | 367 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 6 | 2020-04-01 | 2020-06-30 | 0.782211 | 0.801610 | 1739 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 12 | 2021-10-01 | 2021-12-31 | 0.783219 | 0.799749 | 2387 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 6 | 2020-04-01 | 2020-06-30 | 0.785666 | 0.805179 | 1699 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 12 | 2021-10-01 | 2021-12-31 | 0.785762 | 0.801637 | 2566 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 6 | 2020-04-01 | 2020-06-30 | 0.786593 | 0.806202 | 1677 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 12 | 2021-10-01 | 2021-12-31 | 0.787023 | 0.801579 | 3039 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 27 | 2025-07-01 | 2025-09-30 | 0.788068 | 0.810660 | 1257 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 27 | 2025-07-01 | 2025-09-30 | 0.788068 | 0.810660 | 1257 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 12 | 2021-10-01 | 2021-12-31 | 0.788986 | 0.802809 | 3347 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 7 | 2020-07-01 | 2020-09-30 | 0.789001 | 0.800883 | 4530 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 7 | 2020-07-01 | 2020-09-30 | 0.789001 | 0.800883 | 4530 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 7 | 2020-07-01 | 2020-09-30 | 0.792027 | 0.804411 | 4126 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 7 | 2020-07-01 | 2020-09-30 | 0.792027 | 0.804411 | 4126 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 27 | 2025-07-01 | 2025-09-30 | 0.792813 | 0.814619 | 1327 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 27 | 2025-07-01 | 2025-09-30 | 0.792813 | 0.814619 | 1327 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 28 | 2025-10-01 | 2025-12-31 | 0.799985 | 0.813569 | 3331 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 28 | 2025-10-01 | 2025-12-31 | 0.800251 | 0.813904 | 3294 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 9 | 2021-01-01 | 2021-03-31 | 0.801691 | 0.816256 | 2879 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 9 | 2021-01-01 | 2021-03-31 | 0.801691 | 0.816256 | 2879 | 0 |

## Risk Notes

- This report is valid only when P0=0 and the expected row/seed audits pass.
- If a candidate wins min_wilson95 but loses mean outside tolerance, keep it as challenger rather than champion.
- Future final-forward data must remain outside this selection loop.

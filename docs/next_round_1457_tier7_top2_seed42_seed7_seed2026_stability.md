# 14:57 Top2 Multi-Seed Stability Report (tier7_top2_seed42_seed7_seed2026_stability)

- Created at: 2026-05-14T09:24:26.637554+00:00
- Scheme: `fixed_recent_36m`
- Expected seeds: `3`; expected folds per seed: `23`.
- Selection policy: full rolling, multi-seed, stability first; Q1/April are excluded from selection.

## Decision Snapshot

- Stability-first leader: `pre_new_A_engineerable_control`; seeds=7,42,2026; min=0.713268, mean=0.782220, std=0.034187.
- Mean-first leader: `family_drop_intraday_volume_structure`; mean=0.783020, min=0.698737.

## Self Audit

| level | code | status | detail |
|---|---|---|---|
| P1 | expected_rows_per_variant | PASS | Expected 69 rows per variant; incomplete variants []. |
| P1 | expected_seed_count | PASS | Seed counts [3]; expected 3. |
| P1 | same_fold_set | PASS | Fold sets {'pre_new_A_engineerable_control': [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28], 'family_drop_intraday_volume_structure': [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]}. |
| P0 | no_p0_selected | PASS | P0 selected total 0. |
| P0 | single_expected_backend | PASS | Backends ['gpu']; expected gpu. |
| P0 | single_expected_python | PASS | Python envs ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains .venv5090. |

## Stability-First Leaderboard

| role | variant_id | seeds | fold_runs | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | mean_coverage | p0_selected_total |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | pre_new_A_engineerable_control | 7,42,2026 | 69 | 0.782220 | 0.713268 | 0.034187 | 0.803175 | 163606 | 0.094338 | 0 |
| challenger | family_drop_intraday_volume_structure | 7,42,2026 | 69 | 0.783020 | 0.698737 | 0.034483 | 0.803801 | 164699 | 0.095469 | 0 |

## Worst-Window Rows

| role | variant_id | seed | outer_fold | outer_valid_start | outer_valid_end | wilson_95 | confident_accuracy | confident_count | p0_selected_count |
|---|---|---|---|---|---|---|---|---|---|
| challenger | family_drop_intraday_volume_structure | 2026 | 19 | 2023-07-01 | 2023-09-30 | 0.698737 | 0.730159 | 819 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 14 | 2022-04-01 | 2022-06-30 | 0.713268 | 0.732487 | 2127 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 14 | 2022-04-01 | 2022-06-30 | 0.715592 | 0.734354 | 2221 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 19 | 2023-07-01 | 2023-09-30 | 0.715607 | 0.746617 | 813 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 14 | 2022-04-01 | 2022-06-30 | 0.717696 | 0.735401 | 2483 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 14 | 2022-04-01 | 2022-06-30 | 0.717784 | 0.735889 | 2374 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 19 | 2023-07-01 | 2023-09-30 | 0.719004 | 0.748337 | 902 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 19 | 2023-07-01 | 2023-09-30 | 0.724517 | 0.756793 | 736 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 19 | 2023-07-01 | 2023-09-30 | 0.724777 | 0.756614 | 756 | 0 |
| challenger | family_drop_intraday_volume_structure | 2026 | 18 | 2023-04-01 | 2023-06-30 | 0.726779 | 0.747145 | 1839 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 18 | 2023-04-01 | 2023-06-30 | 0.729887 | 0.751549 | 1614 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 14 | 2022-04-01 | 2022-06-30 | 0.730774 | 0.748277 | 2467 | 0 |
| challenger | family_drop_intraday_volume_structure | 2026 | 14 | 2022-04-01 | 2022-06-30 | 0.731291 | 0.749352 | 2314 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 18 | 2023-04-01 | 2023-06-30 | 0.732868 | 0.753557 | 1757 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 19 | 2023-07-01 | 2023-09-30 | 0.732874 | 0.762813 | 839 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 18 | 2023-04-01 | 2023-06-30 | 0.733481 | 0.754108 | 1765 | 0 |
| challenger | family_drop_intraday_volume_structure | 2026 | 22 | 2024-04-01 | 2024-06-30 | 0.734512 | 0.755375 | 1721 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 22 | 2024-04-01 | 2024-06-30 | 0.734708 | 0.758516 | 1321 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 18 | 2023-04-01 | 2023-06-30 | 0.735568 | 0.756016 | 1787 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 18 | 2023-04-01 | 2023-06-30 | 0.737522 | 0.758166 | 1745 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 25 | 2025-01-01 | 2025-03-31 | 0.739484 | 0.762170 | 1438 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 22 | 2024-04-01 | 2024-06-30 | 0.742612 | 0.764946 | 1472 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 22 | 2024-04-01 | 2024-06-30 | 0.743418 | 0.765161 | 1550 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 17 | 2023-01-01 | 2023-03-31 | 0.745408 | 0.778443 | 668 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 22 | 2024-04-01 | 2024-06-30 | 0.746314 | 0.767601 | 1605 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 25 | 2025-01-01 | 2025-03-31 | 0.749834 | 0.770255 | 1728 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 22 | 2024-04-01 | 2024-06-30 | 0.752154 | 0.773732 | 1538 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 17 | 2023-01-01 | 2023-03-31 | 0.754308 | 0.784695 | 771 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 20 | 2023-10-01 | 2023-12-31 | 0.754507 | 0.784537 | 789 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 20 | 2023-10-01 | 2023-12-31 | 0.754507 | 0.784537 | 789 | 0 |
| challenger | family_drop_intraday_volume_structure | 2026 | 25 | 2025-01-01 | 2025-03-31 | 0.755536 | 0.777476 | 1474 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 17 | 2023-01-01 | 2023-03-31 | 0.756088 | 0.787176 | 733 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 24 | 2024-10-01 | 2024-12-31 | 0.756515 | 0.765402 | 8960 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 25 | 2025-01-01 | 2025-03-31 | 0.758760 | 0.782071 | 1294 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 20 | 2023-10-01 | 2023-12-31 | 0.760563 | 0.791165 | 747 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 20 | 2023-10-01 | 2023-12-31 | 0.760563 | 0.791165 | 747 | 0 |
| challenger | family_drop_intraday_volume_structure | 2026 | 20 | 2023-10-01 | 2023-12-31 | 0.761277 | 0.792857 | 700 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 20 | 2023-10-01 | 2023-12-31 | 0.761277 | 0.792857 | 700 | 0 |
| challenger | family_drop_intraday_volume_structure | 2026 | 24 | 2024-10-01 | 2024-12-31 | 0.761902 | 0.770382 | 9690 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 25 | 2025-01-01 | 2025-03-31 | 0.764415 | 0.787736 | 1272 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 24 | 2024-10-01 | 2024-12-31 | 0.765075 | 0.774261 | 8182 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 25 | 2025-01-01 | 2025-03-31 | 0.765323 | 0.788567 | 1277 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 16 | 2022-10-01 | 2022-12-31 | 0.765381 | 0.785978 | 1626 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 24 | 2024-10-01 | 2024-12-31 | 0.765849 | 0.774819 | 8562 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 24 | 2024-10-01 | 2024-12-31 | 0.768362 | 0.777298 | 8563 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 17 | 2023-01-01 | 2023-03-31 | 0.768564 | 0.798200 | 778 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 16 | 2022-10-01 | 2022-12-31 | 0.768650 | 0.790883 | 1382 | 0 |
| challenger | family_drop_intraday_volume_structure | 2026 | 16 | 2022-10-01 | 2022-12-31 | 0.769631 | 0.790519 | 1561 | 0 |
| challenger | family_drop_intraday_volume_structure | 2026 | 17 | 2023-01-01 | 2023-03-31 | 0.769703 | 0.799479 | 768 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 23 | 2024-07-01 | 2024-09-30 | 0.770061 | 0.816456 | 316 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 16 | 2022-10-01 | 2022-12-31 | 0.770377 | 0.792253 | 1420 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 16 | 2022-10-01 | 2022-12-31 | 0.770380 | 0.791779 | 1484 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 17 | 2023-01-01 | 2023-03-31 | 0.771961 | 0.801849 | 757 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 23 | 2024-07-01 | 2024-09-30 | 0.774745 | 0.821782 | 303 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 16 | 2022-10-01 | 2022-12-31 | 0.775086 | 0.794279 | 1818 | 0 |
| baseline | pre_new_A_engineerable_control | 2026 | 6 | 2020-04-01 | 2020-06-30 | 0.775122 | 0.795611 | 1595 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 24 | 2024-10-01 | 2024-12-31 | 0.776942 | 0.786161 | 7833 | 0 |
| baseline | pre_new_A_engineerable_control | 42 | 23 | 2024-07-01 | 2024-09-30 | 0.777555 | 0.821958 | 337 | 0 |
| challenger | family_drop_intraday_volume_structure | 42 | 23 | 2024-07-01 | 2024-09-30 | 0.777578 | 0.821023 | 352 | 0 |
| challenger | family_drop_intraday_volume_structure | 2026 | 6 | 2020-04-01 | 2020-06-30 | 0.778874 | 0.799247 | 1594 | 0 |

## Risk Notes

- This report is valid only when P0=0 and the expected row/seed audits pass.
- If a candidate wins min_wilson95 but loses mean outside tolerance, keep it as challenger rather than champion.
- Future final-forward data must remain outside this selection loop.

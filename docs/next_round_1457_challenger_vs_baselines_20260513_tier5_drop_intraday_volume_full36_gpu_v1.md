# 14:57 Challenger vs Baselines (20260513_tier5_drop_intraday_volume_full36_gpu_v1)

- Created at: 2026-05-13T20:31:12.048190+00:00
- Challenger: `family_drop_intraday_volume_structure` from `20260513_tier5_drop_intraday_volume_full36_gpu_v1`.
- Baselines: `pre_new_A_engineerable_control, all_A_engineerable` from `20260513_tier3_full36_gpu_v1`.
- Selection policy: fixed_recent_36m full rolling, stability first; Q1/April are not used.

## Decision Snapshot

- Stability-first leader: `family_drop_intraday_volume_structure`; min=0.719004, mean=0.782395, std=0.031859.
- Mean-first leader: `all_A_engineerable`; mean=0.784178, min=0.695688.
- Challenger next step: `eligible_for_multi_seed_or_freeze_gate`.

## Self Audit

| level | code | status | detail |
|---|---|---|---|
| P1 | challenger_full_fold_count | PASS | Challenger completed folds 23/23. |
| P1 | same_fold_set | PASS | Fold sets {'all_A_engineerable': {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28}, 'pre_new_A_engineerable_control': {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28}, 'family_drop_intraday_volume_structure': {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28}}. |
| P0 | no_p0_selected | PASS | P0 selected total 0. |
| P0 | single_expected_backend | PASS | Backends ['gpu']; expected gpu. |
| P0 | single_expected_python | PASS | Python envs ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains .venv5090. |

## Stability-First Leaderboard

| role | variant_id | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | mean_coverage | p0_selected_total |
|---|---|---|---|---|---|---|---|---|---|
| challenger | family_drop_intraday_volume_structure | 23 | 0.782395 | 0.719004 | 0.031859 | 0.802969 | 55558 | 0.097386 | 0 |
| baseline | pre_new_A_engineerable_control | 23 | 0.783150 | 0.717784 | 0.032977 | 0.803986 | 54180 | 0.094297 | 0 |
| baseline | all_A_engineerable | 23 | 0.784178 | 0.695688 | 0.037504 | 0.805330 | 53843 | 0.092967 | 0 |

## Worst-Window Rows

| role | variant_id | outer_fold | outer_valid_start | outer_valid_end | wilson_95 | confident_accuracy | confident_count | p0_selected_count |
|---|---|---|---|---|---|---|---|---|
| baseline | all_A_engineerable | 19 | 2023-07-01 | 2023-09-30 | 0.695688 | 0.730044 | 689 | 0 |
| baseline | pre_new_A_engineerable_control | 14 | 2022-04-01 | 2022-06-30 | 0.717784 | 0.735889 | 2374 | 0 |
| challenger | family_drop_intraday_volume_structure | 19 | 2023-07-01 | 2023-09-30 | 0.719004 | 0.748337 | 902 | 0 |
| baseline | all_A_engineerable | 18 | 2023-04-01 | 2023-06-30 | 0.723692 | 0.746084 | 1532 | 0 |
| baseline | all_A_engineerable | 14 | 2022-04-01 | 2022-06-30 | 0.725748 | 0.743687 | 2376 | 0 |
| challenger | family_drop_intraday_volume_structure | 14 | 2022-04-01 | 2022-06-30 | 0.730774 | 0.748277 | 2467 | 0 |
| baseline | pre_new_A_engineerable_control | 19 | 2023-07-01 | 2023-09-30 | 0.732874 | 0.762813 | 839 | 0 |
| challenger | family_drop_intraday_volume_structure | 18 | 2023-04-01 | 2023-06-30 | 0.735568 | 0.756016 | 1787 | 0 |
| baseline | pre_new_A_engineerable_control | 18 | 2023-04-01 | 2023-06-30 | 0.737522 | 0.758166 | 1745 | 0 |
| challenger | family_drop_intraday_volume_structure | 22 | 2024-04-01 | 2024-06-30 | 0.746314 | 0.767601 | 1605 | 0 |
| challenger | family_drop_intraday_volume_structure | 25 | 2025-01-01 | 2025-03-31 | 0.749834 | 0.770255 | 1728 | 0 |
| baseline | all_A_engineerable | 22 | 2024-04-01 | 2024-06-30 | 0.750756 | 0.773952 | 1336 | 0 |
| baseline | pre_new_A_engineerable_control | 22 | 2024-04-01 | 2024-06-30 | 0.752154 | 0.773732 | 1538 | 0 |
| baseline | pre_new_A_engineerable_control | 20 | 2023-10-01 | 2023-12-31 | 0.754507 | 0.784537 | 789 | 0 |
| challenger | family_drop_intraday_volume_structure | 20 | 2023-10-01 | 2023-12-31 | 0.754507 | 0.784537 | 789 | 0 |
| baseline | pre_new_A_engineerable_control | 17 | 2023-01-01 | 2023-03-31 | 0.756088 | 0.787176 | 733 | 0 |
| baseline | all_A_engineerable | 24 | 2024-10-01 | 2024-12-31 | 0.762098 | 0.770941 | 8906 | 0 |
| baseline | pre_new_A_engineerable_control | 25 | 2025-01-01 | 2025-03-31 | 0.764415 | 0.787736 | 1272 | 0 |
| challenger | family_drop_intraday_volume_structure | 24 | 2024-10-01 | 2024-12-31 | 0.765075 | 0.774261 | 8182 | 0 |
| baseline | all_A_engineerable | 23 | 2024-07-01 | 2024-09-30 | 0.765579 | 0.809524 | 357 | 0 |
| baseline | pre_new_A_engineerable_control | 24 | 2024-10-01 | 2024-12-31 | 0.765849 | 0.774819 | 8562 | 0 |
| baseline | all_A_engineerable | 16 | 2022-10-01 | 2022-12-31 | 0.767578 | 0.788687 | 1538 | 0 |
| challenger | family_drop_intraday_volume_structure | 17 | 2023-01-01 | 2023-03-31 | 0.768564 | 0.798200 | 778 | 0 |
| baseline | pre_new_A_engineerable_control | 16 | 2022-10-01 | 2022-12-31 | 0.770377 | 0.792253 | 1420 | 0 |
| baseline | all_A_engineerable | 17 | 2023-01-01 | 2023-03-31 | 0.772656 | 0.804511 | 665 | 0 |
| baseline | all_A_engineerable | 6 | 2020-04-01 | 2020-06-30 | 0.774112 | 0.793996 | 1699 | 0 |
| challenger | family_drop_intraday_volume_structure | 16 | 2022-10-01 | 2022-12-31 | 0.775086 | 0.794279 | 1818 | 0 |
| baseline | all_A_engineerable | 20 | 2023-10-01 | 2023-12-31 | 0.775301 | 0.806835 | 673 | 0 |
| baseline | pre_new_A_engineerable_control | 23 | 2024-07-01 | 2024-09-30 | 0.777555 | 0.821958 | 337 | 0 |
| challenger | family_drop_intraday_volume_structure | 23 | 2024-07-01 | 2024-09-30 | 0.777578 | 0.821023 | 352 | 0 |
| baseline | pre_new_A_engineerable_control | 6 | 2020-04-01 | 2020-06-30 | 0.780099 | 0.799881 | 1684 | 0 |
| baseline | all_A_engineerable | 25 | 2025-01-01 | 2025-03-31 | 0.781421 | 0.804313 | 1252 | 0 |
| baseline | all_A_engineerable | 12 | 2021-10-01 | 2021-12-31 | 0.782074 | 0.798051 | 2565 | 0 |
| challenger | family_drop_intraday_volume_structure | 6 | 2020-04-01 | 2020-06-30 | 0.782211 | 0.801610 | 1739 | 0 |
| baseline | pre_new_A_engineerable_control | 12 | 2021-10-01 | 2021-12-31 | 0.783219 | 0.799749 | 2387 | 0 |
| challenger | family_drop_intraday_volume_structure | 12 | 2021-10-01 | 2021-12-31 | 0.788986 | 0.802809 | 3347 | 0 |
| baseline | pre_new_A_engineerable_control | 7 | 2020-07-01 | 2020-09-30 | 0.792027 | 0.804411 | 4126 | 0 |
| challenger | family_drop_intraday_volume_structure | 7 | 2020-07-01 | 2020-09-30 | 0.792027 | 0.804411 | 4126 | 0 |
| baseline | pre_new_A_engineerable_control | 27 | 2025-07-01 | 2025-09-30 | 0.792813 | 0.814619 | 1327 | 0 |
| challenger | family_drop_intraday_volume_structure | 27 | 2025-07-01 | 2025-09-30 | 0.792813 | 0.814619 | 1327 | 0 |

## Risk Notes

- This report compares only full 23-fold fixed_recent_36m rows.
- A challenger may proceed only if it improves tail stability without unacceptable mean/accuracy drawdown and with P0=0.
- PhaseC, Q1, and April remain outside the selection loop.

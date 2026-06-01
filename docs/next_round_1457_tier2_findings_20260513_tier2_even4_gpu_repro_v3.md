# 14:57 Next-Round Tier-2 Findings (20260513_tier2_even4_gpu_repro_v3)

- Created at: 2026-05-13T09:39:47.038904+00:00
- Completed matrix rows: 48
- Source CSV: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_results_20260513_tier2_even4_gpu_repro_v3.csv`
- External audit: P0=0, P1=0, WIP=0

## Decision Snapshot

- Tier-2 leader: `pre_new_A_engineerable_control + fixed_recent_36m`; mean Wilson95=0.80013, worst=0.780099.
- Best variant family: `new_5min_family_only`.
- Best time-window scheme: `fixed_recent_36m`.
- Stable window candidate: `pre_new_A_engineerable_control + fixed_recent_36m`.
- This is a formal 4-fold GPU-only screen; it narrows candidates but does not freeze a champion by itself.

## Self Audit

| level | code | status | detail |
|---|---|---|---|
| P1 | expected_fold_rows | PASS | Completed fold rows 48/48. |
| P0 | no_p0_selected | PASS | P0 selected total 0. |
| P0 | single_expected_backend | PASS | Backends ['gpu']; expected gpu. |
| P0 | single_expected_python | PASS | Python envs ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains .venv5090. |
| P1 | bundle_validation_passed | PASS | Rows with failed bundle validation 0. |

## Combo Leaderboard

| variant_id | scheme | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|---|
| pre_new_A_engineerable_control | fixed_recent_36m | 4 | 0.800130 | 0.780099 | 0.015243 | 0.814980 | 13868 | 0 |
| new_5min_family_only | fixed_recent_36m | 4 | 0.799649 | 0.786867 | 0.008659 | 0.814804 | 13459 | 0 |
| all_A_engineerable | fixed_recent_36m | 4 | 0.796810 | 0.774112 | 0.015956 | 0.811561 | 14052 | 0 |
| new_5min_family_only | fixed_start_2020 | 4 | 0.790366 | 0.737628 | 0.035163 | 0.816511 | 11385 | 0 |
| all_A_engineerable | expanding_from_fair_start | 4 | 0.789758 | 0.727409 | 0.048126 | 0.810444 | 6821 | 0 |
| all_A_engineerable | fixed_start_2020 | 4 | 0.787553 | 0.734405 | 0.035524 | 0.809345 | 12089 | 0 |
| pre_new_A_engineerable_control | expanding_from_fair_start | 4 | 0.785881 | 0.717729 | 0.049343 | 0.807141 | 6734 | 0 |
| pre_new_A_engineerable_control | fixed_start_2018 | 4 | 0.784264 | 0.721163 | 0.045713 | 0.810326 | 5332 | 0 |
| new_5min_family_only | expanding_from_fair_start | 4 | 0.783170 | 0.712348 | 0.054255 | 0.803831 | 7098 | 0 |
| new_5min_family_only | fixed_start_2018 | 4 | 0.782089 | 0.723416 | 0.040366 | 0.806743 | 5448 | 0 |
| all_A_engineerable | fixed_start_2018 | 4 | 0.779824 | 0.715427 | 0.043800 | 0.804856 | 5199 | 0 |
| pre_new_A_engineerable_control | fixed_start_2020 | 4 | 0.769728 | 0.646350 | 0.082408 | 0.790121 | 11415 | 0 |

## Variant Aggregate

| variant_id | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| new_5min_family_only | 16 | 0.788819 | 0.712348 | 0.035063 | 0.810472 | 37390 | 0 |
| all_A_engineerable | 16 | 0.788486 | 0.715427 | 0.034487 | 0.809052 | 38161 | 0 |
| pre_new_A_engineerable_control | 16 | 0.785001 | 0.646350 | 0.049327 | 0.805642 | 37349 | 0 |

## Time-Window Aggregate

| scheme | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| fixed_recent_36m | 12 | 0.798863 | 0.774112 | 0.012474 | 0.813782 | 41379 | 0 |
| expanding_from_fair_start | 12 | 0.786270 | 0.712348 | 0.045896 | 0.807139 | 20653 | 0 |
| fixed_start_2020 | 12 | 0.782549 | 0.646350 | 0.051231 | 0.805326 | 34889 | 0 |
| fixed_start_2018 | 12 | 0.782059 | 0.715427 | 0.039257 | 0.807308 | 15979 | 0 |

## Worst Rows

| variant_id | scheme | outer_fold | outer_valid_start | outer_valid_end | wilson_95 | confident_accuracy | confident_count | p0_selected_count |
|---|---|---|---|---|---|---|---|---|
| pre_new_A_engineerable_control | fixed_start_2020 | 6 | 2020-04-01 | 2020-06-30 | 0.646350 | 0.682853 | 659 | 0 |
| new_5min_family_only | expanding_from_fair_start | 19 | 2023-07-01 | 2023-09-30 | 0.712348 | 0.742690 | 855 | 0 |
| all_A_engineerable | fixed_start_2018 | 19 | 2023-07-01 | 2023-09-30 | 0.715427 | 0.747112 | 779 | 0 |
| pre_new_A_engineerable_control | expanding_from_fair_start | 19 | 2023-07-01 | 2023-09-30 | 0.717729 | 0.749357 | 778 | 0 |
| pre_new_A_engineerable_control | fixed_start_2018 | 19 | 2023-07-01 | 2023-09-30 | 0.721163 | 0.752179 | 803 | 0 |
| new_5min_family_only | fixed_start_2018 | 19 | 2023-07-01 | 2023-09-30 | 0.723416 | 0.753939 | 825 | 0 |
| all_A_engineerable | expanding_from_fair_start | 19 | 2023-07-01 | 2023-09-30 | 0.727409 | 0.757362 | 849 | 0 |
| all_A_engineerable | fixed_start_2020 | 6 | 2020-04-01 | 2020-06-30 | 0.734405 | 0.778350 | 388 | 0 |
| new_5min_family_only | fixed_start_2020 | 6 | 2020-04-01 | 2020-06-30 | 0.737628 | 0.796296 | 216 | 0 |
| new_5min_family_only | expanding_from_fair_start | 28 | 2025-10-01 | 2025-12-31 | 0.769114 | 0.785921 | 2415 | 0 |
| all_A_engineerable | fixed_recent_36m | 6 | 2020-04-01 | 2020-06-30 | 0.774112 | 0.793996 | 1699 | 0 |
| all_A_engineerable | expanding_from_fair_start | 28 | 2025-10-01 | 2025-12-31 | 0.776681 | 0.794310 | 2144 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 6 | 2020-04-01 | 2020-06-30 | 0.780099 | 0.799881 | 1684 | 0 |
| pre_new_A_engineerable_control | expanding_from_fair_start | 28 | 2025-10-01 | 2025-12-31 | 0.781390 | 0.798193 | 2324 | 0 |
| pre_new_A_engineerable_control | fixed_start_2018 | 28 | 2025-10-01 | 2025-12-31 | 0.782924 | 0.800277 | 2168 | 0 |
| new_5min_family_only | fixed_recent_36m | 6 | 2020-04-01 | 2020-06-30 | 0.786867 | 0.806748 | 1630 | 0 |
| all_A_engineerable | fixed_start_2018 | 28 | 2025-10-01 | 2025-12-31 | 0.789374 | 0.806586 | 2156 | 0 |
| new_5min_family_only | fixed_start_2018 | 28 | 2025-10-01 | 2025-12-31 | 0.792115 | 0.808753 | 2285 | 0 |
| new_5min_family_only | fixed_start_2018 | 1 | 2019-01-01 | 2019-03-31 | 0.797418 | 0.815965 | 1804 | 0 |
| all_A_engineerable | fixed_recent_36m | 28 | 2025-10-01 | 2025-12-31 | 0.799280 | 0.812590 | 3479 | 0 |

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

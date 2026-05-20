# 14:57 Next-Round Tier-3 Full36 Rolling Findings (20260513_tier3_full36_gpu_v1)

- Created at: 2026-05-13T14:23:32.494769+00:00
- Completed matrix rows: 69
- Source CSV: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_fixed_matrix_results_20260513_tier3_full36_gpu_v1.csv`
- External audit: P0=0, P1=0, WIP=0

## Decision Snapshot

- Matrix leader: `all_A_engineerable + fixed_recent_36m`; mean Wilson95=0.784178, worst=0.695688.
- Best variant family: `all_A_engineerable`.
- Best time-window scheme: `fixed_recent_36m`.
- Stable window candidate: `pre_new_A_engineerable_control + fixed_recent_36m`.
- Formal strict-GPU full 23-fold rolling comparison on fixed_recent_36m; this is a stability gate, not the final frozen champion.

## Self Audit

| level | code | status | detail |
|---|---|---|---|
| P1 | expected_fold_rows | PASS | Completed fold rows 69/69. |
| P0 | no_p0_selected | PASS | P0 selected total 0. |
| P0 | single_expected_backend | PASS | Backends ['gpu']; expected gpu. |
| P0 | single_expected_python | PASS | Python envs ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains .venv5090. |
| P1 | bundle_validation_passed | PASS | Rows with failed bundle validation 0. |

## Combo Leaderboard

| variant_id | scheme | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|---|
| all_A_engineerable | fixed_recent_36m | 23 | 0.784178 | 0.695688 | 0.037504 | 0.805330 | 53843 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 23 | 0.783150 | 0.717784 | 0.032977 | 0.803986 | 54180 | 0 |
| new_5min_family_only | fixed_recent_36m | 23 | 0.781391 | 0.694700 | 0.038039 | 0.802489 | 53881 | 0 |

## Variant Aggregate

| variant_id | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| all_A_engineerable | 23 | 0.784178 | 0.695688 | 0.037504 | 0.805330 | 53843 | 0 |
| pre_new_A_engineerable_control | 23 | 0.783150 | 0.717784 | 0.032977 | 0.803986 | 54180 | 0 |
| new_5min_family_only | 23 | 0.781391 | 0.694700 | 0.038039 | 0.802489 | 53881 | 0 |

## Time-Window Aggregate

| scheme | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| fixed_recent_36m | 69 | 0.782907 | 0.694700 | 0.035726 | 0.803935 | 161904 | 0 |

## Worst Rows

| variant_id | scheme | outer_fold | outer_valid_start | outer_valid_end | wilson_95 | confident_accuracy | confident_count | p0_selected_count |
|---|---|---|---|---|---|---|---|---|
| new_5min_family_only | fixed_recent_36m | 19 | 2023-07-01 | 2023-09-30 | 0.694700 | 0.728551 | 711 | 0 |
| all_A_engineerable | fixed_recent_36m | 19 | 2023-07-01 | 2023-09-30 | 0.695688 | 0.730044 | 689 | 0 |
| new_5min_family_only | fixed_recent_36m | 14 | 2022-04-01 | 2022-06-30 | 0.716754 | 0.734520 | 2471 | 0 |
| new_5min_family_only | fixed_recent_36m | 18 | 2023-04-01 | 2023-06-30 | 0.717538 | 0.739027 | 1686 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 14 | 2022-04-01 | 2022-06-30 | 0.717784 | 0.735889 | 2374 | 0 |
| all_A_engineerable | fixed_recent_36m | 18 | 2023-04-01 | 2023-06-30 | 0.723692 | 0.746084 | 1532 | 0 |
| all_A_engineerable | fixed_recent_36m | 14 | 2022-04-01 | 2022-06-30 | 0.725748 | 0.743687 | 2376 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 19 | 2023-07-01 | 2023-09-30 | 0.732874 | 0.762813 | 839 | 0 |
| new_5min_family_only | fixed_recent_36m | 22 | 2024-04-01 | 2024-06-30 | 0.736376 | 0.757432 | 1682 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 18 | 2023-04-01 | 2023-06-30 | 0.737522 | 0.758166 | 1745 | 0 |
| all_A_engineerable | fixed_recent_36m | 22 | 2024-04-01 | 2024-06-30 | 0.750756 | 0.773952 | 1336 | 0 |
| new_5min_family_only | fixed_recent_36m | 25 | 2025-01-01 | 2025-03-31 | 0.751203 | 0.773938 | 1389 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 22 | 2024-04-01 | 2024-06-30 | 0.752154 | 0.773732 | 1538 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 20 | 2023-10-01 | 2023-12-31 | 0.754507 | 0.784537 | 789 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 17 | 2023-01-01 | 2023-03-31 | 0.756088 | 0.787176 | 733 | 0 |
| all_A_engineerable | fixed_recent_36m | 24 | 2024-10-01 | 2024-12-31 | 0.762098 | 0.770941 | 8906 | 0 |
| new_5min_family_only | fixed_recent_36m | 20 | 2023-10-01 | 2023-12-31 | 0.764409 | 0.796687 | 664 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 25 | 2025-01-01 | 2025-03-31 | 0.764415 | 0.787736 | 1272 | 0 |
| all_A_engineerable | fixed_recent_36m | 23 | 2024-07-01 | 2024-09-30 | 0.765579 | 0.809524 | 357 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 24 | 2024-10-01 | 2024-12-31 | 0.765849 | 0.774819 | 8562 | 0 |

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

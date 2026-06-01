# 14:57 Tier-4 Family Stability Screen (20260513_tier4_family36_stability_screen_v5)

- Created at: 2026-05-13T18:53:46.788321+00:00
- Screen folds: `[14, 18, 19, 28]`
- Baseline reference: `pre_new_A_engineerable_control` from `20260513_tier3_full36_gpu_v1` on the same folds.
- Stability-tradeoff tolerance: mean Wilson drawdown <= `0.001`, mean accuracy drawdown <= `0.002`.
- Role: family screen only; no champion can be promoted from this 4-fold result.
- Q1/April: not used for this screen and not allowed for model selection.

## Baseline Reference

| variant_id | scheme | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|---|
| pre_new_A_engineerable_control | fixed_recent_36m | 4 | 0.747108 | 0.717784 | 0.036417 | 0.767693 | 8252 | 0 |

## Stable Candidate

- Candidate: `family_drop_intraday_volume_structure`; mean=0.746333, min=0.719004, std=0.036439.
- Candidate type: `stability_tradeoff_candidate`.
- Candidate status means only: eligible for complete 23-fold rolling validation.

## Self Audit

| level | code | status | detail |
|---|---|---|---|
| P1 | expected_screen_rows | PASS | Completed rows 60/60. |
| P0 | no_error_rows | PASS | Non-completed rows 0. |
| P0 | no_p0_selected | PASS | P0 selected total 0. |
| P0 | single_expected_backend | PASS | Backends ['gpu']; expected gpu. |
| P0 | single_expected_python | PASS | Python envs ['C:\\Users\\zzzzzzl\\Desktop\\1\\.venv5090\\Scripts\\python.exe']; expected contains .venv5090. |

## Leaderboard

| variant_id | folds | mean_wilson95 | min_wilson95 | std_wilson95 | mean_accuracy | total_candidates | delta_mean_wilson95 | delta_min_wilson95 | strict_candidate | stability_tradeoff_candidate | candidate_type | needs_full_23fold |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| family_drop_intraday_volume_structure | 4 | 0.746333 | 0.719004 | 0.036439 | 0.766550 | 8487 | -0.000775 | 0.001220 | False | True | stability_tradeoff_candidate | True |
| family_drop_technical_pattern | 4 | 0.745869 | 0.714124 | 0.036807 | 0.766621 | 8058 | -0.001239 | -0.003660 | False | False | screen_only | True |
| family_drop_relative_strength | 4 | 0.744570 | 0.714124 | 0.034318 | 0.765266 | 8228 | -0.002537 | -0.003660 | False | False | screen_only | True |
| family_drop_market_breadth | 4 | 0.742310 | 0.714124 | 0.036695 | 0.763228 | 8395 | -0.004798 | -0.003660 | False | False | screen_only | True |
| family_drop_intraday_momentum | 4 | 0.738988 | 0.709356 | 0.041269 | 0.759522 | 8649 | -0.008120 | -0.008428 | False | False | screen_only | True |
| family_drop_intraday_price_structure | 4 | 0.738360 | 0.706984 | 0.042448 | 0.758794 | 8295 | -0.008747 | -0.010800 | False | False | screen_only | True |
| family_drop_momentum | 4 | 0.740033 | 0.706932 | 0.043043 | 0.760281 | 8454 | -0.007075 | -0.010852 | False | False | screen_only | True |
| family_drop_capacity_derivative | 4 | 0.735175 | 0.704674 | 0.041111 | 0.756188 | 8195 | -0.011933 | -0.013110 | False | False | screen_only | True |
| family_drop_price_structure | 4 | 0.735887 | 0.701755 | 0.044224 | 0.757310 | 8060 | -0.011221 | -0.016029 | False | False | screen_only | True |
| family_drop_volume_structure | 4 | 0.734275 | 0.701755 | 0.041305 | 0.755598 | 8352 | -0.012833 | -0.016029 | False | False | screen_only | True |
| family_drop_volume_quality | 4 | 0.738197 | 0.698280 | 0.046024 | 0.758807 | 8284 | -0.008911 | -0.019504 | False | False | screen_only | True |
| family_drop_liquidity | 4 | 0.737478 | 0.698280 | 0.044680 | 0.758110 | 8277 | -0.009630 | -0.019504 | False | False | screen_only | True |
| family_drop_intraday_risk | 4 | 0.737291 | 0.697531 | 0.044900 | 0.758177 | 8219 | -0.009817 | -0.020254 | False | False | screen_only | True |
| family_drop_stk_auction_tier1b | 4 | 0.737243 | 0.696696 | 0.045040 | 0.758445 | 8152 | -0.009865 | -0.021088 | False | False | screen_only | True |
| family_add_intraday_structure | 4 | 0.736102 | 0.695688 | 0.044295 | 0.758101 | 8076 | -0.011006 | -0.022096 | False | False | screen_only | True |

## Worst-Window Rows

| variant_id | outer_fold | outer_valid_start | outer_valid_end | wilson_95 | confident_accuracy | confident_count | p0_selected_count |
|---|---|---|---|---|---|---|---|
| family_add_intraday_structure | 19 | 2023-07-01 | 2023-09-30 | 0.695688 | 0.730044 | 689 | 0 |
| family_drop_stk_auction_tier1b | 19 | 2023-07-01 | 2023-09-30 | 0.696696 | 0.728771 | 789 | 0 |
| family_drop_intraday_risk | 19 | 2023-07-01 | 2023-09-30 | 0.697531 | 0.728337 | 854 | 0 |
| family_drop_liquidity | 19 | 2023-07-01 | 2023-09-30 | 0.698280 | 0.728070 | 912 | 0 |
| family_drop_volume_quality | 19 | 2023-07-01 | 2023-09-30 | 0.698280 | 0.728070 | 912 | 0 |
| family_drop_price_structure | 19 | 2023-07-01 | 2023-09-30 | 0.701755 | 0.733758 | 785 | 0 |
| family_drop_volume_structure | 19 | 2023-07-01 | 2023-09-30 | 0.701755 | 0.733758 | 785 | 0 |
| family_drop_capacity_derivative | 19 | 2023-07-01 | 2023-09-30 | 0.704674 | 0.735469 | 843 | 0 |
| family_drop_momentum | 19 | 2023-07-01 | 2023-09-30 | 0.706932 | 0.735444 | 979 | 0 |
| family_drop_intraday_price_structure | 19 | 2023-07-01 | 2023-09-30 | 0.706984 | 0.735597 | 972 | 0 |
| family_drop_intraday_momentum | 19 | 2023-07-01 | 2023-09-30 | 0.709356 | 0.739953 | 846 | 0 |
| family_drop_intraday_price_structure | 14 | 2022-04-01 | 2022-06-30 | 0.714124 | 0.732634 | 2289 | 0 |
| family_drop_intraday_risk | 14 | 2022-04-01 | 2022-06-30 | 0.714124 | 0.732634 | 2289 | 0 |
| family_drop_liquidity | 14 | 2022-04-01 | 2022-06-30 | 0.714124 | 0.732634 | 2289 | 0 |
| family_drop_market_breadth | 14 | 2022-04-01 | 2022-06-30 | 0.714124 | 0.732634 | 2289 | 0 |
| family_drop_momentum | 14 | 2022-04-01 | 2022-06-30 | 0.714124 | 0.732634 | 2289 | 0 |
| family_drop_relative_strength | 14 | 2022-04-01 | 2022-06-30 | 0.714124 | 0.732634 | 2289 | 0 |
| family_drop_technical_pattern | 14 | 2022-04-01 | 2022-06-30 | 0.714124 | 0.732634 | 2289 | 0 |
| family_drop_volume_quality | 14 | 2022-04-01 | 2022-06-30 | 0.714124 | 0.732634 | 2289 | 0 |
| family_drop_volume_structure | 14 | 2022-04-01 | 2022-06-30 | 0.714124 | 0.732634 | 2289 | 0 |
| family_drop_price_structure | 14 | 2022-04-01 | 2022-06-30 | 0.714447 | 0.732955 | 2288 | 0 |
| family_drop_stk_auction_tier1b | 14 | 2022-04-01 | 2022-06-30 | 0.714770 | 0.733275 | 2287 | 0 |
| family_drop_capacity_derivative | 14 | 2022-04-01 | 2022-06-30 | 0.715404 | 0.733675 | 2343 | 0 |
| pre_new_A_engineerable_control | 14 | 2022-04-01 | 2022-06-30 | 0.717784 | 0.735889 | 2374 | 0 |
| family_drop_intraday_volume_structure | 19 | 2023-07-01 | 2023-09-30 | 0.719004 | 0.748337 | 902 | 0 |
| family_drop_intraday_momentum | 18 | 2023-04-01 | 2023-06-30 | 0.722155 | 0.742889 | 1793 | 0 |
| family_drop_market_breadth | 19 | 2023-07-01 | 2023-09-30 | 0.722200 | 0.753494 | 787 | 0 |
| family_add_intraday_structure | 18 | 2023-04-01 | 2023-06-30 | 0.723692 | 0.746084 | 1532 | 0 |
| family_drop_intraday_momentum | 14 | 2022-04-01 | 2022-06-30 | 0.724348 | 0.741988 | 2465 | 0 |
| family_drop_capacity_derivative | 18 | 2023-04-01 | 2023-06-30 | 0.725058 | 0.746313 | 1695 | 0 |

## Risk Notes

- This screen deliberately uses known weak rolling folds plus the latest fold to reduce single-window optimism.
- It still has only 4 folds, so any positive family result must run complete 23-fold fixed_recent_36m rolling before champion consideration.
- PhaseC, Q1, and April do not participate in selection; Q1/April are only post-freeze seen-research consistency checks.

# 14:57 Next-Round Tier-1 Findings (20260513_tier1_even)

- Created at: 2026-05-13T02:14:13.681952+00:00
- Fixed matrix rows: 36
- Existing bundle score rows: 24
- Audit: P0=0, P1=0, WIP=0

## Decisions

- Tier-1 fixed-matrix leader: `all_A_engineerable + expanding_from_fair_start`.
- Most stable control: `pre_new_A_engineerable_control` with `fixed_start_2018` or `expanding_from_fair_start`.
- `C174-C188` has signal, but `new_5min_family_only` is not a standalone champion; keep it for add/delete and full rolling tests.
- `all_A_plus_B_t1_proxy_policy` is proxy-pending; do not run it until explicit T-1/proxy feature columns exist.
- Do not choose a champion from this 2-fold-per-scheme tier; expand the top schemes to full rolling folds next.

## Fixed Matrix By Variant

| variant_id | folds | mean_wilson95 | min_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|
| pre_new_A_engineerable_control | 12 | 0.781504 | 0.743212 | 0.798534 | 27740 | 0 |
| all_A_engineerable | 12 | 0.778169 | 0.733209 | 0.795329 | 27563 | 0 |
| new_5min_family_only | 12 | 0.777848 | 0.732642 | 0.794683 | 28917 | 0 |

## Fixed Matrix By Scheme

| scheme | folds | mean_wilson95 | min_wilson95 | mean_accuracy | total_candidates |
|---|---|---|---|---|---|
| expanding_from_fair_start | 6 | 0.799085 | 0.769641 | 0.815444 | 13798 |
| fixed_start_2018 | 6 | 0.796949 | 0.770368 | 0.813307 | 13905 |
| fixed_start_2020 | 6 | 0.780487 | 0.774669 | 0.799066 | 11724 |
| fixed_recent_36m | 6 | 0.779964 | 0.773620 | 0.798323 | 11942 |
| fixed_recent_24m | 6 | 0.762505 | 0.746897 | 0.778022 | 17831 |
| fixed_recent_60m | 6 | 0.756054 | 0.732642 | 0.772928 | 15020 |

## Fixed Matrix Top Combos

| variant_id | scheme | folds | mean_wilson95 | min_wilson95 | mean_accuracy | total_candidates | p0_selected_total |
|---|---|---|---|---|---|---|---|
| all_A_engineerable | expanding_from_fair_start | 2 | 0.800317 | 0.776661 | 0.816801 | 4495 | 0 |
| pre_new_A_engineerable_control | fixed_start_2018 | 2 | 0.798616 | 0.780175 | 0.815284 | 4438 | 0 |
| pre_new_A_engineerable_control | expanding_from_fair_start | 2 | 0.798472 | 0.780341 | 0.815228 | 4397 | 0 |
| new_5min_family_only | expanding_from_fair_start | 2 | 0.798467 | 0.769641 | 0.814302 | 4906 | 0 |
| new_5min_family_only | fixed_start_2018 | 2 | 0.796796 | 0.770368 | 0.812796 | 4835 | 0 |
| all_A_engineerable | fixed_start_2018 | 2 | 0.795435 | 0.778225 | 0.811840 | 4632 | 0 |
| pre_new_A_engineerable_control | fixed_start_2020 | 2 | 0.783650 | 0.778579 | 0.801964 | 3928 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 2 | 0.781576 | 0.774594 | 0.799975 | 3935 | 0 |
| new_5min_family_only | fixed_recent_36m | 2 | 0.780712 | 0.773620 | 0.799280 | 3864 | 0 |
| new_5min_family_only | fixed_start_2020 | 2 | 0.780574 | 0.774845 | 0.798940 | 4014 | 0 |
| all_A_engineerable | fixed_recent_36m | 2 | 0.777604 | 0.776862 | 0.795716 | 4143 | 0 |
| all_A_engineerable | fixed_start_2020 | 2 | 0.777236 | 0.774669 | 0.796295 | 3782 | 0 |
| pre_new_A_engineerable_control | fixed_recent_24m | 2 | 0.765800 | 0.749647 | 0.781356 | 5848 | 0 |
| all_A_engineerable | fixed_recent_24m | 2 | 0.763733 | 0.751217 | 0.779478 | 5663 | 0 |
| pre_new_A_engineerable_control | fixed_recent_60m | 2 | 0.760910 | 0.743212 | 0.777393 | 5194 | 0 |
| new_5min_family_only | fixed_recent_24m | 2 | 0.757980 | 0.746897 | 0.773231 | 6320 | 0 |
| all_A_engineerable | fixed_recent_60m | 2 | 0.754689 | 0.733209 | 0.771842 | 4848 | 0 |
| new_5min_family_only | fixed_recent_60m | 2 | 0.752562 | 0.732642 | 0.769550 | 4978 | 0 |

## 2025Q4 Stress Fold

| variant_id | scheme | wilson_95 | confident_accuracy | confident_count | p0_selected_count |
|---|---|---|---|---|---|
| pre_new_A_engineerable_control | fixed_recent_24m | 0.781953 | 0.798788 | 2311 | 0 |
| pre_new_A_engineerable_control | expanding_from_fair_start | 0.780341 | 0.797932 | 2128 | 0 |
| pre_new_A_engineerable_control | fixed_start_2018 | 0.780175 | 0.797603 | 2169 | 0 |
| all_A_engineerable | fixed_start_2020 | 0.779803 | 0.796834 | 2274 | 0 |
| pre_new_A_engineerable_control | fixed_recent_60m | 0.778608 | 0.795863 | 2224 | 0 |
| pre_new_A_engineerable_control | fixed_start_2020 | 0.778579 | 0.795854 | 2219 | 0 |
| all_A_engineerable | fixed_start_2018 | 0.778225 | 0.794787 | 2417 | 0 |
| all_A_engineerable | fixed_recent_36m | 0.776862 | 0.793416 | 2430 | 0 |
| all_A_engineerable | expanding_from_fair_start | 0.776661 | 0.793920 | 2237 | 0 |
| all_A_engineerable | fixed_recent_24m | 0.776250 | 0.792875 | 2414 | 0 |
| all_A_engineerable | fixed_recent_60m | 0.776170 | 0.793776 | 2153 | 0 |
| new_5min_family_only | fixed_start_2020 | 0.774845 | 0.791528 | 2408 | 0 |
| pre_new_A_engineerable_control | fixed_recent_36m | 0.774594 | 0.791795 | 2267 | 0 |
| new_5min_family_only | fixed_recent_36m | 0.773620 | 0.791099 | 2202 | 0 |
| new_5min_family_only | fixed_recent_60m | 0.772482 | 0.790000 | 2200 | 0 |
| new_5min_family_only | fixed_start_2018 | 0.770368 | 0.787351 | 2356 | 0 |
| new_5min_family_only | expanding_from_fair_start | 0.769641 | 0.786622 | 2362 | 0 |
| new_5min_family_only | fixed_recent_24m | 0.769063 | 0.785984 | 2383 | 0 |

## Existing Bundle Score-Only

Existing bundles are score-only and should not be merged numerically with fixed-matrix retraining metrics.

| bundle_id | folds | mean_pge075_wilson95 | min_pge075_wilson95 | mean_daily_top5_wilson95 | min_daily_top5_wilson95 | pge075_count |
|---|---|---|---|---|---|---|
| baseline_phasec | 12 | 0.764021 | 0.710205 | 0.740424 | 0.691047 | 43555 |
| baseline_s2 | 12 | 0.776609 | 0.717243 | 0.730195 | 0.680573 | 44453 |

## Existing Bundle By Outer Fold

| bundle_id | outer_fold | outer_valid_start | outer_valid_end | pge075_wilson95 | pge075_accuracy | pge075_count | daily_top5_wilson95 | daily_top5_accuracy |
|---|---|---|---|---|---|---|---|---|
| baseline_s2 | 1 | 2019-01-01 | 2019-03-31 | 0.717243 | 0.726189 | 9733.000000 | 0.772436 | 0.820690 |
| baseline_phasec | 1 | 2019-01-01 | 2019-03-31 | 0.710205 | 0.719219 | 9730.000000 | 0.746483 | 0.796552 |
| baseline_phasec | 2 | 2019-04-01 | 2019-06-30 | 0.718301 | 0.738180 | 1967.000000 | 0.691047 | 0.743333 |
| baseline_s2 | 2 | 2019-04-01 | 2019-06-30 | 0.746805 | 0.765113 | 2167.000000 | 0.680573 | 0.733333 |
| baseline_phasec | 6 | 2020-04-01 | 2020-06-30 | 0.741658 | 0.766957 | 1150.000000 | 0.750629 | 0.800000 |
| baseline_s2 | 6 | 2020-04-01 | 2020-06-30 | 0.760266 | 0.785392 | 1109.000000 | 0.732540 | 0.783051 |
| baseline_phasec | 14 | 2022-04-01 | 2022-06-30 | 0.739884 | 0.752290 | 4804.000000 | 0.736149 | 0.786441 |
| baseline_s2 | 14 | 2022-04-01 | 2022-06-30 | 0.768851 | 0.780994 | 4630.000000 | 0.714566 | 0.766102 |
| baseline_phasec | 28 | 2025-10-01 | 2025-12-31 | 0.801057 | 0.816693 | 2504.000000 | 0.743945 | 0.793333 |
| baseline_s2 | 28 | 2025-10-01 | 2025-12-31 | 0.808106 | 0.823065 | 2662.000000 | 0.726209 | 0.776667 |

## Next Actions

1. Expand full rolling folds for `all_A_engineerable`, `pre_new_A_engineerable_control`, and `new_5min_family_only` on `expanding_from_fair_start`, `fixed_start_2018`, `fixed_start_2020`, and `fixed_recent_36m`.
2. Keep `fixed_recent_24m` and `fixed_recent_60m` as diagnostic windows, not primary champion selectors.
3. Implement explicit B-class proxy columns before rerunning the B-policy variant.
4. After full rolling, use Q1/April only as seen-research consistency checks, not as final pass/fail.

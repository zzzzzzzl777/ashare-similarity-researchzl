# Dataset Split Research Report - 20260510

## Executive Decision

- Current complete feature evidence starts at label_date 2023-06-09 and ends at 2026-04-30.
- Use nested time splits: fit_train -> inner_valid -> outer_valid; never calibrate on outer_valid.
- Use 3-month outer validation as the main comparison unit; keep 1/2-month windows as drift diagnostics and 6/12-month windows as stability summaries.
- Keep Q1 2026 and April 2026 as seen_research_test only; the next clean final_forward must start after the data protocol is frozen.
- With the current cache, the fully fair quarterly protocol is expanding-from-current-cache-start.
- The current cache is too short for a clean 24m/30m quarterly protocol across all 2024-2025 folds; rebuild older features before judging longer windows.
- Do not claim 2022/2021/2020 start windows are better until a same-schema historical feature cache is rebuilt and audited.
- Historical rebuilds should include at least 120 trading days of warmup before the first intended train label month.

## Selected Evidence Cache

- Cache: `E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_1d06fd67ca1e1175_t1shifted.parquet`
- Rows: 385,622; columns: 817; features: 804
- Event dates: 2023-06-08 to 2026-04-29
- Label dates: 2023-06-09 to 2026-04-30
- T-1 shifted: True
- Forbidden/P0/Class-C columns present in superset: 58 (must be excluded during training)

## Current Protocol Check

- Current shape: fit through 2025-06-30, dev_valid 2025-07-01 to 2025-12-31, Q1/April seen research.
- Fit to 2025-06 filtered rows: 204,669
- 2025H2 dev_valid filtered rows: 86,511
- Q1 2026 seen filtered rows: 43,596
- April 2026 seen filtered rows: 14,010
- Risk: A single 2025H2 tail validation has many rows but only one contiguous market regime.

## Existing Result Context

- Phase C internal CV winner: HPO_budget200 with fold W95s [0.686853, 0.917473, 0.721861].
- Phase C Q1 winner-only seen report: W95=0.72875, count=11403.
- U95 rolling CV W95 folds: [0.714, 0.802, 0.774, 0.75, 0.721, 0.78] (min=0.7145, std=0.0318).
- Phase E frozen April p>=0.75: W95=0.781539, accuracy=0.812874, count=668.
- U95 rebuild seen checks: Q1 W95=0.841, April W95=0.7303; still not final-unseen.
- Phase C half-year folds and U95 bimonthly folds both show large fold-to-fold variation.
- Q1 and April results are useful consistency checks, but both are now seen research windows.
- Internal split selection should be decided before looking at new final_forward months.

## Metric Contract

- Primary: wilson_95_lower_at_p075, accuracy_at_p075, count_at_p075, coverage_at_p075
- Trading: daily_top3_wilson, daily_top5_wilson, daily_top10_wilson, active_days, max_single_day_share
- Stability: min_outer_window_w95, outer_window_std, worst_window, q1_april_decay_seen_only
- Calibration: brier, probability_bucket_monotonicity, raw_vs_isotonic_unique_score_count
- Engineering: selected_feature_forbidden_count, selected_feature_live_available_count, schema_match

## Data Roles

| Role | Start | End | Filtered Rows | Usage |
|---|---:|---:|---:|---|
| development_pool | 2023-06-09 | 2025-12-31 | 291,180 | fit_train, inner_valid, and outer_valid candidates only. |
| q1_2026_seen_research_test | 2026-01-01 | 2026-03-31 | 43,596 | Seen research test only; never final acceptance. |
| april_2026_seen_research_test | 2026-04-01 | 2026-04-30 | 14,010 | Seen research test only; never final acceptance. |
| final_forward | 2026-05-01 |  | 0 | Future unseen months after protocol freeze. |

## Split Manifest Summary

- Candidate split rows: 550
- Eligible split rows: 124

Fully eligible scheme/outer-window pairs under the current cache:

| Scheme | Outer Valid Months | Folds | Min Fit Rows | Min Inner Rows | Min Outer Rows |
|---|---:|---:|---:|---:|---:|
| expanding_from_fair_start | 1 | 24 | 34,256 | 3,875 | 3,875 |
| expanding_from_fair_start | 2 | 12 | 26,457 | 8,928 | 8,928 |
| expanding_from_fair_start | 3 | 8 | 21,673 | 14,689 | 14,689 |
| expanding_from_fair_start | 6 | 4 | 21,673 | 17,559 | 39,415 |
| expanding_from_fair_start | 12 | 2 | 21,673 | 19,248 | 99,497 |

Partially eligible pairs are useful diagnostics only; they cannot prove the full requested window.

| Scheme | Outer Valid Months | Eligible Folds | Total Folds |
|---|---:|---:|---:|
| fixed_recent_12m | 1 | 18 | 24 |
| fixed_recent_18m | 1 | 12 | 24 |
| fixed_recent_24m | 1 | 6 | 24 |
| fixed_recent_12m | 2 | 9 | 12 |
| fixed_recent_18m | 2 | 6 | 12 |
| fixed_recent_24m | 2 | 3 | 12 |
| fixed_recent_12m | 3 | 6 | 8 |
| fixed_recent_18m | 3 | 4 | 8 |
| fixed_recent_24m | 3 | 2 | 8 |
| fixed_recent_12m | 6 | 3 | 4 |
| fixed_recent_18m | 6 | 2 | 4 |
| fixed_recent_24m | 6 | 1 | 4 |
| fixed_recent_12m | 12 | 1 | 2 |
| fixed_recent_18m | 12 | 1 | 2 |

## Monthly Timeline Snapshot

| Month | Role | Filtered Rows | Label Days | Symbols | Filtered Positive Rate |
|---|---|---:|---:|---:|---:|
| 2025-07 | dev_pool_candidate | 14,180 | 23 | 2,096 | 0.5624 |
| 2025-08 | dev_pool_candidate | 16,690 | 21 | 2,223 | 0.6209 |
| 2025-09 | dev_pool_candidate | 17,151 | 22 | 2,037 | 0.6335 |
| 2025-10 | dev_pool_candidate | 11,580 | 17 | 1,865 | 0.6237 |
| 2025-11 | dev_pool_candidate | 13,064 | 20 | 1,917 | 0.6287 |
| 2025-12 | dev_pool_candidate | 13,846 | 23 | 1,767 | 0.6098 |
| 2026-01 | seen_research_test | 18,426 | 20 | 2,209 | 0.6502 |
| 2026-02 | seen_research_test | 9,305 | 14 | 1,721 | 0.6666 |
| 2026-03 | seen_research_test | 15,865 | 22 | 1,963 | 0.6571 |
| 2026-04 | seen_research_test | 14,010 | 21 | 1,990 | 0.6480 |

## Lookback / Rebuild Note

- Max feature-name lookback hint: 120 from `former_leader_memory_120`.
- This is a regex hint, not a substitute for auditing each feature builder.
- If researching 2022/2021/2020 starts, rebuild the feature cache with the same 14:57-safe schema and enough warmup before the first label month.

## Artifacts

- JSON: `E:\ashare_similarity_runtime\data\reports\prediction\dataset_split_research_20260510.json`
- Split manifest CSV: `E:\ashare_similarity_runtime\data\reports\prediction\dataset_split_manifest_20260510.csv`
- Monthly timeline CSV: `E:\ashare_similarity_runtime\data\reports\prediction\dataset_monthly_timeline_20260510.csv`
- Feature cache inventory CSV: `E:\ashare_similarity_runtime\data\reports\prediction\dataset_feature_cache_inventory_20260510.csv`
- Raw daily monthly timeline CSV: `E:\ashare_similarity_runtime\data\reports\prediction\dataset_raw_daily_monthly_timeline_20260510.csv`

## Guardrails

- No model training was run by this script.
- No target definition or live interface was changed.
- Q1/April are recorded as seen research only.

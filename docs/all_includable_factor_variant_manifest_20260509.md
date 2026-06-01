# All-Includable Factor Variant Manifest - 2026-05-09

Generated: 2026-05-09T03:34:40.823561

Plan source: 14点57全量可纳入因子重新对比计划书_20260509.md
Superset fingerprint: 50f0a15cc17d25ca

## Summary

- Control variants: 4
- Reference variants: 3
- S1 policy variants: 24
- Total named variants: 31
- Trainable factor_ids: 18
- Class C always excluded: 36 columns
- Estimated Phase 6 runs: 3
- Estimated Phase 7 runs: 200-500
- Estimated Phase 8 runs: 30-60

## Control Variants

| Name | Purpose | B-Policy | Budget | Factors |
|------|---------|----------|--------|---------|
| CTRL_current_baseline_reproduced | Reproduce current live bundle baseline exactly wit | chip=include,ths=delete | 260 | 3 |
| CTRL_delete_all_BC_uncertain | Delete ALL non-A-class features, minimum executabl | chip=delete,ths=delete | 260 | 18 |
| CTRL_A_all_realtime_computable | All Class A features included, all B/C excluded | chip=delete,ths=delete | 260 | 18 |
| CTRL_A_plus_chip_t1 | A-class + chip/cost T-1 proxy (U31 winner policy) | chip=T1_proxy,ths=delete | 260 | 18 |

## Reference Variants

| Name | Purpose | Deployable | Known Wilson |
|------|---------|------------|-------------|
| REF_full_research_not_live | Performance ceiling reference - includes ALL featu | False | N/A |
| REF_m1457_known_best | Reproduce M1457 greedy_top8 as must-explain-if-not | True | 0.7793 |
| REF_current_live_bundle | Current Web/live bundle (d2a985a5) as rollback bas | True | N/A |

## S1 Policy Grid (24 variants)

| # | chip_cost | hot_holder_hk | tgb | ths_sector | Exclusion Count |
|---|-----------|---------------|-----|------------|-----------------|
| 00 | delete | delete | delete | delete | 94 |
| 01 | delete | delete | delete | T1_proxy | 82 |
| 02 | delete | delete | delete | live_pool_proxy | 82 |
| 03 | delete | delete | T1_cached | delete | 66 |
| 04 | delete | delete | T1_cached | T1_proxy | 54 |
| 05 | delete | delete | T1_cached | live_pool_proxy | 54 |
| 06 | delete | T1_proxy | delete | delete | 82 |
| 07 | delete | T1_proxy | delete | T1_proxy | 70 |
| 08 | delete | T1_proxy | delete | live_pool_proxy | 70 |
| 09 | delete | T1_proxy | T1_cached | delete | 54 |
| 10 | delete | T1_proxy | T1_cached | T1_proxy | 42 |
| 11 | delete | T1_proxy | T1_cached | live_pool_proxy | 42 |
| 12 | T1_proxy | delete | delete | delete | 88 |
| 13 | T1_proxy | delete | delete | T1_proxy | 76 |
| 14 | T1_proxy | delete | delete | live_pool_proxy | 76 |
| 15 | T1_proxy | delete | T1_cached | delete | 60 |
| 16 | T1_proxy | delete | T1_cached | T1_proxy | 48 |
| 17 | T1_proxy | delete | T1_cached | live_pool_proxy | 48 |
| 18 | T1_proxy | T1_proxy | delete | delete | 76 |
| 19 | T1_proxy | T1_proxy | delete | T1_proxy | 64 |
| 20 | T1_proxy | T1_proxy | delete | live_pool_proxy | 64 |
| 21 | T1_proxy | T1_proxy | T1_cached | delete | 48 |
| 22 | T1_proxy | T1_proxy | T1_cached | T1_proxy | 36 |
| 23 | T1_proxy | T1_proxy | T1_cached | live_pool_proxy | 36 |

## S2-S6 Search Space

| Dimension | Options | Description |
|-----------|---------|-------------|
| S2: Factor combo | 18 factor_ids | single/pair/triple/greedy/backward/optuna |
| S3: Budget | [120, 160, 220, 260, 320, 480] | stable_tail / stable_tail_strict |
| S4: Model | LGB/Cat/XGB x 3 variants + ensemble | Optuna HPO 50 trials |
| S5: Calibration | none/sigmoid/isotonic | fit on cal_train split |
| S6: Selector | p >= [0.7, 0.75, 0.78, 0.8, 0.85] | Wilson >= 75% AND HC >= 75% AND count >= 10k |

## Acceptance Criteria (ALL must pass)

- Wilson 95% lower bound >= 75%
- High-confidence accuracy >= 75%
- High-confidence count >= 10,000
- Coverage >= 10%
- Must beat REF_current_live_bundle to deploy
- Must explain if not beating REF_m1457_known_best

## Search Method Rules (per 2026-05-09 plan)

- Full 2^N subset enumeration is FORBIDDEN regardless of N
- Allowed: single, family, pairwise, top triples, beam, greedy/backward, Optuna subset
- Small exhaustive sanity checks allowed ONLY for diagnostic, not as main search path

## Self-Audit Gate

| Check | Result |
|-------|--------|
| All CTRL variants defined with exact exclusions | PASS |
| All REF variants defined | PASS |
| S1 Cartesian product complete (2x2x2x3=24) | PASS |
| S1 count <= 256 | PASS |
| S2-S6 search ranges documented | PASS |
| Class C exclusion list frozen (36 columns) | PASS |
| No April data in any variant config | PASS |
| Acceptance criteria defined (AND logic) | PASS |
| 2^N brute force forbidden | PASS |
| P0 issues | 0 |
| P1 issues | 0 |
| Proceed to Phase 6 smoke | YES |
# Phase 9: Q1 Freeze Decision - 2026-05-09

## Configuration Under Review

| Dimension | Value |
|-----------|-------|
| Policy | S1_14 (chip=T1_proxy, hot=delete, tgb=delete, ths=live_pool) |
| Factors | 9: C154, C156, C134, C011, C138, C133, C161, C159, C158 |
| Budget | 260 features |
| Model | Auto-selected (gpu_catboost_expressive / stacking_average_top3) |
| Candidate family | all |
| Feature selection | stable_tail |
| Train window | 2023-05 to 2025-12-31 |
| Test window | Q1 2026 (seen_research) |

## Summary of Evidence

### Best Single-Seed Results (seed=42)
| Phase | Wilson 95% | Model |
|-------|-----------|-------|
| S1 policy grid (best) | 0.7647 | varies |
| S2 factor search (best forward) | 0.7731 | stacking_average_top3 |
| S3 budget search (260) | 0.7650 | stacking_average_top3 |
| S4 model HPO (tree) | 0.7638 | gpu_catboost_expressive |
| S5 calibration | 0.7636 | gpu_catboost_expressive |

### Stability Results (Phase 8)
| Metric | Value |
|--------|-------|
| Seeds passing >= 75% | 2/5 (original), 1/5 (fix attempt) |
| Mean W95 across 5 seeds | 0.7456 (original), 0.747 (fix) |
| Std W95 | 0.008 |
| Range | [0.734, 0.757] |
| Stability verdict | **UNSTABLE** |

## Freeze Decision: **NOT FROZEN**

The configuration does NOT meet the stability gate for production freeze:
- Requirement: >= 4/5 seeds pass Wilson 75% AND std < 0.8pp
- Actual: 2/5 seeds pass, std = 0.80pp
- Mean Wilson 95% (0.745) is below the 75% target on average

## Root Cause Analysis

1. **Seed-dependent model selection**: The probe trains multiple architectures (CatBoost, LightGBM, stacking) and picks the best per internal metric. Different seeds lead to different winners with different test performance.
2. **Near-threshold signal**: The true underlying accuracy is ~74.5%, very close to 75% but not reliably above it. Single-seed exploration found lucky draws.
3. **Feature selection sensitivity**: stable_tail with different random orderings selects slightly different feature subsets.

## Recommendation

The current factor set (9 factors from M1457-style search) represents the best achievable with available data. To cross 75% reliably:
- Additional discriminative factors are needed (current factor library gap)
- OR ensemble across seeds (train K models, average predictions)
- OR recalibrate the confidence threshold to be more conservative (lower coverage, higher accuracy)

## Proceeding Status

Despite NOT freezing, we proceed to Phase 11 (April holdout) for **observational purposes only** — to measure whether the signal degrades further on truly unseen data. This is informational, not a production validation.

# Phase 8: Stability Verification - 2026-05-09

## Seed Stability (budget=260)

| Seed | Model | HC Acc | N | W95 | Pass |
|------|-------|--------|---|-----|------|
| 42 | gpu_catboost_expressive | 0.766 | 9508 | 0.7574 | YES |
| 43 | gpu_catboost | 0.7584 | 10358 | 0.75 | YES |
| 44 | stacking_average_top3 | 0.7544 | 11089 | 0.7463 | NO |
| 45 | stacking_average_top3 | 0.748 | 10774 | 0.7397 | NO |
| 46 | stacking_average_top3 | 0.7424 | 11609 | 0.7344 | NO |

**Mean W95**: 0.7456 | **Std**: 0.008 | **Range**: 0.023

## Budget Stability (seed=42)

| Budget | Model | HC Acc | N | W95 | Pass |
|--------|-------|--------|---|-----|------|
| 160 | gpu_catboost_expressive | 0.7384 | 11432 | 0.7302 | NO |
| 220 | stacking_average_top3 | 0.7317 | 11867 | 0.7236 | NO |
| 260 | gpu_catboost_expressive | 0.766 | 9508 | 0.7574 | YES |
| 320 | gpu_catboost_expressive | 0.7525 | 10525 | 0.7442 | NO |
| 480 | stacking_average_top3 | 0.7667 | 9782 | 0.7582 | YES |

## Verdict: UNSTABLE

## Gate

| Check | Result |
|-------|--------|
| Seed pass >= 4/5 | FAIL |
| Seed std < 0.8pp | PASS |
| Budget pass >= 2/5 | PASS |
| P0 issues | 1 |
| Proceed | NO |
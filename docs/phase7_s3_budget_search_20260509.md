# Phase 7 Layer 3: S3 Feature Budget Search - 2026-05-09

## Base: S1_14 + S2 best factor set

| Budget | Model | Pool | HC Acc | N | Coverage | W95 | Brier | Pass |
|--------|-------|------|--------|---|----------|-----|-------|------|
| 120 | gpu_catboost | 693.0 | 0.7244 | 12611 | 0.2931 | 0.7165 | 0.1976 | NO |
| 160 | gpu_catboost_expressive | 693.0 | 0.7383 | 11431 | 0.2657 | 0.7302 | 0.1927 | NO |
| 220 | gpu_catboost_expressive | 693.0 | 0.7339 | 11614 | 0.2699 | 0.7257 | 0.1957 | NO |
| 260 | stacking_average_top3 | 693.0 | 0.7735 | 9637 | 0.224 | 0.765 | 0.1709 | YES |
| 320 | gpu_catboost_expressive | 693.0 | 0.7533 | 10323 | 0.2399 | 0.7449 | 0.1801 | NO |
| 480 | gpu_catboost_expressive | 693.0 | 0.7616 | 10351 | 0.2406 | 0.7533 | 0.1762 | YES |

## Best: budget=260 W95=0.765

## Self-Audit Gate

| Check | Result |
|-------|--------|
| All budgets tested | PASS |
| At least one passes Wilson >= 75% | PASS |
| P0 issues | 0 |
| P1 issues | 0 |
| Proceed to S4 | YES |
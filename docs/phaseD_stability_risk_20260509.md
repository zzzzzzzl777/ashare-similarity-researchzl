# Phase D: Stability Risk Rating - 2026-05-09

## Config (Phase C Winner)
- Budget: 200
- Feature selection: stable_tail
- Candidate family: all
- P0 audit: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C

## 5-Seed Results

| Seed | Model | W95 | HC Acc | N | P0 | Pass |
|------|-------|-----|--------|---|----|------|
| 42 | gpu_catboost_expressive | 0.729182 | 0.7373 | 11455 | 0 | NO |
| 43 | gpu_catboost | 0.722365 | 0.7305 | 11556 | 0 | NO |
| 44 | stacking_average_top3 | 0.727926 | 0.7362 | 11107 | 0 | NO |
| 45 | gpu_catboost_expressive | 0.726141 | 0.734 | 12361 | 0 | NO |
| 46 | stacking_average_top3 | 0.728228 | 0.7364 | 11295 | 0 | NO |

## Statistics
- Mean W95: 0.7268
- Range: 0.7224 - 0.7292
- Pass rate: 0/5
- All P0=0: True

## Stability Grade: D
- 不可交付 - but still proceed to April for data collection

## Champion Bundle
- Run dir: None
- Best seed: 42 W95=0.729182

## Gate: PROCEED to Phase E
Stability is risk rating, not hard gate. All grades proceed to frozen April validation.
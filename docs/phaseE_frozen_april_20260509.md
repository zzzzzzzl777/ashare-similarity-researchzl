# Phase E: Frozen April Holdout + Web/Live Gate - 2026-05-09

## Methodology
- Frozen bundle score-only (NO retraining, NO run_gpu_next_day_probe)
- Champion from Phase D: model_bundle.pt
- P0 audit: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C

## April Holdout Results

| Threshold | N | Accuracy | Wilson 95% | Coverage |
|-----------|---|----------|------------|----------|
| p>=0.7 | 1930 | 0.740933 | 0.720921 | 0.128324 |
| p>=0.75 | 668 | 0.812874 | 0.781539 | 0.044415 |
| p>=0.78 | 565 | 0.815929 | 0.781876 | 0.037566 |
| p>=0.8 | 194 | 0.876289 | 0.822524 | 0.012899 |
| p>=0.85 | 24 | 0.916667 | 0.741508 | 0.001596 |

## Monthly Breakdown

- April 1H: N=5679 acc=0.6845 W95=0.6722
- April 2H: N=7799 acc=0.6665 W95=0.656

## Web/Live Gate
- Web gate: PASS
- P0 in selection: 0
- Web-forbidden in selection: 0

## Final Decision: WEAK_APRIL
- Web gate passes but April performance below threshold
- Stability: D

## Rollback Plan
- If April fails: keep current production, champion stays research
- If Web fails: retrain with web-safe features only
- If P0 found: re-run with stricter exclusion
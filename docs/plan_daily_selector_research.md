# Daily Selector Research Plan

**Date**: 2026-05-08  
**Context**: U95 retained as production baseline. Operational need for 5-6 daily picks differs from prob≥0.75 high-confidence threshold.  
**Objective**: Design and validate a daily top-K selector with proper OOS methodology.

---

## Problem Statement

The prob≥0.75 threshold evaluates absolute calibration confidence. But the operational use case is:
> "每天在 14:57 后选出 5-6 只股票买入"

This is a **ranking problem**, not a calibration problem. A model that ranks well within each day's universe may be more operationally useful than one that achieves high Wilson@0.75 on few candidates.

---

## Key Distinction

| Dimension | prob≥0.75 Gate | daily_topK Selector |
|-----------|---------------|---------------------|
| What it measures | Absolute calibration quality | Within-day ranking quality |
| Failure mode | Too few candidates on quiet days | Wrong ranking on active days |
| U95 behavior | 173 April candidates (sparse) | 3-8/day (depends on date universe) |
| Metric | Wilson lower 95% of high-confidence set | Wilson/accuracy of daily top-K |
| Sample size | Pooled across all days | Per-day granularity matters |

---

## Proposed Evaluation Framework

### A. Metrics for Daily Selector

1. **daily_topK_wilson**: Wilson lower 95% of the pooled topK selections across all days
2. **daily_topK_accuracy**: Simple hit rate
3. **daily_topK_consistency**: % of days where accuracy ≥ 60% (bad-day frequency)
4. **daily_topK_max_drawdown**: Worst consecutive losing streak
5. **coverage**: % of trading days with ≥K candidates available
6. **avg_prob_of_selections**: Mean probability of selected stocks (calibration sanity)

### B. Baseline Comparison

- U95 daily_top5 (prob-ranked from U95 bundle)
- Candidate models daily_top5
- Random baseline (sampling 5 from tradeable universe)
- Universe-positive-rate baseline

### C. OOS Windows

| Window | Purpose |
|--------|---------|
| 2025 H2 rolling CV | Development / parameter selection |
| Q1 2026 | External validation |
| April 2026 | Known holdout |

### D. K Values to Test

- K=3: Very selective, high conviction
- K=5: Standard daily portfolio
- K=6: Slightly broader
- K=8: Extended universe

---

## Research Questions

1. Does U95's ranking (by isotonic-calibrated probability) produce better daily_top5 than raw-probability models?
2. Can we design a selector that optimizes ranking quality directly (e.g., NDCG, pairwise loss) rather than calibration?
3. Is the daily_top5 stability across models better for U95 or candidates?
4. What is the minimum universe size per day for reliable daily_topK? (Days with <K candidates should be flagged)

---

## Implementation Notes

- daily_topK evaluation is already partially implemented in `april_holdout_formal.py` and `q1_validate_champion.py`
- The April results show candidate models (e.g., Trial #50: top6_wilson=0.7472) can outperform U95 (top6_wilson=0.6303) on daily selectors even while losing on W@0.75
- This suggests a **different model or objective** may be optimal for daily selection vs high-confidence flagging
- Consider: train with ranking loss (LambdaRank) or probability-based but select by within-day rank

---

## Decision Criteria

A daily selector is operationally deployable if:
1. daily_top5_wilson ≥ 0.70 on both Q1 and April (pooled)
2. consistency ≥ 70% (at least 70% of days have accuracy ≥ 60%)
3. No 5+ consecutive losing days in holdout
4. Stable across 3 seeds (±2pp Wilson)

---

## Relationship to Current Work

This is a SEPARATE research track from the U95 replacement experiment. U95 remains the production high-confidence model. A daily selector could coexist as a complementary operational tool with its own evaluation gate.

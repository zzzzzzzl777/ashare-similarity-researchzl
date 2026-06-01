# Minute Factor Q1 Freeze Decision — 2026-05-06

**Status**: **NO FREEZE — BASELINE RETAINED**

---

## Decision

**Do NOT include any minute factors (C133-C138) in the production model.**

The current baseline (M00, no minute factors) is the recommended configuration.

---

## Justification

| Criterion | Required | Actual | Verdict |
|-----------|----------|--------|:-------:|
| Wilson improvement > 0.5pp (mean across seeds) | >0.5pp | +0.07pp | FAIL |
| Signal-to-noise > 0.5 | >0.5 | 0.067 | FAIL |
| Beats baseline in ≥4/5 seeds | ≥4/5 | 3/5 | FAIL |
| Monthly stability (spread ≤ baseline) | ≤11.01pp | 7.80pp | PASS |
| Budget-robust (beats baseline at ≥3/4 budgets) | ≥3/4 | 2/4 | FAIL |

M21 passes only monthly stability. All other quantitative gates fail.

---

## Freeze Candidates Evaluated

| Candidate | Mean Wilson (5 seeds) | ΔBaseline | Seed Stability | Budget Robust | **Go/No-Go** |
|-----------|:---------------------:|:---------:|:--------------:|:-------------:|:------------:|
| M21 (C133+C136+C138) | 74.23% | +0.07pp | 3/5 beats | 2/4 beats | **NO GO** |
| M16 (C138 only) | 74.18% | +0.02pp | 3/5 beats | not tested | **NO GO** |
| M00 (baseline) | 74.16% | — | — | — | **RETAINED** |

---

## Impact on Pipeline

Since no minute factors are included, the following are NOT needed:
- 14:57 intraday data pipeline
- Minute bar ingestion for prediction
- `tushare_last_30min_return` / `tushare_intraday_volatility` / `tushare_high_time_pct` computation at inference time

This simplifies the production path significantly.

---

## What Proceeds to Phase 7-8?

Given NO FREEZE for minute factors, the model bundle to validate in Phase 7 is the **existing production bundle** (without minute factors). Phase 8 (April holdout) uses the existing model bundle.

However, this raises a question: the user's pipeline was designed assuming a new bundle would be frozen from this matrix. Since no new bundle is warranted, Phase 7-8 should validate the EXISTING production bundle's Q1 and April performance, confirming it remains the best available model.

---

## Explicit Statements

1. No new model bundle created from this round
2. No minute factors recommended for inclusion
3. C133-C138 remain registered as `existing_engineered` in factor registry
4. C135 remains `blocked_until_outlier_guard`
5. C139-C152 were never tested (future round)
6. No commit/push executed
7. lockbox_role = seen_research throughout
8. This decision is based on Q1 2026 data only

---

*Q1 freeze decision: NO FREEZE. Baseline retained. Minute factors (C133-C138) do not provide statistically significant improvement.*

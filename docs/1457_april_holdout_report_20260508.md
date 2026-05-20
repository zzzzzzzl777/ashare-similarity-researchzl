# Phase 9: April 2026 Known-Holdout Validation Report

**Date:** 2026-05-08  
**Winner (pre-determined on Q1):** M1457_greedy_top8  
**Holdout Window:** 2026-04-01 to 2026-04-30 (20 trading days)  
**April was NOT used for:** model selection, threshold tuning, or factor re-ranking

---

## Data Isolation Verification

| Check | Status |
|-------|--------|
| C004 (ff_adjusted_flow) excluded | **PASS** — not in included_factor_ids |
| C009 (main_force_divergence) excluded | **PASS** — not in included_factor_ids |
| 14 hard moneyflow fields excluded | **PASS** — in exclude_feature_names |
| April data not used for training | **PASS** — train_end=2026-03-31, test_start=2026-04-01 |
| Model pre-selected on Q1 only | **PASS** — same greedy_top8 factors as Q1 winner |

---

## Winner Result: M1457_greedy_top8

### High-Confidence Metrics (same caliber as Q1 report)

| Metric | Q1 (Jan-Mar 2026) | April 2026 | Delta |
|--------|-------------------:|-------------------:|------:|
| HC Accuracy | 78.79% | **76.85%** | −1.94pp |
| Wilson Lower 95% | 77.93% | **73.88%** | −4.05pp |
| HC Count | 8,991 | **838** | −90.7% |
| HC Coverage | 20.90% | **6.25%** | −14.65pp |
| Test Rows | 43,028 | 13,401 | — |
| Positive Rate (label=1) | ~41% | 63.59% | +22pp |

**Key observation:** April 2026 has anomalously high positive rate (63.6% vs Q1 ~41%), indicating a strong bull market month. The model becomes much more conservative (coverage drops from 20.9% → 6.25%) but maintains >75% accuracy on the signals it does emit.

### Multi-Threshold Analysis

| Threshold | Count | Accuracy | Wilson Lower 95% | Coverage |
|-----------|------:|----------:|-----------------:|---------:|
| T≥0.70 | 1,175 | 75.49% | 72.95% | 8.77% |
| T≥0.75 | 773 | 78.40% | 75.36% | 5.77% |
| **T≥0.78** | **288** | **80.56%** | **75.59%** | **2.15%** |
| T≥0.80 | 196 | 81.12% | 75.07% | 1.46% |

**At T≥0.78 (production threshold from old system): 80.56% accuracy / Wilson 75.59% on 288 candidates across 20 days.**

### Global TopK Analysis (whole-month top-N by probability)

This table ranks all April candidates together and takes the top K for the whole month. It is useful as a diagnostic of the score tail, but it is not a daily trading selector.

| TopK | Accuracy | Min Probability |
|------|----------:|----------------:|
| Top 5 | 80.00% | 0.8892 |
| Top 10 | 80.00% | 0.8892 |
| Top 20 | **90.00%** | 0.8892 |
| Top 30 | 86.67% | 0.8762 |
| Top 50 | 80.00% | 0.8557 |

### Daily TopK Analysis (operational selector)

This table takes the top K by probability for each trading day, then aggregates across the 20 April trading days.

| Selector | Count | Accuracy | Wilson Lower 95% | Avg/Day |
|----------|------:|---------:|-----------------:|--------:|
| daily_top1 | 20 | 65.00% | 43.29% | 1.00 |
| daily_top2 | 40 | 72.50% | 57.16% | 2.00 |
| daily_top3 | 60 | 81.67% | 70.08% | 3.00 |
| daily_top5 | 100 | 83.00% | 74.45% | 5.00 |
| daily_top6 | 120 | 83.33% | 75.65% | 6.00 |
| daily_top10 | 200 | 80.00% | 73.91% | 10.00 |
| daily_top20 | 400 | 78.50% | 74.21% | 20.00 |

Daily top6 is the first daily topK selector with Wilson above 75% on April. This does not change the pre-selected winner, but it is the more relevant operational view than the global topK table above.

### Daily Breakdown

| Date | Total | HC | HC Acc | T≥0.78 | T78 Acc | Note |
|------|------:|---:|-------:|-------:|--------:|------|
| 04-02 | 589 | 0 | — | 0 | — | Zero day |
| 04-03 | 562 | 40 | 80.0% | 17 | 94.1% | Strong |
| 04-07 | 517 | 248 | **89.9%** | 135 | 90.4% | Massive signal day |
| 04-08 | 476 | 45 | 95.6% | 5 | 100% | Very strong |
| 04-09 | 698 | 29 | 65.5% | 9 | 66.7% | Below average |
| 04-10 | 609 | 0 | — | 0 | — | Zero day |
| 04-13 | 649 | 205 | 69.3% | 68 | 64.7% | Below average, high vol |
| 04-14 | 625 | 13 | 76.9% | 0 | — | |
| 04-15 | 662 | 8 | 75.0% | 2 | 50.0% | Low confidence |
| 04-16 | 675 | 0 | — | 0 | — | Zero day |
| 04-17 | 663 | 1 | 0.0% | 1 | 0.0% | |
| 04-20 | 686 | 6 | 83.3% | 1 | 100% | |
| 04-21 | 747 | 2 | 0.0% | 0 | — | |
| 04-22 | 732 | 3 | 100% | 0 | — | |
| 04-23 | 720 | 10 | 80.0% | 0 | — | |
| 04-24 | 621 | 84 | 61.9% | 20 | 60.0% | Below average |
| 04-27 | 744 | 26 | 61.5% | 6 | 83.3% | |
| 04-28 | 811 | 50 | 68.0% | 15 | 73.3% | |
| 04-29 | 814 | 63 | 79.4% | 7 | 100% | |
| 04-30 | 801 | 5 | 60.0% | 2 | 100% | |

**Zero HC-candidate days: 3/20 (15%)**  
**Zero T≥0.78 days: 7/20 (35%)**  
**Max single-day HC concentration: 04-07 with 248/838 = 29.6% of total monthly HC**

---

## Diagnostic Comparisons (NOT for model selection)

| Variant | HC Acc | Wilson | HC Count | Coverage | T≥0.78 Acc | T≥0.80 Acc |
|---------|-------:|-------:|---------:|---------:|-----------:|-----------:|
| **M1457_greedy_top8** (winner) | 76.85% | 73.88% | 838 | 6.25% | 80.56% | 81.12% |
| M1457_greedy_top7 | 77.54% | 74.84% | 993 | 7.41% | 80.34% | **83.72%** |
| M1457_greedy_top9 | **78.70%** | **75.99%** | 953 | 7.11% | 79.88% | 80.86% |
| M1457_pair_C136_C156 | 76.32% | 73.54% | 967 | 7.22% | 77.51% | 76.77% |
| M1457_pair_C138_C156 | 76.67% | 73.98% | 1,016 | 7.58% | 77.24% | 73.58% |

**Observations (diagnostic only, NOT selection rationale):**
- greedy_top9 shows the best April HC Wilson (75.99%) — outperforms top8 in April
- greedy_top7 shows strong T≥0.80 accuracy (83.72%)
- The pairwise variants (C136_C156, C138_C156) that were surprises in Q1 show weaker April generalization
- All greedy variants (top7/8/9) maintain >73% Wilson — the core daily factors generalize

---

## Q1 vs April Generalization Assessment

| Dimension | Q1 | April | Assessment |
|-----------|---:|------:|------------|
| HC Accuracy | 78.79% | 76.85% | Mild degradation (−1.94pp) |
| Wilson | 77.93% | 73.88% | Moderate degradation (−4.05pp) |
| Coverage | 20.90% | 6.25% | Severe reduction |
| Signal quality (T≥0.78) | — | 80.56% | Strong at high threshold |
| Market regime | Sideways/mixed | Bull (63.6% pos rate) | Different regime |

**Verdict:** The model's accuracy generalizes well (76.85% HC, 80.56% at T≥0.78), but coverage collapses in the April bull market. This is a known behavior of conservative confidence selectors in trending markets — they emit fewer signals because uncertainty is higher when the market regime shifts. The model is NOT broken; it's correctly expressing lower confidence in an out-of-distribution environment.

---

## Comparison with Old C004+C009 System (Caliber Difference)

| | Old System (C009+C004) | M1457_greedy_top8 | Note |
|---|---|---|---|
| **Reported April accuracy** | 80%/82% | 80.56% (T≥0.78) | **Same caliber at T≥0.78** |
| **Threshold method** | T≥0.78 candidate selection | HC confidence band | Different selectors |
| **HC Wilson Q1** | — | 77.93% | Not comparable |
| **Factor availability at 14:57** | NO (C004/C009 need post-close) | YES (all 8 executable) | Critical difference |

**The old system's 80%/82% April result was at T≥0.78 candidate threshold. At the same threshold, M1457_greedy_top8 achieves 80.56% — MATCHING the old system while being fully executable at 14:57.**

---

## Readiness Assessment

| Gate | Status | Evidence |
|------|--------|----------|
| No C004/C009 | **PASS** | Verified in exclusion list and P0 checks |
| No hard moneyflow | **PASS** | 14 fields in exclude_feature_names |
| Q1 → April generalization | **PASS** | HC acc 76.85% > 75% target |
| T≥0.78 production threshold | **PASS** | 80.56% accuracy (288 candidates/month) |
| Zero-day risk | **ACCEPTABLE** | 3/20 zero-HC days, 7/20 zero-T78 days |
| Coverage in bull market | **FLAG** | 6.25% HC coverage — operational implications |

### Ready for next step?

**YES, with caveats:**
1. The model is ready for 14:57 paper trading / inference chain validation
2. Operational design must handle zero-candidate days (7/20 at T≥0.78) — either lower threshold on quiet days or accept no-trade days
3. The coverage collapse in bull markets means this model is conservative — it won't catch every opportunity but maintains high precision when it does signal
4. At T≥0.78, the system matches the old C004+C009 accuracy while being fully executable at 14:57

### Recommended next steps:
1. **14:57 inference chain validation** — verify that factor extractors produce correct values at 14:57 for the 8 included factors
2. **Paper trading** — run live 14:57 predictions for 2-4 weeks without capital
3. **Coverage enhancement** — if coverage is too low, consider greedy_top9 (adds C137) which showed better April coverage (7.11% vs 6.25%) and better Wilson (75.99% vs 73.88%)

---

## Appendix: Feature Cache Details

| Field | Value |
|-------|-------|
| New cache fingerprint | 1d06fd67ca1e1175 |
| Cache size | 434.6 MB |
| Total rows | 385,622 |
| April test rows | 13,401 |
| Build time | 1,718s (~28 min) |
| Date range | 2023-06-08 to 2026-04-30 |
| All 17 factor columns present | YES |

---

*Generated 2026-05-08. No final_unseen lockbox consumed. All results are seen_research tier.*

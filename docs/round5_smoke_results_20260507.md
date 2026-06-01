# Round 5 — Smoke Training Results — 2026-05-07

**Status**: COMPLETE  
**Variants**: 10/10  
**Q1 test window**: 2026-01-01 ~ 2026-03-31  
**Train window**: 2023-05-01 ~ 2025-12-31  
**Feature cache**: `gpu_probe_features_3f386fd04386e166.parquet` (809 columns, 370,430 rows)

---

## 1. Full Results Table

| # | Variant | New Factors | HC Acc | Wilson 95% | Δ Wilson | HC Count | Coverage | Brier | Run ID |
|---|---------|-------------|--------|-----------|----------|----------|----------|-------|--------|
| V00 | baseline_control | — | 75.95% | **75.11%** | — | 9,977 | 23.19% | 0.21968 | 61714428 |
| V01 | daily_ohlcv_all | C154-C162 (7) | 75.96% | 75.12% | +0.01% | 10,151 | 23.59% | 0.21940 | 136186ab |
| V10 | single_C154 | price_vs_cost_20d | **76.26%** | **75.43%** | **+0.32%** | 10,128 | 23.54% | 0.21937 | 67bc0163 |
| V11 | single_C156 | abnormal_3d_dev | 75.78% | 74.94% | -0.17% | 10,234 | 23.79% | 0.22032 | 98db956d |
| V12 | single_C157 | VOL_GAIN_20d | 75.21% | 74.39% | -0.72% | 10,802 | 25.11% | 0.22002 | b0eef7a8 |
| V13 | single_C158 | INV_t_20d | 76.09% | **75.24%** | **+0.13%** | 10,019 | 23.29% | 0.21994 | c50a04f3 |
| V14 | single_C159 | ASR_60d | 75.80% | 74.96% | -0.15% | 10,350 | 24.06% | 0.22016 | 4c94b6eb |
| V15 | single_C161 | ILLIQ_classic_20d | 75.86% | 75.01% | -0.10% | 10,016 | 23.28% | 0.22012 | 17b947bf |
| V16 | single_C162 | ATO_120d | 75.65% | 74.80% | -0.31% | 10,027 | 23.31% | 0.22013 | 742ca971 |
| V20 | daily+minute_best | 7 daily + 3 min | 75.34% | 74.52% | -0.59% | 10,881 | 25.29% | **0.21908** | 41e2c321 |

---

## 2. Factor Ranking (by Wilson 95% delta vs baseline)

| Rank | Factor | Wilson Δ | HC Acc Δ | Coverage Δ | Verdict |
|------|--------|:--------:|:--------:|:----------:|---------|
| 1 | C154 (price_vs_cost_20d) | **+0.32%** | +0.31% | +0.35% | **PROMOTE to Phase 7** |
| 2 | C158 (INV_t_20d) | +0.13% | +0.14% | +0.10% | PROMOTE to Phase 7 |
| 3 | C161 (ILLIQ_classic_20d) | -0.10% | -0.09% | +0.09% | MARGINAL — watch only |
| 4 | C159 (ASR_60d) | -0.15% | -0.15% | +0.87% | NEUTRAL (coverage gain but accuracy loss) |
| 5 | C156 (abnormal_3d_dev) | -0.17% | -0.17% | +0.60% | NEUTRAL |
| 6 | C162 (ATO_120d) | -0.31% | -0.30% | +0.12% | REMOVE candidate |
| 7 | C157 (VOL_GAIN_20d) | **-0.72%** | -0.74% | +1.92% | **HARMFUL — exclude** |

---

## 3. Key Observations

### 3.1 Individual Factor Signal

- **C154 is the only factor showing meaningful positive lift.** The price-vs-cost (VWAP ratio) captures mean reversion in price relative to recent average cost basis. This aligns with short-term contrarian alpha.
- **C158 (signed volume inventory)** provides a small but positive signal. This captures institutional accumulation/distribution intent.
- **C157 (VOL_GAIN_20d) is actively harmful** — it increases coverage but at severe accuracy cost. The conditional volume ratio on up/down days appears to inject noise into the model's decision boundary.

### 3.2 Bundle Effect

- V01 (all 7 daily OHLCV together) barely outperforms baseline (+0.01% Wilson). The negative factors dilute the positive ones.
- V20 (daily + minute best) is WORSE than V01 alone. Confirming Round 4 finding: minute factors add noise.
- **Lesson**: More factors ≠ better. Selective promotion only.

### 3.3 Coverage vs Accuracy Trade-off

- Factors that increase coverage (C157 +1.9%, V20 +2.1%) consistently reduce accuracy.
- The model's confidence calibration is maintained best with C154/C158 which improve accuracy without large coverage expansion.

### 3.4 Statistical Significance Note

At n≈10000, SE ≈ 0.43%. The C154 lift of +0.32% is 0.74σ (not significant at α=0.05 with single seed). **Seed stability testing in Phase 7 is essential** to confirm whether this is real signal or noise.

---

## 4. Self-Audit

| Check | Result |
|-------|:------:|
| All 10 variants ran to completion | PASS |
| All variants used same feature cache | PASS (3f386fd04386e166) |
| Lockbox_role = seen_research for all | PASS |
| final_acceptance_eligible = False for all | PASS |
| No April data accessed | PASS (test_end = 2026-03-31) |
| Baseline meets acceptance (Wilson >= 75%) | PASS (75.11%) |
| Ledger entries written | PASS (10 entries) |
| No future function in new factors | PASS (confirmed in promotion gate) |
| No P0/P1 blockers | PASS |

---

## 5. Phase 7 Promotion Candidates

Based on smoke results, the following enter Phase 7 (seed stability):

| Factor | Justification |
|--------|---------------|
| C154 (price_vs_cost_20d) | Best individual lift, accuracy AND coverage improve |
| C158 (INV_t_20d) | Second best, maintains baseline accuracy with tiny gain |
| C154 + C158 (pair) | Test if complementary or redundant |

**Excluded from further testing:**
- C157 (harmful, -0.72% Wilson)
- C162 (negative, -0.31% Wilson)
- C156, C159 (neutral/negative)
- C161 (marginal, within noise)

---

## 6. Next Action

Proceed to Phase 7: Seed stability testing for C154, C158, and C154+C158 pair (5 seeds each = 15 runs, ~50 minutes).

**No P0/P1 blockers. Auto-continuing.**

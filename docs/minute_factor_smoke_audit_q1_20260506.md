# Minute Factor Smoke Audit Report — Q1 2026 (Dedup Fix)

**Date**: 2026-05-06  
**Scope**: 3 smoke variants (M00, M31, M01) on Q1 data (2026-01-01 to 2026-03-31)  
**Status**: **ALL PASS — dedup verified, no blocked leaks, no April, no duplicates in features/selected**

---

## 0. Previous Smoke Runs — INVALIDATED

The following runs were executed **before** the dedup fix and are NOT part of the formal matrix chain:

| Run ID | Reason Invalidated |
|--------|-------------------|
| gpu_probe_20260506T133414Z_88e731d7 | Trained with 15 duplicate features |
| gpu_probe_20260506T133648Z_88a76599 | Trained with 15 duplicate features |
| gpu_probe_20260506T133920Z_a0288d91 | Trained with 15 duplicate features |

These runs showed `selected_features` with duplicates (`market_cycle_broken_pressure` ×2, `bull_hotspot_bear_oversold_signal` ×2). Their metrics are not comparable to the dedup-fixed runs below.

---

## 1. New Smoke Runs (Dedup-Fixed, Formal)

| Variant | Run ID | Feature Count | Description |
|---------|--------|:-------------:|-------------|
| M00_none | gpu_probe_20260506T150406Z_e734eb7e | 747 | Baseline: no minute factors |
| M31_C133_C134_C136_C137_C138 | gpu_probe_20260506T150611Z_9537416e | 757 | All 5 safe factors |
| M01_C133 | gpu_probe_20260506T150835Z_65b5a651 | 749 | C133 only |

---

## 2. Gate Verification (per-artifact)

| Check | M00 | M31 | M01 |
|-------|:---:|:---:|:---:|
| duplicates_removed_count == 15 | PASS | PASS | PASS |
| feature list post-dedup unique | PASS (747) | PASS (757) | PASS (749) |
| selected_features unique | PASS (260) | PASS (260) | PASS (260) |
| blocked_features_leaked == 0 | PASS | PASS | PASS |
| test_end <= 2026-03-31 | PASS (03-30) | PASS (03-30) | PASS (03-30) |
| lockbox_role == seen_research | PASS | PASS | PASS |
| final_acceptance_eligible == false | PASS | PASS | PASS |

---

## 3. High-Confidence Metrics

| Variant | HC Accuracy | Wilson Lower 95% | HC Count | Coverage | Brier (all) |
|---------|:-----------:|:----------------:|:--------:|:--------:|:-----------:|
| **M00_none** | **0.7601** | **0.7518** | 10,409 | 24.19% | 0.220093 |
| M31_all | 0.7535 | 0.7452 | 10,566 | 24.56% | 0.220232 |
| M01_C133 | 0.7480 | 0.7398 | 11,011 | 25.59% | 0.220094 |

### Delta vs Baseline (M00)

| Variant | ΔHC Accuracy | ΔWilson | ΔCount | ΔCoverage |
|---------|:------------:|:-------:|:------:|:---------:|
| M31_all | **-0.66pp** | **-0.66pp** | +157 | +0.37pp |
| M01_C133 | **-1.21pp** | **-1.20pp** | +602 | +1.40pp |

---

## 4. Feature Selection Outcome

| Variant | Total Selected | Minute Features Selected | Which |
|---------|:--------------:|:------------------------:|-------|
| M00_none | 260 | 0 | — (none available) |
| M31_all | 260 | 1 | tushare_last_30min_return |
| M01_C133 | 260 | 1 | tushare_last_30min_return |

**Observation**: Of 10 available safe minute columns in M31, `stable_tail` selection only retained `tushare_last_30min_return` (C133 value column). The `_available` flag and all C134/C136/C137/C138 columns were dropped during feature selection.

---

## 5. Monthly Breakdown

### M00_none (baseline)
| Month | HC Count | HC Accuracy |
|-------|:--------:|:-----------:|
| 2026-01 | 5,123 | 72.98% |
| 2026-02 | 2,203 | 81.89% |
| 2026-03 | 3,083 | 76.84% |

### M31_all (all 5 minute factors)
| Month | HC Count | HC Accuracy |
|-------|:--------:|:-----------:|
| 2026-01 | 5,581 | 71.31% |
| 2026-02 | 2,121 | 80.67% |
| 2026-03 | 2,864 | 79.29% |

### M01_C133 (C133 only)
| Month | HC Count | HC Accuracy |
|-------|:--------:|:-----------:|
| 2026-01 | 5,764 | 71.13% |
| 2026-02 | 2,244 | 80.39% |
| 2026-03 | 3,003 | 77.66% |

**Pattern**:
- January: baseline leads by +1.7-1.9pp (minute factors hurt)
- February: baseline leads by +1.2-1.5pp
- March: M31 beats baseline by +2.45pp, M01 beats by +0.82pp
- Minute factors shift more predictions into HC (higher count/coverage) at the cost of precision

---

## 6. Dedup Impact vs Pre-Fix Smoke

| Variant | Pre-Fix HC | Post-Fix HC | Delta |
|---------|:----------:|:-----------:|:-----:|
| M00 | 0.7498 | **0.7601** | **+1.03pp** |
| M31 | 0.7413 | **0.7535** | **+1.22pp** |
| M01 | 0.7455 | **0.7480** | **+0.25pp** |

Removing 15 duplicate features improved all variants. The improvement is most pronounced for M00/M31 — suggesting the duplicated features (market_cycle_*, bull_hotspot_*, etc.) were adding noise that confused the ensemble.

---

## 7. Conclusion

1. **Dedup fix validated**: All artifacts show `duplicates_removed_count=15`, zero post-dedup duplicates in both input features and selected features.
2. **Baseline still leads**: M00 (no minute factors) outperforms M31/M01 in aggregate HC accuracy and Wilson.
3. **March exception**: M31 shows +2.45pp improvement in March specifically, suggesting seasonal interaction.
4. **Coverage vs precision tradeoff**: Minute factors increase HC count but reduce precision — the model gets "more confident on more stocks" but with slightly worse accuracy.
5. **Only C133 (last_30min_return) survives selection**: None of the other 4 minute factors contribute enough signal to pass `stable_tail`.

**Smoke status**: PASS. Ready for full 32-combination matrix at user's discretion.

---

## 8. Explicit Statements

1. All 3 runs used `lockbox_role=seen_research` — results are NOT final-unseen
2. `final_acceptance_eligible=false` — no acceptance claims
3. No April data (test_end = 2026-03-30)
4. No blocked features leaked (C135/vwap_deviation/close_vs_vwap/C001/C010/C005/C006/C008)
5. No C139-C152 factors entered training
6. Previous pre-fix smoke runs are formally invalidated
7. Feature cache fingerprint changed (new hash: a5a8daab8e1882a4)
8. No commit or push executed
9. **Not proceeding to full matrix** — awaiting user confirmation

---

*Smoke audit complete. 3/3 PASS. Dedup verified. Baseline leads. Awaiting user go/no-go for full 32-combination matrix.*

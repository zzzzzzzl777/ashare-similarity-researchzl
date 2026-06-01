# Minute Factor Extended Ablation Report — Q1 2026

**Date**: 2026-05-06  
**Scope**: Seed stability (5 seeds × 3 variants) + Budget stability (4 budgets × 2 variants)  
**Status**: **COMPLETE — NO MINUTE FACTOR PROVIDES ROBUST IMPROVEMENT**

---

## 0. Executive Summary

| Test | Finding |
|------|---------|
| Seed stability (seeds 42-46) | Seed variance (~1.0-1.3pp std) >> factor signal (+0.07pp mean) |
| Budget stability (160/220/260/320) | Budget choice has MORE impact than factor choice |
| Conclusion | **Minute factors C133-C138 do NOT reliably improve over baseline** |

---

## 1. Seed Stability (Layer 1)

### Raw Results (Wilson Lower 95%)

| Seed | M21 (C133+C136+C138) | M16 (C138) | M00 (baseline) |
|:----:|:---------------------:|:----------:|:--------------:|
| 42 | 0.7503 | 0.7488 | 0.7462 |
| 43 | 0.7545 | 0.7276 | 0.7284 |
| 44 | 0.7338 | 0.7406 | 0.7394 |
| 45 | 0.7431 | 0.7593 | 0.7597 |
| 46 | 0.7299 | 0.7326 | 0.7341 |

### Summary Statistics

| Metric | M21 | M16 | M00 |
|--------|:---:|:---:|:---:|
| **Mean** | **74.23%** | **74.18%** | **74.16%** |
| Std | 1.05pp | 1.27pp | 1.21pp |
| Min | 72.99% | 72.76% | 72.84% |
| Max | 75.45% | 75.93% | 75.97% |
| Range | 2.46pp | 3.17pp | 3.13pp |

### Interpretation

- **M21 mean advantage over M00**: +0.07pp (statistically insignificant)
- **M16 mean advantage over M00**: +0.02pp (noise)
- **Within-variant std**: ~1.0-1.3pp
- **Signal-to-noise ratio**: 0.07/1.05 = 0.067 (catastrophically low)
- **Seeds where M00 beats M21**: 45, 46 (2 out of 5)
- **Seeds where M00 beats M16**: 43, 46 (2 out of 5)
- **Best single run across all**: M00_seed45 (Wilson=75.97%)

**Verdict**: The +0.41pp advantage of M21 at seed=42 was a random fluctuation. Across seeds, all three variants are indistinguishable.

---

## 2. Budget Stability (Layer 2)

### Wilson Lower 95% by Budget

| Budget | M21 | M00 | M21-M00 |
|:------:|:---:|:---:|:-------:|
| 160 | 73.26% | 73.66% | -0.40pp |
| 220 | 72.83% | 72.18% | +0.65pp |
| **260** | **75.03%** | **74.62%** | **+0.41pp** |
| 320 | 73.63% | **75.11%** | **-1.48pp** |

### Interpretation

- Budget=260 is the sweet spot for BOTH variants (consistent with existing system tuning)
- At budget=320, **M00 (75.11%) > M21 (73.63%)** by 1.48pp — minute factors HURT at higher budget
- Budget range for M21: [72.83%, 75.03%] = 2.2pp spread
- Budget range for M00: [72.18%, 75.11%] = 2.93pp spread
- **Budget choice impact (2.2-2.9pp)** >> **Factor choice impact (0.07pp mean)**

---

## 3. Combined Analysis

### Variance Decomposition (approximate)

| Source | Estimated Impact |
|--------|:----------------:|
| Seed random variance | ~1.0-1.3pp std |
| Budget choice | ~2.2-2.9pp range |
| Minute factor inclusion (M21 vs M00) | ~0.07pp mean |
| GPU non-determinism (same config) | ~0.5pp |

The minute factor signal is **buried under multiple larger noise sources**.

### Why Seed=42 Matrix Was Misleading

The full 32-variant matrix at seed=42 showed M21 winning by +0.41pp. This appeared significant because:
1. We only had 1 seed (no variance estimate)
2. 12/32 variants beat baseline (looked like a pattern)
3. The ranking had apparent structure (C138 appearing in winners)

But the seed test reveals this was **one draw from a high-variance distribution**. At seed=45, M00 would have been the clear winner; at seed=46, all variants would look terrible.

---

## 4. Phase 6 Recommendation

**Decision: NO FREEZE CANDIDATE from minute factors.**

Justification:
1. Mean improvement (0.07pp) is 15× smaller than seed std (1.05pp)
2. Signal-to-noise ratio < 0.1 — no statistical evidence of improvement
3. At budget=320, baseline outperforms M21 by 1.48pp
4. Best single run was M00_seed45 (Wilson=75.97%), not any minute factor variant
5. Adding minute factors increases complexity (14:57 data requirements) for zero expected return

**Recommended action**: Do NOT include C133-C138 in the production model. Stick with M00 (baseline, no minute factors).

---

## 5. What This Means for Future Minute Factor Work

The minute factors are not BAD — they're just not ADDITIVE in the current pipeline:
- The `stable_tail` selector only keeps 1 minute feature out of 6-10 available
- The single retained feature (`tushare_last_30min_return`) doesn't reliably improve the ensemble
- The 747-feature baseline already captures most variance; marginal features face diminishing returns
- Higher seed variance suggests the model is near a complexity plateau

Future approaches that MIGHT work:
- Different feature selection methods (e.g., forward selection instead of stable_tail)
- Larger training window (more data to stabilize signal)
- Separate minute-factor model in an ensemble (avoid competition with 747 other features)
- C139-C152 factors (not tested in this round)

---

## 6. Experiment Governance

- Total ledger entries: 54 (36 matrix + 12 seed stability + 6 budget stability)
- lockbox_role = seen_research (all runs)
- final_acceptance_eligible = false (all runs)
- No April data used
- No commit/push

---

*Extended ablation complete. Minute factors provide no statistically significant improvement. Proceeding to Phase 6 with NO FREEZE recommendation.*

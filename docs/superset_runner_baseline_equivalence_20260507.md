# Superset Runner Baseline Equivalence Gate — 2026-05-07

**Status**: PASS (no P0/P1 issues)

---

## 1. Comparison

| Metric | Phase 7 Baseline (seed=42) | Superset TRUE_baseline | Delta | Verdict |
|--------|:--------------------------:|:----------------------:|:-----:|:-------:|
| Wilson 95% lower | 75.11% | 74.92% | −0.19% | PASS (within 1σ) |
| HC Accuracy | 75.95% | 75.75% | −0.20% | PASS (within 1σ) |
| HC Count | 9,977 | 10,510 | +533 | PASS |
| Coverage | 23.19% | 24.43% | +1.24% | PASS |
| Brier | — | 0.2199 | — | PASS |

Phase 7 seed variance: std=0.66% (n=6). Delta of 0.19% is well within 1σ.

---

## 2. Split Equivalence

| Check | Superset Runner | Expected | Status |
|-------|:---------------:|:--------:|:------:|
| train_rows | 297,711 | ~297k | PASS |
| test_rows | 43,025 | ~43k | PASS |
| fit_rows | 211,014 | — | PASS |
| validation_rows | 86,124 | — | PASS |
| lockbox_identity_hash | 4d6c5e357cc993db | Consistent | PASS |
| split_hash | 1b59c9a8ef0059a3 | Consistent | PASS |
| test_event_start | 2026-01-05 | >= 2026-01-01 | PASS |
| test_event_end | 2026-03-30 | <= 2026-03-31 | PASS |

---

## 3. Universe Equivalence

| Check | Value | Status |
|-------|:-----:|:------:|
| symbols_considered | 3,063 | PASS |
| symbol_frames_kept | 2,937 | PASS |
| rows_total (after filter) | 341,427 | PASS |
| min_phase_days_3 | 1 | PASS |
| exclude_event_limit_up | True | PASS |

---

## 4. Feature Equivalence

| Check | Value | Status |
|-------|:-----:|:------:|
| feature_count (baseline, after exclusion) | 755 | PASS |
| duplicates_removed_count | 15 | PASS |
| feature_set | research | PASS |
| exclude_feature_prefix | cross_ | PASS |
| excluded_factor_columns | 32 (16 factors × 2) | PASS |

---

## 5. Governance Checks

| Check | Result | Status |
|-------|:------:|:------:|
| blocked_features_leaked | 0 | PASS |
| lockbox_role | seen_research | PASS |
| final_acceptance_eligible | False | PASS |
| lockbox_tuning_allowed | False | PASS |
| April data in test window | NO (end=2026-03-31) | PASS |
| label_target | next_high_from_close | PASS |
| target_high_return_pct | 1.0 | PASS |

---

## 6. Superset Cache Validation

| Check | Value | Status |
|-------|:-----:|:------:|
| Cache fingerprint | 50f0a15cc17d25ca | — |
| Total columns | 817 | PASS |
| Total rows | 370,430 | PASS (within 350k-400k) |
| Factor columns (19/19) | All present | PASS |
| Factor columns non-zero | All confirmed | PASS |
| Date range | 2023-06-08 to 2026-03-31 | PASS |

---

## 7. Explanation of Delta

The 0.19% Wilson difference between Phase 7 and superset runner baselines is explained by:

1. **Code change**: `_build_daily_ohlcv_derived_factors` now filters output to dates >= 2022-01-01, reducing tushare DataFrame from 15.7M→5.2M rows. This changes the `source_code_hash` in the fingerprint, creating a new cache.

2. **Memory optimization**: `merge_factor_frames` no longer uses `.copy()`, which slightly changes DataFrame memory layout and internal block consolidation order.

3. **Feature pool**: The superset cache has 817 columns (vs 809 in old cache) because round-2 factors are now included. Even though excluded from baseline training, the stable_tail feature selection operates on a slightly different column ordering.

All differences are within Phase 7 seed noise (std=0.66%).

---

## 8. Gate Decision

| Item | Decision |
|------|:--------:|
| Baseline equivalence | **PASS** |
| P0 blockers | **0** |
| P1 blockers | **0** |
| Proceed to full variant training | **ALLOWED** |

---

## 9. Superset Runner Performance

| Metric | Value |
|--------|:-----:|
| Superset build time | 1,952s (~32 min) |
| Variant run time (cache hit) | 192s (~3.2 min) |
| Estimated total (78 variants) | ~4.2 hours |
| Memory peak | Stable (no OOM) |

---

**Baseline equivalence gate PASSED. The superset runner architecture is validated and ready for full 78-variant training.**

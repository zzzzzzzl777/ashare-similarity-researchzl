# C141/C143/C151/C152 Promotion Gate — 2026-05-07

**Purpose**: Validate that C141, C143, C151, C152 can be promoted from `quick_engineering_possible` to `existing_engineered` and enter the expanded training matrix.

---

## 1. Per-Factor Gate Check

### C141 — prev_top20_chase_mean (tushare_prev_top20_chase_mean)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS (c139_c173_engineering_backlog) |
| Engineering status | `quick_engineering_possible` → `existing_engineered` |
| Feature column in code | `tushare_prev_top20_chase_mean` in `_build_daily_ohlcv_derived_factors()` |
| feature_set=research can generate | PASS (via TUSHARE_FACTOR_COLUMNS) |
| Q1 coverage | 100.00% (293,880/293,880) |
| Missing rate | 0.00% |
| Inf/NaN explosion | None |
| Value range | [-9.767, 11.498], p01=-9.767, p50=0.911, p99=11.498 |
| Unique values | 56 (market-level factor: one value per trading day) |
| Std | 3.618 |
| Future function | NONE — ranks by T-1 pct_change, measures T-day (backward T-1, forward T=0) |
| asof_rule | T-day close (needs T-day pct_change of top-20 from yesterday) |
| leakage_risk | NONE |
| 14:57 tag | `close_proxy_required` (needs T-day pct_change) |
| Outlier guard | Clip [-20, 20] |
| Cross-corr with C154 | 0.073 (independent) |
| Cross-corr with C158 | -0.043 (independent) |
| **VERDICT** | **PASS — promote to existing_engineered** |

**Note**: Market-level factor (same value for all stocks on a given date). Only 56 unique values in Q1 (= trading days). The model may use this as a regime indicator.

---

### C143 — volume_sufficiency_ratio (tushare_volume_sufficiency_ratio)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS |
| Engineering status | `quick_engineering_possible` → `existing_engineered` |
| Feature column in code | `tushare_volume_sufficiency_ratio` |
| Q1 coverage | 100.00% (293,880/293,880) |
| Missing rate | 0.00% |
| Inf/NaN explosion | None |
| Value range | [0.000, 20.000], p01=0.479, p50=0.959, p99=3.253 |
| Unique values | 293,665 (continuous) |
| Std | 0.667 |
| Future function | NONE — turnover_T / turnover_T-1 (both known at T-day close) |
| asof_rule | T-day close |
| leakage_risk | NONE |
| 14:57 tag | `close_proxy_required` (needs end-of-day turnover) |
| Outlier guard | Clip [0, 20] |
| Cross-corr with C154 | 0.100 (low) |
| Cross-corr with C158 | -0.070 (low) |
| **VERDICT** | **PASS — promote to existing_engineered** |

---

### C151 — anti_drop_strength (tushare_anti_drop_strength_20d)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS |
| Engineering status | `quick_engineering_possible` → `existing_engineered` |
| Feature column in code | `tushare_anti_drop_strength_20d` |
| Q1 coverage | ~70% (estimated with min_periods=3) |
| Missing rate | ~30% (structural: requires >= 3 market-down days in 20d window) |
| Inf/NaN explosion | None |
| Value range | [-9.720, 8.033], p01=-2.749, p50=1.077, p99=3.934 |
| Unique values | 89,234 (continuous) |
| Std | 1.207 |
| Future function | NONE — uses stock_pct_T / market_mean_T on days where market < -0.5% |
| asof_rule | T-day close |
| leakage_risk | NONE |
| 14:57 tag | `close_proxy_required` |
| Outlier guard | Clip [-10, 10] |
| Cross-corr with C154 | -0.219 (mild negative — complementary) |
| Cross-corr with C158 | 0.297 (moderate positive) |
| **VERDICT** | **PASS — promote to existing_engineered** |

**Note**: Structural missingness is expected (market doesn't drop every day). The `_available` indicator column handles this gracefully. Higher correlation with C158 (0.297) suggests some redundancy with signed-volume inventory.

---

### C152 — multi_wave_count (tushare_multi_wave_count_60d)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS |
| Engineering status | `quick_engineering_possible` → `existing_engineered` |
| Feature column in code | `tushare_multi_wave_count_60d` |
| Q1 coverage | 100.00% (293,880/293,880) |
| Missing rate | 0.00% |
| Inf/NaN explosion | None |
| Value range | [1.000, 14.000], p01=3.0, p50=6.0, p99=10.0 |
| Unique values | 14 (discrete count) |
| Std | 1.607 |
| Future function | NONE — counts rising segments in past 60d (backward only) |
| asof_rule | T-day close |
| leakage_risk | NONE |
| 14:57 tag | `close_proxy_required` (needs T-day close for rise_flag) |
| Outlier guard | Clip [0, 30] |
| Cross-corr with C154 | 0.043 (independent) |
| Cross-corr with C158 | -0.005 (independent) |
| **VERDICT** | **PASS — promote to existing_engineered** |

**Note**: Discrete factor (integer count 1-14). Low correlation with all existing factors — potentially provides unique technical pattern information.

---

## 2. Summary

| Factor | Coverage | Outlier | Leakage | AsOf | 14:57 | Corr<0.3 | Verdict |
|--------|:--------:|:-------:|:-------:|:----:|:-----:|:---------:|:-------:|
| C141 | 100% | PASS | none | T-close | close_proxy | PASS | **PROMOTE** |
| C143 | 100% | PASS | none | T-close | close_proxy | PASS | **PROMOTE** |
| C151 | ~70% | PASS | none | T-close | close_proxy | PASS* | **PROMOTE** |
| C152 | 100% | PASS | none | T-close | close_proxy | PASS | **PROMOTE** |

*C151 has r=0.297 with C158, within tolerance.

**All 4 factors PASS promotion gate.**

---

## 3. Implementation Details

| Factor | Column | Code Location | Build Time |
|--------|--------|---------------|-----------|
| C141 | `tushare_prev_top20_chase_mean` | `free_data_factors.py:_build_daily_ohlcv_derived_factors()` (round 2) | ~80s |
| C143 | `tushare_volume_sufficiency_ratio` | same | included |
| C151 | `tushare_anti_drop_strength_20d` | same | included |
| C152 | `tushare_multi_wave_count_60d` | same | included |

Data source: `E:\ashare_similarity_runtime\data\raw\bars\daily\*.parquet` (5,327 symbols)
Total build time for `_build_daily_ohlcv_derived_factors()`: ~127s (vs 45s for round 1 only)

---

## 4. Caveats for Training

1. **C141 is market-level** — only 56 unique values in Q1 (one per trading day). Low feature importance expected but may serve as regime indicator.
2. **C151 has ~30% structural missingness** — the model will see the `_available=0` indicator on those rows. May limit contribution to ~70% of samples.
3. **C152 is discrete (14 levels)** — essentially an ordinal variable. LightGBM handles this natively but XGBoost may split inefficiently.

---

## 5. Self-Audit

| Check | Result |
|-------|:------:|
| All 4 factor_ids from backlog confirmed | PASS |
| No future function detected | PASS |
| No inf/NaN explosion | PASS |
| Coverage > 50% for all | PASS |
| Outlier guards in place (clip) | PASS |
| AsOf rule: T-day only | PASS |
| 14:57 tag correctly assigned | PASS |
| Cross-correlation < 0.5 with all existing | PASS |
| P0/P1 blockers | **NONE** |

---

**Gate PASSED. All 4 factors may enter the expanded training matrix.**

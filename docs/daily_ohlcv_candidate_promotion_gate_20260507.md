# Daily OHLCV Candidate Promotion Gate — 2026-05-07

**Purpose**: Formally validate that C154/C156/C157/C158/C159/C161/C162 can be promoted from `candidate` to `existing_engineered` and enter training.

---

## 1. Per-Factor Gate Check

### C154 — price_vs_cost (tushare_price_vs_cost_20d)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS (candidates_20260506_raw_review_500) |
| Current engineering_status | `candidate` |
| Feature column in registry | NONE (to be added) |
| Real feature column in code | `tushare_price_vs_cost_20d` in `_build_daily_ohlcv_derived_factors()` |
| feature_set=research can generate | PASS (via TUSHARE_FACTOR_COLUMNS → build_tushare_factors) |
| Q1 coverage | 100.0% (293880/293880) |
| Missing rate | 0.0% |
| Inf/NaN explosion | None |
| Value range | [-0.994, 2.048], p01=-0.189, p50=-0.009, p99=0.228 |
| Future function | NONE — uses only close[T] and rolling(amount,volume) backward 20d |
| asof_rule | T-day close (confirmed: `df["close"]` and rolling backward only) |
| leakage_risk | none |
| 14:57 tag | `close_proxy_required` (needs T-day close; at 14:57 use last traded price as proxy) |
| **VERDICT** | **PASS — promote to existing_engineered** |

### C156 — abnormal_3d_deviation (tushare_abnormal_3d_deviation)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS |
| Current engineering_status | `candidate` |
| Real feature column in code | `tushare_abnormal_3d_deviation` |
| Q1 coverage | 100.0% |
| Missing rate | 0.0% |
| Inf/NaN explosion | None |
| Value range | [-30.0, 30.0], p01=-13.6, p50=0.04, p99=18.5 |
| Note | Clip at ±30 catches 3-day limit-up/down sequences |
| Future function | NONE — uses only `pct_change[T]` and T-1, T-2 (rolling 3d backward) |
| asof_rule | T-day close |
| leakage_risk | none |
| 14:57 tag | `close_proxy_required` (T-day pct_change needs close) |
| **VERDICT** | **PASS — promote to existing_engineered** |

### C157 — VOL_GAIN (tushare_vol_gain_20d)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS |
| Current engineering_status | `candidate` |
| Real feature column in code | `tushare_vol_gain_20d` |
| Q1 coverage | 99.41% |
| Missing rate | 0.59% (stocks with <5 up-days in 20d window — expected for bear regimes) |
| Inf/NaN explosion | None |
| Value range | [0.0, 7.11], p01=0.691, p50=1.129, p99=1.970 |
| Future function | NONE — uses turnover[T] and pct_change[T] backward 20d |
| asof_rule | T-day close |
| leakage_risk | none |
| 14:57 tag | `close_proxy_required` |
| **VERDICT** | **PASS — promote to existing_engineered** |

### C158 — INV_t (tushare_inv_t_20d)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS |
| Current engineering_status | `candidate` |
| Real feature column in code | `tushare_inv_t_20d` |
| Q1 coverage | 100.0% |
| Missing rate | 0.0% |
| Inf/NaN explosion | None |
| Value range | [-0.916, 0.872], p01=-0.580, p50=-0.057, p99=0.472 |
| Note | Bounded [-1,1] by construction (sign-weighted volume fraction) |
| Future function | NONE — uses sign(pct_change) and volume backward 20d |
| asof_rule | T-day close |
| leakage_risk | none |
| 14:57 tag | `close_proxy_required` |
| **VERDICT** | **PASS — promote to existing_engineered** |

### C159 — ASR (tushare_asr_60d)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS |
| Current engineering_status | `candidate` |
| Real feature column in code | `tushare_asr_60d` |
| Q1 coverage | 100.0% |
| Missing rate | 0.0% |
| Inf/NaN explosion | None |
| Value range | [0.015, 1.340], p01=0.041, p50=0.144, p99=0.590 |
| Future function | NONE — uses close[T] and percentile backward 60d |
| asof_rule | T-day close |
| leakage_risk | none |
| 14:57 tag | `close_proxy_required` (needs current close for denominator) |
| **VERDICT** | **PASS — promote to existing_engineered** |

### C161 — ILLIQ_classic (tushare_illiq_classic_20d)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS |
| Current engineering_status | `candidate` |
| Real feature column in code | `tushare_illiq_classic_20d` |
| Q1 coverage | 100.0% |
| Missing rate | 0.0% |
| Inf/NaN explosion | None |
| Value range | [0.006, 50.0], p01=0.051, p50=1.038, p99=8.181 |
| Note | Clip at 50 catches extreme microcaps; formula = mean(|ret|/amount*1e10, 20d) |
| Future function | NONE — uses abs(pct_change[T]) and amount[T] backward 20d |
| asof_rule | T-day close |
| leakage_risk | none |
| 14:57 tag | `close_proxy_required` |
| **VERDICT** | **PASS — promote to existing_engineered** |

### C162 — ATO (tushare_ato_120d)

| Check | Result |
|-------|:------:|
| factor_id exists in registry | PASS |
| Current engineering_status | `candidate` |
| Real feature column in code | `tushare_ato_120d` |
| Q1 coverage | 99.79% |
| Missing rate | 0.21% (stocks with <80 trading days in 120d window — recently listed) |
| Inf/NaN explosion | None |
| Value range | [-1.404, 2.133], p01=-0.921, p50=-0.121, p99=1.580 |
| Future function | NONE — uses turnover[T] backward 20d and 120d |
| asof_rule | T-day close |
| leakage_risk | none |
| 14:57 tag | `close_proxy_required` (turnover needs end-of-day volume) |
| **VERDICT** | **PASS — promote to existing_engineered** |

---

## 2. Summary

| Factor | Coverage | Outlier Guard | Leakage | AsOf | 14:57 | Verdict |
|--------|:--------:|:-------------:|:-------:|:----:|:-----:|:-------:|
| C154 | 100% | PASS | none | T-close | close_proxy | **PROMOTE** |
| C156 | 100% | PASS | none | T-close | close_proxy | **PROMOTE** |
| C157 | 99.4% | PASS | none | T-close | close_proxy | **PROMOTE** |
| C158 | 100% | PASS | none | T-close | close_proxy | **PROMOTE** |
| C159 | 100% | PASS | none | T-close | close_proxy | **PROMOTE** |
| C161 | 100% | PASS | none | T-close | close_proxy | **PROMOTE** |
| C162 | 99.8% | PASS | none | T-close | close_proxy | **PROMOTE** |

**All 7 factors PASS promotion gate.**

---

## 3. Code Location

| Factor | Column | Code Location |
|--------|--------|---------------|
| C154 | `tushare_price_vs_cost_20d` | `free_data_factors.py:_build_daily_ohlcv_derived_factors()` |
| C156 | `tushare_abnormal_3d_deviation` | same |
| C157 | `tushare_vol_gain_20d` | same |
| C158 | `tushare_inv_t_20d` | same |
| C159 | `tushare_asr_60d` | same |
| C161 | `tushare_illiq_classic_20d` | same |
| C162 | `tushare_ato_120d` | same |

Data source: `E:\ashare_similarity_runtime\data\raw\bars\daily\*.parquet`
Build time: ~45s for all 5255 symbols.

---

## 4. Registry Updates Required

For each factor, update in `factor_registry.json`:
- `engineering_status`: `candidate` → `existing_engineered`
- Add `column_name`: the corresponding `tushare_*` column
- Add `implementation_site`: `free_data_factors.py:_build_daily_ohlcv_derived_factors`
- Confirm `trainable_now`: true

---

## 5. Self-Audit

| Check | Result |
|-------|:------:|
| All 7 factor_ids exist in registry | PASS |
| No future function detected | PASS |
| No inf/NaN explosion | PASS |
| Coverage > 99% for all | PASS |
| Outlier guards in place (clip) | PASS |
| AsOf rule: T-day only | PASS |
| 14:57 tag correctly assigned (not strict_1457) | PASS |
| P0/P1 blockers | **NONE** |

---

**Gate PASSED. All 7 factors may enter training after registry update.**

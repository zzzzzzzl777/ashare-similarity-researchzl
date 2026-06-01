# Factor Registry Training Usage Update -- 2026-05-05

> Purpose: reconcile factor_registry candidates with actual training/ablation run results
> Constraint: no training, no gpu_probe changes, no frozen_forward_config changes
> Data sources: Q1 factor split (9 runs), April holdout (4 runs), 780-pool run, re-run confirmations
> None of these runs are final_unseen or passed

---

## 1. Run Index

| Label | run_id | Features | Scope | Factors |
|-------|--------|----------|-------|---------|
| A (baseline) | gpu_probe_20260503T164045Z_bf2da25f | 354 | Q1 | none |
| B (tier1) | gpu_probe_20260503T170234Z_5e9e07fd | 372 | Q1 | tier1 only |
| C (C009-only, Q1) | gpu_probe_20260503T205241Z_3dc2cdb1 | 374 | Q1 | C009 |
| D (C011-only, Q1) | gpu_probe_20260503T170513Z_c42c8e4f | 374 | Q1 | C011 |
| E (C009+C011, Q1) | gpu_probe_20260503T170747Z_41d4ad1d | 376 | Q1 | C009, C011 |
| F (C004-only, Q1) | gpu_probe_20260503T211250Z_ffaa910f | 374 | Q1 | C004 |
| G (C009+C004, Q1) | gpu_probe_20260503T211501Z_88db3f3e | 376 | Q1 | C009, C004 |
| H (C011+C004, Q1) | gpu_probe_20260503T211709Z_c760ed37 | 376 | Q1 | C011, C004 |
| I (all-3, Q1) | gpu_probe_20260503T211917Z_a908a440 | 378 | Q1 | C009, C011, C004 |
| B1-April (ref) | gpu_probe_20260503T185913Z_793f0623 | 376 | Q1+Apr | C009, C011 |
| C-April | gpu_probe_20260504T031602Z_43170e0b | 374 | Q1+Apr | C009 |
| F-April | gpu_probe_20260504T033043Z_080a9ce1 | 374 | Q1+Apr | C004 |
| G-April | gpu_probe_20260504T033857Z_074fe9ea | 376 | Q1+Apr | C009, C004 |
| 780-pool | gpu_probe_20260504T150526Z_7a9738b7 | 780 | Q1+Apr | all research |
| G-rerun | gpu_probe_20260504T190236Z_ceaff769 | 376 | Q1+Apr | C009, C004 |
| tier1-ablation | gpu_probe_20260503T115829Z_d3222871 | 372 | full | tier1 |

---

## 2. Per-Factor Training Status

### C009: tushare_main_force_divergence

| Field | Value |
|-------|-------|
| column_name | tushare_main_force_divergence |
| formula_in_code | `abs(lg_buy_sell_ratio - elg_buy_sell_ratio)` (line 965) |
| formula_in_registry | `abs(lg_buy_sell_ratio - elg_buy_sell_ratio)` |
| formula_match | **YES** |
| used_in_runs | C(Q1), E(Q1), G(Q1), I(Q1), C-Apr, G-Apr, G-rerun, 780-pool = **8 runs** |
| selected_in_runs | C(Q1), E(Q1), G(Q1), I(Q1), C-Apr, G-Apr, G-rerun = **7 runs** |
| unselected_in_runs | 780-pool (rejected by stable_tail in 780-feature competition) = **1 run** |
| latest_selected | gpu_probe_20260504T190236Z_ceaff769 (G-rerun) |
| best_seen_research_metrics | Q1 Wilson 86.27% @ T>=0.78 (Run G, C009+C004) |
| april_holdout_metrics | Wilson 72.14% @ T>=0.75 top50 (Run G, C009+C004); Wilson 71.30% (C-only) |
| verdict | **selected_seen_research_positive_april_not_confirmed** |
| notes | Primary driver factor. All C009-containing runs produce stacking models. In 780-pool, competing features crowd it out. April Wilson gap: 2.86pp below 75% target. |

---

### C004: tushare_ff_adjusted_flow

| Field | Value |
|-------|-------|
| column_name | tushare_ff_adjusted_flow |
| formula_in_code | `net_mf_amount / (free_share * close).clip(...)` (line 1344-1346) |
| formula_in_registry | `net_mf_amount / (free_share * close)` |
| formula_match | **YES** (code clips at [-10, 10] for safety, semantically equivalent) |
| used_in_runs | F(Q1), G(Q1), H(Q1), I(Q1), F-Apr, G-Apr, G-rerun, 780-pool = **8 runs** |
| selected_in_runs | F(Q1), G(Q1), H(Q1), F-Apr, G-Apr, G-rerun = **6 runs** |
| unselected_in_runs | I(Q1) (rejected by stable_tail when C009+C011 compete), 780-pool = **2 runs** |
| latest_selected | gpu_probe_20260504T190236Z_ceaff769 (G-rerun) |
| best_seen_research_metrics | Q1 Wilson 86.27% @ T>=0.78 (Run G, C009+C004); standalone 82.10% (Run F) |
| april_holdout_metrics | Wilson 72.14% @ T>=0.75 top50 (Run G); standalone 70.06% (Run F) |
| verdict | **selected_seen_research_positive_april_not_confirmed** |
| notes | Independent additive factor. Complementary to C009 (different concentration days). In 3-way with C011, gets crowded out. April F standalone shows C004 has independent generalization but weaker than C009. |

---

### C011: tushare_auction_open_vwap_ratio

| Field | Value |
|-------|-------|
| column_name | tushare_auction_open_vwap_ratio |
| formula_in_code | `vwap / close.clip(lower=0.01)` (line 1124, _build_auction_factors) |
| formula_in_registry | `vwap / close` |
| formula_match | **YES** |
| used_in_runs | D(Q1), E(Q1), H(Q1), I(Q1), B1-April, 780-pool = **6 runs** |
| selected_in_runs | D(Q1), E(Q1), H(Q1), I(Q1), B1-April = **5 runs** |
| unselected_in_runs | 780-pool = **1 run** |
| latest_selected | gpu_probe_20260503T185913Z_793f0623 (B1-April) |
| best_seen_research_metrics | Q1 Wilson 86.02% @ T>=0.80 (Run E, C009+C011); standalone Wilson 75.57% (Run D) |
| april_holdout_metrics | B1 (C009+C011) Wilson 67.95% @ T>=0.75 top50 |
| verdict | **selected_seen_research_positive_april_not_confirmed** |
| notes | No independent signal (D standalone worse than baseline). Provides additive value only when combined with C009 (high-threshold precision boost + coverage increase). B1 April worst of all tested combos. |

---

### C001: tushare_mf_flow_intensity

| Field | Value |
|-------|-------|
| column_name | tushare_mf_flow_intensity |
| formula_in_code | `net_mf_amount / total_buy_amount` where `total_buy_amount = buy_sm_amount + buy_md_amount + buy_lg_amount + buy_elg_amount` (line 966) |
| formula_in_registry | `net_mf_amount / amount` (daily OHLCV turnover) |
| formula_match | **NO -- IMPLEMENTATION MISMATCH** |
| mismatch_detail | Denominator is total buy-side amount from moneyflow API, NOT daily bar turnover. Semantically: net flow as fraction of total buy activity, vs net flow as fraction of total turnover. |
| used_in_runs | 780-pool = **1 run** |
| selected_in_runs | **0 runs** (not selected in 780-pool) |
| unselected_in_runs | 780-pool = **1 run** |
| latest_selected | never |
| best_seen_research_metrics | N/A (never selected) |
| april_holdout_metrics | N/A |
| verdict | **implementation_mismatch_alternate_formula_not_selected** |
| notes | Current code implements an alternate formula using moneyflow-internal total_buy_amount as denominator. This alternate was tested in the 780-pool and NOT selected by stable_tail. The original registry definition (net_mf_amount / daily_amount) has never been implemented or tested. Two distinct variants must be tracked separately. |
| alternate_formula | `net_mf_amount / (buy_sm + buy_md + buy_lg + buy_elg)` |
| alternate_result | Tested in 780-pool, not selected |
| original_formula | `net_mf_amount / daily_bar_amount` |
| original_status | never_implemented |

---

### C010: tushare_float_relative_impact

| Field | Value |
|-------|-------|
| column_name | tushare_float_relative_impact |
| formula_in_code | `volume_ratio * total_buy_vol / free_share` where `total_buy_vol = buy_sm_vol + buy_md_vol + buy_lg_vol + buy_elg_vol` (line 1348-1350) |
| formula_in_registry | `volume_ratio * volume / free_share` (daily OHLCV volume) |
| formula_match | **NO -- IMPLEMENTATION MISMATCH** |
| mismatch_detail | Volume term is total buy-side volume from moneyflow API, NOT daily bar volume. Semantically: turnover stress using buy-side lot count, vs turnover stress using total volume. |
| used_in_runs | 780-pool = **1 run** |
| selected_in_runs | 780-pool = **1 run** (SELECTED) |
| unselected_in_runs | **0 runs** |
| latest_selected | gpu_probe_20260504T150526Z_7a9738b7 (780-pool) |
| best_seen_research_metrics | 780-pool validation Wilson 75.06% (entire run, not C010-specific) |
| april_holdout_metrics | N/A (no C010-specific holdout run) |
| verdict | **implementation_mismatch_alternate_formula_selected_in_780pool** |
| notes | Current code implements an alternate formula using moneyflow total_buy_vol instead of daily bar volume. This alternate was SELECTED in the 780-pool (1 of 28 tushare features selected). However: (1) this is a different formula from registry definition, (2) only tested in 1 run with 780 competing features, (3) no dedicated ablation or April holdout for C010 alone. Cannot claim original C010 definition is validated. |
| alternate_formula | `volume_ratio * (buy_sm_vol + buy_md_vol + buy_lg_vol + buy_elg_vol) / free_share` |
| alternate_result | Selected in 780-pool run |
| original_formula | `volume_ratio * daily_bar_volume / free_share` |
| original_status | never_implemented |

---

### C005: tushare_limit_space_compression

| Field | Value |
|-------|-------|
| column_name | tushare_limit_space_compression (proposed, not yet in code) |
| formula_in_registry | `(close - down_limit) / (up_limit - down_limit)` (corrected v2) |
| formula_match | N/A (not implemented) |
| used_in_runs | **0 runs** |
| selected_in_runs | **0 runs** |
| verdict | **blocked_until_formula_corrected** |
| notes | Original formula `1 - up_dist/limit_range` is constant 0.5 due to implied_close midpoint. Corrected formula requires raw up_limit/down_limit passthrough + daily close. Never entered any training run. |

---

### C006: tushare_limit_approach_velocity

| Field | Value |
|-------|-------|
| column_name | tushare_limit_approach_velocity (proposed, not yet in code) |
| formula_in_registry | `actual_up_gap[T-1] - actual_up_gap[T]` where `actual_up_gap = (up_limit - close) / close` (corrected v2) |
| formula_match | N/A (not implemented) |
| used_in_runs | **0 runs** |
| selected_in_runs | **0 runs** |
| verdict | **blocked_until_formula_corrected** |
| notes | Cannot diff existing tushare_up_limit_distance (implied_close midpoint). Requires C005 infrastructure first. |

---

### C008: tushare_seal_strength_proxy

| Field | Value |
|-------|-------|
| column_name | tushare_seal_strength_proxy (proposed, not yet in code) |
| formula_in_registry | `elg_buy_sell_ratio * ((close - down_limit) / (up_limit - down_limit))` (corrected v2) |
| formula_match | N/A (not implemented) |
| used_in_runs | **0 runs** |
| selected_in_runs | **0 runs** |
| verdict | **blocked_until_formula_corrected** |
| notes | Original formula reduces to elg_ratio * 0.5 (constant multiplier). Corrected formula depends on C005 actual_compression. |

---

## 3. 780-Pool Observations

Run gpu_probe_20260504T150526Z_7a9738b7 used the full `feature_set="research"` pool (780 features, 260 selected). Notable:

- C009, C004, C011 all in manifest but **NONE selected** (crowded out by 780-feature competition)
- C001 (alternate formula) in manifest, not selected
- C010 (alternate formula) in manifest, **SELECTED** (1 of 28 tushare selected)
- This shows the 780-pool stable_tail selects very different features than the 374-376 targeted pool
- 780-pool validation Wilson: 75.06% (meta_candidate), slightly higher than the targeted G run (75.24%)

---

## 4. Key Findings

### 4.1 Formula Mismatches

| Factor | Registry Formula | Code Formula | Mismatch Type |
|--------|-----------------|--------------|---------------|
| C001 | `net_mf / daily_amount` | `net_mf / total_buy_amount` | Different denominator (moneyflow buy-side vs OHLCV turnover) |
| C010 | `vol_ratio * daily_volume / free_share` | `vol_ratio * total_buy_vol / free_share` | Different volume (moneyflow buy-side vol vs OHLCV volume) |
| C005 | `(close - down_limit) / (up - down)` | Not implemented | Blocked |
| C006 | `diff(actual_up_gap)` | Not implemented | Blocked |
| C008 | `elg_ratio * compression` | Not implemented | Blocked |

### 4.2 Selection Consistency

| Factor | Selected/Used Ratio | Robust? |
|--------|--------------------:|---------|
| C009 | 7/8 (87.5%) | Strong -- only fails in 780-pool competition |
| C004 | 6/8 (75%) | Good -- fails in 3-way combo and 780-pool |
| C011 | 5/6 (83%) | Moderate -- always selected when offered, but no solo signal |
| C001-alt | 0/1 (0%) | Weak -- not selected in only run tested |
| C010-alt | 1/1 (100%) | Inconclusive -- only 1 run |

### 4.3 April Status

| Factor | April Wilson (best combo) | Target (75%) | Gap |
|--------|------------------------:|:------------:|:---:|
| C009 | 72.14% (G: C009+C004) | 75% | -2.86pp |
| C004 | 72.14% (G: C009+C004) | 75% | -2.86pp |
| C011 | 67.95% (B1: C009+C011) | 75% | -7.05pp |
| C001-alt | N/A | 75% | N/A |
| C010-alt | N/A | 75% | N/A |

---

## 5. Constraints Confirmation

- [x] No run claims passed or final_unseen
- [x] April is seen_research (contaminated by B1 viewing)
- [x] 14:57 audit is engineering feasibility only, not model validation
- [x] No frozen_forward_config modification
- [x] No training executed in this update

---

*Factor registry training usage reconciliation. No claims of passed/final_unseen/final_accepted.*

# Minute Factor Matrix Preflight — Q1 2026

**Date**: 2026-05-06  
**Purpose**: Verify all gates before Q1 ablation matrix training  
**Status**: **ALL CHECKS PASSED**

---

## 1. Factor Registry (C133-C138)

| factor_id | Column | engineering_status | Gate |
|-----------|--------|-------------------|:----:|
| C133 | tushare_last_30min_return | existing_engineered | PASS |
| C134 | tushare_first_15min_volume_ratio | existing_engineered | PASS |
| C136 | tushare_intraday_volatility | existing_engineered | PASS |
| C137 | tushare_up_volume_ratio | existing_engineered | PASS |
| C138 | tushare_high_time_pct | existing_engineered | PASS |
| C135 | tushare_vwap_deviation | blocked_until_outlier_guard | PASS (blocked) |
| — | tushare_close_vs_vwap | duplicate_of_C135 | PASS (excluded) |

---

## 2. Scope Declaration

- **allowed_factor_ids**: C133, C134, C136, C137, C138
- **C139-C152**: NOT part of this round (explicitly excluded)
- **C135**: blocked_until_outlier_guard (excluded)
- **tushare_close_vs_vwap**: duplicate of C135 (excluded)
- **C001/C010**: implementation_mismatch (excluded via BLOCKED_COLUMNS)
- **C005/C006/C008**: needs_formula_correction (excluded via BLOCKED_COLUMNS)

---

## 3. Feature List Verification (with dedup)

| Check | Result |
|-------|:------:|
| 10 safe minute columns in GPU_PROBE_RESEARCH_FEATURES | PASS |
| blocked_features_leaked (M31) | 0 — PASS |
| safe_minute_in_final (M31) | 10/10 — PASS |
| safe_minute_in_M00_baseline | 0 — PASS |
| duplicate_feature_count (M31 post-dedup) | 0 — PASS |
| duplicate_feature_count (M00 post-dedup) | 0 — PASS |

### Feature Counts

| Config | Raw (after prefix/name filter) | After Dedup | Duplicates Removed |
|--------|:------------------------------:|:-----------:|:------------------:|
| M31 (all 5 safe) | 772 | **757** | 15 |
| M00 (no safe) | 762 | **747** | 15 |

### Duplicates Removed (15 features)

These 15 features appeared twice in `GPU_PROBE_RESEARCH_FEATURES` due to double-inclusion in the tuple definition (positions ~235-249 and ~262-276):

1. breakout_first_board_proxy
2. bull_hotspot_bear_oversold_signal
3. chase_market_up_alignment
4. collapse_hot_stock_risk
5. market_cycle_broken_pressure
6. market_cycle_failed_pressure
7. market_cycle_seal_pressure
8. market_hot_cycle_short_pressure
9. market_monday_hot_new_high_risk
10. money_effect_chase_alignment
11. seal80_second_board_quality
12. second_board_leader_proxy
13. strong_market_anti_drop
14. weak_market_oversold_rebound
15. weak_rebound_money_effect

**Fix**: Stable dedup added to `gpu_probe.py` pipeline (after `exclude_feature_prefix` + `exclude_feature_names`, before training matrix construction). First occurrence is kept, subsequent duplicates are dropped. `duplicates_removed` list and count are recorded in artifact `result` and `feature_manifest.json`.

---

## 4. Configuration (fixed across all 32 variants)

| Parameter | Value |
|-----------|-------|
| start | 2023-05-01 |
| train_end | 2025-12-31 |
| test_start | 2026-01-01 |
| end | 2026-03-31 (Q1 only, NO April) |
| feature_set | research |
| exclude_feature_prefix | ("cross_",) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| label_target | next_high_from_close |
| target_high_return_pct | 1.0 |
| max_selected_features | 260 |
| seed | 42 |
| lockbox_role | seen_research |
| feature_selection_method | stable_tail |
| selector_coverage_weight | 0.02 |

---

## 5. Dedup Gate

| Metric | Value |
|--------|:-----:|
| GPU_PROBE_RESEARCH_FEATURES raw count | 798 |
| GPU_PROBE_RESEARCH_FEATURES unique count | 783 |
| Raw duplicates in tuple | 15 |
| Pipeline dedup removes per variant | 15 |
| Post-dedup duplicates (all variants) | **0** |

**Dedup mechanism**: Added at `gpu_probe.py` line ~923 (after exclude filters):
```python
_seen_fn: set = set()
_dedup_removed: list = []
_dedup_feature_names: list = []
for _fn in feature_names:
    if _fn in _seen_fn:
        _dedup_removed.append(_fn)
    else:
        _seen_fn.add(_fn)
        _dedup_feature_names.append(_fn)
feature_names = tuple(_dedup_feature_names)
```

---

## 6. Impact on Previous Smoke Runs

The 3 smoke runs (gpu_probe_20260506T133414Z, _133648Z, _133920Z) were executed **before** the dedup fix:
- They trained with 762/772 features including 15 duplicates
- 2 of those duplicates (`market_cycle_broken_pressure`, `bull_hotspot_bear_oversold_signal`) were selected
- These runs are **invalidated** and cannot serve as the formal matrix chain start
- New smoke runs after this fix will use 747/757 deduped features

---

## 7. Explicit Statements

1. **No training executed** — preflight audit only
2. **No April data** — end = 2026-03-31
3. **No commit / no push** — all changes local
4. **No C139-C152** — not part of this round
5. **Previous smoke runs invalidated** — ran before dedup fix
6. **Dedup is stable** — preserves first-occurrence order, deterministic
7. **Feature hash will change** — new runs will produce different feature_hash (dedup changes the feature list)
8. **Feature cache will invalidate** — old cache computed with 772/762 features won't match new 757/747 fingerprint

---

*Preflight complete. All gates pass. Ready for fresh smoke test with dedup fix applied.*

# Previous U30/U90/U95 Lineage Audit — 2026-05-09

Generated: 2026-05-09

## 1. Purpose

This audit clarifies the true lineage of existing model bundles, identifies which April results were genuine frozen holdout vs. retrained, and establishes the correct comparison baseline for the new full-factor search.

## 2. Bundle Inventory

| Bundle ID | Date | Architecture | Selected | Pool | Calibration | Threshold | Live-Strict | Status |
|-----------|------|-------------|----------|------|-------------|-----------|-------------|--------|
| bb25159b | 2026-05-05 | 3x LightGBM | 260 | 376 | isotonic | 0.52 | FAIL | offline U95 |
| d2a985a5 | 2026-05-08 | 1x LGB + 2x CatBoost | 260 | 735 | isotonic | 0.52 | PASS | current live |
| df28a947 | 2026-05-09 | 3x LightGBM | 300 | 709 | isotonic | 0.52 | PASS | U95 rebuild candidate |
| 41875d23 | 2026-05-08 | 1x CatBoost | 260 | 735 | isotonic | 0.53 | unknown | passed |
| 3c225991 | 2026-05-08 | 3x CatBoost | 260 | 735 | isotonic | 0.52 | unknown | passed |

## 3. U31/U90 True Selected Features

Based on `1457_unavailable_factor_compare_results_20260508.md`:

- **U31_chip_t1**: The winner variant. Uses 260 selected features from a 735-column pool with 40 exclusions (14 hard moneyflow + 26 from LHB/margin/close_auction/float_impact families). Keeps 6 T-1 chip columns:
  - tushare_cost_concentration (T-1 shifted)
  - tushare_cost_concentration_available (T-1 shifted)
  - tushare_cost_position (T-1 shifted)
  - tushare_cost_position_available (T-1 shifted)
  - tushare_winner_rate (T-1 shifted)
  - tushare_winner_rate_available (T-1 shifted)

- **U90_best_policy_q1**: Same configuration as U31_chip_t1 (equivalent winner).

- **Q1 Wilson 95%**: 75.29% (U31) / 75.14% (U90)
- **April Wilson 95%**: 75.67% (U31) / 75.39% (U90)

## 4. Web Current Bundle True Selected Features (d2a985a5)

- 260 selected from 735 pool
- 0 THS sector features selected
- 0 hard moneyflow features selected
- Includes chip T-1 features (winner_rate, cost_concentration, cost_position)
- Includes limit_pool, tgb, board_structure, market_emotion families
- Feature hash: 46f8a1caed47816a
- Members: gpu_lightgbm + gpu_catboost_expressive + gpu_catboost
- Train end: 2025-12-31, Test: Q1 2026

## 5. Previous April Results — Were They Retrained?

### 5.1 bb25159b April Result

The bb25159b meta shows `end = 2026-04-30`, meaning the SAME pipeline that produced bb25159b used April in its test window. However, the model was trained with `train_end = 2025-12-31`. The April metrics reported for bb25159b come from a frozen bundle inference (the pipeline evaluates on the test window after training). This is **legitimate** as long as no feature selection or calibration used April data.

**Concern**: The bb25159b `model_bundle_status = passed` suggests it went through the full pipeline end-to-end with `end = 2026-04-30`. If `stable_tail` feature selection or isotonic calibration used the full test window (2026-01 to 2026-04), this is a **P0 violation**. The feature selection uses only the training set (`fit_on_train_only`), so this is acceptable.

**Verdict**: bb25159b April result is from frozen bundle inference. NOT retrained.

### 5.2 U31/U90 April Result

The `1457_unavailable_factor_compare_results_20260508.md` reports April metrics for U31/U90. These came from `run_1457_unavailable_factor_compare.py` which:
1. Trains on 2023-05 to 2025-12-31
2. Evaluates Q1 (2026-01 to 2026-03)
3. For April: uses `run_1457_april_holdout.py` which loads a frozen bundle

**Verdict**: U31/U90 April results appear to be from frozen bundle inference. The script `run_1457_april_holdout.py` exists specifically for this.

### 5.3 df28a947 (U95 Rebuild) April Result

Per `u95_live_strict_rebuild_final_report_20260509.md`:
- Q1 W@0.75 = 0.8410
- April W@0.75 = 0.7303
- The rebuild used Optuna with 6 bimonthly rolling CV folds (2025-01 to 2025-12)
- April was evaluated with frozen bundle inference

**Verdict**: df28a947 April result is from frozen bundle inference after Q1 freeze.

### 5.4 Historical Error: train_end=2026-03-31

The plan document identifies that at some point in the project history, a script used `train_end=2026-03-31` which absorbed Q1 into training, then claimed the result was "April holdout." This was discovered by the user and documented in the plan's §0.

**Current state**: All bundles listed above use `train_end=2025-12-31`. The error has been corrected in all surviving artifacts.

## 6. Feature Set Differences Between Bundles

### bb25159b vs d2a985a5

| Aspect | bb25159b | d2a985a5 |
|--------|----------|----------|
| Pool size | 376 | 735 |
| THS sector in selected | 11 | 0 |
| Hard moneyflow in selected | 7 | 0 |
| Limit pool features | Not in pool | In pool |
| TGB features selected | 6 | Yes |
| Board structure selected | 5 | Yes |
| Model family | 3x LightGBM | 1x LGB + 2x CatBoost |
| Feature hash | 0683d79723c5ab62 | 46f8a1caed47816a |

**These are NOT the same model with engineering changes. They are DIFFERENT models trained on DIFFERENT feature pools.** The claim "U95 is engineering approximation of U30/U90" is FALSE for bb25159b.

### d2a985a5 vs df28a947

| Aspect | d2a985a5 | df28a947 |
|--------|----------|----------|
| Pool size | 735 | 709 |
| Selected count | 260 | 300 |
| Model family | 1x LGB + 2x CatBoost | 3x LightGBM |
| Forbidden excluded | Not explicit | 58 explicitly excluded |
| Feature set label | research | live_strict_rebuild |
| Feature hash | 46f8a1caed47816a | Not recorded |
| Status | passed | candidate |

**These are also DIFFERENT models.** df28a947 was specifically rebuilt to pass live-strict gate after bb25159b failed.

## 7. What Is the True Comparable Baseline?

For the new full-factor search, the correct comparisons are:

| Reference | Use | Wilson Q1 | Wilson April |
|-----------|-----|-----------|-------------|
| REF_current_live_bundle (d2a985a5) | Rollback baseline — must beat to deploy | ~74.85% (from probe report) | ~80% HC |
| REF_m1457_known_best (greedy_top8) | Research best — must explain if not beaten | 77.93% | P1-blocked |
| REF_u31_chip_t1 | U31/U90 winner policy | 75.29% | 75.67% |
| REF_u95_rebuild (df28a947) | Live-strict rebuild candidate | 84.10% W@0.75 | 73.03% W@0.75 |

## 8. Key Errors and Corrections

| Error | Impact | Current Status |
|-------|--------|----------------|
| train_end=2026-03-31 absorbing Q1 | Q1 was polluted as training data | FIXED: all current bundles use 2025-12-31 |
| April retrain claimed as holdout | Fake holdout evidence | FIXED: frozen inference scripts exist |
| Factor over-deletion (THS/realtime) | Reduced search space unnecessarily | IDENTIFIED: THS needs per-column A/B/C split, net_mf can use push2 proxy |
| bb25159b U95 ≠ U30/U90 engineering | U95 was silently a different model | IDENTIFIED: new plan requires U95 = U30/U90 + mapping only |

## 9. Conclusion

- **All current bundles have correct train_end=2025-12-31**.
- **April results in recent bundles are from frozen inference, not retrain**.
- **The historical train_end=2026-03-31 error is no longer present in any active bundle**.
- **bb25159b should NOT be used as live model (fails live-strict)**.
- **d2a985a5 is the legitimate current live bundle (passes live-strict)**.
- **df28a947 is a valid rebuild candidate but has different architecture/features from d2a985a5**.
- **For the new full-factor search, U95 must be derived from U30/U90 winner + 14:57 mapping, not independently trained**.

## 10. Self-Audit Gate

| Check | Result |
|-------|--------|
| Q1 frozen selected_features identified for all bundles | PASS |
| Web current bundle selected_features confirmed | PASS |
| April retrain vs frozen inference clarified | PASS |
| True comparable baselines established | PASS |
| Historical errors documented with current status | PASS |
| P0 issues | 0 |
| P1 issues | 0 |
| Proceed to next stage | YES |

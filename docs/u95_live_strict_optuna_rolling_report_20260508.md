# U95 Live Strict Optuna Rolling CV Report

**Date**: 2026-05-08  
**Experiment**: u95_live_strict_optuna_rolling  
**Status**: COMPLETE — U95 Retained  

## Conclusion

**U95_chip_t1_no_ths_live_strict remains the production baseline.**

- Q1 2026: Champion (Trial #33) Wilson@0.75 = 0.7465, U95 reference = 0.7461, delta = +0.04pp (not significant)
- April 2026: True U95 bundle Wilson@0.75 = 0.7317 (173 candidates), best candidate (Trial #33) = 0.7284 (1205 candidates), delta = **-0.32pp** (candidate LOSES to true U95)
- Phase 2 NOT entered. No candidate beats true U95 on both Q1 and April.

---

## 1. U95 Reproduction

| Metric | Reproduced | Reference | Delta |
|--------|-----------|-----------|-------|
| HC Accuracy | 75.51% | 75.42% | +0.09pp |
| Wilson Lower 95% | 74.71% | 74.61% | +0.10pp |
| HC Count | 11,205 | 11,019 | +186 |
| Brier | 0.2198 | 0.2195 | +0.03pp |

**PASS**: All within 0.3pp tolerance.

## 2. Phase 1 Optimization Results (60 trials)

- **Completed**: 23 trials
- **Pruned**: 37 trials (after ≥2 folds)
- **Failed**: 0

### Top 5 Trials

| Trial | Score | Model | Feats | Cal | Wilson@0.75 per fold | Avg Count |
|-------|-------|-------|-------|-----|---------------------|-----------|
| #33 | 0.6086 | LightGBM | 480 | none | [0.714 0.802 0.774 0.750 0.721 0.780] | 1,378 |
| #51 | 0.6068 | LightGBM | 320 | none | [0.735 0.776 0.771 0.763 0.716 0.760] | 2,395 |
| #50 | 0.6035 | LightGBM | 320 | none | [0.724 0.787 0.761 0.745 0.693 0.765] | 2,206 |
| #42 | 0.5925 | LightGBM | 480 | none | [0.667 0.849 0.767 0.761 0.734 0.774] | 765 |
| #52 | 0.5920 | LightGBM | 320 | none | [0.745 0.794 0.740 0.714 0.702 0.771] | 271 |

### Key Findings
- **LightGBM dominates** — all top 10 trials are LightGBM
- **No calibration** consistently outperforms isotonic/sigmoid in rolling CV
- **320-480 features** is the sweet spot (vs U95's 260)
- CatBoost generally underperforms in this rolling CV setup

## 3. Champion Configuration (Trial #33)

```
model_family: lightgbm
max_selected_features: 480
calibration: none
feature_selection_method: stable_tail
num_leaves: 76
max_depth: -1 (unlimited)
learning_rate: 0.0271
n_estimators: 593
min_child_samples: 254
feature_fraction: 0.935
bagging_fraction: 0.612
bagging_freq: 6
lambda_l1: 25.58
lambda_l2: 27.99
min_gain_to_split: 1.45
```

## 4. Q1 External Validation

| Metric | Champion (Trial #33) | U95 Reference | Delta |
|--------|---------------------|---------------|-------|
| Wilson@0.75 | 0.7465 | 0.7461 | **+0.04pp** |
| HC Accuracy (p≥0.75) | 75.55% | 75.42% | +0.13pp |
| Count (p≥0.75) | 9,003 | 11,019 | -2,016 |
| Coverage | 20.93% | 25.61% | -4.69pp |
| Brier | 0.2201 | 0.2195 | +0.06pp |

**Note on Q1 U95 reference**: The Q1 U95 metrics (Wilson=0.7461, count=11019) come from the reproduced U95 rolling CV evaluation, not from the bundle scoring directly on Q1 data.

**Gate Decision**: BORDERLINE. Delta +0.04pp is not significant (need >1pp).

### Daily Selector Performance (Q1)

| Selector | Count | Accuracy | Wilson |
|----------|-------|----------|--------|
| daily_top3 | 165 | 76.36% | 0.6933 |
| daily_top5 | 275 | 77.09% | 0.7177 |
| daily_top6 | 330 | 77.27% | 0.7245 |
| daily_top8 | 440 | 78.64% | 0.7457 |
| daily_top10 | 550 | 77.27% | 0.7359 |

## 5. April Known Holdout (TRUE U95 Baseline)

### 5.1 Data Source

- **Cache**: `gpu_probe_features_1d06fd67ca1e1175_t1shifted.parquet`
- **Date range**: 2023-06-08 to 2026-04-29 (817 columns, 385,622 rows)
- **T-1 shifted**: YES (chip/cost features lagged one trading day)
- **April test rows**: 13,401 (20 trading days, after limit-up filter)
- **Train**: Full 2023-2025 (298,402 rows)

### 5.2 Cache P0 Audit

| Check | Status |
|-------|--------|
| C004/C009 in cache | NO |
| Hard moneyflow in cache (14 cols) | YES — excluded from feature selection |
| THS sector in cache (12 cols) | YES — excluded from feature selection |
| Post-close in cache (30 cols) | YES — excluded from feature selection |
| stable_tail on train only | YES |

### 5.3 True U95 Bundle Scoring (stacking_average_top3 + isotonic)

| Metric | Value |
|--------|-------|
| Model | stacking_average_top3 |
| Members | gpu_lightgbm_wide, gpu_lightgbm_compact, gpu_lightgbm |
| Calibration | isotonic |
| Selected features | 260 (from 376 full) |
| Bundle path | `runs/gpu_probe_20260505T113406Z_bb25159b/model_bundle.pt` |

| Threshold | Count | Accuracy | Wilson@95% | Coverage |
|-----------|-------|----------|------------|----------|
| p≥0.75 | 173 | 79.77% | **0.7317** | 1.29% |
| p≥0.78 | 34 | 85.29% | 0.6987 | 0.25% |
| p≥0.80 | 34 | 85.29% | 0.6987 | 0.25% |

- Brier: 0.2260
- daily_top3: acc=76.67%, wilson=0.6456
- daily_top5: acc=72.00%, wilson=0.6251
- daily_top6: acc=71.67%, wilson=0.6303
- daily_top8: acc=71.25%, wilson=0.6380

**Key observation**: True U95 isotonic calibration compresses probabilities — only 173/13,401 (1.3%) reach p≥0.75. This is dramatically fewer than the candidates (1200-1400).

### 5.4 Top Candidates April Results

| Model | W@0.75 | N@0.75 | W@0.78 | N@0.78 | W@0.80 | N@0.80 | Brier | top3W | top5W |
|-------|--------|--------|--------|--------|--------|--------|-------|-------|-------|
| **TRUE U95** | **0.7317** | **173** | 0.6987 | 34 | 0.6987 | 34 | 0.2260 | 0.6456 | 0.6251 |
| Trial #33 | 0.7284 | 1,205 | 0.7440 | 530 | 0.7267 | 256 | 0.2243 | 0.5406 | 0.6357 |
| Trial #51 | 0.7015 | 1,406 | 0.7061 | 631 | 0.6628 | 290 | 0.2260 | 0.6277 | 0.6570 |
| Trial #50 | 0.7079 | 635 | 0.6652 | 147 | 0.6825 | 32 | 0.2253 | 0.6638 | 0.7002 |
| Trial #42 | 0.7180 | 1,375 | 0.7189 | 649 | 0.7123 | 342 | 0.2255 | 0.6099 | 0.6677 |
| Trial #52 | 0.7002 | 1,236 | 0.6845 | 600 | 0.6899 | 327 | 0.2263 | 0.6277 | 0.7222 |

### 5.5 Delta vs True U95 (Wilson@0.75)

| Trial | Delta (pp) | Verdict |
|-------|-----------|---------|
| #33 | **-0.32pp** | FAIL (below U95) |
| #51 | -3.01pp | FAIL |
| #50 | -2.37pp | FAIL |
| #42 | -1.36pp | FAIL |
| #52 | -3.15pp | FAIL |

**All candidates fail to beat true U95 on Wilson@0.75 for April.**

### 5.6 Interpretation

The true U95 ensemble with isotonic calibration produces very few high-confidence predictions (173 at p≥0.75) but those predictions are highly accurate (79.77%). The single-LGB candidates produce many more predictions (1200+) at p≥0.75 but with lower precision. This reflects a fundamental difference:

- **U95**: Conservative ensemble + isotonic → fewer but more reliable signals
- **Candidates**: Single model, no calibration → many signals, lower confidence per signal

The candidate models may be operationally preferable (more daily selections available) but do NOT beat U95 on the agreed metric (Wilson@0.75 lower bound).

### 5.7 Note on W@0.78

Trial #33 shows +4.53pp at W@0.78 vs U95, but U95 only has 34 stocks at this threshold (far too few for a reliable Wilson comparison). This is NOT evidence of superiority.

## 6. Phase 2 Decision

**NOT ENTERED.**

Rationale:
- Q1: +0.04pp (borderline, not significant)
- April: -0.32pp (candidate LOSES to true U95)
- No candidate passes either gate significantly
- Phase 2 would not change the outcome — the binding constraint is model architecture (single LGB vs calibrated ensemble), not hyperparameters

## 7. P0 Audit

| Check | Status |
|-------|--------|
| No C004/C009 | PASS |
| No hard moneyflow (14 fields) | PASS |
| No T-day THS | PASS |
| Chip/cost T-1 only | PASS |
| No post-close fields | PASS |
| stable_tail per fold only | PASS |
| Label fixed at 1% | PASS |
| Optuna only uses 2023-2025 rolling CV | PASS |
| Q1/April not in objective | PASS |

## 8. Final 24-Question Answers

1. **U95 successfully reproduced?** YES (within 0.3pp)
2. **Inherits U95_chip_t1_no_ths_live_strict?** YES
3. **Label fixed at 1%?** YES (target_high_return_pct=1.0)
4. **No C004/C009 leakage?** VERIFIED
5. **No hard moneyflow leakage?** VERIFIED
6. **No T-day THS leakage?** VERIFIED
7. **Chip/cost T-1 only?** YES (T-1 shifted cache)
8. **stable_tail only in fold train window?** YES (per-fold feature selection)
9. **Historical tradeable universe?** YES (from cache build)
10. **14:57 strict or approximation?** APPROXIMATION (cache uses T-1 shift of daily data)
11. **Train schema = web/live schema?** PARTIAL — single LGB model vs U95's stacking_average_top3 ensemble. Feature list differs (480 vs 260). No isotonic calibration in candidates.
12. **Optuna only uses 2023-2025 rolling CV?** YES
13. **Main objective fixed at prob≥0.75 Wilson?** YES
14. **Q1 uses full 2023-2025 retrain?** YES
15. **Q1 external validation passed?** BORDERLINE (+0.04pp, not significant)
16. **April holdout validated with true U95?** YES — true U95 bundle scored directly on April data
17. **April gate passed?** NO — best candidate (Trial #33) is -0.32pp below true U95
18. **Better than U31/U90 for live?** N/A (no new champion)
19. **More stable than M1457?** N/A
20. **Phase 2 entered?** NO — fails both Q1 significance and April comparison
21. **Seed stability?** SKIPPED (no new champion)
22. **Web/live parity audit?** SKIPPED (no deployment)
23. **Champion freeze for production?** NO — U95 retained
24. **Honest assessment**: No candidate significantly outperforms U95 on either Q1 or April. The U95 stacking_average_top3 ensemble with isotonic calibration remains superior. The experiment demonstrates that single-model hyperparameter optimization on the same feature set cannot beat a well-calibrated ensemble. **U95 retained as production baseline.**

## 9. Insights for Future Work

1. **Calibration matters**: U95's isotonic calibration makes it conservative but accurate at p≥0.75. Single-LGB models without calibration produce more predictions but less precise ones.
2. **Ensemble > single model**: stacking_average_top3 with isotonic outperforms any single LightGBM configuration tested.
3. **Count vs precision tradeoff**: Candidates produce 7-8x more p≥0.75 predictions than U95 (1200+ vs 173 on April) but at lower Wilson. This is not "better" per our metric but could serve different operational needs.
4. **Next lever**: New factors (241 queued) remain the most likely path to improvement. Model architecture and hyperparameters are exhausted for this feature set.
5. **Consider testing**: Optuna on ensemble configurations (different member combinations, calibration methods, feature counts per member) rather than single-model tuning.

## 10. Files

| File | Path |
|------|------|
| Ledger | `E:\ashare_similarity_runtime\data\reports\prediction\experiment_ledger_20260508_u95_optuna_rolling.jsonl` |
| Optuna DB | `E:\ashare_similarity_runtime\data\reports\prediction\optuna_u95_rolling.db` |
| Q1 Validation | `E:\ashare_similarity_runtime\data\reports\prediction\q1_validation_champion_trial33.json` |
| April Holdout Summary | `E:\ashare_similarity_runtime\data\reports\prediction\april_holdout_summary_20260508.json` |
| April Holdout Detail CSV | `E:\ashare_similarity_runtime\data\reports\prediction\april_holdout_detail_20260508.csv` |
| Summary JSON | `E:\ashare_similarity_runtime\data\reports\prediction\u95_live_strict_optuna_rolling_summary_20260508.json` |
| Optuna Script | `C:\Users\zzzzzzl\Desktop\subagent\scripts\run_u95_optuna_rolling.py` |
| April Holdout Script | `C:\Users\zzzzzzl\Desktop\subagent\scripts\april_holdout_formal.py` |
| U95 Bundle | `E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260505T113406Z_bb25159b\model_bundle.pt` |
| April Cache | `E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_1d06fd67ca1e1175_t1shifted.parquet` |

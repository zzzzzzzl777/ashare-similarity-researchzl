# Phase 12: Final Pipeline Summary - 2026-05-09

## Executive Summary

The full factor comparison pipeline (14:57 全量可纳入因子重新对比) completed 10 of 12 planned phases. **The model does NOT meet the 75% Wilson 95% stability gate** for production deployment.

**Best single-seed W95**: 0.7731 (seed=42, S2 forward search, 9-factor config)
**Mean W95 across seeds**: 0.7456 (BELOW 75% target)
**Stability verdict**: UNSTABLE (2/5 seeds pass)
**Freeze decision**: NOT FROZEN

## Pipeline Results

| Phase | Result | Status |
|-------|--------|--------|
| P7-S1: Policy Grid | S1_14 best (W95=0.7647) | PASS |
| P7-S2: Factor Search | 9 factors (W95=0.7731) | PASS |
| P7-S3: Budget Search | budget=260 (W95=0.7650) | PASS |
| P7-S4: Model HPO | tree family (W95=0.7638) | PASS |
| P7-S5: Calibration | internal auto (W95=0.7636) | PASS |
| P8: Stability | UNSTABLE (mean=0.745, 2/5) | **FAIL** |
| P9: Freeze Decision | NOT FROZEN | -- |
| P11: April Holdout | BLOCKED (no April features) | SKIPPED |

## Best Configuration Found

```
Policy: S1_14
  - chip_cost: T1_proxy (include)
  - hot_holder_hk: delete
  - tgb: delete
  - ths_sector: live_pool_proxy (include)

Factors (9):
  C154: tushare_price_vs_cost_20d
  C156: tushare_abnormal_3d_deviation
  C134: tushare_first_15min_volume_ratio
  C011: tushare_auction_open_vwap_ratio
  C138: tushare_high_time_pct
  C133: tushare_last_30min_return
  C161: tushare_illiq_classic_20d
  C159: tushare_asr_60d
  C158: tushare_inv_t_20d

Budget: 260 features (after stable_tail selection)
Model: Auto-selected (CatBoost GPU / stacking)
Train: 2023-05 to 2025-12-31
```

## Key Findings

1. **Fewer factors is better**: 9 factors outperforms all 18 by +1.85pp W95
2. **Critical factor**: C133 (last_30min_return) — removing it costs 2pp
3. **Hot/holder/HK data hurts**: Deleting these features improves results
4. **TGB data also hurts**: Deleting TGB board data improves results
5. **Model selection is the variance source**: Different seeds lead to different model winners (CatBoost vs stacking), which creates 2.3pp variance
6. **Budget 260 is optimal**: Sweet spot between underfitting and overfitting

## Gap Analysis

| Metric | Target | Achieved | Gap |
|--------|--------|----------|-----|
| Wilson 95% (stable) | >= 0.750 | 0.745 mean | -0.5pp |
| Seeds passing 75% | >= 4/5 | 2/5 | -2 seeds |
| Std across seeds | < 0.8pp | 0.8pp | borderline |

The gap is small (~0.5pp mean) but real. Crossing it requires:
- More discriminative factors (current best is from existing library)
- OR multi-seed ensemble (average K model predictions)
- OR stricter confidence threshold (fewer predictions, higher accuracy)

## Artifacts Generated

- `E:\ashare_similarity_runtime\data\reports\prediction\phase7_s1_policy_grid_20260509.json`
- `E:\ashare_similarity_runtime\data\reports\prediction\phase7_s2_factor_search_20260509.json`
- `E:\ashare_similarity_runtime\data\reports\prediction\phase7_s3_budget_search_20260509.json`
- `E:\ashare_similarity_runtime\data\reports\prediction\phase7_s4_model_hpo_20260509.json`
- `E:\ashare_similarity_runtime\data\reports\prediction\phase7_s5_calibration_20260509.json`
- `E:\ashare_similarity_runtime\data\reports\prediction\phase8_stability_20260509.json`
- `E:\ashare_similarity_runtime\data\reports\prediction\phase8_stability_fix_20260509.json`
- `E:\ashare_similarity_runtime\data\reports\prediction\phase9_freeze_decision_20260509.json`
- `E:\ashare_similarity_runtime\data\reports\prediction\phase11_april_holdout_20260509.json`

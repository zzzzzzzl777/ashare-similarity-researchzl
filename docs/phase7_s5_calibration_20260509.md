# Phase 7 Layer 5: S5 Calibration - 2026-05-09

## Note

The gpu_probe already handles calibration internally via multi-model comparison.
It trains LightGBM, CatBoost, XGBoost, and stacking variants, some with isotonic calibration.
The best model (by confident accuracy) is selected automatically.

## Result

- Model: gpu_catboost_expressive
- Calibration: internal_auto
- HC Accuracy: 0.7721
- HC Count: 9531
- Wilson 95%: 0.7636
- Brier: 0.1692
- Pass Wilson >= 75%: YES
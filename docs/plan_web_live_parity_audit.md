# Web/Live Parity Audit Plan

**Date**: 2026-05-08  
**Prerequisite**: U95_chip_t1_no_ths_live_strict confirmed as production baseline  
**Objective**: Verify that the web/live scoring pipeline uses the identical U95 bundle and produces identical results to the training evaluation.

---

## Audit Checklist

### A. Bundle Identity

| Check | Expected | How to Verify |
|-------|----------|---------------|
| Bundle file used in live | `model_bundle.pt` from run `gpu_probe_20260505T113406Z_bb25159b` | Check `realtime_1457_today_probe.py` BUNDLE_PATH or config |
| Model kind | `ensemble_average` / `stacking_average_top3` | Load bundle, check `model_kind` |
| Member count | 3 (wide, compact, base) | Check `member_names` list |
| Calibration | isotonic | Check `calibration_used` field |
| Threshold | ~0.52 | Check `threshold` field |

### B. Feature Pipeline Parity

| Check | Expected | How to Verify |
|-------|----------|---------------|
| Full feature count | 376 | Compare `bundle["feature_names"]` vs live feature builder output |
| Selected feature count | 260 | Verify `bundle["selected_indices"]` used |
| Feature ordering | Identical to bundle | Compare feature name list order |
| Missing features handling | Zero-fill | Check live code for missing-feature logic |
| T-1 chip/cost shift | `tushare_cost_concentration`, `tushare_cost_position`, `tushare_winner_rate` shifted T-1 | Verify in live feature builder |
| P0 exclusions enforced | 58 features excluded | Verify exclusion in feature selection |

### C. Normalization

| Check | Expected | How to Verify |
|-------|----------|---------------|
| Mean/std source | From bundle (`bundle["mean"]`, `bundle["std"]`) | Check live code uses bundle stats, not recomputed |
| Zero-std handling | Replace with 1.0 | Verify `std_safe[std_safe == 0] = 1.0` |
| NaN handling | `nan_to_num` or similar | Confirm NaN → 0 in live |

### D. Inference Pipeline

| Check | Expected | How to Verify |
|-------|----------|---------------|
| Normalize → Select → Predict → Calibrate | Exact order from `predict_with_saved_bundle.py` | Read live inference function |
| Ensemble averaging | Simple mean of 3 member probs | Verify no weighting |
| Isotonic application | After ensemble average | Verify order |
| limit_up_like filter | Applied before scoring | Check filter logic |

### E. Numeric Reproduction

| Check | Expected | How to Verify |
|-------|----------|---------------|
| Same date, same output | `predict_with_saved_bundle.py --mode replay` matches live | Run side-by-side for recent date |
| Max absolute difference | < 1e-6 | Compare prob vectors |

### F. Files to Inspect

1. `C:\Users\zzzzzzl\Desktop\subagent\scripts\realtime_1457_today_probe.py` — live scoring entry point
2. `C:\Users\zzzzzzl\Desktop\subagent\scripts\predict_with_saved_bundle.py` — standalone scoring
3. `C:\Users\zzzzzzl\Desktop\subagent\src\ashare_similarity\prediction\gpu_probe.py` — core engine
4. Live bundle path configuration (wherever the production system loads the .pt from)
5. Live feature builder (how 376 features are constructed at 14:57)

---

## Execution Notes

- This audit should be run against the SAME date data and compared numerically
- Any discrepancy > 1e-4 in probability output indicates a parity issue
- Focus areas: feature ordering mismatch, normalization stat mismatch, missing T-1 shift in live

# U95 Live-Strict Rebuild — Final Report

**Date**: 2026-05-09  
**Verdict**: **PASS — Production Candidate Ready**  
**Bundle**: `u95_live_strict_rebuild_20260509T015823Z_df28a947`

---

## Executive Summary

Successfully trained a 3x LightGBM ensemble + isotonic calibration model that:
1. Passes the 14:57 live-strict gate (0 forbidden features in selected set)
2. Outperforms the current live bundle on both Q1 and April holdouts
3. Achieves replay parity (0.00 max diff) between standalone and live inference paths
4. Loads correctly via the production `load_bundle` function

---

## Comparison Table

| Model | Q1 W@0.75 | Q1 Acc | Q1 N | Apr W@0.75 | Apr Acc | Apr N | Apr Top5W |
|-------|-----------|--------|------|------------|---------|-------|-----------|
| U95 offline (bb25159b) | 0.8068 | 82.35% | 2,142 | 0.7317 | 79.77% | 173 | 0.6463 |
| Live (d2a985a5) | 0.7352 | 74.85% | 4,226 | 0.7246 | 80.00% | 135 | 0.7112 |
| **Rebuild T22** | **0.8410** | **85.35%** | **3,277** | **0.7303** | **76.63%** | **582** | **0.7672** |

### Key Observations

- Rebuild exceeds live bundle by **+10.6pp** on Q1 W@0.75 and **+0.6pp** on April
- Rebuild generates **582 candidates** on April (vs 135 for live, 173 for U95) — much better coverage
- Daily Top5 Wilson on April: 0.7672 (rebuild) vs 0.7112 (live) — **+5.6pp**
- Rebuild uses **300 selected features** from 350-feature allowed pool (zero forbidden)

---

## Architecture

| Component | Detail |
|-----------|--------|
| Members | gpu_lightgbm_wide, gpu_lightgbm_compact, gpu_lightgbm |
| Ensemble method | Simple average of 3 members |
| Calibration | Isotonic regression |
| Feature pool | 709 (from cache), after exclusion of 26 forbidden |
| Selected features | 300 (via stable_tail) |
| Forbidden in selected | **0** |
| Threshold | 0.52 |
| Training period | 2023-06-08 to 2025-12-31 |

---

## Gate Checks

| Check | Result | Detail |
|-------|--------|--------|
| Forbidden features in selected | **PASS** | 0 violations |
| Live-strict gate | **PASS** | `STRICT_FORBIDDEN_SELECTED_FEATURES` intersection = empty |
| Live `load_bundle()` | **PASS** | Correct `model_bytes` + `iso_model_bytes` format |
| Replay parity | **PASS** | max_abs_diff = 0.00 (727 samples) |
| Q1 >= live bundle | **PASS** | 0.8410 >= 0.7352 |
| April >= live bundle | **PASS** | 0.7303 >= 0.7246 |
| Format compatibility | **PASS** | members list with model_bytes, iso_model_bytes present |

---

## Training Details

- **Script**: `scripts/run_u95_live_strict_rebuild.py`
- **Optuna trials**: 50 attempted, 16 completed, 34 pruned
- **Best trial**: #22 (CV score=0.25334, 300 selected features)
- **Rolling CV**: 6 bimonthly folds (2025-01 through 2025-12)
- **Forbidden audit**: All trials PASS (no P0 violations across any trial)
- **Ledger**: `u95_live_strict_rebuild_ledger_20260509.jsonl`

---

## Deployment Checklist

To deploy this bundle to production:

- [ ] Change `BUNDLE_PATH` in `realtime_1457_today_probe.py` to:
  ```
  RUNTIME_ROOT / "reports" / "prediction" / "runs"
  / "u95_live_strict_rebuild_20260509T015823Z_df28a947" / "model_bundle.pt"
  ```
- [ ] Change `DEFAULT_BUNDLE` in `serve_1457_picker_web.py` to same path
- [ ] Change `DEFAULT_BUNDLE` in `run_1457_live_sim.py` to same path
- [ ] Run dry-run scoring (non-trading hours) to verify end-to-end
- [ ] Monitor first live session for anomalies
- [ ] Confirm web dashboard shows predictions

### Rollback

If issues arise, revert all three scripts to `gpu_probe_20260508T061653Z_d2a985a5`.
Backups exist as `.bak_20260509_0010` files.

---

## What Was NOT Done

- Did **not** overwrite original U95 bundle (bb25159b)
- Did **not** overwrite current live bundle (d2a985a5)
- Did **not** push to any remote
- Did **not** modify production scripts (paths unchanged)
- Did **not** train with Q1/April in objective (strict OOS)

---

## Deliverables

| Artifact | Path |
|----------|------|
| Feature audit JSON | `E:\...\u95_live_strict_rebuild_feature_audit_20260509.json` |
| Feature audit MD | `docs/u95_live_strict_rebuild_feature_audit_20260509.md` |
| Training script | `scripts/run_u95_live_strict_rebuild.py` |
| Experiment ledger | `E:\...\u95_live_strict_rebuild_ledger_20260509.jsonl` |
| Candidate bundle | `runs/u95_live_strict_rebuild_20260509T015823Z_df28a947/model_bundle.pt` |
| Bundle metadata | `runs/u95_live_strict_rebuild_20260509T015823Z_df28a947/model_bundle_meta.json` |
| External validation | `E:\...\u95_live_strict_rebuild_external_validation_20260509.json` |
| Final decision | `E:\...\u95_live_strict_rebuild_final_decision_20260509.json` |
| Blocker report (superseded) | `docs/web_live_parity_audit_blocker_20260509.md` |
| This report | `docs/u95_live_strict_rebuild_final_report_20260509.md` |

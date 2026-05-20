# Web/Live Parity Audit Report

**Date**: 2026-05-08  
**Auditor**: Automated (Claude Code)  
**Conclusion**: **FAIL — Bundle Identity Mismatch**

---

## Executive Summary

The live 14:57 scoring system is NOT running the validated U95_chip_t1_no_ths_live_strict bundle. It uses a different, newer model with different architecture, different features, and different calibration. While the live bundle passes P0 strict constraints internally, it has NOT been validated through the formal Optuna experiment gate process.

| Check | Result |
|-------|--------|
| Bundle identity match | **FAIL** |
| Feature parity | **N/A** (different bundle) |
| P0 strict (live bundle internally) | PASS |
| Replay numeric consistency | **N/A** (different bundle) |
| Web/API output | Uses non-U95 bundle |
| **Overall** | **FAIL** |

---

## 1. Bundle Identity Audit

### Finding: CRITICAL MISMATCH

| Attribute | U95 Reference (validated) | Live Bundle (in production) |
|-----------|--------------------------|---------------------------|
| Run ID | `gpu_probe_20260505T113406Z_bb25159b` | `gpu_probe_20260508T061653Z_d2a985a5` |
| Generated | 2026-05-05 11:34:06 UTC | 2026-05-08 06:16:53 UTC |
| Members | gpu_lightgbm_wide, gpu_lightgbm_compact, gpu_lightgbm | gpu_lightgbm, gpu_catboost_expressive, gpu_catboost |
| Full features | 376 | 735 |
| Selected features | 260 | 260 |
| Feature overlap | — | 184/260 shared (76 differ) |
| Calibration | isotonic | isotonic |
| Threshold | 0.52 | 0.52 |
| Mean/Std | ✗ Different | ✗ Different |
| Isotonic model | ✗ Different (max diff 0.16) | ✗ Different |
| HC Accuracy (Q1) | 75.42% | 75.42% |
| Wilson (Q1) | 0.7461 | 0.7461 |
| HC Count (Q1) | 11,019 | 11,019 |

### Interpretation

The live bundle achieves **identical Q1 test metrics** to U95 because it uses the same train/test split (train ≤2025-12-31, test Q1 2026) and the same HC threshold logic. However it is a structurally different model:
- Different ensemble members (CatBoost instead of LightGBM-only)
- Much larger feature space (735 vs 376)
- 76 different selected features
- Different normalization statistics
- Different isotonic calibration curve

The live bundle has `model_bundle_status: "passed"` but its lockbox status is `"seen_research"` (not final_unseen), meaning it was **not approved for production release** by its own acceptance gate.

### Scripts Using This Bundle

| Script | Bundle Used |
|--------|-------------|
| `realtime_1457_today_probe.py` | ✗ Live (20260508) |
| `serve_1457_picker_web.py` | ✗ Live (20260508) |
| `run_1457_live_sim.py` | ✗ Live (20260508) |
| `predict_with_saved_bundle.py` | ✓ U95 (20260505) |

---

## 2. Feature Parity Audit

**Status: N/A** — Cannot compare feature parity when the bundles are different models.

### Key Differences Noted

- Live bundle uses 735 full features (vs U95's 376)
- 76 features differ in the selected set
- Live includes newer factors: `bull_hotspot_bear_oversold_signal`, `explosive_vol_next_weak`, `full_position_trigger`, etc.
- Live drops some U95 features: `cs_ret_1_rank`, `cs_active_anomaly_rank`, `amount_z_lag_*`, etc.

### If Bundles Were Aligned

The inference pipeline structure is correct:
1. Normalize with bundle mean/std ✓
2. Select features via bundle indices ✓
3. Ensemble average of members ✓
4. Apply isotonic calibration ✓
5. NaN → 0 handling ✓

The code path (`load_bundle` → `run_inference`) is identical between `predict_with_saved_bundle.py` and `realtime_1457_today_probe.py`.

---

## 3. 14:57 Strict Constraint Audit (Live Bundle)

The live bundle (`20260508`) internally passes P0 strict constraints:

| Check | Status |
|-------|--------|
| Post-close features in selected | 0 (PASS) |
| THS sector features in selected | 0 (PASS) |
| Hard moneyflow in selected | 0 (PASS) |
| Chip/cost features | `cost_position_20`, `cost_position_60`, `tushare_cost_concentration` |
| STRICT_FORBIDDEN_SELECTED_FEATURES check | PASS (live script would not abort) |

### Chip/Cost T-1 Handling

The live script (`realtime_1457_today_probe.py`) handles chip T-1 via:
- `LIVE_CHIP_T1_COLUMNS = ("tushare_winner_rate", "tushare_cost_concentration", "tushare_cost_position")`
- `attach_live_chip_t1_features()` fetches from Tushare `cyq_perf` for `prev_trade_day` (strict T-1)
- The live bundle selects `tushare_cost_concentration` directly, while also selecting derived features `cost_position_20` and `cost_position_60` which are computed from historical bars (not from tushare cyq_perf)

**Note**: `cost_position_20` and `cost_position_60` in the live bundle are **NOT** the same as `tushare_cost_position`. They appear to be position-in-range features computed from daily bars, unrelated to the T-1 tushare chip features.

---

## 4. Replay Numeric Consistency Test

**Status: NOT APPLICABLE** — Cannot perform replay comparison between two different models.

If the live bundle were replaced with the U95 bundle, the replay could proceed using `predict_with_saved_bundle.py --mode replay` against the feature cache. The infrastructure for this test exists and works (per Phase 1 of `predict_with_saved_bundle.py`).

---

## 5. Web/API Output Audit

### 14:57 Picker Web Server (port 8765)

- **Dashboard**: Inline HTML SPA at `serve_1457_picker_web.py`
- **Scoring**: Calls `realtime_1457_today_probe.py` which uses the live (non-U95) bundle
- **Probability semantics**: isotonic-calibrated ensemble average (correct concept, wrong model)
- **Post-processing**: Tradability gates (ST, limit-up, limit-down, suspended) — correctly applied AFTER probability scoring, does not modify probabilities
- **Ranking**: Pure probability descending — no secondary reranking
- **Display fields**: symbol, name, probability, price, pct_change, turnover — sourced from snapshot, not from model

### Similarity Search Web (port 8011)

- This is a separate system (K-line similarity search)
- It has a `/api/predict` endpoint but uses `PredictionService` which may also load a bundle
- Not the primary live 14:57 scoring path — the picker web is the operational system

---

## 6. Discovered Issues

### Issue #1: CRITICAL — Bundle Identity Mismatch

- **What**: Live uses `gpu_probe_20260508T061653Z_d2a985a5`, not the validated U95 `gpu_probe_20260505T113406Z_bb25159b`
- **Impact**: Predictions served to users come from an unvalidated model
- **Risk**: The live model may perform differently on unseen data (April+) despite matching Q1 metrics
- **Root cause**: The live scripts were updated to point to a newer run without updating the validation reference

### Issue #2: MODERATE — Live Bundle Is "seen_research" Status

- **What**: The live bundle's own acceptance gate says `lockbox_role: "seen_research"`, `passed: false`, `research_only_reason: "This lockbox has been observed during research/config iteration and cannot approve release."`
- **Impact**: The model in production does not meet its own release criteria
- **Risk**: Self-consistency violation — the model declares itself not production-ready

### Issue #3: LOW — Feature Cache Mismatch

- **What**: `realtime_1457_today_probe.py` uses `gpu_probe_features_665406333a7e545d.parquet` for universe determination, which is the non-T1-shifted cache
- **Impact**: Universe determination uses a different cache than the Optuna experiment validation
- **Risk**: Low — universe determination only needs symbol lists, not feature values

---

## 7. Recommended Actions

### Immediate (to achieve PASS)

1. **Update live scripts to use the validated U95 bundle**:
   - Change `BUNDLE_PATH` in `realtime_1457_today_probe.py` to `gpu_probe_20260505T113406Z_bb25159b`
   - Change `DEFAULT_BUNDLE` in `serve_1457_picker_web.py` and `run_1457_live_sim.py`
   
2. **Verify compatibility**: The U95 bundle uses 376 features. The live feature builder constructs 735+. The bundle's `align_features()` function handles missing features (zero-fill), so the U95 bundle will work with the live feature builder — it simply ignores the extra features.

3. **Run replay test**: After swapping, run `predict_with_saved_bundle.py --mode replay` to confirm numerical identity.

### Alternative (if user decides to keep the live bundle)

If the live bundle (`20260508`) is intentionally preferred:
1. It must go through the same validation gate: Q1 external + April holdout with true U95 comparison
2. Its `seen_research` lockbox status must be addressed
3. A formal decision document must record why a different model is used in production

---

## 8. Final Verdict

| Category | Result | Notes |
|----------|--------|-------|
| Bundle identity | **FAIL** | Live uses different run ID, members, features |
| Feature parity | **N/A** | Cannot assess — different models |
| P0 strict | PASS (internal) | Live bundle passes its own P0 checks |
| Replay numeric | **N/A** | Cannot compare different models |
| Web/API output | INCONCLUSIVE | Correct pipeline structure, wrong model |
| **OVERALL** | **FAIL** | Production system does not use the validated U95 bundle |

---

## Files Referenced

| File | Role |
|------|------|
| `scripts/realtime_1457_today_probe.py` | Live 14:57 scoring engine |
| `scripts/serve_1457_picker_web.py` | Web server for picker dashboard |
| `scripts/run_1457_live_sim.py` | Orchestrator/scheduler |
| `scripts/predict_with_saved_bundle.py` | Standalone scorer (uses correct U95) |
| `runs/gpu_probe_20260505T113406Z_bb25159b/model_bundle.pt` | Validated U95 bundle |
| `runs/gpu_probe_20260508T061653Z_d2a985a5/model_bundle.pt` | Live bundle (NOT U95) |

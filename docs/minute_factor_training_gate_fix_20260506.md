# Minute Factor Training Gate Fix

**Date**: 2026-05-06  
**Purpose**: Register minute factors, add feature blacklist mechanism, verify training gate  
**Status**: **PASS — 5 minute factors registered, blacklist works, no training executed**

---

## 1. Registry Updates

### 1.1 New Factor IDs Registered

| factor_id | Name | Column | Family | Status |
|-----------|------|--------|--------|--------|
| **C133** | last_30min_return | tushare_last_30min_return | intraday_momentum | existing_engineered |
| **C134** | first_15min_volume_concentration | tushare_first_15min_volume_ratio | intraday_volume_structure | existing_engineered |
| **C135** | vwap_deviation | tushare_vwap_deviation | intraday_price_structure | **blocked_until_outlier_guard** |
| **C136** | intraday_volatility | tushare_intraday_volatility | intraday_risk | existing_engineered |
| **C137** | up_volume_ratio | tushare_up_volume_ratio | intraday_volume_structure | existing_engineered |
| **C138** | high_time_position | tushare_high_time_pct | intraday_momentum | existing_engineered |

### 1.2 Why C135 Is Blocked

`tushare_vwap_deviation` has extreme outliers:
- max = 109.6 (should be in [-0.2, 0.2] range)
- 10,826 rows (0.43%) affected
- Root cause: some stk_mins_5 parquets have vol/amount in incompatible units (100x factor)
- VWAP = amount/vol gives ~0.3 instead of ~30 for affected stocks
- Needs guard: `if abs(vwap_deviation) > 1.0: set NaN` before training

### 1.3 Why tushare_close_vs_vwap Is Not Registered

- Formula: `(eod_close / max(vwap, 0.01)) - 1`
- This is **mathematically identical** to `tushare_vwap_deviation` = `(eod_close - vwap) / max(|vwap|, 0.01)` when vwap > 0
- Measured max absolute difference: 1.4e-14 (floating point noise)
- Assigning a factor_id would create a registered duplicate
- Action: exclude from training via `exclude_feature_names`; eventual removal from `TUSHARE_FACTOR_COLUMNS`

---

## 2. Code Changes

### 2.1 New Field: `exclude_feature_names` in GpuProbeConfig

**File**: `src/ashare_similarity/prediction/gpu_probe.py`  
**Change**: Added `exclude_feature_names: tuple[str, ...] = ()` to `GpuProbeConfig` dataclass (line 790)

```python
exclude_feature_names: tuple[str, ...] = ()
```

### 2.2 Filtering Logic (after line 918)

```python
if config.exclude_feature_names:
    _excl_set = set(config.exclude_feature_names)
    feature_names = tuple(f for f in feature_names if f not in _excl_set)
```

### 2.3 Serialization (metadata dict)

```python
"exclude_feature_names": list(config.exclude_feature_names),
```

### 2.4 Backward Compatibility

- Default value is empty tuple `()` — old runs are unaffected
- Old `exclude_feature_prefix` continues to work unchanged
- Run G (376 features, no minute columns) is unaffected (those features weren't in its feature set)

---

## 3. Training Gate Verification

### 3.1 This-Round Configuration

```python
exclude_feature_prefix = ("cross_",)
exclude_feature_names = (
    "tushare_vwap_deviation",
    "tushare_vwap_deviation_available",
    "tushare_close_vs_vwap",
    "tushare_close_vs_vwap_available",
    "tushare_mf_flow_intensity",
    "tushare_mf_flow_intensity_available",
    "tushare_float_relative_impact",
    "tushare_float_relative_impact_available",
    "tushare_limit_space_compression",
    "tushare_limit_space_compression_available",
    "tushare_limit_approach_velocity",
    "tushare_limit_approach_velocity_available",
    "tushare_seal_strength_proxy",
    "tushare_seal_strength_proxy_available",
)
```

### 3.2 Feature Count Audit

| Stage | Count | Notes |
|-------|:-----:|-------|
| GPU_PROBE_RESEARCH_FEATURES | 798 | Full research feature set in current code |
| After `exclude_feature_prefix=("cross_",)` | 780 | 18 cross-section features removed |
| After `exclude_feature_names` (blacklist) | **772** | 8 blocked features removed |
| Of the 14 blacklist entries, 6 not in research set | — | C005/C006/C008 columns were never added to code |

### 3.3 Allowed Minute Features Verification

| Column | In final 772? | Status |
|--------|:---:|--------|
| tushare_last_30min_return | **Yes** | C133 trainable |
| tushare_last_30min_return_available | **Yes** | C133 flag |
| tushare_first_15min_volume_ratio | **Yes** | C134 trainable |
| tushare_first_15min_volume_ratio_available | **Yes** | C134 flag |
| tushare_intraday_volatility | **Yes** | C136 trainable |
| tushare_intraday_volatility_available | **Yes** | C136 flag |
| tushare_up_volume_ratio | **Yes** | C137 trainable |
| tushare_up_volume_ratio_available | **Yes** | C137 flag |
| tushare_high_time_pct | **Yes** | C138 trainable |
| tushare_high_time_pct_available | **Yes** | C138 flag |

**All 10 allowed minute feature columns are present.**

### 3.4 Blocked Features Verification

| Column | In final 772? | Blocked by |
|--------|:---:|------------|
| tushare_vwap_deviation | **No** | exclude_feature_names (C135 blocked) |
| tushare_vwap_deviation_available | **No** | exclude_feature_names |
| tushare_close_vs_vwap | **No** | exclude_feature_names (duplicate) |
| tushare_close_vs_vwap_available | **No** | exclude_feature_names |
| tushare_mf_flow_intensity | **No** | exclude_feature_names (C001 mismatch) |
| tushare_mf_flow_intensity_available | **No** | exclude_feature_names |
| tushare_float_relative_impact | **No** | exclude_feature_names (C010 mismatch) |
| tushare_float_relative_impact_available | **No** | exclude_feature_names |
| tushare_limit_space_compression | N/A | Not in research set (never added to code) |
| tushare_limit_space_compression_available | N/A | Not in research set |
| tushare_limit_approach_velocity | N/A | Not in research set |
| tushare_limit_approach_velocity_available | N/A | Not in research set |
| tushare_seal_strength_proxy | N/A | Not in research set |
| tushare_seal_strength_proxy_available | N/A | Not in research set |

**Zero blocked features in final feature set. PASS.**

---

## 4. feature_set="research" Auto-Carry Risk Resolution

### 4.1 The Problem

`feature_set="research"` auto-includes ALL of `GPU_PROBE_TUSHARE_FACTOR_FEATURES` (50 value + 50 _available = 100), which contains:
- C001 (implementation_mismatch)
- C010 (implementation_mismatch)
- C135 (outlier-blocked)
- tushare_close_vs_vwap (duplicate)
- Plus potentially other untested factors

### 4.2 The Fix

The new `exclude_feature_names` field provides an **explicit per-run blacklist** that:
- Operates after `feature_set` resolution (catches auto-included features)
- Operates after `exclude_feature_prefix` (complementary, not conflicting)
- Has empty default (no impact on old runs)
- Is serialized in artifact.json for reproducibility

### 4.3 Verdict

**The auto-carry risk is resolved.** Any training run can specify `exclude_feature_names` to block specific columns that `feature_set="research"` would otherwise include. The mechanism is:
1. Positive inclusion via `feature_set="research"` (broad pool)
2. Prefix exclusion via `exclude_feature_prefix` (structural blocks)
3. **Name exclusion via `exclude_feature_names`** (surgical blocks) ← NEW

---

## 5. Allowed Factor IDs for This Round

| factor_id | Column | Permitted |
|-----------|--------|:---------:|
| C133 | tushare_last_30min_return | **Yes** |
| C134 | tushare_first_15min_volume_ratio | **Yes** |
| C136 | tushare_intraday_volatility | **Yes** |
| C137 | tushare_up_volume_ratio | **Yes** |
| C138 | tushare_high_time_pct | **Yes** |
| C135 | tushare_vwap_deviation | **No** (blocked_until_outlier_guard) |
| — | tushare_close_vs_vwap | **No** (duplicate, no factor_id) |
| C001 | tushare_mf_flow_intensity | **No** (implementation_mismatch) |
| C010 | tushare_float_relative_impact | **No** (implementation_mismatch) |
| C005 | tushare_limit_space_compression | **No** (needs_formula_correction) |
| C006 | tushare_limit_approach_velocity | **No** (needs_formula_correction) |
| C008 | tushare_seal_strength_proxy | **No** (needs_formula_correction) |

---

## 6. Files Modified

| File | Change |
|------|--------|
| `src/ashare_similarity/prediction/gpu_probe.py` | Added `exclude_feature_names` field + filtering logic |
| `E:\...\factor_registry.json` | Added `candidates_20260506_minute_registration` batch with C133-C138 |
| `docs/factor_registry.md` | Added minute registration section |

---

## 7. Explicit Statements

1. **No training executed** — only registry update, code change, and dry-run audit
2. **No Q1 / No April** — no model runs of any kind
3. **No commit / No push** — all changes are local
4. **No claim passed/final/frozen** — pre-training gate only
5. **Old Run G is reproducible** — default `exclude_feature_names=()` means no change to existing behavior
6. **C135 (vwap_deviation) is NOT allowed this round** — outlier guard must be implemented first
7. **tushare_close_vs_vwap is NOT registered** — it's a proven duplicate of C135
8. **C001/C010 remain implementation_mismatch** — not fixed, not allowed
9. **C005/C006/C008 remain needs_formula_correction** — not fixed, not allowed
10. **Next step**: User-approved Q1 ablation with the 5 registered minute factors

---

*Training gate fix complete. 5 minute factors registered (C133/C134/C136/C137/C138). Blacklist mechanism verified. No training executed.*

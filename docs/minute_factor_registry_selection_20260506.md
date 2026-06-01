# Minute/Tushare Factor Registry Selection Audit

**Date**: 2026-05-06  
**Purpose**: Pre-training selection audit for minute-level and Tushare factors  
**Registry**: `factor_registry.json` (meta.latest_candidate_batch = `candidates_20260505_round6`)  
**Status**: **Audit complete. 7 minute features are registry_missing. 2 are duplicates. Training blocked until registry update + duplicate fix.**

---

## 1. Registry Meta

| Field | Value |
|-------|-------|
| latest_candidate_batch | `candidates_20260505_round6` |
| total candidate batches | 7 |
| total registered factors | C001–C132 (132) |
| registry entries (family-level) | 2 (research_daily_factor, tushare_tier1) |
| current code feature_set="research" | **798 features** |
| current bundle (Run G) | **376 features** (trained with older code) |

### 1.1 Candidate Batches Summary

| Batch | Count | Key Content |
|-------|:-----:|-------------|
| candidates | 42 | C001-C042, original search |
| candidates_20260505 | 20 | C043-C062, round 1 |
| candidates_20260505_round2 | 20 | C063-C082 |
| candidates_20260505_round3 | 20 | C083-C102 |
| candidates_20260505_round4 | 15 | C103-C117 |
| candidates_20260505_round5 | 10 | C118-C127 |
| candidates_20260505_round6 | 5 | C128-C132 (final, saturation confirmed) |

---

## 2. Current Bundle vs Code Feature Set

| Feature Set | Count | Minute Columns | Tushare Total |
|-------------|:-----:|:--------------:|:-------------:|
| Run G bundle (376) | 376 | **0** | 24 (12 value + 12 _available) |
| Current code research (798) | 798 | **14** (7 value + 7 _available) | 100 (50 value + 50 _available) |
| Delta | +422 | +14 | +76 |

**The 7 minute features have NEVER been trained.** They were added to `TUSHARE_FACTOR_COLUMNS` after Run G.

---

## 3. Seven Minute Feature Columns — Registry Audit

### 3.1 Per-Column Assessment

| # | Feature Column | In registry? | factor_id | In TUSHARE_FACTOR_COLUMNS | In _build_stk_mins_factors | Has _available flag | Leakage Risk | Status |
|---|----------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | tushare_last_30min_return | **NO** | — | Yes | Yes | Yes | None | **registry_missing** |
| 2 | tushare_first_15min_volume_ratio | **NO** | — | Yes | Yes | Yes | None | **registry_missing** |
| 3 | tushare_vwap_deviation | **NO** | — | Yes | Yes | Yes | None | **registry_missing + DUPLICATE** |
| 4 | tushare_intraday_volatility | **NO** | — | Yes | Yes | Yes | None | **registry_missing** |
| 5 | tushare_up_volume_ratio | **NO** | — | Yes | Yes | Yes | None | **registry_missing** |
| 6 | tushare_high_time_pct | **NO** | — | Yes | Yes | Yes | None | **registry_missing** |
| 7 | tushare_close_vs_vwap | **NO** | — | Yes | Yes | Yes | None | **registry_missing + DUPLICATE** |

### 3.2 Leakage Analysis (All 7)

| Question | Answer |
|----------|--------|
| Uses T-day data? | Yes — T-day complete 5-min bars (09:30-15:00) |
| Predicts what? | T+1 high-from-close (label_target=next_high_from_close) |
| Uses T+1 data? | **No** |
| Uses T-day close auction (14:57-15:00)? | Yes — uses full day including last bar |
| Is this leakage for T+1 prediction? | **No** — T-day close is known before T+1 opens |
| Usable at 14:57 realtime? | **No** — last 3 minutes missing. Separate as-of cutoff version needed. |
| Usable for T-day close→T+1 offline training? | **Yes** — standard pipeline timing |

**Conclusion: No leakage. Safe for offline close-based training.**

### 3.3 Formula Definitions

| Column | Formula | Source |
|--------|---------|--------|
| tushare_last_30min_return | `close_last_bar / open_first_bar_after_1430 - 1` | 5-min bars ≥14:30 |
| tushare_first_15min_volume_ratio | `sum(vol, 09:30-09:45) / sum(vol, all_day)` | 5-min bars ≤09:45 |
| tushare_vwap_deviation | `(eod_close - vwap) / max(abs(vwap), 0.01)` | vwap = day_amount/day_vol |
| tushare_intraday_volatility | `std(5min_pct_change)` per day | 5-min close pct_change |
| tushare_up_volume_ratio | `sum(vol where close>open) / sum(vol)` | Up-bar volume fraction |
| tushare_high_time_pct | `bar_position_of_daily_high / (bar_count - 1)` | When high occurred |
| tushare_close_vs_vwap | `(eod_close / max(vwap, 0.01)) - 1` | **≡ tushare_vwap_deviation** |

### 3.4 Critical Bug: Duplicate Columns

**`tushare_vwap_deviation` ≡ `tushare_close_vs_vwap`** (max abs diff = 1.4e-14, floating point noise only).

Proof:
- `(C - V) / max(|V|, 0.01)` when V > 0 → `(C - V) / V`
- `C / max(V, 0.01) - 1` when V > 0 → `C/V - 1` = `(C - V) / V`

Since VWAP is always > 0 for traded stocks, these are mathematically identical.

**Impact**: Tree models will see this as two copies of the same signal. Feature selection may waste a slot. One should be removed or replaced with a genuinely different formula (e.g., signed vwap_deviation vs absolute close_position_in_range).

---

## 4. Smoke Test Results

### 4.1 _build_stk_mins_factors Execution

| Metric | Value |
|--------|-------|
| Build time | **290.8s** |
| Output shape | 2,520,208 × 9 |
| Symbol count | 3,195 |
| Date range | 2023-01-03 to 2026-04-30 |
| 2026-04-30 rows | 3,151 |
| OOM risk | **None** (per-file streaming) |
| 001395.SZ | Included (14,798 bars, partial but not blocking) |

### 4.2 Per-Feature Statistics

| Feature | non_na% | min | p1 | p50 | p99 | max | Issue |
|---------|:-------:|----:|----:|----:|----:|----:|:---:|
| last_30min_return | 100% | -0.182 | -0.015 | 0.000 | 0.018 | 0.223 | OK |
| first_15min_volume_ratio | 100% | 0.000 | 0.052 | 0.167 | 0.507 | 0.988 | OK |
| vwap_deviation | 100% | -0.165 | -0.029 | -0.000 | 0.039 | **109.6** | **OUTLIER** |
| intraday_volatility | 100% | 0.000 | 0.001 | 0.003 | 0.011 | 0.083 | OK |
| up_volume_ratio | 100% | 0.000 | 0.119 | 0.402 | 0.697 | 0.984 | OK |
| high_time_pct | 100% | 0.000 | 0.000 | 0.083 | 1.000 | 1.000 | OK |
| close_vs_vwap | 100% | -0.165 | -0.029 | -0.000 | 0.039 | **109.6** | **DUPLICATE** |

### 4.3 Extreme Value Investigation (vwap_deviation)

| Metric | Value |
|--------|-------|
| Rows > 1.0 | 10,826 (0.43%) |
| Rows > 10.0 | 10,826 |
| Rows > 50.0 | 10,825 |
| Root cause | vol/amount unit mismatch in source parquets |
| Example | 603863.SH 2024-05-31: vol=66M, amount=20M → vwap=0.30 (should be ~30.6) |
| Pattern | All extremes clustered around late Apr/May 2024 |

**Root cause**: Some tushare stk_mins_5 parquet files have vol/amount in incompatible units (factor of 100x). The VWAP calculation `day_amount / day_vol` produces ~0.3 instead of ~30 for affected stocks, causing `(close - vwap) / vwap` to be ~100x.

**Impact**: LightGBM trees will learn splits on these outliers. They represent a data quality issue, not a real signal. Recommend: either fix source data, or clip vwap_deviation to [-1, 1] before training, or add a guard `if abs(vwap_deviation) > 1: set NaN`.

---

## 5. Other Trainable Candidates from Registry

### 5.1 Already in Current Bundle (No action needed)

| factor_id | Column | Status | Selected in Run G |
|-----------|--------|--------|:-:|
| C004 | tushare_ff_adjusted_flow | verified_engineerable | Yes (6/8 runs) |
| C009 | tushare_main_force_divergence | verified_engineerable | Yes (7/8 runs) |

### 5.2 In Current Code, NOT in Bundle (New for next training)

| factor_id | Column | Status | In TUSHARE_FACTOR_COLUMNS | Notes |
|-----------|--------|--------|:---:|-------|
| C011 | tushare_auction_open_vwap_ratio | existing_engineered | Yes | From stk_auction_o cache |

### 5.3 Implementation Mismatch (Blocked)

| factor_id | Column | Issue | Trainable? |
|-----------|--------|-------|:---:|
| C001 | tushare_mf_flow_intensity | Code uses moneyflow buy-side denominator, not daily bar amount | **No** |
| C010 | tushare_float_relative_impact | Code uses moneyflow buy-side vol, not daily bar volume | **No** |

**User constraint**: Do NOT use C001/C010 unless fixed per registry formula AND registry updated.

### 5.4 Formula Correction Needed (Blocked)

| factor_id | Column | Issue | Trainable? |
|-----------|--------|-------|:---:|
| C005 | tushare_limit_space_compression | implied_close midpoint → constant 0.5 | **No** |
| C006 | tushare_limit_approach_velocity | Can't diff implied_close distance | **No** |
| C008 | tushare_seal_strength_proxy | Depends on C005 fix | **No** |

### 5.5 Intraday-Family Candidates (stk_mins_5 data, NEW formulas)

These are registered candidates that would compute NEW columns from minute data (not the existing 7):

| factor_id | Name | Status | Priority | New Column Needed |
|-----------|------|--------|:---:|:---:|
| C048 | vwap_reclaim_strength | candidate_ready | P0 | Yes |
| C049 | tail_push_strength | candidate_ready | P0 | Yes |
| C064 | intraday_vwap_slope | candidate_ready | P0 | Yes |
| C065 | last_hour_volume_acceleration | candidate_ready | P0 | Yes |
| C072 | five_min_momentum_dispersion | candidate_ready | P0 | Yes |
| C085 | pullback_support_ratio | candidate_ready | P0 | Yes |
| C086 | intraday_pullback_depth | candidate_ready | P0 | Yes |
| C123 | support_failure_signal | candidate_ready | P0 | Yes |
| C071 | close_auction_vs_last_trade | candidate_ready | P0 | Yes |
| C083 | auction_to_first_bar_confirm | candidate_ready | P0 | Yes |
| C084 | auction_gap_fill_speed | candidate_ready | P0 | Yes |
| C076 | intraday_range_position_last_hour | candidate | P1 | Yes |
| C093 | morning_session_momentum_fade | candidate | P1 | Yes |
| C099 | intraday_accumulation_distribution | candidate | P1 | Yes |
| C113 | tail_session_escape_pressure | candidate | P1 | Yes |
| C060 | first15_tail_reversal | needs_validation | P2 | Yes |
| C127 | second_attempt_support | needs_validation | P2 | Yes |

**Status**: All 17 are NEW formulas requiring engineering implementation. None have code yet. **Not trainable this round.**

---

## 6. Training-Ready Factor Classification

### 6.1 trainable_factors (can enter Q1 ablation NOW)

| # | Column | Source | Condition |
|---|--------|--------|-----------|
| 1 | tushare_last_30min_return | stk_mins_5 | Register factor_id first |
| 2 | tushare_first_15min_volume_ratio | stk_mins_5 | Register factor_id first |
| 3 | tushare_intraday_volatility | stk_mins_5 | Register factor_id first |
| 4 | tushare_up_volume_ratio | stk_mins_5 | Register factor_id first |
| 5 | tushare_high_time_pct | stk_mins_5 | Register factor_id first |

**5 unique minute features** (excluding duplicates). All have:
- Real code in `_build_stk_mins_factors`
- 100% non-NA coverage
- Reasonable value distributions
- No leakage for offline training
- Will automatically enter via `feature_set="research"` → `GPU_PROBE_TUSHARE_FACTOR_FEATURES`

### 6.2 engineering_needed (fix before training)

| # | Issue | Column(s) | Fix |
|---|-------|-----------|-----|
| 1 | Duplicate formula | tushare_vwap_deviation, tushare_close_vs_vwap | Remove one OR redefine tushare_close_vs_vwap as a different formula |
| 2 | Extreme outliers | tushare_vwap_deviation | Guard against vwap < 1.0 (unit mismatch) |

### 6.3 blocked (cannot train)

| factor_id | Column | Reason |
|-----------|--------|--------|
| C001 | tushare_mf_flow_intensity | implementation_mismatch (wrong denominator) |
| C010 | tushare_float_relative_impact | implementation_mismatch (wrong volume source) |
| C005 | tushare_limit_space_compression | formula produces constant 0.5 |
| C006 | tushare_limit_approach_velocity | can't diff implied_close distance |
| C008 | tushare_seal_strength_proxy | depends on C005 fix |

### 6.4 registry_missing (need factor_id assignment)

| Column | Suggested factor_id | Suggested Name | Suggested Family |
|--------|:---:|----------------|------------------|
| tushare_last_30min_return | C133 | last_30min_return | intraday_momentum |
| tushare_first_15min_volume_ratio | C134 | first_15min_volume_concentration | intraday_volume_structure |
| tushare_vwap_deviation | C135 | vwap_deviation | intraday_price_structure |
| tushare_intraday_volatility | C136 | intraday_volatility | intraday_risk |
| tushare_up_volume_ratio | C137 | up_volume_ratio | intraday_volume_structure |
| tushare_high_time_pct | C138 | high_time_position | intraday_momentum |
| tushare_close_vs_vwap | — | **REMOVE (duplicate of C135)** | — |

---

## 7. Proposed Registry Entries

```json
[
  {
    "factor_id": "C133",
    "name": "last_30min_return",
    "family": "intraday_momentum",
    "source_type": "code_existing",
    "computable_definition": "close_last_bar / open_first_bar_after_1430 - 1",
    "data_need": "stk_mins_5",
    "asof_rule": "T-day 15:00 (full day bars)",
    "leakage_risk": "none (T-day data for T+1 prediction)",
    "coverage_estimate": "100% (3195 stocks × 804 days)",
    "column_name": "tushare_last_30min_return",
    "engineering_status": "existing_engineered",
    "priority": "P0"
  },
  {
    "factor_id": "C134",
    "name": "first_15min_volume_concentration",
    "family": "intraday_volume_structure",
    "source_type": "code_existing",
    "computable_definition": "sum(vol, 09:30-09:45) / sum(vol, all_day)",
    "data_need": "stk_mins_5",
    "asof_rule": "T-day 15:00",
    "leakage_risk": "none",
    "coverage_estimate": "100%",
    "column_name": "tushare_first_15min_volume_ratio",
    "engineering_status": "existing_engineered",
    "priority": "P0"
  },
  {
    "factor_id": "C135",
    "name": "vwap_deviation",
    "family": "intraday_price_structure",
    "source_type": "code_existing",
    "computable_definition": "(eod_close - vwap) / max(abs(vwap), 0.01)",
    "data_need": "stk_mins_5",
    "asof_rule": "T-day 15:00",
    "leakage_risk": "none",
    "coverage_estimate": "100% (but 0.43% rows have outliers from unit mismatch)",
    "column_name": "tushare_vwap_deviation",
    "engineering_status": "existing_engineered",
    "engineering_note": "Extreme outliers (max=109.6) from vol/amount unit mismatch in some parquets. Needs guard.",
    "priority": "P0"
  },
  {
    "factor_id": "C136",
    "name": "intraday_volatility",
    "family": "intraday_risk",
    "source_type": "code_existing",
    "computable_definition": "std(5min_close_pct_change) per day",
    "data_need": "stk_mins_5",
    "asof_rule": "T-day 15:00",
    "leakage_risk": "none",
    "coverage_estimate": "100%",
    "column_name": "tushare_intraday_volatility",
    "engineering_status": "existing_engineered",
    "priority": "P0"
  },
  {
    "factor_id": "C137",
    "name": "up_volume_ratio",
    "family": "intraday_volume_structure",
    "source_type": "code_existing",
    "computable_definition": "sum(vol where bar close > bar open) / sum(vol)",
    "data_need": "stk_mins_5",
    "asof_rule": "T-day 15:00",
    "leakage_risk": "none",
    "coverage_estimate": "100%",
    "column_name": "tushare_up_volume_ratio",
    "engineering_status": "existing_engineered",
    "priority": "P0"
  },
  {
    "factor_id": "C138",
    "name": "high_time_position",
    "family": "intraday_momentum",
    "source_type": "code_existing",
    "computable_definition": "bar_position_of_daily_high / (bar_count - 1)",
    "data_need": "stk_mins_5",
    "asof_rule": "T-day 15:00",
    "leakage_risk": "none",
    "coverage_estimate": "100%",
    "column_name": "tushare_high_time_pct",
    "engineering_status": "existing_engineered",
    "priority": "P0"
  }
]
```

**`tushare_close_vs_vwap` is NOT assigned a factor_id — it should be REMOVED as a duplicate.**

---

## 8. Q1 Ablation Variant Design (NOT TO EXECUTE)

### Proposed Variants

| Variant | Description | Feature Additions |
|---------|-------------|-------------------|
| G_control_c009_c004 | Baseline — same as Run G | 376 features (existing bundle) |
| G_plus_minute_all | Add all 5 unique minute features | +10 (5 value + 5 _available) |
| G_plus_minute_late | Add only late-session features (last_30min_return, high_time_pct) | +4 (2 value + 2 _available) |
| G_plus_minute_volume_structure | Add volume-structure features (first_15min, up_volume, intraday_vol) | +6 (3 value + 3 _available) |

### Training Parameters (Pre-agreed)

```
start = 2023-05-01
train_end = 2025-12-31
test_start = 2026-01-01
end = 2026-03-31  (Q1)
label_target = next_high_from_close
target_high_return_pct = 1.0
feature_selection_method = stable_tail
max_selected_features = 260
min_phase_days_3 = 1
exclude_event_limit_up = True
exclude_feature_prefix = ("cross_",)
lockbox_role = seen_research
seed = 42
feature_set = research
```

### Pre-Training Blockers

| Blocker | Severity | Resolution |
|---------|:--------:|------------|
| 7 minute features have no factor_id | P0 | Register C133-C138 in factor_registry.json |
| tushare_close_vs_vwap is duplicate of tushare_vwap_deviation | P0 | Remove from TUSHARE_FACTOR_COLUMNS or redefine |
| tushare_vwap_deviation extreme outliers (max=109.6) | P1 | Add guard in _build_stk_mins_factors |
| 798 features >> 376 in bundle (code diverged) | Info | A new "research" run will use 798 features, not 376 |

---

## 9. Explicit Statements

1. **No training executed** — this is pre-training audit only
2. **7 minute features are registry_missing** — cannot train until registered
3. **tushare_close_vs_vwap = tushare_vwap_deviation** — duplicate, must fix
4. **No leakage** in any of the 7 features for offline T+1 prediction
5. **Not usable at 14:57 realtime** without as-of cutoff modification
6. **C001/C010 remain blocked** (implementation_mismatch, per user constraint)
7. **C005/C006/C008 remain blocked** (formula correction needed)
8. **Do not claim passed/final** — pre-training gate only
9. **Do not commit/push**
10. **Next step: register C133-C138 → fix duplicate → then user-approved training**

---

## 10. Data Availability Confirmation

| Source | Path | Files | Date Range | Status |
|--------|------|:-----:|------------|:------:|
| stk_mins_5 | `E:\...\tushare\stk_mins_5` | 3,195 | 2023-01-03 to 2026-04-30 | Available |
| Exception | 001395.SZ | 1 | Partial (14,798 bars) | Noted, not blocking |
| 2026-05-06 | — | 0 | — | Not needed this round |

---

*Pre-training selection audit complete. 5 unique minute features ready for registration and training (pending duplicate fix). 2 blocked duplicates. 5 tushare candidates blocked by formula/implementation issues. 17 intraday-family candidates need new engineering. No training executed.*

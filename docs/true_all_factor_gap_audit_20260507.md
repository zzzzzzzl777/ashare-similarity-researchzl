# True All-Factor Gap Audit — 2026-05-07

**Purpose**: Determine exactly which trainable factors are covered vs. missing in the current `diagnostic_expanded_matrix_51` run, identify governance issues, and establish what must be fixed before any authoritative training comparison can be claimed.

**Authority source**: `E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json`

---

## 1. Factor Registry — Full Status Summary

| Status | Count | Factor IDs |
|--------|:-----:|------------|
| existing_engineered | 13 | C011, C133, C134, C136, C137, C138, C154, C156, C157, C158, C159, C161, C162 |
| verified_engineerable | 2 | C004, C009 |
| candidate_ready | 47 | C043-C050, C063-C072, C083-C092, C103-C110, C118-C123, C128-C132 |
| candidate | 79 | (includes C141, C143, C151, C152 and many others) |
| needs_validation | 10 | C060, C080-C082, C100-C102, C116-C117, C127 |
| needs_engineering | 3 | C059, C061, C062 |
| needs_formula_correction | 3 | C005, C006, C008 |
| implementation_mismatch | 2 | C001, C010 |
| needs_data_check | 2 | C013, C015 |
| blocked_until_outlier_guard | 1 | C135 |
| unknown | 11 | C032-C042 |
| **Total** | **174** | |

---

## 2. Authoritative Trainable Universe (per factor_training_matrix_all_20260507.json)

**15 factors** have `trainable_now=True`:

| # | Factor ID | Column | Family | Source Status |
|---|-----------|--------|--------|:-------------:|
| 1 | C004 | tushare_ff_adjusted_flow | moneyflow_derivative | verified_engineerable |
| 2 | C009 | tushare_main_force_divergence | moneyflow_derivative | verified_engineerable |
| 3 | C011 | tushare_auction_open_vwap_ratio | stk_auction_tier1b | existing_engineered |
| 4 | C133 | tushare_last_30min_return | intraday_momentum | existing_engineered |
| 5 | C134 | tushare_first_15min_volume_ratio | intraday_volume_structure | existing_engineered |
| 6 | C136 | tushare_intraday_volatility | intraday_risk | existing_engineered |
| 7 | C137 | tushare_up_volume_ratio | intraday_volume_structure | existing_engineered |
| 8 | C138 | tushare_high_time_pct | intraday_momentum | existing_engineered |
| 9 | C154 | tushare_price_vs_cost_20d | price_structure | existing_engineered |
| 10 | C156 | tushare_abnormal_3d_deviation | momentum | existing_engineered |
| 11 | C157 | tushare_vol_gain_20d | volume_structure | existing_engineered |
| 12 | C158 | tushare_inv_t_20d | volume_structure | existing_engineered |
| 13 | C159 | tushare_asr_60d | price_structure | existing_engineered |
| 14 | C161 | tushare_illiq_classic_20d | liquidity | existing_engineered |
| 15 | C162 | tushare_ato_120d | volume_structure | existing_engineered |

---

## 3. Minute Factor ID Mapping (M001-M005 → Official IDs)

The `run_expanded_matrix.py` script uses non-registry IDs for minute factors:

| Script ID | Official Registry ID | Column |
|:---------:|:--------------------:|--------|
| M001 | **C133** | tushare_last_30min_return |
| M002 | **C134** | tushare_first_15min_volume_ratio |
| M003 | **C136** | tushare_intraday_volatility |
| M004 | **C137** | tushare_up_volume_ratio |
| M005 | **C138** | tushare_high_time_pct |

**Impact**: All ledger entries and manifest entries using M001-M005 must be re-mapped to C133-C138 for governance compliance. This is a P1 audit-trail defect in the diagnostic run.

---

## 4. Current 51-Variant Manifest Coverage vs. Trainable Universe

### Covered (10 of 15 trainable):
C004, C009, C011, C154, C156, C157, C158, C159, C161, C162

### MISSING (5 of 15 trainable):
| Factor ID | Column | Why Missing |
|-----------|--------|-------------|
| **C133** | tushare_last_30min_return | Present in manifest as "M001" — ID mapping error only |
| **C134** | tushare_first_15min_volume_ratio | Present as "M002" — ID mapping error only |
| **C136** | tushare_intraday_volatility | Present as "M003" — ID mapping error only |
| **C137** | tushare_up_volume_ratio | Present as "M004" — ID mapping error only |
| **C138** | tushare_high_time_pct | Present as "M005" — ID mapping error only |

**Note**: The minute factors ARE included in training (via their column names), but are recorded under wrong IDs (M001-M005 instead of C133-C138). The training is valid but the audit trail is incorrect.

### Extra factors (NOT in trainable universe):
| Factor ID | Status in Registry | Column | Governance |
|-----------|--------------------|--------|:----------:|
| C141 | candidate | NO column_name in registry | **DIAGNOSTIC ONLY** |
| C143 | candidate | NO column_name in registry | **DIAGNOSTIC ONLY** |
| C151 | candidate | NO column_name in registry | **DIAGNOSTIC ONLY** |
| C152 | candidate | NO column_name in registry | **DIAGNOSTIC ONLY** |

---

## 5. C141/C143/C151/C152 Governance Assessment

### Current Status:
- `engineering_status`: candidate
- `column_name`: NOT SET in registry
- `trainable_now`: NOT SET (defaults to False)

### Evidence of Implementation:
- Code exists in `free_data_factors.py:_build_daily_ohlcv_derived_factors()` (round 2 block)
- Columns registered in `TUSHARE_FACTOR_COLUMNS`: YES (4 columns added)
- Promotion gate passed: YES (documented in `c141_c152_promotion_gate_20260507.md`)
- No leakage: CONFIRMED
- No future function: CONFIRMED
- Coverage: C141 100%, C143 100%, C151 ~70%, C152 100%

### Governance Decision:
These factors HAVE real feature columns and PASS the promotion gate, but the **registry has NOT been updated** to reflect `existing_engineered` status. Until the registry is updated:
- Runs including C141/C143/C151/C152 = **diagnostic_only**
- Cannot enter freeze decision based on these runs
- Cannot claim "all trainable factors compared"

### Path to Resolution:
1. Update `factor_registry.json`: set `engineering_status` = `existing_engineered`, add `column_name`, set `trainable_now=True` for C141/C143/C151/C152
2. Regenerate `factor_training_matrix_all_20260507.json` to include 19 trainable factors
3. Only THEN can runs including these factors be authoritative

---

## 6. C139-C173 Full Status (from Engineering Backlog)

| Factor ID | Status | Column Exists | Can Train This Round |
|-----------|--------|:-------------:|:--------------------:|
| C139 | blocked_by_data_source (limit_pool) | NO | NO |
| C140 | blocked_by_data_source (limit_pool) | NO | NO |
| C141 | candidate (code written, gate passed) | YES* | DIAGNOSTIC ONLY |
| C142 | blocked_by_data_source (limit_pool) | NO | NO |
| C143 | candidate (code written, gate passed) | YES* | DIAGNOSTIC ONLY |
| C144-C150 | blocked_by_data_source (limit_pool) | NO | NO |
| C151 | candidate (code written, gate passed) | YES* | DIAGNOSTIC ONLY |
| C152 | candidate (code written, gate passed) | YES* | DIAGNOSTIC ONLY |
| C153 | blocked_by_data_source (limit_pool) | NO | NO |
| C154 | existing_engineered | YES | YES |
| C155 | blocked_by_data_source (sector) | NO | NO |
| C156 | existing_engineered | YES | YES |
| C157 | existing_engineered | YES | YES |
| C158 | existing_engineered | YES | YES |
| C159 | existing_engineered | YES | YES |
| C160 | engineering_needed (complex) | NO | NO |
| C161 | existing_engineered | YES | YES |
| C162 | existing_engineered | YES | YES |
| C163 | engineering_needed (complex) | NO | NO |
| C164-C167 | blocked_by_data_source (limit_pool) | NO | NO |
| C168-C170 | blocked_by_data_source (sector) | NO | NO |
| C171-C173 | blocked_by_data_source (external API) | NO | NO |

*Column exists in code but NOT in registry.

---

## 7. Training Completion Status

| Category | Factor IDs | Status |
|----------|-----------|--------|
| **Smoke-tested (10 variants)** | C154, C156, C157, C158, C159, C161, C162 + C133-C138 as group | Pre-expanded manifest |
| **Seed-stability tested** | C154, C158, C154+C158 pair | Phase 7 complete |
| **In diagnostic_expanded_matrix_51** | C004, C009, C011, C154-C162, C133-C138 (as M001-M005), C141-C152 | Running (NOT authoritative) |
| **Audit-complete but NOT trained** | C141, C143, C151, C152 | Gate passed but registry not updated |
| **Blocked (no engineering path this round)** | C139-C140, C142, C144-C150, C153, C155, C160, C163-C173 | 24 factors deferred |

---

## 8. Blockers

| Severity | Issue | Resolution |
|:--------:|-------|------------|
| **P1** | C141/C143/C151/C152 registry status NOT updated | Update factor_registry.json |
| **P1** | Minute factor IDs wrong in manifest/ledger (M001-M005 vs C133-C138) | Fix mapping in manifest and future scripts |
| **P1** | diagnostic_expanded_matrix_51 CANNOT be used for freeze decision | Must regenerate true manifest after registry fix |
| P2 | C004/C009 are verified_engineerable but not existing_engineered | Verify columns exist, promote if appropriate |

---

## 9. Self-Audit

| Check | Result |
|-------|:------:|
| All 174 factor_ids from registry enumerated | PASS |
| trainable_now universe confirmed (15 factors) | PASS |
| Manifest coverage vs trainable compared | PASS |
| C133-C138 mapping to M001-M005 identified | PASS |
| C141/C143/C151/C152 governance status assessed | PASS |
| C139-C173 full status from backlog included | PASS |
| P0/P1 blockers identified | 3 P1 blockers found |
| Diagnostic run NOT interrupted | PASS (running) |
| No freeze/April/claim made | PASS |

---

## 10. Required Actions Before True Manifest

1. **Update factor_registry.json** for C141/C143/C151/C152:
   - `engineering_status` → `existing_engineered`
   - Add `column_name` field
   - Set `trainable_now` → True (pending registry schema check)

2. **Fix minute factor ID mapping** in all scripts and manifests:
   - M001 → C133, M002 → C134, M003 → C136, M004 → C137, M005 → C138

3. **Regenerate factor_training_matrix** with corrected 19-factor trainable universe

4. **Generate true_all_factor_expansion_manifest** from corrected registry

5. **Only then** proceed to authoritative training runs

---

**Gap audit COMPLETE. 3 P1 blockers prevent freeze. Diagnostic run continues but is NOT authoritative.**

# Phase 0: 14:57 Hard-Unavailable-Excluded Training — Acceptance Audit

**Date:** 2026-05-07  
**Status:** PASS — No P0/P1 blockers  
**Purpose:** Verify handoff document assumptions before any training

---

## 1. Hard Unavailable Features Confirmed

7 same-day Tushare moneyflow split features + 7 `_available` companions = **14 columns to exclude**:

| # | Value Column | Available Companion |
|---|---|---|
| 1 | `tushare_net_mf_amount` | `tushare_net_mf_amount_available` |
| 2 | `tushare_lg_buy_sell_ratio` | `tushare_lg_buy_sell_ratio_available` |
| 3 | `tushare_elg_buy_sell_ratio` | `tushare_elg_buy_sell_ratio_available` |
| 4 | `tushare_mf_strength` | `tushare_mf_strength_available` |
| 5 | `tushare_sm_sell_pressure` | `tushare_sm_sell_pressure_available` |
| 6 | `tushare_main_force_divergence` | `tushare_main_force_divergence_available` |
| 7 | `tushare_ff_adjusted_flow` | `tushare_ff_adjusted_flow_available` |

All 14 confirmed present in superset cache (fingerprint `50f0a15cc17d25ca`). Will be excluded via `exclude_feature_names` at variant training time.

---

## 2. C004/C009 Formal Exclusion

- C004 (`tushare_ff_adjusted_flow`) — **forbidden in this round's formal training**
- C009 (`tushare_main_force_divergence`) — **forbidden in this round's formal training**
- Both can only serve as old full-day reference comparators

---

## 3. Old Manifest Cannot Be Reused

`true_all_factor_expansion_manifest_20260507.json` contains C004/C009 in its trainable universe (19 factors). This round requires a new manifest with only 17 factors (C004/C009 removed).

---

## 4. Superset Runner Architecture Verified

- Script: `scripts/run_superset_factor_matrix.py`
- Architecture: Phase A (build superset once) + Phase B (variant training via column slice)
- Supports `exclude_feature_names` per variant — the mechanism for hard exclusion
- Validated superset cache: fingerprint `50f0a15cc17d25ca`, 370,430 rows × 817 columns
- All 17 remaining trainable factor columns confirmed present and non-zero

---

## 5. Remaining Trainable Factor Universe (17)

| # | Factor ID | Column | As-of Tier |
|---|---|---|---|
| 1 | C011 | tushare_auction_open_vwap_ratio | strict_pre1457_or_metadata |
| 2 | C133 | tushare_last_30min_return | needs_asof_rewrite_for_strict_1457 |
| 3 | C134 | tushare_first_15min_volume_ratio | needs_asof_rewrite_for_strict_1457 |
| 4 | C136 | tushare_intraday_volatility | needs_asof_rewrite_for_strict_1457 |
| 5 | C137 | tushare_up_volume_ratio | needs_asof_rewrite_for_strict_1457 |
| 6 | C138 | tushare_high_time_pct | needs_asof_rewrite_for_strict_1457 |
| 7 | C141 | tushare_prev_top20_chase_mean | approximated_1457_or_post_close |
| 8 | C143 | tushare_volume_sufficiency_ratio | approximated_1457_or_post_close |
| 9 | C151 | tushare_anti_drop_strength_20d | approximated_1457_or_post_close |
| 10 | C152 | tushare_multi_wave_count_60d | approximated_1457_or_post_close |
| 11 | C154 | tushare_price_vs_cost_20d | approximated_1457_or_post_close |
| 12 | C156 | tushare_abnormal_3d_deviation | approximated_1457_or_post_close |
| 13 | C157 | tushare_vol_gain_20d | approximated_1457_or_post_close |
| 14 | C158 | tushare_inv_t_20d | approximated_1457_or_post_close |
| 15 | C159 | tushare_asr_60d | approximated_1457_or_post_close |
| 16 | C161 | tushare_illiq_classic_20d | approximated_1457_or_post_close |
| 17 | C162 | tushare_ato_120d | approximated_1457_or_post_close |

---

## 6. Blocked Factors (Not Trainable This Round)

C001, C004, C005, C006, C008, C009, C010, C135, and all unengineered C139-C173 (those without real feature columns in the superset).

---

## 7. Git State

110 dirty files (modified + untracked). Recorded but not blocking — superset cache was built and validated prior to this session.

---

## 8. P0/P1 Assessment

| Check | Result |
|---|---|
| 7 hard unavailable in scope | ✓ confirmed |
| C004/C009 not in formal universe | ✓ confirmed |
| Old manifest reuse forbidden | ✓ confirmed |
| Superset runner supports variant exclusion | ✓ confirmed |
| 17 factor columns in cache | ✓ confirmed |
| No outstanding P0/P1 from prior work | ✓ confirmed |

**Verdict: PASS — proceed to Phase 1**

---

## 9. Self-Review Record

```
self_review_pass_1_scope_boundary = done
self_review_pass_2_data_factor_boundary = done
self_review_pass_3_engineering_audit_boundary = done
```

- Pass 1: This round is hard-unavailable-excluded training, not old full-day. Old model = reference only. April only after freeze. No final_unseen claims.
- Pass 2: 7 value + 7 available = 14 exclusions. C004/C009 forbidden. T-1 proxy forbidden. push2 forbidden. strict/approximated/post_close distinction required.
- Pass 3: Superset one-build multi-slice. New manifest. Full phase chain. P0/P1 gates. Ledger per run.

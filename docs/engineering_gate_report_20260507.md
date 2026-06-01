# Phase 2: Engineering Gate Report — 2026-05-07

**Status**: **P1 — Engineering required before meaningful new factor training**

---

## 1. Confirmed Trainable Factors (Real Feature Columns Verified)

| Factor ID | Column Name | In Baseline (747-feat)? | Requires Minute Bars? |
|-----------|-------------|:-----------------------:|:---------------------:|
| C004 | `tushare_ff_adjusted_flow` | YES | No |
| C009 | `tushare_main_force_divergence` | YES | No |
| C011 | `tushare_auction_open_vwap_ratio` | YES | No |
| C133 | `tushare_last_30min_return` | No (757-feat mode) | YES |
| C134 | `tushare_first_15min_volume_ratio` | No (757-feat mode) | YES |
| C136 | `tushare_intraday_volatility` | No (757-feat mode) | YES |
| C137 | `tushare_up_volume_ratio` | No (757-feat mode) | YES |
| C138 | `tushare_high_time_pct` | No (757-feat mode) | YES |

### Assessment

- **C004/C009/C011**: Already in the 747-feature baseline. The baseline IS already using these factors. Single-factor ablation would mean REMOVING them, not adding.
- **C133-C138**: Round 4 tested exhaustively (32 combos + 5 seeds + 4 budgets). Conclusion: NO_FREEZE. Signal-to-noise 0.067. Not additive.

**Net new factors available for training: 0**

---

## 2. Blocked Factors (Correctly Prevented)

| Factor | Column | Block Reason | Verified |
|--------|--------|:------------:|:--------:|
| C001 | `tushare_mf_flow_intensity` | implementation_mismatch (code formula != registry formula) | YES |
| C005 | `tushare_limit_space_compression` | needs_formula_correction (constant 0.5) | YES |
| C006 | `tushare_limit_approach_velocity` | needs_formula_correction (depends on C005) | YES |
| C008 | `tushare_seal_strength_proxy` | needs_formula_correction (depends on C005) | YES |
| C010 | `tushare_float_relative_impact` | implementation_mismatch (uses buy_vol not daily vol) | YES |
| C135 | `tushare_vwap_deviation` | blocked_until_outlier_guard (max=109.6) | YES |

All correctly excluded from latest runs.

---

## 3. Daily OHLCV Priority Group — Engineering Status

| Factor ID | Name | Definition | Feature Column | Status |
|-----------|------|-----------|:--------------:|:------:|
| C154 | price_vs_cost | `(close - VWAP_Nd) / VWAP_Nd` | NOT IMPLEMENTED | Needs engineering |
| C156 | abnormal_3d_deviation | `sum(pct_change, 3d) - sum(index_pct, 3d)` | NOT IMPLEMENTED | Needs engineering |
| C157 | VOL_GAIN | `mean(TO|up, 20d) / mean(TO|down, 20d)` | NOT IMPLEMENTED | Needs engineering |
| C158 | INV_t | `-sum(sign(ret)*vol, 20d) / sum(vol, 20d)` | NOT IMPLEMENTED | Needs engineering |
| C159 | ASR | `(pctile90 - pctile10, 60d) / close` | NOT IMPLEMENTED | Needs engineering |
| C161 | ILLIQ_classic | `mean(|ret|/vol, 20d)` | NOT IMPLEMENTED | Needs engineering |
| C162 | ATO | `(mean(TO,20) - mean(TO,120)) / std(TO,120)` | NOT IMPLEMENTED | Needs engineering |

All 7 factors use only daily OHLCV data. All have:
- **asof_rule**: T-day close (safe)
- **leakage_risk**: none
- **data_need**: daily bars (already cached at `E:\ashare_similarity_runtime\data\raw\bars\daily\`)

---

## 4. P1 Assessment

| Issue | Severity | Impact |
|-------|:--------:|--------|
| No net new trainable factors beyond baseline and already-tested minute group | P1 | Cannot perform meaningful new factor comparison without engineering |
| Daily OHLCV group (7 factors) requires code implementation | P1 | Blocking Phase 5+ |
| C139-C152 (13 factors from raw_review) all need engineering | P2 | Future round |
| C153-C173 remaining (14 factors) need limit_pool/API/formula lock | P2 | Future round |

---

## 5. Recommended Action

**Proceed to Phase 3: Implement the 7 daily OHLCV factors (C154/C156/C157/C158/C159/C161/C162).**

These factors:
1. Use only daily bar data (already available in `E:\ashare_similarity_runtime\data\raw\bars\daily\`)
2. Have clean asof (T-day close)
3. Have no leakage risk
4. Have well-defined formulas from academic literature (Amihud, Z-score, conditional volume)
5. Are 14:57 friendly (daily bars available before close or close-proxy feasible)

After implementation, coverage/outlier/asof audit must pass before smoke training.

---

## 6. Self-Audit

| Check | Result |
|-------|:------:|
| All trainable factors verified in actual feature lists | PASS |
| Blocked factors correctly absent from latest runs | PASS |
| C001/C005/C006/C008/C010/C135 blocked | PASS |
| No unauthorized factor enters training | PASS |
| Daily OHLCV formulas from registry (not hand-written) | PASS |
| P1 correctly identified and reported | PASS |

---

**Phase 2 COMPLETE. P1 identified: must engineer daily OHLCV factors before training. Proceeding to Phase 3 implementation.**

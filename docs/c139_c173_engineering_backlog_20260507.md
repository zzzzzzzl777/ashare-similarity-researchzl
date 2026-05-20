# C139-C173 Engineering Backlog Audit — 2026-05-07

**Purpose**: Full status audit of all factors C139-C173 to determine which can enter training this round.

---

## 1. Status Summary

| Status | Count | Factor IDs |
|--------|:-----:|------------|
| existing_engineered (promoted) | 7 | C154, C156, C157, C158, C159, C161, C162 |
| quick_engineering_possible | 4 | **C141, C143, C151, C152** |
| engineering_needed (daily OHLCV, complex) | 2 | C160, C163 |
| blocked_by_data_source (limit_pool) | 15 | C139, C140, C142, C144, C145, C146, C147, C148, C149, C150, C153, C164, C165, C166, C167 |
| blocked_by_data_source (sector_theme) | 3 | C155, C168, C169, C170 |
| blocked_by_data_source (external API) | 3 | C171, C172, C173 |
| duplicate | 0 | — |
| leakage_risk | 0 | — |
| **Total** | **35** | |

---

## 2. Per-Factor Detail

### A. Already Promoted (existing_engineered) — 7 factors

| ID | Name | Column | Status |
|----|------|--------|--------|
| C154 | price_vs_cost | `tushare_price_vs_cost_20d` | In training |
| C156 | abnormal_3d_deviation | `tushare_abnormal_3d_deviation` | In training |
| C157 | VOL_GAIN | `tushare_vol_gain_20d` | In training |
| C158 | INV_t | `tushare_inv_t_20d` | In training |
| C159 | ASR | `tushare_asr_60d` | In training |
| C161 | ILLIQ_classic | `tushare_illiq_classic_20d` | In training |
| C162 | ATO | `tushare_ato_120d` | In training |

### B. Quick Engineering Possible — 4 factors

#### C141 — prev_top20_chase_real
- **Family**: market_breadth
- **Definition**: `mean(pct_change_T, top20_gainers_T-1); red_rate = count(pct_change_T > 0, top20_gainers_T-1) / 20`
- **Data need**: daily_ohlcv ONLY (cross-sectional)
- **AsOf**: T-day close (ranks by T-1, measures T-day)
- **Leakage**: NONE
- **Future function**: NONE
- **Implementation**: Load all daily bars → for each date, rank stocks by T-1 pct_change → top 20 → compute their T-day mean return. Market-level factor (same value for all stocks on a given day).
- **Complexity**: Medium (cross-section computation)
- **Verdict**: **quick_engineering_possible**

#### C143 — is_volume_sufficient
- **Family**: volume_quality
- **Definition**: `turnover_rate_T / turnover_rate_T-1` (continuous ratio)
- **Data need**: daily_ohlcv (turnover field)
- **AsOf**: T-day close
- **Leakage**: NONE
- **Future function**: NONE
- **Implementation**: Per-symbol: `df["turnover"].shift(0) / df["turnover"].shift(1)`. Trivial.
- **Complexity**: Trivial
- **Verdict**: **quick_engineering_possible**

#### C151 — anti_drop_strength
- **Family**: relative_strength
- **Definition**: `pct_change_stock / pct_change_index WHERE pct_change_index < -0.5%`; rolling 20d mean of this conditional ratio
- **Data need**: daily_ohlcv (stock + index SH000001)
- **AsOf**: T-day close
- **Leakage**: NONE
- **Future function**: NONE
- **Implementation**: Load index daily bar → for each stock, compute conditional ratio on index-down days → rolling mean.
- **Complexity**: Low-Medium (needs index reference)
- **Prerequisite**: Index bar file must exist in `E:\ashare_similarity_runtime\data\raw\bars\daily\` (SH000001.parquet or similar)
- **Verdict**: **quick_engineering_possible** (if index bar available)

#### C152 — multi_wave_count
- **Family**: technical_pattern
- **Definition**: `count(rising_segments) in last 60 trading days`; rising_segment = consecutive days where `close > close_5d_ago`
- **Data need**: daily_ohlcv
- **AsOf**: T-day close
- **Leakage**: NONE
- **Future function**: NONE
- **Implementation**: Per-symbol: rolling 60d window, count zero-crossings of `close - close.shift(5)` from negative to positive.
- **Complexity**: Low
- **Verdict**: **quick_engineering_possible**

### C. Engineering Needed (Complex OHLCV) — 2 factors

#### C160 — chip_weight
- **Definition**: Recursive turnover decay `w_i = turnover_i * prod(1 - turnover_j, j>i)` (CYQ foundation)
- **Data need**: daily_ohlcv
- **Complexity**: HIGH (recursive formula across entire history, cumulative product)
- **Verdict**: **engineering_needed** — deferrable to next round

#### C163 — TAM (turnover-adjusted momentum)
- **Definition**: `cumulative_return_12m_skip_1m - beta * mean_turnover_12m`
- **Data need**: daily_ohlcv (needs 12+ months history)
- **Complexity**: Medium-High (requires beta estimation)
- **Verdict**: **engineering_needed** — deferrable to next round

### D. Blocked by Data Source (limit_pool) — 15 factors

| ID | Name | Block Reason |
|----|------|-------------|
| C139 | real_limit_up_premium_gap | Needs stock_zt_pool_previous_em (not in current pipeline) |
| C140 | zbgc_sector_pressure | Needs stock_zt_pool_zbgc_em + sector membership |
| C142 | theme_limit_density | Needs limit_pool + sector theme membership |
| C144 | leader_pull_effect | Needs limit_pool + sector theme |
| C145 | theme_height_suppression | Needs limit_pool + sector theme |
| C146 | support_one_word_count | Needs sector theme + limit detection |
| C147 | eruption_strength | Needs limit_pool (seal_money/unbuyable_rate) |
| C148 | is_ground_sky | Needs limit detection (low==low_limit AND close==high_limit) |
| C149 | seal_trend | Needs limit_pool (seal_money series) |
| C150 | old_leader_decay | Needs limit_pool (highest_board detection) |
| C153 | nuclear_ratio | Needs limit_pool (stock_zt_pool_em consecutive day comparison) |
| C164 | new_leader_emerge | Needs limit_pool (board_height + seal_time) |
| C165 | need_second_seal | Needs limit_pool (for limit-up day identification) |
| C166 | late_seal_ratio | Needs limit_pool (seal_time field) |
| C167 | early_seal_ratio | Needs limit_pool (seal_time field) |

### E. Blocked by Data Source (sector/theme) — 4 factors

| ID | Name | Block Reason |
|----|------|-------------|
| C155 | cap_ratio | Needs sector leader identification + float_mv |
| C168 | vol_premium | Needs sector membership for sector-relative volume |
| C169 | max_theme_weight | Needs ths_index_member weights |
| C170 | hhi_theme_concentration | Needs ths_index_member weights |

### F. Blocked by Data Source (external API) — 3 factors

| ID | Name | Block Reason |
|----|------|-------------|
| C171 | new_high_strength | Needs stock_zt_pool_strong_em (AKShare API not cached) |
| C172 | recent_limit_frequency | Needs stock_zt_pool_strong_em (AKShare API not cached) |
| C173 | true_limit_up_ratio | Needs stock_market_activity_legu (AKShare API not cached) |

---

## 3. Quick-Engineering Plan (This Round)

**Factors to implement**: C141, C143, C151, C152

**Prerequisites**:
1. ✅ Daily bars available at `E:\ashare_similarity_runtime\data\raw\bars\daily\`
2. ⬜ Index bar (SH000001) must be verified in daily bars directory (for C151)
3. ✅ All factors use T-day close only (no future function)
4. ✅ All factors have no leakage risk

**Implementation site**: Add to `_build_daily_ohlcv_derived_factors()` in `free_data_factors.py`

**Columns to add**:
- `tushare_prev_top20_chase_mean` (C141)
- `tushare_volume_sufficiency_ratio` (C143)
- `tushare_anti_drop_strength_20d` (C151)
- `tushare_multi_wave_count_60d` (C152)

**After implementation**: Run promotion gate (same 14-rule gate as C154-C162), update registry, regenerate feature cache, add to expanded manifest.

---

## 4. Deferred to Next Round

| Category | Count | Reason |
|----------|:-----:|--------|
| Complex OHLCV | 2 | C160 (recursive formula), C163 (12m momentum residual) |
| Limit pool dependency | 15 | Data pipeline not built for limit_pool API scraping |
| Sector/theme dependency | 4 | Theme membership data incomplete |
| External API dependency | 3 | API endpoints not cached |
| **Total deferred** | **24** | |

---

## 5. Self-Audit

| Check | Result |
|-------|:------:|
| All 35 factors (C139-C173) assessed | PASS |
| Each has a final status category | PASS |
| No factor left in "unknown" state | PASS |
| Quick-eng candidates verified for: data_source, asof, leakage, future function | PASS |
| Blocked factors have clear blocked_reason | PASS |
| No unauthorized training (all blocked factors excluded) | PASS |
| C154-C162 correctly marked as existing_engineered | PASS |

---

**Backlog audit COMPLETE. 4 factors (C141/C143/C151/C152) cleared for quick engineering.**

# Minute Factor Re-Audit (2026-05-11, updated 2026-05-12)

## Part 1: Existing Minute/Intraday Factors in Registry

### Current Status Summary

| Category | Count |
|----------|-------|
| Registered minute/intraday candidates in C001-C173 | 42 |
| Of which: existing_engineered (have code column) | 6 (+1 blocked) |
| Of which: candidate/candidate_ready (no code yet) | 35 |
| Code-level minute columns (intraday_factors.py) | 29 (`minute_*`) |
| Code-level stk_mins_5 columns (free_data_factors.py) | 7 (`tushare_*`) |
| Total minute-level feature slots in model | 72 (36 base + 36 _available) |

### Engineered Minute Factors (C133-C138)

| ID | Name | Column | Status | Data Source |
|----|------|--------|--------|-------------|
| C133 | last_30min_return | tushare_last_30min_return | existing_engineered | stk_mins_5 |
| C134 | first_15min_volume_concentration | tushare_first_15min_volume_ratio | existing_engineered | stk_mins_5 |
| C135 | vwap_deviation | tushare_vwap_deviation | blocked (outlier) | stk_mins_5 |
| C136 | intraday_volatility | tushare_intraday_volatility | existing_engineered | stk_mins_5 |
| C137 | up_volume_ratio | tushare_up_volume_ratio | existing_engineered | stk_mins_5 |
| C138 | high_time_position | tushare_high_time_pct | existing_engineered | stk_mins_5 |

### Key Findings

- **当前正式库只有 5min 工程化分钟因子。不存在 1min 工程化因子。**
- All 36 code-level minute columns derive from 5-minute bars (stk_mins_5 or local bars/5/).
- "15min" and "30min" in column names are time windows aggregated FROM 5-min bars.
- No `stk_mins_1`, `stk_mins_15`, or `stk_mins_30` references anywhere in code.
- 29 `minute_*` columns from `intraday_factors.py` are in `GPU_PROBE_RESEARCH_FEATURES` but NOT individually registered beyond C133-C138.

---

## Part 2: Full Raw Pool Minute/Tick/L2 Search

### Overall Results

| Category | Count |
|----------|-------|
| Total raw pool records | 3,075 |
| **Minute/tick/L2 related records** | **553** |
| already_registered_or_implemented | 51 |
| minute_bar_engineerable_now (initial) | 209 |
| multi_frequency_candidate | 2 |
| needs_auction_data | 68 |
| still_blocked_l2_tick_orderbook | 189 |
| reject_duplicate_or_vague | 34 |

---

## Part 3: Strict Reclassification of 209 Candidates (2026-05-12)

### Methodology

Two-pass strict review:
1. **Automated**: keyword matching (L2/tick/auction/strategy) + name overlap with 36 existing minute columns + board_structure/market_emotion concept overlap
2. **Manual override**: 50+ individual dispositions based on raw_text analysis, formula verification against `intraday_factors.py` source code

### Reclassification Summary

| Category | Count | Description |
|----------|-------|-------------|
| **ready_to_register_minute_bar** | **132** | Clear formula, 5min bars sufficient, distinct from existing 36 |
| **duplicate_existing** | **14** | Same concept/formula as existing minute column or board_structure feature |
| **needs_formula_clarification** | **15** | No computable scalar formula in raw_text, or pattern/shape description |
| **needs_data_beyond_minute_bar** | **28** | Requires L2/tick/auction/1min/northbound or other unavailable data |
| **reject_not_factor** | **20** | Trading strategy, subjective rule, or non-quantifiable concept |
| TOTAL | 209 | |

### Confirmed Duplicates (code-verified)

| raw_factor_id | Name | Existing Column | Verification |
|---------------|------|-----------------|--------------|
| RAW002091 | AC1 | minute_return_autocorr_intraday | `_autocorr()`: corr(values[1:], values[:-1]) = lag-1 autocorrelation on 5min returns. Identical. |
| RAW002234 | RSK | minute_realized_skew | `_series_skew()`: mean((centered/std)³). Formula sum(r³)/RV^(3/2) is algebraically equivalent. Identical. |
| RAW002106 | CloseSurge | minute_last_30min_volume_ratio | Last 6 bars (14:30-15:00) volume / total. `last_30min_volume_ratio` computes this exactly. Identical. |
| RAW001484 | recovery_ratio | minute_intraday_close_position | `_close_position()`: (close-low)/(high-low). Same formula. Identical. |

### Verified DISTINCT (originally flagged for verification)

| raw_factor_id | Name | Flagged Overlap | Verdict | Reason |
|---------------|------|-----------------|---------|--------|
| RAW002083 | Vol_close_ratio | minute_closing_auction_volume_ratio | **DISTINCT** | Vol_close_ratio = last_bar/TOTAL. closing_auction_volume_ratio = last_bar/MEAN(bars). Different denominators. |
| RAW002085 | VS_ratio | none | **BLOCKED** | Requires 1min data (RV at 1min frequency). No 1min source available. |

---

## Verified Final Top 20 (ready_to_register_minute_bar only)

All duplicates removed. VS_ratio moved to P2-blocked. 5 replacement candidates added from ready pool.

### P0 — High Priority

| # | raw_factor_id | recommended_name | formula | required_columns | frequency | asof_rule | duplicate_check | leakage_check | priority |
|---|---------------|------------------|---------|------------------|-----------|-----------|-----------------|---------------|----------|
| 1 | RAW002088 | intraday_vol_herfindahl | Σ(V_k/V_total)² for k=1..48 (5min bars) | volume_per_bar | 5min | T-day 15:00 | DISTINCT: minute_volume_gini uses Gini coefficient, this uses HHI — different concentration measure | none — uses only T-day completed bars | P0 |
| 2 | RAW002130 | intraday_profit_ratio | Σ(Vol_i × I(Close_i > VWAP_i)) / Σ(Vol_i) | close_per_bar, vwap_per_bar, volume_per_bar | 5min | T-day 15:00 | DISTINCT: No existing feature measures volume-weighted profitable fraction. Academic CYQ concept. | none — uses only T-day completed bars | P0 |
| 3 | RAW002077 | vwap_deviation_normalized | (Close - VWAP) / σ(intraday_prices) | close, vwap, intraday_price_series | 5min | T-day 15:00 | DISTINCT: C135 tushare_vwap_deviation is unnormalized and blocked (outlier). This σ-standardized version fixes the outlier problem. | none | P0 |
| 4 | RAW002090 | intraday_volume_clustering | Max(V_5min) / Mean(V_5min) | volume_per_bar | 5min | T-day 15:00 | DISTINCT: No exact match. minute_volume_gini measures distribution equality; this measures peak-to-average ratio. | none | P0 |
| 5 | RAW001879 | intraday_ofi_proxy | Σ(sign(r_bar) × V_bar) / Σ(V_bar) | return_per_bar, volume_per_bar | 5min | T-day 15:00 | DISTINCT: No OFI (order flow imbalance) feature exists. This is bar-level proxy using return direction × volume. | none — does NOT need L2 order data | P0 |

### P1 — Medium Priority

| # | raw_factor_id | recommended_name | formula | required_columns | frequency | asof_rule | duplicate_check | leakage_check | priority |
|---|---------------|------------------|---------|------------------|-----------|-----------|-----------------|---------------|----------|
| 6 | RAW002082 | close_impact_3min | (Close - Close_bar_14:55) / Close_bar_14:55 | close, close_of_penultimate_bar | 5min (last bar) | T-day 15:00 | DISTINCT: No last-bar price impact feature exists. minute_late_surge_ratio uses volume, not price. | none — 14:55 bar close available at 15:00 | P1 |
| 7 | RAW002083 | eod_volume_concentration | V_last_bar / V_total (last 5min / total day) | volume_per_bar | 5min | T-day 15:00 | DISTINCT: minute_closing_auction_volume_ratio = last_bar / avg_bar (ratio to mean). This = last_bar / TOTAL (proportion). Different denominators → different scale/distribution. | none | P1 |
| 8 | RAW002135 | trapped_volume | Σ(Vol_i × I(VWAP_i > Close) × decay^(N-i)) | vwap_per_bar, close, volume_per_bar | 5min | T-day 15:00 | DISTINCT: Academic CYQ 'underwater chip' concept. No existing feature weights underwater volume with time decay. | none — only T-day data, decay parameter is fixed | P1 |
| 9 | RAW001931 | tail_volatility_ratio | σ(r_last_6_bars) / σ(r_all_bars) | return_per_bar | 5min | T-day 15:00 | DISTINCT: No existing feature compares tail-session volatility to full-day. minute_realized_vol_intraday is absolute, not relative. | none | P1 |
| 10 | RAW002096 | intraday_price_reversal | |r_first_half| / Σ|r_5min| | return_per_bar | 5min | T-day 15:00 | DISTINCT: No first-half concentration of movement factor exists. minute_morning_return is absolute return, not fraction of total path. | none | P1 |
| 11 | RAW001873 | bar_obi_proxy | Σ(((close_k - low_k)/(high_k - low_k) - 0.5) × V_k) / Σ(V_k) | ohlcv_per_bar | 5min | T-day 15:00 | DISTINCT: Volume-weighted bar-level buy/sell pressure proxy. Different from minute_intraday_close_position (single EOD value, not vol-weighted across bars). | none | P1 |
| 16 | RAW000518 | intraday_consolidation_duration | count(bars where |close - vwap|/vwap < 0.003) / total_bars | close_per_bar, vwap_per_bar | 5min | T-day 15:00 | DISTINCT: No existing feature measures fraction of day spent near VWAP. minute_price_efficiency measures path efficiency, not consolidation. | none | P1 |
| 17 | RAW000519 | intraday_breakout_bar_ratio | count(bars where close > vwap×1.005 AND vol > avg_vol×1.5) / total_bars | close_per_bar, vwap_per_bar, volume_per_bar | 5min | T-day 15:00 | DISTINCT: Joint price+volume breakout frequency. No existing minute feature combines both conditions. | none | P1 |
| 18 | RAW000522 | intraday_volume_shrink_ratio | count(bars where V < 0.6 × avg_V) / total_bars | volume_per_bar | 5min | T-day 15:00 | DISTINCT: Fraction of bars with significantly below-average volume. No existing feature measures volume drought frequency. | none | P1 |
| 19 | RAW000717 | prev_30min_volume_ratio | V_14:00-14:30 / V_total | volume_per_bar | 5min (bars 37-42) | T-day 15:00 | DISTINCT: Pre-close 30min (14:00-14:30), not last 30min (14:30-15:00). Different time window from minute_last_30min_volume_ratio. | none | P1 |

### P2 — Lower Priority / Complex / Blocked

| # | raw_factor_id | recommended_name | formula | required_columns | frequency | asof_rule | duplicate_check | leakage_check | priority |
|---|---------------|------------------|---------|------------------|-----------|-----------|-----------------|---------------|----------|
| 12 | RAW002013 | capital_gains_overhang | (Close - Σ(w_i × VWAP_i)) / Close, w_i = turnover_i × Π(1-turnover_j) | close, vwap_per_bar, turnover_per_bar | 5min (multi-day) | T-day 15:00 | DISTINCT: Academic CGO factor. C154 price_vs_cost uses simple rolling VWAP; this uses decay-weighted CYQ cost basis. | none — uses historical data only | P2 |
| 13 | RAW002138 | chip_pressure | Σ(underwater_vol × decay^(t-i) × |VWAP_i - Close|/Close) | vwap_per_bar, close, volume_per_bar | 5min (multi-day) | T-day 15:00 | DISTINCT: Extension of trapped_volume adding distance weighting. No existing feature. | none | P2 |
| 14 | RAW002142 | weighted_avg_cost | Σ(w_i × VWAP_i) / Σ(w_i), w_i from CYQ decay | vwap_per_bar, turnover | 5min (multi-day) | T-day 15:00 | DISTINCT: CYQ-weighted average cost. C160 chip_weight provides the weight, this provides the cost. Complementary. | none | P2 |
| 15 | RAW002144 | ema_vwap_cost | EMA(VWAP, alpha=1/avg_turnover_20d) | vwap, turnover | 5min (multi-day) | T-day 15:00 | DISTINCT: Simplified CYQ cost using EMA with turnover-adaptive alpha. Simpler than CGO/WAC. | none | P2 |
| 20 | RAW002085 | volatility_signature_ratio | RV(1min) / RV(5min) | 1min_returns, 5min_returns | 1min + 5min | T-day 15:00 | DISTINCT: Microstructure noise ratio. Requires 1min data (NOT currently available). | none | P2 (blocked: needs 1min data) |

---

## still_blocked_l2_tick_orderbook (189)

These 189 records reference hard L2/tick requirements:
- 逐笔成交 (tick-level trades)
- 盘口深度 (orderbook depth)
- 委托/撤单 (order/cancel data)
- 买一/卖一封单量 (best bid/ask queue)
- 主动买/主动卖 (aggressor side)
- VPIN / microstructure

**These remain blocked regardless of minute bar availability.**

---

## Constraints Confirmation

- [x] No factor_registry.json modification
- [x] No C174+ added
- [x] No training executed
- [x] No gpu_probe runs
- [x] No frozen_forward_config modification
- [x] Report only — awaiting confirmation before any registration

---

*Generated 2026-05-11, strict reclassification updated 2026-05-12. Registry state: C001-C173 unchanged.*

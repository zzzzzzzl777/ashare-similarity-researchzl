# Promote 24 Pre-Registration Review (2026-05-07)

## Summary

| Disposition | Count |
|-------------|-------|
| **ready_to_register** | **5** |
| needs_data_or_formula_lock | 6 |
| reject | 13 |
| Total reviewed | 24 |

---

## ready_to_register (5)

| # | raw_factor_id | Name | Formula | Data Need | Asof | Dup Check | Engineering Path | Risk |
|---|---------------|------|---------|-----------|------|-----------|------------------|------|
| 1 | RAW001780 | theme_breadth_real | count(limit_up_stocks_in_theme) / count(all_theme_members) | sector_theme (stock_board_concept_name_em) | T-day close | No existing feature measures REAL theme-internal limit-up breadth (C059 limit_theme_breadth = same concept but blocked, C096 concept_breadth_strength uses a different formula). Verify C059/C096 are not equivalent. | stock_board_concept_name_em (free AKShare) gives limit-up stocks per concept per day; divide by ths_index_member count | C059 overlap risk — must verify formula differs |
| 2 | RAW002117 | Sign | sign(Close_t - Max(High[t-N:t-1])); +1 = breakout above prior N-day high, -1 = below | daily_ohlcv | T-day close | Existing `breakout_20` is binary (1 if close > max_high_20d, else 0). `Sign` extends to both directions (+1/-1) and parameterizable N. Distinct signal if N != 20. | Trivial: sign(close - rolling_max(high, N)) | Must fix N; if N=20 then ~equivalent to breakout_20 |
| 3 | RAW002601 | uniqueness_score | 1.0 / (same_theme_limit_up_count + 1) | limit_pool + sector_theme | T-day close | No existing feature measures theme-level scarcity of limit-ups for a stock. Different from sector_limit_up_count (which is raw count, not inverse). | From limit pool + theme mapping: count limit-ups in same theme, take reciprocal | none |
| 4 | RAW000570 | lhb_buy_sell_ratio | lhb_buy_top5_total / lhb_sell_top5_total | lhb (top_list, 805 parquets) | T-day close (LHB published same evening) | Existing: tushare_lhb_net_buy = buy-sell, tushare_lhb_net_rate = net/total. This is RATIO buy/sell (asymmetric vs net difference). Distinct. | top_list parquets: sum buy_amount top5 / sum sell_amount top5 | Sparse (~2% coverage); need _available flag |
| 5 | RAW001512 | pullback_from_high | 1 - close / max(close, lookback_window) | daily_ohlcv | T-day close | Existing: `tgb_pullback_health` is composite (recovery metric), `ma5_pullback_entry` is entry signal. This is pure drawdown depth from recent high — distinct concept. | Simple: 1 - close / rolling_max(close, N). Must fix N (20d? 60d?). | needs_formula_lock: N undefined |

---

## needs_data_or_formula_lock (6)

| # | raw_factor_id | Name | Issue | What's Missing |
|---|---------------|------|-------|----------------|
| 1 | RAW001779 | sector_change_intensity | Uses `stock_board_change_em` API (sector change/addition announcements) | Must verify: (a) AKShare `stock_board_change_em` provides historical data, not just today; (b) asof timing for "change effective date" vs "announcement date" |
| 2 | RAW000456 | board_height_score | max_board_height / historical_avg_max_board | `historical_avg_max_board` lookback window undefined. If short (20d avg) = novel; if all-time = near-constant. Must lock window. |
| 3 | RAW002981 | dragon_tiger_net_buy_ratio | LHB net buy as a ratio (similar to lhb_buy_sell_ratio) | raw_text only says "龙虎榜净买额(AKShare)" with no formula beyond "净". May be identical to existing tushare_lhb_net_buy. Needs formula differentiation. |
| 4 | RAW001742 | seat_premium_score | Historical returns of LHB seats (1/2/3/5/10/20/30 day) | Requires: (a) historical seat-level return computation from `stock_lhb_yyb_detail_em`; (b) seat identification mapping across dates; (c) complex rolling aggregation. Engineering-heavy. |
| 5 | RAW001743 | famous_seat_decay | Same API as seat_premium_score, decay of famous seat effect | Same dependency as seat_premium_score. Cannot register independently until seat infrastructure exists. |
| 6 | RAW000528 | policy_density | count(policy_events[sector] in last_N_days) / N | No policy event data source cached in project. Would need `stock_board_change_em` or external policy database. Data availability unverified. |

---

## reject (13)

| # | raw_factor_id | Name | Reason | Detail |
|---|---------------|------|--------|--------|
| 1 | RAW002830 | temp | concept_duplicate + generic_name | Formula: "涨停数/10 + ad_ratio×5 + 换手比20日均×2 - 跌停数/5 + 炸板率×0.5" = linear combo of market_limit_up_count, ad_ratio, turnover, limit_down_count, board_open_rate — ALL existing features. Name "temp" is non-descriptive. |
| 2 | RAW002968 | northbound_net_buy | data_unknown + duplicate | data_needs=unknown, asof=unknown. Even if resolved: northbound net buy is already `tushare_hk_ratio_delta_1d` (change) or would need `moneyflow_hsgt` integration. Matches C052 northbound_market_tailwind concept. |
| 3 | RAW000183 | institution_trend_buy_yin | trading_strategy | Raw text describes "机构趋势性买入阴线股" = a TRADING ACTION (buy dips that institutions are accumulating). Not a quantifiable market factor. |
| 4 | RAW000595 | avg_seal_time | exact_duplicate | = `market_real_mean_seal_time_minutes` (already in implemented features as market-level average seal time) |
| 5 | RAW000137 | anomaly_200_buysel_imbalance | needs_special_data | Requires "200% 异动" event detection + order-level buy/sell imbalance. Not daily OHLCV computable. |
| 6 | RAW000507 | signal_decay | no_event_source | Formula `exp(-0.3 × hours_since_disclosure)` requires disclosure timestamp. No announcement data cached in project. Pure decay without base signal is meaningless. |
| 7 | RAW000530 | research_surge | no_data_source | "研报数量_近30日" requires broker research report database. Not available in project. Incorrectly labeled as lhb data_need. |
| 8 | RAW001744 | seat_style_vector | ml_model_required | "席位风格向量" requires ML clustering/embedding of seat behavior patterns. Not a simple computable factor. |
| 9 | RAW001943 | Sentiment_Factor_t | no_data_source | Requires announcement-level sentiment scoring (Score_i). No NLP/sentiment infrastructure exists. |
| 10 | RAW001985 | PEAD_factor | no_data_source | SUE (Standardized Unexpected Earnings) requires earnings data + analyst estimates. Not cached (forecast_vip stopped 2025-02, not integrated). |
| 11 | RAW002274 | FAD | no_data_source | Friday Announcement Delay. Same SUE dependency as PEAD + requires announcement date classification. Not available. |
| 12 | RAW002579 | TARGET_CAR | future_variable | "被举牌前1日至后5日" cumulative abnormal return. Uses T+1 to T+5 FUTURE returns as the factor. Clear leakage. |
| 13 | RAW002934 | etf_creation_redemption | no_data_source | ETF creation/redemption data not cached in project (block_trade directory = 0 files, no ETF fund flow API integrated). data_need incorrectly labeled as "lhb". |

---

## Priority-Ordered 7 Candidate Deep Review

### 1. theme_breadth_real → **ready_to_register**
- **Formula**: real_limit_up_in_theme / total_theme_members
- **Not duplicate**: C059 `limit_theme_breadth` is blocked (needs tag parsing); C096 `concept_breadth_strength` formula unknown. This uses `stock_board_concept_name_em` API directly.
- **Engineering**: AKShare free API, T-day after close. Straightforward.
- **Risk**: Must differentiate from C142 `theme_limit_density` (count_in_theme / member_count) — verify C142 uses the same formula. If identical to C142, REJECT.

### 2. pullback_from_high → **ready_to_register** (with formula lock needed)
- **Formula**: 1 - close / rolling_max(close, N)
- **Not duplicate**: `tgb_pullback_health` is recovery composite, `ma5_pullback_entry` is binary entry signal. Pure drawdown depth is distinct.
- **Risk**: N must be locked. Recommend N=20.

### 3. Sign → **ready_to_register** (with formula lock needed)
- **Formula**: sign(close - max(high, N-day))
- **Not duplicate if N ≠ 20**: `breakout_20` exists but is binary (1/0 not +1/-1) and only upside. Sign captures both directions.
- **Engineering**: Trivial rolling max computation.
- **Risk**: Must set N ≠ 20 to avoid redundancy with breakout_20. Recommend N=10 or N=5.

### 4. board_height_score → **needs_formula_lock**
- **Formula**: max_board_height / historical_avg(max_board_height, N)
- **Partial duplicate**: `tgb_board_height_vs_max` already exists (board_height / market_max). This divides market_max_board_height by its own history — related but not identical.
- **Risk**: If N is all-time, denominator is near-constant → useless. Must lock N (recommend 60d).

### 5. avg_seal_time → **REJECT**
- **Duplicate**: `market_real_mean_seal_time_minutes` already implemented.

### 6. uniqueness_score → **ready_to_register**
- **Formula**: 1 / (same_theme_limit_count + 1)
- **Not duplicate**: No existing feature captures theme-level scarcity. `sector_limit_up_count` is raw count per sector, not per-stock inverse.
- **Engineering**: From limit pool, group by theme, count per theme, map back to stock, invert.

### 7. lhb_buy_sell_ratio → **ready_to_register**
- **Formula**: sum(buy_top5) / sum(sell_top5)
- **Not duplicate**: Existing LHB features are net amount and net rate. Ratio (buy/sell) has different distribution properties (asymmetric, unbounded above).
- **Engineering**: top_list parquets already cached (805 files). Simple aggregation.
- **Risk**: Sparse (~2% daily coverage). Must use _available flag.

---

## Constraints Confirmation

- [x] No factor_registry.json modification
- [x] No C174+ added
- [x] No training executed
- [x] No gpu_probe runs
- [x] No frozen_forward_config modification

---

## Critical Note on C142 theme_limit_density

C142 (already registered) is defined as: `limit_count_in_theme / theme_member_count`

theme_breadth_real candidate formula is: `real_limit_up_in_theme / total_theme_members`

**These may be identical**. Before registering theme_breadth_real:
- Verify C142 uses OHLCV-proxy limit detection (close==high_limit) vs real API pool
- If C142 also uses real API data → theme_breadth_real is DUPLICATE → reject
- If C142 uses proxy → theme_breadth_real provides "real pool" version → distinct

---

*Generated 2026-05-07. Registry state: C001-C173. No modifications made.*

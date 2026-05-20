# Raw Review 500 — Third Pass Report (2026-05-06)

## Executive Summary

| Stage | Count | Notes |
|-------|-------|-------|
| Input (raw queue) | 429 | All: free_data=True, leakage=low, needs_level2=False, not in C001-C152 |
| Second-pass promote | 289 | **Too permissive** — many false positives |
| Second-pass reject | 103 | L2/strategy/NLP/intra-queue duplicates |
| Second-pass defer | 37 | No quantifiable operation / vague / cross-market |
| **Third-pass promote** | **39** | After hard blacklist + field aliases + concept dups + formula check |
| Third-pass reject (from 289) | 120 | Added: special data / minute bars / expanded concept dups |
| Third-pass defer (from 289) | 130 | Mostly: no real formula in raw_text (117) |
| **Final manual promote** | **21** | After manual review of 39 survivors (see below) |
| Final manual reject (from 39) | 13 | L2/options/minute/duplicate/ML |
| Final manual defer (from 39) | 5 | Underdefined or complex |

---

## Why Second-Pass 289 Is Not Trustworthy

The automated second pass failed to catch:
1. **Field aliases disguised as formulas** (13): `current_gain = (price-pre_close)/pre_close` = pct_change; `vol_ratio = vol/avg_5d` = volume_ratio already exists
2. **L2/tick data mislabeled as daily** (11): `sell_cancel_rate` uses `stock_l2.sell_cancel_amount`; `drop_volume` references "5分钟量能"
3. **Trading rules masquerading as factors** (16): `chase_only_when_market_up`, `board_keep_break_rule` "连板晋级=留，断板=全走"
4. **Concept duplicates not caught by name** (28): `limitup_premium` = `prev_limit_up_premium`; `seal_ratio_score` = `seal_money_to_float_mv`
5. **No real formula** (117): raw_text is just a title like "Factor 429: `seal_time_factor` - 封板时间因子" with no definition
6. **Cross-market / special data** (18): VIX, HSI, margin data, insider trading, options PCR

---

## Hard Blacklist Applied (User-Specified)

These 18 concepts were unconditionally rejected per prior decisions:

| Name | Reason |
|------|--------|
| limit_up_count_market | = market_limit_up_count (stable feature) |
| today_limit_up | = is_limit_up (close==high_limit) |
| closed_limit_up | = is_limit_up |
| final_close | = is_limit_up |
| peak_price | Reference value, not factor |
| Z_t | Generic "macro state variable" label |
| limit_up_with_volume | Trivial interaction of existing features |
| sector_batch_limit_effect | = sector_limit_up_count |
| second_board_confirm_leader | = is_second_board / board_count==2 |
| opening_seal_speed | = seal_time |
| asking_chase_half_position | Position management, not factor |
| name_geography_mysticism | NLP / text |
| solo_stock_direction_hint | NLP / text |
| position_stock_signal | NLP / text |
| echelon_position_battle | Requires intraday + subjective tier |
| node_second_board_fault_tolerance | Trading rule "节点做二板" |
| board_keep_break_rule | Trading rule "连板=留，断板=走" |
| chip_reflexivity | Philosophical concept, not quantifiable |

---

## Third-Pass Rejection Reasons (120 total from 289)

| Reason | Count | Examples |
|--------|-------|----------|
| concept_duplicate_expanded | 28 | limitup_premium→prev_limit_up_premium, seal_ratio→seal_money_to_float_mv, total_amount→amount |
| vague_categorical | 17 | sector_first_board_attr (outputs categories), Image_t (needs CNN), Buy_Signal (trading signal) |
| trading_strategy_expanded | 16 | chase_only_when_market_up, lurking_capital_trap, ipo_open_board_entry |
| field_alias | 13 | current_price=close, current_gain=pct_change, daily_volume=amount, gap=open/prev-1 |
| hard_blacklist | 11 | User-specified prior rejects |
| l2_disguised_as_daily | 11 | sell_cancel_rate, buy_cancel_rate, attack_volume, quant_fake_seal_detection |
| needs_special_data | 11 | MBR (margin), NB_Flow (northbound), INSIDER_NET (insider), Z_CN (financials) |
| future_variable | 7 | next_day_volume, trough_price (min after limit), volume_decay (after breakout) |
| word_overlap_implemented | 3 | Substring match with implemented features |
| needs_minute_bars | 3 | max_5min_volume, down_vol, late_chase_volume |

---

## Third-Pass Deferrals (130 total)

| Reason | Count | Notes |
|--------|-------|-------|
| no_real_formula | 117 | raw_text is just a title or < 20 chars with no formula operators |
| underdefined_variables | 7 | References fields not in standard data (vacuum_ratio, breakout_gain, etc) |
| cross_market_excluded | 5 | eu_close_return, VIX_close, VIX_change, HSI_close, HSI_afternoon_session |
| categorical_text | 1 | strong_pool_reason (string from API) |

---

## Final Manual Review of 39 Third-Pass Survivors

### PROMOTE (21 candidates)

| # | raw_factor_id | Name | Family | Formula | Data Need | Why Not Duplicate | Implementation Hint |
|---|---------------|------|--------|---------|-----------|-------------------|---------------------|
| 1 | RAW000843 | nuclear_ratio | board_structure | count(stocks in both today's and yesterday's limit pool) / count(yesterday's pool) | limit_pool | No existing feature tracks "repeat limit-up ratio" | Compare consecutive day limit pool membership |
| 2 | RAW000886 | price_vs_cost | price_structure | (close - turnover_weighted_avg_price_Nd) / turnover_weighted_avg_price_Nd | daily_ohlcv | Distinct from simple MA or close/high ratio | Rolling VWAP-like calc: Σ(amount)/Σ(volume) over N days |
| 3 | RAW001075 | cap_ratio | sector_structure | stock.float_mv / max(sector_leader.float_mv, 1) | daily_ohlcv + sector | No existing feature normalizes cap by sector leader cap | Identify sector leader (highest board or highest return), divide |
| 4 | RAW001830 | abnormal_3d_deviation | momentum | sum(stock_pct_change, 3d) - sum(index_pct_change, 3d) | daily_ohlcv | No short-window (3d) excess return feature exists | 3-day cumulative return minus benchmark |
| 5 | RAW002021 | VOL_GAIN | volume_structure | MA(turnover on up-days) / MA(turnover on down-days) | daily_ohlcv | No conditional turnover split by return direction exists | Separate daily turnover into gain/loss days, compute ratio |
| 6 | RAW002044 | INV_t | volume_structure | -Σ(sign(ret_i) × volume_i) / Σ(volume_i), 20d | daily_ohlcv | Novel academic factor (inventory), not in stable features | Sign-weighted volume over 20-day window |
| 7 | RAW002132 | ASR | price_structure | (P_90_percentile - P_10_percentile) / Close | daily_ohlcv | No price range percentile factor exists | Rolling 60d window, compute 90th/10th percentile of closes |
| 8 | RAW002141 | w_i (chip_weight) | price_structure | Turnover_i × Π(1 - Turnover_j) for j > i | daily_ohlcv | CYQ-foundation formula, not in current features | Recursive daily weight: each day's turnover decayed by subsequent turnovers |
| 9 | RAW002236 | ILLIQ_classic | liquidity | (1/D) × Σ|return_d| / volume_d (Amihud) | daily_ohlcv | Classic illiquidity measure, not in stable/research features | Monthly: avg of daily |return|/volume |
| 10 | RAW002242 | ATO | volume_structure | (turnover_20d - turnover_120d) / std(turnover_120d) | daily_ohlcv | Abnormal turnover z-score vs long-term, novel | Short-term vs long-term turnover deviation |
| 11 | RAW002245 | TAM | momentum | MOM_12_1 - β × Turnover (turnover-adjusted momentum) | daily_ohlcv | No turnover-adjusted momentum exists | 12-1 month momentum residualized against turnover |
| 12 | RAW002610 | new_leader_emerge | market_cycle | (stock.board_height == 2) AND (stock.seal_time_rank == 1) | limit_pool | Distinct from C150 old_leader_decay (emergence vs decay) | Find 2-board stock with earliest seal time = new leader signal |
| 13 | RAW002621 | need_second_seal | board_quality | (high - low) / prev_close > 0.12 (transition amplitude) | daily_ohlcv + limit_pool | No intraday amplitude threshold factor for limit stocks | Daily high-low range as % of prev_close, filtered to limit stocks |
| 14 | RAW002647 | late_seal_ratio | board_structure | count(seal_time > 14:00) / total_limit_up_count | limit_pool | Market-level ratio (not per-stock seal_time) | Aggregate seal_time from limit pool API, compute ratio |
| 15 | RAW002648 | early_seal_ratio | board_structure | count(seal_time < 10:30) / total_limit_up_count | limit_pool | Complement of late_seal_ratio, different interpretation | Same as above with < 10:30 threshold |
| 16 | RAW001269 | vol_premium | volume_structure | stock_volume / sector_avg_volume - 1 | daily_ohlcv + sector | No sector-relative volume measure exists | Stock vol / mean(vol, same_sector_stocks) |
| 17 | RAW001424 | max_theme_weight | sector_structure | max(weight across all themes stock belongs to) | sector_theme | No theme membership weight factor exists | From ths_index_member, compute stock's weight in each theme |
| 18 | RAW001425 | hhi (theme_concentration) | sector_structure | sum(theme_weight_i^2) for stock's themes | sector_theme | No theme concentration measure exists | HHI of stock's theme memberships |
| 19 | RAW001720 | new_high_strength | board_structure | From stock_zt_pool_strong_em API: strength metric | limit_pool | Free AKShare API, not in current features | Direct from stock_zt_pool_strong_em free API |
| 20 | RAW001721 | recent_limit_frequency | board_structure | From stock_zt_pool_strong_em API: recent limit-up frequency | limit_pool | Free AKShare API, not in current features | Direct from stock_zt_pool_strong_em free API |
| 21 | RAW001753 | true_limit_up_ratio | market_breadth | From stock_market_activity_legu API: real limit-up ratio | limit_pool | Free AKShare API, market-level activity metric | Direct from stock_market_activity_legu free API |

---

### REJECT from 39 Survivors (13 candidates)

| # | Name | raw_factor_id | Reason |
|---|------|---------------|--------|
| 7 | PCR_volume | RAW001990 | Needs options data (Put/Call volume) — not available |
| 8 | CGO_simple | RAW002012 | Concept duplicate of price_vs_cost (same: price vs weighted avg cost) |
| 9 | Attention | RAW002016 | Needs BSI + NewsShock = external NLP data |
| 12 | r_last | RAW002067 | Needs 13:00 price = minute bars |
| 13 | r_overnight | RAW002071 | = open/prev_close - 1 = likely duplicate of existing open_gap features |
| 14 | r_night | RAW002074 | Same formula as r_overnight (duplicate within queue) |
| 15 | Close_Impact | RAW002082 | Needs 14:57 price = minute bars |
| 17 | Image_t | RAW002115 | Needs CNN model for candlestick images — ML, not market data |
| 22 | Cost_Dev | RAW002143 | Concept duplicate of price_vs_cost |
| 23 | Net_Buy_Ratio | RAW002151 | Needs buy/sell separation = Level 2 |
| 24 | BT_Discount | RAW002154 | Needs block trade data (大宗交易), not daily OHLCV |
| 25 | RISM_abnormal | RAW002189 | Needs "PostVolume" + "Sentiment" = external data |
| 33 | resist_ratio | RAW001063 | = stock_drop / sector_drop = C151 anti_drop_strength (exact duplicate) |

---

### DEFER from 39 Survivors (5 candidates)

| # | Name | raw_factor_id | Missing Information |
|---|------|---------------|---------------------|
| 5 | Crowding_i | RAW001922 | Needs long/short portfolio decomposition (academic construct) |
| 6 | Sub_New_Factor | RAW001961 | Composite with undefined weights w₁...w₄ |
| 16 | VolDistFactor | RAW002107 | "VolAnomaly" and "CloseSurge" undefined |
| 18 | Breakout_Factor | RAW002116 | "Sign", "Strength", "Volume_Confirm" all undefined |
| 19 | KAMA_t | RAW002129 | Standard TA indicator, may overlap with existing momentum features |

---

## Combined 429-Candidate Final Disposition

| Disposition | Count | % |
|-------------|-------|---|
| **Final Promote** | **21** | 4.9% |
| Reject (all passes combined) | 253 | 59.0% |
| Defer (all passes combined) | 155 | 36.1% |

### Rejection breakdown (253 total across all passes):

| Category | Count |
|----------|-------|
| Needs L2 / orderbook / tick | 39 |
| Concept/name duplicate of existing | 55 |
| Trading strategy / position / action | 30 |
| Field alias / trivial rename | 13 |
| Hard blacklist (prior reject) | 11 |
| Needs special data (margin/insider/options/block) | 11 |
| Vague / categorical / ML model | 17 |
| Future variable | 7 |
| NLP / text required | 4 |
| Intra-queue duplicate | 36 |
| Sector feature overlap | 2 |
| Needs minute bars | 6 |
| Queue-final manual reject | 13 |
| Other | 9 |

---

## Corrected "Mis-Promote" List

These were in the second-pass 289 but should NEVER have been promoted:

| Name | What It Actually Is | Correct Disposition |
|------|---------------------|---------------------|
| limit_up_count_market | = market_limit_up_count (existing stable feature) | REJECT: exact duplicate |
| today_limit_up | = close==high_limit (existing is_limit_up) | REJECT: trivial existing |
| closed_limit_up | Same as today_limit_up | REJECT: trivial existing |
| final_close | Same as today_limit_up | REJECT: trivial existing |
| peak_price | = stock.high_limit_day_close (reference value) | REJECT: not a factor |
| current_gain | = (price-pre_close)/pre_close = pct_change | REJECT: field alias |
| vol_ratio | = today_volume/avg_5d = volume_ratio | REJECT: field alias |
| daily_volume | Raw volume column | REJECT: raw field |
| sell_cancel_rate | Uses stock_l2.sell_cancel_amount | REJECT: Level 2 |
| buy_cancel_rate | Uses stock_l2.buy_cancel_amount | REJECT: Level 2 |
| chase_only_when_market_up | "追涨只在大盘涨时" = trading rule | REJECT: strategy |
| board_keep_break_rule | "连板=留,断板=走" = trading rule | REJECT: strategy |
| Image_t | render_candlestick → CNN | REJECT: needs ML model |
| next_day_volume | Future variable | REJECT: leakage |

---

## Registry Write Status

- **Written**: 21 candidates promoted to `factor_registry.json` as batch `candidates_20260506_raw_review_500`
- **IDs assigned**: C153-C173 (sequential, no gaps)
- **All entries**: `training_status="not_trained"`, `lockbox_role="research_candidate"`
- **Not trained**: No gpu_probe run, no model evaluation, no passed/final_unseen claims
- **C001-C152 unchanged**

---

## Constraints Confirmation

- [x] No training executed
- [x] No gpu_probe runs
- [x] No frozen_forward_config modification
- [x] factor_registry.json updated: C153-C173 added (all not_trained/research_candidate)
- [x] No passed/final_unseen/frozen claims
- [x] C001-C152 unchanged

---

*Generated 2026-05-06, updated after registry write. Source: _assessment_429_strict.json (289 second-pass promotes) → 39 third-pass → 21 manual final.*

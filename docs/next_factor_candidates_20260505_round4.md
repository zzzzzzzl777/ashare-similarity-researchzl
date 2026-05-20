# Next Factor Candidates -- 2026-05-05 Round 4

> Round: fourth batch, targeted gap-fill for uncovered dimensions
> Goal: Fill genuinely new dimensions not covered by C001-C102
> Constraint: no training, no gpu_probe.py changes, no frozen_forward_config changes
> Data-first filter: only candidates using verified cached data
> Existing duplicates checked against: C001-C102 + GPU_PROBE_STABLE_FEATURES + TUSHARE_FACTOR_COLUMNS

## Focus: New Dimensions Only

This round explicitly avoids rehashing existing directions. After reviewing all 102 existing candidates, the following dimensions remain genuinely uncovered:

1. **Calendar/Event gates** — day_of_week_sin/cos exist but no holiday proximity, month-end, or earnings window features
2. **Style rotation regime** — no large/small-cap relative strength regime feature
3. **Volatility regime** — no volatility state transition or vol clustering feature
4. **Volume structure** — no consecutive shrink/expand pattern detection
5. **Multi-source flow divergence** — north/domestic/margin never combined in one divergence signal
6. **Risk/loss filter** — no losing-money effect or market retreat detection
7. **Chip loosening** — winner_rate drop + volume spike not captured (C057 is raw delta, C073 is trapped recovery)

## Duplicates Checked and Removed

- 月末效应 raw dummy → day_of_week_sin/cos + month_end_3 already in expanded (Category A features)
- 成交量z-score → volume_z_20 already in expanded
- 连板涨幅 → close to C094 consecutive board height
- 热度×筹码 → close to C092 winner_rate × flow
- 大盘涨跌家数 → C089 market_breadth_thrust already covers advance/decline
- 炸板率 → C098 market_broken_board_fear already covers (z-scored)

---

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 8 | Data cached, formula clear, genuinely new dimension |
| P1 | 5 | Strong logic, needs additional engineering or moderate overlap concern |
| P2 | 2 | Sparse, conditional, or leakage-adjacent requiring careful handling |
| blocked | 0 | — |
| **Total** | **15** | (fewer than prior rounds — intentionally lean to avoid padding) |

---

## P0 Candidates (8)

### C103: volume_shrink_streak

| Field | Value |
|-------|-------|
| factor_id | C103 |
| name | Volume Shrink Streak |
| family | volume_structure |
| source_type | taoguba |
| source_ref | 缩量战法 "连续缩量到极致后突然放量=变盘信号" |
| raw_idea | Count of consecutive days with volume below prior day — prolonged shrinkage precedes breakout |
| computable_definition | `sum(volume[T-i] < volume[T-i-1] for i in 0..9) ` (count of shrink days in last 10) |
| data_need | daily OHLCV (volume), 10-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | volume_z_20 (z-score level), volume_chg_1 (single-day change) |
| duplicate_check | volume_z is LEVEL; volume_chg is 1-day pct change. This is STREAK/PATTERN — consecutive shrinkage structure. No existing feature captures this. |
| engineering_status | candidate_ready |
| priority | P0 |

### C104: volume_expansion_breakout

| Field | Value |
|-------|-------|
| factor_id | C104 |
| name | Volume Expansion Breakout |
| family | volume_structure |
| source_type | taoguba |
| source_ref | 放量突破 "今日量 > 5日均量 × 2 且价格创新高 = 有效突破" |
| raw_idea | Volume expanding 2x above recent average while price at 5-day high = confirmed breakout with participation |
| computable_definition | `(volume / mean(volume, 5) > 2) * (close >= max(close, 5))` as float: `min(volume / mean(volume,5), 5) * (close >= rolling_max(close, 5))` |
| data_need | daily OHLCV, 5-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% (but ~10-15% of stocks meet condition on any day) |
| related_existing_features | volume_ratio (tushare, single-day), dist_high_5/20 (distance from high) |
| duplicate_check | volume_ratio is single-day relative; dist_high is distance from high alone. This is volume×price_high INTERACTION confirming breakout. New composite. |
| engineering_status | candidate_ready |
| priority | P0 |

### C105: realized_volatility_regime

| Field | Value |
|-------|-------|
| factor_id | C105 |
| name | Realized Volatility Regime |
| family | volatility_regime |
| source_type | github_paper |
| source_ref | Volatility clustering; GARCH regime identification for short-horizon |
| raw_idea | Current 5-day realized vol relative to 20-day vol — high ratio = expanding vol regime, low = calm |
| computable_definition | `std(ret_1d, 5) / (std(ret_1d, 20) + eps)` (vol ratio: >1 = expanding, <1 = contracting) |
| data_need | daily OHLCV (returns), 20-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | atr_14_pct (ATR level), intraday_volatility (single-day from 5m bars) |
| duplicate_check | ATR is absolute level; intraday_vol is single-day. This is vol REGIME RATIO (short/long). Captures whether vol is expanding or contracting. New dimension. |
| engineering_status | candidate_ready |
| priority | P0 |

### C106: style_rotation_spread

| Field | Value |
|-------|-------|
| factor_id | C106 |
| name | Style Rotation Spread (Large vs Small) |
| family | style_regime |
| source_type | github_paper |
| source_ref | Size factor rotation; large-cap vs small-cap relative momentum in A-shares |
| raw_idea | 5-day relative return of CSI300 vs CSI1000 — positive = large-cap leading, negative = small-cap leading |
| computable_definition | `ret_5d(CSI300_index) - ret_5d(CSI1000_index)` broadcast as market-level feature |
| data_need | index_dailybasic (000300.SH, 000852.SH) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | 100% (market broadcast) |
| related_existing_features | C078 (index return z-score, single index), market_emotion_score |
| duplicate_check | C078 is single-index momentum. This is SPREAD between two indices capturing style rotation. No existing feature covers relative large/small performance. |
| engineering_status | candidate_ready |
| priority | P0 |

### C107: pre_holiday_proximity

| Field | Value |
|-------|-------|
| factor_id | C107 |
| name | Pre-Holiday Proximity |
| family | calendar_event |
| source_type | github_paper |
| source_ref | Holiday effect in A-shares; documented pre-holiday risk aversion and post-holiday momentum |
| raw_idea | Trading days until next market closure (holiday/weekend) — last 1-2 days before long holiday have documented behavioral shift |
| computable_definition | `exp(-days_to_next_holiday / 3)` where days_to_next_holiday counted from market calendar (0 = holiday eve) |
| data_need | A-share market calendar (deterministic, no external data needed) |
| asof_rule | T-day (deterministic from calendar) |
| leakage_risk | **none** — holidays are pre-announced; this is calendar-based, not forward-looking |
| coverage_estimate | 100% (market broadcast, deterministic) |
| related_existing_features | month_end_3 (month-end flag), day_of_week_sin/cos (weekday cycle) |
| duplicate_check | month_end is month boundary. day_of_week is weekly cycle. This is HOLIDAY proximity (Spring Festival, National Day, etc). Different calendar dimension — long holidays ≠ weekends ≠ month-end. |
| engineering_status | candidate_ready |
| priority | P0 |

### C108: northbound_vs_domestic_flow_divergence

| Field | Value |
|-------|-------|
| factor_id | C108 |
| name | Northbound vs Domestic Flow Divergence |
| family | multi_source_divergence |
| source_type | github_paper |
| source_ref | Smart vs dumb money divergence; foreign vs domestic institutional disagreement |
| raw_idea | When northbound buying but domestic main force selling (or vice versa) — captures institutional disagreement across markets |
| computable_definition | `sign(hk_ratio_delta_1d) * (-sign(net_mf_amount))` at stock level (+1 = diverging, -1 = aligned) |
| data_need | hk_hold + tushare moneyflow |
| asof_rule | T-day close (both published T+1 morning) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~40% (limited by hk_hold coverage: HK-connect stocks only) |
| related_existing_features | C054 (north × price direction), C091 (hot × flow direction) |
| duplicate_check | C054 is north × PRICE; C091 is hot × FLOW. This is NORTH × DOMESTIC_FLOW. Different source pair entirely — institutional cross-market disagreement. |
| engineering_status | candidate_ready |
| priority | P0 |

### C109: losing_money_effect_regime

| Field | Value |
|-------|-------|
| factor_id | C109 |
| name | Losing Money Effect Regime |
| family | risk_filter |
| source_type | taoguba |
| source_ref | 打板情绪 "昨日涨停股今日平均亏损 > 2% = 亏钱效应, 不打板" |
| raw_idea | Average next-day return of previous day's limit-up stocks — negative = hostile losing-money regime |
| computable_definition | `mean(ret_1d[T] for stocks in limit_up_pool[T-1])` broadcast as market-level feature |
| data_need | limit_list_d (T-1 limit-up pool) + daily OHLCV (T-day returns for those stocks) |
| asof_rule | T-day close (uses T-1 limit pool + T-day returns, both known) |
| leakage_risk | none — uses T-1 pool's T-day return, fully realized at T-day close |
| coverage_estimate | 100% (market broadcast) |
| related_existing_features | C090 (limit up/down ratio), C098 (broken board fear), prev_limit_up_premium |
| duplicate_check | C090 is ratio of limit counts. C098 is broken board rate. prev_limit_up_premium exists but is individual stock's own premium. This is MARKET-LEVEL average premium of yesterday's limit-up pool — direct "赚钱/亏钱效应" measure. |
| engineering_status | candidate_ready |
| priority | P0 |

### C110: chip_loosening_signal

| Field | Value |
|-------|-------|
| factor_id | C110 |
| name | Chip Loosening Signal |
| family | cyq_risk |
| source_type | taoguba |
| source_ref | 筹码分析 "获利盘下降+放量 = 主力出货筹码松动" |
| raw_idea | Winner rate decreasing while volume expanding = profitable holders distributing, chips loosening |
| computable_definition | `max(-winner_rate_delta_5d, 0) * max(volume / mean(volume, 5) - 1, 0)` (negative chip change × positive volume surprise) |
| data_need | cyq_perf (winner_rate) + daily OHLCV (volume) |
| asof_rule | T-day close (cyq published T+1) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~80% |
| related_existing_features | C057 (winner_rate_delta alone), C073 (trapped recovery), C092 (winner × flow alignment) |
| duplicate_check | C057 is raw delta (unsigned). C073 is positive delta from low base. C092 is delta × flow direction. This is NEGATIVE delta × VOLUME expansion — specifically captures distribution/loosening. Different: bearish chip signal, not bullish. |
| engineering_status | candidate_ready |
| priority | P0 |

---

## P1 Candidates (5)

### C111: margin_vs_northbound_divergence

| Field | Value |
|-------|-------|
| factor_id | C111 |
| name | Margin vs Northbound Flow Divergence |
| family | multi_source_divergence |
| source_type | github_paper |
| source_ref | Leveraged retail (margin) vs smart money (northbound) disagreement |
| raw_idea | When margin buyers are adding but northbound is selling = retail euphoria without foreign confirmation |
| computable_definition | `sign(rzye_delta_pct) * (-sign(hk_ratio_delta_1d))` (+1 = diverging, -1 = aligned) |
| data_need | margin_detail + hk_hold |
| asof_rule | T-day close (both published T+1) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~35% (intersection of margin-eligible ~70% and HK-connect ~50%) |
| related_existing_features | C095 (margin × flow alignment), C108 (north × domestic flow divergence) |
| duplicate_check | C095 is margin × moneyflow. C108 is north × domestic. This is MARGIN × NORTH directly. Third combination in the three-way. Low coverage limits utility. |
| engineering_status | candidate |
| priority | P1 |

### C112: consecutive_narrow_range

| Field | Value |
|-------|-------|
| factor_id | C112 |
| name | Consecutive Narrow Range Days |
| family | volatility_regime |
| source_type | github_paper |
| source_ref | NR4/NR7 pattern; narrow range precedes expansion (volatility breakout) |
| raw_idea | Count of consecutive days where daily range is below its 20-day average — compression precedes directional move |
| computable_definition | `sum(range_pct[T-i] < mean(range_pct, 20) for i in 0..6)` (narrow days in last 7) |
| data_need | daily OHLCV (range_pct), 20+7 day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | C103 (volume shrink streak), range_pct (single-day level), atr_14_pct (ATR level) |
| duplicate_check | C103 is volume shrink pattern. range_pct/ATR are levels. This is RANGE compression STREAK. Similar structural concept as C103 but for range, not volume. Related but different market dimension (price compression vs volume compression). |
| engineering_status | candidate |
| priority | P1 |

### C113: tail_session_escape_pressure

| Field | Value |
|-------|-------|
| factor_id | C113 |
| name | Tail Session Escape Pressure |
| family | risk_filter |
| source_type | social_live |
| source_ref | 东财实盘 "尾盘急跌=机构抢跑，明日大概率低开" |
| raw_idea | Large negative return in last 30 min relative to full-day range = institutional escape before close |
| computable_definition | `min(last_30min_return, 0) / (range_pct + eps)` (negative, normalized by daily range; more negative = stronger escape) |
| data_need | stk_mins_5 (last_30min_return) + daily range_pct |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | C049 (tail_push_strength, positive tail); last_30min_return (raw) |
| duplicate_check | C049 captures POSITIVE tail push. last_30min_return is raw (unsigned). This specifically captures NEGATIVE tail normalized by range — the escape/dump signal. Complementary to C049 (mirror image). |
| engineering_status | candidate |
| priority | P1 |

### C114: earning_season_proximity

| Field | Value |
|-------|-------|
| factor_id | C114 |
| name | Earnings Season Proximity |
| family | calendar_event |
| source_type | github_paper |
| source_ref | Earnings announcement drift; A-share mandatory disclosure windows (Jan, Apr, Jul, Oct) |
| raw_idea | Distance to next mandatory earnings disclosure month — stocks behave differently approaching/exiting earnings season |
| computable_definition | `exp(-days_to_next_earnings_month / 15)` where earnings_months = {1, 4, 7, 10} for A-shares |
| data_need | calendar only (deterministic from month) |
| asof_rule | T-day (deterministic) |
| leakage_risk | **none** — A-share disclosure windows are fixed by regulation (annual: Jan-Apr, semi: Jul-Aug, quarterly: Apr+Oct) |
| coverage_estimate | 100% (market broadcast, deterministic) |
| related_existing_features | C107 (holiday proximity), month_start_3, month_end_3 |
| duplicate_check | C107 is holiday. month_start/end is generic month boundary. This is EARNINGS SEASON specifically. Different calendar event with different behavioral driver (uncertainty around disclosure). |
| engineering_status | candidate |
| priority | P1 |

### C115: vol_of_vol_regime

| Field | Value |
|-------|-------|
| factor_id | C115 |
| name | Volatility-of-Volatility Regime |
| family | volatility_regime |
| source_type | github_paper |
| source_ref | Vol-of-vol as higher-order risk; instability of volatility signals regime transition |
| raw_idea | Standard deviation of daily realized vol over 10 days — high vol-of-vol = unstable regime, low = stable |
| computable_definition | `std(abs(ret_1d), window=5, rolling over 10 days)` i.e. std of 5-day rolling absolute returns, computed over 10-day window |
| data_need | daily OHLCV (returns), 15-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | C105 (vol ratio short/long), atr_14_pct (ATR level) |
| duplicate_check | C105 is vol short/long ratio (level comparison). ATR is vol level. This is SECOND-ORDER volatility — volatility of volatility. Captures instability/transition, not level or ratio. |
| engineering_status | candidate |
| priority | P1 |

---

## P2 Candidates (2)

### C116: post_holiday_momentum_gate

| Field | Value |
|-------|-------|
| factor_id | C116 |
| name | Post-Holiday Momentum Gate |
| family | calendar_event |
| source_type | taoguba |
| source_ref | 节后效应 "长假后第一天市场方向=节后一周趋势" |
| raw_idea | First trading day after long holiday (>= 3 days off) — binary flag that gates different behavior |
| computable_definition | `(days_since_last_trading > 3) * 1.0` binary flag for post-long-holiday first day |
| data_need | A-share market calendar |
| asof_rule | T-day (deterministic) |
| leakage_risk | none |
| coverage_estimate | 100% (but only fires ~10-15 days/year) |
| related_existing_features | C107 (pre-holiday proximity) |
| duplicate_check | C107 is PRE-holiday. This is POST-holiday. Different timing. Very sparse (~10 days/year). May not provide enough variance for stable_tail to select. |
| engineering_status | needs_validation |
| priority | P2 |

### C117: market_flow_retreat_speed

| Field | Value |
|-------|-------|
| factor_id | C117 |
| name | Market Flow Retreat Speed |
| family | risk_filter |
| source_type | social_live |
| source_ref | 资金撤退速度 "全市场净流出加速=系统性风险来临" |
| raw_idea | Rate of change in market-level net outflow — accelerating outflow = systemic retreat |
| computable_definition | `(market_net_mf[T] - market_net_mf[T-3]) / (abs(mean(market_net_mf, 20)) + eps)` broadcast |
| data_need | tushare moneyflow (aggregated across all stocks), 20-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | 100% (market broadcast) |
| related_existing_features | C074 (market flow regime z-score level), C089 (breadth thrust) |
| duplicate_check | C074 is flow LEVEL (z-score of aggregate flow). This is flow ACCELERATION (3-day change in flow). Related but different: level vs rate-of-change. Moderate overlap concern with C074. |
| engineering_status | needs_validation |
| priority | P2 |

---

## Engineering Readiness Summary

| Status | IDs | Count |
|--------|-----|-------|
| candidate_ready | C103-C110 | 8 |
| candidate (needs minor engineering) | C111-C115 | 5 |
| needs_validation | C116-C117 | 2 |

## Implementation Priority: Top 8 (recommended for training framework)

| Rank | ID | Name | Family | Coverage | Why First |
|------|-----|------|--------|----------|-----------|
| 1 | C105 | realized_volatility_regime | volatility_regime | ~99% | Vol expansion/contraction ratio — no existing vol regime feature |
| 2 | C103 | volume_shrink_streak | volume_structure | ~99% | Consecutive shrinkage pattern — precedes breakout; pure OHLCV, no external data |
| 3 | C109 | losing_money_effect_regime | risk_filter | 100% | 亏钱效应 = direct board-play regime filter; complements C090/C098 |
| 4 | C106 | style_rotation_spread | style_regime | 100% | Large/small-cap rotation; entirely new dimension from index spread |
| 5 | C107 | pre_holiday_proximity | calendar_event | 100% | Holiday proximity gate; deterministic, zero data dependency |
| 6 | C110 | chip_loosening_signal | cyq_risk | ~80% | 筹码松动 (distribution signal); bearish complement to C056/C092 |
| 7 | C104 | volume_expansion_breakout | volume_structure | ~99% | 放量突破 — volume × price-high interaction; classic breakout confirm |
| 8 | C108 | northbound_vs_domestic_divergence | multi_source_divergence | ~40% | Foreign vs domestic disagreement; unique cross-market signal |

---

## Why Only 15 Candidates This Round

After reviewing C001-C102, most remaining ideas either:
- Overlap with existing candidates under different names (e.g., "volume surge relative to 10d" ≈ C063/C104)
- Require data sources not cached (e.g., Level-2 order book, tick-level data)
- Are minor parameter variations of existing factors (e.g., "3d" vs "5d" windows)

Rather than pad to 20 with marginal candidates, this round captures the 15 genuinely new dimensions. The remaining whitespace is mostly:
- Intraday microstructure requiring tick data (blocked)
- Cross-asset signals (bond/commodity → equity, not cached)
- NLP-derived factors from news/announcements (requires text pipeline)

---

## Constraints Confirmation

- [x] No training executed
- [x] No gpu_probe.py changes
- [x] No frozen_forward_config changes
- [x] No passed/final_unseen/final_accepted claims
- [x] All candidates use verified cached data or deterministic calendar
- [x] Duplicate check against C001-C102 + all existing features
- [x] Intentionally lean (15 not 20) to avoid padding with redundant ideas

---

*Factor search round 4, 2026-05-05. 15 new candidates (C103-C117). No claims of passed/final_unseen/final_accepted.*

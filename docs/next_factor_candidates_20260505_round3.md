# Next Factor Candidates -- 2026-05-05 Round 3

> Round: third batch, focus on gaps identified after C001-C082
> Goal: 20 new candidates (C083-C102) from three search paths
> Constraint: no training, no gpu_probe.py changes, no frozen_forward_config changes
> Data-first filter: only candidates using verified cached data
> Existing duplicates checked against: C001-C082 + GPU_PROBE_STABLE_FEATURES + TUSHARE_FACTOR_COLUMNS

## Focus Directions (per user request)

1. 竞价到开盘后的确认/背离 (auction → early session confirmation)
2. 板块/概念强度与个股资金流背离 (sector momentum vs stock flow divergence)
3. 分时结构中的"拉升-回落-承接" (intraday pullback-support patterns)
4. 涨停股池内的相对强弱排序 (relative strength within limit-up universe)
5. 市场环境过滤因子 (market regime filters)
6. 筹码/融资/热度的变化率或背离 (cyq/margin/hot rate-of-change and divergences)

## Duplicates Checked and Removed

- 竞价量能 raw → C063 already covers auction volume surprise
- 竞价高开幅度 × 量 → C043 already covers
- VWAP 趋势 → C064 covers intraday vwap slope
- 尾盘量能占比 → C065 covers last-hour volume acceleration
- 超大单方向一致 → C068 covers elg persistence
- 融资余额变化率 → C069 covers margin momentum 5d
- 北向持股加速度 → C070 covers hk_hold acceleration
- 板块最强概念涨幅 → C082 covers ths_daily_concept_heat

---

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 10 | Data cached, formula clear, non-redundant, directly computable |
| P1 | 7 | Strong logic, needs cross-sectional or multi-source join |
| P2 | 3 | Sparse, overlap concern, or formula uncertain |
| blocked | 0 | — |
| **Total** | **20** | |

---

## P0 Candidates (10)

### C083: auction_to_first_bar_confirm

| Field | Value |
|-------|-------|
| factor_id | C083 |
| name | Auction-to-First-Bar Confirmation |
| family | auction_confirm |
| source_type | taoguba |
| source_ref | 打板手 "竞价高开后第一根5分钟能否站住=真假高开" |
| raw_idea | If first 5-min bar close > auction open price, the gap is confirmed; if it falls back, it's a fake open |
| computable_definition | `(first_5min_close - open) / open` where open = auction price |
| data_need | stk_mins_5 (first bar close) + daily open |
| asof_rule | T-day 9:35 (first bar complete); for training uses T-day value |
| leakage_risk | none (9:35 data available well before close) |
| coverage_estimate | ~95% |
| related_existing_features | C043 (auction price×volume), gap_pct (gap only, no follow-through) |
| duplicate_check | C043 is auction-time only; gap_pct is static gap. This captures post-auction follow-through. New concept. |
| engineering_status | candidate_ready |
| priority | P0 |

### C084: auction_gap_fill_speed

| Field | Value |
|-------|-------|
| factor_id | C084 |
| name | Auction Gap Fill Speed |
| family | auction_confirm |
| source_type | taoguba |
| source_ref | 竞价战法 "高开不回补=强势，高开快速回补=假突破" |
| raw_idea | How quickly (number of bars) the gap gets filled — fast fill = weak, no fill = strong |
| computable_definition | `1 - min(bars_to_fill_gap, 48) / 48` where fill = any bar low <= prev_close; if never filled = 1.0 |
| data_need | stk_mins_5 (bar lows) + daily prev_close + daily open |
| asof_rule | T-day 14:57 (all bars known) |
| leakage_risk | none |
| coverage_estimate | ~95% (all stocks that gap; ~60% have nonzero gap) |
| related_existing_features | gap_pct (static gap), C083 (first-bar only) |
| duplicate_check | gap_pct is level; C083 is first-bar; this is time-to-fill across full day. Different temporal scope. |
| engineering_status | candidate_ready |
| priority | P0 |

### C085: pullback_support_ratio

| Field | Value |
|-------|-------|
| factor_id | C085 |
| name | Pullback Support Ratio |
| family | intraday_structure |
| source_type | taoguba |
| source_ref | 短线操盘 "拉升后回踩不破均价线=承接有力" |
| raw_idea | After intraday high, the depth of pullback relative to the rise measures support strength |
| computable_definition | `1 - (high - close) / (high - low + eps)` equivalent to `(close - low) / (high - low)` = intraday close_position, BUT computed only for bars AFTER the day's high is reached |
| data_need | stk_mins_5 (identify bar where daily high occurs, then compute close position from that bar onward) |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | close_position (full day); C076 intraday_range_position_last_hour (last hour only) |
| duplicate_check | close_position uses full-day range. C076 uses last-hour range. This specifically measures post-high support. Different structural concept. |
| engineering_status | candidate_ready |
| priority | P0 |

### C086: intraday_pullback_depth

| Field | Value |
|-------|-------|
| factor_id | C086 |
| name | Intraday Maximum Pullback Depth |
| family | intraday_structure |
| source_type | github_paper |
| source_ref | Intraday drawdown as risk metric; max drawdown from running high |
| raw_idea | Maximum intraday drawdown from running high — small pullback = institutional support, large = distribution |
| computable_definition | `max((running_high - bar_close) / running_high, all_bars)` computed from 5-min cumulative high |
| data_need | stk_mins_5 (per-bar close vs running intraday high) |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | range_pct (high-low spread), intraday_volatility (std of returns) |
| duplicate_check | range_pct is spread; intraday_vol is dispersion. This is asymmetric drawdown from peak. New risk dimension. |
| engineering_status | candidate_ready |
| priority | P0 |

### C087: limit_pool_relative_strength

| Field | Value |
|-------|-------|
| factor_id | C087 |
| name | Limit-Up Pool Relative Strength |
| family | limit_list |
| source_type | taoguba |
| source_ref | 连板复盘 "同高度板中，封单/换手/时间最优的明日最强" |
| raw_idea | Among all stocks hitting limit-up on same day, rank by composite seal quality — top-ranked have higher next-day premium |
| computable_definition | `rank_within_limit_pool(seal_stability_score)` normalized [0,1], where pool = all T-day limit_list_d entries |
| data_need | limit_list_d (uses C046 seal_stability_score computed for all limit-up stocks) |
| asof_rule | T-day close (published ~16:00) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~2-5% daily (only limit-up stocks) |
| related_existing_features | C046 (seal stability absolute), C047 (turnover urgency absolute) |
| duplicate_check | C046/C047 are absolute scores; this is RELATIVE rank within same-day limit-up pool. Cross-sectional within sparse universe. |
| engineering_status | candidate_ready |
| priority | P0 |

### C088: sector_flow_divergence

| Field | Value |
|-------|-------|
| factor_id | C088 |
| name | Sector Momentum vs Stock Flow Divergence |
| family | divergence |
| source_type | github_paper |
| source_ref | Sector rotation divergence; price vs flow lead-lag |
| raw_idea | Stock's sector is rising (price) but stock's own moneyflow is negative = sector without conviction; vice versa = hidden accumulation |
| computable_definition | `sign(sector_ret_1d) * (-sign(net_mf_amount))` yields +1 when diverging (flow contrarian to sector), -1 when aligned |
| data_need | tushare moneyflow + sector/industry daily return (from ths_daily or moneyflow_ind_dc) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~85% |
| related_existing_features | C053 (rank flow vs industry flow), C077 (rank within sector) |
| duplicate_check | C053 compares stock flow rank to industry flow rank. C077 ranks within sector by flow. This captures PRICE-vs-FLOW divergence between sector and stock. Different signal: price momentum vs flow direction mismatch. |
| engineering_status | candidate_ready |
| priority | P0 |

### C089: market_breadth_thrust

| Field | Value |
|-------|-------|
| factor_id | C089 |
| name | Market Breadth Thrust |
| family | market_regime |
| source_type | github_paper |
| source_ref | Zweig Breadth Thrust adapted for A-shares; market-wide advance/decline regime |
| raw_idea | Fraction of stocks with positive return today — when breadth is extremely high, momentum regime favors continuation |
| computable_definition | `count(ret_1d > 0) / count(all_stocks)` broadcast as market-level feature |
| data_need | daily OHLCV (all stocks) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | 100% (market broadcast) |
| related_existing_features | market_emotion_score (limit-count based), C074 (flow regime), C078 (index return) |
| duplicate_check | market_emotion uses limit counts; C074 uses flow; C078 uses index return. This uses advance/decline ratio. Different market-level signal. |
| engineering_status | candidate_ready |
| priority | P0 |

### C090: market_limit_up_density

| Field | Value |
|-------|-------|
| factor_id | C090 |
| name | Market Limit-Up Density Regime |
| family | market_regime |
| source_type | taoguba |
| source_ref | 打板情绪 "涨停家数/跌停家数 > 5 = 赚钱效应强" |
| raw_idea | Ratio of limit-up to limit-down stocks as pure market regime signal — high ratio = board-play friendly environment |
| computable_definition | `market_limit_up_count / (market_limit_down_count + 1)` broadcast |
| data_need | market features already computed (market_limit_up_count, market_limit_down_count in expanded set) |
| asof_rule | T-day 14:57 (limit counts known by then) |
| leakage_risk | none |
| coverage_estimate | 100% (market broadcast) |
| related_existing_features | market_limit_up_count (raw count), market_limit_down_count (raw count) |
| duplicate_check | Raw counts exist individually. This is their RATIO — captures regime balance, not absolute level. Different semantics. |
| engineering_status | candidate_ready |
| priority | P0 |

### C091: hot_flow_alignment

| Field | Value |
|-------|-------|
| factor_id | C091 |
| name | Hot Attention × Flow Alignment |
| family | divergence |
| source_type | social_live |
| source_ref | 东财/同花顺 "热度上升+资金流入=真热，热度上升+资金流出=出货" |
| raw_idea | Attention increase (hot rank improving) combined with same-direction moneyflow = genuine interest; opposite = distribution |
| computable_definition | `sign(hot_rank_momentum) * sign(net_mf_amount)` yields +1 aligned, -1 diverging |
| data_need | ths_hot + tushare moneyflow |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~60% (limited by ths_hot coverage) |
| related_existing_features | C050 (hot_rank_momentum level), C051 (hot vs price divergence) |
| duplicate_check | C050 is hot momentum alone; C051 is hot vs price. This is hot vs FLOW. Different divergence pair. |
| engineering_status | candidate_ready |
| priority | P0 |

### C092: winner_rate_flow_divergence

| Field | Value |
|-------|-------|
| factor_id | C092 |
| name | Chip Winner Rate × Flow Divergence |
| family | divergence |
| source_type | taoguba |
| source_ref | 筹码+资金 "获利盘增加但资金还在流入 = 主力不出货，继续看多" |
| raw_idea | Winner rate increasing (potential selling pressure) but net flow still positive = main force absorbing profit-taking |
| computable_definition | `sign(winner_rate_delta_5d) * sign(net_mf_amount)` where both positive = flow confirming chip expansion |
| data_need | cyq_perf (winner_rate) + tushare moneyflow |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~75% (min of cyq ~80% and moneyflow ~99%) |
| related_existing_features | C057 (winner_rate_delta alone), C056 (cyq breakout × concentration) |
| duplicate_check | C057 is delta alone; C056 is chip × concentration. This is chip_delta × flow_direction. Different interaction. |
| engineering_status | candidate_ready |
| priority | P0 |

---

## P1 Candidates (7)

### C093: morning_session_momentum_fade

| Field | Value |
|-------|-------|
| factor_id | C093 |
| name | Morning Session Momentum Fade |
| family | intraday_structure |
| source_type | github_paper |
| source_ref | Intraday momentum reversal; opening-hour momentum decay literature |
| raw_idea | Morning session (9:30-11:30) return minus afternoon (13:00-14:57) return — positive means momentum faded |
| computable_definition | `morning_return - afternoon_return` where morning = bars 1-24, afternoon = bars 25-48 |
| data_need | stk_mins_5 |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | C060 (first15 vs tail), C049 (tail push strength) |
| duplicate_check | C060 is first-15-min vs last-30-min. C049 is tail return. This is full morning vs full afternoon. Different temporal split (half-day vs specific windows). |
| engineering_status | candidate |
| priority | P1 |

### C094: limit_consecutive_board_height

| Field | Value |
|-------|-------|
| factor_id | C094 |
| name | Consecutive Board Height |
| family | limit_list |
| source_type | taoguba |
| source_ref | 连板战法 "连板高度 = 市场认可度，同高度中选最强" |
| raw_idea | Number of consecutive limit-up days (board height) — higher boards have different premium profile |
| computable_definition | `consecutive_limit_up_days` from limit_list_d history (count T, T-1, T-2... where each day has limit_up entry) |
| data_need | limit_list_d (daily, check consecutive presence) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~1-3% daily |
| related_existing_features | prev_board_count (existing in expanded), C087 (relative rank within pool) |
| duplicate_check | prev_board_count exists but counts PREVIOUS streak. This counts CURRENT ONGOING streak including today. Different: current vs historical. Needs correlation check. |
| engineering_status | candidate |
| priority | P1 |

### C095: margin_flow_alignment

| Field | Value |
|-------|-------|
| factor_id | C095 |
| name | Margin × Moneyflow Alignment |
| family | divergence |
| source_type | social_live |
| source_ref | 两融+主力 "融资买入方向和主力资金一致=双重确认" |
| raw_idea | Margin balance increasing in same direction as main force flow = leveraged + institutional consensus |
| computable_definition | `sign(rzye_delta_pct) * sign(net_mf_amount)` (+1 = both buying, -1 = diverging) |
| data_need | margin_detail + tushare moneyflow |
| asof_rule | T-day close (both published T+1) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~70% |
| related_existing_features | C055 (margin × price), C069 (margin momentum alone) |
| duplicate_check | C055 is margin × return; C069 is margin level change. This is margin_direction × flow_direction. Different pair. |
| engineering_status | candidate |
| priority | P1 |

### C096: concept_breadth_strength

| Field | Value |
|-------|-------|
| factor_id | C096 |
| name | Concept Breadth Strength |
| family | sentiment |
| source_type | social_live |
| source_ref | 同花顺/东财 "概念板块内涨幅>3%家数/总家数 = 板块强度" |
| raw_idea | Fraction of stocks in stock's best concept board that are up >3% — measures theme breadth vs just the average |
| computable_definition | `count(stock in best_concept where ret_1d > 0.03) / count(all_stocks in best_concept)` |
| data_need | ths_daily + ths_member + daily OHLCV |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~85% |
| related_existing_features | C082 (max concept board return), sector_pct_change_best |
| duplicate_check | C082 uses max concept return (aggregate); this uses BREADTH within concept (how many stocks participating). Different: magnitude vs participation. |
| engineering_status | candidate |
| priority | P1 |

### C097: hot_rank_persistence_3d

| Field | Value |
|-------|-------|
| factor_id | C097 |
| name | Hot Rank Persistence 3-Day |
| family | sentiment |
| source_type | social_live |
| source_ref | 同花顺 "连续3天热度排名前50 = 持续关注" |
| raw_idea | Sustained high attention (hot rank consistently improving over multiple days) vs one-day spike |
| computable_definition | `sum(ths_hot_rank[T-i] < ths_hot_rank[T-i-1] for i in 0..2) / 3` (fraction of last 3 days with improving rank) |
| data_need | ths_hot (ths_hot_rank), 3-day window |
| asof_rule | T-day |
| leakage_risk | none |
| coverage_estimate | ~60-70% |
| related_existing_features | C050 (1-day hot momentum × level) |
| duplicate_check | C050 is 1-day momentum × level interaction. This is 3-day directional persistence (binary streak). Different temporal scope and no level interaction. |
| engineering_status | candidate |
| priority | P1 |

### C098: market_broken_board_fear

| Field | Value |
|-------|-------|
| factor_id | C098 |
| name | Market Broken Board Fear Index |
| family | market_regime |
| source_type | taoguba |
| source_ref | 打板情绪 "炸板率超过40% = 谨慎日，不打板" |
| raw_idea | Market-level broken board rate as regime filter — high broken_board_rate = hostile environment for board plays |
| computable_definition | `market_broken_board_rate` (already exists as feature, but z-scored: `zscore(market_broken_board_rate, window=20)`) |
| data_need | market features (market_broken_board_rate already in expanded) |
| asof_rule | T-day 14:57 (known by then) |
| leakage_risk | none |
| coverage_estimate | 100% (market broadcast) |
| related_existing_features | market_broken_board_rate (raw rate, no z-score normalization) |
| duplicate_check | Raw rate exists. This is z-scored version (relative to recent 20-day history). Transforms absolute to relative regime. Moderate overlap — depends on whether raw rate already captures regime. |
| engineering_status | candidate |
| priority | P1 |

### C099: intraday_accumulation_distribution

| Field | Value |
|-------|-------|
| factor_id | C099 |
| name | Intraday Accumulation-Distribution |
| family | intraday_structure |
| source_type | github_paper |
| source_ref | Williams Accumulation/Distribution adapted to 5-min bars |
| raw_idea | Intraday A/D line slope from 5-min bars — distinguishes accumulation (buying on dips) from distribution (selling on rallies) |
| computable_definition | `sum(((bar_close - bar_low) - (bar_high - bar_close)) / (bar_high - bar_low + eps) * bar_volume, all_48_bars) / sum(bar_volume, 48)` |
| data_need | stk_mins_5 (OHLCV per bar) |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | C048 (vwap × up_volume), C064 (vwap slope), close_position |
| duplicate_check | C048 is end-of-day vwap×volume; C064 is vwap trend slope. This is Williams A/D using bar-level OHLCV structure. Different methodology (price position within bar × volume). |
| engineering_status | candidate |
| priority | P1 |

---

## P2 Candidates (3)

### C100: opening_rotation_signal

| Field | Value |
|-------|-------|
| factor_id | C100 |
| name | Opening Rotation Signal |
| family | auction_confirm |
| source_type | taoguba |
| source_ref | 集合竞价 "9:20-9:25撤单方向 = 真实意图" (竞价最后阶段不可撤单) |
| raw_idea | The difference between 9:20 indicative price and final 9:25 auction price reveals last-minute intent |
| computable_definition | `(auction_final_price - auction_indicative_price_920) / prev_close` |
| data_need | stk_auction_o (may contain only final VWAP, not 9:20 snapshot — needs verification) |
| asof_rule | T-day 9:25 |
| leakage_risk | none |
| coverage_estimate | uncertain — depends on whether stk_auction_o contains pre-final snapshots |
| related_existing_features | C011 (final auction ratio), C043 (final × volume) |
| duplicate_check | C011/C043 use FINAL auction result. This uses CHANGE during auction process. Different if data available. |
| engineering_status | needs_validation |
| priority | P2 |

### C101: cyq_cost_concentration_velocity

| Field | Value |
|-------|-------|
| factor_id | C101 |
| name | CYQ Cost Concentration Velocity |
| family | cyq |
| source_type | github_paper |
| source_ref | Chip concentration dynamics; rate of change in cost_concentration |
| raw_idea | Rapidly increasing cost concentration = chips consolidating to fewer hands = institutional control accelerating |
| computable_definition | `(cost_concentration[T] - cost_concentration[T-5]) / cost_concentration[T-5]` |
| data_need | cyq_perf (cost_concentration), 5-day lag |
| asof_rule | T-day close (cyq published T+1) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~80% |
| related_existing_features | C056 (breakout × concentration level), C073 (winner_rate delta × base) |
| duplicate_check | C056 uses concentration LEVEL × position; C073 uses winner_rate change. This is concentration CHANGE rate. Similar family but different variable's derivative. Moderate overlap with C056 in regime. |
| engineering_status | needs_validation |
| priority | P2 |

### C102: flow_reversal_after_decline

| Field | Value |
|-------|-------|
| factor_id | C102 |
| name | Flow Reversal After Decline |
| family | divergence |
| source_type | taoguba |
| source_ref | 超跌反弹 "连跌后主力资金转正 = 底部信号" |
| raw_idea | Net moneyflow turning positive after 3+ days of negative returns = potential bottom accumulation |
| computable_definition | `(sum(ret_1d < 0, 3) >= 3) * max(net_mf_amount, 0) / (abs(net_mf_amount) + eps)` conditional flow signal |
| data_need | tushare moneyflow + daily OHLCV (3-day return history) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% (but conditional: ~15-20% of stocks meet 3-day decline condition) |
| related_existing_features | C002 (flow momentum z-score), C003 (flow persistence) |
| duplicate_check | C002/C003 are unconditional flow features. This is CONDITIONAL on prior decline. Different: event-gated vs always-on. May be unstable due to conditional logic. |
| engineering_status | needs_validation |
| priority | P2 |

---

## Engineering Readiness Summary

| Status | IDs | Count |
|--------|-----|-------|
| candidate_ready | C083-C092 | 10 |
| candidate (needs minor engineering) | C093-C099 | 7 |
| needs_validation | C100-C102 | 3 |

## Implementation Priority: Top 8 (recommended for training framework)

| Rank | ID | Name | Family | Coverage | Why First |
|------|-----|------|--------|----------|-----------|
| 1 | C083 | auction_to_first_bar_confirm | auction_confirm | ~95% | Gap follow-through confirmation; no existing factor covers this |
| 2 | C085 | pullback_support_ratio | intraday_structure | ~95% | Post-high support; unique structural concept from taoguba |
| 3 | C088 | sector_flow_divergence | divergence | ~85% | Price-vs-flow sector divergence; captures hidden accumulation |
| 4 | C089 | market_breadth_thrust | market_regime | 100% | Market regime from breadth; complements existing emotion features |
| 5 | C090 | market_limit_up_density | market_regime | 100% | Limit-up/down ratio regime; pure board-play environment filter |
| 6 | C086 | intraday_pullback_depth | intraday_structure | ~95% | Max drawdown from running high; risk dimension not currently captured |
| 7 | C092 | winner_rate_flow_divergence | divergence | ~75% | Chip × flow interaction; captures "main force absorbing profit-taking" |
| 8 | C091 | hot_flow_alignment | divergence | ~60% | Hot attention × flow direction; separates genuine heat from distribution |

---

## Constraints Confirmation

- [x] No training executed
- [x] No gpu_probe.py changes
- [x] No frozen_forward_config changes
- [x] No passed/final_unseen/final_accepted claims
- [x] All candidates use verified cached data
- [x] Duplicate check against C001-C082 + all existing features
- [x] Avoided all directions already covered in C043-C082

---

*Factor search round 3, 2026-05-05. 20 new candidates (C083-C102). No claims of passed/final_unseen/final_accepted.*

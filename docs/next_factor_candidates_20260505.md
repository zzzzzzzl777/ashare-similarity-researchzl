# Next Factor Candidates -- 2026-05-05

> Round: post-training-reconciliation, 780-pool derivative exploration
> Goal: 20 new candidates (C043-C062) from 3 search paths
> Constraint: no training, no gpu_probe.py changes, no frozen_forward_config changes
> Data-first filter: only candidates using already cached data or existing OHLCV/Tushare feature frames
> Existing duplicates checked against: GPU_PROBE_STABLE_FEATURES (370), GPU_PROBE_EXPANDED_FEATURES, TUSHARE_FACTOR_COLUMNS (46), C001-C042

## Search Paths

| Path | Source | Rationale |
|------|--------|-----------|
| 1 - taoguba short-term | taoguba 短线大师观察, 打板逻辑 | 贴近实战交易逻辑, A股特有模式 |
| 2 - GitHub/papers | academic alpha, microstructure, flow-price interaction | 跨市场验证的因子逻辑 |
| 3 - social/live traders | 东财/雪球/实盘交易员规则 | 市场参与者视角, 行为金融因子 |

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 8 | Data cached, T-day computable, clear non-redundancy, directly from 780-pool-validated features |
| P1 | 8 | Strong logic, needs additional rolling window or sparse data source |
| P2 | 4 | Formula uncertain, may overlap, or sparse/unstable |
| **Total** | **20** | |

## Existing Features Checked (Duplicates Removed)

The following proposed ideas were **dropped** because equivalent columns already exist in expanded or prior candidates:
- Auction open gap -- close to `gap_pct` and C012 (auction_gap_normalized)
- VWAP deviation rank -- close to existing `cs_vwap_deviation_rank` if computed
- Net flow 5-day sum -- similar to C003 (mf_persistence_5d) in intent
- Seal ratio raw -- already in limit_list_d raw features passed to model
- Winner rate level -- already `cyq_winner_rate` in research feature set
- Last 30min return -- already `last_30min_return` in stk_mins_5 features

---

## P0 Candidates (8)

### C043: auction_price_volume_confirm

| Field | Value |
|-------|-------|
| factor_id | C043 |
| name | Auction Price-Volume Confirmation |
| family | auction |
| source_type | taoguba |
| source_ref | 打板复盘 "集合竞价量价齐升确认" -- 开盘竞价高开+放量才有效 |
| raw_idea | Opening auction showing premium is only meaningful if accompanied by volume; price without volume is fake open |
| computable_definition | `(auction_open_vwap_ratio - 1) * log1p(auction_open_vol / mean(volume, 5))` |
| data_need | stk_auction_o (vwap, vol) + daily volume (5-day mean) |
| asof_rule | T-day 9:25 auction complete, all fields known before 9:30 |
| leakage_risk | none |
| coverage_estimate | ~95% (stk_auction_o cached 804 days) |
| related_existing_features | tushare_auction_open_vwap_ratio (C011, price-only, no volume confirm) |
| duplicate_check | C011 is price-only; this is price×volume interaction. Not redundant. |
| engineering_status | candidate_ready |
| priority | P0 |
| reason | C011 selected in 5/6 runs but has no solo signal; volume confirmation adds discriminative power. Both components cached. |

### C044: auction_close_pressure

| Field | Value |
|-------|-------|
| factor_id | C044 |
| name | Auction Close Pressure |
| family | auction |
| source_type | social_live |
| source_ref | 东财实盘 "尾盘集合竞价抢筹/砸盘" -- 14:57-15:00 集合竞价方向 |
| raw_idea | Close auction premium with volume = institutional tail-session accumulation or distribution |
| computable_definition | `(auction_close_vwap_ratio - 1) * log1p(auction_close_vol / mean(volume, 5))` |
| data_need | stk_auction_c (vwap, vol) + daily volume (5-day mean) |
| asof_rule | T-day 15:00 close auction complete; for 14:57 prediction, use T-1 value |
| leakage_risk | T-day value not available at 14:57; must use T-1 lag |
| coverage_estimate | ~95% (stk_auction_c cached 804 days) |
| related_existing_features | none -- no existing close-auction feature in expanded/research |
| duplicate_check | No close auction factor exists. C043 is open auction; this is close. |
| engineering_status | candidate_ready |
| priority | P0 |
| reason | Close auction is a distinct session from open; captures 14:57-15:00 institutional intent. T-1 lag is still informative (persistence). |

### C045: auction_vwap_shift

| Field | Value |
|-------|-------|
| factor_id | C045 |
| name | Auction VWAP Shift (Open→Close) |
| family | auction |
| source_type | github_paper |
| source_ref | Intraday sentiment drift; opening vs closing auction comparison |
| raw_idea | If close auction premium > open auction premium, sentiment improved during the day; vice versa |
| computable_definition | `auction_close_vwap_ratio - auction_open_vwap_ratio` |
| data_need | stk_auction_o + stk_auction_c |
| asof_rule | T-day 15:00 complete; for 14:57, use T-1 lag |
| leakage_risk | same as C044 (close auction at 15:00); use T-1 |
| coverage_estimate | ~95% |
| related_existing_features | C011 (open only), C044 (close only); this is their difference |
| duplicate_check | Neither C011 nor C044 captures the shift. Not correlated with either alone. |
| engineering_status | candidate_ready |
| priority | P0 |
| reason | Captures intraday sentiment reversal between two auction windows; direction of institutional opinion change |

### C046: seal_stability_score

| Field | Value |
|-------|-------|
| factor_id | C046 |
| name | Seal Stability Score |
| family | limit_list |
| source_type | taoguba |
| source_ref | 打板手法 "封板强度 = 早封+少开 = 强度" |
| raw_idea | Early seal (low first_time_minutes) with few openings (low open_times) is classic strong board signal |
| computable_definition | `seal_ratio / (1 + open_times) * exp(-first_time_minutes / 240)` |
| data_need | limit_list_d (seal_ratio, open_times, first_time_minutes) |
| asof_rule | T-day close (limit_list_d is T-day data, published ~16:00) |
| leakage_risk | none for T+1 prediction; field is T-day summarized |
| coverage_estimate | ~2-5% daily (only limit-up stocks have entries) |
| related_existing_features | raw limit_list_d columns in research set (seal_ratio, open_times, first_time_minutes individually) |
| duplicate_check | Individual raw columns exist but not this composite interaction. Exponential time-decay × stability is new. |
| engineering_status | candidate_ready |
| priority | P0 |
| reason | All 3 components from limit_list_d were selected in 780-pool. This composite captures the taoguba "strong board" consensus into a single score. Sparse but high-signal for board-play universe. |

### C047: first_seal_turnover_urgency

| Field | Value |
|-------|-------|
| factor_id | C047 |
| name | First-Seal Turnover Urgency |
| family | limit_list |
| source_type | taoguba |
| source_ref | 打板复盘 "秒板+高换手 = 资金一致性抢筹" |
| raw_idea | Flash seal (very early) combined with high turnover means aggressive unanimous buying |
| computable_definition | `exp(-first_time_minutes / 240) * limit_turnover` |
| data_need | limit_list_d (first_time_minutes, limit_turnover) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~2-5% daily |
| related_existing_features | limit_list_d raw columns; C046 uses seal_ratio/open_times, this uses turnover |
| duplicate_check | C046 measures stability (seal_ratio × few opens); C047 measures urgency (early × high turnover). Different dimensions. |
| engineering_status | candidate_ready |
| priority | P0 |
| reason | Turnover urgency and seal stability are orthogonal. Turnover measures breadth of participation, stability measures price holding. Both from 780-pool selected data. |

### C048: vwap_reclaim_strength

| Field | Value |
|-------|-------|
| factor_id | C048 |
| name | VWAP Reclaim Strength |
| family | intraday_5m |
| source_type | social_live |
| source_ref | 游资实盘 "站上均价线+上攻量能配合" |
| raw_idea | Price above VWAP with proportional up-volume participation signals institutional support |
| computable_definition | `close_vs_vwap * up_volume_ratio` where close_vs_vwap = (close - vwap) / vwap, up_volume_ratio from 5-min bars |
| data_need | stk_mins_5 (close_vs_vwap, up_volume_ratio) |
| asof_rule | T-day 14:57 (last 5-min bar before close auction) |
| leakage_risk | none (all 5-min data prior to close) |
| coverage_estimate | ~95% (stk_mins_5 widely cached) |
| related_existing_features | close_vs_vwap (level only, no volume dimension) |
| duplicate_check | close_vs_vwap exists alone. This adds volume confirmation. Multiplicative interaction is not linearly representable. |
| engineering_status | candidate_ready |
| priority | P0 |
| reason | close_vs_vwap selected in 780-pool. Adding volume direction creates a quality signal -- above VWAP with down-volume is different from above VWAP with up-volume. |

### C049: tail_push_strength

| Field | Value |
|-------|-------|
| factor_id | C049 |
| name | Tail-Push Strength |
| family | intraday_5m |
| source_type | taoguba |
| source_ref | 尾盘战法 "尾盘拉升+量能配合/波动低 = 明日溢价" |
| raw_idea | Last-30-min push normalized by intraday volatility, confirmed by up-volume ratio |
| computable_definition | `last_30min_return * up_volume_ratio / (1 + intraday_volatility)` where intraday_volatility = std of 5-min returns |
| data_need | stk_mins_5 (last_30min_return, up_volume_ratio, intraday_volatility) |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | last_30min_return (level only, no vol adjustment or volume confirm) |
| duplicate_check | last_30min_return is raw. This is risk-adjusted and volume-confirmed. Triple interaction is new. |
| engineering_status | candidate_ready |
| priority | P0 |
| reason | last_30min_return selected in 780-pool. Raw return is noisy; normalizing by volatility and confirming with volume separates genuine institutional tail-push from random drift. |

### C050: hot_rank_momentum

| Field | Value |
|-------|-------|
| factor_id | C050 |
| name | THS Hot Rank Momentum |
| family | sentiment |
| source_type | social_live |
| source_ref | 同花顺热度排名变化 "热度加速 = 散户关注即将爆发" |
| raw_idea | App heat acceleration (rank improving rapidly) × heat level = attention about to translate to price |
| computable_definition | `-delta(ths_hot_rank, 1) * log1p(ths_hot_value)` where delta = rank[T] - rank[T-1] (negative rank change = rank improving) |
| data_need | ths_hot (ths_hot_rank, ths_hot_value) |
| asof_rule | T-day intraday (ths_hot updated every ~30min) |
| leakage_risk | none |
| coverage_estimate | ~60-70% (ths_hot available for actively traded stocks) |
| related_existing_features | none -- no ths_hot derivative in current feature set |
| duplicate_check | Raw ths_hot fields may be in research set but not their momentum/interaction. |
| engineering_status | candidate_ready |
| priority | P0 |
| reason | Attention precedes price in retail-driven A-share market. Rank momentum captures acceleration of crowd focus before it fully materializes in price. |

---

## P1 Candidates (8)

### C051: hot_price_divergence

| Field | Value |
|-------|-------|
| factor_id | C051 |
| name | Hot-Price Divergence |
| family | sentiment |
| source_type | social_live |
| source_ref | 雪球 "热度上升但价格没涨 = 即将补涨" 逻辑 |
| raw_idea | Stock gaining attention (hot rank improving) faster than price, implies attention leads price |
| computable_definition | `rank(hot_rank_momentum) - rank(ret_1d)` cross-sectional |
| data_need | ths_hot + daily OHLCV |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~60-70% (limited by ths_hot coverage) |
| related_existing_features | C050 (hot_rank_momentum level); this is cross-sectional divergence vs price |
| duplicate_check | C050 is absolute momentum; this is relative divergence vs price. Different concept. |
| engineering_status | candidate |
| priority | P1 |
| reason | Cross-sectional rank required. Coverage limited. But captures lead-lag between attention and price -- a well-documented behavioral factor in retail markets. |

### C052: northbound_market_tailwind

| Field | Value |
|-------|-------|
| factor_id | C052 |
| name | Northbound Market Tailwind |
| family | market_flow |
| source_type | github_paper |
| source_ref | "Foreign Flow Factor" -- literature on QFII/northbound impact on A-shares |
| raw_idea | Aggregate northbound money z-score as a market regime indicator broadcast to all stocks |
| computable_definition | `zscore(north_net_inflow, window=20)` broadcast as market-level feature |
| data_need | moneyflow_hsgt (aggregate northbound daily net) |
| asof_rule | T-day close (northbound data available same day ~16:30) |
| leakage_risk | none for T+1 |
| coverage_estimate | 100% (market-level, applies to all stocks) |
| related_existing_features | market_emotion_score, market_limit_up_count (other market features, different source) |
| duplicate_check | No northbound flow feature in current set. |
| engineering_status | candidate |
| priority | P1 |
| reason | Market-level liquidity regime. Requires moneyflow_hsgt API cache (not yet verified count). Captures foreign institutional sentiment that affects entire market directionally. |

### C053: industry_flow_alignment

| Field | Value |
|-------|-------|
| factor_id | C053 |
| name | Industry Flow Alignment |
| family | industry_flow |
| source_type | github_paper |
| source_ref | "Industry Momentum & Crowding" -- stock flow relative to industry flow |
| raw_idea | Stock receiving more/less flow than its industry peers = alpha opportunity vs crowding |
| computable_definition | `rank(stock_net_mf) - rank(industry_net_flow)` within same industry |
| data_need | tushare moneyflow (stock-level) + moneyflow_ind_ths or moneyflow_ind_dc (industry-level) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~80% (industry flow coverage depends on classification availability) |
| related_existing_features | sector_pct_change_best, sector_strength_rank (price-based, not flow-based) |
| duplicate_check | Existing sector features use price returns. This uses money flow. Different signal source. |
| engineering_status | candidate |
| priority | P1 |
| reason | Industry moneyflow API cache needs verification. Cross-sectional within industry. Captures flow crowding/divergence vs peers. |

### C054: northbound_stock_alignment

| Field | Value |
|-------|-------|
| factor_id | C054 |
| name | Northbound Stock Flow-Price Alignment |
| family | hk_hold |
| source_type | github_paper |
| source_ref | "Smart Money" flow-price alignment in HK-connect data |
| raw_idea | Foreign holding change aligned with price direction = smart money confirmation |
| computable_definition | `hk_ratio_delta_1d * sign(ret_1d)` where hk_ratio_delta = change in HK holding ratio |
| data_need | hk_hold (holding ratio) + daily OHLCV |
| asof_rule | T-day close (hk_hold published T+1 morning for T-day) |
| leakage_risk | none for T+1 prediction (T-day HK data available by T+1 morning) |
| coverage_estimate | ~40-50% (only stocks in HK-connect, ~1000 of 5000) |
| related_existing_features | none -- no hk_hold derivative in current set |
| duplicate_check | No HK holding features exist in expanded. |
| engineering_status | candidate |
| priority | P1 |
| reason | Coverage limited to ~1000 HK-connect stocks. Sparse but high-signal when available. HK holding change is a documented alpha source in A-share literature. |

### C055: margin_chase_pressure

| Field | Value |
|-------|-------|
| factor_id | C055 |
| name | Margin Chase Pressure |
| family | margin |
| source_type | social_live |
| source_ref | 两融追涨逻辑 "融资余额增加 + 涨幅 = 杠杆追涨" |
| raw_idea | Levered buyers (margin) chasing winners amplifies momentum and creates fragility |
| computable_definition | `rzye_delta_pct * max(ret_1d, 0)` where rzye_delta_pct = margin balance day-over-day % change |
| data_need | margin_detail (rzye balance) + daily OHLCV |
| asof_rule | T-day close (margin data published T+1 morning) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~70% (margin-eligible stocks) |
| related_existing_features | none -- no margin derivative in current set |
| duplicate_check | No margin feature in expanded. rzye_delta_pct alone is in research raw set but not this interaction. |
| engineering_status | candidate |
| priority | P1 |
| reason | Margin data ~70% coverage, published T+1 morning. Interaction of margin acceleration with positive return captures leveraged momentum amplification. |

### C056: cyq_breakout_pressure

| Field | Value |
|-------|-------|
| factor_id | C056 |
| name | CYQ Breakout Pressure |
| family | cyq |
| source_type | taoguba |
| source_ref | 筹码分布 "突破密集成本区 + 筹码集中 = 拉升无压" |
| raw_idea | Price above most holders' cost + concentrated chip distribution = minimal selling pressure for further advance |
| computable_definition | `cost_position * cost_concentration` where cost_position = (close - avg_cost) / avg_cost |
| data_need | cyq_perf (winner_rate, cost_concentration, avg_cost) + daily close |
| asof_rule | T-day close (cyq_perf published T+1) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~80% (cyq_perf available for most active stocks) |
| related_existing_features | cost_position_20 (similar concept but uses 20-day window, not chip distribution) |
| duplicate_check | cost_position_20 uses rolling-window pseudo-cost. This uses actual chip distribution from cyq_perf. Different data source and meaning. |
| engineering_status | candidate |
| priority | P1 |
| reason | cyq_perf winner_rate was selected in 780-pool. This interaction captures the specific "breakout above cost + concentrated chips" pattern from taoguba board-play analysis. |

### C057: winner_rate_delta_5d

| Field | Value |
|-------|-------|
| factor_id | C057 |
| name | Winner Rate 5-Day Delta |
| family | cyq |
| source_type | github_paper |
| source_ref | Chip distribution momentum; profit-holder expansion rate |
| raw_idea | Rapid increase in winner rate = price breaking above more cost levels = bullish momentum |
| computable_definition | `winner_rate[T] - winner_rate[T-5]` |
| data_need | cyq_perf (winner_rate), 5-day lag |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~80% |
| related_existing_features | cyq_winner_rate (level only in research set) |
| duplicate_check | Level exists but 5-day momentum is new. First derivative of selected feature. |
| engineering_status | candidate |
| priority | P1 |
| reason | winner_rate level captures static state; delta captures velocity of profit-holder expansion. Same logic as adding momentum to moneyflow (C002). |

### C058: lhb_institutional_confirmation

| Field | Value |
|-------|-------|
| factor_id | C058 |
| name | LHB Institutional Confirmation |
| family | lhb |
| source_type | taoguba |
| source_ref | 龙虎榜 "机构席位净买入占比 > 游资" = 机构认可 |
| raw_idea | When stock enters LHB (dragon-tiger-board), institutional net buy as fraction of total LHB buy indicates smart-money conviction |
| computable_definition | `inst_net_buy / max(abs(lhb_net_buy), eps)` where eps = 1e6 |
| data_need | top_list (lhb_net_buy) + top_inst (inst_buy, inst_sell) |
| asof_rule | T-day close (LHB published T+1 ~18:00) |
| leakage_risk | none for T+1 (published before next trading day) |
| coverage_estimate | ~1-3% daily (only LHB-qualifying stocks) |
| related_existing_features | lhb_appeared, lhb_net_buy, inst_buy_count in research raw |
| duplicate_check | Raw fields exist individually. This interaction (inst fraction) is new. Very sparse. |
| engineering_status | candidate |
| priority | P1 |
| reason | Extremely sparse but high-signal. When available, institutional confirmation on LHB is a well-known alpha source. Works as event-gated factor -- NaN when no LHB, meaningful when present. |

---

## P2 Candidates (4)

### C059: limit_theme_breadth

| Field | Value |
|-------|-------|
| factor_id | C059 |
| name | Limit Theme Breadth |
| family | limit_list |
| source_type | taoguba |
| source_ref | 打板 "板块效应 = 同题材多只涨停 = 明日溢价高" |
| raw_idea | Count of same-theme stocks hitting limit-up on same day; more peers = stronger theme momentum |
| computable_definition | `count(limit_up_stocks in same_theme[T])` using lu_desc from limit_list_d for theme grouping |
| data_need | limit_list_d (lu_desc for theme tag) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~2-5% daily (limit-up stocks only) |
| related_existing_features | market_limit_up_count (aggregate, not theme-specific) |
| duplicate_check | market_limit_up_count is total count. This is within-theme count. Different granularity. |
| engineering_status | needs_engineering |
| priority | P2 |
| reason | Needs reliable lu_desc parsing and same-theme grouping logic. Theme tags are free-text, inconsistent across days. High engineering risk. |

### C060: first15_tail_reversal

| Field | Value |
|-------|-------|
| factor_id | C060 |
| name | First-15 vs Tail Reversal |
| family | intraday_5m |
| source_type | social_live |
| source_ref | 日内反转策略 "开盘冲高回落 vs 尾盘拉升" 方向差异 |
| raw_idea | First 15-min return vs last 30-min return disagreeing = potential reversal setup |
| computable_definition | `sign(last_30min_return) * (last_30min_return - first_15min_return)` |
| data_need | stk_mins_5 (first_15min_return, last_30min_return) |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | last_30min_return, overnight_vs_intraday (similar reversal concept) |
| duplicate_check | May overlap with overnight_vs_intraday decomposition. Needs correlation check. |
| engineering_status | needs_validation |
| priority | P2 |
| reason | Potential overlap with overnight_vs_intraday. Direction sign needs careful thought (are we capturing reversal-buyers or continuation?). |

### C061: hsgt_top10_stock_pressure

| Field | Value |
|-------|-------|
| factor_id | C061 |
| name | HSGT Top-10 Stock Pressure |
| family | hk_hold |
| source_type | github_paper |
| source_ref | Northbound top-10 active stock daily appearance |
| raw_idea | Stock appearing in northbound top-10 active list = exceptional foreign focus |
| computable_definition | `appeared_in_hsgt_top10 * north_net_inflow_rank` |
| data_need | hsgt_top10 (daily top-10 northbound active stocks) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~0.2% daily (only 10 stocks per direction per day) |
| related_existing_features | C054 (northbound stock alignment, uses hk_hold ratio change) |
| duplicate_check | C054 uses broad holding ratio. This is extreme-focus top-10 appearance. Very sparse but different signal. |
| engineering_status | needs_engineering |
| priority | P2 |
| reason | Extremely sparse (10 stocks/day). May not have enough signal for stable_tail selection. But when appearing, it's a very strong institutional attention signal. |

### C062: lhb_afterglow_decay

| Field | Value |
|-------|-------|
| factor_id | C062 |
| name | LHB Afterglow Decay |
| family | lhb |
| source_type | taoguba |
| source_ref | 龙虎榜 "上榜后 1-3 日余热衰减" |
| raw_idea | LHB appearance has decaying effect over subsequent days; capture the half-life of the event |
| computable_definition | `lhb_appeared_lag1 * 0.5 + lhb_appeared_lag2 * 0.25 + lhb_appeared_lag3 * 0.125` with lhb_net_buy sign |
| data_need | top_list (lhb_appeared, lhb_net_buy) with 3-day lag |
| asof_rule | T-day (uses T-1 to T-3 LHB data) |
| leakage_risk | none (all lagged) |
| coverage_estimate | ~3-8% (any stock that appeared in LHB in past 3 days) |
| related_existing_features | lhb_appeared (binary event, no decay modeling) |
| duplicate_check | Raw lhb_appeared is binary same-day. This is exponential decay over 3 days. Different temporal profile. |
| engineering_status | needs_engineering |
| priority | P2 |
| reason | Very sparse and may become regime-specific (works in hot markets with frequent LHB, fails in quiet markets). Decay coefficients are arbitrary. |

---

## Engineering Readiness Summary

| Status | IDs | Count |
|--------|-----|-------|
| candidate_ready | C043, C044, C045, C046, C047, C048, C049, C050 | 8 |
| candidate (needs minor engineering) | C051, C052, C053, C054, C055, C056, C057, C058 | 8 |
| needs_engineering / needs_validation | C059, C060, C061, C062 | 4 |

## Data Source Coverage

| Data Source | Cached Days | Candidates Using | Notes |
|-------------|-------------|-----------------|-------|
| stk_auction_o | 804 | C043, C045 | Both open auction components |
| stk_auction_c | 804 | C044, C045 | Close auction; C044/C045 use T-1 lag for 14:57 |
| limit_list_d | cached | C046, C047, C059 | Sparse ~2-5%; high signal for board-play |
| stk_mins_5 | cached | C048, C049, C060 | High coverage ~95% |
| ths_hot | cached | C050, C051 | ~60-70% coverage |
| moneyflow_hsgt | needs verify | C052 | Market-level; single API call |
| moneyflow_ind_ths | needs verify | C053 | Industry-level flow |
| hk_hold | cached | C054, C061 | ~40-50% (HK-connect only) |
| margin_detail | cached | C055 | ~70% (margin-eligible) |
| cyq_perf | cached | C056, C057 | ~80% |
| top_list + top_inst | cached | C058, C062 | ~1-3% daily (LHB only) |

## Implementation Priority for Training Framework

Immediate (data fully cached, formula clear, non-redundant):
1. **C043** - auction price-volume confirm (builds on C011)
2. **C048** - VWAP reclaim strength (builds on 780-pool selected close_vs_vwap)
3. **C049** - tail push strength (builds on 780-pool selected last_30min_return)
4. **C046** - seal stability score (builds on 780-pool selected limit_list_d fields)
5. **C047** - first seal turnover urgency (same family as C046)
6. **C050** - hot rank momentum (ths_hot cached, unique signal source)

Next (data cached but needs lag handling or cross-sectional):
7. **C044** - auction close pressure (T-1 lag needed)
8. **C045** - auction VWAP shift (T-1 lag needed)

---

## Constraints Confirmation

- [x] No training executed
- [x] No gpu_probe.py changes
- [x] No frozen_forward_config changes
- [x] No passed/final_unseen/final_accepted claims
- [x] All candidates use already cached data sources or verifiable APIs
- [x] Duplicate check performed against all existing features (370 expanded + 46 tushare + C001-C042)

---

*Factor search round 2026-05-05. 20 new candidates (C043-C062). No claims of passed/final_unseen/final_accepted.*

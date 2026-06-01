# Four-Source Shortline Omnibus Candidate Addendum 3 2026-05-17

Scope: factor-library research only. No training, no `gpu_probe`, no model-code changes, no formal registry writes.

This is the fourth scan pass after O001-O330. It adds O331-O450 and tries to absorb the remaining scan-able short-line factor concepts from the local raw pool and external sources. These IDs are still temporary `Oxxx` research IDs, not formal `Cxxx` registry IDs.

## Current Baseline

- Formal registry: `E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json`
- Current formal registry count: C001-C292
- Raw pool records: 3,075
- Previous temporary queue: O001-O330
- This addendum queue: O331-O450

## Fourth-Pass Rule

At this point many remaining raw names are repeats or trading slogans. This pass only keeps a concept if it can be mapped to one of:

- a stock-day / stock-cutoff numeric factor,
- a market or theme state variable useful as a feature or gate,
- an event/attention/flow variable with an identifiable data pipeline,
- a high-frequency template from reports or papers.

Pure position sizing, discretionary stop-loss rules, and duplicate aliases are not separately promoted.

## Addendum 3 Candidate Queue

### A. Limit Premium / Board Ecology / Seal Microstructure

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O331 | market_limit_attempt_count | P0 | local_raw_limit | limit_pool | count stocks that touched upper limit, including failed attempts | ready_engineering_review | O111/O120 |
| O332 | market_open_board_rate_canonical | P0 | local_raw_limit | limit_pool | open_board_count / limit_attempt_count | ready_engineering_review | open_board_rate |
| O333 | limit_premium_decay_curve | P1 | local_raw_limit | limit_pool + returns | fit decay curve of yesterday-limit basket premium over lookback | needs_formula_lock | O030/O119 |
| O334 | limit_premium_regime | P1 | local_raw_limit | limit_pool + returns | premium percentile regime: expanding, stable, decaying, crash | needs_formula_lock | O333 |
| O335 | yesterday_limit_open_premium | P1 | local_raw_limit | limit_pool + daily_ohlcv | average open premium of yesterday limit-up stocks | ready_engineering_review | O119 |
| O336 | max_board_height_ceiling | P1 | local_raw_limit | limit_pool | current max board height vs rolling max/percentile | ready_engineering_review | O026/O118 |
| O337 | market_avg_subnew_board_height | P2 | local_raw_subnew | listing age + limit_pool | average board height of recent IPO/sub-new cohort | ready_engineering_review | O270/O271 |
| O338 | zt_total_nonst_nononeword | P0 | local_raw_limit | limit_pool | non-ST, non-one-word limit-up count | ready_engineering_review | O120 |
| O339 | today_promoted_prev_n_board | P1 | local_raw_limit | limit_pool | prior N-board stocks promoted to N+1 today / prior N-board count | ready_engineering_review | board survival |
| O340 | second_seal_opportunity | P1 | local_raw_limit | limit_pool + 1min | probability/quality of second seal after first break | ready_engineering_review | O129/O341 |
| O341 | reseal_speed_real | P1 | local_raw_limit | 1min + limit_pool | minutes from open-board/break to reseal | ready_engineering_review | O117/O340 |
| O342 | seal_time_distribution_entropy | P1 | local_raw_limit | limit_pool | entropy/concentration of market seal times | ready_engineering_review | seal_time_distribution |
| O343 | seal_ratio_score | P1 | local_raw_limit | limit_pool | seal amount / circulating amount or attempted amount | needs_formula_lock | seal_ratio_factor |
| O344 | seal_queue_success_probability | P1 | local_raw_limit | limit_pool + auction/amount | expected opening volume / seal order queue capped to [0,1] | needs_data_pipeline | success_prob |
| O345 | large_order_seal_count | P2 | local_raw_limit | limit_pool/L2 if available | count/ratio of large seal orders | needs_data_pipeline | order size |
| O346 | one_word_board_count_market | P1 | local_raw_limit | auction + limit_pool | market count of true one-word boards | needs_data_pipeline | O126 |
| O347 | passive_open_board_excess | P2 | local_raw_limit | limit_pool + market state | open-board caused by market/sector weakness proxy | needs_formula_lock | cause attribution |
| O348 | reversal_board_quality | P1 | local_raw_limit | limit_pool + daily/1min | reversal-board score from prior weakness, seal quality, volume | needs_formula_lock | O253 |
| O349 | cb_stock_limit_up_premium_spread | P2 | cross_asset | cb_daily + limit_pool | convertible bond premium spread after underlying stock limit-up | needs_data_pipeline | cb proxy |
| O350 | has_convertible_bond_drag | P2 | cross_asset | cb listing map + sector_theme | flag/penalty if stock has CB or HK proxy reducing leader purity | needs_data_pipeline | O349 |

### B. Dragon / Theme Rotation / Leader Succession

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O351 | dragon_replace_signal | P1 | taoguba | sector_theme + limit_pool | old leader breaks while new theme first-board appears | needs_formula_lock | O149/O150 |
| O352 | break_node_new_dragon | P1 | taoguba | sector_theme + limit_pool | new leader candidate on day old leader limit-down/breaks | needs_formula_lock | O351 |
| O353 | supplement_rise_node | P1 | taoguba | sector_theme + limit_pool | supplement-rally start after leader break/suspension | needs_formula_lock | theme lifecycle |
| O354 | reversal_day_leader_quality | P1 | taoguba | market emotion + daily/limit | quality of strong stocks on market reversal day | needs_formula_lock | O258/O259 |
| O355 | cycle_leader_selection | P1 | taoguba | sector_theme + limit_pool | select cycle leader by board height, timing, breadth, capacity | needs_formula_lock | leader composite |
| O356 | sector_capacity_filter | P1 | taoguba | sector_theme + amount/float | theme amount or float capacity must exceed threshold | needs_data_pipeline | O144/O234 |
| O357 | sector_rotation_momentum | P1 | local_raw_theme | sector_theme + returns | change in sector momentum rank over 1-3d | needs_data_pipeline | O255 |
| O358 | sector_rotation_signal | P1 | local_raw_theme | sector_theme + returns/amount | sector turns from cold to hot: return + amount rank improvement | needs_data_pipeline | O357 |
| O359 | sector_retreat_detection | P1 | local_raw_theme | sector_theme + limit_pool | retreat/ebb condition from breadth, leader break, premium decay | needs_formula_lock | O268 |
| O360 | sector_phase_tracking | P1 | local_raw_theme | sector_theme + limit_pool | numeric phase: trial, main rise, divergence, climax, retreat | needs_formula_lock | O250 |
| O361 | sector_policy_density | P2 | event_theme | policy/news + sector_theme | policy/news event count per sector over trailing window | needs_data_pipeline | O090/O441 |
| O362 | seasonal_theme_rotation | P2 | local_raw_theme | calendar + sector_theme | recurring seasonal theme strength by calendar window | needs_formula_lock | seasonality |
| O363 | sector_heatmap_risk_mode | P2 | taoguba | sector_theme + returns | defensive sectors up while growth down = risk-off heatmap | needs_data_pipeline | broad market |
| O364 | sector_competing_yield | P2 | taoguba | sector_theme + returns | new sector strength forcing old sector concession | needs_formula_lock | subjective metaphor |
| O365 | sector_avg_amount | P1 | local_raw_theme | sector_theme + amount | 5d average amount of sector members | needs_data_pipeline | capacity |
| O366 | sector_realized_volatility_20d | P1 | local_raw_theme | sector_theme + daily/1min | sector realized volatility over 20d | needs_data_pipeline | sector_vol |
| O367 | sector_momentum_rank | P1 | local_raw_theme | sector_theme + returns | sector return rank among all themes/sectors | needs_data_pipeline | O357 |
| O368 | stock_sector_divergence | P1 | local_raw_theme | sector_theme + returns | stock return minus sector return | needs_data_pipeline | sector_divergence |
| O369 | sector_score_intraday | P1 | local_raw_theme | 1min + sector_theme | intraday sector score from breadth, volume, return | needs_data_pipeline | theme PIT |
| O370 | same_sector_switch_count | P2 | taoguba | sector_theme + trade/selection history | repeated switches within same sector as crowding/confirmation proxy | needs_data_pipeline | requires historical selections |
| O371 | follower_position_confirm | P1 | taoguba | sector_theme + limit_pool | follower positions confirm leader quality | needs_formula_lock | O246/O254 |
| O372 | leader_exit_pressure | P2 | taoguba | sector_theme + 1min/daily | leader status deterioration / exit pressure score | needs_formula_lock | trading rule risk |
| O373 | leader_daily_independence_score | P2 | taoguba | sector_theme + returns | current leader day independent of yesterday label via fresh breadth/volume | needs_formula_lock | slogan to factor |
| O374 | leader_chip_structure_proxy | P2 | taoguba | daily_ohlcv + turnover | leader chip cleanliness from turnover decay and trapped volume proxy | needs_formula_lock | O219/O375 |
| O375 | chip_digestion_cycle | P2 | taoguba | daily_ohlcv + sector_theme | days/turnover needed after theme wave for chip digestion | needs_formula_lock | theme second wave |

### C. Cost / Breakout / Reversal / Daily-Structure Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O376 | cost_deviation_wac | P2 | local_raw_cost | daily_ohlcv + turnover | (close - weighted average cost) / weighted average cost | needs_formula_lock | WAC data |
| O377 | cost_deviation_ema | P2 | local_raw_cost | daily_ohlcv | (close - EMA cost proxy) / EMA cost proxy | ready_engineering_review | moving-average duplicate |
| O378 | turnover_decay_rate | P1 | local_raw_volume | daily_ohlcv | exponential decay rate of turnover after shock/limit/breakout | ready_engineering_review | O134/O380 |
| O379 | profit_ratio_cost_distribution | P2 | local_raw_cost | daily_ohlcv + cost model | integral of volume-weighted price distribution below close | needs_formula_lock | cost distribution |
| O380 | volume_price_pivot_stability | P1 | local_raw_volume | daily_ohlcv | stability of price-volume pivot after breakout | needs_formula_lock | pivot formula |
| O381 | breakout_factor_volume_confirm | P1 | local_raw_breakout | daily_ohlcv | breakout sign * strength * volume confirmation | ready_engineering_review | O221 |
| O382 | reversal_with_volume | P1 | local_raw_breakout | daily_ohlcv | reversal signal weighted by volume zscore | ready_engineering_review | O348 |
| O383 | dynamic_volume_comparison | P2 | taoguba | daily_ohlcv + 1min optional | dynamic volume ratio vs expected full-day volume | needs_formula_lock | asof projection |
| O384 | ma5_break_exit_risk | P3 | taoguba | daily_ohlcv | 5-day MA break as negative/risk filter | ready_engineering_review | trading exit |
| O385 | min_daily_volume_300m_gate | P2 | taoguba | daily_ohlcv | liquidity gate: daily amount >= threshold, e.g. 300m | ready_engineering_review | universe filter |
| O386 | selection_priority_score | P2 | taoguba | market/theme/shape | weighted score: environment > stock habit > theme > pattern | needs_formula_lock | broad composite |
| O387 | second_board_entry_premium | P2 | taoguba | limit_pool + returns | premium/continuation behavior after second board entry condition | ready_engineering_review | O339 |
| O388 | second_break_daily_quality | P2 | taoguba | daily_ohlcv | second break above prior high/first high with volume confirm | ready_engineering_review | O160 |
| O389 | themed_sub_ipo | P2 | taoguba | listing age + sector_theme | sub-new stock aligned with current hot theme | needs_data_pipeline | O272 |
| O390 | has_cross_asset_anchor | P2 | cross_asset | CB/HK/futures/US mapping | whether stock/theme has external anchor and anchor return | needs_data_pipeline | O227-O229/O350 |

### D. Broker / Academic High-Frequency Templates Still Not Canonicalized

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O391 | apl20_tail_amount_ratio | P0 | broker_hf | 1min bars | amount in last 20min / all-day or cutoff amount | ready_engineering_review | tail amount |
| O392 | tail20_amount_residual | P1 | broker_hf | 1min bars + turnover | residual of tail20 amount ratio after turnover/size neutralization | ready_engineering_review | O391 |
| O393 | price_elasticity_recovery_speed | P1 | broker_hf | 1min bars | speed of temporary price component recovery after shock | needs_formula_lock | 广发弹性 |
| O394 | elasticity_rebound_ratio | P1 | broker_hf | 1min bars | rebound amount / initial temporary price impact | needs_formula_lock | O393 |
| O395 | voi_order_imbalance_proxy | P2 | broker_l2 | orderbook snapshots | volume order imbalance VOI | blocked_level2_or_scrape | L2 |
| O396 | oir_order_imbalance_rate | P2 | broker_l2 | orderbook snapshots | order imbalance ratio OIR | blocked_level2_or_scrape | L2 |
| O397 | mpb_midprice_basis | P2 | broker_l2 | orderbook + trades | average trade price minus bid-ask midpoint | blocked_level2_or_scrape | L2/trades |
| O398 | ras_relative_amount_spread | P2 | broker_l2 | quote/order data | relative amount spread as transaction cost | blocked_level2_or_scrape | orderbook |
| O399 | quoted_spread_cost | P2 | broker_l2 | bid/ask quote | quoted spread / midprice | blocked_level2_or_scrape | quote data |
| O400 | effective_spread_cost | P2 | broker_l2 | trade + midpoint | 2 * trade direction * (trade price - midquote) | blocked_level2_or_scrape | trade direction |
| O401 | micro_trade_size_bucket_return | P2 | broker_tick | tick trades | returns by small/mid/large/extra-large trade bucket | blocked_level2_or_scrape | tick |
| O402 | big_order_residual_ratio | P2 | broker_tick | tick/order data | residualized big-order amount ratio | blocked_level2_or_scrape | tick/order |
| O403 | long_order_residual_ratio | P2 | broker_tick | order duration | residualized long-duration order ratio | blocked_level2_or_scrape | order duration |
| O404 | early_tail_order_ratio_combo | P2 | broker_tick | tick/order data | early vs tail order-feature ratio composite | blocked_level2_or_scrape | tick/order |
| O405 | volume_diff_abs_mean | P1 | broker_hf | 1min bars | mean(abs(diff(minute_volume))) over session/window | ready_engineering_review | 长江波动时序 |
| O406 | volume_peak_count_factor | P1 | broker_hf | 1min bars | count local peaks in intraday volume series | ready_engineering_review | O318 |
| O407 | hf_volume_volatility_autocorr | P1 | broker_hf | 1min bars | autocorrelation of minute volume volatility | ready_engineering_review | O185 |
| O408 | volatility_peak_cluster_count | P1 | broker_hf | 1min bars | cluster count of local realized-volatility peaks | ready_engineering_review | volatility peaks |
| O409 | local_reversal_by_volume_bucket | P1 | broker_hf | 1min bars | reversal factor calculated separately by volume bucket | ready_engineering_review | 微观划分 |
| O410 | micro_partition_volatility_spread | P1 | broker_hf | 1min bars | volatility spread between high-volume and low-volume partitions | ready_engineering_review | high/low group |
| O411 | high_low_price_bucket_momentum | P1 | broker_hf | 1min bars | momentum conditioned on high-price vs low-price intraday buckets | ready_engineering_review | O004/O006 |
| O412 | high_low_vol_bucket_reversal | P1 | broker_hf | 1min bars | reversal conditioned on high-vol vs low-vol buckets | ready_engineering_review | O007/O012 |
| O413 | amount_distribution_asymmetry | P1 | broker_hf | 1min bars | asymmetry of intraday amount distribution across time buckets | ready_engineering_review | O391 |
| O414 | tail20_volume_concentration | P1 | broker_hf | 1min bars | last 20min volume / full-day or cutoff cumulative volume | ready_engineering_review | O391 volume version |
| O415 | morning_tail_volume_balance | P1 | broker_hf | 1min bars | first30 volume share - tail30 volume share | ready_engineering_review | O179/O180 |

### E. Sentiment / Attention / Market-State Components

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O416 | investor_sentiment_7_component_index | P2 | broker_sentiment | market turnover + fund/margin/valuation | 7-component market sentiment index as feature/gate | needs_data_pipeline | market-level |
| O417 | investor_sentiment_14_component_index | P2 | broker_sentiment | turnover + margin + IPO + fund + valuation | 14-component A-share sentiment index | needs_data_pipeline | O416 |
| O418 | margin_buy_sentiment_component | P2 | broker_sentiment | margin financing | financing buy amount / total turnover or balance change | needs_data_pipeline | margin API |
| O419 | ipo_fundraising_sentiment_component | P2 | broker_sentiment | IPO financing calendar | IPO fundraising scale as sentiment/liquidity drain | needs_data_pipeline | IPO data |
| O420 | closed_fund_discount_sentiment_component | P3 | broker_sentiment | fund discount data | closed-end fund discount as market sentiment | needs_data_pipeline | data source |
| O421 | guba_text_sentiment_dictionary | P2 | social | Guba text + sentiment dictionary | weighted sentiment score from finance-specific lexicon | blocked_level2_or_scrape | NLP |
| O422 | guba_weighted_sentiment_index | P2 | social | Guba text + read/comment weights | sentiment weighted by read/comment/like count | blocked_level2_or_scrape | NLP + scrape |
| O423 | guba_sentiment_vs_5min_volatility | P2 | social_hf | Guba + 5min bars | sentiment shock predicting/confirming 5min realized volatility | blocked_level2_or_scrape | NLP |
| O424 | attention_vs_sentiment_regime | P2 | social | attention + sentiment | regime where attention or sentiment dominates signal | blocked_level2_or_scrape | model feature |
| O425 | dragon_list_reason_type_factor | P1 | dragon_list | top_list/dragon_list | one-hot or scored LHB reason type before next day | needs_data_pipeline | reason parsing |
| O426 | dragon_list_net_buy_ratio | P1 | dragon_list | top_list/dragon_list | net_buy_amount / deal_amount or float market cap | needs_data_pipeline | O197 |
| O427 | dragon_list_turnover_reason_interaction | P1 | dragon_list | top_list/dragon_list | turnover * reason-type interaction | needs_data_pipeline | O425 |
| O428 | dragon_list_historical_reason_premium | P1 | dragon_list | top_list historical | historical next-day premium by reason type up to T-1 | needs_formula_lock | no future leakage |
| O429 | dragon_list_post_event_decay_profile | P2 | dragon_list | top_list historical | decay profile of past similar LHB events, trained only on past | needs_formula_lock | event-history |
| O430 | institutional_survey_recency_intensity | P1 | tushare_event | stk_surv | recency-weighted institutional survey intensity | needs_data_pipeline | O301 |

### F. Event / Float / Holder / Flow / Macro Additions

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O431 | research_survey_industry_cluster | P2 | event | stk_surv + sector_theme | cluster of institutional surveys inside same sector/theme | needs_data_pipeline | O430 |
| O432 | forecast_vip_surprise_sign | P1 | event | forecast_vip | positive/negative forecast revision sign and magnitude | needs_data_pipeline | O300 |
| O433 | pledge_release_risk_relief | P2 | event | pledge_stat | pledge pressure reduction / release as relief signal | needs_data_pipeline | O297 |
| O434 | share_float_unlock_supply_slope | P1 | event | share_float/unlock | slope of free-float supply / unlock pressure | needs_data_pipeline | O296 |
| O435 | ccass_hold_slope_5d | P1 | flow | ccass_hold | 5d slope of CCASS holding ratio | needs_data_pipeline | O299 |
| O436 | hsgt_top10_new_entry_rank | P1 | flow | hsgt_top10 | new entry in HSGT top10 ranked by net buy / float | needs_data_pipeline | O304 |
| O437 | industry_moneyflow_disagreement_accel | P1 | flow | moneyflow_ind_dc/ths + stock flow | acceleration of stock-sector flow disagreement | needs_data_pipeline | O059/O309 |
| O438 | shibor_slope_risk_gate | P2 | macro | shibor | SHIBOR slope/change as short-line risk gate | needs_data_pipeline | O307 |
| O439 | cb_market_turnover_risk_appetite | P2 | cross_asset | cb_daily | convertible-bond market turnover as risk-appetite proxy | needs_data_pipeline | O308 |
| O440 | global_index_volatility_gate | P2 | cross_market | index_global | overnight global volatility/risk-off filter | needs_data_pipeline | O086 |
| O441 | policy_event_density_by_theme | P2 | event_news | policy/news + sector_theme | policy/news count density mapped to theme | blocked_level2_or_scrape | news parser |
| O442 | announcement_good_bad_count_5d | P2 | event | announcements | count positive/negative announcements in trailing 5d | needs_data_pipeline | parser |
| O443 | regulatory_query_recent_flag | P2 | event | exchange announcements | recent inquiry/regulatory letter flag | needs_data_pipeline | parser |
| O444 | forecast_revision_breadth_in_theme | P2 | event_theme | forecast_vip + sector_theme | breadth of positive revisions inside theme | needs_data_pipeline | theme PIT |
| O445 | holdertrade_net_inc_cluster | P2 | event | stk_holdertrade + sector_theme | cluster of shareholder increases in theme/industry | needs_data_pipeline | O298 |
| O446 | block_trade_discount_reversal_by_size | P1 | event_flow | block_trade | block-trade discount reversal conditional on trade size | needs_data_pipeline | O194 |
| O447 | block_trade_premium_continuation | P1 | event_flow | block_trade | premium block trade followed by continuation | needs_data_pipeline | O302 |
| O448 | margin_financing_buy_ratio_stock | P2 | margin | margin detail if available | financing buy / turnover at stock level | needs_data_pipeline | margin API |
| O449 | securities_lending_pressure | P2 | margin | securities lending detail | securities lending balance/turnover as short pressure | needs_data_pipeline | margin API |
| O450 | northbound_theme_cluster_entry | P1 | flow_theme | hsgt_top10 + sector_theme | multiple same-theme stocks newly appear in HSGT top list | needs_data_pipeline | O436 |

## Status Counts

| status | count | meaning |
|---|---:|---|
| ready_engineering_review | 31 | Formula/data path is concrete enough for engineering review |
| needs_formula_lock | 28 | Needs exact threshold, stage taxonomy, or canonical formula |
| needs_data_pipeline | 46 | Requires confirmed API/cache/parser/PIT mapping |
| blocked_level2_or_scrape | 15 | Requires orderbook/tick/NLP/news/social data not yet stable |
| total | 120 | All O331-O450 candidates in this addendum |

## Best Fourth-Pass Engineering Queue

If CC is asked to review for possible C293+ promotion, prioritize:

1. Limit-board concrete features: O331-O342, O335-O341.
2. Minute/high-frequency no-L2 features: O391-O394 and O405-O415.
3. Theme candidates only after PIT sector/theme mapping: O356-O369, O431, O444, O450.
4. Tushare/event candidates after API field landing: O425-O430 and O432-O447.
5. Keep O395-O404, O421-O424, O441 blocked until L2/NLP/news pipelines are proven.

## Saturation Note

After O001-O450, the remaining raw-pool records are mostly duplicate aliases, broad strategy rules, or concepts without deterministic data paths. Further useful work should shift from "more names" to:

- canonical duplicate merge,
- engineering feasibility review,
- data pipeline availability matrix,
- formal promotion plan for C293+.

## Reference URLs

- BigQuant high-frequency factor metadata: https://mf.bigquant.com/data/datasources/cn_stock_factors_hf
- 国信高频订单成交数据: https://mf.bigquant.com/square/paper/0c28553b-c3f4-4447-9aa4-b0fbab8f8fb1
- 信达基于分钟线的高频选股因子: https://mf.bigquant.com/square/paper/39e98ab1-d13f-4a5c-960a-5a0813dca36b
- 华安高频成交额 Alpha / APL20: https://mf.bigquant.com/square/paper/389e9438-0853-4833-a1e8-b30a98ba35aa
- 广发高频弹性因子: https://mf.bigquant.com/square/paper/ac25c187-9db6-4217-b74b-3fa246ba5c24
- 长江高频波动时序信息: https://mf.bigquant.com/square/paper/39323400-a563-48a5-9ca1-fa515b48a1aa
- 中信建投高频量价 VOI/OIR/MPB: https://mf.bigquant.com/square/paper/bf950748-53cb-4c6a-9c47-923d5e92c68b
- 订单交易成本与股票收益 / 高频流动性: https://mf.bigquant.com/square/paper/d164d970-bdf4-4574-a2b5-1e93131eb979
- 龙虎榜数据字段: https://mf.bigquant.com/data/datasources/cn_stock_dragon_list
- 从涨跌停效应到行业反转: https://mf.bigquant.com/square/paper/a6dded73-c8d3-4111-9110-632e73a911a1
- Guba attention paper: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6062915
- Guba sentiment and volatility paper: https://mf.bigquant.com/square/paper/429c4224-1ffb-4df8-886e-a50db28c0ee6

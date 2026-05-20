# Four-Source Shortline Omnibus Candidate Addendum 2 2026-05-17

Scope: factor-library research only. No training, no `gpu_probe`, no model-code changes, no formal registry writes.

This is the third pass after:

- `four_source_shortline_omnibus_candidate_scan_20260517.md` covering O001-O110
- `four_source_shortline_omnibus_candidate_addendum_20260517.md` covering O111-O210

This file adds O211-O330. It focuses on remaining local raw-pool ideas that were not safe to bulk-register before, plus additional sell-side / paper / social-source patterns found in the deeper scan. These are still temporary `Oxxx` scan IDs, not official `Cxxx` registry IDs.

## Current Baseline

- Formal registry: `E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json`
- Current formal registry count: C001-C292
- Raw pool records: 3,075
- Previous temporary queue: O001-O210
- This addendum queue: O211-O330

## Third-Pass Interpretation

The remaining raw pool is not empty, but a large portion is one of:

- same concept under several names,
- trading rule / position rule rather than stock-day factor,
- formula sketch missing a deterministic threshold,
- requiring PIT theme, social, auction, LHB, or orderbook data,
- generic daily OHLCV concept that must be transformed into a short-line event or intraday version.

This file therefore records the remaining usable ideas as merged candidate concepts.

## Addendum 2 Candidate Queue

### A. Volume / Turnover / Limit-Day Quality

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O211 | volume_vs_prev_recheck | P1 | local_raw_volume | daily_ohlcv | today volume / previous-day volume with ST/new-stock filters | ready_engineering_review | generic volume ratio |
| O212 | volume_is_king_state | P1 | taoguba | market amount + stock volume | market amount regime * stock volume confirmation | needs_formula_lock | position rule wording |
| O213 | volume_health_zone | P1 | taoguba | daily_ohlcv + limit_pool | classify volume as ideal/acceptable/danger vs previous day on limit setup | needs_formula_lock | threshold bands |
| O214 | volume_board_type_classifier | P1 | taoguba | daily_ohlcv + limit_pool | classify shrink-acceleration board vs high-turnover divergence board | needs_formula_lock | board type taxonomy |
| O215 | shrink_accelerate_board_quality | P1 | taoguba | daily_ohlcv + limit_pool | limit-up with lower turnover/volume than prior active days and strong seal | ready_engineering_review | O214 subset |
| O216 | turnover_board_30min | P1 | taoguba | 1min + limit_pool | 30min turnover ratio for turnover-board confirmation | ready_engineering_review | minute turnover family |
| O217 | turnover_pct_limit_day | P1 | taoguba | daily_ohlcv + float | turnover rate on limit-up day, normalized by float | ready_engineering_review | existing turnover |
| O218 | turnover_board_vs_shrink_board | P1 | taoguba | daily_ohlcv + limit_pool | interaction: high-turnover board vs shrink board regime | needs_formula_lock | O214 |
| O219 | vacuum_ratio_chip_cleanliness | P1 | taoguba | daily_ohlcv + float | 1 - trapped_volume / float proxy, after breakout/limit setup | needs_formula_lock | chip proxy |
| O220 | trapped_volume_pressure | P2 | taoguba | daily_ohlcv | recent overhead trapped volume / float or amount | needs_formula_lock | chip proxy |
| O221 | breakout_amount_quality | P1 | taoguba | daily_ohlcv | breakout day amount relative to recent resistance-zone amount | ready_engineering_review | breakout factors |
| O222 | volume_price_health | P1 | taoguba | daily_ohlcv + limit_pool | volume expansion with price close near high / limit seal strength | ready_engineering_review | daily duplicate risk |
| O223 | close_impact_tail_3min | P1 | local_raw_minute | 1min bars | (close_or_cutoff - price_14:57) / price_14:57 | ready_engineering_review | live cutoff rule |
| O224 | final_close_gap_to_downlimit | P2 | local_raw_daily | daily_ohlcv + limit rules | close distance from down-limit after stress day | ready_engineering_review | market stress |
| O225 | open_gap_clean | P1 | local_raw_daily | daily_ohlcv | open / prev_close - 1 after event/limit filters | ready_engineering_review | generic gap |
| O226 | overnight_return_asymmetry | P1 | paper_social | daily_ohlcv + attention optional | overnight return sign/asymmetry interacted with attention or prior day | needs_formula_lock | plain overnight |
| O227 | hk_close_return_anchor | P2 | local_raw_cross | HK index close | Hang Seng / HK related index close return as A-share open anchor | needs_data_pipeline | cross-market mapping |
| O228 | us_overnight_anchor | P2 | local_raw_cross | US index/futures | US overnight index return as next-day risk anchor | needs_data_pipeline | cross-market |
| O229 | wti_theme_anchor | P2 | local_raw_cross | WTI/oil close + theme map | oil overnight move mapped to energy/petrochemical themes | needs_data_pipeline | theme mapping |
| O230 | market_amount_regime | P1 | taoguba | market amount | market total amount percentile as risk-on/risk-off regime | ready_engineering_review | broad market filter |

### B. Theme / Leader / Echelon Remaining Concepts

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O231 | sector_first_board_attr | P1 | local_raw_theme | limit_pool + sector_theme | classify first-board as solo, theme-backed, or weak hitchhike | needs_formula_lock | subjective classes |
| O232 | solo_guide_count | P1 | taoguba | limit_pool + sector/theme/name tags | count solo limit-up stocks that imply possible new directions | needs_data_pipeline | text/name mapping |
| O233 | position_stock_signal | P1 | taoguba | limit_pool + sector_theme | position stock hint for sector direction from solo/leader attributes | needs_formula_lock | solo_guide_count |
| O234 | theme_capacity_by_amount | P1 | local_raw_theme | sector_theme + amount | sum theme member 5d amount / market 5d amount | needs_data_pipeline | O144 capacity |
| O235 | theme_middle_trap_density | P1 | taoguba | sector_theme + board height | count 2-4 board non-leader stocks / theme members | needs_data_pipeline | middle crowding |
| O236 | theme_low_level_supply | P1 | taoguba | sector_theme + board height | first/second-board stock count as replenishment supply | needs_data_pipeline | theme echelon |
| O237 | theme_logic_level | P2 | taoguba | sector_theme + catalyst tags | grade theme by policy/industry/event strength | needs_data_pipeline | subjective unless tagged |
| O238 | theme_fermentation_cycle | P1 | taoguba | sector_theme + limit_pool | days from first theme limit to batch limit expansion | needs_data_pipeline | O137 cycle |
| O239 | super_theme_settlement_days | P2 | taoguba | sector_theme + returns | cooling days between first wave and second wave for major theme | needs_formula_lock | theme second wave |
| O240 | theme_second_wave_gap_days | P1 | local_raw_theme | sector_theme + limit_pool | gap between first climax and second-wave launch | needs_data_pipeline | O239 |
| O241 | sector_tier_classify | P1 | taoguba | sector_theme + board height | classify leader/mid/follower/low-level tier inside theme | needs_data_pipeline | tier taxonomy |
| O242 | sector_sustainability_score | P1 | taoguba | sector_theme + limit_pool + catalyst | score theme sustainability from independent followers, new catalyst, breadth | needs_formula_lock | broad composite |
| O243 | sector_followup_count | P1 | taoguba | sector_theme + limit_pool | same-theme other limit-up count when candidate limits | needs_data_pipeline | sector_limit count |
| O244 | sector_climax_signal | P1 | taoguba | sector_theme + limit_pool | theme climax if batch limits exceed threshold and leader accelerates | needs_formula_lock | threshold |
| O245 | sector_first_limit_density | P1 | local_raw_theme | sector_theme + limit_pool | first-board count / theme members on new theme day | needs_data_pipeline | first-board |
| O246 | theme_follower_feedback | P1 | local_raw_theme | sector_theme + returns | next-day average return of followers after leader limit-up | needs_data_pipeline | follower_drag |
| O247 | theme_leader_pull_minute | P1 | local_raw_theme | 1min + sector_theme | same-theme intraday return change after leader seals | needs_data_pipeline | PIT minute theme |
| O248 | leader_follower_premium | P1 | local_raw_theme | sector_theme + returns | leader return premium vs followers over recent cycle | needs_data_pipeline | O145 |
| O249 | leader_composite_score | P1 | local_raw_theme | sector_theme + limit_pool + amount | board height, seal time, amount, follower breadth composite | needs_formula_lock | broad composite |
| O250 | leader_lifecycle_stage | P1 | local_raw_theme | sector_theme + board/returns | emerging, accelerating, climax, weakening, revival stage | needs_formula_lock | lifecycle labels |
| O251 | leader_faith_decay | P2 | taoguba | leader history + returns | recent loss rate of pure leader chasing / board chasing | needs_formula_lock | strategy PnL proxy |
| O252 | former_leader_recall | P2 | taoguba | historical leader tags | former leader reactivation success probability | needs_data_pipeline | leader tag history |
| O253 | leader_reversal_wrap | P1 | taoguba | sector_theme + daily/1min | former leader reversal/engulfing after cooldown | needs_formula_lock | reversal pattern |
| O254 | departure_from_leader | P1 | taoguba | sector_theme + returns | follower independence from leader return correlation | needs_data_pipeline | O154 |
| O255 | money_effect_sector_rotation | P1 | taoguba | sector_theme + returns + amount | rotation into sector with recent赚钱效应 and amount inflow | needs_data_pipeline | theme rotation |

### C. Emotion Cycle / Risk Filters / Sub-New

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O256 | six_emotion_variables | P1 | taoguba | limit_pool + sector_theme | market/speculation/theme emotion composite from six variables | needs_formula_lock | broad composite |
| O257 | emotion_score_raw | P1 | taoguba | limit_pool | limit-ups - broken boards - limit-downs with board height adjustment | ready_engineering_review | emotion_score existing |
| O258 | emotion_reversal_leader_detect | P1 | taoguba | limit_pool + sector_theme | identify leader appearing near ice-point/reversal day | needs_formula_lock | leader detection |
| O259 | ice_point_new_cycle_trial | P1 | taoguba | limit_pool | ice-point condition then first-board/new-theme trial signal | ready_engineering_review | emotion cycle |
| O260 | graduation_photo_risk | P2 | taoguba | sector_theme + limit_pool | broad same-theme acceleration and one-word crowding at climax | needs_formula_lock | subjective metaphor |
| O261 | mid_position_crowding_risk | P1 | taoguba | board height + sector_theme | crowding among 2-4 board non-leaders during high emotion | needs_data_pipeline | O235 |
| O262 | one_day_trip_risk | P1 | taoguba | sector_theme + catalyst + limit_pool | no new logic + weak theme breadth + small capacity risk | needs_formula_lock | text/catalyst tags |
| O263 | no_20cm_board_filter | P2 | taoguba | limit_pool + board type | risk flag for unsupported 20cm limit-board continuation | ready_engineering_review | universe filter |
| O264 | zhaban_high_risk_avoid | P1 | taoguba | limit_pool | broken-board high-risk score from repeated failed seals and weak close | ready_engineering_review | O132 |
| O265 | passive_open_board_risk | P2 | taoguba | limit_pool | board opens due to market/sector weakness rather than healthy turnover | needs_formula_lock | subjective cause |
| O266 | asking_chase_half_position_proxy | P2 | taoguba | limit_pool + 1min | proxy for chase half-position setup: partial strength before seal | needs_formula_lock | position rule |
| O267 | empty_wait_leader_full_proxy | P3 | taoguba | sector_theme + market emotion | proxy for empty-market leader emergence; not a direct stock factor | needs_formula_lock | strategy rule |
| O268 | exit_timing_theme_climax | P2 | taoguba | sector_theme + limit_pool | theme climax day for reducing exposure, usable as negative filter | needs_formula_lock | risk filter |
| O269 | new_ipo_opening_drain | P2 | taoguba | IPO calendar + amount | new-stock open-board pressure draining speculative liquidity | needs_data_pipeline | IPO calendar |
| O270 | sub_new_board_height_ceiling | P2 | taoguba | listing age + board height | max sustainable board height for sub-new stocks in regime | ready_engineering_review | sub-new |
| O271 | sub_new_open_board_timing_v2 | P2 | taoguba | listing age + limit_pool | timing of first open after IPO consecutive boards | ready_engineering_review | O127 |
| O272 | ipo_first_day_turnover_strength | P2 | local_raw_subnew | listing + daily_ohlcv | IPO first-day turnover strength and subsequent short-line demand | needs_data_pipeline | IPO data |
| O273 | regulatory_window_escape_days | P2 | taoguba | announcement/regulatory events | days since regulatory pressure window for theme/stock | needs_data_pipeline | regulatory parser |
| O274 | regulatory_pressure_score | P2 | local_raw_event | announcement/regulatory text | count/severity of regulatory notices in trailing window | needs_data_pipeline | text parser |
| O275 | holiday_liquidity_risk | P2 | taoguba | calendar + market amount | risk filter before long holidays with weak amount and high emotion | ready_engineering_review | calendar |

### D. Social / Forum / News Attention Additions

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O276 | guba_post_read_comment_ratio | P1 | social | Guba posts/reads/comments | comments/read or posts/read as participation quality | needs_data_pipeline | O060/O201 |
| O277 | guba_topic_lifecycle_4stage | P2 | social | Guba topic model | identify topic infancy/growth/regularity/decay stage | blocked_level2_or_scrape | topic pipeline |
| O278 | guba_continuous_drop_attention | P2 | social | Guba topic model + returns | attention to continuous-drop topic as negative/reversal signal | blocked_level2_or_scrape | topic labels |
| O279 | guba_capital_reform_attention_vol | P2 | social | Guba topic model | attention to capital-market-reform topic predicting volatility | blocked_level2_or_scrape | topic labels |
| O280 | forum_attention_size_interaction | P1 | social | Guba + float/mcap | attention effect stronger for smaller/non-main-board firms | needs_data_pipeline | paper-backed |
| O281 | sentiment_liquidity_volatility_tvp | P2 | social | Guba sentiment + liquidity/vol | sentiment shock interacted with liquidity/volatility state | blocked_level2_or_scrape | NLP model |
| O282 | sentiment_down_market_asymmetry | P2 | social | Guba sentiment + market state | sentiment shock weighted more in down-market state | blocked_level2_or_scrape | NLP model |
| O283 | weibo_microblog_mood_cluster | P2 | social | Weibo posts | mood cluster from microblogs as market/theme filter | blocked_level2_or_scrape | Weibo data |
| O284 | attention_vs_sentiment_dominance | P2 | social | posts + NLP sentiment | whether attention or sentiment dominates prediction by regime | blocked_level2_or_scrape | model selection |
| O285 | news_shock_attention_gap | P2 | news_social | news + Guba | gap between news shock and forum attention response | needs_data_pipeline | news parser |
| O286 | short_video_theme_decay | P2 | social_video | short-video scrape | decay of short-video theme mentions after spike | blocked_level2_or_scrape | video platform |
| O287 | live_room_consensus_shift | P2 | social_live | live transcripts | change in live-trader consensus around theme/stock | blocked_level2_or_scrape | transcript |
| O288 | influencer_disagreement_decay | P2 | social_live | influencer posts | disagreement among high-attention accounts and decay | blocked_level2_or_scrape | identity map |
| O289 | comment_velocity_acceleration | P2 | social | timestamped comments | second derivative of post/comment velocity intraday | needs_data_pipeline | timestamp granularity |
| O290 | forum_heat_turnover_pass_through | P1 | social | Guba + 1min turnover | how much forum heat passes through into turnover acceleration | needs_data_pipeline | O061 |

### E. Data-Unlocked Tushare / API Candidate Families

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O291 | stk_factor_pro_macd_hist_change | P1 | tushare_api | stk_factor_pro | MACD histogram change / cross proximity from official technical table | needs_data_pipeline | technical duplicate |
| O292 | stk_factor_pro_kdj_extreme_repair | P1 | tushare_api | stk_factor_pro | KDJ oversold/overbought repair state with short-line filters | needs_data_pipeline | technical duplicate |
| O293 | stk_factor_pro_boll_squeeze_break | P1 | tushare_api | stk_factor_pro | BOLL bandwidth compression then price break | needs_data_pipeline | BOLL duplicate |
| O294 | stk_factor_pro_rsi_divergence_short | P1 | tushare_api | stk_factor_pro | short-window RSI divergence vs price | needs_data_pipeline | technical duplicate |
| O295 | adj_factor_event_jump | P2 | tushare_api | adj_factor | abnormal adjustment-factor jump / corporate action event guard | needs_data_pipeline | mostly filter |
| O296 | share_float_supply_shock | P1 | tushare_api | share_float | free-float supply jump or restricted-share unlock pressure | needs_data_pipeline | unlock family |
| O297 | pledge_stat_pressure_change | P2 | tushare_api | pledge_stat | pledge ratio change and risk pressure | needs_data_pipeline | slow event |
| O298 | stk_holdertrade_net_change | P1 | tushare_api | stk_holdertrade | shareholder net increase/decrease over recent window | needs_data_pipeline | insider signal |
| O299 | ccass_hold_change_hkfloat | P1 | tushare_api | ccass_hold | CCASS holding change scaled by free float | needs_data_pipeline | HK connect/foreign |
| O300 | forecast_vip_revision_intensity | P1 | tushare_api | forecast_vip | magnitude/frequency of earnings forecast revisions | needs_data_pipeline | PEAD |
| O301 | stk_surv_institutional_attention | P1 | tushare_api | stk_surv | institutional survey count/recency change | needs_data_pipeline | research_surge |
| O302 | block_trade_premium_aftershock | P1 | tushare_api | block_trade | block-trade premium/discount followed by intraday aftershock | needs_data_pipeline | O194 |
| O303 | block_trade_buy_sell_pressure | P1 | tushare_api | block_trade | buy/sell side pressure from block trade amount and discount | needs_data_pipeline | O195/O196 |
| O304 | hsgt_top10_rank_new_entry | P1 | tushare_api | hsgt_top10 | newly appearing HSGT top10 net-buy stock flag and rank | needs_data_pipeline | O057/O089 |
| O305 | moneyflow_hsgt_5d_acceleration | P1 | tushare_api | moneyflow_hsgt | 5d acceleration in northbound/southbound flow | needs_data_pipeline | flow acceleration |
| O306 | index_dailybasic_sentiment_gate | P2 | tushare_api | index_dailybasic | index turnover/valuation/liquidity gate for short-line risk | needs_data_pipeline | market filter |
| O307 | shibor_risk_appetite_gate | P2 | tushare_api | shibor | SHIBOR liquidity environment as risk-appetite gate | needs_data_pipeline | macro slow |
| O308 | cb_daily_risk_appetite_proxy | P2 | tushare_api | cb_daily | convertible-bond market activity as speculative appetite proxy | needs_data_pipeline | cross asset |
| O309 | moneyflow_ind_sector_rotation | P1 | tushare_api | moneyflow_ind_dc/ths | industry moneyflow rotation acceleration | needs_data_pipeline | O058/O059 |
| O310 | ggt_daily_southbound_theme_anchor | P2 | tushare_api | ggt_daily | southbound/HK channel flow as theme anchor for A/H related stocks | needs_data_pipeline | sparse |

### F. Additional Broker / Academic High-Frequency Templates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O311 | volume_surge_moment_bright_volatility | P0 | broker_hf | 1min bars | volatility at minute-level volume surge moments | ready_engineering_review | 方正耀眼波动率 |
| O312 | volume_surge_moment_bright_return | P0 | broker_hf | 1min bars | return at minute-level volume surge moments | ready_engineering_review | 方正耀眼收益率 |
| O313 | moderate_adventure_composite | P0 | broker_hf | 1min bars | composite of surge-moment volatility and surge-moment return | needs_formula_lock | O311/O312 |
| O314 | order_size_large_trade_ratio | P2 | broker_tick | tick/order data | large-order trade amount / total amount by segment | blocked_level2_or_scrape | tick data |
| O315 | long_duration_order_ratio | P2 | broker_tick | order data | amount ratio of long-duration orders | blocked_level2_or_scrape | order data |
| O316 | order_quote_aggressiveness_ratio | P2 | broker_tick | order/trade data | aggressive quote/order ratio by buy/sell side | blocked_level2_or_scrape | tick/order |
| O317 | micro_segment_return_skew_by_time | P1 | broker_hf | 1min bars | return skewness by early/mid/late segment | ready_engineering_review | realized skew |
| O318 | volume_peak_count_factor | P1 | broker_hf | 1min bars | count of abnormal volume peaks in trailing window | ready_engineering_review | Kaiyuan peak |
| O319 | volume_ridge_count_factor | P1 | broker_hf | 1min bars | count/length of sustained high-volume ridges | ready_engineering_review | O165/O186 |
| O320 | volume_valley_count_factor | P1 | broker_hf | 1min bars | count/length of low-volume valleys after price shock | ready_engineering_review | O167 |
| O321 | hf_suffix_early5_vs_tail5_spread | P1 | broker_hf | 1min bars | difference between early-5min and tail-5min factor values | ready_engineering_review | BigQuant suffix windows |
| O322 | tail15_trend_strength | P1 | broker_hf | 1min bars | trend strength over tail 15min window | ready_engineering_review | trend_strength |
| O323 | morning60_trend_strength | P1 | broker_hf | 1min bars | trend strength over first 60min window | ready_engineering_review | trend_strength |
| O324 | all_day_trend_strength_ratio | P1 | broker_hf | 1min bars | all-day trend strength normalized by volatility/noise | ready_engineering_review | O024 |
| O325 | micro_reversal_by_order_size | P2 | broker_tick | tick/order data | reversal conditioned on small/mid/large order group | blocked_level2_or_scrape | tick data |
| O326 | micro_volatility_by_trade_direction | P2 | broker_tick | tick/trade direction | volatility split by active buy vs active sell trades | blocked_level2_or_scrape | tick data |
| O327 | liquidity_premium_time_weighted | P2 | broker_l2 | orderbook | liquidity premium with time-weighted depth/cost | blocked_level2_or_scrape | orderbook |
| O328 | liquidity_premium_vol_weighted | P2 | broker_l2 | orderbook + volatility | liquidity premium weighted by volatility state | blocked_level2_or_scrape | orderbook |
| O329 | orderbook_convexity_proxy | P2 | academic_l2 | orderbook | bid/ask depth convexity and spread relation | blocked_level2_or_scrape | orderbook |
| O330 | hf_market_microstructure_noise_commonality | P2 | academic_hf | 1min all-stock bars | stock microstructure noise co-movement with market-wide noise | needs_formula_lock | noise estimator |

## Status Counts

| status | count | meaning |
|---|---:|---|
| ready_engineering_review | 27 | Formula/data path is concrete enough for engineering review |
| needs_formula_lock | 26 | Requires exact threshold, state label, or canonical formula |
| needs_data_pipeline | 49 | Requires confirmed API/cache/scrape/PIT mapping |
| blocked_level2_or_scrape | 18 | Requires tick/orderbook/social/NLP pipeline not yet proven |
| total | 120 | All O211-O330 candidates in this addendum |

## Strongest Near-Term Queue

If the next CC task is candidate engineering review, prioritize:

1. O211-O230 except cross-market anchors O227-O229 if data is not ready.
2. O257, O259, O263, O264, O270-O271, O275 for emotion/risk filters with clear data paths.
3. O311-O313 and O317-O324 for 1min high-frequency factor expansion.
4. O291-O310 only after Tushare proxy field landing and asof verification.
5. O231-O255 only after PIT theme/sector mapping is reliable.

## Remaining Not Fully Scanned / Not Suitable For Bulk Registry

Even after O001-O330, some raw pool concepts remain intentionally outside the candidate queue:

- Pure trading rules such as direct仓位管理, stop-loss discipline, or "full position" commands.
- Text-only concepts without stock-day timestamp, data field, or formula.
- Near-duplicates already represented by a canonical O candidate.
- Orderbook/tick variants that cannot be supported by current stable data.
- Social/video/live-room concepts without a repeatable scrape and timestamp pipeline.

## Source Notes

- BigQuant high-frequency factor metadata motivates intraday window splits such as early 5min, early 15min, early 30min, morning, afternoon, tail 5/15/30min, and trend-strength definitions.
- 方正证券成交量激增报告 motivates volume-surge moment volatility/return and the combined moderate-adventure idea.
- 国信证券高频订单报告 motivates order-size and long-duration order ratios, but these require tick/order data.
- 中信建投 MCI reports and orderbook convexity papers motivate orderbook liquidity candidates, but they stay blocked until stable orderbook data exists.
- SSRN/Guba and arXiv sentiment papers motivate attention topic, sentiment-liquidity-volatility, and down-market asymmetry candidates.
- Taoguba emotion-cycle pages motivate cycle-stage, ice-point, climax, board-height, broken-board, and theme-ladder variables.

## Reference URLs

- BigQuant high-frequency factor metadata: https://mf.bigquant.com/data/datasources/cn_stock_factors_hf
- 方正证券成交量激增 Alpha summary: https://mf.bigquant.com/square/paper/62ec0ac7-6e47-4322-a771-777c135b5118
- 国信证券高频订单成交数据 summary: https://mf.bigquant.com/square/paper/0c28553b-c3f4-4447-9aa4-b0fbab8f8fb1
- 高频波动时间序列信息: https://mf.bigquant.com/square/paper/39323400-a563-48a5-9ca1-fa515b48a1aa
- 光大证券 K线最短路径非流动性: https://bigquant.com/square/paper/b1fcee1b-3789-413e-aef4-4d44e566794e
- 买卖报单流动性 MCI: https://bigquant.com/square/paper/ab6f3379-a409-4972-8fd0-16299e14a569
- Order flow around extreme price changes: https://arxiv.org/abs/1003.0168
- Order-book convexity in China: https://arxiv.org/abs/1211.2078
- Guba retail topic attention: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6062915
- Eastmoney Guba BERT sentiment/liquidity/volatility: https://arxiv.org/abs/2205.05719
- Taoguba emotion-cycle reference: https://m.tgb.cn/a/2fkXr39k0Ds?type=new

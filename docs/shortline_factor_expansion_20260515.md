# Short-Line Factor Expansion (2026-05-15)

## Summary

- Added batch: `candidates_20260515_shortline_full_expansion`
- Added IDs: `C223-C292`
- Added candidates: 70
- Priority split: P0=26, P1=33, P2=11
- Scope: factor-library only. No training, no gpu_probe, no model code change.
- Local raw pool re-screened: 3075 records, with data-unlocked items reconsidered.

## Source Evidence

- local_raw_factor_pool: E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json (3075 local short-line factor records re-screened with newly available data sources.)
- tgb_weak_to_strong: https://www.tgb.cn/a/2rlgmUsdvAp-1 (Weak-to-strong and divergence-to-consensus logic converted into auction/open/sector-linkage factors.)
- dolphindb_worldquant_101: https://docs.dolphindb.cn/en/docs/Tutorials/wq101alpha.html (Formulaic alpha family using open/high/low/close/volume/vwap and industry information.)
- china_high_frequency_liquidity: https://www.sciencedirect.com/science/article/abs/pii/S0927538X25000186 (Chinese high-frequency liquidity paper motivates 1min/5min/10min periodicity and price-impact/liquidity factors.)
- a_share_internet_sentiment_overtrading: https://arxiv.org/abs/2404.12001 (A-share forum sentiment and intraday overtrading interaction motivates social-attention candidates.)
- zhongtai_lhb_seat_flow_report: https://bigdata-s3.wmcloud.com/researchreport/2023-07/23c324011b7b823c1b93f44ee9e252b5.pdf (Dragon-tiger list seat quality and seat-flow momentum motivate LHB/seat factors.)

## Added Candidates

| ID | Name | Priority | Family | Data Need | Definition | Status |
|----|------|----------|--------|-----------|------------|--------|
| C223 | sector_change_intensity_real | P0 | sector_event | sector/theme intraday events + sector flow + members | zscore(event_count_theme_day) + zscore(theme_main_inflow_rate) + zscore(active_member_ratio) | needs_sector_intraday_event_snapshot |
| C224 | theme_breadth_real | P0 | sector_event | theme members + member returns/limit pool | count(theme_member_return > 0 or limit_up) / theme_member_count | needs_theme_member_point_in_time_join |
| C225 | market_emotion_temp_score | P1 | market_emotion | limit_pool + market breadth + turnover | limit_up_count/10 + advance_decline_ratio*5 + market_turnover_ratio_20d*2 - limit_down_count/5 + max_board_height*0.5 | needs_formula_lock_weights |
| C226 | institution_trend_buy_yin | P1 | lhb_pattern | daily OHLCV + top_list/top_inst | I(stock in uptrend and red/negative daily candle) * recent_lhb_institution_net_buy_rate | needs_lhb_backfill |
| C227 | pullback_from_high_ratio | P0 | price_structure | daily OHLCV | 1 - close / rolling_max(high, N) | engineerable_now |
| C228 | breakout_sign_new_high_low | P0 | price_structure | daily OHLCV | sign(close_t - rolling_max(high, N, exclude_today)) with -1 if close_t < rolling_min(low, N, exclude_today) | engineerable_now |
| C229 | dragon_tiger_net_buy_ratio | P0 | lhb | top_list/top_inst | lhb_net_buy_amount / daily_amount for LHB-listed stocks; missing with availability flag otherwise | needs_lhb_backfill |
| C230 | board_height_score_market | P1 | board_structure | limit_pool | today_max_board_height / rolling_mean(today_max_board_height, N) | engineerable_if_limit_pool_history_complete |
| C231 | avg_seal_time_market | P1 | board_structure | limit_pool first_seal_time | mean(first_seal_minutes for limit-up stocks) | engineerable_if_limit_pool_history_complete |
| C232 | theme_uniqueness_score | P0 | sector_structure | limit_pool + theme membership | 1 / (same_theme_limit_up_count + 1) | needs_theme_member_point_in_time_join |
| C233 | anomaly_200_buy_sell_imbalance | P2 | announcement_event | announcement/regulatory event + minute/daily liquidity | I(regulatory_200pct_event_recent) * post_event_buy_sell_imbalance_proxy | needs_event_source_and_formula_lock |
| C234 | announcement_signal_decay | P1 | announcement_event | announcement timestamp + event type | exp(-lambda * hours_since_disclosure) * event_strength_score | needs_announcement_timestamp_pipeline |
| C235 | policy_density_sector | P2 | policy_event | policy/news event tags + sector mapping | count(policy_events_for_sector in trailing N days) / N | needs_policy_event_tag_pipeline |
| C236 | lhb_buy_sell_ratio | P0 | lhb | top_list/top_inst | lhb_buy_top5_total / (lhb_sell_top5_total + eps) | needs_lhb_backfill |
| C237 | seat_premium_score | P0 | lhb_seat | seat history + top_list/top_inst | sum(seat_net_buy_amount * rolling_seat_winrate_weight) / daily_amount | needs_seat_history_backfill |
| C238 | famous_seat_decay | P1 | lhb_seat | seat history + top_list/top_inst | famous_seat_net_buy_score * exp(-days_since_famous_seat_appearance / tau) | needs_seat_history_backfill |
| C239 | seat_style_vector | P1 | lhb_seat | seat history + post-event return statistics | dot(current_stock_seat_net_buy_vector, historical_seat_style_return_vector) | needs_seat_history_backfill |
| C240 | announcement_sentiment_factor | P2 | announcement_event | structured announcement or NLP score + timestamp | sum(event_score_i * recency_weight_i) / count(events) | needs_nlp_or_structured_event_pipeline |
| C241 | pead_sue_drift | P1 | earnings_event | forecast/express/fina_indicator | standardized_unexpected_earnings * I(days_since_announcement <= 60) | needs_financial_event_backfill |
| C242 | friday_announcement_drift | P2 | earnings_event | forecast/express/fina_indicator | standardized_unexpected_earnings * I(announcement_weekday == Friday) | needs_financial_event_backfill |
| C243 | etf_creation_redemption_pressure | P2 | cross_market_flow | ETF creation/redemption records + constituent mapping | net_etf_creation_amount_mapped_to_stock / stock_float_mv | needs_etf_flow_source |
| C244 | seal_time_bucket | P0 | limit_intraday | 1min bars + limit price | bucket(first_time(close >= up_limit)): 09:25, <=10:00, <=10:30, AM, PM, none | needs_1min_backfill |
| C245 | rotten_board_duration | P1 | limit_intraday | 1min bars + limit price | count(minutes after first limit touch where close < up_limit) and/or max continuous open duration | needs_1min_backfill |
| C246 | reseal_strength_real | P0 | limit_intraday | 1min bars + limit price + volume | 1/(minutes_to_reseal+1) * volume_on_reseal / mean(volume_before_reseal) | needs_1min_backfill |
| C247 | board_type_intraday | P1 | limit_intraday | 1min bars + limit price | categorical one-word/T/turnover/rotten encoded from open/high/low/close vs up_limit and open duration | needs_1min_backfill |
| C248 | attack_volume_at_limit | P0 | limit_intraday | 1min bars + limit price | volume in final upward push before first limit touch / max(rolling minute volume before push) | needs_1min_backfill |
| C249 | first_seal_time_rank_in_theme | P0 | limit_theme | 1min/limit pool + theme membership | rank(first_seal_time within same theme) normalized by theme limit-up count | needs_1min_and_theme_join |
| C250 | passive_open_board_beta | P1 | limit_theme | 1min bars + index/theme minute returns + limit price | I(stock opens board) * negative(theme_or_index_return_during_open_window) | needs_1min_and_theme_minute_join |
| C251 | active_rally_against_market | P1 | intraday_relative_strength | 1min stock bars + index/theme minute bars | stock_return_during_attack_window - beta * index_or_theme_return_same_window | needs_1min_and_index_minute_join |
| C252 | board_volume_acceptance | P0 | limit_intraday | 1min bars + limit price | volume_at_or_near_limit / (volume_below_limit_after_first_touch + eps) | needs_1min_backfill |
| C253 | long_seal_late_break_risk | P1 | limit_intraday | 1min bars + limit price | I(sealed_duration_before_14:30 >= 120min and open_board_after_14:30) | needs_1min_backfill |
| C254 | seal_before_1030_flag | P0 | limit_intraday | 1min bars + limit price | I(first_seal_time <= 10:30) | needs_1min_backfill |
| C255 | dynamic_volume_comparison_score | P0 | intraday_volume | 1min bars + historical 1min volume | max(volume_today_1min / same_clock_median_volume_Nd, volume_today_1min / rolling_max_volume_Nd) | needs_1min_backfill |
| C256 | second_wave_failure_ratio | P1 | intraday_pattern | 1min bars | second_rally_peak / first_rally_peak with failure flag if < 1 and late-session weakness | needs_intraday_wave_parser |
| C257 | late_weak_rally_failure | P1 | intraday_pattern | 1min bars | late_session_attempt_return - post_attempt_drawdown, negative if rally fails before close | needs_1min_backfill |
| C258 | first_min_direction | P0 | intraday_open | 1min bars | sign(close_09:31 - open_09:30) | needs_1min_backfill |
| C259 | first_min_flush_strength | P1 | intraday_open | 1min bars + previous-day minute bars | (open_09:30 - low_first_minute) / previous_day_max_minute_range | needs_1min_backfill |
| C260 | auction_amount_vs_prev_max_bar | P0 | auction_intraday | auction amount + previous-day 1min bars | auction_amount / max(previous_day_1min_amount) | needs_auction_and_1min_backfill |
| C261 | weak_to_strong_auction_confirm | P0 | auction_limit_theme | previous-day board weakness + auction + first 10min + theme | I(prev_rotten_or_broken_or_tail_weak) * z(auction_gap) * z(auction_volume_ratio) * I(first_10min_strength_or_seal) * theme_linkage_score | needs_auction_1min_theme_join |
| C262 | one_word_board_assist | P1 | limit_theme | limit pool + theme membership | count(one_word_limit_up_stocks in same theme) / theme_member_count | needs_theme_limit_join |
| C263 | sector_intraday_event_count | P0 | sector_event | stock_board_change_em or equivalent sector event snapshot | count(sector intraday change events by theme/date) | needs_sector_event_snapshot |
| C264 | sector_main_inflow_event_score | P0 | sector_event | sector event snapshot + sector flow | zscore(sector_main_inflow) * log1p(sector_event_count) | needs_sector_event_snapshot |
| C265 | large_buy_event_count | P1 | intraday_event | stock intraday event feed | count(large-buy events for stock before cutoff) | needs_stock_intraday_event_snapshot |
| C266 | open_limit_event_count | P1 | intraday_event | stock intraday event feed + limit price | count(open-limit/broken-limit events for stock before cutoff) | needs_stock_intraday_event_snapshot |
| C267 | auction_rise_event_count | P1 | intraday_event | stock intraday event feed + auction | count(auction-rise events for stock/date) | needs_stock_intraday_event_snapshot |
| C268 | intraday_event_intensity | P0 | intraday_event | stock intraday event feed | weighted_count(large_buy, rocket_launch, fast_rebound, limit_open, limit_seal events) | needs_stock_intraday_event_snapshot |
| C269 | sector_first_board_attribute | P1 | limit_theme | limit pool + theme membership | one-hot/scores for first board being sole seed, theme-linked, or hype-following based on same-theme board count | needs_theme_limit_join |
| C270 | second_board_confirm_leader | P0 | limit_theme | limit pool + theme membership | I(board_count == 2 and rank(first_seal_time within theme) <= top_k and theme_breadth_above_threshold) | needs_theme_limit_join |
| C271 | board_echelon_cluster_strength | P1 | limit_theme | limit pool + theme/region membership | HHI or count concentration of limit-up board heights within same theme/region echelon | needs_theme_region_mapping |
| C272 | turnover_board_real | P0 | limit_intraday | limit pool + daily turnover + auction | I(first_seal_time > 09:25) * turnover_rate * I(open_board_count within acceptable range) | needs_limit_pool_field_backfill |
| C273 | limit_up_last_min_seal | P1 | limit_intraday | 1min bars + limit price | I(first_or_final_seal_time >= 14:55) | needs_1min_backfill |
| C274 | intraday_pressure_weighted | P1 | intraday_cost | minute VWAP/volume + close | sum(volume_i * max(vwap_i - close_t, 0) * decay_i) / (sum(volume_i) * close_t) | needs_1min_or_5min_backfill |
| C275 | cgo_a_cost_gain_overhang | P1 | intraday_cost | minute VWAP/volume + daily turnover | (close_t - sum(weight_tau * vwap_tau)) / close_t, weights based on turnover decay | needs_turnover_decay_formula_lock |
| C276 | ema_cost_anchor_gap | P1 | intraday_cost | minute VWAP + turnover | (close_t - EMA(vwap, alpha=1/avg_turnover)) / close_t | needs_turnover_decay_formula_lock |
| C277 | trapped_value_weighted | P1 | intraday_cost | minute VWAP/volume + close | sum(volume_i * I(vwap_i > close_t) * decay_i) / sum(volume_i) | needs_1min_or_5min_backfill |
| C278 | wq_volume_price_decay_rank | P0 | formulaic_alpha | daily OHLCV + VWAP | rank(decay_linear(correlation(vwap, volume, short_window), decay_window)) with sign chosen by validation | engineerable_now_if_vwap_available |
| C279 | wq_sign_volume_return | P0 | formulaic_alpha | daily OHLCV + volume | sign(delta(volume, 1)) * (-delta(close, 1)) or equivalent WQ sign-volume-return transform | engineerable_now |
| C280 | wq_intraday_range_close_open | P1 | formulaic_alpha | daily OHLCV | (close - open) / (high - low + eps) with cross-sectional neutralization option | engineerable_now |
| C281 | wq_vwap_rank_reversal | P1 | formulaic_alpha | daily OHLCV + VWAP | -rank(delta(vwap, N)) * rank(delta(close, N)) | engineerable_now_if_vwap_available |
| C282 | intraday_w_shape_liquidity_deviation | P0 | intraday_liquidity | 1min/5min bars | distance of stock intraday volume/liquidity curve from market W-shape baseline | needs_1min_backfill_and_market_baseline |
| C283 | minute_periodicity_energy_1_5_10 | P1 | intraday_liquidity | 1min bars | spectral/variance energy of volume or return at 1/5/10-minute periodic components | needs_1min_backfill |
| C284 | opening_closing_volume_imbalance | P1 | intraday_liquidity | 1min/5min bars | (volume_open_30min - volume_close_30min) / total_volume | needs_1min_backfill |
| C285 | liquidity_price_impact_proxy | P1 | intraday_liquidity | 1min bars | abs(return_window) / (amount_window + eps), averaged over intraday windows | needs_1min_backfill |
| C286 | sentiment_overtrading_interaction | P2 | social_sentiment | forum/social sentiment + intraday volume | zscore(social_sentiment) * zscore(intraday_turnover_vs_baseline) | needs_social_sentiment_pipeline |
| C287 | guba_heat_volume_amplification | P2 | social_sentiment | Eastmoney Guba or similar post/comment counts + intraday volume | zscore(post_count_growth) * zscore(volume_acceleration_1min) | needs_social_scrape_pipeline |
| C288 | short_video_attention_shock | P2 | social_sentiment | Bilibili/Douyin/short-video mention counts if timestamped scrape exists | abnormal_growth(video_mentions_or_views for stock/theme) over trailing N hours/days | needs_short_video_scrape_pipeline |
| C289 | social_leader_mention_breadth | P2 | social_sentiment | social posts mapped to stock/theme | unique_author_count_mentioning_stock_or_theme / rolling_baseline_unique_authors | needs_social_scrape_pipeline |
| C290 | halt_reopen_volume_relaxation | P2 | trading_halt_event | suspend/resume events + minute/daily bars | post_resume_volume_peak * exp_decay_fit_or_ratio(first_window_volume / later_window_volume) | needs_suspend_resume_source |
| C291 | halt_reopen_abs_return_decay | P2 | trading_halt_event | suspend/resume events + minute/daily bars | abs_return_first_window / (abs_return_later_window + eps) after reopen | needs_suspend_resume_source |
| C292 | auction_true_order_after_0920 | P1 | auction_microstructure | auction snapshots at/after 09:20 | auction_buy_pressure_after_0920 / auction_buy_pressure_before_0920 or final_valid_order_ratio | needs_auction_snapshot_pipeline |

## Data Backlog

| Source | Priority | Unlocks | Current Status |
|--------|----------|---------|----------------|
| stk_mins 1min | P0 | C244-C261, C273-C285 plus C189-C193 | missing cache |
| limit_pool with first/final seal/open count fields | P0 | C223-C232, C244-C254, C262-C273 | existing but field coverage/asof must be verified |
| theme/sector membership point-in-time join | P0 | C223-C224, C232, C249-C250, C262-C264, C269-C271 | needs join/catalog |
| top_list/top_inst and seat history | P0 | C226, C229, C236-C239 | Tushare top_list/top_inst partially cached; seat history may need AKShare/EM scrape |
| stock/sector intraday event snapshots | P1 | C223, C263-C268 | needs stock_changes_em/stock_board_change_em style snapshot pipeline |
| auction final plus auction snapshots after 09:20 | P1 | C260-C261, C292 | final auction exists; 09:20 snapshot not verified |
| forecast/express/fina_indicator announcement events | P1 | C241-C242 | partial; exact ann_time/asof recommended |
| announcement/policy NLP event pipeline | P2 | C233-C235, C240 | not standardized |
| ETF creation/redemption | P2 | C243 | source not verified |
| social/forum/short-video timestamped scrape | P2 | C286-C289 | not standardized |
| suspend/resume event source | P2 | C290-C291 | not verified |

## Important Exclusions

- True L2 orderbook/tick/cancel factors are still not registered unless a minute/event proxy exists.
- Pure discretionary strategy language is not registered unless it has a deterministic numeric definition.
- Future-outcome formulas such as post-event CAR are not registered in their leaked form.
- Social/Bilibili/Douyin candidates are registered only as P2 research candidates until timestamped scrape pipelines exist.

## Audit Addendum 2026-05-15

This batch remains a research-candidate expansion, not a final training set.

- Do not hand off all 70 candidates at once.
- Prioritize first-wave-after-data IDs: C229, C236, C244, C246, C247, C248, C252, C254, C258, C259, C260, C270, C272, C273, C279, C280.
- C278/C279/C280 definitions were tightened in `factor_registry.json`.
- Entries with `formula_lock_required`, `window_lock_required`, or `external_pipeline_required` must be resolved before training.
- Full audit: `docs/factor_registry_audit_20260515.md`.

# Global Deep Short-Line Factor Search 2026-05-17

Scope: factor-library only. No training, no gpu_probe, no model or frozen config changes.

## Search Surface

- `haitong_hf`: Haitong high-frequency factor reports: minute skew, downside volatility share, tail volume share, price-volume correlation, improved reversal and large-order push logic.
- `citic_hf`: CITIC high-frequency price-volume report: VOI/OIR/MPB families; only low-frequency/minute-bar-safe proxies are admitted here.
- `qlib`: Microsoft Qlib Alpha158/Alpha360 feature handler family, rewritten into explicit cutoff-safe formulas.
- `worldquant`: 101 Formulaic Alphas family, only simple OHLCV/VWAP formulas with explicit asof controls are admitted.
- `academic_intraday`: Academic intraday momentum/order-imbalance literature; converted to minute-bar features only when L2 is not required.
- `local_canonical`: Local canonical registry audit and O001-O450 queue, deduped against C001-C292.
- `local_raw`: Local raw factor pool residual audit, deduped against formal registry and O queue.
- `data_unlocked`: Tushare proxy sources already audited locally: stk_mins_1, stk_mins_5, top_list, block_trade, share_float, forecast_vip, stk_surv, hsgt_top10, ccass_hold and industry moneyflow caches.

## Added To Registry

- Batch: `candidates_20260517_global_deep_search`
- Count: 49
- ID range: `C293-C341`
- Priority counts: {'P0': 24, 'P1': 23, 'P2': 2}
- Family counts: {'minute_hf': 22, 'minute_market': 2, 'auction_open': 3, 'limit_board': 8, 'lhb': 1, 'block_trade': 2, 'unlock_float': 1, 'pledge': 1, 'forecast_event': 1, 'research_event': 1, 'northbound_flow': 2, 'industry_flow': 1, 'formulaic_alpha': 3, 'cross_market': 1}

| ID | Name | Priority | Family | Data Need | Status | Asof |
|---|---|---|---|---|---|---|
| C293 | hf_downside_volatility_share | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C294 | hf_realized_skewness_20d | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C295 | hf_realized_kurtosis_20d | P2 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C296 | tail_volume_share_1457 | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C297 | intraday_price_volume_corr | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C298 | intraday_pv_corr_segment_shift | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C299 | improved_intraday_reversal_1000_to_1457 | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C300 | large_amount_bar_push_return | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C301 | high_price_volume_share | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C302 | low_price_absorption_repair | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C303 | same_clock_return_surprise_z | P0 | minute_hf | 1min bars + trailing same-clock history | engineerable_after_1min_cache_and_history | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C304 | intraday_trend_smoothness | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C305 | shock_volume_decay_half_life | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C306 | shock_price_reversal_efficiency | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C307 | intraday_market_beta_20d | P1 | minute_hf | 1min stock bars + index/all-stock minute return | engineerable_after_1min_and_market_minute_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C308 | intraday_idio_vol_share | P1 | minute_hf | 1min stock bars + index/all-stock minute return | engineerable_after_1min_and_market_minute_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C309 | minute_market_breadth_thrust | P0 | minute_market | 1min all-stock bars | engineerable_after_1min_universe_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C310 | cross_sectional_minute_momentum_rank | P0 | minute_market | 1min all-stock bars | engineerable_after_1min_universe_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C311 | first5_vwap_hold_ratio | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C312 | minute_opening_range_breakout_quality | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C313 | vwap_reclaim_count | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C314 | shortest_path_illiquidity_intraday | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C315 | intraday_volume_entropy | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C316 | late_breakout_fail_probability | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C317 | weak_to_strong_open_reclaim | P0 | auction_open | 1min bars + previous board/weakness tag | engineerable_after_1min_and_prev_state_tag | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C318 | auction_open_to_first5_reclaim | P1 | auction_open | auction final + 1min bars | engineerable_after_auction_snapshot_verified | Auction fields known after 09:25 plus 1min bars <=09:35; safe if auction data is a preopen snapshot, not revised post-close. |
| C319 | auction_false_strength_risk | P1 | auction_open | auction final + 1min bars | engineerable_after_auction_snapshot_verified | Auction fields known after 09:25 plus 1min bars <=09:35; safe if auction data is a preopen snapshot, not revised post-close. |
| C320 | market_open_board_rate | P0 | limit_board | limit pool with open-board/broken-board timestamp | engineerable_if_limit_pool_has_event_time | Use only limit/board events timestamped <= 14:57; if event time is not available, shift to T-1. |
| C321 | market_limit_attempt_count | P0 | limit_board | limit pool events | engineerable_if_limit_pool_has_event_time | Use only limit/board events timestamped <= 14:57; if event time is not available, shift to T-1. |
| C322 | board_height_compression_speed | P0 | limit_board | limit_list_d or limit pool board height history | engineerable_if_limit_pool_history_complete | Use only limit/board events timestamped <= 14:57; if event time is not available, shift to T-1. |
| C323 | broken_board_loss_diffusion | P0 | limit_board | broken-board list + returns | engineerable_if_limit_pool_has_break_status | Use only limit/board events timestamped <= 14:57; if event time is not available, shift to T-1. |
| C324 | first_board_to_second_board_conversion | P0 | limit_board | limit_list_d with board_count history | engineerable_if_limit_pool_history_complete | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C325 | high_board_survival_rate_3d | P0 | limit_board | limit_list_d with board_count history | engineerable_if_limit_pool_history_complete | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C326 | seal_rate_collapse_3d | P0 | limit_board | limit pool with seal/break status | engineerable_if_limit_pool_has_break_status | Use only limit/board events timestamped <= 14:57; if event time is not available, shift to T-1. |
| C327 | seal_money_to_float_mv | P1 | limit_board | limit pool seal amount + share_float | engineerable_if_limit_pool_has_seal_amount | Use only limit/board events timestamped <= 14:57; if event time is not available, shift to T-1. |
| C328 | lhb_net_buy_to_float | P0 | lhb | top_list/top_inst + share_float | engineerable_after_lhb_backfill | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C329 | block_trade_discount_persistence_5d | P0 | block_trade | block_trade + daily close | engineerable_after_block_trade_backfill | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C330 | block_trade_seller_concentration | P1 | block_trade | block_trade with seller party if present | engineerable_if_block_trade_party_fields_exist | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C331 | unlock_pressure_to_adv_30d | P1 | unlock_float | share_float/unlock schedule + daily volume | engineerable_if_unlock_schedule_available | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C332 | pledge_release_acceleration | P1 | pledge | pledge_stat + share_float | engineerable_after_pledge_backfill | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C333 | forecast_revision_dispersion_change | P1 | forecast_event | forecast_vip/express_vip | engineerable_after_forecast_backfill | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C334 | research_survey_recency_decay | P1 | research_event | stk_surv | engineerable_after_survey_backfill | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C335 | hsgt_top10_entry_streak | P1 | northbound_flow | hsgt_top10 | engineerable_after_hsgt_backfill | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C336 | ccass_acceleration_rank | P1 | northbound_flow | ccass_hold | engineerable_after_ccass_backfill | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C337 | industry_flow_rotation_accel | P1 | industry_flow | moneyflow_ind_dc or moneyflow_ind_ths | engineerable_after_industry_flow_join | Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C338 | wq_volume_price_rank_divergence | P1 | formulaic_alpha | daily OHLCV or 14:57 proxy OHLCV | engineerable_now_with_daily_or_1457_proxy | For live 14:57 use T-1 daily fields or explicitly built 14:57 proxy OHLCV; never use T-day final close/amount unless the task is post-close research. |
| C339 | wq_turnover_adjusted_reversal | P1 | formulaic_alpha | daily OHLCV + turnover/free float | engineerable_now_with_daily_or_1457_proxy | For live 14:57 use T-1 daily fields or explicitly built 14:57 proxy OHLCV; never use T-day final close/amount unless the task is post-close research. |
| C340 | qlib_alpha360_intraday_shape_moment | P1 | formulaic_alpha | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C341 | global_overnight_risk_gap | P2 | cross_market | index_global + A50/overseas index series | engineerable_after_global_calendar_alignment | Use only overseas data published before A-share open/14:57; if timestamp is uncertain, shift one trading day. |

## Deferred / Not Registered

- True L2/orderbook factors such as bid-ask depth imbalance, cancellation pressure, and OFI are not registered unless a stable L2 pipeline exists.
- Pure social/video/NLP factors are not expanded further because C286-C289 already cover the broad families and timestamped scrape is not locked.
- Same-name or near-trivial formulas such as `price = close`, raw `volume_ratio`, and target/future-return phrases are rejected.
- Daily final-close formulas are admitted only when they can be shifted to T-1 or rewritten to 14:57 proxy OHLCV.

## Data Handoff

- P0 minute candidates need full `stk_mins_1` coverage and a same-clock history matrix.
- Limit-board candidates need timestamped limit-pool reconstruction to 14:57 or T-1 fallback.
- Event/data-unlocked candidates need T-1 or announcement-time asof joins.
- Formulaic candidates need explicit 14:57 proxy fields before live model use.

## Ten Validation Checks

1. JSON loads: PASS
2. C IDs are continuous: PASS
3. No duplicate factor_id: PASS
4. No duplicate factor name: PASS
5. meta registry count matches actual C objects: PASS
6. New batch exists and count matches detail length: PASS
7. All new entries have required fields: PASS
8. All new entries are training_status=not_trained: PASS
9. All new entries are lockbox_role=research_candidate: PASS
10. No new entry claims is_passed/is_final_unseen/is_frozen_modified: PASS

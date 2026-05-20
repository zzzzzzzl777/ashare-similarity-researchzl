# Web Expanded Short-Line Factor Search 2026-05-17

Scope: factor-library only. No training, no gpu_probe, no model or frozen config changes.

## Search Surface

- `bigquant_hf_price_volume`: https://bigquant.com/square/paper/8fcfe5cd-cdd0-4c5e-af7c-f97fe0a15fa3
- `changjiang_high_position_volume`: https://www.sdyanbao.com/detail/113659
- `bigquant_auction`: https://bigquant.com/square/paper/cd07e2e7-68ae-47a5-8d41-f166e88700b2
- `bigquant_auction_fields`: https://mf.bigquant.com/data/datasources/cn_stock_factors_auction
- `kaiyuan_institution_behavior`: https://bigquant.com/square/paper/99a1c007-ef3e-45dd-8863-41f1d706dfc0
- `gtja_alpha191`: https://bigquant.com/square/paper/fbca3176-2c2b-4b79-88db-d4d5692adb9d
- `alpha191_github`: https://github.com/SelenaMa9812/Guotai-Junan-191-Alpha
- `worldquant_alpha101`: https://arxiv.org/abs/1601.00991
- `spectral_volume`: https://papers.ssrn.com/sol3/Delivery.cfm/4230610.pdf?abstractid=4230610
- `order_imbalance`: https://www.sciencedirect.com/science/article/pii/S0304405X03001752
- `shenzhen_extreme_order_flow`: https://arxiv.org/abs/1003.0168

## Added To Registry

- Batch: `candidates_20260517_web_expanded_surface`
- Count: 14
- ID range: `C342-C355`
- Priority counts: {'P0': 3, 'P1': 10, 'P2': 1}
- Family counts: {'auction_open': 1, 'auction_market': 2, 'lhb': 2, 'holder_trade': 2, 'research_event': 1, 'forecast_event': 1, 'minute_hf': 4, 'minute_market': 1}

| ID | Name | Priority | Family | Data Need | Engineering | Asof |
|---|---|---|---|---|---|---|
| C342 | auction_amount_to_float_mv | P0 | auction_open | opening auction amount + share_float + prev_close | engineerable_after_auction_and_share_float_join | Use only the final opening auction snapshot known after 09:25. If the field is revised post-close, shift to T-1. |
| C343 | auction_participation_breadth | P1 | auction_market | opening auction universe snapshot | engineerable_after_auction_universe_cache | Use only the final opening auction snapshot known after 09:25. If the field is revised post-close, shift to T-1. |
| C344 | auction_open_gap_dispersion | P1 | auction_market | opening auction price + prev_close for universe | engineerable_after_auction_universe_cache | Use only the final opening auction snapshot known after 09:25. If the field is revised post-close, shift to T-1. |
| C345 | lhb_institution_net_to_float | P0 | lhb | top_inst/top_list institution buy/sell + share_float | engineerable_after_top_inst_backfill | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C346 | lhb_buy_seat_concentration_hhi | P1 | lhb | top_list/top_inst detailed buy seat amounts | engineerable_if_lhb_seat_detail_exists | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C347 | insider_trade_net_to_float | P1 | holder_trade | stk_holdertrade + share_float | engineerable_after_stk_holdertrade_backfill | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C348 | insider_trade_recency_decay | P2 | holder_trade | stk_holdertrade event dates + net direction | engineerable_after_stk_holdertrade_backfill | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C349 | survey_participant_intensity_change | P1 | research_event | stk_surv participant count and institution type | engineerable_after_survey_backfill | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C350 | forecast_directional_consensus | P1 | forecast_event | forecast_vip directional forecast fields | engineerable_after_forecast_backfill | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C351 | minute_return_state_transition_entropy | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only minute bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C352 | minute_extreme_pre_peak_ratio | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only minute bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C353 | minute_volume_spectral_residual | P1 | minute_hf | 1min bars + trailing historical volume profiles | engineerable_after_1min_history_matrix | For 14:57 live use only minute bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C354 | cumulative_volume_curve_surprise_1457 | P0 | minute_hf | 1min bars + expected intraday volume curve | engineerable_after_1min_history_matrix | For 14:57 live use only minute bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C355 | minute_volume_synchronization_to_market | P1 | minute_market | 1min all-stock volume profiles | engineerable_after_1min_universe_cache | For 14:57 live use only minute bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |

## Deferred / Not Registered

- `alpha191_full_library`: Do not register 191 formulas as one factor. Needs separate formula catalog and dedup pass before individual C IDs.
- `alpha101_full_library`: Already partly represented by C278-C281 and C338-C340; additional formulas require explicit per-formula translation.
- `true_l2_orderbook`: OFI/depth/cancel-pressure factors remain deferred unless a stable L2/tick pipeline exists.
- `pure_social_video_nlp`: Already represented by C286-C289 broad families; needs timestamped scrape and entity mapping before expansion.

## Validation

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

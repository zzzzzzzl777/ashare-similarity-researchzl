# Web Saturation Short-Line Factor Search 2026-05-17

Scope: factor-library only. No training, no gpu_probe, no model or frozen config changes.

## Saturation Surface

- Chinese high-frequency price-volume reports
- high-position volume and entropy factor reports
- CPV/lagged price-volume correlation family
- single-trade amount / L2 behavior reports
- auction factor data and reports
- LHB fund structure and industry rotation reports
- Taoguba emotion-cycle rules
- social sentiment / intraday overtrading papers
- price-limit pre-hit dynamics papers
- Tushare/API data-field feasibility pass

## Source Evidence

- `gf_hf_factorization_46`: https://bigquant.com/square/paper/aaa3e0c6-4bc0-4ea3-9077-2a4976789c88
- `cj_high_position_volume`: https://asset.quant-wiki.com/pdf/20200916-%E9%95%BF%E6%B1%9F%E8%AF%81%E5%88%B8-%E5%9F%BA%E7%A1%80%E5%9B%A0%E5%AD%90%E7%A0%94%E7%A9%B6%EF%BC%88%E5%8D%81%E4%B8%89%EF%BC%89%EF%BC%9A%E9%AB%98%E9%A2%91%E5%9B%A0%E5%AD%90%EF%BC%88%E5%85%AB%EF%BC%89%EF%BC%8C%E9%AB%98%E4%BD%8D%E6%88%90%E4%BA%A4%E5%9B%A0%E5%AD%90%EF%BC%8C%E4%BB%8E%E9%87%8F%E4%BB%B7%E5%8C%B9%E9%85%8D%E8%AF%B4%E8%B5%B7.pdf
- `df_cpv_shift`: https://bigquant.com/square/paper/775b5485-2ec7-443f-a1d0-48aaceb94eb8
- `kaiyuan_single_trade_amount`: https://bigquant.com/square/paper/74353d24-a9cf-4d17-a9fb-c431ece0a52e
- `lhb_fund_structure`: https://bigquant.com/square/paper/07dff3c0-e071-4985-969d-2a7c263aefe3
- `lhb_industry_rotation`: https://bigquant.com/square/paper/db9c2003-d043-4704-988e-fedf18b4e882
- `taoguba_emotion_cycle`: https://www.tgb.cn/talk/talkSeq/179928
- `internet_sentiment_overtrading`: https://arxiv.org/abs/2404.12001
- `price_limit_prehit_dynamics`: https://arxiv.org/abs/1503.03548
- `tushare_stk_factor`: https://www.tushare.pro/document/2?doc_id=296

## Added To Registry

- Batch: `candidates_20260517_web_saturation`
- Count: 15
- ID range: `C356-C370`
- Priority counts: {'P0': 3, 'P1': 11, 'P2': 1}
- Family counts: {'minute_hf': 5, 'auction_open': 1, 'auction_market': 1, 'lhb': 2, 'social_attention': 1, 'limit_board': 2, 'northbound_flow': 1, 'industry_flow': 1, 'block_trade': 1}

| ID | Name | Priority | Family | Data Need | Engineering | Asof |
|---|---|---|---|---|---|---|
| C356 | volume_lagged_return_corr_1457 | P0 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C357 | large_volume_lagged_return_corr | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C358 | volume_weighted_price_skewness | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C359 | unit_amount_entropy | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C360 | intraday_amihud_tail_ratio | P1 | minute_hf | 1min bars | engineerable_after_1min_cache | For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C361 | auction_turnover_jump_20d | P0 | auction_open | opening auction turnover + trailing history | engineerable_after_auction_history_cache | Use only the final opening auction snapshot known after 09:25. If the field is revised post-close, shift to T-1. |
| C362 | auction_gap_positive_breadth | P1 | auction_market | opening auction price + prev_close for universe | engineerable_after_auction_universe_cache | Use only the final opening auction snapshot known after 09:25. If the field is revised post-close, shift to T-1. |
| C363 | lhb_seat_alpha_score_60d | P1 | lhb | top_list/top_inst seat names + post-event return history | engineerable_after_lhb_seat_history_cache | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C364 | lhb_theme_seat_crowding | P1 | lhb | top_list seat names + theme/industry mapping | engineerable_after_lhb_theme_join | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C365 | guba_sentiment_overtrading_gap | P2 | social_attention | timestamped guba/taoguba sentiment + intraday turnover | needs_timestamped_social_pipeline | Use only posts/comments timestamped <= 14:57 and minute turnover <= 14:57; otherwise shift to T-1. |
| C366 | limit_pre_hit_volume_acceleration | P0 | limit_board | 1min bars + first limit-hit timestamp | engineerable_if_limit_hit_timestamp_available | Use only limit touches and bars timestamped <= 14:57; if first-hit timestamp is unavailable, do not use for live. |
| C367 | limit_pre_hit_return_curvature | P1 | limit_board | 1min bars + first limit-hit timestamp | engineerable_if_limit_hit_timestamp_available | Use only limit touches and bars timestamped <= 14:57; if first-hit timestamp is unavailable, do not use for live. |
| C368 | northbound_top10_turnover_crowding | P1 | northbound_flow | hsgt_top10 turnover/buy/sell + stock float or amount | engineerable_after_hsgt_top10_backfill | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C369 | industry_lhb_flow_rotation_strength | P1 | industry_flow | LHB net buy by industry/theme + industry member map | engineerable_after_lhb_industry_aggregation | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |
| C370 | block_trade_discount_volume_pressure | P1 | block_trade | block_trade price/amount + daily close/ADV | engineerable_after_block_trade_backfill | Use T-1 or explicit publication/announcement timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57. |

## Deferred / Not Registered

- `full_alpha191_alpha101_formula_libraries`: Not bulk-registered. They need per-formula translation, C-ID dedup, and asof review.
- `true_l2_orderbook_cancel_depth_ofi`: Still blocked until stable L2/tick/orderbook pipeline exists.
- `pure_text_social_rules`: Rejected unless converted into timestamped entity-level numeric series.
- `generic_technical_indicators`: Rejected when already present in baseline/research features or too broad without short-line novelty.
- `duplicate_limit_emotion_metrics`: Rejected if already represented by board height, open-board, break-board, seal, or emotion-score families.

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

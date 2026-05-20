# Social Media Factor Deep Search 2026-05-18

Scope: Taoguba, local TGB raw pool, Xueqiu/Guba style public discussions, Bilibili/Douyin short-video search surfaces, and prior local social raw records.

Important boundary: this is registry work only. No training, no gpu_probe, no model config changes.

## Result

- Added candidates: 14 (C393 to C406)
- Priority counts: {'P1': 9, 'P0': 2, 'P2': 3}
- Family counts: {'limit_theme': 4, 'market_cycle': 2, 'market_emotion': 2, 'sector_structure': 2, 'volume_structure': 1, 'announcement_event': 1, 'social_attention': 2}
- All new candidates are research_candidate + not_trained.

## Social Channels Searched

- Taoguba/TGB local raw pool: 1618 social/TGB records were present in raw_factor_pool_index.
- Taoguba web: emotion cycle, leader cycle, weak-to-strong, divergence/ice-point/retreat concepts.
- Xueqiu/Guba style public discussion: short-line tactics and popularity/attention concepts.
- Bilibili/Douyin search surfaces: repeated the same leader/emotion/auction vocabulary, but stable factorization requires timestamped video/comment metadata.

## Already Covered / Not Duplicated

- Existing code or registry concepts cover: board_count, max_board_height, limit_up_count, limit_down_count, broken_board_count, emotion_score, advance_decline_ratio, volume_vs_prev, weak_to_strong auction variants, seal_rate_80_threshold, short_video_attention_shock, social_leader_mention_breadth.
- These were not re-added with new IDs just because a social source mentioned them again.

## Added Candidates

| ID | Name | Priority | Family | Data Need | Status |
|---|---|---:|---|---|---|
| C393 | tgb_echelon_continuity_gap | P1 | limit_theme | limit_pool daily board height by stock; market-wide max_board_height | candidate_ready_after_limit_pool_join |
| C394 | tgb_high_low_switch_pressure | P0 | market_cycle | limit_pool, board height, next-day premium history, low-position first/second board counts | candidate_ready_after_limit_pool_join |
| C395 | tgb_ice_point_repair_age | P1 | market_emotion | daily market limit_up_count, limit_down_count, broken_board_count, emotion_score | candidate_ready_after_market_emotion_join |
| C396 | tgb_first_divergence_repair_strength | P1 | limit_theme | daily OHLCV, first_divergence_flag, theme membership, same-theme limit-up count | candidate_ready_after_theme_join |
| C397 | tgb_solo_guide_theme_signal | P2 | limit_theme | limit_pool, theme/name token map, recent theme occurrence counts | needs_theme_text_pipeline |
| C398 | tgb_theme_capacity_turnover_fit | P1 | sector_structure | theme membership, per-stock amount, market total amount | candidate_ready_after_theme_join |
| C399 | tgb_sector_independence_ex_leader | P1 | sector_structure | theme membership, leader identification, daily OHLCV, limit_pool | candidate_ready_after_theme_join |
| C400 | tgb_explosive_volume_weak_open | P0 | volume_structure | daily volume, daily open/prev_close, optional first 5min or 1min bar return | candidate_ready_after_daily_and_minute_join |
| C401 | tgb_market_split_extreme_divergence | P1 | market_emotion | market limit_up_count, limit_down_count, broken_board_count | code_existing_or_candidate_ready |
| C402 | tgb_regulatory_pressure_countdown | P1 | announcement_event | limit_pool board height, abnormal movement announcements, exchange attention/监管公告 if available | needs_announcement_timestamp_pipeline |
| C403 | tgb_position_uniqueness_score | P1 | limit_theme | theme membership, board height, board type (10cm/20cm/ST), limit_pool | candidate_ready_after_theme_join |
| C404 | tgb_theme_cycle_day_position | P1 | market_cycle | theme membership, theme limit breadth, leader board height, divergence day counter | candidate_ready_after_theme_join |
| C405 | social_cross_platform_attention_consensus | P2 | social_attention | timestamped mention/heat counts from taoguba, guba/xueqiu, and optional Bilibili/Douyin video/comment mentions | needs_timestamped_social_pipeline |
| C406 | short_video_theme_velocity_24h | P2 | social_attention | Bilibili/Douyin video metadata, comments or captions, symbol/theme dictionary, publish timestamps | needs_timestamped_social_pipeline |

## Data / Pipeline Gaps

- C405 and C406 need a timestamped social/video pipeline before training.
- C397 needs reliable theme/name token normalization.
- C402 needs announcement timestamps and exchange-rule mapping; otherwise shift announcements to T+1.
- The other candidates can be derived from daily OHLCV, limit_pool, theme membership, auction/minute bars, or already cached market emotion fields once canonical joins are available.

## Validation

- Registry candidate count after write: 406
- Missing ID check: []
- Duplicate ID check: []
- No new candidate is marked passed, final_unseen, or frozen.

# Raw Review → Registry Promotion Report — 2026-05-06

## Summary

| Metric | Value |
|--------|-------|
| Input queue | 50 candidates |
| Promoted | 14 (C139-C152) |
| Rejected | 20 |
| Deferred | 16 |
| New batch key | `candidates_20260506_raw_review` |
| ID range | C139-C152 |

---

## Selection Criteria (Promotion)

All promoted candidates satisfy:
1. `free_data=True` (no paid data source)
2. `future_leakage_risk=low`
3. `needs_level2=False`
4. Clear, computable definition derivable from raw_text
5. NOT a duplicate of C001-C138 or any of 783 implemented features
6. Distinct signal vs `related_existing_features` (documented per candidate)

---

## Promoted Candidates (14)

| # | factor_id | name | family | priority | data_need | computable_definition (brief) |
|---|-----------|------|--------|----------|-----------|-------------------------------|
| 1 | C139 | real_limit_up_premium_gap | limit_up_premium | P0 | limit_pool + daily | mean(return, real_pool) - mean(return, proxy_pool) |
| 2 | C140 | zbgc_sector_pressure | board_quality | P0 | limit_pool + sector | broken_board_count / limit_attempt_count per sector |
| 3 | C141 | prev_top20_chase_real | market_breadth | P0 | daily_ohlcv | mean(return_T, top20_gainers_T-1) |
| 4 | C142 | theme_limit_density | sector_momentum | P1 | limit_pool + sector | limit_up_count_in_theme / theme_member_count |
| 5 | C143 | is_volume_sufficient | volume_quality | P1 | daily_ohlcv | turnover_T / turnover_T-1 >= 0.7 |
| 6 | C144 | leader_pull_effect | sector_momentum | P1 | daily + limit + sector | mean(sector_peer_return) on stock's limit-up day |
| 7 | C145 | theme_height_suppression | sector_cycle | P1 | daily + limit + sector | max(board_count, same_theme, 1Y) |
| 8 | C146 | support_one_word_count | board_structure | P1 | daily + sector | count(open==close==high_limit, same_sector) |
| 9 | C147 | eruption_strength | market_breadth | P2 | daily + limit | z(limit_count) + z(one_word_count) + z(unbuyable_rate) |
| 10 | C148 | is_ground_sky | extreme_pattern | P2 | daily + limit | (low==low_limit) AND (close==high_limit) |
| 11 | C149 | seal_trend | board_quality | P2 | limit_pool | seal_money_T / seal_money_T-1 - 1 |
| 12 | C150 | old_leader_decay | market_cycle | P2 | daily + limit | top_board_stock broken OR volume_drop > 30% |
| 13 | C151 | anti_drop_strength | relative_strength | P2 | daily_ohlcv | stock_return / index_return on down days |
| 14 | C152 | multi_wave_count | technical_pattern | P2 | daily_ohlcv | count(rising_segment_starts) in 60d window |

---

## Rejected Candidates (20)

| Queue# | factor_name | raw_factor_id | Reason |
|--------|-------------|---------------|--------|
| 5 | limit_up_count_market | RAW002965 | Duplicate of `market_limit_up_count` (stable feature) |
| 7 | sector_batch_limit_effect | RAW000286 | Duplicate of `sector_limit_up_count` (binary version of existing count) |
| 8 | asking_chase_half_position | RAW000290 | Not computable — trading strategy (position sizing), not market factor |
| 10 | second_board_confirm_leader | RAW000287 | Duplicate of `is_second_board` / `board_count == 2` |
| 11 | opening_seal_speed | RAW000312 | Duplicate of `seal_time` (existing stable feature) |
| 16 | sector_followup_count | RAW000041 | Functional duplicate of `sector_limit_up_count - 1` (exclude self) |
| 22 | position_stock_signal | RAW000078 | Requires NLP/text parsing of stock names — not computable from market data |
| 24 | sector_batch_limit_effect | RAW000121 | Duplicate entry of #7 (same concept, different raw_factor_id) |
| 27 | second_board_confirm_leader | RAW000213 | Duplicate entry of #10 |
| 28 | name_geography_mysticism | RAW000241 | Requires NLP (stock name/geography text matching) |
| 29 | solo_stock_direction_hint | RAW000244 | Requires NLP (name-based direction inference) |
| 32 | today_limit_up | RAW000987 | Trivial duplicate: close == high_limit (already `is_limit_up`) |
| 33 | peak_price | RAW000990 | Not a factor — reference price value, not predictive signal |
| 34 | closed_limit_up | RAW001048 | Duplicate of #32 / existing limit-up detection |
| 36 | final_close | RAW001099 | Duplicate of #32 / existing limit-up detection |
| 39 | Z_t | RAW002055 | Not a specific factor — generic "macro state variable" category label |
| 43 | abull | RAW000001 | Not a factor — data source reference (Asking/邱宝裕 biography) |
| 44 | is_sector_leader | RAW000040 | Duplicate entry of #6 (deferred) |
| 48 | hardness_three_exists | RAW000082 | Duplicate of `market_max_board_height >= 3` |
| 6 | is_sector_leader | RAW000258 | Vague formula; overlaps with `sector_strength_rank` + `sector_pct_change_best` |

---

## Deferred Candidates (16)

| Queue# | factor_name | raw_factor_id | Deferral Reason | Possible Resolution |
|--------|-------------|---------------|-----------------|---------------------|
| 4 | hk_close_return | RAW002964 | Partially covered by C128 `global_risk_sentiment_overnight`; cross_ features excluded from expanded | Revisit if cross_ exclusion lifted |
| 12 | hesitant_seal_signal | RAW000313 | Unclear formula; likely overlaps with board_open_count / seal quality features | Clarify if distinct from open_count |
| 13 | dynamic_volume_comparison | RAW000323 | "Three standards" undefined; overlaps volume_ratio family | Define the 3 specific thresholds |
| 14 | min_daily_volume_300m | RAW000329 | Universe filter (amount >= 3e8), not predictive factor | Could add as pre-filter, not factor |
| 19 | solo_guide_count | RAW000074 | "Non-sector limit-up" definition unclear | Define clear sector-independence criterion |
| 21 | sector_first_board_attr | RAW000076 | Categorical classification (3+ categories), not single numeric factor | Decompose into binary factors |
| 23 | board_echelon_city_cluster | RAW000079 | Requires geographic metadata + complex cluster detection | Add after geographic data available |
| 25 | quant_next_day_cash | RAW000124 | "Quant-driven surge" criterion undefined | Define quant-surge detection rule |
| 30 | volume_price_health | RAW000541 | Composite without clear component formula | Propose specific sub-factors |
| 31 | success_prob | RAW000907 | Requires expected_open_volume (not in free data) | Available if limit pool enriched |
| 37 | volume_during_open | RAW001101 | Needs intraday timing to isolate "open period" volume | Available with stk_mins_5 attachment |
| 41 | seal_order_fragmentation | RAW002642 | seal_order_count requires Level 2 order-flow data | Blocked unless proxy found |
| 42 | limit_up_with_volume | RAW002954 | Trivial interaction of existing features (limit_up × high_turnover) | Low priority, already implicitly in model |
| 47 | sector_sustainability_score | RAW000080 | Composite with subjective "new catalyst" component | Remove catalyst; keep other 2 components |
| 49 | echelon_position_battle | RAW000083 | Requires intraday timing + subjective tier classification | Simplify to "afternoon limit-up rate" |
| 50 | midcap_supplement_prob | RAW000084 | "Mid position" and "supplement rally" definitions too vague | Define as percentile-rank-based |

---

## Family Distribution (Promoted)

| Family | Count | Candidates |
|--------|-------|------------|
| board_quality | 2 | C140, C149 |
| market_breadth | 2 | C141, C147 |
| sector_momentum | 2 | C142, C144 |
| limit_up_premium | 1 | C139 |
| volume_quality | 1 | C143 |
| sector_cycle | 1 | C145 |
| board_structure | 1 | C146 |
| extreme_pattern | 1 | C148 |
| market_cycle | 1 | C150 |
| relative_strength | 1 | C151 |
| technical_pattern | 1 | C152 |

---

## Data Dependency Distribution (Promoted)

| Data Source | Candidates Using It |
|-------------|--------------------|
| daily_ohlcv | 14 (all) |
| limit_pool | 10 (C139-C142, C144-C150) |
| sector_theme | 6 (C140, C142, C144-C146) |

---

## Engineering Path Notes

- **Pure daily_ohlcv** (4 factors: C141, C143, C151, C152): Implementable immediately in `_attach_free_factor_features`
- **limit_pool required** (6 factors: C139, C140, C147-C150): Need `stock_zt_pool_*_em` APIs; data exists in `limit_list_d` cache (804 files)
- **sector_theme required** (4 factors: C142, C144-C146): Need `ths_index_member` or concept membership; data in `ths_daily` cache

---

## Constraints Confirmation

- [x] No training executed
- [x] No `frozen_forward_config.json` modification
- [x] No `lockbox_role=passed` or `lockbox_role=final_unseen` claims
- [x] C001-C138 completely unchanged (verified by pre-check)
- [x] All new candidates: `training_status="not_trained"`, `lockbox_role="research_candidate"`
- [x] IDs sequential: C139, C140, ..., C152
- [x] Registry JSON valid (json.load succeeds)

---

*Generated 2026-05-06. Source: raw_to_registry_review_queue_20260506.md (50 reviewed, 14 promoted, 20 rejected, 16 deferred)*

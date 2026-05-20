# Raw Pool Full Remaining Audit (2026-05-07)

## Summary

| Metric | Count |
|--------|-------|
| Total raw pool records | 3075 |
| Already in registry (exact match) | 44 |
| Previously reviewed (429 queue) | 429 |
| **Remaining audited this round** | **2646** |
| promote_candidate | 24 |
| reject | 980 |
| defer | 1642 |
| Intra-audit duplicates (moved to reject) | 0 |
| **Unreviewed remaining** | **0** |

---

## Rejection Reasons

| Reason | Count |
|--------|-------|
| name_duplicate | 404 |
| trading_strategy | 153 |
| needs_level2_keyword | 96 |
| needs_level2_flagged | 75 |
| needs_special_data | 66 |
| future_variable | 58 |
| needs_minute_bars | 46 |
| already_in_registry | 23 |
| vague_categorical | 22 |
| nlp_text_subjective | 14 |
| cross_market | 12 |
| concept_duplicate | 11 |

---

## Deferral Reasons

| Reason | Count |
|--------|-------|
| not_free_data | 1431 |
| no_computable_formula | 165 |
| asof_unclear | 45 |
| no_formula_too_short | 1 |

---

## Top 30 Promote Candidates (by engineering feasibility)

| # | raw_factor_id | Name | Source | Formula (truncated) | Data Need | Asof | Duplicate Check | Engineering Path | Risk |
|---|---------------|------|--------|---------------------|-----------|------|-----------------|------------------|------|
| 1 | RAW001779 | sector_change_intensity | short | / P1 / `sector_change_intensity` / 板块异动次数 + 主力净流入 + 频繁异动个股强度 / `stock_board_chan | sector_theme, announcement | after_close | no_match | sector/theme: ths_index_member + sector  | none |
| 2 | RAW001780 | theme_breadth_real | short | / P1 / `theme_breadth_real` / 概念板块上涨家数 / 成份股数量 / `stock_board_concept_name_em` / | sector_theme | after_close | keyword_overlap | sector/theme: ths_index_member + sector  | keyword_overlap_with_registry |
| 3 | RAW002830 | temp | short | temp = 涨停数/10 + ad_ratio×5 + 换手比20日均×2 - 跌停数/5 + 最高连板×0.5 | daily_ohlcv, limit_pool | after_close | partial_name_match | limit_pool API: stock_zt_pool_em + free_ | partial_name_match_needs_manua |
| 4 | RAW002968 | northbound_net_buy | explore | / 11 / `northbound_net_buy` / 东方财富/AKShare / 是(部分) / | unknown | unknown | no_match | data: unknown | asof_unverified |
| 5 | RAW000183 | institution_trend_buy_yin | tgb | / `institution_trend_buy_yin` 机构趋势票买阴线 / 基金票无延续性；形成短期上涨趋势后买阴线 / 龙虎榜+日线 / Asking语 | daily_ohlcv, lhb | after_close | no_match | data: daily_ohlcv, lhb | none |
| 6 | RAW001512 | pullback_from_high | tgb | pullback_from_high = 1 - stock.close / highest_since_entry | daily_ohlcv | after_close | keyword_overlap | daily_ohlcv_only: straightforward rollin | keyword_overlap_with_registry |
| 7 | RAW002117 | Sign | short | Sign = sign(Close_t - Max(High[t-N:t-1]))  # +1突破新高, -1跌破新低 | daily_ohlcv | after_close | partial_name_match | daily_ohlcv_only: straightforward rollin | partial_name_match_needs_manua |
| 8 | RAW002981 | dragon_tiger_net_buy_ratio | explore | / 24 / `dragon_tiger_net_buy_ratio` / 龙虎榜数据(AKShare) / 是 / | lhb | after_close | no_match | data: lhb | none |
| 9 | RAW000456 | board_height_score | tgb | board_height_score = max_board_height / historical_avg_max_board | limit_pool | after_close | keyword_overlap | limit_pool API: stock_zt_pool_em + free_ | keyword_overlap_with_registry |
| 10 | RAW000595 | avg_seal_time | tgb | avg_seal_time = mean(seal_time for stock in today_limit_up_stocks) | limit_pool | after_close | keyword_overlap | limit_pool API: stock_zt_pool_em + free_ | keyword_overlap_with_registry |
| 11 | RAW002601 | uniqueness_score | short | uniqueness_score = 1.0 / (same_theme_limit_up_count + 1) | limit_pool, sector_theme | after_close | keyword_overlap | limit_pool API: stock_zt_pool_em + free_ | keyword_overlap_with_registry |
| 12 | RAW000137 | anomaly_200_buysel_imbalance | tgb | / `anomaly_200_buysel_imbalance` 200%异动买卖失衡 / 进200%异动监管后买盘限额300万/分钟 → 流动性受限 / 监管 | announcement | after_close | no_match | data: announcement | none |
| 13 | RAW000507 | signal_decay | tgb | signal_decay = exp(-0.3 × hours_since_disclosure) | announcement | after_close | no_match | data: announcement | short_raw_text |
| 14 | RAW000528 | policy_density | tgb | policy_density = count(policy_events[sector] in last_N_days) / N | sector_theme | after_close | keyword_overlap | sector/theme: ths_index_member + sector  | keyword_overlap_with_registry |
| 15 | RAW000530 | research_surge | tgb | research_surge = count(机构调研_近30日) / avg(机构调研_前90日) | lhb | after_close | no_match | data: lhb | none |
| 16 | RAW000570 | lhb_buy_sell_ratio | tgb | lhb_buy_sell_ratio = lhb_buy_top5_total / lhb_sell_top5_total | lhb | after_close | no_match | data: lhb | none |
| 17 | RAW001742 | seat_premium_score | short | / AKShare `stock_lhb_yyb_detail_em` 营业部历史明细 / 营业部买卖净额、后续 1/2/3/5/10/20/30 日表现 /  | lhb | after_close | no_match | data: lhb | none |
| 18 | RAW001743 | famous_seat_decay | short | / AKShare `stock_lhb_yyb_detail_em` 营业部历史明细 / 营业部买卖净额、后续 1/2/3/5/10/20/30 日表现 /  | lhb | after_close | no_match | data: lhb | none |
| 19 | RAW001744 | seat_style_vector | short | / AKShare `stock_lhb_yyb_detail_em` 营业部历史明细 / 营业部买卖净额、后续 1/2/3/5/10/20/30 日表现 /  | lhb | after_close | no_match | data: lhb | none |
| 20 | RAW001943 | Sentiment_Factor_t | short | Sentiment_Factor_t = Σ_{i∈month} Score_i × Recency_Weight_i / N_announcements | announcement | after_close | no_match | data: announcement | none |
| 21 | RAW001985 | PEAD_factor | short | PEAD_factor = SUE × I(公告日后 ≤ 60个交易日) | announcement | after_close | no_match | data: announcement | short_raw_text |
| 22 | RAW002274 | FAD | short | FAD = SUE × I(Friday_announcement) | announcement | after_close | no_match | data: announcement | short_raw_text |
| 23 | RAW002579 | TARGET_CAR | short | TARGET_CAR = Σ(R_target,t - R_market,t) for t in [-1, +5]  # 公告前1日至后5日 | announcement | after_close | no_match | data: announcement | none |
| 24 | RAW002934 | etf_creation_redemption | explore | / `etf_creation_redemption` / ETF净申购/赎回份额 / 大额申购→机构看多 / | lhb | after_close | no_match | data: lhb | none |

---

## Constraints Confirmation

- [x] No factor_registry.json modification
- [x] No C174+ added
- [x] No training executed
- [x] No gpu_probe runs
- [x] No frozen_forward_config modification
- [x] All records audited (0 unreviewed remaining)

---

*Generated 2026-05-07 00:50. Registry state: C001-C173.*
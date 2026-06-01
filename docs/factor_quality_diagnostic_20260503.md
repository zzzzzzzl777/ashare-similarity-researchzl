# Factor Quality Diagnostic Report

> Generated: 2026-05-03 11:25 UTC
> Scope: **seen_research diagnostic only** — read-only, no training, no config changes
> Feature cache: `gpu_probe_features_27f3f4cc8c1b747f.parquet`
> Cache rows: 259369, created: 2026-05-02T14:00:25+00:00
> Selected 260 source: frozen artifact `gpu_probe_20260501T155956Z_d64e3464`

---

## 1. Tushare Raw Cache Audit

Per-API date/stock coverage from `E:\ashare_similarity_runtime\data\cache\prediction\tushare\`.
Excludes `stk_mins_5` (18% stock coverage, not recommended yet).

| API | Partitioning | Files/Dates | Date Range | Sample Stocks | Columns |
|-----|-------------|-------------|------------|---------------|---------|
| moneyflow | per-date | 804 dates | 20230103 ~ 20260430 | 5087 | 20 cols |
| daily_basic | per-date | 804 dates | 20230103 ~ 20260430 | 5339 | 18 cols |
| stk_limit | per-date | 804 dates | 20230103 ~ 20260430 | 6867 | 4 cols |
| stk_auction_o | per-date | 804 dates | 20230103 ~ 20260430 | 5238 | 9 cols |
| stk_auction_c | per-date | 804 dates | 20230103 ~ 20260430 | 5566 | 9 cols |
| stk_holdernumber | per-date | 804 dates | 20230103 ~ 20260430 | 3232 | 4 cols |
| hk_hold | per-date | 774 dates | 20230103 ~ 20260430 | 792 | 7 cols |
| margin_detail | per-date | 804 dates | 20230103 ~ 20260430 | 3918 | 10 cols |
| cyq_perf | per-stock | 3194 stocks | 2023-01-03 ~ 2026-04-30 | 804 dates/stock | per-stock parquet |
| ths_hot | per-date | 623 dates | 20230821 ~ 20260430 | 460 | 11 cols |
| limit_list_d | per-date | 804 dates | 20230103 ~ 20260430 | 59 | 18 cols |
| top_list | per-date | 804 dates | 20230103 ~ 20260430 | 47 | 15 cols |
| top_inst | per-date | 804 dates | 20230103 ~ 20260430 | 47 | 10 cols |

---

## 2. Tushare Factor Column Stats (from research feature cache)

Source: research-scope feature cache (259k rows, 2023-05 ~ 2026-04).
Base columns only (excluding `_available` suffixes).

| Sub-Source | Column | NaN% | Nonzero% | Std | Mean | Min | Max | Flags |
|-----------|--------|------|----------|-----|------|-----|-----|-------|
| moneyflow | `tushare_net_mf_amount` | 0.00% | 100.00% | 15517.5339 | -2964.9194 | -520152.2400 | 458038.1500 | — |
| moneyflow | `tushare_lg_buy_sell_ratio` | 0.00% | 100.00% | 0.2210 | 0.9556 | 0.0000 | 9.5772 | — |
| moneyflow | `tushare_elg_buy_sell_ratio` | 0.00% | 97.43% | 1.4621 | 1.1804 | 0.0000 | 50.0000 | — |
| moneyflow | `tushare_mf_strength` | 0.00% | 100.00% | 0.1361 | -0.0329 | -1.0000 | 0.8361 | — |
| moneyflow | `tushare_sm_sell_pressure` | 0.00% | 100.00% | 0.0563 | 0.4873 | 0.0044 | 1.0000 | — |
| limit_list_d | `tushare_seal_ratio` | 0.00% | 8.55% | 0.0059 | 0.0011 | 0.0000 | 0.3199 | — |
| limit_list_d | `tushare_open_times` | 0.00% | 8.29% | 1.6536 | 0.3226 | 0.0000 | 71.0000 | — |
| limit_list_d | `tushare_first_time_minutes` | 0.00% | 9.79% | 197.4210 | 64.1193 | 0.0000 | 900.0000 | — |
| limit_list_d | `tushare_up_stat_days` | 0.00% | 7.86% | 0.9025 | 0.1893 | 0.0000 | 22.0000 | — |
| limit_list_d | `tushare_limit_type` | 0.00% | 8.53% | 0.2878 | 0.0500 | -1.0000 | 1.0000 | — |
| limit_list_d | `tushare_limit_turnover` | 0.00% | 11.56% | 0.0594 | 0.0174 | 0.0000 | 0.9472 | — |
| top_list_inst | `tushare_lhb_net_buy` | 0.00% | 7.47% | 33352598.1503 | 410219.1722 | -2294291650.4800 | 2257738973.9500 | — |
| top_list_inst | `tushare_lhb_net_rate` | 0.00% | 7.44% | 1.7321 | 0.0085 | -49.4600 | 62.2300 | — |
| top_list_inst | `tushare_lhb_appeared` | 0.00% | 7.51% | 0.2636 | 0.0751 | 0.0000 | 1.0000 | — |
| top_list_inst | `tushare_inst_buy_count` | 0.00% | 7.45% | 1.9069 | 0.4926 | 0.0000 | 25.0000 | — |
| top_list_inst | `tushare_inst_net_buy` | 0.00% | 7.45% | 1181676147.4602 | 26433344.8357 | -2174653294.4000 | 229075104900.0000 | — |
| hk_hold | `tushare_hk_ratio` | 0.00% | 26.29% | 5.8754 | 1.4919 | 0.0000 | 70.4000 | — |
| hk_hold | `tushare_hk_ratio_delta_1d` | 0.00% | 22.40% | 3.0429 | 0.0045 | -69.4400 | 69.5900 | — |
| margin_detail | `tushare_rzye` | 0.00% | 59.77% | 752821344.9613 | 401618963.5371 | 0.0000 | 18224908889.0000 | — |
| margin_detail | `tushare_rzye_delta_pct` | 0.00% | 59.75% | 5.8976 | 0.7374 | -82.3766 | 551.7532 | — |
| margin_detail | `tushare_rzmre_ratio` | 0.00% | 59.77% | 0.1355 | 0.1073 | 0.0000 | 1.6826 | — |
| margin_detail | `tushare_margin_net` | 0.00% | 59.77% | 42168221.8208 | 2759040.9217 | -6754981896.0000 | 1525011674.0000 | — |
| margin_detail | `tushare_rqye_ratio` | 0.00% | 49.65% | 0.0244 | 0.0056 | 0.0000 | 0.6172 | — |
| ths_hot | `tushare_hot_rank` | 0.00% | 12.90% | 128235.1429 | 2825.8624 | 0.0000 | 16257413.0000 | — |
| ths_hot | `tushare_hot_value` | 0.00% | 12.18% | 154164.5966 | 31745.6660 | 0.0000 | 12387252.0000 | — |
| daily_basic | `tushare_volume_ratio` | 0.00% | 100.00% | 0.8572 | 1.3103 | 0.1100 | 36.3900 | — |
| daily_basic | `tushare_free_share` | 0.00% | 100.00% | 100036.8978 | 60399.5819 | 0.0000 | 3207043.1679 | — |
| cyq_perf | `tushare_winner_rate` | 0.00% | 99.98% | 29.6767 | 59.0080 | 0.0000 | 100.5600 | — |
| cyq_perf | `tushare_cost_concentration` | 0.00% | 99.99% | 0.1013 | 1.1512 | 0.0000 | 3.5000 | — |
| cyq_perf | `tushare_cost_position` | 0.00% | 97.35% | 0.0252 | 0.0030 | -0.2237 | 0.6405 | — |
| stk_auction | `tushare_auction_open_vwap_ratio` | 0.00% | 100.00% | 0.0036 | 0.9997 | 0.9226 | 1.0872 | — |
| stk_auction | `tushare_auction_open_vol` | 0.00% | 100.00% | 9754073.5632 | 1650561.8768 | 0.0000 | 2178190049.2800 | — |
| stk_auction | `tushare_auction_close_vwap_ratio` | 0.00% | 100.00% | 0.0062 | 0.9998 | 0.8975 | 1.1400 | — |
| stk_auction | `tushare_auction_close_vol` | 0.00% | 100.00% | 92083253.3821 | 15227442.1661 | 10900.0000 | 23384489984.0000 | — |
| stk_holdernumber | `tushare_holder_num` | 0.00% | 0.00% | 0.0000 | 0.0000 | 0.0000 | 0.0000 | NEAR_CONST |
| stk_holdernumber | `tushare_holder_num_delta_pct` | 0.00% | 0.00% | 0.0000 | 0.0000 | 0.0000 | 0.0000 | NEAR_CONST |
| stk_limit | `tushare_up_limit_distance` | 0.00% | 100.00% | 0.0029 | 0.0998 | 0.0449 | 0.1047 | — |
| stk_limit | `tushare_down_limit_distance` | 0.00% | 100.00% | 0.0029 | 0.0998 | 0.0449 | 0.1047 | — |
| stk_limit | `tushare_limit_range` | 0.00% | 100.00% | 0.0058 | 0.1997 | 0.0899 | 0.2093 | — |

---

## 3. Research Daily Factor Column Stats

Extended emotion/board structure columns from `GPU_PROBE_RESEARCH_FACTOR_COLUMNS` (47 base).
These are market-level daily factors computed from local cache (100% coverage expected).

| Column | NaN% | Nonzero% | Std | Mean | Min | Max | Flags |
|--------|------|----------|-----|------|-----|-----|-------|
| `market_limit_seal_success_rate` | 0.00% | 100.00% | 0.0995 | 0.5478 | 0.1371 | 0.8571 | — |
| `seal_rate_80_threshold` | 0.00% | 0.09% | 0.0296 | 0.0009 | 0.0000 | 1.0000 | NEAR_CONST |
| `market_limit_down_rate` | 0.00% | 90.50% | 0.0430 | 0.0083 | 0.0000 | 0.7791 | — |
| `market_one_word_board_count` | 0.00% | 97.52% | 4.5780 | 5.4891 | 0.0000 | 27.0000 | — |
| `market_high_leader_crash_count` | 0.00% | 58.89% | 3.0619 | 1.4972 | 0.0000 | 32.0000 | — |
| `cycle_day_count` | 0.00% | 57.33% | 2.1089 | 1.5572 | 0.0000 | 12.0000 | — |
| `divergence_day_count` | 0.00% | 69.90% | 3.9593 | 2.7350 | 0.0000 | 27.0000 | — |
| `buy_sell_cycle_phase` | 0.00% | 61.82% | 0.6626 | -0.4232 | -1.0000 | 1.0000 | — |
| `liquidity_exhaustion_signal` | 0.00% | 41.64% | 0.4930 | 0.4164 | 0.0000 | 1.0000 | — |
| `market_split_signal` | 0.00% | 66.59% | 0.4717 | 0.6659 | 0.0000 | 1.0000 | — |
| `quant_climax_type` | 0.00% | 21.44% | 0.5137 | 0.2520 | 0.0000 | 2.0000 | — |
| `vol_stagnation_signal` | 0.00% | 12.74% | 0.3334 | 0.1274 | 0.0000 | 1.0000 | — |
| `bull_rotation_upgrade` | 0.00% | 8.31% | 0.2760 | 0.0831 | 0.0000 | 1.0000 | — |
| `theme_capacity_score` | 0.00% | 100.00% | 0.4874 | 1.7049 | 0.7284 | 3.0000 | — |
| `market_amount_ratio_20` | 0.00% | 100.00% | 0.3400 | 1.0745 | 0.6641 | 3.5230 | — |
| `market_amount_percentile_60` | 0.00% | 100.00% | 0.3233 | 0.5720 | 0.0167 | 1.0000 | — |
| `volume_is_king_signal` | 0.00% | 13.38% | 0.3404 | 0.1338 | 0.0000 | 1.0000 | — |
| `ground_volume_risk` | 0.00% | 1.78% | 0.1320 | 0.0178 | 0.0000 | 1.0000 | — |
| `post_decline_transition` | 0.00% | 5.85% | 0.2346 | 0.0585 | 0.0000 | 1.0000 | — |
| `decline_stabilize_signal` | 0.00% | 16.59% | 0.3720 | 0.1659 | 0.0000 | 1.0000 | — |
| `weak_friday_risk` | 0.00% | 2.14% | 0.1446 | 0.0214 | 0.0000 | 1.0000 | — |
| `prev_top20_chase_return` | 0.00% | 100.00% | 2.3623 | 2.1491 | -6.2691 | 9.9104 | — |
| `prev_top20_chase_win_rate` | 0.00% | 100.00% | 0.1807 | 0.5942 | 0.1000 | 1.0000 | — |
| `prev_bottom20_rebound_return` | 0.00% | 100.00% | 2.3901 | -1.4616 | -9.8398 | 6.6423 | — |
| `money_effect_spread_20` | 0.00% | 100.00% | 2.5535 | 3.6107 | -2.7094 | 15.8307 | — |
| `collapse_warning_signal` | 0.00% | 14.71% | 0.3542 | 0.1471 | 0.0000 | 1.0000 | — |
| `bullish_pivot_recognition` | 0.00% | 5.85% | 0.2346 | 0.0585 | 0.0000 | 1.0000 | — |
| `limit_premium_failure_signal` | 0.00% | 2.51% | 0.1565 | 0.0251 | 0.0000 | 1.0000 | — |
| `bad_sentiment_no_sweep` | 0.00% | 13.86% | 0.3456 | 0.1386 | 0.0000 | 1.0000 | — |
| `high_leader_crash_sentiment_collapse` | 0.00% | 53.65% | 0.4987 | 0.5365 | 0.0000 | 1.0000 | — |
| `no_theme_rotation_mode` | 0.00% | 0.93% | 0.0962 | 0.0093 | 0.0000 | 1.0000 | NEAR_CONST |
| `money_effect_sector_rotation` | 0.00% | 0.78% | 0.0879 | 0.0078 | 0.0000 | 1.0000 | NEAR_CONST |
| `full_position_trigger` | 0.00% | 3.93% | 0.1944 | 0.0393 | 0.0000 | 1.0000 | — |
| `late_cycle_position_cap` | 0.00% | 40.72% | 0.4913 | 0.4072 | 0.0000 | 1.0000 | — |
| `bear_position_reduction` | 0.00% | 66.99% | 0.4703 | 0.6699 | 0.0000 | 1.0000 | — |
| `strong_market_regime` | 0.00% | 4.96% | 0.2170 | 0.0496 | 0.0000 | 1.0000 | — |
| `weak_market_oversold_regime` | 0.00% | 28.40% | 0.4509 | 0.2840 | 0.0000 | 1.0000 | — |
| `bull_hotspot_bear_oversold` | 0.00% | 33.35% | 0.5278 | -0.2344 | -1.0000 | 1.0000 | — |
| `shrink_after_rotten` | 0.00% | 2.52% | 0.1567 | 0.0252 | 0.0000 | 1.0000 | — |
| `explosive_vol_next_weak` | 0.00% | 10.45% | 0.3059 | 0.1045 | 0.0000 | 1.0000 | — |
| `break_node_new_dragon` | 0.00% | 2.25% | 0.1482 | 0.0225 | 0.0000 | 1.0000 | — |
| `dragon_replace_signal` | 0.00% | 2.25% | 0.1482 | 0.0225 | 0.0000 | 1.0000 | — |
| `mid_cap_trap_risk` | 0.00% | 0.89% | 0.0937 | 0.0089 | 0.0000 | 1.0000 | NEAR_CONST |
| `buy_rise_divergence` | 0.00% | 4.54% | 0.2082 | 0.0454 | 0.0000 | 1.0000 | — |
| `bet_decline_exhaustion` | 0.00% | 0.44% | 0.0664 | 0.0044 | 0.0000 | 1.0000 | NEAR_CONST |
| `board_keep_break_signal` | 0.00% | 9.90% | 0.3105 | -0.0513 | -1.0000 | 1.0000 | — |
| `one_day_trip_risk_proxy` | 0.00% | 0.59% | 0.0764 | 0.0059 | 0.0000 | 1.0000 | NEAR_CONST |

---

## 4. Near-Constant Summary

Features with std < 1e-8 or nonzero_pct < 1%.

| Family | Column | Reason |
|--------|--------|--------|
| tushare | `tushare_holder_num` | std=0.00e+00, nonzero=0.00% |
| tushare | `tushare_holder_num_delta_pct` | std=0.00e+00, nonzero=0.00% |
| research_daily | `seal_rate_80_threshold` | nonzero=0.09% |
| research_daily | `no_theme_rotation_mode` | nonzero=0.93% |
| research_daily | `money_effect_sector_rotation` | nonzero=0.78% |
| research_daily | `mid_cap_trap_risk` | nonzero=0.89% |
| research_daily | `bet_decline_exhaustion` | nonzero=0.44% |
| research_daily | `one_day_trip_risk_proxy` | nonzero=0.59% |

---

## 5. High NaN (>30%) Summary

| Family | Column | NaN% |
|--------|--------|------|
| — | (none) | — |

---

## 6. High Correlation with Selected 260 (|r| >= 0.90)

| Target Column | Correlated With | r |
|---------------|----------------|---|
| `market_limit_down_rate` | `market_limit_down_count` | 1.0000 |
| `market_limit_seal_success_rate` | `market_broken_board_rate` | -1.0000 |

---

## 7. Summary & Recommendations

### Tushare Daily Factors

- **39** base columns present in research feature cache (out of 39 target)
- **2** flagged as near-constant
- **0** have |r| >= 0.90 correlation with selected 260
- Raw cache covers 13 API endpoints

### Research Daily Factors

- **47** base columns present in research feature cache (out of 47 target)
- **6** flagged as near-constant
- **2** have |r| >= 0.90 correlation with selected 260
- These are market-level daily factors — same value for all stocks on a given date

### Ablation Priority

Per `unused_factor_family_audit_20260503.md` recommendations:

1. **Research Daily (Tier 1)**: 47 base columns, 100% coverage, zero external dependency.
   Several members showed signal in prior research runs. Recommend as first ablation target.

2. **Tushare Tier 1** (high coverage): `daily_basic`(2), `stk_limit`(3), `stk_auction`(4), `moneyflow`(5) = 14 base columns.
   All have 804 daily cache files (2023-01-03 ~ 2026-04-30).

3. **Tushare Tier 2** (medium coverage): `cyq_perf`(3), `margin_detail`(5), `stk_holdernumber`(2) = 10 base columns.

4. **Tushare Tier 3** (sparse): `limit_list_d`(6), `top_list_inst`(5), `hk_hold`(2), `ths_hot`(2) = 15 base columns.
   `hk_hold` starts later and has fewer dates; `ths_hot` starts 2023-08-21.

5. **NOT recommended**: `stk_mins_5` (18% stock coverage, excluded from this audit).

### Discipline

- This is a **seen_research diagnostic only** — no forward or passed implications.
- Frozen config `gpu_probe_20260501T155956Z_d64e3464` remains unchanged.
- Any ablation runs must follow forward_runbook.md protocol.

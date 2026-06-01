# Minute Factor Variant Manifest — Q1 2026

**Date**: 2026-05-06
**Total variants**: 32 (2^5 combinations of C133/C134/C136/C137/C138)
**Immutable**: YES — no additions/deletions after creation

---

## Fixed Config (all variants)

| Parameter | Value |
|-----------|-------|
| start | 2023-05-01 |
| train_end | 2025-12-31 |
| test_start | 2026-01-01 |
| end | 2026-03-31 |
| feature_set | research |
| exclude_feature_prefix | ("cross_",) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| label_target | next_high_from_close |
| target_high_return_pct | 1.0 |
| max_selected_features | 260 |
| feature_selection_method | stable_tail |
| selector_coverage_weight | 0.02 |
| seed | 42 |
| lockbox_role | seen_research |
| final_acceptance_eligible | False |

---

## Variant Table

| # | Variant | Bits | Included Factors | Description |
|---|---------|:----:|-----------------|-------------|
| 1 | M00_none | 00 | none | baseline (no minute factors) |
| 2 | M01_C133 | 01 | C133 | C133=last_30min_return |
| 3 | M02_C134 | 02 | C134 | C134=first_15min_volume_ratio |
| 4 | M04_C136 | 04 | C136 | C136=intraday_volatility |
| 5 | M08_C137 | 08 | C137 | C137=up_volume_ratio |
| 6 | M16_C138 | 16 | C138 | C138=high_time_pct |
| 7 | M03_C133_C134 | 03 | C133 + C134 | C133=last_30min_return, C134=first_15min_volume_ratio |
| 8 | M05_C133_C136 | 05 | C133 + C136 | C133=last_30min_return, C136=intraday_volatility |
| 9 | M09_C133_C137 | 09 | C133 + C137 | C133=last_30min_return, C137=up_volume_ratio |
| 10 | M17_C133_C138 | 17 | C133 + C138 | C133=last_30min_return, C138=high_time_pct |
| 11 | M06_C134_C136 | 06 | C134 + C136 | C134=first_15min_volume_ratio, C136=intraday_volatility |
| 12 | M10_C134_C137 | 10 | C134 + C137 | C134=first_15min_volume_ratio, C137=up_volume_ratio |
| 13 | M18_C134_C138 | 18 | C134 + C138 | C134=first_15min_volume_ratio, C138=high_time_pct |
| 14 | M12_C136_C137 | 12 | C136 + C137 | C136=intraday_volatility, C137=up_volume_ratio |
| 15 | M20_C136_C138 | 20 | C136 + C138 | C136=intraday_volatility, C138=high_time_pct |
| 16 | M24_C137_C138 | 24 | C137 + C138 | C137=up_volume_ratio, C138=high_time_pct |
| 17 | M07_C133_C134_C136 | 07 | C133 + C134 + C136 | C133=last_30min_return, C134=first_15min_volume_ratio, C136=intraday_volatility |
| 18 | M11_C133_C134_C137 | 11 | C133 + C134 + C137 | C133=last_30min_return, C134=first_15min_volume_ratio, C137=up_volume_ratio |
| 19 | M19_C133_C134_C138 | 19 | C133 + C134 + C138 | C133=last_30min_return, C134=first_15min_volume_ratio, C138=high_time_pct |
| 20 | M13_C133_C136_C137 | 13 | C133 + C136 + C137 | C133=last_30min_return, C136=intraday_volatility, C137=up_volume_ratio |
| 21 | M21_C133_C136_C138 | 21 | C133 + C136 + C138 | C133=last_30min_return, C136=intraday_volatility, C138=high_time_pct |
| 22 | M25_C133_C137_C138 | 25 | C133 + C137 + C138 | C133=last_30min_return, C137=up_volume_ratio, C138=high_time_pct |
| 23 | M14_C134_C136_C137 | 14 | C134 + C136 + C137 | C134=first_15min_volume_ratio, C136=intraday_volatility, C137=up_volume_ratio |
| 24 | M22_C134_C136_C138 | 22 | C134 + C136 + C138 | C134=first_15min_volume_ratio, C136=intraday_volatility, C138=high_time_pct |
| 25 | M26_C134_C137_C138 | 26 | C134 + C137 + C138 | C134=first_15min_volume_ratio, C137=up_volume_ratio, C138=high_time_pct |
| 26 | M28_C136_C137_C138 | 28 | C136 + C137 + C138 | C136=intraday_volatility, C137=up_volume_ratio, C138=high_time_pct |
| 27 | M15_C133_C134_C136_C137 | 15 | C133 + C134 + C136 + C137 | C133=last_30min_return, C134=first_15min_volume_ratio, C136=intraday_volatility, C137=up_volume_ratio |
| 28 | M23_C133_C134_C136_C138 | 23 | C133 + C134 + C136 + C138 | C133=last_30min_return, C134=first_15min_volume_ratio, C136=intraday_volatility, C138=high_time_pct |
| 29 | M27_C133_C134_C137_C138 | 27 | C133 + C134 + C137 + C138 | C133=last_30min_return, C134=first_15min_volume_ratio, C137=up_volume_ratio, C138=high_time_pct |
| 30 | M29_C133_C136_C137_C138 | 29 | C133 + C136 + C137 + C138 | C133=last_30min_return, C136=intraday_volatility, C137=up_volume_ratio, C138=high_time_pct |
| 31 | M30_C134_C136_C137_C138 | 30 | C134 + C136 + C137 + C138 | C134=first_15min_volume_ratio, C136=intraday_volatility, C137=up_volume_ratio, C138=high_time_pct |
| 32 | M31_C133_C134_C136_C137_C138 | 31 | C133 + C134 + C136 + C137 + C138 | C133=last_30min_return, C134=first_15min_volume_ratio, C136=intraday_volatility, C137=up_volume_ratio, C138=high_time_pct |

---

## Factor Reference

| Factor ID | Name | Value Column | Available Column |
|-----------|------|--------------|-----------------|
| C133 | last_30min_return | tushare_last_30min_return | tushare_last_30min_return_available |
| C134 | first_15min_volume_ratio | tushare_first_15min_volume_ratio | tushare_first_15min_volume_ratio_available |
| C136 | intraday_volatility | tushare_intraday_volatility | tushare_intraday_volatility_available |
| C137 | up_volume_ratio | tushare_up_volume_ratio | tushare_up_volume_ratio_available |
| C138 | high_time_pct | tushare_high_time_pct | tushare_high_time_pct_available |

---

*This manifest is frozen. No variants may be added or removed during this experiment round.*
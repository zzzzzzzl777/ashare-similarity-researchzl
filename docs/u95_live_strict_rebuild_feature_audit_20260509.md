# U95 Live-Strict Rebuild — Feature Pool Audit

**Date**: 2026-05-09  
**Source**: U95 bundle `gpu_probe_20260505T113406Z_bb25159b` (376 features)  
**Verdict**: **350 allowed features — SUFFICIENT for rebuild**

---

## Summary

| Metric | Value |
|--------|-------|
| Total feature pool | 376 |
| Forbidden | 26 |
| Allowed | 350 |
| Target selected features | 240–260 |
| Ratio (allowed / target) | 134.6% |
| All allowed in feature cache | YES (all 350 present) |
| Feature cache | `gpu_probe_features_665406333a7e545d.parquet` (795 cols) |

---

## Forbidden Features (26)

### HARD_MONEYFLOW (14 features)

| Feature | Reason |
|---------|--------|
| `tushare_net_mf_amount` | T-day moneyflow; user rule C004 |
| `tushare_net_mf_amount_available` | Availability flag |
| `tushare_lg_buy_sell_ratio` | T-day large buy/sell ratio |
| `tushare_lg_buy_sell_ratio_available` | Availability flag |
| `tushare_elg_buy_sell_ratio` | T-day extra-large buy/sell ratio |
| `tushare_elg_buy_sell_ratio_available` | Availability flag |
| `tushare_mf_strength` | T-day moneyflow strength |
| `tushare_mf_strength_available` | Availability flag |
| `tushare_sm_sell_pressure` | T-day small sell pressure |
| `tushare_sm_sell_pressure_available` | Availability flag |
| `tushare_main_force_divergence` | T-day main force divergence |
| `tushare_main_force_divergence_available` | Availability flag |
| `tushare_ff_adjusted_flow` | T-day free-float adjusted flow |
| `tushare_ff_adjusted_flow_available` | Availability flag |

**Note**: The live script computes T-1 proxies from tushare moneyflow cache, but user instruction explicitly requires full exclusion of all 14 hard moneyflow features from the model's selected set.

### THS_SECTOR (12 features)

| Feature | Reason |
|---------|--------|
| `sector_pct_change_best` | After-close THS concept data |
| `sector_pct_change_best_available` | Availability flag |
| `sector_strength_rank` | After-close THS concept data |
| `sector_strength_rank_available` | Availability flag |
| `sector_limit_up_count` | After-close THS concept data |
| `sector_limit_up_count_available` | Availability flag |
| `sector_divergence` | After-close THS concept data |
| `sector_divergence_available` | Availability flag |
| `sector_duration_days` | After-close THS concept data |
| `sector_duration_days_available` | Availability flag |
| `sector_climax_signal` | After-close THS concept data |
| `sector_climax_signal_available` | Availability flag |

**Data source**: `build_ths_sector_factors()` — `asof_time="after_close"`, published after 15:00. Zero-filled at 14:57.

---

## Allowed Features — Live Executability

### Categories of Allowed Features (350 total)

| Category | Examples | 14:57 Source |
|----------|----------|--------------|
| Returns/momentum | `ret_1`, `ret_5`, `ret_20` | Historical bars (T-1) |
| Volume/amount | `amount_z_20`, `turnover_*` | Historical bars (T-1) |
| Volatility | `atr_14_pct`, `bollinger_*` | Historical bars (T-1) |
| Technical indicators | `rsi_14`, `macd_*`, `adx_14` | Historical bars (T-1) |
| Pattern features | `breakdown_20`, `board_*` | Historical bars (T-1) |
| Chip/cost | `cost_position_20`, `cost_position_60` | Bar-derived (close range position) |
| Tushare daily | `tushare_free_share`, `tushare_volume_ratio` | T-1 daily_basic cache |
| Limit distance | `tushare_up_limit_distance`, `tushare_down_limit_distance` | Bar-derived |
| Board/limit pool | `board_count`, `board_promoted_today` | Historical limit data |
| Cross-sectional rank | `cs_ret_*_rank`, `cs_amount_*` | Computed from universe bars |
| Regime/streak | `up_streak_*`, `down_streak_*` | Historical bars (T-1) |

### Chip/Cost T-1 Features

| Feature | Source | Available at 14:57? |
|---------|--------|---------------------|
| `cost_position_20` | Bar-derived (close position in 20-day high-low range) | YES (T-1 bars) |
| `cost_position_60` | Bar-derived (close position in 60-day high-low range) | YES (T-1 bars) |

Note: `tushare_cost_concentration` and `tushare_cost_position` (from tushare `cyq_perf`) are NOT in U95's 376-feature pool. They would appear in the expanded 735-feature pool only.

---

## Conclusion

The allowed feature pool (350 features) is **well above** the target selection size (240-260). The rebuild can proceed with confidence that:

1. All 350 features exist in the feature cache for train/validation
2. All 350 features are computable at 14:57 from T-1 historical data
3. No forbidden features need to be retained for pool adequacy
4. The ratio of 350/260 = 134.6% provides sufficient selection headroom

**Next step**: Build `run_u95_live_strict_rebuild.py` training script with this 350-feature pool as input.

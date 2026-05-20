# Phase 7 Layer 2: S2 Factor Combination Search - 2026-05-09

## Base Policy: S1_14 (chip=T1, hot=del, tgb=del, ths=live_pool)

## Baseline: all 18 factors W95=0.7546

## Single Factor Ablation

| Factor ID | Column | W95 after removal | Delta | Impact |
|-----------|--------|-------------------|-------|--------|
| C133 | tushare_last_30min_return | 0.7346 | -0.02 | HARMFUL (keep) |
| C136 | tushare_intraday_volatility | 0.7426 | -0.0119 | HARMFUL (keep) |
| C159 | tushare_asr_60d | 0.7454 | -0.0092 | HARMFUL (keep) |
| C137 | tushare_up_volume_ratio | 0.7478 | -0.0067 | HARMFUL (keep) |
| C138 | tushare_high_time_pct | 0.7479 | -0.0067 | HARMFUL (keep) |
| C152 | tushare_multi_wave_count_60d | 0.7495 | -0.0051 | HARMFUL (keep) |
| C011 | tushare_auction_open_vwap_ratio | 0.7501 | -0.0045 | HARMFUL (keep) |
| C161 | tushare_illiq_classic_20d | 0.7505 | -0.004 | HARMFUL (keep) |
| C154 | tushare_price_vs_cost_20d | 0.7514 | -0.0031 | HARMFUL (keep) |
| C004 | tushare_ff_adjusted_flow | 0.7525 | -0.0021 | HARMFUL (keep) |
| C151 | tushare_anti_drop_strength_20d | 0.7541 | -0.0004 | NEUTRAL |
| C134 | tushare_first_15min_volume_ratio | 0.7556 | 0.0011 | HELPFUL (remove) |
| C156 | tushare_abnormal_3d_deviation | 0.7567 | 0.0021 | HELPFUL (remove) |
| C158 | tushare_inv_t_20d | 0.758 | 0.0035 | HELPFUL (remove) |
| C141 | tushare_prev_top20_chase_mean | 0.7583 | 0.0038 | HELPFUL (remove) |
| C143 | tushare_volume_sufficiency_ratio | 0.7596 | 0.005 | HELPFUL (remove) |
| C162 | tushare_ato_120d | 0.7601 | 0.0055 | HELPFUL (remove) |
| C157 | tushare_vol_gain_20d | 0.7607 | 0.0061 | HELPFUL (remove) |

## Greedy Backward Path

| Step | Removed | Remaining | W95 |
|------|---------|-----------|-----|
| 0 | - | 18 | 0.7546 |
| 1 | C157 | 17 | 0.7607 |
| 2 | C134 | 16 | 0.7629 |
| 3 | C011 | 15 | 0.7656 |

## Greedy Forward Path (from M1457_top8)

| Step | Added | Total | W95 |
|------|-------|-------|-----|
| 0 | - | 8 | 0.7668 |
| 1 | C138 | 9 | 0.7731 |

## Top 10 Variants

| # | Variant | Factors | W95 | Pass |
|---|---------|---------|-----|------|
| 1 | S2_fw_step1_try_add_C138 | 9 | 0.7731 | YES |
| 2 | S2_ref_m1457_top8 | 8 | 0.7668 | YES |
| 3 | S2_bw_step3_try_rm_C011 | 15 | 0.7656 | YES |
| 4 | S2_fw_step1_try_add_C137 | 9 | 0.7655 | YES |
| 5 | S2_bw_step2_try_rm_C134 | 16 | 0.7629 | YES |
| 6 | S2_fw_step1_try_add_C136 | 9 | 0.7612 | YES |
| 7 | S2_bw_step2_try_rm_C136 | 16 | 0.7611 | YES |
| 8 | S2_fw_step1_try_add_C004 | 9 | 0.761 | YES |
| 9 | S2_ablate_C157 | 17 | 0.7607 | YES |
| 10 | S2_bw_step2_try_rm_C138 | 16 | 0.7606 | YES |

## Best Result

- Variant: S2_fw_step1_try_add_C138
- Wilson 95%: 0.7731
- Factor IDs: ['C154', 'C156', 'C134', 'C011', 'C138', 'C133', 'C161', 'C159', 'C158']
- Factor count: 9
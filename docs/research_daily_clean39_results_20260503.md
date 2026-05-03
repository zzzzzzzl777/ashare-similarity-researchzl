# Research Daily Clean 39 Results

> Generated: 2026-05-03T13:01:11.331510+00:00
> Experiment: research_daily_clean39
> diagnostic_monkey_patch: true
> lockbox_role: seen_research only — NOT final_unseen, NOT passed, NOT frozen

## Parameters

| Parameter | Value |
|-----------|-------|
| start | 2023-05-01 |
| train_end | 2025-06-30 |
| test_start | 2025-07-01 |
| end | 2026-04-30 |
| train_rows | 300,000 |
| test_rows | 120,000 |
| label_target | next_high_from_close |
| target_high_return_pct | 1.0 |
| feature_selection_method | stable_tail |
| max_selected_features | 260 |
| selector_coverage_weight | 0.02 |
| candidate_family | all |
| lockbox_role | seen_research |
| exclude_event_limit_up | True |
| exclude_feature_prefix | ["cross_"] |
| seed | 42 |
| feature_set (for cache) | research |
| model_input_pool | GPU_PROBE_STABLE_FEATURES + 78 research daily clean39 |
| extra_base_columns | 39 (47 full - 6 near-constant - 2 redundant) |
| extra_total_columns | 78 (39 base + 39 _available) |

## Excluded Columns (8)

### Near-constant (6)

| Column | Nonzero% | Reason |
|--------|----------|--------|
| `seal_rate_80_threshold` | 0.09% | binary < 1 in 1000 |
| `no_theme_rotation_mode` | 0.93% | near-constant |
| `money_effect_sector_rotation` | 0.78% | near-constant |
| `mid_cap_trap_risk` | 0.89% | near-constant |
| `bet_decline_exhaustion` | 0.44% | near-constant |
| `one_day_trip_risk_proxy` | 0.59% | near-constant |

### Redundant with selected 260 (2)

| Column | Correlated With | r |
|--------|----------------|---|
| `market_limit_down_rate` | `market_limit_down_count` | 1.0000 |
| `market_limit_seal_success_rate` | `market_broken_board_rate` | -1.0000 |

## Comparison Table

| | baseline | dirty94 | complete14 | **clean39** |
|---|---|---|---|---|
| **run_id** | `gpu_probe_20260503T113328Z_1b272829` | `gpu_probe_20260503T113537Z_058b885e` | `gpu_probe_20260503T123107Z_b05caa22` | `gpu_probe_20260503T130111Z_6c1306d3` |
| **input features** | 352 | 446 | 380 | 430 |
| **family_in / family_sel** | 0/0 | 94/32 | 28/10 | 78/30 |
| **HC accuracy** | 75.40% | 74.30% | 76.59% | 75.51% |
| **Wilson 95 lower** | 74.74% | 73.66% | 75.94% | 74.86% |
| **HC count** | 16206 | 18268 | 16290 | 17020 |
| **HC coverage** | 13.51% | 15.22% | 13.58% | 14.18% |
| **HC Brier** | — | — | 0.1803 | 0.1958 |
| **All Brier** | 0.2254 | 0.2267 | 0.2238 | 0.2279 |

## Delta vs Baseline

| Metric | Delta |
|--------|-------|
| HC accuracy | +0.001070 (0.7540 -> 0.7551) |
| Wilson 95 lower | +0.001242 (0.7474 -> 0.7486) |
| HC count | +814 (16206 -> 17020) |
| HC coverage | +0.006783 (0.1351 -> 0.1418) |
| All Brier | +0.002446 (0.2254 -> 0.2279) |

## Delta vs Dirty94 (full 47 base)

| Metric | Delta |
|--------|-------|
| HC accuracy | +0.012119 (0.7430 -> 0.7551) |
| Wilson 95 lower | +0.011988 (0.7366 -> 0.7486) |
| HC count | -1248 (18268 -> 17020) |
| HC coverage | -0.010400 (0.1522 -> 0.1418) |
| All Brier | +0.001166 (0.2267 -> 0.2279) |

## Delta vs Tushare Complete14

| Metric | Delta |
|--------|-------|
| HC accuracy | -0.010818 (0.7659 -> 0.7551) |
| Wilson 95 lower | -0.010772 (0.7594 -> 0.7486) |
| HC count | +730 (16290 -> 17020) |
| HC coverage | +0.006083 (0.1358 -> 0.1418) |
| All Brier | +0.004097 (0.2238 -> 0.2279) |

## Column Diagnostic (78 features)

| Column | In Input | Selected | Base? | Skipped | Reason |
|--------|----------|----------|-------|---------|--------|
| `market_one_word_board_count` | True | True | base | False |  |
| `market_high_leader_crash_count` | True | True | base | False |  |
| `cycle_day_count` | True | True | base | False |  |
| `divergence_day_count` | True | True | base | False |  |
| `buy_sell_cycle_phase` | True | True | base | False |  |
| `liquidity_exhaustion_signal` | True | True | base | False |  |
| `market_split_signal` | True | False | base | False |  |
| `quant_climax_type` | True | True | base | False |  |
| `vol_stagnation_signal` | True | False | base | False |  |
| `bull_rotation_upgrade` | True | True | base | False |  |
| `theme_capacity_score` | True | True | base | False |  |
| `market_amount_ratio_20` | True | True | base | False |  |
| `market_amount_percentile_60` | True | True | base | False |  |
| `volume_is_king_signal` | True | True | base | False |  |
| `ground_volume_risk` | True | False | base | False |  |
| `post_decline_transition` | True | True | base | False |  |
| `decline_stabilize_signal` | True | True | base | False |  |
| `weak_friday_risk` | True | True | base | False |  |
| `prev_top20_chase_return` | True | True | base | False |  |
| `prev_top20_chase_win_rate` | True | True | base | False |  |
| `prev_bottom20_rebound_return` | True | True | base | False |  |
| `money_effect_spread_20` | True | True | base | False |  |
| `collapse_warning_signal` | True | False | base | False |  |
| `bullish_pivot_recognition` | True | True | base | False |  |
| `limit_premium_failure_signal` | True | True | base | False |  |
| `bad_sentiment_no_sweep` | True | False | base | False |  |
| `high_leader_crash_sentiment_collapse` | True | False | base | False |  |
| `full_position_trigger` | True | True | base | False |  |
| `late_cycle_position_cap` | True | True | base | False |  |
| `bear_position_reduction` | True | True | base | False |  |
| `strong_market_regime` | True | True | base | False |  |
| `weak_market_oversold_regime` | True | True | base | False |  |
| `bull_hotspot_bear_oversold` | True | True | base | False |  |
| `shrink_after_rotten` | True | True | base | False |  |
| `explosive_vol_next_weak` | True | True | base | False |  |
| `break_node_new_dragon` | True | False | base | False |  |
| `dragon_replace_signal` | True | False | base | False |  |
| `buy_rise_divergence` | True | True | base | False |  |
| `board_keep_break_signal` | True | False | base | False |  |
| `market_one_word_board_count_available` | True | False | _avail | False |  |
| `market_high_leader_crash_count_available` | True | False | _avail | False |  |
| `cycle_day_count_available` | True | False | _avail | False |  |
| `divergence_day_count_available` | True | False | _avail | False |  |
| `buy_sell_cycle_phase_available` | True | False | _avail | False |  |
| `liquidity_exhaustion_signal_available` | True | False | _avail | False |  |
| `market_split_signal_available` | True | False | _avail | False |  |
| `quant_climax_type_available` | True | False | _avail | False |  |
| `vol_stagnation_signal_available` | True | False | _avail | False |  |
| `bull_rotation_upgrade_available` | True | False | _avail | False |  |
| `theme_capacity_score_available` | True | False | _avail | False |  |
| `market_amount_ratio_20_available` | True | False | _avail | False |  |
| `market_amount_percentile_60_available` | True | False | _avail | False |  |
| `volume_is_king_signal_available` | True | False | _avail | False |  |
| `ground_volume_risk_available` | True | False | _avail | False |  |
| `post_decline_transition_available` | True | False | _avail | False |  |
| `decline_stabilize_signal_available` | True | False | _avail | False |  |
| `weak_friday_risk_available` | True | False | _avail | False |  |
| `prev_top20_chase_return_available` | True | False | _avail | False |  |
| `prev_top20_chase_win_rate_available` | True | False | _avail | False |  |
| `prev_bottom20_rebound_return_available` | True | False | _avail | False |  |
| `money_effect_spread_20_available` | True | False | _avail | False |  |
| `collapse_warning_signal_available` | True | False | _avail | False |  |
| `bullish_pivot_recognition_available` | True | False | _avail | False |  |
| `limit_premium_failure_signal_available` | True | False | _avail | False |  |
| `bad_sentiment_no_sweep_available` | True | False | _avail | False |  |
| `high_leader_crash_sentiment_collapse_available` | True | False | _avail | False |  |
| `full_position_trigger_available` | True | False | _avail | False |  |
| `late_cycle_position_cap_available` | True | False | _avail | False |  |
| `bear_position_reduction_available` | True | False | _avail | False |  |
| `strong_market_regime_available` | True | False | _avail | False |  |
| `weak_market_oversold_regime_available` | True | False | _avail | False |  |
| `bull_hotspot_bear_oversold_available` | True | False | _avail | False |  |
| `shrink_after_rotten_available` | True | False | _avail | False |  |
| `explosive_vol_next_weak_available` | True | False | _avail | False |  |
| `break_node_new_dragon_available` | True | False | _avail | False |  |
| `dragon_replace_signal_available` | True | False | _avail | False |  |
| `buy_rise_divergence_available` | True | False | _avail | False |  |
| `board_keep_break_signal_available` | True | False | _avail | False |  |

**Selection summary**: 30/39 clean39 base columns selected.

## Conclusion

### Acceptance Gates (seen_research, 120k setting)

| Gate | Threshold | Clean39 | Pass? |
|------|-----------|---------|-------|
| HC accuracy | >= 75% | 75.51% | YES (barely) |
| Wilson 95 lower | >= 75% | 74.86% | **NO** (-0.14pp) |
| Brier < baseline_brier | < 0.2303 | 0.2279 | YES (naive baseline) |
| Brier < baseline variant | < 0.2254 | 0.2279 | **NO** (+0.0025) |
| HC count | >= 10,000 | 17,020 | YES |
| HC coverage | >= 10% | 14.18% | YES |

**Wilson gate fails** at 74.86% (threshold 75%). Brier is worse than the baseline variant.

### vs Baseline: essentially flat, Brier worsened

HC accuracy +0.1pp and Wilson +0.1pp are within noise. HC count grew +814 and coverage +0.7pp, but Brier worsened by +0.0024. The 30 selected clean39 base columns displaced 30 baseline features with a net-neutral-to-negative tradeoff.

### vs Dirty94: cleaning helped, but not enough

Removing 6 near-constant + 2 redundant columns improved HC accuracy by +1.2pp over dirty94 (74.30% -> 75.51%), confirming the hypothesis that bad columns poison feature selection. However, the clean version still doesn't beat the no-research-daily baseline on Brier.

### vs Complete14: clearly weaker

Clean39 is -1.1pp HC accuracy, -1.1pp Wilson, +0.004 Brier below complete14. Complete14 dominates on every accuracy metric while maintaining comparable count/coverage.

### Recommendation

Clean39 does **not** justify entering combined with complete14:
- Wilson gate fails (74.86% < 75%)
- Brier worsened vs baseline (+0.0025)
- Accuracy gain is negligible (+0.1pp)
- Complete14 is strictly better on accuracy and Brier

**Complete14 (`b05caa22`) remains the sole viable seen_research candidate.** Per ablation plan: "if neither A nor B shows improvement, do not run C." Clean39 does not show meaningful improvement over baseline, so combined is not warranted.

## Constraints Confirmation

- [x] frozen_forward_config.json NOT modified
- [x] diagnostic_monkey_patch = true
- [x] lockbox_role = seen_research
- [x] No run claims 'passed'
- [x] baseline, dirty94, complete14 from prior results (not re-run)
- [x] 6 near-constant + 2 redundant columns excluded from clean set

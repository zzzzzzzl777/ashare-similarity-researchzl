# Feature Family Audit — Code-Derived Grouping

> Generated: 2026-05-03 10:51 UTC
> Run: `gpu_probe_20260503T093827Z_594a3d7d`
> feature_set: `expanded` → dispatches to `GPU_PROBE_STABLE_FEATURES`
> lockbox_role: `seen_research` (NOT final_unseen, NOT passed)
> exclude_feature_prefix: `['cross_']`

---

## 1. Pool Sizes (Raw vs Unique)

| Constant | Raw | Unique | Duplicates? |
|----------|-----|--------|-------------|
| `GPU_PROBE_FEATURES` | 450 | 435 | YES |
| `GPU_PROBE_STABLE_FEATURES` | 370 | 370 | no |
| `GPU_PROBE_BASE_FEATURES` | 338 | 338 | no |
| `GPU_PROBE_RESEARCH_FEATURES` | 790 | 775 | YES |
| `GPU_PROBE_FREE_FACTOR_FEATURES` | 170 | 170 | no |
| `GPU_PROBE_RESEARCH_FREE_FACTOR_FEATURES` | 360 | 360 | no |
| `GPU_PROBE_STABLE_DAILY_FACTOR_FEATURES` | 112 | 112 | no |
| `GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES` | 94 | 94 | no |
| `GPU_PROBE_TGB_FACTOR_FEATURES` | 28 | 28 | no |
| `GPU_PROBE_THS_SECTOR_FEATURES` | 12 | 12 | no |
| `GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES` | 96 | 96 | no |
| `GPU_PROBE_INTRADAY_FACTOR_FEATURES` | 58 | 58 | no |
| `GPU_PROBE_TUSHARE_FACTOR_FEATURES` | 92 | 92 | no |
| `GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS` | 40 | 40 | no |
| `GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS` | 25 | 25 | no |
| `GPU_PROBE_CROSS_MARKET_FEATURES` | 9 | 9 | no |

## 2. Set Arithmetic

| Set | Count |
|-----|-------|
| current_input (artifact result.features) | 352 |
| selected (feature_selection.selected_features) | 260 |
| input_unselected (current_input − selected) | 92 |
| research_raw (GPU_PROBE_RESEARCH_FEATURES raw len) | 790 |
| research_unique | 775 |
| research_not_in_current (research_unique − current_input) | 423 |

## 3. Official Intersection Table (Non-Mutually-Exclusive)

Each row shows how a **code-defined constant set** intersects with current_input / selected.
Features CAN appear in multiple families (constants overlap by design).

| Family | Unique | In Input | Selected | Unselected | Not In Input | Ex. Selected | Ex. Not-In-Input |
|--------|--------|----------|----------|------------|--------------|--------------|------------------|
| cross_market | 18 | 0 | 0 | 0 | 18 | — | cross_sh000001_ret_1, cross_sh000001_ret_1_available |
| tgb | 28 | 28 | 11 | 17 | 0 | tgb_eod_rush_risk, tgb_ma_alignment_score | — |
| ths_sector | 12 | 12 | 12 | 0 | 0 | sector_climax_signal, sector_climax_signal_available | — |
| stable_daily_factor | 112 | 112 | 45 | 67 | 0 | board_height_suppression, consecutive_high_premium_days | — |
| research_daily_factor | 94 | 0 | 0 | 0 | 94 | — | bad_sentiment_no_sweep, bad_sentiment_no_sweep_available |
| limit_pool | 96 | 0 | 0 | 0 | 96 | — | board_height_real, board_height_real_available |
| intraday | 58 | 0 | 0 | 0 | 58 | — | minute_afternoon_start_return, minute_afternoon_start_return_available |
| tushare | 92 | 0 | 0 | 0 | 92 | — | tushare_auction_close_vol, tushare_auction_close_vol_available |
| research_symbol_proxy | 40 | 0 | 0 | 0 | 40 | — | active_turnover_freq_60, amount_300m_turnover_quality |
| research_cross_section | 25 | 0 | 0 | 0 | 25 | — | breakout_first_board_proxy, bull_hotspot_bear_oversold_signal |
| free_factor_features | 170 | 152 | 68 | 84 | 18 | board_height_suppression, consecutive_high_premium_days | cross_sh000001_ret_1, cross_sh000001_ret_1_available |
| research_free_factor_features | 360 | 152 | 68 | 84 | 208 | board_height_suppression, consecutive_high_premium_days | bad_sentiment_no_sweep, bad_sentiment_no_sweep_available |

## 4. Owner Assignment Table (Mutually Exclusive, First-Match)

Each feature assigned to exactly one family by priority order.
Total assigned: 775, research_unique: 775, orphans: 0

| Family | Owned | In Input | Selected | Unselected | Not In Input |
|--------|-------|----------|----------|------------|--------------|
| cross_market | 18 | 0 | 0 | 0 | 18 |
| tgb | 28 | 28 | 11 | 17 | 0 |
| ths_sector | 12 | 12 | 12 | 0 | 0 |
| stable_daily_factor | 112 | 112 | 45 | 67 | 0 |
| research_daily_factor | 94 | 0 | 0 | 0 | 94 |
| limit_pool | 96 | 0 | 0 | 0 | 96 |
| intraday | 58 | 0 | 0 | 0 | 58 |
| tushare | 92 | 0 | 0 | 0 | 92 |
| research_symbol_proxy | 40 | 0 | 0 | 0 | 40 |
| research_cross_section | 25 | 0 | 0 | 0 | 25 |
| core_price_volume | 200 | 200 | 192 | 8 | 0 |

## 5. Fact Verification

### [PASS] expanded maps to GPU_PROBE_STABLE_FEATURES

- artifact feature_set = 'expanded'

### [PASS] stable excludes research_symbol AND research_cross_section

- stable ∩ research_symbol = 0, stable ∩ research_cs = 0

### [PASS] exclude_feature_prefix=[cross_] removed cross_ features from current_input

- exclude_feature_prefix = ['cross_'], cross_ features in stable = 18, cross_ features in current_input = 0

### [PASS] expanded / current_input reconciliation

- **stable_unique**: 370
- **excluded_by_prefix**: 18
- **excluded_by_prefix_features**: 18 items
- **stable_after_prefix_exclusion**: 352
- **current_input_count**: 352
- **stable_only_missing_from_current**: []
- **current_not_in_stable**: []
- **dropped_or_unexpected**: []

### [PASS] family presence in current_input

- **tgb_in_current**: 28
- **ths_sector_in_current**: 12
- **stable_daily_in_current**: 112
- **tushare_in_current**: 0
- **intraday_in_current**: 0
- **limit_pool_in_current**: 0
- **research_daily_in_current**: 0
- **research_symbol_in_current**: 0
- **research_cs_in_current**: 0

## 6. Tushare Sub-Source Breakdown

| API | Base Cols | +Avail | Cache Parquets | Coverage Note | In Input | Selected |
|-----|-----------|--------|----------------|---------------|----------|----------|
| moneyflow | 5 | 10 | 804 | high (~100% stock-day coverage) | 0 | 0 |
| limit_list_d | 6 | 12 | 804 | sparse (~2% stock-day; only limit-up stocks per day) | 0 | 0 |
| top_list_inst | 5 | 10 | 804 | sparse (~2% stock-day; only Dragon Tiger stocks) | 0 | 0 |
| hk_hold | 2 | 4 | 774 | ~17% stock-day (northbound-held stocks only) | 0 | 0 |
| margin_detail | 5 | 10 | 804 | ~36% stock-day (margin-eligible stocks only) | 0 | 0 |
| ths_hot | 2 | 4 | 623 | ~25% stock-day (hot-list stocks only) | 0 | 0 |
| daily_basic | 2 | 4 | 804 | high (~100% stock-day) | 0 | 0 |
| cyq_perf | 3 | 6 | 3194 | ~55% stock-day (chip analysis coverage) | 0 | 0 |
| stk_auction | 4 | 8 | 0 | high (~100% stock-day) | 0 | 0 |
| holdernumber | 2 | 4 | 0 | quarterly release, ~high stock coverage per report | 0 | 0 |
| stk_limit | 3 | 6 | 804 | high (~100% stock-day) | 0 | 0 |
| stk_mins_5 | 7 | 14 | 679 | ~18% stock coverage (514 full + 82 partial / 3195 stocks) | 0 | 0 |

Sub-source base column sum: 46 (should equal TUSHARE_FACTOR_COLUMNS unique base: 46)

## 7. Input-Unselected Features (the 92)

| Feature | Owner Family | Reason |
|---------|-------------|--------|
| `board_count` | stable_daily_factor | near_constant (nonzero_rate=0.0, std=0.0) |
| `board_count_available` | stable_daily_factor | availability_flag_low_variance |
| `board_height_suppression_available` | stable_daily_factor | availability_flag_low_variance |
| `board_promoted_today` | stable_daily_factor | near_constant (nonzero_rate=0.0, std=0.0) |
| `board_promoted_today_available` | stable_daily_factor | availability_flag_low_variance |
| `board_vs_max` | stable_daily_factor | near_constant (nonzero_rate=0.0, std=0.0) |
| `board_vs_max_available` | stable_daily_factor | availability_flag_low_variance |
| `consecutive_high_premium_days_available` | stable_daily_factor | availability_flag_low_variance |
| `consecutive_ice_days_available` | stable_daily_factor | availability_flag_low_variance |
| `consecutive_shrink_days_available` | stable_daily_factor | availability_flag_low_variance |
| `corwin_schultz_spread` | core_price_volume | stable_tail_low_score |
| `emotion_climax_next_day_risk_available` | stable_daily_factor | availability_flag_low_variance |
| `emotion_ice_rebound_setup_available` | stable_daily_factor | availability_flag_low_variance |
| `emotion_phase_climax` | stable_daily_factor | stable_tail_low_score |
| `emotion_phase_climax_available` | stable_daily_factor | availability_flag_low_variance |
| `emotion_phase_code_available` | stable_daily_factor | availability_flag_low_variance |
| `emotion_phase_divergence_available` | stable_daily_factor | availability_flag_low_variance |
| `emotion_phase_ebbing` | stable_daily_factor | stable_tail_low_score |
| `emotion_phase_ebbing_available` | stable_daily_factor | availability_flag_low_variance |
| `emotion_phase_ice` | stable_daily_factor | stable_tail_low_score |
| `emotion_phase_ice_available` | stable_daily_factor | availability_flag_low_variance |
| `emotion_phase_trial_available` | stable_daily_factor | availability_flag_low_variance |
| `emotion_phase_upswing` | stable_daily_factor | stable_tail_low_score |
| `emotion_phase_upswing_available` | stable_daily_factor | availability_flag_low_variance |
| `failed_limit_up_loss_pressure_available` | stable_daily_factor | availability_flag_low_variance |
| `first_divergence_flag_available` | stable_daily_factor | availability_flag_low_variance |
| `first_negative_flag_available` | stable_daily_factor | availability_flag_low_variance |
| `is_first_board` | stable_daily_factor | near_constant (nonzero_rate=0.0, std=0.0) |
| `is_first_board_available` | stable_daily_factor | availability_flag_low_variance |
| `is_high_board` | stable_daily_factor | near_constant (nonzero_rate=0.0, std=0.0) |
| `is_high_board_available` | stable_daily_factor | availability_flag_low_variance |
| `is_second_board` | stable_daily_factor | near_constant (nonzero_rate=0.0, std=0.0) |
| `is_second_board_available` | stable_daily_factor | availability_flag_low_variance |
| `is_space_board` | stable_daily_factor | near_constant (nonzero_rate=0.0, std=0.0) |
| `is_space_board_available` | stable_daily_factor | availability_flag_low_variance |
| `limit_seal_quality_proxy` | core_price_volume | stable_tail_low_score |
| `limit_up_double_shot` | core_price_volume | stable_tail_low_score |
| `limit_up_like` | core_price_volume | stable_tail_low_score |
| `limit_up_streak` | core_price_volume | stable_tail_low_score |
| `limit_up_turnover` | core_price_volume | stable_tail_low_score |
| `market_active_amount_sum_available` | stable_daily_factor | availability_flag_low_variance |
| `market_active_turnover_mean_available` | stable_daily_factor | availability_flag_low_variance |
| `market_advance_decline_ratio_available` | stable_daily_factor | availability_flag_low_variance |
| `market_board_promotion_rate_1to2_available` | stable_daily_factor | availability_flag_low_variance |
| `market_board_promotion_rate_2to3_available` | stable_daily_factor | availability_flag_low_variance |
| `market_board_promotion_rate_available` | stable_daily_factor | availability_flag_low_variance |
| `market_board_promotion_rate_high_available` | stable_daily_factor | availability_flag_low_variance |
| `market_broken_board_count_available` | stable_daily_factor | availability_flag_low_variance |
| `market_broken_board_rate_1st_available` | stable_daily_factor | availability_flag_low_variance |
| `market_broken_board_rate_1to2_available` | stable_daily_factor | availability_flag_low_variance |
| `market_broken_board_rate_available` | stable_daily_factor | availability_flag_low_variance |
| `market_echelon_completeness_available` | stable_daily_factor | availability_flag_low_variance |
| `market_emotion_score_available` | stable_daily_factor | near_constant (nonzero_rate=0.9999999403953552, std=0.0) |
| `market_failed_limit_up_rate_available` | stable_daily_factor | availability_flag_low_variance |
| `market_limit_down_count_available` | stable_daily_factor | availability_flag_low_variance |
| `market_limit_up_count_available` | stable_daily_factor | availability_flag_low_variance |
| `market_max_board_height_available` | stable_daily_factor | availability_flag_low_variance |
| `market_new_high_20_count_available` | stable_daily_factor | availability_flag_low_variance |
| `market_new_low_20_count_available` | stable_daily_factor | availability_flag_low_variance |
| `market_seal_rate_available` | stable_daily_factor | availability_flag_low_variance |
| `one_word_board_proxy` | core_price_volume | stable_tail_low_score |
| `prev_board_count_available` | stable_daily_factor | availability_flag_low_variance |
| `prev_board_premium_available` | stable_daily_factor | availability_flag_low_variance |
| `prev_failed_limit_up_count_available` | stable_daily_factor | availability_flag_low_variance |
| `prev_failed_limit_up_loss_rate_available` | stable_daily_factor | availability_flag_low_variance |
| `prev_failed_limit_up_red_rate_available` | stable_daily_factor | availability_flag_low_variance |
| `prev_failed_limit_up_return_available` | stable_daily_factor | availability_flag_low_variance |
| `prev_limit_up_premium_available` | stable_daily_factor | near_constant (nonzero_rate=0.9999999403953552, std=0.0) |
| `same_height_failure_pressure_available` | stable_daily_factor | availability_flag_low_variance |
| `same_height_success_rate_1_available` | stable_daily_factor | availability_flag_low_variance |
| `same_height_success_rate_2_available` | stable_daily_factor | availability_flag_low_variance |
| `same_height_success_rate_3plus_available` | stable_daily_factor | availability_flag_low_variance |
| `t_shape_board_proxy` | core_price_volume | stable_tail_low_score |
| `tgb_board_height_vs_max` | tgb | stable_tail_low_score |
| `tgb_board_height_vs_max_available` | tgb | availability_flag_low_variance |
| `tgb_board_quality_trend` | tgb | stable_tail_low_score |
| `tgb_board_quality_trend_available` | tgb | availability_flag_low_variance |
| `tgb_eod_rush_risk_available` | tgb | availability_flag_low_variance |
| `tgb_leader_break_signal` | tgb | stable_tail_low_score |
| `tgb_leader_break_signal_available` | tgb | availability_flag_low_variance |
| `tgb_ma_alignment_score_available` | tgb | availability_flag_low_variance |
| `tgb_ma_divergence_5_available` | tgb | availability_flag_low_variance |
| `tgb_market_max_height_available` | tgb | availability_flag_low_variance |
| `tgb_mid_collapse_rate_available` | tgb | availability_flag_low_variance |
| `tgb_new_first_board_count_available` | tgb | availability_flag_low_variance |
| `tgb_nuclear_button_count_available` | tgb | availability_flag_low_variance |
| `tgb_pullback_health_available` | tgb | availability_flag_low_variance |
| `tgb_retreat_intensity_available` | tgb | availability_flag_low_variance |
| `tgb_volume_buildup_score_available` | tgb | availability_flag_low_variance |
| `tgb_zhaban_recovery_score_available` | tgb | availability_flag_low_variance |
| `volume_health_zone_available` | stable_daily_factor | availability_flag_low_variance |
| `volume_vs_prev_available` | stable_daily_factor | availability_flag_low_variance |

## 8. Next-Step Recommendations

### A. Already in input pool, not selected (review candidates)

These 92 features entered the training pipeline but were eliminated by stable_tail.
Most are `_available` flags (near-constant, no action needed) or board per-stock
features zeroed out by `exclude_event_limit_up` + `short_only` sample filter.

**Actionable subset** (non-available, non-near-constant):

- `corwin_schultz_spread` (core_price_volume)
- `emotion_phase_climax` (stable_daily_factor)
- `emotion_phase_ebbing` (stable_daily_factor)
- `emotion_phase_ice` (stable_daily_factor)
- `emotion_phase_upswing` (stable_daily_factor)
- `limit_seal_quality_proxy` (core_price_volume)
- `limit_up_double_shot` (core_price_volume)
- `limit_up_like` (core_price_volume)
- `limit_up_streak` (core_price_volume)
- `limit_up_turnover` (core_price_volume)
- `one_word_board_proxy` (core_price_volume)
- `t_shape_board_proxy` (core_price_volume)
- `tgb_board_height_vs_max` (tgb)
- `tgb_board_quality_trend` (tgb)
- `tgb_leader_break_signal` (tgb)

### B. Not in input pool — needs feature_set=research or config change

- **limit_pool**: 96 total (48 base + 48 _available)
- **research_daily_factor**: 94 total (47 base + 47 _available)
- **tushare**: 92 total (46 base + 46 _available)
- **intraday**: 58 total (29 base + 29 _available)
- **research_symbol_proxy**: 40 total (40 base + 0 _available)
- **research_cross_section**: 25 total (25 base + 0 _available)
- **cross_market**: 18 total (9 base + 9 _available)

### C. Priority ablation suggestion

Do NOT open all families at once. Pick 1-2 with best data readiness:

1. **research_daily_factor** (47 base, 100% coverage, zero external dependency).
   Several members already proved signal in prior research runs
   (`seal_rate_80_threshold`, `buy_sell_cycle_phase`, `cycle_day_count`, etc.).
   Ablation: run `feature_set=expanded` + manually add these 47 columns to stable set,
   compare HC metrics on `seen_research` split.

2. **tushare** — but NOT all 46 at once. Sub-source priority by coverage:
   - Tier 1 (high coverage): daily_basic(2), stk_limit(3), stk_auction(4), moneyflow(5) = 14 columns
   - Tier 2 (medium): cyq_perf(3), margin_detail(5), holdernumber(2) = 10 columns
   - Tier 3 (sparse): limit_list_d(6), top_list_inst(5), hk_hold(2), ths_hot(2) = 15 columns
   - Tier 4 (blocked): stk_mins_5(7) — 18% stock coverage, wait for pull completion
   Start ablation with Tier 1 only (14 columns).

### D. Explicitly not recommended yet

- **limit_pool**: 19% date coverage, 49/50 near-constant in prior research run
- **intraday (stk_mins_5)**: 18% stock coverage, need full pull
- **research_symbol_proxy / research_cross_section**: 0 selected in prior research runs

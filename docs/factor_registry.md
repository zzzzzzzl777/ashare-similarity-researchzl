# Factor Registry

> Updated: 2026-05-15
> Source experiment: controlled_family_ablation (seen_research only)
> diagnostic_monkey_patch: true
> lockbox_role: seen_research -- NOT final_unseen, NOT passed, NOT frozen

## Registry Entries

### research_daily_factor

| Field | Value |
|-------|-------|
| status | trained_seen_not_promote |
| family | GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES |
| input_count | 94 (47 base + 47 _available) |
| selected_count | 32 |
| ablation_variant | expanded_plus_research_daily |
| run_id | gpu_probe_20260503T113537Z_058b885e |
| baseline_run_id | gpu_probe_20260503T113328Z_1b272829 |

**Ablation Metrics vs Baseline**

| Metric | Baseline | With research_daily | Delta |
|--------|----------|---------------------|-------|
| HC accuracy | 0.754042 | 0.742993 | -1.10pp |
| Wilson lower 95 | 0.747352 | 0.736606 | -1.07pp |
| HC count | 16206 | 18268 | +2062 |
| Coverage | 0.135050 | 0.152233 | +1.72pp |
| Brier | 0.225416 | 0.226696 | +0.001280 (worse) |

**Verdict**: All accuracy/calibration metrics degraded. Coverage gain (+1.72pp) does not compensate. Do NOT promote to expanded.

---

### tushare_tier1

| Field | Value |
|-------|-------|
| status | promote_candidate |
| family | Tushare Tier 1 (moneyflow + daily_basic + stk_limit) |
| input_count | 20 (10 base + 10 _available) |
| selected_count | 8 |
| ablation_variant | tushare_tier1_available |
| run_id | gpu_probe_20260503T115829Z_d3222871 |
| baseline_run_id | gpu_probe_20260503T113328Z_1b272829 |

**Ablation Metrics vs Baseline**

| Metric | Baseline | With tushare_tier1 | Delta |
|--------|----------|--------------------|-------|
| HC accuracy | 0.754042 | 0.770902 | +1.69pp |
| Wilson lower 95 | 0.747352 | 0.763934 | +1.66pp |
| HC count | 16206 | 14269 | -1937 |
| Coverage | 0.135050 | 0.118908 | -1.61pp |
| Brier | 0.225416 | 0.224508 | -0.000908 (improved) |

**Verdict**: Accuracy, Wilson, and Brier all improved. Coverage slightly lower (-1.61pp) due to tighter confidence threshold. Promote candidate -- requires final_unseen validation before production.

#### 8 Selected Tushare Features

| # | Feature | API Source |
|---|---------|-----------|
| 1 | tushare_net_mf_amount | moneyflow |
| 2 | tushare_lg_buy_sell_ratio | moneyflow |
| 3 | tushare_elg_buy_sell_ratio | moneyflow |
| 4 | tushare_volume_ratio | daily_basic |
| 5 | tushare_free_share | daily_basic |
| 6 | tushare_up_limit_distance | stk_limit |
| 7 | tushare_down_limit_distance | stk_limit |
| 8 | tushare_limit_range | stk_limit |

#### 2 Not Selected (base columns)

| Feature | API Source | Reason |
|---------|-----------|--------|
| tushare_mf_strength | moneyflow | Not selected by stable_tail |
| tushare_sm_sell_pressure | moneyflow | Not selected by stable_tail |

#### 10 _available Flags: All Not Selected

Expected -- high Tushare coverage (804 cached days) means _available flags have near-zero variance, providing no discriminative signal.

---

## Next-Round Factor Search Directions

| # | Direction | Rationale |
|---|-----------|-----------|
| 1 | moneyflow derivatives | net_mf_amount, lg/elg ratios all selected -- explore rolling z-scores, rank-within-sector, momentum of flows |
| 2 | free_share capacity constraints | free_share selected -- combine with volume/turnover for liquidity-adjusted signals |
| 3 | volume_ratio derivatives | volume_ratio selected -- explore multi-day volume momentum, volume surprise vs moving average |
| 4 | stk_limit proximity derivatives | all 3 limit features selected -- explore distance-to-limit acceleration, limit hit frequency |
| 5 | stk_auction (Tier 1b candidate) | stk_auction_o (804 parquets) and stk_auction_c (804 parquets) cached but excluded this round -- next candidate for ablation |

---

## Diagnostic Caveats

- All runs used `diagnostic_monkey_patch=true` -- feature lists were injected via runtime monkey-patch of `_feature_names_for_config`, not via config field
- `lockbox_role=seen_research` -- these results are exploratory, NOT production-grade
- No run claims `passed` or `final_unseen`
- `frozen_forward_config.json` was NOT modified
- Feature selection method: `stable_tail` with `max_selected_features=260`, `selector_coverage_weight=0.02`
- tushare_tier1 variant used `feature_set="research"` to trigger tushare attachment; baseline and research_daily used `feature_set="expanded"`
- Coverage drop means the confidence selector selected a narrower high-confidence subset; it does not mean Tushare data coverage is lower

---

## Training Usage Ledger (Updated 2026-05-05)

> Full detail: [factor_registry_training_usage_update_20260505.md](factor_registry_training_usage_update_20260505.md)
> Total runs audited: 16 (9 Q1 factor-split + 4 April holdout + 780-pool + G-rerun + tier1-ablation)
> None of these runs are final_unseen or passed.

| ID | Column | Used | Selected | Not-Sel | Verdict | Formula Match |
|----|--------|:----:|:--------:|:-------:|---------|:-------------:|
| C009 | tushare_main_force_divergence | 8 | 7 | 1 | selected_seen_research_positive_april_not_confirmed | YES |
| C004 | tushare_ff_adjusted_flow | 8 | 6 | 2 | selected_seen_research_positive_april_not_confirmed | YES |
| C011 | tushare_auction_open_vwap_ratio | 6 | 5 | 1 | selected_seen_research_positive_april_not_confirmed | YES |
| C001 | tushare_mf_flow_intensity | 1 | 0 | 1 | implementation_mismatch_alternate_not_selected | **NO** |
| C010 | tushare_float_relative_impact | 1 | 1 | 0 | implementation_mismatch_alternate_selected_780pool | **NO** |
| C005 | (not implemented) | 0 | 0 | 0 | blocked_until_formula_corrected | N/A |
| C006 | (not implemented) | 0 | 0 | 0 | blocked_until_formula_corrected | N/A |
| C008 | (not implemented) | 0 | 0 | 0 | blocked_until_formula_corrected | N/A |

### Formula Mismatch Notes

- **C001**: Code uses `net_mf_amount / total_buy_amount` (moneyflow buy-side). Registry defines `net_mf_amount / daily_bar_amount`. Alternate tested, not selected. Original never implemented.
- **C010**: Code uses `vol_ratio * total_buy_vol / free_share` (moneyflow buy-side vol). Registry defines `vol_ratio * daily_volume / free_share`. Alternate tested and SELECTED in 780-pool, but this is not the original definition.

### Best Metrics (seen_research, NOT final)

| Factor Combo | Q1 Best Wilson | April Wilson | Gap to 75% |
|-------------|:-------------:|:-----------:|:----------:|
| C009+C004 (Run G) | 86.27% @ T>=0.78 | 72.14% | -2.86pp |
| C009 only (Run C) | 84.64% @ T>=0.75 | 71.30% | -3.70pp |
| C009+C011 (B1) | 84.59% @ T>=0.75 | 67.95% | -7.05pp |
| C004 only (Run F) | 82.10% @ T>=0.75 | 70.06% | -4.94pp |

---

## Next Search Candidates 2026-05-03

> Three-path search: taoguba short-term context, GitHub/papers, social media/live trading rules
> Full detail: [next_factor_candidates_20260503.md](next_factor_candidates_20260503.md)
> Total: 42 candidates (12 P0, 19 P1, 7 P2, 4 blocked)
> Constraint: no training, no gpu_probe.py changes, no frozen_forward_config changes
> Existing duplicates checked: close_position, volume_z_20, overnight_vs_intraday, corwin_schultz_spread, turnover_chg_5, volume_price_divergence_5 -- all skipped

### P0 Candidates (12)

| ID | Name | Family | Formula | Data Source | Not Redundant Because |
|----|------|--------|---------|-------------|----------------------|
| C001 | mf_flow_intensity | moneyflow | registry: net_mf_amount / daily_amount; tested alternate used total_buy_amount | moneyflow + daily | Original formula not yet implemented; alternate was not selected |
| C002 | mf_momentum_5d | moneyflow | (net_mf - mean_5d) / std_5d | moneyflow | Z-score captures acceleration; raw net_mf is level only |
| C003 | mf_persistence_5d | moneyflow | sum(net_mf > 0, 5) / 5 | moneyflow | Binary streak; removes magnitude noise from net_mf |
| C004 | ff_adjusted_flow | moneyflow | net_mf / (free_share * close) | moneyflow + daily_basic | Interaction of 2 validated features; capacity-normalized flow |
| C005 | limit_space_compression | stk_limit | (close - down_limit) / (up_limit - down_limit) | stk_limit + daily close | Corrected formula; old up_dist/limit_range version is superseded_do_not_use |
| C006 | limit_approach_velocity | stk_limit | actual_up_gap[T-1] - actual_up_gap[T], actual_up_gap=(up_limit-close)/close | stk_limit + daily close | Corrected formula; depends on raw up_limit passthrough |
| C007 | limit_range_utilization | stk_limit | (high-low) / (limit_range * close) | stk_limit + OHLCV | range_pct normalizes by price, this normalizes by constraint |
| C008 | seal_strength_proxy | interaction | elg_ratio * ((close - down_limit) / (up_limit - down_limit)) | moneyflow + stk_limit + daily close | Corrected formula; old version was a constant rescale |
| C009 | main_force_divergence | moneyflow | abs(lg_ratio - elg_ratio) | moneyflow | Institutional disagreement dimension; neither ratio alone captures |
| C010 | float_relative_impact | capacity | registry: vol_ratio * daily_volume / free_share; tested alternate used total_buy_vol | daily_basic + OHLCV | Original formula not yet implemented; alternate selected once but not validated |
| C011 | auction_open_vwap_ratio | stk_auction | already computed (Tier1b) | stk_auction_o | Already coded, not promoted; VWAP != open price |
| C012 | auction_gap_normalized | stk_limit | (open - prev_close) / (limit_range * prev_close) | stk_limit + OHLCV | gap_pct exists but normalizes by price, not limit range |

### P1 Candidates (19)

| ID | Name | Family | Key Formula |
|----|------|--------|-------------|
| C013 | smart_money_divergence | moneyflow | rank(elg_ratio) - rank(sm_ratio) |
| C014 | mf_volume_decoupling | moneyflow | rank(net_mf/amount) - rank(vol_ratio) |
| C015 | mf_concentration | moneyflow | (elg_net + lg_net) / abs(total_net) |
| C016 | elg_momentum_divergence | moneyflow | rank(mean(elg_ratio,5)) - rank(ret_5d) |
| C017 | volume_confirmation_score | volume | body_direction * volume_ratio |
| C018 | volume_divergence_doji | volume | vol_ratio * (1 - abs(body)/range) |
| C019 | volume_asymmetry_10d | volume | (up_vol - dn_vol) / total_vol, 10d |
| C020 | vp_correlation_10d | volume | corr(close, volume, 10) |
| C021 | cumulative_turnover_5d | capacity | sum(volume, 5) / free_share |
| C022 | float_cap_tier | capacity | log10(free_share * close) |
| C023 | amihud_illiquidity_20d | capacity | mean(abs(ret) / dollar_vol, 20) |
| C024 | limit_distance_compression_5d | stk_limit | up_dist[T] / up_dist[T-5] |
| C025 | upper_shadow_limit_ratio | stk_limit | (high - close) / (up_limit - close) |
| C026 | updown_asymmetry | stk_limit | up_dist / down_dist |
| C027 | capital_efficiency | moneyflow | (close - open) / abs(net_mf) |
| C028 | flow_density_in_limit_space | interaction | net_mf / (up_dist * close) |
| C029 | weak_to_strong_signal | interaction | ((close-open)/(limit_range*close)) * vol_ratio |
| C030 | auction_open_vol_normalized | stk_auction | auction_open_vol / mean(volume, 5) |
| C031 | auction_vol_imbalance | stk_auction | log(auction_open_vol / auction_close_vol) |

### P2 Candidates (7)

| ID | Name | Reason for P2 |
|----|------|---------------|
| C032 | volume_surge_with_support | 3-way composite, may overlap existing interactions |
| C033 | mf_vs_price_imbalance | Scaling factor arbitrary, needs tuning |
| C034 | amplitude_x_mf_direction | Close to existing range_x interactions |
| C035 | relative_volume_strength | Close to volume_z * sign(ret) |
| C036 | small_cap_flow_saturation | Unstable 3-way multiplicative |
| C037 | consecutive_limit_momentum | Very sparse (2+ limit-up days only) |
| C038 | close_position_x_volume_rank | Close to existing ret1_x_volume_z5 |

### Blocked Candidates (4)

| ID | Name | Blocked Reason |
|----|------|----------------|
| C039 | seal_order_volume | Requires Level-2 order book |
| C040 | intraday_break_count | Requires tick data for limit-break count |
| C041 | auction_micro_bidding | Requires pre-market Level-2 |
| C042 | hot_money_seat_concentration | Dragon-tiger ~1-2% daily coverage, T+1 delay |

### Engineering Priority: Top 8

> Engineering review: [top8_factor_engineering_review_20260503.md](top8_factor_engineering_review_20260503.md)

| Rank | ID | Name | Engineering Status | Group | Ready? |
|------|-----|------|--------------------|-------|--------|
| 1 | C004 | ff_adjusted_flow | verified_engineerable | C (post-merge, daily close) | YES |
| 2 | C001 | mf_flow_intensity | implementation_mismatch | C (post-merge, daily amount) | NO -- alternate tested, original not implemented |
| 3 | C005 | limit_space_compression | needs_formula_correction | C+ (daily close + raw up/down_limit) | NO -- implied_close != actual close |
| 4 | C006 | limit_approach_velocity | needs_formula_correction | C+ (daily close + raw up_limit, .diff()) | NO -- depends on C005 |
| 5 | C009 | main_force_divergence | verified_engineerable | A (pure tushare, 1 line) | YES |
| 6 | C008 | seal_strength_proxy | needs_formula_correction | C+ (depends on C005 correction) | NO -- depends on C005 |
| 7 | C011 | auction_open_vwap_ratio | existing_engineered | D (already exists) | YES |
| 8 | C010 | float_relative_impact | implementation_mismatch | C (post-merge, daily volume) | NO -- alternate selected once, original not implemented |
|  |  |  | **3/8 ready/reference, 3/8 need formula correction, 2/8 implementation mismatch** |  |  |

---

## Next Factor Search 2026-05-05

> Role: factor library only. No training, no probe run, no model changes.
> New batch: 20 candidate ideas (8 P0, 8 P1, 4 P2), IDs C043-C062.
> Full detail: [next_factor_candidates_20260505.md](next_factor_candidates_20260505.md)
> Data-first filter: only candidates using already cached data or existing OHLCV/Tushare feature frames.

### P0 Candidates (8)

| ID | Name | Family | Formula Sketch | Data Source | Why Next |
|----|------|--------|----------------|-------------|----------|
| C043 | auction_price_volume_confirm | auction | (auction_open_vwap_ratio - 1) * log1p(auction_open_vol / avg_vol_5) | stk_auction_o + daily volume | Opening auction price needs volume confirmation |
| C044 | auction_close_pressure | auction | (auction_close_vwap_ratio - 1) * log1p(auction_close_vol / avg_vol_5) | stk_auction_c + daily volume | Captures 14:57-15:00 close auction pressure |
| C045 | auction_vwap_shift | auction | auction_close_vwap_ratio - auction_open_vwap_ratio | stk_auction_o/c | Intraday sentiment shift from open auction to close auction |
| C046 | seal_stability_score | limit_list | seal_ratio / (1 + open_times) * exp(-first_time_minutes / 240) | limit_list_d | Early seal with few opens is a classic short-term strength proxy |
| C047 | first_seal_turnover_urgency | limit_list | exp(-first_time_minutes / 240) * limit_turnover | limit_list_d | Early board plus active turnover separates strong/weak seals |
| C048 | vwap_reclaim_strength | intraday_5m | close_vs_vwap * up_volume_ratio | stk_mins_5 | Price above VWAP with up-volume participation |
| C049 | tail_push_strength | intraday_5m | last_30min_return * up_volume_ratio / (1 + intraday_volatility) | stk_mins_5 | Tail-session push after full-day trading |
| C050 | hot_rank_momentum | sentiment | -delta(ths_hot_rank, 1-3d) * log1p(ths_hot_value) | ths_hot | App heat acceleration, not just heat level |

### P1 Candidates (8)

| ID | Name | Family | Formula Sketch | Data Source | Reason |
|----|------|--------|----------------|-------------|--------|
| C051 | hot_price_divergence | sentiment | hot_rank_momentum - rank(ret_1d) | ths_hot + OHLCV | Hot attention before price catches up |
| C052 | northbound_market_tailwind | market_flow | zscore(north_money, 20) | moneyflow_hsgt | Broad liquidity regime, broadcast as market feature |
| C053 | industry_flow_alignment | industry_flow | rank(stock_net_mf) - rank(industry_net_flow) | moneyflow + moneyflow_ind_ths/dc | Stock flow relative to its industry crowding |
| C054 | northbound_stock_alignment | hk_hold | hk_ratio_delta_1d * sign(ret_1d) | hk_hold + OHLCV | Foreign holding change aligned with price trend |
| C055 | margin_chase_pressure | margin | rzmre_ratio * max(ret_1d, 0) | margin_detail + OHLCV | Levered buyers chasing winners |
| C056 | cyq_breakout_pressure | cyq | cost_position * cost_concentration | cyq_perf | Price relative to chip cost distribution |
| C057 | winner_rate_delta_5d | cyq | winner_rate - winner_rate_lag_5 | cyq_perf | Rapid profit-holder expansion or contraction |
| C058 | lhb_institutional_confirmation | lhb | inst_net_buy / max(abs(lhb_net_buy), eps) | top_list + top_inst | Sparse but meaningful when stock enters LHB |

### P2 Candidates (4)

| ID | Name | Reason for P2 |
|----|------|---------------|
| C059 | limit_theme_breadth | Needs reliable tag/lu_desc parsing and same-theme grouping |
| C060 | first15_tail_reversal | Needs careful direction sign; may overlap last_30min_return |
| C061 | hsgt_top10_stock_pressure | Sparse stock-level northbound top10 appearance |
| C062 | lhb_afterglow_decay | Very sparse and may become event-regime specific |

---

## Batch: candidates_20260506_minute_registration

> Purpose: Register existing 5-min bar feature columns with working code but no prior factor_id.
> Data source: stk_mins_5 (3195 parquets, 2023-01-03 to 2026-04-30)
> All use T-day 15:00 full bars → T+1 prediction. No leakage.

### Trainable This Round (5)

| ID | Name | Column | Family | Status | Stats |
|----|------|--------|--------|--------|-------|
| C133 | last_30min_return | tushare_last_30min_return | intraday_momentum | existing_engineered | p1=-0.015, p50=0, p99=0.018 |
| C134 | first_15min_volume_concentration | tushare_first_15min_volume_ratio | intraday_volume_structure | existing_engineered | p1=0.052, p50=0.167, p99=0.507 |
| C136 | intraday_volatility | tushare_intraday_volatility | intraday_risk | existing_engineered | p1=0.001, p50=0.003, p99=0.011 |
| C137 | up_volume_ratio | tushare_up_volume_ratio | intraday_volume_structure | existing_engineered | p1=0.119, p50=0.402, p99=0.697 |
| C138 | high_time_position | tushare_high_time_pct | intraday_momentum | existing_engineered | p1=0, p50=0.083, p99=1.0 |

### Blocked This Round (1)

| ID | Name | Column | Status | Blocker |
|----|------|--------|--------|---------|
| C135 | vwap_deviation | tushare_vwap_deviation | blocked_until_outlier_guard | max=109.6 from vol/amount unit mismatch (0.43% rows) |

### Removed / Not Registered (1)

| Column | Status | Reason |
|--------|--------|--------|
| tushare_close_vs_vwap | duplicate_of_C135 | Formula `C/max(V,0.01)-1` ≡ `(C-V)/max(|V|,0.01)` when V>0. No factor_id assigned. |

---

## Batch: candidates_20260506_raw_review

> Purpose: Promote high-quality raw pool candidates with clear computable definitions.
> Source: `raw_to_registry_review_queue_20260506.md` (50 candidates reviewed, 14 promoted)
> All: `training_status="not_trained"`, `lockbox_role="research_candidate"`

### Promoted (14): C139-C152

| ID | Name | Family | Priority | Data Need | Computable Definition |
|----|------|--------|----------|-----------|----------------------|
| C139 | real_limit_up_premium_gap | limit_up_premium | P0 | limit_pool + daily | mean(return, real_pool) - mean(return, proxy_pool) |
| C140 | zbgc_sector_pressure | board_quality | P0 | limit_pool + sector | broken_board_count / limit_attempt per sector |
| C141 | prev_top20_chase_real | market_breadth | P0 | daily_ohlcv | mean(return_T, top20_gainers_T-1) |
| C142 | theme_limit_density | sector_momentum | P1 | limit_pool + sector | limit_count_in_theme / theme_member_count |
| C143 | is_volume_sufficient | volume_quality | P1 | daily_ohlcv | turnover_T / turnover_T-1 >= 0.7 |
| C144 | leader_pull_effect | sector_momentum | P1 | daily + limit + sector | mean(sector_peer_return) on limit-up day |
| C145 | theme_height_suppression | sector_cycle | P1 | daily + limit + sector | max(board_count, same_theme, 1Y) |
| C146 | support_one_word_count | board_structure | P1 | daily + sector | count(open==close==high_limit, same_sector) |
| C147 | eruption_strength | market_breadth | P2 | daily + limit | z(limit_ups) + z(one_word) + z(unbuyable_rate) |
| C148 | is_ground_sky | extreme_pattern | P2 | daily + limit | (low==low_limit) AND (close==high_limit) |
| C149 | seal_trend | board_quality | P2 | limit_pool | seal_money_T / seal_money_T-1 - 1 |
| C150 | old_leader_decay | market_cycle | P2 | daily + limit | top_board_stock broken OR volume -30% |
| C151 | anti_drop_strength | relative_strength | P2 | daily_ohlcv | stock_return / index_return on down days |
| C152 | multi_wave_count | technical_pattern | P2 | daily_ohlcv | count(rising_segment_starts, 60d) |

### Review Statistics

| Outcome | Count |
|---------|-------|
| Promoted | 14 |
| Rejected (duplicate/non-computable) | 20 |
| Deferred (unclear formula/needs data) | 16 |

Full details: `docs/raw_review_to_registry_20260506.md`

---

## Batch: candidates_20260506_raw_review_500

> Purpose: Third-pass strict review of 429 raw pool candidates (from 500-queue).
> Pipeline: 429 input → 289 second-pass → 39 third-pass → 21 manual final
> Source: `docs/raw_review_500_third_pass_20260506.md`
> All: `training_status="not_trained"`, `lockbox_role="research_candidate"`

### Promoted (21): C153-C173

| ID | Name | Family | Priority | Data Need | Computable Definition |
|----|------|--------|----------|-----------|----------------------|
| C153 | nuclear_ratio | board_structure | P1 | limit_pool | intersection(pool_T, pool_T-1) / count(pool_T-1) |
| C154 | price_vs_cost | price_structure | P1 | daily_ohlcv | (close - VWAP_Nd) / VWAP_Nd |
| C155 | cap_ratio | sector_structure | P2 | daily_ohlcv + sector | stock_float_mv / sector_leader_float_mv |
| C156 | abnormal_3d_deviation | momentum | P1 | daily_ohlcv | sum(pct_change, 3d) - sum(index_pct_change, 3d) |
| C157 | VOL_GAIN | volume_structure | P1 | daily_ohlcv | mean(turnover, up-days) / mean(turnover, down-days) |
| C158 | INV_t | volume_structure | P1 | daily_ohlcv | -sum(sign(ret)*vol, 20d) / sum(vol, 20d) |
| C159 | ASR | price_structure | P1 | daily_ohlcv | (P90 - P10) / close, 60d window |
| C160 | chip_weight | price_structure | P2 | daily_ohlcv | turnover_i * prod(1 - turnover_j, j>i) |
| C161 | ILLIQ_classic | liquidity | P0 | daily_ohlcv | mean(\|ret\| / volume, 20d) (Amihud) |
| C162 | ATO | volume_structure | P1 | daily_ohlcv | (mean(turnover,20d) - mean(turnover,120d)) / std(turnover,120d) |
| C163 | TAM | momentum | P2 | daily_ohlcv | MOM_12_1 - beta * mean_turnover_12m |
| C164 | new_leader_emerge | market_cycle | P1 | limit_pool | board_height==2 AND seal_time_rank==1 |
| C165 | need_second_seal | board_quality | P1 | daily_ohlcv + limit_pool | (high - low) / prev_close for limit stocks |
| C166 | late_seal_ratio | board_structure | P1 | limit_pool | count(seal_time > 14:00) / total_limit_up_count |
| C167 | early_seal_ratio | board_structure | P1 | limit_pool | count(seal_time < 10:30) / total_limit_up_count |
| C168 | vol_premium | volume_structure | P1 | daily_ohlcv + sector | stock_vol / mean(vol, sector) - 1 |
| C169 | max_theme_weight | sector_structure | P2 | sector_theme | max(weight_i) across theme memberships |
| C170 | hhi_theme_concentration | sector_structure | P2 | sector_theme | sum(weight_i^2) HHI of theme exposure |
| C171 | new_high_strength | board_structure | P2 | limit_pool | strength from stock_zt_pool_strong_em API |
| C172 | recent_limit_frequency | board_structure | P2 | limit_pool | frequency from stock_zt_pool_strong_em API |
| C173 | true_limit_up_ratio | market_breadth | P1 | limit_pool | ratio from stock_market_activity_legu API |

### Caution Notes

| ID | Issue | Tag |
|----|-------|-----|
| C155 | sector_leader definition not fixed (highest board? highest return?) | needs_formula_lock |
| C160 | Rolling window length and turnover unit (pct or raw) not specified | needs_formula_lock |
| C163 | beta estimation method undefined (cross-sectional regression? fixed?) | needs_formula_lock |
| C171 | Must verify stock_zt_pool_strong_em historical availability and asof timing | needs_api_verification |
| C172 | Must verify stock_zt_pool_strong_em historical availability and asof timing | needs_api_verification |

### Review Statistics

| Outcome | Count |
|---------|-------|
| Final Promote | 21 |
| Reject (all passes) | 253 |
| Defer (all passes) | 155 |
| Promote rate | 4.9% (21/429) |

Full details: `docs/raw_review_500_third_pass_20260506.md`


---

## Batch: candidates_20260512_minute_reaudit

> Purpose: 15 strict-reaudit P0/P1 minute-bar factors (5min bars only)
> Pipeline: 553 minute/tick/L2 → 209 engineerable → strict reclassification → top 15
> Source: `docs/minute_factor_reaudit_20260511.md`
> All: `training_status="not_trained"`, `lockbox_role="research_candidate"`, `engineering_status="candidate_ready"`
> Data: `minute_bar_5min` (stk_mins_5, 3198 parquets available)

### Key Decisions

- **Only 15 of 132 ready candidates registered** — bulk registration deferred, these are highest-confidence P0/P1
- **VS_ratio (RAW002085) NOT registered** — requires 1min data which does not exist in system
- **P2 candidates (CGO_A, chip_pressure, WAC_t, EMA_Cost) NOT registered** — complex multi-day VWAP, deferred
- **132 ready_to_register_minute_bar remain as reserve pool** for future batches

### Promoted (15): C174-C188

| ID | Name | Priority | Formula | Duplicate Check |
|----|------|----------|---------|-----------------|
| C174 | intraday_vol_herfindahl | P0 | sum(V_k/V_total)^2 | HHI != Gini (minute_volume_gini) |
| C175 | intraday_profit_ratio | P0 | sum(Vol*I(Close>VWAP))/sum(Vol) | No existing profitable-fraction feature |
| C176 | vwap_deviation_normalized | P0 | (Close-VWAP)/std(prices) | Fixes blocked C135 outlier via std-normalization |
| C177 | intraday_volume_clustering | P0 | Max(V)/Mean(V) | Peak/avg != Gini equality measure |
| C178 | intraday_ofi_proxy | P0 | sum(sign(r)*V)/sum(V) | No OFI feature exists; no L2 needed |
| C179 | close_impact_3min | P1 | (Close-Close_14:55)/Close_14:55 | Price impact != volume-based late_surge_ratio |
| C180 | eod_volume_concentration | P1 | V_last_bar/V_total | last/TOTAL != last/MEAN (closing_auction_vol_ratio) |
| C181 | trapped_volume | P1 | sum(Vol*I(VWAP>Close)*decay) | CYQ underwater concept, novel |
| C182 | tail_volatility_ratio | P1 | std(r_last6)/std(r_all) | Relative tail vol, not absolute realized_vol |
| C183 | intraday_price_reversal | P1 | |r_first_half|/sum|r| | Path fraction != absolute morning_return |
| C184 | bar_obi_proxy | P1 | sum(((c-l)/(h-l)-0.5)*V)/sum(V) | Vol-weighted across bars != single EOD close_position |
| C185 | intraday_consolidation_duration | P1 | count(near_vwap_bars)/total | Near-VWAP time != price_efficiency |
| C186 | intraday_breakout_bar_ratio | P1 | count(price+vol breakout)/total | Joint condition, novel |
| C187 | intraday_volume_shrink_ratio | P1 | count(V<0.6*avg)/total | Volume drought frequency, novel |
| C188 | prev_30min_volume_ratio | P1 | V_14:00-14:30/V_total | 14:00-14:30 != 14:30-15:00 (last_30min) |

### Code-Verified Duplicate Exclusions

These were in the original Top 20 but confirmed as exact duplicates via source code reading:

| Excluded | Existing Column | Verification |
|----------|-----------------|--------------|
| AC1 (RAW002091) | minute_return_autocorr_intraday | Identical lag-1 autocorrelation |
| RSK (RAW002234) | minute_realized_skew | Identical sum(r³)/RV^(3/2) |
| CloseSurge (RAW002106) | minute_last_30min_volume_ratio | Identical last-30min/total |
| recovery_ratio (RAW001484) | minute_intraday_close_position | Identical (close-low)/(high-low) |

---

## Batch: candidates_20260515_data_unlocked

> Purpose: Register data-unlocked factor candidates after the Tushare proxy/API capability audit.
> Scope: factor-library only; no training, no gpu_probe, no model-code change.
> All: `training_status="not_trained"`, `lockbox_role="research_candidate"`.
> Detailed report: `docs/data_unlocked_factor_mapping_20260515.md`

### Promoted (34): C189-C222

| ID | Name | Priority | Family | Source/Data | Definition | Status |
|----|------|----------|--------|-------------|------------|--------|
| C189 | rv_ratio_1min_vs_5min | P0 | intraday_microstructure | stk_mins / 1min and 5min minute bars | realized_volatility(1min returns) / (realized_volatility(5min returns) + eps) | data_unlocked_needs_1min_backfill |
| C190 | first_5min_strength_1min | P0 | intraday_microstructure | stk_mins / 1min minute bars | (close_09:35 - open_09:30) / open_09:30 | data_unlocked_needs_1min_backfill |
| C191 | attack_volume_real_1min | P0 | intraday_microstructure | stk_mins / 1min minute bars | sum(vol_i * I(ret_i > 0 and close_i near rolling high), early session) / sum(vol_i, early session) | data_unlocked_needs_1min_backfill |
| C192 | dynamic_volume_acceleration_1min | P1 | intraday_microstructure | stk_mins / 1min bars plus same-clock historical baseline | slope(log(volume_1min + 1)) over recent N bars normalized by same-clock historical median | data_unlocked_needs_1min_backfill |
| C193 | reseal_speed_1min | P1 | limit_pool_intraday | stk_mins + stk_limit/limit_list_d / 1min bars plus daily limit price | Minutes between first up-limit touch and successful reseal; missing if no touch. | data_unlocked_needs_1min_backfill |
| C194 | stk_factor_pro_technical_bank | P0 | technical_indicator_bank | stk_factor_pro / vendor-computed technical indicator columns | Curated feature bank from stk_factor_pro technical indicators after removing raw OHLCV/adj duplicates and choosing one adjustment family. | source_verified_needs_full_backfill_and_column_catalog |
| C195 | technical_momentum_confirmation | P1 | technical_indicator_bank | stk_factor_pro / MACD/KDJ/RSI style fields after catalog | zscore(MACD histogram/diff) + zscore(KDJ J-D) + zscore(RSI short-long) | needs_stk_factor_pro_column_catalog |
| C196 | technical_squeeze_breakout | P1 | technical_indicator_bank | stk_factor_pro / BOLL/ATR style fields after catalog | BOLL bandwidth compression plus close position over middle/upper band, normalized by ATR. | needs_stk_factor_pro_column_catalog |
| C197 | volume_moneyflow_technical_divergence | P1 | technical_moneyflow_cross | stk_factor_pro + moneyflow / technical volume indicator columns plus moneyflow | standardized technical volume pressure minus standardized net moneyflow amount rate | needs_stk_factor_pro_column_catalog |
| C198 | block_trade_discount_intensity | P0 | block_trade | block_trade + daily / block trade price/amount plus daily close | amount_weighted_mean(block_trade.price / daily.close - 1) | source_verified_cache_empty_needs_backfill |
| C199 | block_trade_amount_ratio | P0 | block_trade | block_trade + daily / block trade amount plus daily amount | sum(block_trade.amount) / (daily.amount + eps) | source_verified_cache_empty_needs_backfill |
| C200 | block_trade_buyer_concentration | P1 | block_trade | block_trade / block trade buyer/amount fields | HHI of buyer-side amount shares by buyer name for each stock/date. | source_verified_cache_empty_needs_backfill |
| C201 | block_trade_institutional_net_bias | P1 | block_trade | block_trade / block trade buyer/seller text plus amount | (institution_like_buy_amount - institution_like_sell_amount) / total_block_amount | candidate_needs_text_rule_lock |
| C202 | unlock_pressure_30d | P0 | share_float_unlock | share_float + daily_basic / restricted share unlock schedule plus share base | sum(float_share with float_date in (T, T+30]) / current free_float_or_total_share | source_verified_needs_backfill |
| C203 | unlock_holder_concentration | P1 | share_float_unlock | share_float / restricted share unlock holder/float_share fields | HHI of upcoming 30-day unlock float_share by holder_name. | source_verified_needs_backfill |
| C204 | pledge_pressure_delta | P1 | pledge_risk | pledge_stat / pledge ratio/stat fields | pledge_ratio_T - previous_report_pledge_ratio | source_verified_needs_backfill_and_asof_lock |
| C205 | holdertrade_net_buy_ratio | P0 | holder_trade | stk_holdertrade + daily_basic / holder increase/decrease records plus share base | signed_sum(change_vol over last 20 trading days) / total_share_or_float_share | source_verified_cache_empty_needs_backfill |
| C206 | institution_research_heat_20d | P0 | institution_survey | stk_surv / institution survey/event records | rolling 20-day sum(log1p(fund_visitors)) or event_count. | source_verified_cache_exists_needs_coverage_check |
| C207 | research_org_diversity_20d | P1 | institution_survey | stk_surv / institution survey organization fields | nunique(rece_org or org_type) in trailing 20 calendar/trading days. | source_verified_cache_exists_needs_coverage_check |
| C208 | forecast_profit_revision_intensity | P0 | forecast_event | forecast_vip or forecast / profit forecast announcement fields | current midpoint(p_change_min,p_change_max) minus previous forecast midpoint for the same stock. | source_verified_partial_cache_needs_range_backfill |
| C209 | express_growth_acceleration | P1 | financial_event | express + sector membership / earnings express fields plus sector mapping | net_profit_yoy minus sector median net_profit_yoy, optionally first difference vs previous report. | source_verified_needs_backfill_and_asof_lock |
| C210 | hsgt_top10_net_buy_intensity | P0 | northbound_flow | hsgt_top10 + daily / northbound top10 stock flow plus daily amount | hsgt_top10.net_amount / (daily.amount + eps), sparse with availability flag. | source_verified_cache_exists_needs_coverage_check |
| C211 | ccass_hold_change_5d | P0 | foreign_holding | ccass_hold + daily_basic / CCASS shareholding and share base | (ccass_hold_share_T - ccass_hold_share_T-5) / total_share_or_float_share | source_verified_cache_exists_needs_coverage_check |
| C212 | hk_hold_ratio_change_5d | P1 | foreign_holding | hk_hold / HK hold ratio/share fields | hk_hold_ratio_T - hk_hold_ratio_T-5. | source_verified_cache_exists_needs_coverage_check |
| C213 | northbound_market_flow_regime | P1 | market_regime | moneyflow_hsgt / northbound/southbound aggregate flow | rolling zscore(north_money) plus 3-day acceleration, broadcast to all stocks. | source_verified_cache_exists_needs_coverage_check |
| C214 | industry_moneyflow_strength | P0 | industry_flow | moneyflow_ind_dc or moneyflow_ind_ths + membership / industry flow plus sector membership | industry net_amount_rate cross-sectional zscore mapped back to member stocks. | source_verified_partial_cache_needs_membership_join |
| C215 | stock_vs_industry_flow_divergence | P1 | industry_flow | moneyflow + moneyflow_ind_dc/ths + membership / stock moneyflow plus mapped industry moneyflow | stock net_mf zscore minus mapped industry net_amount_rate zscore. | source_verified_partial_cache_needs_membership_join |
| C216 | ths_hot_rank_change_3d | P1 | theme_heat | ths_hot / THS hot rank/value history | -delta(rank, 3d) plus hot value change. | source_verified_cache_exists_needs_duplicate_ablation |
| C217 | global_index_risk_dispersion | P1 | macro_cross_asset | index_global / global index daily returns | cross-sectional dispersion/std of prior-close returns across US/EU/Asia indices. | source_verified_cache_exists_needs_calendar_alignment |
| C218 | shibor_liquidity_slope | P1 | macro_liquidity | shibor / SHIBOR term structure | 1M Shibor minus overnight Shibor, plus 5-day delta. | source_verified_cache_exists_needs_release_time_lock |
| C219 | convertible_bond_risk_appetite | P2 | macro_cross_asset | cb_daily / convertible bond daily market data | market-wide average cb_daily pct_chg plus amount/volume zscore. | source_verified_needs_backfill |
| C220 | ggt_southbound_flow_regime | P2 | southbound_flow | ggt_daily / southbound daily buy/sell amount | (buy_amount - sell_amount) / (buy_amount + sell_amount + eps), rolling zscore. | source_verified_needs_backfill |
| C221 | limit_pool_block_trade_followthrough | P2 | cross_family_interaction | block_trade + limit_list_d / block-trade amount/discount plus limit-up history | I(recent limit-up) * block_trade_amount_ratio or block_trade_discount_intensity. | depends_on_block_trade_backfill |
| C222 | survey_to_forecast_confirmation | P2 | cross_event_interaction | stk_surv + forecast_vip / survey heat plus forecast revision | institution_research_heat_20d * positive forecast revision indicator. | depends_on_survey_and_forecast_backfill |

### Data Fetch Backlog

| API | Priority | Needed By | Current Cache | Fetch Note |
|-----|----------|-----------|---------------|------------|
| stk_mins | P0 | C189, C190, C191, C192, C193 | missing: E:/.../tushare/stk_mins_1 | Pull all tradable A-shares in segmented batches, then verify per-stock bar coverage and bar_time alignment. |
| stk_factor_pro | P0 | C194, C195, C196, C197 | missing | Backfill and build a column catalog; remove raw OHLCV/adj duplicates and choose one adjusted family before training. |
| block_trade | P0 | C198, C199, C200, C201, C221 | directory exists but parquet count is 0 | Pull by trade_date; retain price, amount, buyer, seller, and join daily close/amount. |
| share_float | P0 | C202, C203 | missing | Retain ann_date, float_date, holder_name, float_share; enforce ann_date <= prediction date. |
| stk_holdertrade | P0 | C205 | directory exists but parquet count is 0 | Retain ann_date, in_de, holder_name, change_vol; compute signed holder trade flow. |
| pledge_stat | P1 | C204 | missing | Backfill and lock publication/asof rule before training. |
| express | P1 | C209 | missing | Retain ann_date and end_date; lag if same-day timestamp is unavailable. |
| forecast_vip/forecast | P1 | C208, C222 | partial | Range pull works; backfill by date range and keep forecast revision lineage per stock. |
| moneyflow_ind_dc/moneyflow_ind_ths | P1 | C214, C215 | partial | Backfill industry flow and verify membership mapping via dc_member/ths_member. |
| ggt_daily | P2 | C220 | missing | Secondary cross-market flow; pull after P0/P1 sources. |
| cb_daily | P2 | C219 | missing | Secondary cross-asset risk appetite; pull after P0/P1 sources. |

### Notes

- Existing official minute candidates C174-C188 are 5min-based. C189-C193 are the first data-unlocked 1min candidates.
- `stk_factor_pro` is treated as a candidate feature bank, not an automatic 261-column import. A column catalog and duplicate screen are required first.
- Block-trade, unlock, holder-trade, forecast, and macro/cross-market candidates remain research candidates until data is fetched and asof rules are enforced.

---

## Batch: candidates_20260515_shortline_full_expansion

> Purpose: Full short-line expansion from local raw pool plus TGB/social/GitHub/paper/report search.
> Scope: factor-library only; no training, no gpu_probe, no model-code change.
> All: `training_status="not_trained"`, `lockbox_role="research_candidate"`.
> Detailed report: `docs/shortline_factor_expansion_20260515.md`

### Promoted (70): C223-C292

| ID | Name | Priority | Family | Data Need | Definition | Status |
|----|------|----------|--------|-----------|------------|--------|
| C223 | sector_change_intensity_real | P0 | sector_event | sector/theme intraday events + sector flow + members | zscore(event_count_theme_day) + zscore(theme_main_inflow_rate) + zscore(active_member_ratio) | needs_sector_intraday_event_snapshot |
| C224 | theme_breadth_real | P0 | sector_event | theme members + member returns/limit pool | count(theme_member_return > 0 or limit_up) / theme_member_count | needs_theme_member_point_in_time_join |
| C225 | market_emotion_temp_score | P1 | market_emotion | limit_pool + market breadth + turnover | limit_up_count/10 + advance_decline_ratio*5 + market_turnover_ratio_20d*2 - limit_down_count/5 + max_board_height*0.5 | needs_formula_lock_weights |
| C226 | institution_trend_buy_yin | P1 | lhb_pattern | daily OHLCV + top_list/top_inst | I(stock in uptrend and red/negative daily candle) * recent_lhb_institution_net_buy_rate | needs_lhb_backfill |
| C227 | pullback_from_high_ratio | P0 | price_structure | daily OHLCV | 1 - close / rolling_max(high, N) | engineerable_now |
| C228 | breakout_sign_new_high_low | P0 | price_structure | daily OHLCV | sign(close_t - rolling_max(high, N, exclude_today)) with -1 if close_t < rolling_min(low, N, exclude_today) | engineerable_now |
| C229 | dragon_tiger_net_buy_ratio | P0 | lhb | top_list/top_inst | lhb_net_buy_amount / daily_amount for LHB-listed stocks; missing with availability flag otherwise | needs_lhb_backfill |
| C230 | board_height_score_market | P1 | board_structure | limit_pool | today_max_board_height / rolling_mean(today_max_board_height, N) | engineerable_if_limit_pool_history_complete |
| C231 | avg_seal_time_market | P1 | board_structure | limit_pool first_seal_time | mean(first_seal_minutes for limit-up stocks) | engineerable_if_limit_pool_history_complete |
| C232 | theme_uniqueness_score | P0 | sector_structure | limit_pool + theme membership | 1 / (same_theme_limit_up_count + 1) | needs_theme_member_point_in_time_join |
| C233 | anomaly_200_buy_sell_imbalance | P2 | announcement_event | announcement/regulatory event + minute/daily liquidity | I(regulatory_200pct_event_recent) * post_event_buy_sell_imbalance_proxy | needs_event_source_and_formula_lock |
| C234 | announcement_signal_decay | P1 | announcement_event | announcement timestamp + event type | exp(-lambda * hours_since_disclosure) * event_strength_score | needs_announcement_timestamp_pipeline |
| C235 | policy_density_sector | P2 | policy_event | policy/news event tags + sector mapping | count(policy_events_for_sector in trailing N days) / N | needs_policy_event_tag_pipeline |
| C236 | lhb_buy_sell_ratio | P0 | lhb | top_list/top_inst | lhb_buy_top5_total / (lhb_sell_top5_total + eps) | needs_lhb_backfill |
| C237 | seat_premium_score | P0 | lhb_seat | seat history + top_list/top_inst | sum(seat_net_buy_amount * rolling_seat_winrate_weight) / daily_amount | needs_seat_history_backfill |
| C238 | famous_seat_decay | P1 | lhb_seat | seat history + top_list/top_inst | famous_seat_net_buy_score * exp(-days_since_famous_seat_appearance / tau) | needs_seat_history_backfill |
| C239 | seat_style_vector | P1 | lhb_seat | seat history + post-event return statistics | dot(current_stock_seat_net_buy_vector, historical_seat_style_return_vector) | needs_seat_history_backfill |
| C240 | announcement_sentiment_factor | P2 | announcement_event | structured announcement or NLP score + timestamp | sum(event_score_i * recency_weight_i) / count(events) | needs_nlp_or_structured_event_pipeline |
| C241 | pead_sue_drift | P1 | earnings_event | forecast/express/fina_indicator | standardized_unexpected_earnings * I(days_since_announcement <= 60) | needs_financial_event_backfill |
| C242 | friday_announcement_drift | P2 | earnings_event | forecast/express/fina_indicator | standardized_unexpected_earnings * I(announcement_weekday == Friday) | needs_financial_event_backfill |
| C243 | etf_creation_redemption_pressure | P2 | cross_market_flow | ETF creation/redemption records + constituent mapping | net_etf_creation_amount_mapped_to_stock / stock_float_mv | needs_etf_flow_source |
| C244 | seal_time_bucket | P0 | limit_intraday | 1min bars + limit price | bucket(first_time(close >= up_limit)): 09:25, <=10:00, <=10:30, AM, PM, none | needs_1min_backfill |
| C245 | rotten_board_duration | P1 | limit_intraday | 1min bars + limit price | count(minutes after first limit touch where close < up_limit) and/or max continuous open duration | needs_1min_backfill |
| C246 | reseal_strength_real | P0 | limit_intraday | 1min bars + limit price + volume | 1/(minutes_to_reseal+1) * volume_on_reseal / mean(volume_before_reseal) | needs_1min_backfill |
| C247 | board_type_intraday | P1 | limit_intraday | 1min bars + limit price | categorical one-word/T/turnover/rotten encoded from open/high/low/close vs up_limit and open duration | needs_1min_backfill |
| C248 | attack_volume_at_limit | P0 | limit_intraday | 1min bars + limit price | volume in final upward push before first limit touch / max(rolling minute volume before push) | needs_1min_backfill |
| C249 | first_seal_time_rank_in_theme | P0 | limit_theme | 1min/limit pool + theme membership | rank(first_seal_time within same theme) normalized by theme limit-up count | needs_1min_and_theme_join |
| C250 | passive_open_board_beta | P1 | limit_theme | 1min bars + index/theme minute returns + limit price | I(stock opens board) * negative(theme_or_index_return_during_open_window) | needs_1min_and_theme_minute_join |
| C251 | active_rally_against_market | P1 | intraday_relative_strength | 1min stock bars + index/theme minute bars | stock_return_during_attack_window - beta * index_or_theme_return_same_window | needs_1min_and_index_minute_join |
| C252 | board_volume_acceptance | P0 | limit_intraday | 1min bars + limit price | volume_at_or_near_limit / (volume_below_limit_after_first_touch + eps) | needs_1min_backfill |
| C253 | long_seal_late_break_risk | P1 | limit_intraday | 1min bars + limit price | I(sealed_duration_before_14:30 >= 120min and open_board_after_14:30) | needs_1min_backfill |
| C254 | seal_before_1030_flag | P0 | limit_intraday | 1min bars + limit price | I(first_seal_time <= 10:30) | needs_1min_backfill |
| C255 | dynamic_volume_comparison_score | P0 | intraday_volume | 1min bars + historical 1min volume | max(volume_today_1min / same_clock_median_volume_Nd, volume_today_1min / rolling_max_volume_Nd) | needs_1min_backfill |
| C256 | second_wave_failure_ratio | P1 | intraday_pattern | 1min bars | second_rally_peak / first_rally_peak with failure flag if < 1 and late-session weakness | needs_intraday_wave_parser |
| C257 | late_weak_rally_failure | P1 | intraday_pattern | 1min bars | late_session_attempt_return - post_attempt_drawdown, negative if rally fails before close | needs_1min_backfill |
| C258 | first_min_direction | P0 | intraday_open | 1min bars | sign(close_09:31 - open_09:30) | needs_1min_backfill |
| C259 | first_min_flush_strength | P1 | intraday_open | 1min bars + previous-day minute bars | (open_09:30 - low_first_minute) / previous_day_max_minute_range | needs_1min_backfill |
| C260 | auction_amount_vs_prev_max_bar | P0 | auction_intraday | auction amount + previous-day 1min bars | auction_amount / max(previous_day_1min_amount) | needs_auction_and_1min_backfill |
| C261 | weak_to_strong_auction_confirm | P0 | auction_limit_theme | previous-day board weakness + auction + first 10min + theme | I(prev_rotten_or_broken_or_tail_weak) * z(auction_gap) * z(auction_volume_ratio) * I(first_10min_strength_or_seal) * theme_linkage_score | needs_auction_1min_theme_join |
| C262 | one_word_board_assist | P1 | limit_theme | limit pool + theme membership | count(one_word_limit_up_stocks in same theme) / theme_member_count | needs_theme_limit_join |
| C263 | sector_intraday_event_count | P0 | sector_event | stock_board_change_em or equivalent sector event snapshot | count(sector intraday change events by theme/date) | needs_sector_event_snapshot |
| C264 | sector_main_inflow_event_score | P0 | sector_event | sector event snapshot + sector flow | zscore(sector_main_inflow) * log1p(sector_event_count) | needs_sector_event_snapshot |
| C265 | large_buy_event_count | P1 | intraday_event | stock intraday event feed | count(large-buy events for stock before cutoff) | needs_stock_intraday_event_snapshot |
| C266 | open_limit_event_count | P1 | intraday_event | stock intraday event feed + limit price | count(open-limit/broken-limit events for stock before cutoff) | needs_stock_intraday_event_snapshot |
| C267 | auction_rise_event_count | P1 | intraday_event | stock intraday event feed + auction | count(auction-rise events for stock/date) | needs_stock_intraday_event_snapshot |
| C268 | intraday_event_intensity | P0 | intraday_event | stock intraday event feed | weighted_count(large_buy, rocket_launch, fast_rebound, limit_open, limit_seal events) | needs_stock_intraday_event_snapshot |
| C269 | sector_first_board_attribute | P1 | limit_theme | limit pool + theme membership | one-hot/scores for first board being sole seed, theme-linked, or hype-following based on same-theme board count | needs_theme_limit_join |
| C270 | second_board_confirm_leader | P0 | limit_theme | limit pool + theme membership | I(board_count == 2 and rank(first_seal_time within theme) <= top_k and theme_breadth_above_threshold) | needs_theme_limit_join |
| C271 | board_echelon_cluster_strength | P1 | limit_theme | limit pool + theme/region membership | HHI or count concentration of limit-up board heights within same theme/region echelon | needs_theme_region_mapping |
| C272 | turnover_board_real | P0 | limit_intraday | limit pool + daily turnover + auction | I(first_seal_time > 09:25) * turnover_rate * I(open_board_count within acceptable range) | needs_limit_pool_field_backfill |
| C273 | limit_up_last_min_seal | P1 | limit_intraday | 1min bars + limit price | I(first_or_final_seal_time >= 14:55) | needs_1min_backfill |
| C274 | intraday_pressure_weighted | P1 | intraday_cost | minute VWAP/volume + close | sum(volume_i * max(vwap_i - close_t, 0) * decay_i) / (sum(volume_i) * close_t) | needs_1min_or_5min_backfill |
| C275 | cgo_a_cost_gain_overhang | P1 | intraday_cost | minute VWAP/volume + daily turnover | (close_t - sum(weight_tau * vwap_tau)) / close_t, weights based on turnover decay | needs_turnover_decay_formula_lock |
| C276 | ema_cost_anchor_gap | P1 | intraday_cost | minute VWAP + turnover | (close_t - EMA(vwap, alpha=1/avg_turnover)) / close_t | needs_turnover_decay_formula_lock |
| C277 | trapped_value_weighted | P1 | intraday_cost | minute VWAP/volume + close | sum(volume_i * I(vwap_i > close_t) * decay_i) / sum(volume_i) | needs_1min_or_5min_backfill |
| C278 | wq_volume_price_decay_rank | P0 | formulaic_alpha | daily OHLCV + VWAP | rank(decay_linear(correlation(vwap, volume, short_window), decay_window)) with sign chosen by validation | engineerable_now_if_vwap_available |
| C279 | wq_sign_volume_return | P0 | formulaic_alpha | daily OHLCV + volume | sign(delta(volume, 1)) * (-delta(close, 1)) or equivalent WQ sign-volume-return transform | engineerable_now |
| C280 | wq_intraday_range_close_open | P1 | formulaic_alpha | daily OHLCV | (close - open) / (high - low + eps) with cross-sectional neutralization option | engineerable_now |
| C281 | wq_vwap_rank_reversal | P1 | formulaic_alpha | daily OHLCV + VWAP | -rank(delta(vwap, N)) * rank(delta(close, N)) | engineerable_now_if_vwap_available |
| C282 | intraday_w_shape_liquidity_deviation | P0 | intraday_liquidity | 1min/5min bars | distance of stock intraday volume/liquidity curve from market W-shape baseline | needs_1min_backfill_and_market_baseline |
| C283 | minute_periodicity_energy_1_5_10 | P1 | intraday_liquidity | 1min bars | spectral/variance energy of volume or return at 1/5/10-minute periodic components | needs_1min_backfill |
| C284 | opening_closing_volume_imbalance | P1 | intraday_liquidity | 1min/5min bars | (volume_open_30min - volume_close_30min) / total_volume | needs_1min_backfill |
| C285 | liquidity_price_impact_proxy | P1 | intraday_liquidity | 1min bars | abs(return_window) / (amount_window + eps), averaged over intraday windows | needs_1min_backfill |
| C286 | sentiment_overtrading_interaction | P2 | social_sentiment | forum/social sentiment + intraday volume | zscore(social_sentiment) * zscore(intraday_turnover_vs_baseline) | needs_social_sentiment_pipeline |
| C287 | guba_heat_volume_amplification | P2 | social_sentiment | Eastmoney Guba or similar post/comment counts + intraday volume | zscore(post_count_growth) * zscore(volume_acceleration_1min) | needs_social_scrape_pipeline |
| C288 | short_video_attention_shock | P2 | social_sentiment | Bilibili/Douyin/short-video mention counts if timestamped scrape exists | abnormal_growth(video_mentions_or_views for stock/theme) over trailing N hours/days | needs_short_video_scrape_pipeline |
| C289 | social_leader_mention_breadth | P2 | social_sentiment | social posts mapped to stock/theme | unique_author_count_mentioning_stock_or_theme / rolling_baseline_unique_authors | needs_social_scrape_pipeline |
| C290 | halt_reopen_volume_relaxation | P2 | trading_halt_event | suspend/resume events + minute/daily bars | post_resume_volume_peak * exp_decay_fit_or_ratio(first_window_volume / later_window_volume) | needs_suspend_resume_source |
| C291 | halt_reopen_abs_return_decay | P2 | trading_halt_event | suspend/resume events + minute/daily bars | abs_return_first_window / (abs_return_later_window + eps) after reopen | needs_suspend_resume_source |
| C292 | auction_true_order_after_0920 | P1 | auction_microstructure | auction snapshots at/after 09:20 | auction_buy_pressure_after_0920 / auction_buy_pressure_before_0920 or final_valid_order_ratio | needs_auction_snapshot_pipeline |

### Data Backlog

| Source | Priority | Unlocks | Current Status |
|--------|----------|---------|----------------|
| stk_mins 1min | P0 | C244-C261, C273-C285 plus C189-C193 | missing cache |
| limit_pool with first/final seal/open count fields | P0 | C223-C232, C244-C254, C262-C273 | existing but field coverage/asof must be verified |
| theme/sector membership point-in-time join | P0 | C223-C224, C232, C249-C250, C262-C264, C269-C271 | needs join/catalog |
| top_list/top_inst and seat history | P0 | C226, C229, C236-C239 | Tushare top_list/top_inst partially cached; seat history may need AKShare/EM scrape |
| stock/sector intraday event snapshots | P1 | C223, C263-C268 | needs stock_changes_em/stock_board_change_em style snapshot pipeline |
| auction final plus auction snapshots after 09:20 | P1 | C260-C261, C292 | final auction exists; 09:20 snapshot not verified |
| forecast/express/fina_indicator announcement events | P1 | C241-C242 | partial; exact ann_time/asof recommended |
| announcement/policy NLP event pipeline | P2 | C233-C235, C240 | not standardized |
| ETF creation/redemption | P2 | C243 | source not verified |
| social/forum/short-video timestamped scrape | P2 | C286-C289 | not standardized |
| suspend/resume event source | P2 | C290-C291 | not verified |

### Exclusion Rules

- Do not train P2 social/NLP/halt candidates until their data pipeline and asof rules are deterministic.
- Do not register leaked target formulas; rewrite them into pre-event or known-at-time predictors first.
- Do not assume L2/tick/orderbook availability from 1min bars.

## Audit Addendum 2026-05-15

Scope: C223-C292 (`candidates_20260515_shortline_full_expansion`).

- Structural check passed: C001-C292 are contiguous, unique, and no normalized names are duplicated.
- Added `audit_20260515` gates to C223-C292 in the machine registry.
- First-wave-after-data candidates: C229, C236, C244, C246, C247, C248, C252, C254, C258, C259, C260, C270, C272, C273, C279, C280.
- Formula corrections applied: C278, C279, C280.
- Watchlist counts: 10 window-lock, 17 formula-lock, 32 external-pipeline, 13 overlap-watch.
- Audit report: `docs/factor_registry_audit_20260515.md`.
---

## Batch: candidates_20260517_global_deep_search

> Purpose: Four-source global short-line factor expansion with strict registry gates.
> Scope: factor-library only; no training, no gpu_probe, no model-code change.
> All: `training_status="not_trained"`, `lockbox_role="research_candidate"`.
> Detailed report: `docs/global_deep_factor_search_20260517.md`

### Promoted (49): C293-C341

| ID | Name | Priority | Family | Data Need | Definition | Status |
|----|------|----------|--------|-----------|------------|--------|
| C293 | hf_downside_volatility_share | P0 | minute_hf | 1min bars | sum(r_i^2 for minute returns r_i < 0) / (sum(r_i^2) + eps), optionally averaged over trailing N sessions | engineerable_after_1min_cache |
| C294 | hf_realized_skewness_20d | P1 | minute_hf | 1min bars | mean_over_N_days( sum(r_i^3) / (sum(r_i^2) ** 1.5 + eps) ) | engineerable_after_1min_cache |
| C295 | hf_realized_kurtosis_20d | P2 | minute_hf | 1min bars | mean_over_N_days( sum(r_i^4) / (sum(r_i^2) ** 2 + eps) ) | engineerable_after_1min_cache |
| C296 | tail_volume_share_1457 | P0 | minute_hf | 1min bars | sum(volume_i for i in 14:30-14:57) / (sum(volume_i for i <= 14:57) + eps) | engineerable_after_1min_cache |
| C297 | intraday_price_volume_corr | P0 | minute_hf | 1min bars | corr(close_i, volume_i / (sum(volume_i) + eps)) over bars <= cutoff; optional trailing N-day mean | engineerable_after_1min_cache |
| C298 | intraday_pv_corr_segment_shift | P1 | minute_hf | 1min bars | corr_open_0930_1030(close, volume_share) - corr_tail_1400_1457(close, volume_share) | engineerable_after_1min_cache |
| C299 | improved_intraday_reversal_1000_to_1457 | P0 | minute_hf | 1min bars | (price_1457 / price_1000 - 1) with sign optionally reversed by validation; use trailing N-day smoothed value | engineerable_after_1min_cache |
| C300 | large_amount_bar_push_return | P0 | minute_hf | 1min bars | prod(1 + r_i for bars where amount_i is in top 30pct of intraday amount bars) - 1 | engineerable_after_1min_cache |
| C301 | high_price_volume_share | P0 | minute_hf | 1min bars | sum(volume_i where close_i is in top 20pct of intraday price range) / (sum(volume_i) + eps) | engineerable_after_1min_cache |
| C302 | low_price_absorption_repair | P1 | minute_hf | 1min bars | low_zone_volume_share * max((price_1457 - low_zone_vwap) / (low_zone_vwap + eps), 0) | engineerable_after_1min_cache |
| C303 | same_clock_return_surprise_z | P0 | minute_hf | 1min bars + trailing same-clock history | (cum_return_to_cutoff - mean_same_clock_return_Nd) / (std_same_clock_return_Nd + eps) | engineerable_after_1min_cache_and_history |
| C304 | intraday_trend_smoothness | P1 | minute_hf | 1min bars | abs(price_cutoff / open - 1) / (sum(abs(r_i for i <= cutoff)) + eps) | engineerable_after_1min_cache |
| C305 | shock_volume_decay_half_life | P0 | minute_hf | 1min bars | after largest positive volume_z shock before cutoff, fit log(volume_z) decay and record half-life in minutes | engineerable_after_1min_cache |
| C306 | shock_price_reversal_efficiency | P0 | minute_hf | 1min bars | post_shock_opposite_return_Nmin / (abs(shock_return) + eps) after the largest minute return shock before cutoff | engineerable_after_1min_cache |
| C307 | intraday_market_beta_20d | P1 | minute_hf | 1min stock bars + index/all-stock minute return | rolling_20d beta from stock minute returns to market minute returns, computed using bars <= cutoff | engineerable_after_1min_and_market_minute_cache |
| C308 | intraday_idio_vol_share | P1 | minute_hf | 1min stock bars + index/all-stock minute return | var(residual_i from intraday_market_beta regression) / (var(stock_minute_returns) + eps) | engineerable_after_1min_and_market_minute_cache |
| C309 | minute_market_breadth_thrust | P0 | minute_market | 1min all-stock bars | share_of_universe(cum_return_to_cutoff > same_clock_return_z_threshold) or breadth acceleration over last K minutes | engineerable_after_1min_universe_cache |
| C310 | cross_sectional_minute_momentum_rank | P0 | minute_market | 1min all-stock bars | rank(cum_return_to_cutoff) within tradable universe at cutoff | engineerable_after_1min_universe_cache |
| C311 | first5_vwap_hold_ratio | P0 | minute_hf | 1min bars | count(minutes after 09:35 with close_i >= first5_vwap) / count(minutes after 09:35 up to cutoff) | engineerable_after_1min_cache |
| C312 | minute_opening_range_breakout_quality | P0 | minute_hf | 1min bars | I(price_breaks_first30_high_before_cutoff) * breakout_return / (drawdown_after_breakout + eps) | engineerable_after_1min_cache |
| C313 | vwap_reclaim_count | P1 | minute_hf | 1min bars | count of transitions from close_i < session_vwap_i to close_i >= session_vwap_i before cutoff | engineerable_after_1min_cache |
| C314 | shortest_path_illiquidity_intraday | P0 | minute_hf | 1min bars | sum(abs(r_i)) / (abs(cum_return_to_cutoff) + eps) * 1/(amount_to_cutoff + eps), higher means choppy illiquid path | engineerable_after_1min_cache |
| C315 | intraday_volume_entropy | P1 | minute_hf | 1min bars | -sum(p_i * log(p_i)) where p_i = volume_i / sum(volume_i up to cutoff) | engineerable_after_1min_cache |
| C316 | late_breakout_fail_probability | P1 | minute_hf | 1min bars | I(breakout_after_14:00) * max(breakout_price - price_1457, 0) / (breakout_price + eps) | engineerable_after_1min_cache |
| C317 | weak_to_strong_open_reclaim | P0 | auction_open | 1min bars + previous board/weakness tag | I(open_gap_or_first5_return < 0) * I(price_reclaims_open_or_vwap_before_1030) * volume_confirm_z | engineerable_after_1min_and_prev_state_tag |
| C318 | auction_open_to_first5_reclaim | P1 | auction_open | auction final + 1min bars | I(auction/open weak) * max(close_09:35 - open_price, 0) / (open_price + eps) | engineerable_after_auction_snapshot_verified |
| C319 | auction_false_strength_risk | P1 | auction_open | auction final + 1min bars | I(auction_gap_positive and auction_amount_z high) * max(open_price - close_09:35, 0) / (open_price + eps) | engineerable_after_auction_snapshot_verified |
| C320 | market_open_board_rate | P0 | limit_board | limit pool with open-board/broken-board timestamp | open_board_count_to_cutoff / max(limit_up_touched_count_to_cutoff, 1) | engineerable_if_limit_pool_has_event_time |
| C321 | market_limit_attempt_count | P0 | limit_board | limit pool events | count(stocks that touched up_limit before cutoff) excluding ST and one-word boards if configured | engineerable_if_limit_pool_has_event_time |
| C322 | board_height_compression_speed | P0 | limit_board | limit_list_d or limit pool board height history | delta(max_board_height, 1d or 3d) / trailing_max_board_height_Nd | engineerable_if_limit_pool_history_complete |
| C323 | broken_board_loss_diffusion | P0 | limit_board | broken-board list + returns | mean(next_or_same_cutoff_return of broken-board stocks) - market_return, optionally breadth-weighted | engineerable_if_limit_pool_has_break_status |
| C324 | first_board_to_second_board_conversion | P0 | limit_board | limit_list_d with board_count history | count(prev_day_first_board and today_board_count>=2) / count(prev_day_first_board) | engineerable_if_limit_pool_history_complete |
| C325 | high_board_survival_rate_3d | P0 | limit_board | limit_list_d with board_count history | share of stocks with board_count>=N that keep board_count>=N or do not collapse over next observed 1-3 sessions for historical state feature | engineerable_if_limit_pool_history_complete |
| C326 | seal_rate_collapse_3d | P0 | limit_board | limit pool with seal/break status | seal_success_rate_today_or_cutoff - rolling_mean(seal_success_rate, 3d) | engineerable_if_limit_pool_has_break_status |
| C327 | seal_money_to_float_mv | P1 | limit_board | limit pool seal amount + share_float | seal_amount_at_cutoff / (free_share * price_at_cutoff + eps) | engineerable_if_limit_pool_has_seal_amount |
| C328 | lhb_net_buy_to_float | P0 | lhb | top_list/top_inst + share_float | lhb_net_buy_amount / (free_share * close + eps) for listed stocks; otherwise missing with availability flag | engineerable_after_lhb_backfill |
| C329 | block_trade_discount_persistence_5d | P0 | block_trade | block_trade + daily close | rolling_5d amount-weighted mean((block_price / close_ref) - 1) | engineerable_after_block_trade_backfill |
| C330 | block_trade_seller_concentration | P1 | block_trade | block_trade with seller party if present | HHI of seller-side block_trade amount by seller over trailing N days | engineerable_if_block_trade_party_fields_exist |
| C331 | unlock_pressure_to_adv_30d | P1 | unlock_float | share_float/unlock schedule + daily volume | upcoming_unlock_shares_30d / (rolling_mean(volume_shares, 20d) + eps) | engineerable_if_unlock_schedule_available |
| C332 | pledge_release_acceleration | P1 | pledge | pledge_stat + share_float | -delta(pledged_share_ratio, short_window) - delta(pledged_share_ratio, long_window) | engineerable_after_pledge_backfill |
| C333 | forecast_revision_dispersion_change | P1 | forecast_event | forecast_vip/express_vip | delta(width_of_forecast_interval / abs(forecast_midpoint + eps), N days) | engineerable_after_forecast_backfill |
| C334 | research_survey_recency_decay | P1 | research_event | stk_surv | sum(exp(-days_since_survey / tau) * survey_weight) over trailing N days | engineerable_after_survey_backfill |
| C335 | hsgt_top10_entry_streak | P1 | northbound_flow | hsgt_top10 | consecutive days stock appears in hsgt_top10 net-buy list or rolling entry count | engineerable_after_hsgt_backfill |
| C336 | ccass_acceleration_rank | P1 | northbound_flow | ccass_hold | cross-sectional rank(delta(holding_ratio, short_window) - delta(holding_ratio, long_window)) | engineerable_after_ccass_backfill |
| C337 | industry_flow_rotation_accel | P1 | industry_flow | moneyflow_ind_dc or moneyflow_ind_ths | rank(delta(industry_main_net_inflow_rate, 3d) - delta(industry_main_net_inflow_rate, 10d)) mapped to stock industry | engineerable_after_industry_flow_join |
| C338 | wq_volume_price_rank_divergence | P1 | formulaic_alpha | daily OHLCV or 14:57 proxy OHLCV | rank(delta(close, 1)) - rank(delta(volume, 1)) | engineerable_now_with_daily_or_1457_proxy |
| C339 | wq_turnover_adjusted_reversal | P1 | formulaic_alpha | daily OHLCV + turnover/free float | -ret_1 / (log1p(turnover_rate) + eps) | engineerable_now_with_daily_or_1457_proxy |
| C340 | qlib_alpha360_intraday_shape_moment | P1 | formulaic_alpha | 1min bars | shape moments from normalized intraday close sequence: slope, curvature, max drawdown and last-position percentile | engineerable_after_1min_cache |
| C341 | global_overnight_risk_gap | P2 | cross_market | index_global + A50/overseas index series | zscore(weighted overnight return of A50/HK/US risk basket) * stock_or_theme_beta_to_global_risk | engineerable_after_global_calendar_alignment |

---

## Web Expanded Search 2026-05-17

> Batch: `candidates_20260517_web_expanded_surface`
> IDs: `C342-C355`
> Count: 14
> Scope: factor-library only; no training, no gpu_probe, no frozen/model changes.

| ID | Name | Priority | Family | Status |
|----|------|----------|--------|--------|
| C342 | auction_amount_to_float_mv | P0 | auction_open | engineerable_after_auction_and_share_float_join |
| C343 | auction_participation_breadth | P1 | auction_market | engineerable_after_auction_universe_cache |
| C344 | auction_open_gap_dispersion | P1 | auction_market | engineerable_after_auction_universe_cache |
| C345 | lhb_institution_net_to_float | P0 | lhb | engineerable_after_top_inst_backfill |
| C346 | lhb_buy_seat_concentration_hhi | P1 | lhb | engineerable_if_lhb_seat_detail_exists |
| C347 | insider_trade_net_to_float | P1 | holder_trade | engineerable_after_stk_holdertrade_backfill |
| C348 | insider_trade_recency_decay | P2 | holder_trade | engineerable_after_stk_holdertrade_backfill |
| C349 | survey_participant_intensity_change | P1 | research_event | engineerable_after_survey_backfill |
| C350 | forecast_directional_consensus | P1 | forecast_event | engineerable_after_forecast_backfill |
| C351 | minute_return_state_transition_entropy | P1 | minute_hf | engineerable_after_1min_cache |
| C352 | minute_extreme_pre_peak_ratio | P1 | minute_hf | engineerable_after_1min_cache |
| C353 | minute_volume_spectral_residual | P1 | minute_hf | engineerable_after_1min_history_matrix |
| C354 | cumulative_volume_curve_surprise_1457 | P0 | minute_hf | engineerable_after_1min_history_matrix |
| C355 | minute_volume_synchronization_to_market | P1 | minute_market | engineerable_after_1min_universe_cache |

Full detail: [web_expanded_factor_search_20260517.md](web_expanded_factor_search_20260517.md)

---

## Web Saturation Search 2026-05-17

> Batch: `candidates_20260517_web_saturation`
> IDs: `C356-C370`
> Count: 15
> Scope: factor-library only; no training, no gpu_probe, no frozen/model changes.

| ID | Name | Priority | Family | Status |
|----|------|----------|--------|--------|
| C356 | volume_lagged_return_corr_1457 | P0 | minute_hf | engineerable_after_1min_cache |
| C357 | large_volume_lagged_return_corr | P1 | minute_hf | engineerable_after_1min_cache |
| C358 | volume_weighted_price_skewness | P1 | minute_hf | engineerable_after_1min_cache |
| C359 | unit_amount_entropy | P1 | minute_hf | engineerable_after_1min_cache |
| C360 | intraday_amihud_tail_ratio | P1 | minute_hf | engineerable_after_1min_cache |
| C361 | auction_turnover_jump_20d | P0 | auction_open | engineerable_after_auction_history_cache |
| C362 | auction_gap_positive_breadth | P1 | auction_market | engineerable_after_auction_universe_cache |
| C363 | lhb_seat_alpha_score_60d | P1 | lhb | engineerable_after_lhb_seat_history_cache |
| C364 | lhb_theme_seat_crowding | P1 | lhb | engineerable_after_lhb_theme_join |
| C365 | guba_sentiment_overtrading_gap | P2 | social_attention | needs_timestamped_social_pipeline |
| C366 | limit_pre_hit_volume_acceleration | P0 | limit_board | engineerable_if_limit_hit_timestamp_available |
| C367 | limit_pre_hit_return_curvature | P1 | limit_board | engineerable_if_limit_hit_timestamp_available |
| C368 | northbound_top10_turnover_crowding | P1 | northbound_flow | engineerable_after_hsgt_top10_backfill |
| C369 | industry_lhb_flow_rotation_strength | P1 | industry_flow | engineerable_after_lhb_industry_aggregation |
| C370 | block_trade_discount_volume_pressure | P1 | block_trade | engineerable_after_block_trade_backfill |

Full detail: [web_saturation_factor_search_20260517.md](web_saturation_factor_search_20260517.md)

## Web Saturation Search 2 2026-05-18

- Batch: `candidates_20260518_web_saturation2`
- Added: 22 candidates (`C371-C392`)
- Scope: factor-library only; no training; no gpu_probe; no model/frozen config changes.

| ID | Name | Priority | Family | Engineering |
|---|---|---|---|---|
| C371 | hcvp_price_volume_corr | P0 | minute_hf | engineerable_after_1min_cache |
| C372 | lcvp_price_volume_corr | P1 | minute_hf | engineerable_after_1min_cache |
| C373 | hcvp_lcvp_corr_spread | P0 | minute_hf | engineerable_after_1min_cache |
| C374 | intraday_smart_money_q_return | P0 | minute_smart_money | engineerable_after_1min_cache |
| C375 | intraday_smart_money_q_volume_share | P1 | minute_smart_money | engineerable_after_1min_cache |
| C376 | minute_volume_benford_deviation | P1 | minute_volume_shape | engineerable_after_1min_cache |
| C377 | volume_peak_return_contribution | P0 | minute_volume_peak | engineerable_after_1min_cache |
| C378 | volume_ridge_persistence_share | P1 | minute_volume_peak | engineerable_after_1min_cache |
| C379 | volume_valley_reversal_strength | P1 | minute_volume_peak | engineerable_after_1min_cache |
| C380 | volume_peak_valley_price_spread | P1 | minute_volume_peak | engineerable_after_1min_cache |
| C381 | price_jump_peak_density | P0 | minute_price_jump | engineerable_after_1min_cache |
| C382 | price_jump_ridge_followthrough | P1 | minute_price_jump | engineerable_after_1min_cache |
| C383 | price_jump_valley_reversal | P1 | minute_price_jump | engineerable_after_1min_cache |
| C384 | minute_amount_autocorr_1 | P1 | minute_amount_shape | engineerable_after_1min_cache |
| C385 | minute_amount_tail_kurtosis | P1 | minute_amount_shape | engineerable_after_1min_cache |
| C386 | minute_bipower_jump_ratio | P0 | minute_realized_jump | engineerable_after_1min_cache |
| C387 | bar_vpin_proxy_1min | P1 | minute_orderflow_proxy | engineerable_after_1min_cache |
| C388 | hsgt_top10_member_churn | P1 | northbound_flow | engineerable_after_hsgt_top10_backfill |
| C389 | ccass_holder_concentration_delta | P1 | northbound_flow | engineerable_if_ccass_participant_fields_available |
| C390 | industry_turnover_crowding_score | P1 | industry_crowding | engineerable_after_industry_flow_backfill |
| C391 | technical_signal_consensus_261 | P2 | technical_indicator_bank | engineerable_after_stk_factor_pro_catalog |
| C392 | technical_signal_disagreement_entropy | P2 | technical_indicator_bank | engineerable_after_stk_factor_pro_catalog |

Full report: `C:\Users\zzzzzzl\Desktop\subagent\docs\web_saturation_factor_search_20260518.md`

## Social Media Deep Search 2026-05-18

Purpose: explicitly audit Taoguba, Xueqiu/Guba-style discussion, Bilibili/Douyin short-video surfaces, and the local TGB raw pool for short-line factors without training or model changes.

Batch: `candidates_20260518_social_media_deep_search`

| ID | Name | Priority | Family | Status |
|---|---|---:|---|---|
| C393 | `tgb_echelon_continuity_gap` | P1 | limit_theme | candidate_ready_after_limit_pool_join |
| C394 | `tgb_high_low_switch_pressure` | P0 | market_cycle | candidate_ready_after_limit_pool_join |
| C395 | `tgb_ice_point_repair_age` | P1 | market_emotion | candidate_ready_after_market_emotion_join |
| C396 | `tgb_first_divergence_repair_strength` | P1 | limit_theme | candidate_ready_after_theme_join |
| C397 | `tgb_solo_guide_theme_signal` | P2 | limit_theme | needs_theme_text_pipeline |
| C398 | `tgb_theme_capacity_turnover_fit` | P1 | sector_structure | candidate_ready_after_theme_join |
| C399 | `tgb_sector_independence_ex_leader` | P1 | sector_structure | candidate_ready_after_theme_join |
| C400 | `tgb_explosive_volume_weak_open` | P0 | volume_structure | candidate_ready_after_daily_and_minute_join |
| C401 | `tgb_market_split_extreme_divergence` | P1 | market_emotion | code_existing_or_candidate_ready |
| C402 | `tgb_regulatory_pressure_countdown` | P1 | announcement_event | needs_announcement_timestamp_pipeline |
| C403 | `tgb_position_uniqueness_score` | P1 | limit_theme | candidate_ready_after_theme_join |
| C404 | `tgb_theme_cycle_day_position` | P1 | market_cycle | candidate_ready_after_theme_join |
| C405 | `social_cross_platform_attention_consensus` | P2 | social_attention | needs_timestamped_social_pipeline |
| C406 | `short_video_theme_velocity_24h` | P2 | social_attention | needs_timestamped_social_pipeline |

Notes:
- Already-covered social/TGB basics were not duplicated: board counts, market emotion counts, weak-to-strong auction variants, and existing short-video/social attention factors.
- C405/C406 are social-pipeline candidates only; do not train until timestamped Bilibili/Douyin/Guba/TGB mention data is reproducible.

## Global Saturation Final Search 2026-05-18

Purpose: expanded web/local/source saturation pass across social/TGB, broker reports, GitHub/open-source, academic papers, and local raw pool leftovers. Registry only: no training, no gpu_probe, no model/frozen config changes.

Batch: `candidates_20260518_global_saturation_final`

| ID | Name | Priority | Family | Data Need | Status |
|---|---|---:|---|---|---|
| C407 | `capital_memory_reactivation_score` | P1 | capital_memory | event/theme labels, historical event leaders, daily OHLCV, limit_pool; optional social/LHB confirmation | needs_event_theme_leader_history |
| C408 | `consensus_hot_stock_memory_score` | P2 | capital_memory | timestamped social/stock-bar mentions, LHB appearances, limit_pool board height history | needs_timestamped_social_or_lhb_history |
| C409 | `lottery_max_ivol_skew_pressure` | P1 | behavioral_lottery | daily returns; market/industry benchmark return for idiosyncratic residuals; optional 1min realized variant | engineerable_now_with_daily_history |
| C410 | `limit_premium_decay_regime` | P1 | market_emotion | limit_pool yesterday-limit basket, daily close or 14:57 proxy close, market calendar | candidate_ready_after_limit_pool_join |
| C411 | `industry_limit_reversal_pressure` | P1 | industry_rotation | industry membership, limit_pool, daily returns for industry members | candidate_ready_after_industry_limit_pool_join |
| C412 | `multi_seat_buy_strength` | P1 | lhb_seat | LHB top buy seats, buy amount by seat, daily amount, optional known-seat catalog | engineerable_after_lhb_backfill |
| C413 | `famous_seat_repeat_visit_score` | P1 | lhb_seat | LHB seat history, stock/theme mapping, historical post-LHB forward returns for prior events | engineerable_after_lhb_seat_history_cache |
| C414 | `active_seat_absence_market_risk` | P2 | lhb_market | market-wide LHB seat appearances and rolling active-seat catalog | engineerable_after_lhb_market_history_cache |
| C415 | `intraday_wavelet_highfreq_energy_ratio` | P2 | minute_hf | 1min bars: close; optional amount/volume sequence for parallel volume wavelet energy | engineerable_after_1min_cache |
| C416 | `volume_spike_memory_interval` | P2 | volume_memory | daily volume or 1min volume history; spike threshold based on rolling volume-volatility z-score | engineerable_after_volume_history_cache |

Important asof notes:
- C412-C414 are LHB after-close factors; use for T+1 only unless exact earlier disclosure timestamps are proven.
- C407-C408 require timestamped event/theme/social labels before same-day use.
- C409-C411 can be built from daily/limit/industry histories; C410 can optionally use a 14:57 proxy close.
- C415-C416 need 1min or volume history and must be cutoff-bounded for 14:57 replay.

## All-Channel Factor Expansion 2026-05-18

Purpose: expanded search across local raw pool, broker reports, papers, GitHub/open-source, social/TGB ideas, and data-availability notes. Registry only: no training, no gpu_probe, no model/frozen config changes.

Batch: `candidates_20260518_all_channel_expansion`

| ID | Name | Priority | Family | Data Need | Status |
|---|---|---:|---|---|---|
| C417 | `etf_constituent_flow_pressure` | P1 | etf_flow | ETF constituent weights, ETF net flow or share change, ETF NAV/close, stock float market value | needs_etf_holding_flow_join |
| C418 | `option_pcr_market_sentiment` | P2 | option_market | option daily volume/open-interest by underlying, option basic mapping, market or ETF underlying mapping | needs_option_daily_pipeline |
| C419 | `option_iv_skew_risk` | P2 | option_market | option implied volatility or fields sufficient to compute IV, option delta/moneyness, underlying mapping | needs_option_iv_fields |
| C420 | `convertible_forced_redemption_pressure` | P1 | convertible_bond | convertible-stock mapping, conversion price, stock daily close, convertible status | needs_cb_basic_and_stock_join |
| C421 | `convertible_equity_linkage_premium_gap` | P2 | convertible_bond | convertible daily price, conversion value/premium, underlying stock return | needs_cb_daily_join |
| C422 | `limit_spillover_network_traction` | P1 | limit_network | limit_pool, industry/theme membership, co-limit/correlation network, daily returns | needs_peer_network_cache |
| C423 | `news_surge_sentiment_event_factor` | P2 | news_attention | timestamped stock news count, NLP sentiment, stock-symbol mapping | needs_timestamped_news_pipeline |
| C424 | `margin_buy_intensity_relative` | P1 | margin_derivative | margin_detail financing buy amount, daily amount, stock identifier mapping | needs_margin_detail_join |
| C425 | `short_selling_pressure_ratio` | P2 | margin_derivative | margin short-selling volume/amount fields and daily volume/amount | needs_margin_short_fields |

Asof notes:
- C417 ETF constituent flow is T+1 unless ETF flow/holding timestamps prove same-day availability.
- C418-C419 option features are T+1 unless intraday option data is available and timestamped.
- C420-C421 convertible features are daily/T+1 unless intraday convertible quotes and conversion terms are timestamped.
- C422 can be 14:57-capable if peer limit events are cutoff-bounded.
- C423 requires timestamped news and symbol mapping before same-day use.
- C424-C425 margin features are normally after-close/T+1.

## Saturation Pass 2 2026-05-18

Purpose: second all-channel saturation pass over local raw pool, broker/paper/web sources, TGB/Xueqiu/Bilibili search surfaces, social/search attention, and newly available data directions. Registry only: no training, no gpu_probe, no model/frozen config changes.

Batch: `candidates_20260518_saturation_pass2`

| ID | Name | Priority | Family | Data Need | Status |
|---|---|---:|---|---|---|
| C426 | `yesterday_limit_open_premium` | P1 | limit_premium | limit_pool yesterday basket and daily open/prev close | engineerable_after_limit_pool_and_open_join |
| C427 | `board_height_ceiling_proximity` | P1 | limit_board | limit_pool board_count history | engineerable_after_limit_pool_history |
| C428 | `subnew_limit_board_heat` | P2 | subnew_board | listing date, limit_pool, daily returns | needs_listing_age_limit_pool_join |
| C429 | `seal_time_distribution_entropy` | P1 | limit_board | limit_pool first seal time and market calendar | engineerable_if_limit_pool_has_seal_time |
| C430 | `reversal_board_quality_score` | P1 | limit_board | daily OHLCV, 1min bars, limit_pool seal/open-board fields | needs_formula_lock |
| C431 | `cb_stock_limit_up_premium_spread` | P2 | convertible_bond | cb_daily, cb_basic stock mapping, conversion premium, underlying limit_pool | needs_cb_daily_and_limit_pool_join |
| C432 | `has_convertible_bond_leader_drag` | P2 | convertible_bond | active convertible-stock mapping and theme/leader score | needs_cb_active_mapping |
| C433 | `intraday_theme_reflow_score` | P1 | theme_intraday | theme membership, 1min bars, leader identity or board_count | needs_theme_minute_matrix |
| C434 | `follower_position_confirmation` | P1 | limit_theme | theme membership, leader/follower tag, intraday/daily returns, limit_pool | needs_theme_leader_follower_labels |
| C435 | `tail20_amount_concentration` | P1 | minute_amount_shape | 1min bars amount | engineerable_after_1min_cache |
| C436 | `minute_volume_path_roughness` | P1 | minute_volume_shape | 1min bars volume | engineerable_after_1min_cache |
| C437 | `volume_peak_count_factor` | P1 | minute_volume_peak | 1min bars volume | engineerable_after_1min_cache |
| C438 | `realized_volatility_peak_cluster_count` | P1 | minute_volatility_shape | 1min close/returns | engineerable_after_1min_cache |
| C439 | `local_reversal_by_volume_bucket` | P1 | minute_reversal | 1min returns and volume bucket labels | engineerable_after_1min_cache |
| C440 | `micro_partition_volatility_spread` | P1 | minute_volatility_shape | 1min returns and volume partition labels | engineerable_after_1min_cache |
| C441 | `high_low_price_bucket_momentum` | P1 | minute_price_bucket | 1min close/returns | engineerable_after_1min_cache |
| C442 | `high_low_volume_bucket_reversal` | P1 | minute_volume_bucket | 1min close/returns and volume | engineerable_after_1min_cache |
| C443 | `amount_distribution_asymmetry` | P1 | minute_amount_shape | 1min amount | engineerable_after_1min_cache |
| C444 | `dragon_list_reason_type_score` | P1 | lhb_reason | top_list/LHB reason text, parsed reason categories, stock-date event | needs_lhb_reason_parser |
| C445 | `dragon_list_historical_reason_premium` | P1 | lhb_reason | top_list/LHB reason type, historical forward returns, market regime labels | needs_lhb_reason_history_cache |
| C446 | `guba_attention_surge_score` | P2 | social_attention | timestamped Guba/Eastmoney post count by stock | needs_timestamped_guba_pipeline |
| C447 | `baidu_search_attention_surge` | P2 | search_attention | Baidu search index by stock name/code and timestamp/date | needs_baidu_index_pipeline |
| C448 | `retail_fomo_moneyflow_limit_interaction` | P1 | retail_behavior | moneyflow small-order fields, turnover, daily/limit_pool state | needs_moneyflow_limit_join |
| C449 | `disposition_effect_pressure_proxy` | P2 | retail_behavior | daily returns, chip/cost proxy or turnover-cost model, small-order moneyflow sell pressure | needs_chip_or_cost_and_small_order_sell_fields |
| C450 | `convertible_clause_game_score` | P2 | convertible_bond | cb_basic clause fields, conversion price history, stock close, issuer status | needs_cb_clause_fields |

Asof notes:
- C426-C430 use limit/auction/1min/board data and can be cutoff-bounded if source timestamps exist.
- C431-C432 and C450 are convertible-bond candidates; most practical usage is T+1 unless intraday CB data is timestamped.
- C433-C434 require stable theme and leader/follower labels.
- C435-C443 require 1min cache and one-sided live calculations.
- C444-C445 are LHB reason candidates and are after-close/T+1 only.
- C446-C447 require timestamped social/search pipelines; C448-C449 need moneyflow/chip or cost fields.

## Saturation Pass 3 Tail Review 2026-05-18

Purpose: final tail review of top remaining raw-pool candidates after pass 2. Registry only: no training, no gpu_probe, no model/frozen config changes.

Batch: `candidates_20260518_saturation_pass3_tail`

| ID | Name | Priority | Family | Data Need | Status |
|---|---|---:|---|---|---|
| C451 | `option_unusual_volume_shock` | P2 | option_market | option daily volume by underlying and option type; underlying to stock/ETF mapping | needs_option_daily_pipeline |
| C452 | `option_iv_rv_spread` | P2 | option_market | option implied volatility, underlying realized volatility | needs_option_iv_fields |
| C453 | `option_iv_term_structure_inversion` | P2 | option_market | option IV by maturity and underlying | needs_option_iv_term_structure |
| C454 | `etf_premium_discount_arbitrage_pressure` | P1 | etf_flow | ETF premium/discount or IOPV, ETF holdings weights, constituent stock mapping | needs_etf_iopv_or_premium_pipeline |
| C455 | `last_5min_return_pressure` | P1 | minute_tail | 1min bars close | engineerable_after_1min_cache |
| C456 | `intraday_return_curve_shape` | P1 | minute_path | 1min bars close and fixed intraday windows | engineerable_after_1min_cache |
| C457 | `t_plus1_limit_sell_pressure` | P1 | limit_board | limit_pool prior-day limit-up flag and current turnover/auction/minute volume | needs_limit_pool_turnover_join |
| C458 | `index_option_expiry_week_gate` | P2 | option_market_regime | trading calendar, option expiry calendar, market volatility/PCR state | needs_option_expiry_calendar |
| C459 | `hot_concept_count_exposure` | P2 | theme_attention | stock-theme membership and theme heat score | needs_theme_heat_pipeline |

Asof notes:
- C451-C453 and C458 are option-market candidates; normally T+1 unless timestamped intraday option data exists.
- C454 is ETF premium/discount; daily version is T+1, intraday IOPV version requires timestamps.
- C455-C457 can be cutoff-bounded with 1min/auction/limit data.
- C459 requires timestamped or versioned theme heat.

## Saturation Pass 4 No-New External Review 2026-05-18

Purpose: continue all-channel short-line factor search after C426-C459 and verify whether any additional external or newly available API direction should enter the registry.

Report: `docs/saturation_pass4_no_new_external_review_20260518.md`

Result: no new factor IDs were added. Registry remains C001-C459.

Rechecked surfaces:

- Broker / academic / paper-style high-frequency, microstructure, ETF, option, convertible, and financing sources.
- Open-source / GitHub style factor libraries including Qlib/Alpha-style OHLCV and technical-indicator operators.
- Social/community trading language from Taoguba, Xueqiu, Bilibili/Douyin-style dragon-head, auction, weak-to-strong, re-seal, theme-reflow ideas.
- Newly available Tushare API directions including `block_trade`, `stk_holdertrade`, `pledge_stat`, `forecast_vip`, `hsgt_top10`, `ccass_hold`, `ggt_daily`, `moneyflow_ind`, `index_global`, `shibor`, and `stk_factor_pro`.

Conclusion:

- New API directions are already represented by existing candidate families such as C198-C201/C329-C330/C370 for block trade, C205/C347-C348 for holder trade, C204/C332 for pledge, C081/C208/C333/C350 for forecast, C061/C210/C335/C368/C388 for HSGT top10, C080/C211/C336/C389 for CCASS, C053/C088/C120/C214-C215/C337/C390 for industry flow, C128/C217/C341 for global index, C079/C218 for SHIBOR, and C194-C197/C391-C392 for technical indicator bank.
- Remaining external hits were rejected or deferred because they required Level-2 order book / tick-order fields, lacked a formula and stock-date key, duplicated existing factor families, or could not satisfy a safe asof rule.
- No C460+ candidate should be created from this pass.

## Saturation Pass 5 Event-Gap Review 2026-05-19

Purpose: fill event-driven gaps after registry/raw-pool/web saturation checks. Registry only: no training, no gpu_probe, no model/frozen config changes.

Batch: `candidates_20260519_saturation_pass5_event_gap`

| ID | Name | Priority | Family | Data Need | Status |
|---|---|---:|---|---|---|
| C460 | `buyback_plan_strength` | P1 | buyback_event | repurchase announcement rows, daily close, float market value | engineerable_after_repurchase_backfill |
| C461 | `buyback_execution_pressure` | P1 | buyback_event | repurchase implementation/completion rows and daily amount | engineerable_after_repurchase_backfill |
| C462 | `buyback_price_support_gap` | P2 | buyback_event | active repurchase plan high_limit/exp_date and daily close | needs_active_repurchase_state_table |
| C463 | `esop_discount_incentive_gap` | P2 | employee_stock_ownership | announcement title/pdf extraction for employee stock ownership plan, purchase price, amount, lock-up; daily close and float_mv | needs_anns_d_pdf_parser |
| C464 | `private_placement_break_repair_gap` | P2 | private_placement_event | private placement announcement or issuance details, placement price/amount, daily close, float_mv | needs_private_placement_parser |
| C465 | `ma_restructure_announcement_surprise` | P2 | ma_restructure_event | announcement title/pdf extraction, optional suspend/resume flag, deal size, industry relation, daily close/float_mv | needs_anns_d_ma_parser |

Asof notes:
- C460-C462 use Tushare `repurchase`; same-day use requires reliable `rec_time`, otherwise use T+1.
- C463-C465 use `anns_d`/PDF-derived event fields; all text extraction must be point-in-time and versioned.
- C465 may optionally join `suspend_d`, but it must not use full-day resumption returns before cutoff.

## Social Concept Saturation 2026-05-19

Added formal research candidates `C466`-`C475` from strict review of weak-to-strong / leader temperament / capital recognition / divergence acceptance language.

| ID | Name | Priority | Status |
|---|---|---:|---|
| C466 | false_weak_no_new_low_hold | P0 | not_trained / research_candidate |
| C467 | weak_to_strong_reclaim_efficiency | P0 | not_trained / research_candidate |
| C468 | morning_false_weak_reversal_score | P1 | not_trained / research_candidate |
| C469 | divergence_absorption_efficiency | P0 | not_trained / research_candidate |
| C470 | substitute_leader_kawei_score | P1 | not_trained / research_candidate |
| C471 | first_negative_repair_quality | P1 | not_trained / research_candidate |
| C472 | t_board_reseal_recognition | P1 | not_trained / research_candidate |
| C473 | leader_faith_decay_regime | P1 | not_trained / research_candidate |
| C474 | same_height_competition_pressure | P1 | not_trained / research_candidate |
| C475 | weak_to_strong_no_gap_fill_followthrough | P1 | not_trained / research_candidate |

Detailed report: `C:\Users\zzzzzzl\Desktop\subagent\docs\social_concept_saturation_factor_search_20260519.md`

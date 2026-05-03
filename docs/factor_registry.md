# Factor Registry

> Updated: 2026-05-03
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

## Next Search Candidates 2026-05-03

> Three-path search: taoguba short-term context, GitHub/papers, social media/live trading rules
> Full detail: [next_factor_candidates_20260503.md](next_factor_candidates_20260503.md)
> Total: 42 candidates (12 P0, 19 P1, 7 P2, 4 blocked)
> Constraint: no training, no gpu_probe.py changes, no frozen_forward_config changes
> Existing duplicates checked: close_position, volume_z_20, overnight_vs_intraday, corwin_schultz_spread, turnover_chg_5, volume_price_divergence_5 -- all skipped

### P0 Candidates (12)

| ID | Name | Family | Formula | Data Source | Not Redundant Because |
|----|------|--------|---------|-------------|----------------------|
| C001 | mf_flow_intensity | moneyflow | net_mf_amount / amount | moneyflow + daily | Normalizes raw flow by turnover; 1M flow means different for 10M vs 1B turnover |
| C002 | mf_momentum_5d | moneyflow | (net_mf - mean_5d) / std_5d | moneyflow | Z-score captures acceleration; raw net_mf is level only |
| C003 | mf_persistence_5d | moneyflow | sum(net_mf > 0, 5) / 5 | moneyflow | Binary streak; removes magnitude noise from net_mf |
| C004 | ff_adjusted_flow | moneyflow | net_mf / (free_share * close) | moneyflow + daily_basic | Interaction of 2 validated features; capacity-normalized flow |
| C005 | limit_space_compression | stk_limit | 1 - up_dist / limit_range | stk_limit | Regime-aware (10% vs 20%); up_dist alone is absolute |
| C006 | limit_approach_velocity | stk_limit | up_dist[T-1] - up_dist[T] | stk_limit | First derivative; up_dist is level only |
| C007 | limit_range_utilization | stk_limit | (high-low) / (limit_range * close) | stk_limit + OHLCV | range_pct normalizes by price, this normalizes by constraint |
| C008 | seal_strength_proxy | interaction | elg_ratio * (1 - up_dist/range) | moneyflow + stk_limit | 3-feature product; captures seal-board narrative |
| C009 | main_force_divergence | moneyflow | abs(lg_ratio - elg_ratio) | moneyflow | Institutional disagreement dimension; neither ratio alone captures |
| C010 | float_relative_impact | capacity | vol_ratio * volume / free_share | daily_basic + OHLCV | Turnover stress on float; none of 3 inputs captures alone |
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
| 2 | C001 | mf_flow_intensity | verified_engineerable | C (post-merge, daily amount) | YES |
| 3 | C005 | limit_space_compression | needs_formula_correction | C+ (daily close + raw up/down_limit) | NO -- implied_close != actual close |
| 4 | C006 | limit_approach_velocity | needs_formula_correction | C+ (daily close + raw up_limit, .diff()) | NO -- depends on C005 |
| 5 | C009 | main_force_divergence | verified_engineerable | A (pure tushare, 1 line) | YES |
| 6 | C008 | seal_strength_proxy | needs_formula_correction | C+ (depends on C005 correction) | NO -- depends on C005 |
| 7 | C011 | auction_open_vwap_ratio | existing_engineered | D (already exists) | YES |
| 8 | C010 | float_relative_impact | verified_engineerable | C (post-merge, daily volume) | YES |
|  |  |  | **5/8 ready, 3/8 need engineering** |  |  |

# Factor Ablation Plan — 2026-05-03

> Status: **draft plan only** — no training, no probe execution, no config changes
> Baseline: frozen artifact `gpu_probe_20260501T155956Z_d64e3464` (expanded 307/260 selected)
> Diagnostic source: `docs/factor_quality_diagnostic_20260503.md`

---

## 0. Invalidated Runs

The following runs were produced by accidental script execution and **must be ignored**:

- `gpu_probe_20260503T111817Z_51301ae4` — mistaken family ablation, seen_research scope
- `gpu_probe_20260503T112324Z_140a0dce` — mistaken family ablation, seen_research scope

Do **not** read `gpu_probe_latest.json` as a valid conclusion — it may point to one of the above.
Any future ablation must compare against the frozen baseline artifact, not these runs.

---

## 1. Candidate Groups

### 1A. Research Daily Clean Set (39 base columns)

Source: `GPU_PROBE_RESEARCH_FACTOR_COLUMNS` (47 base), minus exclusions below.

**Excluded — near-constant (nonzero < 1%)**:

| Column | Nonzero% | Reason |
|--------|----------|--------|
| `seal_rate_80_threshold` | 0.09% | binary signal fires < 1 in 1000 rows |
| `no_theme_rotation_mode` | 0.93% | near-constant |
| `money_effect_sector_rotation` | 0.78% | near-constant |
| `mid_cap_trap_risk` | 0.89% | near-constant |
| `bet_decline_exhaustion` | 0.44% | near-constant |
| `one_day_trip_risk_proxy` | 0.59% | near-constant |

**Excluded — redundant with selected 260 (|r| >= 0.90)**:

| Column | Correlated With | r |
|--------|----------------|---|
| `market_limit_down_rate` | `market_limit_down_count` (selected) | 1.0000 |
| `market_limit_seal_success_rate` | `market_broken_board_rate` (selected) | -1.0000 |

**Remaining 39 clean columns**:

```
market_one_word_board_count        market_high_leader_crash_count
cycle_day_count                    divergence_day_count
buy_sell_cycle_phase               liquidity_exhaustion_signal
market_split_signal                quant_climax_type
vol_stagnation_signal              bull_rotation_upgrade
theme_capacity_score               market_amount_ratio_20
market_amount_percentile_60        volume_is_king_signal
ground_volume_risk                 post_decline_transition
decline_stabilize_signal           weak_friday_risk
prev_top20_chase_return            prev_top20_chase_win_rate
prev_bottom20_rebound_return       money_effect_spread_20
collapse_warning_signal            bullish_pivot_recognition
limit_premium_failure_signal       bad_sentiment_no_sweep
high_leader_crash_sentiment_collapse
full_position_trigger              late_cycle_position_cap
bear_position_reduction            strong_market_regime
weak_market_oversold_regime        bull_hotspot_bear_oversold
shrink_after_rotten                explosive_vol_next_weak
break_node_new_dragon              dragon_replace_signal
buy_rise_divergence                board_keep_break_signal
```

Properties:
- Market-level daily factors (same value for all stocks on a given date)
- 0% NaN, 100% date coverage, zero external dependency
- Already computed in research feature cache
- 39 base + 39 `_available` = 78 additional columns

### 1B. Tushare Tier 1 Clean Set (14 base columns)

Source: high-coverage tushare sub-sources (804 daily cache files, 2023-01-03 ~ 2026-04-30).

| Sub-Source | Columns | Sample Stocks | Coverage Note |
|-----------|---------|---------------|---------------|
| moneyflow | 5: `net_mf_amount`, `lg_buy_sell_ratio`, `elg_buy_sell_ratio`, `mf_strength`, `sm_sell_pressure` | 5,087 | ~100% stock-day |
| daily_basic | 2: `volume_ratio`, `free_share` | 5,339 | ~100% stock-day |
| stk_limit | 3: `up_limit_distance`, `down_limit_distance`, `limit_range` | 6,867 | ~100% stock-day |
| stk_auction | 4: `auction_open_vwap_ratio`, `auction_open_vol`, `auction_close_vwap_ratio`, `auction_close_vol` | 5,238/5,566 | ~100% stock-day |

Properties:
- 0% NaN in feature cache, 0 columns flagged near-constant
- 0 redundant with selected 260 (no |r| >= 0.90)
- Per-stock cross-sectional factors (unlike research daily which is market-level)
- 14 base + 14 `_available` = 28 additional columns

### 1C. Explicitly Excluded

| Family | Reason |
|--------|--------|
| `stk_holdernumber` | `tushare_holder_num` and `tushare_holder_num_delta_pct` are all-zero in feature cache (data not reaching builder). Do not include until root cause fixed. |
| `stk_mins_5` | 18% stock coverage (330/3195 stocks), only 2026-02 ~ 2026-04. Wait for full pull. |
| `limit_pool` | 19% date coverage, 49/50 near-constant in prior research run. Not ready. |
| `intraday` | Same as stk_mins_5 — insufficient coverage. |
| `research_symbol_proxy` | 0 selected in all prior research runs. |
| `research_cross_section` | 0 selected in all prior research runs. |

---

## 2. Experiment Matrix

All experiments are **seen_research** scope (lockbox_role=`seen_research`, 2026-01 ~ 2026-04 test window). None can produce `passed` status.

### Experiment A: Research Daily Clean (39 columns)

| Parameter | Value |
|-----------|-------|
| Name | `research_daily_clean_39` |
| feature_set | `expanded` (307 base) + 39 research daily clean = **346 input features** |
| exclude_feature_prefix | `["cross_"]` (unchanged) |
| max_selected_features | 260 (unchanged) |
| feature_selection_method | `stable_tail` |
| candidate_family | `all` |
| selector_coverage_weight | 0.02 |
| sample_filter | identical to frozen config |
| lockbox_role | `seen_research` |
| Expected input cols | 346 base + 346 `_available` + meta = ~700+ total |
| Comparison baseline | frozen artifact `d64e3464` (HC acc 82.93%, Wilson 82.12%, count 8,573) |
| Risk | Market-level factors are identical across stocks on same date — may inflate apparent importance via date-level leakage in tree models. Watch for date-bucket stability degradation. |
| Success criterion | HC accuracy >= baseline 82.93% AND Wilson >= 82.12% AND date-bucket std not worse than 11.8% AND no new single-day > 20% contribution |
| seen_research only | **YES** — result informs but cannot replace forward final_unseen |

### Experiment B: Tushare Tier 1 (14 columns)

| Parameter | Value |
|-----------|-------|
| Name | `tushare_tier1_14` |
| feature_set | `expanded` (307 base) + 14 tushare tier 1 = **321 input features** |
| exclude_feature_prefix | `["cross_"]` (unchanged) |
| max_selected_features | 260 (unchanged) |
| feature_selection_method | `stable_tail` |
| candidate_family | `all` |
| selector_coverage_weight | 0.02 |
| sample_filter | identical to frozen config |
| lockbox_role | `seen_research` |
| Expected input cols | 321 base + 321 `_available` + meta = ~650+ total |
| Comparison baseline | frozen artifact `d64e3464` |
| Risk | Several tushare sub-sources have sparse nonzero rates in feature cache (e.g., limit_list_d ~8%). Stable_tail may eliminate most of them. If few survive selection, the ablation is uninformative — check selected count from each sub-source. |
| Success criterion | same as Experiment A |
| seen_research only | **YES** |

### Experiment C: Combined (Research Daily + Tushare Tier 1)

| Parameter | Value |
|-----------|-------|
| Name | `research_daily_tushare_t1_combined` |
| feature_set | `expanded` (307) + 39 research daily + 14 tushare tier 1 = **360 input features** |
| exclude_feature_prefix | `["cross_"]` |
| max_selected_features | 260 (unchanged) |
| feature_selection_method | `stable_tail` |
| candidate_family | `all` |
| selector_coverage_weight | 0.02 |
| sample_filter | identical to frozen config |
| lockbox_role | `seen_research` |
| Expected input cols | 360 base + 360 `_available` + meta = ~730+ total |
| Comparison baseline | frozen artifact `d64e3464` AND experiments A and B individually |
| Risk | Combined pool exceeds max_selected=260 more aggressively. If new features crowd out proven core features, HC accuracy may drop. Compare selected feature overlap with baseline to detect displacement. |
| Success criterion | same as Experiment A, plus: improvement must exceed better of A or B alone (otherwise prefer simpler config) |
| seen_research only | **YES** |

---

## 3. Execution Order and Dependencies

```
Experiment A (research_daily_clean_39)
    |
    +---> if improved: proceed to C
    |
Experiment B (tushare_tier1_14)       [can run in parallel with A]
    |
    +---> if improved: proceed to C
    |
Experiment C (combined)               [only if A or B shows improvement]
```

- A and B are independent and can run in parallel.
- C depends on A and B results — only run if at least one shows improvement.
- If neither A nor B improves over baseline, do not run C. Conclude that the current expanded 260 is optimal within the seen_research window.

---

## 4. Acceptance Criteria (per experiment)

Each experiment report must include:

| Metric | Threshold | Source |
|--------|-----------|--------|
| HC accuracy | >= frozen baseline (82.93%) | test set high-confidence subset |
| Wilson 95% lower | >= frozen baseline (82.12%) | same |
| HC count | report only (cannot reach 10,000 in 4-month window) | same |
| HC coverage | >= 10% | same |
| Brier score | < baseline Brier | same |
| Date-bucket stability | std <= 11.8%, no single day > 20% | date-bucket diagnostic |
| Feature displacement | report how many of baseline's selected 260 were dropped | feature_selection output |

**None of these experiments can produce `passed` status.** They are diagnostic-only.

If an experiment passes all seen_research criteria, the decision to update frozen config is deferred to the forward final_unseen phase — per the forward_runbook.md discipline, no backward config changes from seen_research results.

---

## 5. What This Plan Does NOT Do

- Does NOT execute any `run_gpu_next_day_probe` call
- Does NOT modify `docs/frozen_forward_config.json`
- Does NOT read or cite results from `gpu_probe_20260503T111817Z_51301ae4` or `gpu_probe_20260503T112324Z_140a0dce`
- Does NOT write or run ablation scripts
- Does NOT pull/refresh market data
- Does NOT commit or push

---

## 6. Open Questions (for user decision before execution)

1. **max_selected_features**: Keep at 260 for all experiments, or increase to 300 for Experiment C to give new features room without displacing core?
2. **Tushare sparse sub-sources**: In Experiment B, limit_list_d/top_list_inst columns have ~8% nonzero. Should we pre-filter these to moneyflow + daily_basic + stk_limit + stk_auction only (removing the 6 sparse-event columns)?
3. **Near-constant threshold**: Current cutoff is nonzero < 1%. Some research daily columns like `ground_volume_risk` (1.78%), `weak_friday_risk` (2.14%), `shrink_after_rotten` (2.52%) are low but above 1%. Should we raise the cutoff to 3% and exclude these as well?
4. **Execution timing**: Run all experiments in the current session, or defer to a dedicated ablation session?

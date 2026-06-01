# Family Ablation Summary — 2026-05-03 (Accidental Runs)

> Status: **seen_research diagnostic only** — accidental execution, not pre-approved
> Source: `scripts/run_family_ablation_probe.py` (PID 49708, already terminated)
> Frozen config: **unchanged** (`gpu_probe_20260501T155956Z_d64e3464`)

---

## 0. Invalidated Runs

| run_id | Reason |
|--------|--------|
| `gpu_probe_20260503T111817Z_51301ae4` | Pre-ablation mistaken execution, ignore |
| `gpu_probe_20260503T112324Z_140a0dce` | Pre-ablation mistaken execution, ignore |

**`gpu_probe_latest.json` must not be cited as a valid conclusion** — it may point to one of the above or to the ablation runs below, none of which were pre-approved.

---

## 1. Comparison Table

| | baseline_expanded_no_cross | expanded_plus_research_daily | tushare_tier1_available |
|---|---|---|---|
| **run_id** | `1b272829` | `058b885e` | **DID NOT COMPLETE** |
| **variant status** | control group | dirty/full research_daily diagnostic | killed at frame 2750/3063 |
| **feature_set** | expanded | expanded | research |
| **input features** | 352 | 446 (352 + 94) | target 390 (370 + 20) |
| **family added** | — | `GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES` full 94 | moneyflow(5) + daily_basic(2) + stk_limit(3) = 10 base + 10 avail |
| **family_in** | 0 | 94 | 20 (never loaded) |
| **family_sel** | 0 | 32 | — |
| **selected** | 260 | 260 | — |
| **test_rows** | 120,000 | 120,000 | — |
| **HC accuracy** | 75.40% | 74.30% | — |
| **Wilson 95 lower** | 74.74% | 73.66% | — |
| **HC count** | 16,206 | 18,268 | — |
| **HC coverage** | 13.51% | 15.22% | — |
| **HC Brier** | 0.1883 | 0.1962 | — |
| **All Brier** | 0.2254 | 0.2267 | — |
| **Baseline Brier** | 0.2304 | 0.2304 | — |
| **Date-bucket median** | 0.750 | 0.762 | — |
| **Date-bucket std** | 0.2109 | 0.1929 | — |

---

## 2. Annotations

### 2.1 baseline_expanded_no_cross (`1b272829`) — control group

- 352 input = expanded 370 − 18 cross_ features. Same feature pool as frozen artifact `d64e3464`.
- Uses 120k test rows (frozen artifact used 57k). Metrics are **not directly comparable** with the frozen artifact's HC acc 82.93% / Wilson 82.12% — the 120k pool includes a wider date range and more marginal samples.
- HC accuracy 75.40% / Wilson 74.74% establishes the **120k-setting baseline** for this comparison only.

### 2.2 expanded_plus_research_daily (`058b885e`) — dirty/full diagnostic

- Added **full** `GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES` (94 columns = 47 base + 47 _available).
- This is **NOT** the `Research Daily clean 39` from `factor_ablation_plan_20260503.md`. It includes:
  - 6 near-constant columns (`seal_rate_80_threshold`, `no_theme_rotation_mode`, `money_effect_sector_rotation`, `mid_cap_trap_risk`, `bet_decline_exhaustion`, `one_day_trip_risk_proxy`)
  - 2 columns redundant with selected 260 (`market_limit_down_rate` r=1.0 with `market_limit_down_count`; `market_limit_seal_success_rate` r=-1.0 with `market_broken_board_rate`)
- Of the 94 added to pool, **32 survived** stable_tail selection, displacing 32 baseline features.
- **Result: worse.** HC accuracy dropped 1.1pp (75.40% → 74.30%), Wilson dropped 1.1pp, HC Brier worsened (0.1883 → 0.1962).
- HC count increased (+2,062) and coverage improved (+1.7pp), but this is a precision-for-coverage tradeoff — the model became less selective, not better.
- Date-bucket std improved (0.211 → 0.193), but this likely reflects the diluted confidence threshold rather than genuine stability gain.

**Displaced baseline features (32 dropped):**
```
amount_z_lag_2        amount_z_lag_3       big_up
breakdown_20          breakout_20          close_pos_lag_1
consolidation_breakout_20  cs_active_volatility_rank  cs_range_rank
cs_turnover_rank      emotion_phase_divergence   failed_breakout_20
first_divergence_flag limit_down_bounce_pct     limit_down_like
market_active_amount_sum  market_active_turnover_mean  near_limit_close
overnight_abs_rank_20 range_lag_0              range_pct
rel_ret_1_to_market   risk_long_upper_after_big_up  sector_climax_signal
sector_divergence     tgb_pullback_health      turnover_mean_5
turnover_sum_5        upper_shadow_x_volume_z  volume_z_lag_2
volume_z_lag_3        volume_z_lag_4
```

Several displaced features (`range_pct`, `limit_down_bounce_pct`, `sector_climax_signal`, `first_divergence_flag`) are likely informative. The full-94 inclusion may be poisoning selection.

### 2.3 tushare_tier1_available — incomplete

- Configured as `feature_set=research` (370 features) + 20 tushare extras = 390 pool.
- Only included moneyflow(5) + daily_basic(2) + stk_limit(3) = **10 base + 10 _available = 20 columns**.
- **Missing stk_auction(4)** despite raw cache having 804 parquets each for stk_auction_o and stk_auction_c. The ablation script excluded stk_auction with comment "0 cache parquets" which was **incorrect** — script was written before verifying the actual cache state.
- Feature cache missed (no prior run with this exact feature combination), so it had to reload all 3,063 stocks from scratch. Killed at frame 2,750/3,063 — no artifact produced.

---

## 3. Conclusions

### What is valid from these runs

| Finding | Valid? | Reason |
|---------|--------|--------|
| 120k baseline HC ~75.4% / Wilson ~74.7% | Informational | Establishes 120k-setting reference, not comparable to frozen 57k metrics |
| Full 94 research_daily hurts HC accuracy | **Directional signal** | Consistent with hypothesis that near-constant + redundant columns + market-level dilution degrade selection |
| Full 94 research_daily increases HC count | Informational | Precision-for-coverage tradeoff, not an improvement |
| Tushare tier1 effect | **Unknown** | Run did not complete |

### What is NOT valid

- These runs cannot update frozen config status.
- `gpu_probe_latest.json` is not a valid conclusion source.
- The research_daily result does NOT invalidate the clean-39 plan — it only shows the dirty-94 version is harmful.

---

## 4. Next Step Recommendation

Pending user approval before any execution:

### 4A. Re-run Research Daily Clean 39 (priority)

The dirty-94 result suggests the 6 near-constant + 2 redundant columns hurt selection. The clean-39 plan (from `factor_ablation_plan_20260503.md` Experiment A) removes these 8 columns and is still the correct next test. The dirty result does not substitute for it.

### 4B. Re-run Tushare Tier1 Complete 14

The ablation script only included 10 base columns (missing stk_auction 4). The correct Tier 1 set is moneyflow(5) + daily_basic(2) + stk_limit(3) + stk_auction(4) = 14 base + 14 _available = 28. stk_auction has 804 parquets confirmed. This needs a corrected run per `factor_ablation_plan_20260503.md` Experiment B.

### 4C. holdernumber must remain excluded

`tushare_holder_num` and `tushare_holder_num_delta_pct` are all-zero in the feature cache despite 804 raw cache files. Root cause is likely the builder not mapping quarterly holdernumber data to daily rows. Do not include until fixed.

### 4D. Combined (Experiment C) deferred

Only run after both 4A and 4B complete, and only if at least one shows improvement over baseline.

**No action will be taken until you confirm.**

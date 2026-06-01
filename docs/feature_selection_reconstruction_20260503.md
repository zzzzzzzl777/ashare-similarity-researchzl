# Feature Selection Reconstruction (2026-05-03)

This note reconstructs the current short-term factor line from runtime artifacts, code constants, and the first-batch engineering shortlist on the desktop.

## Sources

- Runtime latest pointer: `E:\ashare_similarity_runtime\data\reports\prediction\gpu_probe_latest.json`
- Runtime frozen shortlist: `E:\ashare_similarity_runtime\data\reports\prediction\frozen_candidates_20260503.json`
- Runtime ledger: `E:\ashare_similarity_runtime\data\reports\prediction\lockbox_ledger.jsonl`
- Runtime artifacts:
  - `gpu_probe_20260503T093827Z_594a3d7d`
  - `gpu_probe_20260502T163051Z_0b30f2d5`
  - `gpu_probe_20260502T171417Z_b6ddb3f6`
- Code:
  - `src/ashare_similarity/prediction/gpu_probe.py`
  - `src/ashare_similarity/prediction/free_data_factors.py`
  - `src/ashare_similarity/prediction/tgb_daily_factors.py`
  - `src/ashare_similarity/prediction/ths_sector_factors.py`
  - `src/ashare_similarity/prediction/intraday_factors.py`
- Desktop shortlist outputs:
  - `C:\Users\zzzzzzl\Desktop\短线因子工程落地优先级清单.md`
  - `C:\Users\zzzzzzl\Desktop\短线因子现有特征覆盖审计.md`

## 1. Current Runtime State

The current latest probe pointer is:

- `run_id`: `gpu_probe_20260503T093827Z_594a3d7d`
- `generated_at`: `2026-05-03T09:38:27+00:00`
- `lockbox_role`: `seen_research`
- `passed`: `false`
- `final_acceptance_eligible`: `false`
- `code_hash`: `d1b736087f5ece0c`
- `feature_hash`: `a97cd5fe149d26c5`
- `data_hash`: `39bc41eea8cf26ea`
- `split_hash`: `623802cb49b1082b`

This run is **not** one of the two frozen candidates in `frozen_candidates_20260503.json`.

Its runtime config and outcome are:

| Field | Value |
|---|---|
| `feature_set` | `expanded` |
| `candidate_family` | `all` |
| `max_selected_features` | `260` |
| `feature_selection_method` | `stable_tail` |
| `selector_coverage_weight` | `0.02` |
| `exclude_event_limit_up` | `true` |
| `lockbox_role` | `seen_research` |
| HC rows | `15,958` |
| HC coverage | `13.2983%` |
| HC accuracy | `75.4543%` |
| HC Wilson lower 95% | `74.7805%` |
| All-active accuracy | `64.1317%` |
| Conclusion | `research_only` |

Interpretation:

- The run clears HC accuracy and coverage.
- It **does not** clear the Wilson 95% lower bound gate.
- It is still `seen_research`, so it cannot be a formal pass even if the metric gates were met.

## 2. What The Code Currently Exposes

From the live code constants in `gpu_probe.py` and factor modules:

| Pool / Group | Count |
|---|---:|
| `expanded` feature pool | 370 |
| `research` feature pool | 790 |
| `research - expanded` | 420 |
| research symbol proxy columns | 40 |
| research cross-section proxy columns | 25 |
| Tushare factor columns | 46 |
| minute factor columns | 29 |
| limit-pool feature columns with `_available` flags | 96 |
| TGB stock columns | 8 |
| TGB market columns | 6 |
| THS sector columns | 6 |
| market emotion columns | 80 |
| board structure columns | 23 |

Important confirmation:

- The current `expanded` line is **not** the full `research` line.
- The latest selected 260 contains:
  - `0 / 40` research symbol proxy columns
  - `0 / 25` research cross-section proxy columns

So the current line is still the stable/expanded pool, not a research-pool sweep.

## 3. Composition Of The Latest 260

For `gpu_probe_20260503T093827Z_594a3d7d`, the selected 260 break down as:

| Source family | Selected count |
|---|---:|
| core non-external features | 198 |
| `market_emotion_daily_proxy` | 38 |
| `board_structure_daily_proxy` | 7 |
| `tgb_stock_daily` | 6 |
| `tgb_market_regime` | 5 |
| `ths_sector_daily` | 6 |
| `cross_market_returns` | 0 |
| `_available` flags | 6 |

Key takeaways:

- `cross_` features are fully absent in the latest 260.
- TGB and THS sector families are now real contributors inside the stable line.
- Market emotion remains the single biggest external contributor.

## 4. Relation To The Frozen Candidates

The frozen shortlist currently recorded in runtime is:

| Tag | Run | Family | Selected | HC accuracy | HC Wilson | HC coverage | HC count |
|---|---|---|---:|---:|---:|---:|---:|
| `accuracy_priority` | `gpu_probe_20260502T163051Z_0b30f2d5` | `all` | 299 | 81.2412% | 80.5541% | 10.6217% | 12,746 |
| `coverage_priority` | `gpu_probe_20260502T171417Z_b6ddb3f6` | `torch` | 299 | 76.1695% | 75.4695% | 12.0958% | 14,515 |

Both are still `seen_research` only.

### 4a. Latest 260 vs frozen 299 torch

`latest260_all` is a **strict subset** of `frozen299_torch`:

- latest-only: `0`
- removed from frozen299_torch: `39`

Removed names:

```text
board_count
board_promoted_today
board_vs_max
cross_sh000001_ret_1
cross_sh000001_ret_3
cross_sh000001_ret_5
cross_sz399001_ret_1
cross_sz399001_ret_3
cross_sz399001_ret_5
cross_sz399006_ret_1
cross_sz399006_ret_3
cross_sz399006_ret_5
emotion_climax_next_day_risk_available
emotion_phase_ebbing
emotion_phase_ice
emotion_phase_upswing
emotion_phase_upswing_available
is_first_board
is_high_board
is_second_board
is_space_board
limit_seal_quality_proxy
limit_up_double_shot
limit_up_like
limit_up_streak
limit_up_turnover
market_board_promotion_rate_high_available
market_broken_board_rate_1st_available
market_echelon_completeness_available
market_emotion_score_available
market_limit_up_count_available
market_new_low_20_count_available
one_word_board_proxy
prev_failed_limit_up_return_available
same_height_failure_pressure_available
t_shape_board_proxy
tgb_board_height_vs_max
tgb_board_quality_trend
tgb_leader_break_signal
```

Interpretation:

- The current 260 prunes out leftover `cross_` returns, several board-form flags, several availability flags, and three older TGB features.
- It keeps the stronger THS/TGB subset while tightening the pool.

### 4b. Latest 260 vs frozen 299 all

Compared with the older `all` frozen run:

- latest-only: `23`
- removed from frozen299_all: `62`

New names in latest260 relative to frozen299_all:

```text
sector_climax_signal
sector_climax_signal_available
sector_divergence
sector_divergence_available
sector_duration_days
sector_duration_days_available
sector_limit_up_count
sector_limit_up_count_available
sector_pct_change_best
sector_pct_change_best_available
sector_strength_rank
sector_strength_rank_available
tgb_eod_rush_risk
tgb_ma_alignment_score
tgb_ma_divergence_5
tgb_market_max_height
tgb_mid_collapse_rate
tgb_new_first_board_count
tgb_nuclear_button_count
tgb_pullback_health
tgb_retreat_intensity
tgb_volume_buildup_score
tgb_zhaban_recovery_score
```

Interpretation:

- The stable line has clearly migrated away from the old cross-market-heavy 299-all mix.
- The net change is: **remove `cross_` and stale availability baggage; add THS sector and newer TGB daily/regime structure.**

## 5. Current Working Tree Drift Matters

The working tree is ahead of the frozen docs in a few important ways:

- `gpu_probe.py` now has an explicit `exclude_event_limit_up` path that drops rows with `limit_up_like > 0.5` before split/training.
- `gpu_probe.py` now writes `test_predictions.parquet` for each run.
- `pull_tushare_stk_mins.py` now uses adaptive backoff when a segment round makes no progress.

That explains why the newest runtime pointer has:

- a new `code_hash`
- a new `feature_hash`
- a new `data_hash`

So we should treat `gpu_probe_20260503T093827Z_594a3d7d` as a **post-freeze diagnostic branch state**, not as a replacement for the documented frozen forward configuration.

## 6. First-Batch 50 Candidate Crosswalk

The desktop engineering shortlist (`短线因子工程落地优先级清单.md`) contains 50 first-batch candidates.

Exact-name overlap with current code pools:

| Pool | Exact overlap count |
|---|---:|
| `expanded370` | 0 |
| `research790` | 1 |
| latest selected 260 | 0 |

The only exact-name overlap is:

- `low_position_big_yang` -> already present in `research790`, but **not** in `expanded370` and **not** in the latest selected 260.

Cluster split of the first-batch 50:

| Cluster | Count |
|---|---:|
| `premium_signal` | 5 |
| `other` | 8 |
| `seat_lhb` | 8 |
| `board_structure` | 3 |
| `sector_momentum` | 7 |
| `emotion_cycle` | 7 |
| `margin_northbound` | 6 |
| `volume_pattern` | 5 |
| `fundamental` | 1 |

Suggested landing-module split:

| Suggested location | Count |
|---|---:|
| `new module or free_data_factors.py` | 8 |
| `free_data_factors.py (_build_lhb_factors)` | 8 |
| `ths_sector_factors.py (build_ths_sector_factors)` | 7 |
| `free_data_factors.py (build_market_emotion_factor)` | 7 |
| `free_data_factors.py (_build_margin_factors / _build_hk_hold_factors)` | 6 |
| `free_data_factors.py or limit_pool_snapshots.py` | 5 |
| `free_data_factors.py or tgb_daily_factors.py` | 5 |
| `free_data_factors.py (build_board_structure_factor) or tgb_daily_factors.py` | 3 |
| `free_data_factors.py (_build_daily_basic_factors)` | 1 |

Interpretation:

- `seat_lhb` + `margin_northbound` = `14/50` candidates naturally belong to Tushare/LHB/northbound style factor builders. Those are **research-side additions**, not current stable-forward features.
- `sector_momentum` = `7/50` candidates point to `ths_sector_factors.py`, and the current latest 260 already uses **all 6 existing THS sector features**.
- `emotion_cycle` = `7/50` candidates point to `build_market_emotion_factor`, and the latest 260 already uses **38** market emotion features.
- `premium_signal` and part of `board_structure` point toward limit-pool / executable-premium logic, which fits the newer executable-only direction but is **not yet the stable selected set**.

## 7. Bottom Line

If we restate the line in plain language:

1. The live probe line is still an `expanded` stable pool, not a `research` pool.
2. The latest 260 is effectively a tightened subset of the stronger 299-torch configuration.
3. The tightening mainly removed `cross_`, board-form flags, and availability baggage.
4. THS sector and TGB factors are now inside the stable line; research proxy factors are still outside it.
5. The first-batch 50 desktop shortlist is mostly **not implemented yet** in code:
   - exact overlap with `expanded370`: `0`
   - exact overlap with latest selected 260: `0`
   - exact overlap with `research790`: only `low_position_big_yang`
6. So the shortlist should be treated as a **next engineering queue**, not as something already reflected in the current probe artifacts.

## 8. Practical Next Step

The safest continuation path is:

- keep the frozen forward configuration separate
- treat the current 2026-05-03 probe as post-freeze diagnostic drift
- route the first-batch 50 into research-first implementation buckets
- especially separate:
  - Tushare / LHB / northbound candidates -> research only
  - THS sector / emotion-cycle candidates -> family already present, but new exact factors still need evidence
  - executable premium / limit-pool candidates -> promising, but must stay executable-only and should not be silently merged into frozen forward config

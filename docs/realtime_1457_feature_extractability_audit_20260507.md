# 14:57 Feature Extractability Audit - Current G Bundle

**Date:** 2026-05-07
**Bundle:** `E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260505T113406Z_bb25159b\model_bundle.pt`

## Executive Conclusion

Current saved G bundle is **not strict_1457 executable yet**. The blocking issue is data semantics, not speed. The selected feature set contains 7 same-day Tushare moneyflow split features that cannot be reconstructed exactly from OHLCV/minute bars. T-1 proxy is invalid for strict live trading.

## Selected Feature Counts

| Category | Count | Meaning |
|---|---:|---|
| `asof_1457_computable_or_approximable_not_full_day_equivalent` | 201 | Can be computed from 14:57 snapshot/minute-as-of data, but not identical to full-day training value. |
| `strict_exact_or_metadata_pre1457` | 52 | Known before/at 14:57 without using final close/volume/amount, or availability metadata. |
| `strict_unavailable_requires_same_semantic_realtime_moneyflow` | 7 | Needs same-day same-semantic realtime moneyflow split; cannot be derived from OHLCV/minute bars. |

## All Bundle Feature Counts

| Category | Count |
|---|---:|
| `asof_1457_computable_or_approximable_not_full_day_equivalent` | 233 |
| `strict_exact_or_metadata_pre1457` | 136 |
| `strict_unavailable_requires_same_semantic_realtime_moneyflow` | 7 |

## Strict Unavailable Selected Features

| Feature | Meaning | Why unavailable at 14:57 | Required action |
|---|---|---|---|
| `tushare_net_mf_amount` | same-day net money flow | Needs same-semantic intraday moneyflow. OHLCV/minute bars cannot reconstruct it. push2 f62, if stable, is only a rough net-flow proxy and lacks split buckets. | Need same-semantic realtime source, or retrain without these columns / with as-of proxy factors. |
| `tushare_lg_buy_sell_ratio` | large-order buy/sell ratio | Needs same-day buy_lg_amount and sell_lg_amount split data. Minute bars cannot reconstruct order-size buckets. | Need same-semantic realtime source, or retrain without these columns / with as-of proxy factors. |
| `tushare_elg_buy_sell_ratio` | extra-large-order buy/sell ratio | Needs same-day buy_elg_amount and sell_elg_amount split data. OHLCV cannot reconstruct it. | Need same-semantic realtime source, or retrain without these columns / with as-of proxy factors. |
| `tushare_mf_strength` | large/extra-large moneyflow strength | Derived from split buy/sell moneyflow buckets; unavailable without same-semantic split source. | Need same-semantic realtime source, or retrain without these columns / with as-of proxy factors. |
| `tushare_sm_sell_pressure` | small-order selling pressure | Needs same-day sell_sm_amount and buy_sm_amount split data. Cannot be inferred exactly from OHLCV. | Need same-semantic realtime source, or retrain without these columns / with as-of proxy factors. |
| `tushare_main_force_divergence` | main-force divergence | Derived from large and extra-large buy/sell ratios; depends on split source. | Need same-semantic realtime source, or retrain without these columns / with as-of proxy factors. |
| `tushare_ff_adjusted_flow` | free-float adjusted moneyflow | Numerator depends on net_mf_amount. Without same-day net flow it cannot be exact. | Need same-semantic realtime source, or retrain without these columns / with as-of proxy factors. |

## Source Group Counts In Selected Features

| Source group | Count | 14:57 handling |
|---|---:|---|
| `symbol_ohlcv_rolling_from_asof_bar` | 120 | Compute from 14:57 latest price, high/low, volume, amount; not full-day equivalent. |
| `market_emotion_board_structure` | 35 | Requires whole-market 14:57 aggregation; full-day equivalence must be replay-tested. |
| `cross_section_from_1457_universe` | 31 | Requires whole-universe 14:57 snapshot and same filters. |
| `historical_or_calendar` | 27 | Strictly available. |
| `technical_from_asof_ohlcv` | 14 | Compute from historical bars + synthetic 14:57 T-day bar. |
| `tgb_daily_context` | 11 | Approximate/as-of daily context; replay required. |
| `sector_context` | 11 | Requires fixed sector mapping and realtime universe aggregation. |
| `tushare_moneyflow_split` | 7 | Blocked for strict_1457 unless verified realtime same-semantic source exists. |
| `tushare_stk_limit_or_price_limit` | 3 | Computable using pre-known limit price + latest price. |
| `tushare_daily_basic_recomputable_from_volume` | 1 | Volume ratio can be recomputed from 14:57 cumulative volume and historical average; final 3-minute bias remains. |

## C133-C173 Registry 14:57 Status

These registry factors are not automatically valid for 14:57. Most are `T-day close` or `T-day 15:00` semantics and need an as-of rewrite before strict live execution.

| Factor | Name | Engineering status | Registry asof | 14:57 status |
|---|---|---|---|---|
| `C133` | last_30min_return | `existing_engineered` | T-day 15:00 (full day bars required) | `needs_asof_rewrite_for_strict_1457` |
| `C134` | first_15min_volume_concentration | `existing_engineered` | T-day 15:00 | `needs_asof_rewrite_for_strict_1457` |
| `C135` | vwap_deviation | `blocked_until_outlier_guard` | T-day 15:00 | `not_engineered_for_training_or_1457` |
| `C136` | intraday_volatility | `existing_engineered` | T-day 15:00 | `needs_asof_rewrite_for_strict_1457` |
| `C137` | up_volume_ratio | `existing_engineered` | T-day 15:00 | `needs_asof_rewrite_for_strict_1457` |
| `C138` | high_time_position | `existing_engineered` | T-day 15:00 | `needs_asof_rewrite_for_strict_1457` |
| `C139` | real_limit_up_premium_gap | `candidate` | T-day close (uses T-1 pool, T-day returns) | `not_engineered_for_training_or_1457` |
| `C140` | zbgc_sector_pressure | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C141` | prev_top20_chase_real | `candidate` | T-day close (uses T-1 rank, T-day returns) | `not_engineered_for_training_or_1457` |
| `C142` | theme_limit_density | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C143` | is_volume_sufficient | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C144` | leader_pull_effect | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C145` | theme_height_suppression | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C146` | support_one_word_count | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C147` | eruption_strength | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C148` | is_ground_sky | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C149` | seal_trend | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C150` | old_leader_decay | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C151` | anti_drop_strength | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C152` | multi_wave_count | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C153` | nuclear_ratio | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C154` | price_vs_cost | `existing_engineered` | T-day close | `post_close_or_full_day_semantics_need_asof_rewrite` |
| `C155` | cap_ratio | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C156` | abnormal_3d_deviation | `existing_engineered` | T-day close | `post_close_or_full_day_semantics_need_asof_rewrite` |
| `C157` | VOL_GAIN | `existing_engineered` | T-day close | `post_close_or_full_day_semantics_need_asof_rewrite` |
| `C158` | INV_t | `existing_engineered` | T-day close | `post_close_or_full_day_semantics_need_asof_rewrite` |
| `C159` | ASR | `existing_engineered` | T-day close | `post_close_or_full_day_semantics_need_asof_rewrite` |
| `C160` | chip_weight | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C161` | ILLIQ_classic | `existing_engineered` | T-day close | `post_close_or_full_day_semantics_need_asof_rewrite` |
| `C162` | ATO | `existing_engineered` | T-day close | `post_close_or_full_day_semantics_need_asof_rewrite` |
| `C163` | TAM | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C164` | new_leader_emerge | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C165` | need_second_seal | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C166` | late_seal_ratio | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C167` | early_seal_ratio | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C168` | vol_premium | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C169` | max_theme_weight | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C170` | hhi_theme_concentration | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C171` | new_high_strength | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C172` | recent_limit_frequency | `candidate` | T-day close | `not_engineered_for_training_or_1457` |
| `C173` | true_limit_up_ratio | `candidate` | T-day close | `not_engineered_for_training_or_1457` |

## Corrected Rule

- Do not classify T-1 moneyflow fill as strict available. It changes the input distribution and can collapse probabilities.
- Do not classify full-day 5-minute factors as strict 14:57 executable unless they are rewritten to use only bars ending no later than 14:57 and replay-tested.
- `approximated_1457` is useful for engineering diagnostics, but trading eligibility requires either strict as-of features or a model trained on the same approximated/as-of semantics.

## Output Files

- JSON: `E:\ashare_similarity_runtime\data\reports\prediction\realtime_1457_feature_extractability_audit_20260507.json`
- CSV: `C:\Users\zzzzzzl\Desktop\realtime_1457_selected_feature_extractability_20260507.csv`
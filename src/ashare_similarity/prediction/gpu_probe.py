from __future__ import annotations

import json
import hashlib
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.acceptance import AcceptanceThresholds, build_prediction_acceptance
from ashare_similarity.prediction.factor_cache_manager import merge_factor_frames
from ashare_similarity.prediction.free_data_factors import (
    BOARD_STRUCTURE_COLUMNS,
    MARKET_EMOTION_COLUMNS,
    build_board_structure_factor,
    build_cross_market_return_factor,
    build_market_emotion_factor,
)
from ashare_similarity.prediction.split_protocol import (
    SplitProtocolConfig,
    SplitProtocolError,
    purged_train_validation_split as _official_purged_train_validation_split,
)


MIN_GPU_PROBE_TARGET_ACCURACY = 0.75
DESIRED_GPU_PROBE_TEST_ROWS = 50_000
MIN_GPU_PROBE_TEST_ROWS = 1
MIN_GPU_PROBE_HIGH_CONFIDENCE_ROWS = 10_000
MIN_GPU_PROBE_HIGH_CONFIDENCE_COVERAGE = 0.10
MIN_GPU_PROBE_STATISTICAL_ROWS = 1_000
MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS = 200
MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE = MIN_GPU_PROBE_HIGH_CONFIDENCE_COVERAGE
MAX_GPU_PROBE_SELECTED_FEATURES = 299
GPU_PROBE_MARKET_INDEX_SYMBOLS: tuple[str, ...] = ("sh000001", "sz399001", "sz399006")
GPU_PROBE_CROSS_MARKET_FEATURES: tuple[str, ...] = tuple(
    f"cross_{symbol}_ret_{window}"
    for symbol in GPU_PROBE_MARKET_INDEX_SYMBOLS
    for window in (1, 3, 5)
)
GPU_PROBE_RESEARCH_FACTOR_COLUMNS: tuple[str, ...] = (
    "market_limit_down_rate",
    "market_one_word_board_count",
    "divergence_day_count",
    "buy_sell_cycle_phase",
    "liquidity_exhaustion_signal",
    "market_split_signal",
    "quant_climax_type",
    "vol_stagnation_signal",
    "bull_rotation_upgrade",
    "theme_capacity_score",
    "market_amount_ratio_20",
    "market_amount_percentile_60",
    "volume_is_king_signal",
    "ground_volume_risk",
    "post_decline_transition",
    "decline_stabilize_signal",
    "weak_friday_risk",
    "prev_top20_chase_return",
    "prev_top20_chase_win_rate",
    "prev_bottom20_rebound_return",
    "money_effect_spread_20",
    "collapse_warning_signal",
    "shrink_after_rotten",
    "explosive_vol_next_weak",
    "break_node_new_dragon",
    "dragon_replace_signal",
    "mid_cap_trap_risk",
    "buy_rise_divergence",
    "bet_decline_exhaustion",
    "board_keep_break_signal",
    "one_day_trip_risk_proxy",
)
GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS: tuple[str, ...] = (
    "limit_up_freq_60",
    "near_limit_freq_60",
    "failed_limit_freq_60",
    "active_turnover_freq_60",
    "stock_personality_score",
    "first_board_entry",
    "second_board_entry",
    "new_high_board",
    "new_high_breakout_quality",
    "weak_to_strong_daily",
    "low_suck_reversal_proxy",
    "board_failure_repair",
    "monster_acceleration",
    "recognizable_backup",
    "highlight_score",
    "former_leader_memory_120",
    "former_leader_recall",
    "leader_faith_decay_60",
    "leader_faith_decay_pressure",
    "quant_oscillation_score_10",
    "oscillation_breakout_signal",
    "price_position_20",
    "price_position_60",
    "low_position_big_yang",
    "low_position_volume_reversal",
    "ma5_pullback_entry",
    "ma5_break_exit",
    "strong_rebound_from_20low",
    "high_position_climax_risk",
    "trend_pullback_health",
)
GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS: tuple[str, ...] = (
    "cs_price_rank",
    "cs_low_price_advantage",
    "cs_weak_market_focus",
    "cs_stock_leads_index_rebound",
    "cs_reversal_day_leader_quality",
    "cs_emotion_bull_signal",
    "cs_strong_rebound_not_bottom_risk",
    "money_effect_chase_alignment",
    "collapse_hot_stock_risk",
    "weak_rebound_money_effect",
)
GPU_PROBE_STABLE_MARKET_EMOTION_COLUMNS: tuple[str, ...] = tuple(
    column for column in MARKET_EMOTION_COLUMNS if column not in GPU_PROBE_RESEARCH_FACTOR_COLUMNS
)
GPU_PROBE_STABLE_BOARD_STRUCTURE_COLUMNS: tuple[str, ...] = tuple(
    column for column in BOARD_STRUCTURE_COLUMNS if column not in GPU_PROBE_RESEARCH_FACTOR_COLUMNS
)
GPU_PROBE_STABLE_DAILY_FACTOR_FEATURES: tuple[str, ...] = (
    *GPU_PROBE_STABLE_MARKET_EMOTION_COLUMNS,
    *(f"{column}_available" for column in GPU_PROBE_STABLE_MARKET_EMOTION_COLUMNS),
    *GPU_PROBE_STABLE_BOARD_STRUCTURE_COLUMNS,
    *(f"{column}_available" for column in GPU_PROBE_STABLE_BOARD_STRUCTURE_COLUMNS),
)
GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES: tuple[str, ...] = (
    *GPU_PROBE_RESEARCH_FACTOR_COLUMNS,
    *(f"{column}_available" for column in GPU_PROBE_RESEARCH_FACTOR_COLUMNS),
)
GPU_PROBE_ALL_DAILY_FACTOR_FEATURES: tuple[str, ...] = tuple(
    dict.fromkeys((*GPU_PROBE_STABLE_DAILY_FACTOR_FEATURES, *GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES))
)
GPU_PROBE_FREE_FACTOR_FEATURES: tuple[str, ...] = (
    *GPU_PROBE_STABLE_DAILY_FACTOR_FEATURES,
    *GPU_PROBE_CROSS_MARKET_FEATURES,
    *(f"{column}_available" for column in GPU_PROBE_CROSS_MARKET_FEATURES),
)
GPU_PROBE_RESEARCH_FREE_FACTOR_FEATURES: tuple[str, ...] = (
    *GPU_PROBE_FREE_FACTOR_FEATURES,
    *GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES,
)


GPU_PROBE_FEATURES: tuple[str, ...] = (
    "ret_1",
    "ret_2",
    "ret_3",
    "ret_5",
    "ret_10",
    "ret_20",
    "ret_accel_1_3",
    "ret_accel_3_10",
    "ret_mean_3",
    "ret_mean_5",
    "ret_mean_10",
    "ret_std_5",
    "ret_std_10",
    "ret_std_20",
    "volume_chg_1",
    "volume_chg_5",
    "volume_z_5",
    "volume_z_10",
    "volume_z_20",
    "amount_chg_1",
    "amount_chg_5",
    "amount_z_20",
    "turnover",
    "turnover_mean_3",
    "turnover_mean_5",
    "turnover_chg_1",
    "turnover_chg_5",
    "turnover_z_20",
    "turnover_to_max_20",
    "amount_to_max_20",
    "range_pct",
    "body_pct",
    "upper_shadow_pct",
    "lower_shadow_pct",
    "close_position",
    "gap_pct",
    "overnight_return",
    "intraday_return",
    "overnight_intraday_gap",
    "overnight_vs_intraday",
    "overnight_return_3d_mean",
    "overnight_return_5d_mean",
    "overnight_abs_rank_20",
    "reversal_intraday",
    "open_to_high_pct",
    "open_to_low_pct",
    "ma_gap_5",
    "ma_gap_10",
    "ma_gap_20",
    "mean_reversion_distance_5",
    "bollinger_position_20",
    "bollinger_width_20",
    "dist_high_10",
    "dist_high_20",
    "dist_low_10",
    "dist_low_20",
    "breakout_20",
    "breakdown_20",
    "limit_up_like",
    "limit_down_like",
    "failed_limit_up",
    "limit_down_bounce_pct",
    "limit_up_turnover",
    "one_word_board_proxy",
    "t_shape_board_proxy",
    "t_plus_1_selling_pressure",
    "board_space_height_5",
    "big_up",
    "big_down",
    "up_count_3",
    "up_count_5",
    "down_count_3",
    "down_count_5",
    "rsi_6",
    "rsi_14",
    "atr_14_pct",
    "obv_trend_5",
    "mfi_14",
    "macd_hist",
    "macd_signal",
    "kdj_k",
    "kdj_d",
    "kdj_j",
    "cci_20",
    "williams_r_14",
    "adx_14",
    "intraday_reversal_score",
    "limit_up_streak",
    "near_limit_close",
    "failed_breakout_10",
    "failed_breakout_20",
    "volume_price_divergence_5",
    "money_flow_fire",
    "hot_exhaustion_score",
    "limit_touch_fail_proxy",
    "limit_seal_quality_proxy",
    "gap_fill_ratio",
    "gap_continue_score",
    "trend_exhaustion_score",
    "climax_volume_ratio_60",
    "climax_amount_ratio_60",
    "volume_to_mean_20",
    "amount_to_mean_20",
    "daily_amount_300m_gate",
    "amount_300m_turnover_quality",
    "volume_price_match",
    "twenty_cm_board_risk",
    "amount_mean_3",
    "range_mean_3",
    "atr_mean_3",
    "short_phase_score_3",
    "short_phase_days_3",
    "turnover_sum_5",
    "turnover_sum_10",
    "turnover_sum_20",
    "turnover_accel_5_20",
    "limit_up_freq_60",
    "near_limit_freq_60",
    "failed_limit_freq_60",
    "active_turnover_freq_60",
    "stock_personality_score",
    "first_board_entry",
    "second_board_entry",
    "new_high_board",
    "new_high_breakout_quality",
    "weak_to_strong_daily",
    "low_suck_reversal_proxy",
    "board_failure_repair",
    "monster_acceleration",
    "recognizable_backup",
    "highlight_score",
    "former_leader_memory_120",
    "former_leader_recall",
    "leader_faith_decay_60",
    "leader_faith_decay_pressure",
    "quant_oscillation_score_10",
    "oscillation_breakout_signal",
    "new_high_volume_ratio_20",
    "consolidation_days_20",
    "consolidation_breakout_20",
    "reversal_with_volume",
    "cost_position_20",
    "cost_position_60",
    "profit_pressure_20",
    "profit_pressure_60",
    "risk_long_upper_after_big_up",
    "price_position_20",
    "price_position_60",
    "low_position_big_yang",
    "low_position_volume_reversal",
    "ma5_pullback_entry",
    "ma5_break_exit",
    "strong_rebound_from_20low",
    "high_position_climax_risk",
    "trend_pullback_health",
    "day_of_week_sin",
    "day_of_week_cos",
    "month_start_3",
    "month_end_3",
    "ret_lag_0",
    "ret_lag_1",
    "ret_lag_2",
    "ret_lag_3",
    "ret_lag_4",
    "ret_lag_5",
    "ret_lag_6",
    "ret_lag_7",
    "ret_lag_8",
    "ret_lag_9",
    "range_lag_0",
    "range_lag_1",
    "range_lag_2",
    "range_lag_3",
    "range_lag_4",
    "close_pos_lag_0",
    "close_pos_lag_1",
    "close_pos_lag_2",
    "close_pos_lag_3",
    "close_pos_lag_4",
    "volume_z_lag_0",
    "volume_z_lag_1",
    "volume_z_lag_2",
    "volume_z_lag_3",
    "volume_z_lag_4",
    "amount_z_lag_0",
    "amount_z_lag_1",
    "amount_z_lag_2",
    "amount_z_lag_3",
    "amount_z_lag_4",
    "ret1_x_volume_z5",
    "ret5_x_volume_z10",
    "ret1_x_close_position",
    "range_x_volume_z5",
    "turnover_x_range",
    "amount_z_x_range",
    "upper_shadow_x_volume_z",
    "lower_shadow_x_volume_z",
    "cs_ret_1_rank",
    "cs_turnover_rank",
    "cs_amount_z_rank",
    "cs_volume_z_rank",
    "cs_range_rank",
    "cs_volatility_rank",
    "cs_market_positive_rate",
    "cs_market_mean_ret_1",
    "cs_market_mean_range",
    "cs_short_pool_size_log",
    "cs_hot_concentration_rank",
    "cs_limit_up_rate",
    "cs_limit_down_rate",
    "cs_big_up_rate",
    "cs_big_down_rate",
    "cs_failed_limit_up_rate",
    "cs_near_limit_rate",
    "cs_hot_mean",
    "cs_hot_top_decile_mean",
    "cs_emotion_score",
    "rel_ret_1_to_market",
    "rel_range_to_market",
    "volume_z_x_cs_ret_rank",
    "close_pos_x_cs_range_rank",
    "market_cycle_failed_pressure",
    "market_cycle_broken_pressure",
    "market_cycle_seal_pressure",
    "market_monday_hot_new_high_risk",
    "market_hot_cycle_short_pressure",
    "chase_market_up_alignment",
    "strong_market_anti_drop",
    "weak_market_oversold_rebound",
    "second_board_leader_proxy",
    "seal80_second_board_quality",
    "bull_hotspot_bear_oversold_signal",
    "money_effect_chase_alignment",
    "collapse_hot_stock_risk",
    "weak_rebound_money_effect",
    *GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS,
    *GPU_PROBE_FREE_FACTOR_FEATURES,
)
GPU_PROBE_RESEARCH_FEATURES: tuple[str, ...] = (
    *GPU_PROBE_FEATURES,
    *GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES,
)
GPU_PROBE_ALL_FEATURES: tuple[str, ...] = tuple(dict.fromkeys((*GPU_PROBE_RESEARCH_FEATURES,)))
GPU_PROBE_CROSS_SECTION_FEATURES: tuple[str, ...] = tuple(
    name
    for name in GPU_PROBE_FEATURES
    if name.startswith("cs_")
    or name
    in {
        "rel_ret_1_to_market",
        "rel_range_to_market",
        "volume_z_x_cs_ret_rank",
        "close_pos_x_cs_range_rank",
        "market_cycle_failed_pressure",
        "market_cycle_broken_pressure",
        "market_cycle_seal_pressure",
        "market_monday_hot_new_high_risk",
        "market_hot_cycle_short_pressure",
        "chase_market_up_alignment",
        "strong_market_anti_drop",
        "weak_market_oversold_rebound",
        "second_board_leader_proxy",
        "seal80_second_board_quality",
        "bull_hotspot_bear_oversold_signal",
        "money_effect_chase_alignment",
        "collapse_hot_stock_risk",
        "weak_rebound_money_effect",
    }
)
GPU_PROBE_STABLE_FEATURES: tuple[str, ...] = tuple(
    name
    for name in GPU_PROBE_FEATURES
    if name not in GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS
    and name not in GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS
)
GPU_PROBE_BASE_FEATURES: tuple[str, ...] = tuple(
    name for name in GPU_PROBE_STABLE_FEATURES if name not in GPU_PROBE_CROSS_SECTION_FEATURES
)
GPU_PROBE_SYMBOL_FEATURES: tuple[str, ...] = tuple(
    name
    for name in GPU_PROBE_FEATURES
    if name not in GPU_PROBE_CROSS_SECTION_FEATURES and name not in GPU_PROBE_FREE_FACTOR_FEATURES
)
GPU_PROBE_LEGACY_FEATURES: tuple[str, ...] = tuple(
    name
    for name in GPU_PROBE_FEATURES
    if name
    in {
        "ret_1",
        "ret_2",
        "ret_3",
        "ret_5",
        "ret_10",
        "ret_20",
        "ret_accel_1_3",
        "ret_accel_3_10",
        "ret_mean_3",
        "ret_mean_5",
        "ret_mean_10",
        "ret_std_5",
        "ret_std_10",
        "ret_std_20",
        "volume_chg_1",
        "volume_chg_5",
        "volume_z_5",
        "volume_z_10",
        "volume_z_20",
        "amount_chg_1",
        "amount_chg_5",
        "amount_z_20",
        "turnover",
        "turnover_chg_1",
        "turnover_chg_5",
        "turnover_z_20",
        "turnover_to_max_20",
        "amount_to_max_20",
        "range_pct",
        "body_pct",
        "upper_shadow_pct",
        "lower_shadow_pct",
        "close_position",
        "gap_pct",
        "ma_gap_5",
        "ma_gap_10",
        "ma_gap_20",
        "dist_high_10",
        "dist_high_20",
        "dist_low_10",
        "dist_low_20",
        "breakout_20",
        "breakdown_20",
        "limit_up_like",
        "limit_down_like",
        "big_up",
        "big_down",
        "up_count_3",
        "up_count_5",
        "down_count_3",
        "down_count_5",
        "rsi_6",
        "rsi_14",
        "ret1_x_volume_z5",
        "ret5_x_volume_z10",
        "ret1_x_close_position",
        "range_x_volume_z5",
        "turnover_x_range",
        "amount_z_x_range",
        "upper_shadow_x_volume_z",
        "lower_shadow_x_volume_z",
        "cs_ret_1_rank",
        "cs_turnover_rank",
        "cs_amount_z_rank",
        "cs_volume_z_rank",
        "cs_range_rank",
        "cs_volatility_rank",
        "cs_market_positive_rate",
        "cs_market_mean_ret_1",
        "cs_market_mean_range",
        "cs_short_pool_size_log",
    }
)


@dataclass(slots=True)
class GpuProbeConfig:
    start: date
    train_end: date
    test_start: date
    end: date
    train_rows: int = 300_000
    test_rows: int = 50_000
    seed: int = 42
    max_symbols: int | None = None
    epochs: int = 160
    target_accuracy: float = 0.75
    validation_fraction: float = 0.20
    embargo_label_days: int = 1
    short_only: bool = True
    min_turnover: float = 3.0
    min_amount: float = 200_000_000.0
    min_volume_z: float = 1.0
    min_amount_z: float = 1.0
    min_range_pct: float = 3.0
    min_volatility_pct: float = 2.5
    min_abnormal_flags: int = 2
    min_phase_days_3: int = 2
    main_board_only: bool = True
    min_label_return_pct: float = 0.0
    feature_set: str = "expanded"
    max_selected_features: int = MAX_GPU_PROBE_SELECTED_FEATURES
    use_feature_cache: bool = True
    refresh_feature_cache: bool = False


def run_gpu_next_day_probe(store: LocalDataStore, config: GpuProbeConfig) -> dict[str, Any]:
    config_errors = _validate_config(config)
    if config_errors:
        return {
            "status": "invalid_config",
            "errors": config_errors,
            "minimum_target_accuracy": MIN_GPU_PROBE_TARGET_ACCURACY,
            "minimum_test_rows": MIN_GPU_PROBE_TEST_ROWS,
            "desired_test_rows": DESIRED_GPU_PROBE_TEST_ROWS,
        }

    try:
        import torch
    except Exception as exc:  # pragma: no cover - runtime dependency issue
        return {"status": "torch_unavailable", "error": str(exc)}

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    effective_target_accuracy = _effective_target_accuracy(config)
    effective_test_rows = _effective_required_test_rows(config)
    rng = np.random.default_rng(config.seed)
    context_symbols = [str(symbol).zfill(6) for symbol in store.list_cached_symbols("daily")]
    if config.main_board_only:
        context_symbols = [symbol for symbol in context_symbols if _is_main_board_symbol(symbol)]
    symbols = list(context_symbols)
    rng.shuffle(symbols)
    if config.max_symbols is not None:
        symbols = symbols[: max(0, int(config.max_symbols))]

    feature_cache = _feature_cache_descriptor(store, config, symbols=symbols, context_symbols=context_symbols)
    loader_diagnostics: dict[str, Any] = {
        "mode": "feature_cache" if feature_cache.get("hit") else "per_symbol_load_bars",
        "warnings": [],
    }
    feature_started = time.perf_counter()
    data: pd.DataFrame | None = None
    examples_count = 0
    free_factor_reports: list[dict[str, Any]] = list(feature_cache.get("factor_reports") or [])
    if feature_cache.get("hit"):
        data = pd.read_parquet(feature_cache["path"])
        examples_count = int(feature_cache.get("symbol_frames_kept") or data["symbol"].nunique())
        print(
            f"[gpu_probe] feature_cache hit rows={len(data)} path={feature_cache['path']}",
            file=sys.stderr,
            flush=True,
        )
    else:
        examples: list[pd.DataFrame] = []
        daily_context_frames: list[pd.DataFrame] = []
        for index, (symbol, bars) in enumerate(_iter_probe_bars(store, symbols, config, loader_diagnostics), start=1):
            context_frame = _daily_context_slice(bars, symbol=symbol, start=config.start, end=config.end)
            if not context_frame.empty:
                daily_context_frames.append(context_frame)
            frame = _symbol_feature_frame(
                bars,
                symbol=symbol,
                start=config.start,
                end=config.end,
                device=device,
                config=config,
            )
            if not frame.empty:
                examples.append(frame)
            if index == 1 or index % 250 == 0 or index == len(symbols):
                elapsed = time.perf_counter() - feature_started
                print(
                    f"[gpu_probe] feature_frames {index}/{len(symbols)} accepted={len(examples)} "
                    f"loader={loader_diagnostics.get('mode')} elapsed={elapsed:.1f}s",
                    file=sys.stderr,
                    flush=True,
                )
        examples_count = len(examples)
        if examples:
            data = pd.concat(examples, ignore_index=True).sort_values("date")
            factor_context_frames = daily_context_frames
            if len(context_symbols) > len(symbols):
                full_context = _load_daily_context_universe(
                    store,
                    symbols=context_symbols,
                    config=config,
                    diagnostics=loader_diagnostics,
                )
                if not full_context.empty:
                    factor_context_frames = [full_context]
            data, free_factor_reports = _attach_free_factor_features(data, daily_context_frames=factor_context_frames)
            data, market_index_reports = _attach_cached_market_index_features(data, store=store, config=config)
            free_factor_reports.extend(market_index_reports)
            data = _ensure_feature_columns(_add_cross_section_features(data))
            _write_feature_cache(
                feature_cache,
                data,
                symbols_considered=len(symbols),
                symbol_frames_kept=examples_count,
                factor_reports=free_factor_reports,
            )

    if data is None or data.empty:
        return {
            "status": "insufficient_samples",
            "device": str(device),
            "feature_count": float(len(GPU_PROBE_FEATURES)),
            "data_loader": loader_diagnostics,
            "feature_cache": feature_cache,
            "external_factors": free_factor_reports,
        }

    feature_names = _feature_names_for_config(config)
    data = _ensure_feature_columns(data.sort_values("date"))
    data["label_date"] = pd.to_datetime(data["label_date"], errors="coerce")
    data = data.dropna(subset=["date", "label_date"])
    train = data[data["label_date"].dt.date <= config.train_end]
    test = data[(data["date"].dt.date >= config.test_start) & (data["label_date"].dt.date <= config.end)]
    if train.empty or test.empty:
        return {
            "status": "insufficient_samples",
            "device": str(device),
            "rows_total": int(len(data)),
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "symbols_considered": int(len(symbols)),
            "symbol_frames_kept": int(examples_count),
            "feature_build_seconds": round(float(time.perf_counter() - feature_started), 3),
            "data_loader": loader_diagnostics,
            "feature_cache": feature_cache,
            "external_factors": free_factor_reports,
        }

    if len(test) > effective_test_rows:
        test = test.sample(n=effective_test_rows, random_state=config.seed + 2).sort_values("date")

    try:
        result = _train_and_score(
            train,
            test,
            device=device,
            epochs=config.epochs,
            seed=config.seed,
            feature_names=feature_names,
            target_accuracy=effective_target_accuracy,
            max_fit_rows=config.train_rows,
            validation_fraction=config.validation_fraction,
            embargo_label_days=config.embargo_label_days,
            max_selected_features=config.max_selected_features,
        )
    except SplitProtocolError as exc:
        return {
            "status": "invalid_split",
            "error": str(exc),
            "device": str(device),
            "rows_total": int(len(data)),
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "symbols_considered": int(len(symbols)),
            "symbol_frames_kept": int(examples_count),
            "training_protocol": {
                "split": "dev_train_dev_valid_test_lockbox",
                "row_split_fallback_allowed": False,
            },
        }
    acceptance = _acceptance_summary(
        result,
        test_rows=len(test),
        required_test_rows=effective_test_rows,
        target_accuracy=effective_target_accuracy,
        future_label_filter_used=float(config.min_label_return_pct) > 0.0,
    )
    result.update(
        {
            "status": "completed",
            "device": str(device),
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "feature_count": float(len(feature_names)),
            "feature_set": config.feature_set,
            "max_selected_features": int(config.max_selected_features),
            "features": list(feature_names),
            "rows_total": int(len(data)),
            "train_rows": int(result.get("train_window_rows", len(train))),
            "fit_rows": int(result.get("fit_rows", 0)),
            "validation_rows": int(result.get("validation_rows", 0)),
            "test_rows": int(len(test)),
            "symbols_considered": int(len(symbols)),
            "symbol_frames_kept": int(examples_count),
            "feature_build_seconds": round(float(time.perf_counter() - feature_started), 3),
            "data_loader": loader_diagnostics,
            "feature_cache": feature_cache,
            "external_factors": free_factor_reports,
            "requested_test_rows": int(config.test_rows),
            "required_test_rows": int(effective_test_rows),
            "minimum_test_rows": int(MIN_GPU_PROBE_TEST_ROWS),
            "desired_test_rows": int(DESIRED_GPU_PROBE_TEST_ROWS),
            "requested_target_accuracy": float(config.target_accuracy),
            "target_accuracy": float(effective_target_accuracy),
            "minimum_target_accuracy": float(MIN_GPU_PROBE_TARGET_ACCURACY),
            "accuracy_target_met": bool(float(result["accuracy"]) >= float(effective_target_accuracy)),
            "target_met": bool(acceptance["passed"]),
            "acceptance": acceptance,
            "split_manifest": _probe_split_manifest(config, train=train, test=test, training_result=result),
            "short_only": bool(config.short_only),
            "main_board_only": bool(config.main_board_only),
            "min_label_return_pct": float(config.min_label_return_pct),
            "future_label_filter_used": bool(float(config.min_label_return_pct) > 0.0),
            "short_filter": {
                "min_turnover": config.min_turnover,
                "min_amount": config.min_amount,
                "min_volume_z": config.min_volume_z,
                "min_amount_z": config.min_amount_z,
                "min_range_pct": config.min_range_pct,
                "min_volatility_pct": config.min_volatility_pct,
                "min_abnormal_flags": config.min_abnormal_flags,
                "min_phase_days_3": config.min_phase_days_3,
                "phase_rule": "current day must meet turnover, liquidity, and volatility gates; at least min_phase_days_3 of the latest 3 days must meet all three gates.",
            },
            "training_protocol": {
                "split": "dev_train_dev_valid_test_lockbox",
                "validation_fraction": float(config.validation_fraction),
                "embargo_trading_days": int(config.embargo_label_days),
                "row_split_fallback_allowed": False,
                "model_selection": "validation_only",
                "calibration": "validation_only",
                "confidence_threshold_selection": "validation_only",
                "test_usage": "final_acceptance_only",
                "final_fit_allowed_after_acceptance": bool(acceptance["passed"]),
            },
            "test_start": str(test["date"].min().date()),
            "test_end": str(test["date"].max().date()),
            "gpu_scope": "feature_matrix_and_torch_training" if device.type == "cuda" else "cpu_fallback",
            "gpu_enabled": bool(device.type == "cuda"),
            "full_gpu_pipeline": False,
            "cpu_stages": [
                "parquet_io",
                "polars_batch_parquet_scan",
                "pandas_date_filtering",
                "cross_section_feature_join",
                "numpy_bridge_for_xgboost_candidate",
                "json_artifact_serialization",
            ],
        }
    )
    artifacts = _write_gpu_probe_artifacts(store, result)
    if artifacts:
        result["artifacts"] = artifacts
    return result


def _symbol_feature_frame(
    bars: pd.DataFrame,
    *,
    symbol: str,
    start: date,
    end: date,
    device,
    config: GpuProbeConfig,
) -> pd.DataFrame:
    if bars.empty or "date" not in bars.columns:
        return pd.DataFrame()

    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    frame = frame[(frame["date"].dt.date >= start) & (frame["date"].dt.date <= end)].reset_index(drop=True)
    if len(frame) < 45:
        return pd.DataFrame()

    import torch

    month_groups = frame["date"].dt.to_period("M")
    month_position = frame.groupby(month_groups, sort=False).cumcount()
    month_size = frame.groupby(month_groups, sort=False)["date"].transform("size")
    day_of_week = torch.as_tensor(frame["date"].dt.dayofweek.to_numpy(dtype=np.float32), device=device)
    day_angle = day_of_week * (2.0 * 3.141592653589793 / 5.0)
    day_of_week_sin = torch.sin(day_angle)
    day_of_week_cos = torch.cos(day_angle)
    month_start_3 = torch.as_tensor((month_position <= 2).to_numpy(dtype=np.float32), device=device)
    month_end_3 = torch.as_tensor(((month_size - month_position - 1) <= 2).to_numpy(dtype=np.float32), device=device)

    open_ = torch.as_tensor(frame["open"].to_numpy(dtype=np.float32), device=device)
    high = torch.as_tensor(frame["high"].to_numpy(dtype=np.float32), device=device)
    low = torch.as_tensor(frame["low"].to_numpy(dtype=np.float32), device=device)
    close = torch.as_tensor(frame["close"].to_numpy(dtype=np.float32), device=device)
    volume = torch.as_tensor(frame["volume"].fillna(0.0).to_numpy(dtype=np.float32), device=device)
    amount = torch.as_tensor(_numeric_column(frame, "amount", fallback=frame["volume"] * frame["close"]), device=device)
    turnover = torch.as_tensor(_numeric_column(frame, "turnover"), device=device)

    eps = torch.tensor(1e-6, device=device)
    prev_close = _lag(close, 1)
    one_day_return = _pct_change(close, 1)
    volume_log = torch.log1p(torch.clamp(volume, min=0.0))
    amount_log = torch.log1p(torch.clamp(amount, min=0.0))
    high_low = torch.clamp(high - low, min=1e-6)
    range_pct = (high - low) / torch.clamp(close, min=eps) * 100.0
    close_position = (close - low) / high_low
    upper_shadow_pct = (high - torch.maximum(open_, close)) / high_low
    lower_shadow_pct = (torch.minimum(open_, close) - low) / high_low
    overnight_return = (open_ / torch.clamp(prev_close, min=eps) - 1.0) * 100.0
    intraday_return = (close / torch.clamp(open_, min=eps) - 1.0) * 100.0
    overnight_intraday_gap = overnight_return - intraday_return
    overnight_vs_intraday = overnight_return / torch.clamp(torch.abs(intraday_return), min=0.05)
    overnight_return_3d_mean = _rolling_mean(overnight_return, 3)
    overnight_return_5d_mean = _rolling_mean(overnight_return, 5)
    overnight_abs_rank_20 = _rolling_percent_rank(torch.abs(overnight_return), 20)
    reversal_intraday = -intraday_return
    open_to_high_pct = (high / torch.clamp(open_, min=eps) - 1.0) * 100.0
    open_to_low_pct = (low / torch.clamp(open_, min=eps) - 1.0) * 100.0
    volume_z_20 = _rolling_zscore(volume_log, 20)
    amount_z_20 = _rolling_zscore(amount_log, 20)
    ret_std_10 = _rolling_std(one_day_return, 10)
    atr_14_pct = _atr_pct(high, low, close, window=14)
    obv_trend_5 = _obv_trend(close, volume, window=5)
    mfi_14 = _mfi(high, low, close, volume, window=14)
    ma_5 = _rolling_mean(close, 5)
    ma_10 = _rolling_mean(close, 10)
    ma_20 = _rolling_mean(close, 20)
    close_std_20 = _rolling_std(close, 20)
    bollinger_upper_20 = ma_20 + close_std_20 * 2.0
    bollinger_lower_20 = ma_20 - close_std_20 * 2.0
    bollinger_width_20 = (bollinger_upper_20 - bollinger_lower_20) / torch.clamp(ma_20, min=eps)
    bollinger_position_20 = (close - bollinger_lower_20) / torch.clamp(bollinger_upper_20 - bollinger_lower_20, min=eps)
    macd_hist, macd_signal = _macd(close)
    kdj_k, kdj_d, kdj_j = _kdj(high, low, close, window=9)
    cci_20 = _cci(high, low, close, window=20)
    williams_r_14 = _williams_r(high, low, close, window=14)
    adx_14 = _adx(high, low, close, window=14)
    intraday_reversal_score = (
        torch.clamp(one_day_return, min=0.0) / 10.0
        + upper_shadow_pct
        + (1.0 - close_position)
        + torch.clamp(volume_z_20, min=0.0) * 0.1
        + torch.clamp(amount_z_20, min=0.0) * 0.1
    )
    near_limit_close = ((one_day_return >= 8.0) & (close_position >= 0.75)).to(torch.float32)
    limit_up_flag = (one_day_return >= 9.5).to(torch.float32)
    limit_down_flag = (one_day_return <= -9.5).to(torch.float32)
    limit_up_streak = _consecutive_streak(limit_up_flag)
    low_return = (low / torch.clamp(prev_close, min=eps) - 1.0) * 100.0
    limit_down_bounce_pct = torch.where(
        low_return <= -9.5,
        (close / torch.clamp(low, min=eps) - 1.0) * 100.0,
        torch.zeros_like(one_day_return),
    )
    rolling_high_10 = _rolling_max(high, 10)
    rolling_high_20 = _rolling_max(high, 20)
    failed_breakout_10 = ((high >= rolling_high_10) & (close_position <= 0.45)).to(torch.float32)
    failed_breakout_20 = ((high >= rolling_high_20) & (close_position <= 0.45)).to(torch.float32)
    volume_price_divergence_5 = (
        ((_pct_change(close, 5) > 0.0) & (_pct_change(volume_log, 5) < 0.0))
        | ((_pct_change(close, 5) < 0.0) & (_pct_change(volume_log, 5) > 0.0))
    ).to(torch.float32)
    money_flow_fire = (
        torch.clamp(amount_z_20, min=0.0) * 0.35
        + torch.clamp(volume_z_20, min=0.0) * 0.25
        + torch.clamp(_rolling_zscore(turnover, 20), min=0.0) * 0.20
        + torch.clamp(range_pct, min=0.0) / 10.0
        + torch.clamp(obv_trend_5, min=0.0) * 0.15
    )
    hot_exhaustion_score = (
        torch.clamp(amount_z_20, min=0.0) * upper_shadow_pct
        + torch.clamp(one_day_return, min=0.0) / 10.0
        + failed_breakout_10
        + failed_breakout_20
    )
    high_return = (high / torch.clamp(prev_close, min=eps) - 1.0) * 100.0
    limit_touch_fail_proxy = ((high_return >= 9.7) & (one_day_return < 9.0)).to(torch.float32)
    failed_limit_up = ((high_return >= 9.7) & (one_day_return < 9.5)).to(torch.float32)
    limit_seal_quality_proxy = (
        limit_up_flag
        * close_position
        * (1.0 - upper_shadow_pct)
        * torch.clamp(torch.minimum(amount_z_20, volume_z_20), min=0.0)
    )
    gap_pct = (open_ / torch.clamp(prev_close, min=eps) - 1.0) * 100.0
    up_gap_fill = torch.where(gap_pct > 0.0, (open_ - low) / torch.clamp(open_ - prev_close, min=eps), torch.zeros_like(gap_pct))
    down_gap_fill = torch.where(gap_pct < 0.0, (high - open_) / torch.clamp(prev_close - open_, min=eps), torch.zeros_like(gap_pct))
    gap_fill_ratio = torch.clamp(up_gap_fill + down_gap_fill, min=0.0, max=5.0)
    gap_continue_score = gap_pct * close_position * ((close > open_).to(torch.float32) * 2.0 - 1.0)
    trend_exhaustion_score = (
        _pct_change(close, 5) / torch.clamp(ret_std_10, min=eps)
        + upper_shadow_pct
        + volume_z_20
        - close_position
    )
    climax_volume_ratio_60 = volume / torch.clamp(_rolling_max(volume, 60), min=eps)
    climax_amount_ratio_60 = amount / torch.clamp(_rolling_max(amount, 60), min=eps)
    volume_to_mean_20 = volume / torch.clamp(_rolling_mean(volume, 20), min=eps)
    amount_to_mean_20 = amount / torch.clamp(_rolling_mean(amount, 20), min=eps)
    daily_amount_300m_gate = (amount >= 300_000_000.0).to(torch.float32)
    amount_300m_turnover_quality = (
        daily_amount_300m_gate
        * close_position
        * torch.clamp(turnover / 10.0, min=0.0, max=2.0)
        * torch.clamp(range_pct / 5.0, min=0.0, max=2.0)
    )
    volume_price_match = (
        (
            ((one_day_return > 0.0) & (close_position >= 0.60) & (volume_to_mean_20 >= 0.80) & (volume_to_mean_20 <= 2.50))
            | ((one_day_return >= -3.0) & (one_day_return <= 0.0) & (volume_to_mean_20 <= 1.10) & (close >= ma_5 * 0.98))
        ).to(torch.float32)
        - volume_price_divergence_5 * 0.75
        - ((upper_shadow_pct >= 0.35) & (volume_to_mean_20 >= 1.50)).to(torch.float32) * 0.75
    )
    twenty_cm_prefix = str(symbol).zfill(6).startswith(("300", "301", "688", "689", "830", "831", "832", "833", "834", "835", "836", "837", "838", "839", "870", "871", "872", "873", "874", "875", "876", "877", "878", "879", "430", "431", "432", "433", "434", "435", "436", "437", "438", "439"))
    twenty_cm_board_risk = torch.full_like(one_day_return, 1.0 if twenty_cm_prefix else 0.0) * (
        (one_day_return >= 12.0) | (high_return >= 12.0)
    ).to(torch.float32)
    turnover_to_mean_20 = turnover / torch.clamp(_rolling_mean(turnover, 20), min=eps)
    amount_mean_3 = _rolling_mean(amount, 3)
    range_mean_3 = _rolling_mean(range_pct, 3)
    range_mean_20 = _rolling_mean(range_pct, 20)
    atr_mean_3 = _rolling_mean(atr_14_pct, 3)
    turnover_mean_3 = _rolling_mean(turnover, 3)
    turnover_mean_5 = _rolling_mean(turnover, 5)
    phase_turnover_gate = turnover >= float(config.min_turnover)
    phase_liquidity_gate = (amount >= float(config.min_amount)) | (amount_z_20 >= float(config.min_amount_z))
    phase_volatility_gate = (
        (range_pct >= float(config.min_range_pct))
        | (ret_std_10 >= float(config.min_volatility_pct))
        | (atr_14_pct >= float(config.min_volatility_pct))
    )
    phase_day_flag = (phase_turnover_gate & phase_liquidity_gate & phase_volatility_gate).to(torch.float32)
    short_phase_days_3 = _rolling_sum(phase_day_flag, 3)
    short_phase_score_3 = (
        torch.clamp(turnover_mean_3 / max(float(config.min_turnover), 1e-6), max=5.0)
        + torch.clamp(amount_mean_3 / max(float(config.min_amount), 1e-6), max=5.0)
        + torch.clamp(range_mean_3 / max(float(config.min_range_pct), 1e-6), max=5.0)
    )
    turnover_sum_5 = _rolling_sum(turnover, 5)
    turnover_sum_10 = _rolling_sum(turnover, 10)
    turnover_sum_20 = _rolling_sum(turnover, 20)
    turnover_accel_5_20 = turnover_sum_5 / torch.clamp(turnover_sum_20 / 4.0, min=eps)
    rolling_low_20 = _rolling_min(low, 20)
    rolling_low_60 = _rolling_min(low, 60)
    rolling_high_60 = _rolling_max(high, 60)
    price_position_20 = (close - rolling_low_20) / torch.clamp(rolling_high_20 - rolling_low_20, min=eps)
    price_position_60 = (close - rolling_low_60) / torch.clamp(rolling_high_60 - rolling_low_60, min=eps)
    limit_up_freq_60 = _rolling_mean(limit_up_flag, 60)
    near_limit_freq_60 = _rolling_mean(near_limit_close, 60)
    failed_limit_freq_60 = _rolling_mean(failed_limit_up, 60)
    active_turnover_flag = ((turnover >= 3.0) & (amount >= 200_000_000.0) & (range_pct >= 3.0)).to(torch.float32)
    active_turnover_freq_60 = _rolling_mean(active_turnover_flag, 60)
    stock_personality_score = (
        limit_up_freq_60 * 3.0
        + near_limit_freq_60 * 1.5
        + active_turnover_freq_60
        + torch.clamp(_rolling_mean(turnover, 20) / 10.0, max=2.0)
        + torch.clamp(_rolling_mean(range_pct, 20) / 5.0, max=2.0)
    )
    first_board_entry = (limit_up_streak == 1.0).to(torch.float32)
    second_board_entry = (limit_up_streak == 2.0).to(torch.float32)
    new_high_board = (limit_up_flag * (close >= rolling_high_60).to(torch.float32)).to(torch.float32)
    new_high_breakout_quality = new_high_board * close_position * torch.clamp(volume_to_mean_20, max=5.0) / torch.clamp(
        1.0 + upper_shadow_pct,
        min=eps,
    )
    weak_to_strong_daily = (
        (_lag(one_day_return, 1) < 0.0)
        & (gap_pct >= 0.0)
        & (close_position >= 0.85)
        & (one_day_return >= 3.0)
        & (volume_to_mean_20 >= 1.0)
    ).to(torch.float32)
    low_suck_reversal_proxy = lower_shadow_pct * close_position * torch.clamp(volume_z_20, min=0.0)
    board_failure_repair = (
        (_lag(failed_limit_up, 1) > 0.5)
        & (one_day_return >= 3.0)
        & (close_position >= 0.70)
    ).to(torch.float32)
    monster_acceleration = (
        (limit_up_streak >= 2.0)
        & (volume_to_mean_20 <= 1.20)
        & (close_position >= 0.90)
        & (upper_shadow_pct <= 0.15)
    ).to(torch.float32)
    recognizable_backup = stock_personality_score * near_limit_close * (limit_up_streak <= 1.0).to(torch.float32)
    highlight_score = (
        stock_personality_score
        + torch.clamp((close / torch.clamp(ma_20, min=eps) - 1.0) * 10.0, min=-2.0, max=3.0)
        + close_position
        + weak_to_strong_daily * 1.5
        + new_high_breakout_quality * 0.5
        - failed_limit_freq_60
    )
    former_leader_peak_board_120 = _lag(_rolling_max(limit_up_streak, 120), 1)
    former_leader_limit_freq_120 = _lag(_rolling_mean(limit_up_flag, 120), 1)
    former_leader_memory_120 = torch.clamp(former_leader_peak_board_120 / 5.0, min=0.0, max=1.5) + torch.clamp(
        former_leader_limit_freq_120 * 8.0,
        min=0.0,
        max=2.0,
    )
    former_leader_recall = (
        former_leader_memory_120
        * ((one_day_return >= 5.0) | (near_limit_close > 0.5)).to(torch.float32)
        * close_position
        * torch.clamp(volume_to_mean_20, min=0.0, max=3.0)
        / 3.0
    )
    high_board_big_loss = ((_lag(limit_up_streak, 1) >= 2.0) & (one_day_return <= -5.0)).to(torch.float32)
    leader_faith_decay_60 = _rolling_mean(high_board_big_loss, 60)
    leader_faith_decay_pressure = leader_faith_decay_60 * (limit_up_streak + near_limit_close + failed_limit_up)
    active_ret_sign = torch.where(
        torch.abs(one_day_return) >= 1.0,
        torch.sign(one_day_return),
        torch.zeros_like(one_day_return),
    )
    sign_flip = (active_ret_sign * _lag(active_ret_sign, 1) < 0.0).to(torch.float32)
    quant_oscillation_score_10 = _rolling_mean(sign_flip, 10) * torch.clamp(range_mean_3 / 5.0, min=0.0, max=3.0)
    oscillation_breakout_signal = (
        quant_oscillation_score_10
        * (one_day_return >= 3.0).to(torch.float32)
        * close_position
        * torch.clamp(volume_to_mean_20, min=0.0, max=3.0)
    )
    new_high_volume_ratio_20 = (high >= rolling_high_20).to(torch.float32) * volume_to_mean_20
    consolidation_day = ((range_pct <= range_mean_20 * 0.75) & (ret_std_10 <= _rolling_mean(ret_std_10, 20))).to(torch.float32)
    consolidation_days_20 = _rolling_sum(consolidation_day, 20)
    consolidation_breakout_20 = (close >= rolling_high_20).to(torch.float32) * consolidation_days_20 * torch.clamp(
        volume_to_mean_20,
        max=5.0,
    )
    rolling_vwap_20 = _rolling_sum(amount, 20) / torch.clamp(_rolling_sum(volume, 20), min=eps)
    rolling_vwap_60 = _rolling_sum(amount, 60) / torch.clamp(_rolling_sum(volume, 60), min=eps)
    cost_position_20 = close / torch.clamp(rolling_vwap_20, min=eps) - 1.0
    cost_position_60 = close / torch.clamp(rolling_vwap_60, min=eps) - 1.0
    profit_pressure_20 = _profit_pressure(close, window=20)
    profit_pressure_60 = _profit_pressure(close, window=60)
    reversal_with_volume = -one_day_return * torch.clamp(volume_z_20, min=0.0)
    risk_long_upper_after_big_up = (one_day_return >= 5.0).to(torch.float32) * upper_shadow_pct * torch.clamp(volume_z_20, min=0.0)
    low_position_big_yang = (
        (price_position_60 <= 0.35)
        & (one_day_return >= 5.0)
        & (close_position >= 0.70)
        & (volume_to_mean_20 >= 1.10)
    ).to(torch.float32)
    low_position_volume_reversal = (
        (price_position_20 <= 0.30)
        & (lower_shadow_pct >= 0.25)
        & (close_position >= 0.55)
        & (volume_to_mean_20 >= 1.20)
    ).to(torch.float32)
    ma5_pullback_entry = (
        ((_pct_change(close, 10) >= 8.0) | (near_limit_freq_60 >= 0.08))
        & (low <= ma_5 * 1.02)
        & (close >= ma_5 * 0.995)
        & (close_position >= 0.55)
        & (one_day_return >= -2.5)
    ).to(torch.float32)
    ma5_break_exit = (
        ((_pct_change(close, 10) >= 8.0) | (near_limit_freq_60 >= 0.08))
        & (close < ma_5 * 0.985)
        & (one_day_return <= -2.0)
        & (volume_to_mean_20 >= 1.0)
    ).to(torch.float32)
    strong_rebound_from_20low = (
        (low <= rolling_low_20 * 1.05)
        & (one_day_return >= 3.0)
        & (close_position >= 0.70)
        & (volume_to_mean_20 >= 1.0)
    ).to(torch.float32)
    high_position_climax_risk = (
        (price_position_60 >= 0.85)
        & ((_pct_change(close, 10) >= 20.0) | (limit_up_streak >= 2.0))
        & (climax_amount_ratio_60 >= 0.80)
        & ((upper_shadow_pct >= 0.25) | (close_position <= 0.55))
    ).to(torch.float32)
    trend_pullback_health = (
        torch.clamp(_pct_change(close, 20), min=0.0, max=30.0) / 30.0
        * torch.clamp(1.0 - torch.abs(close / torch.clamp(ma_5, min=eps) - 1.0) * 10.0, min=0.0, max=1.0)
        * torch.clamp(volume_to_mean_20, min=0.0, max=2.0)
        * close_position
    )
    limit_up_turnover = limit_up_flag * turnover
    one_word_board_proxy = ((gap_pct >= 9.0) & (limit_up_flag > 0.5) & (range_pct <= 1.5)).to(torch.float32)
    t_shape_board_proxy = (
        (gap_pct >= 8.0)
        & (limit_up_flag > 0.5)
        & (low_return <= 5.0)
        & (close_position >= 0.90)
    ).to(torch.float32)
    t_plus_1_selling_pressure = _lag(limit_up_flag, 1) * turnover_to_mean_20
    board_space_height_5 = (close / torch.clamp(_rolling_min(low, 5), min=eps) - 1.0) * 100.0
    features = {
        "ret_1": one_day_return,
        "ret_2": _pct_change(close, 2),
        "ret_3": _pct_change(close, 3),
        "ret_5": _pct_change(close, 5),
        "ret_10": _pct_change(close, 10),
        "ret_20": _pct_change(close, 20),
        "ret_accel_1_3": _pct_change(close, 1) - _pct_change(close, 3) / 3.0,
        "ret_accel_3_10": _pct_change(close, 3) / 3.0 - _pct_change(close, 10) / 10.0,
        "ret_mean_3": _rolling_mean(one_day_return, 3),
        "ret_mean_5": _rolling_mean(one_day_return, 5),
        "ret_mean_10": _rolling_mean(one_day_return, 10),
        "ret_std_5": _rolling_std(one_day_return, 5),
        "ret_std_10": ret_std_10,
        "ret_std_20": _rolling_std(one_day_return, 20),
        "volume_chg_1": _pct_change(volume_log, 1),
        "volume_chg_5": _pct_change(volume_log, 5),
        "volume_z_5": _rolling_zscore(volume_log, 5),
        "volume_z_10": _rolling_zscore(volume_log, 10),
        "volume_z_20": volume_z_20,
        "amount_chg_1": _pct_change(amount_log, 1),
        "amount_chg_5": _pct_change(amount_log, 5),
        "amount_z_20": amount_z_20,
        "turnover": turnover,
        "turnover_mean_3": turnover_mean_3,
        "turnover_mean_5": turnover_mean_5,
        "turnover_chg_1": _pct_change(turnover, 1),
        "turnover_chg_5": _pct_change(turnover, 5),
        "turnover_z_20": _rolling_zscore(turnover, 20),
        "turnover_to_max_20": turnover / torch.clamp(_rolling_max(turnover, 20), min=eps),
        "amount_to_max_20": amount / torch.clamp(_rolling_max(amount, 20), min=eps),
        "range_pct": range_pct,
        "body_pct": (close - open_) / torch.clamp(open_, min=eps) * 100.0,
        "upper_shadow_pct": upper_shadow_pct,
        "lower_shadow_pct": lower_shadow_pct,
        "close_position": close_position,
        "gap_pct": gap_pct,
        "overnight_return": overnight_return,
        "intraday_return": intraday_return,
        "overnight_intraday_gap": overnight_intraday_gap,
        "overnight_vs_intraday": overnight_vs_intraday,
        "overnight_return_3d_mean": overnight_return_3d_mean,
        "overnight_return_5d_mean": overnight_return_5d_mean,
        "overnight_abs_rank_20": overnight_abs_rank_20,
        "reversal_intraday": reversal_intraday,
        "open_to_high_pct": open_to_high_pct,
        "open_to_low_pct": open_to_low_pct,
        "ma_gap_5": close / torch.clamp(ma_5, min=eps) - 1.0,
        "ma_gap_10": close / torch.clamp(ma_10, min=eps) - 1.0,
        "ma_gap_20": close / torch.clamp(ma_20, min=eps) - 1.0,
        "mean_reversion_distance_5": close / torch.clamp(ma_5, min=eps) - 1.0,
        "bollinger_position_20": bollinger_position_20,
        "bollinger_width_20": bollinger_width_20,
        "dist_high_10": close / torch.clamp(_rolling_max(high, 10), min=eps) - 1.0,
        "dist_high_20": close / torch.clamp(_rolling_max(high, 20), min=eps) - 1.0,
        "dist_low_10": close / torch.clamp(_rolling_min(low, 10), min=eps) - 1.0,
        "dist_low_20": close / torch.clamp(_rolling_min(low, 20), min=eps) - 1.0,
        "breakout_20": (close >= _rolling_max(high, 20)).to(torch.float32),
        "breakdown_20": (close <= _rolling_min(low, 20)).to(torch.float32),
        "limit_up_like": limit_up_flag,
        "limit_down_like": limit_down_flag,
        "failed_limit_up": failed_limit_up,
        "limit_down_bounce_pct": limit_down_bounce_pct,
        "limit_up_turnover": limit_up_turnover,
        "one_word_board_proxy": one_word_board_proxy,
        "t_shape_board_proxy": t_shape_board_proxy,
        "t_plus_1_selling_pressure": t_plus_1_selling_pressure,
        "board_space_height_5": board_space_height_5,
        "big_up": (one_day_return >= 5.0).to(torch.float32),
        "big_down": (one_day_return <= -5.0).to(torch.float32),
        "up_count_3": _rolling_sum((one_day_return > 0).to(torch.float32), 3),
        "up_count_5": _rolling_sum((one_day_return > 0).to(torch.float32), 5),
        "down_count_3": _rolling_sum((one_day_return < 0).to(torch.float32), 3),
        "down_count_5": _rolling_sum((one_day_return < 0).to(torch.float32), 5),
        "rsi_6": _rsi(one_day_return, 6),
        "rsi_14": _rsi(one_day_return, 14),
        "atr_14_pct": atr_14_pct,
        "obv_trend_5": obv_trend_5,
        "mfi_14": mfi_14,
        "macd_hist": macd_hist,
        "macd_signal": macd_signal,
        "kdj_k": kdj_k,
        "kdj_d": kdj_d,
        "kdj_j": kdj_j,
        "cci_20": cci_20,
        "williams_r_14": williams_r_14,
        "adx_14": adx_14,
        "intraday_reversal_score": intraday_reversal_score,
        "limit_up_streak": limit_up_streak,
        "near_limit_close": near_limit_close,
        "failed_breakout_10": failed_breakout_10,
        "failed_breakout_20": failed_breakout_20,
        "volume_price_divergence_5": volume_price_divergence_5,
        "money_flow_fire": money_flow_fire,
        "hot_exhaustion_score": hot_exhaustion_score,
        "limit_touch_fail_proxy": limit_touch_fail_proxy,
        "limit_seal_quality_proxy": limit_seal_quality_proxy,
        "gap_fill_ratio": gap_fill_ratio,
        "gap_continue_score": gap_continue_score,
        "trend_exhaustion_score": trend_exhaustion_score,
        "climax_volume_ratio_60": climax_volume_ratio_60,
        "climax_amount_ratio_60": climax_amount_ratio_60,
        "volume_to_mean_20": volume_to_mean_20,
        "amount_to_mean_20": amount_to_mean_20,
        "daily_amount_300m_gate": daily_amount_300m_gate,
        "amount_300m_turnover_quality": amount_300m_turnover_quality,
        "volume_price_match": volume_price_match,
        "twenty_cm_board_risk": twenty_cm_board_risk,
        "amount_mean_3": amount_mean_3,
        "range_mean_3": range_mean_3,
        "atr_mean_3": atr_mean_3,
        "short_phase_score_3": short_phase_score_3,
        "short_phase_days_3": short_phase_days_3,
        "turnover_sum_5": turnover_sum_5,
        "turnover_sum_10": turnover_sum_10,
        "turnover_sum_20": turnover_sum_20,
        "turnover_accel_5_20": turnover_accel_5_20,
        "limit_up_freq_60": limit_up_freq_60,
        "near_limit_freq_60": near_limit_freq_60,
        "failed_limit_freq_60": failed_limit_freq_60,
        "active_turnover_freq_60": active_turnover_freq_60,
        "stock_personality_score": stock_personality_score,
        "first_board_entry": first_board_entry,
        "second_board_entry": second_board_entry,
        "new_high_board": new_high_board,
        "new_high_breakout_quality": new_high_breakout_quality,
        "weak_to_strong_daily": weak_to_strong_daily,
        "low_suck_reversal_proxy": low_suck_reversal_proxy,
        "board_failure_repair": board_failure_repair,
        "monster_acceleration": monster_acceleration,
        "recognizable_backup": recognizable_backup,
        "highlight_score": highlight_score,
        "former_leader_memory_120": former_leader_memory_120,
        "former_leader_recall": former_leader_recall,
        "leader_faith_decay_60": leader_faith_decay_60,
        "leader_faith_decay_pressure": leader_faith_decay_pressure,
        "quant_oscillation_score_10": quant_oscillation_score_10,
        "oscillation_breakout_signal": oscillation_breakout_signal,
        "new_high_volume_ratio_20": new_high_volume_ratio_20,
        "consolidation_days_20": consolidation_days_20,
        "consolidation_breakout_20": consolidation_breakout_20,
        "reversal_with_volume": reversal_with_volume,
        "cost_position_20": cost_position_20,
        "cost_position_60": cost_position_60,
        "profit_pressure_20": profit_pressure_20,
        "profit_pressure_60": profit_pressure_60,
        "risk_long_upper_after_big_up": risk_long_upper_after_big_up,
        "price_position_20": price_position_20,
        "price_position_60": price_position_60,
        "low_position_big_yang": low_position_big_yang,
        "low_position_volume_reversal": low_position_volume_reversal,
        "ma5_pullback_entry": ma5_pullback_entry,
        "ma5_break_exit": ma5_break_exit,
        "strong_rebound_from_20low": strong_rebound_from_20low,
        "high_position_climax_risk": high_position_climax_risk,
        "trend_pullback_health": trend_pullback_health,
        "day_of_week_sin": day_of_week_sin,
        "day_of_week_cos": day_of_week_cos,
        "month_start_3": month_start_3,
        "month_end_3": month_end_3,
    }
    for lag in range(10):
        features[f"ret_lag_{lag}"] = _lag(one_day_return, lag)
    for lag in range(5):
        features[f"range_lag_{lag}"] = _lag(range_pct, lag)
        features[f"close_pos_lag_{lag}"] = _lag(close_position, lag)
        features[f"volume_z_lag_{lag}"] = _lag(volume_z_20, lag)
        features[f"amount_z_lag_{lag}"] = _lag(amount_z_20, lag)
    features["ret1_x_volume_z5"] = features["ret_1"] * features["volume_z_5"]
    features["ret5_x_volume_z10"] = features["ret_5"] * features["volume_z_10"]
    features["ret1_x_close_position"] = features["ret_1"] * features["close_position"]
    features["range_x_volume_z5"] = features["range_pct"] * features["volume_z_5"]
    features["turnover_x_range"] = features["turnover"] * features["range_pct"]
    features["amount_z_x_range"] = features["amount_z_20"] * features["range_pct"]
    features["upper_shadow_x_volume_z"] = features["upper_shadow_pct"] * features["volume_z_20"]
    features["lower_shadow_x_volume_z"] = features["lower_shadow_pct"] * features["volume_z_20"]

    matrix = torch.stack([torch.nan_to_num(features[name], nan=0.0, posinf=0.0, neginf=0.0) for name in GPU_PROBE_SYMBOL_FEATURES], dim=1)
    next_return = (torch.roll(close, shifts=-1) / torch.clamp(close, min=eps) - 1.0) * 100.0
    label_threshold = max(float(config.min_label_return_pct), 0.0)
    label = (next_return > label_threshold).to(torch.float32)
    valid = torch.arange(len(frame), device=device)
    valid = (valid >= 25) & (valid < len(frame) - 1)
    if label_threshold > 0.0:
        valid = valid & (torch.abs(next_return) >= label_threshold)
    if config.short_only:
        turnover_gate = phase_turnover_gate
        liquidity_gate = phase_liquidity_gate
        volatility_gate = phase_volatility_gate
        phase_gate = features["short_phase_days_3"] >= float(config.min_phase_days_3)
        abnormal_flags = (
            turnover_gate.to(torch.int32)
            + liquidity_gate.to(torch.int32)
            + (features["volume_z_20"] >= float(config.min_volume_z)).to(torch.int32)
            + volatility_gate.to(torch.int32)
            + (features["money_flow_fire"] >= 1.5).to(torch.int32)
            + (features["volume_to_mean_20"] >= 1.5).to(torch.int32)
            + (features["amount_to_mean_20"] >= 1.5).to(torch.int32)
        )
        valid = (
            valid
            & turnover_gate
            & liquidity_gate
            & volatility_gate
            & phase_gate
            & (abnormal_flags >= int(config.min_abnormal_flags))
        )
    if not torch.any(valid):
        return pd.DataFrame()

    valid_mask = valid.detach().cpu().numpy()
    selected = matrix[valid].detach().cpu().numpy()
    labels = label[valid].detach().cpu().numpy()
    out = pd.DataFrame(selected, columns=GPU_PROBE_SYMBOL_FEATURES)
    out["actual"] = labels.astype(np.float32)
    out["next_return_pct"] = next_return[valid].detach().cpu().numpy().astype(np.float32)
    out["close"] = close[valid].detach().cpu().numpy().astype(np.float32)
    out["date"] = frame.loc[valid_mask, "date"].to_numpy()
    out["label_date"] = frame["date"].shift(-1).loc[valid_mask].to_numpy()
    out["symbol"] = symbol
    return out


def _is_main_board_symbol(symbol: str) -> bool:
    normalized = str(symbol).strip().zfill(6)
    return normalized.startswith(("600", "601", "603", "605", "000", "001", "002", "003"))


def _iter_probe_bars(
    store: LocalDataStore,
    symbols: list[str],
    config: GpuProbeConfig,
    diagnostics: dict[str, Any],
):
    batch_loader = getattr(store, "load_market_data", None)
    if callable(batch_loader) and symbols:
        try:
            loaded = batch_loader(
                frequency="daily",
                symbols=symbols,
                start_date=config.start,
                end_date=config.end,
            )
            if hasattr(loaded, "is_empty") and not loaded.is_empty():
                data = loaded.to_pandas()
                if "symbol" in data.columns:
                    diagnostics["mode"] = "polars_batch_load_market_data"
                    data["symbol"] = data["symbol"].astype(str).str.zfill(6)
                    grouped = {str(symbol).zfill(6): group for symbol, group in data.groupby("symbol", sort=False)}
                    for symbol in symbols:
                        group = grouped.get(symbol)
                        if group is not None and not group.empty:
                            yield symbol, group.copy()
                    return
                diagnostics.setdefault("warnings", []).append("batch_loader_missing_symbol_column")
        except Exception as exc:
            diagnostics.setdefault("warnings", []).append(f"batch_loader_failed: {exc}")

    diagnostics["mode"] = "per_symbol_load_bars"
    for symbol in symbols:
        try:
            yield symbol, store.load_bars(symbol, "daily")
        except Exception as exc:
            diagnostics.setdefault("warnings", []).append(f"{symbol}: {exc}")


def _load_daily_context_universe(
    store: LocalDataStore,
    *,
    symbols: list[str],
    config: GpuProbeConfig,
    diagnostics: dict[str, Any],
) -> pd.DataFrame:
    batch_loader = getattr(store, "load_market_data", None)
    if callable(batch_loader) and symbols:
        try:
            loaded = batch_loader(
                frequency="daily",
                symbols=symbols,
                start_date=config.start,
                end_date=config.end,
            )
            if hasattr(loaded, "is_empty") and not loaded.is_empty():
                frame = loaded.to_pandas()
                if "symbol" in frame.columns:
                    frame["symbol"] = frame["symbol"].astype(str).str.zfill(6)
                    columns = [
                        column
                        for column in ("symbol", "date", "open", "high", "low", "close", "volume", "amount", "turnover")
                        if column in frame.columns
                    ]
                    return frame.loc[:, columns].copy()
        except Exception as exc:
            diagnostics.setdefault("warnings", []).append(f"full_factor_context_load_failed: {exc}")
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        try:
            context = _daily_context_slice(store.load_bars(symbol, "daily"), symbol=symbol, start=config.start, end=config.end)
        except Exception as exc:
            diagnostics.setdefault("warnings", []).append(f"{symbol}_factor_context_failed: {exc}")
            continue
        if not context.empty:
            frames.append(context)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _purged_train_validation_split(
    train: pd.DataFrame,
    *,
    validation_fraction: float,
    embargo_label_days: int,
    max_fit_rows: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    frame = train.copy()
    frame["label_date"] = pd.to_datetime(frame["label_date"], errors="coerce")
    frame = frame.dropna(subset=["label_date"])
    if frame.empty:
        raise SplitProtocolError("No train rows remain after label_date parsing.")
    train_end = pd.Timestamp(frame["label_date"].max()).date()
    split_config = SplitProtocolConfig(
        train_end=train_end,
        test_start=train_end + timedelta(days=1),
        end=train_end + timedelta(days=1),
        validation_fraction=validation_fraction,
        embargo_trading_days=embargo_label_days,
        max_fit_rows=max_fit_rows,
        seed=seed,
        allow_row_split_fallback=False,
    )
    fit, valid, info = _official_purged_train_validation_split(frame, split_config)
    info["embargo_label_days"] = int(embargo_label_days)
    info["max_fit_rows"] = int(max_fit_rows)
    return fit, valid, info


def _train_and_score(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    device,
    epochs: int,
    seed: int,
    feature_names: tuple[str, ...],
    target_accuracy: float,
    max_fit_rows: int,
    validation_fraction: float,
    embargo_label_days: int,
    max_selected_features: int,
) -> dict[str, Any]:
    import torch

    torch.manual_seed(seed)
    fit_frame, valid_frame, split_info = _purged_train_validation_split(
        train,
        validation_fraction=validation_fraction,
        embargo_label_days=embargo_label_days,
        max_fit_rows=max_fit_rows,
        seed=seed,
    )
    x_train = torch.as_tensor(fit_frame.loc[:, feature_names].to_numpy(dtype=np.float32), device=device)
    y_train = torch.as_tensor(fit_frame["actual"].to_numpy(dtype=np.float32), device=device).view(-1, 1)
    train_return_abs = torch.as_tensor(
        np.abs(fit_frame.get("next_return_pct", pd.Series(np.zeros(len(fit_frame)))).to_numpy(dtype=np.float32)),
        device=device,
    ).view(-1, 1)
    x_valid = torch.as_tensor(valid_frame.loc[:, feature_names].to_numpy(dtype=np.float32), device=device)
    y_valid = torch.as_tensor(valid_frame["actual"].to_numpy(dtype=np.float32), device=device).view(-1, 1)
    x_test = torch.as_tensor(test.loc[:, feature_names].to_numpy(dtype=np.float32), device=device)
    y_test = torch.as_tensor(test["actual"].to_numpy(dtype=np.float32), device=device).view(-1, 1)

    mean = x_train.mean(dim=0, keepdim=True)
    std = torch.clamp(x_train.std(dim=0, keepdim=True), min=1e-6)
    x_train = (x_train - mean) / std
    x_valid = (x_valid - mean) / std if len(x_valid) else x_valid
    x_test = (x_test - mean) / std
    feature_selection = _select_training_feature_indices(
        x_train,
        y_train.flatten(),
        feature_names,
        max_features=max_selected_features,
    )
    selected_indices = feature_selection.pop("_indices", None)
    selected_feature_names = tuple(feature_names)
    if selected_indices is not None:
        selected_index_values = [int(index) for index in selected_indices.detach().cpu().tolist()]
        selected_feature_names = tuple(feature_names[index] for index in selected_index_values)
        x_train = x_train[:, selected_indices]
        x_valid = x_valid[:, selected_indices] if len(x_valid) else x_valid
        x_test = x_test[:, selected_indices]

    candidates = [
        ("gpu_logistic", _TorchLogistic(x_train.shape[1]).to(device), max(epochs, 80), 0.02),
        ("gpu_mlp_64_32", _TorchMlp(x_train.shape[1], hidden=(64, 32)).to(device), max(epochs, 120), 0.005),
        ("gpu_mlp_128_64", _TorchMlp(x_train.shape[1], hidden=(128, 64)).to(device), max(epochs, 120), 0.003),
        ("gpu_mlp_256_128_64", _TorchMlp(x_train.shape[1], hidden=(256, 128, 64)).to(device), max(epochs, 140), 0.0025),
        ("gpu_residual_mlp_128", _TorchResidualMlp(x_train.shape[1], hidden=128).to(device), max(epochs, 140), 0.003),
        ("gpu_residual_mlp_256", _TorchResidualMlp(x_train.shape[1], hidden=256).to(device), max(epochs, 160), 0.002),
    ]
    pos_rate = torch.clamp(y_train.mean(), min=1e-4, max=1.0 - 1e-4)
    pos_weight = (1.0 - pos_rate) / pos_rate
    sample_weight = 1.0 + torch.clamp(train_return_abs, max=5.0) / 5.0
    best: dict[str, Any] | None = None
    trained_candidates: list[dict[str, Any]] = []
    candidate_warnings: list[str] = []

    for name, model, model_epochs, lr in candidates:
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
        for _ in range(model_epochs):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            logits = model(x_train)
            loss = _focal_bce_with_logits(logits, y_train, pos_weight=pos_weight, sample_weight=sample_weight)
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.no_grad():
            valid_logits = model(x_valid).flatten() if len(x_valid) else torch.empty(0, device=device)
            valid_y = y_valid.flatten() if len(y_valid) else torch.empty(0, device=device)
        calibration = _fit_logit_calibration(valid_logits, valid_y) if len(valid_y) else {"scale": 1.0, "bias": 0.0}
        with torch.no_grad():
            valid_prob = _apply_logit_calibration(valid_logits, calibration)
            threshold, valid_accuracy = _best_threshold(valid_prob, valid_y) if len(valid_y) else (0.5, 0.0)
            band = _best_confidence_band(
                valid_prob,
                valid_y,
                threshold=threshold,
                target_accuracy=target_accuracy,
                min_count=MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS,
                min_coverage=MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE,
            )
            valid_brier = _brier(valid_prob, valid_y) if len(valid_y) else 1.0
            score = _candidate_selection_score(
                valid_accuracy,
                valid_brier,
                band,
                target_accuracy=target_accuracy,
            )
            candidate = {
                    "model_name": name,
                    "model": model,
                    "model_kind": "torch",
                    "selection_score": float(score),
                    "validation_accuracy": float(valid_accuracy),
                    "validation_brier": float(valid_brier),
                    "threshold": float(threshold),
                    "confidence_band": band,
                    "calibration": calibration,
                    "validation_prob": valid_prob.detach(),
                }
            trained_candidates.append(candidate)
            if best is None or score > best["selection_score"]:
                best = candidate

    def _register_candidate(candidate: dict[str, Any]) -> None:
        nonlocal best
        if candidate.get("warning"):
            candidate_warnings.append(str(candidate["warning"]))
            return
        if not candidate:
            return
        trained_candidates.append(candidate)
        if best is None or float(candidate["selection_score"]) > best["selection_score"]:
            best = candidate

    xgboost_variants: tuple[tuple[str, dict[str, Any]], ...] = (
        ("baseline", {}),
        (
            "shallow",
            {
                "n_estimators": 500,
                "max_depth": 3,
                "learning_rate": 0.025,
                "min_child_weight": 3.0,
                "subsample": 0.90,
                "colsample_bytree": 0.75,
            },
        ),
        (
            "deep",
            {
                "n_estimators": 420,
                "max_depth": 5,
                "learning_rate": 0.025,
                "min_child_weight": 1.5,
                "subsample": 0.80,
                "colsample_bytree": 0.90,
            },
        ),
    )
    for variant, params in xgboost_variants:
        _register_candidate(
            _fit_xgboost_candidate(
                x_train,
                y_train,
                x_valid,
                y_valid,
                device=device,
                seed=seed,
                target_accuracy=target_accuracy,
                variant=variant,
                params=params,
            )
        )

    lightgbm_variants: tuple[tuple[str, dict[str, Any]], ...] = (
        ("baseline", {}),
        (
            "compact",
            {
                "n_estimators": 600,
                "learning_rate": 0.020,
                "num_leaves": 15,
                "min_child_samples": 120,
                "reg_lambda": 1.5,
                "colsample_bytree": 0.75,
            },
        ),
        (
            "wide",
            {
                "n_estimators": 380,
                "learning_rate": 0.030,
                "num_leaves": 63,
                "min_child_samples": 55,
                "reg_lambda": 1.2,
                "colsample_bytree": 0.90,
            },
        ),
    )
    for variant, params in lightgbm_variants:
        _register_candidate(
            _fit_lightgbm_candidate(
                x_train,
                y_train,
                x_valid,
                y_valid,
                device=device,
                seed=seed,
                target_accuracy=target_accuracy,
                variant=variant,
                params=params,
            )
        )

    catboost_variants: tuple[tuple[str, dict[str, Any]], ...] = (
        ("baseline", {}),
        (
            "compact",
            {
                "iterations": 550,
                "depth": 4,
                "learning_rate": 0.030,
                "l2_leaf_reg": 8.0,
            },
        ),
        (
            "expressive",
            {
                "iterations": 420,
                "depth": 8,
                "learning_rate": 0.018,
                "l2_leaf_reg": 10.0,
            },
        ),
    )
    for variant, params in catboost_variants:
        _register_candidate(
            _fit_catboost_candidate(
                x_train,
                y_train,
                x_valid,
                y_valid,
                device=device,
                seed=seed,
                target_accuracy=target_accuracy,
                variant=variant,
                params=params,
            )
        )

    ensemble_candidate = _build_average_ensemble_candidate(
        trained_candidates,
        y_valid.flatten(),
        target_accuracy=target_accuracy,
    )
    if ensemble_candidate:
        trained_candidates.append(ensemble_candidate)
        if best is None or float(ensemble_candidate["selection_score"]) > best["selection_score"]:
            best = ensemble_candidate

    assert best is not None
    candidate_reports = _candidate_reports(trained_candidates)
    model = best.get("model")
    model_kind = str(best.get("model_kind", "torch"))
    if model_kind == "torch" and model is not None:
        model.eval()
    with torch.no_grad():
        if model_kind == "ensemble_average":
            valid_prob_for_confidence = _predict_average_ensemble_prob(best["members"], x_valid, device=device) if len(x_valid) else torch.empty(0, device=device)
            prob = _predict_average_ensemble_prob(best["members"], x_test, device=device)
        elif model_kind in {"xgboost", "lightgbm", "catboost"}:
            valid_prob_for_confidence = _predict_xgboost_prob(model, x_valid, device=device) if len(x_valid) else torch.empty(0, device=device)
            prob = _predict_xgboost_prob(model, x_test, device=device)
        else:
            valid_logits = model(x_valid).flatten() if len(x_valid) else torch.empty(0, device=device)
            valid_prob_for_confidence = _apply_logit_calibration(
                valid_logits,
                best.get("calibration") or {"scale": 1.0, "bias": 0.0},
            )
            logits = model(x_test).flatten()
            prob = _apply_logit_calibration(logits, best.get("calibration") or {"scale": 1.0, "bias": 0.0})
        y = y_test.flatten()
        valid_y_for_confidence = y_valid.flatten() if len(y_valid) else torch.empty(0, device=device)
        threshold = float(best["threshold"])
        predicted = (prob >= threshold).to(y.dtype)
        correct = predicted == y
        accuracy = _accuracy(prob, y, threshold=threshold)
        brier = _brier(prob, y)
        positive_rate = float(y.mean().detach().cpu().item())
        baseline_accuracy = max(positive_rate, 1.0 - positive_rate)
        baseline_brier = _constant_brier(y, value=positive_rate)
        band = best.get("confidence_band") or {"low": 0.35, "high": 0.65}
        band_confident = _confidence_mask_from_band(prob, band)
    meta_selector = _fit_meta_confidence_selector(
        x_valid,
        valid_y_for_confidence,
        valid_prob_for_confidence,
        x_test,
        prob,
        threshold=threshold,
        target_accuracy=target_accuracy,
        seed=seed,
    )
    agreement_selector = _fit_agreement_confidence_selector(
        trained_candidates,
        x_valid,
        valid_y_for_confidence,
        valid_prob_for_confidence,
        x_test,
        prob,
        threshold=threshold,
        target_accuracy=target_accuracy,
    )
    regime_selector = _fit_regime_confidence_selector(
        x_valid,
        valid_y_for_confidence,
        valid_prob_for_confidence,
        x_test,
        prob,
        threshold=threshold,
        target_accuracy=target_accuracy,
        feature_names=selected_feature_names,
    )
    with torch.no_grad():
        band_report_source = best.get("confidence_band") or {}
        confidence_selector_report: dict[str, Any] = {
            "method": "probability_band",
            "eligible": bool(
                band_report_source.get("constraint_met")
                and band_report_source.get("target_wilson_met")
                and band_report_source.get("stable_constraint_met")
            ),
            "validation_accuracy": float(band_report_source.get("accuracy") or 0.0),
            "validation_wilson_lower_95": float(band_report_source.get("wilson_lower_95") or 0.0),
            "validation_stability_min_accuracy": float(
                band_report_source.get("stability_min_accuracy") or band_report_source.get("accuracy") or 0.0
            ),
            "validation_stability_min_wilson_lower_95": float(
                band_report_source.get("stability_min_wilson_lower_95")
                or band_report_source.get("wilson_lower_95")
                or 0.0
            ),
            "validation_stability_min_coverage": float(
                band_report_source.get("stability_min_coverage") or band_report_source.get("coverage") or 0.0
            ),
            "validation_stability_chunks": int(band_report_source.get("stability_chunks") or 1),
            "validation_coverage": float(band_report_source.get("coverage") or 0.0),
            "validation_count": int(band_report_source.get("count") or 0),
        }
        selector_options: list[tuple[dict[str, Any], Any]] = [(confidence_selector_report, band_confident)]
        if agreement_selector:
            agreement_report = {
                key: value
                for key, value in agreement_selector.items()
                if key != "test_mask"
            }
            confidence_selector_report["agreement_candidate"] = agreement_report
            selector_options.append((agreement_report, agreement_selector["test_mask"]))
        if meta_selector:
            meta_report = {
                key: value
                for key, value in meta_selector.items()
                if key != "test_mask"
            }
            confidence_selector_report["meta_candidate"] = meta_report
            selector_options.append((meta_report, meta_selector["test_mask"]))
        if regime_selector:
            regime_report = {
                key: value
                for key, value in regime_selector.items()
                if key != "test_mask"
            }
            confidence_selector_report["regime_candidate"] = regime_report
            if bool(regime_report.get("eligible")):
                selector_options.append((regime_report, regime_selector["test_mask"]))
        selected_report, confident = _select_confidence_selector(selector_options)
        confidence_method = str(selected_report.get("method") or "probability_band")
        if selected_report is not confidence_selector_report:
            selected_report = dict(selected_report)
            if "agreement_candidate" not in selected_report and "agreement_candidate" in confidence_selector_report:
                selected_report["agreement_candidate"] = confidence_selector_report["agreement_candidate"]
            if "meta_candidate" not in selected_report and "meta_candidate" in confidence_selector_report:
                selected_report["meta_candidate"] = confidence_selector_report["meta_candidate"]
            if "regime_candidate" not in selected_report and "regime_candidate" in confidence_selector_report:
                selected_report["regime_candidate"] = confidence_selector_report["regime_candidate"]
            confidence_selector_report = selected_report
        confident_accuracy = _accuracy(prob[confident], y[confident], threshold=threshold) if torch.any(confident) else None
        confident_brier = _brier(prob[confident], y[confident]) if torch.any(confident) else None
        correct_count = int(correct.sum().detach().cpu().item())
        confident_correct_count = int(correct[confident].sum().detach().cpu().item()) if torch.any(confident) else 0
        test_oracle_coverage_at_target = _coverage_at_accuracy(
            prob,
            y,
            threshold=threshold,
            target_accuracy=target_accuracy,
        )
    return {
        "model": best["model_name"],
        "model_kind": model_kind,
        "train_window_rows": int(split_info["train_window_rows"]),
        "fit_rows": int(split_info["fit_rows"]),
        "validation_rows": int(split_info["validation_rows"]),
        "validation_start": split_info.get("validation_start"),
        "fit_label_end": split_info.get("fit_label_end"),
        "embargo_label_days": int(split_info["embargo_label_days"]),
        "max_fit_rows": int(split_info["max_fit_rows"]),
        "accuracy": round(float(accuracy), 6),
        "correct_count": int(correct_count),
        "brier": round(float(brier), 6),
        "positive_rate": round(positive_rate, 6),
        "baseline_accuracy": round(float(baseline_accuracy), 6),
        "baseline_brier": round(float(baseline_brier), 6),
        "validation_accuracy": round(float(best["validation_accuracy"]), 6),
        "validation_brier": round(float(best["validation_brier"]), 6),
        "classification_threshold": round(float(best["threshold"]), 6),
        "calibration": best.get("calibration"),
        "validation_confident_accuracy": round(float((best.get("confidence_band") or {}).get("accuracy") or 0.0), 6),
        "validation_confident_coverage": round(float((best.get("confidence_band") or {}).get("coverage") or 0.0), 6),
        "confidence_low_threshold": round(float((best.get("confidence_band") or {}).get("low", 0.35)), 6),
        "confidence_high_threshold": round(float((best.get("confidence_band") or {}).get("high", 0.65)), 6),
        "confidence_side": str((best.get("confidence_band") or {}).get("side", "both")),
        "confidence_min_validation_count": int(MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS),
        "confidence_min_validation_coverage": float(MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE),
        "confidence_method": confidence_method,
        "confidence_selector": confidence_selector_report,
        "confident_accuracy": round(float(confident_accuracy), 6) if confident_accuracy is not None else None,
        "confident_brier": round(float(confident_brier), 6) if confident_brier is not None else None,
        "confident_count": int(confident.sum().detach().cpu().item()),
        "confident_correct_count": int(confident_correct_count),
        "confident_coverage": round(float(confident.float().mean().detach().cpu().item()), 6),
        "validation_confident_target_met": bool(float((best.get("confidence_band") or {}).get("accuracy") or 0.0) >= float(target_accuracy)),
        "confident_target_met": bool(confident_accuracy is not None and float(confident_accuracy) >= float(target_accuracy)),
        "test_oracle_coverage_at_target_accuracy": round(float(test_oracle_coverage_at_target["coverage"]), 6),
        "test_oracle_count_at_target_accuracy": int(test_oracle_coverage_at_target["count"]),
        "test_oracle_target_accuracy": round(float(target_accuracy), 6),
        "test_oracle_note": "Oracle coverage is selected on the test labels for research only; deployable confidence uses validation-selected thresholds.",
        "feature_selection": feature_selection,
        "candidate_reports": candidate_reports,
        "candidate_warnings": candidate_warnings,
    }


def _add_cross_section_features(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    out = data.copy()
    grouped = out.groupby("date", sort=False)
    rank_sources = {
        "cs_ret_1_rank": "ret_1",
        "cs_turnover_rank": "turnover",
        "cs_amount_z_rank": "amount_z_20",
        "cs_volume_z_rank": "volume_z_20",
        "cs_range_rank": "range_pct",
        "cs_volatility_rank": "ret_std_10",
    }
    for target, source in rank_sources.items():
        out[target] = grouped[source].rank(pct=True).fillna(0.5).astype(float)
    out["cs_market_positive_rate"] = grouped["ret_1"].transform(lambda values: float((values > 0).mean()))
    out["cs_market_mean_ret_1"] = grouped["ret_1"].transform("mean").fillna(0.0)
    out["cs_market_mean_range"] = grouped["range_pct"].transform("mean").fillna(0.0)
    out["cs_short_pool_size_log"] = np.log1p(grouped["symbol"].transform("count").astype(float))
    hot_score = out["amount_z_20"] + out["turnover_z_20"] + out["range_pct"] / 10.0
    out["cs_hot_concentration_rank"] = hot_score.groupby(out["date"], sort=False).rank(pct=True).fillna(0.5).astype(float)
    out["cs_limit_up_rate"] = grouped["limit_up_like"].transform("mean").fillna(0.0)
    out["cs_limit_down_rate"] = grouped["limit_down_like"].transform("mean").fillna(0.0)
    out["cs_big_up_rate"] = grouped["big_up"].transform("mean").fillna(0.0)
    out["cs_big_down_rate"] = grouped["big_down"].transform("mean").fillna(0.0)
    out["cs_failed_limit_up_rate"] = grouped["failed_limit_up"].transform("mean").fillna(0.0)
    out["cs_near_limit_rate"] = grouped["near_limit_close"].transform("mean").fillna(0.0)
    out["cs_hot_mean"] = hot_score.groupby(out["date"], sort=False).transform("mean").fillna(0.0)
    hot_top_decile = hot_score >= hot_score.groupby(out["date"], sort=False).transform(lambda values: values.quantile(0.90))
    hot_top_values = hot_score.where(hot_top_decile, np.nan)
    out["cs_hot_top_decile_mean"] = hot_top_values.groupby(out["date"], sort=False).transform("mean").fillna(out["cs_hot_mean"])
    out["cs_emotion_score"] = (
        out["cs_limit_up_rate"] * 2.0
        + out["cs_big_up_rate"]
        + out["cs_near_limit_rate"]
        + out["cs_hot_top_decile_mean"] * 0.1
        - out["cs_limit_down_rate"] * 2.0
        - out["cs_big_down_rate"]
        - out["cs_failed_limit_up_rate"] * 0.5
    )
    out["rel_ret_1_to_market"] = out["ret_1"] - out["cs_market_mean_ret_1"]
    out["rel_range_to_market"] = out["range_pct"] / np.maximum(out["cs_market_mean_range"].abs(), 1e-6)
    out["volume_z_x_cs_ret_rank"] = out["volume_z_20"] * out["cs_ret_1_rank"]
    out["close_pos_x_cs_range_rank"] = out["close_position"] * out["cs_range_rank"]
    out["cs_price_rank"] = grouped["close"].rank(pct=True).fillna(0.5).astype(float)
    weak_market_pressure = (
        (1.0 - out["cs_market_positive_rate"]).clip(lower=0.0)
        + np.maximum(-out["cs_market_mean_ret_1"], 0.0) / 5.0
        + out["cs_limit_down_rate"] * 2.0
    )
    active_strength = (
        np.maximum(out["ret_1"], 0.0) / 10.0
        + out["near_limit_close"].astype(float)
        + out["close_position"].astype(float)
    )
    out["cs_low_price_advantage"] = (1.0 - out["cs_price_rank"]) * weak_market_pressure * active_strength
    out["cs_weak_market_focus"] = weak_market_pressure * out["cs_hot_concentration_rank"] * (
        out["close_position"].astype(float) + out["near_limit_close"].astype(float)
    )
    out["cs_stock_leads_index_rebound"] = (
        np.maximum(out["rel_ret_1_to_market"], 0.0)
        / 10.0
        * out["cs_ret_1_rank"]
        * weak_market_pressure
        * out["close_position"].astype(float)
    )
    reversal_market = (
        (out["cs_market_mean_ret_1"] > 0.0).astype(float)
        * (out["cs_market_positive_rate"] >= 0.55).astype(float)
        * (out["cs_limit_down_rate"] <= out["cs_limit_up_rate"] + 1e-6).astype(float)
    )
    out["cs_reversal_day_leader_quality"] = reversal_market * out["cs_ret_1_rank"] * out["close_position"].astype(float) * (
        1.0 + np.maximum(out["volume_z_20"], 0.0) / 3.0
    )
    out["cs_emotion_bull_signal"] = (
        (out["cs_market_positive_rate"] >= 0.55).astype(float)
        * (out["cs_limit_up_rate"] * 2.0 + out["cs_big_up_rate"] + out["cs_near_limit_rate"] + out["cs_hot_top_decile_mean"] * 0.1)
        * out["cs_ret_1_rank"]
    )
    date_level = (
        out.groupby("date", sort=True)
        .agg(
            market_ret=("ret_1", "mean"),
            positive_rate=("ret_1", lambda values: float((values > 0).mean())),
            limit_up_rate=("limit_up_like", "mean"),
            failed_rate=("failed_limit_up", "mean"),
            big_down_rate=("big_down", "mean"),
        )
        .sort_index()
    )
    prior_weak = date_level["market_ret"].shift(1).rolling(3, min_periods=1).sum() <= -1.5
    rebound_not_bottom = (
        prior_weak.astype(float)
        * (date_level["market_ret"] >= 0.8).astype(float)
        * (1.0 - date_level["limit_up_rate"].clip(lower=0.0, upper=0.20) * 5.0)
        * (1.0 + date_level["failed_rate"] * 2.0 + date_level["big_down_rate"])
        * (date_level["positive_rate"] < 0.65).astype(float)
    )
    out["cs_strong_rebound_not_bottom_risk"] = out["date"].map(rebound_not_bottom).fillna(0.0).astype(float)
    cycle_day = _data_numeric(out, "cycle_day_count")
    failed_rate = _data_numeric(out, "market_failed_limit_up_rate")
    broken_count = _data_numeric(out, "market_broken_board_count")
    seal_rate = _data_numeric(out, "market_seal_rate")
    seal80 = _data_numeric(out, "seal_rate_80_threshold")
    emotion_score = _data_numeric(out, "market_emotion_score")
    new_high_count = _data_numeric(out, "market_new_high_20_count")
    day_cos = _data_numeric(out, "day_of_week_cos")
    strong_market = np.maximum(
        _data_numeric(out, "strong_market_regime"),
        ((out["cs_market_mean_ret_1"] >= 0.80) & (out["cs_market_positive_rate"] >= 0.55)).astype(float),
    )
    weak_oversold = np.maximum(
        _data_numeric(out, "weak_market_oversold_regime"),
        (
            (out["cs_market_positive_rate"] <= 0.45)
            & ((_data_numeric(out, "market_limit_down_count") >= 5.0) | (_data_numeric(out, "market_new_low_20_count") > _data_numeric(out, "market_new_high_20_count")))
        ).astype(float),
    )
    chase_strength = (
        (out["ret_1"] >= 3.0).astype(float)
        * out["close_position"].astype(float)
        * (1.0 + np.maximum(out["volume_z_20"], 0.0) / 3.0)
    )
    second_board = _data_numeric(out, "second_board_entry")
    amount_300m = _data_numeric(out, "daily_amount_300m_gate")
    volume_match = _data_numeric(out, "volume_price_match")
    dist_low_20 = _data_numeric(out, "dist_low_20")
    lower_shadow = _data_numeric(out, "lower_shadow_pct")
    money_spread = _data_numeric(out, "money_effect_spread_20")
    top20_win_rate = _data_numeric(out, "prev_top20_chase_win_rate")
    bottom20_rebound = _data_numeric(out, "prev_bottom20_rebound_return")
    collapse_warning = _data_numeric(out, "collapse_warning_signal")
    hot_exhaustion = _data_numeric(out, "hot_exhaustion_score")
    limit_streak = _data_numeric(out, "limit_up_streak")
    cycle_gate = (cycle_day >= 3.0).astype(float)
    hot_gate = (_data_numeric(out, "market_limit_up_count") >= 40.0).astype(float)
    out["market_cycle_failed_pressure"] = cycle_gate * failed_rate * np.log1p(np.maximum(broken_count, 0.0))
    out["market_cycle_broken_pressure"] = cycle_gate * np.log1p(np.maximum(broken_count, 0.0)) * (
        1.0 + np.maximum(emotion_score, 0.0) / 50.0
    )
    out["market_cycle_seal_pressure"] = cycle_gate * seal_rate * (1.0 + np.maximum(emotion_score, 0.0) / 50.0)
    out["market_monday_hot_new_high_risk"] = (day_cos >= 0.90).astype(float) * np.log1p(
        np.maximum(new_high_count, 0.0)
    ) * hot_gate
    out["market_hot_cycle_short_pressure"] = cycle_gate * hot_gate * (
        failed_rate + np.maximum(_data_numeric(out, "cs_emotion_score"), 0.0) / 10.0
    )
    out["chase_market_up_alignment"] = chase_strength * (strong_market - weak_oversold)
    out["strong_market_anti_drop"] = strong_market * (
        (out["ret_1"] >= -1.0).astype(float)
        * (out["rel_ret_1_to_market"] >= -1.0).astype(float)
        * out["close_position"].astype(float)
        * (1.0 + amount_300m)
    )
    out["weak_market_oversold_rebound"] = weak_oversold * (
        (dist_low_20 <= 0.08).astype(float)
        * (lower_shadow + np.maximum(out["ret_1"], 0.0) / 10.0)
        * (1.0 + np.maximum(out["volume_z_20"], 0.0) / 3.0)
    )
    out["second_board_leader_proxy"] = second_board * out["cs_ret_1_rank"] * (1.0 - failed_rate) * (
        1.0 + np.maximum(_data_numeric(out, "market_max_board_height") - 2.0, 0.0) / 5.0
    )
    out["seal80_second_board_quality"] = seal80 * second_board * out["close_position"].astype(float) * (
        1.0 + amount_300m + np.maximum(volume_match, 0.0)
    )
    out["bull_hotspot_bear_oversold_signal"] = _data_numeric(out, "bull_hotspot_bear_oversold") * (
        out["near_limit_close"].astype(float)
        + np.maximum(out["rel_ret_1_to_market"], 0.0) / 10.0
        + ((dist_low_20 <= 0.08).astype(float) * lower_shadow)
    )
    out["money_effect_chase_alignment"] = chase_strength * (
        np.clip(money_spread / 5.0, -2.0, 2.0) + np.clip(top20_win_rate - 0.5, -0.5, 0.5)
    )
    out["collapse_hot_stock_risk"] = collapse_warning * (
        out["near_limit_close"].astype(float)
        + np.maximum(hot_exhaustion, 0.0)
        + np.maximum(limit_streak - 1.0, 0.0)
    )
    out["weak_rebound_money_effect"] = weak_oversold * np.maximum(bottom20_rebound, 0.0) / 5.0 * (
        (dist_low_20 <= 0.08).astype(float) + lower_shadow
    )
    return out


def _data_numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(0.0, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float)


def _daily_context_slice(bars: pd.DataFrame, *, symbol: str, start: date, end: date) -> pd.DataFrame:
    if bars.empty or "date" not in bars.columns:
        return pd.DataFrame()
    columns = [column for column in ("date", "open", "high", "low", "close", "volume", "amount", "turnover") if column in bars.columns]
    if "date" not in columns:
        return pd.DataFrame()
    frame = bars.loc[:, columns].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"])
    frame = frame[(frame["date"].dt.date >= start) & (frame["date"].dt.date <= end)].reset_index(drop=True)
    if frame.empty:
        return pd.DataFrame()
    frame["symbol"] = str(symbol).zfill(6)
    return frame


def _attach_free_factor_features(
    data: pd.DataFrame,
    *,
    daily_context_frames: list[pd.DataFrame],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    reports: list[dict[str, Any]] = []
    if data.empty or not daily_context_frames:
        return data, reports
    daily_context = pd.concat(daily_context_frames, ignore_index=True)
    try:
        market_factor = build_market_emotion_factor(daily_context)
        board_factor = build_board_structure_factor(daily_context)
        merged, reports = merge_factor_frames(data, [market_factor, board_factor])
    except Exception as exc:
        out = data.copy()
        for column in GPU_PROBE_ALL_DAILY_FACTOR_FEATURES:
            out[column] = 0.0
        reports.append(
            {
                "name": "daily_free_factor_proxy",
                "source": "local_daily_cache",
                "asof_time": "after_close",
                "lag_rule": "T day close-derived free factors; use for T+1 prediction only",
                "coverage_rate": 0.0,
                "status": "failed",
                "error": str(exc),
                "columns": list(GPU_PROBE_ALL_DAILY_FACTOR_FEATURES),
            }
        )
        return out, reports
    return merged, reports


def _attach_cached_market_index_features(
    data: pd.DataFrame,
    *,
    store: LocalDataStore,
    config: GpuProbeConfig,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    reports: list[dict[str, Any]] = []
    index_frames: dict[str, pd.DataFrame] = {}
    loader = getattr(store, "load_market_index", None)
    if not callable(loader):
        return _zero_market_index_features(data, status="missing_loader")
    for symbol in GPU_PROBE_MARKET_INDEX_SYMBOLS:
        try:
            frame = loader(symbol, "daily")
        except TypeError:
            try:
                frame = loader(symbol)
            except Exception:
                frame = pd.DataFrame()
        except Exception:
            frame = pd.DataFrame()
        if frame is None or frame.empty:
            continue
        frame = frame.copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"])
        frame = frame[(frame["date"].dt.date >= config.start) & (frame["date"].dt.date <= config.end)]
        if not frame.empty:
            index_frames[symbol] = frame
    if not index_frames:
        return _zero_market_index_features(data, status="no_cached_index_data")
    try:
        factor = build_cross_market_return_factor(index_frames)
        merged, reports = merge_factor_frames(data, [factor])
    except Exception as exc:
        out, reports = _zero_market_index_features(data, status="failed")
        reports[0]["error"] = str(exc)
        return out, reports
    return merged, reports


def _zero_market_index_features(data: pd.DataFrame, *, status: str) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    out = data.copy()
    for column in GPU_PROBE_CROSS_MARKET_FEATURES:
        out[column] = 0.0
        out[f"{column}_available"] = 0.0
    return out, [
        {
            "name": "cross_market_returns",
            "source": "free_index_cache",
            "asof_time": "source_close_time",
            "lag_rule": "local A-share index close-derived; use for T+1 prediction only",
            "coverage_rate": 0.0,
            "status": status,
            "columns": list(GPU_PROBE_CROSS_MARKET_FEATURES),
            "availability_columns": [f"{column}_available" for column in GPU_PROBE_CROSS_MARKET_FEATURES],
        }
    ]


def _ensure_feature_columns(data: pd.DataFrame) -> pd.DataFrame:
    out = data.copy()
    for column in GPU_PROBE_ALL_FEATURES:
        if column not in out.columns:
            out[column] = 0.0
        out[column] = pd.to_numeric(out[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return out


def _feature_names_for_config(config: GpuProbeConfig) -> tuple[str, ...]:
    feature_set = str(config.feature_set or "expanded").strip().lower()
    if feature_set == "legacy":
        return GPU_PROBE_LEGACY_FEATURES
    if feature_set == "base":
        return GPU_PROBE_BASE_FEATURES
    if feature_set == "expanded":
        return GPU_PROBE_STABLE_FEATURES
    if feature_set == "research":
        return GPU_PROBE_RESEARCH_FEATURES
    raise ValueError("feature_set must be one of: legacy, base, expanded, research")


def _validate_config(config: GpuProbeConfig) -> list[str]:
    errors: list[str] = []
    if config.start > config.train_end:
        errors.append("start must be on or before train_end.")
    if config.train_end >= config.test_start:
        errors.append("train_end must be earlier than test_start to keep holdout labels out of training.")
    if config.test_start > config.end:
        errors.append("test_start must be on or before end.")
    if int(config.train_rows) <= 0:
        errors.append("train_rows must be positive.")
    if int(config.test_rows) <= 0:
        errors.append("test_rows must be positive.")
    if float(config.target_accuracy) <= 0.0 or float(config.target_accuracy) > 1.0:
        errors.append("target_accuracy must be in (0, 1].")
    if int(config.max_selected_features) <= 0:
        errors.append("max_selected_features must be positive.")
    return errors


def _effective_target_accuracy(config: GpuProbeConfig) -> float:
    return max(float(config.target_accuracy), MIN_GPU_PROBE_TARGET_ACCURACY)


def _effective_required_test_rows(config: GpuProbeConfig) -> int:
    return max(int(config.test_rows), MIN_GPU_PROBE_TEST_ROWS)


def _probe_split_manifest(
    config: GpuProbeConfig,
    *,
    train: pd.DataFrame,
    test: pd.DataFrame,
    training_result: dict[str, Any],
) -> dict[str, Any]:
    manifest = {
        "protocol": "dev_train_dev_valid_test_lockbox_v1",
        "dev_train_rule": "label_date <= train_end, then validation is carved out by label_date with trading-day embargo",
        "test_lockbox_rule": "event date >= test_start and label_date <= end",
        "train_end": config.train_end.isoformat(),
        "test_start": config.test_start.isoformat(),
        "end": config.end.isoformat(),
        "validation_fraction": float(config.validation_fraction),
        "embargo_trading_days": int(config.embargo_label_days),
        "row_split_fallback_used": False,
        "train_window_rows": int(training_result.get("train_window_rows", len(train))),
        "fit_rows": int(training_result.get("fit_rows", 0)),
        "validation_rows": int(training_result.get("validation_rows", 0)),
        "test_lockbox_rows": int(len(test)),
        "validation_start": training_result.get("validation_start"),
        "fit_label_end": training_result.get("fit_label_end"),
        "test_event_start": _frame_date_min(test, "date"),
        "test_event_end": _frame_date_max(test, "date"),
        "test_label_end": _frame_date_max(test, "label_date"),
        "lockbox_tuning_allowed": False,
    }
    manifest["split_hash"] = _stable_hash(manifest)
    return manifest


def _acceptance_summary(
    result: dict[str, Any],
    *,
    test_rows: int,
    required_test_rows: int,
    target_accuracy: float,
    future_label_filter_used: bool = False,
) -> dict[str, Any]:
    return build_prediction_acceptance(
        result,
        test_rows=test_rows,
        required_test_rows=required_test_rows,
        target_accuracy=target_accuracy,
        future_label_filter_used=future_label_filter_used,
        thresholds=AcceptanceThresholds(
            target_accuracy=float(target_accuracy),
            desired_lockbox_rows=DESIRED_GPU_PROBE_TEST_ROWS,
            high_confidence_min_rows=MIN_GPU_PROBE_HIGH_CONFIDENCE_ROWS,
            high_confidence_min_coverage=MIN_GPU_PROBE_HIGH_CONFIDENCE_COVERAGE,
            statistical_min_rows=MIN_GPU_PROBE_STATISTICAL_ROWS,
        ),
    )


def _write_gpu_probe_artifacts(store: LocalDataStore, result: dict[str, Any]) -> dict[str, str]:
    config = getattr(store, "config", None)
    storage = getattr(config, "storage", None)
    report_dir = getattr(storage, "report_dir", None)
    if report_dir is None:
        return {}
    directory = Path(report_dir) / "prediction"
    directory.mkdir(parents=True, exist_ok=True)
    run_id = str(result.get("run_id") or _run_id_for_result(result))
    result["run_id"] = run_id
    result["code_hash"] = _source_hash()
    result["feature_hash"] = _stable_hash({"feature_set": result.get("feature_set"), "features": result.get("features")})
    result["data_hash"] = _stable_hash(
        {
            "rows_total": result.get("rows_total"),
            "symbols_considered": result.get("symbols_considered"),
            "symbol_frames_kept": result.get("symbol_frames_kept"),
            "feature_cache": result.get("feature_cache"),
            "external_factors": result.get("external_factors"),
            "data_loader": result.get("data_loader"),
        }
    )
    result["split_hash"] = _stable_hash(result.get("split_manifest") or {})
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "kind": "gpu_prediction_probe_acceptance",
        "run_id": run_id,
        "code_hash": result["code_hash"],
        "feature_hash": result["feature_hash"],
        "data_hash": result["data_hash"],
        "split_hash": result["split_hash"],
        "result": result,
    }
    run_dir = directory / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = run_dir / "artifact.json"
    _write_json_artifact(artifact_path, payload)
    _write_json_artifact(run_dir / "metrics.json", _metrics_artifact(result))
    _write_json_artifact(run_dir / "split_manifest.json", result.get("split_manifest") or {})
    _write_json_artifact(
        run_dir / "feature_manifest.json",
        {
            "feature_hash": result["feature_hash"],
            "feature_set": result.get("feature_set"),
            "feature_count": result.get("feature_count"),
            "features": result.get("features"),
            "feature_cache": result.get("feature_cache"),
            "external_factors": result.get("external_factors"),
        },
    )
    _write_json_artifact(
        run_dir / "data_snapshot.json",
        {
            "data_hash": result["data_hash"],
            "rows_total": result.get("rows_total"),
            "train_rows": result.get("train_rows"),
            "fit_rows": result.get("fit_rows"),
            "validation_rows": result.get("validation_rows"),
            "test_rows": result.get("test_rows"),
            "symbols_considered": result.get("symbols_considered"),
            "symbol_frames_kept": result.get("symbol_frames_kept"),
            "data_loader": result.get("data_loader"),
        },
    )
    _write_json_artifact(
        run_dir / "leakage_check.json",
        {
            "future_label_filter_used": result.get("future_label_filter_used"),
            "future_label_filter_allowed": False,
            "lockbox_tuning_allowed": False,
            "test_oracle_deployable": False,
            "row_split_fallback_used": bool((result.get("split_manifest") or {}).get("row_split_fallback_used")),
        },
    )
    _write_json_artifact(
        run_dir / "gpu_profile.json",
        {
            "gpu_enabled": result.get("gpu_enabled"),
            "gpu_scope": result.get("gpu_scope"),
            "device": result.get("device"),
            "device_name": result.get("device_name"),
            "full_gpu_pipeline": result.get("full_gpu_pipeline"),
            "cpu_stages": result.get("cpu_stages"),
        },
    )
    _write_json_artifact(
        run_dir / "model_card.json",
        {
            "model": result.get("model"),
            "model_kind": result.get("model_kind"),
            "target_accuracy": result.get("target_accuracy"),
            "acceptance": result.get("acceptance"),
            "scope": "A-share active short-term phases only; not all stocks and not quiet periods.",
            "disabled_conditions": [
                "No active-phase filter hit",
                "Future-label filter enabled",
                "Lockbox used during tuning",
                "External factor asof/lag rule unavailable",
            ],
        },
    )
    pointer_payload = {
        "generated_at": payload["generated_at"],
        "kind": "gpu_prediction_probe_latest_pointer",
        "run_id": run_id,
        "artifact": str(artifact_path),
        "passed": bool((result.get("acceptance") or {}).get("passed")),
        "code_hash": result["code_hash"],
        "feature_hash": result["feature_hash"],
        "data_hash": result["data_hash"],
        "split_hash": result["split_hash"],
    }
    latest_path = directory / "gpu_probe_latest.json"
    _write_json_artifact(latest_path, pointer_payload)
    artifacts = {
        "latest": str(latest_path),
        "run_dir": str(run_dir),
        "artifact": str(artifact_path),
    }
    if bool((result.get("acceptance") or {}).get("passed")):
        passed_path = directory / "gpu_probe_passed_latest.json"
        _write_json_artifact(passed_path, pointer_payload)
        artifacts["passed_latest"] = str(passed_path)
    return artifacts


def _metrics_artifact(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": result.get("run_id"),
        "model": result.get("model"),
        "accuracy": result.get("accuracy"),
        "correct_count": result.get("correct_count"),
        "brier": result.get("brier"),
        "baseline_accuracy": result.get("baseline_accuracy"),
        "baseline_brier": result.get("baseline_brier"),
        "confident_accuracy": result.get("confident_accuracy"),
        "confident_brier": result.get("confident_brier"),
        "confident_count": result.get("confident_count"),
        "confident_correct_count": result.get("confident_correct_count"),
        "confident_coverage": result.get("confident_coverage"),
        "acceptance": result.get("acceptance"),
    }


def _run_id_for_result(result: dict[str, Any]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest = _stable_hash(
        {
            "model": result.get("model"),
            "features": result.get("features"),
            "split_manifest": result.get("split_manifest"),
            "metrics": _metrics_artifact(result),
        }
    )[:8]
    return f"gpu_probe_{timestamp}_{digest}"


def _source_hash() -> str:
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
    except Exception:
        return "unavailable"


def _stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _frame_date_min(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame.columns:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def _frame_date_max(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame.columns:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def _write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp_path.replace(path)


def _feature_cache_descriptor(
    store: LocalDataStore,
    config: GpuProbeConfig,
    *,
    symbols: list[str],
    context_symbols: list[str] | None = None,
) -> dict[str, Any]:
    enabled = bool(config.use_feature_cache)
    config_obj = getattr(store, "config", None)
    storage = getattr(config_obj, "storage", None)
    report_dir = getattr(storage, "report_dir", None)
    descriptor: dict[str, Any] = {
        "enabled": enabled,
        "hit": False,
        "refresh": bool(config.refresh_feature_cache),
    }
    if not enabled or report_dir is None:
        return descriptor
    context_symbols = list(context_symbols or symbols)
    fingerprint_payload = {
        "version": 14,
        "feature_names": list(GPU_PROBE_ALL_FEATURES),
        "start": str(config.start),
        "end": str(config.end),
        "main_board_only": bool(config.main_board_only),
        "short_only": bool(config.short_only),
        "min_turnover": float(config.min_turnover),
        "min_amount": float(config.min_amount),
        "min_volume_z": float(config.min_volume_z),
        "min_amount_z": float(config.min_amount_z),
        "min_range_pct": float(config.min_range_pct),
        "min_volatility_pct": float(config.min_volatility_pct),
        "min_abnormal_flags": int(config.min_abnormal_flags),
        "min_phase_days_3": int(config.min_phase_days_3),
        "min_label_return_pct": float(config.min_label_return_pct),
        "symbols_hash": _hash_payload(sorted(symbols)),
        "symbols_count": len(symbols),
        "context_symbols_hash": _hash_payload(sorted(context_symbols)),
        "context_symbols_count": len(context_symbols),
    }
    fingerprint = _hash_payload(fingerprint_payload)[:16]
    directory = Path(report_dir) / "prediction" / "feature_cache"
    path = directory / f"gpu_probe_features_{fingerprint}.parquet"
    meta_path = directory / f"gpu_probe_features_{fingerprint}.json"
    descriptor.update(
        {
            "fingerprint": fingerprint,
            "path": str(path),
            "metadata_path": str(meta_path),
            "symbols_count": len(symbols),
            "context_symbols_count": len(context_symbols),
            "hit": bool(path.exists() and not config.refresh_feature_cache),
        }
    )
    if descriptor["hit"] and meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            descriptor["rows"] = metadata.get("rows")
            descriptor["symbol_frames_kept"] = metadata.get("symbol_frames_kept")
            descriptor["created_at"] = metadata.get("created_at")
            descriptor["factor_reports"] = metadata.get("factor_reports") or []
        except Exception:
            pass
    return descriptor


def _write_feature_cache(
    descriptor: dict[str, Any],
    data: pd.DataFrame,
    *,
    symbols_considered: int,
    symbol_frames_kept: int,
    factor_reports: list[dict[str, Any]] | None = None,
) -> None:
    if not descriptor.get("enabled") or not descriptor.get("path"):
        return
    path = Path(str(descriptor["path"]))
    meta_path = Path(str(descriptor["metadata_path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    data.to_parquet(tmp_path, index=False)
    tmp_path.replace(path)
    metadata = {
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "fingerprint": descriptor.get("fingerprint"),
        "rows": int(len(data)),
        "columns": list(data.columns),
        "symbols_considered": int(symbols_considered),
        "symbol_frames_kept": int(symbol_frames_kept),
        "factor_reports": factor_reports or [],
    }
    _write_json_artifact(meta_path, metadata)
    descriptor["hit"] = False
    descriptor["rows"] = int(len(data))
    descriptor["symbol_frames_kept"] = int(symbol_frames_kept)
    descriptor["factor_reports"] = factor_reports or []
    descriptor["written"] = True


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _numeric_column(frame: pd.DataFrame, column: str, fallback: Any | None = None) -> np.ndarray:
    if column in frame.columns:
        values = frame[column]
    elif fallback is not None:
        values = fallback
    else:
        values = 0.0
    if not isinstance(values, pd.Series):
        values = pd.Series(values, index=frame.index)
    return pd.to_numeric(values, errors="coerce").fillna(0.0).to_numpy(dtype=np.float32)


class _TorchLogistic:
    def __new__(cls, input_dim: int):
        import torch

        return torch.nn.Linear(input_dim, 1)


class _TorchMlp:
    def __new__(cls, input_dim: int, *, hidden: tuple[int, ...]):
        import torch

        layers: list[torch.nn.Module] = []
        previous = input_dim
        for width in hidden:
            layers.extend(
                [
                    torch.nn.Linear(previous, width),
                    torch.nn.BatchNorm1d(width),
                    torch.nn.SiLU(),
                    torch.nn.Dropout(0.10),
                ]
            )
            previous = width
        layers.append(torch.nn.Linear(previous, 1))
        return torch.nn.Sequential(*layers)


class _TorchResidualMlp:
    def __new__(cls, input_dim: int, *, hidden: int):
        import torch

        class ResidualBlock(torch.nn.Module):
            def __init__(self, width: int) -> None:
                super().__init__()
                self.block = torch.nn.Sequential(
                    torch.nn.Linear(width, width),
                    torch.nn.BatchNorm1d(width),
                    torch.nn.SiLU(),
                    torch.nn.Dropout(0.08),
                    torch.nn.Linear(width, width),
                    torch.nn.BatchNorm1d(width),
                )
                self.activation = torch.nn.SiLU()

            def forward(self, values):
                return self.activation(values + self.block(values))

        return torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden),
            torch.nn.BatchNorm1d(hidden),
            torch.nn.SiLU(),
            ResidualBlock(hidden),
            ResidualBlock(hidden),
            torch.nn.Dropout(0.12),
            torch.nn.Linear(hidden, 1),
        )


def _focal_bce_with_logits(logits, target, *, pos_weight, sample_weight, gamma: float = 1.5):
    import torch

    bce = torch.nn.functional.binary_cross_entropy_with_logits(
        logits,
        target,
        pos_weight=pos_weight,
        reduction="none",
    )
    prob = torch.sigmoid(logits)
    pt = torch.where(target > 0.5, prob, 1.0 - prob)
    focal = torch.pow(torch.clamp(1.0 - pt, min=0.0, max=1.0), gamma)
    return torch.mean(bce * focal * sample_weight)


def _fit_xgboost_candidate(
    x_train,
    y_train,
    x_valid,
    y_valid,
    *,
    device,
    seed: int,
    target_accuracy: float,
    variant: str = "baseline",
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if len(x_train) < 50 or len(x_valid) == 0:
        return {}
    try:
        from xgboost import XGBClassifier
    except Exception:
        return {}

    import torch

    try:
        model_params = {
            "n_estimators": 350,
            "max_depth": 4,
            "learning_rate": 0.03,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "tree_method": "hist",
            "device": "cuda" if device.type == "cuda" else "cpu",
            "random_state": seed,
            "n_jobs": 2,
            "verbosity": 0,
        }
        model_params.update(params or {})
        model = XGBClassifier(**model_params)
        model_name = "gpu_xgboost_hist" if device.type == "cuda" else "xgboost_hist"
        if variant != "baseline":
            model_name = f"{model_name}_{variant}"
        train_x = x_train.detach().cpu().numpy()
        train_y = y_train.flatten().detach().cpu().numpy()
        valid_x = x_valid.detach().cpu().numpy()
        valid_y_np = y_valid.flatten().detach().cpu().numpy()
        model.fit(train_x, train_y, eval_set=[(valid_x, valid_y_np)], verbose=False)
        valid_prob = torch.as_tensor(model.predict_proba(valid_x)[:, 1], device=device, dtype=torch.float32)
        valid_y = y_valid.flatten()
        threshold, valid_accuracy = _best_threshold(valid_prob, valid_y)
        band = _best_confidence_band(
            valid_prob,
            valid_y,
            threshold=threshold,
            target_accuracy=target_accuracy,
            min_count=MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS,
            min_coverage=MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE,
        )
        valid_brier = _brier(valid_prob, valid_y)
        score = _candidate_selection_score(
            valid_accuracy,
            valid_brier,
            band,
            target_accuracy=target_accuracy,
        )
        return {
            "model_name": model_name,
            "model": model,
            "model_kind": "xgboost",
            "selection_score": float(score),
            "validation_accuracy": float(valid_accuracy),
            "validation_brier": float(valid_brier),
            "threshold": float(threshold),
            "confidence_band": band,
            "validation_prob": valid_prob.detach(),
        }
    except Exception as exc:
        return {"warning": f"xgboost_candidate_{variant}_unavailable: {exc}"}


def _fit_lightgbm_candidate(
    x_train,
    y_train,
    x_valid,
    y_valid,
    *,
    device,
    seed: int,
    target_accuracy: float,
    variant: str = "baseline",
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if len(x_train) < 50 or len(x_valid) == 0:
        return {}
    try:
        from lightgbm import LGBMClassifier
    except Exception:
        return {}
    if device.type == "cuda":
        device_params = {"device_type": "gpu"}
        model_name = "gpu_lightgbm"
    else:
        device_params = {"device_type": "cpu"}
        model_name = "lightgbm_cpu_fallback"

    if variant != "baseline":
        model_name = f"{model_name}_{variant}"

    import torch

    try:
        model_params = {
            "n_estimators": 450,
            "learning_rate": 0.025,
            "num_leaves": 31,
            "max_depth": -1,
            "min_child_samples": 80,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "reg_alpha": 0.05,
            "reg_lambda": 1.0,
            "objective": "binary",
            "random_state": seed,
            "n_jobs": 2,
            "verbose": -1,
            **device_params,
        }
        model_params.update(params or {})
        model = LGBMClassifier(**model_params)
        train_x = x_train.detach().cpu().numpy()
        train_y = y_train.flatten().detach().cpu().numpy()
        valid_x = x_valid.detach().cpu().numpy()
        valid_y_np = y_valid.flatten().detach().cpu().numpy()
        model.fit(train_x, train_y, eval_set=[(valid_x, valid_y_np)])
        valid_prob = torch.as_tensor(model.predict_proba(valid_x)[:, 1], device=device, dtype=torch.float32)
        valid_y = y_valid.flatten()
        threshold, valid_accuracy = _best_threshold(valid_prob, valid_y)
        band = _best_confidence_band(
            valid_prob,
            valid_y,
            threshold=threshold,
            target_accuracy=target_accuracy,
            min_count=MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS,
            min_coverage=MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE,
        )
        valid_brier = _brier(valid_prob, valid_y)
        score = _candidate_selection_score(
            valid_accuracy,
            valid_brier,
            band,
            target_accuracy=target_accuracy,
        )
        return {
            "model_name": model_name,
            "model": model,
            "model_kind": "lightgbm",
            "selection_score": float(score),
            "validation_accuracy": float(valid_accuracy),
            "validation_brier": float(valid_brier),
            "threshold": float(threshold),
            "confidence_band": band,
            "validation_prob": valid_prob.detach(),
        }
    except Exception as exc:
        return {"warning": f"lightgbm_candidate_{variant}_unavailable: {exc}"}


def _fit_catboost_candidate(
    x_train,
    y_train,
    x_valid,
    y_valid,
    *,
    device,
    seed: int,
    target_accuracy: float,
    variant: str = "baseline",
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if len(x_train) < 50 or len(x_valid) == 0:
        return {}
    try:
        from catboost import CatBoostClassifier
    except Exception:
        return {}
    task_type = "GPU" if device.type == "cuda" else "CPU"
    model_name = "gpu_catboost" if task_type == "GPU" else "catboost_cpu_fallback"
    if variant != "baseline":
        model_name = f"{model_name}_{variant}"

    import torch

    try:
        model_params = {
            "iterations": 450,
            "depth": 6,
            "learning_rate": 0.025,
            "l2_leaf_reg": 6.0,
            "loss_function": "Logloss",
            "eval_metric": "Logloss",
            "random_seed": seed,
            "task_type": task_type,
            "devices": "0" if task_type == "GPU" else None,
            "verbose": False,
            "allow_writing_files": False,
        }
        model_params.update(params or {})
        model = CatBoostClassifier(**model_params)
        train_x = x_train.detach().cpu().numpy()
        train_y = y_train.flatten().detach().cpu().numpy()
        valid_x = x_valid.detach().cpu().numpy()
        valid_y_np = y_valid.flatten().detach().cpu().numpy()
        model.fit(train_x, train_y, eval_set=(valid_x, valid_y_np), verbose=False)
        valid_prob = torch.as_tensor(model.predict_proba(valid_x)[:, 1], device=device, dtype=torch.float32)
        valid_y = y_valid.flatten()
        threshold, valid_accuracy = _best_threshold(valid_prob, valid_y)
        band = _best_confidence_band(
            valid_prob,
            valid_y,
            threshold=threshold,
            target_accuracy=target_accuracy,
            min_count=MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS,
            min_coverage=MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE,
        )
        valid_brier = _brier(valid_prob, valid_y)
        score = _candidate_selection_score(
            valid_accuracy,
            valid_brier,
            band,
            target_accuracy=target_accuracy,
        )
        return {
            "model_name": model_name,
            "model": model,
            "model_kind": "catboost",
            "selection_score": float(score),
            "validation_accuracy": float(valid_accuracy),
            "validation_brier": float(valid_brier),
            "threshold": float(threshold),
            "confidence_band": band,
            "validation_prob": valid_prob.detach(),
        }
    except Exception as exc:
        return {"warning": f"catboost_candidate_{variant}_unavailable: {exc}"}


def _predict_xgboost_prob(model, x_values, *, device):
    import torch

    values = model.predict_proba(x_values.detach().cpu().numpy())[:, 1]
    return torch.as_tensor(values, device=device, dtype=torch.float32)


def _build_average_ensemble_candidate(
    candidates: list[dict[str, Any]],
    valid_y,
    *,
    target_accuracy: float,
) -> dict[str, Any]:
    if len(candidates) < 2 or len(valid_y) == 0:
        return {}
    members = sorted(candidates, key=lambda item: float(item.get("selection_score") or -999.0), reverse=True)[:3]
    valid_probs = [member.get("validation_prob") for member in members if member.get("validation_prob") is not None]
    if len(valid_probs) < 2:
        return {}
    import torch

    ensemble_prob = torch.stack(valid_probs, dim=0).mean(dim=0)
    threshold, valid_accuracy = _best_threshold(ensemble_prob, valid_y)
    band = _best_confidence_band(
        ensemble_prob,
        valid_y,
        threshold=threshold,
        target_accuracy=target_accuracy,
        min_count=MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS,
        min_coverage=MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE,
    )
    valid_brier = _brier(ensemble_prob, valid_y)
    score = _candidate_selection_score(
        valid_accuracy,
        valid_brier,
        band,
        target_accuracy=target_accuracy,
    )
    return {
        "model_name": "stacking_average_top3",
        "model_kind": "ensemble_average",
        "members": members,
        "selection_score": float(score),
        "validation_accuracy": float(valid_accuracy),
        "validation_brier": float(valid_brier),
        "threshold": float(threshold),
        "confidence_band": band,
        "validation_prob": ensemble_prob.detach(),
        "member_models": [str(member.get("model_name")) for member in members],
    }


def _predict_average_ensemble_prob(candidates: list[dict[str, Any]], x_values, *, device):
    import torch

    probs = [_predict_candidate_prob(candidate, x_values, device=device) for candidate in candidates]
    return torch.stack(probs, dim=0).mean(dim=0)


def _predict_candidate_prob(candidate: dict[str, Any], x_values, *, device):
    import torch

    model_kind = str(candidate.get("model_kind", "torch"))
    model = candidate.get("model")
    if model_kind in {"xgboost", "lightgbm", "catboost"}:
        return _predict_xgboost_prob(model, x_values, device=device)
    if model_kind == "torch":
        model.eval()
        logits = model(x_values).flatten() if len(x_values) else torch.empty(0, device=device)
        return _apply_logit_calibration(logits, candidate.get("calibration") or {"scale": 1.0, "bias": 0.0})
    if model_kind == "ensemble_average":
        return _predict_average_ensemble_prob(candidate.get("members") or [], x_values, device=device)
    raise ValueError(f"Unsupported candidate model kind: {model_kind}")


def _select_training_feature_indices(x_train, y_train, feature_names: tuple[str, ...], *, max_features: int) -> dict[str, Any]:
    import torch

    feature_count = int(x_train.shape[1])
    max_features = max(1, int(max_features))
    if feature_count <= max_features:
        return {
            "enabled": False,
            "method": "train_stable_abs_correlation",
            "input_feature_count": feature_count,
            "selected_feature_count": feature_count,
            "dropped_feature_count": 0,
            "max_features": int(max_features),
            "stability_chunks": 1,
            "top_features": list(feature_names[: min(20, len(feature_names))]),
            "_indices": None,
        }
    target = y_train.to(x_train.dtype)
    centered_target = target - target.mean()
    target_std = torch.clamp(centered_target.std(), min=1e-6)
    global_signed_scores = (x_train * centered_target.view(-1, 1)).mean(dim=0) / target_std
    chunk_count = min(4, max(1, int(len(target) // 2000)))
    chunk_scores = []
    if chunk_count > 1:
        edges = torch.linspace(0, len(target), steps=chunk_count + 1, device=x_train.device).round().to(torch.int64)
        for chunk_index in range(chunk_count):
            start = int(edges[chunk_index].detach().cpu().item())
            end = int(edges[chunk_index + 1].detach().cpu().item())
            if end - start < 50:
                continue
            chunk_target = target[start:end] - target[start:end].mean()
            chunk_std = torch.clamp(chunk_target.std(), min=1e-6)
            chunk_scores.append((x_train[start:end] * chunk_target.view(-1, 1)).mean(dim=0) / chunk_std)
    if chunk_scores:
        chunk_score_tensor = torch.stack(chunk_scores, dim=0)
        median_abs_score = torch.median(torch.abs(chunk_score_tensor), dim=0).values
        global_sign = torch.sign(global_signed_scores).view(1, -1)
        chunk_sign = torch.sign(chunk_score_tensor)
        sign_agreement = (chunk_sign == global_sign).to(torch.float32).mean(dim=0)
        stability_weight = 0.50 + 0.50 * sign_agreement
        scores = (torch.abs(global_signed_scores) * 0.65 + median_abs_score * 0.35) * stability_weight
    else:
        scores = torch.abs(global_signed_scores)
    scores = torch.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
    selected = torch.topk(scores, k=max_features, largest=True, sorted=True).indices
    selected_sorted = torch.sort(selected).values
    top = selected[: min(25, int(selected.numel()))].detach().cpu().tolist()
    selected_names = [feature_names[int(index)] for index in top]
    return {
        "enabled": True,
        "method": "train_stable_abs_correlation",
        "input_feature_count": feature_count,
        "selected_feature_count": int(selected_sorted.numel()),
        "dropped_feature_count": int(feature_count - selected_sorted.numel()),
        "max_features": int(max_features),
        "stability_chunks": int(len(chunk_scores) if chunk_scores else 1),
        "top_features": selected_names,
        "_indices": selected_sorted,
    }


def _candidate_selection_score(
    valid_accuracy: float,
    valid_brier: float,
    confidence_band: dict[str, Any],
    *,
    target_accuracy: float,
) -> float:
    confidence_accuracy = float(confidence_band.get("accuracy") or 0.0)
    confidence_coverage = float(confidence_band.get("coverage") or 0.0)
    total_wilson = float(confidence_band.get("wilson_lower_95") or 0.0)
    stable_wilson = float(confidence_band.get("stability_min_wilson_lower_95") or total_wilson)
    confidence_wilson = total_wilson * 0.60 + stable_wilson * 0.40
    confidence_gap = confidence_wilson - float(target_accuracy)
    return float(
        valid_accuracy
        - valid_brier
        + confidence_accuracy * 0.15
        + confidence_wilson * 0.45
        + min(confidence_coverage, 0.30) * 0.05
        + min(float(confidence_band.get("count") or 0) / 1000.0, 1.0) * 0.02
        + confidence_gap * 0.25
    )


def _candidate_reports(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for candidate in candidates:
        band = candidate.get("confidence_band") or {}
        report = {
            "model": str(candidate.get("model_name")),
            "model_kind": str(candidate.get("model_kind")),
            "selection_score": round(float(candidate.get("selection_score") or 0.0), 6),
            "validation_accuracy": round(float(candidate.get("validation_accuracy") or 0.0), 6),
            "validation_brier": round(float(candidate.get("validation_brier") or 0.0), 6),
            "classification_threshold": round(float(candidate.get("threshold") or 0.5), 6),
            "confidence_accuracy": round(float(band.get("accuracy") or 0.0), 6),
            "confidence_wilson_lower_95": round(float(band.get("wilson_lower_95") or 0.0), 6),
            "confidence_stability_min_wilson_lower_95": round(
                float(band.get("stability_min_wilson_lower_95") or band.get("wilson_lower_95") or 0.0),
                6,
            ),
            "confidence_stability_min_accuracy": round(
                float(band.get("stability_min_accuracy") or band.get("accuracy") or 0.0),
                6,
            ),
            "confidence_coverage": round(float(band.get("coverage") or 0.0), 6),
            "confidence_count": int(band.get("count") or 0),
            "confidence_side": str(band.get("side", "both")),
            "confidence_constraint_met": bool(band.get("constraint_met")),
            "confidence_stable_constraint_met": bool(band.get("stable_constraint_met")),
        }
        if candidate.get("member_models"):
            report["member_models"] = list(candidate.get("member_models") or [])
        reports.append(report)
    return sorted(reports, key=lambda item: float(item["selection_score"]), reverse=True)


def _select_confidence_selector(options: list[tuple[dict[str, Any], Any]]) -> tuple[dict[str, Any], Any]:
    if not options:
        raise ValueError("At least one confidence selector is required.")

    def _count(report: dict[str, Any]) -> int:
        return int(report.get("validation_count") or 0)

    def _coverage(report: dict[str, Any]) -> float:
        return float(report.get("validation_coverage") or 0.0)

    eligible = [(report, mask) for report, mask in options if bool(report.get("eligible"))]
    constrained = [
        (report, mask)
        for report, mask in options
        if _count(report) >= MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS
        and _coverage(report) >= MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE
    ]
    usable = [(report, mask) for report, mask in options if _count(report) > 0]
    pool = eligible or constrained or usable or options
    return max(pool, key=lambda item: _confidence_selector_score(item[0]))


def _confidence_selector_score(report: dict[str, Any]) -> float:
    accuracy = float(report.get("validation_accuracy") or 0.0)
    total_wilson = float(report.get("validation_wilson_lower_95") or 0.0)
    stable_wilson = float(report.get("validation_stability_min_wilson_lower_95") or total_wilson)
    wilson = total_wilson * 0.55 + stable_wilson * 0.45
    coverage = float(report.get("validation_coverage") or 0.0)
    count_bonus = min(float(report.get("validation_count") or 0) / 1000.0, 1.0) * 0.02
    target_bonus = 0.08 if bool(report.get("eligible")) else 0.0
    method = str(report.get("method") or "")
    method_bonus = 0.0
    if method == "candidate_agreement":
        method_bonus = 0.035
    elif method == "meta_correctness":
        method_bonus = 0.015
    unstable_probability_penalty = 0.0
    if method == "probability_band" and not bool(report.get("eligible")):
        stability_gap = max(total_wilson - stable_wilson, 0.0)
        unstable_probability_penalty = min(0.05, stability_gap)
    return float(
        wilson
        + accuracy * 0.20
        + min(coverage, 0.30) * 0.08
        + count_bonus
        + target_bonus
        + method_bonus
        - unstable_probability_penalty
    )


def _fit_agreement_confidence_selector(
    candidates: list[dict[str, Any]],
    x_valid,
    y_valid,
    best_valid_prob,
    x_test,
    best_test_prob,
    *,
    threshold: float,
    target_accuracy: float,
) -> dict[str, Any]:
    import torch

    if len(y_valid) < 400 or len(x_test) == 0:
        return {}
    selected_candidates = [
        candidate
        for candidate in sorted(candidates, key=lambda item: float(item.get("selection_score") or -999.0), reverse=True)
        if candidate.get("model_kind") in {"torch", "xgboost", "lightgbm", "catboost", "ensemble_average"}
    ][:5]
    if len(selected_candidates) < 2:
        return {}

    valid_probs = []
    test_probs = []
    thresholds = []
    model_names: list[str] = []
    for candidate in selected_candidates:
        try:
            valid_prob = candidate.get("validation_prob")
            if valid_prob is None or len(valid_prob) != len(y_valid):
                valid_prob = _predict_candidate_prob(candidate, x_valid, device=x_valid.device) if len(x_valid) else torch.empty(0, device=x_valid.device)
            test_prob = _predict_candidate_prob(candidate, x_test, device=x_test.device)
        except Exception:
            continue
        if len(valid_prob) != len(y_valid) or len(test_prob) != len(x_test):
            continue
        valid_probs.append(valid_prob.detach().flatten())
        test_probs.append(test_prob.detach().flatten())
        thresholds.append(float(candidate.get("threshold") or 0.5))
        model_names.append(str(candidate.get("model_name")))
    if len(valid_probs) < 2:
        return {}

    threshold_tensor = torch.as_tensor(thresholds, device=x_valid.device, dtype=torch.float32).view(-1, 1)
    valid_prob_matrix = torch.stack(valid_probs, dim=0)
    test_prob_matrix = torch.stack(test_probs, dim=0)
    valid_pred_matrix = valid_prob_matrix >= threshold_tensor
    test_pred_matrix = test_prob_matrix >= threshold_tensor.to(test_prob_matrix.device)

    valid_vote_pos = valid_pred_matrix.to(torch.float32).mean(dim=0)
    test_vote_pos = test_pred_matrix.to(torch.float32).mean(dim=0)
    valid_agreement = torch.maximum(valid_vote_pos, 1.0 - valid_vote_pos)
    test_agreement = torch.maximum(test_vote_pos, 1.0 - test_vote_pos)
    valid_margin = torch.abs(valid_prob_matrix - threshold_tensor).mean(dim=0)
    test_margin = torch.abs(test_prob_matrix - threshold_tensor.to(test_prob_matrix.device)).mean(dim=0)
    valid_majority = valid_vote_pos >= 0.5
    test_majority = test_vote_pos >= 0.5
    valid_best_pred = best_valid_prob.flatten() >= float(threshold)
    test_best_pred = best_test_prob.flatten() >= float(threshold)
    valid_side_match = valid_majority == valid_best_pred
    test_side_match = test_majority == test_best_pred
    correct = (valid_best_pred.to(y_valid.dtype) == y_valid.flatten()).to(torch.float32)

    agreement_thresholds = torch.linspace(0.60, 1.0, steps=9, device=x_valid.device)
    margin_thresholds = torch.linspace(0.00, 0.30, steps=61, device=x_valid.device)
    agreement_grid = agreement_thresholds.repeat_interleave(len(margin_thresholds))
    margin_grid = margin_thresholds.repeat(len(agreement_thresholds))
    selected = (
        (valid_agreement.view(1, -1) >= agreement_grid.view(-1, 1))
        & (valid_margin.view(1, -1) >= margin_grid.view(-1, 1))
        & valid_side_match.view(1, -1)
    )
    counts = selected.sum(dim=1)
    selected_correct = (selected.to(torch.float32) * correct.view(1, -1)).sum(dim=1)
    accuracies = selected_correct / torch.clamp(counts.to(torch.float32), min=1.0)
    coverages = counts.to(torch.float32) / max(float(len(correct)), 1.0)
    wilson = _torch_wilson_lower(selected_correct, counts)
    valid = (counts >= MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS) & (
        coverages >= MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE
    )
    fallback_valid = counts > 0
    passing = valid & (wilson >= float(target_accuracy))
    if torch.any(passing):
        masked_coverage = torch.where(passing, coverages, torch.full_like(coverages, -1.0))
        index = int(torch.argmax(masked_coverage).detach().cpu().item())
    else:
        candidate_valid = valid if torch.any(valid) else fallback_valid
        masked_wilson = torch.where(candidate_valid, wilson, torch.full_like(wilson, -1.0))
        max_wilson = torch.max(masked_wilson)
        tied = candidate_valid & torch.isclose(wilson, max_wilson)
        masked_coverage = torch.where(tied, coverages, torch.full_like(coverages, -1.0))
        index = int(torch.argmax(masked_coverage).detach().cpu().item())

    agreement_threshold = float(agreement_grid[index].detach().cpu().item())
    margin_threshold = float(margin_grid[index].detach().cpu().item())
    test_mask = (
        (test_agreement >= agreement_threshold)
        & (test_margin >= margin_threshold)
        & test_side_match
    )
    return {
        "method": "candidate_agreement",
        "eligible": bool(valid[index].detach().cpu().item() and (wilson[index] >= float(target_accuracy)).detach().cpu().item()),
        "validation_accuracy": float(accuracies[index].detach().cpu().item()),
        "validation_wilson_lower_95": float(wilson[index].detach().cpu().item()),
        "validation_coverage": float(coverages[index].detach().cpu().item()),
        "validation_count": int(counts[index].detach().cpu().item()),
        "validation_target_wilson_met": bool((wilson[index] >= float(target_accuracy)).detach().cpu().item()),
        "agreement_threshold": agreement_threshold,
        "margin_threshold": margin_threshold,
        "side_match_required": True,
        "models": model_names,
        "test_mask": test_mask,
    }


def _fit_meta_confidence_selector(
    x_valid,
    y_valid,
    valid_prob,
    x_test,
    test_prob,
    *,
    threshold: float,
    target_accuracy: float,
    seed: int,
) -> dict[str, Any]:
    import torch

    if len(y_valid) < 400 or len(x_test) == 0:
        return {}
    torch.manual_seed(int(seed) + 91)
    ordered_count = int(len(y_valid))
    split = min(max(int(ordered_count * 0.55), 100), ordered_count - 100)
    if split <= 0 or split >= ordered_count:
        return {}
    correct = ((valid_prob >= float(threshold)).to(y_valid.dtype) == y_valid).to(torch.float32)
    meta_x = _meta_confidence_features(x_valid, valid_prob, threshold=threshold).detach()
    train_x = meta_x[:split]
    train_y = correct[:split].view(-1, 1)
    select_x = meta_x[split:]
    select_y = correct[split:]
    if len(train_x) < 100 or len(select_x) < 100:
        return {}

    model = torch.nn.Sequential(
        torch.nn.Linear(train_x.shape[1], 64),
        torch.nn.SiLU(),
        torch.nn.Dropout(0.08),
        torch.nn.Linear(64, 1),
    ).to(train_x.device)
    pos_rate = torch.clamp(train_y.mean(), min=1e-4, max=1.0 - 1e-4)
    pos_weight = (1.0 - pos_rate) / pos_rate
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.004, weight_decay=2e-4)
    for _ in range(90):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        logits = model(train_x)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, train_y, pos_weight=pos_weight)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        select_score = torch.sigmoid(model(select_x)).flatten()
        selector = _best_meta_confidence_threshold(
            select_score,
            select_y,
            target_accuracy=target_accuracy,
            min_count=MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS,
            min_coverage=MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE,
        )
        test_x = _meta_confidence_features(x_test, test_prob, threshold=threshold)
        test_score = torch.sigmoid(model(test_x)).flatten()
        test_mask = test_score >= float(selector["threshold"])
    return {
        "method": "meta_correctness",
        "eligible": bool(selector.get("constraint_met") and selector.get("target_wilson_met")),
        "validation_accuracy": float(selector["accuracy"]),
        "validation_wilson_lower_95": float(selector.get("wilson_lower_95") or 0.0),
        "validation_coverage": float(selector["coverage"]),
        "validation_count": int(selector["count"]),
        "validation_target_wilson_met": bool(selector.get("target_wilson_met")),
        "threshold": float(selector["threshold"]),
        "train_rows": int(len(train_x)),
        "selection_rows": int(len(select_x)),
        "test_mask": test_mask,
    }


def _fit_regime_confidence_selector(
    x_valid,
    y_valid,
    valid_prob,
    x_test,
    test_prob,
    *,
    threshold: float,
    target_accuracy: float,
    feature_names: tuple[str, ...],
) -> dict[str, Any]:
    import torch

    if len(y_valid) < 400 or len(x_test) == 0 or not feature_names:
        return {}
    regime_indices = _regime_feature_indices(feature_names)
    if not regime_indices:
        return {}
    device = x_valid.device
    correct = ((valid_prob >= float(threshold)).to(y_valid.dtype) == y_valid.flatten()).to(torch.float32)
    margins = torch.as_tensor([0.00, 0.03, 0.06, 0.09, 0.12, 0.15, 0.20], device=device, dtype=x_valid.dtype)
    quantiles = torch.as_tensor([0.15, 0.25, 0.35, 0.65, 0.75, 0.85], device=device, dtype=x_valid.dtype)
    prob_masks: list[tuple[str, float, Any, Any]] = []
    for margin in margins:
        margin_value = float(margin.detach().cpu().item())
        low = float(max(float(threshold) - margin_value, 0.02))
        high = float(min(float(threshold) + margin_value, 0.98))
        prob_masks.append(("all", margin_value, torch.ones_like(valid_prob, dtype=torch.bool), torch.ones_like(test_prob, dtype=torch.bool)))
        prob_masks.append(("both", margin_value, (valid_prob <= low) | (valid_prob >= high), (test_prob <= low) | (test_prob >= high)))
        prob_masks.append(("long", margin_value, valid_prob >= high, test_prob >= high))
        prob_masks.append(("short", margin_value, valid_prob <= low, test_prob <= low))

    best_eligible: tuple[dict[str, Any], Any] | None = None
    best_constrained: tuple[dict[str, Any], Any] | None = None
    best_usable: tuple[dict[str, Any], Any] | None = None
    n_valid = max(float(len(y_valid)), 1.0)
    for feature_index in regime_indices[:96]:
        valid_values = x_valid[:, feature_index]
        test_values = x_test[:, feature_index]
        if torch.nan_to_num(valid_values.std(), nan=0.0).detach().cpu().item() <= 1e-6:
            continue
        try:
            thresholds = torch.quantile(valid_values, quantiles)
        except Exception:
            continue
        for quantile_index, quantile in enumerate(quantiles.detach().cpu().tolist()):
            cutoff = thresholds[quantile_index]
            if float(quantile) <= 0.50:
                feature_valid = valid_values <= cutoff
                feature_test = test_values <= cutoff
                feature_side = "low"
            else:
                feature_valid = valid_values >= cutoff
                feature_test = test_values >= cutoff
                feature_side = "high"
            for probability_side, margin_value, valid_prob_mask, test_prob_mask in prob_masks:
                selected = feature_valid & valid_prob_mask
                counts = selected.sum()
                if int(counts.detach().cpu().item()) <= 0:
                    continue
                coverage = counts.to(torch.float32) / n_valid
                selected_correct = (selected.to(torch.float32) * correct).sum()
                accuracy = selected_correct / torch.clamp(counts.to(torch.float32), min=1.0)
                wilson = _torch_wilson_lower(selected_correct, counts)
                report = {
                    "method": "regime_probability_gate",
                    "eligible": bool(
                        int(counts.detach().cpu().item()) >= MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS
                        and float(coverage.detach().cpu().item()) >= MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE
                        and float(wilson.detach().cpu().item()) >= float(target_accuracy)
                    ),
                    "validation_accuracy": float(accuracy.detach().cpu().item()),
                    "validation_wilson_lower_95": float(wilson.detach().cpu().item()),
                    "validation_coverage": float(coverage.detach().cpu().item()),
                    "validation_count": int(counts.detach().cpu().item()),
                    "validation_target_wilson_met": bool(float(wilson.detach().cpu().item()) >= float(target_accuracy)),
                    "feature": str(feature_names[feature_index]),
                    "feature_side": feature_side,
                    "feature_quantile": float(quantile),
                    "feature_threshold_standardized": float(cutoff.detach().cpu().item()),
                    "probability_side": probability_side,
                    "probability_margin": float(margin_value),
                }
                test_mask = feature_test & test_prob_mask
                constrained = (
                    int(report["validation_count"]) >= MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS
                    and float(report["validation_coverage"]) >= MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE
                )
                candidate = (report, test_mask)
                if bool(report["eligible"]) and (
                    best_eligible is None
                    or _confidence_selector_score(report) > _confidence_selector_score(best_eligible[0])
                ):
                    best_eligible = candidate
                if constrained and (
                    best_constrained is None
                    or _confidence_selector_score(report) > _confidence_selector_score(best_constrained[0])
                ):
                    best_constrained = candidate
                if best_usable is None or _confidence_selector_score(report) > _confidence_selector_score(best_usable[0]):
                    best_usable = candidate
    selected = best_eligible or best_constrained or best_usable
    if selected is None:
        return {}
    return {**selected[0], "test_mask": selected[1]}


def _regime_feature_indices(feature_names: tuple[str, ...]) -> list[int]:
    prefixes = (
        "market_",
        "emotion_",
        "cs_",
        "cross_",
        "prev_",
        "consecutive_",
        "day_of_week_",
        "month_",
    )
    keywords = (
        "phase",
        "premium",
        "limit",
        "board",
        "rebound",
        "risk",
        "amount",
        "turnover",
        "range",
        "volatility",
    )
    out: list[int] = []
    for index, name in enumerate(feature_names):
        lowered = str(name).lower()
        if lowered.startswith(prefixes) or any(keyword in lowered for keyword in keywords):
            out.append(index)
    return out


def _meta_confidence_features(x_values, prob, *, threshold: float):
    import torch

    prob_column = prob.view(-1, 1)
    margin = torch.abs(prob_column - float(threshold))
    entropy_proxy = prob_column * (1.0 - prob_column)
    side = (prob_column >= float(threshold)).to(x_values.dtype)
    return torch.cat([x_values, prob_column, margin, entropy_proxy, side], dim=1)


def _best_meta_confidence_threshold(
    score,
    correct,
    *,
    target_accuracy: float,
    min_count: int = 1,
    min_coverage: float = 0.0,
) -> dict[str, float | int]:
    import torch

    thresholds = torch.linspace(0.45, 0.95, steps=101, device=score.device)
    selected = score.view(1, -1) >= thresholds.view(-1, 1)
    counts = selected.sum(dim=1)
    selected_correct = (selected.to(torch.float32) * correct.view(1, -1)).sum(dim=1)
    accuracies = selected_correct / torch.clamp(counts.to(torch.float32), min=1.0)
    coverages = counts.to(torch.float32) / max(float(len(correct)), 1.0)
    wilson = _torch_wilson_lower(selected_correct, counts)
    valid = (counts >= int(min_count)) & (coverages >= float(min_coverage))
    fallback_valid = counts > 0
    passing = valid & (wilson >= float(target_accuracy))
    if torch.any(passing):
        masked_coverage = torch.where(passing, coverages, torch.full_like(coverages, -1.0))
        index = int(torch.argmax(masked_coverage).detach().cpu().item())
    else:
        candidate_valid = valid if torch.any(valid) else fallback_valid
        masked_wilson = torch.where(candidate_valid, wilson, torch.full_like(wilson, -1.0))
        max_wilson = torch.max(masked_wilson)
        tied = candidate_valid & torch.isclose(wilson, max_wilson)
        masked_coverage = torch.where(tied, coverages, torch.full_like(coverages, -1.0))
        index = int(torch.argmax(masked_coverage).detach().cpu().item())
    return {
        "threshold": float(thresholds[index].detach().cpu().item()),
        "accuracy": float(accuracies[index].detach().cpu().item()),
        "coverage": float(coverages[index].detach().cpu().item()),
        "count": int(counts[index].detach().cpu().item()),
        "wilson_lower_95": float(wilson[index].detach().cpu().item()),
        "min_count": int(min_count),
        "min_coverage": float(min_coverage),
        "constraint_met": bool(valid[index].detach().cpu().item()),
        "target_wilson_met": bool((wilson[index] >= float(target_accuracy)).detach().cpu().item()),
    }


def _fit_logit_calibration(logits, y) -> dict[str, float]:
    import torch

    if len(y) < 50:
        return {"scale": 1.0, "bias": 0.0}
    raw_logits = logits.detach()
    target = y.detach().to(raw_logits.dtype)
    scale = torch.nn.Parameter(torch.ones((), device=raw_logits.device))
    bias = torch.nn.Parameter(torch.zeros((), device=raw_logits.device))
    optimizer = torch.optim.LBFGS([scale, bias], lr=0.25, max_iter=30, line_search_fn="strong_wolfe")

    def closure():
        optimizer.zero_grad(set_to_none=True)
        adjusted = raw_logits * torch.clamp(scale, min=0.05, max=5.0) + bias
        loss = torch.nn.functional.binary_cross_entropy_with_logits(adjusted, target)
        loss.backward()
        return loss

    try:
        optimizer.step(closure)
    except Exception:
        return {"scale": 1.0, "bias": 0.0}
    return {
        "scale": float(torch.clamp(scale.detach(), min=0.05, max=5.0).cpu().item()),
        "bias": float(torch.clamp(bias.detach(), min=-5.0, max=5.0).cpu().item()),
    }


def _apply_logit_calibration(logits, calibration: dict[str, Any]):
    import torch

    scale = float(calibration.get("scale", 1.0))
    bias = float(calibration.get("bias", 0.0))
    return torch.sigmoid(logits * scale + bias).flatten()


def _accuracy(prob, y, *, threshold: float = 0.5) -> float:
    if len(y) == 0:
        return 0.0
    return float(((prob >= threshold).to(y.dtype) == y).float().mean().detach().cpu().item())


def _best_threshold(prob, y) -> tuple[float, float]:
    import torch

    if len(y) == 0:
        return 0.5, 0.0
    thresholds = torch.linspace(0.25, 0.75, steps=101, device=prob.device)
    predictions = prob.view(1, -1) >= thresholds.view(-1, 1)
    accuracies = (predictions.to(y.dtype) == y.view(1, -1)).float().mean(dim=1)
    index = int(torch.argmax(accuracies).detach().cpu().item())
    return float(thresholds[index].detach().cpu().item()), float(accuracies[index].detach().cpu().item())


def _best_confidence_band(
    prob,
    y,
    *,
    threshold: float,
    target_accuracy: float,
    min_count: int = 1,
    min_coverage: float = 0.0,
):
    import torch

    if len(y) == 0:
        return {
            "low": 0.35,
            "high": 0.65,
            "side": "both",
            "accuracy": 0.0,
            "coverage": 0.0,
            "count": 0,
            "stability_chunks": 0,
            "stability_min_accuracy": 0.0,
            "stability_min_wilson_lower_95": 0.0,
            "stability_min_coverage": 0.0,
            "stable_constraint_met": False,
        }
    margins = torch.linspace(0.02, 0.30, steps=57, device=prob.device)
    lows = torch.clamp(torch.as_tensor(float(threshold), device=prob.device) - margins, min=0.02)
    highs = torch.clamp(torch.as_tensor(float(threshold), device=prob.device) + margins, max=0.98)
    both_selected = (prob.view(1, -1) <= lows.view(-1, 1)) | (prob.view(1, -1) >= highs.view(-1, 1))
    long_selected = prob.view(1, -1) >= highs.view(-1, 1)
    short_selected = prob.view(1, -1) <= lows.view(-1, 1)
    selected = torch.cat([both_selected, long_selected, short_selected], dim=0)
    lows_grid = torch.cat([lows, lows, lows])
    highs_grid = torch.cat([highs, highs, highs])
    side_grid = ["both"] * len(margins) + ["long"] * len(margins) + ["short"] * len(margins)
    counts = selected.sum(dim=1)
    correct = ((prob >= threshold).to(y.dtype) == y).to(torch.float32)
    selected_correct = (selected.to(torch.float32) * correct.view(1, -1)).sum(dim=1)
    accuracies = selected_correct / torch.clamp(counts.to(torch.float32), min=1.0)
    coverages = counts.to(torch.float32) / max(float(len(y)), 1.0)
    wilson = _torch_wilson_lower(selected_correct, counts)
    valid = (counts >= int(min_count)) & (coverages >= float(min_coverage))
    fallback_valid = counts > 0
    stability = _confidence_band_stability(
        selected,
        correct,
        target_accuracy=target_accuracy,
        min_count=min_count,
        min_coverage=min_coverage,
    )
    stable_wilson = stability["min_wilson_lower_95"]
    robust_wilson = wilson * 0.60 + stable_wilson * 0.40
    passing = valid & (wilson >= float(target_accuracy)) & stability["constraint_met"]
    if torch.any(passing):
        masked_coverage = torch.where(passing, coverages, torch.full_like(coverages, -1.0))
        index = int(torch.argmax(masked_coverage).detach().cpu().item())
    else:
        candidate_valid = valid if torch.any(valid) else fallback_valid
        robust_score = robust_wilson + torch.clamp(coverages, max=0.30) * 0.03
        masked_score = torch.where(candidate_valid, robust_score, torch.full_like(robust_score, -1.0))
        max_score = torch.max(masked_score)
        tied = candidate_valid & torch.isclose(robust_score, max_score)
        masked_coverage = torch.where(tied, coverages, torch.full_like(coverages, -1.0))
        index = int(torch.argmax(masked_coverage).detach().cpu().item())
    return {
        "low": float(lows_grid[index].detach().cpu().item()),
        "high": float(highs_grid[index].detach().cpu().item()),
        "side": side_grid[index],
        "accuracy": float(accuracies[index].detach().cpu().item()),
        "coverage": float(coverages[index].detach().cpu().item()),
        "count": int(counts[index].detach().cpu().item()),
        "wilson_lower_95": float(wilson[index].detach().cpu().item()),
        "min_count": int(min_count),
        "min_coverage": float(min_coverage),
        "constraint_met": bool(valid[index].detach().cpu().item()),
        "target_wilson_met": bool((wilson[index] >= float(target_accuracy)).detach().cpu().item()),
        "stability_chunks": int(stability["chunks"]),
        "stability_min_accuracy": float(stability["min_accuracy"][index].detach().cpu().item()),
        "stability_mean_accuracy": float(stability["mean_accuracy"][index].detach().cpu().item()),
        "stability_min_wilson_lower_95": float(stability["min_wilson_lower_95"][index].detach().cpu().item()),
        "stability_min_coverage": float(stability["min_coverage"][index].detach().cpu().item()),
        "stable_constraint_met": bool(stability["constraint_met"][index].detach().cpu().item()),
    }


def _confidence_band_stability(
    selected,
    correct,
    *,
    target_accuracy: float,
    min_count: int,
    min_coverage: float,
) -> dict[str, Any]:
    import torch

    sample_count = int(correct.numel())
    candidate_count = int(selected.shape[0])
    if sample_count == 0 or candidate_count == 0:
        zeros = torch.zeros(candidate_count, device=selected.device, dtype=torch.float32)
        return {
            "chunks": 0,
            "min_accuracy": zeros,
            "mean_accuracy": zeros,
            "min_wilson_lower_95": zeros,
            "min_coverage": zeros,
            "constraint_met": torch.zeros(candidate_count, device=selected.device, dtype=torch.bool),
        }

    chunk_count = 1 if sample_count < 1200 else min(4, max(2, sample_count // 1200))
    if chunk_count == 1:
        chunk_min_count = int(min_count)
        chunk_min_coverage = float(min_coverage)
    else:
        chunk_min_count = max(1, int(min_count) // max(1, chunk_count * 2))
        chunk_min_coverage = float(min_coverage) * 0.35

    chunk_accuracies = []
    chunk_wilsons = []
    chunk_coverages = []
    chunk_valids = []
    for chunk_index in range(chunk_count):
        start = int(round(sample_count * chunk_index / chunk_count))
        end = int(round(sample_count * (chunk_index + 1) / chunk_count))
        if end <= start:
            continue
        chunk_selected = selected[:, start:end]
        chunk_counts = chunk_selected.sum(dim=1)
        chunk_correct = (chunk_selected.to(torch.float32) * correct[start:end].view(1, -1)).sum(dim=1)
        chunk_accuracy = chunk_correct / torch.clamp(chunk_counts.to(torch.float32), min=1.0)
        chunk_coverage = chunk_counts.to(torch.float32) / max(float(end - start), 1.0)
        chunk_wilson = _torch_wilson_lower(chunk_correct, chunk_counts)
        chunk_valid = (chunk_counts >= chunk_min_count) & (chunk_coverage >= chunk_min_coverage)
        chunk_accuracies.append(chunk_accuracy)
        chunk_wilsons.append(chunk_wilson)
        chunk_coverages.append(chunk_coverage)
        chunk_valids.append(chunk_valid)

    if not chunk_accuracies:
        zeros = torch.zeros(candidate_count, device=selected.device, dtype=torch.float32)
        return {
            "chunks": 0,
            "min_accuracy": zeros,
            "mean_accuracy": zeros,
            "min_wilson_lower_95": zeros,
            "min_coverage": zeros,
            "constraint_met": torch.zeros(candidate_count, device=selected.device, dtype=torch.bool),
        }

    accuracies = torch.stack(chunk_accuracies, dim=0)
    wilsons = torch.stack(chunk_wilsons, dim=0)
    coverages = torch.stack(chunk_coverages, dim=0)
    valid_chunks = torch.stack(chunk_valids, dim=0)
    zeros = torch.zeros_like(accuracies)
    valid_float = valid_chunks.to(torch.float32)
    valid_count = torch.clamp(valid_float.sum(dim=0), min=1.0)
    stable_accuracy = torch.where(valid_chunks, accuracies, zeros)
    stable_wilson = torch.where(valid_chunks, wilsons, zeros)
    stable_coverage = torch.where(valid_chunks, coverages, zeros)
    return {
        "chunks": int(valid_chunks.shape[0]),
        "min_accuracy": stable_accuracy.min(dim=0).values,
        "mean_accuracy": stable_accuracy.sum(dim=0) / valid_count,
        "min_wilson_lower_95": stable_wilson.min(dim=0).values,
        "min_coverage": stable_coverage.min(dim=0).values,
        "constraint_met": valid_chunks.all(dim=0) & (stable_wilson.min(dim=0).values >= float(target_accuracy)),
    }


def _confidence_mask_from_band(prob, band: dict[str, Any]):
    side = str(band.get("side") or "both")
    low = float(band.get("low", 0.35))
    high = float(band.get("high", 0.65))
    if side == "long":
        return prob >= high
    if side == "short":
        return prob <= low
    return (prob >= high) | (prob <= low)


def _torch_wilson_lower(successes, counts, *, z: float = 1.959963984540054):
    import torch

    total = counts.to(torch.float32)
    success = successes.to(torch.float32)
    safe_total = torch.clamp(total, min=1.0)
    phat = success / safe_total
    z2 = float(z) * float(z)
    denominator = 1.0 + z2 / safe_total
    centre = phat + z2 / (2.0 * safe_total)
    margin = float(z) * torch.sqrt((phat * (1.0 - phat) + z2 / (4.0 * safe_total)) / safe_total)
    lower = (centre - margin) / denominator
    return torch.where(total > 0, torch.clamp(lower, min=0.0, max=1.0), torch.zeros_like(lower))


def _coverage_at_accuracy(prob, y, *, threshold: float, target_accuracy: float):
    import torch

    if len(y) == 0:
        return {"coverage": 0.0, "count": 0}
    margins = torch.linspace(0.02, 0.45, steps=87, device=prob.device)
    lows = torch.clamp(torch.as_tensor(float(threshold), device=prob.device) - margins, min=0.02)
    highs = torch.clamp(torch.as_tensor(float(threshold), device=prob.device) + margins, max=0.98)
    selected = (prob.view(1, -1) <= lows.view(-1, 1)) | (prob.view(1, -1) >= highs.view(-1, 1))
    counts = selected.sum(dim=1)
    correct = ((prob >= threshold).to(y.dtype) == y).to(torch.float32)
    selected_correct = (selected.to(torch.float32) * correct.view(1, -1)).sum(dim=1)
    accuracies = selected_correct / torch.clamp(counts.to(torch.float32), min=1.0)
    coverages = counts.to(torch.float32) / max(float(len(y)), 1.0)
    passing = (counts > 0) & (accuracies >= float(target_accuracy))
    if not torch.any(passing):
        return {"coverage": 0.0, "count": 0}
    masked_coverage = torch.where(passing, coverages, torch.full_like(coverages, -1.0))
    index = int(torch.argmax(masked_coverage).detach().cpu().item())
    return {
        "coverage": float(coverages[index].detach().cpu().item()),
        "count": int(counts[index].detach().cpu().item()),
    }


def _brier(prob, y) -> float:
    import torch

    if len(y) == 0:
        return 1.0
    return float(torch.mean((prob - y) ** 2).detach().cpu().item())


def _constant_brier(y, *, value: float) -> float:
    import torch

    if len(y) == 0:
        return 1.0
    constant = torch.full_like(y, float(value))
    return float(torch.mean((constant - y) ** 2).detach().cpu().item())


def _pct_change(values, periods: int):
    import torch

    lagged = _lag(values, periods)
    return (values / torch.clamp(lagged, min=1e-6) - 1.0) * 100.0


def _lag(values, periods: int):
    import torch

    if periods <= 0:
        return values
    out = torch.empty_like(values)
    out[:periods] = values[:1]
    out[periods:] = values[:-periods]
    return out


def _rolling_mean(values, window: int):
    import torch

    unfolded = _rolling_unfold(values, window)
    return unfolded.mean(dim=1)


def _rolling_std(values, window: int):
    unfolded = _rolling_unfold(values, window)
    return unfolded.std(dim=1, unbiased=False)


def _rolling_sum(values, window: int):
    return _rolling_unfold(values, window).sum(dim=1)


def _rolling_zscore(values, window: int):
    import torch

    mean = _rolling_mean(values, window)
    std = torch.clamp(_rolling_std(values, window), min=1e-6)
    return (values - mean) / std


def _rolling_max(values, window: int):
    return _rolling_unfold(values, window).max(dim=1).values


def _rolling_min(values, window: int):
    return _rolling_unfold(values, window).min(dim=1).values


def _rolling_percent_rank(values, window: int):
    unfolded = _rolling_unfold(values, window)
    return (unfolded <= values.view(-1, 1)).to(values.dtype).mean(dim=1)


def _atr_pct(high, low, close, *, window: int):
    import torch

    prev_close = _lag(close, 1)
    true_range = torch.maximum(high - low, torch.maximum(torch.abs(high - prev_close), torch.abs(low - prev_close)))
    return _rolling_mean(true_range, window) / torch.clamp(close, min=1e-6) * 100.0


def _obv_trend(close, volume, *, window: int):
    import torch

    direction = torch.sign(close - _lag(close, 1))
    obv = torch.cumsum(direction * volume, dim=0)
    return (obv - _lag(obv, window)) / torch.clamp(_rolling_sum(torch.abs(volume), window), min=1e-6)


def _mfi(high, low, close, volume, *, window: int):
    import torch

    typical = (high + low + close) / 3.0
    money_flow = typical * volume
    direction = typical - _lag(typical, 1)
    positive = torch.where(direction > 0.0, money_flow, torch.zeros_like(money_flow))
    negative = torch.where(direction < 0.0, torch.abs(money_flow), torch.zeros_like(money_flow))
    ratio = _rolling_sum(positive, window) / torch.clamp(_rolling_sum(negative, window), min=1e-6)
    return 100.0 - (100.0 / (1.0 + ratio))


def _ema(values, span: int):
    import torch

    out = torch.empty_like(values)
    if len(values) == 0:
        return out
    alpha = 2.0 / (float(span) + 1.0)
    out[0] = values[0]
    for index in range(1, len(values)):
        out[index] = values[index] * alpha + out[index - 1] * (1.0 - alpha)
    return out


def _macd(close):
    import torch

    dif = _ema(close, 12) - _ema(close, 26)
    signal = _ema(dif, 9)
    hist = dif - signal
    scale = torch.clamp(close, min=1e-6)
    return hist / scale * 100.0, signal / scale * 100.0


def _kdj(high, low, close, *, window: int):
    import torch

    low_min = _rolling_min(low, window)
    high_max = _rolling_max(high, window)
    rsv = (close - low_min) / torch.clamp(high_max - low_min, min=1e-6) * 100.0
    k = torch.empty_like(rsv)
    d = torch.empty_like(rsv)
    if len(rsv) == 0:
        return k, d, rsv
    k[0] = 50.0
    d[0] = 50.0
    for index in range(1, len(rsv)):
        k[index] = k[index - 1] * (2.0 / 3.0) + rsv[index] / 3.0
        d[index] = d[index - 1] * (2.0 / 3.0) + k[index] / 3.0
    j = 3.0 * k - 2.0 * d
    return k, d, j


def _cci(high, low, close, *, window: int):
    import torch

    typical = (high + low + close) / 3.0
    unfolded = _rolling_unfold(typical, window)
    mean = unfolded.mean(dim=1)
    mean_deviation = torch.mean(torch.abs(unfolded - mean.view(-1, 1)), dim=1)
    return (typical - mean) / torch.clamp(0.015 * mean_deviation, min=1e-6)


def _williams_r(high, low, close, *, window: int):
    import torch

    highest = _rolling_max(high, window)
    lowest = _rolling_min(low, window)
    return -100.0 * (highest - close) / torch.clamp(highest - lowest, min=1e-6)


def _adx(high, low, close, *, window: int):
    import torch

    prev_high = _lag(high, 1)
    prev_low = _lag(low, 1)
    prev_close = _lag(close, 1)
    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = torch.where((up_move > down_move) & (up_move > 0.0), up_move, torch.zeros_like(up_move))
    minus_dm = torch.where((down_move > up_move) & (down_move > 0.0), down_move, torch.zeros_like(down_move))
    true_range = torch.maximum(high - low, torch.maximum(torch.abs(high - prev_close), torch.abs(low - prev_close)))
    tr_sum = torch.clamp(_rolling_sum(true_range, window), min=1e-6)
    plus_di = 100.0 * _rolling_sum(plus_dm, window) / tr_sum
    minus_di = 100.0 * _rolling_sum(minus_dm, window) / tr_sum
    dx = 100.0 * torch.abs(plus_di - minus_di) / torch.clamp(plus_di + minus_di, min=1e-6)
    return _rolling_mean(dx, window)


def _consecutive_streak(flags):
    import torch

    out = torch.zeros_like(flags)
    if len(flags) == 0:
        return out
    out[0] = flags[0]
    for index in range(1, len(flags)):
        out[index] = torch.where(flags[index] > 0.5, out[index - 1] + 1.0, torch.tensor(0.0, device=flags.device))
    return out


def _profit_pressure(close, *, window: int):
    unfolded = _rolling_unfold(close, window)
    return (close.view(-1, 1) > unfolded).to(close.dtype).mean(dim=1)


def _rolling_unfold(values, window: int):
    import torch

    padded = torch.cat([values[:1].repeat(window - 1), values])
    return padded.unfold(0, window, 1)


def _rsi(returns, window: int):
    import torch

    gains = torch.clamp(returns, min=0.0)
    losses = torch.clamp(-returns, min=0.0)
    avg_gain = _rolling_mean(gains, window)
    avg_loss = _rolling_mean(losses, window)
    rs = avg_gain / torch.clamp(avg_loss, min=1e-6)
    return 100.0 - (100.0 / (1.0 + rs))

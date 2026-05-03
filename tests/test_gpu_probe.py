from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import json
import numpy as np
import pandas as pd
import pytest

from ashare_similarity.prediction import gpu_probe
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig
from ashare_similarity.prediction.service import PredictionService


def test_symbol_feature_frame_includes_research_factor_pack(make_ohlcv_frame):
    torch = pytest.importorskip("torch")
    frame = make_ohlcv_frame(periods=90, base_price=20.0, volume_base=5_000_000.0)
    frame["amount"] = frame["volume"] * frame["close"]
    frame["turnover"] = np.linspace(2.0, 12.0, len(frame))

    features = gpu_probe._symbol_feature_frame(
        frame,
        symbol="600519",
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
        device=torch.device("cpu"),
        config=GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 12, 31),
            short_only=False,
        ),
    )

    expected = {
        "overnight_return",
        "intraday_return",
        "overnight_vs_intraday",
        "overnight_abs_rank_20",
        "bollinger_position_20",
        "failed_limit_up",
        "limit_down_bounce_pct",
        "t_plus_1_selling_pressure",
        "macd_hist",
        "kdj_k",
        "cci_20",
        "williams_r_14",
        "adx_14",
        "volume_to_mean_20",
        "new_high_volume_ratio_20",
        "consolidation_days_20",
        "reversal_with_volume",
        "price_position_60",
        "low_position_big_yang",
        "ma5_pullback_entry",
        "ma5_break_exit",
        "trend_pullback_health",
        "non_limit_open_strength",
        "auction_board_trigger_proxy",
        "safety_margin_calculation_proxy",
        "seal_grade_confirmation_proxy",
        "mega_order_absorption_proxy",
        "popularity_positive_feedback_proxy",
        "day_of_week_sin",
        "month_end_3",
        "short_phase_days_3",
        "short_phase_score_3",
        "stock_personality_score",
        "new_high_board",
        "weak_to_strong_daily",
        "monster_acceleration",
        "highlight_score",
        "former_leader_recall",
        "leader_faith_decay_60",
        "quant_oscillation_score_10",
        "daily_amount_300m_gate",
        "amount_300m_turnover_quality",
        "volume_price_match",
        "twenty_cm_board_risk",
    }
    assert expected.issubset(features.columns)
    assert features.loc[:, sorted(expected)].notna().all().all()
    assert (pd.to_datetime(features["label_date"]) > pd.to_datetime(features["date"])).all()


def test_feature_set_keeps_noisy_research_factors_out_of_default_expanded():
    expanded = gpu_probe._feature_names_for_config(
        GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 5, 31),
            feature_set="expanded",
        )
    )
    research = gpu_probe._feature_names_for_config(
        GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 5, 31),
            feature_set="research",
        )
    )

    assert "market_limit_down_rate" not in expanded
    assert "explosive_vol_next_weak" not in expanded
    assert "stock_personality_score" not in expanded
    assert "highlight_score" not in expanded
    assert "former_leader_recall" not in expanded
    assert "cs_low_price_advantage" not in expanded
    assert "ma5_pullback_entry" not in expanded
    assert "non_limit_open_strength" not in expanded
    assert "seal_grade_confirmation_proxy" not in expanded
    assert "decline_stabilize_signal" not in expanded
    assert "bullish_pivot_recognition" not in expanded
    assert "real_in_zt_pool" not in expanded
    assert "cycle_day_count" not in expanded
    assert "market_cycle_failed_pressure" not in expanded
    assert "daily_amount_300m_gate" not in expanded
    assert "volume_price_match" not in expanded
    assert "chase_market_up_alignment" not in expanded
    assert "second_board_leader_proxy" not in expanded
    assert "breakout_first_board_proxy" not in expanded
    assert "money_effect_chase_alignment" not in expanded
    assert "collapse_hot_stock_risk" not in expanded
    assert "index_panic_rebound_setup" not in expanded
    assert "market_limit_down_rate" in research
    assert "explosive_vol_next_weak" in research
    assert "stock_personality_score" in research
    assert "highlight_score" in research
    assert "former_leader_recall" in research
    assert "cs_low_price_advantage" in research
    assert "ma5_pullback_entry" in research
    assert "non_limit_open_strength" in research
    assert "seal_grade_confirmation_proxy" in research
    assert "decline_stabilize_signal" in research
    assert "bullish_pivot_recognition" in research
    assert "real_in_zt_pool" in research
    assert "market_real_broken_board_rate" in research
    assert "cycle_day_count" in research
    assert "market_cycle_failed_pressure" in research
    assert "daily_amount_300m_gate" in research
    assert "volume_price_match" in research
    assert "chase_market_up_alignment" in research
    assert "second_board_leader_proxy" in research
    assert "breakout_first_board_proxy" in research
    assert "money_effect_chase_alignment" in research
    assert "collapse_warning_signal" in research
    assert "index_panic_rebound_setup" in research
    assert "tushare_net_mf_amount" not in expanded
    assert "tushare_net_mf_amount" in research
    assert gpu_probe._uses_research_external_factors(
        GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 5, 31),
            feature_set="expanded",
        )
    ) is False
    assert gpu_probe._uses_research_external_factors(
        GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 5, 31),
            feature_set="research",
        )
    ) is True
    assert len(research) > len(expanded)


def test_expanded_feature_set_attaches_cached_factor_frames(monkeypatch, make_ohlcv_frame, tmp_path):
    called: list[str] = []

    def _attach_tgb(data, *, daily_context_frames):
        assert daily_context_frames
        called.append("tgb")
        out = data.copy()
        out["tgb_ma_alignment_score"] = 1.0
        return out, [{"name": "tgb_stock_daily", "status": "available"}]

    def _attach_ths(data, *, store):
        assert store.cache_dir == str(tmp_path)
        called.append("ths")
        out = data.copy()
        out["sector_pct_change_best"] = 1.0
        return out, [{"name": "ths_sector_daily", "status": "available"}]

    def _attach_tushare(*args, **kwargs):
        pytest.fail("research-only Tushare factors should not be attached for expanded")

    def _train_and_score(train, test, **kwargs):
        assert len(train) > 0
        assert len(test) > 0
        n = len(test)
        _pred_df = test[["symbol", "date", "label_date"]].copy()
        _pred_df["probability"] = np.linspace(0.3, 0.9, n)
        _pred_df["predicted_label"] = np.array([0] * (n // 2) + [1] * (n - n // 2), dtype=np.int8)
        _pred_df["confident"] = np.array([0] * max(0, n - 3) + [1] * min(3, n), dtype=np.int8)
        _pred_df["confidence_side"] = "both"
        _pred_df["actual"] = test["actual"].values.astype(np.int8) if "actual" in test.columns else np.zeros(n, dtype=np.int8)
        _pred_df["threshold"] = np.float32(0.5)
        for _c in ("close", "limit_up_like"):
            if _c in test.columns:
                _pred_df[_c] = test[_c].values
        return {
            "_test_predictions_df": _pred_df,
            "model": "stub",
            "model_kind": "stub",
            "accuracy": 1.0,
            "correct_count": int(len(test)),
            "brier": 0.0,
            "positive_rate": 0.5,
            "baseline_accuracy": 0.5,
            "baseline_brier": 0.25,
            "validation_accuracy": 1.0,
            "validation_brier": 0.0,
            "classification_threshold": 0.5,
            "validation_confident_accuracy": 1.0,
            "validation_confident_coverage": 1.0,
            "confidence_low_threshold": 0.35,
            "confidence_high_threshold": 0.65,
            "confident_accuracy": 1.0,
            "confident_brier": 0.0,
            "confident_count": int(len(test)),
            "confident_correct_count": int(len(test)),
            "confident_coverage": 1.0,
            "validation_confident_target_met": True,
            "confident_target_met": True,
            "test_oracle_coverage_at_target_accuracy": 1.0,
            "test_oracle_count_at_target_accuracy": int(len(test)),
            "test_oracle_target_accuracy": 0.75,
            "test_oracle_note": "stub",
            "candidate_warnings": [],
            "train_window_rows": int(len(train)),
            "fit_rows": int(len(train)),
            "validation_rows": 1,
        }

    def _load_bars(symbol, frequency):
        del symbol, frequency
        frame = make_ohlcv_frame(periods=95, base_price=10.0, volume_base=8_000_000.0)
        frame["amount"] = frame["volume"] * frame["close"]
        frame["turnover"] = np.linspace(3.0, 10.0, len(frame))
        return frame

    monkeypatch.setattr(gpu_probe, "_attach_tgb_factor_features", _attach_tgb)
    monkeypatch.setattr(gpu_probe, "_attach_ths_sector_features", _attach_ths)
    monkeypatch.setattr(gpu_probe, "_attach_tushare_factor_features", _attach_tushare)
    monkeypatch.setattr(gpu_probe, "_train_and_score", _train_and_score)

    result = gpu_probe.run_gpu_next_day_probe(
        SimpleNamespace(
            list_cached_symbols=lambda frequency: ["600001"],
            load_bars=_load_bars,
            cache_dir=str(tmp_path),
        ),
        GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 5, 31),
            test_rows=10,
            short_only=False,
            feature_set="expanded",
            use_feature_cache=False,
        ),
    )

    assert result["status"] == "completed"
    assert called == ["tgb", "ths"]
    assert [report["name"] for report in result["external_factors"][-2:]] == [
        "tgb_stock_daily",
        "ths_sector_daily",
    ]


def test_tail_accuracy_feature_scores_prioritize_rare_high_precision_signal():
    torch = pytest.importorskip("torch")
    signal = torch.zeros(240, 2)
    signal[:, 0] = torch.linspace(-1.0, 1.0, 240)
    signal[:24, 1] = 5.0
    target = torch.zeros(240)
    target[:24] = 1.0
    target[80:140] = 1.0

    scores = gpu_probe._tail_accuracy_feature_scores(signal, target)

    assert scores[1] > scores[0]
    selected = gpu_probe._select_training_feature_indices(
        signal,
        target,
        ("smooth_feature", "rare_precision_feature"),
        max_features=1,
        method="stable_tail",
    )
    assert selected["method"] == "train_stable_abs_correlation_tail_accuracy"
    assert selected["top_features"][0] == "rare_precision_feature"


def test_default_feature_selection_matches_stable_historical_abs_correlation():
    torch = pytest.importorskip("torch")
    signal = torch.zeros(200, 2)
    signal[:, 0] = torch.linspace(-1.0, 1.0, 200)
    signal[:20, 1] = 5.0
    target = (signal[:, 0] > 0).to(torch.float32)

    selected = gpu_probe._select_training_feature_indices(
        signal,
        target,
        ("smooth_feature", "rare_precision_feature"),
        max_features=1,
    )

    assert selected["method"] == "train_abs_correlation"
    assert selected["top_features"][0] == "smooth_feature"


def test_feature_selection_forces_jsonl_priority_features():
    torch = pytest.importorskip("torch")
    signal = torch.zeros(240, 2)
    signal[:, 0] = torch.linspace(-1.0, 1.0, 240)
    signal[:, 1] = torch.linspace(0.25, 1.25, 240)
    target = (signal[:, 0] > 0).to(torch.float32)

    selected = gpu_probe._select_training_feature_indices(
        signal,
        target,
        ("smooth_feature", "seal_time_score"),
        max_features=1,
    )

    assert selected["priority_features"] == ["seal_time_score"]
    assert selected["top_features"] == ["seal_time_score"]
    assert selected["selected_features"] == ["seal_time_score"]


def test_feature_selection_fills_remaining_slots_after_priority_features():
    torch = pytest.importorskip("torch")
    signal = torch.zeros(240, 4)
    signal[:, 0] = torch.linspace(-1.0, 1.0, 240)
    signal[:, 1] = -signal[:, 0]
    signal[:, 2] = torch.linspace(0.5, -0.5, 240)
    signal[:, 3] = torch.linspace(0.25, 1.25, 240)
    target = (signal[:, 0] > 0).to(torch.float32)

    selected = gpu_probe._select_training_feature_indices(
        signal,
        target,
        ("smooth_feature", "inverse_feature", "weaker_feature", "market_true_limit_ratio"),
        max_features=2,
    )

    assert selected["priority_features"] == ["market_true_limit_ratio"]
    assert "market_true_limit_ratio" in selected["selected_features"]
    assert "smooth_feature" in selected["selected_features"]
    assert selected["selected_feature_count"] == 2


def test_feature_selection_skips_low_coverage_priority_features():
    torch = pytest.importorskip("torch")
    signal = torch.zeros(240, 2)
    signal[:, 0] = torch.linspace(-1.0, 1.0, 240)
    signal[:2, 1] = 1.0
    target = (signal[:, 0] > 0).to(torch.float32)

    selected = gpu_probe._select_training_feature_indices(
        signal,
        target,
        ("smooth_feature", "seal_time_score"),
        max_features=1,
    )

    assert selected["priority_features"] == []
    assert selected["skipped_priority_feature_count"] == 1
    assert selected["skipped_priority_features"][0]["feature"] == "seal_time_score"
    assert selected["skipped_priority_features"][0]["reason"] == "low_nonzero_coverage"
    assert selected["selected_features"] == ["smooth_feature"]


def test_feature_selection_keeps_rare_daily_priority_features():
    torch = pytest.importorskip("torch")
    signal = torch.zeros(240, 2)
    signal[:, 0] = torch.linspace(-1.0, 1.0, 240)
    signal[:2, 1] = 1.0
    target = (signal[:, 0] > 0).to(torch.float32)

    selected = gpu_probe._select_training_feature_indices(
        signal,
        target,
        ("smooth_feature", "is_second_board"),
        max_features=1,
    )

    assert selected["priority_features"] == ["is_second_board"]
    assert selected["selected_features"] == ["is_second_board"]
    assert selected["skipped_priority_feature_count"] == 0


def test_pair_regime_confidence_selector_finds_two_factor_gate():
    torch = pytest.importorskip("torch")
    rows = 1200
    feature_a = torch.zeros(rows)
    feature_b = torch.zeros(rows)
    feature_a[:120] = 1.0
    feature_b[:120] = 1.0
    feature_a[600:720] = 1.0
    feature_b[600:720] = 1.0
    x_valid = torch.stack([feature_a, feature_b], dim=1)
    x_test = x_valid.clone()
    y_valid = torch.zeros(rows)
    y_valid[:120] = 1.0
    y_valid[600:720] = 1.0
    valid_prob = torch.full((rows,), 0.40)
    valid_prob[:120] = 0.90
    valid_prob[600:720] = 0.90
    test_prob = valid_prob.clone()

    selector = gpu_probe._fit_pair_regime_confidence_selector(
        x_valid,
        y_valid,
        valid_prob,
        x_test,
        test_prob,
        threshold=0.5,
        target_accuracy=0.75,
        feature_names=("market_limit_down_rate", "cross_sz399001_ret_3"),
    )

    assert selector["method"] == "pair_regime_probability_gate"
    assert selector["eligible"] is True
    assert selector["validation_accuracy"] == pytest.approx(1.0)
    assert bool(selector["test_mask"].any())


def test_pair_regime_confidence_selector_returns_best_constrained_fallback():
    torch = pytest.importorskip("torch")
    rows = 1200
    feature_a = torch.zeros(rows)
    feature_b = torch.zeros(rows)
    feature_a[:240] = 1.0
    feature_b[:240] = 1.0
    x_valid = torch.stack([feature_a, feature_b], dim=1)
    x_test = x_valid.clone()
    y_valid = torch.zeros(rows)
    y_valid[:156] = 1.0
    y_valid[240:720] = 1.0
    valid_prob = torch.full((rows,), 0.40)
    valid_prob[:240] = 0.90
    test_prob = valid_prob.clone()

    selector = gpu_probe._fit_pair_regime_confidence_selector(
        x_valid,
        y_valid,
        valid_prob,
        x_test,
        test_prob,
        threshold=0.5,
        target_accuracy=0.75,
        feature_names=("real_seal_time_minutes", "real_in_zt_pool"),
    )

    assert selector["method"] == "pair_regime_probability_gate"
    assert selector["eligible"] is False
    assert selector["validation_count"] >= 200
    assert selector["validation_coverage"] >= 0.10
    assert bool(selector["test_mask"].any())


def test_regime_feature_indices_include_real_limit_pool_jsonl_terms():
    feature_names = (
        "plain_noise",
        "real_seal_time_minutes",
        "real_in_zt_pool",
        "real_in_zbgc_pool",
    )

    indices = gpu_probe._regime_feature_indices(feature_names)

    assert indices == [1, 2, 3]


def test_short_filter_keeps_only_active_stock_phases(make_ohlcv_frame):
    torch = pytest.importorskip("torch")
    frame = make_ohlcv_frame(periods=80, base_price=20.0, volume_base=1_000_000.0)
    frame["amount"] = 50_000_000.0
    frame["turnover"] = 0.8
    active = frame.index >= 45
    frame.loc[active, "volume"] = 18_000_000.0
    frame.loc[active, "amount"] = frame.loc[active, "volume"] * frame.loc[active, "close"]
    frame.loc[active, "turnover"] = 8.0
    frame.loc[active, "high"] = frame.loc[active, "close"] * 1.04
    frame.loc[active, "low"] = frame.loc[active, "close"] * 0.96

    features = gpu_probe._symbol_feature_frame(
        frame,
        symbol="600519",
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
        device=torch.device("cpu"),
        config=GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 12, 31),
            short_only=True,
            min_turnover=3.0,
            min_amount=200_000_000.0,
            min_range_pct=3.0,
            min_phase_days_3=2,
        ),
    )

    assert not features.empty
    assert pd.to_datetime(features["date"]).min() >= pd.to_datetime(frame.loc[46, "date"])
    assert (features["short_phase_days_3"] >= 2.0).all()


def test_acceptance_uses_high_confidence_wilson_gate_not_full_sample_accuracy_only():
    result = {
        "accuracy": 0.81,
        "correct_count": 40_500,
        "brier": 0.21,
        "baseline_brier": 0.24,
        "confident_accuracy": 0.85,
        "confident_correct_count": 8_500,
        "confident_brier": 0.18,
        "confident_count": 10_000,
        "confident_coverage": 0.20,
    }

    accepted = gpu_probe._acceptance_summary(result, test_rows=50_000, required_test_rows=50_000, target_accuracy=0.8)
    too_few_rows = gpu_probe._acceptance_summary(result, test_rows=49_999, required_test_rows=50_000, target_accuracy=0.8)
    weak_brier = gpu_probe._acceptance_summary(
        {**result, "confident_brier": 0.25},
        test_rows=50_000,
        required_test_rows=50_000,
        target_accuracy=0.8,
    )
    tiny_confident = gpu_probe._acceptance_summary(
        {**result, "confident_accuracy": 1.0, "confident_correct_count": 20, "confident_count": 20, "confident_coverage": 0.5},
        test_rows=40,
        required_test_rows=40,
        target_accuracy=0.8,
    )
    future_filtered = gpu_probe._acceptance_summary(
        result,
        test_rows=50_000,
        required_test_rows=50_000,
        target_accuracy=0.8,
        future_label_filter_used=True,
    )
    seen_lockbox = gpu_probe._acceptance_summary(
        result,
        test_rows=50_000,
        required_test_rows=50_000,
        target_accuracy=0.8,
        lockbox_role="seen_research",
    )

    assert accepted["passed"] is True
    assert too_few_rows["passed"] is True
    assert too_few_rows["sample_size_target_met"] is False
    assert too_few_rows["sample_size_required_for_pass"] is False
    assert accepted["high_confidence"]["wilson_lower_met"] is True
    assert tiny_confident["passed"] is False
    assert tiny_confident["high_confidence"]["statistical_rows_met"] is False
    assert weak_brier["passed"] is False
    assert future_filtered["passed"] is False
    assert seen_lockbox["passed"] is False
    assert seen_lockbox["status"] == "research_only"
    assert seen_lockbox["passed_without_lockbox_role_gate"] is True


def test_cross_section_adds_short_emotion_features():
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02"] * 4),
            "symbol": ["600001", "600002", "600003", "600004"],
            "close": [12.0, 8.0, 20.0, 5.0],
            "ret_1": [10.0, 6.0, -6.0, -10.0],
            "turnover": [8.0, 5.0, 4.0, 3.0],
            "amount_z_20": [3.0, 2.0, 1.0, 0.5],
            "volume_z_20": [2.0, 1.5, 1.0, 0.2],
            "range_pct": [9.0, 6.0, 5.0, 4.0],
            "ret_std_10": [3.0, 2.0, 2.0, 1.0],
            "turnover_z_20": [2.0, 1.0, 0.5, 0.1],
            "limit_up_like": [1.0, 0.0, 0.0, 0.0],
            "limit_down_like": [0.0, 0.0, 0.0, 1.0],
            "big_up": [1.0, 1.0, 0.0, 0.0],
            "big_down": [0.0, 0.0, 1.0, 1.0],
            "failed_limit_up": [0.0, 1.0, 0.0, 0.0],
            "near_limit_close": [1.0, 0.0, 0.0, 0.0],
            "close_position": [0.9, 0.8, 0.2, 0.1],
            "cross_sz399001_ret_3": [-6.0, -6.0, -6.0, -6.0],
            "cross_sz399006_ret_3": [-6.5, -6.5, -6.5, -6.5],
            "cross_sh000001_ret_3": [-3.0, -3.0, -3.0, -3.0],
            "dist_low_20": [0.05, 0.10, 0.20, 0.30],
            "lower_shadow_pct": [2.0, 1.0, 0.2, 0.1],
        }
    )

    out = gpu_probe._add_cross_section_features(frame)

    assert out["cs_limit_up_rate"].iloc[0] == pytest.approx(0.25)
    assert out["cs_limit_down_rate"].iloc[0] == pytest.approx(0.25)
    assert out["cs_big_up_rate"].iloc[0] == pytest.approx(0.5)
    assert out["cs_failed_limit_up_rate"].iloc[0] == pytest.approx(0.25)
    assert "cs_emotion_score" in out.columns
    assert "cs_active_anomaly_rank" in out.columns
    assert out.loc[out["symbol"] == "600001", "cs_active_anomaly_rank"].iloc[0] > out.loc[
        out["symbol"] == "600004",
        "cs_active_anomaly_rank",
    ].iloc[0]
    assert out.loc[out["symbol"] == "600001", "cs_short_pool_top_decile"].iloc[0] == pytest.approx(1.0)
    assert "market_cycle_failed_pressure" in out.columns
    assert "market_hot_cycle_short_pressure" in out.columns
    assert "cs_low_price_advantage" in out.columns
    assert "cs_reversal_day_leader_quality" in out.columns
    assert "breakout_first_board_proxy" in out.columns
    assert out["index_panic_rebound_setup"].iloc[0] > 0.0
    assert out["index_panic_rebound_leader"].iloc[0] > out["index_panic_rebound_leader"].iloc[3]


def test_active_anomaly_filter_keeps_ranked_short_pool():
    frame = pd.DataFrame(
        {
            "symbol": ["600001", "600002", "600003"],
            "cs_active_anomaly_rank": [0.95, 0.70, 0.20],
            "actual": [1.0, 0.0, 1.0],
        }
    )
    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
        min_active_anomaly_rank=0.75,
    )

    filtered, report = gpu_probe._apply_active_anomaly_filter(frame, config)

    assert filtered["symbol"].tolist() == ["600001"]
    assert report["enabled"] is True
    assert report["rows_before"] == 3
    assert report["rows_after"] == 1


def test_methodology_audit_keeps_active_rank_out_of_cache_fingerprint():
    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
        min_active_anomaly_rank=0.65,
    )

    audit = gpu_probe._methodology_audit_summary(
        config,
        feature_cache={"fingerprint": "abc123"},
        active_rank_filter={"enabled": True},
        external_factors=[{"name": "sparse_factor", "coverage_rate": 0.001}],
    )

    assert audit["feature_cache_policy"]["active_rank_filter_in_cache_fingerprint"] is False
    assert audit["feature_cache_policy"]["active_rank_filter_stage"] == "post_feature_cache_pre_split"
    assert audit["feature_cache_policy"]["cache_contains_short_filter_matrix"] is True
    assert audit["sample_gate"]["min_active_anomaly_rank"] == pytest.approx(0.65)
    assert audit["low_coverage_factor_reports"] == ["sparse_factor"]


def test_research_diagnostics_isolates_test_oracle_keys():
    result = gpu_probe._isolate_research_diagnostics(
        {
            "accuracy": 0.8,
            "test_oracle_coverage_at_target_accuracy": 0.2,
            "test_oracle_count_at_target_accuracy": 100,
            "test_oracle_note": "research only",
        }
    )

    assert "test_oracle_coverage_at_target_accuracy" not in result
    assert result["research_diagnostics"]["test_oracle"]["test_oracle_count_at_target_accuracy"] == 100
    assert result["research_diagnostics"]["test_oracle"]["note"] == "research only"


def test_lockbox_identity_ignores_self_reported_role():
    train = pd.DataFrame(
        {
            "symbol": ["600001"],
            "date": pd.to_datetime(["2024-02-01"]),
            "label_date": pd.to_datetime(["2024-02-02"]),
        }
    )
    test = pd.DataFrame(
        {
            "symbol": ["600001", "600002"],
            "date": pd.to_datetime(["2024-04-01", "2024-04-01"]),
            "label_date": pd.to_datetime(["2024-04-02", "2024-04-02"]),
        }
    )
    base_config = dict(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 4, 1),
        end=date(2024, 4, 30),
    )

    seen = gpu_probe._probe_split_manifest(
        GpuProbeConfig(**base_config, lockbox_role="seen_research"),
        train=train,
        test=test,
        training_result={},
    )
    final = gpu_probe._probe_split_manifest(
        GpuProbeConfig(**base_config, lockbox_role="final_unseen"),
        train=train,
        test=test,
        training_result={},
    )

    assert seen["split_hash"] != final["split_hash"]
    assert seen["lockbox_identity_hash"] == final["lockbox_identity_hash"]


def test_final_unseen_lockbox_is_blocked_after_research_observation(app_config):
    split_manifest = {
        "lockbox_identity_hash": "same-lockbox",
        "split_hash": "seen-split",
        "train_end": "2024-03-01",
        "test_start": "2024-04-01",
        "end": "2024-04-30",
        "test_event_start": "2024-04-01",
        "test_event_end": "2024-04-30",
        "test_lockbox_rows": 50_000,
    }
    directory = app_config.storage.report_dir / "prediction"
    artifact = directory / "runs" / "seen-run" / "acceptance.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}", encoding="utf-8")
    gpu_probe._append_lockbox_ledger_record(
        directory,
        {
            "run_id": "seen-run",
            "status": "completed",
            "lockbox_role": "seen_research",
            "acceptance": {"passed": False},
            "split_manifest": split_manifest,
            "split_hash": "seen-split",
        },
        artifact_path=artifact,
    )

    final_config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 4, 1),
        end=date(2024, 4, 30),
        lockbox_role="final_unseen",
    )
    ledger = gpu_probe._lockbox_ledger_status(
        SimpleNamespace(config=app_config),
        split_manifest=split_manifest,
        config=final_config,
    )
    acceptance = gpu_probe._acceptance_summary(
        {
            "accuracy": 0.8,
            "brier": 0.2,
            "baseline_brier": 0.24,
            "confident_accuracy": 0.9,
            "confident_brier": 0.18,
            "confident_count": 50_000,
            "confident_correct_count": 45_000,
            "confident_coverage": 1.0,
        },
        test_rows=50_000,
        required_test_rows=50_000,
        target_accuracy=0.75,
        lockbox_role="final_unseen",
        lockbox_ledger=ledger,
    )

    assert ledger["gate_met"] is False
    assert ledger["observed_run_ids"] == ["seen-run"]
    assert acceptance["passed"] is False
    assert acceptance["status"] == "lockbox_reused"
    assert acceptance["passed_without_lockbox_ledger_gate"] is True


def test_run_gpu_probe_threads_target_accuracy_into_training(monkeypatch, make_ohlcv_frame, tmp_path):
    seen: dict[str, object] = {}
    symbols = ["600001", "600002"]

    def _train_and_score(train, test, **kwargs):
        seen["target_accuracy"] = kwargs["target_accuracy"]
        seen["max_selected_features"] = kwargs["max_selected_features"]
        seen["feature_selection_method"] = kwargs["feature_selection_method"]
        seen["candidate_family"] = kwargs["candidate_family"]
        seen["feature_names"] = kwargs["feature_names"]
        seen["train_label_max"] = train["label_date"].max().date()
        seen["test_date_min"] = test["date"].min().date()
        return {
            "model": "stub",
            "model_kind": "stub",
            "accuracy": 0.82,
            "brier": 0.2,
            "positive_rate": 0.51,
            "baseline_accuracy": 0.51,
            "baseline_brier": 0.2499,
            "validation_accuracy": 0.81,
            "validation_brier": 0.21,
            "classification_threshold": 0.5,
            "validation_confident_accuracy": 0.84,
            "validation_confident_coverage": 0.4,
            "confidence_low_threshold": 0.35,
            "confidence_high_threshold": 0.65,
            "confident_accuracy": 0.83,
            "confident_brier": 0.18,
            "confident_count": 10,
            "confident_coverage": 0.5,
            "validation_confident_target_met": True,
            "confident_target_met": True,
            "test_oracle_coverage_at_target_accuracy": 0.5,
            "test_oracle_count_at_target_accuracy": 10,
            "test_oracle_target_accuracy": 0.8,
            "test_oracle_note": "stub",
            "candidate_warnings": [],
        }

    def _load_bars(symbol, frequency):
        del frequency
        base = 10.0 if symbol == "600001" else 12.0
        frame = make_ohlcv_frame(symbol=symbol, periods=95, base_price=base, volume_base=8_000_000.0)
        frame["amount"] = frame["volume"] * frame["close"]
        frame["turnover"] = np.linspace(3.0, 10.0, len(frame))
        return frame

    monkeypatch.setattr(gpu_probe, "_train_and_score", _train_and_score)
    store = SimpleNamespace(list_cached_symbols=lambda frequency: symbols, load_bars=_load_bars, cache_dir=str(tmp_path))

    result = gpu_probe.run_gpu_next_day_probe(
        store,
        GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 5, 31),
            test_rows=20,
            target_accuracy=0.8,
            short_only=False,
            feature_set="expanded",
            max_selected_features=123,
            feature_selection_method="stable_tail",
            candidate_family="torch",
        ),
    )

    assert result["status"] == "completed"
    assert result["target_met"] is False
    assert result["acceptance"]["passed"] is False
    assert result["acceptance"]["sample_size_required_for_pass"] is False
    assert result["acceptance"]["high_confidence"]["statistical_rows_met"] is False
    assert result["required_test_rows"] == 20
    assert result["max_selected_features"] == 123
    assert result["candidate_family"] == "torch"
    assert seen["target_accuracy"] == 0.8
    assert seen["max_selected_features"] == 123
    assert seen["feature_selection_method"] == "stable_tail"
    assert seen["candidate_family"] == "torch"
    assert "overnight_return" in seen["feature_names"]
    assert seen["train_label_max"] <= date(2024, 3, 1)
    assert seen["test_date_min"] >= date(2024, 3, 4)


def test_gpu_probe_prefers_batch_market_data_loader(monkeypatch, make_ohlcv_frame, tmp_path):
    pytest.importorskip("polars")
    import polars as pl

    calls: list[str] = []
    symbols = ["600001", "600002"]

    def _train_and_score(train, test, **kwargs):
        del train, test, kwargs
        return {
            "model": "stub",
            "model_kind": "stub",
            "accuracy": 0.82,
            "brier": 0.2,
            "positive_rate": 0.51,
            "baseline_accuracy": 0.51,
            "baseline_brier": 0.2499,
            "validation_accuracy": 0.81,
            "validation_brier": 0.21,
            "classification_threshold": 0.5,
            "validation_confident_accuracy": 0.84,
            "validation_confident_coverage": 0.4,
            "confidence_low_threshold": 0.35,
            "confidence_high_threshold": 0.65,
            "confident_accuracy": 0.83,
            "confident_brier": 0.18,
            "confident_count": 10,
            "confident_coverage": 0.5,
            "validation_confident_target_met": True,
            "confident_target_met": True,
            "test_oracle_coverage_at_target_accuracy": 0.5,
            "test_oracle_count_at_target_accuracy": 10,
            "test_oracle_target_accuracy": 0.8,
            "test_oracle_note": "stub",
            "candidate_warnings": [],
        }

    frames = []
    for symbol, base in zip(symbols, [10.0, 12.0], strict=True):
        frame = make_ohlcv_frame(symbol=symbol, periods=95, base_price=base, volume_base=8_000_000.0)
        frame["amount"] = frame["volume"] * frame["close"]
        frame["turnover"] = np.linspace(3.0, 10.0, len(frame))
        frames.append(frame)
    market_data = pl.from_pandas(pd.concat(frames, ignore_index=True))

    def _load_market_data(**kwargs):
        calls.append(kwargs["frequency"])
        assert set(kwargs["symbols"]) == set(symbols)
        if kwargs["frequency"] != "daily":
            return pl.DataFrame()
        return market_data

    def _load_bars(symbol, frequency):
        del symbol, frequency
        raise AssertionError("per-symbol loader should not be used when batch loading succeeds")

    monkeypatch.setattr(gpu_probe, "_train_and_score", _train_and_score)
    store = SimpleNamespace(
        list_cached_symbols=lambda frequency: symbols,
        load_market_data=_load_market_data,
        load_bars=_load_bars,
        cache_dir=str(tmp_path),
    )

    result = gpu_probe.run_gpu_next_day_probe(
        store,
        GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 5, 31),
            target_accuracy=0.8,
            short_only=False,
        ),
    )

    assert calls == ["daily"]
    assert result["data_loader"]["mode"] == "polars_batch_load_market_data"


def test_gpu_probe_reuses_feature_cache(monkeypatch, app_config, make_ohlcv_frame):
    pytest.importorskip("polars")
    import polars as pl

    train_calls = 0
    load_calls = 0
    symbols = ["600001", "600002"]

    def _train_and_score(train, test, **kwargs):
        nonlocal train_calls
        del train, test, kwargs
        train_calls += 1
        return {
            "model": "stub",
            "model_kind": "stub",
            "accuracy": 0.82,
            "brier": 0.2,
            "positive_rate": 0.51,
            "baseline_accuracy": 0.51,
            "baseline_brier": 0.2499,
            "validation_accuracy": 0.81,
            "validation_brier": 0.21,
            "classification_threshold": 0.5,
            "validation_confident_accuracy": 0.84,
            "validation_confident_coverage": 0.4,
            "confidence_low_threshold": 0.35,
            "confidence_high_threshold": 0.65,
            "confident_accuracy": 0.83,
            "confident_brier": 0.18,
            "confident_count": 10,
            "confident_coverage": 0.5,
            "validation_confident_target_met": True,
            "confident_target_met": True,
            "test_oracle_coverage_at_target_accuracy": 0.5,
            "test_oracle_count_at_target_accuracy": 10,
            "test_oracle_target_accuracy": 0.8,
            "test_oracle_note": "stub",
            "candidate_warnings": [],
        }

    frames = []
    for symbol, base in zip(symbols, [10.0, 12.0], strict=True):
        frame = make_ohlcv_frame(symbol=symbol, periods=95, base_price=base, volume_base=8_000_000.0)
        frame["amount"] = frame["volume"] * frame["close"]
        frame["turnover"] = np.linspace(3.0, 10.0, len(frame))
        frames.append(frame)
    market_data = pl.from_pandas(pd.concat(frames, ignore_index=True))

    def _load_market_data(**kwargs):
        nonlocal load_calls
        load_calls += 1
        if kwargs["frequency"] != "daily":
            return pl.DataFrame()
        return market_data

    monkeypatch.setattr(gpu_probe, "_train_and_score", _train_and_score)
    store = SimpleNamespace(
        config=app_config,
        cache_dir=app_config.storage.cache_dir,
        list_cached_symbols=lambda frequency: symbols,
        load_market_data=_load_market_data,
        load_bars=lambda symbol, frequency: pytest.fail("load_bars should not be used"),
    )
    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
        target_accuracy=0.8,
        short_only=False,
    )

    first = gpu_probe.run_gpu_next_day_probe(store, config)
    second = gpu_probe.run_gpu_next_day_probe(store, config)

    assert train_calls == 2
    assert load_calls == 1
    assert first["feature_cache"]["written"] is True
    assert second["feature_cache"]["hit"] is True


def test_feature_cache_fingerprint_changes_when_limit_pool_snapshots_change(app_config):
    store = SimpleNamespace(config=app_config)
    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
        short_only=False,
        feature_set="research",
    )
    symbols = ["600001", "600002"]

    before = gpu_probe._feature_cache_descriptor(store, config, symbols=symbols)
    snapshot_dir = app_config.storage.cache_dir / "prediction" / "limit_pool_snapshots" / "trade_date=20260430"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "manifest.json").write_text(
        json.dumps({"trade_date": "20260430", "kinds": {"zt_pool": {"rows": 2}}}),
        encoding="utf-8",
    )

    after = gpu_probe._feature_cache_descriptor(store, config, symbols=symbols)

    assert before["fingerprint"] != after["fingerprint"]
    assert after["limit_pool_snapshot_state"]["status"] == "available"


def test_feature_cache_fingerprint_changes_when_intraday_cache_changes(app_config):
    store = SimpleNamespace(config=app_config)
    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
        short_only=False,
        feature_set="research",
        intraday_factor_frequency="5",
    )
    symbols = ["600001", "600002"]

    before = gpu_probe._feature_cache_descriptor(store, config, symbols=symbols)
    minute_dir = app_config.storage.raw_dir / "bars" / "5"
    minute_dir.mkdir(parents=True, exist_ok=True)
    (minute_dir / "600001.parquet").write_bytes(b"minute-cache-marker")

    after = gpu_probe._feature_cache_descriptor(store, config, symbols=symbols)

    assert before["fingerprint"] != after["fingerprint"]
    assert after["intraday_cache_state"]["status"] == "available"


def test_expanded_feature_cache_fingerprint_changes_when_ths_sector_cache_changes(app_config):
    store = SimpleNamespace(config=app_config)
    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
        short_only=False,
        feature_set="expanded",
    )
    symbols = ["600001", "600002"]

    before = gpu_probe._feature_cache_descriptor(store, config, symbols=symbols)
    ths_dir = app_config.storage.cache_dir / "prediction" / "tushare" / "ths_member"
    ths_dir.mkdir(parents=True, exist_ok=True)
    (ths_dir / "all_members.parquet").write_bytes(b"ths-sector-cache-marker")

    after = gpu_probe._feature_cache_descriptor(store, config, symbols=symbols)

    assert before["fingerprint"] != after["fingerprint"]
    assert after["ths_sector_cache_state"]["status"] == "available"


def test_attach_intraday_factor_features_merges_cached_minute_bars():
    pytest.importorskip("polars")
    import polars as pl

    base = pd.DataFrame(
        {
            "symbol": ["600001", "600001"],
            "date": pd.to_datetime(["2024-04-01", "2024-04-02"]),
            "actual": [1.0, 0.0],
        }
    )
    minute_frame = pd.DataFrame(
        {
            "symbol": ["600001"] * 12,
            "timestamp": pd.date_range("2024-04-01 09:30", periods=12, freq="5min"),
            "open": np.linspace(10.0, 10.2, 12),
            "high": np.linspace(10.1, 10.3, 12),
            "low": np.linspace(9.9, 10.1, 12),
            "close": np.linspace(10.0, 10.4, 12),
            "volume": np.full(12, 1000.0),
        }
    )

    def _load_market_data(**kwargs):
        assert kwargs["frequency"] == "5"
        return pl.from_pandas(minute_frame)

    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
    )

    merged, reports = gpu_probe._attach_intraday_factor_features(
        base,
        store=SimpleNamespace(load_market_data=_load_market_data),
        config=config,
    )

    assert reports[0]["name"] == "intraday_structure"
    assert reports[0]["status"] == "available"
    assert merged.loc[0, "minute_last_30min_return_available"] == pytest.approx(1.0)
    assert merged.loc[1, "minute_last_30min_return_available"] == pytest.approx(0.0)
    assert merged.loc[0, "minute_last_30min_return"] > 0.0


def test_gpu_probe_floors_target_accuracy_at_75(monkeypatch, make_ohlcv_frame, tmp_path):
    seen: dict[str, object] = {}

    def _train_and_score(train, test, **kwargs):
        seen["target_accuracy"] = kwargs["target_accuracy"]
        return {
            "model": "stub",
            "model_kind": "stub",
            "accuracy": 0.7,
            "brier": 0.2,
            "positive_rate": 0.51,
            "baseline_accuracy": 0.51,
            "baseline_brier": 0.2499,
            "validation_accuracy": 0.7,
            "validation_brier": 0.21,
            "classification_threshold": 0.5,
            "validation_confident_accuracy": 0.74,
            "validation_confident_coverage": 0.4,
            "confidence_low_threshold": 0.35,
            "confidence_high_threshold": 0.65,
            "confident_accuracy": 0.74,
            "confident_brier": 0.18,
            "confident_count": 10,
            "confident_coverage": 0.5,
            "validation_confident_target_met": False,
            "confident_target_met": False,
            "test_oracle_coverage_at_target_accuracy": 0.5,
            "test_oracle_count_at_target_accuracy": 10,
            "test_oracle_target_accuracy": 0.75,
            "test_oracle_note": "stub",
            "candidate_warnings": [],
        }

    def _load_bars(symbol, frequency):
        del symbol, frequency
        frame = make_ohlcv_frame(periods=95, base_price=10.0, volume_base=8_000_000.0)
        frame["amount"] = frame["volume"] * frame["close"]
        frame["turnover"] = np.linspace(3.0, 10.0, len(frame))
        return frame

    monkeypatch.setattr(gpu_probe, "_train_and_score", _train_and_score)
    store = SimpleNamespace(list_cached_symbols=lambda frequency: ["600001"], load_bars=_load_bars, cache_dir=str(tmp_path))

    result = gpu_probe.run_gpu_next_day_probe(
        store,
        GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 5, 31),
            target_accuracy=0.5,
            short_only=False,
        ),
    )

    assert result["requested_target_accuracy"] == 0.5
    assert result["target_accuracy"] == 0.75
    assert seen["target_accuracy"] == 0.75


def test_gpu_probe_rejects_overlapping_train_test_dates():
    result = gpu_probe.run_gpu_next_day_probe(
        SimpleNamespace(),
        GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 4),
            test_start=date(2024, 3, 4),
            end=date(2024, 5, 31),
        ),
    )

    assert result["status"] == "invalid_config"
    assert any("train_end" in message for message in result["errors"])


def test_confidence_band_uses_requested_target_accuracy():
    torch = pytest.importorskip("torch")
    prob = torch.tensor([0.95, 0.9, 0.65, 0.55, 0.45, 0.35, 0.1, 0.05])
    y = torch.tensor([1, 1, 0, 1, 0, 1, 0, 0], dtype=torch.float32)

    loose = gpu_probe._best_confidence_band(prob, y, threshold=0.5, target_accuracy=0.75)
    strict = gpu_probe._best_confidence_band(prob, y, threshold=0.5, target_accuracy=1.0)

    assert loose["coverage"] >= strict["coverage"]
    assert strict["accuracy"] >= 1.0


def test_confidence_band_reports_chronological_stability():
    torch = pytest.importorskip("torch")
    prob = torch.linspace(0.02, 0.98, steps=2400)
    y = (prob >= 0.5).to(torch.float32)

    band = gpu_probe._best_confidence_band(
        prob,
        y,
        threshold=0.5,
        target_accuracy=0.75,
        min_count=200,
        min_coverage=0.10,
    )

    assert band["stability_chunks"] > 1
    assert band["stability_min_wilson_lower_95"] <= band["wilson_lower_95"]
    assert "stable_constraint_met" in band


def test_joint_threshold_selection_optimizes_confidence_band_score():
    torch = pytest.importorskip("torch")
    prob = torch.cat(
        [
            torch.full((220,), 0.92),
            torch.full((180,), 0.58),
            torch.full((600,), 0.08),
        ]
    )
    y = torch.cat(
        [
            torch.cat([torch.ones(180), torch.zeros(40)]),
            torch.ones(180),
            torch.zeros(600),
        ]
    ).to(torch.float32)
    target = 0.75
    base_threshold, base_accuracy = gpu_probe._best_threshold(prob, y)
    base_band = gpu_probe._best_confidence_band(
        prob,
        y,
        threshold=base_threshold,
        target_accuracy=target,
        min_count=100,
        min_coverage=0.10,
    )

    threshold, accuracy, band = gpu_probe._best_threshold_and_confidence_band(
        prob,
        y,
        target_accuracy=target,
        min_count=100,
        min_coverage=0.10,
    )

    base_score = gpu_probe._candidate_selection_score(
        base_accuracy,
        gpu_probe._brier(prob, y),
        base_band,
        target_accuracy=target,
    )
    joint_score = gpu_probe._candidate_selection_score(
        accuracy,
        gpu_probe._brier(prob, y),
        band,
        target_accuracy=target,
    )
    assert 0.25 <= threshold <= 0.75
    assert joint_score >= base_score
    assert "wilson_lower_95" in band


def test_confidence_selector_prefers_agreement_when_probability_band_is_unstable():
    probability = {
        "method": "probability_band",
        "eligible": False,
        "validation_accuracy": 0.69,
        "validation_wilson_lower_95": 0.67,
        "validation_stability_min_wilson_lower_95": 0.60,
        "validation_coverage": 0.12,
        "validation_count": 2400,
    }
    agreement = {
        "method": "candidate_agreement",
        "eligible": False,
        "validation_accuracy": 0.66,
        "validation_wilson_lower_95": 0.65,
        "validation_coverage": 0.12,
        "validation_count": 2400,
    }

    selected, mask = gpu_probe._select_confidence_selector([(probability, "band"), (agreement, "agree")])

    assert selected["method"] == "candidate_agreement"
    assert mask == "agree"


def test_confidence_selector_treats_zero_stability_as_real_zero():
    unstable_pair = {
        "method": "pair_regime_probability_gate",
        "eligible": False,
        "validation_accuracy": 0.70,
        "validation_wilson_lower_95": 0.68,
        "validation_stability_min_wilson_lower_95": 0.0,
        "validation_coverage": 0.12,
        "validation_count": 2400,
    }
    agreement = {
        "method": "candidate_agreement",
        "eligible": False,
        "validation_accuracy": 0.64,
        "validation_wilson_lower_95": 0.62,
        "validation_coverage": 0.12,
        "validation_count": 2400,
    }

    selected, mask = gpu_probe._select_confidence_selector([(unstable_pair, "pair"), (agreement, "agree")])

    assert selected["method"] == "candidate_agreement"
    assert mask == "agree"


def test_train_prediction_blocks_without_passed_gpu_probe_artifact(app_config):
    service = PredictionService(
        config=app_config,
        store=SimpleNamespace(),
        data_service=SimpleNamespace(),
        feature_service=SimpleNamespace(),
        search_service=SimpleNamespace(),
    )

    result = service.train_model()

    assert result["status"] == "blocked"
    assert result["acceptance"] == "failed"


def test_train_prediction_reads_passed_gpu_probe_artifact(app_config):
    artifact_dir = app_config.storage.report_dir / "prediction"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artifact_dir / "gpu_probe_passed_latest.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-29T00:00:00+00:00",
                "result": {
                    "model": "stub",
                    "accuracy": 0.76,
                    "brier": 0.2,
                    "baseline_brier": 0.24,
                    "test_rows": 50_000,
                    "target_accuracy": 0.75,
                    "acceptance": {"passed": True, "lockbox_role": "final_unseen", "final_acceptance_eligible": True},
                },
            }
        ),
        encoding="utf-8",
    )
    service = PredictionService(
        config=app_config,
        store=SimpleNamespace(),
        data_service=SimpleNamespace(),
        feature_service=SimpleNamespace(),
        search_service=SimpleNamespace(),
    )

    result = service.train_model()

    assert result["status"] == "ready_for_global_fit"
    assert result["acceptance"] == "passed"
    assert result["gate_artifact"]["test_rows"] == 50_000
    assert result["gate_artifact"]["lockbox_role"] == "final_unseen"


def test_train_prediction_rejects_seen_research_passed_artifact(app_config):
    artifact_dir = app_config.storage.report_dir / "prediction"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artifact_dir / "gpu_probe_passed_latest.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-29T00:00:00+00:00",
                "result": {
                    "model": "stub",
                    "accuracy": 0.76,
                    "brier": 0.2,
                    "baseline_brier": 0.24,
                    "test_rows": 50_000,
                    "target_accuracy": 0.75,
                    "acceptance": {"passed": True, "lockbox_role": "seen_research", "final_acceptance_eligible": False},
                },
            }
        ),
        encoding="utf-8",
    )
    service = PredictionService(
        config=app_config,
        store=SimpleNamespace(),
        data_service=SimpleNamespace(),
        feature_service=SimpleNamespace(),
        search_service=SimpleNamespace(),
    )

    result = service.train_model()

    assert result["status"] == "blocked"
    assert result["acceptance"] == "failed"


def test_train_prediction_reads_immutable_passed_run_pointer(app_config):
    artifact_dir = app_config.storage.report_dir / "prediction"
    run_dir = artifact_dir / "runs" / "run-123"
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "artifact.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-29T00:00:00+00:00",
                "run_id": "run-123",
                "code_hash": "code",
                "feature_hash": "features",
                "data_hash": "data",
                "split_hash": "split",
                "result": {
                    "run_id": "run-123",
                    "model": "stub",
                    "accuracy": 0.76,
                    "confident_accuracy": 0.81,
                    "confident_count": 12_000,
                    "brier": 0.2,
                    "baseline_brier": 0.24,
                    "test_rows": 50_000,
                    "target_accuracy": 0.75,
                    "acceptance": {"passed": True, "lockbox_role": "final_unseen", "final_acceptance_eligible": True},
                },
            }
        ),
        encoding="utf-8",
    )
    (artifact_dir / "gpu_probe_passed_latest.json").write_text(
        json.dumps({"run_id": "run-123", "artifact": str(artifact), "passed": True}),
        encoding="utf-8",
    )
    service = PredictionService(
        config=app_config,
        store=SimpleNamespace(),
        data_service=SimpleNamespace(),
        feature_service=SimpleNamespace(),
        search_service=SimpleNamespace(),
    )

    result = service.train_model(approved_run_id="run-123")

    assert result["status"] == "ready_for_global_fit"
    assert result["approved_run_id"] == "run-123"
    assert result["gate_artifact"]["feature_hash"] == "features"


def test_next_high_from_close_label_marks_intraday_high_1pct_even_if_close_drops(make_ohlcv_frame):
    torch = pytest.importorskip("torch")
    frame = make_ohlcv_frame(periods=90, base_price=10.0, volume_base=5_000_000.0)
    frame["amount"] = frame["volume"] * frame["close"]
    frame["turnover"] = np.linspace(3.0, 10.0, len(frame))

    t_idx = len(frame) - 2
    t1_idx = len(frame) - 1
    t_close = 10.00
    frame.loc[t_idx, "close"] = t_close
    frame.loc[t1_idx, "open"] = t_close * 1.005
    frame.loc[t1_idx, "high"] = t_close * 1.012
    frame.loc[t1_idx, "low"] = t_close * 0.97
    frame.loc[t1_idx, "close"] = t_close * 0.985

    features_high = gpu_probe._symbol_feature_frame(
        frame,
        symbol="600519",
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
        device=torch.device("cpu"),
        config=GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 12, 31),
            short_only=False,
            label_target="next_high_from_close",
            target_high_return_pct=1.0,
        ),
    )
    features_close = gpu_probe._symbol_feature_frame(
        frame,
        symbol="600519",
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
        device=torch.device("cpu"),
        config=GpuProbeConfig(
            start=date(2024, 1, 1),
            train_end=date(2024, 3, 1),
            test_start=date(2024, 3, 4),
            end=date(2024, 12, 31),
            short_only=False,
            label_target="next_close_up",
        ),
    )

    t_date = frame.loc[t_idx, "date"]
    row_high = features_high[features_high["date"] == t_date]
    row_close = features_close[features_close["date"] == t_date]
    assert not row_high.empty, f"T-date {t_date} missing from next_high_from_close features"
    assert not row_close.empty, f"T-date {t_date} missing from next_close_up features"
    assert float(row_high.iloc[0]["actual"]) == 1.0
    assert float(row_close.iloc[0]["actual"]) == 0.0
    assert float(row_high.iloc[0]["next_high_return_pct"]) == pytest.approx(1.2, abs=0.5)
    assert float(row_high.iloc[0]["next_close_return_pct"]) < 0.0
    assert float(row_high.iloc[0]["next_close_up"]) == 0.0


def test_acceptance_coverage_gate_requires_both_count_and_coverage():
    result_high_count_low_coverage = {
        "accuracy": 0.80,
        "correct_count": 40_000,
        "brier": 0.20,
        "baseline_brier": 0.24,
        "confident_accuracy": 0.85,
        "confident_correct_count": 8_500,
        "confident_brier": 0.18,
        "confident_count": 10_000,
        "confident_coverage": 0.05,
    }
    accepted_both = gpu_probe._acceptance_summary(
        {**result_high_count_low_coverage, "confident_coverage": 0.20},
        test_rows=50_000,
        required_test_rows=50_000,
        target_accuracy=0.75,
    )
    fail_low_coverage = gpu_probe._acceptance_summary(
        result_high_count_low_coverage,
        test_rows=50_000,
        required_test_rows=50_000,
        target_accuracy=0.75,
    )
    fail_low_count = gpu_probe._acceptance_summary(
        {**result_high_count_low_coverage, "confident_count": 5_000, "confident_correct_count": 4_250, "confident_coverage": 0.20},
        test_rows=50_000,
        required_test_rows=50_000,
        target_accuracy=0.75,
    )

    assert accepted_both["high_confidence"]["coverage_gate_met"] is True
    assert fail_low_coverage["high_confidence"]["coverage_gate_met"] is False
    assert fail_low_coverage["passed"] is False
    assert fail_low_count["high_confidence"]["coverage_gate_met"] is False
    assert fail_low_count["passed"] is False


def test_seen_research_cannot_final_pass():
    result = {
        "accuracy": 0.82,
        "correct_count": 98_400,
        "brier": 0.20,
        "baseline_brier": 0.24,
        "confident_accuracy": 0.85,
        "confident_correct_count": 10_200,
        "confident_brier": 0.17,
        "confident_count": 12_000,
        "confident_coverage": 0.10,
    }
    accepted = gpu_probe._acceptance_summary(
        result,
        test_rows=120_000,
        required_test_rows=120_000,
        target_accuracy=0.75,
        lockbox_role="seen_research",
    )
    assert accepted["passed"] is False
    assert accepted["status"] == "research_only"
    assert accepted["passed_without_lockbox_role_gate"] is True
    assert accepted["lockbox_role"] == "seen_research"
    assert accepted["lockbox_role_gate_met"] is False
    assert accepted["final_acceptance_eligible"] is False


def test_final_unseen_reused_lockbox_rejected_by_ledger(app_config):
    split_manifest = {
        "lockbox_identity_hash": "reuse-check-identity",
        "split_hash": "research-split-hash",
        "train_end": "2024-03-01",
        "test_start": "2024-04-01",
        "end": "2024-04-30",
        "test_event_start": "2024-04-01",
        "test_event_end": "2024-04-30",
        "test_lockbox_rows": 120_000,
    }
    directory = app_config.storage.report_dir / "prediction"
    artifact = directory / "runs" / "research-run" / "acceptance.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}", encoding="utf-8")
    gpu_probe._append_lockbox_ledger_record(
        directory,
        {
            "run_id": "research-run",
            "status": "completed",
            "lockbox_role": "seen_research",
            "acceptance": {"passed": False, "status": "research_only"},
            "split_manifest": split_manifest,
            "split_hash": "research-split-hash",
        },
        artifact_path=artifact,
    )

    final_config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 4, 1),
        end=date(2024, 4, 30),
        lockbox_role="final_unseen",
    )
    ledger = gpu_probe._lockbox_ledger_status(
        SimpleNamespace(config=app_config),
        split_manifest=split_manifest,
        config=final_config,
    )
    acceptance = gpu_probe._acceptance_summary(
        {
            "accuracy": 0.82,
            "brier": 0.19,
            "baseline_brier": 0.24,
            "confident_accuracy": 0.88,
            "confident_brier": 0.15,
            "confident_count": 120_000,
            "confident_correct_count": 105_600,
            "confident_coverage": 1.0,
        },
        test_rows=120_000,
        required_test_rows=120_000,
        target_accuracy=0.75,
        lockbox_role="final_unseen",
        lockbox_ledger=ledger,
    )

    assert ledger["gate_met"] is False
    assert "research-run" in ledger["observed_run_ids"]
    assert acceptance["passed"] is False
    assert acceptance["status"] == "lockbox_reused"
    assert acceptance["passed_without_lockbox_ledger_gate"] is True
    assert acceptance["final_acceptance_eligible"] is False


def test_default_test_rows_consistent_with_hc_gate():
    import math
    default_config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 4, 1),
        end=date(2024, 6, 30),
    )
    min_implied = math.ceil(
        gpu_probe.MIN_GPU_PROBE_HIGH_CONFIDENCE_ROWS
        / gpu_probe.MIN_GPU_PROBE_HIGH_CONFIDENCE_COVERAGE
    )
    assert min_implied == 100_000
    assert default_config.test_rows >= min_implied
    assert default_config.test_rows == gpu_probe.RECOMMENDED_GPU_PROBE_TEST_ROWS
    assert default_config.test_rows == 120_000


def test_acceptance_output_no_desired_test_rows_field():
    result = {
        "accuracy": 0.80,
        "correct_count": 96_000,
        "brier": 0.20,
        "baseline_brier": 0.24,
        "confident_accuracy": 0.85,
        "confident_correct_count": 10_200,
        "confident_brier": 0.18,
        "confident_count": 12_000,
        "confident_coverage": 0.10,
    }
    accepted = gpu_probe._acceptance_summary(
        result,
        test_rows=120_000,
        required_test_rows=120_000,
        target_accuracy=0.75,
    )
    assert "desired_test_rows" not in accepted
    assert "legacy_default_test_rows" in accepted
    assert accepted["legacy_default_test_rows"] == 50_000
    assert "minimum_test_rows_implied_by_hc_gate" in accepted
    assert accepted["minimum_test_rows_implied_by_hc_gate"] == 100_000


def test_50k_samples_with_10pct_coverage_fails_count_gate():
    result = {
        "accuracy": 0.80,
        "correct_count": 40_000,
        "brier": 0.20,
        "baseline_brier": 0.24,
        "confident_accuracy": 0.85,
        "confident_correct_count": 4_250,
        "confident_brier": 0.18,
        "confident_count": 5_000,
        "confident_coverage": 0.10,
    }
    accepted = gpu_probe._acceptance_summary(
        result,
        test_rows=50_000,
        required_test_rows=50_000,
        target_accuracy=0.75,
    )
    assert accepted["high_confidence"]["coverage_gate_met"] is False
    assert accepted["high_confidence"]["rows"] == 5_000
    assert accepted["passed"] is False


def test_120k_samples_passes_research_quality_gates():
    result = {
        "accuracy": 0.80,
        "correct_count": 96_000,
        "brier": 0.20,
        "baseline_brier": 0.24,
        "confident_accuracy": 0.85,
        "confident_correct_count": 10_200,
        "confident_brier": 0.18,
        "confident_count": 12_000,
        "confident_coverage": 0.10,
    }
    accepted = gpu_probe._acceptance_summary(
        result,
        test_rows=120_000,
        required_test_rows=120_000,
        target_accuracy=0.75,
        lockbox_role="seen_research",
    )
    assert accepted["high_confidence"]["coverage_gate_met"] is True
    assert accepted["high_confidence"]["statistical_rows_met"] is True
    assert accepted["high_confidence"]["wilson_lower_met"] is True
    assert accepted["high_confidence"]["brier_beats_baseline"] is True
    assert accepted["passed_without_lockbox_role_gate"] is True
    assert accepted["passed"] is False
    assert accepted["status"] == "research_only"


def test_event_limit_up_filter_removes_limit_up_rows():
    data = pd.DataFrame({
        "symbol": ["600001", "600002", "600003", "600004"],
        "date": pd.to_datetime(["2024-01-02"] * 4),
        "limit_up_like": [1.0, 0.0, 0.4, 0.6],
        "actual": [1.0, 0.0, 1.0, 1.0],
    })
    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
        exclude_event_limit_up=True,
    )

    filtered, report = gpu_probe._apply_event_limit_up_filter(data, config)

    assert report["enabled"] is True
    assert report["status"] == "applied"
    assert report["rows_before"] == 4
    assert report["rows_after"] == 2
    assert report["dropped_rows"] == 2
    assert set(filtered["symbol"].tolist()) == {"600002", "600003"}


def test_event_limit_up_filter_disabled_keeps_all_rows():
    data = pd.DataFrame({
        "symbol": ["600001", "600002"],
        "date": pd.to_datetime(["2024-01-02"] * 2),
        "limit_up_like": [1.0, 0.0],
        "actual": [1.0, 0.0],
    })
    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
        exclude_event_limit_up=False,
    )

    filtered, report = gpu_probe._apply_event_limit_up_filter(data, config)

    assert report["enabled"] is False
    assert report["status"] == "disabled"
    assert len(filtered) == 2


def test_event_limit_up_filter_hard_fails_on_missing_column():
    data = pd.DataFrame({
        "symbol": ["600001"],
        "date": pd.to_datetime(["2024-01-02"]),
        "actual": [1.0],
    })
    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
        exclude_event_limit_up=True,
    )

    with pytest.raises(ValueError, match="limit_up_like"):
        gpu_probe._apply_event_limit_up_filter(data, config)


def test_methodology_audit_includes_event_limit_up_filter():
    config = GpuProbeConfig(
        start=date(2024, 1, 1),
        train_end=date(2024, 3, 1),
        test_start=date(2024, 3, 4),
        end=date(2024, 5, 31),
        exclude_event_limit_up=True,
    )

    audit = gpu_probe._methodology_audit_summary(
        config,
        feature_cache={"fingerprint": "abc123"},
        active_rank_filter={"enabled": False},
        event_limit_up_filter={"enabled": True, "rows_before": 1000, "rows_after": 900, "dropped_rows": 100},
        external_factors=[],
    )

    assert audit["executable_only_protocol"]["exclude_event_limit_up"] is True
    assert audit["executable_only_protocol"]["candidate_pool"] == "executable_only"
    assert audit["feature_cache_policy"]["event_limit_up_filter_stage"] == "post_feature_cache_pre_split"
    assert audit["sample_gate"]["exclude_event_limit_up"] is True


def _make_stub_test_predictions_df(n: int = 20) -> pd.DataFrame:
    dates = pd.date_range("2024-03-04", periods=n, freq="B")
    return pd.DataFrame({
        "symbol": [f"60000{i % 5 + 1}" for i in range(n)],
        "date": dates,
        "label_date": dates + pd.offsets.BDay(1),
        "probability": np.linspace(0.3, 0.9, n),
        "predicted_label": np.array([0] * (n // 2) + [1] * (n - n // 2), dtype=np.int8),
        "confident": np.array([0] * (n - 5) + [1] * 5, dtype=np.int8),
        "confidence_side": "both",
        "actual": np.array([0] * (n // 2) + [1] * (n - n // 2), dtype=np.int8),
        "threshold": 0.5,
        "close": np.linspace(10.0, 15.0, n),
        "limit_up_like": np.zeros(n),
    })


def test_write_gpu_probe_artifacts_saves_test_predictions_parquet(app_config):
    store = SimpleNamespace(config=app_config)
    pred_df = _make_stub_test_predictions_df(20)
    result = {
        "_test_predictions_df": pred_df,
        "model": "stub",
        "model_kind": "stub",
        "accuracy": 0.8,
        "brier": 0.2,
        "acceptance": {"passed": False, "status": "research_only"},
        "lockbox_role": "seen_research",
        "final_acceptance_eligible": False,
        "feature_set": "expanded",
        "features": ["close"],
        "feature_cache": {},
        "external_factors": [],
        "data_loader": {},
        "rows_total": 100,
        "symbols_considered": 5,
        "symbol_frames_kept": 5,
        "split_manifest": {},
        "selector_coverage_weight": 0.02,
        "candidate_family": "all",
    }
    artifacts = gpu_probe._write_gpu_probe_artifacts(store, result)

    assert "test_predictions" in artifacts, "Artifacts must include test_predictions path"
    pred_path = artifacts["test_predictions"]
    assert pred_path.endswith("test_predictions.parquet")

    import pyarrow.parquet as pq
    table = pq.read_table(pred_path)
    df = table.to_pandas()
    assert len(df) == 20
    required_cols = {"symbol", "date", "probability", "confident", "actual", "limit_up_like"}
    assert required_cols.issubset(set(df.columns)), f"Missing columns: {required_cols - set(df.columns)}"
    assert int(df["confident"].sum()) == 5

    assert result["test_predictions_path"] == pred_path
    assert result["test_predictions_rows"] == 20
    assert result["high_confident_rows"] == 5


def test_write_gpu_probe_artifacts_handles_missing_predictions(app_config):
    store = SimpleNamespace(config=app_config)
    result = {
        "model": "stub",
        "model_kind": "stub",
        "accuracy": 0.8,
        "brier": 0.2,
        "acceptance": {"passed": False, "status": "research_only"},
        "lockbox_role": "seen_research",
        "final_acceptance_eligible": False,
        "feature_set": "expanded",
        "features": ["close"],
        "feature_cache": {},
        "external_factors": [],
        "data_loader": {},
        "rows_total": 100,
        "symbols_considered": 5,
        "symbol_frames_kept": 5,
        "split_manifest": {},
        "selector_coverage_weight": 0.02,
        "candidate_family": "all",
    }
    artifacts = gpu_probe._write_gpu_probe_artifacts(store, result)

    assert "test_predictions" not in artifacts
    assert "test_predictions_path" not in result


def test_test_predictions_confident_count_matches_metrics(app_config):
    store = SimpleNamespace(config=app_config)
    pred_df = _make_stub_test_predictions_df(30)
    pred_df.loc[pred_df.index[-8:], "confident"] = 1
    pred_df.loc[pred_df.index[:-8], "confident"] = 0
    expected_hc = 8
    result = {
        "_test_predictions_df": pred_df,
        "model": "stub",
        "model_kind": "stub",
        "accuracy": 0.8,
        "brier": 0.2,
        "acceptance": {"passed": False, "status": "research_only"},
        "lockbox_role": "seen_research",
        "final_acceptance_eligible": False,
        "feature_set": "expanded",
        "features": ["close"],
        "feature_cache": {},
        "external_factors": [],
        "data_loader": {},
        "rows_total": 100,
        "symbols_considered": 5,
        "symbol_frames_kept": 5,
        "split_manifest": {},
        "selector_coverage_weight": 0.02,
        "candidate_family": "all",
    }
    gpu_probe._write_gpu_probe_artifacts(store, result)

    assert result["high_confident_rows"] == expected_hc

    import pyarrow.parquet as pq
    df = pq.read_table(result["test_predictions_path"]).to_pandas()
    assert int(df["confident"].sum()) == expected_hc


def test_test_predictions_filterable_by_date(app_config):
    store = SimpleNamespace(config=app_config)
    pred_df = _make_stub_test_predictions_df(20)
    target_date = pred_df["date"].iloc[5]
    result = {
        "_test_predictions_df": pred_df,
        "model": "stub",
        "model_kind": "stub",
        "accuracy": 0.8,
        "brier": 0.2,
        "acceptance": {"passed": False, "status": "research_only"},
        "lockbox_role": "seen_research",
        "final_acceptance_eligible": False,
        "feature_set": "expanded",
        "features": ["close"],
        "feature_cache": {},
        "external_factors": [],
        "data_loader": {},
        "rows_total": 100,
        "symbols_considered": 5,
        "symbol_frames_kept": 5,
        "split_manifest": {},
        "selector_coverage_weight": 0.02,
        "candidate_family": "all",
    }
    gpu_probe._write_gpu_probe_artifacts(store, result)

    import pyarrow.parquet as pq
    df = pq.read_table(result["test_predictions_path"]).to_pandas()
    day_df = df[df["date"] == target_date]
    assert len(day_df) > 0, "Should be able to filter test_predictions by a specific date"
    assert "symbol" in day_df.columns
    assert "probability" in day_df.columns
    assert "confident" in day_df.columns
    assert "actual" in day_df.columns

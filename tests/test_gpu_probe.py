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
    assert "decline_stabilize_signal" not in expanded
    assert "cycle_day_count" in expanded
    assert "market_cycle_failed_pressure" in expanded
    assert "daily_amount_300m_gate" in expanded
    assert "volume_price_match" in expanded
    assert "chase_market_up_alignment" in expanded
    assert "second_board_leader_proxy" in expanded
    assert "money_effect_chase_alignment" not in expanded
    assert "collapse_hot_stock_risk" not in expanded
    assert "market_limit_down_rate" in research
    assert "explosive_vol_next_weak" in research
    assert "stock_personality_score" in research
    assert "highlight_score" in research
    assert "former_leader_recall" in research
    assert "cs_low_price_advantage" in research
    assert "ma5_pullback_entry" in research
    assert "decline_stabilize_signal" in research
    assert "money_effect_chase_alignment" in research
    assert "collapse_warning_signal" in research
    assert len(research) > len(expanded)


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

    assert accepted["passed"] is True
    assert too_few_rows["passed"] is True
    assert too_few_rows["sample_size_target_met"] is False
    assert too_few_rows["sample_size_required_for_pass"] is False
    assert accepted["high_confidence"]["wilson_lower_met"] is True
    assert tiny_confident["passed"] is False
    assert tiny_confident["high_confidence"]["statistical_rows_met"] is False
    assert weak_brier["passed"] is False
    assert future_filtered["passed"] is False


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
        }
    )

    out = gpu_probe._add_cross_section_features(frame)

    assert out["cs_limit_up_rate"].iloc[0] == pytest.approx(0.25)
    assert out["cs_limit_down_rate"].iloc[0] == pytest.approx(0.25)
    assert out["cs_big_up_rate"].iloc[0] == pytest.approx(0.5)
    assert out["cs_failed_limit_up_rate"].iloc[0] == pytest.approx(0.25)
    assert "cs_emotion_score" in out.columns
    assert "market_cycle_failed_pressure" in out.columns
    assert "market_hot_cycle_short_pressure" in out.columns
    assert "cs_low_price_advantage" in out.columns
    assert "cs_reversal_day_leader_quality" in out.columns


def test_run_gpu_probe_threads_target_accuracy_into_training(monkeypatch, make_ohlcv_frame):
    seen: dict[str, object] = {}
    symbols = ["600001", "600002"]

    def _train_and_score(train, test, **kwargs):
        seen["target_accuracy"] = kwargs["target_accuracy"]
        seen["max_selected_features"] = kwargs["max_selected_features"]
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
    store = SimpleNamespace(list_cached_symbols=lambda frequency: symbols, load_bars=_load_bars)

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
        ),
    )

    assert result["status"] == "completed"
    assert result["target_met"] is False
    assert result["acceptance"]["passed"] is False
    assert result["acceptance"]["sample_size_required_for_pass"] is False
    assert result["acceptance"]["high_confidence"]["statistical_rows_met"] is False
    assert result["required_test_rows"] == 20
    assert result["max_selected_features"] == 123
    assert seen["target_accuracy"] == 0.8
    assert seen["max_selected_features"] == 123
    assert "overnight_return" in seen["feature_names"]
    assert seen["train_label_max"] <= date(2024, 3, 1)
    assert seen["test_date_min"] >= date(2024, 3, 4)


def test_gpu_probe_prefers_batch_market_data_loader(monkeypatch, make_ohlcv_frame):
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
        calls.append("batch")
        assert set(kwargs["symbols"]) == set(symbols)
        return market_data

    def _load_bars(symbol, frequency):
        del symbol, frequency
        raise AssertionError("per-symbol loader should not be used when batch loading succeeds")

    monkeypatch.setattr(gpu_probe, "_train_and_score", _train_and_score)
    store = SimpleNamespace(
        list_cached_symbols=lambda frequency: symbols,
        load_market_data=_load_market_data,
        load_bars=_load_bars,
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

    assert calls == ["batch"]
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
        del kwargs
        load_calls += 1
        return market_data

    monkeypatch.setattr(gpu_probe, "_train_and_score", _train_and_score)
    store = SimpleNamespace(
        config=app_config,
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


def test_gpu_probe_floors_target_accuracy_at_75(monkeypatch, make_ohlcv_frame):
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
    store = SimpleNamespace(list_cached_symbols=lambda frequency: ["600001"], load_bars=_load_bars)

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
                    "acceptance": {"passed": True},
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
                    "acceptance": {"passed": True},
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

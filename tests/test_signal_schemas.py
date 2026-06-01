from __future__ import annotations

from ashare_similarity.prediction.signals.schemas import (
    BacktestSummaryResponse,
    DailySeriesPoint,
    DailySignalResponse,
    ModelBacktestSummary,
    SignalDateListResponse,
    SignalRow,
    SignalStatusResponse,
    SplitLayerStats,
    StockSignalResponse,
)


def test_signal_row_round_trip() -> None:
    row = SignalRow(
        date="2025-08-01",
        symbol="600519",
        name="贵州茅台",
        model_tag="accuracy_priority",
        best_model="gpu_logistic",
        selector_method="candidate_agreement",
        probability=0.72,
        confident=True,
        actual=1.0,
        correct=True,
        split_layer="dev_valid",
    )
    dumped = row.model_dump()
    restored = SignalRow(**dumped)
    assert restored.symbol == "600519"
    assert restored.confident is True
    assert restored.correct is True


def test_signal_row_correct_none() -> None:
    row = SignalRow(
        date="2025-08-01", symbol="000001", name="", model_tag="t",
        best_model="m", selector_method="s", probability=0.5,
        confident=False, actual=0.0, correct=None, split_layer="dev_valid",
    )
    assert row.correct is None


def test_signal_status_response() -> None:
    r = SignalStatusResponse(status="not_built", candidates=[], research_only=True)
    assert r.status == "not_built"
    assert r.date_range is None


def test_signal_date_list_response() -> None:
    r = SignalDateListResponse(dates=["2025-07-01", "2025-07-02"], count=2)
    assert r.count == 2


def test_daily_signal_response() -> None:
    r = DailySignalResponse(date="2025-07-01", split_layer="dev_valid", signals=[], summary={})
    dumped = r.model_dump()
    assert dumped["date"] == "2025-07-01"


def test_split_layer_stats() -> None:
    s = SplitLayerStats(
        layer="dev_valid", total_rows=1000, confident_count=100,
        confident_accuracy=0.80, confident_coverage=0.10,
        wilson_lower_95=0.72, brier=0.18, baseline_brier=0.23,
    )
    assert s.confident_accuracy == 0.80


def test_backtest_summary_response_serializable() -> None:
    bsr = BacktestSummaryResponse(
        by_model=[
            ModelBacktestSummary(
                model_tag="t", best_model="m", selector_method="s",
                by_layer=[], artifact_reference={},
            )
        ],
        daily_series=[],
        data_range=["2025-07-01", "2026-04-23"],
        research_only=True,
    )
    dumped = bsr.model_dump()
    assert dumped["research_only"] is True

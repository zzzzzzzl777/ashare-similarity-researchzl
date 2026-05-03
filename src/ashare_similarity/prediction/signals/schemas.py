from __future__ import annotations

from pydantic import BaseModel


class SignalRow(BaseModel):
    date: str
    symbol: str
    name: str
    model_tag: str
    best_model: str
    selector_method: str
    probability: float
    confident: bool
    actual: float
    correct: bool | None = None
    split_layer: str


class SplitLayerStats(BaseModel):
    layer: str
    total_rows: int
    confident_count: int
    confident_accuracy: float
    confident_coverage: float
    wilson_lower_95: float
    brier: float
    baseline_brier: float


class ModelBacktestSummary(BaseModel):
    model_tag: str
    best_model: str
    selector_method: str
    by_layer: list[SplitLayerStats]
    artifact_reference: dict


class DailySeriesPoint(BaseModel):
    date: str
    model_tag: str
    accuracy: float | None = None
    coverage: float
    confident_count: int
    split_layer: str


class SignalStatusResponse(BaseModel):
    status: str
    cache_generated_at: str | None = None
    candidates: list[str]
    date_range: list[str] | None = None
    research_only: bool
    sample_symbols: list[str] | None = None


class SignalDateListResponse(BaseModel):
    dates: list[str]
    count: int


class DailySignalResponse(BaseModel):
    date: str
    split_layer: str
    signals: list[SignalRow]
    summary: dict


class StockSignalResponse(BaseModel):
    symbol: str
    name: str
    predictions: list[SignalRow]
    summary_by_model: dict
    message: str | None = None


class BacktestSummaryResponse(BaseModel):
    by_model: list[ModelBacktestSummary]
    daily_series: list[DailySeriesPoint]
    data_range: list[str]
    research_only: bool

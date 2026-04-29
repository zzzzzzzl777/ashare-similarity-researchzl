from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


Frequency = Literal["daily", "1", "5", "15", "30", "60"]
SearchScope = Literal["historical", "all"]


class SearchRequest(BaseModel):
    symbol: str = Field(..., description="A-share stock code or stock name, for example 600519 or 贵州茅台")
    end_date: date | datetime = Field(..., description="Window end date")
    frequency: Frequency = Field(default="daily")
    window_size: int = Field(..., ge=3, le=240)
    top_k: int = Field(default=10, ge=1, le=50)
    search_scope: SearchScope = Field(
        default="historical",
        description="historical excludes windows overlapping the query date range; all includes same-period cross-sectional windows",
    )


class PredictionRequest(BaseModel):
    symbol: str = Field(..., description="A-share stock code or stock name")
    as_of_date: date | datetime = Field(..., description="Prediction anchor date; features may only use data up to this date")
    frequency: Frequency = Field(default="daily")
    horizons: list[int] = Field(default_factory=lambda: [1, 2])
    window_sizes: list[int] = Field(default_factory=lambda: [5, 8, 10, 20])
    top_k: int = Field(default=100, ge=10, le=200)

    @model_validator(mode="after")
    def validate_prediction_scope(self) -> "PredictionRequest":
        self.symbol = self.symbol.strip()
        self.horizons = sorted({int(horizon) for horizon in self.horizons})
        self.window_sizes = sorted({int(window_size) for window_size in self.window_sizes})
        if self.frequency != "daily":
            raise ValueError("一期预测只支持日线。")
        if any(horizon not in {1, 2} for horizon in self.horizons):
            raise ValueError("一期预测只支持未来 1/2 个交易日。")
        if not self.window_sizes or any(window_size < 3 or window_size > 240 for window_size in self.window_sizes):
            raise ValueError("window_sizes 必须在 3 到 240 之间。")
        return self


class DataFreshness(BaseModel):
    last_refresh_at: datetime | None = None
    latest_data_at: datetime | None = None
    data_source: str
    notice: str | None = None


class BackfillFailure(BaseModel):
    symbol: str
    error: str | None = None
    attempted_at: datetime | None = None


class BackfillStatus(BaseModel):
    run_id: str
    frequency: Frequency
    status: Literal["running", "completed", "partial"]
    batch_size: int
    requested_symbols: int
    attempted_symbols: int
    completed_symbols: int
    failed_symbols: int
    skipped_recent_listing: int = 0
    ignored_st_symbols: int = 0
    remaining_symbols: int
    processed_count: int = 0
    cursor: int | None = None
    next_cursor: int | None = None
    resume_cursor: int | None = None
    started_at: datetime
    finished_at: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    last_symbol: str | None = None
    retry_failures: bool = False
    sample_failures: list[BackfillFailure] = Field(default_factory=list)


class CacheStatus(BaseModel):
    frequency: Frequency
    cached_symbols: int
    data_freshness: DataFreshness


class SystemStatus(BaseModel):
    universe_count: int
    filtered_universe_count: int
    cache_status: dict[str, CacheStatus]
    index_status: dict[str, dict[str, Any]]
    index_health: dict[str, dict[str, Any]] = Field(default_factory=dict)
    latest_backfill: BackfillStatus | None = None


class ScoreBreakdown(BaseModel):
    balanced: float
    shape: float
    price_path_distance: float
    candle_geometry_distance: float
    volume_liquidity_distance: float
    environment_distance: float


class ForwardStats(BaseModel):
    horizon: int
    return_pct: float | None
    max_favorable_excursion_pct: float | None
    max_drawdown_pct: float | None


class MatchSeries(BaseModel):
    dates: list[str]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    volume: list[float]


class MatchResult(BaseModel):
    symbol: str
    name: str | None = None
    frequency: Frequency
    start_date: str
    end_date: str
    listing_days: int | None = None
    industry: str | None = None
    scores: ScoreBreakdown
    forward_stats: list[ForwardStats]
    series: MatchSeries
    explanation: list[str] = Field(default_factory=list)


class AggregateForwardStat(BaseModel):
    horizon: int
    avg_return_pct: float | None
    win_rate: float | None
    avg_max_favorable_excursion_pct: float | None
    avg_max_drawdown_pct: float | None


class QueryMeta(BaseModel):
    symbol: str
    frequency: Frequency
    window_size: int
    start_date: str
    end_date: str
    query_series: MatchSeries
    universe_size: int
    candidate_pool_size: int
    filters: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query_meta: QueryMeta
    balanced_matches: list[MatchResult]
    shape_matches: list[MatchResult]
    aggregate_forward_stats: list[AggregateForwardStat]
    data_freshness: DataFreshness
    warnings: list[str] = Field(default_factory=list)


class PredictionFactorSnapshot(BaseModel):
    symbol: str
    name: str | None = None
    as_of_date: str
    window_size: int
    recent_return_1d_pct: float | None = None
    recent_return_3d_pct: float | None = None
    recent_return_5d_pct: float | None = None
    volatility_5d_pct: float | None = None
    volume_zscore: float | None = None
    volume_trend_ratio: float | None = None
    price_volume_divergence: bool = False
    candle_body_ratio: float | None = None
    upper_shadow_ratio: float | None = None
    lower_shadow_ratio: float | None = None
    market_trend_5: float | None = None
    industry_trend_5: float | None = None
    industry_relative_strength_5: float | None = None
    amount_zscore: float | None = None
    amount_trend_ratio: float | None = None
    turnover_zscore: float | None = None
    turnover_trend_ratio: float | None = None
    range_pct: float | None = None
    volatility_10d_pct: float | None = None
    atr_14_pct: float | None = None
    obv_trend_5: float | None = None
    mfi_14: float | None = None
    large_order_fire_score: float | None = None
    short_hot_score: float | None = None
    limit_threshold_pct: float | None = None
    limit_up_like: bool = False
    limit_down_like: bool = False
    big_up: bool = False
    big_down: bool = False
    consecutive_up_days: int = 0
    consecutive_limit_up_days: int = 0
    board_chain_stage: str = "none"
    short_candidate: bool = False
    features: dict[str, float | int | bool | str | None] = Field(default_factory=dict)


class PredictionAnalogueSample(BaseModel):
    symbol: str
    name: str | None = None
    window_size: int
    start_date: str
    end_date: str
    similarity: float
    forward_returns_pct: dict[str, float | None] = Field(default_factory=dict)
    scenarios: dict[str, str | None] = Field(default_factory=dict)


class PredictionHorizonResult(BaseModel):
    horizon: int
    up_probability: float | None = None
    expected_return_pct: float | None = None
    return_quantiles_pct: dict[str, float | None] = Field(default_factory=dict)
    max_drawdown_risk_pct: float | None = None
    kline_scenarios: dict[str, float] = Field(default_factory=dict)
    confidence: str
    confidence_reasons: list[str] = Field(default_factory=list)
    sample_count: int = 0
    selected_model: str = "analogue"
    model_weights: dict[str, float] = Field(default_factory=dict)
    analogue_up_probability: float | None = None
    ml_up_probability: float | None = None


class PredictionModelDiagnostics(BaseModel):
    selected_model: str
    analogue_status: str
    ml_status: str
    passed_validation: bool = False
    warnings: list[str] = Field(default_factory=list)
    ml_training_samples: int = 0
    validation_metrics: dict[str, float | None] = Field(default_factory=dict)
    acceleration: dict[str, Any] = Field(default_factory=dict)


class PredictionBacktestSummary(BaseModel):
    status: str
    sample_size: int = 0
    metrics: dict[str, float | None] = Field(default_factory=dict)
    baseline_metrics: dict[str, float | None] = Field(default_factory=dict)
    acceleration: dict[str, Any] = Field(default_factory=dict)
    acceptance: str = "not_evaluated"
    notes: list[str] = Field(default_factory=list)


class PredictionQueryMeta(BaseModel):
    symbol: str
    name: str | None = None
    as_of_date: str
    frequency: Frequency
    horizons: list[int]
    window_sizes: list[int]
    top_k: int
    search_scope: SearchScope = "historical"


class PredictionResponse(BaseModel):
    query_meta: PredictionQueryMeta
    factor_snapshot: PredictionFactorSnapshot
    analogue_evidence: list[PredictionAnalogueSample]
    predictions: list[PredictionHorizonResult]
    model_diagnostics: PredictionModelDiagnostics
    backtest_summary: PredictionBacktestSummary
    data_freshness: DataFreshness
    warnings: list[str] = Field(default_factory=list)


class BuildRequest(BaseModel):
    frequency: Frequency
    window_size: int = Field(..., ge=3, le=240)
    start_date: date | None = None
    end_date: date | None = None
    symbols: list[str] | None = None
    skip_refresh: bool = False


class BuildSummary(BaseModel):
    frequency: Frequency
    window_size: int
    symbols_processed: int
    windows_created: int
    index_backend: str
    output_paths: dict[str, str]


class AppState(BaseModel):
    config: dict[str, Any]
    bootstrap_completed: bool
    index_status: dict[str, dict[str, Any]]


class SearchFormPayload(BaseModel):
    symbol: str
    end_date: str
    frequency: Frequency = "daily"
    window_size: int = 10
    top_k: int = 10

    @model_validator(mode="after")
    def normalize_symbol(self) -> "SearchFormPayload":
        self.symbol = self.symbol.strip()
        return self

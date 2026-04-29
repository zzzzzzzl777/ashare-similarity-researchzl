from __future__ import annotations

import importlib
import inspect
import shutil
import tempfile
import time
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import numpy as np
import pandas as pd
import pytest

from ashare_similarity.config import (
    AppConfig,
    DataSourceConfig,
    QualityConfig,
    RankingConfig,
    SearchWeights,
    StorageConfig,
)
from ashare_similarity.schemas import (
    AggregateForwardStat,
    DataFreshness,
    ForwardStats,
    MatchResult,
    MatchSeries,
    QueryMeta,
    ScoreBreakdown,
    SearchRequest,
    SearchResponse,
)


class DispatchingStub:
    def __init__(
        self,
        *,
        default: Callable[..., Any] | None = None,
        handlers: Mapping[str, Callable[..., Any]] | None = None,
    ) -> None:
        self._default = default
        self._handlers = dict(handlers or {})
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Callable[..., Any]:
        handler = self._handlers.get(name, self._default)
        if handler is None:
            raise AssertionError(
                f"Missing synthetic stub handler for dependency method `{name}`. "
                "If the implementation now relies on a new collaborator method, "
                "please add a fixture adapter in tests/conftest.py."
            )

        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, args, kwargs))
            return handler(*args, **kwargs)

        return _wrapped


def _build_app_config(tmp_path: Path) -> AppConfig:
    storage_root = tmp_path / "synthetic-data"
    config = AppConfig(
        storage=StorageConfig(
            root_dir=storage_root,
            raw_dir=storage_root / "raw",
            cache_dir=storage_root / "cache",
            index_dir=storage_root / "index",
            report_dir=storage_root / "reports",
            db_path=storage_root / "workspace.duckdb",
        ),
        search_weights=SearchWeights(
            price_path=0.45,
            candle_geometry=0.20,
            volume_liquidity=0.20,
            environment=0.15,
        ),
        ranking=RankingConfig(
            top_k=10,
            recall_k=20,
            max_matches_per_symbol=2,
            overlap_days_limit=2,
            forward_windows=(1, 3, 5, 10),
        ),
        quality=QualityConfig(
            min_listing_days=1,
            min_non_null_ratio=0.95,
            max_zero_volume_ratio=0.20,
            exclude_st=True,
        ),
        data_source=DataSourceConfig(
            provider="synthetic",
            default_adjust="qfq",
            minute_history_notice="Minute data from the free source is only guaranteed for recent history.",
        ),
    )
    config.ensure_directories()
    return config


def _remove_tree_with_retry(path: Path, attempts: int = 5, delay_seconds: float = 0.1) -> None:
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay_seconds)


def _pattern_vector(pattern: str, periods: int) -> np.ndarray:
    patterns = {
        "query": np.array([0.42, 0.68, -0.10, 0.72, -0.15, 0.54, 0.28, -0.08, 0.41, 0.16]),
        "similar": np.array([0.40, 0.70, -0.12, 0.70, -0.12, 0.52, 0.26, -0.05, 0.38, 0.18]),
        "flat": np.array([0.04, -0.02, 0.03, -0.01, 0.04, -0.03, 0.01, -0.02, 0.02, -0.01]),
        "divergent": np.array([-0.55, 0.14, -0.66, 0.09, -0.48, 0.06, -0.37, 0.05, -0.32, 0.04]),
    }
    vector = patterns.get(pattern)
    if vector is None:
        raise AssertionError(f"Unknown synthetic pattern `{pattern}`.")
    repeats = int(np.ceil(periods / len(vector)))
    return np.tile(vector, repeats)[:periods]


def _make_ohlcv_frame(
    *,
    symbol: str = "600519",
    name: str | None = None,
    industry: str = "liquor",
    start: str = "2024-01-02",
    periods: int = 10,
    frequency: str = "daily",
    pattern: str = "query",
    base_price: float = 10.0,
    volume_base: float = 1_000_000.0,
    listing_days: int = 365,
    st_flag: bool = False,
) -> pd.DataFrame:
    if frequency == "daily":
        dates = pd.bdate_range(start=start, periods=periods)
    else:
        dates = pd.date_range(start=start, periods=periods, freq=f"{frequency}min")

    drift = _pattern_vector(pattern, periods)
    close = base_price + np.cumsum(drift)
    open_ = close - drift * 0.35
    high = np.maximum(open_, close) + 0.25
    low = np.minimum(open_, close) - 0.25
    volume = volume_base + np.linspace(0, periods - 1, periods) * 10_000

    frame = pd.DataFrame(
        {
            "symbol": symbol,
            "name": name or f"Synthetic-{symbol}",
            "industry": industry,
            "date": dates,
            "open": np.round(open_, 4),
            "high": np.round(high, 4),
            "low": np.round(low, 4),
            "close": np.round(close, 4),
            "volume": np.round(volume, 2),
            "turnover": np.round(volume * close, 2),
            "listing_days": listing_days,
            "is_st": st_flag,
        }
    )
    return frame


def _make_context_frame(frame: pd.DataFrame) -> pd.DataFrame:
    rows = len(frame)
    return pd.DataFrame(
        {
            "date": pd.to_datetime(frame["date"]),
            "market_return": np.round(np.linspace(0.002, 0.012, rows), 6),
            "industry_return": np.round(np.linspace(0.001, 0.008, rows), 6),
            "turnover_ratio": np.round(np.linspace(0.8, 1.15, rows), 6),
        }
    )


def _to_iso_date(value: Any) -> str:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value[:10]
    raise AssertionError(f"Unsupported date-like value: {value!r}")


def _make_match_series(frame: pd.DataFrame) -> MatchSeries:
    return MatchSeries(
        dates=[_to_iso_date(value) for value in frame["date"].tolist()],
        open=frame["open"].astype(float).tolist(),
        high=frame["high"].astype(float).tolist(),
        low=frame["low"].astype(float).tolist(),
        close=frame["close"].astype(float).tolist(),
        volume=frame["volume"].astype(float).tolist(),
    )


def _make_match_result(
    frame: pd.DataFrame,
    *,
    start: int = 0,
    window_size: int | None = None,
    frequency: str = "daily",
    balanced: float = 0.95,
    shape: float = 0.93,
    price_path_distance: float = 0.05,
    candle_geometry_distance: float = 0.07,
    volume_liquidity_distance: float = 0.10,
    environment_distance: float = 0.12,
    explanation: list[str] | None = None,
) -> MatchResult:
    size = window_size or len(frame)
    window = frame.iloc[start : start + size].reset_index(drop=True)
    if len(window) != size:
        raise AssertionError("Synthetic match window exceeds the provided frame length.")

    return MatchResult(
        symbol=str(window.loc[0, "symbol"]),
        name=str(window.loc[0, "name"]),
        frequency=frequency,
        start_date=_to_iso_date(window.loc[0, "date"]),
        end_date=_to_iso_date(window.loc[len(window) - 1, "date"]),
        listing_days=int(window.loc[len(window) - 1, "listing_days"]),
        industry=str(window.loc[0, "industry"]),
        scores=ScoreBreakdown(
            balanced=balanced,
            shape=shape,
            price_path_distance=price_path_distance,
            candle_geometry_distance=candle_geometry_distance,
            volume_liquidity_distance=volume_liquidity_distance,
            environment_distance=environment_distance,
        ),
        forward_stats=[
            ForwardStats(horizon=1, return_pct=1.2, max_favorable_excursion_pct=1.8, max_drawdown_pct=-0.4),
            ForwardStats(horizon=3, return_pct=2.5, max_favorable_excursion_pct=3.1, max_drawdown_pct=-1.0),
            ForwardStats(horizon=5, return_pct=3.4, max_favorable_excursion_pct=4.2, max_drawdown_pct=-1.5),
            ForwardStats(horizon=10, return_pct=5.1, max_favorable_excursion_pct=6.6, max_drawdown_pct=-2.1),
        ],
        series=_make_match_series(window),
        explanation=explanation or ["synthetic baseline fixture"],
    )


def _load_module_or_fail(module_name: str) -> Any:
    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - failure path is the point of the baseline
        pytest.fail(
            f"Expected module `{module_name}` to be importable for this test baseline. "
            f"Current import error: {exc}"
        )


def _load_public_attr(module_name: str, attr_name: str) -> Any:
    module = _load_module_or_fail(module_name)
    if not hasattr(module, attr_name):
        pytest.fail(
            f"Module `{module_name}` must expose `{attr_name}` to satisfy the test contract."
        )
    return getattr(module, attr_name)


def _invoke_with_supported_kwargs(callable_obj: Callable[..., Any], **kwargs: Any) -> Any:
    signature = inspect.signature(callable_obj)
    parameters = signature.parameters

    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
        return callable_obj(**kwargs)

    supported = {name: value for name, value in kwargs.items() if name in parameters}
    missing_required = [
        name
        for name, parameter in parameters.items()
        if parameter.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        and parameter.default is inspect.Signature.empty
        and name not in supported
    ]
    if missing_required:
        raise AssertionError(
            f"Cannot call `{callable_obj}` with the synthetic test harness. "
            f"Missing required keyword parameters: {missing_required}"
        )
    return callable_obj(**supported)


def _as_records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []

    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")

    if hasattr(value, "metadata_frame") and isinstance(getattr(value, "metadata_frame"), pd.DataFrame):
        return getattr(value, "metadata_frame").to_dict(orient="records")

    if hasattr(value, "metadata") and isinstance(getattr(value, "metadata"), list):
        metadata = getattr(value, "metadata")
        if not metadata or isinstance(metadata[0], Mapping):
            return [dict(item) for item in metadata]

    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")

    if hasattr(value, "to_dicts"):
        return value.to_dicts()  # type: ignore[no-any-return]

    if isinstance(value, list):
        rows: list[dict[str, Any]] = []
        for item in value:
            if hasattr(item, "model_dump"):
                rows.append(item.model_dump(mode="python"))
            elif isinstance(item, Mapping):
                rows.append(dict(item))
            else:
                rows.append(vars(item))
        return rows

    if isinstance(value, Mapping):
        return [dict(value)]

    raise AssertionError(f"Unsupported tabular value for record conversion: {type(value)!r}")


def _extract_match_rows(result: Any, field_name: str = "balanced_matches") -> list[dict[str, Any]]:
    if hasattr(result, field_name):
        return _as_records(getattr(result, field_name))
    if isinstance(result, Mapping) and field_name in result:
        return _as_records(result[field_name])
    if field_name == "balanced_matches":
        return _as_records(result)
    raise AssertionError(
        f"Search result does not expose `{field_name}`. "
        "Please return a SearchResponse-like payload or a flat balanced match list."
    )


def _maybe_patch_attr(monkeypatch: pytest.MonkeyPatch, dotted_path: str, value: Any) -> bool:
    module_name, attr_name = dotted_path.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return False
    if not hasattr(module, attr_name):
        return False
    monkeypatch.setattr(module, attr_name, value)
    return True


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return _build_app_config(tmp_path)


@pytest.fixture
def tmp_path() -> Path:
    path = Path(tempfile.mkdtemp(prefix="ashare_similarity_case_"))
    try:
        yield path
    finally:
        _remove_tree_with_retry(path)


@pytest.fixture
def load_module_or_fail() -> Callable[[str], Any]:
    return _load_module_or_fail


@pytest.fixture
def load_public_attr() -> Callable[[str, str], Any]:
    return _load_public_attr


@pytest.fixture
def invoke_with_supported_kwargs() -> Callable[..., Any]:
    return _invoke_with_supported_kwargs


@pytest.fixture
def as_records() -> Callable[[Any], list[dict[str, Any]]]:
    return _as_records


@pytest.fixture
def extract_match_rows() -> Callable[[Any, str], list[dict[str, Any]]]:
    return _extract_match_rows


@pytest.fixture
def maybe_patch_attr() -> Callable[[pytest.MonkeyPatch, str, Any], bool]:
    return _maybe_patch_attr


@pytest.fixture
def to_iso_date() -> Callable[[Any], str]:
    return _to_iso_date


@pytest.fixture
def stub_factory() -> Callable[..., DispatchingStub]:
    def _factory(
        *,
        default: Callable[..., Any] | None = None,
        handlers: Mapping[str, Callable[..., Any]] | None = None,
    ) -> DispatchingStub:
        return DispatchingStub(default=default, handlers=handlers)

    return _factory


@pytest.fixture
def make_ohlcv_frame() -> Callable[..., pd.DataFrame]:
    return _make_ohlcv_frame


@pytest.fixture
def make_context_frame() -> Callable[[pd.DataFrame], pd.DataFrame]:
    return _make_context_frame


@pytest.fixture
def make_match_result() -> Callable[..., MatchResult]:
    return _make_match_result


@pytest.fixture
def minute_notice_text(app_config: AppConfig) -> str:
    return app_config.data_source.minute_history_notice


@pytest.fixture
def sample_search_request() -> SearchRequest:
    return SearchRequest(
        symbol="600519",
        end_date=date(2024, 1, 15),
        frequency="daily",
        window_size=5,
        top_k=10,
    )


@pytest.fixture
def sample_search_response(
    make_ohlcv_frame: Callable[..., pd.DataFrame],
    make_match_result: Callable[..., MatchResult],
) -> SearchResponse:
    query_frame = make_ohlcv_frame(symbol="600519", start="2024-01-02", periods=5, pattern="query", base_price=1600.0)
    balanced_one = make_match_result(
        make_ohlcv_frame(symbol="000001", start="2022-01-03", periods=5, pattern="similar", base_price=12.0),
        balanced=0.96,
        shape=0.92,
    )
    balanced_two = make_match_result(
        make_ohlcv_frame(symbol="000002", start="2021-06-01", periods=5, pattern="query", base_price=28.0),
        balanced=0.94,
        shape=0.95,
    )

    return SearchResponse(
        query_meta=QueryMeta(
            symbol="600519",
            frequency="daily",
            window_size=5,
            start_date="2024-01-09",
            end_date="2024-01-15",
            query_series=_make_match_series(query_frame),
            universe_size=5000,
            candidate_pool_size=200,
            filters=["exclude_st", "min_listing_days>=120"],
        ),
        balanced_matches=[balanced_one, balanced_two],
        shape_matches=[balanced_two, balanced_one],
        aggregate_forward_stats=[
            AggregateForwardStat(
                horizon=1,
                avg_return_pct=0.8,
                win_rate=0.5,
                avg_max_favorable_excursion_pct=1.2,
                avg_max_drawdown_pct=-0.4,
            ),
            AggregateForwardStat(
                horizon=5,
                avg_return_pct=2.1,
                win_rate=1.0,
                avg_max_favorable_excursion_pct=2.8,
                avg_max_drawdown_pct=-1.1,
            ),
        ],
        data_freshness=DataFreshness(
            last_refresh_at=datetime(2026, 4, 23, 9, 30, 0),
            data_source="synthetic-fixture",
            notice=None,
        ),
        warnings=[],
    )


class FakeSearchService:
    def __init__(self, response: SearchResponse, minute_notice_text: str) -> None:
        self._response = response
        self._minute_notice_text = minute_notice_text
        self.calls: list[Any] = []

    def search(self, request: Any) -> SearchResponse:
        self.calls.append(request)
        response = self._response.model_copy(deep=True)

        if hasattr(request, "symbol"):
            response.query_meta.symbol = request.symbol
        if hasattr(request, "frequency"):
            response.query_meta.frequency = request.frequency
            for match in response.balanced_matches:
                match.frequency = request.frequency
            for match in response.shape_matches:
                match.frequency = request.frequency
            if request.frequency != "daily":
                response.data_freshness.notice = self._minute_notice_text
                if self._minute_notice_text not in response.warnings:
                    response.warnings.append(self._minute_notice_text)
        if hasattr(request, "window_size"):
            response.query_meta.window_size = request.window_size
        if hasattr(request, "top_k"):
            response.balanced_matches = response.balanced_matches[: request.top_k]
            response.shape_matches = response.shape_matches[: request.top_k]
        return response


@pytest.fixture
def mock_search_service(sample_search_response: SearchResponse, minute_notice_text: str) -> FakeSearchService:
    return FakeSearchService(sample_search_response, minute_notice_text)


@pytest.fixture
def mock_runtime(app_config: AppConfig, mock_search_service: FakeSearchService) -> SimpleNamespace:
    return SimpleNamespace(
        config=app_config,
        search_service=mock_search_service,
        data_service=DispatchingStub(default=lambda *args, **kwargs: None),
        feature_service=DispatchingStub(default=lambda *args, **kwargs: None),
        index_service=DispatchingStub(default=lambda *args, **kwargs: None),
        context_service=DispatchingStub(default=lambda *args, **kwargs: None),
    )

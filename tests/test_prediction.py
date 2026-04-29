from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
import numpy as np
import pytest

from ashare_similarity.prediction.analogue_model import AnalogueSample, predict_from_analogues
from ashare_similarity.prediction.factor_builder import build_factor_snapshot
from ashare_similarity.prediction.label_builder import ForwardLabel, build_forward_labels
from ashare_similarity.prediction.service import PredictionService
from ashare_similarity.schemas import DataFreshness, PredictionRequest, PredictionResponse


@pytest.fixture
def prediction_api_client(monkeypatch, load_public_attr, maybe_patch_attr, app_config, mock_runtime):
    create_app = load_public_attr("ashare_similarity.app", "create_app")

    maybe_patch_attr(monkeypatch, "ashare_similarity.runtime.get_runtime", lambda: mock_runtime)
    maybe_patch_attr(monkeypatch, "ashare_similarity.web.routes.get_runtime", lambda: mock_runtime)

    app = create_app()
    app.state.runtime = mock_runtime
    app.state.app_config = app_config

    with TestClient(app) as client:
        yield client


def test_prediction_request_validates_supported_scope():
    request = PredictionRequest(
        symbol=" 600519 ",
        as_of_date=date(2024, 1, 15),
        frequency="daily",
        horizons=[2, 1, 1],
        window_sizes=[20, 5, 5, 10],
        top_k=50,
    )

    assert request.symbol == "600519"
    assert request.horizons == [1, 2]
    assert request.window_sizes == [5, 10, 20]

    with pytest.raises(ValueError, match="1/2"):
        PredictionRequest(symbol="600519", as_of_date=date(2024, 1, 15), horizons=[3])

    with pytest.raises(ValueError):
        PredictionRequest(symbol="600519", as_of_date=date(2024, 1, 15), frequency="5")

    with pytest.raises(ValueError, match="3.*240"):
        PredictionRequest(symbol="600519", as_of_date=date(2024, 1, 15), window_sizes=[2])


def test_api_predict_accepts_stock_name_and_returns_prediction_contract(prediction_api_client, mock_runtime):
    calls: list[PredictionRequest] = []
    mock_runtime.data_service = SimpleNamespace(
        resolve_symbol_query=lambda query, frequency=None, prefer_cached=True: (
            {"symbol": "601778", "name": "Synthetic Tech", "match_type": "name"}
            if query == "Synthetic Tech"
            else None
        )
    )

    def _predict(request: PredictionRequest) -> PredictionResponse:
        calls.append(request)
        return _prediction_response(request)

    mock_runtime.prediction_service = SimpleNamespace(predict=_predict)

    response = prediction_api_client.post(
        "/api/predict",
        json={
            "symbol": "Synthetic Tech",
            "as_of_date": "2024-01-15",
            "frequency": "daily",
            "horizons": [1, 2],
            "window_sizes": [5, 10],
            "top_k": 20,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    model = PredictionResponse.model_validate(payload)
    assert calls and calls[-1].symbol == "601778"
    assert model.query_meta.symbol == "601778"
    assert model.query_meta.as_of_date == "2024-01-15"
    assert model.factor_snapshot.symbol == "601778"
    assert {prediction.horizon for prediction in model.predictions} == {1, 2}
    assert model.model_diagnostics.selected_model
    assert model.backtest_summary.status
    assert model.data_freshness.data_source == "synthetic-fixture"


def test_api_predict_reuses_prediction_cache(prediction_api_client, mock_runtime):
    calls: list[PredictionRequest] = []
    mock_runtime.data_service = SimpleNamespace(resolve_symbol_query=lambda *args, **kwargs: None)

    def _predict(request: PredictionRequest) -> PredictionResponse:
        calls.append(request)
        return _prediction_response(request)

    mock_runtime.prediction_service = SimpleNamespace(predict=_predict)
    payload = {
        "symbol": "600519",
        "as_of_date": "2024-01-15",
        "frequency": "daily",
        "horizons": [1, 2],
        "window_sizes": [5, 10],
        "top_k": 20,
    }

    first = prediction_api_client.post("/api/predict", json=payload)
    assert first.status_code == 200, first.text
    second = prediction_api_client.post("/api/predict", json=payload)
    assert second.status_code == 200, second.text

    assert len(calls) == 1, "Repeated prediction requests should reuse the in-memory prediction cache."
    assert first.json() == second.json()


def test_prediction_query_window_cache_reuses_factor_window(app_config, make_ohlcv_frame):
    build_calls: list[int] = []

    def _build_query_frame(**kwargs):
        window_size = int(kwargs["window_size"])
        build_calls.append(window_size)
        query_series = make_ohlcv_frame(
            symbol=kwargs["symbol"],
            start="2024-01-02",
            periods=max(window_size, 6),
            base_price=100.0,
        )
        return SimpleNamespace(
            symbol=kwargs["symbol"],
            metadata={
                "name": "Synthetic Kweichow",
                "start_date": "2024-01-02",
                "end_date": "2024-01-15",
            },
            series=query_series,
            matrix=np.zeros((1, 4), dtype=np.float32),
            component_slices={},
        )

    class _EmptySearchable:
        row_count = 1

        def search(self, query, top_k):
            del query, top_k
            return np.asarray([], dtype=float), np.asarray([], dtype=int)

    service = PredictionService(
        config=app_config,
        store=SimpleNamespace(load_bars=lambda *args, **kwargs: pytest.fail("No samples should load history.")),
        data_service=SimpleNamespace(get_data_freshness=lambda frequency: DataFreshness(data_source="synthetic-fixture")),
        feature_service=SimpleNamespace(build_query_frame=_build_query_frame),
        search_service=SimpleNamespace(index_service=SimpleNamespace(load=lambda frequency, window_size: _EmptySearchable())),
    )
    request = PredictionRequest(
        symbol="600519",
        as_of_date=date(2024, 1, 15),
        horizons=[1, 2],
        window_sizes=[3, 5],
        top_k=10,
    )
    query_window_cache = {}

    service._build_query_factors(request, query_window_cache=query_window_cache)
    samples, warnings = service._collect_analogue_samples(request, query_window_cache=query_window_cache)

    assert samples == []
    assert warnings == []
    assert build_calls == [5, 3]


def test_prediction_reuses_forward_labels_across_windows(monkeypatch, app_config, make_ohlcv_frame):
    label_calls: list[str] = []
    candidate_history = make_ohlcv_frame(symbol="000001", start="2024-01-02", periods=8, base_price=10.0)

    def _build_query_frame(**kwargs):
        window_size = int(kwargs["window_size"])
        return SimpleNamespace(
            symbol=kwargs["symbol"],
            metadata={
                "name": "Synthetic Kweichow",
                "start_date": "2024-01-15",
                "end_date": "2024-01-15",
            },
            series=make_ohlcv_frame(
                symbol=kwargs["symbol"],
                start="2024-01-09",
                periods=max(window_size, 5),
                base_price=100.0,
            ),
            matrix=np.zeros((1, 4), dtype=np.float32),
            component_slices={},
        )

    class _Searchable:
        row_count = 1

        def __init__(self, window_size: int) -> None:
            self.window_size = window_size

        def search(self, query, top_k):
            del query, top_k
            return np.asarray([0.1], dtype=float), np.asarray([0], dtype=int)

        def metadata_row(self, row_index: int):
            assert row_index == 0
            return {
                "symbol": "000001",
                "name": "Accepted",
                "start_date": "2024-01-04" if self.window_size == 3 else "2024-01-02",
                "end_date": "2024-01-08",
            }

    def _build_forward_labels_once(*args, **kwargs):
        label_calls.append(str(kwargs["end_date"]))
        return build_forward_labels(*args, **kwargs)

    monkeypatch.setattr("ashare_similarity.prediction.service.build_forward_labels", _build_forward_labels_once)

    service = PredictionService(
        config=app_config,
        store=SimpleNamespace(load_bars=lambda symbol, frequency: candidate_history),
        data_service=SimpleNamespace(get_data_freshness=lambda frequency: DataFreshness(data_source="synthetic-fixture")),
        feature_service=SimpleNamespace(build_query_frame=_build_query_frame),
        search_service=SimpleNamespace(index_service=SimpleNamespace(load=lambda frequency, window_size: _Searchable(window_size))),
    )

    samples, warnings = service._collect_analogue_samples(
        PredictionRequest(
            symbol="600519",
            as_of_date=date(2024, 1, 15),
            horizons=[1, 2],
            window_sizes=[3, 5],
            top_k=10,
        )
    )

    assert warnings == []
    assert len(samples) == 2
    assert label_calls == ["2024-01-08"]


def test_analogue_prediction_weights_factor_similarity():
    negative_label = ForwardLabel(1, -1.0, 0.0, -1.0, "mild_down")
    positive_label = ForwardLabel(1, 1.0, 1.0, 0.0, "mild_up")
    samples = [
        AnalogueSample(
            symbol="000001",
            name=None,
            window_size=5,
            start_date="2024-01-01",
            end_date="2024-01-05",
            similarity=0.9,
            factors={"recent_return_1d_pct": -1.0, "recent_return_3d_pct": -2.0, "recent_return_5d_pct": -3.0},
            labels={1: negative_label},
        ),
        AnalogueSample(
            symbol="000002",
            name=None,
            window_size=5,
            start_date="2024-01-01",
            end_date="2024-01-05",
            similarity=0.9,
            factors={"recent_return_1d_pct": 8.0, "recent_return_3d_pct": 9.0, "recent_return_5d_pct": 10.0},
            labels={1: positive_label},
        ),
    ]

    unweighted = predict_from_analogues(samples, [1])[1]
    weighted = predict_from_analogues(
        samples,
        [1],
        query_vector={"recent_return_1d_pct": -1.0, "recent_return_3d_pct": -2.0, "recent_return_5d_pct": -3.0},
    )[1]

    assert unweighted.up_probability == 0.5
    assert weighted.up_probability is not None
    assert weighted.up_probability < 0.5


def test_prediction_backtest_reports_target_accuracy_without_false_pass(
    monkeypatch,
    app_config,
    make_ohlcv_frame,
):
    histories = {
        "000001": make_ohlcv_frame(symbol="000001", start="2024-01-02", periods=40, base_price=10.0),
        "000002": make_ohlcv_frame(symbol="000002", start="2024-01-02", periods=40, base_price=20.0),
    }

    class _StoreStub:
        def list_cached_symbols(self, frequency: str):
            assert frequency == "daily"
            return list(histories)

        def load_bars(self, symbol: str, frequency: str):
            assert frequency == "daily"
            return histories[symbol].copy()

    def _labels(history, *, end_date, horizons, max_label_date=None):
        del end_date, max_label_date
        symbol = str(history.iloc[0]["symbol"])
        return_pct = 1.0 if symbol == "000001" else -1.0
        scenario = "mild_up" if return_pct > 0 else "mild_down"
        return {
            horizon: ForwardLabel(
                horizon=horizon,
                return_pct=return_pct,
                max_favorable_excursion_pct=max(return_pct, 0.0),
                max_drawdown_pct=min(return_pct, 0.0),
                scenario=scenario,
            )
            for horizon in horizons
        }

    def _predict(request: PredictionRequest) -> PredictionResponse:
        response = _prediction_response(request)
        for prediction in response.predictions:
            prediction.up_probability = 0.70
            prediction.analogue_up_probability = 0.70
        return response

    monkeypatch.setattr("ashare_similarity.prediction.service.build_forward_labels", _labels)
    service = PredictionService(
        config=app_config,
        store=_StoreStub(),
        data_service=SimpleNamespace(get_data_freshness=lambda frequency: DataFreshness(data_source="synthetic-fixture")),
        feature_service=SimpleNamespace(),
        search_service=SimpleNamespace(),
    )
    service.predict = _predict

    summary = service.backtest(
        start=date(2024, 1, 1),
        end=date(2024, 3, 1),
        sample_size=2,
        seed=1,
        horizons=[1, 2],
        window_sizes=[5],
        top_k=10,
        target_accuracy=0.75,
        confidence_threshold=0.65,
    )

    assert summary.acceptance == "failed"
    assert summary.sample_size == 4
    assert summary.metrics["direction_accuracy"] == 0.5
    assert summary.metrics["target_accuracy"] == 0.75
    assert summary.metrics["target_met"] == 0.0
    assert summary.metrics["confident_direction_accuracy"] == 0.5
    assert summary.metrics["confident_prediction_count"] == 4.0
    assert summary.metrics["confident_target_met"] == 0.0
    assert summary.metrics["h1_direction_accuracy"] == 0.5
    assert summary.metrics["h2_direction_accuracy"] == 0.5
    assert summary.metrics["all_horizons_evaluable"] == 1.0
    assert summary.metrics["recall_gpu_enabled"] in {0.0, 1.0}
    assert summary.acceleration["full_gpu_pipeline"] is False
    assert "label_build" in summary.acceleration["cpu_stages"]


def test_prediction_backtest_keeps_75_percent_floor_when_target_is_lower(
    monkeypatch,
    app_config,
    make_ohlcv_frame,
):
    history = make_ohlcv_frame(symbol="000001", start="2024-01-02", periods=40, base_price=10.0)

    class _StoreStub:
        def list_cached_symbols(self, frequency: str):
            assert frequency == "daily"
            return ["000001"]

        def load_bars(self, symbol: str, frequency: str):
            assert symbol == "000001"
            assert frequency == "daily"
            return history.copy()

    def _labels(history, *, end_date, horizons, max_label_date=None):
        del history, end_date, max_label_date
        return {
            horizon: ForwardLabel(
                horizon=horizon,
                return_pct=1.0,
                max_favorable_excursion_pct=1.0,
                max_drawdown_pct=0.0,
                scenario="mild_up",
            )
            for horizon in horizons
        }

    def _predict(request: PredictionRequest) -> PredictionResponse:
        response = _prediction_response(request)
        for prediction in response.predictions:
            prediction.up_probability = 0.70
            prediction.analogue_up_probability = 0.70
        return response

    monkeypatch.setattr("ashare_similarity.prediction.service.build_forward_labels", _labels)
    service = PredictionService(
        config=app_config,
        store=_StoreStub(),
        data_service=SimpleNamespace(get_data_freshness=lambda frequency: DataFreshness(data_source="synthetic-fixture")),
        feature_service=SimpleNamespace(),
        search_service=SimpleNamespace(),
    )
    service.predict = _predict

    summary = service.backtest(
        start=date(2024, 1, 1),
        end=date(2024, 3, 1),
        sample_size=1,
        seed=1,
        horizons=[1, 2],
        window_sizes=[5],
        top_k=10,
        target_accuracy=0.5,
        confidence_threshold=0.65,
    )

    assert summary.metrics["target_accuracy"] == 0.75
    assert summary.metrics["target_met"] == 1.0


def test_prediction_backtest_fails_when_requested_horizon_has_no_evaluable_rows(
    monkeypatch,
    app_config,
    make_ohlcv_frame,
):
    history = make_ohlcv_frame(symbol="000001", start="2024-01-02", periods=40, base_price=10.0)

    class _StoreStub:
        def list_cached_symbols(self, frequency: str):
            assert frequency == "daily"
            return ["000001"]

        def load_bars(self, symbol: str, frequency: str):
            assert symbol == "000001"
            assert frequency == "daily"
            return history.copy()

    def _labels(history, *, end_date, horizons, max_label_date=None):
        del history, end_date, max_label_date
        return {
            horizon: ForwardLabel(
                horizon=horizon,
                return_pct=1.0,
                max_favorable_excursion_pct=1.0,
                max_drawdown_pct=0.0,
                scenario="mild_up",
            )
            for horizon in horizons
        }

    def _predict(request: PredictionRequest) -> PredictionResponse:
        response = _prediction_response(request)
        response.predictions = [prediction for prediction in response.predictions if prediction.horizon == 1]
        for prediction in response.predictions:
            prediction.up_probability = 0.90
            prediction.analogue_up_probability = 0.90
        return response

    monkeypatch.setattr("ashare_similarity.prediction.service.build_forward_labels", _labels)
    service = PredictionService(
        config=app_config,
        store=_StoreStub(),
        data_service=SimpleNamespace(get_data_freshness=lambda frequency: DataFreshness(data_source="synthetic-fixture")),
        feature_service=SimpleNamespace(),
        search_service=SimpleNamespace(),
    )
    service.predict = _predict

    summary = service.backtest(
        start=date(2024, 1, 1),
        end=date(2024, 3, 1),
        sample_size=1,
        seed=1,
        horizons=[1, 2],
        window_sizes=[5],
        top_k=10,
        target_accuracy=0.75,
        confidence_threshold=0.65,
    )

    assert summary.acceptance == "failed"
    assert summary.metrics["direction_accuracy"] == 1.0
    assert summary.metrics["target_met"] == 1.0
    assert summary.metrics["h1_prediction_count"] == 1.0
    assert summary.metrics["h2_prediction_count"] == 0.0
    assert summary.metrics["all_horizons_evaluable"] == 0.0


def test_prediction_service_research_signal_does_not_emit_trade_advice(app_config, make_ohlcv_frame):
    query_series = make_ohlcv_frame(symbol="600519", start="2024-01-02", periods=20, base_price=100.0)
    service = PredictionService(
        config=app_config,
        store=SimpleNamespace(),
        data_service=SimpleNamespace(
            resolve_symbol_query=lambda *args, **kwargs: None,
            get_data_freshness=lambda frequency: DataFreshness(data_source="synthetic-fixture"),
        ),
        feature_service=SimpleNamespace(
            build_query_frame=lambda **kwargs: SimpleNamespace(
                symbol=kwargs["symbol"],
                metadata={"name": "Synthetic Kweichow", "end_date": "2024-01-29"},
                series=query_series,
            )
        ),
        search_service=SimpleNamespace(
            search=lambda request: SimpleNamespace(balanced_matches=[])
        ),
    )

    response = service.predict(
        PredictionRequest(
            symbol="600519",
            as_of_date=date(2024, 1, 29),
            horizons=[1, 2],
            window_sizes=[5],
            top_k=10,
        )
    )
    text = response.model_dump_json().lower()

    assert "buy" not in text
    assert "sell" not in text
    assert "\u4e70\u5165" not in text
    assert "\u5356\u51fa" not in text
    assert response.model_diagnostics.warnings
    assert response.model_diagnostics.acceleration["market_scope"] == "main_board_only"


def test_prediction_service_rejects_non_main_board_symbol(app_config):
    service = PredictionService(
        config=app_config,
        store=SimpleNamespace(),
        data_service=SimpleNamespace(resolve_symbol_query=lambda *args, **kwargs: None),
        feature_service=SimpleNamespace(),
        search_service=SimpleNamespace(),
    )

    with pytest.raises(ValueError, match="只看主板"):
        service.predict(
            PredictionRequest(
                symbol="300001",
                as_of_date=date(2024, 1, 29),
                horizons=[1],
                window_sizes=[5],
                top_k=10,
            )
        )


def test_prediction_service_filters_current_or_future_windows_and_future_labels(app_config, make_ohlcv_frame):
    query_series = make_ohlcv_frame(symbol="600519", start="2024-01-08", periods=3, base_price=100.0)
    query_window = SimpleNamespace(
        symbol="600519",
        metadata={"name": "Synthetic Kweichow", "start_date": "2024-01-10", "end_date": "2024-01-10"},
        series=query_series,
        matrix=np.zeros((1, 4), dtype=np.float32),
        component_slices={},
    )
    candidate_history = make_ohlcv_frame(symbol="000001", start="2024-01-05", periods=5, base_price=10.0)
    loaded_symbols: list[str] = []

    class _StoreStub:
        def load_bars(self, symbol: str, frequency: str):
            assert frequency == "daily"
            loaded_symbols.append(symbol)
            if symbol != "000001":
                raise AssertionError(f"Current/future candidate should have been filtered before load: {symbol}")
            return candidate_history

    class _Searchable:
        row_count = 3

        def search(self, query, top_k):
            del query, top_k
            return np.asarray([0.05, 0.1, 0.2], dtype=float), np.asarray([0, 1, 2], dtype=int)

        def metadata_row(self, row_index: int):
            rows = [
                {
                    "symbol": "300001",
                    "name": "Filtered non-main board",
                    "start_date": "2024-01-05",
                    "end_date": "2024-01-09",
                },
                {
                    "symbol": "000001",
                    "name": "Accepted",
                    "start_date": "2024-01-05",
                    "end_date": "2024-01-09",
                },
                {
                    "symbol": "000002",
                    "name": "Overlaps current query",
                    "start_date": "2024-01-08",
                    "end_date": "2024-01-10",
                },
            ]
            return rows[row_index]

    service = PredictionService(
        config=app_config,
        store=_StoreStub(),
        data_service=SimpleNamespace(get_data_freshness=lambda frequency: DataFreshness(data_source="synthetic-fixture")),
        feature_service=SimpleNamespace(build_query_frame=lambda **kwargs: query_window),
        search_service=SimpleNamespace(index_service=SimpleNamespace(load=lambda frequency, window_size: _Searchable())),
    )

    samples, warnings = service._collect_analogue_samples(
        PredictionRequest(
            symbol="600519",
            as_of_date=date(2024, 1, 10),
            horizons=[1, 2],
            window_sizes=[3],
            top_k=10,
        )
    )

    assert warnings == []
    assert loaded_symbols == ["000001"]
    assert [sample.symbol for sample in samples] == ["000001"]
    assert samples[0].labels[1].return_pct is not None
    assert samples[0].labels[2].return_pct is None


def test_factor_snapshot_ignores_rows_after_as_of_date(make_ohlcv_frame):
    full_series = make_ohlcv_frame(symbol="600519", start="2024-01-02", periods=12, base_price=100.0)
    as_of_date = str(full_series.loc[7, "date"].date())
    truncated_series = full_series[full_series["date"] <= full_series.loc[7, "date"]]

    expected = build_factor_snapshot(
        truncated_series,
        symbol="600519",
        name="Synthetic Kweichow",
        as_of_date=as_of_date,
        window_size=8,
    )
    actual = build_factor_snapshot(
        full_series,
        symbol="600519",
        name="Synthetic Kweichow",
        as_of_date=as_of_date,
        window_size=8,
    )

    assert actual.snapshot.as_of_date == as_of_date
    assert actual.snapshot.features == expected.snapshot.features
    assert actual.vector == expected.vector


def test_factor_snapshot_exposes_main_board_short_term_factors(make_ohlcv_frame):
    frame = make_ohlcv_frame(symbol="600001", start="2024-01-02", periods=24, base_price=10.0)
    frame["amount"] = frame["volume"] * frame["close"] * 12.0
    last_index = frame.index[-1]
    previous_close = float(frame.loc[last_index - 1, "close"])
    frame.loc[last_index, "open"] = previous_close * 1.04
    frame.loc[last_index, "close"] = previous_close * 1.098
    frame.loc[last_index, "high"] = previous_close * 1.099
    frame.loc[last_index, "low"] = previous_close * 1.02
    frame.loc[last_index, "volume"] = float(frame["volume"].median()) * 8.0
    frame.loc[last_index, "amount"] = float(frame["amount"].median()) * 12.0
    frame.loc[last_index, "turnover"] = 8.0

    result = build_factor_snapshot(
        frame,
        symbol="600001",
        name="Synthetic Main Board",
        as_of_date=str(frame.loc[last_index, "date"].date()),
        window_size=10,
    )

    assert result.snapshot.limit_threshold_pct == 10.0
    assert result.snapshot.limit_up_like is True
    assert result.snapshot.board_chain_stage in {"first_board", "second_board", "multi_board"}
    assert result.snapshot.large_order_fire_score is not None
    assert result.snapshot.short_hot_score is not None
    assert result.snapshot.amount_zscore is not None
    assert result.snapshot.turnover_zscore is not None
    assert result.snapshot.atr_14_pct is not None
    assert result.snapshot.mfi_14 is not None
    assert result.snapshot.features["main_board_only"] is True


def test_forward_labels_respect_max_label_date(make_ohlcv_frame):
    history = make_ohlcv_frame(symbol="600519", start="2024-01-02", periods=8, base_price=100.0)
    end_date = str(history.loc[4, "date"].date())

    unrestricted = build_forward_labels(history, end_date=end_date, horizons=[1, 2])
    restricted = build_forward_labels(
        history,
        end_date=end_date,
        horizons=[1, 2],
        max_label_date=str(history.loc[5, "date"].date()),
    )

    assert unrestricted[1].return_pct is not None
    assert unrestricted[2].return_pct is not None
    assert restricted[1].return_pct is not None
    assert restricted[2].return_pct is None


def _prediction_response(request: PredictionRequest) -> PredictionResponse:
    return PredictionResponse.model_validate(
        {
            "query_meta": {
                "symbol": request.symbol,
                "name": "Synthetic Tech",
                "as_of_date": str(request.as_of_date),
                "frequency": request.frequency,
                "horizons": request.horizons,
                "window_sizes": request.window_sizes,
                "top_k": request.top_k,
                "search_scope": "historical",
            },
            "factor_snapshot": {
                "symbol": request.symbol,
                "name": "Synthetic Tech",
                "as_of_date": str(request.as_of_date),
                "window_size": request.window_sizes[0],
                "recent_return_1d_pct": 1.2,
                "features": {"recent_return_1d_pct": 1.2, "price_volume_divergence": False},
            },
            "analogue_evidence": [],
            "predictions": [
                {
                    "horizon": horizon,
                    "up_probability": 0.52,
                    "expected_return_pct": 0.8,
                    "return_quantiles_pct": {"p10": -1.0, "p50": 0.5, "p90": 2.0},
                    "max_drawdown_risk_pct": -1.5,
                    "kline_scenarios": {"flat": 1.0},
                    "confidence": "low",
                    "confidence_reasons": ["research signal only"],
                    "sample_count": 30,
                    "selected_model": "analogue",
                    "model_weights": {"analogue": 1.0, "ml": 0.0},
                    "analogue_up_probability": 0.52,
                    "ml_up_probability": None,
                }
                for horizon in request.horizons
            ],
            "model_diagnostics": {
                "selected_model": "analogue",
                "analogue_status": "ready",
                "ml_status": "insufficient_samples",
                "passed_validation": False,
                "warnings": ["research signal only; not investment advice"],
                "ml_training_samples": 0,
                "validation_metrics": {},
            },
            "backtest_summary": {
                "status": "not_available",
                "sample_size": 0,
                "metrics": {},
                "baseline_metrics": {},
                "acceptance": "not_evaluated",
                "notes": ["research validation pending"],
            },
            "data_freshness": {
                "last_refresh_at": datetime(2024, 1, 15, 15, 0, 0),
                "data_source": "synthetic-fixture",
            },
            "warnings": ["research signal only; not investment advice"],
        }
    )

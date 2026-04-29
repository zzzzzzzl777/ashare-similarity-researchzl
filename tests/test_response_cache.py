from __future__ import annotations

from datetime import date, datetime

from ashare_similarity.schemas import PredictionRequest, PredictionResponse
from ashare_similarity.search.response_cache import PredictionResponseCache, SearchResponseCache


def test_search_response_cache_returns_deep_copies(sample_search_request, sample_search_response):
    cache = SearchResponseCache(max_entries=4, ttl_seconds=30)
    cache.put(sample_search_request, sample_search_response)

    cached = cache.get(sample_search_request)
    assert cached is not None
    cached.warnings.append("mutated in test")

    second_read = cache.get(sample_search_request)
    assert second_read is not None
    assert "mutated in test" not in second_read.warnings


def test_search_response_cache_expires_entries(monkeypatch, sample_search_request, sample_search_response):
    timeline = iter([100.0, 100.0, 103.5])
    monkeypatch.setattr("ashare_similarity.search.response_cache.monotonic", lambda: next(timeline))

    cache = SearchResponseCache(max_entries=4, ttl_seconds=3.0)
    cache.put(sample_search_request, sample_search_response)

    assert cache.get(sample_search_request) is not None
    assert cache.get(sample_search_request) is None


def test_prediction_response_cache_returns_deep_copies():
    request = _prediction_request()
    response = _prediction_response(request)
    cache = PredictionResponseCache(max_entries=4, ttl_seconds=30)
    cache.put(request, response)

    cached = cache.get(request)
    assert cached is not None
    cached.warnings.append("mutated in test")
    cached.predictions[0].confidence_reasons.append("mutated confidence")

    second_read = cache.get(request)
    assert second_read is not None
    assert "mutated in test" not in second_read.warnings
    assert "mutated confidence" not in second_read.predictions[0].confidence_reasons


def test_prediction_response_cache_expires_entries(monkeypatch):
    timeline = iter([200.0, 200.0, 204.5])
    monkeypatch.setattr("ashare_similarity.search.response_cache.monotonic", lambda: next(timeline))

    request = _prediction_request()
    cache = PredictionResponseCache(max_entries=4, ttl_seconds=3.0)
    cache.put(request, _prediction_response(request))

    assert cache.get(request) is not None
    assert cache.get(request) is None


def _prediction_request() -> PredictionRequest:
    return PredictionRequest(
        symbol="600519",
        as_of_date=date(2024, 1, 15),
        frequency="daily",
        horizons=[1, 2],
        window_sizes=[5, 10],
        top_k=20,
    )


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
                "features": {"recent_return_1d_pct": 1.2},
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
                "warnings": ["research signal only"],
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
            "warnings": ["research signal only"],
        }
    )

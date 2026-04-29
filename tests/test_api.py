from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from ashare_similarity.schemas import SearchRequest, SearchResponse


@pytest.fixture
def api_client(monkeypatch, load_public_attr, maybe_patch_attr, app_config, mock_runtime):
    create_app = load_public_attr("ashare_similarity.app", "create_app")

    maybe_patch_attr(monkeypatch, "ashare_similarity.runtime.get_runtime", lambda: mock_runtime)
    maybe_patch_attr(monkeypatch, "ashare_similarity.web.routes.get_runtime", lambda: mock_runtime)
    maybe_patch_attr(monkeypatch, "ashare_similarity.web.routes.get_search_service", lambda: mock_runtime.search_service)

    app = create_app()
    app.state.runtime = mock_runtime
    app.state.app_config = app_config

    with TestClient(app) as client:
        yield client


def test_healthz_returns_ok_status(api_client):
    response = api_client.get("/api/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_post_search_returns_search_response_contract(api_client, mock_search_service):
    payload = {
        "symbol": "600519",
        "end_date": "2024-01-15",
        "frequency": "daily",
        "window_size": 5,
        "top_k": 2,
    }

    response = api_client.post("/api/search", json=payload)
    assert response.status_code == 200, response.text

    model = SearchResponse.model_validate(response.json())
    assert model.query_meta.symbol == payload["symbol"]
    assert model.query_meta.frequency == payload["frequency"]
    assert model.query_meta.window_size == payload["window_size"]
    assert len(model.balanced_matches) == 2
    assert len(model.shape_matches) == 2
    assert mock_search_service.calls, "Endpoint should delegate to the runtime search service."
    assert isinstance(mock_search_service.calls[0], SearchRequest), "Endpoint should parse JSON into SearchRequest before calling the service."


def test_post_search_accepts_stock_name(api_client, mock_runtime, mock_search_service):
    mock_runtime.data_service = SimpleNamespace(
        resolve_symbol_query=lambda query, frequency=None, prefer_cached=True: (
            {"symbol": "601778", "name": "晶科科技", "match_type": "name"} if query == "晶科科技" else None
        )
    )

    response = api_client.post(
        "/api/search",
        json={
            "symbol": "晶科科技",
            "end_date": "2024-01-15",
            "frequency": "daily",
            "window_size": 5,
            "top_k": 2,
        },
    )

    assert response.status_code == 200, response.text
    assert mock_search_service.calls[-1].symbol == "601778"
    assert response.json()["query_meta"]["symbol"] == "601778"


def test_post_search_rejects_invalid_payload(api_client):
    response = api_client.post(
        "/api/search",
        json={
            "symbol": "600519",
            "end_date": "2024-01-15",
            "frequency": "daily",
            "window_size": 2,
            "top_k": 0,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith("请求参数校验失败")


def test_post_search_preserves_minute_history_notice(api_client, mock_search_service, minute_notice_text):
    payload = {
        "symbol": "600519",
        "end_date": "2024-01-15",
        "frequency": "1",
        "window_size": 5,
        "top_k": 2,
    }

    response = api_client.post("/api/search", json=payload)
    assert response.status_code == 200, response.text

    model = SearchResponse.model_validate(response.json())
    surfaced_messages = [message for message in [model.data_freshness.notice, *model.warnings] if message]

    assert isinstance(mock_search_service.calls[-1], SearchRequest)
    assert mock_search_service.calls[-1].frequency == "1"
    assert minute_notice_text in surfaced_messages, (
        "Minute-frequency responses must surface the free-data boundary notice through "
        "`data_freshness.notice` or `warnings`."
    )


def test_export_endpoints_support_get_and_post(api_client, mock_search_service):
    query_string = "symbol=600519&end_date=2024-01-15&frequency=daily&window_size=5&top_k=2"

    get_csv = api_client.get(f"/api/export/csv?{query_string}")
    assert get_csv.status_code == 200
    assert get_csv.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"similarity_600519_daily_5.csv\"" == get_csv.headers["content-disposition"]
    assert "bucket,rank" in get_csv.content.decode("utf-8-sig")

    post_csv = api_client.post(
        "/api/export/csv",
        json={
            "symbol": "600519",
            "end_date": "2024-01-15",
            "frequency": "daily",
            "window_size": 5,
            "top_k": 2,
        },
    )
    assert post_csv.status_code == 200
    assert post_csv.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"similarity_600519_daily_5.csv\"" == post_csv.headers["content-disposition"]
    assert "bucket,rank" in post_csv.content.decode("utf-8-sig")

    get_html = api_client.get(f"/api/export/html?{query_string}")
    assert get_html.status_code == 200
    assert "A股K线相似检索报告" in get_html.text
    assert "600519" in get_html.text

    post_html = api_client.post(
        "/api/export/html",
        json={
            "symbol": "600519",
            "end_date": "2024-01-15",
            "frequency": "daily",
            "window_size": 5,
            "top_k": 2,
        },
    )
    assert post_html.status_code == 200
    assert "A股K线相似检索报告" in post_html.text
    assert "600519" in post_html.text


def test_export_endpoints_reuse_cached_search_response(api_client, mock_search_service):
    payload = {
        "symbol": "600519",
        "end_date": "2024-01-15",
        "frequency": "daily",
        "window_size": 5,
        "top_k": 2,
    }

    initial_search = api_client.post("/api/search", json=payload)
    assert initial_search.status_code == 200
    assert len(mock_search_service.calls) == 1

    get_csv = api_client.get("/api/export/csv", params=payload)
    assert get_csv.status_code == 200

    get_html = api_client.get("/api/export/html", params=payload)
    assert get_html.status_code == 200

    assert len(mock_search_service.calls) == 1, "Export endpoints should reuse the cached search response for the same payload."


def test_export_cache_warms_on_first_export(api_client, mock_search_service):
    params = {
        "symbol": "600519",
        "end_date": "2024-01-15",
        "frequency": "daily",
        "window_size": 5,
        "top_k": 2,
    }

    get_csv = api_client.get("/api/export/csv", params=params)
    assert get_csv.status_code == 200
    assert len(mock_search_service.calls) == 1

    post_html = api_client.post("/api/export/html", json=params)
    assert post_html.status_code == 200
    assert len(mock_search_service.calls) == 1, "A matching export request should hit the in-memory response cache."


def test_export_endpoints_return_400_when_search_payload_is_invalid(api_client, mock_search_service):
    def _raise_search_error(_request):
        raise ValueError("查询窗口不可用")

    mock_search_service.search = _raise_search_error

    get_csv = api_client.get(
        "/api/export/csv",
        params={
            "symbol": "600519",
            "end_date": "2024-01-15",
            "frequency": "daily",
            "window_size": 5,
            "top_k": 2,
        },
    )
    assert get_csv.status_code == 400
    assert get_csv.json()["detail"] == "查询窗口不可用"

    post_html = api_client.post(
        "/api/export/html",
        json={
            "symbol": "600519",
            "end_date": "2024-01-15",
            "frequency": "daily",
            "window_size": 5,
            "top_k": 2,
        },
    )
    assert post_html.status_code == 400
    assert post_html.json()["detail"] == "查询窗口不可用"


def test_cached_symbols_endpoint_returns_cached_choices(api_client, mock_runtime):
    mock_runtime.data_service = SimpleNamespace(
        get_cached_symbol_choices=lambda frequency, query=None, limit=12: {
            "frequency": frequency,
            "query": query or "",
            "total_cached": 3,
            "match_count": 2,
            "exact_match": {"symbol": "600036", "name": "招商银行"},
            "items": [
                {"symbol": "600036", "name": "招商银行"},
                {"symbol": "601166", "name": "兴业银行"},
            ][:limit],
        }
    )
    mock_runtime.store = SimpleNamespace(list_cached_symbols=lambda frequency: ["000333", "600036", "601166"])

    response = api_client.get("/api/cached-symbols", params={"frequency": "daily", "q": "600036", "limit": 5})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_cached"] == 3
    assert payload["exact_match"]["symbol"] == "600036"
    assert payload["items"][0]["name"] == "招商银行"


def test_prepare_symbol_endpoint_can_fill_missing_symbol_without_cli(api_client, mock_runtime):
    cached_symbols = {"000333"}

    class _StoreStub:
        def list_cached_symbols(self, frequency: str) -> list[str]:
            assert frequency == "daily"
            return sorted(cached_symbols)

    refresh_calls = []

    def _refresh_market_data(*, frequency, symbols, end_date, **kwargs):
        refresh_calls.append((frequency, tuple(symbols), str(end_date), kwargs))
        cached_symbols.update(symbols)
        return {
            "frequency": frequency,
            "symbols_requested": 1,
            "symbols_processed": 1,
            "completed_symbols": list(symbols),
            "failed_symbols": [],
            "skipped_recent_listing_symbols": [],
            "ignored_st_symbols": [],
        }

    mock_runtime.store = _StoreStub()
    mock_runtime.data_service = SimpleNamespace(
        refresh_market_data=_refresh_market_data,
        get_symbol_name=lambda symbol: "国机精工" if symbol == "002046" else None,
    )
    mock_runtime.feature_service = SimpleNamespace(build_feature_frame=lambda **kwargs: None)
    mock_runtime.index_service = SimpleNamespace(exists=lambda frequency, window_size: True)

    response = api_client.post(
        "/api/prepare-symbol",
        json={
            "symbol": "2046",
            "end_date": "2026-04-23",
            "frequency": "daily",
            "window_size": 10,
            "top_k": 10,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert refresh_calls, "Prepare endpoint should trigger a targeted refresh for the requested symbol."
    assert payload["symbol"] == "002046"
    assert payload["cached_before"] is False
    assert payload["cached_after"] is True
    assert payload["search_ready"] is True
    assert "可以直接检索" in payload["message"]


def test_prepare_symbol_endpoint_does_not_build_index_on_request_path(api_client, mock_runtime):
    cached_symbols = {"000333"}

    class _StoreStub:
        def list_cached_symbols(self, frequency: str) -> list[str]:
            assert frequency == "daily"
            return sorted(cached_symbols)

    def _refresh_market_data(*, frequency, symbols, end_date, **kwargs):
        del frequency, end_date, kwargs
        cached_symbols.update(symbols)
        return {
            "frequency": "daily",
            "symbols_requested": 1,
            "symbols_processed": 1,
            "completed_symbols": list(symbols),
            "failed_symbols": [],
            "skipped_recent_listing_symbols": [],
            "ignored_st_symbols": [],
        }

    mock_runtime.store = _StoreStub()
    mock_runtime.data_service = SimpleNamespace(
        refresh_market_data=_refresh_market_data,
        get_symbol_name=lambda symbol: "国机精工" if symbol == "002046" else None,
    )
    mock_runtime.feature_service = SimpleNamespace(
        build_feature_frame=lambda **kwargs: pytest.fail("Prepare endpoint must not rebuild indexes on the request path.")
    )
    mock_runtime.index_service = SimpleNamespace(
        exists=lambda frequency, window_size: False,
        build=lambda **kwargs: pytest.fail("Prepare endpoint must not rebuild indexes on the request path."),
    )

    response = api_client.post(
        "/api/prepare-symbol",
        json={
            "symbol": "2046",
            "end_date": "2026-04-23",
            "frequency": "daily",
            "window_size": 10,
            "top_k": 10,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["symbol"] == "002046"
    assert payload["cached_after"] is True
    assert payload["index_ready"] is False
    assert payload["search_ready"] is False
    assert payload["build_summary"] is None

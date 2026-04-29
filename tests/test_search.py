from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

import pandas as pd
import pytest

from ashare_similarity.schemas import DataFreshness


def _build_search_ranker(module, app_config, stub_factory):
    for attr_name in ("rank_candidates", "rerank_candidates", "select_top_matches"):
        attr = getattr(module, attr_name, None)
        if callable(attr):
            return attr

    search_service_cls = getattr(module, "SearchService", None)
    if search_service_cls is None:
        pytest.fail(
            "Search baseline needs either a module-level ranking hook "
            "(`rank_candidates`, `rerank_candidates`, or `select_top_matches`) "
            "or a `SearchService` class."
        )

    try:
        service = search_service_cls(
            app_config,
            stub_factory(default=lambda *args, **kwargs: None),
            stub_factory(default=lambda *args, **kwargs: None),
            stub_factory(default=lambda *args, **kwargs: None),
            stub_factory(default=lambda *args, **kwargs: None),
        )
    except TypeError as exc:  # pragma: no cover - exercised only when the integration surface changes
        pytest.fail(
            "SearchService constructor no longer matches the runtime contract "
            "`SearchService(config, store, data_service, feature_service, index_service)`. "
            f"Current error: {exc}"
        )

    for attr_name in (
        "rank_candidates",
        "rerank_candidates",
        "select_top_matches",
        "_rank_candidates",
        "_rerank_candidates",
        "_select_top_matches",
    ):
        attr = getattr(service, attr_name, None)
        if callable(attr):
            return attr

    pytest.fail(
        "Search ranking tests need a pure ranking hook such as "
        "`rank_candidates(...)` or `SearchService._rerank_candidates(...)` "
        "so synthetic candidates can be scored without touching real storage."
    )


def _invoke_ranker(
    ranker,
    *,
    invoke_with_supported_kwargs,
    sample_search_request,
    candidate_results,
    top_k,
):
    candidate_payload = [candidate.model_dump(mode="python") for candidate in candidate_results]
    candidate_frame = pd.json_normalize(candidate_payload)
    return invoke_with_supported_kwargs(
        ranker,
        request=sample_search_request,
        query_request=sample_search_request,
        candidates=candidate_payload,
        candidate_rows=candidate_payload,
        candidate_frame=candidate_frame,
        top_k=top_k,
    )


def test_search_ranking_sorts_by_score_and_caps_matches_per_symbol(
    app_config,
    load_module_or_fail,
    stub_factory,
    invoke_with_supported_kwargs,
    extract_match_rows,
    make_ohlcv_frame,
    make_match_result,
    sample_search_request,
):
    module = load_module_or_fail("ashare_similarity.search.service")
    ranker = _build_search_ranker(module, app_config, stub_factory)

    candidate_results = [
        make_match_result(
            make_ohlcv_frame(symbol="000001", start="2022-01-03", periods=5, pattern="similar"),
            balanced=0.99,
        ),
        make_match_result(
            make_ohlcv_frame(symbol="000002", start="2022-02-07", periods=5, pattern="query"),
            balanced=0.98,
        ),
        make_match_result(
            make_ohlcv_frame(symbol="000001", start="2022-03-01", periods=5, pattern="similar", base_price=13.0),
            balanced=0.97,
        ),
        make_match_result(
            make_ohlcv_frame(symbol="000001", start="2022-04-01", periods=5, pattern="flat", base_price=14.0),
            balanced=0.96,
        ),
    ]

    result = _invoke_ranker(
        ranker,
        invoke_with_supported_kwargs=invoke_with_supported_kwargs,
        sample_search_request=sample_search_request,
        candidate_results=candidate_results,
        top_k=3,
    )
    rows = extract_match_rows(result, "balanced_matches")
    score_values = [row["scores"]["balanced"] for row in rows]
    symbol_counts = Counter(row["symbol"] for row in rows)

    assert len(rows) == 3
    assert score_values == sorted(score_values, reverse=True), "Balanced ranking should be sorted descending by balanced score."
    assert symbol_counts["000001"] == 2, "Ranking must enforce the `max_matches_per_symbol=2` limit from the formal plan."
    assert ("000001", "2022-04-01", "2022-04-07") not in {
        (row["symbol"], row["start_date"], row["end_date"]) for row in rows
    }, "The third match from the same symbol should be removed after capping per-symbol matches."


def test_search_ranking_deduplicates_overlapping_windows_from_same_symbol(
    app_config,
    load_module_or_fail,
    stub_factory,
    invoke_with_supported_kwargs,
    extract_match_rows,
    make_ohlcv_frame,
    make_match_result,
    sample_search_request,
):
    module = load_module_or_fail("ashare_similarity.search.service")
    ranker = _build_search_ranker(module, app_config, stub_factory)

    overlapping_frame = make_ohlcv_frame(symbol="000001", start="2022-02-01", periods=7, pattern="similar")
    candidate_results = [
        make_match_result(overlapping_frame, start=0, window_size=5, balanced=0.99),
        make_match_result(overlapping_frame, start=2, window_size=5, balanced=0.98),
        make_match_result(
            make_ohlcv_frame(symbol="000002", start="2022-03-01", periods=5, pattern="query"),
            balanced=0.97,
        ),
    ]

    result = _invoke_ranker(
        ranker,
        invoke_with_supported_kwargs=invoke_with_supported_kwargs,
        sample_search_request=sample_search_request,
        candidate_results=candidate_results,
        top_k=3,
    )
    rows = extract_match_rows(result, "balanced_matches")
    selected_ranges = {(row["symbol"], row["start_date"], row["end_date"]) for row in rows}

    assert ("000001", "2022-02-01", "2022-02-07") in selected_ranges
    assert ("000001", "2022-02-03", "2022-02-09") not in selected_ranges, (
        "Overlapping windows from the same symbol should be deduplicated when the overlap exceeds "
        "the configured `overlap_days_limit`."
    )


def test_search_service_prefers_matches_with_available_forward_stats(
    app_config,
    load_module_or_fail,
    make_ohlcv_frame,
    make_match_result,
    stub_factory,
):
    module = load_module_or_fail("ashare_similarity.search.service")
    scoring = load_module_or_fail("ashare_similarity.search.scoring")

    service = module.SearchService(
        app_config,
        stub_factory(default=lambda *args, **kwargs: None),
        stub_factory(default=lambda *args, **kwargs: None),
        stub_factory(default=lambda *args, **kwargs: None),
        stub_factory(default=lambda *args, **kwargs: None),
    )

    no_forward = make_match_result(
        make_ohlcv_frame(symbol="000001", start="2022-01-03", periods=5, pattern="similar"),
        balanced=0.99,
    )
    no_forward = no_forward.model_copy(
        update={
            "forward_stats": [
                stat.model_copy(
                    update={
                        "return_pct": None,
                        "max_favorable_excursion_pct": None,
                        "max_drawdown_pct": None,
                    }
                )
                for stat in no_forward.forward_stats
            ]
        }
    )
    has_forward = make_match_result(
        make_ohlcv_frame(symbol="000002", start="2022-02-07", periods=5, pattern="query"),
        balanced=0.98,
    )

    match_by_symbol = {
        no_forward.symbol: no_forward,
        has_forward.symbol: has_forward,
    }

    def fake_build_match(row, score, frequency, *, history_cache):
        del score, frequency
        assert isinstance(history_cache, dict)
        return match_by_symbol[str(row["symbol"])]

    service._build_match = fake_build_match

    candidates = [
        module.CandidateMatch(
            row=pd.Series({"symbol": no_forward.symbol, "start_date": no_forward.start_date, "end_date": no_forward.end_date}),
            score=no_forward.scores,
            distances=scoring.DistanceBreakdown(
                balanced_distance=0.01,
                shape_distance=0.01,
                price_path_distance=0.01,
                candle_geometry_distance=0.01,
                volume_liquidity_distance=0.01,
                environment_distance=0.01,
            ),
        ),
        module.CandidateMatch(
            row=pd.Series({"symbol": has_forward.symbol, "start_date": has_forward.start_date, "end_date": has_forward.end_date}),
            score=has_forward.scores,
            distances=scoring.DistanceBreakdown(
                balanced_distance=0.02,
                shape_distance=0.02,
                price_path_distance=0.02,
                candle_geometry_distance=0.02,
                volume_liquidity_distance=0.02,
                environment_distance=0.02,
            ),
        ),
    ]

    results = service._build_ranked_matches(
        candidate_matches=candidates,
        query=SimpleNamespace(),
        frequency="daily",
        score_key="balanced",
        top_k=1,
        history_cache={},
    )

    assert [match.symbol for match in results] == [has_forward.symbol], (
        "Historical windows with usable forward statistics should outrank windows whose 1/3/5/10-day stats are all empty."
    )


def test_search_service_requires_prebuilt_index_instead_of_building_on_request(
    app_config,
    load_module_or_fail,
    stub_factory,
):
    module = load_module_or_fail("ashare_similarity.search.service")

    index_service = stub_factory(
        handlers={
            "exists": lambda frequency, window_size: False,
            "build": lambda *args, **kwargs: pytest.fail(
                "Search requests should not rebuild indexes on the request path; maintenance must happen offline."
            ),
        }
    )
    service = module.SearchService(
        app_config,
        stub_factory(default=lambda *args, **kwargs: None),
        stub_factory(default=lambda *args, **kwargs: None),
        stub_factory(default=lambda *args, **kwargs: None),
        index_service,
    )

    with pytest.raises(ValueError, match="maintain"):
        service._ensure_index("daily", 10)


def test_search_scope_defaults_to_historical(sample_search_request):
    assert sample_search_request.search_scope == "historical"


def test_search_service_can_detect_same_period_cross_section_overlap(
    app_config,
    load_module_or_fail,
    stub_factory,
):
    module = load_module_or_fail("ashare_similarity.search.service")
    service = module.SearchService(
        app_config,
        stub_factory(default=lambda *args, **kwargs: None),
        stub_factory(default=lambda *args, **kwargs: None),
        stub_factory(default=lambda *args, **kwargs: None),
        stub_factory(default=lambda *args, **kwargs: None),
    )

    query = SimpleNamespace(
        symbol="000333",
        metadata={"start_date": "2026-04-10", "end_date": "2026-04-23"},
    )
    same_period_other_symbol = pd.Series(
        {"symbol": "300444", "start_date": "2026-04-10", "end_date": "2026-04-23"}
    )
    old_period_other_symbol = pd.Series(
        {"symbol": "300444", "start_date": "2024-04-10", "end_date": "2024-04-23"}
    )

    assert service._overlaps_query_period(query, same_period_other_symbol)
    assert not service._overlaps_query(query, same_period_other_symbol)
    assert not service._overlaps_query_period(query, old_period_other_symbol)


def test_search_service_blocks_when_index_lags_newer_cached_history(
    app_config,
    load_module_or_fail,
    sample_search_request,
    sample_search_response,
    stub_factory,
):
    module = load_module_or_fail("ashare_similarity.search.service")

    searchable = SimpleNamespace(
        manifest={"component_slices": {}, "built_from": {"latest_data_at": "2026-04-22T15:00:00"}},
        metadata=pd.DataFrame({"symbol": ["000001", "000002"]}),
    )

    feature_service = stub_factory(
        handlers={
            "build_query_frame": lambda **kwargs: SimpleNamespace(
                symbol=kwargs["symbol"],
                frequency=kwargs["frequency"],
                window_size=kwargs["window_size"],
                metadata={"start_date": "2026-04-10", "end_date": "2026-04-23"},
                series=pd.DataFrame(
                    {
                        "date": pd.to_datetime(["2026-04-10", "2026-04-11"]),
                        "open": [1.0, 1.1],
                        "high": [1.2, 1.3],
                        "low": [0.9, 1.0],
                        "close": [1.1, 1.2],
                        "volume": [100.0, 120.0],
                    }
                ),
                component_slices={},
                warnings=[],
                matrix=pd.DataFrame([[0.1, 0.2]]).to_numpy(dtype="float32"),
            )
        }
    )
    index_service = stub_factory(
        handlers={
            "exists": lambda frequency, window_size: True,
            "load": lambda frequency, window_size: searchable,
        }
    )
    service = module.SearchService(
        app_config,
        stub_factory(handlers={"list_cached_symbols": lambda frequency: ["000001", "000002"]}),
        stub_factory(
            handlers={
                "get_data_freshness": lambda frequency: DataFreshness(
                    data_source="synthetic-fixture",
                    notice=None,
                    last_refresh_at=None,
                    latest_data_at="2026-04-23T15:00:00",
                )
            }
        ),
        feature_service,
        index_service,
    )

    service._collect_candidates = lambda **kwargs: []  # type: ignore[method-assign]
    service._build_ranked_matches = lambda **kwargs: []  # type: ignore[method-assign]
    service._query_meta = lambda **kwargs: sample_search_response.query_meta  # type: ignore[method-assign]
    service._aggregate_forward = lambda matches: []  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="离线重建索引"):
        service.search(sample_search_request)

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from ashare_similarity.data.service import DataService


def test_refresh_context_after_daily_update_rebuilds_industry_context_from_full_universe(app_config):
    calls: dict[str, object] = {}

    context_service = SimpleNamespace(
        refresh_market_context=lambda **kwargs: pd.DataFrame({"date": ["2026-04-23"]}),
        build_industry_context=lambda universe_df: calls.setdefault("industry_universe", universe_df.copy()),
    )
    data_service = DataService(
        app_config,
        store=SimpleNamespace(),
        provider=SimpleNamespace(),
        universe_service=SimpleNamespace(),
        context_service=context_service,
    )

    full_universe = pd.DataFrame(
        [
            {"symbol": "000001", "industry": "bank"},
            {"symbol": "000002", "industry": "appliance"},
        ]
    )
    observed_symbols: list[list[str] | None] = []

    def _enrich_universe_profiles(symbols=None):
        observed_symbols.append(symbols)
        return full_universe

    data_service.enrich_universe_profiles = _enrich_universe_profiles  # type: ignore[method-assign]

    data_service._refresh_context_after_daily_update(
        start_date=None,
        end_date=None,
        symbols=["000001"],
    )

    assert observed_symbols == [None], "Industry context should be rebuilt from the full cached universe, not just the latest backfill batch."
    assert calls["industry_universe"].to_dict(orient="records") == full_universe.to_dict(orient="records")


def test_refresh_context_after_daily_update_can_skip_industry_context_rebuild(app_config):
    calls: dict[str, object] = {}

    context_service = SimpleNamespace(
        refresh_market_context=lambda **kwargs: pd.DataFrame({"date": ["2026-04-23"]}),
        build_industry_context=lambda universe_df: calls.setdefault("industry_universe", universe_df.copy()),
    )
    data_service = DataService(
        app_config,
        store=SimpleNamespace(),
        provider=SimpleNamespace(),
        universe_service=SimpleNamespace(),
        context_service=context_service,
    )

    data_service.enrich_universe_profiles = lambda symbols=None: pd.DataFrame([{"symbol": "000001", "industry": "bank"}])  # type: ignore[method-assign]

    result = data_service._refresh_context_after_daily_update(
        start_date=None,
        end_date=None,
        symbols=["000001"],
        rebuild_industry_context=False,
    )

    assert not calls, "Large backfill refreshes should be able to skip the expensive industry-context rebuild."
    assert not result.empty


def test_cached_symbol_choices_exact_match_stock_name(app_config):
    data_service = DataService(
        app_config,
        store=SimpleNamespace(list_cached_symbols=lambda frequency: ["601778", "000333"]),
        provider=SimpleNamespace(),
        universe_service=SimpleNamespace(
            get_filtered_universe=lambda allow_bootstrap=False: pd.DataFrame(
                [
                    {"symbol": "601778", "name": "晶科科技", "is_st": False},
                    {"symbol": "000333", "name": "美的集团", "is_st": False},
                ]
            )
        ),
        context_service=SimpleNamespace(),
    )

    payload = data_service.get_cached_symbol_choices("daily", query="晶科科技")

    assert payload["exact_match"] == {"symbol": "601778", "name": "晶科科技"}
    assert payload["items"][0] == {"symbol": "601778", "name": "晶科科技"}


def test_resolve_symbol_query_accepts_unique_stock_name(app_config):
    data_service = DataService(
        app_config,
        store=SimpleNamespace(list_cached_symbols=lambda frequency: ["601778"]),
        provider=SimpleNamespace(),
        universe_service=SimpleNamespace(
            get_filtered_universe=lambda allow_bootstrap=False: pd.DataFrame(
                [
                    {"symbol": "601778", "name": "晶科科技", "is_st": False},
                    {"symbol": "000333", "name": "美的集团", "is_st": False},
                ]
            )
        ),
        context_service=SimpleNamespace(),
    )

    assert data_service.resolve_symbol_query("晶科科技", frequency="daily") == {
        "symbol": "601778",
        "name": "晶科科技",
        "match_type": "name",
    }

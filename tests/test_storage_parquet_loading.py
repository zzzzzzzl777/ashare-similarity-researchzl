from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import polars as pl

from ashare_similarity.data.storage import LocalDataStore


def _make_daily_bars(symbol: str, closes: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=len(closes))
    return pd.DataFrame(
        {
            "symbol": [symbol] * len(closes),
            "date": dates,
            "open": closes,
            "high": [value + 0.2 for value in closes],
            "low": [value - 0.2 for value in closes],
            "close": closes,
            "volume": [1_000_000 + index * 10_000 for index, _ in enumerate(closes)],
            "turnover": [close * 1_000_000 for close in closes],
        }
    )


def _make_intraday_index_frame(index_symbol: str, closes: list[float]) -> pl.DataFrame:
    timestamps = pd.date_range("2024-01-02 09:30:00", periods=len(closes), freq="30min")
    return pl.DataFrame(
        {
            "index_symbol": [index_symbol] * len(closes),
            "timestamp": timestamps,
            "open": closes,
            "high": [value + 0.1 for value in closes],
            "low": [value - 0.1 for value in closes],
            "close": closes,
            "volume": [100_000 + index * 1_000 for index, _ in enumerate(closes)],
            "turnover": [close * 100_000 for close in closes],
        }
    )


def test_load_market_data_filters_symbols_and_dates(app_config):
    store = LocalDataStore(app_config)
    store.save_bars("000001", "daily", _make_daily_bars("000001", [10.0, 10.2, 10.4, 10.6]))
    store.save_bars("000002", "daily", _make_daily_bars("000002", [20.0, 20.2, 20.4, 20.6]))

    frame = store.load_market_data(
        "daily",
        symbols=["000002"],
        start_date=date(2024, 1, 3),
        end_date=date(2024, 1, 4),
    )

    assert frame.get_column("symbol").to_list() == ["000002", "000002"]
    assert [value.date() for value in frame.get_column("date").to_list()] == [date(2024, 1, 3), date(2024, 1, 4)]
    assert frame.get_column("close").to_list() == [20.2, 20.4]


def test_load_market_index_data_filters_index_symbol_and_timestamps(app_config):
    store = LocalDataStore(app_config)
    store.save_market_index_data(
        "1min",
        "000300",
        _make_intraday_index_frame("000300", [3000.0, 3001.0, 3002.0, 3003.0]),
        provider="synthetic",
    )
    store.save_market_index_data(
        "1min",
        "000905",
        _make_intraday_index_frame("000905", [5000.0, 5001.0, 5002.0, 5003.0]),
        provider="synthetic",
    )

    frame = store.load_market_index_data(
        "1min",
        symbols=["000300"],
        start_date=datetime(2024, 1, 2, 10, 0, 0),
        end_date=datetime(2024, 1, 2, 10, 30, 0),
    )

    assert frame.get_column("index_symbol").to_list() == ["000300", "000300"]
    assert frame.get_column("timestamp").to_list() == [
        datetime(2024, 1, 2, 10, 0, 0),
        datetime(2024, 1, 2, 10, 30, 0),
    ]
    assert frame.get_column("close").to_list() == [3001.0, 3002.0]


def test_load_market_data_filters_lazy_scan_before_collect(app_config, monkeypatch):
    store = LocalDataStore(app_config)
    store.save_bars("000001", "daily", _make_daily_bars("000001", [10.0, 10.2, 10.4, 10.6]))

    events: list[str] = []
    original_filter = pl.LazyFrame.filter
    original_collect = pl.LazyFrame.collect

    def spy_filter(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        events.append("filter")
        return original_filter(self, *args, **kwargs)

    def spy_collect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        events.append("collect")
        return original_collect(self, *args, **kwargs)

    monkeypatch.setattr(pl.LazyFrame, "filter", spy_filter)
    monkeypatch.setattr(pl.LazyFrame, "collect", spy_collect)

    frame = store.load_market_data(
        "daily",
        symbols=["000001"],
        start_date=date(2024, 1, 3),
        end_date=date(2024, 1, 4),
    )

    assert frame.height == 2
    assert "collect" in events
    assert events[: events.index("collect")].count("filter") >= 2

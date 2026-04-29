from __future__ import annotations

from datetime import datetime

import pandas as pd


def test_market_symbol_routes_beijing_exchange_prefixes(load_module_or_fail):
    module = load_module_or_fail("ashare_similarity.data.base")

    assert module.to_market_symbol("920000") == "bj920000"
    assert module.to_market_symbol("830809") == "bj830809"
    assert module.to_market_symbol("831278") == "bj831278"


def test_daily_history_falls_back_to_sina_when_eastmoney_fails(app_config, load_module_or_fail, monkeypatch):
    module = load_module_or_fail("ashare_similarity.data.akshare_provider")
    provider = module.AkshareDataProvider(app_config, store=None)

    monkeypatch.setattr(provider, "_with_retry", lambda func, *args, **kwargs: func(*args, **kwargs))

    def fake_hist(**kwargs):
        raise RuntimeError("eastmoney unavailable")

    def fake_daily(**kwargs):
        assert kwargs["symbol"] == "sz000001"
        return pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
                "open": [10.0, 10.2],
                "high": [10.3, 10.5],
                "low": [9.9, 10.0],
                "close": [10.1, 10.4],
                "volume": [1000, 1200],
                "amount": [10000, 12500],
                "turnover": [0.01, 0.012],
            }
        )

    monkeypatch.setattr(module.ak, "stock_zh_a_hist", fake_hist)
    monkeypatch.setattr(module.ak, "stock_zh_a_daily", fake_daily)

    frame = provider.fetch_price_history("000001", "daily")

    assert not frame.empty
    assert frame["symbol"].tolist() == ["000001", "000001"]
    assert frame["frequency"].tolist() == ["daily", "daily"]
    assert round(float(frame.iloc[-1]["turnover"]), 4) == 1.2
    assert frame["pct_change"].notna().all()
    assert frame["amplitude"].notna().all()


def test_minute_history_falls_back_to_sina_when_eastmoney_fails(app_config, load_module_or_fail, monkeypatch):
    module = load_module_or_fail("ashare_similarity.data.akshare_provider")
    provider = module.AkshareDataProvider(app_config, store=None)

    monkeypatch.setattr(provider, "_with_retry", lambda func, *args, **kwargs: func(*args, **kwargs))

    def fake_hist_min(**kwargs):
        raise RuntimeError("eastmoney minute unavailable")

    def fake_sina_minute(**kwargs):
        assert kwargs["symbol"] == "sz000001"
        assert kwargs["period"] == "5"
        return pd.DataFrame(
            {
                "day": [
                    "2024-01-03 09:35:00",
                    "2024-01-03 09:40:00",
                    "2024-01-03 09:45:00",
                ],
                "open": [10.0, 10.1, 10.2],
                "high": [10.1, 10.2, 10.3],
                "low": [9.9, 10.0, 10.1],
                "close": [10.05, 10.15, 10.25],
                "volume": [100, 110, 120],
                "amount": [1000, 1100, 1200],
            }
        )

    monkeypatch.setattr(module.ak, "stock_zh_a_hist_min_em", fake_hist_min)
    monkeypatch.setattr(module.ak, "stock_zh_a_minute", fake_sina_minute)

    frame = provider.fetch_price_history(
        "000001",
        "5",
        start_date=datetime(2024, 1, 3, 9, 36),
        end_date=datetime(2024, 1, 3, 9, 45),
    )

    assert not frame.empty
    assert frame["frequency"].tolist() == ["5", "5"]
    assert frame["symbol"].tolist() == ["000001", "000001"]
    assert frame["timestamp"].tolist() == [
        pd.Timestamp("2024-01-03 09:40:00"),
        pd.Timestamp("2024-01-03 09:45:00"),
    ]
    assert frame["pct_change"].notna().all()


def test_market_index_history_falls_back_to_tencent_when_sina_fails(app_config, load_module_or_fail, monkeypatch):
    module = load_module_or_fail("ashare_similarity.data.akshare_provider")
    provider = module.AkshareDataProvider(app_config, store=None)

    monkeypatch.setattr(provider, "_with_retry", lambda func, *args, **kwargs: func(*args, **kwargs))

    def fake_index_daily(**kwargs):
        raise RuntimeError("sina index unavailable")

    def fake_index_daily_tx(**kwargs):
        assert kwargs["symbol"] == "sh000001"
        return pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
                "open": [3000, 3020],
                "close": [3010, 3035],
                "high": [3020, 3040],
                "low": [2995, 3015],
                "amount": [1.0, 2.0],
            }
        )

    monkeypatch.setattr(module.ak, "stock_zh_index_daily", fake_index_daily)
    monkeypatch.setattr(module.ak, "stock_zh_index_daily_tx", fake_index_daily_tx)

    frame = provider.fetch_market_index_history("sh000001")

    assert not frame.empty
    assert frame["index_symbol"].tolist() == ["sh000001", "sh000001"]
    assert frame["pct_change"].tolist()[0] == 0.0
    assert round(float(frame["pct_change"].tolist()[1]), 4) == round((3035 - 3010) / 3010 * 100.0, 4)


def test_daily_history_merges_secondary_source_when_primary_is_partial(app_config, load_module_or_fail, monkeypatch):
    module = load_module_or_fail("ashare_similarity.data.akshare_provider")
    provider = module.AkshareDataProvider(app_config, store=None)

    monkeypatch.setattr(provider, "_with_retry", lambda func, *args, **kwargs: func(*args, **kwargs))

    def fake_hist(**kwargs):
        return pd.DataFrame(
            {
                "日期": [pd.Timestamp("2024-01-03").date(), pd.Timestamp("2024-01-04").date()],
                "股票代码": ["000001", "000001"],
                "开盘": [10.3, 10.4],
                "收盘": [10.35, 10.45],
                "最高": [10.5, 10.6],
                "最低": [10.2, 10.3],
                "成交量": [1300, 1400],
                "成交额": [13000, 14500],
                "振幅": [2.0, 2.1],
                "涨跌幅": [1.0, 0.97],
                "涨跌额": [0.1, 0.1],
                "换手率": [1.1, 1.2],
            }
        )

    def fake_daily(**kwargs):
        assert kwargs["symbol"] == "sz000001"
        return pd.DataFrame(
            {
                "date": [
                    pd.Timestamp("2024-01-01").date(),
                    pd.Timestamp("2024-01-02").date(),
                    pd.Timestamp("2024-01-03").date(),
                ],
                "open": [10.0, 10.1, 9.0],
                "high": [10.2, 10.3, 9.5],
                "low": [9.9, 10.0, 8.8],
                "close": [10.05, 10.2, 9.1],
                "volume": [1000, 1100, 9999],
                "amount": [10000, 11200, 99999],
                "turnover": [0.01, 0.011, 0.5],
            }
        )

    monkeypatch.setattr(module.ak, "stock_zh_a_hist", fake_hist)
    monkeypatch.setattr(module.ak, "stock_zh_a_daily", fake_daily)

    frame = provider.fetch_price_history("000001", "daily")

    assert frame["date"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
        pd.Timestamp("2024-01-04"),
    ]
    assert frame["symbol"].tolist() == ["000001", "000001", "000001", "000001"]
    assert frame["frequency"].tolist() == ["daily", "daily", "daily", "daily"]
    assert round(float(frame.loc[frame["date"] == pd.Timestamp("2024-01-03"), "close"].iloc[0]), 2) == 10.35
    assert round(float(frame.loc[frame["date"] == pd.Timestamp("2024-01-03"), "turnover"].iloc[0]), 2) == 1.1


def test_daily_history_uses_beijing_prefix_for_920_symbols_on_sina_fallback(app_config, load_module_or_fail, monkeypatch):
    module = load_module_or_fail("ashare_similarity.data.akshare_provider")
    provider = module.AkshareDataProvider(app_config, store=None)

    monkeypatch.setattr(provider, "_with_retry", lambda func, *args, **kwargs: func(*args, **kwargs))

    def fake_hist(**kwargs):
        raise RuntimeError("eastmoney unavailable")

    def fake_daily(**kwargs):
        assert kwargs["symbol"] == "bj920000"
        return pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
                "open": [10.0, 10.2],
                "high": [10.3, 10.5],
                "low": [9.9, 10.0],
                "close": [10.1, 10.4],
                "volume": [1000, 1200],
                "amount": [10000, 12500],
                "turnover": [0.01, 0.012],
            }
        )

    monkeypatch.setattr(module.ak, "stock_zh_a_hist", fake_hist)
    monkeypatch.setattr(module.ak, "stock_zh_a_daily", fake_daily)

    frame = provider.fetch_price_history("920000", "daily")

    assert not frame.empty
    assert frame["symbol"].tolist() == ["920000", "920000"]


def test_daily_history_falls_back_to_cdr_source_for_689_symbols(app_config, load_module_or_fail, monkeypatch):
    module = load_module_or_fail("ashare_similarity.data.akshare_provider")
    provider = module.AkshareDataProvider(app_config, store=None)

    monkeypatch.setattr(provider, "_with_retry", lambda func, *args, **kwargs: func(*args, **kwargs))

    def fake_hist(**kwargs):
        raise RuntimeError("eastmoney unavailable")

    def fake_daily(**kwargs):
        raise RuntimeError("sina unavailable")

    def fake_cdr(**kwargs):
        assert kwargs["symbol"] == "sh689009"
        return pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
                "open": [29.8, 28.63],
                "high": [29.95, 29.10],
                "low": [28.63, 28.54],
                "close": [28.65, 28.72],
                "volume": [3513703.0, 2392553.0],
                "amount": [102247150.0, 68839827.0],
            }
        )

    monkeypatch.setattr(module.ak, "stock_zh_a_hist", fake_hist)
    monkeypatch.setattr(module.ak, "stock_zh_a_daily", fake_daily)
    monkeypatch.setattr(module.ak, "stock_zh_a_cdr_daily", fake_cdr)
    monkeypatch.setattr(module.ak, "stock_zh_a_hist_tx", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("should not use tx")))

    frame = provider.fetch_price_history("689009", "daily")

    assert not frame.empty
    assert frame["symbol"].tolist() == ["689009", "689009"]
    assert frame["close"].tolist() == [28.65, 28.72]

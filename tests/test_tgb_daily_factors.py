from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_similarity.prediction.tgb_daily_factors import (
    TGB_MARKET_COLUMNS,
    TGB_STOCK_COLUMNS,
    build_tgb_market_regime_factors,
    build_tgb_stock_factors,
)


def _make_daily(
    symbols: list[str],
    periods: int = 30,
    *,
    base_price: float = 10.0,
) -> pd.DataFrame:
    """Build a synthetic daily OHLCV DataFrame."""
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for symbol in symbols:
        close = base_price + np.cumsum(np.random.default_rng(42).normal(0, 0.1, periods))
        close = np.maximum(close, 1.0)
        high = close * 1.02
        low = close * 0.98
        rows.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "date": dates,
                    "open": close * 0.995,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": np.random.default_rng(42).integers(500_000, 3_000_000, periods).astype(float),
                    "amount": 100_000_000.0,
                    "turnover": 4.0,
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def test_tgb_stock_factors_produces_all_columns():
    daily = _make_daily(["600001", "600002"], periods=70)
    factor = build_tgb_stock_factors(daily)

    assert factor.name == "tgb_stock_daily"
    assert factor.join_keys == ("symbol", "date")
    for col in TGB_STOCK_COLUMNS:
        assert col in factor.columns, f"Missing column: {col}"
        assert col in factor.frame.columns
    assert factor.frame[list(TGB_STOCK_COLUMNS)].isna().sum().sum() == 0


def test_tgb_ma_alignment_perfect_uptrend():
    dates = pd.bdate_range("2024-01-02", periods=80)
    close = 10.0 + np.arange(80) * 0.2
    daily = pd.DataFrame(
        {
            "symbol": "600001",
            "date": dates,
            "open": close * 0.99,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1_000_000.0,
        }
    )

    factor = build_tgb_stock_factors(daily)
    last = factor.frame.sort_values("date").iloc[-1]
    assert last["tgb_ma_alignment_score"] == pytest.approx(4.0)
    assert last["tgb_ma_divergence_5"] > 0.0


def test_tgb_ma_alignment_downtrend():
    dates = pd.bdate_range("2024-01-02", periods=80)
    close = 20.0 - np.arange(80) * 0.15
    close = np.maximum(close, 1.0)
    daily = pd.DataFrame(
        {
            "symbol": "600001",
            "date": dates,
            "open": close * 1.01,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1_000_000.0,
        }
    )

    factor = build_tgb_stock_factors(daily)
    last = factor.frame.sort_values("date").iloc[-1]
    assert last["tgb_ma_alignment_score"] <= 1.0


def test_tgb_board_height_vs_max_detects_leader():
    dates = pd.bdate_range("2024-01-02", periods=10)
    rows = []
    close_leader = [10.0] * 5 + [10.0 * 1.1, 10.0 * 1.1 * 1.1, 10.0 * 1.1 * 1.1 * 1.1, 10.0 * 1.1**3 * 1.01, 10.0 * 1.1**3 * 1.02]
    close_follower = [10.0] * 10
    rows.append(
        pd.DataFrame(
            {
                "symbol": "600001",
                "date": dates,
                "open": close_leader,
                "high": close_leader,
                "low": [c * 0.99 for c in close_leader],
                "close": close_leader,
                "volume": 1_000_000.0,
            }
        )
    )
    rows.append(
        pd.DataFrame(
            {
                "symbol": "600002",
                "date": dates,
                "open": close_follower,
                "high": [c * 1.01 for c in close_follower],
                "low": [c * 0.99 for c in close_follower],
                "close": close_follower,
                "volume": 1_000_000.0,
            }
        )
    )

    factor = build_tgb_stock_factors(pd.concat(rows, ignore_index=True))
    leader_day7 = factor.frame[
        (factor.frame["symbol"] == "600001") & (factor.frame["date"] == dates[7])
    ]
    assert len(leader_day7) == 1
    assert leader_day7.iloc[0]["tgb_board_height_vs_max"] == pytest.approx(1.0)

    follower_day7 = factor.frame[
        (factor.frame["symbol"] == "600002") & (factor.frame["date"] == dates[7])
    ]
    assert follower_day7.iloc[0]["tgb_board_height_vs_max"] == pytest.approx(0.0)


def test_tgb_market_regime_produces_all_columns():
    daily = _make_daily(["600001", "600002", "600003"], periods=20)
    factor = build_tgb_market_regime_factors(daily)

    assert factor.name == "tgb_market_regime"
    assert factor.join_keys == ("date",)
    for col in TGB_MARKET_COLUMNS:
        assert col in factor.columns, f"Missing column: {col}"
    assert factor.frame[list(TGB_MARKET_COLUMNS)].isna().sum().sum() == 0


def test_tgb_market_regime_nuclear_button():
    dates = pd.bdate_range("2024-01-02", periods=5)
    rows = []
    for idx in range(10):
        symbol = f"600{idx:03d}"
        close = np.full(5, 10.0)
        if idx < 3:
            close[-2] = 10.0 * 1.06
            close[-1] = 10.0 * 0.93
        rows.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "date": dates,
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 1_000_000.0,
                }
            )
        )
    factor = build_tgb_market_regime_factors(pd.concat(rows, ignore_index=True))
    last = factor.frame.sort_values("date").iloc[-1]
    assert last["tgb_nuclear_button_count"] >= 3.0


def test_tgb_leader_break_signal():
    dates = pd.bdate_range("2024-01-02", periods=8)
    rows = []
    leader_close = [10.0, 11.0, 12.1, 13.31, 14.641, 14.641 * 1.1, 14.641 * 1.1 * 0.95, 14.641 * 1.1 * 0.95 * 0.97]
    rows.append(
        pd.DataFrame(
            {
                "symbol": "600001",
                "date": dates,
                "open": leader_close,
                "high": leader_close,
                "low": [c * 0.98 for c in leader_close],
                "close": leader_close,
                "volume": 1_000_000.0,
            }
        )
    )
    for i in range(5):
        symbol = f"600{i+2:03d}"
        rows.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "date": dates,
                    "open": 10.0,
                    "high": 10.2,
                    "low": 9.8,
                    "close": 10.0,
                    "volume": 1_000_000.0,
                }
            )
        )
    factor = build_tgb_market_regime_factors(pd.concat(rows, ignore_index=True))
    day6 = factor.frame[factor.frame["date"] == dates[6]]
    assert len(day6) == 1
    assert day6.iloc[0]["tgb_leader_break_signal"] == pytest.approx(1.0)


def test_tgb_eod_rush_risk_detects_sneak_limit():
    dates = pd.bdate_range("2024-01-02", periods=5)
    daily = pd.DataFrame(
        {
            "symbol": "600001",
            "date": dates,
            "open": [10.0, 10.0, 10.0, 10.0, 10.0],
            "high": [10.1, 10.1, 10.1, 10.1, 10.6],
            "low": [9.9, 9.9, 9.9, 9.9, 10.0],
            "close": [10.0, 10.0, 10.0, 10.0, 10.59],
            "volume": 1_000_000.0,
        }
    )
    factor = build_tgb_stock_factors(daily)
    last = factor.frame.sort_values("date").iloc[-1]
    assert last["tgb_eod_rush_risk"] == pytest.approx(1.0)


def test_tgb_zhaban_recovery_detects_bounce():
    dates = pd.bdate_range("2024-01-02", periods=4)
    daily = pd.DataFrame(
        {
            "symbol": "600001",
            "date": dates,
            "open": [10.0, 10.0, 10.0, 9.7],
            "high": [10.1, 10.1, 11.0, 10.3],
            "low": [9.9, 9.9, 9.5, 9.5],
            "close": [10.0, 10.0, 9.6, 10.2],
            "volume": 1_000_000.0,
        }
    )
    factor = build_tgb_stock_factors(daily)
    day3 = factor.frame[factor.frame["date"] == dates[2]]
    assert day3.iloc[0]["tgb_zhaban_recovery_score"] == pytest.approx(0.0)

    day4 = factor.frame[factor.frame["date"] == dates[3]]
    assert day4.iloc[0]["tgb_zhaban_recovery_score"] > 0.0

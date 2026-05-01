from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_similarity.prediction.intraday_factors import build_intraday_daily_factors, build_intraday_factor_frame


def test_build_intraday_daily_factors_extracts_tail_session_signal():
    timestamps = pd.date_range("2026-04-20 09:30", periods=60, freq="5min")
    close = np.linspace(10.0, 11.0, len(timestamps))
    frame = pd.DataFrame(
        {
            "symbol": "600001",
            "timestamp": timestamps,
            "open": close - 0.02,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
            "volume": np.r_[np.full(54, 1000.0), np.full(6, 5000.0)],
        }
    )
    frame["amount"] = frame["close"] * frame["volume"]

    factors = build_intraday_daily_factors(frame)

    assert len(factors) == 1
    row = factors.iloc[0]
    assert row["symbol"] == "600001"
    assert row["last_30min_return"] > 0
    assert row["last_5min_return"] > 0
    assert "late_surge_ratio" in factors.columns
    assert "late_surge_lure_risk" in factors.columns
    assert "steady_intraday_rise_score" in factors.columns
    assert row["steady_intraday_rise_score"] > 0
    assert row["last_30min_volume_ratio"] > 1
    assert row["last_30min_vs_day"] > 0
    assert row["first_15min_return"] > 0
    assert row["closing_auction_volume_ratio"] > 1
    assert row["vwap_deviation_eod"] > 0
    assert 0.0 <= row["high_point_time"] <= 1.0
    assert 0.0 <= row["low_point_time"] <= 1.0
    assert row["intraday_close_position"] > 0.8
    assert row["volume_gini"] > 0
    assert 0.0 <= row["volume_entropy"] <= 1.0
    assert row["up_volume_ratio"] > 0.8
    assert row["realized_volatility_5min"] > 0


def test_build_intraday_factor_frame_prefixes_columns_for_merge_safety():
    timestamps = pd.date_range("2026-04-20 09:30", periods=10, freq="5min")
    frame = pd.DataFrame(
        {
            "symbol": "600001",
            "timestamp": timestamps,
            "open": np.linspace(10.0, 10.3, len(timestamps)),
            "high": np.linspace(10.1, 10.4, len(timestamps)),
            "low": np.linspace(9.9, 10.2, len(timestamps)),
            "close": np.linspace(10.0, 10.35, len(timestamps)),
            "volume": np.full(len(timestamps), 1000.0),
        }
    )

    factor = build_intraday_factor_frame(frame)

    assert factor.name == "intraday_structure"
    assert "minute_intraday_return" in factor.columns
    assert "intraday_return" not in factor.columns
    assert "minute_last_30min_return" in factor.frame.columns

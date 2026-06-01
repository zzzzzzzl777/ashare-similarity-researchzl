from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_similarity.prediction.intraday_factors import (
    _last_minutes,
    build_intraday_daily_factors,
    build_intraday_factor_frame,
)


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
    assert row["intraday_vol_herfindahl"] > 0
    assert 0.0 <= row["intraday_profit_ratio"] <= 1.0
    assert row["intraday_volume_clustering"] > 1
    assert row["eod_volume_concentration"] > 0
    assert 0.0 <= row["trapped_volume"] <= 1.0
    assert row["tail_volatility_ratio"] >= 0
    assert 0.0 <= row["intraday_consolidation_duration"] <= 1.0
    assert 0.0 <= row["intraday_breakout_bar_ratio"] <= 1.0
    assert 0.0 <= row["intraday_volume_shrink_ratio"] <= 1.0
    assert 0.0 <= row["prev_30min_volume_ratio"] <= 1.0


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
    assert "minute_intraday_vol_herfindahl" in factor.columns
    assert "minute_prev_30min_volume_ratio" in factor.columns
    assert "intraday_return" not in factor.columns
    assert "minute_last_30min_return" in factor.frame.columns


def test_last_minutes_handles_lunch_break():
    """Bug 4 verification: _last_minutes must use bar count, not timedelta."""
    morning = pd.date_range("2024-06-03 09:30", "2024-06-03 11:30", freq="5min")
    afternoon = pd.date_range("2024-06-03 13:00", "2024-06-03 13:15", freq="5min")
    timestamps = morning.append(afternoon)
    n = len(timestamps)
    group = pd.DataFrame({
        "timestamp": timestamps,
        "open": 10.0,
        "high": 10.1,
        "low": 9.9,
        "close": np.linspace(10.0, 10.5, n),
        "volume": 1000.0,
    })
    result = _last_minutes(group, minutes=30)
    assert len(result) == 6, f"expected 6 bars for 30 min with 5-min bars, got {len(result)}"
    assert result["timestamp"].iloc[0] >= pd.Timestamp("2024-06-03 11:00")

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_similarity.prediction.free_data_factors import (
    build_board_structure_factor,
    build_cross_market_return_factor,
    build_market_emotion_factor,
)


def test_build_market_emotion_factor_from_daily_cache():
    dates = pd.bdate_range("2024-01-02", periods=25)
    rows = []
    for symbol, base in [("600001", 10.0), ("600002", 20.0)]:
        close = base + np.arange(len(dates)) * 0.1
        rows.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "date": dates,
                    "high": close * 1.02,
                    "low": close * 0.98,
                    "close": close,
                    "amount": 100_000_000.0,
                    "turnover": 4.0,
                }
            )
        )
    daily = pd.concat(rows, ignore_index=True)
    daily.loc[(daily["symbol"] == "600001") & (daily["date"] == dates[-1]), "close"] *= 1.105
    daily.loc[(daily["symbol"] == "600001") & (daily["date"] == dates[-1]), "high"] = daily.loc[
        (daily["symbol"] == "600001") & (daily["date"] == dates[-1]), "close"
    ]

    factor = build_market_emotion_factor(daily)

    assert factor.name == "market_emotion_daily_proxy"
    assert factor.join_keys == ("date",)
    assert "market_limit_up_count" in factor.columns
    assert factor.frame["market_limit_up_count"].iloc[-1] >= 1.0
    assert "liquidity_exhaustion_signal" in factor.columns
    assert "quant_climax_type" in factor.columns
    assert "market_amount_ratio_20" in factor.columns
    assert "volume_is_king_signal" in factor.columns
    assert "post_decline_transition" in factor.columns
    assert "market_limit_seal_success_rate" in factor.columns
    assert "seal_rate_80_threshold" in factor.columns
    assert "bull_hotspot_bear_oversold" in factor.columns
    assert "prev_top20_chase_return" in factor.columns
    assert "prev_top20_chase_win_rate" in factor.columns
    assert "collapse_warning_signal" in factor.columns
    assert "bullish_pivot_recognition" in factor.columns
    assert "limit_premium_failure_signal" in factor.columns
    assert "bad_sentiment_no_sweep" in factor.columns
    assert "high_leader_crash_sentiment_collapse" in factor.columns
    assert "money_effect_sector_rotation" in factor.columns
    assert "full_position_trigger" in factor.columns
    assert "same_height_success_rate_1" in factor.columns
    assert "prev_failed_limit_up_return" in factor.columns
    assert "failed_limit_up_loss_pressure" in factor.columns
    assert factor.lag_rule == "T day close-derived; use for T+1 prediction only"


def test_build_market_emotion_factor_tracks_new_market_structure_signals():
    dates = pd.bdate_range("2024-01-02", periods=12)
    rows = []
    for idx in range(25):
        symbol = f"600{idx:03d}"
        close = np.full(len(dates), 10.0)
        if idx < 10:
            close[-1] = close[-2] * 0.90
        elif idx < 20:
            close[-1] = close[-2] * 1.10
        high = close.copy()
        low = close.copy()
        rows.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "date": dates,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": 1_000_000.0,
                    "amount": 10_000_000.0,
                    "turnover": 3.0,
                }
            )
        )
    factor = build_market_emotion_factor(pd.concat(rows, ignore_index=True))
    last = factor.frame.sort_values("date").iloc[-1]

    assert last["liquidity_exhaustion_signal"] == pytest.approx(1.0)
    assert last["market_split_signal"] == pytest.approx(1.0)
    assert last["market_limit_down_rate"] > 0.0


def test_build_market_emotion_factor_tracks_failed_board_next_day_profile():
    dates = pd.bdate_range("2024-01-02", periods=5)
    rows = []
    close = np.array([10.0, 10.5, 9.5, 9.6, 9.7])
    rows.append(
        pd.DataFrame(
            {
                "symbol": "600001",
                "date": dates,
                "high": [10.0, 11.0, 9.7, 9.8, 9.9],
                "low": [10.0, 10.0, 9.4, 9.5, 9.6],
                "close": close,
                "amount": 100_000_000.0,
                "turnover": 4.0,
            }
        )
    )
    rows.append(
        pd.DataFrame(
            {
                "symbol": "600002",
                "date": dates,
                "high": np.full(len(dates), 20.2),
                "low": np.full(len(dates), 19.8),
                "close": np.full(len(dates), 20.0),
                "amount": 100_000_000.0,
                "turnover": 4.0,
            }
        )
    )

    factor = build_market_emotion_factor(pd.concat(rows, ignore_index=True))
    target = factor.frame.sort_values("date").iloc[2]

    assert target["prev_failed_limit_up_count"] == pytest.approx(1.0)
    assert target["prev_failed_limit_up_return"] < 0.0
    assert target["prev_failed_limit_up_loss_rate"] == pytest.approx(1.0)
    assert target["failed_limit_up_loss_pressure"] > 0.0


def test_build_cross_market_return_factor_applies_known_time_lag():
    dates = pd.bdate_range("2024-01-02", periods=6)
    index = pd.DataFrame({"date": dates, "close": [100, 101, 102, 103, 104, 105]})

    factor = build_cross_market_return_factor({"vix": index}, lag_days={"vix": 1})

    assert factor.name == "cross_market_returns"
    assert "cross_vix_ret_1" in factor.columns
    assert pd.isna(factor.frame["cross_vix_ret_1"].iloc[1])
    assert factor.frame["cross_vix_ret_1"].iloc[2] == pytest.approx(1.0)


def test_build_board_structure_factor_tracks_limit_up_echelon():
    dates = pd.bdate_range("2024-01-02", periods=6)
    rows = []
    for symbol, base in [("600001", 10.0), ("600002", 20.0)]:
        close = np.full(len(dates), base)
        for idx in range(1, len(dates)):
            close[idx] = close[idx - 1] * (1.10 if symbol == "600001" and idx <= 3 else 1.01)
        rows.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "date": dates,
                    "high": close,
                    "low": close * 0.98,
                    "close": close,
                    "volume": np.linspace(1_000_000.0, 3_000_000.0, len(dates)),
                }
            )
        )
    daily = pd.concat(rows, ignore_index=True)

    factor = build_board_structure_factor(daily)
    target = factor.frame[factor.frame["symbol"] == "600001"].sort_values("date")

    assert factor.name == "board_structure_daily_proxy"
    assert factor.join_keys == ("symbol", "date")
    assert target["board_count"].iloc[3] >= 3.0
    assert target["is_space_board"].iloc[3] == pytest.approx(1.0)
    assert target["volume_vs_prev"].iloc[-1] > 0.0
    assert "break_node_new_dragon" in factor.columns


def test_build_board_structure_factor_tracks_signal_system_proxies():
    dates = pd.bdate_range("2024-01-02", periods=15)
    close = np.full(len(dates), 10.0)
    volume = np.linspace(1_000_000.0, 2_000_000.0, len(dates))
    volume[-2] = 20_000_000.0
    open_ = close.copy()
    open_[-1] = close[-2] * 1.005
    daily = pd.DataFrame(
        {
            "symbol": "600001",
            "date": dates,
            "open": open_,
            "high": close * 1.02,
            "low": close * 0.98,
            "close": close,
            "volume": volume,
        }
    )

    factor = build_board_structure_factor(daily)
    target = factor.frame.sort_values("date")

    assert target["explosive_vol_next_weak"].iloc[-1] == pytest.approx(1.0)
    assert "shrink_after_rotten" in factor.columns
    assert "bet_decline_exhaustion" in factor.columns

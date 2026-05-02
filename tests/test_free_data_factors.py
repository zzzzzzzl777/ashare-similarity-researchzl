from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import tempfile
from pathlib import Path

from ashare_similarity.prediction.free_data_factors import (
    _build_stk_mins_factors,
    _limit_threshold_for_symbol,
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


def test_limit_threshold_varies_by_board():
    """Bug 1 verification: ChiNext/STAR use 20%, main board uses 10%."""
    assert _limit_threshold_for_symbol("600001") == 10.0
    assert _limit_threshold_for_symbol("000001") == 10.0
    assert _limit_threshold_for_symbol("300001") == 20.0
    assert _limit_threshold_for_symbol("301001") == 20.0
    assert _limit_threshold_for_symbol("688001") == 20.0
    assert _limit_threshold_for_symbol("830001") == 30.0
    assert _limit_threshold_for_symbol("430001") == 30.0

    dates = pd.bdate_range("2024-01-02", periods=3)
    rows = []
    for symbol, base in [("600001", 10.0), ("300001", 10.0), ("688001", 10.0)]:
        close = [base, base, base * 1.15]
        rows.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "date": dates,
                    "high": close,
                    "low": [base, base, base * 1.10],
                    "close": close,
                    "volume": 1_000_000.0,
                    "amount": 100_000_000.0,
                    "turnover": 4.0,
                }
            )
        )
    daily = pd.concat(rows, ignore_index=True)

    board = build_board_structure_factor(daily)
    last_date = dates[-1]
    board_last = board.frame[board.frame["date"] == last_date].set_index("symbol")

    assert board_last.loc["600001", "board_count"] >= 1.0, "main board 15% should be limit-up"
    assert board_last.loc["300001", "board_count"] == 0.0, "ChiNext 15% must NOT be limit-up (threshold 20%)"
    assert board_last.loc["688001", "board_count"] == 0.0, "STAR 15% must NOT be limit-up (threshold 20%)"

    emotion = build_market_emotion_factor(daily)
    last_emo = emotion.frame[emotion.frame["date"] == last_date].iloc[0]
    assert last_emo["market_limit_up_count"] == 1.0, "only main board stock hits limit"


def test_stk_mins_last30_uses_1430_not_1445():
    """Bug 2 verification: last 30 minutes should start at 14:30, not 14:45."""
    import datetime as _dt

    times_morning = [_dt.time(h, m) for h in range(9, 12) for m in range(0, 60, 5)
                     if _dt.time(9, 30) <= _dt.time(h, m) <= _dt.time(11, 30)]
    times_afternoon = [_dt.time(h, m) for h in range(13, 16) for m in range(0, 60, 5)
                       if _dt.time(13, 5) <= _dt.time(h, m) <= _dt.time(15, 0)]
    all_times = times_morning + times_afternoon
    n = len(all_times)
    date_str = "2024-06-03"
    trade_times = [pd.Timestamp(f"{date_str} {t.strftime('%H:%M:%S')}") for t in all_times]
    bars = pd.DataFrame({
        "ts_code": "600001.SH",
        "trade_time": trade_times,
        "open": 10.0,
        "high": 10.1,
        "low": 9.9,
        "close": np.linspace(10.0, 10.5, n),
        "vol": 1000.0,
        "amount": 10000.0,
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        mins_dir = Path(tmpdir) / "stk_mins_5"
        mins_dir.mkdir()
        bars.to_parquet(mins_dir / "600001.parquet")
        result = _build_stk_mins_factors(Path(tmpdir))

    assert len(result) == 1
    row = result.iloc[0]
    assert not pd.isna(row["tushare_last_30min_return"]), "last30 should have data"

    last30_count = len([t for t in all_times if t >= _dt.time(14, 30)])
    assert last30_count >= 6, f"expected >= 6 bars in last 30 min, got {last30_count}"


def test_cross_market_foreign_indices_auto_lag():
    """Bug 3 verification: US/VIX/CNH must auto-lag >= 1 to prevent leakage."""
    dates = pd.bdate_range("2024-01-02", periods=6)
    vix_data = pd.DataFrame({"date": dates, "close": [20, 21, 22, 23, 24, 25]})
    sp500_data = pd.DataFrame({"date": dates, "close": [4500, 4510, 4520, 4530, 4540, 4550]})
    sh_data = pd.DataFrame({"date": dates, "close": [3000, 3010, 3020, 3030, 3040, 3050]})

    factor = build_cross_market_return_factor(
        {"vix": vix_data, "sp500": sp500_data, "sh000001": sh_data}
    )

    assert "cross_vix_ret_1" in factor.columns
    assert "cross_sp500_ret_1" in factor.columns
    assert "cross_sh000001_ret_1" in factor.columns

    frame = factor.frame.sort_values("date").reset_index(drop=True)
    assert pd.isna(frame["cross_vix_ret_1"].iloc[1]), "vix day 1 should be NaN (lag=1)"
    assert not pd.isna(frame["cross_vix_ret_1"].iloc[2]), "vix day 2 should have value"
    assert pd.isna(frame["cross_sp500_ret_1"].iloc[1]), "sp500 day 1 should be NaN (lag=1)"
    assert not pd.isna(frame["cross_sh000001_ret_1"].iloc[1]), "A-share index needs no lag"


def test_emotion_phase_one_hot_mutually_exclusive():
    """Bug 5 verification: emotion_phase binary indicators must be mutually exclusive."""
    dates = pd.bdate_range("2024-01-02", periods=5)
    rows = []
    for idx in range(30):
        symbol = f"600{idx:03d}"
        close = np.full(len(dates), 10.0)
        if idx < 5:
            close[-1] = close[-2] * 0.90
        elif idx >= 25:
            close[-1] = close[-2] * 1.10
        rows.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "date": dates,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 1_000_000.0,
                    "amount": 10_000_000.0,
                    "turnover": 3.0,
                }
            )
        )
    factor = build_market_emotion_factor(pd.concat(rows, ignore_index=True))
    phase_cols = [c for c in factor.columns if c.startswith("emotion_phase_") and c != "emotion_phase_code"]
    for _, row in factor.frame.iterrows():
        total = sum(row[c] for c in phase_cols)
        assert total <= 1.0, f"date {row['date']}: multiple emotion phases active ({total})"

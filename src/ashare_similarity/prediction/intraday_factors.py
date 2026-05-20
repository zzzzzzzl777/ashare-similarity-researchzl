from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_similarity.prediction.factor_cache_manager import FactorFrame


INTRADAY_FACTOR_COLUMNS: tuple[str, ...] = (
    "minute_intraday_return",
    "minute_last_30min_return",
    "minute_last_30min_vs_day",
    "minute_price_1430_return",
    "minute_late_surge_ratio",
    "minute_late_surge_lure_risk",
    "minute_last_5min_return",
    "minute_last_30min_volume_ratio",
    "minute_first_15min_return",
    "minute_first_15min_volume_ratio",
    "minute_midday_return",
    "minute_afternoon_start_return",
    "minute_closing_auction_volume_ratio",
    "minute_vwap_deviation_eod",
    "minute_high_point_time",
    "minute_low_point_time",
    "minute_intraday_close_position",
    "minute_volume_distribution_skew",
    "minute_volume_entropy",
    "minute_volume_gini",
    "minute_price_volume_corr_intraday",
    "minute_return_autocorr_intraday",
    "minute_realized_volatility_5min",
    "minute_realized_skew",
    "minute_realized_kurtosis",
    "minute_intraday_trend_strength",
    "minute_steady_intraday_rise_score",
    "minute_morning_afternoon_imbalance",
    "minute_up_volume_ratio",
    "minute_intraday_vol_herfindahl",
    "minute_intraday_profit_ratio",
    "minute_vwap_deviation_normalized",
    "minute_intraday_volume_clustering",
    "minute_intraday_ofi_proxy",
    "minute_close_impact_3min",
    "minute_eod_volume_concentration",
    "minute_trapped_volume",
    "minute_tail_volatility_ratio",
    "minute_intraday_price_reversal",
    "minute_bar_obi_proxy",
    "minute_intraday_consolidation_duration",
    "minute_intraday_breakout_bar_ratio",
    "minute_intraday_volume_shrink_ratio",
    "minute_prev_30min_volume_ratio",
)


def build_intraday_factor_frame(minute_bars: pd.DataFrame) -> FactorFrame:
    factors = build_intraday_daily_factors(minute_bars)
    if factors.empty:
        frame = pd.DataFrame(columns=["symbol", "date", *INTRADAY_FACTOR_COLUMNS])
    else:
        rename = {
            column: f"minute_{column}"
            for column in factors.columns
            if column not in {"symbol", "date"}
        }
        frame = factors.rename(columns=rename)
        for column in INTRADAY_FACTOR_COLUMNS:
            if column not in frame.columns:
                frame[column] = 0.0
        frame = frame.loc[:, ["symbol", "date", *INTRADAY_FACTOR_COLUMNS]]
    return FactorFrame(
        name="intraday_structure",
        frame=frame,
        columns=INTRADAY_FACTOR_COLUMNS,
        source="cached_minute_bars",
        asof_time="after_close",
        lag_rule="T-day minute bars up to close only; usable for T+1 prediction.",
    )


def build_intraday_daily_factors(minute_bars: pd.DataFrame) -> pd.DataFrame:
    if minute_bars.empty or "timestamp" not in minute_bars.columns:
        return pd.DataFrame()

    frame = minute_bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame = frame.dropna(subset=["timestamp"]).sort_values("timestamp")
    if frame.empty:
        return pd.DataFrame()
    frame["date"] = frame["timestamp"].dt.normalize()
    for column in ("open", "high", "low", "close", "volume", "amount"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "amount" not in frame.columns:
        frame["amount"] = frame["close"].fillna(0.0) * frame["volume"].fillna(0.0)

    rows: list[dict[str, object]] = []
    group_columns = ["date"]
    if "symbol" in frame.columns:
        group_columns.insert(0, "symbol")
    for key, group in frame.groupby(group_columns, sort=False):
        group = group.dropna(subset=["open", "high", "low", "close"])
        if group.empty:
            continue
        symbol = key[0] if isinstance(key, tuple) and len(group_columns) == 2 else group["symbol"].iloc[0] if "symbol" in group.columns else None
        day = key[-1] if isinstance(key, tuple) else key
        last_window = _last_minutes(group, minutes=30)
        last_5_window = _last_minutes(group, minutes=5)
        first_15_window = _first_minutes(group, minutes=15)
        midday_window = _clock_window(group, start="11:00", end="11:30")
        afternoon_start_window = _clock_window(group, start="13:00", end="13:15")
        day_open = float(group["open"].iloc[0])
        day_close = float(group["close"].iloc[-1])
        last_open = float(last_window["open"].iloc[0]) if not last_window.empty else day_close
        last_5_open = float(last_5_window["open"].iloc[0]) if not last_5_window.empty else day_close
        first_15_open = float(first_15_window["open"].iloc[0]) if not first_15_window.empty else day_open
        first_15_close = float(first_15_window["close"].iloc[-1]) if not first_15_window.empty else day_open
        midday_return = _window_return(midday_window)
        afternoon_start_return = _window_return(afternoon_start_window)
        total_volume = float(group["volume"].fillna(0.0).sum()) if "volume" in group.columns else 0.0
        last_volume = float(last_window["volume"].fillna(0.0).sum()) if "volume" in last_window.columns else 0.0
        first_15_volume = float(first_15_window["volume"].fillna(0.0).sum()) if "volume" in first_15_window.columns else 0.0
        closing_auction_volume = float(group["volume"].fillna(0.0).iloc[-1]) if "volume" in group.columns else 0.0
        amount = float(group["amount"].fillna(0.0).sum())
        volume = float(group["volume"].fillna(0.0).sum()) if "volume" in group.columns else 0.0
        vwap = amount / volume if volume > 0 else day_close
        high_index = group["high"].astype(float).idxmax()
        low_index = group["low"].astype(float).idxmin()
        first_ts = group["timestamp"].iloc[0]
        last_ts = group["timestamp"].iloc[-1]
        span_seconds = max((last_ts - first_ts).total_seconds(), 1.0)
        high_time_position = (group.loc[high_index, "timestamp"] - first_ts).total_seconds() / span_seconds
        low_time_position = (group.loc[low_index, "timestamp"] - first_ts).total_seconds() / span_seconds
        avg_30m_volume = total_volume / max(_session_minutes(group) / 30.0, 1.0)
        avg_15m_volume = total_volume / max(_session_minutes(group) / 15.0, 1.0)
        avg_bar_volume = total_volume / max(float(len(group)), 1.0)
        intraday_return = _pct(day_close, day_open)
        last_30min_return = _pct(day_close, last_open)
        price_1430 = _price_at_or_before(group, "14:30")
        price_1430_return = _pct(day_close, price_1430) if price_1430 is not None else 0.0
        late_surge_ratio = _safe_div(day_close - (price_1430 if price_1430 is not None else last_open), day_close - day_open)
        minute_returns = group["close"].astype(float).pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
        minute_return_pct = minute_returns * 100.0
        volumes = group["volume"].fillna(0.0).astype(float) if "volume" in group.columns else pd.Series(0.0, index=group.index)
        price_volume_corr = _safe_corr(minute_return_pct.to_numpy(), volumes.to_numpy())
        positive_volume = float(volumes[minute_returns > 0.0].sum())
        closes = group["close"].astype(float)
        highs = group["high"].astype(float)
        lows = group["low"].astype(float)
        volume_values = volumes.to_numpy(dtype=float)
        close_values = closes.to_numpy(dtype=float)
        high_values = highs.to_numpy(dtype=float)
        low_values = lows.to_numpy(dtype=float)
        running_amount = group["amount"].fillna(0.0).astype(float).cumsum()
        running_volume = volumes.cumsum()
        running_vwap = (running_amount / running_volume.replace(0.0, np.nan)).ffill().fillna(day_close)
        running_vwap_values = running_vwap.to_numpy(dtype=float)
        price_std = float(np.nanstd(close_values))
        avg_volume = float(np.nanmean(volume_values)) if len(volume_values) else 0.0
        total_volume_safe = max(total_volume, 1e-12)
        volume_share = volume_values / total_volume_safe
        last_6_returns = minute_returns.tail(6).to_numpy(dtype=float)
        first_half = group.iloc[: max(1, len(group) // 2)]
        first_half_return = _pct(float(first_half["close"].iloc[-1]), float(first_half["open"].iloc[0])) if not first_half.empty else 0.0
        abs_return_sum = float(np.abs(minute_return_pct.to_numpy(dtype=float)).sum())
        bar_spread = np.maximum(high_values - low_values, 1e-12)
        bar_close_position = (close_values - low_values) / bar_spread
        decays = np.power(0.97, np.arange(len(group) - 1, -1, -1, dtype=float))
        trapped_mask = running_vwap_values > close_values
        rows.append(
            {
                "symbol": str(symbol).zfill(6) if symbol is not None else None,
                "date": pd.Timestamp(day).date(),
                "intraday_return": intraday_return,
                "last_30min_return": last_30min_return,
                "last_30min_vs_day": last_30min_return / max(abs(intraday_return), 0.05),
                "price_1430_return": price_1430_return,
                "late_surge_ratio": late_surge_ratio,
                "late_surge_lure_risk": float(intraday_return > 0.0 and late_surge_ratio > 0.50),
                "last_5min_return": _pct(day_close, last_5_open),
                "last_30min_volume_ratio": last_volume / avg_30m_volume if avg_30m_volume > 0 else 0.0,
                "first_15min_return": _pct(first_15_close, first_15_open),
                "first_15min_volume_ratio": first_15_volume / avg_15m_volume if avg_15m_volume > 0 else 0.0,
                "midday_return": midday_return,
                "afternoon_start_return": afternoon_start_return,
                "closing_auction_volume_ratio": closing_auction_volume / avg_bar_volume if avg_bar_volume > 0 else 0.0,
                "vwap_deviation_eod": _pct(day_close, vwap),
                "high_point_time": float(high_time_position),
                "low_point_time": float(low_time_position),
                "intraday_close_position": _close_position(
                    day_close,
                    float(group["high"].max()),
                    float(group["low"].min()),
                ),
                "volume_distribution_skew": _weighted_skew_by_position(volumes),
                "volume_entropy": _normalized_entropy(volumes),
                "volume_gini": _gini(volumes),
                "price_volume_corr_intraday": price_volume_corr,
                "return_autocorr_intraday": _autocorr(minute_return_pct.to_numpy()),
                "realized_volatility_5min": float(np.sqrt(np.square(minute_return_pct.to_numpy()).sum())),
                "realized_skew": _series_skew(minute_return_pct.to_numpy()),
                "realized_kurtosis": _series_kurtosis(minute_return_pct.to_numpy()),
                "intraday_trend_strength": abs(intraday_return) / max(float(np.abs(minute_return_pct).sum()), 0.05),
                "steady_intraday_rise_score": max(intraday_return, 0.0) / max(float(np.abs(minute_return_pct).sum()), 0.05)
                * max(0.0, 1.0 - max(late_surge_ratio - 0.50, 0.0)),
                "morning_afternoon_imbalance": _morning_afternoon_imbalance(group, volumes),
                "up_volume_ratio": positive_volume / total_volume if total_volume > 0 else 0.0,
                "intraday_vol_herfindahl": float(np.square(volume_share).sum()),
                "intraday_profit_ratio": float(volume_values[close_values > running_vwap_values].sum() / total_volume_safe),
                "vwap_deviation_normalized": _safe_div(day_close - vwap, price_std),
                "intraday_volume_clustering": _safe_div(float(np.nanmax(volume_values)) if len(volume_values) else 0.0, avg_volume),
                "intraday_ofi_proxy": float(np.sign(minute_returns.to_numpy(dtype=float)) @ volume_values / total_volume_safe),
                "close_impact_3min": _pct(day_close, float(close_values[-2])) if len(close_values) >= 2 else 0.0,
                "eod_volume_concentration": float(volume_values[-1] / total_volume_safe) if len(volume_values) else 0.0,
                "trapped_volume": float((volume_values * trapped_mask.astype(float) * decays).sum() / total_volume_safe),
                "tail_volatility_ratio": _safe_div(float(np.nanstd(last_6_returns)), float(np.nanstd(minute_returns.to_numpy(dtype=float)))),
                "intraday_price_reversal": abs(first_half_return) / max(abs_return_sum, 0.05),
                "bar_obi_proxy": float(((bar_close_position - 0.5) * volume_values).sum() / total_volume_safe),
                "intraday_consolidation_duration": float(
                    np.mean(np.abs(close_values - running_vwap_values) / np.maximum(running_vwap_values, 1e-12) < 0.003)
                ),
                "intraday_breakout_bar_ratio": float(
                    np.mean((close_values > running_vwap_values * 1.005) & (volume_values > avg_volume * 1.5))
                ),
                "intraday_volume_shrink_ratio": float(np.mean(volume_values < avg_volume * 0.6)) if avg_volume > 0 else 0.0,
                "prev_30min_volume_ratio": float(
                    _clock_window(group, start="14:00", end="14:30")["volume"].fillna(0.0).astype(float).sum()
                    / total_volume_safe
                )
                if "volume" in group.columns
                else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _last_minutes(group: pd.DataFrame, *, minutes: int) -> pd.DataFrame:
    if len(group) <= 1:
        return group
    diffs = group["timestamp"].diff().dropna()
    bar_interval_min = diffs.median().total_seconds() / 60.0
    if bar_interval_min <= 0:
        return group
    n_bars = max(1, round(minutes / bar_interval_min))
    return group.iloc[-min(n_bars, len(group)):]


def _first_minutes(group: pd.DataFrame, *, minutes: int) -> pd.DataFrame:
    if len(group) <= 1:
        return group
    diffs = group["timestamp"].diff().dropna()
    bar_interval_min = diffs.median().total_seconds() / 60.0
    if bar_interval_min <= 0:
        return group
    n_bars = max(1, round(minutes / bar_interval_min))
    return group.iloc[:min(n_bars, len(group))]


def _clock_window(group: pd.DataFrame, *, start: str, end: str) -> pd.DataFrame:
    times = group["timestamp"].dt.time
    start_time = pd.Timestamp(start).time()
    end_time = pd.Timestamp(end).time()
    return group[(times >= start_time) & (times <= end_time)]


def _window_return(group: pd.DataFrame) -> float:
    if group.empty:
        return 0.0
    return _pct(float(group["close"].iloc[-1]), float(group["open"].iloc[0]))


def _price_at_or_before(group: pd.DataFrame, clock_time: str) -> float | None:
    cutoff = pd.Timestamp(clock_time).time()
    subset = group[group["timestamp"].dt.time <= cutoff]
    if subset.empty:
        return None
    return float(subset["close"].iloc[-1])


def _session_minutes(group: pd.DataFrame) -> float:
    if len(group) <= 1:
        return 1.0
    return max((group["timestamp"].iloc[-1] - group["timestamp"].iloc[0]).total_seconds() / 60.0, float(len(group)))


def _pct(value: float, base: float) -> float:
    if abs(base) < 1e-12:
        return 0.0
    return (value / base - 1.0) * 100.0


def _safe_div(value: float, base: float) -> float:
    if abs(base) < 1e-12:
        return 0.0
    return value / base


def _close_position(close: float, high: float, low: float) -> float:
    spread = high - low
    if spread <= 1e-12:
        return 0.5
    return (close - low) / spread


def _safe_corr(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) < 2 or len(right) < 2:
        return 0.0
    left = np.nan_to_num(left.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    right = np.nan_to_num(right.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    if np.std(left) <= 1e-12 or np.std(right) <= 1e-12:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def _autocorr(values: np.ndarray) -> float:
    values = np.nan_to_num(values.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    if len(values) < 3:
        return 0.0
    return _safe_corr(values[1:], values[:-1])


def _series_skew(values: np.ndarray) -> float:
    values = np.nan_to_num(values.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    if len(values) < 3:
        return 0.0
    centered = values - values.mean()
    std = values.std()
    if std <= 1e-12:
        return 0.0
    return float(np.mean((centered / std) ** 3))


def _series_kurtosis(values: np.ndarray) -> float:
    values = np.nan_to_num(values.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    if len(values) < 4:
        return 0.0
    centered = values - values.mean()
    std = values.std()
    if std <= 1e-12:
        return 0.0
    return float(np.mean((centered / std) ** 4))


def _normalized_entropy(values: pd.Series) -> float:
    weights = values.fillna(0.0).astype(float).clip(lower=0.0).to_numpy()
    total = weights.sum()
    if total <= 0.0 or len(weights) <= 1:
        return 0.0
    prob = weights / total
    prob = prob[prob > 0.0]
    return float(-(prob * np.log(prob)).sum() / np.log(len(weights)))


def _gini(values: pd.Series) -> float:
    array = np.sort(values.fillna(0.0).astype(float).clip(lower=0.0).to_numpy())
    if len(array) == 0:
        return 0.0
    total = array.sum()
    if total <= 0.0:
        return 0.0
    index = np.arange(1, len(array) + 1, dtype=float)
    return float((2.0 * np.sum(index * array) / (len(array) * total)) - ((len(array) + 1.0) / len(array)))


def _weighted_skew_by_position(values: pd.Series) -> float:
    weights = values.fillna(0.0).astype(float).clip(lower=0.0).to_numpy()
    total = weights.sum()
    if total <= 0.0 or len(weights) <= 1:
        return 0.0
    positions = np.linspace(-1.0, 1.0, len(weights))
    mean = float(np.sum(positions * weights) / total)
    std = float(np.sqrt(np.sum(((positions - mean) ** 2) * weights) / total))
    if std <= 1e-12:
        return 0.0
    return float(np.sum((((positions - mean) / std) ** 3) * weights) / total)


def _morning_afternoon_imbalance(group: pd.DataFrame, volumes: pd.Series) -> float:
    times = group["timestamp"].dt.time
    morning = float(volumes[times < pd.Timestamp("12:00").time()].sum())
    afternoon = float(volumes[times >= pd.Timestamp("12:00").time()].sum())
    if morning == 0.0 and afternoon == 0.0:
        split = len(volumes) // 2
        morning = float(volumes.iloc[:split].sum())
        afternoon = float(volumes.iloc[split:].sum())
    return morning / max(afternoon, 1e-12)

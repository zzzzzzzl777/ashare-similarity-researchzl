from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ashare_similarity.schemas import PredictionFactorSnapshot


@dataclass(slots=True)
class BuiltFactors:
    snapshot: PredictionFactorSnapshot
    vector: dict[str, float]


FACTOR_COLUMNS: tuple[str, ...] = (
    "recent_return_1d_pct",
    "recent_return_3d_pct",
    "recent_return_5d_pct",
    "volatility_5d_pct",
    "volatility_10d_pct",
    "volume_zscore",
    "volume_trend_ratio",
    "amount_zscore",
    "amount_trend_ratio",
    "turnover_zscore",
    "turnover_trend_ratio",
    "range_pct",
    "atr_14_pct",
    "obv_trend_5",
    "mfi_14",
    "candle_body_ratio",
    "upper_shadow_ratio",
    "lower_shadow_ratio",
    "market_trend_5",
    "industry_trend_5",
    "industry_relative_strength_5",
    "large_order_fire_score",
    "short_hot_score",
    "limit_threshold_pct",
    "limit_up_like",
    "limit_down_like",
    "big_up",
    "big_down",
    "consecutive_up_days",
    "consecutive_limit_up_days",
)


def build_factor_snapshot(
    series: pd.DataFrame,
    *,
    symbol: str,
    name: str | None,
    as_of_date: str,
    window_size: int,
) -> BuiltFactors:
    series = _truncate_as_of(series, as_of_date)
    if series.empty:
        vector = {column: 0.0 for column in FACTOR_COLUMNS}
        snapshot = PredictionFactorSnapshot(
            symbol=symbol,
            name=name,
            as_of_date=as_of_date,
            window_size=window_size,
            features=vector,
        )
        return BuiltFactors(snapshot=snapshot, vector=vector)

    frame = series.copy()
    close = frame["close"].astype(float)
    open_ = frame["open"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    volume = frame["volume"].fillna(0.0).astype(float)
    amount = _amount_series(frame, close, volume)
    turnover = _numeric_series(frame, "turnover")
    returns = close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0) * 100.0
    latest = frame.iloc[-1]
    high_low = max(float(latest["high"]) - float(latest["low"]), 1e-9)
    recent_5d = _return_over(close, 5)
    volume_zscore = _zscore_latest(np.log1p(np.maximum(volume.to_numpy(dtype=float), 0.0)))
    volume_trend = _tail_mean_ratio(volume, recent=5, previous=5)
    amount_zscore = _zscore_latest(np.log1p(np.maximum(amount.to_numpy(dtype=float), 0.0)))
    amount_trend = _tail_mean_ratio(amount, recent=5, previous=5)
    turnover_zscore = _zscore_latest(turnover.to_numpy(dtype=float))
    turnover_trend = _tail_mean_ratio(turnover, recent=5, previous=5)
    range_pct = _finite_float((float(latest["high"]) - float(latest["low"])) / max(float(latest["close"]), 1e-9) * 100.0)
    volatility_10d = float(returns.tail(10).std(ddof=0)) if len(returns) else 0.0
    atr_14_pct = _atr_pct(high, low, close, window=14)
    obv_trend_5 = _obv_trend(close, volume, window=5)
    mfi_14 = _mfi(high, low, close, volume, window=14)
    market_trend_5 = _last_numeric(frame, "market_trend_5")
    industry_trend_5 = _last_numeric(frame, "industry_return_trend_5")
    industry_relative_strength_5 = _finite_float(industry_trend_5 - market_trend_5)
    limit_threshold = _limit_threshold_pct(symbol)
    limit_streak = _consecutive_threshold(returns, threshold=max(limit_threshold - 0.5, 1.0))
    up_streak = _consecutive_positive(returns)
    latest_ret = _return_over(close, 1) or 0.0
    limit_up_like = latest_ret >= max(limit_threshold - 0.5, 1.0)
    limit_down_like = latest_ret <= -max(limit_threshold - 0.5, 1.0)
    big_up = latest_ret >= 5.0
    big_down = latest_ret <= -5.0
    intraday_reversal_score = _intraday_reversal_score(
        latest_ret=latest_ret,
        high=float(latest["high"]),
        low=float(latest["low"]),
        close=float(latest["close"]),
        open_=float(latest["open"]),
        volume_zscore=volume_zscore or 0.0,
        amount_zscore=amount_zscore or 0.0,
    )
    large_order_fire_score = _finite_float(
        max(amount_zscore or 0.0, 0.0) * 0.35
        + max(volume_zscore or 0.0, 0.0) * 0.25
        + max(turnover_zscore or 0.0, 0.0) * 0.20
        + max(range_pct, 0.0) / 10.0
        + max(latest_ret, 0.0) / 10.0
        + max(obv_trend_5, 0.0) * 0.15
    )
    short_hot_score = _finite_float(
        large_order_fire_score * 0.45
        + max(industry_relative_strength_5, 0.0) * 0.20
        + max(volatility_10d, 0.0) / 10.0
        + min(float(limit_streak), 3.0) * 0.20
        + max(intraday_reversal_score, 0.0) * 0.10
    )
    short_candidate = _is_short_candidate(
        amount_zscore=amount_zscore or 0.0,
        volume_zscore=volume_zscore or 0.0,
        turnover_zscore=turnover_zscore or 0.0,
        range_pct=range_pct,
        volatility_10d_pct=volatility_10d,
        large_order_fire_score=large_order_fire_score,
    )
    price_volume_divergence = bool(
        (recent_5d is not None)
        and (volume_trend is not None)
        and ((recent_5d > 0 and volume_trend < 1.0) or (recent_5d < 0 and volume_trend > 1.0))
    )

    vector = {
        "recent_return_1d_pct": latest_ret,
        "recent_return_3d_pct": _return_over(close, 3) or 0.0,
        "recent_return_5d_pct": recent_5d or 0.0,
        "volatility_5d_pct": float(returns.tail(5).std(ddof=0)) if len(returns) else 0.0,
        "volatility_10d_pct": volatility_10d,
        "volume_zscore": volume_zscore or 0.0,
        "volume_trend_ratio": volume_trend or 1.0,
        "amount_zscore": amount_zscore or 0.0,
        "amount_trend_ratio": amount_trend or 1.0,
        "turnover_zscore": turnover_zscore or 0.0,
        "turnover_trend_ratio": turnover_trend or 1.0,
        "range_pct": range_pct,
        "atr_14_pct": atr_14_pct,
        "obv_trend_5": obv_trend_5,
        "mfi_14": mfi_14,
        "candle_body_ratio": abs(float(latest["close"]) - float(latest["open"])) / high_low,
        "upper_shadow_ratio": (float(latest["high"]) - max(float(latest["open"]), float(latest["close"]))) / high_low,
        "lower_shadow_ratio": (min(float(latest["open"]), float(latest["close"])) - float(latest["low"])) / high_low,
        "market_trend_5": market_trend_5,
        "industry_trend_5": industry_trend_5,
        "industry_relative_strength_5": industry_relative_strength_5,
        "large_order_fire_score": large_order_fire_score,
        "short_hot_score": short_hot_score,
        "limit_threshold_pct": limit_threshold,
        "limit_up_like": 1.0 if limit_up_like else 0.0,
        "limit_down_like": 1.0 if limit_down_like else 0.0,
        "big_up": 1.0 if big_up else 0.0,
        "big_down": 1.0 if big_down else 0.0,
        "consecutive_up_days": float(up_streak),
        "consecutive_limit_up_days": float(limit_streak),
    }
    vector = {key: _finite_float(value) for key, value in vector.items()}
    features: dict[str, float | int | bool | str | None] = dict(vector)
    features["price_volume_divergence"] = price_volume_divergence
    features["short_candidate"] = short_candidate
    features["board_chain_stage"] = _board_chain_stage(limit_streak)
    features["main_board_only"] = _is_main_board_symbol(symbol)
    features["intraday_reversal_score"] = intraday_reversal_score
    snapshot = PredictionFactorSnapshot(
        symbol=symbol,
        name=name,
        as_of_date=as_of_date,
        window_size=window_size,
        recent_return_1d_pct=vector["recent_return_1d_pct"],
        recent_return_3d_pct=vector["recent_return_3d_pct"],
        recent_return_5d_pct=vector["recent_return_5d_pct"],
        volatility_5d_pct=vector["volatility_5d_pct"],
        volume_zscore=vector["volume_zscore"],
        volume_trend_ratio=vector["volume_trend_ratio"],
        price_volume_divergence=price_volume_divergence,
        candle_body_ratio=vector["candle_body_ratio"],
        upper_shadow_ratio=vector["upper_shadow_ratio"],
        lower_shadow_ratio=vector["lower_shadow_ratio"],
        market_trend_5=vector["market_trend_5"],
        industry_trend_5=vector["industry_trend_5"],
        industry_relative_strength_5=vector["industry_relative_strength_5"],
        amount_zscore=vector["amount_zscore"],
        amount_trend_ratio=vector["amount_trend_ratio"],
        turnover_zscore=vector["turnover_zscore"],
        turnover_trend_ratio=vector["turnover_trend_ratio"],
        range_pct=vector["range_pct"],
        volatility_10d_pct=vector["volatility_10d_pct"],
        atr_14_pct=vector["atr_14_pct"],
        obv_trend_5=vector["obv_trend_5"],
        mfi_14=vector["mfi_14"],
        large_order_fire_score=vector["large_order_fire_score"],
        short_hot_score=vector["short_hot_score"],
        limit_threshold_pct=vector["limit_threshold_pct"],
        limit_up_like=limit_up_like,
        limit_down_like=limit_down_like,
        big_up=big_up,
        big_down=big_down,
        consecutive_up_days=up_streak,
        consecutive_limit_up_days=limit_streak,
        board_chain_stage=_board_chain_stage(limit_streak),
        short_candidate=short_candidate,
        features=features,
    )
    return BuiltFactors(snapshot=snapshot, vector=vector)


def _truncate_as_of(series: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    if series.empty or "date" not in series.columns:
        return series

    frame = series.copy()
    dates = pd.to_datetime(frame["date"], errors="coerce")
    anchor = pd.to_datetime(as_of_date, errors="coerce")
    if pd.isna(anchor):
        return frame
    return frame.loc[dates <= anchor].copy()


def vector_to_array(vector: dict[str, float]) -> list[float]:
    return [float(vector.get(column, 0.0) or 0.0) for column in FACTOR_COLUMNS]


def _return_over(close: pd.Series, periods: int) -> float | None:
    if len(close) <= periods:
        return None
    base = float(close.iloc[-periods - 1])
    if abs(base) < 1e-9:
        return None
    return _finite_float((float(close.iloc[-1]) - base) / base * 100.0)


def _tail_mean_ratio(values: pd.Series, *, recent: int, previous: int) -> float | None:
    if len(values) < recent + previous:
        return None
    recent_mean = float(values.tail(recent).mean())
    previous_mean = float(values.iloc[-recent - previous : -recent].mean())
    if abs(previous_mean) < 1e-9:
        return None
    return _finite_float(recent_mean / previous_mean)


def _zscore_latest(values: np.ndarray) -> float | None:
    if values.size < 2:
        return None
    std = float(values.std())
    if std <= 1e-9 or not np.isfinite(std):
        return 0.0
    return _finite_float((float(values[-1]) - float(values.mean())) / std)


def _last_numeric(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns or frame.empty:
        return 0.0
    return _finite_float(frame[column].fillna(0.0).astype(float).iloc[-1])


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.zeros(len(frame)), index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0).astype(float)


def _amount_series(frame: pd.DataFrame, close: pd.Series, volume: pd.Series) -> pd.Series:
    if "amount" in frame.columns:
        return _numeric_series(frame, "amount")
    return (volume * close).fillna(0.0).astype(float)


def _atr_pct(high: pd.Series, low: pd.Series, close: pd.Series, *, window: int) -> float:
    if len(close) < 2:
        return 0.0
    prev_close = close.shift(1).fillna(close)
    true_range = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = float(true_range.tail(window).mean()) if len(true_range) else 0.0
    latest_close = max(float(close.iloc[-1]), 1e-9)
    return _finite_float(atr / latest_close * 100.0)


def _obv_trend(close: pd.Series, volume: pd.Series, *, window: int) -> float:
    if len(close) <= window:
        return 0.0
    direction = np.sign(close.diff().fillna(0.0).to_numpy(dtype=float))
    obv = pd.Series(np.cumsum(direction * volume.fillna(0.0).to_numpy(dtype=float)), index=close.index)
    recent = float(obv.iloc[-1] - obv.iloc[-window])
    scale = float(volume.tail(window).abs().sum())
    if scale <= 1e-9:
        return 0.0
    return _finite_float(recent / scale)


def _mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, *, window: int) -> float:
    if len(close) <= 1:
        return 50.0
    typical = (high + low + close) / 3.0
    money_flow = typical * volume.fillna(0.0)
    direction = typical.diff().fillna(0.0)
    positive = money_flow.where(direction > 0.0, 0.0).tail(window).sum()
    negative = money_flow.where(direction < 0.0, 0.0).abs().tail(window).sum()
    if float(negative) <= 1e-9:
        return 100.0 if float(positive) > 0.0 else 50.0
    ratio = float(positive) / float(negative)
    return _finite_float(100.0 - (100.0 / (1.0 + ratio)))


def _intraday_reversal_score(
    *,
    latest_ret: float,
    high: float,
    low: float,
    close: float,
    open_: float,
    volume_zscore: float,
    amount_zscore: float,
) -> float:
    high_low = max(high - low, 1e-9)
    upper_shadow = max(high - max(open_, close), 0.0) / high_low
    close_position = (close - low) / high_low
    hot_volume = max(volume_zscore, 0.0) + max(amount_zscore, 0.0)
    return _finite_float(max(latest_ret, 0.0) / 10.0 + upper_shadow + (1.0 - close_position) + hot_volume * 0.1)


def _limit_threshold_pct(symbol: str) -> float:
    normalized = str(symbol).strip().zfill(6)
    if normalized.startswith(("300", "301", "688")):
        return 20.0
    if normalized.startswith(("8", "4", "920")):
        return 30.0
    return 10.0


def _is_main_board_symbol(symbol: str) -> bool:
    normalized = str(symbol).strip().zfill(6)
    return normalized.startswith(("600", "601", "603", "605", "000", "001", "002", "003"))


def _consecutive_positive(returns: pd.Series) -> int:
    count = 0
    for value in reversed(returns.fillna(0.0).tolist()):
        if float(value) <= 0.0:
            break
        count += 1
    return count


def _consecutive_threshold(returns: pd.Series, *, threshold: float) -> int:
    count = 0
    for value in reversed(returns.fillna(0.0).tolist()):
        if float(value) < threshold:
            break
        count += 1
    return count


def _board_chain_stage(limit_streak: int) -> str:
    if limit_streak <= 0:
        return "none"
    if limit_streak == 1:
        return "first_board"
    if limit_streak == 2:
        return "second_board"
    return "multi_board"


def _is_short_candidate(
    *,
    amount_zscore: float,
    volume_zscore: float,
    turnover_zscore: float,
    range_pct: float,
    volatility_10d_pct: float,
    large_order_fire_score: float,
) -> bool:
    abnormal_flags = sum(
        [
            amount_zscore >= 1.0,
            volume_zscore >= 1.0,
            turnover_zscore >= 1.0,
            range_pct >= 3.0,
            volatility_10d_pct >= 2.5,
            large_order_fire_score >= 1.5,
        ]
    )
    return abnormal_flags >= 3


def _finite_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not np.isfinite(number):
        return 0.0
    return round(number, 6)

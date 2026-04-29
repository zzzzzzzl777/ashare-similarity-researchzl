from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class EncodedWindow:
    vector: np.ndarray
    components: dict[str, np.ndarray]
    component_slices: dict[str, tuple[int, int]]


def _safe_zscore(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    std = float(values.std())
    if std == 0.0 or not np.isfinite(std):
        return np.zeros_like(values, dtype=float)
    return (values - float(values.mean())) / std


def _safe_ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    denominator = np.where(np.abs(denominator) < 1e-9, 1.0, denominator)
    return numerator / denominator


def encode_window(window: pd.DataFrame) -> EncodedWindow:
    close = window["close"].to_numpy(dtype=float)
    open_ = window["open"].to_numpy(dtype=float)
    high = window["high"].to_numpy(dtype=float)
    low = window["low"].to_numpy(dtype=float)
    volume = window["volume"].fillna(0.0).to_numpy(dtype=float)
    turnover = window.get("turnover", pd.Series(np.zeros(len(window)))).fillna(0.0).to_numpy(dtype=float)
    amplitude = window.get("amplitude", pd.Series(np.zeros(len(window)))).fillna(0.0).to_numpy(dtype=float)

    base_close = close[0] if close.size else 1.0
    price_path = np.concatenate(
        [
            _safe_ratio(close, np.full_like(close, base_close)) - 1.0,
            np.concatenate([[0.0], np.diff(close) / np.where(np.abs(close[:-1]) < 1e-9, 1.0, close[:-1])]),
        ]
    )

    spread = np.where(np.abs(high - low) < 1e-9, 1.0, high - low)
    candle_geometry = np.concatenate(
        [
            _safe_ratio(close - open_, spread),
            _safe_ratio(high - np.maximum(open_, close), spread),
            _safe_ratio(np.minimum(open_, close) - low, spread),
        ]
    )

    volume_liquidity = np.concatenate(
        [
            _safe_zscore(np.log1p(np.maximum(volume, 0.0))),
            _safe_zscore(turnover),
            _safe_zscore(amplitude),
        ]
    )

    env_columns = [
        "market_return_mean",
        "market_trend_5",
        "market_volatility_5",
        "industry_return_mean",
        "industry_return_trend_5",
    ]
    env_parts = []
    for column in env_columns:
        env_parts.append(window.get(column, pd.Series(np.zeros(len(window)))).fillna(0.0).to_numpy(dtype=float))
    environment = np.concatenate(env_parts)

    components = {
        "price_path": price_path.astype(np.float32),
        "candle_geometry": candle_geometry.astype(np.float32),
        "volume_liquidity": volume_liquidity.astype(np.float32),
        "environment": environment.astype(np.float32),
    }

    vector_parts: list[np.ndarray] = []
    slices: dict[str, tuple[int, int]] = {}
    cursor = 0
    for name, part in components.items():
        vector_parts.append(part)
        slices[name] = (cursor, cursor + len(part))
        cursor += len(part)
    vector = np.concatenate(vector_parts).astype(np.float32)
    return EncodedWindow(vector=vector, components=components, component_slices=slices)

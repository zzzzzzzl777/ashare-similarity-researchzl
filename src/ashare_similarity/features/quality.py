from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ashare_similarity.config import AppConfig


@dataclass(slots=True)
class QualityResult:
    is_valid: bool
    reasons: list[str]


class QualityFilter:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def evaluate(self, window: pd.DataFrame, listing_days: int | None = None) -> QualityResult:
        del listing_days
        reasons: list[str] = []
        required = ["open", "high", "low", "close", "volume"]
        non_null_ratio = float(window[required].notna().mean().mean()) if not window.empty else 0.0
        if non_null_ratio < self.config.quality.min_non_null_ratio:
            reasons.append("window contains too many missing values")

        if not window.empty:
            zero_volume_ratio = float((window["volume"].fillna(0) <= 0).mean())
            if zero_volume_ratio > self.config.quality.max_zero_volume_ratio:
                reasons.append("window contains too many zero-volume bars")

            price_columns = window[["open", "high", "low", "close"]].to_numpy(dtype=float)
            if not np.isfinite(price_columns).all():
                reasons.append("window contains non-finite price values")

            if (window["high"] < window[["open", "close", "low"]].max(axis=1)).any():
                reasons.append("high price geometry is invalid")

            if (window["low"] > window[["open", "close", "high"]].min(axis=1)).any():
                reasons.append("low price geometry is invalid")

        return QualityResult(is_valid=not reasons, reasons=reasons)

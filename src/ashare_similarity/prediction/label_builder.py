from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class ForwardLabel:
    horizon: int
    return_pct: float | None
    max_favorable_excursion_pct: float | None
    max_drawdown_pct: float | None
    scenario: str | None


def build_forward_labels(
    history: pd.DataFrame,
    *,
    end_date: str,
    horizons: list[int],
    max_label_date: str | None = None,
) -> dict[int, ForwardLabel]:
    labels: dict[int, ForwardLabel] = {}
    if history.empty:
        return {
            horizon: ForwardLabel(horizon, None, None, None, None)
            for horizon in horizons
        }

    frame = history.copy()
    time_col = "date" if "date" in frame.columns else "timestamp"
    frame[time_col] = pd.to_datetime(frame[time_col])
    frame = frame.sort_values(time_col).reset_index(drop=True)
    end_ts = pd.Timestamp(end_date)
    max_label_ts = pd.Timestamp(max_label_date) if max_label_date else None
    matches = frame.index[frame[time_col] == end_ts]
    if len(matches) == 0:
        matches = frame.index[frame[time_col].dt.normalize() == end_ts.normalize()]
    if len(matches) == 0:
        return {
            horizon: ForwardLabel(horizon, None, None, None, None)
            for horizon in horizons
        }

    entry_index = int(matches[-1])
    entry_close = float(frame.iloc[entry_index]["close"])
    for horizon in horizons:
        future = frame.iloc[entry_index + 1 : entry_index + horizon + 1]
        if abs(entry_close) < 1e-9 or len(future) < horizon:
            labels[horizon] = ForwardLabel(horizon, None, None, None, None)
            continue
        if max_label_ts is not None and pd.Timestamp(future.iloc[-1][time_col]) > max_label_ts:
            labels[horizon] = ForwardLabel(horizon, None, None, None, None)
            continue
        return_pct = (float(future.iloc[-1]["close"]) - entry_close) / entry_close * 100.0
        mfe = (float(future["high"].max()) - entry_close) / entry_close * 100.0
        mdd = (float(future["low"].min()) - entry_close) / entry_close * 100.0
        labels[horizon] = ForwardLabel(
            horizon=horizon,
            return_pct=_round(return_pct),
            max_favorable_excursion_pct=_round(mfe),
            max_drawdown_pct=_round(mdd),
            scenario=_scenario(future, entry_close),
        )
    return labels


def _scenario(future: pd.DataFrame, entry_close: float) -> str:
    last = future.iloc[-1]
    close_return = (float(last["close"]) - entry_close) / entry_close * 100.0 if abs(entry_close) > 1e-9 else 0.0
    if close_return >= 3.0:
        return "strong_up"
    if close_return <= -3.0:
        return "strong_down"
    spread = max(float(last["high"]) - float(last["low"]), 1e-9)
    upper = (float(last["high"]) - max(float(last["open"]), float(last["close"]))) / spread
    lower = (min(float(last["open"]), float(last["close"])) - float(last["low"])) / spread
    if upper >= 0.45:
        return "upper_shadow_pressure"
    if lower >= 0.45:
        return "lower_shadow_support"
    if close_return > 0:
        return "mild_up"
    if close_return < 0:
        return "mild_down"
    return "flat"


def _round(value: float | None) -> float | None:
    if value is None or not np.isfinite(value):
        return None
    return round(float(value), 4)

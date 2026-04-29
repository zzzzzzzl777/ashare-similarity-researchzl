from __future__ import annotations

from typing import Iterator

import pandas as pd

from ashare_similarity.data.base import Frequency


def time_column_for_frequency(frequency: Frequency) -> str:
    return "date" if frequency == "daily" else "timestamp"


def iter_rolling_windows(
    bars: pd.DataFrame,
    frequency: Frequency,
    window_size: int,
) -> Iterator[tuple[int, int, pd.DataFrame]]:
    if bars.empty or len(bars) < window_size:
        return
    time_col = time_column_for_frequency(frequency)
    sorted_bars = bars.sort_values(time_col).reset_index(drop=True)
    for end_idx in range(window_size - 1, len(sorted_bars)):
        start_idx = end_idx - window_size + 1
        window = sorted_bars.iloc[start_idx : end_idx + 1].copy().reset_index(drop=True)
        yield start_idx, end_idx, window

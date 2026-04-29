from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ashare_similarity.data.base import Frequency


@dataclass(slots=True)
class FeatureFrame:
    frequency: Frequency
    window_size: int
    matrix: np.ndarray
    metadata: pd.DataFrame
    component_slices: dict[str, tuple[int, int]]
    built_from: dict[str, Any] = field(default_factory=dict)

    @property
    def metadata_frame(self) -> pd.DataFrame:
        return self.metadata


@dataclass(slots=True)
class QueryWindow:
    frequency: Frequency
    window_size: int
    symbol: str
    end_label: str
    matrix: np.ndarray
    metadata: dict[str, Any]
    series: pd.DataFrame
    component_slices: dict[str, tuple[int, int]]
    warnings: list[str] = field(default_factory=list)

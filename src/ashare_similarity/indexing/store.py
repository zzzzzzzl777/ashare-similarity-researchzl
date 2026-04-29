from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ashare_similarity.data.base import Frequency
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.features.models import FeatureFrame


@dataclass(slots=True)
class PersistedFeatureSet:
    frequency: Frequency
    window_size: int
    matrix: np.ndarray
    metadata: Any
    manifest: dict[str, Any]
    paths: dict[str, Path]

    @property
    def row_count(self) -> int:
        return int(self.matrix.shape[0]) if self.matrix.ndim == 2 else 0


class FeatureStore:
    def __init__(self, store: LocalDataStore) -> None:
        self.store = store

    def save(self, feature_frame: FeatureFrame) -> PersistedFeatureSet:
        matrix = np.asarray(feature_frame.matrix, dtype=np.float32)
        if matrix.ndim != 2:
            raise ValueError("FeatureFrame.matrix must be a 2D numpy array.")

        metadata = feature_frame.metadata.copy()
        if not metadata.empty:
            metadata = metadata.reset_index(drop=True)
        if len(metadata.index) != matrix.shape[0]:
            raise ValueError(
                "FeatureFrame.metadata row count must match FeatureFrame.matrix row count."
            )

        if matrix.shape[0] and "window_id" not in metadata.columns:
            metadata["window_id"] = [
                self._build_window_id(row, row_index)
                for row_index, row in metadata.iterrows()
            ]

        manifest = {
            "frequency": feature_frame.frequency,
            "window_size": feature_frame.window_size,
            "vector_dim": int(matrix.shape[1]) if matrix.size else 0,
            "row_count": int(matrix.shape[0]),
            "symbol_count": int(metadata["symbol"].nunique()) if "symbol" in metadata.columns and not metadata.empty else 0,
            "component_slices": feature_frame.component_slices,
            "built_from": feature_frame.built_from,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "metadata_columns": metadata.columns.tolist(),
        }
        output_paths = self.store.save_feature_artifacts(
            frequency=feature_frame.frequency,
            window_size=feature_frame.window_size,
            matrix=matrix,
            metadata=metadata,
            manifest=manifest,
        )
        paths = {name: Path(path) for name, path in output_paths.items()}
        return PersistedFeatureSet(
            frequency=feature_frame.frequency,
            window_size=feature_frame.window_size,
            matrix=matrix,
            metadata=metadata,
            manifest=manifest,
            paths=paths,
        )

    def load(self, frequency: Frequency, window_size: int) -> PersistedFeatureSet:
        matrix, metadata, manifest = self.store.load_feature_artifacts(frequency, window_size)
        directory = self.store.feature_dir(frequency, window_size)
        paths = {
            "matrix": directory / "matrix.npy",
            "metadata": directory / "metadata.parquet",
            "manifest": directory / "manifest.json",
        }
        return PersistedFeatureSet(
            frequency=frequency,
            window_size=window_size,
            matrix=np.asarray(matrix, dtype=np.float32),
            metadata=metadata.reset_index(drop=True),
            manifest=manifest,
            paths=paths,
        )

    def _build_window_id(self, row: pd.Series, row_index: int) -> str:
        symbol = str(row.get("symbol", "unknown"))
        frequency = str(row.get("frequency", "unknown"))
        start_date = str(row.get("start_date", "na"))
        end_date = str(row.get("end_date", "na"))
        return "|".join([symbol, frequency, start_date, end_date, str(row_index)])

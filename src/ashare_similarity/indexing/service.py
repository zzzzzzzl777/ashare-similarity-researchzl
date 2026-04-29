from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from ashare_similarity.config import AppConfig
from ashare_similarity.data.base import Frequency
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.features.models import FeatureFrame
from ashare_similarity.indexing.compact_builder import COMPACT_STORAGE_FORMAT
from ashare_similarity.indexing.backend import AnnBackend, SearchIndex
from ashare_similarity.indexing.store import FeatureStore, PersistedFeatureSet
from ashare_similarity.schemas import BuildSummary


class CompactMetadataAccessor:
    """Random-access reader for compact metadata without loading all rows."""

    def __init__(
        self,
        path: Path,
        *,
        row_count: int,
        symbol_count: int,
        columns: list[str] | None = None,
    ) -> None:
        self.path = path
        self._row_count = int(row_count)
        self._symbol_count = int(symbol_count)
        self._columns = list(columns or [])
        self._row_group_offsets: list[int] | None = None
        self._row_group_lengths: list[int] | None = None
        self._parquet_file: pq.ParquetFile | None = None

    @property
    def index(self) -> range:
        return range(self._row_count)

    @property
    def columns(self) -> pd.Index:
        return pd.Index(self._columns)

    def __len__(self) -> int:
        return self._row_count

    def symbol_nunique(self) -> int:
        return self._symbol_count

    def row_at(self, row_index: int) -> pd.Series:
        row_index = int(row_index)
        if row_index < 0 or row_index >= self._row_count:
            raise IndexError(row_index)
        offsets, lengths = self._layout()
        group_index = bisect_right(offsets, row_index) - 1
        if group_index < 0:
            raise IndexError(row_index)
        local_index = row_index - offsets[group_index]
        if local_index >= lengths[group_index]:
            raise IndexError(row_index)

        parquet = self._parquet()
        table = parquet.read_row_group(group_index).slice(local_index, 1)
        frame = table.to_pandas()
        if frame.empty:
            raise IndexError(row_index)
        return frame.iloc[0].copy()

    def _layout(self) -> tuple[list[int], list[int]]:
        if self._row_group_offsets is not None and self._row_group_lengths is not None:
            return self._row_group_offsets, self._row_group_lengths

        parquet = self._parquet()
        offsets: list[int] = []
        lengths: list[int] = []
        cursor = 0
        for group_index in range(parquet.num_row_groups):
            row_count = int(parquet.metadata.row_group(group_index).num_rows)
            offsets.append(cursor)
            lengths.append(row_count)
            cursor += row_count

        self._row_group_offsets = offsets
        self._row_group_lengths = lengths
        if self._row_count and cursor != self._row_count:
            raise RuntimeError(
                f"Compact metadata row_count mismatch in {self.path}: manifest={self._row_count}, parquet={cursor}."
            )
        return offsets, lengths

    def _parquet(self) -> pq.ParquetFile:
        if self._parquet_file is None:
            self._parquet_file = pq.ParquetFile(self.path)
        return self._parquet_file


@dataclass(slots=True)
class SearchableIndex:
    frequency: Frequency
    window_size: int
    search_index: SearchIndex
    metadata: Any
    manifest: dict[str, Any]
    paths: dict[str, Path]
    cache_token: tuple[tuple[str, int, int], ...] | None = None

    @property
    def backend_name(self) -> str:
        return self.search_index.backend_name

    @property
    def matrix(self):
        return self.search_index.matrix

    @property
    def row_count(self) -> int:
        row_count = int(self.manifest.get("row_count") or 0)
        if row_count:
            return row_count
        return int(len(self.metadata.index))

    @property
    def symbol_count(self) -> int:
        symbol_count = int(self.manifest.get("symbol_count") or 0)
        if symbol_count:
            return symbol_count
        if hasattr(self.metadata, "symbol_nunique"):
            return int(self.metadata.symbol_nunique())
        if "symbol" in self.metadata.columns:
            return int(self.metadata["symbol"].nunique())
        return 0

    def metadata_row(self, row_index: int) -> pd.Series:
        if hasattr(self.metadata, "row_at"):
            return self.metadata.row_at(row_index)
        return self.metadata.iloc[int(row_index)].copy()

    def search(self, query, top_k: int):
        if self.manifest.get("storage_format") == COMPACT_STORAGE_FORMAT:
            from ashare_similarity.indexing.compact_builder import project_recall_vector

            vector = query[0] if getattr(query, "ndim", 1) == 2 else query
            query = project_recall_vector(vector, self.manifest.get("component_slices") or {}).reshape(1, -1)
            expected_dim = int(self.manifest.get("recall_vector_dim") or 0)
            if expected_dim and int(query.shape[1]) != expected_dim:
                raise ValueError(
                    f"Compact query projection dimension mismatch: got {query.shape[1]}, expected {expected_dim}."
                )
        return self.search_index.search(query=query, top_k=top_k)


class IndexService:
    def __init__(self, config: AppConfig, store: LocalDataStore) -> None:
        self.config = config
        self.store = store
        self.feature_store = FeatureStore(store)
        self.ann_backend = AnnBackend(prefer_faiss=True)
        self._cache: dict[tuple[Frequency, int], SearchableIndex] = {}

    def _artifact_paths(self, frequency: Frequency, window_size: int) -> dict[str, Path]:
        directory = self.store.feature_dir(frequency, window_size)
        return {
            "matrix": directory / "matrix.npy",
            "metadata": directory / "metadata.parquet",
            "manifest": directory / "manifest.json",
            "ann_matrix": directory / "ann_matrix.npy",
            "ann_search_matrix": directory / "ann_search_matrix.npy",
            "backend": directory / "backend.json",
            "faiss": directory / "ann_index.faiss",
        }

    def _cache_token(self, frequency: Frequency, window_size: int) -> tuple[tuple[str, int, int], ...] | None:
        paths = self._artifact_paths(frequency, window_size)
        required = ("matrix", "metadata", "manifest", "ann_matrix", "backend")
        if paths["manifest"].exists():
            try:
                import json

                manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
                if manifest.get("storage_format") == COMPACT_STORAGE_FORMAT:
                    required = ("metadata", "manifest", "ann_search_matrix", "backend")
            except Exception:
                return None
        if any(not paths[name].exists() for name in required):
            return None

        tokens: list[tuple[str, int, int]] = []
        for name, path in paths.items():
            if not path.exists():
                continue
            stat = path.stat()
            tokens.append((name, stat.st_mtime_ns, stat.st_size))
        return tuple(tokens)

    def _build_searchable(
        self,
        *,
        frequency: Frequency,
        window_size: int,
        search_index: SearchIndex,
        stored: PersistedFeatureSet,
        manifest: dict[str, Any] | None = None,
    ) -> SearchableIndex:
        directory = self.store.feature_dir(frequency, window_size)
        index_manifest = dict(manifest or stored.manifest)
        index_manifest.setdefault("backend", search_index.backend_name)
        index_manifest.setdefault(
            "output_paths",
            {
                **{key: str(path) for key, path in stored.paths.items()},
                "ann_matrix": str(directory / "ann_matrix.npy"),
                "ann_search_matrix": str(directory / "ann_search_matrix.npy"),
                "backend": str(directory / "backend.json"),
            },
        )
        return SearchableIndex(
            frequency=frequency,
            window_size=window_size,
            search_index=search_index,
            metadata=stored.metadata,
            manifest=index_manifest,
            paths={
                **stored.paths,
                "ann_matrix": directory / "ann_matrix.npy",
                "ann_search_matrix": directory / "ann_search_matrix.npy",
                "backend": directory / "backend.json",
            },
            cache_token=self._cache_token(frequency, window_size),
        )

    def build(self, feature_frame: FeatureFrame, frequency: Frequency, window_size: int) -> BuildSummary:
        stored = self.feature_store.save(feature_frame)
        search_index = self.ann_backend.build(stored.matrix)
        directory = self.store.feature_dir(frequency, window_size)
        self.ann_backend.save(search_index, directory)

        output_paths = {key: str(path) for key, path in stored.paths.items()}
        output_paths["ann_matrix"] = str(directory / "ann_matrix.npy")
        output_paths["ann_search_matrix"] = str(directory / "ann_search_matrix.npy")
        output_paths["backend"] = str(directory / "backend.json")
        if search_index.backend_name.startswith("faiss"):
            output_paths["faiss"] = str(directory / "ann_index.faiss")

        build_metadata = {
            **stored.manifest,
            "output_paths": output_paths,
            "backend": search_index.backend_name,
        }
        if hasattr(self.store, "record_build"):
            self.store.record_build(
                frequency=frequency,
                window_size=window_size,
                backend=search_index.backend_name,
                rows_count=stored.row_count,
                metadata_json=build_metadata,
            )

        searchable = self._build_searchable(
            frequency=frequency,
            window_size=window_size,
            search_index=search_index,
            stored=PersistedFeatureSet(
                frequency=stored.frequency,
                window_size=stored.window_size,
                matrix=stored.matrix,
                metadata=stored.metadata,
                manifest=stored.manifest,
                paths={key: Path(path) for key, path in output_paths.items()},
            ),
            manifest=build_metadata,
        )
        self._cache[(frequency, window_size)] = searchable

        return BuildSummary(
            frequency=frequency,
            window_size=window_size,
            symbols_processed=int(stored.metadata["symbol"].nunique()) if "symbol" in stored.metadata.columns and not stored.metadata.empty else 0,
            windows_created=stored.row_count,
            index_backend=search_index.backend_name,
            output_paths=output_paths,
        )

    def build_compact(
        self,
        *,
        feature_service,
        frequency: Frequency,
        window_size: int,
        symbols: list[str],
    ) -> BuildSummary:
        from ashare_similarity.indexing.compact_builder import build_compact_index

        summary = build_compact_index(
            config=self.config,
            store=self.store,
            feature_service=feature_service,
            frequency=frequency,
            window_size=window_size,
            symbols=symbols,
        )
        self._cache.pop((frequency, window_size), None)
        return summary

    def load(self, frequency: Frequency, window_size: int) -> SearchableIndex:
        cache_key = (frequency, window_size)
        cached = self._cache.get(cache_key)
        current_token = self._cache_token(frequency, window_size)
        if cached is not None and cached.cache_token == current_token:
            return cached
        self._cache.pop(cache_key, None)

        directory = self.store.feature_dir(frequency, window_size)
        manifest_path = directory / "manifest.json"
        manifest = None
        if manifest_path.exists():
            import json

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest and manifest.get("storage_format") == COMPACT_STORAGE_FORMAT:
            search_index = self.ann_backend.load(directory)
            expected_rows = int(manifest.get("row_count") or 0)
            expected_dim = int(manifest.get("recall_vector_dim") or 0)
            actual_rows = int(search_index.matrix.shape[0])
            actual_dim = int(search_index.mean.size)
            if expected_rows and actual_rows != expected_rows:
                raise RuntimeError(
                    f"Compact index in {directory} has row_count={actual_rows}, expected {expected_rows}."
                )
            if expected_dim and actual_dim != expected_dim:
                raise RuntimeError(
                    f"Compact index in {directory} has recall_vector_dim={actual_dim}, expected {expected_dim}."
                )
            metadata = CompactMetadataAccessor(
                directory / "metadata.parquet",
                row_count=expected_rows or actual_rows,
                symbol_count=int(manifest.get("symbol_count") or 0),
                columns=list(manifest.get("metadata_columns") or []),
            )
            if int(len(metadata)) != actual_rows:
                raise RuntimeError(
                    f"Compact index in {directory} has metadata rows={len(metadata)}, matrix rows={actual_rows}."
                )
            stored = PersistedFeatureSet(
                frequency=frequency,
                window_size=window_size,
                matrix=search_index.matrix,
                metadata=metadata,
                manifest=manifest,
                paths={
                    "metadata": directory / "metadata.parquet",
                    "manifest": directory / "manifest.json",
                },
            )
            searchable = self._build_searchable(
                frequency=frequency,
                window_size=window_size,
                search_index=search_index,
                manifest=manifest,
                stored=stored,
            )
            self._cache[cache_key] = searchable
            return searchable

        stored = self.feature_store.load(frequency, window_size)
        search_index = self.ann_backend.load(directory)
        if search_index.matrix.shape != stored.matrix.shape:
            raise ValueError(
                f"{frequency} 窗口 {window_size} 的索引工件与特征矩阵不一致，"
                "请先重建该窗口索引。"
            )

        manifest = dict(stored.manifest)
        searchable = self._build_searchable(
            frequency=frequency,
            window_size=window_size,
            search_index=search_index,
            manifest=manifest,
            stored=stored,
        )
        self._cache[cache_key] = searchable
        return searchable

    def get_cached(self, frequency: Frequency, window_size: int) -> SearchableIndex | None:
        cache_key = (frequency, window_size)
        cached = self._cache.get(cache_key)
        if cached is None:
            return None
        current_token = self._cache_token(frequency, window_size)
        if cached.cache_token != current_token:
            self._cache.pop(cache_key, None)
            return None
        return cached

    def exists(self, frequency: Frequency, window_size: int) -> bool:
        return self._cache_token(frequency, window_size) is not None

    def feature_directory(self, frequency: Frequency, window_size: int) -> Path:
        return self.store.feature_dir(frequency, window_size)

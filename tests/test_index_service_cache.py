from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ashare_similarity.features.models import FeatureFrame
from ashare_similarity.indexing.service import IndexService
from ashare_similarity.data.storage import LocalDataStore


class _StubSearchIndex:
    def __init__(self, matrix: np.ndarray, backend_name: str = "synthetic-backend") -> None:
        self.matrix = matrix
        self.backend_name = backend_name

    def search(self, query, top_k: int):
        del query
        indices = np.arange(min(top_k, len(self.matrix)), dtype=np.int64)
        return np.zeros(indices.shape, dtype=np.float32), indices


class _StubAnnBackend:
    def __init__(self) -> None:
        self.load_calls = 0

    def build(self, matrix: np.ndarray) -> _StubSearchIndex:
        return _StubSearchIndex(np.asarray(matrix, dtype=np.float32))

    def save(self, search_index: _StubSearchIndex, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "ann_matrix.npy", search_index.matrix)
        np.save(directory / "ann_search_matrix.npy", search_index.matrix)
        (directory / "backend.json").write_text(
            json.dumps({"backend": search_index.backend_name}, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self, directory: Path) -> _StubSearchIndex:
        self.load_calls += 1
        matrix = np.load(directory / "ann_matrix.npy")
        return _StubSearchIndex(matrix)


def test_index_service_invalidates_cached_index_when_artifacts_change(app_config):
    store = LocalDataStore(app_config)
    service = IndexService(app_config, store)
    stub_backend = _StubAnnBackend()
    service.ann_backend = stub_backend

    feature_frame = FeatureFrame(
        frequency="daily",
        window_size=5,
        matrix=np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32),
        metadata=pd.DataFrame(
            [
                {"symbol": "000001", "start_date": "2026-04-01", "end_date": "2026-04-07", "frequency": "daily"},
                {"symbol": "000002", "start_date": "2026-04-08", "end_date": "2026-04-14", "frequency": "daily"},
            ]
        ),
        component_slices={"price_path": (0, 2)},
        built_from={"latest_data_at": "2026-04-14T15:00:00"},
    )

    service.build(feature_frame, "daily", 5)

    first = service.load("daily", 5)
    assert stub_backend.load_calls == 0, "Freshly built indexes should come from the in-process cache."

    manifest_path = store.feature_dir("daily", 5) / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["test_marker"] = "invalidate-cache"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    second = service.load("daily", 5)
    third = service.load("daily", 5)

    assert first is not second, "Artifact changes on disk should invalidate the in-process index cache."
    assert second is third, "Once reloaded, the refreshed index should be cached again."
    assert stub_backend.load_calls == 1


def test_index_service_exists_requires_full_loadable_artifact_set(app_config):
    store = LocalDataStore(app_config)
    service = IndexService(app_config, store)
    service.ann_backend = _StubAnnBackend()

    feature_frame = FeatureFrame(
        frequency="daily",
        window_size=5,
        matrix=np.asarray([[0.1, 0.2]], dtype=np.float32),
        metadata=pd.DataFrame(
            [{"symbol": "000001", "start_date": "2026-04-01", "end_date": "2026-04-07", "frequency": "daily"}]
        ),
        component_slices={"price_path": (0, 2)},
        built_from={"latest_data_at": "2026-04-14T15:00:00"},
    )

    service.build(feature_frame, "daily", 5)
    assert service.exists("daily", 5) is True

    matrix_path = store.feature_dir("daily", 5) / "matrix.npy"
    matrix_path.unlink()

    assert service.exists("daily", 5) is False, "Readiness checks should fail when core feature artifacts are missing."


def test_index_service_load_refuses_to_mutate_inconsistent_artifacts_on_read(app_config):
    store = LocalDataStore(app_config)
    service = IndexService(app_config, store)
    stub_backend = _StubAnnBackend()
    service.ann_backend = stub_backend

    feature_frame = FeatureFrame(
        frequency="daily",
        window_size=5,
        matrix=np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32),
        metadata=pd.DataFrame(
            [
                {"symbol": "000001", "start_date": "2026-04-01", "end_date": "2026-04-07", "frequency": "daily"},
                {"symbol": "000002", "start_date": "2026-04-08", "end_date": "2026-04-14", "frequency": "daily"},
            ]
        ),
        component_slices={"price_path": (0, 2)},
        built_from={"latest_data_at": "2026-04-14T15:00:00"},
    )

    service.build(feature_frame, "daily", 5)

    ann_matrix_path = store.feature_dir("daily", 5) / "ann_matrix.npy"
    np.save(ann_matrix_path, np.asarray([[0.9, 0.8, 0.7]], dtype=np.float32))

    with pytest.raises(ValueError, match="请先重建该窗口索引"):
        service.load("daily", 5)

    reloaded = np.load(ann_matrix_path)
    assert reloaded.shape == (1, 3), "Read paths must not silently rewrite ANN artifacts when they detect inconsistencies."

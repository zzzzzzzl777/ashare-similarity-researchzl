from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ashare_similarity.indexing import backend as ann_backend


def _sample_matrix(offset: float = 0.0) -> np.ndarray:
    return np.asarray(
        [
            [0.0 + offset, 1.0 + offset, 2.0 + offset],
            [3.0 + offset, 4.0 + offset, 5.0 + offset],
            [6.0 + offset, 7.0 + offset, 8.0 + offset],
        ],
        dtype=np.float32,
    )


def _search_index(
    matrix: np.ndarray,
    *,
    backend_name: str = "sklearn-nearest",
    artifact_backend: str | None = None,
    index: object | None = None,
) -> ann_backend.SearchIndex:
    search_matrix, mean, scale = ann_backend._standardize_matrix(matrix)
    return ann_backend.SearchIndex(
        backend_name=backend_name,
        matrix=matrix,
        search_matrix=search_matrix,
        mean=mean,
        scale=scale,
        index=index,
        artifact_backend=artifact_backend or backend_name,
        device="cpu",
        device_name=None,
        backend_details={},
    )


def _hidden_artifacts(directory: Path) -> list[Path]:
    return sorted(
        [
            item
            for item in directory.iterdir()
            if item.is_file() and item.name.startswith(".") and (item.name.endswith(".tmp") or item.name.endswith(".bak"))
        ],
        key=lambda item: item.name,
    )


def test_ann_backend_save_rolls_back_all_core_artifacts_when_backend_replace_fails(tmp_path, monkeypatch):
    backend = ann_backend.AnnBackend(prefer_faiss=False, prefer_torch_cuda=False)
    directory = tmp_path / "index"
    directory.mkdir(parents=True, exist_ok=True)

    initial_index = _search_index(_sample_matrix())
    backend.save(initial_index, directory)

    ann_matrix_path = directory / "ann_matrix.npy"
    ann_search_matrix_path = directory / "ann_search_matrix.npy"
    backend_path = directory / "backend.json"
    original_files = {
        ann_matrix_path: ann_matrix_path.read_bytes(),
        ann_search_matrix_path: ann_search_matrix_path.read_bytes(),
        backend_path: backend_path.read_bytes(),
    }

    updated_index = _search_index(_sample_matrix(offset=100.0))
    original_replace = backend._replace_file
    failure_state = {"raised": False}

    def fail_backend_commit(source: Path, destination: Path) -> None:
        if destination == backend_path and not failure_state["raised"]:
            failure_state["raised"] = True
            raise OSError("simulated backend replace failure")
        original_replace(source, destination)

    monkeypatch.setattr(backend, "_replace_file", fail_backend_commit)

    with pytest.raises(OSError, match="simulated backend replace failure"):
        backend.save(updated_index, directory)

    for path, original_bytes in original_files.items():
        assert path.read_bytes() == original_bytes
    assert _hidden_artifacts(directory) == []


def test_ann_backend_save_rolls_back_faiss_artifact_when_faiss_replace_fails(tmp_path, monkeypatch):
    backend = ann_backend.AnnBackend(prefer_faiss=False, prefer_torch_cuda=False)
    directory = tmp_path / "index"
    directory.mkdir(parents=True, exist_ok=True)

    fake_faiss = SimpleNamespace(
        write_index=lambda index, path: Path(path).write_bytes(index["blob"]),
    )
    monkeypatch.setattr(ann_backend, "faiss", fake_faiss)

    faiss_path = directory / "ann_index.faiss"
    initial_index = _search_index(
        _sample_matrix(),
        backend_name="faiss-flat",
        artifact_backend="faiss-flat",
        index={"blob": b"faiss-initial"},
    )
    backend.save(initial_index, directory)

    original_files = {
        directory / "ann_matrix.npy": (directory / "ann_matrix.npy").read_bytes(),
        directory / "ann_search_matrix.npy": (directory / "ann_search_matrix.npy").read_bytes(),
        directory / "backend.json": (directory / "backend.json").read_bytes(),
        faiss_path: faiss_path.read_bytes(),
    }

    updated_index = _search_index(
        _sample_matrix(offset=50.0),
        backend_name="faiss-flat",
        artifact_backend="faiss-flat",
        index={"blob": b"faiss-updated"},
    )
    original_replace = backend._replace_file
    failure_state = {"raised": False}

    def fail_faiss_commit(source: Path, destination: Path) -> None:
        if destination == faiss_path and not failure_state["raised"]:
            failure_state["raised"] = True
            raise OSError("simulated faiss replace failure")
        original_replace(source, destination)

    monkeypatch.setattr(backend, "_replace_file", fail_faiss_commit)

    with pytest.raises(OSError, match="simulated faiss replace failure"):
        backend.save(updated_index, directory)

    for path, original_bytes in original_files.items():
        assert path.read_bytes() == original_bytes
    assert _hidden_artifacts(directory) == []

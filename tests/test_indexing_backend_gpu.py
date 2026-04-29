from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from ashare_similarity.indexing import backend as ann_backend


def _sample_matrix() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [5.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )


def _fake_torch_search_index(
    raw_matrix: np.ndarray,
    search_matrix: np.ndarray,
    mean: np.ndarray,
    scale: np.ndarray,
    *,
    artifact_backend: str,
    backend_details: dict | None = None,
) -> ann_backend.SearchIndex:
    details = dict(backend_details or {})
    details["runtime_backend_source"] = "torch-cuda"
    return ann_backend.SearchIndex(
        backend_name="torch-cuda-bruteforce",
        matrix=raw_matrix,
        search_matrix=search_matrix,
        mean=mean,
        scale=scale,
        index=ann_backend.TorchLinearIndex(
            matrix_tensor="synthetic-gpu-matrix",
            squared_norms="synthetic-gpu-norms",
            device="cuda:0",
            device_name="Synthetic GPU",
        ),
        artifact_backend=artifact_backend,
        device="cuda:0",
        device_name="Synthetic GPU",
        backend_details=details,
    )


def test_ann_backend_build_prefers_torch_cuda_backend(monkeypatch):
    backend = ann_backend.AnnBackend(prefer_faiss=False, prefer_torch_cuda=True)

    monkeypatch.setattr(
        ann_backend.AnnBackend,
        "_build_torch_index",
        lambda self, raw_matrix, search_matrix, mean, scale, *, artifact_backend, backend_details=None: _fake_torch_search_index(
            raw_matrix,
            search_matrix,
            mean,
            scale,
            artifact_backend=artifact_backend,
            backend_details=backend_details,
        ),
    )

    search_index = backend.build(_sample_matrix())

    assert search_index.backend_name == "torch-cuda-bruteforce"
    assert search_index.artifact_backend == "torch-cuda-bruteforce"
    assert search_index.device == "cuda:0"
    assert search_index.device_name == "Synthetic GPU"


def test_ann_backend_build_falls_back_to_cpu_backend_when_torch_cuda_is_unavailable(monkeypatch):
    backend = ann_backend.AnnBackend(prefer_faiss=False, prefer_torch_cuda=True)

    def _fail_torch_backend(self, *args, **kwargs):
        raise RuntimeError("CUDA is unavailable for synthetic test coverage.")

    monkeypatch.setattr(ann_backend.AnnBackend, "_build_torch_index", _fail_torch_backend)

    search_index = backend.build(_sample_matrix())

    assert search_index.backend_name == "sklearn-nearest"
    assert search_index.device == "cpu"
    assert search_index.backend_details["preferred_backend"] == "torch-cuda-bruteforce"
    assert "CUDA is unavailable" in search_index.backend_details["fallback_reason"]


def test_ann_backend_load_can_promote_legacy_cpu_artifact_to_torch_cuda_runtime(monkeypatch, tmp_path):
    backend = ann_backend.AnnBackend(prefer_faiss=False, prefer_torch_cuda=True)
    matrix = _sample_matrix()
    search_matrix, mean, scale = ann_backend._standardize_matrix(matrix)
    directory = tmp_path / "index"
    directory.mkdir(parents=True, exist_ok=True)

    np.save(directory / "ann_matrix.npy", matrix)
    np.save(directory / "ann_search_matrix.npy", search_matrix)
    (directory / "backend.json").write_text(
        json.dumps(
            {
                "backend": "sklearn-nearest",
                "mean": mean.tolist(),
                "scale": scale.tolist(),
                "backend_details": {"runtime_backend_source": "sklearn"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        ann_backend.AnnBackend,
        "_build_torch_index",
        lambda self, raw_matrix, search_matrix, mean, scale, *, artifact_backend, backend_details=None: _fake_torch_search_index(
            raw_matrix,
            search_matrix,
            mean,
            scale,
            artifact_backend=artifact_backend,
            backend_details=backend_details,
        ),
    )

    search_index = backend.load(directory)

    assert search_index.backend_name == "torch-cuda-bruteforce"
    assert search_index.artifact_backend == "sklearn-nearest"
    assert search_index.device == "cuda:0"
    assert search_index.backend_details["runtime_override_from_artifact"] == "sklearn-nearest"


def test_ann_backend_load_uses_cuda_chunked_runtime_for_compact_artifact(monkeypatch, tmp_path):
    backend = ann_backend.AnnBackend(prefer_faiss=False, prefer_torch_cuda=True)
    directory = tmp_path / "compact-index"
    directory.mkdir(parents=True, exist_ok=True)
    search_matrix = np.asarray([[0.0, 0.0], [1.0, 0.0], [5.0, 0.0]], dtype=np.float16)
    search_matrix.tofile(directory / "ann_search_matrix.npy")
    (directory / "backend.json").write_text(
        json.dumps(
            {
                "backend": ann_backend.COMPACT_STORAGE_FORMAT,
                "mean": [0.0, 0.0],
                "scale": [1.0, 1.0],
                "ann_search_matrix_encoding": "raw_float16",
                "ann_search_matrix_shape": [3, 2],
                "ann_search_matrix_dtype": "float16",
                "backend_details": {"storage_format": ann_backend.COMPACT_STORAGE_FORMAT},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ann_backend, "torch", SimpleNamespace())
    monkeypatch.setattr(
        ann_backend,
        "get_acceleration_environment",
        lambda: {
            "torch_cuda_available": True,
            "torch_device_name": "Synthetic GPU",
            "torch_version": "synthetic",
            "torch_cuda_device_count": 1,
        },
    )

    search_index = backend.load(directory)

    assert search_index.backend_name == "torch-cuda-chunked"
    assert search_index.artifact_backend == ann_backend.COMPACT_STORAGE_FORMAT
    assert search_index.device == "cuda:0"
    assert search_index.device_name == "Synthetic GPU"
    assert search_index.backend_details["runtime_backend_source"] == "torch-cuda-chunked"


def test_torch_cuda_chunked_runtime_search_uses_chunked_helper(monkeypatch, tmp_path):
    matrix_path = tmp_path / "ann_search_matrix.npy"
    np.asarray([[0.0, 0.0], [1.0, 0.0], [5.0, 0.0]], dtype=np.float16).tofile(matrix_path)
    search_index = ann_backend.SearchIndex(
        backend_name="torch-cuda-chunked",
        matrix=np.empty((3, 0), dtype=np.float32),
        search_matrix=np.empty((0, 2), dtype=np.float32),
        mean=np.zeros(2, dtype=np.float32),
        scale=np.ones(2, dtype=np.float32),
        index=None,
        artifact_backend=ann_backend.COMPACT_STORAGE_FORMAT,
        device="cuda:0",
        device_name="Synthetic GPU",
        backend_details={
            "ann_search_matrix_path": str(matrix_path),
            "ann_search_matrix_encoding": "raw_float16",
            "ann_search_matrix_shape": [3, 2],
        },
    )

    def _fake_chunked(matrix, query, limit, *, device, chunk_size=500_000):
        assert matrix.shape == (3, 2)
        assert device == "cuda:0"
        assert limit == 2
        np.testing.assert_array_equal(query, np.asarray([0.0, 0.0], dtype=np.float32))
        return np.asarray([0.0, 1.0], dtype=np.float32), np.asarray([0, 1], dtype=np.int64)

    monkeypatch.setattr(ann_backend, "_search_torch_chunked", _fake_chunked)

    distances, indices = search_index.search(np.asarray([0.0, 0.0], dtype=np.float32), top_k=2)

    np.testing.assert_array_equal(distances, np.asarray([0.0, 1.0], dtype=np.float32))
    np.testing.assert_array_equal(indices, np.asarray([0, 1], dtype=np.int64))


def test_torch_runtime_search_failure_falls_back_to_numpy(monkeypatch):
    matrix = _sample_matrix()
    search_matrix, mean, scale = ann_backend._standardize_matrix(matrix)
    search_index = ann_backend.SearchIndex(
        backend_name="torch-cuda-bruteforce",
        matrix=matrix,
        search_matrix=search_matrix,
        mean=mean,
        scale=scale,
        index=ann_backend.TorchLinearIndex(
            matrix_tensor="synthetic-gpu-matrix",
            squared_norms="synthetic-gpu-norms",
            device="cuda:0",
            device_name="Synthetic GPU",
        ),
        artifact_backend="torch-cuda-bruteforce",
        device="cuda:0",
        device_name="Synthetic GPU",
        backend_details={"preferred_backend": "torch-cuda-bruteforce"},
    )

    def _raise_runtime_failure(*args, **kwargs):
        raise RuntimeError("simulated CUDA failure")

    monkeypatch.setattr(ann_backend, "_search_torch_index", _raise_runtime_failure)

    distances, indices = search_index.search(matrix[0], top_k=2)

    assert search_index.backend_name == "numpy-bruteforce"
    assert search_index.device == "cpu"
    assert search_index.device_name is None
    assert "simulated CUDA failure" in search_index.backend_details["fallback_reason"]
    np.testing.assert_allclose(distances[0], 0.0)
    np.testing.assert_array_equal(indices, np.asarray([0, 1], dtype=np.int64))


def test_ann_backend_save_records_runtime_device_metadata(tmp_path):
    backend = ann_backend.AnnBackend(prefer_faiss=False, prefer_torch_cuda=True)
    matrix = _sample_matrix()
    search_matrix, mean, scale = ann_backend._standardize_matrix(matrix)
    search_index = ann_backend.SearchIndex(
        backend_name="torch-cuda-bruteforce",
        matrix=matrix,
        search_matrix=search_matrix,
        mean=mean,
        scale=scale,
        index=ann_backend.TorchLinearIndex(
            matrix_tensor="synthetic-gpu-matrix",
            squared_norms="synthetic-gpu-norms",
            device="cuda:0",
            device_name="Synthetic GPU",
        ),
        artifact_backend="torch-cuda-bruteforce",
        device="cuda:0",
        device_name="Synthetic GPU",
        backend_details={"preferred_backend": "torch-cuda-bruteforce"},
    )

    directory = tmp_path / "saved-index"
    backend.save(search_index, directory)
    backend_meta = json.loads((directory / "backend.json").read_text(encoding="utf-8"))

    assert backend_meta["backend"] == "torch-cuda-bruteforce"
    assert backend_meta["active_backend_at_build"] == "torch-cuda-bruteforce"
    assert backend_meta["device"] == "cuda:0"
    assert backend_meta["device_name"] == "Synthetic GPU"
    assert backend_meta["backend_details"]["preferred_backend"] == "torch-cuda-bruteforce"

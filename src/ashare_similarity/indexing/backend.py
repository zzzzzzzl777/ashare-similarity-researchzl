from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np

from ashare_similarity.indexing.compact_builder import COMPACT_STORAGE_FORMAT

try:
    import faiss  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    faiss = None

try:
    from sklearn.neighbors import NearestNeighbors
except Exception:  # pragma: no cover - optional dependency
    NearestNeighbors = None

try:
    import torch  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    torch = None


@dataclass(slots=True)
class TorchLinearIndex:
    matrix_tensor: Any
    squared_norms: Any
    device: str
    device_name: str | None


@dataclass(slots=True)
class SearchIndex:
    backend_name: str
    matrix: np.ndarray
    search_matrix: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    index: object | None = None
    artifact_backend: str | None = None
    device: str = "cpu"
    device_name: str | None = None
    backend_details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.artifact_backend:
            self.artifact_backend = self.backend_name
        self.backend_details = _coerce_backend_details(self.backend_details)
        if not self.device:
            self.device = "cuda:0" if "cuda" in str(self.backend_name) else "cpu"

    def runtime_metadata(self) -> dict[str, Any]:
        details = dict(self.backend_details)
        details.update(
            {
                "active_backend": self.backend_name,
                "artifact_backend": self.artifact_backend or self.backend_name,
                "active_device": self.device,
                "active_device_name": self.device_name,
            }
        )
        return _coerce_backend_details(details)

    def search(self, query: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        row_count = _row_count(self)
        if row_count == 0:
            return np.zeros((0,), dtype=np.float32), np.zeros((0,), dtype=np.int64)

        query_vector = np.asarray(query, dtype=np.float32)
        if query_vector.ndim == 2:
            query_vector = query_vector[0]
        transformed_query = _transform_query(query_vector, self.mean, self.scale).reshape(1, -1)
        limit = max(1, min(int(top_k), row_count))

        if self.backend_name.startswith("torch") and isinstance(self.index, TorchLinearIndex):
            try:
                return _search_torch_index(self.index, transformed_query, limit)
            except Exception as exc:
                self._fallback_to_numpy(f"torch runtime search failed: {exc}")

        if self.backend_name.startswith("faiss") and self.index is not None:
            try:
                distances, indices = self.index.search(transformed_query, limit)
                return distances[0].astype(np.float32, copy=False), indices[0].astype(np.int64, copy=False)
            except Exception as exc:
                self._fallback_to_numpy(f"faiss runtime search failed: {exc}")

        if self.backend_name.startswith("sklearn") and self.index is not None:
            try:
                distances, indices = self.index.kneighbors(transformed_query, n_neighbors=limit)
                return distances[0].astype(np.float32, copy=False), indices[0].astype(np.int64, copy=False)
            except Exception as exc:
                self._fallback_to_numpy(f"sklearn runtime search failed: {exc}")

        if self.backend_name == "torch-cuda-chunked" and self.backend_details.get("ann_search_matrix_path"):
            try:
                return _search_torch_chunked(
                    self._open_search_matrix(),
                    transformed_query.reshape(-1),
                    limit,
                    device=self.device,
                )
            except Exception as exc:
                self._fallback_to_numpy(f"torch CUDA chunked search failed: {exc}")

        if self.search_matrix.size == 0 and self.backend_details.get("ann_search_matrix_path"):
            return _search_numpy_chunked(
                self._open_search_matrix(),
                transformed_query.reshape(-1),
                limit,
            )

        if isinstance(self.search_matrix, np.memmap) or row_count > 1_000_000:
            return _search_numpy_chunked(
                self._open_search_matrix() if self.search_matrix.size == 0 else self.search_matrix,
                transformed_query.reshape(-1),
                limit,
            )

        delta = self.search_matrix - transformed_query
        distances = np.sqrt(np.sum(delta * delta, axis=1, dtype=np.float32))
        indices = np.argpartition(distances, limit - 1)[:limit]
        order = np.argsort(distances[indices], kind="stable")
        ranked_indices = indices[order]
        return distances[ranked_indices].astype(np.float32, copy=False), ranked_indices.astype(np.int64, copy=False)

    def _open_search_matrix(self) -> np.ndarray:
        path = self.backend_details.get("ann_search_matrix_path")
        if not path:
            return self.search_matrix
        if self.backend_details.get("ann_search_matrix_encoding") == "raw_float16":
            shape = tuple(int(value) for value in self.backend_details.get("ann_search_matrix_shape", []))
            if len(shape) != 2:
                raise RuntimeError("Compact raw search matrix shape is missing or invalid.")
            return np.memmap(str(path), dtype=np.float16, mode="r", shape=shape)
        return np.load(str(path), mmap_mode="r")

    def _fallback_to_numpy(self, reason: str) -> None:
        failed_backend = self.backend_name
        details = dict(self.backend_details)
        chain = list(details.get("fallback_chain") or [])
        chain.append(reason)
        details["fallback_chain"] = chain
        details["fallback_reason"] = reason
        details["fallback_from"] = failed_backend
        self.backend_details = _coerce_backend_details(details)
        self.backend_name = "numpy-bruteforce"
        self.device = "cpu"
        self.device_name = None
        self.index = None


class AnnBackend:
    def __init__(self, prefer_faiss: bool = True, prefer_torch_cuda: bool = True) -> None:
        self.prefer_faiss = prefer_faiss
        self.prefer_torch_cuda = prefer_torch_cuda

    def build(self, matrix: np.ndarray) -> SearchIndex:
        raw_matrix = np.asarray(matrix, dtype=np.float32)
        if raw_matrix.ndim != 2:
            raise ValueError("Feature matrix must be 2D.")
        if raw_matrix.shape[0] == 0 or raw_matrix.shape[1] == 0:
            raise ValueError("Feature matrix is empty; cannot build ANN index.")

        search_matrix, mean, scale = _standardize_matrix(raw_matrix)
        fallback_chain: list[str] = []

        if self.prefer_torch_cuda:
            try:
                return self._build_torch_index(
                    raw_matrix,
                    search_matrix,
                    mean,
                    scale,
                    artifact_backend="torch-cuda-bruteforce",
                )
            except Exception as exc:
                fallback_chain.append(f"torch-cuda backend unavailable during build: {exc}")

        if self.prefer_faiss and faiss is not None:
            try:
                return self._build_faiss_index(
                    raw_matrix,
                    search_matrix,
                    mean,
                    scale,
                    artifact_backend=None,
                    backend_details=self._selection_details(fallback_chain),
                )
            except Exception as exc:
                fallback_chain.append(f"faiss backend unavailable during build: {exc}")

        if NearestNeighbors is not None:
            try:
                model = NearestNeighbors(metric="euclidean", algorithm="auto")
                model.fit(search_matrix)
                return SearchIndex(
                    backend_name="sklearn-nearest",
                    matrix=raw_matrix,
                    search_matrix=search_matrix,
                    mean=mean,
                    scale=scale,
                    index=model,
                    artifact_backend="sklearn-nearest",
                    device="cpu",
                    device_name=None,
                    backend_details=self._selection_details(fallback_chain),
                )
            except Exception as exc:
                fallback_chain.append(f"sklearn backend unavailable during build: {exc}")

        return SearchIndex(
            backend_name="numpy-bruteforce",
            matrix=raw_matrix,
            search_matrix=search_matrix,
            mean=mean,
            scale=scale,
            index=None,
            artifact_backend="numpy-bruteforce",
            device="cpu",
            device_name=None,
            backend_details=self._selection_details(fallback_chain),
        )

    def save(self, search_index: SearchIndex, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        ann_matrix_path = directory / "ann_matrix.npy"
        ann_search_matrix_path = directory / "ann_search_matrix.npy"
        backend_path = directory / "backend.json"
        faiss_path = directory / "ann_index.faiss"
        backend_payload = {
            "backend": search_index.artifact_backend or search_index.backend_name,
            "active_backend_at_build": search_index.backend_name,
            "dimension": int(search_index.matrix.shape[1]) if search_index.matrix.ndim == 2 else 0,
            "vector_count": int(search_index.matrix.shape[0]) if search_index.matrix.ndim == 2 else 0,
            "mean": search_index.mean.astype(np.float32).tolist(),
            "scale": search_index.scale.astype(np.float32).tolist(),
            "device": search_index.device,
            "device_name": search_index.device_name,
            "backend_details": _coerce_backend_details(search_index.backend_details),
        }
        staged_files = {
            ann_matrix_path: self._write_npy_temp(
                ann_matrix_path,
                search_index.matrix.astype(np.float32, copy=False),
            ),
            ann_search_matrix_path: self._write_npy_temp(
                ann_search_matrix_path,
                search_index.search_matrix.astype(np.float32, copy=False),
            ),
            backend_path: self._write_text_temp(
                backend_path,
                json.dumps(backend_payload, ensure_ascii=False, indent=2),
            ),
        }
        stale_targets: list[Path] = []
        if search_index.backend_name.startswith("faiss") and search_index.index is not None and faiss is not None:
            staged_files[faiss_path] = self._write_faiss_temp(faiss_path, search_index.index)
        elif faiss_path.exists():
            stale_targets.append(faiss_path)

        self._commit_atomic_files(staged_files, stale_targets=stale_targets)

    def load(self, directory: Path) -> SearchIndex:
        backend_meta = json.loads((directory / "backend.json").read_text(encoding="utf-8"))
        mean = np.asarray(backend_meta.get("mean", []), dtype=np.float32)
        scale = np.asarray(backend_meta.get("scale", []), dtype=np.float32)
        artifact_backend = str(backend_meta.get("backend", "numpy-bruteforce"))
        compact_storage = artifact_backend == COMPACT_STORAGE_FORMAT

        if compact_storage:
            search_path = directory / "ann_search_matrix.npy"
            if backend_meta.get("ann_search_matrix_encoding") == "raw_float16":
                search_shape = tuple(int(value) for value in backend_meta.get("ann_search_matrix_shape", []))
                if len(search_shape) != 2:
                    raise RuntimeError(f"Compact raw search matrix shape is missing in {directory / 'backend.json'}.")
            else:
                search_matrix_probe = np.load(search_path, mmap_mode="r")
                search_shape = tuple(search_matrix_probe.shape)
                del search_matrix_probe
            search_matrix = np.empty((0, int(search_shape[1])), dtype=np.float32)
            raw_matrix = np.empty((int(search_shape[0]), 0), dtype=np.float32)
        else:
            raw_matrix = np.load(directory / "ann_matrix.npy").astype(np.float32, copy=False)
            if (directory / "ann_search_matrix.npy").exists():
                search_matrix = np.load(directory / "ann_search_matrix.npy").astype(np.float32, copy=False)
            else:
                search_matrix, mean, scale = _standardize_matrix(raw_matrix, mean=mean, scale=scale)

        if compact_storage:
            search_matrix = np.asarray(search_matrix)
        else:
            search_matrix = np.asarray(search_matrix, dtype=np.float32)

        backend_details = _coerce_backend_details(backend_meta.get("backend_details"))
        fallback_chain = list(backend_details.get("fallback_chain") or [])

        if self.prefer_torch_cuda and not compact_storage:
            try:
                runtime_index = self._build_torch_index(
                    raw_matrix,
                    search_matrix,
                    mean,
                    scale,
                    artifact_backend=artifact_backend,
                    backend_details=backend_details,
                )
                if artifact_backend != runtime_index.backend_name:
                    runtime_index.backend_details["runtime_override_from_artifact"] = artifact_backend
                return runtime_index
            except Exception as exc:
                fallback_chain.append(f"torch-cuda backend unavailable during load: {exc}")

        if artifact_backend.startswith("faiss") and faiss is not None and (directory / "ann_index.faiss").exists():
            index = faiss.read_index(str(directory / "ann_index.faiss"))
            return SearchIndex(
                backend_name=artifact_backend,
                matrix=raw_matrix,
                search_matrix=search_matrix,
                mean=mean,
                scale=scale,
                index=index,
                artifact_backend=artifact_backend,
                device="cpu",
                device_name=None,
                backend_details=self._selection_details(fallback_chain, base_details=backend_details),
            )

        if compact_storage:
            backend_details["ann_search_matrix_path"] = str(directory / "ann_search_matrix.npy")
            backend_details["ann_search_matrix_encoding"] = backend_meta.get("ann_search_matrix_encoding")
            backend_details["ann_search_matrix_shape"] = backend_meta.get("ann_search_matrix_shape")
            backend_details["ann_search_matrix_dtype"] = backend_meta.get("ann_search_matrix_dtype")
            backend_details["compact_row_count"] = int(raw_matrix.shape[0])
            if self.prefer_torch_cuda:
                environment = get_acceleration_environment()
                if torch is not None and environment.get("torch_cuda_available"):
                    backend_details["runtime_backend_source"] = "torch-cuda-chunked"
                    backend_details["torch_version"] = environment.get("torch_version")
                    backend_details["torch_cuda_device_count"] = environment.get("torch_cuda_device_count")
                    return SearchIndex(
                        backend_name="torch-cuda-chunked",
                        matrix=raw_matrix,
                        search_matrix=search_matrix,
                        mean=mean,
                        scale=scale,
                        index=None,
                        artifact_backend=artifact_backend,
                        device="cuda:0",
                        device_name=environment.get("torch_device_name"),
                        backend_details=self._selection_details(fallback_chain, base_details=backend_details),
                    )
            return SearchIndex(
                backend_name="numpy-bruteforce",
                matrix=raw_matrix,
                search_matrix=search_matrix,
                mean=mean,
                scale=scale,
                index=None,
                artifact_backend=artifact_backend,
                device="cpu",
                device_name=None,
                backend_details=self._selection_details(fallback_chain, base_details=backend_details),
            )

        if NearestNeighbors is not None:
            model = NearestNeighbors(metric="euclidean", algorithm="auto")
            model.fit(search_matrix)
            return SearchIndex(
                backend_name="sklearn-nearest",
                matrix=raw_matrix,
                search_matrix=search_matrix,
                mean=mean,
                scale=scale,
                index=model,
                artifact_backend=artifact_backend,
                device="cpu",
                device_name=None,
                backend_details=self._selection_details(fallback_chain, base_details=backend_details),
            )

        return SearchIndex(
            backend_name="numpy-bruteforce",
            matrix=raw_matrix,
            search_matrix=search_matrix,
            mean=mean,
            scale=scale,
            index=None,
            artifact_backend=artifact_backend,
            device="cpu",
            device_name=None,
            backend_details=self._selection_details(fallback_chain, base_details=backend_details),
        )

    def _build_torch_index(
        self,
        raw_matrix: np.ndarray,
        search_matrix: np.ndarray,
        mean: np.ndarray,
        scale: np.ndarray,
        *,
        artifact_backend: str,
        backend_details: dict[str, Any] | None = None,
    ) -> SearchIndex:
        environment = get_acceleration_environment()
        if torch is None:
            raise RuntimeError("torch is not installed.")
        if not environment["torch_cuda_available"]:
            reason = environment.get("torch_cuda_error") or "torch CUDA is unavailable."
            raise RuntimeError(str(reason))

        device = "cuda:0"
        matrix_tensor = torch.as_tensor(search_matrix, dtype=torch.float32, device=device)
        squared_norms = torch.sum(matrix_tensor * matrix_tensor, dim=1)
        details = self._selection_details([], base_details=backend_details)
        details["runtime_backend_source"] = "torch-cuda"
        details["torch_version"] = environment.get("torch_version")
        details["torch_cuda_device_count"] = environment.get("torch_cuda_device_count")
        return SearchIndex(
            backend_name="torch-cuda-bruteforce",
            matrix=raw_matrix,
            search_matrix=search_matrix,
            mean=mean,
            scale=scale,
            index=TorchLinearIndex(
                matrix_tensor=matrix_tensor,
                squared_norms=squared_norms,
                device=device,
                device_name=environment.get("torch_device_name"),
            ),
            artifact_backend=artifact_backend,
            device=device,
            device_name=environment.get("torch_device_name"),
            backend_details=details,
        )

    def _build_faiss_index(
        self,
        raw_matrix: np.ndarray,
        search_matrix: np.ndarray,
        mean: np.ndarray,
        scale: np.ndarray,
        *,
        artifact_backend: str | None = None,
        backend_details: dict[str, Any] | None = None,
    ) -> SearchIndex:
        assert faiss is not None
        dimension = search_matrix.shape[1]
        if search_matrix.shape[0] >= 1000:
            index = faiss.IndexHNSWFlat(dimension, 32)
            index.hnsw.efConstruction = 120
            index.hnsw.efSearch = 96
            backend_name = "faiss-hnsw"
        else:
            index = faiss.IndexFlatL2(dimension)
            backend_name = "faiss-flat"
        index.add(search_matrix)
        details = self._selection_details([], base_details=backend_details)
        details["runtime_backend_source"] = "faiss"
        return SearchIndex(
            backend_name=backend_name,
            matrix=raw_matrix,
            search_matrix=search_matrix,
            mean=mean,
            scale=scale,
            index=index,
            artifact_backend=artifact_backend or backend_name,
            device="cpu",
            device_name=None,
            backend_details=details,
        )

    def _selection_details(
        self,
        fallback_chain: list[str],
        *,
        base_details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        details = _coerce_backend_details(base_details)
        if fallback_chain:
            details["fallback_chain"] = list(fallback_chain)
            details["fallback_reason"] = fallback_chain[-1]
        if self.prefer_torch_cuda:
            details.setdefault("preferred_backend", "torch-cuda-bruteforce")
        return details

    def _write_npy_temp(self, destination: Path, array: np.ndarray) -> Path:
        temp_path = self._temp_path(destination)
        with temp_path.open("wb") as handle:
            np.save(handle, np.asarray(array, dtype=np.float32))
        return temp_path

    def _write_text_temp(self, destination: Path, content: str) -> Path:
        temp_path = self._temp_path(destination)
        temp_path.write_text(content, encoding="utf-8")
        return temp_path

    def _write_faiss_temp(self, destination: Path, index: object) -> Path:
        if faiss is None:
            raise RuntimeError("faiss is not available.")
        temp_path = self._temp_path(destination)
        faiss.write_index(index, str(temp_path))
        return temp_path

    def _commit_atomic_files(
        self,
        staged_files: dict[Path, Path],
        *,
        stale_targets: list[Path] | None = None,
    ) -> None:
        stale_targets = list(stale_targets or [])
        backup_paths: dict[Path, Path] = {}
        committed_targets: list[Path] = []
        commit_targets = list(staged_files.keys())
        if stale_targets:
            commit_targets.extend(path for path in stale_targets if path not in staged_files)

        try:
            for target in commit_targets:
                if target.exists():
                    backup_path = self._backup_path(target)
                    self._replace_file(target, backup_path)
                    backup_paths[target] = backup_path

            for target, temp_path in staged_files.items():
                self._replace_file(temp_path, target)
                committed_targets.append(target)
        except Exception:
            for target in reversed(committed_targets):
                self._remove_file(target)
            for target in reversed(commit_targets):
                backup_path = backup_paths.get(target)
                if backup_path is not None and backup_path.exists():
                    self._replace_file(backup_path, target)
            raise
        finally:
            for temp_path in staged_files.values():
                self._remove_file(temp_path)
            for backup_path in backup_paths.values():
                self._remove_file(backup_path)

    def _temp_path(self, destination: Path) -> Path:
        return destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")

    def _backup_path(self, destination: Path) -> Path:
        return destination.with_name(f".{destination.name}.{uuid4().hex}.bak")

    def _replace_file(self, source: Path, destination: Path) -> None:
        for attempt in range(6):
            try:
                source.replace(destination)
                return
            except OSError as exc:
                if not _is_retryable_file_error(exc) or attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))

    def _remove_file(self, path: Path) -> None:
        for attempt in range(6):
            try:
                path.unlink(missing_ok=True)
                return
            except FileNotFoundError:
                return
            except OSError as exc:
                if not _is_retryable_file_error(exc) or attempt == 5:
                    return
                time.sleep(0.05 * (attempt + 1))


def _is_retryable_file_error(exc: OSError) -> bool:
    return isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in {5, 32, 33}


def get_acceleration_environment() -> dict[str, Any]:
    faiss_available = faiss is not None
    faiss_gpu_api_available = bool(faiss_available and hasattr(faiss, "StandardGpuResources"))

    torch_available = torch is not None
    torch_cuda_available = False
    torch_cuda_device_count = 0
    torch_device_name = None
    torch_version = getattr(torch, "__version__", None) if torch_available else None
    torch_cuda_error = None

    if torch_available:
        cuda_api = getattr(torch, "cuda", None)
        if cuda_api is None:
            torch_cuda_error = "torch.cuda API is unavailable."
        else:
            try:
                torch_cuda_available = bool(cuda_api.is_available())
                if torch_cuda_available:
                    torch_cuda_device_count = int(cuda_api.device_count())
                    if torch_cuda_device_count <= 0:
                        torch_cuda_available = False
                        torch_cuda_error = "torch.cuda.device_count() returned 0."
                    elif hasattr(cuda_api, "get_device_name"):
                        torch_device_name = str(cuda_api.get_device_name(0))
            except Exception as exc:
                torch_cuda_available = False
                torch_cuda_error = str(exc)

    return {
        "faiss_available": faiss_available,
        "faiss_gpu_api_available": faiss_gpu_api_available,
        "torch_available": torch_available,
        "torch_version": torch_version,
        "torch_cuda_available": torch_cuda_available,
        "torch_cuda_device_count": torch_cuda_device_count,
        "torch_device_name": torch_device_name,
        "torch_cuda_error": torch_cuda_error,
    }


def _search_torch_index(
    torch_index: TorchLinearIndex,
    transformed_query: np.ndarray,
    limit: int,
) -> tuple[np.ndarray, np.ndarray]:
    if torch is None:
        raise RuntimeError("torch is not installed.")

    query_tensor = torch.as_tensor(transformed_query.reshape(-1), dtype=torch.float32, device=torch_index.device)
    query_squared_norm = torch.sum(query_tensor * query_tensor)
    distances_sq = torch_index.squared_norms + query_squared_norm - 2.0 * torch.matmul(torch_index.matrix_tensor, query_tensor)
    distances_sq = torch.clamp(distances_sq, min=0.0)
    top_values, top_indices = torch.topk(distances_sq, k=limit, largest=False, sorted=True)
    distances = torch.sqrt(top_values).detach().cpu().numpy().astype(np.float32, copy=False)
    indices = top_indices.detach().cpu().numpy().astype(np.int64, copy=False)
    return distances, indices


def _search_torch_chunked(
    matrix: np.ndarray,
    query: np.ndarray,
    limit: int,
    *,
    device: str,
    chunk_size: int = 2_000_000,
) -> tuple[np.ndarray, np.ndarray]:
    if torch is None:
        raise RuntimeError("torch is not installed.")

    chunk_size = _configured_gpu_chunk_size(chunk_size)
    best_distances = np.full((0,), np.inf, dtype=np.float32)
    best_indices = np.zeros((0,), dtype=np.int64)
    query_vector = np.asarray(query, dtype=np.float32).reshape(-1)
    total_rows = int(matrix.shape[0])
    with torch.no_grad():
        query_tensor = torch.as_tensor(query_vector, dtype=torch.float32, device=device)
        query_squared_norm = torch.sum(query_tensor * query_tensor)
        for start in range(0, total_rows, chunk_size):
            stop = min(start + chunk_size, total_rows)
            chunk = np.asarray(matrix[start:stop], dtype=np.float32)
            chunk_tensor = torch.as_tensor(chunk, dtype=torch.float32, device=device)
            squared_norms = torch.sum(chunk_tensor * chunk_tensor, dim=1)
            distances_sq = squared_norms + query_squared_norm - 2.0 * torch.matmul(chunk_tensor, query_tensor)
            distances_sq = torch.clamp(distances_sq, min=0.0)
            local_limit = min(limit, int(distances_sq.numel()))
            top_values, top_indices = torch.topk(distances_sq, k=local_limit, largest=False, sorted=False)
            candidate_distances = torch.sqrt(top_values).detach().cpu().numpy().astype(np.float32, copy=False)
            candidate_indices = top_indices.detach().cpu().numpy().astype(np.int64, copy=False) + start
            best_distances = np.concatenate([best_distances, candidate_distances])
            best_indices = np.concatenate([best_indices, candidate_indices])
            keep = min(limit, best_distances.size)
            keep_indices = np.argpartition(best_distances, keep - 1)[:keep]
            best_distances = best_distances[keep_indices]
            best_indices = best_indices[keep_indices]
            del chunk_tensor, squared_norms, distances_sq, top_values, top_indices
    order = np.argsort(best_distances, kind="stable")
    return best_distances[order].astype(np.float32, copy=False), best_indices[order].astype(np.int64, copy=False)


def _configured_gpu_chunk_size(default: int) -> int:
    import os

    raw_value = os.environ.get("ASHARE_SIMILARITY_GPU_CHUNK_ROWS")
    if not raw_value:
        return int(default)
    try:
        value = int(raw_value)
    except ValueError:
        return int(default)
    return max(100_000, min(value, 10_000_000))


def _search_numpy_chunked(matrix: np.ndarray, query: np.ndarray, limit: int, chunk_size: int = 250_000) -> tuple[np.ndarray, np.ndarray]:
    best_distances = np.full((0,), np.inf, dtype=np.float32)
    best_indices = np.zeros((0,), dtype=np.int64)
    query_vector = np.asarray(query, dtype=np.float32).reshape(1, -1)
    total_rows = int(matrix.shape[0])
    for start in range(0, total_rows, chunk_size):
        stop = min(start + chunk_size, total_rows)
        chunk = np.asarray(matrix[start:stop], dtype=np.float32)
        delta = chunk - query_vector
        distances = np.sqrt(np.sum(delta * delta, axis=1, dtype=np.float32))
        local_limit = min(limit, distances.size)
        local_indices = np.argpartition(distances, local_limit - 1)[:local_limit]
        candidate_distances = distances[local_indices]
        candidate_indices = local_indices.astype(np.int64, copy=False) + start
        best_distances = np.concatenate([best_distances, candidate_distances.astype(np.float32, copy=False)])
        best_indices = np.concatenate([best_indices, candidate_indices])
        keep = min(limit, best_distances.size)
        keep_indices = np.argpartition(best_distances, keep - 1)[:keep]
        best_distances = best_distances[keep_indices]
        best_indices = best_indices[keep_indices]
    order = np.argsort(best_distances, kind="stable")
    return best_distances[order].astype(np.float32, copy=False), best_indices[order].astype(np.int64, copy=False)


def _row_count(search_index: SearchIndex) -> int:
    matrix_rows = int(search_index.matrix.shape[0]) if getattr(search_index.matrix, "ndim", 0) >= 1 else 0
    search_rows = (
        int(search_index.search_matrix.shape[0])
        if getattr(search_index.search_matrix, "ndim", 0) >= 1
        else 0
    )
    return max(matrix_rows, search_rows)


def _coerce_backend_details(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): _jsonable_value(item) for key, item in value.items()}
    return {}


def _jsonable_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable_value(item) for item in value]
    return str(value)


def _standardize_matrix(
    matrix: np.ndarray,
    *,
    mean: np.ndarray | None = None,
    scale: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if matrix.ndim != 2:
        raise ValueError("matrix must be 2D")
    if matrix.shape[1] == 0:
        return matrix.astype(np.float32, copy=False), np.zeros(0, dtype=np.float32), np.zeros(0, dtype=np.float32)

    if mean is None or mean.size == 0:
        mean = matrix.mean(axis=0).astype(np.float32)
    if scale is None or scale.size == 0:
        scale = matrix.std(axis=0).astype(np.float32)

    mean = mean.astype(np.float32, copy=False)
    scale = scale.astype(np.float32, copy=False)
    scale[scale < 1e-8] = 1.0
    normalized = np.ascontiguousarray((matrix.astype(np.float32) - mean) / scale, dtype=np.float32)
    return normalized, mean, scale


def _transform_query(query: np.ndarray, mean: np.ndarray, scale: np.ndarray) -> np.ndarray:
    vector = np.asarray(query, dtype=np.float32).reshape(-1)
    dimension = mean.size if mean.size else vector.size
    fitted = np.zeros(dimension, dtype=np.float32)
    usable = min(vector.size, dimension)
    if usable:
        fitted[:usable] = vector[:usable]
    safe_scale = scale.astype(np.float32, copy=False)
    safe_scale[safe_scale < 1e-8] = 1.0
    return ((fitted - mean) / safe_scale).astype(np.float32, copy=False)

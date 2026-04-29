from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class TensorCacheKey:
    sample_scope: str
    feature_schema: list[str]
    split_hash: str
    label_config: dict[str, Any]
    feature_fingerprint: str | None = None
    dtype: str = "float32"
    version: int = 1

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class TensorCacheManager:
    """Small immutable numpy tensor cache used before optional torch GPU loading."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def paths_for(self, key: TensorCacheKey) -> dict[str, Path]:
        stem = f"tensor_cache_{key.fingerprint()}"
        return {
            "arrays": self.cache_dir / f"{stem}.npz",
            "manifest": self.cache_dir / f"{stem}.json",
        }

    def exists(self, key: TensorCacheKey) -> bool:
        paths = self.paths_for(key)
        return paths["arrays"].exists() and paths["manifest"].exists()

    def save(self, key: TensorCacheKey, arrays: dict[str, np.ndarray], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        paths = self.paths_for(key)
        serializable = {name: np.asarray(value, dtype=key.dtype) for name, value in arrays.items()}
        np.savez_compressed(paths["arrays"], **serializable)
        manifest = {
            "fingerprint": key.fingerprint(),
            "key": asdict(key),
            "arrays": {name: list(value.shape) for name, value in serializable.items()},
            "metadata": metadata or {},
        }
        _atomic_write_json(paths["manifest"], manifest)
        return {**manifest, "path": str(paths["arrays"])}

    def load(self, key: TensorCacheKey) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        paths = self.paths_for(key)
        if not self.exists(key):
            raise FileNotFoundError(f"Tensor cache miss for fingerprint {key.fingerprint()}")
        with np.load(paths["arrays"]) as loaded:
            arrays = {name: loaded[name] for name in loaded.files}
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        return arrays, manifest


def standardize_train_valid_test(
    x_train: np.ndarray,
    x_valid: np.ndarray,
    x_test: np.ndarray,
    *,
    eps: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    train = np.asarray(x_train, dtype=np.float32)
    valid = np.asarray(x_valid, dtype=np.float32)
    test = np.asarray(x_test, dtype=np.float32)
    mean = train.mean(axis=0, keepdims=True)
    std = np.maximum(train.std(axis=0, keepdims=True), float(eps))
    return (
        (train - mean) / std,
        (valid - mean) / std,
        (test - mean) / std,
        {"mean": mean.astype(np.float32), "std": std.astype(np.float32)},
    )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp_path.replace(path)

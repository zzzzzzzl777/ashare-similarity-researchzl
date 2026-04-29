from __future__ import annotations

import numpy as np
import pytest

from ashare_similarity.prediction.tensor_cache import (
    TensorCacheKey,
    TensorCacheManager,
    standardize_train_valid_test,
)


def test_tensor_cache_fingerprint_changes_with_split_hash(tmp_path):
    key_a = TensorCacheKey(
        sample_scope="active_short_phase",
        feature_schema=["ret_1", "turnover"],
        split_hash="split-a",
        label_config={"horizon": 1},
    )
    key_b = TensorCacheKey(
        sample_scope="active_short_phase",
        feature_schema=["ret_1", "turnover"],
        split_hash="split-b",
        label_config={"horizon": 1},
    )
    assert key_a.fingerprint() != key_b.fingerprint()

    manager = TensorCacheManager(tmp_path)
    arrays = {"X_train": np.ones((3, 2)), "y_train": np.array([1, 0, 1])}
    manifest = manager.save(key_a, arrays, metadata={"device": "cuda"})
    loaded, loaded_manifest = manager.load(key_a)

    assert manifest["fingerprint"] == key_a.fingerprint()
    assert loaded_manifest["metadata"]["device"] == "cuda"
    assert loaded["X_train"].shape == (3, 2)
    with pytest.raises(FileNotFoundError):
        manager.load(key_b)


def test_standardize_train_valid_test_fits_only_train_distribution():
    train = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    valid = np.array([[5.0, 6.0]], dtype=np.float32)
    test = np.array([[7.0, 8.0]], dtype=np.float32)

    x_train, x_valid, x_test, stats = standardize_train_valid_test(train, valid, test)

    assert x_train.mean(axis=0) == pytest.approx([0.0, 0.0])
    assert stats["mean"].tolist() == [[2.0, 3.0]]
    assert x_valid.ravel().tolist() == pytest.approx([3.0, 3.0])
    assert x_test.ravel().tolist() == pytest.approx([5.0, 5.0])

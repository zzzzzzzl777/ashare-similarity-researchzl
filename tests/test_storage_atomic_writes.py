from __future__ import annotations

import json

import numpy as np
import pandas as pd
import polars as pl
import pytest

from ashare_similarity.data.storage import LocalDataStore


def _make_daily_bars(symbol: str, closes: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=len(closes))
    return pd.DataFrame(
        {
            "symbol": [symbol] * len(closes),
            "date": dates,
            "open": closes,
            "high": [value + 0.2 for value in closes],
            "low": [value - 0.2 for value in closes],
            "close": closes,
            "volume": [1_000_000 + index * 10_000 for index, _ in enumerate(closes)],
            "turnover": [close * 1_000_000 for close in closes],
        }
    )


def _make_feature_payload(row_count: int, *, offset: float = 0.0) -> tuple[np.ndarray, pd.DataFrame, dict[str, object]]:
    matrix = np.arange(row_count * 2, dtype=np.float32).reshape(row_count, 2) + offset
    metadata = pd.DataFrame(
        {
            "symbol": [f"00000{index + 1}" for index in range(row_count)],
            "frequency": ["daily"] * row_count,
            "start_date": pd.bdate_range("2024-01-02", periods=row_count),
            "end_date": pd.bdate_range("2024-01-08", periods=row_count),
        }
    )
    manifest = {
        "frequency": "daily",
        "window_size": 5,
        "row_count": row_count,
        "vector_dim": 2,
        "metadata_columns": metadata.columns.tolist(),
    }
    return matrix, metadata, manifest


def test_save_frame_keeps_existing_parquet_when_replace_fails(app_config, monkeypatch):
    store = LocalDataStore(app_config)
    symbol = "000001"
    initial = _make_daily_bars(symbol, [10.0, 10.5])
    updated = _make_daily_bars(symbol, [10.0, 10.5, 11.0])

    path = store.save_bars(symbol, "daily", initial)
    original_bytes = path.read_bytes()
    registry_before = store._query_registry(category="market_data", frequency="daily")

    original_replace = store._replace_file

    def fail_replace(source, destination):
        if destination == path:
            raise OSError("simulated parquet replace failure")
        return original_replace(source, destination)

    monkeypatch.setattr(store, "_replace_file", fail_replace)

    with pytest.raises(OSError, match="simulated parquet replace failure"):
        store.save_bars(symbol, "daily", updated)

    assert path.read_bytes() == original_bytes
    pd.testing.assert_frame_equal(
        store.load_bars(symbol, "daily").reset_index(drop=True),
        initial.reset_index(drop=True),
        check_dtype=False,
    )
    assert store._query_registry(category="market_data", frequency="daily") == registry_before
    assert not list(path.parent.glob("*.tmp"))
    assert not [item for item in path.parent.iterdir() if item.name.startswith(".") and item.suffix in {".tmp", ".bak"}]


def test_save_frame_rolls_back_parquet_when_registry_upsert_fails(app_config, monkeypatch):
    store = LocalDataStore(app_config)
    initial = pl.DataFrame(
        {
            "index_symbol": ["000001"],
            "date": [pd.Timestamp("2024-01-02").date()],
            "open": [10.0],
            "high": [10.2],
            "low": [9.8],
            "close": [10.1],
            "volume": [1_000_000],
        }
    )
    updated = pl.DataFrame(
        {
            "index_symbol": ["000001"],
            "date": [pd.Timestamp("2024-01-03").date()],
            "open": [11.0],
            "high": [11.2],
            "low": [10.8],
            "close": [11.1],
            "volume": [1_100_000],
        }
    )

    path = store.save_market_index_data("daily", "000001", initial, provider="synthetic")
    assert path is not None
    original_bytes = path.read_bytes()
    registry_before = store._query_registry(category="market_index_context", frequency="daily")

    def fail_registry(_payload):
        raise RuntimeError("simulated registry failure")

    monkeypatch.setattr(store, "_upsert_frame_registry", fail_registry)

    with pytest.raises(RuntimeError, match="simulated registry failure"):
        store.save_market_index_data("daily", "000001", updated, provider="synthetic")

    assert path.read_bytes() == original_bytes
    assert store._query_registry(category="market_index_context", frequency="daily") == registry_before
    assert not [item for item in path.parent.iterdir() if item.name.startswith(".") and item.suffix in {".tmp", ".bak"}]


def test_save_feature_artifacts_rolls_back_when_manifest_commit_fails(app_config, monkeypatch):
    store = LocalDataStore(app_config)
    matrix, metadata, manifest = _make_feature_payload(2)
    updated_matrix, updated_metadata, updated_manifest = _make_feature_payload(3, offset=100.0)

    output_paths = store.save_feature_artifacts("daily", 5, matrix, metadata, manifest)
    matrix_path = store.feature_dir("daily", 5) / "matrix.npy"
    metadata_path = store.feature_dir("daily", 5) / "metadata.parquet"
    manifest_path = store.feature_dir("daily", 5) / "manifest.json"
    original_files = {
        "matrix": matrix_path.read_bytes(),
        "metadata": metadata_path.read_bytes(),
        "manifest": manifest_path.read_bytes(),
    }

    original_replace = store._replace_file

    def fail_manifest_replace(source, destination):
        if destination == manifest_path:
            raise OSError("simulated manifest replace failure")
        return original_replace(source, destination)

    monkeypatch.setattr(store, "_replace_file", fail_manifest_replace)

    with pytest.raises(OSError, match="simulated manifest replace failure"):
        store.save_feature_artifacts("daily", 5, updated_matrix, updated_metadata, updated_manifest)

    assert output_paths == {
        "matrix": str(matrix_path),
        "metadata": str(metadata_path),
        "manifest": str(manifest_path),
    }
    assert matrix_path.read_bytes() == original_files["matrix"]
    assert metadata_path.read_bytes() == original_files["metadata"]
    assert manifest_path.read_bytes() == original_files["manifest"]

    loaded_matrix, loaded_metadata, loaded_manifest = store.load_feature_artifacts("daily", 5)
    np.testing.assert_array_equal(loaded_matrix, matrix)
    pd.testing.assert_frame_equal(loaded_metadata.reset_index(drop=True), metadata.reset_index(drop=True), check_dtype=False)
    assert loaded_manifest == manifest
    assert not [item for item in store.feature_dir("daily", 5).iterdir() if item.name.startswith(".") and item.suffix in {".tmp", ".bak"}]


def test_load_feature_artifacts_rejects_manifest_mismatch(app_config):
    store = LocalDataStore(app_config)
    matrix, metadata, manifest = _make_feature_payload(2)
    store.save_feature_artifacts("daily", 5, matrix, metadata, manifest)

    manifest_path = store.feature_dir("daily", 5) / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                **manifest,
                "row_count": 1,
                "metadata_columns": ["symbol"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="inconsistent"):
        store.load_feature_artifacts("daily", 5)

from __future__ import annotations

import gc
from types import SimpleNamespace

import numpy as np
import pandas as pd

from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.features.service import FeatureService
from ashare_similarity.indexing.compact_builder import COMPACT_STORAGE_FORMAT
from ashare_similarity.indexing.service import CompactMetadataAccessor
from ashare_similarity.indexing.service import IndexService


def test_compact_index_builds_without_persisting_full_raw_matrix(app_config, make_ohlcv_frame):
    store = LocalDataStore(app_config)
    frame_a = make_ohlcv_frame(symbol="000001", periods=12, pattern="query")
    frame_b = make_ohlcv_frame(symbol="000002", periods=12, pattern="similar", base_price=12.0)
    store.save_bars("000001", "daily", frame_a)
    store.save_bars("000002", "daily", frame_b)

    data_service = SimpleNamespace(
        load_price_history=lambda **kwargs: store.load_bars(
            kwargs["symbol"],
            kwargs["frequency"],
            kwargs.get("start_date"),
            kwargs.get("end_date"),
        ),
        get_symbol_name=lambda symbol: f"Name-{symbol}",
    )
    context_service = SimpleNamespace(
        get_market_context=lambda: pd.DataFrame(),
        get_industry_context=lambda: pd.DataFrame(),
    )
    feature_service = FeatureService(app_config, store, data_service, context_service)
    index_service = IndexService(app_config, store)
    index_service.ann_backend.prefer_torch_cuda = False

    summary = index_service.build_compact(
        feature_service=feature_service,
        frequency="daily",
        window_size=5,
        symbols=["000001", "000002"],
    )

    index_dir = store.feature_dir("daily", 5)
    assert summary.index_backend == COMPACT_STORAGE_FORMAT
    assert summary.symbols_processed == 2
    assert (index_dir / "ann_search_matrix.npy").exists()
    assert not (index_dir / "matrix.npy").exists()
    assert not (index_dir / "ann_matrix.npy").exists()

    query = feature_service.build_query_frame(
        symbol="000001",
        end_date=frame_a["date"].iloc[-1].date(),
        frequency="daily",
        window_size=5,
        ensure_remote=False,
    )
    searchable = index_service.load("daily", 5)
    assert isinstance(searchable.metadata, CompactMetadataAccessor)
    assert searchable.symbol_count == 2
    assert searchable.row_count == searchable.manifest["row_count"]
    assert searchable.metadata_row(0)["symbol"] in {"000001", "000002"}
    distances, indices = searchable.search(query.matrix.astype(np.float32), top_k=3)

    assert distances.shape == indices.shape
    assert indices.size == 3
    assert searchable.manifest["storage_format"] == COMPACT_STORAGE_FORMAT
    index_service._cache.clear()
    del searchable
    gc.collect()

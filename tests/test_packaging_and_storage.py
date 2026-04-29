from __future__ import annotations

from pathlib import Path

import pandas as pd

from ashare_similarity.app import _static_dir
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.web.routes import template_dir
from ashare_similarity.web.viewmodels import build_initial_view_model


def test_packaged_web_assets_exist():
    static_dir = _static_dir()
    assert static_dir.exists()
    assert (static_dir / "app.js").exists()
    assert (static_dir / "styles.css").exists()
    assert (static_dir / "vendor" / "echarts.min.js").exists()
    assert Path(template_dir).exists()
    assert (Path(template_dir) / "index.html").exists()


def test_storage_read_methods_do_not_create_registry_files(app_config):
    store = LocalDataStore(app_config)

    assert not store.db_path.exists()

    assert store.list_cached_symbols("daily") == []
    assert store.list_builds() == []
    assert store.get_build_info("daily", 10) is None
    assert store.get_latest_backfill_run("daily") is None

    assert not store.db_path.exists(), "Read-only status helpers should not create DuckDB files when no cache exists."


def test_initial_view_model_prefers_cached_daily_symbol_and_latest_date(app_config):
    store = LocalDataStore(app_config)
    runtime = type("RuntimeStub", (), {"store": store})()

    original_list_cached_symbols = store.list_cached_symbols
    original_load_bars = store.load_bars
    try:
        store.list_cached_symbols = lambda frequency: ["000333"] if frequency == "daily" else []  # type: ignore[method-assign]
        store.load_bars = lambda symbol, frequency: pd.DataFrame({"date": [pd.Timestamp("2026-04-23")]})  # type: ignore[method-assign]
        model = build_initial_view_model(runtime)
    finally:
        store.list_cached_symbols = original_list_cached_symbols  # type: ignore[method-assign]
        store.load_bars = original_load_bars  # type: ignore[method-assign]

    assert model["defaults"]["symbol"] == "000333"
    assert model["defaults"]["end_date"] == "2026-04-23"

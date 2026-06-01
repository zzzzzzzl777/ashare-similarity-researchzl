from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from ashare_similarity.prediction.frozen_forward import (
    DEFAULT_FORWARD_START,
    build_forward_gpu_probe_config,
    load_available_trading_dates,
    load_frozen_forward_protocol,
    resolve_forward_window,
    summarize_gpu_probe_config,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sample_frozen_config(tmp_path: Path) -> dict:
    artifact_dir = tmp_path / "runs" / "gpu_probe_frozen"
    _write_json(
        artifact_dir / "split_manifest.json",
        {
            "train_end": "2025-12-31",
            "validation_fraction": 0.2,
            "embargo_trading_days": 1,
        },
    )
    _write_json(
        artifact_dir / "model_card.json",
        {
            "acceptance": {
                "required_test_rows": 60000,
            }
        },
    )
    return {
        "frozen_at": "2026-05-02T00:00:00+08:00",
        "frozen_artifact_path": str(artifact_dir),
        "label": {
            "label_target": "next_high_from_close",
            "target_high_return_pct": 1.0,
        },
        "features": {
            "feature_set": "expanded",
            "exclude_feature_prefix": ["cross_"],
            "max_selected_features": 260,
            "feature_selection_method": "stable_tail",
        },
        "model": {
            "candidate_family": "all",
            "selector_coverage_weight": 0.02,
            "seed": 42,
        },
        "sample_filter": {
            "short_only": True,
            "main_board_only": True,
            "min_turnover": 3.0,
            "min_amount": 200000000,
            "min_volume_z": 1.0,
            "min_amount_z": 1.0,
            "min_range_pct": 3.0,
            "min_volatility_pct": 2.5,
            "min_phase_days_3": 1,
            "min_abnormal_flags": 2,
            "min_active_anomaly_rank": 0.0,
        },
        "acceptance_gate": {
            "accuracy_min": 0.75,
        },
        "lockbox": {
            "forward_lockbox_role": "final_unseen",
        },
    }


def test_load_available_trading_dates_prefers_market_context(tmp_path: Path) -> None:
    runtime_home = tmp_path / "runtime"
    market_context = runtime_home / "data" / "cache" / "context" / "market_context.parquet"
    market_context.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-04-30", "2026-05-06", "2026-05-07"]),
            "market_return_mean": [0.0, 0.0, 0.0],
        }
    ).to_parquet(market_context, index=False)

    dates = load_available_trading_dates(runtime_home)

    assert dates == [
        date(2026, 4, 30),
        date(2026, 5, 6),
        date(2026, 5, 7),
    ]


def test_load_available_trading_dates_unions_both_sources(tmp_path: Path) -> None:
    runtime_home = tmp_path / "runtime"

    market_context = runtime_home / "data" / "cache" / "context" / "market_context.parquet"
    market_context.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"date": pd.to_datetime(["2026-04-28", "2026-04-29", "2026-04-30"])}
    ).to_parquet(market_context, index=False)

    index_dir = runtime_home / "data" / "cache" / "market" / "daily"
    index_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"date": pd.to_datetime(["2026-04-30", "2026-05-06", "2026-05-07"])}
    ).to_parquet(index_dir / "sh000001.parquet", index=False)

    dates = load_available_trading_dates(runtime_home)

    assert date(2026, 4, 28) in dates
    assert date(2026, 4, 30) in dates
    assert date(2026, 5, 6) in dates
    assert date(2026, 5, 7) in dates
    assert dates == sorted(set(dates))


def test_resolve_forward_window_blocks_without_post_freeze_data(tmp_path: Path) -> None:
    frozen_config = _sample_frozen_config(tmp_path)

    window = resolve_forward_window(
        frozen_config,
        [date(2026, 4, 29), date(2026, 4, 30)],
    )

    assert not window.ready
    assert window.forward_test_start is None
    assert window.latest_available_date == date(2026, 4, 30)
    assert "2026-05-02" in str(window.blocked_reason)


def test_build_forward_gpu_probe_config_uses_frozen_fields(tmp_path: Path) -> None:
    frozen_config = _sample_frozen_config(tmp_path)
    protocol = load_frozen_forward_protocol(frozen_config)
    window = resolve_forward_window(
        frozen_config,
        [date(2026, 4, 30), date(2026, 5, 6), date(2026, 5, 7)],
    )

    probe_config = build_forward_gpu_probe_config(frozen_config, protocol, window)

    assert probe_config.start == DEFAULT_FORWARD_START
    assert probe_config.train_end == date(2025, 12, 31)
    assert probe_config.test_start == date(2026, 5, 6)
    assert probe_config.end == date(2026, 5, 7)
    assert probe_config.test_rows == 60000
    assert probe_config.feature_set == "expanded"
    assert probe_config.exclude_feature_prefix == ("cross_",)
    assert probe_config.lockbox_role == "final_unseen"
    assert probe_config.min_phase_days_3 == 1
    assert probe_config.target_accuracy == 0.75
    assert probe_config.exclude_event_limit_up is False


def test_summary_shows_exclude_event_limit_up_code_default(tmp_path: Path) -> None:
    frozen_config = _sample_frozen_config(tmp_path)
    protocol = load_frozen_forward_protocol(frozen_config)
    window = resolve_forward_window(
        frozen_config,
        [date(2026, 4, 30), date(2026, 5, 6), date(2026, 5, 7)],
    )
    probe_config = build_forward_gpu_probe_config(frozen_config, protocol, window)
    summary = summarize_gpu_probe_config(probe_config, frozen_config=frozen_config)

    assert summary["exclude_event_limit_up"] is False
    assert summary["exclude_event_limit_up_source"] == "frozen_config_absent_legacy_false"


def test_summary_shows_exclude_event_limit_up_from_frozen_config(tmp_path: Path) -> None:
    frozen_config = _sample_frozen_config(tmp_path)
    frozen_config["sample_filter"]["exclude_event_limit_up"] = False
    protocol = load_frozen_forward_protocol(frozen_config)
    window = resolve_forward_window(
        frozen_config,
        [date(2026, 4, 30), date(2026, 5, 6), date(2026, 5, 7)],
    )
    probe_config = build_forward_gpu_probe_config(frozen_config, protocol, window)
    summary = summarize_gpu_probe_config(probe_config, frozen_config=frozen_config)

    assert summary["exclude_event_limit_up"] is False
    assert summary["exclude_event_limit_up_source"] == "frozen_config"
    assert probe_config.exclude_event_limit_up is False

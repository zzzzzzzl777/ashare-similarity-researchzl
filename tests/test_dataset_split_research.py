from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


def _load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_dataset_split_research.py"
    spec = importlib.util.spec_from_file_location("run_dataset_split_research", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sample_protocol_frame() -> pd.DataFrame:
    dates = pd.date_range("2023-06-09", "2024-03-31", freq="B")
    rows = []
    for symbol in ("000001", "000002"):
        for label_date in dates:
            rows.append(
                {
                    "symbol": symbol,
                    "date": label_date - pd.Timedelta(days=1),
                    "label_date": label_date,
                    "_filter_pass": True,
                    "_actual": 1.0,
                }
            )
    return pd.DataFrame(rows)


def test_fixed_start_before_cache_is_marked_truncated(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "DEV_OUTER_START", pd.Timestamp("2024-01-01"))
    monkeypatch.setattr(module, "DEV_OUTER_END", pd.Timestamp("2024-03-31"))
    monkeypatch.setattr(module, "MIN_FIT_ROWS", 1)
    monkeypatch.setattr(module, "MIN_INNER_ROWS", 1)
    monkeypatch.setattr(module, "MIN_OUTER_ROWS", 1)

    frame = _sample_protocol_frame()
    manifest = module.build_split_manifest(
        frame,
        pd.Timestamp("2023-06-09"),
        embargo_days=1,
    )

    fixed_start = manifest[
        (manifest["scheme"] == "fixed_start_2020")
        & (manifest["outer_valid_months"] == 3)
        & (manifest["outer_fold"] == 1)
    ].iloc[0]
    expanding = manifest[
        (manifest["scheme"] == "expanding_from_fair_start")
        & (manifest["outer_valid_months"] == 3)
        & (manifest["outer_fold"] == 1)
    ].iloc[0]

    assert bool(fixed_start["history_truncated_by_cache"]) is True
    assert bool(fixed_start["eligible_for_protocol"]) is False
    assert "requested_history_before_cache_start" in fixed_start["ineligibility_reason"]
    assert bool(expanding["history_truncated_by_cache"]) is False
    assert bool(expanding["eligible_for_protocol"]) is True

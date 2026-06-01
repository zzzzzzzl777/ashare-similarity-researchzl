from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import pandas as pd


def _load_history_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "update_1457_history.py"
    spec = importlib.util.spec_from_file_location("update_1457_history_under_test", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_snapshot(path: Path, *, quote_date: str, quote_time: str) -> None:
    pd.DataFrame(
        {
            "symbol": ["000001"],
            "quote_date": [quote_date],
            "quote_time": [quote_time],
            "high": [11.0],
            "latest_price": [10.5],
        }
    ).to_parquet(path, index=False)


def test_postclose_snapshot_calendar_excludes_intraday_misdated_files(tmp_path, monkeypatch):
    history = _load_history_module()
    monkeypatch.setattr(history, "REALTIME_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(history, "MARKET_INDEX_PATH", tmp_path / "missing_market.parquet")
    monkeypatch.setattr(history, "TUSHARE_STK_FACTOR_DIR", tmp_path / "missing_tushare")
    history._POSTCLOSE_SNAPSHOT_CACHE.clear()
    history._POSTCLOSE_SNAPSHOT_VALID_CACHE.clear()

    bogus = tmp_path / "sina_snapshot_postclose_20260517_102847.parquet"
    valid_18 = tmp_path / "sina_snapshot_postclose_20260518_151059.parquet"
    valid_19 = tmp_path / "sina_snapshot_postclose_20260519_164100.parquet"
    _write_snapshot(bogus, quote_date="2026-05-18", quote_time="10:28:36")
    _write_snapshot(valid_18, quote_date="2026-05-18", quote_time="15:00:00")
    _write_snapshot(valid_19, quote_date="2026-05-19", quote_time="15:00:00")

    assert history._is_valid_postclose_snapshot(bogus, date(2026, 5, 17)) is False
    assert history._is_valid_postclose_snapshot(valid_18, date(2026, 5, 18)) is True
    assert history._postclose_snapshot_path(date(2026, 5, 18)) == valid_18

    next_day = history._load_calendar_next_day()

    assert date(2026, 5, 17) not in next_day
    assert next_day == {date(2026, 5, 18): date(2026, 5, 19)}


def test_formal_rows_are_used_only_when_postclose_date_is_absent(tmp_path, monkeypatch):
    history = _load_history_module()
    monkeypatch.setattr(history, "REALTIME_OUTPUT_DIR", tmp_path)

    selector_path = tmp_path / "realtime_1457_m1457_selector_top6_20260528_141344.csv"
    pd.DataFrame(
        {
            "symbol": ["600707"],
            "name": ["彩虹股份"],
            "probability": ["0.7888889"],
            "latest_price": ["10.87"],
            "turnover_today": ["8.0"],
        }
    ).to_csv(selector_path, index=False, encoding="utf-8-sig")
    timing_path = tmp_path / "realtime_1457_m1457_timing_20260528_141344.json"
    timing_path.write_text(
        json.dumps(
            {
                "target_date": "2026-05-28",
                "run_mode": "formal",
                "selector": {"selector_csv": str(selector_path)},
                "live_results": {
                    "run_mode": "formal",
                    "status": "ok",
                    "is_formal_valid": True,
                    "snapshot_time_status": "verified",
                    "output_grade": "approximated_1457",
                },
            }
        ),
        encoding="utf-8",
    )

    rows = history._formal_rows({}, exclude_date_keys=set())

    assert len(rows) == 1
    assert rows.iloc[0]["date"] == "2026/5/28"
    assert rows.iloc[0]["source"] == "formal_1457"
    assert rows.iloc[0]["run_id"] == "20260528_141344"

    excluded = history._formal_rows({}, exclude_date_keys={"2026-05-28"})

    assert excluded.empty

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from ashare_similarity.data.base import SecurityProfile
from ashare_similarity.schemas import BackfillStatus


def _make_status(
    *,
    status: str,
    attempted_symbols: int,
    completed_symbols: int,
    failed_symbols: int,
    remaining_symbols: int,
    resume_cursor: int,
    retry_failures: bool = False,
) -> BackfillStatus:
    return BackfillStatus(
        run_id="run-001",
        frequency="daily",
        status=status,
        batch_size=10,
        requested_symbols=200,
        attempted_symbols=attempted_symbols,
        completed_symbols=completed_symbols,
        failed_symbols=failed_symbols,
        skipped_recent_listing=0,
        ignored_st_symbols=0,
        remaining_symbols=remaining_symbols,
        processed_count=completed_symbols,
        cursor=resume_cursor,
        next_cursor=resume_cursor,
        resume_cursor=resume_cursor,
        started_at=datetime(2026, 4, 23, 9, 30, 0),
        finished_at=None if status != "completed" else datetime(2026, 4, 23, 9, 35, 0),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        last_symbol="000001",
        retry_failures=retry_failures,
        sample_failures=[],
    )


def test_backfill_loop_runs_multiple_rounds_and_applies_retry_cadence(
    monkeypatch,
    app_config,
    load_public_attr,
    stub_factory,
):
    store_cls = load_public_attr("ashare_similarity.data.storage", "LocalDataStore")
    service_cls = load_public_attr("ashare_similarity.data.service", "DataService")
    store = store_cls(app_config)

    universe = pd.DataFrame(
        {
            "symbol": ["000001", "000002"],
            "name": ["PingAn", "Vanke"],
            "is_st": [False, False],
        }
    )

    provider = stub_factory(handlers={"get_frequency_notice": lambda frequency: None})
    universe_service = stub_factory(
        handlers={
            "get_filtered_universe": lambda: universe.copy(),
            "get_universe": lambda: universe.copy(),
            "get_listing_days": lambda symbol, as_of=None: 365,
            "get_profile": lambda symbol: SecurityProfile(
                symbol=symbol,
                name=f"Synthetic-{symbol}",
                industry="finance",
                listing_date=date(2020, 1, 1),
                is_st=False,
            ),
        }
    )
    context_service = stub_factory(
        handlers={
            "refresh_market_context": lambda *args, **kwargs: pd.DataFrame(),
            "build_industry_context": lambda *args, **kwargs: pd.DataFrame(),
        }
    )
    service = service_cls(app_config, store, provider, universe_service, context_service)

    statuses = [
        _make_status(
            status="partial",
            attempted_symbols=20,
            completed_symbols=12,
            failed_symbols=8,
            remaining_symbols=180,
            resume_cursor=20,
            retry_failures=False,
        ),
        _make_status(
            status="completed",
            attempted_symbols=40,
            completed_symbols=32,
            failed_symbols=8,
            remaining_symbols=0,
            resume_cursor=40,
            retry_failures=True,
        ),
    ]

    calls: list[dict[str, object]] = []
    sleep_calls: list[float] = []

    def fake_backfill_market_data(**kwargs):
        calls.append(kwargs)
        current_status = statuses[len(calls) - 1]
        return {
            "resume_used": len(calls) > 1,
            "symbols_scheduled_this_invocation": 20,
            "latest_status": current_status.model_dump(mode="json"),
        }

    def fake_get_backfill_status(*, run_id=None, frequency=None):
        if not calls:
            return None
        return statuses[min(len(calls) - 1, len(statuses) - 1)]

    monkeypatch.setattr(service, "backfill_market_data", fake_backfill_market_data)
    monkeypatch.setattr(service, "get_backfill_status", fake_get_backfill_status)

    summary = service.run_backfill_loop(
        frequency="daily",
        batch_size=10,
        max_symbols_per_round=20,
        max_rounds=5,
        round_interval_seconds=0.25,
        retry_failures_every=2,
        stop_after_idle_rounds=2,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        resume=True,
        sleep_fn=sleep_calls.append,
    )

    assert len(calls) == 2, "The loop should stop once the underlying backfill reports completion."
    assert calls[0]["retry_failures"] is False
    assert calls[1]["retry_failures"] is True, "Retry cadence should activate on the configured round."
    assert summary["rounds_completed"] == 2
    assert summary["stop_reason"] == "completed"
    assert summary["latest_status"]["run_id"] == "run-001"
    assert summary["rounds"][1]["continued_run"] is True, "Later rounds should continue the same persisted backfill run."
    assert sleep_calls == [0.25], "The loop should only sleep between rounds that actually continue."

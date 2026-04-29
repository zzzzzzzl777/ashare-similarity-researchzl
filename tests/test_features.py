from __future__ import annotations

import numpy as np
import pytest


def _build_feature_service(feature_service_cls, app_config, stub_factory, frame, context_frame):
    try:
        return feature_service_cls(
            app_config,
            stub_factory(default=lambda *args, **kwargs: None),
            stub_factory(default=lambda *args, **kwargs: frame),
            stub_factory(default=lambda *args, **kwargs: context_frame),
        )
    except TypeError as exc:  # pragma: no cover - exercised only when the integration surface changes
        pytest.fail(
            "FeatureService constructor no longer matches the runtime contract "
            "`FeatureService(config, store, data_service, context_service)`. "
            f"Current error: {exc}"
        )


def test_build_feature_frame_creates_one_row_per_eligible_window(
    app_config,
    load_public_attr,
    stub_factory,
    make_ohlcv_frame,
    make_context_frame,
    invoke_with_supported_kwargs,
    as_records,
    to_iso_date,
):
    feature_service_cls = load_public_attr("ashare_similarity.features.service", "FeatureService")
    frame = make_ohlcv_frame(symbol="000001", start="2024-01-02", periods=8, pattern="query")
    context_frame = make_context_frame(frame)
    service = _build_feature_service(feature_service_cls, app_config, stub_factory, frame, context_frame)

    build_feature_frame = getattr(service, "build_feature_frame", None)
    if not callable(build_feature_frame):
        pytest.fail("FeatureService must expose `build_feature_frame(...)` as its public feature entrypoint.")

    result = invoke_with_supported_kwargs(
        build_feature_frame,
        frequency="daily",
        window_size=5,
        symbols=["000001"],
        start_date=frame["date"].iloc[0].date(),
        end_date=frame["date"].iloc[-1].date(),
    )
    rows = sorted(as_records(result), key=lambda row: str(row.get("end_date")))

    assert len(rows) == 4, "8 bars with a 5-bar rolling window should produce 4 eligible windows."
    assert {row.get("symbol") for row in rows} == {"000001"}
    assert all("start_date" in row for row in rows), "Feature rows must carry `start_date` for downstream search output."
    assert all("end_date" in row for row in rows), "Feature rows must carry `end_date` for downstream search output."
    assert to_iso_date(rows[0]["start_date"]) == to_iso_date(frame["date"].iloc[0])
    assert to_iso_date(rows[-1]["end_date"]) == to_iso_date(frame["date"].iloc[-1])


def test_build_feature_frame_filters_dirty_windows_without_future_leakage(
    app_config,
    load_public_attr,
    stub_factory,
    make_ohlcv_frame,
    make_context_frame,
    invoke_with_supported_kwargs,
    as_records,
    to_iso_date,
):
    feature_service_cls = load_public_attr("ashare_similarity.features.service", "FeatureService")
    frame = make_ohlcv_frame(symbol="000001", start="2024-01-02", periods=8, pattern="query")
    frame.loc[2, "close"] = np.nan
    context_frame = make_context_frame(frame)
    service = _build_feature_service(feature_service_cls, app_config, stub_factory, frame, context_frame)

    build_feature_frame = getattr(service, "build_feature_frame", None)
    if not callable(build_feature_frame):
        pytest.fail("FeatureService must expose `build_feature_frame(...)` as its public feature entrypoint.")

    result = invoke_with_supported_kwargs(
        build_feature_frame,
        frequency="daily",
        window_size=4,
        symbols=["000001"],
        start_date=frame["date"].iloc[0].date(),
        end_date=frame["date"].iloc[-1].date(),
    )
    rows = sorted(as_records(result), key=lambda row: str(row.get("end_date")))

    assert rows, "Feature builder should keep clean trailing windows even when earlier windows are dirty."
    assert all("end_date" in row for row in rows), "Feature rows must carry `end_date` for quality and leakage checks."

    actual_end_dates = [to_iso_date(row["end_date"]) for row in rows]
    expected_end_dates = [
        to_iso_date(frame["date"].iloc[6]),
        to_iso_date(frame["date"].iloc[7]),
    ]
    assert actual_end_dates == expected_end_dates, (
        "Windows that include NaN bars should be filtered out, but the terminal clean window "
        "must still be produced without requiring any future bars."
    )


def test_build_query_frame_can_run_in_read_only_mode_without_remote_fetch(
    app_config,
    load_public_attr,
    stub_factory,
    make_ohlcv_frame,
    make_context_frame,
):
    feature_service_cls = load_public_attr("ashare_similarity.features.service", "FeatureService")
    frame = make_ohlcv_frame(symbol="000333", start="2026-04-10", periods=12, pattern="query")
    context_frame = make_context_frame(frame)
    captured = {"ensure_remote": None}

    def load_price_history(**kwargs):
        captured["ensure_remote"] = kwargs.get("ensure_remote")
        return frame

    class Profile:
        symbol = "000333"
        name = "Synthetic-000333"
        industry = "appliance"
        listing_date = None
        is_st = False

    data_service = stub_factory(
        handlers={
            "load_price_history": load_price_history,
            "get_security_profile": lambda symbol: Profile(),
        }
    )
    context_service = stub_factory(
        handlers={
            "get_market_context": lambda: context_frame,
            "get_industry_context": lambda: context_frame.assign(industry="appliance"),
        }
    )
    service = feature_service_cls(app_config, stub_factory(default=lambda *args, **kwargs: None), data_service, context_service)

    result = service.build_query_frame(
        symbol="000333",
        end_date=frame["date"].iloc[-1].date(),
        frequency="daily",
        window_size=10,
        ensure_remote=False,
    )

    assert captured["ensure_remote"] is False
    assert result.symbol == "000333"
    assert result.window_size == 10


def test_build_feature_frame_keeps_recent_listing_windows_when_bars_are_long_enough(
    app_config,
    load_public_attr,
    stub_factory,
    make_ohlcv_frame,
    make_context_frame,
    invoke_with_supported_kwargs,
    as_records,
):
    app_config.quality.min_listing_days = 120
    feature_service_cls = load_public_attr("ashare_similarity.features.service", "FeatureService")
    frame = make_ohlcv_frame(symbol="301001", start="2024-01-02", periods=25, pattern="query")
    context_frame = make_context_frame(frame)

    class Profile:
        symbol = "301001"
        name = "Synthetic-301001"
        industry = "growth"
        listing_date = None
        is_st = False

    data_service = stub_factory(
        handlers={
            "load_price_history": lambda **kwargs: frame,
            "get_security_profile": lambda symbol: Profile(),
        }
    )
    data_service.universe_service = stub_factory(handlers={"get_listing_days": lambda symbol, as_of=None: 25})
    context_service = stub_factory(
        handlers={
            "get_market_context": lambda: context_frame,
            "get_industry_context": lambda: context_frame.assign(industry="growth"),
        }
    )
    service = feature_service_cls(app_config, stub_factory(default=lambda *args, **kwargs: None), data_service, context_service)

    result = invoke_with_supported_kwargs(
        service.build_feature_frame,
        frequency="daily",
        window_size=20,
        symbols=["301001"],
        start_date=frame["date"].iloc[0].date(),
        end_date=frame["date"].iloc[-1].date(),
    )

    rows = as_records(result)
    assert len(rows) == 6, "Recent listings with enough bars should still contribute eligible rolling windows."

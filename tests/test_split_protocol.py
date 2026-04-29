from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from ashare_similarity.prediction.split_protocol import (
    SplitProtocolConfig,
    SplitProtocolError,
    assert_no_purged_overlap,
    build_official_splits,
)


def test_build_official_splits_uses_time_order_and_trading_day_embargo():
    dates = pd.bdate_range("2024-01-02", periods=45)
    frame = pd.DataFrame(
        {
            "symbol": ["600001"] * len(dates),
            "date": dates,
            "label_date": dates + pd.offsets.BDay(1),
            "actual": np.arange(len(dates)) % 2,
        }
    )

    fit, valid, lockbox, manifest = build_official_splits(
        frame,
        SplitProtocolConfig(
            train_end=date(2024, 2, 8),
            test_start=date(2024, 2, 15),
            end=date(2024, 3, 5),
            validation_fraction=0.25,
            embargo_trading_days=2,
        ),
    )

    assert not fit.empty
    assert not valid.empty
    assert not lockbox.empty
    assert_no_purged_overlap(fit, valid)
    assert manifest.row_split_fallback_used is False
    assert manifest.to_dict()["split_hash"]
    assert pd.to_datetime(fit["label_date"]).max() < pd.to_datetime(valid["label_date"]).min()
    assert pd.to_datetime(lockbox["date"]).min().date() >= date(2024, 2, 15)


def test_build_official_splits_rejects_overlapping_lockbox_dates():
    with pytest.raises(SplitProtocolError):
        build_official_splits(
            pd.DataFrame({"date": ["2024-01-02"], "label_date": ["2024-01-03"]}),
            SplitProtocolConfig(
                train_end=date(2024, 2, 1),
                test_start=date(2024, 2, 1),
                end=date(2024, 2, 8),
            ),
        )

from __future__ import annotations

import pandas as pd
import pytest

from ashare_similarity.prediction.level2_importer import import_level2_file
from ashare_similarity.prediction.level2_schema import Level2SchemaError, validate_level2_frame


def test_validate_level2_orderbook_schema_normalizes_symbol_and_timestamp():
    frame = validate_level2_frame(
        pd.DataFrame(
            {
                "symbol": ["1"],
                "timestamp": ["2024-01-02 09:30:00"],
                "bid_price_1": [10.0],
                "bid_volume_1": [1000],
                "ask_price_1": [10.01],
                "ask_volume_1": [1200],
            }
        ),
        "orderbook",
    )

    assert frame.loc[0, "symbol"] == "000001"
    assert str(frame.attrs["level2_table"]) == "orderbook"


def test_validate_level2_schema_reports_missing_required_columns():
    with pytest.raises(Level2SchemaError):
        validate_level2_frame(pd.DataFrame({"symbol": ["600001"]}), "trades")


def test_import_level2_file_reads_csv_and_returns_metadata(tmp_path):
    path = tmp_path / "trades.csv"
    pd.DataFrame(
        {
            "symbol": ["600001"],
            "timestamp": ["2024-01-02 09:31:00"],
            "price": [10.2],
            "volume": [300],
            "amount": [3060.0],
            "side": ["B"],
        }
    ).to_csv(path, index=False)

    frame, metadata = import_level2_file(path, table="trades")

    assert len(frame) == 1
    assert metadata["table"] == "trades"
    assert metadata["source"] == "local_file"

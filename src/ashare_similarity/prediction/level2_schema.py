from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


class Level2SchemaError(ValueError):
    """Raised when a local Level2 file does not match the standard schema."""


@dataclass(frozen=True, slots=True)
class Level2Schema:
    table: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...] = ()


LEVEL2_SCHEMAS: dict[str, Level2Schema] = {
    "orderbook": Level2Schema(
        table="orderbook",
        required_columns=(
            "symbol",
            "timestamp",
            "bid_price_1",
            "bid_volume_1",
            "ask_price_1",
            "ask_volume_1",
        ),
        optional_columns=tuple(
            item
            for level in range(2, 11)
            for item in (
                f"bid_price_{level}",
                f"bid_volume_{level}",
                f"ask_price_{level}",
                f"ask_volume_{level}",
            )
        ),
    ),
    "trades": Level2Schema(
        table="trades",
        required_columns=("symbol", "timestamp", "price", "volume", "amount", "side"),
        optional_columns=("trade_id", "order_id", "buyer_order_id", "seller_order_id"),
    ),
    "auction": Level2Schema(
        table="auction",
        required_columns=("symbol", "timestamp", "indicative_price", "matched_volume", "unmatched_volume"),
        optional_columns=("side", "auction_phase", "amount"),
    ),
}


def validate_level2_frame(frame: pd.DataFrame, table: str) -> pd.DataFrame:
    table = str(table).strip().lower()
    schema = LEVEL2_SCHEMAS.get(table)
    if schema is None:
        raise Level2SchemaError(f"Unsupported Level2 table `{table}`. Expected one of {sorted(LEVEL2_SCHEMAS)}.")
    missing = [column for column in schema.required_columns if column not in frame.columns]
    if missing:
        raise Level2SchemaError(f"Level2 `{table}` missing required columns: {missing}")
    out = frame.copy()
    out["symbol"] = out["symbol"].astype(str).str.zfill(6)
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    out = out.dropna(subset=["symbol", "timestamp"]).sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    for column in _numeric_columns(schema):
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    out.attrs["level2_table"] = table
    out.attrs["level2_schema"] = schema
    return out


def describe_level2_schema(table: str | None = None) -> dict[str, Any]:
    if table is not None:
        schema = LEVEL2_SCHEMAS[str(table).strip().lower()]
        return _schema_payload(schema)
    return {name: _schema_payload(schema) for name, schema in LEVEL2_SCHEMAS.items()}


def _schema_payload(schema: Level2Schema) -> dict[str, Any]:
    return {
        "table": schema.table,
        "required_columns": list(schema.required_columns),
        "optional_columns": list(schema.optional_columns),
    }


def _numeric_columns(schema: Level2Schema) -> tuple[str, ...]:
    return tuple(
        column
        for column in [*schema.required_columns, *schema.optional_columns]
        if column != "symbol" and column != "timestamp" and not column.endswith("_id") and column not in {"side", "auction_phase"}
    )

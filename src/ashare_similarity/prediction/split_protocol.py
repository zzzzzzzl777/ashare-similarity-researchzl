from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

import pandas as pd


class SplitProtocolError(ValueError):
    """Raised when the official time-series split cannot be created safely."""


@dataclass(frozen=True, slots=True)
class SplitProtocolConfig:
    train_end: date
    test_start: date
    end: date
    validation_fraction: float = 0.20
    embargo_trading_days: int = 1
    max_fit_rows: int | None = None
    seed: int = 42
    date_col: str = "date"
    label_end_col: str = "label_date"
    symbol_col: str = "symbol"
    allow_row_split_fallback: bool = False


@dataclass(frozen=True, slots=True)
class SplitManifest:
    protocol: str
    train_end: str
    test_start: str
    end: str
    validation_fraction: float
    embargo_trading_days: int
    train_window_rows: int
    fit_rows: int
    validation_rows: int
    lockbox_rows: int
    validation_start: str | None
    embargo_start: str | None
    fit_label_end: str | None
    validation_label_start: str | None
    lockbox_event_start: str | None
    lockbox_event_end: str | None
    row_split_fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["split_hash"] = self.split_hash()
        return payload

    def split_hash(self) -> str:
        raw = json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_official_splits(
    frame: pd.DataFrame,
    config: SplitProtocolConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, SplitManifest]:
    """Build dev_train/dev_valid/test_lockbox with trading-day purge/embargo."""
    _validate_config(config)
    prepared = _prepare_frame(frame, date_col=config.date_col, label_end_col=config.label_end_col)
    train_window = prepared[prepared[config.label_end_col].dt.date <= config.train_end].copy()
    lockbox = prepared[
        (prepared[config.date_col].dt.date >= config.test_start)
        & (prepared[config.label_end_col].dt.date <= config.end)
    ].copy()
    fit, valid, split_info = purged_train_validation_split(train_window, config)
    manifest = SplitManifest(
        protocol="dev_train_dev_valid_test_lockbox_v1",
        train_end=config.train_end.isoformat(),
        test_start=config.test_start.isoformat(),
        end=config.end.isoformat(),
        validation_fraction=float(split_info["validation_fraction"]),
        embargo_trading_days=int(config.embargo_trading_days),
        train_window_rows=int(len(train_window)),
        fit_rows=int(len(fit)),
        validation_rows=int(len(valid)),
        lockbox_rows=int(len(lockbox)),
        validation_start=split_info.get("validation_start"),
        embargo_start=split_info.get("embargo_start"),
        fit_label_end=split_info.get("fit_label_end"),
        validation_label_start=split_info.get("validation_label_start"),
        lockbox_event_start=_date_min(lockbox, config.date_col),
        lockbox_event_end=_date_max(lockbox, config.date_col),
        row_split_fallback_used=bool(split_info.get("row_split_fallback_used", False)),
    )
    return fit, valid, lockbox.reset_index(drop=True), manifest


def purged_train_validation_split(
    train_window: pd.DataFrame,
    config: SplitProtocolConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    frame = _prepare_frame(train_window, date_col=config.date_col, label_end_col=config.label_end_col)
    sort_cols = [config.label_end_col, config.date_col]
    if config.symbol_col in frame.columns:
        sort_cols.append(config.symbol_col)
    frame = frame.sort_values(sort_cols).reset_index(drop=True)
    if len(frame) < 3:
        raise SplitProtocolError("Need at least 3 training-window rows for an official purged split.")

    fraction = min(max(float(config.validation_fraction), 0.05), 0.50)
    unique_label_dates = pd.Index(frame[config.label_end_col].dt.normalize().unique()).sort_values()
    if len(unique_label_dates) < 3:
        raise SplitProtocolError("Need at least 3 unique label dates for an official purged split.")

    split_index = min(max(int(len(unique_label_dates) * (1.0 - fraction)), 1), len(unique_label_dates) - 1)
    validation_start = pd.Timestamp(unique_label_dates[split_index])
    embargo_index = max(split_index - max(int(config.embargo_trading_days), 0), 0)
    embargo_start = pd.Timestamp(unique_label_dates[embargo_index])

    fit = frame[frame[config.label_end_col] < embargo_start].copy()
    valid = frame[frame[config.label_end_col] >= validation_start].copy()
    if fit.empty or valid.empty:
        if not config.allow_row_split_fallback:
            raise SplitProtocolError(
                "Official split produced an empty fit or validation set; row split fallback is disabled."
            )
        row_split = min(max(int(len(frame) * (1.0 - fraction)), 1), len(frame) - 1)
        fit = frame.iloc[:row_split].copy()
        valid = frame.iloc[row_split:].copy()
        validation_start = pd.Timestamp(valid[config.label_end_col].min())
        embargo_start = validation_start
        fallback_used = True
    else:
        fallback_used = False

    if config.max_fit_rows is not None and len(fit) > int(config.max_fit_rows):
        fit = (
            fit.sample(n=int(config.max_fit_rows), random_state=int(config.seed) + 1)
            .sort_values(sort_cols)
            .reset_index(drop=True)
        )

    info = {
        "train_window_rows": int(len(frame)),
        "fit_rows": int(len(fit)),
        "validation_rows": int(len(valid)),
        "validation_fraction": float(fraction),
        "validation_start": validation_start.date().isoformat(),
        "validation_label_start": pd.Timestamp(valid[config.label_end_col].min()).date().isoformat(),
        "fit_label_end": pd.Timestamp(fit[config.label_end_col].max()).date().isoformat(),
        "embargo_start": embargo_start.date().isoformat(),
        "embargo_trading_days": int(config.embargo_trading_days),
        "max_fit_rows": int(config.max_fit_rows) if config.max_fit_rows is not None else None,
        "row_split_fallback_used": bool(fallback_used),
    }
    return fit.reset_index(drop=True), valid.reset_index(drop=True), info


def assert_no_purged_overlap(
    fit: pd.DataFrame,
    valid: pd.DataFrame,
    *,
    label_end_col: str = "label_date",
) -> None:
    if fit.empty or valid.empty:
        raise SplitProtocolError("Cannot validate purge overlap on empty split frames.")
    fit_label_end = pd.to_datetime(fit[label_end_col], errors="coerce").max()
    valid_label_start = pd.to_datetime(valid[label_end_col], errors="coerce").min()
    if pd.isna(fit_label_end) or pd.isna(valid_label_start) or fit_label_end >= valid_label_start:
        raise SplitProtocolError("Purged split still has overlapping fit/validation label windows.")


def _prepare_frame(frame: pd.DataFrame, *, date_col: str, label_end_col: str) -> pd.DataFrame:
    missing = [column for column in (date_col, label_end_col) if column not in frame.columns]
    if missing:
        raise SplitProtocolError(f"Missing split column(s): {missing}")
    out = frame.copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out[label_end_col] = pd.to_datetime(out[label_end_col], errors="coerce")
    out = out.dropna(subset=[date_col, label_end_col])
    if out.empty:
        raise SplitProtocolError("No rows remain after parsing split dates.")
    return out


def _validate_config(config: SplitProtocolConfig) -> None:
    if config.train_end >= config.test_start:
        raise SplitProtocolError("train_end must be earlier than test_start.")
    if config.test_start > config.end:
        raise SplitProtocolError("test_start must be on or before end.")


def _date_min(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _date_max(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()

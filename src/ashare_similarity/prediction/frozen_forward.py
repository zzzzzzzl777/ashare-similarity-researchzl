from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from ashare_similarity.prediction.gpu_probe import GpuProbeConfig


DEFAULT_FORWARD_START = date(2023, 5, 1)
DEFAULT_FORWARD_TEST_ROWS = 60_000
DEFAULT_MARKET_INDEX_SYMBOL = "sh000001"


@dataclass(slots=True, frozen=True)
class FrozenForwardProtocol:
    start: date
    train_end: date
    required_test_rows: int
    validation_fraction: float
    embargo_label_days: int
    frozen_artifact_path: Path


@dataclass(slots=True, frozen=True)
class ForwardWindow:
    frozen_at: date
    forward_test_start: date | None
    forward_end: date | None
    latest_available_date: date | None
    blocked_reason: str | None = None

    @property
    def ready(self) -> bool:
        return (
            self.blocked_reason is None
            and self.forward_test_start is not None
            and self.forward_end is not None
        )


def _parse_iso_date(value: str) -> date:
    text = str(value).strip()
    if len(text) < 10:
        raise ValueError(f"Expected ISO date-like value, got {value!r}")
    return date.fromisoformat(text[:10])


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_frozen_forward_config(path: Path) -> dict[str, Any]:
    return _load_json(path)


def load_frozen_forward_protocol(
    frozen_config: Mapping[str, Any],
    *,
    default_start: date = DEFAULT_FORWARD_START,
) -> FrozenForwardProtocol:
    artifact_path = Path(str(frozen_config["frozen_artifact_path"])).expanduser().resolve()
    split_manifest = _load_json(artifact_path / "split_manifest.json")
    model_card = _load_json(artifact_path / "model_card.json")
    acceptance = model_card.get("acceptance") or {}
    return FrozenForwardProtocol(
        start=default_start,
        train_end=_parse_iso_date(str(split_manifest["train_end"])),
        required_test_rows=int(acceptance.get("required_test_rows", DEFAULT_FORWARD_TEST_ROWS)),
        validation_fraction=float(split_manifest.get("validation_fraction", 0.20)),
        embargo_label_days=int(split_manifest.get("embargo_trading_days", 1)),
        frozen_artifact_path=artifact_path,
    )


def _load_dates_from_parquet(path: Path) -> list[date]:
    if not path.exists():
        return []
    frame = pd.read_parquet(path, columns=["date"])
    if "date" not in frame.columns or frame.empty:
        return []
    timestamps = pd.to_datetime(frame["date"], errors="coerce").dropna()
    return sorted({timestamp.date() for timestamp in timestamps})


def load_available_trading_dates(runtime_home: Path) -> list[date]:
    runtime_root = Path(runtime_home).expanduser().resolve()
    market_context_path = runtime_root / "data" / "cache" / "context" / "market_context.parquet"
    market_index_path = (
        runtime_root
        / "data"
        / "cache"
        / "market"
        / "daily"
        / f"{DEFAULT_MARKET_INDEX_SYMBOL}.parquet"
    )
    all_dates: set[date] = set()
    all_dates.update(_load_dates_from_parquet(market_context_path))
    all_dates.update(_load_dates_from_parquet(market_index_path))
    return sorted(all_dates)


def resolve_forward_window(
    frozen_config: Mapping[str, Any],
    trading_dates: Sequence[date],
) -> ForwardWindow:
    frozen_at = _parse_iso_date(str(frozen_config["frozen_at"]))
    dates = sorted(set(trading_dates))
    latest = dates[-1] if dates else None
    if not dates:
        return ForwardWindow(
            frozen_at=frozen_at,
            forward_test_start=None,
            forward_end=None,
            latest_available_date=None,
            blocked_reason="No cached trading dates were found.",
        )
    post_freeze_dates = [value for value in dates if value > frozen_at]
    if not post_freeze_dates:
        return ForwardWindow(
            frozen_at=frozen_at,
            forward_test_start=None,
            forward_end=None,
            latest_available_date=latest,
            blocked_reason=(
                f"No post-freeze trading date is available after {frozen_at.isoformat()}."
            ),
        )
    return ForwardWindow(
        frozen_at=frozen_at,
        forward_test_start=post_freeze_dates[0],
        forward_end=post_freeze_dates[-1],
        latest_available_date=latest,
    )


def build_forward_gpu_probe_config(
    frozen_config: Mapping[str, Any],
    protocol: FrozenForwardProtocol,
    window: ForwardWindow,
) -> GpuProbeConfig:
    if not window.ready:
        raise ValueError(f"Forward window is not ready: {window.blocked_reason}")
    features = dict(frozen_config.get("features") or {})
    model = dict(frozen_config.get("model") or {})
    label = dict(frozen_config.get("label") or {})
    sample_filter = dict(frozen_config.get("sample_filter") or {})
    acceptance_gate = dict(frozen_config.get("acceptance_gate") or {})
    lockbox = dict(frozen_config.get("lockbox") or {})
    exclude_prefix = tuple(str(value) for value in (features.get("exclude_feature_prefix") or []))
    _elu_value = sample_filter.get("exclude_event_limit_up")
    if _elu_value is None:
        _elu_value = features.get("exclude_event_limit_up")
    exclude_event_limit_up = bool(_elu_value) if _elu_value is not None else False
    return GpuProbeConfig(
        start=protocol.start,
        train_end=protocol.train_end,
        test_start=window.forward_test_start,
        end=window.forward_end,
        test_rows=protocol.required_test_rows,
        seed=int(model.get("seed", 42)),
        target_accuracy=float(acceptance_gate.get("accuracy_min", 0.75)),
        validation_fraction=float(protocol.validation_fraction),
        embargo_label_days=int(protocol.embargo_label_days),
        short_only=bool(sample_filter.get("short_only", True)),
        min_turnover=float(sample_filter.get("min_turnover", 3.0)),
        min_amount=float(sample_filter.get("min_amount", 200_000_000.0)),
        min_volume_z=float(sample_filter.get("min_volume_z", 1.0)),
        min_amount_z=float(sample_filter.get("min_amount_z", 1.0)),
        min_range_pct=float(sample_filter.get("min_range_pct", 3.0)),
        min_volatility_pct=float(sample_filter.get("min_volatility_pct", 2.5)),
        min_abnormal_flags=int(sample_filter.get("min_abnormal_flags", 2)),
        min_phase_days_3=int(sample_filter.get("min_phase_days_3", 1)),
        min_active_anomaly_rank=float(sample_filter.get("min_active_anomaly_rank", 0.0)),
        main_board_only=bool(sample_filter.get("main_board_only", True)),
        label_target=str(label.get("label_target", "next_high_from_close")),
        target_high_return_pct=float(label.get("target_high_return_pct", 1.0)),
        feature_set=str(features.get("feature_set", "expanded")),
        max_selected_features=int(features.get("max_selected_features", 260)),
        feature_selection_method=str(features.get("feature_selection_method", "stable_tail")),
        candidate_family=str(model.get("candidate_family", "all")),
        selector_coverage_weight=float(model.get("selector_coverage_weight", 0.02)),
        lockbox_role=str(lockbox.get("forward_lockbox_role", "final_unseen")),
        exclude_event_limit_up=exclude_event_limit_up,
        exclude_feature_prefix=exclude_prefix,
    )


def summarize_gpu_probe_config(
    config: GpuProbeConfig,
    *,
    frozen_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "start": config.start.isoformat(),
        "train_end": config.train_end.isoformat(),
        "test_start": config.test_start.isoformat(),
        "end": config.end.isoformat(),
        "test_rows": config.test_rows,
        "target_accuracy": config.target_accuracy,
        "label_target": config.label_target,
        "target_high_return_pct": config.target_high_return_pct,
        "feature_set": config.feature_set,
        "exclude_feature_prefix": list(config.exclude_feature_prefix),
        "max_selected_features": config.max_selected_features,
        "feature_selection_method": config.feature_selection_method,
        "candidate_family": config.candidate_family,
        "selector_coverage_weight": config.selector_coverage_weight,
        "short_only": config.short_only,
        "main_board_only": config.main_board_only,
        "min_turnover": config.min_turnover,
        "min_amount": config.min_amount,
        "min_volume_z": config.min_volume_z,
        "min_amount_z": config.min_amount_z,
        "min_range_pct": config.min_range_pct,
        "min_volatility_pct": config.min_volatility_pct,
        "min_phase_days_3": config.min_phase_days_3,
        "min_abnormal_flags": config.min_abnormal_flags,
        "lockbox_role": config.lockbox_role,
        "seed": config.seed,
        "exclude_event_limit_up": config.exclude_event_limit_up,
    }
    if frozen_config is not None:
        sf = frozen_config.get("sample_filter") or {}
        ft = frozen_config.get("features") or {}
        if "exclude_event_limit_up" in sf or "exclude_event_limit_up" in ft:
            summary["exclude_event_limit_up_source"] = "frozen_config"
        else:
            summary["exclude_event_limit_up_source"] = (
                "frozen_config_absent_legacy_false"
            )
    return summary

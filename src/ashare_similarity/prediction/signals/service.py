from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ashare_similarity.prediction.signals.config import SignalConfig
from ashare_similarity.prediction.signals.metrics import (
    baseline_brier,
    brier_score,
    wilson_lower_95,
)
from ashare_similarity.prediction.signals.schemas import (
    BacktestSummaryResponse,
    DailySeriesPoint,
    DailySignalResponse,
    ModelBacktestSummary,
    SignalDateListResponse,
    SignalRow,
    SignalStatusResponse,
    SplitLayerStats,
    StockSignalResponse,
)

logger = logging.getLogger(__name__)

_HASH_FIELDS = ("run_id", "feature_hash", "data_hash", "split_hash", "code_hash")


class SignalService:

    def __init__(self, signal_config: SignalConfig) -> None:
        self._config = signal_config
        self._cache: pd.DataFrame | None = None
        self._manifest: dict[str, Any] | None = None
        self._status: str = "not_checked"

    def get_status(self) -> SignalStatusResponse:
        self._ensure_loaded()
        if self._status == "ready":
            manifest = self._manifest or {}
            date_range = manifest.get("test_date_range")
            sample_symbols: list[str] = []
            if self._cache is not None:
                syms = sorted(self._cache["symbol"].unique().tolist())
                sample_symbols = syms[:5]
            return SignalStatusResponse(
                status="ready",
                cache_generated_at=manifest.get("generated_at"),
                candidates=[c["candidate_tag"] for c in manifest.get("candidates", [])],
                date_range=date_range,
                research_only=manifest.get("research_only", True),
                sample_symbols=sample_symbols,
            )
        return SignalStatusResponse(
            status=self._status,
            candidates=[],
            research_only=True,
        )

    def is_ready(self) -> bool:
        self._ensure_loaded()
        return self._status == "ready"

    def get_dates(self) -> SignalDateListResponse:
        df = self._require_cache()
        dates = sorted(df["date"].dt.strftime("%Y-%m-%d").unique().tolist())
        return SignalDateListResponse(dates=dates, count=len(dates))

    def get_daily_signals(
        self,
        date: str,
        model_tag: str | None = None,
        *,
        resolve_name: Any = None,
    ) -> DailySignalResponse:
        df = self._require_cache()
        mask = df["date"].dt.strftime("%Y-%m-%d") == date
        if model_tag:
            mask = mask & (df["model_tag"] == model_tag)
        subset = df[mask].sort_values(["confident", "probability"], ascending=[False, False])

        rows = self._to_signal_rows(subset, resolve_name=resolve_name)
        split_layer = subset["split_layer"].iloc[0] if len(subset) > 0 else ""

        summary: dict[str, Any] = {}
        for tag in subset["model_tag"].unique():
            tag_df = subset[subset["model_tag"] == tag]
            conf = tag_df[tag_df["confident"]]
            conf_correct = conf["correct"].sum() if "correct" in conf.columns and len(conf) > 0 else 0
            summary[tag] = {
                "total": len(tag_df),
                "confident": len(conf),
                "accuracy": round(float(conf_correct / len(conf)), 4) if len(conf) > 0 else None,
            }
        return DailySignalResponse(date=date, split_layer=split_layer, signals=rows, summary=summary)

    def get_stock_signals(
        self,
        symbol: str,
        date: str | None = None,
        *,
        resolve_name: Any = None,
    ) -> StockSignalResponse:
        df = self._require_cache()
        mask = df["symbol"] == symbol
        if date:
            mask = mask & (df["date"].dt.strftime("%Y-%m-%d") == date)
        subset = df[mask].sort_values("date", ascending=False)

        name = ""
        if resolve_name and callable(resolve_name):
            name = resolve_name(symbol) or ""

        rows = self._to_signal_rows(subset, resolve_name=resolve_name)

        message: str | None = None
        if len(subset) == 0:
            all_symbols = set(df["symbol"].unique())
            if symbol not in all_symbols:
                message = f"股票 {symbol} 不在本次回测信号缓存的研究样本中"

        summary_by_model: dict[str, Any] = {}
        for tag in subset["model_tag"].unique():
            tag_df = subset[subset["model_tag"] == tag]
            total_correct = int(tag_df["correct"].sum()) if "correct" in tag_df.columns else 0
            conf = tag_df[tag_df["confident"]]
            conf_correct = int(conf["correct"].sum()) if "correct" in conf.columns and len(conf) > 0 else 0
            summary_by_model[tag] = {
                "total": len(tag_df),
                "correct": total_correct,
                "accuracy": round(total_correct / len(tag_df), 4) if len(tag_df) > 0 else None,
                "confident_count": len(conf),
                "confident_correct": conf_correct,
                "confident_accuracy": round(conf_correct / len(conf), 4) if len(conf) > 0 else None,
            }
        return StockSignalResponse(symbol=symbol, name=name, predictions=rows, summary_by_model=summary_by_model, message=message)

    def get_backtest_summary(self) -> BacktestSummaryResponse:
        df = self._require_cache()
        manifest = self._manifest or {}

        by_model: list[ModelBacktestSummary] = []
        daily_series: list[DailySeriesPoint] = []

        for cand in manifest.get("candidates", []):
            tag = cand["candidate_tag"]
            tag_df = df[df["model_tag"] == tag]
            layers: list[SplitLayerStats] = []
            for layer in ["dev_valid", "seen_research"]:
                layer_df = tag_df[tag_df["split_layer"] == layer]
                if len(layer_df) == 0:
                    continue
                conf = layer_df[layer_df["confident"]]
                conf_correct_arr = conf["correct"].values if "correct" in conf.columns else np.zeros(0)
                successes = int(conf_correct_arr.sum())
                layers.append(SplitLayerStats(
                    layer=layer,
                    total_rows=len(layer_df),
                    confident_count=len(conf),
                    confident_accuracy=round(float(successes / len(conf)), 6) if len(conf) > 0 else 0.0,
                    confident_coverage=round(len(conf) / len(layer_df), 6) if len(layer_df) > 0 else 0.0,
                    wilson_lower_95=round(wilson_lower_95(successes, len(conf)), 6),
                    brier=round(brier_score(layer_df["actual"].values, layer_df["probability"].values), 6),
                    baseline_brier=round(baseline_brier(layer_df["actual"].values), 6),
                ))

            by_model.append(ModelBacktestSummary(
                model_tag=tag,
                best_model=cand.get("best_model", ""),
                selector_method=cand.get("selector_method", ""),
                by_layer=layers,
                artifact_reference=cand.get("artifact_reference", {}),
            ))

            for layer in ["dev_valid", "seen_research"]:
                layer_df = tag_df[tag_df["split_layer"] == layer]
                for date_val, date_group in layer_df.groupby(layer_df["date"].dt.strftime("%Y-%m-%d")):
                    conf = date_group[date_group["confident"]]
                    conf_correct_arr = conf["correct"].values if "correct" in conf.columns else np.zeros(0)
                    conf_correct_count = int(conf_correct_arr.sum())
                    daily_series.append(DailySeriesPoint(
                        date=str(date_val),
                        model_tag=tag,
                        accuracy=round(float(conf_correct_count / len(conf)), 4) if len(conf) > 0 else None,
                        coverage=round(len(conf) / len(date_group), 4) if len(date_group) > 0 else 0.0,
                        confident_count=len(conf),
                        split_layer=layer,
                    ))

        daily_series.sort(key=lambda d: (d.date, d.model_tag))
        date_range = manifest.get("test_date_range", [])
        return BacktestSummaryResponse(
            by_model=by_model,
            daily_series=daily_series,
            data_range=date_range,
            research_only=manifest.get("research_only", True),
        )

    def _ensure_loaded(self) -> None:
        if self._status not in {"not_checked"}:
            return
        current_path = self._config.cache_root / "current.json"
        if not current_path.exists():
            self._status = "not_built"
            return
        try:
            with open(current_path, encoding="utf-8") as f:
                current = json.load(f)
            build_id = current.get("build_id", "")
            build_dir = self._config.cache_root / build_id
            manifest_path = build_dir / "manifest.json"
            cache_path = build_dir / "signal_cache.parquet"
            if not manifest_path.exists() or not cache_path.exists():
                self._status = "not_built"
                return
            with open(manifest_path, encoding="utf-8") as f:
                self._manifest = json.load(f)

            if not self._validate_manifest():
                self._status = "manifest_mismatch"
                self._cache = None
                return

            self._cache = pd.read_parquet(cache_path)
            self._status = "ready"
            logger.info("Signal cache loaded: %d rows from build %s", len(self._cache), build_id)
        except Exception:
            logger.exception("Failed to load signal cache")
            self._status = "not_built"

    def _validate_manifest(self) -> bool:
        if self._manifest is None:
            return False
        frozen_path = self._config.frozen_candidates_path
        if not frozen_path.exists():
            logger.warning("Frozen candidates not found at %s, cannot validate manifest", frozen_path.name)
            return False

        try:
            with open(frozen_path, encoding="utf-8") as f:
                frozen = json.load(f)
        except Exception:
            logger.warning("Cannot read frozen candidates at %s", frozen_path.name)
            return False

        frozen_by_tag: dict[str, dict[str, Any]] = {}
        for c in frozen.get("candidates", []):
            frozen_by_tag[c["tag"]] = c

        manifest_candidates = self._manifest.get("candidates", [])
        manifest_tags = {mc.get("candidate_tag", "") for mc in manifest_candidates}
        frozen_tags = set(frozen_by_tag.keys())
        if manifest_tags != frozen_tags:
            logger.warning(
                "Candidate set mismatch: manifest=%s vs frozen=%s",
                sorted(manifest_tags), sorted(frozen_tags),
            )
            return False

        for mc in manifest_candidates:
            tag = mc.get("candidate_tag", "")
            fc = frozen_by_tag.get(tag)
            if fc is None:
                logger.warning("Manifest candidate '%s' not found in frozen candidates", tag)
                return False
            for field in _HASH_FIELDS:
                manifest_val = mc.get(field, "")
                frozen_val = fc.get(field, "")
                if manifest_val and frozen_val and manifest_val != frozen_val:
                    logger.warning(
                        "Manifest mismatch for %s.%s: manifest=%s vs frozen=%s",
                        tag, field, manifest_val, frozen_val,
                    )
                    return False
        return True

    def _require_cache(self) -> pd.DataFrame:
        self._ensure_loaded()
        if self._cache is None:
            raise RuntimeError("Signal cache not available")
        return self._cache

    def _to_signal_rows(self, df: pd.DataFrame, *, resolve_name: Any = None) -> list[SignalRow]:
        rows: list[SignalRow] = []
        has_correct = "correct" in df.columns
        for _, row in df.iterrows():
            symbol = str(row["symbol"])
            name = ""
            if resolve_name and callable(resolve_name):
                name = resolve_name(symbol) or ""
            actual = float(row["actual"])
            prob = float(row["probability"])
            confident = bool(row["confident"])
            correct: bool | None = None
            if has_correct:
                correct = bool(row["correct"])
            elif not pd.isna(actual):
                threshold = float(row.get("decision_threshold", 0.5))
                predicted = prob >= threshold
                correct = predicted == (actual >= 0.5)
            rows.append(SignalRow(
                date=row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])[:10],
                symbol=symbol,
                name=name,
                model_tag=str(row["model_tag"]),
                best_model=str(row["best_model"]),
                selector_method=str(row["selector_method"]),
                probability=round(prob, 6),
                confident=confident,
                actual=actual,
                correct=correct,
                split_layer=str(row["split_layer"]),
            ))
        return rows

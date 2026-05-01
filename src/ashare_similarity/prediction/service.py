from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ashare_similarity.config import AppConfig
from ashare_similarity.data.base import Frequency
from ashare_similarity.data.service import DataService
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.features.encoder import encode_window
from ashare_similarity.features.service import FeatureService
from ashare_similarity.prediction.analogue_model import AnalogueSample, predict_from_analogues
from ashare_similarity.prediction.ensemble import build_horizon_prediction
from ashare_similarity.prediction.factor_builder import build_factor_snapshot
from ashare_similarity.prediction.label_builder import build_forward_labels
from ashare_similarity.prediction.ml_model import predict_with_ml
from ashare_similarity.schemas import (
    DataFreshness,
    PredictionAnalogueSample,
    PredictionBacktestSummary,
    PredictionModelDiagnostics,
    PredictionQueryMeta,
    PredictionRequest,
    PredictionResponse,
)
from ashare_similarity.search.scoring import score_window_pair
from ashare_similarity.search.service import SearchService


class PredictionService:
    def __init__(
        self,
        config: AppConfig,
        store: LocalDataStore,
        data_service: DataService,
        feature_service: FeatureService,
        search_service: SearchService,
    ) -> None:
        self.config = config
        self.store = store
        self.data_service = data_service
        self.feature_service = feature_service
        self.search_service = search_service

    def predict(self, request: PredictionRequest) -> PredictionResponse:
        request = self._resolve_request(request)
        query_window_cache: dict[int, Any] = {}
        query_window, factors = self._build_query_factors(request, query_window_cache=query_window_cache)
        samples, warnings = self._collect_analogue_samples(request, query_window_cache=query_window_cache)
        analogue_predictions = predict_from_analogues(samples, request.horizons, query_vector=factors.vector)
        ml_predictions = predict_with_ml(samples, factors.vector, request.horizons)
        predictions = [
            build_horizon_prediction(analogue_predictions[horizon], ml_predictions[horizon])
            for horizon in request.horizons
        ]
        diagnostics = self._diagnostics(samples, ml_predictions)
        evidence = self._evidence_payload(samples[: min(len(samples), 20)], request.horizons)
        freshness = self._get_data_freshness(request.frequency)
        warnings = list(dict.fromkeys([*warnings, *diagnostics.warnings]))
        return PredictionResponse(
            query_meta=PredictionQueryMeta(
                symbol=query_window.symbol,
                name=query_window.metadata.get("name"),
                as_of_date=str(query_window.metadata["end_date"]),
                frequency=request.frequency,
                horizons=request.horizons,
                window_sizes=request.window_sizes,
                top_k=request.top_k,
                search_scope="historical",
            ),
            factor_snapshot=factors.snapshot,
            analogue_evidence=evidence,
            predictions=predictions,
            model_diagnostics=diagnostics,
            backtest_summary=PredictionBacktestSummary(
                status="not_available",
                acceptance="not_evaluated",
                notes=["当前 Web 预测使用在线相似样本与轻量 ML 对照；正式验收请运行 backtest-prediction。"],
            ),
            data_freshness=freshness,
            warnings=warnings,
        )

    def backtest(
        self,
        *,
        start: date,
        end: date,
        sample_size: int = 50,
        seed: int = 42,
        horizons: list[int] | None = None,
        window_sizes: list[int] | None = None,
        top_k: int = 40,
        target_accuracy: float = 0.75,
        confidence_threshold: float = 0.65,
    ) -> PredictionBacktestSummary:
        horizons = sorted({int(horizon) for horizon in (horizons or [1, 2])})
        if not horizons:
            horizons = [1, 2]
        window_sizes = sorted({int(window_size) for window_size in (window_sizes or [5, 8, 10, 20])})
        if not window_sizes:
            window_sizes = [5, 8, 10, 20]
        top_k = max(10, int(top_k))
        target_accuracy = _bounded_float(target_accuracy, default=0.75, lower=0.75, upper=1.0)
        confidence_threshold = _bounded_float(confidence_threshold, default=0.65, lower=0.5, upper=1.0)
        max_horizon = max(horizons)
        acceleration = self._acceleration_diagnostics()
        symbols = [str(symbol).zfill(6) for symbol in self.store.list_cached_symbols("daily")]
        symbols = [symbol for symbol in symbols if _is_main_board_symbol(symbol)]
        if not symbols:
            return PredictionBacktestSummary(
                status="no_cache",
                acceptance="failed",
                acceleration=acceleration,
                notes=["没有可用主板日线缓存，无法回测预测模型。"],
            )

        rng = np.random.default_rng(seed)
        rng.shuffle(symbols)
        rows: list[dict[str, float]] = []
        attempted = 0
        for symbol in symbols:
            if attempted >= sample_size:
                break
            bars = self.store.load_bars(symbol, "daily")
            if bars.empty or "date" not in bars.columns:
                continue
            bars["date"] = pd.to_datetime(bars["date"])
            candidates = bars[(bars["date"].dt.date >= start) & (bars["date"].dt.date <= end)].iloc[:-max_horizon]
            if len(candidates) < 20:
                continue
            as_of_index = int(rng.integers(0, len(candidates)))
            as_of = candidates.iloc[as_of_index]["date"].date()
            try:
                response = self.predict(
                    PredictionRequest(
                        symbol=symbol,
                        as_of_date=as_of,
                        frequency="daily",
                        horizons=horizons,
                        window_sizes=window_sizes,
                        top_k=top_k,
                    )
                )
            except Exception:
                continue
            labels = build_forward_labels(bars, end_date=str(as_of), horizons=horizons)
            for prediction in response.predictions:
                label = labels.get(prediction.horizon)
                if label is None or label.return_pct is None or prediction.up_probability is None:
                    continue
                actual = 1.0 if label.return_pct > 0 else 0.0
                rows.append(
                    {
                        "horizon": float(prediction.horizon),
                        "prob": float(prediction.up_probability),
                        "actual": actual,
                        "confident": 1.0
                        if _is_confident_probability(float(prediction.up_probability), confidence_threshold)
                        else 0.0,
                    }
                )
            attempted += 1

        if not rows:
            return PredictionBacktestSummary(
                status="insufficient_samples",
                sample_size=0,
                acceptance="failed",
                acceleration=acceleration,
                notes=["回测样本不足，无法计算稳定指标。"],
            )

        recall_gpu_enabled = bool(acceleration.get("recall_gpu_enabled"))
        frame = pd.DataFrame(rows)
        accuracy = float(((frame["prob"] >= 0.5).astype(float) == frame["actual"]).mean())
        brier = float(((frame["prob"] - frame["actual"]) ** 2).mean())
        confident = frame[frame["confident"] > 0]
        confident_accuracy = (
            float(((confident["prob"] >= 0.5).astype(float) == confident["actual"]).mean())
            if not confident.empty
            else None
        )
        confident_brier = float(((confident["prob"] - confident["actual"]) ** 2).mean()) if not confident.empty else None
        baseline_prob = float(frame["actual"].mean())
        baseline_brier = float(((baseline_prob - frame["actual"]) ** 2).mean())
        baseline_accuracy = float(max(frame["actual"].mean(), 1.0 - frame["actual"].mean()))
        metrics: dict[str, float | None] = {
            "direction_accuracy": round(accuracy, 6),
            "brier": round(brier, 6),
            "target_accuracy": round(target_accuracy, 6),
            "target_met": 1.0 if accuracy >= target_accuracy else 0.0,
            "prediction_count": float(len(frame)),
            "confident_direction_accuracy": round(confident_accuracy, 6) if confident_accuracy is not None else None,
            "confident_brier": round(confident_brier, 6) if confident_brier is not None else None,
            "confident_prediction_count": float(len(confident)),
            "confident_coverage": round(float(len(confident) / len(frame)), 6),
            "confident_target_met": 1.0
            if confident_accuracy is not None and confident_accuracy >= target_accuracy
            else 0.0,
            "confidence_threshold": round(confidence_threshold, 6),
            "recall_gpu_enabled": 1.0 if recall_gpu_enabled else 0.0,
        }
        missing_horizons: list[int] = []
        for horizon in horizons:
            metrics[f"h{horizon}_prediction_count"] = 0.0
            metrics[f"h{horizon}_confident_prediction_count"] = 0.0
        for horizon, group in frame.groupby("horizon"):
            horizon_id = int(horizon)
            horizon_accuracy = float(((group["prob"] >= 0.5).astype(float) == group["actual"]).mean())
            metrics[f"h{horizon_id}_direction_accuracy"] = round(horizon_accuracy, 6)
            horizon_confident = group[group["confident"] > 0]
            metrics[f"h{horizon_id}_prediction_count"] = float(len(group))
            metrics[f"h{horizon_id}_confident_prediction_count"] = float(len(horizon_confident))
            if not horizon_confident.empty:
                horizon_confident_accuracy = float(
                    ((horizon_confident["prob"] >= 0.5).astype(float) == horizon_confident["actual"]).mean()
                )
                metrics[f"h{horizon_id}_confident_direction_accuracy"] = round(horizon_confident_accuracy, 6)
        for horizon in horizons:
            if metrics[f"h{horizon}_prediction_count"] <= 0:
                missing_horizons.append(horizon)
        metrics["all_horizons_evaluable"] = 0.0 if missing_horizons else 1.0
        accepted = (
            not missing_horizons
            and brier < baseline_brier
            and accuracy >= baseline_accuracy
            and accuracy >= target_accuracy
        )
        notes = [
            "回测仅抽样主板标的，采用随机历史锚点逐笔预测，不随机打散训练验证顺序。",
            f"验收目标为整体方向准确率达到 {target_accuracy:.0%}，同时 Brier Score 优于样本先验基线。",
            (
                "召回检索运行后端："
                f"{acceleration.get('recall_backend', 'unknown')} / {acceleration.get('recall_device', 'unknown')}。"
            ),
            "该报告用于判断研究信号是否具备边际优势，不构成交易建议。",
        ]
        if not recall_gpu_enabled:
            notes.append("当前回测未检测到 GPU 召回；因子、标签、重排和 sklearn 校准仍主要运行在 CPU。")
        if missing_horizons:
            notes.append(f"以下预测周期没有可评估样本，不能通过验收：{missing_horizons}。")
        if accuracy < target_accuracy:
            notes.append(f"整体方向准确率 {accuracy:.2%} 尚未达到 {target_accuracy:.0%} 目标。")
        if confident_accuracy is None:
            notes.append(f"没有满足置信阈值 {confidence_threshold:.0%}/{1.0 - confidence_threshold:.0%} 的预测样本。")
        elif confident_accuracy >= target_accuracy:
            notes.append(
                f"高置信样本方向准确率 {confident_accuracy:.2%} 达到目标，但覆盖率为 {len(confident) / len(frame):.2%}。"
            )
        return PredictionBacktestSummary(
            status="completed",
            sample_size=int(len(frame)),
            metrics=metrics,
            baseline_metrics={
                "direction_accuracy": round(baseline_accuracy, 6),
                "brier": round(baseline_brier, 6),
                "positive_rate": round(baseline_prob, 6),
            },
            acceleration=acceleration,
            acceptance="passed" if accepted else "failed",
            notes=notes,
        )

    def train_model(self, *, approved_run_id: str | None = None) -> dict[str, Any]:
        gate = self._latest_passed_gpu_probe_artifact(approved_run_id=approved_run_id)
        if gate is None:
            return {
                "status": "blocked",
                "acceptance": "failed",
                "persistent_model_created": False,
                "approved_run_id": approved_run_id,
                "message": (
                    "全局拟合被阻止：需要先运行 gpu-prediction-probe，并产生通过 75% 准确率和 Brier "
                    "验收的 data/reports/prediction/gpu_probe_passed_latest.json。"
                ),
            }
        report = {
            "status": "ready_for_global_fit",
            "acceptance": "passed",
            "persistent_model_created": False,
            "approved_run_id": approved_run_id or gate.get("run_id"),
            "gate_artifact": gate,
            "message": "GPU 探针验收已通过门禁；持久化全局模型训练将在下一阶段落盘实现。",
        }
        return report

    def _latest_passed_gpu_probe_artifact(self, *, approved_run_id: str | None = None) -> dict[str, Any] | None:
        storage = getattr(self.config, "storage", None)
        report_dir = getattr(storage, "report_dir", None)
        if report_dir is None:
            return None
        prediction_dir = Path(report_dir) / "prediction"
        path = prediction_dir / "gpu_probe_passed_latest.json"
        if approved_run_id:
            approved_path = prediction_dir / "runs" / approved_run_id / "artifact.json"
            if approved_path.exists():
                path = approved_path
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if isinstance(payload, dict) and payload.get("artifact") and "result" not in payload:
            artifact_path = Path(str(payload["artifact"]))
            if not artifact_path.exists():
                return None
            try:
                payload = json.loads(artifact_path.read_text(encoding="utf-8"))
                path = artifact_path
            except Exception:
                return None
        result = payload.get("result") if isinstance(payload, dict) else None
        acceptance = result.get("acceptance") if isinstance(result, dict) else None
        if not isinstance(acceptance, dict) or not acceptance.get("passed"):
            return None
        if acceptance.get("lockbox_role") != "final_unseen" or not acceptance.get("final_acceptance_eligible"):
            return None
        run_id = payload.get("run_id") or result.get("run_id")
        if approved_run_id and str(run_id) != str(approved_run_id):
            return None
        return {
            "path": str(path),
            "generated_at": payload.get("generated_at"),
            "run_id": run_id,
            "code_hash": payload.get("code_hash") or result.get("code_hash"),
            "feature_hash": payload.get("feature_hash") or result.get("feature_hash"),
            "data_hash": payload.get("data_hash") or result.get("data_hash"),
            "split_hash": payload.get("split_hash") or result.get("split_hash"),
            "model": result.get("model"),
            "accuracy": result.get("accuracy"),
            "confident_accuracy": result.get("confident_accuracy"),
            "confident_count": result.get("confident_count"),
            "brier": result.get("brier"),
            "baseline_brier": result.get("baseline_brier"),
            "test_rows": result.get("test_rows"),
            "target_accuracy": result.get("target_accuracy"),
            "lockbox_role": acceptance.get("lockbox_role"),
            "final_acceptance_eligible": acceptance.get("final_acceptance_eligible"),
        }

    def _resolve_request(self, request: PredictionRequest) -> PredictionRequest:
        resolver = getattr(self.data_service, "resolve_symbol_query", None)
        resolved_symbol: str | None = None
        if callable(resolver):
            resolved = resolver(request.symbol, frequency=request.frequency, prefer_cached=True)
            if isinstance(resolved, dict) and resolved.get("symbol"):
                resolved_symbol = str(resolved["symbol"]).zfill(6)
        if resolved_symbol is None and request.symbol.isdigit():
            resolved_symbol = request.symbol.zfill(6)
        if resolved_symbol is None:
            raise ValueError(f"无法识别股票代码或名称：{request.symbol}")
        if not _is_main_board_symbol(resolved_symbol):
            raise ValueError("当前短线预测模式只看主板标的：支持 600/601/603/605/000/001/002/003 开头股票。")
        return request.model_copy(update={"symbol": resolved_symbol})

    def _build_query_factors(
        self,
        request: PredictionRequest,
        *,
        query_window_cache: dict[int, Any] | None = None,
    ):
        last_error: Exception | None = None
        for window_size in sorted(request.window_sizes, reverse=True):
            try:
                query_window = self._get_query_window(
                    request,
                    window_size,
                    query_window_cache=query_window_cache,
                )
                factors = build_factor_snapshot(
                    query_window.series,
                    symbol=query_window.symbol,
                    name=query_window.metadata.get("name"),
                    as_of_date=str(query_window.metadata["end_date"]),
                    window_size=window_size,
                )
                return query_window, factors
            except Exception as exc:
                last_error = exc
                continue
        raise ValueError(f"无法构建预测目标窗口：{last_error}") from last_error

    def _collect_analogue_samples(
        self,
        request: PredictionRequest,
        *,
        query_window_cache: dict[int, Any] | None = None,
    ) -> tuple[list[AnalogueSample], list[str]]:
        samples_by_key: dict[tuple[str, str, str], AnalogueSample] = {}
        history_cache: dict[tuple[str, Frequency], pd.DataFrame] = {}
        labels_cache: dict[tuple[str, str, str], Any] = {}
        warnings: list[str] = []
        per_window_target = max(10, int(np.ceil(request.top_k / max(len(request.window_sizes), 1))))
        per_window_recall = max(250, per_window_target * 12)

        def load_history(symbol: str) -> pd.DataFrame:
            cache_key = (symbol, request.frequency)
            if cache_key not in history_cache:
                history_cache[cache_key] = self.store.load_bars(symbol, request.frequency)
            return history_cache[cache_key]

        for window_size in request.window_sizes:
            try:
                query_window = self._get_query_window(
                    request,
                    window_size,
                    query_window_cache=query_window_cache,
                )
                searchable = self.search_service.index_service.load(request.frequency, window_size)
                row_count = int(getattr(searchable, "row_count", 0) or len(searchable.metadata.index))
                recall_k = min(row_count, per_window_recall)
                distances, indices = searchable.search(query_window.matrix.astype(np.float32), recall_k)
            except Exception as exc:
                warnings.append(f"窗口 {window_size} 相似样本检索失败：{exc}")
                continue

            accepted_for_window = 0
            query_start = pd.Timestamp(query_window.metadata["start_date"])
            for distance, raw_index in zip(distances.tolist(), indices.tolist(), strict=False):
                if accepted_for_window >= per_window_target:
                    break
                row_index = int(raw_index)
                if row_index < 0:
                    continue
                try:
                    row = searchable.metadata_row(row_index)
                except Exception:
                    continue
                candidate_symbol = str(row.get("symbol", "")).strip().zfill(6)
                start_date = str(row.get("start_date"))
                end_date = str(row.get("end_date"))
                if not _is_main_board_symbol(candidate_symbol):
                    continue
                if not candidate_symbol or not _ends_before_query_window(row, query_start):
                    continue
                key = (candidate_symbol, start_date, end_date)
                if key in samples_by_key:
                    continue
                history = load_history(candidate_symbol)
                labels_key = (candidate_symbol, end_date, str(request.as_of_date))
                if labels_key not in labels_cache:
                    labels_cache[labels_key] = build_forward_labels(
                        history,
                        end_date=end_date,
                        horizons=request.horizons,
                        max_label_date=str(request.as_of_date),
                    )
                labels = labels_cache[labels_key]
                if not any(label.return_pct is not None for label in labels.values()):
                    continue
                match_series = _history_window(history, end_date=end_date, window_size=window_size)
                if match_series.empty:
                    continue
                similarity = _reranked_similarity(
                    query_vector=query_window.matrix[0],
                    candidate_window=match_series,
                    component_slices=query_window.component_slices,
                    fallback_distance=float(distance),
                    weights=self.config.search_weights,
                )
                factors = build_factor_snapshot(
                    match_series,
                    symbol=candidate_symbol,
                    name=_optional_str(row.get("name")),
                    as_of_date=end_date,
                    window_size=window_size,
                )
                samples_by_key[key] = AnalogueSample(
                    symbol=candidate_symbol,
                    name=_optional_str(row.get("name")),
                    window_size=window_size,
                    start_date=start_date,
                    end_date=end_date,
                    similarity=similarity,
                    factors=factors.vector,
                    labels=labels,
                )
                accepted_for_window += 1

        samples = sorted(samples_by_key.values(), key=lambda sample: sample.similarity, reverse=True)
        return samples[: request.top_k], warnings

    def _get_query_window(
        self,
        request: PredictionRequest,
        window_size: int,
        *,
        query_window_cache: dict[int, Any] | None = None,
    ):
        if query_window_cache is not None and window_size in query_window_cache:
            return query_window_cache[window_size]
        query_window = self.feature_service.build_query_frame(
            symbol=request.symbol,
            end_date=request.as_of_date,
            frequency=request.frequency,
            window_size=window_size,
            ensure_remote=False,
        )
        if query_window_cache is not None:
            query_window_cache[window_size] = query_window
        return query_window

    def _diagnostics(self, samples: list[AnalogueSample], ml_predictions) -> PredictionModelDiagnostics:
        ml_values = list(ml_predictions.values())
        passed = any(item.passed_validation for item in ml_values)
        validation_metrics: dict[str, float | None] = {}
        for item in ml_values:
            for key, value in item.validation_metrics.items():
                validation_metrics[f"h{item.horizon}_{key}"] = value
        warnings = [
            "仅展示研究信号，不构成买卖建议。",
            "当前预测研究范围已固定为主板短线样本，涨跌停因子按主板 10cm 近似处理。",
        ]
        if not passed:
            warnings.append("监督学习对照尚未通过 walk-forward 基线验收，默认以相似历史样本为主。")
        if len(samples) < 20:
            warnings.append("相似历史样本不足，预测置信度应视为不足样本。")
        return PredictionModelDiagnostics(
            selected_model="ensemble" if passed else "analogue",
            analogue_status="ready" if samples else "no_samples",
            ml_status="validated" if passed else "; ".join(sorted({item.status for item in ml_values})),
            passed_validation=passed,
            warnings=warnings,
            ml_training_samples=max((item.sample_count for item in ml_values), default=0),
            validation_metrics=validation_metrics,
            acceleration=self._acceleration_diagnostics(),
        )

    def _acceleration_diagnostics(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        daily_windows = sorted(int(window) for window in self.config.build_defaults.daily_window_sizes)

        for window_size in reversed(daily_windows):
            try:
                searchable = self.search_service.index_service.load("daily", window_size)
                runtime_metadata = getattr(searchable.search_index, "runtime_metadata", None)
                if callable(runtime_metadata):
                    metadata = dict(runtime_metadata())
                    break
            except Exception:
                continue

        backend = str(metadata.get("active_backend") or metadata.get("artifact_backend") or "unknown")
        device = str(metadata.get("active_device") or "cpu")
        device_name = metadata.get("active_device_name")
        gpu_recall = "cuda" in f"{backend} {device}".lower()
        return {
            "recall_backend": backend,
            "recall_device": device,
            "recall_device_name": device_name,
            "recall_gpu_enabled": gpu_recall,
            "gpu_scope": "recall_only" if gpu_recall else "none",
            "full_gpu_pipeline": False,
            "market_scope": "main_board_only",
            "main_board_limit_threshold_pct": 10.0,
            "rerank": "cpu",
            "factor_label_ml": "cpu",
            "cpu_stages": [
                "data_io",
                "feature_build",
                "dtw_rerank",
                "factor_build",
                "label_build",
                "sklearn_calibration",
                "metrics",
            ],
            "note": (
                "相似样本召回会尽量使用 Torch CUDA；DTW 精排、因子构建、标签生成和 "
                "sklearn 校准仍在 CPU 上运行，避免把研究信号包装成不存在的全 GPU 模型。"
            ),
        }

    def _evidence_payload(self, samples: list[AnalogueSample], horizons: list[int]) -> list[PredictionAnalogueSample]:
        payload: list[PredictionAnalogueSample] = []
        for sample in samples:
            payload.append(
                PredictionAnalogueSample(
                    symbol=sample.symbol,
                    name=sample.name,
                    window_size=sample.window_size,
                    start_date=sample.start_date,
                    end_date=sample.end_date,
                    similarity=round(float(sample.similarity), 6),
                    forward_returns_pct={
                        str(horizon): sample.labels[horizon].return_pct if horizon in sample.labels else None
                        for horizon in horizons
                    },
                    scenarios={
                        str(horizon): sample.labels[horizon].scenario if horizon in sample.labels else None
                        for horizon in horizons
                    },
                )
            )
        return payload

    def _get_data_freshness(self, frequency: Frequency) -> DataFreshness:
        freshness = self.data_service.get_data_freshness(frequency)
        if isinstance(freshness, DataFreshness):
            return freshness
        if isinstance(freshness, dict):
            return DataFreshness.model_validate(freshness)
        return DataFreshness(data_source=self.config.data_source.provider)


def _history_window(history: pd.DataFrame, *, end_date: str, window_size: int) -> pd.DataFrame:
    if history.empty:
        return history
    time_col = "date" if "date" in history.columns else "timestamp"
    frame = history.copy()
    frame[time_col] = pd.to_datetime(frame[time_col], errors="coerce")
    end_ts = pd.Timestamp(end_date)
    window = frame[frame[time_col].dt.normalize() <= end_ts.normalize()].sort_values(time_col).tail(window_size)
    return window.rename(columns={time_col: "date"}).copy()


def _ends_before_query_window(row: pd.Series, query_start: pd.Timestamp) -> bool:
    try:
        candidate_end = pd.Timestamp(row.get("end_date"))
    except Exception:
        return False
    if pd.isna(candidate_end):
        return False
    return candidate_end.normalize() < query_start.normalize()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except Exception:
        pass
    text = str(value).strip()
    return text or None


def _is_main_board_symbol(symbol: str) -> bool:
    normalized = str(symbol).strip().zfill(6)
    return normalized.startswith(("600", "601", "603", "605", "000", "001", "002", "003"))


def _similarity_from_distance(distance: float) -> float:
    if not np.isfinite(distance):
        return 0.0
    return round(float(1.0 / (1.0 + max(distance, 0.0))), 6)


def _is_confident_probability(probability: float, threshold: float) -> bool:
    if not np.isfinite(probability):
        return False
    threshold = min(max(float(threshold), 0.5), 1.0)
    return probability >= threshold or probability <= 1.0 - threshold


def _bounded_float(value: float, *, default: float, lower: float, upper: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    if not np.isfinite(number):
        number = default
    return min(max(number, lower), upper)


def _reranked_similarity(
    *,
    query_vector: np.ndarray,
    candidate_window: pd.DataFrame,
    component_slices: dict[str, tuple[int, int]],
    fallback_distance: float,
    weights: Any,
) -> float:
    try:
        encoded = encode_window(candidate_window)
        score, _ = score_window_pair(
            query_vector=query_vector,
            candidate_vector=encoded.vector,
            component_slices=component_slices,
            weights=weights,
        )
        return float(score.balanced)
    except Exception:
        return _similarity_from_distance(fallback_distance)

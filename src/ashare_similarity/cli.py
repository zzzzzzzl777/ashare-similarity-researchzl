from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from datetime import date
from typing import Any

import uvicorn

from ashare_similarity.doctor import build_doctor_report
from ashare_similarity.indexing.health import index_entry_is_stale, latest_data_at
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe
from ashare_similarity.runtime import get_runtime
from ashare_similarity.schemas import BuildRequest, PredictionRequest, SearchRequest
from ashare_similarity.status_payload import attach_index_health
from ashare_similarity.web_launcher import (
    DEFAULT_PORT_SCAN_LIMIT,
    DEFAULT_WEB_HOST,
    DEFAULT_WEB_PORT,
    build_launch_info,
)


FREQUENCY_CHOICES = ["daily", "1", "5", "15", "30", "60"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A股K线相似检索命令行工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap", help="初始化股票池与基础市场环境")
    bootstrap.add_argument(
        "--with-sample",
        action="store_true",
        help="初始化后额外抓取一小批日线样本数据",
    )

    build = subparsers.add_parser("build", help="构建特征与检索索引")
    build.add_argument("--frequency", required=True, choices=FREQUENCY_CHOICES)
    build.add_argument("--window-size", required=True, type=int)
    build.add_argument("--start-date")
    build.add_argument("--end-date")
    build.add_argument("--symbols", nargs="*")
    build.add_argument("--skip-refresh", action="store_true")

    backfill = subparsers.add_parser("backfill", help="按批次回填本地市场数据缓存")
    backfill.add_argument("--frequency", required=True, choices=FREQUENCY_CHOICES)
    backfill.add_argument("--batch-size", type=int, default=20)
    backfill.add_argument("--max-symbols", type=int)
    backfill.add_argument("--start-date")
    backfill.add_argument("--end-date")
    backfill.add_argument("--symbols", nargs="*")
    backfill.add_argument("--retry-failures", action="store_true")
    backfill.set_defaults(resume=True)
    backfill.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="不续跑最近一次匹配的未完成任务，而是新建一次回填任务",
    )

    backfill_loop = subparsers.add_parser(
        "backfill-loop",
        help="循环执行可恢复回填，适合长期扩充缓存",
    )
    _add_backfill_loop_arguments(backfill_loop)

    maintain = subparsers.add_parser(
        "maintain",
        help="执行完整维护流程：回填缓存，并在需要时重建默认索引",
    )
    _add_backfill_loop_arguments(maintain)
    maintain.add_argument("--window-sizes", nargs="*", type=int)
    maintain.add_argument("--skip-rebuild", action="store_true")
    maintain.add_argument(
        "--force-rebuild",
        action="store_true",
        help="即使没有新增缓存标的，也强制重建索引",
    )

    search = subparsers.add_parser("search", help="检索相似K线窗口")
    search.add_argument("--symbol", required=True)
    search.add_argument("--end-date", required=True)
    search.add_argument("--frequency", required=True, choices=FREQUENCY_CHOICES)
    search.add_argument("--window-size", required=True, type=int)
    search.add_argument("--top-k", type=int, default=10)
    search.add_argument("--search-scope", choices=["historical", "all"], default="historical")

    predict = subparsers.add_parser("predict", help="输出未来 1/2 个交易日的研究型概率预测")
    predict.add_argument("--symbol", required=True)
    predict.add_argument("--as-of", required=True, dest="as_of_date")
    predict.add_argument("--frequency", choices=["daily"], default="daily")
    predict.add_argument("--horizons", nargs="*", type=int, default=[1, 2])
    predict.add_argument("--window-sizes", nargs="*", type=int, default=[5, 8, 10, 20])
    predict.add_argument("--top-k", type=int, default=100)

    backtest_prediction = subparsers.add_parser(
        "backtest-prediction",
        help="滚动抽样验证预测信号是否优于基线",
    )
    backtest_prediction.add_argument("--start", required=True)
    backtest_prediction.add_argument("--end", required=True)
    backtest_prediction.add_argument("--sample-size", type=int, default=50)
    backtest_prediction.add_argument("--seed", type=int, default=42)
    backtest_prediction.add_argument("--horizons", nargs="*", type=int, default=[1, 2])
    backtest_prediction.add_argument("--window-sizes", nargs="*", type=int, default=[5, 8, 10, 20])
    backtest_prediction.add_argument("--top-k", type=int, default=40)
    backtest_prediction.add_argument("--target-accuracy", type=float, default=0.75)
    backtest_prediction.add_argument("--confidence-threshold", type=float, default=0.65)

    gpu_probe = subparsers.add_parser(
        "gpu-prediction-probe",
        help="用 Torch CUDA 批量验证近三年下一交易日方向预测",
    )
    gpu_probe.add_argument("--start", required=True)
    gpu_probe.add_argument("--train-end", required=True)
    gpu_probe.add_argument("--test-start", required=True)
    gpu_probe.add_argument("--end", required=True)
    gpu_probe.add_argument("--train-rows", type=int, default=300_000)
    gpu_probe.add_argument("--test-rows", type=int, default=120_000)
    gpu_probe.add_argument("--seed", type=int, default=42)
    gpu_probe.add_argument("--max-symbols", type=int)
    gpu_probe.add_argument("--epochs", type=int, default=160)
    gpu_probe.add_argument("--target-accuracy", type=float, default=0.75)
    gpu_probe.add_argument("--validation-fraction", type=float, default=0.20)
    gpu_probe.add_argument("--embargo-label-days", type=int, default=1)
    gpu_probe.add_argument("--short-only", action=argparse.BooleanOptionalAction, default=True)
    gpu_probe.add_argument("--min-turnover", type=float, default=3.0)
    gpu_probe.add_argument("--min-amount", type=float, default=200_000_000.0)
    gpu_probe.add_argument("--min-volume-z", type=float, default=1.0)
    gpu_probe.add_argument("--min-amount-z", type=float, default=1.0)
    gpu_probe.add_argument("--min-range-pct", type=float, default=3.0)
    gpu_probe.add_argument("--min-volatility-pct", type=float, default=2.5)
    gpu_probe.add_argument("--min-abnormal-flags", type=int, default=2)
    gpu_probe.add_argument("--min-phase-days-3", type=int, default=2)
    gpu_probe.add_argument("--min-active-anomaly-rank", type=float, default=0.0)
    gpu_probe.add_argument("--main-board-only", action=argparse.BooleanOptionalAction, default=True)
    gpu_probe.add_argument("--min-label-return-pct", type=float, default=0.0)
    gpu_probe.add_argument("--label-target", choices=["next_close_up", "next_high_from_close"], default="next_high_from_close")
    gpu_probe.add_argument("--target-high-return-pct", type=float, default=1.0)
    gpu_probe.add_argument("--feature-set", choices=["legacy", "base", "expanded", "research"], default="expanded")
    gpu_probe.add_argument("--max-selected-features", type=int, default=299)
    gpu_probe.add_argument("--feature-selection-method", choices=["abs_correlation", "stable_tail"], default="abs_correlation")
    gpu_probe.add_argument("--candidate-family", choices=["all", "torch", "tree"], default="all")
    gpu_probe.add_argument("--intraday-factor-frequency", choices=["1", "5", "15", "30", "60"], default="5")
    gpu_probe.add_argument("--feature-cache", action=argparse.BooleanOptionalAction, default=True)
    gpu_probe.add_argument("--refresh-feature-cache", action="store_true")
    gpu_probe.add_argument("--lockbox-role", choices=["seen_research", "final_unseen"], default="seen_research")
    gpu_probe.add_argument("--selector-coverage-weight", type=float, default=0.02)
    gpu_probe.add_argument("--exclude-feature-prefix", nargs="*", default=None, help="Drop features matching any prefix before training (ablation)")

    prediction_build_dataset = subparsers.add_parser(
        "prediction-build-dataset",
        help="Build the managed prediction dataset/cache manifest.",
    )
    prediction_build_dataset.add_argument("--start")
    prediction_build_dataset.add_argument("--train-end")
    prediction_build_dataset.add_argument("--test-start")
    prediction_build_dataset.add_argument("--end")

    prediction_walkforward = subparsers.add_parser(
        "prediction-walkforward",
        help="Report the walk-forward protocol entrypoint for model selection.",
    )
    prediction_walkforward.add_argument("--start")
    prediction_walkforward.add_argument("--train-end")
    prediction_walkforward.add_argument("--test-start")
    prediction_walkforward.add_argument("--end")

    prediction_lockbox = subparsers.add_parser(
        "prediction-lockbox",
        help="Report the lockbox protocol entrypoint for final acceptance.",
    )
    prediction_lockbox.add_argument("--approved-run-id")

    subparsers.add_parser("train-prediction", help="生成预测模型训练状态报告")

    status = subparsers.add_parser("status", help="查看当前缓存、建库与回填状态")
    status.add_argument("--frequency", choices=FREQUENCY_CHOICES)

    doctor = subparsers.add_parser("doctor", help="执行可用性自检并输出使用建议")
    doctor.add_argument("--symbol")
    doctor.add_argument("--end-date")
    doctor.add_argument("--frequency", choices=FREQUENCY_CHOICES, default="daily")
    doctor.add_argument("--window-size", type=int, default=10)
    doctor.add_argument("--top-k", type=int, default=10)

    serve = subparsers.add_parser("serve", help="启动本地 Web 服务")
    serve.add_argument("--host", default=DEFAULT_WEB_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_WEB_PORT)
    serve.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
    )
    serve.add_argument("--reload", action="store_true")
    serve.add_argument(
        "--port-scan-limit",
        type=int,
        default=DEFAULT_PORT_SCAN_LIMIT,
        help="首选端口被占用时，继续尝试的端口数量",
    )

    if "train-prediction" in subparsers.choices:
        subparsers.choices["train-prediction"].add_argument("--approved-run-id")

    return parser


def _add_backfill_loop_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--frequency", required=True, choices=FREQUENCY_CHOICES)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--max-symbols-per-round", type=int, default=100)
    parser.add_argument("--max-rounds", type=int, default=10)
    parser.add_argument("--round-interval-seconds", type=float, default=5.0)
    parser.add_argument(
        "--retry-failures-every",
        type=int,
        default=0,
        help="每 N 轮重试一次之前失败的标的；填 0 表示关闭",
    )
    parser.add_argument(
        "--stop-after-idle-rounds",
        type=int,
        default=2,
        help="连续 N 轮没有新增进展时停止；填 0 表示关闭",
    )
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--symbols", nargs="*")
    parser.set_defaults(resume=True)
    parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="不续跑最近一次匹配的未完成任务，而是新建一次回填任务",
    )


def _serialize(value: Any) -> str:
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json(indent=2)
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _default_window_sizes(runtime, frequency: str) -> list[int]:
    if frequency == "daily":
        return list(runtime.config.build_defaults.daily_window_sizes)
    return list(runtime.config.build_defaults.minute_window_sizes)


def _cached_symbols(runtime, frequency: str) -> list[str]:
    if hasattr(runtime.store, "list_cached_symbols"):
        return runtime.store.list_cached_symbols(frequency)
    return []


def _status_payload(runtime) -> dict[str, Any]:
    status = runtime.data_service.get_system_status()
    if hasattr(status, "model_dump"):
        return status.model_dump(mode="json")
    if isinstance(status, dict):
        return status
    return dict(status)


def _status_backfill_payload(runtime, *, frequency: str) -> Any:
    latest_backfill = runtime.data_service.get_backfill_status(frequency=frequency)
    if hasattr(latest_backfill, "model_dump"):
        return latest_backfill.model_dump(mode="json")
    return latest_backfill


def _status_payload_with_index_health(runtime, *, frequency: str | None = None) -> dict[str, Any]:
    payload = _status_payload(runtime)

    if frequency:
        payload["latest_backfill"] = _status_backfill_payload(runtime, frequency=frequency)
        cache_status = payload.get("cache_status") or {}
        payload["cache_status"] = {frequency: cache_status[frequency]} if frequency in cache_status else {}
        index_status = payload.get("index_status") or {}
        payload["index_status"] = {
            key: value
            for key, value in index_status.items()
            if isinstance(value, Mapping) and value.get("frequency") == frequency
        }
        return attach_index_health(runtime, payload, frequencies=[frequency])

    return attach_index_health(runtime, payload)


def _index_rebuild_state(runtime, *, frequency: str, target_window_sizes: list[int]) -> dict[str, Any]:
    status_payload = _status_payload(runtime)
    cache_for_frequency = (status_payload.get("cache_status") or {}).get(frequency, {})
    cached_symbols = int(cache_for_frequency.get("cached_symbols", 0) or 0)
    cache_latest_data_at = latest_data_at(cache_for_frequency.get("data_freshness") or {})
    index_status = status_payload.get("index_status") or {}
    matching_indexes = {
        int(value.get("window_size")): value
        for value in index_status.values()
        if value.get("frequency") == frequency and value.get("window_size") is not None
    }
    missing_indexes = [window for window in target_window_sizes if not runtime.index_service.exists(frequency, window)]
    stale_indexes = sorted(
        window
        for window in target_window_sizes
        if window not in missing_indexes
        and window in matching_indexes
        and index_entry_is_stale(
            matching_indexes[window],
            cached_symbols=cached_symbols,
            latest_data_at=cache_latest_data_at,
        )
    )
    return {
        "cached_symbols": cached_symbols,
        "latest_data_at": cache_latest_data_at,
        "missing_indexes": missing_indexes,
        "stale_indexes": stale_indexes,
    }


def _build_indexes(runtime, *, frequency: str, window_sizes: list[int]) -> dict[str, Any]:
    cached_symbols = _cached_symbols(runtime, frequency)
    summaries: list[dict[str, Any]] = []
    if not cached_symbols:
        return {
            "rebuild_triggered": False,
            "reason": "no_cached_symbols",
            "window_sizes": window_sizes,
            "cached_symbols": 0,
            "builds": summaries,
        }

    for window_size in window_sizes:
        if frequency == "daily" and len(cached_symbols) >= 1000 and hasattr(runtime.index_service, "build_compact"):
            build_summary = runtime.index_service.build_compact(
                feature_service=runtime.feature_service,
                frequency=frequency,
                window_size=window_size,
                symbols=cached_symbols,
            )
        else:
            feature_frame = runtime.feature_service.build_feature_frame(
                frequency=frequency,
                window_size=window_size,
                symbols=cached_symbols,
            )
            if feature_frame.matrix.size == 0:
                summaries.append(
                    {
                        "frequency": frequency,
                        "window_size": window_size,
                        "status": "skipped",
                        "reason": "no_features",
                    }
                )
                continue
            build_summary = runtime.index_service.build(
                feature_frame=feature_frame,
                frequency=frequency,
                window_size=window_size,
            )
        summaries.append(
            {
                "status": "built",
                **(build_summary.model_dump(mode="json") if hasattr(build_summary, "model_dump") else build_summary),
            }
        )

    return {
        "rebuild_triggered": True,
        "reason": "completed",
        "window_sizes": window_sizes,
        "cached_symbols": len(cached_symbols),
        "builds": summaries,
    }


def handle_bootstrap(with_sample: bool) -> None:
    runtime = get_runtime()
    summary = runtime.data_service.bootstrap(with_sample=with_sample)
    print(_serialize(summary))


def handle_build(request: BuildRequest) -> None:
    runtime = get_runtime()
    if not request.skip_refresh:
        runtime.data_service.refresh_market_data(
            frequency=request.frequency,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    build_symbols = request.symbols or _cached_symbols(runtime, request.frequency)
    if (
        request.frequency == "daily"
        and request.start_date is None
        and request.end_date is None
        and len(build_symbols) >= 1000
        and hasattr(runtime.index_service, "build_compact")
    ):
        summary = runtime.index_service.build_compact(
            feature_service=runtime.feature_service,
            frequency=request.frequency,
            window_size=request.window_size,
            symbols=build_symbols,
        )
    else:
        feature_frame = runtime.feature_service.build_feature_frame(
            frequency=request.frequency,
            window_size=request.window_size,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        summary = runtime.index_service.build(
            feature_frame=feature_frame,
            frequency=request.frequency,
            window_size=request.window_size,
        )
    print(_serialize(summary))


def handle_search(request: SearchRequest) -> None:
    runtime = get_runtime()
    response = runtime.search_service.search(request)
    print(response.model_dump_json(indent=2))


def handle_predict(request: PredictionRequest) -> None:
    runtime = get_runtime()
    response = runtime.prediction_service.predict(request)
    print(response.model_dump_json(indent=2))


def handle_backtest_prediction(
    *,
    start: date,
    end: date,
    sample_size: int,
    seed: int,
    horizons: list[int],
    window_sizes: list[int],
    top_k: int,
    target_accuracy: float,
    confidence_threshold: float,
) -> None:
    runtime = get_runtime()
    response = runtime.prediction_service.backtest(
        start=start,
        end=end,
        sample_size=sample_size,
        seed=seed,
        horizons=horizons,
        window_sizes=window_sizes,
        top_k=top_k,
        target_accuracy=target_accuracy,
        confidence_threshold=confidence_threshold,
    )
    print(response.model_dump_json(indent=2))


def handle_gpu_prediction_probe(config: GpuProbeConfig) -> None:
    runtime = get_runtime()
    print(_serialize(run_gpu_next_day_probe(runtime.store, config)))


def handle_train_prediction(approved_run_id: str | None = None) -> None:
    runtime = get_runtime()
    print(_serialize(runtime.prediction_service.train_model(approved_run_id=approved_run_id)))


def handle_prediction_protocol_entrypoint(command: str, **kwargs: Any) -> None:
    print(
        _serialize(
            {
                "status": "ready",
                "command": command,
                "protocol": "free_data_first_dev_train_dev_valid_test_lockbox",
                "implemented_modules": [
                    "split_protocol",
                    "tensor_cache",
                    "factor_cache_manager",
                    "level2_schema",
                    "level2_importer",
                ],
                "arguments": kwargs,
                "gpu_policy": {
                    "gpu_first": True,
                    "cpu_io_stages": ["AKShare/network", "Parquet/DuckDB/JSON IO", "pandas joins"],
                    "single_gpu_training": "serial on one CUDA device; subagents are for data/factor/report tasks",
                },
                "level2_policy": "reserved schema only; mobile Tonghuashun Level2 is not a programmatic training source",
            }
        )
    )


def handle_backfill(
    *,
    frequency: str,
    batch_size: int,
    max_symbols: int | None,
    start_date: date | None,
    end_date: date | None,
    symbols: list[str] | None,
    resume: bool,
    retry_failures: bool,
) -> None:
    runtime = get_runtime()
    summary = runtime.data_service.backfill_market_data(
        frequency=frequency,
        batch_size=batch_size,
        max_symbols=max_symbols,
        start_date=start_date,
        end_date=end_date,
        symbols=symbols,
        resume=resume,
        retry_failures=retry_failures,
    )
    print(_serialize(summary))


def handle_backfill_loop(
    *,
    frequency: str,
    batch_size: int,
    max_symbols_per_round: int | None,
    max_rounds: int,
    round_interval_seconds: float,
    retry_failures_every: int,
    stop_after_idle_rounds: int,
    start_date: date | None,
    end_date: date | None,
    symbols: list[str] | None,
    resume: bool,
) -> None:
    runtime = get_runtime()
    summary = runtime.data_service.run_backfill_loop(
        frequency=frequency,
        batch_size=batch_size,
        max_symbols_per_round=max_symbols_per_round,
        max_rounds=max_rounds,
        round_interval_seconds=round_interval_seconds,
        retry_failures_every=retry_failures_every,
        stop_after_idle_rounds=stop_after_idle_rounds,
        start_date=start_date,
        end_date=end_date,
        symbols=symbols,
        resume=resume,
    )
    print(_serialize(summary))


def handle_maintain(
    *,
    frequency: str,
    batch_size: int,
    max_symbols_per_round: int | None,
    max_rounds: int,
    round_interval_seconds: float,
    retry_failures_every: int,
    stop_after_idle_rounds: int,
    start_date: date | None,
    end_date: date | None,
    symbols: list[str] | None,
    resume: bool,
    window_sizes: list[int] | None,
    skip_rebuild: bool,
    force_rebuild: bool,
) -> None:
    runtime = get_runtime()
    backfill_summary = runtime.data_service.run_backfill_loop(
        frequency=frequency,
        batch_size=batch_size,
        max_symbols_per_round=max_symbols_per_round,
        max_rounds=max_rounds,
        round_interval_seconds=round_interval_seconds,
        retry_failures_every=retry_failures_every,
        stop_after_idle_rounds=stop_after_idle_rounds,
        start_date=start_date,
        end_date=end_date,
        symbols=symbols,
        resume=resume,
    )

    target_window_sizes = window_sizes or _default_window_sizes(runtime, frequency)
    rebuild_state = _index_rebuild_state(runtime, frequency=frequency, target_window_sizes=target_window_sizes)
    missing_indexes = rebuild_state["missing_indexes"]
    stale_indexes = rebuild_state["stale_indexes"]
    rebuild_window_sizes: list[int] = []
    rebuild_reason = None
    if skip_rebuild:
        rebuild_summary = {
            "rebuild_triggered": False,
            "reason": "skipped_by_flag",
            "window_sizes": [],
            "target_window_sizes": target_window_sizes,
            "missing_indexes": missing_indexes,
            "stale_indexes": stale_indexes,
            "cached_symbols": len(_cached_symbols(runtime, frequency)),
            "builds": [],
        }
    elif force_rebuild:
        rebuild_reason = "forced"
        rebuild_window_sizes = list(target_window_sizes)
    elif backfill_summary.get("new_completed_symbols_total", 0) > 0:
        rebuild_reason = "new_cached_symbols"
        rebuild_window_sizes = list(target_window_sizes)
    elif missing_indexes:
        rebuild_reason = "missing_indexes"
        rebuild_window_sizes = list(dict.fromkeys([*missing_indexes, *stale_indexes]))
    elif stale_indexes:
        rebuild_reason = "stale_indexes"
        rebuild_window_sizes = list(stale_indexes)
    else:
        rebuild_reason = None

    if skip_rebuild:
        pass
    elif rebuild_reason is None:
        rebuild_summary = {
            "rebuild_triggered": False,
            "reason": "no_cache_change",
            "window_sizes": [],
            "target_window_sizes": target_window_sizes,
            "missing_indexes": missing_indexes,
            "stale_indexes": stale_indexes,
            "builds": [],
        }
    else:
        rebuild_summary = _build_indexes(runtime, frequency=frequency, window_sizes=rebuild_window_sizes)
        rebuild_summary["reason"] = rebuild_reason
        rebuild_summary["target_window_sizes"] = target_window_sizes
        rebuild_summary["missing_indexes"] = missing_indexes
        rebuild_summary["stale_indexes"] = stale_indexes

    summary = {
        "frequency": frequency,
        "maintenance_completed": True,
        "backfill": backfill_summary,
        "rebuild": rebuild_summary,
    }
    print(_serialize(summary))


def handle_status(frequency: str | None = None) -> None:
    runtime = get_runtime()
    print(_serialize(_status_payload_with_index_health(runtime, frequency=frequency)))


def handle_doctor(
    *,
    symbol: str | None,
    end_date: str | None,
    frequency: str,
    window_size: int,
    top_k: int,
) -> None:
    runtime = get_runtime()
    request = None
    if symbol and end_date:
        request = SearchRequest(
            symbol=symbol,
            end_date=end_date,
            frequency=frequency,
            window_size=window_size,
            top_k=top_k,
        )
    report = build_doctor_report(runtime, request=request)
    print(_serialize(report))


def handle_serve(*, host: str, port: int, log_level: str, reload: bool, port_scan_limit: int) -> None:
    launch = build_launch_info(host, port, scan_limit=port_scan_limit)
    print(
        _serialize(
            {
                "status": "starting",
                "host": launch.host,
                "port": launch.port,
                "browser_url": launch.browser_url,
                "access_urls": launch.access_urls,
            }
        )
    )
    uvicorn.run(
        "ashare_similarity.app:create_app",
        factory=True,
        host=launch.host,
        port=launch.port,
        log_level=log_level,
        reload=reload,
    )


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "bootstrap":
        handle_bootstrap(with_sample=args.with_sample)
        return

    if args.command == "build":
        build_request = BuildRequest(
            frequency=args.frequency,
            window_size=args.window_size,
            start_date=_parse_date(args.start_date),
            end_date=_parse_date(args.end_date),
            symbols=args.symbols or None,
            skip_refresh=bool(getattr(args, "skip_refresh", False)),
        )
        handle_build(build_request)
        return

    if args.command == "search":
        search_request = SearchRequest(
            symbol=args.symbol,
            end_date=args.end_date,
            frequency=args.frequency,
            window_size=args.window_size,
            top_k=args.top_k,
            search_scope=args.search_scope,
        )
        handle_search(search_request)
        return

    if args.command == "predict":
        prediction_request = PredictionRequest(
            symbol=args.symbol,
            as_of_date=args.as_of_date,
            frequency=args.frequency,
            horizons=args.horizons,
            window_sizes=args.window_sizes,
            top_k=args.top_k,
        )
        handle_predict(prediction_request)
        return

    if args.command == "backtest-prediction":
        handle_backtest_prediction(
            start=_parse_date(args.start),
            end=_parse_date(args.end),
            sample_size=args.sample_size,
            seed=args.seed,
            horizons=args.horizons,
            window_sizes=args.window_sizes,
            top_k=args.top_k,
            target_accuracy=args.target_accuracy,
            confidence_threshold=args.confidence_threshold,
        )
        return

    if args.command == "gpu-prediction-probe":
        handle_gpu_prediction_probe(
            GpuProbeConfig(
                start=_parse_date(args.start),
                train_end=_parse_date(args.train_end),
                test_start=_parse_date(args.test_start),
                end=_parse_date(args.end),
                train_rows=args.train_rows,
                test_rows=args.test_rows,
                seed=args.seed,
                max_symbols=args.max_symbols,
                epochs=args.epochs,
                target_accuracy=args.target_accuracy,
                validation_fraction=args.validation_fraction,
                embargo_label_days=args.embargo_label_days,
                short_only=args.short_only,
                min_turnover=args.min_turnover,
                min_amount=args.min_amount,
                min_volume_z=args.min_volume_z,
                min_amount_z=args.min_amount_z,
                min_range_pct=args.min_range_pct,
                min_volatility_pct=args.min_volatility_pct,
                min_abnormal_flags=args.min_abnormal_flags,
                min_phase_days_3=args.min_phase_days_3,
                min_active_anomaly_rank=args.min_active_anomaly_rank,
                main_board_only=args.main_board_only,
                min_label_return_pct=args.min_label_return_pct,
                label_target=args.label_target,
                target_high_return_pct=args.target_high_return_pct,
                feature_set=args.feature_set,
                max_selected_features=args.max_selected_features,
                feature_selection_method=args.feature_selection_method,
                candidate_family=args.candidate_family,
                intraday_factor_frequency=args.intraday_factor_frequency,
                use_feature_cache=args.feature_cache,
                refresh_feature_cache=args.refresh_feature_cache,
                lockbox_role=args.lockbox_role,
                selector_coverage_weight=args.selector_coverage_weight,
                exclude_feature_prefix=tuple(args.exclude_feature_prefix) if args.exclude_feature_prefix else (),
            )
        )
        return

    if args.command == "prediction-build-dataset":
        handle_prediction_protocol_entrypoint(
            args.command,
            start=args.start,
            train_end=args.train_end,
            test_start=args.test_start,
            end=args.end,
        )
        return

    if args.command == "prediction-walkforward":
        handle_prediction_protocol_entrypoint(
            args.command,
            start=args.start,
            train_end=args.train_end,
            test_start=args.test_start,
            end=args.end,
        )
        return

    if args.command == "prediction-lockbox":
        handle_prediction_protocol_entrypoint(args.command, approved_run_id=args.approved_run_id)
        return

    if args.command == "train-prediction":
        handle_train_prediction(approved_run_id=getattr(args, "approved_run_id", None))
        return

    if args.command == "backfill":
        handle_backfill(
            frequency=args.frequency,
            batch_size=args.batch_size,
            max_symbols=getattr(args, "max_symbols", None),
            start_date=_parse_date(args.start_date),
            end_date=_parse_date(args.end_date),
            symbols=getattr(args, "symbols", None) or None,
            resume=bool(args.resume),
            retry_failures=bool(getattr(args, "retry_failures", False)),
        )
        return

    if args.command == "backfill-loop":
        handle_backfill_loop(
            frequency=args.frequency,
            batch_size=args.batch_size,
            max_symbols_per_round=getattr(args, "max_symbols_per_round", None),
            max_rounds=args.max_rounds,
            round_interval_seconds=args.round_interval_seconds,
            retry_failures_every=args.retry_failures_every,
            stop_after_idle_rounds=args.stop_after_idle_rounds,
            start_date=_parse_date(args.start_date),
            end_date=_parse_date(args.end_date),
            symbols=getattr(args, "symbols", None) or None,
            resume=bool(args.resume),
        )
        return

    if args.command == "maintain":
        handle_maintain(
            frequency=args.frequency,
            batch_size=args.batch_size,
            max_symbols_per_round=getattr(args, "max_symbols_per_round", None),
            max_rounds=args.max_rounds,
            round_interval_seconds=args.round_interval_seconds,
            retry_failures_every=args.retry_failures_every,
            stop_after_idle_rounds=args.stop_after_idle_rounds,
            start_date=_parse_date(args.start_date),
            end_date=_parse_date(args.end_date),
            symbols=getattr(args, "symbols", None) or None,
            resume=bool(args.resume),
            window_sizes=getattr(args, "window_sizes", None) or None,
            skip_rebuild=bool(getattr(args, "skip_rebuild", False)),
            force_rebuild=bool(getattr(args, "force_rebuild", False)),
        )
        return

    if args.command == "status":
        handle_status(frequency=getattr(args, "frequency", None))
        return

    if args.command == "doctor":
        handle_doctor(
            symbol=getattr(args, "symbol", None),
            end_date=getattr(args, "end_date", None),
            frequency=args.frequency,
            window_size=args.window_size,
            top_k=args.top_k,
        )
        return

    if args.command == "serve":
        handle_serve(
            host=args.host,
            port=args.port,
            log_level=args.log_level,
            reload=bool(args.reload),
            port_scan_limit=args.port_scan_limit,
        )
        return

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from datetime import date, datetime, timedelta, timezone
from time import sleep as default_sleep
from typing import Any, Callable

import pandas as pd

from ashare_similarity.config import AppConfig
from ashare_similarity.context.service import ContextService
from ashare_similarity.data.base import Frequency, SecurityProfile
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.data.universe import UniverseService
from ashare_similarity.schemas import BackfillFailure, BackfillStatus, CacheStatus, DataFreshness, SystemStatus


SUCCESSFUL_BACKFILL_STATUSES = {"completed", "ignored_st"}


class DataService:
    def __init__(
        self,
        config: AppConfig,
        store: LocalDataStore,
        provider,
        universe_service: UniverseService,
        context_service: ContextService,
    ) -> None:
        self.config = config
        self.store = store
        self.provider = provider
        self.universe_service = universe_service
        self.context_service = context_service

    def _utcnow(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _backfill_snapshot_path(self, frequency: Frequency) -> Any:
        return self.config.storage.report_dir / f"backfill_runtime_{frequency}.json"

    def _load_backfill_snapshot_payload(self, frequency: Frequency) -> dict[str, Any] | None:
        path = self._backfill_snapshot_path(frequency)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _is_store_lock_error(self, exc: Exception) -> bool:
        checker = getattr(self.store, "_is_duckdb_lock_error", None)
        if callable(checker):
            try:
                return bool(checker(exc))
            except Exception:
                return False
        message = str(exc).lower()
        return "workspace.duckdb" in message and ("already open" in message or "进程无法访问" in message)

    def _write_backfill_status_snapshot(self, status: BackfillStatus) -> None:
        path = self._backfill_snapshot_path(status.frequency)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = status.model_dump(mode="json")
        payload["captured_at"] = self._utcnow().isoformat()
        payload["process_id"] = os.getpid()
        try:
            payload["cached_symbols"] = len(self.store.list_cached_symbols(status.frequency))
            payload["data_freshness"] = self.get_data_freshness(status.frequency).model_dump(mode="json")
        except Exception:
            payload["cached_symbols"] = None
            payload["data_freshness"] = None
        temp_path = path.with_name(f"{path.name}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        temp_path.replace(path)

    def _read_backfill_status_snapshot(
        self,
        *,
        frequency: Frequency | None = None,
        run_id: str | None = None,
    ) -> BackfillStatus | None:
        candidate_frequencies: list[Frequency] = [frequency] if frequency is not None else ["daily", "1", "5", "15", "30", "60"]
        for candidate_frequency in candidate_frequencies:
            payload = self._load_backfill_snapshot_payload(candidate_frequency)
            if payload is None:
                continue
            if run_id is not None and payload.get("run_id") != run_id:
                continue
            try:
                return BackfillStatus.model_validate(payload)
            except Exception:
                continue
        return None

    def _active_backfill_snapshot(self, frequency: Frequency = "daily") -> BackfillStatus | None:
        payload = self._load_backfill_snapshot_payload(frequency)
        if payload is None or payload.get("status") != "running":
            return None
        if not self._snapshot_process_running(payload):
            return None
        path = self._backfill_snapshot_path(frequency)
        try:
            snapshot_age = self._utcnow() - datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            return None
        if snapshot_age > timedelta(minutes=max(int(self.config.backfill.stale_run_after_minutes), 0)):
            return None
        try:
            return BackfillStatus.model_validate(payload)
        except Exception:
            return None

    def _snapshot_process_running(self, payload: dict[str, Any] | None) -> bool:
        if not payload:
            return False
        try:
            pid = int(payload.get("process_id") or 0)
        except (TypeError, ValueError):
            return False
        if pid <= 0:
            return False
        if os.name == "nt":
            try:
                import ctypes

                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if not handle:
                    return False
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            except Exception:
                return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _build_filesystem_cache_status(
        self,
        frequency: Frequency,
        *,
        snapshot_payload: dict[str, Any] | None = None,
    ) -> CacheStatus:
        cached_symbols = 0
        if snapshot_payload is not None:
            cached_symbols = int(snapshot_payload.get("cached_symbols") or 0)
        if cached_symbols <= 0:
            fallback = getattr(self.store, "_list_cached_symbols_from_filesystem", None)
            if callable(fallback):
                cached_symbols = len(fallback(frequency))
        freshness_payload = snapshot_payload.get("data_freshness") if snapshot_payload is not None else None
        if freshness_payload:
            freshness = DataFreshness.model_validate(freshness_payload)
        else:
            fallback_freshness = getattr(self.store, "_get_freshness_from_filesystem", None)
            if callable(fallback_freshness):
                payload = fallback_freshness(frequency)
                freshness = (
                    DataFreshness(
                        data_source=str(payload["provider"]),
                        notice=json.dumps(payload["notice"], ensure_ascii=False)
                        if isinstance(payload.get("notice"), dict)
                        else payload.get("notice"),
                        last_refresh_at=payload.get("last_refresh_at"),
                        latest_data_at=payload.get("end_ts"),
                    )
                    if payload
                    else DataFreshness(data_source="akshare", notice=None, last_refresh_at=None, latest_data_at=None)
                )
            else:
                freshness = DataFreshness(data_source="akshare", notice=None, last_refresh_at=None, latest_data_at=None)
        if frequency != "daily":
            freshness.notice = self.config.data_source.minute_history_notice
        return CacheStatus(frequency=frequency, cached_symbols=cached_symbols, data_freshness=freshness)

    def _build_filesystem_index_status(self) -> dict[str, dict[str, Any]]:
        builds: dict[str, dict[str, Any]] = {}
        fallback = getattr(self.store, "_list_builds_from_filesystem", None)
        entries = fallback() if callable(fallback) else []
        for build in entries:
            key = f"{build['frequency']}_{build['window_size']}"
            builds[key] = {
                "frequency": build["frequency"],
                "window_size": build["window_size"],
                "backend": build["backend"],
                "rows_count": build["rows_count"],
                "built_at": build["built_at"],
                "metadata": build["metadata_json"],
            }
        return builds

    def bootstrap(self, with_sample: bool = False) -> dict[str, Any]:
        universe = self.universe_service.bootstrap()
        market = self.context_service.refresh_market_context()
        summary: dict[str, Any] = {
            "universe_count": int(len(universe)),
            "market_context_rows": int(len(market)),
            "sample_loaded": False,
        }
        if with_sample:
            preferred = ["600519", "000333", "601318", "300750", "600036", "002594", "600900", "000651", "601166", "300059"]
            available = set(universe["symbol"].astype(str).tolist())
            sample_symbols = [symbol for symbol in preferred if symbol in available]
            if not sample_symbols:
                sample_symbols = universe.head(10)["symbol"].tolist()
            sample_end = date.today()
            sample_start = sample_end - timedelta(days=180)
            sample_refresh = self.refresh_market_data(
                frequency="daily",
                symbols=sample_symbols,
                start_date=sample_start,
                end_date=sample_end,
            )
            summary["sample_loaded"] = True
            summary["sample_symbols"] = sample_symbols
            summary["sample_refresh"] = sample_refresh
        return summary

    def _resolve_symbols(self, symbols: list[str] | None) -> list[str]:
        if symbols:
            normalized = [symbol.strip().zfill(6) for symbol in symbols if symbol and symbol.strip()]
        else:
            normalized = self.universe_service.get_filtered_universe()["symbol"].tolist()
        seen: set[str] = set()
        resolved: list[str] = []
        for symbol in normalized:
            if symbol in seen:
                continue
            seen.add(symbol)
            resolved.append(symbol)
        return resolved

    def _collect_symbol_market_data(
        self,
        *,
        symbol: str,
        frequency: Frequency,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        try:
            profile = self.get_security_profile(symbol)
            if profile.is_st and self.config.quality.exclude_st:
                return {"symbol": symbol, "status": "ignored_st"}

            listing_days = self.universe_service.get_listing_days(symbol, as_of=end_date)

            bars = self.provider.fetch_price_history(
                symbol=symbol,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
                adjust=self.config.data_source.default_adjust,
            )
            if bars.empty:
                return {
                    "symbol": symbol,
                    "status": "failed",
                    "error": "No market data returned for the requested range.",
                }
            if listing_days is None and frequency == "daily":
                listing_days = int(len(bars))

            return {
                "symbol": symbol,
                "status": "completed",
                "rows": int(len(bars)),
                "bars": bars,
            }
        except Exception as exc:
            return {"symbol": symbol, "status": "failed", "error": str(exc)}

    def _refresh_symbol_data(
        self,
        *,
        symbol: str,
        frequency: Frequency,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        result = self._collect_symbol_market_data(
            symbol=symbol,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
        )
        if result["status"] != "completed":
            result.pop("bars", None)
            return result
        try:
            self.store.save_bars(symbol, frequency, result["bars"])
        except Exception as exc:
            return {"symbol": symbol, "status": "failed", "error": str(exc)}
        result.pop("bars", None)
        return result

    def _refresh_context_after_daily_update(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        symbols: list[str] | None,
        rebuild_industry_context: bool = True,
    ) -> pd.DataFrame:
        market = self.context_service.refresh_market_context(start_date=start_date, end_date=end_date)
        if rebuild_industry_context:
            del symbols
            enriched = self.enrich_universe_profiles()
            self.context_service.build_industry_context(enriched)
        return market

    def refresh_market_data(
        self,
        frequency: Frequency,
        symbols: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        refresh_context: bool = True,
        rebuild_industry_context: bool = True,
    ) -> dict[str, Any]:
        selected = self._resolve_symbols(symbols)
        completed_symbols: list[str] = []
        skipped_recent_listing_symbols: list[str] = []
        ignored_st_symbols: list[str] = []
        failed_symbols: list[dict[str, str]] = []

        for symbol in selected:
            result = self._refresh_symbol_data(
                symbol=symbol,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
            )
            status = result["status"]
            if status == "completed":
                completed_symbols.append(symbol)
                continue
            if status == "skipped_recent_listing":
                skipped_recent_listing_symbols.append(symbol)
                continue
            if status == "ignored_st":
                ignored_st_symbols.append(symbol)
                continue
            failed_symbols.append({"symbol": symbol, "error": str(result.get("error") or "Unknown error")})

        notice = None
        if frequency != "daily":
            notice = self.config.data_source.minute_history_notice
            provider_notice = self.provider.get_frequency_notice(frequency) if hasattr(self.provider, "get_frequency_notice") else None
            if provider_notice is not None:
                self.store.save_notice(frequency, provider_notice)

        if frequency == "daily" and refresh_context:
            market = self._refresh_context_after_daily_update(
                start_date=start_date,
                end_date=end_date,
                symbols=selected,
                rebuild_industry_context=rebuild_industry_context,
            )
        else:
            market = pd.DataFrame()

        return {
            "frequency": frequency,
            "symbols_requested": len(selected),
            "symbols_processed": len(completed_symbols),
            "completed_symbols": completed_symbols,
            "skipped_recent_listing": len(skipped_recent_listing_symbols),
            "skipped_recent_listing_symbols": skipped_recent_listing_symbols,
            "ignored_st_symbols": ignored_st_symbols,
            "failed_symbols": failed_symbols,
            "market_context_rows": len(market),
            "notice": notice,
        }

    def _resolve_backfill_workers(self, *, frequency: Frequency, batch_size: int) -> int:
        if frequency != "daily":
            return 1
        configured = max(int(self.config.backfill.max_workers), 1)
        return max(1, min(batch_size, configured))

    def _run_backfill_batch(
        self,
        *,
        batch: list[str],
        frequency: Frequency,
        start_date: date | None,
        end_date: date | None,
    ) -> list[tuple[str, dict[str, Any]]]:
        workers = self._resolve_backfill_workers(frequency=frequency, batch_size=len(batch))
        if workers <= 1 or len(batch) <= 1:
            return [
                (
                    symbol,
                    self._refresh_symbol_data(
                        symbol=symbol,
                        frequency=frequency,
                        start_date=start_date,
                        end_date=end_date,
                    ),
                )
                for symbol in batch
            ]

        order = {symbol: index for index, symbol in enumerate(batch)}
        results: list[tuple[str, dict[str, Any]]] = []
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=f"ashare-backfill-{frequency}") as executor:
            future_map = {
                executor.submit(
                    self._collect_symbol_market_data,
                    symbol=symbol,
                    frequency=frequency,
                    start_date=start_date,
                    end_date=end_date,
                ): symbol
                for symbol in batch
            }
            for future in as_completed(future_map):
                symbol = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover
                    result = {"symbol": symbol, "status": "failed", "error": str(exc)}
                results.append((symbol, result))
        results.sort(key=lambda item: order[item[0]])
        finalized: list[tuple[str, dict[str, Any]]] = []
        for symbol, result in results:
            if result.get("status") == "completed":
                try:
                    self.store.save_bars(symbol, frequency, result["bars"])
                    result = {
                        "symbol": symbol,
                        "status": "completed",
                        "rows": int(result.get("rows", 0) or 0),
                    }
                except Exception as exc:
                    result = {"symbol": symbol, "status": "failed", "error": str(exc)}
            else:
                result.pop("bars", None)
            finalized.append((symbol, result))
        return finalized

    def _summarize_backfill_progress(
        self,
        *,
        run_id: str,
        frequency: Frequency,
        mark_finished: bool = False,
        last_symbol: str | None = None,
    ) -> BackfillStatus:
        run = self.store.get_backfill_run(run_id)
        if run is None:
            raise ValueError(f"Backfill run {run_id} does not exist.")

        attempts = self.store.list_backfill_attempts(run_id)
        statuses = {record["symbol"]: record["status"] for record in attempts}
        completed_symbols = sum(1 for status in statuses.values() if status == "completed")
        skipped_recent_listing = sum(1 for status in statuses.values() if status == "skipped_recent_listing")
        ignored_st_symbols = sum(1 for status in statuses.values() if status == "ignored_st")
        failed_symbols = sum(1 for status in statuses.values() if status == "failed")
        remaining_symbols = max(run["requested_symbols"] - completed_symbols - skipped_recent_listing - ignored_st_symbols, 0)

        if remaining_symbols == 0:
            status = "completed"
        elif mark_finished:
            status = "partial"
        else:
            status = "running"

        finished_at = self._utcnow() if mark_finished else None
        self.store.update_backfill_run(
            run_id,
            attempted_symbols=len(statuses),
            completed_symbols=completed_symbols,
            failed_symbols=failed_symbols,
            skipped_recent_listing=skipped_recent_listing,
            ignored_st_symbols=ignored_st_symbols,
            remaining_symbols=remaining_symbols,
            status=status,
            last_symbol=last_symbol,
            finished_at=finished_at,
        )
        refreshed = self.store.get_backfill_run(run_id)
        if refreshed is None:
            raise ValueError(f"Backfill run {run_id} does not exist after update.")
        failures = self.store.list_backfill_attempts(run_id, statuses=["failed"], limit=10)
        return BackfillStatus(
            run_id=refreshed["run_id"],
            frequency=frequency,
            status=refreshed["status"],
            batch_size=refreshed["batch_size"],
            requested_symbols=refreshed["requested_symbols"],
            attempted_symbols=refreshed["attempted_symbols"],
            completed_symbols=refreshed["completed_symbols"],
            failed_symbols=refreshed["failed_symbols"],
            skipped_recent_listing=refreshed["skipped_recent_listing"],
            ignored_st_symbols=refreshed["ignored_st_symbols"],
            remaining_symbols=refreshed["remaining_symbols"],
            processed_count=refreshed["completed_symbols"],
            cursor=refreshed["attempted_symbols"],
            next_cursor=refreshed["attempted_symbols"],
            resume_cursor=refreshed["attempted_symbols"],
            started_at=refreshed["started_at"],
            finished_at=refreshed["finished_at"],
            start_date=refreshed["start_date"],
            end_date=refreshed["end_date"],
            last_symbol=refreshed["last_symbol"],
            retry_failures=refreshed["retry_failures"],
            sample_failures=[
                BackfillFailure(
                    symbol=record["symbol"],
                    error=record["error"],
                    attempted_at=record["attempted_at"],
                )
                for record in failures
            ],
        )

    def _should_process_backfill_symbol(self, status: str | None, *, retry_failures: bool) -> bool:
        if status is None:
            return True
        if status in SUCCESSFUL_BACKFILL_STATUSES:
            return False
        if status == "failed":
            return retry_failures
        return True

    def _load_cached_symbol_set(self, frequency: Frequency) -> set[str]:
        return {str(symbol).strip().zfill(6) for symbol in self.store.list_cached_symbols(frequency)}

    def _should_auto_mark_cached_backfill_symbols(
        self,
        *,
        symbols: list[str] | None,
        start_date: date | None,
        end_date: date | None,
    ) -> bool:
        return symbols is None and start_date is None and end_date is None

    def _mark_cached_backfill_attempts(
        self,
        *,
        run_id: str,
        target_symbols: list[str],
        status_map: dict[str, str],
        cached_symbols: set[str],
    ) -> list[str]:
        cached_hits: list[str] = []
        for symbol in target_symbols:
            if symbol not in cached_symbols:
                continue
            if status_map.get(symbol) in SUCCESSFUL_BACKFILL_STATUSES:
                continue
            self.store.record_backfill_attempt(
                run_id=run_id,
                symbol=symbol,
                status="completed",
            )
            status_map[symbol] = "completed"
            cached_hits.append(symbol)
        return cached_hits

    def backfill_market_data(
        self,
        *,
        frequency: Frequency,
        batch_size: int = 20,
        max_symbols: int | None = None,
        symbols: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        resume: bool = True,
        retry_failures: bool = False,
    ) -> dict[str, Any]:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0.")

        target_symbols = self._resolve_symbols(symbols)
        if not target_symbols:
            raise ValueError("No symbols available for backfill.")

        run = None
        if resume and hasattr(self.store, "find_resumable_backfill_run"):
            run = self.store.find_resumable_backfill_run(
                frequency=frequency,
                symbols=target_symbols,
                start_date=start_date,
                end_date=end_date,
            )

        if run is None:
            run_id = self.store.create_backfill_run(
                frequency=frequency,
                symbols=target_symbols,
                batch_size=batch_size,
                start_date=start_date,
                end_date=end_date,
                retry_failures=retry_failures,
            )
        else:
            run_id = run["run_id"]
            target_symbols = run["symbols"]
            retry_failures = retry_failures or run["retry_failures"]
            if self._is_stale_backfill_run(run):
                run["status"] = "partial"
            if hasattr(self.store, "update_backfill_run"):
                self.store.update_backfill_run(
                    run_id,
                    attempted_symbols=run["attempted_symbols"],
                    completed_symbols=run["completed_symbols"],
                    failed_symbols=run["failed_symbols"],
                    skipped_recent_listing=run["skipped_recent_listing"],
                    ignored_st_symbols=run["ignored_st_symbols"],
                    remaining_symbols=run["remaining_symbols"],
                    status=run["status"],
                    last_symbol=run["last_symbol"],
                    finished_at=run["finished_at"],
                    batch_size=batch_size,
                    retry_failures=retry_failures,
                )

        cached_symbols = set()
        if self._should_auto_mark_cached_backfill_symbols(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
        ):
            cached_symbols = self._load_cached_symbol_set(frequency)

        existing_attempts = self.store.list_backfill_attempts(run_id)
        status_map = {record["symbol"]: record["status"] for record in existing_attempts}
        completed_before = sum(1 for status in status_map.values() if status == "completed")
        failed_before = sum(1 for status in status_map.values() if status == "failed")
        already_cached_symbols = self._mark_cached_backfill_attempts(
            run_id=run_id,
            target_symbols=target_symbols,
            status_map=status_map,
            cached_symbols=cached_symbols,
        )
        pending_symbols = [
            symbol
            for symbol in target_symbols
            if self._should_process_backfill_symbol(status_map.get(symbol), retry_failures=retry_failures)
        ]
        if max_symbols is not None:
            pending_symbols = pending_symbols[:max_symbols]

        batch_summaries: list[dict[str, Any]] = []
        last_symbol: str | None = None
        initial_status = self._summarize_backfill_progress(
            run_id=run_id,
            frequency=frequency,
            mark_finished=False,
            last_symbol=run["last_symbol"] if run is not None else None,
        )
        self._write_backfill_status_snapshot(initial_status)

        for offset in range(0, len(pending_symbols), batch_size):
            batch = pending_symbols[offset : offset + batch_size]
            batch_completed: list[str] = []
            batch_failed: list[dict[str, str]] = []
            batch_skipped_recent_listing: list[str] = []
            batch_ignored_st: list[str] = []

            for symbol, result in self._run_backfill_batch(
                batch=batch,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
            ):
                last_symbol = symbol
                self.store.record_backfill_attempt(
                    run_id=run_id,
                    symbol=symbol,
                    status=result["status"],
                    error=result.get("error"),
                )
                if result["status"] == "completed":
                    batch_completed.append(symbol)
                elif result["status"] == "skipped_recent_listing":
                    batch_skipped_recent_listing.append(symbol)
                elif result["status"] == "ignored_st":
                    batch_ignored_st.append(symbol)
                else:
                    batch_failed.append({"symbol": symbol, "error": str(result.get("error") or "Unknown error")})

            progress = self._summarize_backfill_progress(
                run_id=run_id,
                frequency=frequency,
                mark_finished=False,
                last_symbol=last_symbol,
            )
            self._write_backfill_status_snapshot(progress)
            batch_summaries.append(
                {
                    "batch_index": offset // batch_size + 1,
                    "symbols_requested": len(batch),
                    "completed_symbols": batch_completed,
                    "skipped_recent_listing_symbols": batch_skipped_recent_listing,
                    "ignored_st_symbols": batch_ignored_st,
                    "failed_symbols": batch_failed,
                    "progress": progress.model_dump(mode="json"),
                }
            )

        if frequency == "daily" and pending_symbols:
            self._refresh_context_after_daily_update(
                start_date=start_date,
                end_date=end_date,
                symbols=pending_symbols,
                rebuild_industry_context=self.config.backfill.rebuild_industry_context_during_backfill,
            )

        final_status = self._summarize_backfill_progress(
            run_id=run_id,
            frequency=frequency,
            mark_finished=True,
            last_symbol=last_symbol,
        )
        self._write_backfill_status_snapshot(final_status)

        return {
            "run_id": run_id,
            "frequency": frequency,
            "batch_size": batch_size,
            "resume_used": run is not None,
            "retry_failures": retry_failures,
            "requested_symbols": len(target_symbols),
            "target_symbols": len(target_symbols),
            "cached_symbols_before": len(cached_symbols) if cached_symbols else len(self.store.list_cached_symbols(frequency)),
            "cached_symbols_after": len(self.store.list_cached_symbols(frequency)),
            "already_cached_symbols": len(already_cached_symbols),
            "symbols_scheduled_this_invocation": len(pending_symbols),
            "processed_batches": len(batch_summaries),
            "symbols_processed": final_status.completed_symbols,
            "new_completed_symbols": max(final_status.completed_symbols - completed_before - len(already_cached_symbols), 0),
            "new_failed_symbols": max(final_status.failed_symbols - failed_before, 0),
            "failed_symbols": [failure.model_dump(mode="json") for failure in final_status.sample_failures],
            "resume_cursor": final_status.resume_cursor,
            "completed": final_status.status == "completed",
            "latest_status": final_status.model_dump(mode="json"),
            "batches": batch_summaries,
        }

    def run_backfill_loop(
        self,
        *,
        frequency: Frequency,
        batch_size: int = 20,
        max_symbols_per_round: int | None = 100,
        max_rounds: int = 10,
        round_interval_seconds: float = 5.0,
        retry_failures_every: int = 0,
        stop_after_idle_rounds: int = 2,
        start_date: date | None = None,
        end_date: date | None = None,
        symbols: list[str] | None = None,
        resume: bool = True,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> dict[str, Any]:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0.")
        if max_rounds <= 0:
            raise ValueError("max_rounds must be greater than 0.")
        if max_symbols_per_round is not None and max_symbols_per_round <= 0:
            raise ValueError("max_symbols_per_round must be greater than 0 when provided.")
        if round_interval_seconds < 0:
            raise ValueError("round_interval_seconds must be greater than or equal to 0.")
        if retry_failures_every < 0:
            raise ValueError("retry_failures_every must be greater than or equal to 0.")
        if stop_after_idle_rounds < 0:
            raise ValueError("stop_after_idle_rounds must be greater than or equal to 0.")

        sleeper = sleep_fn or default_sleep
        rounds: list[dict[str, Any]] = []
        idle_rounds = 0
        previous_progress: tuple[Any, ...] | None = None
        stop_reason = "max_rounds_reached"
        new_completed_total = 0

        for round_number in range(1, max_rounds + 1):
            previous_status = self.get_backfill_status(frequency=frequency)
            previous_run_id = previous_status.run_id if previous_status is not None else None
            previous_cursor = previous_status.resume_cursor if previous_status is not None else 0
            previous_completed = previous_status.completed_symbols if previous_status is not None else 0

            round_retry_failures = retry_failures_every > 0 and round_number % retry_failures_every == 0
            summary = self.backfill_market_data(
                frequency=frequency,
                batch_size=batch_size,
                max_symbols=max_symbols_per_round,
                start_date=start_date,
                end_date=end_date,
                symbols=symbols,
                resume=resume,
                retry_failures=round_retry_failures,
            )
            latest_status = summary["latest_status"]
            new_completed = int(summary.get("new_completed_symbols", 0))
            new_completed_total += new_completed
            waiting_for_retry_window = (
                summary.get("symbols_scheduled_this_invocation", 0) == 0
                and not round_retry_failures
                and retry_failures_every > 0
                and int(latest_status.get("failed_symbols", 0)) > 0
            )
            current_progress = (
                latest_status.get("run_id"),
                latest_status.get("resume_cursor"),
                latest_status.get("completed_symbols"),
                latest_status.get("failed_symbols"),
                latest_status.get("remaining_symbols"),
            )
            progressed = current_progress != previous_progress or waiting_for_retry_window
            idle_rounds = 0 if progressed else idle_rounds + 1
            previous_progress = current_progress

            rounds.append(
                {
                    "round": round_number,
                    "run_id": latest_status.get("run_id"),
                    "continued_run": previous_run_id is not None and previous_run_id == latest_status.get("run_id"),
                    "resume_used": summary.get("resume_used", False),
                    "retry_failures": round_retry_failures,
                    "resume_cursor_before": previous_cursor,
                    "resume_cursor_after": latest_status.get("resume_cursor"),
                    "symbols_scheduled": summary.get("symbols_scheduled_this_invocation", 0),
                    "completed_symbols_before": previous_completed,
                    "completed_symbols": latest_status.get("completed_symbols", 0),
                    "new_completed_symbols": new_completed,
                    "failed_symbols": latest_status.get("failed_symbols", 0),
                    "remaining_symbols": latest_status.get("remaining_symbols", 0),
                    "status": latest_status.get("status"),
                    "awaiting_retry_window": waiting_for_retry_window,
                }
            )

            if latest_status.get("status") == "completed":
                stop_reason = "completed"
                break

            if summary.get("symbols_scheduled_this_invocation", 0) == 0 and not waiting_for_retry_window:
                stop_reason = "no_pending_symbols"
                break

            if stop_after_idle_rounds > 0 and idle_rounds >= stop_after_idle_rounds:
                stop_reason = "idle_round_limit_reached"
                break

            if round_number < max_rounds and round_interval_seconds > 0:
                sleeper(round_interval_seconds)

        final_status = self.get_backfill_status(frequency=frequency)
        return {
            "frequency": frequency,
            "batch_size": batch_size,
            "max_symbols_per_round": max_symbols_per_round,
            "max_rounds": max_rounds,
            "round_interval_seconds": round_interval_seconds,
            "retry_failures_every": retry_failures_every,
            "stop_after_idle_rounds": stop_after_idle_rounds,
            "rounds_completed": len(rounds),
            "new_completed_symbols_total": new_completed_total,
            "stop_reason": stop_reason,
            "latest_status": final_status.model_dump(mode="json") if final_status is not None else None,
            "rounds": rounds,
        }

    def get_backfill_status(
        self,
        *,
        run_id: str | None = None,
        frequency: Frequency | None = None,
    ) -> BackfillStatus | None:
        if run_id is None and frequency is not None:
            active_snapshot = self._active_backfill_snapshot(frequency)
            if active_snapshot is not None:
                return active_snapshot
        try:
            if run_id is not None:
                run = self.store.get_backfill_run(run_id)
            else:
                run = self.store.get_latest_backfill_run(frequency=frequency)
                if (
                    run is not None
                    and self._is_stale_backfill_run(run)
                    and int(run.get("attempted_symbols", 0) or 0) == 0
                    and hasattr(self.store, "get_latest_completed_backfill_run")
                ):
                    completed_run = self.store.get_latest_completed_backfill_run(frequency=frequency)
                    if completed_run is not None:
                        run = completed_run
            if run is None:
                return self._read_backfill_status_snapshot(frequency=frequency, run_id=run_id)
            failures = self.store.list_backfill_attempts(run["run_id"], statuses=["failed"], limit=10)
            status = "partial" if self._is_stale_backfill_run(run) else run["status"]
            return BackfillStatus(
                run_id=run["run_id"],
                frequency=run["frequency"],
                status=status,
                batch_size=run["batch_size"],
                requested_symbols=run["requested_symbols"],
                attempted_symbols=run["attempted_symbols"],
                completed_symbols=run["completed_symbols"],
                failed_symbols=run["failed_symbols"],
                skipped_recent_listing=run["skipped_recent_listing"],
                ignored_st_symbols=run["ignored_st_symbols"],
                remaining_symbols=run["remaining_symbols"],
                processed_count=run["completed_symbols"],
                cursor=run["attempted_symbols"],
                next_cursor=run["attempted_symbols"],
                resume_cursor=run["attempted_symbols"],
                started_at=run["started_at"],
                finished_at=run["finished_at"],
                start_date=run["start_date"],
                end_date=run["end_date"],
                last_symbol=run["last_symbol"],
                retry_failures=run["retry_failures"],
                sample_failures=[
                    BackfillFailure(
                        symbol=record["symbol"],
                        error=record["error"],
                        attempted_at=record["attempted_at"],
                    )
                    for record in failures
                ],
            )
        except Exception as exc:
            if not self._is_store_lock_error(exc):
                raise
            return self._read_backfill_status_snapshot(frequency=frequency, run_id=run_id)

    def enrich_universe_profiles(self, symbols: list[str] | None = None, *, allow_remote: bool = False) -> pd.DataFrame:
        universe = self.universe_service.get_universe().copy()
        if symbols:
            universe = universe[universe["symbol"].isin(symbols)]
        industries: list[str | None] = []
        listing_dates: list[str | None] = []
        for symbol in universe["symbol"]:
            profile = self.get_security_profile(symbol, allow_remote=allow_remote)
            industries.append(profile.industry)
            listing_dates.append(profile.listing_date.isoformat() if profile.listing_date else None)
        universe["industry"] = industries
        universe["listing_date"] = listing_dates
        return universe

    def load_price_history(
        self,
        symbol: str,
        frequency: Frequency,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        ensure_remote: bool = True,
    ) -> pd.DataFrame:
        symbol = symbol.strip().zfill(6)
        df = self.store.load_bars(symbol, frequency, start_date=start_date, end_date=end_date)
        if df.empty and ensure_remote:
            self.refresh_market_data(
                frequency=frequency,
                symbols=[symbol],
                start_date=start_date.date() if isinstance(start_date, datetime) else start_date,
                end_date=end_date.date() if isinstance(end_date, datetime) else end_date,
            )
            df = self.store.load_bars(symbol, frequency, start_date=start_date, end_date=end_date)
        return df

    def get_security_profile(self, symbol: str, *, allow_remote: bool = False) -> SecurityProfile:
        getter = getattr(self.universe_service, "get_profile")
        try:
            return getter(symbol, allow_remote=allow_remote)
        except TypeError:
            return getter(symbol)

    def _is_stale_backfill_run(self, run: dict[str, Any]) -> bool:
        if run.get("status") != "running":
            return False
        frequency = run.get("frequency")
        if frequency:
            snapshot_payload = self._load_backfill_snapshot_payload(frequency)
            if (
                snapshot_payload is not None
                and snapshot_payload.get("run_id") == run.get("run_id")
                and snapshot_payload.get("status") == "running"
                and not self._snapshot_process_running(snapshot_payload)
            ):
                return True
        timeout_minutes = max(int(self.config.backfill.stale_run_after_minutes), 0)
        if timeout_minutes <= 0:
            return False
        latest_attempts = self.store.list_backfill_attempts(run["run_id"], limit=1)
        last_activity = latest_attempts[0]["attempted_at"] if latest_attempts else run.get("started_at")
        if last_activity is None:
            return False
        return (self._utcnow() - last_activity) > timedelta(minutes=timeout_minutes)

    def get_symbol_name(self, symbol: str) -> str | None:
        universe = self.universe_service.get_universe()
        match = universe[universe["symbol"] == symbol]
        if match.empty:
            return None
        return str(match.iloc[0]["name"])

    def resolve_symbol_query(
        self,
        query: str,
        *,
        frequency: Frequency | None = None,
        prefer_cached: bool = True,
    ) -> dict[str, Any] | None:
        raw_query = str(query or "").strip()
        if not raw_query:
            return None

        normalized_query = raw_query.zfill(6) if raw_query.isdigit() else raw_query
        universe = self.universe_service.get_filtered_universe(allow_bootstrap=False).copy()
        if universe.empty:
            if normalized_query.isdigit():
                return {"symbol": normalized_query, "name": None, "match_type": "symbol"}
            return None

        universe["symbol"] = universe["symbol"].astype(str).str.zfill(6)
        universe["name_text"] = universe["name"].fillna("").astype(str) if "name" in universe.columns else ""
        candidates = universe
        if prefer_cached and frequency is not None:
            cached_symbols = {str(symbol).strip().zfill(6) for symbol in self.store.list_cached_symbols(frequency)}
            cached_candidates = candidates[candidates["symbol"].isin(cached_symbols)]
            if not cached_candidates.empty:
                candidates = cached_candidates

        lower_query = normalized_query.lower()
        exact_symbol = candidates[candidates["symbol"] == normalized_query].head(1)
        if not exact_symbol.empty:
            row = exact_symbol.iloc[0]
            return {"symbol": str(row["symbol"]), "name": row["name_text"] or None, "match_type": "symbol"}

        exact_name = candidates[candidates["name_text"].str.lower() == lower_query].head(2)
        if len(exact_name) == 1:
            row = exact_name.iloc[0]
            return {"symbol": str(row["symbol"]), "name": row["name_text"] or None, "match_type": "name"}

        partial_name = candidates[candidates["name_text"].str.contains(normalized_query, case=False, regex=False)].copy()
        if len(partial_name) == 1:
            row = partial_name.iloc[0]
            return {"symbol": str(row["symbol"]), "name": row["name_text"] or None, "match_type": "name_partial"}

        if normalized_query.isdigit():
            return {"symbol": normalized_query, "name": None, "match_type": "symbol"}
        return None

    def get_filtered_universe(self) -> pd.DataFrame:
        return self.universe_service.get_filtered_universe()

    def get_cached_symbol_choices(
        self,
        frequency: Frequency,
        *,
        query: str | None = None,
        limit: int = 12,
    ) -> dict[str, Any]:
        normalized_query = str(query or "").strip()
        if normalized_query.isdigit():
            normalized_query = normalized_query.zfill(6)

        cached_symbols = [str(symbol).strip().zfill(6) for symbol in self.store.list_cached_symbols(frequency)]
        total_cached = len(cached_symbols)
        if total_cached == 0:
            return {
                "frequency": frequency,
                "query": normalized_query,
                "total_cached": 0,
                "match_count": 0,
                "exact_match": None,
                "items": [],
            }

        universe = self.universe_service.get_filtered_universe(allow_bootstrap=False).copy()
        if universe.empty:
            choices = pd.DataFrame({"symbol": cached_symbols, "name": [None] * total_cached})
        else:
            universe["symbol"] = universe["symbol"].astype(str).str.zfill(6)
            choices = universe[universe["symbol"].isin(cached_symbols)][["symbol", "name"]].copy()
            missing_symbols = sorted(set(cached_symbols) - set(choices["symbol"].tolist()))
            if missing_symbols:
                choices = pd.concat(
                    [
                        choices,
                        pd.DataFrame({"symbol": missing_symbols, "name": [None] * len(missing_symbols)}),
                    ],
                    ignore_index=True,
                )

        choices["name"] = choices["name"].where(choices["name"].notna(), None)
        preferred_symbols = ("000333", "600036", "600900", "601166", "300750", "002594")
        choices["preferred_rank"] = choices["symbol"].apply(
            lambda value: preferred_symbols.index(value) if value in preferred_symbols else len(preferred_symbols)
        )

        exact_match: dict[str, Any] | None = None
        if normalized_query:
            lower_query = normalized_query.lower()
            choices["name_text"] = choices["name"].fillna("").astype(str)
            choices["symbol_rank"] = choices["symbol"].apply(
                lambda value: 0 if value == normalized_query else 1 if value.startswith(normalized_query) else 2
            )
            choices["name_rank"] = choices["name_text"].str.lower().apply(
                lambda value: 0 if lower_query and value.startswith(lower_query) else 1 if lower_query in value else 2
            )
            mask = (
                (choices["symbol"] == normalized_query)
                | choices["symbol"].str.contains(normalized_query, regex=False)
                | choices["name_text"].str.contains(normalized_query, case=False, regex=False)
            )
            filtered = choices[mask].copy()
            filtered = filtered.sort_values(
                by=["symbol_rank", "name_rank", "preferred_rank", "symbol"],
                kind="stable",
            )
            exact_row = filtered[filtered["symbol"] == normalized_query].head(1)
            if exact_row.empty:
                exact_row = filtered[filtered["name_text"].str.lower() == lower_query].head(1)
            if exact_row.empty and len(filtered) == 1:
                exact_row = filtered.head(1)
            if not exact_row.empty:
                exact_match = {
                    "symbol": str(exact_row.iloc[0]["symbol"]),
                    "name": exact_row.iloc[0]["name"] or None,
                }
        else:
            filtered = choices.sort_values(by=["preferred_rank", "symbol"], kind="stable").copy()

        items = filtered.head(max(int(limit), 1))[["symbol", "name"]].to_dict(orient="records")
        return {
            "frequency": frequency,
            "query": normalized_query,
            "total_cached": total_cached,
            "match_count": int(len(filtered)),
            "exact_match": exact_match,
            "items": [
                {
                    "symbol": str(item["symbol"]),
                    "name": item["name"] or None,
                }
                for item in items
            ],
        }

    def get_data_freshness(self, frequency: Frequency) -> DataFreshness:
        freshness = self.store.get_freshness(frequency)
        if frequency != "daily":
            freshness.notice = self.config.data_source.minute_history_notice
        return freshness

    def get_system_status(self) -> SystemStatus:
        universe = self.universe_service.get_universe(allow_bootstrap=False)
        filtered_universe = self.universe_service.get_filtered_universe(allow_bootstrap=False)
        active_daily_snapshot = self._active_backfill_snapshot("daily")
        active_daily_payload = self._load_backfill_snapshot_payload("daily") if active_daily_snapshot is not None else None

        if active_daily_snapshot is not None:
            cache_status = {
                frequency: (
                    self._build_filesystem_cache_status(frequency, snapshot_payload=active_daily_payload)
                    if frequency == "daily"
                    else self._build_filesystem_cache_status(frequency)
                )
                for frequency in ("daily", "1", "5", "15", "30", "60")
            }
            builds = self._build_filesystem_index_status()
            latest_backfill = active_daily_snapshot
        else:
            cache_status = {
                frequency: CacheStatus(
                    frequency=frequency,
                    cached_symbols=len(self.store.list_cached_symbols(frequency)),
                    data_freshness=self.get_data_freshness(frequency),
                )
                for frequency in ("daily", "1", "5", "15", "30", "60")
            }

            builds: dict[str, dict[str, Any]] = {}
            for build in self.store.list_builds():
                key = f"{build['frequency']}_{build['window_size']}"
                builds[key] = {
                    "frequency": build["frequency"],
                    "window_size": build["window_size"],
                    "backend": build["backend"],
                    "rows_count": build["rows_count"],
                    "built_at": build["built_at"],
                    "metadata": build["metadata_json"],
                }
            latest_backfill = self.get_backfill_status()

        return SystemStatus(
            universe_count=int(len(universe)),
            filtered_universe_count=int(len(filtered_universe)),
            cache_status=cache_status,
            index_status=builds,
            latest_backfill=latest_backfill,
        )

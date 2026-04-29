from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

# Keep local builds stable on Windows machines that are also running GPU
# training jobs. Polars reads these at import time, so set them before import.
os.environ.setdefault("POLARS_MAX_THREADS", "2")
os.environ.setdefault("RAYON_NUM_THREADS", "2")

import pandas as pd
import polars as pl

from ashare_similarity.config import AppConfig
from ashare_similarity.data.base import DateLike, Frequency, ProviderNotice, SecurityProfile, normalize_datetime
from ashare_similarity.schemas import DataFreshness


class LocalDataStore:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.cache_dir = self.config.storage.cache_dir
        self.db_path = self.config.storage.db_path

    def _utcnow(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def universe_path(self) -> Path:
        return self.config.storage.cache_dir / "universe.parquet"

    def profile_path(self, symbol: str) -> Path:
        return self.config.storage.cache_dir / "profiles" / f"{symbol}.json"

    def bars_path(self, symbol: str, frequency: Frequency) -> Path:
        base = self.config.storage.raw_dir / "bars" / frequency
        return base / f"{symbol}.parquet"

    def market_index_path(self, symbol: str, frequency: Frequency = "daily") -> Path:
        return self.config.storage.cache_dir / "market" / frequency / f"{symbol}.parquet"

    def market_context_path(self) -> Path:
        return self.config.storage.cache_dir / "context" / "market_context.parquet"

    def industry_context_path(self) -> Path:
        return self.config.storage.cache_dir / "context" / "industry_context.parquet"

    def industry_boards_path(self) -> Path:
        return self.config.storage.cache_dir / "context" / "industry_boards.parquet"

    def industry_membership_path(self) -> Path:
        return self.config.storage.cache_dir / "context" / "industry_membership.parquet"

    def industry_history_path(self, industry_code: str) -> Path:
        return self.config.storage.cache_dir / "context" / "industry_history" / f"{industry_code}.parquet"

    def notice_path(self, frequency: Frequency) -> Path:
        return self.config.storage.cache_dir / "context" / "notices" / f"{frequency}.json"

    def feature_dir(self, frequency: Frequency, window_size: int) -> Path:
        return self.config.storage.index_dir / frequency / f"window_{window_size}"

    def ensure_parent(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def save_universe(self, df: pd.DataFrame | pl.DataFrame) -> Path:
        path = self.universe_path()
        self.ensure_parent(path)
        frame = self._to_polars(df)
        self._atomic_write_parquet(path, frame)
        self._upsert_registry(
            category="universe_snapshot",
            frequency="meta",
            identifier="latest",
            path=path,
            row_count=frame.height,
            provider="akshare",
            start_ts=None,
            end_ts=None,
            metadata=None,
            notice_json=None,
        )
        return path

    def load_universe(self) -> pd.DataFrame:
        path = self.universe_path()
        if not path.exists():
            return pd.DataFrame(columns=["symbol", "name", "is_st"])
        return pl.read_parquet(path).to_pandas()

    def load_universe_frame(self) -> pl.DataFrame:
        path = self.universe_path()
        if not path.exists():
            return pl.DataFrame()
        return pl.read_parquet(path)

    def save_profile(self, profile: SecurityProfile) -> Path:
        path = self.profile_path(profile.symbol)
        self.ensure_parent(path)
        self._atomic_write_text(
            path,
            json.dumps(profile.to_record(), ensure_ascii=False, indent=2),
        )
        return path

    def load_profile(self, symbol: str) -> SecurityProfile | None:
        path = self.profile_path(symbol)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        listing_date = payload.get("listing_date")
        if listing_date:
            payload["listing_date"] = date.fromisoformat(listing_date)
        return SecurityProfile(**payload)

    def save_bars(self, symbol: str, frequency: Frequency, df: pd.DataFrame | pl.DataFrame) -> Path:
        frame = self._to_polars(df)
        path = self._save_frame(
            category="market_data",
            frame=frame,
            frequency=frequency,
            identifier=symbol,
            provider="akshare",
            merge_on=["symbol", "timestamp" if frequency != "daily" else "date"],
        )
        if path is None:
            path = self.bars_path(symbol, frequency)
        return path

    def load_bars(
        self,
        symbol: str,
        frequency: Frequency,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> pd.DataFrame:
        frame = self.load_market_data(
            frequency=frequency,
            symbols=[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        return frame.to_pandas() if not frame.is_empty() else pd.DataFrame()

    def list_cached_symbols(self, frequency: Frequency) -> list[str]:
        try:
            records = self._query_registry(category="market_data", frequency=frequency)
        except Exception as exc:
            if not self._is_duckdb_lock_error(exc):
                raise
            return self._list_cached_symbols_from_filesystem(frequency)
        return sorted({record["identifier"] for record in records if record["identifier"]})

    def save_market_index(self, symbol: str, df: pd.DataFrame | pl.DataFrame, frequency: Frequency = "daily") -> Path:
        frame = self._to_polars(df)
        path = self._save_frame(
            category="market_index_context",
            frame=frame,
            frequency=frequency,
            identifier=symbol,
            provider="akshare",
            merge_on=["index_symbol", "timestamp" if frequency != "daily" else "date"],
        )
        if path is None:
            path = self.market_index_path(symbol, frequency)
        return path

    def load_market_index(self, symbol: str, frequency: Frequency = "daily") -> pd.DataFrame:
        frame = self.load_market_index_data(frequency=frequency, symbols=[symbol])
        return frame.to_pandas() if not frame.is_empty() else pd.DataFrame()

    def save_market_context(self, df: pd.DataFrame | pl.DataFrame) -> Path:
        path = self.market_context_path()
        self.ensure_parent(path)
        frame = self._to_polars(df)
        self._atomic_write_parquet(path, frame)
        self._upsert_registry(
            category="market_context_summary",
            frequency="daily",
            identifier="latest",
            path=path,
            row_count=frame.height,
            provider="akshare",
            start_ts=None,
            end_ts=None,
            metadata=None,
            notice_json=None,
        )
        return path

    def load_market_context(self) -> pd.DataFrame:
        path = self.market_context_path()
        if not path.exists():
            return pd.DataFrame()
        return pl.read_parquet(path).to_pandas()

    def save_industry_context(self, df: pd.DataFrame | pl.DataFrame) -> Path:
        path = self.industry_context_path()
        self.ensure_parent(path)
        frame = self._to_polars(df)
        self._atomic_write_parquet(path, frame)
        self._upsert_registry(
            category="industry_context_summary",
            frequency="daily",
            identifier="latest",
            path=path,
            row_count=frame.height,
            provider="akshare",
            start_ts=None,
            end_ts=None,
            metadata=None,
            notice_json=None,
        )
        return path

    def load_industry_context(self) -> pd.DataFrame:
        path = self.industry_context_path()
        if not path.exists():
            return pd.DataFrame()
        return pl.read_parquet(path).to_pandas()

    def save_feature_artifacts(
        self,
        frequency: Frequency,
        window_size: int,
        matrix: Any,
        metadata: pd.DataFrame,
        manifest: dict[str, Any],
    ) -> dict[str, str]:
        directory = self.feature_dir(frequency, window_size)
        directory.mkdir(parents=True, exist_ok=True)
        matrix_path = directory / "matrix.npy"
        metadata_path = directory / "metadata.parquet"
        manifest_path = directory / "manifest.json"
        metadata_frame = pl.from_pandas(metadata)

        staged_paths = {
            "matrix": self._temporary_path(matrix_path),
            "metadata": self._temporary_path(metadata_path),
            "manifest": self._temporary_path(manifest_path),
        }
        try:
            self._write_numpy_file(staged_paths["matrix"], matrix)
            self._write_parquet_file(staged_paths["metadata"], metadata_frame)
            self._write_text_file(
                staged_paths["manifest"],
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            self._commit_file_batch(
                [
                    (staged_paths["matrix"], matrix_path),
                    (staged_paths["metadata"], metadata_path),
                    (staged_paths["manifest"], manifest_path),
                ]
            )
        finally:
            for staged_path in staged_paths.values():
                self._cleanup_file(staged_path)
        return {
            "matrix": str(matrix_path),
            "metadata": str(metadata_path),
            "manifest": str(manifest_path),
        }

    def load_feature_artifacts(self, frequency: Frequency, window_size: int) -> tuple[Any, pd.DataFrame, dict[str, Any]]:
        import numpy as np

        directory = self.feature_dir(frequency, window_size)
        matrix = np.load(directory / "matrix.npy")
        metadata = pl.read_parquet(directory / "metadata.parquet").to_pandas()
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        self._validate_feature_artifacts(
            directory=directory,
            matrix=matrix,
            metadata=metadata,
            manifest=manifest,
        )
        return matrix, metadata, manifest

    def record_build(
        self,
        frequency: Frequency,
        window_size: int,
        backend: str,
        rows_count: int,
        metadata_json: dict[str, Any],
    ) -> None:
        build_key = f"{frequency}:{window_size}"
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO builds AS target
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(build_key) DO UPDATE SET
                    frequency = excluded.frequency,
                    window_size = excluded.window_size,
                    backend = excluded.backend,
                    rows_count = excluded.rows_count,
                    built_at = excluded.built_at,
                    metadata_json = excluded.metadata_json
                """,
                [
                    build_key,
                    frequency,
                    window_size,
                    backend,
                    rows_count,
                    self._utcnow(),
                    json.dumps(metadata_json, ensure_ascii=False),
                ],
            )

    def get_build_info(self, frequency: Frequency, window_size: int) -> dict[str, Any] | None:
        if not self.db_path.exists():
            return None
        with self._connect(read_only=True) as connection:
            result = connection.execute(
                "SELECT * FROM builds WHERE build_key = ?",
                [f"{frequency}:{window_size}"],
            ).fetchone()
            if not result:
                return None
            columns = [item[0] for item in connection.description]
        payload = dict(zip(columns, result, strict=False))
        payload["metadata_json"] = json.loads(payload["metadata_json"])
        return payload

    def list_builds(self) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return self._list_builds_from_filesystem()
        try:
            with self._connect(read_only=True) as connection:
                rows = connection.execute(
                    """
                    SELECT
                        build_key,
                        frequency,
                        window_size,
                        backend,
                        rows_count,
                        built_at,
                        metadata_json
                    FROM builds
                    ORDER BY built_at DESC, build_key DESC
                    """
                ).fetchall()
        except Exception as exc:
            if not self._is_duckdb_lock_error(exc):
                raise
            return self._list_builds_from_filesystem()
        builds: list[dict[str, Any]] = []
        for row in rows:
            payload = {
                "build_key": row[0],
                "frequency": row[1],
                "window_size": row[2],
                "backend": row[3],
                "rows_count": row[4],
                "built_at": row[5],
                "metadata_json": json.loads(row[6]) if row[6] else {},
            }
            builds.append(payload)
        return builds

    def create_backfill_run(
        self,
        *,
        frequency: Frequency,
        symbols: Sequence[str],
        batch_size: int,
        start_date: date | None = None,
        end_date: date | None = None,
        retry_failures: bool = False,
    ) -> str:
        run_id = uuid4().hex
        now = self._utcnow()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO backfill_runs (
                    run_id,
                    frequency,
                    start_date,
                    end_date,
                    batch_size,
                    requested_symbols,
                    attempted_symbols,
                    completed_symbols,
                    failed_symbols,
                    skipped_recent_listing,
                    ignored_st_symbols,
                    remaining_symbols,
                    last_symbol,
                    status,
                    retry_failures,
                    symbols_json,
                    started_at,
                    finished_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run_id,
                    frequency,
                    start_date,
                    end_date,
                    batch_size,
                    len(symbols),
                    0,
                    0,
                    0,
                    0,
                    0,
                    len(symbols),
                    None,
                    "running",
                    retry_failures,
                    json.dumps(list(symbols), ensure_ascii=False),
                    now,
                    None,
                ],
            )
        return run_id

    def update_backfill_run(
        self,
        run_id: str,
        *,
        attempted_symbols: int,
        completed_symbols: int,
        failed_symbols: int,
        skipped_recent_listing: int,
        ignored_st_symbols: int,
        remaining_symbols: int,
        status: str,
        last_symbol: str | None = None,
        finished_at: datetime | None = None,
        batch_size: int | None = None,
        retry_failures: bool | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE backfill_runs
                SET attempted_symbols = ?,
                    completed_symbols = ?,
                    failed_symbols = ?,
                    skipped_recent_listing = ?,
                    ignored_st_symbols = ?,
                    remaining_symbols = ?,
                    status = ?,
                    last_symbol = COALESCE(?, last_symbol),
                    finished_at = ?,
                    batch_size = COALESCE(?, batch_size),
                    retry_failures = COALESCE(?, retry_failures)
                WHERE run_id = ?
                """,
                [
                    attempted_symbols,
                    completed_symbols,
                    failed_symbols,
                    skipped_recent_listing,
                    ignored_st_symbols,
                    remaining_symbols,
                    status,
                    last_symbol,
                    finished_at,
                    batch_size,
                    retry_failures,
                    run_id,
                ],
            )

    def record_backfill_attempt(
        self,
        *,
        run_id: str,
        symbol: str,
        status: str,
        error: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO backfill_attempts AS target
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id, symbol) DO UPDATE SET
                    status = excluded.status,
                    error = excluded.error,
                    attempted_at = excluded.attempted_at
                """,
                [
                    run_id,
                    symbol,
                    status,
                    error,
                    self._utcnow(),
                ],
            )

    def list_backfill_attempts(
        self,
        run_id: str,
        *,
        statuses: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        query = """
            SELECT run_id, symbol, status, error, attempted_at
            FROM backfill_attempts
            WHERE run_id = ?
        """
        parameters: list[Any] = [run_id]
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            query += f" AND status IN ({placeholders})"
            parameters.extend(list(statuses))
        query += " ORDER BY attempted_at DESC, symbol ASC"
        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)
        with self._connect(read_only=True) as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [
            {
                "run_id": row[0],
                "symbol": row[1],
                "status": row[2],
                "error": row[3],
                "attempted_at": row[4],
            }
            for row in rows
        ]

    def get_backfill_run(self, run_id: str) -> dict[str, Any] | None:
        if not self.db_path.exists():
            return None
        query = """
            SELECT
                run_id,
                frequency,
                start_date,
                end_date,
                batch_size,
                requested_symbols,
                attempted_symbols,
                completed_symbols,
                failed_symbols,
                skipped_recent_listing,
                ignored_st_symbols,
                remaining_symbols,
                last_symbol,
                status,
                retry_failures,
                symbols_json,
                started_at,
                finished_at
            FROM backfill_runs
            WHERE run_id = ?
        """
        with self._connect(read_only=True) as connection:
            row = connection.execute(query, [run_id]).fetchone()
        return self._row_to_backfill_run(row)

    def get_latest_backfill_run(self, frequency: Frequency | None = None) -> dict[str, Any] | None:
        if not self.db_path.exists():
            return None
        query = """
            SELECT
                run_id,
                frequency,
                start_date,
                end_date,
                batch_size,
                requested_symbols,
                attempted_symbols,
                completed_symbols,
                failed_symbols,
                skipped_recent_listing,
                ignored_st_symbols,
                remaining_symbols,
                last_symbol,
                status,
                retry_failures,
                symbols_json,
                started_at,
                finished_at
            FROM backfill_runs
        """
        parameters: list[Any] = []
        if frequency is not None:
            query += " WHERE frequency = ?"
            parameters.append(frequency)
        query += " ORDER BY started_at DESC, run_id DESC LIMIT 1"
        with self._connect(read_only=True) as connection:
            row = connection.execute(query, parameters).fetchone()
        return self._row_to_backfill_run(row)

    def get_latest_completed_backfill_run(self, frequency: Frequency | None = None) -> dict[str, Any] | None:
        if not self.db_path.exists():
            return None
        query = """
            SELECT
                run_id,
                frequency,
                start_date,
                end_date,
                batch_size,
                requested_symbols,
                attempted_symbols,
                completed_symbols,
                failed_symbols,
                skipped_recent_listing,
                ignored_st_symbols,
                remaining_symbols,
                last_symbol,
                status,
                retry_failures,
                symbols_json,
                started_at,
                finished_at
            FROM backfill_runs
            WHERE status = 'completed'
        """
        parameters: list[Any] = []
        if frequency is not None:
            query += " AND frequency = ?"
            parameters.append(frequency)
        query += " ORDER BY finished_at DESC, started_at DESC, run_id DESC LIMIT 1"
        with self._connect(read_only=True) as connection:
            row = connection.execute(query, parameters).fetchone()
        return self._row_to_backfill_run(row)

    def find_resumable_backfill_run(
        self,
        *,
        frequency: Frequency,
        symbols: Sequence[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any] | None:
        if not self.db_path.exists():
            return None
        query = """
            SELECT
                run_id,
                frequency,
                start_date,
                end_date,
                batch_size,
                requested_symbols,
                attempted_symbols,
                completed_symbols,
                failed_symbols,
                skipped_recent_listing,
                ignored_st_symbols,
                remaining_symbols,
                last_symbol,
                status,
                retry_failures,
                symbols_json,
                started_at,
                finished_at
            FROM backfill_runs
            WHERE frequency = ?
              AND status IN ('running', 'partial')
            ORDER BY started_at DESC, run_id DESC
        """
        with self._connect(read_only=True) as connection:
            rows = connection.execute(query, [frequency]).fetchall()
        requested = list(symbols)
        for row in rows:
            payload = self._row_to_backfill_run(row)
            if payload is None:
                continue
            if payload["start_date"] != start_date or payload["end_date"] != end_date:
                continue
            if payload["symbols"] == requested:
                return payload
        return None

    def update_freshness(
        self,
        dataset: str,
        frequency: str,
        notice: str | None,
        data_source: str = "akshare",
    ) -> None:
        self._upsert_registry(
            category="freshness",
            frequency=frequency,
            identifier=dataset,
            path=self.config.storage.db_path,
            row_count=1,
            provider=data_source,
            start_ts=None,
            end_ts=None,
            metadata=None,
            notice_json=notice,
        )

    def get_freshness(self, frequency: Frequency) -> DataFreshness:
        try:
            freshness = self.get_latest_refresh(category="market_data", frequency=frequency)
        except Exception as exc:
            if not self._is_duckdb_lock_error(exc):
                raise
            freshness = self._get_freshness_from_filesystem(frequency)
        if not freshness:
            return DataFreshness(data_source="akshare", notice=None, last_refresh_at=None, latest_data_at=None)
        notice = freshness["notice"]
        return DataFreshness(
            data_source=str(freshness["provider"]),
            notice=json.dumps(notice, ensure_ascii=False) if isinstance(notice, dict) else notice,
            last_refresh_at=freshness["last_refresh_at"],
            latest_data_at=freshness.get("end_ts"),
        )

    def save_market_data(
        self,
        frequency: str,
        symbol: str,
        frame: pl.DataFrame,
        *,
        provider: str,
        metadata: dict[str, Any] | None = None,
        notice: ProviderNotice | None = None,
    ) -> Path | None:
        return self._save_frame(
            category="market_data",
            frame=frame,
            frequency=frequency,
            identifier=symbol,
            provider=provider,
            metadata=metadata,
            notice=notice,
            merge_on=["symbol", "timestamp" if frequency != "daily" else "date"],
        )

    def load_market_data(
        self,
        frequency: str,
        *,
        symbols: Sequence[str] | None = None,
        start_date: DateLike | None = None,
        end_date: DateLike | None = None,
    ) -> pl.DataFrame:
        return self._load_frame(
            category="market_data",
            frequency=frequency,
            identifiers=symbols,
            start_date=start_date,
            end_date=end_date,
        )

    def save_market_index_data(
        self,
        frequency: str,
        index_symbol: str,
        frame: pl.DataFrame,
        *,
        provider: str,
        metadata: dict[str, Any] | None = None,
        notice: ProviderNotice | None = None,
    ) -> Path | None:
        return self._save_frame(
            category="market_index_context",
            frame=frame,
            frequency=frequency,
            identifier=index_symbol,
            provider=provider,
            metadata=metadata,
            notice=notice,
            merge_on=["index_symbol", "timestamp" if frequency != "daily" else "date"],
        )

    def load_market_index_data(
        self,
        frequency: str = "daily",
        *,
        symbols: Sequence[str] | None = None,
        start_date: DateLike | None = None,
        end_date: DateLike | None = None,
    ) -> pl.DataFrame:
        return self._load_frame(
            category="market_index_context",
            frequency=frequency,
            identifiers=symbols,
            start_date=start_date,
            end_date=end_date,
        )

    def save_industry_boards(self, frame: pl.DataFrame, *, provider: str, metadata: dict[str, Any] | None = None) -> Path | None:
        path = self.industry_boards_path()
        self.ensure_parent(path)
        if frame.is_empty():
            return None
        self._atomic_write_parquet(path, frame)
        self._upsert_registry(
            category="industry_boards",
            frequency="meta",
            identifier="latest",
            path=path,
            row_count=frame.height,
            provider=provider,
            start_ts=None,
            end_ts=None,
            metadata=metadata,
            notice_json=None,
        )
        return path

    def load_industry_boards(self) -> pl.DataFrame:
        path = self.industry_boards_path()
        if not path.exists():
            return pl.DataFrame()
        return pl.read_parquet(path)

    def save_industry_membership(
        self,
        frame: pl.DataFrame,
        *,
        provider: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path | None:
        path = self.industry_membership_path()
        self.ensure_parent(path)
        if frame.is_empty():
            return None
        payload = frame.unique(subset=["industry_code", "symbol"], keep="last")
        self._atomic_write_parquet(path, payload)
        self._upsert_registry(
            category="industry_membership",
            frequency="meta",
            identifier="latest",
            path=path,
            row_count=payload.height,
            provider=provider,
            start_ts=None,
            end_ts=None,
            metadata=metadata,
            notice_json=None,
        )
        return path

    def load_industry_membership(self, *, symbols: Sequence[str] | None = None) -> pl.DataFrame:
        path = self.industry_membership_path()
        if not path.exists():
            return pl.DataFrame()
        frame = pl.read_parquet(path)
        if symbols:
            frame = frame.filter(pl.col("symbol").is_in(list(symbols)))
        return frame

    def save_industry_history(
        self,
        industry_code: str,
        frame: pl.DataFrame,
        *,
        provider: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path | None:
        return self._save_frame(
            category="industry_context",
            frame=frame,
            frequency="daily",
            identifier=industry_code,
            provider=provider,
            metadata=metadata,
            merge_on=["industry_code", "date"],
        )

    def load_industry_history(
        self,
        *,
        industry_codes: Sequence[str] | None = None,
        start_date: DateLike | None = None,
        end_date: DateLike | None = None,
    ) -> pl.DataFrame:
        return self._load_frame(
            category="industry_context",
            frequency="daily",
            identifiers=industry_codes,
            start_date=start_date,
            end_date=end_date,
        )

    def save_notice(self, frequency: str, notice: ProviderNotice) -> Path:
        path = self.notice_path(frequency)
        self.ensure_parent(path)
        self._atomic_write_text(path, notice.to_json())
        self._upsert_registry(
            category="provider_notice",
            frequency=frequency,
            identifier="latest",
            path=path,
            row_count=1,
            provider=notice.provider,
            start_ts=None,
            end_ts=None,
            metadata=None,
            notice_json=notice.to_json(),
        )
        return path

    def load_notice(self, frequency: str) -> dict[str, Any] | None:
        path = self.notice_path(frequency)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def get_latest_refresh(self, *, category: str, frequency: str | None = None) -> dict[str, Any] | None:
        records = self._query_registry(category=category, frequency=frequency)
        if not records:
            return None
        latest = max(records, key=lambda item: item["last_refresh_at"] or datetime.min)
        notice_payload = None
        if frequency:
            notice_payload = self.load_notice(frequency)
        elif latest["notice_json"]:
            try:
                notice_payload = json.loads(latest["notice_json"])
            except json.JSONDecodeError:
                notice_payload = latest["notice_json"]
        return {
            "last_refresh_at": latest["last_refresh_at"],
            "start_ts": latest["start_ts"],
            "end_ts": latest["end_ts"],
            "provider": latest["provider"],
            "notice": notice_payload,
            "path": latest["path"],
        }

    def _save_frame(
        self,
        *,
        category: str,
        frame: pl.DataFrame,
        provider: str,
        frequency: str | None = None,
        identifier: str | None = None,
        metadata: dict[str, Any] | None = None,
        notice: ProviderNotice | None = None,
        merge_on: Sequence[str] | None = None,
    ) -> Path | None:
        if frame.is_empty():
            return None
        path = self._dataset_path(category=category, frequency=frequency, identifier=identifier)
        self.ensure_parent(path)
        payload = frame.sort(self._sort_columns(frame))
        if path.exists():
            current = pl.read_parquet(path)
            payload = pl.concat([current, payload], how="diagonal_relaxed")
            if merge_on:
                subset = [column for column in merge_on if column in payload.columns]
                if subset:
                    payload = payload.unique(subset=subset, keep="last")
            payload = payload.sort(self._sort_columns(payload))
        bounds = self._frame_bounds(payload)
        registry_payload = {
            "category": category,
            "frequency": frequency,
            "identifier": identifier,
            "path": path,
            "row_count": payload.height,
            "provider": provider,
            "start_ts": bounds["start_ts"],
            "end_ts": bounds["end_ts"],
            "metadata": metadata,
            "notice_json": notice.to_json() if notice else None,
        }
        self._atomic_write_parquet_with_registry(path, payload, registry_payload)
        return path

    def _upsert_frame_registry(self, registry_payload: dict[str, Any]) -> None:
        self._upsert_registry(
            category=registry_payload["category"],
            frequency=registry_payload["frequency"],
            identifier=registry_payload["identifier"],
            path=registry_payload["path"],
            row_count=registry_payload["row_count"],
            provider=registry_payload["provider"],
            start_ts=registry_payload["start_ts"],
            end_ts=registry_payload["end_ts"],
            metadata=registry_payload["metadata"],
            notice_json=registry_payload["notice_json"],
        )

    def _load_frame(
        self,
        *,
        category: str,
        frequency: str | None = None,
        identifiers: Sequence[str] | None = None,
        start_date: DateLike | None = None,
        end_date: DateLike | None = None,
    ) -> pl.DataFrame:
        records = self._query_registry(category=category, frequency=frequency, identifiers=identifiers)
        if not records:
            return pl.DataFrame()
        paths = [record["path"] for record in records if Path(record["path"]).exists()]
        if not paths:
            return pl.DataFrame()
        cast_options = getattr(pl, "ScanCastOptions", None)
        if cast_options is not None:
            frame = pl.scan_parquet(
                paths,
                cast_options=cast_options(integer_cast="allow-float", float_cast="upcast"),
            )
        else:
            frame = pl.scan_parquet(paths)
        columns = self._frame_columns(frame)
        if identifiers:
            id_column = self._identifier_column(category)
            if id_column in columns:
                frame = frame.filter(pl.col(id_column).is_in(list(identifiers)))
        frame = self._filter_by_time(frame, start_date=start_date, end_date=end_date).collect()
        return frame.sort(self._sort_columns(frame))

    def _filter_by_time(
        self,
        frame: pl.DataFrame | pl.LazyFrame,
        *,
        start_date: DateLike | None,
        end_date: DateLike | None,
    ) -> pl.DataFrame | pl.LazyFrame:
        if isinstance(frame, pl.DataFrame) and frame.is_empty():
            return frame
        columns = self._frame_columns(frame)
        time_column = "timestamp" if "timestamp" in columns else "date" if "date" in columns else None
        if time_column is None:
            return frame
        filtered = frame
        start_dt = normalize_datetime(start_date)
        end_dt = normalize_datetime(end_date, end_of_day=True)
        if start_dt is not None:
            filtered = filtered.filter(pl.col(time_column) >= pl.lit(start_dt if time_column == "timestamp" else start_dt.date()))
        if end_dt is not None:
            filtered = filtered.filter(pl.col(time_column) <= pl.lit(end_dt if time_column == "timestamp" else end_dt.date()))
        return filtered

    def _frame_columns(self, frame: pl.DataFrame | pl.LazyFrame) -> list[str]:
        if isinstance(frame, pl.LazyFrame):
            return frame.collect_schema().names()
        return frame.columns

    def _identifier_column(self, category: str) -> str:
        if category == "market_index_context":
            return "index_symbol"
        if category == "industry_context":
            return "industry_code"
        return "symbol"

    def _dataset_path(
        self,
        *,
        category: str,
        frequency: str | None = None,
        identifier: str | None = None,
    ) -> Path:
        if category == "market_data" and identifier and frequency:
            return self.bars_path(identifier, frequency)
        if category == "market_index_context" and identifier and frequency:
            return self.market_index_path(identifier, frequency)
        if category == "industry_context" and identifier:
            return self.industry_history_path(identifier)
        base_dir = self.cache_dir / category
        if frequency:
            base_dir = base_dir / f"frequency={frequency}"
        filename = self._safe_identifier(identifier or "latest")
        return base_dir / f"{filename}.parquet"

    def _safe_identifier(self, value: str) -> str:
        return re.sub(r"[^0-9A-Za-z._-]+", "_", value)

    def _frame_bounds(self, frame: pl.DataFrame) -> dict[str, datetime | None]:
        time_column = "timestamp" if "timestamp" in frame.columns else "date" if "date" in frame.columns else None
        if time_column is None or frame.is_empty():
            return {"start_ts": None, "end_ts": None}
        bounds = frame.select(
            pl.col(time_column).min().alias("start_ts"),
            pl.col(time_column).max().alias("end_ts"),
        ).row(0, named=True)
        start_value = bounds["start_ts"]
        end_value = bounds["end_ts"]
        if isinstance(start_value, date) and not isinstance(start_value, datetime):
            start_value = datetime.combine(start_value, datetime.min.time())
        if isinstance(end_value, date) and not isinstance(end_value, datetime):
            end_value = datetime.combine(end_value, datetime.min.time())
        return {"start_ts": start_value, "end_ts": end_value}

    def _sort_columns(self, frame: pl.DataFrame) -> list[str]:
        preferred = [column for column in ("symbol", "index_symbol", "industry_code", "timestamp", "date") if column in frame.columns]
        return preferred or frame.columns[:1]

    def _temporary_path(self, path: Path) -> Path:
        return path.with_name(f".{path.name}.{uuid4().hex}.tmp")

    def _backup_path(self, path: Path) -> Path:
        return path.with_name(f".{path.name}.{uuid4().hex}.bak")

    def _cleanup_file(self, path: Path | None) -> None:
        if path is None:
            return
        for attempt in range(6):
            try:
                path.unlink()
                return
            except FileNotFoundError:
                return
            except OSError as exc:
                if not self._is_retryable_file_error(exc) or attempt == 5:
                    return
                time.sleep(0.05 * (attempt + 1))

    def _replace_file(self, source: Path, destination: Path) -> None:
        self.ensure_parent(destination)
        for attempt in range(6):
            try:
                os.replace(source, destination)
                return
            except OSError as exc:
                if not self._is_retryable_file_error(exc) or attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))

    def _is_retryable_file_error(self, exc: OSError) -> bool:
        return isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in {5, 32, 33}

    def _restore_file(self, source: Path, destination: Path) -> None:
        self.ensure_parent(destination)
        for attempt in range(6):
            try:
                os.replace(source, destination)
                return
            except OSError as exc:
                if not self._is_retryable_file_error(exc) or attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))

    def _write_text_file(self, path: Path, content: str, *, encoding: str = "utf-8") -> None:
        self.ensure_parent(path)
        path.write_text(content, encoding=encoding)

    def _write_parquet_file(self, path: Path, frame: pl.DataFrame) -> None:
        self.ensure_parent(path)
        frame.write_parquet(path)

    def _write_numpy_file(self, path: Path, value: Any) -> None:
        import numpy as np

        self.ensure_parent(path)
        with path.open("wb") as handle:
            np.save(handle, value)

    def _atomic_write_text(self, path: Path, content: str, *, encoding: str = "utf-8") -> None:
        temp_path = self._temporary_path(path)
        try:
            self._write_text_file(temp_path, content, encoding=encoding)
            self._replace_file(temp_path, path)
        finally:
            self._cleanup_file(temp_path)

    def _atomic_write_parquet(self, path: Path, frame: pl.DataFrame) -> None:
        temp_path = self._temporary_path(path)
        try:
            self._write_parquet_file(temp_path, frame)
            self._replace_file(temp_path, path)
        finally:
            self._cleanup_file(temp_path)

    def _atomic_write_parquet_with_registry(
        self,
        path: Path,
        frame: pl.DataFrame,
        registry_payload: dict[str, Any],
    ) -> None:
        temp_path = self._temporary_path(path)
        backup_path = self._backup_path(path) if path.exists() else None
        committed = False
        restored = False
        try:
            self._write_parquet_file(temp_path, frame)
            if backup_path is not None:
                self._replace_file(path, backup_path)
            self._replace_file(temp_path, path)
            committed = True
            try:
                self._upsert_frame_registry(registry_payload)
            except Exception:
                self._cleanup_file(path)
                if backup_path is not None and backup_path.exists():
                    self._restore_file(backup_path, path)
                    restored = True
                raise
        except Exception:
            if not committed and backup_path is not None and backup_path.exists():
                self._restore_file(backup_path, path)
                restored = True
            raise
        finally:
            self._cleanup_file(temp_path)
            if backup_path is not None and restored:
                self._cleanup_file(backup_path)
            elif backup_path is not None and committed:
                self._cleanup_file(backup_path)

    def _commit_file_batch(self, replacements: Sequence[tuple[Path, Path]]) -> None:
        committed: list[tuple[Path, Path | None]] = []
        try:
            for source, destination in replacements:
                backup_path = self._backup_path(destination) if destination.exists() else None
                if backup_path is not None:
                    os.replace(destination, backup_path)
                try:
                    self._replace_file(source, destination)
                except Exception:
                    self._cleanup_file(destination)
                    if backup_path is not None and backup_path.exists():
                        os.replace(backup_path, destination)
                    raise
                committed.append((destination, backup_path))
            for _, backup_path in committed:
                self._cleanup_file(backup_path)
        except Exception:
            for destination, backup_path in reversed(committed):
                self._cleanup_file(destination)
                if backup_path is not None and backup_path.exists():
                    os.replace(backup_path, destination)
            raise

    def _validate_feature_artifacts(
        self,
        *,
        directory: Path,
        matrix: Any,
        metadata: pd.DataFrame,
        manifest: dict[str, Any],
    ) -> None:
        row_count = manifest.get("row_count")
        if isinstance(row_count, int):
            actual_matrix_rows = int(matrix.shape[0]) if getattr(matrix, "ndim", 0) >= 1 else 0
            actual_metadata_rows = int(len(metadata.index))
            if actual_matrix_rows != row_count or actual_metadata_rows != row_count:
                raise RuntimeError(
                    f"Feature artifacts in {directory} are inconsistent with manifest row_count={row_count}."
                )

        vector_dim = manifest.get("vector_dim")
        if isinstance(vector_dim, int) and getattr(matrix, "ndim", 0) == 2 and int(matrix.shape[1]) != vector_dim:
            raise RuntimeError(
                f"Feature artifacts in {directory} are inconsistent with manifest vector_dim={vector_dim}."
            )

        metadata_columns = manifest.get("metadata_columns")
        if isinstance(metadata_columns, list) and metadata.columns.tolist() != metadata_columns:
            raise RuntimeError(
                f"Feature artifacts in {directory} are inconsistent with manifest metadata_columns."
            )

    def _to_polars(self, frame: pd.DataFrame | pl.DataFrame) -> pl.DataFrame:
        if isinstance(frame, pl.DataFrame):
            return frame
        if frame.empty:
            return pl.DataFrame()
        return pl.from_pandas(frame, include_index=False)

    def _initialize_registry(self) -> None:
        import duckdb

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(self.db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_registry (
                    dataset_key VARCHAR PRIMARY KEY,
                    category VARCHAR NOT NULL,
                    frequency VARCHAR,
                    identifier VARCHAR,
                    path VARCHAR NOT NULL,
                    row_count BIGINT NOT NULL,
                    start_ts TIMESTAMP,
                    end_ts TIMESTAMP,
                    provider VARCHAR NOT NULL,
                    last_refresh_at TIMESTAMP NOT NULL,
                    notice_json VARCHAR,
                    metadata_json VARCHAR
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS builds (
                    build_key VARCHAR PRIMARY KEY,
                    frequency VARCHAR,
                    window_size INTEGER,
                    backend VARCHAR,
                    rows_count INTEGER,
                    built_at TIMESTAMP,
                    metadata_json VARCHAR
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS backfill_runs (
                    run_id VARCHAR PRIMARY KEY,
                    frequency VARCHAR NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    batch_size INTEGER NOT NULL,
                    requested_symbols INTEGER NOT NULL,
                    attempted_symbols INTEGER NOT NULL,
                    completed_symbols INTEGER NOT NULL,
                    failed_symbols INTEGER NOT NULL,
                    skipped_recent_listing INTEGER NOT NULL,
                    ignored_st_symbols INTEGER NOT NULL,
                    remaining_symbols INTEGER NOT NULL,
                    last_symbol VARCHAR,
                    status VARCHAR NOT NULL,
                    retry_failures BOOLEAN NOT NULL,
                    symbols_json VARCHAR NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    finished_at TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS backfill_attempts (
                    run_id VARCHAR NOT NULL,
                    symbol VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    error VARCHAR,
                    attempted_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (run_id, symbol)
                )
                """
            )

    def _upsert_registry(
        self,
        *,
        category: str,
        path: Path,
        row_count: int,
        provider: str,
        frequency: str | None = None,
        identifier: str | None = None,
        start_ts: datetime | None = None,
        end_ts: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        notice_json: str | None = None,
    ) -> None:
        dataset_key = self._dataset_key(category=category, frequency=frequency, identifier=identifier)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO cache_registry AS target
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_key) DO UPDATE SET
                    category = excluded.category,
                    frequency = excluded.frequency,
                    identifier = excluded.identifier,
                    path = excluded.path,
                    row_count = excluded.row_count,
                    start_ts = excluded.start_ts,
                    end_ts = excluded.end_ts,
                    provider = excluded.provider,
                    last_refresh_at = excluded.last_refresh_at,
                    notice_json = excluded.notice_json,
                    metadata_json = excluded.metadata_json
                """,
                [
                    dataset_key,
                    category,
                    frequency,
                    identifier,
                    str(path),
                    row_count,
                    start_ts,
                    end_ts,
                    provider,
                    self._utcnow(),
                    notice_json,
                    json.dumps(metadata, ensure_ascii=False, default=str) if metadata else None,
                ],
            )

    def _query_registry(
        self,
        *,
        category: str,
        frequency: str | None = None,
        identifiers: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        query = """
            SELECT
                category,
                frequency,
                identifier,
                path,
                row_count,
                start_ts,
                end_ts,
                provider,
                last_refresh_at,
                notice_json,
                metadata_json
            FROM cache_registry
            WHERE category = ?
        """
        parameters: list[Any] = [category]
        if frequency is not None:
            query += " AND frequency = ?"
            parameters.append(frequency)
        if identifiers:
            placeholders = ",".join("?" for _ in identifiers)
            query += f" AND identifier IN ({placeholders})"
            parameters.extend(list(identifiers))
        query += " ORDER BY identifier"
        with self._connect(read_only=True) as connection:
            rows = connection.execute(query, parameters).fetchall()
        keys = [
            "category",
            "frequency",
            "identifier",
            "path",
            "row_count",
            "start_ts",
            "end_ts",
            "provider",
            "last_refresh_at",
            "notice_json",
            "metadata_json",
        ]
        return [dict(zip(keys, row, strict=True)) for row in rows]

    def _list_cached_symbols_from_filesystem(self, frequency: Frequency) -> list[str]:
        bars_dir = self.config.storage.raw_dir / "bars" / frequency
        if not bars_dir.exists():
            return []
        return sorted(
            path.stem
            for path in bars_dir.glob("*.parquet")
            if path.is_file() and path.stem.isdigit() and len(path.stem) == 6
        )

    def _get_freshness_from_filesystem(self, frequency: Frequency) -> dict[str, Any] | None:
        bars_dir = self.config.storage.raw_dir / "bars" / frequency
        if not bars_dir.exists():
            return None
        parquet_files = [path for path in bars_dir.glob("*.parquet") if path.is_file()]
        if not parquet_files:
            return None
        latest_path = max(parquet_files, key=lambda path: path.stat().st_mtime)
        notice_payload = self.load_notice(frequency)
        return {
            "last_refresh_at": datetime.fromtimestamp(latest_path.stat().st_mtime),
            "start_ts": None,
            "end_ts": None,
            "provider": "akshare",
            "notice": notice_payload,
            "path": str(latest_path),
        }

    def _list_builds_from_filesystem(self) -> list[dict[str, Any]]:
        builds: list[dict[str, Any]] = []
        index_root = self.config.storage.index_dir
        if not index_root.exists():
            return builds
        for manifest_path in index_root.glob("*\\window_*\\manifest.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            frequency = str(manifest.get("frequency") or manifest_path.parent.parent.name)
            try:
                window_size = int(manifest.get("window_size") or manifest_path.parent.name.replace("window_", ""))
            except ValueError:
                continue
            backend = manifest.get("backend")
            backend_path = manifest_path.parent / "backend.json"
            if backend_path.exists():
                try:
                    backend_payload = json.loads(backend_path.read_text(encoding="utf-8"))
                    backend = backend_payload.get("backend") or backend
                except (OSError, json.JSONDecodeError):
                    pass
            built_at = manifest.get("built_at") or datetime.fromtimestamp(manifest_path.stat().st_mtime)
            builds.append(
                {
                    "build_key": f"{frequency}:{window_size}",
                    "frequency": frequency,
                    "window_size": window_size,
                    "backend": backend,
                    "rows_count": int(manifest.get("row_count") or 0),
                    "built_at": built_at,
                    "metadata_json": manifest,
                }
            )
        return sorted(
            builds,
            key=lambda item: (
                item["built_at"] if isinstance(item["built_at"], datetime) else datetime.min,
                item["build_key"],
            ),
            reverse=True,
        )

    def _dataset_key(self, *, category: str, frequency: str | None, identifier: str | None) -> str:
        return f"{category}|{frequency or 'na'}|{identifier or 'na'}"

    def _row_to_backfill_run(self, row: Any) -> dict[str, Any] | None:
        if not row:
            return None
        symbols = json.loads(row[15]) if row[15] else []
        return {
            "run_id": row[0],
            "frequency": row[1],
            "start_date": row[2],
            "end_date": row[3],
            "batch_size": row[4],
            "requested_symbols": row[5],
            "attempted_symbols": row[6],
            "completed_symbols": row[7],
            "failed_symbols": row[8],
            "skipped_recent_listing": row[9],
            "ignored_st_symbols": row[10],
            "remaining_symbols": row[11],
            "last_symbol": row[12],
            "status": row[13],
            "retry_failures": bool(row[14]),
            "symbols": symbols,
            "started_at": row[16],
            "finished_at": row[17],
        }

    def _connect(self, *, read_only: bool = False):  # type: ignore[no-untyped-def]
        try:
            import duckdb
        except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError("duckdb is required to use LocalDataStore. Install project dependencies first.") from exc
        if read_only:
            return duckdb.connect(str(self.db_path), read_only=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            self._initialize_registry()
        return duckdb.connect(str(self.db_path), read_only=read_only)

    def _is_duckdb_lock_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return (
            "workspace.duckdb" in message
            and (
                "another program is using this file" in message
                or "file is already open" in message
                or "unique file handle conflict" in message
                or "进程无法访问" in message
            )
        )

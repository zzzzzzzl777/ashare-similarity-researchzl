from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from time import monotonic, sleep
from typing import Any

import pandas as pd

try:  # pragma: no cover
    import tushare as ts
except Exception:  # pragma: no cover
    ts = None  # type: ignore[assignment]


DEFAULT_PROXY_BASE_URL = "http://124.220.22.110:8020/"


class _RateLimiter:
    """Very small process-local rate limiter.

    The proxy seller warns about cooldowns when hitting request bursts.
    We cap calls/minute across threads in one process.
    """

    def __init__(self, calls_per_minute: int) -> None:
        safe_calls = max(int(calls_per_minute), 1)
        self._min_interval_sec = 60.0 / float(safe_calls)
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0

    def wait(self) -> None:
        with self._lock:
            now = monotonic()
            if now < self._next_allowed_at:
                sleep(self._next_allowed_at - now)
                now = monotonic()
            self._next_allowed_at = max(self._next_allowed_at, now) + self._min_interval_sec


@dataclass(frozen=True, slots=True)
class TsyTushareProxyConfig:
    token: str
    base_url: str = DEFAULT_PROXY_BASE_URL
    calls_per_minute: int = 110

    @staticmethod
    def from_env() -> TsyTushareProxyConfig | None:
        token = (os.environ.get("TSY_TUSHARE_TOKEN") or "").strip()
        if not token:
            return None
        base_url = (os.environ.get("TSY_TUSHARE_BASE_URL") or DEFAULT_PROXY_BASE_URL).strip()
        calls = os.environ.get("TSY_TUSHARE_CALLS_PER_MINUTE")
        calls_per_minute = 110
        if calls:
            try:
                calls_per_minute = int(calls)
            except ValueError:
                calls_per_minute = 110
        return TsyTushareProxyConfig(token=token, base_url=base_url, calls_per_minute=calls_per_minute)


class TsyTushareProxyClient:
    """Thin wrapper over tushare SDK, with proxy base-url + rate limiting."""

    def __init__(self, config: TsyTushareProxyConfig) -> None:
        if ts is None:  # pragma: no cover
            raise RuntimeError("tushare is not installed; unable to use TSY proxy")
        self.config = config
        self._limiter = _RateLimiter(config.calls_per_minute)
        self._pro = ts.pro_api(config.token)
        # The proxy seller provides an alternate gateway URL (non-official).
        # tushare SDK uses a private attr for request URL.
        setattr(self._pro, "_DataApi__http_url", config.base_url)

    def query(self, api_name: str, **params: Any) -> pd.DataFrame:
        self._limiter.wait()
        try:
            return self._pro.query(api_name, **params)
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"tushare proxy query failed: {api_name}: {exc}") from exc

    def fetch_stock_mins(
        self,
        *,
        ts_code: str,
        freq: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch A-share history minute bars via `stk_mins`.

        Notes:
        - Official tushare doc says single call returns up to 8000 rows, so long ranges
          should be paged by time window.
        - This client keeps the call small; paging is handled by the caller if needed.
        """

        self._limiter.wait()
        kwargs: dict[str, Any] = {"ts_code": ts_code, "freq": freq}
        if start_date is not None:
            kwargs["start_date"] = _format_ts_datetime(start_date)
        if end_date is not None:
            kwargs["end_date"] = _format_ts_datetime(end_date)
        try:
            df = self._pro.stk_mins(**kwargs)
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"tushare proxy stk_mins failed: {ts_code} {freq}: {exc}") from exc
        if df is None or len(df) == 0:
            return pd.DataFrame()
        return df


def _format_ts_datetime(value: date | datetime) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return datetime.combine(value, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")


def suggest_time_window(
    *,
    frequency: str,
    start_date: date | datetime | None,
    end_date: date | datetime | None,
) -> tuple[datetime, datetime]:
    """Derive a safe default window when caller doesn't provide one."""

    if end_date is None:
        end_ts = datetime.now()
    else:
        end_ts = end_date if isinstance(end_date, datetime) else datetime.combine(end_date, datetime.max.time().replace(microsecond=0))
    if start_date is None:
        # Keep defaults small to avoid an accidental "10 years minutes" request.
        lookback_days = 10 if str(frequency) != "1" else 5
        start_ts = end_ts - timedelta(days=lookback_days)
    else:
        start_ts = start_date if isinstance(start_date, datetime) else datetime.combine(start_date, datetime.min.time())
    return start_ts.replace(tzinfo=None), end_ts.replace(tzinfo=None)


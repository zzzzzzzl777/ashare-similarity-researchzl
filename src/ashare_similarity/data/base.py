from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time
from typing import Any, Literal, Protocol, runtime_checkable

import pandas as pd
import polars as pl


Frequency = Literal["daily", "1", "5", "15", "30", "60"]
DateLike = date | datetime


@dataclass(slots=True)
class SecurityProfile:
    symbol: str
    name: str | None = None
    industry: str | None = None
    listing_date: date | None = None
    is_st: bool = False

    def to_record(self) -> dict[str, object]:
        record = asdict(self)
        if self.listing_date:
            record["listing_date"] = self.listing_date.isoformat()
        return record


@dataclass(frozen=True, slots=True)
class MarketIndexDefinition:
    symbol: str
    name: str


@dataclass(slots=True)
class ProviderNotice:
    notice_id: str
    provider: str
    frequency: str
    title: str
    summary: str
    severity: str = "warning"
    source_url: str | None = None
    constraints: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["constraints"] = list(self.constraints)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))


@dataclass(slots=True)
class MarketDataRequest:
    frequency: Frequency
    symbols: list[str] | None = None
    start_date: DateLike | None = None
    end_date: DateLike | None = None
    adjust: str | None = None


@dataclass(slots=True)
class CacheArtifact:
    category: str
    path: str
    frequency: str | None = None
    identifier: str | None = None
    row_count: int = 0
    start_ts: datetime | None = None
    end_ts: datetime | None = None
    last_refresh_at: datetime | None = None


DEFAULT_MARKET_INDEXES: tuple[MarketIndexDefinition, ...] = (
    MarketIndexDefinition(symbol="000001", name="上证指数"),
    MarketIndexDefinition(symbol="399001", name="深证成指"),
    MarketIndexDefinition(symbol="399006", name="创业板指"),
    MarketIndexDefinition(symbol="000688", name="科创50"),
    MarketIndexDefinition(symbol="899050", name="北证50"),
)


def normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().lower()
    cleaned = cleaned.removeprefix("sh").removeprefix("sz").removeprefix("bj").removeprefix("csi")
    digits = re.sub(r"\D", "", cleaned)
    return digits.zfill(6)[-6:]


def infer_exchange(symbol: str) -> str:
    code = normalize_symbol(symbol)
    if code.startswith(
        (
            "600",
            "601",
            "603",
            "605",
            "688",
            "689",
            "900",
            "730",
            "732",
            "733",
            "734",
            "735",
            "736",
        )
    ):
        return "sh"
    if code.startswith(
        (
            "430",
            "431",
            "830",
            "831",
            "832",
            "833",
            "834",
            "835",
            "836",
            "837",
            "838",
            "839",
            "870",
            "871",
            "872",
            "873",
            "899",
            "920",
        )
    ):
        return "bj"
    return "sz"


def to_market_symbol(symbol: str) -> str:
    code = normalize_symbol(symbol)
    return f"{infer_exchange(code)}{code}"


def to_index_symbol(symbol: str) -> str:
    return normalize_symbol(symbol)


def normalize_datetime(value: DateLike | None, *, end_of_day: bool = False) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    day_time = time.max.replace(microsecond=0) if end_of_day else time.min
    return datetime.combine(value, day_time)


def format_ymd(value: DateLike | None) -> str | None:
    normalized = normalize_datetime(value, end_of_day=False)
    if normalized is None:
        return None
    return normalized.strftime("%Y%m%d")


def format_timestamp(value: DateLike | None, *, end_of_day: bool = False) -> str | None:
    normalized = normalize_datetime(value, end_of_day=end_of_day)
    if normalized is None:
        return None
    return normalized.strftime("%Y-%m-%d %H:%M:%S")


def build_minute_history_notice(frequency: str, provider: str = "akshare") -> ProviderNotice:
    base_constraints = [
        "AKShare 的 A 股分钟线来自东方财富免费接口，不提供全历史分钟数据。",
        "该限制会影响股票分钟线缓存设计，系统只能保证近期分钟数据可用。",
    ]
    metadata: dict[str, Any] = {
        "coverage": "recent_only",
        "free_provider": True,
        "supports_adjust": frequency != "1",
    }
    if frequency == "1":
        base_constraints.append("1 分钟股票数据通常只覆盖最近 5 个交易日，且不支持复权。")
        base_constraints.append("1 分钟索引数据通常也只能返回当前或极近期窗口数据。")
        metadata["stock_recent_trading_days"] = 5
        metadata["stock_adjust_supported"] = False
    else:
        base_constraints.append(f"{frequency} 分钟股票数据只保证近期窗口可取，历史覆盖长度取决于东方财富接口。")
        base_constraints.append(f"{frequency} 分钟索引数据同样只保证近期窗口可取。")
        metadata["stock_recent_trading_days"] = None
        metadata["stock_adjust_supported"] = True

    return ProviderNotice(
        notice_id=f"{provider}-minute-history-limit-{frequency}",
        provider=provider,
        frequency=frequency,
        title="免费分钟线历史范围受限",
        summary="分钟线仅能稳定覆盖免费接口允许的近期时间窗，不能当作全历史分钟数据库使用。",
        severity="warning",
        source_url="https://akshare.akfamily.xyz/data/stock/stock.html",
        constraints=tuple(base_constraints),
        metadata=metadata,
    )


class DataProvider(Protocol):
    def fetch_universe(self) -> pd.DataFrame:
        ...

    def fetch_security_profile(self, symbol: str) -> SecurityProfile:
        ...

    def fetch_price_history(
        self,
        symbol: str,
        frequency: Frequency,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        ...

    def fetch_market_index_history(
        self,
        symbol: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> pd.DataFrame:
        ...


@runtime_checkable
class MarketDataProvider(Protocol):
    provider_name: str

    def get_frequency_notice(self, frequency: Frequency) -> ProviderNotice | None:
        ...

    def get_universe_snapshot(self) -> pl.DataFrame:
        ...

    def get_daily_bars(
        self,
        symbol: str,
        start_date: DateLike | None = None,
        end_date: DateLike | None = None,
        adjust: str | None = None,
    ) -> pl.DataFrame:
        ...

    def get_minute_bars(
        self,
        symbol: str,
        frequency: Frequency,
        start_date: DateLike | None = None,
        end_date: DateLike | None = None,
        adjust: str | None = None,
    ) -> pl.DataFrame:
        ...

    def get_market_index_bars(
        self,
        symbol: str,
        frequency: Frequency = "daily",
        start_date: DateLike | None = None,
        end_date: DateLike | None = None,
    ) -> pl.DataFrame:
        ...

    def list_industry_boards(self) -> pl.DataFrame:
        ...

    def get_industry_board_members(self, industry_code: str, industry_name: str | None = None) -> pl.DataFrame:
        ...

    def get_industry_board_history(
        self,
        industry_code: str,
        industry_name: str | None = None,
        start_date: DateLike | None = None,
        end_date: DateLike | None = None,
    ) -> pl.DataFrame:
        ...

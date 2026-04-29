from __future__ import annotations

from datetime import date, datetime, timedelta
from time import sleep

import akshare as ak
import numpy as np
import pandas as pd

from ashare_similarity.config import AppConfig
from ashare_similarity.data.base import Frequency, SecurityProfile, build_minute_history_notice, to_market_symbol
from ashare_similarity.data.storage import LocalDataStore


class AkshareDataProvider:
    provider_name = "akshare"
    MARKET_INDEXES = ("sh000001", "sz399001", "sz399006")

    def __init__(self, config: AppConfig, store: LocalDataStore) -> None:
        self.config = config
        self.store = store

    def get_frequency_notice(self, frequency: Frequency):
        if frequency == "daily":
            return None
        return build_minute_history_notice(frequency, provider=self.provider_name)

    def _with_retry(self, func, *args, **kwargs):
        last_error = None
        for attempt in range(3):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                if attempt == 2:
                    raise
                sleep(1.2 * (attempt + 1))
        raise last_error  # pragma: no cover

    def fetch_universe(self) -> pd.DataFrame:
        df = self._with_retry(ak.stock_info_a_code_name)
        df = df.rename(columns={"code": "symbol", "name": "name"})
        df["symbol"] = df["symbol"].astype(str).str.zfill(6)
        df["is_st"] = df["name"].astype(str).str.contains("ST|退", regex=True, na=False)
        return df[["symbol", "name", "is_st"]].drop_duplicates("symbol").reset_index(drop=True)

    def fetch_security_profile(self, symbol: str) -> SecurityProfile:
        normalized_symbol = str(symbol).strip().zfill(6)
        raw = self._with_retry(ak.stock_individual_info_em, symbol=normalized_symbol)
        mapping = {str(row["item"]).strip(): row["value"] for _, row in raw.iterrows()}
        name = str(mapping.get("股票简称", "")).strip() or None
        industry = str(mapping.get("行业", "")).strip() or None
        listing_raw = str(mapping.get("上市时间", "")).strip()
        listing_date = None
        if listing_raw.isdigit():
            listing_date = datetime.strptime(listing_raw, "%Y%m%d").date()
        return SecurityProfile(
            symbol=normalized_symbol,
            name=name,
            industry=industry,
            listing_date=listing_date,
            is_st=bool(name and ("ST" in name or "退" in name)),
        )

    def fetch_price_history(
        self,
        symbol: str,
        frequency: Frequency,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        normalized_symbol = str(symbol).strip().zfill(6)
        if frequency == "daily":
            return self._fetch_daily_bars(
                symbol=normalized_symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        return self._fetch_minute_bars(
            symbol=normalized_symbol,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

    def fetch_market_index_history(
        self,
        symbol: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> pd.DataFrame:
        errors: list[str] = []
        for loader in (self._fetch_market_index_history_sina, self._fetch_market_index_history_tencent):
            try:
                frame = loader(symbol=symbol, start_date=start_date, end_date=end_date)
                if not frame.empty:
                    return frame.reset_index(drop=True)
            except Exception as exc:
                errors.append(f"{loader.__name__}: {exc}")
        raise RuntimeError(f"Unable to fetch market index history for {symbol}: {' | '.join(errors)}")

    def _fetch_daily_bars(
        self,
        symbol: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        errors: list[str] = []
        primary: pd.DataFrame | None = None
        try:
            frame = self._fetch_daily_bars_eastmoney(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
            if not frame.empty:
                primary = frame.reset_index(drop=True)
                if self._daily_frame_is_complete_enough(
                    primary,
                    start_date=start_date,
                    end_date=end_date,
                ):
                    return primary
        except Exception as exc:
            errors.append(f"{self._fetch_daily_bars_eastmoney.__name__}: {exc}")

        fallback_loaders = [self._fetch_daily_bars_sina]
        if symbol.startswith("689"):
            fallback_loaders.append(self._fetch_daily_bars_cdr)
        fallback_loaders.append(self._fetch_daily_bars_tencent)

        for loader in fallback_loaders:
            try:
                frame = loader(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
                if not frame.empty:
                    fallback = frame.reset_index(drop=True)
                    if primary is not None and not primary.empty:
                        return self._merge_daily_frames([primary, fallback])
                    return fallback
            except Exception as exc:
                errors.append(f"{loader.__name__}: {exc}")
        if primary is not None and not primary.empty:
            return primary
        raise RuntimeError(f"Unable to fetch daily bars for {symbol}: {' | '.join(errors)}")

    def _daily_frame_is_complete_enough(
        self,
        frame: pd.DataFrame,
        *,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> bool:
        if frame.empty:
            return False
        if start_date is not None or end_date is not None:
            return True
        min_complete_rows = max(int(self.config.quality.min_listing_days), 60)
        return len(frame) >= min_complete_rows

    def _fetch_minute_bars(
        self,
        symbol: str,
        frequency: Frequency,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        errors: list[str] = []
        for loader in (self._fetch_minute_bars_eastmoney, self._fetch_minute_bars_sina):
            try:
                frame = loader(
                    symbol=symbol,
                    frequency=frequency,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
                if not frame.empty:
                    return frame.reset_index(drop=True)
            except Exception as exc:
                errors.append(f"{loader.__name__}: {exc}")
        raise RuntimeError(f"Unable to fetch minute bars for {symbol} {frequency}: {' | '.join(errors)}")

    def _fetch_market_index_history_sina(
        self,
        *,
        symbol: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> pd.DataFrame:
        frame = self._with_retry(ak.stock_zh_index_daily, symbol=symbol).rename(
            columns={
                "date": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
            }
        )
        return self._normalize_market_index_frame(frame, symbol=symbol, start_date=start_date, end_date=end_date)

    def _fetch_market_index_history_tencent(
        self,
        *,
        symbol: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> pd.DataFrame:
        frame = self._with_retry(ak.stock_zh_index_daily_tx, symbol=symbol)
        return self._normalize_market_index_frame(frame, symbol=symbol, start_date=start_date, end_date=end_date)

    def _fetch_daily_bars_eastmoney(
        self,
        *,
        symbol: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        raw = self._with_retry(
            ak.stock_zh_a_hist,
            symbol=symbol,
            period="daily",
            start_date=(start_date or date(1990, 1, 1)).strftime("%Y%m%d"),
            end_date=(end_date or date.today()).strftime("%Y%m%d"),
            adjust=adjust,
        )
        if raw.empty:
            return pd.DataFrame()
        frame = raw.rename(
            columns={
                "日期": "date",
                "股票代码": "symbol",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "pct_change",
                "涨跌额": "change",
                "换手率": "turnover",
            }
        )
        return self._normalize_daily_frame(frame, symbol=symbol)

    def _fetch_daily_bars_sina(
        self,
        *,
        symbol: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        raw = self._with_retry(
            ak.stock_zh_a_daily,
            symbol=to_market_symbol(symbol),
            start_date=(start_date or date(1990, 1, 1)).strftime("%Y%m%d"),
            end_date=(end_date or date.today()).strftime("%Y%m%d"),
            adjust=adjust,
        )
        if raw.empty:
            return pd.DataFrame()
        frame = raw.copy()
        if "turnover" in frame.columns:
            frame["turnover"] = pd.to_numeric(frame["turnover"], errors="coerce") * 100.0
        return self._normalize_daily_frame(frame, symbol=symbol)

    def _fetch_daily_bars_cdr(
        self,
        *,
        symbol: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        del adjust
        raw = self._with_retry(
            ak.stock_zh_a_cdr_daily,
            symbol=to_market_symbol(symbol),
            start_date=(start_date or date(1990, 1, 1)).strftime("%Y%m%d"),
            end_date=(end_date or date.today()).strftime("%Y%m%d"),
        )
        if raw.empty:
            return pd.DataFrame()
        frame = raw.copy()
        return self._normalize_daily_frame(frame, symbol=symbol)

    def _fetch_daily_bars_tencent(
        self,
        *,
        symbol: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        raw = self._with_retry(
            ak.stock_zh_a_hist_tx,
            symbol=to_market_symbol(symbol),
            start_date=(start_date or date(1990, 1, 1)).strftime("%Y%m%d"),
            end_date=(end_date or date.today()).strftime("%Y%m%d"),
            adjust=adjust,
        )
        if raw.empty:
            return pd.DataFrame()
        frame = raw.rename(columns={"amount": "volume"})
        return self._normalize_daily_frame(frame, symbol=symbol)

    def _fetch_minute_bars_eastmoney(
        self,
        *,
        symbol: str,
        frequency: Frequency,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        effective_adjust = "" if frequency == "1" else adjust
        minute_start = self._as_minute_ts(start_date) or (datetime.now() - timedelta(days=10))
        minute_end = self._as_minute_ts(end_date) or datetime.now()
        raw = self._with_retry(
            ak.stock_zh_a_hist_min_em,
            symbol=symbol,
            start_date=minute_start.strftime("%Y-%m-%d %H:%M:%S"),
            end_date=minute_end.strftime("%Y-%m-%d %H:%M:%S"),
            period=str(frequency),
            adjust=effective_adjust,
        )
        if raw.empty:
            return pd.DataFrame()
        frame = raw.rename(
            columns={
                "时间": "timestamp",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "pct_change",
                "涨跌额": "change",
                "换手率": "turnover",
            }
        )
        return self._normalize_minute_frame(
            frame,
            symbol=symbol,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
        )

    def _fetch_minute_bars_sina(
        self,
        *,
        symbol: str,
        frequency: Frequency,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        raw = self._with_retry(
            ak.stock_zh_a_minute,
            symbol=to_market_symbol(symbol),
            period=str(frequency),
            adjust="" if frequency == "1" else adjust,
        )
        if raw.empty:
            return pd.DataFrame()
        frame = raw.rename(columns={"day": "timestamp"})
        return self._normalize_minute_frame(
            frame,
            symbol=symbol,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
        )

    def _normalize_market_index_frame(
        self,
        frame: pd.DataFrame,
        *,
        symbol: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> pd.DataFrame:
        normalized = frame.copy()
        normalized["date"] = pd.to_datetime(normalized["date"])
        for column in ("open", "high", "low", "close"):
            if column in normalized.columns:
                normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        if "volume" not in normalized.columns:
            normalized["volume"] = 0.0
        if start_date is not None:
            normalized = normalized[normalized["date"] >= pd.Timestamp(start_date)]
        if end_date is not None:
            normalized = normalized[normalized["date"] <= pd.Timestamp(end_date)]
        normalized["index_symbol"] = symbol
        normalized["pct_change"] = normalized["close"].pct_change().fillna(0.0) * 100.0
        return normalized.reset_index(drop=True)

    def _normalize_daily_frame(self, frame: pd.DataFrame, *, symbol: str) -> pd.DataFrame:
        normalized = frame.copy()
        normalized["date"] = pd.to_datetime(normalized["date"])
        for column in ("open", "high", "low", "close", "volume", "amount", "turnover", "amplitude", "pct_change", "change"):
            if column in normalized.columns:
                normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        normalized = normalized.sort_values("date").reset_index(drop=True)
        prev_close = normalized["close"].shift(1)
        if "change" not in normalized.columns:
            normalized["change"] = normalized["close"].diff().fillna(0.0)
        else:
            normalized["change"] = normalized["change"].fillna(normalized["close"].diff()).fillna(0.0)
        if "pct_change" not in normalized.columns:
            normalized["pct_change"] = normalized["close"].pct_change().fillna(0.0) * 100.0
        else:
            normalized["pct_change"] = normalized["pct_change"].fillna(normalized["close"].pct_change() * 100.0).fillna(0.0)
        fallback_amplitude = ((normalized["high"] - normalized["low"]) / prev_close.replace(0, np.nan)) * 100.0
        if "amplitude" not in normalized.columns:
            normalized["amplitude"] = fallback_amplitude
        else:
            normalized["amplitude"] = normalized["amplitude"].fillna(fallback_amplitude)
        if "turnover" not in normalized.columns:
            normalized["turnover"] = 0.0
        if "amount" not in normalized.columns:
            normalized["amount"] = 0.0
        if "volume" not in normalized.columns:
            normalized["volume"] = 0.0
        normalized["symbol"] = symbol
        normalized["frequency"] = "daily"
        normalized["amplitude"] = normalized["amplitude"].fillna(0.0)
        normalized["turnover"] = normalized["turnover"].fillna(0.0)
        normalized["amount"] = normalized["amount"].fillna(0.0)
        normalized["volume"] = normalized["volume"].fillna(0.0)
        return normalized[
            [
                "date",
                "symbol",
                "frequency",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "amplitude",
                "pct_change",
                "change",
                "turnover",
            ]
        ].dropna(subset=["date", "open", "high", "low", "close"]).reset_index(drop=True)

    def _merge_daily_frames(self, frames: list[pd.DataFrame]) -> pd.DataFrame:
        if not frames:
            return pd.DataFrame()
        if len(frames) == 1:
            return frames[0].reset_index(drop=True)

        merged = pd.concat(frames, ignore_index=True)
        merged = merged.sort_values("date")
        merged = merged.drop_duplicates(subset=["date"], keep="first")
        primary = frames[0]
        merged_is_more_complete = (
            len(merged) > len(primary)
            or merged["date"].min() < primary["date"].min()
            or merged["date"].max() > primary["date"].max()
        )
        if merged_is_more_complete:
            return merged.reset_index(drop=True)
        return primary.reset_index(drop=True)

    def _normalize_minute_frame(
        self,
        frame: pd.DataFrame,
        *,
        symbol: str,
        frequency: Frequency,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> pd.DataFrame:
        normalized = frame.copy()
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"])
        start_ts = self._as_minute_ts(start_date)
        end_ts = self._as_minute_ts(end_date)
        if start_ts is not None:
            normalized = normalized[normalized["timestamp"] >= pd.Timestamp(start_ts)]
        if end_ts is not None:
            normalized = normalized[normalized["timestamp"] <= pd.Timestamp(end_ts)]
        for column in ("open", "high", "low", "close", "volume", "amount", "turnover", "amplitude", "pct_change", "change"):
            if column in normalized.columns:
                normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        normalized = normalized.sort_values("timestamp").reset_index(drop=True)
        prev_close = normalized["close"].shift(1)
        if "change" not in normalized.columns:
            normalized["change"] = normalized["close"].diff().fillna(0.0)
        else:
            normalized["change"] = normalized["change"].fillna(normalized["close"].diff()).fillna(0.0)
        if "pct_change" not in normalized.columns:
            normalized["pct_change"] = normalized["close"].pct_change().fillna(0.0) * 100.0
        else:
            normalized["pct_change"] = normalized["pct_change"].fillna(normalized["close"].pct_change() * 100.0).fillna(0.0)
        fallback_amplitude = ((normalized["high"] - normalized["low"]) / prev_close.replace(0, np.nan)) * 100.0
        if "amplitude" not in normalized.columns:
            normalized["amplitude"] = fallback_amplitude
        else:
            normalized["amplitude"] = normalized["amplitude"].fillna(fallback_amplitude)
        if "turnover" not in normalized.columns:
            normalized["turnover"] = 0.0
        if "amount" not in normalized.columns:
            normalized["amount"] = 0.0
        if "volume" not in normalized.columns:
            normalized["volume"] = 0.0
        normalized["date"] = normalized["timestamp"].dt.normalize()
        normalized["symbol"] = symbol
        normalized["frequency"] = str(frequency)
        normalized["amplitude"] = normalized["amplitude"].fillna(0.0)
        normalized["turnover"] = normalized["turnover"].fillna(0.0)
        normalized["amount"] = normalized["amount"].fillna(0.0)
        normalized["volume"] = normalized["volume"].fillna(0.0)
        return normalized[
            [
                "timestamp",
                "date",
                "symbol",
                "frequency",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "amplitude",
                "pct_change",
                "change",
                "turnover",
            ]
        ].dropna(subset=["timestamp", "open", "high", "low", "close"]).reset_index(drop=True)

    def _as_minute_ts(self, value: date | datetime | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.combine(value, datetime.min.time())

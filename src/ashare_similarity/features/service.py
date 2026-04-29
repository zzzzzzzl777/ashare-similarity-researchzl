from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

import numpy as np
import pandas as pd

from ashare_similarity.config import AppConfig
from ashare_similarity.context.service import ContextService
from ashare_similarity.data.base import Frequency
from ashare_similarity.data.service import DataService
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.features.encoder import encode_window
from ashare_similarity.features.models import FeatureFrame, QueryWindow
from ashare_similarity.features.quality import QualityFilter
from ashare_similarity.features.rolling import iter_rolling_windows, time_column_for_frequency


class FeatureService:
    def __init__(
        self,
        config: AppConfig,
        store: LocalDataStore,
        data_service: DataService,
        context_service: ContextService,
    ) -> None:
        self.config = config
        self.store = store
        self.data_service = data_service
        self.context_service = context_service
        self.quality_filter = QualityFilter(config)

    def _optional_attr(self, target: Any, name: str) -> Any | None:
        try:
            return getattr(target, name)
        except (AttributeError, AssertionError):
            return None

    def _resolve_symbols(self, symbols: list[str] | None) -> list[str]:
        if symbols:
            return [symbol.strip().zfill(6) for symbol in symbols]
        resolver = self._optional_attr(self.data_service, "_resolve_symbols")
        if callable(resolver):
            resolved = resolver(symbols)
            if isinstance(resolved, list):
                return [str(symbol).strip().zfill(6) for symbol in resolved]
        return []

    def _load_bars(
        self,
        symbol: str,
        frequency: Frequency,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        ensure_remote: bool = False,
    ) -> pd.DataFrame:
        loader = getattr(self.data_service, "load_price_history", None)
        if callable(loader):
            frame = loader(
                symbol=symbol,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
                ensure_remote=ensure_remote,
            )
            if isinstance(frame, pd.DataFrame):
                return frame.copy()
        fallback = getattr(self.data_service, "get_price_history", None)
        if callable(fallback):
            frame = fallback(symbol=symbol, frequency=frequency, start_date=start_date, end_date=end_date)
            if isinstance(frame, pd.DataFrame):
                return frame.copy()
        if isinstance(self.data_service, pd.DataFrame):
            return self.data_service.copy()
        generic = getattr(self.data_service, "__getattr__", None)
        if callable(generic):
            try:
                frame = self.data_service.load_price_history(symbol=symbol, frequency=frequency)
                if isinstance(frame, pd.DataFrame):
                    return frame.copy()
            except Exception:
                pass
        return pd.DataFrame()

    def _get_profile(self, symbol: str, bars: pd.DataFrame) -> Any:
        loader = getattr(self.data_service, "get_security_profile", None)
        if callable(loader):
            profile = loader(symbol)
            if profile is not None and not isinstance(profile, pd.DataFrame) and hasattr(profile, "symbol"):
                return profile

        class _Profile:
            def __init__(self, frame: pd.DataFrame) -> None:
                self.symbol = symbol
                self.name = str(frame["name"].iloc[0]) if "name" in frame.columns and not frame.empty else None
                self.industry = str(frame["industry"].iloc[0]) if "industry" in frame.columns and not frame.empty else None
                self.listing_date = None
                self.is_st = bool(frame["is_st"].iloc[0]) if "is_st" in frame.columns and not frame.empty else False

        return _Profile(bars)

    def _get_listing_days(self, symbol: str, bars: pd.DataFrame, as_of: date | None) -> int | None:
        universe_service = self._optional_attr(self.data_service, "universe_service")
        getter = self._optional_attr(universe_service, "get_listing_days") if universe_service is not None else None
        if callable(getter):
            listing_days = getter(symbol, as_of=as_of)
            if listing_days is not None:
                return int(listing_days)
        if "listing_days" in bars.columns and not bars.empty:
            return int(bars["listing_days"].iloc[-1])
        return None

    def _normalize_market_context(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        normalized = frame.copy()
        rename_map = {
            "market_return": "market_return_mean",
            "market_trend": "market_trend_5",
            "market_volatility": "market_volatility_5",
            "industry_return": "industry_return_mean",
            "industry_trend": "industry_return_trend_5",
            "turnover_ratio": "industry_turnover_mean",
        }
        normalized = normalized.rename(columns=rename_map)
        if "market_trend_5" not in normalized.columns and "market_return_mean" in normalized.columns:
            normalized["market_trend_5"] = normalized["market_return_mean"].rolling(5, min_periods=1).mean()
        if "market_volatility_5" not in normalized.columns and "market_return_mean" in normalized.columns:
            normalized["market_volatility_5"] = normalized["market_return_mean"].rolling(5, min_periods=1).std().fillna(0.0)
        if "industry_return_trend_5" not in normalized.columns and "industry_return_mean" in normalized.columns:
            normalized["industry_return_trend_5"] = normalized["industry_return_mean"].rolling(5, min_periods=1).mean()
        if "industry_turnover_mean" not in normalized.columns:
            normalized["industry_turnover_mean"] = 0.0
        if "industry_amplitude_mean" not in normalized.columns:
            normalized["industry_amplitude_mean"] = 0.0
        return normalized

    def _get_market_context(self) -> pd.DataFrame:
        getter = getattr(self.context_service, "get_market_context", None)
        if callable(getter):
            frame = getter()
            if isinstance(frame, pd.DataFrame):
                return self._normalize_market_context(frame)
        if isinstance(self.context_service, pd.DataFrame):
            return self._normalize_market_context(self.context_service)
        return pd.DataFrame()

    def _get_industry_context(self) -> pd.DataFrame:
        getter = getattr(self.context_service, "get_industry_context", None)
        if callable(getter):
            frame = getter()
            if isinstance(frame, pd.DataFrame):
                return self._normalize_market_context(frame)
        return pd.DataFrame()

    def _normalize_end_dt(self, frequency: Frequency, end_date: date | datetime) -> pd.Timestamp:
        if isinstance(end_date, datetime):
            return pd.Timestamp(end_date)
        if frequency == "daily":
            return pd.Timestamp(end_date)
        return pd.Timestamp(datetime.combine(end_date, time(23, 59, 59)))

    def _enrich_with_context(self, bars: pd.DataFrame, industry: str | None, frequency: Frequency) -> pd.DataFrame:
        frame = bars.copy()
        if frame.empty:
            return frame
        market = self._get_market_context()
        if not market.empty:
            market["date"] = pd.to_datetime(market["date"]).dt.normalize()
            frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
            market_cols = ["date", "market_return_mean", "market_volatility_5", "market_trend_5"]
            frame = frame.merge(market[market_cols], on="date", how="left")
        industry_context = self._get_industry_context()
        if industry and not industry_context.empty:
            industry_context["date"] = pd.to_datetime(industry_context["date"]).dt.normalize()
            if "industry" in industry_context.columns:
                industry_slice = industry_context[industry_context["industry"] == industry]
            else:
                industry_slice = industry_context.copy()
            if industry_slice.empty and "industry_return_mean" in industry_context.columns:
                industry_slice = industry_context.copy()
                industry_slice["industry"] = industry
            frame = frame.merge(
                industry_slice[
                    ["date", "industry_return_mean", "industry_turnover_mean", "industry_amplitude_mean", "industry_return_trend_5"]
                ],
                on="date",
                how="left",
            )
        fill_columns = [
            "market_return_mean",
            "market_volatility_5",
            "market_trend_5",
            "industry_return_mean",
            "industry_turnover_mean",
            "industry_amplitude_mean",
            "industry_return_trend_5",
        ]
        for column in fill_columns:
            if column not in frame.columns:
                frame[column] = 0.0
            frame[column] = frame[column].fillna(0.0)
        return frame

    def build_feature_frame(
        self,
        frequency: Frequency,
        window_size: int,
        symbols: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> FeatureFrame:
        selected = self._resolve_symbols(symbols)
        vectors: list[np.ndarray] = []
        metadata_rows: list[dict[str, Any]] = []
        slices: dict[str, tuple[int, int]] | None = None
        time_col = time_column_for_frequency(frequency)
        latest_data_at: pd.Timestamp | None = None

        for symbol in selected:
            bars = self._load_bars(
                symbol=symbol,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
                ensure_remote=False,
            )
            if bars.empty:
                continue
            symbol_latest = pd.to_datetime(bars[time_col]).max()
            if latest_data_at is None or symbol_latest > latest_data_at:
                latest_data_at = symbol_latest
            profile = self._get_profile(symbol, bars)
            listing_days = self._get_listing_days(symbol, bars, end_date)
            enriched = self._enrich_with_context(bars, profile.industry, frequency)
            for start_idx, end_idx, window in iter_rolling_windows(enriched, frequency, window_size):
                quality = self.quality_filter.evaluate(window, listing_days=listing_days)
                if not quality.is_valid:
                    continue
                encoded = encode_window(window)
                vectors.append(encoded.vector)
                slices = encoded.component_slices
                metadata_rows.append(
                    {
                        "symbol": symbol,
                        "name": profile.name or getattr(self.data_service, "get_symbol_name", lambda _: None)(symbol),
                        "industry": profile.industry,
                        "listing_days": listing_days,
                        "frequency": frequency,
                        "start_idx": start_idx,
                        "end_idx": end_idx,
                        "start_date": pd.Timestamp(window.iloc[0][time_col]).isoformat(),
                        "end_date": pd.Timestamp(window.iloc[-1][time_col]).isoformat(),
                        "window_length": len(window),
                    }
                )

        matrix = np.vstack(vectors) if vectors else np.zeros((0, 0), dtype=np.float32)
        metadata = pd.DataFrame(metadata_rows)
        return FeatureFrame(
            frequency=frequency,
            window_size=window_size,
            matrix=matrix,
            metadata=metadata,
            component_slices=slices or {},
            built_from={
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "symbols_count": len(selected),
                "latest_data_at": latest_data_at.isoformat() if latest_data_at is not None else None,
            },
        )

    def build_query_frame(
        self,
        symbol: str,
        end_date: date | datetime,
        frequency: Frequency,
        window_size: int,
        *,
        ensure_remote: bool = True,
    ) -> QueryWindow:
        symbol = symbol.strip().zfill(6)
        end_ts = self._normalize_end_dt(frequency, end_date)
        start_window_hint = end_ts - pd.Timedelta(days=window_size * (3 if frequency == "daily" else 2))
        bars = self._load_bars(
            symbol=symbol,
            frequency=frequency,
            start_date=start_window_hint.to_pydatetime(),
            end_date=end_ts.to_pydatetime(),
            ensure_remote=ensure_remote,
        )
        if bars.empty:
            if ensure_remote:
                raise ValueError(f"未找到标的 {symbol} 在所选区间内的本地缓存或远程行情数据。")
            raise ValueError(f"标的 {symbol} 在所选区间内没有本地缓存，请先运行 maintain 或 backfill。")
        time_col = time_column_for_frequency(frequency)
        bars[time_col] = pd.to_datetime(bars[time_col])
        window = bars[bars[time_col] <= end_ts].sort_values(time_col).tail(window_size).copy().reset_index(drop=True)
        if len(window) < window_size:
            raise ValueError(f"标的 {symbol} 的可用K线不足，无法构建 {window_size} 根K线的查询窗口。")
        profile = self._get_profile(symbol, bars)
        listing_days = self._get_listing_days(symbol, bars, end_ts.date())
        window = self._enrich_with_context(window, profile.industry, frequency)
        quality = self.quality_filter.evaluate(window, listing_days=listing_days)
        warnings = quality.reasons.copy()
        encoded = encode_window(window)
        metadata = {
            "symbol": symbol,
            "name": profile.name or getattr(self.data_service, "get_symbol_name", lambda _: None)(symbol),
            "industry": profile.industry,
            "listing_days": listing_days,
            "start_date": pd.Timestamp(window.iloc[0][time_col]).isoformat(),
            "end_date": pd.Timestamp(window.iloc[-1][time_col]).isoformat(),
        }
        return QueryWindow(
            frequency=frequency,
            window_size=window_size,
            symbol=symbol,
            end_label=metadata["end_date"],
            matrix=encoded.vector.reshape(1, -1),
            metadata=metadata,
            series=window,
            component_slices=encoded.component_slices,
            warnings=warnings,
        )

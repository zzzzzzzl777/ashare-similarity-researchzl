from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from ashare_similarity.config import AppConfig
from ashare_similarity.data.akshare_provider import AkshareDataProvider
from ashare_similarity.data.storage import LocalDataStore


class ContextService:
    def __init__(self, config: AppConfig, store: LocalDataStore, provider: AkshareDataProvider) -> None:
        self.config = config
        self.store = store
        self.provider = provider

    def bootstrap(self) -> dict[str, int]:
        market = self.refresh_market_context()
        return {"market_context_rows": len(market), "industry_context_rows": len(self.get_industry_context())}

    def refresh_context(
        self,
        *,
        frequency: str,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> dict[str, int]:
        market = self.refresh_market_context(start_date=start_date, end_date=end_date)
        return {"market_context_rows": len(market), "industry_context_rows": len(self.get_industry_context())}

    def refresh_market_context(
        self,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
    ) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for symbol in self.provider.MARKET_INDEXES:
            frame = self.provider.fetch_market_index_history(symbol, start_date=start_date, end_date=end_date)
            if frame.empty:
                continue
            self.store.save_market_index(symbol, frame)
            renamed = frame[["date", "close", "pct_change"]].rename(
                columns={
                    "close": f"{symbol}_close",
                    "pct_change": f"{symbol}_pct_change",
                }
            )
            frames.append(renamed)
        if not frames:
            return pd.DataFrame()
        merged = frames[0]
        for frame in frames[1:]:
            merged = merged.merge(frame, on="date", how="outer")
        merged = merged.sort_values("date").reset_index(drop=True)
        pct_cols = [column for column in merged.columns if column.endswith("_pct_change")]
        merged["market_return_mean"] = merged[pct_cols].mean(axis=1).fillna(0.0)
        merged["market_volatility_5"] = merged["market_return_mean"].rolling(5, min_periods=1).std().fillna(0.0)
        merged["market_trend_5"] = merged["market_return_mean"].rolling(5, min_periods=1).mean().fillna(0.0)
        self.store.save_market_context(merged)
        return merged

    def build_industry_context(self, universe_df: pd.DataFrame) -> pd.DataFrame:
        rows: list[pd.DataFrame] = []
        for record in universe_df.itertuples(index=False):
            industry = getattr(record, "industry", None)
            symbol = getattr(record, "symbol")
            if not industry:
                continue
            bars = self.store.load_bars(symbol, "daily")
            if bars.empty:
                continue
            frame = bars[["date", "pct_change", "turnover", "amplitude"]].copy()
            frame["industry"] = industry
            rows.append(frame)
        if not rows:
            return pd.DataFrame()
        merged = pd.concat(rows, ignore_index=True)
        grouped = (
            merged.groupby(["date", "industry"], as_index=False)
            .agg(
                industry_return_mean=("pct_change", "mean"),
                industry_turnover_mean=("turnover", "mean"),
                industry_amplitude_mean=("amplitude", "mean"),
                constituents=("pct_change", "size"),
            )
            .sort_values(["industry", "date"])
            .reset_index(drop=True)
        )
        grouped["industry_return_trend_5"] = (
            grouped.groupby("industry")["industry_return_mean"]
            .rolling(5, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
        self.store.save_industry_context(grouped)
        return grouped

    def get_market_context(self) -> pd.DataFrame:
        frame = self.store.load_market_context()
        if frame.empty:
            return self.refresh_market_context()
        return frame

    def get_industry_context(self) -> pd.DataFrame:
        return self.store.load_industry_context()

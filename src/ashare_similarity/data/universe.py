from __future__ import annotations

from datetime import date

import pandas as pd

from ashare_similarity.config import AppConfig
from ashare_similarity.data.base import SecurityProfile
from ashare_similarity.data.storage import LocalDataStore


class UniverseService:
    def __init__(self, config: AppConfig, store: LocalDataStore, provider) -> None:
        self.config = config
        self.store = store
        self.provider = provider

    def bootstrap(self, force_refresh: bool = False) -> pd.DataFrame:
        cached = self.store.load_universe()
        if not cached.empty and not force_refresh:
            return cached
        df = self.provider.fetch_universe()
        self.store.save_universe(df)
        return df

    def get_universe(self, allow_bootstrap: bool = True) -> pd.DataFrame:
        df = self.store.load_universe()
        if df.empty and allow_bootstrap:
            return self.bootstrap()
        if df.empty:
            return pd.DataFrame(columns=["symbol", "name", "is_st"])
        return df

    def get_filtered_universe(self, allow_bootstrap: bool = True) -> pd.DataFrame:
        df = self.get_universe(allow_bootstrap=allow_bootstrap).copy()
        if self.config.quality.exclude_st and "is_st" in df.columns:
            df = df[~df["is_st"].fillna(False)]
        return df.reset_index(drop=True)

    def get_profile(
        self,
        symbol: str,
        refresh: bool = False,
        *,
        allow_remote: bool = False,
    ) -> SecurityProfile:
        normalized_symbol = str(symbol).strip().zfill(6)
        profile = self.store.load_profile(normalized_symbol)
        if profile and not refresh:
            return profile
        universe = self.get_universe()
        match = universe[universe["symbol"] == normalized_symbol]
        fallback_name = str(match.iloc[0]["name"]) if not match.empty and "name" in match.columns else None
        fallback_is_st = bool(match.iloc[0]["is_st"]) if not match.empty and "is_st" in match.columns else False
        fallback_profile = SecurityProfile(
            symbol=normalized_symbol,
            name=fallback_name,
            industry=None,
            listing_date=None,
            is_st=fallback_is_st,
        )
        if not allow_remote:
            self.store.save_profile(fallback_profile)
            return fallback_profile
        try:
            profile = self.provider.fetch_security_profile(normalized_symbol)
        except Exception:
            profile = fallback_profile
        self.store.save_profile(profile)
        return profile

    def get_listing_days(self, symbol: str, as_of: date | None = None) -> int | None:
        profile = self.get_profile(symbol, allow_remote=False)
        if profile.listing_date is None:
            return None
        ref = as_of or date.today()
        return max((ref - profile.listing_date).days, 0)

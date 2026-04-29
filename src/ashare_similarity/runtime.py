from __future__ import annotations

from functools import lru_cache

from ashare_similarity.config import AppConfig, get_default_config
from ashare_similarity.context.service import ContextService
from ashare_similarity.data.akshare_provider import AkshareDataProvider
from ashare_similarity.data.service import DataService
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.data.universe import UniverseService
from ashare_similarity.features.service import FeatureService
from ashare_similarity.indexing.service import IndexService
from ashare_similarity.prediction.service import PredictionService
from ashare_similarity.search.service import SearchService


class Runtime:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or get_default_config()
        self.store = LocalDataStore(self.config)
        self.provider = AkshareDataProvider(self.config, self.store)
        self.universe_service = UniverseService(self.config, self.store, self.provider)
        self.context_service = ContextService(self.config, self.store, self.provider)
        self.data_service = DataService(
            self.config,
            self.store,
            self.provider,
            self.universe_service,
            self.context_service,
        )
        self.feature_service = FeatureService(
            self.config,
            self.store,
            self.data_service,
            self.context_service,
        )
        self.index_service = IndexService(self.config, self.store)
        self.search_service = SearchService(
            self.config,
            self.store,
            self.data_service,
            self.feature_service,
            self.index_service,
        )
        self.prediction_service = PredictionService(
            self.config,
            self.store,
            self.data_service,
            self.feature_service,
            self.search_service,
        )


@lru_cache(maxsize=1)
def get_runtime() -> Runtime:
    return Runtime()

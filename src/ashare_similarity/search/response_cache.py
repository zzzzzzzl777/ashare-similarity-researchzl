from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from ashare_similarity.schemas import PredictionRequest, PredictionResponse, SearchRequest, SearchResponse


@dataclass(frozen=True, slots=True)
class SearchRequestKey:
    symbol: str
    end_date: str
    frequency: str
    window_size: int
    top_k: int
    search_scope: str


@dataclass(frozen=True, slots=True)
class PredictionRequestKey:
    symbol: str
    as_of_date: str
    frequency: str
    horizons: tuple[int, ...]
    window_sizes: tuple[int, ...]
    top_k: int


@dataclass(slots=True)
class CachedSearchResponse:
    created_at: float
    response: SearchResponse


@dataclass(slots=True)
class CachedPredictionResponse:
    created_at: float
    response: PredictionResponse


class SearchResponseCache:
    def __init__(self, *, max_entries: int = 64, ttl_seconds: float = 300.0) -> None:
        self.max_entries = max(int(max_entries), 1)
        self.ttl_seconds = max(float(ttl_seconds), 0.0)
        self._entries: OrderedDict[SearchRequestKey, CachedSearchResponse] = OrderedDict()
        self._lock = Lock()

    def get(self, request: SearchRequest) -> SearchResponse | None:
        key = _request_key(request)
        now = monotonic()
        with self._lock:
            cached = self._entries.get(key)
            if cached is None:
                return None
            if self._is_expired(cached, now):
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return cached.response.model_copy(deep=True)

    def put(self, request: SearchRequest, response: SearchResponse) -> None:
        key = _request_key(request)
        now = monotonic()
        cached = CachedSearchResponse(created_at=now, response=response.model_copy(deep=True))
        with self._lock:
            self._entries[key] = cached
            self._entries.move_to_end(key)
            self._purge_expired_locked(now)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _is_expired(self, cached: CachedSearchResponse, now: float) -> bool:
        return self.ttl_seconds == 0.0 or (now - cached.created_at) > self.ttl_seconds

    def _purge_expired_locked(self, now: float) -> None:
        expired_keys = [key for key, cached in self._entries.items() if self._is_expired(cached, now)]
        for key in expired_keys:
            self._entries.pop(key, None)


class PredictionResponseCache:
    def __init__(self, *, max_entries: int = 32, ttl_seconds: float = 300.0) -> None:
        self.max_entries = max(int(max_entries), 1)
        self.ttl_seconds = max(float(ttl_seconds), 0.0)
        self._entries: OrderedDict[PredictionRequestKey, CachedPredictionResponse] = OrderedDict()
        self._lock = Lock()

    def get(self, request: PredictionRequest) -> PredictionResponse | None:
        key = _prediction_request_key(request)
        now = monotonic()
        with self._lock:
            cached = self._entries.get(key)
            if cached is None:
                return None
            if self._is_expired(cached, now):
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return cached.response.model_copy(deep=True)

    def put(self, request: PredictionRequest, response: PredictionResponse) -> None:
        key = _prediction_request_key(request)
        now = monotonic()
        cached = CachedPredictionResponse(created_at=now, response=response.model_copy(deep=True))
        with self._lock:
            self._entries[key] = cached
            self._entries.move_to_end(key)
            self._purge_expired_locked(now)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _is_expired(self, cached: CachedPredictionResponse, now: float) -> bool:
        return self.ttl_seconds == 0.0 or (now - cached.created_at) > self.ttl_seconds

    def _purge_expired_locked(self, now: float) -> None:
        expired_keys = [key for key, cached in self._entries.items() if self._is_expired(cached, now)]
        for key in expired_keys:
            self._entries.pop(key, None)


def _request_key(request: SearchRequest) -> SearchRequestKey:
    payload = request.model_dump(mode="json")
    return SearchRequestKey(
        symbol=str(payload["symbol"]),
        end_date=str(payload["end_date"]),
        frequency=str(payload["frequency"]),
        window_size=int(payload["window_size"]),
        top_k=int(payload["top_k"]),
        search_scope=str(payload.get("search_scope", "historical")),
    )


def _prediction_request_key(request: PredictionRequest) -> PredictionRequestKey:
    payload = request.model_dump(mode="json")
    return PredictionRequestKey(
        symbol=str(payload["symbol"]),
        as_of_date=str(payload["as_of_date"]),
        frequency=str(payload["frequency"]),
        horizons=tuple(int(item) for item in payload.get("horizons", [])),
        window_sizes=tuple(int(item) for item in payload.get("window_sizes", [])),
        top_k=int(payload["top_k"]),
    )

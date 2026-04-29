from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


_LOCAL_HOME_PATTERN = re.compile(
    r"\$env:ASHARE_SIMILARITY_HOME\s*=\s*(?P<quote>['\"])(?P<home>.+?)(?P=quote)",
    re.IGNORECASE,
)


def _storage_home_from_local_script(repo_root: Path) -> Path | None:
    """Read the ignored local PowerShell config used by the launch scripts."""

    local_script = repo_root / "ashare_similarity.local.ps1"
    if not local_script.exists():
        return None
    try:
        content = local_script.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _LOCAL_HOME_PATTERN.search(content)
    if not match:
        return None
    configured = match.group("home").strip()
    if not configured:
        return None
    return Path(configured).expanduser().resolve()


def _default_storage_root() -> Path:
    configured = os.environ.get("ASHARE_SIMILARITY_HOME")
    if configured:
        return Path(configured).expanduser().resolve() / "data"

    package_dir = Path(__file__).resolve().parent
    repo_root = package_dir.parents[1]
    local_home = _storage_home_from_local_script(repo_root)
    if local_home is not None:
        return local_home / "data"

    if (repo_root / "pyproject.toml").exists():
        return repo_root / "data"

    return Path.home().resolve() / ".ashare_similarity" / "data"


@dataclass(slots=True)
class SearchWeights:
    price_path: float = 0.45
    candle_geometry: float = 0.20
    volume_liquidity: float = 0.20
    environment: float = 0.15


@dataclass(slots=True)
class RankingConfig:
    top_k: int = 10
    recall_k: int = 200
    max_matches_per_symbol: int = 2
    overlap_days_limit: int = 2
    forward_windows: tuple[int, ...] = (1, 3, 5, 10)


@dataclass(slots=True)
class QualityConfig:
    min_listing_days: int = 120
    min_non_null_ratio: float = 0.95
    max_zero_volume_ratio: float = 0.20
    exclude_st: bool = True


@dataclass(slots=True)
class DataSourceConfig:
    provider: str = "akshare"
    default_adjust: str = "qfq"
    minute_history_notice: str = "分钟线基于免费接口，仅保证近期数据可用；1分钟数据通常仅覆盖近5个交易日。"


@dataclass(slots=True)
class BuildDefaultsConfig:
    daily_window_sizes: tuple[int, ...] = (5, 8, 10, 20)
    minute_window_sizes: tuple[int, ...] = (60, 120, 240)


@dataclass(slots=True)
class BackfillConfig:
    max_workers: int = 12
    stale_run_after_minutes: int = 30
    rebuild_industry_context_during_backfill: bool = False


@dataclass(slots=True)
class StorageConfig:
    root_dir: Path = field(default_factory=_default_storage_root)
    raw_dir: Path | None = None
    cache_dir: Path | None = None
    index_dir: Path | None = None
    report_dir: Path | None = None
    db_path: Path | None = None

    def __post_init__(self) -> None:
        self.root_dir = Path(self.root_dir).expanduser().resolve()
        self.raw_dir = Path(self.raw_dir or (self.root_dir / "raw")).expanduser().resolve()
        self.cache_dir = Path(self.cache_dir or (self.root_dir / "cache")).expanduser().resolve()
        self.index_dir = Path(self.index_dir or (self.root_dir / "index")).expanduser().resolve()
        self.report_dir = Path(self.report_dir or (self.root_dir / "reports")).expanduser().resolve()
        self.db_path = Path(self.db_path or (self.root_dir / "workspace.duckdb")).expanduser().resolve()


@dataclass(slots=True)
class AppConfig:
    storage: StorageConfig = field(default_factory=StorageConfig)
    search_weights: SearchWeights = field(default_factory=SearchWeights)
    ranking: RankingConfig = field(default_factory=RankingConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    build_defaults: BuildDefaultsConfig = field(default_factory=BuildDefaultsConfig)
    backfill: BackfillConfig = field(default_factory=BackfillConfig)

    def ensure_directories(self) -> None:
        for path in (
            self.storage.root_dir,
            self.storage.raw_dir,
            self.storage.cache_dir,
            self.storage.index_dir,
            self.storage.report_dir,
        ):
            Path(path).mkdir(parents=True, exist_ok=True)


def get_default_config() -> AppConfig:
    return AppConfig()

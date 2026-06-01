from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ashare_similarity.config import AppConfig


@dataclass(slots=True)
class SignalConfig:
    cache_root: Path
    report_dir: Path
    frozen_candidates_path: Path
    artifact_base_dir: Path

    @classmethod
    def from_app_config(
        cls,
        config: AppConfig,
        *,
        frozen_candidates_filename: str = "frozen_candidates_20260503.json",
    ) -> SignalConfig:
        override = os.environ.get("SIGNAL_CACHE_DIR")
        if override:
            cache_root = Path(override).expanduser().resolve()
        else:
            cache_root = Path(config.storage.cache_dir) / "prediction" / "signals" / "v1"

        report_dir = Path(config.storage.report_dir) / "prediction"
        return cls(
            cache_root=cache_root,
            report_dir=report_dir,
            frozen_candidates_path=report_dir / frozen_candidates_filename,
            artifact_base_dir=report_dir / "runs",
        )

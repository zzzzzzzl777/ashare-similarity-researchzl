"""Build a score-only research feature cache for extended 14:57 window work.

The script refreshes only the feature cache and returns before model training.
Use it before running the full window/model matrix so 2017+ raw history can be
converted into the same feature schema as the current research pipeline.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2017-01-03")
    parser.add_argument("--train-end", default="2025-12-31")
    parser.add_argument("--test-start", default="2026-01-01")
    parser.add_argument("--end", default="2026-04-30")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-symbols", type=int, default=0, help="0 means all cached main-board symbols.")
    parser.add_argument(
        "--context-subset-only",
        action="store_true",
        help="Use only sampled symbols for market context. For smoke tests only; do not use for formal builds.",
    )
    parser.add_argument("--asof-date", default=datetime.now().strftime("%Y%m%d"))
    return parser.parse_args()


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime, Path)):
        return str(value)
    raise TypeError(type(value).__name__)


def main() -> int:
    args = parse_args()
    cfg = get_default_config()
    cfg.ensure_directories()
    store = LocalDataStore(cfg)
    probe_cfg = GpuProbeConfig(
        start=_parse_date(args.start),
        train_end=_parse_date(args.train_end),
        test_start=_parse_date(args.test_start),
        end=_parse_date(args.end),
        seed=args.seed,
        max_symbols=None if args.max_symbols <= 0 else args.max_symbols,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=299,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=(),
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=True,
        build_feature_cache_only=True,
        context_subset_only=bool(args.context_subset_only),
    )
    result = run_gpu_next_day_probe(store, probe_cfg)
    out_dir = cfg.storage.report_dir / "prediction"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"extended_1457_feature_cache_build_{args.asof_date}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
    print(json.dumps({"status": result.get("status"), "output": str(out_path), "feature_cache": result.get("feature_cache")}, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "feature_cache_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())

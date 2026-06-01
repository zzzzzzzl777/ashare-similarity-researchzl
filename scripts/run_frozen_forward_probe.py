from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.frozen_forward import (
    build_forward_gpu_probe_config,
    load_available_trading_dates,
    load_frozen_forward_config,
    load_frozen_forward_protocol,
    resolve_forward_window,
    summarize_gpu_probe_config,
)
from ashare_similarity.prediction.gpu_probe import run_gpu_next_day_probe


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run or validate the frozen final_unseen forward probe.",
    )
    parser.add_argument(
        "--config",
        default=str(REPO_ROOT / "docs" / "frozen_forward_config.json"),
        help="Path to docs/frozen_forward_config.json",
    )
    parser.add_argument(
        "--runtime-home",
        default=None,
        help="Optional ASHARE_SIMILARITY_HOME override (root before /data).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved forward config without launching training.",
    )
    return parser


def _resolve_runtime_home(runtime_home_arg: str | None) -> Path:
    if runtime_home_arg:
        return Path(runtime_home_arg).expanduser().resolve()
    configured = os.environ.get("ASHARE_SIMILARITY_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    app_config = get_default_config()
    return app_config.storage.root_dir.parent


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.runtime_home:
        os.environ["ASHARE_SIMILARITY_HOME"] = str(Path(args.runtime_home).expanduser().resolve())

    frozen_config = load_frozen_forward_config(Path(args.config).expanduser().resolve())
    protocol = load_frozen_forward_protocol(frozen_config)
    runtime_home = _resolve_runtime_home(args.runtime_home)
    trading_dates = load_available_trading_dates(runtime_home)
    window = resolve_forward_window(frozen_config, trading_dates)

    if not window.ready:
        payload = {
            "status": "blocked",
            "reason": window.blocked_reason,
            "frozen_at": window.frozen_at.isoformat(),
            "latest_available_date": (
                window.latest_available_date.isoformat()
                if window.latest_available_date is not None
                else None
            ),
            "runtime_home": str(runtime_home),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if args.dry_run else 2

    probe_config = build_forward_gpu_probe_config(frozen_config, protocol, window)
    summary = {
        "status": "ready" if args.dry_run else "launching",
        "runtime_home": str(runtime_home),
        "frozen_at": window.frozen_at.isoformat(),
        "latest_available_date": window.latest_available_date.isoformat(),
        "resolved_probe_config": summarize_gpu_probe_config(probe_config, frozen_config=frozen_config),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.dry_run:
        return 0

    app_config = get_default_config()
    store = LocalDataStore(app_config)
    result = run_gpu_next_day_probe(store, probe_config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

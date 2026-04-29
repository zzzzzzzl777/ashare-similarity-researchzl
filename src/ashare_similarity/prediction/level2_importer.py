from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_similarity.prediction.level2_schema import validate_level2_frame


def import_level2_file(path: str | Path, *, table: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(str(source_path))
    suffix = source_path.suffix.lower()
    if suffix == ".csv":
        raw = pd.read_csv(source_path)
    elif suffix in {".parquet", ".pq"}:
        raw = pd.read_parquet(source_path)
    else:
        raise ValueError("Level2 importer supports CSV and Parquet files only.")
    frame = validate_level2_frame(raw, table)
    metadata = {
        "table": str(table).strip().lower(),
        "path": str(source_path),
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "fingerprint": _file_fingerprint(source_path),
        "source": "local_file",
        "asof_time": "file_timestamp",
        "lag_rule": "local Level2 history only; never infer unavailable history from mobile UI",
    }
    return frame, metadata


def _file_fingerprint(path: Path) -> str:
    stat = path.stat()
    payload = {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

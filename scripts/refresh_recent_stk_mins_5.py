"""Refresh recent Tushare 5min bars for frozen-forward scoring.

This script is intentionally narrow: it only appends a recent 5min window into
the existing stk_mins_5 parquet cache. It does not train, select features, or
change any model artifact.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

try:
    import tushare as ts
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"tushare import failed: {exc}") from exc


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_DIR = Path(r"E:\ashare_similarity_runtime\data\cache\prediction\tushare\stk_mins_5")
DEFAULT_LOG_DIR = REPO_ROOT / "logs" / "forward_refresh"
DEFAULT_PROXY_BASE_URL = "http://124.220.22.110:8020/"


class RateLimiter:
    def __init__(self, calls_per_minute: int) -> None:
        self._min_interval = 60.0 / float(max(1, calls_per_minute))
        self._next_allowed = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = monotonic()
            if now < self._next_allowed:
                time.sleep(self._next_allowed - now)
                now = monotonic()
            self._next_allowed = max(self._next_allowed, now) + self._min_interval


_thread_local = threading.local()
_write_lock = threading.Lock()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="YYYY-mm-dd HH:MM:SS")
    parser.add_argument("--end", required=True, help="YYYY-mm-dd HH:MM:SS")
    parser.add_argument("--freq", default="5min")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--calls-per-minute", type=int, default=120)
    parser.add_argument("--max-symbols", type=int, default=0, help="Smoke-test limit; 0 means all mainboard symbols.")
    parser.add_argument("--force", action="store_true", help="Fetch even when local cache already reaches --end.")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--asof-date", default=datetime.now().strftime("%Y%m%d"))
    return parser.parse_args()


def get_env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def get_pro(token: str, base_url: str):
    if not hasattr(_thread_local, "pro"):
        pro = ts.pro_api(token)
        pro._DataApi__http_url = base_url
        _thread_local.pro = pro
    return _thread_local.pro


def atomic_write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def classify_error(exc: Exception) -> str:
    msg = str(exc)
    lower = msg.lower()
    if "40101" in msg or "permission" in lower:
        return "permission_denied"
    if "40203" in msg or "rate" in lower or "frequency" in lower:
        return "rate_limit"
    if "timeout" in lower or "timed out" in lower:
        return "timeout"
    return "error"


def local_max_trade_time(path: Path) -> pd.Timestamp | None:
    if not path.exists():
        return None
    try:
        table = pq.read_table(path, columns=["trade_time"])
        if table.num_rows == 0:
            return None
        series = pd.to_datetime(table.to_pandas()["trade_time"], errors="coerce")
        value = series.max()
        if pd.isna(value):
            return None
        return pd.Timestamp(value)
    except Exception:
        return None


def fetch_symbol(
    *,
    ts_code: str,
    token: str,
    base_url: str,
    limiter: RateLimiter,
    cache_dir: Path,
    start: str,
    end: str,
    freq: str,
    force: bool,
) -> dict[str, Any]:
    out_path = cache_dir / f"{ts_code}.parquet"
    target_end = pd.Timestamp(end)
    local_max = local_max_trade_time(out_path)
    if not force and local_max is not None and local_max >= target_end:
        return {"ts_code": ts_code, "status": "skip_current", "rows": 0, "local_max": str(local_max)}

    pro = get_pro(token, base_url)
    last_error = ""
    for attempt in range(1, 4):
        try:
            limiter.wait()
            df = pro.stk_mins(ts_code=ts_code, freq=freq, start_date=start, end_date=end)
            rows = 0 if df is None else int(len(df))
            if rows <= 0:
                return {"ts_code": ts_code, "status": "empty", "rows": 0, "local_max": str(local_max)}
            df = df.copy()
            df["trade_time"] = pd.to_datetime(df["trade_time"], errors="coerce")
            df = df.dropna(subset=["trade_time"])
            with _write_lock:
                if out_path.exists():
                    old = pd.read_parquet(out_path)
                    old["trade_time"] = pd.to_datetime(old["trade_time"], errors="coerce")
                    merged = pd.concat([old, df], ignore_index=True)
                    merged = merged.drop_duplicates(subset=["ts_code", "trade_time"], keep="last")
                else:
                    merged = df
                merged = merged.sort_values("trade_time").reset_index(drop=True)
                atomic_write_parquet(merged, out_path)
            new_max = pd.Timestamp(merged["trade_time"].max())
            return {"ts_code": ts_code, "status": "saved", "rows": rows, "local_max": str(local_max), "new_max": str(new_max)}
        except Exception as exc:  # pragma: no cover - network dependent
            err_type = classify_error(exc)
            last_error = f"{err_type}: {str(exc)[:200]}"
            if err_type == "permission_denied":
                return {"ts_code": ts_code, "status": err_type, "rows": 0, "error": last_error}
            if err_type == "rate_limit":
                time.sleep(60)
                continue
            if err_type == "timeout" and attempt < 3:
                time.sleep(10 * attempt)
                continue
            break
    return {"ts_code": ts_code, "status": "error", "rows": 0, "error": last_error}


def get_mainboard_symbols(token: str, base_url: str, limiter: RateLimiter) -> list[str]:
    pro = get_pro(token, base_url)
    limiter.wait()
    df = pro.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name,market,list_date")
    codes = sorted(str(x) for x in df["ts_code"].tolist() if re.match(r"^(00|60)", str(x)))
    if not codes:
        raise RuntimeError("stock_basic returned no mainboard-like 00/60 symbols")
    return codes


def audit_cache(cache_dir: Path, symbols: list[str], target_end: str) -> dict[str, Any]:
    target = pd.Timestamp(target_end)
    by_date: dict[str, int] = {}
    current = 0
    missing_file = 0
    stale = 0
    for ts_code in symbols:
        path = cache_dir / f"{ts_code}.parquet"
        mx = local_max_trade_time(path)
        if mx is None:
            missing_file += 1
            continue
        day = mx.strftime("%Y-%m-%d")
        by_date[day] = by_date.get(day, 0) + 1
        if mx >= target:
            current += 1
        else:
            stale += 1
    return {
        "target_end": target_end,
        "symbols": len(symbols),
        "current_symbols": current,
        "stale_symbols": stale,
        "missing_files": missing_file,
        "coverage": round(current / len(symbols), 6) if symbols else 0.0,
        "max_trade_time_distribution_tail": dict(sorted(by_date.items())[-10:]),
    }


def main() -> int:
    args = parse_args()
    token = get_env("TSY_TUSHARE_TOKEN")
    if not token:
        print("Missing TSY_TUSHARE_TOKEN; refusing to run.", file=sys.stderr)
        return 2
    base_url = get_env("TSY_TUSHARE_BASE_URL", DEFAULT_PROXY_BASE_URL)
    os.environ["NO_PROXY"] = "124.220.22.110"
    os.environ["no_proxy"] = "124.220.22.110"

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    args.log_dir.mkdir(parents=True, exist_ok=True)
    limiter = RateLimiter(args.calls_per_minute)
    symbols = get_mainboard_symbols(token, base_url, limiter)
    if args.max_symbols > 0:
        symbols = symbols[: args.max_symbols]

    progress_path = args.log_dir / f"recent_stk_mins_5_{args.asof_date}_{args.start[:10]}_{args.end[:10]}.json"
    progress = load_json(progress_path, {"completed": {}, "results": []})
    completed = set(progress.get("completed", {}).keys())

    if args.audit_only:
        audit = audit_cache(args.cache_dir, symbols, args.end)
        print(json.dumps({"status": "audit_only", "audit": audit, "progress_path": str(progress_path)}, ensure_ascii=False, indent=2))
        return 0

    pending = [code for code in symbols if code not in completed]
    print(json.dumps({
        "status": "starting",
        "symbols": len(symbols),
        "pending": len(pending),
        "workers": args.workers,
        "calls_per_minute": args.calls_per_minute,
        "start": args.start,
        "end": args.end,
        "progress_path": str(progress_path),
    }, ensure_ascii=False, indent=2), flush=True)

    counts: dict[str, int] = {}
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [
            pool.submit(
                fetch_symbol,
                ts_code=ts_code,
                token=token,
                base_url=base_url,
                limiter=limiter,
                cache_dir=args.cache_dir,
                start=args.start,
                end=args.end,
                freq=args.freq,
                force=args.force,
            )
            for ts_code in pending
        ]
        for idx, future in enumerate(as_completed(futures), 1):
            row = future.result()
            status = str(row.get("status"))
            counts[status] = counts.get(status, 0) + 1
            progress.setdefault("completed", {})[str(row["ts_code"])] = status
            progress.setdefault("results", []).append(row)
            if idx % 50 == 0 or idx == len(futures):
                save_json(progress_path, progress)
                print(json.dumps({
                    "done": idx,
                    "pending_total": len(pending),
                    "elapsed_s": round(time.perf_counter() - started, 1),
                    "counts": counts,
                }, ensure_ascii=False), flush=True)
    save_json(progress_path, progress)

    audit = audit_cache(args.cache_dir, symbols, args.end)
    summary = {
        "status": "completed",
        "elapsed_s": round(time.perf_counter() - started, 3),
        "counts": counts,
        "audit": audit,
        "progress_path": str(progress_path),
    }
    summary_path = args.log_dir / f"recent_stk_mins_5_summary_{args.asof_date}_{args.start[:10]}_{args.end[:10]}.json"
    save_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0 if counts.get("permission_denied", 0) == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())

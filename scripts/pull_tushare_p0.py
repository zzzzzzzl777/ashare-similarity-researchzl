from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ashare_similarity.data.tushare_proxy_client import TsyTushareProxyClient, TsyTushareProxyConfig


DEFAULT_OUTPUT_ROOT = Path(r"E:\ashare_similarity_runtime\data\cache\prediction\tushare")
DEFAULT_REPORT_DIR = REPO_ROOT / "run_logs"
DEFAULT_APIS = ("moneyflow", "limit_list_d", "top_list", "top_inst")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull P0 Tushare research data through the TSY proxy.")
    parser.add_argument("--start", default="20230101")
    parser.add_argument("--end", default="20260502")
    parser.add_argument("--apis", nargs="*", default=list(DEFAULT_APIS))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--sleep-seconds", type=float, default=0.62)
    parser.add_argument("--max-dates", type=int, default=0, help="Smoke-test limit. 0 means all remaining dates.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    cfg = TsyTushareProxyConfig.from_env()
    if cfg is None:
        print("Missing TSY_TUSHARE_TOKEN; load ashare_similarity.local.ps1 first.", file=sys.stderr)
        return 2

    client = TsyTushareProxyClient(cfg)
    start = _compact_date(args.start)
    end = _compact_date(args.end)
    trade_dates = _trade_dates(client, start=start, end=end)
    if args.max_dates and args.max_dates > 0:
        trade_dates = trade_dates[: int(args.max_dates)]

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc)
    summary: dict[str, Any] = {
        "source": "tushare_tsy_proxy",
        "generated_at": started_at.isoformat(),
        "date_range": {"start": start, "end": end},
        "requested_trade_dates": len(trade_dates),
        "apis": {},
    }
    for api_name in args.apis:
        api_summary = _pull_trade_date_api(
            client,
            api_name=api_name,
            trade_dates=trade_dates,
            output_root=output_root,
            sleep_seconds=float(args.sleep_seconds),
            overwrite=bool(args.overwrite),
        )
        summary["apis"][api_name] = api_summary
    summary["completed_at"] = datetime.now(timezone.utc).isoformat()
    summary["fingerprint"] = _hash_payload(summary)
    report_path = report_dir / f"data_coverage_tushare_p0_{started_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    _atomic_write_text(report_path, json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    print(json.dumps({"status": "completed", "report_path": str(report_path), "apis": summary["apis"]}, ensure_ascii=False, indent=2, default=str))
    return 0


def _pull_trade_date_api(
    client: TsyTushareProxyClient,
    *,
    api_name: str,
    trade_dates: list[str],
    output_root: Path,
    sleep_seconds: float,
    overwrite: bool,
) -> dict[str, Any]:
    api_dir = output_root / api_name
    api_dir.mkdir(parents=True, exist_ok=True)
    log_path = api_dir / "_pull_log.json"
    progress = _load_json(log_path) or {
        "api_name": api_name,
        "completed_dates": [],
        "empty_dates": [],
        "failed_dates": [],
        "total_rows": 0,
        "last_update": None,
    }
    done = set(progress.get("completed_dates") or [])
    if overwrite:
        done = set()
        progress["completed_dates"] = []
        progress["empty_dates"] = []
        progress["failed_dates"] = []
        progress["total_rows"] = 0
    remaining = [date_text for date_text in trade_dates if date_text not in done]
    consecutive_errors = 0
    rows_added = 0
    files_written = 0
    failed: list[dict[str, str]] = []
    print(f"[tushare_p0] {api_name}: done={len(done)} remaining={len(remaining)}", flush=True)
    for index, trade_date in enumerate(remaining, start=1):
        try:
            frame = client.query(api_name, trade_date=trade_date)
            if frame is None:
                frame = pd.DataFrame()
            if not frame.empty:
                path = api_dir / f"{trade_date}.parquet"
                _atomic_write_parquet(path, frame)
                rows = int(len(frame))
                rows_added += rows
                files_written += 1
                progress["total_rows"] = int(progress.get("total_rows") or 0) + rows
            else:
                progress.setdefault("empty_dates", []).append(trade_date)
            progress.setdefault("completed_dates", []).append(trade_date)
            progress["last_update"] = datetime.now(timezone.utc).isoformat()
            if index == 1 or index % 25 == 0 or index == len(remaining):
                _atomic_write_text(log_path, json.dumps(progress, ensure_ascii=False, indent=2, default=str))
                print(
                    f"[tushare_p0] {api_name}: {index}/{len(remaining)} latest={trade_date} "
                    f"rows_total={progress.get('total_rows')}",
                    flush=True,
                )
            consecutive_errors = 0
            time.sleep(max(sleep_seconds, 0.0))
        except Exception as exc:
            consecutive_errors += 1
            error = str(exc)
            failed.append({"trade_date": trade_date, "error": error[:500]})
            progress.setdefault("failed_dates", []).append({"trade_date": trade_date, "error": error[:500]})
            _atomic_write_text(log_path, json.dumps(progress, ensure_ascii=False, indent=2, default=str))
            print(f"[tushare_p0] {api_name}: ERROR {trade_date}: {error[:160]}", flush=True)
            if "40203" in error:
                time.sleep(60.0)
            else:
                time.sleep(min(30.0, 2.0 ** min(consecutive_errors, 5)))
            if consecutive_errors >= 5:
                print(f"[tushare_p0] {api_name}: stopping after 5 consecutive errors", flush=True)
                break
    _atomic_write_text(log_path, json.dumps(progress, ensure_ascii=False, indent=2, default=str))
    return _coverage_summary(api_name=api_name, api_dir=api_dir, trade_dates=trade_dates, rows_added=rows_added, files_written=files_written, failed=failed)


def _coverage_summary(
    *,
    api_name: str,
    api_dir: Path,
    trade_dates: list[str],
    rows_added: int,
    files_written: int,
    failed: list[dict[str, str]],
) -> dict[str, Any]:
    parquet_files = sorted(api_dir.glob("*.parquet"))
    dates_with_files = {path.stem for path in parquet_files}
    completed_log = _load_json(api_dir / "_pull_log.json") or {}
    completed_dates = set(completed_log.get("completed_dates") or [])
    total_rows = 0
    symbols: set[str] = set()
    file_fingerprints: list[dict[str, Any]] = []
    for path in parquet_files:
        try:
            stat = path.stat()
            frame = pd.read_parquet(path, columns=None)
            total_rows += int(len(frame))
            if "ts_code" in frame.columns:
                symbols.update(frame["ts_code"].dropna().astype(str).unique().tolist())
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            file_fingerprints.append({"name": path.name, "rows": int(len(frame)), "size": int(stat.st_size), "sha256": digest})
        except Exception as exc:
            file_fingerprints.append({"name": path.name, "error": str(exc)[:200]})
    coverage = len(completed_dates.intersection(trade_dates)) / max(len(trade_dates), 1)
    return {
        "source": "tushare_tsy_proxy",
        "function": api_name,
        "date_range": {"start": min(trade_dates) if trade_dates else None, "end": max(trade_dates) if trade_dates else None},
        "symbol_count": len(symbols),
        "rows": total_rows,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "asof_rule": "trade_date data; usable after the source has published T-day data for T+1 research only",
        "coverage": round(float(coverage), 6),
        "requested_trade_dates": len(trade_dates),
        "completed_dates": len(completed_dates.intersection(trade_dates)),
        "dates_with_files": len(dates_with_files),
        "rows_added_this_run": rows_added,
        "files_written_this_run": files_written,
        "missing_reason": "not_started_or_empty_or_failed" if coverage < 1.0 else None,
        "failed": failed[-10:],
        "fingerprint": _hash_payload(file_fingerprints),
    }


def _trade_dates(client: TsyTushareProxyClient, *, start: str, end: str) -> list[str]:
    cal = client.query("trade_cal", exchange="SSE", start_date=start, end_date=end, is_open="1")
    if cal is None or cal.empty or "cal_date" not in cal.columns:
        raise RuntimeError("trade_cal returned no open dates")
    return sorted(cal["cal_date"].astype(str).tolist())


def _compact_date(value: str) -> str:
    return pd.to_datetime(str(value).replace("-", ""), format="%Y%m%d", errors="raise").strftime("%Y%m%d")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _hash_payload(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _atomic_write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(tmp_path, index=False)
    tmp_path.replace(path)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())

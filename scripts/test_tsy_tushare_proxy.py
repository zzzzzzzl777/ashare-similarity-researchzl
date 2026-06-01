from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ashare_similarity.data.tushare_proxy_client import TsyTushareProxyClient, TsyTushareProxyConfig


def _parse_dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test TSY tushare proxy connectivity (no token printed).")
    parser.add_argument("--ts-code", default="600000.SH", help="tushare ts_code, e.g. 600000.SH")
    parser.add_argument("--freq", default="5min", help="minute frequency: 1min/5min/15min/30min/60min")
    parser.add_argument("--start", default=None, help="start datetime, e.g. 2026-05-01 09:30:00")
    parser.add_argument("--end", default=None, help="end datetime, e.g. 2026-05-01 15:00:00")
    args = parser.parse_args()

    cfg = TsyTushareProxyConfig.from_env()
    if cfg is None:
        print("Missing env var TSY_TUSHARE_TOKEN. Refusing to run.")
        return 2

    client = TsyTushareProxyClient(cfg)
    # Basic connectivity sanity check first (low cost).
    try:
        cal = client.query("trade_cal", exchange="SSE", start_date=datetime.now().strftime("%Y%m01"))
        print(f"trade_cal ok: rows={len(cal)} base_url={cfg.base_url}")
    except Exception as exc:
        print(f"trade_cal failed: {exc}")
        return 3

    end_dt = _parse_dt(args.end) if args.end else datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
    start_dt = _parse_dt(args.start) if args.start else (end_dt - timedelta(hours=6))

    try:
        df = client.fetch_stock_mins(ts_code=args.ts_code, freq=args.freq, start_date=start_dt, end_date=end_dt)
    except Exception as exc:
        print(f"stk_mins failed: {exc}")
        print(
            "If the error mentions 40203 / frequency limit, it usually means either:\n"
            "1) minute permission not enabled for this token, or\n"
            "2) daily quota already exhausted (shared upstream / per-token limit).\n"
            "Ask the seller whether stk_mins permission+quota is truly independent per token."
        )
        return 4

    print(f"stk_mins ok: ts_code={args.ts_code} freq={args.freq} rows={len(df)}")
    if len(df) > 0:
        print("head:")
        print(df.head(3).to_string(index=False))
        print("tail:")
        print(df.tail(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

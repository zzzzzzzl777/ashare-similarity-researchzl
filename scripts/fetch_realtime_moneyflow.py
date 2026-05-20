# -*- coding: utf-8 -*-
"""Fetch real-time moneyflow from eastmoney push2 — honest capability assessment.

What push2 CAN reliably provide (batch, via ulist.np):
  f62  -> net main force inflow (主力净流入), in 元
  f8   -> turnover (换手率), raw value in percentage points (e.g. 5.81 = 5.81%)

What push2 CANNOT reliably provide:
  f135-f142 buy/sell breakdown — batch endpoints return garbage values.
  Individual qt/stock/get endpoint returns different field semantics and is
  too slow for full universe fetch. NOT validated against tushare ground truth.

Consequence for selected features:
  tushare_net_mf_amount      -> CAN approximate from f62 (net flow, same semantics)
  tushare_lg_buy_sell_ratio  -> CANNOT (needs buy_lg / sell_lg split)
  tushare_elg_buy_sell_ratio -> CANNOT (needs buy_elg / sell_elg split)
  tushare_mf_strength        -> CANNOT (needs big_buy / big_sell split)
  tushare_sm_sell_pressure   -> CANNOT (needs sell_sm / total_sm)
  tushare_main_force_divergence -> CANNOT (depends on lg/elg ratios)
  tushare_mf_flow_intensity  -> PARTIALLY (needs total_buy_amount)

Usage:
    from fetch_realtime_moneyflow import fetch_net_mf_batch, fetch_turnover_batch
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from typing import Optional

import numpy as np
import pandas as pd

PUSH2_BASE = "http://push2.eastmoney.com/api/qt/ulist.np/get"

# Features that REQUIRE buy/sell breakdown (push2 cannot provide reliably)
MONEYFLOW_BREAKDOWN_FEATURES = (
    "tushare_lg_buy_sell_ratio",
    "tushare_elg_buy_sell_ratio",
    "tushare_mf_strength",
    "tushare_sm_sell_pressure",
    "tushare_main_force_divergence",
    "tushare_mf_flow_intensity",
)

# Features that CAN be approximated from push2 net flow
MONEYFLOW_NET_FEATURES = (
    "tushare_net_mf_amount",
)


def _push2_get(url: str, timeout: int = 15, retries: int = 3) -> dict | None:
    """HTTP GET to push2 via urllib. Retries on 502 Bad Gateway."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=timeout)
            return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 502 and attempt < retries:
                time.sleep(1.0 + attempt * 0.5)
                continue
            return None
        except Exception:
            if attempt < retries:
                time.sleep(1.0)
                continue
            return None
    return None


def _secid(symbol: str) -> str:
    """Convert 6-digit symbol to push2 secid format."""
    if symbol.startswith("6"):
        return f"1.{symbol}"
    return f"0.{symbol}"


def fetch_net_mf_batch(
    symbols: list[str],
    timeout: int = 15,
    batch_size: int = 50,
) -> dict[str, float]:
    """Fetch net main force inflow (f62) for all symbols via batch endpoint.

    Returns dict of symbol -> net_mf_amount in 元 (NOT 万元).
    Caller must convert to 万元 (/ 10000) to match tushare training scale.
    """
    results = {}
    consecutive_failures = 0

    for i in range(0, len(symbols), batch_size):
        if consecutive_failures >= 5:
            break

        batch = symbols[i:i + batch_size]
        secid_str = ",".join(_secid(s) for s in batch)
        url = (f"{PUSH2_BASE}?secids={secid_str}"
               f"&fields=f12,f62"
               f"&ut=fa5fd1943c7b386f172d6893dbbd1821")
        try:
            data = _push2_get(url, timeout=timeout)
            if data and data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    sym = item.get("f12", "")
                    f62 = item.get("f62")
                    if f62 is not None and f62 != "-":
                        results[sym] = float(f62)
                consecutive_failures = 0
            else:
                consecutive_failures += 1
        except Exception as e:
            print(f"  [net_mf batch] chunk {i} failed: {e}")
            consecutive_failures += 1
        time.sleep(0.15)

    return results


def fetch_turnover_batch(
    symbols: list[str],
    timeout: int = 15,
    batch_size: int = 50,
) -> dict[str, float]:
    """Fetch turnover (f8) from push2 batch endpoint.

    Returns dict of symbol -> turnover in PERCENTAGE POINTS (e.g. 5.81 = 5.81%).
    This matches tushare daily_basic turnover_rate unit.
    NOTE: push2 f8 is raw percentage * 100, so we divide by 100 here.
          Example: f8=581 means 5.81%.
    """
    results = {}
    consecutive_failures = 0

    for i in range(0, len(symbols), batch_size):
        if consecutive_failures >= 5:
            break

        batch = symbols[i:i + batch_size]
        secid_str = ",".join(_secid(s) for s in batch)
        url = (f"{PUSH2_BASE}?secids={secid_str}"
               f"&fields=f12,f8"
               f"&ut=fa5fd1943c7b386f172d6893dbbd1821")
        try:
            data = _push2_get(url, timeout=timeout)
            if data and data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    sym = item.get("f12", "")
                    raw = item.get("f8")
                    if raw is not None and raw != "-":
                        results[sym] = float(raw) / 100.0
                consecutive_failures = 0
            else:
                consecutive_failures += 1
        except Exception as e:
            print(f"  [turnover batch] chunk {i} failed: {e}")
            consecutive_failures += 1
        time.sleep(0.15)

    return results


def compute_turnover_from_volume(
    volume_map: dict[str, float],
    float_share_map: dict[str, float],
) -> dict[str, float]:
    """Compute normal turnover percentage from realtime volume and cached float_share.

    turnover_pct = realtime_volume / (float_share * 10000) * 100
    float_share is in 万股, volume is in 股. This matches tushare
    daily_basic.turnover_rate. free_share would instead approximate
    daily_basic.turnover_rate_f.

    Returns dict of symbol -> turnover in percentage points (matches tushare).
    """
    results = {}
    for sym, vol in volume_map.items():
        fs = float_share_map.get(sym)
        if fs and fs > 0 and vol > 0:
            results[sym] = vol / (fs * 10000.0) * 100.0
    return results


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    test_symbols = ["000001", "600519", "300750", "002594", "688981"]
    print(f"=== Push2 capability test ({len(test_symbols)} symbols) ===")
    print(f"NOTE: push2 only responds during market hours (9:15-15:30)")
    print()

    print("--- Net MF (f62) ---")
    net_mf = fetch_net_mf_batch(test_symbols)
    if net_mf:
        for sym, val in net_mf.items():
            print(f"  {sym}: {val:>15,.0f} yuan = {val/10000:>10,.2f} 万元")
    else:
        print("  No data (market closed?)")

    print()
    print("--- Turnover (f8) ---")
    turnover = fetch_turnover_batch(test_symbols)
    if turnover:
        for sym, val in turnover.items():
            print(f"  {sym}: {val:.4f}%")
    else:
        print("  No data (market closed?)")

    print()
    print("--- Feature availability summary ---")
    print(f"  tushare_net_mf_amount: {'PROXY (from f62)' if net_mf else 'MISSING'}")
    for f in MONEYFLOW_BREAKDOWN_FEATURES:
        print(f"  {f}: UNAVAILABLE (no buy/sell split from push2)")

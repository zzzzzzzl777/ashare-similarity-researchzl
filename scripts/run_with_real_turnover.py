# -*- coding: utf-8 -*-
"""Run inference with today's REAL turnover from eastmoney."""
import sys, requests, time, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\scripts")
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\src")

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

from realtime_1457_today_probe import (
    load_bundle, run_inference, get_universe_from_cache,
    build_config, load_daily_bars, build_symbol_features,
    attach_all_factors, align_features,
    WarmupState, BUNDLE_PATH, TUSHARE_DIR, NAME_CACHE_PATH, TODAY,
)
from ashare_similarity.prediction.gpu_probe import build_ths_sector_factors, _ensure_feature_columns

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}


def fetch_eastmoney_batch(symbols):
    session = requests.Session()
    session.trust_env = False
    results = {}
    batch_size = 50
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        secids = []
        for s in batch:
            if s.startswith("6"):
                secids.append(f"1.{s}")
            else:
                secids.append(f"0.{s}")
        secid_str = ",".join(secids)
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "secids": secid_str,
            "fields": "f12,f14,f2,f3,f5,f6,f8,f15,f16,f17,f18",
            "ut": "fa5fd1943c7b386f172d6893dbbd1821",
        }
        try:
            r = session.get(url, params=params, timeout=15, proxies=PROXY)
            if r.status_code == 200:
                data = r.json()
                if data.get("data") and data["data"].get("diff"):
                    for item in data["data"]["diff"]:
                        sym = item.get("f12", "")
                        results[sym] = {
                            "latest_price": item.get("f2", 0) / 100 if item.get("f2") else np.nan,
                            "volume": item.get("f5", 0) * 100 if item.get("f5") else 0,
                            "amount": item.get("f6", 0) if item.get("f6") else 0,
                            "turnover": item.get("f8", 0) / 100 if item.get("f8") else np.nan,
                            "high": item.get("f15", 0) / 100 if item.get("f15") else np.nan,
                            "low": item.get("f16", 0) / 100 if item.get("f16") else np.nan,
                            "open": item.get("f17", 0) / 100 if item.get("f17") else np.nan,
                            "prev_close": item.get("f18", 0) / 100 if item.get("f18") else np.nan,
                            "name": item.get("f14", ""),
                        }
        except Exception as e:
            print(f"  Batch {i} failed: {e}")
        time.sleep(0.3)
    return results


def main():
    print("[0] Fetching today real data from eastmoney...")
    universe = get_universe_from_cache()
    em_data = fetch_eastmoney_batch(universe)
    print(f"    Got: {len(em_data)}/{len(universe)} stocks")

    # Build snapshot with REAL turnover
    rows = []
    for sym in universe:
        if sym in em_data:
            d = em_data[sym]
            rows.append({
                "symbol": sym, "name": d["name"],
                "open": d["open"], "high": d["high"], "low": d["low"],
                "latest_price": d["latest_price"],
                "volume": d["volume"], "amount": d["amount"],
                "turnover": d["turnover"], "prev_close": d["prev_close"],
            })
    snapshot = pd.DataFrame(rows)
    snapshot["symbol"] = snapshot["symbol"].astype(str).str.zfill(6)
    print(f"    Turnover available: {snapshot['turnover'].notna().sum()}/{len(snapshot)}")

    # Warmup
    state = WarmupState()
    state.bundle = load_bundle(BUNDLE_PATH)
    state.universe = universe
    state.config = build_config()
    state.all_bars = load_daily_bars(state.universe, state.config.start, TODAY - timedelta(days=1))
    print(f"[1] Bundle + bars loaded ({len(state.all_bars)} symbols)")

    state.ths_factor = build_ths_sector_factors(TUSHARE_DIR)
    print(f"[2] THS sector loaded")

    state.name_map = {}
    if NAME_CACHE_PATH.exists():
        with open(NAME_CACHE_PATH, "r", encoding="utf-8") as f:
            state.name_map = json.load(f)

    # LIVE with real turnover
    print()
    print("=" * 60)
    print("LIVE — real close + real turnover from eastmoney")
    print("=" * 60)
    t_live = time.perf_counter()

    snap_universe = snapshot[snapshot["latest_price"] > 0].copy()
    print(f"[1] Valid stocks: {len(snap_universe)}")

    # Inject today's bar with REAL turnover
    snap_map = snap_universe.set_index("symbol")
    dummy_date = TODAY + timedelta(days=1)
    bars_with_today = {}
    injected = 0
    for sym, df in state.all_bars.items():
        bars_with_today[sym] = df
        if sym not in snap_map.index:
            continue
        row = snap_map.loc[sym]
        if pd.isna(row.get("latest_price")) or row.get("latest_price", 0) <= 0:
            continue
        if (df["date"].dt.date == TODAY).any():
            continue
        price = row["latest_price"]
        real_turnover = row.get("turnover", np.nan)
        today_row = {
            "date": pd.Timestamp(TODAY),
            "open": row.get("open", np.nan),
            "high": row.get("high", np.nan),
            "low": row.get("low", np.nan),
            "close": price,
            "volume": row.get("volume", np.nan),
            "amount": row.get("amount", np.nan),
            "turnover": real_turnover,
        }
        dummy_row = {
            "date": pd.Timestamp(dummy_date),
            "open": price, "high": price, "low": price, "close": price,
            "volume": 0.0, "amount": 0.0, "turnover": 0.0,
        }
        bars_with_today[sym] = pd.concat([df, pd.DataFrame([today_row, dummy_row])], ignore_index=True)
        injected += 1
    print(f"[2] Injected with real turnover: {injected} stocks")

    # Build features
    print("[3] Building symbol features...")
    data, context_frames, sym_timing = build_symbol_features(bars_with_today, state.config, TODAY)
    print(f"    Accepted: {len(data)} rows")

    if data.empty:
        print("FATAL: No features")
        sys.exit(1)

    precomputed = {"ths_factor": state.ths_factor}
    data, factor_timing = attach_all_factors(data, context_frames, state.config, precomputed=precomputed)
    print(f"[4] After factors: {data.shape[1]} columns")

    data = _ensure_feature_columns(data)

    if "limit_up_like" in data.columns:
        before = len(data)
        data = data[data["limit_up_like"] != 1].copy()
        print(f"[5] Limit-up filter: {before} -> {len(data)}")

    raw_features, gap_stats = align_features(data, state.bundle)
    print(f"[6] Feature alignment: {raw_features.shape}")
    print(f"    unavailable: {gap_stats['unavailable_feature_count']}")

    prob = run_inference(state.bundle, raw_features)
    total_live = time.perf_counter() - t_live
    print(f"[7] Inference: {len(prob)} predictions")
    print(f"LIVE TOTAL: {total_live:.1f}s")

    # Output
    symbols = data["symbol"].values
    names = [state.name_map.get(s, "") for s in symbols]
    out_df = pd.DataFrame({
        "symbol": symbols, "name": names, "probability": prob,
        "close": [snap_map.loc[s, "latest_price"] if s in snap_map.index else np.nan for s in symbols],
        "turnover_today": [snap_map.loc[s, "turnover"] if s in snap_map.index else np.nan for s in symbols],
        "pct_change": [
            (snap_map.loc[s, "latest_price"] / snap_map.loc[s, "prev_close"] - 1) * 100
            if s in snap_map.index and snap_map.loc[s, "prev_close"] > 0 else np.nan
            for s in symbols
        ],
    })
    out_df = out_df.sort_values("probability", ascending=False).reset_index(drop=True)

    threshold = state.bundle["threshold"]
    print(f"\n=== 今日候选（收盘价 + 今日真实换手率, threshold={threshold:.2f}）===")
    print(f"Total scored: {len(out_df)}")
    print(f"Above threshold: {(out_df['probability'] >= threshold).sum()}")
    print(f"Prob >= 0.75: {(out_df['probability'] >= 0.75).sum()}")
    print(f"Prob >= 0.70: {(out_df['probability'] >= 0.70).sum()}")
    print()

    hc = out_df[out_df["probability"] >= 0.75]
    print(f"高置信候选 (>= 0.75): {len(hc)} 只")
    for _, r in hc.iterrows():
        print(f"  {r['symbol']}  {str(r['name'])[:10]:<10} prob={r['probability']:.4f}  "
              f"收盘={r['close']:.2f}  换手={r['turnover_today']:.2f}%  涨跌={r['pct_change']:+.2f}%")

    print()
    top20 = out_df.head(20)
    print("Top 20:")
    for _, r in top20.iterrows():
        print(f"  {r['symbol']}  {str(r['name'])[:10]:<10} prob={r['probability']:.4f}  "
              f"收盘={r['close']:.2f}  换手={r['turnover_today']:.2f}%  涨跌={r['pct_change']:+.2f}%")

    out_path = r"C:\Users\zzzzzzl\Desktop\realtime_1457_candidates_20260506_close_real_turnover.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()

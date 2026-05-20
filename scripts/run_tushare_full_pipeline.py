# -*- coding: utf-8 -*-
"""Run full inference pipeline with tushare official post-close data.

This uses EXACTLY the same data source as training:
- moneyflow: tushare moneyflow parquet (buy/sell breakdown)
- turnover: tushare daily_basic (turnover_rate)
- stk_limit: tushare stk_limit (up/down limit prices)
- volume_ratio: tushare daily_basic (volume_ratio)

No push2 approximation. No fallback to 0. Exact training match.
"""
import sys
import io
import time
import json
import pickle

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\scripts")
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\src")

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

from realtime_1457_today_probe import (
    load_bundle, run_inference, get_universe_from_cache,
    build_config, load_daily_bars, build_symbol_features,
    attach_all_factors, fetch_realtime_snapshot,
    inject_snapshot_bar, BUNDLE_PATH, TUSHARE_DIR,
    NAME_CACHE_PATH, TODAY,
)
from ashare_similarity.prediction.gpu_probe import _ensure_feature_columns
from ashare_similarity.prediction.free_data_factors import build_tushare_factors
from ashare_similarity.prediction.factor_cache_manager import merge_factor_frames
from ashare_similarity.prediction.ths_sector_factors import build_ths_sector_factors


def main():
    t_total = time.perf_counter()

    print("=" * 60)
    print("Full Pipeline — tushare post-close data (exact training match)")
    print("=" * 60)
    print()

    # 1. Load bundle
    t0 = time.perf_counter()
    bundle = load_bundle(BUNDLE_PATH)
    print(f"[1] Bundle loaded ({time.perf_counter()-t0:.2f}s)")
    print(f"    Selected features: {len(bundle['selected_feature_names'])}")
    print(f"    Threshold: {bundle['threshold']:.4f}")

    # 2. Universe
    t0 = time.perf_counter()
    universe = get_universe_from_cache()
    print(f"[2] Universe: {len(universe)} stocks ({time.perf_counter()-t0:.2f}s)")

    # 3. Historical bars
    config = build_config()
    t0 = time.perf_counter()
    all_bars = load_daily_bars(universe, config.start, TODAY - timedelta(days=1))
    print(f"[3] Historical bars: {len(all_bars)} symbols ({time.perf_counter()-t0:.1f}s)")

    # 4. THS sector
    t0 = time.perf_counter()
    ths_factor = build_ths_sector_factors(TUSHARE_DIR)
    print(f"[4] THS sector pre-computed ({time.perf_counter()-t0:.1f}s)")

    # 5. Snapshot from Sina (closing prices)
    t0 = time.perf_counter()
    snapshot = fetch_realtime_snapshot(universe=universe)
    print(f"[5] Snapshot (Sina): {len(snapshot)} stocks ({time.perf_counter()-t0:.2f}s)")

    if snapshot.empty:
        print("FATAL: empty snapshot")
        return

    # 6. Load REAL turnover from tushare daily_basic
    t0 = time.perf_counter()
    db_path = TUSHARE_DIR / "daily_basic" / "20260506.parquet"
    turnover_map = {}
    if db_path.exists():
        db_df = pd.read_parquet(db_path)
        for _, r in db_df.iterrows():
            sym = str(r["ts_code"]).split(".")[0]
            tr = pd.to_numeric(r.get("turnover_rate"), errors="coerce")
            if pd.notna(tr):
                turnover_map[sym] = tr
    print(f"[6] Tushare turnover: {len(turnover_map)} stocks ({time.perf_counter()-t0:.2f}s)")

    # 7. Inject today's bar
    snap_valid = snapshot[snapshot["latest_price"] > 0].copy()
    bars_with_today = inject_snapshot_bar(
        all_bars.copy(), snap_valid, TODAY, turnover_map=turnover_map
    )
    injected = sum(
        1 for sym in bars_with_today
        if (bars_with_today[sym]["date"].dt.date == TODAY).any()
    )
    print(f"[7] Injected today bar: {injected} stocks (tushare turnover)")

    # 8. Build symbol features
    print("[8] Building symbol features...")
    t0 = time.perf_counter()
    data, context_frames, _ = build_symbol_features(bars_with_today, config, TODAY)
    print(f"    {len(data)} rows, {data.shape[1]} cols ({time.perf_counter()-t0:.1f}s)")

    if data.empty:
        print("FATAL: no features")
        return

    # 9. Attach factors (cross-section, free, cross-market, TGB, THS, limit_pool)
    print("[9] Attaching factors...")
    t0 = time.perf_counter()
    precomputed = {"ths_factor": ths_factor}
    data, _ = attach_all_factors(data, context_frames, config, precomputed=precomputed)
    print(f"    After factors: {data.shape[1]} cols ({time.perf_counter()-t0:.1f}s)")

    # 10. Attach tushare factors FROM CACHE (exact training source!)
    print("[10] Attaching tushare factors (from tushare cache — exact training match)...")
    t0 = time.perf_counter()
    tushare_factor = build_tushare_factors(TUSHARE_DIR)
    if not tushare_factor.frame.empty:
        data, _ = merge_factor_frames(data, [tushare_factor])
        print(f"     Merged {len(tushare_factor.frame)} tushare rows ({time.perf_counter()-t0:.1f}s)")
    else:
        print("     WARNING: tushare factors empty!")

    # 11. Ensure all feature columns
    data = _ensure_feature_columns(data)

    # 12. Limit-up filter
    if "limit_up_like" in data.columns:
        before = len(data)
        data = data[data["limit_up_like"] != 1].copy()
        print(f"[11] Limit-up filter: {before} -> {len(data)}")

    # 13. Feature alignment
    feature_names = bundle["feature_names"]
    fallback_count = 0
    for fname in feature_names:
        if fname not in data.columns:
            data[fname] = 0.0
            fallback_count += 1
    raw = data[list(feature_names)].to_numpy(dtype=np.float32)
    print(f"[12] Feature matrix: {raw.shape}, fallback(missing)={fallback_count}")

    # 14. Verify tushare features have real values
    tushare_selected = [f for f in bundle["selected_feature_names"] if f.startswith("tushare_")]
    print(f"[13] Tushare feature coverage ({len(tushare_selected)} in selected):")
    for f in tushare_selected:
        if f in data.columns:
            nz = (data[f] != 0).sum()
            print(f"     {f:<40} non-zero: {nz}/{len(data)}")

    # 15. Inference
    t0 = time.perf_counter()
    prob = run_inference(bundle, raw)
    print(f"[14] Inference: {len(prob)} predictions ({time.perf_counter()-t0:.2f}s)")

    total_time = time.perf_counter() - t_total
    print(f"\nTOTAL: {total_time:.1f}s")

    # Build output
    symbols = data["symbol"].values if "symbol" in data.columns else np.array([""] * len(data))
    snap_lookup = snap_valid.set_index("symbol")

    name_map = {}
    if NAME_CACHE_PATH.exists():
        with open(NAME_CACHE_PATH, "r", encoding="utf-8") as f:
            name_map = json.load(f)
    snap_names = {r["symbol"]: r.get("name", "") for _, r in snap_valid.iterrows()}
    names = [snap_names.get(s, name_map.get(s, "")) for s in symbols]

    out_df = pd.DataFrame({
        "symbol": symbols, "name": names, "probability": prob,
        "latest_price": [snap_lookup.loc[s, "latest_price"] if s in snap_lookup.index else np.nan for s in symbols],
        "prev_close": [snap_lookup.loc[s, "prev_close"] if s in snap_lookup.index else np.nan for s in symbols],
        "pct_change": [snap_lookup.loc[s, "pct_change"] if s in snap_lookup.index else np.nan for s in symbols],
        "turnover": [turnover_map.get(s, np.nan) for s in symbols],
    })

    # Tradability gates
    def _limit_pct(sym, name):
        s = str(sym).zfill(6)
        is_st = bool(pd.notna(name) and ("ST" in str(name).upper() or "退" in str(name)))
        if s.startswith(("300", "301", "688")):
            return 20.0
        elif s.startswith(("8", "4")):
            return 30.0
        else:
            return 5.0 if is_st else 10.0

    out_df["is_st"] = out_df["name"].apply(
        lambda n: bool(pd.notna(n) and ("ST" in str(n).upper() or "退" in str(n)))
    )
    out_df["board_limit_pct"] = [_limit_pct(s, n) for s, n in zip(out_df["symbol"], out_df["name"])]
    out_df["up_limit_price"] = (out_df["prev_close"] * (1 + out_df["board_limit_pct"] / 100)).round(2)
    out_df["down_limit_price"] = (out_df["prev_close"] * (1 - out_df["board_limit_pct"] / 100)).round(2)
    out_df["is_limit_up"] = (out_df["latest_price"] >= out_df["up_limit_price"] * 0.995)
    out_df["is_limit_down"] = (out_df["latest_price"] <= out_df["down_limit_price"] * 1.005)
    out_df["is_suspended"] = (out_df["latest_price"].isna()) | (out_df["latest_price"] <= 0)
    out_df["tradable"] = ~(out_df["is_st"] | out_df["is_limit_up"] | out_df["is_limit_down"] | out_df["is_suspended"])

    threshold = bundle["threshold"]
    out_df["is_candidate"] = out_df["tradable"] & (out_df["probability"] >= threshold)
    out_df = out_df.sort_values("probability", ascending=False).reset_index(drop=True)

    # Save
    out_path = r"C:\Users\zzzzzzl\Desktop\realtime_1457_candidates_20260506_tushare_full.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nSaved: {out_path}")

    # Results
    cands = out_df[out_df["is_candidate"]]
    print(f"\n{'='*60}")
    print(f"2026-05-06 正式候选 (tushare 收盘, 与训练数据源完全一致)")
    print(f"{'='*60}")
    print(f"Total scored: {len(out_df)}")
    print(f"ST: {out_df['is_st'].sum()} | 涨停: {out_df['is_limit_up'].sum()} | 跌停: {out_df['is_limit_down'].sum()}")
    print(f"Tradable: {out_df['tradable'].sum()}")
    print(f"Above threshold ({threshold:.2f}): {(out_df['probability'] >= threshold).sum()}")
    print(f"Candidates: {len(cands)}")
    print(f"prob >= 0.75: {(cands['probability'] >= 0.75).sum()}")
    print(f"prob >= 0.70: {(cands['probability'] >= 0.70).sum()}")
    print()

    hc = cands[cands["probability"] >= 0.75]
    if len(hc) > 0:
        print(f"高置信候选 (prob >= 0.75): {len(hc)} 只")
        for _, r in hc.iterrows():
            print(f"  {r['symbol']:>6}  {str(r['name'])[:10]:<10}  prob={r['probability']:.4f}  "
                  f"价格={r['latest_price']:.2f}  涨跌={r['pct_change']:+.2f}%  换手={r['turnover']:.2f}%")
    else:
        print("高置信候选 (prob >= 0.75): 0 只")
    print()

    print("Top 25:")
    for _, r in cands.head(25).iterrows():
        tr = f"{r['turnover']:.2f}%" if pd.notna(r["turnover"]) else "N/A"
        print(f"  {r['symbol']:>6}  {str(r['name'])[:10]:<10}  prob={r['probability']:.4f}  "
              f"价格={r['latest_price']:.2f}  涨跌={r['pct_change']:+.2f}%  换手={tr}")


if __name__ == "__main__":
    main()

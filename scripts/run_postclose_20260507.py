# -*- coding: utf-8 -*-
"""Run full pipeline with post-close snapshot + tushare T-1 factors for 20260507.

Since tushare hasn't published 20260507 moneyflow/daily_basic yet,
we use:
- Post-close sina snapshot (final values after 15:00)
- Turnover computed from volume / float_share (T-1 daily_basic)
- Tushare moneyflow ratios from 20260506 (T-1 is correct for features)
"""
import sys
import io
import time
import json
import warnings

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\scripts")
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\src")
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
    NAME_CACHE_PATH,
)
from ashare_similarity.prediction.gpu_probe import _ensure_feature_columns

TODAY = date(2026, 5, 7)


def main():
    t_total = time.perf_counter()

    print("=" * 60)
    print("Full Pipeline - post-close snapshot + tushare T-1 factors")
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

    # 4. Snapshot (post-close = final values)
    t0 = time.perf_counter()
    snapshot = fetch_realtime_snapshot(universe=universe)
    print(f"[4] Snapshot: {len(snapshot)} stocks ({time.perf_counter()-t0:.2f}s)")
    if snapshot.empty:
        print("FATAL: empty snapshot")
        return

    # 5. Turnover from volume/float_share (tushare daily_basic not available for today)
    t0 = time.perf_counter()
    db_dir = TUSHARE_DIR / "daily_basic"
    float_share_map = {}
    if db_dir.exists():
        for db_path in reversed(sorted(db_dir.glob("*.parquet"))):
            try:
                db_df = pd.read_parquet(db_path, columns=["ts_code", "float_share"])
            except Exception:
                continue
            for _, r in db_df.iterrows():
                sym = str(r["ts_code"]).split(".")[0]
                if sym in float_share_map:
                    continue
                fs = pd.to_numeric(r.get("float_share"), errors="coerce")
                if pd.notna(fs) and fs > 0:
                    float_share_map[sym] = fs
            if len(float_share_map) >= max(1, int(len(universe) * 0.98)):
                break

    turnover_map = {}
    for _, r in snapshot.iterrows():
        sym = r["symbol"]
        vol = r.get("volume", 0)
        fs = float_share_map.get(sym)
        if fs and fs > 0 and vol and vol > 0:
            turnover_map[sym] = vol / (fs * 10000.0) * 100.0
    print(f"[5] Turnover (vol/float_share): {len(turnover_map)} stocks ({time.perf_counter()-t0:.2f}s)")

    # 6. Inject today bar
    snap_valid = snapshot[snapshot["latest_price"] > 0].copy()
    bars_with_today = inject_snapshot_bar(
        all_bars.copy(), snap_valid, TODAY, turnover_map=turnover_map
    )
    injected = sum(
        1 for sym in bars_with_today
        if (bars_with_today[sym]["date"].dt.date == TODAY).any()
    )
    print(f"[6] Injected today bar: {injected} stocks")

    # 7. Build symbol features
    print("[7] Building symbol features...")
    t0 = time.perf_counter()
    data, context_frames, _ = build_symbol_features(bars_with_today, config, TODAY)
    print(f"    {len(data)} rows, {data.shape[1]} cols ({time.perf_counter()-t0:.1f}s)")
    if data.empty:
        print("FATAL: no features")
        return

    # 8. Attach factors
    print("[8] Attaching factors...")
    t0 = time.perf_counter()
    data, _ = attach_all_factors(data, context_frames, config, precomputed={})
    print(f"    After factors: {data.shape[1]} cols ({time.perf_counter()-t0:.1f}s)")

    # 9. Tushare moneyflow ratios (fast path: load latest 3 parquets, compute directly)
    print("[9] Attaching tushare moneyflow ratios (T-1, fast path)...")
    t0 = time.perf_counter()
    mf_dir = TUSHARE_DIR / "moneyflow"
    mf_ratio_count = 0
    if mf_dir.is_dir() and "symbol" in data.columns:
        mf_files = sorted(mf_dir.glob("*.parquet"))[-3:]
        mf_dfs = []
        for f in mf_files:
            try:
                mf_dfs.append(pd.read_parquet(f))
            except Exception:
                pass
        if mf_dfs:
            mf_df = pd.concat(mf_dfs, ignore_index=True)
            mf_df["symbol"] = mf_df["ts_code"].str.split(".").str[0]
            mf_df["_date"] = pd.to_datetime(mf_df["trade_date"], format="%Y%m%d", errors="coerce")
            mf_df = mf_df.sort_values("_date").drop_duplicates("symbol", keep="last")

            for col in ("net_mf_amount", "buy_lg_amount", "sell_lg_amount",
                        "buy_elg_amount", "sell_elg_amount", "buy_sm_amount",
                        "sell_sm_amount", "buy_md_amount", "sell_md_amount"):
                mf_df[col] = pd.to_numeric(mf_df.get(col), errors="coerce").fillna(0.0)

            big_buy = mf_df["buy_lg_amount"] + mf_df["buy_elg_amount"]
            big_sell = mf_df["sell_lg_amount"] + mf_df["sell_elg_amount"]
            lg_ratio = (mf_df["buy_lg_amount"] / np.maximum(mf_df["sell_lg_amount"], 100.0)).clip(upper=50.0)
            elg_ratio = (mf_df["buy_elg_amount"] / np.maximum(mf_df["sell_elg_amount"], 100.0)).clip(upper=50.0)
            total_buy = mf_df["buy_sm_amount"] + mf_df["buy_md_amount"] + mf_df["buy_lg_amount"] + mf_df["buy_elg_amount"]

            mf_ratios = pd.DataFrame({
                "symbol": mf_df["symbol"].values,
                "tushare_net_mf_amount": mf_df["net_mf_amount"].values,
                "tushare_lg_buy_sell_ratio": lg_ratio.values,
                "tushare_elg_buy_sell_ratio": elg_ratio.values,
                "tushare_mf_strength": ((big_buy - big_sell) / np.maximum(big_buy + big_sell, 1.0)).values,
                "tushare_sm_sell_pressure": (mf_df["sell_sm_amount"] / np.maximum(mf_df["buy_sm_amount"] + mf_df["sell_sm_amount"], 1.0)).values,
                "tushare_main_force_divergence": (lg_ratio - elg_ratio).abs().values,
                "tushare_mf_flow_intensity": (mf_df["net_mf_amount"] / np.maximum(total_buy, 1.0)).values,
            }).set_index("symbol")

            sym_col = data["symbol"]
            for col in mf_ratios.columns:
                if col in data.columns:
                    mask = sym_col.isin(mf_ratios.index)
                    data.loc[mask, col] = sym_col[mask].map(mf_ratios[col]).values
                    mf_ratio_count += int(mask.sum())
                else:
                    data[col] = sym_col.map(mf_ratios[col]).fillna(0.0).values
                    mf_ratio_count += int(sym_col.isin(mf_ratios.index).sum())
            print(f"    {mf_ratio_count} cells assigned ({time.perf_counter()-t0:.2f}s)")
        else:
            print("    WARNING: no moneyflow parquets found!")
    else:
        print("    WARNING: moneyflow dir missing or no symbol column!")

    # 10. Ensure columns
    data = _ensure_feature_columns(data)

    # 11. Limit-up filter
    if "limit_up_like" in data.columns:
        before = len(data)
        data = data[data["limit_up_like"] != 1].copy()
        print(f"[10] Limit-up filter: {before} -> {len(data)}")

    # 12. Feature alignment
    feature_names = bundle["feature_names"]
    fallback_count = 0
    for fname in feature_names:
        if fname not in data.columns:
            data[fname] = 0.0
            fallback_count += 1
    raw = data[list(feature_names)].to_numpy(dtype=np.float32)
    print(f"[11] Feature matrix: {raw.shape}, fallback(missing)={fallback_count}")

    # 13. Tushare feature coverage
    tushare_selected = [f for f in bundle["selected_feature_names"] if f.startswith("tushare_")]
    print(f"[12] Tushare feature coverage ({len(tushare_selected)} in selected):")
    for f in tushare_selected:
        if f in data.columns:
            nz = (data[f] != 0).sum()
            print(f"     {f:<40} non-zero: {nz}/{len(data)}")

    # 14. Inference
    t0 = time.perf_counter()
    prob = run_inference(bundle, raw)
    print(f"[13] Inference: {len(prob)} predictions ({time.perf_counter()-t0:.2f}s)")

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
    out_path = r"C:\Users\zzzzzzl\Desktop\realtime_1457_candidates_20260507_postclose.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nSaved: {out_path}")

    # Results
    cands = out_df[out_df["is_candidate"]]
    print(f"\n{'='*60}")
    print(f"2026-05-07 候选 (post-close snapshot + tushare T-1 factors)")
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
            tr = f"{r['turnover']:.2f}%" if pd.notna(r["turnover"]) else "N/A"
            print(f"  {r['symbol']:>6}  {str(r['name'])[:10]:<10}  prob={r['probability']:.4f}  "
                  f"价格={r['latest_price']:.2f}  涨跌={r['pct_change']:+.2f}%  换手={tr}")
    else:
        print("高置信候选 (prob >= 0.75): 0 只")
    print()

    print("Top 30:")
    for _, r in cands.head(30).iterrows():
        tr = f"{r['turnover']:.2f}%" if pd.notna(r["turnover"]) else "N/A"
        print(f"  {r['symbol']:>6}  {str(r['name'])[:10]:<10}  prob={r['probability']:.4f}  "
              f"价格={r['latest_price']:.2f}  涨跌={r['pct_change']:+.2f}%  换手={tr}")


if __name__ == "__main__":
    main()

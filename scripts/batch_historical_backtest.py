#!/usr/bin/env python
"""Batch Historical Backtest — Postclose Candidate Selection

Runs model inference on feature cache (2023-06-08 to 2026-04-29) to produce
historical candidate selections with next-day verification.

Output:
  - batch_postclose_all_candidates.csv (all prob >= 0.70, with verification)
  - batch_postclose_gaps.txt (data gap report)
"""

from __future__ import annotations

import json
import pickle
import sys
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

SUBAGENT_ROOT = Path("C:/Users/zzzzzzl/Desktop/subagent")
sys.path.insert(0, str(SUBAGENT_ROOT / "src"))

RUNTIME_ROOT = Path("E:/ashare_similarity_runtime/data")
DAILY_BARS_DIR = RUNTIME_ROOT / "raw" / "bars" / "daily"
MARKET_INDEX_PATH = RUNTIME_ROOT / "cache" / "market" / "daily" / "sh000001.parquet"
FEATURE_CACHE_PATH = (
    RUNTIME_ROOT / "reports" / "prediction" / "feature_cache"
    / "gpu_probe_features_550a77f54882058f.parquet"
)
BUNDLE_PATH = (
    RUNTIME_ROOT / "reports" / "prediction" / "runs"
    / "gpu_probe_20260509T105830Z_12605e2b" / "model_bundle.pt"
)
NAME_CACHE_PATH = SUBAGENT_ROOT / "scripts" / "_symbol_name_cache.json"
OUTPUT_DIR = RUNTIME_ROOT / "reports" / "prediction"

CANDIDATE_THRESHOLD = 0.70
HISTORY_START = pd.Timestamp("2023-06-08")
HISTORY_END = pd.Timestamp("2026-04-29")
ALL_CANDIDATES_CSV = OUTPUT_DIR / "batch_postclose_all_candidates.csv"
GAP_REPORT = OUTPUT_DIR / "batch_postclose_gaps.txt"


def load_bundle(path: Path, device: str = "cpu") -> dict:
    import torch
    bundle = torch.load(path, map_location=device, weights_only=False)
    members = []
    for m in bundle["members"]:
        model = pickle.loads(m["model_bytes"])
        members.append({"model": model, "model_name": m["model_name"],
                        "model_kind": m["model_kind"]})
    iso_model = pickle.loads(bundle["iso_model_bytes"]) if bundle.get("iso_model_bytes") else None
    return {
        "members": members,
        "mean": bundle["mean"],
        "std": bundle["std"],
        "selected_indices": bundle["selected_indices"],
        "feature_names": bundle["feature_names"],
        "selected_feature_names": bundle["selected_feature_names"],
        "iso_model": iso_model,
        "calibration_used": bundle["calibration_used"],
        "threshold": bundle["threshold"],
    }


def run_inference(bundle: dict, raw_features: np.ndarray, device: str = "cpu") -> np.ndarray:
    import torch
    x = torch.as_tensor(raw_features, dtype=torch.float32, device=device)
    mean = bundle["mean"].to(device)
    std = bundle["std"].to(device)
    std_safe = std.clone()
    std_safe[std_safe == 0] = 1.0
    x = (x - mean) / std_safe
    if bundle["selected_indices"] is not None:
        x = x[:, bundle["selected_indices"].to(device)]
    x_np = x.detach().cpu().numpy()
    probs = np.stack([m["model"].predict_proba(x_np)[:, 1].astype(np.float32)
                      for m in bundle["members"]], axis=0)
    prob = probs.mean(axis=0)
    if bundle["calibration_used"] == "isotonic" and bundle["iso_model"] is not None:
        prob = bundle["iso_model"].predict(prob.astype(np.float64)).astype(np.float32)
    return prob


def main() -> int:
    t_total = time.perf_counter()
    print("=" * 60)
    print("BATCH HISTORICAL BACKTEST — All candidates >= 0.70")
    print("=" * 60)

    # 1. Load model bundle
    t0 = time.perf_counter()
    bundle = load_bundle(BUNDLE_PATH)
    feature_names = list(bundle["feature_names"])
    print(f"[1] Bundle loaded ({time.perf_counter()-t0:.2f}s): "
          f"{len(feature_names)} features, {len(bundle['selected_feature_names'])} selected")

    # 2. Trading calendar → next-day map
    t0 = time.perf_counter()
    cal = pd.read_parquet(MARKET_INDEX_PATH, columns=["date"])
    cal_dates = pd.to_datetime(cal["date"]).dt.date.sort_values().tolist()
    next_day_map = {cal_dates[i]: cal_dates[i + 1] for i in range(len(cal_dates) - 1)}
    print(f"[2] Calendar loaded ({time.perf_counter()-t0:.2f}s): {len(cal_dates)} days")

    # 3. Name map
    t0 = time.perf_counter()
    raw_names = json.loads(NAME_CACHE_PATH.read_text(encoding="utf-8"))
    name_map = {str(k).zfill(6): v for k, v in raw_names.items()}
    print(f"[3] Name map ({time.perf_counter()-t0:.2f}s): {len(name_map)} symbols")

    # 4. Feature cache → inference
    t0 = time.perf_counter()
    fc = pd.read_parquet(FEATURE_CACHE_PATH)
    fc["date"] = pd.to_datetime(fc["date"])
    fc["symbol"] = fc["symbol"].astype(str).str.zfill(6)
    fc = fc[(fc["date"] >= HISTORY_START) & (fc["date"] <= HISTORY_END)].copy()
    n_before = len(fc)
    fc = fc.drop_duplicates(subset=["symbol", "date"], keep="first")
    n_deduped = n_before - len(fc)
    print(f"[4] Feature cache ({time.perf_counter()-t0:.2f}s): {len(fc)} rows, "
          f"{fc['date'].nunique()} dates"
          + (f" (deduplicated {n_deduped})" if n_deduped > 0 else ""))

    # 4a. Compute missing daily-derived factors from daily bars
    t0 = time.perf_counter()
    DAILY_DERIVED_COLS = [
        "tushare_price_vs_cost_20d", "tushare_abnormal_3d_deviation",
        "tushare_inv_t_20d", "tushare_asr_60d", "tushare_illiq_classic_20d",
        "tushare_vol_gain_20d", "tushare_ato_120d",
    ]
    # Force recompute: drop stale daily-derived columns from cache so they get recalculated
    stale_cols = [c for c in DAILY_DERIVED_COLS if c in fc.columns]
    if stale_cols:
        fc.drop(columns=stale_cols, inplace=True)
        print(f"[4a] Dropped {len(stale_cols)} stale daily-derived columns from cache for recompute")
    missing_in_cache = [f for f in feature_names if f not in fc.columns]
    need_daily_derived = [f for f in missing_in_cache if f in DAILY_DERIVED_COLS]
    if need_daily_derived:
        print(f"[4a] Computing {len(need_daily_derived)} missing daily-derived factors from bars...")
        _derived_chunks: list[pd.DataFrame] = []
        for fpath in sorted(DAILY_BARS_DIR.glob("*.parquet")):
            try:
                df = pd.read_parquet(fpath, columns=["date", "symbol", "close", "volume", "amount", "pct_change", "turnover"])
            except Exception:
                continue
            if df.empty or len(df) < 120:
                continue
            df = df.sort_values("date").reset_index(drop=True)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            for col in ("close", "volume", "amount", "pct_change", "turnover"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
            sym = str(df["symbol"].iloc[0]).zfill(6) if "symbol" in df.columns else fpath.stem.zfill(6)
            vwap_20 = df["amount"].rolling(20, min_periods=15).sum() / df["volume"].rolling(20, min_periods=15).sum().clip(lower=1)
            out_row = {"symbol": sym, "date": df["date"]}
            if "tushare_price_vs_cost_20d" in need_daily_derived:
                out_row["tushare_price_vs_cost_20d"] = ((df["close"] - vwap_20) / vwap_20.clip(lower=0.01)).clip(-50, 50)
            if "tushare_abnormal_3d_deviation" in need_daily_derived:
                out_row["tushare_abnormal_3d_deviation"] = df["pct_change"].rolling(3, min_periods=3).sum().clip(-30, 30)
            if "tushare_inv_t_20d" in need_daily_derived:
                signed_vol = np.sign(df["pct_change"]) * df["volume"]
                out_row["tushare_inv_t_20d"] = (-signed_vol.rolling(20, min_periods=15).sum() / df["volume"].rolling(20, min_periods=15).sum().clip(lower=1)).clip(-50, 50)
            if "tushare_asr_60d" in need_daily_derived:
                p90 = df["close"].rolling(60, min_periods=40).quantile(0.9)
                p10 = df["close"].rolling(60, min_periods=40).quantile(0.1)
                out_row["tushare_asr_60d"] = ((p90 - p10) / df["close"].clip(lower=0.01)).clip(-50, 50)
            if "tushare_illiq_classic_20d" in need_daily_derived:
                abs_ret_over_amount = (df["pct_change"].abs() / 100.0) / df["amount"].clip(lower=1) * 1e10
                out_row["tushare_illiq_classic_20d"] = abs_ret_over_amount.rolling(20, min_periods=15).mean().clip(-50, 50)
            if "tushare_vol_gain_20d" in need_daily_derived:
                up_mask = df["pct_change"] > 0
                down_mask = df["pct_change"] <= 0
                to = df["turnover"]
                out_row["tushare_vol_gain_20d"] = (to.where(up_mask).rolling(20, min_periods=5).mean() / to.where(down_mask).rolling(20, min_periods=5).mean().clip(lower=0.001)).clip(-50, 50)
            if "tushare_ato_120d" in need_daily_derived:
                to = df["turnover"]
                to_20 = to.rolling(20, min_periods=15).mean()
                to_120 = to.rolling(120, min_periods=80).mean()
                to_120_std = to.rolling(120, min_periods=80).std()
                out_row["tushare_ato_120d"] = ((to_20 - to_120) / to_120_std.clip(lower=0.001)).clip(-50, 50)
            chunk = pd.DataFrame(out_row)
            chunk = chunk.dropna(subset=["date"])
            chunk = chunk[chunk["date"] >= pd.Timestamp("2017-01-01")]
            if not chunk.empty:
                _derived_chunks.append(chunk)
        if _derived_chunks:
            derived_df = pd.concat(_derived_chunks, ignore_index=True)
            derived_df["date"] = pd.to_datetime(derived_df["date"])
            derived_df["symbol"] = derived_df["symbol"].astype(str).str.zfill(6)
            fc = fc.merge(derived_df, on=["symbol", "date"], how="left", suffixes=("", "_derived"))
            for col in need_daily_derived:
                if col + "_derived" in fc.columns:
                    fc[col] = fc[col + "_derived"]
                    fc.drop(columns=[col + "_derived"], inplace=True)
                elif col not in fc.columns:
                    fc[col] = np.nan
            print(f"[4a] Daily-derived factors computed ({time.perf_counter()-t0:.1f}s): "
                  f"{len(derived_df)} rows, merged {need_daily_derived}")
        else:
            print(f"[4a] WARNING: no daily-derived factors computed")
    else:
        print(f"[4a] No missing daily-derived factors (all in cache)")

    # 4a2. Compute intraday features from 5-min bars (overwrite cache placeholders)
    t0 = time.perf_counter()
    STK_MINS_DIR = RUNTIME_ROOT / "cache" / "prediction" / "tushare" / "stk_mins_5"
    INTRADAY_FEATURES = ["tushare_last_30min_return", "tushare_vwap_deviation", "tushare_close_vs_vwap"]
    placeholder_mask = (fc["tushare_vwap_deviation"] == 0) & (fc["tushare_close_vs_vwap"] == 0)
    n_placeholder = placeholder_mask.sum()
    if n_placeholder > 1000 and STK_MINS_DIR.is_dir():
        import datetime as _dt
        t_1430 = _dt.time(14, 30)
        mins_files = sorted(STK_MINS_DIR.glob("*.parquet"))
        intraday_chunks: list[pd.DataFrame] = []
        for mf in mins_files:
            try:
                bars = pd.read_parquet(mf, columns=["ts_code", "trade_time", "close", "open", "high", "low", "vol", "amount"])
            except Exception:
                continue
            if bars.empty:
                continue
            bars["trade_time"] = pd.to_datetime(bars["trade_time"], errors="coerce")
            for col in ("close", "open", "high", "low", "vol", "amount"):
                bars[col] = pd.to_numeric(bars.get(col), errors="coerce")
            bars["symbol"] = bars["ts_code"].astype(str).str.split(".").str[0].str.zfill(6)
            bars["date"] = bars["trade_time"].dt.normalize()
            bars["time"] = bars["trade_time"].dt.time
            bars = bars.dropna(subset=["date", "close"]).sort_values(["symbol", "date", "trade_time"])
            if bars.empty:
                continue
            gk = ["symbol", "date"]
            grouped = bars.groupby(gk, sort=False)
            day_stats = grouped.agg(
                bar_count=("close", "size"),
                day_vol=("vol", "sum"),
                day_amount=("amount", "sum"),
                eod_close=("close", "last"),
            ).reset_index()
            day_stats = day_stats[(day_stats["bar_count"] >= 5) & (day_stats["day_vol"] > 0)].copy()
            if day_stats.empty:
                continue
            day_stats["vwap"] = day_stats["day_amount"] / day_stats["day_vol"]
            last30 = bars[bars["time"] >= t_1430].groupby(gk, sort=False).agg(
                l30_open=("open", "first"), l30_close=("close", "last"), l30_count=("close", "size"),
            ).reset_index()
            last30["tushare_last_30min_return"] = np.where(
                last30["l30_count"] >= 2, last30["l30_close"] / last30["l30_open"] - 1, np.nan)
            result = day_stats.merge(last30[gk + ["tushare_last_30min_return"]], on=gk, how="left")
            result["tushare_vwap_deviation"] = (result["eod_close"] - result["vwap"]) / np.maximum(np.abs(result["vwap"]), 0.01)
            result["tushare_close_vs_vwap"] = (result["eod_close"] / np.maximum(result["vwap"], 0.01)) - 1.0
            intraday_chunks.append(result[gk + INTRADAY_FEATURES].copy())

        if intraday_chunks:
            intraday_df = pd.concat(intraday_chunks, ignore_index=True)
            intraday_df["date"] = pd.to_datetime(intraday_df["date"])
            intraday_df["symbol"] = intraday_df["symbol"].astype(str).str.zfill(6)
            # Replace 0-placeholder intraday values with NaN so 5min-computed values take priority
            placeholder_mask = (fc["tushare_vwap_deviation"] == 0) & (fc["tushare_close_vs_vwap"] == 0)
            if placeholder_mask.any():
                for col in INTRADAY_FEATURES:
                    if col in fc.columns:
                        fc.loc[placeholder_mask, col] = np.nan
                print(f"[4a2] Cleared {placeholder_mask.sum()} intraday placeholder rows before merge")
            fc = fc.merge(intraday_df, on=["symbol", "date"], how="left", suffixes=("", "_5min"))
            for col in INTRADAY_FEATURES:
                col_5min = col + "_5min"
                if col_5min in fc.columns:
                    fc[col] = fc[col_5min].combine_first(fc[col])
                    fc.drop(columns=[col_5min], inplace=True)
            print(f"[4a2] Intraday features computed from 5-min bars ({time.perf_counter()-t0:.1f}s): "
                  f"{len(mins_files)} files, {len(intraday_df)} rows")
        else:
            print(f"[4a2] WARNING: no intraday features computed from 5-min bars")
    else:
        print(f"[4a2] Skipped 5-min bar processing ({n_placeholder} placeholders, threshold=1000)")
        placeholder_mask = (fc["tushare_vwap_deviation"] == 0) & (fc["tushare_close_vs_vwap"] == 0)

    # 4b. Drop rows with missing/placeholder intraday data
    # When 5-min bars are unavailable, vwap_deviation and close_vs_vwap are both 0 (placeholder).
    # In real data these two are NEVER both 0 simultaneously — safe to use as "no data" marker.
    t0 = time.perf_counter()
    CRITICAL_INTRADAY = [
        "tushare_last_30min_return",
        "tushare_vwap_deviation",
        "tushare_close_vs_vwap",
    ]
    still_missing = [f for f in feature_names if f not in fc.columns]
    for fname in still_missing:
        fc[fname] = 0.0
    if still_missing:
        print(f"[4b] Filled {len(still_missing)} remaining missing features with 0: {still_missing[:5]}...")

    # Drop rows where vwap_deviation AND close_vs_vwap are both 0 (no 5-min data)
    if "tushare_vwap_deviation" in fc.columns and "tushare_close_vs_vwap" in fc.columns:
        no_intraday_mask = (fc["tushare_vwap_deviation"] == 0) & (fc["tushare_close_vs_vwap"] == 0)
        n_dropped_intraday = no_intraday_mask.sum()
        fc = fc.loc[~no_intraday_mask]
        print(f"[4b] Dropped {n_dropped_intraday} rows without intraday data "
              f"({len(fc)} rows remain)")

    # Build raw feature matrix and drop ANY row with NaN in selected features
    raw = fc[feature_names].to_numpy(dtype=np.float32)
    selected_idx = bundle["selected_indices"].numpy() if bundle["selected_indices"] is not None else np.arange(raw.shape[1])
    selected_raw = raw[:, selected_idx]
    row_has_nan = np.isnan(selected_raw).any(axis=1)
    n_nan_rows = row_has_nan.sum()
    if n_nan_rows > 0:
        fc = fc.loc[~row_has_nan]
        raw = raw[~row_has_nan]
        print(f"[4b] Dropped {n_nan_rows} additional rows with NaN in selected features "
              f"({len(fc)} rows remain)")

    fc["probability"] = run_inference(bundle, raw)
    print(f"[5] Inference ({time.perf_counter()-t0:.2f}s): "
          f"{(fc['probability'] >= CANDIDATE_THRESHOLD).sum()} above {CANDIDATE_THRESHOLD}")

    # 5. Filter to candidates >= threshold
    cands = fc[fc["probability"] >= CANDIDATE_THRESHOLD].copy()
    cands["name"] = cands["symbol"].map(name_map).fillna("")
    st_mask = cands["name"].str.contains("ST|退", case=False, na=False)
    n_st = st_mask.sum()
    cands = cands[~st_mask].copy()
    print(f"[6] After ST filter: {len(cands)} candidates ({n_st} ST excluded)")

    # 6. Build date/label_date columns
    cands["signal_date"] = cands["date"].dt.date
    cands["label_date"] = cands["signal_date"].map(next_day_map)
    no_next = cands["label_date"].isna()
    n_no_next = no_next.sum()
    cands = cands[~no_next].copy()
    print(f"[7] Dropped {n_no_next} rows with no next trading day")

    # 7. Load daily bars for next-day verification (vectorized)
    t0 = time.perf_counter()
    next_day_records = []
    symbols_needed = cands["symbol"].unique()
    for sym in symbols_needed:
        path = DAILY_BARS_DIR / f"{sym}.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path, columns=["date", "high", "close"])
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df.rename(columns={"high": "next_high", "close": "next_close"})
        df["symbol"] = sym
        df = df.rename(columns={"date": "label_date"})
        next_day_records.append(df[["symbol", "label_date", "next_high", "next_close"]])

    if next_day_records:
        next_day_df = pd.concat(next_day_records, ignore_index=True)
    else:
        next_day_df = pd.DataFrame(columns=["symbol", "label_date", "next_high", "next_close"])
    print(f"[8] Daily bars loaded ({time.perf_counter()-t0:.2f}s): "
          f"{len(symbols_needed)} symbols, {len(next_day_df)} next-day records")

    # 8. Merge next-day data
    cands = cands.merge(next_day_df, on=["symbol", "label_date"], how="left")

    today_close = cands["close"].astype(float)
    valid_close = (today_close > 0) & today_close.notna()
    cands["next_high_return_pct"] = np.where(
        valid_close & cands["next_high"].notna(),
        np.round((cands["next_high"].astype(float) / today_close - 1) * 100, 2),
        np.nan,
    )
    cands["next_close_return_pct"] = np.where(
        valid_close & cands["next_close"].notna(),
        np.round((cands["next_close"].astype(float) / today_close - 1) * 100, 2),
        np.nan,
    )
    cands["hit"] = np.where(
        cands["next_high_return_pct"].notna(),
        np.where(cands["next_high_return_pct"] >= 1.0, "hit", "miss"),
        "",
    )

    # 9. Format and sort
    def fmt_d(d):
        if pd.isna(d):
            return ""
        if isinstance(d, date):
            return f"{d.year}/{d.month}/{d.day}"
        return str(d)

    out = pd.DataFrame({
        "date": cands["signal_date"].map(fmt_d),
        "label_date": cands["label_date"].map(fmt_d),
        "symbol": cands["symbol"],
        "name": cands["name"],
        "probability": cands["probability"].round(6),
        "hit": cands["hit"],
        "next_high_return_pct": cands["next_high_return_pct"],
        "next_close_return_pct": cands["next_close_return_pct"],
        "close": cands["close"].round(2),
        "换手": cands["turnover"].round(2),
    })
    out["_sort_date"] = cands["signal_date"].values
    out = out.sort_values(["_sort_date", "probability"], ascending=[True, False]).reset_index(drop=True)
    out.drop(columns=["_sort_date"], inplace=True)

    # 10. Write
    t0 = time.perf_counter()
    out.to_csv(ALL_CANDIDATES_CSV, index=False, encoding="utf-8-sig")
    print(f"[9] CSV written ({time.perf_counter()-t0:.2f}s): {ALL_CANDIDATES_CSV}")
    print(f"    Total rows: {len(out)}")
    print(f"    Date range: {out['date'].iloc[0]} to {out['date'].iloc[-1]}")
    print(f"    Unique dates: {out['date'].nunique()}")

    # Stats
    verified = out[out["hit"].isin(["hit", "miss"])]
    if len(verified) > 0:
        hits = (verified["hit"] == "hit").sum()
        total = len(verified)
        print(f"\n=== STATS (prob >= {CANDIDATE_THRESHOLD}) ===")
        print(f"  Verified: {total}, Hits: {hits} ({hits/total*100:.2f}%)")
        print(f"  Avg next_high_return: {verified['next_high_return_pct'].mean():.2f}%")
        print(f"  Avg next_close_return: {verified['next_close_return_pct'].mean():.2f}%")

    # Gap report — comprehensive
    fc_all_dates = sorted(fc["date"].dt.date.unique())
    out_dates_set = set(out["date"].map(lambda d: date(*[int(x) for x in d.split("/")])).unique()) if len(out) > 0 else set()
    no_candidate_dates = sorted(set(fc_all_dates) - out_dates_set)
    unverified_mask = ~out["hit"].isin(["hit", "miss"])
    unverified_dates = sorted(out.loc[unverified_mask, "date"].unique()) if unverified_mask.any() else []

    gap = [
        "=== 历史验证数据覆盖报告 ===",
        f"Feature cache 覆盖: {fc_all_dates[0]} ~ {fc_all_dates[-1]} ({len(fc_all_dates)} 个交易日)",
        f"输出候选覆盖: {out['date'].iloc[0]} ~ {out['date'].iloc[-1]} ({out['date'].nunique()} 个交易日)",
        f"",
        f"=== 统计 ===",
        f"总候选: {len(out)} (prob >= {CANDIDATE_THRESHOLD})",
        f"ST 排除: {n_st}",
        f"无下一交易日: {n_no_next}",
        f"未验证 (无次日行情): {unverified_mask.sum()}",
        f"命中率: {hits}/{total} = {hits/total*100:.2f}%" if len(verified) > 0 else "命中率: N/A",
        f"",
        f"=== 无候选日期 ({len(no_candidate_dates)} 天) ===",
        f"(这些日期 feature cache 中有数据，但模型未给出 prob >= {CANDIDATE_THRESHOLD} 的候选)",
    ]
    for d in no_candidate_dates:
        gap.append(f"  {d}")

    gap.extend([
        f"",
        f"=== 缺失数据区间 ===",
        f"Feature cache 起始前 (~ {fc_all_dates[0]}): 无 feature cache",
        f"Feature cache 结束后 ({fc_all_dates[-1]} ~): 需要更新 feature cache",
    ])

    if unverified_dates:
        gap.extend([
            f"",
            f"=== 未验证日期 ({len(unverified_dates)} 天) ===",
            f"(有候选但无次日行情数据，无法计算 hit/miss)",
        ])
        for d in unverified_dates:
            gap.append(f"  {d}")

    gap.append(f"\n耗时: {time.perf_counter()-t_total:.1f}s")
    GAP_REPORT.write_text("\n".join(gap), encoding="utf-8")
    print(f"\n[10] Gap report: {GAP_REPORT}")
    print(f"\nDONE — {time.perf_counter()-t_total:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

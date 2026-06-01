"""Sidecar PhaseC v2 pred_high scorer for May 2026.

This script is intentionally read-only with respect to the production Web
feature cache and bundles.  It reconstructs the 30 stable PhaseC v2 features
for May realtime candidate CSVs, scores the existing second-stage model, and
writes separate sidecar outputs.
"""

from __future__ import annotations

import json
import math
import pickle
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore


REPORT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
OUT_DIR = REPORT_DIR / "sidecar"
REALTIME_DIR = Path(r"C:\Users\zzzzzzl\Desktop\realtime_1457_outputs")
MODEL_PATH = REPORT_DIR / "phasec_surge_v2_strict_20260520_models.pkl"
EXISTING_SCORED = REPORT_DIR / "phasec_surge_v2_strict_20260520_scored.parquet"
RUN_TAG = "phasec_may_pred_high_sidecar_20260521"
THRESHOLD = 0.70


@dataclass
class SourceChoice:
    date: pd.Timestamp
    candidate_file: Path
    snapshot_file: Path | None
    data_grade: str
    candidate_asof: str
    snapshot_asof: str | None


def zsym(value) -> str:
    text = str(value).strip()
    if "." in text:
        text = text.split(".")[0]
    return text.zfill(6)


def parse_dt(value) -> pd.Timestamp:
    return pd.to_datetime(value, errors="coerce")


def rolling_with_pad(values: np.ndarray, window: int, op: str) -> np.ndarray:
    values = np.asarray(values, dtype="float64")
    if len(values) == 0:
        return values
    padded = np.concatenate([np.repeat(values[0], window - 1), values])
    out = np.empty(len(values), dtype="float64")
    for i in range(len(values)):
        chunk = padded[i : i + window]
        if op == "mean":
            out[i] = np.nanmean(chunk)
        elif op == "std":
            out[i] = np.nanstd(chunk)
        elif op == "max":
            out[i] = np.nanmax(chunk)
        elif op == "min":
            out[i] = np.nanmin(chunk)
        elif op == "sum":
            out[i] = np.nansum(chunk)
        else:
            raise ValueError(op)
    return out


def lag(values: np.ndarray, periods: int) -> np.ndarray:
    values = np.asarray(values, dtype="float64")
    if len(values) == 0 or periods <= 0:
        return values
    out = np.empty(len(values), dtype="float64")
    out[:periods] = values[0]
    out[periods:] = values[:-periods]
    return out


def pct_change(values: np.ndarray, periods: int) -> np.ndarray:
    l = lag(values, periods)
    return (values / np.clip(l, 1e-6, None) - 1.0) * 100.0


def limit_threshold(symbol: str) -> float:
    s = zsym(symbol)
    if s.startswith(("300", "301", "688", "689", "830", "831", "832", "833", "834", "835", "836", "837", "838", "839", "870", "871", "872", "873", "874", "875", "876", "877", "878", "879", "430", "431", "432", "433", "434", "435", "436", "437", "438", "439")):
        return 20.0
    return 10.0


def compute_symbol_features(group: pd.DataFrame) -> pd.DataFrame:
    g = group.sort_values("date").copy()
    open_ = pd.to_numeric(g["open"], errors="coerce").to_numpy("float64")
    high = pd.to_numeric(g["high"], errors="coerce").to_numpy("float64")
    low = pd.to_numeric(g["low"], errors="coerce").to_numpy("float64")
    close = pd.to_numeric(g["close"], errors="coerce").to_numpy("float64")
    volume = pd.to_numeric(g["volume"], errors="coerce").fillna(0.0).to_numpy("float64")
    amount = pd.to_numeric(g["amount"], errors="coerce").fillna(0.0).to_numpy("float64")
    turnover = pd.to_numeric(g["turnover"], errors="coerce").fillna(0.0).to_numpy("float64")
    eps = 1e-6

    prev_close = lag(close, 1)
    ret_1 = pct_change(close, 1)
    volume_log = np.log1p(np.clip(volume, 0, None))
    amount_log = np.log1p(np.clip(amount, 0, None))
    high_low = np.clip(high - low, eps, None)
    range_pct = (high - low) / np.clip(close, eps, None) * 100.0
    close_position = (close - low) / high_low
    upper_shadow_pct = (high - np.maximum(open_, close)) / high_low
    lower_shadow_pct = (np.minimum(open_, close) - low) / high_low
    gap_pct = (open_ / np.clip(prev_close, eps, None) - 1.0) * 100.0
    volume_z_20 = (volume_log - rolling_with_pad(volume_log, 20, "mean")) / np.clip(rolling_with_pad(volume_log, 20, "std"), eps, None)
    amount_z_20 = (amount_log - rolling_with_pad(amount_log, 20, "mean")) / np.clip(rolling_with_pad(amount_log, 20, "std"), eps, None)
    ret_std_10 = rolling_with_pad(ret_1, 10, "std")
    true_range = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    atr_14_pct = rolling_with_pad(true_range, 14, "mean") / np.clip(close, eps, None) * 100.0
    ma_5 = rolling_with_pad(close, 5, "mean")
    ma_10 = rolling_with_pad(close, 10, "mean")
    ma_20 = rolling_with_pad(close, 20, "mean")
    gains = np.clip(ret_1, 0, None)
    losses = np.clip(-ret_1, 0, None)
    rsi_14 = 100.0 - (100.0 / (1.0 + rolling_with_pad(gains, 14, "mean") / np.clip(rolling_with_pad(losses, 14, "mean"), eps, None)))

    lim = limit_threshold(g["symbol"].iloc[0])
    limit_detect = lim - 0.5
    near_limit_close = ((ret_1 >= (lim - 2.0)) & (close_position >= 0.75)).astype("float64")
    limit_up_flag = (ret_1 >= limit_detect).astype("float64")
    active_turnover_flag = ((turnover >= 3.0) & (amount >= 200_000_000.0) & (range_pct >= 3.0)).astype("float64")

    out = g[["date", "symbol", "name"]].copy()
    out["close"] = close
    out["ret_1"] = ret_1
    out["ret_3"] = pct_change(close, 3)
    out["ret_5"] = pct_change(close, 5)
    out["range_pct"] = range_pct
    out["body_pct"] = (close - open_) / np.clip(open_, eps, None) * 100.0
    out["upper_shadow_pct"] = upper_shadow_pct
    out["lower_shadow_pct"] = lower_shadow_pct
    out["close_position"] = close_position
    out["gap_pct"] = gap_pct
    out["ma_gap_5"] = close / np.clip(ma_5, eps, None) - 1.0
    out["ma_gap_10"] = close / np.clip(ma_10, eps, None) - 1.0
    out["ma_gap_20"] = close / np.clip(ma_20, eps, None) - 1.0
    out["rsi_14"] = rsi_14
    out["atr_14_pct"] = atr_14_pct
    out["turnover_chg_1"] = pct_change(turnover, 1)
    out["turnover_to_max_20"] = turnover / np.clip(rolling_with_pad(turnover, 20, "max"), eps, None)
    out["range_lag_1"] = lag(range_pct, 1)
    out["range_lag_2"] = lag(range_pct, 2)
    out["range_lag_3"] = lag(range_pct, 3)
    out["range_lag_4"] = lag(range_pct, 4)
    out["range_mean_3"] = rolling_with_pad(range_pct, 3, "mean")
    out["limit_up_freq_60"] = rolling_with_pad(limit_up_flag, 60, "mean")
    out["near_limit_freq_60"] = rolling_with_pad(near_limit_close, 60, "mean")
    out["active_turnover_freq_60"] = rolling_with_pad(active_turnover_flag, 60, "mean")
    out["_volume_z_20"] = volume_z_20
    out["_amount_z_20"] = amount_z_20
    out["_ret_std_10"] = ret_std_10
    return out


def add_cross_section(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["cs_market_mean_range"] = out.groupby("date")["range_pct"].transform("mean").fillna(0.0)
    out["_cs_ret_1_rank"] = out.groupby("date")["ret_1"].rank(pct=True).fillna(0.5)
    out["_cs_range_rank"] = out.groupby("date")["range_pct"].rank(pct=True).fillna(0.5)
    out["volume_z_x_cs_ret_rank"] = out["_volume_z_20"] * out["_cs_ret_1_rank"]
    out["close_pos_x_cs_range_rank"] = out["close_position"] * out["_cs_range_rank"]
    return out


def choose_candidate_file(date: pd.Timestamp) -> tuple[Path | None, str]:
    files = sorted(REALTIME_DIR.glob(f"realtime_1457_m1457_full_{date:%Y%m%d}_*.csv"))
    if not files:
        return None, "missing_candidate_csv"
    scored: list[tuple[int, int, Path, str]] = []
    for path in files:
        try:
            df = pd.read_csv(path, dtype={"symbol": str})
        except Exception:
            continue
        if df.empty or "probability" not in df.columns:
            continue
        asof = str(df.get("asof_time", pd.Series([""])).dropna().astype(str).iloc[0]) if "asof_time" in df.columns and df["asof_time"].notna().any() else ""
        asof_ts = parse_dt(asof)
        rows = len(df)
        score = 0
        if pd.notna(asof_ts):
            t = asof_ts.time()
            minutes = t.hour * 60 + t.minute + t.second / 60
            if 14 * 60 + 50 <= minutes <= 15 * 60:
                score += 1000
            if minutes <= 15 * 60:
                score += 100
            score -= int(abs(minutes - (14 * 60 + 57)))
        if rows < 20:
            score -= 500
        scored.append((score, rows, path, asof))
    if not scored:
        return None, "unreadable_candidate_csv"
    scored.sort(key=lambda x: (x[0], x[1], x[2].stat().st_mtime), reverse=True)
    return scored[0][2], scored[0][3]


def choose_snapshot_file(date: pd.Timestamp) -> tuple[Path | None, str, str]:
    exact = REALTIME_DIR / f"sina_snapshot_1457_{date:%Y%m%d}.parquet"
    if exact.exists():
        return exact, "exact_1457", f"{date:%Y-%m-%d} 14:57"
    post = sorted(REALTIME_DIR.glob(f"sina_snapshot_postclose_{date:%Y%m%d}_*.parquet"), key=lambda p: p.stat().st_mtime)
    if post:
        return post[-1], "postclose_proxy", ""
    return None, "missing_snapshot", ""


def load_extra_daily_rows(symbols: set[str], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    tushare_dir = Path(r"E:\ashare_similarity_runtime\data\cache\prediction\tushare\stk_factor_pro")
    for path in sorted(tushare_dir.glob("*.parquet")):
        try:
            d = pd.to_datetime(path.stem, format="%Y%m%d")
        except Exception:
            continue
        if d < start or d > end:
            continue
        try:
            f = pd.read_parquet(path)
        except Exception:
            continue
        if "ts_code" not in f.columns:
            continue
        tmp = pd.DataFrame()
        tmp["symbol"] = f["ts_code"].astype(str).str[:6].map(zsym)
        tmp = tmp[tmp["symbol"].isin(symbols)].copy()
        if tmp.empty:
            continue
        tmp["date"] = d
        tmp["name"] = ""
        tmp["open"] = pd.to_numeric(f.loc[tmp.index, "open"], errors="coerce")
        tmp["high"] = pd.to_numeric(f.loc[tmp.index, "high"], errors="coerce")
        tmp["low"] = pd.to_numeric(f.loc[tmp.index, "low"], errors="coerce")
        tmp["close"] = pd.to_numeric(f.loc[tmp.index, "close"], errors="coerce")
        tmp["volume"] = pd.to_numeric(f.loc[tmp.index, "vol"], errors="coerce") * 100.0
        tmp["amount"] = pd.to_numeric(f.loc[tmp.index, "amount"], errors="coerce") * 1000.0
        tmp["turnover"] = pd.to_numeric(f.loc[tmp.index, "turnover_rate"], errors="coerce")
        tmp["source"] = "tushare_stk_factor_pro"
        frames.append(tmp)

    for path in sorted(REALTIME_DIR.glob("sina_snapshot_postclose_202605*.parquet"), key=lambda p: p.stat().st_mtime):
        parts = path.stem.split("_")
        ymd = next((p for p in parts if p.startswith("202605") and len(p) == 8), None)
        if not ymd:
            continue
        d = pd.to_datetime(ymd, format="%Y%m%d")
        if d < start or d > end:
            continue
        snap = normalize_snapshot(pd.read_parquet(path), d)
        snap = snap[snap["symbol"].isin(symbols)].copy()
        if snap.empty:
            continue
        snap["source"] = f"postclose_snapshot:{path.name}"
        frames.append(snap)

    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    return out.dropna(subset=["date", "symbol", "close"])


def normalize_snapshot(snap: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
    out = snap.copy()
    out["symbol"] = out["symbol"].map(zsym)
    out["date"] = date
    out["name"] = out.get("name", "")
    out["open"] = pd.to_numeric(out.get("open", np.nan), errors="coerce")
    out["high"] = pd.to_numeric(out.get("high", np.nan), errors="coerce")
    out["low"] = pd.to_numeric(out.get("low", np.nan), errors="coerce")
    out["close"] = pd.to_numeric(out.get("latest_price", out.get("close", np.nan)), errors="coerce")
    out["volume"] = pd.to_numeric(out.get("volume", np.nan), errors="coerce")
    out["amount"] = pd.to_numeric(out.get("amount", np.nan), errors="coerce")
    out["turnover"] = pd.to_numeric(out.get("turnover", np.nan), errors="coerce")
    return out[["date", "symbol", "name", "open", "high", "low", "close", "volume", "amount", "turnover"]]


def load_existing_cache_rows() -> pd.DataFrame:
    if not EXISTING_SCORED.exists():
        return pd.DataFrame()
    df = pd.read_parquet(EXISTING_SCORED)
    df["date"] = pd.to_datetime(df["date"])
    sub = df[(df["date"] >= "2026-05-06") & (df["date"] <= "2026-05-08")].copy()
    if sub.empty:
        return sub
    prob_col = "iso_prob" if "iso_prob" in sub.columns else "raw_prob"
    out = pd.DataFrame(
        {
            "date": sub["date"],
            "symbol": sub["symbol"].map(zsym),
            "name": sub.get("name", ""),
            "probability": pd.to_numeric(sub[prob_col], errors="coerce"),
            "raw_prob": pd.to_numeric(sub.get("raw_prob", sub[prob_col]), errors="coerce"),
            "iso_prob": pd.to_numeric(sub.get("iso_prob", sub[prob_col]), errors="coerce"),
            "pred_high_pct": pd.to_numeric(sub["pred_high_pct"], errors="coerce"),
            "pred_high_minus2_pct": pd.to_numeric(sub.get("v2_pred_high2_mean", np.nan), errors="coerce"),
            "surge5_prob": pd.to_numeric(sub.get("v2_surge5_prob_mean", np.nan), errors="coerce"),
            "limit10_prob": pd.to_numeric(sub.get("v2_limit10_prob_mean", np.nan), errors="coerce"),
            "latest_price": pd.to_numeric(sub.get("close", np.nan), errors="coerce"),
            "pct_change": pd.to_numeric(sub.get("ret_1", np.nan), errors="coerce"),
            "turnover_today": np.nan,
            "data_grade": "existing_phasec_feature_cache_to_0508",
            "candidate_file": str(EXISTING_SCORED),
            "snapshot_file": str(EXISTING_SCORED),
            "notes": "PhaseC v2 scored parquet already contains second-stage predictions.",
        }
    )
    return out[out["probability"] >= THRESHOLD].copy()


def score_sidecar_dates() -> tuple[pd.DataFrame, dict]:
    with MODEL_PATH.open("rb") as f:
        bundle = pickle.load(f)
    stable_features = list(bundle["stable_features"])
    seeds = list(bundle["seeds"])
    models_by_seed = bundle["final_models_per_seed"]

    source_choices: list[SourceChoice] = []
    candidate_frames: list[pd.DataFrame] = []
    for d in pd.date_range("2026-05-11", "2026-05-20", freq="D"):
        cfile, asof = choose_candidate_file(d)
        if cfile is None:
            continue
        sfile, snap_grade, snap_asof = choose_snapshot_file(d)
        data_grade = snap_grade
        asof_ts = parse_dt(asof)
        if pd.notna(asof_ts):
            minutes = asof_ts.hour * 60 + asof_ts.minute + asof_ts.second / 60
            if not (14 * 60 + 50 <= minutes <= 15 * 60):
                data_grade = f"{snap_grade}_candidate_asof_{asof_ts:%H%M%S}"
            elif abs(minutes - (14 * 60 + 57)) > 3:
                data_grade = f"{snap_grade}_candidate_near1457"
        if snap_grade == "postclose_proxy":
            data_grade = "postclose_proxy_not_live"
        source_choices.append(SourceChoice(d, cfile, sfile, data_grade, asof, snap_asof))
        c = pd.read_csv(cfile, dtype={"symbol": str})
        c["date"] = d
        c["symbol"] = c["symbol"].map(zsym)
        c["probability"] = pd.to_numeric(c["probability"], errors="coerce")
        c["raw_prob"] = c["probability"]
        c["iso_prob"] = c["probability"]
        c["candidate_file"] = str(cfile)
        c["candidate_asof"] = asof
        c["data_grade"] = data_grade
        c["snapshot_file"] = str(sfile) if sfile else ""
        candidate_frames.append(c)

    if not candidate_frames:
        return pd.DataFrame(), {"error": "no_candidate_frames"}

    candidates = pd.concat(candidate_frames, ignore_index=True)
    candidates = candidates.dropna(subset=["probability"])
    candidate_symbols = set(candidates["symbol"].unique())

    cfg = get_default_config()
    store = LocalDataStore(cfg)
    print(f"Loading base daily bars for {len(candidate_symbols)} symbols...", flush=True)
    loaded = store.load_market_data(
        "daily",
        symbols=sorted(candidate_symbols),
        start_date=date(2025, 10, 1),
        end_date=date(2026, 5, 20),
    ).to_pandas()
    loaded["symbol"] = loaded["symbol"].map(zsym)
    loaded["date"] = pd.to_datetime(loaded["date"])
    keep_cols = ["date", "symbol", "open", "high", "low", "close", "volume", "amount", "turnover"]
    history_base = loaded[[c for c in keep_cols if c in loaded.columns]].copy()
    history_base["name"] = ""
    history_base["source"] = "local_daily_bars"
    extra = load_extra_daily_rows(candidate_symbols, pd.Timestamp("2026-05-06"), pd.Timestamp("2026-05-20"))
    print(f"Base bars={len(history_base):,}; extra daily rows={len(extra):,}", flush=True)

    scored_parts: list[pd.DataFrame] = []
    detail: list[dict] = []

    for choice in source_choices:
        d = choice.date
        c = candidates[candidates["date"].eq(d)].copy()
        if c.empty:
            continue
        hist = history_base[history_base["date"] < d].copy()
        if not extra.empty:
            hist = pd.concat([hist, extra[extra["date"] < d]], ignore_index=True)
        hist = hist[hist["symbol"].isin(set(c["symbol"]))].copy()
        hist = hist.drop_duplicates(["symbol", "date"], keep="last")

        if choice.snapshot_file and choice.snapshot_file.exists():
            snap = normalize_snapshot(pd.read_parquet(choice.snapshot_file), d)
        else:
            snap = pd.DataFrame(columns=["date", "symbol", "name", "open", "high", "low", "close", "volume", "amount", "turnover"])
        cur = c.merge(snap, on="symbol", how="left", suffixes=("", "_snap"))
        for col in ["name", "open", "high", "low", "close", "volume", "amount", "turnover"]:
            snap_col = f"{col}_snap"
            if snap_col in cur.columns:
                if col in cur.columns:
                    cur[col] = cur[snap_col].combine_first(cur[col])
                else:
                    cur[col] = cur[snap_col]
        cur["name"] = cur["name"].combine_first(cur.get("name_snap", pd.Series(index=cur.index, dtype=object))).fillna("")
        cur["open"] = pd.to_numeric(cur["open"], errors="coerce").fillna(pd.to_numeric(cur.get("prev_close", np.nan), errors="coerce"))
        cur["close"] = pd.to_numeric(cur["close"], errors="coerce").fillna(pd.to_numeric(cur.get("latest_price", np.nan), errors="coerce"))
        cur["high"] = pd.to_numeric(cur["high"], errors="coerce").fillna(np.maximum(cur["open"], cur["close"]))
        cur["low"] = pd.to_numeric(cur["low"], errors="coerce").fillna(np.minimum(cur["open"], cur["close"]))
        cur["volume"] = pd.to_numeric(cur["volume"], errors="coerce").fillna(0.0)
        cur["amount"] = pd.to_numeric(cur["amount"], errors="coerce").fillna(cur["volume"] * cur["close"])
        cur["turnover"] = pd.to_numeric(cur.get("turnover_today", cur.get("turnover", np.nan)), errors="coerce").combine_first(pd.to_numeric(cur["turnover"], errors="coerce")).fillna(0.0)

        cur_bars = cur[["date", "symbol", "name", "open", "high", "low", "close", "volume", "amount", "turnover"]].copy()
        bars = pd.concat([hist[["date", "symbol", "name", "open", "high", "low", "close", "volume", "amount", "turnover"]], cur_bars], ignore_index=True)
        bars = bars.dropna(subset=["date", "symbol", "close"])
        feat = pd.concat([compute_symbol_features(g) for _, g in bars.groupby("symbol", sort=False)], ignore_index=True)
        today_feat = add_cross_section(feat[feat["date"].eq(d)].copy())
        today = cur.merge(today_feat, on=["date", "symbol"], how="left", suffixes=("", "_feat"))
        if "name_feat" in today.columns:
            today["name"] = today["name"].replace("", np.nan).combine_first(today["name_feat"]).fillna("")
        for col in stable_features:
            if col not in today.columns:
                today[col] = 0.0
        X = today[stable_features].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32)
        pred_high = []
        pred_high2 = []
        surge5 = []
        limit10 = []
        for seed in seeds:
            clf5, clf10, reg_h, reg_h2 = models_by_seed[seed]
            surge5.append(clf5.predict_proba(X)[:, 1])
            limit10.append(clf10.predict_proba(X)[:, 1])
            pred_high.append(np.clip(reg_h.predict(X), -10, 20))
            pred_high2.append(np.clip(reg_h2.predict(X), -10, 18.0))
        today["surge5_prob"] = np.mean(np.vstack(surge5), axis=0)
        today["limit10_prob"] = np.mean(np.vstack(limit10), axis=0)
        today["pred_high_pct"] = np.mean(np.vstack(pred_high), axis=0)
        today["pred_high_minus2_pct"] = np.mean(np.vstack(pred_high2), axis=0)
        today["latest_price"] = today["close"]
        today["pct_change"] = today["ret_1"]
        today["notes"] = np.where(
            today["data_grade"].eq("exact_1457"),
            "sidecar exact 14:57 snapshot + realtime candidate probability",
            "sidecar proxy/near snapshot; see data_grade",
        )
        scored_parts.append(today)
        detail.append(
            {
                "date": f"{d:%Y-%m-%d}",
                "candidate_rows": int(len(c)),
                "snapshot_rows": int(len(snap)),
                "scored_rows": int(len(today)),
                "data_grade": choice.data_grade,
                "candidate_file": str(choice.candidate_file),
                "snapshot_file": str(choice.snapshot_file) if choice.snapshot_file else None,
            }
        )
        print(f"{d:%Y-%m-%d}: scored {len(today):,} rows ({choice.data_grade})", flush=True)

    if not scored_parts:
        return pd.DataFrame(), {"error": "no_scored_parts", "sources": detail}
    sidecar_all = pd.concat(scored_parts, ignore_index=True)
    out_cols = [
        "date", "symbol", "name", "probability", "raw_prob", "iso_prob",
        "pred_high_pct", "pred_high_minus2_pct", "surge5_prob", "limit10_prob",
        "latest_price", "pct_change", "turnover_today", "data_grade",
        "candidate_asof", "candidate_file", "snapshot_file", "notes",
    ]
    for col in out_cols:
        if col not in sidecar_all.columns:
            sidecar_all[col] = np.nan
    return sidecar_all[out_cols].copy(), {"sources": detail, "stable_features": stable_features}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_existing_cache_rows()
    sidecar, meta = score_sidecar_dates()
    combined = pd.concat([existing, sidecar], ignore_index=True, sort=False)
    combined["date"] = pd.to_datetime(combined["date"])
    combined["probability"] = pd.to_numeric(combined["probability"], errors="coerce")
    combined["pred_high_pct"] = pd.to_numeric(combined["pred_high_pct"], errors="coerce")
    combined = combined[combined["probability"] >= THRESHOLD].copy()
    combined = combined.drop_duplicates(["date", "symbol"], keep="last")
    combined = combined.sort_values(["date", "pred_high_pct", "probability"], ascending=[True, False, False])
    combined["rank_pred_high"] = combined.groupby("date").cumcount() + 1

    full_path = OUT_DIR / f"{RUN_TAG}_all_ge{int(THRESHOLD*100)}.parquet"
    csv_path = OUT_DIR / f"{RUN_TAG}_all_ge{int(THRESHOLD*100)}.csv"
    summary_path = OUT_DIR / f"{RUN_TAG}_summary.json"
    desktop_csv = Path.home() / "Desktop" / f"{RUN_TAG}_all_ge{int(THRESHOLD*100)}.csv"
    combined.to_parquet(full_path, index=False)
    combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
    shutil.copy2(csv_path, desktop_csv)

    daily = []
    for d, g in combined.groupby("date", sort=True):
        daily.append(
            {
                "date": f"{d:%Y-%m-%d}",
                "count": int(len(g)),
                "top": [
                    {
                        "symbol": r.symbol,
                        "name": r.name,
                        "probability": float(r.probability),
                        "pred_high_pct": float(r.pred_high_pct),
                        "data_grade": r.data_grade,
                    }
                    for r in g.head(10).itertuples(index=False)
                ],
            }
        )
    summary = {
        "run_tag": RUN_TAG,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "threshold": THRESHOLD,
        "model_path": str(MODEL_PATH),
        "production_cache_untouched": True,
        "outputs": {"parquet": str(full_path), "csv": str(csv_path), "desktop_csv": str(desktop_csv)},
        "meta": meta,
        "daily": daily,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== PhaseC May pred_high sidecar complete ===")
    print(f"rows >= {THRESHOLD:.2f}: {len(combined):,}")
    print(f"csv: {csv_path}")
    print(f"desktop: {desktop_csv}")
    for item in daily:
        print(f"\n{item['date']} count={item['count']}")
        for top in item["top"]:
            print(
                f"  {top['symbol']} {top['name']} prob={top['probability']:.6f} "
                f"pred_high={top['pred_high_pct']:.2f}% grade={top['data_grade']}"
            )


if __name__ == "__main__":
    main()

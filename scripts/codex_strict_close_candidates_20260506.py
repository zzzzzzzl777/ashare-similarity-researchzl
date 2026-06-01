#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Strict post-close candidate inference for 2026-05-06.

This is a diagnostic post-close run:
- load the frozen G model bundle;
- fetch 2026-05-06 close/turnover from Eastmoney push2;
- rebuild features with the frozen training sample gate;
- filter non-tradeable/ST/limit-up rows;
- write audited candidates.

It does not train, tune, change factors, commit, or push.
"""

from __future__ import annotations

import json
import pickle
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.stdout.reconfigure(encoding="utf-8")

SUBAGENT_ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
sys.path.insert(0, str(SUBAGENT_ROOT / "src"))

RUNTIME_ROOT = Path(r"E:\ashare_similarity_runtime\data")
DAILY_BARS_DIR = RUNTIME_ROOT / "raw" / "bars" / "daily"
MARKET_INDEX_DIR = RUNTIME_ROOT / "cache" / "market" / "daily"
TUSHARE_DIR = RUNTIME_ROOT / "cache" / "prediction" / "tushare"
LIMIT_POOL_DIR = RUNTIME_ROOT / "cache" / "prediction" / "limit_pool_snapshots"
BUNDLE_DIR = RUNTIME_ROOT / "reports" / "prediction" / "runs" / "gpu_probe_20260505T113406Z_bb25159b"
BUNDLE_PATH = BUNDLE_DIR / "model_bundle.pt"
TARGET_DATE = date(2026, 5, 6)
NEXT_DUMMY_DATE = TARGET_DATE + timedelta(days=1)
PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

OUTPUT_CSV = Path(r"C:\Users\zzzzzzl\Desktop\strict_close_candidates_20260506.csv")
AUDIT_JSON = RUNTIME_ROOT / "reports" / "prediction" / "strict_close_candidates_20260506_audit.json"

from ashare_similarity.prediction.factor_cache_manager import merge_factor_frames
from ashare_similarity.prediction.free_data_factors import build_cross_market_return_factor, build_tushare_factors
from ashare_similarity.prediction.gpu_probe import (
    GPU_PROBE_CROSS_MARKET_FEATURES,
    GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES,
    GPU_PROBE_MARKET_INDEX_SYMBOLS,
    GPU_PROBE_THS_SECTOR_FEATURES,
    GPU_PROBE_TUSHARE_FACTOR_FEATURES,
    GpuProbeConfig,
    _add_cross_section_features,
    _attach_free_factor_features,
    _attach_tgb_factor_features,
    _daily_context_slice,
    _ensure_feature_columns,
    _is_main_board_symbol,
    _symbol_feature_frame,
)
from ashare_similarity.prediction.limit_pool_snapshots import (
    build_limit_pool_snapshot_factors,
    load_snapshot_bundles,
)
from ashare_similarity.prediction.ths_sector_factors import build_ths_sector_factors


def load_bundle(path: Path, device: str = "cpu") -> dict:
    import torch

    bundle = torch.load(path, map_location=device, weights_only=False)
    members = []
    for member in bundle["members"]:
        members.append(
            {
                "model": pickle.loads(member["model_bytes"]),
                "model_name": member["model_name"],
                "model_kind": member["model_kind"],
            }
        )
    iso_model = pickle.loads(bundle["iso_model_bytes"]) if bundle.get("iso_model_bytes") else None
    return {
        "model_kind": bundle["model_kind"],
        "model_name": bundle["model_name"],
        "member_names": bundle["member_names"],
        "members": members,
        "mean": bundle["mean"],
        "std": bundle["std"],
        "selected_indices": bundle["selected_indices"],
        "feature_names": tuple(bundle["feature_names"]),
        "selected_feature_names": tuple(bundle["selected_feature_names"]),
        "iso_model": iso_model,
        "calibration_used": bundle["calibration_used"],
        "threshold": float(bundle["threshold"]),
    }


def run_inference(bundle: dict, raw_features: np.ndarray) -> np.ndarray:
    import torch

    x = torch.as_tensor(raw_features, dtype=torch.float32, device="cpu")
    mean = bundle["mean"].to("cpu")
    std = bundle["std"].to("cpu").clone()
    std[std == 0] = 1.0
    x = (x - mean) / std
    if bundle["selected_indices"] is not None:
        x = x[:, bundle["selected_indices"].to("cpu")]
    x_np = x.detach().cpu().numpy()
    probs = np.stack([m["model"].predict_proba(x_np)[:, 1].astype(np.float32) for m in bundle["members"]], axis=0)
    prob = probs.mean(axis=0)
    if bundle["calibration_used"] == "isotonic" and bundle["iso_model"] is not None:
        prob = bundle["iso_model"].predict(prob.astype(np.float64)).astype(np.float32)
    return prob


def strict_config() -> GpuProbeConfig:
    return GpuProbeConfig(
        start=TARGET_DATE - timedelta(days=400),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=TARGET_DATE + timedelta(days=5),
        short_only=True,
        main_board_only=True,
        min_turnover=3.0,
        min_amount=200_000_000.0,
        min_range_pct=3.0,
        min_volatility_pct=2.5,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_set="research",
    )


def all_main_board_symbols() -> list[str]:
    symbols = [p.stem.zfill(6) for p in DAILY_BARS_DIR.glob("*.parquet")]
    return sorted(s for s in symbols if _is_main_board_symbol(s))


def fetch_eastmoney_batch(symbols: list[str]) -> pd.DataFrame:
    session = requests.Session()
    session.trust_env = False
    rows: list[dict] = []
    for i in range(0, len(symbols), 60):
        batch = symbols[i : i + 60]
        secids = [f"{'1' if s.startswith('6') else '0'}.{s}" for s in batch]
        params = {
            "secids": ",".join(secids),
            "fields": "f12,f14,f2,f3,f5,f6,f8,f15,f16,f17,f18",
            "ut": "fa5fd1943c7b386f172d6893dbbd1821",
        }
        try:
            resp = session.get(
                "https://push2.eastmoney.com/api/qt/ulist.np/get",
                params=params,
                timeout=15,
                proxies=PROXY,
            )
            if resp.status_code != 200:
                continue
            payload = resp.json()
            diff = (payload.get("data") or {}).get("diff") or []
            for item in diff:
                sym = str(item.get("f12") or "").zfill(6)
                if not sym or sym == "000000":
                    continue
                latest = item.get("f2")
                prev_close = item.get("f18")
                open_ = item.get("f17")
                high = item.get("f15")
                low = item.get("f16")
                volume = item.get("f5")
                amount = item.get("f6")
                turnover = item.get("f8")
                rows.append(
                    {
                        "symbol": sym,
                        "rt_name": str(item.get("f14") or ""),
                        "open": open_ / 100 if open_ not in (None, "-", 0) else np.nan,
                        "high": high / 100 if high not in (None, "-", 0) else np.nan,
                        "low": low / 100 if low not in (None, "-", 0) else np.nan,
                        "close": latest / 100 if latest not in (None, "-", 0) else np.nan,
                        "prev_close": prev_close / 100 if prev_close not in (None, "-", 0) else np.nan,
                        "volume": volume * 100 if volume not in (None, "-") else np.nan,
                        "amount": amount if amount not in (None, "-") else np.nan,
                        "turnover": turnover / 100 if turnover not in (None, "-", 0) else np.nan,
                    }
                )
        except Exception:
            continue
        time.sleep(0.08)
    snapshot = pd.DataFrame(rows).drop_duplicates("symbol", keep="last")
    if snapshot.empty:
        return snapshot
    numeric_cols = ["open", "high", "low", "close", "prev_close", "volume", "amount", "turnover"]
    for col in numeric_cols:
        snapshot[col] = pd.to_numeric(snapshot[col], errors="coerce")
    snapshot["pct_change"] = (snapshot["close"] / snapshot["prev_close"] - 1.0) * 100.0
    return snapshot


def load_daily_bars(symbols: list[str], config: GpuProbeConfig) -> dict[str, pd.DataFrame]:
    bars = {}
    for sym in symbols:
        path = DAILY_BARS_DIR / f"{sym}.parquet"
        if not path.exists():
            continue
        try:
            df = pd.read_parquet(path)
        except Exception:
            continue
        if "date" not in df.columns:
            continue
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df[(df["date"].dt.date >= config.start) & (df["date"].dt.date <= TARGET_DATE - timedelta(days=1))]
        if not df.empty:
            bars[sym] = df.reset_index(drop=True)
    return bars


def inject_today_bars(bars: dict[str, pd.DataFrame], snapshot: pd.DataFrame) -> dict[str, pd.DataFrame]:
    snap = snapshot.set_index("symbol")
    out = {}
    for sym, df in bars.items():
        if sym not in snap.index:
            continue
        row = snap.loc[sym]
        if not np.isfinite(row["close"]) or row["close"] <= 0:
            continue
        today_row = {
            "date": pd.Timestamp(TARGET_DATE),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
            "amount": row["amount"],
            "turnover": row["turnover"],
        }
        dummy_row = {
            "date": pd.Timestamp(NEXT_DUMMY_DATE),
            "open": row["close"],
            "high": row["close"],
            "low": row["close"],
            "close": row["close"],
            "volume": 0.0,
            "amount": 0.0,
            "turnover": 0.0,
        }
        out[sym] = pd.concat([df, pd.DataFrame([today_row, dummy_row])], ignore_index=True)
    return out


def build_symbol_features(all_bars: dict[str, pd.DataFrame], config: GpuProbeConfig) -> tuple[pd.DataFrame, list[pd.DataFrame]]:
    import torch

    device = torch.device("cpu")
    examples = []
    context_frames = []
    symbols = list(all_bars)
    t0 = time.perf_counter()
    for idx, sym in enumerate(symbols, 1):
        bars_df = all_bars[sym]
        context = _daily_context_slice(bars_df, symbol=sym, start=config.start, end=config.end)
        if not context.empty:
            context_frames.append(context)
        frame = _symbol_feature_frame(bars_df, symbol=sym, start=config.start, end=config.end, device=device, config=config)
        if not frame.empty:
            row = frame[frame["date"].dt.date == TARGET_DATE]
            if not row.empty:
                examples.append(row)
        if idx == 1 or idx % 500 == 0 or idx == len(symbols):
            print(f"  features {idx}/{len(symbols)} accepted={len(examples)} elapsed={time.perf_counter() - t0:.1f}s", flush=True)
    if not examples:
        return pd.DataFrame(), context_frames
    return pd.concat(examples, ignore_index=True), context_frames


def attach_factors(data: pd.DataFrame, context_frames: list[pd.DataFrame], config: GpuProbeConfig) -> tuple[pd.DataFrame, dict]:
    reports: dict[str, str | int | float | bool] = {}
    data = _add_cross_section_features(data)
    data, _ = _attach_free_factor_features(data, daily_context_frames=context_frames)
    data, _ = _attach_tgb_factor_features(data, daily_context_frames=context_frames)

    index_frames = {}
    for symbol in GPU_PROBE_MARKET_INDEX_SYMBOLS:
        path = MARKET_INDEX_DIR / f"{symbol}.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df[(df["date"].dt.date >= config.start) & (df["date"].dt.date <= config.end)]
        if not df.empty:
            index_frames[symbol] = df
    if index_frames:
        data, _ = merge_factor_frames(data, [build_cross_market_return_factor(index_frames)])
    else:
        for col in GPU_PROBE_CROSS_MARKET_FEATURES:
            data[col] = 0.0
            data[f"{col}_available"] = 0.0

    try:
        ths = build_ths_sector_factors(TUSHARE_DIR)
        if not ths.frame.empty:
            data, _ = merge_factor_frames(data, [ths])
        reports["ths_rows"] = int(len(ths.frame))
    except Exception as exc:
        reports["ths_error"] = str(exc)
        for col in GPU_PROBE_THS_SECTOR_FEATURES:
            data[col] = 0.0

    try:
        tushare_factor = build_tushare_factors(TUSHARE_DIR)
        reports["tushare_factor_rows"] = int(len(tushare_factor.frame))
        reports["tushare_has_target_date"] = bool(
            not tushare_factor.frame.empty
            and (pd.to_datetime(tushare_factor.frame["date"], errors="coerce").dt.date == TARGET_DATE).any()
        )
        if not tushare_factor.frame.empty:
            data, _ = merge_factor_frames(data, [tushare_factor])
    except Exception as exc:
        reports["tushare_error"] = str(exc)
        for col in GPU_PROBE_TUSHARE_FACTOR_FEATURES:
            data[col] = 0.0

    try:
        frames = load_snapshot_bundles(LIMIT_POOL_DIR) if LIMIT_POOL_DIR.is_dir() else []
        factors = build_limit_pool_snapshot_factors(frames) if frames else []
        if factors:
            data, _ = merge_factor_frames(data, factors)
        reports["limit_pool_factor_count"] = int(len(factors))
    except Exception as exc:
        reports["limit_pool_error"] = str(exc)
        for col in GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES:
            data[col] = 0.0

    data = _ensure_feature_columns(data)
    return data, reports


def align_features(data: pd.DataFrame, bundle: dict) -> tuple[np.ndarray, dict]:
    missing = []
    for feature in bundle["feature_names"]:
        if feature not in data.columns:
            data[feature] = 0.0
            missing.append(feature)
    selected = set(bundle["selected_feature_names"])
    selected_tushare = sorted(f for f in selected if f.startswith("tushare_"))
    target_tushare_missing = []
    if selected_tushare:
        target_rows = data["date"].dt.date == TARGET_DATE
        for col in selected_tushare:
            vals = pd.to_numeric(data.loc[target_rows, col], errors="coerce")
            available_col = f"{col}_available"
            if vals.notna().sum() == 0 or (available_col in data.columns and pd.to_numeric(data.loc[target_rows, available_col], errors="coerce").fillna(0).sum() == 0):
                target_tushare_missing.append(col)
    raw = data[list(bundle["feature_names"])].to_numpy(dtype=np.float32)
    return raw, {
        "missing_feature_columns": missing,
        "selected_tushare_features": selected_tushare,
        "selected_tushare_missing_or_unavailable": target_tushare_missing,
    }


def is_st_or_delist(name: str) -> bool:
    n = str(name or "").upper()
    return "ST" in n or "退" in n


def up_limit_pct(symbol: str, name: str) -> float:
    if is_st_or_delist(name):
        return 5.0
    if symbol.startswith(("300", "301", "688", "689")):
        return 20.0
    return 10.0


def main() -> None:
    t_start = time.perf_counter()
    bundle = load_bundle(BUNDLE_PATH)
    config = strict_config()
    symbols = all_main_board_symbols()
    print(f"symbols main_board={len(symbols)}")

    snapshot = fetch_eastmoney_batch(symbols)
    print(f"snapshot rows={len(snapshot)} turnover={snapshot['turnover'].notna().sum() if not snapshot.empty else 0}")
    if snapshot.empty:
        raise RuntimeError("empty Eastmoney snapshot")

    bars = load_daily_bars(symbols, config)
    print(f"daily bars loaded={len(bars)}")
    bars_today = inject_today_bars(bars, snapshot)
    print(f"today bars injected={len(bars_today)}")

    data, context_frames = build_symbol_features(bars_today, config)
    print(f"short_only feature rows={len(data)} columns={data.shape[1] if not data.empty else 0}")
    if data.empty:
        raise RuntimeError("no short_only rows")

    data, factor_reports = attach_factors(data, context_frames, config)
    raw, gap_stats = align_features(data, bundle)
    prob = run_inference(bundle, raw)

    snap = snapshot.set_index("symbol")
    out = data[["symbol", "date", "close", "limit_up_like", "turnover", "amount", "range_pct", "short_phase_days_3"]].copy()
    out["probability"] = prob
    out["name"] = [snap.loc[s, "rt_name"] if s in snap.index else "" for s in out["symbol"]]
    out["prev_close"] = [snap.loc[s, "prev_close"] if s in snap.index else np.nan for s in out["symbol"]]
    out["pct_change"] = [snap.loc[s, "pct_change"] if s in snap.index else np.nan for s in out["symbol"]]
    out["rt_turnover"] = [snap.loc[s, "turnover"] if s in snap.index else np.nan for s in out["symbol"]]
    out["rt_amount"] = [snap.loc[s, "amount"] if s in snap.index else np.nan for s in out["symbol"]]
    out["rt_high"] = [snap.loc[s, "high"] if s in snap.index else np.nan for s in out["symbol"]]
    out["rt_low"] = [snap.loc[s, "low"] if s in snap.index else np.nan for s in out["symbol"]]
    out["is_st_or_delist"] = [is_st_or_delist(n) for n in out["name"]]
    out["limit_pct_rule"] = [up_limit_pct(s, n) for s, n in zip(out["symbol"], out["name"])]
    out["near_or_at_limit_up"] = out["pct_change"] >= (out["limit_pct_rule"] - 0.30)
    out["strict_tradeable"] = (
        (~out["is_st_or_delist"])
        & (~out["near_or_at_limit_up"])
        & (pd.to_numeric(out["limit_up_like"], errors="coerce").fillna(0) <= 0.5)
        & (pd.to_numeric(out["rt_turnover"], errors="coerce").fillna(0) >= 3.0)
        & (pd.to_numeric(out["rt_amount"], errors="coerce").fillna(0) >= 200_000_000.0)
        & out["symbol"].map(_is_main_board_symbol)
    )
    out["high_conf"] = out["probability"] >= 0.75
    out["official_candidate"] = False
    if not gap_stats["selected_tushare_missing_or_unavailable"]:
        out["official_candidate"] = out["strict_tradeable"] & out["high_conf"]
    out["diagnostic_candidate"] = out["strict_tradeable"] & out["high_conf"]

    columns = [
        "symbol", "name", "probability", "close", "pct_change", "rt_turnover",
        "rt_amount", "range_pct", "short_phase_days_3", "limit_up_like",
        "is_st_or_delist", "near_or_at_limit_up", "strict_tradeable",
        "high_conf", "official_candidate", "diagnostic_candidate",
    ]
    out = out.sort_values(["probability", "rt_turnover"], ascending=[False, False]).reset_index(drop=True)
    out[columns].to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    audit = {
        "target_date": str(TARGET_DATE),
        "bundle": str(BUNDLE_PATH),
        "bundle_threshold": bundle["threshold"],
        "bundle_selected_count": len(bundle["selected_feature_names"]),
        "model_train_end": "2025-12-31",
        "universe_main_board_symbols": len(symbols),
        "snapshot_rows": int(len(snapshot)),
        "daily_bars_loaded": int(len(bars)),
        "today_bars_injected": int(len(bars_today)),
        "short_only_rows": int(len(data)),
        "scored_rows": int(len(out)),
        "above_bundle_threshold": int((out["probability"] >= bundle["threshold"]).sum()),
        "above_0_75": int((out["probability"] >= 0.75).sum()),
        "strict_tradeable": int(out["strict_tradeable"].sum()),
        "diagnostic_candidates": int(out["diagnostic_candidate"].sum()),
        "official_candidates": int(out["official_candidate"].sum()),
        "factor_reports": factor_reports,
        "gap_stats": gap_stats,
        "warning": (
            "No official candidates if selected Tushare features are unavailable for target date. "
            "Diagnostic candidates are filtered but not formally valid."
        ),
        "elapsed_sec": round(time.perf_counter() - t_start, 3),
    }
    AUDIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print("\nTop diagnostic candidates:")
    print(out[out["diagnostic_candidate"]][columns].head(30).to_string(index=False))
    print(f"\nWrote {OUTPUT_CSV}")
    print(f"Wrote {AUDIT_JSON}")


if __name__ == "__main__":
    main()

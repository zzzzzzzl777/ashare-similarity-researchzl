"""Search PhaseC selection rules for next-day high-minus-2 exits.

The objective here is different from tp10.  For each selected candidate the
assumed realized return is next_high_return_pct minus two percentage points,
with a capped-high variant to avoid corporate-action outliers.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
OUT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
SOURCE = OUT_DIR / "phasec_surge_analysis_20260520_scored_candidates.parquet"
RUN_TAG = "phasec_high_minus2_rule_search_20260520"


PERIODS = {
    "stress_2017_2022": ("2017-01-01", "2022-12-31", 100),
    "dev_2023_2025": ("2023-01-01", "2025-12-31", 80),
    "q1_2026": ("2026-01-01", "2026-03-31", 10),
    "apr_2026": ("2026-04-01", "2026-04-30", 3),
    "may_2026_partial": ("2026-05-01", "2026-05-31", 1),
    "all": ("2017-01-01", "2026-05-31", 150),
}


BASE_COLS = [
    "date",
    "symbol",
    "name",
    "raw_prob",
    "iso_prob",
    "surge5_score",
    "limit10_score",
    "pred_high_pct",
    "surge_combo_score",
    "next_high_return_pct",
    "next_close_return_pct",
    "next_low_return_pct",
    "close",
    "turnover",
    "turnover_z_20",
    "volume_z_20",
    "amount_z_20",
    "range_pct",
    "rsi_6",
    "rsi_14",
    "gap_pct",
    "ma_gap_5",
    "ma_gap_20",
    "atr_14_pct",
    "cs_amount_z_rank",
    "cs_volume_z_rank",
    "cs_turnover_rank",
    "cs_range_rank",
    "cs_market_mean_range",
    "close_position",
]


def num(df: pd.DataFrame, col: str, default: float = 0.0) -> np.ndarray:
    if col not in df.columns:
        return np.full(len(df), default, dtype=np.float64)
    return pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(default).to_numpy(dtype=np.float64)


def make_masks(df: pd.DataFrame) -> list[tuple[str, np.ndarray]]:
    raw = num(df, "raw_prob", -1.0)
    iso = num(df, "iso_prob", -1.0)
    az = num(df, "amount_z_20")
    vz = num(df, "volume_z_20")
    tz = num(df, "turnover_z_20")
    turnover = num(df, "turnover")
    close = num(df, "close")
    rsi6 = num(df, "rsi_6", 50.0)
    rng = num(df, "range_pct")
    gap = num(df, "gap_pct")
    atr = num(df, "atr_14_pct")
    csr = num(df, "cs_range_rank")
    csa = num(df, "cs_amount_z_rank")
    cst = num(df, "cs_turnover_rank")
    market_range = num(df, "cs_market_mean_range")

    bases: list[tuple[str, np.ndarray]] = []
    # Keep the search broad enough to compare realistic PhaseC candidate pools,
    # but avoid a blind combinatorial explosion.  These thresholds cover the
    # practical region discussed for live use.
    for thr in [0.70, 0.72, 0.73, 0.75, 0.78, 0.80, 0.82]:
        bases.append((f"raw>={thr:.2f}", raw >= thr))
        bases.append((f"iso>={thr:.2f}", iso >= thr))
        bases.append((f"raw_or_iso>={thr:.2f}", (raw >= thr) | (iso >= thr)))

    refiners: list[tuple[str, np.ndarray]] = [
        ("none", np.ones(len(df), dtype=bool)),
        ("amount_z>=0", az >= 0),
        ("amount_z>=0.5", az >= 0.5),
        ("amount_z>=1", az >= 1),
        ("volume_z>=0", vz >= 0),
        ("volume_z>=0.5", vz >= 0.5),
        ("turnover_z>=0", tz >= 0),
        ("turnover>=3", turnover >= 3),
        ("turnover>=5", turnover >= 5),
        ("turnover_5_30", (turnover >= 5) & (turnover <= 30)),
        ("turnover_8_35", (turnover >= 8) & (turnover <= 35)),
        ("close_3_80", (close >= 3) & (close <= 80)),
        ("close_5_60", (close >= 5) & (close <= 60)),
        ("rsi6<=45", rsi6 <= 45),
        ("rsi6<=55", rsi6 <= 55),
        ("rsi6_35_65", (rsi6 >= 35) & (rsi6 <= 65)),
        ("range>=3", rng >= 3),
        ("range_2_10", (rng >= 2) & (rng <= 10)),
        ("gap<=3", gap <= 3),
        ("gap_-5_5", (gap >= -5) & (gap <= 5)),
        ("atr>=3", atr >= 3),
        ("cs_range_top50", csr >= 0.5),
        ("cs_amount_top50", csa >= 0.5),
        ("cs_turnover_top50", cst >= 0.5),
        ("market_range>=2", market_range >= 2),
    ]

    masks: list[tuple[str, np.ndarray]] = []
    seen = set()
    for bname, bmask in bases:
        for r1_name, r1_mask in refiners:
            name = bname if r1_name == "none" else f"{bname}|{r1_name}"
            mask = bmask & r1_mask
            if name not in seen:
                masks.append((name, mask))
                seen.add(name)
        compact_refiners = [r for r in refiners if r[0] in {"amount_z>=0", "volume_z>=0", "turnover>=5", "rsi6<=55", "close_5_60", "range_2_10"}]
        for r1_name, r1_mask in compact_refiners:
            for r2_name, r2_mask in compact_refiners:
                if r1_name >= r2_name:
                    continue
                name = f"{bname}|{r1_name}|{r2_name}"
                if name in seen:
                    continue
                masks.append((name, bmask & r1_mask & r2_mask))
                seen.add(name)
    return masks


def add_rank_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    raw = num(out, "raw_prob", -1.0)
    iso = num(out, "iso_prob", -1.0)
    surge5 = num(out, "surge5_score", -1.0)
    limit10 = num(out, "limit10_score", -1.0)
    pred_high = num(out, "pred_high_pct", 0.0)
    combo = num(out, "surge_combo_score", -1.0)
    az = num(out, "amount_z_20")
    vz = num(out, "volume_z_20")
    rsi6 = num(out, "rsi_6", 50.0)
    turnover = num(out, "turnover")
    rng = num(out, "range_pct")

    out["rank_raw"] = raw
    out["rank_iso"] = iso
    out["rank_surge5"] = surge5
    out["rank_limit10"] = limit10
    out["rank_pred_high"] = pred_high
    out["rank_combo"] = combo
    out["rank_raw_then_rsi_low"] = raw * 10_000 - rsi6
    out["rank_iso_then_rsi_low"] = iso * 10_000 - rsi6
    out["rank_raw_amount"] = raw * 10_000 + az
    out["rank_raw_volume"] = raw * 10_000 + vz
    out["rank_surge_limit"] = surge5 * 10_000 + limit10
    out["rank_high_amount"] = pred_high * 1_000 + az
    out["rank_hot_liquid"] = raw * 10_000 + np.clip(az, 0, None) + np.clip(vz, 0, None) + turnover / 10.0
    out["rank_volatility_break"] = raw * 10_000 + rng + np.clip(az, 0, None)
    return out


def evaluate(sel: pd.DataFrame, cap_high: float = 20.0) -> dict | None:
    if sel.empty:
        return None
    high = pd.to_numeric(sel["next_high_return_pct"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    high = high.clip(lower=-30, upper=cap_high)
    realized = high - 2.0
    tmp = sel.copy()
    tmp["realized_high_minus2"] = realized
    tmp = tmp.dropna(subset=["realized_high_minus2"])
    if tmp.empty:
        return None
    daily = tmp.groupby("date_key")["realized_high_minus2"].mean().sort_index()
    if daily.empty:
        return None
    comp = float((np.prod(1.0 + daily.to_numpy(dtype=np.float64) / 100.0) - 1.0) * 100.0)
    high_ret = pd.to_numeric(tmp["next_high_return_pct"], errors="coerce")
    return {
        "signal_days": int(daily.shape[0]),
        "tickets": int(tmp.shape[0]),
        "total_return_pct": round(comp, 2),
        "avg_daily_return_pct": round(float(daily.mean()), 3),
        "daily_win_rate": round(float((daily > 0).mean()), 4),
        "ticket_win_rate": round(float((tmp["realized_high_minus2"] > 0).mean()), 4),
        "high1_rate": round(float((high_ret >= 1).mean()), 4),
        "high3_rate": round(float((high_ret >= 3).mean()), 4),
        "high5_rate": round(float((high_ret >= 5).mean()), 4),
        "high8_rate": round(float((high_ret >= 8).mean()), 4),
        "limit10_rate": round(float((high_ret >= 10).mean()), 4),
        "max_daily_loss_pct": round(float(daily.min()), 2),
        "max_daily_gain_pct": round(float(daily.max()), 2),
        "sharpe": None if daily.std(ddof=0) == 0 else round(float(daily.mean() / daily.std(ddof=0) * math.sqrt(252)), 2),
    }


def period_slice(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    d = df["date"]
    return df[(d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))]


def search(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rank_cols = [
        "rank_raw",
        "rank_iso",
        "rank_surge5",
        "rank_limit10",
        "rank_pred_high",
        "rank_combo",
        "rank_raw_then_rsi_low",
        "rank_iso_then_rsi_low",
        "rank_raw_amount",
        "rank_raw_volume",
        "rank_surge_limit",
        "rank_high_amount",
        "rank_hot_liquid",
        "rank_volatility_break",
    ]
    top_ns = [1, 2, 3, 4, 5, 6]
    masks = make_masks(df)
    sorted_by_rank: dict[str, pd.DataFrame] = {}
    for rank_col in rank_cols:
        if rank_col not in df.columns:
            continue
        sorted_by_rank[rank_col] = df.sort_values(
            ["date_key", rank_col, "rank_raw", "symbol"],
            ascending=[True, False, False, True],
            kind="mergesort",
        )
    rows = []
    t0 = time.time()
    for idx, (mask_name, mask) in enumerate(masks, 1):
        if int(mask.sum()) < 50:
            continue
        for rank_col, sorted_df in sorted_by_rank.items():
            ranked = sorted_df[mask[sorted_df.index.to_numpy()]].copy()
            if ranked.empty:
                continue
            ranked["daily_rank"] = ranked.groupby("date_key", sort=False).cumcount() + 1
            ranked = ranked[ranked["daily_rank"] <= max(top_ns)]
            for top_n in top_ns:
                row = {
                    "mask": mask_name,
                    "rank_col": rank_col,
                    "top_n": top_n,
                }
                ok = True
                for pname, (start, end, min_days) in PERIODS.items():
                    sel = period_slice(ranked[ranked["daily_rank"] <= top_n], start, end)
                    ev20 = evaluate(sel, cap_high=20.0)
                    ev10 = evaluate(sel, cap_high=10.0)
                    if ev20 is None or ev20["signal_days"] < min_days:
                        ok = False
                        break
                    row[pname] = ev20
                    if pname in {"all", "q1_2026", "apr_2026", "may_2026_partial"}:
                        row[f"{pname}_cap10"] = ev10
                if not ok:
                    continue
                stress = row["stress_2017_2022"]
                dev = row["dev_2023_2025"]
                q1 = row["q1_2026"]
                apr = row["apr_2026"]
                may = row["may_2026_partial"]
                row["robust_score"] = round(
                    min(stress["avg_daily_return_pct"], dev["avg_daily_return_pct"], q1["avg_daily_return_pct"], apr["avg_daily_return_pct"]) * 40
                    + min(stress["daily_win_rate"], dev["daily_win_rate"], q1["daily_win_rate"], apr["daily_win_rate"]) * 100
                    + min(stress["high5_rate"], dev["high5_rate"], q1["high5_rate"], apr["high5_rate"]) * 80
                    + math.log1p(max(row["all"]["total_return_pct"], 0)) * 12
                    + min(may["avg_daily_return_pct"], 2.0) * 5,
                    4,
                )
                row["current_score"] = round(q1["avg_daily_return_pct"] * 30 + apr["avg_daily_return_pct"] * 30 + may["avg_daily_return_pct"] * 10 + q1["high5_rate"] * 60 + apr["high5_rate"] * 60, 4)
                rows.append(row)
        if idx % 100 == 0:
            print(f"masks {idx}/{len(masks)} rows={len(rows)} elapsed={time.time()-t0:.0f}s", flush=True)
    res = pd.DataFrame(rows)
    if not res.empty:
        res = res.sort_values(["robust_score", "current_score"], ascending=[False, False])
    return res, {"mask_count": len(masks), "rank_cols": rank_cols, "top_ns": top_ns}


def main() -> None:
    t0 = time.time()
    print(f"Loading {SOURCE}", flush=True)
    available_cols = set(pq.read_schema(SOURCE).names)
    read_cols = [c for c in BASE_COLS if c in available_cols]
    missing_cols = sorted(set(BASE_COLS) - set(read_cols))
    if missing_cols:
        print(f"Optional columns missing and skipped: {missing_cols}", flush=True)
    df = pd.read_parquet(SOURCE, columns=read_cols)
    df["date"] = pd.to_datetime(df["date"])
    df["date_key"] = df["date"].dt.strftime("%Y-%m-%d")
    before = len(df)
    df = df.drop_duplicates(["date", "symbol"]).reset_index(drop=True).copy()
    print(f"Rows {before:,} -> {len(df):,}; days={df['date_key'].nunique():,}", flush=True)
    df = add_rank_columns(df)
    res, meta = search(df)
    if res.empty:
        raise SystemExit("No rules found")
    out_csv = OUT_DIR / f"{RUN_TAG}_top_rules.csv"
    out_json = OUT_DIR / f"{RUN_TAG}.json"
    top = res.head(300)
    top.to_csv(out_csv, index=False, encoding="utf-8-sig")
    payload = {
        "run_tag": RUN_TAG,
        "source": str(SOURCE),
        "generated_at": pd.Timestamp.now().isoformat(),
        "objective": "select PhaseC candidates for next-day high return; realized return = min(next_high_return_pct, 20) - 2",
        "meta": meta,
        "best_robust": res.iloc[0].to_dict(),
        "best_current": res.sort_values(["current_score", "robust_score"], ascending=[False, False]).iloc[0].to_dict(),
        "top_rules_csv": str(out_csv),
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("BEST_ROBUST", json.dumps(payload["best_robust"], ensure_ascii=False, default=str)[:4000], flush=True)
    print(f"Wrote {out_json}", flush=True)
    print(f"Wrote {out_csv}", flush=True)
    print(f"Done in {(time.time()-t0)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()

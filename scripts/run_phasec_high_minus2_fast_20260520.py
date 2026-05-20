"""Fast PhaseC rule search for next-day high-minus-2 exits.

Goal:
    Find a practical rule that selects PhaseC candidates most likely to surge
    next day.  Backtest return assumes the user can sell two percentage points
    below the next-day intraday high:

        realized = min(next_high_return_pct, cap) - 2

The cap-20 result is the primary research number; cap-10 is also reported as a
more conservative sanity view.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


OUT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
SOURCE = OUT_DIR / "phasec_surge_analysis_20260520_scored_candidates.parquet"
RUN_TAG = "phasec_high_minus2_fast_20260520"

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
    "raw_prob",
    "iso_prob",
    "surge5_score",
    "limit10_score",
    "pred_high_pct",
    "surge_combo_score",
    "next_high_return_pct",
    "next_close_return_pct",
    "close",
    "turnover",
    "turnover_z_20",
    "volume_z_20",
    "amount_z_20",
    "range_pct",
    "rsi_6",
    "gap_pct",
    "ma_gap_5",
    "atr_14_pct",
    "cs_amount_z_rank",
    "cs_volume_z_rank",
    "cs_turnover_rank",
    "cs_range_rank",
    "cs_market_mean_range",
    "close_position",
]


def n(df: pd.DataFrame, col: str, default: float = 0.0) -> np.ndarray:
    if col not in df.columns:
        return np.full(len(df), default, dtype=np.float64)
    return pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(default).to_numpy(dtype=np.float64)


def add_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    raw = n(out, "raw_prob", -1)
    iso = n(out, "iso_prob", -1)
    surge5 = n(out, "surge5_score", -1)
    limit10 = n(out, "limit10_score", -1)
    pred_high = n(out, "pred_high_pct", 0)
    combo = n(out, "surge_combo_score", -1)
    az = n(out, "amount_z_20")
    vz = n(out, "volume_z_20")
    rsi6 = n(out, "rsi_6", 50)
    turnover = n(out, "turnover")
    rng = n(out, "range_pct")
    close_pos = n(out, "close_position", 0.5)

    out["rank_raw"] = raw
    out["rank_iso"] = iso
    out["rank_surge5"] = surge5
    out["rank_limit10"] = limit10
    out["rank_pred_high"] = pred_high
    out["rank_combo"] = combo
    out["rank_raw_then_rsi_low"] = raw * 10000 - rsi6
    out["rank_iso_then_rsi_low"] = iso * 10000 - rsi6
    out["rank_raw_amount"] = raw * 10000 + az
    out["rank_raw_volume"] = raw * 10000 + vz
    out["rank_surge_limit"] = surge5 * 10000 + limit10
    out["rank_high_amount"] = pred_high * 1000 + az
    out["rank_hot_liquid"] = raw * 10000 + np.clip(az, 0, None) + np.clip(vz, 0, None) + turnover / 10
    out["rank_reversal_hot"] = raw * 10000 - rsi6 + np.clip(az, 0, None) + rng + close_pos
    return out


def build_masks(df: pd.DataFrame) -> list[tuple[str, np.ndarray]]:
    raw = n(df, "raw_prob", -1)
    iso = n(df, "iso_prob", -1)
    az = n(df, "amount_z_20")
    vz = n(df, "volume_z_20")
    tz = n(df, "turnover_z_20")
    turnover = n(df, "turnover")
    close = n(df, "close")
    rsi6 = n(df, "rsi_6", 50)
    rng = n(df, "range_pct")
    gap = n(df, "gap_pct")
    atr = n(df, "atr_14_pct")
    csa = n(df, "cs_amount_z_rank")
    csv = n(df, "cs_volume_z_rank")
    cst = n(df, "cs_turnover_rank")
    csr = n(df, "cs_range_rank")
    cp = n(df, "close_position", 0.5)
    market_range = n(df, "cs_market_mean_range")

    bases: list[tuple[str, np.ndarray]] = []
    for thr in [0.70, 0.72, 0.73, 0.75, 0.78, 0.80]:
        bases.extend(
            [
                (f"raw>={thr:.2f}", raw >= thr),
                (f"iso>={thr:.2f}", iso >= thr),
                (f"raw_or_iso>={thr:.2f}", (raw >= thr) | (iso >= thr)),
                (f"raw_and_iso>={thr:.2f}", (raw >= thr) & (iso >= thr)),
            ]
        )

    filters: list[tuple[str, np.ndarray]] = [
        ("none", np.ones(len(df), dtype=bool)),
        ("amount_z>=0", az >= 0),
        ("amount_z>=0.5", az >= 0.5),
        ("amount_z>=1", az >= 1),
        ("volume_z>=0", vz >= 0),
        ("volume_z>=0.5", vz >= 0.5),
        ("amount_z>=0&volume_z>=0", (az >= 0) & (vz >= 0)),
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
        ("gap_-5_5", (gap >= -5) & (gap <= 5)),
        ("atr>=3", atr >= 3),
        ("cs_amount_top50", csa >= 0.5),
        ("cs_volume_top50", csv >= 0.5),
        ("cs_turnover_top50", cst >= 0.5),
        ("cs_range_top50", csr >= 0.5),
        ("close_position>=0.5", cp >= 0.5),
        ("market_range>=2", market_range >= 2),
        ("hot_liquid", (az >= 0) & (vz >= 0) & (turnover >= 5)),
        ("reversal_liquid", (rsi6 <= 55) & (az >= 0) & (turnover >= 3)),
        ("breakout_liquid", (rng >= 3) & (az >= 0) & (turnover >= 3)),
        ("compact_price_liquid", (close >= 5) & (close <= 60) & (turnover >= 5)),
    ]

    masks: list[tuple[str, np.ndarray]] = []
    for bname, bmask in bases:
        for fname, fmask in filters:
            name = bname if fname == "none" else f"{bname}|{fname}"
            masks.append((name, bmask & fmask))
    return masks


def metrics_for_indices(df: pd.DataFrame, idx: np.ndarray, cap_high: float, start: str, end: str) -> dict | None:
    if idx.size == 0:
        return None
    sub = df.iloc[idx]
    sub = sub[(sub["date"] >= pd.Timestamp(start)) & (sub["date"] <= pd.Timestamp(end))]
    if sub.empty:
        return None
    high = pd.to_numeric(sub["next_high_return_pct"], errors="coerce").clip(lower=-30, upper=cap_high)
    tmp = pd.DataFrame({"date_key": sub["date_key"].to_numpy(), "realized": high.to_numpy() - 2.0, "high": high.to_numpy()})
    tmp = tmp.dropna()
    if tmp.empty:
        return None
    daily = tmp.groupby("date_key")["realized"].mean().sort_index()
    if daily.empty:
        return None
    comp = float((np.prod(1 + daily.to_numpy() / 100.0) - 1) * 100)
    return {
        "signal_days": int(daily.shape[0]),
        "tickets": int(tmp.shape[0]),
        "total_return_pct": round(comp, 2),
        "avg_daily_return_pct": round(float(daily.mean()), 3),
        "daily_win_rate": round(float((daily > 0).mean()), 4),
        "ticket_win_rate": round(float((tmp["realized"] > 0).mean()), 4),
        "high3_rate": round(float((tmp["high"] >= 3).mean()), 4),
        "high5_rate": round(float((tmp["high"] >= 5).mean()), 4),
        "high8_rate": round(float((tmp["high"] >= 8).mean()), 4),
        "limit10_rate": round(float((tmp["high"] >= 10).mean()), 4),
        "max_daily_loss_pct": round(float(daily.min()), 2),
        "max_daily_gain_pct": round(float(daily.max()), 2),
        "sharpe": None if daily.std(ddof=0) == 0 else round(float(daily.mean() / daily.std(ddof=0) * math.sqrt(252)), 2),
    }


def search(df: pd.DataFrame) -> pd.DataFrame:
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
        "rank_reversal_hot",
    ]
    top_ns = [1, 2, 3, 4, 5, 6]
    masks = [(name, mask) for name, mask in build_masks(df) if int(mask.sum()) >= 50]
    date_groups = {k: g.index.to_numpy() for k, g in df.groupby("date_key", sort=True)}

    sorted_groups: dict[str, list[np.ndarray]] = {}
    symbols = df["symbol"].astype(str).to_numpy()
    for rank_col in rank_cols:
        score = pd.to_numeric(df[rank_col], errors="coerce").fillna(-1e18).to_numpy()
        groups: list[np.ndarray] = []
        for idx in date_groups.values():
            # lexsort uses last key as primary: score descending, then symbol ascending.
            order = np.lexsort((symbols[idx], -score[idx]))
            groups.append(idx[order])
        sorted_groups[rank_col] = groups

    rows = []
    t0 = time.time()
    total = len(masks) * len(rank_cols)
    done = 0
    for mask_name, mask in masks:
        for rank_col, groups in sorted_groups.items():
            done += 1
            selected_by_top = {n: [] for n in top_ns}
            for idx in groups:
                hit = idx[mask[idx]]
                if hit.size == 0:
                    continue
                hit = hit[: max(top_ns)]
                for top_n in top_ns:
                    if hit.size >= top_n:
                        selected_by_top[top_n].append(hit[:top_n])
                    else:
                        selected_by_top[top_n].append(hit)
            for top_n, chunks in selected_by_top.items():
                if not chunks:
                    continue
                selected = np.concatenate(chunks)
                row = {"mask": mask_name, "rank_col": rank_col, "top_n": top_n}
                ok = True
                for pname, (start, end, min_days) in PERIODS.items():
                    ev20 = metrics_for_indices(df, selected, 20.0, start, end)
                    if ev20 is None or ev20["signal_days"] < min_days:
                        ok = False
                        break
                    row[pname] = ev20
                    if pname in {"all", "q1_2026", "apr_2026", "may_2026_partial"}:
                        row[f"{pname}_cap10"] = metrics_for_indices(df, selected, 10.0, start, end)
                if not ok:
                    continue
                stress = row["stress_2017_2022"]
                dev = row["dev_2023_2025"]
                q1 = row["q1_2026"]
                apr = row["apr_2026"]
                may = row["may_2026_partial"]
                row["robust_score"] = round(
                    min(stress["avg_daily_return_pct"], dev["avg_daily_return_pct"], q1["avg_daily_return_pct"], apr["avg_daily_return_pct"]) * 45
                    + min(stress["daily_win_rate"], dev["daily_win_rate"], q1["daily_win_rate"], apr["daily_win_rate"]) * 100
                    + min(stress["high5_rate"], dev["high5_rate"], q1["high5_rate"], apr["high5_rate"]) * 90
                    + min(stress["limit10_rate"], dev["limit10_rate"], q1["limit10_rate"], apr["limit10_rate"]) * 80
                    + math.log1p(max(row["all"]["total_return_pct"], 0)) * 10
                    + min(may["avg_daily_return_pct"], 2.0) * 5,
                    4,
                )
                row["current_score"] = round(
                    q1["avg_daily_return_pct"] * 25
                    + apr["avg_daily_return_pct"] * 35
                    + may["avg_daily_return_pct"] * 10
                    + q1["high5_rate"] * 60
                    + apr["high5_rate"] * 80
                    + apr["limit10_rate"] * 70,
                    4,
                )
                rows.append(row)
            if done % 200 == 0:
                print(f"checked {done}/{total}, rows={len(rows)}, elapsed={time.time()-t0:.0f}s", flush=True)

    res = pd.DataFrame(rows)
    if not res.empty:
        res = res.sort_values(["robust_score", "current_score"], ascending=[False, False])
    return res


def monthly_for_rule(df: pd.DataFrame, rule: dict, cap_high: float = 20.0) -> pd.DataFrame:
    masks = dict(build_masks(df))
    mask = masks[rule["mask"]]
    score = pd.to_numeric(df[rule["rank_col"]], errors="coerce").fillna(-1e18)
    ranked = df.loc[mask].copy()
    ranked["_score"] = score.loc[ranked.index]
    ranked = ranked.sort_values(["date_key", "_score", "rank_raw", "symbol"], ascending=[True, False, False, True])
    ranked["daily_rank"] = ranked.groupby("date_key").cumcount() + 1
    sel = ranked[ranked["daily_rank"] <= int(rule["top_n"])].copy()
    high = pd.to_numeric(sel["next_high_return_pct"], errors="coerce").clip(lower=-30, upper=cap_high)
    sel["realized"] = high - 2.0
    sel["month"] = sel["date"].dt.strftime("%Y-%m")
    daily = sel.groupby(["month", "date_key"])["realized"].mean().reset_index()
    rows = []
    for month, part in daily.groupby("month"):
        vals = part["realized"].to_numpy()
        rows.append(
            {
                "month": month,
                "signal_days": int(len(vals)),
                "total_return_pct": round(float((np.prod(1 + vals / 100.0) - 1) * 100), 2),
                "avg_daily_return_pct": round(float(np.mean(vals)), 3),
                "daily_win_rate": round(float(np.mean(vals > 0)), 4),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    t0 = time.time()
    available = set(pq.read_schema(SOURCE).names)
    read_cols = [c for c in BASE_COLS if c in available]
    print(f"Loading {SOURCE}", flush=True)
    df = pd.read_parquet(SOURCE, columns=read_cols)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(["date", "symbol"]).reset_index(drop=True)
    df["date_key"] = df["date"].dt.strftime("%Y-%m-%d")
    df = add_scores(df)
    print(f"Rows={len(df):,}, days={df['date_key'].nunique():,}", flush=True)
    res = search(df)
    if res.empty:
        raise SystemExit("No rules found")
    best_robust = res.iloc[0].to_dict()
    best_current = res.sort_values(["current_score", "robust_score"], ascending=[False, False]).iloc[0].to_dict()
    out_csv = OUT_DIR / f"{RUN_TAG}_top_rules.csv"
    out_json = OUT_DIR / f"{RUN_TAG}.json"
    res.head(300).to_csv(out_csv, index=False, encoding="utf-8-sig")
    monthly_robust = monthly_for_rule(df, best_robust)
    monthly_current = monthly_for_rule(df, best_current)
    payload = {
        "run_tag": RUN_TAG,
        "source": str(SOURCE),
        "generated_at": pd.Timestamp.now().isoformat(),
        "objective": "PhaseC candidate selection for next-day surge; realized = min(next_high_return_pct, 20) - 2",
        "best_robust": best_robust,
        "best_current": best_current,
        "monthly_best_robust": monthly_robust.to_dict("records"),
        "monthly_best_current": monthly_current.to_dict("records"),
        "top_rules_csv": str(out_csv),
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("BEST_ROBUST", json.dumps(best_robust, ensure_ascii=False, default=str)[:5000], flush=True)
    print("BEST_CURRENT", json.dumps(best_current, ensure_ascii=False, default=str)[:5000], flush=True)
    print(f"Wrote {out_json}", flush=True)
    print(f"Wrote {out_csv}", flush=True)
    print(f"Done in {(time.time()-t0)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()

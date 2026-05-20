"""PhaseC live-safe surge scorer and strategy optimizer.

This runner starts from the already scored PhaseC candidate pool and adds a
second-stage surge model that uses only 14:57-engineerable columns.  It is meant
to absorb the useful "surge score" idea without reintroducing post-close or hard
moneyflow leakage.

Key design choices:
- Candidate model is frozen PhaseC; this script does not retrain PhaseC.
- The second-stage scorer is trained with rolling out-of-sample predictions for
  2021-2025 so strategy selection does not use in-sample scorer output.
- 2026 Q1 / April / May are forward reports only. They are not used to train the
  surge scorer.
- Intraday high/low based exits are marked idealized; minute-order replay is
  still required before live execution of stop/take-profit rules.
"""

from __future__ import annotations

import json
import math
import pickle
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from lightgbm import LGBMClassifier, LGBMRegressor
except Exception as exc:  # pragma: no cover
    raise RuntimeError("lightgbm is required") from exc


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
OUT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
DOC_DIR = ROOT / "docs"
RUN_TAG = "phasec_live_safe_surge_optimizer_20260520"
INPUT_SCORED = OUT_DIR / "phasec_surge_analysis_20260520_scored_candidates.parquet"

FORBIDDEN_PATTERNS = [
    "tushare_net_mf",
    "tushare_mf_",
    "tushare_ff_adjusted_flow",
    "minute_last_30min",
    "minute_vwap",
    "tushare_last_30min",
    "tushare_vwap",
    "tushare_close_vs_vwap",
    "auction_close",
    "close_auction",
    "post_close",
    "postclose",
]

META_AND_TARGET_COLS = {
    "date",
    "label_date",
    "date_key",
    "month",
    "symbol",
    "name",
    "actual",
    "next_high_return_pct",
    "next_close_return_pct",
    "next_low_return_pct",
    "source_cache",
    "surge5_score",
    "limit10_score",
    "pred_high_pct",
    "surge_combo_score",
    "safe_surge5_score",
    "safe_limit10_score",
    "safe_pred_high_pct",
    "safe_combo_score",
    "score_source",
}

PERIODS = [
    ("stress_oof_2021_2022", "2021-01-01", "2022-12-31"),
    ("dev_oof_2023_2025", "2023-01-01", "2025-12-31"),
    ("q1_2026_forward", "2026-01-01", "2026-03-31"),
    ("apr_2026_forward", "2026-04-01", "2026-04-30"),
    ("may_2026_partial", "2026-05-01", "2026-05-31"),
]

EXIT_MODES = [
    "close",
    "tp3",
    "tp5",
    "tp7",
    "tp10",
    "sl1_tp5",
    "sl2_tp5",
    "sl2_tp7",
    "sl3_tp10",
]

TOP_NS = [1, 2, 3, 4, 5, 6]


@dataclass(frozen=True)
class Rule:
    mask_name: str
    rank_col: str
    top_n: int
    exit_mode: str


def is_forbidden(name: str) -> bool:
    low = name.lower()
    return any(p in low for p in FORBIDDEN_PATTERNS)


def safe_num(df: pd.DataFrame, col: str, fill: float = 0.0) -> np.ndarray:
    if col not in df.columns:
        return np.full(len(df), fill, dtype=np.float64)
    return (
        pd.to_numeric(df[col], errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .fillna(fill)
        .to_numpy(dtype=np.float64)
    )


def pct_prod(returns_pct: np.ndarray) -> float:
    if len(returns_pct) == 0:
        return 0.0
    clipped = np.clip(np.asarray(returns_pct, dtype=np.float64) / 100.0, -0.95, 10.0)
    return float((np.prod(1.0 + clipped) - 1.0) * 100.0)


def period_mask(df: pd.DataFrame, start: str, end: str) -> np.ndarray:
    d = pd.to_datetime(df["date"])
    return ((d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))).to_numpy()


def choose_live_safe_features(df: pd.DataFrame) -> list[str]:
    numeric_cols = []
    for col in df.columns:
        if col in META_AND_TARGET_COLS or is_forbidden(col):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            vals = pd.to_numeric(df[col], errors="coerce")
            if vals.notna().mean() >= 0.70 and vals.nunique(dropna=True) >= 5:
                numeric_cols.append(col)

    # Ensure first-stage probabilities are always present.
    for col in ["raw_prob", "iso_prob"]:
        if col in df.columns and col not in numeric_cols:
            numeric_cols.insert(0, col)
    return numeric_cols


def load_pool() -> pd.DataFrame:
    if not INPUT_SCORED.exists():
        raise FileNotFoundError(INPUT_SCORED)
    df = pd.read_parquet(INPUT_SCORED)
    df["date"] = pd.to_datetime(df["date"])
    df["label_date"] = pd.to_datetime(df["label_date"], errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    df["date_key"] = df["date"].dt.strftime("%Y-%m-%d")
    df["month"] = df["date"].dt.strftime("%Y-%m")
    before = len(df)
    df = df.sort_values(["date", "symbol"]).drop_duplicates(["date", "symbol"], keep="last")
    if len(df) != before:
        print(f"Deduplicated scored pool: {before:,} -> {len(df):,}", flush=True)
    for col in ["raw_prob", "iso_prob", "actual", "next_high_return_pct", "next_close_return_pct", "next_low_return_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["raw_prob", "iso_prob", "next_high_return_pct", "next_close_return_pct", "next_low_return_pct"]).copy()
    print(
        f"Loaded pool: {len(df):,} rows, {df['date_key'].nunique():,} days, "
        f"{df['date'].min().date()}..{df['date'].max().date()}",
        flush=True,
    )
    return df.reset_index(drop=True)


def lgb_params(seed: int, target: str) -> dict:
    common = {
        "n_estimators": 360,
        "learning_rate": 0.035,
        "num_leaves": 31,
        "max_depth": -1,
        "min_child_samples": 120,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "reg_lambda": 8.0,
        "random_state": seed,
        "n_jobs": -1,
        "verbose": -1,
    }
    if target == "limit10":
        common.update({"num_leaves": 23, "min_child_samples": 150, "reg_lambda": 10.0})
    return common


def fit_three_heads(
    x_train: pd.DataFrame,
    train_df: pd.DataFrame,
    seed: int,
) -> tuple[LGBMClassifier, LGBMClassifier, LGBMRegressor]:
    y5 = (train_df["next_high_return_pct"].astype(float) >= 5.0).astype(int)
    y10 = (train_df["next_high_return_pct"].astype(float) >= 9.8).astype(int)
    yh = train_df["next_high_return_pct"].astype(float).clip(-20, 20)

    clf5 = LGBMClassifier(**lgb_params(seed, "surge5"), class_weight="balanced")
    clf10 = LGBMClassifier(**lgb_params(seed + 100, "limit10"), class_weight="balanced")
    reg = LGBMRegressor(**lgb_params(seed + 200, "reg"))

    clf5.fit(x_train, y5)
    clf10.fit(x_train, y10)
    reg.fit(x_train, yh)
    return clf5, clf10, reg


def add_score_columns(
    df: pd.DataFrame,
    x: pd.DataFrame,
    models: tuple[LGBMClassifier, LGBMClassifier, LGBMRegressor],
    idx: np.ndarray,
) -> None:
    clf5, clf10, reg = models
    pred5 = clf5.predict_proba(x.loc[idx])[:, 1]
    pred10 = clf10.predict_proba(x.loc[idx])[:, 1]
    pred_high = np.clip(reg.predict(x.loc[idx]), -5, 12)
    scaled_high = np.clip((pred_high + 2.0) / 14.0, 0.0, 1.0)
    df.loc[idx, "safe_surge5_score"] = pred5
    df.loc[idx, "safe_limit10_score"] = pred10
    df.loc[idx, "safe_pred_high_pct"] = pred_high
    df.loc[idx, "safe_combo_score"] = (
        0.40 * df.loc[idx, "raw_prob"].to_numpy(dtype=float)
        + 0.25 * df.loc[idx, "iso_prob"].to_numpy(dtype=float)
        + 0.20 * pred5
        + 0.10 * pred10
        + 0.05 * scaled_high
    )


def train_rolling_scorer(df: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    for col in ["safe_surge5_score", "safe_limit10_score", "safe_pred_high_pct", "safe_combo_score"]:
        df[col] = np.nan
    df["score_source"] = "unscored"

    x = df[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32)
    years = [2021, 2022, 2023, 2024, 2025]
    fold_meta = []
    for year in years:
        train_idx = df.index[df["date"] < pd.Timestamp(f"{year}-01-01")].to_numpy()
        valid_idx = df.index[
            (df["date"] >= pd.Timestamp(f"{year}-01-01"))
            & (df["date"] <= pd.Timestamp(f"{year}-12-31"))
        ].to_numpy()
        if len(train_idx) < 20_000 or len(valid_idx) == 0:
            continue
        print(f"Training OOF surge fold {year}: train={len(train_idx):,}, valid={len(valid_idx):,}", flush=True)
        models = fit_three_heads(x.loc[train_idx], df.loc[train_idx], seed=42 + year)
        add_score_columns(df, x, models, valid_idx)
        df.loc[valid_idx, "score_source"] = "oof"
        fold_meta.append({"valid_year": year, "train_rows": int(len(train_idx)), "valid_rows": int(len(valid_idx))})

    final_train_idx = df.index[df["date"] <= pd.Timestamp("2025-12-31")].to_numpy()
    forward_idx = df.index[df["date"] >= pd.Timestamp("2026-01-01")].to_numpy()
    print(f"Training final surge scorer for 2026: train={len(final_train_idx):,}, forward={len(forward_idx):,}", flush=True)
    final_models = fit_three_heads(x.loc[final_train_idx], df.loc[final_train_idx], seed=99)
    if len(forward_idx):
        add_score_columns(df, x, final_models, forward_idx)
        df.loc[forward_idx, "score_source"] = "forward_final"

    model_path = OUT_DIR / f"{RUN_TAG}_surge_models.pkl"
    with model_path.open("wb") as f:
        pickle.dump({"feature_cols": feature_cols, "final_models": final_models, "folds": fold_meta}, f)

    diag = {
        "feature_count": len(feature_cols),
        "feature_cols": feature_cols,
        "folds": fold_meta,
        "model_path": str(model_path),
        "oof_rows": int((df["score_source"] == "oof").sum()),
        "forward_rows": int((df["score_source"] == "forward_final").sum()),
    }
    return df, diag


def build_rule_masks(df: pd.DataFrame, selection_only: pd.DataFrame) -> list[tuple[str, np.ndarray]]:
    raw = safe_num(df, "raw_prob")
    iso = safe_num(df, "iso_prob")
    combo = safe_num(df, "safe_combo_score", np.nan)
    s5 = safe_num(df, "safe_surge5_score", np.nan)
    pred_high = safe_num(df, "safe_pred_high_pct", np.nan)
    turnover = safe_num(df, "turnover")
    close = safe_num(df, "close")
    rsi6 = safe_num(df, "rsi_6", 50.0)
    vol = safe_num(df, "volume_z_20")
    amt = safe_num(df, "amount_z_20")
    rng = safe_num(df, "range_pct")
    cp = safe_num(df, "close_position", 0.5)

    masks: list[tuple[str, np.ndarray]] = []
    base_specs: list[tuple[str, np.ndarray]] = []
    for thr in [0.65, 0.70, 0.72, 0.73, 0.75, 0.78, 0.80]:
        base_specs.append((f"raw>={thr:.2f}", raw >= thr))
        base_specs.append((f"iso>={thr:.2f}", iso >= thr))
    for col, values, label in [
        ("safe_combo_score", combo, "combo"),
        ("safe_surge5_score", s5, "s5"),
        ("safe_pred_high_pct", pred_high, "predH"),
    ]:
        sel_vals = pd.to_numeric(selection_only[col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(sel_vals) < 100:
            continue
        for q in [0.55, 0.65, 0.75, 0.85, 0.90]:
            val = float(sel_vals.quantile(q))
            base_specs.append((f"{label}_dev_q{int(q*100)}>={val:.3f}", values >= val))

    refiners = [
        ("none", np.ones(len(df), dtype=bool)),
        ("turnover_3_20", (turnover >= 3) & (turnover <= 20)),
        ("turnover_5_30", (turnover >= 5) & (turnover <= 30)),
        ("close_3_80", (close >= 3) & (close <= 80)),
        ("close_5_80", (close >= 5) & (close <= 80)),
        ("volume_z>=0", vol >= 0),
        ("amount_z>=0", amt >= 0),
        ("rsi6<=55", rsi6 <= 55),
        ("rsi6<=45", rsi6 <= 45),
        ("range>=2", rng >= 2),
        ("close_pos>=0.55", cp >= 0.55),
        ("t5_30_vol0", (turnover >= 5) & (turnover <= 30) & (vol >= 0)),
        ("t5_30_amt0", (turnover >= 5) & (turnover <= 30) & (amt >= 0)),
        ("t5_30_rsi55", (turnover >= 5) & (turnover <= 30) & (rsi6 <= 55)),
        ("vol0_rsi55", (vol >= 0) & (rsi6 <= 55)),
        ("amt0_rsi55", (amt >= 0) & (rsi6 <= 55)),
    ]
    for base_name, base_mask in base_specs:
        for ref_name, ref_mask in refiners:
            name = base_name if ref_name == "none" else f"{base_name}|{ref_name}"
            mask = base_mask & ref_mask
            if int(mask.sum()) >= 100:
                masks.append((name, mask))
    return masks


def compute_exit(df: pd.DataFrame, mode: str) -> np.ndarray:
    close_ret = safe_num(df, "next_close_return_pct")
    high_ret = safe_num(df, "next_high_return_pct")
    low_ret = safe_num(df, "next_low_return_pct")
    if mode == "close":
        return close_ret
    if mode.startswith("tp") and "_tp" not in mode:
        tp = float(mode[2:])
        return np.where(high_ret >= tp, tp, close_ret)
    if "_tp" in mode:
        left, right = mode.split("_")
        sl = -float(left[2:])
        tp = float(right[2:])
        sl_hit = low_ret <= sl
        tp_hit = high_ret >= tp
        out = close_ret.copy()
        out[tp_hit & ~sl_hit] = tp
        out[sl_hit] = sl
        return out
    raise ValueError(mode)


def evaluate_selected(sel: pd.DataFrame, top_n: int, exit_mode: str, min_days: int = 5) -> dict | None:
    picked = sel[sel["daily_rank"] <= top_n].copy()
    if picked.empty:
        return None
    returns = compute_exit(picked, exit_mode)
    picked["realized_return_pct"] = returns
    daily = picked.groupby("date_key")["realized_return_pct"].mean().to_numpy(dtype=float)
    if len(daily) < min_days:
        return None
    return {
        "signal_days": int(len(daily)),
        "tickets": int(len(picked)),
        "total_return_pct": round(pct_prod(daily), 2),
        "avg_daily_return_pct": round(float(np.mean(daily)), 3),
        "daily_win_rate": round(float((daily > 0).mean()), 4),
        "ticket_win_rate": round(float((returns > 0).mean()), 4),
        "high1_rate": round(float((picked["next_high_return_pct"] >= 1.0).mean()), 4),
        "high3_rate": round(float((picked["next_high_return_pct"] >= 3.0).mean()), 4),
        "high5_rate": round(float((picked["next_high_return_pct"] >= 5.0).mean()), 4),
        "limit10_rate": round(float((picked["next_high_return_pct"] >= 9.8).mean()), 4),
        "max_daily_loss_pct": round(float(np.min(daily)), 2),
        "max_daily_gain_pct": round(float(np.max(daily)), 2),
        "sharpe": round(float(np.mean(daily) / np.std(daily, ddof=1) * math.sqrt(252)), 2)
        if len(daily) > 2 and np.std(daily, ddof=1) > 0
        else None,
    }


def rank_frame(df: pd.DataFrame, mask: np.ndarray, rank_col: str) -> pd.DataFrame:
    sub = df.loc[mask].copy()
    if sub.empty:
        return sub
    sort_cols = ["date_key", rank_col, "raw_prob", "iso_prob"]
    ascending = [True, False, False, False]
    if rank_col == "score_then_rsi6_low":
        sub["score_then_rsi6_low"] = safe_num(sub, "safe_combo_score") * 10_000 - safe_num(sub, "rsi_6", 50.0)
        sort_cols = ["date_key", "score_then_rsi6_low", "raw_prob"]
        ascending = [True, False, False]
    elif rank_col == "score_then_turnover":
        sub["score_then_turnover"] = safe_num(sub, "safe_combo_score") * 10_000 + safe_num(sub, "turnover")
        sort_cols = ["date_key", "score_then_turnover", "raw_prob"]
        ascending = [True, False, False]
    elif rank_col == "score_then_amount_z":
        sub["score_then_amount_z"] = safe_num(sub, "safe_combo_score") * 10_000 + safe_num(sub, "amount_z_20")
        sort_cols = ["date_key", "score_then_amount_z", "raw_prob"]
        ascending = [True, False, False]
    elif rank_col == "score_then_closepos":
        sub["score_then_closepos"] = safe_num(sub, "safe_combo_score") * 10_000 + safe_num(sub, "close_position")
        sort_cols = ["date_key", "score_then_closepos", "raw_prob"]
        ascending = [True, False, False]

    sub = sub.sort_values(sort_cols, ascending=ascending)
    sub["daily_rank"] = sub.groupby("date_key").cumcount() + 1
    return sub


def rule_score(row: dict) -> float:
    dev = row["dev_oof_2023_2025"]
    stress = row["stress_oof_2021_2022"]
    if dev["signal_days"] < 80 or dev["tickets"] < 100:
        return -1e9
    score = 0.0
    score += min(dev["total_return_pct"], 2000) * 0.20
    score += dev["avg_daily_return_pct"] * 80
    score += dev["daily_win_rate"] * 120
    score += dev["high5_rate"] * 80
    score += (dev["sharpe"] or 0) * 15
    score += max(stress["total_return_pct"], -500) * 0.05
    score += stress["daily_win_rate"] * 40
    score -= abs(min(dev["max_daily_loss_pct"], 0)) * 3
    score -= max(0, 40 - stress["signal_days"]) * 3
    return round(float(score), 4)


def search_rules(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    selection_mask = period_mask(df, "2023-01-01", "2025-12-31") & (df["score_source"].to_numpy() == "oof")
    selection_only = df.loc[selection_mask].copy()
    masks = build_rule_masks(df, selection_only)
    rank_cols = [
        "raw_prob",
        "iso_prob",
        "safe_combo_score",
        "safe_surge5_score",
        "safe_limit10_score",
        "safe_pred_high_pct",
        "score_then_rsi6_low",
        "score_then_turnover",
        "score_then_amount_z",
        "score_then_closepos",
    ]
    period_specs = [(name, period_mask(df, start, end)) for name, start, end in PERIODS]
    all_rows: list[dict] = []
    kept: list[dict] = []
    t0 = time.time()
    print(f"Searching rules: masks={len(masks)}, rank_cols={len(rank_cols)}", flush=True)
    for mi, (mask_name, mask) in enumerate(masks, 1):
        for rank_col in rank_cols:
            if rank_col not in df.columns and not rank_col.startswith("score_then_"):
                continue
            ranked = rank_frame(df, mask, rank_col)
            if ranked.empty:
                continue
            for top_n in TOP_NS:
                max_ranked = ranked[ranked["daily_rank"] <= top_n].copy()
                if max_ranked.empty:
                    continue
                for exit_mode in EXIT_MODES:
                    row = {
                        "mask": mask_name,
                        "rank_col": rank_col,
                        "top_n": top_n,
                        "exit_mode": exit_mode,
                    }
                    ok = True
                    for period_name, pmask in period_specs:
                        ev = evaluate_selected(max_ranked.loc[pmask[max_ranked.index]], top_n, exit_mode)
                        if ev is None:
                            ok = False
                            break
                        row[period_name] = ev
                    if not ok:
                        continue
                    row["strict_score"] = rule_score(row)
                    all_rows.append(row)
                    if row["strict_score"] > -1e8:
                        kept.append(row)
        if mi % 25 == 0:
            print(f"  masks {mi}/{len(masks)} checked, rows={len(all_rows):,}, elapsed={time.time()-t0:.0f}s", flush=True)
    kept = sorted(kept, key=lambda r: r["strict_score"], reverse=True)
    all_rows = sorted(all_rows, key=lambda r: r.get("strict_score", -1e9), reverse=True)
    return kept[:200], all_rows


def monthly_breakdown(df: pd.DataFrame, rule: dict) -> list[dict]:
    masks = build_rule_masks(df, df.loc[period_mask(df, "2023-01-01", "2025-12-31")])
    mask_map = {name: mask for name, mask in masks}
    ranked = rank_frame(df, mask_map[rule["mask"]], rule["rank_col"])
    picked = ranked[ranked["daily_rank"] <= int(rule["top_n"])].copy()
    picked["realized_return_pct"] = compute_exit(picked, rule["exit_mode"])
    rows = []
    for month, sub in picked.groupby("month"):
        daily = sub.groupby("date_key")["realized_return_pct"].mean().to_numpy(dtype=float)
        rows.append(
            {
                "month": month,
                "signal_days": int(len(daily)),
                "tickets": int(len(sub)),
                "return_pct": round(pct_prod(daily), 2),
                "daily_win_rate": round(float((daily > 0).mean()), 4) if len(daily) else None,
                "high5_rate": round(float((sub["next_high_return_pct"] >= 5.0).mean()), 4) if len(sub) else None,
                "limit10_rate": round(float((sub["next_high_return_pct"] >= 9.8).mean()), 4) if len(sub) else None,
            }
        )
    return rows


def feature_lift(df: pd.DataFrame, feature_cols: list[str]) -> list[dict]:
    scored = df.dropna(subset=["safe_combo_score"]).copy()
    if scored.empty:
        return []
    top = scored["safe_combo_score"] >= scored["safe_combo_score"].quantile(0.90)
    bottom = scored["safe_combo_score"] <= scored["safe_combo_score"].quantile(0.10)
    rows = []
    for col in feature_cols:
        vals = pd.to_numeric(scored[col], errors="coerce")
        if vals.notna().mean() < 0.70:
            continue
        rows.append(
            {
                "feature": col,
                "top10_mean": round(float(vals[top].mean()), 6),
                "bottom10_mean": round(float(vals[bottom].mean()), 6),
                "delta": round(float(vals[top].mean() - vals[bottom].mean()), 6),
            }
        )
    rows.sort(key=lambda r: abs(r["delta"]), reverse=True)
    return rows[:40]


def write_outputs(df: pd.DataFrame, feature_cols: list[str], diag: dict, top_rules: list[dict], all_rules: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    scored_path = OUT_DIR / f"{RUN_TAG}_scored.parquet"
    json_path = OUT_DIR / f"{RUN_TAG}.json"
    rules_path = OUT_DIR / f"{RUN_TAG}_top_rules.csv"
    monthly_path = OUT_DIR / f"{RUN_TAG}_best_monthly.csv"
    lift_path = OUT_DIR / f"{RUN_TAG}_feature_lift.csv"
    md_path = DOC_DIR / f"{RUN_TAG}.md"

    df.to_parquet(scored_path, index=False)
    pd.DataFrame(top_rules).to_csv(rules_path, index=False, encoding="utf-8-sig")
    best = top_rules[0] if top_rules else None
    monthly = monthly_breakdown(df, best) if best else []
    pd.DataFrame(monthly).to_csv(monthly_path, index=False, encoding="utf-8-sig")
    lift = feature_lift(df, feature_cols)
    pd.DataFrame(lift).to_csv(lift_path, index=False, encoding="utf-8-sig")

    audit = {
        "run_tag": RUN_TAG,
        "input": str(INPUT_SCORED),
        "rows": int(len(df)),
        "days": int(df["date_key"].nunique()),
        "feature_count": len(feature_cols),
        "forbidden_selected": [c for c in feature_cols if is_forbidden(c)],
        "score_sources": df["score_source"].value_counts(dropna=False).to_dict(),
        "train_test_boundary": "OOF 2021-2025; final scorer trained <=2025-12-31; 2026 forward only",
        "exit_caveat": "tp/sl exits are daily high-low idealized and need minute-order replay before live execution",
        "diag": diag,
        "best_rule": best,
        "top_rules": top_rules[:20],
        "monthly_best": monthly,
        "feature_lift_top": lift[:25],
    }
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# PhaseC Live-Safe Surge Optimizer - {RUN_TAG}",
        "",
        "## Verdict",
        "",
        "- This run keeps PhaseC frozen and adds a second-stage live-safe surge scorer.",
        "- The scorer uses rolling out-of-sample predictions for 2021-2025; 2026 is report-only.",
        "- Forbidden/post-close/hard-moneyflow fields are excluded from the scorer.",
        "- Stop/take-profit returns are still daily high-low idealized and require minute-order replay before live use.",
        "",
        "## Audit",
        "",
        f"- Rows: {len(df):,}",
        f"- Days: {df['date_key'].nunique():,}",
        f"- Feature count: {len(feature_cols)}",
        f"- Forbidden selected: `{audit['forbidden_selected']}`",
        f"- Score sources: `{audit['score_sources']}`",
        "",
        "## Best Strict Rule",
        "",
    ]
    if best:
        lines += [
            f"- mask: `{best['mask']}`",
            f"- rank: `{best['rank_col']}`",
            f"- top_n: `{best['top_n']}`",
            f"- exit: `{best['exit_mode']}`",
            f"- strict_score: `{best['strict_score']}`",
            "",
        ]
        for name, *_ in PERIODS:
            ev = best[name]
            lines.append(
                f"- {name}: return={ev['total_return_pct']}%, days={ev['signal_days']}, "
                f"daily_win={ev['daily_win_rate']}, high5={ev['high5_rate']}, "
                f"limit10={ev['limit10_rate']}, max_loss={ev['max_daily_loss_pct']}%"
            )
    lines += [
        "",
        "## Monthly Breakdown For Best Rule",
        "",
    ]
    for row in monthly:
        lines.append(
            f"- {row['month']}: return={row['return_pct']}%, days={row['signal_days']}, "
            f"daily_win={row['daily_win_rate']}, high5={row['high5_rate']}, limit10={row['limit10_rate']}"
        )
    lines += [
        "",
        "## Top Feature Lift In Live-Safe Surge Score",
        "",
    ]
    for row in lift[:20]:
        lines.append(f"- {row['feature']}: top10-bottom10 delta={row['delta']}")
    lines += [
        "",
        "## Files",
        "",
        f"- JSON: `{json_path}`",
        f"- Scored candidates: `{scored_path}`",
        f"- Top rules: `{rules_path}`",
        f"- Monthly: `{monthly_path}`",
        f"- Feature lift: `{lift_path}`",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {md_path}", flush=True)


def main() -> None:
    t0 = time.time()
    df = load_pool()
    feature_cols = choose_live_safe_features(df)
    forbidden = [c for c in feature_cols if is_forbidden(c)]
    if forbidden:
        raise RuntimeError(f"Forbidden fields leaked into live-safe feature set: {forbidden}")
    print(f"Live-safe scorer feature count: {len(feature_cols)}", flush=True)
    print("Feature preview:", feature_cols[:12], flush=True)

    df, diag = train_rolling_scorer(df, feature_cols)
    top_rules, all_rules = search_rules(df)
    if not top_rules:
        raise RuntimeError("No eligible strict strategy rules found")
    write_outputs(df, feature_cols, diag, top_rules, all_rules)
    print(f"Done in {(time.time() - t0) / 60.0:.1f} min", flush=True)
    print("Best:", json.dumps(top_rules[0], ensure_ascii=False)[:2400], flush=True)


if __name__ == "__main__":
    main()

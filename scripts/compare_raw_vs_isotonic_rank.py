"""Compare raw ensemble probabilities vs isotonic-calibrated probabilities.

This is score-only diagnostics:
- no retraining
- no run_gpu_next_day_probe
- no Q1/April objective fitting

It loads an already frozen bundle and existing feature caches, then evaluates
ranking and threshold behavior under raw_prob and iso_prob.
"""

from __future__ import annotations

import json
import math
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch


PHASE_E_JSON = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\phaseE_frozen_april_20260509.json")
PRETRAIN_JSON = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\phaseC_pretrain_2023_02_04_validation_20260509.json")

OUT_JSON = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\raw_vs_isotonic_rank_compare_20260509.json")
OUT_MD = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\raw_vs_isotonic_rank_compare_20260509.md")
OUT_CSV = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\raw_vs_isotonic_rank_compare_daily_20260509.csv")
OUT_FINE_THRESHOLD_CSV = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\raw_vs_isotonic_threshold_curve_20260509.csv")

META_COLS = {
    "symbol",
    "name",
    "date",
    "label_date",
    "close",
    "actual",
    "next_close_return_pct",
    "next_high_return_pct",
    "next_low_return_pct",
    "limit_up_like",
    "short_phase_days_3",
}


def wilson_lower(n: int, p: float) -> float:
    if n <= 0:
        return 0.0
    z = 1.96
    denom = 1.0 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n)))
    return float((center - margin) / denom)


def safe_auc(y: np.ndarray, score: np.ndarray) -> float | None:
    if len(np.unique(y)) < 2:
        return None
    try:
        from sklearn.metrics import roc_auc_score

        return float(roc_auc_score(y, score))
    except Exception:
        return None


def safe_ap(y: np.ndarray, score: np.ndarray) -> float | None:
    if len(np.unique(y)) < 2:
        return None
    try:
        from sklearn.metrics import average_precision_score

        return float(average_precision_score(y, score))
    except Exception:
        return None


def load_bundle(bundle_path: Path) -> dict:
    payload = torch.load(str(bundle_path), map_location="cpu", weights_only=False)
    members = [pickle.loads(member["model_bytes"]) for member in payload["members"]]
    iso_model = pickle.loads(payload["iso_model_bytes"]) if payload.get("iso_model_bytes") else None
    return {
        "members": members,
        "mean": payload["mean"],
        "std": payload["std"],
        "selected_indices": payload["selected_indices"],
        "feature_names": list(payload["feature_names"]),
        "selected_feature_names": list(payload.get("selected_feature_names", ())),
        "iso_model": iso_model,
        "calibration_used": payload.get("calibration_used", "none"),
        "threshold": float(payload.get("threshold", 0.5)),
        "model_name": payload.get("model_name", "unknown"),
    }


def predict_raw_and_iso(bundle: dict, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    feature_names = bundle["feature_names"]
    raw_features = np.zeros((len(frame), len(feature_names)), dtype=np.float32)
    for i, name in enumerate(feature_names):
        if name in frame.columns:
            raw_features[:, i] = frame[name].fillna(0).to_numpy(dtype=np.float32)

    x = torch.as_tensor(raw_features, dtype=torch.float32)
    std = bundle["std"].clone()
    std[std == 0] = 1.0
    x = (x - bundle["mean"]) / std
    if bundle["selected_indices"] is not None:
        x = x[:, bundle["selected_indices"]]
    x_np = x.numpy()

    member_probs = [
        member.predict_proba(x_np)[:, 1].astype(np.float32)
        for member in bundle["members"]
    ]
    raw_prob = np.stack(member_probs, axis=0).mean(axis=0).astype(np.float32)
    if bundle["calibration_used"] == "isotonic" and bundle["iso_model"] is not None:
        iso_prob = bundle["iso_model"].predict(raw_prob.astype(np.float64)).astype(np.float32)
    else:
        iso_prob = raw_prob.copy()
    return raw_prob, iso_prob


def load_scoring_frame(cache_path: Path, bundle: dict, start: str, end: str) -> pd.DataFrame:
    schema_cols = set(pq.read_schema(str(cache_path)).names)
    cols = [c for c in sorted(META_COLS | set(bundle["feature_names"])) if c in schema_cols]
    missing = [c for c in bundle["feature_names"] if c not in schema_cols]
    if missing:
        raise RuntimeError(f"Feature cache missing {len(missing)} bundle features, examples={missing[:10]}")

    frame = pd.read_parquet(str(cache_path), columns=cols)
    frame = frame[(frame["date"] >= start) & (frame["date"] <= end)].copy()
    if "limit_up_like" in frame.columns:
        frame = frame[frame["limit_up_like"] != 1].copy()
    if "short_phase_days_3" in frame.columns:
        frame = frame[frame["short_phase_days_3"] >= 1].copy()
    if "actual" not in frame.columns:
        raise RuntimeError(f"{cache_path} has no actual column")
    return frame


def threshold_metrics(frame: pd.DataFrame, score_col: str, thresholds: list[float]) -> dict:
    y = frame["actual"].to_numpy(dtype=np.float32)
    score = frame[score_col].to_numpy(dtype=np.float32)
    out = {}
    for threshold in thresholds:
        mask = score >= threshold
        n = int(mask.sum())
        if n:
            acc = float(y[mask].mean())
            days = int(frame.loc[mask, "date"].nunique())
        else:
            acc = None
            days = 0
        out[f"{threshold:.2f}"] = {
            "count": n,
            "signal_days": days,
            "accuracy": None if acc is None else round(acc, 6),
            "wilson_95": None if acc is None else round(wilson_lower(n, acc), 6),
            "coverage": round(n / len(frame), 6) if len(frame) else 0.0,
        }
    return out


def topk_metrics(frame: pd.DataFrame, score_col: str, ks: list[int]) -> dict:
    out = {}
    for k in ks:
        rows = []
        for _, group in frame.sort_values([score_col, "symbol"], ascending=[False, True]).groupby("date", sort=True):
            take = group.head(k)
            if len(take):
                rows.append(take)
        if not rows:
            out[f"top{k}"] = {"count": 0, "signal_days": 0, "accuracy": None, "wilson_95": None}
            continue
        selected = pd.concat(rows, ignore_index=True)
        n = len(selected)
        acc = float(selected["actual"].mean())
        out[f"top{k}"] = {
            "count": int(n),
            "signal_days": int(selected["date"].nunique()),
            "accuracy": round(acc, 6),
            "wilson_95": round(wilson_lower(n, acc), 6),
            "avg_per_day": round(n / frame["date"].nunique(), 3),
        }
    return out


def daily_top6_threshold_metrics(frame: pd.DataFrame, score_col: str, threshold: float = 0.75) -> dict:
    rows = []
    for _, group in frame[frame[score_col] > threshold].sort_values([score_col, "symbol"], ascending=[False, True]).groupby("date", sort=True):
        if len(group) == 0:
            continue
        top_score = group[score_col].nlargest(min(6, len(group))).min()
        rows.append(group[group[score_col] >= top_score])
    if not rows:
        return {"count": 0, "signal_days": 0, "accuracy": None, "wilson_95": None}
    selected = pd.concat(rows, ignore_index=True)
    n = len(selected)
    acc = float(selected["actual"].mean())
    return {
        "count": int(n),
        "signal_days": int(selected["date"].nunique()),
        "accuracy": round(acc, 6),
        "wilson_95": round(wilson_lower(n, acc), 6),
        "avg_per_signal_day": round(n / selected["date"].nunique(), 3),
    }


def equal_count_topn_metrics(frame: pd.DataFrame, n_values: list[int]) -> dict:
    """Compare raw_prob and iso_prob using identical overall ticket counts."""
    out = {}
    for n in n_values:
        row = {}
        for col in ["raw_prob", "iso_prob"]:
            selected = frame.sort_values([col, "date", "symbol"], ascending=[False, True, True]).head(n)
            if len(selected) == 0:
                row[col] = {
                    "count": 0,
                    "signal_days": 0,
                    "accuracy": None,
                    "wilson_95": None,
                    "cutoff_score": None,
                }
                continue
            acc = float(selected["actual"].mean())
            row[col] = {
                "count": int(len(selected)),
                "signal_days": int(selected["date"].nunique()),
                "accuracy": round(acc, 6),
                "wilson_95": round(wilson_lower(len(selected), acc), 6),
                "cutoff_score": round(float(selected[col].min()), 6),
            }
        raw_acc = row["raw_prob"]["accuracy"]
        iso_acc = row["iso_prob"]["accuracy"]
        if raw_acc is None or iso_acc is None:
            winner = "NA"
        elif raw_acc > iso_acc:
            winner = "raw_prob"
        elif iso_acc > raw_acc:
            winner = "iso_prob"
        else:
            winner = "tie"
        row["winner_by_accuracy"] = winner
        out[str(n)] = row
    return out


def fine_threshold_rows(frame: pd.DataFrame, score_col: str, thresholds: list[float], window_label: str) -> list[dict]:
    rows = []
    y = frame["actual"].to_numpy(dtype=np.float32)
    score = frame[score_col].to_numpy(dtype=np.float32)
    for threshold in thresholds:
        mask = score >= threshold
        n = int(mask.sum())
        if n:
            acc = float(y[mask].mean())
            days = int(frame.loc[mask, "date"].nunique())
            w95 = wilson_lower(n, acc)
        else:
            acc = None
            days = 0
            w95 = None
        rows.append({
            "window": window_label,
            "score": score_col,
            "threshold": round(float(threshold), 4),
            "count": n,
            "signal_days": days,
            "accuracy": "" if acc is None else round(acc, 6),
            "wilson_95": "" if w95 is None else round(w95, 6),
            "coverage": round(n / len(frame), 6) if len(frame) else 0.0,
        })
    return rows


def summarize_window(label: str, frame: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    y = frame["actual"].to_numpy(dtype=np.float32)
    summary: dict[str, object] = {
        "label": label,
        "rows": int(len(frame)),
        "trading_days": int(frame["date"].nunique()),
    }
    daily_rows = []
    for col in ["raw_prob", "iso_prob"]:
        score = frame[col].to_numpy(dtype=np.float32)
        summary[col] = {
            "auc": None if safe_auc(y, score) is None else round(safe_auc(y, score), 6),
            "average_precision": None if safe_ap(y, score) is None else round(safe_ap(y, score), 6),
            "unique_scores": int(pd.Series(score).round(8).nunique()),
            "thresholds": threshold_metrics(frame, col, [0.70, 0.75, 0.78, 0.80, 0.85]),
            "topk": topk_metrics(frame, col, [3, 5, 6, 10, 20]),
            "daily_top6_p_gt_075_ties": daily_top6_threshold_metrics(frame, col, 0.75),
        }
        for date_value, group in frame.groupby("date", sort=True):
            row = {"window": label, "date": date_value, "score": col, "rows": len(group)}
            for threshold in [0.70, 0.75, 0.78, 0.80, 0.85]:
                mask = group[col] >= threshold
                row[f"t{threshold:.2f}_count"] = int(mask.sum())
                row[f"t{threshold:.2f}_acc"] = "" if not mask.any() else round(float(group.loc[mask, "actual"].mean()), 6)
            for k in [3, 5, 6, 10, 20]:
                take = group.sort_values([col, "symbol"], ascending=[False, True]).head(k)
                row[f"top{k}_acc"] = "" if len(take) == 0 else round(float(take["actual"].mean()), 6)
            daily_rows.append(row)

    coarse_counts = []
    for col in ["raw_prob", "iso_prob"]:
        for threshold in [0.70, 0.75, 0.78, 0.80, 0.85]:
            coarse_counts.append(int((frame[col] >= threshold).sum()))
    base_counts = [20, 30, 50, 100, 150, 200, 300, 500, 800, 1000, 1500, 2000]
    n_values = sorted({
        n for n in base_counts + coarse_counts
        if n > 0 and n <= len(frame)
    })
    summary["equal_count_topn"] = equal_count_topn_metrics(frame, n_values)
    return summary, pd.DataFrame(daily_rows)


def main() -> None:
    phase_e = json.loads(PHASE_E_JSON.read_text(encoding="utf-8"))
    bundle_path = Path(phase_e["champion_bundle"])
    april_cache = Path(phase_e["feature_cache"])
    pretrain = json.loads(PRETRAIN_JSON.read_text(encoding="utf-8"))
    pretrain_cache = Path(pretrain["feature_cache"])

    bundle = load_bundle(bundle_path)

    windows = [
        ("april_2026", april_cache, "2026-04-01", "2026-04-30"),
        ("pretrain_2023_02_04", pretrain_cache, "2023-02-01", "2023-04-30"),
    ]

    summaries = {}
    daily_parts = []
    threshold_curve_rows = []
    fine_thresholds = [round(x / 100.0, 2) for x in range(60, 91)]
    for label, cache_path, start, end in windows:
        frame = load_scoring_frame(cache_path, bundle, start, end)
        raw_prob, iso_prob = predict_raw_and_iso(bundle, frame)
        frame["raw_prob"] = raw_prob
        frame["iso_prob"] = iso_prob
        summary, daily = summarize_window(label, frame)
        summaries[label] = summary
        daily_parts.append(daily)
        for score_col in ["raw_prob", "iso_prob"]:
            threshold_curve_rows.extend(fine_threshold_rows(frame, score_col, fine_thresholds, label))

    daily_out = pd.concat(daily_parts, ignore_index=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    daily_out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    pd.DataFrame(threshold_curve_rows).to_csv(OUT_FINE_THRESHOLD_CSV, index=False, encoding="utf-8-sig")

    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "raw_vs_isotonic_rank_compare",
        "methodology": "frozen bundle score-only; raw ensemble probability vs isotonic-calibrated probability",
        "bundle": str(bundle_path),
        "bundle_info": {
            "model_name": bundle["model_name"],
            "calibration_used": bundle["calibration_used"],
            "threshold": bundle["threshold"],
            "feature_count_full": len(bundle["feature_names"]),
            "feature_count_selected": len(bundle["selected_feature_names"]),
        },
        "interpretation_note": "Isotonic is monotonic, so true ranking usually stays almost the same; differences mainly come from probability plateaus/ties and threshold calibration.",
        "windows": summaries,
        "daily_csv": str(OUT_CSV),
        "fine_threshold_csv": str(OUT_FINE_THRESHOLD_CSV),
    }
    OUT_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Raw vs Isotonic Ranking Compare - 2026-05-09",
        "",
        "## Method",
        "- Frozen bundle score-only; no retraining.",
        "- raw_prob = average model predict_proba before isotonic.",
        "- iso_prob = raw_prob after bundle isotonic model.",
        "- Ranking metrics: AUC/AP/topK. Threshold metrics: fixed probability cutoffs.",
        "",
    ]
    for label, summary in summaries.items():
        lines.extend([
            f"## {label}",
            f"- Rows: {summary['rows']}, trading days: {summary['trading_days']}",
            "",
            "| Score | AUC | AP | unique scores | top6 acc | top6 W95 | top6 p>0.75 count | top6 p>0.75 acc | p>0.75 count | p>0.75 acc | p>=0.80 count | p>=0.80 acc |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for col in ["raw_prob", "iso_prob"]:
            info = summary[col]
            top6 = info["topk"]["top6"]
            daily_top = info["daily_top6_p_gt_075_ties"]
            t075 = info["thresholds"]["0.75"]
            t080 = info["thresholds"]["0.80"]
            lines.append(
                f"| {col} | {info['auc']} | {info['average_precision']} | {info['unique_scores']} | "
                f"{top6['accuracy']} | {top6['wilson_95']} | {daily_top['count']} | {daily_top['accuracy']} | "
                f"{t075['count']} | {t075['accuracy']} | {t080['count']} | {t080['accuracy']} |"
            )
        lines.append("")
        lines.extend([
            "### Equal-count overall TopN",
            "",
            "| N | raw acc | raw W95 | raw days | iso acc | iso W95 | iso days | winner |",
            "|---:|---:|---:|---:|---:|---:|---:|---|",
        ])
        for n_str, row in summary["equal_count_topn"].items():
            raw = row["raw_prob"]
            iso = row["iso_prob"]
            lines.append(
                f"| {n_str} | {raw['accuracy']} | {raw['wilson_95']} | {raw['signal_days']} | "
                f"{iso['accuracy']} | {iso['wilson_95']} | {iso['signal_days']} | {row['winner_by_accuracy']} |"
            )
        lines.append("")
    lines.extend([
        "## Notes",
        "- If AUC/AP/topK are nearly identical, raw and isotonic have the same ranking; choose by threshold behavior and live interpretability.",
        "- If iso unique score count is much lower, isotonic is creating probability plateaus, which can increase same-score ties.",
        f"- Daily detail CSV: `{OUT_CSV}`",
        f"- Fine threshold curve CSV: `{OUT_FINE_THRESHOLD_CSV}`",
    ])
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(output["windows"], ensure_ascii=False, indent=2))
    print(f"JSON: {OUT_JSON}")
    print(f"MD: {OUT_MD}")
    print(f"Daily CSV: {OUT_CSV}")
    print(f"Fine threshold CSV: {OUT_FINE_THRESHOLD_CSV}")


if __name__ == "__main__":
    main()

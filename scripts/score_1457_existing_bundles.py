"""Score existing PhaseC/S2 bundles on the next-round rolling windows.

This is score-only by design: no fitting, no feature selection, no calibration
changes. It lets historical bundles join the same evidence table as the fixed
config full-factor matrix without leaking Q1/April into training decisions.
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config


DEFAULT_BUNDLES = {
    "baseline_s2": Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T002433Z_a0ec8105\model_bundle.pt"),
    "baseline_phasec": Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt"),
}

META_COLS = {
    "symbol",
    "date",
    "label_date",
    "actual",
    "close",
    "turnover",
    "limit_up_like",
    "short_phase_days_3",
    "next_close_return_pct",
    "next_high_return_pct",
    "next_low_return_pct",
}


def parse_args() -> argparse.Namespace:
    cfg = get_default_config()
    report_dir = cfg.storage.report_dir / "prediction"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof-date", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--feature-cache", type=Path, required=True)
    parser.add_argument("--time-window-csv", type=Path, default=report_dir / "next_round_1457_time_window_manifest_20260513.csv")
    parser.add_argument("--bundle", action="append", default=[], help="name=path; defaults to S2 and PhaseC.")
    parser.add_argument("--scheme", action="append", default=[])
    parser.add_argument("--max-folds-per-scheme", type=int, default=0)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def wilson_lower(p: float | None, n: int, z: float = 1.959963984540054) -> float:
    if p is None or n <= 0:
        return 0.0
    z2 = z * z
    denom = 1.0 + z2 / float(n)
    centre = float(p) + z2 / (2.0 * float(n))
    margin = z * math.sqrt((float(p) * (1.0 - float(p)) + z2 / (4.0 * float(n))) / float(n))
    return max(0.0, min(1.0, (centre - margin) / denom))


def parse_bundles(items: list[str]) -> dict[str, Path]:
    if not items:
        return dict(DEFAULT_BUNDLES)
    out: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Bundle must be name=path, got {item!r}")
        name, path = item.split("=", 1)
        out[name.strip()] = Path(path.strip())
    return out


def choose_default_schemes(window_df: pd.DataFrame) -> list[str]:
    preferred = [
        "fixed_recent_24m",
        "fixed_recent_36m",
        "fixed_recent_60m",
        "fixed_start_2018",
        "fixed_start_2020",
        "expanding_from_fair_start",
    ]
    available = set(window_df["scheme"].astype(str))
    return [scheme for scheme in preferred if scheme in available]


def selected_windows(window_df: pd.DataFrame, schemes: list[str], max_folds_per_scheme: int) -> pd.DataFrame:
    chosen_schemes = schemes or choose_default_schemes(window_df)
    train_window_valid = pd.to_datetime(window_df["fit_train_start"], errors="coerce").le(
        pd.to_datetime(window_df["fit_train_end"], errors="coerce")
    )
    if "train_window_valid" in window_df.columns:
        train_window_valid = train_window_valid & window_df["train_window_valid"].astype(bool)
    mask = (
        window_df["scheme"].isin(chosen_schemes)
        & window_df["primary_outer_unit"].astype(bool)
        & window_df["eligible_after_rebuild"].astype(bool)
        & ~window_df["train_uses_seen_research"].astype(bool)
        & train_window_valid
    )
    selected = window_df.loc[mask].copy().sort_values(["scheme", "outer_valid_start", "outer_fold"])
    if max_folds_per_scheme > 0:
        selected = pd.concat(
            [_sample_evenly(group, max_folds_per_scheme) for _, group in selected.groupby("scheme", sort=False)],
            ignore_index=True,
        )
    return selected.reset_index(drop=True)


def _sample_evenly(group: pd.DataFrame, count: int) -> pd.DataFrame:
    if count <= 0 or len(group) <= count:
        return group
    if count == 1:
        return group.iloc[[-1]]
    positions = sorted({round(i * (len(group) - 1) / (count - 1)) for i in range(count)})
    return group.iloc[positions]


def load_bundle(path: Path) -> dict[str, Any]:
    payload = torch.load(str(path), map_location="cpu", weights_only=False)
    members = [pickle.loads(member["model_bytes"]) for member in payload["members"]]
    iso = pickle.loads(payload["iso_model_bytes"]) if payload.get("iso_model_bytes") else None
    return {
        "path": str(path),
        "members": members,
        "mean": payload["mean"],
        "std": payload["std"],
        "selected_indices": payload["selected_indices"],
        "feature_names": list(payload["feature_names"]),
        "selected_feature_names": list(payload.get("selected_feature_names") or []),
        "iso_model": iso,
        "calibration_used": payload.get("calibration_used"),
        "threshold": payload.get("threshold"),
    }


def score_bundle(bundle: dict[str, Any], frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    feature_names = bundle["feature_names"]
    raw_features = np.zeros((len(frame), len(feature_names)), dtype=np.float32)
    for idx, name in enumerate(feature_names):
        if name in frame.columns:
            raw_features[:, idx] = pd.to_numeric(frame[name], errors="coerce").fillna(0.0).to_numpy(dtype=np.float32)
    x = torch.as_tensor(raw_features, dtype=torch.float32)
    std = bundle["std"].clone()
    std[std == 0] = 1.0
    x = (x - bundle["mean"]) / std
    selected_indices = bundle.get("selected_indices")
    if selected_indices is not None:
        x = x[:, selected_indices]
    x_np = x.numpy()
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="X does not have valid feature names.*",
            category=UserWarning,
        )
        raw_prob = np.stack([member.predict_proba(x_np)[:, 1].astype(np.float32) for member in bundle["members"]], axis=0).mean(axis=0)
    score_prob = raw_prob
    if bundle.get("calibration_used") == "isotonic" and bundle.get("iso_model") is not None:
        score_prob = bundle["iso_model"].predict(raw_prob.astype(np.float64)).astype(np.float32)
    return raw_prob, score_prob


def threshold_metrics(prob: np.ndarray, actual: np.ndarray, thresholds: tuple[float, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for threshold in thresholds:
        mask = prob >= threshold
        n = int(mask.sum())
        acc = float(actual[mask].mean()) if n else None
        key = str(threshold).replace(".", "")
        out[f"pge_{key}_count"] = n
        out[f"pge_{key}_accuracy"] = acc
        out[f"pge_{key}_wilson95"] = wilson_lower(acc, n)
    return out


def daily_topk_metrics(prob: np.ndarray, frame: pd.DataFrame, topks: tuple[int, ...]) -> dict[str, Any]:
    temp = frame[["date", "actual"]].copy()
    temp["prob"] = prob
    out: dict[str, Any] = {}
    for k in topks:
        selected = temp.sort_values(["date", "prob"], ascending=[True, False]).groupby("date", sort=False).head(k)
        n = int(len(selected))
        acc = float(selected["actual"].mean()) if n else None
        out[f"daily_top{k}_count"] = n
        out[f"daily_top{k}_days"] = int(selected["date"].nunique()) if n else 0
        out[f"daily_top{k}_accuracy"] = acc
        out[f"daily_top{k}_wilson95"] = wilson_lower(acc, n)
    return out


def load_frame(cache_path: Path, bundles: dict[str, dict[str, Any]]) -> pd.DataFrame:
    schema = set(pq.read_schema(cache_path).names)
    needed = set(META_COLS)
    for bundle in bundles.values():
        bundle["missing_feature_names"] = [name for name in bundle["feature_names"] if name not in schema]
        bundle["missing_selected_feature_names"] = [
            name for name in bundle.get("selected_feature_names") or [] if name not in schema
        ]
        needed.update(bundle["feature_names"])
    columns = [column for column in sorted(needed) if column in schema]
    frame = pd.read_parquet(cache_path, columns=columns)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame


def result_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return str(row.get("bundle_id")), str(row.get("scheme")), int(row.get("outer_fold") or 0)


def load_completed(path: Path) -> set[tuple[str, str, int]]:
    out: set[tuple[str, str, int]] = set()
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.add(result_key(json.loads(line)))
        except Exception:
            continue
    return out


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_summary(jsonl_path: Path, csv_path: Path, summary_path: Path) -> None:
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()] if jsonl_path.exists() else []
    if rows:
        pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
    df = pd.DataFrame(rows)
    leaderboard: list[dict[str, Any]] = []
    if not df.empty:
        metric = "daily_top5_wilson95" if "daily_top5_wilson95" in df.columns else "pge_075_wilson95"
        agg = df.groupby(["bundle_id", "scheme"], dropna=False).agg(
            folds=("outer_fold", "count"),
            mean_daily_top5_wilson95=("daily_top5_wilson95", "mean"),
            min_daily_top5_wilson95=("daily_top5_wilson95", "min"),
            mean_pge075_wilson95=("pge_075_wilson95", "mean"),
            total_pge075=("pge_075_count", "sum"),
        ).reset_index()
        agg = agg.sort_values([metric.replace("daily_top5", "mean_daily_top5") if metric.startswith("daily") else "mean_pge075_wilson95"], ascending=False)
        leaderboard = agg.to_dict("records")
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "leaderboard": leaderboard,
        "jsonl": str(jsonl_path),
        "csv": str(csv_path),
    }
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    cfg = get_default_config()
    out_dir = cfg.storage.report_dir / "prediction"
    bundles = {name: load_bundle(path) for name, path in parse_bundles(args.bundle).items()}
    windows = selected_windows(pd.read_csv(args.time_window_csv), args.scheme, args.max_folds_per_scheme)
    jsonl_path = out_dir / f"next_round_1457_existing_bundle_scores_{args.asof_date}.jsonl"
    csv_path = out_dir / f"next_round_1457_existing_bundle_scores_{args.asof_date}.csv"
    summary_path = out_dir / f"next_round_1457_existing_bundle_scores_summary_{args.asof_date}.json"
    completed = load_completed(jsonl_path) if args.resume else set()
    print(json.dumps({"bundles": list(bundles), "windows": len(windows), "planned_scores": len(bundles) * len(windows), "already_completed": len(completed)}, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        return 0
    frame = load_frame(args.feature_cache, bundles)
    for bundle_id, bundle in bundles.items():
        for window in windows.to_dict("records"):
            key = (bundle_id, str(window["scheme"]), int(window["outer_fold"]))
            if key in completed:
                continue
            mask = (
                frame["date"].ge(pd.Timestamp(window["outer_valid_start"]))
                & frame["date"].le(pd.Timestamp(window["outer_valid_end"]))
            )
            sample = frame.loc[mask].copy()
            if "limit_up_like" in sample.columns:
                sample = sample[sample["limit_up_like"].fillna(0).astype(float).ne(1.0)]
            if "short_phase_days_3" in sample.columns:
                sample = sample[pd.to_numeric(sample["short_phase_days_3"], errors="coerce").fillna(0).ge(1)]
            started = time.perf_counter()
            raw_prob, score_prob = score_bundle(bundle, sample)
            actual = pd.to_numeric(sample["actual"], errors="coerce").fillna(0).to_numpy(dtype=np.float32)
            row = {
                "bundle_id": bundle_id,
                "bundle_path": bundle["path"],
                "scheme": str(window["scheme"]),
                "outer_fold": int(window["outer_fold"]),
                "outer_valid_start": str(window["outer_valid_start"]),
                "outer_valid_end": str(window["outer_valid_end"]),
                "rows": int(len(sample)),
                "elapsed_s": round(time.perf_counter() - started, 3),
                "calibration_used": bundle.get("calibration_used"),
                "feature_count": len(bundle["feature_names"]),
                "selected_feature_count": len(bundle.get("selected_feature_names") or []),
                "missing_feature_count": len(bundle.get("missing_feature_names") or []),
                "missing_selected_feature_count": len(bundle.get("missing_selected_feature_names") or []),
                "status": "completed",
            }
            row.update({f"raw_{k}": v for k, v in threshold_metrics(raw_prob, actual, (0.69, 0.75, 0.78, 0.80)).items()})
            row.update(threshold_metrics(score_prob, actual, (0.69, 0.75, 0.78, 0.80)))
            row.update(daily_topk_metrics(score_prob, sample, (3, 5, 10)))
            append_jsonl(jsonl_path, row)
            write_summary(jsonl_path, csv_path, summary_path)
            completed.add(key)
            print(f"[existing_bundle] done {bundle_id} {key[1]} fold={key[2]} rows={len(sample)}", flush=True)
    write_summary(jsonl_path, csv_path, summary_path)
    print(f"[existing_bundle] summary: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""One-shot: M1457_greedy_top8 replay through 2026-05-07, prob>0.75 top6 with ties."""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

spec = importlib.util.spec_from_file_location(
    "run_1457_april_holdout",
    REPO_ROOT / "scripts" / "run_1457_april_holdout.py",
)
rh = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(rh)

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

REPORT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
SUMMARY_PATH = REPORT_DIR / "m1457_greedy_top8_through_20260507_run_summary.json"
TABLE_PATH = REPORT_DIR / "m1457_greedy_top8_through_20260507_T075gt_top6_ties_table.csv"


def main() -> int:
    exclude = rh._build_exclude_names(rh.WINNER["factors"])
    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2026, 3, 31),
        test_start=date(2026, 4, 1),
        end=date(2026, 5, 7),
        seed=42,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=exclude,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )

    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    print(f"START {started}", flush=True)
    print(f"Excluded features: {len(exclude)}", flush=True)
    print("Running M1457_greedy_top8 through label_date<=2026-05-07...", flush=True)

    t0 = time.time()
    store = LocalDataStore(get_default_config())
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0
    print(f"RUN_STATUS {result.get('status')} elapsed={elapsed:.1f}s", flush=True)

    summary = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "variant": "M1457_greedy_top8",
        "window": {
            "train_end": "2026-03-31",
            "test_start": "2026-04-01",
            "end_label_date": "2026-05-07",
        },
        "status": result.get("status"),
        "elapsed_seconds": round(elapsed, 1),
        "run_id": result.get("run_id"),
        "test_predictions_path": result.get("test_predictions_path"),
        "test_rows": result.get("test_rows") or result.get("test_predictions_rows"),
        "high_confident_rows": result.get("high_confident_rows"),
        "confident_accuracy": result.get("confident_accuracy"),
        "confident_coverage": result.get("confident_coverage"),
        "feature_cache": result.get("feature_cache"),
        "model_bundle_status": result.get("model_bundle_status"),
        "exclude_feature_names_count": len(exclude),
        "included_factor_ids": rh.WINNER["factors"],
        "hard_moneyflow_excluded": rh.HARD_UNAVAILABLE_FEATURES,
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"SUMMARY {SUMMARY_PATH}", flush=True)

    pred_path = result.get("test_predictions_path")
    if result.get("status") != "completed" or not pred_path or not Path(pred_path).exists():
        print(f"NO_TABLE status={result.get('status')}", flush=True)
        return 2

    import numpy as np
    import pandas as pd

    pred = pd.read_parquet(pred_path)
    pred["date"] = pd.to_datetime(pred["date"])
    pred["label_date"] = pd.to_datetime(pred["label_date"])

    # Strict > 0.75 (not >=)
    selected = pred[
        (pred["probability"] > 0.75)
        & (pred["label_date"] <= pd.Timestamp("2026-05-07"))
    ].copy()

    # Per signal-date top6 with ties
    groups = []
    for _, group in selected.groupby(selected["date"].dt.date, sort=True):
        group = group.sort_values(["probability", "symbol"], ascending=[False, True]).copy()
        if len(group) > 6:
            cutoff = group.iloc[5]["probability"]
            group = group[group["probability"] >= cutoff].copy()
        groups.append(group)
    output = pd.concat(groups, ignore_index=True) if groups else selected.iloc[0:0].copy()

    # Name lookup
    name_map = {}
    name_cache_path = REPO_ROOT / "scripts" / "_symbol_name_cache.json"
    if name_cache_path.exists():
        raw = json.loads(name_cache_path.read_text(encoding="utf-8"))
        for key, value in raw.items():
            raw_key = str(key)
            name_map[raw_key] = value
            name_map[raw_key.zfill(6)] = value
            try:
                name_map[str(int(raw_key))] = value
            except ValueError:
                pass

    def fmt_date(value):
        ts = pd.to_datetime(value)
        return f"{ts.year}/{ts.month}/{ts.day}"

    def fmt_symbol(value):
        text = str(value)
        try:
            return str(int(text))
        except ValueError:
            return text

    def fmt_num(value, digits=2):
        if pd.isna(value):
            return ""
        return round(float(value), digits)

    def name_for(value):
        text = str(value)
        return (
            name_map.get(text)
            or name_map.get(text.zfill(6))
            or name_map.get(fmt_symbol(text))
            or ""
        )

    table = pd.DataFrame(
        {
            "date": output["date"].map(fmt_date),
            "label_date": output["label_date"].map(fmt_date),
            "symbol": output["symbol"].map(fmt_symbol),
            "name": output["symbol"].map(name_for),
            "probability": output["probability"].map(lambda x: round(float(x), 6)),
            "hit": output["actual"].map(lambda x: "hit" if int(x) == 1 else "miss"),
            "next_high_return_pct": output.apply(
                lambda r: fmt_num(r.get("next_high_return_pct", np.nan)), axis=1
            ),
            "next_close_return_pct": output.apply(
                lambda r: fmt_num(r.get("next_close_return_pct", np.nan)), axis=1
            ),
            "close": output["close"].map(fmt_num),
            "换手": output["turnover"].map(fmt_num) if "turnover" in output.columns else "",
        }
    )
    table.to_csv(TABLE_PATH, index=False, encoding="utf-8-sig")
    print(f"TABLE {TABLE_PATH} rows={len(table)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

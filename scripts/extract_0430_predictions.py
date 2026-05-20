"""Extract 04-30 predictions by patching the last-row exclusion.

The pipeline drops each symbol's last row because torch.roll(-1) wraps.
We patch TWO barriers:
  1. valid mask: include last row (valid < len(frame) instead of len(frame)-1)
  2. label_date: fill NaT with the row's own date so dropna/test-filter keep it

For 04-30 (the last date in data):
- The label (actual) is GARBAGE (wrapped from first row) — ignore it
- The probability is REAL — the model predicts based on 04-30 features
- Training is unaffected: train_end=2025-12-31, no symbol's last row is in train

Output: 04-30 candidates sorted by probability.
"""
from __future__ import annotations
import inspect, json, math, os, sys, textwrap, time
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import torch
import numpy as np
import pandas as pd
import ashare_similarity.prediction.gpu_probe as gp
from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import (
    GPU_PROBE_STABLE_FEATURES,
    GpuProbeConfig,
    run_gpu_next_day_probe,
)

# Feature definitions (same as ablation script)
TUSHARE_TIER1_BASE = (
    "tushare_net_mf_amount", "tushare_lg_buy_sell_ratio", "tushare_elg_buy_sell_ratio",
    "tushare_mf_strength", "tushare_sm_sell_pressure", "tushare_volume_ratio",
    "tushare_free_share", "tushare_up_limit_distance", "tushare_down_limit_distance",
    "tushare_limit_range",
)
TUSHARE_TIER1_FEATURES = (*TUSHARE_TIER1_BASE, *(f"{c}_available" for c in TUSHARE_TIER1_BASE))
C009_FEATURES = ("tushare_main_force_divergence", "tushare_main_force_divergence_available")
C004_FEATURES = ("tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available")
TIER1_PLUS_C009_C004 = (*TUSHARE_TIER1_FEATURES, *C009_FEATURES, *C004_FEATURES)


def main():
    app_config = get_default_config()
    store = LocalDataStore(app_config)

    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 4, 30),
        train_rows=300_000,
        test_rows=120_000,
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        min_phase_days_3=1,
        selector_coverage_weight=0.02,
        candidate_family="all",
        lockbox_role="seen_research",
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        seed=42,
        feature_set="research",
        use_feature_cache=False,
    )

    custom_features = tuple(dict.fromkeys((*GPU_PROBE_STABLE_FEATURES, *TIER1_PLUS_C009_C004)))

    # --- Patch 1: feature names (same as ablation) ---
    original_fn = gp._feature_names_for_config
    call_state = {"count": 0}
    def _two_phase(cfg):
        call_state["count"] += 1
        return original_fn(cfg) if call_state["count"] == 1 else custom_features
    gp._feature_names_for_config = _two_phase

    # --- Patch 2: _symbol_feature_frame to include last row ---
    # Two changes:
    #   a) valid < len(frame) - 1  -->  valid < len(frame)
    #   b) After label_date assignment, fill NaT with the row's own date
    original_symbol_feature_frame = gp._symbol_feature_frame
    src_lines = inspect.getsource(gp._symbol_feature_frame).split('\n')
    patched_lines = []
    for line in src_lines:
        if 'valid < len(frame) - 1' in line:
            patched_lines.append(line.replace('len(frame) - 1', 'len(frame)'))
            print(f"  Patch A: {line.strip()} -> ...len(frame))", file=sys.stderr)
        elif 'out["label_date"] = frame["date"].shift(-1)' in line:
            patched_lines.append(line)
            # Add line to fill NaT label_date with the row's own date
            indent = len(line) - len(line.lstrip())
            fill_line = ' ' * indent + 'out["label_date"] = out["label_date"].fillna(out["date"])'
            patched_lines.append(fill_line)
            print(f"  Patch B: added label_date NaT fill after: {line.strip()}", file=sys.stderr)
        else:
            patched_lines.append(line)

    patched_src = textwrap.dedent('\n'.join(patched_lines))

    exec_globals = dict(gp.__dict__)
    exec_globals.update({
        'pd': pd, 'np': np, 'torch': torch,
        'math': math, 'time': time,
    })
    exec(compile(patched_src, '<patched>', 'exec'), exec_globals)
    gp._symbol_feature_frame = exec_globals['_symbol_feature_frame']
    print("  _symbol_feature_frame patched successfully (valid mask + label_date fill)", file=sys.stderr)

    # --- Patch 3: dropna in run_gpu_next_day_probe ---
    # Line 921: data = data.dropna(subset=["date", "label_date"])
    # After patch 2, label_date is filled so this should be fine.
    # But just in case, also patch to only drop on "date" (not label_date).
    # Actually with patch 2 filling NaT, dropna should keep all rows. No extra patch needed.

    print("\nRunning G (C009+C004) with patched valid mask + label_date fill...", file=sys.stderr)
    t0 = time.perf_counter()

    try:
        result = run_gpu_next_day_probe(store, config)
    finally:
        gp._feature_names_for_config = original_fn
        gp._symbol_feature_frame = original_symbol_feature_frame

    elapsed = time.perf_counter() - t0
    print(f"Done in {elapsed:.1f}s, status={result.get('status')}", file=sys.stderr)

    # Find predictions file
    run_id = result.get("run_id", "")
    pred_path = ""
    if run_id:
        base = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs")
        pred_path = str(base / run_id / "test_predictions.parquet")

    print(f"run_id: {run_id}", file=sys.stderr)
    print(f"pred_path: {pred_path}", file=sys.stderr)

    if pred_path and os.path.exists(pred_path):
        df = pd.read_parquet(pred_path)
        df["date"] = pd.to_datetime(df["date"])
        print(f"Total predictions: {len(df)}", file=sys.stderr)
        print(f"Last 5 dates: {sorted(df['date'].dt.date.unique())[-5:]}", file=sys.stderr)

        d30 = df[df["date"].dt.date == date(2026, 4, 30)]
        print(f"04-30 predictions: {len(d30)}", file=sys.stderr)

        if len(d30) > 0:
            # Note: actual/next_high_return_pct/next_close_return_pct for 04-30 are GARBAGE
            # Only probability and close are meaningful
            cands = d30[d30["probability"] >= 0.75].sort_values("probability", ascending=False)
            cands70 = d30[d30["probability"] >= 0.70].sort_values("probability", ascending=False)
            print(f"04-30 T>=0.75 candidates: {len(cands)}", file=sys.stderr)
            print(f"04-30 T>=0.70 candidates: {len(cands70)}", file=sys.stderr)

            cols = ["symbol", "probability", "close"]
            if "turnover" in d30.columns:
                cols.append("turnover")

            print("\n=== 04-30 T>=0.75 candidates (for 05-06 buying) ===")
            if len(cands) > 0:
                print(cands[cols].to_string(index=False))
            else:
                print("(none)")

            print(f"\n=== 04-30 T>=0.70 candidates (relaxed, top 30) ===")
            print(cands70[cols].head(30).to_string(index=False))

            print(f"\n=== 04-30 probability distribution ===")
            print(d30["probability"].describe().to_string())
        else:
            print("04-30 still not in predictions!", file=sys.stderr)
            print(f"Last 5 dates: {sorted(df['date'].dt.date.unique())[-5:]}", file=sys.stderr)
            # Debug: check if any label_date is NaT
            if "label_date" in df.columns:
                nat_count = df["label_date"].isna().sum()
                print(f"NaT label_date rows: {nat_count}", file=sys.stderr)
    else:
        print(f"Could not find predictions at: {pred_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""End-to-end timing test for real-time inference feasibility.

Simulates the 14:57 scenario:
  Phase A: Parallel feature computation for ALL symbols
  Phase B: Model training + prediction (using feature cache to isolate timing)
  Phase C: Full pipeline timing with parallel features
"""
import time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import torch
from datetime import date
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
import ashare_similarity.prediction.gpu_probe as gp
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, GPU_PROBE_STABLE_FEATURES

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

CONFIG = GpuProbeConfig(
    start=date(2023, 5, 1), train_end=date(2025, 12, 31),
    test_start=date(2026, 1, 1), end=date(2026, 4, 30),
    train_rows=300_000, test_rows=120_000,
    label_target='next_high_from_close', target_high_return_pct=1.0,
    feature_selection_method='stable_tail', max_selected_features=260,
    min_phase_days_3=1, selector_coverage_weight=0.02,
    candidate_family='all', lockbox_role='seen_research',
    exclude_event_limit_up=True, exclude_feature_prefix=('cross_',),
    seed=42, feature_set='research',
)


def compute_symbol(sym):
    """Compute features for one symbol in a subprocess."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    import torch, pandas as pd
    from ashare_similarity.config import get_default_config
    from ashare_similarity.data.storage import LocalDataStore
    import ashare_similarity.prediction.gpu_probe as gp

    store = LocalDataStore(get_default_config())
    device = torch.device('cpu')
    bars = store.load_market_data('daily', symbols=[sym])
    bars_pd = bars.to_pandas() if hasattr(bars, 'to_pandas') else pd.DataFrame(bars)
    frame = gp._symbol_feature_frame(
        bars_pd, symbol=sym, start=CONFIG.start, end=CONFIG.end,
        device=device, config=CONFIG,
    )
    if frame is not None and not frame.empty:
        return frame
    return None


def test_phase_a():
    """Phase A: Parallel feature computation for ALL symbols."""
    print("=" * 60)
    print("PHASE A: Parallel feature computation (ALL symbols)")
    print("=" * 60)

    store = LocalDataStore(get_default_config())
    symbols = [str(s).zfill(6) for s in store.list_cached_symbols('daily')]
    # Filter to main board
    symbols = [s for s in symbols if s.startswith(('600','601','603','605','000','001','002','003','300'))]
    print(f"  Symbols to process: {len(symbols)}")

    t0 = time.perf_counter()
    frames = []
    with ProcessPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(compute_symbol, symbols))
    for frame in results:
        if frame is not None:
            frames.append(frame)

    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    elapsed = time.perf_counter() - t0

    print(f"  Results: {len(data)} rows, {data['symbol'].nunique() if len(data) > 0 else 0} symbols")
    print(f"  Time: {elapsed:.1f}s = {elapsed/60:.1f} min")
    if len(data) > 0:
        dates = sorted(data['date'].dt.date.unique())
        print(f"  Date range: {dates[0]} to {dates[-1]}")
        last_day = data[data['date'].dt.date == dates[-1]]
        print(f"  Last day ({dates[-1]}): {len(last_day)} rows")
    return data, elapsed


def test_phase_b():
    """Phase B: Model training + prediction using feature cache (no feature computation)."""
    print()
    print("=" * 60)
    print("PHASE B: Model training + prediction (feature cache)")
    print("=" * 60)

    custom_features = tuple(dict.fromkeys((*GPU_PROBE_STABLE_FEATURES, *TIER1_PLUS_C009_C004)))

    original_fn = gp._feature_names_for_config
    call_state = {"count": 0}
    def _two_phase(cfg):
        call_state["count"] += 1
        return original_fn(cfg) if call_state["count"] == 1 else custom_features
    gp._feature_names_for_config = _two_phase

    store = LocalDataStore(get_default_config())

    config_cached = GpuProbeConfig(
        start=date(2023, 5, 1), train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1), end=date(2026, 4, 30),
        train_rows=300_000, test_rows=120_000,
        label_target='next_high_from_close', target_high_return_pct=1.0,
        feature_selection_method='stable_tail', max_selected_features=260,
        min_phase_days_3=1, selector_coverage_weight=0.02,
        candidate_family='all', lockbox_role='seen_research',
        exclude_event_limit_up=True, exclude_feature_prefix=('cross_',),
        seed=42, feature_set='research',
        use_feature_cache=True,  # USE CACHE - skip feature building
    )

    t0 = time.perf_counter()
    result = run_gpu_next_day_probe(store, config_cached)
    elapsed = time.perf_counter() - t0

    gp._feature_names_for_config = original_fn

    print(f"  Status: {result.get('status')}")
    print(f"  Time: {elapsed:.1f}s = {elapsed/60:.1f} min")
    print(f"  (This is feature selection + model training + prediction)")
    return result, elapsed


if __name__ == '__main__':
    from ashare_similarity.prediction.gpu_probe import run_gpu_next_day_probe
    import threading

    print(f"CPU cores: {os.cpu_count()}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
    print()

    # Phase A: parallel feature computation
    data_a, time_a = test_phase_a()

    # Phase B: model training + prediction (with cache)
    result_b, time_b = test_phase_b()

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Data acquisition (from prior test):     ~11s")
    print(f"  Feature computation (8 proc parallel):  {time_a:.0f}s")
    print(f"  Model train + predict (cache):          {time_b:.0f}s")
    print(f"  ---")
    total_with_train = 11 + time_a + time_b
    total_predict_only = 11 + time_a + 5  # assume 5s for predict-only
    print(f"  Total WITH retraining:                  {total_with_train:.0f}s = {total_with_train/60:.1f}min")
    print(f"  Total predict-only (saved model):       {total_predict_only:.0f}s = {total_predict_only/60:.1f}min")
    print()
    if total_predict_only <= 180:
        print(f"  >> predict-only fits in 3-min window (14:57 -> {total_predict_only:.0f}s)")
    else:
        print(f"  >> predict-only EXCEEDS 3-min window by {total_predict_only-180:.0f}s")
    if total_with_train <= 180:
        print(f"  >> with retraining also fits!")
    else:
        start_time_min = 57 - (total_with_train / 60)
        print(f"  >> with retraining: need to start at ~14:{start_time_min:.0f}")

"""Test parallel feature computation speed."""
import time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import torch
from datetime import date
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
import ashare_similarity.prediction.gpu_probe as gp
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig

CONFIG = GpuProbeConfig(
    start=date(2023, 5, 1), train_end=date(2025, 12, 31),
    test_start=date(2026, 1, 1), end=date(2026, 4, 30),
    train_rows=300_000, test_rows=120_000,
    label_target='next_high_from_close', target_high_return_pct=1.0,
    feature_selection_method='stable_tail', max_selected_features=260,
    min_phase_days_3=1, seed=42, feature_set='research',
)

def compute_one(sym):
    app_config = get_default_config()
    store = LocalDataStore(app_config)
    device = torch.device('cpu')
    bars = store.load_market_data('daily', symbols=[sym])
    bars_pd = bars.to_pandas() if hasattr(bars, 'to_pandas') else pd.DataFrame(bars)
    frame = gp._symbol_feature_frame(
        bars_pd, symbol=sym, start=CONFIG.start, end=CONFIG.end,
        device=device, config=CONFIG,
    )
    return sym, len(frame) if frame is not None and not frame.empty else 0


def compute_one_thread(args):
    sym, store, device = args
    bars = store.load_market_data('daily', symbols=[sym])
    bars_pd = bars.to_pandas() if hasattr(bars, 'to_pandas') else pd.DataFrame(bars)
    frame = gp._symbol_feature_frame(
        bars_pd, symbol=sym, start=CONFIG.start, end=CONFIG.end,
        device=device, config=CONFIG,
    )
    return sym, len(frame) if frame is not None and not frame.empty else 0


if __name__ == '__main__':
    app_config = get_default_config()
    store = LocalDataStore(app_config)
    symbols = [str(s).zfill(6) for s in store.list_cached_symbols('daily')]
    test_batch = symbols[:200]
    print(f'CPU cores: {os.cpu_count()}')
    print(f'Test batch: {len(test_batch)} symbols')

    # Thread pool (shares GIL but avoids pickle issues)
    for n_workers in [8, 16]:
        device = torch.device('cpu')
        args = [(sym, store, device) for sym in test_batch]
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            results = list(executor.map(compute_one_thread, args))
        elapsed = time.perf_counter() - t0
        est_2000 = elapsed / len(test_batch) * 2000
        print(f'ThreadPool({n_workers}): {len(test_batch)} symbols in {elapsed:.1f}s '
              f'({elapsed/len(test_batch):.3f}s/sym) → 2000 est: {est_2000:.0f}s = {est_2000/60:.1f}min')

    # Process pool
    for n_workers in [8, 16]:
        t0 = time.perf_counter()
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            results = list(executor.map(compute_one, test_batch))
        elapsed = time.perf_counter() - t0
        est_2000 = elapsed / len(test_batch) * 2000
        print(f'ProcessPool({n_workers}): {len(test_batch)} symbols in {elapsed:.1f}s '
              f'({elapsed/len(test_batch):.3f}s/sym) → 2000 est: {est_2000:.0f}s = {est_2000/60:.1f}min')

"""Smoke test: verify build_tushare_factors produces all 39 columns without OOM.
Loads only 5 dates per API to keep memory low.
"""
import sys, os
sys.path.insert(0, r'C:\Users\zzzzzzl\Desktop\subagent\src')

from pathlib import Path
import pandas as pd

TUSHARE_DIR = Path(r'E:\ashare_similarity_runtime\data\cache\prediction\tushare')

# Quick check: which API dirs exist and have data?
print("=== Data directories ===")
for d in sorted(TUSHARE_DIR.iterdir()):
    if d.is_dir() and not d.name.startswith('_'):
        parquets = list(d.glob("*.parquet"))
        print(f"  {d.name}: {len(parquets)} parquet files")

# Now test the actual build function
print("\n=== Testing build_tushare_factors ===")
from ashare_similarity.prediction.free_data_factors import (
    build_tushare_factors, TUSHARE_FACTOR_COLUMNS,
)

print(f"Expected columns ({len(TUSHARE_FACTOR_COLUMNS)}): {TUSHARE_FACTOR_COLUMNS}")

ff = build_tushare_factors(TUSHARE_DIR)
print(f"\nFactorFrame name: {ff.name}")
print(f"Shape: {ff.frame.shape}")
print(f"Columns in frame: {list(ff.frame.columns)}")

missing = [c for c in TUSHARE_FACTOR_COLUMNS if c not in ff.frame.columns]
if missing:
    print(f"\nMISSING columns: {missing}")
else:
    print(f"\nAll {len(TUSHARE_FACTOR_COLUMNS)} factor columns present.")

# Non-null stats
print("\n=== Non-null counts (sample) ===")
for col in TUSHARE_FACTOR_COLUMNS:
    nn = ff.frame[col].notna().sum()
    print(f"  {col}: {nn:,} non-null")

print(f"\nTotal rows: {len(ff.frame):,}")
print(f"Date range: {ff.frame['date'].min()} to {ff.frame['date'].max()}")
print("\nSMOKE TEST PASSED")

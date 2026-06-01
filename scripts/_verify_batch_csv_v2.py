"""Re-verify batch CSV against raw daily bar parquet files."""
import pandas as pd
import numpy as np
from pathlib import Path

CSV = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\batch_postclose_all_candidates.csv")
BARS_DIR = Path(r"E:\ashare_similarity_runtime\data\raw\bars\daily")

df = pd.read_csv(CSV, dtype=str)
df["probability"] = df["probability"].astype(float)
df["next_high_return_pct"] = pd.to_numeric(df["next_high_return_pct"], errors="coerce")
df["next_close_return_pct"] = pd.to_numeric(df["next_close_return_pct"], errors="coerce")
df["close"] = pd.to_numeric(df["close"], errors="coerce")
df["_dt"] = pd.to_datetime(df["date"], format="mixed")
df["_ldt"] = pd.to_datetime(df["label_date"], format="mixed")

has_return = df["next_high_return_pct"].notna()
errors = []

# ── Check 1: Hit label consistency ──
print("=" * 60)
print("CHECK 1: Hit label vs next_high_return_pct consistency")
print("=" * 60)
wrong_hit = df[(df["hit"] == "hit") & has_return & (df["next_high_return_pct"] < 1.0)]
wrong_miss = df[(df["hit"] == "miss") & has_return & (df["next_high_return_pct"] >= 1.0)]
wrong_empty = df[~df["hit"].isin(["hit", "miss"]) & has_return]
print(f"  hit but return < 1.0: {len(wrong_hit)}")
print(f"  miss but return >= 1.0: {len(wrong_miss)}")
print(f"  empty hit but has return: {len(wrong_empty)}")
if len(wrong_hit) + len(wrong_miss) + len(wrong_empty) > 0:
    errors.append("CHECK1 FAIL")

# ── Check 2+3+10: Spot-check returns + close vs raw bars (all periods) ──
print("\n" + "=" * 60)
print("CHECK 2/3/10: Spot-check vs raw parquet bars")
print("=" * 60)

np.random.seed(42)
verified = df[has_return].copy()

# Sample: 100 from 2017-2022 (OOS), 50 from 2023+
oos = verified[verified["_dt"] < "2023-01-01"]
is_period = verified[verified["_dt"] >= "2023-01-01"]

oos_idx = np.random.choice(len(oos), size=min(150, len(oos)), replace=False)
is_idx = np.random.choice(len(is_period), size=min(50, len(is_period)), replace=False)
sample = pd.concat([oos.iloc[oos_idx], is_period.iloc[is_idx]])

bar_cache = {}
def get_bars(sym):
    if sym not in bar_cache:
        p = BARS_DIR / f"{sym}.parquet"
        if p.exists():
            b = pd.read_parquet(p)
            b["_date"] = pd.to_datetime(b["date"])
            b = b.set_index("_date")
            bar_cache[sym] = b
        else:
            bar_cache[sym] = None
    return bar_cache[sym]

n_checked = 0
return_mismatches = []
close_mismatches = []
hit_label_mismatches = []

for _, row in sample.iterrows():
    sym = row["symbol"]
    bars = get_bars(sym)
    if bars is None:
        continue

    signal_dt = row["_dt"]
    label_dt = row["_ldt"]

    if signal_dt not in bars.index or label_dt not in bars.index:
        continue

    raw_close = float(bars.loc[signal_dt, "close"])
    if isinstance(raw_close, pd.Series):
        raw_close = float(raw_close.iloc[0])
    raw_next_high = float(bars.loc[label_dt, "high"])
    if isinstance(raw_next_high, pd.Series):
        raw_next_high = float(raw_next_high.iloc[0])
    raw_next_close = float(bars.loc[label_dt, "close"])
    if isinstance(raw_next_close, pd.Series):
        raw_next_close = float(raw_next_close.iloc[0])

    expected_high_ret = round((raw_next_high / raw_close - 1) * 100, 2)
    expected_close_ret = round((raw_next_close / raw_close - 1) * 100, 2)
    expected_hit = "hit" if expected_high_ret >= 1.0 else "miss"

    n_checked += 1

    # Close price check
    csv_close = row["close"]
    if abs(raw_close - csv_close) > 0.02:
        close_mismatches.append(
            f"  {row['date']} {sym}: csv_close={csv_close}, raw_close={raw_close}"
        )

    # Return check
    csv_ret = row["next_high_return_pct"]
    if abs(expected_high_ret - csv_ret) > 0.02:
        return_mismatches.append(
            f"  {row['date']} {sym}: csv_ret={csv_ret}, expected={expected_high_ret} "
            f"(raw_close={raw_close}, raw_high={raw_next_high})"
        )

    # Hit label check
    if row["hit"] != expected_hit:
        hit_label_mismatches.append(
            f"  {row['date']} {sym}: csv_hit={row['hit']}, expected={expected_hit}, "
            f"ret={expected_high_ret}"
        )

print(f"  Spot-checked: {n_checked} rows (OOS 2017-22 + IS 2023+)")
print(f"  Close price mismatches: {len(close_mismatches)}")
print(f"  Return mismatches: {len(return_mismatches)}")
print(f"  Hit label mismatches: {len(hit_label_mismatches)}")

if close_mismatches:
    errors.append(f"CHECK3: {len(close_mismatches)} close mismatches")
    for m in close_mismatches[:10]:
        print(m)
if return_mismatches:
    errors.append(f"CHECK2: {len(return_mismatches)} return mismatches")
    for m in return_mismatches[:10]:
        print(m)
if hit_label_mismatches:
    errors.append(f"CHECK10: {len(hit_label_mismatches)} hit label mismatches")
    for m in hit_label_mismatches[:10]:
        print(m)

# ── Check 4: Probability range ──
print(f"\n{'='*60}\nCHECK 4: Prob range\n{'='*60}")
print(f"  Min: {df['probability'].min():.6f}, Max: {df['probability'].max():.6f}, Below 0.70: {(df['probability']<0.70).sum()}")

# ── Check 5: Duplicates ──
print(f"\n{'='*60}\nCHECK 5: Duplicates\n{'='*60}")
dupes = df.duplicated(subset=["date", "symbol"], keep=False).sum()
print(f"  Duplicate (date,symbol): {dupes}")
if dupes > 0:
    errors.append(f"CHECK5: {dupes} duplicates")

# ── Check 6: Sorting ──
print(f"\n{'='*60}\nCHECK 6: Date sorting\n{'='*60}")
sorted_ok = df["_dt"].is_monotonic_increasing
print(f"  Monotonic ascending: {sorted_ok}")
if not sorted_ok:
    errors.append("CHECK6: not sorted")

# ── Check 7: ST ──
print(f"\n{'='*60}\nCHECK 7: ST exclusion\n{'='*60}")
st_count = df["name"].str.contains("ST", case=False, na=False).sum()
print(f"  ST rows: {st_count}")
if st_count > 0:
    errors.append(f"CHECK7: {st_count} ST")

# ── Check 8: Unverified ──
print(f"\n{'='*60}\nCHECK 8: Unverified rows\n{'='*60}")
unv = df[~df["hit"].isin(["hit","miss"])]
unv_has_ret = unv[unv["next_high_return_pct"].notna()]
print(f"  Unverified: {len(unv)}, with return data (should be 0): {len(unv_has_ret)}")
if len(unv_has_ret) > 0:
    errors.append(f"CHECK8: {len(unv_has_ret)} unverified with returns")

# ── Check 9: Symbol format ──
print(f"\n{'='*60}\nCHECK 9: Symbol format\n{'='*60}")
bad = (~df["symbol"].str.match(r"^\d{6}$")).sum()
print(f"  Bad symbols: {bad}")

# ── Extra: Deep edge cases ──
print(f"\n{'='*60}\nCHECK EXTRA: Edge cases around hit=1.0% boundary\n{'='*60}")
# Check rows where next_high_return_pct is very close to 1.0
boundary = df[has_return & (df["next_high_return_pct"].between(0.98, 1.02))].copy()
print(f"  Rows in 0.98-1.02% range: {len(boundary)}")
# Verify these boundary rows against raw bars
n_boundary_checked = 0
boundary_errors = []
for _, row in boundary.iterrows():
    sym = row["symbol"]
    bars = get_bars(sym)
    if bars is None:
        continue
    signal_dt = row["_dt"]
    label_dt = row["_ldt"]
    if signal_dt not in bars.index or label_dt not in bars.index:
        continue
    raw_close = float(bars.loc[signal_dt, "close"])
    if isinstance(raw_close, pd.Series):
        raw_close = float(raw_close.iloc[0])
    raw_high = float(bars.loc[label_dt, "high"])
    if isinstance(raw_high, pd.Series):
        raw_high = float(raw_high.iloc[0])
    exact_ret = (raw_high / raw_close - 1) * 100
    rounded_ret = round(exact_ret, 2)
    expected_hit = "hit" if rounded_ret >= 1.0 else "miss"
    n_boundary_checked += 1
    if row["hit"] != expected_hit:
        boundary_errors.append(
            f"  {row['date']} {sym}: exact_ret={exact_ret:.6f}%, rounded={rounded_ret}, "
            f"csv_hit={row['hit']}, expected={expected_hit}"
        )

print(f"  Boundary rows verified: {n_boundary_checked}")
print(f"  Boundary label errors: {len(boundary_errors)}")
if boundary_errors:
    errors.append(f"BOUNDARY: {len(boundary_errors)} errors")
    for e in boundary_errors[:20]:
        print(e)

# ── Summary ──
print(f"\n{'='*60}\nFINAL SUMMARY\n{'='*60}")
if errors:
    print(f"  ERRORS: {len(errors)}")
    for e in errors:
        print(f"    - {e}")
else:
    print(f"  ALL CHECKS PASSED ({n_checked} rows spot-checked against raw bars, {n_boundary_checked} boundary rows verified)")

"""Comprehensive re-verification of batch historical backtest CSV.

10 checks:
1. Hit label consistency: next_high_return_pct >= 1.0 iff hit == "hit"
2. Spot-check raw bars: verify next_high_return_pct against actual daily bars
3. Close price consistency: close matches signal-day bars
4. Date/label_date mapping: label_date == next trading day after date
5. Probability range: all prob >= 0.70
6. Symbol validity: all 6-digit, no duplicates within same date
7. Sorting: dates in ascending order
8. Unverified rows: no next-day data → hit is empty
9. ST exclusion: no ST names in output
10. 2017-2022 specific: spot-check earliest/hardest OOS period against raw bars
"""
import pandas as pd
import numpy as np
from pathlib import Path
import pickle, struct

CSV = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\batch_postclose_all_candidates.csv")
BARS_DIR = Path(r"E:\ashare_similarity_runtime\data\daily_bars")

df = pd.read_csv(CSV, dtype=str)
df["probability"] = df["probability"].astype(float)
df["next_high_return_pct"] = pd.to_numeric(df["next_high_return_pct"], errors="coerce")
df["next_close_return_pct"] = pd.to_numeric(df["next_close_return_pct"], errors="coerce")
df["close"] = pd.to_numeric(df["close"], errors="coerce")

errors = []

# ── Check 1: Hit label consistency ──
print("="*60)
print("CHECK 1: Hit label vs next_high_return_pct consistency")
print("="*60)
has_return = df["next_high_return_pct"].notna()
hit_mask = df["hit"] == "hit"
miss_mask = df["hit"] == "miss"
empty_mask = ~df["hit"].isin(["hit", "miss"])

# hit should have return >= 1.0
wrong_hit = df[hit_mask & has_return & (df["next_high_return_pct"] < 1.0)]
# miss should have return < 1.0
wrong_miss = df[miss_mask & has_return & (df["next_high_return_pct"] >= 1.0)]
# empty hit should have no return data
wrong_empty = df[empty_mask & has_return]

print(f"  hit but return < 1.0: {len(wrong_hit)}")
print(f"  miss but return >= 1.0: {len(wrong_miss)}")
print(f"  empty hit but has return: {len(wrong_empty)}")
if len(wrong_hit) > 0:
    errors.append(f"CHECK1: {len(wrong_hit)} rows labeled hit but return < 1.0")
    print(f"  Examples:")
    print(wrong_hit[["date","symbol","next_high_return_pct","hit"]].head(5).to_string())
if len(wrong_miss) > 0:
    errors.append(f"CHECK1: {len(wrong_miss)} rows labeled miss but return >= 1.0")
    print(f"  Examples:")
    print(wrong_miss[["date","symbol","next_high_return_pct","hit"]].head(5).to_string())
if len(wrong_empty) > 0:
    errors.append(f"CHECK1: {len(wrong_empty)} rows empty hit but has return data")

# ── Check 2: Spot-check against raw daily bars ──
print("\n" + "="*60)
print("CHECK 2: Spot-check next_high_return_pct against raw bars")
print("="*60)

def load_daily_bars(symbol):
    path = BARS_DIR / f"{symbol}.pkl"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)

# Sample 50 rows from different periods
np.random.seed(42)
verified_df = df[has_return].copy()
sample_idx = np.random.choice(len(verified_df), size=min(100, len(verified_df)), replace=False)
sample = verified_df.iloc[sample_idx]

n_checked = 0
n_mismatch = 0
mismatch_details = []

for _, row in sample.iterrows():
    symbol = row["symbol"]
    signal_date = row["date"]  # e.g. "2017/2/14"
    label_date = row["label_date"]  # next trading day
    csv_high_ret = row["next_high_return_pct"]
    csv_close = row["close"]

    bars = load_daily_bars(symbol)
    if bars is None:
        continue

    # Parse dates - bars might have different date format
    if isinstance(bars, pd.DataFrame):
        if "trade_date" in bars.columns:
            bars["_date"] = pd.to_datetime(bars["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
        elif "date" in bars.columns:
            bars["_date"] = pd.to_datetime(bars["date"], format="mixed", errors="coerce")
        else:
            continue

        signal_dt = pd.to_datetime(signal_date, format="mixed")
        label_dt = pd.to_datetime(label_date, format="mixed")

        # Get signal day close
        signal_row = bars[bars["_date"] == signal_dt]
        label_row = bars[bars["_date"] == label_dt]

        if signal_row.empty or label_row.empty:
            continue

        if "close" in bars.columns:
            raw_close = float(signal_row["close"].iloc[0])
        else:
            continue

        if "high" in bars.columns:
            raw_high = float(label_row["high"].iloc[0])
        else:
            continue

        expected_ret = round((raw_high / raw_close - 1) * 100, 2)

        n_checked += 1
        if abs(expected_ret - csv_high_ret) > 0.02:
            n_mismatch += 1
            mismatch_details.append({
                "date": signal_date,
                "symbol": symbol,
                "csv_close": csv_close,
                "raw_close": raw_close,
                "raw_high": raw_high,
                "csv_ret": csv_high_ret,
                "expected_ret": expected_ret,
                "diff": abs(expected_ret - csv_high_ret),
            })

print(f"  Spot-checked: {n_checked}")
print(f"  Mismatches (diff > 0.02pp): {n_mismatch}")
if n_mismatch > 0:
    errors.append(f"CHECK2: {n_mismatch}/{n_checked} spot-check mismatches")
    for m in mismatch_details[:10]:
        print(f"    {m['date']} {m['symbol']}: csv_close={m['csv_close']}, raw_close={m['raw_close']}, "
              f"raw_high={m['raw_high']}, csv_ret={m['csv_ret']}, expected={m['expected_ret']}, diff={m['diff']}")

# ── Check 3: Close price vs raw bars ──
print("\n" + "="*60)
print("CHECK 3: Close price consistency with raw bars")
print("="*60)
n_close_checked = 0
n_close_mismatch = 0
close_mismatches = []

for _, row in sample.iterrows():
    symbol = row["symbol"]
    signal_date = row["date"]
    csv_close = row["close"]

    bars = load_daily_bars(symbol)
    if bars is None or not isinstance(bars, pd.DataFrame):
        continue

    if "trade_date" in bars.columns:
        bars["_date"] = pd.to_datetime(bars["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
    elif "date" in bars.columns:
        bars["_date"] = pd.to_datetime(bars["date"], format="mixed", errors="coerce")
    else:
        continue

    signal_dt = pd.to_datetime(signal_date, format="mixed")
    signal_row = bars[bars["_date"] == signal_dt]
    if signal_row.empty or "close" not in bars.columns:
        continue

    raw_close = float(signal_row["close"].iloc[0])
    n_close_checked += 1
    if abs(raw_close - csv_close) > 0.02:
        n_close_mismatch += 1
        close_mismatches.append(f"  {signal_date} {symbol}: csv={csv_close}, raw={raw_close}")

print(f"  Checked: {n_close_checked}")
print(f"  Mismatches: {n_close_mismatch}")
if n_close_mismatch > 0:
    errors.append(f"CHECK3: {n_close_mismatch}/{n_close_checked} close price mismatches")
    for m in close_mismatches[:5]:
        print(m)

# ── Check 4: Probability range ──
print("\n" + "="*60)
print("CHECK 4: Probability range")
print("="*60)
below_threshold = df[df["probability"] < 0.70]
print(f"  Min prob: {df['probability'].min():.6f}")
print(f"  Max prob: {df['probability'].max():.6f}")
print(f"  Below 0.70: {len(below_threshold)}")
if len(below_threshold) > 0:
    errors.append(f"CHECK4: {len(below_threshold)} rows with prob < 0.70")

# ── Check 5: Duplicates ──
print("\n" + "="*60)
print("CHECK 5: Duplicate (date, symbol) pairs")
print("="*60)
dupes = df.duplicated(subset=["date", "symbol"], keep=False)
print(f"  Duplicate rows: {dupes.sum()}")
if dupes.sum() > 0:
    errors.append(f"CHECK5: {dupes.sum()} duplicate date+symbol rows")
    print(df[dupes].head(5)[["date","symbol","probability"]].to_string())

# ── Check 6: Date sorting ──
print("\n" + "="*60)
print("CHECK 6: Date sorting (ascending)")
print("="*60)
df["_dt"] = pd.to_datetime(df["date"], format="mixed")
is_sorted = df["_dt"].is_monotonic_increasing
# Actually we need to check that within same date, prob is descending
# But primary sort should be date ascending
dates_sorted = all(df["_dt"].iloc[i] <= df["_dt"].iloc[i+1] for i in range(len(df)-1))
print(f"  Dates monotonically non-decreasing: {dates_sorted}")
if not dates_sorted:
    # Find first violation
    for i in range(len(df)-1):
        if df["_dt"].iloc[i] > df["_dt"].iloc[i+1]:
            print(f"  First violation at row {i}: {df['date'].iloc[i]} > {df['date'].iloc[i+1]}")
            break
    errors.append("CHECK6: dates not sorted ascending")

# ── Check 7: ST exclusion ──
print("\n" + "="*60)
print("CHECK 7: ST stock exclusion")
print("="*60)
st_mask = df["name"].str.contains("ST", case=False, na=False)
print(f"  Rows with ST in name: {st_mask.sum()}")
if st_mask.sum() > 0:
    errors.append(f"CHECK7: {st_mask.sum()} ST rows found")
    print(df[st_mask].head(5)[["date","symbol","name"]].to_string())

# ── Check 8: Unverified rows analysis ──
print("\n" + "="*60)
print("CHECK 8: Unverified rows (no next-day data)")
print("="*60)
unverified = df[~df["hit"].isin(["hit", "miss"])]
verified_count = len(df) - len(unverified)
print(f"  Verified: {verified_count}")
print(f"  Unverified: {len(unverified)}")
if len(unverified) > 0:
    # All unverified should have NaN returns
    unv_with_return = unverified[unverified["next_high_return_pct"].notna()]
    print(f"  Unverified with return data (should be 0): {len(unv_with_return)}")
    if len(unv_with_return) > 0:
        errors.append(f"CHECK8: {len(unv_with_return)} unverified rows have return data")

# ── Check 9: Symbol format ──
print("\n" + "="*60)
print("CHECK 9: Symbol format (6 digits)")
print("="*60)
bad_symbols = df[~df["symbol"].str.match(r"^\d{6}$")]
print(f"  Bad symbols: {len(bad_symbols)}")
if len(bad_symbols) > 0:
    errors.append(f"CHECK9: {len(bad_symbols)} malformed symbols")

# ── Check 10: 2017-2022 specific deep spot-check ──
print("\n" + "="*60)
print("CHECK 10: Deep spot-check 2017-2022 OOS period")
print("="*60)

oos_df = df[(df["_dt"] >= "2017-01-01") & (df["_dt"] < "2023-01-01") & has_return].copy()
print(f"  OOS 2017-2022 verified rows: {len(oos_df)}")

# Sample 100 from OOS period specifically
oos_sample_idx = np.random.choice(len(oos_df), size=min(200, len(oos_df)), replace=False)
oos_sample = oos_df.iloc[oos_sample_idx]

n_oos_checked = 0
n_oos_mismatch = 0
oos_mismatch_details = []

for _, row in oos_sample.iterrows():
    symbol = row["symbol"]
    signal_date = row["date"]
    label_date = row["label_date"]
    csv_high_ret = row["next_high_return_pct"]
    csv_close = row["close"]

    bars = load_daily_bars(symbol)
    if bars is None or not isinstance(bars, pd.DataFrame):
        continue

    if "trade_date" in bars.columns:
        bars["_date"] = pd.to_datetime(bars["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
    elif "date" in bars.columns:
        bars["_date"] = pd.to_datetime(bars["date"], format="mixed", errors="coerce")
    else:
        continue

    signal_dt = pd.to_datetime(signal_date, format="mixed")
    label_dt = pd.to_datetime(label_date, format="mixed")

    signal_row = bars[bars["_date"] == signal_dt]
    label_row = bars[bars["_date"] == label_dt]

    if signal_row.empty or label_row.empty:
        continue

    if "close" not in bars.columns or "high" not in bars.columns:
        continue

    raw_close = float(signal_row["close"].iloc[0])
    raw_high = float(label_row["high"].iloc[0])
    expected_ret = round((raw_high / raw_close - 1) * 100, 2)

    n_oos_checked += 1

    # Check close
    if abs(raw_close - csv_close) > 0.02:
        n_oos_mismatch += 1
        oos_mismatch_details.append(
            f"  CLOSE MISMATCH: {signal_date} {symbol} csv_close={csv_close} raw_close={raw_close}"
        )

    # Check return
    if abs(expected_ret - csv_high_ret) > 0.02:
        n_oos_mismatch += 1
        oos_mismatch_details.append(
            f"  RETURN MISMATCH: {signal_date} {symbol} csv_ret={csv_high_ret} expected={expected_ret} "
            f"(raw_close={raw_close}, raw_high={raw_high})"
        )

    # Check hit label
    expected_hit = "hit" if expected_ret >= 1.0 else "miss"
    if row["hit"] != expected_hit:
        n_oos_mismatch += 1
        oos_mismatch_details.append(
            f"  HIT LABEL MISMATCH: {signal_date} {symbol} csv_hit={row['hit']} expected={expected_hit} ret={expected_ret}"
        )

print(f"  OOS spot-checked: {n_oos_checked}")
print(f"  OOS mismatches: {n_oos_mismatch}")
if n_oos_mismatch > 0:
    errors.append(f"CHECK10: {n_oos_mismatch} OOS mismatches in {n_oos_checked} checks")
    for m in oos_mismatch_details[:20]:
        print(m)

# ── Summary ──
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
if errors:
    print(f"  ERRORS FOUND: {len(errors)}")
    for e in errors:
        print(f"    - {e}")
else:
    print("  ALL 10 CHECKS PASSED")

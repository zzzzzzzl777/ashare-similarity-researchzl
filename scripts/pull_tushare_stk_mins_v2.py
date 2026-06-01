"""Tushare stk_mins 5min v2 — 按段遍历 + 重试到清零

Strategy: outer loop = 8 segments, inner loop = all stocks.
Each segment retries until all eligible stocks have data (max 10 rounds).
Cooldown only affects a few stocks per round, never loses entire stock data.
"""
import os
os.environ['http_proxy'] = 'http://127.0.0.1:7897'
os.environ['https_proxy'] = 'http://127.0.0.1:7897'

import tushare as ts
import pandas as pd
import time, json, sys
from datetime import datetime, date

ts.set_token('05ed8ff7dbeb572be350d12fc2f1a9c3483c7e837fcb6701151f10f2')
pro = ts.pro_api()
pro._DataApi__http_url = 'http://tsy.xiaodefa.cn'
pro._DataApi__timeout = 120

SAVE_DIR = r'E:\ashare_similarity_runtime\data\cache\prediction\tushare\stk_mins_5'
SEG_DIR = os.path.join(SAVE_DIR, '_segments')
SLEEP_INTERVAL = 6.0

SEGMENTS = [
    ('2023-01-03 09:30:00', '2023-06-01 15:00:00'),
    ('2023-06-02 09:30:00', '2023-11-01 15:00:00'),
    ('2023-11-02 09:30:00', '2024-04-01 15:00:00'),
    ('2024-04-02 09:30:00', '2024-09-01 15:00:00'),
    ('2024-09-02 09:30:00', '2025-02-01 15:00:00'),
    ('2025-02-02 09:30:00', '2025-07-01 15:00:00'),
    ('2025-07-02 09:30:00', '2025-12-01 15:00:00'),
    ('2025-12-02 09:30:00', '2026-05-02 15:00:00'),
]


def _get_stock_list():
    """Get mainboard stock list with retry."""
    print("Getting mainboard stock list...")
    for attempt in range(3):
        try:
            stock_list = pro.stock_basic(
                exchange='', list_status='L',
                fields='ts_code,symbol,name,market,list_date')
            break
        except Exception:
            if attempt < 2:
                print(f"  stock_basic timeout, retrying in 30s... ({attempt+1}/3)")
                time.sleep(30)
            else:
                raise
    mainboard = stock_list[stock_list['market'] == '主板']
    codes = sorted(mainboard['ts_code'].tolist())
    stock_info = dict(zip(mainboard['ts_code'], mainboard['list_date']))
    print(f"Total listed: {len(stock_list)}, mainboard: {len(mainboard)}")
    return codes, stock_info


def _eligible_for_segment(list_date_str, seg_end_str):
    """Stock is eligible if listed before segment end date."""
    list_date = datetime.strptime(str(list_date_str), '%Y%m%d').date()
    seg_end = datetime.strptime(seg_end_str[:10], '%Y-%m-%d').date()
    return list_date <= seg_end


def _detect_gaps(df):
    """Detect date gaps > 14 calendar days."""
    if df is None or df.empty:
        return [], 0
    df = df.copy()
    df['trade_time'] = pd.to_datetime(df['trade_time'], errors='coerce')
    dates = sorted(df['trade_time'].dt.date.unique())
    total_days = len(dates)
    gaps = []
    for j in range(1, len(dates)):
        calendar_gap = (dates[j] - dates[j - 1]).days
        if calendar_gap > 14:
            gaps.append({
                'from': str(dates[j - 1]),
                'to': str(dates[j]),
                'calendar_days': calendar_gap,
            })
    return gaps, total_days


def pull_by_segment():
    """Pull all stocks segment by segment, retrying until 100% coverage."""
    os.makedirs(SEG_DIR, exist_ok=True)
    codes, stock_info = _get_stock_list()
    time.sleep(SLEEP_INTERVAL)

    for seg_idx, (seg_start, seg_end) in enumerate(SEGMENTS):
        seg_path = os.path.join(SEG_DIR, f'seg_{seg_idx}')
        os.makedirs(seg_path, exist_ok=True)

        eligible = [c for c in codes
                    if _eligible_for_segment(stock_info[c], seg_end)]
        done = {f.replace('.parquet', '') for f in os.listdir(seg_path)
                if f.endswith('.parquet')}
        remaining = [c for c in eligible if c not in done]

        if not remaining:
            print(f"\n=== Segment {seg_idx} ({seg_start[:10]}~{seg_end[:10]}): "
                  f"already complete ({len(eligible)} stocks) ===")
            continue

        round_num = 0
        max_rounds = 10

        while remaining and round_num < max_rounds:
            round_num += 1
            print(f"\n=== Segment {seg_idx} Round {round_num}, "
                  f"remaining: {len(remaining)}/{len(eligible)} ===")

            still_empty = []
            consecutive_empties = 0

            for i, ts_code in enumerate(remaining):
                try:
                    df = pro.stk_mins(ts_code=ts_code, freq='5min',
                                       start_date=seg_start, end_date=seg_end)
                    time.sleep(SLEEP_INTERVAL)
                except Exception as e:
                    err_str = str(e).lower()
                    if any(kw in err_str for kw in
                           ['timeout', 'timed out', 'connection', '40203']):
                        print(f"  TIMEOUT at {ts_code}, sleeping 600s...")
                        time.sleep(600)
                        still_empty.append(ts_code)
                        still_empty.extend(remaining[i + 1:])
                        break
                    else:
                        still_empty.append(ts_code)
                        continue

                if df is not None and len(df) > 0:
                    df.to_parquet(
                        os.path.join(seg_path, f'{ts_code}.parquet'),
                        index=False)
                    consecutive_empties = 0
                else:
                    consecutive_empties += 1
                    still_empty.append(ts_code)

                    if consecutive_empties >= 5:
                        print(f"  5 consecutive empties at stock {i + 1}, "
                              f"cooldown detected. Sleeping 360s...")
                        time.sleep(360)
                        consecutive_empties = 0

                if (i + 1) % 20 == 0:
                    filled = i + 1 - len(still_empty)
                    print(f"  [{seg_idx}][R{round_num}] {i + 1}/{len(remaining)}, "
                          f"filled: {filled}, empty: {len(still_empty)}")
                    time.sleep(30)

            if still_empty:
                print(f"  Segment {seg_idx} Round {round_num} done, "
                      f"still empty: {len(still_empty)}, "
                      f"waiting 360s before retry...")
                time.sleep(360)

            remaining = still_empty

        if remaining:
            print(f"  WARNING: Segment {seg_idx} still has {len(remaining)} "
                  f"stocks after {max_rounds} rounds: {remaining[:10]}")
        else:
            print(f"  Segment {seg_idx} COMPLETE: "
                  f"all {len(eligible)} stocks filled.")


def merge_segments():
    """Merge all segment parquets into per-stock final parquets."""
    all_codes = set()
    for seg_idx in range(len(SEGMENTS)):
        seg_path = os.path.join(SEG_DIR, f'seg_{seg_idx}')
        if os.path.exists(seg_path):
            for f in os.listdir(seg_path):
                if f.endswith('.parquet'):
                    all_codes.add(f.replace('.parquet', ''))

    existing = {f.replace('.parquet', '') for f in os.listdir(SAVE_DIR)
                if f.endswith('.parquet')}
    all_codes |= existing

    print(f"Merging {len(all_codes)} stocks "
          f"from {len(SEGMENTS)} segments + {len(existing)} existing...")

    merged = 0
    for ts_code in sorted(all_codes):
        dfs = []

        existing_path = os.path.join(SAVE_DIR, f'{ts_code}.parquet')
        if os.path.exists(existing_path):
            try:
                dfs.append(pd.read_parquet(existing_path))
            except Exception:
                pass

        for seg_idx in range(len(SEGMENTS)):
            path = os.path.join(SEG_DIR, f'seg_{seg_idx}', f'{ts_code}.parquet')
            if os.path.exists(path):
                try:
                    dfs.append(pd.read_parquet(path))
                except Exception:
                    continue

        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            combined = combined.drop_duplicates(subset=['ts_code', 'trade_time'])
            combined = combined.sort_values('trade_time').reset_index(drop=True)
            combined.to_parquet(existing_path, index=False)
            merged += 1

    print(f"Merge complete: {merged} stocks written.")


def verify_and_patch():
    """Verify data completeness and report issues."""
    codes, stock_info = _get_stock_list()
    time.sleep(SLEEP_INTERVAL)

    issues = []
    total_rows = 0
    full = 0
    partial = 0
    missing = 0

    for ts_code in codes:
        path = os.path.join(SAVE_DIR, f'{ts_code}.parquet')
        list_date = datetime.strptime(str(stock_info[ts_code]), '%Y%m%d').date()

        if not os.path.exists(path):
            if list_date <= date(2026, 5, 1):
                issues.append((ts_code, 'missing'))
                missing += 1
            continue

        try:
            df = pd.read_parquet(path)
        except Exception:
            issues.append((ts_code, 'corrupt'))
            continue

        total_rows += len(df)
        gaps, total_days = _detect_gaps(df)

        expected_start = max(list_date, date(2023, 1, 3))
        expected_days = (date(2026, 5, 2) - expected_start).days * 0.69

        if total_days < expected_days * 0.8:
            issues.append((ts_code,
                           f'low_days:{total_days}/{expected_days:.0f}'))
            partial += 1
        elif gaps:
            for g in gaps:
                issues.append((ts_code,
                               f"gap:{g['from']}~{g['to']}"))
            partial += 1
        else:
            full += 1

    print(f"\n=== Verification ===")
    print(f"  Total stocks: {len(codes)}")
    print(f"  Full coverage: {full}")
    print(f"  Partial/gaps: {partial}")
    print(f"  Missing: {missing}")
    print(f"  Total rows: {total_rows:,}")
    if issues:
        print(f"  Issues ({len(issues)}):")
        for code, issue in issues[:20]:
            print(f"    {code}: {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")


def status():
    """Show per-segment completion status."""
    print("=== Segment Status ===")
    total_files = 0
    for seg_idx in range(len(SEGMENTS)):
        seg_path = os.path.join(SEG_DIR, f'seg_{seg_idx}')
        count = 0
        if os.path.exists(seg_path):
            count = len([f for f in os.listdir(seg_path)
                        if f.endswith('.parquet')])
        total_files += count
        start, end = SEGMENTS[seg_idx]
        print(f"  Segment {seg_idx} ({start[:10]}~{end[:10]}): {count} stocks")
    print(f"  Total segment files: {total_files}")

    existing = len([f for f in os.listdir(SAVE_DIR)
                   if f.endswith('.parquet')])
    print(f"  Final parquets: {existing}")


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if mode == 'pull':
        pull_by_segment()
    elif mode == 'merge':
        merge_segments()
    elif mode == 'verify':
        verify_and_patch()
    elif mode == 'status':
        status()
    elif mode == 'all':
        pull_by_segment()
        merge_segments()
        verify_and_patch()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python pull_tushare_stk_mins_v2.py "
              "[pull|merge|verify|status|all]")

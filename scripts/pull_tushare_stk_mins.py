"""Tushare stk_mins 5min — v2 按段拉取 + 三种冷却检测 + 保证100%完整"""
import os
os.environ['http_proxy'] = 'http://127.0.0.1:7897'
os.environ['https_proxy'] = 'http://127.0.0.1:7897'

import tushare as ts
import pandas as pd
import hashlib
import time, json, sys
from datetime import datetime, date, timedelta

ts.set_token('05ed8ff7dbeb572be350d12fc2f1a9c3483c7e837fcb6701151f10f2')
pro = ts.pro_api()
pro._DataApi__http_url = 'http://tsy.xiaodefa.cn'
pro._DataApi__timeout = 120

SAVE_DIR = r'E:\ashare_similarity_runtime\data\cache\prediction\tushare\stk_mins_5'
SEG_DIR = os.path.join(SAVE_DIR, '_segments')
LOG_FILE = os.path.join(SAVE_DIR, '_pull_log_v2.json')
SLEEP_INTERVAL = 6.0
ROW_LIMIT = 8000
EXPECTED_ROWS_PER_SEG = 4500
MAX_ROUNDS = 10
COOLDOWN_WAIT = 360
TIMEOUT_WAIT = 600
BATCH_SIZE = 20
BATCH_REST = 30
CONSECUTIVE_EMPTY_THRESHOLD = 3

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


# ─── 工具函数 ───

def get_stock_list():
    for attempt in range(3):
        try:
            stock_list = pro.stock_basic(
                exchange='', list_status='L',
                fields='ts_code,symbol,name,market,list_date')
            mainboard = stock_list[stock_list['market'] == '主板']
            codes = sorted(mainboard['ts_code'].tolist())
            stock_info = dict(zip(mainboard['ts_code'], mainboard['list_date']))
            print(f"Mainboard stocks: {len(codes)}")
            time.sleep(SLEEP_INTERVAL)
            return codes, stock_info
        except Exception:
            if attempt < 2:
                print(f"  stock_basic timeout, retry in 30s ({attempt+1}/3)")
                time.sleep(30)
            else:
                raise


def is_eligible(list_date_str, seg_end_str):
    """股票上市日期 <= segment 结束日期才可能有数据"""
    list_date = datetime.strptime(list_date_str, '%Y%m%d').date()
    seg_end = datetime.strptime(seg_end_str[:10], '%Y-%m-%d').date()
    return list_date <= seg_end


def expected_rows(list_date_str, seg_start_str, seg_end_str):
    """估算该股票在该段的期望行数"""
    list_date = datetime.strptime(list_date_str, '%Y%m%d').date()
    seg_start = datetime.strptime(seg_start_str[:10], '%Y-%m-%d').date()
    seg_end = datetime.strptime(seg_end_str[:10], '%Y-%m-%d').date()
    actual_start = max(list_date, seg_start)
    if actual_start >= seg_end:
        return 0
    cal_days = (seg_end - actual_start).days
    return max(int(cal_days * 0.69 * 49), 200)


def is_segment_complete(df, list_date_str, seg_start_str, seg_end_str):
    """判断返回数据是否完整（不只是非空）"""
    if df is None or len(df) == 0:
        return False
    exp = expected_rows(list_date_str, seg_start_str, seg_end_str)
    if exp <= 0:
        return True
    if len(df) < exp * 0.4:
        return False
    return True


def is_timeout_error(e):
    err = str(e).lower()
    return any(kw in err for kw in ['timeout', 'timed out', 'connection', '40203', '\xc6\xb5'])


def pull_single(ts_code, seg_start, seg_end):
    """拉取单只股票的单个 segment，带 8000 行截断保护"""
    df = pro.stk_mins(ts_code=ts_code, freq='5min',
                      start_date=seg_start, end_date=seg_end)
    time.sleep(SLEEP_INTERVAL)

    if df is None or df.empty:
        return pd.DataFrame()

    if len(df) >= ROW_LIMIT:
        from datetime import datetime as dt
        s = dt.strptime(seg_start, '%Y-%m-%d %H:%M:%S')
        e = dt.strptime(seg_end, '%Y-%m-%d %H:%M:%S')
        mid = s + (e - s) / 2
        mid_date = mid.strftime('%Y-%m-%d')
        df1 = pro.stk_mins(ts_code=ts_code, freq='5min',
                           start_date=seg_start,
                           end_date=f'{mid_date} 15:00:00')
        time.sleep(SLEEP_INTERVAL)
        df2 = pro.stk_mins(ts_code=ts_code, freq='5min',
                           start_date=f'{mid_date} 09:30:00',
                           end_date=seg_end)
        time.sleep(SLEEP_INTERVAL)
        parts = [x for x in [df1, df2] if x is not None and not x.empty]
        if parts:
            df = pd.concat(parts, ignore_index=True)
            df = df.drop_duplicates(subset=['ts_code', 'trade_time'])

    return df


# ─── 进度管理 ───

def load_progress():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'version': 'v2',
        'completed_segments': {},
        'daily_requests': 0,
        'daily_date': None,
        'total_requests': 0,
        'errors': [],
    }


def save_progress(progress):
    progress['last_update'] = datetime.now().isoformat()
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


# ─── 核心拉取逻辑 ───

def pull_by_segment():
    os.makedirs(SAVE_DIR, exist_ok=True)
    os.makedirs(SEG_DIR, exist_ok=True)

    codes, stock_info = get_stock_list()
    progress = load_progress()

    today = date.today().isoformat()
    if progress.get('daily_date') != today:
        progress['daily_date'] = today
        progress['daily_requests'] = 0

    v1_complete = {}
    print("Pre-scanning existing v1 parquets for complete segments...")
    for f in os.listdir(SAVE_DIR):
        if not f.endswith('.parquet') or f.startswith('_'):
            continue
        code = f.replace('.parquet', '')
        if code not in stock_info:
            continue
        try:
            df = pd.read_parquet(os.path.join(SAVE_DIR, f))
            df['trade_time'] = pd.to_datetime(df['trade_time'])
            complete_segs = set()
            for sidx, (ss, se) in enumerate(SEGMENTS):
                if not is_eligible(stock_info[code], se):
                    continue
                mask = (df['trade_time'] >= ss) & (df['trade_time'] <= se)
                seg_data = df[mask]
                if is_segment_complete(seg_data, stock_info[code], ss, se):
                    complete_segs.add(sidx)
            v1_complete[code] = complete_segs
        except Exception:
            pass
    print(f"  Pre-scanned {len(v1_complete)} v1 parquets")

    for seg_idx, (seg_start, seg_end) in enumerate(SEGMENTS):
        seg_key = f'seg_{seg_idx}'
        seg_path = os.path.join(SEG_DIR, seg_key)
        os.makedirs(seg_path, exist_ok=True)

        eligible = [c for c in codes if is_eligible(stock_info[c], seg_end)]

        done = set()
        for f in os.listdir(seg_path):
            if not f.endswith('.parquet'):
                continue
            code = f.replace('.parquet', '')
            if code not in stock_info:
                done.add(code)
                continue
            try:
                df = pd.read_parquet(os.path.join(seg_path, f))
                if is_segment_complete(df, stock_info[code], seg_start, seg_end):
                    done.add(code)
            except Exception:
                pass

        for code in eligible:
            if code not in done and seg_idx in v1_complete.get(code, set()):
                done.add(code)

        remaining = [c for c in eligible if c not in done]

        if not remaining:
            print(f"Segment {seg_idx} ({seg_start[:10]}~{seg_end[:10]}): "
                  f"all {len(eligible)} stocks complete, skipping.")
            continue

        print(f"\n{'='*60}")
        print(f"Segment {seg_idx} ({seg_start[:10]}~{seg_end[:10]}): "
              f"{len(eligible)} eligible, {len(done)} done, {len(remaining)} remaining")

        round_num = 0
        current_wait = COOLDOWN_WAIT
        while remaining and round_num < MAX_ROUNDS:
            round_num += 1
            print(f"\n--- Seg {seg_idx} Round {round_num}, "
                  f"remaining: {len(remaining)} ---")

            still_need = []
            consecutive_empties = 0
            pulled_this_round = 0

            for i, ts_code in enumerate(remaining):
                try:
                    df = pull_single(ts_code, seg_start, seg_end)
                    progress['daily_requests'] += 1
                    progress['total_requests'] += 1
                    pulled_this_round += 1

                except Exception as e:
                    if is_timeout_error(e):
                        print(f"  TIMEOUT at {ts_code}, "
                              f"sleeping {TIMEOUT_WAIT}s...")
                        progress['errors'].append({
                            'type': 'timeout',
                            'stock': ts_code,
                            'seg': seg_idx,
                            'time': datetime.now().isoformat(),
                        })
                        if len(progress['errors']) > 200:
                            progress['errors'] = progress['errors'][-200:]
                        save_progress(progress)
                        time.sleep(TIMEOUT_WAIT)
                        still_need.append(ts_code)
                        still_need.extend(remaining[i+1:])
                        break
                    else:
                        still_need.append(ts_code)
                        continue

                if df.empty:
                    consecutive_empties += 1
                    still_need.append(ts_code)
                elif not is_segment_complete(
                        df, stock_info[ts_code], seg_start, seg_end):
                    consecutive_empties += 1
                    still_need.append(ts_code)
                    print(f"  {ts_code} partial: {len(df)} rows "
                          f"(expected ~{expected_rows(stock_info[ts_code], seg_start, seg_end)})")
                else:
                    df.to_parquet(
                        os.path.join(seg_path, f'{ts_code}.parquet'),
                        index=False)
                    consecutive_empties = 0

                if consecutive_empties >= CONSECUTIVE_EMPTY_THRESHOLD:
                    print(f"  {consecutive_empties} consecutive incomplete, "
                          f"cooldown detected. Sleeping {COOLDOWN_WAIT}s...")
                    save_progress(progress)
                    time.sleep(COOLDOWN_WAIT)
                    still_need.extend(remaining[i+1:])
                    break

                if pulled_this_round % BATCH_SIZE == 0 and pulled_this_round > 0:
                    print(f"  [Seg{seg_idx}][R{round_num}] "
                          f"pulled {pulled_this_round}, "
                          f"pending retry: {len(still_need)}")
                    time.sleep(BATCH_REST)

            if still_need:
                if len(still_need) >= len(remaining):
                    current_wait = min(current_wait * 2, 3600)
                else:
                    current_wait = COOLDOWN_WAIT
                print(f"  Round {round_num} done. "
                      f"Still need: {len(still_need)}. "
                      f"Waiting {current_wait}s before next round...")
                save_progress(progress)
                time.sleep(current_wait)
            else:
                print(f"  Round {round_num} done. "
                      f"Segment {seg_idx} COMPLETE!")

            remaining = still_need

        if remaining:
            print(f"  WARNING: Segment {seg_idx} still has "
                  f"{len(remaining)} stocks after {MAX_ROUNDS} rounds")
            print(f"  Remaining: {remaining[:20]}")

        save_progress(progress)
        print(f"Segment {seg_idx} finished. "
              f"Total requests today: {progress['daily_requests']}")

    save_progress(progress)
    print(f"\nAll segments done. "
          f"Total requests: {progress['total_requests']}")


# ─── 合并 ───

def merge():
    """把 _segments/ 里的段级 parquet 合并成每股一个最终 parquet，
    同时合并 v1 已有的 parquet"""
    all_codes = set()

    for seg_idx in range(len(SEGMENTS)):
        seg_path = os.path.join(SEG_DIR, f'seg_{seg_idx}')
        if not os.path.exists(seg_path):
            continue
        for f in os.listdir(seg_path):
            if f.endswith('.parquet'):
                all_codes.add(f.replace('.parquet', ''))

    for f in os.listdir(SAVE_DIR):
        if f.endswith('.parquet') and f[0] != '_':
            all_codes.add(f.replace('.parquet', ''))

    print(f"Merging {len(all_codes)} stocks...")

    merged_count = 0
    total_rows = 0

    for ts_code in sorted(all_codes):
        dfs = []

        for seg_idx in range(len(SEGMENTS)):
            path = os.path.join(SEG_DIR, f'seg_{seg_idx}',
                                f'{ts_code}.parquet')
            if os.path.exists(path):
                try:
                    dfs.append(pd.read_parquet(path))
                except Exception:
                    pass

        v1_path = os.path.join(SAVE_DIR, f'{ts_code}.parquet')
        if os.path.exists(v1_path):
            try:
                dfs.append(pd.read_parquet(v1_path))
            except Exception:
                pass

        if not dfs:
            continue

        combined = pd.concat(dfs, ignore_index=True)
        combined = combined.drop_duplicates(
            subset=['ts_code', 'trade_time'])
        combined = combined.sort_values('trade_time').reset_index(drop=True)
        combined.to_parquet(
            os.path.join(SAVE_DIR, f'{ts_code}.parquet'), index=False)

        merged_count += 1
        total_rows += len(combined)

    print(f"Merged {merged_count} stocks, {total_rows:,} total rows.")


# ─── 修复现有 parquet 的段级缺失 ───

def scan_repair_needs(codes, stock_info):
    """扫描现有 parquet，找出需要补拉的 (stock, segment_idx) 对"""
    repair = {}

    for ts_code in codes:
        path = os.path.join(SAVE_DIR, f'{ts_code}.parquet')
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_parquet(path)
        except Exception:
            continue

        df['trade_time'] = pd.to_datetime(df['trade_time'])

        for seg_idx, (seg_start, seg_end) in enumerate(SEGMENTS):
            if not is_eligible(stock_info.get(ts_code, '19900101'), seg_end):
                continue

            mask = ((df['trade_time'] >= seg_start) &
                    (df['trade_time'] <= seg_end))
            seg_data = df[mask]

            if not is_segment_complete(
                    seg_data, stock_info.get(ts_code, '19900101'),
                    seg_start, seg_end):
                repair.setdefault(seg_idx, []).append(ts_code)

    total = sum(len(v) for v in repair.values())
    print(f"Scan complete: {total} (stock, segment) pairs need repair")
    for seg_idx in sorted(repair.keys()):
        print(f"  Seg {seg_idx}: {len(repair[seg_idx])} stocks")

    return repair


def repair_segments():
    """补拉现有 parquet 中缺失/截断的段"""
    codes, stock_info = get_stock_list()
    repair = scan_repair_needs(codes, stock_info)

    if not repair:
        print("No repair needed.")
        return

    os.makedirs(SEG_DIR, exist_ok=True)
    progress = load_progress()

    for seg_idx in sorted(repair.keys()):
        seg_start, seg_end = SEGMENTS[seg_idx]
        seg_path = os.path.join(SEG_DIR, f'seg_{seg_idx}')
        os.makedirs(seg_path, exist_ok=True)

        remaining = repair[seg_idx]

        still_need = []
        for ts_code in remaining:
            existing = os.path.join(seg_path, f'{ts_code}.parquet')
            if os.path.exists(existing):
                try:
                    df = pd.read_parquet(existing)
                    if is_segment_complete(
                            df, stock_info[ts_code],
                            seg_start, seg_end):
                        continue
                except Exception:
                    pass
            still_need.append(ts_code)

        if not still_need:
            print(f"Seg {seg_idx} repair: all already fixed in _segments/")
            continue

        print(f"\nRepairing Seg {seg_idx}: {len(still_need)} stocks")

        round_num = 0
        current_wait = COOLDOWN_WAIT
        while still_need and round_num < MAX_ROUNDS:
            round_num += 1
            new_remaining = []
            consecutive_empties = 0

            for i, ts_code in enumerate(still_need):
                try:
                    df = pull_single(ts_code, seg_start, seg_end)
                    progress['total_requests'] += 1
                except Exception as e:
                    if is_timeout_error(e):
                        print(f"  TIMEOUT, sleeping {TIMEOUT_WAIT}s...")
                        time.sleep(TIMEOUT_WAIT)
                        new_remaining.append(ts_code)
                        new_remaining.extend(still_need[i+1:])
                        break
                    else:
                        new_remaining.append(ts_code)
                        continue

                if df.empty or not is_segment_complete(
                        df, stock_info[ts_code], seg_start, seg_end):
                    consecutive_empties += 1
                    new_remaining.append(ts_code)
                    if consecutive_empties >= CONSECUTIVE_EMPTY_THRESHOLD:
                        print(f"  Cooldown detected, sleeping {COOLDOWN_WAIT}s...")
                        time.sleep(COOLDOWN_WAIT)
                        new_remaining.extend(still_need[i+1:])
                        break
                else:
                    df.to_parquet(
                        os.path.join(seg_path, f'{ts_code}.parquet'),
                        index=False)
                    consecutive_empties = 0

            if new_remaining:
                if len(new_remaining) >= len(still_need):
                    current_wait = min(current_wait * 2, 3600)
                else:
                    current_wait = COOLDOWN_WAIT
                print(f"  Round done. Still need: {len(new_remaining)}. Waiting {current_wait}s...")
                time.sleep(current_wait)
            still_need = new_remaining

        save_progress(progress)

    print("Repair complete.")


# ─── 验证 ───

def verify():
    """最终验证：每只主板股票是否数据完整"""
    codes, stock_info = get_stock_list()

    missing_stocks = []
    incomplete_stocks = []
    good = 0

    for ts_code in codes:
        path = os.path.join(SAVE_DIR, f'{ts_code}.parquet')
        if not os.path.exists(path):
            missing_stocks.append(ts_code)
            continue

        try:
            df = pd.read_parquet(path)
        except Exception:
            missing_stocks.append(ts_code)
            continue

        df['trade_time'] = pd.to_datetime(df['trade_time'])

        bad_segs = []
        for seg_idx, (seg_start, seg_end) in enumerate(SEGMENTS):
            if not is_eligible(stock_info[ts_code], seg_end):
                continue
            mask = ((df['trade_time'] >= seg_start) &
                    (df['trade_time'] <= seg_end))
            seg_data = df[mask]
            if not is_segment_complete(
                    seg_data, stock_info[ts_code], seg_start, seg_end):
                bad_segs.append(seg_idx)

        if bad_segs:
            incomplete_stocks.append((ts_code, bad_segs))
        else:
            good += 1

    print(f"\n{'='*60}")
    print(f"Verification Report")
    print(f"  Total mainboard: {len(codes)}")
    print(f"  Complete: {good}")
    print(f"  Missing (no file): {len(missing_stocks)}")
    print(f"  Incomplete (segment gaps): {len(incomplete_stocks)}")

    if missing_stocks:
        print(f"\n  Missing stocks (first 20): {missing_stocks[:20]}")
    if incomplete_stocks:
        print(f"\n  Incomplete stocks (first 20):")
        for ts_code, segs in incomplete_stocks[:20]:
            print(f"    {ts_code}: missing segs {segs}")

    return missing_stocks, incomplete_stocks


# ─── 状态报告 ───

def status():
    """打印当前拉取状态"""
    progress = load_progress()
    parquets = len([f for f in os.listdir(SAVE_DIR)
                    if f.endswith('.parquet') and f[0] != '_'])
    seg_counts = {}
    for seg_idx in range(len(SEGMENTS)):
        seg_path = os.path.join(SEG_DIR, f'seg_{seg_idx}')
        if os.path.exists(seg_path):
            seg_counts[seg_idx] = len([
                f for f in os.listdir(seg_path)
                if f.endswith('.parquet')])
        else:
            seg_counts[seg_idx] = 0

    print(f"time: {datetime.now().isoformat()}")
    print(f"final parquets: {parquets}")
    print(f"total_requests: {progress.get('total_requests', 0)}")
    print(f"daily_requests: {progress.get('daily_requests', 0)} "
          f"(date: {progress.get('daily_date', 'N/A')})")
    print(f"segment parquets:")
    for i in range(len(SEGMENTS)):
        print(f"  seg_{i}: {seg_counts.get(i, 0)}")
    print(f"errors: {len(progress.get('errors', []))}")


# ─── CLI ───

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if mode == 'pull':
        pull_by_segment()
    elif mode == 'repair':
        repair_segments()
    elif mode == 'merge':
        merge()
    elif mode == 'verify':
        verify()
    elif mode == 'status':
        status()
    elif mode == 'all':
        repair_segments()
        pull_by_segment()
        merge()
        missing, incomplete = verify()
        if missing or incomplete:
            print(f"\nStill have gaps. Run again: python {sys.argv[0]} all")
        else:
            print("\n100% COMPLETE!")
    else:
        print("Usage: python pull_tushare_stk_mins.py "
              "[pull|repair|merge|verify|status|all]")

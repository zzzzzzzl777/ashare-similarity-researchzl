"""Tushare P1 - 同花顺热度 ths_hot + ths_daily + ths_member"""
import tushare as ts
import pandas as pd
import os, time, json
from datetime import datetime

ts.set_token('05ed8ff7dbeb572be350d12fc2f1a9c3483c7e837fcb6701151f10f2')
pro = ts.pro_api()
pro._DataApi__http_url = 'http://tsy.xiaodefa.cn'

BASE_DIR = r'E:\ashare_similarity_runtime\data\cache\prediction\tushare'

def get_trade_dates(start='20230101', end='20260502'):
    df = pro.trade_cal(exchange='SSE', start_date=start, end_date=end, is_open='1')
    return sorted(df['cal_date'].tolist())

def load_progress(log_file):
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            return json.load(f)
    return {'completed_dates': [], 'total_rows': 0, 'last_update': None}

def save_progress(progress, log_file):
    progress['last_update'] = datetime.now().isoformat()
    with open(log_file, 'w') as f:
        json.dump(progress, f, indent=2)

def pull_by_date(api_name, api_func):
    save_dir = os.path.join(BASE_DIR, api_name)
    log_file = os.path.join(save_dir, '_pull_log.json')
    dates = get_trade_dates()
    progress = load_progress(log_file)
    done = set(progress['completed_dates'])
    remaining = [d for d in dates if d not in done]
    print(f"{api_name}: done {len(done)}, remaining {len(remaining)}")

    errors = 0
    for i, td in enumerate(remaining):
        try:
            df = api_func(trade_date=td)
            if df is not None and len(df) > 0:
                df.to_parquet(os.path.join(save_dir, f'{td}.parquet'), index=False)
                progress['total_rows'] += len(df)
            progress['completed_dates'].append(td)
            if (i + 1) % 50 == 0:
                save_progress(progress, log_file)
                print(f"[{i+1}/{len(remaining)}] {td}, total: {progress['total_rows']}")
            time.sleep(0.55)
            errors = 0
        except Exception as e:
            errors += 1
            print(f"[{i+1}] {td} ERROR: {str(e)[:100]}")
            if errors >= 5:
                save_progress(progress, log_file)
                print(f"{api_name}: too many errors, stopping")
                return
            time.sleep(2 ** errors)
    save_progress(progress, log_file)
    print(f"{api_name} done! Total: {progress['total_rows']}")

def pull_ths_member():
    save_dir = os.path.join(BASE_DIR, 'ths_member')
    log_file = os.path.join(save_dir, '_pull_log.json')
    progress = load_progress(log_file)

    print("Getting concept list from ths_index()...")
    concept_list = pro.ths_index()
    print(f"Total concepts: {len(concept_list)}")
    time.sleep(0.55)

    done = set(progress.get('completed_codes', []))
    if 'completed_codes' not in progress:
        progress['completed_codes'] = []

    all_dfs = []
    errors = 0
    remaining = [row for _, row in concept_list.iterrows() if row['ts_code'] not in done]
    print(f"ths_member: done {len(done)}, remaining {len(remaining)}")

    for i, row in enumerate(remaining):
        try:
            df = pro.ths_member(ts_code=row['ts_code'])
            if df is not None and len(df) > 0:
                all_dfs.append(df)
                progress['total_rows'] = progress.get('total_rows', 0) + len(df)
            progress['completed_codes'].append(row['ts_code'])
            if (i + 1) % 100 == 0:
                save_progress(progress, log_file)
                print(f"[{i+1}/{len(remaining)}] {row['ts_code']} {row['name']}, total: {progress['total_rows']}")
            time.sleep(0.55)
            errors = 0
        except Exception as e:
            errors += 1
            print(f"[{i+1}] {row['ts_code']} ERROR: {str(e)[:100]}")
            if errors >= 5:
                save_progress(progress, log_file)
                print("ths_member: too many errors, stopping")
                if all_dfs:
                    pd.concat(all_dfs, ignore_index=True).to_parquet(
                        os.path.join(save_dir, 'all_members_partial.parquet'), index=False)
                return
            time.sleep(2 ** errors)

    if all_dfs:
        merged = pd.concat(all_dfs, ignore_index=True)
        merged.to_parquet(os.path.join(save_dir, 'all_members.parquet'), index=False)
        print(f"ths_member done! Saved {len(merged)} rows to all_members.parquet")

    save_progress(progress, log_file)

if __name__ == '__main__':
    pull_by_date('ths_hot', pro.ths_hot)
    pull_by_date('ths_daily', pro.ths_daily)
    pull_ths_member()

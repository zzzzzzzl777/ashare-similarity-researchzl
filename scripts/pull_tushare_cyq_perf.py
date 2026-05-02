"""Tushare P2 - 筹码分布 cyq_perf，按股票逐个拉取"""
import tushare as ts
import pandas as pd
import os, time, json
from datetime import datetime

ts.set_token('05ed8ff7dbeb572be350d12fc2f1a9c3483c7e837fcb6701151f10f2')
pro = ts.pro_api()
pro._DataApi__http_url = 'http://tsy.xiaodefa.cn'

SAVE_DIR = r'E:\ashare_similarity_runtime\data\cache\prediction\tushare\cyq_perf'
LOG_FILE = os.path.join(SAVE_DIR, '_pull_log.json')

def load_progress():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return {'completed_codes': [], 'total_rows': 0, 'last_update': None}

def save_progress(progress):
    progress['last_update'] = datetime.now().isoformat()
    with open(LOG_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def pull():
    print("Getting stock list...")
    stock_list = pro.stock_basic(exchange='', list_status='L',
        fields='ts_code,symbol,name,area,industry,market,list_date')
    mainboard = stock_list[stock_list['market'] == '主板']
    print(f"Total listed: {len(stock_list)}, mainboard: {len(mainboard)}")
    time.sleep(0.55)

    progress = load_progress()
    done = set(progress['completed_codes'])
    remaining = [c for c in mainboard['ts_code'].tolist() if c not in done]
    print(f"cyq_perf: done {len(done)}, remaining {len(remaining)}")

    errors = 0
    for i, ts_code in enumerate(remaining):
        try:
            df = pro.cyq_perf(ts_code=ts_code, start_date='20230101', end_date='20260502')
            if df is not None and len(df) > 0:
                df.to_parquet(os.path.join(SAVE_DIR, f'{ts_code}.parquet'), index=False)
                progress['total_rows'] += len(df)
            progress['completed_codes'].append(ts_code)
            if (i + 1) % 100 == 0:
                save_progress(progress)
                print(f"[{i+1}/{len(remaining)}] {ts_code}, total: {progress['total_rows']}")
            time.sleep(0.55)
            errors = 0
        except Exception as e:
            errors += 1
            print(f"[{i+1}] {ts_code} ERROR: {str(e)[:100]}")
            if errors >= 5:
                save_progress(progress)
                print("Too many errors, stopping")
                return
            time.sleep(2 ** errors)
    save_progress(progress)
    print(f"cyq_perf done! Total: {progress['total_rows']}")

if __name__ == '__main__':
    pull()

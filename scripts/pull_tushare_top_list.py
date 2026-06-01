"""Tushare P0 - 龙虎榜 top_list + top_inst，按交易日拉取"""
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

def pull_api(api_name, api_func):
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

if __name__ == '__main__':
    pull_api('top_list', pro.top_list)
    pull_api('top_inst', pro.top_inst)

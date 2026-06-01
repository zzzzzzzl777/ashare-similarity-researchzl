"""
Tushare P0 数据拉取脚本 - 按日期拉取个股资金流向 moneyflow
按交易日拉取，每日一个请求，存 parquet
"""
import tushare as ts
import pandas as pd
import os
import time
import json
from datetime import datetime

# 连接
ts.set_token('05ed8ff7dbeb572be350d12fc2f1a9c3483c7e837fcb6701151f10f2')
pro = ts.pro_api()
pro._DataApi__http_url = 'http://tsy.xiaodefa.cn'

SAVE_DIR = r'E:\ashare_similarity_runtime\data\cache\prediction\tushare\moneyflow'
LOG_FILE = os.path.join(SAVE_DIR, '_pull_log.json')

def get_trade_dates(start='20230101', end='20260502'):
    """获取交易日历"""
    df = pro.trade_cal(exchange='SSE', start_date=start, end_date=end, is_open='1')
    return sorted(df['cal_date'].tolist())

def load_progress():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return {'completed_dates': [], 'total_rows': 0, 'last_update': None}

def save_progress(progress):
    progress['last_update'] = datetime.now().isoformat()
    with open(LOG_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def pull_moneyflow():
    print("Getting trade dates...")
    dates = get_trade_dates()
    print(f"Total trade dates: {len(dates)}")

    progress = load_progress()
    done = set(progress['completed_dates'])
    remaining = [d for d in dates if d not in done]
    print(f"Already done: {len(done)}, remaining: {len(remaining)}")

    errors = 0
    for i, trade_date in enumerate(remaining):
        try:
            df = pro.moneyflow(trade_date=trade_date)
            if df is not None and len(df) > 0:
                fpath = os.path.join(SAVE_DIR, f'{trade_date}.parquet')
                df.to_parquet(fpath, index=False)
                progress['total_rows'] += len(df)

            progress['completed_dates'].append(trade_date)

            if (i + 1) % 50 == 0:
                save_progress(progress)
                print(f"[{i+1}/{len(remaining)}] {trade_date} done, total rows: {progress['total_rows']}")

            time.sleep(0.55)
            errors = 0

        except Exception as e:
            err_msg = str(e)
            errors += 1
            print(f"[{i+1}] {trade_date} ERROR: {err_msg[:100]}")
            if errors >= 5:
                print("Too many consecutive errors, saving and stopping")
                save_progress(progress)
                return
            time.sleep(2 ** errors)

    save_progress(progress)
    print(f"\nMoneyflow pull complete! Total dates: {len(progress['completed_dates'])}, total rows: {progress['total_rows']}")

if __name__ == '__main__':
    pull_moneyflow()

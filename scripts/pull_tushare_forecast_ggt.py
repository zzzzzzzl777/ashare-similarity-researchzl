"""Tushare forecast_vip + ggt_top10 — 按交易日拉取（次优先级，stk_mins 完成后再跑）"""
import tushare as ts
import pandas as pd
import hashlib
import os, time, json
from datetime import datetime, date

ts.set_token('05ed8ff7dbeb572be350d12fc2f1a9c3483c7e837fcb6701151f10f2')
pro = ts.pro_api()
pro._DataApi__http_url = 'http://tsy.xiaodefa.cn'

BASE_DIR = r'E:\ashare_similarity_runtime\data\cache\prediction\tushare'
SLEEP_INTERVAL = 0.6


def get_trade_dates(start='20230101', end=None):
    if end is None:
        end = date.today().strftime('%Y%m%d')
    df = pro.trade_cal(exchange='SSE', start_date=start, end_date=end, is_open='1')
    time.sleep(SLEEP_INTERVAL)
    return sorted(df['cal_date'].tolist())


def _manifest_template(api_name):
    return {
        'api': api_name,
        'completed_dates': [],
        'symbol_count': 0,
        'rows': 0,
        'date_range': {'min': None, 'max': None},
        'captured_at': None,
        'error_count': 0,
        'fingerprint': None,
        'last_update': None,
    }


def load_progress(log_file, api_name):
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        tpl = _manifest_template(api_name)
        tpl.update(data)
        return tpl
    return _manifest_template(api_name)


def save_progress(progress, log_file):
    progress['last_update'] = datetime.now().isoformat()
    progress['captured_at'] = datetime.now().isoformat()
    dates = progress['completed_dates']
    if dates:
        progress['date_range'] = {'min': min(dates), 'max': max(dates)}
    date_str = ','.join(sorted(dates[-20:]))
    progress['fingerprint'] = hashlib.sha256(
        f"{progress['api']}_{progress['rows']}_{date_str}".encode()
    ).hexdigest()[:16]
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)


def pull_by_date(api_name, api_func, date_param='trade_date'):
    save_dir = os.path.join(BASE_DIR, api_name)
    os.makedirs(save_dir, exist_ok=True)
    log_file = os.path.join(save_dir, '_pull_log.json')

    dates = get_trade_dates()
    progress = load_progress(log_file, api_name)
    done = set(progress['completed_dates'])
    remaining = [d for d in dates if d not in done]
    print(f"\n{api_name}: done {len(done)}, remaining {len(remaining)}")

    errors = 0
    for i, td in enumerate(remaining):
        try:
            df = api_func(**{date_param: td})
            if df is not None and len(df) > 0:
                df.to_parquet(os.path.join(save_dir, f'{td}.parquet'), index=False)
                progress['rows'] += len(df)
                progress['symbol_count'] = max(
                    progress['symbol_count'],
                    df['ts_code'].nunique() if 'ts_code' in df.columns else 0
                )
            progress['completed_dates'].append(td)
            if (i + 1) % 50 == 0:
                save_progress(progress, log_file)
                print(f"  [{i+1}/{len(remaining)}] {td}, rows: {progress['rows']}, "
                      f"errors: {progress['error_count']}")
            time.sleep(SLEEP_INTERVAL)
            errors = 0
        except Exception as e:
            errors += 1
            progress['error_count'] += 1
            err_str = str(e)
            print(f"  [{i+1}] {td} ERROR: {err_str[:100]}")
            if '40203' in err_str:
                print(f"  Rate limited, sleeping 60s...")
                time.sleep(60)
            elif errors >= 5:
                save_progress(progress, log_file)
                print(f"  Too many errors on {api_name}, stopping")
                return
            else:
                time.sleep(2 ** errors)
    save_progress(progress, log_file)
    print(f"{api_name} done! Rows: {progress['rows']}, errors: {progress['error_count']}")


def main():
    print("=== forecast_vip (by ann_date) ===")
    pull_by_date('forecast_vip', pro.forecast_vip, date_param='ann_date')

    print("\n=== ggt_top10 (by trade_date) ===")
    pull_by_date('ggt_top10', pro.ggt_top10, date_param='trade_date')


if __name__ == '__main__':
    main()

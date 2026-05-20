"""Backfill tushare data for 2020-05-15 ~ 2020-07-31 (with warmup for rolling features).

Pulls: limit_list_d, stk_limit, ths_daily, daily_basic, moneyflow, margin,
       cyq_perf, stk_mins_5, stk_auction_o, stk_auction_c, top_list, top_inst
"""
import tushare as ts
import pandas as pd
import os, time, json, sys
from pathlib import Path
from datetime import datetime

TUSHARE_TOKEN = (os.environ.get("TUSHARE_TOKEN") or os.environ.get("TSY_TUSHARE_TOKEN") or "").strip()
if not TUSHARE_TOKEN:
    raise RuntimeError("Missing TUSHARE_TOKEN or TSY_TUSHARE_TOKEN")
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()
pro._DataApi__http_url = 'http://tsy.xiaodefa.cn'
pro._DataApi__timeout = 120

TUSHARE_DIR = Path(r'E:\ashare_similarity_runtime\data\cache\prediction\tushare')
START_DATE = '20200515'
END_DATE = '20200731'
SLEEP = 0.6


def get_trade_dates():
    df = pro.trade_cal(exchange='SSE', start_date=START_DATE, end_date=END_DATE, is_open='1')
    time.sleep(SLEEP)
    return sorted(df['cal_date'].tolist())


def get_stock_list():
    sl = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,market,list_date')
    time.sleep(SLEEP)
    # Include stocks listed before 2020-07-31
    sl = sl[sl['list_date'] <= END_DATE]
    print(f"Stocks listed by {END_DATE}: {len(sl)}")
    return sl


# ──── Per-date pullers ────

def pull_per_date(api_name, save_subdir, trade_dates, extra_params=None):
    save_dir = TUSHARE_DIR / save_subdir
    save_dir.mkdir(parents=True, exist_ok=True)

    existing = {f.stem for f in save_dir.glob('*.parquet') if not f.name.startswith('_')}
    todo = [d for d in trade_dates if d not in existing]
    print(f"\n[{api_name}] Total dates: {len(trade_dates)}, existing: {len(existing)}, todo: {len(todo)}")

    errors = 0
    for i, td in enumerate(todo):
        try:
            params = {'trade_date': td}
            if extra_params:
                params.update(extra_params)
            df = getattr(pro, api_name)(**params)
            if df is not None and len(df) > 0:
                df.to_parquet(save_dir / f'{td}.parquet', index=False)
            time.sleep(SLEEP)
            errors = 0
            if (i + 1) % 20 == 0:
                print(f"  [{api_name}] {i+1}/{len(todo)} done ({td})")
        except Exception as e:
            errors += 1
            print(f"  [{api_name}] {td} ERROR: {str(e)[:120]}")
            if errors >= 5:
                print(f"  [{api_name}] Too many errors, stopping at {td}")
                return False
            time.sleep(2 ** errors)

    print(f"  [{api_name}] Complete!")
    return True


def pull_limit_list_d(trade_dates):
    return pull_per_date('limit_list_d', 'limit_list_d', trade_dates)


def pull_stk_limit(trade_dates):
    return pull_per_date('stk_limit', 'stk_limit', trade_dates)


def pull_ths_daily(trade_dates):
    return pull_per_date('ths_daily', 'ths_daily', trade_dates)


def pull_daily_basic(trade_dates):
    return pull_per_date('daily_basic', 'daily_basic', trade_dates)


def pull_moneyflow(trade_dates):
    return pull_per_date('moneyflow', 'moneyflow', trade_dates)


def pull_margin(trade_dates):
    return pull_per_date('margin', 'margin', trade_dates)


def pull_margin_detail(trade_dates):
    return pull_per_date('margin_detail', 'margin_detail', trade_dates)


def pull_top_list(trade_dates):
    return pull_per_date('top_list', 'top_list', trade_dates)


def pull_top_inst(trade_dates):
    return pull_per_date('top_inst', 'top_inst', trade_dates)


def pull_stk_auction_o(trade_dates):
    return pull_per_date('stk_auction', 'stk_auction_o', trade_dates, {'auction_type': 'call'})


def pull_stk_auction_c(trade_dates):
    return pull_per_date('stk_auction', 'stk_auction_c', trade_dates, {'auction_type': 'close'})


def pull_index_global(trade_dates):
    return pull_per_date('index_global', 'index_global', trade_dates)


def pull_holdernumber(trade_dates):
    return pull_per_date('stk_holdernumber', 'stk_holdernumber', trade_dates)


def pull_hsgt_top10(trade_dates):
    return pull_per_date('hsgt_top10', 'hsgt_top10', trade_dates)


def pull_hk_hold(trade_dates):
    return pull_per_date('hk_hold', 'hk_hold', trade_dates)


def pull_moneyflow_hsgt(trade_dates):
    return pull_per_date('moneyflow_hsgt', 'moneyflow_hsgt', trade_dates)


# ──── Per-symbol pullers ────

def pull_cyq_perf(stock_list):
    save_dir = TUSHARE_DIR / 'cyq_perf'
    save_dir.mkdir(parents=True, exist_ok=True)

    # Check which stocks already have 2020 data
    todo = []
    for _, row in stock_list.iterrows():
        ts_code = row['ts_code']
        path = save_dir / f'{ts_code}.parquet'
        if path.exists():
            try:
                df = pd.read_parquet(path, columns=['trade_date'])
                td_str = df['trade_date'].astype(str)
                has_2020 = ((td_str >= START_DATE) & (td_str <= END_DATE)).any()
                if has_2020:
                    continue
            except:
                pass
        if row['list_date'] <= END_DATE:
            todo.append(ts_code)

    print(f"\n[cyq_perf] Stocks needing 2020 data: {len(todo)}")

    errors = 0
    for i, ts_code in enumerate(todo):
        try:
            df = pro.cyq_perf(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
            if df is not None and len(df) > 0:
                # Append to existing file if present
                path = save_dir / f'{ts_code}.parquet'
                if path.exists():
                    existing = pd.read_parquet(path)
                    df = pd.concat([existing, df], ignore_index=True)
                    df = df.drop_duplicates(subset=['ts_code', 'trade_date'])
                    df = df.sort_values('trade_date').reset_index(drop=True)
                df.to_parquet(path, index=False)
            time.sleep(SLEEP)
            errors = 0
            if (i + 1) % 50 == 0:
                print(f"  [cyq_perf] {i+1}/{len(todo)} ({ts_code})")
        except Exception as e:
            errors += 1
            print(f"  [cyq_perf] {ts_code} ERROR: {str(e)[:120]}")
            if errors >= 5:
                print(f"  [cyq_perf] Too many errors, stopping")
                return False
            time.sleep(2 ** errors)

    print(f"  [cyq_perf] Complete!")
    return True


def pull_stk_mins_5(stock_list):
    save_dir = TUSHARE_DIR / 'stk_mins_5'
    save_dir.mkdir(parents=True, exist_ok=True)

    seg_start = '2020-05-15 09:30:00'
    seg_end = '2020-07-31 15:00:00'

    todo = []
    for _, row in stock_list.iterrows():
        ts_code = row['ts_code']
        if row['list_date'] > END_DATE:
            continue
        path = save_dir / f'{ts_code}.parquet'
        if path.exists():
            try:
                df = pd.read_parquet(path, columns=['trade_time'])
                df['trade_time'] = pd.to_datetime(df['trade_time'])
                has_2020 = ((df['trade_time'] >= seg_start) & (df['trade_time'] <= seg_end)).any()
                if has_2020:
                    continue
            except:
                pass
        todo.append(ts_code)

    print(f"\n[stk_mins_5] Stocks needing 2020 data: {len(todo)}")

    BATCH = 20
    errors = 0
    for i, ts_code in enumerate(todo):
        try:
            df = pro.stk_mins(ts_code=ts_code, freq='5min',
                              start_date=seg_start, end_date=seg_end)
            time.sleep(6.0)  # stk_mins needs longer sleep

            if df is not None and len(df) > 0:
                # Append to existing
                path = save_dir / f'{ts_code}.parquet'
                if path.exists():
                    existing = pd.read_parquet(path)
                    df = pd.concat([existing, df], ignore_index=True)
                    df = df.drop_duplicates(subset=['ts_code', 'trade_time'])
                    df = df.sort_values('trade_time').reset_index(drop=True)
                df.to_parquet(path, index=False)
            errors = 0
            if (i + 1) % BATCH == 0:
                print(f"  [stk_mins_5] {i+1}/{len(todo)} ({ts_code})")
                time.sleep(30)  # batch rest
        except Exception as e:
            errors += 1
            err_str = str(e).lower()
            print(f"  [stk_mins_5] {ts_code} ERROR: {str(e)[:120]}")
            if 'timeout' in err_str or 'timed out' in err_str:
                time.sleep(600)
            elif errors >= 5:
                print(f"  [stk_mins_5] Too many errors, stopping")
                return False
            else:
                time.sleep(2 ** errors)

    print(f"  [stk_mins_5] Complete!")
    return True


# ──── Main ────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'

    print(f"{'='*60}")
    print(f"Tushare 2020 Backfill: {START_DATE} ~ {END_DATE}")
    print(f"Mode: {mode}")
    print(f"{'='*60}")

    trade_dates = get_trade_dates()
    print(f"Trading days: {len(trade_dates)} ({trade_dates[0]} ~ {trade_dates[-1]})")

    if mode in ('all', 'date'):
        # Per-date sources (fast, ~0.6s each)
        pull_limit_list_d(trade_dates)
        pull_stk_limit(trade_dates)
        pull_ths_daily(trade_dates)
        pull_daily_basic(trade_dates)
        pull_moneyflow(trade_dates)
        pull_margin(trade_dates)
        pull_margin_detail(trade_dates)
        pull_top_list(trade_dates)
        pull_top_inst(trade_dates)
        pull_stk_auction_o(trade_dates)
        pull_stk_auction_c(trade_dates)
        pull_index_global(trade_dates)
        pull_holdernumber(trade_dates)
        pull_hsgt_top10(trade_dates)
        pull_hk_hold(trade_dates)
        pull_moneyflow_hsgt(trade_dates)

    if mode in ('all', 'symbol'):
        stock_list = get_stock_list()
        pull_cyq_perf(stock_list)

    if mode in ('all', 'mins'):
        stock_list = get_stock_list() if 'stock_list' not in dir() else stock_list
        pull_stk_mins_5(stock_list)

    print(f"\n{'='*60}")
    print("2020 Backfill complete!")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()

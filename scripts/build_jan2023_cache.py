"""Build patched feature cache for Jan 2023 from local tushare files."""
import pandas as pd
import numpy as np
from pathlib import Path

tushare_dir = Path('E:/ashare_similarity_runtime/data/cache/prediction/tushare')
daily_dir = Path('E:/ashare_similarity_runtime/data/raw/bars/daily')

base = pd.read_parquet('E:/ashare_similarity_runtime/data/reports/prediction/feature_cache/gpu_probe_features_64ba73ab6db5f833.parquet')
jan = base[(base['date'] >= '2023-01-01') & (base['date'] <= '2023-01-31')].copy().reset_index(drop=True)
symbols = jan['symbol'].unique()
dates_dt = jan['date'].unique()
dates_str = [pd.Timestamp(d).strftime('%Y%m%d') for d in sorted(dates_dt)]
print(f'Jan 2023: {len(jan)} rows, {len(dates_str)} days, {len(symbols)} symbols')

# 1. CYQ_PERF
print('\n--- CYQ_PERF ---')
cyq_dir = tushare_dir / 'cyq_perf'
cyq_rows = []
for sym in symbols:
    for suffix in ['.SZ', '.SH', '.BJ']:
        path = cyq_dir / f'{sym}{suffix}.parquet'
        if path.exists():
            df = pd.read_parquet(path)
            df['trade_date'] = df['trade_date'].astype(str)
            df_w = df[df['trade_date'].isin(dates_str)]
            if not df_w.empty:
                df_w = df_w.copy()
                df_w['symbol'] = sym
                cyq_rows.append(df_w)
            break
if cyq_rows:
    cyq = pd.concat(cyq_rows, ignore_index=True)
    cyq['date'] = pd.to_datetime(cyq['trade_date'], format='%Y%m%d')
    merged = jan[['symbol','date']].merge(
        cyq[['symbol','date','winner_rate','cost_5pct','cost_15pct','cost_50pct','cost_85pct','cost_95pct']],
        on=['symbol','date'], how='left')
    jan['tushare_winner_rate'] = merged['winner_rate'].fillna(0).values.astype(np.float32)
    jan['tushare_cost_concentration'] = (
        (merged['cost_85pct'].fillna(0) - merged['cost_15pct'].fillna(0)) /
        merged['cost_50pct'].fillna(1).clip(lower=0.01)
    ).fillna(0).values.astype(np.float32)
    print(f'  winner_rate coverage: {(jan["tushare_winner_rate"] != 0).sum()}/{len(jan)}')

# 2. LIMIT_LIST_D (contains seal_ratio, open_times, first_time etc)
print('\n--- LIMIT_LIST_D ---')
limit_list_dir = tushare_dir / 'limit_list_d'
limit_rows = []
for d in dates_str:
    path = limit_list_dir / f'{d}.parquet'
    if path.exists():
        df = pd.read_parquet(path)
        if not df.empty:
            limit_rows.append(df)
if limit_rows:
    stk_lim = pd.concat(limit_rows, ignore_index=True)
    stk_lim['symbol'] = stk_lim['ts_code'].str.replace(r'\.\w+$', '', regex=True).str.zfill(6)
    stk_lim['date'] = pd.to_datetime(stk_lim['trade_date'].astype(str), format='%Y%m%d')
    lu = stk_lim[stk_lim['limit'] == 'U'].copy()
    merged = jan[['symbol','date']].merge(
        lu[['symbol','date','fd_amount','first_time','open_times','up_stat']],
        on=['symbol','date'], how='left')
    jan['tushare_seal_ratio'] = merged['fd_amount'].fillna(0).values.astype(np.float32)
    jan['tushare_open_times'] = merged['open_times'].fillna(0).values.astype(np.float32)
    def time_to_min(t):
        if pd.isna(t) or str(t) in ('', '0', 'nan'):
            return 0.0
        try:
            p = str(t).split(':')
            return max((int(p[0]) * 60 + int(p[1])) - 570, 0.0)
        except:
            return 0.0
    jan['tushare_first_time_minutes'] = merged['first_time'].apply(time_to_min).values.astype(np.float32)
    jan['tushare_limit_turnover'] = merged['fd_amount'].fillna(0).values.astype(np.float32)
    def parse_up_stat(v):
        if pd.isna(v) or str(v) in ('', '0', 'nan'):
            return 0.0
        try:
            parts = str(v).split('/')
            return float(parts[0])
        except:
            return 0.0
    jan['tushare_limit_type'] = merged['up_stat'].apply(parse_up_stat).values.astype(np.float32)
    print(f'  limit events matched: {(jan["tushare_seal_ratio"] != 0).sum()}')

# 3. DAILY_BASIC
print('\n--- DAILY_BASIC ---')
basic_dir = tushare_dir / 'daily_basic'
basic_rows = []
for d in dates_str:
    path = basic_dir / f'{d}.parquet'
    if path.exists():
        basic_rows.append(pd.read_parquet(path))
if basic_rows:
    basic = pd.concat(basic_rows, ignore_index=True)
    basic['symbol'] = basic['ts_code'].str.replace(r'\.\w+$', '', regex=True).str.zfill(6)
    basic['date'] = pd.to_datetime(basic['trade_date'].astype(str), format='%Y%m%d')
    if 'volume_ratio' in basic.columns:
        merged = jan[['symbol','date']].merge(basic[['symbol','date','volume_ratio']], on=['symbol','date'], how='left')
        jan['tushare_volume_ratio'] = merged['volume_ratio'].fillna(0).values.astype(np.float32)
        print(f'  volume_ratio coverage: {(jan["tushare_volume_ratio"] != 0).sum()}/{len(jan)}')

# 4. STK_MINS_5
print('\n--- STK_MINS_5 ---')
mins_dir = tushare_dir / 'stk_mins_5'
mins_results = []
for sym in symbols:
    for suffix in ['.SZ', '.SH', '.BJ']:
        path = mins_dir / f'{sym}{suffix}.parquet'
        if path.exists():
            df = pd.read_parquet(path)
            df['trade_time'] = pd.to_datetime(df['trade_time'])
            df['trade_date'] = df['trade_time'].dt.strftime('%Y%m%d')
            df_w = df[df['trade_date'].isin(dates_str)]
            if df_w.empty:
                break
            for td, grp in df_w.groupby('trade_date'):
                if len(grp) < 10:
                    continue
                grp = grp.sort_values('trade_time')
                last_6 = grp.tail(6)
                last_close = grp.iloc[-1]['close']
                last_30_open = last_6.iloc[0]['open']
                last_30min_ret = (last_close / last_30_open - 1) * 100 if last_30_open > 0 else 0.0
                vwap = (grp['amount'].sum() / grp['vol'].sum()) if grp['vol'].sum() > 0 else last_close
                vwap_dev = (last_close / vwap - 1) * 100 if vwap > 0 else 0.0
                close_vs_vwap = 1.0 if last_close > vwap else 0.0
                mins_results.append({
                    'symbol': sym, 'date': pd.Timestamp(td),
                    'last_30min_return': last_30min_ret,
                    'vwap_deviation': vwap_dev,
                    'close_vs_vwap': close_vs_vwap
                })
            break
if mins_results:
    mins_df = pd.DataFrame(mins_results)
    mins_df['date'] = pd.to_datetime(mins_df['date'], format='%Y%m%d')
    merged = jan[['symbol','date']].merge(mins_df, on=['symbol','date'], how='left')
    jan['tushare_last_30min_return'] = merged['last_30min_return'].fillna(0).values.astype(np.float32)
    jan['tushare_vwap_deviation'] = merged['vwap_deviation'].fillna(0).values.astype(np.float32)
    jan['tushare_close_vs_vwap'] = merged['close_vs_vwap'].fillna(0).values.astype(np.float32)
    print(f'  last_30min_return coverage: {(jan["tushare_last_30min_return"] != 0).sum()}/{len(jan)}')

# 5. DAILY_OHLCV_DERIVED
print('\n--- DAILY_OHLCV_DERIVED ---')
ohlcv_rows = []
for sym in symbols:
    path = daily_dir / f'{sym}.parquet'
    if not path.exists():
        continue
    df = pd.read_parquet(path)
    df_w = df[(df['date'] >= '2022-10-01') & (df['date'] <= '2023-01-31')].sort_values('date')
    if len(df_w) < 20:
        continue
    jan_dates = jan[jan['symbol'] == sym]['date'].values
    for td in jan_dates:
        sub = df_w[df_w['date'] <= td].tail(60)
        if len(sub) < 20:
            continue
        c = sub['close'].values
        v = sub['volume'].values
        cost_20 = np.mean(c[-20:])
        pvc = (c[-1] / cost_20 - 1) * 100 if cost_20 > 0 else 0
        r3 = (c[-1] / c[-4] - 1) * 100 if len(c) >= 4 else 0
        rets = np.diff(c[-21:]) / c[-21:-1] * 100 if len(c) >= 21 else np.array([0])
        std = np.std(rets) if len(rets) > 1 else 1
        abn = r3 / max(std, 0.01)
        abs_rets = np.abs(np.diff(c[-21:]) / c[-21:-1]) if len(c) >= 21 else np.array([0])
        vols20 = v[-20:] if len(v) >= 20 else v
        inv_t = np.mean(abs_rets / np.maximum(vols20[:len(abs_rets)], 1)) * 1e8
        asr = np.mean(v[-min(60, len(v)):])
        ohlcv_rows.append({'symbol': sym, 'date': td, 'pvc': pvc, 'abn': abn, 'inv': inv_t, 'asr': asr})
ohlcv_df = pd.DataFrame(ohlcv_rows)
if not ohlcv_df.empty:
    merged = jan[['symbol','date']].merge(ohlcv_df, on=['symbol','date'], how='left')
    jan['tushare_price_vs_cost_20d'] = merged['pvc'].fillna(0).values.astype(np.float32)
    jan['tushare_abnormal_3d_deviation'] = merged['abn'].fillna(0).values.astype(np.float32)
    jan['tushare_inv_t_20d'] = merged['inv'].fillna(0).values.astype(np.float32)
    jan['tushare_asr_60d'] = merged['asr'].fillna(0).values.astype(np.float32)
    print(f'  price_vs_cost_20d coverage: {(jan["tushare_price_vs_cost_20d"] != 0).sum()}/{len(jan)}')

# 6. THS SECTOR
print('\n--- THS SECTOR ---')
ths_dir = tushare_dir / 'ths_daily'
target_files = sorted([f for f in ths_dir.glob('2023*.parquet') if f.stem <= '20230131'])
print(f'  THS files: {len(target_files)}')
if target_files:
    frames = []
    for f in target_files:
        try:
            d = pd.read_parquet(f, columns=['ts_code', 'trade_date', 'pct_change'])
            if not d.empty:
                frames.append(d)
        except:
            continue
    if frames:
        concept_daily = pd.concat(frames, ignore_index=True)
        concept_daily['trade_date'] = concept_daily['trade_date'].astype(str)
        concept_daily = concept_daily.rename(columns={'ts_code': 'concept_code'})
        concept_daily = concept_daily.sort_values(['concept_code', 'trade_date']).reset_index(drop=True)
        is_up = (concept_daily['pct_change'] > 0).astype(int).values
        cids = concept_daily['concept_code'].values
        streak = np.zeros(len(concept_daily), dtype=np.float32)
        for i in range(len(concept_daily)):
            if i == 0 or cids[i] != cids[i-1]:
                streak[i] = float(is_up[i])
            elif is_up[i]:
                streak[i] = streak[i-1] + 1
            else:
                streak[i] = 0
        concept_daily['streak_days'] = streak
        n_per = concept_daily.groupby('trade_date')['concept_code'].transform('count')
        concept_daily['rank_pct'] = concept_daily.groupby('trade_date')['pct_change'].rank(ascending=False, method='min') / n_per
        members = pd.read_parquet(tushare_dir / 'ths_member' / 'all_members.parquet')
        members = members.rename(columns={'ts_code': 'concept_code', 'con_code': 'ts_code'})
        members['symbol'] = members['ts_code'].str.replace(r'\.\w+$', '', regex=True).str.zfill(6)
        members = members[['symbol', 'concept_code']].drop_duplicates()
        stock_concept = members.merge(concept_daily, on='concept_code', how='inner')
        stock_concept = stock_concept.dropna(subset=['pct_change'])
        if not stock_concept.empty:
            best_idx = stock_concept.groupby(['symbol', 'trade_date'])['pct_change'].idxmax().dropna()
            best = stock_concept.loc[best_idx].copy()
            best['date'] = pd.to_datetime(best['trade_date'], format='%Y%m%d')
            merged = jan[['symbol','date']].merge(
                best[['symbol','date','pct_change','rank_pct','streak_days']],
                on=['symbol','date'], how='left')
            jan['sector_pct_change_best'] = merged['pct_change'].fillna(0).values.astype(np.float32)
            jan['sector_strength_rank'] = (1 - merged['rank_pct'].fillna(0.5)).values.astype(np.float32)
            jan['sector_duration_days'] = merged['streak_days'].fillna(0).values.astype(np.float32)
            # sector_limit_up_count
            limit_dir = tushare_dir / 'limit_list_d'
            lu_frames = []
            for d in dates_str:
                p = limit_dir / f'{d}.parquet'
                if p.exists():
                    ldf = pd.read_parquet(p, columns=['trade_date', 'ts_code', 'limit'])
                    lu_only = ldf[ldf['limit'] == 'U']
                    if not lu_only.empty:
                        lu_frames.append(lu_only)
            if lu_frames:
                all_lu = pd.concat(lu_frames, ignore_index=True)
                all_lu['symbol'] = all_lu['ts_code'].str.replace(r'\.\w+$', '', regex=True).str.zfill(6)
                all_lu['trade_date'] = all_lu['trade_date'].astype(str)
                lu_concept = all_lu.merge(members, on='symbol').groupby(['trade_date', 'concept_code']).size().reset_index(name='lu_count')
                best2 = best[['symbol', 'date', 'concept_code']].copy()
                best2['trade_date'] = best2['date'].dt.strftime('%Y%m%d')
                best2 = best2.merge(lu_concept, on=['trade_date', 'concept_code'], how='left')
                merged2 = jan[['symbol','date']].merge(best2[['symbol','date','lu_count']], on=['symbol','date'], how='left')
                jan['sector_limit_up_count'] = merged2['lu_count'].fillna(0).values.astype(np.float32)
            print(f'  sector coverage: {(jan["sector_pct_change_best"] != 0).sum()}/{len(jan)}')

# Set availability flags
for col in list(jan.columns):
    if col.endswith('_available') and ('tushare_' in col or 'sector_' in col):
        base_col = col.replace('_available', '')
        if base_col in jan.columns:
            jan[col] = (jan[base_col] != 0).astype(np.float32)

out_path = 'E:/ashare_similarity_runtime/data/reports/prediction/feature_cache/jan_2023_patched.parquet'
jan.to_parquet(out_path, index=False)
print(f'\nDone: {out_path} ({len(jan)} rows, {len(jan.columns)} cols)')

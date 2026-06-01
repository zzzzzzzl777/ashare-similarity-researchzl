import os
import pyarrow.parquet as pq
from pathlib import Path

cache_1 = Path(r'E:/ashare_similarity_runtime/data/cache/prediction/tushare/stk_mins_1')
cache_5 = Path(r'E:/ashare_similarity_runtime/data/cache/prediction/tushare/stk_mins_5')

bad_proxy = []
bad_genuine = []
good = 0
total = 0

files = sorted(f for f in os.listdir(str(cache_1)) if f.endswith('.parquet') and not f.startswith('_'))
for f in files:
    total += 1
    code = f.replace('.parquet', '')
    try:
        df1 = pq.read_table(str(cache_1 / f), columns=['trade_time']).to_pandas()
        months = sorted(df1['trade_time'].astype(str).str[:7].unique())
        if len(months) < 2:
            good += 1
            continue
        fy, fm = int(months[0][:4]), int(months[0][5:7])
        ly, lm = int(months[-1][:4]), int(months[-1][5:7])
        expected = (ly - fy) * 12 + (lm - fm) + 1
        cov1 = len(months) / expected * 100
        if cov1 >= 90:
            good += 1
            continue
        p5 = cache_5 / f
        cov5 = 0
        if p5.exists():
            df5 = pq.read_table(str(p5), columns=['trade_time']).to_pandas()
            m5 = sorted(df5['trade_time'].astype(str).str[:7].unique())
            if len(m5) >= 2:
                fy5, fm5 = int(m5[0][:4]), int(m5[0][5:7])
                ly5, lm5 = int(m5[-1][:4]), int(m5[-1][5:7])
                exp5 = (ly5-fy5)*12+(lm5-fm5)+1
                cov5 = len(m5)/exp5*100
        if cov5 >= 90 and cov1 < 85:
            bad_proxy.append(code)
        else:
            bad_genuine.append(code)
    except Exception:
        bad_proxy.append(code)

print(f'Total: {total}  Good: {good}  Genuine-low: {len(bad_genuine)}  Proxy-bad: {len(bad_proxy)}')
print(f'Quality: {good}/{total} = {good*100/total:.1f}%')
if bad_proxy:
    print(f'Proxy-dropped ({len(bad_proxy)} files need repair)')

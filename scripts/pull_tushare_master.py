"""Master runner: 按优先级顺序串行拉取所有剩余 Tushare 数据
top_list+top_inst 已在后台跑，这个脚本从 stk_auction 开始接力
"""
import subprocess, sys

PYTHON = r'C:\Python314\python'
SCRIPTS_DIR = r'C:\Users\zzzzzzl\Desktop\subagent\scripts'

PULL_SEQUENCE = [
    # P0 (top_list+top_inst 已另行启动)
    ('pull_tushare_auction.py', 'stk_auction_o + stk_auction_c'),
    ('pull_tushare_holdernumber.py', 'stk_holdernumber'),
    ('pull_tushare_stk_limit.py', 'stk_limit'),
    # P1
    ('pull_tushare_hk_hold.py', 'hk_hold'),
    ('pull_tushare_margin_detail.py', 'margin_detail'),
    ('pull_tushare_ths.py', 'ths_hot + ths_daily + ths_member'),
    # P2
    ('pull_tushare_daily_basic.py', 'daily_basic'),
    ('pull_tushare_cyq_perf.py', 'cyq_perf'),
    ('pull_tushare_ccass_hsgt.py', 'ccass_hold + moneyflow_hsgt'),
    # P3
    ('pull_tushare_global_shibor.py', 'index_global + shibor'),
]

for script, desc in PULL_SEQUENCE:
    path = f'{SCRIPTS_DIR}\\{script}'
    print(f'\n{"="*60}')
    print(f'Starting: {desc} ({script})')
    print(f'{"="*60}')
    result = subprocess.run([PYTHON, path], capture_output=False)
    if result.returncode != 0:
        print(f'WARNING: {script} exited with code {result.returncode}')
    else:
        print(f'DONE: {desc}')

print(f'\n{"="*60}')
print('All pulls complete!')
print(f'{"="*60}')

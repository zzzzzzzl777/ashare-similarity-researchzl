# Tushare 数据拉取与因子研究交接文档

> 生成时间：2026-05-02
> 用途：新会话接手 Tushare 数据拉取和因子研究实验时的完整上下文
> 生成者：上一个 ClaudeCode 会话，已完成连接验证和全 API 测试

---

## 0. 项目背景（必读）

这是一个 A 股短线 T+1 预测系统。当前状态：

- **冻结配置**已确定（`docs/frozen_forward_config.json`），状态 `strong_research_candidate`，不是 passed
- **两条并行线**必须严格隔离：
  1. **Forward final_unseen**：按冻结配置每日跑预测，不加任何新因子，不改任何参数
  2. **Research 实验**（本文档范围）：用 Tushare 新数据构造新因子，做消融实验
- **冻结配置不动**：任何新因子只能进 `research` 因子集，不能修改 `docs/frozen_forward_config.json`
- **晋级纪律**：research 因子需通过 smoke → 消融 → expanded 流程，不能直接进 forward

关键文件：
- 核心仓库：`C:\Users\zzzzzzl\Desktop\subagent\`
- 运行数据：`E:\ashare_similarity_runtime\`
- 实验台账：`docs/prediction_experiment_log.md`
- 冻结配置：`docs/frozen_forward_config.json`
- Forward runbook：`docs/forward_runbook.md`
- 因子晋级登记：`docs/factor_promotion_registry.md`
- 执行计划：`C:\Users\zzzzzzl\Desktop\股票预测模型（1）.md`

桌面因子研究文档（三份，是候选因子的来源）：
- `C:\Users\zzzzzzl\Desktop\因子探索.md`（~1100 行，§13 有 P0/P1/P2 优先级清单）
- `C:\Users\zzzzzzl\Desktop\短线因子.md`（巨大文档，169 节，§80-120 系统性因子百科，§121-169 淘股吧实战因子）
- `C:\Users\zzzzzzl\Desktop\淘股吧短线因子提取.md`（27 类因子，§16-§27 为新增）

---

## 1. Tushare Pro 代理连接信息

```python
import tushare as ts
ts.set_token('05ed8ff7dbeb572be350d12fc2f1a9c3483c7e837fcb6701151f10f2')
pro = ts.pro_api()
pro._DataApi__http_url = 'http://tsy.xiaodefa.cn'
```

| 项目 | 值 |
|------|------|
| 接口地址 | `http://tsy.xiaodefa.cn`（HTTP，非 HTTPS，token 明文传输） |
| 积分 | 15000 点 |
| 频率限制 | 120 次/分钟（建议 sleep 0.6s） |
| Key 过期 | **2026-05-09 01:03:35 北京时间**（7 天有效） |
| 含独立权限 | 数量 1（分钟线独立配额，**1min/5min 已复测可用**，详见 §9 和 §4.10） |
| Key 检查 | `POST http://tsy.xiaodefa.cn/api/check-key` body `{"key": "<token>"}` |
| 文档 | `http://tsy.xiaodefa.cn/docs`（HTTP） |

### 已知坑

1. **`pro_bar` 等模块级函数**必须传 `api=pro`，否则走官方地址：
   ```python
   ts.pro_bar(ts_code='000001.SZ', start_date='20260101', end_date='20260430', freq='D', api=pro)
   ```

2. **GBK 编码**：代理返回的中文错误信息是 GBK 编码的 JSON，Windows 终端可能乱码。用错误码（40203/40101）判断，不要依赖中文消息。

3. **HTTP 非 HTTPS**：token 明文传输，注意不要在公共网络使用。

4. **分钟线频率差异**：早期测试曾因共享池拥挤返回 40203；2026-05-02 复测确认 `stk_mins` 的 **1min/5min 可用**，并已启动 `stk_mins_5` 拉取。15min/30min/60min 仍触发频率限制；分钟线数据在 merge/verify 完成前只能视为进行中。

5. **日期格式**：所有 API 的日期参数格式为 `YYYYMMDD`（字符串），不是 `YYYY-MM-DD`。

---

## 2. API 可用性测试结果（2026-05-02 凌晨已验证）

### 已验证可用

| API | 说明 | 调用方式 | 单日行数 |
|-----|------|----------|----------|
| `daily` | 日线行情 | `trade_date` 或 `ts_code` | ~5460 |
| `adj_factor` | 复权因子 | `ts_code` + 日期范围 | - |
| `daily_basic` | 换手率/PE/PB/市值 | `trade_date` | ~5460 |
| `moneyflow` | 个股资金流向 | `trade_date` | ~5151 |
| `moneyflow_ind_dc` | 行业资金流（东财） | `trade_date` | - |
| `moneyflow_ind_ths` | 行业资金流（同花顺） | `trade_date` | - |
| `limit_list_d` | 涨跌停明细 | `trade_date` | ~104（有涨跌停的） |
| `top_list` | 龙虎榜 | `trade_date` | ~96 |
| `top_inst` | 龙虎榜机构席位 | `trade_date` | ~1006 |
| `cyq_perf` | 筹码分布 | `ts_code` + 日期范围 | ~1/日/股 |
| `margin_detail` | 融资融券明细 | `trade_date` | ~1989 |
| `margin` | 融资融券汇总 | `trade_date` | - |
| `hk_hold` | 沪深港通持股 | `trade_date` | ~925 |
| `hsgt_top10` | 沪深港通十大成交 | `trade_date` | - |
| `ths_hot` | 同花顺热度 | `trade_date` | ~1332 |
| `ths_daily` | 概念板块行情 | `trade_date` | ~1504 |
| `ths_member` | 概念成分股 | `ts_code`（概念代码） | ~3826 |
| `index_daily` | 指数行情 | `ts_code` 或 `trade_date` | - |
| `index_dailybasic` | 指数每日指标 | `trade_date` | - |
| `index_classify` | 行业分类 | 无日期，一次性 | - |
| `block_trade` | 大宗交易 | `trade_date` | ~92 |
| `stk_factor` | 技术因子 | `ts_code` + 日期范围 | ~1/日/股 |
| `stk_factor_pro` | 技术因子Pro | `ts_code` + 日期范围 | - |
| `opt_daily` | 期权日行情 | `trade_date` | - |
| `fut_daily` | 期货日行情 | `trade_date` | - |
| `pledge_stat` | 股权质押 | `ts_code` | - |
| `stk_holdertrade` | 股东增减持 | `ann_date` | ~70 |
| `share_float` | 限售解禁 | `ts_code` | - |
| `stk_surv` | 机构调研 | `trade_date`（surv_date） | ~400 |
| `broker_recommend` | 券商评级 | - | - |
| `income_vip` | 利润表 | `ts_code` | - |
| `cashflow_vip` | 现金流量表 | `ts_code` | - |
| `fina_indicator_vip` | 财务指标 | `ts_code` | - |
| `stk_auction_o` | 开盘集合竞价 | `trade_date` | ~5495 |
| `stk_auction_c` | 收盘集合竞价 | `trade_date` | ~5510 |
| `stk_auction` | 竞价汇总（仅近期有历史） | `trade_date` | ~5439 |
| `stk_holdernumber` | 股东户数 | `trade_date` 或 `ts_code` | ~5500 |
| `stk_limit` | 每日涨跌停价格 | `trade_date` | ~7574 |
| `ccass_hold` | CCASS持仓（港交所中央结算） | `trade_date` | ~927 |
| `index_weight` | 指数成分权重（沪深300等） | `index_code` + `trade_date` | ~300 |
| `moneyflow_hsgt` | 沪深港通资金流向（市场级） | `trade_date` | 1 |
| `suspend_d` | 停牌信息 | `trade_date` | ~98 |
| `stock_basic` | 股票基本信息列表 | 无日期 | ~5512 |
| `disclosure_date` | 财报披露计划 | `end_date` | ~5515 |
| `cb_daily` | 可转债日线 | `trade_date` | ~338 |
| `index_global` | 全球指数 | `trade_date` | ~19 |
| `shibor` | SHIBOR利率 | `date` | 1 |
| `us_tycr` | 美国国债收益率 | `date` | 1 |
| `cn_cpi` | CPI | `month`（YYYYMM） | ~507 |
| `cn_ppi` | PPI | `month` | ~414 |
| `cn_m` | 货币供应量 | `month` | ~579 |
| `eco_cal` | 经济日历 | `date` | ~100 |
| `cb_basic` | 可转债基本信息 | 无日期 | ~1125 |
| `opt_basic` | 期权基本信息 | `exchange` | ~11540 |
| `balancesheet_vip` | 资产负债表 | `ts_code` | - |
| `stk_mins` | **分钟线（1min/5min）** | `ts_code` + `freq` + 日期范围 | 49/日(5min), 241/日(1min) |
| `forecast_vip` | 业绩预告（预增/预减/扭亏） | `ann_date` | ~6 |
| `ggt_top10` | 港股通十大个股成交明细 | `trade_date` | ~20 |
| `report_rc` | 卖方盈利预测评级 | `ts_code` | ~5000 |
| `express_vip` | 业绩快报 | `ts_code` | ~4 |
| `bak_daily` | 备用行情（独特字段全 null，无价值） | `trade_date` | ~5518 |

### 不可用

| API | 错误码 | 说明 |
|-----|--------|------|
| `stk_mins` (15min/30min/60min) | 40203 | 15/30/60 分钟频率触发频率限制，只有 **1min 和 5min 可用** |
| `cyq_extra` | 40101 | 无权限 |
| `news` | 40203 | 频率限制 |
| `major_news` | 40203 | 频率限制 |
| `anns` | - | 接口不存在（代理不支持） |
| `sw_member` | - | 接口不存在 |
| `mainbz_vip` | - | 接口不存在 |

---

## 3. 每个 API 返回的字段（实测）

### moneyflow（按 trade_date 拉取，单日 ~5151 行）
```
ts_code, trade_date,
buy_sm_vol, buy_sm_amount,      # 小单买入（量/金额，万元）
sell_sm_vol, sell_sm_amount,     # 小单卖出
buy_md_vol, buy_md_amount,      # 中单买入
sell_md_vol, sell_md_amount,     # 中单卖出
buy_lg_vol, buy_lg_amount,      # 大单买入
sell_lg_vol, sell_lg_amount,     # 大单卖出
buy_elg_vol, buy_elg_amount,    # 特大单买入
sell_elg_vol, sell_elg_amount,   # 特大单卖出
net_mf_vol, net_mf_amount       # 主力净流入（量/金额）
```

### limit_list_d（按 trade_date，单日 ~100 行）
```
trade_date, ts_code, industry, name, close, pct_chg, amount,
limit_amount,    # 板上成交额
float_mv,        # 流通市值
total_mv,        # 总市值
turnover_ratio,  # 换手率
fd_amount,       # 封单金额
first_time,      # 首次封板时间 (HHMMSS)
last_time,       # 最后封板时间
open_times,      # 炸板次数
up_stat,         # 连板统计 (如 "2/3")
limit_times,     # 涨停次数
limit            # U=涨停, D=跌停, Z=炸板
```

### top_list（按 trade_date，单日 ~96 行）
```
trade_date, ts_code, name, close, pct_change, turnover_rate, amount,
l_sell,       # 龙虎榜卖出额
l_buy,        # 龙虎榜买入额
l_amount,     # 龙虎榜总额
net_amount,   # 龙虎榜净买入
net_rate,     # 净买入占比%
amount_rate,  # 龙虎榜成交占比%
float_values, # 流通市值
reason        # 上榜原因
```

### top_inst（按 trade_date，单日 ~1006 行）
```
trade_date, ts_code, exalter(席位名),
buy, buy_rate, sell, sell_rate, net_buy,
side(0=买入, 1=卖出), reason
```

### hk_hold（按 trade_date，单日 ~925 行）
```
code, trade_date, ts_code, name,
vol,     # 持股数量
ratio,   # 持股比例%
exchange # SH/SZ
```

### margin_detail（按 trade_date，单日 ~1989 行）
```
trade_date, ts_code,
rzye,   # 融资余额
rqye,   # 融券余额
rzmre,  # 融资买入额
rqyl,   # 融券余量
rzche,  # 融资偿还额
rqchl,  # 融券偿还量
rqmcl,  # 融券卖出量
rzrqye  # 融资融券余额
```

### ths_hot（按 trade_date，单日 ~1332 行）
```
trade_date, data_type, ts_code, ts_name,
rank,          # 热度排名
pct_change,    # 涨跌幅
current_price, # 现价
hot,           # 热度值
concept,       # 所属概念
rank_time,     # 排名时间
rank_reason    # 上榜原因
```

### ths_daily（按 trade_date，单日 ~1504 行）
```
ts_code(概念代码), trade_date,
open, high, low, close, pre_close, avg_price,
change, pct_change, vol, turnover_rate
```

### ths_member（按概念 ts_code，一次性映射）
```
ts_code(概念代码), con_code(成分股代码), con_name
```

### cyq_perf（按 ts_code + 日期范围，每日每股 1 行）
```
ts_code, trade_date,
his_low,      # 历史最低价
his_high,     # 历史最高价
cost_5pct,    # 5%成本价
cost_15pct,   # 15%成本价
cost_50pct,   # 50%成本价（中位成本）
cost_85pct,   # 85%成本价
cost_95pct,   # 95%成本价
weight_avg,   # 加权平均成本
winner_rate   # 获利比例
```

### daily_basic（按 trade_date，单日 ~5460 行）
```
ts_code, trade_date, close,
turnover_rate,    # 换手率%
turnover_rate_f,  # 换手率(自由流通)%
volume_ratio,     # 量比
pe, pe_ttm,       # 市盈率/TTM
pb,               # 市净率
ps, ps_ttm,       # 市销率/TTM
dv_ratio, dv_ttm, # 股息率/TTM
total_share,      # 总股本(万)
float_share,      # 流通股本(万)
free_share,       # 自由流通股本(万)
total_mv,         # 总市值(万)
circ_mv           # 流通市值(万)
```

### block_trade（按 trade_date，单日 ~92 行）
```
ts_code, trade_date, price, vol, amount, buyer, seller
```

### stk_holdertrade（按 ann_date，单日 ~70 行）
```
ts_code, ann_date, holder_name, holder_type,
in_de(增减持方向), change_vol, change_ratio,
after_share, after_ratio, avg_price, total_share
```

### stk_surv（按 trade_date/surv_date，单日 ~400 行）
```
ts_code, name, surv_date,
fund_visitors, rece_place, rece_mode,
rece_org, org_type, comp_rece
```

### pledge_stat（按 ts_code）
```
ts_code, end_date, pledge_count,
unrest_pledge, rest_pledge, total_share, pledge_ratio
```

### stk_factor（按 ts_code + 日期范围）
```
ts_code, trade_date, close, open, high, low, pre_close,
change, pct_change, vol, amount, adj_factor,
open_hfq/qfq, close_hfq/qfq, high_hfq/qfq, low_hfq/qfq, pre_close_hfq/qfq,
macd_dif, macd_dea, macd, kdj_k, kdj_d, kdj_j,
rsi_6, rsi_12, rsi_24, boll_upper, boll_mid, boll_lower, cci
```

---

## 4. 因子-API 完整映射（三份桌面文档交叉审查）

> 以下因子来源标注对应桌面文档章节号，方便在新会话中定位上下文。

### P0 最高优先级（7 天内必拉）

#### 4.1 个股资金流向 `moneyflow`
- **因子来源**：因子探索§13 P0"净大单/净主力资金流"、短线因子§13"资金结构因子"、淘股吧§13"资金结构-主力净流入比"
- **可构造因子**：
  - `tushare_net_mf_amount`：净主力流入金额（直接取 `net_mf_amount`）
  - `tushare_lg_buy_sell_ratio = buy_lg_amount / max(sell_lg_amount, 1)`：大单买卖比
  - `tushare_elg_buy_sell_ratio = buy_elg_amount / max(sell_elg_amount, 1)`：特大单买卖比
  - `tushare_mf_vol_ratio = net_mf_amount / amount`：主力净流入占成交额比（需与 daily 的 amount 合并）
  - `tushare_mf_momentum_3d/5d`：资金流入 3/5 日动量（需时序计算）
  - `tushare_sm_sell_pressure = sell_sm_amount / (buy_sm_amount + sell_sm_amount)`：散户抛压
- **拉取方式**：按 `trade_date` 逐日拉取，804 个交易日 = 804 次请求，约 7 分钟

#### 4.2 涨跌停明细 `limit_list_d`
- **因子来源**：因子探索§13 P0"封板质量"、短线因子§3"连板梯队结构"、淘股吧§1"封板质量-封单金额/流通市值"、§3"连板梯队"、§11"延边刺客-封板强度"
- **可构造因子**：
  - `tushare_seal_ratio = fd_amount / float_mv`：封单比（封单金额/流通市值）
  - `tushare_open_times`：炸板次数
  - `tushare_first_time_minutes`：首封时间（转分钟，越早越强）
  - `tushare_up_stat_days`：连板天数（解析 "2/3" 格式）
  - `tushare_limit_type`：涨停/跌停/炸板标记
  - `tushare_limit_turnover = amount / float_mv`：板上换手
- **拉取方式**：按 `trade_date` 逐日，804 次请求，约 7 分钟

#### 4.3 龙虎榜 `top_list` + `top_inst`
- **因子来源**：因子探索§13 P1"席位行为"、淘股吧§18"席位行为微观博弈"、§19"北京炒家首板操作"、§27"延边出客操作体系"
- **可构造因子**：
  - `tushare_lhb_net_buy = l_buy - l_sell`：龙虎榜净买入
  - `tushare_lhb_net_rate`：净买入占比
  - `tushare_inst_buy_count`：机构席位买入数（从 top_inst 聚合）
  - `tushare_inst_net_buy`：机构净买入（从 top_inst 聚合）
  - `tushare_hot_seat_flag`：知名游资席位出现标记（需维护游资席位名单）
  - `tushare_lhb_appeared`：是否上榜（0/1，覆盖面窄但信号强）
- **拉取方式**：按 `trade_date` 逐日，top_list 804 次 + top_inst 804 次 = 1608 次请求，约 15 分钟

#### 4.3b 开盘/收盘集合竞价 `stk_auction_o` + `stk_auction_c`
- **因子来源**：淘股吧§6"竞价"、因子探索§13"竞价量价"
- **可构造因子**：
  - `tushare_auction_open_vwap_ratio = stk_auction_o.vwap / pre_close`：开盘竞价均价偏离
  - `tushare_auction_open_vol`：开盘竞价成交量（量越大关注度越高）
  - `tushare_auction_open_range = (high - low) / low`：竞价振幅
  - `tushare_auction_close_vwap_ratio`：收盘竞价均价偏离
  - `tushare_auction_close_vol`：收盘竞价成交量
- **拉取方式**：按 `trade_date`，各 804 次 = 1608 次请求，约 15 分钟
- **注意**：`stk_auction`（汇总版）历史覆盖不稳定（2023/2024 返回 0 行），只拉 `stk_auction_o` 和 `stk_auction_c`

#### 4.3c 股东户数 `stk_holdernumber`
- **因子来源**：因子探索§1"筹码集中度"
- **可构造因子**：
  - `tushare_holder_num`：股东户数
  - `tushare_holder_num_delta_pct`：股东户数变化率（季度间，筹码集中/分散）
  - `tushare_holder_num_per_share = holder_num / total_share`：每万股股东数
- **拉取方式**：按 `trade_date`，804 次请求，约 7 分钟
- **注意**：数据按季报披露，非每日更新，同一季度内数值不变

#### 4.3d 每日涨跌停价格 `stk_limit`
- **因子来源**：短线因子§3"连板梯队"、淘股吧§11"延边刺客"
- **可构造因子**：
  - `tushare_up_limit_distance = (up_limit - close) / close`：距涨停板距离（越小越接近涨停）
  - `tushare_down_limit_distance = (close - down_limit) / close`：距跌停板距离
  - `tushare_limit_range = (up_limit - down_limit) / close`：涨跌停幅度（区分 10cm/20cm/30cm）
- **拉取方式**：按 `trade_date`，804 次请求，约 7 分钟

### P1 高优先级

#### 4.4 沪深港通持股 `hk_hold`
- **因子来源**：因子探索§4"跨市场信号-北向资金"、短线因子§72"北向资金"、淘股吧§22"赵老哥核心"中的资金流向敏感度
- **可构造因子**：
  - `tushare_hk_ratio`：北向持股比例
  - `tushare_hk_ratio_delta_1d/5d`：持股比例 1/5 日变化
  - `tushare_hk_vol_delta_pct`：持股数量变化率
- **拉取方式**：按 `trade_date`，804 次请求，约 7 分钟

#### 4.5 融资融券 `margin_detail`
- **因子来源**：因子探索§13 P1"融资余额变化率"、短线因子§65"杠杆资金"
- **可构造因子**：
  - `tushare_rzye`：融资余额
  - `tushare_rzye_delta_pct`：融资余额变化率（需时序）
  - `tushare_rzmre_ratio = rzmre / rzye`：融资买入占余额比
  - `tushare_margin_net = rzmre - rzche`：融资净买入
  - `tushare_rqye_ratio = rqye / rzrqye`：融券占比（做空压力）
- **拉取方式**：按 `trade_date`，804 次请求，约 7 分钟

#### 4.6 同花顺热度 `ths_hot` + `ths_daily` + `ths_member`
- **因子来源**：因子探索§5"散户情绪-热搜/热度"、淘股吧§8"板块/题材热度"、§4"情绪周期"
- **可构造因子**：
  - `tushare_hot_rank`：热度排名
  - `tushare_hot_value`：热度值
  - `tushare_hot_rank_delta`：排名变化（需时序）
  - `tushare_concept_pct_change`：所属概念板块涨跌幅（通过 ths_member 关联 ths_daily）
  - `tushare_multi_concept_avg_hot`：多概念平均热度
- **拉取方式**：ths_hot 按 `trade_date` 804 次；ths_daily 按 `trade_date` 804 次；ths_member 按概念代码一次性拉取（`ths_index()` 返回 1724 个概念 = 1724 次请求）
- **预估耗时**：~15 分钟（ths_hot + ths_daily） + ~16 分钟（ths_member）

### P2 中优先级

#### 4.6b CCASS 持仓 `ccass_hold`
- **因子来源**：因子探索§4"跨市场信号"
- **可构造因子**：
  - `tushare_ccass_hold_ratio`：CCASS 持仓比例
  - `tushare_ccass_hold_ratio_delta`：持仓比例变化
- **拉取方式**：按 `trade_date`，804 次，约 7 分钟

#### 4.6c 指数成分权重 `index_weight`
- **可构造因子**：
  - `tushare_in_csi300`：是否沪深 300 成分股（0/1）
  - `tushare_index_weight`：成分权重
- **拉取方式**：按 `index_code` + `trade_date`，需拉 300/500/1000 三个指数 × 月频 ≈ 120 次

#### 4.6d 沪深港通资金流向 `moneyflow_hsgt`
- **因子来源**：因子探索§4"北向资金市场级"
- **可构造因子**：
  - `tushare_hgt_net`：沪股通净流入
  - `tushare_sgt_net`：深股通净流入
  - `tushare_hsgt_momentum_5d`：北向资金 5 日动量
- **拉取方式**：按 `trade_date`，804 次，约 7 分钟

#### 4.7 筹码分布 `cyq_perf`
- **因子来源**：因子探索§1"微结构-筹码集中度"
- **可构造因子**：
  - `tushare_winner_rate`：获利比例
  - `tushare_cost_concentration = cost_85pct / cost_15pct`：筹码集中度
  - `tushare_cost_position = (close - cost_50pct) / cost_50pct`：价格相对中位成本偏离
- **拉取方式**：按 `ts_code` + 日期范围，需逐股拉取，约 5000+ 股票 = 5000+ 次请求，约 46 分钟
- **注意**：如果时间紧，优先拉主板短线异动票（约 3000 只），跳过冷门小盘股

#### 4.8 每日基础指标 `daily_basic`
- **说明**：补充 volume_ratio（量比）、free_share（自由流通）、circ_mv（流通市值）等
- **已有数据**：部分字段项目中已有（turnover_rate, pe, pb），但 volume_ratio 和 free_share 是新增
- **拉取方式**：按 `trade_date`，804 次，约 7 分钟

#### 4.9 期权/期货 `opt_daily` + `fut_daily`
- **因子来源**：因子探索§6"衍生品信号"
- **可构造因子**：
  - `tushare_etf_opt_pcr`：50ETF/300ETF 期权认沽认购比
  - `tushare_if_basis`：股指期货基差
- **拉取方式**：按 `trade_date`，约 15 分钟

#### 4.10 分钟线 `stk_mins`（1min / 5min）
- **重要更新**：之前测试返回 40203，2026-05-02 复测确认 **1min 和 5min 可用**（独立配额）。15min/30min/60min 仍触发频率限制。
- **因子来源**：短线因子§80"分钟结构"、因子探索§13"盘口/微结构"
- **可构造因子**：
  - `tushare_last_30min_return`：尾盘 30 分钟收益率
  - `tushare_first_15min_volume_ratio`：开盘 15 分钟成交量占全天比
  - `tushare_vwap_deviation`：VWAP 偏离度
  - `tushare_intraday_volatility`：日内波动率
  - `tushare_up_volume_ratio`：上涨 bar 成交量占比
  - `tushare_high_time_pct`：最高价出现时间（尾盘冲高 vs 早盘冲高）
  - `tushare_close_vs_vwap`：收盘价相对 VWAP 位置
- **拉取方式**：按 `ts_code` + 日期范围，单次上限 8000 行（5min 约覆盖 163 天），需分段拉
- **预估请求**：~5000 股 × 5 段 = ~25,000 次，约 3.5 小时
- **存储**：`E:\...\tushare\stk_mins_5\{ts_code}.parquet`（按股票存）
- **频率选择**：优先拉 5min（数据量小 5 倍，因子构造更简单），1min 按需补充
- **注意**：
  - `trade_time` 格式为 `YYYY-MM-DD HH:MM:SS`，与其他 API 的 `YYYYMMDD` 不同
  - 字段：`ts_code, trade_time, close, open, high, low, vol, amount`（无 vwap，需自行计算 `amount/vol`）
  - 数据量大，建议只拉主板活跃股（~3000 只），不拉全 A

#### 4.11 业绩预告 `forecast_vip`
- **因子来源**：淘股吧§16"事件驱动"
- **可构造因子**：
  - `tushare_forecast_type`：预告类型（预增=1/略增=0.5/扭亏=0.5/续盈=0/首亏=-1/预减=-1/略减=-0.5）
  - `tushare_forecast_pchange_mid = (p_change_min + p_change_max) / 2`：预告净利变动中值
- **拉取方式**：按 `ann_date` 逐日，804 次，约 7 分钟
- **注意**：不是每天都有预告，大部分日期返回 0 行；覆盖率可能 <5%，只能 smoke/research

#### 4.12 港股通十大成交 `ggt_top10`
- **可构造因子**：
  - `tushare_ggt_top10_flag`：是否为港股通十大成交标的（0/1）
  - `tushare_ggt_net_amount`：港股通净买入金额
- **拉取方式**：按 `trade_date`，804 次，约 7 分钟

### P3 低优先级（有时间再拉）

| API | 因子方向 |
|-----|----------|
| `block_trade` | 大宗交易折溢价 |
| `stk_holdertrade` | 股东增减持 |
| `share_float` | 限售解禁压力 |
| `stk_surv` | 机构调研热度 |
| `pledge_stat` | 质押风险 |
| `broker_recommend` | 评级变化 |

---

## 5. 请求量估算与时间可行性

> **重要**：15000 积分是**接口权限等级**（决定能访问哪些 API），不是按次消耗的余额。调用 API 不会扣减积分。真正的约束是：
> - **频率**：120 次/分钟（约 2 次/秒，实际建议 0.55s 间隔 ≈ 109 次/分钟）
> - **时限**：Key 于 2026-05-09 过期
> - **理论上限**：7 天 × 16 小时/天 × 60 分/小时 × 109 次/分 ≈ 732,480 次请求，远超所需

| 优先级 | API | 请求数 | 耗时估算（@0.55s/次） |
|--------|-----|--------|----------------------|
| P0 | moneyflow | 804 | ~7.4 分钟 |
| P0 | limit_list_d | 804 | ~7.4 分钟 |
| P0 | top_list + top_inst | 1,608 | ~14.7 分钟 |
| P0 | stk_auction_o + stk_auction_c | 1,608 | ~14.7 分钟 |
| P0 | stk_holdernumber | 804 | ~7.4 分钟 |
| P0 | stk_limit | 804 | ~7.4 分钟 |
| P1 | hk_hold | 804 | ~7.4 分钟 |
| P1 | margin_detail | 804 | ~7.4 分钟 |
| P1 | ths_hot + ths_daily | 1,608 | ~14.7 分钟 |
| P1 | ths_member（1724 概念） | 1,724 | ~15.8 分钟 |
| P2 | daily_basic | 804 | ~7.4 分钟 |
| P2 | cyq_perf（主板 ~3000 只） | ~3,000 | ~27.5 分钟 |
| P2 | ccass_hold + moneyflow_hsgt | 1,608 | ~14.7 分钟 |
| P2 | opt_daily + fut_daily | ~1,608 | ~14.7 分钟 |
| P2 | forecast_vip + ggt_top10 | ~1,608 | ~14.7 分钟 |
| P0 | **stk_mins 5min（主板 ~3000 只）** | **~15,000** | **~2.3 小时** |
| P3 | 其他 | ~2,000 | ~18.3 分钟 |
| **合计** | | **~36,604** | **~5.6 小时** |

**结论**：加上分钟线约 5.6 小时，7 天时间绰绰有余。分钟线是单项最大的拉取任务。

---

## 6. 数据存储规范

```
E:\ashare_similarity_runtime\data\cache\prediction\tushare\
├── moneyflow\
│   ├── 20230103.parquet     # 按交易日存储
│   ├── 20230104.parquet
│   └── _pull_log.json       # 拉取进度（已完成日期列表）
├── limit_list_d\
│   ├── 20230103.parquet
│   └── _pull_log.json
├── top_list\
├── top_inst\
├── hk_hold\
├── margin_detail\
├── ths_hot\
├── ths_daily\
├── ths_member\              # 一次性映射表，不按日期
│   └── all_members.parquet
├── cyq_perf\
│   ├── 000001.SZ.parquet    # 按股票存储（因为按 ts_code 拉取）
│   └── _pull_log.json
├── daily_basic\
├── block_trade\
├── stk_mins_5\              # 5min 分钟线，按股票存储
│   ├── 000001.SZ.parquet
│   └── _pull_log.json
├── forecast_vip\
├── ggt_top10\
└── ...
```

- 格式：parquet（列式存储，压缩好，pandas 直接读）
- 按交易日拉的 API：每日一个 `{YYYYMMDD}.parquet`
- 按股票拉的 API（cyq_perf/stk_factor）：每股一个 `{ts_code}.parquet`
- 每个子目录有 `_pull_log.json` 记录进度，支持断点续传
- 目录已创建完毕

---

## 7. 拉取脚本编写指南

### 通用模板（按日期拉取）

```python
import tushare as ts
import pandas as pd
import os, time, json
from datetime import datetime

ts.set_token('05ed8ff7dbeb572be350d12fc2f1a9c3483c7e837fcb6701151f10f2')
pro = ts.pro_api()
pro._DataApi__http_url = 'http://tsy.xiaodefa.cn'

SAVE_DIR = r'E:\ashare_similarity_runtime\data\cache\prediction\tushare\{API_NAME}'
LOG_FILE = os.path.join(SAVE_DIR, '_pull_log.json')

def get_trade_dates(start='20230101', end=None):
    if end is None:
        from datetime import date
        end = date.today().strftime('%Y%m%d')
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

def pull():
    dates = get_trade_dates()
    progress = load_progress()
    done = set(progress['completed_dates'])
    remaining = [d for d in dates if d not in done]
    print(f"Done: {len(done)}, remaining: {len(remaining)}")

    errors = 0
    for i, td in enumerate(remaining):
        try:
            df = pro.{API_NAME}(trade_date=td)  # 替换 API 名
            if df is not None and len(df) > 0:
                df.to_parquet(os.path.join(SAVE_DIR, f'{td}.parquet'), index=False)
                progress['total_rows'] += len(df)
            progress['completed_dates'].append(td)
            if (i + 1) % 50 == 0:
                save_progress(progress)
                print(f"[{i+1}/{len(remaining)}] {td}, total: {progress['total_rows']}")
            time.sleep(0.55)
            errors = 0
        except Exception as e:
            errors += 1
            print(f"[{i+1}] {td} ERROR: {str(e)[:100]}")
            if errors >= 5:
                save_progress(progress)
                print("Too many errors, stopping")
                return
            time.sleep(2 ** errors)
    save_progress(progress)
    print(f"Done! Total: {progress['total_rows']}")

pull()
```

### 纪律

- 每次请求 sleep >= 0.55 秒
- 连续 5 次错误停止，人工检查
- 进度保存支持断点续传
- 不要并发请求（共享池频率限制）
- P0 优先拉完再拉 P1

---

## 8. 基础数据参考

- 交易日总数（2023-01-01 ~ 2026-05-02）：**804 个**
- 单日股票数（2026-04-30 基准）：**~5460 只**
- 主板 10cm 股票：**~3063 只**（预测系统 main_board_only 过滤后）

---

## ~~9. stk_mins 分钟线~~ 已复测可用（1min/5min）

**2026-05-02 上午复测**：`stk_mins` 的 1min 和 5min 频率现在可正常拉取，返回完整数据。15min/30min/60min 仍触发 40203 频率限制。

```
stk_mins 1min: 241 rows/日  (000001.SZ, 2026-04-28)
stk_mins 5min:  49 rows/日  (000001.SZ, 2026-04-28)
单次上限: 8000 行（5min 约覆盖 163 交易日）
字段: ts_code, trade_time, close, open, high, low, vol, amount
```

之前 40203 可能是共享池拥挤，Key 含"独立 数量 1"的配额现在生效了。详见 §4.10。

---

## 10. 运行环境

| 项目 | 值 |
|------|------|
| Python | `C:\Python314\python`，版本 3.14.3 |
| tushare | 1.4.29（`pip install tushare`，已装好） |
| pandas | 2.3.3 |
| pyarrow | 24.0.0（parquet 读写依赖） |
| 核心仓库 | `C:\Users\zzzzzzl\Desktop\subagent\` |
| 运行数据盘 | `E:\ashare_similarity_runtime\` |
| 网络代理 | `127.0.0.1:7897`（GitHub 访问必须设这个代理，Tushare API 不需要） |

---

## 11. Git 状态

| 项目 | 值 |
|------|------|
| 远程 | `https://github.com/zzzzzzzl777/ashare-similarity-researchzl.git`（HTTPS，非 SSH） |
| 当前分支 | `codex/research-freeze-forward` |
| 最新 commit | `6a04e29 research: frozen forward config for next_high_from_close prediction` |
| Draft PR | https://github.com/zzzzzzzl777/ashare-similarity-researchzl/pull/1 |
| git push 需代理 | `https_proxy=http://127.0.0.1:7897 git push ...` |

注意：SSH push 不可用（机器上只有绑定到另一个仓库的 deploy key）。必须用 HTTPS + 代理。

---

## 12. 已有数据盘点

### 已有（不需要从 Tushare 重拉）

| 数据 | 路径 | 数量 |
|------|------|------|
| 日线 parquet（全 A 股） | `E:\...\data\raw\bars\daily\` | 5327 只股票 |
| 5 分钟线 parquet（部分） | `E:\...\data\raw\bars\5\` | 330 只股票（仅近 3 个月免费源） |
| 涨停池快照 | `E:\...\data\cache\prediction\limit_pool_snapshots\` | 154 个 manifest |
| 预测 run artifacts | `E:\...\data\reports\prediction\runs\` | 147 次 run |

### 已建目录，拉取状态各异（2026-05-02 晚间二次审计）

> **重要**：上一个会话已通过 `pull_tushare_master.py` 拉取了大部分数据。新会话务必先检查每个目录的 `_pull_log.json` 确认实际进度，不要盲目重拉。

| 目录 | 状态（以目录 `_pull_log.json` 与 parquet 文件复核） |
|------|------|
| moneyflow | **804/804 完成** |
| limit_list_d | **804/804 完成** |
| top_list | **804/804 完成** |
| top_inst | **804/804 完成** |
| stk_auction_o | **804/804 完成** |
| stk_auction_c | **804/804 完成** |
| stk_holdernumber | **804/804 完成** |
| stk_limit | **804/804 完成** |
| margin_detail | **804/804 完成** |
| daily_basic | **804/804 完成** |
| ths_daily | **803/804 基本完成** |
| index_global | **804/804 完成** |
| shibor | **804/804 完成** |
| hk_hold | ~774/804 接近完成 |
| ccass_hold | ~775/804 接近完成 |
| moneyflow_hsgt | ~778/804 接近完成 |
| ths_hot | 804 日期已处理，623 个有数据 parquet |
| cyq_perf | ~3194/~5000 只股票 进行中 |
| ths_member | 1 文件（一次性映射表，已完成） |
| stk_mins_5 | **进行中**：根目录已有 679 个最终 parquet；`_segments` 正在补段，`pull_tushare_stk_mins.py pull` 仍在运行。旧 manifest 曾写 3195 只/2156 万行，但需等 merge + verify 后再认定完成 |
| forecast_vip | 部分完成：500 个 ann_date 已处理，393 个 parquet，18104 行 |
| ggt_top10 | 尚未产出有效 parquet/log，待 `forecast_vip` 后续调度 |
| hsgt_top10 | 804 日期已处理，773 个有数据 parquet |
| moneyflow_ind_dc | 804 日期已处理，635 个有数据 parquet |
| moneyflow_ind_ths | 804 日期已处理，392 个有数据 parquet |
| margin | 803/804，1 个日期失败待补 |
| index_dailybasic | 803/804，1 个日期失败待补 |
| stk_surv | 804 日期已处理，747 个有数据 parquet |

### 注意

- 日线数据已有，**不要用 Tushare `daily` API 重拉日线**，浪费时间和请求配额
- `daily_basic` 中的 turnover_rate / pe / pb 等字段项目中可能已有部分来源，但 **volume_ratio（量比）、free_share（自由流通股本）是新增字段**，需要从 Tushare 拉
- `limit_list_d` 与已有的 `limit_pool_snapshots` 是**不同数据源**（Tushare 版有封单额/首封时间/炸板次数等结构化字段，已有的快照是 AKShare 源），两者互补

---

## 13. 已有脚本

`C:\Users\zzzzzzl\Desktop\subagent\scripts\` 下已有：

| 脚本 | 用途 | 状态 |
|------|------|------|
| `pull_tushare_moneyflow.py` | 拉取 moneyflow 数据 | 已完成 |
| `pull_tushare_master.py` | 串行调度全部 API 拉取 | 已跑过；以各目录 `_pull_log.json` 为准 |
| `pull_tushare_p0.py` | P0 数据拉取（使用 proxy client） | 已跑过 |
| `pull_tushare_limit_list_d.py` | limit_list_d | 已完成 |
| `pull_tushare_top_list.py` | top_list + top_inst | 已完成 |
| `pull_tushare_auction.py` | stk_auction_o + stk_auction_c | 已完成 |
| `pull_tushare_holdernumber.py` | stk_holdernumber | 已完成 |
| `pull_tushare_stk_limit.py` | stk_limit | 已完成 |
| `pull_tushare_hk_hold.py` | hk_hold | 进行中 |
| `pull_tushare_margin_detail.py` | margin_detail | 已完成 |
| `pull_tushare_ths.py` | ths_hot + ths_daily + ths_member | 进行中 |
| `pull_tushare_daily_basic.py` | daily_basic | 已完成 |
| `pull_tushare_cyq_perf.py` | cyq_perf（主板 ~3000 只） | 进行中 |
| `pull_tushare_ccass_hsgt.py` | ccass_hold + moneyflow_hsgt | 进行中 |
| `pull_tushare_global_shibor.py` | index_global + shibor | 已完成 |
| `pull_tushare_stk_mins.py` | stk_mins 5min 分段拉取/修复/合并 | 进行中；不要重复启动同类进程 |
| `pull_tushare_stk_mins_v2.py` | stk_mins 5min 备用分段拉取脚本 | 已写好；使用前先检查当前活跃进程和 `_segments` 状态 |
| `pull_tushare_forecast_ggt.py` | forecast_vip + ggt_top10 | forecast_vip 已部分产出；ggt_top10 尚无有效产出 |
| `test_tsy_tushare_proxy.py` | Tushare 代理连接测试 | 已跑过 |
| `capture_limit_pool_snapshot.py` | AKShare 涨停池快照捕获 | 既有脚本 |
| `scan_factor_doc.py` | 因子文档扫描 | 既有脚本 |
| `mine_high_confidence_rules.py` | 规则挖掘 | 既有脚本 |

---

## 14. API 特殊调用注意事项

### ths_member 需要先获取概念代码列表

`ths_member` 按概念代码（如 `885338.TI`）拉取成分股，不能按日期拉。需要先通过 `ths_index()` 获取全部概念列表：

```python
concept_list = pro.ths_index()
# columns: ts_code, name, count, exchange, list_date, type
# 共 1724 个概念
# type: R=行业, N=概念, S=地域 等
```

然后逐个概念拉取成分股：
```python
for _, row in concept_list.iterrows():
    members = pro.ths_member(ts_code=row['ts_code'])
    time.sleep(0.55)
```

### cyq_perf 按股票拉取，需要股票列表

```python
# 获取全部上市公司（stock_basic 已验证可用）
stock_list = pro.stock_basic(exchange='', list_status='L')
# 或只拉主板：
stock_list = stock_list[stock_list['market'].isin(['主板'])]
```

每只股票拉全部日期范围（`start_date='20230101', end_date=当前日期`），大约 804 行/股。

### stock_basic 获取股票列表

多个 API 需要股票代码列表（cyq_perf、stk_factor、pledge_stat、share_float）。统一用 `stock_basic` 获取：

```python
stock_list = pro.stock_basic(exchange='', list_status='L',
    fields='ts_code,symbol,name,area,industry,market,list_date')
# 返回约 5400+ 行
# market 字段：主板/创业板/科创板/北交所/CDR
```

### ths_hot 的 data_type 参数

`ths_hot` 返回的 `data_type` 字段区分热度类型，拉取时不需要指定，默认返回所有类型。

### moneyflow 金额单位

**金额字段单位是万元**，不是元。构造因子时与 daily 的 amount（单位也是千元）合并需要对齐单位。

### limit_list_d first_time 格式

`first_time` 是 `HHMMSS` 字符串（如 `"093001"` = 09:30:01），需要解析为分钟数：
```python
def parse_time_to_minutes(t):
    if pd.isna(t) or t is None or t == 'None':
        return float('nan')
    t = str(t).zfill(6)
    return int(t[:2]) * 60 + int(t[2:4]) + int(t[4:6]) / 60
```

### limit_list_d up_stat 格式

`up_stat` 是字符串如 `"2/3"`（表示 3 天中有 2 天涨停），需要解析：
```python
def parse_up_stat(s):
    if pd.isna(s) or '/' not in str(s):
        return 0, 0
    parts = str(s).split('/')
    return int(parts[0]), int(parts[1])
```

### 某些日期 API 返回空

节假日后首个交易日、或某些 API 特定日期可能返回 0 行数据（如 `top_list` 不是每天都有龙虎榜）。脚本中用 `if df is not None and len(df) > 0` 保护，空日期照样标记为已完成。

### 竞价接口已复测可用

> **上一个会话判断"竞价无法提取"是错误的。** 实际有三个竞价汇总接口：

| API | 说明 | 历史覆盖 | 单日行数 |
|-----|------|----------|----------|
| `stk_auction_o` | 开盘集合竞价（9:15-9:25 汇总） | **2023-01-03 起有数据**（5012 行），可做历史训练 | ~5495 |
| `stk_auction_c` | 收盘集合竞价（14:57-15:00 汇总） | **2023-01-03 起有数据**（5330 行），可做历史训练 | ~5510 |
| `stk_auction` | 竞价汇总（含换手率/量比） | **仅近期有数据**，2023/2024 返回 0 行，历史不稳定 | ~5439 |

`stk_auction_o` 字段：`ts_code, trade_date, close, open, high, low, vol, amount, vwap`
`stk_auction_c` 字段：`ts_code, trade_date, close, open, high, low, vol, amount, vwap`
`stk_auction` 字段：`ts_code, trade_date, vol, price, amount, pre_close, turnover_rate, volume_ratio, float_share`

可构造因子：
- `tushare_auction_open_vwap_ratio = stk_auction_o.vwap / pre_close`：竞价成交均价偏离（开盘）
- `tushare_auction_open_vol`：开盘竞价成交量
- `tushare_auction_close_vwap_ratio`：收盘竞价成交均价偏离
- `tushare_auction_volume_ratio`：竞价量比（来自 stk_auction，仅近期）

**结论**：`stk_auction_o` 和 `stk_auction_c` 可拉历史数据，进入 research-only；`stk_auction` 历史覆盖不稳定，先不作为主力。

### 40203 错误处理

如果某个 API 突然返回 40203（频率限制），说明共享池当前繁忙。策略：
1. 先 sleep 60 秒重试
2. 如果持续 40203，换个时段（凌晨/清晨通常空闲）
3. 如果某个 API 始终 40203，可能是该 API 的独立权限未开通

### stk_mins 分钟线拉取注意事项（新增）

1. **只有 1min 和 5min 可用**，15min/30min/60min 触发 40203
2. **单次上限 8000 行**：5min 约覆盖 163 个交易日，需按时间窗口分段拉取
3. **按股票拉**，不能按日期拉：`pro.stk_mins(ts_code='000001.SZ', freq='5min', start_date='2023-01-03 09:30:00', end_date='2023-06-30 15:00:00')`
4. **日期格式与其他 API 不同**：`start_date`/`end_date` 用 `YYYY-MM-DD HH:MM:SS`，不是 `YYYYMMDD`
5. **存储按股票**：`stk_mins_5/{ts_code}.parquet`，每只股票一个文件，内含全部日期
6. **建议只拉主板活跃股**（~3000 只），不拉全 A，节省时间
7. **分段模板**（每只股票 5 段）：
   ```python
   segments = [
       ('2023-01-03 09:30:00', '2023-07-31 15:00:00'),
       ('2023-08-01 09:30:00', '2024-01-31 15:00:00'),
       ('2024-02-01 09:30:00', '2024-07-31 15:00:00'),
       ('2024-08-01 09:30:00', '2025-01-31 15:00:00'),
       ('2025-02-01 09:30:00', '2026-05-02 15:00:00'),
   ]
   all_dfs = []
   for s, e in segments:
       df = pro.stk_mins(ts_code=code, freq='5min', start_date=s, end_date=e)
       if df is not None and len(df) > 0:
           all_dfs.append(df)
       time.sleep(0.55)
   if all_dfs:
       pd.concat(all_dfs).to_parquet(f'stk_mins_5/{code}.parquet', index=False)
   ```
8. **进度日志**：用 `_pull_log.json` 记录已完成的股票代码列表，支持断点续传

---

## 15. 因子接入现有管线的位置

新因子构造完成后，需要接入现有代码：

| 步骤 | 文件 | 说明 |
|------|------|------|
| 因子计算 | `src/ashare_similarity/prediction/free_data_factors.py` | 新增 Tushare 因子的计算函数 |
| 因子注册 | 因子名以 `tushare_` 为前缀，加入 `research` 因子集 | 不进 `expanded` |
| 数据读取 | 从 `E:\...\tushare\{api}\{date}.parquet` 读取 | 需要新增读取逻辑 |
| 覆盖率检查 | 每个因子必须报告覆盖率（非 NaN 比例） | <30% 只能 smoke |
| 消融实验 | 用 `--feature-set research` 跑 probe | 对比有无新因子的差异 |

---

## 16. 新会话启动提示

新会话打开后，按此顺序操作：

### 第一步：读取上下文（必须全部读完再动手）

1. 读本文档：`C:\Users\zzzzzzl\Desktop\subagent\docs\tushare_data_handoff.md`
2. 读执行计划：`C:\Users\zzzzzzl\Desktop\股票预测模型（1）.md`
3. 读冻结配置：`C:\Users\zzzzzzl\Desktop\subagent\docs\frozen_forward_config.json`（了解不能动什么）
4. 读实验台账：`C:\Users\zzzzzzl\Desktop\subagent\docs\prediction_experiment_log.md`（了解已做过什么实验）

### 第二步：检查 Key 有效性

```python
import requests
r = requests.post('http://tsy.xiaodefa.cn/api/check-key',
    json={'key': '05ed8ff7dbeb572be350d12fc2f1a9c3483c7e837fcb6701151f10f2'})
print(r.json())
```

Key 于 **2026-05-09 01:03:35** 过期。如果已过期，所有 API 调用会失败，需要用户重新购买 Key 并更新 token。过期后本文档中的 token 作废，但因子映射（§4）、存储规范（§6）、管线接入（§15）仍然有效。

### 第三步：拉取数据

- 按 P0 → P1 → P2 → P3 顺序拉
- `scripts/pull_tushare_moneyflow.py` 已写好可直接运行（moneyflow 的拉取脚本）
- 其他 API 参考 §7 模板编写脚本，或直接在交互式环境中拉
- 拉取过程中用 check-key 定期检查 Key 是否仍有效

### 第四步：构造因子

- 因子名以 `tushare_` 为前缀
- 只进 `research` 因子集
- 接入点：`src/ashare_similarity/prediction/free_data_factors.py`
- 每个因子必须报告覆盖率

### 第五步：消融实验

- 用 `--feature-set research` 跑 `gpu-prediction-probe`
- 对比有无 Tushare 因子的差异
- 结果记录到 `docs/prediction_experiment_log.md`
- **不动冻结配置**

### 绝对不能做的事

1. 不能修改 `docs/frozen_forward_config.json`
2. 不能把新因子直接加入 `expanded` 因子集
3. 不能用 2026-01~04 数据得出 `passed` 结论
4. 不能自动 git commit / push（需用户确认）
5. 不能删除任何已有数据或备份
6. 不能用 Tushare 重拉已有的日线数据（浪费积分）

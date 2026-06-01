# Raw-to-Registry Review Queue (500) -- 2026-05-06

> 500 candidates from raw factor pool most worth human/engineering review
> Filtered: free_data=True, leakage=low, needs_level2=False, not implemented, not in C001-C152
> Exclusion: exact + substring match against GPU_PROBE_FEATURES + STABLE + RESEARCH + TUSHARE_FACTOR_COLUMNS + BOARD_STRUCTURE_COLUMNS + MARKET_EMOTION_COLUMNS (783 features) + 152 registry candidates

---

## Selection Criteria

1. free_data=True
2. future_leakage_risk=low
3. needs_level2=False
4. registry_match_status=no_match (not in C001-C152)
5. normalized_name NOT in any implemented feature constant (exact OR substring)
6. normalized_name NOT in any registry candidate name (exact OR substring, 152 candidates)
7. Priority data_needs: minute, auction, daily_ohlcv, limit_pool, moneyflow, lhb, hot_rank

Candidates passing all filters: 429 (from 3,075 total pool)
Output pool: top 429 by composite score
Score range: 88 - 33

---

## Data Needs Distribution (Top 429)

| data_needs | Count |
|-----------|-------|
| daily_ohlcv | 238 |
| sector_theme | 132 |
| limit_pool | 119 |
| cross_market | 8 |

---

### 1. hk_close_return

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002964 |
| source_file | explore |
| source_line | 550 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | P0 |
| suggested_bucket | expanded |
| score | 88 |
| raw_text | | 7 | `hk_close_return` (恒生指数) | AKShare | 是 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 13. 具体可新增因子清单（按优先级） > P0 — 最高优先级（预期准确率提升最大） |

**Why review**: Source-marked P0 | Suggested for expanded pool | Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 2. limit_up_count_market

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002965 |
| source_file | explore |
| source_line | 551 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | P0 |
| suggested_bucket | expanded |
| score | 88 |
| raw_text | | 8 | `limit_up_count_market` | AKShare | 是 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 13. 具体可新增因子清单（按优先级） > P0 — 最高优先级（预期准确率提升最大） |

**Why review**: Source-marked P0 | Suggested for expanded pool | High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 3. is_sector_leader

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000258 |
| source_file | tgb |
| source_line | 578 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | P0 |
| suggested_bucket | expanded |
| score | 83 |
| raw_text | 5. `is_sector_leader` 是否板块龙头 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P0 - 最高优先级（预计单因子IC最高） |

**Why review**: Source-marked P0 | Suggested for expanded pool | Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 4. sector_batch_limit_effect

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000286 |
| source_file | tgb |
| source_line | 609 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | P1 |
| suggested_bucket | expanded |
| score | 78 |
| raw_text | 25. `sector_batch_limit_effect` 板块批量涨停效应 ★新增 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P1 - 高优先级 |

**Why review**: Source-marked P1 | Suggested for expanded pool | High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 5. asking_chase_half_position

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000290 |
| source_file | tgb |
| source_line | 613 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | P1 |
| suggested_bucket | expanded |
| score | 78 |
| raw_text | 29. `asking_chase_half_position` 追涨半仓→涨停全仓（Asking核心） ★★新增 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P1 - 高优先级 |

**Why review**: Source-marked P1 | Suggested for expanded pool | High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 6. second_board_confirm_leader

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000287 |
| source_file | tgb |
| source_line | 610 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | P1 |
| suggested_bucket | expanded |
| score | 73 |
| raw_text | 26. `second_board_confirm_leader` 二板定龙头（赵老哥核心） ★★新增 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P1 - 高优先级 |

**Why review**: Source-marked P1 | Suggested for expanded pool | Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 7. opening_seal_speed

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000312 |
| source_file | tgb |
| source_line | 638 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | P2 |
| suggested_bucket | research |
| score | 48 |
| raw_text | 41. `opening_seal_speed` 开盘封板速度 ★新增 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P2 - 中优先级 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 8. hesitant_seal_signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000313 |
| source_file | tgb |
| source_line | 639 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | P2 |
| suggested_bucket | research |
| score | 48 |
| raw_text | 42. `hesitant_seal_signal` 犹豫封板信号 ★新增 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P2 - 中优先级 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 9. dynamic_volume_comparison

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000323 |
| source_file | tgb |
| source_line | 649 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | P2 |
| suggested_bucket | research |
| score | 48 |
| raw_text | 52. `dynamic_volume_comparison` 动态量比三标准（北京炒家核心） ★★新增 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P2 - 中优先级 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 10. min_daily_volume_300m

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000329 |
| source_file | tgb |
| source_line | 655 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | P2 |
| suggested_bucket | research |
| score | 48 |
| raw_text | 58. `min_daily_volume_300m` 最低日成交额3亿（赵老哥） ★★新增 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P2 - 中优先级 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 11. sector_followup_count

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000041 |
| source_file | tgb |
| source_line | 122 |
| data_needs | ['daily_ohlcv', 'limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `sector_followup_count` 板块跟风数 | 个股涨停当日，同板块其他涨停数 | 板块+日线 | 龙头战法帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 5. 龙头属性因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 12. solo_guide_count

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000074 |
| source_file | tgb |
| source_line | 185 |
| data_needs | ['daily_ohlcv', 'limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `solo_guide_count` 独苗指引数 | 非板块性的独立涨停股数量（暗示方向的单只股） | 全市场日线 | 涨停板拆解帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 11. 涨停板拆解因子（延边刺客体系） |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 13. sector_first_board_attr

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000076 |
| source_file | tgb |
| source_line | 187 |
| data_needs | ['daily_ohlcv', 'limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `sector_first_board_attr` 首板归因分类 | 首板股属于哪个板块/题材（独苗/板块效应/蹭热点） | 板块+日线 | 涨停板拆解帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 11. 涨停板拆解因子（延边刺客体系） |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 14. position_stock_signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000078 |
| source_file | tgb |
| source_line | 189 |
| data_needs | ['daily_ohlcv', 'limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `position_stock_signal` 身位股信号 | 独苗涨停股代码/名称暗示的板块方向 | 全市场日线 | 涨停板拆解帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 11. 涨停板拆解因子（延边刺客体系） |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 15. board_echelon_city_cluster

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000079 |
| source_file | tgb |
| source_line | 190 |
| data_needs | ['daily_ohlcv', 'limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `board_echelon_city_cluster` 城市/板块抱团线 | 连板梯队是否形成地域/板块抱团（如苏州5321） | 全市场日线 | 涨停板拆解帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 11. 涨停板拆解因子（延边刺客体系） |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 16. sector_batch_limit_effect

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000121 |
| source_file | tgb |
| source_line | 247 |
| data_needs | ['daily_ohlcv', 'limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `sector_batch_limit_effect` 板块批量涨停效应 | 板块是否出现批量涨停（涨停家数排名前三） | 全市场日线 | 节奏训练帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 14. 流动性与节奏因子（小土堆爆金币体系） |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 17. quant_next_day_cash

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000124 |
| source_file | tgb |
| source_line | 255 |
| data_needs | ['daily_ohlcv', 'limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `quant_next_day_cash` 量化次日兑现率 | 量化起爆次日涨停股中高开低走/跌停比例 | 全市场日线 | 万字长文帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 16. 量化行为与身位因子（小土堆万字长文体系）★新增 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 18. second_board_confirm_leader

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000213 |
| source_file | tgb |
| source_line | 374 |
| data_needs | ['daily_ohlcv', 'limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `second_board_confirm_leader` 二板定龙头 | 第二个涨停板确认龙头地位；首板不确定，二板才是确认信号 | 全市场日线 | 赵老哥(外部编纂) | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 22. 赵老哥核心因子（外部编纂）★新增 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 19. name_geography_mysticism

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000241 |
| source_file | tgb |
| source_line | 422 |
| data_needs | ['daily_ohlcv', 'limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `name_geography_mysticism` 名字/地域语料信号 | 华字辈/苏浙鲁地域/谐音梗→量化语料匹配涨停概率 | 文本+日线 | 延边出客·324/325/429帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 26. 延边出客帖子正文因子（拆解框架衍生）★新增 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 20. solo_stock_direction_hint

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000244 |
| source_file | tgb |
| source_line | 425 |
| data_needs | ['daily_ohlcv', 'limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `solo_stock_direction_hint` 独苗方向暗示 | 单只涨停股的属性/名称/地域暗示板块方向 | 全市场日线+文本 | 延边出客·324/429拆解 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 26. 延边出客帖子正文因子（拆解框架衍生）★新增 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 21. volume_price_health

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000541 |
| source_file | tgb |
| source_line | 3722 |
| data_needs | ['limit_pool', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | 涨停量价健康度 volume_price_health |
| section | 披露12小时后信号衰减约97% > 十七、半路/低吸/尾盘/接力链因子（第六轮搜索） > 17.1 万次涨停回测统计因子 > 涨停量价健康度 volume_price_health |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 22. success_prob

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000907 |
| source_file | tgb |
| source_line | 8126 |
| data_needs | ['daily_ohlcv', 'limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | success_prob = min(expected_open_volume / seal_order_queue, 1.0) |
| section | 排板成功率评估 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 23. today_limit_up

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000987 |
| source_file | tgb |
| source_line | 8840 |
| data_needs | ['limit_pool', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | today_limit_up = stock.close == stock.high_limit  # T日涨停 |
| section | 前提: T-1日大跌(跌幅>-5%)或断板, T日涨停 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 24. peak_price

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000990 |
| source_file | tgb |
| source_line | 8876 |
| data_needs | ['daily_ohlcv', 'limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | peak_price = stock.high_limit_day_close  # 涨停日收盘价 |
| section | 涨停后回调幅度 vs 反包概率 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 25. closed_limit_up

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001048 |
| source_file | tgb |
| source_line | 9302 |
| data_needs | ['limit_pool', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | closed_limit_up = stock.close == stock.high_limit  # 收涨停 |
| section | 地天板(当日触及跌停后封涨停)的识别与次日预测 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 26. final_close

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001099 |
| source_file | tgb |
| source_line | 9649 |
| data_needs | ['limit_pool', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | final_close = stock.close == stock.high_limit  # 最终是否回封 |
| section | 炸板(涨停打开)不全是坏事, 关键看炸板质量 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 27. volume_during_open

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001101 |
| source_file | tgb |
| source_line | 9651 |
| data_needs | ['limit_pool', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | volume_during_open = stock.volume_during_open  # 炸板期间成交量 |
| section | 炸板(涨停打开)不全是坏事, 关键看炸板质量 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 28. Z_t

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002055 |
| source_file | short |
| source_line | 4812 |
| data_needs | ['daily_ohlcv', 'limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | Z_t = 宏观/市场状态变量(波动率、换手率、涨停比例) |
| section | 注册制IPO收益分布 (2020-2025统计) > 78. 因子截面交互 > 78.4 条件因子有效性模型 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 29. seal_order_fragmentation

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002642 |
| source_file | short |
| source_line | 10164 |
| data_needs | ['daily_ohlcv', 'limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | seal_order_fragmentation = seal_order_count / seal_total_amount |
| section | 代理指标: 封板瞬间大单笔数(量化特征=多笔小单快速堆叠) |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 30. limit_up_with_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002954 |
| source_file | explore |
| source_line | 447 |
| data_needs | ['daily_ohlcv', 'limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 43 |
| raw_text | | `limit_up_with_volume` | 涨停+换手率>5% | 放量涨停→次日看高开 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 10. 条件预测：不预测所有样本 > 10.2 筛选高可预测性的条件因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 31. abull

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000001 |
| source_file | tgb |
| source_line | 41 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | **Asking（邱宝裕）** | **abull.org完整语录+雪球/知乎/百度文库等20+外部编纂** | **外部** | **追涨半仓→涨停加仓/守株待兔半仓→不加仓+龙头定义+量能标准** | |
| section | 淘股吧名人堂短线因子提取报告 > 数据来源 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 32. is_sector_leader

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000040 |
| source_file | tgb |
| source_line | 121 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `is_sector_leader` 是否板块龙头 | 板块内涨幅最大+连板最高 | 板块+日线 | 龙头战法帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 5. 龙头属性因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 33. sector_sustainability_score

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000080 |
| source_file | tgb |
| source_line | 191 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `sector_sustainability_score` 题材持续性评分 | 基于脱离龙头能否独立+新催化+资金合力综合评分 | 综合判断 | 涨停板拆解帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 11. 涨停板拆解因子（延边刺客体系） |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 34. hardness_three_exists

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000082 |
| source_file | tgb |
| source_line | 193 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `hardness_three_exists` 硬度三存在性 | "三在哪我在哪"：硬度三(三连板)存在时才能拿捏主升 | 全市场日线 | 延边出客实抓·324 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 11. 涨停板拆解因子（延边刺客体系） |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 35. echelon_position_battle

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000083 |
| source_file | tgb |
| source_line | 194 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `echelon_position_battle` 梯队身位争夺 | 午后连板代表不同梯队+让位判断+小弟跑路暗示 | 全市场日线 | 延边出客实抓·429 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 11. 涨停板拆解因子（延边刺客体系） |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 36. midcap_supplement_prob

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000084 |
| source_file | tgb |
| source_line | 195 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `midcap_supplement_prob` 中位补涨概率 | 中位股本好的有概率冲击补涨（参考首板出现时龙头身位） | 全市场日线 | 延边出客实抓·325 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 11. 涨停板拆解因子（延边刺客体系） |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 37. node_second_board_fault_tolerance

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000091 |
| source_file | tgb |
| source_line | 202 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `node_second_board_fault_tolerance` 节点做二板保容错 | 一定要在节点做二板，容错率就保住了 | 日线 | 延边出客实抓·429 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 11. 涨停板拆解因子（延边刺客体系） |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 38. board_keep_break_rule

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000101 |
| source_file | tgb |
| source_line | 217 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `board_keep_break_rule` 板留断走原则 | 连板晋级=留，断板=全走（操作框架因子） | 日线 | 南山游龙帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 12. 信号体系因子（橘子洲炒家/南山游龙） |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 39. chip_reflexivity

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000111 |
| source_file | tgb |
| source_line | 232 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `chip_reflexivity` 筹码反身性 | 炒一次渣一次形成共识 → 筹码博弈性增强 = 破局点 | 历史日线 | 夺权预期帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 13. 资金结构与周期因子（只核大学生体系） |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 40. super_theme_settlement_days

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000116 |
| source_file | tgb |
| source_line | 237 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `super_theme_settlement_days` 大题材沉淀期天数 | 超级题材二波中间需要的沉淀交易日数（通常半月到一月） | 历史日线 | 夺权预期帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 13. 资金结构与周期因子（只核大学生体系） |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 41. quant_eruption_signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000123 |
| source_file | tgb |
| source_line | 254 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `quant_eruption_signal` 量化起爆信号 | 大市值一字板+多个一字板同板块 = 量化起爆 | 全市场日线 | 万字长文帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 16. 量化行为与身位因子（小土堆万字长文体系）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 42. quant_oscillation_stock

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000126 |
| source_file | tgb |
| source_line | 257 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `quant_oscillation_stock` 量化振荡股标记 | 大涨一天跌一天交替 = 量化属性股 | 日线 | 万字长文帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 16. 量化行为与身位因子（小土堆万字长文体系）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 43. position_uniqueness

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000127 |
| source_file | tgb |
| source_line | 258 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `position_uniqueness` 身位唯一性 | 板块内唯一的20cm二连板/唯一创业板连板 | 全市场日线 | 万字长文帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 16. 量化行为与身位因子（小土堆万字长文体系）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 44. capital_memory

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000128 |
| source_file | tgb |
| source_line | 259 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `capital_memory` 资金记忆 | 历史同类事件中领涨的票再次出现同类事件 | 历史日线 | 万字长文帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 16. 量化行为与身位因子（小土堆万字长文体系）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 45. potential_outside_buy

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000129 |
| source_file | tgb |
| source_line | 260 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `potential_outside_buy` 潜在场外买盘 | 多个一字板买不到的程度（一字板数越多=场外买盘越多） | 全市场日线 | 万字长文帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 16. 量化行为与身位因子（小土堆万字长文体系）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 46. supplement_rise_node

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000132 |
| source_file | tgb |
| source_line | 263 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `supplement_rise_node` 补涨节点 | 龙头真正断板当天/二次停牌 = 补涨起点 | 全市场日线 | 万字长文帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 16. 量化行为与身位因子（小土堆万字长文体系）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 47. absolute_height_highlow_cut

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000133 |
| source_file | tgb |
| source_line | 264 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `absolute_height_highlow_cut` 绝对高度高低切 | 市场存在绝对高度+面临停牌/断板 → 高低切信号 | 全市场日线 | 万字长文帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 16. 量化行为与身位因子（小土堆万字长文体系）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 48. first_divergence_type

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000135 |
| source_file | tgb |
| source_line | 271 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `first_divergence_type` 首次分歧类型 | 强修复=整体回流；弱修复=局部聚焦 | 全市场日线 | 倒车接人帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 17. 修复与监管因子（只核大学生补充）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 49. repair_anchor_logic

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000136 |
| source_file | tgb |
| source_line | 272 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `repair_anchor_logic` 修复锚定逻辑 | 长逻辑最正（能拍计算器的业绩票）优先回流 | 基本面+日线 | 倒车接人帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 17. 修复与监管因子（只核大学生补充）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 50. height_determines_direction

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000140 |
| source_file | tgb |
| source_line | 276 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `height_determines_direction` 高度定方向 | 市场最高板确定后 → 同方向补涨有锚定 | 全市场日线 | 石油焖龙虾帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 17. 修复与监管因子（只核大学生补充）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 51. themed_sub_ipo

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000155 |
| source_file | tgb |
| source_line | 296 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `themed_sub_ipo` 带题材次新股标记 | 次新股+当前热点题材的叠加效应 | 板块+日线 | 著名刺客20150907 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 18. 席位行为与微观博弈因子（著名刺客复盘体系扩展）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 52. new_ipo_opening_drain

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000165 |
| source_file | tgb |
| source_line | 306 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `new_ipo_opening_drain` 新股开板资金分流 | 大批新股临近开板→资金被分流→现有热点缺乏对手盘 | 新股日历+日线 | 退学炒股"次新股闷杀" | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 18. 席位行为与微观博弈因子（著名刺客复盘体系扩展）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 53. asking_chase_half_position

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000174 |
| source_file | tgb |
| source_line | 325 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `asking_chase_half_position` 追涨半仓判定 | 追涨入场=半仓；当日涨停→次日全仓；当日不涨停→次日择高出 | 仓位管理 | Asking语录第36条 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 20. Asking超短体系因子（外部编纂完整版）★新增 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 54. chase_only_when_market_up

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000179 |
| source_file | tgb |
| source_line | 330 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `chase_only_when_market_up` 追涨需大盘配合 | 追涨操作只在大盘已大涨时；大盘好→最强股继续涨；大盘差→最强股横几天可退出 | 指数+日线 | Asking语录第22条 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 20. Asking超短体系因子（外部编纂完整版）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 55. leader_timing_not_size

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000180 |
| source_file | tgb |
| source_line | 331 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `leader_timing_not_size` 龙头看时机不看盘子 | 龙头不在盘子大小，在启动时机；先于大盘连续上涨并带动关联股=龙头 | 全市场日线 | Asking语录第8条 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 20. Asking超短体系因子（外部编纂完整版）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 56. no_20cm_board

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000198 |
| source_file | tgb |
| source_line | 354 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `no_20cm_board` 20cm板回避标记 | 创业板/科创板20%涨停板基本不碰；无板块支持的20cm连板=极其危险 | 基础数据 | 北京炒家(外部编纂) | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 21. 仓位止损量化因子（跨交易者汇总）★新增 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 57. six_emotion_variables

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000205 |
| source_file | tgb |
| source_line | 361 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `six_emotion_variables` 6变量定仓位 | 市场情绪+投机情绪(涨停数/连板高度/炸板率)+板块情绪(龙头高度/板块持续性) | 综合判断 | 涅盘重升(外部编纂) | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 21. 仓位止损量化因子（跨交易者汇总）★新增 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 58. sell_rule_ma_suppress

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000208 |
| source_file | tgb |
| source_line | 364 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `sell_rule_ma_suppress` 均线压制=卖 | 股价被均线压制无法突破→减仓/离场 | 日线 | 涅盘重升卖出规则 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 21. 仓位止损量化因子（跨交易者汇总）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 59. entry_at_limit_up

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000209 |
| source_file | tgb |
| source_line | 370 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `entry_at_limit_up` 涨停价成交率 | 个股买入成交价在涨停价的比例（赵老哥>90%） | 交易数据 | 赵老哥(外部编纂) | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 22. 赵老哥核心因子（外部编纂）★新增 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 60. min_daily_volume_300m

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000212 |
| source_file | tgb |
| source_line | 373 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `min_daily_volume_300m` 最低日成交额3亿 | 目标股日成交额必须>=3亿元 | 日线 | 赵老哥(外部编纂) | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 22. 赵老哥核心因子（外部编纂）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 61. demon_stock_relaunch_timing

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000228 |
| source_file | tgb |
| source_line | 399 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `demon_stock_relaunch_timing` 妖股正确介入时机 | 人气消退+形态转烂+大阴线后→再次启动才是真发动 | 日线形态 | 收割逻辑·100W实盘 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 24. 收割逻辑(涅盘重升)系统构建因子（实抓100W实盘+年终总结）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 62. limit_up_overnight_priority

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000234 |
| source_file | tgb |
| source_line | 410 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `limit_up_overnight_priority` 涨停板过夜最重要 | 手里有涨停板过夜比什么都重要 | 持仓策略 | 延边出客实抓·324 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 25. 延边出客操作体系因子（实抓541条回复）★新增 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 63. sell_price_vs_close

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000237 |
| source_file | tgb |
| source_line | 413 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `sell_price_vs_close` 卖价比收盘价高=容错率高 | 下午卖掉且卖价>收盘价=容错率高 | 成交价对比 | 延边出客实抓·429 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 25. 延边出客操作体系因子（实抓541条回复）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 64. leader_daily_independent

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000238 |
| source_file | tgb |
| source_line | 414 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `leader_daily_independent` 龙头每天独立 | 龙头的每一天都是独立的→不受前日影响 | 日线 | 延边出客实抓·325 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 25. 延边出客操作体系因子（实抓541条回复）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 65. lurking_capital_trap

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000246 |
| source_file | tgb |
| source_line | 432 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `lurking_capital_trap` 潜伏资金陷阱 | 横盘股打板=潜伏资金一枪爆头→横盘股不打板 | 日线形态 | 北京炒家·20万起步 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 27. 北京炒家首板微观操作因子（深度回复衍生）★新增 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 66. attack_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000331 |
| source_file | tgb |
| source_line | 660 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | P3 |
| suggested_bucket | research |
| score | 38 |
| raw_text | 42. `attack_volume` 攻击量 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P3 - 低优先级（需要Level2或特殊数据） |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 67. passive_open_board

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000333 |
| source_file | tgb |
| source_line | 662 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | P3 |
| suggested_bucket | research |
| score | 38 |
| raw_text | 44. `passive_open_board` 被动开板 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P3 - 低优先级（需要Level2或特殊数据） |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 68. large_order_seal_count

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000339 |
| source_file | tgb |
| source_line | 668 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | P3 |
| suggested_bucket | research |
| score | 38 |
| raw_text | 50. `large_order_seal_count` 大单封板手数 ★新增 |
| section | 淘股吧名人堂短线因子提取报告 > 四、因子优先级排序（对模型贡献预估） > P3 - 低优先级（需要Level2或特殊数据） |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 69. hot_sector_rotate

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000354 |
| source_file | tgb |
| source_line | 1092 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `hot_sector_rotate` 热点轮动 | 持仓板块与当日涨停板块重合度 | 退学炒股OCR(精功=光伏/浩源=天然气) | |
| section | 淘股吧名人堂短线因子提取报告 > 八、交割单分析与实盘赛数据 > 8.1 退学炒股交割单分析（OCR实提取） > 评论区交割单深度OCR（新增213张）★大幅更新 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 70. stock_personality_history

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000365 |
| source_file | tgb |
| source_line | 1252 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `stock_personality_history` 历史股性评分 | 历史涨停频率+连板频率+主动拉升频率 | 北京炒家亮点 | |
| section | 淘股吧名人堂短线因子提取报告 > 八、交割单分析与实盘赛数据 > 8.6 北京炒家详细操作方法论 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 71. sibling_stock_signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000367 |
| source_file | tgb |
| source_line | 1272 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `sibling_stock_signal` 兄弟股联动信号 | 同名/同集团/同业务股票一只涨停→另一只跟随概率 | 著名刺客复盘 | |
| section | 淘股吧名人堂短线因子提取报告 > 八、交割单分析与实盘赛数据 > 8.7 著名刺客战法演变与复盘因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 72. new_high_vs_oversold

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000382 |
| source_file | tgb |
| source_line | 1774 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `new_high_vs_oversold` 新高品种主动/超跌被动 | 新高品种涨停→超跌跟涨；新高品种不涨→超跌被套 | 只核大学生·0125 | |
| section | 淘股吧名人堂短线因子提取报告 > 十一、实盘抓取核心内容（974+条作者回复精选 + 帖子正文实抓） > 11.7 只核大学生 — 今日份思考系列（帖子正文实抓）★新增 完成 > 可量化因子（从帖子正文提取） |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 73. first_seal_success_rate

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000438 |
| source_file | tgb |
| source_line | 2505 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 一封板成功率因子 first_seal_success_rate |
| section | 淘股吧名人堂短线因子提取报告 > 十三、第四轮深度搜索补充因子（龙头/打板/反包/妖股） > 13.2 打板体系深度因子群 > 一封板成功率因子 first_seal_success_rate |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 74. broken_board_factor

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000440 |
| source_file | tgb |
| source_line | 2546 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 烂板因子 broken_board_factor |
| section | 淘股吧名人堂短线因子提取报告 > 十三、第四轮深度搜索补充因子（龙头/打板/反包/妖股） > 13.2 打板体系深度因子群 > 烂板因子 broken_board_factor |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 75. board_height_position_mapping

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000455 |
| source_file | tgb |
| source_line | 2804 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 连板高度仓位映射因子 board_height_position_mapping |
| section | 淘股吧名人堂短线因子提取报告 > 十四、第四轮深度搜索补充因子（仓位/止损/时机/复盘） > 14.1 仓位管理量化因子群 > 连板高度仓位映射因子 board_height_position_mapping |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 76. zt_count_position_mapping

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000457 |
| source_file | tgb |
| source_line | 2819 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 涨停家数-仓位映射因子 zt_count_position_mapping |
| section | 淘股吧名人堂短线因子提取报告 > 十四、第四轮深度搜索补充因子（仓位/止损/时机/复盘） > 14.1 仓位管理量化因子群 > 涨停家数-仓位映射因子 zt_count_position_mapping |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 77. board_fail_stop_loss

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000459 |
| source_file | tgb |
| source_line | 2856 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 打板炸板止损因子 board_fail_stop_loss |
| section | 淘股吧名人堂短线因子提取报告 > 十四、第四轮深度搜索补充因子（仓位/止损/时机/复盘） > 14.2 止盈止损体系因子群 > 打板炸板止损因子 board_fail_stop_loss |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 78. zt_reason_next_day_mapping

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000467 |
| source_file | tgb |
| source_line | 3010 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 涨停原因分类-次日走势映射因子 zt_reason_next_day_mapping |
| section | 淘股吧名人堂短线因子提取报告 > 十四、第四轮深度搜索补充因子（仓位/止损/时机/复盘） > 14.4 复盘体系量化因子群 > 涨停原因分类-次日走势映射因子 zt_reason_next_day_mapping |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 79. zt_total

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000472 |
| source_file | tgb |
| source_line | 3069 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | zt_total = 涨停板总量（非ST，非一字） |
| section | 淘股吧名人堂短线因子提取报告 > 十四、第四轮深度搜索补充因子（仓位/止损/时机/复盘） > 14.4 复盘体系量化因子群 > 市场容量综合评分因子 market_capacity_composite_score |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 80. cb_stock_limit_up_premium_spread

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000476 |
| source_file | tgb |
| source_line | 3126 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 正股涨停转债溢价传导因子 cb_stock_limit_up_premium_spread |
| section | 淘股吧名人堂短线因子提取报告 > 十五、第五轮深度搜索补充因子（可转债/次新/ST/大盘择时） > 15.1 可转债联动因子群 > 正股涨停转债溢价传导因子 cb_stock_limit_up_premium_spread |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 81. sub_new_board_height_ceiling

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000482 |
| source_file | tgb |
| source_line | 3183 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 次新股连板高度天花板因子 sub_new_board_height_ceiling |
| section | 淘股吧名人堂短线因子提取报告 > 十五、第五轮深度搜索补充因子（可转债/次新/ST/大盘择时） > 15.2 次新股专项因子群 > 次新股连板高度天花板因子 sub_new_board_height_ceiling |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 82. market_avg_height

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000484 |
| source_file | tgb |
| source_line | 3189 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | market_avg_height = 同期全市场新股平均连板数 |
| section | 淘股吧名人堂短线因子提取报告 > 十五、第五轮深度搜索补充因子（可转债/次新/ST/大盘择时） > 15.2 次新股专项因子群 > 次新股连板高度天花板因子 sub_new_board_height_ceiling |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 83. market_volume_state

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000492 |
| source_file | tgb |
| source_line | 3271 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 两市成交额状态因子 market_volume_state |
| section | 淘股吧名人堂短线因子提取报告 > 十五、第五轮深度搜索补充因子（可转债/次新/ST/大盘择时） > 15.4 大盘择时系统化因子群 > 两市成交额状态因子 market_volume_state |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 84. daily_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000493 |
| source_file | tgb |
| source_line | 3276 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | daily_volume = 沪深两市当日成交额（亿元） |
| section | 淘股吧名人堂短线因子提取报告 > 十五、第五轮深度搜索补充因子（可转债/次新/ST/大盘择时） > 15.4 大盘择时系统化因子群 > 两市成交额状态因子 market_volume_state |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 85. multi_seat_score

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000511 |
| source_file | tgb |
| source_line | 3438 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | multi_seat_score = sum(seat_buy_amount[i] for i in top5_buyers) / total_volume |
| section | 披露12小时后信号衰减约97% > 多席位同时买入强度 multi_seat_buy_strength |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 86. quant_fake_seal_detection

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000531 |
| source_file | tgb |
| source_line | 3561 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 量化封板后秒撤/诱多识别 quant_fake_seal_detection |
| section | 披露12小时后信号衰减约97% > 16.4 量化资金行为对抗因子群 > 量化封板后秒撤/诱多识别 quant_fake_seal_detection |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 87. quant_sector_weight

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000534 |
| source_file | tgb |
| source_line | 3615 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | quant_sector_weight = sector_turnover / total_market_turnover |
| section | 披露12小时后信号衰减约97% > 16.4 量化资金行为对抗因子群 > 量化资金日内净流出时段 quant_intraday_net_outflow |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 88. limit_up_time_category

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000540 |
| source_file | tgb |
| source_line | 3704 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 涨停封板时段分类 limit_up_time_category |
| section | 披露12小时后信号衰减约97% > 十七、半路/低吸/尾盘/接力链因子（第六轮搜索） > 17.1 万次涨停回测统计因子 > 涨停封板时段分类 limit_up_time_category |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 89. trend_alignment

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000549 |
| source_file | tgb |
| source_line | 3763 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 涨停趋势对齐 trend_alignment |
| section | 披露12小时后信号衰减约97% > 十七、半路/低吸/尾盘/接力链因子（第六轮搜索） > 17.1 万次涨停回测统计因子 > 涨停趋势对齐 trend_alignment |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 90. zhaban_next_day_loss

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000551 |
| source_file | tgb |
| source_line | 3781 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 炸板次日亏损统计 zhaban_next_day_loss |
| section | 披露12小时后信号衰减约97% > 十七、半路/低吸/尾盘/接力链因子（第六轮搜索） > 17.2 炸板次日亏损量化因子 > 炸板次日亏损统计 zhaban_next_day_loss |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 91. huifeng_quality

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000552 |
| source_file | tgb |
| source_line | 3809 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 回封质量 huifeng_quality |
| section | 披露12小时后信号衰减约97% > 十七、半路/低吸/尾盘/接力链因子（第六轮搜索） > 17.2 炸板次日亏损量化因子 > 回封质量 huifeng_quality |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 92. zhaban_high_risk_avoid

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000553 |
| source_file | tgb |
| source_line | 3824 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 炸板高风险规避 zhaban_high_risk_avoid |
| section | 披露12小时后信号衰减约97% > 十七、半路/低吸/尾盘/接力链因子（第六轮搜索） > 17.2 炸板次日亏损量化因子 > 炸板高风险规避 zhaban_high_risk_avoid |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 93. seal_time_factor

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000573 |
| source_file | tgb |
| source_line | 4198 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 429: `seal_time_factor` - 封板时间因子 |
| section | 警惕"游资合作出货": 次日卖出席位出现前日买入游资时排除 > 18.2 打板质量因子群 > Factor 429: `seal_time_factor` - 封板时间因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 94. seal_ratio_factor

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000575 |
| source_file | tgb |
| source_line | 4219 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 430: `seal_ratio_factor` - 封成比因子 |
| section | 大盘大跌日早盘封板溢价也会降低 > Factor 430: `seal_ratio_factor` - 封成比因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 95. seal_ratio_score

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000577 |
| source_file | tgb |
| source_line | 4225 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | seal_ratio_score = { |
| section | 封成比 = 收盘时封单金额 / 当日成交金额 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 96. max_consecutive_board_height

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000592 |
| source_file | tgb |
| source_line | 4367 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 437: `max_consecutive_board_height` - 连板高度空间因子 |
| section | 赚钱效应回暖首日(从负转正): 积极做多信号, 次日正收益概率62% > Factor 437: `max_consecutive_board_height` - 连板高度空间因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 97. seal_time_distribution

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000594 |
| source_file | tgb |
| source_line | 4387 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 438: `seal_time_distribution` - 封板时间分布因子 |
| section | 需区分"自然晋级"和"一字顶板"(缩量一字连板不代表真正情绪) > Factor 438: `seal_time_distribution` - 封板时间分布因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 98. cb_underlying_limit_linkage

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000601 |
| source_file | tgb |
| source_line | 4485 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 441: `cb_underlying_limit_linkage` - 正股涨停联动因子 |
| section | 2022年可转债新规(涨跌幅限制20%)后策略收益有所下降 > Factor 441: `cb_underlying_limit_linkage` - 正股涨停联动因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 99. ipo_open_board_entry

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000605 |
| source_file | tgb |
| source_line | 4586 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 445: `ipo_open_board_entry` - 新股开板首日买入因子 |
| section | 市场低波动期策略失效 > 19.2 次新股短线因子 > Factor 445: `ipo_open_board_entry` - 新股开板首日买入因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 100. volume_board_quality

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000631 |
| source_file | tgb |
| source_line | 5055 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 461: `volume_board_quality` - 缩量板vs放量板质量因子 |
| section | 杂毛股的烂板: 大概率见顶, 应回避 > Factor 461: `volume_board_quality` - 缩量板vs放量板质量因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 101. vol_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000632 |
| source_file | tgb |
| source_line | 5061 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | vol_ratio = stock.today_volume / stock.avg_volume_5d |
| section | 量化规则 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 102. exit_timing

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000640 |
| source_file | tgb |
| source_line | 5163 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | exit_timing = "题材高潮日(涨停家数最多日)减仓" |
| section | 提前1个月布局, 题材兑现前离场 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 103. volume_change

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000691 |
| source_file | tgb |
| source_line | 5802 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | volume_change = (vol_925 - vol_922) / max(vol_922, 1) |
| section | 量化规则 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 104. bidding_limit_count

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000697 |
| source_file | tgb |
| source_line | 5871 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | bidding_limit_count = count_bidding_limit_up() |
| section | 竞价涨停数(0~25分) |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 105. avg_gap

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000698 |
| source_file | tgb |
| source_line | 5877 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | avg_gap = mean(bidding_gap for s in yesterday_limit_up_stocks) |
| section | 昨日涨停股竞价表现(0~25分) |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 106. volume_falling

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000704 |
| source_file | tgb |
| source_line | 5920 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | volume_falling = volume_at_highs[-1] < volume_at_highs[-2] * 0.7 |
| section | 顶背离: 价格创新高但对应量能递减 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 107. confidence

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000705 |
| source_file | tgb |
| source_line | 5924 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | confidence = volume_at_highs[-2] / volume_at_highs[-1]  # 背离幅度 |
| section | 顶背离: 价格创新高但对应量能递减 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 108. pulse_volume_signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000726 |
| source_file | tgb |
| source_line | 6100 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 487: `pulse_volume_signal` - 脉冲放量方向因子 |
| section | 关键: 开盘30分钟的"方向+量能"组合比单独方向更可靠 > Factor 487: `pulse_volume_signal` - 脉冲放量方向因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 109. real_body

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000733 |
| source_file | tgb |
| source_line | 6167 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | real_body = abs(candle.close - candle.open) |
| section | 量化规则 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 110. current_gain

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000735 |
| source_file | tgb |
| source_line | 6195 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | current_gain = (stock.price - stock.pre_close) / stock.pre_close |
| section | 量化规则 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 111. limitup_count

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000744 |
| source_file | tgb |
| source_line | 6286 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | limitup_count = market_data.limitup_count          # 涨停家数 |
| section | 量化规则 - 基于Tushare limit_list_d API |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 112. limitup_premium

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000748 |
| source_file | tgb |
| source_line | 6290 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | limitup_premium = market_data.yesterday_limitup_avg_open_premium  # 昨日涨停溢价 |
| section | 量化规则 - 基于Tushare limit_list_d API |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 113. target

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000755 |
| source_file | tgb |
| source_line | 6339 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | target = "首个涨停+板块龙头属性+前期未大跌的强势股" |
| section | 买入目标: 冰点期次日"率先涨停"的辨识度股票 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 114. volume_board_type_classifier

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000800 |
| source_file | tgb |
| source_line | 7029 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 511: `volume_board_type_classifier` - 缩量加速板vs放量分歧板分类因子 |
| section | 来源: 淘股吧"二波战法"讨论 > Factor 511: `volume_board_type_classifier` - 缩量加速板vs放量分歧板分类因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 115. volume_valid

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000811 |
| source_file | tgb |
| source_line | 7105 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | volume_valid = ( |
| section | 仅信任9:20后数据(9:15-9:20可撤单, 不可靠) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 116. open_pct

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000819 |
| source_file | tgb |
| source_line | 7182 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | open_pct = (ad.price_925 - stock.pre_close) / stock.pre_close |
| section | T日竞价分析(9:20-9:25) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 117. vol_trend

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000820 |
| source_file | tgb |
| source_line | 7183 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | vol_trend = "递增" if ad.volume_924 > ad.volume_922 else "递减" |
| section | T日竞价分析(9:20-9:25) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 118. prev_limit_up_stocks

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000840 |
| source_file | tgb |
| source_line | 7414 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | prev_limit_up_stocks = market.get_prev_day_limit_up() |
| section | 量化规则 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 119. nuclear_hits

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000842 |
| source_file | tgb |
| source_line | 7417 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | nuclear_hits = [s for s in prev_limit_up_stocks if s in today_limit_down] |
| section | 量化规则 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 120. nuclear_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000843 |
| source_file | tgb |
| source_line | 7418 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | nuclear_ratio = len(nuclear_hits) / max(len(prev_limit_up_stocks), 1) |
| section | 量化规则 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 121. night_session

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000865 |
| source_file | tgb |
| source_line | 7703 |
| data_needs | ['daily_ohlcv', 'cross_market'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | night_session = get_futures_night_close(commodity_code) |
| section | 量化规则 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 122. night_change

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000867 |
| source_file | tgb |
| source_line | 7707 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | night_change = (night_session - day_close) / day_close |
| section | 夜盘涨幅 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 123. total_amount

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000880 |
| source_file | tgb |
| source_line | 7874 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | total_amount = sum(stock.daily_turnover_amount[-lookback:]) |
| section | 方法1: 加权平均成本法 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 124. total_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000881 |
| source_file | tgb |
| source_line | 7875 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | total_volume = sum(stock.daily_volume[-lookback:]) |
| section | 方法1: 加权平均成本法 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 125. avg_cost

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000882 |
| source_file | tgb |
| source_line | 7876 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | avg_cost = total_amount / total_volume if total_volume > 0 else stock.close |
| section | 方法1: 加权平均成本法 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 126. price_vs_cost

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000886 |
| source_file | tgb |
| source_line | 7892 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | price_vs_cost = (stock.close - estimated_cost) / estimated_cost |
| section | 当前价格相对成本的位置 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 127. expected_open_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000906 |
| source_file | tgb |
| source_line | 8124 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | expected_open_volume = stock.avg_daily_volume * 0.3  # 预计打开成交量 |
| section | 排板成功率评估 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 128. second_seal_opportunity

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000918 |
| source_file | tgb |
| source_line | 8223 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 539: `second_seal_opportunity` - 二封三封机会因子 |
| section | 来源: 淘股吧打板派对烂板的系统性归纳 > Factor 539: `second_seal_opportunity` - 二封三封机会因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 129. reseal_quality

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000919 |
| source_file | tgb |
| source_line | 8236 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | reseal_quality = { |
| section | 回封条件评估 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 130. sell_cancel_rate

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000927 |
| source_file | tgb |
| source_line | 8316 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | sell_cancel_rate = stock_l2.sell_cancel_amount / stock_l2.sell_order_amount |
| section | 撤单异常检测 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 131. buy_cancel_rate

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000928 |
| source_file | tgb |
| source_line | 8317 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | buy_cancel_rate = stock_l2.buy_cancel_amount / stock_l2.buy_order_amount |
| section | 撤单异常检测 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 132. active_buy

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000933 |
| source_file | tgb |
| source_line | 8355 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | active_buy = sum(t.amount for t in ticks if t.direction == "buy") |
| section | 主动买入 vs 主动卖出 (按成交方向分) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 133. active_sell

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000934 |
| source_file | tgb |
| source_line | 8356 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | active_sell = sum(t.amount for t in ticks if t.direction == "sell") |
| section | 主动买入 vs 主动卖出 (按成交方向分) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 134. big_active_buy

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000935 |
| source_file | tgb |
| source_line | 8359 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | big_active_buy = sum(t.amount for t in ticks if t.direction == "buy" and t.amount > 500000) |
| section | 大单主动买入(>50万元的单笔成交) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 135. big_active_sell

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000936 |
| source_file | tgb |
| source_line | 8360 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | big_active_sell = sum(t.amount for t in ticks if t.direction == "sell" and t.amount > 500000) |
| section | 大单主动买入(>50万元的单笔成交) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 136. drop_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000957 |
| source_file | tgb |
| source_line | 8593 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | drop_volume = stock.volume_last(5) / stock.avg_5min_volume  # 5分钟量能放大倍数 |
| section | 急跌识别 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 137. current_price

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000960 |
| source_file | tgb |
| source_line | 8629 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | current_price = stock.close |
| section | 量化规则 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 138. reversal_board_quality

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000985 |
| source_file | tgb |
| source_line | 8833 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 552: `reversal_board_quality` - 反包涨停质量评分因子 |
| section | 来源: 淘股吧职业短线选手的资金管理经验 > 二十六、反包修复 / 龙回头二波 / 情绪冰点转折 / 断板后走势因子群 > 26.1 反包涨停因子群 > Factor 552: `reversal_board_quality` - 反包涨停质量评分因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 139. prev_drop

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000986 |
| source_file | tgb |
| source_line | 8839 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | prev_drop = stock.pct_change_t1  # T-1涨跌幅 |
| section | 前提: T-1日大跌(跌幅>-5%)或断板, T日涨停 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 140. vol_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000988 |
| source_file | tgb |
| source_line | 8847 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | vol_ratio = stock.volume_t0 / stock.volume_t1 |
| section | 1. 放量程度: T日成交量 vs T-1日 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 141. trough_price

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000991 |
| source_file | tgb |
| source_line | 8877 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | trough_price = min(stock.low_prices_after_limit)  # 涨停后最低价 |
| section | 涨停后回调幅度 vs 反包概率 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 142. yesterday_limit_premium

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001020 |
| source_file | tgb |
| source_line | 9111 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | yesterday_limit_premium = market.yesterday_limit_up_avg_return |
| section | 维度4: 昨日涨停表现(溢价为负) |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 143. open_board_rate

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001021 |
| source_file | tgb |
| source_line | 9116 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | open_board_rate = market.open_board_count / max(market.limit_up_attempt_count, 1) |
| section | 维度5: 炸板率偏高 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 144. limit_premium_decay_regime

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001027 |
| source_file | tgb |
| source_line | 9200 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 563: `limit_premium_decay_regime` - 涨停溢价衰减regime因子 |
| section | 来源: 淘股吧情绪周期3.0, 养家心法"冰点期率先涨停 = 下一周期核心" > Factor 563: `limit_premium_decay_regime` - 涨停溢价衰减regime因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 145. premiums

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001028 |
| source_file | tgb |
| source_line | 9206 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | premiums = market_history.yesterday_limit_up_avg_returns[-lookback:] |
| section | 跟踪过去N天的涨停溢价(昨日涨停股今日平均涨跌幅)趋势 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 146. today_promoted

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001056 |
| source_file | tgb |
| source_line | 9349 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | today_promoted = sum(1 for s in prev_day_n_board if s.today_limit_up) |
| section | 这是情绪周期最核心的量化观测指标之一 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 147. limit_up_count_10d

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001062 |
| source_file | tgb |
| source_line | 9403 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | limit_up_count_10d = stock.limit_up_count_last_10d |
| section | 维度2: 近期活跃度 — 近10日涨停次数 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 148. avg_trade_size

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001071 |
| source_file | tgb |
| source_line | 9471 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | avg_trade_size = stock.total_amount / max(stock.trade_count, 1) |
| section | 特征1: 小单密集成交(每笔成交额偏小但频率极高) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 149. cap_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001075 |
| source_file | tgb |
| source_line | 9520 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | cap_ratio = stock.float_market_cap / max(sector.leader_float_cap, 1) |
| section | 条件4: 流通市值与原龙头接近(容量够) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 150. peak_limit_up

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001077 |
| source_file | tgb |
| source_line | 9542 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | peak_limit_up = sector.max_limit_up_count_in_cycle |
| section | 维度1: 板块内涨停家数峰值 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 151. sector_avg_amount

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001078 |
| source_file | tgb |
| source_line | 9545 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | sector_avg_amount = sector.avg_daily_amount_5d |
| section | 维度2: 板块日均成交额 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 152. open_board_quality

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001097 |
| source_file | tgb |
| source_line | 9641 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 575: `open_board_quality` - 炸板质量分级因子 |
| section | 来源: 淘股吧妖股形态因子(§十三), 连板晋级率统计 > 27.4 炸板/烂板分析因子群 > Factor 575: `open_board_quality` - 炸板质量分级因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 153. open_count

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001098 |
| source_file | tgb |
| source_line | 9648 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | open_count = stock.limit_open_count_today  # 今日炸板次数 |
| section | 炸板(涨停打开)不全是坏事, 关键看炸板质量 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 154. close_to_limit

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001105 |
| source_file | tgb |
| source_line | 9666 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | close_to_limit = (stock.close - stock.prev_close) / stock.prev_close |
| section | 未回封 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 155. gap

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001135 |
| source_file | tgb |
| source_line | 9878 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | gap = stock.open / stock.prev_close - 1 |
| section | 复牌首日缺口+承接质量 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 156. refill_seconds

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001149 |
| source_file | tgb |
| source_line | 10008 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | refill_seconds = stock.seal_refill_seconds_median |
| section | 封单被成交后恢复原规模所需秒数 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 157. trigger_days

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001164 |
| source_file | tgb |
| source_line | 10184 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | trigger_days = cb.days_close_above_130pct_in_30d |
| section | 常见触发框架: 15/30天收盘价 >= 转股价130% |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 158. active_buy

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001174 |
| source_file | tgb |
| source_line | 10300 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | active_buy = stock.active_buy_amount_10m |
| section | 核心看大单砸盘是否被有效承接 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 159. prev_close_reclaim_speed

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001181 |
| source_file | tgb |
| source_line | 10323 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 603: `prev_close_reclaim_speed` - 回收昨收速度因子 |
| section | 来源: 淘股吧承接力复盘框架, "砸不死才是强" > Factor 603: `prev_close_reclaim_speed` - 回收昨收速度因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 160. weak_to_strong_volume_efficiency

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001187 |
| source_file | tgb |
| source_line | 10353 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 604: `weak_to_strong_volume_efficiency` - 弱转强量价效率因子 |
| section | 来源: 淘股吧弱转强确认细则, "先收昨收再谈转强" > 33.2 弱转强深度因子群 > Factor 604: `weak_to_strong_volume_efficiency` - 弱转强量价效率因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 161. repaired

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001195 |
| source_file | tgb |
| source_line | 10382 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | repaired = [s for s in sector.members if s.reclaimed_prev_close] |
| section | 龙头修复后, 跟风票是否同步回暖 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 162. recovering

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001199 |
| source_file | tgb |
| source_line | 10426 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | recovering = [s for s in sector.members if s.return_1330_to_close > 0.03] |
| section | 13:30后回流的板块广度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 163. trapped_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001211 |
| source_file | tgb |
| source_line | 10524 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | trapped_volume = stock.volume_in_overhang_zone |
| section | 当前价到左侧压力区之间的历史成交密度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 164. vacuum_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001213 |
| source_file | tgb |
| source_line | 10526 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | vacuum_ratio = 1 - trapped_volume / max(floating_shares, 1) |
| section | 当前价到左侧压力区之间的历史成交密度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 165. breakout_gain

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001215 |
| source_file | tgb |
| source_line | 10539 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | breakout_gain = stock.close / max(stock.left_pressure_price, 1) - 1 |
| section | 突破左侧高点所需成交额/涨幅效率 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 166. breakout_amount

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001216 |
| source_file | tgb |
| source_line | 10540 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | breakout_amount = stock.amount_on_breakout_day / max(stock.float_market_cap, 1) |
| section | 突破左侧高点所需成交额/涨幅效率 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 167. passed

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001218 |
| source_file | tgb |
| source_line | 10543 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | passed = stock.close > stock.left_pressure_price and stock.close_near_day_high |
| section | 突破左侧高点所需成交额/涨幅效率 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 168. volume_price_pivot_stability

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001222 |
| source_file | tgb |
| source_line | 10590 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 614: `volume_price_pivot_stability` - 量价枢轴稳定因子 |
| section | 来源: 淘股吧套牢盘消化逻辑, "突破后第二天不死才是真释放" > Factor 614: `volume_price_pivot_stability` - 量价枢轴稳定因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 169. volume_decay

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001224 |
| source_file | tgb |
| source_line | 10597 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | volume_decay = stock.avg_volume_3d_after_breakout / max(stock.breakout_day_volume, 1) |
| section | 突破后围绕新平台的稳定度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 170. final_close_gap

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001227 |
| source_file | tgb |
| source_line | 10632 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | final_close_gap = stock.close / stock.low_limit - 1 |
| section | 跌停后被撬开, 判断是衰竭还是继续下跌中继 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 171. close_back

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001238 |
| source_file | tgb |
| source_line | 10708 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | close_back = stock.close > stock.open or stock.close > stock.prev_close |
| section | 恐慌是否一次性释放完毕 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 172. sub_new_open_board_timing

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001255 |
| source_file | tgb |
| source_line | 10833 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 624: `sub_new_open_board_timing` - 次新股开板时机因子 |
| section | 来源: 淘股吧高位卡监管经验, "有预期也要扣掉停牌风险" > 三十八、次新股/新股开板/注册制次新因子群 > 38.1 次新股开板因子群 > Factor 624: `sub_new_open_board_timing` - 次新股开板时机因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 173. open_board_day_amplitude

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001258 |
| source_file | tgb |
| source_line | 10841 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | open_board_day_amplitude = stock.open_board_day_amplitude |
| section | 新股连板后首次开板的时机特征 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 174. first_day_return

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001261 |
| source_file | tgb |
| source_line | 10861 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | first_day_return = stock.first_day_close / stock.issue_price - 1 |
| section | 注册制新股上市首日换手率与涨幅的配合 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 175. total_buy_amount

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001276 |
| source_file | tgb |
| source_line | 10940 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | total_buy_amount = stock.top5_buy_amount |
| section | 龙虎榜买入前5席位中知名游资的集中度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 176. known_amount

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001277 |
| source_file | tgb |
| source_line | 10941 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | known_amount = sum(s.amount for s in known_seats) |
| section | 龙虎榜买入前5席位中知名游资的集中度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 177. hot_buy

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001281 |
| source_file | tgb |
| source_line | 10961 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | hot_buy = stock.hot_money_buy_amount |
| section | 龙虎榜中机构席位与游资席位的买入力量对比 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 178. reduce_amount_30d

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001311 |
| source_file | tgb |
| source_line | 11175 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | reduce_amount_30d = stock.insider_reduce_amount_30d |
| section | 重要股东近期净减持占流通市值的比例 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 179. increase_amount_30d

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001312 |
| source_file | tgb |
| source_line | 11176 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | increase_amount_30d = stock.insider_increase_amount_30d |
| section | 重要股东近期净减持占流通市值的比例 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 180. net_sell

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001313 |
| source_file | tgb |
| source_line | 11177 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | net_sell = reduce_amount_30d - increase_amount_30d |
| section | 重要股东近期净减持占流通市值的比例 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 181. bt_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001319 |
| source_file | tgb |
| source_line | 11219 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | bt_volume = stock.block_trade_volume |
| section | 大宗交易后次日市场承接力度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 182. next_day_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001320 |
| source_file | tgb |
| source_line | 11220 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | next_day_volume = stock.next_day_volume |
| section | 大宗交易后次日市场承接力度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 183. absorb_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001322 |
| source_file | tgb |
| source_line | 11223 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | absorb_ratio = next_day_volume / max(bt_volume * 3, 1) |
| section | 大宗交易后次日市场承接力度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 184. board_height_ceiling

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001323 |
| source_file | tgb |
| source_line | 11252 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 641: `board_height_ceiling` - 连板高度天花板因子 |
| section | 来源: 淘股吧大宗后走势分析, "次日能消化大宗量的3倍以上就没问题" > 四十二、连板高度梯队/板块轮动传导/题材生命周期因子群 > 42.1 连板高度/梯队因子群 > Factor 641: `board_height_ceiling` - 连板高度天花板因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 185. days_active

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001342 |
| source_file | tgb |
| source_line | 11342 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | days_active = theme.days_since_first_limit_up |
| section | 题材从发酵到退潮的生命周期定位 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 186. margin_buy

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001352 |
| source_file | tgb |
| source_line | 11391 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | margin_buy = stock.margin_buy_amount_today |
| section | 融资买入额占当日成交额的比例 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 187. total_amount

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001353 |
| source_file | tgb |
| source_line | 11392 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | total_amount = stock.total_turnover_today |
| section | 融资买入额占当日成交额的比例 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 188. short_balance_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001362 |
| source_file | tgb |
| source_line | 11441 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | short_balance_ratio = stock.short_balance / max(stock.float_market_cap, 1) |
| section | 融券余额占流通市值比例 + 融券卖出异动 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 189. short_sell_today

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001363 |
| source_file | tgb |
| source_line | 11442 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | short_sell_today = stock.short_sell_amount_today |
| section | 融券余额占流通市值比例 + 融券卖出异动 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 190. short_sell_avg

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001364 |
| source_file | tgb |
| source_line | 11443 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | short_sell_avg = stock.short_sell_amount_20d_avg |
| section | 融券余额占流通市值比例 + 融券卖出异动 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 191. algo_volume_pct

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001397 |
| source_file | tgb |
| source_line | 11634 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | algo_volume_pct = stock.estimated_algo_volume_pct |
| section | 量化策略在该股上的拥挤程度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 192. volumes

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001402 |
| source_file | tgb |
| source_line | 11657 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | volumes = stock.volume_per_5m_slice |
| section | 成交量在各时间切片的均匀度(量化越多越均匀) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 193. is_algo_heavy

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001404 |
| source_file | tgb |
| source_line | 11675 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | is_algo_heavy = stock.estimated_algo_volume_pct > 0.5 |
| section | 选择量化策略失效的窗口介入 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 194. us_market_close

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001418 |
| source_file | tgb |
| source_line | 11777 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | us_market_close = market.sp500_overnight_return |
| section | 隔夜外盘+期指夜盘+富时A50对A股情绪的提前反映 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 195. composite

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001420 |
| source_file | tgb |
| source_line | 11780 |
| data_needs | ['cross_market', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | composite = 0.5 * a50_overnight_return + 0.3 * us_market_close + 0.2 * hk_pre_market |
| section | 隔夜外盘+期指夜盘+富时A50对A股情绪的提前反映 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 196. avg_20d

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001450 |
| source_file | tgb |
| source_line | 11942 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | avg_20d = stock.turnover_rate_20d_avg |
| section | 量化规则 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 197. volume_structure_quality

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001453 |
| source_file | tgb |
| source_line | 11959 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 668: `volume_structure_quality` - 量能结构质量因子 |
| section | 来源: 淘股吧量能分析, "放量方向决定性质: 涨放量是启动, 跌放量是出货" > Factor 668: `volume_structure_quality` - 量能结构质量因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 198. up_days_avg_vol

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001454 |
| source_file | tgb |
| source_line | 11965 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | up_days_avg_vol = stock.avg_volume_on_up_days_10d |
| section | 上涨时放量、回调时缩量的健康度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 199. down_days_avg_vol

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001455 |
| source_file | tgb |
| source_line | 11966 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | down_days_avg_vol = stock.avg_volume_on_down_days_10d |
| section | 上涨时放量、回调时缩量的健康度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 200. vol_percentile_60d

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001458 |
| source_file | tgb |
| source_line | 11987 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | vol_percentile_60d = stock.volume_percentile_60d |
| section | 成交量缩至近期极低水平后的变盘信号 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 201. vol_percentile_20d

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001459 |
| source_file | tgb |
| source_line | 11988 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | vol_percentile_20d = stock.volume_percentile_20d |
| section | 成交量缩至近期极低水平后的变盘信号 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 202. volume_price_divergence_alert

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001461 |
| source_file | tgb |
| source_line | 12000 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 670: `volume_price_divergence_alert` - 量价背离预警因子 |
| section | 来源: 淘股吧地量选股, "地量之后必有变盘, 方向看基本面和题材" > Factor 670: `volume_price_divergence_alert` - 量价背离预警因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 203. price_new_high_5d

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001462 |
| source_file | tgb |
| source_line | 12006 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | price_new_high_5d = stock.close >= stock.high_5d * 0.99 |
| section | 价格创新高但成交量递减的背离 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 204. vol_declining

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001463 |
| source_file | tgb |
| source_line | 12007 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | vol_declining = stock.volume < stock.volume_5d_avg * 0.7 |
| section | 价格创新高但成交量递减的背离 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 205. price_new_low_5d

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001464 |
| source_file | tgb |
| source_line | 12009 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | price_new_low_5d = stock.close <= stock.low_5d * 1.01 |
| section | 价格创新高但成交量递减的背离 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 206. vol_declining_low

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001465 |
| source_file | tgb |
| source_line | 12010 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | vol_declining_low = stock.volume < stock.volume_5d_avg * 0.7 |
| section | 价格创新高但成交量递减的背离 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 207. late_chase_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001480 |
| source_file | tgb |
| source_line | 12109 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | late_chase_volume = stock.volume_last_30m / max(stock.volume_first_30m, 1) |
| section | 散户追高情绪的量化 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 208. second_break

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001490 |
| source_file | tgb |
| source_line | 12167 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | second_break = stock.close > first_high |
| section | N型: 拉升→回调不破低→二次突破前高 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 209. drop_volume_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001502 |
| source_file | tgb |
| source_line | 12226 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | drop_volume_ratio = stock.drop_10m_volume / max(stock.avg_10m_volume, 1) |
| section | 短时间内大幅下跌的瀑布式杀跌 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 210. current_gain

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001511 |
| source_file | tgb |
| source_line | 12287 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | current_gain = stock.close / entry_price - 1 |
| section | 浮盈达到一定比例后激活移动止盈 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 211. super_large

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001542 |
| source_file | tgb |
| source_line | 12501 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | super_large = stock.super_large_order_amount |
| section | 超大单(>100万)成交占比 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 212. total

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001543 |
| source_file | tgb |
| source_line | 12502 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | total = stock.total_turnover |
| section | 超大单(>100万)成交占比 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 213. historical_limit_up_dna

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001558 |
| source_file | tgb |
| source_line | 12603 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Factor 693: `historical_limit_up_dna` - 历史涨停基因因子 |
| section | 来源: 淘股吧股性分析, "股性活跃的票短线才有肉" > Factor 693: `historical_limit_up_dna` - 历史涨停基因因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 214. records

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001559 |
| source_file | tgb |
| source_line | 12609 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | records = stock.limit_up_next_day_records_1y |
| section | 该股历史上涨停后的次日表现统计 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 215. bid_depth

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001574 |
| source_file | tgb |
| source_line | 12713 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | bid_depth = sum(stock.bid_volume_levels[:5]) |
| section | 买盘5档挂单量与卖盘5档挂单量的失衡 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 216. ask_depth

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001575 |
| source_file | tgb |
| source_line | 12714 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | ask_depth = sum(stock.ask_volume_levels[:5]) |
| section | 买盘5档挂单量与卖盘5档挂单量的失衡 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 217. bid_slope

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001585 |
| source_file | tgb |
| source_line | 12762 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | bid_slope = linear_slope(stock.bid_volume_levels[:10]) |
| section | 买卖盘挂单量随价格距离的衰减速度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 218. ask_slope

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001586 |
| source_file | tgb |
| source_line | 12763 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | ask_slope = linear_slope(stock.ask_volume_levels[:10]) |
| section | 买卖盘挂单量随价格距离的衰减速度 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 219. visible_bid

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001589 |
| source_file | tgb |
| source_line | 12783 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | visible_bid = sum(stock.bid_volume_levels[:5]) |
| section | 实际成交远超可见挂单量, 暗示有隐藏订单(冰山单) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 220. actual_buy_volume_5m

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001590 |
| source_file | tgb |
| source_line | 12784 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | actual_buy_volume_5m = stock.actual_buy_volume_last_5m |
| section | 实际成交远超可见挂单量, 暗示有隐藏订单(冰山单) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 221. hidden_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001591 |
| source_file | tgb |
| source_line | 12786 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | hidden_ratio = actual_buy_volume_5m / max(visible_bid, 1) |
| section | 实际成交远超可见挂单量, 暗示有隐藏订单(冰山单) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 222. Normalized_OFI

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001642 |
| source_file | short |
| source_line | 218 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Normalized_OFI = OFI_window / total_depth_or_volume |
| section | 短线因子 > 4. 订单流动态因子 OFI / MLOFI > 4.1 L1 OFI |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 223. buy_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001645 |
| source_file | short |
| source_line | 259 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | 主动买量 | `buy_volume` | 吃卖盘成交量 | |
| section | 短线因子 > 5. 成交主动性因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 224. sell_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001646 |
| source_file | short |
| source_line | 260 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | 主动卖量 | `sell_volume` | 吃买盘成交量 | |
| section | 短线因子 > 5. 成交主动性因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 225. theme_capacity_by_amount

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001791 |
| source_file | short |
| source_line | 1106 |
| data_needs | ['daily_ohlcv', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `theme_capacity_by_amount` | 题材成份近5日成交额合计 / 全市场成交额 | 大题材能承接大资金，小题材容易一日游 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.5 “龙头/题材容量”因子补强 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 226. theme_capacity_by_float_mv

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001792 |
| source_file | short |
| source_line | 1107 |
| data_needs | ['sector_theme', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `theme_capacity_by_float_mv` | 题材成份流通市值合计 / 全市场流通市值 | 容量过小的题材难以持续 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.5 “龙头/题材容量”因子补强 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 227. theme_follower_feedback

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001797 |
| source_file | short |
| source_line | 1112 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `theme_follower_feedback` | 龙头涨停后跟风股次日平均收益 | 龙头带动力 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.5 “龙头/题材容量”因子补强 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 228. sentiment_liquidity_boost

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001829 |
| source_file | short |
| source_line | 1173 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `sentiment_liquidity_boost` | 正向情绪变化对成交量/换手率的促进 | 文本情绪 + 日线 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.8 社交热度/股吧情绪因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 229. abnormal_3d_deviation

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001830 |
| source_file | short |
| source_line | 1186 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `abnormal_3d_deviation` | 近3个交易日个股涨跌幅 - 对应指数涨跌幅 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.9 异常监管因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 230. next_close_return

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001839 |
| source_file | short |
| source_line | 1227 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `next_close_return` | 次日收盘收益 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.10 对训练集的建议修正 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 231. next_red_close

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001840 |
| source_file | short |
| source_line | 1228 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `next_red_close` | 次日是否红盘收 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.10 对训练集的建议修正 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 232. next_board_success

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001841 |
| source_file | short |
| source_line | 1229 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `next_board_success` | 次日是否涨停/连板 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.10 对训练集的建议修正 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 233. concept_membership_snapshot

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001847 |
| source_file | short |
| source_line | 1279 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 3. 建立 `concept_membership_snapshot`，把涨停股映射到概念板块，做题材涨停密度和题材容量。 |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.12 这轮扫描后的优先开发顺序 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 234. feature_i

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001857 |
| source_file | short |
| source_line | 1391 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | feature_i = field_{i%6}(t - i//6) / ref(close, 0)   # 全部对当日收盘归一化 |
| section | 短线因子 > 34. 经典技术指标有效性实证 > 34.6 Qlib Alpha360 结构 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 235. at_limit

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001864 |
| source_file | short |
| source_line | 1517 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | 涨停/跌停 | 收益截断在 ±10%/±20%，盘口因子标记为 `at_limit` | |
| section | 短线因子 > 36. 特征工程最佳实践 > 36.4 A股特殊处理 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 236. down_vol

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001876 |
| source_file | short |
| source_line | 1687 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | down_vol = df[df['kind']=='D']['volume'].sum() |
| section | kind: U=买入主动, D=卖出主动, E=中性 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 237. WTI_close_change

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001894 |
| source_file | short |
| source_line | 1822 |
| data_needs | ['sector_theme', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | WTI 原油隔夜 | `WTI_close_change` | 05:00 | 石化/能源板块 ~55-62% | |
| section | Microprice（5档盘口，实时） > 40. 跨市场因子 > 40.2 跨市场因子矩阵 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 238. Crowding_i

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001922 |
| source_file | short |
| source_line | 2316 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Crowding_i = (1/3) * [Turnover_long/Turnover_short + Vol_long/Vol_short + Beta_long/Beta_short] |
| section | 截面回归正交化 > 50. 因子衰减与拥挤度 > 50.1 A股因子拥挤度度量方法 > 券商主流方法汇总 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 239. News_Surge_t

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001948 |
| source_file | short |
| source_line | 2978 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | News_Surge_t = (News_Volume_t - MA20(News_Volume)) / std20(News_Volume) |
| section | 截面回归正交化 > 62. NLP事件驱动因子 > 62.3 突发事件/新闻异常量因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 240. Buy_Signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001957 |
| source_file | short |
| source_line | 3055 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Buy_Signal = (开板后跌幅 > 20%) AND (换手率 < 开板日换手率×0.3) AND (量比 < 0.8) |
| section | 截面回归正交化 > 63. IPO/次新股量化因子 > 63.1 新股开板后最优介入因子 (核准制) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 241. Sub_New_Factor

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001961 |
| source_file | short |
| source_line | 3103 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Sub_New_Factor = w₁ × Rev_20d + w₂ × 换手率衰减斜率 + w₃ × 相对行业PE + w₄ × 解禁日距离 |
| section | 注册制IPO收益分布 (2020-2025统计) > 63.3 次新股动量/反转因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 242. Buy_Signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001968 |
| source_file | short |
| source_line | 3154 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Buy_Signal = (Break_Depth < -15%) AND (Break_Duration > 20) AND (换手率触底回升) AND (大盘企稳) |
| section | 注册制IPO收益分布 (2020-2025统计) > 63.5 破发股回升因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 243. PCR_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001990 |
| source_file | short |
| source_line | 3565 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | PCR_volume = Put成交量 / Call成交量 |
| section | 注册制IPO收益分布 (2020-2025统计) > 68. 期权隐含波动率因子 > 68.3 Put-Call Ratio因子 (PCR) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 244. V_t

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002011 |
| source_file | short |
| source_line | 3853 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | V_t = 换手率 (作为持仓概率的代理) |
| section | 注册制IPO收益分布 (2020-2025统计) > 71. 行为金融异象因子 > 71.1 处置效应因子 / 资本利得突出度 (CGO) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 245. CGO_simple

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002012 |
| source_file | short |
| source_line | 3856 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | CGO_simple = (P_t - MA_turnover_weighted) / P_t |
| section | 注册制IPO收益分布 (2020-2025统计) > 71. 行为金融异象因子 > 71.1 处置效应因子 / 资本利得突出度 (CGO) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 246. Attention

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002016 |
| source_file | short |
| source_line | 3890 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Attention = rank(Abnormal_Turnover) + rank(ΔBSI) + rank(NewsShock) |
| section | 注册制IPO收益分布 (2020-2025统计) > 71. 行为金融异象因子 > 71.2 关注度因子 (Investor Attention Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 247. VOL_GAIN

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002021 |
| source_file | short |
| source_line | 3973 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | VOL_GAIN = MA(Turnover | R_cum>0) / MA(Turnover | R_cum<0) |
| section | 注册制IPO收益分布 (2020-2025统计) > 71. 行为金融异象因子 > 71.5 过度自信因子 (Overconfidence Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 248. OC_simple

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002022 |
| source_file | short |
| source_line | 3976 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | OC_simple = Turnover_rank_20d × sign(Return_60d) |
| section | 注册制IPO收益分布 (2020-2025统计) > 71. 行为金融异象因子 > 71.5 过度自信因子 (Overconfidence Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 249. INV_t

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002044 |
| source_file | short |
| source_line | 4397 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | INV_t = -Σ(sign(ret_i) × volume_i) / Σ(volume_i), 20日滚动 |
| section | 注册制IPO收益分布 (2020-2025统计) > 74. 微观结构进阶因子 > 74.7 做市商存货风险代理 (Inventory Risk) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 250. SSVR_t

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002047 |
| source_file | short |
| source_line | 4465 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | SSVR_t = 融券卖出额_t / 总成交额_t |
| section | 注册制IPO收益分布 (2020-2025统计) > 75. 融资融券信号深化 > 75.3 融券卖出占比因子 (SSVR) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 251. r_last

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002067 |
| source_file | short |
| source_line | 5098 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | r_last  = ln(P_close) - ln(P_13:00)   (下午收益) |
| section | 注册制IPO收益分布 (2020-2025统计) > 81. 高频Alpha信号 (Intraday / High-Frequency Alpha Signals) > 81.1 日内动量因子 (Intraday Momentum) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 252. r_overnight

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002071 |
| source_file | short |
| source_line | 5122 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | r_overnight = ln(P_open_t) - ln(P_close_{t-1}) |
| section | 注册制IPO收益分布 (2020-2025统计) > 81. 高频Alpha信号 (Intraday / High-Frequency Alpha Signals) > 81.2 隔夜收益异象 (Overnight Return Anomaly) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 253. r_day

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002073 |
| source_file | short |
| source_line | 5129 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | r_day = ln(P_close_t) - ln(P_open_t) |
| section | 注册制IPO收益分布 (2020-2025统计) > 81. 高频Alpha信号 (Intraday / High-Frequency Alpha Signals) > 81.2 隔夜收益异象 (Overnight Return Anomaly) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 254. r_night

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002074 |
| source_file | short |
| source_line | 5130 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | r_night = ln(P_open_t) - ln(P_close_{t-1}) |
| section | 注册制IPO收益分布 (2020-2025统计) > 81. 高频Alpha信号 (Intraday / High-Frequency Alpha Signals) > 81.2 隔夜收益异象 (Overnight Return Anomaly) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 255. Close_Impact

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002082 |
| source_file | short |
| source_line | 5201 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Close_Impact = (P_close - P_14:57) / P_14:57  (最后3分钟价格变动) |
| section | 注册制IPO收益分布 (2020-2025统计) > 81. 高频Alpha信号 (Intraday / High-Frequency Alpha Signals) > 81.5 收盘集合竞价冲击因子 (Close Auction Impact) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 256. StealthTrade

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002098 |
| source_file | short |
| source_line | 5322 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | StealthTrade = 同向连续小单的总金额 / 总成交额 |
| section | 注册制IPO收益分布 (2020-2025统计) > 82. 另类高频因子 (Alternative High-Frequency Factors) > 82.4 大单识别 / 隐藏大单因子 (Large/Stealth Trade Detection) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 257. VolDistFactor

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002107 |
| source_file | short |
| source_line | 5359 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | VolDistFactor = VolAnomaly * sign(CloseSurge - MedianCloseSurge) |
| section | 注册制IPO收益分布 (2020-2025统计) > 82. 另类高频因子 (Alternative High-Frequency Factors) > 82.5 日内成交量分布异常因子 (Intraday Volume Distribution Anomaly) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 258. Image_t

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002115 |
| source_file | short |
| source_line | 5474 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Image_t = render_candlestick(OHLCV[t-20:t])  # 20日K线图渲染为64x64像素 |
| section | 注册制IPO收益分布 (2020-2025统计) > 83. 技术形态识别因子 (Technical Pattern Recognition Factors) > 83.3 CNN图像识别因子 (CNN Chart Image Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 259. Breakout_Factor

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002116 |
| source_file | short |
| source_line | 5492 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Breakout_Factor = Sign * Strength * Volume_Confirm |
| section | 注册制IPO收益分布 (2020-2025统计) > 83. 技术形态识别因子 (Technical Pattern Recognition Factors) > 83.4 突破确认因子 (Breakout Confirmation Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 260. KAMA_t

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002129 |
| source_file | short |
| source_line | 5654 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | KAMA_t = KAMA_{t-1} + SC * (Close_t - KAMA_{t-1}) |
| section | 注册制IPO收益分布 (2020-2025统计) > 84. 趋势强度 / 波浪因子 (Trend Strength / Wave Factors) > 84.5 自适应动量因子 (Adaptive Momentum, KAMA-based) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 261. Profit_Ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002131 |
| source_file | short |
| source_line | 5688 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Profit_Ratio = integral(CDF(Price) * Volume_weight) |
| section | 注册制IPO收益分布 (2020-2025统计) > 85. 筹码分布 / 成本因子 (Chip Distribution / Cost Factors) > 85.1 获利盘比例因子 (Profit Ratio Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 262. ASR

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002132 |
| source_file | short |
| source_line | 5716 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | ASR = (P_90 - P_10) / Close_t |
| section | 注册制IPO收益分布 (2020-2025统计) > 85. 筹码分布 / 成本因子 (Chip Distribution / Cost Factors) > 85.2 成本集中度因子 (Cost Concentration, ASR) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 263. w_i

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002141 |
| source_file | short |
| source_line | 5765 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | w_i = Turnover_i * Π_{j=i+1}^{t} (1 - Turnover_j) |
| section | 注册制IPO收益分布 (2020-2025统计) > 85. 筹码分布 / 成本因子 (Chip Distribution / Cost Factors) > 85.4 换手率衰减成本因子 (Turnover-Weighted Cost Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 264. Cost_Dev

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002143 |
| source_file | short |
| source_line | 5772 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Cost_Dev = (Close_t - WAC_t) / WAC_t |
| section | 注册制IPO收益分布 (2020-2025统计) > 85. 筹码分布 / 成本因子 (Chip Distribution / Cost Factors) > 85.4 换手率衰减成本因子 (Turnover-Weighted Cost Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 265. Cost_Dev_Simple

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002145 |
| source_file | short |
| source_line | 5776 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Cost_Dev_Simple = (Close - EMA_Cost) / EMA_Cost |
| section | 注册制IPO收益分布 (2020-2025统计) > 85. 筹码分布 / 成本因子 (Chip Distribution / Cost Factors) > 85.4 换手率衰减成本因子 (Turnover-Weighted Cost Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 266. Net_Buy_Ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002151 |
| source_file | short |
| source_line | 5903 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Net_Buy_Ratio = (Buy_Amount - Sell_Amount) / Total_MktCap |
| section | 超预期大但公告日反应不充分的股票, 后续漂移空间更大 > 86.4 大股东/高管增减持因子 (Insider Net Purchase Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 267. BT_Discount

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002154 |
| source_file | short |
| source_line | 5926 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | BT_Discount = (P_block - P_close) / P_close  (大宗交易成交价/收盘价偏离) |
| section | 过去N天大股东/高管净买入金额占总市值比 > 86.5 大宗交易折价因子 (Block Trade Discount Factor) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 268. RISM_abnormal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002189 |
| source_file | short |
| source_line | 6270 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | RISM_abnormal = (PostVolume / MA20_PostVolume) * Sentiment |
| section | 高值代表市场关注度提升 > 89. NLP / 文本 / 舆情因子 (NLP & Sentiment Factors) > 89.3 社交媒体散户情绪因子 (Retail Investor Sentiment, RISM) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 269. PCR_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002207 |
| source_file | short |
| source_line | 6482 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | PCR_volume = Volume_put / Volume_call |
| section | 高值代表市场关注度提升 > 91. 期权隐含信息因子 (Option-Implied Factors) > 91.3 认沽认购比率因子 (Put-Call Ratio, PCR) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 270. ILLIQ_classic

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002236 |
| source_file | short |
| source_line | 6790 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | ILLIQ_classic = (1/D) · Σ |r_i,d| / Volume_d   # 原始Amihud |
| section | 高频版: > 94. 流动性进阶因子 > 94.1 `AMIHUD_ADJ` - 改进Amihud非流动性因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 271. SignedVolume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002240 |
| source_file | short |
| source_line | 6812 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | SignedVolume = Volume × sign(r_t) (Lee-Ready法则标记方向) |
| section | SignedVolume = Volume × sign(r_t) (Lee-Ready法则标记方向) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 272. ATO

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002241 |
| source_file | short |
| source_line | 6824 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 94.3 `ATO` - 异常换手率因子 |
| section | Rolling 20日 > 94.3 `ATO` - 异常换手率因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 273. ATO

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002242 |
| source_file | short |
| source_line | 6830 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | ATO = (Turnover_20d - Turnover_120d) / std(Turnover_120d) |
| section | Rolling 20日 > 94.3 `ATO` - 异常换手率因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 274. TAM

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002244 |
| source_file | short |
| source_line | 6863 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 94.5 `TAM` - 换手率调整动量因子 |
| section | γ < 0 表示放量下跌后有反转(流动性好), γ绝对值小表示流动性差 > 94.5 `TAM` - 换手率调整动量因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 275. TAM

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002245 |
| source_file | short |
| source_line | 6871 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | TAM = MOM_12_1 - β₂·Turnover  # 剔除换手率影响 |
| section | 方法1: Fama-MacBeth回归 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 276. MBR

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002249 |
| source_file | short |
| source_line | 6942 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | MBR = Margin_Buy_Amount / Total_Turnover_Amount |
| section | 或: 融券余额 / 流通市值 > 95.2 `MARGIN_BUY_RATIO` - 融资买入占比因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 277. SVI

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002264 |
| source_file | short |
| source_line | 7060 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | SVI = Search Volume Index (百度指数) |
| section | SVI = Search Volume Index (百度指数) |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 278. NB_Flow

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002368 |
| source_file | short |
| source_line | 7893 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | NB_Flow = Net_Buy_amount / Free_Float_MktCap  # 日度 |
| section | 注册制版: Underpricing = Close_day1 / Offer_price - 1 > 103.4 `NB_FLOW` - 北向资金流因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 279. Margin_Buy_Ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002398 |
| source_file | short |
| source_line | 8193 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Margin_Buy_Ratio = Daily_Margin_Buy / Total_Market_Volume |
| section | 领先A股1-3个月 > 106. 量化择时因子 > 106.1 `MARGIN_MOMENTUM` - 融资余额动量因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 280. CRISI

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002399 |
| source_file | short |
| source_line | 8195 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | CRISI = f(融资余额占比, 融资买入额占比, 融券余额占比, 两融换手率) |
| section | CRISI综合指数(深交所): |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 281. PCR_Volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002406 |
| source_file | short |
| source_line | 8254 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | PCR_Volume = Put_Volume / Call_Volume    # 成交量PCR |
| section | 顶部背离: 指数新高但Breadth/New_HL下降 → 看空预警 > 106.4 `PCR_SENTIMENT` - 期权认沽认购比因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 282. SVI

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002430 |
| source_file | short |
| source_line | 8468 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | SVI = Search Volume Index |
| section | SVI = Search Volume Index |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 283. r_overnight

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002442 |
| source_file | short |
| source_line | 8577 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | r_overnight = ln(P_open_t / P_close_{t-1}) |
| section | 高正偏度 = 彩票型分布 = 散户偏好 = 被高估 > 109.3 `OVERNIGHT_RET` - 隔夜收益因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 284. LIMIT_HIT_FREQ

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002468 |
| source_file | short |
| source_line | 8817 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 111.4 `LIMIT_HIT_FREQ` - 涨停频率/涨停板彩票效应因子 |
| section | 高散户净买入 = 噪声交易需求 = 逆向信号 = 未来跑输 > 111.4 `LIMIT_HIT_FREQ` - 涨停频率/涨停板彩票效应因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 285. Z_CN

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002524 |
| source_file | short |
| source_line | 9392 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | Z_CN = f(NI/TA, WC/TA, RE/TA, Cash/CL, AR_Turnover_Change) |
| section | 中国改进版(吴世农&卢贤义 2001): |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 286. IND_CROWD_j

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002540 |
| source_file | short |
| source_line | 9526 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | IND_CROWD_j = z(Turnover_j) + z(Fund_Overweight_j) + z(Corr_j) + z(Valuation_j) |
| section | 集中度下降 → 行业趋势性机会, 可以配行业ETF > 117.5 `IND_CROWD` - 行业拥挤度因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 287. INSIDER_NET_i

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002575 |
| source_file | short |
| source_line | 9727 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | INSIDER_NET_i = (Insider_Buy_Amount - Insider_Sell_Amount) / Market_Cap_i |
| section | 内部人净买入比率 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 288. follower_drag_coeff

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002602 |
| source_file | short |
| source_line | 10002 |
| data_needs | ['limit_pool', 'sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | follower_drag_coeff = mean(sector_peers_next_day_return | leader_limit_up_today) |
| section | 带动系数: leader涨停后, 同板块其他股次日涨幅均值 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 289. stage

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002607 |
| source_file | short |
| source_line | 10018 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | stage = 3  # decaying: 炸板或低开 |
| section | 龙头生命周期: emerging(0) / confirmed(1) / mature(2) / decaying(3) |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 290. new_leader_emerge

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002610 |
| source_file | short |
| source_line | 10026 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | new_leader_emerge = (new_stock.board_height == 2 and new_stock.seal_time_rank == 1) |
| section | 老龙头衰退 + 新龙头崛起 = 切换信号 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 291. need_second_seal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002621 |
| source_file | short |
| source_line | 10073 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | need_second_seal = transition_amplitude > 0.12  # V型超过12%需二封确认 |
| section | 收割逻辑: "拉得太快从跌4到涨停筹码太不稳，要等二封" |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 292. last_wave_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002625 |
| source_file | short |
| source_line | 10092 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | last_wave_volume = volume_in_last_5min_before_limit |
| section | 冲板最后一波的质量(连板龙头作手:"攻击量必须是当日最大") |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 293. max_5min_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002626 |
| source_file | short |
| source_line | 10093 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | max_5min_volume = max(all_5min_volumes_today) |
| section | 冲板最后一波的质量(连板龙头作手:"攻击量必须是当日最大") |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 294. attack_quality

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002627 |
| source_file | short |
| source_line | 10094 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | attack_quality = last_wave_volume / max_5min_volume |
| section | 冲板最后一波的质量(连板龙头作手:"攻击量必须是当日最大") |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 295. quant_crowding

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002643 |
| source_file | short |
| source_line | 10167 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | quant_crowding = seal_order_fragmentation / historical_median_fragmentation |
| section | 低碎片化 = 传统大户封板 → 次日溢价更高 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 296. PREMIUM_DECAY_CURVE

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002644 |
| source_file | short |
| source_line | 10170 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 124.2 `PREMIUM_DECAY_CURVE` - 涨停溢价衰减曲线 |
| section | 低碎片化 = 传统大户封板 → 次日溢价更高 > 124.2 `PREMIUM_DECAY_CURVE` - 涨停溢价衰减曲线 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 297. late_seal_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002647 |
| source_file | short |
| source_line | 10188 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | late_seal_ratio = count(seal_time > 14:00) / total_limit_up_count |
| section | 游资主导: 封板时间集中在9:30-10:30, 溢价高, 连板率高 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 298. early_seal_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002648 |
| source_file | short |
| source_line | 10189 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | early_seal_ratio = count(seal_time < 10:30) / total_limit_up_count |
| section | 游资主导: 封板时间集中在9:30-10:30, 溢价高, 连板率高 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 299. REVERSAL_BOARD_QUALITY

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002657 |
| source_file | short |
| source_line | 10250 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 126.1 `REVERSAL_BOARD_QUALITY` - 反包涨停质量评分 |
| section | 强度 = 四步评分的加权平均 > 126. 反包涨停与龙回头二波因子 (Reversal Board & Leader Pullback Factors) > 126.1 `REVERSAL_BOARD_QUALITY` - 反包涨停质量评分 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 300. LIMIT_PREMIUM_REGIME

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002662 |
| source_file | short |
| source_line | 10329 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 127.3 `LIMIT_PREMIUM_REGIME` - 涨停溢价regime因子 |
| section | 强度 = 四步评分的加权平均 > 127. 情绪冰点转折与涨停溢价regime因子 (Freezing Point Reversal & Premium Regime) > 127.3 `LIMIT_PREMIUM_REGIME` - 涨停溢价regime因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 301. activity

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002667 |
| source_file | short |
| source_line | 10377 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | activity = 涨停频率×0.3 + 日均振幅×0.25 + 连板基因×0.25 + 妖股基因×0.2 |
| section | 强度 = 四步评分的加权平均 > 128. 辨识度与人气股量化因子 (Recognition & Popularity Quantification) > 128.2 `STOCK_PERSONALITY` - 股性活跃度因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 302. OPEN_BOARD_QUALITY

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002671 |
| source_file | short |
| source_line | 10428 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 129.3 `OPEN_BOARD_QUALITY` - 炸板质量分级 |
| section | 强度 = 四步评分的加权平均 > 129. 卡位补涨龙与妖股识别因子 (Substitute Leader & Monster Stock Detection) > 129.3 `OPEN_BOARD_QUALITY` - 炸板质量分级 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 303. PREV_CLOSE_RECLAIM_SPEED

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002704 |
| source_file | short |
| source_line | 10738 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 135.3 `PREV_CLOSE_RECLAIM_SPEED` - 回收昨收速度因子 |
| section | 强度 = 四步评分的加权平均 > 135. 真弱假弱与分歧承接因子 (True/False Weakness & Divergence Absorption) > 135.3 `PREV_CLOSE_RECLAIM_SPEED` - 回收昨收速度因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 304. WEAK_TO_STRONG_VOLUME_EFFICIENCY

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002705 |
| source_file | short |
| source_line | 10748 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 135.4 `WEAK_TO_STRONG_VOLUME_EFFICIENCY` - 弱转强量价效率因子 |
| section | 强度 = 四步评分的加权平均 > 135. 真弱假弱与分歧承接因子 (True/False Weakness & Divergence Absorption) > 135.4 `WEAK_TO_STRONG_VOLUME_EFFICIENCY` - 弱转强量价效率因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 305. VOLUME_PRICE_PIVOT_STABILITY

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002720 |
| source_file | short |
| source_line | 10863 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 137.5 `VOLUME_PRICE_PIVOT_STABILITY` - 量价枢轴稳定因子 |
| section | 强度 = 四步评分的加权平均 > 137. 筹码断层与左压突破因子 (Chip Vacuum & Left-Side Pressure Breakout) > 137.5 `VOLUME_PRICE_PIVOT_STABILITY` - 量价枢轴稳定因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 306. SUB_NEW_OPEN_BOARD_TIMING

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002735 |
| source_file | short |
| source_line | 10986 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 140.1 `SUB_NEW_OPEN_BOARD_TIMING` - 次新股开板时机因子 |
| section | 强度 = 四步评分的加权平均 > 140. 次新股与新股开板因子 (Sub-New Stock & IPO Open Board Factors) > 140.1 `SUB_NEW_OPEN_BOARD_TIMING` - 次新股开板时机因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 307. discount

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002753 |
| source_file | short |
| source_line | 11142 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | discount = 1 - 大宗成交价/收盘价 |
| section | 强度 = 四步评分的加权平均 > 143. 大宗交易与股东增减持因子 (Block Trade & Insider Activity Factors) > 143.1 `BLOCK_TRADE_DISCOUNT_RATE` - 大宗交易折价率因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 308. BOARD_HEIGHT_CEILING

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002761 |
| source_file | short |
| source_line | 11199 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 144.1 `BOARD_HEIGHT_CEILING` - 连板高度天花板因子 |
| section | 强度 = 四步评分的加权平均 > 144. 连板高度梯队与板块轮动因子 (Board Height Tier & Sector Rotation Factors) > 144.1 `BOARD_HEIGHT_CEILING` - 连板高度天花板因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 309. composite

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002792 |
| source_file | short |
| source_line | 11471 |
| data_needs | ['daily_ohlcv', 'cross_market'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | composite = 0.5×A50隔夜涨跌 + 0.3×美股收盘涨跌 + 0.2×港股盘前涨跌 |
| section | 强度 = 四步评分的加权平均 > 148. 隔夜消息面与盘前情绪因子 (Overnight News & Pre-Market Sentiment Factors) > 148.4 `PRE_MARKET_SENTIMENT_SHIFT` - 盘前情绪转变因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 310. VOLUME_STRUCTURE_QUALITY

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002804 |
| source_file | short |
| source_line | 11562 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 150.2 `VOLUME_STRUCTURE_QUALITY` - 量能结构质量因子 |
| section | 强度 = 四步评分的加权平均 > 150. 换手率异动与量能结构因子 (Turnover Spike & Volume Structure Factors) > 150.2 `VOLUME_STRUCTURE_QUALITY` - 量能结构质量因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 311. VOLUME_PRICE_DIVERGENCE_ALERT

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002807 |
| source_file | short |
| source_line | 11585 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 150.4 `VOLUME_PRICE_DIVERGENCE_ALERT` - 量价背离预警因子 |
| section | 强度 = 四步评分的加权平均 > 150. 换手率异动与量能结构因子 (Turnover Spike & Volume Structure Factors) > 150.4 `VOLUME_PRICE_DIVERGENCE_ALERT` - 量价背离预警因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 312. HISTORICAL_LIMIT_UP_DNA

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002840 |
| source_file | short |
| source_line | 11878 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | 156.2 `HISTORICAL_LIMIT_UP_DNA` - 历史涨停基因因子 |
| section | 强度 = 四步评分的加权平均 > 156. 股性活跃度与历史涨停基因因子 (Stock Personality & Limit-Up DNA Factors) > 156.2 `HISTORICAL_LIMIT_UP_DNA` - 历史涨停基因因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 313. big_order_net_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002865 |
| source_file | explore |
| source_line | 210 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `big_order_net_ratio` | (大单买入额-大单卖出额) / 总成交额 | 主力净买入→次日看涨 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 4. 微观结构因子（最高价值维度） > 4.2 大单/超大单因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 314. informed_trading_prob

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002878 |
| source_file | explore |
| source_line | 233 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `informed_trading_prob` | VPIN（Volume-Synchronized Probability of Informed Trading） | 知情交易概率 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 4. 微观结构因子（最高价值维度） > 4.4 逐笔成交特征 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 315. main_force_net_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002881 |
| source_file | explore |
| source_line | 245 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `main_force_net_ratio` | 东方财富/同花顺 | 主力净流入 / 总成交额 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 5. 资金流与主力行为因子 > 5.1 主力资金流向 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 316. margin_buy_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002890 |
| source_file | explore |
| source_line | 264 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `margin_buy_ratio` | 融资买入额 / 总成交额 | 杠杆资金参与度 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 5. 资金流与主力行为因子 > 5.3 融资融券因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 317. eu_close_return

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002899 |
| source_file | explore |
| source_line | 289 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `eu_close_return` | 欧洲（DAX/FTSE）收盘涨跌幅 | 欧洲收盘→全球情绪传导 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 6. 跨资产/跨市场信号因子 > 6.1 全球指数联动 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 318. hk_close_return

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002900 |
| source_file | explore |
| source_line | 290 |
| data_needs | ['cross_market', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `hk_close_return` | 恒生指数当日涨跌 | 港股→A股强联动 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 6. 跨资产/跨市场信号因子 > 6.1 全球指数联动 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 319. limit_up_open_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002922 |
| source_file | explore |
| source_line | 345 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `limit_up_open_ratio` | 涨停打开比例 | 追涨意愿（不打开→情绪强） | |
| section | 因子探索：短线次日方向预测因子全景研究 > 7. 投资者情绪与注意力因子 > 7.3 市场情绪温度计 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 320. lunch_break_effect

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002951 |
| source_file | explore |
| source_line | 423 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `lunch_break_effect` | 上午收盘价 vs 下午开盘价 | 午休消化信息 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 9. 日内模式与收盘竞价因子 > 9.4 分时形态因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 321. main_force_net_strong_buy

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002952 |
| source_file | explore |
| source_line | 445 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `main_force_net_strong_buy` | 主力净流入 > 总成交额 5% | 大资金有明确方向 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 10. 条件预测：不预测所有样本 > 10.2 筛选高可预测性的条件因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 322. limit_up_seal_time

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003000 |
| source_file | explore |
| source_line | 700 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `limit_up_seal_time` | 涨停首次封板时间 | 越早封板→资金越强 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.1 涨跌停板机制相关因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 323. limit_up_open_count

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003001 |
| source_file | explore |
| source_line | 701 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `limit_up_open_count` | 涨停期间打开次数 | 0次(一字板)→最强; 多次打开→弱 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.1 涨跌停板机制相关因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 324. new_high_vs_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003023 |
| source_file | explore |
| source_line | 738 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `new_high_vs_volume` | 创N日新高时的成交量相对水平 | 缩量新高→假突破; 放量新高→真突破 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.4 筹码结构因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 325. t_plus_1_effect

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003030 |
| source_file | explore |
| source_line | 750 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `t_plus_1_effect` | 前日涨停今日首次可卖 | T+1制度下的自然卖压 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.5 短线特殊时间因子 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 326. option_unusual_volume

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003075 |
| source_file | explore |
| source_line | 903 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 38 |
| raw_text | | `option_unusual_volume` | 期权成交量突变(>均值2倍) | 知情交易信号 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 18. 补充：期权隐含信息与衍生品深度因子 > 18.2 A股可用的期权信号因子 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 327. sector_score

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000058 |
| source_file | tgb |
| source_line | 154 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `sector_score` 题材分 | 板块当日涨幅×10 | 板块数据 | 预期管理帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 8. 板块/题材因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 328. sector_sustainability

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000061 |
| source_file | tgb |
| source_line | 157 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `sector_sustainability` 板块持续性 | 板块连续上涨天数 | 板块数据 | 龙头战法帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 8. 板块/题材因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 329. sector_competing_yield

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000087 |
| source_file | tgb |
| source_line | 198 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `sector_competing_yield` 板块争宠让位 | 兔死狗哼：新板块拉升→旧板块怕争宠→让位给同盟晋级 | 板块数据 | 延边出客实抓·325 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 11. 涨停板拆解因子（延边刺客体系） |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 330. sector_heatmap_structure

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000095 |
| source_file | tgb |
| source_line | 211 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `sector_heatmap_structure` 涨幅榜结构 | 防守板块涨+科技跌 = 避险模式；反之 = 进攻模式 | 板块数据 | 六信号帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 12. 信号体系因子（橘子洲炒家/南山游龙） |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 331. has_convertible_bond

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000099 |
| source_file | tgb |
| source_line | 215 |
| data_needs | ['sector_theme', 'cross_market'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `has_convertible_bond` 有转债/港股标记 | 有转债或港股的个股难以成为龙头 | 基础数据 | 南山游龙帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 12. 信号体系因子（橘子洲炒家/南山游龙） |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 332. performance_liquidity_combo

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000159 |
| source_file | tgb |
| source_line | 300 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `performance_liquidity_combo` 业绩×流动性组合 | 业绩+流动性=行业龙头溢价(2017后结构特征) | 基本面+成交量 | 著名刺客"主线分析" | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 18. 席位行为与微观博弈因子（著名刺客复盘体系扩展）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 333. mature_bull_signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000171 |
| source_file | tgb |
| source_line | 317 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `mature_bull_signal` 成熟牛识别 | 缩量锁仓+行业龙头集中度提升=成熟牛(持续数年) | 指数+行业数据 | 北京炒家百倍帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 19. 仓位管理与市场regime因子（北京炒家体系）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 334. board_effect_required

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000185 |
| source_file | tgb |
| source_line | 336 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `board_effect_required` 板块效应必须 | 短线炒作除大势配合外必须含板块强势才能提高成功率 | 板块数据 | Asking语录第11条 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 20. Asking超短体系因子（外部编纂完整版）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 335. selection_priority_score

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000199 |
| source_file | tgb |
| source_line | 355 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `selection_priority_score` 选股优先级综合评分 | 大环境>股性>题材>形态 四层权重打分 | 综合判断 | 北京炒家(外部编纂) | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 21. 仓位止损量化因子（跨交易者汇总）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 336. pure_kline_board_winrate

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000217 |
| source_file | tgb |
| source_line | 383 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `pure_kline_board_winrate` 纯K线打板胜率 | 纯技术打板胜率约45%→需情绪/板块/龙头等因子补充 | 历史统计 | 炒股养家语录 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 23. 炒股养家胜率仓位因子（外部编纂）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 337. direction_efficiency_time

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000220 |
| source_file | tgb |
| source_line | 391 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `direction_efficiency_time` 方向×效率×时间三要素 | 方向(板块选择)>效率(买卖时机)>时间(持有周期)优先级排序 | 综合判断 | 收割逻辑·年终总结 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 24. 收割逻辑(涅盘重升)系统构建因子（实抓100W实盘+年终总结）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 338. earning_effect_track

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000221 |
| source_file | tgb |
| source_line | 392 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `earning_effect_track` 赚钱效应跟踪 | 板块赚钱效应=弱板块被强板块带起来的概率 | 板块涨幅对比 | 收割逻辑·100W实盘 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 24. 收割逻辑(涅盘重升)系统构建因子（实抓100W实盘+年终总结）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 339. emotion_bad_no_scan

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000227 |
| source_file | tgb |
| source_line | 398 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `emotion_bad_no_scan` 情绪不好不扫板 | 情绪不好千万不能扫板，除非主流板块龙头 | 综合判断 | 收割逻辑·100W实盘 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 24. 收割逻辑(涅盘重升)系统构建因子（实抓100W实盘+年终总结）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 340. sector_rotation_huddle

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000229 |
| source_file | tgb |
| source_line | 400 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `sector_rotation_huddle` 弱势资金抱团轮转 | 行情弱→资金抱团几个赚钱效应板块轮转→高抛低吸另一个 | 板块资金流 | 收割逻辑·100W实盘 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 24. 收割逻辑(涅盘重升)系统构建因子（实抓100W实盘+年终总结）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 341. empty_wait_leader_full

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000233 |
| source_file | tgb |
| source_line | 409 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `empty_wait_leader_full` 空仓等龙头初现满仓怼 | 空仓状态→龙头初现→满仓一把梭 | 仓位管理 | 延边出客实抓·429 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 25. 延边出客操作体系因子（实抓541条回复）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 342. high_low_switch_signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000240 |
| source_file | tgb |
| source_line | 421 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `high_low_switch_signal` 高低切信号 | 高位板块畏高+低位避险/业绩品种起势=切换信号 | 板块涨幅对比 | 延边出客·428帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 26. 延边出客帖子正文因子（拆解框架衍生）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 343. departure_from_leader

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000242 |
| source_file | tgb |
| source_line | 423 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `departure_from_leader` 脱离龙头独立性 | 跟风股能否脱离龙头独立走强=板块持续性硬指标 | 个股vs龙头相关性 | 延边出客·325帖 | |
| section | 淘股吧名人堂短线因子提取报告 > 一、可量化短线因子清单 > 26. 延边出客帖子正文因子（拆解框架衍生）★新增 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 344. same_sector_switch

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000345 |
| source_file | tgb |
| source_line | 1062 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `same_sector_switch` 同板块连续切换 | 连续买入同板块不同个股次数（雄安系列=4次） | 退学炒股OCR交割单 | |
| section | 淘股吧名人堂短线因子提取报告 > 八、交割单分析与实盘赛数据 > 8.1 退学炒股交割单分析（OCR实提取） > 交割单实际提取数据 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 345. follow_mainstream_score

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000357 |
| source_file | tgb |
| source_line | 1121 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `follow_mainstream_score` 跟随主流评分 | 个股所属板块是否为当前最热主线 | 著名刺客方法论 | |
| section | 淘股吧名人堂短线因子提取报告 > 八、交割单分析与实盘赛数据 > 8.2 著名刺客交割单分析（OCR实提取） |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 346. sector_capacity_filter

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000378 |
| source_file | tgb |
| source_line | 1770 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `sector_capacity_filter` 板块容量过滤 | 板块成交占全市场比例→判断能否承载主线 | 只核大学生·夺权排除法 | |
| section | 淘股吧名人堂短线因子提取报告 > 十一、实盘抓取核心内容（974+条作者回复精选 + 帖子正文实抓） > 11.7 只核大学生 — 今日份思考系列（帖子正文实抓）★新增 完成 > 可量化因子（从帖子正文提取） |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 347. chip_digestion_cycle

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000381 |
| source_file | tgb |
| source_line | 1773 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `chip_digestion_cycle` 筹码消化周期 | 大题材二波需一个月+沉淀期 | 只核大学生·夺权预期 | |
| section | 淘股吧名人堂短线因子提取报告 > 十一、实盘抓取核心内容（974+条作者回复精选 + 帖子正文实抓） > 11.7 只核大学生 — 今日份思考系列（帖子正文实抓）★新增 完成 > 可量化因子（从帖子正文提取） |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 348. follower_position_confirm

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000388 |
| source_file | tgb |
| source_line | 1958 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | **小弟位置确认龙头质量 follower_position_confirm**： |
| section | 淘股吧名人堂短线因子提取报告 > 十一、实盘抓取核心内容（974+条作者回复精选 + 帖子正文实抓） > 11.10 收割逻辑 — 100W实盘15,488评论深度挖掘（179条回复+199张交割单OCR）★新增 > A. 入场因子（新增） |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 349. theme_logic_level

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000423 |
| source_file | tgb |
| source_line | 2300 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 题材逻辑级别因子 theme_logic_level |
| section | 淘股吧名人堂短线因子提取报告 > 十二、第三轮深度搜索补充因子 > 12.4 题材生命周期因子群 > 题材逻辑级别因子 theme_logic_level |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 350. cross_theme_seesaw

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000424 |
| source_file | tgb |
| source_line | 2310 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 跨题材资金翘翘板因子 cross_theme_seesaw |
| section | 淘股吧名人堂短线因子提取报告 > 十二、第三轮深度搜索补充因子 > 12.4 题材生命周期因子群 > 跨题材资金翘翘板因子 cross_theme_seesaw |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 351. leader_recognition_score

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000432 |
| source_file | tgb |
| source_line | 2420 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 龙头辨识度评分因子 leader_recognition_score |
| section | 淘股吧名人堂短线因子提取报告 > 十三、第四轮深度搜索补充因子（龙头/打板/反包/妖股） > 13.1 龙头战法量化因子群 > 龙头辨识度评分因子 leader_recognition_score |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 352. leader_chip_structure

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000433 |
| source_file | tgb |
| source_line | 2437 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 龙头筹码结构因子 leader_chip_structure |
| section | 淘股吧名人堂短线因子提取报告 > 十三、第四轮深度搜索补充因子（龙头/打板/反包/妖股） > 13.1 龙头战法量化因子群 > 龙头筹码结构因子 leader_chip_structure |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 353. leader_switch_signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000435 |
| source_file | tgb |
| source_line | 2451 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 龙头切换信号因子 leader_switch_signal |
| section | 淘股吧名人堂短线因子提取报告 > 十三、第四轮深度搜索补充因子（龙头/打板/反包/妖股） > 13.1 龙头战法量化因子群 > 龙头切换信号因子 leader_switch_signal |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 354. leader_reversal_wrap

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000436 |
| source_file | tgb |
| source_line | 2469 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 龙头反包因子 leader_reversal_wrap |
| section | 淘股吧名人堂短线因子提取报告 > 十三、第四轮深度搜索补充因子（龙头/打板/反包/妖股） > 13.1 龙头战法量化因子群 > 龙头反包因子 leader_reversal_wrap |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 355. sector_policy_density

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000527 |
| source_file | tgb |
| source_line | 3531 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 行业政策密集度因子 sector_policy_density |
| section | 披露12小时后信号衰减约97% > 16.3 消息面/事件驱动因子群 > 行业政策密集度因子 sector_policy_density |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 356. leader_succession_cycle

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000556 |
| source_file | tgb |
| source_line | 3908 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 龙头接替周期 leader_succession_cycle |
| section | 披露12小时后信号衰减约97% > 十七、半路/低吸/尾盘/接力链因子（第六轮搜索） > 17.4 龙头接替与补涨龙框架 > 龙头接替周期 leader_succession_cycle |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 357. sector_retreat_detection

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000559 |
| source_file | tgb |
| source_line | 3968 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 退潮期检测信号 sector_retreat_detection |
| section | 披露12小时后信号衰减约97% > 十七、半路/低吸/尾盘/接力链因子（第六轮搜索） > 17.5 板块阶段跟踪与退潮信号 > 退潮期检测信号 sector_retreat_detection |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 358. sector_phase_tracking

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000560 |
| source_file | tgb |
| source_line | 3992 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 板块阶段编号跟踪 sector_phase_tracking |
| section | 披露12小时后信号衰减约97% > 十七、半路/低吸/尾盘/接力链因子（第六轮搜索） > 17.5 板块阶段跟踪与退潮信号 > 板块阶段编号跟踪 sector_phase_tracking |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 359. seasonal_theme_rotation

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000637 |
| source_file | tgb |
| source_line | 5140 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 463: `seasonal_theme_rotation` - 季节性题材轮动因子 |
| section | 注意: 预期充分的政策(如两会前市场已炒作)出台后常"利好出尽" > Factor 463: `seasonal_theme_rotation` - 季节性题材轮动因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 360. seasonal_themes

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000638 |
| source_file | tgb |
| source_line | 5144 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | seasonal_themes = { |
| section | 量化规则 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 361. leader_premium_decay

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000678 |
| source_file | tgb |
| source_line | 5672 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 476: `leader_premium_decay` - 龙头溢价衰减曲线因子 |
| section | 买入应优先核心, 止损应优先杂毛 > Factor 476: `leader_premium_decay` - 龙头溢价衰减曲线因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 362. theme_fermentation_cycle

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000781 |
| source_file | tgb |
| source_line | 6683 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 503: `theme_fermentation_cycle` - 题材发酵周期因子 |
| section | 来源: 淘股吧龙头战法深度拆解、雪球主线题材判断、新浪主线周期五阶段解析 > Factor 503: `theme_fermentation_cycle` - 题材发酵周期因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 363. sector_tier_classify

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000784 |
| source_file | tgb |
| source_line | 6772 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 504: `sector_tier_classify` - 板块梯队三级划分因子 |
| section | 来源: 淘股吧大小周期理论看题材兴衰 > 二十三、板块梯队轮动 / 妖股连板进阶 / 竞价深度 / 复盘方法论因子群 > 23.1 板块梯队与轮动进阶因子 > Factor 504: `sector_tier_classify` - 板块梯队三级划分因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 364. sorted_stocks

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000785 |
| source_file | tgb |
| source_line | 6779 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | sorted_stocks = sorted(sector_stocks, key=lambda s: ( |
| section | 排序: 连板高度→首封时间→累计涨幅 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 365. step1_sectors

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000827 |
| source_file | tgb |
| source_line | 7246 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | step1_sectors = { |
| section | Step1: 板块(15分钟) |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 366. cycle_leader_selection

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000861 |
| source_file | tgb |
| source_line | 7648 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 526: `cycle_leader_selection` - 周期龙头筛选因子 |
| section | 来源: 淘股吧周期股交易者对各类催化剂效果的经验统计 > Factor 526: `cycle_leader_selection` - 周期龙头筛选因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 367. leader_stock_exit_rules

| Field | Value |
|-------|-------|
| raw_factor_id | RAW000971 |
| source_file | tgb |
| source_line | 8705 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 550: `leader_stock_exit_rules` - 龙头股止盈法则因子 |
| section | 来源: 淘股吧情绪交易派的止盈体系 > Factor 550: `leader_stock_exit_rules` - 龙头股止盈法则因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 368. leader_pullback_quality

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001004 |
| source_file | tgb |
| source_line | 8955 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 556: `leader_pullback_quality` - 龙头回调质量评分因子 |
| section | 来源: 网络统计样本+淘股吧反包战法经验 > 26.2 龙回头/二波行情因子群 > Factor 556: `leader_pullback_quality` - 龙头回调质量评分因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 369. emotion_reversal_leader_detect

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001026 |
| source_file | tgb |
| source_line | 9166 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 562: `emotion_reversal_leader_detect` - 情绪反转龙头识别因子 |
| section | 来源: 淘股吧情绪周期操作策略, 复盘网情绪拐点多维度解析 > Factor 562: `emotion_reversal_leader_detect` - 情绪反转龙头识别因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 370. resist_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001063 |
| source_file | tgb |
| source_line | 9421 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | resist_ratio = stock.drop_pct / max(abs(sector.drop_pct), 0.001) |
| section | 维度6: 抗跌性 — 板块回调时个股跌幅/板块跌幅 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 371. sector_capacity_estimation

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001076 |
| source_file | tgb |
| source_line | 9534 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 572: `sector_capacity_estimation` - 板块题材容量估算因子 |
| section | 来源: 淘股吧补涨龙/卡位战法经验, "龙头接替/补涨龙框架因子"(§十五)扩展 > Factor 572: `sector_capacity_estimation` - 板块题材容量估算因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 372. leader_follower_repair_spread

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001194 |
| source_file | tgb |
| source_line | 10376 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 605: `leader_follower_repair_spread` - 龙头跟风修复扩散因子 |
| section | 来源: 淘股吧弱转强盘中量价观察, "花更少的钱拉更高才是真转强" > Factor 605: `leader_follower_repair_spread` - 龙头跟风修复扩散因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 373. spread_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001197 |
| source_file | tgb |
| source_line | 10385 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | spread_ratio = len(strong) / max(len(sector.members), 1) |
| section | 龙头修复后, 跟风票是否同步回暖 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 374. reflow_leader_confirmation

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001204 |
| source_file | tgb |
| source_line | 10444 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 607: `reflow_leader_confirmation` - 回流龙头确认因子 |
| section | 来源: 淘股吧午后回流复盘, "回流看的是一批不是一只" > Factor 607: `reflow_leader_confirmation` - 回流龙头确认因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 375. sector_vol

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001268 |
| source_file | tgb |
| source_line | 10884 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | sector_vol = stock.sector_realized_vol_20d |
| section | 上市60日内波动率相对同行业的溢价 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 376. vol_premium

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001269 |
| source_file | tgb |
| source_line | 10885 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | vol_premium = stock_vol / max(sector_vol, 0.01) - 1 |
| section | 上市60日内波动率相对同行业的溢价 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 377. sector_rotation_momentum

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001337 |
| source_file | tgb |
| source_line | 11315 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 644: `sector_rotation_momentum` - 板块轮动动量因子 |
| section | 来源: 淘股吧连板梯队分析, "距天花板越近关注度越高" > 42.2 板块轮动/题材生命周期因子群 > Factor 644: `sector_rotation_momentum` - 板块轮动动量因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 378. theme_lifecycle_stage

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001341 |
| source_file | tgb |
| source_line | 11336 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 645: `theme_lifecycle_stage` - 题材生命周期阶段因子 |
| section | 来源: 淘股吧板块轮动复盘, "首板数环比增速是板块启动最早信号" > Factor 645: `theme_lifecycle_stage` - 题材生命周期阶段因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 379. leader_status

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001345 |
| source_file | tgb |
| source_line | 11345 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | leader_status = theme.leader_stock_status |
| section | 题材从发酵到退潮的生命周期定位 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 380. position_theme_concentration

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001421 |
| source_file | tgb |
| source_line | 11808 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Factor 662: `position_theme_concentration` - 持仓题材集中度因子 |
| section | 来源: 淘股吧盘前预判, "A50+美股+港股三合一看隔夜情绪" > 四十七、短线多票组合/仓位分配/相关性管理因子群 > 47.1 持仓集中度/相关性因子群 > Factor 662: `position_theme_concentration` - 持仓题材集中度因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 381. theme_weights

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001422 |
| source_file | tgb |
| source_line | 11814 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | theme_weights = {} |
| section | 当前持仓中同一题材的仓位集中度 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 382. max_theme_weight

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001424 |
| source_file | tgb |
| source_line | 11819 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | max_theme_weight = max(theme_weights.values()) if theme_weights else 0 |
| section | 当前持仓中同一题材的仓位集中度 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 383. hhi

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001425 |
| source_file | tgb |
| source_line | 11820 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | hhi = sum(w**2 for w in theme_weights.values()) |
| section | 当前持仓中同一题材的仓位集中度 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 384. volume_zscore

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001658 |
| source_file | short |
| source_line | 585 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | 成交量 | `relative_volume`, `volume_zscore`, `buy_sell_imbalance`, `large_trade_ratio` | |
| section | 短线因子 > 17. 最小可落地因子集 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 385. buy_sell_imbalance

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001659 |
| source_file | short |
| source_line | 585 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | 成交量 | `relative_volume`, `volume_zscore`, `buy_sell_imbalance`, `large_trade_ratio` | |
| section | 短线因子 > 17. 最小可落地因子集 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 386. large_trade_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001660 |
| source_file | short |
| source_line | 585 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | 成交量 | `relative_volume`, `volume_zscore`, `buy_sell_imbalance`, `large_trade_ratio` | |
| section | 短线因子 > 17. 最小可落地因子集 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 387. index_residual_ret

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001674 |
| source_file | short |
| source_line | 589 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | 横截面 | `industry_neutral_ret_5m`, `rank(relative_volume)`, `index_residual_ret` | |
| section | 短线因子 > 17. 最小可落地因子集 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 388. strong_pool_reason

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001719 |
| source_file | short |
| source_line | 1028 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | AKShare `stock_zt_pool_strong_em` 强势股池 | 是否新高、量比、涨停统计、入选理由 | `strong_pool_reason`, `new_high_strength`, `recent_limit_frequency` | 近期数据 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.2 可直接接入的数据源扫描 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 389. new_high_strength

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001720 |
| source_file | short |
| source_line | 1028 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | AKShare `stock_zt_pool_strong_em` 强势股池 | 是否新高、量比、涨停统计、入选理由 | `strong_pool_reason`, `new_high_strength`, `recent_limit_frequency` | 近期数据 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.2 可直接接入的数据源扫描 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 390. recent_limit_frequency

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001721 |
| source_file | short |
| source_line | 1028 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | AKShare `stock_zt_pool_strong_em` 强势股池 | 是否新高、量比、涨停统计、入选理由 | `strong_pool_reason`, `new_high_strength`, `recent_limit_frequency` | 近期数据 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.2 可直接接入的数据源扫描 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 391. market_activity_real

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001751 |
| source_file | short |
| source_line | 1039 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | AKShare `stock_market_activity_legu` 赚钱效应 | 上涨、下跌、涨停、真实涨停、跌停、活跃度 | `market_activity_real`, `real_limit_up_count`, `true_limit_up_ratio` | 当前数据；历史需落库 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.2 可直接接入的数据源扫描 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 392. true_limit_up_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001753 |
| source_file | short |
| source_line | 1039 |
| data_needs | ['limit_pool'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | AKShare `stock_market_activity_legu` 赚钱效应 | 上涨、下跌、涨停、真实涨停、跌停、活跃度 | `market_activity_real`, `real_limit_up_count`, `true_limit_up_ratio` | 当前数据；历史需落库 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.2 可直接接入的数据源扫描 |

**Why review**: High-signal data source | Clean asof_time
**Engineering path**: limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py

---

### 393. theme_leader_gap

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001793 |
| source_file | short |
| source_line | 1108 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `theme_leader_gap` | 龙头涨幅/连板高度 - 题材第二名 | 龙头是否唯一 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.5 “龙头/题材容量”因子补强 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 394. theme_middle_trap_density

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001794 |
| source_file | short |
| source_line | 1109 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `theme_middle_trap_density` | 题材内 2-4 板但非龙头数量 | 中位股拥挤风险 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.5 “龙头/题材容量”因子补强 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 395. theme_low_level_supply

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001795 |
| source_file | short |
| source_line | 1110 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `theme_low_level_supply` | 题材内首板/二板数量 | 补涨梯队是否充足 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.5 “龙头/题材容量”因子补强 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 396. theme_echelon_slope

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001796 |
| source_file | short |
| source_line | 1111 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `theme_echelon_slope` | 各高度板数量的斜率 | 梯队健康度 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.5 “龙头/题材容量”因子补强 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 397. theme_second_wave_gap_days

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001799 |
| source_file | short |
| source_line | 1114 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `theme_second_wave_gap_days` | 第一波高潮后到二波启动的间隔 | 二波沉淀周期 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.5 “龙头/题材容量”因子补强 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 398. theme_cross_market_anchor

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001800 |
| source_file | short |
| source_line | 1115 |
| data_needs | ['sector_theme', 'cross_market'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `theme_cross_market_anchor` | 美股/港股/期货映射标的收益 | 外部锚定题材的隔夜影响 | |
| section | 短线因子 > 33. A股超短生态因子扫描（项目对齐） > 33.5 “龙头/题材容量”因子补强 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 399. VIX_close

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001891 |
| source_file | short |
| source_line | 1820 |
| data_needs | ['cross_market', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | VIX 水平/变化 | `VIX_close`, `VIX_change` | 05:00 | VIX突增>20%→A股下跌~65% | |
| section | Microprice（5档盘口，实时） > 40. 跨市场因子 > 40.2 跨市场因子矩阵 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 400. VIX_change

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001892 |
| source_file | short |
| source_line | 1820 |
| data_needs | ['cross_market', 'daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | VIX 水平/变化 | `VIX_close`, `VIX_change` | 05:00 | VIX突增>20%→A股下跌~65% | |
| section | Microprice（5档盘口，实时） > 40. 跨市场因子 > 40.2 跨市场因子矩阵 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 401. HSI_close

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001897 |
| source_file | short |
| source_line | 1825 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | 恒生指数 | `HSI_close`, `HSI_afternoon_session` | A股15:00后HSI仍交易到16:00 | ~58-65% | |
| section | Microprice（5档盘口，实时） > 40. 跨市场因子 > 40.2 跨市场因子矩阵 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 402. HSI_afternoon_session

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001898 |
| source_file | short |
| source_line | 1825 |
| data_needs | ['daily_ohlcv'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | 恒生指数 | `HSI_close`, `HSI_afternoon_session` | A股15:00后HSI仍交易到16:00 | ~58-65% | |
| section | Microprice（5档盘口，实时） > 40. 跨市场因子 > 40.2 跨市场因子矩阵 |

**Why review**: Clean asof_time
**Engineering path**: Daily OHLCV from main dataframe (always available)

---

### 403. Style_Embedding_Distance

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001905 |
| source_file | short |
| source_line | 1949 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | Contrastive Asset Embeddings | 2024 | 收益率序列对比学习生成资产嵌入 | `Style_Embedding_Distance = cosine_sim(embed_i, sector_centroid)` | |
| section | Microprice（5档盘口，实时） > 42. 深度学习架构用于股票预测 > 42.3 对比学习 / 自监督学习 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 404. Residual

| Field | Value |
|-------|-------|
| raw_factor_id | RAW001978 |
| source_file | short |
| source_line | 3395 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Residual = ETF实际收益 - 基于成分股收益的理论收益 |
| section | 注册制IPO收益分布 (2020-2025统计) > 66. ETF联动/套利因子 > 66.4 ETF-成分股领先滞后因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 405. IPCA

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002319 |
| source_file | short |
| source_line | 7477 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 100.2 `IPCA` - 工具化主成分因子 |
| section | 损失: L = Σ(r - r_hat)² + λ||W||² + γ×reconstruction_loss > 100.2 `IPCA` - 工具化主成分因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 406. Sector_Signal_j

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002384 |
| source_file | short |
| source_line | 8074 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Sector_Signal_j = Sign(Commodity_Mom_20d_j) × |Commodity_Beta_j| |
| section | 信号: 用商品动量预测股票收益 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 407. Sector_Signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002415 |
| source_file | short |
| source_line | 8329 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | Sector_Signal = Σ (Commodity_Mom_j × Weight_j_to_sector) |
| section | 快速贬值(>2%/月) → 触发防御配置 > 107.2 `COMMODITY_SPILLOVER` - 商品动量溢出因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 408. LEADER_COMPOSITE_SCORE

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002599 |
| source_file | short |
| source_line | 9987 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 121.1 `LEADER_COMPOSITE_SCORE` - 龙头综合评分 |
| section | 找出最拥挤的因子并降权 > 121. 龙头实时识别与生命周期因子 (Leader Stock Real-time Scoring) > 121.1 `LEADER_COMPOSITE_SCORE` - 龙头综合评分 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 409. LEADER_LIFECYCLE_STAGE

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002603 |
| source_file | short |
| source_line | 10007 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 121.2 `LEADER_LIFECYCLE_STAGE` - 龙头生命周期阶段 |
| section | 带动系数: leader涨停后, 同板块其他股次日涨幅均值 > 121.2 `LEADER_LIFECYCLE_STAGE` - 龙头生命周期阶段 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 410. stage

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002604 |
| source_file | short |
| source_line | 10012 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | stage = 0  # emerging: 首板秒封+热门板块 |
| section | 龙头生命周期: emerging(0) / confirmed(1) / mature(2) / decaying(3) |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 411. LEADER_SWITCH_SIGNAL

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002608 |
| source_file | short |
| source_line | 10021 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 121.3 `LEADER_SWITCH_SIGNAL` - 龙头切换信号 |
| section | 龙头生命周期: emerging(0) / confirmed(1) / mature(2) / decaying(3) > 121.3 `LEADER_SWITCH_SIGNAL` - 龙头切换信号 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 412. switch_signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002611 |
| source_file | short |
| source_line | 10027 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | switch_signal = old_leader_decay and new_leader_emerge and (new_stock.sector != old_leader.sector) |
| section | 老龙头衰退 + 新龙头崛起 = 切换信号 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 413. LEADER_FOLLOWER_PREMIUM

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002612 |
| source_file | short |
| source_line | 10032 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 121.4 `LEADER_FOLLOWER_PREMIUM` - 龙头跟风溢价 |
| section | 老龙头衰退 + 新龙头崛起 = 切换信号 > 121.4 `LEADER_FOLLOWER_PREMIUM` - 龙头跟风溢价 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 414. step2_pass

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002652 |
| source_file | short |
| source_line | 10234 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | step2_pass = target_sector_score > 0.7 |
| section | 只有当5步全部通过时才生成买入信号 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 415. LEADER_PULLBACK_QUALITY

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002658 |
| source_file | short |
| source_line | 10265 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 126.2 `LEADER_PULLBACK_QUALITY` - 龙头回调质量评分 |
| section | 强度 = 四步评分的加权平均 > 126. 反包涨停与龙回头二波因子 (Reversal Board & Leader Pullback Factors) > 126.2 `LEADER_PULLBACK_QUALITY` - 龙头回调质量评分 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 416. LEADER_FOLLOWER_REPAIR_SPREAD

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002707 |
| source_file | short |
| source_line | 10757 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 135.5 `LEADER_FOLLOWER_REPAIR_SPREAD` - 龙头跟风修复扩散因子 |
| section | 强度 = 四步评分的加权平均 > 135. 真弱假弱与分歧承接因子 (True/False Weakness & Divergence Absorption) > 135.5 `LEADER_FOLLOWER_REPAIR_SPREAD` - 龙头跟风修复扩散因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 417. spread_ratio

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002708 |
| source_file | short |
| source_line | 10760 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | spread_ratio = 回收昨收且涨>3%的成员数 / 板块成员总数 |
| section | 强度 = 四步评分的加权平均 > 135. 真弱假弱与分歧承接因子 (True/False Weakness & Divergence Absorption) > 135.5 `LEADER_FOLLOWER_REPAIR_SPREAD` - 龙头跟风修复扩散因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 418. REFLOW_LEADER_CONFIRMATION

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002711 |
| source_file | short |
| source_line | 10787 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 136.2 `REFLOW_LEADER_CONFIRMATION` - 回流龙头确认因子 |
| section | 强度 = 四步评分的加权平均 > 136. 午后回流与尾盘抢筹因子 (Afternoon Reflow & Tail Chase Factors) > 136.2 `REFLOW_LEADER_CONFIRMATION` - 回流龙头确认因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 419. SECTOR_ROTATION_MOMENTUM

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002765 |
| source_file | short |
| source_line | 11233 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 144.4 `SECTOR_ROTATION_MOMENTUM` - 板块轮动动量因子 |
| section | 强度 = 四步评分的加权平均 > 144. 连板高度梯队与板块轮动因子 (Board Height Tier & Sector Rotation Factors) > 144.4 `SECTOR_ROTATION_MOMENTUM` - 板块轮动动量因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 420. THEME_LIFECYCLE_STAGE

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002766 |
| source_file | short |
| source_line | 11245 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 144.5 `THEME_LIFECYCLE_STAGE` - 题材生命周期阶段因子 |
| section | 强度 = 四步评分的加权平均 > 144. 连板高度梯队与板块轮动因子 (Board Height Tier & Sector Rotation Factors) > 144.5 `THEME_LIFECYCLE_STAGE` - 题材生命周期阶段因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 421. POSITION_THEME_CONCENTRATION

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002793 |
| source_file | short |
| source_line | 11486 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | 149.1 `POSITION_THEME_CONCENTRATION` - 持仓题材集中度因子 |
| section | 强度 = 四步评分的加权平均 > 149. 短线多票组合与仓位管理因子 (Multi-Stock Portfolio & Position Management Factors) > 149.1 `POSITION_THEME_CONCENTRATION` - 持仓题材集中度因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 422. northbound_sector_flow

| Field | Value |
|-------|-------|
| raw_factor_id | RAW002888 |
| source_file | explore |
| source_line | 257 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `northbound_sector_flow` | 北向对该行业的净流入 | 行业级别外资偏好 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 5. 资金流与主力行为因子 > 5.2 北向资金因子（A股特有强信号） |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 423. dragon_head_flag

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003013 |
| source_file | explore |
| source_line | 718 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `dragon_head_flag` | 是否板块人气龙头 | 龙头享受溢价 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.2 连板/接力因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 424. sector_momentum_1d

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003014 |
| source_file | explore |
| source_line | 724 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `sector_momentum_1d` | 所属板块当日涨幅 | 板块强→个股次日延续 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.3 板块/题材轮动因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 425. sector_momentum_rank

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003015 |
| source_file | explore |
| source_line | 725 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `sector_momentum_rank` | 板块涨幅在所有板块的排名 | 领涨板块效应 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.3 板块/题材轮动因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 426. sector_rotation_signal

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003016 |
| source_file | explore |
| source_line | 726 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `sector_rotation_signal` | 板块是否从冷变热(3日) | 资金轮入信号 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.3 板块/题材轮动因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 427. concept_count_hot

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003017 |
| source_file | explore |
| source_line | 727 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `concept_count_hot` | 个股关联的热门概念数量 | 多概念加持→资金关注 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.3 板块/题材轮动因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 428. sector_leader_return

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003018 |
| source_file | explore |
| source_line | 728 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `sector_leader_return` | 板块龙头当日涨幅 | 龙头带动效应 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.3 板块/题材轮动因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

### 429. index_component_return

| Field | Value |
|-------|-------|
| raw_factor_id | RAW003047 |
| source_file | explore |
| source_line | 779 |
| data_needs | ['sector_theme'] |
| asof_time | after_close |
| priority | unknown |
| suggested_bucket | research |
| score | 33 |
| raw_text | | `index_component_return` | 所属指数成分股平均涨幅 | 指数拖拽/推升效应 | |
| section | 因子探索：短线次日方向预测因子全景研究 > 15. 补充：A股短线特有因子深度挖掘 > 15.7 关联股票/产业链因子 |

**Why review**: Clean asof_time
**Engineering path**: ths_daily/moneyflow_ind_dc cache via sector features

---

## Excluded Feature Check

The following known features were correctly excluded from this queue:

- max_board_height: implemented=True, in_registry=False, in_queue=False
- market_max_board_height: implemented=True, in_registry=False, in_queue=False
- board_count: implemented=True, in_registry=False, in_queue=False
- prev_limit_up_premium: implemented=True, in_registry=False, in_queue=False
- volume_vs_prev: implemented=True, in_registry=False, in_queue=False
- seal_rate_80_threshold: implemented=True, in_registry=False, in_queue=False
- seal_money_to_float_mv: implemented=True, in_registry=False, in_queue=False
- emotion_score: implemented=True, in_registry=False, in_queue=False
- seal_time: implemented=True, in_registry=False, in_queue=False
- real_limit_up_premium_gap: implemented=False, in_registry=True, in_queue=False
- zbgc_sector_pressure: implemented=False, in_registry=True, in_queue=False
- theme_limit_density: implemented=False, in_registry=True, in_queue=False

---

## Encoding Note

raw_text and section fields are stored as valid UTF-8 in the source JSONL files.
No actual encoding corruption detected. Terminal display artifacts (mojibake) are
due to Windows console codepage mismatch, not data corruption.

---

*Generated 2026-05-06. Source: raw_factor_pool_index.json (3,075 records). Registry: C001-C152 (152 candidates)*
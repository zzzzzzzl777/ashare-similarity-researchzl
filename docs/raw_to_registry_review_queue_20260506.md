# Raw-to-Registry Review Queue (50) -- 2026-05-06

> 50 candidates from raw factor pool most worth human/engineering review
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
Output pool: top 50 by composite score
Score range: 88 - 38

---

## Data Needs Distribution (Top 50)

| data_needs | Count |
|-----------|-------|
| daily_ohlcv | 41 |
| limit_pool | 27 |
| sector_theme | 20 |

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
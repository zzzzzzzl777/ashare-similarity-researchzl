# 淘股吧(TaoGuBa) A股短线交易因子研究

> 数据来源：淘股吧 (tgb.cn) 多位实战派用户帖子
> 采集日期：2026-04-30

---

## 方向一：半路板/低吸战法

### Factor 1: `limit_up_time_category` - 涨停时间段分类因子

**来源**: 东方圣《万次涨停回测：次日必涨的铁律！看懂这3点，抓板成功率超85%》
- URL: https://www.tgb.cn/a/2r0quFL61AP-1

**量化规则**:
```python
# 涨停封板时间与次日连板概率
if seal_time in range("09:30", "10:30"):  # 早盘强势板
    next_day_limit_prob = 0.85  # 次日涨停率85%
    signal = "最强势，主力抢筹"
elif seal_time in range("13:30", "14:30"):  # 午盘突破板
    next_day_limit_prob = 0.65  # 次日涨停率65%
    signal = "稳扎稳打，稳健型"
elif seal_time >= "14:50":  # 尾盘偷袭板
    next_day_drop_prob = 0.61  # 次日下跌率61%
    signal = "主力诱多，必避"
```

**实证数据**:
- 样本：2021-2026年 A股 10276次涨停（剔除新股、ST）
- 早盘板特征：开盘直线拉升角度>45度，量能同步放大，封单坚决
- 尾盘偷袭板特征：最后10分钟拉板，封单小、量能虚、抛压大

---

### Factor 2: `volume_price_health` - 涨停量价健康度因子

**来源**: 东方圣《万次涨停回测》
- URL: https://www.tgb.cn/a/2r0quFL61AP-1

**量化规则**:
```python
# 量价健康标准（核心三条件）
volume_ratio = today_volume / avg_volume_5d  # 量比
turnover_rate = today_turnover / float_shares  # 换手率
seal_order_ratio = seal_order_amount / today_turnover_amount  # 封单金额/成交额

# 判定条件
is_healthy = (
    1.5 <= volume_ratio <= 2.5 and  # 温和放量，非爆量
    0.05 <= turnover_rate <= 0.12 and  # 换手5%-12%
    seal_order_ratio >= 0.05 and  # 封单金额>=当日成交额5%
    buy1_ratio >= 0.25  # 买一占比超25%
)
```

**实证数据**:
| 条件 | 次日连板率 | 平均高开 |
|------|-----------|---------|
| 符合标准 | 73% | +4.2% |
| 放量超3倍、换手>20% | 18% | 大概率出货 |

---

### Factor 3: `capital_purity` - 资金纯正度因子

**来源**: 东方圣《万次涨停回测》
- URL: https://www.tgb.cn/a/2r0quFL61AP-1

**量化规则**:
```python
# 主力资金流向判断
main_force_net = super_large_order_net + large_order_net  # 超大单+大单净流入
retail_net = medium_order_net + small_order_net  # 中小单净流量

# 真涨停信号: main_force_net > 0 且 retail_net < 0 (主力买、散户卖)
# 假涨停信号: large_order_net < 0 且 small_order_net > 0 (主力出、散户接)

if main_force_net > 1e8:  # 主力净流入超1亿
    next_day_limit_rate = 0.68  # 次日连板率68%
elif main_force_net < 0:  # 主力净流出
    next_day_drop_rate = 0.57  # 次日下跌率57%
```

---

### Factor 4: `trend_alignment` - 趋势对齐因子

**来源**: 东方圣《万次涨停回测》
- URL: https://www.tgb.cn/a/2r0quFL61AP-1

**量化规则**:
```python
# 趋势对齐条件（铁律一）
is_uptrend = (
    close > ma20 and close > ma60 and  # 站稳20日、60日均线
    ma20 > ma20_prev and ma60 > ma60_prev  # 均线向上发散（多头排列）
)

# 实证数据
# 87% 的连板股涨停前已站稳20日、60日均线
# 下跌趋势中涨停，次日连板率仅11%，80%次日低开低走
```

---

### Factor 5: `eod_low_suction` - 尾盘低吸因子（趋势股）

**来源**: 弈者谋势《当前市场方向与风格的应对技巧探讨》
- URL: https://www.tgb.cn/a/2mMqKAKazNv

**量化规则**:
```python
# 尾盘低吸选股九大条件
def eod_low_suction_signal(stock):
    conditions = [
        stock.is_uptrend and stock.broke_platform,  # 一、上升趋势突破平台
        stock.has_limit_up_history,  # 四、左边有大阳或涨停
        stock.pullback_to_ma5 and stock.volume_shrink,  # 二、缩量回调不破5日线
        stock.eod_volume_shrink and stock.has_lower_shadow,  # 三、尾盘缩量有下影线
        stock.no_premium_sellers,  # 五、涨停突破后无溢价割肉盘
        stock.hold_after_limit,  # 六、涨停后不跌
        stock.eod_active_buying and stock.price_at_low,  # 七、尾盘有资金抢筹且股价低位
        stock.emotion_turning_up,  # 八、冰点后尾盘向上拉升
        stock.has_accumulation_trace  # 九、有建仓痕迹/量能堆积
    ]
    return sum(conditions) >= 5  # 满足5条以上

# 买点细化
# - 大幅缩量回调不破5日线 → 较好买点
# - 突破后回调至20日线 → 可介入
# - 收小阳优于收小阴/十字星
# - 长阴短柱（跌幅大、成交小）后再次缩量收长下影/小阳 → 介入机会
```

**重要注意**: "尾盘拉涨停是偷鸡"（原文），需区分尾盘低吸趋势股 vs 尾盘偷袭涨停

---

### Factor 6: `relay_strategy_conditions` - 接力战法条件因子

**来源**: 弈者谋势《当前市场方向与风格的应对技巧探讨》
- URL: https://www.tgb.cn/a/2mMqKAKazNv

**量化规则**:
```python
# 一进二接力选股条件
class RelayConditions:
    # 买入类型一：弱转强接力
    weak_to_strong = [
        "炸板后高开反包",
        "大烂板后高开快速涨停",
        "断板后反包",
        "大阴线反核或反包",
        "低开后抢筹快速拉升涨停",
        "封成比超预期",
        "顶一字参与同属性核心票"
    ]
    
    # 选股筛选（每日复盘找"最"票）
    screening_criteria = {
        "梯队最前",  # 连板高度最高
        "地位最高",  # 板块核心
        "逻辑最强",  # 题材确定性
        "人气最旺",  # 热度关注度
        "小弟最多",  # 跟风最多
        "盘子最小",  # 市值小
        "股价最低",  # 股价低
        "位置最低",  # 起涨位置低
        "涨停最早",  # 封板时间早
        "套牢最轻",  # 上方无大量套牢盘
    }
    # 原文："有时仅凭其中一个最就可以上"

    # 关键数值条件
    open_gap = (0.03, 0.06)  # 开盘高开3-6%为好
    volume_pattern = "前期高量→下跌平/缩量→倍量涨停"  # 建仓痕迹
    
    # 禁区
    avoid = [
        "指数下跌、情绪退潮时放弃接力",
        "首板缩量涨停后秒板换手不足→次日高开低走",
        "开盘高开过多且开盘成交金额不足"
    ]
```

---

### Factor 7: `position_by_market_regime` - 大盘周期仓位因子

**来源**: 炒股为解套《转 龙头》
- URL: https://m.tgb.cn/a/22WTZ9li7eP?type=new

**量化规则**:
```python
# 大盘周期 → 仓位 → 操作模式
market_regimes = {
    "主升": {
        "condition": "情绪高涨，量能>1万亿，主线清晰，涨多跌少，连板赚钱效应强",
        "position": "全仓",
        "primary": "打板/龙头低吸",
        "secondary": "趋势龙头低吸"
    },
    "震荡": {
        "condition": "情绪一般，量能8000-10000亿，涨跌平衡，板块轮动",
        "primary": "趋势龙头低吸",
        "position": "半仓",
        "secondary": "打板/龙头低吸"
    },
    "下跌": {
        "condition": "情绪冰点，量能<8000亿，无主线一日游，涨少跌多",
        "position": "空仓",
        "primary": "坚决空仓等待"
    }
}
```

---

## 方向二：涨停回封/炸板回封策略

### Factor 8: `zhaban_next_day_loss` - 炸板次日亏损统计因子

**来源**: ppplay《主板首板炸板及二板炸板后次日平均亏损(2024年至今2025年)》
- URL: https://www.tgb.cn/a/2lIxXnBQF9z

**量化规则**:
```python
# 核心统计数据（2024.01.01 - 2025.09.29）
zhaban_stats = {
    "首板炸板": {
        "样本数": 3127,
        "次日平均亏损_开盘价": -0.0452,  # -4.52%
        "次日平均亏损_收盘价": -0.0578,  # -5.78%
        "次日开盘盈利占比": 0.347,  # 34.7%
        "次日收盘盈利占比": 0.293,  # 29.3%
    },
    "二板炸板": {
        "样本数": 789,
        "次日平均亏损_开盘价": -0.0587,  # -5.87%
        "次日平均亏损_收盘价": -0.0723,  # -7.23%
        "次日开盘盈利占比": 0.292,  # 29.2%
        "次日收盘盈利占比": 0.245,  # 24.5%
    }
}

# 按炸板时间分段（首板）
zhaban_by_time = {
    "早盘(9:30-10:30)":  {"avg_loss": -0.061, "win_rate": 0.282},
    "午间(10:30-14:00)": {"avg_loss": -0.042, "win_rate": 0.335},
    "尾盘(14:00后)":     {"avg_loss": -0.053, "win_rate": 0.301},
}

# 按题材强度（首板）
zhaban_by_theme = {
    "主线题材": {"avg_loss": -0.038, "win_rate": 0.386},
    "支线题材": {"avg_loss": -0.065, "win_rate": 0.251},
}

# 按情绪周期（二板）
zhaban_by_emotion = {
    "主升期": {"avg_loss": -0.041, "win_rate": 0.356},
    "退潮期": {"avg_loss": -0.079, "win_rate": 0.187},
}

# 按资金结构（二板）
zhaban_by_capital = {
    "游资主导": {"avg_loss": -0.068, "win_rate": 0.223},
    "机构介入": {"avg_loss": -0.037, "win_rate": 0.395},
}
```

---

### Factor 9: `huifeng_quality` - 回封质量因子

**来源**: ppplay《主板首板炸板及二板炸板后次日平均亏损》+ 富儿公《炸板回封交易法》
- URL: https://www.tgb.cn/a/2lIxXnBQF9z
- URL: https://www.tgb.cn/a/1J2ESG6yyho

**量化规则**:
```python
# 回封低风险条件（尾盘炸板回封）
def is_low_risk_huifeng(stock):
    """
    14:30后炸板且15分钟内回封 → 次日平均亏损仅-1.2%
    vs 不回封: -5.3%
    """
    return (
        stock.zhaban_time >= "14:30" and
        stock.huifeng_time - stock.zhaban_time <= timedelta(minutes=15) and
        stock.has_institutional_buy  # 机构介入更佳: 次日平均亏损-2.3%
    )

# 回封操作三步骤（富儿公方法）
# 第一步：观察上板力度
# 第二步：观察封单构成（大单占比、稳定性）
# 第三步：观察封板稳定性
# 给出炸板预判 + 下单反应时间
# 关键：抢回封时盘口已稳定、抛压轻
```

---

### Factor 10: `huifeng_board_entry` - 回封打板介入因子

**来源**: 炒股为解套《转 龙头》
- URL: https://m.tgb.cn/a/22WTZ9li7eP?type=new

**量化规则**:
```python
# 龙头分歧接力 - 回封打板条件
def huifeng_board_signal(stock):
    """开板分歧后弱转强回封"""
    conditions = {
        "必须核心龙头": stock.is_sector_leader,
        "高标连板": stock.consecutive_limits >= 4,
        "高人气": stock.hot_rank <= 5,
        "带动性": stock.has_follower_stocks,
        "放量换手": stock.turnover_rate_today > 0.15,  # 炸板必须放量换手
        "弱转强回封": stock.weak_to_strong_pattern,
    }
    return all(conditions.values())

# 具体操作手法
entry_rules = {
    "不封不打": "没封住不打板",
    "封住速排": "封住后迅速排队",
    "预炸速撤": "预感要炸提前撤单",
    "回封速打": "确认回封后快速打板",
    "确认扫板": "确认买入扫板"
}

# 卖点
exit_rules = {
    "次日竞价不及预期": "竞价卖出",
    "次日未涨停": "高点卖出",
    "次日涨停再次炸板": "板砸卖出（断板当日不回封即走）"
}
```

---

### Factor 11: `zhaban_high_risk_avoid` - 炸板高风险规避因子

**来源**: ppplay《主板首板炸板及二板炸板后次日平均亏损》
- URL: https://www.tgb.cn/a/2lIxXnBQF9z

**量化规则**:
```python
# 必须规避的高风险炸板类型
high_risk_zhaban = {
    "早盘秒板炸板": {
        "condition": "9:30-9:45封板后5分钟内炸板",
        "avg_loss": -0.068,
        "action": "坚决回避"
    },
    "无题材支撑炸板": {
        "condition": "板块当日涨停家数<=1家（孤儿板）",
        "avg_loss": -0.061,
        "action": "警惕资金诱多"
    },
    "退潮期二板炸板": {
        "condition": "连板高度<=3板且板块指数下跌",
        "avg_loss": -0.085,
        "action": "空仓观望"
    },
    "缩量加速炸板": {
        "condition": "二板量<首板量*0.6且封单<2万手",
        "avg_loss": -0.073,
        "action": "筹码断层引发抛压"
    },
    "关键支撑位失守": {
        "condition": "炸板后跌破5日线或前期平台",
        "avg_loss": -0.072,
        "note": "90%后续5日继续下跌"
    },
    "成交量异常放大": {
        "condition": "炸板时量>前5日均值*3",
        "avg_loss": -0.065,
        "note": "主力出逃迹象明显"
    }
}

# 相对低风险机会
low_risk_opportunity = {
    "尾盘炸板回封": {
        "condition": "14:30后炸板+15分钟内回封",
        "avg_loss": -0.012,
        "note": "部分标的可反包"
    },
    "机构介入炸板": {
        "condition": "龙虎榜机构净买入",
        "avg_loss": -0.023,
    },
    "主线题材分歧炸板": {
        "condition": "板块涨停>=5家且炸板后分时成交密集区>-3%",
        "avg_loss": -0.032,
        "note": "可通过弱转强修复"
    },
    "放量换手炸板(二板)": {
        "condition": "换手>30%且成交额环比首板+50%-100%",
        "avg_loss": -0.045,
        "note": "筹码充分换手后抛压减轻"
    }
}
```

---

## 方向三：尾盘战法/尾盘半路

### Factor 12: `eod_sneak_limit_penalty` - 尾盘偷袭涨停惩罚因子

**来源**: 东方圣《万次涨停回测》
- URL: https://www.tgb.cn/a/2r0quFL61AP-1

**量化规则**:
```python
# 尾盘偷袭涨停（14:50后封板）
eod_sneak_signal = {
    "特征": "最后10分钟拉板，封单小、量能虚、抛压大",
    "次日下跌率": 0.61,  # 61%次日下跌
    "惯性低开概率": 0.826,  # 82.6%次日惯性低开
    "操作建议": "必避，主力诱多，第二天直接埋人"
}

# 区分规则：
# 尾盘偷袭板 ≠ 尾盘低吸趋势股
# 偷袭板：无前期铺垫，突然拉板
# 低吸趋势股：上升趋势+缩量回调+尾盘止跌企稳
```

---

### Factor 13: `eod_buying_window` - 尾盘买入时间窗口因子

**来源**: 弈者谋势《当前市场方向与风格的应对技巧探讨》+ 淘股吧话题《尾盘买入法》
- URL: https://www.tgb.cn/a/2mMqKAKazNv
- URL: https://www.tgb.cn/talk/talkSeq/65238

**量化规则**:
```python
# 尾盘低吸策略框架
class EODLowSuction:
    """
    核心逻辑：利用T+1规则，尾盘买入争取次日先手
    规避日内波动风险，降低成本，避免追高被量化收割
    """
    
    # 选时条件
    timing = {
        "买入": "冰点后尾盘出现向上拉升可买",
        "不买": "尾盘大幅下杀时不买",
        "预判": "预判次日指数与题材走势"
    }
    
    # 选股条件（9项条件清单）
    stock_selection = {
        1: "个股处于上升趋势，突破平台",
        2: "涨停+趋势走法为主，大幅缩量回调不破5日线",
        3: "尾盘缩量有下影线（收小阳最佳）",
        4: "左边有大阳或涨停的更强势",
        5: "涨停突破后无溢价割肉盘→轻仓介入",
        6: "涨停后不跌的个股",
        7: "尾盘有资金抢筹且股价必须在低位",
        8: "注意选时+执行计划+止损纪律",
        9: "有建仓痕迹、量能堆积、业绩增长、多次涨停"
    }
    
    # 卖点
    exit = "次日不涨停就卖出"  # 尾盘买入法典型思路
```

---

### Factor 14: `eod_zhaban_time_penalty` - 炸板时段与次日低开概率

**来源**: ppplay《主板首板炸板及二板炸板后次日平均亏损》
- URL: https://www.tgb.cn/a/2lIxXnBQF9z

**量化规则**:
```python
# 不同时段炸板的次日低开率
eod_zhaban_penalty = {
    "14:00后炸板": {
        "avg_loss": -0.053,
        "win_rate": 0.301,
        "next_day_low_open_prob": 0.826,  # 82.6%惯性低开
        "reason": "资金抢跑或指数拖累"
    }
}

# 但如果14:30后炸板+15分钟内回封 → 反转信号
eod_huifeng_reversal = {
    "avg_loss": -0.012,  # 仅-1.2%
    "example": "某机器人概念股尾盘炸板回封后次日+5.3%"
}
```

---

## 方向四：资金接力链条/板块轮动节奏

### Factor 15: `leader_succession_cycle` - 龙头接替周期因子

**来源**: 直击七寸123456《干货贴：龙头-补涨-切换-空仓》
- URL: https://www.tgb.cn/a/26R2UPyruwj

**量化规则**:
```python
# 龙头识别方法
def identify_new_leader(market_state):
    """
    规则：龙头断板的前一日或当日，是下一只龙头出现首板的时间节点
    验证方法：
    1. 龙头断板 → 杀中位股（3板以上）
    2. 中位股被淘汰后，剩余的唯一最高标 = 新龙头
    3. 新龙头通常在4板或5板时可确认
    """
    old_leader_break_date = market_state.leader_break_date
    # 在断板前一日或当日的首板/二板中寻找
    candidates = get_new_boards(date_range=[old_leader_break_date - 1, old_leader_break_date])
    
    # 等中位股淘汰后，看谁存活且成为唯一最高标
    for day in range(old_leader_break_date + 1, old_leader_break_date + 3):
        survivors = get_surviving_highest(day)
        if len(survivors) == 1:  # 唯一性确认
            return survivors[0]  # 新龙头

# 操作周期八字箴言
cycle = "龙头 → 补涨 → 空仓 → 切换"
```

---

### Factor 16: `buchang_dragon_timing` - 补涨龙出现时机因子

**来源**: 直击七寸123456《干货贴：龙头-补涨-切换-空仓》
- URL: https://www.tgb.cn/a/26R2UPyruwj

**量化规则**:
```python
# 补涨龙两种类型
class BuchangDragon:
    # 类型一：伴随补涨龙
    class Companion:
        """
        出现时机：龙头追平或破局之前连板压制的时间节点
        特征：与龙头同属性/同逻辑
        断板规律：与龙头断板日相同 或 前后相差一天
        """
        timing = "龙头高度追平之前的连板压制 或 破局前期的连板压制"
        exit_rule = "断板之日必须及时卖出，不可格局"
        
    # 类型二：龙头断板后的补涨
    class PostBreak:
        """
        出现时机：龙头断板前一日 或 断板当日
        必须条件：与龙头有共同逻辑性或同属性
        """
        timing = "龙头断板前一日或当日的涨停板中"
        difficulty = "多只候选时存在竞争关系，后期PK淘汰"
        exit_rule = "断板即走，大多A杀走势"
        
    # PK胜出规则（同级别候选中选择更优的）
    pk_criteria = {
        "市值更小": "优于大盘子",
        "股价更低": "优于高价股",
        "实体板更多": "优于一字板多的"
    }
    
    # 补涨心理逻辑
    psychology = "看到龙头大涨又不愿追高→转向同题材低位票→减少分歧直接一致→常走加速"
```

---

### Factor 17: `sector_rotation_signal` - 板块轮动切换信号因子

**来源**: 直击七寸123456《干货贴》+ 大龙丫丫《资金高低切换防守态度》
- URL: https://www.tgb.cn/a/26R2UPyruwj
- URL: https://www.tgb.cn/a/2oZ8RmCz3lE

**量化规则**:
```python
# 退潮期两大信号
def detect_retreat_phase(market):
    signal_1 = (
        market.highest_consecutive_limit_break and  # 全市场最高连板断板见顶
        market.mid_level_stocks_collective_loss  # 中位股集体吃面
    )
    signal_2 = (
        market.nuclear_button_appeared  # 核按钮出现
        # 强势股(前日涨停)次日直接跌停或天地板
    )
    return signal_1 or signal_2

# 退潮期操作
retreat_strategy = {
    "大多数人": "空仓（最优解）",
    "少数敏锐者": "高切低试错当下新热点题材方向",
    "禁忌": "不能追高，尽量不打板"
}

# 切换定义
switch_rule = """
切换 = 与当前/之前龙头炒作完全不同或大部分不同
不同共性才能聚集新人气，因为老共性都在散发亏钱效应
切换的目的是找下一阶段的龙头
"""

# 高低切换信号（大龙丫丫数据）
high_low_switch_signals = {
    "首板晋级成功率大幅增加 + 跌停板>10家": "情绪分歧风险信号",
    "进攻性板块大分歧 + 资金做低位补涨": "混沌周期试错阶段",
    "资金进攻意愿降低": "倾向防守或低位板块避险",
    "板块前排放巨量震荡": "筹码不稳定信号"
}
```

---

### Factor 18: `emotion_cycle_position` - 情绪周期仓位管理因子

**来源**: 炒股为解套《转 龙头》+ 大龙丫丫《资金高低切换》
- URL: https://m.tgb.cn/a/22WTZ9li7eP?type=new
- URL: https://www.tgb.cn/a/2oZ8RmCz3lE

**量化规则**:
```python
# 四阶段情绪周期操作框架
emotion_cycle = {
    "第一阶段_题材主升期": {
        "position": "重仓猛干",
        "primary": "龙头分歧接力 + 龙头趋势低吸",
        "key": "买在分歧预期差，卖出一致预期兑现",
        "leader_entry": "分歧转一致的连板确认打板",
        "leader_exit": "断板当日不回封即走",
        "trend_leader_entry": "主升一浪首次分歧回调5日线附近分批低吸",
        "trend_leader_exit": "高位首次有效跌破5日线"
    },
    "第二阶段_高位震荡期": {
        "position": "轻仓博弈",
        "primary": "同题材高低切换→龙头补涨首板打板",
        "conditions": [
            "高标龙头5板以上必然发酵同题材低位补涨",
            "龙头断板必须温和调整不能A杀大幅负反馈",
            "补涨龙必须是卡位日内第一个首板",
            "补涨龙一般一波到顶然后A杀"
        ]
    },
    "第三阶段_题材主跌期": {
        "position": "空仓为最优解",
        "options": [
            "博弈杀跌反抽（第二天持续杀跌，尾盘找买点，第三天有修复）",
            "新题材切换轻仓试错"
        ],
        "warning": "坑完板客坑低吸，空仓应对无人及"
    },
    "第四阶段_低位震荡期": {
        "position": "轻仓试错",
        "primary": "新题材首板套利+新题材二板竞价打板",
        "key": "龙头见顶杀高位的阶段，往往是布局低位新题材的最好时机"
    }
}

# 仓位控制
position_control = {
    "standard": "分仓3票",
    "light_test": "单票1万",
    "standard_build": "单票2万",
    "heavy_add": "单票3万",
    "max_concentrated": "确定性机会，单票5万（不参与回调）"
}
```

---

### Factor 19: `buchang_dragon_kawei` - 补涨龙卡位因子

**来源**: 炒股舵主阿海哥《大盘节点+补涨龙卡点理解》
- URL: https://www.tgb.cn/a/2qnxaNXaNON-1

**量化规则**:
```python
# 补涨龙卡位成功/失败的应对
def buchang_kawei_strategy(buchang_dragon, old_leader):
    """
    补涨龙定位：老龙同属性、同题材链条
    卡位判断：补涨龙能否突破当前连板高度压制
    """
    target_height = old_leader.max_consecutive_limits  # 如7板
    
    if buchang_dragon.consecutive_limits >= target_height:
        # 卡位成功 = 新龙登基
        # 此时边打边撤老题材，迎接新题材
        action = "老题材边打边撤，空仓位等新主升"
    else:
        # 卡位失败
        # 题材退潮，中位股人均一个跌停
        action = "赶快走，不玩中位股，不玩其他杂题材"
    
    return action

# 关键判断节点
key_insight = """
如果补涨龙过不了龙头高度（如7板），就是补涨龙失败。
如果不能催助龙头涨停，题材退潮。
如果卡位成功（新龙登基），底下会有新题材出现 = 真正的主升。
"""
```

---

### Factor 20: `sector_phase_tracking` - 板块趋势阶段跟踪因子

**来源**: 大龙丫丫《资金高低切换防守态度》
- URL: https://www.tgb.cn/a/2oZ8RmCz3lE

**量化规则**:
```python
# 板块趋势阶段跟踪
class SectorPhaseTracker:
    """
    每个板块按"阶段"编号，标注每阶段的领涨核心
    用于判断板块处于主升/分歧/退潮的哪个位置
    """
    
    # 实际数据示例（AI/人工智能板块）
    ai_phases = {
        1: {"leaders": ["海立股份", "淳中科技"], "followers": ["张江高科"]},
        2: {"leaders": ["海立股份", "东芯股份"]},
        5: {"leaders": ["寒武纪", "海光信息"]},
        # ... 到第13阶段
        13: {"leaders": ["通富微电", "海光信息"]},
    }
    
    # 板块强度判断信号
    strength_signals = {
        "positive": [
            "连板高位板继续晋级突破高度空间",
            "主动进监控的情绪标震荡走强",
            "断板容量票走强修复",
            "行业龙头未走弱补跌"
        ],
        "negative": [
            "前排核心走弱",
            "批量炸板无修复反包",
            "跌停极端负反馈",
            "板块指数有效破5日线"
        ]
    }
    
    # 实战情绪数据
    emotion_metrics = {
        "涨停板家数": 82,
        "连板股家数": 19,
        "炸板率": 0.299,  # 29.9%
        "首板晋级成功率": 0.20,  # 20%
        "跌停家数": 12,
        "涨停总成交/市场总量": 0.47,  # 0.47为中区间
    }
```

---

### Factor 21: `competition_bidding_entry` - 竞价超预期介入因子

**来源**: 炒股为解套《转 龙头》
- URL: https://m.tgb.cn/a/22WTZ9li7eP?type=new

**量化规则**:
```python
# 二板竞价打板条件（竞价量能判断）
def bidding_volume_threshold(stock):
    """
    竞价量能判断标准：
    - 与昨日涨停爆量对比：竞价量>=50%符合预期，>=66%超预期，>=100%爆量
    - 与昨日成交额对比（按市值分档）：
    """
    thresholds_by_turnover = {
        "2亿以下": 0.15,    # 竞价占昨日成交15%
        "2-5亿":  0.10,    # 竞价占昨日成交10%
        "5-10亿": 0.08,    # 竞价占昨日成交8%
        "10-20亿": 0.05,   # 竞价占昨日成交5%
        "20亿以上": 0.04,  # 竞价占昨日成交4%
    }
    
    # 竞价涨幅与操作
    bidding_actions = {
        "高开3%-5%": {
            "condition": "竞价量>=首板爆量50%，分时重心平稳或临近结束小幅上涨抢筹",
            "action": "买入一半仓位"
        },
        "高开8%-10%": {
            "condition": "竞价量>=首板爆量100%，分时重心平稳，结束时涨停价2%内小幅下砸最佳",
            "action": "买入一半仓位（最强信号）"
        },
        "高开5%-8%": {
            "condition": "风报比不高",
            "action": "谨慎，尤其缩量强高开到此位置"
        }
    }
    return thresholds_by_turnover, bidding_actions
```

---

## 综合因子交叉应用建议

```python
# 组合应用框架
def trading_decision(market_state, stock):
    # Step 1: 判断大盘周期 (Factor 7)
    regime = get_market_regime(market_state)
    if regime == "下跌":
        return "空仓"
    
    # Step 2: 判断情绪周期阶段 (Factor 18)
    phase = get_emotion_phase(market_state)
    
    # Step 3: 根据阶段选择策略
    if phase == "主升期":
        # 龙头打板/低吸 (Factor 6, 10)
        if stock.is_leader and stock.weak_to_strong:
            return "回封打板" if stock.at_limit else "5日线低吸"
    
    elif phase == "高位震荡":
        # 补涨龙卡位 (Factor 16, 19)
        if stock.is_buchang_candidate:
            return "首板打板（轻仓）"
    
    elif phase == "主跌期":
        # 尾盘低吸试错 (Factor 5, 13)
        if stock.eod_low_suction_signal:
            return "尾盘低吸（极轻仓）"
    
    elif phase == "切换期":
        # 新题材试错 (Factor 17)
        return "新题材首板套利"
    
    # Step 4: 风控 - 避免高风险炸板 (Factor 11)
    if stock.zhaban_high_risk:
        return "回避"
```

---

## 来源索引

| # | 作者 | 帖子标题 | URL |
|---|------|---------|-----|
| 1 | 东方圣 | 万次涨停回测：次日必涨的铁律！看懂这3点，抓板成功率超85% | https://www.tgb.cn/a/2r0quFL61AP-1 |
| 2 | 弈者谋势 | 当前市场方向与风格的应对技巧探讨 | https://www.tgb.cn/a/2mMqKAKazNv |
| 3 | 直击七寸123456 | 干货贴：龙头-补涨-切换-空仓 | https://www.tgb.cn/a/26R2UPyruwj |
| 4 | 炒股为解套 | 转 龙头（龙头战法完整体系） | https://m.tgb.cn/a/22WTZ9li7eP?type=new |
| 5 | ppplay | 主板首板炸板及二板炸板后次日平均亏损(2024年至今2025年) | https://www.tgb.cn/a/2lIxXnBQF9z |
| 6 | 富儿公 | 炸板回封交易法2 | https://www.tgb.cn/a/1J2ESG6yyho |
| 7 | 大龙丫丫 | 资金高低切换防守态度，短期内变盘阶段！ | https://www.tgb.cn/a/2oZ8RmCz3lE |
| 8 | 炒股舵主阿海哥 | 大盘节点+补涨龙卡点理解 | https://www.tgb.cn/a/2qnxaNXaNON-1 |
| 9 | (话题聚合) | 尾盘买入法 | https://www.tgb.cn/talk/talkSeq/65238 |
| 10 | (话题聚合) | 高低切换板块切换 | https://www.tgb.cn/talk/talkSeq/119596 |

---

## 数据质量说明

1. **Factor 8 (炸板统计)**: ppplay帖子声明数据为AI生成的统计分析，基于2024.01-2025.09历史数据，样本量3127(首板)+789(二板)，数据仅供参考。
2. **Factor 1-4 (涨停铁律)**: 东方圣声明数据来自同花顺、东方财富、证券时报数据宝等终端。样本10276次涨停(2021-2026)。
3. **Factor 5-6 (尾盘低吸/接力)**: 弈者谋势为实战经验总结，含具体案例但无大样本统计。
4. **Factor 15-16 (龙头/补涨)**: 直击七寸123456为规律性描述+历史案例验证，非统计回测。
5. 所有因子均来自论坛用户帖子，需进一步量化回测验证后方可用于实盘策略。

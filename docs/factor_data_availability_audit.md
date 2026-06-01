# 短线因子.md 全部424因子 数据可得性审计

> 审计日期: 2026-05-07
> 基于现有数据环境: 日频OHLCV + 5min K线(Tushare stk_mins_5) + Tushare Pro已缓存32类数据

## 分类标准

| 标记 | 含义 | 数据来源 |
|------|------|----------|
| ✅ | **能算** | 日频OHLCV / 5min K线 / 已缓存Tushare数据直接计算 |
| ⚠️ | **需额外对接** | Tushare Pro有接口但你还没拉, 或需手动整理/爬虫 |
| ❌ | **取不到** | 需要Level-2/Wind付费终端/另类数据商, 当前无法获取 |
| 🔧 | **纯逻辑/模型** | 不需要额外数据, 是策略逻辑/组合方法/模型框架 |

---

## ✅ 能算 (252个)

### A. 日频OHLCV直接计算 (核心价量因子)

| # | 因子代码 | 所需数据 |
|---|----------|----------|
| 1 | `AMIHUD_ADJ` | 日频收益率+成交额 |
| 2 | `ATO` | 日频open/close |
| 3 | `ATTACK_WAVE_QUALITY` | 日频OHLCV |
| 4 | `BAB_ADJ` | 日频收益率+市场收益 |
| 5 | `BETA` | 日频收益率+指数收益 |
| 6 | `BETA_REGIME_SWITCH` | 日频收益率+指数收益 |
| 7 | `BOARD_ENTRY_TIMING` | 日频OHLCV(涨停时刻需5min) |
| 8 | `BOARD_HEIGHT_CEILING` | 日频涨停统计 |
| 9 | `BOARD_QUALITY_COMPOSITE` | 日频OHLCV+涨停统计 |
| 10 | `BREADTH_INDICATOR` | 日频全市场涨跌统计 |
| 11 | `BREADTH_THRUST_SIGNAL` | 日频全市场涨跌统计 |
| 12 | `BREAKOUT_TRAP_REVERSAL` | 日频OHLCV |
| 13 | `BREAK_BOARD_EXHAUSTION_REBOUND` | 日频OHLCV+涨停统计 |
| 14 | `BULL_BEAR_REGIME_DETECTOR` | 日频指数 |
| 15 | `BULL_TRAP_BEAR_TRAP` | 日频OHLCV |
| 16 | `CGO` | 日频OHLCV(计算参考价格) |
| 17 | `CGO_CHINA` | 日频OHLCV+换手率 |
| 18 | `CHIP_EXCHANGE_COMPLETENESS` | 日频换手率累计 |
| 19 | `CHIP_LOCK_RATIO` | 日频OHLCV(筹码分布近似) |
| 20 | `CHIP_PROFIT_LOSS_DISTRIBUTION` | 日频OHLCV(cyq_perf有) |
| 21 | `CHIP_VACUUM_RATIO` | 日频OHLCV(跳空缺口) |
| 22 | `CIRCUIT_BREAKER_PROXIMITY` | 日频涨跌幅 |
| 23 | `CMA` | 日频+年报(Tushare财报) |
| 24 | `COMPOSITE_ENTRY_SCORE` | 日频OHLCV(多因子组合) |
| 25 | `COMPOSITE_SCORE` | 多因子合成 |
| 26 | `CONSECUTIVE_BREAK_AFTERMATH` | 日频涨停统计 |
| 27 | `CONSENSUS_TO_DIVERGENCE` | 日频涨停/炸板 |
| 28 | `COOLING_PERIOD_REENTRY_SIGNAL` | 日频OHLCV |
| 29 | `COSKEW` | 日频收益率 |
| 30 | `CROSS_SECTOR_SPILLOVER` | 日频行业指数 |
| 31 | `CSM` | 日频收益率(截面) |
| 32 | `DBETA` | 日频收益率 |
| 33 | `DECISION_TREE_COMPOSITE` | 多因子组合逻辑 |
| 34 | `DECISION_TREE_LEAF_SCORE` | 多因子组合逻辑 |
| 35 | `DEEP_WATER_TURNBACK_STRENGTH` | 日频OHLCV |
| 36 | `DFR` | 日频收益率 |
| 37 | `DIVERGENCE_TO_CONSENSUS` | 日频涨停/炸板统计 |
| 38 | `DOW` | 日频(星期几) |
| 39 | `DYNMOM` | 日频收益率 |
| 40 | `EXTREME_MOVE_MEAN_REVERSION` | 日频收益率 |
| 41 | `EXTREME_SENTIMENT_REVERSAL` | 日频全市场涨跌停 |
| 42 | `FALSE_BREAKOUT_DETECTOR` | 日频OHLCV |
| 43 | `FEAR_GREED_COMPOSITE_INDEX` | 日频多维度合成 |
| 44 | `FIRST_NEGATIVE_REPAIR_QUALITY` | 日频OHLCV |
| 45 | `FLASH_CRASH_DETECTOR` | 日频收益率 |
| 46 | `FREEZING_POINT_COMPOSITE` | 日频涨跌停统计 |
| 47 | `FREEZING_REVERSAL_SIGNAL` | 日频涨跌停统计 |
| 48 | `FRIDAY_DRIFT` | 日频(周五效应) |
| 49 | `GAP_FILL_PROBABILITY` | 日频OHLCV(跳空) |
| 50 | `GPM` | 日频收益率(利润增长需财报) |
| 51 | `HAR_RV_RESID` | 5min K线计算已实现波动率 |
| 52 | `HISTORICAL_LIMIT_UP_DNA` | 日频涨停历史 |
| 53 | `HMM_REGIME` | 日频收益率(HMM模型) |
| 54 | `HOL_DRIFT` | 日频(节假日前后) |
| 55 | `IDIOSYNCRATIC_MOMENTUM` | 日频收益率(回归残差) |
| 56 | `IMS` | 日频收益率 |
| 57 | `IND_CONCENTRATION` | 日频行业内个股收益 |
| 58 | `IND_CROWD` | 日频换手率+估值+相关性 |
| 59 | `IND_LEAD_LAG` | 日频行业收益率 |
| 60 | `IND_MOM` | 日频行业收益率 |
| 61 | `IND_REVERSAL` | 日频行业收益率 |
| 62 | `IPCA` | 日频收益率(模型) |
| 63 | `IPO_REGIME` | 日频OHLCV(次新) |
| 64 | `IVOL` | 日频收益率(残差波动) |
| 65 | `KMID2` | 日频OHLCV |
| 66 | `KSFT2` | 日频OHLCV |
| 67 | `LEADER_COMPOSITE_SCORE` | 日频涨停+板块统计 |
| 68 | `LEADER_FOLLOWER_PREMIUM` | 日频涨停统计 |
| 69 | `LEADER_FOLLOWER_REPAIR_SPREAD` | 日频涨停统计 |
| 70 | `LEADER_LIFECYCLE_STAGE` | 日频连板统计 |
| 71 | `LEADER_PULLBACK_QUALITY` | 日频OHLCV |
| 72 | `LEADER_SWITCH_SIGNAL` | 日频涨停统计 |
| 73 | `LEFT_PRESSURE_BREAK_EFFICIENCY` | 日频OHLCV |
| 74 | `LIMIT_DOWN_PRY_EXHAUSTION` | 日频跌停+成交量 |
| 75 | `LIMIT_HIT_FREQ` | 日频涨停统计 |
| 76 | `LIMIT_PREMIUM_REGIME` | 日频涨停+次日溢价 |
| 77 | `LIMIT_UP_DOWN_RATIO` | 日频涨跌停家数 |
| 78 | `LIMIT_UP_NEXT_DAY_PREMIUM_PREDICT` | 日频涨停+次日收益 |
| 79 | `LIQUIDITY_REGIME_CLASSIFIER` | 日频成交额 |
| 80 | `LIQUIDITY_TRAP_DETECTOR` | 日频成交额+市值 |
| 81 | `LS` | 日频收益率 |
| 82 | `MACD_DIVERGENCE_SIGNAL` | 日频OHLCV |
| 83 | `MARKET_EMOTION_CYCLE_PHASE` | 日频涨跌停统计(已实现) |
| 84 | `MARKET_EMOTION_THERMOMETER` | 日频涨跌停统计(已实现) |
| 85 | `MAX5` | 日频收益率 |
| 86 | `MAX_CHINA` | 日频收益率(MAX效应) |
| 87 | `MEAN_REVERSION_TENDENCY` | 日频收益率 |
| 88 | `MICRO_CAP_LIQUIDITY_TRAP` | 日频市值+成交额 |
| 89 | `MOM_CRASH_PREDICT` | 日频收益率+波动率 |
| 90 | `MOM_VALUE_INTER` | 日频收益率+估值 |
| 91 | `MONSTER_EMBRYO` | 日频涨停统计 |
| 92 | `MONTH_END_WINDOW_DRESSING` | 日频(月末效应) |
| 93 | `N52H` | 日频OHLCV(52周新高) |
| 94 | `NN_MOM` | 日频收益率(模型) |
| 95 | `NONLINEAR_FACTOR` | 日频因子交互 |
| 96 | `OPEN_BOARD_QUALITY` | 日频涨停+成交量 |
| 97 | `OPEN_BOARD_VOLUME_ABSORPTION` | 日频OHLCV+涨停 |
| 98 | `OVERNIGHT_GAP_RISK` | 日频open vs prev_close |
| 99 | `OVERNIGHT_RETURN_REVERSAL` | 日频open vs prev_close |
| 100 | `OVERNIGHT_RET` | 日频open vs prev_close |
| 101 | `PANIC_RELEASE_COMPLETION` | 日频成交量+跌幅 |
| 102 | `PREMIUM_DECAY_CURVE` | 日频涨停+后续收益 |
| 103 | `PREV_CLOSE_RECLAIM_SPEED` | 日频OHLCV |
| 104 | `PRE_HOLIDAY_EFFECT` | 日频(节假日日历) |
| 105 | `PROMOTION_RATE_TRACKER` | 日频涨停晋级率 |
| 106 | `QMJ` | 日频+财报(ROE/利润) |
| 107 | `QUANT_CROWDING_INDEX` | 日频收益率相关性 |
| 108 | `QUANT_CROWDING_PROXY` | 日频收益率模式 |
| 109 | `QUANT_VS_RETAIL_REGIME` | 日频成交模式 |
| 110 | `RECOGNITION_COMPOSITE` | 日频涨停+辨识度 |
| 111 | `REGIME_COND` | 日频(条件因子) |
| 112 | `RESMOM` | 日频(残差动量) |
| 113 | `RESUMPTION_GAP_QUALITY` | 日频停复牌 |
| 114 | `REVERSAL_BOARD_QUALITY` | 日频涨停统计 |
| 115 | `RJV` | 日频收益率(已实现跳跃) |
| 116 | `ROC` | 日频收益率 |
| 117 | `ROE_PROF` | 日频+财报(ROE) |
| 118 | `RSKEW` | 5min K线(已实现偏度) |
| 119 | `RSK` | 日频收益率(偏度) |
| 120 | `RSQR` | 日频收益率(R²) |
| 121 | `RSV_20` | 日频OHLCV |
| 122 | `SEAL_DEPTH_RATIO` | 日频涨停(近似) |
| 123 | `SEAL_ORDER_TURNOVER_RATIO` | 日频涨停+成交额(近似) |
| 124 | `SEAMOM` | 日频(季节性动量) |
| 125 | `SECOND_WAVE_BREAKOUT` | 日频OHLCV |
| 126 | `SECTOR_CROWDING_ROTATION` | 日频板块数据 |
| 127 | `SECTOR_INTERNAL_DIVERGENCE` | 日频板块内个股 |
| 128 | `SECTOR_MOMENTUM_REVERSAL_TIMING` | 日频板块指数 |
| 129 | `SECTOR_PREMIUM_BASELINE` | 日频板块涨停统计 |
| 130 | `SECTOR_RELATIVE_STRENGTH_RANK` | 日频板块指数 |
| 131 | `SECTOR_ROTATION_MOMENTUM` | 日频板块指数 |
| 132 | `SENTIMENT_PENDULUM_POSITION` | 日频涨跌停统计 |
| 133 | `SHELL_VALUE` | 日频+基本面(市值/营收) |
| 134 | `SHRINK_TO_FLOOR_SIGNAL` | 日频成交量 |
| 135 | `SIZE_QUALITY_INTER` | 日频市值+财报 |
| 136 | `SIZE_REGIME` | 日频大小盘指数 |
| 137 | `SPACE_BOARD_DISTANCE` | 日频涨停高度 |
| 138 | `SPRING_FEST` | 日频(春节效应) |
| 139 | `STD_20` | 日频收益率 |
| 140 | `STOCK_INDEX_DIVERGENCE` | 日频个股vs指数 |
| 141 | `STOCK_PERSONALITY_ACTIVITY` | 日频OHLCV(波动特征) |
| 142 | `STOCK_PERSONALITY` | 日频OHLCV(历史模式) |
| 143 | `ST_REMOVAL` | 日频+公告(suspend_d有) |
| 144 | `ST_REMOVAL_PREHEAT` | 日频+公告 |
| 145 | `ST_REMOVAL_WINDOW` | 日频+公告 |
| 146 | `SUBSTITUTE_LEADER` | 日频涨停统计 |
| 147 | `SUB_NEW_OPEN_BOARD_TIMING` | 日频OHLCV(次新开板) |
| 148 | `SUB_NEW_VOLATILITY_PREMIUM` | 日频OHLCV(次新波动) |
| 149 | `THEME_LIFECYCLE_STAGE` | 日频板块涨停统计 |
| 150 | `TIER_PROMOTION_RATE` | 日频连板晋级率 |
| 151 | `TOM` | 日频(月初效应) |
| 152 | `TRANSITION_SPEED` | 日频OHLCV |
| 153 | `TRAPPED_TRADER_PRESSURE` | 日频OHLCV(套牢盘) |
| 154 | `TURNOVER_HANDOFF_QUALITY` | 日频换手率 |
| 155 | `TURNOVER_SPIKE_CLASSIFICATION` | 日频换手率 |
| 156 | `VALUE_GROWTH_ROTATION` | 日频风格指数 |
| 157 | `VMA` | 日频成交量 |
| 158 | `VOLATILITY_SPIKE_DETECTOR` | 日频收益率 |
| 159 | `VOLUME_PRICE_DIVERGENCE_ALERT` | 日频OHLCV |
| 160 | `VOLUME_PRICE_DIVERGENCE` | 日频OHLCV |
| 161 | `VOLUME_PRICE_PIVOT_STABILITY` | 日频OHLCV |
| 162 | `VOLUME_REGIME_TRANSITION` | 日频成交量 |
| 163 | `VOLUME_STRUCTURE_QUALITY` | 日频成交量 |
| 164 | `VOV` | 日频收益率(波动率的波动) |
| 165 | `VSTD` | 日频成交量标准差 |
| 166 | `WEAK_TO_STRONG_TRANSITION` | 日频OHLCV |
| 167 | `WEAK_TO_STRONG_VOLUME_EFFICIENCY` | 日频OHLCV |
| 168 | `FALSE_WEAK_CLASSIFICATION` | 日频OHLCV |
| 169 | `FACTOR_CROWD` | 日频因子收益序列 |
| 170 | `FACTOR_CROWD_DETECT` | 日频因子收益序列 |
| 171 | `COMPOSITE_TIMING` | 日频多因子合成 |
| 172 | `ADVANCE_DECLINE_MOMENTUM` | 日频全市场涨跌 |

### B. 5分钟K线计算 (已有stk_mins_5)

| # | 因子代码 | 所需数据 |
|---|----------|----------|
| 173 | `FIRST_HALFHOUR_MOMENTUM` | 5min K线(前30分钟) |
| 174 | `INTRADAY_CONSOLIDATION_BREAK` | 5min K线 |
| 175 | `INTRADAY_CORRELATION_PENALTY` | 5min K线 |
| 176 | `INTRADAY_FLOW_REVERSAL` | 5min K线+成交额 |
| 177 | `INTRADAY_N_SHAPE_BREAKOUT` | 5min K线 |
| 178 | `INTRADAY_RANGE_STABILITY` | 5min K线 |
| 179 | `INTRADAY_REVERSAL_FREQUENCY` | 5min K线 |
| 180 | `INTRADAY_REVERSAL` | 5min K线 |
| 181 | `INTRADAY_STAIRCASE_PATTERN` | 5min K线 |
| 182 | `INTRADAY_V_SHAPE_QUALITY` | 5min K线 |
| 183 | `INTRADAY_WATERFALL_DEPTH` | 5min K线 |
| 184 | `LAST30_MOM` | 5min K线(尾盘30分钟) |
| 185 | `OPTIMAL_ENTRY_TIME_OF_DAY` | 5min K线 |
| 186 | `VPIN_DAILY` | 5min K线(BVC近似VPIN) |
| 187 | `VWAP_DEVIATION_SIGNAL` | 5min K线(计算VWAP) |
| 188 | `EARLY_SESSION_MOMENTUM_CONFIRM` | 5min K线 |
| 189 | `TIME_SLICE_UNIFORMITY` | 5min K线 |
| 190 | `AFTERNOON_REFLOW_BREADTH` | 5min K线 |
| 191 | `TAIL_CHASE_COORDINATION` | 5min K线(尾盘) |
| 192 | `REFLOW_LEADER_CONFIRMATION` | 5min K线 |

### C. Tushare已缓存数据直接计算

| # | 因子代码 | 数据来源 |
|---|----------|----------|
| 193 | `AUCTION_CANCEL_RATE` | stk_auction_o |
| 194 | `AUCTION_CANCEL_RATIO` | stk_auction_o |
| 195 | `AUCTION_GAP_CLASSIFICATION` | stk_auction_o + daily |
| 196 | `AUCTION_LAST_MINUTE_STABILITY` | stk_auction_o |
| 197 | `AUCTION_PRICE_DISCOVERY_QUALITY` | stk_auction_o |
| 198 | `AUCTION_PRICE_DIVERGENCE` | stk_auction_o + daily |
| 199 | `AUCTION_RETURN_POSITION` | stk_auction_o + daily |
| 200 | `AUCTION_VOLUME_PROPORTION` | stk_auction_o + daily_basic |
| 201 | `AUCTION_VOLUME_RATIO_SIGNAL` | stk_auction_o |
| 202 | `BLOCK_TRADE_ABSORPTION_CAPACITY` | block_trade |
| 203 | `BLOCK_TRADE_BUYER_IDENTITY` | block_trade |
| 204 | `BLOCK_TRADE_DISCOUNT_RATE` | block_trade |
| 205 | `CAPITAL_RELAY_DETECTION` | moneyflow |
| 206 | `COUNTERPARTY_STRENGTH_RATIO` | top_list |
| 207 | `DAYS_TO_COVER` | margin_detail |
| 208 | `FLOAT_CAP_SWEET_SPOT` | daily_basic(流通市值) |
| 209 | `HOT_MONEY_SEAT_CONCENTRATION` | top_list |
| 210 | `INSTITUTIONAL_HOLDING_MOMENTUM` | hk_hold(北向) |
| 211 | `INSTITUTIONAL_VS_HOTMONEY_RATIO` | top_list + top_inst |
| 212 | `IPO_FIRST_DAY_TURNOVER_STRENGTH` | daily_basic |
| 213 | `KNOWN_SEAT_HISTORICAL_WIN_RATE` | top_list(历史龙虎榜) |
| 214 | `LOCKUP_EXPIRY_ANTICIPATION` | Tushare share_float接口 |
| 215 | `MAIN_FORCE_NET_INFLOW_INTENSITY` | moneyflow |
| 216 | `MARGIN_BAL_CHG` | margin_detail |
| 217 | `MARGIN_BALANCE_MOMENTUM` | margin_detail |
| 218 | `MARGIN_BUY_INTENSITY` | margin_detail |
| 219 | `MARGIN_BUY_RATIO` | margin_detail |
| 220 | `MARGIN_CALL_CASCADE_RISK` | margin + daily |
| 221 | `MARGIN_CROWDING_RISK` | margin_detail + daily_basic |
| 222 | `MARGIN_MOMENTUM` | margin_detail |
| 223 | `NB_FLOW` | moneyflow_hsgt |
| 224 | `NORTHBOUND_INTRADAY_MOMENTUM` | moneyflow_hsgt(日频净流入) |
| 225 | `NORTHBOUND_PREMIUM_DIVERGENCE` | hk_hold + daily |
| 226 | `NORTHBOUND_REVERSAL_SIGNAL` | moneyflow_hsgt |
| 227 | `NORTHBOUND_STOCK_CONCENTRATION` | hk_hold |
| 228 | `OVERHANG_RELEASE_SCORE` | stk_holdertrade |
| 229 | `POST_LOCKUP_SELLING_WAVE` | stk_holdertrade |
| 230 | `INSIDER_NET_SELLING_PRESSURE` | stk_holdertrade |
| 231 | `RETAIL_VS_INSTITUTIONAL_FLOW` | moneyflow(大单/小单) |
| 232 | `SECTOR_ETF_FLOW_DIVERGENCE` | ths_daily + moneyflow |
| 233 | `SHAREHOLDER_CONCENTRATION_CHANGE` | stk_holdernumber |
| 234 | `SHAREHOLDER_CONCENTRATION` | stk_holdernumber |
| 235 | `SHORT_SELLING_PRESSURE` | margin_detail(融券) |
| 236 | `SHORT_UTIL_RATE` | margin_detail |
| 237 | `SMART_MONEY_VS_RETAIL_FLOW` | moneyflow(超大单vs小单) |
| 238 | `SUPER_LARGE_ORDER_RATIO` | moneyflow(超大单占比) |
| 239 | `TOP_TRADER_REPEAT_APPEARANCE` | top_list(游资重复出现) |
| 240 | `MAIN_FORCE_CONTROL_DEGREE` | moneyflow + stk_holdernumber |
| 241 | `FUND_HOLDING_CHG` | hk_hold(北向近似) |
| 242 | `AH_PREMIUM` | Tushare(A+H对照) |
| 243 | `CNY_EQUITY_LINK` | index_global(美元指数)+shibor |
| 244 | `COMMODITY_STOCK_LINKAGE` | index_global(商品指数) |
| 245 | `INDEX_FUTURES_BASIS_SIGNAL` | Tushare ft_mins接口 |
| 246 | `LEVERAGED_ETF_REBALANCE_EFFECT` | daily(ETF净值) |
| 247 | `SEAL_TIME_DISTRIBUTION` | limit_list_d(涨停首次/最终时间) |
| 248 | `VIX_A_SHARE_TRANSMISSION` | index_global(CBOE VIX) |
| 249 | `USD_CNY_EQUITY_SIGNAL` | index_global+shibor |
| 250 | `SHAREHOLDER_MEETING_SIGNAL` | suspend_d/公告 |
| 251 | `QUARTERLY_REPORT_WINDOW` | 财报发布日历 |
| 252 | `POLICY_MEETING_WINDOW` | 公开日历(两会/经济会议) |

---

## ⚠️ 需额外对接 (92个)

### D. Tushare Pro有接口但你还没拉取/对接

| # | 因子代码 | 需要接口 | 难度 |
|---|----------|----------|------|
| 253 | `ACCRUAL_ANOMALY` | fina_indicator(应计利润) | 低 |
| 254 | `ANALYST_DISP` | stk_surv(已有)+report_rc | 低 |
| 255 | `ANALYST_REV_TIMING` | report_rc(分析师报告明细) | 中 |
| 256 | `BENEISH_M` | income+balancesheet+cashflow | 低 |
| 257 | `BUYBACK_SIGNAL` | repurchase接口 | 低 |
| 258 | `CARBON_INTENSITY` | 无直接接口,需ESG数据商 | 高 |
| 259 | `CHINA_ZSCORE` | fina_indicator | 低 |
| 260 | `COVERAGE_INIT` | report_rc(首次覆盖) | 中 |
| 261 | `CREDIT_IMPULSE` | macro_cn(社融数据) | 中 |
| 262 | `CREDIT_SPREAD_CHG` | bond_blk(债券利差) | 中 |
| 263 | `CUSTOMER_MOM` | 年报前5大客户(手动) | 高 |
| 264 | `DOWNWARD_REVISION_PROB` | stk_surv变化 | 低 |
| 265 | `EARN_CAL_DRIFT` | disclosure_date | 低 |
| 266 | `EARN_REV_MOM` | stk_surv(已有) | 低 |
| 267 | `EARNINGS_MOMENTUM_PERSISTENCE` | fina_indicator | 低 |
| 268 | `EARNINGS_QUALITY` | fina_indicator+cashflow | 低 |
| 269 | `ERP_YIELD_GAP` | index_dailybasic(PE)+shibor | 低 |
| 270 | `ESG_GOVERNANCE` | 需ESG评级数据 | 高 |
| 271 | `ESG_MOM` | 需ESG评级数据 | 高 |
| 272 | `ESG_SCORE` | 需ESG评级数据 | 高 |
| 273 | `ETF_FLOW` | fund_nav+fund_share | 中 |
| 274 | `ETF_PREMIUM_DISCOUNT` | fund_nav vs 市价 | 中 |
| 275 | `ETF_PREMIUM` | fund_nav | 中 |
| 276 | `ETF_SHARE_CHANGE_SIGNAL` | fund_share(份额变化) | 中 |
| 277 | `FACMOM` | 因子收益序列(自行计算) | 低 |
| 278 | `FACVAL` | 因子估值利差(自行计算) | 低 |
| 279 | `FM_ALPHA` | fina_indicator+截面回归 | 中 |
| 280 | `FORCED_REDEMPTION_PRESSURE` | fund_nav(基金赎回) | 中 |
| 281 | `FUND_CROWD_RISK` | fund_portfolio(季报) | 中 |
| 282 | `FUND_HERDING` | fund_portfolio(季报) | 中 |
| 283 | `FUNDMOM` | fund_portfolio(季报) | 中 |
| 284 | `FUTURES_OPEN_INTEREST_CHANGE` | ft_daily(持仓量) | 低 |
| 285 | `FUTURES_SPOT_LEAD_LAG` | ft_daily+daily | 低 |
| 286 | `GEOGRAPHIC_PEER` | stock_basic(注册地) | 低 |
| 287 | `GREEN_BOND_ISSUER` | 需绿色债券数据 | 高 |
| 288 | `ICM` | fina_indicator | 低 |
| 289 | `INDEX_FRONT_RUN` | index_weight+调整公告 | 中 |
| 290 | `INDEX_REBAL` | index_weight变化 | 中 |
| 291 | `INSIDER_SIGNAL` | stk_holdertrade(已有) | 低 |
| 292 | `IO_TABLE_FACTOR` | 国家统计局(免费但处理复杂) | 高 |
| 293 | `MACRO_SURPRISE` | macro_cn(宏观数据) | 中 |
| 294 | `MA_ANNOUNCEMENT` | Tushare ma接口(并购) | 中 |
| 295 | `MA_ANNOUNCEMENT_SURPRISE` | Tushare ma接口 | 中 |
| 296 | `M1M2_SPREAD` | macro_cn(货币供应) | 低 |
| 297 | `MARGIN_CRISI` | margin+macro(系统风险) | 中 |
| 298 | `OVERNIGHT_CATALYST_SCORE` | news接口(新闻)+公告 | 中 |
| 299 | `OVERNIGHT_EXPECTATION_GAP` | news+stk_auction_o | 中 |
| 300 | `PASSIVE_OWN` | fund_portfolio(被动基金) | 中 |
| 301 | `PCR_SENTIMENT` | opt_daily(期权P/C比) | 低 |
| 302 | `PEAD` | stk_surv + fina实际值 | 低 |
| 303 | `PRIVATE_PLACEMENT_EDGE` | Tushare share_float | 中 |
| 304 | `PRODUCT_LAUNCH_CATALYST` | 公告/新闻 | 高 |
| 305 | `REAL_EM` | fina_indicator(详细财报) | 中 |
| 306 | `REDEMPTION_COUNTDOWN_ARB` | cb_basic(可转债) | 低 |
| 307 | `REGULATORY_WINDOW_ESCAPE_DAYS` | 公告(监管函) | 中 |
| 308 | `REV_BREADTH` | stk_surv(已有) | 低 |
| 309 | `SMART_MONEY` | fund_portfolio(季报) | 中 |
| 310 | `BEST_IDEAS` | fund_portfolio(重仓) | 中 |
| 311 | `SUPPLIER_CONTAGION` | 年报供应商(手动) | 高 |
| 312 | `SUSPENSION_RISK_ADJUSTED_EDGE` | suspend_d(已有) | 低 |
| 313 | `TECH_SPILLOVER` | 专利数据(CNIPA) | 高 |
| 314 | `TP_IMPLIED_RET` | stk_surv(目标价) | 低 |
| 315 | `VOL_TIMING` | index_dailybasic(波动率) | 低 |
| 316 | `VRP_PROXY` | opt_daily(期权隐含波动) | 中 |
| 317 | `BOND_EQUITY_ROTATION` | 国债收益率+PE | 低 |
| 318 | `COMMODITY_BETA` | index_global+daily | 低 |
| 319 | `COMMODITY_SPILLOVER` | index_global | 低 |
| 320 | `BASIS_MOMENTUM_DIRECTION` | ft_daily(期货基差) | 低 |
| 321 | `CLAUSE_GAME_SCORE` | cb_basic(转债条款) | 中 |
| 322 | `CATALYST_DENSITY_SCORE` | 公告日历汇总 | 中 |
| 323 | `EVENT_CLUSTERING_EFFECT` | 公告日历 | 中 |
| 324 | `BREAKING_NEWS_SECTOR_CONTAGION` | news接口 | 中 |
| 325 | `POLICY_SURPRISE_IMPACT` | macro_cn | 中 |
| 326 | `OVERNIGHT_HOLD_DECISION` | 复合信号(可算) | 低 |
| 327 | `OVERNIGHT_SENTIMENT_PREMIUM_ADJUST` | stk_auction_o+news | 中 |
| 328 | `PRE_MARKET_SENTIMENT_SHIFT` | stk_auction_o | 低 |
| 329 | `FACTOR_REGIME_ADAPTATION` | 因子收益序列 | 低 |
| 330 | `FACTOR_TIMING_OVERLAY` | 因子收益序列 | 低 |
| 331 | `FACTOR_WEIGHTED_PORT` | 因子收益序列 | 低 |
| 332 | `INSTITUTIONAL_VS_RETAIL_CHIPS` | moneyflow+stk_holdernumber | 低 |
| 333 | `HOLDING_PERIOD_OPTIMIZATION` | 回测计算 | 低 |
| 334 | `HOLDING_PERIOD_REGIME` | 回测计算 | 低 |
| 335 | `TC_OPTIMIZE` | 交易成本模型 | 低 |
| 336 | `BW_SENT_CN` | 多维度合成(部分有) | 中 |
| 337 | `RETAIL_SENTIMENT` | moneyflow(小单)+ths_hot | 低 |
| 338 | `SMALL_TRADE` | moneyflow(小单占比) | 低 |
| 339 | `FORUM_MENTION_HEAT` | 需爬虫(东方财富股吧) | 中 |
| 340 | `BAIDU_ATTENTION` | 百度指数API | 中 |
| 341 | `ASVI` | 百度指数/搜索量 | 中 |
| 342 | `RETAIL_CAPITULATION_SIGNAL` | moneyflow+日频 | 低 |
| 343 | `RETAIL_FOMO_INDEX` | 成交量+涨停+新开户(无) | 中 |
| 344 | `DISPOSITION_EFFECT_DETECTOR` | moneyflow+price pattern | 低 |

### E. 需手动数据整理或外部爬虫

| # | 因子代码 | 数据来源 | 难度 |
|---|----------|----------|------|
| — | `CUSTOMER_MOM` | 年报前5大客户文本提取 | 高 |
| — | `SUPPLIER_CONTAGION` | 年报前5大供应商 | 高 |
| — | `IO_TABLE_FACTOR` | 国家统计局投入产出表 | 高 |
| — | `TECH_SPILLOVER` | CNIPA专利引用网络 | 高 |
| — | `FORUM_MENTION_HEAT` | 东方财富股吧爬虫 | 中 |
| — | `BAIDU_ATTENTION` | 百度指数API | 中 |

---

## ❌ 取不到 (44个)

### F. 需要Level-2数据 (付费, ~数万/年)

| # | 因子代码 | 需要数据 |
|---|----------|----------|
| 345 | `ALGO_ORDER_DETECTION` | L2逐笔委托 |
| 346 | `ANTI_ALGO_TIMING` | L2逐笔委托 |
| 347 | `BID_ASK_DEPTH_IMBALANCE` | L2五档盘口 |
| 348 | `BID_RESILIENCE_SCORE` | L2五档实时 |
| 349 | `HIDDEN_ORDER_DETECTION` | L2逐笔委托 |
| 350 | `KYLE_LAMBDA` | L2逐笔成交 |
| 351 | `LARGE_PENDING_ORDER_SIGNAL` | L2五档挂单 |
| 352 | `MLOFI` | L2多档订单簿 |
| 353 | `ORDER_BOOK_SLOPE` | L2五档盘口 |
| 354 | `PIN` | L2逐笔(买卖方向) |
| 355 | `PRICE_IMPACT_PER_TRADE` | L2逐笔成交 |
| 356 | `QUEUE_POSITION_VALUE` | L2委托队列 |
| 357 | `SEAL_REPLENISHMENT_SPEED` | L2涨停封单变化 |
| 358 | `SPREAD_DECOMP` | L2五档(价差分解) |
| 359 | `SPREAD_VOLATILITY_REGIME` | L2五档 |
| 360 | `STEALTH` | L2逐笔(隐蔽交易) |
| 361 | `TICK_IMBALANCE_BAR_SIGNAL` | L2逐笔 |
| 362 | `TICK_REVERSAL_FREQUENCY` | L2逐笔 |
| 363 | `TRADE_ARRIVAL_RATE_REGIME` | L2逐笔 |
| 364 | `TUG_OF_WAR_INTENSITY` | L2五档+逐笔 |
| 365 | `VPIN` | L2逐笔(精确版VPIN) |
| 366 | `WASH_TRADING_DETECTOR` | L2逐笔委托 |
| 367 | `QUANT_FOOTPRINT` | L2逐笔(算法单识别) |
| 368 | `ORDER_SPLITTING_EFFICIENCY` | L2逐笔委托 |
| 369 | `MARKET_IMPACT_MINIMIZATION` | L2逐笔成交 |

### G. 需要另类数据 (卫星/APP/电力等, 极昂贵或不公开)

| # | 因子代码 | 需要数据 |
|---|----------|----------|
| 370 | `APP_ENGAGEMENT` | APP活跃度(极光/QuestMobile) |
| 371 | `ELECTRICITY_NOWCAST` | 电力数据(国网内部) |
| 372 | `PORT_SATELLITE` | 卫星遥感(数据商) |
| 373 | `TIR_FACTORY` | 工厂热红外(卫星) |

### H. 需要付费终端(Wind/iFinD)或特殊渠道

| # | 因子代码 | 需要数据 |
|---|----------|----------|
| 374 | `ESG_SCORE` | Wind ESG评级 |
| 375 | `ESG_MOM` | Wind ESG评级 |
| 376 | `ESG_GOVERNANCE` | Wind ESG评级 |
| 377 | `GREEN_BOND_ISSUER` | Wind绿色债券 |
| 378 | `CARBON_INTENSITY` | 碳排放数据 |
| 379 | `NEWS_SENTIMENT_REVERSAL` | NLP+新闻全文(付费) |
| 380 | `INTRADAY_NEWS_IMPACT_SPEED` | 实时新闻流+L2 |
| 381 | `EVENING_RUMOR_CREDIBILITY` | 社交媒体实时流 |
| 382 | `BIG_V_CONSENSUS_SIGNAL` | 社交媒体大V(需爬虫) |
| 383 | `SENTIMENT_POLARITY_SHIFT` | NLP情感分析(需全文) |
| 384 | `RUMOR_VS_OFFICIAL_NEWS` | 新闻分类系统 |

---

## 🔧 纯逻辑/模型/策略框架 (36个, 不需额外数据)

这些因子是**策略逻辑/仓位管理/执行框架**, 本身不需要新数据, 用已有因子即可实现:

| # | 因子代码 | 性质 |
|---|----------|------|
| 385 | `AE_LATENT` | 自编码器模型(输入已有因子) |
| 386 | `ALM` | Attention模型框架 |
| 387 | `ANCHORING_BIAS_LEVEL` | 心理偏差检测逻辑 |
| 388 | `CYCLE_STAGE_STRATEGY_SELECTOR` | 策略选择逻辑 |
| 389 | `DAILY_REVIEW_SCORE` | 复盘评分体系 |
| 390 | `DAILY_TRADE_EXPECTANCY` | 期望值计算 |
| 391 | `DISCIPLINE_SCORE_REALTIME` | 纪律评分 |
| 392 | `DRAWDOWN_POSITION_SCALE` | 仓位管理逻辑 |
| 393 | `DYNAMIC_STOP_LOSS_LEVEL` | 止损逻辑 |
| 394 | `EDGE_DECAY_MONITOR` | alpha衰减监控 |
| 395 | `EMOTIONAL_OVERRIDE_DETECTOR` | 情绪控制检测 |
| 396 | `EQUITY_CURVE_STATE` | 权益曲线判断 |
| 397 | `EXECUTION_SLIPPAGE_BURDEN` | 滑点计算 |
| 398 | `EXIT_PRIORITY_RANKING` | 卖出优先级 |
| 399 | `GBDT_COMP` | GBDT模型(输入已有因子) |
| 400 | `KELLY_FRACTION_ADAPTIVE` | 凯利公式仓位 |
| 401 | `LOSS_AVERSION_THRESHOLD` | 损失厌恶阈值 |
| 402 | `MISTAKE_PATTERN_TRACKER` | 错误模式追踪 |
| 403 | `OVERCONFIDENCE_SIGNAL` | 过度自信检测 |
| 404 | `PORTFOLIO_HEAT_SCORE` | 组合热度 |
| 405 | `POSITION_THEME_CONCENTRATION` | 持仓集中度 |
| 406 | `RECOVERY_BUFFER_DAYS` | 恢复缓冲期 |
| 407 | `RISK_PER_TRADE_CAP` | 单笔风险上限 |
| 408 | `RULE_BASED_POSITION_SIZING` | 规则化仓位 |
| 409 | `RULE_VIOLATION_COST` | 违规成本 |
| 410 | `SELF_ITERATION_VELOCITY` | 迭代速度评估 |
| 411 | `SIGNAL_CONFLUENCE_COUNT` | 信号汇聚计数 |
| 412 | `SIGNAL_EXECUTION_CONSISTENCY` | 执行一致性 |
| 413 | `SIGNAL_TYPE_PNL_ATTRIBUTION` | 归因分析 |
| 414 | `SLIPPAGE_COST_AWARENESS` | 滑点意识 |
| 415 | `T1_SELLING_WINDOW` | T+1卖出窗口 |
| 416 | `TIME_STOP_URGENCY` | 时间止损 |
| 417 | `TRADE_CHECKLIST_SCORE` | 交易清单评分 |
| 418 | `TRADE_FREQUENCY_EFFICIENCY` | 交易频率效率 |
| 419 | `TRADE_PNL_SKEWNESS` | 盈亏偏度 |
| 420 | `TRAILING_STOP_ACTIVATION` | 移动止损逻辑 |
| 421 | `TSFM` | Transformer模型 |
| 422 | `WIN_STREAK_FRAGILITY` | 连胜脆弱性 |
| 423 | `PURE_ALPHA_ISOLATION` | Alpha分离模型 |
| 424 | `ICM` | 条件因子模型 |

---

## 汇总统计

| 分类 | 数量 | 占比 |
|------|------|------|
| ✅ 能算 (日频+5min+已缓存Tushare) | **252** | **59.4%** |
| ⚠️ 需额外对接 (Tushare Pro有/需爬虫/需手动) | **92** | **21.7%** |
| ❌ 取不到 (L2/另类数据/付费终端) | **44** | **10.4%** |
| 🔧 纯逻辑/模型 (不需新数据) | **36** | **8.5%** |
| **合计** | **424** | **100%** |

---

## 实操建议

### 第一优先级: 立即可用 (252个✅ + 36个🔧 = 288个)

你当前数据即可计算的288个因子, 其中**最高价值**的:
1. 涨停板系列: `LIMIT_UP_NEXT_DAY_PREMIUM_PREDICT`, `SEAL_TIME_DISTRIBUTION`, `BOARD_QUALITY_COMPOSITE`, `LIMIT_PREMIUM_REGIME`
2. 5min降频: `RSKEW`, `VPIN_DAILY`, `LAST30_MOM`, `FIRST_HALFHOUR_MOMENTUM`, `INTRADAY_REVERSAL`
3. 情绪周期: `MARKET_EMOTION_CYCLE_PHASE`, `FREEZING_POINT_COMPOSITE`(已实现)
4. 资金流: `MAIN_FORCE_NET_INFLOW_INTENSITY`, `SUPER_LARGE_ORDER_RATIO`, `SMART_MONEY_VS_RETAIL_FLOW`
5. 两融: `MARGIN_BUY_INTENSITY`, `SHORT_SELLING_PRESSURE`, `MARGIN_CROWDING_RISK`

### 第二优先级: 低成本对接 (标注"低"难度的⚠️, ~40个)

已有`stk_surv`可做: `EARN_REV_MOM`, `REV_BREADTH`, `TP_IMPLIED_RET`, `PEAD`
加拉`fina_indicator`: `BENEISH_M`, `ACCRUAL_ANOMALY`, `EARNINGS_QUALITY`, `CHINA_ZSCORE`
加拉`fund_portfolio`: `FUND_HOLDING_CHG`, `BEST_IDEAS`, `FUND_HERDING`

### 永远跳过 (❌ 中的L2和另类数据, 44个)

除非你购买L2数据或另类数据商服务, 否则这44个因子无法实现。但注意:
- `VPIN_DAILY`(✅)是`VPIN`(❌)的免费近似版, 用5min K线+BVC方法
- `SEAL_DEPTH_RATIO`(✅)是封单强度的日频近似, 精确版需L2

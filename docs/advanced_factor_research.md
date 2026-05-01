# Advanced Factor Research: A-Share Market
## ESG/Green Finance, Fund Holdings, Analyst Advanced, Financial Quality

---

## 1. ESG/绿色金融因子 (ESG & Green Finance Factors)

### 1.1 ESG综合评分因子 (ESG Composite Score Factor)

| Item | Detail |
|------|--------|
| **Factor Name** | ESG Score / ESG综合评分 |
| **Formula** | `ESG_Score = weighted(E_pillar, S_pillar, G_pillar)` where weights vary by industry; typically E=30-40%, S=20-30%, G=30-40% |
| **Data Sources** | 华证ESG (SynTao/CASVI), Wind ESG, MSCI China ESG, 商道融绿 |
| **IC (Monthly)** | 2-4% (weak but positive); ICIR ~ 0.2-0.4 |
| **Key Findings** | ESG factor in China shows weaker predictability than in developed markets. Positive alpha mainly comes from Governance pillar. E-score effective post-2020 with carbon neutrality policy push. |
| **References** | - Feng, Chen & Tang (2023) "ESG Rating and Stock Returns: Evidence from China" *Pacific-Basin Finance Journal*<br>- 华泰证券 (2022) "ESG投资:从理念到量化实践" 金工研报<br>- Li & Polychronopoulos (2020) "What a Difference an ESG Ratings Provider Makes!" *Research Affiliates* |

**Notes for A-share implementation:**
- 华证ESG has broadest A-share coverage (~4000+ stocks)
- Monthly rebalance; ESG scores update quarterly
- Better as negative screen (avoid bottom quintile) than positive selection
- IC improves significantly when combined with quality/momentum factors

### 1.2 ESG评级变动因子 (ESG Rating Change/Momentum)

| Item | Detail |
|------|--------|
| **Factor Name** | ESG Rating Change / ESG评级变动 |
| **Formula** | `ESG_Change = ESG_Score(t) - ESG_Score(t-1)` or `ESG_Upgrade = 1 if rating_upgraded, 0 otherwise` |
| **IC (Monthly)** | 3-5% (stronger than level); ICIR ~ 0.3-0.5 |
| **Key Findings** | ESG upgrades predict positive returns over 3-6 months. The "ESG momentum" effect is more robust than ESG level. |
| **References** | - Nagy et al. (2016) "Can ESG Add Alpha?" *Journal of Investing*<br>- 中信证券 (2021) "ESG评级调整的alpha效应" 研报 |

### 1.3 碳交易敞口因子 (Carbon Exposure Factor)

| Item | Detail |
|------|--------|
| **Factor Name** | Carbon Intensity / 碳排放强度 |
| **Formula** | `Carbon_Intensity = Total_CO2_Emissions / Revenue` <br> `Carbon_Risk = Industry_Avg_Carbon - Firm_Carbon` (lower is better) |
| **IC (Monthly)** | 1-3% (emerging, unstable); stronger in high-carbon industries |
| **Key Findings** | Since China ETS launch (2021), high-carbon firms in covered sectors (power, steel, cement) show relative underperformance. Carbon-efficient firms within high-carbon industries earn 2-4% annual premium. |
| **References** | - Bolton & Kacperczyk (2021) "Do Investors Care about Carbon Risk?" *Journal of Financial Economics*<br>- 国盛证券 (2022) "碳中和背景下的绿色投资因子" 研报<br>- Zhang & Wang (2022) "Carbon Trading and Firm Value in China" *China Journal of Accounting Research* |

### 1.4 绿色债券溢价因子 (Green Bond Premium)

| Item | Detail |
|------|--------|
| **Factor Name** | Green Bond Issuer Premium / 绿债发行人溢价 |
| **Formula** | `Green_Premium = Stock_of_Green_Bond_Issuer - Matched_Non_Green_Issuer` |
| **IC (Monthly)** | ~2-3% for equity; bond greenium ~-5 to -15bps (yield discount) |
| **Key Findings** | Green bond issuers in China show slight equity premium, mainly through signaling channel. Greenium (yield discount) for green bonds is approximately 5-15bps in China. |
| **References** | - Flammer (2021) "Corporate Green Bonds" *Journal of Financial Economics*<br>- 中金公司 (2022) "中国绿色债券市场与绿色溢价研究" |

---

## 2. 基金持仓因子 (Mutual Fund Holdings Factors)

### 2.1 基金持仓集中度/重仓因子 (Fund Holding Concentration)

| Item | Detail |
|------|--------|
| **Factor Name** | Fund Ownership Ratio / 基金持股比例 |
| **Formula** | `Fund_Ownership = Sum(Fund_Holdings_Shares_i) / Total_Shares_Outstanding` |
| **IC (Monthly)** | 3-6%; ICIR ~ 0.3-0.6 |
| **Key Findings** | Stocks heavily held by mutual funds tend to outperform in momentum regimes but suffer crowding risk in drawdowns. Positive IC mainly during 2017-2021 "core asset" era, weakened post-2022. |
| **References** | - Yan & Zhang (2009) "Institutional Investors and Equity Returns" *Review of Financial Studies*<br>- 广发证券 (2020) "公募基金持仓因子的alpha来源" 研报<br>- 天风证券 (2021) "基金重仓股效应与拥挤度测度" |

### 2.2 基金持仓变动因子 (Fund Holding Change)

| Item | Detail |
|------|--------|
| **Factor Name** | Fund Holding Change / 基金增持比例 |
| **Formula** | `Fund_Change = Fund_Ownership(Q) - Fund_Ownership(Q-1)` <br> or `Fund_Change_Pct = [Fund_Ownership(Q) - Fund_Ownership(Q-1)] / Fund_Ownership(Q-1)` |
| **IC (Monthly)** | 4-7%; ICIR ~ 0.4-0.7 (one of the stronger fundamental factors) |
| **Key Findings** | Quarter-over-quarter increase in fund holdings is a strong predictor. Lag effect: holdings disclosed with 1-quarter delay, but signal persists 2-3 months post-disclosure. |
| **References** | - Chen, Jegadeesh & Wermers (2000) "The Value of Active Mutual Fund Management" *Journal of Financial and Quantitative Analysis*<br>- 华泰证券 (2019) "基金持仓变动因子的多维度挖掘" |

### 2.3 基金羊群效应因子 (Fund Herding Factor)

| Item | Detail |
|------|--------|
| **Factor Name** | Fund Herding Measure / 基金羊群效应 |
| **Formula** | `LSV_Herding = |p(i,t) - p(t)| - E|p(i,t) - p(t)|` <br> where `p(i,t) = Buyers(i,t) / [Buyers(i,t) + Sellers(i,t)]`, `p(t) = avg fraction of buyers` <br> (Lakonishok, Shleifer & Vishny 1992) |
| **IC (Monthly)** | Buy-herding: 3-5% (positive); Sell-herding: -4 to -6% (negative predictive) |
| **Key Findings** | Buy-side herding predicts short-term positive returns (1-3 months) followed by reversal. Sell-side herding predicts continued negative returns. In China, herding is more pronounced than in US markets due to retail-dominated trading. |
| **References** | - Lakonishok, Shleifer & Vishny (1992) "The Impact of Institutional Trading on Stock Prices" *Journal of Financial Economics*<br>- Jiang & Verardo (2018) "Does Herding Behavior Reveal Skill?" *Journal of Finance*<br>- 伍旭川, 何鹏 (2005) "中国开放式基金羊群行为分析" *金融研究* |

### 2.4 聪明钱因子 (Smart Money Factor)

| Item | Detail |
|------|--------|
| **Factor Name** | Smart Money / Net Fund Flow Direction / 聪明资金 |
| **Formula** | `Smart_Money = Fund_Flow_Institutional - Fund_Flow_Retail` <br> Alternative: `SM = Σ(Fund_Return_Past * Fund_Position_Change)` (skill-weighted flow) |
| **IC (Monthly)** | 3-5%; more effective as a timing/regime indicator |
| **Key Findings** | Institutional fund inflows tend to predict positive returns (smart money), while retail fund inflows predict negative returns (dumb money). The spread is approximately 6-10% annualized in A-shares. North-bound (陆股通/沪深港通) flow is a particularly strong smart money signal. |
| **References** | - Frazzini & Lamont (2008) "Dumb Money: Mutual Fund Flows and the Cross-Section of Stock Returns" *Journal of Financial Economics*<br>- Gruber (1996) "Another Puzzle: The Growth in Actively Managed Mutual Funds" *Journal of Finance*<br>- 海通证券 (2020) "北向资金择股能力与聪明钱效应" |

### 2.5 基金经理信心因子 (Fund Manager Conviction)

| Item | Detail |
|------|--------|
| **Factor Name** | Fund Conviction / 基金经理集中持仓信心度 |
| **Formula** | `Conviction = Σ(Weight_in_Portfolio_i * I(Weight > Benchmark_Weight * 2))` <br> or `Best_Ideas = Top_5_Holdings_Weight / Total_Holdings` |
| **IC (Monthly)** | 4-6% for "best ideas" stocks; ICIR ~ 0.4-0.5 |
| **Key Findings** | Stocks where multiple high-performing fund managers make concentrated bets (top holdings) significantly outperform their other holdings. The "best ideas" approach (Cohen, Polk & Silli 2010) works in A-shares, yielding 8-12% annual alpha. |
| **References** | - Cohen, Polk & Silli (2010) "Best Ideas" Working Paper (published 2021 in *Management Science*)<br>- 申万宏源 (2021) "明星基金经理的Best Ideas策略" 研报 |

---

## 3. 分析师因子进阶 (Advanced Analyst Factors)

### 3.1 盈利预测调整动量 (Earnings Revision Momentum)

| Item | Detail |
|------|--------|
| **Factor Name** | Earnings Revision Momentum / 盈利预测调整动量 / FY1变动 |
| **Formula** | `Rev_Mom = [EPS_Forecast_FY1(t) - EPS_Forecast_FY1(t-30d)] / |EPS_Forecast_FY1(t-30d)|` <br> or `Rev_Mom = [Consensus_EPS(t) - Consensus_EPS(t-1month)] / Price` |
| **IC (Monthly)** | 5-8%; ICIR ~ 0.5-0.8 (one of the highest IC factors in A-shares) |
| **Key Findings** | Earnings revision is among the most powerful single factors in A-shares. Upward revisions predict continued positive returns for 1-3 months. Works best in mid-cap universe. Suffers during "estimate cuts" regime (bear markets). |
| **References** | - Givoly & Lakonishok (1979) "The Information Content of Financial Analysts' Forecasts" *Journal of Accounting and Economics*<br>- Chan, Jegadeesh & Lakonishok (1996) "Momentum Strategies" *Journal of Finance*<br>- 国泰君安 (2018) "一致预期因子深度研究:盈利调整的alpha" |

### 3.2 盈利预测调整宽度 (Earnings Revision Breadth)

| Item | Detail |
|------|--------|
| **Factor Name** | Revision Breadth / 调整宽度 |
| **Formula** | `Breadth = (N_Up - N_Down) / (N_Up + N_Down + N_Unchanged)` <br> where N_Up = analysts revising up, N_Down = analysts revising down |
| **IC (Monthly)** | 4-7%; ICIR ~ 0.4-0.6 |
| **Key Findings** | Breadth is more stable than magnitude-based revision. When >70% of analysts revise in same direction, next-month return predictability is very high. Combined with magnitude gives IC ~ 8-10%. |
| **References** | - Barber, Lehavy, McNichols & Trueman (2001) "Can Investors Profit from the Prophets?" *Journal of Finance*<br>- 华泰证券 (2020) "分析师预期修正的多维度因子构建" |

### 3.3 分析师分歧度因子 (Analyst Disagreement / Forecast Dispersion)

| Item | Detail |
|------|--------|
| **Factor Name** | Forecast Dispersion / 分析师分歧度 |
| **Formula** | `Dispersion = Std(EPS_Forecasts_All_Analysts) / |Mean(EPS_Forecasts)|` <br> (coefficient of variation of analyst EPS estimates) |
| **IC (Monthly)** | -3 to -5% (negative: high dispersion predicts underperformance); ICIR ~ -0.3 to -0.5 |
| **Key Findings** | High analyst disagreement predicts lower future returns (Diether et al. 2002). In A-shares, the effect is stronger due to short-selling constraints (hard to arbitrage overvalued stocks). Monthly long-short spread ~ 1-2%. |
| **References** | - Diether, Malloy & Scherbina (2002) "Differences of Opinion and the Cross Section of Stock Returns" *Journal of Finance*<br>- Johnson (2004) "Forecast Dispersion and the Cross Section of Expected Returns" *Journal of Finance*<br>- 中信建投 (2019) "分析师分歧度因子在A股的有效性" |

### 3.4 目标价隐含收益率 (Target Price Implied Return)

| Item | Detail |
|------|--------|
| **Factor Name** | Target Price Implied Return / 目标价隐含收益率 |
| **Formula** | `TP_Return = (Consensus_Target_Price - Current_Price) / Current_Price` |
| **IC (Monthly)** | 3-5%; ICIR ~ 0.3-0.4 |
| **Key Findings** | Moderate predictive power. Works better when filtered by analyst quality (star analysts). Chinese analysts tend to set over-optimistic targets, so the factor works better as a relative ranking within sectors rather than absolute signal. |
| **References** | - Brav & Lehavy (2003) "An Empirical Analysis of Analysts' Target Prices" *Journal of Finance*<br>- 光大证券 (2020) "分析师目标价因子的构建与优化" |

### 3.5 首次覆盖效应 (Analyst Coverage Initiation)

| Item | Detail |
|------|--------|
| **Factor Name** | Coverage Initiation / 分析师首次覆盖 |
| **Formula** | `Initiation = 1 if first_analyst_report_in_6months, 0 otherwise` <br> `Initiation_Count = Number_of_new_analysts_covering_in_past_month` |
| **IC (Event-based)** | CAR(0,+30) ~ +3 to +5% for newly covered stocks |
| **Key Findings** | Analyst initiation creates an information event. In A-shares, previously uncovered stocks that gain first coverage show significant positive drift. Small/mid-cap universe benefits most. |
| **References** | - Irvine (2003) "The Incremental Impact of Analyst Initiation of Coverage" *Journal of Accounting and Economics*<br>- 招商证券 (2019) "分析师首次覆盖的事件驱动策略" |

---

## 4. 财务质量/操纵因子 (Financial Quality & Manipulation Factors)

### 4.1 Beneish M-Score (中国A股版)

| Item | Detail |
|------|--------|
| **Factor Name** | Beneish M-Score / 财务操纵概率 |
| **Formula** | `M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI` <br><br> Where: DSRI=Days Sales Receivable Index, GMI=Gross Margin Index, AQI=Asset Quality Index, SGI=Sales Growth Index, DEPI=Depreciation Index, SGAI=SGA Index, TATA=Total Accruals to Total Assets, LVGI=Leverage Index <br><br> **If M > -1.78, likely manipulator** |
| **IC (Monthly)** | -2 to -4% (negative: high M-score predicts negative returns); more powerful as risk screen |
| **Key Findings** | Works in A-shares but requires parameter recalibration for Chinese accounting standards. High M-score firms (potential manipulators) underperform by 8-15% annually. Best used as negative screen rather than standalone factor. Post-2019 new securities law increased detection sensitivity. |
| **References** | - Beneish (1999) "The Detection of Earnings Manipulation" *Financial Analysts Journal*<br>- 陈信元, 夏立军 (2006) "审计任期与审计质量" *会计研究* (China recalibration)<br>- 兴业证券 (2020) "财务异常因子:基于Beneish模型的A股实证" |

**China-specific calibration notes:**
- TATA coefficient should be increased (accrual manipulation more common in A-shares)
- Add related-party transaction variable for better fit
- Threshold adjusted to M > -1.49 for China (lower bar due to higher manipulation frequency)

### 4.2 应计异象因子 (Accrual Anomaly Factor)

| Item | Detail |
|------|--------|
| **Factor Name** | Total Accruals / 应计利润因子 |
| **Formula** | `Accruals = (ΔCA - ΔCash) - (ΔCL - ΔSTD - ΔTP) - DEP` <br> Scaled: `Accrual_Ratio = Accruals / Average_Total_Assets` <br><br> Simpler version (Balance Sheet approach): <br> `Accrual = (Net_Income - Operating_Cash_Flow) / Total_Assets` |
| **IC (Monthly)** | -3 to -5% (negative: high accruals predict lower returns); ICIR ~ -0.3 to -0.5 |
| **Key Findings** | Sloan (1996) accrual anomaly exists in A-shares but is weaker than in US. Works better in non-SOE universe. Decayed somewhat post-2015 as market became more efficient. Annual long-short ~ 6-10%. |
| **References** | - Sloan (1996) "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows?" *The Accounting Review*<br>- 李志文, 宋衍蘅 (2006) "应计项目的增量信息含量" *会计研究*<br>- 海通证券 (2017) "应计因子在A股的实证检验与改进" |

### 4.3 盈余质量因子 (Earnings Quality: Cash Flow vs Accrual)

| Item | Detail |
|------|--------|
| **Factor Name** | Earnings Quality / Cash-based Earnings / 盈余质量因子 |
| **Formula** | `EQ = Operating_Cash_Flow / Net_Income` <br> (higher = better quality, more cash-backed earnings) <br><br> Alternative (Dechow & Dichev 2002): <br> `EQ = -Std(Residuals from: WC_Accruals = a + b1*CFO(t-1) + b2*CFO(t) + b3*CFO(t+1))` |
| **IC (Monthly)** | 3-5% (positive: high earnings quality predicts positive returns); ICIR ~ 0.3-0.5 |
| **Key Findings** | Cash-backed earnings are more persistent. Firms with CFO/NI > 1 consistently outperform in A-shares. Particularly effective in identifying "cash cow" quality stocks. Works well combined with ROE/profitability factors. |
| **References** | - Dechow & Dichev (2002) "The Quality of Accruals and Earnings" *The Accounting Review*<br>- Dechow, Ge & Schrand (2010) "Understanding Earnings Quality: A Review" *Journal of Accounting and Economics*<br>- 国信证券 (2019) "盈余质量因子的构建与A股实证" |

### 4.4 财务困境预测因子 (Financial Distress - China Z-Score)

| Item | Detail |
|------|--------|
| **Factor Name** | China Z-Score / Modified Altman Z / ST预测因子 |
| **Formula** | **Original Altman (1968):** <br> `Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5` <br> X1=WC/TA, X2=RE/TA, X3=EBIT/TA, X4=MVE/TL, X5=Sales/TA <br><br> **China-modified (various papers):** <br> `Z_CN = a + b1*(NI/TA) + b2*(WC/TA) + b3*(Retained_Earnings/TA) + b4*(Cash/CurrentLiabilities) + b5*(AR_Turnover_Change)` <br><br> Cutoff: Z < 1.81 (distress zone), 1.81-2.99 (grey zone), >2.99 (safe) |
| **IC (Monthly)** | 2-4% (positive: higher Z = safer = mild outperformance); stronger as risk screen for avoiding ST stocks |
| **Key Findings** | Original Altman Z has ~65-70% accuracy for China (lower than US 80-90%). Chinese modifications incorporating cash flow ratios and related-party transactions improve accuracy to 75-85%. Mainly used to avoid ST (Special Treatment) stocks rather than as alpha factor. |
| **References** | - Altman (1968) "Financial Ratios, Discriminant Analysis, and the Prediction of Corporate Bankruptcy" *Journal of Finance*<br>- 吴世农, 卢贤义 (2001) "我国上市公司财务困境的预测模型研究" *经济研究*<br>- 张玲, 曾维火 (2004) "基于Z值模型的上市公司财务预警系统" *会计研究*<br>- Altman et al. (2007) "Financial Distress Prediction in an International Context: A Review" *Journal of International Financial Management and Accounting* |

### 4.5 真实盈余管理因子 (Real Earnings Management)

| Item | Detail |
|------|--------|
| **Factor Name** | Real Earnings Management / 真实盈余管理 |
| **Formula** | **Roychowdhury (2006) model:** <br> `Abnormal_CFO = CFO/A(t-1) - [a1/A(t-1) + b1*Sales/A(t-1) + c1*ΔSales/A(t-1)]` <br> `Abnormal_Prod = Prod/A(t-1) - [a2/A(t-1) + b2*Sales/A(t-1) + c2*ΔSales/A(t-1) + d2*ΔSales(t-1)/A(t-1)]` <br> `Abnormal_DiscExp = DiscExp/A(t-1) - [a3/A(t-1) + b3*Sales(t-1)/A(t-1)]` <br><br> `REM = -Abnormal_CFO + Abnormal_Prod - Abnormal_DiscExp` <br> (higher REM = more real manipulation) |
| **IC (Monthly)** | -2 to -3% (negative: high REM predicts negative returns); ICIR ~ -0.2 to -0.3 |
| **Key Findings** | Real earnings management is more prevalent in China post-2007 new accounting standards (which curbed accrual manipulation). High REM firms show poor subsequent returns, especially around SEO/refinancing periods. SOEs show less REM than private firms. |
| **References** | - Roychowdhury (2006) "Earnings Management through Real Activities Manipulation" *Journal of Accounting and Economics*<br>- Cohen & Zarowin (2010) "Accrual-based and Real Earnings Management around Seasoned Equity Offerings" *Journal of Accounting and Economics*<br>- 李增福, 郑友环 (2010) "真实活动操控的盈余管理研究" *南开管理评论*<br>- 方红星, 金玉娜 (2011) "高质量内部控制能抑制盈余管理吗?" *会计研究* |

---

## Summary Table: Factor IC Comparison

| Category | Factor | Monthly IC | ICIR | Direction | Stability |
|----------|--------|-----------|------|-----------|-----------|
| ESG | ESG Score Level | 2-4% | 0.2-0.4 | + | Low |
| ESG | ESG Rating Change | 3-5% | 0.3-0.5 | + | Medium |
| ESG | Carbon Intensity | 1-3% | 0.1-0.3 | - (low=good) | Low |
| Fund | Fund Ownership Level | 3-6% | 0.3-0.6 | + | Medium |
| Fund | Fund Holding Change | 4-7% | 0.4-0.7 | + | High |
| Fund | Fund Herding (Buy) | 3-5% | 0.3-0.5 | + | Medium |
| Fund | Smart Money (北向) | 3-5% | 0.3-0.5 | + | Medium |
| Fund | Manager Conviction | 4-6% | 0.4-0.5 | + | Medium |
| Analyst | Earnings Revision Mom | 5-8% | 0.5-0.8 | + | **High** |
| Analyst | Revision Breadth | 4-7% | 0.4-0.6 | + | High |
| Analyst | Forecast Dispersion | -3 to -5% | -0.3 to -0.5 | - (high=bad) | Medium |
| Analyst | Target Price Return | 3-5% | 0.3-0.4 | + | Low-Med |
| Analyst | Coverage Initiation | +3-5% CAR | N/A (event) | + | Medium |
| Quality | Beneish M-Score | -2 to -4% | -0.2 to -0.4 | - (high=bad) | Medium |
| Quality | Accruals (Sloan) | -3 to -5% | -0.3 to -0.5 | - (high=bad) | Medium |
| Quality | Earnings Quality | 3-5% | 0.3-0.5 | + | High |
| Quality | China Z-Score | 2-4% | 0.2-0.4 | + | Medium |
| Quality | Real EM (Roychowdhury) | -2 to -3% | -0.2 to -0.3 | - (high=bad) | Low-Med |

---

## Key Implementation Notes for Short-term Trading

1. **Highest IC factors for short-term**: Earnings Revision Momentum (5-8%) and Fund Holding Change (4-7%) are the strongest single factors.

2. **Data lag issues**:
   - Fund holdings: Quarterly disclosure with ~1 month lag (top 10 monthly for some)
   - ESG scores: Quarterly/annual updates
   - Analyst revisions: Real-time (Wind/iFind terminal)
   - Financial quality: Quarterly with ~1 month lag

3. **Combination recommendations**:
   - Analyst revision + Fund flow direction: complementary signals
   - Earnings quality + Low accruals: compound quality signal
   - ESG momentum + Low carbon: regime-dependent green alpha

4. **Decay and crowding**:
   - Fund holding factors most crowded (many quants use)
   - Analyst revision still relatively under-exploited in A-shares
   - Financial quality factors are slow-moving, better for monthly+ horizons
   - ESG factors still emerging, less crowded but lower IC

---

## Key Academic References (Consolidated)

### International Foundation Papers
1. Sloan (1996) - Accrual anomaly
2. Beneish (1999) - Earnings manipulation detection
3. Dechow & Dichev (2002) - Earnings quality
4. Diether, Malloy & Scherbina (2002) - Analyst disagreement
5. Roychowdhury (2006) - Real earnings management
6. Frazzini & Lamont (2008) - Dumb money effect
7. Cohen, Polk & Silli (2010/2021) - Best ideas
8. Bolton & Kacperczyk (2021) - Carbon risk pricing
9. Lakonishok, Shleifer & Vishny (1992) - Institutional herding

### China-Specific Key Papers
1. 吴世农, 卢贤义 (2001) - China financial distress prediction, 经济研究
2. 伍旭川, 何鹏 (2005) - China mutual fund herding, 金融研究
3. 李志文, 宋衍蘅 (2006) - Accrual anomaly in China, 会计研究
4. 李增福, 郑友环 (2010) - Real earnings management China, 南开管理评论
5. 方红星, 金玉娜 (2011) - Internal control and earnings management, 会计研究
6. Feng, Chen & Tang (2023) - ESG and stock returns in China, Pacific-Basin Finance Journal

### Sell-Side Research Reports (券商研报)
1. 华泰证券 - ESG投资, 基金持仓变动因子
2. 中信证券 - ESG评级调整alpha
3. 国泰君安 - 一致预期因子
4. 广发证券 - 公募基金持仓因子
5. 天风证券 - 基金重仓股拥挤度
6. 海通证券 - 北向资金聪明钱, 应计因子
7. 兴业证券 - Beneish模型A股实证
8. 国信证券 - 盈余质量因子
9. 光大证券 - 分析师目标价因子
10. 招商证券 - 分析师首次覆盖策略
11. 中信建投 - 分析师分歧度因子
12. 国盛证券 - 碳中和绿色投资因子
13. 申万宏源 - Best Ideas策略

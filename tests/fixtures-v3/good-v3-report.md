> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；机会成本=美国 10Y 国债 ×2；持仓未核验。

## First-Page Verdict

现价 $100；最新财报为 2026Q2 10-Q；最终评级 | Watchlist

## Evidence Ledger

| 数据项 | 数值 | 日期 | 来源/层级 | 单位/期间/口径 | 可信度 |
|---|---:|---|---|---|---|
| 当前价格 | $100 | 2026-08-07 | SEC/market source | USD/share, close | 高 |
| TTM FCF | $10B | 2026Q2 | SEC Tier 1 | USD, TTM | 高 |

## 1. Overview

### Key Forces

- 本次财报改变了什么：Cloud 增速加快。
- 本次财报没有改变什么：Search 仍是现金牛。

## 2. Financial Autopsy

### Reported / Adjusted / Normalized 正常化桥

Reported、Adjusted、Normalized 已分列；利润正常化与现金流正常化分开。CapEx 制度与 OCF 运行率已核对。证券分类：现金、有价证券、非上市证券、受限证券、债务和租赁负债分列。

## 3. Moat Analysis

品牌、规模和转换成本仍然存在。

## 4. Valuation and 10-year payback

EPS 与 FCF/share 双口径，EV/FCF 也已计算。股数口径：market cap 使用 point-in-time common shares，EPS/FCF/share 使用 diluted weighted-average shares。

### 估值计算与股息处理

目标回报价格由 `scripts/valuation_math.py` 计算，股息处理为名义税后累计，不计再投资。

### 名义 10 年回本测试

名义 10 年回本测试：EPS 和 FCF/share 均需继续增长。

### 贴现 10 年回本测试

| 贴现率 r | EPS 所需 g | FCF 所需 g | 判断 |
|---|---:|---:|---|
| 10Y 国债 ×2 | 5% | 7% | 观察 |
| 8% | 8% | 10% | 观察 |
| 10% | 10% | 13% | 偏难 |

## 5. Liquidity and Cap Filter

流动性结论：不构成约束。

## 6. Risk Ranking

主要风险是监管、竞争和 CapEx 回报不及预期。

## 7. Growth Potential

市场仍有结构性增长，但增长上限取决于商业化和资本回报。

## 8. Tax Drag and Net Yield

投资者税务身份为中国大陆个人；股息、预扣税和税后净收益已列明。五年税后股息累计使用 `dividend-total`，不是手工加总。

## 9. Institutional and Opportunity Cost

### Variant View

市场共识偏乐观；我们的 Variant View 是现金回报恢复速度低于收入增长。机会成本是美国 10Y 国债 ×2。

## 10. Position and Exit Rules

### Pre-Mortem

失败路径是 CapEx 增长持续超过经营现金流。

### Action Triggers

价格低于 $80、FCF margin 低于 5%、或 thesis 逻辑被破坏时复核或退出。

## 11. Final Verdict

### 三原则扣问

| 原则 | 回答 |
|---|---|
| 持有 = 买入 | 否 |
| 沉没成本不是成本，机会成本才是真成本 | 机会成本胜出 |
| 10 年回本测试 | 观察 |

最终评级：Watchlist。

## Sources

- [Alphabet Q2 2026 10-Q](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000071/goog-20260630.htm)

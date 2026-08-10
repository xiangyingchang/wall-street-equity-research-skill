# {{ticker}} {{company}} — 华尔街式股票脱水质检（optimized-v3）

> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；机会成本=对应计价货币 10Y 国债 ×2 + 高质量替代资产。数据日期：{{date}}。如与实际 Input 不同，必须在报告中改写。

## First-Page Verdict

| 项目 | 结论 |
|---|---|
| 最终评级 | {{verdict}} |
| 当前动作 | {{action}} |
| 核心理由 | [待填] |
| 当前价格是否值得重新买入 | [待填] |
| 相对机会成本是否胜出 | [待填] |
| 10 年回本测试是否通过 | [待填] |
| 安全买入区间 | [待填] |
| 最大风险 | [待填] |
| 置信度 | [待填] |
| 需人工复核 | [待填] |

## Evidence Ledger

| 数据项 | 数值 | 日期 | 来源/层级 | 单位/期间/口径 | 可信度 |
|---|---:|---|---|---|---|
| 当前价格 / 市值 | [待填] | [待填] | [待填] | [待填] | [待填] |
| 营收 / 净利润 / OCF / CapEx / FCF | [待填] | [待填] | [待填] | TTM/FY | [待填] |
| EPS / FCF per share | [待填] | [待填] | [待填] | TTM/Forward/Normalized | [待填] |
| 股数分母 | [待填] | [待填] | [待填] | point-in-time / diluted weighted average | [待填] |
| 现金 / 有价证券 / 债务 / 租赁 | [待填] | [待填] | [待填] | 最新财报 | [待填] |
| 股息 / 回购 / SBC | [待填] | [待填] | [待填] | 最新公告/期间 | [待填] |
| 10Y 国债 ×2 | [待填] | [待填] | [待填] | opportunity-cost hurdle | [待填] |

## 1. 华尔街式全景扫描 Overview

### Key Forces

1. [待填]
2. [待填]
3. [待填]

- 本次财报改变了什么：[待填]
- 本次财报没有改变什么：[待填]

商业模式、行业趋势、Bull/Base/Bear 和未来 12-24 个月变量：[待填]

## 2. 深度财务剖析与股本蚕食检查 Financial Autopsy

五年趋势、TTM/Forward、利润率、OCF、CapEx、FCF、SBC、回购、现金、债务和租赁：[待填]

### Reported / Adjusted / Normalized 正常化桥

| 口径 | EPS | 经营利润率 | FCF/share | 调整依据与置信度 |
|---|---:|---:|---:|---|
| Reported 财报值 | [待填] | [待填] | [待填] | [待填] |
| Adjusted 调整值 | [待填] | [待填] | [待填] | [待填] |
| Normalized 常态值 | [待填] | [待填] | [待填] | [待填] |

利润正常化与现金流正常化分开；一次性项目不得自动加回 FCF。CapEx 制度、全年指引和 OCF 运行率：[待填]

## 3. 护城河与反脆弱测试 Moat Analysis

用户/客户规模及期间变化、参与度或商业化指标、转换成本、竞争反应和反脆弱性：[待填]

## 4. 极限估值与 10 年回本数学审判

TTM/Forward/Normalized EPS、FCF/share、EV/FCF、起始 EPS、EPS CAGR、退出 PE、持有年限、股数分母和股息处理：[待填]

### Price Discipline 价格纪律

| 价格线 | 公式 | 数值 | 情景 / 置信度 | 动作含义 |
|---|---|---:|---|---|
| Earnings reference price | normalized EPS × reference PE | [待填] | [待填] | 估值参考 |
| Target-return price | `valuation_math.py target-price` | [待填] | [待填] | 目标回报 |
| Cash-confirmation price | normalized FCF/share ÷ cash hurdle | [待填] | [待填] | 现金确认 |
| Joint new-money price | min(active gates) | [待填] | [待填] | 联合门槛 |
| Safety price | target-return price × (1 - safety margin) | [待填] | [待填] | 安全边际 |

价格线输入、公式、现金流置信度和动作映射：[待填]

### 名义 10 年回本测试

EPS 所需增长：[待填]；FCF/share 所需增长：[待填]；结论：[待填]

### 贴现 10 年回本测试

| 贴现率 r | EPS 所需 g | FCF 所需 g | 判断 |
|---|---:|---:|---|
| 10Y 国债 ×2 | [待填] | [待填] | [待填] |
| 8% | [待填] | [待填] | [待填] |
| 10% | [待填] | [待填] | [待填] |

## 5. 流动性黑洞与小盘股熔断测试 Liquidity & Cap Filter

流动性结论：不构成约束 / 构成约束。若构成约束，90 日平均成交额、仓位金额、压力参与率和压力退出天数：[待填]

## 6. 致命风险排序 Risk Ranking

| 风险 | 概率 | 损害 | 领先指标 | 失效动作 |
|---|---|---|---|---|
| [待填] | [待填] | [待填] | [待填] | [待填] |

## 7. 物理增长极限测算 Growth Potential

TAM、当前市占率、未来 5-10 年增长上限、催化剂、再投资需求与物理可达性：[待填]

## 8. 真实到手收益与税收摩擦 Tax Drag & Net Yield

税务身份：[待填]；股息总额、预扣税、股息增长、年限和 `dividend-total` 输出：[待填]

税后股息累计公式：`sum(dividend_0 × (1 + dividend_growth)^t × (1 - withholding_rate))`，不可手填总数。回购是否真正减少股本：[待填]

## 9. 机构视角与机会成本比对 Institutional & Opportunity Cost

### Variant View

市场共识：[待填]；我们的不同判断：[待填]；反证条件：[待填]

与 10Y 国债 ×2、指数、同行和高确定性替代资产比较：[待填]

## 10. 仓位与风控 Position Sizing & Exit Rules

当前持仓事实：Ledger 快照时间、active position 过滤和持仓未核验说明：[待填]

最大仓位、加仓、减仓、清仓条件：[待填]

### Pre-Mortem

最可能的失败路径：[待填]

### Action Triggers

价格、估值、经营和 thesis-break 触发条件：[待填]

## 11. 终极系统判决 The Final Verdict

### 三原则扣问

| 原则 | 回答 |
|---|---|
| 持有 = 买入 | [待填] |
| 沉没成本不是成本，机会成本才是真成本 | [待填] |
| 10 年回本测试 | [待填] |

### 投资评级

Buy / Hold-Index / Watchlist / Avoid 只能选一个。评级理由、价格线、置信度和最终复核清单：[待填]

## Sources

- [公司 IR / 财报](https://www.sec.gov/)

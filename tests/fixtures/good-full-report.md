> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；机会成本=美国 10Y 国债 ×2。

## First-Page Verdict
现价：$10。最新财报：earnings release。最终评级 | Buy

## Evidence Ledger
| 数据项 | 数值 | 日期 | 来源/层级 | 口径 | 可信度 |
|---|---:|---|---|---|---|
| 美国 10Y 国债 | 4.5% | 2026-07-01 | Treasury | 10Y | 高 |

## 1. 华尔街式全景扫描 Overview

### Key Forces
- 本次财报改变了什么：增长放慢。
- 本次财报没有改变什么：护城河仍在。

业务判断：广告商业化仍是主要价值驱动。

## 2. 财务剖析 Financial Autopsy
收入和利润保持增长，CapEx +19.1%，主要由于产能建设提速。

### Reported / Adjusted / Normalized 正常化桥
| 口径 | EPS | 经营利润率 | FCF/share | 证据与限制 |
|---|---:|---:|---:|---|
| Reported 财报值 | $10 | 30% | $1 | 财报原始值 |
| Adjusted 调整值 | $11 | 32% | $1 | 一次性项目有官方依据 |
| Normalized 常态值 | $12 | 33% | $2 | 模型假设，置信度中 |

利润正常化与现金流正常化分开；一次性项目不会自动加回 FCF。

### CapEx 制度与现金流检查
季度 CapEx、全年 CapEx 指引和经营现金流运行率均已核对，当前压力属于计划内结构性变化。

## 3. 护城河 Moat Analysis
网络效应：用户规模 10 亿，较上年增长 8%；参与度和 ARPU 继续提升。

## 4. 极限估值 + 10 年回本数学审判

### 周期/高 CapEx 双估值闸门
EV/FCF 与中周期估值。

目标回报价格：$9。起始 EPS $10，EPS CAGR 8%，退出 PE 18x，持有 5 年，目标回报 9.5%，股息处理为 reinvested_yield。股数口径为加权平均稀释股数。由 `scripts/valuation_math.py` 的 terminal_price / target_price 公式计算。

### Price Discipline 价格纪律
| 价格线 | 公式 | 数值 | 情景 / 置信度 | 动作含义 |
|---|---|---:|---|---|
| Earnings reference price | normalized EPS × reference PE | $10 | Base / 中 | 估值参考，不自动买入 |
| Target-return price | valuation runtime | $9 | Base / 中 | 目标回报 |
| Cash-confirmation price | normalized FCF/share ÷ cash hurdle | $8 | Base / 中 | 现金确认 |
| Joint new-money price | min(active executable gates) | $8 | Base / 中 | Review / Buy gate |
| Safety price | target-return price × (1 - safety margin) | $6 | Base / 中 | 安全边际 |
Price Discipline 输入：Base 情景；Normalized EPS $10；reference PE 18x；Normalized FCF/share $2；cash hurdle 6%，现金流置信度 medium；joint action Review。公式由 `scripts/valuation_math.py` 计算，动作映射为 Review。

### 名义 10 年回本测试
通过。

### 贴现 10 年回本测试
| 贴现率 r | EPS 所需 g | 判断 |
|---|---:|---|
| 10Y 国债 ×1 | 1% | 通过 |
| 10Y 国债 ×2 | 5% | 观察 |
| 8% | 8% | 观察 |
| 10% | 10% | 偏难 |

## 5. 致命风险排序 Risk Ranking
流动性结论：不构成约束。

## 6. 物理增长极限 Growth Potential
TAM 和竞争格局支持中期增长，但需跟踪利润率。

## 7. 机构视角 + 机会成本
机会成本比较：美国 10Y 国债 ×2。

## 8. 仓位与风控
仓位与风险边界：当前仓位需受估值约束。

### Pre-Mortem
失败路径：增长低于预期。

### Action Triggers
价格 ≤ $8；估值低于 20x；经营增长低于 10% 时复核；thesis 逻辑破坏时卖出。

## 9. 最终判决 Final Verdict

### Variant View
市场共识：普通好公司。我们的判断：价格不够好。

### 三原则扣问
| 原则 | 回答 |
|---|---|
| 持有 = 买入 | 是，愿意买 |
| 沉没成本不是成本，机会成本才是真成本 | 机会成本胜出 |
| 10 年回本测试 | 通过 |

## Sources
- [Company IR](https://investor.example.invalid/earnings)

# {{ticker}} {{company}} — 华尔街式分析报告

> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；机会成本=对应计价货币 10Y 国债 ×2 + 相关高质量替代资产。

## First-Page Verdict

| 项目 | 结论 |
|---|---|
| 最终评级 | {{verdict}} |
| 当前动作 | {{action}}（必须等于 Action Resolution 的 resolved action） |
| 核心理由 | TODO |
| 当前价格是否值得重新买入 | TODO |
| 相对机会成本是否胜出 | TODO（比较 runtime IRR） |
| 10 年回本压力测试 | TODO（压力测试，不是单独否决器） |
| 公允价值 / 买入区间 / 压力价格 | TODO（分别列示） |
| 最大风险 | TODO |
| 需人工复核的数据 | TODO |

### Researchability Record

| 项目 | 结论 |
|---|---|
| 报告类型 | 常规报告 / 最新财报更新（TODO） |
| 信息丰富度 | A / B / C（存在 filing gap、近似 TTM 或低置信度 owner earnings 时最高 B） |
| AI 研究置信度 | 高 / 中 / 低（信息丰富度 B 时最高中） |
| 投资确定性 | 高 / 中 / 低 |
| 首页决策置信度 | 高 / 中 / 低 |
| 差异说明 | TODO |

## Evidence Ledger

| 数据项 | 数值 | 日期 | 来源/层级 | 口径 | 可信度 |
|---|---:|---|---|---|---|
| 当前价格 | TODO | {{date}} | TODO（数据商只能 Tier 2） | TODO | TODO |
| 总股本 | TODO | {{date}} | TODO | TODO | TODO |
| 市值 | TODO | {{date}} | TODO | 价格 × 股本 | TODO |
| 现金及等价物 | TODO | {{date}} | TODO | TODO | TODO |
| 有息负债 | TODO | {{date}} | TODO | TODO | TODO |
| TTM EPS | TODO | {{date}} | TODO | TODO | TODO |
| TTM PE | TODO | {{date}} | TODO | 当前价格 ÷ TTM EPS | TODO |
| TTM FCF/share | TODO | {{date}} | TODO | TODO | TODO |
| FCF yield | TODO | {{date}} | TODO | TTM FCF/share ÷ 当前价格 | TODO |
| 10Y Treasury | TODO | {{date}} | TODO | ×1 | TODO |
| 10Y Treasury ×2 | TODO | {{date}} | TODO | ×2目标回报门槛，不是实际无风险资产 | TODO |
| 估算组合权重 | TODO | {{date}} | TODO | TODO | TODO |
| 最新财报 / filing gap | TODO | TODO | TODO | TODO | TODO |

## 1. 华尔街式全景扫描 Overview

### Key Forces

1. TODO
2. TODO
3. TODO

TODO

## 2. 财务剖析 Financial Autopsy

TODO

### One-off Adjustment Ledger

| Adjustment ID | Period | Item | Pre-tax/after-tax | Cash/non-cash | Repeatability | Per-share impact | Treatment | Source |
|---|---|---|---|---|---|---:|---|---|
| TODO | TODO | TODO | TODO | TODO | TODO | TODO | Include / exclude / partial | TODO |

## 3. 护城河 Moat Analysis

TODO

## 4. 极限估值 + 10 年回本数学审判

### 周期/高 CapEx 双估值闸门

TODO

### Scenario EPS Bridge

| Bridge ID | Scenario | Revenue | Operating margin | Operating income | Other income/expense | Pre-tax income | Tax rate | Net income | Diluted shares | EPS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BR-BEAR | Bear | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| BR-BASE | Base | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| BR-BULL | Bull | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |

### Valuation Basis Registry

| Basis ID | Metric | Value | Period | Adjustments | Bridge ID | Use |
|---|---|---:|---|---|---|---|
| TODO-BEAR | EPS/share | TODO | TODO | Adjustment IDs | BR-BEAR | Bear |
| TODO-BASE | EPS/share | TODO | TODO | Adjustment IDs | BR-BASE | Base |
| TODO-BULL | EPS/share | TODO | TODO | Adjustment IDs | BR-BULL | Bull |
| TODO-FCF | FCF/share | TODO | TODO | TODO | N/A | FCF reference |

### Scenario Valuation

| Scenario | Basis ID | Metric value | Multiple | Fair value | Safety margin | Buy price | Key assumptions |
|---|---|---:|---:|---:|---:|---:|---|
| Bear | TODO-BEAR | TODO | TODO | TODO | TODO | TODO | TODO |
| Base | TODO-BASE | TODO | TODO | TODO | TODO | TODO | TODO |
| Bull | TODO-BULL | TODO | TODO | TODO | TODO | TODO | TODO |

### Capex / Owner Earnings Bridge

| Item | Value/range | Period | Evidence | Confidence |
|---|---:|---|---|---|
| Reported OCF | TODO | TODO | TODO | TODO |
| Reported Capex | TODO | TODO | TODO | TODO |
| Reported FCF | TODO | TODO | TODO | TODO |
| Depreciation & amortization | TODO / Unclear | TODO | TODO | TODO |
| Maintenance Capex | TODO / Unclear | TODO | TODO | TODO |
| Growth Capex | TODO / Unclear | TODO | TODO | TODO |
| Strategic / AI Capex | TODO / Unclear | TODO | TODO | TODO |
| Owner Earnings / Normalized FCF | TODO / Unclear | TODO | TODO | TODO |

> 不得把 Capex 标为 non-cash。公司未披露拆分时，不得把全部 Capex 直接命名为 AI/strategic Capex。

### 5-year Scenario IRR — Runtime Output

| Scenario | Starting Basis ID | Starting EPS | EPS CAGR | Exit PE | Annual DPS / yield | Terminal EPS | Terminal price | Cumulative dividends | Total return | 5-year IRR | Runtime command/result ref |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Bear | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| Base | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| Bull | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |

> EPS CAGR 模式不得再单独加回购/缩股收益。所有数值必须由 `valuation_runtime.py irr` 生成。

### Reverse Expectations — Runtime Output

| Current price | Starting Basis ID | Target annual return | Exit PE | Years | Required terminal EPS | Required EPS CAGR | Runtime command/result ref |
|---:|---|---:|---:|---:|---:|---:|---|
| TODO | TODO | TODO | TODO | 5 | TODO | TODO | TODO |

> 默认问题：当前价要达到目标年化回报，在指定退出倍数下需要多高终值 EPS 和 EPS CAGR。不得只反推“未来股价保持现价”。

### 名义 10 年回本压力测试

TODO

### 贴现 10 年回本压力测试

| 贴现率 r | EPS 所需 g | FCF 所需 g | EV/FCF 所需 g | 判断 |
|---|---:|---:|---:|---|
| 10Y 国债 ×1 | TODO | TODO | TODO | TODO |
| 10Y 国债 ×2 | TODO | TODO | TODO | TODO |
| 8% | TODO | TODO | TODO | TODO |
| 10% | TODO | TODO | TODO | TODO |

## 5. 致命风险排序 Risk Ranking

TODO

## 6. 物理增长极限 Growth Potential

TODO

## 7. 机构视角 + 机会成本比对 Institutional & Opportunity Cost

TODO：比较 runtime IRR 与实际国债收益率、个人股票目标回报、指数和高质量替代权益资产。

## 8. 仓位与风控 Position Sizing & Exit Rules

TODO

### Pre-Mortem

TODO

### Action Matrix

| Action | Trigger type | Executable condition | Position/execution |
|---|---|---|---|
| Buy | valuation | N/A — current action is not Buy | TODO |
| Add | price | TODO | TODO |
| Hold | operating | TODO | TODO |
| Reduce | operating/valuation | TODO | TODO |
| Sell | thesis-break | TODO | TODO |

### Current Action Evaluation

| Rule ID | Action | Current facts used | Triggered |
|---|---|---|---|
| TODO | HOLD | TODO | true / false |
| TODO | REDUCE | TODO | true / false |
| TODO | SELL | TODO | true / false |

| Runtime field | Result |
|---|---|
| Triggered rule IDs | TODO |
| Resolved action | TODO（无规则触发时必须 REVIEW） |
| Reported action | TODO |
| Match | true / false（必须 true 才可交付） |

### 公允价值、买入价、压力价格与目标价口径

直接引用 Module 4 Scenario Valuation，不得生成第二套边界。

### 价格区间摘要

| 价格区间 | 估值语境 | 推导来源 |
|---|---|---|
| TODO 以上 | 高估区 | Module 4 |
| TODO-TODO | 合理/观察区 | Module 4 |
| TODO 以下 | 买入/压力区 | Module 4 |

## 9. 最终判决 Final Verdict

### Variant View

TODO

### 三原则扣问

| 原则 | 回答 |
|---|---|
| 持有 = 买入 | TODO |
| 沉没成本不是成本，机会成本才是真成本 | TODO（引用 runtime IRR） |
| 10 年回本测试 | TODO（压力测试） |

### Confidence Boundary

TODO

## Verification

| Check | Result |
|---|---|
| Valuation runtime | TODO |
| Reported action matches resolved action | TODO |
| Valuation consistency | TODO |
| Lint | TODO |
| Audit verdict | TODO |

## Sources

- TODO

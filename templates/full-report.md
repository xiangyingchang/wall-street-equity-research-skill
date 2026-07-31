# {{ticker}} {{company}} — 华尔街式分析报告

> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；机会成本=对应计价货币 10Y 国债 ×2 + 相关高质量替代资产。

## First-Page Verdict

| 项目 | 结论 |
|---|---|
| 最终评级 | {{verdict}} |
| 当前动作 | {{action}} |
| 核心理由 | TODO |
| 当前价格是否值得重新买入 | TODO |
| 相对机会成本是否胜出 | TODO（比较预期总回报/IRR，不机械比较当期 FCF yield） |
| 10 年回本压力测试 | TODO（压力测试，不是单独否决器） |
| 公允价值 / 买入区间 / 压力价格 | TODO（分别列示，不得混称） |
| 最大风险 | TODO |
| 需人工复核的数据 | TODO |

### Researchability Record

| 项目 | 结论 |
|---|---|
| 报告类型 | 常规报告 / 最新财报更新（TODO） |
| 信息丰富度 | A / B / C（TODO） |
| AI 研究置信度 | 高 / 中 / 低（受信息丰富度约束） |
| 投资确定性 | 高 / 中 / 低（独立的商业判断） |
| 首页决策置信度 | 高 / 中 / 低（由证据与 thesis 保守导出） |
| 差异说明 | 仅当两者表面不一致时，用一句话解释 TODO |

## Evidence Ledger

| 数据项 | 数值 | 日期 | 来源/层级 | 口径 | 可信度 |
|---|---:|---|---|---|---|
| 当前价格 | TODO | {{date}} | TODO | TODO | TODO |
| 总股本 | TODO | {{date}} | TODO | TODO | TODO |
| 市值 | TODO | {{date}} | TODO | 价格 × 股本；输入与偏差 TODO | TODO |
| 现金及等价物 | TODO | {{date}} | TODO | TODO | TODO |
| 有息负债 | TODO | {{date}} | TODO | TODO | TODO |
| TTM EPS | TODO | {{date}} | TODO | TODO | TODO |
| TTM PE | TODO | {{date}} | TODO | 当前价格 ÷ TTM EPS | TODO |
| TTM FCF/share | TODO | {{date}} | TODO | 计算值；输入与偏差 TODO | TODO |
| FCF yield | TODO | {{date}} | TODO | TTM FCF/share ÷ 当前价格 | TODO |
| 10Y Treasury | TODO | {{date}} | TODO | ×1 | TODO |
| 10Y Treasury ×2 | TODO | {{date}} | TODO | ×2 | TODO |
| 估算组合权重 | TODO | {{date}} | TODO | TODO | TODO |
| 最新财报 | TODO | TODO | TODO | TODO | TODO |

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

### Valuation Basis Registry

| Basis ID | Metric | Value | Period | Adjustments | Use |
|---|---|---:|---|---|---|
| TODO-BEAR | EPS/share or FCF/share | TODO | TODO | None / Adjustment IDs | Bear |
| TODO-BASE | EPS/share or FCF/share | TODO | TODO | None / Adjustment IDs | Base |
| TODO-BULL | EPS/share or FCF/share | TODO | TODO | None / Adjustment IDs | Bull |

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
| Maintenance Capex | TODO / Unclear | TODO | TODO | TODO |
| Growth Capex | TODO / Unclear | TODO | TODO | TODO |
| Strategic / AI Capex | TODO / Unclear | TODO | TODO | TODO |
| Owner Earnings / Normalized FCF | TODO / Unclear | TODO | TODO | TODO |

### 5-year Scenario IRR

TODO：至少输出 Bear/Base/Bull 的 5 年 IRR，列明盈利增长、分红/回购、稀释和退出倍数。

### Reverse Expectations

TODO：当前价格隐含的收入增速、利润率、资本强度或 FCF 恢复路径是什么？

### 名义 10 年回本压力测试

TODO

### 贴现 10 年回本压力测试

| 贴现率 r | EPS 所需 g | FCF 所需 g | EV/FCF 所需 g | 判断 |
|---|---:|---:|---:|---|
| 10Y 国债 ×1 | TODO | TODO | TODO | TODO |
| 10Y 国债 ×2 | TODO | TODO | TODO | TODO |
| 8% | TODO | TODO | TODO | TODO |
| 10% | TODO | TODO | TODO | TODO |

> 10 年回本是零终值压力测试。失败会提高估值门槛，但不得单独覆盖 Scenario IRR、Reverse Expectations 与商业质量证据。

## 5. 致命风险排序 Risk Ranking

TODO

## 6. 物理增长极限 Growth Potential

TODO

## 7. 机构视角 + 机会成本比对 Institutional & Opportunity Cost

TODO：比较预期股东总回报 / IRR 与国债、指数和高质量替代资产，不要求当前 FCF yield 机械超过国债 ×2。

## 8. 仓位与风控 Position Sizing & Exit Rules

TODO：经营阈值优先使用 TTM 或连续两个季度；单季度 Capex/营运资本时点不应自动触发大幅减仓。

### Pre-Mortem

TODO

### Action Matrix

| Action | Trigger type | Executable condition | Position/execution |
|---|---|---|---|
| Buy | valuation | N/A — current action only; define an honest valuation condition before using Buy | TODO |
| Add | price | TODO explicit comparator/threshold | TODO |
| Hold | operating | TODO explicit comparator/threshold | TODO |
| Reduce | valuation | TODO explicit comparator/threshold | TODO |
| Sell | thesis-break | TODO thesis-break condition | TODO |

### 公允价值、买入价、压力价格与目标价口径

直接引用 Module 4 Scenario Valuation：

- Base fair value / 目标价口径：TODO
- Base buy price：TODO
- Bear/Stress price：TODO
- 不得再用另一套 EPS、倍数或折扣生成第二组价格边界。

### 价格区间摘要

| 价格区间 | 估值语境 | 推导来源 |
|---|---|---|
| TODO 以上 | 高估区 | Module 4 Scenario Valuation |
| TODO-TODO | 合理/观察区 | Module 4 Scenario Valuation |
| TODO 以下 | 买入/压力区（明确是哪一种） | Module 4 Scenario Valuation |

## 9. 最终判决 Final Verdict

### Variant View

TODO

> 仅在四镜头存在未解决的实质分歧时，列在此处或下方最终判决，最多 4 条；不要角色扮演引用。

### 三原则扣问

| 原则 | 回答 |
|---|---|
| 持有 = 买入 | TODO |
| 沉没成本不是成本，机会成本才是真成本 | TODO（用预期 IRR 比较） |
| 10 年回本测试 | TODO（压力测试，不是唯一模型） |

### Confidence Boundary

AI 研究置信度与投资确定性是不同判断；如两者表面不一致，以上方 Researchability Record 的一句话说明为准。

## Sources

- TODO

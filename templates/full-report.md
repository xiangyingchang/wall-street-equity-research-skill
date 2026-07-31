# {{ticker}} {{company}} — 华尔街式分析报告

> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；实际无风险基准=对应计价货币 10Y 国债；股票最低目标回报=10Y 国债 ×2；替代权益资产=相关指数与高质量公司。

## First-Page Verdict

| 项目 | 结论 |
|---|---|
| 最终评级 | {{verdict}} |
| 当前动作 | {{action}}（必须等于 fact-based Action Evaluation 的 resolved action） |
| 核心理由 | TODO |
| 当前价格是否值得重新买入 | TODO |
| 相对机会成本是否胜出 | TODO（比较 runtime IRR；区分实际资产和目标回报门槛） |
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
| 10Y Treasury | TODO | {{date}} | TODO | 实际可投资无风险基准 | TODO |
| 10Y Treasury ×2 | TODO | {{date}} | 计算值 | 股票最低目标回报 hurdle，不是资产 | TODO |
| 估算组合权重 | TODO | {{date}} | TODO | TODO | TODO |
| 最新财报 / filing gap | TODO | TODO | TODO | TODO | TODO |

### Canonical Fact Registry

| Fact ID | Metric | Value | Period/as-of | Source/Tier | Basis/Unit | Confidence |
|---|---|---:|---|---|---|---|
| FACT-CURRENT-PRICE | Current price | TODO | TODO | TODO | 原币种/share | TODO |
| FACT-TTM-OP-MARGIN | TTM operating margin | TODO | TODO | TODO | decimal / % | TODO |
| FACT-TTM-FCF | TTM FCF | TODO | TODO | TODO | 原币种亿 | TODO |
| FACT-CURRENT-WEIGHT | Current portfolio weight | TODO | TODO | TODO | decimal / % | TODO |

> 单季、TTM、Forward 必须使用不同 Fact ID。正文、估值和 Action Evaluation 引用同一指标时，以本表为唯一权威值。

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
| TODO | 历史已发生期间 | TODO | TODO | TODO | TODO | TODO | Include / exclude / partial | TODO |

> 本表只记录已经发生的会计或现金项目。未来收入、margin、税率、股数、Capex 正常化和退出倍数不得放入本表。

## 3. 护城河 Moat Analysis

TODO

## 4. 极限估值 + 10 年回本数学审判

### 周期/高 CapEx 双估值闸门

TODO

### Scenario Assumption Registry

| Assumption ID | Scenario | Variable | Value | Period | Evidence/rationale | Confidence |
|---|---|---|---:|---|---|---|
| ASM-BEAR-REV | Bear | Revenue growth | TODO | Forward 12M | TODO | TODO |
| ASM-BASE-MARGIN | Base | Operating margin | TODO | Forward 12M | TODO | TODO |
| ASM-BULL-EXIT | Bull | Exit PE | TODO | Year 5 | TODO | TODO |

### Forward Revenue Bridge

| Revenue Bridge ID | Scenario | Period | Revenue | Growth/guide basis | Source/assumption ID |
|---|---|---|---:|---|---|
| REV-BEAR-Q1 | Bear | Forward Q1 | TODO | TODO | TODO |
| REV-BEAR-Q2 | Bear | Forward Q2 | TODO | TODO | TODO |
| REV-BEAR-Q3 | Bear | Forward Q3 | TODO | TODO | TODO |
| REV-BEAR-Q4 | Bear | Forward Q4 | TODO | TODO | TODO |
| REV-BASE-Q1 | Base | Forward Q1 | TODO | TODO | TODO |
| REV-BASE-Q2 | Base | Forward Q2 | TODO | TODO | TODO |
| REV-BASE-Q3 | Base | Forward Q3 | TODO | TODO | TODO |
| REV-BASE-Q4 | Base | Forward Q4 | TODO | TODO | TODO |
| REV-BULL-Q1 | Bull | Forward Q1 | TODO | TODO | TODO |
| REV-BULL-Q2 | Bull | Forward Q2 | TODO | TODO | TODO |
| REV-BULL-Q3 | Bull | Forward Q3 | TODO | TODO | TODO |
| REV-BULL-Q4 | Bull | Forward Q4 | TODO | TODO | TODO |

> Forward 12M Revenue 必须为四个明确期间之和，或引用有日期和来源的 FY/NTM 一致预期。禁止“单季 ×4.5”或无定义 run-rate adjustment。

### Scenario EPS Bridge — Runtime Output

| Bridge ID | Scenario | Revenue | Operating margin | Operating income | Other income/expense | Pre-tax income | Tax rate | Net income | Diluted shares | EPS | Runtime command/result ref |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BR-BEAR | Bear | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py eps-bridge ...` |
| BR-BASE | Base | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py eps-bridge ...` |
| BR-BULL | Bull | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py eps-bridge ...` |

> Operating income、pre-tax income、net income 和 EPS 必须逐行复制 `eps-bridge` 输出，禁止手填。Revenue 必须等于对应 Scenario 的 Forward Revenue Bridge 合计。

### Valuation Basis Registry

| Basis ID | Metric | Value | Period | Adjustments | Bridge ID | Use |
|---|---|---:|---|---|---|---|
| TODO-BEAR | EPS/share | TODO | Forward 12M | None / historical Adjustment IDs | BR-BEAR | Bear |
| TODO-BASE | EPS/share | TODO | Forward 12M | None / historical Adjustment IDs | BR-BASE | Base |
| TODO-BULL | EPS/share | TODO | Forward 12M | None / historical Adjustment IDs | BR-BULL | Bull |
| TODO-FCF | FCF/share | TODO | TODO | TODO | N/A | FCF reference |

> Forward operating model可由 Bridge ID 独立生成，不得为了“看起来有桥接”强行引用无关的历史 Adjustment ID。

### Scenario Valuation

| Scenario | Basis ID | Metric value | Multiple | Fair value | Safety margin | Buy price | Key assumptions |
|---|---|---:|---:|---:|---:|---:|---|
| Bear | TODO-BEAR | TODO | TODO | TODO | TODO | TODO | TODO |
| Base | TODO-BASE | TODO | TODO | TODO | TODO | TODO | TODO |
| Bull | TODO-BULL | TODO | TODO | TODO | TODO | TODO | TODO |

### Capex / Owner Earnings Bridge

| Item | Value/range | Period | Evidence | Confidence |
|---|---:|---|---|---|
| Total reported OCF | TODO | TODO | TODO | TODO |
| Total reported Capex | TODO | TODO | TODO | TODO |
| Reported FCF | TODO | TODO | TODO | TODO |
| Depreciation & amortization | TODO / Unclear | TODO | TODO | TODO |
| Maintenance Capex | TODO / Unclear | TODO | TODO | TODO |
| Growth Capex | TODO / Unclear | TODO | TODO | TODO |
| Strategic / AI Capex | Unclear unless disclosed | TODO | TODO | TODO |
| Owner Earnings / Normalized FCF | TODO / Unclear | TODO | TODO | TODO |

> 不得把 Capex 标为 non-cash。公司未披露拆分时，Strategic / AI Capex 必须写 Unclear，不得把 Total Capex 偷换成 AI Capex。未来 Capex 正常化属于 Scenario Assumption Registry。

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
| 股票最低目标回报（默认 10Y ×2） | TODO | TODO | TODO | TODO |
| 8% | TODO | TODO | TODO | TODO |
| 10% | TODO | TODO | TODO | TODO |

## 5. 致命风险排序 Risk Ranking

TODO

## 6. 物理增长极限 Growth Potential

TODO

## 7. 机构视角 + 机会成本比对 Institutional & Opportunity Cost

| Comparator | Type | Expected return / yield | Risk | Evidence |
|---|---|---:|---|---|
| 10Y government bond | Investable risk-free benchmark | TODO | Low | TODO |
| 10Y ×2 | Required-return hurdle, not an asset | TODO | N/A | Calculation |
| Broad index | Investable equity alternative | TODO | Equity risk | TODO |
| Relevant peer | Investable equity alternative | TODO | Equity risk | TODO |
| Target company Base | Scenario IRR | TODO | Company-specific | Runtime |

## 8. 仓位与风控 Position Sizing & Exit Rules

TODO

### Pre-Mortem

TODO

### Action Matrix

| Action | Trigger type | Executable condition | Position/execution |
|---|---|---|---|
| Buy | valuation | N/A — current action is not Buy | TODO |
| Add | price | TODO（引用 Fact ID） | TODO |
| Hold | operating | TODO（引用 Fact ID） | TODO |
| Reduce | operating/valuation | TODO（引用 Fact ID） | TODO |
| Sell | thesis-break | TODO（引用 Fact ID） | TODO |

### Current Action Evaluation — Fact-Based Runtime Output

| Rule ID | Action | Logic | Runtime condition results | Triggered |
|---|---|---|---|---|
| TODO | HOLD | all / any | `FACT-X actual operator expected => true/false` | true / false |
| TODO | REDUCE | all / any | TODO | true / false |
| TODO | SELL | all / any | TODO | true / false |

| Runtime field | Result |
|---|---|
| Canonical Fact IDs used | TODO |
| Triggered rule IDs | TODO |
| Resolved action | TODO（无规则触发时必须 REVIEW） |
| Reported action | TODO |
| Match | true / false（必须 true 才可交付） |
| Runtime command/result ref | `python3 scripts/valuation_runtime.py evaluate-action --input action-evaluation.json` |

> Runtime 输入必须包含 `facts`、结构化 `conditions` 和 operators；禁止由 Agent 先写 `triggered=true/false`。完整报告不得使用 legacy `resolve-action`。

### 公允价值、买入价、压力价格与目标价口径

直接引用 Module 4 Scenario Valuation，不得生成第二套边界。

### 价格区间摘要

| 价格区间 | 估值语境 | 推导来源 |
|---|---|---|
| TODO 以上 | 高估区 | Module 4 |
| TODO-TODO | 合理/观察区 | Module 4 |
| TODO-TODO | 买入区 | Module 4 |
| TODO 以下 | Deep-value / Thesis-review zone：基本面未破坏才可买 | Module 4 + Action Matrix |

## 9. 最终判决 Final Verdict

### Variant View

TODO

### 三原则扣问

| 原则 | 回答 |
|---|---|
| 持有 = 买入 | TODO |
| 沉没成本不是成本，机会成本才是真成本 | TODO（引用 runtime IRR，并区分 hurdle 与可投资资产） |
| 10 年回本测试 | TODO（压力测试） |

### Confidence Boundary

TODO

## Verification

| Check | Result |
|---|---|
| EPS Bridge runtime | TODO |
| Scenario IRR / Reverse runtime | TODO |
| Fact-based Action Evaluation | TODO |
| Reported action matches resolved action | TODO |
| Valuation consistency | TODO |
| Lint | TODO |
| Audit verdict | TODO |

## Sources

- TODO

# {{ticker}} {{company}} — 华尔街式分析报告

> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；实际无风险基准=对应计价货币 10Y 国债；股票最低目标回报=10Y 国债 ×2；替代权益资产=相关指数与高质量公司。

### Generation Manifest

| Field | Value |
|---|---|
| Skill version | 1.5.1 |
| Template schema | full-report-v1.5.1 |
| Git commit | TODO（实际生成仓库 HEAD） |
| Report ID | TODO |
| Runtime artifacts directory | TODO（与报告同目录的 `<report>.artifacts/`） |

> Git commit、Skill version 与 Template schema 缺失或不匹配时不得交付。

## First-Page Verdict

| 项目 | 结论 |
|---|---|
| 最终评级 | {{verdict}} |
| 当前动作 | {{action}}（必须等于 Action Evaluation v2 与 Robustness 的最终建议） |
| 核心理由 | TODO |
| 当前价格是否值得重新买入 | TODO（引用 Base target-return price） |
| 相对机会成本是否胜出 | TODO（比较 Return Pair IRR 与目标回报） |
| 10 年回本压力测试 | TODO（压力测试，不是单独否决器） |
| Forward reference / Target-return / Buy / Stress price | TODO（四类价格分别列示） |
| 最大风险 | TODO |
| 需人工复核的数据 | TODO |

### Researchability Record

| 项目 | 结论 |
|---|---|
| 报告类型 | 常规报告 / 最新财报更新（TODO） |
| 信息丰富度 | A / B / C（存在 filing gap、近似 owner earnings 时最高 B） |
| AI 研究置信度 | 高 / 中 / 低（信息丰富度 B 时最高中） |
| 投资确定性 | 高 / 中 / 低 |
| 首页决策置信度 | 高 / 中 / 低 |
| 差异说明 | TODO |

## Evidence Ledger

| 数据项 | 数值 | 日期 | 来源/层级 | 口径 | 可信度 |
|---|---:|---|---|---|---|
| 当前价格 | TODO | {{date}} | TODO（数据商只能 Tier 2） | TODO | TODO |
| 总股本 | TODO | {{date}} | TODO | point-in-time shares outstanding；不得直接用 weighted-average diluted shares | TODO |
| Weighted-average diluted shares | TODO | TODO | TODO | 仅供 EPS 等期间平均每股计算 | TODO |
| 市值 | TODO | {{date}} | 计算值 | 当前价格 × point-in-time shares | TODO |
| 现金及等价物 | TODO | {{date}} | TODO | TODO | TODO |
| 有息负债 | TODO | {{date}} | TODO | TODO | TODO |
| TTM EPS | TODO | {{date}} | 计算值 | `ttm-derive` 四季度合计 | TODO |
| TTM PE | TODO | {{date}} | 计算值 | 当前价格 ÷ TTM EPS | TODO |
| TTM FCF/share | TODO | {{date}} | 计算值 | TTM FCF ÷ reconciled share basis | TODO |
| FCF yield | TODO | {{date}} | 计算值 | TTM FCF ÷ 市值 | TODO |
| 10Y Treasury | TODO | {{date}} | TODO | 实际可投资无风险基准 | TODO |
| 10Y Treasury ×2 | TODO | {{date}} | 计算值 | 股票最低目标回报 hurdle，不是资产 | TODO |
| 估算组合权重 | TODO | {{date}} | TODO | 用户持仓快照 | TODO |
| 最新财报 / filing gap | TODO | TODO | TODO | TODO | TODO |

### Point-in-Time Share Reconciliation

| Point-in-time shares ID | Point-in-time shares | As-of | Source/Tier | Weighted-average diluted shares | Difference | Market-cap basis |
|---|---:|---|---|---:|---:|---|
| FACT-SHARES-POINT | TODO | TODO | TODO | TODO | TODO | FACT-CURRENT-PRICE × FACT-SHARES-POINT |

> 仅写“见 reconciliation”不算完成；本表必须有可验证的 point-in-time shares、日期与来源。

### Canonical Value Registry

| Value ID | Kind | Metric | Value | Period/as-of | Source/Tier | Basis/Unit | Confidence | Inputs/Formula |
|---|---|---|---:|---|---|---|---|---|
| FACT-CURRENT-PRICE | FACT | Current price | TODO | TODO | TODO | 原币种/share | TODO | source |
| FACT-SHARES-POINT | FACT | Point-in-time shares | TODO | TODO | TODO | shares | TODO | source |
| FACT-SHARES-WAVG | FACT | Weighted-average diluted shares | TODO | TODO | TODO | shares | TODO | source |
| FACT-Q1-REV | FACT | Quarterly revenue | TODO | TODO | TODO | 原币种亿 | TODO | source |
| FACT-Q1-OI | FACT | Quarterly operating income | TODO | TODO | TODO | 原币种亿 | TODO | source |
| FACT-Q1-EPS | FACT | Quarterly GAAP EPS | TODO | TODO | TODO | 原币种/share | TODO | source |
| FACT-Q1-FCF | FACT | Quarterly FCF | TODO | TODO | TODO | 原币种亿 | TODO | source |
| DERIVED-TTM-EPS | DERIVED | TTM EPS | TODO | TODO | calculated | 原币种/share | TODO | FACT-Q1-EPS + FACT-Q2-EPS + FACT-Q3-EPS + FACT-Q4-EPS；RUN-TTM-EPS |
| DERIVED-TTM-OP-MARGIN | DERIVED | TTM operating margin | TODO | TODO | calculated | decimal / % | TODO | FACT-Q1-OI..Q4 / FACT-Q1-REV..Q4；RUN-TTM-MARGIN |
| DERIVED-TTM-FCF | DERIVED | TTM FCF | TODO | TODO | calculated | 原币种亿 | TODO | FACT-Q1-FCF + FACT-Q2-FCF + FACT-Q3-FCF + FACT-Q4-FCF；RUN-TTM-FCF |
| MODEL-BASE-REFERENCE-VALUE | MODEL | Base forward reference value | TODO | Scenario | runtime | 原币种/share | TODO | RUN-SCENARIO-BASE |
| MODEL-BASE-TARGET-RETURN-PRICE | MODEL | Base target-return price | TODO | Scenario | runtime | 原币种/share | TODO | RUN-RETURN-BASE |

> `FACT-*` 只放外部可验证事实；`DERIVED-*` 必须列出实际存在的输入 IDs；`MODEL-*` 放估值与回报模型输出。所有引用必须在全局 ID Graph 中闭合。

### TTM Derivation - Runtime Output

| Derivation ID | Metric | Mode | Component IDs | Component totals | Value | Runtime Artifact ID |
|---|---|---|---|---|---:|---|
| DERIVED-TTM-EPS | TTM EPS | sum | TODO（四个季度 FACT EPS IDs） | TODO | TODO | RUN-TTM-EPS |
| DERIVED-TTM-OP-MARGIN | TTM operating margin | ratio | TODO（四个 OI + 四个 Revenue FACT IDs） | TODO | TODO | RUN-TTM-MARGIN |
| DERIVED-TTM-FCF | TTM FCF | sum | TODO（四个季度 FACT FCF IDs） | TODO | TODO | RUN-TTM-FCF |

> TTM margin = 四季度 operating income 合计 ÷ 四季度 revenue 合计，不得平均季度利润率。

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
| ADJ-TODO | 历史已发生期间 | TODO | TODO | TODO | TODO | TODO | Include / exclude / partial | TODO |

> 本表只记录已经发生的会计或现金项目。Forward Basis 不得把历史 Adjustment IDs 伪装成直接数学输入。

## 3. 护城河 Moat Analysis

TODO

### 护城河五维评分

| 维度 | 分数 | 证据 |
|---|---:|---|
| TODO | TODO | TODO |
| TODO | TODO | TODO |
| TODO | TODO | TODO |
| TODO | TODO | TODO |
| TODO | TODO | TODO |

### 竞品对比 Peer Comparison

| 公司 | 指标 1 | 指标 2 | 指标 3 |
|---|---:|---:|---:|
| TODO | TODO | TODO | TODO |
| TODO | TODO | TODO | TODO |

## 4. 极限估值 + 10 年回本数学审判

### 周期/高 CapEx 双估值闸门

TODO

### Scenario Assumption Registry

| Assumption ID | Scenario | Variable | Value | Scope | Mode | Base period | Forecast period | Input role | Evidence/rationale | Confidence |
|---|---|---|---:|---|---|---|---|---|---|---|
| ASM-BEAR-Q1-REV | Bear | Revenue growth / guide | TODO | quarter | yoy / qoq / guide_midpoint / explicit / consensus | TODO | TODO | revenue growth | TODO | TODO |
| ASM-BASE-Q1-REV | Base | Revenue growth / guide | TODO | quarter | TODO | TODO | TODO | revenue growth | TODO | TODO |
| ASM-BULL-Q1-REV | Bull | Revenue growth / guide | TODO | quarter | TODO | TODO | TODO | revenue growth | TODO | TODO |
| ASM-BEAR-MARGIN | Bear | Operating margin | TODO | Forward 12M | explicit | - | Forward 12M | operating margin | TODO | TODO |
| ASM-BASE-MARGIN | Base | Operating margin | TODO | Forward 12M | explicit | - | Forward 12M | operating margin | TODO | TODO |
| ASM-BULL-MARGIN | Bull | Operating margin | TODO | Forward 12M | explicit | - | Forward 12M | operating margin | TODO | TODO |
| ASM-BASE-TAX | Base | Tax rate | TODO | Forward 12M | explicit | - | Forward 12M | tax rate | TODO | TODO |
| ASM-BASE-SHARES | Base | Diluted shares | TODO | Forward 12M | explicit | - | Forward 12M | diluted shares | TODO | TODO |
| ASM-BASE-OTHER-INCOME | Base | Other income/expense | TODO | Forward 12M | explicit | - | Forward 12M | other income | TODO | TODO |
| ASM-BASE-EPS-CAGR | Base | EPS CAGR | TODO | 5Y | explicit | - | Year 5 | eps cagr | TODO | TODO |
| ASM-BASE-EXIT | Base | Exit PE | TODO | 5Y | explicit | - | Year 5 | exit pe | TODO | TODO |
| ASM-BASE-DIVIDEND | Base | Dividend yield / DPS | TODO | 5Y | explicit | - | Year 1-5 | dividend | TODO | TODO |
| ASM-TARGET-RETURN | All | Target return | TODO | 5Y | explicit | - | Year 1-5 | target return | TODO | TODO |
| ASM-BASE-REFERENCE-MULTIPLE | Base | Reference multiple | TODO | Forward 12M | explicit | - | Forward 12M | reference multiple | TODO | TODO |
| ASM-BASE-SAFETY-MARGIN | Base | Safety margin | TODO | current | explicit | - | current | safety margin | TODO | TODO |
| ASM-BASE-CAPEX | Base | Capex normalization | TODO | TODO | explicit | - | TODO | capex normalization | TODO | TODO |

> Bear/Base/Bull 的同类输入均需分别注册。tax、shares、other income、EPS CAGR、dividend、exit PE、reference multiple、safety margin 不得以裸数字进入 runtime。

### Revenue Forecast - Runtime Output

| Revenue Bridge ID | Scenario | Forecast period | Mode | Base period | Base Value ID | Growth/Value Assumption ID | Revenue | Runtime Artifact ID |
|---|---|---|---|---|---|---|---:|---|
| REV-BEAR-Q1 | Bear | TODO | TODO | TODO | TODO | ASM-BEAR-Q1-REV | TODO | RUN-REV-BEAR |
| REV-BEAR-Q2 | Bear | TODO | TODO | TODO | TODO | TODO | TODO | RUN-REV-BEAR |
| REV-BEAR-Q3 | Bear | TODO | TODO | TODO | TODO | TODO | TODO | RUN-REV-BEAR |
| REV-BEAR-Q4 | Bear | TODO | TODO | TODO | TODO | TODO | TODO | RUN-REV-BEAR |
| REV-BASE-Q1 | Base | TODO | TODO | TODO | TODO | ASM-BASE-Q1-REV | TODO | RUN-REV-BASE |
| REV-BASE-Q2 | Base | TODO | TODO | TODO | TODO | TODO | TODO | RUN-REV-BASE |
| REV-BASE-Q3 | Base | TODO | TODO | TODO | TODO | TODO | TODO | RUN-REV-BASE |
| REV-BASE-Q4 | Base | TODO | TODO | TODO | TODO | TODO | TODO | RUN-REV-BASE |
| REV-BULL-Q1 | Bull | TODO | TODO | TODO | TODO | ASM-BULL-Q1-REV | TODO | RUN-REV-BULL |
| REV-BULL-Q2 | Bull | TODO | TODO | TODO | TODO | TODO | TODO | RUN-REV-BULL |
| REV-BULL-Q3 | Bull | TODO | TODO | TODO | TODO | TODO | TODO | RUN-REV-BULL |
| REV-BULL-Q4 | Bull | TODO | TODO | TODO | TODO | TODO | TODO | RUN-REV-BULL |

> `yoy` 的 Base period 必须是上一年同季度；`qoq` 必须是上一季度。Revenue row 的 mode、base period、forecast period 与 Assumption 必须逐项一致。

### Scenario EPS Bridge - Runtime Output

| Bridge ID | Scenario | Revenue | Operating margin | Operating income | Other income/expense | Pre-tax income | Tax rate | Net income | Diluted shares | EPS | Input Assumption IDs | Runtime Artifact ID |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BR-BEAR | Bear | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | ASM-BEAR-MARGIN, ASM-BEAR-TAX, ASM-BEAR-SHARES, ASM-BEAR-OTHER-INCOME | RUN-EPS-BEAR |
| BR-BASE | Base | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | ASM-BASE-MARGIN, ASM-BASE-TAX, ASM-BASE-SHARES, ASM-BASE-OTHER-INCOME | RUN-EPS-BASE |
| BR-BULL | Bull | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | ASM-BULL-MARGIN, ASM-BULL-TAX, ASM-BULL-SHARES, ASM-BULL-OTHER-INCOME | RUN-EPS-BULL |

### Valuation Basis Registry

| Basis ID | Metric | Value | Period | Adjustments | Bridge ID | Input Assumption IDs | Use |
|---|---|---:|---|---|---|---|---|
| B-BEAR | EPS/share | TODO | Forward 12M | None | BR-BEAR | TODO（实际进入 BR-BEAR 的 ASM IDs） | Bear |
| B-BASE | EPS/share | TODO | Forward 12M | None | BR-BASE | TODO（实际进入 BR-BASE 的 ASM IDs） | Base |
| B-BULL | EPS/share | TODO | Forward 12M | None | BR-BULL | TODO（实际进入 BR-BULL 的 ASM IDs） | Bull |
| B-FCF | FCF/share | TODO | TTM | None | N/A | DERIVED-TTM-FCF, FACT-SHARES-POINT | FCF reference |

### Scenario Valuation - Runtime Output

| Scenario | Basis ID | Metric value | Reference multiple | Forward reference value | Target-return price | Safety margin | Buy price | Input Assumption IDs | Runtime Artifact ID |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| Bear | B-BEAR | TODO | TODO | TODO | TODO | TODO | TODO | ASM-BEAR-REFERENCE-MULTIPLE, ASM-BEAR-SAFETY-MARGIN | RUN-SCENARIO-BEAR |
| Base | B-BASE | TODO | TODO | TODO | TODO | TODO | TODO | ASM-BASE-REFERENCE-MULTIPLE, ASM-BASE-SAFETY-MARGIN | RUN-SCENARIO-BASE |
| Bull | B-BULL | TODO | TODO | TODO | TODO | TODO | TODO | ASM-BULL-REFERENCE-MULTIPLE, ASM-BULL-SAFETY-MARGIN | RUN-SCENARIO-BULL |

> 必须运行 `python3 scripts/report_integrity_v151.py scenario-value --input ...`。Forward reference = Metric × reference multiple；Buy price = Target-return price × (1 - safety margin)。禁止手填或机械对 Forward reference 打折。

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

### Return Pair - Runtime Output

| Scenario | Starting Basis ID | Starting EPS | EPS CAGR | Exit PE | Years | Dividend assumption | Target return | 5-year IRR | Required terminal EPS | Required EPS CAGR | Target-return price | Input Assumption IDs | Runtime Artifact ID |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| Bear | B-BEAR | TODO | TODO | TODO | 5 | TODO | TODO | TODO | TODO | TODO | TODO | ASM-BEAR-EPS-CAGR, ASM-BEAR-EXIT, ASM-BEAR-DIVIDEND, ASM-TARGET-RETURN | RUN-RETURN-BEAR |
| Base | B-BASE | TODO | TODO | TODO | 5 | TODO | TODO | TODO | TODO | TODO | TODO | ASM-BASE-EPS-CAGR, ASM-BASE-EXIT, ASM-BASE-DIVIDEND, ASM-TARGET-RETURN | RUN-RETURN-BASE |
| Bull | B-BULL | TODO | TODO | TODO | 5 | TODO | TODO | TODO | TODO | TODO | TODO | ASM-BULL-EPS-CAGR, ASM-BULL-EXIT, ASM-BULL-DIVIDEND, ASM-TARGET-RETURN | RUN-RETURN-BULL |

> Required terminal EPS 必须等于 Starting EPS × (1 + Required EPS CAGR)^Years，并与 Runtime Artifact 逐字段一致。

### 名义 10 年回本压力测试

TODO

### 贴现 10 年回本压力测试

| 贴现率 r | EPS 所需 g | FCF 所需 g | EV/FCF 所需 g | 判断 |
|---|---:|---:|---:|---|
| 10Y 国债 ×1 | TODO | TODO | TODO | TODO |
| 10Y Treasury ×2 | TODO | TODO | TODO | TODO |
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
| Target company Base | Scenario IRR | TODO | Company-specific | RUN-RETURN-BASE |

## 8. 仓位与风控 Position Sizing & Exit Rules

TODO

### Pre-Mortem

TODO

### Threshold Policy Registry

| Threshold ID | Metric | Value | Basis | Lookback | Confirmation | Tolerance | Minimum confidence | Rationale |
|---|---|---:|---|---|---:|---:|---|---|
| THR-BUY-PRICE | Current price | TODO | MODEL-BASE-TARGET-RETURN-PRICE | Current | 1 | TODO | Medium | TODO |
| THR-ADD-PRICE | Current price | TODO | MODEL-BASE-TARGET-RETURN-PRICE | Current | 1 | TODO | Medium | TODO |
| THR-HOLD-OPERATING | TODO | TODO | historical distribution / guide | TODO | TODO | TODO | TODO | TODO |
| THR-REDUCE-OPERATING | TODO | TODO | historical distribution / thesis | TODO | TODO | TODO | TODO | TODO |
| THR-SELL-THESIS | TODO | TODO | thesis-break | TODO | TODO | TODO | TODO | TODO |

### Action Matrix

| Rule ID | Action | Trigger type | Executable condition | Position/execution |
|---|---|---|---|---|
| RULE-BUY | BUY | valuation | FACT-CURRENT-PRICE < THR-BUY-PRICE AND thesis intact | TODO |
| RULE-ADD | ADD | valuation/operating | FACT-CURRENT-PRICE < THR-ADD-PRICE AND operating confirmation | TODO |
| RULE-HOLD | HOLD | operating | DERIVED-* meets THR-HOLD-OPERATING | TODO |
| RULE-REDUCE-OPERATING | REDUCE | operating | DERIVED-* breaches THR-REDUCE-OPERATING | TODO |
| RULE-REDUCE-VALUATION | REDUCE | valuation | MODEL-* / FACT-* breaches declared THR-* | TODO |
| RULE-SELL | SELL | thesis-break | DERIVED-* breaches THR-SELL-THESIS | TODO |

> `N/A because current action is not X` 禁止。所有 executable rules 必须进入 Action Evaluation runtime。

### Current Action Evaluation - Runtime Output

| Rule ID | Action | Logic | Condition status | Triggered / indeterminate | Reason |
|---|---|---|---|---|---|
| RULE-BUY | BUY | all / any | TODO | TODO | TODO |
| RULE-ADD | ADD | all / any | TODO | TODO | TODO |
| RULE-HOLD | HOLD | all / any | TODO | TODO | TODO |
| RULE-REDUCE-OPERATING | REDUCE | all / any | TODO | TODO | TODO |
| RULE-REDUCE-VALUATION | REDUCE | all / any | TODO | TODO | TODO |
| RULE-SELL | SELL | all / any | TODO | TODO | TODO |

| Runtime field | Result |
|---|---|
| Mode | v2-threshold-policy |
| Canonical Value IDs used | TODO |
| Threshold IDs used | TODO |
| Triggered rule IDs | TODO |
| Indeterminate rule IDs | TODO |
| Resolved action | TODO（不确定或无触发时 REVIEW） |
| Reported action | TODO |
| Match | TODO |
| Action artifact ID | RUN-ACTION |
| Robustness artifact ID | RUN-ROBUSTNESS |
| Robustness stable | TODO |
| Robustness recommended action | TODO（stable=false 时必须 REVIEW） |

### 公允价值、目标回报价格、买入价与压力价格

- Forward reference value：TODO
- Target-return price：TODO
- Safety-margin buy price：TODO
- Stress price：TODO

### 价格区间摘要

| 价格区间 | 估值语境 | 推导来源 |
|---|---|---|
| TODO 以下 | 目标回报买入区（基本面未破坏） | Scenario Valuation runtime |
| TODO-TODO | 观察区 | Target-return price 至 forward reference value |
| TODO 以上 | 高估区 | Scenario reference / Bull boundary |

## 9. 最终判决 Final Verdict

### Variant View

TODO

### 三原则扣问

| 原则 | 回答 |
|---|---|
| 持有 = 买入 | TODO（引用 Return Pair 与 target-return price） |
| 沉没成本不是成本，机会成本才是真成本 | TODO |
| 10 年回本测试 | TODO（压力测试） |

### Confidence Boundary

TODO

### Runtime Artifact Manifest

| Artifact ID | Runtime | Artifact file | Artifact hash | Report section | Status |
|---|---|---|---|---|---|
| RUN-TTM-EPS | ttm-derive | TODO | TODO（64位 SHA-256） | TTM Derivation | TODO |
| RUN-TTM-MARGIN | ttm-derive | TODO | TODO | TTM Derivation | TODO |
| RUN-TTM-FCF | ttm-derive | TODO | TODO | TTM Derivation | TODO |
| RUN-REV-BEAR | revenue-bridge | TODO | TODO | Revenue Forecast | TODO |
| RUN-REV-BASE | revenue-bridge | TODO | TODO | Revenue Forecast | TODO |
| RUN-REV-BULL | revenue-bridge | TODO | TODO | Revenue Forecast | TODO |
| RUN-EPS-BEAR | eps-bridge | TODO | TODO | EPS Bridge | TODO |
| RUN-EPS-BASE | eps-bridge | TODO | TODO | EPS Bridge | TODO |
| RUN-EPS-BULL | eps-bridge | TODO | TODO | EPS Bridge | TODO |
| RUN-RETURN-BEAR | return-pair | TODO | TODO | Return Pair | TODO |
| RUN-RETURN-BASE | return-pair | TODO | TODO | Return Pair | TODO |
| RUN-RETURN-BULL | return-pair | TODO | TODO | Return Pair | TODO |
| RUN-SCENARIO-BEAR | scenario-value | TODO | TODO | Scenario Valuation | TODO |
| RUN-SCENARIO-BASE | scenario-value | TODO | TODO | Scenario Valuation | TODO |
| RUN-SCENARIO-BULL | scenario-value | TODO | TODO | Scenario Valuation | TODO |
| RUN-ACTION | evaluate-action | TODO | TODO | Action Evaluation | TODO |
| RUN-ROBUSTNESS | robustness | TODO | TODO | Robustness | TODO |

> Existing runtime JSON must be wrapped with `report_integrity_v151.py wrap-artifact`; checker 使用 `--artifacts-dir` 验证文件、ID 与 hash。

### Verification

| Check | Result |
|---|---|
| TTM derivation runtime | TODO |
| Revenue bridge runtime | TODO |
| EPS bridge runtime | TODO |
| Return pair runtime | TODO |
| Scenario valuation runtime | TODO |
| Fact-based action evaluation | TODO |
| Action robustness | TODO |
| Runtime artifact binding | TODO |
| Global ID graph | TODO |
| Revenue period semantics | TODO |
| Valuation consistency | TODO |
| Input/decision consistency | TODO |
| Runtime/reference integrity | TODO |
| Lint | TODO |
| Audit verdict | TODO |

> 以上任一项为 TODO / FAIL / 未运行 / Unknown，报告不得交付。

## Sources

- TODO

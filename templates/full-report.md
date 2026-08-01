# {{ticker}} {{company}} — 华尔街式分析报告

> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；实际无风险基准=对应计价货币 10Y 国债；股票最低目标回报=10Y 国债 ×2；替代权益资产=相关指数与高质量公司。

## First-Page Verdict

| 项目 | 结论 |
|---|---|
| 最终评级 | {{verdict}} |
| 当前动作 | {{action}}（必须等于 Action Evaluation v2 与 Robustness 的最终建议） |
| 核心理由 | TODO |
| 当前价格是否值得重新买入 | TODO |
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
| 市值 | TODO | {{date}} | 计算值 | 当前价格 × point-in-time shares | TODO |
| 现金及等价物 | TODO | {{date}} | TODO | TODO | TODO |
| 有息负债 | TODO | {{date}} | TODO | TODO | TODO |
| TTM EPS | TODO | {{date}} | 计算值 | `ttm-derive` 四季度合计 | TODO |
| TTM PE | TODO | {{date}} | 计算值 | 当前价格 ÷ TTM EPS | TODO |
| TTM FCF/share | TODO | {{date}} | 计算值 | `ttm-derive` / point-in-time or reconciled shares | TODO |
| FCF yield | TODO | {{date}} | 计算值 | TTM FCF/share ÷ 当前价格 | TODO |
| 10Y Treasury | TODO | {{date}} | TODO | 实际可投资无风险基准 | TODO |
| 10Y Treasury ×2 | TODO | {{date}} | 计算值 | 股票最低目标回报 hurdle，不是资产 | TODO |
| 估算组合权重 | TODO | {{date}} | TODO | 用户持仓快照 | TODO |
| 最新财报 / filing gap | TODO | TODO | TODO | TODO | TODO |

### Canonical Value Registry

| Value ID | Kind | Metric | Value | Period/as-of | Source/Tier | Basis/Unit | Confidence | Inputs/Formula |
|---|---|---|---:|---|---|---|---|---|
| FACT-CURRENT-PRICE | FACT | Current price | TODO | TODO | TODO | 原币种/share | TODO | source |
| FACT-Q1-REV | FACT | Quarterly revenue | TODO | TODO | TODO | 原币种亿 | TODO | source |
| DERIVED-TTM-EPS | DERIVED | TTM EPS | TODO | TODO | calculated | 原币种/share | TODO | `ttm-derive` + four FACT IDs |
| DERIVED-TTM-OP-MARGIN | DERIVED | TTM operating margin | TODO | TODO | calculated | decimal / % | TODO | `ttm-derive` ratio + eight FACT IDs |
| DERIVED-TTM-FCF | DERIVED | TTM FCF | TODO | TODO | calculated | 原币种亿 | TODO | `ttm-derive` + four FACT IDs |
| MODEL-BASE-REFERENCE-VALUE | MODEL | Base forward reference value | TODO | Scenario | runtime | 原币种/share | TODO | Basis × reference multiple |
| MODEL-BASE-TARGET-RETURN-PRICE | MODEL | Base target-return price | TODO | Scenario | runtime | 原币种/share | TODO | `return-pair` |

> `FACT-*` 只放外部可验证事实；`DERIVED-*` 必须写 Inputs/Formula；`MODEL-*` 放 fair value、IRR、目标价等模型输出。禁止 `FACT-BULL-FAIR-VALUE` 之类命名。

### TTM Derivation - Runtime Output

| Derivation ID | Metric | Mode | Component IDs | Component totals | Value | Runtime ref |
|---|---|---|---|---|---:|---|
| DERIV-TTM-EPS | TTM EPS | sum | TODO（四个季度 FACT IDs） | TODO | TODO | `valuation_runtime.py ttm-derive --input ttm-eps.json` |
| DERIV-TTM-OP-MARGIN | TTM operating margin | ratio | TODO（四个 OI + 四个 Revenue FACT IDs） | TODO | TODO | `valuation_runtime.py ttm-derive --input ttm-margin.json` |
| DERIV-TTM-FCF | TTM FCF | sum | TODO（四个季度 FACT IDs） | TODO | TODO | `valuation_runtime.py ttm-derive --input ttm-fcf.json` |

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
| TODO | 历史已发生期间 | TODO | TODO | TODO | TODO | TODO | Include / exclude / partial | TODO |

> 本表只记录已经发生的会计或现金项目。未来收入、margin、税率、股数、Capex 正常化和退出倍数不得放入本表。

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

| Assumption ID | Scenario | Variable | Value | Period | Evidence/rationale | Confidence |
|---|---|---|---:|---|---|---|
| ASM-BEAR-REV | Bear | Revenue growth / guide path | TODO | Forward 12M | TODO | TODO |
| ASM-BASE-REV | Base | Revenue growth / guide path | TODO | Forward 12M | TODO | TODO |
| ASM-BULL-REV | Bull | Revenue growth / guide path | TODO | Forward 12M | TODO | TODO |
| ASM-BASE-MARGIN | Base | Operating margin | TODO | Forward 12M | TODO | TODO |
| ASM-BASE-TAX | Base | Tax rate | TODO | Forward 12M | TODO | TODO |
| ASM-BASE-SHARES | Base | Diluted shares | TODO | Forward 12M | TODO | TODO |
| ASM-BASE-EPS-CAGR | Base | EPS CAGR | TODO | Year 1-5 | TODO | TODO |
| ASM-BASE-EXIT | Base | Exit PE | TODO | Year 5 | TODO | TODO |
| ASM-BASE-DIVIDEND | Base | Dividend yield / DPS | TODO | Year 1-5 | TODO | TODO |
| ASM-BASE-CAPEX | Base | Capex normalization | TODO | TODO | TODO | TODO |

### Revenue Forecast - Runtime Output

| Revenue Bridge ID | Scenario | Period | Mode | Base Value | Growth | Guide Low | Guide High | Revenue | Source/Assumption ID | Runtime ref |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| REV-BEAR-Q1 | Bear | TODO | guide_midpoint / yoy / qoq / explicit / consensus | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input bear-revenue.json` |
| REV-BEAR-Q2 | Bear | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input bear-revenue.json` |
| REV-BEAR-Q3 | Bear | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input bear-revenue.json` |
| REV-BEAR-Q4 | Bear | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input bear-revenue.json` |
| REV-BASE-Q1 | Base | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input base-revenue.json` |
| REV-BASE-Q2 | Base | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input base-revenue.json` |
| REV-BASE-Q3 | Base | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input base-revenue.json` |
| REV-BASE-Q4 | Base | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input base-revenue.json` |
| REV-BULL-Q1 | Bull | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input bull-revenue.json` |
| REV-BULL-Q2 | Bull | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input bull-revenue.json` |
| REV-BULL-Q3 | Bull | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input bull-revenue.json` |
| REV-BULL-Q4 | Bull | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py revenue-bridge --input bull-revenue.json` |

> 每个 Scenario 恰好四个期间。YoY/QoQ 必须显示 base 和 growth；guide_midpoint 必须显示 low/high。Bull 低于 Base 必须解释 timing/mix；不同增长假设不得无解释地产生相同总收入。

### Scenario EPS Bridge - Runtime Output

| Bridge ID | Scenario | Revenue | Operating margin | Operating income | Other income/expense | Pre-tax income | Tax rate | Net income | Diluted shares | EPS | Runtime command/result ref |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BR-BEAR | Bear | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py eps-bridge ...` |
| BR-BASE | Base | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py eps-bridge ...` |
| BR-BULL | Bull | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py eps-bridge ...` |

### Valuation Basis Registry

| Basis ID | Metric | Value | Period | Adjustments | Bridge ID | Use |
|---|---|---:|---|---|---|---|
| B-BEAR | EPS/share | TODO | Forward 12M | None / historical Adjustment IDs | BR-BEAR | Bear |
| B-BASE | EPS/share | TODO | Forward 12M | None / historical Adjustment IDs | BR-BASE | Base |
| B-BULL | EPS/share | TODO | Forward 12M | None / historical Adjustment IDs | BR-BULL | Bull |
| B-FCF | FCF/share | TODO | TTM | None | N/A | FCF reference |

### Scenario Valuation

| Scenario | Basis ID | Metric value | Multiple | Fair value | Target-return price | Safety margin | Buy price | Key assumptions |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Bear | B-BEAR | TODO | TODO | TODO（forward reference） | TODO（Return Pair） | TODO | TODO | TODO |
| Base | B-BASE | TODO | TODO | TODO（forward reference） | TODO（Return Pair） | TODO | TODO | TODO |
| Bull | B-BULL | TODO | TODO | TODO（forward reference） | TODO（Return Pair） | TODO | TODO | TODO |

> `Fair value` 在本表是 forward reference value，以兼容既有 checker；真正满足目标回报的当前价格以 `Target-return price` 为准。Buy price 应从 Target-return price 施加额外不确定性折扣，而不是机械对 Fair value 打折。

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

> Capex 是现金。未披露拆分时，Strategic / AI Capex 必须写 Unclear。未来 Capex 正常化属于 Scenario Assumption Registry。

### Return Pair - Runtime Output

| Scenario | Starting Basis ID | Starting EPS | EPS CAGR | Exit PE | Dividend assumption | Target return | 5-year IRR | Required terminal EPS | Required EPS CAGR | Target-return price | Runtime ref |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| Bear | B-BEAR | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py return-pair ...` |
| Base | B-BASE | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py return-pair ...` |
| Bull | B-BULL | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | `valuation_runtime.py return-pair ...` |

> 新报告不得分别调用 `valuation_runtime.py irr` 与 `reverse`。Return Pair 的股息、期限、退出倍数、起始 Basis 与目标回报必须共享。

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
| Target company Base | Scenario IRR | TODO | Company-specific | Return Pair runtime |

## 8. 仓位与风控 Position Sizing & Exit Rules

TODO

### Pre-Mortem

TODO

### Threshold Policy Registry

| Threshold ID | Metric | Value | Basis | Lookback | Confirmation | Tolerance | Minimum confidence | Rationale |
|---|---|---:|---|---|---:|---:|---|---|
| THR-ADD-PRICE | Current price / target-return price | TODO | MODEL target-return price | Current | 1 | TODO | medium | TODO |
| THR-HOLD-OPERATING | TODO | TODO | historical distribution / guide | TODO | TODO | TODO | TODO | TODO |
| THR-REDUCE-OPERATING | TODO | TODO | historical distribution / thesis | TODO | TODO | TODO | TODO | TODO |
| THR-SELL-THESIS | TODO | TODO | thesis-break | TODO | TODO | TODO | TODO | TODO |

> 每个数值条件必须引用 THR-*。Basis、Lookback、Confirmation、Tolerance、Minimum confidence、Rationale 缺一不可。

### Action Matrix

| Action | Trigger type | Executable condition | Position/execution |
|---|---|---|---|
| Buy | valuation | N/A — current action is not Buy | TODO |
| Add | price | FACT-CURRENT-PRICE < THR-ADD-PRICE | TODO |
| Hold | operating | DERIVED-* meets THR-HOLD-OPERATING | TODO |
| Reduce | operating/valuation | DERIVED-* breaches THR-REDUCE-OPERATING | TODO |
| Sell | thesis-break | DERIVED-* breaches THR-SELL-THESIS | TODO |

### Current Action Evaluation - Runtime Output

| Rule ID | Action | Logic | Condition status | Triggered / indeterminate | Reason |
|---|---|---|---|---|---|
| TODO | HOLD | all / any | `VALUE actual operator THR expected => true/false/indeterminate` | TODO | TODO |
| TODO | REDUCE | all / any | TODO | TODO | TODO |
| TODO | SELL | all / any | TODO | TODO | TODO |

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
| Runtime command | `python3 scripts/valuation_runtime.py evaluate-action --input action-evaluation.json` |
| Robustness command | `python3 scripts/valuation_runtime.py robustness --input action-evaluation.json --shock 0.05` |
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
| TODO 以下 | 目标回报买入区（基本面未破坏） | Return Pair target-return price + safety margin |
| TODO-TODO | 观察区 | Target-return price 至 forward reference value |
| TODO 以上 | 高估区 | Scenario reference / Bull boundary |

> 当前价落入“买入区”时，First Page 不得同时写“不值得买入”或动作 Reduce/Sell。价格低于 Stress price 时应进入 Thesis Review，而不是机械抄底。

## 9. 最终判决 Final Verdict

### Variant View

TODO

### 三原则扣问

| 原则 | 回答 |
|---|---|
| 持有 = 买入 | TODO（引用 Return Pair 与目标回报价格） |
| 沉没成本不是成本，机会成本才是真成本 | TODO |
| 10 年回本测试 | TODO（压力测试） |

### Confidence Boundary

TODO

### Verification

| Check | Result |
|---|---|
| TTM derivation runtime | TODO |
| Revenue bridge runtime | TODO |
| EPS bridge runtime | TODO |
| Return pair runtime | TODO |
| Fact-based action evaluation | TODO |
| Action robustness | TODO |
| Valuation consistency | TODO |
| Input/decision consistency | TODO |
| Lint | TODO |
| Audit verdict | TODO |

> 以上任一项为 TODO / FAIL / 未运行 / Unknown，报告不得交付。

## Sources

- TODO

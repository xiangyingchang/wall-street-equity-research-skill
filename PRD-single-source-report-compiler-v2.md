# PRD：Single-Source Report Compiler v2

## 状态

实施中 — 2026-08-01

## 背景

从 v1.1 到 v1.5.1，Skill 已陆续加入：估值口径注册、一次性调整、EPS Bridge、Return Pair、TTM Derivation、Revenue Bridge、Threshold Policy、Action Robustness、Runtime Artifact、全局 ID Graph 与字段绑定。

这些版本修复了大量局部错误，但仍不断出现新的不一致。根因并不是“还缺一个 Checker”，而是当前架构本身允许同一事实、假设、计算结果和动作在多个地方被 Agent 重复书写。

当前流程实质上是：

```text
Agent 收集事实
→ Agent 手写多个 Registry / Runtime input
→ Runtime 计算
→ Agent 再把结果复制进 Markdown
→ 多个 Checker 从 Markdown 反向猜测是否一致
```

这会系统性产生以下问题：

1. **Markdown 同时承担输入、输出和验证载体。** Agent 可以在正文、表格、Legacy 表和结论中写出不同值。
2. **Runtime 并非唯一真相。** 即使 Runtime 计算正确，Agent 仍可能复制错字段、舍入错、引用错 ID。
3. **兼容逻辑污染报告。** 为旧 Checker 保留 Legacy Compatibility Tables，导致同一经济概念出现两套价格和两套语义。
4. **决策规则不是完整的 Policy Object。** Action Matrix 可遗漏 valuation-based Reduce；阈值、容差、uncertainty、确认期可能分散在不同地方。
5. **Assumption 类型不够强。** `Base` 既可能代表场景，也被当作全局公共税率/股息；`guide_midpoint` 的 Value 仍可能写成增长率。
6. **Verification 是报告中的声明，而不是构建结果。** 报告写 PASS 并不等于实际构建链路全部执行。
7. **测试偏向单元和已知错误。** 每轮针对新发现的错误加规则，形成 whack-a-mole；缺少真实公司端到端 golden fixture。
8. **旧版 Checker 与新版 Schema 并行演进。** 为保持旧表头兼容，模板越来越复杂，报告可读性持续下降。

因此，本次不再继续对 Markdown 增加补丁，而是重构信任边界：

> **唯一可编辑输入是结构化 Report Spec；所有数值表、决策、价格区间、Runtime Artifact、Verification 和 Markdown 均由单一 Compiler 生成。**

## 核心原则

### 1. Single Source of Truth

事实、假设、场景、阈值、持仓和叙事都进入一个 `report-spec-v2` JSON 文件。Markdown 不再是计算输入。

### 2. Compile, Don’t Validate After the Fact

Compiler 从 Spec 一次性：

- 校验 Schema；
- 计算 TTM；
- 计算 Revenue / EPS / Return / Payback；
- 求值 Decision Policy；
- 生成 Price Zones；
- 输出 Runtime Bundle；
- 生成 Markdown；
- 输出 Verification Manifest。

不再让 Agent 手工复制 Runtime 结果。

### 3. One Economic Concept, One Field

Base target-return price、buy price、current action 等结果只在 Runtime Bundle 中存在一次；Markdown 中所有展示均由 Renderer 引用同一字段。

### 4. No Legacy Tables in Reports

兼容性属于代码层，不属于报告层。新报告禁止输出 Legacy Compatibility Tables。

### 5. Decision Policy Must Be Complete

Policy 必须同时覆盖：

- valuation；
- operating；
- thesis-break；
- portfolio constraint（可选）。

持有=买入原则必须在 Policy 中有可执行表达，而不是只写在结论文字中。

### 6. Fail Closed

只要 Spec 不完整、场景引用错误、Policy 缺少必需维度、Runtime 失败或输出不可复现，就不生成“正式报告”。

## 目标

1. 新增 `report-spec-v2` 结构化输入契约。
2. 新增单入口编译器：

```bash
python3 scripts/report_pipeline_v2.py build --spec <spec.json> --output <report.md>
```

3. Compiler 生成：
   - `<report>.md`
   - `<report>.bundle.json`
   - `<report>.verification.json`
4. Agent 不得手工填写数值型 Runtime Output 表。
5. 删除 v2 报告中的 Legacy Compatibility Tables。
6. 新增 typed assumptions：`scope=global|bear|base|bull`，并强制场景引用规则。
7. 新增 mode-specific Revenue schema：
   - `guide_midpoint` 使用 low/high；
   - `guide_high` 使用 high；
   - `yoy/qoq` 使用 base value + growth；
   - `explicit/consensus` 使用 value + source。
8. 新增完整 Decision Policy：
   - valuation Hold/Reduce/Buy/Add；
   - operating Hold/Reduce；
   - thesis-break Sell；
   - explicit uncertainty/tolerance；
   - mandatory valuation-based Reduce/Review rule。
9. 新增 Payback Runtime，禁止手填 10 年回本结果。
10. Price Zones 由 target-return price、buy price 和 action thresholds 自动生成，且语义必须与动作一致。
11. Verification Manifest 由 Compiler 生成，报告不得手填 PASS。
12. 新增 Meta 端到端 golden fixture，比较完整 Bundle 和关键 Markdown 片段。
13. 将旧 `valuation_consistency.py`、`input_decision_consistency.py` 对 v2 报告降级为 wrapper：调用 Compiler Verify，不再要求 Legacy 表。

## Report Spec v2

顶层结构：

```json
{
  "schema_version": "report-spec-v2",
  "report": {},
  "facts": {},
  "quarterly_series": {},
  "assumptions": {},
  "scenarios": {},
  "decision_policy": {},
  "portfolio": {},
  "narrative": {},
  "sources": []
}
```

### report

- ticker
- company
- as_of
- currency
- tax_identity
- horizon
- current_price_fact_id
- target_return_assumption_id

### facts

每个 Fact：

- value
- unit
- as_of/period
- source
- tier
- confidence
- uncertainty（显式）

### assumptions

每个 Assumption：

- scope：`global|bear|base|bull`
- role
- value 或 mode-specific payload
- period
- rationale
- confidence

场景只能引用：

```text
自己的 scope + global scope
```

### scenarios

每个场景定义：

- four forward revenue periods；
- operating margin assumption；
- tax assumption；
- other income assumption；
- diluted shares assumption；
- EPS CAGR；
- exit multiple；
- dividend；
- reference multiple；
- safety margin。

### decision_policy

必须包含：

```json
{
  "valuation": {},
  "operating": {},
  "thesis_break": {},
  "resolution": {}
}
```

其中 valuation 必须至少包含：

- `buy_below_buy_price`
- `add_below_buy_price`
- `reduce_when_irr_below_hurdle`

operating 必须至少包含：

- hold threshold
- reduce threshold

所有阈值的 tolerance、uncertainty、confirmation 均在 Policy 内，不允许从文字中追加。

## Compiler 输出

### Bundle

`report-bundle-v2` 包含：

- normalized facts；
- derived TTM values；
- scenario revenue；
- scenario EPS；
- return pairs；
- payback outputs；
- scenario prices；
- market-implied expectations；
- decision evaluation；
- robustness；
- price zones；
- source/spec hashes。

### Markdown

Markdown 仅是 Bundle 的一种渲染视图。所有数值表均从 Bundle 生成，不允许模板中保留人工数值占位表。

### Verification Manifest

包含：

- spec schema PASS；
- source closure PASS；
- assumption scope PASS；
- calculations PASS；
- decision policy completeness PASS；
- decision robustness PASS；
- markdown hash；
- bundle hash；
- compiler version；
- Git commit（由执行端注入）。

## 关键设计决策

### 1. REVIEW 与 REDUCE 的关系

如果 Base IRR 明显低于 hurdle，valuation policy 必须给出：

- REDUCE；或
- REVIEW（如果差距落入显式 tolerance/uncertainty 带）。

不能仅因经营指标处于中性区而忽略估值维度。

### 2. Hold = Buy

报告必须同时输出：

- new-money action；
- existing-position action。

例如：

```text
New money: DO NOT BUY
Existing position: HOLD / REVIEW / REDUCE
```

避免把“不适合新增”与“必须卖出”混成同一个动作。

### 3. Price Zones

自动生成：

- `<= buy_price`：安全边际买入区；
- `(buy_price, target_return_price]`：目标回报达标区；
- `(target_return_price, forward_reference]`：回报不足观察区；
- `> forward_reference`：估值偏高区。

区间名称与 Buy/Add 规则必须一致。

### 4. Payback

新增确定性求根：

```text
sum_{t=1..N} EPS0*(1+g)^t/(1+r)^t = current_price
```

输出 nominal 和各 discount-rate 所需 growth，不再人工估算。

## 实施范围

### 新增

- `scripts/report_pipeline_v2.py`
- `scripts/report_spec_v2.py`
- `scripts/report_renderer_v2.py`
- `references/report-spec-v2.md`
- `references/decision-policy-v2.md`
- `templates/report-spec-v2.example.json`
- `tests/fixtures/meta_v2_spec.json`
- `tests/fixtures/meta_v2_expected.json`
- `tests/test_report_pipeline_v2.py`

### 修改

- `SKILL.md`
- `references/report-contract.md`
- `references/valuation-runtime.md`
- `scripts/valuation_consistency.py`
- `scripts/input_decision_consistency.py`
- CI workflow（显式运行 v2 end-to-end test）

### 废弃

新报告中禁止：

- Legacy Compatibility Tables；
- 人工 Verification 表；
- Markdown 作为 Runtime input；
- 分散的 hidden uncertainty；
- scenario 交叉引用其他场景 assumption；
- 人工 10 年回本表。

旧 v1.x 报告仍可使用 legacy checker，但不得作为新生成报告模板。

## 不在范围内

- 自动抓取财报和市场数据；
- 自动判断哪一个假设最合理；
- 完整 DCF / Monte Carlo；
- 自动下单；
- 组合级优化器。

## 验证标准

### 架构

1. 同一个 Spec 重复编译，Bundle 和 Markdown hash 完全一致（除显式 generated_at 外，v2 不写动态时间）。
2. Markdown 中不存在 Legacy Compatibility Tables。
3. 修改 Bundle 中任一关键值但不改 Spec，不可能通过 verify。
4. 所有 Markdown 数字表均由 Renderer 生成。

### Assumption

5. Bear 引用 Base assumption 必须 FAIL；引用 Global assumption PASS。
6. `guide_midpoint` 不接受 growth 作为 Value。
7. `guide_high` 必须输出 high，不得输出 midpoint。
8. hidden uncertainty 不存在：所有 uncertainty 来自 Fact 或 Policy。

### Decision

9. 缺少 valuation-based Reduce/Review 规则必须 FAIL。
10. Base IRR 低于 hurdle 且超过 tolerance 时，不得只输出 HOLD。
11. new-money action 与 existing-position action 分开输出。
12. Price Zones 与 Buy/Add 阈值冲突时 FAIL。

### Math

13. Payback runtime 数值通过独立测试向量。
14. Scenario value、return pair、market-implied growth 与现有 math 交叉验证。
15. Meta fixture 输出关键结果稳定。

### End-to-End

16. `build` 生成 Markdown、Bundle、Verification 三个文件。
17. `verify` 对未修改产物 PASS。
18. 修改 Markdown 数字、Bundle 数字或 Spec 后不重建，verify FAIL。
19. 全量 unittest、lint self-test、fixtures、CI PASS。

## 成功定义

本版本成功，不是“Checker 又能抓住几个错误”，而是：

> Agent 无法通过手工复制、重复表格、隐藏输入或遗漏规则制造一份看起来 PASS 但内部不一致的报告。报告必须由单一 Spec 编译产生，所有数值和动作只有一个权威来源。
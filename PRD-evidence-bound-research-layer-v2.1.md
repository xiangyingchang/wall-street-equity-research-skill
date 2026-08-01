# PRD：Evidence-Bound Research Layer v2.1

## 状态

实施中 — 2026-08-01

## 背景

v2.0 通过 Single-Source Compiler 解决了长期反复出现的数值复制、Legacy 表冲突、隐藏 uncertainty、动作遗漏和 Markdown 篡改问题。最新 Meta v2 报告证明底层计算链路已经明显更可靠：同一 Spec 可确定性生成 Bundle、Markdown 与 Verification，价格和动作不再出现多套真相。

但最新报告也暴露了新的、且更本质的交付缺陷：

1. 九个研究模块被压缩成一句话，报告退化为“计算摘要”。
2. 模块 4 缺失，固定九模块合同没有被 Compiler 强制。
3. Scenario 只展示输出，不展示收入、利润率、税率、股数、EPS CAGR、倍数等关键输入与依据。
4. Evidence 只展示三个 TTM 数字，没有四季度构成、财务趋势、Capex/OCF、股数、市值和来源映射。
5. Sources 只有机构名称，没有 Source ID、文件标题、日期、Tier、URL/locator 和事实引用关系。
6. `REDUCE` 虽然数学闭合，但缺少对假设置信度、持仓规模、税费和替代资产的解释，容易显得机械。
7. v2 的 Renderer 将 narrative 当成自由字符串，既没有深度要求，也没有证据绑定。

根因不是 Single-Source Compiler 错了，而是 v2.0 只建立了“数值单一真相”，没有建立“研究论证单一真相”。目前架构是：

```text
Typed Spec
→ Deterministic Analytical Bundle
→ Thin Markdown Renderer
```

正确架构应为：

```text
Typed Spec
→ Deterministic Analytical Bundle
→ Evidence-bound Research Layer
→ Complete Markdown Report
```

数值、动作和价格继续由 Compiler 控制；定性研究必须结构化、引用 Source/Fact/Model IDs，并满足最低论证深度。不能回到 Markdown-first，也不能允许 Agent 在正文中新造数字。

## 核心原则

### 1. Numbers remain compiler-owned

正文只能引用 Bundle 中已有的 Fact/Derived/Scenario/Decision IDs。Research Layer 不允许定义新的数字型事实、估值或动作。

### 2. Claims require evidence

每个关键研究判断必须包含：

- claim；
- evidence_refs；
- confidence；
- implication。

`evidence_refs` 只能引用已注册 Source IDs、Fact IDs 或 Bundle paths。

### 3. Nine modules are mandatory

模块 1-9 必须全部存在，且模块 4 不得用前置估值表替代。每个模块有明确的最小内容合同。

### 4. Depth is structural, not word-count theatre

不单纯按字数判定，而要求每个模块包含指定对象：关键力量、财务驱动、护城河维度、估值解释、风险机制、增长约束、机会成本、仓位规则、最终判决。

### 5. Sources are first-class objects

Source 不是字符串列表，而是结构化对象：

- source_id；
- title；
- publisher；
- date；
- tier；
- locator/url；
- document_type；
- scope。

事实和研究 claim 必须可追溯到 Source ID。

### 6. Decision explanation is separate from decision calculation

Compiler 决定动作；Research Layer 解释：

- 为什么该动作在当前假设下成立；
- 哪些假设最敏感；
- 什么情况会推翻动作；
- 对新资金和存量仓位分别意味着什么。

研究文字不得覆盖 Compiler action。

## 目标

1. 将 `report-spec-v2` 升级为 `report-spec-v2.1`，新增结构化 `research` 和 `sources` 合同。
2. 保留 v2 的单一 Spec/Bundle/Markdown/Verification 架构，不恢复手写 Markdown。
3. 强制九模块完整存在。
4. 为每个模块定义最小结构与证据覆盖要求。
5. 生成完整 Evidence Ledger、Quarterly TTM Bridge、Scenario Assumption Table、Source Registry 和 Claim-Evidence Matrix。
6. Narrative 中禁止未绑定数字；所有数值引用必须来自 Bundle path 或 Fact ID。
7. 增加研究质量验证：模块完整性、claim 数量、证据引用闭合、来源 Tier、反方观点、风险触发器和决策解释。
8. 保留并扩展 Meta end-to-end golden fixture，验证报告不再是 130 行计算摘要。
9. Verification Manifest 增加 research completeness、evidence closure、source quality 和 numeric-reference safety。
10. 输出仍然由单一 Compiler 生成，篡改检测继续有效。

## Spec v2.1 设计

### sources

```json
"sources": {
  "SRC-META-Q2-2026": {
    "title": "Meta Reports Second Quarter 2026 Results",
    "publisher": "Meta Investor Relations",
    "date": "2026-07-30",
    "tier": 1,
    "document_type": "earnings-release",
    "locator": "https://...",
    "scope": ["revenue", "operating_income", "capex", "fcf"]
  }
}
```

### facts

Fact 继续包含 value/unit/period/confidence，同时必须增加 `source_ids`。Tier 1 可得时，关键财务事实不得只引用 Tier 2。

### research

```json
"research": {
  "overview": {
    "thesis": {"text": "...", "evidence_refs": ["FACT-*"], "confidence": "medium"},
    "key_forces": [{"claim": "...", "evidence_refs": ["FACT-*", "SRC-*"], "implication": "..."}],
    "variant_view": {"text": "...", "evidence_refs": ["..."]}
  },
  "financial_autopsy": {},
  "moat": {},
  "valuation": {},
  "risks": {},
  "growth_limits": {},
  "opportunity_cost": {},
  "positioning": {},
  "final_verdict": {}
}
```

## 九模块最低合同

### 1. Overview

- 1 个 thesis；
- 至少 3 个 key forces；
- 1 个 variant view；
- 每个对象至少 1 个 evidence ref。

### 2. Financial Autopsy

- revenue / margin / cash-flow 三类分析；
- 至少一个 4-quarter trend table；
- Capex 与 OCF/FCF 的关系；
- 一次性项目和口径边界；
- 至少 4 个 evidence refs。

### 3. Moat

- 至少 4 个维度；
- 每个维度包含 score、evidence、counter-evidence；
- 网络效应公司必须引用用户/参与度指标；
- 输出 moat trajectory：strengthening / stable / weakening。

### 4. Valuation and Payback

- 展示 Scenario 输入和输出；
- 解释 Base 假设来源；
- 展示 reverse expectations；
- 展示 payback；
- 明确 forward reference、target-return、buy price 各自含义；
- 至少 1 个 sensitivity/critical assumption。

### 5. Risks

- 至少 3 个排序风险；
- 每个风险包含 mechanism、leading indicators、trigger、mitigant、evidence refs；
- 风险必须能连接到 Action Policy 或 thesis break。

### 6. Growth Limits

- TAM/用户/变现/资本强度至少覆盖两类约束；
- 区分物理增长、价格增长和利润率增长；
- 明确最可能的增长来源和上限。

### 7. Opportunity Cost

- 实际无风险基准；
- 目标回报 hurdle；
- 至少一个指数和一个可比公司；
- 比较回报、风险和证据质量；
- 不得把 hurdle 当作可投资资产。

### 8. Positioning

- new-money 与 existing-position 分开解释；
- position size / tax / liquidity / concentration 至少讨论两项；
- 给出 Add/Hold/Reduce/Sell 的可执行条件；
- 动作不得覆盖 Compiler 输出。

### 9. Final Verdict

- 总结动作；
- 三原则扣问；
- confidence boundary；
- 关键反证条件；
- 明确“什么事实变化会改变结论”。

## Renderer 输出

新增以下完整部分：

1. Build Manifest；
2. First-Page Verdict；
3. Source Registry；
4. Evidence Ledger；
5. Quarterly TTM Bridge；
6. Scenario Assumption & Valuation；
7. Payback；
8. Decision Policy；
9. 九模块完整研究正文；
10. Claim-Evidence Matrix；
11. Verification 摘要。

## 研究安全规则

1. Research text 中出现数字时，必须通过 `value_refs` 指向 Bundle/Fact；Renderer 负责插入数字。
2. 允许自由文字，但自由文字不得包含未绑定的货币、百分比、倍数和股数。
3. Claim 只能引用已存在的 Source/Fact/Model paths。
4. Source ID 不存在、Fact 无 source_ids、关键 claim 无证据时 FAIL。
5. Tier 1 可用而关键财务 Fact 仅有 Tier 2 时 FAIL 或降级置信度。
6. Narrative 不能改变 action、threshold、uncertainty 或 scenario value。

## 不在范围内

- 自动抓取外部资料；
- 自动判断研究观点一定正确；
- 完整 DCF/Monte Carlo；
- 组合级优化；
- 自动生成长篇空洞文字；
- 支持旧 v1.x Markdown 迁移。

## 验证标准

### Architecture

1. 数值仍只有 Spec/Bundle 一个权威来源。
2. Markdown 篡改后 verify FAIL。
3. Research Layer 无法新增动作或数值。
4. 模块 1-9 缺任一模块时 build FAIL。

### Evidence

5. Fact 引用不存在的 Source ID 时 FAIL。
6. Claim 无 evidence_refs 时 FAIL。
7. Claim 引用不存在 ID/path 时 FAIL。
8. Sources 只有字符串而非结构化对象时 FAIL。
9. 关键财务 Fact 无 Tier 1 来源时降级或 FAIL。

### Research completeness

10. Overview 少于 3 个 key forces 时 FAIL。
11. Moat 少于 4 个维度时 FAIL。
12. Risks 少于 3 个时 FAIL。
13. 模块 4 缺失时 FAIL。
14. Final Verdict 缺反证条件或 confidence boundary 时 FAIL。
15. 任何模块仅一句自由文本而无结构对象时 FAIL。

### Numeric safety

16. Research 自由文本中出现未绑定 `$`、`%`、`x` 倍数或大额数字时 FAIL。
17. Scenario 输入表全部来自 assumptions/bundle。
18. Markdown 中每个关键数字可追溯到 Bundle path。

### End-to-End

19. Meta fixture 生成九模块完整报告。
20. Meta 报告包含 Source Registry、Evidence Ledger、TTM Bridge、Assumption Table、Claim-Evidence Matrix。
21. 生成报告不得出现“未提供叙事内容”。
22. 报告不得缺少模块 4。
23. 全量 unittest、CI build/verify PASS。

## 成功定义

v2.1 成功不是把报告变长，而是：

> 底层数值继续只有一个真相，同时每个关键投资判断都有结构化证据、反方观点、机制解释和可推翻条件；最终报告既不会自相矛盾，也不再只是计算摘要。

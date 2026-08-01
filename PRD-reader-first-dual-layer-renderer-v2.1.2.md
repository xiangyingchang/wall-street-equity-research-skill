# PRD：Reader-First Dual-Layer Renderer v2.1.2

## 状态

实施中 — 2026-08-01

## 背景

v2.1.1 已经解决单一数值真相、Evidence Role、Value Binding、动态 Research Quality 与篡改检测，但最新 Meta 报告仍然明显难读。问题不在计算层，也不在研究内容不足，而在 Renderer 把“给人读的投资报告”和“给机器审计的结构化底稿”混在同一个 Markdown 中。

当前主报告在进入 Overview 前，连续展示 Build Manifest、Source Registry、Evidence Ledger、Quarterly TTM Bridge、三套 Scenario Assumptions、Decision Policy、Robustness 与 Price Zones。正文中又反复输出 `FACT-*`、`BUNDLE:*`、`[supports]`、confidence 等系统字段，末尾再重复完整 Claim-Evidence Matrix。结果是：工程可信度很高，但阅读路径被审计信息打断，叙事被拆成大量“判断—投资含义—证据 ID—置信度”卡片。

历史报告可读性更好，原因不是数据更多，而是它先给结论，再围绕三个核心矛盾组织论证，将关键数字直接嵌入自然语言，最后才附数据和来源。v2.1.2 需要保留 v2.1.1 的全部可信度约束，同时彻底分离 Reader Layer 与 Audit Layer。

## 根因

1. 一个 Renderer 同时承担投资沟通与机器审计两个互相冲突的目标。
2. Source/Fact/Assumption/Claim ID 获得与投资结论相同的视觉权重。
3. Evidence ID 在正文中直接展示，面向内部实现而非读者。
4. Claim block 固定拆成多段短句，破坏连续论证。
5. Claim-Evidence Matrix 和 Verification 出现在主报告中，重复正文且制造噪音。
6. 价值绑定已实现，但实际研究正文中关键数字使用密度仍低。
7. Pipeline 只生成一个 Markdown，无法让主报告保持简洁而又完整保留审计底稿。

## 目标

1. 生成独立的 Reader Report 与 Audit Appendix。
2. Reader Report 控制为清晰、连续、面向投资决策的自然语言报告。
3. Audit Appendix 完整保留 Build Manifest、Source Registry、Evidence Ledger、TTM Bridge、Scenario Assumptions、Decision Policy、Claim-Evidence Matrix 与 Verification。
4. Reader Report 不显示 `FACT-*`、`BUNDLE:*`、`[supports]`、Spec/Bundle hash 等实现细节。
5. Reader Report 只显示人类可读的来源简称；详细 ID 映射放入 Audit Appendix。
6. 将关键数字自然嵌入论证，而不是只留在前置表格。
7. 九个固定研究模块继续完整存在，且模块顺序不变。
8. Compiler、Bundle、决策政策与数值公式保持不变。
9. verify 同时校验 Reader Report、Audit Appendix、Bundle 与 Verification，任一被修改均失败。

## 设计

### A. 四件套交付

构建后生成：

```text
<report>.md
<report>.audit.md
<report>.bundle.json
<report>.verification.json
```

其中：

- `<report>.md`：Reader Report，给投资者阅读；
- `<report>.audit.md`：Audit Appendix，给 Agent、审计器与复核者使用；
- Bundle 与 Verification 保持机器可读。

### B. Reader Report 信息架构

1. 标题与一句生成声明；
2. 一页结论：评级、两类动作、关键价格、核心矛盾、下一步验证；
3. 三个核心矛盾；
4. 九个研究模块；
5. 精简的估值表、风险表和价格区间；
6. 精简来源列表与 Audit Appendix 路径。

Reader Report 不展示：

- Build hash；
- Source ID / Fact ID / Bundle path；
- 完整 Evidence Ledger；
- 完整 Scenario Assumption Registry；
- Decision Policy 原始字段；
- Claim-Evidence Matrix；
- Verification 表。

### C. Audit Appendix 信息架构

完整展示：

- Build Manifest；
- Source Registry；
- Evidence Ledger；
- Quarterly TTM Bridge；
- Scenario Assumptions；
- Scenario Valuation；
- Payback；
- Decision Policy、Robustness 与 Price Zones；
- Claim-Evidence Matrix；
- Research Quality 与 Verification。

### D. 人类可读证据标签

Reader Report 的证据脚注只显示来源标题或简写，例如：

```text
来源：Meta Q2 2026 财报、美国财政部收益率曲线、Base 情景模型。
```

底层仍通过 Evidence Refs 绑定；Renderer 根据 Fact→Source、Source title 和 Bundle path 生成标签。

### E. 连续论证

Reader Report 不再机械输出每条 claim 的 Evidence ID 和 confidence。模块内部将相关 claims 合并为 2–5 个自然段：

- 判断；
- 关键数字；
- 为什么重要；
- 反向证据或边界。

confidence 只在结论边界或真正低置信度判断中自然呈现。

### F. 关键数字覆盖

Reader Report 至少自然展示：

- 当前价格；
- Base IRR 与 target return；
- Base target-return price / buy price / forward reference；
- TTM EPS、TTM operating margin、TTM FCF；
- Base/Bear/Bull EPS 和 IRR；
- 关键季度收入、利润率、FCF；
- Payback 关键结果；
- 主要风险触发条件。

所有数字来自 Bundle，禁止手填。

## 非目标

- 不修改估值公式、Scenario 假设或 Action 决策政策；
- 不降低 Source、Evidence、Value Binding、Research Quality 校验；
- 不回到 Markdown-first；
- 不删除 Audit 数据；
- 不引入新的研究模块；
- 不自动判断投资假设是否经济上正确。

## 验收标准

1. Reader Report 在模块1前不得出现 Source Registry、Evidence Ledger、Build Manifest、Claim-Evidence Matrix。
2. Reader Report 不得出现 `FACT-`、`BUNDLE:`、`[supports]`、Spec hash、Bundle hash。
3. Audit Appendix 必须包含上述完整审计结构。
4. Reader Report 必须包含模块1–9。
5. Reader Report 必须包含 Base IRR、target return、target-return price 与关键 TTM 数据。
6. Reader Report 必须包含连续自然语言段落，而非每条 claim 固定输出证据 ID。
7. 主报告建议长度控制在 150–260 行；Audit Appendix 不设上限。
8. 修改 Reader Report、Audit Appendix、Bundle 或 Verification 任一文件后 verify 必须失败。
9. Verification 必须同时记录 reader markdown hash 与 audit markdown hash。
10. 全量 unittest、lint、自测与 Meta 端到端 build/verify 全部通过。

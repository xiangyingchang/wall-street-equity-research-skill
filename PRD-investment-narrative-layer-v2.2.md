# PRD：Investment Narrative Layer v2.2

## 状态

实施中 — 2026-08-01

## 背景

v2.1.2 已经完成 Reader Report 与 Audit Appendix 分层，解决了审计信息压垮主报告的问题。最新 Meta Reader Report 的结构、数据一致性和可读性已经显著改善，但仍存在明显的“AI 摘要感”：同一观点在一页结论、核心矛盾和 Overview 中重复；财务章节陈列事实多、解释因果少；护城河、机会成本和风险容易落入通用模板；Variant View 只有一句话；关键数字尚未被充分组织成一条有因果、有冲突、有反证的投资故事。

问题不在数值 Compiler，也不在证据约束，而在 Research Spec 仍以离散 Claim 为最主要叙事单位。Renderer 能把 Claim 排成段落，却无法可靠地决定：哪些事实属于同一主题、因果链如何展开、哪些反向证据必须并列、什么验证信号能推翻结论。

本次优化同时研究了 `xbtlin/ai-berkshire`。值得借鉴的不是其具体大师人格，而是以下方法：

1. **多视角对抗**：商业模式、财务估值、行业竞争、风险管理分别独立形成判断，再由主笔综合，而不是单一视角平滑掉冲突。
2. **Bull vs Bear 显式张力**：要求看多和看空逻辑同时存在，避免只写“平衡分析”的正确废话。
3. **镜子测试 / 决策备忘录**：最终结论必须能用少量句子说明“为什么买、为什么不买、错在哪里”。
4. **信息丰富度与反共识机制**：资料多时更应寻找非共识和反面证据；资料不足时允许留白。
5. **研究职责分工**：商业、财务、行业、风险各自有明确问题清单，防止模板化覆盖却没有真正解释。

v2.2 不引入依赖特定客户端的多 Agent 编排，而是把这些优秀方法沉淀成可验证的 Narrative Contract，使任何 Agent 都必须先形成主题、机制链、对抗观点和证伪条件，再由 Compiler 生成主报告。

## 根因

1. Claim 是原子事实判断，但不是完整投资论证。
2. Reader Renderer 按模块顺序串联 Claim，缺乏跨 Claim 的主题聚合与因果结构。
3. 同一个核心判断在结论、核心矛盾、Overview 中重复出现。
4. 财务事实没有强制回答“为什么变化、变化来自哪里、对估值有什么影响”。
5. 护城河和机会成本缺乏公司特异性约束，容易产生适用于任何大公司的模板句。
6. Variant View、Bull Case、Bear Case、反证条件没有形成对称结构。
7. 风险表有风险名称和触发条件，但缺少“概率 × 影响 × 估值传导”的投资含义。
8. 当前 Research Quality 主要验证结构与证据闭环，尚未验证 Narrative 的因果、对抗和决策闭环。

## 目标

1. 在 Source → Fact → Claim 与 Reader Report 之间增加 `Theme / Narrative` 层。
2. 每个核心 Theme 必须包含：中心判断、机制链、关键事实、反向证据、投资含义、验证信号。
3. Reader Report 以 3–5 个核心投资主题组织论证，而不是重复同一组摘要。
4. 财务章节强制形成“变化 → 原因 → 现金流/利润影响 → 估值影响”的桥接。
5. 显式生成 Bull Case、Bear Case 和 Base Case 的核心分歧，不允许只有一句 Variant View。
6. 增加“镜子测试”：用 5 句话以内说明业务本质、护城河、估值、最大风险和动作。
7. 增加公司特异性校验：核心 Theme 必须引用公司/产品/业务/竞争对手实体，禁止全部由通用词组成。
8. 增加 Narrative Quality 动态校验，而不是硬编码 PASS。
9. 保持 v2.1.2 的单一数值真相、Reader/Audit 双层输出、Evidence Roles、Value Binding 与篡改检测不变。

## 设计

### A. Narrative Theme Schema

Research Spec 新增：

```json
"narrative": {
  "themes": [
    {
      "id": "THEME-CAPEX-RETURNS",
      "title": "广告主业强劲，但资本回报决定估值上限",
      "thesis": {"text_template": "...", "value_refs": {}, "evidence_refs": [], "confidence": "medium"},
      "mechanism": [
        {"claim": "...", "evidence_refs": [], "confidence": "high", "implication": "..."}
      ],
      "counter_case": {"text": "...", "evidence_refs": [], "confidence": "medium"},
      "investment_implication": "...",
      "validation_signals": ["...", "..."]
    }
  ],
  "debate": {
    "bull_case": {...},
    "bear_case": {...},
    "base_case": {...},
    "key_disagreement": "..."
  },
  "mirror_test": [
    "这门生意的本质是……",
    "护城河是……",
    "当前价格意味着……",
    "最大的风险是……",
    "因此动作是……"
  ]
}
```

### B. Theme Contract

- Theme 数量：3–5。
- 每个 Theme 至少 2 条 mechanism Claim。
- 每个 Theme 至少 1 个 supports evidence 和 1 个 counter_evidence role。
- 每个 Theme 至少 2 个 validation signals。
- Theme title/thesis 必须包含公司特异性实体或引用 Company Entity Registry。
- Theme 之间不得高度重复；标题 token 重叠超过阈值时 FAIL。
- Theme 必须覆盖：业务/护城河、财务/资本配置、估值/机会成本三类主题。

### C. Company Entity Registry

Spec 新增：

```json
"company_entities": ["Meta", "Facebook", "Instagram", "WhatsApp", "Threads", "Reels", "Reality Labs"]
```

Narrative Themes、Moat、Risks、Opportunity Cost 中至少达到最低实体覆盖。目的是阻止“网络效应、数据、生态、资本”这类可复制到任何公司的模板分析。

### D. Adversarial Debate

借鉴 AI Berkshire 的多视角对抗，但不绑定四大师人格。必须形成：

- Bull Case：市场低估了什么；兑现路径是什么；需要哪些证据。
- Bear Case：市场高估了什么；失败机制是什么；最早会在哪里暴露。
- Base Case：当前最可能路径；核心假设；为什么不是 Bull 或 Bear。
- Key Disagreement：Bull 与 Bear 真正分歧的单一变量。

每个 Case 必须有 Evidence Roles 和至少一个 Compiler-owned value binding。

### E. Causal Financial Bridge

财务模块新增 `causal_bridge`：

```text
Revenue/engagement change
→ cost/capex driver
→ operating margin / FCF effect
→ per-share / valuation implication
```

至少包含一个季度对比和一个资本配置解释。Reader 不再只说“收入强、FCF弱”，必须说明为什么。

### F. Mirror Test

最终报告新增精简“镜子测试”，最多五句，必须覆盖：

1. 生意本质；
2. 护城河；
3. 当前估值；
4. 最大风险；
5. 当前动作。

所有数字必须使用 value_refs；动作必须来自 Compiler。

### G. Reader Renderer

- 一页结论不再在 Overview 中原样重复。
- “三个核心矛盾”升级为“核心投资叙事”，每个 Theme 渲染为 1–2 个连续自然段。
- Overview 只提供行业位置、非共识和 Debate，不重复一页结论。
- 财务章节优先渲染 causal bridge。
- 护城河使用公司实体与具体产品，减少通用四维模板感。
- 估值章节加入 Bull/Bear/Base 核心分歧。
- 最终判决加入 Mirror Test。

### H. Narrative Quality

Verification 新增动态检查：

- `themes_complete`；
- `causal_chains_complete`；
- `adversarial_debate_complete`；
- `company_specificity`；
- `counter_evidence_coverage`；
- `mirror_test_complete`；
- `narrative_redundancy`；
- `numeric_argument_density`。

## 非目标

- 不修改估值公式、场景数值或决策政策；
- 不强制真实并行多 Agent；
- 不模仿巴菲特、芒格等人物口吻；
- 不增加更多顶层研究模块；
- 不降低审计与数据约束；
- 不自动保证假设在经济学上正确。

## 验收标准

1. Spec 缺少 narrative/themes/debate/mirror_test 时 FAIL。
2. Theme 少于 3 个、机制链少于 2 条、没有反向证据或验证信号时 FAIL。
3. Theme 无公司特异性实体时 FAIL。
4. Bull/Bear/Base 任一缺失或没有 value binding 时 FAIL。
5. 财务 causal bridge 不完整时 FAIL。
6. Mirror Test 超过 5 句、缺少估值/风险/动作任一项时 FAIL。
7. Reader Report 不再重复“一页结论”的三条内容到 Overview。
8. Reader Report 必须出现至少 3 个 Theme 标题、Bull/Bear/Base 对抗和镜子测试。
9. Reader Report 中关键财务数字必须被用于因果解释，而不仅存在于表格。
10. Narrative Quality 全部来自真实 validator 结果。
11. Reader、Audit、Bundle、Verification 任一篡改后 verify 失败。
12. 全量 unittest、lint、自测和 Meta 端到端 build/verify 全部通过。

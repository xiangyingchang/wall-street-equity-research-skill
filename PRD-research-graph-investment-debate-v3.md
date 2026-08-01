# PRD：Research Graph、Investment Debate 与 Narrative Synthesis v3

## 状态

实施中 — 2026-08-01

## 背景

v2.1.2 已经解决了报告可信度和可读性之间的冲突：数值由单一 Spec/Bundle 生成，Reader Report 与 Audit Appendix 分离，主报告不再暴露内部 ID。但最新 Meta Reader Report 仍然存在最后一类质量问题：它虽然好读，却仍然主要是“把若干 Claims 按模块顺序串起来”，没有稳定形成真正的投资研究叙事。

具体表现：

1. 同一观点在一页结论、Overview 和模块正文重复出现，缺少推进；
2. 财务数据被正确列出，但没有稳定解释“发生了什么、为什么发生、是否可持续、对估值意味着什么”；
3. 机会成本、护城河和风险容易退化为适用于任何公司的通用模板；
4. Variant View、Bull/Bear 争论和最终裁决过短，没有解释为什么某一方更有说服力；
5. 敏感性分析停留在结果表，没有说明哪些假设真正主导结论；
6. 现有结构是 Fact → Claim → Markdown，缺少 Observation、Hypothesis、Challenge、Resolution 和 Theme 层；
7. 单一 Agent 可以写出逻辑自洽的报告，但不一定主动挑战自己的结论。

AI Berkshire 中值得借鉴的不是“四位大师”的人设，而是三点：

- 多视角独立研究，而不是单一路径；
- 强制 Bull/Bear 对抗和反偏见机制；
- Team Lead 在冲突中做裁决，而不是简单平均观点。

本项目不照搬大师角色，也不依赖特定 Agent 工具；v3 将这些思想抽象为可验证的 Research Graph 和 Investment Debate，并继续保持单一数据真相。

## 根因

v2.1.2 的可信链已经成熟，但研究对象仍然以“孤立 Claim”为基本单元。Renderer 只能把 Claim 组合成段落，无法知道：

- 哪些 Facts 共同形成一个 Observation；
- Observation 支持什么 Hypothesis；
- 哪些反例挑战 Hypothesis；
- 最终如何裁决；
- 该裁决如何影响估值和动作；
- 不同模块应围绕哪几个公司特有的 Theme 推进。

因此真正缺失的是研究中间层，而不是更多模板或更多表格。

## 目标

1. 将研究链路升级为：

```text
Source → Fact → Observation → Hypothesis → Challenge → Resolution → Theme → Narrative → Decision
```

2. 每份报告必须定义 3–5 个公司特有的 Investment Themes，而不是仅按通用模块组织 Claims。
3. 每个 Theme 必须包含：
   - 核心问题；
   - observations；
   - hypothesis；
   - challenge；
   - resolution；
   - decision impact；
   - falsification condition；
   - evidence refs；
   - value refs。
4. 强制生成独立 Bull Case、Bear Case 和 Adjudication；最终裁决必须说明采纳和未采纳的理由。
5. 增加 Sensitivity Explanation：明确 Base IRR 对 revenue、margin、EPS CAGR、exit multiple 等变量的方向、相对重要性和结论影响。
6. Reader Report 以 Themes 推动叙事，减少重复总结和通用模板。
7. Audit Appendix 完整展示 Research Graph、Debate 和 Sensitivity 的结构化对象。
8. 不修改 v2 的事实、估值、决策公式和篡改检测。
9. 不要求运行环境一定支持多 Agent；若支持，可由不同 Agent 独立产生 graph nodes，最终仍必须合并进同一 Spec。

## 设计

### A. Research Graph Schema

Spec 新增：

```json
{
  "research_graph": {
    "themes": [
      {
        "theme_id": "THEME-CAPITAL-RETURNS",
        "title": "AI资本开支能否转化为股东回报",
        "core_question": "高额投入是暂时压低现金流，还是永久抬高资本强度？",
        "observations": [
          {
            "observation_id": "OBS-FCF-COLLAPSE",
            "text_template": "最新季度自由现金流降至 {q2_fcf}。",
            "value_refs": {},
            "evidence_refs": []
          }
        ],
        "hypothesis": {},
        "challenge": {},
        "resolution": {},
        "decision_impact": {},
        "falsification": {},
        "module_links": ["financial_autopsy", "valuation", "risks"]
      }
    ],
    "debate": {
      "bull": {},
      "bear": {},
      "adjudication": {}
    },
    "sensitivity": {
      "drivers": []
    }
  }
}
```

### B. Theme Contract

每个 Theme：

- `theme_id` 使用 `THEME-*`；
- title 和 core question 必须公司特有，禁止通用占位描述；
- 至少 2 个 observations；
- hypothesis、challenge、resolution、decision impact、falsification 均为 evidence-bound claim；
- challenge 必须至少包含一个 `counter_evidence` role；
- resolution 必须同时引用 supports 和 counter_evidence；
- decision impact 必须引用 Bundle 中的动作、IRR、价格或关键模型值；
- module_links 至少覆盖两个模块；
- Theme 之间引用的 Observation ID 不得重复。

### C. Investment Debate

Debate 包含：

- Bull：最强看多论点，而非稻草人；
- Bear：最强看空论点；
- Adjudication：
  - accepted points；
  - rejected/discounted points；
  - decisive evidence；
  - remaining uncertainty；
  - why current action follows。

Bull 与 Bear 均至少包含 3 条独立 arguments，每条绑定 evidence。Adjudication 必须引用双方 argument IDs，不得重新创造第三套无来源观点。

### D. Sensitivity Explanation

每个 driver 包含：

- driver ID；
- variable；
- base assumption path；
- direction；
- importance：high/medium/low；
- mechanism；
- upside case；
- downside case；
- decision consequence；
- evidence refs。

Compiler 不重新做完整 Monte Carlo，但必须解释哪些输入支配 Base IRR 和 target-return price。

### E. Narrative Synthesis

Reader Renderer 使用 Theme 生成“投资叙事”而不是直接堆 Claims：

1. Core question；
2. Evidence-backed observations；
3. Base hypothesis；
4. Strongest challenge；
5. Resolution；
6. Decision impact；
7. What would falsify it。

九模块仍保留，但模块内容优先引用关联 Themes；避免同一观点在一页结论和 Overview 原样重复。

### F. Multi-Agent Adapter（借鉴 AI Berkshire）

新增非强制运行合同：

- business analyst：商业模式和护城河 observations；
- financial analyst：财务和估值 observations；
- industry challenger：竞争与反共识 challenge；
- risk assessor：失败路径和 falsification；
- lead：resolution、debate adjudication、最终 narrative。

如果运行环境支持 subagents，可并行执行；否则单 Agent 必须顺序模拟独立视角。所有输出必须写入同一 `research_graph`，不能直接编辑 Markdown。

### G. Quality Gates

阻断以下情况：

- Theme 少于 3 或多于 5；
- Theme 名称过于通用；
- challenge 没有 counter evidence；
- resolution 未同时处理正反证据；
- Debate 少于 3 条 Bull 或 Bear；
- Adjudication 未引用双方 argument IDs；
- Sensitivity 缺少高重要性 driver；
- Reader 没有 Theme narrative 或 Investment Debate；
- Theme narrative 原样重复 Overview 关键句；
- Audit 缺少 Research Graph；
- Research Graph、Reader、Audit、Bundle 或 Verification 任一篡改。

## 非目标

- 不修改 valuation runtime、payback 或 decision policy；
- 不引入无法复现的 LLM runtime 依赖；
- 不照搬巴菲特/芒格等人格化评分；
- 不把不同 Agent 结论简单平均；
- 不要求所有公司使用同样的 Theme 名称；
- 不自动判断所有经济假设一定正确。

## 验收标准

1. Meta fixture 至少生成 3 个公司特有 Themes。
2. Reader 包含“投资叙事”和“Bull vs Bear 投资辩论”。
3. Reader 的财务、护城河、估值和风险内容能够引用 Theme resolution，而不是通用模板句。
4. Audit 包含完整 Research Graph、Debate、Sensitivity。
5. Bull/Bear 各至少 3 条 argument；Adjudication 引用双方 IDs。
6. 每个 Theme 的 challenge 含 counter evidence，resolution 同时处理正反证据。
7. 至少一个 high-importance sensitivity driver。
8. 修改 graph node、debate、Reader、Audit、Bundle、Verification 任一内容后 verify 失败。
9. 全量 unittest、lint、自测、Meta build/verify 全部通过。
10. 完成后进行独立 code review，重点检查 schema 旁路、重复真相、Renderer 注入和测试虚假 PASS。

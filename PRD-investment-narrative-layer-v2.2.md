# PRD：Investment Narrative Layer v2.2

## 状态

完成 — 2026-08-01

## 背景

v2.1.2 已完成 Reader Report 与 Audit Appendix 分层，但 Meta Reader Report 仍有明显的“AI 摘要感”：同一判断在首页、核心矛盾和 Overview 中重复；财务章节陈列事实多、解释因果少；护城河、风险和机会成本容易落入通用模板；Variant View 只有一句话；关键数字没有被组织成一条有冲突、有机制、有反证的投资故事。

根因不是数值 Compiler 或证据约束，而是 Spec 仍以离散 Claim 为主要叙事单位。Claim 能证明一句话，却不能自然表达一个完整投资主题。

本次同时研究了 `xbtlin/ai-berkshire`，采纳了其方法论中最值得保留的部分：多视角独立判断、Bull/Bear 显式对抗、最终主笔综合、镜子测试、反共识和反面证据。没有引入对特定客户端或真实多 Agent 编排的依赖，也没有模仿具体投资大师的口吻。

## 目标

1. 在 Source → Fact → Claim 与 Reader Report 之间增加 Theme / Narrative 层。
2. 每个核心 Theme 包含中心判断、机制链、关键证据、反向证据、投资含义和验证信号。
3. Reader 以 3–5 个核心主题组织论证，不再重复三条摘要。
4. 财务章节形成“经营变化 → 成本/资本驱动 → 利润率/现金流 → 估值”的因果桥。
5. 显式形成 Bull、Base、Bear 以及唯一核心分歧变量。
6. 增加五句话镜子测试，覆盖业务、护城河、估值、风险和动作。
7. 强制公司特异性实体，阻止可复制到任何公司的模板分析。
8. Narrative Quality 由 Validator 动态计算。
9. 保持 v2.1.2 的单一数值真相、Reader/Audit 分层、Evidence Roles、Value Binding 和篡改检测。

## 已实施

### Narrative Theme Contract

新增 `scripts/report_narrative_v22.py`：

- `company_entities` 至少四个；
- Theme 数量 3–5；
- Theme 类型必须覆盖 business、capital、valuation；
- 每个 Theme 至少两条 mechanism claims；
- 每个 Theme 必须有 counter-case、counter-evidence 和至少两个 validation signals；
- Theme 必须命中公司、产品、业务、技术或竞争对手实体；
- Theme ID 唯一，标题不得高度重复。

### Adversarial Debate

Narrative Spec 必须包含：

- Bull Case；
- Base Case；
- Bear Case；
- key disagreement。

每个 Case 均包含 thesis、Compiler-owned value anchor、path to win 和 earliest failure signal。

### Causal Financial Bridge

新增四段结构：

```text
operating change
→ cost / capex driver
→ margin / FCF effect
→ valuation implication
```

Meta fixture 现在直接解释收入、经营利润、人工智能基础设施、自由现金流和估值口径之间的因果关系。

### Mirror Test

新增严格五句话结构：

1. 生意本质；
2. 护城河；
3. 当前估值；
4. 最大风险；
5. 当前动作。

数字和动作继续通过 `value_refs` 绑定 Compiler。

### Narrative Renderer

新增 `scripts/report_renderer_narrative_v22.py`：

- 将旧“三个核心矛盾”替换成三个完整投资主题；
- Overview 只保留行业位置、非共识和 Bull/Base/Bear Debate；
- 财务章节插入因果桥；
- 最终报告插入镜子测试；
- Audit Appendix 增加 Narrative Theme 和 Debate 定义；
- 保留 Reader/Audit 双层结构和全部底层审计能力。

### Narrative Quality

Verification 新增：

- `themes_complete`；
- `causal_chains_complete`；
- `adversarial_debate_complete`；
- `company_specificity`；
- `counter_evidence_coverage`；
- `mirror_test_complete`；
- `narrative_redundancy`；
- `numeric_argument_density`。

### Skill、文档和 Fixture

- `SKILL.md` 升级至 v2.2；
- 新增 `references/investment-narrative-v2.2.md`；
- Meta fixture 增加 Meta、Facebook、Instagram、WhatsApp、Threads、Reels、Reality Labs 等实体；
- Meta fixture 增加广告机器、人工智能资本回报、价格隐含预期三个主题；
- 新增 `tests/test_narrative_v22.py`；
- CI 增加 v2.2 端到端检查。

## 非目标

- 不修改估值公式、场景数值或决策政策；
- 不强制真实并行多 Agent；
- 不模仿巴菲特、芒格等人物口吻；
- 不增加新的顶层研究模块；
- 不降低审计和来源要求；
- 不自动保证假设在经济学上正确。

## 验证结果

GitHub Actions `Validate` run #254 与最终文档提交后的 run #261：PASS。

- Python syntax：PASS；
- financial rigor / report audit / report lint self-tests：PASS；
- lint fixtures：PASS；
- 全量 unittest：**169 / 169 PASS**；
- v2.2 Meta build：PASS；
- v2.2 Meta verify：PASS；
- Theme 完整性：3 个主题 PASS；
- 财务因果桥：4 个步骤 PASS；
- Bull/Base/Bear Debate：3 个 Cases PASS；
- 公司特异性：7 个实体命中 PASS；
- Counter-evidence：12 个引用 PASS；
- Mirror Test：5 句话 PASS；
- 旧三条摘要重复块已删除：PASS；
- Reader/Audit/Bundle/Verification 一致性与篡改检测：PASS。

## 交付边界

PR #8 尚未合并。Agent 最终审查通过后需要：

1. 将 v2.2、v2.1.2、v2.1.1、v2.1 change log 按版本倒序合并进 `references/change-log.md`；
2. 删除 staged change-log 文件；
3. 保留全部历史记录；
4. retarget/rebase PR #8 到 main；
5. 再次运行完整 CI；
6. 合并后从新的 v2.2 Spec 重新生成 Meta Reader、Audit、Bundle 和 Verification。

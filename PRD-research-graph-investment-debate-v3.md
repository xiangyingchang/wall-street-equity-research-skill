# PRD：Research Graph、Investment Debate 与 Narrative Synthesis v3

## 状态

完成 — 2026-08-01

## 背景与根因

v2.1.2 已经解决单一数值真相、证据追溯和 Reader/Audit 分层，但研究的基本单元仍是孤立 Claim。报告能正确陈述事实，却不能稳定回答：为什么发生、替代解释是什么、哪一方更有说服力、哪些假设真正决定动作。

根因不是 Renderer，而是缺少 Fact 与 Narrative 之间的研究中间层。

AI Berkshire 值得借鉴的是独立视角、对抗分析和 Team Lead 裁决；本项目不复制人格化大师评分，也不依赖特定多 Agent Runtime。

## 目标

```text
Source → Fact → Observation → Hypothesis → Challenge
       → Resolution → Theme → Narrative → Decision
```

要求：3–5 个公司特有 Themes；每个 Theme 有 observations、hypothesis、challenge、resolution、decision impact、falsification；强制 Bull/Bear 与 Lead Adjudication；解释关键敏感变量；Reader 用 Theme 推进叙事；Audit 保存完整图结构；保留 v2.1.2 数值和审计边界。

## 已实施

### Research Graph

新增 `scripts/report_research_graph_v3.py`，支持 `THEME-*`、`OBS-*`、hypothesis、challenge、resolution、decision impact、falsification 和 module links。Challenge 必须含 counter evidence；Resolution 必须同时处理支持和反方证据；Decision impact 必须引用 Bundle。Theme links 必须合法并覆盖九个正式模块。

### Investment Debate

Bull/Bear 各至少三个全局唯一 `ARG-*`。Adjudication 的 accepted/discounted IDs 必须有效、非重叠，并接受双方至少一个观点。遗漏的有效论点采取保守策略自动进入 discounted，并在 Audit 和 quality 中披露。remaining uncertainty 为必填。

### Sensitivity Explanation

每个 `DRV-*` 包含 variable、Assumption JSON Pointer、direction、importance、mechanism、upside/downside、decision consequence 和 evidence refs。至少一个 high driver。路径必须绑定真实 Assumption Registry；兼容别名归一化为 canonical path，未知 ID 直接失败。

Assumption Pointer 输入只允许 `/assumptions/<ASM-ID>/value`，或 Spec 兼容形式 `/assumptions/scenario/<ASM-ID>/value`；Compiler 输出统一归一化为前者。不得通过任意额外路径层级绕过 canonical path 校验。

### Compiler、Renderer 与 Pipeline

新增 `report_compiler_v3.py`、`report_renderer_v3.py`、`report_pipeline_v3.py` 和 `references/research-graph-v3.md`。Reader 模块1改为 Theme narrative；估值部分新增关键假设解释；最终判决前新增 Bull vs Bear；Audit 保存完整 Graph。Audit 表格统一转义。Build 在写文件前执行 Reader/Audit gate；Verification 的 narrative、debate、sensitivity、Reader、Audit 状态由真实检查计算，不再硬编码。

Reader gate 必须显式拒绝 `THEME-`、`OBS-`、`ARG-`、`DRV-` 以及既有审计标识；Reader 的 Audit 指针只使用自然语言，不得点名内部 Registry/Matrix。中文列表拼接不得产生“。；”等重复标点。Audit 必须始终分别披露 accepted、discounted、auto-discounted，即使 auto-discounted 集合为空。

### Multi-Perspective Adapter

定义 business analyst、financial analyst、industry challenger、risk assessor、lead analyst 五个角色。前四者可并行，也可分轮执行；必须独立形成观点，再由 Lead Analyst 裁决。所有结果写入同一 Spec，不机械平均评分。

多视角独立性是研究要求，subagent 不是架构依赖。默认可由主 Agent 分轮完成；只有用户明确要求，或独立调研的收益显著高于 token/延迟成本时才并行调用 subagent。

### Skill Runtime Contract

`SKILL.md` 只保留触发条件、不可违反的边界、执行顺序和交付契约；详细 schema 与边界案例路由到 `references/` 和 PRD，避免每次运行重复加载同一说明。目标是不超过 1,000 tokens，同时不削弱 v3 的 Graph、Evidence、Decision 和双层输出约束。

### Reader Amount Units

Reader 延续既有单位标准：收入、经营利润、FCF、Forward Revenue 等绝对金额使用报告原币种加“亿”，不做跨币种换算；股价、EPS、目标价等每股金额保持原币种每股值。不得输出无法判断量纲的裸绝对金额。

### Company and Horizon Binding

Reader 的公司名、回报年限和回本年限必须来自 Spec/Bundle；基础 Renderer 不得硬编码 Meta、广告/关系链业务描述或 5/10 年标题。公司特有判断必须来自研究对象或 v3 Theme，不得藏在通用 Renderer 中。

## 非目标

不修改估值、回本或动作公式；不照搬大师人格评分；不依赖特定多 Agent Runtime；不声称结构化辩论自动保证假设正确。

## 测试与验证结果

GitHub Actions Validate run #289：PASS。

- Python syntax：PASS；
- financial rigor / audit / lint self-tests：PASS；
- lint fixtures：PASS；
- 全量 unittest：168 / 168 PASS；
- v2.1.2 end-to-end：PASS；
- v3 Meta build / verify：PASS；
- 3 Themes、6 Observations；
- 3 Bull、3 Bear；
- 3 Drivers、2 High；
- Reader Theme narrative / Sensitivity / Debate：PASS；
- Reader 内部 ID 排除：PASS；
- Audit 完整 Graph 与 escaping：PASS；
- build-time Reader/Audit gate：PASS；
- dynamic Verification：PASS；
- Graph/Reader/Audit/Bundle/Verification 篡改检测：PASS。

## 独立 Code Review

发现并修复：

1. Theme links 未保证九模块覆盖；
2. Bull/Bear Argument ID 可能冲突；
3. Adjudication 可能重叠或静默遗漏论点；
4. 中文短 implication 被旧长度门槛误报；
5. Sensitivity path 未绑定真实 Assumption Registry；
6. Fixture 引用不存在 Bundle path；
7. Audit Graph 表格未转义；
8. Build 可能先写出不合格产物；
9. Verification 多项状态硬编码 PASS；
10. v3 Compiler 未明确阻断旧 schema。
11. Reader gate 未显式拦截 v3 内部 ID 前缀；
12. 空 auto-discounted 集合未在 Audit 中显式披露；
13. Assumption Pointer 可携带多余路径层级后被静默归一化。
14. Reader 页尾仍点名内部 Source Registry / Claim-Evidence Matrix；
15. Observation 与风险指标等中文列表拼接产生重复标点，影响连续阅读。
16. v3 专项测试仅直接覆盖 Audit 篡改，Reader/Bundle/Verification/Spec 依赖 v2 间接覆盖；
17. Graph Audit 表格转义缺少 v3 专项回归。
18. `SKILL.md` 重复 PRD 内容，运行时 token 成本过高；
19. subagent 并行被写成默认路径，而 v3 只要求独立视角，不要求特定 Agent Runtime。
20. v2.1.2/v3 Reader 将绝对金额渲染为无单位裸数字，丢失既有“原币种 + 亿”标准。
21. 通用 Reader Renderer 硬编码 Meta、广告网络叙述和 5/10 年期限，Meta fixture 无法发现跨公司错误。

以上均已修复并通过最终 CI。

## 交付边界

PR #9 为 stacked PR。先合并 PR #8，再将 PR #9 rebase/retarget 到 main，重新运行完整 CI。合并前将 staged v3 change log 合入总记录并删除 staged 文件。

# PRD：Research Graph、Investment Debate 与 Narrative Synthesis v3

## 状态

完成 — 2026-08-01

## 背景与根因

v2.1.2 已经解决单一数值真相、证据追溯和 Reader/Audit 分层，但研究的基本单元仍是孤立 Claim。报告能正确陈述事实，却不能稳定回答：为什么发生、替代解释是什么、哪一方更有说服力、哪些假设真正决定动作。

根因不是 Renderer，而是缺少 Fact 与 Narrative 之间的研究中间层。

AI Berkshire 值得借鉴的是独立视角、对抗分析和 Team Lead 裁决；本项目不复制人格化大师评分，也不依赖特定多 Agent Runtime。

## 目标

将研究链路升级为：

```text
Source → Fact → Observation → Hypothesis → Challenge
       → Resolution → Theme → Narrative → Decision
```

要求：

1. 每份报告定义 3–5 个公司特有 Investment Themes；
2. 每个 Theme 包含 observations、hypothesis、challenge、resolution、decision impact、falsification；
3. 强制最强 Bull、最强 Bear 和 Lead Adjudication；
4. 解释决定 Base IRR 与目标回报价格的关键敏感变量；
5. Reader 用 Theme 推进叙事，Audit 保存完整图结构；
6. 保留 v2.1.2 的数值、决策、证据和篡改边界。

## 已实施

### Research Graph

新增 `scripts/report_research_graph_v3.py`：

- `THEME-*`：3–5 个公司特有主题；
- `OBS-*`：每个 Theme 至少两个观察；
- hypothesis；
- challenge，必须含 `counter_evidence`；
- resolution，必须同时处理 supports 与 counter evidence；
- decision impact，必须引用 Bundle；
- falsification；
- module links，必须指向合法研究模块。

### Investment Debate

- Bull 至少三个 `ARG-*`；
- Bear 至少三个 `ARG-*`；
- Argument ID 全局唯一；
- Adjudication 的 accepted/discounted IDs 必须有效、非重叠；
- accepted 必须同时包含 Bull 与 Bear 观点；
- 裁决保留 remaining uncertainty。

### Sensitivity Explanation

每个 `DRV-*` 包含：

- variable；
- assumption JSON Pointer；
- direction；
- importance；
- mechanism；
- upside/downside；
- decision consequence；
- evidence refs。

至少一个 driver 为 high importance。

### Compiler、Renderer 与 Pipeline

新增：

- `scripts/report_compiler_v3.py`；
- `scripts/report_renderer_v3.py`；
- `scripts/report_pipeline_v3.py`；
- `references/research-graph-v3.md`。

v3：

- 强制 `report-spec-v3.0`；
- 生成 `report-bundle-v3.0`；
- Reader 模块1改为 Theme narrative；
- 估值部分新增“哪些假设真正决定估值”；
- 最终判决前新增 Bull vs Bear 投资辩论；
- Audit 保存 Theme、Observation、Argument、Driver 和 evidence role；
- Reader、Audit、Bundle、Verification 继续做确定性重建和篡改校验。

### Multi-Perspective Adapter

Skill 定义五个独立研究角色：

1. business analyst；
2. financial analyst；
3. industry challenger；
4. risk assessor；
5. lead analyst。

有 subagents 时前四者可并行；没有时必须分离轮次执行。所有结果写入同一个 Spec，禁止直接编辑 Markdown或机械平均评分。

## 非目标

- 不修改估值、回本或动作公式；
- 不照搬大师人格和评分；
- 不引入不可复现的 LLM 运行依赖；
- 不声称结构化辩论自动保证经济假设正确。

## 测试与验证结果

GitHub Actions Validate run #271：PASS。

- Python syntax：PASS；
- financial rigor / audit / lint self-tests：PASS；
- lint fixtures：PASS；
- 全量 unittest：**168 / 168 PASS**；
- v2.1.2 end-to-end：PASS；
- v3 Meta build：PASS；
- v3 Meta verify：PASS；
- Research Graph：3 Themes、6 Observations；
- Debate：3 Bull、3 Bear；
- Sensitivity：3 Drivers，其中 2 个 High；
- Reader 包含 Theme narrative、Sensitivity Explanation、Bull vs Bear；
- Reader 不含 Theme/Argument 内部 IDs；
- Audit 包含完整 Research Graph；
- graph/Reader/Audit/Bundle/Verification 篡改检测：PASS。

## 独立 Code Review

实施后进行了单独 Review，发现并修复：

1. Theme module links 未验证合法模块名；
2. Argument ID 仅在单侧去重，可能 Bull/Bear 冲突；
3. Adjudication accepted/discounted 可能重叠；
4. Graph implication 复用旧 Claim 最低长度导致合理短句误报；
5. 测试 Fixture 引用了不存在的 Bundle path；
6. v3 Compiler 未明确阻断旧 schema 输入。

修复后重新跑完整 CI 并通过。

## 交付边界

PR #9 为 stacked PR。先完成并合并 PR #8，再将 PR #9 rebase/retarget 到 main，重新运行完整 CI。合并前将 `references/change-log-v3.0.md` 合入总 change log 并删除 staged 文件。

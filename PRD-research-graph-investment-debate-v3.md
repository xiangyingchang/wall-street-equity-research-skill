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
- module links，必须指向合法研究模块并覆盖九个正式模块。

### Investment Debate

- Bull 至少三个 `ARG-*`；
- Bear 至少三个 `ARG-*`；
- Argument ID 全局唯一；
- Adjudication 的 accepted/discounted IDs 必须有效、非重叠；
- accepted 必须同时包含 Bull 与 Bear 观点；
- 未显式分类的 Argument 采取保守策略自动进入 discounted，并在 Audit 与 quality 中披露；
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

至少一个 driver 为 high importance。Assumption pointer 必须解析到真实 Assumption Registry；历史别名会归一化成 canonical path，未知 ID 直接失败。

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
- Audit 表格统一做 Markdown escaping；
- Reader、Audit、Bundle、Verification 继续做确定性重建和篡改校验；
- build 阶段即执行 Reader/Audit 完整性检查，不再先生成一个自称 PASS 的无效产物；
- Verification 的 narrative、debate、sensitivity、reader、audit 状态由实际结构和渲染检查动态计算，不再硬编码 PASS。

### Multi-Perspective Adapter

Skill 定义五个独立研究角色：

1. business analyst；
2. financial analyst；
3. industry challenger；
4. risk assessor；
5. lead analyst。

有 subagents 时前四者可并行；没有时必须分离轮次执行。所有结果写入同一个 Spec，禁止直接编辑 Markdown 或机械平均评分。

## 非目标

- 不修改估值、回本或动作公式；
- 不照搬大师人格和评分；
- 不引入不可复现的 LLM 运行依赖；
- 不声称结构化辩论自动保证经济假设正确。

## 测试与验证结果

GitHub Actions Validate run #285：PASS。

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
- build-time Reader/Audit gate：PASS；
- dynamic Verification：PASS；
- graph/Reader/Audit/Bundle/Verification 篡改检测：PASS。

## 独立 Code Review

实施后进行了单独 Review，发现并修复：

1. Theme module links 只验证合法性，没有验证九模块覆盖；
2. Argument ID 仅在单侧去重，可能 Bull/Bear 冲突；
3. Adjudication accepted/discounted 可能重叠，且遗漏的论点可能被静默忽略；
4. Graph implication 复用旧 Claim 最低长度导致合理中文短句误报；
5. Sensitivity assumption path 只验证字符串前缀，没有绑定真实 Assumption Registry；
6. Meta fixture 引用了不存在的 Bundle path；
7. Audit Graph 表格未统一转义管道符与换行；
8. v3 build 在渲染不完整时仍可能先写出产物；
9. Verification 的 narrative/debate/sensitivity/reader/audit 状态存在硬编码 PASS；
10. v3 Compiler 未明确阻断旧 schema 输入。

以上问题均已修复，并在最终完整 CI 中通过。

## 交付边界

PR #9 为 stacked PR。先完成并合并 PR #8，再将 PR #9 rebase/retarget 到 main，重新运行完整 CI。合并前将 `references/change-log-v3.0.md` 合入总 change log 并删除 staged 文件。
# PRD：Reader-First Dual-Layer Renderer v2.1.2

## 状态

完成 — 2026-08-01

## 背景

v2.1.1 已经解决单一数值真相、Evidence Role、Value Binding、动态 Research Quality 与篡改检测，但最新 Meta 报告仍然明显难读。问题不在计算层，也不在研究内容不足，而在 Renderer 把“给人读的投资报告”和“给机器审计的结构化底稿”混在同一个 Markdown 中。

主报告在进入 Overview 前连续展示 Build Manifest、Source Registry、Evidence Ledger、Quarterly TTM Bridge、三套 Scenario Assumptions、Decision Policy、Robustness 与 Price Zones。正文又反复输出 `FACT-*`、`BUNDLE:*`、`[supports]` 和 confidence，末尾重复完整 Claim-Evidence Matrix。工程可信度很高，但阅读路径被审计信息打断。

历史报告更好读，是因为它先给结论，再围绕核心矛盾组织论证，并把关键数字嵌入自然语言。v2.1.2 的目标是在不削弱 v2.1.1 可信度的前提下，将 Reader Layer 与 Audit Layer 分离。

## 根因

1. 一个 Renderer 同时承担投资沟通与机器审计两个冲突目标。
2. Source/Fact/Assumption/Claim ID 获得与投资结论相同的视觉权重。
3. Claim block 被固定拆成“判断—投资含义—证据 ID—置信度”卡片，破坏连续论证。
4. Claim-Evidence Matrix 与 Verification 出现在主报告中，重复正文。
5. Pipeline 只生成一个 Markdown，无法同时满足简洁阅读和完整审计。

## 目标

1. 生成独立 Reader Report 与 Audit Appendix。
2. Reader Report 面向投资决策和自然阅读。
3. Audit Appendix 完整保留全部来源、事实、假设、证据与验证结构。
4. Reader Report 不显示内部 ID、Evidence Role、hash 或审计注册表。
5. 关键数字自然嵌入论证。
6. 九个固定模块完整保留。
7. Compiler、Bundle、估值公式和决策政策保持不变。
8. verify 同时校验 Reader、Audit、Bundle 与 Verification。

## 已实施

### 双层 Renderer

新增：

```text
scripts/report_renderer_readable_v212.py
```

提供：

- `render_reader_markdown(bundle)`；
- `render_audit_markdown(bundle)`。

Reader Report 采用“结论—核心矛盾—九模块—主要来源”的阅读顺序；Audit Appendix 复用完整 v2.1.1 审计视图并明确标记为机器审计层。

### 四份生成产物

`report_pipeline_v2.py build` 现在生成：

```text
<report>.md
<report>.audit.md
<report>.md.bundle.json
<report>.md.verification.json
```

Verification 新增：

- `reader_markdown_hash`；
- `audit_markdown_hash`；
- `reader_layer_clean`；
- `audit_layer_complete`。

### Reader Report

Reader Report：

- 首屏展示新资金动作、已有仓位动作、当前价、Base IRR、目标回报、三类关键价格；
- 将程序枚举翻译为自然中文；
- 用三个核心矛盾组织 Overview；
- 在财务、估值、机会成本和仓位模块中直接展示 Bundle 数字；
- 保留精简季度表、Scenario 表、风险表和价格区间；
- 用来源标题生成“主要依据”，不暴露内部 ID；
- 最后仅展示精简来源列表并指向 Audit Appendix。

Reader Report 明确禁止：

- Build Manifest；
- Source Registry；
- Evidence Ledger；
- Claim-Evidence Matrix；
- `FACT-*`、`BUNDLE:*`、`[supports]`；
- Spec/Bundle hash。

### Audit Appendix

Audit Appendix 完整保留：

- Build Manifest；
- Source Registry；
- Evidence Ledger；
- Quarterly TTM Bridge；
- Scenario Assumptions and Valuation；
- Payback；
- Decision Policy、Robustness 与 Price Zones；
- 九模块原始 evidence-bound research；
- Claim-Evidence Matrix；
- Verification。

### Verify

`verify` 现在会：

1. 重新编译 Reader 与 Audit；
2. 比较 Reader Markdown；
3. 比较 Audit Markdown；
4. 比较 Bundle；
5. 比较 Verification；
6. 检查 Reader 是否含审计 token；
7. 检查 Reader 九模块与关键决策数字；
8. 检查 Reader 行数预算；
9. 检查 Audit 完整结构。

### 测试和 CI

更新：

- `tests/test_report_pipeline_v2.py`；
- `tests/test_research_quality_v211.py`；
- `.github/workflows/validate.yml`；
- `SKILL.md` 至 v2.1.2。

新增覆盖：

- Reader 层无内部 ID；
- Audit 层保留全部追溯信息；
- Reader/Audit 分别篡改均失败；
- Verification 同时绑定两个 Markdown hash；
- Reader 长度预算；
- Reader 关键数字覆盖；
- Reader 与 Audit 的确定性输出。

## 非目标

- 不修改估值公式、Scenario 假设或 Action 决策政策；
- 不降低 Source、Evidence、Value Binding、Research Quality 校验；
- 不回到 Markdown-first；
- 不删除 Audit 数据；
- 不引入新研究模块；
- 不自动判断投资假设是否经济上正确。

## 验证结果

GitHub Actions `Validate` run #213：PASS。

- Python syntax：PASS；
- financial rigor / report audit / report lint self-tests：PASS；
- lint fixtures：PASS；
- 全量 unittest：**159 / 159 PASS**；
- v2.1.2 Meta end-to-end build：PASS；
- v2.1.2 Meta end-to-end verify：PASS；
- Reader Report 与 Audit Appendix 均成功生成；
- Reader 九模块与关键决策数字：PASS；
- Reader 无 Source Registry / Claim-Evidence Matrix / FACT / BUNDLE：PASS；
- Audit 包含 Source Registry / Claim-Evidence Matrix / evidence roles：PASS；
- Reader、Audit、Bundle、Verification 篡改检测：PASS。

## 交付边界

PR #8 尚未合并。Agent 测试通过后：

1. 将 v2.1.2、v2.1.1、v2.1 change log 按版本倒序合并入 `references/change-log.md`；
2. 删除 staged change-log 文件；
3. 保留历史记录；
4. 将 PR #8 retarget/rebase 到 main；
5. 再跑完整 CI；
6. 合并后从新的 Spec 重新生成 Meta Reader、Audit、Bundle 与 Verification。

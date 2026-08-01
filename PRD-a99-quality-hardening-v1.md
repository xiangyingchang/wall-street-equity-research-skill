# PRD：a99 历史结构质量加固 v1

状态：完成 — 2026-08-01
基线：`a99c4f6`（2026-07-01）
目标：保留历史报告的阅读节奏，修复明确的契约、来源、流动性和测试缺口。

## 背景

`a99c4f6` 的结论先行、Evidence Ledger、连续论证和固定模块结构更接近用户熟悉的报告。但该版本存在以下可验证问题：

- 10/11 模块的文档和模板口径漂移；
- lint 只检查关键词，真实来源、表格、空模块和重复模块都可能漏过；
- 流动性“按需分析”没有客观触发标准；
- 网络效应护城河没有强制用户规模和变化数据；
- 没有真正的 Python 单元测试；
- 本次行为变更没有形成 PRD 与 change-log 闭环。

## 目标与非目标

### 目标

1. 保留历史 Reader 结构：First-Page Verdict → Evidence Ledger → 连续模块论证 → Final Verdict → Sources。
2. 固定为 9 个模块：删除独立 `Tax Drag & Net Yield`，将税务身份、预扣税和汇率摩擦放入相关机会成本或仓位说明。
3. 让 lint 能识别真实 Markdown 报告的关键结构，而不是只检查标题关键词。
4. 将流动性从固定模块改为有公式、有阈值的条件门禁。
5. 对网络效应护城河强制记录当前用户规模、期间变化和至少一个参与度/商业化指标。
6. 用 unittest 覆盖以上行为，并保留 self-test 与 fixture 验证。

### 非目标

- 不引入 v2/v3 的 Spec、Bundle、Research Graph 或双层 Audit Renderer。
- 不改变旧版估值公式和投资三原则。
- 不在本次改动中加入 Agent provider、模型或耗时 telemetry。

## 目标报告契约

### 顶层结构

报告必须严格按以下顺序出现，且每项恰好一次：

1. First-Page Verdict
2. Evidence Ledger
3. `## 1.` 至 `## 9.`
4. Sources

每个模块必须有实际正文，不能只保留标题或 `TODO` 占位符。模块 1 保留 `Key Forces`，模块 8 保留 `Pre-Mortem` 和 `Action Triggers`，模块 9 保留 `Variant View` 和 `三原则扣问`。

### 来源与 Evidence Ledger

- Sources 区域至少包含一个真实 `https://` 链接；`Company IR`、`latest filing` 等泛化文字不能替代链接。
- Evidence Ledger 必须包含 Markdown 表头和至少一行数据。
- 报告不能以 `TODO`、`TBD` 或未填充占位符交付。

### 流动性门禁

模块 5 必须写明 `流动性结论：不构成约束` 或 `流动性结论：构成约束`。

若构成约束，必须同时给出：

- 90 日平均成交额；
- 本次仓位金额或计划仓位金额；
- 压力参与率；
- 压力退出天数。

统一公式：

```text
压力退出天数 = 仓位金额 / (90 日平均成交额 × 压力参与率)
```

默认压力参与率为 5%。压力退出天数大于 5 个交易日时，判定为流动性约束；缺少仓位金额时只能标记“需人工复核”，不得给出超过 5% 的仓位建议。

### 网络效应门禁

当模块 3 使用“网络效应”或等价表述作为护城河依据时，必须同时出现：

- 当前用户规模或活跃用户指标；
- 同比、环比或明确期间变化；
- 至少一个参与度或商业化指标，例如 DAU/MAU、使用时长、广告展示、价格、ARPU 或转化率。

### Action Triggers

模块 8 的 Action Triggers 必须覆盖价格、估值、经营和 thesis-break/逻辑破坏四类触发器，并至少出现一个量化数字或价格条件。

## 验收标准

- `python3 -m unittest discover -s tests` 至少包含并通过新增的 lint 行为测试。
- `python3 scripts/report_lint.py --self-test` 通过。
- `python3 scripts/report_lint.py --fixtures tests/fixtures` 通过。
- 缺少真实来源 URL、Evidence Ledger 数据行、模块正文、四档贴现表格、流动性条件字段或网络效应用户指标时，lint 必须失败。
- 重复顶层模块、额外顶层模块和遗留 `TODO` 时，lint 必须失败。
- 从全新模板生成的 Meta 报告通过 lint，并保持历史报告的连续论证结构。

## 变更记录要求

实现前先将本 PRD 状态改为“实施中”，并新增 staged change-log；实现和测试完成后，将 PRD 改为“完成”，再整合 change-log。

## 实施结果

- `SKILL.md`、`README.md`、`references/report-contract.md`、`references/full-methodology.md` 和模板统一为 9 模块。
- 删除独立税收模块；保留必要的税务、股息和汇率说明在机会成本与仓位语境中。
- `report_lint.py` 增加精确模块顺序、真实 HTTPS 来源、Evidence Ledger 数据行、无占位符、贴现表格、条件流动性、网络效应用户指标和 Action Triggers 检查。
- 新增 8 个 unittest，覆盖来源、模块、Evidence Ledger、贴现表格、流动性、网络效应和占位符失败路径。
- 使用全新模板生成 Meta 报告，保留历史阅读结构并加入 DAP、广告展示量和平均广告价格变化。

## 验收结果

- `python3 -m py_compile scripts/*.py tests/*.py`：PASS
- `python3 -m unittest discover -s tests`：8/8 PASS
- `python3 scripts/report_lint.py --self-test`：PASS
- `python3 scripts/report_lint.py --fixtures tests/fixtures`：PASS
- Meta 报告 lint：PASS
- TTM 收入、经营利润、利润率、EPS、FCF 和价格线独立复核：PASS

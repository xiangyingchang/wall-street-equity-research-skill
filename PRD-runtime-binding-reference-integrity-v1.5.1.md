# PRD: Runtime Binding、Reference Integrity 与 Period Semantics v1.5.1

## 状态

完成 - 2026-08-01

## 背景

Meta v1.5 报告证明，v1.5 已经把 TTM、Revenue Forecast、Return Pair、Threshold Policy 与 Action Robustness 纳入确定性流程，但“结构存在”仍不等于“报告内容与 runtime 原始输出完全一致”。报告仍出现：

1. Required terminal EPS 与 Required EPS CAGR 不闭合，但 Verification 仍显示 PASS；
2. Scenario Valuation 乘法与 Buy price 有误；
3. Action Matrix 引用未定义 ID，且 Buy/Add 规则未进入 Runtime Evaluation；
4. Canonical Registry 与 Action Evaluation 存在 MODEL ID 命名漂移；
5. Revenue 算术正确，但 YoY 使用错误基期，Assumption mode/value/period 也可能不匹配；
6. Derived Values 声称引用若干 FACT IDs，但这些 ID 并不存在；
7. 市值 reconciliation 只在文字中声称存在；
8. tax、shares、EPS CAGR、dividend、multiple、safety margin 等仍以裸数字进入模型；
9. Forward Basis 把历史 Adjustment IDs 当作直接公式输入；
10. Checker 没有把 Markdown 字段与原始 Runtime JSON 逐字段绑定。

根因：v1.5 建立了输入与决策对象，但没有建立全局 ID 图、runtime artifact 强绑定、期间语义和所有决策输入的来源闭包。

## 目标

1. 所有 `FACT/DERIVED/MODEL/ASM/THR/B/BR/REV/RUN` 定义与引用闭合；
2. Runtime 输出生成稳定 artifact hash，报告字段与 artifact 逐字段匹配；
3. Scenario Valuation 由 runtime 生成；
4. Revenue Forecast 校验 forecast/base period、mode 与 Assumption；
5. 所有决策输入必须引用 Value ID 或 Assumption ID；
6. Action Matrix 全部 executable rules 必须进入 Evaluation；
7. Point-in-time market cap 必须有结构化 share reconciliation；
8. Forward Basis 只能引用实际进入公式的 Bridge/Assumption；
9. Verification PASS 必须来自实际命令结果。

## 已实施

### Runtime Artifact Envelope

新增 `scripts/integrity_common.py`：

- canonical JSON 序列化；
- SHA-256 `artifact_hash`；
- `schema_version`、`runtime_name`、`artifact_id`、`input_refs`、`inputs`、`outputs` 统一 envelope；
- `RUN-*` artifact ID 约束。

新增 CLI：

```bash
python3 scripts/report_integrity_v151.py wrap-artifact --input wrap.json --output RUN-X.json
```

### Scenario Valuation Runtime

新增：

```bash
python3 scripts/report_integrity_v151.py scenario-value --input scenario.json --output RUN-SCENARIO-X.json
```

确定性计算：

```text
forward reference value = metric value × reference multiple
buy price = target-return price × (1 - safety margin)
```

Buy price 不再从 forward reference value 机械打折。

### Runtime/Reference Integrity Checker

新增 `scripts/integrity_checker.py` 与：

```bash
python3 scripts/report_integrity_v151.py check <report.md> --artifacts-dir <dir>
```

检查：

- 全局 ID Graph；
- Value prefix 与 Kind；
- Derived input IDs 真正存在；
- Runtime Artifact Manifest、文件、ID 与 hash；
- Revenue/EPS/Return Pair/Scenario Valuation 字段与 artifact outputs 一致；
- YoY/QoQ base-period 语义；
- Revenue row 与 Assumption mode/base/forecast period 一致；
- Assumption closure；
- Forward Basis 不得引用历史 Adjustment IDs；
- Action Matrix 与 Evaluation Rule ID 集合一致；
- Point-in-Time Share Reconciliation 完整；
- Verification 中新增的完整性项目必须存在且 PASS。

### 模板与 Skill

- `SKILL.md` 升级至 `1.5.1`；
- `templates/full-report.md` 升级至 `full-report-v1.5.1`；
- 新增 Generation Manifest；
- 新增 Point-in-Time Share Reconciliation；
- 扩展 Scenario Assumption Registry：Scope、Mode、Base period、Forecast period、Input role；
- Revenue/EPS/Return Pair/Scenario Valuation 表新增 Assumption IDs 与 Runtime Artifact IDs；
- Action Matrix 新增 Rule ID，并要求 Buy/Add/Hold/Reduce/Sell 完整进入 Evaluation；
- 新增 Runtime Artifact Manifest；
- 新增 `references/runtime-binding-integrity.md` 权威合同。

### 测试

新增 `tests/test_report_integrity_v151.py`，覆盖：

- artifact hash 确定性；
- Scenario Valuation 公式；
- Return Pair terminal EPS/CAGR 不闭合；
- Scenario multiplication 错误；
- 未定义 ID；
- Action rule 遗漏；
- 错误 YoY 基期；
- Forward Basis 使用历史 Adjustment；
- artifact 文件缺失/hash 不一致。

Meta v1.5 报告已被新 checker 人工回归拒绝；其关键失败模式均有自动化测试。

## 不在范围内

- 不抓取外部数据；
- 不自动选择经济上最合理的假设；
- 不实现完整 DCF/Monte Carlo；
- 不改变九个顶层模块；
- 不替代人工投资判断；
- 不要求旧版报告自动迁移。

## 验证结果

GitHub Actions `Validate` run #94：PASS。

- Python syntax：PASS；
- financial rigor self-test：PASS；
- report audit self-test：PASS；
- report lint self-test：PASS；
- lint fixtures：PASS；
- 全量 unittest：**127 / 127 PASS**；
- 新增 v1.5.1 tests：**10 / 10 PASS**；
- Template/new-report recognition：PASS；
- `29.24 × 20` Scenario runtime 输出 `584.8000`：PASS；
- Buy price 使用 target-return price：PASS；
- Return Pair 不闭合 negative test：PASS；
- undefined ID / missing Rule ID / bad YoY period / historical Adjustment negative tests：PASS；
- artifact missing/hash mismatch negative tests：PASS。

## 交付边界

PR #6 尚未合并。Agent 审查通过后需：

1. 将 `references/change-log-v1.5.1.md` 插入 `references/change-log.md` 顶部；
2. 删除 staged change-log 文件；
3. 保留全部历史记录；
4. 再跑完整 CI；
5. 合并后从干净 v1.5.1 模板重新生成 Meta 报告及 runtime artifact 目录。

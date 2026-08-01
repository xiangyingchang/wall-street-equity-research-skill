# PRD: Runtime Binding、Reference Integrity 与 Period Semantics v1.5.1

## 状态

实施中 - 2026-08-01

## 背景

Meta v1.5 报告证明，v1.5 已经把 TTM、Revenue Forecast、Return Pair、Threshold Policy 与 Action Robustness 纳入确定性流程，但“结构存在”仍不等于“报告内容与 runtime 原始输出完全一致”。最新报告仍出现：

1. Return Pair 表中的 Required terminal EPS 与 Required EPS CAGR 互相不闭合，说明 Agent 复制或字段映射错误，但 Verification 仍显示 PASS。
2. Base Forward reference value 的乘法与 Buy price 不精确，说明 Scenario Valuation 仍由 Agent 手填。
3. Action Matrix 引用了不存在的 `THR-ADD-PRICE`、`FACT-CONSECUTIVE-FCF-Q`；Current Action Evaluation 又遗漏 Buy/Add 规则。
4. Canonical Registry 使用 `MODEL-BULL-FORWARD-VALUE`，Action Evaluation 却声明使用 `MODEL-BULL-FAIR-VALUE`，跨表 ID 不一致。
5. Revenue Bridge 的算术正确，但 `yoy` 行可能引用错误基期；Assumption ID 的 growth mode/value/period 也可能与预测行不一致。
6. Derived Value 声称引用若干 FACT IDs，但对应 FACT 行并不存在；目前没有全局引用图。
7. Evidence Ledger 声称存在 point-in-time share reconciliation，但报告中没有可验证的 reconciliation 表。
8. EPS Bridge、Return Pair、Scenario Valuation 中仍有 tax rate、share count、EPS CAGR、dividend yield、reference multiple、safety margin 等裸数字，没有完整 Assumption ID。
9. Forward EPS Basis 仍把历史 Adjustment IDs 当作直接数学输入，形成虚假追溯链。
10. Checker 对 Runtime 表格与原始 JSON 的逐字段绑定不足，导致格式 PASS 掩盖字段复制错误。

根因：v1.5 建立了输入与决策对象，但尚未建立“所有 ID 的全局引用图”“runtime artifact 与报告表格的强绑定”“期间语义”和“所有决策输入的来源闭包”。

## 目标

1. 建立全报告 ID Graph，所有 `FACT/DERIVED/MODEL/ASM/THR/B/BR/REV/RUN` 定义与引用必须闭合。
2. Runtime 输出生成稳定 artifact hash；报告表格必须声明并匹配对应 artifact，阻止手工复制错误。
3. Scenario Valuation 由确定性 runtime 生成 forward reference value、target-return price、buy price 和 stress price。
4. Revenue Forecast 强制校验 forecast period、base period、mode 与 Assumption 的语义一致性。
5. 新报告所有 valuation/action 数字输入必须引用 Value ID 或 Assumption ID，禁止无来源裸数字。
6. Action Matrix 中所有未来动作都必须有完整、可求值规则；Runtime Evaluation 不得遗漏 Matrix 中的规则。
7. Point-in-time market-cap calculation 必须有 share reconciliation 结构，不得仅用文字声称。
8. Forward Basis 的 provenance 只能引用实际进入公式的 Bridge/Assumption，不得把历史 Adjustment IDs 伪装成数学输入。
9. Verification PASS 必须基于实际 checker/runtime 结果与 artifact hash，不接受手填 PASS。

## 改动范围

### A. Runtime Artifact Envelope

所有新 runtime 命令支持 JSON 输入，并输出：

- `schema_version`；
- `runtime_name`；
- `artifact_id`；
- `input_refs`；
- `inputs`；
- `outputs`；
- `artifact_hash`（canonical JSON SHA-256）。

报告引用 artifact ID 与 hash；checker 重新计算表格关键字段与 hash。

### B. Scenario Valuation Runtime

新增确定性命令：

```bash
python3 scripts/report_integrity_v151.py scenario-value --input scenario-value.json
```

输出：

- metric value；
- reference multiple；
- forward reference value；
- target-return price；
- safety margin；
- buy price；
- stress/reference role；
- artifact hash。

### C. Global ID Graph

新增 checker 收集定义与引用：

- `FACT-*`、`DERIVED-*`、`MODEL-*`；
- `ASM-*`；
- `THR-*`；
- `B-*`、`BR-*`、`REV-*`；
- `RUN-*` artifact。

拦截：未定义引用、重复定义、前缀/Kind 不匹配、跨表命名漂移、关键 orphan ID、Action Matrix 规则未进入 Evaluation。

### D. Runtime Table Binding

新增 Runtime Artifact Manifest：

| Artifact ID | Runtime | Input refs | Output fields | Artifact hash | Report section |

Checker 至少逐字段核对：

- TTM Derivation；
- Revenue Forecast；
- EPS Bridge；
- Return Pair；
- Scenario Valuation；
- Action Evaluation；
- Robustness。

### E. Revenue Period Semantics

Revenue row 必须声明：

- forecast period；
- base period；
- mode；
- growth/value Assumption ID；
- runtime artifact ID。

规则：

- `yoy` 的 base period 必须是上一年同季度；
- `qoq` 的 base period 必须是上一季度；
- Assumption 的 mode、value、scope、forecast period 必须匹配；
- guide/consensus/explicit 必须保留 source/as-of/rationale。

### F. Assumption Closure

Scenario Assumption Registry 增加：

- scope；
- mode；
- base period；
- forecast period；
- input role。

必须注册：tax rate、diluted shares、EPS CAGR、dividend assumption、exit PE、reference multiple、safety margin、other income。

### G. Action Completeness

- Buy/Add/Hold/Reduce/Sell 中所有声明为 executable 的规则必须进入 runtime input。
- Matrix 中引用的 Value/Threshold ID 必须存在。
- `N/A because current action is not X` 不得代替未来规则。
- Evaluation rule IDs 必须与 Action Matrix Rule IDs 一一对应。

### H. Share Reconciliation

新增 Point-in-Time Share Reconciliation：

- point-in-time shares；
- weighted-average diluted shares；
- difference；
- source/date；
- market-cap calculation basis。

### I. 文档、模板、测试

更新：

- `SKILL.md` 到 v1.5.1；
- `templates/full-report.md`；
- `references/input-decision-robustness.md`；
- 新增 `references/runtime-binding-integrity.md`；
- 新增 checker/runtime 与测试；
- CI 纳入新测试。

## 不在范围内

- 不抓取外部数据；
- 不自动选择经济上最合理的假设；
- 不实现完整 DCF/Monte Carlo；
- 不改变九个顶层模块；
- 不替代人工投资判断；
- 不要求旧版历史报告全部迁移。

## 验证标准

1. Return Pair 中 Required terminal EPS 与 Required CAGR 不闭合时 FAIL。
2. `29.24 × 20 = 582` 必须 FAIL；Scenario runtime 应输出约 584.8（按精确 input 输出）。
3. 缺失 `THR-ADD-PRICE`、`FACT-CONSECUTIVE-FCF-Q` 必须 FAIL。
4. `MODEL-BULL-FORWARD-VALUE` 与 `MODEL-BULL-FAIR-VALUE` 命名漂移必须 FAIL。
5. Action Matrix 存在 Add/Buy 规则但 Evaluation 缺失时 FAIL。
6. Q3 2026 使用 Q2 2026 作为 YoY 基期必须 FAIL。
7. Revenue row 引用的 Assumption mode/value/period 不一致必须 FAIL。
8. Derived inputs 引用不存在的 FACT IDs 必须 FAIL。
9. 只有“见 reconciliation”文字但无表格时 FAIL。
10. tax/share/EPS CAGR/dividend/multiple/safety-margin 等决策输入无 ASM ID 时 FAIL。
11. Forward Basis 将历史 Adjustment IDs 作为直接输入时 FAIL。
12. Artifact hash 或关键输出字段与报告表格不匹配时 FAIL。
13. Meta v1.5 报告作为 negative fixture 必须被新 checker 拒绝。
14. Python syntax、全量 unittest、lint fixtures、diff check PASS。

# PRD：Research Quality Binding v2.1.1

## 状态

完成 — 2026-08-01

## 问题定义

v2.1 已经补回九模块、Source Registry、Evidence Ledger、Claim-Evidence Matrix 和结构化 Research Layer，但 code review 发现系统仍主要保证“对象存在”，尚未充分保证“数字与论证真正融合、证据角色明确、验证结果真实计算”。

核心问题：

1. Research 只能写无数字文本，缺少 `value_refs` 与编译期插值。
2. `evidence_refs` 只验证 ID/path 存在，不区分 supports/context/counter-evidence。
3. `research_quality` 与 Markdown Verification 被硬编码为 PASS/True。
4. Dot-separated Bundle path 对包含小数点的 key 不稳定。
5. 风险 confidence、rank、Source scope 和 Markdown table escaping 校验不足。
6. 测试偏重模块存在性，缺少 value binding、evidence role、动态 verification 与路径安全测试。

## 目标

1. 新增 `text_template + value_refs`，正文能够引用 Compiler-owned 数字。
2. Evidence Ref 升级为 `ref + role`。
3. 每个关键 Claim 至少包含一个 supports。
4. Bundle value path 使用 JSON Pointer。
5. Research Quality 由 validator 实际生成。
6. 风险 confidence/rank、Source scope、Markdown escaping 全部进入硬校验。
7. 增加端到端与负向回归测试。

## 已实施

### Value Binding

Claim 支持：

```json
{
  "text_template": "当前价格对应 Base IRR 为 {base_irr}，低于目标回报 {target_return}。",
  "value_refs": {
    "base_irr": {"path": "/decision/valuation/base_irr", "format": "percent"},
    "target_return": {"path": "/decision/valuation/target_return", "format": "percent"}
  }
}
```

实现：

- `text_template` / `claim_template`；
- placeholders 与 `value_refs` 一一匹配；
- JSON Pointer path；
- money/percent/multiple/number/integer/text format；
- 编译时插值；
- 未绑定数字继续阻断。

### Typed Evidence Roles

支持：

```json
{"ref": "FACT-Q2-26-FCF", "role": "supports"}
{"ref": "SRC-META-Q2-2026", "role": "context"}
{"ref": "BUNDLE:/scenarios/bull/returns/irr/irr_pct", "role": "counter_evidence"}
```

规则：

- role 只能是 supports/context/counter_evidence；
- 每个 Claim 至少一个 supports；
- Renderer 和 Claim-Evidence Matrix 显示证据角色。

### JSON Pointer

新增 JSON Pointer walker，支持包含小数点的 key，例如：

```text
/derived/payback_required_growth/0.094
```

Value refs 强制使用 JSON Pointer。

### Dynamic Research Quality

Bundle 实际生成：

- modules count；
- claim count；
- supporting refs count；
- bound values count；
- source count；
- numeric safety status。

Verification 与 Markdown 从该对象动态渲染，不再硬编码 PASS。

### Additional Validation

- risk confidence 必须为 low/medium/high；
- risk rank 必须唯一且从一开始连续；
- Source scope 必须覆盖 Fact category；
- Markdown table cell 统一转义 pipe 和 line break；
- Verification 文件与重新编译结果完整比较。

### 文档和版本

- Skill 升级至 `2.1.1`；
- Spec/Bundle/Verification schema 升级至 v2.1.1；
- 新增 `references/research-quality-binding-v2.1.1.md`；
- CI 增加 value-binding 和 evidence-role 端到端断言。

## 不在范围内

- 不自动判断 Claim 与 evidence 在经济学上一定正确；
- 不使用 LLM judge 作为硬门禁；
- 不改变 Single-Source Compiler；
- 不新增研究模块；
- 不实现完整组合优化。

## 验证结果

GitHub Actions `Validate` run #190：PASS。

- Python syntax：PASS；
- financial rigor / audit / lint self-tests：PASS；
- lint fixtures：PASS；
- 全量 unittest：**155 / 155 PASS**；
- v2.1.1 end-to-end build：PASS；
- v2.1.1 end-to-end verify：PASS；
- Meta 正文插入 Base IRR `5.51%`：PASS；
- Meta 正文插入目标回报 `9.40%`：PASS；
- Meta 正文插入 target-return price `$456.67`：PASS；
- Evidence roles rendered：PASS；
- Research quality：9 modules、37 claims、88 supporting refs、3 bound values、9 sources；
- missing value ref / invalid JSON Pointer / missing supports / invalid role：negative tests PASS；
- invalid risk confidence / duplicate rank / source-scope mismatch：negative tests PASS；
- Markdown table escaping：PASS；
- Markdown / Bundle / Spec / Verification tamper detection：PASS。

## 交付边界

PR #8 仍未合并。Agent 审查通过后：

1. 先确认 PR #7 已进入 main；
2. 将 PR #8 rebase/retarget 到 main；
3. 把 v2.1 与 v2.1.1 change-log 按顺序插入总 change-log；
4. 删除 staged change-log 文件；
5. 再跑完整 CI；
6. 合并后从全新 v2.1.1 Spec 重新生成 Meta 四件套。

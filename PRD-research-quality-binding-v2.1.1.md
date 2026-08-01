# PRD：Research Quality Binding v2.1.1

## 状态

实施中 — 2026-08-01

## 背景

v2.1 已经补回九模块、Source Registry、Evidence Ledger、Claim-Evidence Matrix 和结构化 Research Layer，但 code review 发现系统仍主要保证“对象存在”，尚未充分保证“数字与论证真正融合、证据角色明确、验证结果真实计算”。

核心问题：

1. Research 只能写无数字文本，缺少 `value_refs` 与编译期插值，导致正文仍然难以用 IRR、目标回报、利润率、价格等关键数字完成论证。
2. `evidence_refs` 只验证 ID/path 存在，不区分 supports/context/counter-evidence，无法表达证据在论证中的角色。
3. `research_quality` 与 Markdown Verification 被硬编码为 PASS/True，而不是由实际检查结果生成。
4. `BUNDLE:<dot.path>` 对包含小数点的 key 不稳定，应该迁移到 JSON Pointer 风格路径。
5. 风险 confidence、rank 唯一性/连续性、Source scope 与 Fact 语义匹配、Markdown 表格转义等边界校验不足。
6. 现有测试偏重模块和行数存在性，缺少 value binding、evidence role、动态 verification 与路径安全测试。

## 目标

1. 新增 `text_template + value_refs`，由 Renderer 插入 Compiler-owned 数值，正文可以自然完成数字论证，但不能手写新数字。
2. 将 Evidence Ref 升级为结构化对象：`ref + role`，支持 `supports | context | counter_evidence`。
3. 关键 Claim 至少有一个 supports；Moat/Valuation/Final Verdict 等关键模块必须包含限制或反向证据。
4. Bundle path 改为 JSON Pointer：`BUNDLE:/scenarios/base/...`，不再用点号解析。
5. Research Quality checks 由 validator 实际计算并写入 Bundle/Verification，不再硬编码。
6. 风险 confidence 必须枚举合法，rank 必须唯一且连续。
7. Source scope 必须覆盖 Fact metric category；关键财务 Fact 继续要求 Tier 1。
8. 所有 Markdown table cell 统一转义，避免 `|`、换行破坏表格。
9. 增加端到端和负向测试，确保报告正文可引用数值、证据角色闭合、Verification 来源真实。

## 设计

### Claim v2.1.1

```json
{
  "text_template": "当前价格对应 Base IRR 为 {base_irr}，低于目标回报 {target_return}。",
  "value_refs": {
    "base_irr": {
      "path": "/decision/valuation/base_irr",
      "format": "percent"
    },
    "target_return": {
      "path": "/decision/valuation/target_return",
      "format": "percent"
    }
  },
  "evidence_refs": [
    {"ref": "BUNDLE:/decision/valuation/base_irr", "role": "supports"},
    {"ref": "SRC-US-TREASURY", "role": "context"}
  ],
  "confidence": "high",
  "implication": "新资金不应主动进入。"
}
```

规则：

- `text_template` 中所有 `{placeholder}` 必须在 `value_refs` 中定义；
- `value_refs.path` 必须使用 JSON Pointer；
- format 仅允许 money/percent/multiple/number/integer/text；
- Renderer 插值后生成最终 text；
- 原始模板除 placeholder 外不得包含未绑定数值；
- evidence 至少一个 supports。

### Evidence Role

```json
{"ref": "FACT-Q2-26-FCF", "role": "supports"}
{"ref": "SRC-META-Q2-2026", "role": "context"}
{"ref": "BUNDLE:/scenarios/bull/returns/irr/irr_pct", "role": "counter_evidence"}
```

### Research Quality Result

Bundle 写入：

```json
"research_quality": {
  "status": "PASS",
  "checks": {
    "modules_complete": {"status": "PASS", "count": 9},
    "evidence_closure": {"status": "PASS", "supporting_refs": 42},
    "value_binding": {"status": "PASS", "bound_values": 18},
    "source_registry": {"status": "PASS", "sources": 9},
    "numeric_reference_safety": {"status": "PASS"}
  }
}
```

Verification 和 Markdown 摘要都从该对象渲染，不允许固定写 PASS。

## 不在范围内

- 不自动判断 Claim 与证据在经济学上一定正确；
- 不引入 LLM judge 作为硬门禁；
- 不改变 v2 的 Single-Source Compiler；
- 不增加新的研究模块；
- 不实现完整组合优化。

## 验证标准

1. 带 `value_refs` 的正文能正确渲染百分比、货币和倍数。
2. placeholder 缺失、未使用或 path 不存在时 build FAIL。
3. 手写未绑定数字仍 FAIL。
4. 旧 `BUNDLE:derived...0.094` dot path FAIL；JSON Pointer 可正确读取 `0.094` key。
5. Claim 无 supports evidence 时 FAIL。
6. 非法 evidence role 时 FAIL。
7. 风险 confidence 非枚举值时 FAIL。
8. 风险 rank 重复或不连续时 FAIL。
9. Fact 引用 scope 不覆盖 metric category 的 Source 时 FAIL。
10. Markdown 中 `|` 和换行被安全转义。
11. research_quality 与 verification 不得硬编码；篡改后 verify FAIL。
12. Meta fixture 的关键估值段落必须直接包含编译插入的 Base IRR、目标回报和 target-return price。
13. 全量 CI、unittest、build、verify PASS。

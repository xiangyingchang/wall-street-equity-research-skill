# PRD：Evidence-Bound Research Layer v2.1

## 状态

完成 — 2026-08-01

## 问题定义

v2.0 已经解决数值重复、隐藏输入、Legacy 表冲突和 Markdown 篡改，但首份 Meta v2 报告退化成计算摘要：九个研究模块过薄、模块 4 缺失、来源不结构化、场景输入缺少解释、研究判断没有证据绑定。

根因不是 Single-Source Compiler 错了，而是架构只建立了“数值单一真相”，没有建立“研究论证合同”。

```text
Typed Spec
→ Deterministic Analytical Bundle
→ Evidence-bound Research Layer
→ Complete Markdown Report
```

数值、价格、动作和验证继续由 Compiler 控制；定性研究采用结构化 Claim，并引用 Source、Fact 或 Bundle 路径。

## 目标

1. 升级为 `report-spec-v2.1` / `report-bundle-v2.1`。
2. 新增结构化 `SRC-*` Source Registry。
3. 每个 Fact 必须引用 Source IDs。
4. 强制完整九模块，模块 4 不得缺失。
5. 每个关键判断必须包含 claim/text、evidence_refs、confidence，必要时包含 implication 和 counter-evidence。
6. 自由研究文字不得创造未绑定的价格、百分比、倍数、阈值或动作。
7. 生成 Source Registry、Evidence Ledger、Quarterly TTM Bridge、Scenario Assumptions、完整九模块和 Claim-Evidence Matrix。
8. 保持 Spec、Bundle、Markdown、Verification 的确定性和篡改检测。
9. 使用完整 Meta fixture 进行端到端验证，避免再次退化为计算摘要。

## 已实施

### Research Compiler

新增：

- `scripts/report_research_v21.py`
- `scripts/report_compiler_v21.py`

实现：

- 结构化 Source 校验；
- Fact-to-Source 闭包；
- Source/Fact/Bundle evidence path 校验；
- 九模块完整性；
- Claim 深度与置信度；
- 护城河维度、反向证据和趋势；
- 风险机制、领先指标、触发器和缓释因素；
- 未绑定数字拦截；
- Research Quality 状态写入 Bundle。

### Renderer 与 Pipeline

更新：

- `scripts/report_renderer_v2.py`
- `scripts/report_pipeline_v2.py`

生成内容包括：

1. Build Manifest；
2. First-Page Verdict；
3. Source Registry；
4. Evidence Ledger；
5. Quarterly TTM Bridge；
6. Scenario Assumptions and Valuation；
7. Payback；
8. Decision Policy；
9. 完整模块 1-9；
10. Claim-Evidence Matrix；
11. 自动 Verification 摘要。

Verify 会阻止模块缺失、薄叙事占位、Legacy 表和派生产物篡改。

### 九模块合同

- Overview：thesis、至少三个 key forces、variant view；
- Financial Autopsy：revenue、margin、cash flow/Capex、one-offs；
- Moat：至少四个维度、评分、证据、反向证据、trajectory；
- Valuation：Base解释、reverse expectations、payback、关键假设；
- Risks：至少三个风险及 mechanism、indicators、trigger、mitigant；
- Growth Limits：增长引擎、至少两个约束、增长上限；
- Opportunity Cost：无风险基准、hurdle、指数和同业；
- Positioning：新资金、存量仓位、组合约束、执行；
- Final Verdict：总结、三原则、confidence boundary、反证条件。

### 合同与测试

更新/新增：

- `SKILL.md` → v2.1.0；
- `references/research-layer-v2.1.md`；
- `tests/meta_v21_factory.py`；
- `tests/meta_v21_spec.py`；
- `tests/test_report_pipeline_v2.py`；
- CI v2.1 真实 build + verify。

## 不在范围内

- 自动抓取资料；
- 自动保证投资假设正确；
- 完整 DCF 或 Monte Carlo；
- 组合级优化；
- 旧 v1.x 报告迁移。

## 验证结果

GitHub Actions Validate run #164：PASS。

- Python syntax：PASS；
- financial rigor / audit / lint self-tests：PASS；
- lint fixtures：PASS；
- 全量 unittest：**143 / 143 PASS**；
- v2.1 end-to-end build：PASS；
- v2.1 end-to-end verify：PASS；
- Source Registry / Evidence Ledger / TTM Bridge / Scenario Assumptions / Claim-Evidence Matrix：PASS；
- 模块 1-9 完整，模块 4 存在：PASS；
- Markdown、Bundle、Spec 篡改检测：PASS；
- 缺失模块、缺失 evidence、无效 source、未绑定数字：negative tests PASS；
- guide-high 与 midpoint 区分：PASS；
- Legacy Compatibility 与薄叙事占位缺失检查：PASS；
- 生成报告超过最小完整研究结构，不再是计算摘要：PASS。

## 交付边界

PR #8 是叠加在 PR #7 之上的研究层升级。Agent 应先审查并合并 PR #7，再将 PR #8 变基或合并；随后整合 change log、再次跑 CI，并用全新的 v2.1 Spec 重新生成 Meta 报告。

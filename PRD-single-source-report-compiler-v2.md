# PRD：Single-Source Report Compiler v2

## 状态

完成 — 2026-08-01

## 问题定义

v1.1-v1.5.1 持续修复了算术、口径、ID、Runtime、阈值和验证问题，但每一版仍可能出现新的不一致。根因不是缺少更多 Checker，而是错误的信任边界：

```text
Agent 手写事实/假设
→ Runtime 计算
→ Agent 把结果复制进 Markdown
→ 多个 Checker 再从 Markdown 反向猜测一致性
```

同一经济概念会同时存在于 Registry、Runtime 表、Legacy 表、价格区间和结论文字中。只要允许重复书写，就必然继续出现字段复制错误、语义漂移、隐藏输入和规则遗漏。

## 核心方案

将系统从 Markdown-first 改为 Compiler-first：

```text
一个 report-spec-v2 JSON
→ 一个确定性 report-bundle-v2
→ 一个编译生成的 Markdown
→ 一个编译生成的 Verification Manifest
```

唯一允许人工编辑的是 Spec。Markdown、Bundle 和 Verification 都是派生产物，任何手工修改都会导致 verify 失败。

## 目标

1. 单一结构化输入，不再手工复制 Runtime 表。
2. 所有事实、假设、场景、Policy、叙事和来源只在 Spec 中定义一次。
3. TTM、Revenue、EPS、IRR、Reverse Expectations、价格、Payback、Decision、Robustness、Price Zones 由 Compiler 统一生成。
4. 新报告彻底删除 Legacy Compatibility Tables。
5. Bear/Base/Bull 只能引用自身或 Global assumptions。
6. Revenue 使用 mode-specific schema，`guide_high` 与 `guide_midpoint` 不再混用。
7. uncertainty/tolerance 只能存在于 typed Fact/Policy，不能从叙事中追加。
8. Decision Policy 必须同时覆盖 valuation、operating、thesis break。
9. 区分 new-money action 与 existing-position action。
10. Base IRR 明显低于 hurdle 时，existing-position action 不得仅因经营指标正常而返回 HOLD。
11. 10 年回本由确定性求根生成。
12. Build/Verify 能检测 Spec、Bundle 或 Markdown 的任何未同步修改。
13. 真实 Meta fixture 作为端到端 golden test，而不是只写合成单元测试。

## Report Spec v2

顶层结构：

```json
{
  "schema_version": "report-spec-v2",
  "report": {},
  "facts": {},
  "quarterly_series": {},
  "assumptions": {},
  "scenarios": {},
  "decision_policy": {},
  "portfolio": {},
  "narrative": {},
  "sources": []
}
```

### Facts

每个 Fact 必须包含 value、unit、period/as_of、source、tier、confidence；需要缓冲时显式写 uncertainty。

### Assumptions

每个 Assumption 必须包含：

- scope：`global|bear|base|bull`
- role
- rationale
- confidence
- scalar value 或 mode-specific fields

场景只能引用自己的 scope 或 global scope。

### Revenue modes

- `guide_midpoint`：low/high/source
- `guide_high`：low/high/source
- `yoy`：prior-year same-quarter base + growth
- `qoq`：previous-quarter base + growth
- `explicit`：value/source/rationale
- `consensus`：value/source/as_of

### Decision Policy

必须包含：

- valuation：reduce_gap、review_band、buy_below、add_below
- operating：metric、hold_threshold、reduce_threshold、tolerance、uncertainty、confirmation
- thesis_break：typed conditions
- robustness_shock

Resolution 顺序：

1. thesis break → SELL
2. Base IRR materially below hurdle → REDUCE
3. valuation neutral band → REVIEW
4. operating reduce → REDUCE
5. operating neutral band → REVIEW
6. otherwise → HOLD

若 robustness 改变动作，除独立触发 SELL 外，降级为 REVIEW。

## 已实施

### Compiler

新增：

- `scripts/report_spec_v2.py`
- `scripts/report_renderer_v2.py`
- `scripts/report_pipeline_v2.py`

命令：

```bash
python3 scripts/report_pipeline_v2.py build --spec <spec.json> --output <report.md>
python3 scripts/report_pipeline_v2.py verify --spec <spec.json> --output <report.md>
```

Build 生成：

- `<report>.md`
- `<report>.md.bundle.json`
- `<report>.md.verification.json`

### 计算

Compiler 统一生成：

- 四季度 TTM EPS、FCF、operating margin
- Bear/Base/Bull 四期 Revenue
- Revenue-to-EPS Bridge
- 5Y IRR、Reverse Expectations、target-return price
- forward reference 与 buy price
- nominal / discounted payback required growth
- new-money / existing-position actions
- decision robustness
- price zones
- spec、bundle、markdown hashes

### 合同与模板

新增：

- `references/report-spec-v2.md`
- `references/decision-policy-v2.md`
- `templates/report-spec-v2.example.json`

`SKILL.md` 升级到 v2.0.0，明确禁止新报告继续使用 Markdown-first 和 Legacy Compatibility Tables。

### 测试

新增：

- `tests/fixtures/meta_v2_spec.json`
- `tests/fixtures/meta_v2_expected.json`
- `tests/test_report_pipeline_v2.py`

覆盖：

- Meta golden outputs
- deterministic build
- Markdown / Bundle / Spec tamper detection
- cross-scenario assumption rejection
- missing valuation policy rejection
- hidden narrative uncertainty不参与计算
- guide_high 与 midpoint 区分
- payback monotonicity
- price-zone/action 一致性

CI 新增真实 build + verify smoke test。

## 关键行为变化

### 两个动作而不是一个动作

```text
New money: BUY / WATCH / DO_NOT_BUY
Existing position: HOLD / REVIEW / REDUCE / SELL
```

这解决了“不值得新增”与“是否应该卖出现有仓位”长期混淆的问题。

### 估值正式进入存量仓位决策

Meta fixture 中 Base IRR 显著低于 hurdle，超过显式 reduce_gap + review_band，因此 existing-position action 为 REDUCE；不会再被 FCF 中性带完全遮蔽。

### 不再维护报告内兼容表

v2 报告没有 Legacy Compatibility Tables。v1.x Checker 只服务历史报告；v2 的唯一权威验证命令是 `report_pipeline_v2.py verify`。

## 与初始 PRD 的差异

初始方案曾计划让旧 `valuation_consistency.py` 和 `input_decision_consistency.py` 自动 wrapper 到 v2 verify。最终没有这样做，因为仅凭 Markdown 无法可靠定位对应 Spec，强行兼容会重新引入隐式路径。最终选择更明确的边界：

- v1.x 报告 → legacy checker
- v2 报告 → Spec + build/verify

这是主动收窄，而不是遗漏。

## 验证结果

GitHub Actions Validate run #129：PASS。

- Python syntax：PASS
- financial rigor / report audit / report lint self-tests：PASS
- lint fixtures：PASS
- 全量 unittest：**139 / 139 PASS**
- v2 end-to-end build：PASS
- v2 end-to-end verify：PASS
- 生成 Markdown、Bundle、Verification 三文件：PASS
- Legacy Compatibility absence check：PASS
- Meta golden fixture：PASS
- Markdown tamper detection：PASS
- Bundle tamper detection：PASS
- Spec change without rebuild detection：PASS
- cross-scenario assumption rejection：PASS
- missing valuation Reduce policy rejection：PASS
- guide_high output high rather than midpoint：PASS
- deterministic hash/rebuild：PASS

## 不在范围内

- 自动抓取财报和市场数据
- 自动判断哪一个假设最合理
- 完整 DCF / Monte Carlo
- 自动下单
- 组合级优化器

## 成功定义

本版本不是“再增加几个 Checker”，而是让以下行为在架构上不可行：

- 手工复制错 Runtime 字段
- 同一价格出现两套值
- 用 Legacy 表污染新报告
- 在文字里临时追加 uncertainty
- Bear/Bull 借用 Base assumption
- 遗漏 valuation decision dimension
- 修改报告后仍声称 PASS

新报告必须由一个 Spec 编译产生，所有数值和动作只有一个权威来源。
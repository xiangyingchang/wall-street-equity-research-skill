# PRD: Input Provenance、Return Consistency 与 Decision Robustness v1.5

## 状态

实施中 - 2026-08-01

## 背景

Meta 2026-08-01 v1.4 报告说明，v1.4 已经解决“给定输入后的数学错误”：Scenario EPS Bridge、IRR、Reverse Expectations 和 Action Evaluation 均可复算。但报告仍能通过结构约束，同时出现以下问题：

1. Canonical Fact Registry 中 TTM operating margin 为 35%，竞品表又写 43%；按四个季度官方数据计算约为 38.08%。
2. TTM EPS 写为约 $27.25，但四季 GAAP EPS 合计为 $26.55；当前 TTM Fact 没有强制由四个季度自动推导。
3. Forward Revenue Bridge 虽然有四行，但 Q1/Q2 2027 标注“+12% YoY”的收入与基准季度不匹配；Bull 单季收入低于 Base，Base/Bull 总收入相同，却声称不同增长假设。
4. Action runtime 已不接受人工 `triggered=true/false`，但阈值仍可任意设置。例如 TTM FCF < $400亿 触发 Reduce，没有阈值来源、回看窗口、确认期、容忍区间或最低数据置信度。
5. 当前价 $549 被同时描述为“不值得买入”“应 Reduce”和“位于买入区”，跨模块语义冲突没有被拦截。
6. Scenario Valuation 使用 20.5x 的 Base fair value，而 5-year IRR 使用 18x exit PE；两者可以并存，但报告没有区分 forward reference value、target-return-consistent price 和 safety-margin buy price。
7. IRR 使用 0.5% dividend yield，Reverse Expectations 未使用同一股息假设，两个对称模型的输入不一致。
8. `FACT-BULL-FAIR-VALUE` 把主观模型输出注册为事实，混淆了事实、推导值、假设和模型输出。
9. Verification 中 Valuation consistency、Lint、Audit verdict 仍为 TODO，报告却被当作已完成交付。
10. 稀释加权平均股数被直接用于市值计算，未区分 period-average diluted shares 与 point-in-time shares outstanding。

根因是 v1.4 保障了“公式闭合”和“条件由 runtime 比较”，但尚未保障：

- 输入自身由来源或上游公式推导；
- 假设标签与实际数值一致；
- 阈值具有可审计来源和容忍区间；
- 决策对轻微输入变化具有稳定性；
- Fair Value、目标回报价格和买入价使用一致语义；
- 完整报告在验证未完成时 fail closed。

## 目标

1. TTM EPS、TTM revenue、TTM operating income、TTM operating margin 等关键指标必须由 runtime 根据明确季度组件生成。
2. Forward Revenue 每一行必须由 guide、YoY、QoQ、explicit source 或 consensus 模式生成，不能只手填一个最终值并附加不匹配的增长标签。
3. IRR、Reverse Expectations 和 target-return-consistent current price 使用同一组股息、期限、退出倍数和起始 Basis 输入。
4. Canonical Registry 明确区分 `FACT`、`DERIVED` 和 `MODEL`；模型输出不得伪装为 Fact。
5. Action Matrix 的每个数值阈值必须引用 Threshold ID；Threshold 必须声明来源、回看窗口、确认期、容忍区间、最低置信度和理由。
6. 当实际值处于阈值容忍区间、数据置信度不足、确认期不足，或轻微扰动会改变动作时，resolved action 必须降级为 `REVIEW`。
7. Price Zone、First-Page Verdict、Action Matrix 和 current action 的语义必须一致。
8. Forward reference value、target-return price、safety-margin buy price 和 stress price 必须分开。
9. Verification 存在 TODO / FAIL / 未运行 / Unknown 时，完整报告必须失败。
10. Point-in-time market cap 不得使用 weighted-average diluted shares，除非显式标为估算并提供 point-in-time reconciliation。

## 改动范围

### A. Runtime `ttm-derive`

新增 JSON 输入命令：

```bash
python3 scripts/valuation_runtime.py ttm-derive --input ttm.json
```

支持：

- `sum`：四季度 EPS、Revenue、FCF 等求和；
- `ratio`：四季度 numerator 合计 ÷ denominator 合计，例如 TTM operating margin；
- 必须恰好四个明确季度，period 不得重复；
- 输出 component IDs、component totals、最终值和 runtime result。

### B. Runtime `revenue-bridge`

新增 JSON 输入命令：

```bash
python3 scripts/valuation_runtime.py revenue-bridge --input revenue.json
```

每个预测期间必须使用以下模式之一：

- `guide_midpoint`：由 guide low/high 计算；
- `yoy`：由明确 base value / base ID 和 YoY growth 计算；
- `qoq`：由明确 base value / base ID 和 QoQ growth 计算；
- `explicit`：引用有日期、来源和理由的显式预测；
- `consensus`：引用有日期和来源的一致预期。

Runtime 输出每期收入、四期合计、模式和输入；禁止只传最终收入并附加无法复算的增长标签。

### C. Runtime `return-pair`

新增共享输入命令，一次性输出：

- 5-year Scenario IRR；
- Reverse Expectations；
- target-return-consistent current price；
- 使用的 dividend assumption、exit PE、years、target return 和 starting Basis。

IRR 与 Reverse 不得使用不同股息假设。旧 `irr` / `reverse` 保留兼容，但新完整报告必须使用 `return-pair`。

### D. Canonical Value Registry

模板将 Canonical Fact Registry 升级为：

| Value ID | Kind | Metric | Value | Period/as-of | Source/Tier | Basis/Unit | Confidence | Inputs/Formula |

规则：

- `FACT-*`：外部可验证事实；
- `DERIVED-*`：由 FACT / DERIVED 计算的值，必须写 Inputs/Formula 或 runtime ref；
- `MODEL-*`：估值、IRR、目标价等模型输出；
- 未来输入仍属于 Scenario Assumption Registry；
- `FACT-*` 不得包含 fair value、IRR、target price 等模型语义。

### E. Threshold Policy Registry 与 Action Evaluation v2

新增：

| Threshold ID | Metric | Value | Basis | Lookback | Confirmation | Tolerance | Minimum confidence | Rationale |

`evaluate-action` 新输入支持：

- `values`：包含 value、kind、confidence；
- `thresholds`：包含 value、tolerance、minimum_confidence、confirmation；
- condition 通过 `threshold` 引用，不得在新报告中直接传裸数值；
- 容忍区间内返回 `indeterminate`；
- 置信度低于门槛返回 `indeterminate`；
- 确认期不足返回 `indeterminate`；
- 任一可能影响当前最高优先级动作的 indeterminate 条件存在时，resolved action 为 `REVIEW`。

### F. Runtime `robustness`

新增：

```bash
python3 scripts/valuation_runtime.py robustness --input action-evaluation.json --shock 0.05
```

对指定敏感 Value ID 做 ±5%（可配置）扰动，重复 Action Evaluation：

- 输出 baseline action；
- 输出每个扰动场景的 resolved action；
- 动作变化则 `stable=false`；
- 新完整报告在 `stable=false` 时不得给出确定性 Buy/Add/Reduce/Sell，必须 REVIEW 或解释为组合外部约束。

### G. Consistency Checker v1.5

扩展 `valuation_consistency.py`，至少拦截：

1. `FACT-*` 承载 fair value、IRR、target price 等模型输出；
2. TTM DERIVED 值没有 component/runtime bridge；
3. 同一 TTM 指标在 Registry 和其他结构化表中出现明显冲突；
4. Revenue Bridge 的 YoY/QoQ/guide 算术不一致；
5. Bull 预测低于 Base、或不同增长假设得到相同总收入但没有明确解释；
6. IRR / Reverse 没有共享 `return-pair` 结果；
7. Action 数值条件没有 Threshold ID；
8. Threshold 缺 basis/lookback/confirmation/tolerance/minimum confidence/rationale；
9. 当前价落在“买入区”，但首页写“不值得买入”或 current action 为 Reduce/Sell；
10. Forward reference value 被直接当作目标回报公允价值，未列 target-return-consistent price；
11. Verification 包含 TODO、FAIL、未运行、Unknown；
12. 市值使用 weighted-average diluted shares 且无 reconciliation；
13. Canonical Registry、Scenario Assumption、Threshold 和 Model 输出 ID 重复或跨类型前缀错误。

### H. 模板与文档

更新：

- `SKILL.md` 至 v1.5.0；
- `templates/full-report.md`；
- `references/valuation-runtime.md`；
- `references/report-contract.md` 或新增权威 addendum；
- 测试与 README/方法论中受影响的执行顺序。

## 不在范围内

- 不自动抓取财报、价格、一致预期或投资组合；
- 不自动决定哪一个增长率、利润率、退出倍数最合理；
- 不实现完整 DCF 或概率加权 Monte Carlo；
- 不自动解析全部自然语言事实；
- 不改变九个顶层模块；
- 不替代组合层面的集中度、税务或流动性判断；
- 不强制所有公司都使用相同绝对阈值。

## 验证标准

1. TTM EPS 输入 `1.05 + 8.88 + 10.44 + 6.18`，runtime 输出 `26.55`。
2. TTM operating margin 输入四季 revenue / operating income，runtime 输出约 `38.08%`。
3. Q1 2027 base revenue `563.11`、YoY growth `12%`，runtime 输出约 `630.68`，不得输出 `700`。
4. Revenue Bridge 中 Bull 单季低于 Base 时 checker 至少 WARNING；无解释且场景总额/增长标签矛盾时 ERROR。
5. `return-pair` 使用同一股息假设输出 IRR、Reverse 和 target-return price。
6. `FACT-BULL-FAIR-VALUE` 或其他模型语义的 `FACT-*` 必须 FAIL。
7. 裸数值 Action threshold 在新完整报告中必须 FAIL。
8. 378.7 对 400、tolerance 5% 时应进入 indeterminate / REVIEW，而不是确定性 REDUCE。
9. ±5% shock 改变 resolved action 时 robustness `stable=false`，报告 current action 必须 REVIEW。
10. 当前价处于买入区且首页“不值得买入”或 action=REDUCE 时 checker FAIL。
11. Verification 任一必需项为 TODO / FAIL / 未运行 / Unknown 时 checker FAIL。
12. weighted-average diluted shares 直接用于 market cap 时 checker FAIL 或要求显式 reconciliation。
13. `python3 -m py_compile scripts/*.py` PASS。
14. `python3 -m unittest discover -s tests` PASS。
15. `report_lint.py --self-test` 与 fixtures PASS。
16. `git diff --check` PASS。

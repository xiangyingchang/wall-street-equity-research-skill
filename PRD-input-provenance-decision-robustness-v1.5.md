# PRD: Input Provenance、Return Consistency 与 Decision Robustness v1.5

## 状态

完成 - 2026-08-01

## 背景

Meta 2026-08-01 v1.4 报告证明，正确公式仍会放大错误或脆弱输入：

1. TTM operating margin 在不同章节出现 35% 与 43%，但四季度数据约为 38.08%。
2. TTM EPS 写为约 $27.25，而四季 GAAP EPS 合计为 $26.55。
3. Forward Revenue 虽有四行，但标注 +12% YoY 的预测与基准季度不匹配；Base/Bull 总额相同却声称不同增长路径。
4. `$400亿` FCF Reduce 阈值缺少来源、回看窗口、确认期、容忍区间与最低置信度。
5. 当前价格同时被描述为“不值得买入”“Reduce”和“位于买入区”。
6. IRR 与 Reverse Expectations 使用了不同股息输入。
7. Fair value 被注册为 `FACT-*`，混淆事实与模型输出。
8. weighted-average diluted shares 被直接用于 point-in-time market cap。
9. Verification 仍为 TODO，但报告被当作完成交付。

根因：v1.4 保障了公式闭合和条件比较，却没有保障输入来源、预测变换、阈值政策、价格语义和决策稳定性。

## 目标

1. 决策关键 TTM 值由四季度组件自动生成。
2. Forward Revenue 每期由 guide / YoY / QoQ / explicit / consensus 模式自动生成。
3. IRR、Reverse Expectations 与 target-return price 共用一组输入。
4. Canonical Registry 区分 `FACT`、`DERIVED`、`MODEL`。
5. Action 数值阈值必须引用 Threshold Policy。
6. 容忍区间、低置信度、确认不足或小扰动导致动作变化时，动作降级为 `REVIEW`。
7. First Page、Price Zone、Action Matrix 与 current action 语义一致。
8. Forward reference value、target-return price、buy price 与 stress price 分离。
9. Verification 未全部 PASS 时 fail closed。
10. 市值使用 point-in-time shares，或显式估算并 reconciliation。

## 已实施

### Runtime

- `valuation_runtime.py ttm-derive`
  - `sum`：四季度 EPS、Revenue、FCF 等求和；
  - `ratio`：四季度 numerator 合计 ÷ denominator 合计；
  - 强制四个唯一期间。
- `valuation_runtime.py revenue-bridge`
  - 支持 `guide_midpoint`、`yoy`、`qoq`、`explicit`、`consensus`；
  - 输出逐期收入和 Forward 12M 合计。
- `valuation_runtime.py return-pair`
  - 共享 dividend、years、exit PE、starting EPS 与 target return；
  - 同时输出 IRR、Reverse Expectations 与 target-return price。
- `evaluate-action` v2
  - 使用结构化 `values`、`thresholds`；
  - 支持 confidence、uncertainty、tolerance、confirmation；
  - 条件状态为 true / false / indeterminate；
  - 高优先级 indeterminate 时 resolved action 为 REVIEW。
- `valuation_runtime.py robustness`
  - 对指定 Value ID 进行 ±shock；
  - 动作变化时 `stable=false`，recommended action 为 REVIEW。

### 报告合同

- Canonical Value Registry：`FACT-*` / `DERIVED-*` / `MODEL-*`。
- TTM Derivation Runtime table。
- Revenue Forecast Runtime table。
- Return Pair Runtime table。
- Threshold Policy Registry。
- Action Evaluation v2 + Robustness 输出。
- Scenario Valuation 区分 forward reference、target-return、safety-margin buy、stress price。
- Verification 增加两个 consistency checker 和全部 runtime PASS 门槛。

### 检查器

新增 `scripts/input_decision_consistency.py`，拦截：

- 模型输出注册为 FACT；
- TTM DERIVED 无组件/runtime provenance；
- YoY/QoQ/guide 收入算术不闭合；
- 不同增长假设产生相同 Base/Bull 总额而无解释；
- 裸数值 Action threshold；
- Threshold Policy 字段缺失；
- 新报告分别使用 `irr` / `reverse`；
- robustness 不稳定但动作不是 REVIEW；
- 当前价处于买入区但 verdict no-buy / Reduce / Sell；
- weighted-average shares 直接用于 market cap；
- 结构化 TTM margin 冲突；
- Verification TODO / FAIL / 未运行 / Unknown。

## 不在范围内

- 不自动抓取财报、价格、一致预期或投资组合；
- 不自动选择经济上最合理的增长率、利润率、倍数或阈值；
- 不实现完整 DCF、Monte Carlo 或组合优化；
- 不改变九个顶层模块；
- 不替代组合层面的税务、集中度或流动性判断。

## 验证结果

GitHub Actions `Validate` run #69：PASS。

- Python syntax：PASS。
- financial rigor / report audit / report lint self-tests：PASS。
- lint fixtures：PASS。
- 全量 unittest：117 / 117 PASS。
- TTM EPS：`1.05 + 8.88 + 10.44 + 6.18 = 26.5500` PASS。
- TTM operating margin：约 `38.08%` PASS。
- Revenue YoY：`563.11 × 1.12 = 630.6832` PASS。
- Return Pair：Base IRR `6.54%`、Reverse required EPS CAGR `8.90%`、target-return price `479.7122` PASS。
- `378.7` 对 threshold `400`，5% tolerance + 1% uncertainty：indeterminate / REVIEW PASS。
- ±5% shock 改变动作：`stable=false`、recommended action `REVIEW` PASS。
- model-as-FACT、naked threshold、buy-zone conflict、Verification TODO、weighted-average shares misuse：negative tests PASS。

## 交付边界

PR #5 尚未合并。最终合并前需将 `references/change-log-v1.5.md` 插入 `references/change-log.md` 顶部并删除 staging file，然后重新跑 CI。

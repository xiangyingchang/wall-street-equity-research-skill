# PRD: Scenario Bridge、Canonical Facts 与 Action Evaluation v1.4

## 状态

完成 - 2026-08-01

## 背景

Meta 2026-08-01 报告使用 v1.3 runtime 后，IRR 与 Reverse Expectations 的公式已经可复算，但错误输入仍可被精确放大：

1. Scenario EPS Bridge 声明 Revenue=$2,750亿、Operating margin=35%、Tax rate=18%、Diluted shares=25.7亿，却手填 EPS=$22；按表内数字应约为 $30.71。
2. Forward revenue 使用“单季度 ×4.5”而没有逐季假设，既不是 TTM，也不是可审计的 Forward 12M。
3. Action runtime 接收 Agent 手工给出的 `triggered=true/false`，因此 Agent 可以先把临界条件判为 true，再让 runtime 为预设结论盖章。
4. 同一指标在不同章节出现 31%、35%、43% 等多个值，但没有唯一 Canonical Fact ID，跨章节冲突未被发现。
5. 历史 One-off Adjustment 与未来情景假设混在同一 Ledger；Capex 正常化被错误标记为 non-cash。
6. `10Y Treasury ×2` 被写成“低风险资产”，混淆了实际可投资资产与个人股票目标回报门槛。

根因是 v1.3 只保证了“给定输入后的数学正确”，尚未保证 Scenario Bridge 输入输出闭合、Action 条件由事实自动求值、以及全文关键事实只有一个权威值。

## 目标

1. Scenario EPS 必须由 runtime 根据 Revenue、margin、other income、tax、shares 自动生成，禁止手填。
2. Action Matrix 的当前真假必须由 runtime 根据 Canonical Facts 与结构化条件自动求值，禁止传入人工 `triggered`。
3. 建立 Canonical Fact Registry；Action、估值、正文引用相同指标时使用同一个 Fact ID。
4. Forward 12M 收入必须来自逐期 Revenue Bridge 或明确的年度预测来源，禁止“季度 ×4.5”等无定义年化。
5. 历史会计调整与未来情景假设分离：Adjustment Ledger 只放已发生项目，Scenario Assumption Registry 放未来假设。
6. 机会成本表明确区分 investable benchmark、required-return hurdle 和 equity alternative。
7. 保持现有 v1.3 IRR、Reverse Expectations 和旧 `resolve-action` API 的向后兼容，但完整报告必须使用新的事实求值流程。

## 改动范围

### A. Runtime `eps-bridge`

新增命令：

```bash
python3 scripts/valuation_runtime.py eps-bridge \
  --revenue 2750 \
  --operating-margin 0.35 \
  --other-income 0 \
  --tax-rate 0.18 \
  --diluted-shares 25.7
```

确定性输出 operating_income、pre_tax_income、net_income、eps。

规则：

- `operating_income = revenue × operating_margin`
- `pre_tax_income = operating_income + other_income`
- `net_income = pre_tax_income × (1-tax_rate)`
- `eps = net_income ÷ diluted_shares`
- 税率必须在 `[0,1)`；股数与收入必须大于 0。

### B. Runtime `evaluate-action`

输入改为 Canonical Facts 和条件表达式：

```json
{
  "current_action": "Hold",
  "facts": {
    "FACT-TTM-OP-MARGIN": 0.381,
    "FACT-TTM-FCF": 378.7,
    "FACT-CURRENT-PRICE": 549
  },
  "rules": [
    {
      "id": "reduce-op",
      "action": "REDUCE",
      "logic": "all",
      "conditions": [
        {"fact": "FACT-TTM-OP-MARGIN", "operator": "<", "value": 0.35}
      ]
    }
  ]
}
```

Runtime 必须：

- 自己读取 fact、执行比较并生成 `triggered`；
- 支持 `< <= > >= == !=`；
- 支持 `all` / `any`；
- 输出每个 condition 的 actual、operator、expected、result；
- 缺失 Fact、未知操作符、非数字比较必须 fail closed；
- 没有规则触发时返回 `REVIEW`；优先级仍为 SELL > REDUCE > ADD > BUY > HOLD。

旧 `resolve-action` 保留，仅用于兼容，不得用于新完整报告。

### C. Canonical Fact Registry

模板新增表：

| Fact ID | Metric | Value | Period/as-of | Source/Tier | Basis/Unit | Confidence |

要求 Fact ID 唯一；Action runtime 只能引用已登记 Fact ID；单季、TTM、Forward 必须使用不同 Fact ID 和明确期间。

### D. Forward Revenue Bridge

Scenario EPS 前新增逐期收入表：

| Revenue Bridge ID | Scenario | Period | Revenue | Growth/guide basis | Source/assumption ID |

Forward 12M 必须为四个明确季度/期间之和，或引用有日期和来源的 FY/NTM 一致预期。禁止无定义的“季度 ×4.5”“run-rate adjustment”。

### E. Scenario Assumption Registry

新增：

| Assumption ID | Scenario | Variable | Value | Period | Evidence/rationale | Confidence |

未来收入增速、margin、tax、shares、capex normalization、exit multiple 和 EPS CAGR 放在此表；One-off Adjustment Ledger 不再承载未来假设。

### F. Consistency checker

扩展 `valuation_consistency.py`，至少拦截：

1. Scenario EPS Bridge 的 operating income / pre-tax / net income / EPS 算术不闭合；
2. Basis Value 与 Bridge EPS 不一致；
3. Duplicate Fact ID；
4. `10Y ×2` 被标为“资产”或“极低风险可投资资产”；
5. Capex / forward assumptions 出现在 One-off Adjustment Ledger；
6. 完整报告仍使用人工 `Triggered=true/false` 而没有 fact-based runtime evaluation。

## 不在范围内

- 不自动抓取财报、价格或一致预期；
- 不自动判断哪一个 operating margin 假设最合理；
- 不实现完整 DCF；
- 不自动识别所有自然语言中的事实引用；
- 不改变九个顶层模块；
- 不替代人工判断 Scenario 概率。

## 验证标准

1. Meta bridge 输入 2750 / 35% / 0 / 18% / 25.7，runtime EPS 输出约 30.71，而不是 22。
2. Action facts 中 TTM margin=38.1%、Reduce threshold <35% 时，Reduce=false；无其他规则触发时 resolved action=REVIEW。
3. 缺失 Fact ID、未知 operator、字符串与数值非法比较均 FAIL。
4. `valuation_consistency.py` 对 EPS Bridge 算错、Basis/Bridge 不一致、重复 Fact ID、人工 triggered 表格和机会成本类型混淆 FAIL。
5. 模板包含 Canonical Fact Registry、Forward Revenue Bridge、Scenario Assumption Registry、runtime EPS Bridge 和 fact-based Current Action Evaluation。
6. SKILL 版本更新到 1.4.0，runtime reference 和 canonical template 同步。
7. `python3 -m py_compile scripts/*.py` PASS。
8. `python3 -m unittest discover -s tests` PASS。
9. `report_lint.py --self-test` 与 fixtures PASS。
10. `git diff --check` PASS。

## 完成验证

- GitHub Actions `Validate` run #49：PASS。
- Python syntax：PASS。
- Financial rigor、report audit、report lint self-tests：PASS。
- Lint fixtures：PASS。
- 全量 unittest：109/109 PASS。
- Meta EPS Bridge regression：`30.7101` PASS。
- Meta Action Evaluation regression：`38.1% < 35%` 为 false；无其他规则触发时 `REVIEW` PASS。
- 模板字段识别：修复 `10Y Treasury ×2` 原子标签后 PASS。

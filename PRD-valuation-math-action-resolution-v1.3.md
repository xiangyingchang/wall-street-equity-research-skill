# PRD — Valuation Math and Action Resolution v1.3

## 背景

Meta 2026-07-31 重跑报告已经具备 Valuation Basis Registry、One-off Adjustment Ledger、Scenario Valuation、5-year IRR、Reverse Expectations 与 Action Matrix，但仍出现四类严重问题：

1. 5 年 IRR 手填错误，且回购对 EPS 与股东回报重复计入。
2. Reverse Expectations 公式错误，没有区分“保持现价”与“达到目标回报”。
3. Normalized EPS 只有情景标签，没有 Revenue → Margin → Net income → Shares → EPS 的完整桥接。
4. 报告正文声称 Reduce，但 Action Matrix 的实际条件未触发。

这类错误会让报告在结构、lint 和表格完整性均通过时，仍给出错误交易动作。

## 现状

- `valuation_consistency.py` 能检查部分乘法、收益率和文本一致性，但不能作为估值计算权威。
- 5-year IRR、Reverse Expectations 和 Action Matrix 当前允许模型手算或手填。
- Normalized EPS Basis 可以在缺少完整盈利桥接时注册。
- Action Matrix 只有结构校验，没有基于输入事实的确定性求值。

## 目标

1. 新增确定性 Decimal 估值运行时，统一计算：
   - 终值 EPS、终值股价、累计股息、总回报、5 年 IRR；
   - 目标回报下的 Reverse Expectations；
   - Action Matrix 条件布尔值与最终 resolved action。
2. 明确回购处理：
   - 若输入是 EPS CAGR，回购缩股不得再次加到回报中；
   - 若输入是净利润 CAGR，可单独输入股数变化推导 EPS。
3. 强制 normalized EPS 使用完整桥接表，并要求每个 Basis ID 引用桥接行。
4. 报告不得自行声称某动作被触发；当前动作必须引用运行时的 resolved action。
5. 修正来源分层：Yahoo Finance 等标准化数据商只能是 Tier 2。
6. 信息存在 filing gap、近似 TTM 或低置信度 owner earnings 时，Researchability 不得为 A / High。

## 改动范围

- 新增 `scripts/valuation_runtime.py`。
- 新增 `tests/test_valuation_runtime.py`。
- 更新 `SKILL.md`、`templates/full-report.md`、`references/report-contract.md`、`references/full-methodology.md`。
- 更新 `references/change-log.md`。

## 不在范围内

- 不自动抓取真实市场或财报数据。
- 不替代现有 research-pack、audit v4/v5 或来源人工复核。
- 不自动推断 maintenance/growth/AI capex。
- 不为具体公司预设盈利、倍数或动作阈值。

## 验证标准

### 数学

- Meta 示例：`price=549, start_eps=22, eps_cagr=8%, exit_pe=18, dividend_yield=0.5%, years=5` 的 IRR 必须约为 1.7%，不得为 9.5%。
- Reverse Expectations：在 `price=549, target_return=9.4%, exit_pe=18, years=5` 下，终值 EPS 必须约为 47.8；从 22 起算所需 CAGR 必须约为 16.8%。
- EPS CAGR 模式中若另传回购缩股，程序必须拒绝，防止双算。

### 决策

- 当 Hold 与 Reduce 条件都未触发时，resolved action 必须为 `REVIEW`，不得强制 Reduce。
- 当前动作若与 resolved action 不一致，报告交付必须失败。

### 结构

- Scenario EPS Bridge 至少包含 Revenue、Operating margin、Operating income、Tax rate、Net income、Diluted shares、EPS。
- 每个 Bear/Base/Bull EPS Basis 必须引用一个 bridge ID。

### 工程

- `python3 -m py_compile scripts/valuation_runtime.py`
- `python3 -m unittest tests.test_valuation_runtime`
- 现有完整测试、self-test、fixtures 和 `git diff --check` 不回归。

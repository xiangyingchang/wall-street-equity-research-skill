# PRD：利润正常化与现金流纪律 v1

状态：完成 — 2026-08-01
基线：`6c5ca25`（a99 历史结构质量加固版）
目标：保留 a99 的 Reader 结构，同时把财报数据、正常化口径和价格纪律变成可审计、可复算的报告契约。

## 背景

Meta 复核暴露出四类问题：

- 报告值、一次性调整值和正常化假设没有分层；
- 利润正常化与现金流正常化被混在一起；
- 高 CapEx 季度是否为极端情况没有与全年指引比较；
- 名义十年回本和目标回报价格存在手工计算漂移。

## 目标

1. 保留 First-Page Verdict、Evidence Ledger、连续论证和 9 个固定模块。
2. 强制报告分别展示 Reported、Adjusted、Normalized 三种口径。
3. 强制把利润正常化和现金流正常化分开，并披露调整依据和置信度。
4. 高 CapEx 公司必须比较季度 CapEx、全年指引、经营现金流运行率，不能仅凭单季度低 FCF 判定“极端”。
5. 固定 TTM EPS、FCF/share 的股数口径，并要求披露加权平均股数或期末流通股的选择。
6. 用可测试的 Python 运行时计算十年回本、目标回报价格和 IRR，禁止报告手填无法复现的价格线。
7. 价格纪律同时展示盈利参考价值、目标回报价格和现金流确认价格，避免把三者混成一个“公平价格”。

## 非目标

- 不引入 v2/v3 Spec、Bundle、Research Graph 或双层 Audit Renderer。
- 不删除 a99 的历史报告结构或覆盖旧 Meta 报告。
- 不把一次性利润表费用自动加回 FCF；现金流调整必须有现金流或管理层口径证据。
- 不加入 Agent provider、模型或耗时 telemetry。

## 报告契约

### 正常化桥

模块 2 必须包含一张表，至少有：

| 口径 | EPS | 经营利润率 | FCF/share | 证据与限制 |
|---|---:|---:|---:|---|
| Reported |  |  |  | 财报原始值 |
| Adjusted |  |  |  | 有官方披露的一次性项目 |
| Normalized |  |  |  | 模型假设和置信度 |

报告必须明确写出：利润正常化与现金流正常化分开；一次性税项、法务、裁员等利润表项目不得自动改变 FCF。

### CapEx 制度检查

高 CapEx 公司必须披露季度 CapEx、全年 CapEx 指引或长期资本开支假设、经营现金流运行率，并标明当前高 CapEx 是“计划内结构性”还是“暂时性异常”。若没有依据，只能标记“未证实”。

### 股数与资产负债表口径

TTM EPS 和 FCF/share 必须说明使用季度加权平均稀释股数、期间加权平均股数还是期末流通股。现金、债务和租赁负债必须分开披露；“净现金”只能在口径完整时使用。

### 估值运行时

标准十年回本公式：

```text
M = sum_{t=1}^{10} (((1+g)/(1+r))^t)
```

目标回报价格必须记录 starting EPS、EPS CAGR、exit PE、years、target return、dividend yield 和 dividend treatment。默认 dividend treatment 为 `reinvested_yield`，公式为：

```text
terminal_price = starting_eps * (1 + eps_cagr)^years * exit_pe
target_price = terminal_price / (1 + target_return)^years * (1 + dividend_yield)^years
```

如果采用其他股息处理方式，报告必须明确说明，且不得直接复用旧价格。

## 实现范围

- 修改 `SKILL.md`、`references/report-contract.md`、`references/full-methodology.md` 和 `templates/full-report.md`。
- 新增 `scripts/valuation_math.py`，提供 payback、target-price、IRR 的确定性计算。
- 扩展 `scripts/report_lint.py`，检查正常化桥、现金流分离、CapEx 制度、股数口径和公式输入披露。
- 更新 fixture 和 unittest，覆盖缺失桥、混淆 FCF、缺失股数口径及运行时数学。
- 从全新模板生成一份新的 Meta 报告，不覆盖历史报告。

## 验收标准

- `python3 -m py_compile scripts/*.py tests/*.py` 通过。
- 全量 unittest、lint self-test、fixture test 通过。
- `valuation_math.py` 对 Meta 示例输出：名义 EPS 回本约 `13.13%`，名义 FCF 回本约 `23.31%`；目标回报价格在股息再投资口径下可复现。
- 缺少 Reported/Adjusted/Normalized 桥、利润现金流分离、CapEx 制度检查或股数口径时，lint 失败。
- 新 Meta 报告使用官方财报数据，正常化 EPS 与 FCF 分别披露，价格线由运行时重新计算，并通过 lint。

## 变更记录要求

实现前先创建 staged change-log；实现和验证完成后，将本 PRD 状态改为“完成”，再把 staged change-log 插入 `references/change-log.md` 顶部，不覆盖历史记录。

## 实施结果

- `SKILL.md`、`references/report-contract.md`、`references/full-methodology.md` 和模板增加正常化桥、现金流制度、股数口径和股息处理要求。
- 新增 `scripts/valuation_math.py`，统一 payback、target-return price 和 IRR 计算。
- `report_lint.py` 增加 Reported / Adjusted / Normalized、利润现金流分离、CapEx 制度、股数口径和估值输入检查。
- 从全新模板生成 Meta 报告 `META.US-Meta-华尔街式分析报告-2026-08-01-a99-normalized-v1.md`，未覆盖旧报告。

## 验收结果

- `python3 -m py_compile scripts/*.py tests/*.py`：PASS
- `python3 -m unittest discover -s tests`：15/15 PASS
- `python3 scripts/report_lint.py --self-test`：PASS
- `python3 scripts/report_lint.py --fixtures tests/fixtures`：PASS
- Meta 新报告 `report_lint.py`：PASS
- `valuation_math.py`：名义 EPS 13.13%、名义 FCF 23.31%、Base target-return price $461.90、Base IRR 5.49%：PASS
- `git diff --check`：PASS

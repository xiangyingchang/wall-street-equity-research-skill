# PRD：周期股价格纪律 v2

状态：完成 — 2026-08-01
基线：`2368da4`（正常化财务与现金流纪律 v1）
目标：吸收海力士报告中“中周期估值 + 价格区间 + 经营确认”的优点，但把价格线变成可复算、可解释、不能混淆的决策模块。

## 背景

海力士报告的价格纪律用新周期 EPS 乘 12x/15x/18x 得到价格区间，再用 6% FCF yield 和 HBM/CapEx 条件确认。这个结构适合周期股，但存在四个问题：

- 中周期 EPS/FCF 的来源没有完整桥接；
- Forward 与 TTM 的十年回本公式没有明确区分；
- 6% FCF yield 与 8.51% 机会成本之间没有关系说明；
- 价格区间、目标回报价格和现金收益率价格没有分层。

## 目标

1. 保留 a99 Reader 结构和现有正常化桥。
2. 为周期/高 CapEx 公司加入可复算的 `Price Discipline` 模块。
3. 分开四类价格：盈利参考价值、目标回报价格、现金流确认价格、联合新资金价格。
4. 每条价格线都必须披露公式、输入、情景、置信度和适用边界。
5. 价格区间只作为行动规则，不冒充唯一公平价值。
6. 当盈利和现金流两个门槛同时启用时，联合新资金价格取有效门槛中更严格的一条；当现金流未证实时，动作最高只能为 Review。
7. 支持不同公司的 PE 倍数、FCF yield 和目标回报输入，不把海力士的 12x/15x/18x 或 6% 写死为全市场常数。

## 非目标

- 不把价格纪律变成完整 DCF。
- 不删除目标回报运行时、正常化桥或十年回本压力测试。
- 不把单季度峰值 EPS/FCF 自动当作周期中枢。
- 不直接覆盖旧 Meta 或海力士报告。

## 价格纪律契约

模块 4 必须包含 `### Price Discipline 价格纪律`，至少展示：

| 价格线 | 公式 | 作用 |
|---|---|---|
| Earnings reference price | normalized EPS × reference PE | 估值参考，不等于买入价 |
| Target-return price | valuation runtime | 满足目标回报的价格 |
| Cash-confirmation price | normalized FCF/share ÷ cash hurdle | 现金流确认线 |
| Joint new-money price | min(active executable gates) | 新资金 Buy/Add 的最高价格 |
| Safety price | target-return price × (1 - margin) | 安全边际价格 |

### 输入要求

- Normalized EPS 和 Normalized FCF 必须来自正常化桥，并标注 Bear/Base/Bull 或 Stress/Base/High 情景。
- Reference PE 必须说明依据：增长、周期性、ROIC、杠杆、竞争和同业区间。
- Cash hurdle 必须说明是机会成本、股权回报门槛还是单独现金确认阈值，不能只写一个裸数字。
- Target-return price 必须沿用 `scripts/valuation_math.py`，披露 starting EPS、EPS CAGR、exit PE、years、target return、dividend yield 和 dividend treatment。
- 若现金流置信度为 low 或未证实，Cash-confirmation price 只能标记为 Conditional，联合动作必须为 Review。
- 价格区间必须写清楚动作：No-chase、Observe、Buy、Add、Reduce 或 Sell，并把价格门槛与经营确认条件绑定。

## 运行时

新增以下确定性计算：

```text
earnings_reference_price = normalized_eps * reference_pe
cash_confirmation_price = normalized_fcf_per_share / cash_hurdle
joint_new_money_price = min(active executable prices)
```

PE/FCF 的十年回本仍按 Forward `t=0..9` 与 TTM `t=1..10` 明确区分，不能因为报告使用“当前周期”就默认 Forward。

## 验收标准

- `valuation_math.py price-zones` 能输出盈利参考价、现金流确认价和联合价格。
- 海力士示例：EPS 75K、PE 12/15/18、FCF 62K、FCF hurdle 6%，输出 900K、1.125M、1.35M 及约 1.033M 现金确认价；联合新资金价约 1.033M。
- 缺少 Price Discipline、公式、输入、情景、现金流状态或动作映射时，lint 失败。
- Meta 新报告必须显示新的价格纪律表，并重新计算联合新资金价格。
- 全量 unittest、lint self-test、fixtures、Meta 报告 lint、数学运行时和 `git diff --check` 通过。

## 变更记录要求

实现前先创建 staged change-log；实现和验证完成后将本 PRD 标为“完成”，再把 staged change-log 插入 `references/change-log.md` 顶部，不覆盖历史记录。

## 实施结果

- `SKILL.md`、报告合同、完整方法论和模板新增 Price Discipline 契约。
- `valuation_math.py` 新增 earnings reference、cash confirmation、joint new-money price 和 cash-confidence 状态计算。
- lint 强制检查五条价格线、输入、公式、情景、置信度和动作映射。
- 海力士示例：12x/15x/18x 输出 KRW 0.90M/1.125M/1.35M，6% FCF 确认价约 KRW 1.033M。
- 从全新模板重跑 Meta，生成 `META.US-Meta-华尔街式分析报告-2026-08-01-a99-price-discipline-v2.md`，旧报告未覆盖。

## 验收结果

- `python3 -m py_compile scripts/*.py tests/*.py`：PASS
- `python3 -m unittest discover -s tests`：19/19 PASS
- `python3 scripts/report_lint.py --self-test`：PASS
- `python3 scripts/report_lint.py --fixtures tests/fixtures`：PASS
- Meta 新报告 lint：PASS
- 海力士 price-zones 示例：PASS
- Meta Base Price Discipline：目标回报 `$461.90`、现金确认 `$405.68`、联合价格 `$405.68`、现金状态 `REVIEW_CASH_CONFIDENCE`：PASS
- `git diff --check`：PASS

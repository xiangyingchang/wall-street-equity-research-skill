# Wall Street Equity Research Skill Change Log

## ledger-authoritative-positions-v1 — 2026-08-02

### Change

- 将当前持仓事实来源从过时 Dashboard 切换为鉴权后的 Ledger `/api/stocks`。
- 规定只把 `amount > 0` 的 Ledger 记录视为 active position；零数量记录只保留为历史。
- 明确 `/api/allocation` 只能作为配置快照交叉参考，因为其股票价格读取保存的 `Stock.currentPrice`，可能滞后。
- 新增只读 `ledger_portfolio_preflight.py`，输出持仓、价格时间、来源和 warning，不保存认证 token。
- 借鉴 AI-伯克希尔的双源交叉验证、差异标记和 `financial_rigor.py` 精确市值/估值验算规则。

### Reason

旧 Dashboard 已经过时，继续引用会把历史仓位误写成当前事实。AI-伯克希尔的 FinMind 工具只覆盖台股，没有通用稳定的美股行情接口；可借鉴的是数据交叉验证和精确计算，而不是把 FinMind 当成美股行情源。

### Verification

- `python3 -m py_compile scripts/*.py tests/*.py`：PASS
- `python3 -m unittest tests.test_ledger_portfolio_preflight -v`：9/9 PASS
- `python3 -m unittest discover -s tests`：28/28 PASS
- `python3 scripts/report_lint.py --self-test`：PASS
- `python3 scripts/report_lint.py --fixtures tests/fixtures`：PASS
- 无 `LEDGER_AUTH_TOKEN` 时安全失败且不输出 token：PASS
- `git diff --check`：PASS

## price-discipline-v2 — 2026-08-01

### Change

- 吸收海力士报告的中周期估值、价格区间和经营确认结构。
- 新增 Earnings reference price、Target-return price、Cash-confirmation price、Joint new-money price 和 Safety price 五类价格线。
- 新增 `price-zones` 运行时，所有 PE 和 FCF yield 价格由输入计算，禁止把海力士阈值写死成全市场规则。
- 要求价格纪律披露情景、输入、公式、置信度、适用边界和动作映射。
- 修正周期股 Forward / TTM 十年回本口径混淆，并要求低置信度现金流只能产生 Review。
- 基于新 Skill 从干净模板重跑 Meta，旧报告保留不覆盖。

### Reason

海力士报告的价格纪律很适合周期股，但原始区间由未充分桥接的中周期假设和未解释的阈值组成，且没有把估值参考价、目标回报价和现金收益率价分开。新模块保留其决策价值，同时把价格线绑定到正常化数据和确定性运行时。

### Verification

- `python3 -m py_compile scripts/*.py tests/*.py`：PASS
- `python3 -m unittest discover -s tests`：19/19 PASS
- `python3 scripts/report_lint.py --self-test`：PASS
- `python3 scripts/report_lint.py --fixtures tests/fixtures`：PASS
- Meta 新报告 lint：PASS
- 海力士 price-zones 示例：PASS
- Meta Base Price Discipline：目标回报 `$461.90`、现金确认 `$405.68`、联合价格 `$405.68`、现金状态 `REVIEW_CASH_CONFIDENCE`：PASS
- `git diff --check`：PASS

## normalized-financials-cashflow-discipline-v1 — 2026-08-01

### Change

- 新增 Reported / Adjusted / Normalized 三层正常化桥，强制区分利润正常化与现金流正常化。
- 新增高 CapEx 制度检查，要求把季度 CapEx、全年指引和经营现金流运行率放在同一判断中。
- 新增股数、债务、租赁负债和“净现金”口径披露要求。
- 新增确定性的十年回本、目标回报价格和 IRR 计算脚本，避免手工数学漂移。
- 扩展 report lint 和 unittest，阻止无正常化桥、无现金流分离、无股数口径的报告通过。
- 基于新 Skill 从干净模板重跑 Meta 报告，保留旧报告作为对照，不覆盖历史文件。

### Reason

Meta 复核显示，原报告把 Q2 低 FCF 近似视为极端情况，却没有与 2026 CapEx 指引比较；同时 `$22` Normalized EPS 没有计算桥，`$25` Normalized FCF/share 也没有现金流依据。名义十年回本和目标回报价格还存在无法复现的手工计算。新规则把数据事实、一次性调整、模型假设和现金回报分别锁定。

### Verification

- `python3 -m py_compile scripts/*.py tests/*.py`：PASS
- `python3 -m unittest discover -s tests`：15/15 PASS
- `python3 scripts/report_lint.py --self-test`：PASS
- `python3 scripts/report_lint.py --fixtures tests/fixtures`：PASS
- Meta 新报告 lint：PASS
- `valuation_math.py`：名义 EPS 13.13%、名义 FCF 23.31%、Base target-return price $461.90、Base IRR 5.49%：PASS
- `git diff --check`：PASS

## a99-quality-hardening-v1 — 2026-08-01

### Change

- 以 `a99c4f6` 为历史结构基线，将报告契约、模板和方法论统一为 9 个模块。
- 删除独立 `Tax Drag & Net Yield` 模块，保留必要的税务和汇率说明。
- `report_lint.py` 增加精确顶层结构、真实 HTTPS 来源、Evidence Ledger 数据行、贴现表格、条件流动性、网络效应用户指标、Action Triggers 和占位符检查。
- 新增 8 个 unittest，覆盖来源、模块、Evidence Ledger、贴现表格、流动性、网络效应和占位符失败路径。
- 从全新模板生成 Meta 报告，包含 DAP 36亿（同比 +3%）、广告展示量 +14% 和平均广告价格 +12%。

### Reason

旧版 lint 只检查标题和关键词，空 Evidence Ledger、无真实 URL 来源、重复模块和非表格贴现说明都可以通过；流动性“按需分析”也没有退出天数阈值。Meta 等网络效应公司还需要强制记录用户规模和期间变化，才能让护城河判断可验证。

### Verification

- `python3 -m py_compile scripts/*.py tests/*.py`：PASS
- `python3 -m unittest discover -s tests`：8/8 PASS
- `python3 scripts/report_lint.py --self-test`：PASS
- `python3 scripts/report_lint.py --fixtures tests/fixtures`：PASS
- Meta 报告 lint：PASS
- TTM 与估值计算独立复核：PASS

## 2026-06-30

### Change

- Added prior-report delta requirements to `SKILL.md` and `references/report-contract.md`.
- Added strict `Hold-Index` action boundaries so it cannot read like Buy-lite.
- Added confidence cap when current price, 10Y yield, or peer valuation depends on unconfirmed Tier 2 market data.
- Added 403 / blocked IR fallback guidance: use regulator archives first and record extraction failures.
- Extended `scripts/report_lint.py` to fail non-Buy reports that use buy-like language without an observation-only qualifier.
- Extended `scripts/report_lint.py` to require a prior-report delta section when `previous_report` or prior-report language is present.

### Reason

The 2026-06-29 CME report review found that the original draft could be read as a soft Buy despite a `Hold-Index` rating. It also showed that the most useful part of a rerun was the explicit comparison against the previous report, and that Tier 2 market data should not inherit high confidence from otherwise strong SEC filing evidence.

### Verification

- `python3 scripts/report_lint.py --self-test`
- `python3 scripts/report_lint.py "/Users/haoshifasheng/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/股票/CME/CME-CME Group-华尔街式分析报告-2026-06-29.md"`
- `python3 /Users/haoshifasheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/haoshifasheng/.agents/skills/wall-street-equity-research`

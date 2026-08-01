# Wall Street Equity Research Skill Change Log

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

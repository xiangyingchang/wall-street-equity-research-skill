# Wall Street Equity Research Skill Change Log

## 2026-07-24

### Change

- Limited `本次财报改变了什么 / 没有改变什么` to explicit latest-earnings update reports.
- Restored ordinary full-report `Key Forces` to business model, value drivers, and the 1-3 variables that determine intrinsic value.
- Updated the canonical template and lint rules so ordinary full reports no longer need fake earnings-update bullets.

### Reason

A general company initiation report should not pretend to be an earnings update. The old template and lint gate forced irrelevant wording and weakened the analytical focus of `Key Forces`.

### Verification

- `python3 scripts/report_lint.py --self-test`
- `python3 scripts/report_lint.py --fixtures tests/fixtures`
- `python3 /Users/muskxiang/.bg-agent/config-with-app/skills/skill-creator/scripts/quick_validate.py .`

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
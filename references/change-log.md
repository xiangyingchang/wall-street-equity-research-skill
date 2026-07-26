# Wall Street Equity Research Skill Change Log

## 2026-07-26

### Batch 1 — Decimal calculation rigor

**Change:** Added MIT-attributed, zero-dependency `scripts/validation_common.py` and `scripts/financial_rigor.py`; they share finite Decimal parsing, report-to-authority discrepancy, symmetric independent-source spread, and exact calculation. Positive and negative source order cannot reduce the spread.

**Reason:** Market-cap and valuation arithmetic must be reproducible, while <=1% is consistent, >1%-5% needs reconciliation, and >5% cannot enter analysis without Tier 1 verification.

**Verification:** `python3 scripts/financial_rigor.py --self-test` passed; 100 versus 106 blocks and large decimal literals retain Decimal precision.

### Batch 2 — Deterministic manual report audit

**Change:** Added MIT-attributed, zero-dependency `scripts/report_audit.py` with full-cell amount parsing, header-filtered eligible numeric columns, a >=15% denominator, eligible-universe hashes, generated results template, live-report manifest reconstruction, normalized vendor-domain independence, provenance structure, and manual-only reconciliation gates. Added the complete upstream notice in `references/third-party-notices.md`.

**Reason:** Extraction can prioritize review, but no script may silently fetch, refresh, or reconcile market evidence.

**Verification:** `python3 scripts/report_audit.py --self-test` and `python3 -m unittest tests/test_validation_cli.py` passed; eight CLI/parser tests cover canonical fixture extraction, full currency forms, malformed/empty/stale inputs, rehashed manifest tampering, same-vendor subdomains, report types, and positive/negative source order.

### Batch 3 — Market-aware validation policy

**Change:** Added `references/data-validation.md` and linked it from the runtime skill, report contract, and methodology; it documents the exact extract/template/verdict commands and human provenance boundary.

**Reason:** Tier 1 authority, practical Tier 2 checks, accounting/FX/date/unit/share-count differences, and historical price adjustment need a single explicit policy across US, Hong Kong, and A-share reports.

**Verification:** `references/data-validation.md`, the contract, and the methodology were cross-checked for the same Tier 1/Tier 2 rules.

### Batch 4 — Research-confidence boundary

**Change:** Added `references/researchability.md` as the single authority for deterministic A/B/C evidence coverage, AI confidence caps, investment certainty, and first-page decision confidence. Lint validates report type, values, and caps.

**Reason:** Evidence abundance measures research coverage, not investment quality; information scarcity alone is not a negative verdict.

**Verification:** `python3 scripts/report_lint.py --self-test` and `python3 scripts/report_lint.py --fixtures tests/fixtures` passed.

### Registry refresh

**Change:** Refactored `SKILL.md` to the LLM-first style guide: complete metadata, compact runtime rules, decision gates, output contract, and local references.

**Verification:** `python3 /Users/haoshifasheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py .` passed. Run `gentle-ai skill-registry refresh` before relying on updated metadata in a registry-driven environment.

### Batch 5 — Four-lens overlay

**Change:** Kept the authoritative Duan/Buffett/Munger/Li Lu mapping only in the methodology, reduced the runtime skill to a pointer, and limited the contract to observable unresolved-disagreement output; preserved the 2026-07-24 latest-earnings-only delta rule.

**Reason:** The overlay should sharpen existing analysis without creating a roleplay section or forcing ordinary reports to pretend they are earnings updates.

**Verification:** `report_lint` self-test includes an explicit earnings-update negative case, while the normal passing fixture contains no earnings-delta bullets.

### Batch 6 — Manifest v4 decision coverage and internal-source hardening

**Change:**

- Upgraded the audit manifest to v4 and force-included decision-critical fields when present: price, shares, market cap, cash, debt, TTM EPS, TTM FCF/share, 10Y yield, 2× yield, portfolio weight, and all EPS/FCF/EV-FCF payback outputs. The final selected count still determines the reported `actual_ratio`, and manifest/universe hashes remain deterministic.
- Classified Module 4 payback outputs from their metric columns before reading 10Y discount-row labels, preventing required-growth values from being mislabeled as government yields.
- Added the `Internal` portfolio evidence tier but restricted `portfolio_system` URLs to the exact canonical `https://github.com/xiangyingchang/portfolio-dashboard` repository after safe host/path case and trailing-slash normalization. Arbitrary, lookalike, credential-bearing, queried, or fragmented GitHub URLs are rejected.
- Added regressions for mandatory inclusion, payback/yield separation, exact repository approval, arbitrary GitHub rejection, missing manifest results, empty required fresh values, and invalid required sources.

**Reason:**

- A 15% hash sample could omit the values that directly drive an investment decision while still returning PASS.
- Broad 10Y label matching could demand yield provenance for payback-growth calculations.
- Trusting every `github.com` URL as an internal portfolio authority allowed attacker-controlled or fake repositories to masquerade as the canonical dashboard.
- Verdict must fail closed when any required manifest result, recomputed value, or source evidence is absent or invalid.

**Verification:** `python3 scripts/report_audit.py --self-test`, `python3 -m unittest discover -s tests`, `python3 scripts/report_lint.py --self-test`, and `python3 scripts/report_lint.py --fixtures tests/fixtures` passed. The current META report reconstructed manifest v4 at 25/63 eligible cells (39.68%), and all 25 required audit outcomes passed.

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

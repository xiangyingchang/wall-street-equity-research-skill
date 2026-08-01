# v2.0 Change Log — Single-Source Report Compiler

## 2026-08-01

### Change

- Replaced Markdown-first generation with a single `report-spec-v2` JSON source of truth.
- Added deterministic `report_pipeline_v2.py build/verify`.
- Added `report-bundle-v2` and generated Verification Manifest.
- Added deterministic renderer; Markdown is now a compiled view and cannot be safely hand-edited.
- Removed Legacy Compatibility Tables from all v2 reports.
- Added typed `global|bear|base|bull` assumptions and rejected cross-scenario references.
- Added mode-specific Revenue inputs:
  - guide midpoint;
  - guide high;
  - YoY;
  - QoQ;
  - explicit;
  - consensus.
- Added deterministic TTM, Revenue, EPS, Return Pair, Scenario Price, Payback, Decision, Robustness, and Price Zone compilation.
- Added separate `new_money_action` and `existing_position_action`.
- Added mandatory valuation-based Reduce/Review policy so “Hold = Buy” is executable.
- Moved tolerance and uncertainty into typed Policy/Fact fields; narrative text cannot change calculations.
- Added deterministic nominal and discounted payback root solving.
- Generated Price Zones from the same Base prices used by decisions.
- Added Spec, Bundle, and Markdown hashes plus tamper detection.
- Added Meta end-to-end Spec and golden expected outputs.
- Upgraded `SKILL.md` to v2.0.0.
- Added `references/report-spec-v2.md`, `references/decision-policy-v2.md`, and `templates/report-spec-v2.example.json`.
- Added explicit CI build + verify smoke test.

### Root cause addressed

v1.1-v1.5.1 fixed local arithmetic and consistency failures, but allowed the Agent to write the same economic concept repeatedly in Runtime tables, canonical tables, Legacy tables, price zones, and prose. Every additional checker reduced one class of errors while preserving the architecture that created the next class.

v2 changes the trust boundary:

```text
one typed Spec
→ one deterministic Bundle
→ one compiled Markdown report
→ one generated Verification Manifest
```

The report is no longer a second editable data model.

### Decision changes

- New-money and existing-position decisions are separate.
- SELL is reserved for thesis break.
- Material Base IRR shortfall can trigger REDUCE even when operating data is not yet broken.
- Explicit valuation review bands and operating tolerance/uncertainty determine REVIEW.
- Unstable robustness downgrades the existing-position action to REVIEW unless SELL independently triggers.

### Compatibility boundary

- v1.x reports continue to use legacy checkers.
- v2 reports use Spec + `report_pipeline_v2.py verify`.
- Compatibility tables are not emitted into v2 Markdown.

### Verification

GitHub Actions Validate run #129: PASS.

- Python syntax: PASS.
- financial rigor, report audit, and report lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **139 / 139 PASS**.
- v2 end-to-end build: PASS.
- v2 end-to-end verify: PASS.
- Markdown, Bundle, Verification file generation: PASS.
- Meta golden fixture: PASS.
- deterministic repeat build: PASS.
- Markdown tamper detection: PASS.
- Bundle tamper detection: PASS.
- Spec-change-without-rebuild detection: PASS.
- cross-scenario assumption rejection: PASS.
- missing valuation Reduce policy rejection: PASS.
- hidden narrative uncertainty isolation: PASS.
- guide-high versus midpoint test: PASS.
- deterministic payback monotonicity: PASS.
- Legacy Compatibility absence check: PASS.

### Integration

Before merging PR #7:

1. prepend this entry below the title in `references/change-log.md`;
2. delete `references/change-log-v2.0.md`;
3. preserve all historical entries;
4. rerun full CI;
5. merge only after Agent review and green CI;
6. regenerate Meta from a fresh `report-spec-v2` file, not from the old Markdown report.
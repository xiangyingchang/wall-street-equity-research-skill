# v2.1 Change Log — Evidence-Bound Research Layer

## 2026-08-01

### Change

- Upgraded new-report schema to `report-spec-v2.1` and bundle schema to `report-bundle-v2.1`.
- Added structured `SRC-*` Source Registry with title, publisher, date, tier, document type, locator, and scope.
- Required every Fact to reference registered Source IDs; critical company financial facts require Tier 1 evidence when available.
- Added structured Research Layer covering all nine modules.
- Added claim/text, evidence_refs, confidence, implication, counter-evidence, risk mechanism, indicators, triggers, and mitigants.
- Added evidence closure for `SRC-*`, `FACT-*`, and `BUNDLE:<path>` references.
- Added numeric-safety validation so research prose cannot introduce unbound prices, percentages, multiples, large numeric facts, thresholds, or actions.
- Added complete generated Source Registry, Evidence Ledger, Quarterly TTM Bridge, Scenario Assumption tables, modules 1-9, Claim-Evidence Matrix, and Verification summary.
- Restored module 4 as a mandatory Valuation and Payback research section.
- Added Moat minimum contract: four dimensions, scores, evidence, counter-evidence, and trajectory.
- Added Risk minimum contract: three ranked risks with mechanism, leading indicators, trigger, and mitigant.
- Added separate research explanations for new-money and existing-position decisions without allowing narrative to override Compiler actions.
- Updated `report_pipeline_v2.py` build/verify to use the v2.1 research compiler and enforce required report sections.
- Updated `SKILL.md` to v2.1.0.
- Added `references/research-layer-v2.1.md`.
- Added a complete Meta v2.1 Spec factory and end-to-end research-quality tests.
- Updated CI to generate, build, and verify a full v2.1 Meta report.

### Reason

v2.0 correctly established one numeric truth, but its first Meta report was a thin calculation summary: most modules contained one sentence, module 4 was absent, sources were vague, assumptions were hidden, and claims lacked evidence binding.

v2.1 preserves the Single-Source Compiler and adds a constrained Research Layer:

```text
one typed Spec
→ deterministic analytical Bundle
→ evidence-bound Research Layer
→ complete compiled Markdown
→ generated Verification Manifest
```

This avoids both previous failure modes: freehand Markdown inconsistency and compiler-generated research shallowness.

### Verification

GitHub Actions Validate run #164: PASS.

- Python syntax: PASS.
- financial rigor, audit, and lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **143 / 143 PASS**.
- v2.1 end-to-end build: PASS.
- v2.1 end-to-end verify: PASS.
- all nine modules present, including module 4: PASS.
- Source Registry, Evidence Ledger, Quarterly TTM Bridge, Scenario Assumptions, and Claim-Evidence Matrix: PASS.
- report depth threshold and thin-placeholder rejection: PASS.
- Markdown, Bundle, and Spec tamper detection: PASS.
- missing module, missing evidence, undefined source, and unbound numeric negative tests: PASS.
- cross-scenario assumption and missing valuation-policy negative tests: PASS.
- guide-high versus midpoint test: PASS.
- deterministic Payback and Price Zone tests: PASS.
- Legacy Compatibility absence check: PASS.

### Integration

PR #8 is stacked on PR #7.

Before final merge:

1. review and merge PR #7;
2. rebase or retarget PR #8 onto the updated main branch;
3. prepend this entry below the title in `references/change-log.md`;
4. delete `references/change-log-v2.1.md`;
5. preserve every historical change-log entry;
6. rerun the full CI suite;
7. regenerate Meta from a fresh v2.1 Spec and deliver Spec, Markdown, Bundle, and Verification together.

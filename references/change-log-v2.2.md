# v2.2 Change Log — Investment Narrative Layer

## 2026-08-01

### Change

- Added a Theme/Narrative layer between evidence-bound Claims and Reader rendering.
- Added Company Entity Registry to require company-, product-, segment-, technology-, or competitor-specific analysis.
- Added 3–5 core investment themes with:
  - category: business / capital / valuation;
  - thesis;
  - at least two mechanism claims;
  - counter-case and counter-evidence;
  - investment implication;
  - at least two validation signals.
- Added explicit Bull/Base/Bear adversarial debate with a Compiler-owned value anchor, path to win, earliest failure signal, and one key disagreement.
- Added a four-step causal financial bridge:

```text
operating change
→ cost / capex driver
→ margin / FCF effect
→ valuation implication
```

- Added a strict five-statement Mirror Test covering business essence, moat, valuation, largest risk, and action.
- Replaced the repeated “three core tensions” block with complete investment themes.
- Reworked Overview to show non-consensus and Bull/Base/Bear disagreement instead of repeating the first-page verdict.
- Added dynamic Narrative Quality checks:
  - themes completeness;
  - causal-chain completeness;
  - adversarial-debate completeness;
  - company specificity;
  - counter-evidence coverage;
  - mirror-test completeness;
  - narrative redundancy;
  - numeric argument density.
- Added `scripts/report_narrative_v22.py` and `scripts/report_renderer_narrative_v22.py`.
- Added `references/investment-narrative-v2.2.md`.
- Upgraded `SKILL.md`, report pipeline, Verification schema, Meta fixture, tests, and CI to v2.2.
- Preserved the v2.1.2 Reader/Audit split, Single-Source Compiler, evidence roles, value binding, decision formulas, and tamper detection.

### Lessons adopted from xbtlin/ai-berkshire

- Separate commercial, financial, competitive, and risk questions before synthesis.
- Preserve explicit tension between bullish and bearish interpretations instead of smoothing them into generic balance.
- Require a concise decision memo / mirror test that explains the investment in a few sentences.
- Treat abundant information as a reason to search for non-consensus and counter-evidence, not as proof of certainty.
- Force clear judgments and falsification conditions while allowing honest uncertainty.
- Do not require named-investor imitation or a specific multi-agent client; encode the useful discipline in the report contract.

### Reason

v2.1.2 was reliable and readable, but the report still behaved like a collection of polished claims rather than a true investment narrative. The same judgment could recur on the first page and in Overview; financial facts were often listed without explaining the causal path; moat, risks, and opportunity cost could remain generic; and Variant View was too short to expose the real disagreement.

v2.2 makes the argument explicit and falsifiable: what the company-specific theme is, how the mechanism affects earnings or cash flow, what evidence points the other way, what the investment implication is, and which future signal changes the conclusion.

### Scope boundary

- No valuation-formula or decision-policy changes.
- No mandatory multi-agent runtime dependency.
- No imitation of named investor personas.
- No new top-level report modules.
- No reduction in audit, evidence, source, or value-binding requirements.

### Verification

GitHub Actions `Validate` run #254 and final documentation run #261: PASS.

- Python syntax: PASS.
- financial rigor / report audit / report lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **169 / 169 PASS**.
- v2.2 Meta build: PASS.
- v2.2 Meta verify: PASS.
- 3 complete investment themes: PASS.
- 4-step causal financial bridge: PASS.
- Bull/Base/Bear debate: PASS.
- 7 company entities detected: PASS.
- 12 counter-evidence references: PASS.
- 5-statement Mirror Test: PASS.
- repeated legacy summary block absent: PASS.
- Reader/Audit separation and all tamper tests: PASS.

### Integration

Before merging PR #8:

1. prepend this entry, followed by v2.1.2, v2.1.1, and v2.1, below the title in `references/change-log.md`;
2. delete staged version change-log files;
3. preserve every historical entry;
4. retarget/rebase PR #8 onto main;
5. rerun the complete CI suite;
6. merge only after final Agent review and green CI;
7. regenerate Meta from a fresh v2.2 Spec and deliver Spec, Reader, Audit, Bundle, and Verification together.

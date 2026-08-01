# v3.0 Change Log — Research Graph and Investment Debate

## 2026-08-01

### Change

- Added `report-spec-v3.0` and `report-bundle-v3.0`.
- Added Research Graph: Source → Fact → Observation → Hypothesis → Challenge → Resolution → Theme → Narrative → Decision.
- Added 3–5 company-specific `THEME-*` objects and `OBS-*` observations.
- Required counter evidence in every challenge and evidence reconciliation in every resolution.
- Required Theme links to cover all nine research modules.
- Added Bull/Bear Investment Debate with at least three globally unique `ARG-*` arguments per side and Lead Adjudication.
- Prevented overlap/unknown debate IDs; omitted arguments are conservatively auto-discounted and disclosed.
- Added `DRV-*` Sensitivity Explanation with real Assumption Registry binding, canonical path normalization, direction, importance, mechanism, cases, and decision consequence.
- Added multi-perspective workflow inspired by AI Berkshire without copying persona scores or requiring a specific agent runtime.
- Added Theme-based Reader narrative, strongest challenge, falsification, Sensitivity Explanation, and Bull/Bear Debate.
- Added complete Graph structures to Audit and escaped all Graph table cells.
- Added independent v3 compiler, renderer, build, and verify pipeline.
- Build now blocks before writing invalid Reader/Audit artifacts.
- Verification statuses are derived from real graph and render checks rather than hard-coded PASS.
- Upgraded `SKILL.md` to v3.0.0.
- Added Meta v3 fixture, graph contract, focused tests, and CI validation.

### Reason

v2.1.2 was reliable and readable but still treated isolated Claims as the core research unit. It could state conclusions without consistently explaining causality, testing alternatives, adjudicating competing views, or identifying which assumptions control the decision.

v3 adds the missing research-process layer while preserving numeric truth and audit boundaries.

### What was learned from AI Berkshire

Adopted: independent perspectives, adversarial analysis, anti-bias challenge, Lead Analyst adjudication, and separation of exact calculation from prose.

Not adopted: persona-based master scores, fixed famous-investor roles, dependency on a specific subagent framework, or averaging conflicting opinions.

### Code review fixes

Independent review found and fixed:

- Theme links did not guarantee all nine modules were covered;
- Bull and Bear could reuse an Argument ID;
- Adjudication sets could overlap or silently omit arguments;
- concise Chinese implications were rejected by the old length gate;
- Sensitivity paths were not resolved against the real registry;
- fixture paths were invalid;
- Graph Audit tables did not escape pipes/newlines;
- build could write artifacts before validating render contracts;
- Verification statuses were hard-coded;
- v3 compiler did not reject legacy schema.

### Verification

GitHub Actions Validate run #289: PASS.

- Python syntax: PASS.
- financial rigor / audit / lint: PASS.
- full unittest suite: 168 / 168 PASS.
- v2.1.2 regression: PASS.
- v3 Meta build / verify: PASS.
- 3 Themes, 6 Observations, 3 Bull, 3 Bear, 3 Drivers, 2 High.
- Reader narrative / Sensitivity / Debate: PASS.
- Reader internal-ID exclusion: PASS.
- Audit Graph and escaping: PASS.
- build-time Reader/Audit gates: PASS.
- dynamic Verification: PASS.
- Graph/Reader/Audit/Bundle/Verification tamper binding: PASS.

### Integration

PR #9 is stacked on v2.1.2. Before merge: merge PR #8; rebase or retarget PR #9 to main; rerun complete CI; prepend this entry to the main change log; delete the staged file; preserve history.
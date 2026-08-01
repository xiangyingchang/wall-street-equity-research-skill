# v2.1.1 Change Log — Research Quality Binding

## 2026-08-01

### Change

- Added `text_template` / `claim_template` plus `value_refs` so research prose can embed compiler-owned values.
- Added JSON Pointer value paths and support for decimal dictionary keys.
- Added value formatting for money, percent, multiple, number, integer, and text.
- Upgraded evidence refs to typed `{ref, role}` objects.
- Added evidence roles: supports, context, and counter_evidence.
- Required at least one supporting evidence ref for every Claim.
- Replaced hard-coded research-quality flags with validator-generated counts and statuses.
- Generated Verification and Markdown quality summaries from actual Research Quality results.
- Added risk confidence validation and unique/consecutive rank enforcement.
- Added Source scope versus Fact-category validation.
- Added Markdown table escaping for pipes and line breaks.
- Strengthened Verification to compare the complete generated Verification artifact.
- Upgraded Skill, Spec, Bundle, and Verification schemas to v2.1.1.
- Added `references/research-quality-binding-v2.1.1.md`.
- Added 12 focused v2.1.1 tests and end-to-end CI assertions.

### Reason

v2.1 restored complete research structure, but prose could not directly use core valuation numbers; evidence only needed to exist rather than carry a declared logical role; quality statuses were hard-coded; dot paths were fragile for decimal keys; and several validation boundaries remained weak. v2.1.1 makes the Research Layer numerically integrated and honestly verified without changing the Single-Source Compiler architecture.

### Verification

GitHub Actions `Validate` run #190: PASS.

- Python syntax: PASS.
- financial rigor / report audit / report lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **155 / 155 PASS**.
- v2.1.1 build and verify: PASS.
- Meta prose renders Base IRR `5.51%`, target return `9.40%`, and target-return price `$456.67`: PASS.
- Research quality output: 9 modules, 37 claims, 88 supporting refs, 3 bound values, 9 sources.
- missing value ref / invalid JSON Pointer / missing supporting evidence / invalid evidence role negative tests: PASS.
- invalid risk confidence / duplicate rank / source-scope mismatch negative tests: PASS.
- Markdown table escaping: PASS.
- Spec / Bundle / Markdown / Verification tamper detection: PASS.

### Scope boundary

- Does not automatically judge whether evidence economically proves a claim.
- Does not use an LLM judge as a hard gate.
- Does not change the Single-Source Compiler architecture.
- Does not add research modules or portfolio optimization.

### Integration

Before merging PR #8:

1. confirm PR #7 is merged;
2. rebase or retarget PR #8 onto main;
3. prepend v2.1.1 and v2.1 entries below the title in `references/change-log.md`;
4. delete both staged change-log files without altering history;
5. rerun the full CI suite;
6. merge only after final Agent review and green CI.

# v2.2 Change Log — Investment Narrative Layer

## 2026-08-01

### Planned change

- Add a Theme/Narrative layer between evidence-bound Claims and Reader rendering.
- Add Company Entity Registry to enforce company-specific analysis.
- Require 3–5 core investment themes with mechanism chains, counter-cases, investment implications, and validation signals.
- Add explicit Bull/Bear/Base adversarial debate and a single key disagreement.
- Add a causal financial bridge from operating change to cost/capex, margin/FCF, and valuation consequence.
- Add a five-sentence Mirror Test covering business essence, moat, valuation, risk, and action.
- Reduce repeated summary language across First Page, Core Tensions, and Overview.
- Add dynamic Narrative Quality checks for theme completeness, causal chains, debate, company specificity, counter-evidence, mirror test, redundancy, and numeric argument density.
- Keep the v2.1.2 Reader/Audit split, Single-Source Compiler, evidence roles, value binding, and tamper detection unchanged.

### Lessons adopted from xbtlin/ai-berkshire

- Separate commercial, financial, competitive, and risk questions before synthesis.
- Preserve explicit tension between bullish and bearish interpretations instead of smoothing them into generic balance.
- Require a concise decision memo / mirror test that can explain the investment in a few sentences.
- Treat abundant information as a reason to search for non-consensus and counter-evidence, not as proof of certainty.
- Force clear judgments and falsification conditions while allowing honest uncertainty.

### Scope boundary

- No valuation formula or decision-policy changes.
- No mandatory multi-agent runtime dependency.
- No imitation of named investor personas.
- No new top-level report modules.
- No reduction in audit or source requirements.

### Verification target

- missing themes/debate/mirror test fails;
- generic themes without company entities fail;
- themes without mechanism, counter-evidence, or validation signals fail;
- incomplete causal financial bridge fails;
- Bull/Bear/Base cases without compiler-owned values fail;
- mirror test longer than five sentences or missing a required dimension fails;
- repeated Reader summary blocks fail redundancy checks;
- Reader contains core themes, adversarial debate, causal financial explanation, and mirror test;
- full unittest, lint, self-tests, and Meta build/verify pass.

### Integration

After implementation and validation:

1. replace this planned entry with actual implementation and exact results;
2. prepend v2.2 below the title in `references/change-log.md`;
3. delete `references/change-log-v2.2.md`;
4. mark `PRD-investment-narrative-layer-v2.2.md` completed;
5. rerun CI before merge.

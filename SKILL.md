---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 脱水质检, 10年回本测试, 估值审判, 值不值, or 该不该买. Produce evidence-bound single-stock research."
license: MIT
metadata:
  author: xiangyingchang
  version: "2.2"
---

## Activation Contract

Use for one listed equity when the user requests valuation, buy/hold/sell judgment, a full report, or the trigger phrases above. In the Obsidian stock vault, a ticker or 跑一下/分析下 means a complete saved report unless the user explicitly asks for a quick take.

## v2.2 Trust Boundary

A new report has exactly one editable analytical source:

```text
<report>.spec.json   (report-spec-v2.2)
```

The compiler produces four immutable views:

```text
<report>.md                  Reader Report
<report>.audit.md            Audit Appendix
<report>.md.bundle.json      Analytical Bundle
<report>.md.verification.json
```

The Bundle remains the single numeric truth. The Narrative Layer organizes facts and claims into an investment argument. The Reader Report communicates that argument. The Audit Appendix preserves complete traceability. Neither Markdown file may be hand-edited.

## Hard Rules

- Never invent prices, filings, yields, facts, sources, evidence references, company entities, or causal claims. Tier 1 evidence wins conflicts.
- New reports must use the v2.2 narrative pipeline; v1.x Markdown-first and earlier v2 renderers are historical-only.
- Build with:

```bash
python3 scripts/report_pipeline_v2.py build --spec <report>.spec.json --output <report>.md
```

- Verify with:

```bash
python3 scripts/report_pipeline_v2.py verify --spec <report>.spec.json --output <report>.md
```

- Delivery requires Spec, Reader Markdown, Audit Markdown, Bundle, and Verification together.
- No Legacy Compatibility Tables. Compatibility belongs in code, never in either report layer.
- Facts, quarterly series, assumptions, scenarios, decision policy, research claims, narrative themes, evidence roles, company entities, and sources live only in the Spec.

### Dual-layer rendering

- Reader Report is for investment communication. It must be readable without understanding internal IDs or compiler implementation.
- Audit Appendix is for Agent review, reproducibility, evidence tracing, and validation.
- Reader Report must not contain Build Manifest, hashes, Source Registry, Evidence Ledger, internal IDs, full Assumption Registry, raw Decision Policy fields, Claim-Evidence Matrix, or Verification table.
- Audit Appendix must contain all of those audit structures.
- Reader Report must contain all nine modules, the core investment themes, Bull/Base/Bear debate, financial causal bridge, mirror test, and key decision numbers.
- Reader Report target length is 140–340 Markdown lines; Audit Appendix has no line limit.
- Evidence shown in the Reader Report uses human-readable source titles, not internal IDs.

### Numeric ownership and value binding

- TTM, Revenue, EPS, IRR, Reverse Expectations, prices, payback, actions, robustness, and price zones are compiler outputs.
- Research and Narrative text may not introduce unbound currency values, percentages, multiples, large numeric facts, thresholds, or actions.
- To use a number in prose, define `text_template` or `claim_template` with `value_refs`.
- Every `value_refs.path` uses JSON Pointer, for example `/decision/valuation/base_irr`.
- Supported formats are `money|percent|multiple|number|integer|text`.
- Template placeholders and `value_refs` keys must match exactly.
- Tolerance and uncertainty exist only in typed Facts/Policy. Narrative cannot add hidden buffers.

### Evidence roles

- Evidence refs are typed objects: `{ref, role}`.
- Allowed roles: `supports`, `context`, `counter_evidence`.
- Every key claim requires at least one `supports` ref.
- Every core Narrative Theme requires at least one `counter_evidence` ref.
- Evidence roles remain visible in Audit Appendix; Reader Report shows only human-readable source summaries.
- Moat dimensions require explicit counter-evidence text; valuation and final-verdict claims must state sensitivity or falsification boundaries.

### Sources and facts

- `sources` is a structured `SRC-*` registry, not a list of publisher names.
- Every Source requires title, publisher, date, tier, document type, locator, and scope.
- Every Fact requires `source_ids` that resolve to registered Sources.
- Source scope must cover the Fact metric category.
- Critical company financial facts require Tier 1 evidence when available; current market price may use Tier 2 with explicit confidence.
- Network-effects claims require user/engagement evidence.

### Assumptions and scenarios

- Assumption scope is `global|bear|base|bull`. A scenario may reference only its own or global assumptions.
- Revenue modes are typed: `guide_midpoint`, `guide_high`, `yoy`, `qoq`, `explicit`, or `consensus`.
- Every future numeric input requires a typed Assumption.
- Historical adjustments may support assumptions but are not direct Forward EPS formula inputs.

### Investment Narrative Layer

The Spec must include `company_entities` and `narrative`.

- `company_entities` contains at least four company-, product-, platform-, segment-, or competitor-specific entities.
- `narrative.themes` contains 3–5 themes.
- Themes must collectively cover `business`, `capital`, and `valuation`.
- Every Theme requires:
  - unique `THEME-*` ID;
  - company-specific title and thesis;
  - at least two mechanism claims;
  - investment implication;
  - counter-case with counter-evidence;
  - at least two validation signals.
- Theme titles may not be near-duplicates.
- Generic phrases such as “network effects, data, ecosystem, capital” are insufficient unless tied to specific products, segments, users, competitors, or operating mechanisms.

### Adversarial debate

- `narrative.debate` must include Bull Case, Base Case, Bear Case, and one key disagreement.
- Each Case must state:
  - thesis;
  - Compiler-owned value anchor;
  - path to win;
  - earliest failure signal.
- Do not smooth Bull and Bear into generic balance. The report must reveal the variable on which the two sides truly disagree.
- Named-investor personas are optional inspiration, never a required output style.

### Causal financial bridge

The financial narrative must explicitly connect:

```text
operating change
→ cost / capex driver
→ margin / cash-flow effect
→ valuation implication
```

At least one quarterly comparison and one capital-allocation mechanism must be bound to evidence or Compiler-owned values. “Revenue strong, FCF weak” without causal explanation is incomplete.

### Mirror test

The final report must contain exactly five concise statements covering:

1. business essence;
2. moat;
3. current valuation;
4. largest risk;
5. current action.

Any number or action in the Mirror Test must come from `value_refs` or the Compiler.

### Decision policy

- Decision Policy includes valuation, operating, and thesis-break dimensions.
- Output two decisions:
  - `new_money_action`: BUY / WATCH / DO_NOT_BUY;
  - `existing_position_action`: HOLD / REVIEW / REDUCE / SELL.
- SELL is reserved for thesis break. REDUCE may result from material valuation shortfall or operating deterioration.
- If robustness changes the existing-position action, resolve to REVIEW unless SELL independently triggers.
- Price-zone semantics and action rules use the same Base prices.

### Reader Report contract

The Reader Report follows this order:

1. One-page verdict;
2. Core investment narrative themes;
3. Overview and Bull/Base/Bear debate;
4. Financial Autopsy and causal bridge;
5. Moat;
6. Valuation and Payback;
7. Risk Ranking;
8. Growth Limits;
9. Opportunity Cost;
10. Positioning;
11. Final Verdict and Mirror Test;
12. concise source list and Audit Appendix pointer.

Writing requirements:

- Lead with judgment, then mechanism, evidence, counter-case, and validation boundary.
- Do not repeat the same three summary points in One-page Verdict, Core Narrative, and Overview.
- Merge related claims into continuous prose; do not render every claim as a repeated claim/implication/evidence/confidence card.
- Embed compiler-owned key numbers naturally in the argument.
- Use tables only when comparison is clearer than prose.
- Translate program enums into natural Chinese in the Reader Report.
- Do not expose machine-oriented labels such as `base IRR materially below hurdle`.
- Company-specific entities and mechanisms must appear throughout Moat, Risks, Opportunity Cost, and Themes.

### Audit Appendix contract

The Audit Appendix must preserve:

- Build Manifest;
- Source Registry;
- Evidence Ledger;
- Quarterly TTM Bridge;
- Scenario Assumptions and Valuation;
- Payback Stress Test;
- Decision Policy Evaluation and Robustness;
- Price Zones;
- all nine research modules with evidence roles;
- Claim-Evidence Matrix;
- Investment Narrative Theme definitions and debate;
- dynamic Research Quality, Narrative Quality, and Verification summaries.

### Research and Narrative quality

- `research_quality` and `narrative_quality` are computed by validators; they may not be hard-coded.
- Narrative Quality must validate theme completeness, causal chains, adversarial debate, company specificity, counter-evidence, mirror test, redundancy, and numeric argument density.
- Verification must include both `reader_markdown_hash` and `audit_markdown_hash`.
- `verify` recompiles Reader Report, Audit Appendix, Bundle, and Verification, and compares all four outputs.
- Modifying any generated file without rebuilding must fail verification.
- Markdown table cells must escape pipes and newlines.

## Decision Gates

| Condition | Required result |
|---|---|
| Missing/conflicting critical facts | Fail build or explicitly lower confidence; never fill by inference. |
| Fact references missing Source or incompatible Source scope | Fail build. |
| Key claim lacks supporting evidence | Fail build. |
| Theme lacks company entity, mechanism chain, counter-evidence, or validation signal | Fail build. |
| Bull/Base/Bear debate or key disagreement missing | Fail build. |
| Causal financial bridge incomplete | Fail build. |
| Mirror Test not exactly five required dimensions | Fail build. |
| Research references missing Fact/Source/Bundle JSON Pointer | Fail build. |
| Value placeholder/path/format invalid | Fail build. |
| Research module missing or structurally thin | Fail build. |
| Free narrative introduces unbound numeric content | Fail build. |
| Scenario references another scenario's assumption | Fail build. |
| Decision Policy lacks valuation Reduce/Review | Fail build. |
| Base IRR materially below hurdle | Existing-position action cannot resolve to HOLD. |
| Robustness is unstable | Existing-position action becomes REVIEW unless SELL triggers. |
| Reader repeats legacy summary blocks | Verify fails. |
| Reader Report contains audit IDs, registries, hashes, or Claim-Evidence Matrix | Verify fails. |
| Audit Appendix lacks required audit structures | Verify fails. |
| Reader Report outside readability budget | Verify fails. |
| Any generated output differs from compiler output | Verify fails; do not deliver. |
| Legacy Compatibility Tables appear | Verify fails. |

## Execution Steps

1. Collect ticker, tax identity, horizon, current holding, target return, market price, latest filings, quarterly facts, user/engagement data, peers, risk-free rate, and source metadata.
2. Start from a v2.2 Spec example or the Meta fixture structure. Never start from an old Markdown report.
3. Register Sources, Facts, quarterly series, assumptions, Decision Policy, all nine research modules, and Company Entity Registry.
4. Form 3–5 Narrative Themes only after the evidence and scenarios are assembled.
5. For each Theme, write mechanism chain, counter-case, investment implication, and validation signals.
6. Write Bull/Base/Bear debate and identify the single key disagreement.
7. Write the financial causal bridge and five-statement Mirror Test.
8. Use typed evidence roles and `value_refs` whenever prose needs a number.
9. Run `build`; confirm all four generated artifacts exist.
10. Read the Reader Report first. It should make sense without opening the Audit Appendix.
11. Review the Audit Appendix for source closure, assumptions, evidence roles, Narrative Quality, and verification.
12. Run `verify`.
13. Deliver only when Reader, Audit, Bundle, and Verification all match compiler output.

## Output Contract

Return:

- Spec path;
- Reader Markdown path;
- Audit Markdown path;
- Bundle path;
- Verification path;
- new-money action;
- existing-position action;
- Base IRR, target-return price, and buy price;
- principal uncertainty and key disagreement;
- verify result.

The Reader Report must be readable, company-specific, adversarial, causal, and decision-oriented. The Audit Appendix must be exhaustive and machine-auditable. Neither may substitute for the other.

## Legacy Boundary

- Existing v1.x reports may still use legacy checkers.
- Earlier v2 reports may be inspected, but new reports must use v2.2 Narrative rendering.
- Never generate a new report from `templates/full-report.md`.
- Never add compatibility tables to a compiled report.
- `report_pipeline_v2.py verify` is authoritative for v2.2.

## References

- `PRD-single-source-report-compiler-v2.md` — single-source architecture.
- `PRD-evidence-bound-research-layer-v2.1.md` — research-layer architecture.
- `PRD-research-quality-binding-v2.1.1.md` — value binding and evidence roles.
- `PRD-reader-first-dual-layer-renderer-v2.1.2.md` — Reader/Audit separation.
- `PRD-investment-narrative-layer-v2.2.md` — theme, debate, causal bridge, and mirror-test contract.
- `references/report-spec-v2.md` — numeric Spec contract.
- `references/decision-policy-v2.md` — decision resolution.
- `references/research-layer-v2.1.md` — source, claim, module, and numeric-safety contract.
- `references/investment-narrative-v2.2.md` — narrative authoring and validation guide.
- `tests/meta_v21_factory.py` / `tests/meta_v21_spec.py` — complete Meta reference Spec.

## Skill 维护纪律（强制）

Any behavior change must follow this order:

1. write/update PRD;
2. stage change log;
3. implement code, contract, and tests;
4. run complete end-to-end fixture plus full CI;
5. finalize PRD and change log before merge.

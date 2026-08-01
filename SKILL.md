---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 脱水质检, 10年回本测试, 估值审判, 值不值, or 该不该买. Produce evidence-bound single-stock research."
license: MIT
metadata:
  author: xiangyingchang
  version: "2.1.2"
---

## Activation Contract

Use for one listed equity when the user requests valuation, buy/hold/sell judgment, a full report, or the trigger phrases above. In the Obsidian stock vault, a ticker or 跑一下/分析下 means a complete saved report unless the user explicitly asks for a quick take.

## v2.1.2 Trust Boundary

A new report has exactly one editable analytical source:

```text
<report>.spec.json   (report-spec-v2.1.1)
```

The compiler produces four immutable views:

```text
<report>.md                  Reader Report
<report>.audit.md            Audit Appendix
<report>.md.bundle.json      Analytical Bundle
<report>.md.verification.json
```

The Bundle remains the single numeric truth. The Reader Report communicates the investment argument. The Audit Appendix preserves complete traceability. Neither Markdown file may be hand-edited.

## Hard Rules

- Never invent prices, filings, yields, facts, sources, or evidence references. Tier 1 evidence wins conflicts.
- New reports must use the v2.1.2 dual-layer pipeline; v1.x Markdown-first and earlier v2 renderers are historical-only.
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
- Facts, quarterly series, assumptions, scenarios, decision policy, research claims, evidence roles, and sources live only in the Spec.

### Dual-layer rendering

- Reader Report is for investment communication. It must be readable without understanding internal IDs or compiler implementation.
- Audit Appendix is for Agent review, reproducibility, evidence tracing, and validation.
- Reader Report must not contain:
  - Build Manifest or hashes;
  - Source Registry or Evidence Ledger;
  - `FACT-*`, `BUNDLE:*`, `SRC-*`, `[supports]`, or other internal reference syntax;
  - full Scenario Assumption Registry;
  - raw Decision Policy fields;
  - Claim-Evidence Matrix;
  - Verification table.
- Audit Appendix must contain all of the above audit structures.
- Reader Report must contain all nine modules and the key decision numbers needed to understand the conclusion.
- Reader Report target length is 120–300 Markdown lines; Audit Appendix has no line limit.
- Evidence shown in the Reader Report uses human-readable source titles, not internal IDs.

### Numeric ownership and value binding

- TTM, Revenue, EPS, IRR, Reverse Expectations, prices, payback, actions, robustness, and price zones are compiler outputs.
- Research text may not introduce unbound currency values, percentages, multiples, large numeric facts, thresholds, or actions.
- To use a number in prose, define `text_template` or `claim_template` with `value_refs`.
- Every `value_refs.path` uses JSON Pointer, for example `/decision/valuation/base_irr`.
- Supported formats are `money|percent|multiple|number|integer|text`.
- Template placeholders and `value_refs` keys must match exactly.
- Tolerance and uncertainty exist only in typed Facts/Policy. Narrative cannot add hidden buffers.

### Evidence roles

- Evidence refs are typed objects: `{ref, role}`.
- Allowed roles: `supports`, `context`, `counter_evidence`.
- Every key claim requires at least one `supports` ref.
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
2. Three core tensions;
3. Overview;
4. Financial Autopsy;
5. Moat;
6. Valuation and Payback;
7. Risk Ranking;
8. Growth Limits;
9. Opportunity Cost;
10. Positioning;
11. Final Verdict;
12. concise source list and Audit Appendix pointer.

Writing requirements:

- Lead with judgment, then evidence, then boundaries.
- Merge related claims into continuous prose; do not render every claim as a repeated claim/implication/evidence/confidence card.
- Embed compiler-owned key numbers naturally in the argument.
- Use tables only when comparison is clearer than prose.
- Translate program enums into natural Chinese in the Reader Report.
- Do not expose machine-oriented labels such as `base IRR materially below hurdle`.

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
- dynamic Verification summary.

### Research completeness

All nine modules remain mandatory:

1. Overview;
2. Financial Autopsy;
3. Moat;
4. Valuation and Payback;
5. Risk Ranking;
6. Growth Limits;
7. Opportunity Cost;
8. Positioning;
9. Final Verdict.

Each research object requires evidence refs, at least one supports role, and confidence. A one-sentence free-form module is not a valid report.

### Research quality and verification

- `research_quality` is computed by validators; it may not be hard-coded.
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
| Research references missing Fact/Source/Bundle JSON Pointer | Fail build. |
| Value placeholder/path/format invalid | Fail build. |
| Research module missing or structurally thin | Fail build. |
| Free narrative introduces unbound numeric content | Fail build. |
| Scenario references another scenario's assumption | Fail build. |
| Decision Policy lacks valuation Reduce/Review | Fail build. |
| Base IRR materially below hurdle | Existing-position action cannot resolve to HOLD. |
| Robustness is unstable | Existing-position action becomes REVIEW unless SELL triggers. |
| Reader Report contains audit IDs, registries, hashes, or Claim-Evidence Matrix | Verify fails. |
| Audit Appendix lacks required audit structures | Verify fails. |
| Reader Report outside readability budget | Verify fails. |
| Any generated output differs from compiler output | Verify fails; do not deliver. |
| Legacy Compatibility Tables appear | Verify fails. |

## Execution Steps

1. Collect ticker, tax identity, horizon, current holding, target return, market price, latest filings, quarterly facts, user/engagement data, peers, risk-free rate, and source metadata.
2. Start from a v2.1.1 Spec example or the Meta factory structure. Never start from an old Markdown report.
3. Register Sources, Facts, quarterly series, assumptions, Decision Policy, and all nine research modules.
4. Use typed evidence roles and `value_refs` whenever prose needs a number.
5. Run `build`; confirm all four generated artifacts exist.
6. Read the Reader Report first. It should make sense without opening the Audit Appendix.
7. Review the Audit Appendix for source closure, assumptions, evidence roles, and verification.
8. Run `verify`.
9. Deliver only when Reader, Audit, Bundle, and Verification all match compiler output.

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
- principal uncertainty;
- verify result.

The Reader Report must be readable and decision-oriented. The Audit Appendix must be exhaustive and machine-auditable. Neither may substitute for the other.

## Legacy Boundary

- Existing v1.x reports may still use legacy checkers.
- Earlier v2 reports may be inspected, but new reports must use v2.1.2 dual-layer rendering.
- Never generate a new report from `templates/full-report.md`.
- Never add compatibility tables to a compiled report.
- `report_pipeline_v2.py verify` is authoritative for v2.1.2.

## References

- `PRD-single-source-report-compiler-v2.md` — single-source architecture.
- `PRD-evidence-bound-research-layer-v2.1.md` — research-layer architecture.
- `PRD-research-quality-binding-v2.1.1.md` — value binding and evidence roles.
- `PRD-reader-first-dual-layer-renderer-v2.1.2.md` — Reader/Audit separation and readability contract.
- `references/report-spec-v2.md` — numeric Spec contract.
- `references/decision-policy-v2.md` — decision resolution.
- `references/research-layer-v2.1.md` — source, claim, module, and numeric-safety contract.
- `tests/meta_v21_factory.py` / `tests/meta_v21_spec.py` — complete Meta reference Spec.

## Skill 维护纪律（强制）

Any behavior change must follow this order:

1. write/update PRD;
2. stage change log;
3. implement code, contract, and tests;
4. run complete end-to-end fixture plus full CI;
5. finalize PRD and change log before merge.

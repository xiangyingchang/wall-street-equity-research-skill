---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 脱水质检, 10年回本测试, 估值审判, 值不值, or 该不该买. Produce evidence-bound, adversarial single-stock research."
license: MIT
metadata:
  author: xiangyingchang
  version: "3.0.0"
---

## Activation Contract

Use for one listed equity when the user requests valuation, buy/hold/sell judgment, a full report, or the trigger phrases above. A ticker plus 跑一下/分析下 means a complete saved report unless the user asks for a quick take.

## v3 Trust Boundary

A new report has one editable analytical source:

```text
<report>.spec.json   (report-spec-v3.0)
```

The v3 compiler produces four immutable artifacts:

```text
<report>.md                  Reader Report
<report>.audit.md            Audit Appendix
<report>.md.bundle.json      Analytical Bundle
<report>.md.verification.json
```

The Bundle is the single numeric truth. The Reader Report communicates the investment argument. The Audit Appendix preserves complete traceability. Generated files may not be hand-edited.

## Build and Verify

```bash
python3 scripts/report_pipeline_v3.py build \
  --spec <report>.spec.json \
  --output <report>.md

python3 scripts/report_pipeline_v3.py verify \
  --spec <report>.spec.json \
  --output <report>.md
```

Delivery requires Spec, Reader, Audit, Bundle, and Verification together.

## Hard Rules

- Never invent prices, filings, yields, facts, sources, assumptions, evidence references, graph nodes, or debate arguments.
- New reports use v3. v1.x and v2.x pipelines are historical or migration paths only.
- No Legacy Compatibility Tables.
- Facts, assumptions, research claims, Research Graph, debate, sensitivity, and policy live only in the Spec.
- Calculated numbers and actions live only in the Bundle.
- Reader and Audit are compiler-owned views.

## Single Numeric Truth

- TTM, Revenue, EPS, IRR, Reverse Expectations, prices, payback, actions, robustness, and price zones are compiler outputs.
- Research text may not introduce unbound currency values, percentages, multiples, large numeric facts, thresholds, or actions.
- Numeric prose uses `text_template` / `claim_template` with `value_refs` JSON Pointers.
- Supported formats: `money|percent|multiple|number|integer|text`.
- Tolerance and uncertainty exist only in typed Facts or Decision Policy.

## Sources, Facts, and Evidence

- Sources use `SRC-*` and require title, publisher, date, tier, document type, locator, and scope.
- Facts use `FACT-*` and require resolvable `source_ids`.
- Critical financial facts require Tier 1 evidence when available; market price may use Tier 2 with explicit confidence.
- Evidence refs are typed: `supports|context|counter_evidence`.
- Every key claim requires supporting evidence.
- Network-effect claims require user or engagement evidence.

## Research Graph v3

The required research chain is:

```text
Source → Fact → Observation → Hypothesis → Challenge
       → Resolution → Theme → Narrative → Decision
```

Every report defines 3–5 company-specific Investment Themes. Each Theme requires:

- `THEME-*` ID;
- specific title and core question;
- at least two `OBS-*` observations;
- hypothesis;
- strongest challenge;
- resolution;
- decision impact;
- falsification condition;
- at least two linked research modules.

Rules:

- Theme titles such as “财务表现”“估值”“风险” are too generic.
- Challenge requires `counter_evidence`.
- Resolution must address both supporting and counter evidence.
- Decision impact must reference Bundle values or actions.
- Observation IDs may not be reused.
- Reader narrative follows: what happened → why → strongest objection → resolution → decision impact → falsification.

## Investment Debate

Every report contains a formal Bull/Bear debate:

- Bull: at least three evidence-bound `ARG-*` arguments;
- Bear: at least three evidence-bound `ARG-*` arguments;
- Adjudication: accepted points, discounted points, decisive evidence, remaining uncertainty, and why the current action follows.

The Bull case must be the strongest credible version, not a straw man. The Bear case must identify causal failure paths, not generic risk labels. Adjudication must reference argument IDs from both sides and may not invent an unsupported third view.

## Sensitivity Explanation

Every report contains at least three `DRV-*` drivers. Each driver requires:

- variable;
- base assumption path;
- direction: `positive|negative|mixed`;
- importance: `high|medium|low`;
- mechanism;
- upside case;
- downside case;
- decision consequence;
- evidence refs.

At least one driver must be high importance. Explain which variables dominate Base IRR and target-return price; do not merely print a sensitivity table.

## Multi-Perspective Research Adapter

Borrow the process, not the personas, from multi-agent research systems.

Preferred independent roles:

1. business analyst — business model, customer value, moat observations;
2. financial analyst — financial bridge, valuation, sensitivity observations;
3. industry challenger — competition, non-consensus evidence, strongest challenge;
4. risk assessor — failure mechanisms, leading indicators, falsification;
5. lead analyst — resolutions, debate adjudication, narrative, final decision.

When subagents are available, run the first four independently and in parallel. When they are unavailable, simulate them sequentially with separate passes. They must write structured nodes into one Spec; they must never edit Markdown or average scores mechanically.

## Assumptions and Scenarios

- Assumption scope is `global|bear|base|bull`.
- A scenario may reference only its own or global assumptions.
- Revenue modes are typed: `guide_midpoint|guide_high|yoy|qoq|explicit|consensus`.
- Every future numeric input requires a typed assumption.
- Historical adjustments may support assumptions but are not direct forward formula inputs.

## Decision Policy

Output two decisions:

- `new_money_action`: BUY / WATCH / DO_NOT_BUY;
- `existing_position_action`: HOLD / REVIEW / REDUCE / SELL.

SELL is reserved for thesis break. REDUCE may result from material valuation shortfall or operating deterioration. If robustness changes the existing-position action, resolve to REVIEW unless SELL independently triggers. Research narrative may explain but may not override compiler actions.

## Reader Report Contract

The Reader Report must:

- lead with the one-page verdict;
- explain 3–5 Theme narratives;
- contain all nine fixed modules;
- include sensitivity explanation and Bull/Bear debate;
- embed compiler-owned numbers naturally;
- use human-readable source titles;
- state what would falsify the conclusion;
- avoid repeated summary language and generic company-agnostic prose.

It must not contain internal IDs, Bundle paths, hashes, registries, Claim-Evidence Matrix, or raw Verification fields.

## Audit Appendix Contract

The Audit Appendix must preserve:

- Build Manifest;
- Source Registry;
- Evidence Ledger;
- Quarterly TTM Bridge;
- Scenario Assumptions and Valuation;
- Payback and Decision Policy;
- Research Graph nodes;
- Bull/Bear arguments and Adjudication IDs;
- Sensitivity drivers;
- all evidence roles;
- Claim-Evidence Matrix;
- dynamic Verification.

## Nine Fixed Modules

1. Investment Narrative / Overview;
2. Financial Autopsy;
3. Moat;
4. Valuation and Payback;
5. Risk Ranking;
6. Growth Limits;
7. Opportunity Cost;
8. Positioning;
9. Final Verdict.

## Decision Gates

| Condition | Required result |
|---|---|
| Missing/conflicting critical fact | Fail or explicitly lower confidence. |
| Missing Source, invalid scope, or missing supporting evidence | Fail build. |
| Research Graph missing or fewer than three Themes | Fail build. |
| Theme challenge lacks counter evidence | Fail build. |
| Theme resolution does not reconcile both sides | Fail build. |
| Bull/Bear has fewer than three arguments | Fail build. |
| Adjudication references unknown arguments or ignores one side | Fail build. |
| No high-importance sensitivity driver | Fail build. |
| Scenario references another scenario's assumption | Fail build. |
| Base IRR materially below hurdle | Existing-position action cannot resolve to HOLD. |
| Robustness unstable | Existing-position action becomes REVIEW unless SELL triggers. |
| Reader exposes internal IDs or omits Theme/Debate/Sensitivity | Verify fails. |
| Audit omits Research Graph | Verify fails. |
| Any generated artifact differs from compiler output | Verify fails. |

## Execution Steps

1. Collect current facts and structured sources.
2. Build quarterly series, assumptions, scenarios, and Decision Policy.
3. Conduct independent business, financial, industry-challenge, and risk passes.
4. Convert findings into observations rather than prose conclusions.
5. Group observations into 3–5 company-specific Themes.
6. Write hypotheses, strongest challenges, resolutions, decision impacts, and falsification conditions.
7. Build Bull/Bear arguments and Lead Adjudication.
8. Identify decision-critical sensitivity drivers.
9. Build with `report_pipeline_v3.py`.
10. Read Reader Report for causal flow and repetition.
11. Review Audit Appendix for evidence closure and graph integrity.
12. Verify and deliver all five artifacts only after PASS.

## Output Contract

Return:

- Spec path;
- Reader path;
- Audit path;
- Bundle path;
- Verification path;
- new-money and existing-position actions;
- Base IRR, target-return price, and buy price;
- decisive Theme;
- strongest Bull argument;
- strongest Bear argument;
- unresolved uncertainty;
- verify result.

## Legacy Boundary

- Existing v1.x and v2.x reports may be inspected with their historical pipelines.
- New reports use `report_pipeline_v3.py`.
- Never generate a new report from `templates/full-report.md` or edit generated Markdown.

## References

- `PRD-single-source-report-compiler-v2.md`
- `PRD-evidence-bound-research-layer-v2.1.md`
- `PRD-research-quality-binding-v2.1.1.md`
- `PRD-reader-first-dual-layer-renderer-v2.1.2.md`
- `PRD-research-graph-investment-debate-v3.md`
- `references/research-graph-v3.md`
- `tests/meta_v3_spec.py`

## Skill 维护纪律（强制）

Any behavior change must follow this order:

1. write/update PRD;
2. stage change log;
3. implement code, contract, and tests;
4. run full fixture, complete CI, and independent code review;
5. finalize PRD and change log before merge.

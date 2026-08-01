---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 脱水质检, 10年回本测试, 估值审判, 值不值, or 该不该买. Produce evidence-bound single-stock research."
license: MIT
metadata:
  author: xiangyingchang
  version: "2.1.0"
---

## Activation Contract

Use for one listed equity when the user requests valuation, buy/hold/sell judgment, a full report, or the trigger phrases above. In the Obsidian stock vault, a ticker or 跑一下/分析下 means a complete saved report unless the user explicitly asks for a quick take.

## v2.1 Trust Boundary

A new report has exactly one editable analytical source:

```text
<report>.spec.json   (report-spec-v2.1)
```

Compiler outputs must never be hand-edited:

```text
<report>.md
<report>.md.bundle.json
<report>.md.verification.json
```

The compiler owns all numeric truth, actions, price zones, payback outputs, evidence tables, and verification. The Research Layer owns structured qualitative claims, but every claim must cite registered Fact, Source, or Bundle paths.

## Hard Rules

- Never invent prices, filings, yields, facts, sources, or evidence references. Tier 1 evidence wins conflicts.
- New reports must use `report-spec-v2.1`; v1.x Markdown-first and v2.0 thin-narrative generation are historical-only.
- Build with:

```bash
python3 scripts/report_pipeline_v2.py build --spec <report>.spec.json --output <report>.md
```

- Verify with:

```bash
python3 scripts/report_pipeline_v2.py verify --spec <report>.spec.json --output <report>.md
```

- Delivery requires Spec, Markdown, Bundle, and Verification files together.
- No Legacy Compatibility Tables. Compatibility belongs in code, never in the report.
- Markdown is a compiled view. Do not copy Runtime values or write final report tables by hand.
- Facts, quarterly series, assumptions, scenarios, decision policy, research claims, and sources live only in the Spec.

### Numeric ownership

- TTM, Revenue, EPS, IRR, Reverse Expectations, prices, payback, actions, robustness, and price zones are compiler outputs.
- Research text may not introduce unbound currency values, percentages, multiples, large numeric facts, thresholds, or actions.
- A qualitative claim references numeric evidence through `FACT-*` or `BUNDLE:<path>`.
- Tolerance and uncertainty exist only in typed Facts/Policy. Narrative cannot add hidden buffers.

### Sources and facts

- `sources` is a structured `SRC-*` registry, not a list of publisher names.
- Every Source requires title, publisher, date, tier, document type, locator, and scope.
- Every Fact requires `source_ids` that resolve to registered Sources.
- Critical company financial facts require Tier 1 evidence when available; current market price may use Tier 2 with explicit confidence.
- Network-effects claims require user/engagement evidence.

### Assumptions and scenarios

- Assumption scope is `global|bear|base|bull`. A scenario may reference only its own or global assumptions.
- Revenue modes are typed:
  - `guide_midpoint`: low/high/source;
  - `guide_high`: low/high/source;
  - `yoy`: prior-year same-quarter base + growth;
  - `qoq`: previous-quarter base + growth;
  - `explicit`: value/source/rationale;
  - `consensus`: value/source/as_of.
- Every future numeric input requires a typed Assumption.
- Historical adjustments may support assumptions but are not direct Forward EPS formula inputs.

### Decision policy

- Decision Policy includes valuation, operating, and thesis-break dimensions.
- Valuation must include executable Reduce/Review behavior when Base IRR falls below the hurdle.
- Output two decisions:
  - `new_money_action`: BUY / WATCH / DO_NOT_BUY;
  - `existing_position_action`: HOLD / REVIEW / REDUCE / SELL.
- SELL is reserved for thesis break. REDUCE may result from material valuation shortfall or operating deterioration.
- If robustness changes the existing-position action, resolve to REVIEW unless SELL independently triggers.
- Price-zone semantics and action rules use the same Base prices.

### Research completeness

All nine modules are mandatory:

1. Overview;
2. Financial Autopsy;
3. Moat;
4. Valuation and Payback;
5. Risk Ranking;
6. Growth Limits;
7. Opportunity Cost;
8. Positioning;
9. Final Verdict.

Module 4 may not be omitted because valuation tables appear earlier.

Minimum contracts:

- Overview: thesis, at least three key forces, variant view.
- Financial Autopsy: revenue, margin, cash flow/Capex, one-offs.
- Moat: at least four scored dimensions, evidence and counter-evidence, trajectory.
- Valuation: Base interpretation, reverse expectations, payback interpretation, critical assumption.
- Risks: at least three ranked risks with mechanism, indicators, trigger, mitigant.
- Growth Limits: growth engine, at least two constraints, ceiling.
- Opportunity Cost: risk-free benchmark, hurdle, index/peer alternatives.
- Positioning: new money, existing position, portfolio constraints, execution.
- Final Verdict: summary, three principles, confidence boundary, falsification condition.

Each research object requires evidence refs and confidence. A one-sentence free-form module is not a valid report.

## Decision Gates

| Condition | Required result |
|---|---|
| Missing/conflicting critical facts | Fail build or explicitly lower confidence; never fill by inference. |
| Fact references missing Source | Fail build. |
| Key claim lacks evidence refs | Fail build. |
| Research references missing Fact/Source/Bundle path | Fail build. |
| Research module missing or structurally thin | Fail build. |
| Free narrative introduces unbound numeric content | Fail build. |
| Scenario references another scenario's assumption | Fail build. |
| Decision Policy lacks valuation Reduce/Review | Fail build. |
| Base IRR materially below hurdle | Existing-position action cannot resolve to HOLD. |
| Robustness is unstable | Existing-position action becomes REVIEW unless SELL triggers. |
| Any output differs from compiler output | Verify fails; do not deliver. |
| Legacy Compatibility Tables appear | Verify fails. |

## Execution Steps

1. Collect ticker, tax identity, horizon, current holding, target return, market price, latest filings, quarterly facts, user/engagement data, peers, risk-free rate, and source metadata.
2. Start from a v2.1 Spec example or the Meta v2.1 factory structure. Never start from an old Markdown report.
3. Register Sources first.
4. Register Facts with Source IDs and confidence.
5. Fill quarterly series and typed assumptions; do not calculate TTM or scenario outputs manually.
6. Define complete Decision Policy with explicit tolerance, uncertainty, and robustness shock.
7. Write structured `research` objects for all nine modules. Claims may explain model outputs but may not create new numbers or override actions.
8. Run `build`.
9. Review Bundle assumptions, decisions, and research evidence closure before reading Markdown.
10. Run `verify`.
11. Deliver only when all four files exist and verify is PASS.

## Output Contract

Return:

- Spec path;
- Markdown path;
- Bundle path;
- Verification path;
- new-money action;
- existing-position action;
- Base IRR, target-return price, and buy price;
- principal research uncertainty;
- source/evidence completeness result;
- verify result.

The Markdown must include Source Registry, Evidence Ledger, Quarterly TTM Bridge, Scenario Assumptions and Valuation, Payback, Decision Policy, all nine modules, Claim-Evidence Matrix, and Verification summary.

## Legacy Boundary

- Existing v1.x reports may still use legacy checkers.
- v2.0 reports may be inspected, but new reports must use v2.1 Research Layer.
- Never generate a new report from `templates/full-report.md`.
- Never add compatibility tables to a compiled report.
- `report_pipeline_v2.py verify` is authoritative for v2.1.

## References

- `PRD-single-source-report-compiler-v2.md` — single-source architecture.
- `PRD-evidence-bound-research-layer-v2.1.md` — research-layer design and acceptance criteria.
- `references/report-spec-v2.md` — numeric Spec contract.
- `references/decision-policy-v2.md` — decision resolution.
- `references/research-layer-v2.1.md` — source, claim, module, and numeric-safety contract.
- `tests/meta_v21_factory.py` — complete Meta reference Spec factory.
- `references/report-contract.md` — evidence and rating caps.
- `references/data-validation.md` — source validation.
- `references/full-methodology.md` — qualitative nine-module method.

## Skill 维护纪律（强制）

Any behavior change must follow this order:

1. write/update PRD;
2. stage change log;
3. implement code, contract, and tests;
4. run complete end-to-end fixture plus full CI;
5. finalize PRD and change log before merge.
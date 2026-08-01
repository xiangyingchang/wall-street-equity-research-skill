---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 脱水质检, 10年回本测试, 估值审判, 值不值, or 该不该买. Produce evidence-bound single-stock research."
license: MIT
metadata:
  author: xiangyingchang
  version: "2.0.0"
---

## Activation Contract

Use for one listed equity when the user requests valuation, buy/hold/sell judgment, a full report, or the trigger phrases above. In the Obsidian stock vault, a ticker or 跑一下/分析下 means a full saved report unless the user asks for a quick take.

## v2 Trust Boundary

A new report has exactly one editable analytical source:

```text
<report>.spec.json   (report-spec-v2)
```

The following are compiler outputs and must never be hand-edited:

```text
<report>.md
<report>.md.bundle.json
<report>.md.verification.json
```

Markdown is a rendered view, not an input. Do not copy Runtime values into a template by hand.

## Hard Rules

- Never invent prices, filings, yields, facts, or sources. Tier 1 evidence wins conflicts.
- New reports must use `report-spec-v2`; v1.x Markdown-first generation is historical-only.
- Build with:

```bash
python3 scripts/report_pipeline_v2.py build --spec <report>.spec.json --output <report>.md
```

- Verify with:

```bash
python3 scripts/report_pipeline_v2.py verify --spec <report>.spec.json --output <report>.md
```

- Delivery requires the Markdown, Bundle, and Verification files together.
- No Legacy Compatibility Tables in v2 reports. Backward compatibility belongs in code, never in the report.
- Facts, quarterly series, assumptions, scenarios, decision policy, narrative, and sources live only in the Spec.
- `global|bear|base|bull` assumption scope is mandatory. A scenario may reference only its own assumptions or global assumptions.
- Revenue modes are typed:
  - `guide_midpoint`: low/high/source;
  - `guide_high`: low/high/source;
  - `yoy`: prior-year same-quarter base + growth;
  - `qoq`: previous-quarter base + growth;
  - `explicit`: value/source/rationale;
  - `consensus`: value/source/as_of.
- `guide_midpoint` may not use a growth rate as its value. `guide_high` must output high, not midpoint.
- TTM EPS, revenue, operating margin, and FCF are compiler-derived from exactly four quarterly Fact IDs.
- Bear/Base/Bull Revenue, EPS, IRR, Reverse Expectations, target-return price, buy price, payback, decision, robustness, and price zones are compiler outputs.
- Historical adjustments may support assumptions but are never direct Forward EPS formula inputs.
- Every future numeric input requires a typed Assumption in the Spec.
- Tolerance and uncertainty must be explicit Policy/Fact fields. Narrative text cannot add another hidden buffer.
- Decision Policy must include valuation, operating, and thesis-break dimensions.
- Valuation Policy must include an executable Reduce/Review rule when Base IRR falls below the target-return hurdle. “Hold = Buy” cannot remain prose-only.
- Output two separate decisions:
  - `new_money_action`: BUY / WATCH / DO_NOT_BUY;
  - `existing_position_action`: HOLD / REVIEW / REDUCE / SELL.
- SELL is reserved for thesis break. REDUCE may be triggered by material valuation shortfall or operating deterioration.
- If robustness shocks change the existing-position action, resolve to REVIEW unless SELL is independently triggered.
- Price-zone names and action rules are generated from the same Base buy/target/reference prices.
- 10-year payback is deterministic runtime output; no hand-written payback table.
- Verification PASS comes only from the compiler. A Markdown table claiming PASS is not evidence.
- Manual edits to Spec-derived Markdown or Bundle must cause `verify` to fail.
- Network-effects moat claims require user/engagement evidence in the Spec narrative/sources.
- Weighted-average diluted shares are for per-share period calculations, not point-in-time market cap.
- Capex is cash. Undisclosed maintenance/growth/AI splits remain `Unclear`.

## Decision Gates

| Condition | Required result |
|---|---|
| Missing/conflicting critical facts | Fail build or lower confidence in Spec; never fill by inference. |
| Scenario references another scenario's assumption | Fail build. |
| Decision Policy lacks valuation Reduce/Review | Fail build. |
| Hidden uncertainty appears only in prose | Ignore prose; only typed Policy/Fact uncertainty is used. |
| Base IRR materially below hurdle | Existing-position action cannot resolve to HOLD. |
| Robustness is unstable | Existing-position action becomes REVIEW unless SELL triggers. |
| New-money price exceeds target-return price | New-money action is DO_NOT_BUY. |
| Any output file differs from compiler output | Verify fails; do not deliver. |
| Legacy Compatibility Tables appear | Verify fails. |

## Execution Steps

1. Collect ticker, market, tax identity, horizon, current holding, target return, current price, latest filings, quarterly facts, and sources.
2. Copy `templates/report-spec-v2.example.json` to the target company folder.
3. Fill facts and quarterly series. Do not calculate TTM manually.
4. Fill typed global and scenario assumptions. Keep Bear/Base/Bull ownership explicit.
5. Define complete Decision Policy with explicit tolerance, uncertainty, and robustness shock.
6. Put qualitative analysis in the Spec `narrative` fields; do not add calculated numbers there unless they are already compiler outputs.
7. Run `build`.
8. Review the generated Bundle first, then Markdown.
9. Run `verify`.
10. Deliver only when verify PASS and all three files exist.

## Output Contract

Return:

- Spec path;
- Markdown path;
- Bundle path;
- Verification path;
- new-money action;
- existing-position action;
- Base IRR and target-return price;
- principal uncertainty;
- verify result.

## Legacy Boundary

- Existing v1.x reports may still be inspected with old checkers.
- Never generate a new report from `templates/full-report.md`.
- Never add v1.x compatibility tables to a v2 report.
- `valuation_consistency.py` and `input_decision_consistency.py` are legacy tools until their v2 wrappers are completed; `report_pipeline_v2.py verify` is authoritative for v2.

## References

- `references/report-spec-v2.md` — single-source Spec contract.
- `references/decision-policy-v2.md` — decision resolution and price-zone semantics.
- `PRD-single-source-report-compiler-v2.md` — architecture and acceptance criteria.
- `templates/report-spec-v2.example.json` — starting Spec.
- `tests/fixtures/meta_v2_spec.json` — end-to-end reference fixture.
- `references/report-contract.md` — evidence and rating caps that still apply.
- `references/data-validation.md` — source validation.
- `references/full-methodology.md` — qualitative 9-module method.

## Skill 维护纪律（强制）

Any behavior change must follow this order:

1. write/update PRD;
2. stage change log;
3. implement code, contract, and tests;
4. run end-to-end fixture plus full CI;
5. finalize PRD and change log before merge.

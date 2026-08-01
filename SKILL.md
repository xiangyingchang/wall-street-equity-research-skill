---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 估值审判, 值不值, or 该不该买. Produce evidence-bound adversarial equity research."
license: MIT
metadata:
  author: xiangyingchang
  version: "3.1.0"
---

## Activation Contract

Use for a listed equity when the user requests valuation, a buy/hold/sell judgment, or a full report. In an Obsidian stock vault, a ticker plus 跑一下/分析下 means a complete saved report unless the user asks for a quick take.

## Hard Rules

- Read `references/research-graph-v3.md`, `references/report-spec-v2.md`, and `references/decision-policy-v2.md` before building a report.
- Start from one fresh `report-spec-v3.1` JSON Spec. Never copy an old Markdown report or edit generated files.
- Build and verify only with:

```bash
python3 scripts/report_pipeline_v3.py build --spec <spec.json> --output <report.md>
python3 scripts/report_pipeline_v3.py verify --spec <spec.json> --output <report.md>
```

- Deliver Spec, Reader, Audit, Bundle, and Verification together.
- The Bundle owns every calculation and action. Narrative may explain but never override it.
- Never invent facts, prices, holdings, sources, assumptions, evidence, graph nodes, or arguments. Prefer Tier 1 evidence; Tier 2 market data must be labeled.
- Every Source requires a real HTTPS URL, date, precise locator, scope, and publisher. Generic source placeholders fail build. TTM inputs must share currency, scale, and per-share units where applicable.
- Bind research numbers through JSON Pointer `value_refs`. Keep Sources, Facts, assumptions, policy, research, and Graph in the Spec.
- Render absolute money in the report currency plus `亿`; keep prices and EPS as per-share values. Never perform cross-currency conversion.
- Use 2-6 material company-specific Themes with 1-4 Observations each; do not pad the count. Require counter-evidence in every Challenge, both sides in every Resolution, Bundle evidence in every Decision Impact, and links covering the decision chain.
- Use 2-6 globally unique Bull and 2-6 Bear arguments. Accepted and discounted IDs must be valid and disjoint; disclose auto-discounted arguments.
- Use 2-6 decision-critical sensitivity drivers, one high importance, and a resolvable Assumption Pointer.
- Operating policy must use company-specific `metrics[]`, not a universal FCF gate. Each metric declares value reference, direction, thresholds, tolerance, uncertainty, and confirmation.
- Require explicit `portfolio_context`. Separate the research candidate action from the executable action; missing position/current/target weights must block an executable REDUCE and resolve to REVIEW.
- Require explicit `prior_report_context`: compare the latest baseline when it exists, or state why none exists. Preserve the old reported IRR separately from a runtime recalculation; never inherit an old calculated value by copying prose.
- Reader must show one current-decision table plus exactly one six-row Action Matrix (Buy/Add/Hold/Review/Reduce/Sell), the three principles (持有=买入、机会成本、10年回本), visible Base assumptions, natural Theme synthesis, and clickable sources.
- Reader must be natural Chinese and contain no internal IDs, Bundle paths, registry names, evidence roles, or hashes. Audit must preserve the complete graph, IDs, roles, assumptions, decisions, and dynamic verification.
- Independent business, financial, challenge, and risk perspectives are required. Parallel subagents are optional; use them only when requested or when their benefit justifies token and latency cost.

## Decision Gates

| Condition | Result |
|---|---|
| Missing or conflicting critical evidence | Fail or lower confidence explicitly. |
| Invalid source, Fact, evidence, value, or assumption reference | Fail build. |
| Graph, debate, sensitivity, or decision-chain coverage incomplete | Fail build. |
| Base IRR materially below hurdle | Research candidate cannot be HOLD. |
| Candidate REDUCE but portfolio status/current/target weight is incomplete | Executable action = REVIEW. |
| Robustness unstable | REVIEW unless SELL independently triggers. |
| Reader exposes audit syntax or Audit loses traceability | Fail build/verify. |
| Any generated artifact differs from compiler output | Fail verify. |

## Execution Steps

1. Collect the smallest sufficient data pack: prior report, current price, actual holdings context, filings, four-quarter facts, company-specific operating metrics, peers, rates, and direct source metadata.
2. Reconcile units and discrepancies; register Sources, Facts, derived calculations, assumptions, scenarios, operating metrics, and Decision Policy in a fresh Spec.
3. Conduct independent business, financial, challenge, and risk passes; synthesize only material logic into Themes and a Bull/Bear adjudication.
4. Apply the three principles, decision-critical sensitivity drivers, falsification conditions, and portfolio execution gate.
5. Build all artifacts; read the Reader for directness, prior-report delta, logic, repetition, visible assumptions, and one Action Matrix; inspect the Audit for closure.
6. Run verify and deliver only when artifact checks pass; disclose portfolio `REVIEW` rather than pretending missing context is complete.

## Output Contract

Return the five artifact paths; new-money action; research candidate and executable existing-position actions; portfolio-context status; Base IRR, target-return price, and buy price; decisive Theme; strongest Bull and Bear arguments; unresolved uncertainty; and verify result.

## References

- `references/research-graph-v3.md` - v3 graph, debate, and sensitivity contract.
- `references/report-spec-v2.md` - Spec, numeric ownership, and provenance.
- `references/decision-policy-v2.md` - action resolution and price zones.
- `PRD-research-graph-investment-debate-v3.md` - design rationale and acceptance history.
- `PRD-data-reasoning-reader-v3.1.md` - v3.1 data, decision, and Reader redesign.

Any Skill behavior change must follow: PRD -> staged change log -> code/tests -> full CI -> final review.

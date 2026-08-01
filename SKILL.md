---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 估值审判, 值不值, or 该不该买. Produce evidence-bound adversarial equity research."
license: MIT
metadata:
  author: xiangyingchang
  version: "3.0.0"
---

## Activation Contract

Use for a listed equity when the user requests valuation, a buy/hold/sell judgment, or a full report. In an Obsidian stock vault, a ticker plus 跑一下/分析下 means a complete saved report unless the user asks for a quick take.

## Hard Rules

- Read `references/research-graph-v3.md`, `references/report-spec-v2.md`, and `references/decision-policy-v2.md` before building a report.
- Start from one fresh `report-spec-v3.0` JSON Spec. Never copy an old Markdown report or edit generated files.
- Build and verify only with:

```bash
python3 scripts/report_pipeline_v3.py build --spec <spec.json> --output <report.md>
python3 scripts/report_pipeline_v3.py verify --spec <spec.json> --output <report.md>
```

- Deliver Spec, Reader, Audit, Bundle, and Verification together.
- The Bundle owns every calculation and action. Narrative may explain but never override it.
- Never invent facts, prices, sources, assumptions, evidence, graph nodes, or arguments. Prefer Tier 1 evidence; Tier 2 market data must be labeled.
- Bind research numbers through JSON Pointer `value_refs`. Keep Sources, Facts, assumptions, policy, research, and Graph in the Spec.
- Render absolute money in the report currency plus `亿`; keep prices and EPS as per-share values. Never perform cross-currency conversion.
- Require 3-5 company-specific Themes, at least two Observations each, counter-evidence in every Challenge, both sides in every Resolution, Bundle evidence in every Decision Impact, and links covering all nine modules.
- Require at least three globally unique Bull and three Bear arguments. Accepted and discounted IDs must be valid and disjoint; disclose auto-discounted arguments.
- Require at least three sensitivity drivers, one high importance, and a resolvable Assumption Pointer.
- Reader must be natural Chinese and contain no internal IDs, Bundle paths, registry names, evidence roles, or hashes. Audit must preserve the complete graph, IDs, roles, assumptions, decisions, and dynamic verification.
- Independent business, financial, challenge, and risk perspectives are required. Parallel subagents are optional; use them only when requested or when their benefit justifies token and latency cost.

## Decision Gates

| Condition | Result |
|---|---|
| Missing or conflicting critical evidence | Fail or lower confidence explicitly. |
| Invalid source, Fact, evidence, value, or assumption reference | Fail build. |
| Graph, debate, sensitivity, or nine-module coverage incomplete | Fail build. |
| Base IRR materially below hurdle | Existing-position action cannot be HOLD. |
| Robustness unstable | REVIEW unless SELL independently triggers. |
| Reader exposes audit syntax or Audit loses traceability | Fail build/verify. |
| Any generated artifact differs from compiler output | Fail verify. |

## Execution Steps

1. Collect current price, holdings context, filings, four-quarter facts, user/engagement data when network effects matter, peers, rates, and source metadata.
2. Register Sources, Facts, assumptions, scenarios, and Decision Policy in a fresh Spec.
3. Conduct independent business, financial, challenge, and risk passes; synthesize them into Themes and a Bull/Bear adjudication.
4. Add decision-critical sensitivity drivers and falsification conditions.
5. Build all artifacts, read the Reader for logic and repetition, then inspect the Audit for closure.
6. Run verify and deliver only on PASS.

## Output Contract

Return the five artifact paths; new-money and existing-position actions; Base IRR, target-return price, and buy price; decisive Theme; strongest Bull and Bear arguments; unresolved uncertainty; and verify result.

## References

- `references/research-graph-v3.md` - v3 graph, debate, and sensitivity contract.
- `references/report-spec-v2.md` - Spec, numeric ownership, and provenance.
- `references/decision-policy-v2.md` - action resolution and price zones.
- `PRD-research-graph-investment-debate-v3.md` - design rationale and acceptance history.

Any Skill behavior change must follow: PRD -> staged change log -> code/tests -> full CI -> final review.

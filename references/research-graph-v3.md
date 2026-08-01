# Research Graph v3.1 Contract

## Purpose

v3 inserts a research reasoning layer between evidence and prose. The goal is to stop treating isolated claims as the basic unit of investment research.

```text
Source → Fact → Observation → Hypothesis → Challenge
       → Resolution → Theme → Narrative → Decision
```

## Theme

A Theme is a company-specific investment question, not a report heading. Good examples:

- AI capital spending and incremental shareholder return;
- advertising recommendation flywheel versus platform maturity;
- current price versus required operating delivery.

Bad examples:

- financial performance;
- valuation;
- risks;
- growth.

Use 2-6 Themes based on materiality, not a fixed quota. Each Theme contains 1-4 observations, a hypothesis, the strongest credible challenge, a resolution, decision impact, falsification, and module links. Across all Themes, links must cover overview, valuation, opportunity cost, positioning, final verdict, and at least one company-specific operating module.

## Observation

An Observation describes what the evidence shows without jumping directly to the final judgment. It uses an `OBS-*` ID and evidence/value bindings.

## Hypothesis

A Hypothesis explains the causal mechanism connecting observations. It is provisional, not automatically accepted.

## Challenge

A Challenge is the strongest credible alternative explanation. It must contain `counter_evidence`; generic caveats do not qualify.

## Resolution

A Resolution explicitly weighs supporting and counter evidence. It must cite both roles and explain why one interpretation currently dominates.

## Decision Impact

Decision Impact connects the Theme to compiler-owned values or actions. Narrative cannot override the action.

## Falsification

Falsification states the observable condition that would invalidate the resolution. It must be measurable in future evidence, not a vague statement to “monitor developments.”

## Investment Debate

Bull and Bear each require 2-6 `ARG-*` arguments. Arguments are independent research propositions, not repeated sentences from the Theme narrative; do not add weak points to hit a count.

Adjudication must:

- reference accepted and discounted argument IDs;
- accept at least one point from each side;
- explain the decisive evidence;
- state remaining uncertainty;
- explain why the current action follows.

## Sensitivity Explanation

Use 2-6 `DRV-*` drivers that actually control the decision. At least one driver is high importance. Each driver explains mechanism, upside, downside, and decision consequence. Assumption pointers accept `/assumptions/<ASM-ID>/value` or the Spec form `/assumptions/scenario/<ASM-ID>/value`; compiled output is canonical.

## Multi-Perspective Workflow

When parallel agents are available:

- business analyst writes business/moat observations;
- financial analyst writes financial/valuation observations;
- industry challenger writes counter-evidence and alternative hypotheses;
- risk assessor writes failure paths and falsification;
- lead analyst groups Themes, resolves conflicts, adjudicates debate, and writes final narrative.

Agents never edit generated Markdown. They contribute nodes to one Spec.

## Quality Gates

Build fails when:

- fewer than two or more than six Themes exist;
- Theme titles are generic;
- a Theme has no Observation, more than four Observations, or reuses an ID;
- challenge lacks counter-evidence;
- resolution ignores one side;
- decision impact lacks Bundle evidence;
- Bull or Bear has fewer than two or more than six arguments;
- adjudication references unknown IDs or ignores one side;
- no high-importance sensitivity driver exists.
- Reader exposes `THEME-*`, `OBS-*`, `ARG-*`, or `DRV-*` IDs;
- Audit omits accepted, discounted, or auto-discounted disclosure;
- a sensitivity pointer contains extra path segments or an unknown Assumption ID.

## Rendering

Reader Report synthesizes each Theme into continuous prose, shows a compact evidence debate and actual Base assumption values, and never prints the old seven-node label sequence or internal IDs. The complete node graph remains in Audit.

Audit Appendix shows complete Theme, Observation, Argument, Driver, and evidence-role structures.

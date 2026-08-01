# Evidence-Bound Research Layer v2.1

## Purpose

v2.1 preserves the v2 Single-Source Compiler while restoring full investment-research depth. Numbers remain compiler-owned; qualitative analysis becomes structured, evidence-bound, and verifiable.

## Source Registry

`report-spec-v2.1` uses a `sources` object keyed by `SRC-*` IDs. Every source requires:

- title;
- publisher;
- date;
- tier;
- document type;
- locator;
- scope.

Publisher names alone are insufficient. The locator may be a URL, filing identifier, or stable document location.

## Fact provenance

Every Fact requires `source_ids`. Company financial facts require Tier 1 evidence when available. Current price may rely on Tier 2 market data with explicit confidence and uncertainty.

## Research object

Every claim-like object includes:

```json
{
  "claim": "qualitative judgment without unbound numeric literals",
  "evidence_refs": ["FACT-*", "SRC-*", "BUNDLE:path.to.value"],
  "implication": "why this matters to valuation or action",
  "confidence": "low|medium|high"
}
```

Objects using `text` instead of `claim` follow the same rules.

## Evidence reference types

- `FACT-*`: registered factual input;
- `SRC-*`: registered source document;
- `BUNDLE:<path>`: compiler-derived analytical output.

Any missing reference fails build.

## Numeric safety

Free research text cannot introduce currency values, percentages, multiples, large standalone numbers, thresholds, or actions. Numeric reasoning must cite a Bundle path or Fact ID and be rendered by the compiler-owned tables.

This prevents narrative from silently overriding the analytical model.

## Nine-module contract

### Overview

- thesis;
- at least three key forces;
- variant view.

### Financial Autopsy

- revenue;
- margin;
- cash flow and Capex;
- one-offs and accounting boundary.

### Moat

- at least four dimensions;
- one-to-five score;
- evidence;
- counter-evidence;
- strengthening/stable/weakening trajectory.

### Valuation and Payback

- Base-case interpretation;
- reverse expectations;
- payback interpretation;
- critical assumption.

### Risks

At least three ranked items, each with mechanism, leading indicators, trigger, mitigant, evidence, and confidence.

### Growth Limits

- growth engine;
- at least two constraints;
- long-term ceiling.

### Opportunity Cost

- risk-free benchmark;
- required-return hurdle;
- index and peer alternatives;
- risk and evidence-quality interpretation.

### Positioning

- new-money interpretation;
- existing-position interpretation;
- portfolio constraints;
- execution discipline.

### Final Verdict

- summary;
- Hold = Buy;
- opportunity cost;
- payback;
- confidence boundary;
- falsification condition.

## Generated report sections

A v2.1 report includes:

1. Build Manifest;
2. First-Page Verdict;
3. Source Registry;
4. Evidence Ledger;
5. Quarterly TTM Bridge;
6. Scenario Assumptions and Valuation;
7. Payback;
8. Decision Policy;
9. all nine research modules;
10. Claim-Evidence Matrix;
11. Verification summary.

## Verification

Build fails when:

- a module is missing;
- a module is structurally thin;
- a claim lacks evidence;
- a Fact lacks valid source IDs;
- a source is incomplete;
- a research path is invalid;
- free text contains unbound numeric content;
- a scenario or decision violates the v2 analytical contract.

`report_pipeline_v2.py verify` remains authoritative and checks the Spec, Bundle, Markdown, and Verification hashes together.

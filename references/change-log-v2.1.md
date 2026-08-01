# v2.1 Change Log — Evidence-Bound Research Layer

## 2026-08-01

### Planned change

- Extend `report-spec-v2` into `report-spec-v2.1` with structured `sources` and `research` objects.
- Keep all numeric truth compiler-owned; Research Layer may only reference existing Fact/Bundle paths.
- Require all nine research modules and block missing module 4.
- Add structured Source Registry with title, publisher, date, tier, document type, locator, and scope.
- Require every Fact to reference Source IDs.
- Add claim/evidence/confidence/implication objects for qualitative research.
- Add minimum module contracts for Overview, Financial Autopsy, Moat, Valuation, Risks, Growth Limits, Opportunity Cost, Positioning, and Final Verdict.
- Generate Evidence Ledger, Quarterly TTM Bridge, Scenario Assumption Table, Claim-Evidence Matrix, and complete nine-module Markdown.
- Add numeric-safety checks so free narrative cannot introduce unbound prices, percentages, multiples, share counts, or actions.
- Add evidence-closure, source-quality, module-completeness, and research-depth checks to Verification Manifest.
- Expand the Meta end-to-end fixture from a calculation summary into a complete evidence-bound research report.

### Reason

v2.0 fixed the architectural inconsistency of Markdown-first generation, but the first generated Meta v2 report became too thin: most research modules contained one sentence, module 4 was missing, sources were unstructured, scenario inputs were hidden, and the REDUCE decision lacked a proper research explanation.

The correct next step is not to restore freehand Markdown. It is to add a constrained Research Layer on top of the deterministic Bundle: numbers remain compiler-owned, while qualitative claims become typed objects bound to sources and model outputs.

### Success target

- one numeric truth remains intact;
- all nine modules are complete;
- every key claim has evidence;
- every source is structured and traceable;
- no narrative can create new numbers or override decisions;
- the Meta report is materially useful as investment research, not merely a calculation summary;
- build/verify remains deterministic and tamper-resistant.

### Integration

After implementation and validation:

1. replace this planned entry with exact implementation and test results;
2. prepend it below the title in `references/change-log.md`;
3. delete `references/change-log-v2.1.md`;
4. mark `PRD-evidence-bound-research-layer-v2.1.md` completed;
5. rerun full CI before merge.
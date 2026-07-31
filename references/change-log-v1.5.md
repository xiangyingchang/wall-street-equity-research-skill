# v1.5 Change Log — Input Provenance and Decision Robustness

## 2026-08-01

### Planned change

- Add deterministic `ttm-derive` runtime for four-quarter sums and ratios.
- Add deterministic `revenue-bridge` runtime so guide/YoY/QoQ forecasts are calculated from explicit bases instead of hand-filled final values.
- Add shared `return-pair` runtime for IRR, Reverse Expectations, and target-return-consistent current price using one assumption set.
- Upgrade the Canonical Registry to distinguish `FACT`, `DERIVED`, and `MODEL` values and prevent model outputs from being labelled as facts.
- Add a Threshold Policy Registry with basis, lookback, confirmation, tolerance, minimum confidence, and rationale.
- Upgrade fact-based Action Evaluation to support structured value metadata, threshold references, neutral bands, confirmation requirements, and confidence gates.
- Add action robustness testing under configurable input shocks; unstable actions must resolve to REVIEW in new full reports.
- Expand valuation consistency checks for TTM provenance, revenue-growth arithmetic, scenario ordering, threshold provenance, price-zone/action contradictions, return-assumption consistency, verification TODOs, and weighted-average-share market-cap misuse.
- Update the canonical template, runtime contract, skill instructions, tests, and affected report contract guidance.

### Reason

The Meta v1.4 report demonstrated that deterministic arithmetic alone is insufficient. The report correctly calculated EPS, IRR, Reverse Expectations, and rule booleans from supplied inputs, but the supplied inputs and thresholds were internally inconsistent or weakly justified. TTM operating margin appeared as 35% and 43% in different sections instead of the approximately 38.08% four-quarter calculation; forward rows labelled +12% YoY did not reconcile to their base quarters; a manually chosen $400亿 FCF threshold created a deterministic REDUCE despite only a small difference from an approximate TTM value; the current price was simultaneously described as not worth buying, a Reduce, and inside a buy zone; and required verification stages remained TODO.

v1.5 moves the trust boundary upstream: inputs, forecast transformations, threshold policies, return assumptions, and decision stability become auditable runtime objects rather than prose conventions.

### Scope boundary

- No automatic market, filing, consensus, or portfolio data fetching.
- No automatic selection of economically correct growth, margin, multiple, or threshold assumptions.
- No full DCF, Monte Carlo, or portfolio optimizer.
- No change to the nine-module report structure.
- Legacy runtime commands remain available for old artifacts, but new full reports must use the v1.5 flow.

### Verification target

- TTM EPS vector: `1.05 + 8.88 + 10.44 + 6.18 = 26.55`.
- TTM operating margin vector: four-quarter operating income / revenue ≈ `38.08%`.
- Revenue vector: `563.11 × 1.12 = 630.6832`, not `700`.
- Return-pair uses one dividend assumption for IRR and Reverse Expectations and outputs target-return price.
- A model fair value labelled `FACT-*` fails.
- A naked Action threshold fails in a new full report.
- `378.7` versus threshold `400` with `5%` tolerance resolves as indeterminate / REVIEW.
- A ±5% input shock that changes the action returns `stable=false`.
- Buy-zone / no-buy / Reduce contradictions fail.
- Verification TODO / FAIL / unrun / Unknown fails.
- Weighted-average diluted shares used directly for market cap fails without reconciliation.
- Python syntax, full unittest suite, lint self-test, fixtures, and diff check pass.

### Integration

After implementation and full validation:

1. replace this planned entry with the final implemented change list and exact test results;
2. prepend the finalized entry below the title in `references/change-log.md`;
3. delete `references/change-log-v1.5.md`;
4. mark `PRD-input-provenance-decision-robustness-v1.5.md` completed;
5. rerun CI before merge.

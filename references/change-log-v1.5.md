# v1.5 Change Log — Input Provenance and Decision Robustness

## 2026-08-01

### Change

- Added `valuation_runtime.py ttm-derive` for deterministic four-quarter sums and ratios, including TTM EPS and TTM operating margin.
- Added `valuation_runtime.py revenue-bridge` with `guide_midpoint`, `yoy`, `qoq`, `explicit`, and `consensus` modes so each forecast period is generated from auditable inputs.
- Added `valuation_runtime.py return-pair`, which uses one shared assumption set to output Scenario IRR, Reverse Expectations, and target-return-consistent current price.
- Extended Reverse Expectations to support the same dividend-yield assumption used by Scenario IRR.
- Upgraded Action Evaluation with v2 `values` and `thresholds` objects:
  - value kind (`FACT` / `DERIVED` / `MODEL`);
  - confidence and declared uncertainty;
  - threshold basis, lookback, confirmation, tolerance, minimum confidence, and rationale;
  - tri-state condition results: true / false / indeterminate;
  - REVIEW resolution when material indeterminacy can affect the highest-priority action.
- Added `valuation_runtime.py robustness` for configurable ±input shocks. Unstable decisions return `stable=false` and recommend `REVIEW`.
- Added `scripts/input_decision_consistency.py` to block:
  - model outputs labelled as FACT;
  - TTM values without component/runtime provenance;
  - unreconciled YoY/QoQ/guide Revenue rows;
  - effectively identical Base/Bull totals under conflicting growth assumptions;
  - naked Action thresholds and incomplete Threshold policies;
  - separate new-report `irr` / `reverse` commands;
  - unstable robustness with a non-REVIEW action;
  - buy-zone / no-buy / Reduce-Sell contradictions;
  - weighted-average diluted shares used directly for market cap;
  - conflicting structured TTM operating-margin values;
  - incomplete or failed Verification rows.
- Updated `SKILL.md` to v1.5.0.
- Updated `templates/full-report.md` with Canonical Value Registry, TTM Derivation, Revenue Forecast Runtime, Return Pair, Threshold Policy Registry, Action Evaluation v2, Robustness, and blocking Verification rows.
- Updated `references/valuation-runtime.md` and added `references/input-decision-robustness.md` as the v1.5 authoritative contract.
- Added and expanded regression tests for all Meta v1.4 failure modes.

### Reason

The Meta v1.4 report proved that deterministic arithmetic alone is insufficient. It correctly calculated EPS, IRR, Reverse Expectations, and rule booleans from supplied inputs, but the inputs and thresholds were internally inconsistent or weakly justified:

- TTM operating margin appeared as 35% and 43% instead of the approximately 38.08% four-quarter calculation;
- TTM EPS was about $27.25 instead of the four-quarter $26.55;
- +12% YoY Revenue rows did not reconcile to their base quarters;
- a manually selected $400亿 FCF threshold created a deterministic REDUCE without threshold provenance or a neutral band;
- current price was simultaneously no-buy, Reduce, and inside a buy zone;
- IRR and Reverse used different dividend inputs;
- fair value was registered as a Fact;
- weighted-average diluted shares were used for point-in-time market cap;
- required Verification stages remained TODO.

v1.5 moves the trust boundary upstream: values, forecast transformations, threshold policies, shared return assumptions, price semantics, and decision stability are now auditable runtime objects.

### Scope boundary

- No automatic market, filing, consensus, or portfolio data fetching.
- Runtime does not choose economically correct growth, margin, multiple, or threshold assumptions.
- No full DCF, Monte Carlo, or portfolio optimizer.
- The nine-module report structure is unchanged.
- Legacy `irr`, `reverse`, scalar-facts `evaluate-action`, and `resolve-action` remain available for old artifacts only.

### Verification

GitHub Actions `Validate` run #69: PASS.

- `python -m py_compile scripts/*.py`: PASS.
- financial rigor, report audit, and report lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **117 / 117 PASS**.
- TTM EPS vector: `1.05 + 8.88 + 10.44 + 6.18 = 26.5500`: PASS.
- TTM operating margin vector: approximately `38.08%`: PASS.
- Revenue vector: `563.11 × 1.12 = 630.6832`: PASS.
- Return Pair vector: Base IRR `6.54%`, Reverse required EPS CAGR `8.90%`, target-return price `479.7122`: PASS.
- Near-threshold vector: `378.7` vs `400`, tolerance `5%` plus uncertainty `1%` => indeterminate / REVIEW: PASS.
- ±5% robustness vector changes the action => `stable=false`, recommended action REVIEW: PASS.
- Negative tests for model-as-FACT, naked thresholds, buy-zone contradictions, Verification TODO, and weighted-average-share market-cap misuse: PASS.

### Integration

Before merging PR #5:

1. prepend this entry below the title in `references/change-log.md`;
2. delete `references/change-log-v1.5.md`;
3. preserve every historical change-log entry;
4. rerun CI on the integration commit.

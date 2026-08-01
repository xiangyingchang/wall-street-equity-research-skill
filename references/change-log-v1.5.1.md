# v1.5.1 Change Log — Runtime Binding and Reference Integrity

## 2026-08-01

### Planned change

- Add a deterministic runtime artifact envelope with canonical JSON SHA-256 hashes.
- Add deterministic Scenario Valuation runtime for forward reference value, target-return price, safety-margin buy price, and stress/reference roles.
- Add a global ID graph checker covering `FACT/DERIVED/MODEL/ASM/THR/B/BR/REV/RUN` definitions and references.
- Add Runtime Artifact Manifest requirements and report-to-runtime field binding checks.
- Add Revenue forecast period semantics: YoY/QoQ base-period validation and Assumption mode/value/scope matching.
- Require complete Assumption closure for tax rate, share count, EPS CAGR, dividends, exit PE, reference multiple, safety margin, and other income.
- Require Action Matrix and Runtime Evaluation rule completeness; undeclared IDs and omitted executable rules fail.
- Require structured point-in-time share reconciliation for market-cap calculations.
- Block Forward Basis rows that cite historical Adjustment IDs as if they were direct formula inputs.
- Update the canonical template, Skill contract, references, tests, and CI coverage.

### Reason

The Meta v1.5 report showed that v1.5 correctly introduced TTM derivation, Revenue Forecast runtime, Return Pair, Threshold Policy, tri-state Action Evaluation, and Robustness, but still allowed incorrect report transcription and incomplete provenance:

- Required terminal EPS did not reconcile with Required EPS CAGR;
- Scenario Valuation multiplication and buy-price rounding were wrong;
- Action Matrix referenced missing IDs and omitted Buy/Add from Runtime Evaluation;
- Value IDs drifted across sections;
- YoY Revenue used a wrong base quarter while arithmetic still passed;
- Derived Values referenced FACT IDs that were not defined;
- market-cap reconciliation was claimed but absent;
- several valuation inputs remained naked numbers;
- Forward EPS falsely cited historical Adjustment IDs.

v1.5.1 moves the trust boundary from “runtime was mentioned” to “the exact runtime artifact, every field, every ID, every period, and every input reference is bound and verifiable.”

### Scope boundary

- No external data fetching.
- No automatic choice of economically correct assumptions.
- No full DCF or Monte Carlo.
- No change to the nine-module report structure.
- Old reports are not required to migrate unless regenerated under v1.5.1.

### Verification target

- inconsistent Return Pair terminal EPS/CAGR fails;
- incorrect Scenario Valuation multiplication fails;
- missing or drifting IDs fail;
- Action Matrix/Evaluation rule omissions fail;
- invalid YoY/QoQ base periods fail;
- Assumption mismatch and missing input IDs fail;
- missing share reconciliation fails;
- historical adjustments used as forward formula inputs fail;
- runtime artifact hash or field mismatch fails;
- Meta v1.5 report is a negative fixture;
- Python syntax, full unittest suite, lint fixtures, and diff check pass.

### Integration

After implementation and validation:

1. replace this planned entry with the actual implementation and exact test results;
2. prepend the finalized v1.5.1 entry to `references/change-log.md` after the title;
3. delete `references/change-log-v1.5.1.md`;
4. mark `PRD-runtime-binding-reference-integrity-v1.5.1.md` completed;
5. rerun CI before merge.

# v1.5.1 Change Log — Runtime Binding and Reference Integrity

## 2026-08-01

### Change

- Added deterministic Runtime Artifact Envelope with canonical JSON SHA-256 hashes.
- Added `report_integrity_v151.py wrap-artifact` to persist exact runtime inputs/outputs as `RUN-*` JSON artifacts.
- Added deterministic `scenario-value` runtime:
  - forward reference value = metric value × reference multiple;
  - buy price = target-return price × (1 - safety margin).
- Added global ID Graph validation for `FACT-*`, `DERIVED-*`, `MODEL-*`, `ASM-*`, `THR-*`, `B-*`, `BR-*`, `REV-*`, and `RUN-*`.
- Added runtime file/hash/field binding for Revenue Forecast, EPS Bridge, Return Pair, and Scenario Valuation.
- Added Revenue period semantics:
  - YoY base period must be prior-year same quarter;
  - QoQ base period must be previous quarter;
  - Revenue row mode/base/forecast period must match its Assumption.
- Added Assumption closure for operating margin, tax rate, diluted shares, other income, EPS CAGR, dividend, exit PE, target return, reference multiple, safety margin, and period-level revenue inputs.
- Added Action completeness checks:
  - every executable rule has a Rule ID;
  - Action Matrix and Runtime Evaluation Rule ID sets must match;
  - `N/A because current action is not X` is forbidden.
- Added structured Point-in-Time Share Reconciliation for market-cap calculations.
- Blocked Forward Basis rows from citing historical Adjustment IDs as direct formula inputs.
- Upgraded `SKILL.md` to v1.5.1 and `templates/full-report.md` to `full-report-v1.5.1`.
- Added Generation Manifest and Runtime Artifact Manifest.
- Added `references/runtime-binding-integrity.md`.
- Added 10 v1.5.1 regression tests covering runtime binding and Meta v1.5 failure modes.

### Reason

The Meta v1.5 report proved that deterministic runtimes and structured tables were still insufficient when the Markdown report was not bound to the exact runtime artifacts. The report still contained:

- Required terminal EPS inconsistent with Required EPS CAGR;
- incorrect Scenario Valuation multiplication and buy price;
- missing Action/Threshold IDs and omitted Buy/Add evaluation rules;
- MODEL ID naming drift across sections;
- YoY Revenue using the wrong base quarter;
- Derived Values referring to FACT IDs that did not exist;
- claimed but absent market-cap share reconciliation;
- unregistered decision inputs;
- historical adjustments attached to forward formula bases.

v1.5.1 moves the trust boundary from “runtime mentioned” to “exact runtime file, hash, field, ID, period, and assumption are verifiable.”

### Scope boundary

- No external data fetching.
- No automatic selection of economically correct assumptions.
- No full DCF or Monte Carlo.
- No change to the nine-module report structure.
- Existing reports need migration only when regenerated under v1.5.1.

### Verification

GitHub Actions `Validate` run #94: PASS.

- Python syntax: PASS.
- financial rigor, report audit, and report lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **127 / 127 PASS**.
- new v1.5.1 tests: **10 / 10 PASS**.
- template/new-report recognition: PASS.
- Scenario runtime vector: `29.24 × 20 = 584.8000`: PASS.
- target-return-based buy-price calculation: PASS.
- Return Pair terminal EPS/CAGR mismatch negative test: PASS.
- Scenario multiplication mismatch negative test: PASS.
- undefined ID and omitted Action rule negative tests: PASS.
- invalid YoY base-period negative test: PASS.
- historical Adjustment in Forward Basis negative test: PASS.
- artifact missing/hash mismatch negative tests: PASS.
- uploaded Meta v1.5 report manually rejected by the new integrity checker; its critical failure modes are covered by regression tests.

### Integration

Before merging PR #6:

1. prepend this entry below the title in `references/change-log.md`;
2. delete `references/change-log-v1.5.1.md`;
3. preserve every historical change-log entry;
4. rerun the complete validation suite and CI;
5. merge only after final Agent review and green CI.

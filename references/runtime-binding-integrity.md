# Runtime Binding and Reference Integrity Contract v1.5.1

## Purpose

v1.5.1 closes the gap between “a runtime was mentioned” and “the report is an exact, auditable rendering of that runtime.” It adds artifact files, hashes, a global ID graph, period semantics, assumption closure, complete Action rules, and deterministic Scenario Valuation.

## Generation Manifest

Every new report declares:

| Field | Required value |
|---|---|
| Skill version | `1.5.1` |
| Template schema | `full-report-v1.5.1` |
| Git commit | actual repository HEAD used for generation |
| Report ID | stable report identifier |
| Runtime artifacts directory | sibling directory containing `RUN-*.json` artifacts |

A missing or stale manifest blocks delivery.

## Runtime Artifact Envelope

Existing runtime output must be wrapped with:

```bash
python3 scripts/report_integrity_v151.py wrap-artifact \
  --input wrap-input.json \
  --output report.artifacts/RUN-RETURN-BASE.json
```

Input schema:

```json
{
  "runtime_name": "return-pair",
  "artifact_id": "RUN-RETURN-BASE",
  "input_refs": ["B-BASE", "ASM-BASE-CAGR", "ASM-BASE-EXIT"],
  "inputs": {"...": "exact runtime inputs"},
  "outputs": {"...": "exact runtime JSON output"}
}
```

Output envelope contains `schema_version`, `runtime_name`, `artifact_id`, `input_refs`, `inputs`, `outputs`, and a canonical JSON SHA-256 `artifact_hash`.

The report records file and hash in Runtime Artifact Manifest. Final validation must use `--artifacts-dir`; merely printing a hash in Markdown is insufficient.

## Scenario Valuation Runtime

Use:

```bash
python3 scripts/report_integrity_v151.py scenario-value \
  --input scenario-base.json \
  --output report.artifacts/RUN-SCENARIO-BASE.json
```

Input:

```json
{
  "artifact_id": "RUN-SCENARIO-BASE",
  "scenario": "Base",
  "metric_value": "29.24",
  "reference_multiple": "20",
  "target_return_price": "456.67",
  "safety_margin": "0.10",
  "input_refs": [
    "B-BASE",
    "MODEL-BASE-TARGET-RETURN-PRICE",
    "ASM-BASE-REFERENCE-MULTIPLE",
    "ASM-BASE-SAFETY-MARGIN"
  ]
}
```

Formula:

```text
forward reference value = metric value × reference multiple
buy price = target-return price × (1 - safety margin)
```

Do not calculate buy price from forward reference value. Forward reference describes a multiple-based valuation context; target-return price is the price consistent with the user's required annual return.

## Global ID Graph

The checker recognizes these namespaces:

- `FACT-*` — external facts;
- `DERIVED-*` — calculated values;
- `MODEL-*` — analytical outputs;
- `ASM-*` — forward assumptions;
- `THR-*` — threshold policies;
- `B-*` — valuation bases;
- `BR-*` — EPS bridges;
- `REV-*` — revenue rows;
- `RUN-*` — runtime artifacts.

Rules:

1. every reference must have exactly one definition;
2. Value prefix must match Kind;
3. Derived Values list the actual component IDs;
4. table-to-table names may not drift;
5. Action Matrix IDs and Evaluation IDs must match exactly;
6. runtime artifacts referenced by rows must exist in the manifest and on disk.

## Revenue Period Semantics

Each Revenue row declares forecast period, mode, base period, base Value ID, growth/value Assumption ID, and Runtime Artifact ID.

Rules:

```text
yoy: base period = prior-year same quarter
qoq: base period = immediately previous quarter
```

The referenced Assumption must match row mode, base period, forecast period, and value. Correct arithmetic with the wrong quarter is a failure.

## Assumption Closure

Every decision-critical future input requires an `ASM-*` row with Scenario, Variable, Value, Scope, Mode, Base period, Forecast period, Input role, Evidence/rationale, and Confidence.

At minimum register each period's revenue guide/growth/value, operating margin, tax rate, other income/expense, diluted shares, EPS CAGR, exit PE, dividend yield/DPS, target return, reference multiple, safety margin, and Capex normalization when used.

A runtime command containing an unregistered decision input is incomplete.

## Forward Basis Provenance

A Forward EPS Basis references its `BR-*` bridge and the `ASM-*` inputs that entered that bridge. It must use `Adjustments=None`. Historical `ADJ-*` items may explain why an assumption was chosen, but they are not direct formula inputs unless a separate historical-adjustment bridge explicitly calculates the value.

## Point-in-Time Share Reconciliation

Market cap requires a structured table with point-in-time shares Value ID, point-in-time shares, as-of date, source/tier, weighted-average diluted shares, difference, and market-cap basis.

Weighted-average diluted shares remain valid for EPS. They are not interchangeable with point-in-time shares for market cap.

## Action Completeness

Every executable Action Matrix row has a Rule ID. Buy, Add, Hold, Reduce, and Sell rules cannot be omitted merely because they are not the current action. The Runtime Evaluation rule-ID set must equal the Action Matrix executable rule-ID set.

## Field Binding

When artifact files are available, `report_integrity_v151.py check` compares report rows with artifact outputs, including Revenue period values; EPS Bridge revenue, profit, tax, shares, and EPS; Return Pair assumptions, IRR, required terminal EPS, required CAGR, and target-return price; and Scenario Valuation metric, multiple, forward reference, target-return price, safety margin, and buy price.

Any mismatch blocks delivery.

## Final Validation

```bash
python3 scripts/report_integrity_v151.py check \
  股票/<公司>/<report>.md \
  --artifacts-dir 股票/<公司>/<report>.artifacts
```

This command is mandatory in addition to:

```bash
python3 scripts/valuation_consistency.py <report.md>
python3 scripts/input_decision_consistency.py <report.md>
python3 scripts/report_lint.py <report.md>
python3 scripts/report_audit.py recognize --report <report.md>
```

Verification rows may be marked PASS only from actual command results.

# Report Spec v2 Contract

## One editable source

A new report starts from one JSON file with `schema_version=report-spec-v2`. The JSON is the only editable analytical source. Markdown, calculated tables, decisions, price zones, Bundle, and Verification are compiler outputs.

## Required top-level objects

```text
report
facts
quarterly_series
assumptions
scenarios
decision_policy
narrative
sources
```

## Facts

Each fact requires:

- value
- unit
- period or as_of
- source
- tier
- confidence
- uncertainty when material

Facts are external observations. They are never model outputs.

## Quarterly series

`eps`, `revenue`, `operating_income`, and `fcf` each contain exactly four Fact IDs. The compiler derives TTM sums and ratios.

## Assumptions

Each assumption requires:

- scope: `global`, `bear`, `base`, or `bull`
- role
- rationale
- confidence
- scalar value or mode-specific fields

A scenario may reference only assumptions with its own scope or `global` scope.

## Revenue modes

- `guide_midpoint`: low, high, source
- `guide_high`: low, high, source
- `yoy`: growth and a prior-year same-quarter base reference
- `qoq`: growth and an immediately prior-quarter base reference
- `explicit`: value, source, rationale
- `consensus`: value, source, as_of

Do not put a growth percentage in a `guide_midpoint` assumption's value field. Guide modes are defined by low/high.

## Scenario requirements

Bear, Base, and Bull each require four forward revenue periods and assumption references for:

- operating_margin
- tax_rate
- other_income
- diluted_shares
- eps_cagr
- exit_pe
- dividend_yield
- reference_multiple
- safety_margin

## Outputs

The compiler emits:

- report Markdown
- `report-bundle-v2` JSON
- `report-verification-v2` JSON

These outputs are reproducible from the Spec. Manual edits invalidate verification.

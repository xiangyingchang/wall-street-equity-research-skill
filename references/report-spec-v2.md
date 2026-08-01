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

## v3.1 overlay

`report-spec-v3.1` keeps the v2 numerical core and adds `research`, `research_graph`, explicit `portfolio_context`, and explicit `prior_report_context`. It also requires:

- every Source to include a valid HTTPS `url`, ISO date no later than report `as_of`, publisher, document type, precise locator, and scope;
- no generic index/peer/source placeholders;
- `decision_policy.require_portfolio_context=true`;
- company-specific `decision_policy.operating.metrics[]`;
- homogeneous currency and scale for revenue, operating income, and FCF TTM series;
- the same per-share currency unit for EPS and current price.

Facts, calculations, assumptions, and portfolio observations remain distinct. Missing portfolio data is represented as `position_status=unknown`; it is never filled by inference.

Each operating metric's declared unit must equal the unit on its referenced Fact or derived object. Multi-period confirmation must resolve to an explicit non-negative integer Fact/Bundle value; fractional or silently assumed confirmation fails build.

`prior_report_context` is `available` or `not_available`. Available baselines record prior actions, reported Base IRR, rating/metric/thesis/method deltas, and calculation status. `recalculated` status requires the old price, starting EPS, EPS CAGR, exit PE, years, and dividend yield; the Compiler recomputes the old IRR and rejects a mismatching declared value. This preserves historical wording without preserving historical arithmetic errors.

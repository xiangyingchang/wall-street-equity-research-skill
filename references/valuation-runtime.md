# Valuation Runtime Contract

## Purpose

`scripts/valuation_runtime.py` is the deterministic numeric authority for:

1. four-quarter TTM derivations;
2. forward Revenue bridges;
3. Scenario EPS bridges;
4. shared IRR / Reverse Expectations / target-return price;
5. threshold-policy Action Evaluation;
6. Action robustness under input shocks.

Runtime never fetches data and never chooses economically reasonable assumptions. It guarantees only that declared, auditable inputs produce reproducible outputs. See `references/input-decision-robustness.md` for the complete v1.5 provenance and semantic contract.

## TTM Derivation

Use:

```bash
python3 scripts/valuation_runtime.py ttm-derive --input ttm.json
```

- `sum` requires exactly four unique periods.
- `ratio` requires four numerator and four denominator components covering the same periods.
- TTM operating margin is the ratio of period totals, not the average of quarterly margins.
- Every runtime output is copied into the TTM Derivation table and registered as `DERIVED-*`.

## Revenue Bridge

Use:

```bash
python3 scripts/valuation_runtime.py revenue-bridge --input revenue.json
```

Each Scenario has exactly four periods and each row uses one mode:

- `guide_midpoint`;
- `yoy`;
- `qoq`;
- `explicit`;
- `consensus`.

YoY/QoQ outputs are calculated from base value × (1 + growth). Guide outputs are calculated from the stated range. The report may not hand-fill a different result.

## Scenario EPS Bridge

Use:

```bash
python3 scripts/valuation_runtime.py eps-bridge \
  --revenue 2750 \
  --operating-margin 0.35 \
  --other-income 0 \
  --tax-rate 0.18 \
  --diluted-shares 25.7
```

The runtime calculates:

```text
operating income = revenue × operating margin
pre-tax income = operating income + other income/expense
net income = pre-tax income × (1 - tax rate)
EPS = net income ÷ diluted shares
```

The Revenue input must equal the matching `revenue-bridge` Scenario total.

## Shared Return Pair

New full reports use:

```bash
python3 scripts/valuation_runtime.py return-pair \
  --current-price 549 \
  --starting-eps 30.7101 \
  --eps-cagr 0.06 \
  --exit-pe 18 \
  --years 5 \
  --target-return 0.094 \
  --annual-dividend-yield 0.005
```

One command returns:

- terminal EPS and terminal price;
- cumulative dividends;
- total return and annualized IRR;
- Reverse Expectations terminal EPS and EPS CAGR;
- target-return-consistent current price;
- the shared assumptions used by both calculations.

Legacy `irr` and `reverse` commands remain available for old artifacts. New full reports may not cite them separately.

### Buyback rule

When growth is EPS CAGR, buybacks and dilution are already embedded in per-share growth. Do not add a separate buyback yield or share-count return. Explicit share-count modeling remains available only through net-income mode in the legacy Scenario IRR API.

## Canonical Values

Action Evaluation v2 accepts a `values` object. Every entry declares:

```json
{
  "value": "378.7",
  "kind": "DERIVED",
  "confidence": "medium",
  "uncertainty": "0.01"
}
```

Allowed kinds are `FACT`, `DERIVED`, and `MODEL`. IDs and registry Kind must agree.

## Threshold Policy

Each numeric condition references a threshold object with all fields:

```json
{
  "value": "400",
  "basis": "historical distribution",
  "lookback": "12 quarters",
  "confirmation": 2,
  "tolerance": "0.05",
  "minimum_confidence": "medium",
  "rationale": "sustained FCF deterioration"
}
```

Naked literals are legacy-only.

## Action Evaluation v2

Use:

```bash
python3 scripts/valuation_runtime.py evaluate-action --input action-evaluation.json
```

A v1.5 report records mode `v2-threshold-policy`.

Conditions use:

```json
{
  "value_id": "DERIVED-TTM-FCF",
  "operator": "<",
  "threshold": "THR-FCF-REDUCE",
  "confirmation_value": "DERIVED-CONSECUTIVE-FCF-BREACH"
}
```

Condition status is:

- `true`;
- `false`;
- `indeterminate`.

Indeterminate applies when confidence is below policy minimum, the value is within tolerance plus declared uncertainty, or confirmation is insufficient. An indeterminate rule capable of matching or outranking the current highest-priority action makes the resolved action `REVIEW`.

Default priority remains `SELL > REDUCE > ADD > BUY > HOLD`.

### Legacy modes

- scalar `facts` plus literal `value` / `value_fact` remain accepted for old artifacts;
- `resolve-action` remains available for old artifacts;
- neither legacy mode is acceptable in a new full report.

## Robustness

Use:

```bash
python3 scripts/valuation_runtime.py robustness \
  --input action-evaluation.json \
  --shock 0.05
```

The Action payload declares `sensitivity_values`. Runtime applies ±5% shocks and reports every shocked resolved action.

- `stable=true`: all shocked actions equal baseline.
- `stable=false`: at least one action changes; recommended action is `REVIEW`.

## Price Semantics

Reports keep four outputs separate:

| Output | Meaning |
|---|---|
| Forward reference value | Forward metric × reference multiple |
| Target-return price | Current price consistent with the stated return hurdle and Return Pair assumptions |
| Safety-margin buy price | Target-return price after an additional explicit uncertainty discount |
| Stress price | Downside Scenario output; not automatically a buy threshold |

Price zones should be anchored to target-return price. A price below forward reference value is not automatically a buy.

## Point-in-Time Share Rule

Weighted-average diluted shares are suitable for EPS, not for point-in-time market cap. Market cap must use period-end/current shares outstanding, or disclose an estimate and reconcile the difference.

## Delivery Order

1. Register quarterly source FACT values.
2. Run `ttm-derive` and register DERIVED values.
3. Register forward assumptions.
4. Run `revenue-bridge` for each Scenario.
5. Run `eps-bridge` using Revenue totals.
6. Register Basis IDs and Scenario reference values.
7. Run `return-pair` for each Scenario.
8. Register Threshold policies.
9. Run Action Evaluation v2 and robustness.
10. Run `valuation_consistency.py` and `input_decision_consistency.py`.
11. Run lint, recognition, and audit.
12. Deliver only when every Verification row is PASS.

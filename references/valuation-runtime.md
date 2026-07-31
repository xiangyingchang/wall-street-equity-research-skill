# Valuation Runtime Contract

## Purpose

`scripts/valuation_runtime.py` is the numeric authority for:

1. Scenario EPS Bridge；
2. 5-year Scenario IRR；
3. Reverse Expectations；
4. fact-based Action Matrix evaluation and resolution.

Runtime never fetches data and never decides which assumptions are reasonable. It guarantees that declared inputs produce reproducible outputs and that Action conditions are evaluated from canonical facts rather than analyst-supplied booleans.

## Canonical Fact Registry

Every full valuation report must contain:

| Fact ID | Metric | Value | Period/as-of | Source/Tier | Basis/Unit | Confidence |
|---|---|---:|---|---|---|---|

Rules:

- Fact ID must be unique and stable inside one report.
- Single-quarter, TTM, FY and Forward values require different Fact IDs.
- Action rules must reference Fact IDs, not restate prose values.
- When the same decision metric appears elsewhere, the Canonical Fact Registry is authoritative.
- A changed fact must trigger regeneration of all downstream runtime outputs.

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

The report must copy runtime outputs exactly. For the example above, EPS is approximately `$30.71`; `$22` would fail consistency validation.

### Forward Revenue Bridge

A Forward 12M EPS Bridge must first establish revenue using one of these methods:

1. Four explicit forward quarters/periods whose sum equals Scenario Revenue; or
2. A dated FY/NTM estimate from a declared source with a single matching period.

The default full-report template uses four periods. Undefined constructions such as `latest quarter ×4.5`, “4.5-quarter adjustment”, or an unexplained run-rate multiplier are forbidden.

## Historical Adjustments vs Scenario Assumptions

### One-off Adjustment Ledger

Use only for events that have already occurred, such as:

- historical non-cash tax charges or benefits;
- legal settlements;
- restructuring costs;
- asset impairments.

### Scenario Assumption Registry

Use for future assumptions, including:

- revenue growth;
- operating margin;
- other income;
- tax rate;
- diluted shares;
- Capex normalization;
- exit multiple;
- EPS CAGR.

A future Capex assumption is not a historical adjustment and Capex may never be labelled non-cash.

## Scenario IRR

Use:

```bash
python3 scripts/valuation_runtime.py irr \
  --current-price 549 \
  --starting-eps 22 \
  --eps-cagr 0.08 \
  --exit-pe 18 \
  --years 5 \
  --annual-dividend-yield 0.005
```

Required report fields:

- current price;
- starting EPS Basis ID;
- EPS CAGR;
- exit multiple;
- terminal EPS;
- terminal price;
- cumulative dividends;
- total return;
- annualized IRR.

### Buyback rule

When the growth input is EPS CAGR, buybacks and dilution are already reflected in per-share growth. Do not add a separate buyback yield or share-count change. The runtime rejects this combination.

To model share-count change explicitly, use `metric_mode=net_income`: start from net-income growth and provide share-count CAGR to derive terminal EPS.

## Reverse Expectations

Use:

```bash
python3 scripts/valuation_runtime.py reverse \
  --current-price 549 \
  --starting-eps 22 \
  --target-return 0.094 \
  --exit-pe 18 \
  --years 5
```

Default question:

> What terminal EPS and EPS CAGR are required for the current price to earn the stated annual target return at the stated exit multiple?

Do not confuse this with merely keeping the future share price equal to today's price.

## Fact-Based Action Evaluation

Full reports must use:

```bash
python3 scripts/valuation_runtime.py evaluate-action --input action-evaluation.json
```

Example:

```json
{
  "current_action": "Review",
  "facts": {
    "FACT-TTM-OP-MARGIN": 0.381,
    "FACT-TTM-FCF": 378.7,
    "FACT-CURRENT-PRICE": 549
  },
  "rules": [
    {
      "id": "hold-operating",
      "action": "HOLD",
      "logic": "all",
      "conditions": [
        {"fact": "FACT-TTM-OP-MARGIN", "operator": ">=", "value": 0.35},
        {"fact": "FACT-TTM-FCF", "operator": ">", "value": 400}
      ]
    },
    {
      "id": "reduce-operating",
      "action": "REDUCE",
      "logic": "all",
      "conditions": [
        {"fact": "FACT-TTM-OP-MARGIN", "operator": "<", "value": 0.35}
      ]
    }
  ]
}
```

Supported operators:

- `<`
- `<=`
- `>`
- `>=`
- `==`
- `!=`

Rules may use `logic=all` or `logic=any`. A condition can compare a fact with a literal `value`, or with another canonical fact through `value_fact`.

The runtime outputs:

- each condition's actual value, expected value, operator and boolean result;
- each rule's calculated `triggered` value;
- triggered rule IDs;
- resolved action;
- whether the reported action matches.

Fail-closed behavior:

- missing Fact ID: error;
- missing comparison value: error;
- unknown operator: error;
- invalid numeric comparison: error;
- duplicate or empty Rule ID: error;
- no triggered rule: `REVIEW`;
- same-priority conflicting actions: `REVIEW`.

Default priority is `SELL > REDUCE > ADD > BUY > HOLD`.

### Legacy resolver

`resolve-action` remains available only for backward compatibility with old artifacts. It accepts precomputed booleans and therefore is not acceptable for a new full report. `valuation_consistency.py` blocks full reports that cite the legacy command.

## Opportunity-Cost Types

Reports must distinguish:

| Type | Example | Meaning |
|---|---|---|
| Investable risk-free benchmark | Actual 10Y government bond yield | A real asset/yield available to investors |
| Required-return hurdle | 10Y yield ×2 | The user's equity return threshold; not an asset |
| Investable equity alternative | Broad index or peer company | An alternative risky asset |
| Target-company Scenario IRR | Base/Bear/Bull runtime IRR | Model output for the company |

Never label `10Y ×2` as a low-risk or risk-free investable asset.

## Source and Confidence Constraints

- SEC, issuer IR, and exchange notices are Tier 1.
- Yahoo Finance, StockAnalysis, Macrotrends, Koyfin, TIKR, Futu, and equivalent vendors are Tier 2.
- A current price from only one Tier 2 source cannot be marked Tier 1 or High-confidence cross-validated evidence.
- When the latest earnings release is newer than the latest filed 10-Q/annual report, or TTM/owner-earnings bases remain approximate, Information Richness is at most B and AI Research Confidence is at most Medium.

## Delivery Order

1. Populate Canonical Facts and Scenario Assumptions.
2. Generate Forward Revenue Bridge.
3. Run `eps-bridge` for every Bear/Base/Bull row.
4. Register Basis IDs using the runtime EPS outputs.
5. Run Scenario IRR and Reverse Expectations.
6. Run fact-based `evaluate-action`.
7. Run `valuation_consistency.py`.
8. Run `report_lint.py`.
9. Run recognition and audit verdict.

A structural PASS does not override a runtime or bridge mismatch.

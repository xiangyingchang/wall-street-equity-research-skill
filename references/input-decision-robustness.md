# Input Provenance and Decision Robustness Contract

## Purpose

v1.5 moves the trust boundary upstream. Correct formulas do not make unsupported inputs or arbitrary thresholds reliable. A full report must show where every decision-critical value came from, how every forward value was transformed, why every executable threshold exists, and whether the current action survives small input changes.

## 1. Canonical value kinds

Use one Canonical Value Registry:

| Value ID | Kind | Metric | Value | Period/as-of | Source/Tier | Basis/Unit | Confidence | Inputs/Formula |
|---|---|---|---:|---|---|---|---|---|

Allowed kinds:

- `FACT-*`: externally verifiable source value. Examples: quarterly revenue, quarter-end shares outstanding, current price.
- `DERIVED-*`: deterministic calculation from registered FACT/DERIVED inputs. Examples: TTM EPS, TTM operating margin, net cash.
- `MODEL-*`: analytical output. Examples: fair value, target-return price, Scenario IRR, stress price.

Rules:

1. The ID prefix must match Kind.
2. `FACT-*` may not contain fair value, IRR, target price, buy price, or stress price semantics.
3. Every `DERIVED-*` includes component IDs and formula/runtime reference.
4. Single-quarter, TTM, FY, Forward, and point-in-time values use distinct IDs.
5. Scenario assumptions remain in Scenario Assumption Registry rather than the Canonical Value Registry.

## 2. TTM derivation

New reports use:

```bash
python3 scripts/valuation_runtime.py ttm-derive --input ttm.json
```

Supported modes:

- `sum`: exactly four unique quarterly components;
- `ratio`: four numerator and four denominator components covering the same periods.

Example TTM EPS input:

```json
{
  "id": "DERIVED-TTM-EPS",
  "metric": "TTM EPS",
  "mode": "sum",
  "components": [
    {"id": "FACT-Q3-2025-EPS", "period": "Q3 2025", "value": "1.05"},
    {"id": "FACT-Q4-2025-EPS", "period": "Q4 2025", "value": "8.88"},
    {"id": "FACT-Q1-2026-EPS", "period": "Q1 2026", "value": "10.44"},
    {"id": "FACT-Q2-2026-EPS", "period": "Q2 2026", "value": "6.18"}
  ]
}
```

This outputs `26.5500`.

A TTM margin must use the ratio of four-quarter totals, not an average of quarterly percentages.

## 3. Revenue forecast runtime

New reports use:

```bash
python3 scripts/valuation_runtime.py revenue-bridge --input revenue.json
```

Each scenario contains exactly four forward periods. Each period uses one mode:

- `guide_midpoint`: `low`, `high`, and source;
- `yoy`: base value/base ID and growth;
- `qoq`: base value/base ID and growth;
- `explicit`: value, source, and rationale;
- `consensus`: value, source, and as-of date.

The report table must expose the actual transformation inputs:

| Revenue Bridge ID | Scenario | Period | Mode | Base Value | Growth | Guide Low | Guide High | Revenue | Source/Assumption ID | Runtime ref |

A label such as `+12% YoY` is invalid unless the shown revenue reconciles to `base × (1 + 12%)`.

Scenario ordering rules:

- Bull below Base for a matching period requires an explicit timing/mix explanation and is at least a warning.
- Base and Bull totals that are effectively equal while using different growth assumptions are an error unless the report explicitly reconciles the path and timing.

## 4. Shared return pair

New reports use:

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

One command outputs:

- terminal EPS and price;
- cumulative dividends;
- total return and annualized IRR;
- Reverse Expectations terminal EPS and EPS CAGR;
- target-return-consistent current price.

The dividend assumption, years, exit PE, starting EPS, and target return are shared. Separate `irr` and `reverse` commands remain for legacy artifacts only.

### Price semantics

Do not collapse these outputs:

1. **Forward reference value**: forward metric × reference multiple.
2. **Target-return price**: maximum current price consistent with the stated target annual return and Return Pair assumptions.
3. **Safety-margin buy price**: target-return price after any additional explicit uncertainty discount.
4. **Stress price**: downside scenario value, not automatically a buy threshold.

Price zones should normally be anchored to target-return price, not to forward reference value multiplied by an arbitrary percentage.

## 5. Threshold Policy Registry

Every executable numeric condition references a registered Threshold ID:

| Threshold ID | Metric | Value | Basis | Lookback | Confirmation | Tolerance | Minimum confidence | Rationale |

Required semantics:

- **Basis**: management guidance, historical distribution, valuation output, covenant, thesis-break level, or other auditable basis.
- **Lookback**: period used to set or test the threshold.
- **Confirmation**: number of observations/periods required.
- **Tolerance**: neutral band around the threshold.
- **Minimum confidence**: lowest acceptable input confidence.
- **Rationale**: why crossing this threshold maps to the stated action.

Naked conditions such as `TTM FCF < 400` are invalid in a new report. Use `DERIVED-TTM-FCF < THR-FCF-REDUCE`.

## 6. Action Evaluation v2

New reports use `values` and `thresholds`, not legacy scalar `facts` and raw literals:

```json
{
  "current_action": "REVIEW",
  "values": {
    "DERIVED-TTM-FCF": {
      "value": "378.7",
      "kind": "DERIVED",
      "confidence": "medium",
      "uncertainty": "0.01"
    }
  },
  "thresholds": {
    "THR-FCF-REDUCE": {
      "value": "400",
      "basis": "historical distribution",
      "lookback": "12 quarters",
      "confirmation": 2,
      "tolerance": "0.05",
      "minimum_confidence": "medium",
      "rationale": "sustained FCF deterioration"
    }
  },
  "rules": [
    {
      "id": "reduce-op",
      "action": "REDUCE",
      "logic": "all",
      "conditions": [
        {
          "value_id": "DERIVED-TTM-FCF",
          "operator": "<",
          "threshold": "THR-FCF-REDUCE",
          "confirmation_value": "DERIVED-CONSECUTIVE-FCF-BREACH"
        }
      ]
    }
  ]
}
```

Condition status is tri-state:

- `true`;
- `false`;
- `indeterminate`.

Indeterminate applies when:

- value confidence is below policy minimum;
- value is inside tolerance plus declared measurement uncertainty;
- confirmation requirement is not met.

If an indeterminate rule can match or outrank the highest triggered action, resolved action is `REVIEW`.

## 7. Robustness test

Run:

```bash
python3 scripts/valuation_runtime.py robustness \
  --input action-evaluation.json \
  --shock 0.05
```

The input declares `sensitivity_values`. Runtime applies ±5% shocks and re-evaluates the Action Matrix.

- `stable=true`: every shocked scenario resolves to the baseline action.
- `stable=false`: at least one small shock changes the action.

A new full report with `stable=false` cannot present a deterministic Buy/Add/Reduce/Sell. The action must be `REVIEW`, unless a separately documented portfolio constraint—not the single-stock threshold—requires action.

## 8. Semantic consistency

`scripts/input_decision_consistency.py` blocks:

- model output registered as FACT;
- TTM DERIVED value without component/runtime provenance;
- unreconciled YoY/QoQ/guide revenue rows;
- different growth assumptions producing effectively identical Base/Bull totals without reconciliation;
- naked Action thresholds;
- missing Threshold policy fields;
- separate new-report `irr` and `reverse` commands;
- missing Return Pair target-return price;
- unstable robustness with a non-REVIEW resolved action;
- current price inside a buy zone while First Page says no-buy or Reduce/Sell;
- weighted-average diluted shares used directly for market cap without point-in-time reconciliation;
- conflicting structured TTM operating-margin values;
- Verification TODO / FAIL / unrun / Unknown or missing required checks.

Run it after `valuation_consistency.py` and before structural lint/audit.

## 9. Verification contract

Every full report contains actual results for:

- TTM derivation runtime;
- Revenue bridge runtime;
- EPS bridge runtime;
- Return Pair runtime;
- fact-based Action Evaluation;
- Action robustness;
- valuation consistency;
- input/decision consistency;
- lint;
- audit verdict.

Every row must be PASS. A placeholder is a failed delivery, not a documentation note.

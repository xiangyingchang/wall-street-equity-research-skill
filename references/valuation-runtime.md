# Valuation Runtime Contract

## Purpose

`valuation_runtime.py` is the numeric authority for 5-year IRR, Reverse Expectations, and Action Matrix resolution. Reports may explain its outputs, but may not hand-write different values.

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

- current price
- starting EPS Basis ID
- EPS CAGR
- exit multiple
- terminal EPS
- terminal price
- cumulative dividends
- total return
- annualized IRR

### Buyback rule

When the growth input is EPS CAGR, buybacks and dilution are already reflected in per-share growth. Do not add a separate buyback yield or share-count change. The runtime rejects this combination.

If the analyst wants to model share-count change explicitly, use `metric_mode=net_income`: start from net income growth and provide share-count CAGR to derive terminal EPS.

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

Reverse Expectations must answer a stated question. The default question is:

> What terminal EPS and EPS CAGR are required for the current price to earn the stated annual target return at the stated exit multiple?

Do not confuse this with the lower hurdle of merely keeping the future share price equal to today's price.

## Normalized EPS Bridge

No normalized EPS Basis may be registered without a scenario bridge containing all fields below:

| Bridge ID | Scenario | Revenue | Operating margin | Operating income | Other income/expense | Pre-tax income | Tax rate | Net income | Diluted shares | EPS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|

Rules:

1. `Operating income = Revenue × Operating margin`.
2. `Pre-tax income = Operating income + other income/expense`.
3. `Net income = Pre-tax income × (1 - tax rate)` unless a separately sourced tax bridge is used.
4. `EPS = Net income ÷ diluted shares`.
5. Every Bear/Base/Bull EPS Basis ID must cite exactly one Bridge ID.
6. Labels such as “30% margin corresponds to $18 EPS” are insufficient without the full bridge.

## Action Resolution

Action Matrix rows still define the policy, but their current truth values must be evaluated explicitly and passed to:

```bash
python3 scripts/valuation_runtime.py resolve-action --input action-evaluation.json
```

Example:

```json
{
  "current_action": "Reduce",
  "rules": [
    {"id": "hold-operating", "action": "HOLD", "triggered": false},
    {"id": "reduce-operating", "action": "REDUCE", "triggered": false},
    {"id": "sell-thesis", "action": "SELL", "triggered": false}
  ]
}
```

If no rule is triggered, the resolved action is `REVIEW`. The report must not invent an action to fill the gap. If the reported action differs from `resolved_action`, delivery fails.

Default priority is `SELL > REDUCE > ADD > BUY > HOLD`. Same-priority conflicts resolve to `REVIEW`.

## Source and confidence constraints

- SEC, issuer IR, and exchange notices are Tier 1.
- Yahoo Finance, StockAnalysis, Macrotrends, Koyfin, TIKR, Futu, and equivalent vendors are Tier 2.
- A current price from only one Tier 2 source cannot be marked Tier 1 or High-confidence cross-validated evidence.
- When the latest earnings release is newer than the latest filed 10-Q/annual report, or TTM/owner-earnings bases remain approximate, Information Richness is at most B and AI Research Confidence is at most Medium.

## Delivery order

1. Generate and record runtime outputs.
2. Run `valuation_consistency.py`.
3. Run `report_lint.py`.
4. Run report recognition and audit verdict.

A structural PASS does not override a runtime mismatch.

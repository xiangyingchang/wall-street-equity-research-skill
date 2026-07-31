\
# Valuation Consistency

This reference is authoritative for valuation-basis identity, adjustment bridges,
scenario math, and the boundary between fair value and an executable buy price.
It complements `data-validation.md`: data validation checks evidence provenance;
this file checks whether the report uses that evidence coherently.

## Core rule

A report may be conservative once. It may not stack a pessimistic earnings base,
a pessimistic multiple, and a second unexplained discount and then call the result
"fair value". Separate these concepts:

- **Fair value:** the value implied by one explicit scenario before a safety discount.
- **Buy price:** fair value after one explicit safety-margin discount.
- **Stress price:** the value of a separate Bear/Stress scenario, not another name for
  the Base-case buy price.

When evidence cannot distinguish two nearby prices reliably, output a range and lower
confidence. Do not manufacture false precision to satisfy a template.

## 1. Valuation Basis Registry

Module 4 must contain exactly one table with these columns:

| Basis ID | Metric | Value | Period | Adjustments | Use |
|---|---|---:|---|---|---|

Rules:

1. `Basis ID` is unique and stable within the report.
2. Every EPS/FCF value used in a scenario references one registered Basis ID.
3. `Adjustments` is `None` or a comma-separated list of Adjustment IDs.
4. A normalized or adjusted basis without a documented bridge is invalid.
5. Bear, Base, and Bull are scenario labels. Do not rename the Bear basis as
   "mid-cycle" or "central" merely to make a low target look objective.
6. The `Use` column states whether the basis supports reported valuation, Base case,
   Bear case, Bull case, payback pressure test, or another explicit purpose.

## 2. One-off Adjustment Ledger

If any report text uses `adjusted`, `normalized`, `core`, `中枢`, `调整后`, or
`正常化` for EPS, FCF, profit, or margin, module 2 must include:

| Adjustment ID | Period | Item | Pre-tax/after-tax | Cash/non-cash | Repeatability | Per-share impact | Treatment | Source |
|---|---|---|---|---|---|---:|---|---|

Rules:

- Tax charges and later tax benefits from the same event must be treated symmetrically.
- Legal and restructuring expenses are not automatically non-recurring. State their
  cash character and recurrence probability.
- `Per-share impact` may be a range or `Unclear`; invented precision is worse than a
  declared gap.
- A report may decline to adjust an item. Record that decision instead of silently
  omitting it.

## 3. Scenario Valuation

Module 4 must contain:

| Scenario | Basis ID | Metric value | Multiple | Fair value | Safety margin | Buy price | Key assumptions |
|---|---|---:|---:|---:|---:|---:|---|

The arithmetic is binding:

```text
Fair value = Metric value × Multiple
Buy price = Fair value × (1 - Safety margin)
```

Tolerance is 2% for displayed rounding. Scenario fair values should normally satisfy
`Bear <= Base <= Bull`. Any exception requires an explicit explanation beside the
table and must not be hidden by relabeling scenarios.

The First-Page Verdict and module 8 price zones must be derived from this table. They
must not introduce a second independent set of price boundaries.

## 4. Capex / Owner Earnings Bridge

For high-capex companies, distinguish at least:

| Item | Value/range | Period | Evidence | Confidence |
|---|---:|---|---|---|
| Reported OCF |  |  |  |  |
| Reported Capex |  |  |  |  |
| Reported FCF |  |  |  |  |
| Maintenance Capex |  |  |  |  |
| Growth Capex |  |  |  |  |
| Strategic / AI Capex |  |  |  |  |
| Owner Earnings / Normalized FCF |  |  |  |  |

Missing company disclosure may be recorded as `Unclear`. Do not annualize one quarter
of FCF and present it as durable earning power without a cash bridge and explicit
seasonality/procurement analysis.

## 5. Three-model valuation triangle

The 10-year payback remains mandatory, but it is a **pressure test**, not a complete
DCF and not a sole veto. The default decision synthesis is:

1. **5-year scenario IRR (primary):** Bear/Base/Bull operating assumptions, exit
   multiple, dividends/buybacks, and dilution.
2. **Reverse expectations / reverse DCF:** what growth, margin, and capital intensity
   are implied by today's price.
3. **10-year payback pressure test:** whether the valuation requires physically
   implausible compounding under a deliberately harsh zero-terminal-value lens.

Suggested synthesis weights are 50% / 30% / 20%; they are judgment aids, not a fake
weighted-score machine. A failed payback test raises the hurdle and lowers confidence,
but does not by itself force Reduce/Sell when the other models and business evidence
support an adequate expected IRR.

## 6. Opportunity cost

Compare **expected shareholder total return / IRR** with the relevant bond, index, and
high-quality alternative assets. Do not require a growing company's current FCF yield
to mechanically exceed `10Y Treasury ×2`; that confuses a current yield with a total
return hurdle. Keep `10Y ×2` as the user's required-return benchmark when appropriate.

## 7. Action Matrix

Operating triggers should normally use TTM or consecutive-quarter evidence. A single
quarter of capex timing or working-capital noise should not automatically force a
large position change. Sell remains a thesis-break action; threshold misses are
warnings unless the report explains why they constitute a durable thesis break.

## 8. Required semantic audit

Before `report_lint.py` and `report_audit.py`, run:

```bash
python3 scripts/valuation_consistency.py /path/to/report.md
```

The checker validates table contracts, Basis/Adjustment references, scenario math,
scenario ordering, basic PE/FCF-yield recomputation, and several high-confidence prose
contradictions. Warnings require human review; errors block delivery.

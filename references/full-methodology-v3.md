# optimized-v3 Full Methodology

Read this file for a full report. Keep the visible report narrative concise;
put detailed source notes in the Evidence Ledger and Sources section.

## 1. Input and source preflight

Record ticker, market, tax identity, holding period, opportunity-cost benchmark,
current holding state, and position/target amount. If omitted, declare defaults
before the First-Page Verdict.

For US/HK/other non-A-share names, inspect the latest company IR release or
deck, regulator filing, current close/latest session price, relevant 10Y yield,
peer valuation, and filing gaps. Use Tier 1 sources for facts and Tier 2 only for
cross-checks. Never fill live numbers from model memory.

## 2. Evidence Ledger and bridge

Build the ledger before prose. For every key number record date, unit, period,
source tier, URL/locator, accounting definition, and confidence. Construct the
TTM bridge from compatible quarterly or FY/YTD periods. Show:

- Reported: filing value;
- Adjusted: only adjustments supported by evidence;
- Normalized: explicit model assumption and confidence;
- profit normalization separately from cash-flow normalization.

For high-CapEx names, state whether the current CapEx regime is structural,
planned, temporary, or unresolved. Keep SBC, repurchases, and share-count trend
visible rather than treating buybacks as automatically accretive.

## 3. Module guidance

### 1. Overview

Explain how the company earns money, where profit actually comes from, industry
structure, Bull/Base/Bear conditions, and the 12-24 month variables. Add 1-3 Key
Forces and explicitly state what the latest filing changed and did not change.

### 2. Financial Autopsy

Show five-year revenue/profit/OCF/CapEx/FCF trends, TTM and Forward, margins,
SBC, buybacks, debt, cash, leases, and the denominator used for each per-share
metric. Reconcile GAAP earnings distortions before valuation.

### 3. Moat Analysis

Test scale, switching costs, network effects, brand/distribution, cost advantage,
and competitor response. A network-effect claim requires current scale, period
change, and an engagement or monetization metric.

### 4. Valuation and payback

Run EPS and FCF/share in parallel. For high-CapEx names also run EV/FCF and state
which base controls the verdict. Use these formulas through the deterministic
runtime:

```text
TTM nominal:       M = sum((1+g)^t for t=1..10)
Forward nominal:   M = sum((1+g)^t for t=0..9)
Discounted:        M = sum(((1+g)/(1+r))^t for t=1..10)
```

Show the three V3 discount scales: 10Y x2, 8%, and 10%. Record the input vector:
starting EPS/FCF, CAGR, exit multiple, years, target return, dividend yield,
dividend mode, safety margin, and share denominator.

### 5. Liquidity and Cap Filter

For liquid large caps, say why liquidity is not a constraint. When it is a
constraint, show average traded value, position value, stress participation,
and exit days. Do not mechanically add a small-cap stress table to every report.

### 6. Risk Ranking

Rank the risks by probability and damage. Each top risk needs a leading indicator,
what would falsify the thesis, and the action if it occurs.

### 7. Growth Potential

Estimate market size, share, growth ceiling, catalysts, reinvestment needs, and
whether the required payback growth is physically reachable.

### 8. Tax Drag and Net Yield

State the investor tax identity. For dividends, show gross dividend, withholding,
growth assumption, years, and the after-tax total from `dividend-total`. For
buybacks, test whether shares actually declined after SBC. Do not call a paper
investment gain distributable cash.

### 9. Institutional and Opportunity Cost

Compare the stock with the relevant 10Y x2 hurdle, index, peer, and higher-
certainty alternatives. Write the Variant View: what consensus gets wrong and
what evidence would prove the variant wrong.

### 10. Position and risk rules

Do not infer a current holding from an old report. If Ledger is unavailable, say
`持仓未核验`. Provide maximum position, add/reduce/exit conditions, Pre-Mortem,
and quantified Action Triggers.

### 11. Final Verdict

Before the four-level rating, answer explicitly:

1. Is holding equivalent to buying at today's price?
2. Does this beat the opportunity-cost alternative?
3. Does the 10-year payback work under the stated scale?

Then provide one rating, price lines, confidence, and the smallest set of data
that must be refreshed before acting.

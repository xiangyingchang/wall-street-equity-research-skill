# optimized-v3 Report Contract

## Output order

The saved Markdown report must contain exactly this top-level order:

1. `## First-Page Verdict`
2. `## Evidence Ledger`
3. `## 1.` through `## 11.`
4. `## Sources`

Optional comparisons, prior-report deltas, and data caveats belong inside the
nearest module; they must not interrupt this order.

New reports must not begin with visible YAML frontmatter.

## First-Page Verdict

Include: rating (`Buy`, `Hold-Index`, `Watchlist`, or `Avoid`), current action,
whether today's price is worth re-buying, opportunity-cost result, 10-year
payback result, price range, largest risk, confidence, and 1-3 items requiring
manual review.

## Evidence Ledger

Each key number records value, date, source URL or filing, source tier, unit,
period/definition, and confidence. At minimum cover price, market cap, revenue,
profit, OCF, CapEx, FCF, EPS, FCF/share, shares, cash, debt, dividends, buybacks,
SBC, segment metrics, yield, and peer valuation where relevant.

## Eleven modules

1. Overview: business model, industry, Bull/Base/Bear, 12-24 month variables,
   Key Forces, and what the latest report changed or did not change.
2. Financial Autopsy: five-year trend, TTM/Forward, Reported/Adjusted/
   Normalized bridge, profit-vs-cash normalization, CapEx regime, SBC and
   buyback quality, and share-count trend.
3. Moat Analysis: customer/user scale, engagement or monetization, switching
   costs, network effects, competitors, and anti-fragility.
4. Valuation and 10-year payback: TTM/Forward/Normalized EPS and FCF/share,
   EV/FCF, target PE, deterministic price lines, nominal payback, and three
   discounted scales: 10Y x2, 8%, and 10%. A 10Y x1 row may be added.
5. Liquidity and Cap Filter: liquidity conclusion, position-size stress math
   only when the company or position makes it relevant.
6. Risk Ranking: ranked business, balance-sheet, regulatory, capital-allocation,
   and valuation risks with falsification evidence.
7. Growth Potential: TAM, share, growth ceiling, catalysts, and physical limits.
8. Tax Drag and Net Yield: investor tax identity, withholding, after-tax
   dividends, buyback quality, and the explicit dividend calculation vector.
9. Institutional and Opportunity Cost: peers, bonds, index, and the alternative
   use of capital; include the Variant View.
10. Position Sizing and Exit Rules: current holding state, sizing, add/reduce/
    exit rules, Pre-Mortem, and quantified Action Triggers.
11. Final Verdict: the three principles, one rating, price lines, confidence,
    and review checklist.

## Math and accounting rules

### Dividend total

For nominal after-tax dividends over `n` years:

```text
after_tax_total = sum(dividend_0 * (1 + dividend_growth)^t * (1 - withholding_rate)
                      for t in 0..n-1)
```

Use `scripts/valuation_math.py dividend-total`; do not confuse a nominal sum
with a reinvested-yield return component.

### Share denominators

- Market cap: point-in-time common shares outstanding at the price date.
- EPS: diluted weighted-average shares from the relevant filing.
- FCF/share: diluted weighted-average shares for the matching period when
  available; otherwise disclose the proxy denominator and lower confidence.

### Security classification

Separate current/non-current marketable securities, non-marketable securities,
restricted securities, cash, debt, and lease liabilities. Only call an amount
net cash when the included assets are liquid enough for that use.

### Normalization

Reported, Adjusted, and Normalized values are distinct. A non-cash income
statement adjustment cannot be added back to FCF without cash-flow or company
evidence. For high-CapEx companies, compare quarterly CapEx, full-year guidance,
OCF run rate, depreciation, and assets not yet in service.

## Rating gates

`Buy` requires a positive current-price re-buy decision, opportunity-cost pass,
and a physically defensible 10-year payback result. If key data are unresolved,
use `Watchlist` or `Avoid`; never convert uncertainty into a Buy.

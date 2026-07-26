# Data Validation

Use this reference before assigning confidence to a report. It governs source choice and reconciliation; it does not permit automatic data fetching.

## Source hierarchy by market

| Market | Tier 1 authority | Practical Tier 2 cross-check |
|---|---|---|
| US | SEC EDGAR filings, issuer IR releases/decks, NYSE/Nasdaq notices | Market data vendors such as StockAnalysis, Macrotrends, Yahoo Finance, Koyfin, or TIKR |
| Hong Kong | HKEXNews filings and issuer IR | AASTOCKS, Futu, Bloomberg-style/vendor snapshots; use ADR data only after FX and ADR-ratio reconciliation |
| A-share | 巨潮资讯/CNINFO filings, SSE/SZSE notices, issuer announcements | Eastmoney, Tonghuashun, Wind-style/vendor snapshots |

Tier 1 decides a conflict. Tier 2 is useful for speed and independent cross-checking, but cannot replace a filing or an official market notice.

## Discrepancy rules

| Difference | Required treatment |
|---:|---|
| <=1% | Mark consistent; retain both sources in the Evidence Ledger. |
| >1%-5% | Reconcile and explain before using: GAAP/non-GAAP, FX date, reporting date, unit scale, or basic/diluted shares. |
| >5% | Block the figure from analysis until Tier 1 verification resolves it. |

Use `scripts/financial_rigor.py cross-validate` for a reproducible direct source-range check. After lint, run `python3 scripts/report_audit.py extract --report <report.md> --manifest-out <manifest.json> --results-out <results.json>`; it writes the exact hashed manifest and a fillable results template. Fill each result's `fresh_value`, source `name/tier/source_url/authority_type`, and, for Tier 2, independent `secondary_source.value` plus boolean `reconciliation` and explanation. Run `python3 scripts/report_audit.py verdict --report <report.md> --manifest <manifest.json> --results <results.json>`. Neither script fetches data.

The audit denominator is only full-cell numeric values in eligible Markdown table columns. Label, date, source, tier, basis/口径, judgment, description, notes, and confidence columns are excluded before parsing. Descriptive or compound cells and all prose numbers are outside automated coverage, so every key decision number must appear as a standalone table value. Verdict reconstructs the eligible universe and deterministic selection from the current report; a self-rehashed reduced, added, or altered manifest blocks.

## Manual verification boundaries

- Record the value date, fiscal/reporting period, currency, unit, source tier, and accounting basis beside every key number.
- Do not compare GAAP and non-GAAP profit, TTM and fiscal-year totals, basic and diluted EPS, or pre- and post-transaction share counts as if they were the same field.
- Convert FX only with the stated rate and date; do not merge close, regular-session, and after-hours prices.
- For market cap, use a contemporaneous actual price and latest share count. Repurchases, issuance, ADR ratios, and treasury shares may explain a mismatch but must be recorded.
- Historical price comparisons must state adjustment basis. Use a consistent split/dividend-adjusted series for historical returns and valuation bands; do not mix it with unadjusted current snapshots.
- Filing fundamentals (market cap, shares, revenue, net income, EPS, FCF/share, cash, debt) require Tier 1 validation. Current market price and government yield may use declared Tier 2 only with a second independent allowed source, both values, a boolean reconciliation field, and a non-empty explanation. Blogs, forums, and social posts are not allowed sources.
- Tier 2 independence is evaluated by normalized allowlisted vendor domain, so different URLs or subdomains of the same vendor are not independent. The script does not implement a general public-suffix registry; only configured evidence hosts are accepted.
- Automation may calculate, extract, and flag. It validates declared source structure but cannot prove real-world provenance; a human must retrieve sources, confirm issuer domains, judge accounting equivalence, resolve conflicts, and decide freshness.

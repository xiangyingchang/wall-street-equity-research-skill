# Data Validation

Use this reference before assigning confidence to a report. It governs source choice and reconciliation; it does not permit automatic data fetching.

## Source hierarchy by market

| Market | Tier 1 authority | Practical Tier 2 cross-check |
|---|---|---|
| US | SEC EDGAR filings, issuer IR releases/decks, NYSE/Nasdaq notices | Market data vendors such as StockAnalysis, Macrotrends, Yahoo Finance, Koyfin, or TIKR |
| Hong Kong | HKEXNews filings and issuer IR | AASTOCKS, Futu, Bloomberg-style/vendor snapshots; use ADR data only after FX and ADR-ratio reconciliation |
| A-share | 巨潮资讯/CNINFO filings, SSE/SZSE notices, issuer announcements | Eastmoney, Tonghuashun, Wind-style/vendor snapshots |

Tier 1 decides a conflict. Tier 2 is useful for speed and independent cross-checking, but cannot replace a filing or an official market notice.

For v3.1, every registered Source must include the direct HTTPS URL actually used plus a precise locator inside that document or index. A publisher label, search-result title, or generic phrase such as “peer filings” is not a source. Reader renders clickable links; Audit preserves the full URL and locator.

## Discrepancy rules

| Difference | Required treatment |
|---:|---|
| <=1% | Mark consistent; retain both sources in the Evidence Ledger. |
| >1%-5% | Reconcile and explain before using: GAAP/non-GAAP, FX date, reporting date, unit scale, or basic/diluted shares. |
| >5% | Block the figure from analysis until Tier 1 verification resolves it. |

Use `scripts/financial_rigor.py cross-validate` for a reproducible direct source-range check. `scripts/new_report.py` runs recognition automatically for generated skeletons; manually created or copied skeletons must run `python3 scripts/report_audit.py recognize --report <report.md>` explicitly. Both paths rerun recognition after lint and before extraction. Recognition traverses the same Markdown tables and uses the exact matching/classification authority as extraction, but accepts placeholder or non-numeric values. Then run `python3 scripts/report_audit.py extract --report <report.md> --manifest-out <manifest.json> --results-out <results.json>`; it writes the exact hashed manifest and a fillable results template. Fill each result's `fresh_value`, source `name/tier/source_url/authority_type`, and, for Tier 2, independent `secondary_source.value` plus boolean `reconciliation` and explanation. Run `python3 scripts/report_audit.py verdict --report <report.md> --manifest <manifest.json> --results <results.json>`. None of these commands fetches data.

## Canonical payback formulas

Use `python3 scripts/financial_rigor.py payback --formula-id <id> --multiple <M> --discount-rate <r> --years <N> --json` for reproducible payback roots. `payback_ttm_v1` defines `M = sum(t=1..N) [((1+g)/(1+r))^t]`. `payback_forward_v1` defines `M = sum(t=1..N) [(1+g)^(t-1)/(1+r)^t]`; the first Forward term is discounted at `t=1`, never at `t=0`. Nominal cases use the selected formula with `r=0`, not a separate shortcut.

The engine uses Decimal precision 50, requires `M>0`, positive integer years, `r>-1`, and a solved root `g>-1`. Convergence requires all three checks: interval width `<=1e-24`, absolute residual `<=1e-24`, and, for a nonzero target, relative residual `<=1e-24`. `payback_forward_v1` with `years=1` is always rejected as non-identifiable because its modeled multiple is growth-independent, even when the target matches that constant. JSON numeric fields, including `interval_width`, are strings. Keep full-precision roots in audit artifacts and round only in the report or other caller-owned display layer.

The same registry exposes exact Decimal `sum_v1`, `difference_v1`, `product_v1`, `ratio_v1`, `ttm_sum_v1`, and `ttm_bridge_v1`. Pack-backed derived inputs are reference-only: `fact_ref` resolves value, unit, `as_of`, and source IDs from a registered decimal fact; `derived_ref` resolves them recursively from another registered record. A caller may not repeat those fields in either reference. Only a positive integer payback `years` input may use `literal` with unit `year`. Cycles, undefined references, and duplicate input names fail closed.

`ttm_sum_v1` requires exactly four unique consecutive `FYyyyy-Qn` periods; resolved dates must strictly increase, adjacent quarters must be 70-115 days apart, and labels must be within one calendar year of their dates. The set's unique `FYyyyy-Q4` period end must have year exactly `yyyy`, preventing a whole-set one-year label shift. `ttm_bridge_v1` requires exactly one `fy`, `current_ytd`, and `prior_ytd`, computes `FY + current YTD - prior YTD`, requires FY/prior in one fiscal year and current in the adjacent year, requires FY duration 4 and equal current/prior YTD durations from 1 through 3, and enforces `prior_ytd < fy < current_ytd`. The annual FY period end year must exactly match its declared fiscal year; current/prior YTD dates are 350-385 days apart, and each bridge leg fits a 13-week-per-quarter window with 35-day 52/53-week tolerance. A single aggregate TTM input or detached chronology is never accepted. Formula validation also enforces unit algebra and scale: additive formulas require identical units, ratios preserve compatible dimensions or supported currency/share pairs, products allow only registered combinations, and payback requires `x`, `ratio`, and `year`.

## Durable research recovery

For resumable or multi-session work, use `research-pack-v1` as described in `references/research-pack-v1.md`. Initialization stores absolute report/previous-report paths and refuses report/pack symlinks. Register canonical HTTPS sources before declaring `sources_ready`; add typed facts that cite those source IDs before `facts_ready`; then lock the exact positive Decimal price/share basis before valuation work. Every downstream stage requires all predecessors to remain `CURRENT` under recomputed hashes. Source changes remove source-dependent checkpoints, fact changes remove fact-dependent checkpoints, and a reasoned valuation revision removes the valuation lock and every later checkpoint.

The pack is durable recovery state, not evidence authority. Its hashes prove only that the recorded upstream inputs are unchanged. Re-open sources and apply the discrepancy and provenance rules above before using a resumed value. Valuation revision requires every upstream checkpoint through `facts_ready` to be current by recomputed hash, even when `valuation_locked` itself is stale. Strict JSON rejects duplicate object keys, non-finite constants, unknown defined keys, malformed types, missing source IDs, and recursive case-insensitive `provider`, `model`, `token`, `tokens`, `finish_reason`, `timing`, `retry`, `runtime`, `latency`, `duration`, `started_at`, or `ended_at` keys while preserving evidence dates and `as_of`. Original URLs containing ASCII controls or DEL anywhere are rejected before parsing. `derived_records` use the strict contract in `research-pack-v1.md`; `evidence_gates` remains empty until its later batch. Every supported research-pack mutation holds one shared advisory lock for its full read-modify-write sequence. This serializes cooperative skill writers only; external processes that ignore the lock remain able to mutate the file.

Audit v4 remains the legacy manual fresh-results workflow described above, with unchanged bytes, decision logic, and numeric grammar; `$10/share` remains ineligible under v4. Report/manifest/results paths must resolve distinctly; extraction rejects symlink outputs, validates before writing, and atomically commits both outputs with rollback. Audit v5 is selected only by `extract --pack`: validated immutable snapshots bind every derived record to one numeric Markdown cell and reject parsed objects whose exact recursive Python types differ from their JSON bytes. V5 verdict recursively reruns formulas, validates payback residuals, unit algebra/conversion, `ROUND_HALF_UP` rounding, resolved provenance, checkpoints, and cells, and accepts no `results.json`. It acquires the shared advisory lock before re-reading/comparing the pack snapshot and holds it through reconstruction and atomic persistence. Cooperative skill writers therefore cannot be overwritten; arbitrary lock-bypassing filesystem writes are outside that guarantee. PASS writes the exact manifest-bound pack, whose SHA-256 equals the manifest; identical reruns remain PASS without rewriting. Neither version fetches data.

The audit denominator is only full-cell numeric values in eligible Markdown table columns. Label, date, source, tier, basis/口径, judgment, description, notes, and confidence columns are excluded before parsing. Descriptive or compound cells and all prose numbers are outside automated coverage, so every key decision number must appear as a standalone table value. Verdict reconstructs the eligible universe and deterministic selection from the current report; a self-rehashed reduced, added, or altered manifest blocks.

## Manual verification boundaries

- Record the value date, fiscal/reporting period, currency, unit, source tier, and accounting basis beside every key number.
- Before any TTM sum or margin ratio, verify that all quarterly inputs use one currency and one scale. Revenue, operating income, and FCF may not be added or compared across mixed currencies/scales; EPS and current price must use the same per-share currency unit.
- Do not compare GAAP and non-GAAP profit, TTM and fiscal-year totals, basic and diluted EPS, or pre- and post-transaction share counts as if they were the same field.
- Convert FX only with the stated rate and date; do not merge close, regular-session, and after-hours prices.
- For market cap, use a contemporaneous actual price and latest share count. Repurchases, issuance, ADR ratios, and treasury shares may explain a mismatch but must be recorded.
- Historical price comparisons must state adjustment basis. Use a consistent split/dividend-adjusted series for historical returns and valuation bands; do not mix it with unadjusted current snapshots.
- Filing fundamentals (market cap, shares, revenue, net income, EPS, FCF/share, cash, debt) require Tier 1 validation. Current market price and government yield may use declared Tier 2 only with a second independent allowed source, both values, a boolean reconciliation field, and a non-empty explanation. Blogs, forums, and social posts are not allowed sources.
- Tier 2 independence is evaluated by normalized allowlisted vendor domain, so different URLs or subdomains of the same vendor are not independent. The script does not implement a general public-suffix registry; only configured evidence hosts are accepted.
- Automation may calculate, extract, and flag. It validates declared source structure but cannot prove real-world provenance; a human must retrieve sources, confirm issuer domains, judge accounting equivalence, resolve conflicts, and decide freshness.

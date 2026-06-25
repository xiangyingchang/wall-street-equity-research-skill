# Report Contract

## Default Inputs

If the user says "按默认", state this near the top:

```markdown
> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；机会成本=对应计价货币 10Y 国债 x2 + 相关高质量替代资产。
```

Adjust the benchmark by currency and asset class:

- USD assets: US 10Y Treasury x2, Nasdaq 100, S&P 500, Alphabet, Microsoft, NVIDIA, or other relevant US alternatives.
- RMB/HKD China assets: China 10Y government bond x2, CNOOC, Shenhua, CMB, broad China equity alternatives.

## Output Mode Defaults

In the user's Obsidian stock vault, these phrases imply a full report saved as Markdown:

- "跑一下 + 股票名/代码"
- "分析下 + 股票名/代码"
- "看看 + 股票名/代码"
- a bare ticker/company request that clearly refers to a stock

Only use a chat-only quick take when the user explicitly asks for "快评", "简单说下", "不用建文档", "先别写文件", or equivalent.

The saved report must include frontmatter, a default-input statement, First-Page Verdict, Evidence Ledger, 11 fixed modules, final verdict, and source links.

## First-Page Verdict

Start full reports in this order:

1. First-Page Verdict
2. Evidence Ledger
3. 11 fixed modules

The verdict table must include:

| Item | Required judgment |
|---|---|
| Final rating | Buy / Hold-Index / Watchlist / Avoid |
| Current action | Buy / Hold / Reduce / Sell / Wait |
| Core reason | One sentence |
| Worth buying again at today's price | Yes / No / Unclear |
| Beats opportunity cost | Yes / No / Unclear |
| 10-year payback test | Pass / Fail / Super-compounder exception only |
| Safe buy zone | Target multiple and implied price |
| Biggest risk | One sentence |
| Confidence | High / Medium / Low |
| Needs manual verification | 1-3 most important items |

## Evidence Ledger

Include, when relevant:

- Current price, market cap, EV
- Net debt, cash, debt, interest coverage
- Revenue, net income, EPS, OCF, capex, FCF
- EPS/share and FCF/share using TTM, forward, or normalized口径
- PE, forward PE, EV/EBITDA, FCF yield, PB, dividend yield
- Dividend DPS, total dividends, buybacks, SBC, share count trend
- Segment revenue/profit, key operating metrics
- Liquidity and average trading value
- 2-3 direct competitor valuation references
- Relevant 10Y government bond yield and opportunity-cost benchmark

Each row should include value, date, source/tier,口径, and confidence.

For A-share reports, the Evidence Ledger should be seeded from `scripts/a_share_prefetch.py` when possible. Use `summary` first, `peer_comparison` second, and raw `financials` only for drill-down. Do not blindly paste the JSON: convert it into the report table, keep Tier 1/Tier 2 labels explicit, and preserve `summary.manual_verification_notes`.

For US, HK, and other non-A-share reports, complete and disclose this preflight before the verdict:

- Latest company IR earnings release and any earnings deck/prepared-remarks PDF.
- Latest regulator filing: SEC 10-K/10-Q/8-K/20-F/6-K, HKEX annual/interim/announcement, or local equivalent.
- Filing gap: state when the press release is newer than the latest 10-Q/annual filing.
- Current close/latest regular-session price; add after-hours/pre-market price separately when material.
- Relevant 10Y government bond yield and opportunity-cost benchmark.
- Peer valuation set and any source conflicts.

If a source is a PDF, extract text with `scripts/pdf_text_extract.py <pdf_or_url>` when possible. If extraction fails, record the tool/dependency failure and cap confidence for any management-commentary claim based only on headlines or snippets.

If `summary.business_model_flags.equity_method_holding_company` is true:

- State that consolidated FCF is structurally less useful and should be deweighted.
- Do not ignore FCF; use it as a cash pass-through warning rather than a simple operating-quality verdict.
- Emphasize EPS, dividend payout, investment-income durability, major investee quality, ownership percentages, and dividend pass-through.
- Cap the rating at Watchlist unless Tier 1 filings have been checked for major investees and cash-distribution mechanics.

## Rating Caps

- Missing latest annual report: do not rate Buy.
- Missing latest quarterly/interim report: maximum Watchlist.
- Missing EPS or FCF/share: do not rate Buy.
- Missing current price or valuation multiples: do not rate Buy.
- Missing debt/cash data: maximum Watchlist.
- Missing liquidity data: do not recommend more than 5% portfolio weight.
- Only Tier 2/3 data and no filing spot-check: confidence maximum Medium.
- Conflicting data with unresolved source quality: show the conflict and use the conservative口径.

## 10-Year Payback

Use the payback model as a pressure test, not a full DCF.

Forward PE:

```text
M = sum_{t=0}^{9}(1+g)^t = ((1+g)^10 - 1) / g
```

TTM PE:

```text
M = sum_{t=1}^{10}(1+g)^t
```

Run EPS and FCF/share where possible. For cyclical companies, add normalized mid-cycle earnings and do not rely on peak-cycle PE.

For cyclical or capex-heavy companies, the valuation section must include a dual-base table:

- Peak/current-cycle EPS and FCF multiples.
- Normalized mid-cycle EPS and FCF multiples.
- EV/FCF, especially when capex is structurally high.
- A verdict sentence naming which earnings base drives the rating.

Default to this stricter treatment for memory, semiconductors, energy, shipping, commodities, banks, insurers, brokers, real estate, autos, airlines, and hardware supply-chain companies.

Before the final verdict, explicitly answer:

1. If holding equals buying today, would you buy at the current price?
2. Since sunk cost is not cost and opportunity cost is the real cost, does it beat the relevant alternative?
3. Is the required 10-year growth physically plausible, especially under r=8%?

The discounted 10-year payback test must always include four explicit rows:

| Discount rate | Purpose |
|---|---|
| Relevant 10Y government bond yield ×1 | Risk-free baseline |
| Relevant 10Y government bond yield ×2 | Opportunity-cost hard hurdle |
| 8% | Normal equity-cost hurdle |
| 10% | High-risk equity hurdle |

Do not replace the four-row test with only `r=8%` / `r=9%`, even when `10Y×2` is close to 9%.

Use a dedicated heading such as `### 三原则扣问`. These answers must appear in the final verdict section, not only in the First-Page Verdict table.

Buy should require all three to pass. If not, use Hold-Index, Watchlist, or Avoid unless a clearly justified super-compounder exception applies.

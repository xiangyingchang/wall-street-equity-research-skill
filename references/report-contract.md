# Report Contract

## Default Inputs

If the user says "按默认", state this near the top:

```markdown
> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；机会成本=对应计价货币 10Y 国债 x2 + 相关高质量替代资产。
```

Adjust the benchmark by currency and asset class:

- USD assets: US 10Y Treasury x2, Nasdaq 100, S&P 500, Alphabet, Microsoft, NVIDIA, or other relevant US alternatives.
- RMB/HKD China assets: China 10Y government bond x2, CNOOC, Shenhua, CMB, broad China equity alternatives.

The tax identity and opportunity-cost benchmark are not optional flavor text: `report_lint.py` blocks any report that omits the tax identity, and blocks any valuation report that names no opportunity-cost benchmark. See Semantic Lint Gates below.

## Output Mode Defaults

In the user's Obsidian stock vault, these phrases imply a full report saved as Markdown:

- "跑一下 + 股票名/代码"
- "分析下 + 股票名/代码"
- "看看 + 股票名/代码"
- a bare ticker/company request that clearly refers to a stock

Only use a chat-only quick take when the user explicitly asks for "快评", "简单说下", "不用建文档", "先别写文件", or equivalent.

The saved report must not include visible YAML frontmatter. It must include default input, First-Page Verdict, Evidence Ledger, Key Forces, Variant View, Pre-Mortem, one Action Matrix, 10 fixed modules plus pre-module sections, final verdict, and source links.

Read `references/data-validation.md` before populating the Evidence Ledger. Automation may calculate and flag, but it must not fetch or silently resolve evidence conflicts.

Metadata such as ticker, company, market, date, verdict, and action belongs in the filename, title, Evidence Ledger, or internal workflow notes. Do not expose YAML frontmatter in the final report body.

For new reports, start from `templates/full-report.md` or generate a skeleton with `scripts/new_report.py`. Hand-written skeletons are not acceptable for full Obsidian reports. The generator runs recognition automatically and fails closed. For a manually created or copied canonical skeleton, immediately run `python3 scripts/report_audit.py recognize --report <report.md>`. Placeholder values are valid, but every mandatory decision field label must be recognized without ambiguity. Both paths must rerun recognition before extraction.

## Durable Research Pack

For a resumable or multi-session full report, initialize `research-pack-v1` with `scripts/new_report.py --research-pack [path]` or `scripts/research_pack.py init`. Initialization records absolute report continuity paths and refuses report/pack symlinks. `new_report.py` validates arguments and pack conflicts before touching an existing report, stages report and pack outputs, and rolls back both sides on failure; without a pack it prints only the historical report-path line. Follow `references/research-pack-v1.md` for the strict source, fact, checkpoint, and valuation-basis contracts.

The pack is a durable recovery checkpoint. It may preserve canonical inputs and detect stale downstream stages, but it does not fetch or validate real-world evidence and does not replace the report, lint, recognition, or audit verdict. Every downstream stage and valuation revision requires all upstream checkpoints through `facts_ready` to remain current by recomputed hash; a stale valuation lock may be replaced only after upstream recovery. Strict schema validation rejects duplicate JSON keys, unknown defined keys, non-finite JSON, malformed types, missing or cyclic fact/derived/source references, detached TTM fiscal dates (including shifted Q4 or annual FY anchors), invalid unit algebra/rounding/bindings, nonempty deferred `evidence_gates`, and recursive case-insensitive telemetry keys. URL hosts normalize IDNA dot variants and DNS trailing dots before source identity. Every skill-supported pack writer shares an advisory lock across read-modify-write; this prevents lost updates among cooperative writers but cannot protect against unrelated processes that bypass the lock.

## First-Page Verdict

Start full reports in this order:

1. First-Page Verdict (pre-module section)
2. Evidence Ledger (pre-module section)
3. 10 fixed modules

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
| Needs manual verification | 1-3 most important items |

Immediately below this table, add one compact `### Researchability Record`, including First-page Confidence. Follow `references/researchability.md` exactly; do not add a second generic report-confidence label. The final verdict only confirms the distinction, without repeating the record.

## Key Forces

Inside `## 1. 华尔街式全景扫描 Overview`, include a dedicated subsection named `### Key Forces` before the general business overview. Do not create an extra top-level `## Key Forces` section that interrupts the 10-module structure.

Rules:

- Identify 1-3 variables that will decide intrinsic value over the next 3-5 years.
- Give extra depth to modules connected to these variables; do not spread attention evenly when the value driver is concentrated.
- For latest-earnings updates only, add two bullets: `本次财报改变了什么` and `本次财报没有改变什么`. For ordinary full stock reports, do not force these bullets; use `Key Forces` to explain the core business model, value driver, and 1-3 variables that decide intrinsic value.

## Evidence Ledger

Include, when relevant:

- Current price, market cap, EV
- Net debt, cash, debt, interest coverage
- Revenue, net income, EPS, OCF, capex, FCF
- EPS/share and FCF/share using TTM, forward, or normalized口径
- PE, forward PE, EV/EBITDA, FCF yield, PB, dividend yield
- Dividend DPS, total dividends, buybacks, SBC, share count trend
- Segment revenue/profit, key operating metrics
- Liquidity and average trading value only when liquidity is a real constraint; for large liquid names, do not create a standalone liquidity module.
- 2-3 direct competitor valuation references
- Relevant 10Y government bond yield and opportunity-cost benchmark

Each row should include value, date, source/tier,口径, and confidence.

For calculated fields, add an input/output check: market cap (price x shares), valuation multiple (price / per-share metric), FCF/share, and any scenario target. Run `scripts/financial_rigor.py` where applicable. Record `consistent` at <=1%; reconcile and explain >1%-5%; block values >5% until Tier 1 verification. After lint, rerun recognition. Reports without a research pack use Audit v4 `extract --results-out` and `verdict --results`; v4 paths must be distinct and output files are an atomic pair. Its legacy numeric parser is frozen, so `/share` support is v5-only. Reports with strict bound derived records and current checkpoints through `draft_ready` use Audit v5 `extract --pack` and `verdict --pack`. V5 inputs use `fact_ref`/acyclic `derived_ref`; only payback years may be literal. Fiscal-date plausibility and unit algebra are validated before exact cells. V5 rejects `--results`, duplicate JSON keys, path collisions, symlink inputs, forged snapshot values or Python types, and cooperative concurrent pack changes. Verdict holds the shared pack lock from its in-lock snapshot comparison through commit. A failed verdict leaves artifacts unchanged; PASS atomically writes the manifest-bound `audit_passed` pack, and identical reruns remain PASS without byte changes. Both modes are offline, and legacy v4 manifest bytes and decisions remain compatible.

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

## Variant View, Pre-Mortem, and Action Matrix

Every full report must include these dedicated headings:

- `### Variant View`: state market consensus, the report's different view, and why the market may be wrong.
- `### Pre-Mortem`: if the investment fails, name the most likely failure path and the earliest observable warning signal.
- `### Action Matrix`: include exactly one table in module 9 with the exact columns `Action | Trigger type | Executable condition | Position/execution`. It must cover Buy, Add, Hold, Reduce, Sell and price, valuation, operating, thesis-break trigger types. Honest N/A is allowed only for Buy or Add; non-N/A executable rows must still cover every trigger type and at least Hold, Reduce, and Sell.
When a research pack is present and its `action_matrix` is non-empty, Audit v5 cross-checks that the report's module 9 table is in structural correspondence with the pack entries: the same action set and trigger-type set, with no missing or extra actions. Each pack `action_matrix` entry must declare exactly `action`, `trigger_type`, `condition`, `execution`, and `na` (true only for Buy or Add).

All executable conditional trades and thresholds belong only in this matrix. First-Page Verdict and Final Verdict may state the current action and summarize price ranges, but must not define a conditional trade. The legacy `Action Triggers` heading is not allowed.

## Semantic Lint Gates

`scripts/report_lint.py` enforces three semantic gates in addition to its structural checks:

- **Tax identity**: the report must declare a tax identity context (for example `税务身份=中国大陆个人`, a US-listed investor, or an HK-listed investor) so tax friction is not silently omitted. An explicit `N/A` is allowed only with a stated reason. This prevents reports that omit tax considerations entirely.
- **Opportunity-cost benchmark**: whenever the report mentions valuation, it must reference an opportunity-cost benchmark (a 10Y government bond yield, an index return, or an explicit alternative asset). The contract already requires an opportunity-cost pass for Buy ratings in module 10; this gate extends the benchmark requirement to every rating, so a non-Buy report cannot lean on valuation language while naming no benchmark.
- **Previous-report delta**: when the pack's `previous_report` is set or the report text references a prior report, the report must contain a delta/comparison covering at least the rating change (or an explicit "unchanged"), a key metric change, and the thesis change (or an explicit "unchanged"). This stops reruns from silently dropping the comparison against the prior report.

## Variant View Boundary

Do not add a four-lens section or roleplay quotes. Only list unresolved material disagreements in `### Variant View` or Final Verdict, capped at four bullets; otherwise synthesize the conclusion normally. The authoritative lens-to-module mapping is in `references/full-methodology.md`.

---
name: wall-street-equity-research
description: Wall Street style equity research and stock due diligence for A-share, Hong Kong, US, and other listed equities. Use when the user asks to analyze a stock, "跑一下" a stock, judge whether a ticker is worth buying or holding, run a "华尔街分析", "脱水质检", "10年回本测试", "估值审判", "该不该买", "值不值", or compare a single equity against opportunity cost. In the user's Obsidian stock vault, "跑一下 + 股票名/代码" means a full template-faithful Markdown report saved under the stock/company folder unless the user explicitly asks for a quick take. Do not use for broad portfolio allocation, pure macro views, non-stock product research, or 横纵分析法.
---

# Wall Street Equity Research

Run a ruthless but evidence-bound single-stock investment review. The output must help the user decide whether to buy, hold, reduce, sell, or wait.

## Core Rules

- Treat "持有 = 买入", opportunity cost, and the 10-year payback test as the highest-priority investment disciplines.
- Never invent current prices, valuation multiples, financials, filing facts, or bond yields from memory. Use current sources when the answer depends on live or recent data.
- Prefer Tier 1 sources: SEC EDGAR, company IR, exchange filings, HKEXNews, 巨潮资讯, and official announcements. Use Tier 2 data vendors only for speed and cross-checking. Treat media and search snippets as leads, not proof.
- If key data is missing or only second-hand, downgrade confidence and cap the rating according to `references/report-contract.md`.
- Be candid. A famous company at a bad price is still a bad buy.

## Workflow

1. Identify the ticker, market, tax identity, holding period, opportunity-cost benchmark, current holding state, and intended or existing position size.
2. If the user does not specify inputs, ask once. If they ask to use defaults, state the defaults explicitly in the report.
3. Gather the latest available filings and market data before writing conclusions.
4. Build an Evidence Ledger with value, date, source tier, accounting/market口径, and confidence.
5. For A-share reports, run `scripts/a_share_prefetch.py <code> --peers <peer codes...>` before drafting when network access is available. Start from `summary` for the flattened quote/rates/TTM/dividend/valuation fields, use `peer_comparison` for the peer table, preserve `summary.manual_verification_notes`, and only drill into raw `financials` or `announcements` when needed. If it fails, state the failure and fall back to manual source collection.
6. For US, HK, and other non-A-share reports, run a manual preflight checklist before drafting: company IR latest earnings release/deck, regulator filing (SEC 10-K/10-Q/8-K/20-F/6-K or HKEX annual/interim/announcement), current close/latest/after-hours or market-session price, relevant 10Y government yield, peer valuations, and any missing-filing gap. If an earnings PDF/deck is used, extract text with `scripts/pdf_text_extract.py <pdf_or_url>` or explicitly record why extraction failed.
7. Separate market prices when they materially differ: close price, latest regular-session price, pre-market/after-hours price, and FX date/rate. Do not mix them in valuation tables; show both valuation outcomes when the difference can change the verdict.
8. For cyclical or capex-heavy companies, force a dual valuation table: peak/current-cycle EPS and FCF, normalized mid-cycle EPS and FCF, EV/FCF, and a short statement explaining which earnings base drives the final verdict. Memory, semiconductors, energy, shipping, commodities, banks, insurers, brokers, real estate, autos, airlines, and hardware supply-chain names default to this rule.
9. If the current working context is the user's Obsidian stock vault or prior reports exist under `股票/`, treat "跑一下", "分析下", "看看", or a ticker/company name request as a full report request. Read `references/source-map.md`, inspect 1-2 prior reports for style continuity, run the 11-module review in `references/full-methodology.md`, and save the Markdown report under `股票/<公司名>/`.
10. Use the compact contract in `references/report-contract.md` only when the user explicitly asks for "快评", "简单说下", "不用建文档", or the task is clearly outside the Obsidian report workflow.
11. When saving an Obsidian report, include frontmatter, default-input statement, First-Page Verdict, Evidence Ledger, the 11 fixed modules, final verdict, source links, and file path confirmation. If the prefetch JSON flags `equity_method_holding_company`, explicitly deweight consolidated FCF in the verdict and analyze EPS, dividends, investment-income durability, and underlying investee quality.

## Required Sources

- `references/report-contract.md`: read for every task using this skill.
- `references/source-map.md`: read when locating the user's Obsidian authority docs or prior reports.
- `references/full-methodology.md`: read for full deep reports, template-faithful reports, or when the user explicitly asks for "完整", "11模块", "脱水质检", or "华尔街模板".

## Helper Scripts

- `scripts/a_share_prefetch.py`: A-share preflight data collector. It handles SSE announcement lookup for Shanghai-listed companies, Tencent GBK quote decoding, Eastmoney gzip financial tables, dividend records, TTM/FCF derivation, approximate EV/FCF, peer comparison, equity-method holding-company flags, ChinaBond 10Y government bond yield caching, and 10-year payback math. Shenzhen-listed companies still need separate CNINFO filing-link collection.
- `scripts/pdf_text_extract.py`: earnings PDF/deck text extractor. It accepts a local PDF path or HTTP(S) URL, tries `pypdf` first and `pdfplumber` second, and prints extracted text plus dependency/failure notes. Use it for prepared remarks, earnings decks, HKEX PDFs, and annual-report PDFs when HTML/XBRL is not enough.

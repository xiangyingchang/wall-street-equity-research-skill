# Source Map

This skill was distilled from the user's Obsidian stock research method and prior reports.

## Authority Docs

- `/Users/muskxiang/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/股票/_方法论/股票脱水质检Prompt-优化版.md`
- `/Users/muskxiang/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/股票/_方法论/2026 资产配置备忘录 (V4).md`

The first file is the current authority for the stock due-diligence prompt. The second file is now a historical allocation memo; use only its durable disciplines, not its holdings, allocation percentages, or dated execution TODOs.

## Obsidian Stock Vault Default

When `cwd` is `/Users/muskxiang/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian` and the user says "跑一下 + 股票名/代码", the default output is a full Obsidian Markdown report, not a chat-only quick take.

Use this rule unless the user explicitly says "快评", "简单说下", "不用建文档", "先别写文件", or equivalent.

Default save path:

```text
股票/<公司名>/<TICKER>-<公司名>-华尔街式分析报告-YYYY-MM-DD.md
```

For dual-listed companies, prefer the user-requested market in the filename. Add the other listing inside Evidence Ledger and opportunity-cost comparison when it affects valuation.

## Prior Report Locations

Search these folders for examples and continuity:

- `/Users/muskxiang/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/股票`
- `/Users/muskxiang/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/股票/_报告`
- `/Users/muskxiang/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/股票/_汇总`

Useful search patterns:

```bash
rg -n "First-Page Verdict|Evidence Ledger|10 年回本|持有 = 买入|最终评级|安全买入区间" 股票 -S
find 股票 -maxdepth 3 -type f -iname '*华尔街式分析报告*' -print
```

Before writing a new report, inspect at least one recent comparable report for style and structure, such as a Hong Kong dividend/China asset report for HK stocks or a US tech report for US stocks. Do not copy wording; copy the artifact contract.

## A-Share Data Preflight

For A-share reports, run the helper first when network access is available:

```bash
python3 /Users/muskxiang/.agents/skills/wall-street-equity-research/scripts/a_share_prefetch.py 600900 --peers 600905 600025 600886 600674 600795 601985
```

Use the JSON output to seed:

- SSE announcement links for Shanghai-listed companies' annual, quarterly, dividend, and shareholder-return-plan filings.
- Tencent quote fields decoded with GBK, including price, PE, PB, market cap, shares, volume, and peer valuations.
- Eastmoney financial tables, including annual/quarterly metrics, balance sheet, income statement, cash flow, and dividends.
- ChinaBond 10Y government bond yield, cached locally for 30 days by default.
- Derived TTM revenue, net profit, EPS, OCF, capex, FCF, FCF/share, P/FCF, EV/FCF, and 10-year payback math.

Known limitations:

- China 10Y yield is fetched from ChinaBond and cached at `~/.cache/wall-street-equity-research/china_10y_yield.json`. Use `--refresh-china-10y` to force refresh, or `--china-10y-cache-days N` to change the freshness window. If the source fails and only stale cache is available, mark the rate as stale in the report.
- Shenzhen-listed companies currently need separate CNINFO filing links. The script still fetches Tencent quotes, Eastmoney financial tables, and dividend records for SZ tickers.

## Existing Legacy Skill

The previous generated skill lives at:

- `/Users/muskxiang/.workbuddy/skills/wall-street-equity-research/SKILL.md`

Treat it as a legacy bundled copy of the method, not the active installed skill.

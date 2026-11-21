# Source Map

This skill was distilled from the user's Obsidian stock research method and prior reports.

## 报告与历史基线

默认交付和历史报告检索均从 Notion 投研报告库开始。见 [Notion 交付](notion-delivery.md)。新一期使用同一标的和市场的最新可取得基线，注明日期、来源和缺项。双重上市时优先用户指定的市场，另一柜台在影响估值时列入对照。

## A-Share Data Preflight

For A-share reports, run the helper first when network access is available:

```bash
python3 /Users/haoshifasheng/.codex/skills/wall-street-equity-research/scripts/a_share_prefetch.py 600900 --peers 600905 600025 600886 600674 600795 601985
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

## Active Installed Skill

The active installed copy lives at:

- `/Users/haoshifasheng/.codex/skills/wall-street-equity-research/SKILL.md`

The Git repository remains the editing authority; sync the installed copy only after tests pass.

---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 脱水质检, 10年回本测试, 估值审判, 值不值, or 该不该买. Produce evidence-bound single-stock research."
license: MIT
metadata:
  author: xiangyingchang
  version: "1.1.0"
---

## Activation Contract

Use for one listed equity when the user asks for valuation, buy/hold/sell judgment, a full stock report, or the trigger phrases above. In the Obsidian stock vault, a ticker or 跑一下/分析下 means a full saved report unless the user asks for a quick take. Do not use for portfolio allocation, macro, products, or 横纵分析法.

## Hard Rules

- Never invent live prices, filings, yields, or valuation data; Tier 1 evidence decides conflicts.
- Use `templates/full-report.md`; reports have pre-module sections plus 10 fixed modules, never visible YAML frontmatter.
- Keep earnings deltas only for `报告类型=最新财报更新`; ordinary reports do not require them.
- Include Key Forces, Variant View, Pre-Mortem, Action Triggers, four discount rows, and final 三原则扣问.
- Apply calculated-value checks and the manual audit; do not let automation fetch or resolve provenance.

## Decision Gates

| Condition | Required action |
|---|---|
| Full report | Read every reference below, use the template, and save under `股票/<公司名>/`. |
| A-share | Run `scripts/a_share_prefetch.py` when network access permits; preserve its manual notes. |
| US/HK/other | Complete IR, filing, current-price, 10Y, peer, and PDF-extraction preflight. |
| Latest earnings update | Add what changed and what did not inside module 1. |
| Missing or conflicting critical evidence | Apply the rating caps in `references/report-contract.md`. |

## Execution Steps

1. Collect ticker, market, tax identity, horizon, opportunity cost, holding state, and size; state defaults when used.
2. Build the Evidence Ledger with date, tier, basis, unit, and calculated input/output checks. Apply `scripts/financial_rigor.py` thresholds.
3. Add the compact Researchability Record under First-Page Verdict and follow `references/researchability.md`.
4. Run the 10 modules using `references/full-methodology.md`; use its four-lens mapping without roleplay or a new section.
5. Lint, then run `report_audit extract --manifest-out ... --results-out ...`; fill the generated template and run the complete `python3 scripts/report_audit.py verdict --report ... --manifest ... --results ...` command.

## Output Contract

Return the report path, final rating/action, key uncertainty, and verification result. A full report is incomplete unless lint and audit verdict both pass.

## References

- `references/report-contract.md` — full-report contract and rating caps.
- `references/data-validation.md` — sources, provenance, discrepancy, and executable audit workflow.
- `references/researchability.md` — authoritative A/B/C and confidence rules.
- `references/full-methodology.md` — 10-module method and four-lens mapping.
- `references/source-map.md` — Obsidian locations and prior-report continuity.
- `templates/full-report.md` — required report skeleton.

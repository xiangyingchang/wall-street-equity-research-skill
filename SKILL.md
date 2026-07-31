---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 脱水质检, 10年回本测试, 估值审判, 值不值, or 该不该买. Produce evidence-bound single-stock research."
license: MIT
metadata:
  author: xiangyingchang
  version: "1.3.0"
---

## Activation Contract

Use for one listed equity when the user asks for valuation, buy/hold/sell judgment, a full stock report, or the trigger phrases above. In the Obsidian stock vault, a ticker or 跑一下/分析下 means a full saved report unless the user asks for a quick take. Do not use for portfolio allocation, macro, products, or 横纵分析法.

## Hard Rules

- Never invent live prices, filings, yields, or valuation data; Tier 1 evidence decides conflicts.
- Use `templates/full-report.md`; reports have pre-module sections plus 9 fixed modules, never visible YAML frontmatter.
- Keep earnings deltas only for `报告类型=最新财报更新`; ordinary reports do not require them.
- Include Key Forces, Variant View, Pre-Mortem, one module 8 Action Matrix, four discount rows, and final 三原则扣问.
- Keep every executable conditional trade and threshold only in the Action Matrix; First-Page and Final Verdict may state the current action or summarize ranges without defining another trade rule.
- Apply calculated-value checks and the manual audit; do not let automation fetch or resolve provenance.
- Treat `research-pack-v1` as durable recovery state only; never add provider, model, token, timing, retry, or runtime telemetry.
- **Network-effects moat = user metrics required.**
- **Analysis density gates (lint-enforced):** Module 3 must include a 5+ row moat score table (dimension/score/evidence). Module 4 must include a multi-scenario valuation gate (3+ rows: peak/mid-cycle/normalized) for high-capex (≥$50B) or cyclical companies. Report must include a peer comparison table (2+ competitors, 2+ metrics) or state "无直接可比竞品". Variant View must be in module 9 only. Module 8 must include a price-zone summary table (at least 2 of safe-margin/observation/overvalued tiers). Module 8 or 9 must include a quantified target PE / target price. Absolute money amounts must use "亿" with original currency; per-share/multiple/ratio/KRW exempt. Network-effect claims require multi-period user metrics and a dedicated table.
- **Valuation consistency is mandatory:** every valuation basis must have a Basis ID; adjusted/normalized metrics require an Adjustment Ledger; Scenario Valuation must separate fair value, buy price, and stress price. The 10-year payback is a pressure test, not a sole veto. Follow `references/valuation-consistency.md`.
- **Valuation runtime is authoritative:** 5-year IRR, Reverse Expectations, and current Action Matrix resolution must come from `scripts/valuation_runtime.py`; the report may not hand-write a conflicting number or claim an untriggered action. Follow `references/valuation-runtime.md`.
- **Normalized EPS requires a full bridge:** Revenue → operating margin → operating income → pre-tax income → tax → net income → diluted shares → EPS. A scenario label or margin-only assertion is not a bridge.
- **No buyback double count:** when scenario growth is EPS CAGR, do not add a separate buyback/share-count yield to IRR. Model share-count change only from net-income growth mode.
- **Source tiers are fixed:** SEC/issuer IR/exchange are Tier 1; Yahoo Finance and other standardized vendors are Tier 2.
- In pack-backed v5, declare derived inputs by `fact_ref` or `derived_ref`; only payback `years` may be a literal. Never copy caller-supplied values, units, dates, or source IDs into reference inputs.

## Decision Gates

| Condition | Required action |
|---|---|
| Full report | Read every reference below, use the template, and save under `股票/<公司名>/`. |
| A-share | Run `scripts/a_share_prefetch.py` when network access permits; preserve its manual notes. |
| US/HK/other | Complete IR, filing, current-price, 10Y, peer, and PDF-extraction preflight. |
| Latest earnings update | Add what changed and what did not inside module 1. |
| Network-effects moat claim | Evidence Ledger must include multi-period user/engagement metrics; module 3 must contain a user-metrics table with YoY trends. |
| Missing or conflicting critical evidence | Apply the rating caps in `references/report-contract.md`. |
| Valuation report | Build the Basis Registry, Adjustment Ledger, Scenario EPS Bridge, Scenario Valuation, Capex Bridge, runtime IRR, runtime Reverse Expectations, and runtime Action Resolution. |
| Filing gap or approximate TTM/owner earnings | Information Richness ≤ B and AI Research Confidence ≤ Medium until resolved. |
| Resumable or multi-session report | Initialize `research-pack-v1` and resume from its first missing or stale checkpoint. |

## Execution Steps

1. Collect ticker, market, tax identity, horizon, opportunity cost, holding state, and size; state defaults when used.
2. Create the canonical skeleton. `scripts/new_report.py` runs recognition automatically and fails closed; add `--research-pack [path]` for a durable recovery pack. For a manually created or copied skeleton, immediately run `python3 scripts/report_audit.py recognize --report <report.md>`.
3. Build the Evidence Ledger with atomic field labels, date, tier, basis, unit, and calculated input/output checks. Apply `scripts/financial_rigor.py` thresholds.
4. Add the compact Researchability Record and follow `references/researchability.md` plus the filing-gap caps in `references/valuation-runtime.md`.
5. Run the 9 modules using `references/full-methodology.md`.
6. Before writing the verdict, run `scripts/valuation_runtime.py` for every Scenario IRR row and Reverse Expectations row. Build an explicit JSON evaluation of Action Matrix current truth values and run `resolve-action`. Copy the runtime outputs exactly into the report.
7. Run `python3 scripts/valuation_consistency.py <report.md>` and resolve every ERROR. Then lint and rerun `report_audit.py recognize`. Complete v4 or v5 audit as applicable.

## Output Contract

Return the report path, final rating/action, key uncertainty, runtime verification result, valuation consistency result, lint result, and audit result. A full report is incomplete unless runtime action matches the reported action and all validation stages pass.

## References

- `references/report-contract.md` — full-report contract and rating caps.
- `references/data-validation.md` — sources, provenance, discrepancy, and executable audit workflow.
- `references/research-pack-v1.md` — deterministic recovery pack, checkpoints, and valuation-basis lock.
- `references/researchability.md` — authoritative A/B/C and confidence rules.
- `references/valuation-consistency.md` — valuation basis, adjustment bridge, scenario math, and fair-value boundaries.
- `references/valuation-runtime.md` — deterministic IRR, reverse expectations, normalized EPS bridge, and action resolution.
- `references/full-methodology.md` — 9-module method and four-lens mapping.
- `references/source-map.md` — Obsidian locations and prior-report continuity.
- `templates/full-report.md` - required report skeleton.

## Skill 维护纪律（强制）

任何对本 skill 的行为改动必须按以下顺序执行：

1. **先完善 PRD**：在 `PRD-*.md` 中写明背景、现状、目标、改动范围、不在范围内、验证标准。
2. **记录变更**：改动落地后在 `references/change-log.md` 顶部新增条目。
3. **再执行**：代码、模板、methodology、contract、测试同步更新，跑完整验证套件。

PRD 和 change-log 是仓库的一等公民，与代码同等重要，必须 commit 到仓库。

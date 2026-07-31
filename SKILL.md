---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 脱水质检, 10年回本测试, 估值审判, 值不值, or 该不该买. Produce evidence-bound single-stock research."
license: MIT
metadata:
  author: xiangyingchang
  version: "1.2.0"
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
- **Analysis density gates (lint-enforced):** Module 3 must include a 5+ row moat score table (dimension/score/evidence). Module 4 must include a multi-scenario valuation gate (3+ rows: peak/mid-cycle/normalized) for high-capex (≥$50B) or cyclical companies. Report must include a peer comparison table (2+ competitors, 2+ metrics) or state "无直接可比竞品". Variant View must be in module 9 only. Module 8 must include a price-zone summary table (at least 2 of safe-margin/observation/overvalued tiers). Module 8 or 9 must include a quantified target PE / target price (keyword + numeric value); pure qualitative wording does not satisfy. Absolute money amounts must use "亿" with original currency (e.g. $1,300亿 not $130B), no cross-currency conversion; per-share/multiple/ratio/KRW exempt. If the moat analysis claims network effects (社交网络、双边平台、用户飞轮), the Evidence Ledger must include at minimum multi-period DAU/MAU/DAP or equivalent engagement data with YoY trends, and module 3 must contain a dedicated user-metrics table that supports the claim. Common sources: company IR operating metrics, SEC 10-K/10-Q business section, earnings slides. Never substitute qualitative descriptions ("全球最大社交平台") for quantified user evidence.
- **Valuation consistency is mandatory:** every valuation basis must have a Basis ID; adjusted/normalized metrics require an Adjustment Ledger; Scenario Valuation must separate fair value, buy price, and stress price. The 10-year payback is a pressure test, not a sole veto. Follow `references/valuation-consistency.md`.
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
| Valuation report | Build the Basis Registry, Adjustment Ledger, Scenario Valuation, and Capex Bridge; run `valuation_consistency.py` before lint/audit. |
| Resumable or multi-session report | Initialize `research-pack-v1` and resume from its first missing or stale checkpoint. |

## Execution Steps

1. Collect ticker, market, tax identity, horizon, opportunity cost, holding state, and size; state defaults when used.
2. Create the canonical skeleton. `scripts/new_report.py` runs recognition automatically and fails closed; add `--research-pack [path]` for a durable recovery pack. For a manually created or copied skeleton, immediately run `python3 scripts/report_audit.py recognize --report <report.md>`. Fix missing, ambiguous, or unrecognized mandatory labels before populating values.
3. Build the Evidence Ledger with atomic field labels, date, tier, basis, unit, and calculated input/output checks. If the company relies on network effects, add at minimum three-period DAU/MAU/DAP or equivalent engagement metrics with YoY trends. Apply `scripts/financial_rigor.py` thresholds.
4. Add the compact Researchability Record under First-Page Verdict and follow `references/researchability.md`.
5. Run the 9 modules using `references/full-methodology.md`; use its four-lens mapping without roleplay or a new section.
6. Run `python3 scripts/valuation_consistency.py <report.md>` and resolve every ERROR. Then lint and rerun `report_audit.py recognize`. Without a research pack, use the unchanged v4 `extract --results-out ...` and `verdict --results ...` workflow. With a current pack containing bound derived records, use v5 `extract --pack ... --manifest-out ...` and `verdict --pack ... --manifest ...`; v5 resolves reference inputs from the pack snapshot, rejects symlinked artifacts, never accepts a results file, and only a successful verdict may write `audit_passed`.

## Output Contract

Return the report path, final rating/action, key uncertainty, and verification result. A full report is incomplete unless lint and audit verdict both pass.

## References

- `references/report-contract.md` — full-report contract and rating caps.
- `references/data-validation.md` — sources, provenance, discrepancy, and executable audit workflow.
- `references/research-pack-v1.md` — deterministic recovery pack, checkpoints, and valuation-basis lock.
- `references/researchability.md` — authoritative A/B/C and confidence rules.
- `references/valuation-consistency.md` — valuation basis, adjustment bridge, scenario math, and fair-value boundaries.
- `references/full-methodology.md` — 9-module method and four-lens mapping.
- `references/source-map.md` — Obsidian locations and prior-report continuity.
- `templates/full-report.md` - required report skeleton.

## Skill 维护纪律（强制）

任何对本 skill 的行为改动（新增/修改 lint gate、调整模块结构、改变报告契约）必须按以下顺序执行，不得跳步：

1. **先完善 PRD**：在 `PRD-*.md` 中写明背景、现状、目标、改动范围、不在范围内、验证标准。无 PRD 不得改代码。
2. **记录变更**：改动落地后在 `references/change-log.md` 顶部新增条目，写明 Change / Reason / Scope boundary / Verification。
3. **再执行**：代码、模板、methodology、contract、测试同步更新，跑完整验证套件（py_compile + unittest + self-test + fixtures + diff --check）。

PRD 和 change-log 是仓库的一等公民，与代码同等重要，必须 commit 到仓库。

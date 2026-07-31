---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 脱水质检, 10年回本测试, 估值审判, 值不值, or 该不该买. Produce evidence-bound single-stock research."
license: MIT
metadata:
  author: xiangyingchang
  version: "1.5.0"
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
- **Analysis density gates:** Module 3 requires a 5+ row moat score table. Module 4 requires multi-scenario valuation for high-capex or cyclical companies. Include peer comparison, Variant View in module 9, price-zone summary, quantified target price, and standardized original-currency `亿` units.
- **Valuation consistency is mandatory:** every valuation basis has a Basis ID; Scenario Valuation separates forward reference value, target-return price, safety-margin buy price, and stress price. The 10-year payback is a pressure test, not a sole veto.
- **Canonical Value Registry is mandatory:** `FACT-*` is externally verifiable, `DERIVED-*` is calculated from registered inputs, and `MODEL-*` is an analytical output. Fair value, target price, buy price, stress price, or IRR may never be labelled `FACT-*`.
- **TTM values are runtime-authoritative:** TTM EPS, revenue, operating income, FCF, and ratios must come from `valuation_runtime.py ttm-derive` using four explicit periods. A prose approximation is not a canonical TTM value.
- **Historical adjustments and forward assumptions are separate:** One-off Adjustment Ledger contains only occurred items. Revenue growth, margin, tax, shares, Capex normalization, exit PE, dividend assumptions, and EPS CAGR belong in Scenario Assumption Registry.
- **Forward Revenue is runtime-authoritative:** each forecast period uses `guide_midpoint`, `yoy`, `qoq`, `explicit`, or `consensus` mode through `valuation_runtime.py revenue-bridge`. Hand-filled outputs with unreconciled growth labels are forbidden.
- **Scenario EPS is runtime-authoritative:** every Bear/Base/Bull Revenue → margin → operating income → pre-tax income → tax → net income → shares → EPS row comes from `valuation_runtime.py eps-bridge`.
- **Returns share one assumption set:** new full reports use `valuation_runtime.py return-pair`; separate `irr` and `reverse` commands are legacy-only. Return Pair must output Scenario IRR, Reverse Expectations, and target-return-consistent current price using the same dividend, years, exit PE, target return, and starting Basis.
- **Action thresholds require policy:** every numeric Action condition references a `THR-*` entry declaring basis, lookback, confirmation, tolerance, minimum confidence, and rationale. Naked numeric thresholds are forbidden.
- **Action truth is runtime-authoritative:** new full reports use `valuation_runtime.py evaluate-action` in `v2-threshold-policy` mode with structured values and thresholds. The Agent may not submit `triggered=true/false`.
- **Neutral bands fail closed:** insufficient confidence, missing confirmation, or values inside threshold tolerance produce `indeterminate`; an indeterminate rule capable of changing the highest-priority action resolves to `REVIEW`.
- **Decision robustness is mandatory:** run `valuation_runtime.py robustness` with at least ±5% shocks on decision-critical values. If the resolved action changes, current action must be `REVIEW` unless an explicit external portfolio constraint independently requires action.
- **No buyback double count:** when scenario growth is EPS CAGR, do not add separate buyback/share-count yield. Model share-count change only from net-income growth mode.
- **Opportunity-cost types are explicit:** actual 10Y yield is an investable risk-free benchmark; `10Y ×2` is a required-return hurdle, not an asset; indices/peers are risky investable alternatives.
- **Capex semantics:** Capex is cash. If the company does not disclose maintenance/growth/AI splits, write Unclear; never rename Total Capex as AI Capex.
- **Point-in-time market cap requires point-in-time shares:** weighted-average diluted shares are an EPS denominator, not a market-cap share count, unless explicitly reconciled and marked as an estimate.
- **Source tiers are fixed:** SEC/issuer IR/exchange are Tier 1; Yahoo Finance and other standardized vendors are Tier 2.
- **Verification is blocking:** TTM runtime, revenue runtime, EPS runtime, Return Pair, Action Evaluation, robustness, both consistency checkers, lint, and audit must all be PASS. TODO / FAIL / 未运行 / Unknown means the report is incomplete.
- In pack-backed v5, declare derived inputs by `fact_ref` or `derived_ref`; only payback `years` may be a literal. Never copy caller-supplied values, units, dates, or source IDs into reference inputs.

## Decision Gates

| Condition | Required action |
|---|---|
| Full report | Read every reference below, use the template, and save under `股票/<公司名>/`. |
| A-share | Run `scripts/a_share_prefetch.py` when network access permits; preserve its manual notes. |
| US/HK/other | Complete IR, filing, current-price, 10Y, peer, and PDF-extraction preflight. |
| Latest earnings update | Add what changed and what did not inside module 1. |
| Network-effects moat claim | Evidence Ledger includes multi-period user/engagement metrics; module 3 contains a user-metrics table with YoY trends. |
| Missing or conflicting critical evidence | Apply rating caps in `references/report-contract.md`. |
| Valuation report | Build Canonical Value Registry, TTM Derivation, historical Adjustment Ledger, Scenario Assumption Registry, Revenue Forecast Runtime, EPS Bridge, Basis Registry, Scenario Valuation, Capex Bridge, Return Pair, Threshold Policy Registry, Action Evaluation v2, and robustness output. |
| Filing gap or approximate owner earnings | Information Richness ≤ B and AI Research Confidence ≤ Medium until resolved. |
| No Action rule triggers, material indeterminacy, or unstable robustness | Current action must be REVIEW. |
| Current price lies inside a buy zone but verdict says no-buy or Reduce/Sell | Resolve the contradiction before delivery; rename the zone or change the action. |
| Resumable or multi-session report | Initialize `research-pack-v1` and resume from its first missing or stale checkpoint. |

## Execution Steps

1. Collect ticker, market, tax identity, horizon, opportunity cost, holding state, and size; state defaults when used.
2. Create the canonical skeleton. `scripts/new_report.py` runs recognition automatically and fails closed; add `--research-pack [path]` for durable recovery. For a manually created or copied skeleton, immediately run `python3 scripts/report_audit.py recognize --report <report.md>`.
3. Build Evidence Ledger and Canonical Value Registry with atomic labels, periods, source tiers, basis/unit, confidence, and Inputs/Formula. Use point-in-time shares for market cap.
4. Run `valuation_runtime.py ttm-derive` for every decision-critical TTM sum or ratio and copy outputs exactly.
5. Add Researchability Record and apply filing-gap caps. Build historical One-off Adjustment Ledger separately from Scenario Assumption Registry.
6. Run `valuation_runtime.py revenue-bridge` for four periods in each scenario. Use those totals as `eps-bridge` revenue inputs; copy EPS Bridge outputs exactly.
7. Register Basis IDs. Separate forward reference value from target-return price, safety-margin buy price, and stress price.
8. Run `valuation_runtime.py return-pair` for Bear/Base/Bull. Copy IRR, Reverse Expectations, target-return price, and shared assumptions exactly.
9. Define every executable threshold in Threshold Policy Registry. Run `evaluate-action` in `v2-threshold-policy` mode, then run `robustness --shock 0.05` or stricter. Unstable results resolve to REVIEW.
10. Run `python3 scripts/valuation_consistency.py <report.md>` and `python3 scripts/input_decision_consistency.py <report.md>`; resolve every ERROR and review every WARNING.
11. Run lint, recognition, and v4/v5 audit as applicable. Replace every Verification placeholder with actual PASS results before delivery.

## Output Contract

Return the report path, final rating/action, key uncertainty, TTM runtime result, Revenue/EPS Bridge result, Return Pair result, fact-based Action Evaluation result, robustness result, both consistency results, lint result, and audit result. A full report is incomplete unless all runtime outputs match the report, the action is stable or REVIEW, and every Verification row is PASS.

## References

- `references/report-contract.md` — full-report contract and rating caps.
- `references/data-validation.md` — sources, provenance, discrepancy, and executable audit workflow.
- `references/research-pack-v1.md` — deterministic recovery pack, checkpoints, and valuation-basis lock.
- `references/researchability.md` — authoritative A/B/C and confidence rules.
- `references/valuation-consistency.md` — valuation basis, scenario math, and fair-value boundaries.
- `references/valuation-runtime.md` — deterministic runtime command contracts.
- `references/input-decision-robustness.md` — v1.5 value kinds, TTM/revenue provenance, threshold policy, semantic consistency, and robustness requirements.
- `references/full-methodology.md` — 9-module method and four-lens mapping.
- `references/source-map.md` — Obsidian locations and prior-report continuity.
- `templates/full-report.md` — required report skeleton.

## Skill 维护纪律（强制）

任何对本 skill 的行为改动必须按以下顺序执行：

1. **先完善 PRD**：在 `PRD-*.md` 中写明背景、现状、目标、改动范围、不在范围内、验证标准。
2. **记录变更**：实施前创建版本变更记录，改动落地并验证后更新为最终结果，再合并进 `references/change-log.md`。
3. **再执行**：代码、模板、methodology/contract、测试同步更新，跑完整验证套件。

PRD 和 change-log 是仓库的一等公民，与代码同等重要，必须 commit 到仓库。

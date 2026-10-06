---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 估值审判, 值不值, or 该不该买. Produce evidence-bound adversarial equity research."
license: MIT
metadata:
  author: xiangyingchang
  version: "3.2.0"
---

## 变更目的约定

所有变更的目的，都是得出更加准确、科学的研究报告，帮助用户理解风险、收益和行动条件，指导实际投资。不要为了完善而完善；始终围绕投资判断保持目标意识。

每项变更先说明要减少哪类研究错误、改善哪项投资判断，再用相应证据或测试验证。不能提高研究准确性、可验证性或决策清晰度的改动，不因增加功能、检查或流程而推进。事实、解释与假设分开；结论不确定时明确说明，不制造确定性。

## Activation Contract

Use for a listed equity when the user requests valuation, a buy/hold/sell judgment, or a full report. In an Obsidian stock vault, a ticker plus 跑一下/分析下 means a complete saved report unless the user asks for a quick take.

## Hard Rules

- Read `references/research-graph-v3.md`, `references/report-spec-v2.md`, and `references/decision-policy-v2.md` before building a report.
- Start from one fresh `report-spec-v3.1` JSON Spec. Never copy an old Markdown report or edit generated files.
- Build and verify only with:

```bash
python3 scripts/report_pipeline_v3.py build --spec <spec.json> --output <report.md>
python3 scripts/report_pipeline_v3.py verify --spec <spec.json> --output <report.md>
```

- Deliver Spec, Reader, Audit, Bundle, and Verification together.
- The Bundle owns every calculation and action. Narrative may explain but never override it.
- Never invent facts, prices, holdings, sources, assumptions, evidence, graph nodes, or arguments. Prefer Tier 1 evidence; Tier 2 market data must be labeled.
- Every Source requires a real HTTPS URL, date, precise locator, scope, and publisher. Generic source placeholders fail build. TTM inputs must share currency, scale, and per-share units where applicable.
- Actual TTM inputs must be four distinct consecutive quarters matching the baseline EPS window and ending by `report.as_of`; non-calendar fiscal quarters require explicit ISO `period_end`. Forecasts cannot be actual TTM.
- Bind final summary, 持有=买入, debate adjudication, and each Theme decision impact with `text_template` and `value_refs` using `format: action` on `/decision/new_money_action`. Bind other action labels to compiled existing-position actions; migrate static action conclusions before building.
- Bind research numbers through JSON Pointer `value_refs`. Keep Sources, Facts, assumptions, policy, research, and Graph in the Spec.
- Quote every per-share price (current, target-return, buy, forward reference, price zones) in the listing-market currency: HK-listed → HKD, US-listed → USD, A-share → CNY. Never use a secondary counter (e.g. HK RMB counter 80700) to avoid FX. When the reporting currency differs, set `report.price_currency` and `report.fx_fact_id`; the FX Fact must have a Tier 1 source (e.g. CFETS central parity) and an as-of date, and only the compiler converts EPS. Absolute money stays in the reporting currency (`report.currency`) plus `亿`. No other cross-currency conversion.
- The opportunity-cost hurdle follows the price currency: use that currency's 10Y government yield × 2 (HKD → HK 10Y, USD → UST 10Y, CNY → China 10Y) and include an explicit 8% row in the payback table.
- Use 2-6 material company-specific Themes with 1-4 Observations each; do not pad the count. Require counter-evidence in every Challenge, both sides in every Resolution, Bundle evidence in every Decision Impact, and links covering the decision chain.
- Use 2-6 globally unique Bull and 2-6 Bear arguments. Accepted and discounted IDs must be valid and disjoint; disclose auto-discounted arguments.
- Use 2-6 decision-critical sensitivity drivers, one high importance, and a resolvable Assumption Pointer.
- Operating policy must use company-specific `metrics[]`, not a universal FCF gate. Each metric declares value reference, direction, thresholds, tolerance, uncertainty, and confirmation.
- Require explicit `portfolio_context`. Separate the research candidate action from the executable action; missing position/current/target weights must block an executable REDUCE and resolve to REVIEW.
- Require explicit `prior_report_context`: compare the latest baseline when it exists, or state why none exists. Preserve the old reported IRR separately from a runtime recalculation; never inherit an old calculated value by copying prose.
- Reader must show one current-decision table plus exactly one six-row Action Matrix (Buy/Add/Hold/Review/Reduce/Sell), the three principles (持有=买入、机会成本、10年回本), visible Base assumptions, natural Theme synthesis, and clickable sources.
- Reader must be natural Chinese and contain no internal IDs, Bundle paths, registry names, evidence roles, or hashes. Audit must preserve the complete graph, IDs, roles, assumptions, decisions, and dynamic verification.
- Independent business, financial, challenge, and risk perspectives are required. Parallel subagents are optional; use them only when requested or when their benefit justifies token and latency cost.

## Decision Gates

| Condition | Result |
|---|---|
| Missing or conflicting critical evidence | Fail or lower confidence explicitly. |
| Invalid source, Fact, evidence, value, or assumption reference | Fail build. |
| Graph, debate, sensitivity, or decision-chain coverage incomplete | Fail build. |
| Base IRR materially below hurdle | Research candidate cannot be HOLD. |
| Candidate REDUCE but portfolio status/current/target weight is incomplete | Executable action = REVIEW. |
| Robustness unstable | REVIEW unless SELL independently triggers. |
| Reader exposes audit syntax or Audit loses traceability | Fail build/verify. |
| Any generated artifact differs from compiler output | Fail verify. |

## Execution Steps

1. Collect the smallest sufficient data pack: prior report, current price, filings, four-quarter facts, company-specific operating metrics, peers, rates, and direct source metadata. For holdings, run `LEDGER_AUTH_TOKEN=... python3 scripts/ledger_portfolio_preflight.py --ticker <TICKER>` when Ledger is available and copy `portfolio_context_draft` into the Spec; ask the user for `target_weight`. If `trusted` is false or Ledger is unavailable, keep `position_status: unknown` (portfolio REVIEW), never an inferred empty position. Never print or persist the token.
2. Reconcile units and discrepancies; register Sources, Facts, derived calculations, assumptions, scenarios, operating metrics, and Decision Policy in a fresh Spec.
3. Conduct independent business, financial, challenge, and risk passes; synthesize only material logic into Themes and a Bull/Bear adjudication.
4. Apply the three principles, decision-critical sensitivity drivers, falsification conditions, and portfolio execution gate.
5. Build all artifacts, then read the Reader as the investor would and fix the Spec (not the output) until each check holds:
   - The first screen answers: what to do now, at what price it changes, and how far the price is from that line.
   - `什么会改变结论` break-even distances are plausible against the evidence; if a key assumption sits within one shock step of break-even, say the conclusion is fragile and lower confidence.
   - Every Theme states one company-specific mechanism with numbers; delete any sentence that would fit any company.
   - Falsification conditions are observable in the next one or two filings, with a metric and threshold.
   - The delta versus the prior report is explicit, and repetition across sections is removed.
6. Run verify and deliver only when artifact checks pass; disclose portfolio `REVIEW` rather than pretending missing context is complete.

The legacy five-line `Price Discipline` table (`templates/full-report.md`, `references/report-contract.md`) is not part of the v3 Reader; v3 prices come only from the Bundle.

## Output Contract

Return the five artifact paths; new-money action; research candidate and executable existing-position actions; portfolio-context status; Base IRR, target-return price, buy price, and distance from the current price; the most fragile assumption and its break-even; decisive Theme; strongest Bull and Bear arguments; unresolved uncertainty; and verify result.

The Reader must also contain the v3.2 decision-support blocks (from `research.decision_support`, build fails if missing): cash-basis valuation and cash confirmation price, three-basis payback, peer comparison (≥3), Bull/Base/Bear operating premises, normalization bridge, CapEx/R&D/PPE and balance sheet (cash, debt, buyback, SBC, shares), 5-year trend, ≥5 risks with probability/damage/indicator/action, new-money price ladder with current tier, five-type Action Triggers, Pre-Mortem, liquidity, 5-year after-tax dividends, and a minimum review checklist. Report the current ladder tier and its position range.

v3.2 decision coherence (company-agnostic; build fails on contradictions): declare `report.cash_valuation.decisive_basis` + `decisive_reason`, `accounting_basis` per earnings basis, optional `normalized_fcf`; machine-checkable `ladder_premises[tier].conditions` for every tier that allocates money (unpublished evidence = `status: unknown` + `pending`); `decision_support.cash_flow_escalation` aligned with thesis_break; `decision_support.roic`; peer `basis`; normalized-layer `method`; trigger `existing_action`; numbers bound in the growth ceiling and in at least two opportunity-cost comparators. Majority-size tiers must clear the hurdle on the decisive basis (anchor their floor at `BUNDLE:/derived/cash_valuation/decisive/confirmation_price`) or carry `price_ladder.cash_gate_waiver`. The Reader then states one executable new-money cap (`可执行新资金上限`), price tier vs executable tier, blockers, escalation level and ROIC; report these in the summary. Full contract: `references/full-methodology.md`.

## References

- `references/research-graph-v3.md` - v3 graph, debate, and sensitivity contract.
- `references/report-spec-v2.md` - Spec, numeric ownership, and provenance.
- `references/decision-policy-v2.md` - action resolution and price zones.
- `PRD-research-graph-investment-debate-v3.md` - design rationale and acceptance history.
- `PRD-data-reasoning-reader-v3.1.md` - v3.1 data, decision, and Reader redesign.
- `PRD-decision-guidance-v3.2.md` - break-even sensitivity, price distance, single valuation engine.

Any Skill behavior change must follow: PRD -> staged change log -> code/tests -> full CI -> final review.

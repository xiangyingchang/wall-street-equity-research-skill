---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 估值审判, 值不值, or 该不该买. Produce evidence-bound adversarial equity research."
license: MIT
metadata:
  author: xiangyingchang
  version: "3.4.2"
---

## 变更目的约定

所有变更的目的，都是得出更加准确、科学的研究报告，帮助用户理解风险、收益和行动条件，指导实际投资。不要为了完善而完善；始终围绕投资判断保持目标意识。

每项变更先说明要减少哪类研究错误、改善哪项投资判断，再用相应证据或测试验证。不能提高研究准确性、可验证性或决策清晰度的改动，不因增加功能、检查或流程而推进。事实、解释与假设分开；结论不确定时明确说明，不制造确定性。

## Activation Contract

Use for a listed equity when the user requests valuation, a buy/hold/sell judgment, or a full report. A ticker plus 跑一下/分析下 means a complete report delivered to Notion unless the user asks for a quick take.

## Hard Rules

- Read `references/research-graph-v3.md`, `references/report-spec-v2.md`, and `references/decision-policy-v2.md` before building a report.
- Initialize a fresh `report-spec-v3.1` (v3.2 fields) with `python3 scripts/new_report.py --format v3-spec --ticker <TICKER> --company <NAME> --market <MARKET> --out <new-spec.json>`. Fill null/TODO leaves explicitly; use `references/spec-v3.2-quickstart.md`. Never copy an old Markdown report or edit generated files.
- Build and verify only with:

```bash
python3 scripts/report_pipeline_v3.py build --spec <spec.json> --output <report.md>
python3 scripts/report_pipeline_v3.py verify --spec <spec.json> --output <report.md>
```

- Keep research artifacts in a dedicated `~/research-runs/<job-id>/` directory. After semantic review, verify and independent lint pass, use native Notion MCP to create one row in 投研报告 and write the full Reader into its body with status 初版未核验. Fetch the page to confirm its body and status, then record the URL, local Reader path and SHA-256 in `delivery.json` and retain a verified, privacy-checked compact audit archive before cleaning other intermediates. See [Notion delivery](references/notion-delivery.md).
- The Bundle owns every calculation and action. Narrative may explain but never override it.
- Never invent facts, prices, holdings, sources, assumptions, evidence, graph nodes, or arguments. Prefer Tier 1 evidence; Tier 2 market data must be labeled.
- Every Source requires a real HTTPS URL, date, precise locator, scope, and publisher. Generic source placeholders fail build. TTM inputs must share currency, scale, and per-share units where applicable.
- Companies without quarterly cash-flow disclosure may use explicit historical annual `cash_flow_basis` (see report-spec-v2.md), never invented quarters; unknown latest cash flow forces zero executable new money and REVIEW.
- Actual TTM inputs must be four distinct consecutive quarters matching the baseline EPS window and ending by `report.as_of`; non-calendar fiscal quarters require explicit ISO `period_end`. Forecasts cannot be actual TTM.
- Bind final summary, 持有=买入, debate adjudication, and each Theme decision impact with `text_template` and `value_refs` using `format: action` on `/decision/new_money_action`. Bind other action labels to compiled existing-position actions; migrate static action conclusions before building.
- Bind research numbers through JSON Pointer `value_refs`. Keep Sources, Facts, assumptions, policy, research, and Graph in the Spec.
- Quote every per-share price (current, target-return, buy, forward reference, price zones) in the listing-market currency: HK-listed → HKD, US-listed → USD, A-share → CNY. Never use a secondary counter (e.g. HK RMB counter 80700) to avoid FX. When the reporting currency differs, set `report.price_currency` and `report.fx_fact_id`; the FX Fact must have a Tier 1 source (e.g. CFETS central parity) and an as-of date, and only the compiler converts EPS. Absolute money stays in the reporting currency (`report.currency`) plus `亿`. No other cross-currency conversion.
- Explain each decision price in plain Chinese at first use: state which cash or earnings basis it uses, which position stage it governs, and what other conditions still block action. Label adjusted or conditional cash prices as assumptions and say they do not authorize a trade. Keep the first-tranche range, safety-margin boundary, and actual reported-FCF return threshold distinct; never leave a model field name as a standalone action label.
- The opportunity-cost hurdle follows the price currency: use that currency's 10Y government yield × 2 (HKD → HK 10Y, USD → UST 10Y, CNY → China 10Y) and include an explicit 8% row in the payback table.
- Use 2-6 material company-specific Themes with 1-4 Observations each; do not pad the count. Require counter-evidence in every Challenge, both sides in every Resolution, Bundle evidence in every Decision Impact, and links covering the decision chain.
- Use 2-6 globally unique Bull and 2-6 Bear arguments. Accepted and discounted IDs must be valid and disjoint; disclose auto-discounted arguments.
- Use 2-6 decision-critical sensitivity drivers, one high importance, and a resolvable Assumption Pointer.
- Operating policy must use company-specific `metrics[]`, not a universal FCF gate. Each metric declares value reference, direction, thresholds, tolerance, uncertainty, and confirmation.
- Require explicit `portfolio_context`. `current_weight` means the stock's CNY value divided by verified Notion portfolio net assets, including stocks, cash, options, crypto, liabilities, and FX. Separate the research candidate action from the executable action; missing position/current/target weights must block an executable REDUCE and resolve to REVIEW. A stock-pool ratio may be shown as supporting context, but it must never be labeled or used as the net-asset weight.
- When a stock-pool ratio is available but net-asset weight is unknown, say “占全部资产净值的比例未核实”; do not use the ambiguous phrase “当前权重未知/缺失”.
- Require explicit `prior_report_context`: compare the latest baseline when it exists, or state why none exists. Preserve the old reported IRR separately from a runtime recalculation; never inherit an old calculated value by copying prose.
- Reader must show one current-decision table plus exactly one six-row Action Matrix (Buy/Add/Hold/Review/Reduce/Sell), the three principles (持有=买入、机会成本、10年回本), visible Base assumptions, natural Theme synthesis, and clickable sources.
- Reader must be natural Chinese and contain no internal IDs, Bundle paths, registry names, evidence roles, or hashes. Audit must preserve the complete graph, IDs, roles, assumptions, decisions, and dynamic verification.
- Independent business, financial, challenge, and risk perspectives are required. Default to one sequential task via `scripts/run_reports.py`; no full-context child (`fork_turns=all`). If a requested independent challenge needs a child, use `fork_turns=none` and pass only the task, narrow contract, relevant Fact/source excerpts and output path. Preserve strongest counter-evidence and falsification thresholds. Route bounded mechanical tasks via the model policy below; never downgrade investment judgment on cost alone.

## Model routing (P0 implementation of review P1-2)

| Step | Model / effort | Basis and escalation |
|---|---|---|
| Fetch an already located source; extract fields, units, periods and source metadata | gpt-6.1-terra / high | Bounded input and typed output permit same-input comparison. Conflicting sources, missing quarters, ADR/FX or reported/adjusted ambiguity escalate to Sol. |
| Draft a narrow factual section from accepted Facts | gpt-6.1-terra / high | No new assumptions, cash normalization, valuation or action. Sol checks source fidelity and meaning before merging. |
| Map fields/paths or explain a narrow compiler error | gpt-6-luna / max | Output is a candidate patch/explanation; deterministic checks plus Sol acceptance required. Evidence gaps or changed actions escalate. |
| Build, verify, independent lint, completion JSON | Python / shell | No model is needed; run full checks, including after resume. Luna/max only if a narrow explanation is useful. |
| Business mechanism, four research perspectives, strongest countercase, normalization, assumptions, synthesis, full Reader review and final adjudication | gpt-6.1-sol / medium | These require investment judgment. Retain Sol and increase effort only when unresolved complexity warrants it. |

Run bounded calls with `scripts/run_model_task.py --profile terra|luna --task extract|section|format|error --input <minimal-prompt.txt> --out <new-directory>`; it pins the actual model/effort and starts a fresh session, without inherited history. Read `references/model-routing.md` when delegating. Low-tier output remains a candidate until same-input comparison against Sol and source/contract checks pass; unknown values must stay unknown. Evidence of one Micron case permits only the tested task shape, not blanket approval for every company or ADR/FX case. Untested or degraded task shapes stay with Sol. Record model/effort, input hash, usage, time and acceptance outside evidence packs. Token reduction is not guaranteed by lower pricing.

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

## Before publishing a decision

- Resolve checks that can be done now. Read the available filings, dated market data and authorized holdings records, and reproduce decision-critical calculations. State what was verified, the resulting action, and the evidence behind it. When the model returns REVIEW, explain what to do now and name the specific evidence or user decision still needed. Preserve the compiled action. Never infer a target weight or trade size.
- Check the timing and units of return cash flows. IRR uses the dates or periods of the individual cash flows, including dividends and sale proceeds. A calculation that moves all dividends to the exit date must be identified as an end-of-period annualized return approximation. State dividend amount or yield, how it depends on the entry price, and the tax convention. If the current compiler only reproduces the approximation, disclose it and label any timed cash-flow calculation as a separate check.
- For banks, assess distribution capacity using sustainable earnings, regulatory capital and buffers, credit quality, and approved distributions. Explain how deposits, lending and interbank flows affect reported operating cash flow. Industrial-company FCF and consecutive negative cash-flow tests do not establish a bank's distribution capacity. If a model requires such a gate, disclose the methodology limitation and leave unsupported inputs unknown.
- For a focused check of an existing report, state which inputs and conclusions were verified and which artifacts were rebuilt. Date the supplement and identify any historical output it supersedes. Claim full verification only after a successful rebuild and verification.

## Reader structure and language

- Start with the current decision, then a visible price block. Show the dated reference quote in listing currency, the Base target-return price with its annualized hurdle and horizon, and the Base safety-margin price with its discount. Show the distance from the same quote to both lines. Keep independently checked prices and historical model prices explicitly labeled by method and date.
- Build the main reading path around why the action follows from the business and financial evidence, how the valuation was derived, and what would change the action. Keep the single Action Matrix easy to find. When reorganizing an existing Notion report, group detailed tables and historical model results under descriptive collapsible headings where helpful. Preserve evidence, periods, and source links.
- Read the entire report in plain Chinese. At first use, explain what a decision-critical metric measures and what change would mean for the investment. Identify thresholds as model, company, or regulatory thresholds as applicable. Remove repeated conclusions and replace vague tasks with the specific missing evidence and its timing. Use humanizer-zh for Chinese editing when available. Preserve figures, units, periods, cash-flow timing, assumptions, uncertainty, sources, and executable actions. For compiled reports, make prose changes in the Spec and rebuild and verify.

## Execution Steps

1. First resume saved evidence/Spec in the same run directory. Check source hashes, expiry, latest reporting period, four-quarter window, and compiler fingerprint; fill only missing/stale evidence. Use the v3 adapter in `references/research-pack-v1.md`; saved, verified, and current are distinct. Collect the smallest sufficient data pack: prior report, current price, filings, four-quarter facts, company-specific operating metrics, peers, rates, and direct source metadata. For holdings, use the current records in the user's authorized Notion asset register. Match ticker and listing market, aggregate across accounts, and cite quantity, valuation dates and the weight denominator in the Spec's portfolio_context. A denominator must be complete and comparable to support an executable weight; label any mixed-date estimate separately. Keep missing or inaccessible data unknown and use a target weight only if explicitly confirmed. Treat legacy Ledger records as historical. Keep private portfolio links and identifiers out of public skill files.
2. Persist fetched originals/excerpts once; register native Sources/Facts through the immutable v3 evidence adapter, reused by draft, challenge, build and verify (`--evidence-pack`). Keep market quotes, historical snapshots and filings separate; use new pack filenames for revisions. Reconcile units and discrepancies; register Sources, Facts, derived calculations, assumptions, scenarios, operating metrics, and Decision Policy in a fresh Spec.
3. Conduct independent business, financial, challenge, and risk passes; synthesize only material logic into Themes and a Bull/Bear adjudication.
4. Apply the three principles, decision-critical sensitivity drivers, falsification conditions, and portfolio execution gate.
5. Run `python3 scripts/spec_precheck.py --spec <spec.json>` to aggregate static gaps (no default facts), then build all artifacts, then read the Reader as the investor would and fix the Spec (not the output) until each check holds:
   - The opening shows the current action and the two clearly labeled Base prices immediately below it. Pricing and execution conditions agree with the compiled decision.
   - `什么会改变结论` break-even distances are plausible against the evidence; if a key assumption sits within one shock step of break-even, say the conclusion is fragile and lower confidence.
   - Every Theme states one company-specific mechanism with numbers; delete any sentence that would fit any company.
   - Falsification conditions are observable in the next one or two filings, with a metric and threshold.
   - The delta versus the prior report is explicit, and repetition across sections is removed.
6. Save a Reader-hash-bound semantic review receipt (four perspectives; see quickstart), run full verify and independent `python3 scripts/report_lint.py <report.md>` on every delivery, including resumed jobs; deliver only when artifact checks pass; disclose portfolio `REVIEW` rather than pretending missing context is complete.

The legacy five-line `Price Discipline` table (`templates/full-report.md`, `references/report-contract.md`) is not part of the v3 Reader; v3 prices come only from the Bundle.

## Output Contract

Return the Notion page URL, local Reader path and delivery receipt; new-money action; research candidate and executable existing-position actions; portfolio-context status; Base IRR, target-return price, buy price, and distance from the current price; the most fragile assumption and its break-even; decisive Theme; strongest Bull and Bear arguments; unresolved uncertainty; and verify result.

The Reader must also contain the v3.2 decision-support blocks (from `research.decision_support`, build fails if missing): cash-basis valuation with the price where actual reported FCF reaches the return hurdle, explained in plain Chinese, three-basis payback, peer comparison (≥3), Bull/Base/Bear operating premises, normalization bridge, CapEx/R&D/PPE and balance sheet (cash, debt, buyback, SBC, shares), 5-year trend, ≥5 risks with probability/damage/indicator/action, new-money price ladder with current tier, five-type Action Triggers, Pre-Mortem, liquidity, 5-year after-tax dividends, and a minimum review checklist. Report the current ladder tier and its position range.

v3.2 decision coherence (company-agnostic; build fails on contradictions): declare `report.cash_valuation.decisive_basis` + `decisive_reason`, `accounting_basis` per earnings basis, optional `normalized_fcf`; machine-checkable `ladder_premises[tier].conditions` for every tier that allocates money (unpublished evidence = `status: unknown` + `pending`); `decision_support.cash_flow_escalation` aligned with thesis_break; `decision_support.roic`; peer `basis`; normalized-layer `method`; trigger `existing_action`; numbers bound in the growth ceiling and in at least two opportunity-cost comparators. Majority-size tiers must clear the hurdle on the decisive basis (anchor their floor at `BUNDLE:/derived/cash_valuation/decisive/confirmation_price`) or carry `price_ladder.cash_gate_waiver`. The Reader then states one executable new-money cap (`可执行新资金上限`), price tier vs executable tier, blockers, escalation level and ROIC; report these in the summary. Full contract: `references/full-methodology.md`.

## References

- `references/research-graph-v3.md` - v3 graph, debate, and sensitivity contract.
- `references/report-spec-v2.md` - Spec, numeric ownership, and provenance.
- `references/decision-policy-v2.md` - action resolution and price zones.
- `PRD-research-graph-investment-debate-v3.md` - design rationale and acceptance history.
- `PRD-data-reasoning-reader-v3.1.md` - v3.1 data, decision, and Reader redesign.
- `PRD-decision-guidance-v3.2.md` - break-even sensitivity, price distance, single valuation engine.

Any Skill behavior change must follow: PRD -> staged change log -> code/tests -> full CI -> final review.

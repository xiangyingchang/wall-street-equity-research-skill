# Decision guidance v3.2 — 2026-10-06

## 变更目的约定

所有变更的目的，都是得出更加准确、科学的研究报告，帮助用户理解风险、收益和行动条件，指导实际投资。不要为了完善而完善；始终围绕投资判断保持目标意识。

每项变更先说明要减少哪类研究错误、改善哪项投资判断，再用相应证据或测试验证。不能提高研究准确性、可验证性或决策清晰度的改动，不因增加功能、检查或流程而推进。事实、解释与假设分开；结论不确定时明确说明，不制造确定性。

## Goal

Make the v3 Reader answer what an investor acts on: what to do now, at what price or
assumption the answer changes, how far away that is, and how large a position is actually
executable. Every block that existed in the hand-written V3-Fast reports and helped a decision
must be bound to the Spec, and the compiled decision layers (valuation, ladder, triggers,
escalation, first screen) must resolve to one answer, not several.

## Background

A review of the 0700.HK report (2026-10-06) against the 2026-08-15 V3-Fast report found three
classes of failure. (1) The installed skill copies were pre-v3.1, so compiler checks never ran on
real reports. (2) Three redesigns (v2 compiler, v3 Theme narrative, 1b8b4f5 merge) silently dropped
useful content: Overview / business model / earnings update, cash-basis valuation, three-basis
payback, new-money price ladder, five-type triggers, Pre-Mortem, peers, risk probability and
damage, normalization bridge, CapEx and balance sheet, 5-year trend. (3) After restoring them,
the Reader gave three conflicting execution answers at the same price (Action Matrix "watch",
ladder "trial buy", triggers "do not buy"), and EPS target and FCF confirmation price diverged
2.4x with no declared decisive basis.

## Requirements

Iteration 1 — decision guidance
- Single-variable break-even values (operating margin, EPS CAGR, exit PE) and one-step shocks from
  the same `valuation_runtime` engine as the Bundle (`bundle.decision_sensitivity`).
- First screen shows distance from current price to target-return and safety prices.
- `valuation_math.py` delegates IRR / target price to `valuation_runtime`; add `safety_price`.
- Ledger preflight: localhost-only http, env-only token, negative-quantity warnings, `trusted`,
  `--ticker` draft of `portfolio_context`; target weight is never inferred.
- Full `现金流确认价` label lint; Reader quality self-check in SKILL execution steps.

Iteration 2 — listing currency
- Per-share prices use the listing-market currency. `report.price_currency` + `report.fx_fact_id`;
  the compiler converts EPS once at the EPS-to-price comparison and discloses rate and date.
  Absolute amounts keep the reporting currency. Mismatch without an FX fact fails the build.

Iteration 3 — Overview restored
- `## 1. Overview：商业模式与本次财报` with business model, segments, Key Forces, earnings update
  (changed / unchanged), Variant View, then the investment Themes.
- `research.overview.business_model` and `earnings_update` are required.

Iteration 4 — decision support restored (`research.decision_support`, required)
- Cash valuation (two earnings bases + FCF yield vs hurdle + the price where actual reported FCF
  reaches the hurdle, explained in plain Chinese), three-basis payback, 5-year after-tax dividends,
  new-money price ladder with premises, ≥5 risks with
  probability / damage / leading indicators / action, five-type Action Triggers, Pre-Mortem, ≥3 peers,
  normalization bridge, scenario operating premises, CapEx / R&D / PPE / balance sheet, 5-year trend,
  liquidity, minimum review checklist.

Iteration 5 — decision coherence (company-agnostic)
- `scripts/report_decision_coherence_v32.py` merges valuation, ladder, escalation and triggers into
  one executable new-money cap; contradictions fail the build.
- Spec declares `decisive_basis` + `decisive_reason`, `accounting_basis`, optional `normalized_fcf`.
- Ladder tiers that allocate money carry machine-checkable `conditions` (met / unmet / unknown);
  unmet or unknown premises downgrade the executable tier. Majority-size tiers must clear the hurdle
  on the decisive basis or carry `cash_gate_waiver`.
- One `cash_flow_escalation` table replaces scattered FCF thresholds and must agree with thesis_break.
- Triggers split new-money and existing-position action; valuation gates bind new money only.
- `roic` (ROIC and incremental ROIC), peer `basis`, normalized-layer `method`, margin × exit-PE grid,
  numbers bound in growth ceiling and opportunity-cost comparators.

## Acceptance

- Sensitivity Base IRR equals Bundle Base IRR; break-even values reproduce the hurdle.
- Legacy helper IRR / target price equal `return_pair` to rounding.
- Missing any required block, conflicting execution answer, or unmatched escalation fails the build.
- Reader marks exactly one `◀ 价格所在` tier and one `◀ 当前级` escalation level.
- 262 unit tests, self-tests, fixtures, and v2.1.2 / v3 build + verify CI paths pass.
- 0700.HK re-run passes build, verify and lint with one executable answer.

## Limits

No live research, Ledger fetch, or trading action. Break-even values are single-variable; the
two-dimensional grid covers only margin × exit PE. Spec schema name stays `report-spec-v3.1`; old
Specs must add the new required blocks before recompiling.

## Review fixes — 2026-10-06

- Reject BUY when the compiled executable new-money position cap is zero; build and verify must fail closed.
- Apply the majority-position cash gate to position_max, the amount actually permitted, not position_min.
- Require cash-valuation TTM inputs to use four distinct facts from consecutive fiscal quarters; retain exact Decimal sums and reject missing/invalid periods.
- Preserve listing markets in Ledger ticker matching and normalize Hong Kong leading-zero aliases. Multiple matching records require review rather than choosing one silently.
- Validate the four original reproductions and positive controls, full unit suite, lint/self-tests and both pipeline build/verify paths.

## Follow-up review fixes — 2026-10-06

- Align actual cash-valuation TTM windows with the baseline quarterly series and report cutoff, rejecting future or stale windows. Explicit quarter-end dates support non-calendar fiscal years.
- Bind material action conclusions to compiled actions using the existing text-template mechanism; reject static action claims in these conclusion fields. Keep company-specific reasoning and historical comparisons.
- Verify both original reproductions, changed-price BUY and unchanged-price DO_NOT_BUY outputs, and migration errors with build/verify tests.


## 2026-10-07 年度现金流披露适配
目的：避免公司只披露年度现金流时伪造四季数据或把旧年度现金流冒称最新 TTM。允许显式历史年度基准，但必须保留真实日期和原因；未知最新季度现金流、连续负季度计数时不得填零，也不得据此开放新资金。
Schema：顶层 cash_flow_basis={frequency:annual,fact_id,period_end,reason}，quarterly_series.fcf=[]。兼容数值指针附 frequency、period_end、label。年度 Fact 须 FYyyyy 及明确 period_end，结束不晚于报告日。cash_flow_escalation.status=unknown + pending 强制新资金上限零、已有仓位 REVIEW（独立 SELL 保留）。验收覆盖虚假季度、未来年度、口径标签及 fail-closed，保持全部既有 CI。

验收结果：2026-10-07 新增 7 项专项、全量 292 项单测及原 V2/V3 CI 端到端通过；年度/FY截止日一致、FCF类别、历史期间分句、未知计数上限零及独立 SELL 均已复查。仅源码本地改动，未提交或安装。

2026-10-07 最终 Reader 审查：历史现金参考价不能自动表述为大仓位成立条件；最新现金流未知时首页及 Action Matrix 买入/加仓/持有须明确核验约束，与上限零一致。

2026-10-07 主口径回本修正：三原则的回本判决必须与 cash_valuation.decisive_basis 一致；EPS 表保留作对照。现金口径缺少独立增长假设时，Base EPS 增长仅作对照，不足以判现金回本通过；历史年度/最新现金未知一律待核实。

## Follow-up — Plain-language price guidance (2026-10-22)

Purpose: remove ambiguity between a trial-entry range, the safety-margin boundary, and the price at which actual reported free cash flow reaches the minimum cash-return hurdle. A reader must not have to infer the action from model field names.

Requirements:
- The first page states the current new-money action, executable cap, price tier, blocker, and the meaning of the actual-FCF hurdle price.
- The cash-valuation section says that the actual-FCF price is where the modeled cash yield reaches the hurdle; it is not a standalone buy instruction.
- A conditional cash price names its assumption and states that it is not executable without evidence for that assumption.
- The price ladder identifies the safety-margin boundary between position stages and keeps operating conditions beside the price bands.
- Keep all formulas and computed prices unchanged.

Acceptance: a regression test checks the first-page wording and price-stage distinction; a rendered conditional-price example names the assumption; the Tencent 0700.HK Reader passes build, verify, and lint. Full CI must pass.

## Follow-up — Portfolio weight denominator (2026-10-22)

The research-only Ledger API now provides a separate owner-scoped portfolio summary with one CNY net-assets aggregate, a valuation date, freshness by component, and FX rates; it returns no account names or per-component balances. The preflight replaces the saved stock component in that aggregate with fresh, timestamped, two-source quotes for every active stock, and computes `current_weight` only when cash, options, crypto, liabilities, and FX are fresh. If any required non-stock component is missing, stale, or unpriced, keep `current_weight` empty. A separate `stock_pool_weight` may show one stock's share of all active stock value. The Reader must name that stock-only denominator, state that cash and other assets are excluded, and keep executable portfolio actions at REVIEW while net-asset or target weights are unknown.

When `stock_pool_weight` is available and `current_weight` is unknown, name the missing measure explicitly as “占全部资产净值的比例未核实”. Do not say only “当前权重未知” or “当前权重无法核算”, because the Reader already has a verified stock-pool ratio.

## Follow-up — Portfolio blocker diagnostics and latest validated quotes (2026-10-22)

Purpose: prevent stale portfolio values from appearing current, and make a missing net-asset weight immediately actionable. Also avoid selecting a matching prior-close pair when two providers agree on a later US trade.

Requirements:
- If `current_weight` is empty, state each missing or expired non-stock component by name and its last data date, then say which Ledger records must be updated before rerunning.
- Keep the verified share of all stock market value separate from the total net-asset weight. Do not use stale component data to estimate a current total-asset percentage.
- Parse Sina US trade timestamps from its US market-time fields, not its China-time server clock. Parse Nasdaq timestamps that include a time and ET/EDT/EST.
- Among pairs of independent quotes that agree within 1%, use the pair with the latest common observation time. Preserve the fail-closed rule when no agreeing pair exists.
- Bound quote-provider concurrency and retry transient Nasdaq network/server failures once so a rate-limited request does not invalidate every holding in the portfolio.

Acceptance: parser regressions cover Sina pre-market and prior-close observations plus Nasdaq timestamps with and without a time; portfolio diagnostics name stale cash and liability dates; pair-selection test prefers the latest agreeing pair; transient Nasdaq failures retry once; full report-tool tests pass.

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
- Cash valuation (two earnings bases + FCF yield vs hurdle + cash confirmation price), three-basis
  payback, 5-year after-tax dividends, new-money price ladder with premises, ≥5 risks with
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

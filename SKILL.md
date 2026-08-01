---
name: wall-street-equity-research
description: "Trigger: analyze a listed stock, 跑一下, 华尔街分析, 脱水质检, 10年回本测试, 估值审判, 值不值, or 该不该买. Produce evidence-bound single-stock research."
license: MIT
metadata:
  author: xiangyingchang
  version: "1.5.1"
---

## Activation Contract

Use for one listed equity when the user asks for valuation, buy/hold/sell judgment, a full stock report, or the trigger phrases above. In the Obsidian stock vault, a ticker or 跑一下/分析下 means a full saved report unless the user asks for a quick take. Do not use for portfolio allocation, macro, products, or 横纵分析法.

## Hard Rules

- Never invent live prices, filings, yields, or valuation data; Tier 1 evidence decides conflicts.
- Use `templates/full-report.md`; reports have pre-module sections plus 9 fixed modules, never visible YAML frontmatter.
- Every generated report must declare Skill version `1.5.1`, Template schema `full-report-v1.5.1`, actual Git commit, Report ID, and Runtime artifacts directory.
- Keep earnings deltas only for `报告类型=最新财报更新`; ordinary reports do not require them.
- Include Key Forces, Variant View, Pre-Mortem, a complete module 8 Action Matrix, four discount rows, and final 三原则扣问.
- Keep every executable conditional trade and threshold only in the Action Matrix; First-Page and Final Verdict may summarize but may not create another rule.
- Treat `research-pack-v1` as durable recovery state only; never add provider, model, token, timing, retry, or runtime telemetry.
- **Network-effects moat = user metrics required.**
- **Canonical Value Registry is mandatory:** `FACT-*` is externally verifiable, `DERIVED-*` is calculated from registered inputs, and `MODEL-*` is a model output. Every referenced ID must exist and prefix must match Kind.
- **Global ID Graph is blocking:** all `FACT/DERIVED/MODEL/ASM/THR/B/BR/REV/RUN` definitions and references must close. Missing IDs, naming drift, duplicate IDs, or orphan decision inputs fail delivery.
- **TTM values are runtime-authoritative:** TTM EPS, revenue, operating income, FCF, and ratios come from four explicit periods through `valuation_runtime.py ttm-derive`.
- **Derived provenance must be real:** a `DERIVED-*` row must list the actual registered component IDs. “four FACT IDs” without those IDs existing is invalid.
- **Historical adjustments and forward assumptions are separate:** Forward Basis rows may not cite historical Adjustment IDs as direct formula inputs.
- **Assumption closure is mandatory:** tax, other income, share count, EPS CAGR, dividend, exit PE, target return, reference multiple, safety margin, and every revenue growth/value input require `ASM-*` IDs.
- **Forward Revenue is runtime-authoritative and period-aware:** each period uses `guide_midpoint`, `yoy`, `qoq`, `explicit`, or `consensus`. YoY base period is prior-year same quarter; QoQ base period is previous quarter. Revenue rows must match the referenced Assumption mode, base period, forecast period, and value.
- **Scenario EPS is runtime-authoritative:** Bear/Base/Bull EPS rows come from `valuation_runtime.py eps-bridge` and list all input Assumption IDs.
- **Returns share one assumption set:** use `valuation_runtime.py return-pair`; separate `irr` and `reverse` are legacy-only. Required terminal EPS must reconcile with starting EPS, required CAGR, and years.
- **Scenario Valuation is runtime-authoritative:** run `report_integrity_v151.py scenario-value`. Forward reference = metric × reference multiple. Buy price = target-return price × (1 - safety margin), not a mechanical discount from forward reference.
- **Runtime artifacts are binding:** wrap every runtime output with `report_integrity_v151.py wrap-artifact`, save JSON in `<report>.artifacts/`, record artifact ID/file/hash in Runtime Artifact Manifest, and bind report table fields to the artifact.
- **Action thresholds require policy:** every numeric condition references `THR-*` with basis, lookback, confirmation, tolerance, minimum confidence, and rationale.
- **Action Matrix must be complete:** Buy/Add/Hold/Reduce/Sell executable rules must all have Rule IDs and all must be included in Runtime Evaluation. `N/A because current action is not X` is forbidden.
- **Neutral bands fail closed:** insufficient confidence, missing confirmation, tolerance-band values, or unstable robustness resolve to `REVIEW`.
- **Decision robustness is mandatory:** run at least ±5% shocks on decision-critical values. If action changes, current action is `REVIEW` unless an independent portfolio constraint is explicitly documented.
- **Point-in-time market cap requires structured reconciliation:** weighted-average diluted shares are an EPS denominator, not a market-cap share count. A prose reference to reconciliation is insufficient.
- **No buyback double count:** EPS CAGR already includes per-share effects; do not separately add buyback yield.
- **Opportunity-cost types are explicit:** actual 10Y yield is investable; `10Y ×2` is a required-return hurdle; indices/peers are risky alternatives.
- **Capex semantics:** Capex is cash. Undisclosed maintenance/growth/AI splits must be `Unclear`.
- **Verification is blocking:** runtime, artifact binding, ID graph, period semantics, valuation consistency, input/decision consistency, runtime/reference integrity, lint, and audit must all be actual PASS. TODO / FAIL / 未运行 / Unknown means incomplete.
- In pack-backed v5, declare derived inputs by `fact_ref` or `derived_ref`; only payback years may be a literal.

## Decision Gates

| Condition | Required action |
|---|---|
| Full report | Read every reference, use the v1.5.1 template, and save under `股票/<公司名>/`. |
| A-share | Run `scripts/a_share_prefetch.py` when network access permits; preserve manual notes. |
| US/HK/other | Complete IR, filing, current-price, 10Y, peer, and PDF-extraction preflight. |
| Latest earnings update | Add what changed and what did not inside module 1. |
| Network-effects moat claim | Evidence Ledger includes multi-period user/engagement metrics; module 3 includes a trend table. |
| Missing/conflicting critical evidence | Apply rating caps in `references/report-contract.md`. |
| Valuation report | Build Generation Manifest, Share Reconciliation, Canonical Value Registry, TTM Derivation, Adjustment Ledger, expanded Assumption Registry, Revenue Forecast, EPS Bridge, Basis Registry, Scenario Valuation runtime, Capex Bridge, Return Pair, Threshold Policy, complete Action Matrix, Action Evaluation, Robustness, and Runtime Artifact Manifest. |
| Filing gap or approximate owner earnings | Information Richness ≤ B and AI Research Confidence ≤ Medium. |
| No trigger, material indeterminacy, or unstable robustness | Current action must be REVIEW. |
| Price-zone/verdict conflict | Resolve before delivery; rename the zone or change the action. |
| Runtime artifact missing/hash mismatch/report-field mismatch | Fail delivery. |

## Execution Steps

1. Collect ticker, market, tax identity, horizon, opportunity cost, holding state, and size; state defaults.
2. Create a clean report from `templates/full-report.md`. Fill Generation Manifest from the actual repository HEAD.
3. Build Evidence Ledger, Point-in-Time Share Reconciliation, and Canonical Value Registry. Register every quarterly component used downstream.
4. Run `valuation_runtime.py ttm-derive` for every decision-critical TTM value. Wrap each output into a `RUN-*` artifact.
5. Build historical Adjustment Ledger separately from the expanded Scenario Assumption Registry. Register every numeric valuation input.
6. Run `valuation_runtime.py revenue-bridge` for four periods per scenario. Validate YoY/QoQ base periods and Assumption matches. Wrap outputs.
7. Run `valuation_runtime.py eps-bridge` for Bear/Base/Bull, using only registered inputs. Wrap outputs.
8. Register Basis IDs with `Adjustments=None` for forward bridges. Run `valuation_runtime.py return-pair` and wrap outputs.
9. Run `python3 scripts/report_integrity_v151.py scenario-value --input ... --output ...` for Bear/Base/Bull.
10. Define all Action rules and Threshold policies. Run `evaluate-action` and `robustness`; wrap both outputs.
11. Populate Runtime Artifact Manifest with actual files and hashes.
12. Run:
   - `python3 scripts/valuation_consistency.py <report.md>`
   - `python3 scripts/input_decision_consistency.py <report.md>`
   - `python3 scripts/report_integrity_v151.py check <report.md> --artifacts-dir <dir>`
   - lint, recognition, and audit.
13. Replace Verification placeholders only with actual command results. Any failure blocks delivery.

## Output Contract

Return the report path, final rating/action, key uncertainty, TTM/Revenue/EPS/Return/Scenario artifacts, Action Evaluation and Robustness results, all three consistency/integrity results, lint result, and audit result. A report is complete only when artifact files exist, hashes match, all table fields bind to runtime outputs, the global ID graph closes, and every Verification row is PASS.

## References

- `references/report-contract.md` — full-report contract and rating caps.
- `references/data-validation.md` — sources, provenance, discrepancy, and executable audit workflow.
- `references/research-pack-v1.md` — deterministic recovery pack and checkpoints.
- `references/researchability.md` — authoritative A/B/C and confidence rules.
- `references/valuation-consistency.md` — valuation basis and scenario boundaries.
- `references/valuation-runtime.md` — deterministic runtime command contracts.
- `references/input-decision-robustness.md` — v1.5 value kinds, threshold policy, and robustness.
- `references/runtime-binding-integrity.md` — v1.5.1 artifact binding, ID graph, period semantics, and assumption closure.
- `references/full-methodology.md` — 9-module method.
- `references/source-map.md` — Obsidian locations and prior-report continuity.
- `templates/full-report.md` — required v1.5.1 skeleton.

## Skill 维护纪律（强制）

任何对本 skill 的行为改动必须按以下顺序执行：

1. **先完善 PRD**：写明背景、现状、目标、范围、不在范围内、验证标准。
2. **先记录变更**：实施前创建版本变更记录；验证后更新为最终结果并合并进 `references/change-log.md`。
3. **再执行**：代码、模板、合同、测试同步更新，跑完整验证套件。

PRD 和 change-log 是仓库的一等公民，与代码同等重要，必须 commit 到仓库。

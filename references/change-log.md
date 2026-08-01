# Wall Street Equity Research Skill Change Log

## v3.1 - Data, Reasoning, and Decision Reader

## 2026-08-01

### Change

- Upgraded the active contract to `report-spec-v3.1`, `report-bundle-v3.1`, and Compiler/Verification 3.1.0.
- Required direct HTTPS source URLs, ISO dates no later than report as-of, precise locators, and rejection of generic index/peer placeholders.
- Added homogeneous TTM currency/scale checks and per-share currency checks; dynamic operating metric units must match their referenced Fact/Bundle values.
- Replaced the universal FCF operating gate with company-specific `metrics[]`, supporting higher/lower-is-better thresholds, explicit uncertainty bands, and integer confirmation evidence.
- Added mandatory portfolio context and separated the research candidate from the executable existing-position action. Candidate REDUCE without position/current/target weights becomes REVIEW; no position becomes NOT_APPLICABLE.
- Added mandatory prior-report context. Old reported IRR is preserved separately from a Decimal runtime recalculation using the old price, EPS, CAGR, exit multiple, horizon, and dividend assumptions.
- Changed Graph cardinality from fixed quotas to 2–6 material Themes, 1–4 observations per Theme, 2–6 arguments per side, and 2–6 sensitivity drivers while preserving evidence/counter-evidence/adjudication gates.
- Rebuilt the Reader first page around a current-decision summary, one six-action Matrix, the three original investment principles, visible Base assumptions, prior-report delta, and clickable sources.
- Replaced the seven repeated Theme labels with continuous evidence → explanation → challenge → decision → falsification prose; kept the complete node graph in Audit.
- Added a v3.1 Reader profile to `report_lint.py` and made Pipeline build/verify enforce it, so Reader/Audit separation no longer bypasses the established report discipline.
- Made source/calculation/data-quality/portfolio/prior-report/render checks dynamic; intentional missing portfolio context is REVIEW, not a false PASS or an invented trade.
- Added human thesis-break labels and blocked new-money BUY whenever thesis break triggers, regardless of price.
- Corrected stale active paths in `references/source-map.md` and stale module-8/9 Action Matrix references in the methodology.

### Reason

v3.0 improved auditability but directly rendered its graph as fixed three-theme, three-bull, three-bear, seven-label prose. The result was less direct and less useful than earlier reports. It also allowed missing URLs, a hard-coded FCF gate, historical arithmetic drift, and context-free REDUCE instructions.

v3.1 restores the earlier report's decision rhythm without giving up deterministic calculations or tamper-proof artifacts: collect accurate data, adjudicate only material logic, apply the three principles, then write a natural Reader.

### Verification

- Python syntax, financial rigor, audit, and lint self-tests: PASS.
- Lint fixtures: PASS.
- Full unittest suite: 184 / 184 PASS.
- v2.1.2 regression build/verify: PASS.
- v3.1 META build/verify and integrated report lint: PASS.
- Reader: 261 lines, zero old seven-label sequences, one authoritative Action Matrix.
- META prior-report IRR: reported 9.50%, runtime recalculated 1.64%; declared mismatch regression blocks.
- Source URL, unit, dynamic metric, portfolio gate, prior-report, thesis-break, Reader/Audit, and all-artifact tamper regressions: PASS.
- Skill quick validation and `git diff --check`: PASS.
- GitHub Actions first pass: push run 30694261919 and PR run 30694275857 PASS.

### Integration

Implemented in PR #10. The staged v3.1 change log was merged into this history and deleted before final CI.

## v3.0 - Research Graph and Investment Debate

## 2026-08-01

### Change

- Added `report-spec-v3.0` and `report-bundle-v3.0`.
- Added Research Graph: Source → Fact → Observation → Hypothesis → Challenge → Resolution → Theme → Narrative → Decision.
- Added 3–5 company-specific `THEME-*` objects and `OBS-*` observations.
- Required counter evidence in every challenge and evidence reconciliation in every resolution.
- Required Theme links to cover all nine research modules.
- Added Bull/Bear Investment Debate with at least three globally unique `ARG-*` arguments per side and Lead Adjudication.
- Prevented overlap/unknown debate IDs; omitted arguments are conservatively auto-discounted and disclosed.
- Added `DRV-*` Sensitivity Explanation with real Assumption Registry binding, canonical path normalization, direction, importance, mechanism, cases, and decision consequence.
- Added multi-perspective workflow inspired by AI Berkshire without copying persona scores or requiring a specific agent runtime.
- Reduced `SKILL.md` to a routing contract; detailed rules remain in local PRD/references.
- Clarified that independent perspectives are required but parallel subagents are optional and cost-aware.
- Restored report-currency-aware Reader formatting: absolute financial amounts use original currency plus `亿`, while per-share values remain per-share.
- Bound company name, return horizon, and payback horizon to the Spec; removed Meta-specific business prose from the shared Renderer.
- Added Theme-based Reader narrative, strongest challenge, falsification, Sensitivity Explanation, and Bull/Bear Debate.
- Added complete Graph structures to Audit and escaped all Graph table cells.
- Added independent v3 compiler, renderer, build, and verify pipeline.
- Build now blocks before writing invalid Reader/Audit artifacts.
- Verification statuses are derived from real graph and render checks rather than hard-coded PASS.
- Reader gates explicitly reject `THEME-*`, `OBS-*`, `ARG-*`, and `DRV-*` leakage.
- Reader Audit pointers use natural language and Chinese list joins avoid duplicated punctuation.
- Audit always discloses accepted, discounted, and auto-discounted argument sets, including an empty auto-discounted set.
- Sensitivity Assumption Pointers accept only the canonical Bundle form or the explicit Spec `scenario` form; arbitrary extra path components fail validation.
- Upgraded `SKILL.md` to v3.0.0.
- Added Meta v3 fixture, graph contract, focused tests, and CI validation.

### Reason

v2.1.2 was reliable and readable but still treated isolated Claims as the core research unit. It could state conclusions without consistently explaining causality, testing alternatives, adjudicating competing views, or identifying which assumptions control the decision.

v3 adds the missing research-process layer while preserving numeric truth and audit boundaries.

### What was learned from AI Berkshire

Adopted: independent perspectives, adversarial analysis, anti-bias challenge, Lead Analyst adjudication, and separation of exact calculation from prose.

Not adopted: persona-based master scores, fixed famous-investor roles, dependency on a specific subagent framework, or averaging conflicting opinions.

### Code review fixes

Independent review found and fixed:

- Theme links did not guarantee all nine modules were covered;
- Bull and Bear could reuse an Argument ID;
- Adjudication sets could overlap or silently omit arguments;
- concise Chinese implications were rejected by the old length gate;
- Sensitivity paths were not resolved against the real registry;
- fixture paths were invalid;
- Graph Audit tables did not escape pipes/newlines;
- build could write artifacts before validating render contracts;
- Verification statuses were hard-coded;
- v3 compiler did not reject legacy schema;
- Reader validation did not explicitly reject v3 internal ID prefixes;
- Audit omitted the auto-discounted field when the set was empty;
- sensitivity pointers with extra path segments were silently normalized;
- the Reader footer named internal Registry/Matrix structures;
- Observation and risk-indicator joins emitted duplicated punctuation;
- v3 tests did not directly cover all five tamper targets or Graph table escaping;
- the runtime Skill duplicated long-form documentation and defaulted to costly subagent parallelism;
- Reader tables and TTM prose dropped units from absolute financial amounts;
- the shared Reader Renderer hard-coded Meta, advertising-network prose, and 5/10-year labels.

### Verification

Final local pre-merge validation after rebase and Agent review: PASS. Final GitHub Actions validation is recorded by PR #9.

- Python syntax: PASS.
- financial rigor / audit / lint: PASS.
- full unittest suite: 177 / 177 PASS.
- v2.1.2 regression: PASS.
- v3 Meta build / verify: PASS.
- 3 Themes, 6 Observations, 3 Bull, 3 Bear, 3 Drivers, 2 High.
- Reader narrative / Sensitivity / Debate: PASS.
- Reader internal-ID exclusion: PASS.
- Audit Graph and escaping: PASS.
- build-time Reader/Audit gates: PASS.
- dynamic Verification: PASS.
- Graph/Reader/Audit/Bundle/Verification tamper binding: PASS.

### Integration

PR #8 was merged first. PR #9 was rebased onto `main`; this entry was prepended without modifying historical records; the staged change-log file was deleted before final CI.

## v2.1.2 - Reader-First Dual-Layer Renderer

## 2026-08-01

### Change

- Added a Reader-First dual-layer renderer.
- Added `scripts/report_renderer_readable_v212.py` with:
  - `render_reader_markdown(bundle)`;
  - `render_audit_markdown(bundle)`.
- Build now generates four immutable artifacts:
  - `<report>.md` Reader Report;
  - `<report>.audit.md` Audit Appendix;
  - `<report>.md.bundle.json`;
  - `<report>.md.verification.json`.
- Reader Report now leads with actions, current price, Base IRR, hurdle, target-return price, buy price, forward reference, core thesis, three core tensions, and falsification condition.
- Reader Report keeps all nine modules but removes implementation noise:
  - no Build Manifest or hashes;
  - no Source Registry or Evidence Ledger;
  - no internal `FACT-*`, `SRC-*`, `BUNDLE:*`, or `[supports]` tokens;
  - no full Assumption Registry or raw Decision Policy;
  - no Claim-Evidence Matrix or Verification table.
- Related claims are rendered as continuous prose instead of repeated claim/implication/evidence/confidence cards.
- Compiler-owned TTM, Scenario, IRR, price, payback, and action numbers are embedded directly into the readable argument.
- Reader evidence notes use human-readable source titles and “报告情景模型”.
- Audit Appendix preserves the complete v2.1.1 traceability view, including all registries, IDs, evidence roles, assumptions, policy evaluation, Claim-Evidence Matrix, and Verification.
- Verification now records both `reader_markdown_hash` and `audit_markdown_hash`.
- Verify recompiles and compares Reader Markdown, Audit Markdown, Bundle, and Verification independently.
- Added Reader-layer cleanliness checks, Audit-layer completeness checks, nine-module checks, key-number checks, and a 120–300 line readability budget.
- Updated Skill contract to v2.1.2.
- Updated CI and regression tests for dual-layer generation and tamper detection.

### Reason

v2.1.1 was reliable but difficult to read because it gave hashes, IDs, registries, evidence roles, and verification tables the same visual weight as the investment argument. The main report behaved like an audit export and forced the reader to reconstruct the thesis.

v2.1.2 does not weaken evidence controls or return to Markdown-first writing. It compiles a reader-facing report and a machine-facing appendix from the same Bundle, so readability and auditability no longer compete inside one document.

### Scope boundary

- No valuation formula changes.
- No Scenario-assumption changes.
- No decision-policy changes.
- No new research modules.
- No reduction in Source, Evidence Role, Value Binding, Research Quality, or tamper controls.
- Audit data is moved, not deleted.

### Verification

GitHub Actions `Validate` run #213: PASS.

- Python syntax: PASS.
- financial rigor / report audit / report lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **159 / 159 PASS**.
- v2.1.2 Meta build: PASS.
- v2.1.2 Meta verify: PASS.
- Reader Report generated: PASS.
- Audit Appendix generated: PASS.
- Reader contains all nine modules and key decision numbers: PASS.
- Reader excludes Source Registry, Claim-Evidence Matrix, FACT IDs, Bundle paths, and evidence-role tokens: PASS.
- Audit includes Source Registry, Claim-Evidence Matrix, and evidence roles: PASS.
- Reader tamper detection: PASS.
- Audit tamper detection: PASS.
- Bundle tamper detection: PASS.
- Verification tamper detection: PASS.
- deterministic Reader and Audit output: PASS.

### Integration

Before merging PR #8:

1. prepend this entry, followed by v2.1.1 and v2.1, below the title in `references/change-log.md`;
2. delete all three staged change-log files;
3. preserve every historical entry;
4. retarget/rebase PR #8 onto main;
5. rerun full CI;
6. merge only after Agent review and green CI;
7. regenerate Meta and deliver Spec, Reader, Audit, Bundle, and Verification together.

## v2.1.1 - Research Quality Binding

## 2026-08-01

### Planned change

- Add `text_template + value_refs` so research prose can embed compiler-owned values without handwritten numbers.
- Replace dot-separated Bundle paths with JSON Pointer paths.
- Upgrade evidence refs to typed `{ref, role}` objects with `supports`, `context`, and `counter_evidence`.
- Require at least one supporting evidence ref for each key claim.
- Compute Research Quality results dynamically and render Verification from those results.
- Validate risk confidence and rank uniqueness/continuity.
- Validate Source scope against Fact metric category.
- Escape Markdown table content safely.
- Add end-to-end and negative tests for value binding, evidence roles, path safety, source scope, dynamic verification, and table escaping.

### Reason

v2.1 restored complete research structure, but its prose still could not directly use core numbers; evidence only needed to exist rather than carry an explicit logical role; several quality flags were hard-coded; dot paths failed for decimal keys; and some validation boundaries remained weak. v2.1.1 turns the Research Layer from a structured outline into a numerically integrated and honestly verified report layer without changing the Single-Source Compiler architecture.

### Integration

After implementation and validation:

1. replace this planned entry with exact implementation and test results;
2. prepend it below the title in `references/change-log.md`;
3. delete `references/change-log-v2.1.1.md`;
4. mark `PRD-research-quality-binding-v2.1.1.md` completed;
5. rerun full CI before merge.

## v2.1 - Evidence-Bound Research Layer

## 2026-08-01

### Change

- Upgraded new-report schema to `report-spec-v2.1` and bundle schema to `report-bundle-v2.1`.
- Added structured `SRC-*` Source Registry with title, publisher, date, tier, document type, locator, and scope.
- Required every Fact to reference registered Source IDs; critical company financial facts require Tier 1 evidence when available.
- Added structured Research Layer covering all nine modules.
- Added claim/text, evidence_refs, confidence, implication, counter-evidence, risk mechanism, indicators, triggers, and mitigants.
- Added evidence closure for `SRC-*`, `FACT-*`, and `BUNDLE:<path>` references.
- Added numeric-safety validation so research prose cannot introduce unbound prices, percentages, multiples, large numeric facts, thresholds, or actions.
- Added complete generated Source Registry, Evidence Ledger, Quarterly TTM Bridge, Scenario Assumption tables, modules 1-9, Claim-Evidence Matrix, and Verification summary.
- Restored module 4 as a mandatory Valuation and Payback research section.
- Added Moat minimum contract: four dimensions, scores, evidence, counter-evidence, and trajectory.
- Added Risk minimum contract: three ranked risks with mechanism, leading indicators, trigger, and mitigant.
- Added separate research explanations for new-money and existing-position decisions without allowing narrative to override Compiler actions.
- Updated `report_pipeline_v2.py` build/verify to use the v2.1 research compiler and enforce required report sections.
- Updated `SKILL.md` to v2.1.0.
- Added `references/research-layer-v2.1.md`.
- Added a complete Meta v2.1 Spec factory and end-to-end research-quality tests.
- Updated CI to generate, build, and verify a full v2.1 Meta report.

### Reason

v2.0 correctly established one numeric truth, but its first Meta report was a thin calculation summary: most modules contained one sentence, module 4 was absent, sources were vague, assumptions were hidden, and claims lacked evidence binding.

v2.1 preserves the Single-Source Compiler and adds a constrained Research Layer:

```text
one typed Spec
→ deterministic analytical Bundle
→ evidence-bound Research Layer
→ complete compiled Markdown
→ generated Verification Manifest
```

This avoids both previous failure modes: freehand Markdown inconsistency and compiler-generated research shallowness.

### Verification

GitHub Actions Validate run #164: PASS.

- Python syntax: PASS.
- financial rigor, audit, and lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **143 / 143 PASS**.
- v2.1 end-to-end build: PASS.
- v2.1 end-to-end verify: PASS.
- all nine modules present, including module 4: PASS.
- Source Registry, Evidence Ledger, Quarterly TTM Bridge, Scenario Assumptions, and Claim-Evidence Matrix: PASS.
- report depth threshold and thin-placeholder rejection: PASS.
- Markdown, Bundle, and Spec tamper detection: PASS.
- missing module, missing evidence, undefined source, and unbound numeric negative tests: PASS.
- cross-scenario assumption and missing valuation-policy negative tests: PASS.
- guide-high versus midpoint test: PASS.
- deterministic Payback and Price Zone tests: PASS.
- Legacy Compatibility absence check: PASS.

### Integration

PR #8 is stacked on PR #7.

Before final merge:

1. review and merge PR #7;
2. rebase or retarget PR #8 onto the updated main branch;
3. prepend this entry below the title in `references/change-log.md`;
4. delete `references/change-log-v2.1.md`;
5. preserve every historical change-log entry;
6. rerun the full CI suite;
7. regenerate Meta from a fresh v2.1 Spec and deliver Spec, Markdown, Bundle, and Verification together.

## v2.0 - Single-Source Report Compiler

## 2026-08-01

### Change

- Replaced Markdown-first generation with a single `report-spec-v2` JSON source of truth.
- Added deterministic `report_pipeline_v2.py build/verify`.
- Added `report-bundle-v2` and generated Verification Manifest.
- Added deterministic renderer; Markdown is now a compiled view and cannot be safely hand-edited.
- Removed Legacy Compatibility Tables from all v2 reports.
- Added typed `global|bear|base|bull` assumptions and rejected cross-scenario references.
- Added mode-specific Revenue inputs:
  - guide midpoint;
  - guide high;
  - YoY;
  - QoQ;
  - explicit;
  - consensus.
- Added deterministic TTM, Revenue, EPS, Return Pair, Scenario Price, Payback, Decision, Robustness, and Price Zone compilation.
- Added separate `new_money_action` and `existing_position_action`.
- Added mandatory valuation-based Reduce/Review policy so “Hold = Buy” is executable.
- Moved tolerance and uncertainty into typed Policy/Fact fields; narrative text cannot change calculations.
- Added deterministic nominal and discounted payback root solving.
- Generated Price Zones from the same Base prices used by decisions.
- Added Spec, Bundle, and Markdown hashes plus tamper detection.
- Added Meta end-to-end Spec and golden expected outputs.
- Upgraded `SKILL.md` to v2.0.0.
- Added `references/report-spec-v2.md`, `references/decision-policy-v2.md`, and `templates/report-spec-v2.example.json`.
- Added explicit CI build + verify smoke test.

### Root cause addressed

v1.1-v1.5.1 fixed local arithmetic and consistency failures, but allowed the Agent to write the same economic concept repeatedly in Runtime tables, canonical tables, Legacy tables, price zones, and prose. Every additional checker reduced one class of errors while preserving the architecture that created the next class.

v2 changes the trust boundary:

```text
one typed Spec
→ one deterministic Bundle
→ one compiled Markdown report
→ one generated Verification Manifest
```

The report is no longer a second editable data model.

### Decision changes

- New-money and existing-position decisions are separate.
- SELL is reserved for thesis break.
- Material Base IRR shortfall can trigger REDUCE even when operating data is not yet broken.
- Explicit valuation review bands and operating tolerance/uncertainty determine REVIEW.
- Unstable robustness downgrades the existing-position action to REVIEW unless SELL independently triggers.

### Compatibility boundary

- v1.x reports continue to use legacy checkers.
- v2 reports use Spec + `report_pipeline_v2.py verify`.
- Compatibility tables are not emitted into v2 Markdown.

### Verification

GitHub Actions Validate run #129: PASS.

- Python syntax: PASS.
- financial rigor, report audit, and report lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **139 / 139 PASS**.
- v2 end-to-end build: PASS.
- v2 end-to-end verify: PASS.
- Markdown, Bundle, Verification file generation: PASS.
- Meta golden fixture: PASS.
- deterministic repeat build: PASS.
- Markdown tamper detection: PASS.
- Bundle tamper detection: PASS.
- Spec-change-without-rebuild detection: PASS.
- cross-scenario assumption rejection: PASS.
- missing valuation Reduce policy rejection: PASS.
- hidden narrative uncertainty isolation: PASS.
- guide-high versus midpoint test: PASS.
- deterministic payback monotonicity: PASS.
- Legacy Compatibility absence check: PASS.

### Integration

Before merging PR #7:

1. prepend this entry below the title in `references/change-log.md`;
2. delete `references/change-log-v2.0.md`;
3. preserve all historical entries;
4. rerun full CI;
5. merge only after Agent review and green CI;
6. regenerate Meta from a fresh `report-spec-v2` file, not from the old Markdown report.

## v1.5.1 - Runtime Binding and Reference Integrity

## 2026-08-01

### Change

- Added deterministic Runtime Artifact Envelope with canonical JSON SHA-256 hashes.
- Added `report_integrity_v151.py wrap-artifact` to persist exact runtime inputs/outputs as `RUN-*` JSON artifacts.
- Added deterministic `scenario-value` runtime:
  - forward reference value = metric value × reference multiple;
  - buy price = target-return price × (1 - safety margin).
- Added global ID Graph validation for `FACT-*`, `DERIVED-*`, `MODEL-*`, `ASM-*`, `THR-*`, `B-*`, `BR-*`, `REV-*`, and `RUN-*`.
- Added runtime file/hash/field binding for Revenue Forecast, EPS Bridge, Return Pair, and Scenario Valuation.
- Added Revenue period semantics:
  - YoY base period must be prior-year same quarter;
  - QoQ base period must be previous quarter;
  - Revenue row mode/base/forecast period must match its Assumption.
- Added Assumption closure for operating margin, tax rate, diluted shares, other income, EPS CAGR, dividend, exit PE, target return, reference multiple, safety margin, and period-level revenue inputs.
- Added Action completeness checks:
  - every executable rule has a Rule ID;
  - Action Matrix and Runtime Evaluation Rule ID sets must match;
  - `N/A because current action is not X` is forbidden.
- Added structured Point-in-Time Share Reconciliation for market-cap calculations.
- Blocked Forward Basis rows from citing historical Adjustment IDs as direct formula inputs.
- Upgraded `SKILL.md` to v1.5.1 and `templates/full-report.md` to `full-report-v1.5.1`.
- Added Generation Manifest and Runtime Artifact Manifest.
- Added `references/runtime-binding-integrity.md`.
- Added 10 v1.5.1 regression tests covering runtime binding and Meta v1.5 failure modes.

### Reason

The Meta v1.5 report proved that deterministic runtimes and structured tables were still insufficient when the Markdown report was not bound to the exact runtime artifacts. The report still contained:

- Required terminal EPS inconsistent with Required EPS CAGR;
- incorrect Scenario Valuation multiplication and buy price;
- missing Action/Threshold IDs and omitted Buy/Add evaluation rules;
- MODEL ID naming drift across sections;
- YoY Revenue using the wrong base quarter;
- Derived Values referring to FACT IDs that did not exist;
- claimed but absent market-cap share reconciliation;
- unregistered decision inputs;
- historical adjustments attached to forward formula bases.

v1.5.1 moves the trust boundary from “runtime mentioned” to “exact runtime file, hash, field, ID, period, and assumption are verifiable.”

### Scope boundary

- No external data fetching.
- No automatic selection of economically correct assumptions.
- No full DCF or Monte Carlo.
- No change to the nine-module report structure.
- Existing reports need migration only when regenerated under v1.5.1.

### Verification

GitHub Actions `Validate` run #94: PASS.

- Python syntax: PASS.
- financial rigor, report audit, and report lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **127 / 127 PASS**.
- new v1.5.1 tests: **10 / 10 PASS**.
- template/new-report recognition: PASS.
- Scenario runtime vector: `29.24 × 20 = 584.8000`: PASS.
- target-return-based buy-price calculation: PASS.
- Return Pair terminal EPS/CAGR mismatch negative test: PASS.
- Scenario multiplication mismatch negative test: PASS.
- undefined ID and omitted Action rule negative tests: PASS.
- invalid YoY base-period negative test: PASS.
- historical Adjustment in Forward Basis negative test: PASS.
- artifact missing/hash mismatch negative tests: PASS.
- uploaded Meta v1.5 report manually rejected by the new integrity checker; its critical failure modes are covered by regression tests.

### Integration

Before merging PR #6:

1. prepend this entry below the title in `references/change-log.md`;
2. delete `references/change-log-v1.5.1.md`;
3. preserve every historical change-log entry;
4. rerun the complete validation suite and CI;
5. merge only after final Agent review and green CI.

## v1.5 - Input Provenance and Decision Robustness

## 2026-08-01

### Change

- Added `valuation_runtime.py ttm-derive` for deterministic four-quarter sums and ratios, including TTM EPS and TTM operating margin.
- Added `valuation_runtime.py revenue-bridge` with `guide_midpoint`, `yoy`, `qoq`, `explicit`, and `consensus` modes so each forecast period is generated from auditable inputs.
- Added `valuation_runtime.py return-pair`, which uses one shared assumption set to output Scenario IRR, Reverse Expectations, and target-return-consistent current price.
- Extended Reverse Expectations to support the same dividend-yield assumption used by Scenario IRR.
- Upgraded Action Evaluation with v2 `values` and `thresholds` objects:
  - value kind (`FACT` / `DERIVED` / `MODEL`);
  - confidence and declared uncertainty;
  - threshold basis, lookback, confirmation, tolerance, minimum confidence, and rationale;
  - tri-state condition results: true / false / indeterminate;
  - REVIEW resolution when material indeterminacy can affect the highest-priority action.
- Added `valuation_runtime.py robustness` for configurable ±input shocks. Unstable decisions return `stable=false` and recommend `REVIEW`.
- Added `scripts/input_decision_consistency.py` to block:
  - model outputs labelled as FACT;
  - TTM values without component/runtime provenance;
  - unreconciled YoY/QoQ/guide Revenue rows;
  - effectively identical Base/Bull totals under conflicting growth assumptions;
  - naked Action thresholds and incomplete Threshold policies;
  - separate new-report `irr` / `reverse` commands;
  - unstable robustness with a non-REVIEW action;
  - buy-zone / no-buy / Reduce-Sell contradictions;
  - weighted-average diluted shares used directly for market cap;
  - conflicting structured TTM operating-margin values;
  - incomplete or failed Verification rows.
- Updated `SKILL.md` to v1.5.0.
- Updated `templates/full-report.md` with Canonical Value Registry, TTM Derivation, Revenue Forecast Runtime, Return Pair, Threshold Policy Registry, Action Evaluation v2, Robustness, and blocking Verification rows.
- Updated `references/valuation-runtime.md` and added `references/input-decision-robustness.md` as the v1.5 authoritative contract.
- Added and expanded regression tests for all Meta v1.4 failure modes.

### Reason

The Meta v1.4 report proved that deterministic arithmetic alone is insufficient. It correctly calculated EPS, IRR, Reverse Expectations, and rule booleans from supplied inputs, but the inputs and thresholds were internally inconsistent or weakly justified:

- TTM operating margin appeared as 35% and 43% instead of the approximately 38.08% four-quarter calculation;
- TTM EPS was about $27.25 instead of the four-quarter $26.55;
- +12% YoY Revenue rows did not reconcile to their base quarters;
- a manually selected $400亿 FCF threshold created a deterministic REDUCE without threshold provenance or a neutral band;
- current price was simultaneously no-buy, Reduce, and inside a buy zone;
- IRR and Reverse used different dividend inputs;
- fair value was registered as a Fact;
- weighted-average diluted shares were used for point-in-time market cap;
- required Verification stages remained TODO.

v1.5 moves the trust boundary upstream: values, forecast transformations, threshold policies, shared return assumptions, price semantics, and decision stability are now auditable runtime objects.

### Scope boundary

- No automatic market, filing, consensus, or portfolio data fetching.
- Runtime does not choose economically correct growth, margin, multiple, or threshold assumptions.
- No full DCF, Monte Carlo, or portfolio optimizer.
- The nine-module report structure is unchanged.
- Legacy `irr`, `reverse`, scalar-facts `evaluate-action`, and `resolve-action` remain available for old artifacts only.

### Verification

GitHub Actions `Validate` run #73: PASS.

- `python -m py_compile scripts/*.py`: PASS.
- financial rigor, report audit, and report lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **117 / 117 PASS**.
- TTM EPS vector: `1.05 + 8.88 + 10.44 + 6.18 = 26.5500`: PASS.
- TTM operating margin vector: approximately `38.08%`: PASS.
- Revenue vector: `563.11 × 1.12 = 630.6832`: PASS.
- Return Pair vector: Base IRR `6.54%`, Reverse required EPS CAGR `8.90%`, target-return price `479.7122`: PASS.
- Near-threshold vector: `378.7` vs `400`, tolerance `5%` plus uncertainty `1%` => indeterminate / REVIEW: PASS.
- ±5% robustness vector changes the action => `stable=false`, recommended action REVIEW: PASS.
- Negative tests for model-as-FACT, naked thresholds, buy-zone contradictions, Verification TODO, and weighted-average-share market-cap misuse: PASS.

### Integration

Before merging PR #5:

1. prepend this entry below the title in `references/change-log.md`;
2. delete `references/change-log-v1.5.md`;
3. preserve every historical change-log entry;
4. rerun CI on the integration commit.

## v1.4 - Deterministic EPS Bridge and Fact-Based Actions

## 2026-08-01

### Change

- Added `valuation_runtime.py eps-bridge` as the numeric authority for Revenue → operating income → pre-tax income → net income → EPS calculations.
- Added `valuation_runtime.py evaluate-action`, which evaluates Action Matrix conditions directly from Canonical Fact IDs and structured operators instead of accepting analyst-supplied `triggered=true/false`.
- Added strict fail-closed action evaluation for missing facts, unknown operators, invalid comparisons, duplicate Rule IDs, empty conditions, and fact-to-fact comparisons.
- Added Canonical Fact Registry, Scenario Assumption Registry, and four-period Forward Revenue Bridge to the canonical report template.
- Separated historical One-off Adjustments from forward revenue, margin, tax, share-count, Capex-normalization, exit-multiple, and growth assumptions.
- Expanded `valuation_consistency.py` to block:
  - Scenario EPS Bridge arithmetic that does not reconcile;
  - Basis values that differ from the referenced Bridge EPS;
  - duplicate Canonical Fact IDs;
  - Forward Revenue totals that do not match Scenario Revenue;
  - undefined quarter ×4.5/run-rate annualization;
  - future assumptions stored in the historical Adjustment Ledger;
  - Capex labelled non-cash;
  - legacy manual Triggered tables or `resolve-action` in new full reports;
  - `10Y ×2` presented as a low-risk investable asset.
- Updated `SKILL.md` to v1.4.0 and updated `templates/full-report.md` and `references/valuation-runtime.md` to make the new flow mandatory.
- Added focused regression tests reproducing the Meta 2026-08-01 failures.
- Preserved the canonical `10Y Treasury ×2` Evidence Ledger label so field recognition and generated-report fail-closed behavior remain compatible.

### Reason

The Meta 2026-08-01 rerun used correct IRR and Reverse Expectations formulas but fed them unsupported inputs. Its Scenario EPS Bridge stated Revenue `$2,750亿`, margin `35%`, tax `18%`, and shares `25.7亿`, while hand-writing EPS `$22`; the declared inputs imply about `$30.71`. The report also used an undefined “quarter ×4.5” revenue annualization and marked a Reduce rule as triggered through analyst judgment before sending the boolean to runtime.

The v1.3 runtime guaranteed arithmetic after inputs were supplied, but did not guarantee that bridge outputs were calculated from those inputs or that Action conditions were evaluated from source-bound facts. v1.4 closes those two gaps.

### Scope boundary

- No market or filing data is fetched automatically.
- Runtime does not decide which revenue, margin, tax, Capex, multiple, or growth assumptions are economically reasonable.
- No full DCF engine is added.
- Natural-language fact extraction remains out of scope; reports must register decision facts explicitly.
- Legacy `resolve-action` remains available for old artifacts but is blocked for new full reports.
- The nine-module report structure is unchanged.

### Verification

- GitHub Actions `Validate` run #49: PASS.
- `python3 -m py_compile scripts/*.py`: PASS.
- Financial rigor, report audit, and report lint self-tests: PASS.
- `python3 scripts/report_lint.py --fixtures tests/fixtures`: PASS.
- `python3 -m unittest discover -s tests`: 109/109 PASS.
- Meta EPS Bridge vector: `2750 × 35% × (1-18%) ÷ 25.7 = 30.7101`: PASS.
- Meta action vector: TTM margin `38.1%`, Reduce threshold `<35%` → Reduce false; with no other triggered rule → `REVIEW`: PASS.
- Generated template recognition: PASS after restoring the atomic `10Y Treasury ×2` label.

### Integration

Prepend this entry to `references/change-log.md` and delete `references/change-log-v1.4.md` during final merge integration. Historical entries must not be dropped.

## v1.3 - Deterministic Valuation Runtime

**Change**

- Added `scripts/valuation_runtime.py` as the numeric authority for Scenario IRR, Reverse Expectations, and current Action Matrix resolution.
- Added a strict no-double-count rule: EPS CAGR cannot be combined with separate buyback/share-count yield.
- Added `references/valuation-runtime.md` with the full Scenario EPS Bridge and source/confidence caps.
- Updated `SKILL.md` to v1.3.0 and made runtime outputs mandatory before verdict.
- Updated `templates/full-report.md` with Scenario EPS Bridge, runtime output tables, Current Action Evaluation, and verification results.
- Added `tests/test_valuation_runtime.py` covering the Meta IRR error, reverse-expectation math, buyback double counting, and no-trigger REVIEW behavior.

**Reason**

The Meta 2026-07-31 report passed structural checks while hand-writing a 9.5% IRR that should be about 1.6%, computing Reverse Expectations incorrectly, registering unsupported normalized EPS, and claiming Reduce when no Action Matrix rule had triggered.

**Scope boundary**

The runtime does not fetch data or decide accounting assumptions. It deterministically calculates from explicit inputs and refuses internally inconsistent modeling choices.

**Verification target**

- `python3 -m py_compile scripts/valuation_runtime.py`
- `python3 -m unittest tests.test_valuation_runtime`
- full existing unittest suite, lint self-test, fixtures, and diff check.

## PR #3 Review Fixes

**Change**
- Fixed `test_valuation_runtime.py` expected values: terminal_eps `32.3262` -> `32.3252`, irr_pct `1.63` -> `1.64`, required_terminal_eps `47.8203` -> `47.7954`. The original assertions had transposition typos; the runtime computation was correct.
- Fixed critical Decimal context leak: `valuation_runtime.py` set `getcontext().prec = 50` at module level, which mutated the global Decimal precision and caused `report_audit.build_manifest` to produce different hashes when tests ran in discover order. Replaced with `localcontext()` inside `scenario_irr` and `reverse_expectations` so the high precision is scoped to valuation math only.
- Removed unused `getcontext` import.
- Added regression test `test_importing_module_does_not_change_global_decimal_precision` to prevent future global context mutations.

**Reason**

The context leak was a silent test-order-dependent failure: `test_v4_fixture_bytes_hash_and_verdict_remain_compatible` passed in isolation but failed in `discover` mode because `test_valuation_runtime` (alphabetically earlier) imported `valuation_runtime`, which raised global precision to 50, changing manifest hash arithmetic.

**Verification**

- `python3 -m py_compile scripts/valuation_runtime.py` PASS
- `python3 -m unittest tests.test_valuation_runtime` 6/6 PASS
- `python3 -m unittest discover -s tests` 92/92 PASS
- `python3 scripts/report_lint.py --self-test` PASS
- `python3 scripts/report_lint.py --fixtures tests/fixtures` PASS
- `git diff --check` PASS
- Meta IRR = 1.64% (not 9.5%); Reverse EPS = 47.7954 (about 47.8); CAGR = 16.79% (about 16.8%)
- EPS CAGR + buyback correctly rejected; no-trigger resolves REVIEW

This file is staged separately because the existing monolithic `references/change-log.md` must be prepended during final integration without discarding historical entries.


## 2026-07-31

### Valuation-basis registry, scenario math, and semantic consistency audit

**Change:**
- Added `references/valuation-consistency.md` as the authoritative contract for Valuation Basis Registry, One-off Adjustment Ledger, Scenario Valuation, Capex / Owner Earnings Bridge, fair-value/buy-price/stress-price separation, and three-model valuation synthesis.
- Added `scripts/valuation_consistency.py`, a blocking semantic checker for basis/adjustment references, scenario arithmetic and ordering, PE/FCF-yield reconciliation, and high-confidence prose contradictions.
- Updated `templates/full-report.md` with the new registries/bridges, 5-year Scenario IRR, Reverse Expectations, and explicit separation of fair value, buy price, and stress price.
- Updated `SKILL.md`, report contract, methodology, and README so the semantic checker runs before structural lint/audit. Fixed stale "10 modules" wording to 9 modules.
- Added unit tests covering valid reports, bad scenario math, unknown Basis IDs, FCF-yield mismatch, and unknown Adjustment IDs.

**Reason:** The Meta 2026-07-30 report passed existing lint/audit while containing valuation-scale drift, arithmetic contradictions, overlapping price zones, unsupported normalized EPS, and repeated conservative discounts. Structural completeness is not semantic correctness.

**Scope boundary:** This batch does not fetch data, estimate maintenance capex, implement a full DCF engine, or automatically rewrite historical reports. The new checker validates declared report structure and arithmetic; accounting judgments and source truth remain human responsibilities.

**Verification:** GitHub Actions runs py_compile, the full unittest suite, report-lint self-test, fixtures, the new checker tests, and diff-check before committing the migration. See the PR checks for the exact result.

## 2026-07-31

### Gate 7 extension + B-level conversion rate fix

**Change:**
- Extended Gate 7 to cover share counts (2.566B -> 25.66亿) and user/engagement metrics (3.60B DAP -> 36亿), not just $-prefixed money amounts. Added `WESTERN_BARE_SUFFIX` and `SHARE_USER_CONTEXT` patterns; bare suffixes flagged only on lines with share/user-metric context keywords.
- Fixed critical B-level conversion rate error: previous commit (ceefdd2) used B=1.0, but 1 billion = 10亿, so all B-level amounts were 10x too small (e.g. `$130B` became `$130亿` instead of `$1,300亿`). Correct rate: B=10, M=0.01, T=10000. Re-converted the entire Meta 2026-07-30 report from the original pre-conversion version with correct rates.
- Fixed PER_SHARE_CONTEXT false-positive: `/股` in "债务/股权比" and "share" in "FCF/share" column name caused entire lines to be skipped, leaving B-level amounts unconverted. Removed the line-skip logic since per-share amounts (e.g. `$6.18`) have no M/B/T suffix and are naturally not matched.
- Updated PRD, methodology, and report-contract descriptions to reflect correct conversion rates and the "any Western suffix fails" logic (not "亿 coexistence required").

**Reason:** User requested all amounts including share counts and user metrics be converted to "亿" for readability. During implementation, discovered the B-level conversion rate was wrong (B=1.0 instead of B=10), meaning all dollar amounts in the previous commit were 10x too small. This was a silent data-integrity error that lint could not catch (lint only checks for Western suffixes, not conversion correctness).

**Scope boundary:** No change to lint detection logic for $-prefixed amounts (already working). Only extended to bare suffixes on share/user lines. Conversion correctness is the report author's responsibility; lint enforces unit format, not arithmetic.

**Verification:** `python3 -m py_compile scripts/*.py` PASS; `python3 -m unittest discover -s tests` 76/76 PASS; `report_lint.py --self-test` PASS; `report_lint.py --fixtures tests/fixtures` PASS; `git diff --check` PASS. Meta report lint+audit PASS with correct amounts ($1,300亿 capex, $902.64亿 cash, 25.66亿 shares, 36亿 DAP).

## 2026-07-31

### Amount unit standardization lint gate - absolute amounts must use "亿"

**Change:**
- **Gate 7 (report_lint.py):** Absolute money amounts must use "亿" (yi) with the original currency, not Western M/B/T suffixes (e.g. `$1,300亿` not `$130B`). No cross-currency conversion. Per-share amounts, multiples, ratios, KRW amounts, and formula variables are exempt. KRW reports are fully exempt (face value too large for "亿" to be practical).
- Updated `references/full-methodology.md`: added "金额单位标准（lint 强制）" section before Evidence Ledger, documenting the standard and exemptions.
- Updated `references/report-contract.md`: added Analysis Density Gates entry 7.
- Updated `SKILL.md` Hard Rules: added amount-unit standardization to the analysis-density-gates bullet.
- Updated fixture and self-test inline good report: `Revenue >= $10B` -> `Revenue >= $100亿`.
- Updated `tests/test_validation_cli.py`: synced `$10B` -> `$100亿` in matrix variable and negative-contract cases.
- Migrated the live Meta 2026-07-30 report: converted 117 absolute-amount occurrences from Western M/B/T to "亿" (e.g. `$130B` -> `$130亿`, `$784M` -> `$7.84亿`, `$1.503T` -> `$15,030亿`).

**Reason:** Meta 2026-07-30 report used Western M/B/T suffixes (`$130B`, `$784M`, `$1.33T`) throughout, with zero occurrences of "亿". Unit inconsistency reduces readability and prevents quick cross-comparison of absolute scale. User requested: amounts at the "亿" magnitude must uniformly use "亿" as the standard unit, with no cross-currency conversion.

**Scope boundary:** No cross-currency conversion (no exchange-rate dependency or audit risk). Per-share amounts (EPS, price, dividend, target price), multiples (PE x), ratios, and percentages are unchanged. KRW reports are exempt. User metrics (DAP 3.60B) and share counts without $ prefix are not enforced by this gate (industry convention).

**Verification:** `python3 -m py_compile scripts/*.py` PASS; `python3 -m unittest discover -s tests` 76/76 PASS; `report_lint.py --self-test` PASS; `report_lint.py --fixtures tests/fixtures` PASS; `git diff --check` PASS. Meta report passes lint and audit after migration. SK海力士 (KRW) correctly exempted.

## 2026-07-31

### Price discipline lint gates - target PE/price + price-zone summary

**Change:**
- **Gate 5 (report_lint.py):** Module 8 must contain a price-zone summary table whose header or cells reference at least 2 of the three tiers (safe-margin / observation / overvalued). Pure-observation names may state "无价格区间" with a reason to skip; holding positions may not use this exemption.
- **Gate 6 (report_lint.py):** Module 8 or 9 must contain a target-price keyword (目标 PE / 目标价 / target PE / target price / 安全买入) near a numeric value. Pure qualitative wording does not satisfy the gate.
- Updated `templates/full-report.md`: added `### 目标 PE 与价格线` and `### 价格区间摘要` placeholders after the module 8 Action Matrix, aligning template with methodology.
- Updated `references/full-methodology.md`: marked the target-PE and price-zone-summary sections as lint-enforced requirements (not just guidance).
- Updated `references/report-contract.md` Analysis Density Gates: added entries 5 and 6.
- Updated `SKILL.md` Hard Rules: added price-zone summary and quantified target PE to the analysis-density-gates bullet.
- Updated fixture and self-test inline good report with price-zone table and target PE; regenerated v4 manifest.
- Migrated the live Meta 2026-07-30 report: added target PE (18x x $22 = ~$396) and three-tier price-zone table to module 8.

**Reason:** Meta 2026-07-30 module 8 had only discipline thresholds and Action Matrix; the target PE / price line and price-zone summary required by methodology were missing. SK海力士 report contained a price-zone table, confirming it was a historical convention that the Meta report dropped. Same root cause as the prior four gates: prose guidance without lint enforcement and no template placeholder, so the LLM skipped it.

**Scope boundary:** No module structure change. Price zones still only explain valuation context; all executable trades remain defined solely by the Action Matrix. No payback formula or Evidence Ledger field changes.

**Verification:** `python3 -m py_compile scripts/*.py` PASS; `python3 -m unittest discover -s tests` 76/76 PASS; `report_lint.py --self-test` PASS; `report_lint.py --fixtures tests/fixtures` PASS; `git diff --check` PASS. Meta report passes lint and audit after migration.

## 2026-07-31

### Analysis density gates - self-test fixture fix + methodology hardening

**Change:**
- Fixed `report_lint.py --self-test` regression: the built-in good report lacked the moat score table and peer comparison table required by the new gates. Added both tables to the inline fixture (moat 5-row score table in module 3; peer comparison table under a `### 竞品对比` subheading with 2 competitors x 3 metrics).
- Strengthened `references/full-methodology.md`: upgraded the moat scoring, peer comparison, and multi-scenario valuation bullets from prose guidance to explicit lint-enforced requirements (referencing `report_lint.py` and the ≥$50B capex / cyclical keyword trigger).
- Added the network-effects user-metrics requirement to methodology module 3 (DAU/MAU/DAP with YoY trends).
- Marked `PRD-analysis-density.md` status as 完成.

**Reason:** The self-test fixture was not updated when the new gates were added, so `report_lint.py --self-test` regressed. The methodology still described these as "should" rather than "must + lint-enforced", so LLMs could still treat them as optional. Both are now consistent with the lint gates.

**Verification:** `python3 -m py_compile scripts/*.py` PASS; `python3 -m unittest discover -s tests` 76/76 PASS; `report_lint.py --self-test` PASS; `report_lint.py --fixtures tests/fixtures` PASS; `git diff --check` PASS. Live reports (SK海力士, MU, Meta) correctly FAIL on the new gates where structure is missing, confirming the gates are working as intended.

## 2026-07-30

### Analysis density lint gates - moat score table, multi-scenario valuation, peer comparison, Variant View placement

**Change:**

- **Gate 1 (report_lint.py):** Module 3 must now contain a moat score table with 5+ scored dimensions (column named 'score' or '分数'), each with non-empty evidence. Prevents散文-only moat analysis.
- **Gate 2 (report_lint.py):** Module 4 must contain a multi-scenario valuation gate table (3+ rows) when capex >= $50B or cyclical industry keywords are detected. Covers peak/mid-cycle/normalized/EV-FCF scenarios. Non-cyclical, low-capex companies are exempt.
- **Gate 3 (report_lint.py):** Report must include a peer comparison table with 2+ competitors and 2+ metrics. An explicit "无直接可比竞品" claim with reason exempts the report.
- **Gate 4 (report_lint.py):** Variant View must appear as `### Variant View` in module 9 only; module 6 placement is now a lint error.
- Updated fixture, v4 manifest, and test expectations for the new table content.

**Reason:** Meta 2026-07-30 report lacked moat scoring, multi-scenario valuation, and peer comparison despite methodology already requiring them. The rules existed as prose guidance but had no lint enforcement, allowing the LLM to skip them. These gates upgrade guidance to hard constraints.

**Scope boundary:** No module structure change (still 9 modules). No Action Matrix, payback formula, or Evidence Ledger field changes. Non-cyclical companies are exempt from the multi-scenario valuation gate. Existing reports (SK海力士, MU) pass; Meta requires a rerun.

### Remove module 7 (Tax Drag & Net Yield); reduce from 10 to 9 modules

**Change:**

- Removed the dedicated `## 7. 真实到手收益 + 税收摩擦 Tax Drag & Net Yield` module from the report contract, methodology, template, and fixtures. The report now has 9 fixed modules instead of 10.
- Renumbered the trailing modules: old 8 (Institutional & Opportunity Cost) -> 7, old 9 (Position Sizing & Exit Rules / Pre-Mortem / Action Matrix) -> 8, old 10 (Final Verdict / Variant View / 三原则扣问) -> 9.
- `scripts/report_lint.py`: removed `"7."` (the old Tax Drag slot) and `"10."` from `EXPECTED_TOP_SECTIONS` so the expected top-level sequence is `First-Page Verdict -> Evidence Ledger -> ## 1. through ## 9.`; renamed the lint section bindings `module9`/`module10` to `module8`/`module9` (Pre-Mortem and Action Matrix now checked against module 8; 三原则扣问 and Buy-rating gates now checked against module 9); updated `action_matrix_errors` signature/docstring and all "module 9"/"module 10" lint messages to "module 8"/"module 9"; renumbered the built-in self-test good report.
- `templates/full-report.md` and `tests/fixtures/good-full-report.md`: removed the module-7 section and renumbered 8/9/10 to 7/8/9.
- `SKILL.md` and `references/report-contract.md`: "10 fixed modules" -> "9 fixed modules", "10-module" -> "9-module", and "module 9 Action Matrix" -> "module 8 Action Matrix"; the Buy-rating opportunity-cost pass reference moved from module 10 to module 9.
- `references/full-methodology.md`: removed the module-7 section, renumbered subsequent module headings and all positional `第 N 模块` references; reworded the four-lens mapping (capital allocation no longer has a dedicated module; buyback/SBC remains in module 2) and the two `税务身份决定第 8 模块的预扣税` lines (withholding tax no longer has a dedicated module; tax identity still affects opportunity-cost and after-tax return caliber, and the tax-identity lint gate still requires declaring 税务身份).
- Migrated the two live Obsidian reports (META 2026-07-30, MU 2026-07-30-rerun) to the 9-module structure.

**Reason:** The user decided tax drag / net yield analysis is no longer needed in reports. Removing it shortens every report by one module and drops a section whose content (withholding tax, buyback yield) overlapped with module 2 (Financial Autopsy) and module 7 (Institutional & Opportunity Cost). The tax-identity lint gate is retained so reports still declare their investor tax context.

**Scope boundary:** No provider/model/token telemetry was added. The audit v4/v5 paths, research-pack schema, payback formulas, and the structural Action Matrix contract are unchanged; only module numbers and the removed module's prose moved. The Action Matrix table is still located by its `### Action Matrix` heading, now under module 8 instead of module 9.

**Verification:** `python3 -m py_compile scripts/*.py` passed; `python3 -m unittest discover -s tests` passed; `financial_rigor.py`, `report_audit.py`, and `report_lint.py` self-tests passed; `report_lint.py --fixtures tests/fixtures` passed; both live reports pass lint; `git diff --check` passed.


### Network-effects moat requires quantified user metrics

**Change:**

- **Hard Rule (SKILL.md):** Added a rule that when the moat analysis claims network effects, the Evidence Ledger must include multi-period DAU/MAU/DAP or equivalent engagement data with YoY trends, and module 3 must contain a dedicated user-metrics table. Never substitute qualitative descriptions for quantified user evidence.
- **Decision Gate:** Added a new gate for network-effects companies.
- **Execution Step 3:** Explicitly calls for at minimum three-period user/engagement metrics with YoY trends.

**Reason:** The wall-street-equity-research method judges moats by evidence, not narrative. Network effects are the most commonly claimed yet least quantified moat—every platform company says it, few provide the data to prove it. This rule closes that gap by requiring user-metric tables in any report that invokes network effects as a moat. Meta 2026-07-30 report was the first report to comply.

**Scope boundary:** Applies to all reports where the moat analysis claims network effects, social platforms, two-sided marketplaces, or user flywheels. Companies where the moat is based on other factors (IP, regulation, cost advantage) are unaffected.

### 4R Code Review Fixes - Atomic transactions, lock timeout, symlink hardening, Action Matrix dedup, verdict messages

**Change:**

- **R4 CRITICAL-1 (`new_report.py`):** Made `_write_transaction` truly atomic across the report+pack two-file commit. A failed `os.replace` for the pack after the report committed now restores the original pack bytes (when overwriting an existing pack) and rolls back the report, so a pack write failure can never leave a new report with a missing or partially written pack.
- **R4 CRITICAL-2 (`research_pack.py`):** `pack_write_lock` no longer blocks indefinitely. It now acquires `fcntl.flock` with `LOCK_NB` in a bounded retry loop (default 30s timeout) and raises `StateConflict("pack lock timeout: another writer may be stuck")` on timeout instead of hanging the process. No threading-based timeout is used.
- **R1 WARNING-1 (`research_pack.py`):** `pack_write_lock` now calls `reject_symlink(lock_path, "pack lock")` before opening the lock file, closing the symlink gap that only checked the pack path.
- **R1 WARNING-2 (`research_pack.py`):** `_load_json` (the source/fact/derived-record/valuation-basis JSON reader) now calls `reject_symlink(path, label)` before reading bytes, so a crafted symlink cannot redirect a JSON input read.
- **R2 CRITICAL (`validation_common.py`, `report_lint.py`, `report_audit.py`):** Moved the shared Action Matrix contract (`ACTION_MATRIX_COLUMNS`, `ACTION_MATRIX_NA_VALUE`) and the canonical "find the module 9 Action Matrix table" locator (`find_action_matrix_table`) into `validation_common.py`. `report_lint.py` and `report_audit.py` both import from there and the duplicated local definitions were removed, so the two tools can no longer drift on the header contract or table-location sequence.
- **R2 WARNING-2 (`report_audit.py`):** Removed the dead `_ACTION_MATRIX_NA` constant (the audit only extracts action/trigger sets, never N/A values).
- **R4 WARNING (`report_audit.py`):** Fixed the misleading v4/v5 verdict error messages. A manifest version mismatch with `--pack` now reports `manifest version X is incompatible with --pack; use --results for v4 or re-extract with --pack for v5`, and an unknown version with `--results` reports `manifest version X is incompatible with --results; use --pack for v5 or re-extract a v4 manifest for --results`, instead of both mislabeling the problem as a flag incompatibility.
- Added regressions: pack-restore-on-overwrite rollback, pack-lock timeout with a held lock, symlinked lock-path rejection, symlinked `_load_json` input rejection, and version-specific verdict mismatch messages.

**Reason:** The 4R review found a non-atomic two-file transaction that could lose the pack on failure, an unbounded lock that could hang a writer, two symlink-rejection gaps in the pack/JSON read paths, duplicated Action Matrix parsing that could drift between the lint and audit tools, dead code, and verdict error messages that misdiagnosed version mismatches as flag incompatibilities.

**Scope boundary:** No provider/model/token telemetry was added. The v4 audit path, v4 manifest/results bytes, no-pack workflows, and empty `action_matrix` packs are unchanged. The lock timeout default is 30s and configurable per call. The lint keeps its granular error messages while delegating the canonical table location to the shared helper.

**Verification:** `python3 -m py_compile scripts/*.py` passed; `python3 -m unittest discover -s tests` passed 76 tests; `financial_rigor.py --self-test`, `report_audit.py --self-test`, and `report_lint.py --self-test` passed; `report_lint.py --fixtures tests/fixtures` passed; `git diff --check` passed; both live reports (MU 2026-07-30, META 2026-07-26) pass lint.

### Optimization Batch 2C - Semantic Action Matrix, tax, opportunity-cost, and previous-report gates

**Change:**

- Added a strict per-entry schema for the research pack's `action_matrix` in `scripts/research_pack.py`: each entry must have exactly `action` (Buy/Add/Hold/Reduce/Sell), `trigger_type` (price/valuation/operating/thesis-break), `condition` (nonempty string), `execution` (nonempty string), and `na` (boolean; true only for Buy or Add). Unknown or missing keys, invalid actions or trigger types, empty condition/execution, a non-boolean `na`, and `na: true` on Hold/Reduce/Sell now fail `validate` and `status`. An empty array remains valid. This replaces the prior "array of JSON objects" placeholder check.
- Added a v5-only semantic Action Matrix correspondence check in `scripts/report_audit.py`: when a pack's `action_matrix` is non-empty, extract and verdict verify the report's module 9 Action Matrix table declares the same action set and trigger-type set, with no missing or extra actions or trigger types. A missing or malformed report table blocks. This is a structural correspondence check, not a free-text condition parser. An empty pack `action_matrix` skips the check, so existing packs and the no-pack v4 path are unaffected.
- Added a tax identity gate in `scripts/report_lint.py`: the report must declare a tax identity context (e.g. 税务身份=中国大陆个人, a US-listed or HK-listed investor) or state N/A with a reason; otherwise lint blocks. This prevents reports that silently omit tax considerations.
- Added an opportunity-cost benchmark gate in `scripts/report_lint.py`: whenever the report mentions valuation, it must reference an opportunity-cost benchmark (10Y government bond, index return, or explicit alternative). The contract already enforced an opportunity-cost pass for Buy ratings in module 10; this gate extends the benchmark requirement to every rating.
- Strengthened the previous-report delta gate in `scripts/report_lint.py`: when the pack's `previous_report` is set or the report text references a prior report, the report must contain a delta covering at least the rating change (or explicit "unchanged"), a key metric change, and the thesis change (or explicit "unchanged"). The earlier change-log entry described this rule; the refactored lint had lost it, so it was rebuilt and strengthened to require all three sub-deltas.
- Updated `tests/test_report_audit_v5.py` with action_matrix entry-schema and v5 correspondence regressions, and `tests/test_validation_cli.py` with tax-identity, opportunity-cost, and previous-report-delta regressions. Updated the lint self-test good report to carry a tax identity so the new gate passes.
- Updated `references/report-contract.md` and `references/research-pack-v1.md` with the new gates, schema, and correspondence behavior.

**Reason:** The pack deferred Action Matrix semantics and the report lint did not enforce tax identity, an all-rating opportunity-cost benchmark, or a complete prior-report delta. Those gaps let a rerun silently drop tax friction, benchmark comparisons, or the comparison against the previous report, and let a pack's Action Matrix drift from the report's module 9 table.

**Scope boundary:** No provider/model/token telemetry was added. The Action Matrix check is structural correspondence only and does not parse free-text conditions. The v4 audit path, v4 manifest/results bytes, no-pack workflows, and empty `action_matrix` packs are unchanged. The lint gates are text-based structural checks; they do not fetch or verify real-world evidence.

**Verification:** `python3 -m py_compile scripts/*.py` passed; `python3 -m unittest discover -s tests` passed 71 tests; `financial_rigor.py`, `report_audit.py`, and `report_lint.py` self-tests passed; `report_lint.py --fixtures tests/fixtures` passed; `git diff --check` passed.

### Optimization Batch 1 — Canonical payback formula registry

**Change:**

- Added `scripts/financial_formulas.py` as the single Decimal-50 registry for `payback_ttm_v1` and `payback_forward_v1`, including nominal `r=0` evaluation through the same formulas, strict input domains, adaptive upper bracketing, deterministic bisection, and explicit no-root/nonconvergence errors. Convergence requires interval width `<=1e-24`, absolute residual `<=1e-24`, and relative residual `<=1e-24` for a nonzero target; `payback_forward_v1` with `years=1` always raises a non-identifiable domain error because growth cannot be solved from its constant output.
- Added `financial_rigor.py payback` with human-readable and JSON output. JSON preserves every numeric field, including `interval_width`, as a string and identifies the formula and exact inputs.
- Replaced the A-share float solver implementation with a compatibility wrapper over `payback_ttm_v1`; its public float/`None` return contract and caller-owned rounding remain unchanged.
- Added focused MU TTM/Forward vectors, a current META TTM vector, domain/no-root/non-identifiable/nonconvergence CLI failures, >100% adaptive bracket, determinism, absolute and relative residuals, JSON typing and exact keys, no-engine-rounding, A-share compatibility, and wrong Forward `t=0` denominator regressions. CI now discovers both the existing 18-test suite and the new formula suite.
- Documented the canonical formula IDs and first-year Forward discount convention in `references/data-validation.md`.

**Reason:** The report workflow had multiple payback implementations and a historical Forward discount-index ambiguity. One named, high-precision engine makes valuation roots reproducible without changing A-share payload types or adding telemetry.

**Scope boundary:** No Forward calculation was added to the A-share interface, no caller rounding moved into the engine, and no telemetry was added.

**Verification:** See the final Batch 1 handoff for the exact full-suite, self-test, fixture, skill-validation, and diff-check commands and results.

### Optimization Batch 2A — Durable research pack and valuation-basis lock

**Change:**

- Added zero-dependency `scripts/research_pack.py` with the strict `research-pack-v1` top-level contract; atomic sorted JSON writes; stable exit/stderr behavior; canonical HTTPS source IDs; strict source/fact schemas; typed Decimal/date facts; undefined-source validation; and ordered `initialized -> sources_ready -> facts_ready -> valuation_locked -> matrix_ready -> draft_ready -> audit_passed` upstream hashes.
- Added source/fact invalidation, idempotent `UNCHANGED` writes, a positive Decimal price/share valuation basis, explicit market-price kinds, reasoned canonical revision history, and valuation/downstream invalidation without wall-clock fields.
- Added optional `scripts/new_report.py --research-pack [path]` and `--previous-report` integration while preserving the legacy generator path and output when omitted.
- Added `references/research-pack-v1.md` plus focused runtime pointers in `SKILL.md`, `README.md`, `references/data-validation.md`, and `references/report-contract.md`.
- Added `tests/test_research_pack.py` for URL normalization, source conflicts, undefined references, typed values, atomic failure, checkpoint ordering/hashes/invalidation, valuation revisions, deterministic bytes, CLI contracts, and legacy/optional `new_report.py` behavior. Existing CI discovery already includes this file through `python -m unittest discover -s tests`, so no workflow-only edit was needed.
- Applied the confirmed Batch 2A review fixes: `new_report.py` now refuses report/pack symlinks and path collisions, preflights arguments and pack conflicts before `--force`, stages both outputs, rolls back existing bytes on failure, removes temporary files, and restores the historical one-line no-pack stdout while keeping recognition fail-closed and silent on success.
- Strengthened checkpoint gates so every predecessor must be `CURRENT` by recomputed hash, while source/fact mutations deterministically remove their dependent checkpoint suffix.
- Tightened the schema and CLI: `derived_records` and `evidence_gates` must be empty objects; recursive `provider`/`model`/`tokens`/`finish_reason`, unknown defined keys, non-finite JSON constants, malformed types, and undefined valuation source IDs fail closed; invalid `status` is nonzero without a traceback.
- Resolved report continuity paths to absolute form, rejected URL authority whitespace/control characters, preserved repeated internal path slashes while removing exactly one documented trailing slash, and added collision/control/stale-upstream/rollback/symlink regressions.
- Required `revise-valuation` to recompute and verify every upstream checkpoint through `facts_ready`; a stale valuation lock can be revised only after those upstream hashes are current.
- Expanded recursive telemetry-key rejection to the case-insensitive set `provider`, `model`, `token`, `tokens`, `finish_reason`, `timing`, `retry`, `runtime`, `latency`, `duration`, `started_at`, and `ended_at`, while retaining legitimate evidence dates and `as_of`.
- Rejected ASCII control characters and DEL anywhere in the original URL before parsing, preventing newline/tab stripping from collapsing distinct path, query, fragment, or authority inputs.

**Reason:** Interrupted research should resume from durable, deterministic evidence and valuation inputs instead of reconstructing state or silently changing the market basis.

**Scope boundary:** The research pack is durable recovery state, not provider/model/token/timing/retry/runtime telemetry. Batch 2A adds no Audit v5 behavior, semantic Action Matrix validation, automatic fetching, or provenance resolution.

**Verification:** `python3 -m unittest discover -s tests` passed 51 tests; `financial_rigor.py --self-test`, `report_audit.py --self-test`, `report_lint.py --self-test`, and `report_lint.py --fixtures tests/fixtures` passed; `quick_validate.py .` reported `Skill is valid!`; the expanded case-insensitive Batch 2A telemetry-field scan passed; and `git diff --check` passed.

### Optimization Batch 2B — Derived records and pack-backed Audit v5

**Change:**

- Extended the Decimal-50 registry with exact `sum_v1`, `difference_v1`, `product_v1`, `ratio_v1`, `ttm_sum_v1`, and `ttm_bridge_v1` results while retaining both payback IDs and their residual/tolerance contract. TTM sum requires four consecutive `FYyyyy-Qn` labels, adjacent 70-115 day spacing, and an exact calendar-year match for the set's unique Q4 fiscal-year anchor. TTM bridge requires typed `fy + current_ytd - prior_ytd`, an exact annual FY period-end year anchor, adjacent declared fiscal years, 350-385 day YTD comparison, and 13-week-per-quarter bridge windows with 35-day 52/53-week tolerance.
- Enabled strict `derived_records` and `research_pack.py derived-add`: `fact_ref` and recursive `derived_ref` inputs resolve value/unit/date/source provenance from registered pack objects, while the only literal is positive integer payback `years`. Caller-supplied value/source fields on references are rejected. Undefined references, cycles, duplicate input names, TTM chronology errors, unsupported unit algebra/scaling, incorrect computed values, and duplicate bindings fail closed. Identical additions are `UNCHANGED`; conflicts fail; mutations invalidate `matrix_ready` and later checkpoints.
- Added manifest v5 behind `report_audit.py extract --pack`. Extract and verdict use validated immutable single-read snapshots whose public constructors reject forged text/byte, parsed/byte, or exact recursive Python type mismatches; they reject report/pack/manifest symlinks, path collisions, and duplicate JSON keys. V5 recursively recomputes references, formulas, TTM chronology, payback residuals, unit algebra/conversion, rounding, provenance, bindings, and actual cells.
- Defined stable audit persistence without a self-referential hash and closed the remaining cooperative TOCTOU window. Every skill-supported research-pack writer and v5 verdict uses one sibling advisory lock; verdict re-reads and compares the pack inside the lock, constructs and validates the final state, and atomically commits before release. A competing cooperative writer is preserved and causes a stale verdict snapshot to block. The guarantee intentionally excludes arbitrary processes that bypass the advisory lock. Failed verdicts write nothing, the actual pack SHA-256 equals manifest `pack_sha256`, and identical reruns remain PASS without byte changes.
- Hardened v4 CLI paths without changing manifest/results bytes, verdict logic, or numeric grammar: report/manifest/results must resolve distinctly, symlink outputs and collisions fail before writes, and extraction commits both outputs through one rollback-capable atomic transaction. Validation failures preserve prior bytes, and `$10/share` remains ineligible under frozen v4 parsing while `/share` is v5-only.
- Normalized Unicode IDNA separators and ASCII/Unicode DNS trailing dots into one canonical host/source ID.
- Added compact MU/META vectors, detached 2010/2015/2020/2025 and whole-set +1-year chronology attacks, reference laundering/cycle/undefined cases, unit scale attacks, value and tuple/list snapshot forgeries, a deterministic two-supported-writer race, stable reruns, IDNA variants, v4 collisions, deterministic v5 output, and frozen current-fixture v4 byte/hash/verdict/parser regressions.
- Updated `SKILL.md`, `README.md`, and the data-validation, research-pack, and report-contract references with the command split and compatibility boundary.

**Reason:** Calculated report values need reproducible component provenance and offline recomputation. Plausible spacing alone did not bind a whole fiscal label set to its real year; canonical JSON equality did not preserve Python object identity; and a compare followed by an unlocked replace still allowed a cooperative writer's update to be lost. Exact fiscal anchors, type-strict snapshots, and a shared lock covering the complete supported write transaction make those cases fail closed.

**Compatibility:** V4 extraction/verdict behavior, manifest bytes, caller-filled results authority, payback callers, and no-pack workflows remain unchanged. The reference-only schema applies only to pack-backed v5 derived inputs, selected with `--pack`. No network fetching, telemetry, semantic Action Matrix/evidence gates, or live MU/META migration was added.

**Verification:** `python3 -m unittest tests/test_report_audit_v5.py` passed 15 focused tests and `python3 -m unittest discover -s tests` passed 66 tests. `financial_rigor.py`, `report_audit.py`, and `report_lint.py` self-tests passed; lint fixtures passed; `quick_validate.py .` reported `Skill is valid!`; `py_compile` passed for `financial_formulas.py`, `research_pack.py`, `report_audit.py`, `new_report.py`, and the focused test. The targeted telemetry regression detected all 12 forbidden keys without false-positive date fields; explicit v4 and v5 CLI groups passed 3 tests each; and `git diff --check` passed.

## 2026-07-26

### Batch 1 — Decimal calculation rigor

**Change:** Added MIT-attributed, zero-dependency `scripts/validation_common.py` and `scripts/financial_rigor.py`; they share finite Decimal parsing, report-to-authority discrepancy, symmetric independent-source spread, and exact calculation. Positive and negative source order cannot reduce the spread.

**Reason:** Market-cap and valuation arithmetic must be reproducible, while <=1% is consistent, >1%-5% needs reconciliation, and >5% cannot enter analysis without Tier 1 verification.

**Verification:** `python3 scripts/financial_rigor.py --self-test` passed; 100 versus 106 blocks and large decimal literals retain Decimal precision.

### Batch 2 — Deterministic manual report audit

**Change:** Added MIT-attributed, zero-dependency `scripts/report_audit.py` with full-cell amount parsing, header-filtered eligible numeric columns, a >=15% denominator, eligible-universe hashes, generated results template, live-report manifest reconstruction, normalized vendor-domain independence, provenance structure, and manual-only reconciliation gates. Added the complete upstream notice in `references/third-party-notices.md`.

**Reason:** Extraction can prioritize review, but no script may silently fetch, refresh, or reconcile market evidence.

**Verification:** `python3 scripts/report_audit.py --self-test` and `python3 -m unittest tests/test_validation_cli.py` passed; eight CLI/parser tests cover canonical fixture extraction, full currency forms, malformed/empty/stale inputs, rehashed manifest tampering, same-vendor subdomains, report types, and positive/negative source order.

### Batch 3 — Market-aware validation policy

**Change:** Added `references/data-validation.md` and linked it from the runtime skill, report contract, and methodology; it documents the exact extract/template/verdict commands and human provenance boundary.

**Reason:** Tier 1 authority, practical Tier 2 checks, accounting/FX/date/unit/share-count differences, and historical price adjustment need a single explicit policy across US, Hong Kong, and A-share reports.

**Verification:** `references/data-validation.md`, the contract, and the methodology were cross-checked for the same Tier 1/Tier 2 rules.

### Batch 4 — Research-confidence boundary

**Change:** Added `references/researchability.md` as the single authority for deterministic A/B/C evidence coverage, AI confidence caps, investment certainty, and first-page decision confidence. Lint validates report type, values, and caps.

**Reason:** Evidence abundance measures research coverage, not investment quality; information scarcity alone is not a negative verdict.

**Verification:** `python3 scripts/report_lint.py --self-test` and `python3 scripts/report_lint.py --fixtures tests/fixtures` passed.

### Registry refresh

**Change:** Refactored `SKILL.md` to the LLM-first style guide: complete metadata, compact runtime rules, decision gates, output contract, and local references.

**Verification:** `python3 /Users/haoshifasheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py .` passed. Run `gentle-ai skill-registry refresh` before relying on updated metadata in a registry-driven environment.

### Batch 5 — Four-lens overlay

**Change:** Kept the authoritative Duan/Buffett/Munger/Li Lu mapping only in the methodology, reduced the runtime skill to a pointer, and limited the contract to observable unresolved-disagreement output; preserved the 2026-07-24 latest-earnings-only delta rule.

**Reason:** The overlay should sharpen existing analysis without creating a roleplay section or forcing ordinary reports to pretend they are earnings updates.

**Verification:** `report_lint` self-test includes an explicit earnings-update negative case, while the normal passing fixture contains no earnings-delta bullets.

### Batch 6 — Manifest v4 decision coverage and internal-source hardening

**Change:**

- Upgraded the audit manifest to v4 and force-included decision-critical fields when present: price, shares, market cap, cash, debt, TTM EPS, TTM FCF/share, 10Y yield, 2× yield, portfolio weight, and all EPS/FCF/EV-FCF payback outputs. The final selected count still determines the reported `actual_ratio`, and manifest/universe hashes remain deterministic.
- Classified Module 4 payback outputs from their metric columns before reading 10Y discount-row labels, preventing required-growth values from being mislabeled as government yields.
- Added the `Internal` portfolio evidence tier but restricted `portfolio_system` URLs to the exact canonical `https://github.com/xiangyingchang/portfolio-dashboard` repository after safe host/path case and trailing-slash normalization. Arbitrary, lookalike, credential-bearing, queried, or fragmented GitHub URLs are rejected.
- Added regressions for mandatory inclusion, payback/yield separation, exact repository approval, arbitrary GitHub rejection, missing manifest results, empty required fresh values, and invalid required sources.

**Reason:**

- A 15% hash sample could omit the values that directly drive an investment decision while still returning PASS.
- Broad 10Y label matching could demand yield provenance for payback-growth calculations.
- Trusting every `github.com` URL as an internal portfolio authority allowed attacker-controlled or fake repositories to masquerade as the canonical dashboard.
- Verdict must fail closed when any required manifest result, recomputed value, or source evidence is absent or invalid.

**Verification:** `python3 scripts/report_audit.py --self-test`, `python3 -m unittest discover -s tests`, `python3 scripts/report_lint.py --self-test`, and `python3 scripts/report_lint.py --fixtures tests/fixtures` passed. The current META report reconstructed manifest v4 at 25/63 eligible cells (39.68%), and all 25 required audit outcomes passed.

### Batch 7 — Field-recognition preflight and authoritative Action Matrix

**Change:**

- Moved the existing Markdown table traversal into `scripts/validation_common.py` and reused it from audit extraction, field recognition, and lint. The existing audit classifier and alias registry remain the sole field-classification authority; no parallel parser or registry was added.
- Added `scripts/report_audit.py recognize --report <report.md>`. It recognizes all manifest-v4 mandatory decision categories from labels even when value cells contain placeholders, reports missing categories plus line-numbered unrecognized or ambiguous decision labels, and returns 0 for a valid recognition contract, 1 for contract failures, and 2 for invalid input or usage.
- Updated `scripts/new_report.py`, `SKILL.md`, `README.md`, `references/report-contract.md`, `references/full-methodology.md`, `references/data-validation.md`, and CI so recognition runs immediately after canonical skeleton creation and is required again before extraction.
- Made the canonical template's mandatory Evidence Ledger rows atomic and classifier-compatible, and added the missing atomic EV/FCF required-growth column to module 4.
- Replaced `Action Triggers` with exactly one module 9 `Action Matrix` using the exact columns `Action | Trigger type | Executable condition | Position/execution`. Lint now requires Buy/Add/Hold/Reduce/Sell and price/valuation/operating/thesis-break coverage, rejects duplicate or malformed matrices and legacy headings, and conservatively blocks explicit conditional threshold trades outside the matrix while excluding source text.
- Added focused regressions for missing or duplicate matrices, wrong columns, missing actions or trigger types, external conditional threshold trades, legacy headings, missing or unrecognized decision fields, ambiguous labels, and invalid recognize input. Updated the canonical good fixture and lint self-test to the new matrix contract.
- Migrated the 2026-07-26 META report without changing its Hold-Index investment decision: all executable conditions and thresholds now live only in the module 9 Action Matrix, while First-Page and Final Verdict retain current-action and range summaries without duplicate trade rules.
- Regenerated the META manifest/results after the report hash changed from `815751dde944971d8913b879ee4fa2f1424dea4373c4ed0650f6e4d15a59dabd` to `f40f84a93978a26208f523c8f7abc97a5003fc6a7f7c4aa31611e7caddc70288`; all 25 prior source-evidence records were remapped by stable field identity and preserved.

**Reason:** Placeholder skeletons need a deterministic label contract before numeric extraction, and multiple copies of executable trade logic can silently diverge. Atomic labels make mandatory audit coverage predictable; one authoritative matrix keeps investment execution coherent without weakening current-action summaries or source evidence.

**Scope boundary:** Execution telemetry was explicitly excluded by user scope. No telemetry fields, logging, counters, or runtime instrumentation were added.

**Verification:** The canonical template and migrated META report pass `recognize`; the canonical fixture and META report pass lint; the regenerated META manifest remains version 4 with 25/63 selected cells (39.68%), and verdict reconstruction returns PASS with all 25 outcomes preserved.

### Batch 8 — Confirmed review corrections

**Change:**

- Replaced the duplicated recognition matcher with one `classification_matches` authority shared by extraction and recognition. Recognition no longer discards unrecognized rows after mandatory coverage is complete; `当前报价` remains a line-numbered failure, and no-space composite labels such as `当前价格及市值` are ambiguous.
- Limited matrix masking to the canonical table lines, so rules under later level-4 headings remain visible to lint. Expanded conservative rule detection to portfolio-specific threshold actions such as `价格低于 $8：加仓`, while excluding company/competitor asset-sale prose without portfolio context.
- Restricted N/A to Buy/Add and required executable non-N/A coverage for price, valuation, operating, thesis-break plus Hold/Reduce/Sell. An all-N/A matrix now fails.
- Added a subprocess contract test proving `scripts/new_report.py` automatically recognizes a valid generated skeleton and deletes the output on recognition failure. Removed the redundant standalone template-recognition CI command because the unit contract now exercises that path.
- Clarified generated versus manually created/copied skeleton workflows, converted the methodology's second action table into a non-executable price-range summary, corrected the module count to 10, and normalized `Hold-Index` spelling in touched contract documentation.
- Normalized the remaining runtime verdict vocabulary in README, the OpenAI agent prompt, and methodology to the sole canonical set `Buy / Hold-Index / Watchlist / Avoid`. `Avoid-Chase` is no longer a rating; chase risk is stated separately. Added an explicit runtime-file allowlist regression that rejects known obsolete verdict lists without scanning reports or historical changelog entries.

**Reason:** Review found fail-open recognition cleanup, hidden post-matrix rules, insufficient N/A execution guarantees, a competitor-prose false-positive risk, contradictory generator/contract documentation, and stale verdict terminology that could imply a fifth rating. These corrections close those exact gaps without changing the report decision or manifest-v4 extraction contract.

## 2026-07-24

### Change

- Limited `本次财报改变了什么 / 没有改变什么` to explicit latest-earnings update reports.
- Restored ordinary full-report `Key Forces` to business model, value drivers, and the 1-3 variables that determine intrinsic value.
- Updated the canonical template and lint rules so ordinary full reports no longer need fake earnings-update bullets.

### Reason

A general company initiation report should not pretend to be an earnings update. The old template and lint gate forced irrelevant wording and weakened the analytical focus of `Key Forces`.

### Verification

- `python3 scripts/report_lint.py --self-test`
- `python3 scripts/report_lint.py --fixtures tests/fixtures`
- `python3 /Users/muskxiang/.bg-agent/config-with-app/skills/skill-creator/scripts/quick_validate.py .`

## 2026-06-30

### Change

- Added prior-report delta requirements to `SKILL.md` and `references/report-contract.md`.
- Added strict `Hold-Index` action boundaries so it cannot read like Buy-lite.
- Added confidence cap when current price, 10Y yield, or peer valuation depends on unconfirmed Tier 2 market data.
- Added 403 / blocked IR fallback guidance: use regulator archives first and record extraction failures.
- Extended `scripts/report_lint.py` to fail non-Buy reports that use buy-like language without an observation-only qualifier.
- Extended `scripts/report_lint.py` to require a prior-report delta section when `previous_report` or prior-report language is present.

### Reason

The 2026-06-29 CME report review found that the original draft could be read as a soft Buy despite a `Hold-Index` rating. It also showed that the most useful part of a rerun was the explicit comparison against the previous report, and that Tier 2 market data should not inherit high confidence from otherwise strong SEC filing evidence.

### Verification

- `python3 scripts/report_lint.py --self-test`
- `python3 scripts/report_lint.py "/Users/haoshifasheng/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/股票/CME/CME-CME Group-华尔街式分析报告-2026-06-29.md"`
- `python3 /Users/haoshifasheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/haoshifasheng/.agents/skills/wall-street-equity-research`

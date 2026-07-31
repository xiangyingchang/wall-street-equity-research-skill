# Wall Street Equity Research Skill Change Log

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

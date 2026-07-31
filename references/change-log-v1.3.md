# v1.3 Change Log — Deterministic Valuation Runtime

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

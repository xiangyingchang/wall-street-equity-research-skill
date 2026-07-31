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

This file is staged separately because the existing monolithic `references/change-log.md` must be prepended during final integration without discarding historical entries.

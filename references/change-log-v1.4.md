# v1.4 Change Log — Deterministic EPS Bridge and Fact-Based Actions

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

### Verification target

- `python3 -m py_compile scripts/*.py`
- `python3 -m unittest tests.test_valuation_runtime`
- `python3 -m unittest tests.test_valuation_consistency`
- `python3 -m unittest discover -s tests`
- `python3 scripts/report_lint.py --self-test`
- `python3 scripts/report_lint.py --fixtures tests/fixtures`
- `git diff --check`
- Meta EPS Bridge vector: `2750 × 35% × (1-18%) ÷ 25.7 = 30.7101`
- Meta action vector: TTM margin `38.1%`, Reduce threshold `<35%` → Reduce false; with no other triggered rule → `REVIEW`

### Integration

After the full validation suite passes, prepend this entry to `references/change-log.md`, delete `references/change-log-v1.4.md`, and mark `PRD-deterministic-bridge-action-v1.4.md` as completed with the final test counts.

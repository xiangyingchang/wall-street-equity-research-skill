# v2.0 Change Log — Single-Source Report Compiler

## 2026-08-01

### Planned change

- Replace Markdown-first generation with a single `report-spec-v2` JSON source of truth.
- Add one deterministic compiler that generates Markdown, Bundle, and Verification Manifest.
- Remove Legacy Compatibility Tables from all new reports.
- Add typed global/scenario assumptions and reject cross-scenario references.
- Add mode-specific Revenue assumptions (`guide_midpoint`, `guide_high`, `yoy`, `qoq`, `explicit`, `consensus`).
- Add complete Decision Policy covering valuation, operating, thesis-break, and optional portfolio constraints.
- Separate new-money action from existing-position action.
- Add valuation-based Reduce/Review enforcement for the “Hold = Buy” principle.
- Move tolerance and uncertainty entirely into typed facts/policy; hidden narrative adjustments fail.
- Add deterministic Payback runtime.
- Generate Price Zones from the same prices used by Action rules.
- Generate Verification Manifest from actual build results rather than report-authored PASS text.
- Add Meta end-to-end golden fixture and tamper-detection tests.
- Make v2 verification the path for new reports; retain v1.x checkers only for historical reports.

### Reason

v1.1-v1.5.1 progressively fixed arithmetic, provenance, runtime binding, ID references, period semantics, and action robustness, but the architecture still allowed Agent-authored duplication. The same economic concept could appear in Runtime output, a canonical table, a Legacy table, a price-zone table, and prose. This created repeated regressions despite each local checker being correct.

The root cause is that Markdown remained both an input and an output. v2 moves all editable analytical state into a typed Spec and treats Markdown as a compiled view.

### Success target

- one spec → one reproducible bundle → one report;
- no duplicated economic truth;
- no hand-copied runtime tables;
- no hidden uncertainty;
- no omitted valuation decision dimension;
- no Legacy tables;
- deterministic payback and price zones;
- end-to-end verification detects changes to Spec, Bundle, or Markdown.

### Integration

After implementation and validation:

1. replace this planned entry with exact implementation and test results;
2. prepend it below the title in `references/change-log.md`;
3. delete `references/change-log-v2.0.md`;
4. mark `PRD-single-source-report-compiler-v2.md` completed;
5. rerun full CI before merge.
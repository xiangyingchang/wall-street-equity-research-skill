# v2.1.2 Change Log — Reader-First Dual-Layer Renderer

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

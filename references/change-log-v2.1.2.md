# v2.1.2 Change Log — Reader-First Dual-Layer Renderer

## 2026-08-01

### Planned change

- Split the generated Markdown into a Reader Report and a separate Audit Appendix.
- Keep the Single-Source Compiler and all v2.1.1 evidence/value constraints unchanged.
- Move Build Manifest, Source Registry, Evidence Ledger, full Scenario Assumptions, Decision Policy, Claim-Evidence Matrix, and Verification out of the Reader Report.
- Render human-readable evidence labels instead of internal IDs in the Reader Report.
- Merge related claims into continuous prose instead of repeating a fixed claim/implication/evidence/confidence card pattern.
- Increase the density of compiler-owned key numbers in natural-language analysis.
- Generate and verify four artifacts: Reader Markdown, Audit Markdown, Bundle JSON, and Verification JSON.
- Add reader/audit hashes to Verification and tamper tests for both Markdown files.
- Add readability regression tests that block internal IDs and audit tables from the Reader Report while requiring them in the Audit Appendix.

### Reason

v2.1.1 is reliable but difficult to read. The main report gives implementation objects—hashes, IDs, registries, evidence roles, and verification tables—the same visual weight as the investment conclusion. The content is fragmented into dozens of small cards and the reader must reconstruct the investment argument from system output.

The fix is not to weaken evidence controls or return to hand-written Markdown. The fix is to separate the human communication layer from the machine audit layer while compiling both from the same Bundle.

### Scope boundary

- No valuation or decision-policy changes.
- No new research modules.
- No reduction in evidence, source, or numeric binding requirements.
- No Markdown-first editing.
- Audit information remains complete, but moves to a separate generated file.

### Verification target

- Reader Report contains all nine modules and key decision numbers.
- Reader Report contains no internal IDs, evidence-role tokens, hashes, or audit registries.
- Audit Appendix contains the complete audit structures.
- Reader Report stays within the configured readability line budget.
- Reader, Audit, Bundle, and Verification tampering all fail verification.
- Full test suite, self-tests, fixtures, and Meta end-to-end build/verify pass.

### Integration

After implementation and validation:

1. replace this planned entry with actual implementation and exact results;
2. prepend the finalized v2.1.2 entry to `references/change-log.md`;
3. delete `references/change-log-v2.1.2.md`;
4. mark `PRD-reader-first-dual-layer-renderer-v2.1.2.md` completed;
5. rerun CI before merge.

# v3.0 Change Log — Research Graph and Investment Debate

## 2026-08-01

### Planned change

- Add a structured Research Graph between Claims and Narrative.
- Add company-specific Investment Themes with observations, hypothesis, challenge, resolution, decision impact, and falsification.
- Add a formal Bull/Bear Investment Debate and Lead Adjudication.
- Add Sensitivity Explanation for the variables that dominate Base IRR and target-return price.
- Add a tool-agnostic multi-perspective research adapter inspired by AI Berkshire's independent analyst/team-lead workflow.
- Render Theme-based narrative in the Reader Report and full Research Graph in the Audit Appendix.
- Add quality gates for counter-evidence, positive/negative evidence reconciliation, debate completeness, adjudication references, and high-importance sensitivity drivers.
- Preserve the v2.1.2 single-source compiler, deterministic calculations, dual-layer renderer, and tamper detection.

### Reason

v2.1.2 is reliable and readable, but the report still behaves like a well-formatted sequence of Claims. It does not consistently explain causality, challenge its own thesis, adjudicate competing views, or identify which assumptions truly drive the decision. The missing layer is not another report template; it is a structured research process.

AI Berkshire demonstrates the value of independent perspectives, adversarial analysis, and a lead analyst who resolves conflicts. v3 adopts these process ideas without copying persona-based scoring or introducing runtime dependence on a specific multi-agent tool.

### Scope boundary

- No change to valuation formulas or decision policy.
- No return to Markdown-first editing.
- No requirement for a specific Agent framework.
- No automatic averaging of analyst views.
- No claim that structured debate guarantees economically correct assumptions.

### Verification target

- Meta fixture contains 3–5 company-specific Themes.
- Every Theme has observations, hypothesis, challenge, resolution, decision impact, and falsification.
- Challenges contain counter-evidence; resolutions reconcile both sides.
- Bull and Bear each contain at least three arguments.
- Adjudication references both Bull and Bear argument IDs.
- At least one high-importance sensitivity driver exists.
- Reader contains Theme narrative and Investment Debate without internal IDs.
- Audit contains full Research Graph.
- Graph/Reader/Audit/Bundle/Verification tampering fails.
- Full test suite and end-to-end build/verify pass.

### Integration

After implementation and independent code review:

1. replace this planned entry with actual changes and exact test results;
2. prepend the finalized v3.0 entry to `references/change-log.md`;
3. delete `references/change-log-v3.0.md`;
4. mark `PRD-research-graph-investment-debate-v3.md` completed;
5. rerun CI before merge.

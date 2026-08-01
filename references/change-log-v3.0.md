# v3.0 Change Log — Research Graph and Investment Debate

## 2026-08-01

### Change

- Added `report-spec-v3.0` and `report-bundle-v3.0`.
- Added a structured Research Graph:
  - Source → Fact → Observation → Hypothesis → Challenge → Resolution → Theme → Narrative → Decision.
- Added 3–5 company-specific `THEME-*` Investment Themes.
- Added `OBS-*` observations, evidence-bound hypotheses, strongest challenges, resolutions, decision impacts, and falsification conditions.
- Required counter-evidence in every challenge and positive/negative evidence reconciliation in every resolution.
- Added formal Bull/Bear Investment Debate:
  - at least three `ARG-*` arguments per side;
  - globally unique argument IDs;
  - Lead Adjudication with accepted and discounted IDs from both sides;
  - remaining uncertainty.
- Added `DRV-*` Sensitivity Explanation for the variables that dominate Base IRR and target-return price.
- Added a tool-agnostic multi-perspective workflow inspired by AI Berkshire:
  - business analyst;
  - financial analyst;
  - industry challenger;
  - risk assessor;
  - lead analyst.
- Added v3 Reader narrative:
  - Theme-based module 1;
  - strongest challenge and falsification for every Theme;
  - sensitivity explanation in valuation;
  - Bull vs Bear debate before final verdict.
- Added full Research Graph, Debate, and Sensitivity structures to Audit Appendix.
- Added independent v3 compiler, renderer, build, and verify pipeline.
- Upgraded `SKILL.md` to v3.0.0.
- Added Meta v3 fixture, graph contract, focused tests, and CI end-to-end validation.

### Reason

v2.1.2 was reliable and readable but still treated isolated Claims as the core research unit. It could state conclusions without consistently explaining causality, testing alternative explanations, adjudicating competing views, or identifying the model variables that control the decision.

v3 adds the missing research process layer while preserving the existing numeric truth and audit boundaries.

### What was learned from AI Berkshire

Adopted:

- independent analytical perspectives;
- adversarial Bull/Bear analysis;
- explicit anti-bias challenge;
- Lead Analyst adjudication rather than mechanical averaging;
- exact calculations remain separated from prose.

Not adopted:

- persona-based “master” scores;
- fixed famous-investor roles;
- dependency on a specific subagent framework;
- averaging conflicting opinions.

### Code review fixes

Independent review found and fixed:

- invalid Theme module links were not blocked;
- Bull and Bear could reuse the same Argument ID;
- Adjudication accepted and discounted sets could overlap;
- concise but valid graph implications were rejected by the older Claim length gate;
- Meta fixture referenced an undefined Bundle path;
- v3 compiler did not explicitly reject legacy schema input.

### Verification

GitHub Actions Validate run #271: PASS.

- Python syntax: PASS.
- financial rigor / report audit / report lint self-tests: PASS.
- lint fixtures: PASS.
- full unittest suite: **168 / 168 PASS**.
- v2.1.2 end-to-end regression: PASS.
- v3 Meta build and verify: PASS.
- Research Graph: 3 Themes, 6 Observations.
- Debate: 3 Bull arguments, 3 Bear arguments.
- Sensitivity: 3 Drivers, 2 High importance.
- Reader Theme narrative, Sensitivity, and Bull/Bear sections: PASS.
- Reader internal-ID exclusion: PASS.
- Audit full graph inclusion: PASS.
- Graph/Reader/Audit/Bundle/Verification tamper binding: PASS.

### Integration

PR #9 is stacked on the v2.1.2 branch. Before merge:

1. merge PR #8;
2. rebase or retarget PR #9 to main;
3. rerun complete CI;
4. prepend this entry to `references/change-log.md`;
5. delete `references/change-log-v3.0.md`;
6. preserve all historical entries.

# PRD: optimized-v3 Reader + V3-Fast Guardrails

## Baseline

- Baseline contract: `optimized-v3`, the historical 11-module research memo.
- Historical source preserved in the user's local skill archive as
  `SKILL.legacy-20260809.md`.
- The pre-migration active skill snapshot is maintained outside this Git
  repository so local rollback remains independent of the published branch.

## Goal

Keep V3's business-to-valuation-to-action reading rhythm while preventing the
three observed failure classes: hand-calculated dividend totals, ambiguous
per-share denominators, and mixed security/liquidity classifications.

## Default execution mode

`V3-Fast` is the default. It performs one data collection pass, one Evidence
Ledger, deterministic local valuation math, and a compact report lint. It does
not build a Research Graph, Spec, Bundle, multi-artifact Compiler, or Audit
Appendix.

`V3-Deep` is optional and should be used only for high-CapEx, conflicting-data,
material-earnings-change, or explicitly requested audit work.

## Single-source flow

```text
fresh sources -> Evidence Ledger -> V3 11-module Reader
                              \-> deterministic math + V3 lint
```

The guardrails must consume the same ledger and input vector as the report;
they must not repeat the research pass.

## Required guardrails

1. Calculate nominal and discounted payback with `valuation_math.py`.
2. Calculate multi-year after-tax dividends with the explicit sum command;
   never hand-fill the total.
3. Label market-cap shares separately from diluted EPS/FCF-share denominator.
4. Separate cash, marketable securities, non-marketable securities, restricted
   securities, debt, and lease liabilities.
5. Require source, date, unit, period, and confidence for key numbers.

## Non-goals

- Do not change the V3 rating vocabulary or 11-module order.
- Do not expose compiler IDs, graph nodes, bundle hashes, or verification
  metadata in the default Reader.
- Do not run a second provider or filing research pipeline merely to validate
  the first one.

## Acceptance criteria

- The active skill validates with `quick_validate.py`.
- `new_report.py --profile v3` creates the V3 11-module skeleton.
- `report_lint.py --profile v3` accepts a completed V3 report and rejects
  frontmatter, missing modules, missing dividend treatment, missing denominator
  disclosure, and missing three-scale payback rows.
- `valuation_math.py dividend-total` reproduces the five-year after-tax
  dividend calculation without manual arithmetic.
- The pre-migration snapshot remains byte-identical and the restore instructions
  remain available.

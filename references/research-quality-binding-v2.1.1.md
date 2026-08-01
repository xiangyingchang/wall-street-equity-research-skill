# Research Quality Binding v2.1.1

## Purpose

v2.1.1 keeps the v2 Single-Source Compiler and v2.1 Research Layer, but closes four trust gaps: prose could not embed compiler-owned values, evidence had no logical role, Bundle paths were fragile dot strings, and quality/verification flags were hard-coded.

## Value Binding

Use `text_template` or `claim_template` with `value_refs`:

```json
{
  "text_template": "Base IRR 为 {base_irr}，低于目标回报 {target_return}。",
  "value_refs": {
    "base_irr": {"path": "/decision/valuation/base_irr", "format": "percent"},
    "target_return": {"path": "/decision/valuation/target_return", "format": "percent"}
  }
}
```

Rules:

- paths are JSON Pointer;
- placeholders and `value_refs` keys match exactly;
- supported formats are money, percent, multiple, number, integer, and text;
- unresolved or unused placeholders fail;
- free text still cannot contain unbound currency, percentage, multiple, threshold, or large numeric literals.

## Evidence Roles

Evidence refs use:

```json
{"ref": "FACT-Q2-26-FCF", "role": "supports"}
{"ref": "SRC-META-Q2-2026", "role": "context"}
{"ref": "BUNDLE:/scenarios/bull/returns/irr/irr_pct", "role": "counter_evidence"}
```

Allowed roles:

- `supports` — directly supports the claim;
- `context` — supplies background or scope;
- `counter_evidence` — challenges or limits the claim.

Every claim requires at least one supports ref.

## Source Scope

Each Fact category must be covered by at least one referenced Source scope. Revenue facts need revenue scope, operating-income facts need operating-income scope, EPS facts need EPS scope, FCF facts need FCF scope, and price/share facts need corresponding market-data scope.

## Risk Quality

Risk confidence must be low, medium, or high. Risk ranks must be unique and exactly consecutive from one through the number of risks.

## Dynamic Research Quality

The compiler calculates and stores:

- module count;
- claim count;
- supporting evidence count;
- bound value count;
- source count;
- numeric-reference safety.

Markdown and Verification render from this object. They may not contain fixed PASS strings independent of the validator result.

## Markdown Safety

All table cells escape pipes and line breaks before rendering.

## Verification

`report_pipeline_v2.py verify` recompiles Spec, Bundle, Markdown, and Verification and compares all derived artifacts. Any manually edited quality status, value, evidence role, or report text fails verification.

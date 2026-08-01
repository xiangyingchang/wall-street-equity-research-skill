# v2.1.1 Change Log — Research Quality Binding

## 2026-08-01

### Planned change

- Add `text_template + value_refs` so research prose can embed compiler-owned values without handwritten numbers.
- Replace dot-separated Bundle paths with JSON Pointer paths.
- Upgrade evidence refs to typed `{ref, role}` objects with `supports`, `context`, and `counter_evidence`.
- Require at least one supporting evidence ref for each key claim.
- Compute Research Quality results dynamically and render Verification from those results.
- Validate risk confidence and rank uniqueness/continuity.
- Validate Source scope against Fact metric category.
- Escape Markdown table content safely.
- Add end-to-end and negative tests for value binding, evidence roles, path safety, source scope, dynamic verification, and table escaping.

### Reason

v2.1 restored complete research structure, but its prose still could not directly use core numbers; evidence only needed to exist rather than carry an explicit logical role; several quality flags were hard-coded; dot paths failed for decimal keys; and some validation boundaries remained weak. v2.1.1 turns the Research Layer from a structured outline into a numerically integrated and honestly verified report layer without changing the Single-Source Compiler architecture.

### Integration

After implementation and validation:

1. replace this planned entry with exact implementation and test results;
2. prepend it below the title in `references/change-log.md`;
3. delete `references/change-log-v2.1.1.md`;
4. mark `PRD-research-quality-binding-v2.1.1.md` completed;
5. rerun full CI before merge.

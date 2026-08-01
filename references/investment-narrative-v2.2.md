# Investment Narrative Authoring Guide v2.2

## Purpose

The Narrative Layer turns verified facts and scenario outputs into a causal, company-specific investment argument without allowing prose to create a second numeric truth.

The flow is:

```text
Source → Fact → Claim → Theme → Debate → Reader Report
```

Claims remain atomic and auditable. Themes explain how several claims interact. Debate exposes the variable on which reasonable investors disagree. The Reader Renderer converts these structures into continuous prose.

## Core Theme

Every report requires 3–5 Themes covering:

- business / moat;
- capital allocation / financial mechanism;
- valuation / opportunity cost.

Each Theme contains:

```json
{
  "id": "THEME-CAPEX-RETURNS",
  "category": "capital",
  "title": "Company-specific title",
  "thesis": {"text_template": "...", "value_refs": {}, "evidence_refs": [], "confidence": "medium"},
  "mechanism": [
    {"claim": "...", "evidence_refs": [], "confidence": "high", "implication": "..."},
    {"claim": "...", "evidence_refs": [], "confidence": "medium", "implication": "..."}
  ],
  "counter_case": {"text": "...", "evidence_refs": [], "confidence": "medium"},
  "investment_implication": "...",
  "validation_signals": ["...", "..."]
}
```

A good Theme answers six questions:

1. What is the judgment?
2. Through what mechanism does it affect earnings or cash flow?
3. Which facts support it?
4. What evidence points the other way?
5. What does it mean for valuation or position sizing?
6. What future observation would strengthen or invalidate it?

## Company specificity

Maintain `company_entities` with company, product, platform, segment, technology, and competitor names.

Generic wording is insufficient:

```text
The company has network effects, data, ecosystem, and capital.
```

Company-specific wording is acceptable:

```text
Instagram and Reels expand content inventory; Meta's recommendation and advertiser feedback loop converts that inventory into monetization.
```

At least one company entity must appear in each Theme's title, thesis, mechanism, or implication.

## Adversarial debate

Every report contains Bull, Base, and Bear Cases. This is inspired by adversarial research teams: independent commercial, financial, competitive, and risk perspectives are synthesized only after their disagreement is explicit.

Each Case states:

- thesis;
- one Compiler-owned value anchor;
- path to win;
- earliest failure signal.

The debate concludes with one `key_disagreement`—the variable that most clearly separates Bull and Bear.

Do not write three cosmetic versions of the same paragraph. A valid debate changes assumptions, mechanism, and falsification signal.

## Causal financial bridge

The financial section must connect four steps:

```text
operating change
→ cost or capital driver
→ margin / free-cash-flow effect
→ valuation consequence
```

Example:

```text
Revenue remained strong
→ AI infrastructure and data-center spending accelerated
→ depreciation and Capex reduced margin and FCF conversion
→ historical peak FCF is not an appropriate valuation base
```

At least one quarterly comparison must use `value_refs`. The cost driver must cite primary evidence or be explicitly marked lower confidence.

## Mirror test

The final five statements answer:

1. What is the business?
2. What is the moat?
3. What does the current price imply?
4. What is the largest risk?
5. What is the action?

The test is intentionally short. If the investment cannot be explained in five precise statements, the earlier analysis has not identified the real decision variables.

## Reader-writing rules

- Do not repeat the one-page verdict verbatim in Overview.
- Use Theme sections to explain mechanisms, not to restate headlines.
- Use the Bull/Base/Bear section to reveal disagreement, not to perform generic balance.
- Prefer one paragraph with a causal chain over four isolated claim cards.
- Place numbers inside the argument through `value_refs`.
- Include counter-case and validation signals near the Theme, not buried in an appendix.
- Keep internal IDs and evidence roles in Audit only.

## Narrative Quality checks

The Compiler verifies:

- 3–5 complete Themes;
- business/capital/valuation coverage;
- at least two mechanism claims per Theme;
- counter-evidence coverage;
- at least two validation signals per Theme;
- company-entity coverage;
- Bull/Base/Bear completeness;
- causal bridge completeness;
- exactly five Mirror Test statements;
- Theme-title redundancy;
- bound numeric argument density.

Passing these checks does not prove that an investment thesis is economically correct. It proves that the thesis is explicit, evidence-bound, company-specific, adversarial, causal, falsifiable, and reproducible.

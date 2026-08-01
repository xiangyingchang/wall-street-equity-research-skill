# Staged Change Log — v3.1

## 2026-08-01 — Data → Reasoning → Decision Reader

**Status:** implementation complete; remote CI pending.

**Planned change:** require source URLs and reject placeholder sources; validate homogeneous TTM units; replace the fixed FCF operating gate with company-specific metric references; add explicit portfolio context and separate candidate from executable existing-position actions; require a prior-report delta with runtime IRR recalculation; make Graph cardinality dynamic; rewrite the v3 Reader around one Action Matrix, the three original investment principles, visible Base assumptions, natural Theme synthesis, compact debate/sensitivity, and clickable sources; derive verification statuses from bundle checks and run the v3.1-aware report lint profile inside the Pipeline.

**Reason:** v3.0 improved auditability but its fixed Graph-to-prose mapping made the report repetitive and indirect, while missing URLs, hidden assumptions, a hard-coded FCF gate, and context-free `REDUCE` could still produce false confidence.

**Scope boundary:** preserve v2/v2.1 compatibility, current valuation/payback math, the nine-module methodology, Reader/Audit separation, and the rule that generated artifacts are compiler-owned. No implicit FX conversion or invented portfolio data.

**Verification:** Python syntax PASS; all three self-tests and lint fixtures PASS; 184/184 unittests PASS; v2.1.2 and v3.1 build/verify PASS; v3.1 integrated report lint PASS; skill validation and diff check PASS. The META fixture intentionally leaves portfolio weights unknown, so data quality and portfolio context correctly report REVIEW while every artifact/integrity check passes.

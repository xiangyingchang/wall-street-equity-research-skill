#!/usr/bin/env python3
"""Apply the valuation-consistency upgrade on the feature branch.

This migration script is intentionally temporary. The GitHub Actions job removes it
before committing the resulting product changes.
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"anchor not found in {path}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


VALUATION_REFERENCE = dedent(r'''\
# Valuation Consistency

This reference is authoritative for valuation-basis identity, adjustment bridges,
scenario math, and the boundary between fair value and an executable buy price.
It complements `data-validation.md`: data validation checks evidence provenance;
this file checks whether the report uses that evidence coherently.

## Core rule

A report may be conservative once. It may not stack a pessimistic earnings base,
a pessimistic multiple, and a second unexplained discount and then call the result
"fair value". Separate these concepts:

- **Fair value:** the value implied by one explicit scenario before a safety discount.
- **Buy price:** fair value after one explicit safety-margin discount.
- **Stress price:** the value of a separate Bear/Stress scenario, not another name for
  the Base-case buy price.

When evidence cannot distinguish two nearby prices reliably, output a range and lower
confidence. Do not manufacture false precision to satisfy a template.

## 1. Valuation Basis Registry

Module 4 must contain exactly one table with these columns:

| Basis ID | Metric | Value | Period | Adjustments | Use |
|---|---|---:|---|---|---|

Rules:

1. `Basis ID` is unique and stable within the report.
2. Every EPS/FCF value used in a scenario references one registered Basis ID.
3. `Adjustments` is `None` or a comma-separated list of Adjustment IDs.
4. A normalized or adjusted basis without a documented bridge is invalid.
5. Bear, Base, and Bull are scenario labels. Do not rename the Bear basis as
   "mid-cycle" or "central" merely to make a low target look objective.
6. The `Use` column states whether the basis supports reported valuation, Base case,
   Bear case, Bull case, payback pressure test, or another explicit purpose.

## 2. One-off Adjustment Ledger

If any report text uses `adjusted`, `normalized`, `core`, `中枢`, `调整后`, or
`正常化` for EPS, FCF, profit, or margin, module 2 must include:

| Adjustment ID | Period | Item | Pre-tax/after-tax | Cash/non-cash | Repeatability | Per-share impact | Treatment | Source |
|---|---|---|---|---|---|---:|---|---|

Rules:

- Tax charges and later tax benefits from the same event must be treated symmetrically.
- Legal and restructuring expenses are not automatically non-recurring. State their
  cash character and recurrence probability.
- `Per-share impact` may be a range or `Unclear`; invented precision is worse than a
  declared gap.
- A report may decline to adjust an item. Record that decision instead of silently
  omitting it.

## 3. Scenario Valuation

Module 4 must contain:

| Scenario | Basis ID | Metric value | Multiple | Fair value | Safety margin | Buy price | Key assumptions |
|---|---|---:|---:|---:|---:|---:|---|

The arithmetic is binding:

```text
Fair value = Metric value × Multiple
Buy price = Fair value × (1 - Safety margin)
```

Tolerance is 2% for displayed rounding. Scenario fair values should normally satisfy
`Bear <= Base <= Bull`. Any exception requires an explicit explanation beside the
table and must not be hidden by relabeling scenarios.

The First-Page Verdict and module 8 price zones must be derived from this table. They
must not introduce a second independent set of price boundaries.

## 4. Capex / Owner Earnings Bridge

For high-capex companies, distinguish at least:

| Item | Value/range | Period | Evidence | Confidence |
|---|---:|---|---|---|
| Reported OCF |  |  |  |  |
| Reported Capex |  |  |  |  |
| Reported FCF |  |  |  |  |
| Maintenance Capex |  |  |  |  |
| Growth Capex |  |  |  |  |
| Strategic / AI Capex |  |  |  |  |
| Owner Earnings / Normalized FCF |  |  |  |  |

Missing company disclosure may be recorded as `Unclear`. Do not annualize one quarter
of FCF and present it as durable earning power without a cash bridge and explicit
seasonality/procurement analysis.

## 5. Three-model valuation triangle

The 10-year payback remains mandatory, but it is a **pressure test**, not a complete
DCF and not a sole veto. The default decision synthesis is:

1. **5-year scenario IRR (primary):** Bear/Base/Bull operating assumptions, exit
   multiple, dividends/buybacks, and dilution.
2. **Reverse expectations / reverse DCF:** what growth, margin, and capital intensity
   are implied by today's price.
3. **10-year payback pressure test:** whether the valuation requires physically
   implausible compounding under a deliberately harsh zero-terminal-value lens.

Suggested synthesis weights are 50% / 30% / 20%; they are judgment aids, not a fake
weighted-score machine. A failed payback test raises the hurdle and lowers confidence,
but does not by itself force Reduce/Sell when the other models and business evidence
support an adequate expected IRR.

## 6. Opportunity cost

Compare **expected shareholder total return / IRR** with the relevant bond, index, and
high-quality alternative assets. Do not require a growing company's current FCF yield
to mechanically exceed `10Y Treasury ×2`; that confuses a current yield with a total
return hurdle. Keep `10Y ×2` as the user's required-return benchmark when appropriate.

## 7. Action Matrix

Operating triggers should normally use TTM or consecutive-quarter evidence. A single
quarter of capex timing or working-capital noise should not automatically force a
large position change. Sell remains a thesis-break action; threshold misses are
warnings unless the report explains why they constitute a durable thesis break.

## 8. Required semantic audit

Before `report_lint.py` and `report_audit.py`, run:

```bash
python3 scripts/valuation_consistency.py /path/to/report.md
```

The checker validates table contracts, Basis/Adjustment references, scenario math,
scenario ordering, basic PE/FCF-yield recomputation, and several high-confidence prose
contradictions. Warnings require human review; errors block delivery.
''')


CHECKER = dedent(r'''\
#!/usr/bin/env python3
"""Semantic valuation consistency checks for equity-research Markdown reports."""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Finding:
    level: str
    message: str


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _tables(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    result: list[dict[str, object]] = []
    i = 0
    while i + 1 < len(lines):
        header = lines[i].strip()
        sep = lines[i + 1].strip()
        if header.startswith("|") and sep.startswith("|") and re.fullmatch(r"\|?[\s:|-]+\|?", sep):
            headers = [cell.strip() for cell in header.strip("|").split("|")]
            rows: list[list[str]] = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[j].strip().strip("|").split("|")]
                if len(cells) == len(headers):
                    rows.append(cells)
                j += 1
            result.append({"headers": headers, "rows": rows, "line": i + 1})
            i = j
        else:
            i += 1
    return result


def _find_table(tables: Iterable[dict[str, object]], required: set[str]) -> dict[str, object] | None:
    for table in tables:
        headers = {_norm(str(h)) for h in table["headers"]}  # type: ignore[index]
        if required <= headers:
            return table
    return None


def _decimal(raw: str) -> Decimal | None:
    value = raw.replace(",", "").replace("$", "").replace("¥", "").replace("€", "")
    value = value.replace("×", "x").replace("倍", "x").strip()
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return None


def _percent(raw: str) -> Decimal | None:
    number = _decimal(raw)
    if number is None:
        return None
    return number / Decimal(100) if "%" in raw else number


def _rows_as_dict(table: dict[str, object]) -> list[dict[str, str]]:
    headers = [str(h) for h in table["headers"]]  # type: ignore[index]
    return [dict(zip(headers, [str(c) for c in row])) for row in table["rows"]]  # type: ignore[index]


def _get(row: dict[str, str], name: str) -> str:
    target = _norm(name)
    for key, value in row.items():
        if _norm(key) == target:
            return value
    return ""


def _ledger_values(tables: list[dict[str, object]]) -> dict[str, Decimal]:
    values: dict[str, Decimal] = {}
    for table in tables:
        headers = {_norm(str(h)) for h in table["headers"]}  # type: ignore[index]
        if not ({"数据项", "数值"} <= headers or {"item", "value"} <= headers):
            continue
        for row in _rows_as_dict(table):
            label = _get(row, "数据项") or _get(row, "item")
            raw = _get(row, "数值") or _get(row, "value")
            number = _decimal(raw)
            if label and number is not None:
                values[_norm(label)] = number
    return values


def _lookup(values: dict[str, Decimal], patterns: list[str]) -> Decimal | None:
    for label, value in values.items():
        if any(re.search(pattern, label, re.I) for pattern in patterns):
            return value
    return None


def validate_text(text: str) -> list[Finding]:
    findings: list[Finding] = []
    tables = _tables(text)

    basis = _find_table(tables, {"basis id", "metric", "value", "period", "adjustments", "use"})
    adjustment = _find_table(
        tables,
        {"adjustment id", "period", "item", "pre-tax/after-tax", "cash/non-cash", "repeatability", "per-share impact", "treatment", "source"},
    )
    scenario = _find_table(
        tables,
        {"scenario", "basis id", "metric value", "multiple", "fair value", "safety margin", "buy price", "key assumptions"},
    )
    capex_bridge = _find_table(tables, {"item", "value/range", "period", "evidence", "confidence"})

    if basis is None:
        findings.append(Finding("ERROR", "missing Valuation Basis Registry table"))
    if adjustment is None:
        findings.append(Finding("ERROR", "missing One-off Adjustment Ledger table"))
    if scenario is None:
        findings.append(Finding("ERROR", "missing Scenario Valuation table"))
    if capex_bridge is None:
        findings.append(Finding("ERROR", "missing Capex / Owner Earnings Bridge table"))

    basis_ids: set[str] = set()
    adjustment_ids: set[str] = set()
    if adjustment is not None:
        for row in _rows_as_dict(adjustment):
            adjustment_id = _get(row, "Adjustment ID").strip()
            if adjustment_id and not adjustment_id.upper().startswith("TODO"):
                if adjustment_id in adjustment_ids:
                    findings.append(Finding("ERROR", f"duplicate Adjustment ID: {adjustment_id}"))
                adjustment_ids.add(adjustment_id)

    if basis is not None:
        for row in _rows_as_dict(basis):
            basis_id = _get(row, "Basis ID").strip()
            if not basis_id or basis_id.upper().startswith("TODO"):
                continue
            if basis_id in basis_ids:
                findings.append(Finding("ERROR", f"duplicate Basis ID: {basis_id}"))
            basis_ids.add(basis_id)
            refs = _get(row, "Adjustments").strip()
            if refs and _norm(refs) not in {"none", "n/a", "na", "无"}:
                for ref in re.split(r"[,，;；\s]+", refs):
                    if ref and ref not in adjustment_ids:
                        findings.append(Finding("ERROR", f"Basis {basis_id} references unknown Adjustment ID: {ref}"))

    scenario_values: dict[str, Decimal] = {}
    if scenario is not None:
        for row in _rows_as_dict(scenario):
            name = _get(row, "Scenario").strip()
            basis_id = _get(row, "Basis ID").strip()
            metric = _decimal(_get(row, "Metric value"))
            multiple = _decimal(_get(row, "Multiple"))
            fair = _decimal(_get(row, "Fair value"))
            margin = _percent(_get(row, "Safety margin"))
            buy = _decimal(_get(row, "Buy price"))
            if not name or name.upper().startswith("TODO"):
                continue
            if basis_id not in basis_ids:
                findings.append(Finding("ERROR", f"Scenario {name} references unknown Basis ID: {basis_id}"))
            if None in {metric, multiple, fair, margin, buy}:
                findings.append(Finding("ERROR", f"Scenario {name} has an unparseable numeric field"))
                continue
            assert metric is not None and multiple is not None and fair is not None and margin is not None and buy is not None
            expected_fair = metric * multiple
            expected_buy = fair * (Decimal(1) - margin)
            fair_error = abs(fair - expected_fair) / max(abs(expected_fair), Decimal("0.01"))
            buy_error = abs(buy - expected_buy) / max(abs(expected_buy), Decimal("0.01"))
            if fair_error > Decimal("0.02"):
                findings.append(Finding("ERROR", f"Scenario {name} fair value is not Metric value × Multiple"))
            if buy_error > Decimal("0.02"):
                findings.append(Finding("ERROR", f"Scenario {name} buy price is not Fair value × (1 - Safety margin)"))
            if buy > fair:
                findings.append(Finding("ERROR", f"Scenario {name} buy price exceeds fair value"))
            scenario_values[_norm(name)] = fair

    def scenario_value(pattern: str) -> Decimal | None:
        for name, value in scenario_values.items():
            if re.search(pattern, name, re.I):
                return value
        return None

    bear = scenario_value(r"bear|悲观|压力|stress")
    base = scenario_value(r"base|基准|中性")
    bull = scenario_value(r"bull|乐观")
    if bear is not None and base is not None and bear > base:
        findings.append(Finding("ERROR", "Bear fair value exceeds Base fair value"))
    if base is not None and bull is not None and base > bull:
        findings.append(Finding("ERROR", "Base fair value exceeds Bull fair value"))

    ledger = _ledger_values(tables)
    price = _lookup(ledger, [r"当前价格", r"当前股价", r"current price"])
    eps = _lookup(ledger, [r"ttm eps"])
    fcf_share = _lookup(ledger, [r"ttm fcf/share", r"ttm fcf per share"])
    pe = _lookup(ledger, [r"ttm pe", r"p/e"])
    fcf_yield = _lookup(ledger, [r"fcf yield", r"自由现金流收益率"])
    if price is not None and eps not in {None, Decimal(0)} and pe is not None:
        expected = price / eps  # type: ignore[operator]
        if abs(pe - expected) / expected > Decimal("0.03"):
            findings.append(Finding("ERROR", "Evidence Ledger TTM PE does not reconcile to price / TTM EPS"))
    if price is not None and fcf_share is not None and fcf_yield is not None:
        expected = fcf_share / price * Decimal(100)
        shown = fcf_yield if fcf_yield > Decimal(1) else fcf_yield * Decimal(100)
        if abs(shown - expected) > Decimal("0.20"):
            findings.append(Finding("ERROR", "Evidence Ledger FCF yield does not reconcile to FCF/share / price"))

    for match in re.finditer(r"(?P<pct>\d+(?:\.\d+)?)\s*%[^\n]{0,35}(?:翻倍|double)|(?:翻倍|double)[^\n]{0,35}(?P<pct2>\d+(?:\.\d+)?)\s*%", text, re.I):
        raw = match.group("pct") or match.group("pct2")
        if raw and Decimal(raw) < Decimal(90):
            findings.append(Finding("ERROR", f"'翻倍/double' conflicts with stated growth of {raw}%"))

    for match in re.finditer(r"(?P<a>\d+(?:\.\d+)?)[^\n]{0,25}(?:beat|超过|高于)[^\n]{0,25}(?:上限|upper)[^\n]{0,10}(?P<b>\d+(?:\.\d+)?)", text, re.I):
        if Decimal(match.group("a")) < Decimal(match.group("b")):
            findings.append(Finding("ERROR", f"stated beat/above upper bound conflicts with {match.group('a')} < {match.group('b')}"))

    if re.search(r"(?:单季|季度|Q[1-4])[^\n]{0,80}(?:FCF|自由现金流)[^\n]{0,80}(?:年化|annualized)", text, re.I):
        findings.append(Finding("WARNING", "single-quarter FCF is annualized; verify seasonality, procurement timing, and cash adjustments"))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    text = args.report.read_text(encoding="utf-8")
    findings = validate_text(text)
    for finding in findings:
        print(f"{finding.level}: {finding.message}")
    errors = [finding for finding in findings if finding.level == "ERROR"]
    if errors:
        print(f"FAIL: {len(errors)} valuation-consistency error(s)")
        return 1
    warnings = sum(finding.level == "WARNING" for finding in findings)
    print(f"PASS: valuation consistency ({warnings} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''')


TEST = dedent(r'''\
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


GOOD = """
# TEST Test — 华尔街式分析报告

## Evidence Ledger

| 数据项 | 数值 | 日期 | 来源/层级 | 口径 | 可信度 |
|---|---:|---|---|---|---|
| 当前价格 | $100 | 2026-07-31 | Tier 1 | close | 高 |
| TTM EPS | $5 | 2026-07-31 | Tier 1 | TTM | 高 |
| TTM PE | 20x | 2026-07-31 | calc | price/EPS | 高 |
| TTM FCF/share | $4 | 2026-07-31 | calc | TTM | 高 |
| FCF yield | 4% | 2026-07-31 | calc | FCF/share/price | 高 |

## 2. 财务剖析 Financial Autopsy

### One-off Adjustment Ledger

| Adjustment ID | Period | Item | Pre-tax/after-tax | Cash/non-cash | Repeatability | Per-share impact | Treatment | Source |
|---|---|---|---|---|---|---:|---|---|
| ADJ-1 | FY2026-Q2 | legal | pre-tax | cash | medium | $0.20 | exclude 50% | filing |

## 4. 极限估值 + 10 年回本数学审判

### Valuation Basis Registry

| Basis ID | Metric | Value | Period | Adjustments | Use |
|---|---|---:|---|---|---|
| EPS-BEAR | EPS/share | $4 | FY+1 | None | Bear |
| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-1 | Base |
| EPS-BULL | EPS/share | $6 | FY+1 | ADJ-1 | Bull |

### Scenario Valuation

| Scenario | Basis ID | Metric value | Multiple | Fair value | Safety margin | Buy price | Key assumptions |
|---|---|---:|---:|---:|---:|---:|---|
| Bear | EPS-BEAR | $4 | 15x | $60 | 20% | $48 | weak growth |
| Base | EPS-BASE | $5 | 20x | $100 | 15% | $85 | normal growth |
| Bull | EPS-BULL | $6 | 25x | $150 | 10% | $135 | strong growth |

### Capex / Owner Earnings Bridge

| Item | Value/range | Period | Evidence | Confidence |
|---|---:|---|---|---|
| Reported OCF | $100亿 | FY2026 | filing | High |
| Reported Capex | $50亿 | FY2026 | filing | High |
| Reported FCF | $50亿 | FY2026 | calc | High |
| Maintenance Capex | Unclear | FY2026 | no disclosure | Low |
| Growth Capex | Unclear | FY2026 | no disclosure | Low |
| Strategic / AI Capex | Unclear | FY2026 | no disclosure | Low |
| Owner Earnings / Normalized FCF | Unclear | FY2026 | no disclosure | Low |
"""


class ValuationConsistencyCliTests(unittest.TestCase):
    def run_check(self, text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "scripts/valuation_consistency.py", str(path)],
                check=False,
                text=True,
                capture_output=True,
            )

    def test_good_report_passes(self) -> None:
        result = self.run_check(GOOD)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bad_scenario_math_fails(self) -> None:
        result = self.run_check(GOOD.replace("| Base | EPS-BASE | $5 | 20x | $100 |", "| Base | EPS-BASE | $5 | 20x | $120 |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fair value", result.stdout)

    def test_unknown_basis_fails(self) -> None:
        result = self.run_check(GOOD.replace("| Bear | EPS-BEAR |", "| Bear | EPS-MISSING |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown Basis ID", result.stdout)

    def test_fcf_yield_reconciliation_fails(self) -> None:
        result = self.run_check(GOOD.replace("| FCF yield | 4% |", "| FCF yield | 2% |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FCF yield", result.stdout)

    def test_adjustment_reference_fails(self) -> None:
        result = self.run_check(GOOD.replace("| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-1 |", "| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-X |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown Adjustment ID", result.stdout)


if __name__ == "__main__":
    unittest.main()
''')


TEMPLATE = dedent(r'''\
# {{ticker}} {{company}} — 华尔街式分析报告

> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；机会成本=对应计价货币 10Y 国债 ×2 + 相关高质量替代资产。

## First-Page Verdict

| 项目 | 结论 |
|---|---|
| 最终评级 | {{verdict}} |
| 当前动作 | {{action}} |
| 核心理由 | TODO |
| 当前价格是否值得重新买入 | TODO |
| 相对机会成本是否胜出 | TODO（比较预期总回报/IRR，不机械比较当期 FCF yield） |
| 10 年回本压力测试 | TODO（压力测试，不是单独否决器） |
| 公允价值 / 买入区间 / 压力价格 | TODO（分别列示，不得混称） |
| 最大风险 | TODO |
| 需人工复核的数据 | TODO |

### Researchability Record

| 项目 | 结论 |
|---|---|
| 报告类型 | 常规报告 / 最新财报更新（TODO） |
| 信息丰富度 | A / B / C（TODO） |
| AI 研究置信度 | 高 / 中 / 低（受信息丰富度约束） |
| 投资确定性 | 高 / 中 / 低（独立的商业判断） |
| 首页决策置信度 | 高 / 中 / 低（由证据与 thesis 保守导出） |
| 差异说明 | 仅当两者表面不一致时，用一句话解释 TODO |

## Evidence Ledger

| 数据项 | 数值 | 日期 | 来源/层级 | 口径 | 可信度 |
|---|---:|---|---|---|---|
| 当前价格 | TODO | {{date}} | TODO | TODO | TODO |
| 总股本 | TODO | {{date}} | TODO | TODO | TODO |
| 市值 | TODO | {{date}} | TODO | 价格 × 股本；输入与偏差 TODO | TODO |
| 现金及等价物 | TODO | {{date}} | TODO | TODO | TODO |
| 有息负债 | TODO | {{date}} | TODO | TODO | TODO |
| TTM EPS | TODO | {{date}} | TODO | TODO | TODO |
| TTM PE | TODO | {{date}} | TODO | 当前价格 ÷ TTM EPS | TODO |
| TTM FCF/share | TODO | {{date}} | TODO | 计算值；输入与偏差 TODO | TODO |
| FCF yield | TODO | {{date}} | TODO | TTM FCF/share ÷ 当前价格 | TODO |
| 10Y Treasury | TODO | {{date}} | TODO | ×1 | TODO |
| 10Y Treasury ×2 | TODO | {{date}} | TODO | ×2 | TODO |
| 估算组合权重 | TODO | {{date}} | TODO | TODO | TODO |
| 最新财报 | TODO | TODO | TODO | TODO | TODO |

## 1. 华尔街式全景扫描 Overview

### Key Forces

1. TODO
2. TODO
3. TODO

TODO

## 2. 财务剖析 Financial Autopsy

TODO

### One-off Adjustment Ledger

| Adjustment ID | Period | Item | Pre-tax/after-tax | Cash/non-cash | Repeatability | Per-share impact | Treatment | Source |
|---|---|---|---|---|---|---:|---|---|
| TODO | TODO | TODO | TODO | TODO | TODO | TODO | Include / exclude / partial | TODO |

## 3. 护城河 Moat Analysis

TODO

## 4. 极限估值 + 10 年回本数学审判

### 周期/高 CapEx 双估值闸门

TODO

### Valuation Basis Registry

| Basis ID | Metric | Value | Period | Adjustments | Use |
|---|---|---:|---|---|---|
| TODO-BEAR | EPS/share or FCF/share | TODO | TODO | None / Adjustment IDs | Bear |
| TODO-BASE | EPS/share or FCF/share | TODO | TODO | None / Adjustment IDs | Base |
| TODO-BULL | EPS/share or FCF/share | TODO | TODO | None / Adjustment IDs | Bull |

### Scenario Valuation

| Scenario | Basis ID | Metric value | Multiple | Fair value | Safety margin | Buy price | Key assumptions |
|---|---|---:|---:|---:|---:|---:|---|
| Bear | TODO-BEAR | TODO | TODO | TODO | TODO | TODO | TODO |
| Base | TODO-BASE | TODO | TODO | TODO | TODO | TODO | TODO |
| Bull | TODO-BULL | TODO | TODO | TODO | TODO | TODO | TODO |

### Capex / Owner Earnings Bridge

| Item | Value/range | Period | Evidence | Confidence |
|---|---:|---|---|---|
| Reported OCF | TODO | TODO | TODO | TODO |
| Reported Capex | TODO | TODO | TODO | TODO |
| Reported FCF | TODO | TODO | TODO | TODO |
| Maintenance Capex | TODO / Unclear | TODO | TODO | TODO |
| Growth Capex | TODO / Unclear | TODO | TODO | TODO |
| Strategic / AI Capex | TODO / Unclear | TODO | TODO | TODO |
| Owner Earnings / Normalized FCF | TODO / Unclear | TODO | TODO | TODO |

### 5-year Scenario IRR

TODO：至少输出 Bear/Base/Bull 的 5 年 IRR，列明盈利增长、分红/回购、稀释和退出倍数。

### Reverse Expectations

TODO：当前价格隐含的收入增速、利润率、资本强度或 FCF 恢复路径是什么？

### 名义 10 年回本压力测试

TODO

### 贴现 10 年回本压力测试

| 贴现率 r | EPS 所需 g | FCF 所需 g | EV/FCF 所需 g | 判断 |
|---|---:|---:|---:|---|
| 10Y 国债 ×1 | TODO | TODO | TODO | TODO |
| 10Y 国债 ×2 | TODO | TODO | TODO | TODO |
| 8% | TODO | TODO | TODO | TODO |
| 10% | TODO | TODO | TODO | TODO |

> 10 年回本是零终值压力测试。失败会提高估值门槛，但不得单独覆盖 Scenario IRR、Reverse Expectations 与商业质量证据。

## 5. 致命风险排序 Risk Ranking

TODO

## 6. 物理增长极限 Growth Potential

TODO

## 7. 机构视角 + 机会成本比对 Institutional & Opportunity Cost

TODO：比较预期股东总回报 / IRR 与国债、指数和高质量替代资产，不要求当前 FCF yield 机械超过国债 ×2。

## 8. 仓位与风控 Position Sizing & Exit Rules

TODO：经营阈值优先使用 TTM 或连续两个季度；单季度 Capex/营运资本时点不应自动触发大幅减仓。

### Pre-Mortem

TODO

### Action Matrix

| Action | Trigger type | Executable condition | Position/execution |
|---|---|---|---|
| Buy | valuation | N/A — current action only; define an honest valuation condition before using Buy | TODO |
| Add | price | TODO explicit comparator/threshold | TODO |
| Hold | operating | TODO explicit comparator/threshold | TODO |
| Reduce | valuation | TODO explicit comparator/threshold | TODO |
| Sell | thesis-break | TODO thesis-break condition | TODO |

### 公允价值、买入价与压力价格

直接引用 Module 4 Scenario Valuation：

- Base fair value：TODO
- Base buy price：TODO
- Bear/Stress price：TODO
- 不得再用另一套 EPS、倍数或折扣生成第二组价格边界。

### 价格区间摘要

| 价格区间 | 估值语境 | 推导来源 |
|---|---|---|
| TODO 以上 | 高估区 | Module 4 Scenario Valuation |
| TODO-TODO | 合理/观察区 | Module 4 Scenario Valuation |
| TODO 以下 | 买入/压力区（明确是哪一种） | Module 4 Scenario Valuation |

## 9. 最终判决 Final Verdict

### Variant View

TODO

> 仅在四镜头存在未解决的实质分歧时，列在此处或下方最终判决，最多 4 条；不要角色扮演引用。

### 三原则扣问

| 原则 | 回答 |
|---|---|
| 持有 = 买入 | TODO |
| 沉没成本不是成本，机会成本才是真成本 | TODO（用预期 IRR 比较） |
| 10 年回本测试 | TODO（压力测试，不是唯一模型） |

### Confidence Boundary

AI 研究置信度与投资确定性是不同判断；如两者表面不一致，以上方 Researchability Record 的一句话说明为准。

## Sources

- TODO
''')


CHANGELOG_ENTRY = dedent('''\
## 2026-07-31

### Valuation-basis registry, scenario math, and semantic consistency audit

**Change:**
- Added `references/valuation-consistency.md` as the authoritative contract for Valuation Basis Registry, One-off Adjustment Ledger, Scenario Valuation, Capex / Owner Earnings Bridge, fair-value/buy-price/stress-price separation, and three-model valuation synthesis.
- Added `scripts/valuation_consistency.py`, a blocking semantic checker for basis/adjustment references, scenario arithmetic and ordering, PE/FCF-yield reconciliation, and high-confidence prose contradictions.
- Updated `templates/full-report.md` with the new registries/bridges, 5-year Scenario IRR, Reverse Expectations, and explicit separation of fair value, buy price, and stress price.
- Updated `SKILL.md`, report contract, methodology, and README so the semantic checker runs before structural lint/audit. Fixed stale "10 modules" wording to 9 modules.
- Added unit tests covering valid reports, bad scenario math, unknown Basis IDs, FCF-yield mismatch, and unknown Adjustment IDs.

**Reason:** The Meta 2026-07-30 report passed existing lint/audit while containing valuation-scale drift, arithmetic contradictions, overlapping price zones, unsupported normalized EPS, and repeated conservative discounts. Structural completeness is not semantic correctness.

**Scope boundary:** This batch does not fetch data, estimate maintenance capex, implement a full DCF engine, or automatically rewrite historical reports. The new checker validates declared report structure and arithmetic; accounting judgments and source truth remain human responsibilities.

**Verification:** GitHub Actions runs py_compile, the full unittest suite, report-lint self-test, fixtures, the new checker tests, and diff-check before committing the migration. See the PR checks for the exact result.

''')


def main() -> None:
    # New authoritative files.
    (ROOT / "references" / "valuation-consistency.md").write_text(VALUATION_REFERENCE, encoding="utf-8")
    (ROOT / "scripts" / "valuation_consistency.py").write_text(CHECKER, encoding="utf-8")
    (ROOT / "tests" / "test_valuation_consistency.py").write_text(TEST, encoding="utf-8")
    (ROOT / "templates" / "full-report.md").write_text(TEMPLATE, encoding="utf-8")

    # Skill activation and execution contract.
    skill = ROOT / "SKILL.md"
    replace_once(skill, '  version: "1.1.0"', '  version: "1.2.0"')
    replace_once(
        skill,
        '- In pack-backed v5, declare derived inputs by `fact_ref` or `derived_ref`; only payback `years` may be a literal. Never copy caller-supplied values, units, dates, or source IDs into reference inputs.\n',
        '- **Valuation consistency is mandatory:** every valuation basis must have a Basis ID; adjusted/normalized metrics require an Adjustment Ledger; Scenario Valuation must separate fair value, buy price, and stress price. The 10-year payback is a pressure test, not a sole veto. Follow `references/valuation-consistency.md`.\n- In pack-backed v5, declare derived inputs by `fact_ref` or `derived_ref`; only payback `years` may be a literal. Never copy caller-supplied values, units, dates, or source IDs into reference inputs.\n',
    )
    replace_once(
        skill,
        '| Missing or conflicting critical evidence | Apply the rating caps in `references/report-contract.md`. |\n',
        '| Missing or conflicting critical evidence | Apply the rating caps in `references/report-contract.md`. |\n| Valuation report | Build the Basis Registry, Adjustment Ledger, Scenario Valuation, and Capex Bridge; run `valuation_consistency.py` before lint/audit. |\n',
    )
    replace_once(skill, '5. Run the 10 modules using `references/full-methodology.md`;', '5. Run the 9 modules using `references/full-methodology.md`;')
    replace_once(
        skill,
        '6. Lint and rerun `report_audit.py recognize`.',
        '6. Run `python3 scripts/valuation_consistency.py <report.md>` and resolve every ERROR. Then lint and rerun `report_audit.py recognize`.',
    )
    replace_once(
        skill,
        '- `references/researchability.md` — authoritative A/B/C and confidence rules.\n',
        '- `references/researchability.md` — authoritative A/B/C and confidence rules.\n- `references/valuation-consistency.md` — valuation basis, adjustment bridge, scenario math, and fair-value boundaries.\n',
    )

    # Contract: add one authoritative section without duplicating the full methodology.
    contract = ROOT / "references" / "report-contract.md"
    contract_text = contract.read_text(encoding="utf-8")
    anchor = "## Rating Caps\n"
    insertion = dedent('''\
## Valuation Consistency Contract

`references/valuation-consistency.md` is authoritative for valuation semantics. Every valuation report must include a Valuation Basis Registry, One-off Adjustment Ledger, Scenario Valuation, and—when capital intensity is material—a Capex / Owner Earnings Bridge. Fair value, buy price, and stress price are distinct outputs. The price-zone summary must be derived from the Scenario Valuation table rather than introducing independent boundaries.

Run `python3 scripts/valuation_consistency.py <report.md>` before structural lint and audit. Errors block delivery. Warnings require explicit human review.

The 10-year payback remains mandatory as a pressure test, but a failed payback row is not a sole Buy/Reduce/Sell veto. Opportunity cost is judged on expected total shareholder return / IRR, not by mechanically requiring current FCF yield to exceed a bond yield or `10Y ×2`.

''')
    if anchor not in contract_text:
        raise RuntimeError("report-contract anchor missing")
    contract.write_text(contract_text.replace(anchor, insertion + anchor, 1), encoding="utf-8")

    # Methodology: install the valuation semantics before module 5.
    methodology = ROOT / "references" / "full-methodology.md"
    method_text = methodology.read_text(encoding="utf-8")
    method_text = method_text.replace("进入 10 个模块前", "进入 9 个模块前")
    method_anchor = "## 5. 致命风险排序 Risk Ranking"
    method_insertion = dedent('''\
### 估值口径一致性（强制）

模块 4 必须执行 `references/valuation-consistency.md`：先建立 Valuation Basis Registry 和 One-off Adjustment Ledger，再输出 Bear/Base/Bull Scenario Valuation；高 Capex 公司增加 Capex / Owner Earnings Bridge。公允价值、买入价和压力价格必须分开，且模块 8 的价格区间只能引用这里的结果。

估值判断采用三角验证：5 年 Scenario IRR 为主、Reverse Expectations 为辅、10 年回本为压力测试。10 年回本的零终值假设很严厉，不得单独一票否决。机会成本比较使用预期股东总回报 / IRR，不要求成长公司的当前 FCF yield 机械超过国债 ×2。

交付前先运行：

```bash
python3 scripts/valuation_consistency.py <report.md>
```

''')
    if method_anchor not in method_text:
        raise RuntimeError("full-methodology module-5 anchor missing")
    methodology.write_text(method_text.replace(method_anchor, method_insertion + method_anchor, 1), encoding="utf-8")

    # README discoverability.
    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    list_anchor = "- [`scripts/report_lint.py`](scripts/report_lint.py)：报告交付前的硬约束检查\n"
    if list_anchor in readme_text:
        readme_text = readme_text.replace(
            list_anchor,
            list_anchor + "- [`scripts/valuation_consistency.py`](scripts/valuation_consistency.py)：估值口径、情景数学与跨章节语义一致性检查\n",
            1,
        )
    command_anchor = 'python3 scripts/report_audit.py recognize --report "/path/to/report.md"\npython3 scripts/report_lint.py "/path/to/report.md"'
    if command_anchor in readme_text:
        readme_text = readme_text.replace(
            command_anchor,
            'python3 scripts/valuation_consistency.py "/path/to/report.md"\n' + command_anchor,
            1,
        )
    readme.write_text(readme_text, encoding="utf-8")

    # Change log is prepended, preserving history.
    changelog = ROOT / "references" / "change-log.md"
    old_log = changelog.read_text(encoding="utf-8")
    title = "# Wall Street Equity Research Skill Change Log\n\n"
    if not old_log.startswith(title):
        raise RuntimeError("unexpected change-log title")
    changelog.write_text(title + CHANGELOG_ENTRY + old_log[len(title):], encoding="utf-8")

    # Mark PRD completed only after the migration has been materialized; tests run next.
    prd = ROOT / "PRD-valuation-consistency.md"
    prd.write_text(prd.read_text(encoding="utf-8").replace("实施中 - 2026-07-31", "完成 - 2026-07-31", 1), encoding="utf-8")


if __name__ == "__main__":
    main()

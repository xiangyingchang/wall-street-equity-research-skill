#!/usr/bin/env python3
"""Semantic valuation consistency checks for equity-research Markdown reports."""
from __future__ import annotations

import argparse
import re
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
        result = Decimal(match.group(0))
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


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


def _relative_error(actual: Decimal, expected: Decimal) -> Decimal:
    return abs(actual - expected) / max(abs(expected), Decimal("0.01"))


def _is_placeholder(value: str) -> bool:
    return not value.strip() or value.strip().upper().startswith("TODO")


def validate_text(text: str) -> list[Finding]:
    findings: list[Finding] = []
    tables = _tables(text)

    fact_registry = _find_table(
        tables,
        {"fact id", "metric", "value", "period/as-of", "source/tier", "basis/unit", "confidence"},
    )
    adjustment = _find_table(
        tables,
        {
            "adjustment id",
            "period",
            "item",
            "pre-tax/after-tax",
            "cash/non-cash",
            "repeatability",
            "per-share impact",
            "treatment",
            "source",
        },
    )
    assumptions = _find_table(
        tables,
        {"assumption id", "scenario", "variable", "value", "period", "evidence/rationale", "confidence"},
    )
    revenue_bridge = _find_table(
        tables,
        {"revenue bridge id", "scenario", "period", "revenue", "growth/guide basis", "source/assumption id"},
    )
    eps_bridge = _find_table(
        tables,
        {
            "bridge id",
            "scenario",
            "revenue",
            "operating margin",
            "operating income",
            "other income/expense",
            "pre-tax income",
            "tax rate",
            "net income",
            "diluted shares",
            "eps",
        },
    )
    basis = _find_table(
        tables,
        {"basis id", "metric", "value", "period", "adjustments", "bridge id", "use"},
    )
    scenario = _find_table(
        tables,
        {"scenario", "basis id", "metric value", "multiple", "fair value", "safety margin", "buy price", "key assumptions"},
    )
    capex_bridge = _find_table(tables, {"item", "value/range", "period", "evidence", "confidence"})

    for table, message in [
        (fact_registry, "missing Canonical Fact Registry table"),
        (adjustment, "missing One-off Adjustment Ledger table"),
        (assumptions, "missing Scenario Assumption Registry table"),
        (revenue_bridge, "missing Forward Revenue Bridge table"),
        (eps_bridge, "missing Scenario EPS Bridge table"),
        (basis, "missing Valuation Basis Registry table with Bridge ID"),
        (scenario, "missing Scenario Valuation table"),
    ]:
        if table is None:
            findings.append(Finding("ERROR", message))

    high_capex = bool(re.search(r"(?:资本强度|capital\s+intensity)\s*[:=：]\s*(?:高|high)", text, re.I))
    for capex_match in re.finditer(
        r"(?:capex|资本开支)[^\n|]{0,50}(?:[$¥€£]|USD|CNY|HKD|RMB)?\s*([0-9,]+(?:\.[0-9]+)?)\s*亿",
        text,
        re.I,
    ):
        amount = _decimal(capex_match.group(1))
        if amount is not None and amount >= Decimal("500"):
            high_capex = True
            break
    if high_capex and capex_bridge is None:
        findings.append(Finding("ERROR", "high-capex report is missing Capex / Owner Earnings Bridge table"))
    elif capex_bridge is None:
        findings.append(
            Finding("WARNING", "Capex / Owner Earnings Bridge omitted; acceptable only when capital intensity is not material")
        )

    fact_ids: set[str] = set()
    if fact_registry is not None:
        for row in _rows_as_dict(fact_registry):
            fact_id = _get(row, "Fact ID").strip()
            if _is_placeholder(fact_id):
                continue
            if fact_id in fact_ids:
                findings.append(Finding("ERROR", f"duplicate Fact ID: {fact_id}"))
            fact_ids.add(fact_id)
            if _is_placeholder(_get(row, "Period/as-of")):
                findings.append(Finding("ERROR", f"Fact {fact_id} has no period/as-of"))
            if _is_placeholder(_get(row, "Source/Tier")):
                findings.append(Finding("ERROR", f"Fact {fact_id} has no source/tier"))

    adjustment_ids: set[str] = set()
    if adjustment is not None:
        for row in _rows_as_dict(adjustment):
            adjustment_id = _get(row, "Adjustment ID").strip()
            if _is_placeholder(adjustment_id):
                continue
            if adjustment_id in adjustment_ids:
                findings.append(Finding("ERROR", f"duplicate Adjustment ID: {adjustment_id}"))
            adjustment_ids.add(adjustment_id)
            adjustment_text = " ".join(row.values())
            if re.search(r"forward|未来|情景|scenario|capex\s*(?:正常化|normalization)", adjustment_text, re.I):
                findings.append(
                    Finding(
                        "ERROR",
                        f"Adjustment {adjustment_id} contains a forward/scenario assumption; move it to Scenario Assumption Registry",
                    )
                )
            if re.search(r"capex|资本开支", adjustment_text, re.I) and re.search(
                r"non[- ]?cash|非现金", _get(row, "Cash/non-cash"), re.I
            ):
                findings.append(Finding("ERROR", f"Adjustment {adjustment_id} incorrectly labels Capex as non-cash"))

    assumption_ids: set[str] = set()
    if assumptions is not None:
        for row in _rows_as_dict(assumptions):
            assumption_id = _get(row, "Assumption ID").strip()
            if _is_placeholder(assumption_id):
                continue
            if assumption_id in assumption_ids:
                findings.append(Finding("ERROR", f"duplicate Assumption ID: {assumption_id}"))
            assumption_ids.add(assumption_id)

    bridge_values: dict[str, Decimal] = {}
    bridge_scenarios: dict[str, str] = {}
    bridge_revenues: dict[str, Decimal] = {}
    if eps_bridge is not None:
        for row in _rows_as_dict(eps_bridge):
            bridge_id = _get(row, "Bridge ID").strip()
            if _is_placeholder(bridge_id):
                continue
            scenario_name = _get(row, "Scenario").strip()
            revenue = _decimal(_get(row, "Revenue"))
            margin = _percent(_get(row, "Operating margin"))
            operating_income = _decimal(_get(row, "Operating income"))
            other_income = _decimal(_get(row, "Other income/expense"))
            pre_tax = _decimal(_get(row, "Pre-tax income"))
            tax_rate = _percent(_get(row, "Tax rate"))
            net_income = _decimal(_get(row, "Net income"))
            shares = _decimal(_get(row, "Diluted shares"))
            eps = _decimal(_get(row, "EPS"))
            values = {revenue, margin, operating_income, other_income, pre_tax, tax_rate, net_income, shares, eps}
            if None in values:
                findings.append(Finding("ERROR", f"Scenario EPS Bridge {bridge_id} has an unparseable numeric field"))
                continue
            assert revenue is not None
            assert margin is not None
            assert operating_income is not None
            assert other_income is not None
            assert pre_tax is not None
            assert tax_rate is not None
            assert net_income is not None
            assert shares is not None
            assert eps is not None
            if revenue <= 0 or shares <= 0 or tax_rate < 0 or tax_rate >= 1:
                findings.append(Finding("ERROR", f"Scenario EPS Bridge {bridge_id} has invalid revenue/shares/tax inputs"))
                continue
            expected_op = revenue * margin
            expected_pre_tax = operating_income + other_income
            expected_net = pre_tax * (Decimal(1) - tax_rate)
            expected_eps = net_income / shares
            for label, actual, expected in [
                ("operating income", operating_income, expected_op),
                ("pre-tax income", pre_tax, expected_pre_tax),
                ("net income", net_income, expected_net),
                ("EPS", eps, expected_eps),
            ]:
                if _relative_error(actual, expected) > Decimal("0.005"):
                    findings.append(
                        Finding("ERROR", f"Scenario EPS Bridge {bridge_id} {label} does not reconcile to its inputs")
                    )
            bridge_values[bridge_id] = eps
            bridge_scenarios[bridge_id] = _norm(scenario_name)
            bridge_revenues[bridge_id] = revenue

    revenue_by_scenario: dict[str, Decimal] = {}
    revenue_rows_by_scenario: dict[str, int] = {}
    if revenue_bridge is not None:
        for row in _rows_as_dict(revenue_bridge):
            bridge_id = _get(row, "Revenue Bridge ID").strip()
            if _is_placeholder(bridge_id):
                continue
            scenario_name = _norm(_get(row, "Scenario"))
            revenue = _decimal(_get(row, "Revenue"))
            if revenue is None:
                findings.append(Finding("ERROR", f"Revenue Bridge {bridge_id} has unparseable revenue"))
                continue
            revenue_by_scenario[scenario_name] = revenue_by_scenario.get(scenario_name, Decimal(0)) + revenue
            revenue_rows_by_scenario[scenario_name] = revenue_rows_by_scenario.get(scenario_name, 0) + 1
            source_ref = _get(row, "Source/assumption ID").strip()
            if source_ref and source_ref not in assumption_ids and not re.search(r"tier\s*[12]|filing|ir|consensus", source_ref, re.I):
                findings.append(Finding("ERROR", f"Revenue Bridge {bridge_id} references unknown assumption/source: {source_ref}"))

        for bridge_id, scenario_name in bridge_scenarios.items():
            if scenario_name not in revenue_by_scenario:
                findings.append(Finding("ERROR", f"Scenario EPS Bridge {bridge_id} has no matching Forward Revenue Bridge rows"))
                continue
            if revenue_rows_by_scenario[scenario_name] < 4:
                findings.append(
                    Finding("ERROR", f"Forward Revenue Bridge for {scenario_name} must contain at least four explicit periods")
                )
            if _relative_error(revenue_by_scenario[scenario_name], bridge_revenues[bridge_id]) > Decimal("0.005"):
                findings.append(
                    Finding("ERROR", f"Scenario EPS Bridge {bridge_id} revenue does not equal summed Forward Revenue Bridge")
                )

    if re.search(r"(?:×|x|\*)\s*4\.5|4\.5\s*(?:个)?季度|run[- ]?rate\s+adjustment", text, re.I):
        findings.append(Finding("ERROR", "undefined quarter ×4.5/run-rate revenue annualization is not allowed"))

    basis_ids: set[str] = set()
    basis_values: dict[str, Decimal] = {}
    if basis is not None:
        for row in _rows_as_dict(basis):
            basis_id = _get(row, "Basis ID").strip()
            if _is_placeholder(basis_id):
                continue
            if basis_id in basis_ids:
                findings.append(Finding("ERROR", f"duplicate Basis ID: {basis_id}"))
            basis_ids.add(basis_id)
            basis_value = _decimal(_get(row, "Value"))
            if basis_value is not None:
                basis_values[basis_id] = basis_value
            refs = _get(row, "Adjustments").strip()
            bridge_id = _get(row, "Bridge ID").strip()
            if bridge_id and _norm(bridge_id) not in {"n/a", "na", "none", "无"}:
                if bridge_id not in bridge_values:
                    findings.append(Finding("ERROR", f"Basis {basis_id} references unknown Bridge ID: {bridge_id}"))
                elif basis_value is not None and _relative_error(basis_value, bridge_values[bridge_id]) > Decimal("0.005"):
                    findings.append(Finding("ERROR", f"Basis {basis_id} Value does not match Scenario EPS Bridge {bridge_id}"))
            normalized_cue = " ".join(
                [_get(row, "Basis ID"), _get(row, "Metric"), _get(row, "Period"), _get(row, "Use")]
            )
            has_adjustment = _norm(refs) not in {"", "none", "n/a", "na", "无"}
            has_bridge = _norm(bridge_id) not in {"", "none", "n/a", "na", "无"}
            if re.search(r"normalized|adjusted|core|中枢|调整后|正常化", normalized_cue, re.I) and not (
                has_adjustment or has_bridge
            ):
                findings.append(Finding("ERROR", f"normalized/adjusted Basis {basis_id} has no adjustment or scenario bridge"))
            if has_adjustment:
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
            if _is_placeholder(name):
                continue
            if basis_id not in basis_ids:
                findings.append(Finding("ERROR", f"Scenario {name} references unknown Basis ID: {basis_id}"))
            elif metric is not None and basis_id in basis_values:
                registered = basis_values[basis_id]
                if _relative_error(metric, registered) > Decimal("0.02"):
                    findings.append(Finding("ERROR", f"Scenario {name} Metric value does not match registered Basis {basis_id}"))
            if None in {metric, multiple, fair, margin, buy}:
                findings.append(Finding("ERROR", f"Scenario {name} has an unparseable numeric field"))
                continue
            assert metric is not None and multiple is not None and fair is not None and margin is not None and buy is not None
            expected_fair = metric * multiple
            expected_buy = fair * (Decimal(1) - margin)
            if _relative_error(fair, expected_fair) > Decimal("0.02"):
                findings.append(Finding("ERROR", f"Scenario {name} fair value is not Metric value × Multiple"))
            if _relative_error(buy, expected_buy) > Decimal("0.02"):
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
        if _relative_error(pe, expected) > Decimal("0.03"):
            findings.append(Finding("ERROR", "Evidence Ledger TTM PE does not reconcile to price / TTM EPS"))
    if price is not None and fcf_share is not None and fcf_yield is not None:
        expected = fcf_share / price * Decimal(100)
        if abs(fcf_yield - expected) > Decimal("0.20"):
            findings.append(Finding("ERROR", "Evidence Ledger FCF yield does not reconcile to FCF/share / price"))

    legacy_action_table = _find_table(tables, {"rule id", "action", "current facts used", "triggered"})
    if legacy_action_table is not None:
        findings.append(
            Finding("ERROR", "legacy manual Triggered table is not allowed; use fact-based valuation_runtime.py evaluate-action")
        )
    if not re.search(r"valuation_runtime\.py\s+evaluate-action", text, re.I):
        findings.append(Finding("ERROR", "missing fact-based evaluate-action runtime command/result reference"))
    if re.search(r"valuation_runtime\.py\s+resolve-action", text, re.I):
        findings.append(Finding("ERROR", "full reports may not use legacy resolve-action"))

    for table in tables:
        headers = {_norm(str(h)) for h in table["headers"]}  # type: ignore[index]
        if not ({"资产", "asset", "instrument", "benchmark"} & headers):
            continue
        for row in _rows_as_dict(table):
            row_text = " ".join(row.values())
            if re.search(r"10\s*y|10\s*年", row_text, re.I) and re.search(r"(?:×|x|\*)\s*2", row_text) and re.search(
                r"极低|very\s+low|risk[- ]?free|无风险", row_text, re.I
            ):
                findings.append(
                    Finding("ERROR", "10Y Treasury ×2 is a required-return hurdle, not a low-risk investable asset")
                )

    for match in re.finditer(
        r"(?P<pct>\d+(?:\.\d+)?)\s*%[^\n]{0,35}(?:翻倍|double)|(?:翻倍|double)[^\n]{0,35}(?P<pct2>\d+(?:\.\d+)?)\s*%",
        text,
        re.I,
    ):
        raw = match.group("pct") or match.group("pct2")
        if raw and Decimal(raw) < Decimal(90):
            findings.append(Finding("ERROR", f"'翻倍/double' conflicts with stated growth of {raw}%"))

    for match in re.finditer(
        r"(?P<a>\d+(?:\.\d+)?)[^\n]{0,25}(?:beat|超过|高于)[^\n]{0,25}(?:上限|upper)[^\n]{0,10}(?P<b>\d+(?:\.\d+)?)",
        text,
        re.I,
    ):
        if Decimal(match.group("a")) < Decimal(match.group("b")):
            findings.append(
                Finding("ERROR", f"stated beat/above upper bound conflicts with {match.group('a')} < {match.group('b')}")
            )

    if re.search(r"(?:单季|季度|Q[1-4])[^\n]{0,80}(?:FCF|自由现金流)[^\n]{0,80}(?:年化|annualized)", text, re.I):
        findings.append(
            Finding("WARNING", "single-quarter FCF is annualized; verify seasonality, procurement timing, and cash adjustments")
        )

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

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

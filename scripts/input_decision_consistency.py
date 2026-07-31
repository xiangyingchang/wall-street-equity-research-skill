#!/usr/bin/env python3
"""Input provenance and decision-robustness checks for equity reports."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    level: str
    message: str


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _tables(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    result: list[dict[str, Any]] = []
    section = ""
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#"):
            section = line
        if i + 1 < len(lines):
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
                result.append({"headers": headers, "rows": rows, "line": i + 1, "section": section})
                i = j
                continue
        i += 1
    return result


def _find_table(tables: list[dict[str, Any]], required: set[str]) -> dict[str, Any] | None:
    for table in tables:
        headers = {_norm(str(h)) for h in table["headers"]}
        if required <= headers:
            return table
    return None


def _rows(table: dict[str, Any]) -> list[dict[str, str]]:
    headers = [str(h) for h in table["headers"]]
    return [dict(zip(headers, [str(cell) for cell in row])) for row in table["rows"]]


def _get(row: dict[str, str], name: str) -> str:
    target = _norm(name)
    for key, value in row.items():
        if _norm(key) == target:
            return value
    return ""


def _number(raw: str) -> Decimal | None:
    value = raw.replace(",", "").replace("$", "").replace("¥", "").replace("€", "").replace("×", "x").replace("倍", "x")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
    if not match:
        return None
    try:
        result = Decimal(match.group(0))
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def _percent(raw: str) -> Decimal | None:
    value = _number(raw)
    if value is None:
        return None
    return value / Decimal(100) if "%" in raw else value


def _relative_error(actual: Decimal, expected: Decimal) -> Decimal:
    return abs(actual - expected) / max(abs(expected), Decimal("0.01"))


def _contains_placeholder(value: str) -> bool:
    return bool(re.search(r"\bTODO\b|未运行|unknown|not run|待运行", value, re.I))


def _parse_range(raw: str) -> tuple[Decimal | None, Decimal | None]:
    cleaned = raw.replace(",", "").replace("$", "").strip()
    numbers = [Decimal(x) for x in re.findall(r"\d+(?:\.\d+)?", cleaned)]
    if not numbers:
        return None, None
    if re.search(r"以下|below|<", cleaned, re.I):
        return None, numbers[0]
    if re.search(r"以上|above|>", cleaned, re.I):
        return numbers[0], None
    if len(numbers) >= 2:
        return min(numbers[0], numbers[1]), max(numbers[0], numbers[1])
    return numbers[0], numbers[0]


def _in_range(value: Decimal, low: Decimal | None, high: Decimal | None) -> bool:
    return (low is None or value >= low) and (high is None or value <= high)


def validate_text(text: str) -> list[Finding]:
    findings: list[Finding] = []
    tables = _tables(text)

    values = _find_table(tables, {"value id", "kind", "metric", "value", "period/as-of", "source/tier", "basis/unit", "confidence", "inputs/formula"})
    ttm = _find_table(tables, {"derivation id", "metric", "mode", "component ids", "component totals", "value", "runtime ref"})
    revenue = _find_table(tables, {"revenue bridge id", "scenario", "period", "mode", "base value", "growth", "guide low", "guide high", "revenue", "source/assumption id", "runtime ref"})
    thresholds = _find_table(tables, {"threshold id", "metric", "value", "basis", "lookback", "confirmation", "tolerance", "minimum confidence", "rationale"})
    return_pair_table = _find_table(tables, {"scenario", "starting basis id", "starting eps", "eps cagr", "exit pe", "dividend assumption", "target return", "5-year irr", "required terminal eps", "required eps cagr", "target-return price", "runtime ref"})
    verification = _find_table(tables, {"check", "result"})

    for table, message in [
        (values, "missing Canonical Value Registry"),
        (ttm, "missing TTM Derivation Runtime table"),
        (revenue, "missing Revenue Forecast Runtime table"),
        (thresholds, "missing Threshold Policy Registry"),
        (return_pair_table, "missing shared Return Pair Runtime table"),
        (verification, "missing Verification table"),
    ]:
        if table is None:
            findings.append(Finding("ERROR", message))

    value_ids: set[str] = set()
    if values is not None:
        for row in _rows(values):
            value_id = _get(row, "Value ID").strip()
            if not value_id or value_id.upper().startswith("TODO"):
                continue
            if value_id in value_ids:
                findings.append(Finding("ERROR", f"duplicate Value ID: {value_id}"))
            value_ids.add(value_id)
            kind = _get(row, "Kind").strip().upper()
            if kind not in {"FACT", "DERIVED", "MODEL"}:
                findings.append(Finding("ERROR", f"Value {value_id} has invalid Kind: {kind}"))
            if not value_id.upper().startswith(f"{kind}-"):
                findings.append(Finding("ERROR", f"Value {value_id} prefix does not match Kind {kind}"))
            metric = _get(row, "Metric")
            combined = f"{value_id} {metric}".casefold()
            if kind == "FACT" and re.search(r"fair value|公允价值|target price|目标价|\birr\b|buy price|买入价|stress price|压力价", combined, re.I):
                findings.append(Finding("ERROR", f"model output is incorrectly registered as FACT: {value_id}"))
            if kind == "DERIVED" and re.search(r"\bttm\b", combined, re.I):
                formula = _get(row, "Inputs/Formula")
                if not formula.strip() or not re.search(r"ttm-derive|DERIV-|FACT-", formula, re.I):
                    findings.append(Finding("ERROR", f"TTM derived Value {value_id} lacks component/runtime provenance"))

    ttm_ids: set[str] = set()
    if ttm is not None:
        for row in _rows(ttm):
            derivation_id = _get(row, "Derivation ID").strip()
            if not derivation_id or derivation_id.upper().startswith("TODO"):
                continue
            if derivation_id in ttm_ids:
                findings.append(Finding("ERROR", f"duplicate TTM Derivation ID: {derivation_id}"))
            ttm_ids.add(derivation_id)
            mode = _get(row, "Mode").strip().lower()
            component_ids = [x for x in re.split(r"[,，;；\s]+", _get(row, "Component IDs")) if x]
            if mode not in {"sum", "ratio"}:
                findings.append(Finding("ERROR", f"TTM Derivation {derivation_id} has invalid mode"))
            if len(component_ids) < 4:
                findings.append(Finding("ERROR", f"TTM Derivation {derivation_id} needs four explicit component IDs"))
            if "ttm-derive" not in _get(row, "Runtime ref"):
                findings.append(Finding("ERROR", f"TTM Derivation {derivation_id} lacks ttm-derive runtime ref"))

    revenue_totals: dict[str, Decimal] = {}
    revenue_by_period: dict[tuple[str, str], Decimal] = {}
    if revenue is not None:
        scenario_counts: dict[str, int] = {}
        for row in _rows(revenue):
            bridge_id = _get(row, "Revenue Bridge ID").strip()
            if not bridge_id or bridge_id.upper().startswith("TODO"):
                continue
            scenario = _get(row, "Scenario").strip().casefold()
            period = _get(row, "Period").strip().casefold()
            mode = _get(row, "Mode").strip().lower()
            shown = _number(_get(row, "Revenue"))
            if shown is None:
                findings.append(Finding("ERROR", f"Revenue Bridge {bridge_id} has invalid Revenue"))
                continue
            scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1
            revenue_totals[scenario] = revenue_totals.get(scenario, Decimal(0)) + shown
            revenue_by_period[(scenario, period)] = shown
            if "revenue-bridge" not in _get(row, "Runtime ref"):
                findings.append(Finding("ERROR", f"Revenue Bridge {bridge_id} lacks revenue-bridge runtime ref"))
            if mode in {"yoy", "qoq"}:
                base = _number(_get(row, "Base Value"))
                growth = _percent(_get(row, "Growth"))
                if base is None or growth is None:
                    findings.append(Finding("ERROR", f"Revenue Bridge {bridge_id} lacks base/growth inputs"))
                else:
                    expected = base * (Decimal(1) + growth)
                    if _relative_error(shown, expected) > Decimal("0.005"):
                        findings.append(Finding("ERROR", f"Revenue Bridge {bridge_id} does not reconcile to base × (1 + growth)"))
            elif mode == "guide_midpoint":
                low = _number(_get(row, "Guide Low"))
                high = _number(_get(row, "Guide High"))
                if low is None or high is None:
                    findings.append(Finding("ERROR", f"Revenue Bridge {bridge_id} lacks guide range"))
                else:
                    expected = (low + high) / Decimal(2)
                    if _relative_error(shown, expected) > Decimal("0.005"):
                        findings.append(Finding("ERROR", f"Revenue Bridge {bridge_id} is not guide midpoint"))
            elif mode not in {"explicit", "consensus"}:
                findings.append(Finding("ERROR", f"Revenue Bridge {bridge_id} has invalid mode"))
        for scenario, count in scenario_counts.items():
            if count != 4:
                findings.append(Finding("ERROR", f"Revenue scenario {scenario} must have exactly four periods"))
        periods = {period for scenario, period in revenue_by_period if scenario == "base"}
        for period in periods:
            base = revenue_by_period.get(("base", period))
            bull = revenue_by_period.get(("bull", period))
            if base is not None and bull is not None and bull < base:
                findings.append(Finding("WARNING", f"Bull revenue is below Base for {period}; require an explicit timing explanation"))

    assumptions = _find_table(tables, {"assumption id", "scenario", "variable", "value", "period", "evidence/rationale", "confidence"})
    if assumptions is not None and {"base", "bull"} <= set(revenue_totals):
        base_growth: set[Decimal] = set()
        bull_growth: set[Decimal] = set()
        for row in _rows(assumptions):
            if "revenue" not in _get(row, "Variable").casefold():
                continue
            growth = _percent(_get(row, "Value"))
            if growth is None:
                continue
            scenario = _get(row, "Scenario").strip().casefold()
            if scenario == "base":
                base_growth.add(growth)
            elif scenario == "bull":
                bull_growth.add(growth)
        if _relative_error(revenue_totals["base"], revenue_totals["bull"]) <= Decimal("0.005") and base_growth and bull_growth and base_growth != bull_growth:
            findings.append(Finding("ERROR", "Base and Bull Forward Revenue totals are effectively identical despite different revenue-growth assumptions"))

    threshold_ids: set[str] = set()
    if thresholds is not None:
        required_text = ["Metric", "Basis", "Lookback", "Confirmation", "Tolerance", "Minimum confidence", "Rationale"]
        for row in _rows(thresholds):
            threshold_id = _get(row, "Threshold ID").strip()
            if not threshold_id or threshold_id.upper().startswith("TODO"):
                continue
            if threshold_id in threshold_ids:
                findings.append(Finding("ERROR", f"duplicate Threshold ID: {threshold_id}"))
            threshold_ids.add(threshold_id)
            if not threshold_id.startswith("THR-"):
                findings.append(Finding("ERROR", f"Threshold ID must start THR-: {threshold_id}"))
            for field in required_text:
                value = _get(row, field).strip()
                if not value or value.upper().startswith("TODO"):
                    findings.append(Finding("ERROR", f"Threshold {threshold_id} missing {field}"))
            tolerance = _percent(_get(row, "Tolerance"))
            if tolerance is None or tolerance < 0:
                findings.append(Finding("ERROR", f"Threshold {threshold_id} has invalid tolerance"))

    action_matrix = _find_table(tables, {"action", "trigger type", "executable condition", "position/execution"})
    if action_matrix is not None:
        for row in _rows(action_matrix):
            condition = _get(row, "Executable condition")
            if re.search(r"(?:<|>|<=|>=)\s*[-+$]?\d", condition) and "THR-" not in condition:
                findings.append(Finding("ERROR", f"Action {_get(row, 'Action')} uses a naked numeric threshold; reference THR-*"))

    if "valuation_runtime.py return-pair" not in text:
        findings.append(Finding("ERROR", "new full report must use valuation_runtime.py return-pair"))
    if re.search(r"valuation_runtime\.py\s+irr\b", text) or re.search(r"valuation_runtime\.py\s+reverse\b", text):
        findings.append(Finding("ERROR", "new full report may not use separate irr/reverse commands"))
    if "v2-threshold-policy" not in text:
        findings.append(Finding("ERROR", "Action Evaluation must record v2-threshold-policy mode"))
    if "valuation_runtime.py robustness" not in text:
        findings.append(Finding("ERROR", "missing action robustness runtime reference"))

    robust_match = re.search(r"Robustness stable\s*\|\s*([^|\n]+)", text, re.I)
    action_match = re.search(r"Resolved action\s*\|\s*([^|\n]+)", text, re.I)
    if robust_match and re.search(r"false", robust_match.group(1), re.I):
        if not action_match or "REVIEW" not in action_match.group(1).upper():
            findings.append(Finding("ERROR", "unstable robustness result requires resolved action REVIEW"))

    if values is not None:
        evidence = _find_table(tables, {"数据项", "数值", "日期", "来源/层级", "口径", "可信度"})
        if evidence is not None:
            share_basis = ""
            market_basis = ""
            for row in _rows(evidence):
                label = _get(row, "数据项").casefold()
                if "股本" in label or "shares" in label:
                    share_basis = _get(row, "口径")
                if "市值" in label or "market cap" in label:
                    market_basis = _get(row, "口径")
            if re.search(r"weighted[- ]?average|加权平均", share_basis, re.I) and not re.search(r"reconcil|期末|point[- ]?in[- ]?time|估算", f"{share_basis} {market_basis}", re.I):
                findings.append(Finding("ERROR", "market cap uses weighted-average diluted shares without point-in-time reconciliation"))

    margin_values: set[Decimal] = set()
    for match in re.finditer(r"(?:TTM\s*(?:operating\s*margin|经营利润率)|经营利润率[^|\n]{0,20}TTM)[^|\n]{0,20}(\d+(?:\.\d+)?)\s*%", text, re.I):
        margin_values.add(Decimal(match.group(1)))
    if len(margin_values) > 1 and max(margin_values) - min(margin_values) > Decimal("1"):
        findings.append(Finding("ERROR", f"conflicting TTM operating-margin values across report: {sorted(margin_values)}"))

    evidence_values: dict[str, Decimal] = {}
    evidence = _find_table(tables, {"数据项", "数值"})
    if evidence is not None:
        for row in _rows(evidence):
            value = _number(_get(row, "数值"))
            if value is not None:
                evidence_values[_norm(_get(row, "数据项"))] = value
    current_price = next((value for label, value in evidence_values.items() if label in {"当前价格", "当前股价", "current price"}), None)
    current_action = ""
    worth_buying = ""
    first_page = _find_table(tables, {"项目", "结论"})
    if first_page is not None:
        for row in _rows(first_page):
            item = _get(row, "项目")
            if "当前动作" in item:
                current_action = _get(row, "结论").upper()
            if "当前价格是否值得重新买入" in item:
                worth_buying = _get(row, "结论")
    zone = _find_table(tables, {"价格区间", "估值语境", "推导来源"})
    if current_price is not None and zone is not None:
        for row in _rows(zone):
            context = _get(row, "估值语境")
            if "买入区" not in context:
                continue
            low, high = _parse_range(_get(row, "价格区间"))
            if _in_range(current_price, low, high):
                if re.search(r"否|no", worth_buying, re.I) or re.search(r"REDUCE|SELL|减仓|清仓", current_action, re.I):
                    findings.append(Finding("ERROR", "current price is inside a buy zone while the verdict says no-buy or Reduce/Sell"))

    if return_pair_table is not None:
        for row in _rows(return_pair_table):
            if not _get(row, "Scenario") or _get(row, "Scenario").upper().startswith("TODO"):
                continue
            if not _get(row, "Target-return price").strip():
                findings.append(Finding("ERROR", f"Return Pair row {_get(row, 'Scenario')} lacks target-return price"))
            if "return-pair" not in _get(row, "Runtime ref"):
                findings.append(Finding("ERROR", f"Return Pair row {_get(row, 'Scenario')} lacks runtime ref"))

    if verification is not None:
        required_checks = {"ttm derivation runtime", "revenue bridge runtime", "eps bridge runtime", "return pair runtime", "fact-based action evaluation", "action robustness", "valuation consistency", "input/decision consistency", "lint", "audit verdict"}
        seen: set[str] = set()
        for row in _rows(verification):
            check = _norm(_get(row, "Check"))
            result = _get(row, "Result").strip()
            seen.add(check)
            if _contains_placeholder(result) or re.search(r"\bFAIL\b", result, re.I):
                findings.append(Finding("ERROR", f"Verification {check} is incomplete or failed"))
        for check in sorted(required_checks - seen):
            findings.append(Finding("ERROR", f"Verification is missing required check: {check}"))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    findings = validate_text(args.report.read_text(encoding="utf-8"))
    for finding in findings:
        print(f"{finding.level}: {finding.message}")
    errors = [finding for finding in findings if finding.level == "ERROR"]
    if errors:
        print(f"FAIL: {len(errors)} input/decision consistency error(s)")
        return 1
    warnings = sum(finding.level == "WARNING" for finding in findings)
    print(f"PASS: input/decision consistency ({warnings} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

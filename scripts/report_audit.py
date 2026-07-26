#!/usr/bin/env python3
"""Manual-only report audit with a hashed manifest and provenance checks.

Adapted from AI Berkshire's MIT-licensed report_audit.py; see
references/third-party-notices.md. This tool never fetches data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from validation_common import classify_discrepancy, decimal, direct_discrepancy_percent, symmetric_spread_percent


VERSION = 4
MINIMUM_RATIO = Decimal("0.15")
AMOUNT = re.compile(r"^(?P<sign>[+-]?)(?P<currency>[$¥€£]?)(?P<postsign>[+-]?)(?P<number>(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?|\.\d+)(?P<suffix>%|[xX]|倍|万亿|亿(?:元|美元|港元)?|[BMT])?$", re.I)
PAREN_INNER = re.compile(r"^\((?P<inner>.+)\)(?P<suffix>%|[xX]|倍|万亿|亿(?:元|美元|港元)?|[BMT])$", re.I)
EXCLUDED_HEADERS = ("date", "日期", "时间", "source", "来源", "层级", "tier", "口径", "basis", "判断", "judgment", "verdict", "说明", "description", "备注", "note", "可信度", "confidence")
OFFICIAL_HOSTS = ("sec.gov", "federalreserve.gov", "treasury.gov", "hkexnews.hk", "cninfo.com.cn", "sse.com.cn", "szse.cn", "nyse.com", "nasdaq.com")
TIER2_HOSTS = ("stockanalysis.com", "macrotrends.net", "finance.yahoo.com", "koyfin.com", "tikr.com", "aastocks.com", "eastmoney.com", "10jqka.com.cn")
REJECTED_HOSTS = ("reddit.com", "medium.com", "substack.com", "blogspot.", "wordpress.", "x.com", "twitter.com", "facebook.com")
CANONICAL_PORTFOLIO_HOST = "github.com"
CANONICAL_PORTFOLIO_PATH = "/xiangyingchang/portfolio-dashboard"
ALIASES = {
    "market_price": ("current price", "close price", "现价", "当前价格", "收盘价", "股价"),
    "market_cap": ("market cap", "市值"), "shares": ("shares outstanding", "share count", "total shares", "总股本", "稀释股数", "股本"),
    "revenue": ("revenue", "营业收入", "营收", "收入"), "net_income": ("net income", "净利润", "归母净利润"),
    "ttm_eps": ("ttm eps", "ttm每股收益"),
    "ttm_fcf_per_share": ("ttm fcf/share", "ttm fcf per share", "每股ttm fcf", "ttm每股自由现金流"),
    "eps": ("eps", "每股收益"), "fcf_per_share": ("fcf per share", "free cash flow per share", "每股自由现金流", "fcf/股"),
    "portfolio_weight": ("estimated portfolio weight", "portfolio weight", "估算组合权重", "组合权重"),
    "cash": ("cash", "现金", "现金及等价物"), "debt": ("debt", "债务", "有息负债"),
}
YIELD_ALIASES = ("10y government yield", "10y treasury yield", "10y treasury", "10年国债", "10 年国债", "10y国债", "美国10y国债", "us10ytreasury")
MANDATORY_SINGLE_FIELDS = (
    "market_price",
    "shares",
    "market_cap",
    "cash",
    "debt",
    "ttm_eps",
    "ttm_fcf_per_share",
    "government_yield",
    "government_yield_x2",
    "portfolio_weight",
)
MANDATORY_ALL_FIELDS = ("payback_eps", "payback_fcf", "payback_ev_fcf")


def error(message: str) -> ValueError:
    return ValueError(message)


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def parse_numeric(text: str) -> tuple[str, str] | None:
    value = re.sub(r"\s+", "", text.strip())
    if not value:
        return None
    negative = False
    if value.startswith("(") and value.endswith(")"):
        negative, value = True, value[1:-1]
    else:
        parenthesized = PAREN_INNER.fullmatch(value)
        if parenthesized:
            negative = True
            value = f"{parenthesized.group('inner')}{parenthesized.group('suffix')}"
    match = AMOUNT.fullmatch(value)
    if not match:
        return None
    signs = f"{match.group('sign')}{match.group('postsign')}"
    if "+" in signs and "-" in signs:
        return None
    negative = negative or "-" in signs
    number = decimal(match.group("number"))
    if negative:
        number = -abs(number)
    unit = f"{match.group('currency') or ''}{match.group('suffix') or ''}"
    return str(number), unit


def eligible_header(header: str) -> bool:
    key = normalized(re.sub(r"[*`_]", "", header))
    return bool(key) and not any(token in key for token in EXCLUDED_HEADERS)


def payback_field(section: str, row_label: str, column: str) -> str | None:
    if not re.match(r"##\s*4\.", section, re.I):
        return None
    row, column_key = normalized(row_label), normalized(column)
    growth_column = any(token in column_key for token in ("所需g", "requiredg", "growth", "cagr", "年增速", "年化g")) or ("payback" in column_key and column_key.endswith("g"))
    if not growth_column:
        return None
    metric = column_key if any(token in column_key for token in ("eps", "fcf")) else row
    if "ev/fcf" in metric or "evfcf" in metric:
        return "payback_ev_fcf"
    if "fcf" in metric or "自由现金流" in metric:
        return "payback_fcf"
    if "eps" in metric or "每股收益" in metric:
        return "payback_eps"
    return None


def is_x2_yield(label: str) -> bool:
    value = normalized(label).replace("×", "x")
    return any(token in value for token in ("x2", "×2", "2x", "double"))


def classify(section: str, row_label: str, column: str) -> str:
    payback = payback_field(section, row_label, column)
    if payback:
        return payback
    context, label = normalized(f"{row_label} {column}"), normalized(row_label)
    if any(normalized(alias) in label for alias in YIELD_ALIASES):
        return "government_yield_x2" if is_x2_yield(row_label) else "government_yield"
    for field, aliases in ALIASES.items():
        if any(normalized(alias) in context for alias in aliases):
            return field
    return "other"


def extract_points(report: str) -> list[dict[str, Any]]:
    points, section, lines, index = [], "", report.splitlines(), 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("## "):
            section = line
        if not (line.startswith("|") and index + 1 < len(lines) and re.fullmatch(r"\|[\s:|-]+\|", lines[index + 1].strip())):
            index += 1
            continue
        headers = [cell.strip() for cell in line.strip("|").split("|")]
        index += 2
        while index < len(lines) and lines[index].strip().startswith("|"):
            cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
            row_label = re.sub(r"[*`_]", "", cells[0]).strip() if cells else ""
            for column_index, cell in enumerate(cells[1:], start=1):
                column = headers[column_index] if column_index < len(headers) else f"column-{column_index}"
                if not eligible_header(column):
                    continue
                parsed = parse_numeric(cell)
                if not parsed:
                    continue
                value, unit = parsed
                points.append({"field": classify(section, row_label, column), "label": row_label, "column": column, "reported_value": value, "unit": unit, "line_number": index + 1, "section": section})
            index += 1
    return points


def tier_policy(field: str) -> dict[str, Any]:
    if field == "portfolio_weight":
        return {"allowed_tiers": ["Internal"], "tier2_requires_secondary": False}
    market_or_yield = field in {"market_price", "government_yield", "government_yield_x2"}
    return {"allowed_tiers": ["Tier 1", "Tier 2"] if market_or_yield else ["Tier 1"], "tier2_requires_secondary": market_or_yield}


def build_manifest(report: str, ratio: Decimal) -> dict[str, Any]:
    if not MINIMUM_RATIO <= ratio <= Decimal("1"):
        raise error("ratio must be >= 0.15 and <= 1")
    points, report_sha256 = extract_points(report), hashlib.sha256(report.encode()).hexdigest()
    target = math.ceil(len(points) * float(ratio))
    selected: dict[tuple[int, str, str], dict[str, Any]] = {}
    for field in MANDATORY_SINGLE_FIELDS:
        candidates = [point for point in points if point["field"] == field]
        if candidates:
            point = min(candidates, key=lambda item: (item["line_number"], item["column"]))
            selected[(point["line_number"], point["label"], point["column"])] = point
    for point in points:
        if point["field"] in MANDATORY_ALL_FIELDS:
            selected[(point["line_number"], point["label"], point["column"])] = point
    for point in sorted(points, key=digest):
        if len(selected) >= target:
            break
        selected[(point["line_number"], point["label"], point["column"])] = point
    eligible_universe_ids = sorted(digest({"report_sha256": report_sha256, **point}) for point in points)
    items = []
    for point in sorted(selected.values(), key=lambda item: (item["line_number"], item["column"])):
        item = {**point, "required_tier_policy": tier_policy(point["field"])}
        item["id"] = digest({"report_sha256": report_sha256, **point})
        items.append(item)
    body = {"version": VERSION, "report_sha256": report_sha256, "requested_ratio": str(ratio), "actual_ratio": str(Decimal(len(items)) / Decimal(len(points))) if points else "0", "eligible_numeric_table_cells": len(points), "eligible_universe_ids": eligible_universe_ids, "items": items}
    return {**body, "manifest_sha256": digest(body)}


def results_template(manifest: dict[str, Any]) -> dict[str, Any]:
    results = []
    for item in manifest["items"]:
        result: dict[str, Any] = {"id": item["id"], "fresh_value": None, "source": {"name": "", "tier": "", "source_url": "", "authority_type": ""}, "reconciliation": False, "reconciliation_explanation": ""}
        if item["required_tier_policy"]["tier2_requires_secondary"]:
            result["secondary_source"] = {"name": "", "tier": "", "source_url": "", "authority_type": "", "value": None}
        results.append(result)
    return {"manifest_sha256": manifest["manifest_sha256"], "results": results}


def load_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise error(f"JSON constant {value!r} is not allowed")
    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise error(f"invalid JSON in {path}: {exc}") from exc


def require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise error(f"{name} must be an object")
    return value


def host(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise error("source_url must be an https URL")
    return parsed.hostname.lower()


def approved_portfolio_source(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return False
    path = parsed.path.rstrip("/").casefold()
    return (
        parsed.hostname.casefold() == CANONICAL_PORTFOLIO_HOST
        and path == CANONICAL_PORTFOLIO_PATH
        and parsed.username is None
        and parsed.password is None
        and parsed.port is None
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    )


def source_valid(value: Any, allowed_tiers: list[str], name: str) -> dict[str, Any]:
    source = require_object(value, name)
    required, allowed = {"name", "tier", "source_url", "authority_type"}, {"name", "tier", "source_url", "authority_type", "issuer_domain", "value"}
    if not required.issubset(source) or not set(source).issubset(allowed) or not all(isinstance(source[key], str) and source[key].strip() for key in required):
        raise error(f"{name} requires name, tier, source_url, and authority_type")
    if source["tier"] not in allowed_tiers:
        raise error(f"{name}.tier must be one of {allowed_tiers}")
    source_host = host(source["source_url"])
    if any(blocked in source_host for blocked in REJECTED_HOSTS):
        raise error(f"{name} host is not an allowed evidence source")
    authority = source["authority_type"]
    if source["tier"] == "Tier 1":
        if authority in {"regulator", "exchange"} and not any(source_host == official or source_host.endswith(f".{official}") for official in OFFICIAL_HOSTS):
            raise error(f"{name} Tier 1 regulator/exchange host is not recognized")
        if authority == "company_ir":
            issuer = source.get("issuer_domain")
            if not isinstance(issuer, str) or not issuer.strip() or not (source_host == issuer.lower() or source_host.endswith(f".{issuer.lower()}")):
                raise error(f"{name} company_ir requires confirmed issuer_domain")
        if authority not in {"regulator", "exchange", "company_ir"}:
            raise error(f"{name} Tier 1 authority_type is invalid")
    elif source["tier"] == "Internal":
        if authority != "portfolio_system" or not approved_portfolio_source(source["source_url"]):
            raise error(f"{name} Internal source must be an approved portfolio system")
    elif authority != "tier2_vendor" or not any(source_host == vendor or source_host.endswith(f".{vendor}") for vendor in TIER2_HOSTS):
        raise error(f"{name} Tier 2 host or authority_type is invalid")
    return source


def normalized_vendor_domain(url: str) -> str:
    source_host = host(url)
    for domain in (*TIER2_HOSTS, *OFFICIAL_HOSTS):
        if source_host == domain or source_host.endswith(f".{domain}"):
            return domain
    parts = source_host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else source_host


def validate_manifest(manifest: Any) -> dict[str, Any]:
    manifest = require_object(manifest, "manifest")
    required = {"version", "report_sha256", "requested_ratio", "actual_ratio", "eligible_numeric_table_cells", "eligible_universe_ids", "items", "manifest_sha256"}
    if set(manifest) != required or manifest["version"] != VERSION or not isinstance(manifest["items"], list):
        raise error("manifest has an invalid shape")
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if digest(body) != manifest["manifest_sha256"]:
        raise error("manifest hash does not match its contents")
    return manifest


def evaluate(manifest: Any, payload: Any, report: str) -> dict[str, Any]:
    manifest = validate_manifest(manifest)
    if hashlib.sha256(report.encode()).hexdigest() != manifest["report_sha256"]:
        return {"verdict": "BLOCK", "reason": "current report hash differs from manifest; re-extract"}
    expected = build_manifest(report, decimal(manifest["requested_ratio"]))
    if canonical(expected) != canonical(manifest):
        return {"verdict": "BLOCK", "reason": "manifest does not match reconstruction from current report"}
    if not manifest["eligible_numeric_table_cells"] or not manifest["items"]:
        return {"verdict": "BLOCK", "reason": "no eligible numeric Markdown table cells were extracted"}
    payload = require_object(payload, "results payload")
    if set(payload) != {"manifest_sha256", "results"} or payload["manifest_sha256"] != manifest["manifest_sha256"] or not isinstance(payload["results"], list):
        raise error("results must contain exactly manifest_sha256 and results")
    items = {item["id"]: item for item in manifest["items"]}
    results = [require_object(result, "result") for result in payload["results"]]
    ids = [result.get("id") for result in results]
    if len(ids) != len(set(ids)) or set(ids) != set(items):
        raise error("results must cover every manifest ID exactly once")
    outcomes, overall = [], "PASS"
    for result in results:
        item, policy = items[result["id"]], items[result["id"]]["required_tier_policy"]
        fresh = decimal(result.get("fresh_value"))
        source = source_valid(result.get("source"), policy["allowed_tiers"], "source")
        differences = [direct_discrepancy_percent(decimal(item["reported_value"]), fresh)]
        if source["tier"] == "Tier 2":
            secondary = source_valid(result.get("secondary_source"), ["Tier 1", "Tier 2"], "secondary_source")
            if normalized_vendor_domain(secondary["source_url"]) == normalized_vendor_domain(source["source_url"]):
                raise error("Tier 2 validation requires an independent secondary source")
            secondary_value = decimal(secondary.get("value"))
            differences.append(symmetric_spread_percent([fresh, secondary_value]))
            if not isinstance(result.get("reconciliation"), bool) or not isinstance(result.get("reconciliation_explanation"), str) or not result["reconciliation_explanation"].strip():
                raise error("Tier 2 validation requires boolean reconciliation and explanation")
        maximum = max(differences)
        classification, guidance = classify_discrepancy(maximum)
        status = "PASS" if classification == "CONSISTENT" or (classification == "RECONCILE" and result.get("reconciliation") is True and result.get("reconciliation_explanation", "").strip()) else "RECONCILE" if classification == "RECONCILE" else "BLOCK"
        overall = "BLOCK" if status == "BLOCK" else "RECONCILE_REQUIRED" if status == "RECONCILE" and overall != "BLOCK" else overall
        outcomes.append({"id": result["id"], "field": item["field"], "status": status, "max_difference_pct": str(maximum), "reason": guidance})
    return {"verdict": overall, "manifest_sha256": manifest["manifest_sha256"], "outcomes": outcomes}


def self_test() -> int:
    report = """## Evidence Ledger\n| Data | Value | Alt |\n|---|---:|---:|\n| Current price | $10 | $10 |\n| Revenue | ($0.80)B | -$0.80B |\n| US 10Y government yield | 4.5% | |\n| US 10Y government yield ×2 | 9.0% | |\n\n## 4. Valuation\n| Rate | EPS required g |\n|---|---:|\n| 10Y government yield ×1 | 5% |\n"""
    try:
        manifest = build_manifest(report, MINIMUM_RATIO)
        try:
            build_manifest(report, Decimal("0.14"))
            raise error("minimum ratio regression")
        except ValueError:
            pass
        fields = {item["field"] for item in manifest["items"]}
        if not manifest["eligible_numeric_table_cells"] or not {"government_yield", "government_yield_x2", "payback_eps"}.issubset(fields):
            raise error("table/yield classification regression")
        if {item["reported_value"] for item in extract_points(report) if item["field"] == "revenue"} != {"-0.80"}:
            raise error("currency accounting-negative regression")
        template = results_template(manifest)
        for result, item in zip(template["results"], manifest["items"]):
            result["fresh_value"] = item["reported_value"]
            result["source"] = {"name": "SEC", "tier": "Tier 1", "source_url": "https://www.sec.gov/Archives", "authority_type": "regulator"}
        if evaluate(manifest, template, report)["verdict"] != "PASS":
            raise error("pass regression")
        if evaluate(manifest, template, report + "\nchanged")["verdict"] != "BLOCK":
            raise error("stale report regression")
        if evaluate(build_manifest("## Evidence Ledger\n| A | B |\n|---|---|\n", MINIMUM_RATIO), {"manifest_sha256": "x", "results": []}, "## Evidence Ledger\n| A | B |\n|---|---|\n")["verdict"] != "BLOCK":
            raise error("empty extraction regression")
        with tempfile.TemporaryDirectory() as directory:
            malformed = Path(directory) / "malformed.json"
            malformed.write_text("{", encoding="utf-8")
            try:
                load_json(malformed)
                raise error("malformed JSON regression")
            except ValueError:
                pass
        print("SELF-TEST PASS")
        return 0
    except (ValueError, KeyError, TypeError) as exc:
        print(f"SELF-TEST FAIL: {exc}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic, manual-only report data audit.")
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    extract = commands.add_parser("extract", help="write a manifest and prefilled results template")
    extract.add_argument("--report", type=Path, required=True)
    extract.add_argument("--manifest-out", type=Path, required=True)
    extract.add_argument("--results-out", type=Path, required=True)
    extract.add_argument("--ratio", default="0.15")
    verdict = commands.add_parser("verdict", help="validate results against the exact current report and manifest")
    verdict.add_argument("--report", type=Path, required=True)
    verdict.add_argument("--manifest", type=Path, required=True)
    verdict.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.self_test:
            return self_test()
        if args.command == "extract":
            manifest = build_manifest(args.report.read_text(encoding="utf-8"), decimal(args.ratio))
            args.manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            args.results_out.write_text(json.dumps(results_template(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"WROTE {args.manifest_out} and {args.results_out}: {len(manifest['items'])}/{manifest['eligible_numeric_table_cells']} eligible table cells ({Decimal(manifest['actual_ratio']):.2%})")
            return 0
        if args.command == "verdict":
            outcome = evaluate(load_json(args.manifest), load_json(args.results), args.report.read_text(encoding="utf-8"))
            print(json.dumps(outcome, ensure_ascii=False, indent=2))
            return 0 if outcome["verdict"] == "PASS" else 1
        parser.print_help()
        return 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

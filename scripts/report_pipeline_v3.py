#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_lint import lint_text
from scripts.report_pipeline_v2 import artifact_paths, load_json, write_json
from scripts.report_renderer_v3 import render_audit_markdown, render_reader_markdown
from scripts.report_spec_v2 import SpecError, canonical_json, sha256


def _reader_errors(markdown: str, bundle: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    forbidden = (
        "THEME-", "OBS-", "ARG-", "DRV-", "FACT-", "SRC-", "BUNDLE:",
        "[supports]", "[context]", "[counter_evidence]",
        "Source Registry", "Evidence Ledger", "Claim-Evidence Matrix",
        "Spec hash", "Bundle hash", "hash", "Hash",
        "**核心问题：**", "**发生了什么：**", "**基础判断：**",
        "**最强反方：**", "**综合裁决：**", "**对决策的影响：**", "**什么会推翻判断：**",
    )
    for token in forbidden:
        if token in markdown:
            errors.append(f"reader report contains audit token: {token}")
    required = (
        "## 一页结论",
        "### Action Matrix（唯一执行口径）",
        "### 三条原投资原则",
        "### Base 情景关键假设",
        "### 与上次报告相比",
        "## 1. 决定回报的投资主线",
        "### 最强正反证据与裁决",
        "### 真正决定估值的变量",
        "## 8. 组合约束与执行边界",
        "## 主要来源",
    )
    for token in required:
        if token not in markdown:
            errors.append(f"reader report missing v3 narrative content: {token}")
    for heading in range(1, 10):
        if f"## {heading}." not in markdown:
            errors.append(f"reader research module {heading} missing")
    if markdown.count("### Action Matrix（唯一执行口径）") != 1:
        errors.append("reader report must contain exactly one authoritative Action Matrix")
    if not re.search(r"\[[^\]]+\]\(https://[^)]+\)", markdown):
        errors.append("reader report requires clickable HTTPS source links")
    if bundle and not bundle.get("portfolio_context", {}).get("complete", False):
        if "不能直接执行" not in markdown or bundle["decision"]["existing_position_action"] != "REVIEW":
            errors.append("reader report must disclose blocked portfolio execution and resolve to REVIEW")
    line_count = len(markdown.splitlines())
    if line_count > 360:
        errors.append(f"reader report exceeds v3.1 readability ceiling: {line_count}")
    return errors


def _audit_errors(markdown: str) -> list[str]:
    required = (
        "## Research Graph v3.1", "### Investment Debate", "### Sensitivity Explanation",
        "THEME-", "OBS-", "ARG-", "DRV-", "Accepted:", "Discounted:", "Auto-discounted:",
        "[supports]", "/assumptions/",
    )
    return [f"audit section missing: {token}" for token in required if token not in markdown]


def _source_check(bundle: dict[str, Any]) -> str:
    sources = bundle.get("source_registry", {})
    if not sources:
        return "FAIL"
    for source in sources.values():
        if not str(source.get("url", "")).startswith("https://"):
            return "FAIL"
    return "PASS"


def _calculation_check(bundle: dict[str, Any]) -> str:
    try:
        scenario_irr = Decimal(str(bundle["scenarios"]["base"]["returns"]["irr"]["irr_pct"])) / Decimal(100)
        decision_irr = Decimal(str(bundle["decision"]["valuation"]["base_irr"]))
        Decimal(str(bundle["scenarios"]["base"]["prices"]["target_return"]))
        Decimal(str(bundle["scenarios"]["base"]["prices"]["buy"]))
        if abs(scenario_irr - decision_irr) > Decimal("0.0001"):
            return "FAIL"
        if not bundle.get("derived", {}).get("payback_required_growth"):
            return "FAIL"
    except (KeyError, TypeError, InvalidOperation):
        return "FAIL"
    return "PASS"


def _verification(bundle: dict[str, Any], spec_path: Path, output: Path, audit_path: Path, bundle_path: Path, reader: str, audit: str) -> dict[str, Any]:
    reader_errors = _reader_errors(reader, bundle)
    audit_errors = _audit_errors(audit)
    report_lint_errors = lint_text(reader)
    graph_quality = bundle["research_graph_quality"]
    source_status = _source_check(bundle)
    calculation_status = _calculation_check(bundle)
    checks = {
        "spec_schema": "PASS",
        "data_quality": bundle["data_quality"]["status"],
        "source_closure": source_status,
        "source_urls": bundle["data_quality"]["source_urls"]["status"],
        "calculations": calculation_status,
        "ttm_units": bundle["data_quality"]["ttm_units"]["status"],
        "portfolio_context": bundle["data_quality"]["portfolio_context"]["status"],
        "prior_report_context": bundle["data_quality"]["prior_report_context"]["status"],
        "research_quality": bundle["research_quality"]["status"],
        "research_graph": graph_quality["status"],
        "theme_narrative": "PASS" if graph_quality["themes"] >= 2 and graph_quality["observations"] >= 2 else "FAIL",
        "investment_debate": "PASS" if graph_quality["bull_arguments"] >= 2 and graph_quality["bear_arguments"] >= 2 else "FAIL",
        "sensitivity_explanation": "PASS" if graph_quality["sensitivity_drivers"] >= 2 and graph_quality["high_importance_drivers"] >= 1 else "FAIL",
        "reader_layer_clean": "PASS" if not reader_errors else "FAIL",
        "report_lint": "PASS" if not report_lint_errors else "FAIL",
        "audit_layer_complete": "PASS" if not audit_errors else "FAIL",
        "tamper_binding": "PASS",
    }
    return {
        "schema_version": "report-verification-v3.1",
        "compiler_version": "3.1.0",
        "spec_file": str(spec_path),
        "report_file": str(output),
        "audit_file": str(audit_path),
        "bundle_file": str(bundle_path),
        "checks": checks,
        "reader_errors": reader_errors,
        "report_lint_errors": report_lint_errors,
        "audit_errors": audit_errors,
        "research_quality": bundle["research_quality"],
        "research_graph_quality": graph_quality,
        "spec_hash": bundle["spec_hash"],
        "bundle_hash": bundle["bundle_hash"],
        "reader_markdown_hash": sha256(reader),
        "audit_markdown_hash": sha256(audit),
    }


def build(spec_path: Path, output: Path) -> dict[str, Any]:
    spec = load_json(spec_path)
    bundle = compile_report_v3(spec)
    reader = render_reader_markdown(bundle)
    audit = render_audit_markdown(bundle)
    reader_errors = _reader_errors(reader, bundle)
    audit_errors = _audit_errors(audit)
    report_lint_errors = lint_text(reader)
    if reader_errors or audit_errors or report_lint_errors:
        raise SpecError("; ".join(reader_errors + audit_errors + [f"report lint: {error}" for error in report_lint_errors]))
    bundle_path, verification_path, audit_path = artifact_paths(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(reader, encoding="utf-8")
    audit_path.write_text(audit, encoding="utf-8")
    write_json(bundle_path, bundle)
    verification = _verification(bundle, spec_path, output, audit_path, bundle_path, reader, audit)
    write_json(verification_path, verification)
    return verification


def verify(spec_path: Path, output: Path) -> dict[str, Any]:
    spec = load_json(spec_path)
    expected_bundle = compile_report_v3(spec)
    expected_reader = render_reader_markdown(expected_bundle)
    expected_audit = render_audit_markdown(expected_bundle)
    bundle_path, verification_path, audit_path = artifact_paths(output)
    if not all(path.exists() for path in (output, audit_path, bundle_path, verification_path)):
        raise SpecError("reader, audit, bundle, and verification files must all exist")
    actual_reader = output.read_text(encoding="utf-8")
    actual_audit = audit_path.read_text(encoding="utf-8")
    actual_bundle = load_json(bundle_path)
    actual_verification = load_json(verification_path)
    expected_verification = _verification(expected_bundle, spec_path, output, audit_path, bundle_path, expected_reader, expected_audit)
    errors: list[str] = []
    if actual_reader != expected_reader:
        errors.append("Reader Markdown differs from compiler output")
    if actual_audit != expected_audit:
        errors.append("Audit Markdown differs from compiler output")
    if canonical_json(actual_bundle) != canonical_json(expected_bundle):
        errors.append("Bundle differs from compiler output")
    if canonical_json(actual_verification) != canonical_json(expected_verification):
        errors.append("Verification differs from compiler output")
    errors.extend(_reader_errors(actual_reader, actual_bundle))
    errors.extend(_audit_errors(actual_audit))
    errors.extend(f"report lint: {error}" for error in lint_text(actual_reader))
    if errors:
        raise SpecError("; ".join(errors))
    return {
        "status": "PASS",
        "errors": [],
        "spec_hash": expected_bundle["spec_hash"],
        "bundle_hash": expected_bundle["bundle_hash"],
        "reader_markdown_hash": sha256(expected_reader),
        "audit_markdown_hash": sha256(expected_audit),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research Graph equity report compiler v3")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--spec", type=Path, required=True)
        cmd.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.spec, args.output) if args.command == "build" else verify(args.spec, args.output)
    except (SpecError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

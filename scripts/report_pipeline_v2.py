#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.report_compiler_v21 import compile_report_v21
from scripts.report_renderer_readable_v212 import render_audit_markdown, render_reader_markdown
from scripts.report_spec_v2 import SpecError, canonical_json, sha256


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SpecError("spec must be a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def artifact_paths(output: Path) -> tuple[Path, Path, Path]:
    return (
        output.with_suffix(output.suffix + ".bundle.json"),
        output.with_suffix(output.suffix + ".verification.json"),
        output.with_suffix(".audit" + output.suffix),
    )


def _verification(
    bundle: dict[str, Any],
    spec_path: Path,
    output: Path,
    audit_path: Path,
    bundle_path: Path,
    reader_markdown: str,
    audit_markdown: str,
) -> dict[str, Any]:
    quality_checks = bundle["research_quality"]["checks"]
    checks = {
        "spec_schema": "PASS",
        "source_closure": "PASS",
        "assumption_scope": "PASS",
        "calculations": "PASS",
        "decision_policy_completeness": "PASS",
        "decision_robustness": "PASS" if bundle["decision"]["robustness"]["stable"] else "REVIEW",
        "legacy_tables_absent": "PASS",
        "reader_layer_clean": "PASS",
        "audit_layer_complete": "PASS",
    }
    checks.update({name: result["status"] for name, result in quality_checks.items()})
    return {
        "schema_version": "report-verification-v2.1.2",
        "compiler_version": "2.1.2",
        "spec_file": str(spec_path),
        "report_file": str(output),
        "audit_file": str(audit_path),
        "bundle_file": str(bundle_path),
        "checks": checks,
        "research_quality": bundle["research_quality"],
        "spec_hash": bundle["spec_hash"],
        "bundle_hash": bundle["bundle_hash"],
        "reader_markdown_hash": sha256(reader_markdown),
        "audit_markdown_hash": sha256(audit_markdown),
    }


def build(spec_path: Path, output: Path) -> dict[str, Any]:
    spec = load_json(spec_path)
    bundle = compile_report_v21(spec)
    reader_markdown = render_reader_markdown(bundle)
    audit_markdown = render_audit_markdown(bundle)
    bundle_path, verification_path, audit_path = artifact_paths(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(reader_markdown, encoding="utf-8")
    audit_path.write_text(audit_markdown, encoding="utf-8")
    write_json(bundle_path, bundle)
    verification = _verification(
        bundle,
        spec_path,
        output,
        audit_path,
        bundle_path,
        reader_markdown,
        audit_markdown,
    )
    write_json(verification_path, verification)
    return verification


def _reader_errors(markdown: str) -> list[str]:
    errors: list[str] = []
    forbidden = (
        "## Source Registry",
        "## Evidence Ledger",
        "## Claim-Evidence Matrix",
        "### Build Manifest",
        "FACT-",
        "BUNDLE:",
        "[supports]",
        "Spec hash",
        "Bundle hash",
    )
    for token in forbidden:
        if token in markdown:
            errors.append(f"reader report contains audit token: {token}")
    for heading in range(1, 10):
        if f"## {heading}." not in markdown:
            errors.append(f"reader research module {heading} missing")
    required_text = ("Base 5年 IRR", "最低目标回报", "目标回报价格", "TTM EPS", "TTM 经营利润率", "TTM FCF")
    for token in required_text:
        if token not in markdown:
            errors.append(f"reader report missing key decision content: {token}")
    line_count = len(markdown.splitlines())
    if line_count < 120 or line_count > 300:
        errors.append(f"reader report line count outside readability budget: {line_count}")
    return errors


def _audit_errors(markdown: str) -> list[str]:
    required = (
        "### Build Manifest",
        "## Source Registry",
        "## Evidence Ledger",
        "## Quarterly TTM Bridge",
        "## Scenario Assumptions and Valuation",
        "## Decision Policy Evaluation",
        "## Claim-Evidence Matrix",
        "## Verification",
    )
    errors = [f"audit section missing: {token}" for token in required if token not in markdown]
    if "Legacy Checker Compatibility" in markdown or "Legacy Compatibility" in markdown:
        errors.append("legacy compatibility tables are forbidden")
    return errors


def verify(spec_path: Path, output: Path) -> dict[str, Any]:
    spec = load_json(spec_path)
    expected_bundle = compile_report_v21(spec)
    expected_reader = render_reader_markdown(expected_bundle)
    expected_audit = render_audit_markdown(expected_bundle)
    bundle_path, verification_path, audit_path = artifact_paths(output)
    if not output.exists() or not audit_path.exists() or not bundle_path.exists() or not verification_path.exists():
        raise SpecError("reader report, audit appendix, bundle, and verification files must all exist")
    actual_reader = output.read_text(encoding="utf-8")
    actual_audit = audit_path.read_text(encoding="utf-8")
    actual_bundle = load_json(bundle_path)
    actual_verification = load_json(verification_path)
    expected_verification = _verification(
        expected_bundle,
        spec_path,
        output,
        audit_path,
        bundle_path,
        expected_reader,
        expected_audit,
    )
    errors: list[str] = []
    if actual_reader != expected_reader:
        errors.append("Reader Markdown differs from compiler output")
    if actual_audit != expected_audit:
        errors.append("Audit Markdown differs from compiler output")
    if canonical_json(actual_bundle) != canonical_json(expected_bundle):
        errors.append("Bundle differs from compiler output")
    if canonical_json(actual_verification) != canonical_json(expected_verification):
        errors.append("Verification differs from compiler output")
    errors.extend(_reader_errors(actual_reader))
    errors.extend(_audit_errors(actual_audit))
    if "未提供叙事内容" in actual_reader:
        errors.append("thin narrative placeholder is forbidden")
    result = {
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
        "spec_hash": expected_bundle["spec_hash"],
        "bundle_hash": expected_bundle["bundle_hash"],
        "reader_markdown_hash": sha256(expected_reader),
        "audit_markdown_hash": sha256(expected_audit),
    }
    if errors:
        raise SpecError("; ".join(errors))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Single-source reader-first equity report compiler v2.1.2")
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

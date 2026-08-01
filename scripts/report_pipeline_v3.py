#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_pipeline_v2 import artifact_paths, load_json, write_json
from scripts.report_renderer_v3 import render_audit_markdown, render_reader_markdown
from scripts.report_spec_v2 import SpecError, canonical_json, sha256


def _reader_errors(markdown: str) -> list[str]:
    errors: list[str] = []
    forbidden = ("FACT-", "BUNDLE:", "[supports]", "## Source Registry", "## Claim-Evidence Matrix", "Spec hash", "Bundle hash")
    for token in forbidden:
        if token in markdown:
            errors.append(f"reader report contains audit token: {token}")
    required = (
        "## 1. 投资叙事与核心矛盾",
        "### Bull vs Bear 投资辩论",
        "### 哪些假设真正决定估值",
        "**发生了什么：**",
        "**最强反方：**",
        "**综合裁决：**",
        "**什么会推翻判断：**",
    )
    for token in required:
        if token not in markdown:
            errors.append(f"reader report missing v3 narrative content: {token}")
    for heading in range(1, 10):
        if f"## {heading}." not in markdown:
            errors.append(f"reader research module {heading} missing")
    line_count = len(markdown.splitlines())
    if line_count < 170 or line_count > 420:
        errors.append(f"reader report line count outside v3 budget: {line_count}")
    return errors


def _audit_errors(markdown: str) -> list[str]:
    required = ("## Research Graph v3", "### Investment Debate", "### Sensitivity Explanation", "THEME-", "ARG-", "DRV-")
    return [f"audit section missing: {token}" for token in required if token not in markdown]


def _verification(bundle: dict[str, Any], spec_path: Path, output: Path, audit_path: Path, bundle_path: Path, reader: str, audit: str) -> dict[str, Any]:
    reader_errors = _reader_errors(reader)
    audit_errors = _audit_errors(audit)
    graph_quality = bundle["research_graph_quality"]
    checks = {
        "spec_schema": "PASS",
        "source_closure": "PASS",
        "calculations": "PASS",
        "research_quality": bundle["research_quality"]["status"],
        "research_graph": graph_quality["status"],
        "theme_narrative": "PASS" if graph_quality["themes"] >= 3 and graph_quality["observations"] >= 6 else "FAIL",
        "investment_debate": "PASS" if graph_quality["bull_arguments"] >= 3 and graph_quality["bear_arguments"] >= 3 else "FAIL",
        "sensitivity_explanation": "PASS" if graph_quality["sensitivity_drivers"] >= 3 and graph_quality["high_importance_drivers"] >= 1 else "FAIL",
        "reader_layer_clean": "PASS" if not reader_errors else "FAIL",
        "audit_layer_complete": "PASS" if not audit_errors else "FAIL",
        "tamper_binding": "PASS",
    }
    return {
        "schema_version": "report-verification-v3.0",
        "compiler_version": "3.0.0",
        "spec_file": str(spec_path),
        "report_file": str(output),
        "audit_file": str(audit_path),
        "bundle_file": str(bundle_path),
        "checks": checks,
        "reader_errors": reader_errors,
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
    reader_errors = _reader_errors(reader)
    audit_errors = _audit_errors(audit)
    if reader_errors or audit_errors:
        raise SpecError("; ".join(reader_errors + audit_errors))
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
    errors.extend(_reader_errors(actual_reader))
    errors.extend(_audit_errors(actual_audit))
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

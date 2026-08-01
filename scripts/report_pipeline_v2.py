#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.report_renderer_v2 import render_markdown
from scripts.report_spec_v2 import SpecError, canonical_json, compile_spec, sha256


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SpecError("spec must be a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def artifact_paths(output: Path) -> tuple[Path, Path]:
    return output.with_suffix(output.suffix + ".bundle.json"), output.with_suffix(output.suffix + ".verification.json")


def build(spec_path: Path, output: Path) -> dict[str, Any]:
    spec = load_json(spec_path)
    bundle = compile_spec(spec)
    markdown = render_markdown(bundle)
    bundle_path, verification_path = artifact_paths(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    write_json(bundle_path, bundle)
    verification = {
        "schema_version": "report-verification-v2",
        "compiler_version": bundle["compiler_version"],
        "spec_file": str(spec_path),
        "report_file": str(output),
        "bundle_file": str(bundle_path),
        "checks": {
            "spec_schema": "PASS",
            "source_closure": "PASS",
            "assumption_scope": "PASS",
            "calculations": "PASS",
            "decision_policy_completeness": "PASS",
            "decision_robustness": "PASS" if bundle["decision"]["robustness"]["stable"] else "REVIEW",
            "legacy_tables_absent": "PASS",
        },
        "spec_hash": bundle["spec_hash"],
        "bundle_hash": bundle["bundle_hash"],
        "markdown_hash": sha256(markdown),
    }
    write_json(verification_path, verification)
    return verification


def verify(spec_path: Path, output: Path) -> dict[str, Any]:
    spec = load_json(spec_path)
    expected_bundle = compile_spec(spec)
    expected_markdown = render_markdown(expected_bundle)
    bundle_path, verification_path = artifact_paths(output)
    if not output.exists() or not bundle_path.exists() or not verification_path.exists():
        raise SpecError("report, bundle, and verification files must all exist")
    actual_markdown = output.read_text(encoding="utf-8")
    actual_bundle = load_json(bundle_path)
    actual_verification = load_json(verification_path)
    errors: list[str] = []
    if actual_markdown != expected_markdown:
        errors.append("Markdown differs from compiler output")
    if canonical_json(actual_bundle) != canonical_json(expected_bundle):
        errors.append("Bundle differs from compiler output")
    if actual_verification.get("spec_hash") != expected_bundle["spec_hash"]:
        errors.append("verification spec_hash mismatch")
    if actual_verification.get("bundle_hash") != expected_bundle["bundle_hash"]:
        errors.append("verification bundle_hash mismatch")
    if actual_verification.get("markdown_hash") != sha256(expected_markdown):
        errors.append("verification markdown_hash mismatch")
    if "Legacy Checker Compatibility" in actual_markdown or "Legacy Compatibility" in actual_markdown:
        errors.append("legacy compatibility tables are forbidden in v2")
    result = {
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
        "spec_hash": expected_bundle["spec_hash"],
        "bundle_hash": expected_bundle["bundle_hash"],
        "markdown_hash": sha256(expected_markdown),
    }
    if errors:
        raise SpecError("; ".join(errors))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Single-source equity report compiler v2")
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

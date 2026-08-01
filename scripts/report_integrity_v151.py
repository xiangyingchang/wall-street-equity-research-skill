#!/usr/bin/env python3
"""v1.5.1 runtime artifact binding and report reference-integrity CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.integrity_checker import validate_text
from scripts.integrity_common import Finding, build_artifact, scenario_value

__all__ = ["Finding", "build_artifact", "scenario_value", "validate_text"]


def read_json(path: str) -> dict[str, Any]:
    import sys
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict): raise ValueError("JSON input must be an object")
    return value


def emit(value: dict[str, Any], output: str | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    Path(output).write_text(text, encoding="utf-8") if output else print(text, end="")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="command", required=True)
    for name in ["wrap-artifact", "scenario-value"]:
        cmd = sub.add_parser(name); cmd.add_argument("--input", required=True); cmd.add_argument("--output")
    check = sub.add_parser("check"); check.add_argument("report", type=Path); check.add_argument("--artifacts-dir", type=Path)
    args = p.parse_args(argv)
    if args.command == "wrap-artifact":
        x = read_json(args.input); emit(build_artifact(runtime_name=str(x.get("runtime_name", "")), artifact_id=str(x.get("artifact_id", "")), input_refs=[str(i) for i in x.get("input_refs", [])], inputs=x.get("inputs", {}), outputs=x.get("outputs", {})), args.output); return 0
    if args.command == "scenario-value": emit(scenario_value(read_json(args.input)), args.output); return 0
    findings = validate_text(args.report.read_text(encoding="utf-8"), artifacts_dir=args.artifacts_dir, require_artifacts=True)
    for item in findings: print(f"{item.level}: {item.message}")
    errors = [x for x in findings if x.level == "ERROR"]
    if errors: print(f"FAIL: {len(errors)} v1.5.1 integrity error(s)"); return 1
    print("PASS: runtime binding and reference integrity"); return 0


if __name__ == "__main__": raise SystemExit(main())

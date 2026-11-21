#!/usr/bin/env python3
"""Run one bounded prompt in a fresh Codex session; never promote candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


PROFILES = {
    "sol": ("gpt-6.1-sol", "medium"),
    "terra": ("gpt-6.1-terra", "high"),
    "luna": ("gpt-6-luna", "max"),
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "terra/luna are experimental: candidate.md is never an accepted result. "
            "The owner must compare it with sol using identical prompt bytes (check "
            "prompt_sha256), then pass the task's semantic gate before defaulting "
            "to a lower tier. Commercial judgment, synthesis and final verdicts "
            "must use --task judgment --profile sol. No automatic promotion."
        ),
    )
    result.add_argument("--profile", choices=PROFILES, default="sol")
    result.add_argument("--task", required=True,
                        choices=("extract", "format", "error", "section", "judgment"))
    result.add_argument("--input", type=Path, required=True, help="UTF-8 prompt file only")
    result.add_argument("--out", type=Path, required=True, help="New run directory; existing paths are refused")
    result.add_argument("--codex", default="codex", help="Codex executable name or path (resolved with shutil.which)")
    return result


def run(args: argparse.Namespace) -> int:
    if args.task == "judgment" and args.profile != "sol":
        raise ValueError("judgment requires sol/medium; lower tiers are experimental mechanical tasks only")
    prompt = args.input.expanduser().read_bytes()
    if not prompt.strip():
        raise ValueError("prompt file is empty")
    prompt.decode("utf-8")  # Fail before creating outputs for invalid input.
    executable = shutil.which(args.codex)
    if executable is None:
        raise ValueError(f"Codex executable not found: {args.codex}")
    out = args.out.expanduser().absolute()
    out.mkdir()  # Atomic exclusive reservation, including protection against symlinks.
    model, effort = PROFILES[args.profile]
    experimental = args.profile != "sol"
    output = out / ("candidate.md" if experimental else "output.md")
    argv = [
        executable, "exec", "--ignore-user-config", "--ephemeral",
        "--skip-git-repo-check", "--sandbox", "read-only",
        "-c", 'approval_policy="never"', "-c", 'web_search="disabled"',
        "--model", model, "-c", f'model_reasoning_effort="{effort}"',
        "--color", "never", "-o", str(output), "-",
    ]
    started = time.monotonic()
    exit_code = 1
    try:
        with (out / "run.log").open("ab") as log, tempfile.TemporaryDirectory(prefix="model-task-") as cwd:
            # A clean working root and plain `exec` prevent history/fork reuse.
            log.write(f"profile={args.profile} experimental={experimental}\n".encode())
            log.flush()
            try:
                exit_code = subprocess.run(argv, input=prompt, cwd=cwd, stdout=log,
                                           stderr=subprocess.STDOUT, check=False).returncode
            except OSError as exc:
                log.write(f"launcher error: {exc}\n".encode())
                exit_code = 127
            if exit_code == 0 and (not output.is_file() or not output.stat().st_size):
                log.write(b"launcher error: Codex produced no final message\n")
                exit_code = 1
    finally:
        metrics = {
            "model": model, "effort": effort, "task": args.task,
            "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "exit_code": exit_code, "experimental": experimental,
            "accepted": False,
        }
        with (out / "run-metrics.jsonl").open("a", encoding="utf-8") as telemetry:
            telemetry.write(json.dumps(metrics, ensure_ascii=False) + "\n")
    if exit_code == 0:
        print(f"{'Experimental candidate' if experimental else 'Output'}: {output}")
        print("Acceptance pending: owner must compare identical inputs and apply the semantic gate.")
    return exit_code


def main(argv: list[str] | None = None) -> int:
    cli = parser()
    args = cli.parse_args(argv)
    try:
        return run(args)
    except (OSError, ValueError) as exc:
        cli.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())

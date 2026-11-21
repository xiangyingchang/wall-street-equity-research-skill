#!/usr/bin/env python3
"""Record a verified native Notion MCP delivery and clean a single research run."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from evidence_pack_v3 import read, sha_file
from research_pack import write_pack_atomic

PAGE_URL = re.compile(r"https://(?:app\.notion\.com/p/|(?:www\.)?notion\.so/)[0-9a-f]{32}")
PERSPECTIVES = {"business", "financial", "challenge", "risk"}
ARCHIVE = "audit-package.zip"
EVENTS = ".delivery-events.jsonl"
MAX_MEMBER = 2 * 1024 * 1024


def event(run: Path, stage: str, result: str, reason: str = "") -> None:
    # Never persist exception text, subprocess output, credentials or portfolio data.
    row = {"time": datetime.now(timezone.utc).isoformat(), "stage": stage,
           "result": result, "reason": reason}
    with (run / EVENTS).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def checked_stage(run: Path, stage: str, operation):
    try:
        result = operation()
    except Exception as error:
        reason = type(error).__name__
        if isinstance(error, subprocess.CalledProcessError):
            reason += f" (exit {error.returncode})"
        event(run, stage, "failed", reason)
        raise
    event(run, stage, "passed")
    return result


def verify_archive(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("audit archive is corrupt")
        manifest = json.loads(archive.read("manifest.json"))
        expected = {"spec.json", "evidence.json", "audit.md", "bundle.json", "verification.json",
                    "semantic-review.json", "sources.json", "delivery-summary.json"}
        if (set(manifest["files"]) != expected or set(archive.namelist()) != expected | {"manifest.json"}
                or len(archive.namelist()) != len(expected) + 1 or not manifest.get("compiler_version")):
            raise ValueError("audit archive manifest is incomplete")
        for name, digest in manifest["files"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("audit archive hash mismatch")


def create_archive(run: Path, reader: Path, args: argparse.Namespace, receipt: dict) -> None:
    paths = {"spec.json": run / args.spec, "evidence.json": run / args.evidence_pack,
             "audit.md": reader.with_suffix(".audit.md"), "bundle.json": run / (reader.name + ".bundle.json"),
             "verification.json": run / (reader.name + ".verification.json"),
             "semantic-review.json": run / args.semantic_review}
    files = {}
    for name, path in paths.items():
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MEMBER:
            raise ValueError("audit input missing, unsafe, or too large")
        files[name] = path.read_bytes()
    # Fail closed on recognizable secrets or a complete holdings collection. Do not
    # silently redact compiler-bound data: an operator must prepare safe inputs.
    sensitive = re.compile(rb'(?i)(?:"(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|private[_-]?key|holdings|positions)"\s*:\s*(?!null|\[\s*\]|\{\s*\})|bearer\s+[a-z0-9._-]{12,}|sk-[a-z0-9_-]{16,})')
    if any(sensitive.search(data) for data in files.values()):
        raise ValueError("audit input contains sensitive fields; sanitize before delivery")
    spec = json.loads(files["spec.json"])
    verification = json.loads(files["verification.json"])
    files["sources.json"] = json.dumps(spec["sources"], ensure_ascii=False, indent=2).encode()
    summary = {"readback": "operator compared fetched Notion content and status", "receipt": receipt,
               "events": [json.loads(line) for line in (run / EVENTS).read_text().splitlines()]}
    files["delivery-summary.json"] = json.dumps(summary, ensure_ascii=False, indent=2).encode()
    manifest = {"compiler_version": verification["compiler_version"],
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    fd, tmp = tempfile.mkstemp(prefix=".audit-", suffix=".zip", dir=run)
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        verify_archive(Path(tmp))
        os.replace(tmp, run / ARCHIVE)
    finally:
        Path(tmp).unlink(missing_ok=True)


def update_archive_events(run: Path) -> None:
    path = run / ARCHIVE
    verify_archive(path)
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist() if name != "manifest.json"}
        manifest = json.loads(archive.read("manifest.json"))
    summary = json.loads(files["delivery-summary.json"])
    events = [json.loads(line) for line in (run / EVENTS).read_text().splitlines()]
    prefix = summary["events"]
    summary["events"] += events[len(prefix):] if events[:len(prefix)] == prefix else events
    files["delivery-summary.json"] = json.dumps(summary, ensure_ascii=False, indent=2).encode()
    manifest["files"]["delivery-summary.json"] = hashlib.sha256(files["delivery-summary.json"]).hexdigest()
    fd, tmp = tempfile.mkstemp(prefix=".audit-", suffix=".zip", dir=run)
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        verify_archive(Path(tmp))
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def read_receipt(path: Path, reader: Path) -> dict:
    receipt = read(path)
    expected = {
        "notion_url": receipt["notion_url"],
        "report_path": str(reader.resolve()),
        "sha256": sha_file(reader),
    }
    if receipt != expected or not PAGE_URL.fullmatch(receipt["notion_url"]):
        raise ValueError("delivery receipt does not match the local Reader")
    return receipt


def finalize(args: argparse.Namespace) -> dict:
    run = args.reader.parent
    if not run.is_absolute() or run.is_symlink() or run.resolve().parent != args.runs_root.resolve():
        raise ValueError("Reader must be in a dedicated run directory directly under the runs root")
    reader = args.reader
    receipt_path = run / "delivery.json"
    if (run / ARCHIVE).is_symlink() or (run / EVENTS).is_symlink():
        raise ValueError("archive and event paths must not be symlinks")
    if not reader.is_file() or reader.is_symlink() or reader.suffix != ".md" or receipt_path.is_symlink():
        raise ValueError("expected a local Markdown Reader and a regular receipt path")
    digest = sha_file(reader)
    if not PAGE_URL.fullmatch(args.notion_url) or digest != args.readback_reader_sha256:
        raise ValueError("Notion page URL or readback Reader hash is invalid")
    receipt = {"notion_url": args.notion_url, "report_path": str(reader), "sha256": digest}
    names = {
        args.spec, args.evidence_pack, args.semantic_review, reader.with_suffix(".audit.md").name,
        reader.name + ".bundle.json", reader.name + ".verification.json", *args.remove,
    }
    if any(not name or Path(name).name != name or name in {".", "..", reader.name, receipt_path.name, ARCHIVE, EVENTS} for name in names):
        raise ValueError("cleanup accepts only names of intermediate artifacts in this run")
    if reader != reader.resolve():
        raise ValueError("use the canonical report path")
    directory_fd = os.open(run, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(directory_fd, fcntl.LOCK_EX)
        if receipt_path.exists():
            if read_receipt(receipt_path, reader) != receipt:
                raise ValueError("delivery already recorded for a different Notion page")
            verify_archive(run / ARCHIVE)
        else:
            def preflight():
                if not getattr(args, "privacy_reviewed", False):
                    raise ValueError("privacy review of audit inputs is required before delivery")
                review = read(run / args.semantic_review)
                if review.get("status") != "PASS" or review.get("reader_sha256") != digest or set(review.get("perspectives", [])) != PERSPECTIVES:
                    raise ValueError("full Reader semantic review missing or stale")
                # The existing verifier binds the path spelling used by build.
                verification = read(run / (reader.name + ".verification.json"))
                spec_arg = verification["spec_file"]
                output_arg = verification["report_file"]
                if ((run / spec_arg).resolve() != run / args.spec or (run / output_arg).resolve() != reader):
                    raise ValueError("build with absolute paths or relative to the run directory before delivery")
                return spec_arg, output_arg
            spec_arg, output_arg = checked_stage(run, "preflight", preflight)
            scripts = Path(__file__).resolve().parent
            checked_stage(run, "verify", lambda: subprocess.run(
                [sys.executable, str(scripts / "report_pipeline_v3.py"), "verify", "--spec", spec_arg,
                 "--output", output_arg, "--evidence-pack", str(run / args.evidence_pack)], cwd=run, check=True,
            ))
            checked_stage(run, "lint", lambda: subprocess.run([sys.executable, str(scripts / "report_lint.py"), str(reader)], check=True))
            if sha_file(reader) != digest:
                raise ValueError("Reader changed during verification")
            event(run, "notion_readback", "passed")
            checked_stage(run, "archive", lambda: create_archive(run, reader, args, receipt))
            verify_archive(run / ARCHIVE)
            write_pack_atomic(receipt_path, receipt, lock_held=True)
        def cleanup():
            for name in sorted(names):
                path = run / name
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink(missing_ok=True)
        checked_stage(run, "cleanup", cleanup)
        update_archive_events(run)
        (run / EVENTS).unlink(missing_ok=True)
    finally:
        os.close(directory_fd)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reader", type=Path, required=True)
    parser.add_argument("--notion-url", required=True)
    parser.add_argument("--readback-reader-sha256", required=True, help="SHA-256 of the local Reader compared to the fetched Notion page")
    parser.add_argument("--runs-root", type=Path, default=Path.home() / "research-runs")
    parser.add_argument("--spec", default="spec.json")
    parser.add_argument("--evidence-pack", default="evidence.json")
    parser.add_argument("--semantic-review", default="semantic-review.json")
    parser.add_argument("--privacy-reviewed", action="store_true", help="Confirm audit inputs were reviewed for secrets and complete personal holdings")
    parser.add_argument("--remove", action="append", default=[], help="Additional run-owned intermediate artifact name, repeatable")
    try:
        finalize(parser.parse_args())
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

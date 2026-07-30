#!/usr/bin/env python3
"""Create a new Obsidian equity report from the canonical template."""

from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path
import tempfile

from report_audit import recognize_fields
from research_pack import (
    InputError,
    ResearchPackError,
    StateConflict,
    build_initial_pack,
    canonical_json_bytes,
    load_pack,
    pack_write_lock,
    reject_symlink,
)


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_DIR / "templates" / "full-report.md"


def render(template: str, values: dict[str, str]) -> str:
    text = template
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _stage_bytes(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return temporary
    except OSError as error:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise InputError(f"cannot stage output for {path}: {error}") from error


def _paths_collide(first: Path, second: Path) -> bool:
    if first.expanduser().resolve(strict=False) == second.expanduser().resolve(strict=False):
        return True
    if first.exists() and second.exists():
        try:
            return os.path.samefile(first, second)
        except OSError:
            return False
    return False


def _write_transaction(
    report_path: Path,
    report_payload: bytes,
    pack_path: Path | None,
    pack_payload: bytes | None,
    write_pack: bool,
    *,
    lock_held: bool = False,
) -> None:
    if write_pack and pack_path is not None and not lock_held:
        with pack_write_lock(pack_path):
            if pack_path.exists():
                raise StateConflict(
                    f"pack was created by another cooperative writer: {pack_path}"
                )
            return _write_transaction(
                report_path,
                report_payload,
                pack_path,
                pack_payload,
                write_pack,
                lock_held=True,
            )
    report_temporary: Path | None = None
    pack_temporary: Path | None = None
    report_backup: Path | None = None
    pack_backup: Path | None = None
    report_existed = report_path.exists()
    report_replaced = False
    pack_replaced = False
    try:
        report_temporary = _stage_bytes(report_path, report_payload)
        if pack_path is not None and pack_payload is not None:
            pack_temporary = _stage_bytes(pack_path, pack_payload)
        if report_existed:
            report_backup = _stage_bytes(report_path, report_path.read_bytes())
        # Stage the pre-existing pack bytes so a failed pack replace can restore
        # the original file instead of leaving it missing or partially written.
        if write_pack and pack_path is not None and pack_path.exists():
            pack_backup = _stage_bytes(pack_path, pack_path.read_bytes())

        os.replace(report_temporary, report_path)
        report_temporary = None
        report_replaced = True
        if write_pack and pack_path is not None and pack_temporary is not None:
            os.replace(pack_temporary, pack_path)
            pack_temporary = None
            pack_replaced = True
    except OSError as error:
        # If the pack replace failed after the report committed, the transaction
        # is not atomic: roll back the report too, and restore the original pack
        # bytes if this run was overwriting an existing pack.
        if pack_replaced and pack_backup is not None:
            try:
                os.replace(pack_backup, pack_path)
                pack_backup = None
            except OSError as rollback_error:
                raise InputError(
                    f"output transaction failed and pack restore failed: {rollback_error}"
                ) from rollback_error
        if report_replaced:
            try:
                if report_backup is not None:
                    os.replace(report_backup, report_path)
                    report_backup = None
                else:
                    report_path.unlink(missing_ok=True)
            except OSError as rollback_error:
                raise InputError(
                    f"output transaction failed and report rollback failed: {rollback_error}"
                ) from rollback_error
        raise InputError(f"output transaction failed: {error}") from error
    finally:
        for temporary in (report_temporary, pack_temporary, report_backup, pack_backup):
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a report skeleton from templates/full-report.md.")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--verdict", default="TODO")
    parser.add_argument("--action", default="TODO")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--research-pack",
        nargs="?",
        const="AUTO",
        metavar="PATH",
        help="Initialize research-pack-v1; omit PATH to place it beside the report.",
    )
    parser.add_argument(
        "--previous-report",
        type=Path,
        help="Prior report recorded in --research-pack continuity metadata.",
    )
    args = parser.parse_args()

    try:
        if args.previous_report is not None and args.research_pack is None:
            raise InputError("--previous-report requires --research-pack")
        for label, value in (
            ("ticker", args.ticker),
            ("company", args.company),
            ("market", args.market),
            ("verdict", args.verdict),
            ("action", args.action),
        ):
            if not value.strip():
                raise InputError(f"--{label} must be nonempty")
        try:
            report_date = date.fromisoformat(args.date)
        except ValueError as error:
            raise InputError("--date must be a valid ISO date (YYYY-MM-DD)") from error
        if report_date.isoformat() != args.date:
            raise InputError("--date must use canonical YYYY-MM-DD form")

        reject_symlink(args.out, "report")
        if args.out.exists() and not args.force:
            raise StateConflict(f"output exists, pass --force to overwrite: {args.out}")

        pack_status = None
        pack_path = None
        pack = None
        write_pack = False
        if args.research_pack is not None:
            pack_path = (
                args.out.with_suffix(".research-pack.json")
                if args.research_pack == "AUTO"
                else Path(args.research_pack)
            )
            reject_symlink(pack_path, "pack")
            if _paths_collide(args.out, pack_path):
                raise InputError("report and pack paths must be different files")
            pack = build_initial_pack(
                ticker=args.ticker,
                market=args.market,
                report=args.out,
                previous_report=args.previous_report,
            )
            if pack_path.exists():
                if load_pack(pack_path) != pack:
                    raise StateConflict(f"pack already exists with different content: {pack_path}")
                pack_status = "UNCHANGED"
            else:
                pack_status = "CREATED"
                write_pack = True

        template = TEMPLATE.read_text(encoding="utf-8")
        report = render(
            template,
            {
                "ticker": args.ticker,
                "company": args.company,
                "market": args.market,
                "date": args.date,
                "verdict": args.verdict,
                "action": args.action,
            },
        )
        recognition = recognize_fields(report)
        if recognition["status"] != "PASS":
            raise InputError(f"generated skeleton failed field recognition: {recognition}")
        _write_transaction(
            args.out,
            report.encode("utf-8"),
            pack_path,
            canonical_json_bytes(pack, pretty=True) if pack is not None else None,
            write_pack,
        )
    except OSError as error:
        raise SystemExit(f"ERROR: output I/O failed: {error}") from error
    except ResearchPackError as error:
        raise SystemExit(f"ERROR: {error}") from error

    print(args.out)
    if pack_path is not None:
        print(f"RESEARCH PACK {pack_status}: {pack_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

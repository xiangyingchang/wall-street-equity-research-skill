#!/usr/bin/env python3
"""Focused regressions for deterministic research-pack-v1 recovery state."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))

from research_pack import (  # noqa: E402
    CHECKPOINT_ORDER,
    InputError,
    StateConflict,
    add_fact,
    add_source,
    build_initial_pack,
    canonicalize_url,
    checkpoint_hash,
    lock_valuation,
    pack_write_lock,
    revise_valuation,
    schema_issues,
    set_checkpoint,
    source_id,
    status_payload,
    write_pack_atomic,
)
from new_report import _write_transaction  # noqa: E402


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def source_payload(
    url: str = "https://Example.COM:443/filing/#section",
    *,
    title: str = "Annual report",
) -> dict[str, object]:
    return {
        "url": url,
        "title": title,
        "publisher": "Example Corp",
        "tier": "Tier 1",
        "published_date": "2026-07-29",
    }


def fact_payload(identifier: str, source: str) -> dict[str, object]:
    return {
        "fact_id": identifier,
        "field": "Revenue",
        "value_type": "decimal",
        "value": "123.4500",
        "unit": "USDm",
        "as_of": "2026-06-30",
        "source_ids": [source],
    }


def basis_payload(source: str, price: str = "100.00") -> dict[str, object]:
    return {
        "price": {
            "value": price,
            "currency": "USD",
            "kind": "regular_close",
            "market_date": "2026-07-29",
            "source_id": source,
        },
        "shares": {
            "value": "10.0",
            "as_of": "2026-06-30",
            "source_id": source,
        },
    }


class ResearchPackUnitTests(unittest.TestCase):
    def test_url_normalization_is_https_conservative_and_query_preserving(self) -> None:
        cases = {
            "HTTPS://Example.COM:443": "https://example.com/",
            "https://Example.COM:443/Filings/Q2/#page=3": "https://example.com/Filings/Q2",
            "https://example.com:8443/a/": "https://example.com:8443/a",
            "https://example.com/a/?b=2&a=1#fragment": "https://example.com/a?b=2&a=1",
            "https://BÜCHER.example/Über/": "https://xn--bcher-kva.example/Über",
            "https://example.com/a//b/": "https://example.com/a//b",
            "https://example.com/a///": "https://example.com/a//",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(canonicalize_url(raw), expected)
        for raw in (
            "http://example.com/a",
            "https:///missing",
            "https://u:p@example.com/a",
            "https://exa mple.com/a",
            "https://exa\nmple.com/a",
            "https://exa\tmple.com/a",
            "https://exa\x7fmple.com/a",
        ):
            with self.subTest(raw=raw), self.assertRaises(InputError):
                canonicalize_url(raw)

        collisions = (
            ("https://example.com/a\nb", "https://example.com/ab"),
            ("https://example.com/a\tb", "https://example.com/ab"),
            ("https://example.com/path?q=a\nb", "https://example.com/path?q=ab"),
            ("https://example.com/path?q=a\tb", "https://example.com/path?q=ab"),
            ("https://example.com/path#frag\nment", "https://example.com/path#fragment"),
            ("https://example.com/a\x7fb", "https://example.com/ab"),
        )
        for dirty, clean in collisions:
            with self.subTest(dirty=dirty), self.assertRaisesRegex(
                InputError, "ASCII control characters or DEL"
            ):
                canonicalize_url(dirty)
            self.assertTrue(canonicalize_url(clean).startswith("https://example.com/"))

    def test_source_registry_is_idempotent_and_conflicts_fail_closed(self) -> None:
        pack = build_initial_pack(ticker="test", market="us", report="report.md")
        self.assertEqual(add_source(pack, source_payload()), "UPDATED")
        identifier = next(iter(pack["sources"]))
        self.assertEqual(identifier, source_id("https://example.com/filing"))
        self.assertEqual(add_source(pack, source_payload()), "UNCHANGED")
        with self.assertRaisesRegex(StateConflict, "metadata conflicts"):
            add_source(pack, source_payload(title="Conflicting title"))
        self.assertEqual(pack["sources"][identifier]["title"], "Annual report")

        with mock.patch("research_pack.source_id", return_value=identifier):
            with self.assertRaisesRegex(StateConflict, "metadata conflicts"):
                add_source(pack, source_payload("https://different.example/filing"))
        self.assertEqual(len(pack["sources"]), 1)

    def test_init_paths_are_absolute_and_symlinks_are_rejected(self) -> None:
        pack = build_initial_pack(
            ticker="TEST",
            market="US",
            report="relative-report.md",
            previous_report="relative-previous.md",
        )
        self.assertTrue(Path(pack["report"]["path"]).is_absolute())
        self.assertTrue(Path(pack["previous_report"]["path"]).is_absolute())
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            target = directory / "target.md"
            target.write_text("target", encoding="utf-8")
            linked = directory / "linked.md"
            linked.symlink_to(target)
            with self.assertRaisesRegex(InputError, "must not be a symlink"):
                build_initial_pack(ticker="TEST", market="US", report=linked)

    def test_fact_schema_canonicalizes_decimal_and_blocks_undefined_reference(self) -> None:
        pack = build_initial_pack(ticker="TEST", market="US", report="report.md")
        add_source(pack, source_payload())
        set_checkpoint(pack, "sources_ready")
        missing = source_id("https://example.com/missing")
        self.assertEqual(add_fact(pack, fact_payload("revenue", missing)), "UPDATED")
        self.assertEqual(pack["facts"]["revenue"]["value"], "123.45")
        self.assertTrue(any("undefined source ID" in issue for issue in schema_issues(pack)))
        with self.assertRaisesRegex(StateConflict, "undefined source IDs"):
            set_checkpoint(pack, "facts_ready")

    def test_typed_decimal_and_date_validation_is_strict(self) -> None:
        identifier = source_id("https://example.com/source")
        fact = fact_payload("revenue", identifier)
        fact["value"] = 123
        with self.assertRaisesRegex(InputError, "Decimal encoded as a string"):
            add_fact(build_initial_pack(ticker="T", market="US", report="r.md"), fact)
        fact = fact_payload("revenue", identifier)
        fact["as_of"] = "2026-02-30"
        with self.assertRaisesRegex(InputError, "valid ISO date"):
            add_fact(build_initial_pack(ticker="T", market="US", report="r.md"), fact)

        pack = self._ready_for_valuation()
        invalid = basis_payload(next(iter(pack["sources"])))
        invalid["price"]["value"] = 0
        with self.assertRaisesRegex(InputError, "Decimal encoded as a string"):
            lock_valuation(pack, invalid)
        invalid = basis_payload(next(iter(pack["sources"])), "-1")
        with self.assertRaisesRegex(InputError, "must be positive"):
            lock_valuation(pack, invalid)

    def test_atomic_write_failure_preserves_original_and_removes_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = directory / "pack.json"
            original = build_initial_pack(ticker="ONE", market="US", report="report.md")
            write_pack_atomic(path, original)
            before = path.read_bytes()
            changed = build_initial_pack(ticker="TWO", market="US", report="report.md")
            with mock.patch("research_pack.os.replace", side_effect=OSError("injected failure")):
                with self.assertRaisesRegex(InputError, "atomic pack write failed"):
                    write_pack_atomic(path, changed)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(directory.glob(".pack.json.*.tmp")), [])

    def test_checkpoint_order_hash_idempotency_and_source_invalidation(self) -> None:
        pack = build_initial_pack(ticker="TEST", market="US", report="report.md")
        initialized = pack["checkpoints"]["initialized"]["upstream_hash"]
        self.assertEqual(initialized, checkpoint_hash(pack, "initialized"))
        self.assertEqual(set_checkpoint(pack, "initialized"), "UNCHANGED")
        with self.assertRaisesRegex(StateConflict, "requires predecessor"):
            set_checkpoint(pack, "facts_ready")

        add_source(pack, source_payload())
        identifier = next(iter(pack["sources"]))
        self.assertEqual(set_checkpoint(pack, "sources_ready"), "UPDATED")
        sources_hash = pack["checkpoints"]["sources_ready"]["upstream_hash"]
        self.assertEqual(set_checkpoint(pack, "sources_ready"), "UNCHANGED")
        self.assertEqual(pack["checkpoints"]["sources_ready"]["upstream_hash"], sources_hash)
        add_fact(pack, fact_payload("revenue", identifier))
        self.assertEqual(set_checkpoint(pack, "facts_ready"), "UPDATED")
        self.assertEqual(lock_valuation(pack, basis_payload(identifier)), "UPDATED")
        self.assertEqual(set_checkpoint(pack, "matrix_ready"), "UPDATED")
        self.assertEqual(
            set(pack["checkpoints"]),
            {"initialized", "sources_ready", "facts_ready", "valuation_locked", "matrix_ready"},
        )

        add_source(pack, source_payload("https://example.com/quarterly"))
        self.assertEqual(set(pack["checkpoints"]), {"initialized"})

    def test_downstream_checkpoint_rejects_exact_stale_upstream_hash(self) -> None:
        pack = self._ready_for_valuation()
        identifier = next(iter(pack["sources"]))
        pack["sources"][identifier]["title"] = "Changed without invalidation"
        with self.assertRaisesRegex(
            StateConflict,
            "checkpoint valuation_locked requires CURRENT predecessor sources_ready",
        ):
            lock_valuation(pack, basis_payload(identifier))
        self.assertNotIn("valuation_locked", pack["checkpoints"])

    def test_fact_change_invalidates_only_fact_and_downstream_checkpoints(self) -> None:
        pack = self._ready_for_valuation()
        identifier = next(iter(pack["sources"]))
        lock_valuation(pack, basis_payload(identifier))
        set_checkpoint(pack, "matrix_ready")
        add_fact(pack, fact_payload("margin", identifier))
        self.assertEqual(set(pack["checkpoints"]), {"initialized", "sources_ready"})

    def test_valuation_lock_and_reasoned_revision(self) -> None:
        pack = self._ready_for_valuation()
        identifier = next(iter(pack["sources"]))
        first = basis_payload(identifier)
        self.assertEqual(lock_valuation(pack, first), "UPDATED")
        self.assertEqual(lock_valuation(pack, first), "UNCHANGED")
        with self.assertRaisesRegex(StateConflict, "use revise-valuation"):
            lock_valuation(pack, basis_payload(identifier, "101"))
        set_checkpoint(pack, "matrix_ready")
        second = basis_payload(identifier, "101.00")
        self.assertEqual(revise_valuation(pack, second, "Market close corrected"), "UPDATED")
        self.assertNotIn("valuation_locked", pack["checkpoints"])
        self.assertNotIn("matrix_ready", pack["checkpoints"])
        self.assertEqual(
            pack["valuation_basis"]["revisions"],
            [
                {
                    "old": {**first, "price": {**first["price"], "value": "100"}, "shares": {**first["shares"], "value": "10"}},
                    "new": {**second, "price": {**second["price"], "value": "101"}, "shares": {**second["shares"], "value": "10"}},
                    "reason": "Market close corrected",
                }
            ],
        )
        self.assertEqual(lock_valuation(pack, second), "UPDATED")

    def test_revision_requires_current_upstream_but_can_replace_stale_lock(self) -> None:
        pack = self._ready_for_valuation()
        identifier = next(iter(pack["sources"]))
        lock_valuation(pack, basis_payload(identifier))
        revised = basis_payload(identifier, "101")

        pack["sources"][identifier]["title"] = "Updated source title"
        with self.assertRaisesRegex(
            StateConflict,
            "checkpoint valuation_locked requires CURRENT predecessor sources_ready",
        ):
            revise_valuation(pack, revised, "Use corrected close")
        self.assertEqual(pack["valuation_basis"]["revisions"], [])

        for stage in ("sources_ready", "facts_ready"):
            pack["checkpoints"][stage] = {"upstream_hash": checkpoint_hash(pack, stage)}
        self.assertNotEqual(
            pack["checkpoints"]["valuation_locked"]["upstream_hash"],
            checkpoint_hash(pack, "valuation_locked"),
        )
        self.assertEqual(revise_valuation(pack, revised, "Use corrected close"), "UPDATED")
        self.assertNotIn("valuation_locked", pack["checkpoints"])

    def test_status_is_deterministic_and_reports_next_stage(self) -> None:
        pack = build_initial_pack(ticker="TEST", market="US", report="report.md")
        first = status_payload(pack)
        second = status_payload(pack)
        self.assertEqual(first, second)
        self.assertTrue(first["valid"])
        self.assertEqual(first["next_checkpoint"], "sources_ready")
        self.assertEqual([row["name"] for row in first["checkpoints"]], list(CHECKPOINT_ORDER))

    def test_deferred_objects_telemetry_unknown_keys_and_valuation_sources_fail(self) -> None:
        pack = build_initial_pack(ticker="TEST", market="US", report="report.md")
        pack["derived_records"] = {"unexpected": {}}
        pack["evidence_gates"] = []
        forbidden = (
            "provider",
            "MODEL",
            "Token",
            "tokens",
            "finish_reason",
            "Timing",
            "retry",
            "RUNTIME",
            "latency",
            "Duration",
            "started_at",
            "ENDED_AT",
        )
        pack["action_matrix"] = [
            {
                "nested": {key: "forbidden" for key in forbidden},
                "as_of": "2026-06-30",
                "market_date": "2026-07-29",
            }
        ]
        pack["identity"]["unknown"] = "value"
        issues = schema_issues(pack)
        self.assertTrue(any("derived_records['unexpected']" in issue for issue in issues))
        self.assertTrue(any("evidence_gates must be an empty object" in issue for issue in issues))
        telemetry_issues = [issue for issue in issues if "forbidden telemetry key" in issue]
        self.assertEqual(len(telemetry_issues), len(forbidden))
        self.assertFalse(any("as_of" in issue or "market_date" in issue for issue in telemetry_issues))
        self.assertTrue(any("identity has unknown keys" in issue for issue in issues))

        ready = self._ready_for_valuation()
        identifier = next(iter(ready["sources"]))
        lock_valuation(ready, basis_payload(identifier))
        ready["sources"].pop(identifier)
        valuation_issues = schema_issues(ready)
        self.assertTrue(
            any("valuation_basis.current references undefined source ID" in issue for issue in valuation_issues)
        )

    def _ready_for_valuation(self) -> dict[str, object]:
        pack = build_initial_pack(ticker="TEST", market="US", report="report.md")
        add_source(pack, source_payload())
        identifier = next(iter(pack["sources"]))
        set_checkpoint(pack, "sources_ready")
        add_fact(pack, fact_payload("revenue", identifier))
        set_checkpoint(pack, "facts_ready")
        return pack


class ResearchPackCliTests(unittest.TestCase):
    def test_identical_init_bytes_and_idempotent_cli_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = directory / "report.md"
            report.write_text("# Report\n", encoding="utf-8")
            packs = [directory / "first.json", directory / "second.json"]
            for pack in packs:
                completed = run(
                    "scripts/research_pack.py",
                    "init",
                    "--pack",
                    str(pack),
                    "--ticker",
                    "test",
                    "--market",
                    "us",
                    "--report",
                    str(report),
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("CREATED", completed.stdout)
            self.assertEqual(packs[0].read_bytes(), packs[1].read_bytes())
            before = packs[0].read_bytes()
            repeated = run(
                "scripts/research_pack.py",
                "init",
                "--pack",
                str(packs[0]),
                "--ticker",
                "TEST",
                "--market",
                "US",
                "--report",
                str(report),
            )
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertIn("UNCHANGED", repeated.stdout)
            self.assertEqual(packs[0].read_bytes(), before)

    def test_cli_source_fact_validate_status_and_exit_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            pack = directory / "pack.json"
            report = directory / "report.md"
            report.write_text("# Report\n", encoding="utf-8")
            self._init(pack, report)

            malformed = directory / "malformed.json"
            malformed.write_text('{"url":', encoding="utf-8")
            invalid_input = run(
                "scripts/research_pack.py",
                "source-add",
                "--pack",
                str(pack),
                "--source",
                str(malformed),
            )
            self.assertEqual(invalid_input.returncode, 2)
            self.assertEqual(invalid_input.stdout, "")
            self.assertIn("ERROR:", invalid_input.stderr)

            source_path = directory / "source.json"
            source_path.write_text(json.dumps(source_payload()), encoding="utf-8")
            added = self._command(pack, "source-add", "--source", source_path)
            self.assertIn("UPDATED", added.stdout)
            unchanged = self._command(pack, "source-add", "--source", source_path)
            self.assertIn("UNCHANGED", unchanged.stdout)
            identifier = next(iter(json.loads(pack.read_text())["sources"]))

            conflict_payload = source_payload(title="Different")
            source_path.write_text(json.dumps(conflict_payload), encoding="utf-8")
            conflict = run(
                "scripts/research_pack.py",
                "source-add",
                "--pack",
                str(pack),
                "--source",
                str(source_path),
            )
            self.assertEqual(conflict.returncode, 1)
            self.assertEqual(conflict.stdout, "")
            self.assertIn("ERROR:", conflict.stderr)

            fact_path = directory / "fact.json"
            fact_path.write_text(
                json.dumps(fact_payload("bad-reference", source_id("https://example.com/undefined"))),
                encoding="utf-8",
            )
            self._command(pack, "fact-add", "--fact", fact_path)
            invalid_pack = run("scripts/research_pack.py", "validate", "--pack", str(pack))
            self.assertEqual(invalid_pack.returncode, 1)
            self.assertIn("undefined source ID", invalid_pack.stderr)

            payload = json.loads(pack.read_text())
            payload["facts"]["bad-reference"]["source_ids"] = [identifier]
            pack.write_text(json.dumps(payload), encoding="utf-8")
            valid = run("scripts/research_pack.py", "validate", "--pack", str(pack))
            self.assertEqual(valid.returncode, 0, valid.stderr)
            status = run("scripts/research_pack.py", "status", "--pack", str(pack))
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertEqual(json.loads(status.stdout)["next_checkpoint"], "sources_ready")

    def test_strict_json_malformed_types_and_invalid_status_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = directory / "report.md"
            report.write_text("# Report\n", encoding="utf-8")
            pack = directory / "pack.json"
            self._init(pack, report)
            source_path = directory / "source.json"

            source_path.write_text(
                '{"url":"https://example.com","title":NaN,"publisher":"X","tier":"Tier 1","published_date":null}',
                encoding="utf-8",
            )
            nonfinite = run(
                "scripts/research_pack.py",
                "source-add",
                "--pack",
                str(pack),
                "--source",
                str(source_path),
            )
            self.assertEqual(nonfinite.returncode, 2)
            self.assertIn("ERROR:", nonfinite.stderr)
            self.assertNotIn("Traceback", nonfinite.stderr)

            malformed_source = source_payload()
            malformed_source["tier"] = []
            source_path.write_text(json.dumps(malformed_source), encoding="utf-8")
            wrong_type = run(
                "scripts/research_pack.py",
                "source-add",
                "--pack",
                str(pack),
                "--source",
                str(source_path),
            )
            self.assertEqual(wrong_type.returncode, 2)
            self.assertIn("ERROR:", wrong_type.stderr)
            self.assertNotIn("Traceback", wrong_type.stderr)

            payload = json.loads(pack.read_text())
            payload["sources"] = []
            pack.write_text(json.dumps(payload), encoding="utf-8")
            invalid = run("scripts/research_pack.py", "validate", "--pack", str(pack))
            self.assertEqual(invalid.returncode, 2)
            self.assertIn("ERROR:", invalid.stderr)
            self.assertNotIn("Traceback", invalid.stderr)
            status = run("scripts/research_pack.py", "status", "--pack", str(pack))
            self.assertEqual(status.returncode, 2)
            self.assertFalse(json.loads(status.stdout)["valid"])
            self.assertNotIn("Traceback", status.stderr)

    def test_cli_checkpoint_and_valuation_revision_flow(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = directory / "report.md"
            report.write_text("# Report\n", encoding="utf-8")
            pack = directory / "pack.json"
            self._init(pack, report)
            source_path = directory / "source.json"
            source_path.write_text(json.dumps(source_payload()), encoding="utf-8")
            self._command(pack, "source-add", "--source", source_path)
            identifier = next(iter(json.loads(pack.read_text())["sources"]))
            self._command(pack, "checkpoint", "--name", "sources_ready")
            fact_path = directory / "fact.json"
            fact_path.write_text(json.dumps(fact_payload("revenue", identifier)), encoding="utf-8")
            self._command(pack, "fact-add", "--fact", fact_path)
            self._command(pack, "checkpoint", "--name", "facts_ready")
            basis_path = directory / "basis.json"
            basis_path.write_text(json.dumps(basis_payload(identifier)), encoding="utf-8")
            self._command(pack, "valuation-lock", "--basis", basis_path)
            self._command(pack, "checkpoint", "--name", "matrix_ready")

            basis_path.write_text(json.dumps(basis_payload(identifier, "101")), encoding="utf-8")
            empty_reason = run(
                "scripts/research_pack.py",
                "revise-valuation",
                "--pack",
                str(pack),
                "--basis",
                str(basis_path),
                "--reason",
                "",
            )
            self.assertEqual(empty_reason.returncode, 2)
            revised = self._command(
                pack,
                "revise-valuation",
                "--basis",
                basis_path,
                "--reason",
                "Corrected close",
            )
            self.assertIn("UPDATED", revised.stdout)
            payload = json.loads(pack.read_text())
            self.assertEqual(payload["valuation_basis"]["revisions"][0]["reason"], "Corrected close")
            self.assertNotIn("valuation_locked", payload["checkpoints"])

    def test_new_report_legacy_output_and_optional_pack_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            legacy = directory / "legacy.md"
            completed = self._new_report(legacy)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, f"{legacy}\n")
            self.assertEqual(list(directory.glob("*.json")), [])

            automatic = directory / "automatic.md"
            generated = self._new_report(automatic, "--research-pack")
            automatic_pack = directory / "automatic.research-pack.json"
            self.assertEqual(generated.returncode, 0, generated.stderr)
            self.assertTrue(automatic_pack.exists())
            self.assertIn(f"RESEARCH PACK CREATED: {automatic_pack}", generated.stdout)

            explicit = directory / "explicit.md"
            explicit_pack = directory / "state" / "pack.json"
            previous = directory / "previous.md"
            previous.write_text("# Previous\n", encoding="utf-8")
            generated = self._new_report(
                explicit,
                "--research-pack",
                str(explicit_pack),
                "--previous-report",
                str(previous),
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            payload = json.loads(explicit_pack.read_text())
            self.assertEqual(payload["previous_report"], {"path": str(previous.resolve())})
            self.assertEqual(payload["report"], {"path": str(explicit.resolve())})

    def test_new_report_force_pack_conflict_rolls_back_existing_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = directory / "report.md"
            report.write_bytes(b"original-report\n")
            pack = directory / "pack.json"
            conflict = run(
                "scripts/research_pack.py",
                "init",
                "--pack",
                str(pack),
                "--ticker",
                "OTHER",
                "--market",
                "US",
                "--report",
                str(report),
            )
            self.assertEqual(conflict.returncode, 0, conflict.stderr)
            report_before = report.read_bytes()
            pack_before = pack.read_bytes()
            failed = self._new_report(
                report,
                "--force",
                "--research-pack",
                str(pack),
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("pack already exists with different content", failed.stderr)
            self.assertEqual(report.read_bytes(), report_before)
            self.assertEqual(pack.read_bytes(), pack_before)
            self.assertEqual(list(directory.glob(".*.tmp")), [])

    def test_new_report_refuses_report_pack_symlinks_and_path_collision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            target_report = directory / "target-report.md"
            target_report.write_bytes(b"target-report\n")
            linked_report = directory / "linked-report.md"
            linked_report.symlink_to(target_report)
            failed_report = self._new_report(linked_report, "--force")
            self.assertNotEqual(failed_report.returncode, 0)
            self.assertIn("must not be a symlink", failed_report.stderr)
            self.assertEqual(target_report.read_bytes(), b"target-report\n")

            target_pack = directory / "target-pack.json"
            target_pack.write_bytes(b"target-pack\n")
            linked_pack = directory / "linked-pack.json"
            linked_pack.symlink_to(target_pack)
            output = directory / "new.md"
            failed_pack = self._new_report(output, "--research-pack", str(linked_pack))
            self.assertNotEqual(failed_pack.returncode, 0)
            self.assertIn("must not be a symlink", failed_pack.stderr)
            self.assertFalse(output.exists())
            self.assertEqual(target_pack.read_bytes(), b"target-pack\n")

            collision = directory / "collision.md"
            collision.write_bytes(b"collision\n")
            failed_collision = self._new_report(
                collision,
                "--force",
                "--research-pack",
                str(collision),
            )
            self.assertNotEqual(failed_collision.returncode, 0)
            self.assertIn("must be different files", failed_collision.stderr)
            self.assertEqual(collision.read_bytes(), b"collision\n")

    def test_two_file_transaction_rolls_back_report_when_pack_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = directory / "report.md"
            pack = directory / "pack.json"
            report.write_bytes(b"before\n")
            real_replace = __import__("os").replace
            calls = 0

            def fail_second_replace(source: Path, destination: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected pack failure")
                real_replace(source, destination)

            with mock.patch("new_report.os.replace", side_effect=fail_second_replace):
                with self.assertRaisesRegex(InputError, "output transaction failed"):
                    _write_transaction(report, b"after\n", pack, b"{}\n", True)
            self.assertEqual(report.read_bytes(), b"before\n")
            self.assertFalse(pack.exists())
            self.assertEqual(list(directory.glob(".*.tmp")), [])

    def test_pack_replace_failure_restores_original_pack_and_rolls_back_report(self) -> None:
        # When overwriting an existing pack, a failed pack replace must restore
        # the original pack bytes AND roll back the report so the two-file
        # transaction stays atomic instead of leaving a new report with no pack.
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = directory / "report.md"
            pack = directory / "pack.json"
            report.write_bytes(b"report-before\n")
            pack.write_bytes(b"pack-before\n")
            real_replace = __import__("os").replace
            calls = 0

            def fail_second_replace(source: Path, destination: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected pack failure")
                real_replace(source, destination)

            with mock.patch("new_report.os.replace", side_effect=fail_second_replace):
                with self.assertRaisesRegex(InputError, "output transaction failed"):
                    _write_transaction(report, b"report-after\n", pack, b"pack-after\n", True, lock_held=True)
            self.assertEqual(report.read_bytes(), b"report-before\n")
            self.assertEqual(pack.read_bytes(), b"pack-before\n")
            self.assertEqual(list(directory.glob(".*.tmp")), [])

    def test_pack_write_lock_times_out_when_held(self) -> None:
        # A second acquirer with a short timeout must raise a clear error
        # instead of blocking forever when the lock is already held.
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            pack = directory / "pack.json"
            held = threading.Event()
            release = threading.Event()
            acquirer_error: list[BaseException] = []

            def holder() -> None:
                with pack_write_lock(pack):
                    held.set()
                    release.wait(5)

            def acquirer() -> None:
                try:
                    with pack_write_lock(pack, timeout=0.3):
                        pass
                except BaseException as exc:  # pragma: no cover - surfaced below
                    acquirer_error.append(exc)

            thread = threading.Thread(target=holder)
            thread.start()
            self.assertTrue(held.wait(2))
            late = threading.Thread(target=acquirer)
            late.start()
            late.join(5)
            release.set()
            thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertFalse(late.is_alive())
            self.assertEqual(len(acquirer_error), 1)
            self.assertIsInstance(acquirer_error[0], StateConflict)
            self.assertIn("pack lock timeout", str(acquirer_error[0]))

    def test_pack_write_lock_rejects_symlinked_lock_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            target = directory / "target.lock"
            target.write_bytes(b"")
            pack = directory / "pack.json"
            # The cooperative lock file lives at .pack.json.lock; symlink it so
            # reject_symlink(lock_path) must catch it before opening.
            (directory / ".pack.json.lock").symlink_to(target)
            with self.assertRaisesRegex(InputError, "pack lock path must not be a symlink"):
                with pack_write_lock(pack):
                    pass  # pragma: no cover - should never acquire

    def test_load_json_rejects_symlinked_input(self) -> None:
        # _load_json (source/fact/record/basis inputs) must reject symlinks so a
        # crafted link cannot redirect a JSON read at another path.
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            pack = directory / "pack.json"
            report = directory / "report.md"
            report.write_text("# Report\n", encoding="utf-8")
            self._init(pack, report)
            target = directory / "real-source.json"
            target.write_text(json.dumps(source_payload()), encoding="utf-8")
            linked = directory / "linked-source.json"
            linked.symlink_to(target)
            failed = run(
                "scripts/research_pack.py",
                "source-add",
                "--pack",
                str(pack),
                "--source",
                str(linked),
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("must not be a symlink", failed.stderr)

    def _init(self, pack: Path, report: Path) -> None:
        completed = run(
            "scripts/research_pack.py",
            "init",
            "--pack",
            str(pack),
            "--ticker",
            "TEST",
            "--market",
            "US",
            "--report",
            str(report),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def _command(
        self,
        pack: Path,
        command: str,
        option: str,
        value: str | Path,
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        completed = run(
            "scripts/research_pack.py",
            command,
            "--pack",
            str(pack),
            option,
            str(value),
            *extra,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed

    def _new_report(self, output: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(
            "scripts/new_report.py",
            "--ticker",
            "TEST",
            "--company",
            "Test Company",
            "--market",
            "US",
            "--out",
            str(output),
            *extra,
        )


if __name__ == "__main__":
    unittest.main()

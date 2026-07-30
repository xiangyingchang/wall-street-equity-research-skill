#!/usr/bin/env python3
"""Focused Audit v5 provenance, snapshot, and v4 compatibility regressions."""

from __future__ import annotations

from contextlib import contextmanager
import json
import hashlib
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))

from financial_formulas import CONVERGENCE_TOLERANCE, evaluate_formula, modeled_multiple  # noqa: E402
from report_audit import (  # noqa: E402
    AuditV5Snapshot,
    AuditV5VerdictSnapshot,
    MINIMUM_RATIO,
    build_manifest,
    build_manifest_v5,
    canonical,
    evaluate,
    evaluate_v5,
    load_json,
    parse_numeric,
    parse_numeric_v5,
    results_template,
    write_outputs_atomic,
)
from research_pack import (  # noqa: E402
    InputError,
    StateConflict,
    add_derived_record,
    add_fact,
    add_source,
    build_initial_pack,
    canonical_derived_record,
    canonicalize_url,
    checkpoint_hash,
    load_pack,
    lock_valuation,
    pack_write_lock,
    schema_issues,
    set_checkpoint,
    source_id,
    write_pack_atomic,
)


FIXTURE = ROOT / "tests/fixtures/report-audit-v5.md"
V4_REPORT = ROOT / "tests/fixtures/good-full-report.md"
V4_MANIFEST = ROOT / "tests/fixtures/report-audit-v4-manifest.json"


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(ROOT / arguments[0]), *arguments[1:]],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class AuditV5Tests(unittest.TestCase):
    def _fact(
        self,
        pack: dict[str, object],
        source: str,
        fact_id: str,
        value: str,
        unit: str,
        as_of: str,
    ) -> None:
        add_fact(
            pack,
            {
                "fact_id": fact_id,
                "field": fact_id,
                "value_type": "decimal",
                "value": value,
                "unit": unit,
                "as_of": as_of,
                "source_ids": [source],
            },
        )

    def _ref(self, name: str, fact_id: str, **metadata: object) -> dict[str, object]:
        return {"name": name, "kind": "fact_ref", "fact_id": fact_id, **metadata}

    def _derived_ref(self, name: str, record_id: str, **metadata: object) -> dict[str, object]:
        return {
            "name": name,
            "kind": "derived_ref",
            "derived_record_id": record_id,
            **metadata,
        }

    def _record(
        self,
        identifier: str,
        formula_id: str,
        inputs: list[dict[str, object]],
        computed_value: str,
        computed_unit: str,
        reported_value: str,
        reported_unit: str,
        places: int,
        label: str,
    ) -> dict[str, object]:
        return {
            "id": identifier,
            "formula_id": formula_id,
            "inputs": inputs,
            "computed": {"value": computed_value, "unit": computed_unit},
            "reported": {"value": reported_value, "unit": reported_unit},
            "rounding": {"mode": "ROUND_HALF_UP", "places": places},
            "binding": {"section": "## Derived Audit", "label": label, "column": "Value"},
        }

    def _pack(self, report: Path) -> dict[str, object]:
        pack = build_initial_pack(ticker="MU", market="US", report=report)
        source_url = "https://www.sec.gov./Archives/edgar/data/723125/mu-20260528.htm"
        canonical_url = canonicalize_url(source_url)
        self.assertEqual(canonical_url, "https://www.sec.gov/Archives/edgar/data/723125/mu-20260528.htm")
        source = source_id(canonical_url)
        add_source(
            pack,
            {
                "url": source_url,
                "title": "Micron filing",
                "publisher": "SEC",
                "tier": "Tier 1",
                "published_date": "2026-06-25",
            },
        )

        self._fact(pack, source, "price", "820.53", "USD", "2026-07-30")
        self._fact(pack, source, "shares", "1000", "shares", "2026-07-30")
        quarter_dates = ("2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31")
        for index, (eps, fcf, as_of) in enumerate(
            zip(("8.14", "10.82", "10.95", "14.26"), ("25", "30", "32", "35.92"), quarter_dates),
            start=1,
        ):
            self._fact(pack, source, f"eps_q{index}", eps, "USD/share", as_of)
            self._fact(pack, source, f"fcf_q{index}", fcf, "USD_B", as_of)
        with localcontext() as context:
            context.prec = 50
            multiple = Decimal("820.53") / Decimal("122.92")
        self._fact(pack, source, "multiple_raw", str(multiple), "x", "2026-07-30")
        self._fact(pack, source, "one_ratio", "1", "ratio", "2026-07-30")
        self._fact(pack, source, "discount_rate", "0.0461", "ratio", "2026-07-30")
        self._fact(pack, source, "meta_fy", "52", "USD_B", "2025-12-31")
        self._fact(pack, source, "meta_current_ytd", "25", "USD_B", "2026-09-30")
        self._fact(pack, source, "meta_prior_ytd", "20", "USD_B", "2025-09-30")

        set_checkpoint(pack, "sources_ready")
        set_checkpoint(pack, "facts_ready")
        lock_valuation(
            pack,
            {
                "price": {
                    "value": "820.53",
                    "currency": "USD",
                    "kind": "regular_close",
                    "market_date": "2026-07-30",
                    "source_id": source,
                },
                "shares": {"value": "1000", "as_of": "2026-07-30", "source_id": source},
            },
        )

        periods = ("FY2025-Q3", "FY2025-Q4", "FY2026-Q1", "FY2026-Q2")
        eps_inputs = [self._ref(f"q{index}", f"eps_q{index}", period=period) for index, period in enumerate(periods, 1)]
        fcf_inputs = [self._ref(f"q{index}", f"fcf_q{index}", period=period) for index, period in enumerate(periods, 1)]
        multiple_record = self._record(
            "mu_multiple",
            "product_v1",
            [self._ref("factor", "one_ratio"), self._ref("multiple", "multiple_raw")],
            str(multiple),
            "x",
            str(multiple.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_UP)),
            "x",
            12,
            "MU Forward multiple",
        )
        payback_result = evaluate_formula(
            "payback_forward_v1",
            [
                {"name": "multiple", "value": str(multiple)},
                {"name": "discount_rate", "value": "0.0461"},
                {"name": "years", "value": "10"},
            ],
        )
        records = (
            self._record("mu_ttm_eps", "ttm_sum_v1", eps_inputs, "44.17", "USD/share", "44.17", "USD/share", 2, "MU TTM EPS"),
            self._record("mu_ttm_fcf", "ttm_sum_v1", fcf_inputs, "122.92", "USD_B", "122.92", "USD_B", 2, "MU TTM FCF"),
            multiple_record,
            self._record(
                "mu_forward",
                "payback_forward_v1",
                [
                    self._derived_ref("multiple", "mu_multiple"),
                    self._ref("discount_rate", "discount_rate"),
                    {"name": "years", "kind": "literal", "value": "10", "unit": "year"},
                ],
                str(payback_result.value),
                "ratio",
                str((payback_result.value * 100).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
                "%",
                6,
                "MU Forward required g",
            ),
            self._record(
                "meta_ttm_fcf",
                "ttm_bridge_v1",
                [
                    self._ref("annual", "meta_fy", role="fy", fiscal_year=2025, duration_quarters=4),
                    self._ref("current", "meta_current_ytd", role="current_ytd", fiscal_year=2026, duration_quarters=3),
                    self._ref("prior", "meta_prior_ytd", role="prior_ytd", fiscal_year=2025, duration_quarters=3),
                ],
                "57",
                "USD_B",
                "57",
                "USD_B",
                0,
                "META TTM FCF",
            ),
        )
        for record in records:
            add_derived_record(pack, record)
        set_checkpoint(pack, "matrix_ready")
        set_checkpoint(pack, "draft_ready")
        return pack

    def _workspace(self, directory: Path) -> tuple[Path, Path, dict[str, object]]:
        report = directory / "report.md"
        report.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        pack = self._pack(report)
        pack_path = directory / "pack.json"
        write_pack_atomic(pack_path, pack)
        return report, pack_path, pack

    def _refresh_checkpoints(self, pack: dict[str, object], report: Path) -> None:
        report_bytes = report.read_bytes()
        pack["checkpoints"].pop("audit_passed", None)
        for stage in ("initialized", "sources_ready", "facts_ready", "valuation_locked", "matrix_ready", "draft_ready"):
            pack["checkpoints"][stage] = {
                "upstream_hash": checkpoint_hash(pack, stage, report_bytes=report_bytes)
            }

    def _extract(self, report: Path, pack: Path, manifest: Path) -> subprocess.CompletedProcess[str]:
        return run(
            "scripts/report_audit.py",
            "extract",
            "--report",
            str(report),
            "--pack",
            str(pack),
            "--manifest-out",
            str(manifest),
        )

    def test_exact_mu_meta_vectors_and_recursive_derived_reference(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report, pack_path, pack = self._workspace(Path(raw))
            manifest = build_manifest_v5(AuditV5Snapshot.load(report, pack_path))
            self.assertEqual([item["derived_record_id"] for item in manifest["items"]], sorted(pack["derived_records"]))
            self.assertEqual(pack["derived_records"]["mu_ttm_eps"]["computed"]["value"], "44.17")
            self.assertEqual(pack["derived_records"]["mu_ttm_fcf"]["computed"]["value"], "122.92")
            self.assertEqual(pack["derived_records"]["meta_ttm_fcf"]["computed"]["value"], "57")
            self.assertEqual(pack["derived_records"]["mu_forward"]["inputs"][0]["kind"], "derived_ref")
            root = Decimal(pack["derived_records"]["mu_forward"]["computed"]["value"])
            multiple = Decimal(pack["facts"]["multiple_raw"]["value"])
            self.assertLessEqual(
                abs(modeled_multiple("payback_forward_v1", root, "0.0461", 10) - multiple),
                CONVERGENCE_TOLERANCE,
            )

    def test_v5_cli_is_deterministic_and_only_success_marks_audit_passed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report, pack_path, _ = self._workspace(directory)
            manifest = directory / "manifest.json"
            first = self._extract(report, pack_path, manifest)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_bytes = manifest.read_bytes()
            second = self._extract(report, pack_path, manifest)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(manifest.read_bytes(), first_bytes)

            verdict = run(
                "scripts/report_audit.py", "verdict", "--report", str(report),
                "--pack", str(pack_path), "--manifest", str(manifest),
            )
            self.assertEqual(verdict.returncode, 0, verdict.stderr)
            completed = load_pack(pack_path)
            audit = completed["checkpoints"]["audit_passed"]
            manifest_payload = json.loads(manifest.read_text())
            self.assertEqual(audit["manifest_sha256"], manifest_payload["audit_binding_sha256"])
            self.assertEqual(audit["report_sha256"], manifest_payload["report_sha256"])
            self.assertEqual(hashlib.sha256(pack_path.read_bytes()).hexdigest(), manifest_payload["pack_sha256"])

            persisted_bytes = pack_path.read_bytes()
            rerun = run(
                "scripts/report_audit.py", "verdict", "--report", str(report),
                "--pack", str(pack_path), "--manifest", str(manifest),
            )
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertEqual(pack_path.read_bytes(), persisted_bytes)

            with self.assertRaisesRegex(InputError, "only be written"):
                set_checkpoint(completed, "audit_passed")
            generic = run(
                "scripts/research_pack.py", "checkpoint", "--pack", str(pack_path),
                "--name", "audit_passed",
            )
            self.assertEqual(generic.returncode, 2)

    def test_verdict_version_mismatch_messages_are_specific(self) -> None:
        # R4: a version mismatch must name the version, not mislabel the problem
        # as a flag incompatibility. Case 2: --pack with a non-v5 manifest.
        # Case 5: --results with an unknown-version manifest.
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report, pack_path, _ = self._workspace(directory)
            manifest = directory / "manifest.json"
            self.assertEqual(self._extract(report, pack_path, manifest).returncode, 0)

            v4_manifest = directory / "v4.json"
            tampered = json.loads(manifest.read_text())
            tampered["version"] = 4
            v4_manifest.write_text(json.dumps(tampered), encoding="utf-8")
            case2 = run(
                "scripts/report_audit.py", "verdict", "--report", str(report),
                "--pack", str(pack_path), "--manifest", str(v4_manifest),
            )
            self.assertEqual(case2.returncode, 2)
            self.assertIn("manifest version 4 is incompatible with --pack", case2.stderr)
            self.assertIn("use --results for v4", case2.stderr)

            unknown_manifest = directory / "unknown.json"
            unknown_manifest.write_text(json.dumps({"version": 99}), encoding="utf-8")
            results = directory / "results.json"
            results.write_text(json.dumps({"results": []}), encoding="utf-8")
            case5 = run(
                "scripts/report_audit.py", "verdict", "--report", str(report),
                "--manifest", str(unknown_manifest), "--results", str(results),
            )
            self.assertEqual(case5.returncode, 2)
            self.assertIn("manifest version 99 is incompatible with --results", case5.stderr)
            self.assertIn("use --pack for v5", case5.stderr)

    def test_ttm_period_and_bridge_metadata_are_strict(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report, _, base = self._workspace(Path(raw))

            def shift_ttm_labels(pack: dict[str, object]) -> None:
                for item in pack["derived_records"]["mu_ttm_eps"]["inputs"]:
                    year = int(item["period"][2:6]) + 1
                    item["period"] = f"FY{year}{item['period'][6:]}"

            def shift_bridge_labels(pack: dict[str, object]) -> None:
                for item in pack["derived_records"]["meta_ttm_fcf"]["inputs"]:
                    item["fiscal_year"] += 1

            cases = {
                "syntax": lambda pack: pack["derived_records"]["mu_ttm_eps"]["inputs"][0].update(period="2025-Q3"),
                "nonconsecutive": lambda pack: pack["derived_records"]["mu_ttm_eps"]["inputs"][3].update(period="FY2026-Q3"),
                "quarter-date": lambda pack: pack["facts"]["eps_q2"].update(as_of="2025-05-31"),
                "fy-duration": lambda pack: pack["derived_records"]["meta_ttm_fcf"]["inputs"][0].update(duration_quarters=3),
                "ytd-duration": lambda pack: pack["derived_records"]["meta_ttm_fcf"]["inputs"][1].update(duration_quarters=2),
                "fiscal-adjacency": lambda pack: pack["derived_records"]["meta_ttm_fcf"]["inputs"][1].update(fiscal_year=2027),
                "bridge-date": lambda pack: pack["facts"]["meta_current_ytd"].update(as_of="2025-08-31"),
                "detached-quarter-years": lambda pack: [
                    pack["facts"][f"eps_q{index}"].update(as_of=f"{year}-06-30")
                    for index, year in enumerate((2010, 2015, 2020, 2025), 1)
                ],
                "detached-bridge-years": lambda pack: [
                    pack["facts"][fact_id].update(as_of=as_of)
                    for fact_id, as_of in (
                        ("meta_prior_ytd", "2010-09-30"),
                        ("meta_fy", "2015-12-31"),
                        ("meta_current_ytd", "2020-09-30"),
                    )
                ],
                "whole-ttm-plus-one-year": shift_ttm_labels,
                "whole-bridge-plus-one-year": shift_bridge_labels,
            }
            for name, mutate in cases.items():
                with self.subTest(name=name):
                    pack = json.loads(json.dumps(base))
                    mutate(pack)
                    issues = schema_issues(pack, verify_checkpoint_hashes=False, report_bytes=report.read_bytes())
                    self.assertTrue(any("ttm_" in issue or "period" in issue for issue in issues), issues)

    def test_fact_and_derived_refs_block_laundering_undefined_and_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report, _, base = self._workspace(Path(raw))
            laundering = json.loads(json.dumps(base["derived_records"]["mu_ttm_eps"]))
            laundering["inputs"][0]["value"] = "999"
            with self.assertRaisesRegex(InputError, "unknown keys: value"):
                canonical_derived_record(laundering, base)

            undefined_fact = json.loads(json.dumps(base["derived_records"]["mu_ttm_eps"]))
            undefined_fact["id"] = "undefined_fact"
            undefined_fact["inputs"][0]["fact_id"] = "missing"
            with self.assertRaisesRegex(StateConflict, "undefined fact_id"):
                canonical_derived_record(undefined_fact, base)

            undefined_derived = json.loads(json.dumps(base["derived_records"]["mu_forward"]))
            undefined_derived["id"] = "undefined_derived"
            undefined_derived["inputs"][0]["derived_record_id"] = "missing"
            with self.assertRaisesRegex(StateConflict, "undefined derived_record_id"):
                canonical_derived_record(undefined_derived, base)

            cycle = json.loads(json.dumps(base))
            first = cycle["derived_records"]["mu_ttm_eps"]
            second = cycle["derived_records"]["mu_ttm_fcf"]
            first["inputs"][0] = self._derived_ref("q1", "mu_ttm_fcf", period="FY2025-Q3")
            second["inputs"][0] = self._derived_ref("q1", "mu_ttm_eps", period="FY2025-Q3")
            issues = schema_issues(cycle, verify_checkpoint_hashes=False, report_bytes=report.read_bytes())
            self.assertTrue(any("cycle detected" in issue for issue in issues), issues)

            literal_financial = json.loads(json.dumps(base["derived_records"]["mu_ttm_eps"]))
            literal_financial["id"] = "literal_financial"
            literal_financial["inputs"][0] = {
                "name": "q1", "kind": "literal", "value": "8.14", "unit": "USD/share",
                "period": "FY2025-Q3",
            }
            with self.assertRaisesRegex(InputError, "literal input is not allowed"):
                canonical_derived_record(literal_financial, base)

    def test_unit_algebra_and_scaling_reject_fake_combinations(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            _, _, pack = self._workspace(Path(raw))
            source = next(iter(pack["sources"]))
            self._fact(pack, source, "usd_b", "2", "USD_B", "2026-07-30")
            self._fact(pack, source, "usd", "2", "USD", "2026-07-30")
            self._fact(pack, source, "shares_b", "4", "shares_B", "2026-07-30")
            self._fact(pack, source, "shares_plain", "4", "shares", "2026-07-30")
            self._fact(pack, source, "per_share", "3", "USD/share", "2026-07-30")

            ratio = self._record(
                "ratio_scale", "ratio_v1",
                [self._ref("numerator", "usd_b"), self._ref("denominator", "usd")],
                "1000000000", "ratio", "1000000000", "ratio", 0, "unused",
            )
            self.assertEqual(canonical_derived_record(ratio, pack)["computed"]["value"], "1000000000")
            per_share = self._record(
                "per_share_calc", "ratio_v1",
                [self._ref("numerator", "usd_b"), self._ref("denominator", "shares_b")],
                "0.5", "USD/share", "0.5", "USD/share", 1, "unused",
            )
            canonical_derived_record(per_share, pack)
            product = self._record(
                "product_scale", "product_v1",
                [self._ref("a", "per_share"), self._ref("b", "shares_b")],
                "12", "USD_B", "12", "USD_B", 0, "unused",
            )
            canonical_derived_record(product, pack)

            invalid = self._record(
                "fake_ratio", "ratio_v1",
                [self._ref("numerator", "usd"), self._ref("denominator", "shares_plain")],
                "0.5", "ratio", "0.5", "ratio", 1, "unused",
            )
            with self.assertRaisesRegex(InputError, "computed.unit must be 'USD/share'"):
                canonical_derived_record(invalid, pack)
            fake_scale = self._record(
                "fake_scale", "ratio_v1",
                [self._ref("numerator", "usd_b"), self._ref("denominator", "shares_plain")],
                "0.5", "USD/share", "0.5", "USD/share", 1, "unused",
            )
            with self.assertRaisesRegex(InputError, "does not support"):
                canonical_derived_record(fake_scale, pack)
            invalid_product = self._record(
                "invalid_product", "product_v1",
                [self._ref("a", "usd"), self._ref("b", "shares_plain")],
                "8", "USD", "8", "USD", 0, "unused",
            )
            with self.assertRaisesRegex(InputError, "does not support"):
                canonical_derived_record(invalid_product, pack)

    def test_immutable_snapshot_symlinks_collisions_and_bound_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report, pack, _ = self._workspace(directory)
            manifest = directory / "manifest.json"
            report_before, pack_before = report.read_bytes(), pack.read_bytes()
            for collision in (report, pack):
                completed = self._extract(report, pack, collision)
                self.assertEqual(completed.returncode, 2)
                self.assertIn("distinct", completed.stderr)
            self.assertEqual(report.read_bytes(), report_before)
            self.assertEqual(pack.read_bytes(), pack_before)

            for target, label in ((report, "report"), (pack, "pack")):
                link = directory / f"{label}-link"
                link.symlink_to(target)
                args_report = link if label == "report" else report
                args_pack = link if label == "pack" else pack
                completed = self._extract(args_report, args_pack, manifest)
                self.assertEqual(completed.returncode, 2)
                self.assertIn("symlink", completed.stderr)

            manifest_target = directory / "manifest-target.json"
            manifest_target.write_text("sentinel", encoding="utf-8")
            manifest_link = directory / "manifest-link.json"
            manifest_link.symlink_to(manifest_target)
            completed = self._extract(report, pack, manifest_link)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(manifest_target.read_text(), "sentinel")

            wrong = load_pack(pack)
            wrong["report"]["path"] = str(directory / "other.md")
            write_pack_atomic(pack, wrong)
            completed = self._extract(report, pack, manifest)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("bound by the pack", completed.stderr)

    def test_public_snapshot_construction_rejects_forged_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report, pack, parsed_pack = self._workspace(directory)
            good = AuditV5Snapshot.load(report, pack)
            with self.assertRaisesRegex(ValueError, "report text does not match"):
                AuditV5Snapshot(
                    good.report_path,
                    good.pack_path,
                    good.report_bytes,
                    good.report + "forged",
                    good.pack_bytes,
                    good.pack,
                )
            forged_pack = json.loads(json.dumps(parsed_pack))
            forged_pack["identity"]["ticker"] = "FORGED"
            with self.assertRaisesRegex(ValueError, "parsed pack does not match"):
                AuditV5Snapshot(
                    good.report_path,
                    good.pack_path,
                    good.report_bytes,
                    good.report,
                    good.pack_bytes,
                    forged_pack,
                )
            forged_pack_types = json.loads(json.dumps(parsed_pack))
            forged_pack_types["action_matrix"] = tuple(forged_pack_types["action_matrix"])
            with self.assertRaisesRegex(ValueError, "parsed pack does not match"):
                AuditV5Snapshot(
                    good.report_path,
                    good.pack_path,
                    good.report_bytes,
                    good.report,
                    good.pack_bytes,
                    forged_pack_types,
                )

            manifest_path = directory / "manifest.json"
            self.assertEqual(self._extract(report, pack, manifest_path).returncode, 0)
            verdict_snapshot = AuditV5VerdictSnapshot.load(report, pack, manifest_path)
            forged_manifest = json.loads(json.dumps(verdict_snapshot.manifest))
            forged_manifest["version"] = 4
            with self.assertRaisesRegex(ValueError, "parsed manifest does not match"):
                AuditV5VerdictSnapshot(
                    verdict_snapshot.audit,
                    verdict_snapshot.manifest_path,
                    verdict_snapshot.manifest_bytes,
                    forged_manifest,
                )
            forged_manifest_types = json.loads(json.dumps(verdict_snapshot.manifest))
            forged_manifest_types["items"] = tuple(forged_manifest_types["items"])
            with self.assertRaisesRegex(ValueError, "parsed manifest does not match"):
                AuditV5VerdictSnapshot(
                    verdict_snapshot.audit,
                    verdict_snapshot.manifest_path,
                    verdict_snapshot.manifest_bytes,
                    forged_manifest_types,
                )

    def test_verdict_lock_preserves_a_concurrent_supported_writer(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report, pack, _ = self._workspace(directory)
            manifest = directory / "manifest.json"
            self.assertEqual(self._extract(report, pack, manifest).returncode, 0)
            snapshot = AuditV5VerdictSnapshot.load(report, pack, manifest)
            writer_locked = threading.Event()
            audit_waiting = threading.Event()
            release_writer = threading.Event()
            source_url = "https://www.sec.gov/Archives/edgar/data/723125/concurrent.htm"
            concurrent_source_id = source_id(source_url)
            writer_error: list[BaseException] = []
            audit_outcome: list[dict[str, object]] = []

            def supported_writer() -> None:
                try:
                    with pack_write_lock(pack):
                        writer_locked.set()
                        if not release_writer.wait(2):
                            raise AssertionError("audit writer did not attempt the shared lock")
                        changed = load_pack(pack)
                        add_source(
                            changed,
                            {
                                "url": source_url,
                                "title": "Concurrent filing",
                                "publisher": "SEC",
                                "tier": "Tier 1",
                                "published_date": "2026-07-30",
                            },
                        )
                        write_pack_atomic(pack, changed, lock_held=True)
                except BaseException as exc:  # pragma: no cover - surfaced below
                    writer_error.append(exc)

            @contextmanager
            def observed_audit_lock(path: Path):
                audit_waiting.set()
                with pack_write_lock(path):
                    yield

            writer = threading.Thread(target=supported_writer)
            writer.start()
            self.assertTrue(writer_locked.wait(2))
            with mock.patch("report_audit.pack_write_lock", observed_audit_lock):
                audit = threading.Thread(target=lambda: audit_outcome.append(evaluate_v5(snapshot)))
                audit.start()
                self.assertTrue(audit_waiting.wait(2))
                self.assertTrue(audit.is_alive())
                release_writer.set()
                writer.join(2)
                audit.join(2)

            self.assertFalse(writer.is_alive())
            self.assertFalse(audit.is_alive())
            self.assertEqual(writer_error, [])
            self.assertEqual(len(audit_outcome), 1)
            outcome = audit_outcome[0]
            self.assertEqual(outcome["verdict"], "BLOCK")
            self.assertIn("changed concurrently", outcome["reason"])
            completed = load_pack(pack)
            self.assertIn(concurrent_source_id, completed["sources"])
            self.assertNotIn("audit_passed", completed["checkpoints"])

    def test_idna_dot_variants_and_ascii_trailing_dots_dedupe(self) -> None:
        expected = "https://www.sec.gov/Archives/example"
        variants = (
            "https://www.sec.gov/Archives/example",
            "https://www.sec.gov./Archives/example",
            "https://www。sec。gov。/Archives/example",
            "https://www．sec．gov．/Archives/example",
            "https://www｡sec｡gov｡/Archives/example",
        )
        canonical = [canonicalize_url(value) for value in variants]
        self.assertEqual(canonical, [expected] * len(variants))
        self.assertEqual(len({source_id(value) for value in canonical}), 1)

    def test_v4_cli_collisions_symlink_outputs_and_failed_validation_preserve_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = directory / "report.md"
            report.write_bytes(V4_REPORT.read_bytes())
            manifest = directory / "manifest.json"
            results = directory / "results.json"
            manifest.write_bytes(b"manifest-before\n")
            results.write_bytes(b"results-before\n")

            collision_cases = (
                (report, results),
                (manifest, report),
                (manifest, manifest),
            )
            for manifest_out, results_out in collision_cases:
                completed = run(
                    "scripts/report_audit.py", "extract", "--report", str(report),
                    "--manifest-out", str(manifest_out), "--results-out", str(results_out),
                )
                self.assertEqual(completed.returncode, 2)
                self.assertIn("distinct", completed.stderr)
            self.assertEqual(report.read_bytes(), V4_REPORT.read_bytes())
            self.assertEqual(manifest.read_bytes(), b"manifest-before\n")
            self.assertEqual(results.read_bytes(), b"results-before\n")

            for output, target in ((directory / "manifest-link", manifest), (directory / "results-link", results)):
                output.symlink_to(target)
            completed = run(
                "scripts/report_audit.py", "extract", "--report", str(report),
                "--manifest-out", str(directory / "manifest-link"),
                "--results-out", str(directory / "results-link"),
            )
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(manifest.read_bytes(), b"manifest-before\n")
            self.assertEqual(results.read_bytes(), b"results-before\n")

            completed = run(
                "scripts/report_audit.py", "extract", "--report", str(report),
                "--manifest-out", str(manifest), "--results-out", str(results),
                "--ratio", "0.14",
            )
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(manifest.read_bytes(), b"manifest-before\n")
            self.assertEqual(results.read_bytes(), b"results-before\n")

            valid = run(
                "scripts/report_audit.py", "extract", "--report", str(report),
                "--manifest-out", str(manifest), "--results-out", str(results),
            )
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertEqual(manifest.read_bytes(), V4_MANIFEST.read_bytes())
            verdict_collision = run(
                "scripts/report_audit.py", "verdict", "--report", str(report),
                "--manifest", str(report), "--results", str(results),
            )
            self.assertEqual(verdict_collision.returncode, 2)
            self.assertIn("distinct", verdict_collision.stderr)

    def test_v4_two_output_transaction_rolls_back_replace_failure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            first = directory / "manifest.json"
            second = directory / "results.json"
            first.write_bytes(b"manifest-before\n")
            second.write_bytes(b"results-before\n")
            real_replace = __import__("os").replace
            calls = 0

            def fail_second_replace(source: Path, destination: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected second replace failure")
                real_replace(source, destination)

            with mock.patch("report_audit.os.replace", side_effect=fail_second_replace):
                with self.assertRaisesRegex(OSError, "injected second replace failure"):
                    write_outputs_atomic(
                        [(first, b"manifest-after\n"), (second, b"results-after\n")]
                    )
            self.assertEqual(first.read_bytes(), b"manifest-before\n")
            self.assertEqual(second.read_bytes(), b"results-before\n")
            self.assertEqual(list(directory.glob(".*.tmp")), [])

    def test_duplicate_json_keys_and_failed_verdict_never_mark_audit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report, pack, _ = self._workspace(directory)
            manifest = directory / "manifest.json"
            self.assertEqual(self._extract(report, pack, manifest).returncode, 0)

            duplicate_manifest = directory / "duplicate-manifest.json"
            duplicate_manifest.write_text('{"version":5,"version":5}', encoding="utf-8")
            failed = run(
                "scripts/report_audit.py", "verdict", "--report", str(report),
                "--pack", str(pack), "--manifest", str(duplicate_manifest),
            )
            self.assertEqual(failed.returncode, 2)
            self.assertIn("duplicate JSON object key", failed.stderr)
            self.assertNotIn("audit_passed", load_pack(pack)["checkpoints"])

            duplicate_pack = directory / "duplicate-pack.json"
            duplicate_pack.write_text('{"schema_version":"research-pack-v1","schema_version":"x"}', encoding="utf-8")
            failed = self._extract(report, duplicate_pack, directory / "unused.json")
            self.assertEqual(failed.returncode, 2)
            self.assertIn("duplicate JSON object key", failed.stderr)

            report.write_text(report.read_text().replace("$44.17/share", "$44.18/share"), encoding="utf-8")
            blocked = run(
                "scripts/report_audit.py", "verdict", "--report", str(report),
                "--pack", str(pack), "--manifest", str(manifest),
            )
            self.assertEqual(blocked.returncode, 1, blocked.stderr)
            self.assertNotIn("audit_passed", load_pack(pack)["checkpoints"])

    def test_v5_verdict_rejects_all_symlinks_without_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report, pack, _ = self._workspace(directory)
            manifest = directory / "manifest.json"
            self.assertEqual(self._extract(report, pack, manifest).returncode, 0)
            expected_bytes = {
                report: report.read_bytes(),
                pack: pack.read_bytes(),
                manifest: manifest.read_bytes(),
            }

            for target, label in ((report, "report"), (pack, "pack"), (manifest, "manifest")):
                with self.subTest(label=label):
                    link = directory / f"verdict-{label}-link"
                    link.symlink_to(target)
                    arguments = {
                        "report": report,
                        "pack": pack,
                        "manifest": manifest,
                    }
                    arguments[label] = link
                    failed = run(
                        "scripts/report_audit.py", "verdict",
                        "--report", str(arguments["report"]),
                        "--pack", str(arguments["pack"]),
                        "--manifest", str(arguments["manifest"]),
                    )
                    self.assertEqual(failed.returncode, 2)
                    self.assertIn("symlink", failed.stderr)
                    for path, payload in expected_bytes.items():
                        self.assertEqual(path.read_bytes(), payload)
                    self.assertNotIn("audit_passed", load_pack(pack)["checkpoints"])

    def test_v5_tampering_and_cli_incompatible_args_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report, pack, _ = self._workspace(directory)
            manifest = directory / "manifest.json"
            self.assertEqual(self._extract(report, pack, manifest).returncode, 0)
            results = directory / "results.json"
            results.write_text("{}", encoding="utf-8")
            cases = (
                (("extract", "--report", str(report), "--pack", str(pack), "--manifest-out", str(manifest), "--results-out", str(results)), "incompatible"),
                (("verdict", "--report", str(report), "--manifest", str(manifest)), "requires --pack"),
                (("verdict", "--report", str(report), "--manifest", str(manifest), "--pack", str(pack), "--results", str(results)), "incompatible"),
            )
            for arguments, message in cases:
                completed = run("scripts/report_audit.py", *arguments)
                self.assertEqual(completed.returncode, 2)
                self.assertIn(message, completed.stderr)

            tampered = json.loads(manifest.read_text())
            tampered["items"][0]["formula_id"] = "sum_v1"
            manifest.write_text(json.dumps(tampered), encoding="utf-8")
            completed = run(
                "scripts/report_audit.py", "verdict", "--report", str(report),
                "--pack", str(pack), "--manifest", str(manifest),
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertNotIn("audit_passed", load_pack(pack)["checkpoints"])

    def test_v4_fixture_bytes_hash_and_verdict_remain_compatible(self) -> None:
        self.assertIsNone(parse_numeric("$10/share"))
        self.assertEqual(parse_numeric_v5("$10/share"), ("10", "$/share"))
        share_report = "## Evidence Ledger\n| Metric | Value |\n|---|---:|\n| EPS | $10/share |\n"
        self.assertEqual(build_manifest(share_report, MINIMUM_RATIO)["eligible_numeric_table_cells"], 0)
        expected_bytes = V4_MANIFEST.read_bytes()
        expected = json.loads(expected_bytes)
        rebuilt = build_manifest(V4_REPORT.read_text(encoding="utf-8"), MINIMUM_RATIO)
        rebuilt_bytes = (json.dumps(rebuilt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.assertEqual(rebuilt_bytes, expected_bytes)
        self.assertEqual(rebuilt["manifest_sha256"], expected["manifest_sha256"])
        results = results_template(rebuilt)
        for result, item in zip(results["results"], rebuilt["items"]):
            result["fresh_value"] = item["reported_value"]
            result["source"] = {
                "name": "SEC", "tier": "Tier 1",
                "source_url": "https://www.sec.gov/Archives", "authority_type": "regulator",
            }
        self.assertEqual(evaluate(rebuilt, results, V4_REPORT.read_text(encoding="utf-8"))["verdict"], "PASS")

        with tempfile.TemporaryDirectory() as raw:
            duplicate = Path(raw) / "duplicate.json"
            duplicate.write_text('{"version":4,"version":4}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                load_json(duplicate)

    def test_action_matrix_entry_schema_validation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report, _, base = self._workspace(Path(raw))
            report_bytes = report.read_bytes()
            base_copy = lambda: json.loads(json.dumps(base))

            good = base_copy()
            good["action_matrix"] = [
                {"action": "Buy", "trigger_type": "valuation", "condition": "N/A", "execution": "No position", "na": True},
                {"action": "Add", "trigger_type": "price", "condition": "Price < $8", "execution": "Add 1%", "na": False},
                {"action": "Sell", "trigger_type": "thesis-break", "condition": "Thesis broken", "execution": "Exit", "na": False},
            ]
            issues = schema_issues(good, verify_checkpoint_hashes=False, report_bytes=report_bytes)
            self.assertFalse([i for i in issues if "action_matrix" in i], issues)

            unknown_key = base_copy()
            unknown_key["action_matrix"] = [
                {"action": "Buy", "trigger_type": "price", "condition": "c", "execution": "e", "na": False, "extra": 1}
            ]
            self.assertTrue(
                any("unknown keys" in i for i in schema_issues(unknown_key, verify_checkpoint_hashes=False, report_bytes=report_bytes))
            )

            missing_key = base_copy()
            missing_key["action_matrix"] = [
                {"action": "Buy", "trigger_type": "price", "condition": "c", "execution": "e"}
            ]
            self.assertTrue(
                any("action_matrix[0] missing keys: na" in i for i in schema_issues(missing_key, verify_checkpoint_hashes=False, report_bytes=report_bytes))
            )

            bad_action = base_copy()
            bad_action["action_matrix"] = [
                {"action": "Wait", "trigger_type": "price", "condition": "c", "execution": "e", "na": False}
            ]
            self.assertTrue(
                any("action must be one of" in i for i in schema_issues(bad_action, verify_checkpoint_hashes=False, report_bytes=report_bytes))
            )

            bad_trigger = base_copy()
            bad_trigger["action_matrix"] = [
                {"action": "Buy", "trigger_type": "momentum", "condition": "c", "execution": "e", "na": False}
            ]
            self.assertTrue(
                any("trigger_type must be one of" in i for i in schema_issues(bad_trigger, verify_checkpoint_hashes=False, report_bytes=report_bytes))
            )

            na_on_hold = base_copy()
            na_on_hold["action_matrix"] = [
                {"action": "Hold", "trigger_type": "price", "condition": "c", "execution": "e", "na": True}
            ]
            self.assertTrue(
                any("na may be true only for Buy or Add" in i for i in schema_issues(na_on_hold, verify_checkpoint_hashes=False, report_bytes=report_bytes))
            )

            na_not_bool = base_copy()
            na_not_bool["action_matrix"] = [
                {"action": "Buy", "trigger_type": "price", "condition": "c", "execution": "e", "na": "yes"}
            ]
            self.assertTrue(
                any("na must be a boolean" in i for i in schema_issues(na_not_bool, verify_checkpoint_hashes=False, report_bytes=report_bytes))
            )

            empty_ok = base_copy()
            empty_ok["action_matrix"] = []
            self.assertFalse(
                [i for i in schema_issues(empty_ok, verify_checkpoint_hashes=False, report_bytes=report_bytes) if "action_matrix" in i]
            )

    def test_v5_semantic_action_matrix_correspondence_blocks_mismatch(self) -> None:
        from report_audit import action_matrix_correspondence_issues
        matrix_report = (
            FIXTURE.read_text(encoding="utf-8")
            + "\n\n## 8. 仓位与风控\n\n### Action Matrix\n"
            "| Action | Trigger type | Executable condition | Position/execution |\n"
            "|---|---|---|---|\n"
            "| Buy | valuation | N/A | No position |\n"
            "| Add | price | Price < $8 | Add 1% |\n"
            "| Hold | operating | Revenue >= $10B | Hold |\n"
            "| Reduce | valuation | Price >= $20 | Reduce to 3% |\n"
            "| Sell | thesis-break | Thesis broken | Exit |\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = directory / "report.md"
            report.write_text(matrix_report, encoding="utf-8")
            pack = self._pack(report)
            pack_path = directory / "pack.json"

            matching = [
                {"action": "Buy", "trigger_type": "valuation", "condition": "N/A", "execution": "No position", "na": True},
                {"action": "Add", "trigger_type": "price", "condition": "Price < $8", "execution": "Add 1%", "na": False},
                {"action": "Hold", "trigger_type": "operating", "condition": "Revenue >= $10B", "execution": "Hold", "na": False},
                {"action": "Reduce", "trigger_type": "valuation", "condition": "Price >= $20", "execution": "Reduce to 3%", "na": False},
                {"action": "Sell", "trigger_type": "thesis-break", "condition": "Thesis broken", "execution": "Exit", "na": False},
            ]
            pack["action_matrix"] = matching
            self.assertEqual(action_matrix_correspondence_issues(pack, matrix_report), [])
            self._refresh_checkpoints(pack, report)
            write_pack_atomic(pack_path, pack)
            manifest = directory / "manifest.json"
            self.assertEqual(self._extract(report, pack_path, manifest).returncode, 0, manifest.read_text())

            missing_sell = [e for e in matching if e["action"] != "Sell"]
            pack["action_matrix"] = missing_sell
            self._refresh_checkpoints(pack, report)
            write_pack_atomic(pack_path, pack)
            issues = action_matrix_correspondence_issues(pack, matrix_report)
            self.assertTrue(any("absent from the pack action_matrix: sell" in i for i in issues), issues)
            blocked = self._extract(report, pack_path, directory / "blocked.json")
            self.assertEqual(blocked.returncode, 2)
            self.assertIn("correspondence", blocked.stderr)

            extra_action = matching + [
                {"action": "Wait", "trigger_type": "price", "condition": "c", "execution": "e", "na": False}
            ]
            pack["action_matrix"] = extra_action
            self._refresh_checkpoints(pack, report)
            write_pack_atomic(pack_path, pack)
            self.assertTrue(
                any("missing actions present in the pack action_matrix: wait" in i for i in action_matrix_correspondence_issues(pack, matrix_report))
            )
            self.assertEqual(self._extract(report, pack_path, directory / "blocked2.json").returncode, 2)

            no_table_pack = json.loads(json.dumps(pack))
            no_table_pack["action_matrix"] = matching
            self._refresh_checkpoints(no_table_pack, report)
            no_table_report = directory / "no-matrix.md"
            no_table_report.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            no_table_path = directory / "no-matrix.json"
            write_pack_atomic(no_table_path, no_table_pack)
            self.assertEqual(
                self._extract(no_table_report, no_table_path, directory / "no-table.json").returncode, 2
            )

if __name__ == "__main__":
    unittest.main()

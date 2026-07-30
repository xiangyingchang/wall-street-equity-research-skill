#!/usr/bin/env python3
"""Regressions for canonical payback formulas and compatibility callers."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from a_share_prefetch import solve_payback as solve_a_share_payback  # noqa: E402
from financial_formulas import (  # noqa: E402
    CONVERGENCE_TOLERANCE,
    PaybackDomainError,
    PaybackNonConvergenceError,
    PaybackNonIdentifiableError,
    PaybackNoRootError,
    modeled_multiple,
    solve_payback,
)


MU_RATES = ("0", "0.0461", "0.0922", "0.08", "0.10")


class FinancialFormulaTests(unittest.TestCase):
    def test_mu_ttm_vectors(self) -> None:
        expected_percent = ("11.01", "16.13", "21.25", "19.90", "22.12")
        for rate, expected in zip(MU_RATES, expected_percent):
            with self.subTest(rate=rate):
                result = solve_payback("payback_ttm_v1", "18.576636", rate, 10)
                self.assertEqual((result.root * 100).quantize(Decimal("0.01")), Decimal(expected))
                self.assertLessEqual(result.absolute_residual, CONVERGENCE_TOLERANCE)
                self.assertLessEqual(result.interval_width, CONVERGENCE_TOLERANCE)

    def test_mu_forward_vectors_and_rejects_wrong_t0_discounting(self) -> None:
        multiple = Decimal("820.53") / Decimal("122.92")
        expected_percent = ("-9.395573", "-4.071637", "1.287244", "-0.134272", "2.197322")
        for rate, expected in zip(MU_RATES, expected_percent):
            with self.subTest(rate=rate):
                result = solve_payback("payback_forward_v1", multiple, rate, 10)
                self.assertEqual((result.root * 100).quantize(Decimal("0.000001")), Decimal(expected))
                self.assertLessEqual(result.absolute_residual, CONVERGENCE_TOLERANCE)
                with localcontext() as context:
                    context.prec = 50
                    wrong_t0 = sum(
                        (((Decimal("1") + result.root) / (Decimal("1") + Decimal(rate))) ** period)
                        for period in range(10)
                    )
                if rate != "0":
                    self.assertGreater(abs(wrong_t0 - multiple), Decimal("0.01"))
                self.assertLessEqual(
                    abs(modeled_multiple("payback_forward_v1", result.root, rate, 10) - multiple),
                    CONVERGENCE_TOLERANCE,
                )

    def test_meta_ttm_vector_from_current_report(self) -> None:
        nominal = solve_payback("payback_ttm_v1", "21.643", "0", 10)
        discounted = solve_payback("payback_ttm_v1", "21.643", "0.0469", 10)
        self.assertEqual((nominal.root * 100).quantize(Decimal("0.01")), Decimal("13.68"))
        self.assertEqual((discounted.root * 100).quantize(Decimal("0.01")), Decimal("19.01"))

    def test_domain_no_root_and_adaptive_upper_bracket(self) -> None:
        for multiple in ("0", "-1"):
            with self.subTest(multiple=multiple), self.assertRaises(PaybackDomainError):
                solve_payback("payback_ttm_v1", multiple, "0", 10)
        for years in (0, -1, 1.5, True):
            with self.subTest(years=years), self.assertRaises(PaybackDomainError):
                solve_payback("payback_ttm_v1", "1", "0", years)  # type: ignore[arg-type]
        with self.assertRaises(PaybackDomainError):
            solve_payback("payback_ttm_v1", "1", "-1", 10)
        with self.assertRaises(PaybackDomainError):
            solve_payback("unknown", "1", "0", 10)
        with self.assertRaises(PaybackNoRootError):
            solve_payback("payback_forward_v1", "1", "0", 10)
        high_growth = solve_payback("payback_ttm_v1", "5", "0", 1)
        self.assertGreater(high_growth.root, Decimal("1"))
        self.assertLessEqual(abs(high_growth.root - Decimal("4")), CONVERGENCE_TOLERANCE)

    def test_forward_one_year_is_always_non_identifiable(self) -> None:
        for multiple in ("1", "2"):
            with self.subTest(multiple=multiple), self.assertRaisesRegex(
                PaybackNonIdentifiableError, "non-identifiable.*growth-independent"
            ):
                solve_payback("payback_forward_v1", multiple, "0", 1)

    def test_tiny_nonzero_target_cannot_pass_on_absolute_residual_alone(self) -> None:
        with self.assertRaises(PaybackNonConvergenceError):
            solve_payback("payback_ttm_v1", "1e-60", "0", 10)

    def test_deterministic_unrounded_result_and_a_share_compatibility(self) -> None:
        first = solve_payback("payback_ttm_v1", "18.576636", "0.08", 10)
        second = solve_payback("payback_ttm_v1", "18.576636", "0.08", 10)
        self.assertEqual(first, second)
        self.assertNotEqual(first.root, first.root.quantize(Decimal("0.0001")))

        compatible = solve_a_share_payback(18.576636, 0.08)
        self.assertIsInstance(compatible, float)
        self.assertAlmostEqual(compatible, float(first.root), places=15)
        self.assertIsNone(solve_a_share_payback(0, 0.08))
        self.assertIsNone(solve_a_share_payback(18.576636, -1.0))

    def test_cli_json_numeric_fields_are_strings_and_human_output_is_readable(self) -> None:
        command = [
            sys.executable,
            "scripts/financial_rigor.py",
            "payback",
            "--formula-id",
            "payback_ttm_v1",
            "--multiple",
            "18.58",
            "--discount-rate",
            "0.08",
            "--years",
            "10",
        ]
        encoded = subprocess.run(command + ["--json"], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(encoded.returncode, 0, encoded.stderr)
        payload = json.loads(encoded.stdout)
        self.assertEqual(payload["formula_id"], "payback_ttm_v1")
        self.assertIs(payload["convergence"], True)
        for value in payload["inputs"].values():
            self.assertIsInstance(value, str)
        self.assertEqual(
            set(payload),
            {
                "formula_id",
                "inputs",
                "root",
                "modeled_multiple",
                "absolute_residual",
                "relative_residual",
                "iterations",
                "interval_width",
                "convergence",
            },
        )
        self.assertEqual(set(payload["inputs"]), {"multiple", "discount_rate", "years"})
        for key in (
            "root",
            "modeled_multiple",
            "absolute_residual",
            "relative_residual",
            "iterations",
            "interval_width",
        ):
            self.assertIsInstance(payload[key], str)
        self.assertLessEqual(Decimal(payload["absolute_residual"]), CONVERGENCE_TOLERANCE)
        self.assertLessEqual(Decimal(payload["relative_residual"]), CONVERGENCE_TOLERANCE)
        self.assertLessEqual(Decimal(payload["interval_width"]), CONVERGENCE_TOLERANCE)

        human = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn("Formula: payback_ttm_v1", human.stdout)
        self.assertIn("Required growth:", human.stdout)
        self.assertIn("Interval width:", human.stdout)
        self.assertIn("Converged: yes", human.stdout)

    def test_cli_rejects_unknown_formula_and_invalid_domains_on_stderr(self) -> None:
        cases = {
            "unknown formula": ("unknown", "1", "0", "10"),
            "invalid multiple": ("payback_ttm_v1", "0", "0", "10"),
            "invalid rate": ("payback_ttm_v1", "1", "-1", "10"),
            "invalid years": ("payback_ttm_v1", "1", "0", "0"),
        }
        for label, (formula_id, multiple, rate, years) in cases.items():
            with self.subTest(case=label):
                completed = self._run_payback_cli(formula_id, multiple, rate, years)
                self.assertNotEqual(completed.returncode, 0)
                self.assertTrue(completed.stderr.strip())
                self.assertIn("ERROR:", completed.stderr)

    def test_cli_rejects_forward_one_year_for_matching_and_nonmatching_targets(self) -> None:
        for multiple in ("1", "2"):
            with self.subTest(multiple=multiple):
                completed = self._run_payback_cli("payback_forward_v1", multiple, "0", "1")
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("non-identifiable", completed.stderr)
                self.assertIn("growth-independent", completed.stderr)

    def test_cli_reports_no_root_on_stderr(self) -> None:
        completed = self._run_payback_cli("payback_forward_v1", "1", "0", "10")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("ERROR:", completed.stderr)
        self.assertIn("no root", completed.stderr)

    def test_cli_reports_max_iteration_nonconvergence_on_stderr(self) -> None:
        completed = self._run_payback_cli("payback_ttm_v1", "1e-60", "0", "10")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("ERROR:", completed.stderr)
        self.assertIn("did not satisfy", completed.stderr)
        self.assertIn("1024 iterations", completed.stderr)

    @staticmethod
    def _run_payback_cli(
        formula_id: str, multiple: str, discount_rate: str, years: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "scripts/financial_rigor.py",
                "payback",
                "--formula-id",
                formula_id,
                "--multiple",
                multiple,
                "--discount-rate",
                discount_rate,
                "--years",
                years,
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()

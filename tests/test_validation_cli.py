#!/usr/bin/env python3
"""CLI-level regressions for the validation scripts."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))
from report_audit import MINIMUM_RATIO, build_manifest, extract_points, parse_numeric, source_valid  # noqa: E402


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PYTHON, *arguments], cwd=ROOT, text=True, capture_output=True, check=False)


def rehash_manifest(manifest: dict) -> None:
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    manifest["manifest_sha256"] = hashlib.sha256(encoded).hexdigest()


REPORT = """## Evidence Ledger
| Data | Value | Alternative |
|---|---:|---:|
| Current price | $100 | $100 |
| Revenue | ($0.80)B | -$0.80B |
| US 10Y government yield | 4.5% | |
| US 10Y government yield ×2 | 9.0% | |

## 4. Valuation
| Rate | EPS required g |
|---|---:|
| 10Y government yield ×1 | 5% |
"""


DECISION_CRITICAL_REPORT = """## Evidence Ledger
| Data | Value |
|---|---:|
| Current price | $595.19 |
| Total shares | 2.538B |
| Market cap | $1.511T |
| Cash | $81.180B |
| Debt | $58.748B |
| TTM EPS | $27.50 |
| TTM FCF/share | $17.9815 |
| US 10Y Treasury | 4.69% |
| US 10Y Treasury ×2 | 9.38% |
| Estimated portfolio weight | 5.24% |

## 4. Valuation
| Basis | Current multiple M | 10-year payback required annual g |
|---|---:|---:|
| TTM EPS | 21.643x | 13.68% |
| FCF/share | 33.100x | 21.05% |
| EV/FCF | 32.609x | 20.79% |

| Discount rate | EPS required g | FCF required g | EV/FCF required g |
|---|---:|---:|---:|
| 10Y Treasury ×1: 4.69% | 19.01% | 26.73% | 26.46% |
| 10Y Treasury ×2: 9.38% | 24.34% | 32.41% | 32.12% |
| 8% | 22.77% | 30.74% | 30.46% |
| 10% | 25.05% | 33.16% | 32.87% |
"""


class ValidationCliTests(unittest.TestCase):
    def write_report(self, directory: Path, text: str = REPORT) -> Path:
        path = directory / "report.md"
        path.write_text(text, encoding="utf-8")
        return path

    def extract(self, directory: Path, report: Path) -> tuple[Path, Path, dict]:
        manifest, results = directory / "manifest.json", directory / "results.json"
        completed = run("scripts/report_audit.py", "extract", "--report", str(report), "--manifest-out", str(manifest), "--results-out", str(results))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return manifest, results, json.loads(manifest.read_text())

    def test_extract_template_and_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = self.write_report(directory)
            manifest, results, payload = self.extract(directory, report)
            self.assertEqual(payload["eligible_numeric_table_cells"], 7)
            self.assertEqual(sum(item["field"] == "government_yield" for item in payload["items"]), 1)
            self.assertEqual(sum(item["field"] == "government_yield_x2" for item in payload["items"]), 1)
            self.assertIn("-0.80", {item["reported_value"] for item in extract_points(report.read_text(encoding="utf-8"))})
            template = json.loads(results.read_text())
            self.assertEqual(template["manifest_sha256"], payload["manifest_sha256"])
            for result, item in zip(template["results"], payload["items"]):
                result["fresh_value"] = item["reported_value"]
                result["source"] = {"name": "SEC", "tier": "Tier 1", "source_url": "https://www.sec.gov/Archives", "authority_type": "regulator"}
            results.write_text(json.dumps(template), encoding="utf-8")
            completed = run("scripts/report_audit.py", "verdict", "--report", str(report), "--manifest", str(manifest), "--results", str(results))
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_decision_critical_fields_are_mandatory_and_payback_is_not_yield(self) -> None:
        manifest = build_manifest(DECISION_CRITICAL_REPORT, MINIMUM_RATIO)
        self.assertEqual(manifest, build_manifest(DECISION_CRITICAL_REPORT, MINIMUM_RATIO))
        fields = {item["field"] for item in manifest["items"]}
        self.assertTrue(
            {
                "market_price",
                "shares",
                "market_cap",
                "cash",
                "debt",
                "ttm_eps",
                "ttm_fcf_per_share",
                "government_yield",
                "government_yield_x2",
                "portfolio_weight",
                "payback_eps",
                "payback_fcf",
                "payback_ev_fcf",
            }.issubset(fields)
        )
        payback = [item for item in manifest["items"] if item["field"].startswith("payback_")]
        self.assertEqual(sum(item["field"] == "payback_eps" for item in payback), 5)
        self.assertEqual(sum(item["field"] == "payback_fcf" for item in payback), 5)
        self.assertEqual(sum(item["field"] == "payback_ev_fcf" for item in payback), 5)
        self.assertFalse(any(item["field"].startswith("government_yield") for item in payback))
        self.assertEqual(
            Decimal(manifest["actual_ratio"]),
            Decimal(len(manifest["items"])) / Decimal(manifest["eligible_numeric_table_cells"]),
        )
        self.assertGreater(Decimal(manifest["actual_ratio"]), MINIMUM_RATIO)

    def test_malformed_empty_stale_and_tier2_spread(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = self.write_report(directory)
            manifest, results, payload = self.extract(directory, report)
            low_ratio = run("scripts/report_audit.py", "extract", "--report", str(report), "--manifest-out", str(directory / "low-manifest.json"), "--results-out", str(directory / "low-results.json"), "--ratio", "0.14")
            self.assertEqual(low_ratio.returncode, 2)
            results.write_text("{", encoding="utf-8")
            malformed = run("scripts/report_audit.py", "verdict", "--report", str(report), "--manifest", str(manifest), "--results", str(results))
            self.assertEqual(malformed.returncode, 2)
            empty = self.write_report(directory, "## Evidence Ledger\n| A | B |\n|---|---|\n")
            empty_manifest, empty_results, _ = self.extract(directory, empty)
            blocked = run("scripts/report_audit.py", "verdict", "--report", str(empty), "--manifest", str(empty_manifest), "--results", str(empty_results))
            self.assertEqual(blocked.returncode, 1)
            report.write_text(REPORT + "\nchanged", encoding="utf-8")
            stale = run("scripts/report_audit.py", "verdict", "--report", str(report), "--manifest", str(manifest), "--results", str(empty_results))
            self.assertEqual(stale.returncode, 1)
            self.assertIn("current report hash differs", stale.stdout)

    def test_report_type_marker(self) -> None:
        fixture = (ROOT / "tests/fixtures/good-full-report.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as raw:
            ordinary = Path(raw) / "ordinary.md"
            ordinary.write_text(fixture, encoding="utf-8")
            self.assertEqual(run("scripts/report_lint.py", str(ordinary)).returncode, 0)
            update = Path(raw) / "update.md"
            update.write_text(fixture.replace("报告类型 | 常规报告", "报告类型 | 最新财报更新"), encoding="utf-8")
            self.assertEqual(run("scripts/report_lint.py", str(update)).returncode, 1)

    def test_tier2_spread_blocks_in_either_source_order(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            for report_text, pairs in ((REPORT, (("100", "105.1"), ("105.1", "100"))), (REPORT.replace("| Current price | $100 | $100 |", "| Current price | -$100 | -$100 |"), (("-100", "-105.1"), ("-105.1", "-100")))):
                report = self.write_report(directory, report_text)
                manifest, results, payload = self.extract(directory, report)
                for first, second in pairs:
                    template = json.loads(results.read_text())
                    for result, item in zip(template["results"], payload["items"]):
                        result["fresh_value"] = item["reported_value"]
                        result["source"] = {"name": "SEC", "tier": "Tier 1", "source_url": "https://www.sec.gov/Archives", "authority_type": "regulator"}
                    target = next(index for index, item in enumerate(payload["items"]) if item["field"] == "market_price")
                    template["results"][target].update({"fresh_value": first, "source": {"name": "StockAnalysis", "tier": "Tier 2", "source_url": "https://stockanalysis.com/stocks/x", "authority_type": "tier2_vendor"}, "secondary_source": {"name": "Yahoo Finance", "tier": "Tier 2", "source_url": "https://finance.yahoo.com/quote/X", "authority_type": "tier2_vendor", "value": second}, "reconciliation": True, "reconciliation_explanation": "Explicitly measured independent-source spread."})
                    results.write_text(json.dumps(template), encoding="utf-8")
                    completed = run("scripts/report_audit.py", "verdict", "--report", str(report), "--manifest", str(manifest), "--results", str(results))
                    self.assertEqual(completed.returncode, 1, completed.stderr)

    def test_full_cell_amount_forms_and_excluded_columns(self) -> None:
        amount_report = """## Evidence Ledger
| Metric | Value | Date | Source | 判断 |
|---|---:|---|---|---|
| Revenue A | ($0.80B) | 2026-07-26 | SEC 10-K | 10Y basis |
| Revenue B | ($0.80)B | 2026-07-26 | SEC 10-K | pass 5% |
| Revenue C | (¥0.80亿) | 2026-07-26 | SEC 10-K | pass |
| Revenue D | -$1.25B | 2026-07-26 | SEC 10-K | pass |
| Revenue E | -¥0.80亿 | 2026-07-26 | SEC 10-K | pass |
| Revenue F | $-1.25B | 2026-07-26 | SEC 10-K | pass |
| Margin | 12.5% | 2026-07-26 | Filing | pass |
| Users | 1,234.56 | 2026-07-26 | Filing | pass |
| Rejected | about $1.2B | 2026-07-26 | Filing | pass |
"""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = self.write_report(directory, amount_report)
            _, _, manifest = self.extract(directory, report)
            self.assertEqual(manifest["eligible_numeric_table_cells"], 8)
            self.assertEqual(parse_numeric("($0.80B)"), ("-0.80", "$B"))
            self.assertEqual(parse_numeric("($0.80)B"), ("-0.80", "$B"))
            self.assertEqual(parse_numeric("(¥0.80亿)"), ("-0.80", "¥亿"))
            self.assertEqual(parse_numeric("-$1.25B"), ("-1.25", "$B"))
            self.assertEqual(parse_numeric("-¥0.80亿"), ("-0.80", "¥亿"))
            self.assertEqual(parse_numeric("$-1.25B"), ("-1.25", "$B"))
            self.assertEqual(parse_numeric("12.5%"), ("12.5", "%"))
            self.assertEqual(parse_numeric("1,234.56"), ("1234.56", ""))
            self.assertIsNone(parse_numeric("about $1.2B"))

    def test_canonical_fixture_extracts_only_intended_values(self) -> None:
        fixture = ROOT / "tests/fixtures/good-full-report.md"
        with tempfile.TemporaryDirectory() as raw:
            _, _, manifest = self.extract(Path(raw), fixture)
            self.assertEqual(manifest["eligible_numeric_table_cells"], 5)
            self.assertEqual(len(manifest["items"]), 5)
            self.assertEqual(sum(item["field"] == "government_yield" for item in manifest["items"]), 1)
            self.assertEqual(sum(item["field"] == "payback_eps" for item in manifest["items"]), 4)
            self.assertFalse(
                any(
                    item["field"].startswith("government_yield")
                    for item in manifest["items"]
                    if item["section"].startswith("## 4.")
                )
            )

    def test_rehashed_manifest_tampering_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = self.write_report(directory)
            manifest_path, results, original = self.extract(directory, report)
            for case in ("reduced", "added", "altered"):
                manifest = json.loads(json.dumps(original))
                if case == "reduced":
                    manifest["items"] = manifest["items"][:-1]
                elif case == "added":
                    fake = dict(manifest["items"][0])
                    fake["id"] = "f" * 64
                    manifest["items"].append(fake)
                else:
                    manifest["items"][0]["reported_value"] = "999"
                rehash_manifest(manifest)
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                completed = run("scripts/report_audit.py", "verdict", "--report", str(report), "--manifest", str(manifest_path), "--results", str(results))
                self.assertEqual(completed.returncode, 1, case)

    def test_same_vendor_subdomains_and_symmetric_financial_cli(self) -> None:
        for values in ('{"a":100,"b":105.1}', '{"a":105.1,"b":100}', '{"a":-100,"b":-105.1}', '{"a":-105.1,"b":-100}'):
            completed = run("scripts/financial_rigor.py", "cross-validate", "--field", "spread", "--values", values)
            self.assertEqual(completed.returncode, 1, values)
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = self.write_report(directory)
            manifest, results, payload = self.extract(directory, report)
            template = json.loads(results.read_text())
            for result, item in zip(template["results"], payload["items"]):
                result["fresh_value"] = item["reported_value"]
                result["source"] = {"name": "SEC", "tier": "Tier 1", "source_url": "https://www.sec.gov/Archives", "authority_type": "regulator"}
            target = next(index for index, item in enumerate(payload["items"]) if item["field"] == "market_price")
            template["results"][target].update({"fresh_value": "100", "source": {"name": "Yahoo", "tier": "Tier 2", "source_url": "https://finance.yahoo.com/quote/X", "authority_type": "tier2_vendor"}, "secondary_source": {"name": "Yahoo API", "tier": "Tier 2", "source_url": "https://query1.finance.yahoo.com/v8/X", "authority_type": "tier2_vendor", "value": "100"}, "reconciliation": True, "reconciliation_explanation": "same vendor check"})
            results.write_text(json.dumps(template), encoding="utf-8")
            completed = run("scripts/report_audit.py", "verdict", "--report", str(report), "--manifest", str(manifest), "--results", str(results))
            self.assertNotEqual(completed.returncode, 0)

    def test_official_us_yield_domains_are_tier1(self) -> None:
        for url in (
            "https://www.federalreserve.gov/releases/h15/",
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/",
        ):
            source = {"name": "US government yield", "tier": "Tier 1", "source_url": url, "authority_type": "regulator"}
            self.assertEqual(source_valid(source, ["Tier 1"], "source"), source)

    def test_portfolio_weight_uses_scoped_internal_evidence(self) -> None:
        for url in (
            "https://github.com/xiangyingchang/portfolio-dashboard",
            "https://GITHUB.COM/XIANGYINGCHANG/PORTFOLIO-DASHBOARD/",
        ):
            with self.subTest(url=url):
                source = {
                    "name": "Portfolio Dashboard",
                    "tier": "Internal",
                    "source_url": url,
                    "authority_type": "portfolio_system",
                }
                self.assertEqual(source_valid(source, ["Internal"], "source"), source)
        for url in (
            "https://github.com/attacker/fake-portfolio",
            "https://github.com/xiangyingchang/portfolio-dashboard-evil",
            "https://example.com/xiangyingchang/portfolio-dashboard",
        ):
            with self.subTest(url=url):
                invalid = {
                    "name": "Fake Portfolio",
                    "tier": "Internal",
                    "source_url": url,
                    "authority_type": "portfolio_system",
                }
                with self.assertRaisesRegex(ValueError, "approved portfolio system"):
                    source_valid(invalid, ["Internal"], "source")

    def test_verdict_fails_closed_on_missing_or_invalid_required_results(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = self.write_report(directory)
            manifest, results, payload = self.extract(directory, report)
            valid = json.loads(results.read_text())
            for result, item in zip(valid["results"], payload["items"]):
                result["fresh_value"] = item["reported_value"]
                result["source"] = {
                    "name": "SEC",
                    "tier": "Tier 1",
                    "source_url": "https://www.sec.gov/Archives",
                    "authority_type": "regulator",
                }

            missing = json.loads(json.dumps(valid))
            missing["results"].pop()
            results.write_text(json.dumps(missing), encoding="utf-8")
            completed = run(
                "scripts/report_audit.py",
                "verdict",
                "--report",
                str(report),
                "--manifest",
                str(manifest),
                "--results",
                str(results),
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("results must cover every manifest ID exactly once", completed.stderr)

            empty_outcome = json.loads(json.dumps(valid))
            empty_outcome["results"][0]["fresh_value"] = ""
            results.write_text(json.dumps(empty_outcome), encoding="utf-8")
            completed = run(
                "scripts/report_audit.py",
                "verdict",
                "--report",
                str(report),
                "--manifest",
                str(manifest),
                "--results",
                str(results),
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("invalid numeric value", completed.stderr)

            invalid_source = json.loads(json.dumps(valid))
            invalid_source["results"][0]["source"] = {
                "name": "",
                "tier": "",
                "source_url": "",
                "authority_type": "",
            }
            results.write_text(json.dumps(invalid_source), encoding="utf-8")
            completed = run(
                "scripts/report_audit.py",
                "verdict",
                "--report",
                str(report),
                "--manifest",
                str(manifest),
                "--results",
                str(results),
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("requires name, tier, source_url, and authority_type", completed.stderr)


if __name__ == "__main__":
    unittest.main()

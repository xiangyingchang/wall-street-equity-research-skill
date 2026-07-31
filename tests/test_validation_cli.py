#!/usr/bin/env python3
"""CLI-level regressions for the validation scripts."""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
RUNTIME_VERDICT_FILES = (
    ROOT / "README.md",
    ROOT / "SKILL.md",
    ROOT / "agents/openai.yaml",
    ROOT / "examples/input-template.md",
    ROOT / "templates/full-report.md",
    ROOT / "references/data-validation.md",
    ROOT / "references/full-methodology.md",
    ROOT / "references/report-contract.md",
    ROOT / "references/researchability.md",
    ROOT / "references/source-map.md",
)
VERDICT_DECLARATION_FILES = (
    ROOT / "README.md",
    ROOT / "agents/openai.yaml",
    ROOT / "references/full-methodology.md",
    ROOT / "references/report-contract.md",
)
OBSOLETE_VERDICT_PATTERNS = (
    re.compile(r"Hold\s*/\s*Index", re.I),
    re.compile(r"Avoid-Chase", re.I),
    re.compile(r"Buy\s*/\s*Hold\s*/\s*Watchlist\s*/\s*Avoid", re.I),
    re.compile(r"\bbuy\s*,\s*hold\s*,\s*watchlist\s*,\s*(?:or\s+)?avoid\b", re.I),
)
CANONICAL_VERDICT_LIST = re.compile(
    r"Buy\s*(?:/|,)\s*Hold-Index\s*(?:/|,)\s*Watchlist\s*(?:/|,)\s*(?:or\s+)?Avoid",
    re.I,
)
sys.path.insert(0, str(ROOT / "scripts"))
from report_audit import MINIMUM_RATIO, build_manifest, classification_matches, extract_points, parse_numeric, recognize_fields, source_valid  # noqa: E402


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

    def test_runtime_verdict_vocabulary_is_canonical(self) -> None:
        violations = []
        for path in RUNTIME_VERDICT_FILES:
            text = path.read_text(encoding="utf-8")
            for pattern in OBSOLETE_VERDICT_PATTERNS:
                for match in pattern.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    violations.append(f"{path.relative_to(ROOT)}:{line}: {match.group(0)}")
        self.assertEqual(violations, [], "obsolete runtime verdict vocabulary:\n" + "\n".join(violations))
        for path in VERDICT_DECLARATION_FILES:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertRegex(path.read_text(encoding="utf-8"), CANONICAL_VERDICT_LIST)

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

    def test_recognize_placeholder_template_and_contract_failures(self) -> None:
        template = (ROOT / "templates/full-report.md").read_text(encoding="utf-8")
        recognized = recognize_fields(template)
        self.assertEqual(recognized["status"], "PASS", recognized)
        self.assertEqual(set(recognized["recognized_mandatory_categories"]), {
            "market_price", "shares", "market_cap", "cash", "debt", "ttm_eps",
            "ttm_fcf_per_share", "government_yield", "government_yield_x2",
            "portfolio_weight", "payback_eps", "payback_fcf", "payback_ev_fcf",
        })
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            report = self.write_report(directory, template)
            completed = run("scripts/report_audit.py", "recognize", "--report", str(report))
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

            complete_with_unrecognized = template.replace(
                "| 当前价格 | TODO |",
                "| 当前价格 | TODO |\n| 当前报价 | TODO |",
                1,
            )
            report.write_text(complete_with_unrecognized, encoding="utf-8")
            unrecognized = run("scripts/report_audit.py", "recognize", "--report", str(report))
            self.assertEqual(unrecognized.returncode, 1)
            self.assertIn('"missing_required_categories": []', unrecognized.stdout)
            self.assertIn('"line_number"', unrecognized.stdout)
            self.assertIn("当前报价", unrecognized.stdout)

            report.write_text(template.replace("| 当前价格 | TODO |", "| 当前价格及市值 | TODO |", 1), encoding="utf-8")
            ambiguous = run("scripts/report_audit.py", "recognize", "--report", str(report))
            self.assertEqual(ambiguous.returncode, 1)
            self.assertIn('"ambiguous_decision_label_rows"', ambiguous.stdout)
            self.assertIn("当前价格及市值", ambiguous.stdout)
            self.assertEqual(
                classification_matches("## Evidence Ledger", "当前价格及市值", "数值"),
                ["market_price", "market_cap"],
            )

    def test_recognize_invalid_input_returns_usage_error(self) -> None:
        missing = run("scripts/report_audit.py", "recognize", "--report", "/definitely/missing/report.md")
        self.assertEqual(missing.returncode, 2)
        with tempfile.TemporaryDirectory() as raw:
            invalid = Path(raw) / "report.txt"
            invalid.write_text("not markdown", encoding="utf-8")
            completed = run("scripts/report_audit.py", "recognize", "--report", str(invalid))
            self.assertEqual(completed.returncode, 2)
            self.assertIn("expected a Markdown report", completed.stderr)

    def test_action_matrix_negative_contracts(self) -> None:
        fixture = (ROOT / "tests/fixtures/good-full-report.md").read_text(encoding="utf-8")
        matrix = """### Action Matrix
| Action | Trigger type | Executable condition | Position/execution |
|---|---|---|---|
| Buy | valuation | N/A — current action is not Buy | No position |
| Add | price | Price < $8 and operating gates pass | Add 1% |
| Hold | operating | Revenue >= $100亿 | Hold current position |
| Reduce | valuation | Price >= $20 | Reduce to 3% |
| Sell | thesis-break | Thesis broken | Exit position |
"""
        cases = {
            "missing": (fixture.replace(matrix, ""), "exactly one"),
            "duplicate": (fixture.replace(matrix, matrix + "\n" + matrix), "exactly one"),
            "wrong-columns": (fixture.replace("Action | Trigger type | Executable condition | Position/execution", "Action | Type | Condition | Execution"), "columns must be exactly"),
            "missing-action": (fixture.replace("| Buy | valuation | N/A — current action is not Buy | No position |\n", ""), "missing actions: buy"),
            "missing-type": (fixture.replace("| Sell | thesis-break | Thesis broken | Exit position |", "| Sell | operating | Thesis broken | Exit position |"), "missing trigger types: thesis-break"),
            "external-trade": (fixture.replace("## Sources", "如果价格低于 $8，就 Buy。\n\n## Sources"), "conditional threshold trade"),
           "post-matrix-h4-trade": (fixture.replace("## 9.", "#### Post-matrix note\n价格低于 $8：加仓\n\n## 9.", 1), "conditional threshold trade"),
           "all-na": (fixture.replace("| Add | price | Price < $8 and operating gates pass | Add 1% |", "| Add | price | N/A | N/A |").replace("| Hold | operating | Revenue >= $100亿 | Hold current position |", "| Hold | operating | N/A | N/A |").replace("| Reduce | valuation | Price >= $20 | Reduce to 3% |", "| Reduce | valuation | N/A | N/A |").replace("| Sell | thesis-break | Thesis broken | Exit position |", "| Sell | thesis-break | N/A | N/A |"), "missing executable non-N/A"),
           "hold-na": (fixture.replace("| Hold | operating | Revenue >= $100亿 | Hold current position |", "| Hold | operating | N/A | N/A |"), "N/A is allowed only for Buy or Add"),
            "legacy": (fixture.replace("### Action Matrix", "### Action Triggers", 1), "legacy 'Action Triggers'"),
        }
        with tempfile.TemporaryDirectory() as raw:
            for name, (text, expected) in cases.items():
                with self.subTest(name=name):
                    report = Path(raw) / f"{name}.md"
                    report.write_text(text, encoding="utf-8")
                    completed = run("scripts/report_lint.py", str(report))
                    self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
                    self.assertIn(expected, completed.stdout)

    def test_action_matrix_ignores_company_competitor_prose(self) -> None:
        fixture = (ROOT / "tests/fixtures/good-full-report.md").read_text(encoding="utf-8")
        prose = "当竞争对手价格低于 $8 时卖出资产，公司利润会下降。\n| 安全买入区间 | 参考区间：<$8；这里只汇总估值区间，执行条件见唯一 Action Matrix。 |"
        with tempfile.TemporaryDirectory() as raw:
            report = Path(raw) / "competitor-prose.md"
            report.write_text(fixture.replace("## Sources", f"{prose}\n\n## Sources"), encoding="utf-8")
            completed = run("scripts/report_lint.py", str(report))
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_new_report_runs_recognition_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            output = directory / "generated.md"
            completed = run(
                "scripts/new_report.py",
                "--ticker", "TEST",
                "--company", "Test Company",
                "--market", "US",
                "--out", str(output),
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(completed.stdout, f"{output}\n")
            self.assertTrue(output.exists())

            sandbox = directory / "invalid-skill"
            shutil.copytree(ROOT / "scripts", sandbox / "scripts")
            shutil.copytree(ROOT / "templates", sandbox / "templates")
            template = sandbox / "templates" / "full-report.md"
            template.write_text(
                template.read_text(encoding="utf-8").replace("| 当前价格 | TODO |", "| 当前报价 | TODO |", 1),
                encoding="utf-8",
            )
            invalid_output = directory / "invalid.md"
            failed = subprocess.run(
                [
                    PYTHON,
                    str(sandbox / "scripts" / "new_report.py"),
                    "--ticker", "TEST",
                    "--company", "Test Company",
                    "--market", "US",
                    "--out", str(invalid_output),
                ],
                cwd=sandbox,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("failed field recognition", failed.stderr)
            self.assertFalse(invalid_output.exists())

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
            self.assertEqual(manifest["eligible_numeric_table_cells"], 11)
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

    def test_tax_identity_gate_blocks_silent_omission(self) -> None:
        fixture = (ROOT / "tests/fixtures/good-full-report.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            missing = directory / "no-tax.md"
            missing.write_text(fixture.replace("税务身份=中国大陆个人；", ""), encoding="utf-8")
            blocked = run("scripts/report_lint.py", str(missing))
            self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
            self.assertIn("tax identity", blocked.stdout)

            na_ok = directory / "tax-na.md"
            na_ok.write_text(
                fixture.replace("税务身份=中国大陆个人；", "税务身份=N/A，原因：免税账户；"),
                encoding="utf-8",
            )
            passed = run("scripts/report_lint.py", str(na_ok))
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)

            english_ok = directory / "tax-en.md"
            english_ok.write_text(
                fixture.replace("税务身份=中国大陆个人；", "tax identity: US-listed investor; "),
                encoding="utf-8",
            )
            passed_en = run("scripts/report_lint.py", str(english_ok))
            self.assertEqual(passed_en.returncode, 0, passed_en.stdout + passed_en.stderr)

    def test_opportunity_cost_gate_blocks_all_ratings_without_benchmark(self) -> None:
        fixture = (ROOT / "tests/fixtures/good-full-report.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            no_benchmark = directory / "no-benchmark.md"
            stripped = (
                fixture.replace("机会成本=美国 10Y 国债 ×2。", "")
                .replace("| 美国 10Y 国债 | 4.5% | 2026-07-01 | Treasury | 10Y | 高 |", "| 指标 | 4.5% | 2026-07-01 | Treasury | 10Y | 高 |")
                .replace("10Y 国债 ×1", "贴现率 ×1")
                .replace("10Y 国债 ×2", "贴现率 ×2")
                .replace("机会成本才是真成本", "沉没成本才是真成本")
                .replace("机会成本胜出", "持有成本胜出")
                .replace("## 7. 机构视角 + 机会成本", "## 7. 机构视角")
            )
            no_benchmark.write_text(stripped, encoding="utf-8")
            blocked = run("scripts/report_lint.py", str(no_benchmark))
            self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
            self.assertIn("opportunity-cost benchmark", blocked.stdout)

    def test_previous_report_delta_gate_requires_rating_metric_thesis(self) -> None:
        fixture = (ROOT / "tests/fixtures/good-full-report.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            cue_only = directory / "cue-only.md"
            cue_only.write_text(
                fixture + "\n本报告是上一份报告的更新报告。\n",
                encoding="utf-8",
            )
            blocked = run("scripts/report_lint.py", str(cue_only))
            self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
            self.assertIn("rating change", blocked.stdout)
            self.assertIn("key metrics", blocked.stdout)
            self.assertIn("thesis change", blocked.stdout)

            full_delta = directory / "full-delta.md"
            full_delta.write_text(
                fixture + "\n本报告是上一份报告的更新报告。评级维持不变。EPS 从 8 变化到 10。投资逻辑不变。\n",
                encoding="utf-8",
            )
            passed = run("scripts/report_lint.py", str(full_delta))
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)

            no_cue = directory / "no-cue.md"
            no_cue.write_text(fixture, encoding="utf-8")
            self.assertEqual(run("scripts/report_lint.py", str(no_cue)).returncode, 0)


if __name__ == "__main__":
    unittest.main()

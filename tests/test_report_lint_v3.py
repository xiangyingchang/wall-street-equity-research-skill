import unittest
from pathlib import Path

from scripts import report_lint


FIXTURE = Path(__file__).parent / "fixtures-v3" / "good-v3-report.md"


class V3ReportLintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good = FIXTURE.read_text(encoding="utf-8")

    def test_v3_fixture_passes(self):
        self.assertEqual(report_lint.lint_v3_text(self.good), [])

    def test_frontmatter_fails(self):
        report = "---\nverdict: Watchlist\n---\n" + self.good
        self.assertTrue(report_lint.lint_v3_text(report))

    def test_dividend_total_guard_fails_when_removed(self):
        report = self.good.replace("dividend-total", "manual dividend sum")
        self.assertTrue(report_lint.lint_v3_text(report))

    def test_v3_contract_requires_three_discount_rows(self):
        report = self.good.replace("| 10Y 国债 ×2 | 5% | 7% | 观察 |\n", "")
        self.assertTrue(report_lint.lint_v3_text(report))


if __name__ == "__main__":
    unittest.main()

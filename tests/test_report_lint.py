import unittest
from pathlib import Path

from scripts import report_lint


FIXTURE = Path(__file__).parent / "fixtures" / "good-full-report.md"


class ReportLintContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good = FIXTURE.read_text(encoding="utf-8")

    def assert_fails(self, report: str, message: str):
        errors = report_lint.lint_text(report)
        self.assertTrue(errors, message)

    def test_good_fixture_passes(self):
        self.assertEqual(report_lint.lint_text(self.good), [])

    def test_requires_real_https_source(self):
        report = self.good.replace("https://investor.example.invalid/earnings", "")
        self.assert_fails(report, "source-less report must fail")

    def test_requires_exact_unique_top_level_modules(self):
        report = self.good.replace("## Sources\n", "## 9. Duplicate\nextra\n\n## Sources\n", 1)
        self.assert_fails(report, "duplicate module must fail")

    def test_requires_evidence_data_row(self):
        report = self.good.replace(
            "| 数据项 | 数值 | 日期 | 来源/层级 | 口径 | 可信度 |\n"
            "|---|---:|---|---|---|---|\n"
            "| 美国 10Y 国债 | 4.5% | 2026-07-01 | Treasury | 10Y | 高 |\n",
            "",
        )
        self.assert_fails(report, "empty evidence ledger must fail")

    def test_requires_discount_rows_as_table_rows(self):
        report = self.good.replace(
            "| 10Y 国债 ×1 | 1% | 通过 |\n"
            "| 10Y 国债 ×2 | 5% | 观察 |\n"
            "| 8% | 8% | 观察 |\n"
            "| 10% | 10% | 偏难 |\n",
            "文字说明：贴现率包括 10Y 国债 ×1、10Y 国债 ×2、8% 和 10%，但未形成表格。\n",
        )
        self.assert_fails(report, "discount prose without rows must fail")

    def test_network_effect_requires_user_metrics(self):
        report = self.good.replace(
            "网络效应：用户规模 10 亿，较上年增长 8%；参与度和 ARPU 继续提升。",
            "网络效应仍然强。",
        )
        self.assert_fails(report, "unsupported network-effect claim must fail")

    def test_constrained_liquidity_requires_exit_inputs(self):
        report = self.good.replace("流动性结论：不构成约束。", "流动性结论：构成约束。")
        self.assert_fails(report, "constrained liquidity without math must fail")

    def test_unresolved_placeholder_fails(self):
        report = self.good.replace("业务判断：广告商业化仍是主要价值驱动。", "业务判断：TODO")
        self.assert_fails(report, "placeholder report must fail")

    def test_normalization_bridge_is_required(self):
        report = self.good.replace("### Reported / Adjusted / Normalized 正常化桥", "### 财务桥")
        self.assert_fails(report, "normalization bridge must be explicit")

    def test_profit_and_cash_normalization_must_be_separate(self):
        report = self.good.replace("利润正常化与现金流正常化分开；", "利润和现金流一起正常化；")
        self.assert_fails(report, "profit and cash normalization must be separated")

    def test_valuation_inputs_and_dividend_treatment_are_required(self):
        report = self.good.replace("股息处理为 reinvested_yield。", "股息率已考虑。")
        self.assert_fails(report, "dividend treatment must be explicit")


if __name__ == "__main__":
    unittest.main()

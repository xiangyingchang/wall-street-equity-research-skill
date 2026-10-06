import unittest

from scripts import report_lint


class PriceDisciplineLabelTests(unittest.TestCase):
    good = '### Price Discipline 价格纪律\n| 价格线 | 怎么算 | 数值 | 情景 / 置信度 | 动作含义 |\n|---|---|---:|---|---|\n| **盈利参考价**（`Earnings reference price`） | 常态 EPS × 参考 PE | $10 | Base / 中 | 估值参考，不自动买入 |\n| **目标回报价**（`Target-return price`） | 目标回报倒推买入价 | $9 | Base / 中 | 目标回报 |\n| **现金流确认价**（`Cash-confirmation price`） | 常态 FCF/股 ÷ 现金收益率门槛 | $8 | Base / 中 | 现金确认 |\n| **联合新资金价**（`Joint new-money price`） | 所有有效执行门槛中的最低价 | $8 | Base / 中 | Review / Buy gate |\n| **安全边际价**（`Safety price`） | 目标回报价 ×（1 - 安全边际） | $6 | Base / 中 | 安全边际 |\nPrice Discipline 输入：Base 情景；Normalized EPS $10；reference PE 18x；Normalized FCF/share $2；cash hurdle 6%，现金流置信度 medium；joint action Review。公式由 `scripts/valuation_math.py` 计算，动作映射为 Review。\n\n'

    def test_price_discipline_requires_chinese_reader_labels(self):
        for label in ("盈利参考价", "目标回报价", "现金流确认价", "联合新资金价", "安全边际价"):
            with self.subTest(label=label):
                report = self.good.replace(label, "English-only label")
                self.assertTrue(any(
                    "Chinese reader-facing" in error
                    for error in report_lint.price_discipline_label_errors(report)
                ))

    def test_price_discipline_rejects_chinese_label_in_later_column(self):
        report = self.good.replace(
            "| **盈利参考价**（`Earnings reference price`） | 常态 EPS × 参考 PE |",
            "| Earnings reference price | **盈利参考价** 常态 EPS × 参考 PE |",
        )
        self.assertIn(
            "Price Discipline must use a Chinese reader-facing Chinese earnings reference label",
            report_lint.price_discipline_label_errors(report),
        )

    def test_price_discipline_rejects_label_prefix_only(self):
        report = self.good.replace("盈利参考价", "盈利参考价错误标签")
        self.assertIn(
            "Price Discipline must use a Chinese reader-facing Chinese earnings reference label",
            report_lint.price_discipline_label_errors(report),
        )

    def test_price_discipline_accepts_plain_chinese_first_column(self):
        report = self.good.replace(
            "**盈利参考价**（`Earnings reference price`）", "盈利参考价"
        )
        self.assertEqual(report_lint.price_discipline_label_errors(report), [])

    def test_active_report_without_legacy_table_is_unchanged(self):
        self.assertEqual(report_lint.price_discipline_label_errors("### 估值\n目标回报价 $9"), [])

    def test_full_report_uses_label_gate(self):
        from pathlib import Path
        report = (Path(__file__).parent / "fixtures" / "good-full-report.md").read_text()
        report = report.replace("### 名义", self.good + "### 名义", 1)
        self.assertEqual(report_lint.lint_text(report), [])
        self.assertTrue(any("Chinese reader-facing" in e for e in report_lint.lint_text(
            report.replace("盈利参考价", "English-only label")
        )))

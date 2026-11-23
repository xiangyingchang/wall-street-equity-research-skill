from pathlib import Path
import tempfile
import unittest

from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_lint import lint_text, top_sections
from scripts.report_pipeline_v3 import build, verify
from scripts.report_readable_v3 import READING_ORDER, split_report
from scripts.report_renderer_v3 import render_audit_markdown, render_reader_markdown
from scripts.report_spec_v2 import SpecError, sha256
from tests.meta_v3_spec import make_spec, write_spec
from tests.test_annual_cash_basis import annual_spec
from tests.test_price_currency_fx import _hkd_spec


class ReadableReportTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.spec = Path(directory.name) / "spec.json"
        self.output = self.spec.with_suffix(".md")
        write_spec(self.spec)
        self.receipt = build(self.spec, self.output)
        self.reader = self.output.read_text(encoding="utf-8")
        self.body, self.appendix = split_report(self.reader)

    def test_default_build_has_one_reading_path_and_receipt(self):
        self.assertIn(READING_ORDER, self.body)
        self.assertEqual([title for title, _ in top_sections(self.reader)], [
            "1. 现在怎么做", "2. 经营证据", "3. 估值", "4. 什么会改变仓位判断",
            "5. 附录｜财务底稿、估值明细与执行规则",
        ])
        self.assertLess(self.body.index("**新资金：暂不买入"), self.body.index("### 价格指导"))
        self.assertIn("已有仓位：复核", self.body)
        self.assertIn("研究候选为“减仓”", self.body)
        self.assertNotIn("Action Matrix", self.body)
        self.assertEqual(self.reader.count("Action Matrix（唯一执行口径）"), 1)
        self.assertEqual(lint_text(self.reader), [])
        self.assertEqual(self.receipt["checks"]["readable_presentation"], "PASS")
        self.assertEqual(self.receipt["reader_markdown_hash"], sha256(self.reader))
        self.assertEqual(verify(self.spec, self.output)["reader_markdown_hash"], sha256(self.reader))
        self.assertEqual({path.name for path in self.spec.parent.iterdir()}, {
            "spec.json", "spec.md", "spec.audit.md", "spec.md.bundle.json", "spec.md.verification.json",
        })

    def test_appendix_retains_all_compiler_content_and_audit(self):
        bundle = compile_report_v3(make_spec())
        self.assertEqual(self.appendix, render_reader_markdown(bundle))
        for heading in ("Action Matrix（唯一执行口径）", "利润率 × 退出市盈率", "最近四个季度", "公司特有经营闸门",
                        "与上次报告相比", "新资金价格阶梯", "Action Triggers", "主要来源"):
            self.assertIn(heading, self.appendix)
        self.assertEqual(lint_text(self.appendix), [])
        self.assertEqual(self.output.with_suffix(".audit.md").read_text(encoding="utf-8"),
                         render_audit_markdown(bundle))

    def test_body_reuses_prices_and_model_numbers_at_the_same_precision(self):
        self.assertIn("**参考股价** $549.00（2026-07-31，USD）", self.body)
        for label in ("目标回报价", "安全边际价"):
            row = next(line for line in self.appendix.splitlines() if line.startswith(f"| {label} |"))
            self.assertIn(row, self.body)
        self.assertIn("期末折算年化回报为 5.51%，目标为 9.40%", self.body)
        self.assertIn("每股收益年增长 6.00%", self.body)
        self.assertIn("18.00 倍市盈率", self.body)
        self.assertIn("0.50% 的股息率", self.body)
        self.assertIn("2.74%", self.body)
        self.assertIn("$159.87", self.body)
        self.assertIn("目标仓位的 **0%**", self.body)

    def test_readable_prices_follow_the_listing_currency(self):
        write_spec(self.spec, _hkd_spec())
        build(self.spec, self.output)
        body, appendix = split_report(self.output.read_text(encoding="utf-8"))
        self.assertIn("**参考股价** HK$4,282.20（2026-07-31，HKD）", body)
        self.assertIn("计价口径", body)
        for label in ("目标回报价", "安全边际价"):
            price_row = next(line for line in appendix.splitlines() if line.startswith(f"| {label} |"))
            self.assertIn("HK$", price_row)
            self.assertIn(price_row, body)

    def test_unknown_cash_is_disclosed_without_a_current_cash_price(self):
        write_spec(self.spec, annual_spec())
        build(self.spec, self.output)
        body, appendix = split_report(self.output.read_text(encoding="utf-8"))
        self.assertIn("最新现金流尚未核实", body)
        self.assertIn("目标仓位的 **0%**", body)
        self.assertNotIn("股价不高于", body)
        self.assertIn("FY2025 历史年度自由现金流", appendix)

    def test_verify_rejects_tampered_numbers_in_either_section(self):
        for from_end in (False, True):
            with self.subTest(appendix=from_end):
                pos = self.reader.rindex("$456.67") if from_end else self.reader.index("$456.67")
                changed = self.reader[:pos] + self.reader[pos:].replace("$456.67", "$456.68", 1)
                self.output.write_text(changed, encoding="utf-8")
                with self.assertRaisesRegex(SpecError, "Reader Markdown differs"):
                    verify(self.spec, self.output)

    def test_independent_lint_rejects_missing_body_and_appendix(self):
        self.assertTrue(lint_text(self.reader.replace("## 3. 估值", "### 3. 估值", 1)))
        self.assertTrue(lint_text(self.body))
        self.assertTrue(lint_text(self.reader.replace("#### 三口径回本测试", "", 1)))

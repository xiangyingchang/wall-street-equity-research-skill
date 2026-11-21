from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_pipeline_v3 import build, verify
from scripts.report_spec_v2 import SpecError
from tests.meta_v3_spec import make_spec, write_spec


def annual_spec():
    s = make_spec()
    fid = s["quarterly_series"]["fcf"][0]
    annual = deepcopy(s["facts"][fid])
    annual.update(value="100", period="FY2025", period_end="2025-12-31")
    s["facts"]["FACT-ANNUAL-FCF"] = annual
    s["quarterly_series"]["fcf"] = []
    s["cash_flow_basis"] = {"frequency": "annual", "fact_id": "FACT-ANNUAL-FCF", "period_end": "2025-12-31", "reason": "公司仅披露年度现金流，最新季度实际现金流尚未公开。"}
    s["report"]["cash_valuation"].pop("fcf_fact_ids", None)
    s["decision_support"]["cash_flow_escalation"] = {"status": "unknown", "pending": "最新季度现金流与连续负现金流季度数尚未披露，需等正式财报确认"}
    return s


class AnnualCashBasisTests(unittest.TestCase):
    def test_historical_cash_remains_labeled_and_blocks_money(self):
        s = annual_spec()
        b = compile_report_v3(s)
        self.assertEqual(b["derived"]["ttm"]["fcf"]["frequency"], "annual")
        self.assertEqual(b["derived"]["cash_valuation"]["fcf"]["label"], "FY2025 历史年度自由现金流")
        self.assertEqual(float(b["decision_coherence"]["executable_position_max"]), 0)
        self.assertEqual(b["decision"]["existing_position_candidate_action"], "REVIEW")
        self.assertEqual(b["data_quality"]["cash_flow_basis"]["status"], "REVIEW")
        self.assertIsNone(b["decision_coherence"]["escalation"]["actual"])
        with tempfile.TemporaryDirectory() as tmp:
            spec, out = Path(tmp)/"annual.json", Path(tmp)/"annual.md"
            write_spec(spec, s)
            build(spec, out)
            verify(spec, out)
            reader = out.read_text()
            self.assertIn("FY2025 历史年度自由现金流", reader)
            self.assertIn("不得将未披露计数记为零", reader)
            self.assertNotIn("TTM FCF", reader)
            self.assertIn("不是上述四季 TTM", reader)
            self.assertNotIn("None 个季度", reader)
            self.assertNotIn("未升级", reader)
            self.assertIn("最新现金未核验，不能据此建仓", reader)
            self.assertNotIn("大仓位只在该价附近成立", reader)
            self.assertIn("最新现金流已核验、连续负现金流季度数已确认且新资金闸门已重新通过", reader)

    def test_cannot_fabricate_quarters_or_unknown_zero(self):
        for mutate in (
            lambda s: s["quarterly_series"].update(fcf=make_spec()["quarterly_series"]["fcf"]),
            lambda s: s["cash_flow_basis"].update(period_end="2027-12-31"),
            lambda s: s["facts"]["FACT-ANNUAL-FCF"].update(period="FY2025-Q4"),
            lambda s: s["decision_support"]["cash_flow_escalation"].update(status="known"),
            lambda s: s["decision_support"]["cash_flow_escalation"].update(counter_ref="FACT-CAPEX-CONSECUTIVE"),
        ):
            s = annual_spec()
            mutate(s)
            with self.assertRaises(SpecError):
                compile_report_v3(s)

    def test_undisclosed_prior_irr_is_not_zero(self):
        s = annual_spec()
        s["prior_report_context"].update(previous_base_irr_reported=None, calculation_status="unverified")
        b = compile_report_v3(s)
        self.assertIsNone(b["prior_report_context"]["previous_base_irr_reported"])
        s["prior_report_context"]["calculation_status"] = "verified"
        with self.assertRaises(SpecError):
            compile_report_v3(s)

    def test_unknown_cash_prevents_buy_even_at_deep_discount(self):
        s = annual_spec()
        s["facts"][s["report"]["current_price_fact_id"]]["value"] = "100"
        metric = s["decision_policy"]["operating"]["metrics"][0]
        metric["hold_threshold"], metric["reduce_threshold"] = "1", "0.5"
        b = compile_report_v3(s)
        self.assertEqual(b["decision"]["new_money_action"], "WATCH")
        self.assertEqual(float(b["decision_coherence"]["executable_position_max"]), 0)

    def test_unknown_cash_never_hides_independent_thesis_break(self):
        s = annual_spec()
        for condition in s["decision_policy"]["thesis_break"]["conditions"]:
            s["facts"][condition["fact_id"]]["value"] = "0" if condition["operator"] == "<" else "5"
        b = compile_report_v3(s)
        self.assertEqual(b["decision"]["existing_position_candidate_action"], "SELL")
        self.assertEqual(b["decision"]["new_money_action"], "DO_NOT_BUY")

    def test_future_annual_cash_is_rejected(self):
        s = annual_spec()
        s["cash_flow_basis"]["period_end"] = "2027-12-31"
        s["facts"]["FACT-ANNUAL-FCF"].update(period="FY2027", period_end="2027-12-31")
        with self.assertRaisesRegex(SpecError, "after report.as_of"):
            compile_report_v3(s)

    def test_annual_fact_must_match_year_and_fcf_metric(self):
        s = annual_spec()
        s["facts"]["FACT-ANNUAL-FCF"]["period"] = "FY2030"
        with self.assertRaisesRegex(SpecError, "FY year"):
            compile_report_v3(s)
        s = annual_spec()
        s["cash_flow_basis"]["fact_id"] = "FACT-REVENUE-FY2025"
        s["facts"]["FACT-REVENUE-FY2025"] = s["facts"].pop("FACT-ANNUAL-FCF")
        with self.assertRaisesRegex(SpecError, "identify free cash flow"):
            compile_report_v3(s)

    def test_payback_uses_cash_decisive_basis_instead_of_gaap_eps(self):
        from scripts.report_renderer_v3 import _payback_principle
        b = compile_report_v3(annual_spec())
        # Force a profitable-looking EPS reference alongside a more demanding cash basis.
        target = min(b["derived"]["payback_required_growth"], key=lambda r: abs(float(r)-float(b["target_return"])))
        b["derived"]["payback_required_growth"][target] = "0.01"
        row = next(x for x in b["derived"]["cash_valuation"]["bases"] if x["basis_id"] == "fcf")
        rate = min(row["payback_required_growth"], key=lambda r: abs(float(r)-float(b["target_return"])))
        row["payback_required_growth"][rate] = "0.1417"
        result, explanation = _payback_principle(b)
        self.assertIn("当前不通过", result)
        self.assertIn("14.17%", explanation)
        self.assertIn("不能替代独立现金增长假设", explanation)
        self.assertNotEqual(result, "通过")

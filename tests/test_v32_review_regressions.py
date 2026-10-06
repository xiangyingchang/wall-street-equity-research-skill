"""Behavior regressions for the four confirmed v3.2 review findings."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from scripts.ledger_portfolio_preflight import portfolio_context_draft
from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_pipeline_v3 import build, verify
from scripts.report_renderer_v3 import render_reader_markdown
from scripts.report_spec_v2 import SpecError, _ttm_sum
from tests.meta_v3_spec import make_spec, write_spec


class ReviewDecisionTests(unittest.TestCase):
    def buy_spec(self):
        spec = make_spec()
        spec["facts"][spec["report"]["current_price_fact_id"]]["value"] = "100"
        metric = spec["decision_policy"]["operating"]["metrics"][0]
        metric["hold_threshold"], metric["reduce_threshold"] = "1", "0.5"
        return spec

    def test_buy_with_zero_execution_cap_is_rejected_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, reader = Path(tmp) / "spec.json", Path(tmp) / "reader.md"
            write_spec(source, self.buy_spec())
            with self.assertRaisesRegex(SpecError, "executable position cap is zero"):
                build(source, reader)
            self.assertFalse(reader.exists())
            with self.assertRaisesRegex(SpecError, "executable position cap is zero"):
                verify(source, reader)

    def test_verified_positive_execution_cap_allows_buy(self):
        spec = self.buy_spec()
        for tier in ("trial", "build", "full"):
            spec["decision_support"]["ladder_premises"][tier]["conditions"] = [
                {"label": "当前经营闸门", "ref": "BUNDLE:/decision/operating/status",
                 "operator": "==", "threshold": "hold"}]
        with tempfile.TemporaryDirectory() as tmp:
            source, reader = Path(tmp) / "spec.json", Path(tmp) / "reader.md"
            write_spec(source, spec)
            build(source, reader)
            self.assertEqual(verify(source, reader)["status"], "PASS")
        bundle = compile_report_v3(spec)
        self.assertEqual(bundle["decision"]["new_money_action"], "BUY")
        self.assertGreater(float(bundle["decision_coherence"]["executable_position_max"]), 0)

    def test_majority_upper_bound_cannot_hide_behind_49_percent_minimum(self):
        spec = make_spec()
        tiers = spec["decision_policy"]["price_ladder"]["tiers"]
        tiers[2]["position_min"], tiers[2]["position_max"] = "0.49", "0.60"
        tiers[3]["position_min"] = "0.49"
        tiers[2]["floor_ref"] = "BUNDLE:/scenarios/base/prices/buy"
        tiers[2]["floor_multiplier"] = "0.95"
        with self.assertRaisesRegex(SpecError, "cash_gate_waiver"):
            compile_report_v3(spec)


class ReviewTtmTests(unittest.TestCase):
    def test_repeated_fcf_quarter_rejected_by_build(self):
        spec = make_spec()
        spec["report"]["cash_valuation"]["fcf_fact_ids"] = ["FACT-Q1-26-FCF"] * 4
        with self.assertRaisesRegex(SpecError, "unique fact IDs"):
            compile_report_v3(spec)
        with tempfile.TemporaryDirectory() as tmp:
            source, reader = Path(tmp) / "spec.json", Path(tmp) / "reader.md"
            write_spec(source, spec)
            for operation in (build, verify):
                with self.assertRaisesRegex(SpecError, "unique fact IDs"):
                    operation(source, reader)

    def test_duplicate_period_with_distinct_fact_ids_rejected(self):
        spec = make_spec()
        ids = spec["quarterly_series"]["fcf"]
        spec["facts"][ids[0]]["period"] = spec["facts"][ids[1]]["period"]
        with self.assertRaisesRegex(SpecError, "consecutive fiscal quarters"):
            _ttm_sum(spec, ids, "cash_valuation.fcf")

    def test_nonconsecutive_quarters_rejected(self):
        spec = make_spec()
        ids = spec["quarterly_series"]["fcf"]
        spec["facts"][ids[0]]["period"] = "Q1 2025"
        with self.assertRaisesRegex(SpecError, "consecutive fiscal quarters"):
            _ttm_sum(spec, ids, "cash_valuation.fcf")

    def test_missing_period_rejected(self):
        spec = make_spec()
        ids = spec["quarterly_series"]["fcf"]
        spec["facts"][ids[0]].pop("period")
        with self.assertRaisesRegex(SpecError, "FYyyyy-Qn"):
            _ttm_sum(spec, ids, "cash_valuation.fcf")

    def test_valid_ttm_keeps_exact_total(self):
        spec = make_spec()
        total, unit = _ttm_sum(spec, spec["quarterly_series"]["fcf"], "cash_valuation.fcf")
        self.assertEqual(str(total), "378.70")
        self.assertEqual(unit, "USD bn/10")


class ReviewTickerTests(unittest.TestCase):
    def snapshot(self, code="00700.HK", market="HK"):
        return {"trusted": True, "warnings": [], "retrieved_at": "2026-10-06T00:00:00Z",
                "positions": [{"code": code, "market": market, "currency": "HKD", "holding_value": 1000}]}

    def test_hong_kong_aliases_identify_the_same_holding(self):
        for ticker in ("0700.HK", "00700.HK", "700.HK", "00700"):
            with self.subTest(ticker=ticker):
                self.assertEqual(portfolio_context_draft(self.snapshot(), ticker)["position_status"], "held")

    def test_explicit_market_is_preserved(self):
        self.assertEqual(portfolio_context_draft(self.snapshot(), "00700.US")["position_status"], "not_held")

    def test_bare_record_uses_its_market(self):
        self.assertEqual(portfolio_context_draft(self.snapshot("0700", "HK"), "00700.HK")["position_status"], "held")

    def test_share_class_suffix_is_not_discarded(self):
        snapshot = self.snapshot("BRK.B", "US")
        self.assertEqual(portfolio_context_draft(snapshot, "BRK.B.US")["position_status"], "held")
        self.assertEqual(portfolio_context_draft(snapshot, "BRK.A.US")["position_status"], "not_held")

    def test_duplicate_alias_records_require_review(self):
        snapshot = self.snapshot()
        duplicate = deepcopy(snapshot["positions"][0])
        duplicate["code"] = "0700.HK"
        snapshot["positions"].append(duplicate)
        self.assertEqual(portfolio_context_draft(snapshot, "0700.HK")["position_status"], "unknown")


class FollowupReviewTests(unittest.TestCase):
    def test_future_cash_quarters_fail_build_and_verify(self):
        spec = make_spec()
        spec["report"]["cash_valuation"]["fcf_fact_ids"] = []
        for index, fid in enumerate(spec["quarterly_series"]["fcf"]):
            key = f"FACT-FUTURE-FCF-{index}"
            spec["facts"][key] = deepcopy(spec["facts"][fid])
            spec["facts"][key]["period"] = ("Q3 2029", "Q4 2029", "Q1 2030", "Q2 2030")[index]
            spec["report"]["cash_valuation"]["fcf_fact_ids"].append(key)
        with tempfile.TemporaryDirectory() as tmp:
            source, reader = Path(tmp) / "spec.json", Path(tmp) / "reader.md"
            write_spec(source, spec)
            for operation in (build, verify):
                with self.assertRaisesRegex(SpecError, "after report.as_of"):
                    operation(source, reader)
            self.assertFalse(reader.exists())

    def test_future_baseline_is_rejected_even_if_cash_window_matches(self):
        spec = make_spec()
        for name in ("eps", "revenue", "operating_income", "fcf"):
            for index, fid in enumerate(spec["quarterly_series"][name]):
                spec["facts"][fid]["period"] = ("Q3 2029", "Q4 2029", "Q1 2030", "Q2 2030")[index]
        with self.assertRaisesRegex(SpecError, "after report.as_of"):
            compile_report_v3(spec)

    def test_stale_consecutive_cash_window_cannot_replace_baseline(self):
        spec = make_spec()
        ids = []
        for index, fid in enumerate(spec["quarterly_series"]["fcf"]):
            key = f"FACT-STALE-FCF-{index}"
            spec["facts"][key] = deepcopy(spec["facts"][fid])
            spec["facts"][key]["period"] = ("Q3 2024", "Q4 2024", "Q1 2025", "Q2 2025")[index]
            ids.append(key)
        spec["report"]["cash_valuation"]["fcf_fact_ids"] = ids
        with self.assertRaisesRegex(SpecError, "match the baseline"):
            compile_report_v3(spec)

    def test_explicit_quarter_end_after_cutoff_is_rejected(self):
        spec = make_spec()
        spec["facts"]["FACT-Q2-26-FCF"]["period_end"] = "2027-06-30"
        with self.assertRaisesRegex(SpecError, "after report.as_of"):
            compile_report_v3(spec)

    def test_noncalendar_fiscal_quarters_use_explicit_end_dates(self):
        spec = make_spec()
        ids = spec["quarterly_series"]["fcf"]
        for series in ("fcf", "eps"):
            for index, fid in enumerate(spec["quarterly_series"][series]):
                spec["facts"][fid]["period"] = f"FY2026-Q{index + 1}"
                spec["facts"][fid]["period_end"] = ("2025-08-31", "2025-11-30", "2026-02-28", "2026-05-31")[index]
        total, _ = _ttm_sum(spec, ids, "cash_valuation.fcf")
        self.assertEqual(str(total), "378.70")

    def test_static_final_action_requires_migration(self):
        spec = make_spec()
        spec["research"]["final_verdict"]["hold_equals_buy"] = {
            "text": "当前价格不会成为新的主动买入选择。",
            "evidence_refs": ["BUNDLE:/decision/new_money_action"], "confidence": "medium"}
        with self.assertRaisesRegex(SpecError, "migrate static conclusions"):
            compile_report_v3(spec)

    def test_binding_cannot_hide_a_hardcoded_contradictory_action(self):
        spec = make_spec()
        spec["research_graph"]["themes"][0]["decision_impact"]["text_template"] += "新资金暂不买入。"
        with self.assertRaisesRegex(SpecError, "unbound action conclusion"):
            compile_report_v3(spec)

    def test_adjudication_implication_cannot_add_a_second_action(self):
        spec = make_spec()
        spec["research_graph"]["debate"]["adjudication"]["implication"] = "因此不否定公司质量；新资金暂不买入。"
        with self.assertRaisesRegex(SpecError, "unbound action conclusion"):
            compile_report_v3(spec)

    def test_price_change_updates_all_material_action_conclusions(self):
        spec = ReviewDecisionTests().buy_spec()
        for tier in ("trial", "build", "full"):
            spec["decision_support"]["ladder_premises"][tier]["conditions"] = [
                {"label": "当前经营闸门", "ref": "BUNDLE:/decision/operating/status", "operator": "==", "threshold": "hold"}]
        bundle = compile_report_v3(spec)
        self.assertEqual(bundle["decision"]["new_money_action"], "BUY")
        claims = [theme["decision_impact"] for theme in bundle["research_graph"]["themes"]]
        claims += [bundle["research_graph"]["debate"]["adjudication"], bundle["research"]["final_verdict"]["hold_equals_buy"]]
        for claim in claims:
            self.assertIn("买入", claim["text"])
            self.assertNotIn("不买入", claim["text"])
        reader = render_reader_markdown(bundle)
        self.assertNotIn("新增资金暂不买入", reader)
        self.assertNotIn("新资金暂不买入", reader)
        self.assertNotIn("当前价格不会成为新的主动买入选择", reader)
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "spec.json", Path(tmp) / "reader.md"
            write_spec(source, spec)
            build(source, output)
            self.assertEqual(verify(source, output)["status"], "PASS")

    def test_unchanged_price_keeps_no_buy_conclusions(self):
        bundle = compile_report_v3(make_spec())
        self.assertEqual(bundle["decision"]["new_money_action"], "DO_NOT_BUY")
        self.assertIn("不买入", bundle["research"]["final_verdict"]["hold_equals_buy"]["text"])
        self.assertIn("不买入", bundle["research_graph"]["debate"]["adjudication"]["text"])

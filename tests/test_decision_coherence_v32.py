"""Regression tests for the v3.2 decision-coherence layer (company-agnostic contracts)."""
from __future__ import annotations

from copy import deepcopy
import tempfile
from pathlib import Path
import unittest

from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_pipeline_v3 import build
from scripts.report_spec_v2 import SpecError
from tests.meta_v3_spec import make_spec, write_spec


class DecisionCoherenceV32Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = make_spec()
        cls.bundle = compile_report_v3(deepcopy(cls.spec))
        with tempfile.TemporaryDirectory() as tmp:
            spec_path, report_path = Path(tmp) / "meta.spec.json", Path(tmp) / "meta.md"
            write_spec(spec_path, deepcopy(cls.spec))
            build(spec_path, report_path)
            cls.reader = report_path.read_text(encoding="utf-8")

    def assertCompileFails(self, spec, fragment):
        with self.assertRaises(SpecError) as ctx:
            compile_report_v3(spec)
        self.assertIn(fragment, str(ctx.exception))

    # ---- compiled output ----
    def test_coherence_block_compiled(self):
        c = self.bundle["decision_coherence"]
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["decisive"]["basis_id"], "fcf")
        self.assertEqual(c["executable_position_max"], "0.0000")
        self.assertEqual(c["escalation"]["current_level"], 1)
        self.assertIsNotNone(c["roic"]["incremental_roic"])

    def test_exactly_one_executable_tier_at_most(self):
        tiers = self.bundle["price_ladder"]["tiers"]
        self.assertLessEqual(sum(1 for t in tiers if t["executable"]), 1)
        self.assertTrue(all("premise_status" in t for t in tiers))

    def test_sensitivity_grid_present(self):
        grid = self.bundle["decision_sensitivity"]["grid"]
        self.assertEqual(len(grid["rows"]), 5)
        self.assertEqual(len(grid["columns"]), 5)

    def test_reader_surfaces(self):
        for marker in ("### 现金流升级表", "### ROIC 与增量 ROIC", "利润率 × 退出市盈率", "可执行新资金上限", "现金门槛", "前提状态", "决定买点的口径"):
            self.assertIn(marker, self.reader)
        self.assertEqual(self.reader.count("◀ 价格所在"), 1)

    # ---- fail-closed contracts ----
    def test_missing_decisive_basis_fails(self):
        spec = deepcopy(self.spec)
        spec["report"]["cash_valuation"].pop("decisive_basis")
        self.assertCompileFails(spec, "decisive")

    def test_invalid_accounting_basis_fails(self):
        spec = deepcopy(self.spec)
        spec["report"]["cash_valuation"]["earnings_bases"][0]["accounting_basis"] = "pro-forma"
        self.assertCompileFails(spec, "accounting_basis")

    def test_watch_cannot_exceed_trial_cap(self):
        spec = deepcopy(self.spec)
        spec["decision_policy"]["price_ladder"]["tiers"][0]["position_max"] = "0.5"
        spec["decision_support"]["ladder_premises"]["no-chase"]["conditions"] = [
            {"label": "经营闸门", "ref": "BUNDLE:/decision/operating/status", "operator": "==", "threshold": "hold"}]
        spec["decision_support"]["cash_flow_escalation"]["levels"][0]["new_money_cap"] = "1"
        with self.assertRaises(SpecError):
            compile_report_v3(spec)

    def test_allocating_tier_requires_conditions(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["ladder_premises"]["trial"].pop("conditions")
        self.assertCompileFails(spec, "machine-checkable premises")

    def test_unknown_premise_blocks_execution(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["ladder_premises"]["trial"]["conditions"] = [
            {"label": "资本开支指引不再上调", "status": "unknown", "pending": "下一季财报指引"}]
        bundle = compile_report_v3(spec)
        tiers = {t["tier_id"]: t for t in bundle["price_ladder"]["tiers"]}
        self.assertEqual(tiers["trial"]["premise_status"], "unknown")
        self.assertFalse(tiers["trial"]["executable"])

    def test_unmet_outranks_unknown(self):
        tiers = {t["tier_id"]: t for t in self.bundle["price_ladder"]["tiers"]}
        self.assertEqual(tiers["trial"]["premise_status"], "unmet")

    def test_escalation_top_level_must_match_thesis_break(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["cash_flow_escalation"]["levels"][-1]["min_count"] = 5
        self.assertCompileFails(spec, "thesis-break threshold")

    def test_escalation_top_level_must_stop_new_money(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["cash_flow_escalation"]["levels"][-1]["new_money_cap"] = "0.05"
        self.assertCompileFails(spec, "top level must stop")

    def test_escalation_caps_must_not_increase(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["cash_flow_escalation"]["levels"][1]["new_money_cap"] = "0.5"
        self.assertCompileFails(spec, "non-increasing")

    def test_thesis_trigger_must_sell(self):
        spec = deepcopy(self.spec)
        for t in spec["decision_support"]["action_triggers"]:
            if t["category"] == "thesis_break":
                t["existing_action"] = "REVIEW"
        self.assertCompileFails(spec, "thesis_break trigger")

    def test_valuation_trigger_cannot_sell(self):
        spec = deepcopy(self.spec)
        for t in spec["decision_support"]["action_triggers"]:
            if t["category"] == "valuation":
                t["existing_action"] = "SELL"
        self.assertCompileFails(spec, "valuation alone")

    def test_trigger_requires_existing_action(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["action_triggers"][0].pop("existing_action")
        self.assertCompileFails(spec, "existing_action")

    def test_peer_basis_must_match_own_basis(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["valuation"]["peers"][0]["basis"] = "adjusted"
        self.assertCompileFails(spec, "like with like")

    def test_normalized_layer_cannot_reuse_other_refs(self):
        spec = deepcopy(self.spec)
        rows = spec["decision_support"]["normalization"]
        normalized = next(r for r in rows if r["layer"] == "normalized")
        normalized["value_refs"] = ["FACT-Q2-26-FCF"]
        self.assertCompileFails(spec, "only repeats")

    def test_normalized_layer_requires_method(self):
        spec = deepcopy(self.spec)
        next(r for r in spec["decision_support"]["normalization"] if r["layer"] == "normalized").pop("method")
        self.assertCompileFails(spec, "requires method")

    def test_growth_ceiling_must_bind_numbers(self):
        spec = deepcopy(self.spec)
        spec["research"]["growth_limits"]["ceiling"] = {
            "text": "可持续增长上限取决于商业化效率能否快于资本和监管成本上升。",
            "evidence_refs": ["SRC-META-Q2-2026"], "implication": "乐观情景需要经营杠杆重新出现。", "confidence": "medium"}
        self.assertCompileFails(spec, "growth_limits.ceiling")

    def test_comparators_must_bind_numbers(self):
        spec = deepcopy(self.spec)
        comparators = spec["research"]["opportunity_cost"]["comparators"]
        comparators[1] = {"claim": "股票最低目标回报是决策门槛，而不是可直接购买的资产。", "evidence_refs": ["BUNDLE:/target_return"],
                          "implication": "不得把门槛伪装成低风险替代品。", "confidence": "high"}
        self.assertCompileFails(spec, "opportunity_cost")

    def test_roic_requires_positive_capital(self):
        spec = deepcopy(self.spec)
        spec["facts"]["FACT-FY2025-CASH-SEC"]["value"] = "99999"
        self.assertCompileFails(spec, "invested capital must be positive")

    def test_majority_tier_requires_cash_gate_or_waiver(self):
        spec = deepcopy(self.spec)
        tiers = spec["decision_policy"]["price_ladder"]["tiers"]
        tiers[2]["position_min"] = "0.5"
        tiers[2]["position_max"] = "0.6"
        tiers[2]["floor_ref"] = "BUNDLE:/scenarios/base/prices/buy"
        tiers[2]["floor_multiplier"] = "0.95"
        self.assertCompileFails(spec, "cash_gate_waiver")
        spec["decision_policy"]["price_ladder"]["cash_gate_waiver"] = "大仓位不以现金口径为准，原因是资本开支属于一次性扩产且已有合同覆盖。"
        compile_report_v3(spec)


if __name__ == "__main__":
    unittest.main()

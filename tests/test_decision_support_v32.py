from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import tempfile
from pathlib import Path
import unittest

from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_lint import lint_text
from scripts.report_pipeline_v3 import build
from scripts.report_spec_v2 import SpecError
from tests.meta_v3_spec import make_spec, write_spec


def D(value) -> Decimal:
    return Decimal(str(value))


class DecisionSupportV32Tests(unittest.TestCase):
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

    # ---- contract presence ----
    def test_missing_decision_support_fails(self):
        spec = deepcopy(self.spec)
        spec.pop("decision_support")
        self.assertCompileFails(spec, "decision_support")

    def test_missing_cash_valuation_fails(self):
        spec = deepcopy(self.spec)
        spec["report"].pop("cash_valuation")
        self.assertCompileFails(spec, "cash_valuation")

    def test_missing_price_ladder_fails(self):
        spec = deepcopy(self.spec)
        spec["decision_policy"].pop("price_ladder")
        self.assertCompileFails(spec, "price_ladder")

    # ---- decision support content ----
    def test_missing_trigger_category_fails(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["action_triggers"] = [t for t in spec["decision_support"]["action_triggers"] if t["category"] != "cash_flow"]
        self.assertCompileFails(spec, "cash_flow")

    def test_too_few_risks_fails(self):
        spec = deepcopy(self.spec)
        spec["research"]["risks"]["items"] = spec["research"]["risks"]["items"][:4]
        self.assertCompileFails(spec, "risks")

    def test_risk_without_probability_fails(self):
        spec = deepcopy(self.spec)
        spec["research"]["risks"]["items"][0].pop("probability")
        self.assertCompileFails(spec, "probability")

    def test_ladder_premises_must_match_tiers(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["ladder_premises"].pop("full")
        self.assertCompileFails(spec, "ladder_premises")

    def test_too_few_peers_fails(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["valuation"]["peers"] = spec["decision_support"]["valuation"]["peers"][:2]
        self.assertCompileFails(spec, "peers")

    def test_history_requires_normalization_layers(self):
        spec = deepcopy(self.spec)
        spec["decision_support"]["normalization"] = [r for r in spec["decision_support"]["normalization"] if r["layer"] != "normalized"]
        self.assertCompileFails(spec, "normalized")

    # ---- price ladder rules ----
    def test_ladder_floor_must_decrease(self):
        spec = deepcopy(self.spec)
        spec["decision_policy"]["price_ladder"]["tiers"][2]["floor_multiplier"] = "1.10"
        self.assertCompileFails(spec, "floor")

    def test_tier_above_target_return_must_be_zero(self):
        spec = deepcopy(self.spec)
        spec["decision_policy"]["price_ladder"]["tiers"][0]["position_max"] = "0.10"
        self.assertCompileFails(spec, "new money must be zero")

    def test_exactly_one_current_tier(self):
        tiers = self.bundle["price_ladder"]["tiers"]
        self.assertEqual(sum(1 for t in tiers if t["current"]), 1)

    # ---- numeric correctness ----
    def test_cash_valuation_math(self):
        cv = self.bundle["derived"]["cash_valuation"]
        price = D(self.spec["facts"]["FACT-CURRENT-PRICE"]["value"])
        target = D(self.bundle["target_return"])
        for row in cv["bases"]:
            self.assertLessEqual(abs(D(row["multiple"]) * D(row["per_share_price"]) - price), D("0.05"))
            self.assertLessEqual(abs(D(row["yield"]) - D(row["per_share_price"]) / price), D("0.0001"))
        fcf = cv["fcf"]
        self.assertLessEqual(abs(D(cv["cash_confirmation_price"]) - D(fcf["per_share_price"]) / target), D("0.05"))
        self.assertEqual(cv["fcf_passes_hurdle"], D(fcf["yield"]) >= target)

    def test_dividend_math(self):
        div = self.bundle["derived"]["cash_valuation"]["dividend"]
        dps, g, w, n = D(div["dps_price"]), D(div["growth"]), D(div["withholding"]), int(div["years"])
        gross = sum(dps * (1 + g) ** t for t in range(n))
        self.assertLessEqual(abs(D(div["gross_total"]) - gross), D("0.01"))
        self.assertLessEqual(abs(D(div["net_total"]) - gross * (1 - w)), D("0.01"))

    # ---- reader lint ----
    def test_reader_contains_v32_sections_and_passes_lint(self):
        for heading in ("### 现金口径估值", "### 三口径回本测试", "### 同业对比", "### 新资金价格阶梯", "### Action Triggers",
                        "### Pre-Mortem", "### 最小复核清单", "### 正常化桥", "### CapEx、研发与资产负债表", "年趋势", "年税后股息"):
            self.assertIn(heading, self.reader)
        self.assertEqual(lint_text(self.reader), [])

    def test_lint_fails_when_section_removed(self):
        for heading in ("### 现金口径估值", "### Pre-Mortem", "### 新资金价格阶梯", "### 最小复核清单"):
            broken = self.reader.replace(heading, "### 已删除章节")
            self.assertTrue(lint_text(broken), heading)


if __name__ == "__main__":
    unittest.main()

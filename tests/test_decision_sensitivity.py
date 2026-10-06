import unittest
from decimal import Decimal

from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_renderer_v3 import render_reader_markdown
from tests.meta_v3_spec import make_spec


class DecisionSensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = make_spec()
        cls.bundle = compile_report_v3(cls.spec)
        cls.data = cls.bundle["decision_sensitivity"]

    def test_base_irr_matches_bundle_engine(self):
        bundle_irr = Decimal(self.bundle["scenarios"]["base"]["returns"]["irr"]["irr_pct"]) / 100
        self.assertEqual(Decimal(self.data["base_irr"]), bundle_irr.quantize(Decimal("0.0001")))

    def test_break_even_values_reach_hurdle(self):
        from scripts.decision_sensitivity import _base_inputs, _irr

        inputs = _base_inputs(self.bundle)
        hurdle = Decimal(self.data["target_return"])
        for row in self.data["drivers"]:
            with self.subTest(role=row["role"]):
                shocked = dict(inputs)
                shocked[row["role"]] = Decimal(row["break_even_value"])
                self.assertLess(abs(_irr(shocked) - hurdle), Decimal("0.0003"))

    def test_shocks_move_irr_in_expected_direction(self):
        base = Decimal(self.data["base_irr"])
        for row in self.data["drivers"]:
            shocks = {item["direction"]: Decimal(item["irr"]) for item in row["shocks"]}
            with self.subTest(role=row["role"]):
                self.assertLess(shocks["down"], base)
                self.assertGreater(shocks["up"], base)

    def test_reader_shows_price_distance_and_sensitivity(self):
        reader = render_reader_markdown(self.bundle)
        self.assertIn("### 什么会改变结论", reader)
        self.assertIn("需再跌", reader)
        self.assertNotIn("这仍是当前结论最需要防守的解释", reader)
        self.assertNotIn("decision_sensitivity", reader)


if __name__ == "__main__":
    unittest.main()

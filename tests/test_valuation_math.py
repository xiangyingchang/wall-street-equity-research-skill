import unittest

from scripts.valuation_math import payback_growth, price_zones, target_return_price, total_return_irr


class ValuationMathTests(unittest.TestCase):
    def test_nominal_ttm_payback_matches_contract(self):
        self.assertAlmostEqual(payback_growth(556.71 / 26.55) * 100, 13.13, places=2)
        self.assertAlmostEqual(payback_growth(556.71 / 14.76) * 100, 23.31, places=2)

    def test_discounted_payback_matches_contract(self):
        self.assertAlmostEqual(payback_growth(556.71 / 26.55, discount_rate=0.095) * 100, 23.88, places=2)
        self.assertAlmostEqual(payback_growth(556.71 / 14.76, discount_rate=0.095) * 100, 35.03, places=2)

    def test_target_price_is_reproducible_with_dividend_treatment(self):
        self.assertAlmostEqual(
            target_return_price(22, 0.06, 18, 5, 0.095, 0.0038, dividend_mode="reinvested_yield"),
            343.08,
            places=2,
        )
        self.assertAlmostEqual(
            target_return_price(22, 0.06, 18, 5, 0.095, 0.0038, dividend_mode="none"),
            336.63,
            places=2,
        )

    def test_irr_uses_same_inputs_as_target_price(self):
        irr = total_return_irr(556.71, 29.62, 0.06, 18, 5, 0.0038)
        price = target_return_price(29.62, 0.06, 18, 5, 0.095, 0.0038)
        self.assertAlmostEqual(irr * 100, 5.49, places=2)
        self.assertAlmostEqual(price, 461.90, places=2)

    def test_price_zones_build_reference_cash_and_joint_gates(self):
        zones = price_zones(75000, [12, 15, 18], 15, 62000, 0.06, target_return_price_value=1100000)
        self.assertEqual([round(row["price"]) for row in zones["earnings_reference_prices"]], [900000, 1125000, 1350000])
        self.assertAlmostEqual(zones["cash_confirmation_price"], 1033333.33, places=2)
        self.assertAlmostEqual(zones["joint_new_money_price"], 1033333.33, places=2)
        self.assertAlmostEqual(zones["target_return_price"], 1100000, places=2)
        self.assertEqual(zones["joint_action_status"], "EXECUTABLE")

    def test_low_confidence_cash_gate_forces_review(self):
        zones = price_zones(75000, [12, 15, 18], 15, 62000, 0.06, cash_confidence="conditional")
        self.assertEqual(zones["joint_action_status"], "REVIEW_CASH_CONFIDENCE")


if __name__ == "__main__":
    unittest.main()

import unittest

from scripts.valuation_math import payback_growth, target_return_price, total_return_irr


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


if __name__ == "__main__":
    unittest.main()

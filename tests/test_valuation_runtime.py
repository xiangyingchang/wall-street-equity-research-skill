from decimal import Decimal
import unittest

from scripts.valuation_runtime import reverse_expectations, resolve_action, scenario_irr


class ValuationRuntimeTests(unittest.TestCase):
    def test_meta_base_irr_is_not_9_5_percent(self):
        result = scenario_irr(
            current_price=Decimal("549"),
            starting_eps=Decimal("22"),
            eps_cagr=Decimal("0.08"),
            exit_pe=Decimal("18"),
            years=5,
            annual_dividend_yield=Decimal("0.005"),
        )
        self.assertEqual(result["terminal_eps"], "32.3262")
        self.assertEqual(result["irr_pct"], "1.63")

    def test_eps_growth_rejects_extra_buyback(self):
        with self.assertRaisesRegex(ValueError, "already embedded"):
            scenario_irr(
                current_price=Decimal("549"),
                starting_eps=Decimal("22"),
                eps_cagr=Decimal("0.08"),
                exit_pe=Decimal("18"),
                years=5,
                share_count_cagr=Decimal("-0.02"),
            )

    def test_reverse_expectations_for_target_return(self):
        result = reverse_expectations(
            current_price=Decimal("549"),
            starting_eps=Decimal("22"),
            target_return=Decimal("0.094"),
            exit_pe=Decimal("18"),
            years=5,
        )
        self.assertEqual(result["required_terminal_eps"], "47.8203")
        self.assertEqual(result["required_eps_cagr_pct"], "16.79")

    def test_no_trigger_resolves_review(self):
        result = resolve_action(
            {
                "current_action": "Reduce",
                "rules": [
                    {"id": "hold", "action": "HOLD", "triggered": False},
                    {"id": "reduce-op", "action": "REDUCE", "triggered": False},
                    {"id": "sell", "action": "SELL", "triggered": False},
                ],
            }
        )
        self.assertEqual(result["resolved_action"], "REVIEW")
        self.assertFalse(result["reported_action_matches"])

    def test_highest_priority_trigger_wins(self):
        result = resolve_action(
            {
                "rules": [
                    {"id": "hold", "action": "HOLD", "triggered": True},
                    {"id": "reduce-op", "action": "REDUCE", "triggered": True},
                ]
            }
        )
        self.assertEqual(result["resolved_action"], "REDUCE")


if __name__ == "__main__":
    unittest.main()

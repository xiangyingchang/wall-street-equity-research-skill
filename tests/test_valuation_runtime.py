from decimal import Decimal
import unittest

from scripts.valuation_runtime import (
    evaluate_action,
    reverse_expectations,
    resolve_action,
    scenario_eps_bridge,
    scenario_irr,
)


class ValuationRuntimeTests(unittest.TestCase):
    def test_meta_eps_bridge_is_calculated_not_hand_written(self):
        result = scenario_eps_bridge(
            revenue=Decimal("2750"),
            operating_margin=Decimal("0.35"),
            other_income=Decimal("0"),
            tax_rate=Decimal("0.18"),
            diluted_shares=Decimal("25.7"),
        )
        self.assertEqual(result["operating_income"], "962.5000")
        self.assertEqual(result["net_income"], "789.2500")
        self.assertEqual(result["eps"], "30.7101")

    def test_eps_bridge_rejects_invalid_tax_rate(self):
        with self.assertRaisesRegex(ValueError, "tax_rate"):
            scenario_eps_bridge(
                revenue=Decimal("100"),
                operating_margin=Decimal("0.20"),
                other_income=Decimal("0"),
                tax_rate=Decimal("1"),
                diluted_shares=Decimal("10"),
            )

    def test_meta_base_irr_is_not_9_5_percent(self):
        result = scenario_irr(
            current_price=Decimal("549"),
            starting_eps=Decimal("22"),
            eps_cagr=Decimal("0.08"),
            exit_pe=Decimal("18"),
            years=5,
            annual_dividend_yield=Decimal("0.005"),
        )
        self.assertEqual(result["terminal_eps"], "32.3252")
        self.assertEqual(result["irr_pct"], "1.64")

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
        self.assertEqual(result["required_terminal_eps"], "47.7954")
        self.assertEqual(result["required_eps_cagr_pct"], "16.79")

    def test_fact_based_action_does_not_allow_conservative_override(self):
        result = evaluate_action(
            {
                "current_action": "Reduce",
                "facts": {
                    "FACT-TTM-OP-MARGIN": "0.381",
                    "FACT-TTM-FCF": "378.7",
                    "FACT-CURRENT-PRICE": "549",
                },
                "rules": [
                    {
                        "id": "hold-op",
                        "action": "HOLD",
                        "logic": "all",
                        "conditions": [
                            {"fact": "FACT-TTM-OP-MARGIN", "operator": ">=", "value": "0.35"},
                            {"fact": "FACT-TTM-FCF", "operator": ">", "value": "400"},
                        ],
                    },
                    {
                        "id": "reduce-op",
                        "action": "REDUCE",
                        "conditions": [
                            {"fact": "FACT-TTM-OP-MARGIN", "operator": "<", "value": "0.35"}
                        ],
                    },
                    {
                        "id": "sell",
                        "action": "SELL",
                        "conditions": [
                            {"fact": "FACT-CURRENT-PRICE", "operator": "<", "value": "100"}
                        ],
                    },
                ],
            }
        )
        self.assertEqual(result["resolved_action"], "REVIEW")
        self.assertEqual(result["triggered_rule_ids"], [])
        self.assertFalse(result["reported_action_matches"])
        reduce_rule = next(item for item in result["evaluated_rules"] if item["id"] == "reduce-op")
        self.assertFalse(reduce_rule["triggered"])
        self.assertEqual(reduce_rule["conditions"][0]["actual"], "0.381")

    def test_fact_based_action_supports_any_and_priority(self):
        result = evaluate_action(
            {
                "facts": {"PRICE": "700", "MARGIN": "0.30"},
                "rules": [
                    {
                        "id": "hold",
                        "action": "HOLD",
                        "conditions": [{"fact": "PRICE", "operator": ">", "value": "1"}],
                    },
                    {
                        "id": "reduce",
                        "action": "REDUCE",
                        "logic": "any",
                        "conditions": [
                            {"fact": "PRICE", "operator": ">", "value": "650"},
                            {"fact": "MARGIN", "operator": "<", "value": "0.35"},
                        ],
                    },
                ],
            }
        )
        self.assertEqual(result["resolved_action"], "REDUCE")
        self.assertEqual(result["triggered_rule_ids"], ["hold", "reduce"])

    def test_fact_to_fact_comparison(self):
        result = evaluate_action(
            {
                "facts": {"PRICE": "90", "BUY_PRICE": "100"},
                "rules": [
                    {
                        "id": "add",
                        "action": "ADD",
                        "conditions": [
                            {"fact": "PRICE", "operator": "<", "value_fact": "BUY_PRICE"}
                        ],
                    }
                ],
            }
        )
        self.assertEqual(result["resolved_action"], "ADD")

    def test_fact_based_action_missing_fact_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "missing fact"):
            evaluate_action(
                {
                    "facts": {"PRICE": "100"},
                    "rules": [
                        {
                            "id": "bad",
                            "action": "HOLD",
                            "conditions": [{"fact": "MISSING", "operator": ">", "value": 1}],
                        }
                    ],
                }
            )

    def test_fact_based_action_unknown_operator_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported operator"):
            evaluate_action(
                {
                    "facts": {"PRICE": "100"},
                    "rules": [
                        {
                            "id": "bad",
                            "action": "HOLD",
                            "conditions": [{"fact": "PRICE", "operator": "approximately", "value": 100}],
                        }
                    ],
                }
            )

    def test_fact_based_action_rejects_mixed_type_equality(self):
        with self.assertRaisesRegex(ValueError, "matching string or boolean types"):
            evaluate_action(
                {
                    "facts": {"STATUS": "good"},
                    "rules": [
                        {
                            "id": "bad",
                            "action": "HOLD",
                            "conditions": [{"fact": "STATUS", "operator": "==", "value": True}],
                        }
                    ],
                }
            )

    def test_legacy_no_trigger_resolves_review(self):
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

    def test_legacy_highest_priority_trigger_wins(self):
        result = resolve_action(
            {
                "rules": [
                    {"id": "hold", "action": "HOLD", "triggered": True},
                    {"id": "reduce-op", "action": "REDUCE", "triggered": True},
                ]
            }
        )
        self.assertEqual(result["resolved_action"], "REDUCE")

    def test_importing_module_does_not_change_global_decimal_precision(self):
        from decimal import getcontext

        self.assertEqual(getcontext().prec, 28)


if __name__ == "__main__":
    unittest.main()

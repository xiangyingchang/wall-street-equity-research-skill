from decimal import Decimal, getcontext
import unittest

from scripts.valuation_runtime import (
    evaluate_action,
    revenue_bridge,
    return_pair,
    reverse_expectations,
    robustness,
    scenario_eps_bridge,
    scenario_irr,
    ttm_derive,
)


class ValuationRuntimeTests(unittest.TestCase):
    def test_meta_base_irr_is_not_9_5_percent(self):
        result = scenario_irr(current_price=Decimal("549"), starting_eps=Decimal("22"), eps_cagr=Decimal("0.08"), exit_pe=Decimal("18"), years=5, annual_dividend_yield=Decimal("0.005"))
        self.assertEqual(result["terminal_eps"], "32.3252")
        self.assertEqual(result["irr_pct"], "1.64")

    def test_eps_growth_rejects_extra_buyback(self):
        with self.assertRaisesRegex(ValueError, "already embedded"):
            scenario_irr(current_price=Decimal("549"), starting_eps=Decimal("22"), eps_cagr=Decimal("0.08"), exit_pe=Decimal("18"), years=5, share_count_cagr=Decimal("-0.02"))

    def test_reverse_expectations_for_target_return(self):
        result = reverse_expectations(current_price=Decimal("549"), starting_eps=Decimal("22"), target_return=Decimal("0.094"), exit_pe=Decimal("18"), years=5)
        self.assertEqual(result["required_terminal_eps"], "47.7954")
        self.assertEqual(result["required_eps_cagr_pct"], "16.79")

    def test_eps_bridge_meta_vector(self):
        result = scenario_eps_bridge(revenue=Decimal("2750"), operating_margin=Decimal("0.35"), other_income=Decimal("0"), tax_rate=Decimal("0.18"), diluted_shares=Decimal("25.7"))
        self.assertEqual(result["eps"], "30.7101")

    def test_ttm_eps_sum(self):
        result = ttm_derive({"id": "DERIVED-TTM-EPS", "metric": "TTM EPS", "mode": "sum", "components": [
            {"id": "FACT-Q3-EPS", "period": "Q3 2025", "value": "1.05"},
            {"id": "FACT-Q4-EPS", "period": "Q4 2025", "value": "8.88"},
            {"id": "FACT-Q1-EPS", "period": "Q1 2026", "value": "10.44"},
            {"id": "FACT-Q2-EPS", "period": "Q2 2026", "value": "6.18"},
        ]})
        self.assertEqual(result["value"], "26.5500")

    def test_ttm_operating_margin_ratio(self):
        result = ttm_derive({"id": "DERIVED-TTM-OP-MARGIN", "metric": "TTM operating margin", "mode": "ratio", "numerator": [
            {"id": "N1", "period": "Q3 2025", "value": "205.35"}, {"id": "N2", "period": "Q4 2025", "value": "247.45"}, {"id": "N3", "period": "Q1 2026", "value": "228.72"}, {"id": "N4", "period": "Q2 2026", "value": "187.75"}], "denominator": [
            {"id": "D1", "period": "Q3 2025", "value": "512.42"}, {"id": "D2", "period": "Q4 2025", "value": "598.93"}, {"id": "D3", "period": "Q1 2026", "value": "563.11"}, {"id": "D4", "period": "Q2 2026", "value": "608.01"}]})
        self.assertEqual(result["value_pct"], "38.08")

    def test_revenue_bridge_recomputes_yoy(self):
        result = revenue_bridge({"scenario": "Base", "periods": [
            {"id": "REV-Q3", "period": "Q3 2026", "mode": "guide_midpoint", "low": "610", "high": "640", "source": "Meta IR"},
            {"id": "REV-Q4", "period": "Q4 2026", "mode": "qoq", "base_id": "REV-Q3", "growth": "0.09"},
            {"id": "REV-Q1", "period": "Q1 2027", "mode": "yoy", "base_id": "FACT-Q1-REV", "base_value": "563.11", "growth": "0.12"},
            {"id": "REV-Q2", "period": "Q2 2027", "mode": "yoy", "base_id": "FACT-Q2-REV", "base_value": "608.01", "growth": "0.12"}]})
        self.assertEqual(result["periods"][2]["revenue"], "630.6832")
        self.assertEqual(result["periods"][3]["revenue"], "680.9712")

    def test_return_pair_shares_dividend_assumption(self):
        result = return_pair(current_price=Decimal("549"), starting_eps=Decimal("30.7101"), eps_cagr=Decimal("0.06"), exit_pe=Decimal("18"), years=5, target_return=Decimal("0.094"), annual_dividend_yield=Decimal("0.005"))
        self.assertEqual(result["irr"]["irr_pct"], "6.54")
        self.assertEqual(result["reverse"]["required_eps_cagr_pct"], "8.90")
        self.assertEqual(result["assumptions"]["dividend"]["mode"], "yield")
        self.assertEqual(result["target_return_price"], "479.7122")

    def test_legacy_no_trigger_resolves_review(self):
        result = evaluate_action({"current_action": "Reduce", "facts": {"FACT-MARGIN": "0.381", "FACT-FCF": "378.7"}, "rules": [{"id": "reduce", "action": "REDUCE", "logic": "all", "conditions": [{"fact": "FACT-MARGIN", "operator": "<", "value": "0.35"}]}]})
        self.assertEqual(result["resolved_action"], "REVIEW")
        self.assertFalse(result["reported_action_matches"])

    def test_threshold_neutral_band_resolves_review(self):
        result = evaluate_action(self._v2_payload())
        self.assertEqual(result["resolved_action"], "REVIEW")
        self.assertEqual(result["indeterminate_rule_ids"], ["reduce-op"])
        self.assertFalse(result["reported_action_matches"])

    def test_v2_rejects_naked_threshold(self):
        payload = self._v2_payload()
        payload["rules"][0]["conditions"][0].pop("threshold")
        payload["rules"][0]["conditions"][0]["value"] = "400"
        with self.assertRaisesRegex(ValueError, "registered threshold"):
            evaluate_action(payload)

    def test_confirmation_requirement(self):
        payload = self._v2_payload()
        payload["thresholds"]["THR-FCF"]["confirmation"] = 2
        payload["values"]["DERIVED-CONSECUTIVE"] = {"value": "1", "kind": "DERIVED", "confidence": "high", "uncertainty": "0"}
        payload["rules"][0]["conditions"][0]["confirmation_value"] = "DERIVED-CONSECUTIVE"
        result = evaluate_action(payload)
        self.assertEqual(result["resolved_action"], "REVIEW")
        self.assertIn("confirmation", result["evaluated_rules"][0]["conditions"][0]["reason"])

    def test_robustness_detects_unstable_action(self):
        payload = self._v2_payload()
        payload["sensitivity_values"] = ["DERIVED-TTM-FCF"]
        result = robustness(payload, Decimal("0.05"))
        self.assertFalse(result["stable"])
        self.assertEqual(result["recommended_action"], "REVIEW")

    def test_importing_module_does_not_change_global_decimal_precision(self):
        self.assertEqual(getcontext().prec, 28)

    @staticmethod
    def _v2_payload():
        return {"current_action": "REDUCE", "values": {"DERIVED-TTM-FCF": {"value": "378.7", "kind": "DERIVED", "confidence": "medium", "uncertainty": "0.01"}}, "thresholds": {"THR-FCF": {"value": "400", "basis": "historical distribution", "lookback": "12 quarters", "confirmation": 1, "tolerance": "0.05", "minimum_confidence": "medium", "rationale": "FCF durability threshold"}}, "rules": [{"id": "reduce-op", "action": "REDUCE", "logic": "all", "conditions": [{"value_id": "DERIVED-TTM-FCF", "operator": "<", "threshold": "THR-FCF"}]}]}


if __name__ == "__main__":
    unittest.main()

import copy
import unittest
from decimal import Decimal

from scripts.decision_sensitivity import _base_inputs, _irr
from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_renderer_v3 import render_reader_markdown
from scripts.report_spec_v2 import SpecError
from tests.meta_v3_spec import make_spec

FX = Decimal("7.8")  # 1 USD = 7.8 HKD (fixture only)


def _hkd_spec(fx_unit: str = "HKD/USD", fx_value: str = "7.8") -> dict:
    spec = copy.deepcopy(make_spec())
    report = spec["report"]
    price_id = report["current_price_fact_id"]
    price = spec["facts"][price_id]
    price["value"] = str(Decimal(str(price["value"])) * FX)
    price["unit"] = "HKD/share"
    report["price_currency"] = "HKD"
    report["fx_fact_id"] = "FACT-FX-USDHKD"
    source_id = price["source_ids"][0]
    spec["facts"]["FACT-FX-USDHKD"] = {
        "value": fx_value, "unit": fx_unit, "source": "fixture fx", "tier": "Tier 1",
        "confidence": "high", "as_of": report["as_of"], "source_ids": [source_id],
    }
    # FX facts need a Tier 1 source; reuse a Tier 1 filing source from the fixture.
    tier1 = next(sid for sid, src in _sources(spec).items() if str(src["tier"]).replace("Tier ", "") == "1")
    spec["facts"]["FACT-FX-USDHKD"]["source_ids"] = [tier1]
    return spec


def _sources(spec: dict) -> dict:
    raw = spec.get("sources", {})
    if isinstance(raw, list):
        return {item["source_id"]: item for item in raw}
    return raw


class PriceCurrencyFxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_bundle = compile_report_v3(make_spec())
        cls.bundle = compile_report_v3(_hkd_spec())

    def test_irr_invariant_under_consistent_fx(self):
        base = self.base_bundle["scenarios"]["base"]["returns"]["irr"]["irr_pct"]
        fx = self.bundle["scenarios"]["base"]["returns"]["irr"]["irr_pct"]
        self.assertEqual(base, fx)

    def test_prices_scale_by_fx(self):
        base = Decimal(self.base_bundle["scenarios"]["base"]["prices"]["target_return"])
        fx = Decimal(self.bundle["scenarios"]["base"]["prices"]["target_return"])
        self.assertLess(abs(fx - base * FX), Decimal("0.01"))

    def test_inverse_fx_quote_gives_same_result(self):
        inverse = compile_report_v3(_hkd_spec("USD/HKD", str(Decimal(1) / FX)))
        self.assertEqual(
            inverse["scenarios"]["base"]["returns"]["irr"]["irr_pct"],
            self.bundle["scenarios"]["base"]["returns"]["irr"]["irr_pct"],
        )

    def test_sensitivity_uses_same_fx(self):
        inputs = _base_inputs(self.bundle)
        bundle_irr = Decimal(self.bundle["scenarios"]["base"]["returns"]["irr"]["irr_pct"]) / 100
        self.assertLess(abs(_irr(inputs) - bundle_irr), Decimal("0.0001"))
        hurdle = Decimal(self.bundle["decision_sensitivity"]["target_return"])
        for row in self.bundle["decision_sensitivity"]["drivers"]:
            with self.subTest(role=row["role"]):
                shocked = dict(inputs)
                shocked[row["role"]] = Decimal(row["break_even_value"])
                self.assertLess(abs(_irr(shocked) - hurdle), Decimal("0.0003"))

    def test_reader_quotes_listing_currency_and_discloses_fx(self):
        reader = render_reader_markdown(self.bundle)
        self.assertIn("HK$", reader)
        self.assertIn("计价口径", reader)

    def test_mismatched_currency_without_fx_fails(self):
        spec = _hkd_spec()
        del spec["report"]["fx_fact_id"]
        with self.assertRaises(SpecError):
            compile_report_v3(spec)

    def test_fx_pair_must_match_currencies(self):
        spec = _hkd_spec("HKD/EUR")
        with self.assertRaises(SpecError):
            compile_report_v3(spec)


if __name__ == "__main__":
    unittest.main()

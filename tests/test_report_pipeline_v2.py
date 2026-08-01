from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from scripts.report_pipeline_v2 import build, verify
from scripts.report_renderer_v2 import render_markdown
from scripts.report_spec_v2 import SpecError, compile_spec

FIXTURE = Path(__file__).parent / "fixtures" / "meta_v2_spec.json"


def load_spec():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class ReportPipelineV2Tests(unittest.TestCase):
    def test_meta_end_to_end_core_outputs(self):
        bundle = compile_spec(load_spec())
        self.assertEqual(bundle["derived"]["ttm"]["eps"]["value"], "26.5500")
        self.assertEqual(bundle["derived"]["ttm"]["operating_margin"]["value_pct"], "38.08")
        self.assertEqual(bundle["scenarios"]["base"]["revenue"]["forward_revenue"], "2617.9032")
        self.assertEqual(bundle["scenarios"]["bull"]["revenue"]["periods"][0]["revenue"], "640.0000")
        self.assertEqual(bundle["scenarios"]["base"]["eps_bridge"]["eps"], "29.2350")
        self.assertEqual(bundle["decision"]["new_money_action"], "DO_NOT_BUY")
        self.assertEqual(bundle["decision"]["existing_position_action"], "REDUCE")
        self.assertTrue(bundle["decision"]["robustness"]["stable"])

    def test_markdown_has_one_source_and_no_legacy_tables(self):
        markdown = render_markdown(compile_spec(load_spec()))
        self.assertIn("report-spec-v2", markdown)
        self.assertIn("New money action", markdown)
        self.assertIn("Existing position action", markdown)
        self.assertNotIn("Legacy Compatibility", markdown)
        self.assertNotIn("Legacy Checker Compatibility", markdown)
        self.assertEqual(markdown.count("Base buy price"), 1)

    def test_build_and_verify_detect_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "spec.json"
            report_path = root / "report.md"
            spec_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            result = build(spec_path, report_path)
            self.assertEqual(result["checks"]["spec_schema"], "PASS")
            self.assertEqual(verify(spec_path, report_path)["status"], "PASS")
            report_path.write_text(report_path.read_text(encoding="utf-8").replace("$456.67", "$999.99", 1), encoding="utf-8")
            with self.assertRaises(SpecError):
                verify(spec_path, report_path)

    def test_cross_scenario_assumption_reference_fails(self):
        spec = load_spec()
        spec["scenarios"]["bear"]["assumptions"]["operating_margin"] = "ASM-BASE-MARGIN"
        with self.assertRaisesRegex(SpecError, "bear cannot reference base assumption"):
            compile_spec(spec)

    def test_missing_valuation_reduce_policy_fails(self):
        spec = load_spec()
        del spec["decision_policy"]["valuation"]["reduce_gap"]
        with self.assertRaisesRegex(SpecError, "valuation policy missing reduce_gap"):
            compile_spec(spec)

    def test_hidden_uncertainty_cannot_be_added_in_narrative(self):
        spec = load_spec()
        spec["decision_policy"]["operating"]["uncertainty"] = "0"
        spec["narrative"]["final_verdict"] = "Use an extra 1% uncertainty not declared in policy."
        bundle = compile_spec(spec)
        self.assertEqual(bundle["decision"]["operating"]["uncertainty"], "0.0000")

    def test_price_zones_match_new_money_actions(self):
        bundle = compile_spec(load_spec())
        self.assertEqual(bundle["price_zones"][0]["action"], "BUY")
        self.assertEqual(bundle["price_zones"][1]["action"], "WATCH")
        self.assertEqual(bundle["price_zones"][2]["action"], "DO_NOT_BUY")
        self.assertEqual(bundle["price_zones"][0]["max"], bundle["scenarios"]["base"]["prices"]["buy"])

    def test_payback_is_runtime_derived_and_monotonic(self):
        bundle = compile_spec(load_spec())
        values = bundle["derived"]["payback_required_growth"]
        self.assertGreater(float(values["0.094"]), float(values["0.047"]))
        self.assertGreater(float(values["0.10"]), float(values["0.08"]))

    def test_same_spec_is_deterministic(self):
        a = compile_spec(load_spec())
        b = compile_spec(load_spec())
        self.assertEqual(a["bundle_hash"], b["bundle_hash"])
        self.assertEqual(render_markdown(a), render_markdown(b))


if __name__ == "__main__":
    unittest.main()

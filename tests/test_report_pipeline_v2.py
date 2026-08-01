from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.report_compiler_v21 import compile_report_v21
from scripts.report_pipeline_v2 import artifact_paths, build, verify
from scripts.report_renderer_readable_v212 import render_audit_markdown, render_reader_markdown
from scripts.report_spec_v2 import SpecError
from tests.meta_v21_spec import make_spec

FIXTURES = Path(__file__).parent / "fixtures"
EXPECTED_FIXTURE = FIXTURES / "meta_v2_expected.json"


def load_expected():
    return json.loads(EXPECTED_FIXTURE.read_text(encoding="utf-8"))


class ReportPipelineV21Tests(unittest.TestCase):
    def test_meta_end_to_end_golden_outputs(self):
        bundle = compile_report_v21(make_spec())
        expected = load_expected()
        actual = {
            "ttm_eps": bundle["derived"]["ttm"]["eps"]["value"],
            "ttm_operating_margin_pct": bundle["derived"]["ttm"]["operating_margin"]["value_pct"],
            "ttm_fcf": bundle["derived"]["ttm"]["fcf"]["value"],
            "base_forward_revenue": bundle["scenarios"]["base"]["revenue"]["forward_revenue"],
            "base_eps": bundle["scenarios"]["base"]["eps_bridge"]["eps"],
            "base_irr_pct": bundle["scenarios"]["base"]["returns"]["irr"]["irr_pct"],
            "base_target_return_price": bundle["scenarios"]["base"]["prices"]["target_return"],
            "base_buy_price": bundle["scenarios"]["base"]["prices"]["buy"],
            "bull_q3_revenue": bundle["scenarios"]["bull"]["revenue"]["periods"][0]["revenue"],
            "new_money_action": bundle["decision"]["new_money_action"],
            "existing_position_action": bundle["decision"]["existing_position_action"],
            "robustness_stable": bundle["decision"]["robustness"]["stable"],
        }
        self.assertEqual(actual, expected)

    def test_reader_report_is_complete_and_readable(self):
        markdown = render_reader_markdown(compile_report_v21(make_spec()))
        for number in range(1, 10):
            self.assertIn(f"## {number}.", markdown)
        for token in ("Base 5年 IRR", "最低目标回报", "目标回报价格", "TTM EPS", "TTM 经营利润率", "TTM FCF"):
            self.assertIn(token, markdown)
        for forbidden in ("## Source Registry", "## Evidence Ledger", "## Claim-Evidence Matrix", "FACT-", "BUNDLE:", "[supports]", "Spec hash", "Bundle hash"):
            self.assertNotIn(forbidden, markdown)
        self.assertNotIn("Legacy Compatibility", markdown)
        self.assertNotIn("未提供叙事内容", markdown)
        self.assertGreaterEqual(len(markdown.splitlines()), 120)
        self.assertLessEqual(len(markdown.splitlines()), 300)

    def test_audit_appendix_keeps_full_traceability(self):
        audit = render_audit_markdown(compile_report_v21(make_spec()))
        for token in ("### Build Manifest", "## Source Registry", "## Evidence Ledger", "## Quarterly TTM Bridge", "## Scenario Assumptions and Valuation", "## Decision Policy Evaluation", "## Claim-Evidence Matrix", "## Verification"):
            self.assertIn(token, audit)
        self.assertIn("FACT-", audit)
        self.assertIn("BUNDLE:", audit)
        self.assertNotIn("Legacy Compatibility", audit)

    def _built_files(self, root: Path):
        spec_path = root / "spec.json"
        report_path = root / "report.md"
        spec_path.write_text(json.dumps(make_spec(), ensure_ascii=False), encoding="utf-8")
        build(spec_path, report_path)
        bundle_path, verification_path, audit_path = artifact_paths(report_path)
        return spec_path, report_path, audit_path, bundle_path, verification_path

    def test_build_and_verify_detect_reader_markdown_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            spec_path, report_path, _, _, _ = self._built_files(Path(temp))
            self.assertEqual(verify(spec_path, report_path)["status"], "PASS")
            report_path.write_text(report_path.read_text(encoding="utf-8").replace("$456.67", "$999.99", 1), encoding="utf-8")
            with self.assertRaises(SpecError):
                verify(spec_path, report_path)

    def test_verify_detects_audit_markdown_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            spec_path, report_path, audit_path, _, _ = self._built_files(Path(temp))
            audit_path.write_text(audit_path.read_text(encoding="utf-8").replace("PASS", "FAIL", 1), encoding="utf-8")
            with self.assertRaises(SpecError):
                verify(spec_path, report_path)

    def test_verify_detects_bundle_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            spec_path, report_path, _, bundle_path, _ = self._built_files(Path(temp))
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle["decision"]["existing_position_action"] = "HOLD"
            bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
            with self.assertRaises(SpecError):
                verify(spec_path, report_path)

    def test_verify_detects_verification_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            spec_path, report_path, _, _, verification_path = self._built_files(Path(temp))
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
            verification["checks"]["reader_layer_clean"] = "FAIL"
            verification_path.write_text(json.dumps(verification), encoding="utf-8")
            with self.assertRaises(SpecError):
                verify(spec_path, report_path)

    def test_verify_detects_spec_change_without_rebuild(self):
        with tempfile.TemporaryDirectory() as temp:
            spec_path, report_path, _, _, _ = self._built_files(Path(temp))
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["facts"]["FACT-CURRENT-PRICE"]["value"] = "500"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(SpecError):
                verify(spec_path, report_path)

    def test_missing_module_four_fails(self):
        spec = make_spec()
        del spec["research"]["valuation"]
        with self.assertRaisesRegex(SpecError, "research missing modules"):
            compile_report_v21(spec)

    def test_thin_overview_fails(self):
        spec = make_spec()
        spec["research"]["overview"]["key_forces"] = spec["research"]["overview"]["key_forces"][:2]
        with self.assertRaisesRegex(SpecError, "at least three key forces"):
            compile_report_v21(spec)

    def test_missing_claim_evidence_fails(self):
        spec = make_spec()
        spec["research"]["overview"]["thesis"]["evidence_refs"] = []
        with self.assertRaisesRegex(SpecError, "requires evidence_refs"):
            compile_report_v21(spec)

    def test_undefined_source_fails(self):
        spec = make_spec()
        spec["facts"]["FACT-Q2-26-FCF"]["source_ids"] = ["SRC-MISSING"]
        with self.assertRaisesRegex(SpecError, "undefined source"):
            compile_report_v21(spec)

    def test_unbound_numeric_narrative_fails(self):
        spec = make_spec()
        spec["research"]["overview"]["thesis"]["text"] = "当前价格明显偏高，但回报不足。$549"
        with self.assertRaisesRegex(SpecError, "unbound numeric content"):
            compile_report_v21(spec)

    def test_cross_scenario_assumption_reference_fails(self):
        spec = make_spec()
        spec["scenarios"]["bear"]["assumptions"]["operating_margin"] = "ASM-BASE-MARGIN"
        with self.assertRaisesRegex(SpecError, "bear cannot reference base assumption"):
            compile_report_v21(spec)

    def test_missing_valuation_reduce_policy_fails(self):
        spec = make_spec()
        del spec["decision_policy"]["valuation"]["reduce_gap"]
        with self.assertRaisesRegex(SpecError, "valuation policy missing reduce_gap"):
            compile_report_v21(spec)

    def test_guide_high_is_not_midpoint(self):
        bundle = compile_report_v21(make_spec())
        self.assertEqual(bundle["scenarios"]["base"]["revenue"]["periods"][0]["revenue"], "625.0000")
        self.assertEqual(bundle["scenarios"]["bull"]["revenue"]["periods"][0]["revenue"], "640.0000")

    def test_price_zones_match_new_money_actions(self):
        bundle = compile_report_v21(make_spec())
        self.assertEqual(bundle["price_zones"][0]["action"], "BUY")
        self.assertEqual(bundle["price_zones"][1]["action"], "WATCH")
        self.assertEqual(bundle["price_zones"][2]["action"], "DO_NOT_BUY")
        self.assertEqual(bundle["price_zones"][0]["max"], bundle["scenarios"]["base"]["prices"]["buy"])

    def test_payback_is_runtime_derived_and_monotonic(self):
        bundle = compile_report_v21(make_spec())
        values = bundle["derived"]["payback_required_growth"]
        self.assertGreater(float(values["0.094"]), float(values["0.047"]))
        self.assertGreater(float(values["0.10"]), float(values["0.08"]))

    def test_same_spec_is_deterministic(self):
        spec = make_spec()
        a = compile_report_v21(spec)
        b = compile_report_v21(deepcopy(spec))
        self.assertEqual(a["bundle_hash"], b["bundle_hash"])
        self.assertEqual(render_reader_markdown(a), render_reader_markdown(b))
        self.assertEqual(render_audit_markdown(a), render_audit_markdown(b))


if __name__ == "__main__":
    unittest.main()

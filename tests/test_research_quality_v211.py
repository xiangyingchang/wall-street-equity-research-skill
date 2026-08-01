from __future__ import annotations

from copy import deepcopy
import unittest

from scripts.report_compiler_v21 import compile_report_v21
from scripts.report_renderer_readable_v212 import render_audit_markdown, render_reader_markdown
from scripts.report_spec_v2 import SpecError
from tests.meta_v21_spec import make_spec


class ResearchQualityV211Tests(unittest.TestCase):
    def test_value_refs_render_bound_numbers(self):
        bundle = compile_report_v21(make_spec())
        markdown = render_reader_markdown(bundle)
        self.assertIn("Base IRR", markdown)
        self.assertIn("5.51%", markdown)
        self.assertIn("9.40%", markdown)
        self.assertIn("$456.67", markdown)
        self.assertGreaterEqual(bundle["research_quality"]["checks"]["value_binding"]["bound_values"], 3)

    def test_missing_value_ref_fails(self):
        spec = make_spec()
        claim = spec["research"]["valuation"]["reverse_expectations"]
        del claim["value_refs"]["target_return"]
        with self.assertRaisesRegex(SpecError, "placeholders and value_refs must match"):
            compile_report_v21(spec)

    def test_invalid_json_pointer_fails(self):
        spec = make_spec()
        spec["research"]["valuation"]["reverse_expectations"]["value_refs"]["base_irr"]["path"] = "decision.valuation.base_irr"
        with self.assertRaisesRegex(SpecError, "JSON Pointer"):
            compile_report_v21(spec)

    def test_json_pointer_supports_decimal_key(self):
        spec = make_spec()
        item = spec["research"]["final_verdict"]["payback"]
        item.pop("text", None)
        item["text_template"] = "目标回报口径下的回本增长要求为 {growth}。"
        item["value_refs"] = {"growth": {"path": "/derived/payback_required_growth/0.094", "format": "percent"}}
        bundle = compile_report_v21(spec)
        self.assertIn("%", bundle["research"]["final_verdict"]["payback"]["text"])

    def test_claim_without_supporting_role_fails(self):
        spec = make_spec()
        spec["research"]["overview"]["thesis"]["evidence_refs"] = [
            {"ref": "SRC-META-Q2-2026", "role": "context"}
        ]
        with self.assertRaisesRegex(SpecError, "requires supporting evidence"):
            compile_report_v21(spec)

    def test_invalid_evidence_role_fails(self):
        spec = make_spec()
        spec["research"]["overview"]["thesis"]["evidence_refs"][0]["role"] = "proves"
        with self.assertRaisesRegex(SpecError, "invalid evidence role"):
            compile_report_v21(spec)

    def test_invalid_risk_confidence_fails(self):
        spec = make_spec()
        spec["research"]["risks"]["items"][0]["confidence"] = "very-high"
        with self.assertRaisesRegex(SpecError, "invalid confidence"):
            compile_report_v21(spec)

    def test_duplicate_risk_rank_fails(self):
        spec = make_spec()
        spec["research"]["risks"]["items"][1]["rank"] = 1
        with self.assertRaisesRegex(SpecError, "unique and consecutive"):
            compile_report_v21(spec)

    def test_source_scope_mismatch_fails(self):
        spec = make_spec()
        spec["sources"]["SRC-META-Q2-2026"]["scope"] = ["users"]
        with self.assertRaisesRegex(SpecError, "source scope does not cover"):
            compile_report_v21(spec)

    def test_research_quality_is_computed(self):
        bundle = compile_report_v21(make_spec())
        quality = bundle["research_quality"]
        self.assertEqual(quality["status"], "PASS")
        self.assertEqual(quality["checks"]["modules_complete"]["count"], 9)
        self.assertGreater(quality["checks"]["evidence_closure"]["supporting_refs"], 0)
        self.assertGreater(quality["checks"]["source_registry"]["sources"], 0)

    def test_markdown_table_escaping_is_preserved_in_audit(self):
        spec = make_spec()
        spec["sources"]["SRC-INDEX"]["title"] = "Index | Reference\nFactsheet"
        markdown = render_audit_markdown(compile_report_v21(spec))
        self.assertIn("Index \\| Reference<br>Factsheet", markdown)

    def test_reader_hides_internal_evidence_ids(self):
        markdown = render_reader_markdown(compile_report_v21(make_spec()))
        self.assertNotIn("FACT-", markdown)
        self.assertNotIn("BUNDLE:", markdown)
        self.assertNotIn("[supports]", markdown)
        self.assertIn("主要依据：", markdown)

    def test_same_input_remains_deterministic(self):
        spec = make_spec()
        a = compile_report_v21(spec)
        b = compile_report_v21(deepcopy(spec))
        self.assertEqual(a["bundle_hash"], b["bundle_hash"])
        self.assertEqual(render_reader_markdown(a), render_reader_markdown(b))
        self.assertEqual(render_audit_markdown(a), render_audit_markdown(b))


if __name__ == "__main__":
    unittest.main()

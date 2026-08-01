from __future__ import annotations

from copy import deepcopy
import tempfile
from pathlib import Path
import unittest

from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_pipeline_v3 import build, verify
from scripts.report_spec_v2 import SpecError
from tests.meta_v3_spec import make_spec, write_spec


class ResearchGraphV3Tests(unittest.TestCase):
    def test_meta_graph_compiles(self):
        bundle = compile_report_v3(make_spec())
        quality = bundle["research_graph_quality"]
        self.assertEqual(quality["status"], "PASS")
        self.assertEqual(quality["themes"], 3)
        self.assertGreaterEqual(quality["observations"], 6)
        self.assertEqual(quality["bull_arguments"], 3)
        self.assertEqual(quality["bear_arguments"], 3)
        self.assertGreaterEqual(quality["high_importance_drivers"], 1)

    def test_reader_and_audit_include_v3_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "meta.spec.json"
            report_path = root / "meta.md"
            write_spec(spec_path)
            build(spec_path, report_path)
            result = verify(spec_path, report_path)
            self.assertEqual(result["status"], "PASS")
            reader = report_path.read_text(encoding="utf-8")
            audit = report_path.with_suffix(".audit.md").read_text(encoding="utf-8")
            self.assertIn("## 1. 投资叙事与核心矛盾", reader)
            self.assertIn("### Bull vs Bear 投资辩论", reader)
            self.assertIn("### 哪些假设真正决定估值", reader)
            self.assertIn("**最强反方：**", reader)
            self.assertNotIn("THEME-CAPITAL-RETURNS", reader)
            self.assertIn("## Research Graph v3", audit)
            self.assertIn("THEME-CAPITAL-RETURNS", audit)
            self.assertIn("ARG-BULL-AD-EFFICIENCY", audit)
            self.assertIn("DRV-OPERATING-MARGIN", audit)

    def test_missing_counter_evidence_fails(self):
        spec = make_spec()
        spec["research_graph"]["themes"][0]["challenge"]["evidence_refs"] = [
            {"ref": "FACT-Q2-26-FCF", "role": "supports"}
        ]
        with self.assertRaisesRegex(SpecError, "challenge requires counter_evidence"):
            compile_report_v3(spec)

    def test_resolution_must_reconcile_both_sides(self):
        spec = make_spec()
        spec["research_graph"]["themes"][0]["resolution"]["evidence_refs"] = [
            {"ref": "FACT-Q2-26-FCF", "role": "supports"}
        ]
        with self.assertRaisesRegex(SpecError, "resolution must reconcile"):
            compile_report_v3(spec)

    def test_debate_requires_three_arguments_each(self):
        spec = make_spec()
        spec["research_graph"]["debate"]["bull"] = spec["research_graph"]["debate"]["bull"][:2]
        with self.assertRaisesRegex(SpecError, "at least three arguments"):
            compile_report_v3(spec)

    def test_adjudication_cannot_reference_unknown_argument(self):
        spec = make_spec()
        spec["research_graph"]["debate"]["adjudication"]["accepted_argument_ids"].append("ARG-UNKNOWN")
        with self.assertRaisesRegex(SpecError, "undefined argument IDs"):
            compile_report_v3(spec)

    def test_sensitivity_requires_high_importance_driver(self):
        spec = make_spec()
        for item in spec["research_graph"]["sensitivity"]["drivers"]:
            item["importance"] = "medium"
        with self.assertRaisesRegex(SpecError, "high-importance driver"):
            compile_report_v3(spec)

    def test_graph_tampering_fails_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "meta.spec.json"
            report_path = root / "meta.md"
            write_spec(spec_path)
            build(spec_path, report_path)
            audit_path = report_path.with_suffix(".audit.md")
            audit_path.write_text(audit_path.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")
            with self.assertRaises(SpecError):
                verify(spec_path, report_path)

    def test_v3_schema_is_required(self):
        spec = make_spec()
        spec["schema_version"] = "report-spec-v2.1.1"
        with self.assertRaisesRegex(SpecError, "report-spec-v3.0"):
            compile_report_v3(spec)


if __name__ == "__main__":
    unittest.main()

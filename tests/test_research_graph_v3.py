from __future__ import annotations

from copy import deepcopy
import json
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
            self.assertIn("TTM FCF 为 $378.70亿", reader)
            self.assertIn("| Base | $2,617.90亿 | $29.23 |", reader)
            for token in ("THEME-", "OBS-", "ARG-", "DRV-", "Source Registry", "Evidence Ledger", "Claim-Evidence Matrix", "hash"):
                self.assertNotIn(token, reader)
            self.assertNotIn("。；", reader)
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

    def test_theme_shape_and_module_coverage_are_enforced(self):
        spec = make_spec()
        spec["research_graph"]["themes"] = spec["research_graph"]["themes"][:2]
        with self.assertRaisesRegex(SpecError, "3-5 themes"):
            compile_report_v3(spec)

        spec = make_spec()
        spec["research_graph"]["themes"][0]["observations"] = spec["research_graph"]["themes"][0]["observations"][:1]
        with self.assertRaisesRegex(SpecError, "at least two observations"):
            compile_report_v3(spec)

        spec = make_spec()
        for theme in spec["research_graph"]["themes"]:
            theme["module_links"] = [x for x in theme["module_links"] if x != "positioning"]
        with self.assertRaisesRegex(SpecError, "do not cover modules: positioning"):
            compile_report_v3(spec)

    def test_decision_impact_requires_bundle_evidence(self):
        spec = make_spec()
        spec["research_graph"]["themes"][0]["decision_impact"]["evidence_refs"] = [
            {"ref": "FACT-Q2-26-FCF", "role": "supports"}
        ]
        with self.assertRaisesRegex(SpecError, "requires Bundle evidence"):
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

    def test_argument_ids_are_global_and_adjudication_sets_are_disjoint(self):
        spec = make_spec()
        spec["research_graph"]["debate"]["bear"][0]["argument_id"] = spec["research_graph"]["debate"]["bull"][0]["argument_id"]
        with self.assertRaisesRegex(SpecError, "duplicate or invalid argument ID"):
            compile_report_v3(spec)

        spec = make_spec()
        accepted = spec["research_graph"]["debate"]["adjudication"]["accepted_argument_ids"]
        spec["research_graph"]["debate"]["adjudication"]["discounted_argument_ids"].append(accepted[0])
        with self.assertRaisesRegex(SpecError, "non-empty and disjoint"):
            compile_report_v3(spec)

    def test_auto_discounted_is_always_disclosed_in_audit(self):
        spec = make_spec()
        arguments = [
            item["argument_id"]
            for side in ("bull", "bear")
            for item in spec["research_graph"]["debate"][side]
        ]
        adjudication = spec["research_graph"]["debate"]["adjudication"]
        adjudication["accepted_argument_ids"] = [arguments[0], arguments[3]]
        adjudication["discounted_argument_ids"] = [item for item in arguments if item not in adjudication["accepted_argument_ids"]]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "meta.spec.json"
            report_path = root / "meta.md"
            write_spec(spec_path, spec)
            build(spec_path, report_path)
            audit = report_path.with_suffix(".audit.md").read_text(encoding="utf-8")
            self.assertIn("Auto-discounted: none", audit)

    def test_sensitivity_requires_high_importance_driver(self):
        spec = make_spec()
        for item in spec["research_graph"]["sensitivity"]["drivers"]:
            item["importance"] = "medium"
        with self.assertRaisesRegex(SpecError, "high-importance driver"):
            compile_report_v3(spec)

    def test_sensitivity_path_must_be_exact_and_known(self):
        spec = make_spec()
        spec["research_graph"]["sensitivity"]["drivers"][0]["base_assumption_path"] = "/assumptions/EXTRA/ASM-BASE-CAGR/value"
        with self.assertRaisesRegex(SpecError, "must use /assumptions/<ASM-ID>/value or /assumptions/scenario/<ASM-ID>/value"):
            compile_report_v3(spec)

        spec = make_spec()
        spec["research_graph"]["sensitivity"]["drivers"][0]["base_assumption_path"] = "/assumptions/ASM-UNKNOWN/value"
        with self.assertRaisesRegex(SpecError, "undefined assumption"):
            compile_report_v3(spec)

    def test_reader_rejects_v3_internal_id_prefixes(self):
        spec = make_spec()
        spec["research_graph"]["themes"][0]["title"] = "Meta THEME-LEAK internal marker"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "meta.spec.json"
            report_path = root / "meta.md"
            write_spec(spec_path, spec)
            with self.assertRaisesRegex(SpecError, "reader report contains audit token: THEME-"):
                build(spec_path, report_path)

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

    def test_all_v3_artifact_and_spec_tampering_fails(self):
        for target in ("reader", "audit", "bundle", "verification", "spec"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                spec_path = root / "meta.spec.json"
                report_path = root / "meta.md"
                write_spec(spec_path)
                build(spec_path, report_path)
                if target == "reader":
                    report_path.write_text(report_path.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")
                elif target == "audit":
                    audit_path = report_path.with_suffix(".audit.md")
                    audit_path.write_text(audit_path.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")
                elif target == "bundle":
                    path = report_path.with_suffix(".md.bundle.json")
                    value = json.loads(path.read_text(encoding="utf-8"))
                    value["compiler_version"] = "tampered"
                    path.write_text(json.dumps(value), encoding="utf-8")
                elif target == "verification":
                    path = report_path.with_suffix(".md.verification.json")
                    value = json.loads(path.read_text(encoding="utf-8"))
                    value["checks"]["research_graph"] = "FAIL"
                    path.write_text(json.dumps(value), encoding="utf-8")
                else:
                    value = json.loads(spec_path.read_text(encoding="utf-8"))
                    value["report"]["company"] = "Tampered Meta"
                    spec_path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(SpecError):
                    verify(spec_path, report_path)

    def test_graph_audit_table_escaping(self):
        spec = make_spec()
        spec["research_graph"]["themes"][0]["observations"][0]["text"] = "管道|符与\n换行仍必须保持在同一表格单元格。"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "meta.spec.json"
            report_path = root / "meta.md"
            write_spec(spec_path, spec)
            build(spec_path, report_path)
            audit = report_path.with_suffix(".audit.md").read_text(encoding="utf-8")
            self.assertIn("管道\\|符与<br>换行仍必须保持在同一表格单元格。", audit)

    def test_v3_schema_is_required(self):
        spec = make_spec()
        spec["schema_version"] = "report-spec-v2.1.1"
        with self.assertRaisesRegex(SpecError, "report-spec-v3.0"):
            compile_report_v3(spec)


if __name__ == "__main__":
    unittest.main()

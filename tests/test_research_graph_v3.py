from __future__ import annotations

from copy import deepcopy
import json
import tempfile
from pathlib import Path
import unittest

from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_lint import lint_text
from scripts.report_pipeline_v3 import _calculation_check, build, verify
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
        self.assertEqual(bundle["schema_version"], "report-bundle-v3.1")
        self.assertEqual(bundle["decision"]["existing_position_candidate_action"], "REDUCE")
        self.assertEqual(bundle["decision"]["existing_position_action"], "REVIEW")
        self.assertEqual(bundle["prior_report_context"]["previous_base_irr_reported"], "0.095")
        self.assertEqual(bundle["prior_report_context"]["previous_base_irr_recalculated"], "0.0164")

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
            self.assertIn("## 1. 决定回报的投资主线", reader)
            self.assertIn("### 最强正反证据与裁决", reader)
            self.assertIn("### 真正决定估值的变量", reader)
            self.assertIn("### 三条原投资原则", reader)
            self.assertIn("### Base 情景关键假设", reader)
            self.assertIn("### 与上次报告相比", reader)
            self.assertIn("报告写为 9.50%；运行时复算为 1.64%", reader)
            self.assertIn("| Base IRR |", reader)
            self.assertEqual(reader.count("### Action Matrix（唯一执行口径）"), 1)
            self.assertIn("研究层给出的存量候选动作是“减仓”", reader)
            self.assertIn("唯一可执行动作是“复核”", reader)
            self.assertIn("](https://", reader)
            self.assertIn("TTM FCF 为 $378.70亿", reader)
            self.assertIn("| Base | $2,617.90亿 | $29.23 |", reader)
            for token in (
                "THEME-", "OBS-", "ARG-", "DRV-", "Source Registry", "Evidence Ledger", "Claim-Evidence Matrix", "hash",
                "**核心问题：**", "**发生了什么：**", "**基础判断：**", "**最强反方：**",
                "**综合裁决：**", "**对决策的影响：**", "**什么会推翻判断：**",
            ):
                self.assertNotIn(token, reader)
            self.assertNotIn("。；", reader)
            self.assertIn("## Research Graph v3.1", audit)
            self.assertIn("THEME-CAPITAL-RETURNS", audit)
            self.assertIn("ARG-BULL-AD-EFFICIENCY", audit)
            self.assertIn("DRV-OPERATING-MARGIN", audit)
            self.assertEqual(lint_text(reader), [])

    def test_missing_counter_evidence_fails(self):
        spec = make_spec()
        spec["research_graph"]["themes"][0]["challenge"]["evidence_refs"] = [
            {"ref": "FACT-Q2-26-FCF", "role": "supports"}
        ]
        with self.assertRaisesRegex(SpecError, "challenge requires counter_evidence"):
            compile_report_v3(spec)

    def test_theme_shape_is_dynamic_and_decision_chain_is_enforced(self):
        spec = make_spec()
        spec["research_graph"]["themes"] = spec["research_graph"]["themes"][:2]
        spec["research_graph"]["themes"][1]["module_links"].append("final_verdict")
        bundle = compile_report_v3(spec)
        self.assertEqual(bundle["research_graph_quality"]["themes"], 2)

        spec = make_spec()
        spec["research_graph"]["themes"][0]["observations"] = spec["research_graph"]["themes"][0]["observations"][:1]
        bundle = compile_report_v3(spec)
        self.assertEqual(bundle["research_graph_quality"]["observations"], 5)

        spec = make_spec()
        spec["research_graph"]["themes"] = spec["research_graph"]["themes"][:1]
        with self.assertRaisesRegex(SpecError, "2-6 material themes"):
            compile_report_v3(spec)

        spec = make_spec()
        for theme in spec["research_graph"]["themes"]:
            theme["module_links"] = [x for x in theme["module_links"] if x != "positioning"]
        with self.assertRaisesRegex(SpecError, "do not cover decision chain: positioning"):
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

    def test_debate_cardinality_is_dynamic_but_requires_both_sides(self):
        spec = make_spec()
        removed = spec["research_graph"]["debate"]["bull"][2]["argument_id"]
        spec["research_graph"]["debate"]["bull"] = spec["research_graph"]["debate"]["bull"][:2]
        spec["research_graph"]["debate"]["adjudication"]["discounted_argument_ids"].remove(removed)
        bundle = compile_report_v3(spec)
        self.assertEqual(bundle["research_graph_quality"]["bull_arguments"], 2)

        spec = make_spec()
        spec["research_graph"]["debate"]["bull"] = spec["research_graph"]["debate"]["bull"][:1]
        with self.assertRaisesRegex(SpecError, "2-6 material arguments"):
            compile_report_v3(spec)

    def test_source_url_and_placeholder_sources_fail_closed(self):
        spec = make_spec()
        del spec["sources"]["SRC-META-Q2-2026"]["url"]
        with self.assertRaisesRegex(SpecError, "missing url"):
            compile_report_v3(spec)

        spec = make_spec()
        spec["sources"]["SRC-INDEX"]["publisher"] = "Index provider"
        with self.assertRaisesRegex(SpecError, "generic placeholder publisher"):
            compile_report_v3(spec)

        spec = make_spec()
        spec["sources"]["SRC-INDEX"]["url"] = "http://example.com/index"
        with self.assertRaisesRegex(SpecError, "valid HTTPS url"):
            compile_report_v3(spec)

        spec = make_spec()
        spec["sources"]["SRC-INDEX"]["date"] = "2026-08-01"
        with self.assertRaisesRegex(SpecError, "later than report.as_of"):
            compile_report_v3(spec)

        spec = make_spec()
        del spec["report"]["tax_identity"]
        with self.assertRaisesRegex(SpecError, "missing tax_identity"):
            compile_report_v3(spec)

    def test_prior_report_delta_is_explicit_and_recalculated(self):
        spec = make_spec()
        spec["prior_report_context"]["previous_base_irr_recalculated"] = "0.095"
        with self.assertRaisesRegex(SpecError, "mismatches runtime"):
            compile_report_v3(spec)

        spec = make_spec()
        del spec["prior_report_context"]["metric_delta"]
        with self.assertRaisesRegex(SpecError, "missing metric_delta"):
            compile_report_v3(spec)

        spec = make_spec()
        spec["prior_report_context"] = {
            "status": "not_available",
            "reason": "这是首次覆盖该公司，股票目录中没有可比较的历史报告。",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "first.spec.json"
            report_path = root / "first.md"
            write_spec(spec_path, spec)
            build(spec_path, report_path)
            reader = report_path.read_text(encoding="utf-8")
            self.assertIn("未找到可比的上一份报告", reader)
            self.assertEqual(lint_text(reader), [])

    def test_company_specific_operating_metric_is_not_hardcoded_to_fcf(self):
        spec = make_spec()
        spec["decision_policy"]["operating"]["metrics"] = [{
            "metric_id": "OP-TTM-MARGIN",
            "label": "TTM 经营利润率",
            "value_ref": "BUNDLE:/derived/ttm/operating_margin/value",
            "unit": "ratio",
            "direction": "higher_is_better",
            "hold_threshold": "0.37",
            "reduce_threshold": "0.30",
            "tolerance": "0.01",
            "uncertainty": "0.005",
            "confirmation_periods": 1,
        }]
        bundle = compile_report_v3(spec)
        metric = bundle["decision"]["operating"]["metrics"][0]
        self.assertEqual(metric["metric_id"], "OP-TTM-MARGIN")
        self.assertEqual(metric["value"], "0.3808")
        self.assertEqual(metric["status"], "hold")
        self.assertNotIn("ttm_fcf", bundle["decision"]["operating"])

        spec = make_spec()
        spec["decision_policy"]["operating"]["metrics"][0]["unit"] = "CNY bn/10"
        with self.assertRaisesRegex(SpecError, "mismatches referenced value unit"):
            compile_report_v3(spec)

        spec = make_spec()
        spec["decision_policy"]["operating"]["metrics"][0]["confirmation_periods"] = "1.5"
        with self.assertRaisesRegex(SpecError, "positive integer"):
            compile_report_v3(spec)

        spec = make_spec()
        spec["decision_policy"]["operating"]["metrics"] = [{
            "metric_id": "OP-CAPEX-DURATION",
            "label": "连续高资本开支季度数",
            "value_ref": "FACT-CONSECUTIVE-CAPEX-Q",
            "unit": "quarters",
            "direction": "lower_is_better",
            "hold_threshold": "2",
            "reduce_threshold": "4",
            "tolerance": "0",
            "uncertainty": "0",
            "confirmation_periods": 1,
        }]
        lower_is_better = compile_report_v3(spec)
        self.assertEqual(lower_is_better["decision"]["operating"]["metrics"][0]["status"], "hold")

        spec = make_spec()
        metric = spec["decision_policy"]["operating"]["metrics"][0]
        metric.update({
            "hold_threshold": "450",
            "reduce_threshold": "400",
            "tolerance": "0",
            "uncertainty": "0",
            "confirmation_periods": 2,
            "confirmation_ref": "FACT-CONSECUTIVE-CAPEX-Q",
        })
        confirmation_gated = compile_report_v3(spec)
        self.assertEqual(confirmation_gated["decision"]["operating"]["metrics"][0]["status"], "review")
        self.assertEqual(confirmation_gated["decision"]["operating"]["metrics"][0]["confirmation_actual"], "1.0000")

    def test_portfolio_context_gates_executable_reduce(self):
        unknown = compile_report_v3(make_spec())
        self.assertEqual(unknown["decision"]["existing_position_candidate_action"], "REDUCE")
        self.assertEqual(unknown["decision"]["existing_position_action"], "REVIEW")

        spec = make_spec()
        spec["portfolio_context"].update({"position_status": "held", "current_weight": "0.08", "target_weight": "0.05", "confidence": "high"})
        held = compile_report_v3(spec)
        self.assertEqual(held["decision"]["existing_position_action"], "REDUCE")
        self.assertEqual(held["decision"]["portfolio_context"]["gate"], "passed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "held.spec.json"
            report_path = root / "held.md"
            write_spec(spec_path, spec)
            build(spec_path, report_path)
            self.assertEqual(lint_text(report_path.read_text(encoding="utf-8")), [])

        spec = make_spec()
        spec["portfolio_context"].update({"position_status": "held", "current_weight": "0.05", "target_weight": "0.08", "confidence": "high"})
        invalid_target = compile_report_v3(spec)
        self.assertEqual(invalid_target["decision"]["existing_position_action"], "REVIEW")
        self.assertEqual(invalid_target["decision"]["portfolio_context"]["gate"], "blocked_missing_reduce_target")

        spec = make_spec()
        spec["portfolio_context"].update({"position_status": "not_held", "confidence": "high"})
        absent = compile_report_v3(spec)
        self.assertEqual(absent["decision"]["existing_position_action"], "NOT_APPLICABLE")

    def test_thesis_break_blocks_new_money_before_price_rules(self):
        spec = make_spec()
        spec["decision_policy"]["thesis_break"]["logic"] = "any"
        spec["facts"]["FACT-CURRENT-PRICE"]["value"] = "100"
        spec["decision_policy"]["operating"]["metrics"][0].update({
            "hold_threshold": "300",
            "reduce_threshold": "200",
            "tolerance": "0",
            "uncertainty": "0",
        })
        bundle = compile_report_v3(spec)
        self.assertTrue(bundle["decision"]["thesis_break"]["triggered"])
        self.assertEqual(bundle["decision"]["new_money_action"], "DO_NOT_BUY")
        self.assertEqual(bundle["decision"]["existing_position_candidate_action"], "SELL")

    def test_ttm_currency_or_scale_mismatch_fails(self):
        spec = make_spec()
        spec["facts"]["FACT-Q2-26-FCF"]["unit"] = "CNY bn/10"
        with self.assertRaisesRegex(SpecError, "one explicit unit"):
            compile_report_v3(spec)

    def test_calculation_check_is_derived_not_hardcoded(self):
        bundle = compile_report_v3(make_spec())
        self.assertEqual(_calculation_check(bundle), "PASS")
        bundle["decision"]["valuation"]["base_irr"] = "0.9999"
        self.assertEqual(_calculation_check(bundle), "FAIL")

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
        with self.assertRaisesRegex(SpecError, "report-spec-v3.1"):
            compile_report_v3(spec)


if __name__ == "__main__":
    unittest.main()

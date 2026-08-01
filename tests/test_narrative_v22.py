from copy import deepcopy
import unittest

from scripts.report_compiler_v21 import compile_report_v21
from scripts.report_pipeline_v2 import _reader_errors
from scripts.report_renderer_narrative_v22 import render_reader_markdown
from scripts.report_spec_v2 import SpecError
from tests.meta_v21_spec import make_spec


class NarrativeV22Tests(unittest.TestCase):
    def test_meta_narrative_compiles(self):
        bundle = compile_report_v21(make_spec())
        self.assertEqual(bundle["narrative_quality"]["status"], "PASS")
        self.assertEqual(len(bundle["narrative"]["themes"]), 3)
        self.assertEqual(bundle["narrative_quality"]["checks"]["adversarial_debate_complete"]["cases"], 3)

    def test_reader_contains_themes_debate_causal_bridge_and_mirror_test(self):
        markdown = render_reader_markdown(compile_report_v21(make_spec()))
        for token in (
            "## 核心投资叙事",
            "Meta 的广告机器仍强",
            "人工智能资本开支正在把利润问题改写成资本回报问题",
            "Bull / Base / Bear",
            "### 财务因果桥",
            "### 镜子测试",
        ):
            self.assertIn(token, markdown)
        self.assertNotIn("### 三个核心矛盾", markdown)
        self.assertNotIn("本次判断可以压缩成三条主线", markdown)
        self.assertEqual(_reader_errors(markdown), [])

    def test_missing_narrative_fails(self):
        spec = make_spec()
        del spec["narrative"]
        with self.assertRaisesRegex(SpecError, "narrative must be an object"):
            compile_report_v21(spec)

    def test_too_few_themes_fails(self):
        spec = make_spec()
        spec["narrative"]["themes"] = spec["narrative"]["themes"][:2]
        with self.assertRaisesRegex(SpecError, "3-5 themes"):
            compile_report_v21(spec)

    def test_theme_without_company_entity_fails(self):
        spec = make_spec()
        theme = spec["narrative"]["themes"][0]
        theme["title"] = "强大的广告商业模式仍然具备长期竞争优势"
        theme["thesis"]["text"] = "核心业务通过用户注意力和广告需求形成持续反馈闭环。"
        for item in theme["mechanism"]:
            item["claim"] = "推荐效率和内容库存共同提升商业化能力。"
        theme["investment_implication"] = "业务质量能够支撑较高的长期价值下限。"
        with self.assertRaisesRegex(SpecError, "lacks company-specific entity"):
            compile_report_v21(spec)

    def test_theme_without_counter_evidence_role_fails(self):
        spec = make_spec()
        theme = spec["narrative"]["themes"][0]
        for item in [theme["thesis"], theme["counter_case"], *theme["mechanism"]]:
            for ref in item["evidence_refs"]:
                ref["role"] = "supports"
        with self.assertRaisesRegex(SpecError, "requires counter_evidence role"):
            compile_report_v21(spec)

    def test_theme_without_mechanism_chain_fails(self):
        spec = make_spec()
        spec["narrative"]["themes"][0]["mechanism"] = spec["narrative"]["themes"][0]["mechanism"][:1]
        with self.assertRaisesRegex(SpecError, "at least two mechanism claims"):
            compile_report_v21(spec)

    def test_incomplete_debate_fails(self):
        spec = make_spec()
        del spec["narrative"]["debate"]["bear_case"]
        with self.assertRaisesRegex(SpecError, "bear_case must be an object"):
            compile_report_v21(spec)

    def test_mirror_test_must_have_five_statements(self):
        spec = make_spec()
        spec["narrative"]["mirror_test"] = spec["narrative"]["mirror_test"][:4]
        with self.assertRaisesRegex(SpecError, "exactly five"):
            compile_report_v21(spec)

    def test_same_spec_has_deterministic_narrative(self):
        a = compile_report_v21(make_spec())
        b = compile_report_v21(deepcopy(make_spec()))
        self.assertEqual(a["narrative"], b["narrative"])
        self.assertEqual(render_reader_markdown(a), render_reader_markdown(b))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.meta_v21_spec import make_spec as make_v21_spec


def ev(ref: str, role: str = "supports") -> dict[str, str]:
    return {"ref": ref, "role": role}


def node(text: str, refs: list[dict[str, str]], implication: str = "该判断直接影响估值和当前动作。", confidence: str = "medium") -> dict[str, Any]:
    return {"text": text, "evidence_refs": refs, "implication": implication, "confidence": confidence}


def argument(argument_id: str, claim: str, refs: list[dict[str, str]], implication: str) -> dict[str, Any]:
    return {"argument_id": argument_id, "claim": claim, "evidence_refs": refs, "implication": implication, "confidence": "medium"}


def make_spec() -> dict[str, Any]:
    spec = make_v21_spec()
    spec["schema_version"] = "report-spec-v3.0"
    spec["research_graph"] = {
        "themes": [
            {
                "theme_id": "THEME-CAPITAL-RETURNS",
                "title": "人工智能资本开支能否转化为股东回报",
                "core_question": "当前自由现金流压缩是投资周期的暂时现象，还是资本强度永久上升？",
                "observations": [
                    {"observation_id": "OBS-FCF-COMPRESSION", **node("最新季度自由现金流出现断崖式压缩。", [ev("FACT-Q2-26-FCF"), ev("SRC-META-Q2-2026")])},
                    {"observation_id": "OBS-MARGIN-PRESSURE", **node("经营利润率仍高但最新季度已经明显回落。", [ev("FACT-Q2-26-OI"), ev("BUNDLE:/derived/ttm/operating_margin/value_pct")])},
                ],
                "hypothesis": node("资本开支正在把优质广告业务的利润转化为更晚兑现的现金回报。", [ev("FACT-Q1-26-FCF"), ev("FACT-Q2-26-FCF"), ev("SRC-META-Q2-2026")], "估值应从历史自由现金流转向增量资本回报。"),
                "challenge": node("季度采购时点和在建工程可能夸大了现金流恶化的持续性。", [ev("FACT-Q2-26-FCF", "counter_evidence"), ev("FACT-Q1-26-FCF")], "单季自由现金流不能单独证明长期资本回报下降。"),
                "resolution": node("现金流压力既包含季度波动，也反映资本强度进入新的更高平台。", [ev("FACT-Q2-26-FCF"), ev("FACT-Q1-26-FCF", "counter_evidence"), ev("SRC-META-Q2-2026")], "当前应要求未来财报证明投入可以恢复利润率和自由现金流。"),
                "decision_impact": node("资本回报未被验证前，基础情景回报不足以支持新增资金。", [ev("BUNDLE:/decision/valuation/base_irr"), ev("BUNDLE:/decision/valuation/target_return")], "已有仓位也需要降低对乐观资本回报的依赖。"),
                "falsification": node("若利润率与自由现金流在后续报告期持续恢复，该主题的悲观裁决将被推翻。", [ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct"), ev("SRC-META-Q2-2026")], "届时应重新评估减仓结论。"),
                "module_links": ["financial_autopsy", "valuation", "risks", "positioning"],
            },
            {
                "theme_id": "THEME-AD-FLYWHEEL",
                "title": "广告推荐飞轮能否继续抵消平台成熟",
                "core_question": "用户规模成熟后，推荐效率和商业化工具能否继续推动高质量增长？",
                "observations": [
                    {"observation_id": "OBS-REVENUE-RESILIENCE", **node("连续季度收入仍保持强韧增长趋势。", [ev("FACT-Q1-26-REV"), ev("FACT-Q2-26-REV")])},
                    {"observation_id": "OBS-USER-MATURITY", **node("用户规模成熟使新增用户对增长的边际贡献下降。", [ev("SRC-META-USERS")])},
                ],
                "hypothesis": node("推荐算法和广告自动化正在把增长引擎从用户扩张转向每用户价值提升。", [ev("SRC-META-USERS"), ev("FACT-Q2-26-REV")], "主业质量仍足以支撑较高利润底盘。"),
                "challenge": node("竞争平台争夺时长和隐私限制可能削弱推荐与定向广告优势。", [ev("SRC-PEER", "counter_evidence"), ev("SRC-META-USERS")], "广告飞轮并非不可逆。"),
                "resolution": node("广告飞轮仍然有效，但未来增长更依赖效率而不是用户自然扩张。", [ev("FACT-Q2-26-REV"), ev("SRC-PEER", "counter_evidence"), ev("SRC-META-USERS")], "估值可以承认主业质量，却不能假设增长永远维持峰值。"),
                "decision_impact": node("主业韧性阻止了卖出结论，但不足以抵消当前价格的回报缺口。", [ev("BUNDLE:/decision/existing_position_action"), ev("BUNDLE:/decision/valuation/base_irr")], "动作应是估值纪律而不是商业模式否定。"),
                "falsification": node("若广告效率和参与度同步持续恶化，主业韧性的判断将失效。", [ev("SRC-META-USERS"), ev("SRC-PEER")], "届时需要把风险从估值问题升级为核心逻辑破坏。"),
                "module_links": ["overview", "moat", "growth_limits", "opportunity_cost"],
            },
            {
                "theme_id": "THEME-PRICE-EXPECTATIONS",
                "title": "当前价格要求什么样的经营兑现",
                "core_question": "市场价格隐含的盈利路径是否已经超过基础情景能够可靠提供的水平？",
                "observations": [
                    {"observation_id": "OBS-IRR-GAP", **node("基础情景回报明显低于最低目标回报。", [ev("BUNDLE:/decision/valuation/base_irr"), ev("BUNDLE:/decision/valuation/target_return")])},
                    {"observation_id": "OBS-SCENARIO-SPREAD", **node("乐观与悲观情景之间存在非常宽的回报分布。", [ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct"), ev("BUNDLE:/scenarios/bear/returns/irr/irr_pct")])},
                ],
                "hypothesis": node("现价需要更接近乐观情景的利润率恢复和每股收益增长。", [ev("BUNDLE:/scenarios/base/prices/target_return"), ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct")], "基础情景不足以为集中持仓提供足够补偿。"),
                "challenge": node("高质量复利公司可能长期享有高于传统估值框架的质量溢价。", [ev("BUNDLE:/scenarios/bull/prices/forward_reference", "counter_evidence"), ev("SRC-META-USERS")], "机械要求所有公司达到同一回报门槛可能过度保守。"),
                "resolution": node("质量溢价合理，但不能替代对未来现金回报和机会成本的验证。", [ev("BUNDLE:/decision/valuation/base_irr"), ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct", "counter_evidence"), ev("BUNDLE:/decision/valuation/target_return")], "当前价格更适合等待而不是主动承担预测风险。"),
                "decision_impact": node("新增资金暂不买入，已有仓位按回报缺口执行降低暴露。", [ev("BUNDLE:/decision/new_money_action"), ev("BUNDLE:/decision/existing_position_action")], "价格下降或经营证据增强才会改变动作。"),
                "falsification": node("若基础情景盈利路径上修并显著提高预期回报，当前价格纪律需要重算。", [ev("BUNDLE:/scenarios/base/returns/irr/irr_pct"), ev("BUNDLE:/scenarios/base/prices/target_return")], "结论不是静态目标价，而是随经营证据更新。"),
                "module_links": ["valuation", "opportunity_cost", "positioning", "final_verdict"],
            },
        ],
        "debate": {
            "bull": [
                argument("ARG-BULL-AD-EFFICIENCY", "广告推荐和自动化工具仍可能持续提高广告主回报。", [ev("SRC-META-USERS"), ev("FACT-Q2-26-REV")], "主业增长可能长期高于基础情景。"),
                argument("ARG-BULL-AI-OPTIONALITY", "人工智能基础设施可能形成广告和新产品的长期复利平台。", [ev("SRC-META-Q2-2026"), ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct")], "当前现金流压缩可能换来更高终值。"),
                argument("ARG-BULL-QUALITY-PREMIUM", "关系链和多产品分发能力支持长期质量溢价。", [ev("SRC-META-USERS"), ev("SRC-PEER")], "传统目标回报门槛可能低估稀缺资产。"),
            ],
            "bear": [
                argument("ARG-BEAR-CAPITAL-INTENSITY", "资本强度上升正在削弱历史自由现金流估值的可靠性。", [ev("FACT-Q2-26-FCF"), ev("SRC-META-Q2-2026")], "股东回报可能长期低于利润表表现。"),
                argument("ARG-BEAR-RETURN-GAP", "基础情景回报显著低于最低目标回报。", [ev("BUNDLE:/decision/valuation/base_irr"), ev("BUNDLE:/decision/valuation/target_return")], "当前价格没有提供足够机会成本补偿。"),
                argument("ARG-BEAR-EXECUTION-RISK", "乐观情景需要利润率恢复和新业务商业化同时兑现。", [ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct"), ev("SRC-META-Q2-2026")], "多个关键变量同时成功的概率不应被默认。"),
            ],
            "adjudication": {
                **node("主业质量和人工智能上行空间值得承认，但基础情景回报缺口与资本强度上升更直接决定当前动作。", [ev("BUNDLE:/decision/valuation/base_irr"), ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct", "counter_evidence"), ev("FACT-Q2-26-FCF")], "因此不否定公司质量，但坚持暂不买入并降低已有仓位暴露。"),
                "accepted_argument_ids": ["ARG-BULL-AD-EFFICIENCY", "ARG-BEAR-CAPITAL-INTENSITY", "ARG-BEAR-RETURN-GAP"],
                "discounted_argument_ids": ["ARG-BULL-QUALITY-PREMIUM", "ARG-BEAR-EXECUTION-RISK"],
                "remaining_uncertainty": "人工智能投入的增量资本回报仍缺少足够长的经营历史验证。",
            },
        },
        "sensitivity": {
            "drivers": [
                {
                    "driver_id": "DRV-OPERATING-MARGIN",
                    "variable": "前瞻经营利润率恢复幅度",
                    "base_assumption_path": "/assumptions/scenario/ASM-BASE-MARGIN/value",
                    "direction": "positive",
                    "importance": "high",
                    "mechanism": "利润率直接决定前瞻每股收益并放大终值差异。",
                    "upside_case": "折旧压力被收入增长吸收后，利润率恢复将显著提高基础情景回报。",
                    "downside_case": "折旧和研发持续快于收入增长会压低每股收益和目标回报价格。",
                    "decision_consequence": "利润率无法恢复会强化减仓，持续恢复则可能把动作降级为持有或复核。",
                    "evidence_refs": [ev("BUNDLE:/scenarios/base/eps_bridge/operating_margin"), ev("FACT-Q2-26-OI")],
                },
                {
                    "driver_id": "DRV-EPS-GROWTH",
                    "variable": "未来每股收益复合增长路径",
                    "base_assumption_path": "/assumptions/scenario/ASM-BASE-EPS-CAGR/value",
                    "direction": "positive",
                    "importance": "high",
                    "mechanism": "每股收益增长同时影响终值和五年内部回报率。",
                    "upside_case": "广告效率和回购共同推动更高每股收益增长时，现价回报会快速改善。",
                    "downside_case": "资本开支拖累利润和回购能力时，基础情景回报将继续低于门槛。",
                    "decision_consequence": "增长路径上修是重新加仓最关键的模型条件之一。",
                    "evidence_refs": [ev("BUNDLE:/scenarios/base/returns/assumptions/eps_cagr"), ev("SRC-META-Q2-2026")],
                },
                {
                    "driver_id": "DRV-EXIT-MULTIPLE",
                    "variable": "长期退出估值倍数假设",
                    "base_assumption_path": "/assumptions/scenario/ASM-BASE-EXIT/value",
                    "direction": "positive",
                    "importance": "medium",
                    "mechanism": "退出倍数决定终值，但不能替代经营现金回报。",
                    "upside_case": "质量溢价长期维持时，终值会高于保守基础情景。",
                    "downside_case": "资本回报下降会令市场压缩估值倍数并形成双重打击。",
                    "decision_consequence": "若结论主要依赖倍数扩张而非盈利兑现，应维持谨慎动作。",
                    "evidence_refs": [ev("BUNDLE:/scenarios/base/returns/assumptions/exit_pe"), ev("SRC-PEER")],
                },
            ]
        },
    }
    return spec


def write_spec(path: Path) -> None:
    path.write_text(json.dumps(make_spec(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_spec(args.output)

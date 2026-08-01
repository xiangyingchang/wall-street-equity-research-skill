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


def node(text: str, refs: list[dict[str, str]], implication: str, confidence: str = "medium") -> dict[str, Any]:
    return {"text": text, "evidence_refs": refs, "implication": implication, "confidence": confidence}


def argument(argument_id: str, claim: str, refs: list[dict[str, str]], implication: str) -> dict[str, Any]:
    return {"argument_id": argument_id, "claim": claim, "evidence_refs": refs, "implication": implication, "confidence": "medium"}


def make_spec() -> dict[str, Any]:
    spec = make_v21_spec()
    spec["schema_version"] = "report-spec-v3.1"
    spec["decision_policy"]["require_portfolio_context"] = True
    legacy_operating = spec["decision_policy"]["operating"]
    spec["decision_policy"]["operating"] = {
        "metrics": [{
            "metric_id": "OP-TTM-FCF",
            "label": "TTM 自由现金流",
            "value_ref": "BUNDLE:/derived/ttm/fcf/value",
            "unit": "USD bn/10",
            "direction": "higher_is_better",
            "hold_threshold": legacy_operating["hold_threshold"],
            "reduce_threshold": legacy_operating["reduce_threshold"],
            "tolerance": legacy_operating["tolerance"],
            "uncertainty": legacy_operating["uncertainty"],
            "confirmation_periods": legacy_operating["confirmation"],
        }]
    }
    spec["decision_policy"]["thesis_break"]["conditions"][0]["label"] = "单季自由现金流"
    spec["decision_policy"]["thesis_break"]["conditions"][1]["label"] = "连续高资本开支季度数"
    spec["portfolio_context"] = {
        "position_status": "unknown",
        "as_of": "2026-08-01",
        "source": "Portfolio Dashboard snapshot not supplied to this fixture",
        "confidence": "low",
        "current_weight": None,
        "target_weight": None,
        "tax_friction": "unknown",
        "constraints": "必须读取实际组合权重后，才能把研究候选减仓转成可执行动作。",
    }
    spec["prior_report_context"] = {
        "status": "available",
        "path": "股票/Meta/META.US-Meta-华尔街式分析报告-2026-07-31.md",
        "as_of": "2026-07-31",
        "previous_new_money_action": "DO_NOT_BUY",
        "previous_existing_position_action": "REDUCE",
        "previous_base_irr_reported": "0.095",
        "previous_base_irr_recalculated": "0.0164",
        "calculation_status": "recalculated",
        "recalculation_inputs": {
            "current_price": "549",
            "starting_eps": "22",
            "eps_cagr": "0.08",
            "exit_pe": "18",
            "years": "5",
            "dividend_yield": "0.005",
        },
        "rating_delta": "评级维持新资金暂不买入；存量研究候选仍为降低暴露，但本版增加组合执行闸门。",
        "metric_delta": "估值 Base IRR 从上版报告值改为运行时复算，并在本版采用新的前瞻盈利桥接。",
        "thesis_delta": "投资逻辑没有改变：主业质量仍强，资本开支回报与现价机会成本仍是核心矛盾。",
        "methodology_delta": "方法从手写场景结果升级为可复算 Bundle、动态经营指标和持仓上下文闸门。",
    }
    rationale_updates = {
        "ASM-BASE-MARGIN": "一次性费用消退，但保留折旧与研发压力。",
        "ASM-BASE-CAGR": "主业进入中周期后的每股盈利增长中枢。",
        "ASM-BASE-EXIT": "成熟期倍数低于当前质量溢价水平。",
        "ASM-GLOBAL-DIVIDEND": "按当前年度股息率作为保守现金回报。",
        "ASM-GLOBAL-SAFETY": "人工智能资本开支回报尚未验证。",
    }
    for assumption_id, rationale in rationale_updates.items():
        spec["assumptions"][assumption_id]["rationale"] = rationale
    spec["research_graph"] = {
        "themes": [
            {
                "theme_id": "THEME-CAPITAL-RETURNS",
                "title": "人工智能资本开支能否转化为股东回报",
                "core_question": "当前自由现金流压缩是投资周期的暂时现象，还是资本强度永久上升？",
                "observations": [
                    {"observation_id": "OBS-FCF-COMPRESSION", **node("最新季度自由现金流出现断崖式压缩。", [ev("FACT-Q2-26-FCF"), ev("SRC-META-Q2-2026")], "资本开支已经成为股东回报的核心变量。")},
                    {"observation_id": "OBS-MARGIN-PRESSURE", **node("经营利润率仍高但最新季度已经明显回落。", [ev("FACT-Q2-26-OI"), ev("BUNDLE:/derived/ttm/operating_margin/value_pct")], "利润表开始反映折旧和研发投入压力。")},
                ],
                "hypothesis": node("资本开支正在把优质广告业务的利润转化为更晚兑现的现金回报。", [ev("FACT-Q1-26-FCF"), ev("FACT-Q2-26-FCF")], "估值应从历史自由现金流转向增量资本回报。"),
                "challenge": node("季度采购时点可能夸大现金流恶化的持续性。", [ev("FACT-Q2-26-FCF", "counter_evidence"), ev("FACT-Q1-26-FCF")], "单季自由现金流不能单独证明长期回报下降。"),
                "resolution": node("现金流压力既包含季度波动，也反映资本强度进入更高平台。", [ev("FACT-Q2-26-FCF"), ev("FACT-Q1-26-FCF", "counter_evidence")], "未来财报必须证明投入可以恢复利润率和现金流。"),
                "decision_impact": node("资本回报未被验证前，基础情景回报不足以支持新增资金。", [ev("BUNDLE:/decision/valuation/base_irr"), ev("BUNDLE:/decision/valuation/target_return")], "已有仓位也需要降低对乐观资本回报的依赖。"),
                "falsification": node("若利润率与自由现金流持续恢复，当前悲观裁决将被推翻。", [ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct"), ev("SRC-META-Q2-2026")], "届时应重新评估降低暴露的研究候选。"),
                "module_links": ["financial_autopsy", "valuation", "risks", "positioning"],
            },
            {
                "theme_id": "THEME-AD-FLYWHEEL",
                "title": "广告推荐飞轮能否继续抵消平台成熟",
                "core_question": "用户规模成熟后，推荐效率和商业化工具能否继续推动高质量增长？",
                "observations": [
                    {"observation_id": "OBS-REVENUE-RESILIENCE", **node("连续季度收入仍保持强韧增长趋势。", [ev("FACT-Q1-26-REV"), ev("FACT-Q2-26-REV")], "广告主业并未出现结构性需求衰退。")},
                    {"observation_id": "OBS-USER-MATURITY", **node("用户规模成熟使新增用户贡献持续下降。", [ev("SRC-META-USERS")], "增长必须更多依靠变现和参与度。")},
                ],
                "hypothesis": node("推荐算法和广告自动化正在把增长引擎转向每用户价值提升。", [ev("SRC-META-USERS"), ev("FACT-Q2-26-REV")], "主业质量仍足以支撑较高利润底盘。"),
                "challenge": node("竞争平台和隐私限制可能削弱推荐与定向广告优势。", [ev("SRC-PEER", "counter_evidence"), ev("SRC-META-USERS")], "广告飞轮并非不可逆转。"),
                "resolution": node("广告飞轮仍然有效，但未来增长更依赖效率而非用户扩张。", [ev("FACT-Q2-26-REV"), ev("SRC-PEER", "counter_evidence")], "估值不能假设增长永久维持峰值。"),
                "decision_impact": node("主业韧性阻止卖出结论，但不足以抵消当前价格回报缺口。", [ev("BUNDLE:/decision/existing_position_action"), ev("BUNDLE:/decision/valuation/base_irr")], "动作是估值纪律而不是商业模式否定。"),
                "falsification": node("若广告效率和参与度同步恶化，主业韧性判断将失效。", [ev("SRC-META-USERS"), ev("SRC-PEER")], "风险将从估值问题升级为核心逻辑破坏。"),
                "module_links": ["overview", "moat", "growth_limits", "opportunity_cost"],
            },
            {
                "theme_id": "THEME-PRICE-EXPECTATIONS",
                "title": "当前价格要求什么样的经营兑现",
                "core_question": "市场价格隐含的盈利路径是否超过基础情景能够可靠提供的水平？",
                "observations": [
                    {"observation_id": "OBS-IRR-GAP", **node("基础情景回报明显低于最低目标回报。", [ev("BUNDLE:/decision/valuation/base_irr"), ev("BUNDLE:/decision/valuation/target_return")], "现价缺少足够的机会成本补偿。")},
                    {"observation_id": "OBS-SCENARIO-SPREAD", **node("乐观与悲观情景之间存在很宽的回报分布。", [ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct"), ev("BUNDLE:/scenarios/bear/returns/irr/irr_pct")], "当前结论高度依赖关键假设兑现。")},
                ],
                "hypothesis": node("现价需要更接近乐观情景的利润率恢复和每股收益增长。", [ev("BUNDLE:/scenarios/base/prices/target_return"), ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct")], "基础情景不足以补偿集中持仓风险。"),
                "challenge": node("高质量复利公司可能长期享有传统模型之外的质量溢价。", [ev("BUNDLE:/scenarios/bull/prices/forward_reference", "counter_evidence"), ev("SRC-META-USERS")], "统一回报门槛可能对稀缺资产过度保守。"),
                "resolution": node("质量溢价合理，但不能替代对未来现金回报的验证。", [ev("BUNDLE:/decision/valuation/base_irr"), ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct", "counter_evidence")], "当前价格更适合等待而不是主动承担预测风险。"),
                "decision_impact": node("新增资金暂不买入，估值层对已有仓位给出降低暴露候选。", [ev("BUNDLE:/decision/new_money_action"), ev("BUNDLE:/decision/existing_position_action")], "实际执行仍取决于组合状态、当前权重和目标权重。"),
                "falsification": node("若基础情景盈利路径上修，当前价格纪律需要重新计算。", [ev("BUNDLE:/scenarios/base/returns/irr/irr_pct"), ev("BUNDLE:/scenarios/base/prices/target_return")], "结论会随经营证据动态更新。"),
                "module_links": ["valuation", "opportunity_cost", "positioning", "final_verdict"],
            },
        ],
        "debate": {
            "bull": [
                argument("ARG-BULL-AD-EFFICIENCY", "广告推荐和自动化工具仍可能持续提高广告主回报。", [ev("SRC-META-USERS"), ev("FACT-Q2-26-REV")], "主业增长可能长期高于基础情景。"),
                argument("ARG-BULL-AI-OPTIONALITY", "人工智能基础设施可能形成广告和新产品的长期复利平台。", [ev("SRC-META-Q2-2026"), ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct")], "现金流压缩可能换来更高长期终值。"),
                argument("ARG-BULL-QUALITY-PREMIUM", "关系链和多产品分发能力支持长期质量溢价。", [ev("SRC-META-USERS"), ev("SRC-PEER")], "传统目标回报门槛可能低估稀缺资产。"),
            ],
            "bear": [
                argument("ARG-BEAR-CAPITAL-INTENSITY", "资本强度上升削弱历史自由现金流估值的可靠性。", [ev("FACT-Q2-26-FCF"), ev("SRC-META-Q2-2026")], "股东回报可能长期低于利润表表现。"),
                argument("ARG-BEAR-RETURN-GAP", "基础情景回报显著低于最低目标回报。", [ev("BUNDLE:/decision/valuation/base_irr"), ev("BUNDLE:/decision/valuation/target_return")], "当前价格没有提供足够风险补偿。"),
                argument("ARG-BEAR-EXECUTION-RISK", "乐观情景需要利润率恢复和新业务商业化同时兑现。", [ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct"), ev("SRC-META-Q2-2026")], "多个变量同时成功的概率不应被默认。"),
            ],
            "adjudication": {
                **node("主业质量和人工智能上行空间值得承认，但回报缺口与资本强度更直接决定当前动作。", [ev("BUNDLE:/decision/valuation/base_irr"), ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct", "counter_evidence"), ev("FACT-Q2-26-FCF")], "因此不否定公司质量；新资金暂不买入，存量候选动作须经组合闸门确认。"),
                "accepted_argument_ids": ["ARG-BULL-AD-EFFICIENCY", "ARG-BEAR-CAPITAL-INTENSITY", "ARG-BEAR-RETURN-GAP"],
                "discounted_argument_ids": ["ARG-BULL-QUALITY-PREMIUM", "ARG-BEAR-EXECUTION-RISK"],
                "remaining_uncertainty": "人工智能投入的增量资本回报仍缺少足够长的经营历史验证。",
            },
        },
        "sensitivity": {
            "drivers": [
                {"driver_id": "DRV-OPERATING-MARGIN", "variable": "前瞻经营利润率恢复幅度", "base_assumption_path": "/assumptions/scenario/ASM-BASE-MARGIN/value", "direction": "positive", "importance": "high", "mechanism": "利润率直接决定前瞻每股收益并放大终值差异。", "upside_case": "折旧压力被收入增长吸收后，基础情景回报将显著改善。", "downside_case": "折旧和研发持续快于收入增长会压低目标回报价格。", "decision_consequence": "利润率无法恢复会强化降低暴露候选，持续恢复则可能转为持有。", "evidence_refs": [ev("BUNDLE:/scenarios/base/eps_bridge/eps"), ev("FACT-Q2-26-OI")]},
                {"driver_id": "DRV-EPS-GROWTH", "variable": "未来每股收益复合增长路径", "base_assumption_path": "/assumptions/scenario/ASM-BASE-EPS-CAGR/value", "direction": "positive", "importance": "high", "mechanism": "每股收益增长同时影响终值和五年内部回报率。", "upside_case": "广告效率和回购推动更高增长时，现价回报会快速改善。", "downside_case": "资本开支拖累利润和回购能力时，回报将继续低于门槛。", "decision_consequence": "增长路径上修是重新加仓最关键的模型条件之一。", "evidence_refs": [ev("BUNDLE:/scenarios/base/returns/irr/irr_pct"), ev("SRC-META-Q2-2026")]},
                {"driver_id": "DRV-EXIT-MULTIPLE", "variable": "长期退出估值倍数假设", "base_assumption_path": "/assumptions/scenario/ASM-BASE-EXIT/value", "direction": "positive", "importance": "medium", "mechanism": "退出倍数决定终值，但不能替代经营现金回报。", "upside_case": "质量溢价长期维持时，终值会高于保守基础情景。", "downside_case": "资本回报下降会令市场压缩倍数并形成双重打击。", "decision_consequence": "若结论主要依赖倍数扩张而非盈利兑现，应维持谨慎。", "evidence_refs": [ev("BUNDLE:/scenarios/base/returns/irr/irr_pct"), ev("SRC-PEER")]},
            ]
        },
    }
    spec["research"]["positioning"]["existing_position"]["text"] = "估值层给出降低暴露候选，但持仓状态、当前权重和目标权重缺失时只能复核。"
    spec["research"]["positioning"]["portfolio_constraints"]["text"] = "真实持仓权重、目标权重、税费和替代资产质量共同决定能否执行调整。"
    spec["research"]["final_verdict"]["falsification"]["text"] = "若增量资本开支带来可持续的利润率恢复和自由现金流增长，当前谨慎结论需要重新评估。"
    spec["research"]["final_verdict"]["falsification"]["implication"] = "相反，资本开支继续增长而回报不改善，将强化降低暴露的研究候选。"
    return spec


def write_spec(path: Path, spec: dict[str, Any] | None = None) -> None:
    path.write_text(json.dumps(make_spec() if spec is None else spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_spec(args.output)

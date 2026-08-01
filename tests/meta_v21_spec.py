from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.meta_v21_factory import make_spec as _base_spec


def _pointer(ref: str) -> str:
    if not ref.startswith("BUNDLE:"):
        return ref
    raw = ref.removeprefix("BUNDLE:")
    if raw.startswith("derived.payback_required_growth."):
        raw = "derived.payback_required_growth"
    return "BUNDLE:/" + raw.replace(".", "/")


def _normalize_research(value: Any) -> None:
    if isinstance(value, dict):
        refs = value.get("evidence_refs")
        if isinstance(refs, list):
            value["evidence_refs"] = [
                {"ref": _pointer(str(ref.get("ref", ""))), "role": str(ref.get("role", "supports"))}
                if isinstance(ref, dict)
                else {"ref": _pointer(str(ref)), "role": "supports"}
                for ref in refs
            ]
        for child in value.values():
            _normalize_research(child)
    elif isinstance(value, list):
        for child in value:
            _normalize_research(child)


def _ev(*refs: str, counter: str | None = None) -> list[dict[str, str]]:
    out = [{"ref": _pointer(ref), "role": "supports"} for ref in refs]
    if counter:
        out.append({"ref": _pointer(counter), "role": "counter_evidence"})
    return out


def _claim(text: str, refs: list[dict[str, str]], implication: str = "该判断会直接影响当前估值和仓位纪律。", confidence: str = "medium") -> dict[str, Any]:
    return {"claim": text, "evidence_refs": refs, "confidence": confidence, "implication": implication}


def _text(text: str, refs: list[dict[str, str]], confidence: str = "medium") -> dict[str, Any]:
    return {"text": text, "evidence_refs": refs, "confidence": confidence}


def make_spec() -> dict[str, Any]:
    spec = _base_spec()
    spec["schema_version"] = "report-spec-v2.2"
    for scope in ("shares", "current price"):
        if scope not in spec["sources"]["SRC-META-Q2-2026"]["scope"]:
            spec["sources"]["SRC-META-Q2-2026"]["scope"].append(scope)
    names = [
        "网络效应与关系链核心护城河能力",
        "数据资产与广告技术基础设施能力",
        "多边生态网络与产品分发协同能力",
        "资本实力与长期组织执行竞争能力",
    ]
    for item, name in zip(spec["research"]["moat"]["dimensions"], names):
        item["name"] = name
    for risk in spec["research"]["risks"]["items"]:
        risk["leading_indicators"] = [text if len(text) >= 12 else f"{text}并形成持续趋势。" for text in risk["leading_indicators"]]
    _normalize_research(spec["research"])

    valuation = spec["research"]["valuation"]["reverse_expectations"]
    valuation.pop("text", None)
    valuation["text_template"] = "当前价格对应 Base IRR 为 {base_irr}，低于目标回报 {target_return}，因此需要更强的经营兑现。"
    valuation["value_refs"] = {
        "base_irr": {"path": "/decision/valuation/base_irr", "format": "percent"},
        "target_return": {"path": "/decision/valuation/target_return", "format": "percent"},
    }

    new_money = spec["research"]["positioning"]["new_money"]
    new_money.pop("text", None)
    new_money["text_template"] = "新资金应等待 Base target-return price {target_price} 或更强的经营证据，而不是在当前价格主动买入。"
    new_money["value_refs"] = {"target_price": {"path": "/scenarios/base/prices/target_return", "format": "money"}}

    spec["company_entities"] = ["Meta", "Facebook", "Instagram", "WhatsApp", "Threads", "Reels", "Reality Labs"]
    spec["narrative"] = {
        "themes": [
            {
                "id": "THEME-AD-MACHINE",
                "category": "business",
                "title": "Meta 的广告机器仍强，Instagram 与 Reels 决定护城河能否继续变宽",
                "thesis": _text("Meta 的核心价值仍来自 Facebook、Instagram 与 Reels 共同形成的注意力、推荐和广告反馈闭环。", _ev("SRC-META-USERS", "FACT-Q2-26-REV", counter="SRC-PEERS"), "high"),
                "mechanism": [
                    _claim("Instagram 与 Reels 提供持续扩张的内容库存，人工智能推荐提高用户时长和广告匹配效率。", _ev("SRC-META-USERS", counter="SRC-PEERS"), "更高参与度只有转化为广告价格或展示增长，才会形成每股价值。", "high"),
                    _claim("WhatsApp 与 Threads 提供尚未完全兑现的商业化选择权，但当前估值不应提前计入全部潜力。", _ev("SRC-META-USERS", counter="SRC-META-Q2-2026"), "选择权应作为上行情景，而不是基础情景的确定利润。"),
                ],
                "counter_case": _text("如果 TikTok、YouTube 或新内容形态持续分流年轻用户，Meta 的广告反馈闭环可能从增强转为成熟。", _ev("SRC-PEERS", counter="SRC-META-USERS")),
                "investment_implication": "主业质量支持较高估值下限，但不能单独证明现价具有足够安全边际。",
                "validation_signals": ["Instagram 与 Reels 的参与度和广告展示继续同步增长。", "广告价格改善能够抵消内容结构变化与隐私约束。"],
            },
            {
                "id": "THEME-CAPEX-RETURNS",
                "category": "capital",
                "title": "Meta 的人工智能资本开支正在把利润问题改写成资本回报问题",
                "thesis": _text("Meta 最新季度收入仍强，但自由现金流骤降说明数据中心、服务器与人工智能基础设施已经改变现金回收节奏。", _ev("FACT-Q2-26-REV", "FACT-Q2-26-FCF", counter="FACT-Q1-26-FCF"), "high"),
                "mechanism": [
                    _claim("基础设施投入先进入资本开支，随后通过折旧和运营成本压缩利润率，因此收入增长不会立刻等比例转化为自由现金流。", _ev("FACT-Q2-26-OI", "FACT-Q2-26-FCF", counter="FACT-Q1-26-OI"), "估值必须从历史现金流峰值切换到资本回报兑现路径。", "high"),
                    _claim("Reality Labs 与长期人工智能投入扩大了 Meta 的上行选择权，也提高了管理层资本配置失误的代价。", _ev("SRC-META-Q2-2026", counter="SRC-META-Q3-2025"), "未来两个报告期的利润率和自由现金流恢复比单季收入增速更重要。"),
                ],
                "counter_case": _text("如果人工智能投入显著提升推荐效率、广告创意转化和新产品商业化，当前现金流压缩可能只是高回报投资的前置阶段。", _ev("SRC-META-Q2-2026", counter="FACT-Q2-26-FCF")),
                "investment_implication": "资本回报未验证前，应降低对历史自由现金流和稳定利润率的依赖。",
                "validation_signals": ["资本开支增速放缓后经营利润率重新改善。", "新增收入和自由现金流能够与人工智能投入形成可量化对应。"],
            },
            {
                "id": "THEME-PRICE-EXPECTATIONS",
                "category": "valuation",
                "title": "Meta 当前价格要求经营结果明显高于 Base，但尚未完全定价 Bull",
                "thesis": {
                    "text_template": "Meta 当前价格对应的 Base IRR 只有 {base_irr}，低于最低目标回报 {hurdle}，价格已经要求更接近乐观情景的兑现。",
                    "value_refs": {
                        "base_irr": {"path": "/decision/valuation/base_irr", "format": "percent"},
                        "hurdle": {"path": "/decision/valuation/target_return", "format": "percent"},
                    },
                    "evidence_refs": _ev("BUNDLE:/decision/valuation/base_irr", "BUNDLE:/decision/valuation/target_return", counter="BUNDLE:/scenarios/bull/returns/irr/irr_pct"),
                    "confidence": "high",
                },
                "mechanism": [
                    _claim("Base 情景无法覆盖集中持股需要的风险补偿，持有现有仓位的机会成本已经高于新增买入判断。", _ev("BUNDLE:/decision/valuation/base_irr", counter="BUNDLE:/scenarios/bull/returns/irr/irr_pct"), "好公司与好价格必须分开判断。", "high"),
                    _claim("Bull 情景仍提供可观上行，说明争议核心不是 Meta 必然高估，而是资本回报兑现概率是否足够高。", _ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct", counter="BUNDLE:/scenarios/bear/returns/irr/irr_pct"), "仓位动作应保留上行参与，同时降低 Base 回报不足的暴露。"),
                ],
                "counter_case": _text("如果未来利润率、每股收益和长期倍数同时接近 Bull 假设，现价仍可能获得高于门槛的回报。", _ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct", counter="BUNDLE:/decision/valuation/base_irr")),
                "investment_implication": "新资金暂不买入，已有仓位减仓，但结论必须随资本回报证据更新。",
                "validation_signals": ["Base 情景 IRR 回升至最低目标回报附近。", "目标回报价格上升并接近当前市场价格。"],
            },
        ],
        "debate": {
            "bull_case": {
                "thesis": _text("Bull Case 认为 Meta 的人工智能投入会同时提升广告效率、用户参与度和新产品商业化。", _ev("SRC-META-USERS", "SRC-META-Q2-2026", counter="FACT-Q2-26-FCF")),
                "value_ref": {"path": "/scenarios/bull/returns/irr/irr_pct", "format": "percent"},
                "path_to_win": "Reels 与人工智能推荐继续提升广告变现，利润率在投入高峰后恢复。",
                "failure_signal": "资本开支持续上升，但广告效率和利润率没有对应改善。",
            },
            "base_case": {
                "thesis": _text("Base Case 认为广告主业保持增长，但资本强度和折旧限制利润率恢复速度。", _ev("FACT-Q2-26-REV", "FACT-Q2-26-OI", counter="SRC-META-USERS")),
                "value_ref": {"path": "/scenarios/base/returns/irr/irr_pct", "format": "percent"},
                "path_to_win": "收入增长保持稳健，资本开支逐步稳定，自由现金流恢复但不回到历史峰值。",
                "failure_signal": "收入增长和利润率同时明显偏离基础假设。",
            },
            "bear_case": {
                "thesis": _text("Bear Case 认为 Meta 正进入资本回报下降阶段，竞争、监管和 Reality Labs 会延长现金流压力。", _ev("FACT-Q2-26-FCF", "SRC-PEERS", counter="FACT-Q2-26-REV")),
                "value_ref": {"path": "/scenarios/bear/returns/irr/irr_pct", "format": "percent"},
                "path_to_win": "只有市场价格大幅下降或经营投入快速收缩，悲观情景的下行风险才会被吸收。",
                "failure_signal": "自由现金流和经营利润率连续恢复将削弱悲观判断。",
            },
            "key_disagreement": "人工智能资本开支最终带来的增量经营利润，能否超过折旧、服务器和数据中心带来的长期成本。",
        },
        "financial_causal_bridge": {
            "operating_change": {
                "text_template": "Q2 收入达到 {revenue}，但经营利润降至 {oi}，说明需求增长没有完整转化为经营杠杆。",
                "value_refs": {"revenue": {"path": "/facts/FACT-Q2-26-REV/value", "format": "number"}, "oi": {"path": "/facts/FACT-Q2-26-OI/value", "format": "number"}},
                "evidence_refs": _ev("FACT-Q2-26-REV", "FACT-Q2-26-OI"), "confidence": "high",
            },
            "cost_driver": _text("主要压力来自人工智能基础设施、数据中心、服务器、研发和后续折旧，而不是广告需求突然崩塌。", _ev("SRC-META-Q2-2026", counter="FACT-Q2-26-REV"), "medium"),
            "cash_flow_effect": {
                "text_template": "自由现金流从上一季度 {prior_fcf} 降至 {current_fcf}，资本开支几乎吞掉了当期经营现金创造。",
                "value_refs": {"prior_fcf": {"path": "/facts/FACT-Q1-26-FCF/value", "format": "number"}, "current_fcf": {"path": "/facts/FACT-Q2-26-FCF/value", "format": "number"}},
                "evidence_refs": _ev("FACT-Q1-26-FCF", "FACT-Q2-26-FCF"), "confidence": "high",
            },
            "valuation_effect": _text("因此估值不能简单年化历史自由现金流，而应围绕利润率恢复、资本开支稳定和每股收益增长建立情景。", _ev("BUNDLE:/decision/valuation/base_irr", counter="BUNDLE:/scenarios/bull/returns/irr/irr_pct"), "high"),
        },
        "mirror_test": [
            _text("这门生意的本质是用 Facebook、Instagram、WhatsApp 和 Reels 聚合注意力，再通过广告系统将注意力变现。", _ev("SRC-META-USERS", "FACT-Q2-26-REV"), "high"),
            _text("护城河来自关系链、内容供给、广告主需求和人工智能推荐形成的多边反馈闭环。", _ev("SRC-META-USERS", counter="SRC-PEERS"), "high"),
            {"text_template": "当前 Base IRR 仅为 {irr}，现价没有提供足够的新增资金回报。", "value_refs": {"irr": {"path": "/decision/valuation/base_irr", "format": "percent"}}, "evidence_refs": _ev("BUNDLE:/decision/valuation/base_irr"), "confidence": "high"},
            _text("最大风险不是广告业务突然消失，而是人工智能资本开支长期无法转化为更高利润和自由现金流。", _ev("FACT-Q2-26-FCF", "SRC-META-Q2-2026", counter="FACT-Q2-26-REV"), "high"),
            {"text_template": "因此新资金动作是 {new_action}，已有仓位动作是 {existing_action}。", "value_refs": {"new_action": {"path": "/decision/new_money_action", "format": "text"}, "existing_action": {"path": "/decision/existing_position_action", "format": "text"}}, "evidence_refs": _ev("BUNDLE:/decision/new_money_action", "BUNDLE:/decision/existing_position_action"), "confidence": "high"},
        ],
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

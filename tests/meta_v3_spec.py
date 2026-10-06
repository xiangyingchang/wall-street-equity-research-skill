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
    spec["research"]["overview"]["business_model"] = node(
        "用户免费使用社交与内容应用，广告主为精准曝光付费；推荐系统和关系链共同决定广告转化效率。",
        [ev("SRC-META-USERS"), ev("SRC-META-Q2-2026")], "估值取决于广告效率能否覆盖不断上升的基础设施投入。", "high")
    spec["research"]["overview"]["earnings_update"] = {
        "period": node("二零二六年第二季度业绩与用户指标补充材料", [ev("SRC-META-Q2-2026")], "这是本报告依据的最新财报。", "high"),
        "changed": node("最新季度自由现金流明显下降，资本开支第一次成为股东回报的主要约束。", [ev("FACT-Q2-26-FCF"), ev("SRC-META-Q2-2026")], "估值不能再沿用历史自由现金流峰值。", "high"),
        "unchanged": node("收入需求没有出现结构性衰退，广告主业仍是利润与现金的核心来源。", [ev("FACT-Q2-26-REV"), ev("SRC-META-USERS")], "争议在资本回报而不在主业需求。", "high"),
    }
    spec["research"]["positioning"]["existing_position"]["text"] = "估值层给出降低暴露候选，但持仓状态、当前权重和目标权重缺失时只能复核。"
    spec["research"]["positioning"]["portfolio_constraints"]["text"] = "真实持仓权重、目标权重、税费和替代资产质量共同决定能否执行调整。"
    spec["research"]["final_verdict"]["falsification"]["text"] = "若增量资本开支带来可持续的利润率恢复和自由现金流增长，当前谨慎结论需要重新评估。"
    spec["research"]["final_verdict"]["falsification"]["implication"] = "相反，资本开支继续增长而回报不改善，将强化降低暴露的研究候选。"
    add_v32_decision_support(spec)
    research = spec["research"]
    research["growth_limits"]["ceiling"] = tnode(
        "Base IRR 只有 {base}，而乐观情景也需要经营杠杆重新出现才能越过门槛 {target}。",
        {"base": {"path": "/decision/valuation/base_irr", "format": "percent"}, "target": {"path": "/target_return", "format": "percent"}},
        [ev("BUNDLE:/decision/valuation/base_irr"), ev("SRC-META-Q2-2026")], "可持续增长上限取决于商业化效率能否快于资本成本上升。")
    comparators = research["opportunity_cost"]["comparators"]
    comparators[1] = {"claim_template": "股票最低目标回报 {target} 是决策门槛，而不是可直接购买的资产。",
                      "value_refs": {"target": {"path": "/target_return", "format": "percent"}},
                      "evidence_refs": ["BUNDLE:/target_return"], "implication": "不得把门槛伪装成低风险替代品。", "confidence": "high"}
    comparators[3] = {"claim_template": "同业比较之前，本公司 Base IRR 为 {base}，需先跟同业的增长质量和资本强度对照。",
                      "value_refs": {"base": {"path": "/decision/valuation/base_irr", "format": "percent"}},
                      "evidence_refs": ["SRC-PEER", "BUNDLE:/decision/valuation/base_irr"], "implication": "机会成本应同时考虑质量和估值。", "confidence": "medium"}
    return spec


def _fx(value: str, unit: str, source_id: str, period: str, source: str) -> dict[str, Any]:
    return {"value": value, "unit": unit, "period": period, "source": source, "tier": "Tier 1", "confidence": "high", "source_ids": [source_id]}


def tnode(template: str, values: dict[str, Any], refs: list[dict[str, str]], implication: str, confidence: str = "medium") -> dict[str, Any]:
    return {"text_template": template, "value_refs": values, "evidence_refs": refs, "implication": implication, "confidence": confidence}


def add_v32_decision_support(spec: dict[str, Any]) -> None:
    """v3.2 fixture data: cash valuation, price ladder, history, bridges, triggers, pre-mortem."""
    facts = spec["facts"]
    spec["sources"]["SRC-META-10K-2025"] = {
        "title": "Meta Platforms 2025 Form 10-K", "publisher": "U.S. Securities and Exchange Commission", "date": "2026-01-29",
        "tier": 1, "document_type": "annual-report", "locator": "Item 7 MD&A and Item 8 consolidated statements, fiscal 2021-2025",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001326801&type=10-K",
        "scope": ["revenue", "operating income", "fcf", "capex", "research and development"],
    }
    q2 = "SRC-META-Q2-2026"
    facts.update({
        "FACT-SHARES-OUTSTANDING": _fx("25.20", "100m shares", q2, "2026-07-24", "Meta 10-Q cover page shares outstanding"),
        "FACT-DPS-ANNUALIZED": _fx("2.10", "USD/share", q2, "Q2 2026", "Meta quarterly dividend annualized"),
        "FACT-Q2-26-CAPEX": _fx("190.00", "USD bn/10", q2, "Q2 2026", "Meta 8-K capital expenditures"),
        "FACT-Q2-26-RND": _fx("150.00", "USD bn/10", q2, "Q2 2026", "Meta 8-K research and development"),
        "FACT-Q2-26-CASH-NET": _fx("420.00", "USD bn/10", q2, "Q2 2026", "Meta 8-K cash and marketable securities less debt"),
        "FACT-Q2-26-BUYBACK": _fx("60.00", "USD bn/10", q2, "Q2 2026", "Meta 8-K share repurchases"),
        "FACT-Q2-26-SBC": _fx("45.00", "USD bn/10", q2, "Q2 2026", "Meta 8-K share-based compensation"),
    })
    k10 = "SRC-META-10K-2025"
    facts.update({
        "FACT-FY2024-EQUITY": _fx("1826.37", "USD bn/10", k10, "FY2024", "Meta 10-K total stockholders equity"),
        "FACT-FY2025-EQUITY": _fx("2170.00", "USD bn/10", k10, "FY2025", "Meta 10-K total stockholders equity"),
        "FACT-FY2024-DEBT": _fx("288.26", "USD bn/10", k10, "FY2024", "Meta 10-K long-term debt"),
        "FACT-FY2025-DEBT": _fx("289.00", "USD bn/10", k10, "FY2025", "Meta 10-K long-term debt"),
        "FACT-FY2024-CASH-SEC": _fx("778.15", "USD bn/10", k10, "FY2024", "Meta 10-K cash and marketable securities"),
        "FACT-FY2025-CASH-SEC": _fx("815.00", "USD bn/10", k10, "FY2025", "Meta 10-K cash and marketable securities"),
    })
    annual = {
        "REV": ["1179.29", "1166.09", "1349.02", "1645.01", "2009.66"],
        "OI": ["467.53", "288.44", "467.51", "693.80", "832.76"],
        "FCF": ["389.93", "190.44", "430.10", "521.02", "440.00"],
    }
    years = ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
    for metric, values in annual.items():
        for year, value in zip(years, values):
            facts[f"FACT-{year}-{metric}"] = _fx(value, "USD bn/10", "SRC-META-10K-2025", year, "Meta Form 10-K")
    spec["assumptions"]["ASM-DIVIDEND-GROWTH"] = {"scope": "global", "role": "dividend_growth", "value": "0.05", "rationale": "股息随盈利温和增长。", "confidence": "medium"}
    spec["assumptions"]["ASM-DIVIDEND-WITHHOLDING"] = {"scope": "global", "role": "withholding_tax", "value": "0.10", "rationale": "中美税收协定下美股股息预扣税。", "confidence": "high"}
    spec["report"]["cash_valuation"] = {
        "shares_fact_id": "FACT-SHARES-OUTSTANDING",
        "earnings_bases": [{"basis_id": "gaap", "label": "GAAP 摊薄 EPS", "accounting_basis": "reported", "eps_fact_ids": spec["quarterly_series"]["eps"]}],
        "decisive_basis": "fcf",
        "decisive_reason": "资本开支高峰期利润表高估股东可得现金，满仓新资金必须由自由现金流口径过门槛。",
        "fcf_label": "自由现金流",
        "dividend": {"dps_fact_id": "FACT-DPS-ANNUALIZED", "growth_assumption_id": "ASM-DIVIDEND-GROWTH", "withholding_assumption_id": "ASM-DIVIDEND-WITHHOLDING", "years": 5},
    }
    spec["decision_policy"]["price_ladder"] = {
        "watch_trial_cap": "0.25",
        "tiers": [
            {"tier_id": "no-chase", "action": "不新增", "floor_ref": "BUNDLE:/scenarios/base/prices/target_return", "position_min": "0", "position_max": "0"},
            {"tier_id": "trial", "action": "试探建仓", "floor_ref": "BUNDLE:/scenarios/base/prices/buy", "position_min": "0", "position_max": "0.25"},
            {"tier_id": "build", "action": "分批建仓", "floor_ref": "BUNDLE:/derived/cash_valuation/decisive/confirmation_price", "position_min": "0.25", "position_max": "0.60"},
            {"tier_id": "full", "action": "接近目标仓", "position_min": "0.60", "position_max": "1"},
        ],
    }
    for index, (probability, impact, action) in enumerate([
        ("medium_high", "high", "资本开支指引再上调时暂停新增资金并重算现金口径估值。"),
        ("medium", "medium_high", "广告增速跌破经营闸门时把已有仓位转入复核。"),
        ("low_medium", "high", "出现直接限制定向广告的新规时重估退出倍数。"),
    ]):
        spec["research"]["risks"]["items"][index].update({"probability": probability, "impact": impact, "action": action})
    spec["research"]["risks"]["items"].extend([
        {"rank": 4, "risk": "股权激励稀释抵消回购，每股价值增长低于利润增长。", "mechanism": "股权激励是真实成本，回购缩量后股本不再下降。",
         "leading_indicators": ["季度回购金额连续两个季度下降。", "股权激励费用占收入比例持续上升。"], "trigger": "稀释后股本同比转为上升。",
         "mitigant": "利润规模足以同时覆盖投资与回购。", "evidence_refs": [ev("FACT-Q2-26-SBC"), ev("FACT-Q2-26-BUYBACK")], "confidence": "medium",
         "probability": "low_medium", "impact": "medium", "action": "用稀释后股本复算每股自由现金流再决定是否加仓。"},
        {"rank": 5, "risk": "新业务亏损长期化，现实实验室持续吞噬广告利润。", "mechanism": "长期亏损部门把集团利润率压在低位，市场给予更低倍数。",
         "leading_indicators": ["现实实验室部门季度亏损继续扩大。", "管理层不给出新业务亏损收窄时间表。"], "trigger": "新业务亏损同比扩大且广告利润率同步下滑。",
         "mitigant": "管理层已多次控制新业务开支节奏。", "evidence_refs": [ev("SRC-META-Q2-2026"), ev("FACT-Q2-26-OI")], "confidence": "medium",
         "probability": "medium", "impact": "medium", "action": "下调 Base 利润率假设并重新编译价格阶梯。"},
    ])
    fcf_row = "/derived/cash_valuation/fcf"
    spec["decision_support"] = {
        "valuation": {
            "cash_interpretation": tnode("自由现金流收益率只有 {fcf_yield}，远低于门槛 {target}；只有回到现金确认价 {confirm} 附近，现金口径才单独支持买入。",
                                         {"fcf_yield": {"path": f"{fcf_row}/yield", "format": "percent"}, "target": {"path": "/target_return", "format": "percent"},
                                          "confirm": {"path": "/derived/cash_valuation/cash_confirmation_price", "format": "price"}},
                                         [ev(f"BUNDLE:{fcf_row}/yield"), ev("BUNDLE:/target_return")], "现金口径比盈利口径更严，资本开支回落前不能用利润倍数替代。"),
            "peers": [
                {"name": "Alphabet", "basis": "reported", "metric": "TTM 市盈率", "value": "22.5", "source_id": "SRC-PEER", "as_of": "2026-07-31", "judgement": "同为广告平台，资本开支同样上升。"},
                {"name": "Amazon", "basis": "reported", "metric": "TTM 市盈率", "value": "34.0", "source_id": "SRC-PEER", "as_of": "2026-07-31", "judgement": "零售与云混合，倍数不完全可比。"},
                {"name": "Snap", "basis": "market", "metric": "EV/Sales", "value": "3.1", "format": "number", "source_id": "SRC-PEER", "as_of": "2026-07-31", "judgement": "仍亏损，只能用销售倍数比较。"},
            ],
            "peer_interpretation": node("同业倍数说明市场仍给广告平台质量溢价，但同业也在加大资本开支，相对便宜不等于绝对便宜。",
                                        [ev("SRC-PEER"), ev("BUNDLE:/derived/cash_valuation/bases/0/multiple")], "同业对比只作参照，不改变绝对回报门槛。"),
        },
        "scenario_premises": {
            "bull": node("广告单价与展示量同步增长，资本开支在明年见顶，自由现金流利润率恢复到历史中枢。", [ev("BUNDLE:/scenarios/bull/returns/irr/irr_pct")], "需要连续两个季度的财报确认。"),
            "base": node("广告保持中双位数增长，资本开支维持高位但不再上调，利润率小幅回落后企稳。", [ev("BUNDLE:/scenarios/base/returns/irr/irr_pct")], "这是当前定价与决策的主要锚点。"),
            "bear": node("广告增速回落到个位数，资本开支继续上调，自由现金流长期低于净利润。", [ev("BUNDLE:/scenarios/bear/returns/irr/irr_pct")], "这是资本强度永久上升的压力情形。"),
        },
        "financial_history": {
            "years": years,
            "metrics": [
                {"label": "收入", "fact_ids": [f"FACT-{y}-REV" for y in years]},
                {"label": "经营利润", "fact_ids": [f"FACT-{y}-OI" for y in years]},
                {"label": "自由现金流", "fact_ids": [f"FACT-{y}-FCF" for y in years]},
            ],
            "interpretation": node("收入和经营利润五年间显著增长，但自由现金流在最近一年先于利润回落，资本开支开始吞噬现金。",
                                   [ev("FACT-FY2025-FCF"), ev("FACT-FY2025-OI"), ev("SRC-META-10K-2025")], "趋势支持主业质量，但不支持按历史现金流外推。"),
        },
        "normalization": [
            {"layer": "reported", "label": "TTM GAAP 每股盈利", "value_refs": [{"ref": "BUNDLE:/derived/cash_valuation/bases/0/per_share_reporting", "unit": "USD/share"}],
             "note": node("报表口径包含一次性法律费用和重组费用。", [ev("FACT-Q2-26-EPS")], "直接使用会低估公司的常态盈利。")},
            {"layer": "adjusted", "label": "TTM 自由现金流", "value_refs": ["FACT-Q2-26-FCF", {"ref": "BUNDLE:/derived/ttm/fcf/value", "unit": "USD bn/10", "caption": "TTM"}],
             "note": node("现金口径扣除资本开支，最能反映股东可得现金。", [ev("FACT-Q2-26-FCF")], "资本开支高峰期的现金流会低于常态。")},
            {"layer": "normalized", "label": "常态化经营利润", "value_refs": ["FACT-Q2-26-OI"], "method": "以单季经营利润为起点，剔除一次性法律与重组费用后再外推。",
             "note": node("剔除一次性费用后的经营利润才可以外推，但仍要扣除更高的折旧。", [ev("FACT-Q2-26-OI")], "外推未来盈利时以该口径为起点。")},
        ],
        "capex_balance": [
            {"category": "capex", "label": "单季资本开支", "value_refs": ["FACT-Q2-26-CAPEX"], "note": node("资本开支是现金流压缩的主因。", [ev("FACT-Q2-26-CAPEX")], "资本开支回落之前现金口径估值受压。")},
            {"category": "rnd", "label": "单季研发", "value_refs": ["FACT-Q2-26-RND"], "note": node("研发投入维持高位以支撑模型训练。", [ev("FACT-Q2-26-RND")], "研发是经营成本，不能当成资本化投入看待。")},
            {"category": "balance_sheet", "label": "净现金", "value_refs": ["FACT-Q2-26-CASH-NET"], "note": node("净现金充足，足以支撑投入周期。", [ev("FACT-Q2-26-CASH-NET")], "资产负债表不是当前投资判断的约束。")},
            {"category": "shareholder_return", "label": "单季回购", "value_refs": ["FACT-Q2-26-BUYBACK"], "note": node("回购规模随现金流收缩而放缓。", [ev("FACT-Q2-26-BUYBACK")], "每股价值增长将更依赖利润本身。")},
            {"category": "sbc", "label": "单季股权激励", "value_refs": ["FACT-Q2-26-SBC"], "note": node("股权激励是真实成本，需从调整后利润中扣回。", [ev("FACT-Q2-26-SBC")], "调整后口径不能忽略股权稀释。")},
            {"category": "shares", "label": "已发行股本", "value_refs": ["FACT-SHARES-OUTSTANDING"], "note": node("市值按披露日已发行股本计算，不使用情景假设。", [ev("FACT-SHARES-OUTSTANDING")], "股本变化会直接影响每股价值。")},
        ],
        "ladder_premises": {
            "no-chase": node("现价高于目标回报价，任何经营改善都不足以补偿机会成本。", [ev("BUNDLE:/scenarios/base/prices/target_return")], "这一档只观察，不新增任何资金。"),
            "trial": {**node("经营闸门全部支持持有，且资本开支指引没有再上调。", [ev("BUNDLE:/decision/operating/status")], "两项条件满足后才可以试探建仓。"),
                      "conditions": [{"label": "经营闸门", "ref": "BUNDLE:/decision/operating/status", "operator": "==", "threshold": "hold"},
                                     {"label": "资本开支指引不再上调", "status": "unknown", "pending": "下一季财报指引"}]},
            "build": {**node("在试探条件之外，单季自由现金流恢复为明显正值。", [ev("FACT-Q2-26-FCF")], "现金流证据到位之后再分批买入。"),
                      "conditions": [{"label": "经营闸门", "ref": "BUNDLE:/decision/operating/status", "operator": "==", "threshold": "hold"},
                                     {"label": "单季自由现金流", "ref": "FACT-Q2-26-FCF", "unit": "USD bn/10", "operator": ">=", "threshold": "50"}]},
            "full": {**node("资本开支见顶得到确认，且广告增速没有跌破经营闸门。", [ev("SRC-META-Q2-2026")], "两项同时满足才可以接近目标仓位。"),
                     "conditions": [{"label": "单季自由现金流", "ref": "FACT-Q2-26-FCF", "unit": "USD bn/10", "operator": ">=", "threshold": "100"},
                                    {"label": "资本开支见顶", "status": "unknown", "pending": "管理层全年资本开支指引"}]},
        },
        "action_triggers": [
            {"category": "price", "condition": tnode("股价跌破安全边际价 {buy}。", {"buy": {"path": "/price_ladder/buy_price", "format": "price"}}, [ev("BUNDLE:/price_ladder/buy_price")], "价格只是必要条件，不是充分条件。"), "action": "按价格阶梯分批，不一次性买满。", "existing_action": "NONE"},
            {"category": "valuation", "condition": tnode("Base IRR 低于门槛 {target} 且缺口扩大。", {"target": {"path": "/target_return", "format": "percent"}}, [ev("BUNDLE:/decision/valuation/irr_gap")], "估值缺口是减仓候选动作的来源。"), "action": "已有仓位进入复核，确认权重后再决定是否减仓。", "existing_action": "REVIEW"},
            {"category": "operating", "condition": node("经营闸门任一指标跌破降低暴露阈值。", [ev("BUNDLE:/decision/operating/status")], "经营恶化的优先级高于价格信号。"), "action": "暂停新增资金并重算 Base 情景。", "existing_action": "REVIEW"},
            {"category": "cash_flow", "condition": node("单季自由现金流连续两个季度接近零或为负。", [ev("FACT-Q2-26-FCF")], "现金流是资本回报最直接的证据。"), "action": "下调现金口径估值并收紧价格阶梯。", "existing_action": "REVIEW"},
            {"category": "thesis_break", "condition": node("投资逻辑破坏条件全部满足。", [ev("BUNDLE:/decision/thesis_break/triggered")], "逻辑破坏优先于一切估值信号。"), "action": "确认真实持仓后退出，价格阶梯整体暂停。", "existing_action": "SELL"},
        ],
        "cash_flow_escalation": {
            "counter_ref": "FACT-CONSECUTIVE-CAPEX-Q",
            "counter_label": "连续高资本开支季度数",
            "levels": [
                {"min_count": 1, "new_money_cap": "0.25", "action": "新资金最多试探仓，等待下一季现金流。"},
                {"min_count": 2, "new_money_cap": "0.10", "action": "新资金压到观察仓，重算现金口径估值。"},
                {"min_count": 3, "new_money_cap": "0.05", "action": "新资金基本停止，已有仓位进入复核。"},
                {"min_count": 4, "new_money_cap": "0", "action": "停止新资金，按投资逻辑破坏处理已有仓位。"},
            ],
        },
        "roic": {
            "years": ["FY2024", "FY2025"],
            "operating_income_fact_ids": ["FACT-FY2024-OI", "FACT-FY2025-OI"],
            "tax_rate_ref": "ASM-GLOBAL-TAX",
            "invested_capital": [
                {"label": "股东权益", "sign": 1, "fact_ids": ["FACT-FY2024-EQUITY", "FACT-FY2025-EQUITY"]},
                {"label": "有息负债", "sign": 1, "fact_ids": ["FACT-FY2024-DEBT", "FACT-FY2025-DEBT"]},
                {"label": "现金及有价证券", "sign": -1, "fact_ids": ["FACT-FY2024-CASH-SEC", "FACT-FY2025-CASH-SEC"]},
            ],
            "method": "经营利润按全局税率折算税后，投入资本取权益加有息负债减现金及有价证券。",
            "interpretation": node("整体回报仍高，但增量资本回报才是检验人工智能投入是否值得的指标。", [ev("FACT-FY2025-OI"), ev("FACT-FY2025-EQUITY")], "增量回报持续低于门槛时不应给资本开支估值溢价。"),
        },
        "pre_mortem": {
            "failure_path": node("资本开支持续上调而广告增长放缓，自由现金流长期低迷，市场把公司重估为资本密集型平台。", [ev("FACT-Q2-26-FCF"), ev("SRC-META-Q2-2026")], "这是这笔投资最可能的亏损路径。"),
            "analysis_error": node("最危险的错误是把模型排名和用户参与度当成现金回报的证据。", [ev("SRC-META-USERS")], "只有现金流和利润率能验证投入回报。"),
            "early_signals": ["公司把全年资本开支指引再次上调。", "广告展示量增长但平均单价持续下降。"],
        },
        "liquidity": node("美股大盘股流动性充足，正常仓位规模不构成执行约束。", [ev("SRC-YAHOO-PRICE")], "执行风险主要来自财报跳空而不是成交量。"),
        "review_checklist": [
            "资本开支指引是否再次上调，单季自由现金流是否恢复为正。",
            "广告增速和经营利润率是否仍高于经营闸门。",
            "现价落在价格阶梯哪一档，组合权重是否已确认。",
        ],
    }


def write_spec(path: Path, spec: dict[str, Any] | None = None) -> None:
    path.write_text(json.dumps(make_spec() if spec is None else spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_spec(args.output)

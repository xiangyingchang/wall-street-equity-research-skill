from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

BASE = Path(__file__).parent / "fixtures" / "meta_v2_spec.json"


def _c(text: str, refs: list[str], implication: str = "该判断会影响估值或动作。", confidence: str = "medium") -> dict[str, Any]:
    return {"claim": text, "evidence_refs": refs, "implication": implication, "confidence": confidence}


def _t(text: str, refs: list[str], implication: str = "该判断会影响估值或动作。", confidence: str = "medium") -> dict[str, Any]:
    return {"text": text, "evidence_refs": refs, "implication": implication, "confidence": confidence}


def make_spec() -> dict[str, Any]:
    spec = json.loads(BASE.read_text(encoding="utf-8"))
    spec["schema_version"] = "report-spec-v2.1"
    spec["sources"] = {
        "SRC-META-Q3-2025": {"title": "Meta Reports Third Quarter Results", "publisher": "Meta Investor Relations", "date": "2025-10-29", "tier": 1, "document_type": "earnings-release", "locator": "Q3 2025 results and filing index", "url": "https://investor.atmeta.com/financials/", "scope": ["revenue", "operating income", "eps", "fcf"]},
        "SRC-META-Q4-2025": {"title": "Meta Reports Fourth Quarter and Full Year Results", "publisher": "Meta Investor Relations", "date": "2026-01-28", "tier": 1, "document_type": "earnings-release", "locator": "Q4 and FY2025 results and filing index", "url": "https://investor.atmeta.com/financials/", "scope": ["revenue", "operating income", "eps", "fcf"]},
        "SRC-META-Q1-2026": {"title": "Meta Reports First Quarter Results", "publisher": "Meta Investor Relations", "date": "2026-04-29", "tier": 1, "document_type": "earnings-release", "locator": "Q1 2026 results and filing index", "url": "https://investor.atmeta.com/financials/", "scope": ["revenue", "operating income", "eps", "fcf"]},
        "SRC-META-Q2-2026": {"title": "Meta Reports Second Quarter Results", "publisher": "Meta Investor Relations", "date": "2026-07-30", "tier": 1, "document_type": "earnings-release", "locator": "Q2 2026 results and filing index", "url": "https://investor.atmeta.com/financials/", "scope": ["revenue", "operating income", "eps", "fcf", "capex"]},
        "SRC-META-USERS": {"title": "Meta Quarterly User and Engagement Metrics", "publisher": "Meta Investor Relations", "date": "2026-07-30", "tier": 1, "document_type": "earnings-supplement", "locator": "Q2 2026 user and engagement metrics supplement", "url": "https://investor.atmeta.com/financials/", "scope": ["users", "engagement", "advertising"]},
        "SRC-US-TREASURY": {"title": "Daily Treasury Par Yield Curve Rates", "publisher": "United States Treasury", "date": "2026-07-31", "tier": 1, "document_type": "market-rate", "locator": "Daily Treasury par yield curve table", "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve", "scope": ["risk-free rate"]},
        "SRC-YAHOO-PRICE": {"title": "Meta Platforms Market Quote", "publisher": "Yahoo Finance", "date": "2026-07-31", "tier": 2, "document_type": "market-data", "locator": "META historical quote and close", "url": "https://finance.yahoo.com/quote/META/", "scope": ["current price"]},
        "SRC-INDEX": {"title": "S&P 500 Index", "publisher": "S&P Dow Jones Indices", "date": "2026-07-31", "tier": 2, "document_type": "benchmark", "locator": "S&P 500 index overview and factsheet", "url": "https://www.spglobal.com/spdji/en/indices/equity/sp-500/", "scope": ["opportunity cost"]},
        "SRC-PEER": {"title": "Alphabet SEC Filing Index", "publisher": "U.S. Securities and Exchange Commission", "date": "2026-07-31", "tier": 1, "document_type": "peer-filings", "locator": "Alphabet 10-K and 10-Q filing index", "url": "https://www.sec.gov/edgar/browse/?CIK=1652044&owner=exclude", "scope": ["peer comparison"]}
    }
    period_source = {
        "Q3 2025": "SRC-META-Q3-2025",
        "Q4 2025": "SRC-META-Q4-2025",
        "Q1 2026": "SRC-META-Q1-2026",
        "Q2 2026": "SRC-META-Q2-2026",
    }
    for fact_id, fact in spec["facts"].items():
        if fact_id == "FACT-CURRENT-PRICE":
            fact["source_ids"] = ["SRC-YAHOO-PRICE"]
        else:
            fact["source_ids"] = [period_source.get(fact.get("period", fact.get("as_of", "Q2 2026")), "SRC-META-Q2-2026")]

    spec["research"] = {
        "overview": {
            "thesis": _t("广告主业仍具备高质量现金创造能力，但资本开支能否转化为可验证的增量回报，是当前估值的决定性矛盾。", ["FACT-Q2-26-REV", "FACT-Q2-26-FCF", "BUNDLE:decision.valuation.base_irr"], "现价下不应把主业质量直接等同于足够的预期回报。"),
            "key_forces": [
                _c("广告收入与商业化效率仍是利润和现金流的核心来源。", ["FACT-Q1-26-REV", "FACT-Q2-26-REV", "SRC-META-USERS"], "若广告效率延续，利润底盘仍有支撑。", "high"),
                _c("基础设施投入和折旧压力正在显著改变自由现金流的时间分布。", ["FACT-Q1-26-FCF", "FACT-Q2-26-FCF", "SRC-META-Q2-2026"], "估值必须关注资本回报而非只看收入增长。"),
                _c("当前价格隐含的回报要求高于基础情景能够提供的水平。", ["BUNDLE:scenarios.base.returns.irr.irr_pct", "BUNDLE:target_return", "BUNDLE:scenarios.base.prices.target_return"], "新资金应等待更好的价格或更强的经营证据。")
            ],
            "variant_view": _t("市场可能低估人工智能投入对广告推荐、创意生成和新产品商业化的长期价值。", ["SRC-META-USERS", "SRC-META-Q2-2026", "BUNDLE:scenarios.bull.returns.irr.irr_pct"], "若增量收入和利润率兑现，悲观的现金流视角会低估长期价值。", "low")
        },
        "financial_autopsy": {
            "revenue": _t("收入趋势仍然强劲，主业并未显示需求层面的结构性衰退。", ["FACT-Q3-25-REV", "FACT-Q4-25-REV", "FACT-Q1-26-REV", "FACT-Q2-26-REV"], "估值争议来自资本强度，而不是收入崩塌。", "high"),
            "margin": _t("滚动经营利润率仍保持较高水平，但最新季度出现明显压缩。", ["FACT-Q3-25-OI", "FACT-Q4-25-OI", "FACT-Q1-26-OI", "FACT-Q2-26-OI", "BUNDLE:derived.ttm.operating_margin.value_pct"], "基础情景必须给折旧和研发投入留下足够空间。"),
            "cash_flow": _t("最新季度自由现金流骤降，说明资本开支已经成为股东回报的主要约束。", ["FACT-Q1-26-FCF", "FACT-Q2-26-FCF", "SRC-META-Q2-2026"], "短期不应使用历史自由现金流峰值直接估值。"),
            "one_offs": _t("税务与重组等一次性项目会扰动单季每股收益，长期模型应优先依赖经营桥接。", ["FACT-Q3-25-EPS", "FACT-Q1-26-EPS", "SRC-META-Q3-2025", "SRC-META-Q1-2026"], "前瞻每股收益需要由收入、利润率、税率和股数共同推导。")
        },
        "moat": {
            "trajectory": "stable",
            "dimensions": [
                {**_c("社交网络的规模和关系链仍构成高迁移成本。", ["SRC-META-USERS"], "用户规模为广告业务提供稳定供给。", "high"), "name": "网络效应与关系链", "score": 5, "counter_evidence": "用户规模成熟后，新增用户对增长的贡献会持续下降。"},
                {**_c("跨产品数据和广告基础设施提升了推荐与商业化效率。", ["SRC-META-USERS", "SRC-META-Q2-2026"], "效率优势有助于维持广告主回报。", "medium"), "name": "数据与广告技术", "score": 5, "counter_evidence": "隐私政策和监管可能削弱数据使用范围。"},
                {**_c("品牌、开发者和广告主生态形成多边平台优势。", ["SRC-META-USERS", "SRC-PEER"], "生态密度提高竞争者复制成本。", "medium"), "name": "生态与分发", "score": 4, "counter_evidence": "短视频和新内容平台仍会争夺用户时长。"},
                {**_c("强资产负债表和现金创造能力支持长期基础设施投入。", ["FACT-Q3-25-FCF", "FACT-Q4-25-FCF", "FACT-Q1-26-FCF"], "资本能力允许公司进行长期竞争。", "high"), "name": "资本与执行能力", "score": 4, "counter_evidence": "资本充足也可能放大低回报投资和管理层过度自信。"}
            ]
        },
        "valuation": {
            "base_case": _t("基础情景假设主业保持增长，但利润率和长期倍数均低于最乐观状态。", ["BUNDLE:scenarios.base.revenue.forward_revenue", "BUNDLE:scenarios.base.eps_bridge.eps", "BUNDLE:scenarios.base.prices.forward_reference"], "该情景适合作为当前决策的主要锚点。"),
            "reverse_expectations": _t("当前价格要求未来每股收益增长显著高于基础情景设定。", ["BUNDLE:scenarios.base.returns.reverse.required_eps_cagr_pct", "BUNDLE:scenarios.base.returns.irr.irr_pct", "BUNDLE:target_return"], "只有更接近乐观情景的经营结果才能覆盖机会成本。"),
            "payback_interpretation": _t("回本压力测试显示，现价需要长期保持较强盈利增长才能覆盖资本成本。", ["BUNDLE:derived.payback_required_growth.0.094", "BUNDLE:derived.payback_required_growth.0"], "回本模型应作为压力测试，而不是单独否决公司质量。"),
            "critical_assumption": _t("最敏感的假设是资本开支之后的利润率恢复与每股收益增长。", ["BUNDLE:scenarios.base.assumption_refs.operating_margin", "BUNDLE:scenarios.base.assumption_refs.eps_cagr", "SRC-META-Q2-2026"], "未来财报应优先验证增量资本回报。")
        },
        "risks": {
            "items": [
                {"rank": 1, "risk": "人工智能基础设施投资回报低于预期。", "mechanism": "高资本开支和折旧持续侵蚀自由现金流与利润率。", "leading_indicators": ["资本开支继续上调而增量收入缺少对应改善。", "折旧增速长期高于收入和经营利润增速。"], "trigger": "资本投入连续多个报告期无法带来经营利润和现金流改善。", "mitigant": "广告推荐效率和新产品商业化可能带来高增量回报。", "evidence_refs": ["FACT-Q2-26-FCF", "SRC-META-Q2-2026"], "confidence": "high"},
                {"rank": 2, "risk": "广告增长和用户时长被竞争者分流。", "mechanism": "用户注意力转移会削弱广告库存和定价能力。", "leading_indicators": ["参与度趋势转弱。", "广告展示和价格同时恶化。"], "trigger": "核心应用参与度与广告效率出现持续性下降。", "mitigant": "产品矩阵和推荐算法仍具备强分发能力。", "evidence_refs": ["SRC-META-USERS", "SRC-PEER"], "confidence": "medium"},
                {"rank": 3, "risk": "监管与平台规则限制数据和商业化能力。", "mechanism": "隐私、反垄断和内容监管可能增加成本并限制产品整合。", "leading_indicators": ["重大诉讼和监管处罚增加。", "关键市场的数据使用规则收紧。"], "trigger": "监管措施直接改变广告定向或产品互操作能力。", "mitigant": "地域和产品多元化可以分散单一政策冲击。", "evidence_refs": ["SRC-META-Q2-2026"], "confidence": "medium"}
            ]
        },
        "growth_limits": {
            "growth_engine": _t("未来增长主要依靠广告变现效率、短视频商业化和新产品，而非单纯用户扩张。", ["SRC-META-USERS", "FACT-Q2-26-REV"], "收入增长将更多取决于每用户价值和产品创新。"),
            "constraints": [
                _c("全球用户规模接近成熟，新增用户对整体增长的边际贡献下降。", ["SRC-META-USERS"], "增长需要更多依靠变现和参与度。"),
                _c("基础设施和折旧提高了实现利润增长所需的资本强度。", ["FACT-Q2-26-FCF", "SRC-META-Q2-2026"], "收入增长不一定等价于股东自由现金流增长。"),
                _c("监管和竞争限制了利润率无限扩张的可能性。", ["SRC-PEER", "SRC-META-Q2-2026"], "长期估值倍数不应建立在持续利润率扩张上。")
            ],
            "ceiling": _t("可持续增长上限取决于商业化效率能否快于资本和监管成本上升。", ["BUNDLE:scenarios.base.returns.irr.irr_pct", "BUNDLE:scenarios.bull.returns.irr.irr_pct", "SRC-META-Q2-2026"], "乐观情景需要经营杠杆重新出现。")
        },
        "opportunity_cost": {
            "interpretation": _t("公司质量较高，但当前基础情景回报低于股票最低目标回报。", ["BUNDLE:scenarios.base.returns.irr.irr_pct", "BUNDLE:target_return"], "持有现有仓位需要确认其相对指数和无风险资产仍有足够补偿。"),
            "comparators": [
                _c("国债收益率是实际可投资的低风险基准。", ["SRC-US-TREASURY"], "股票必须提供额外风险补偿。", "high"),
                _c("股票最低目标回报是决策门槛，而不是可直接购买的资产。", ["BUNDLE:target_return"], "不得把门槛伪装成低风险替代品。", "high"),
                _c("宽基指数提供分散化的权益替代方案。", ["SRC-INDEX"], "单股持仓需要补偿集中度和公司特定风险。"),
                _c("同业公司可用于比较增长质量、资本强度和估值。", ["SRC-PEER"], "机会成本应同时考虑质量和估值。")
            ]
        },
        "positioning": {
            "new_money": _t("新资金不应在当前价格主动买入，应等待目标回报价格或更强的经营证据。", ["BUNDLE:decision.new_money_action", "BUNDLE:scenarios.base.prices.target_return"], "当前优先保留资金选择权。", "high"),
            "existing_position": _t("存量仓位动作由估值回报缺口触发，但减仓幅度仍应结合组合权重和税务成本。", ["BUNDLE:decision.existing_position_action", "BUNDLE:decision.valuation.irr_gap"], "动作是降低机会成本暴露，而不是否定公司长期质量。"),
            "portfolio_constraints": _t("集中度、税费和替代资产质量会影响实际减仓幅度。", ["BUNDLE:decision.existing_position_action", "SRC-INDEX"], "单股研究动作需要在组合层面复核。"),
            "execution": _t("执行应分步完成，并在下一次财报验证现金流、利润率和资本回报。", ["FACT-Q2-26-FCF", "SRC-META-Q2-2026"], "避免因单一季度波动一次性完成全部调整。")
        },
        "final_verdict": {
            "summary": _t("公司主业质量仍强，但现价基础情景回报不足，新增资金应回避，存量仓位应降低机会成本暴露。", ["BUNDLE:decision.new_money_action", "BUNDLE:decision.existing_position_action", "BUNDLE:scenarios.base.returns.irr.irr_pct"], "最终动作来自 Compiler，不接受正文覆盖。", "high"),
            "hold_equals_buy": _t("若今天没有持仓，当前价格不会成为新的主动买入选择。", ["BUNDLE:decision.new_money_action", "BUNDLE:scenarios.base.prices.target_return"], "继续持有必须由组合约束或更高置信度的乐观假设解释。"),
            "opportunity_cost": _t("资本应优先流向风险调整后回报更高且证据更充分的资产。", ["BUNDLE:target_return", "SRC-INDEX", "SRC-US-TREASURY"], "历史成本不能成为继续持有的理由。"),
            "payback": _t("回本测试要求较强的长期盈利增长，说明现价对执行质量要求较高。", ["BUNDLE:derived.payback_required_growth.0.094"], "该结果强化审慎动作但不是单独卖出理由。"),
            "confidence_boundary": _t("结论对资本开支回报、利润率恢复和长期每股收益增长高度敏感。", ["BUNDLE:scenarios.base.assumption_refs.operating_margin", "BUNDLE:scenarios.base.assumption_refs.eps_cagr", "SRC-META-Q2-2026"], "这些变量未被下一轮财报验证前，决策置信度不应标记为最高。"),
            "falsification": _t("若增量资本开支带来可持续的利润率恢复和自由现金流增长，当前减仓结论需要重新评估。", ["FACT-Q2-26-FCF", "BUNDLE:scenarios.bull.returns.irr.irr_pct"], "相反，资本开支继续增长而回报不改善将强化减仓逻辑。")
        }
    }
    return deepcopy(spec)


def write_spec(path: Path) -> None:
    path.write_text(json.dumps(make_spec(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_spec(args.output)

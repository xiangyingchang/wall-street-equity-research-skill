"""Present a verified v3 compiler Reader as one report with a full appendix."""
from __future__ import annotations

import re
from typing import Any

from scripts.report_renderer_readable_v212 import (
    _claim_text, _fx_note, _money, _pct_decimal, _price_currency, _source_note,
)
from scripts.report_renderer_v3 import _action, _assumption, _format_assumption, _portfolio_limit, _price_guidance


READING_ORDER = "> 阅读顺序：先看当前动作和价格，再看经营证据、估值和仓位复核条件。完整底稿与执行规则见附录。"
SECTIONS = (
    "1. 现在怎么做",
    "2. 经营证据",
    "3. 估值",
    "4. 什么会改变仓位判断",
    "5. 附录｜财务底稿、估值明细与执行规则",
)


def split_report(markdown: str) -> tuple[str, str]:
    """Recover the original compiler Reader from the appendix for lint and verification."""
    body, separator, appendix = markdown.partition(f"\n## {SECTIONS[-1]}\n\n")
    if not separator or not appendix:
        return markdown, ""
    title = markdown.split("\n", 1)[0]
    return body, title + "\n\n" + re.sub(r"^#(#{2,5} )", r"\1", appendix, flags=re.M)


def _operating_evidence(bundle: dict[str, Any]) -> list[str]:
    business_model = bundle["research"]["overview"].get("business_model")
    lines = []
    if business_model:
        lines.extend([_claim_text(business_model), ""])
        lines += _source_note(bundle, [business_model])
    for theme in bundle["research_graph"]["themes"]:
        evidence = [*theme["observations"], theme["resolution"], theme["challenge"]]
        lines.extend([" ".join(dict.fromkeys(_claim_text(item) for item in evidence)), ""])
        lines += _source_note(bundle, evidence)
    return lines


def _valuation(bundle: dict[str, Any]) -> list[str]:
    report = bundle["report"]
    currency = _price_currency(report)
    assumptions = {role: _format_assumption(role, _assumption(bundle, role)[1])
                   for role in ("eps_cagr", "exit_pe", "dividend_yield")}
    coherence = bundle["decision_coherence"]
    cash = coherence["decisive"]
    lines = [
        f"基础情景假设每股收益年增长 {assumptions['eps_cagr']}，"
        f"持有 {report['return_years']} 年后按 {assumptions['exit_pe'].removesuffix('x')} 倍市盈率卖出。"
        f"模型按 {assumptions['dividend_yield']} 的股息率估算分红，"
        "反推价格时维持股息率。模型把历年股息直接相加，与卖出所得一起计入期末，再按持有年限算年化回报。", "",
    ]
    if coherence["escalation"].get("status") == "unknown":
        lines.extend(["最新现金流尚未核实。历史现金口径与待核实项目见附录。", ""])
    else:
        lines.extend([
            f"按{cash['label']}计算，参考股价对应的收益率为 {_pct_decimal(cash['yield'])}，"
            f"最低要求为 {_pct_decimal(bundle['target_return'])}。", "",
        ])
        if cash.get("confirmation_price") is not None:
            lines.extend([
                f"按这一口径，股价不高于 {_money(cash['confirmation_price'], currency)} 时，收益率达到门槛。"
                "实际下单仍须满足附录列出的执行条件。", "",
            ])
    return lines


def _recheck_conditions(bundle: dict[str, Any]) -> list[str]:
    final = bundle["research"]["final_verdict"]
    conditions = [final["falsification"], *(theme["falsification"] for theme in bundle["research_graph"]["themes"])]
    return [
        *(f"- {condition}" for condition in dict.fromkeys(_claim_text(item) for item in conditions)),
        "",
        "价格进入可考虑的区间时，重算回报并复核经营和仓位条件。具体执行条件见附录的行动表。", "",
    ]


def render_readable_markdown(bundle: dict[str, Any], compiler_reader: str) -> str:
    title, appendix = compiler_reader.split("\n\n", 1)
    decision = bundle["decision"]
    coherence = bundle["decision_coherence"]
    valuation = decision["valuation"]
    cap = float(coherence["executable_position_max"]) * 100
    fx = _fx_note(bundle)
    candidate = _action(decision["existing_position_candidate_action"])
    executable = _action(decision["existing_position_action"])
    candidate_note = f"已有仓位的研究候选为“{candidate}”。" if candidate != executable else ""
    body = [
        title, "", READING_ORDER, "",
        f"## {SECTIONS[0]}", "",
        f"**新资金：{_action(decision['new_money_action'])}。已有仓位：{executable}。** "
        f"{candidate_note}{_portfolio_limit(bundle)}", "",
        f"按基础情景持有 {bundle['report']['return_years']} 年，期末折算年化回报为 "
        f"{_pct_decimal(valuation['base_irr'])}，目标为 {_pct_decimal(valuation['target_return'])}。"
        f"当前新资金最多可用目标仓位的 **{cap:.0f}%**。", "",
        *_price_guidance(bundle),
        "达到价格线后，仍须核对经营和仓位条件。", "",
        *([f"> 计价口径：{fx}", ""] if fx else []),
        f"## {SECTIONS[1]}", "",
        *_operating_evidence(bundle),
        f"## {SECTIONS[2]}", "",
        *_valuation(bundle),
        f"## {SECTIONS[3]}", "",
        *_recheck_conditions(bundle),
        f"## {SECTIONS[4]}", "",
    ]
    appendix = re.sub(r"^(#{2,5} )", r"#\1", appendix, flags=re.M)
    return "\n".join(body) + "\n" + appendix

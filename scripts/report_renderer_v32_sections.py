"""Reader sections for the v3.2 decision-support layer.

Pure formatting: every number comes from the compiled bundle (facts, derived
cash valuation, price ladder) or from validated decision_support text.
"""
from __future__ import annotations

from typing import Any

from scripts.report_renderer_readable_v212 import (
    _absolute_money,
    _claim_text,
    _discount_rate_label,
    _escape,
    _money,
    _paragraph,
    _pct_decimal,
    _price_currency,
    _source_note,
    _ten_year_yield,
)

LEVEL_LABELS = {"low": "低", "low_medium": "低中", "medium": "中", "medium_high": "中高", "high": "高", "very_high": "极高"}
TRIGGER_LABELS = {"price": "价格", "valuation": "估值", "operating": "经营", "cash_flow": "现金流", "thesis_break": "逻辑失效"}
LAYER_LABELS = {"reported": "Reported（报表口径）", "adjusted": "Adjusted（公司调整口径）", "normalized": "Normalized（可外推口径）"}
CATEGORY_LABELS = {
    "capex": "资本开支", "rnd": "研发", "ppe": "固定资产", "balance_sheet": "资产负债表",
    "investments": "投资组合", "shareholder_return": "股东回报", "sbc": "股权激励", "shares": "股本", "other": "其他",
}


def _value(value: Any, unit: str) -> str:
    unit = str(unit or "").strip()
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if unit == "ratio":
        return _pct_decimal(number)
    if unit.endswith(" bn/10"):
        return _absolute_money(number, unit.split(" ")[0])
    if unit.endswith("/share"):
        return _money(number, unit.split("/")[0])
    if unit == "100m shares":
        return f"{number:,.2f}亿股"
    if unit == "quarters":
        return f"{int(number)} 个季度"
    if unit == "multiple":
        return f"{number:.2f}x"
    return f"{number:,.2f} {unit}".strip()


def _cells(values: list[dict[str, Any]]) -> str:
    parts = []
    for item in values:
        text = _value(item["value"], item["unit"])
        parts.append(f"{item['caption']} {text}".strip() if item.get("caption") else text)
    return "；".join(parts)


def _support(bundle: dict[str, Any]) -> dict[str, Any]:
    return bundle["decision_support"]


def history_reader(bundle: dict[str, Any]) -> str:
    history = _support(bundle)["financial_history"]
    years = history["years"]
    lines = [
        f"### {len(years)}年趋势", "",
        "| 指标 | " + " | ".join(years) + " |",
        "|---|" + "---:|" * len(years),
    ]
    for metric in history["metrics"]:
        cells = ["—" if cell is None else _value(cell["value"], cell["unit"]) for cell in metric["cells"]]
        lines.append(f"| {_escape(metric['label'])} | " + " | ".join(cells) + " |")
    lines.extend(["", _paragraph(history["interpretation"]), ""])
    if history.get("limitation"):
        lines.extend([f"> 数据限制：{history['limitation']}", ""])
    return "\n".join(lines)


def normalization_reader(bundle: dict[str, Any]) -> str:
    rows = _support(bundle)["normalization"]
    lines = [
        "### 正常化桥（Reported / Adjusted / Normalized）", "",
        "| 口径 | 项目 | 数值 | 怎么用 |", "|---|---|---|---|",
    ]
    order = {"reported": 0, "adjusted": 1, "normalized": 2}
    for row in sorted(rows, key=lambda x: order[x["layer"]]):
        note = _paragraph(row["note"])
        if row.get("method"):
            note = f"方法：{row['method']} {note}"
        lines.append("| " + " | ".join([
            LAYER_LABELS[row["layer"]], _escape(row["label"]), _escape(_cells(row["values"])), _escape(note),
        ]) + " |")
    lines.append("")
    return "\n".join(lines)


def capex_balance_reader(bundle: dict[str, Any]) -> str:
    rows = _support(bundle)["capex_balance"]
    lines = [
        "### CapEx、研发与资产负债表", "",
        "| 类别 | 项目 | 数值 | 对估值的含义 |", "|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join([
            CATEGORY_LABELS[row["category"]], _escape(row["label"]), _escape(_cells(row["values"])), _escape(_paragraph(row["note"])),
        ]) + " |")
    lines.append("")
    notes = [row["note"] for row in [*rows, *_support(bundle)["normalization"]]]
    notes.append(_support(bundle)["financial_history"]["interpretation"])
    if bundle.get("decision_coherence"):
        notes.append(bundle["decision_coherence"]["roic"]["interpretation"])
    lines += _source_note(bundle, notes)
    return "\n".join(lines)


def financial_extension(bundle: dict[str, Any]) -> str:
    parts = [history_reader(bundle), normalization_reader(bundle)]
    if bundle.get("decision_coherence"):
        parts.append(roic_reader(bundle))
    parts.append(capex_balance_reader(bundle))
    return "\n".join(parts)


def _multiple(value: Any) -> str:
    return "N/A（为负）" if value is None else f"{float(value):.2f}x"


def cash_valuation_reader(bundle: dict[str, Any]) -> str:
    cash = bundle["derived"]["cash_valuation"]
    price_ccy = cash["price_currency"]
    reporting = cash["reporting_currency"]
    current = bundle["facts"][bundle["report"]["current_price_fact_id"]]["value"]
    same = price_ccy == reporting
    header = f"| 口径 | TTM 每股（{reporting}） |" + ("" if same else f" 折合 {price_ccy} |") + " 倍数 | 收益率 | 相对门槛 |"
    lines = [
        "### 现金口径估值", "",
        f"现价 {_money(current, price_ccy)} × 已发行股本 {float(cash['shares_100m']):,.2f}亿股 = 市值 {_absolute_money(cash['market_cap_price_100m'], price_ccy)}"
        + (f"（≈{_absolute_money(cash['market_cap_reporting_100m'], reporting)}）" if not same else "")
        + f"。门槛收益率 {_pct_decimal(cash['target_return'])}。", "",
        header, "|---|---:|" + ("" if same else "---:|") + "---:|---:|---:|",
    ]
    for row in cash["bases"]:
        gap = float(row["hurdle_gap"]) * 100
        cells = [_escape(row["label"]), _money(row["per_share_reporting"], reporting)]
        if not same:
            cells.append(_money(row["per_share_price"], price_ccy))
        cells += [_multiple(row["multiple"]), _pct_decimal(row["yield"]), f"{gap:+.2f} 个百分点"]
        lines.append("| " + " | ".join(cells) + " |")
    fcf = cash["fcf"]
    confirmation = cash.get("cash_confirmation_price")
    verdict = "已达到" if cash["fcf_passes_hurdle"] else "尚未达到"
    line = f"自由现金流收益率 {_pct_decimal(fcf['yield'])}，{verdict}门槛"
    if confirmation is not None:
        line += f"；只用当前 TTM 自由现金流满足门槛，股价需不高于 {_money(confirmation, price_ccy)}（现金确认价）"
    lines.extend(["", line + "。"])
    normalized = cash.get("normalized_fcf")
    if normalized:
        n_confirm = normalized.get("confirmation_price")
        lines.extend(["", f"正常化自由现金流（{_escape(normalized['method'])}）收益率 {_pct_decimal(normalized['yield'])}"
                      + (f"，对应确认价 {_money(n_confirm, price_ccy)}" if n_confirm else "，为负") + "。"])
    decisive = cash.get("decisive")
    if decisive:
        verdict = "已过" if decisive["passes_hurdle"] else "未过"
        confirm = _money(decisive["confirmation_price"], price_ccy) if decisive.get("confirmation_price") else "无（为负）"
        lines.extend(["", f"**决定买点的口径：{_escape(decisive['label'])}**（收益率 {_pct_decimal(decisive['yield'])}，{verdict}门槛；确认价 {confirm}）。{_escape(decisive['reason'])}"])
    lines.extend(["", _paragraph(_support(bundle)["valuation"]["cash_interpretation"]), ""])
    return "\n".join(lines)


def payback_matrix_reader(bundle: dict[str, Any]) -> str:
    cash = bundle["derived"]["cash_valuation"]
    years = cash["payback_years"]
    bases = cash["bases"]
    ten_year = _ten_year_yield(bundle)
    lines = [
        "### 三口径回本测试", "",
        f"同一股价分别用不同盈利/现金口径做 {years} 年回本：数字越高，说明现价对该口径要求的年增长越苛刻。", "",
        "| 贴现率 | " + " | ".join(_escape(row["label"]) for row in bases) + " |",
        "|---:|" + "---:|" * len(bases),
    ]
    for rate in cash["discount_rates"]:
        cells = []
        for row in bases:
            value = row["payback_required_growth"].get(rate)
            cells.append("无解" if value is None else _pct_decimal(value))
        lines.append(f"| {_discount_rate_label(rate, bundle['target_return'], ten_year)} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def _peer_value(item: dict[str, Any]) -> str:
    if item["format"] == "percent":
        return _pct_decimal(item["value"])
    if item["format"] == "number":
        return f"{float(item['value']):,.2f}"
    return f"{float(item['value']):.2f}x"


BASIS_LABELS = {"reported": "报表口径", "adjusted": "调整后口径", "market": "市场数据"}


def peers_reader(bundle: dict[str, Any]) -> str:
    valuation = _support(bundle)["valuation"]
    cash = bundle["derived"]["cash_valuation"]
    lines = ["### 同业对比", "", "| 公司 | 指标 | 口径 | 数值 | 截至 | 判断 |", "|---|---|---|---:|---|---|"]
    earnings = [row for row in cash["bases"] if row["kind"] == "earnings"]
    peer_bases = {item["basis"] for item in valuation["peers"]}
    shown = [row for row in earnings if row.get("accounting_basis") in peer_bases] or earnings[:1]
    for own in shown:
        basis = BASIS_LABELS.get(own.get("accounting_basis") or "", "本报告口径")
        lines.append(f"| **{_escape(bundle['report']['company'])}** | {_escape(own['label'])} 市盈率 | {basis} | {_multiple(own['multiple'])} | {bundle['report']['as_of']} | 本报告口径 |")
    for item in valuation["peers"]:
        lines.append("| " + " | ".join([
            _escape(item["name"]), _escape(item["metric"]), BASIS_LABELS[item["basis"]], _peer_value(item), _escape(item["as_of"]), _escape(item["judgement"]),
        ]) + " |")
    lines.extend(["", _paragraph(valuation["peer_interpretation"]), ""])
    refs = [{"evidence_refs": [{"ref": item["source_id"], "role": "supports"}]} for item in valuation["peers"]]
    lines += _source_note(bundle, [*refs, valuation["peer_interpretation"], valuation["cash_interpretation"]])
    return "\n".join(lines)


def scenario_premises_reader(bundle: dict[str, Any]) -> str:
    premises = _support(bundle)["scenario_premises"]
    lines = ["### 情景经营前提（未来 12-24 个月）", "", "| 情景 | 5年 IRR | 需要看到的经营事实 |", "|---|---:|---|"]
    for name, label in (("bull", "Bull"), ("base", "Base"), ("bear", "Bear")):
        irr = bundle["scenarios"][name]["returns"]["irr"]["irr_pct"]
        lines.append(f"| {label} | {float(irr):.2f}% | {_escape(_paragraph(premises[name]))} |")
    lines.append("")
    return "\n".join(lines)


def valuation_extension(bundle: dict[str, Any]) -> str:
    return "\n".join([cash_valuation_reader(bundle), payback_matrix_reader(bundle), peers_reader(bundle), scenario_premises_reader(bundle)])


def risk_reader(bundle: dict[str, Any]) -> str:
    risks = _support(bundle)["risks"]
    lines = [
        "## 5. 致命风险排序", "",
        "| 排名 | 风险 | 概率 | 损害 | 传导与领先指标 | 触发与动作 |", "|---:|---|---|---|---|---|",
    ]
    for item in risks:
        indicators = "；".join(x.rstrip("。") for x in item["leading_indicators"])
        lines.append("| " + " | ".join([
            str(item["rank"]), _escape(item["risk"]), LEVEL_LABELS[item["probability"]], LEVEL_LABELS[item["impact"]],
            _escape(f"{item['mechanism']} 领先指标：{indicators}。"),
            _escape(f"触发：{item['trigger']} 动作：{item['action']}"),
        ]) + " |")
    lines.extend(["", "概率和损害是定性分档，用于排序和决定监控频率，不是统计概率。", ""])
    lines += _source_note(bundle, risks)
    return "\n".join(lines)


def _range(tier: dict[str, Any], currency: str) -> str:
    floor, ceiling = tier.get("floor"), tier.get("ceiling")
    if ceiling is None and floor is not None:
        return f"≥ {_money(floor, currency)}"
    if floor is None and ceiling is not None:
        return f"< {_money(ceiling, currency)}"
    return f"{_money(floor, currency)} – {_money(ceiling, currency)}"


def _position(tier: dict[str, Any]) -> str:
    low, high = float(tier["position_min"]) * 100, float(tier["position_max"]) * 100
    if high == 0:
        return "0（不新增）"
    if low == high:
        return f"{high:.0f}%"
    return f"{low:.0f}%–{high:.0f}%"


PREMISE_LABELS = {"met": "满足", "unmet": "未满足", "unknown": "待验证"}
OPERATOR_LABELS = {">": ">", ">=": "≥", "<": "<", "<=": "≤", "==": "=", "!=": "≠"}
STATUS_WORDS = {"hold": "支持持有", "review": "需要复核", "reduce": "触发降低暴露", "True": "是", "False": "否"}


def _condition_value(value: Any, unit: str) -> str:
    text = str(value)
    if text in STATUS_WORDS:
        return STATUS_WORDS[text]
    try:
        float(text)
    except ValueError:
        return text
    return _value(text, unit)


def _premise_cell(tier: dict[str, Any]) -> str:
    parts = []
    for item in tier.get("premise_conditions", []):
        if item["status"] == "unknown":
            parts.append(f"{item['label']}：待验证（{item['pending']}）")
        else:
            mark = "✓" if item["status"] == "met" else "✗"
            parts.append(
                f"{mark} {item['label']}：{_condition_value(item['actual'], item['unit'])}"
                f"（要求 {OPERATOR_LABELS[item['operator']]} {_condition_value(item['threshold'], item['unit'])}）"
            )
    status = PREMISE_LABELS[tier.get("premise_status", "met")]
    return f"**{status}**" + ("：" + "；".join(parts) if parts else "")


def ladder_reader(bundle: dict[str, Any]) -> str:
    ladder = bundle["price_ladder"]
    premises = _support(bundle)["ladder_premises"]
    coherence = bundle["decision_coherence"]
    currency = _price_currency(bundle["report"])
    decisive = coherence["decisive"]
    lines = [
        "### 新资金价格阶梯", "",
        f"仓位按“占目标仓位的比例”表述；Base 目标回报价 {_money(ladder['target_return_price'], currency)}、安全边际价 {_money(ladder['buy_price'], currency)}。"
        f"价格只是必要条件：每档还必须满足经营前提，前提未满足或待验证时自动退回上一档。"
        f"决定买点的现金口径是“{_escape(decisive['label'])}”，其确认价 {_money(decisive['confirmation_price'], currency) if decisive.get('confirmation_price') else '无（为负）'}。", "",
        "| 价格区间 | 动作 | 新资金仓位（占目标仓位） | 经营前提 | 前提状态 | 当前 |", "|---|---|---:|---|---|:---:|",
    ]
    for tier in ladder["tiers"]:
        marks = []
        if tier["current"]:
            marks.append("◀ 价格所在")
        if tier.get("executable"):
            marks.append("✓ 可执行")
        lines.append("| " + " | ".join([
            _range(tier, currency), _escape(tier["action"]), _position(tier),
            _escape(_paragraph(premises[tier["tier_id"]])), _escape(_premise_cell(tier)), " ".join(marks),
        ]) + " |")
    executable = next((t for t in ladder["tiers"] if t.get("executable")), None)
    located = next(t for t in ladder["tiers"] if t["current"])
    summary = f"现价落在“{located['action']}”档；"
    if executable is None:
        summary += "当前没有可执行档"
    elif executable["tier_id"] == located["tier_id"]:
        summary += "该档前提已满足"
    else:
        summary += f"该档前提未全部满足，退回“{executable['action']}”档"
    summary += f"，可执行新资金仓位上限 {float(coherence['executable_position_max']) * 100:.0f}%（占目标仓位）。"
    if coherence["blockers"]:
        summary += "卡点：" + "；".join(coherence["blockers"]) + "。"
    lines.extend(["", summary])
    if coherence.get("cash_gate_waiver"):
        lines.extend(["", f"> 现金口径豁免：{coherence['cash_gate_waiver']}"])
    if ladder.get("suspended"):
        lines.extend(["", "> 投资逻辑破坏条件已触发：价格阶梯整体暂停，任何价位都不新增资金。"])
    lines.append("")
    return "\n".join(lines)


def escalation_reader(bundle: dict[str, Any]) -> str:
    escalation = bundle["decision_coherence"]["escalation"]
    lines = [
        "### 现金流升级表", "",
        f"按“{escalation['counter_label']}”逐级收紧新资金；当前为 {escalation['actual']} 个季度。最高一级与投资逻辑破坏条件使用同一阈值。", "",
        "| 级别 | 触发计数（季度） | 新资金上限（占目标仓位） | 动作 | 当前 |", "|---:|---:|---:|---|:---:|",
    ]
    for item in escalation["levels"]:
        lines.append("| " + " | ".join([
            str(item["level"]), f"≥ {item['min_count']}", f"{float(item['new_money_cap']) * 100:.0f}%",
            _escape(item["action"]), "◀ 当前级" if item["level"] == escalation["current_level"] else "",
        ]) + " |")
    if not escalation["current_level"]:
        lines.extend(["", "当前未进入任何升级级别。"])
    lines.append("")
    return "\n".join(lines)


def roic_reader(bundle: dict[str, Any]) -> str:
    roic = bundle["decision_coherence"]["roic"]
    currency = roic["unit"].split(" ")[0]
    formula = " ".join(("+ " if c["sign"] > 0 else "− ") + c["label"] for c in roic["components"]).lstrip("+ ")
    lines = [
        "### ROIC 与增量 ROIC", "",
        f"投入资本 = {formula}；税后经营利润 = 经营利润 × (1 − {_pct_decimal(roic['tax_rate'])})。{roic['method']}", "",
        "| 年度 | 税后经营利润 | 投入资本 | ROIC |", "|---|---:|---:|---:|",
    ]
    for row in roic["rows"]:
        lines.append(f"| {row['year']} | {_absolute_money(row['nopat'], currency)} | {_absolute_money(row['invested_capital'], currency)} | {_pct_decimal(row['roic'])} |")
    incremental = roic["incremental_roic"]
    lines.extend([
        "",
        f"增量 ROIC（{roic['incremental_from']} → {roic['incremental_to']}）："
        + (_pct_decimal(incremental) if incremental is not None else "投入资本未增加，无法计算") + "。", "",
        _paragraph(roic["interpretation"]), "",
    ])
    return "\n".join(lines)


def triggers_reader(bundle: dict[str, Any]) -> str:
    support = _support(bundle)
    existing_labels = {"NONE": "不变", "REVIEW": "复核", "REDUCE": "减仓候选", "SELL": "卖出"}
    lines = [escalation_reader(bundle), "### Action Triggers", "", "| 类别 | 触发条件 | 新资金动作 | 已有仓位 |", "|---|---|---|---|"]
    for item in support["action_triggers"]:
        lines.append(f"| {TRIGGER_LABELS[item['category']]} | {_escape(_paragraph(item['condition']))} | {_escape(item['action'])} | {existing_labels[item['existing_action']]} |")
    pre = support["pre_mortem"]
    signals = "；".join(x.rstrip("。") for x in pre["early_signals"])
    lines.extend([
        "",
        "### Pre-Mortem", "",
        "假设三年后这笔投资亏了钱，最可能的原因是：", "",
        f"- **失败路径：** {_paragraph(pre['failure_path'])}",
        f"- **最危险的分析错误：** {_paragraph(pre['analysis_error'])}",
        f"- **最早能看到的信号：** {signals}。", "",
        f"**流动性：** {_paragraph(support['liquidity'])}", "",
    ])
    lines += _source_note(bundle, [*[x["condition"] for x in support["action_triggers"]], pre["failure_path"], pre["analysis_error"], support["liquidity"]])
    return "\n".join(lines)


def positioning_extension(bundle: dict[str, Any]) -> str:
    return "\n".join([ladder_reader(bundle), triggers_reader(bundle)])


def final_extension(bundle: dict[str, Any]) -> str:
    cash = bundle["derived"]["cash_valuation"]
    dividend = cash.get("dividend")
    lines: list[str] = []
    if dividend:
        currency = cash["price_currency"]
        tax = bundle["report"].get("tax_identity", "")
        lines.extend([
            f"### {dividend['years']}年税后股息", "",
            f"按每股股息 {_money(dividend['dps_price'], currency)}、年增 {_pct_decimal(dividend['growth'])}、预扣税 {_pct_decimal(dividend['withholding'])}（{tax}），"
            f"{dividend['years']} 年税后累计 {_money(dividend['net_total'], currency)}（税前 {_money(dividend['gross_total'], currency)}），"
            f"相当于现价的 {_pct_decimal(dividend['net_total_yield'])}。股息只是回报的小头，不能替代盈利增长。", "",
        ])
    lines.extend(["### 最小复核清单", "", "下一次财报或价格进入阶梯下一档时，只需先复核这几件事：", ""])
    for index, item in enumerate(_support(bundle)["review_checklist"], 1):
        lines.append(f"{index}. {item}")
    lines.append("")
    return "\n".join(lines)

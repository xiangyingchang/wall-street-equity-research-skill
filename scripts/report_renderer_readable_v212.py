from __future__ import annotations

from typing import Any, Iterable

from scripts.report_renderer_v2 import render_markdown as render_legacy_audit_markdown


def _currency_prefix(currency: Any) -> str:
    code = str(currency or "").upper()
    return {"USD": "$", "HKD": "HK$", "CNY": "CNY ", "RMB": "RMB ", "KRW": "KRW "}.get(code, f"{code} " if code else "")


def _money(value: Any, currency: Any = "USD") -> str:
    try:
        return f"{_currency_prefix(currency)}{float(value):,.2f}"
    except Exception:
        return str(value)


def _pct_decimal(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return str(value)


def _pct_number(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return str(value)


def _number(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return str(value)


def _absolute_money(value: Any, currency: Any) -> str:
    try:
        return f"{_currency_prefix(currency)}{float(value):,.2f}亿"
    except Exception:
        return str(value)


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


def _claim_text(item: dict[str, Any], field: str = "text") -> str:
    value = item.get(field, item.get("claim", ""))
    return str(value).strip()


def _paragraph(item: dict[str, Any], *, include_counter: bool = False) -> str:
    text = _claim_text(item)
    implication = str(item.get("implication", "")).strip()
    counter = str(item.get("counter_evidence", "")).strip() if include_counter else ""
    parts = [text]
    if implication:
        parts.append(implication)
    if counter:
        parts.append(f"需要同时看到的是：{counter}")
    return " ".join(part for part in parts if part)


def _join_chinese(items: list[str]) -> str:
    return "；".join(str(item).strip().rstrip("。；;") for item in items) + "。"


def _evidence_objects(item: dict[str, Any]) -> Iterable[str]:
    for raw in item.get("evidence_refs", []):
        if isinstance(raw, dict):
            yield str(raw.get("ref", ""))
        else:
            yield str(raw)


def _human_sources(bundle: dict[str, Any], items: Iterable[dict[str, Any]], limit: int = 4) -> str:
    source_ids: list[str] = []
    model_used = False
    for item in items:
        for ref in _evidence_objects(item):
            if ref.startswith("SRC-"):
                source_ids.append(ref)
            elif ref.startswith("FACT-"):
                fact = bundle.get("facts", {}).get(ref, {})
                source_ids.extend(str(x) for x in fact.get("source_ids", []))
            elif ref.startswith("BUNDLE:"):
                model_used = True
    seen: set[str] = set()
    labels: list[str] = []
    for source_id in source_ids:
        if source_id in seen:
            continue
        seen.add(source_id)
        source = bundle.get("source_registry", {}).get(source_id)
        if source:
            title = str(source.get("title", source_id))
            labels.append(title)
        if len(labels) >= limit:
            break
    if model_used:
        labels.append("报告情景模型")
    return "、".join(labels)


def _source_note(bundle: dict[str, Any], items: Iterable[dict[str, Any]]) -> list[str]:
    text = _human_sources(bundle, items)
    return [f"> 主要依据：{text}", ""] if text else []


def _quarter_rows(bundle: dict[str, Any]) -> list[tuple[str, str, str, str, str]]:
    series = bundle["quarterly_series"]
    currency = bundle["report"].get("currency", "")
    rows: list[tuple[str, str, str, str, str]] = []
    for index in range(4):
        ids = {key: series[key][index] for key in ("revenue", "operating_income", "eps", "fcf")}
        period = str(bundle["facts"][ids["revenue"]].get("period", ""))
        rows.append((
            period,
            _absolute_money(bundle["facts"][ids["revenue"]]["value"], currency),
            _absolute_money(bundle["facts"][ids["operating_income"]]["value"], currency),
            _money(bundle["facts"][ids["eps"]]["value"], currency),
            _absolute_money(bundle["facts"][ids["fcf"]]["value"], currency),
        ))
    return rows


def _action_label(value: str) -> str:
    mapping = {
        "BUY": "买入",
        "WATCH": "观察",
        "DO_NOT_BUY": "暂不买入",
        "HOLD": "持有",
        "REVIEW": "复核",
        "REDUCE": "减仓",
        "SELL": "卖出",
    }
    return mapping.get(str(value), str(value))


def _reason_label(reason: str) -> str:
    mapping = {
        "base IRR materially below hurdle": "基础情景回报显著低于最低目标回报",
        "base IRR within review band": "基础情景回报处于复核区间",
        "operating evidence within neutral band": "经营数据处于中性容差区间",
        "thesis break": "核心投资逻辑被破坏",
    }
    return mapping.get(reason, reason.replace("_", " "))


def render_reader_markdown(bundle: dict[str, Any]) -> str:
    report = bundle["report"]
    currency = report.get("currency", "")
    company = report["company"]
    return_years = report["return_years"]
    payback_years = report["payback_years"]
    scenarios = bundle["scenarios"]
    decision = bundle["decision"]
    base = scenarios["base"]
    bear = scenarios["bear"]
    bull = scenarios["bull"]
    research = bundle["research"]
    derived = bundle["derived"]
    lines: list[str] = []

    thesis = research["overview"]["thesis"]
    key_forces = research["overview"]["key_forces"]
    current_price = bundle["facts"].get("FACT-CURRENT-PRICE", {}).get("value", "—")

    lines.extend([
        f"# {report['ticker']} {report['company']} — 华尔街式分析报告", "",
        f"> 数据截至 {report['as_of']}。本报告由单一数据源编译生成；详细证据、假设和验证结果见同名 `.audit.md`。", "",
        "## 一页结论", "",
        "| 项目 | 判断 |", "|---|---|",
        f"| 新资金 | **{_action_label(decision['new_money_action'])}** |",
        f"| 已有仓位 | **{_action_label(decision['existing_position_action'])}** |",
        f"| 当前价格 | {_money(current_price, currency)} |",
        f"| Base {return_years}年 IRR | {_pct_decimal(decision['valuation']['base_irr'])} |",
        f"| 最低目标回报 | {_pct_decimal(decision['valuation']['target_return'])} |",
        f"| 目标回报价格 | {_money(base['prices']['target_return'], currency)} |",
        f"| 安全边际买入价 | {_money(base['prices']['buy'], currency)} |",
        f"| Forward reference | {_money(base['prices']['forward_reference'], currency)} |", "",
        f"**核心判断：** {_claim_text(thesis)}", "",
        f"现价下，新资金应选择**{_action_label(decision['new_money_action'])}**，已有仓位建议**{_action_label(decision['existing_position_action'])}**。直接原因是{_reason_label(str(decision['reason']))}：Base IRR 只有 {_pct_decimal(decision['valuation']['base_irr'])}，低于 {_pct_decimal(decision['valuation']['target_return'])} 的最低目标回报。", "",
        "### 三个核心矛盾", "",
    ])
    for index, item in enumerate(key_forces, 1):
        lines.append(f"{index}. **{_claim_text(item, 'claim')}** {_claim_text(item, 'implication')}")
    lines.extend(["", f"**下一步最值得验证：** {research['final_verdict']['falsification']['text']}", ""])

    overview = research["overview"]
    lines.extend(["## 1. 华尔街式全景扫描", "", _paragraph(overview["thesis"]), ""])
    lines.append("本次判断可以压缩成三条主线：")
    for item in overview["key_forces"]:
        lines.append(f"- **{_claim_text(item, 'claim')}** {_claim_text(item, 'implication')}")
    lines.extend(["", f"**Variant View：** {_paragraph(overview['variant_view'], include_counter=True)}", ""])
    lines += _source_note(bundle, [overview["thesis"], *overview["key_forces"], overview["variant_view"]])

    financial = research["financial_autopsy"]
    ttm = derived["ttm"]
    lines.extend([
        "## 2. 财务剖析", "",
        f"过去四个季度，{company} 的 TTM EPS 为 {_money(ttm['eps']['value'], currency)}，TTM 经营利润率为 {_pct_number(ttm['operating_margin']['value_pct'])}，TTM FCF 为 {_absolute_money(ttm['fcf']['value'], currency)}。", "",
        _paragraph(financial["revenue"]), "",
        _paragraph(financial["margin"]), "",
        _paragraph(financial["cash_flow"]), "",
        _paragraph(financial["one_offs"]), "",
        "### 最近四个季度", "",
        "| 期间 | 收入 | 经营利润 | EPS | FCF |", "|---|---:|---:|---:|---:|",
    ])
    for row in _quarter_rows(bundle):
        lines.append("| " + " | ".join(_escape(x) for x in row) + " |")
    lines.extend([""])
    lines += _source_note(bundle, financial.values())

    moat = research["moat"]
    lines.extend(["## 3. 护城河", "", f"{company} 的护城河整体趋势为 **{moat['trajectory']}**。", ""])
    lines.extend(["| 维度 | 评分 | 判断 | 反向证据 |", "|---|---:|---|---|"])
    for item in moat["dimensions"]:
        lines.append("| " + " | ".join([
            _escape(item["name"]), f"{item['score']}/5", _escape(item["claim"]), _escape(item["counter_evidence"]),
        ]) + " |")
    lines.extend([""])
    lines += _source_note(bundle, moat["dimensions"])

    valuation = research["valuation"]
    lines.extend([
        f"## 4. 极限估值与{payback_years}年回本", "",
        _paragraph(valuation["base_case"]), "",
        f"| 场景 | Forward revenue | EPS | {return_years}年 IRR | 目标回报价格 | 安全边际买入价 |", "|---|---:|---:|---:|---:|---:|",
        f"| Bear | {_absolute_money(bear['revenue']['forward_revenue'], currency)} | {_money(bear['eps_bridge']['eps'], currency)} | {_pct_number(bear['returns']['irr']['irr_pct'])} | {_money(bear['prices']['target_return'], currency)} | {_money(bear['prices']['buy'], currency)} |",
        f"| Base | {_absolute_money(base['revenue']['forward_revenue'], currency)} | {_money(base['eps_bridge']['eps'], currency)} | {_pct_number(base['returns']['irr']['irr_pct'])} | {_money(base['prices']['target_return'], currency)} | {_money(base['prices']['buy'], currency)} |",
        f"| Bull | {_absolute_money(bull['revenue']['forward_revenue'], currency)} | {_money(bull['eps_bridge']['eps'], currency)} | {_pct_number(bull['returns']['irr']['irr_pct'])} | {_money(bull['prices']['target_return'], currency)} | {_money(bull['prices']['buy'], currency)} |", "",
        _paragraph(valuation["reverse_expectations"]), "",
        _paragraph(valuation["payback_interpretation"]), "",
        f"| 贴现率 | {payback_years}年回本所需 EPS 增长 |", "|---:|---:|",
    ])
    for rate, growth in derived["payback_required_growth"].items():
        lines.append(f"| {_pct_decimal(rate)} | {_pct_decimal(growth)} |")
    lines.extend(["", f"**最关键假设：** {_paragraph(valuation['critical_assumption'])}", ""])
    lines += _source_note(bundle, valuation.values())

    risks = research["risks"]["items"]
    lines.extend(["## 5. 致命风险排序", "", "| 排名 | 风险 | 传导机制 | 领先指标 | 触发条件 |", "|---:|---|---|---|---|"])
    for item in risks:
        lines.append("| " + " | ".join([
            str(item["rank"]), _escape(item["risk"]), _escape(item["mechanism"]),
            _escape(_join_chinese(item["leading_indicators"])), _escape(item["trigger"]),
        ]) + " |")
    lines.extend(["", "风险不是用来证明公司一定会失败，而是明确什么事实出现时，当前判断必须改变。", ""])
    lines += _source_note(bundle, risks)

    growth = research["growth_limits"]
    lines.extend(["## 6. 物理增长极限", "", _paragraph(growth["growth_engine"]), "", "增长上限主要受三类约束："])
    for item in growth["constraints"]:
        lines.append(f"- **{_claim_text(item, 'claim')}** {_claim_text(item, 'implication')}")
    lines.extend(["", _paragraph(growth["ceiling"]), ""])
    lines += _source_note(bundle, [growth["growth_engine"], *growth["constraints"], growth["ceiling"]])

    opportunity = research["opportunity_cost"]
    lines.extend(["## 7. 机构视角与机会成本", "", _paragraph(opportunity["interpretation"]), ""])
    for item in opportunity["comparators"]:
        lines.append(f"- {_claim_text(item, 'claim')} {_claim_text(item, 'implication')}")
    lines.extend(["", f"Base IRR 为 {_pct_decimal(decision['valuation']['base_irr'])}，而最低目标回报为 {_pct_decimal(decision['valuation']['target_return'])}。因此争议不是 {company} 是否是一家好公司，而是当前价格是否给出了足够的风险补偿。", ""])
    lines += _source_note(bundle, [opportunity["interpretation"], *opportunity["comparators"]])

    positioning = research["positioning"]
    lines.extend([
        "## 8. 仓位与风控", "",
        f"**新资金：{_action_label(decision['new_money_action'])}。** {_paragraph(positioning['new_money'])}", "",
        f"**已有仓位：{_action_label(decision['existing_position_action'])}。** {_paragraph(positioning['existing_position'])}", "",
        _paragraph(positioning["portfolio_constraints"]), "",
        _paragraph(positioning["execution"]), "",
        "### 价格区间", "",
        "| 区间 | 价格 | 新资金含义 |", "|---|---|---|",
    ])
    for zone in bundle["price_zones"]:
        if "min" not in zone:
            price_range = f"≤ {_money(zone['max'], currency)}"
        elif "max" not in zone:
            price_range = f"> {_money(zone['min'], currency)}"
        else:
            price_range = f"({_money(zone['min'], currency)}, {_money(zone['max'], currency)}]"
        lines.append(f"| {_escape(zone['name'])} | {price_range} | {_action_label(zone['action'])} |")
    lines.extend([""])
    lines += _source_note(bundle, positioning.values())

    final = research["final_verdict"]
    lines.extend([
        "## 9. 最终判决", "",
        _paragraph(final["summary"]), "",
        f"**持有等于买入：** {_paragraph(final['hold_equals_buy'])}", "",
        f"**机会成本：** {_paragraph(final['opportunity_cost'])}", "",
        f"**{payback_years}年回本：** {_paragraph(final['payback'])}", "",
        f"**置信度边界：** {_paragraph(final['confidence_boundary'])}", "",
        f"**反证条件：** {_paragraph(final['falsification'])}", "",
        "## 主要来源", "",
    ])
    for source in list(bundle["source_registry"].values())[:8]:
        lines.append(f"- {_escape(source['title'])} — {_escape(source['publisher'])}，{_escape(source['date'])}")
    lines.extend(["", "> 完整证据链、模型假设与验证结果见同名 `.audit.md`。", ""])
    return "\n".join(lines)


def render_audit_markdown(bundle: dict[str, Any]) -> str:
    legacy = render_legacy_audit_markdown(bundle)
    lines = legacy.splitlines()
    if lines:
        lines[0] = f"# {bundle['report']['ticker']} {bundle['report']['company']} — 审计附录 v2.1.2"
    if len(lines) > 2:
        lines[2] = "> 本文件为机器审计层，完整保留来源、事实、假设、证据引用、质量检查与验证结果；面向读者的投资报告见同名 `.md`。"
    return "\n".join(lines)

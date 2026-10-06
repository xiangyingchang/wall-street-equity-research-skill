from __future__ import annotations

from itertools import zip_longest
from typing import Any

from scripts import report_renderer_v32_sections as v32
from scripts.report_renderer_readable_v212 import (
    _absolute_money,
    _action_label,
    _claim_text,
    _escape,
    _fx_note,
    _join_chinese,
    _money,
    _paragraph,
    _pct_decimal,
    _price_currency,
    _source_note,
    render_audit_markdown as render_audit_v212,
    render_reader_markdown as render_reader_v212,
)


def _replace_section(markdown: str, start: str, end: str, replacement: str) -> str:
    start_index = markdown.index(start)
    end_index = markdown.index(end, start_index)
    return markdown[:start_index] + replacement.rstrip() + "\n\n" + markdown[end_index:]


def _action(value: Any) -> str:
    if str(value) == "NOT_APPLICABLE":
        return "不适用"
    return _action_label(str(value))


def _confidence(value: Any) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(str(value).lower(), str(value))


def _assumption(bundle: dict[str, Any], role: str) -> tuple[str, dict[str, Any]]:
    assumption_id = bundle["scenarios"]["base"]["assumption_refs"][role]
    return assumption_id, bundle["assumptions"][assumption_id]


def _format_assumption(role: str, item: dict[str, Any]) -> str:
    value = item.get("value")
    if role in {"operating_margin", "tax_rate", "eps_cagr", "dividend_yield", "safety_margin"}:
        return _pct_decimal(value)
    if role in {"exit_pe", "reference_multiple"}:
        return f"{float(value):.2f}x"
    if role == "diluted_shares":
        return f"{float(value):,.2f} 亿股"
    return str(value)


def _payback_principle(bundle: dict[str, Any]) -> tuple[str, str]:
    target = float(bundle["target_return"])
    rates = bundle["derived"]["payback_required_growth"]
    rate = min(rates, key=lambda value: abs(float(value) - target))
    required = float(rates[rate])
    _, base_growth = _assumption(bundle, "eps_cagr")
    expected = float(base_growth["value"])
    result = "通过" if expected >= required else "不通过"
    explanation = f"按 {_pct_decimal(rate)} 贴现，回本要求 EPS 年增 {_pct_decimal(required)}；Base 仅假设 {_pct_decimal(expected)}。"
    return result, explanation


def _portfolio_limit(bundle: dict[str, Any]) -> str:
    context = bundle["portfolio_context"]
    status = context["position_status"]
    if status == "not_held":
        return "组合确认当前无仓位，因此已有仓位动作不适用。"
    if status == "unknown":
        return "未取得真实持仓状态、当前权重与目标权重；研究候选动作不能直接执行。"
    current = context.get("current_weight")
    target = context.get("target_weight")
    if current is None:
        return "已确认持仓，但当前权重缺失；不能计算调仓幅度。"
    if target is None:
        return f"当前权重为 {_pct_decimal(current)}，但目标权重缺失；不能执行减仓。"
    return f"当前权重 {_pct_decimal(current)}，目标权重 {_pct_decimal(target)}；税务/摩擦为 {context['tax_friction']}。"


def _prior_report_reader(bundle: dict[str, Any]) -> str:
    prior = bundle["prior_report_context"]
    lines = ["### 与上次报告相比", ""]
    if prior["status"] == "not_available":
        lines.append(f"未找到可比的上一份报告：{prior['reason']}")
        return "\n".join(lines)
    decision = bundle["decision"]
    reported = _pct_decimal(prior["previous_base_irr_reported"])
    recalculated = prior.get("previous_base_irr_recalculated")
    prior_irr = f"报告写为 {reported}"
    if recalculated is not None:
        prior_irr += f"；运行时复算为 {_pct_decimal(recalculated)}"
    calculation_label = {"recalculated": "已按旧报告输入复算", "verified": "已验证", "unverified": "未验证"}[prior["calculation_status"]]
    lines.extend([
        f"> 对比基线：`{prior['path']}`（数据截至 {prior['as_of']}；旧 IRR：{calculation_label}）。", "",
        "| 对比项 | 上次报告 | 本次报告 |", "|---|---|---|",
        f"| 新资金 | {_action(prior['previous_new_money_action'])} | {_action(decision['new_money_action'])} |",
        f"| 已有仓位 | {_action(prior['previous_existing_position_action'])} | 研究候选 {_action(decision['existing_position_candidate_action'])}；可执行 {_action(decision['existing_position_action'])} |",
        f"| Base IRR | {prior_irr} | {_pct_decimal(decision['valuation']['base_irr'])} |", "",
        f"- **评级变化：** 新资金从“{_action(prior['previous_new_money_action'])}”到“{_action(decision['new_money_action'])}”；"
        f"已有仓位由“{_action(prior['previous_existing_position_action'])}”到当前可执行“{_action(decision['existing_position_action'])}”。",
        f"- **关键指标变化：** {prior['metric_delta']}",
        f"- **投资逻辑变化：** {prior['thesis_delta']}",
        f"- **方法变化：** {prior['methodology_delta']}",
    ])
    return "\n".join(lines)


def _condition_value(value: Any, unit: str, currency: str) -> str:
    if unit == "ratio":
        return _pct_decimal(value)
    if currency and currency in unit and "/share" not in unit:
        return _absolute_money(value, currency)
    if "/share" in unit:
        return _money(value, unit.split("/")[0])
    if unit == "quarters":
        return f"{int(float(value))} 个季度"
    return f"{float(value):,.2f} {unit}".strip()


def _thesis_break_text(bundle: dict[str, Any]) -> str:
    thesis = bundle["decision"]["thesis_break"]
    currency = bundle["report"]["currency"]
    conditions = [
        f"{item['label']} {item['operator']} {_condition_value(item['expected'], item['unit'], currency)}"
        for item in thesis["conditions"]
    ]
    logic = "且" if thesis.get("logic") == "all" else "或"
    return f"{logic.join(conditions)}。"


def _action_matrix_rows(bundle: dict[str, Any]) -> list[tuple[str, str, str, str, str]]:
    decision = bundle["decision"]
    valuation = decision["valuation"]
    base = bundle["scenarios"]["base"]
    currency = _price_currency(bundle["report"])
    reduce_boundary = float(valuation["reduce_gap"]) + float(valuation["review_band"])
    hold_boundary = max(0.0, float(valuation["reduce_gap"]) - float(valuation["review_band"]))
    candidate = decision["existing_position_candidate_action"]
    executable = decision["existing_position_action"]
    new_money = decision["new_money_action"]
    context = bundle["portfolio_context"]

    def state(action: str) -> str:
        labels: list[str] = []
        if action == "BUY":
            labels.append({"BUY": "新资金当前动作", "WATCH": "新资金为观察：未进入可执行买入", "DO_NOT_BUY": "新资金不买入"}[new_money])
        if action == candidate:
            labels.append("已有仓位研究候选")
        if action == executable:
            labels.append("已有仓位当前可执行")
        return "；".join(dict.fromkeys(labels)) or "未触发"

    add_execution = "仅在组合给出高于当前权重的目标权重后分步执行。"
    if context["position_status"] != "held" or context.get("current_weight") is None or context.get("target_weight") is None:
        add_execution = "N/A：持仓状态或目标权重不完整。"
    elif float(context["target_weight"]) <= float(context["current_weight"]):
        add_execution = "N/A：当前目标权重不高于现有权重。"

    return [
        (
            "买入", "price + operating",
            f"现价 ≤ {_money(base['prices']['buy'], currency)}，全部经营闸门支持持有，且投资逻辑未破坏。",
            "新资金分步建仓，不因公司质量跳过安全边际。", state("BUY"),
        ),
        (
            "加仓", "price + portfolio",
            f"已持仓、现价 ≤ {_money(base['prices']['buy'], currency)}，且组合目标权重高于当前权重。",
            add_execution, "未由公司模型单独触发",
        ),
        (
            "持有", "valuation + operating",
            f"Base IRR 缺口 ≤ {_pct_decimal(hold_boundary)}，经营闸门无降低暴露或复核信号，且投资逻辑未破坏。",
            "维持经组合确认的仓位；不把历史成本当理由。", state("HOLD"),
        ),
        (
            "复核", "valuation / robustness / portfolio",
            f"IRR 缺口进入 {_pct_decimal(hold_boundary)}–{_pct_decimal(reduce_boundary)} 中性带；或缺口较低但经营信号中性；或鲁棒性/组合上下文不完整。",
            "暂停交易，补齐证据、持仓权重和目标权重后重编译。", state("REVIEW"),
        ),
        (
            "减仓", "valuation / operating",
            f"IRR 缺口 > {_pct_decimal(reduce_boundary)}；或缺口 ≤ {_pct_decimal(hold_boundary)} 且经营闸门触发降低暴露；同时必须有当前权重 > 目标权重。",
            "只减到已登记目标权重；缺任一组合字段则自动降为复核。", state("REDUCE"),
        ),
        (
            "卖出", "thesis-break",
            _thesis_break_text(bundle),
            "仅在投资逻辑破坏且确认真实持仓后退出，不由估值偏高单独触发。", state("SELL"),
        ),
    ]


def _price_distance(current: Any, target: Any) -> str:
    current_value = float(current)
    target_value = float(target)
    if current_value <= 0:
        return "无法计算"
    change = target_value / current_value - 1
    if change >= 0:
        return f"该线高于现价 {abs(change) * 100:.1f}%"
    return f"需再跌 {abs(change) * 100:.1f}%"


def _sensitivity_value(role: str, value: Any) -> str:
    if value is None:
        return "无解"
    if role == "exit_pe":
        return f"{float(value):.1f}x"
    return _pct_decimal(value)


def _sensitivity_distance(role: str, value: Any) -> str:
    if value is None:
        return "无解"
    number = float(value)
    if role == "exit_pe":
        return f"{number:+.1f}x"
    return f"{number * 100:+.1f} 个百分点"


def _decision_sensitivity_reader(bundle: dict[str, Any]) -> str:
    data = bundle.get("decision_sensitivity")
    if not data:
        return ""
    lines = [
        "### 什么会改变结论", "",
        f"下表只动一个变量、其他 Base 假设不变，回答“要错多少，结论才会变”。Base IRR {_pct_decimal(data['base_irr'])}，门槛 {_pct_decimal(data['target_return'])}。", "",
        "| 变量 | Base 值 | 达到门槛所需值 | 距离 | 下调一步 IRR | 上调一步 IRR |", "|---|---:|---:|---:|---:|---:|",
    ]
    for row in data["drivers"]:
        shocks = {item["direction"]: item for item in row["shocks"]}

        def shock_text(direction: str) -> str:
            item = shocks.get(direction)
            if not item:
                return "—"
            return f"{_sensitivity_value(row['role'], item['value'])} → {_pct_decimal(item['irr'])}（{_action(item['valuation_candidate'])}）"

        lines.append("| " + " | ".join([
            row["label"],
            _sensitivity_value(row["role"], row["base_value"]),
            _sensitivity_value(row["role"], row["break_even_value"]),
            _sensitivity_distance(row["role"], row["distance_to_break_even"]),
            shock_text("down"),
            shock_text("up"),
        ]) + " |")
    lines.extend([
        "",
        "距离越小，当前结论越脆弱；括号内是只看估值缺口时的存量候选动作，最终仍受经营闸门和组合闸门约束。", "",
    ])
    grid = data.get("grid")
    if grid:
        lines.extend([
            "#### 利润率 × 退出市盈率（Base IRR）", "",
            "两个变量同时变动时的 IRR；✓ 表示达到门槛。中间格为 Base。", "",
            "| 经营利润率 \\ 退出市盈率 | " + " | ".join(f"{float(x):.1f}x" for x in grid["columns"]) + " |",
            "|---:|" + "---:|" * len(grid["columns"]),
        ])
        for row in grid["rows"]:
            cells = ["—" if cell is None else f"{_pct_decimal(cell['irr'])}{' ✓' if cell['passes'] else ''}" for cell in row["cells"]]
            lines.append(f"| {_pct_decimal(row['operating_margin'])} | " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def _execution_summary(bundle: dict[str, Any]) -> list[str]:
    coherence = bundle.get("decision_coherence")
    if not coherence:
        return []
    currency = _price_currency(bundle["report"])
    decisive = coherence["decisive"]
    escalation = coherence["escalation"]
    confirm = _money(decisive["confirmation_price"], currency) if decisive.get("confirmation_price") else "无（为负）"
    position = float(coherence["executable_position_max"]) * 100
    lines = [
        "| 执行检查 | 当前 | 含义 |", "|---|---|---|",
        f"| 现金门槛（{_escape(decisive['label'])}） | 收益率 {_pct_decimal(decisive['yield'])} vs 门槛 {_pct_decimal(bundle['target_return'])}，{'已过' if decisive['passes_hurdle'] else '未过'} | 现金确认价 {confirm}；大仓位只在该价附近成立。 |",
        f"| 价格阶梯 | 价格所在“{_escape(coherence['price_tier_action'])}”档 | 可执行新资金上限 **{position:.0f}%**（占目标仓位）"
        + (f"；卡点：{_escape('；'.join(coherence['blockers']))}" if coherence["blockers"] else "") + "。 |",
        f"| 现金流升级表 | {_escape(escalation['counter_label'])} {escalation['actual']} 个季度，" + (f"第 {escalation['current_level']} 级" if escalation["current_level"] else "未升级") + " | "
        + (_escape(escalation["levels"][escalation["current_level"] - 1]["action"]) if escalation["current_level"] else "按价格阶梯执行。") + " |",
        "",
    ]
    return lines


def _decision_page(bundle: dict[str, Any]) -> str:
    report = bundle["report"]
    decision = bundle["decision"]
    base = bundle["scenarios"]["base"]
    current_fact = bundle["facts"][report["current_price_fact_id"]]
    current_price = current_fact["value"]
    currency = _price_currency(report)
    return_years = report["return_years"]
    candidate = decision["existing_position_candidate_action"]
    executable = decision["existing_position_action"]
    portfolio_limit = _portfolio_limit(bundle)
    hurdle_pass = float(decision["valuation"]["base_irr"]) >= float(decision["valuation"]["target_return"])
    hold_equals_buy = "通过" if decision["new_money_action"] == "BUY" else "不通过"
    payback_result, payback_explanation = _payback_principle(bundle)
    thesis = bundle["research"]["overview"]["thesis"]

    lines = [
        "## 一页结论", "",
        "### 当前决策", "",
        "| 对象 | 研究候选 | 可执行动作 | 依据与限制 |", "|---|---|---|---|",
        f"| 新资金 | {_action(decision['new_money_action'])} | **{_action(decision['new_money_action'])}** | 现价 {_money(current_price, currency)}；Base 目标回报价 {_money(base['prices']['target_return'], currency)}（{_price_distance(current_price, base['prices']['target_return'])}），安全边际价 {_money(base['prices']['buy'], currency)}（{_price_distance(current_price, base['prices']['buy'])}）。 |",
        f"| 已有仓位 | {_action(candidate)} | **{_action(executable)}** | {_escape(portfolio_limit)} |", "",
        *( [f"> 计价口径：{_fx_note(bundle)}", ""] if _fx_note(bundle) else [] ),
        *_execution_summary(bundle),
        f"> **结论：** {_claim_text(thesis)} 研究层给出的存量候选动作是“{_action(candidate)}”，但组合闸门后的唯一可执行动作是“{_action(executable)}”。", "",
        "### Action Matrix（唯一执行口径）", "",
        "| 动作 | 触发类型 | 可执行条件 | 仓位/执行 | 当前状态 |", "|---|---|---|---|---|",
    ]
    for row in _action_matrix_rows(bundle):
        lines.append("| " + " | ".join(_escape(value) for value in row) + " |")
    lines.extend([
        "",
        "### 三条原投资原则", "",
        "| 原则 | 结论 | 决策标准 |", "|---|---|---|",
        f"| 持有等于买入 | **{hold_equals_buy}** | 如果今天没有仓位，现价下的新资金动作是“{_action(decision['new_money_action'])}”。 |",
        f"| 机会成本 | **{'通过' if hurdle_pass else '不通过'}** | Base {return_years}年 IRR {_pct_decimal(decision['valuation']['base_irr'])}，最低目标回报 {_pct_decimal(decision['valuation']['target_return'])}。 |",
        f"| {report['payback_years']}年回本 | **{payback_result}** | {payback_explanation} |", "",
        "### Base 情景关键假设", "",
        "| 假设 | Base 值 | 依据 | 置信度 |", "|---|---:|---|---|",
    ])
    labels = {
        "operating_margin": "前瞻经营利润率",
        "eps_cagr": "长期 EPS 增长",
        "exit_pe": "退出市盈率",
        "dividend_yield": "股息率",
        "safety_margin": "安全边际折扣",
    }
    for role, label in labels.items():
        _, item = _assumption(bundle, role)
        lines.append(f"| {label} | {_format_assumption(role, item)} | {_escape(item['rationale'])} | {_confidence(item['confidence'])} |")
    lines.extend(["", _decision_sensitivity_reader(bundle)])
    lines.extend([
        "", _prior_report_reader(bundle), "",
        f"**当前最重要的验证点：** {bundle['research']['final_verdict']['falsification']['text']}", "",
    ])
    return "\n".join(lines)


def _segment_rows(bundle: dict[str, Any]) -> list[str]:
    overview = bundle["research"]["overview"]
    segments = overview.get("segments") or []
    if not segments:
        return []
    facts = bundle["facts"]
    currency = bundle["report"].get("currency", "")
    revenue_ids = [item["revenue_fact_id"] for item in segments]
    total = sum(float(facts[fact_id]["value"]) for fact_id in revenue_ids)
    period = str(facts[revenue_ids[0]].get("period", ""))
    lines = [
        f"| 业务（{period}） | 收入 | 占比 | 同比 | 怎么赚钱 |",
        "|---|---:|---:|---:|---|",
    ]
    for item in segments:
        revenue = float(facts[item["revenue_fact_id"]]["value"])
        share = f"{revenue / total * 100:.1f}%" if total else "N/A"
        yoy = _pct_decimal(facts[item["yoy_fact_id"]]["value"]) if item.get("yoy_fact_id") else "N/A"
        lines.append("| " + " | ".join([
            _escape(item["name"]),
            _absolute_money(revenue, currency),
            share,
            yoy,
            _escape(f"{_claim_text(item, 'claim')} {item.get('implication', '')}".strip()),
        ]) + " |")
    lines.append("")
    return lines


def _overview_reader(bundle: dict[str, Any]) -> str:
    overview = bundle["research"]["overview"]
    lines = ["## 1. Overview：商业模式与本次财报", ""]
    if overview.get("business_model"):
        lines.extend([_paragraph(overview["business_model"]), ""])
    lines.extend(["**核心判断：**" + _paragraph(overview["thesis"]), ""])
    lines += _segment_rows(bundle)
    lines.extend(["### Key Forces", ""])
    for index, item in enumerate(overview["key_forces"], 1):
        lines.append(f"{index}. **{_claim_text(item, 'claim')}** {item.get('implication', '')}".rstrip())
    lines.append("")
    update = overview.get("earnings_update")
    if update:
        lines.extend([
            f"### 本次财报：{_claim_text(update['period'])}", "",
            f"- **本次财报改变了什么：** {_paragraph(update['changed'])}",
            f"- **本次财报没有改变什么：** {_paragraph(update['unchanged'])}", "",
        ])
    lines.extend([f"**Variant View：** {_paragraph(overview['variant_view'], include_counter=True)}", ""])
    sources = [overview["thesis"], *overview["key_forces"], overview["variant_view"]]
    if overview.get("business_model"):
        sources.append(overview["business_model"])
    sources += overview.get("segments") or []
    if update:
        sources += list(update.values())
    lines += _source_note(bundle, sources)
    return "\n".join(lines)


def _theme_reader(bundle: dict[str, Any]) -> str:
    graph = bundle["research_graph"]
    lines = ["### 决定回报的投资主线", ""]
    for index, theme in enumerate(graph["themes"], 1):
        observations = _join_chinese([_claim_text(item) for item in theme["observations"]])
        lines.extend([
            f"#### 主线 {index}：{theme['title']}", "",
            f"{observations} {_paragraph(theme['hypothesis'])} {_paragraph(theme['resolution'], include_counter=True)}", "",
            f"反过来看，{_paragraph(theme['challenge'], include_counter=True)}", "",
            f"落到决策上，{_paragraph(theme['decision_impact'])} 推翻条件：{_paragraph(theme['falsification'])}", "",
        ])
        lines += _source_note(bundle, [*theme["observations"], theme["hypothesis"], theme["challenge"], theme["resolution"]])
    return "\n".join(lines)


def _debate_reader(bundle: dict[str, Any]) -> str:
    debate = bundle["research_graph"]["debate"]
    lines = [
        "### 最强正反证据与裁决", "",
        "| 支持更乐观判断 | 支持更谨慎判断 |", "|---|---|",
    ]
    for bull, bear in zip_longest(debate["bull"], debate["bear"]):
        bull_text = f"{_claim_text(bull, 'claim')} {bull.get('implication', '')}" if bull else "—"
        bear_text = f"{_claim_text(bear, 'claim')} {bear.get('implication', '')}" if bear else "—"
        lines.append(f"| {_escape(bull_text)} | {_escape(bear_text)} |")
    adjudication = debate["adjudication"]
    lines.extend([
        "", f"**裁决：** {_paragraph(adjudication, include_counter=True)}", "",
        f"当前仍无法消除的不确定性是：{adjudication['remaining_uncertainty']}", "",
    ])
    lines += _source_note(bundle, [*debate["bull"], *debate["bear"], adjudication])
    return "\n".join(lines)


def _assumption_from_path(bundle: dict[str, Any], path: str) -> dict[str, Any]:
    assumption_id = path.split("/")[-2]
    return bundle["assumptions"][assumption_id]


def _sensitivity_reader(bundle: dict[str, Any]) -> str:
    drivers = bundle["research_graph"]["sensitivity"]["drivers"]
    labels = {"high": "高", "medium": "中", "low": "低"}
    lines = [
        "### 真正决定估值的变量", "",
        "| 变量 | Base 设定 | 重要性 | 为什么重要 | 向上/向下时怎样改变判断 |", "|---|---:|---|---|---|",
    ]
    for item in drivers:
        assumption = _assumption_from_path(bundle, item["base_assumption_path"])
        base_value = _format_assumption(str(assumption.get("role", "")), assumption)
        movement = f"向上：{item['upside_case']} 向下：{item['downside_case']} {item['decision_consequence']}"
        lines.append("| " + " | ".join([
            _escape(item["variable"]), _escape(base_value), labels[item["importance"]],
            _escape(item["mechanism"]), _escape(movement),
        ]) + " |")
    lines.append("")
    return "\n".join(lines)


def _metric_display(value: Any, unit: str, currency: str) -> str:
    if unit == "ratio":
        return _pct_decimal(value)
    if currency and currency in unit and "/share" not in unit:
        return _absolute_money(value, currency)
    return f"{float(value):,.2f} {unit}".strip()


def _portfolio_reader(bundle: dict[str, Any]) -> str:
    context = bundle["portfolio_context"]
    decision = bundle["decision"]
    currency = bundle["report"]["currency"]
    status_label = {"held": "已持有", "not_held": "未持有", "unknown": "未知"}[context["position_status"]]
    lines = [
        "## 8. 组合约束与执行边界", "",
        f"组合状态为 **{status_label}**，数据截至 {context['as_of']}，来源为 {context['source']}，置信度为 {_confidence(context['confidence'])}。{_portfolio_limit(bundle)}", "",
        f"研究模型的候选动作是 **{_action(decision['existing_position_candidate_action'])}**；组合闸门结果是 **{_action(decision['existing_position_action'])}**。具体交易规则只以上方唯一 Action Matrix 为准。", "",
        "### 公司特有经营闸门", "",
        "| 指标 | 当前值 | 支持持有阈值 | 降低暴露阈值 | 状态 |", "|---|---:|---:|---:|---|",
    ]
    for item in decision["operating"]["metrics"]:
        lines.append("| " + " | ".join([
            _escape(item["label"]),
            _metric_display(item["value"], item["unit"], currency),
            _metric_display(item["hold_threshold"], item["unit"], currency),
            _metric_display(item["reduce_threshold"], item["unit"], currency),
            {"hold": "支持持有", "review": "需要复核", "reduce": "触发降低暴露"}[item["status"]],
        ]) + " |")
    positioning = bundle["research"]["positioning"]
    lines.extend([
        "", _paragraph(positioning["portfolio_constraints"]), "",
        _paragraph(positioning["execution"]), "",
    ])
    lines += _source_note(bundle, [positioning["portfolio_constraints"], positioning["execution"]])
    return "\n".join(lines)


def _final_reader(bundle: dict[str, Any]) -> str:
    final = bundle["research"]["final_verdict"]
    payback_years = bundle["report"]["payback_years"]
    return "\n".join([
        "## 9. 最终判决", "",
        "最终动作已经在第一页的唯一 Action Matrix 中确定；这里不再建立第二套交易口径。", "",
        f"**持有等于买入：** {_paragraph(final['hold_equals_buy'])}", "",
        f"**机会成本：** {_paragraph(final['opportunity_cost'])}", "",
        f"**{payback_years}年回本：** {_paragraph(final['payback'])}", "",
        f"**置信度边界：** {_paragraph(final['confidence_boundary'])}", "",
        f"**反证条件：** {_paragraph(final['falsification'])}", "",
    ])


def render_reader_markdown(bundle: dict[str, Any]) -> str:
    markdown = render_reader_v212(bundle)
    context_line = (
        f"> 默认输入：税务身份={bundle['report'].get('tax_identity', '未提供')}；"
        f"投资周期={bundle['report'].get('horizon', '未提供')}；报告契约=Compiler Reader v3.2。\n>\n"
    )
    markdown = markdown.replace("> 数据截至", context_line + "> 数据截至", 1)
    markdown = markdown.replace("由单一数据源编译生成", "由单一 Spec 编译生成", 1)
    markdown = _replace_section(markdown, "## 一页结论", "## 1. 华尔街式全景扫描", _decision_page(bundle))
    markdown = _replace_section(markdown, "## 1. 华尔街式全景扫描", "## 2. 财务剖析", _overview_reader(bundle) + "\n\n" + _theme_reader(bundle))
    if bundle.get("decision_support"):
        markdown = markdown.replace("## 3. 护城河", v32.financial_extension(bundle) + "\n## 3. 护城河", 1)
        markdown = _replace_section(markdown, "## 5. 致命风险排序", "## 6. 物理增长极限", v32.risk_reader(bundle))
        markdown = markdown.replace("## 5. 致命风险排序", v32.valuation_extension(bundle) + "\n" + _sensitivity_reader(bundle) + "\n## 5. 致命风险排序", 1)
    else:
        markdown = markdown.replace("## 5. 致命风险排序", _sensitivity_reader(bundle) + "\n## 5. 致命风险排序", 1)
    portfolio = _portfolio_reader(bundle)
    if bundle.get("decision_support"):
        portfolio += "\n\n" + v32.positioning_extension(bundle)
    markdown = _replace_section(markdown, "## 8. 仓位与风控", "## 9. 最终判决", portfolio)
    markdown = markdown.replace("## 9. 最终判决", _debate_reader(bundle) + "\n## 9. 最终判决", 1)
    final = _final_reader(bundle)
    if bundle.get("decision_support"):
        final += "\n" + v32.final_extension(bundle)
    markdown = _replace_section(markdown, "## 9. 最终判决", "## 主要来源", final)
    return markdown


def _evidence_refs(item: dict[str, Any]) -> str:
    return ", ".join(f"{x.get('ref')}[{x.get('role')}]" for x in item.get("evidence_refs", []))


def _graph_audit(bundle: dict[str, Any]) -> str:
    graph = bundle["research_graph"]
    quality = bundle["research_graph_quality"]
    lines = [
        "## Research Graph v3.1", "",
        "| Check | Value |", "|---|---:|",
        f"| Themes | {quality['themes']} |",
        f"| Observations | {quality['observations']} |",
        f"| Bull arguments | {quality['bull_arguments']} |",
        f"| Bear arguments | {quality['bear_arguments']} |",
        f"| Classified arguments | {quality['classified_arguments']} |",
        f"| Sensitivity drivers | {quality['sensitivity_drivers']} |",
        f"| High-importance drivers | {quality['high_importance_drivers']} |", "",
    ]
    auto_discounted = quality.get("auto_discounted_arguments", [])
    lines.extend([f"> Auto-discounted: {', '.join(auto_discounted) if auto_discounted else 'none'}", ""])
    for theme in graph["themes"]:
        lines.extend([
            f"### {theme['theme_id']} — {theme['title']}", "",
            f"- Core question: {theme['core_question']}",
            f"- Module links: {', '.join(theme['module_links'])}", "",
            "| Node | Text | Evidence |", "|---|---|---|",
        ])
        for item in theme["observations"]:
            lines.append(f"| {_escape(item['observation_id'])} | {_escape(_claim_text(item))} | {_escape(_evidence_refs(item))} |")
        for name in ("hypothesis", "challenge", "resolution", "decision_impact", "falsification"):
            item = theme[name]
            lines.append(f"| {_escape(name)} | {_escape(_claim_text(item))} | {_escape(_evidence_refs(item))} |")
        lines.append("")
    debate = graph["debate"]
    lines.extend(["### Investment Debate", "", "| Side | Argument ID | Claim | Evidence |", "|---|---|---|---|"])
    for side in ("bull", "bear"):
        for item in debate[side]:
            lines.append(f"| {_escape(side)} | {_escape(item['argument_id'])} | {_escape(_claim_text(item, 'claim'))} | {_escape(_evidence_refs(item))} |")
    adjudication = debate["adjudication"]
    lines.extend([
        "", f"**Adjudication:** {_claim_text(adjudication)}", "",
        f"- Accepted: {', '.join(adjudication['accepted_argument_ids'])}",
        f"- Discounted: {', '.join(adjudication['discounted_argument_ids'])}",
        f"- Auto-discounted: {', '.join(adjudication['auto_discounted_argument_ids']) if adjudication['auto_discounted_argument_ids'] else 'none'}",
        f"- Remaining uncertainty: {adjudication['remaining_uncertainty']}", "",
        "### Sensitivity Explanation", "",
        "| Driver ID | Variable | Assumption | Direction | Importance | Mechanism | Decision consequence | Evidence |", "|---|---|---|---|---|---|---|---|",
    ])
    for item in graph["sensitivity"]["drivers"]:
        lines.append("| " + " | ".join(_escape(value) for value in [
            item["driver_id"], item["variable"], item["base_assumption_path"], item["direction"], item["importance"], item["mechanism"], item["decision_consequence"], _evidence_refs(item),
        ]) + " |")
    lines.append("")
    sensitivity = bundle.get("decision_sensitivity")
    if sensitivity:
        lines.extend([
            "### Decision Sensitivity (quantified)", "",
            f"- Base IRR: {sensitivity['base_irr']}; hurdle: {sensitivity['target_return']}; base valuation candidate: {sensitivity['base_valuation_candidate']}", "",
            "| Role | Base | Step | Break-even | Distance | Shocks |", "|---|---:|---:|---:|---:|---|",
        ])
        for row in sensitivity["drivers"]:
            shocks = "; ".join(f"{item['direction']} {item['value']} -> IRR {item['irr']} ({item['valuation_candidate']})" for item in row["shocks"])
            lines.append(f"| {row['role']} | {row['base_value']} | {row['step']} | {row['break_even_value']} | {row['distance_to_break_even']} | {_escape(shocks)} |")
        lines.append("")
    return "\n".join(lines)


def render_audit_markdown(bundle: dict[str, Any]) -> str:
    audit = render_audit_v212(bundle)
    lines = audit.splitlines()
    if lines:
        lines[0] = f"# {bundle['report']['ticker']} {bundle['report']['company']} — 审计附录 v3.1"
    audit = "\n".join(lines)
    return audit.rstrip() + "\n\n" + _graph_audit(bundle)

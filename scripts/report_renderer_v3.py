from __future__ import annotations

from itertools import zip_longest
from typing import Any

from scripts.report_renderer_readable_v212 import (
    _absolute_money,
    _action_label,
    _claim_text,
    _escape,
    _join_chinese,
    _money,
    _paragraph,
    _pct_decimal,
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
    calculation_label = {"recalculated": "已由 runtime 复算", "verified": "已验证", "unverified": "未验证"}[prior["calculation_status"]]
    lines.extend([
        f"> 对比基线：`{prior['path']}`（数据截至 {prior['as_of']}；旧 IRR：{calculation_label}）。", "",
        "| 对比项 | 上次报告 | 本次报告 |", "|---|---|---|",
        f"| 新资金 | {_action(prior['previous_new_money_action'])} | {_action(decision['new_money_action'])} |",
        f"| 已有仓位 | {_action(prior['previous_existing_position_action'])} | 研究候选 {_action(decision['existing_position_candidate_action'])}；可执行 {_action(decision['existing_position_action'])} |",
        f"| Base IRR | {prior_irr} | {_pct_decimal(decision['valuation']['base_irr'])} |", "",
        f"- **评级变化：** {prior['rating_delta']}",
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
        return _money(value, currency)
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
    currency = bundle["report"]["currency"]
    reduce_boundary = float(valuation["reduce_gap"]) + float(valuation["review_band"])
    hold_boundary = max(0.0, float(valuation["reduce_gap"]) - float(valuation["review_band"]))
    candidate = decision["existing_position_candidate_action"]
    executable = decision["existing_position_action"]
    new_money = decision["new_money_action"]
    context = bundle["portfolio_context"]

    def state(action: str) -> str:
        labels: list[str] = []
        if action == "BUY" and new_money == "BUY":
            labels.append("当前新资金动作")
        if action == "REVIEW" and (executable == "REVIEW" or new_money == "WATCH"):
            labels.append("当前可执行动作")
        if action == candidate:
            labels.append("研究候选")
        if action == executable and "当前可执行动作" not in labels:
            labels.append("当前可执行")
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


def _decision_page(bundle: dict[str, Any]) -> str:
    report = bundle["report"]
    decision = bundle["decision"]
    base = bundle["scenarios"]["base"]
    current_fact = bundle["facts"][report["current_price_fact_id"]]
    current_price = current_fact["value"]
    currency = report["currency"]
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
        f"| 新资金 | {_action(decision['new_money_action'])} | **{_action(decision['new_money_action'])}** | 现价 {_money(current_price, currency)}；Base 目标回报价 {_money(base['prices']['target_return'], currency)}，安全边际价 {_money(base['prices']['buy'], currency)}。 |",
        f"| 已有仓位 | {_action(candidate)} | **{_action(executable)}** | {_escape(portfolio_limit)} |", "",
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
    lines.extend([
        "", _prior_report_reader(bundle), "",
        f"**当前最重要的验证点：** {bundle['research']['final_verdict']['falsification']['text']}", "",
    ])
    return "\n".join(lines)


def _theme_reader(bundle: dict[str, Any]) -> str:
    graph = bundle["research_graph"]
    lines = ["## 1. 决定回报的投资主线", ""]
    for index, theme in enumerate(graph["themes"], 1):
        observations = _join_chinese([_claim_text(item) for item in theme["observations"]])
        lines.extend([
            f"### {index}. {theme['title']}", "",
            f"{observations} {_paragraph(theme['hypothesis'])} {_paragraph(theme['resolution'], include_counter=True)}", "",
            f"反过来看，{_paragraph(theme['challenge'], include_counter=True)} 这仍是当前结论最需要防守的解释。", "",
            f"落到决策上，{_paragraph(theme['decision_impact'])} 若要推翻这条判断，需要看到：{_paragraph(theme['falsification'])}", "",
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
        f"投资周期={bundle['report'].get('horizon', '未提供')}；报告契约=Compiler Reader v3.1。\n>\n"
    )
    markdown = markdown.replace("> 数据截至", context_line + "> 数据截至", 1)
    markdown = markdown.replace("由单一数据源编译生成", "由单一 Spec 编译生成", 1)
    markdown = _replace_section(markdown, "## 一页结论", "## 1. 华尔街式全景扫描", _decision_page(bundle))
    markdown = _replace_section(markdown, "## 1. 华尔街式全景扫描", "## 2. 财务剖析", _theme_reader(bundle))
    markdown = markdown.replace("## 5. 致命风险排序", _sensitivity_reader(bundle) + "\n## 5. 致命风险排序", 1)
    markdown = _replace_section(markdown, "## 8. 仓位与风控", "## 9. 最终判决", _portfolio_reader(bundle))
    markdown = markdown.replace("## 9. 最终判决", _debate_reader(bundle) + "\n## 9. 最终判决", 1)
    markdown = _replace_section(markdown, "## 9. 最终判决", "## 主要来源", _final_reader(bundle))
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
    return "\n".join(lines)


def render_audit_markdown(bundle: dict[str, Any]) -> str:
    audit = render_audit_v212(bundle)
    lines = audit.splitlines()
    if lines:
        lines[0] = f"# {bundle['report']['ticker']} {bundle['report']['company']} — 审计附录 v3.1"
    audit = "\n".join(lines)
    return audit.rstrip() + "\n\n" + _graph_audit(bundle)

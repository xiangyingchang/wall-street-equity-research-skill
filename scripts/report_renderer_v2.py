from __future__ import annotations

from typing import Any, Iterable


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return str(value)


def _pct_decimal(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return str(value)


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


def _refs(item: dict[str, Any]) -> str:
    refs = item.get("evidence_refs", [])
    return ", ".join(f"{ref['ref']}[{ref['role']}]" if isinstance(ref, dict) else str(ref) for ref in refs)


def _claim_block(title: str, item: dict[str, Any], field: str = "text") -> list[str]:
    lines = [f"### {title}", "", str(item[field]), ""]
    if item.get("implication"):
        lines.extend([f"**投资含义：** {item['implication']}", ""])
    if item.get("counter_evidence"):
        lines.extend([f"**反向证据：** {item['counter_evidence']}", ""])
    lines.extend([f"**证据：** `{_refs(item)}` · **置信度：** {item['confidence']}", ""])
    return lines


def _fact_value(bundle: dict[str, Any], fact_id: str) -> str:
    return str(bundle["facts"][fact_id]["value"])


def _quarter_rows(bundle: dict[str, Any]) -> list[tuple[str, str, str, str, str]]:
    series = bundle["quarterly_series"]
    rows = []
    for index in range(4):
        ids = {key: series[key][index] for key in ("revenue", "operating_income", "eps", "fcf")}
        period = bundle["facts"][ids["revenue"]].get("period", "")
        rows.append((period, _fact_value(bundle, ids["revenue"]), _fact_value(bundle, ids["operating_income"]), _fact_value(bundle, ids["eps"]), _fact_value(bundle, ids["fcf"])))
    return rows


def _assumption_rows(bundle: dict[str, Any], scenario: str) -> Iterable[tuple[str, str, str, str, str]]:
    refs = bundle["scenarios"][scenario]["assumption_refs"]
    assumptions = bundle["assumptions"]
    for role, assumption_id in refs.items():
        item = assumptions[assumption_id]
        if "value" in item:
            value = str(item["value"])
        elif "growth" in item:
            value = f"growth={item['growth']}"
        elif "low" in item and "high" in item:
            value = f"{item['low']}–{item['high']}"
        else:
            value = "mode-specific"
        yield role, assumption_id, value, str(item.get("rationale", "")), str(item.get("confidence", ""))


def _all_claims(research: dict[str, Any]) -> list[tuple[str, str, list[dict[str, str]], str]]:
    claims: list[tuple[str, str, list[dict[str, str]], str]] = []

    def visit(path: str, value: Any) -> None:
        if isinstance(value, dict):
            text = value.get("claim", value.get("text"))
            refs = value.get("evidence_refs")
            confidence = value.get("confidence")
            if isinstance(text, str) and isinstance(refs, list):
                claims.append((path, text, refs, str(confidence)))
            for key, child in value.items():
                if key not in {"claim", "text", "evidence_refs", "confidence", "implication", "counter_evidence", "value_refs"}:
                    visit(f"{path}.{key}" if path else key, child)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(f"{path}[{index}]", child)

    visit("research", research)
    return claims


def render_markdown(bundle: dict[str, Any]) -> str:
    report = bundle["report"]
    scenarios = bundle["scenarios"]
    decision = bundle["decision"]
    base = scenarios["base"]
    research = bundle["research"]
    quality = bundle["research_quality"]
    lines: list[str] = []

    lines.extend([
        f"# {report['ticker']} {report['company']} — 华尔街式分析报告 v2.1.1", "",
        "> 本报告由 `report-spec-v2.1.1` 单一数据源编译生成。数值、动作与价格由 Compiler 控制；研究判断通过 Evidence Role 和 Value Binding 连接到同一 Bundle。禁止手工修改 Markdown。", "",
        "### Build Manifest", "", "| Field | Value |", "|---|---|",
        "| Schema | report-spec-v2.1.1 → report-bundle-v2.1.1 |",
        f"| Compiler | {bundle['compiler_version']} |", f"| As-of | {_escape(report['as_of'])} |",
        f"| Spec hash | `{bundle['spec_hash']}` |", f"| Bundle hash | `{bundle['bundle_hash']}` |", "",
        "## First-Page Verdict", "", "| 项目 | 结论 |", "|---|---|",
        f"| New money action | **{decision['new_money_action']}** |",
        f"| Existing position action | **{decision['existing_position_action']}** |",
        f"| 动作原因 | {_escape(decision['reason'])} |",
        f"| Base IRR | {_pct_decimal(decision['valuation']['base_irr'])} |",
        f"| 股票最低目标回报 | {_pct_decimal(decision['valuation']['target_return'])} |",
        f"| Base target-return price | {_money(base['prices']['target_return'])} |",
        f"| Base buy price | {_money(base['prices']['buy'])} |",
        f"| Base forward reference | {_money(base['prices']['forward_reference'])} |", "",
        research["overview"]["thesis"]["text"], "",
        f"证据：`{_refs(research['overview']['thesis'])}` · 置信度：{research['overview']['thesis']['confidence']}", "",
        "## Source Registry", "", "| Source ID | Title | Publisher | Date | Tier | Type | Scope | Locator | URL |", "|---|---|---|---|---:|---|---|---|---|",
    ])
    for source_id, source in bundle["source_registry"].items():
        cells = [source_id, source['title'], source['publisher'], source['date'], source['tier'], source['document_type'], ', '.join(source['scope']), source['locator'], source.get('url', '')]
        lines.append("| " + " | ".join(_escape(x) for x in cells) + " |")

    lines.extend(["", "## Evidence Ledger", "", "| Fact ID | Value | Unit | Period/as-of | Source IDs | Tier | Confidence |", "|---|---:|---|---|---|---|---|"])
    for fact_id, fact in bundle["facts"].items():
        source_ids = fact.get("source_ids", [])
        tiers = sorted({str(bundle['source_registry'][sid]['tier']) for sid in source_ids})
        cells = [fact_id, fact['value'], fact['unit'], fact.get('period', fact.get('as_of', '')), ', '.join(source_ids), ', '.join(tiers), fact['confidence']]
        lines.append("| " + " | ".join(_escape(x) for x in cells) + " |")

    lines.extend(["", "## Quarterly TTM Bridge", "", "| Period | Revenue | Operating income | EPS | FCF |", "|---|---:|---:|---:|---:|"])
    for row in _quarter_rows(bundle):
        lines.append("| " + " | ".join(_escape(x) for x in row) + " |")
    lines.extend(["", "| TTM Metric | Value | Runtime source |", "|---|---:|---|",
        f"| TTM EPS | {_money(bundle['derived']['ttm']['eps']['value'])} | ttm-derive |",
        f"| TTM operating margin | {bundle['derived']['ttm']['operating_margin']['value_pct']}% | ttm-derive |",
        f"| TTM FCF | {bundle['derived']['ttm']['fcf']['value']} | ttm-derive |", "",
        "## Scenario Assumptions and Valuation", ""])
    for name in ("bear", "base", "bull"):
        lines.extend([f"### {name.title()} assumptions", "", "| Role | Assumption ID | Value/payload | Rationale | Confidence |", "|---|---|---|---|---|"])
        for row in _assumption_rows(bundle, name):
            lines.append("| " + " | ".join(_escape(x) for x in row) + " |")
        lines.append("")
    lines.extend(["| Scenario | Forward revenue | EPS | 5Y IRR | Required EPS CAGR | Forward reference | Target-return price | Buy price |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for name in ("bear", "base", "bull"):
        item = scenarios[name]
        lines.append(f"| {name.title()} | {item['revenue']['forward_revenue']} | {_money(item['eps_bridge']['eps'])} | {item['returns']['irr']['irr_pct']}% | {item['returns']['reverse']['required_eps_cagr_pct']}% | {_money(item['prices']['forward_reference'])} | {_money(item['prices']['target_return'])} | {_money(item['prices']['buy'])} |")

    lines.extend(["", "## Payback Stress Test", "", "| Discount rate | Required EPS growth |", "|---:|---:|"])
    for rate, growth in bundle["derived"]["payback_required_growth"].items():
        lines.append(f"| {_pct_decimal(rate)} | {_pct_decimal(growth)} |")

    lines.extend(["", "## Decision Policy Evaluation", "", "### Valuation", "", "| Field | Value |", "|---|---:|"])
    for key, value in decision["valuation"].items():
        lines.append(f"| {_escape(key)} | {_pct_decimal(value)} |")
    lines.extend(["", "### Operating", "", "| Field | Value |", "|---|---:|"])
    for key, value in decision["operating"].items():
        shown = _pct_decimal(value) if key in {"tolerance", "uncertainty"} else value
        lines.append(f"| {_escape(key)} | {_escape(shown)} |")
    lines.extend(["", "### Robustness", "", f"- Shock: {_pct_decimal(decision['robustness']['shock'])}", f"- Stable: {str(decision['robustness']['stable']).lower()}", f"- Shocked actions: {', '.join(decision['robustness']['shocked_actions'])}", "", "## Price Zones", "", "| Zone | Range | New-money meaning |", "|---|---|---|"])
    for zone in bundle["price_zones"]:
        if "min" not in zone:
            price_range = f"≤ {_money(zone['max'])}"
        elif "max" not in zone:
            price_range = f"> {_money(zone['min'])}"
        else:
            price_range = f"({_money(zone['min'])}, {_money(zone['max'])}]"
        lines.append(f"| {_escape(zone['name'])} | {price_range} | {_escape(zone['action'])} |")

    overview = research["overview"]
    lines.extend(["", "## 1. 华尔街式全景扫描 Overview", ""])
    lines += _claim_block("核心投资假设", overview["thesis"])
    lines.extend(["### Key Forces", ""])
    for index, item in enumerate(overview["key_forces"], 1):
        lines.extend([f"**{index}. {item['claim']}**", "", f"投资含义：{item.get('implication', '')}", "", f"证据：`{_refs(item)}` · 置信度：{item['confidence']}", ""])
    lines += _claim_block("Variant View", overview["variant_view"])

    financial = research["financial_autopsy"]
    lines.extend(["## 2. 财务剖析 Financial Autopsy", ""])
    for title, key in (("收入驱动", "revenue"), ("利润率", "margin"), ("现金流与资本开支", "cash_flow"), ("一次性项目与口径", "one_offs")):
        lines += _claim_block(title, financial[key])

    moat = research["moat"]
    lines.extend(["## 3. 护城河 Moat Analysis", "", f"**护城河趋势：{moat['trajectory']}**", "", "| 维度 | 分数 | 判断 | 反向证据 | Evidence |", "|---|---:|---|---|---|"])
    for item in moat["dimensions"]:
        lines.append("| " + " | ".join([_escape(item['name']), f"{item['score']}/5", _escape(item['claim']), _escape(item['counter_evidence']), f"`{_refs(item)}`"]) + " |")

    valuation = research["valuation"]
    lines.extend(["", "## 4. 极限估值 + 10 年回本数学审判", ""])
    for title, key in (("Base Case 解释", "base_case"), ("Reverse Expectations", "reverse_expectations"), ("Payback 解释", "payback_interpretation"), ("最关键假设", "critical_assumption")):
        lines += _claim_block(title, valuation[key])

    lines.extend(["## 5. 致命风险排序 Risk Ranking", "", "| 排名 | 风险 | 作用机制 | 领先指标 | 触发条件 | 缓释因素 | Evidence |", "|---:|---|---|---|---|---|---|"])
    for item in research["risks"]["items"]:
        cells = [item['rank'], item['risk'], item['mechanism'], '；'.join(item['leading_indicators']), item['trigger'], item['mitigant'], f"`{_refs(item)}`"]
        lines.append("| " + " | ".join(_escape(x) for x in cells) + " |")

    growth = research["growth_limits"]
    lines.extend(["", "## 6. 物理增长极限 Growth Potential", ""])
    lines += _claim_block("最可能的增长引擎", growth["growth_engine"])
    lines.extend(["### 关键约束", ""])
    for item in growth["constraints"]:
        lines.extend([f"- **{item['claim']}** — {item.get('implication', '')}  ", f"  Evidence: `{_refs(item)}` · Confidence: {item['confidence']}"])
    lines.append("")
    lines += _claim_block("增长上限判断", growth["ceiling"])

    opportunity = research["opportunity_cost"]
    lines.extend(["## 7. 机构视角与机会成本", ""])
    lines += _claim_block("机会成本解释", opportunity["interpretation"])
    lines.extend(["### Comparators", ""])
    for item in opportunity["comparators"]:
        lines.append(f"- {item['claim']} — {item.get('implication', '')} (`{_refs(item)}`)")
    lines.append("")

    positioning = research["positioning"]
    lines.extend(["## 8. 仓位与风控", ""])
    for title, key in (("New money", "new_money"), ("Existing position", "existing_position"), ("组合约束", "portfolio_constraints"), ("执行纪律", "execution")):
        lines += _claim_block(title, positioning[key])

    final = research["final_verdict"]
    lines.extend(["## 9. 最终判决 Final Verdict", ""])
    for title, key in (("总结", "summary"), ("持有 = 买入", "hold_equals_buy"), ("机会成本", "opportunity_cost"), ("十年回本", "payback"), ("Confidence Boundary", "confidence_boundary"), ("反证条件", "falsification")):
        lines += _claim_block(title, final[key])

    lines.extend(["## Claim-Evidence Matrix", "", "| Claim path | Claim | Evidence refs | Confidence |", "|---|---|---|---|"])
    for path, text, refs, confidence in _all_claims(research):
        ref_text = ", ".join(f"{ref['ref']}[{ref['role']}]" for ref in refs)
        lines.append("| " + " | ".join([_escape(path), _escape(text), f"`{_escape(ref_text)}`", _escape(confidence)]) + " |")

    lines.extend(["", "## Verification", "", "> Verification 由 Compiler 写入独立 `.verification.json` 文件；本报告不接受人工填写 PASS。", "", "| Research check | Result | Details |", "|---|---|---|"])
    for name, result in quality["checks"].items():
        details = ", ".join(f"{k}={v}" for k, v in result.items() if k != "status")
        lines.append(f"| {_escape(name)} | {_escape(result['status'])} | {_escape(details)} |")
    lines.append("")
    return "\n".join(lines)

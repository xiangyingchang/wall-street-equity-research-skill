from __future__ import annotations

from typing import Any


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


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body.strip()}\n"


def render_markdown(bundle: dict[str, Any]) -> str:
    report = bundle["report"]
    scenarios = bundle["scenarios"]
    decision = bundle["decision"]
    base = scenarios["base"]
    narrative = bundle.get("narrative", {})

    lines: list[str] = []
    lines.append(f"# {report['ticker']} {report['company']} — 华尔街式分析报告 v2")
    lines.append("")
    lines.append("> 本报告由 `report-spec-v2` 单一数据源编译生成。所有数值表、价格区间、动作与验证结果来自同一个 Bundle；禁止手工修改 Markdown。")
    lines.append("")
    lines.append("### Build Manifest")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append("| Schema | report-spec-v2 → report-bundle-v2 |")
    lines.append(f"| Compiler | {bundle['compiler_version']} |")
    lines.append(f"| As-of | {report['as_of']} |")
    lines.append(f"| Spec hash | `{bundle['spec_hash']}` |")
    lines.append(f"| Bundle hash | `{bundle['bundle_hash']}` |")
    lines.append("")

    lines.append("## First-Page Verdict")
    lines.append("")
    lines.append("| 项目 | 结论 |")
    lines.append("|---|---|")
    lines.append(f"| New money action | **{decision['new_money_action']}** |")
    lines.append(f"| Existing position action | **{decision['existing_position_action']}** |")
    lines.append(f"| 动作原因 | {decision['reason']} |")
    lines.append(f"| Base IRR | {_pct_decimal(decision['valuation']['base_irr'])} |")
    lines.append(f"| 股票最低目标回报 | {_pct_decimal(decision['valuation']['target_return'])} |")
    lines.append(f"| Base target-return price | {_money(base['prices']['target_return'])} |")
    lines.append(f"| Base buy price | {_money(base['prices']['buy'])} |")
    lines.append(f"| Base forward reference | {_money(base['prices']['forward_reference'])} |")
    lines.append("")

    lines.append("## Evidence and TTM")
    lines.append("")
    lines.append("| Metric | Value | Runtime source |")
    lines.append("|---|---:|---|")
    lines.append(f"| TTM EPS | {_money(bundle['derived']['ttm']['eps']['value'])} | ttm-derive |")
    lines.append(f"| TTM operating margin | {bundle['derived']['ttm']['operating_margin']['value_pct']}% | ttm-derive |")
    lines.append(f"| TTM FCF | {bundle['derived']['ttm']['fcf']['value']} | ttm-derive |")
    lines.append("")

    lines.append("## Scenario Valuation")
    lines.append("")
    lines.append("| Scenario | Forward revenue | EPS | 5Y IRR | Required EPS CAGR | Forward reference | Target-return price | Buy price |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name in ("bear", "base", "bull"):
        item = scenarios[name]
        lines.append(
            f"| {name.title()} | {item['revenue']['forward_revenue']} | {_money(item['eps_bridge']['eps'])} | "
            f"{item['returns']['irr']['irr_pct']}% | {item['returns']['reverse']['required_eps_cagr_pct']}% | "
            f"{_money(item['prices']['forward_reference'])} | {_money(item['prices']['target_return'])} | {_money(item['prices']['buy'])} |"
        )
    lines.append("")

    lines.append("## Payback Stress Test")
    lines.append("")
    lines.append("| Discount rate | Required EPS growth |")
    lines.append("|---:|---:|")
    for rate, growth in bundle["derived"]["payback_required_growth"].items():
        lines.append(f"| {_pct_decimal(rate)} | {_pct_decimal(growth)} |")
    lines.append("")

    lines.append("## Decision Policy Evaluation")
    lines.append("")
    lines.append("### Valuation")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---:|")
    for key, value in decision["valuation"].items():
        lines.append(f"| {key} | {_pct_decimal(value)} |")
    lines.append("")
    lines.append("### Operating")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---:|")
    for key, value in decision["operating"].items():
        shown = _pct_decimal(value) if key in {"tolerance", "uncertainty"} else value
        lines.append(f"| {key} | {shown} |")
    lines.append("")
    lines.append("### Robustness")
    lines.append("")
    lines.append(f"- Shock: {_pct_decimal(decision['robustness']['shock'])}")
    lines.append(f"- Stable: {str(decision['robustness']['stable']).lower()}")
    lines.append(f"- Shocked actions: {', '.join(decision['robustness']['shocked_actions'])}")
    lines.append("")

    lines.append("## Price Zones")
    lines.append("")
    lines.append("| Zone | Range | New-money meaning |")
    lines.append("|---|---|---|")
    for zone in bundle["price_zones"]:
        if "min" not in zone:
            price_range = f"≤ {_money(zone['max'])}"
        elif "max" not in zone:
            price_range = f"> {_money(zone['min'])}"
        else:
            price_range = f"({_money(zone['min'])}, {_money(zone['max'])}]"
        lines.append(f"| {zone['name']} | {price_range} | {zone['action']} |")
    lines.append("")

    for heading, key in [
        ("1. 华尔街式全景扫描 Overview", "overview"),
        ("2. 财务剖析 Financial Autopsy", "financial_autopsy"),
        ("3. 护城河 Moat Analysis", "moat"),
        ("5. 致命风险排序 Risk Ranking", "risks"),
        ("6. 物理增长极限 Growth Potential", "growth_limits"),
        ("7. 机构视角与机会成本", "opportunity_cost"),
        ("8. 仓位与风控", "positioning"),
        ("9. 最终判决 Final Verdict", "final_verdict"),
    ]:
        lines.append(_section(heading, str(narrative.get(key, "未提供叙事内容。"))))

    lines.append("## Verification")
    lines.append("")
    lines.append("> Verification 由 Compiler 写入独立 `.verification.json` 文件；本报告不接受人工填写 PASS。")
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    for source in bundle.get("sources", []):
        lines.append(f"- {source}")
    lines.append("")
    return "\n".join(lines)

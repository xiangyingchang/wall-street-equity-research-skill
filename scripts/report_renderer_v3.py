from __future__ import annotations

from typing import Any

from scripts.report_renderer_readable_v212 import (
    _claim_text,
    _escape,
    _paragraph,
    _source_note,
    render_audit_markdown as render_audit_v212,
    render_reader_markdown as render_reader_v212,
)


def _replace_section(markdown: str, start: str, end: str, replacement: str) -> str:
    start_index = markdown.index(start)
    end_index = markdown.index(end, start_index)
    return markdown[:start_index] + replacement.rstrip() + "\n\n" + markdown[end_index:]


def _theme_reader(bundle: dict[str, Any]) -> str:
    graph = bundle["research_graph"]
    lines = ["## 1. 投资叙事与核心矛盾", ""]
    for index, theme in enumerate(graph["themes"], 1):
        lines.extend([
            f"### {index}. {theme['title']}", "",
            f"**核心问题：** {theme['core_question']}", "",
        ])
        observation_text = "；".join(_claim_text(item) for item in theme["observations"])
        lines.extend([
            f"**发生了什么：** {observation_text}", "",
            f"**基础判断：** {_paragraph(theme['hypothesis'])}", "",
            f"**最强反方：** {_paragraph(theme['challenge'], include_counter=True)}", "",
            f"**综合裁决：** {_paragraph(theme['resolution'], include_counter=True)}", "",
            f"**对决策的影响：** {_paragraph(theme['decision_impact'])}", "",
            f"**什么会推翻判断：** {_paragraph(theme['falsification'])}", "",
        ])
        lines += _source_note(bundle, [*theme["observations"], theme["hypothesis"], theme["challenge"], theme["resolution"]])
    return "\n".join(lines)


def _debate_reader(bundle: dict[str, Any]) -> str:
    debate = bundle["research_graph"]["debate"]
    lines = ["### Bull vs Bear 投资辩论", "", "#### 最强看多论点", ""]
    for item in debate["bull"]:
        lines.append(f"- **{_claim_text(item, 'claim')}** {item.get('implication', '')}".rstrip())
    lines.extend(["", "#### 最强看空论点", ""])
    for item in debate["bear"]:
        lines.append(f"- **{_claim_text(item, 'claim')}** {item.get('implication', '')}".rstrip())
    adjudication = debate["adjudication"]
    lines.extend([
        "", "#### 研究负责人裁决", "",
        _paragraph(adjudication, include_counter=True), "",
        f"**仍未解决的不确定性：** {adjudication['remaining_uncertainty']}", "",
    ])
    return "\n".join(lines)


def _sensitivity_reader(bundle: dict[str, Any]) -> str:
    drivers = bundle["research_graph"]["sensitivity"]["drivers"]
    labels = {"high": "高", "medium": "中", "low": "低", "positive": "正向", "negative": "负向", "mixed": "双向"}
    lines = ["### 哪些假设真正决定估值", ""]
    for item in drivers:
        lines.extend([
            f"- **{item['variable']}（重要性：{labels[item['importance']]}，影响方向：{labels[item['direction']]}）**：{item['mechanism']} ",
            f"  - 乐观变化：{item['upside_case']}",
            f"  - 悲观变化：{item['downside_case']}",
            f"  - 决策含义：{item['decision_consequence']}",
        ])
    lines.append("")
    return "\n".join(lines)


def render_reader_markdown(bundle: dict[str, Any]) -> str:
    markdown = render_reader_v212(bundle)
    markdown = _replace_section(markdown, "## 1. 华尔街式全景扫描", "## 2. 财务剖析", _theme_reader(bundle))
    markdown = markdown.replace("## 5. 致命风险排序", _sensitivity_reader(bundle) + "\n## 5. 致命风险排序", 1)
    markdown = markdown.replace("## 9. 最终判决", _debate_reader(bundle) + "\n## 9. 最终判决", 1)
    return markdown


def _evidence_refs(item: dict[str, Any]) -> str:
    return ", ".join(f"{x.get('ref')}[{x.get('role')}]" for x in item.get("evidence_refs", []))


def _graph_audit(bundle: dict[str, Any]) -> str:
    graph = bundle["research_graph"]
    quality = bundle["research_graph_quality"]
    lines = [
        "## Research Graph v3", "",
        "| Check | Value |", "|---|---:|",
        f"| Themes | {quality['themes']} |",
        f"| Observations | {quality['observations']} |",
        f"| Bull arguments | {quality['bull_arguments']} |",
        f"| Bear arguments | {quality['bear_arguments']} |",
        f"| Classified arguments | {quality['classified_arguments']} |",
        f"| Sensitivity drivers | {quality['sensitivity_drivers']} |",
        f"| High-importance drivers | {quality['high_importance_drivers']} |", "",
    ]
    if quality.get("auto_discounted_arguments"):
        lines.extend([f"> Auto-discounted unclassified arguments: {', '.join(quality['auto_discounted_arguments'])}", ""])
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
    return audit.rstrip() + "\n\n" + _graph_audit(bundle)

from __future__ import annotations

import re
from typing import Any

from scripts.report_renderer_readable_v212 import render_audit_markdown as render_audit_v212
from scripts.report_renderer_readable_v212 import render_reader_markdown as render_reader_v212


def _claim_text(item: dict[str, Any], field: str = "text") -> str:
    return str(item.get(field, item.get("claim", ""))).strip()


def _paragraph(item: dict[str, Any], field: str = "text") -> str:
    text = _claim_text(item, field)
    implication = str(item.get("implication", "")).strip()
    return " ".join(x for x in (text, implication) if x)


def _theme_block(theme: dict[str, Any]) -> str:
    mechanism = " ".join(_paragraph(item, "claim") for item in theme["mechanism"])
    counter = _claim_text(theme["counter_case"])
    signals = "；".join(theme["validation_signals"])
    return (
        f"### {theme['title']}\n\n"
        f"{_claim_text(theme['thesis'])} {mechanism}\n\n"
        f"**投资含义：** {theme['investment_implication']}\n\n"
        f"**反向情形：** {counter}\n\n"
        f"**验证信号：** {signals}"
    )


def _debate_block(debate: dict[str, Any]) -> str:
    labels = (("bull_case", "Bull Case"), ("base_case", "Base Case"), ("bear_case", "Bear Case"))
    parts = ["### Bull / Base / Bear：真正的分歧", ""]
    for key, label in labels:
        case = debate[key]
        parts.extend([
            f"**{label}：** {_claim_text(case['thesis'])}",
            f"兑现路径：{case['path_to_win']} 最早证伪信号：{case['failure_signal']}",
            "",
        ])
    parts.append(f"**核心分歧变量：** {debate['key_disagreement']}")
    return "\n".join(parts)


def _mirror_block(items: list[dict[str, Any]]) -> str:
    lines = ["### 镜子测试", ""]
    for index, item in enumerate(items, 1):
        lines.append(f"{index}. {_claim_text(item)}")
    return "\n".join(lines)


def render_reader_markdown(bundle: dict[str, Any]) -> str:
    markdown = render_reader_v212(bundle)
    narrative = bundle["narrative"]

    themes = "\n\n".join(_theme_block(theme) for theme in narrative["themes"])
    core_pattern = re.compile(
        r"### 三个核心矛盾\n\n.*?\n\n\*\*下一步最值得验证：\*\*.*?\n\n",
        re.S,
    )
    markdown, count = core_pattern.subn(
        "## 核心投资叙事\n\n" + themes + "\n\n",
        markdown,
        count=1,
    )
    if count != 1:
        raise ValueError("unable to replace legacy core-tension block")

    overview_pattern = re.compile(
        r"## 1\. 华尔街式全景扫描\n\n.*?(?=## 2\. 财务剖析)",
        re.S,
    )
    overview = bundle["research"]["overview"]
    overview_text = (
        "## 1. 华尔街式全景扫描\n\n"
        f"{_paragraph(overview['thesis'])}\n\n"
        f"**非共识视角：** {_paragraph(overview['variant_view'])}\n\n"
        + _debate_block(narrative["debate"])
        + "\n\n"
    )
    markdown, count = overview_pattern.subn(overview_text, markdown, count=1)
    if count != 1:
        raise ValueError("unable to replace overview with narrative debate")

    causal = narrative["financial_causal_bridge"]
    causal_text = (
        "### 财务因果桥\n\n"
        f"**经营变化：** {_claim_text(causal['operating_change'])}\n\n"
        f"**成本与资本驱动：** {_claim_text(causal['cost_driver'])}\n\n"
        f"**现金流结果：** {_claim_text(causal['cash_flow_effect'])}\n\n"
        f"**估值含义：** {_claim_text(causal['valuation_effect'])}\n\n"
    )
    markdown = markdown.replace("## 2. 财务剖析\n\n", "## 2. 财务剖析\n\n" + causal_text, 1)

    mirror = _mirror_block(narrative["mirror_test"])
    marker = "## 主要来源"
    if marker not in markdown:
        raise ValueError("reader report missing sources marker")
    markdown = markdown.replace(marker, mirror + "\n\n" + marker, 1)
    return markdown


def render_audit_markdown(bundle: dict[str, Any]) -> str:
    audit = render_audit_v212(bundle)
    narrative = bundle["narrative"]
    lines = ["", "## Investment Narrative Layer v2.2", ""]
    for theme in narrative["themes"]:
        lines.extend([
            f"### {theme['id']} — {theme['title']}", "",
            f"- Category: {theme['category']}",
            f"- Thesis: {_claim_text(theme['thesis'])}",
            f"- Investment implication: {theme['investment_implication']}",
            f"- Counter case: {_claim_text(theme['counter_case'])}",
            f"- Validation signals: {'；'.join(theme['validation_signals'])}",
            f"- Entity hits: {', '.join(theme['entity_hits'])}", "",
        ])
    lines.extend([_debate_block(narrative["debate"]), "", _mirror_block(narrative["mirror_test"]), ""])
    return audit.rstrip() + "\n" + "\n".join(lines)

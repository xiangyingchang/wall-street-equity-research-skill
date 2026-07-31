#!/usr/bin/env python3
"""Lint an Obsidian equity research report for structure and content discipline."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

from validation_common import iter_markdown_tables
from validation_common import (
    ACTION_MATRIX_COLUMNS,
    ACTION_MATRIX_NA_VALUE as NA_VALUE,
    find_action_matrix_table,
)


REQUIRED_PATTERNS = [
    ("default input statement", re.compile(r"默认输入|input_", re.I)),
    ("First-Page Verdict", re.compile(r"First-Page Verdict|首页结论|一页结论", re.I)),
    ("Evidence Ledger", re.compile(r"Evidence Ledger|证据台账|证据账本", re.I)),
    ("Final Verdict", re.compile(r"Final Verdict|最终判决|最终结论", re.I)),
    ("source links", re.compile(r"Source Links|Sources|来源链接|参考资料|参考来源|资料来源", re.I)),
    ("current price", re.compile(r"现价|当前价格|close price|regular-session|after-hours|盘后|收盘价", re.I)),
    ("latest filing or earnings", re.compile(r"最新财报|最新季报|最新年报|earnings release|10-K|10-Q|20-F|6-K|HKEX|公告", re.I)),
    ("10Y government yield", re.compile(r"10Y|10 年|10年|国债|Treasury", re.I)),
    ("hold equals buy", re.compile(r"持有\s*[=＝]\s*买入|持有等于买入", re.I)),
    ("sunk cost discipline", re.compile(r"沉没成本|机会成本才是真成本|opportunity cost", re.I)),
    ("10-year payback discipline", re.compile(r"10\s*年回本|十年回本|10-year payback", re.I)),
]

EXPECTED_TOP_SECTIONS = [
    "First-Page Verdict",
    "Evidence Ledger",
    "1.",
    "2.",
    "3.",
    "4.",
    "5.",
    "6.",
    "7.",
    "8.",
    "9.",
]
REQUIRED_ACTIONS = {"buy", "add", "hold", "reduce", "sell"}
REQUIRED_TRIGGER_TYPES = {"price", "valuation", "operating", "thesis-break"}
# Tax identity gate (Batch 2C): every report must declare a tax identity
# context so tax friction is not silently omitted. A declared identity in the
# default-input line (e.g. 税务身份=中国大陆个人) or an explicit investor context
# satisfies this; an explicit N/A is allowed only with a stated reason.
TAX_IDENTITY = re.compile(
    r"税务身份|tax\s+identity|tax\s+residency|tax\s+status|"
    r"a[\s-]*share\s+investor|us[\s-]*listed\s+investor|hk[\s-]*listed\s+investor|"
    r"港股通|a\s*股\s*投资者|美股\s*投资者|港股\s*投资者|"
    r"中国大陆个人|内地个人|非居民|居民",
    re.I,
)
TAX_IDENTITY_NA = re.compile(
    r"税务身份[^\n]{0,40}(?:n/?a|不适用)[^\n]{0,60}(?:原因|理由|because|reason|:|：)|"
    r"tax\s+identity[^\n]{0,40}(?:n/?a|not\s+applicable)[^\n]{0,60}(?:reason|because|:|：)",
    re.I,
)
# Opportunity-cost benchmark gate (Batch 2C): when a report mentions valuation
# it must reference an opportunity-cost benchmark for every rating, not only Buy.
OPPORTUNITY_COST_BENCHMARK = re.compile(
    r"机会成本|opportunity\s+cost|"
    r"10\s*y(?:ear)?\s*(?:国债|government\s+bond|treasury)|10\s*年\s*国债|"
    r"国债\s*x\s*2|treasury\s*x\s*2|"
    r"指数(?:收益|回报)|index\s+(?:return|benchmark)|"
    r"替代资产|alternative\s+(?:asset|benchmark)|参考标的",
    re.I,
)
VALUATION_CUE = re.compile(
    r"估值|valuation|pe\b|p/e|ev/ebitda|fcf\s*yield|forward\s+pe|贴现|payback|回本|"
    r"安全买入|target\s+(?:multiple|price)|目标价|内在价值|intrinsic",
    re.I,
)
# Previous-report delta gate (Batch 2C): when the pack references a previous
# report (or the report text references a prior report), the report must contain
# a delta/comparison section covering rating, key metrics, and thesis changes.
PREVIOUS_REPORT_CUE = re.compile(
    r"previous\s+report|prior\s+report|上一份报告|前一份报告|上一期报告|上次报告|"
    r"上次评级|前期报告|对比上期|与上期相比|相比上次|更新报告",
    re.I,
)
RATING_DELTA = re.compile(
    r"评级[\s\S]{0,80}(?:升级|下调|维持|不变|unchanged|raised|lowered|kept|"
    r"从[^\n]{0,20}到)|"
    r"rating[\s\S]{0,80}(?:upgraded|downgraded|maintained|unchanged|kept|"
    r"raised|lowered)",
    re.I,
)
METRIC_DELTA = re.compile(
    r"(?:eps|fcf|revenue|营收|净利润|每股收益|自由现金流|市值|pe|估值|multiple|"
    r"price|价格|股息|dividend|利润|收入)[\s\S]{0,120}(?:变|升降|增减|变化|上涨|下跌|"
    r"提高|下降|上调|下调|差|比较|对比|vs\.?|versus|从|至|到|"
    r"changed|grew|rose|fell|increased|decreased|revised|vs\.?\s|compared)",
    re.I,
)
THESIS_DELTA = re.compile(
    r"(?:投资逻辑|论点|thesis|核心观点|核心逻辑|投资论点|看法|结论)[\s\S]{0,160}"
    r"(?:变|不变|unchanged|调整|修正|更新|强化|弱化|确认|推翻|维持|未变|未改|"
    r"updated|revised|confirmed|maintained|shifted)",
    re.I,
)
CONDITIONAL_CUE = re.compile(r"\b(?:if|when|once|unless|only\s+when)\b|若|如果|当|只有|仅在|一旦|触发", re.I)
PORTFOLIO_SPECIFIC_TRADE = re.compile(r"\b(?:buy|add|hold|reduce|sell)\b|加仓|减仓|清仓|增持|减持", re.I)
GENERIC_CHINESE_TRADE = re.compile(r"买入|持有|卖出")
PORTFOLIO_CONTEXT = re.compile(r"仓位|持仓|组合|账户|股票|股份|头寸|position|portfolio|shares?|stake", re.I)
RULE_STYLE_TRADE = re.compile(r"(?:：|:|=>|→|则|就)\s*(?:买入|持有|卖出)")
EXPLICIT_THRESHOLD = re.compile(
    r"(?:[<>≤≥]=?\s*[$¥€£]?\s*\d)|(?:低于|高于|不高于|不低于|至少|至多|达到|超过|跌破|升破|below|above|at\s+least|at\s+most)[^\n]{0,16}[$¥€£]?\s*\d",
    re.I,
)
THESIS_BREAK = re.compile(r"thesis(?:-|\s)*break|thesis\s+broken|论点破坏|投资逻辑破坏|逻辑破坏", re.I)
NON_EXECUTABLE_RANGE_SUMMARY = re.compile(
    r"只.*(?:汇总|摘要)|不在此处定义执行|执行(?:条件|规则|来源)[^\n]*Action Matrix|仅见[^\n]*Action Matrix",
    re.I,
)


def normalize(text: str) -> str:
    return (
        text.replace("×", "x")
        .replace("Ｘ", "x")
        .replace("＊", "*")
        .replace("　", " ")
        .lower()
    )


def has_discount_row(text: str, row: str) -> bool:
    norm = normalize(text)
    if row == "10y_x1":
        return bool(
            re.search(r"10\s*y[^|\n]{0,30}(x|\*)\s*1", norm)
            or re.search(r"10\s*年[^|\n]{0,30}(x|\*)\s*1", norm)
            or re.search(r"国债[^|\n]{0,30}(x|\*)\s*1", norm)
        )
    if row == "10y_x2":
        return bool(
            re.search(r"10\s*y[^|\n]{0,30}(x|\*)\s*2", norm)
            or re.search(r"10\s*年[^|\n]{0,30}(x|\*)\s*2", norm)
            or re.search(r"国债[^|\n]{0,30}(x|\*)\s*2", norm)
        )
    if row == "8":
        return bool(re.search(r"(^|[|>\n\r\t -])8\s*%", norm))
    if row == "10":
        return bool(re.search(r"(^|[|>\n\r\t -])10\s*%", norm))
    raise ValueError(row)


def top_sections(text: str) -> list[tuple[str, int]]:
    sections: list[tuple[str, int]] = []
    for match in re.finditer(r"^##\s+(.+?)\s*$", text, re.M):
        sections.append((match.group(1).strip(), match.start()))
    return sections


def section_body(text: str, heading_regex: str) -> str:
    match = re.search(rf"^##\s+{heading_regex}.*$", text, re.M)
    if not match:
        return ""
    next_match = re.search(r"^##\s+", text[match.end() :], re.M)
    if not next_match:
        return text[match.end() :]
    return text[match.end() : match.end() + next_match.start()]


def top_section_token(title: str) -> str | None:
    if re.search(r"First-Page Verdict|首页结论|一页结论", title, re.I):
        return "First-Page Verdict"
    if re.search(r"Evidence Ledger|证据台账|证据账本", title, re.I):
        return "Evidence Ledger"
    number_match = re.match(r"(\d+)\.", title)
    if number_match:
        return f"{number_match.group(1)}."
    if re.search(r"Source Links|Sources|来源链接|参考资料|参考来源|资料来源", title, re.I):
        return "Sources"
    return title


def researchability_values(first_page: str) -> tuple[str | None, str | None, str | None]:
    def value(label: str) -> str | None:
        match = re.search(rf"(?:{label})[^\n]*?(?:[:：|])\s*(A|B|C|高|中|低|high|medium|low)\b", first_page, re.I)
        return match.group(1).lower() if match else None

    return value(r"信息丰富度|information richness"), value(r"AI\s*研究置信度|AI research confidence"), value(r"投资确定性|investment certainty")


def action_matrix_errors(text: str, module8: str) -> list[str]:
    errors: list[str] = []
    headings = list(re.finditer(r"^#{1,6}\s+Action Matrix\s*$", text, re.M))
    if len(headings) != 1:
        errors.append(f"report must contain exactly one heading named 'Action Matrix'; found {len(headings)}")
    module_headings = list(re.finditer(r"^###\s+Action Matrix\s*$", module8, re.M))
    if len(module_headings) != 1:
        errors.append("module 8 must contain exactly one '### Action Matrix' heading")
        return errors
    table = find_action_matrix_table(module8)
    if table is None:
        # The shared locator collapses heading/table/header problems to None;
        # re-derive only the detail needed for a lint-grade message so the
        # canonical locate contract stays single-sourced in validation_common.
        matrix_heading = module_headings[0]
        tail = module8[matrix_heading.end() :]
        next_heading = re.search(r"^#{1,6}\s+", tail, re.M)
        matrix_block = tail[: next_heading.start()] if next_heading else tail
        tables = list(iter_markdown_tables(matrix_block))
        if len(tables) != 1:
            errors.append(f"Action Matrix must contain exactly one Markdown table; found {len(tables)}")
        elif tables[0]["headers"] != ACTION_MATRIX_COLUMNS:
            errors.append(
                "Action Matrix columns must be exactly: Action | Trigger type | Executable condition | Position/execution"
            )
        return errors
    actions: set[str] = set()
    trigger_types: set[str] = set()
    executable_actions: set[str] = set()
    executable_trigger_types: set[str] = set()
    for row in table["rows"]:
        cells = row["cells"]
        if len(cells) != len(ACTION_MATRIX_COLUMNS):
            errors.append(f"Action Matrix row at line {row['line_number']} must have exactly four cells")
            continue
        action, trigger_type, condition, execution = (cell.strip() for cell in cells)
        actions.add(action.casefold())
        trigger_types.add(trigger_type.casefold())
        if not condition or not execution:
            errors.append(f"Action Matrix row for '{action or 'unknown'}' must include condition and execution")
            continue
        is_na = bool(NA_VALUE.search(condition) or NA_VALUE.search(execution))
        if is_na and action.casefold() not in {"buy", "add"}:
            errors.append(f"Action Matrix N/A is allowed only for Buy or Add, not '{action}'")
        if not is_na:
            executable_actions.add(action.casefold())
            executable_trigger_types.add(trigger_type.casefold())
    missing_actions = sorted(REQUIRED_ACTIONS - actions)
    missing_types = sorted(REQUIRED_TRIGGER_TYPES - trigger_types)
    if missing_actions:
        errors.append(f"Action Matrix missing actions: {', '.join(missing_actions)}")
    if missing_types:
        errors.append(f"Action Matrix missing trigger types: {', '.join(missing_types)}")
    missing_executable_actions = sorted({"hold", "reduce", "sell"} - executable_actions)
    missing_executable_types = sorted(REQUIRED_TRIGGER_TYPES - executable_trigger_types)
    if missing_executable_actions:
        errors.append(f"Action Matrix missing executable non-N/A actions: {', '.join(missing_executable_actions)}")
    if missing_executable_types:
        errors.append(f"Action Matrix missing executable non-N/A trigger types: {', '.join(missing_executable_types)}")
    return errors


def canonical_matrix_table_lines(text: str) -> set[int]:
    """Return only the exact canonical Action Matrix table line numbers."""
    lines = text.splitlines()
    heading_indexes = [
        index for index, line in enumerate(lines) if re.fullmatch(r"###\s+Action Matrix\s*", line)
    ]
    if len(heading_indexes) != 1:
        return set()
    index = heading_indexes[0] + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index + 1 >= len(lines):
        return set()
    headers = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
    if headers != ACTION_MATRIX_COLUMNS or not re.fullmatch(r"\|[\s:|-]+\|", lines[index + 1].strip()):
        return set()
    masked = {index + 1, index + 2}
    index += 2
    while index < len(lines) and lines[index].strip().startswith("|"):
        masked.add(index + 1)
        index += 1
    return masked


def has_portfolio_trade(line: str) -> bool:
    if PORTFOLIO_SPECIFIC_TRADE.search(line):
        return True
    return bool(
        GENERIC_CHINESE_TRADE.search(line)
        and (PORTFOLIO_CONTEXT.search(line) or RULE_STYLE_TRADE.search(line))
    )


def external_conditional_trade_errors(text: str) -> list[str]:
    """Flag only explicit conditional threshold trades outside the sole matrix."""
    masked_lines = canonical_matrix_table_lines(text)
    scan_text = text
    sources = re.search(r"^##\s+(?:Source Links|Sources|来源链接|参考资料|参考来源|资料来源)\b.*$", scan_text, re.M | re.I)
    if sources:
        scan_text = scan_text[: sources.start()]
    errors: list[str] = []
    in_fence = False
    for line_number, line in enumerate(scan_text.splitlines(), start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or line_number in masked_lines or line.lstrip().startswith(">"):
            continue
        if NON_EXECUTABLE_RANGE_SUMMARY.search(line):
            continue
        conditional_trade = EXPLICIT_THRESHOLD.search(line) and has_portfolio_trade(line)
        thesis_sell = THESIS_BREAK.search(line) and has_portfolio_trade(line)
        if conditional_trade or thesis_sell:
            errors.append(f"conditional threshold trade must appear only in Action Matrix (line {line_number})")
    return errors


def tax_identity_errors(text: str) -> list[str]:
    """Gate 2 (Batch 2C): the report must declare a tax identity context.

    Tax friction differs by investor type (A-share, US-listed, HK-listed, etc.),
    so a report that silently omits tax considerations can mislead. A declared
    identity (e.g. 税务身份=中国大陆个人, a US-listed investor) satisfies the gate;
    an explicit N/A is allowed only with a stated reason.
    """
    if TAX_IDENTITY.search(text):
        return []
    if TAX_IDENTITY_NA.search(text):
        return []
    return ["report must declare a tax identity (e.g. 税务身份=中国大陆个人) or state N/A with a reason"]


def opportunity_cost_benchmark_errors(text: str) -> list[str]:
    """Gate 3 (Batch 2C): a valuation report must reference an opportunity-cost
    benchmark for every rating.

    The contract already enforces an opportunity-cost pass for Buy ratings in
    module 9. This gate extends the requirement: whenever the report mentions
    valuation, it must also reference an opportunity-cost benchmark (10Y
    government bond, index return, or explicit alternative) somewhere in the
    report, regardless of the final rating.
    """
    if not VALUATION_CUE.search(text):
        return []
    if OPPORTUNITY_COST_BENCHMARK.search(text):
        return []
    return [
        "report mentions valuation but references no opportunity-cost benchmark "
        "(10Y government bond, index return, or explicit alternative)"
    ]


def previous_report_delta_errors(text: str) -> list[str]:
    """Gate 4 (Batch 2C): when a previous report is referenced, the report must
    contain a delta/comparison section.

    The pack's `previous_report` field or in-report prior-report language
    triggers this gate. It then requires at least: a rating change (or explicit
    "unchanged"), a key metric change, and a thesis change (or explicit
    "unchanged"). This prevents reruns that silently drop the comparison.
    """
    if not PREVIOUS_REPORT_CUE.search(text):
        return []
    errors: list[str] = []
    if not RATING_DELTA.search(text):
        errors.append(
            "previous-report delta must state the rating change or an explicit "
            "'unchanged' (评级维持/不变)"
        )
    if not METRIC_DELTA.search(text):
        errors.append(
            "previous-report delta must compare key metrics against the prior report"
        )
    if not THESIS_DELTA.search(text):
        errors.append(
            "previous-report delta must state the thesis change or an explicit "
            "'unchanged' (投资逻辑不变)"
        )
    return errors



# --- Analysis Density Gates (PRD: analysis-density) ---

CYCLICAL_KEYWORDS = re.compile(
    r"存储|半导体|周期股|cyclical|semiconductor|memory|DRAM|NAND|航运|"
    r"能源|石油|银行|券商|汽车|钢铁|化工|mining|oil|gas|shipping|bank",
    re.I,
)
HIGH_CAPEX = re.compile(r"(?:capex|资本开支|capital\s+expenditure)[^\n]{0,30}(?:\$?\s*(\d{2,4})(?:\.\d+)?)\s*[Bb]", re.I)
PEER_TABLE_METRICS = re.compile(r"PE|P/E|利润率|margin|增速|growth|市占率|share|市值|cap", re.I)
NO_COMPETITOR_CLAIM = re.compile(r"无直接可比竞品|no\s+direct\s+competitor|无可比", re.I)


def moat_score_table_errors(module3: str) -> list[str]:
    """Gate 1: module 3 must contain a quantified moat score table.

    Requires a Markdown table with at least 5 data rows, a column named
    'score' or '分数', and non-empty evidence per row.
    """
    tables = list(iter_markdown_tables(module3))
    for table in tables:
        headers = [h.strip().lower() for h in table["headers"]]
        score_col = None
        for i, h in enumerate(headers):
            if "score" in h or "分数" in h:
                score_col = i
                break
        if score_col is None:
            continue
        data_rows = []
        for r in table["rows"]:
            cells = r.get("cells", []) if isinstance(r, dict) else r
            if any(c.strip() for c in cells):
                data_rows.append(r)
        if len(data_rows) >= 5:
            return []
    return ["module 3 must include a moat score table with at least 5 scored dimensions (column named 'score' or '分数')"]


def multi_valuation_gate_errors(text: str, module4: str) -> list[str]:
    """Gate 2: high-capex or cyclical companies must have multi-scenario valuation.

    Triggers when capex >= $50B or cyclical industry keywords are present.
    Requires module 4 to have a table with 3+ rows covering multiple valuation
    scenarios (peak/mid-cycle/normalized/EV-FCF).
    """
    triggered = False
    for m in HIGH_CAPEX.finditer(text):
        val = float(m.group(1))
        if val >= 50:
            triggered = True
            break
    if not triggered and CYCLICAL_KEYWORDS.search(text):
        triggered = True
    if not triggered:
        return []

    scenario_keywords = re.compile(r"峰值|新周期|中枢|旧周期|平准|normalized|peak|mid.?cycle|EV/FCF|EV.?FCF", re.I)
    tables = list(iter_markdown_tables(module4))
    for table in tables:
        data_rows = []
        for r in table["rows"]:
            cells = r.get("cells", []) if isinstance(r, dict) else r
            if any(c.strip() for c in cells):
                data_rows.append(cells)
        if len(data_rows) < 3:
            continue
        table_text = " ".join(" ".join(r) for r in [table["headers"]] + data_rows)
        if scenario_keywords.search(table_text):
            return []
    return ["module 4 must include a multi-scenario valuation gate table (peak/mid-cycle/normalized) for high-capex or cyclical companies"]


def peer_comparison_errors(text: str) -> list[str]:
    """Gate 3: report must include a peer comparison table with 2+ competitors.

    Looks for a table whose first column or headers reference at least 2
    non-target company names and include at least 2 comparison metrics.
    """
    if NO_COMPETITOR_CLAIM.search(text):
        return []
    tables = list(iter_markdown_tables(text))
    for table in tables:
        header_text = " ".join(table["headers"])
        all_text = header_text + " " + " ".join(" ".join(r) for r in table["rows"])
        metric_count = len(PEER_TABLE_METRICS.findall(all_text))
        if metric_count >= 2:
            first_col = []
            for r in table["rows"]:
                cells = r.get("cells", []) if isinstance(r, dict) else r
                if cells and cells[0].strip():
                    first_col.append(cells[0].strip())
            companies = [c for c in first_col if len(c) > 1 and not c.replace(".", "").replace("-", "").isdigit()]
            if len(companies) >= 2:
                return []
    return ["report must include a peer comparison table with at least 2 competitors and 2+ metrics (or state '无直接可比竞品')"]


def variant_view_placement_errors(module6: str, module9: str) -> list[str]:
    """Gate 4: Variant View must be in module 9, not module 6."""
    errors = []
    if re.search(r"^###\s+Variant View\s*$", module6, re.M):
        errors.append("Variant View must be in module 9 (Final Verdict), not module 6")
    if not re.search(r"^###\s+Variant View\s*$", module9, re.M):
        errors.append("module 9 must include '### Variant View'")
    return errors


def lint_text(text: str) -> list[str]:
    errors: list[str] = []

    for label, pattern in REQUIRED_PATTERNS:
        if not pattern.search(text):
            errors.append(f"missing {label}")

    if re.match(r"\A---\s*\n.*?\n---\s*\n", text, re.S):
        errors.append("frontmatter must not appear in the report body")

    sections = top_sections(text)
    tokens = [top_section_token(title) for title, _ in sections]
    contract_tokens = [token for token in tokens if token != "Sources"]
    if contract_tokens[: len(EXPECTED_TOP_SECTIONS)] != EXPECTED_TOP_SECTIONS:
        errors.append(
           "top-level section order must be First-Page Verdict -> Evidence Ledger -> ## 1. through ## 9."
        )
    extra_before_sources = [
        token
        for token in contract_tokens
        if token not in EXPECTED_TOP_SECTIONS
    ]
    for token in extra_before_sources:
        errors.append(f"unexpected top-level section '{token}' inside report contract")

    if re.search(r"^##\s+Key Forces\s*$", text, re.M):
        errors.append("Key Forces must be a subsection inside module 1, not a top-level section")

    module1 = section_body(text, r"1\.")
    module3 = section_body(text, r"3\.")
    module4 = section_body(text, r"4\.")
    module6 = section_body(text, r"6\.")
    module8 = section_body(text, r"8\.")
    module9 = section_body(text, r"9\.")
    first_page = section_body(text, r"First-Page Verdict|首页结论|一页结论")

    report_type = re.search(r"报告类型\s*(?:[:：|])\s*(常规报告|最新财报更新)", first_page)
    if not report_type:
        errors.append("Researchability Record must declare 报告类型 as 常规报告 or 最新财报更新")

    richness, ai_confidence, investment_certainty = researchability_values(first_page)
    decision_confidence_match = re.search(r"(?:首页决策置信度|first-page confidence)[^\n]*?(?:[:：|])\s*(高|中|低|high|medium|low)\b", first_page, re.I)
    if richness not in {"a", "b", "c"}:
        errors.append("Researchability Record must declare information richness A, B, or C")
    confidence_rank = {"low": 1, "低": 1, "medium": 2, "中": 2, "high": 3, "高": 3}
    if ai_confidence not in confidence_rank:
        errors.append("Researchability Record must declare AI research confidence High, Medium, or Low")
    if investment_certainty not in confidence_rank:
        errors.append("Researchability Record must declare investment certainty High, Medium, or Low")
    if not decision_confidence_match:
        errors.append("Researchability Record must declare First-page Confidence High, Medium, or Low")
    if richness == "b" and confidence_rank.get(ai_confidence, 99) > 2:
        errors.append("B information richness caps AI research confidence at Medium")
    if richness == "c" and confidence_rank.get(ai_confidence, 99) > 1:
        errors.append("C information richness caps AI research confidence at Low")
    if ai_confidence and investment_certainty and ai_confidence != investment_certainty:
        explanation = re.search(r"(?:差异说明|mismatch explanation)\s*(?:[:：|])\s*([^|\n]{8,})", first_page, re.I)
        if not explanation:
            errors.append("Researchability Record needs a one-sentence mismatch explanation")

    if not re.search(r"^###\s+Key Forces\b", module1, re.M):
        errors.append("module 1 must include '### Key Forces'")
    is_latest_earnings_update = bool(report_type and report_type.group(1) == "最新财报更新")
    if is_latest_earnings_update:
        if not re.search(r"本次财报改变了什么", module1):
            errors.append("latest-earnings update must include '本次财报改变了什么' inside module 1")
        if not re.search(r"本次财报(没有|未)改变什么|本次财报没有改变了什么", module1):
            errors.append("latest-earnings update must include '本次财报没有改变什么' inside module 1")

    for label, pattern in [
        ("module 4 nominal 10-year payback", r"名义\s*10\s*年回本|名义十年回本"),
        ("module 4 discounted 10-year payback", r"贴现\s*10\s*年回本|贴现十年回本"),
        ("module 4 dual valuation", r"双估值|中周期|normalized|高\s*CapEx|EV/FCF"),
    ]:
        if not re.search(pattern, module4, re.I):
            errors.append(f"missing {label}")

    if not re.search(r"^###\s+Pre-Mortem\b|^###\s+预演失败\b", module8, re.M):
        errors.append("module 8 must include '### Pre-Mortem'")
    if re.search(r"^#{1,6}\s+(?:Action Triggers|动作触发)\s*$", text, re.M | re.I):
        errors.append("legacy 'Action Triggers' heading is not allowed; use the sole module 8 Action Matrix")
    errors.extend(action_matrix_errors(text, module8))
    errors.extend(external_conditional_trade_errors(text))
    errors.extend(tax_identity_errors(text))
    errors.extend(opportunity_cost_benchmark_errors(text))
    errors.extend(previous_report_delta_errors(text))
    errors.extend(moat_score_table_errors(module3))
    errors.extend(multi_valuation_gate_errors(text, module4))
    errors.extend(peer_comparison_errors(text))
    errors.extend(variant_view_placement_errors(module6, module9))
    if not re.search(r"###\s*三原则扣问", module9):
        errors.append("module 9 must include dedicated '### 三原则扣问'")

    missing_discount = [
        label
        for label, row in [
            ("10Y x1 discount row", "10y_x1"),
            ("10Y x2 discount row", "10y_x2"),
            ("8% discount row", "8"),
            ("10% discount row", "10"),
        ]
        if not has_discount_row(text, row)
    ]
    errors.extend(f"missing {item}" for item in missing_discount)

    if re.search(r"CapEx[^。\n]{0,80}[+＋-]\s*\d+(?:\.\d+)?\s*%", text, re.I) and not re.search(
        r"CapEx[\s\S]{0,500}(原因|主要由于|由于|来自|拆分|勘探|开发|产能建设|工作量)", text, re.I
    ):
        errors.append("CapEx growth is mentioned but no nearby reason/explanation is provided")

    if re.search(r"最终评级\s*\|[^|\n]*Buy|verdict:\s*Buy", text, re.I):
        if not re.search(r"持有\s*[=＝]\s*买入[\s\S]{0,300}(是|愿意|通过)", module9):
            errors.append("Buy rating requires a positive hold-equals-buy answer in module 9")
        if not re.search(r"机会成本[\s\S]{0,300}(胜出|明显|通过|高于)", module9):
            errors.append("Buy rating requires opportunity-cost pass in module 9")
        if not re.search(r"10\s*年回本[\s\S]{0,300}(通过|可解释)", module9):
            errors.append("Buy rating requires 10-year payback pass in module 9")

    return errors


def lint(path: Path) -> list[str]:
    return lint_text(path.read_text(encoding="utf-8"))


def run_fixture_tests(fixtures_dir: Path) -> int:
    failures = 0
    for path in sorted(fixtures_dir.glob("*.md")):
        errors = lint(path)
        should_pass = path.name.startswith("good-")
        if should_pass and errors:
            failures += 1
            print(f"FIXTURE FAIL {path.name}: expected pass")
            for error in errors:
                print(f"- {error}")
        if not should_pass and not errors:
            failures += 1
            print(f"FIXTURE FAIL {path.name}: expected fail")
    if failures:
        return 1
    print("FIXTURE TESTS PASS")
    return 0


def self_test() -> int:
    good_report = """> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；机会成本=美国 10Y 国债 ×2。

## First-Page Verdict
现价 / 当前价格：$10。最新财报：earnings release。最终评级 | Buy

### Researchability Record
| 项目 | 结论 |
|---|---|
| 报告类型 | 常规报告 |
| 信息丰富度 | A |
| AI 研究置信度 | 高 |
| 投资确定性 | 中 |
| 首页决策置信度 | 中 |
| 差异说明 | 证据完整但竞争格局仍使经济结果不确定。 |

## Evidence Ledger
| 指标 | 值 |
|---|---|
| 美国 10Y 国债 | 4.5% |

## 1. 华尔街式全景扫描 Overview

### Key Forces
- 需求强度。
- 成本结构。
- 估值锚。

## 2. 财务剖析 Financial Autopsy
CapEx +19.1%，主要由于产能建设提速。

## 3. 护城河 Moat Analysis
| 维度 | 分数 | 证据 |
|---|---|---|
| 品牌 | 4 | 复购率高 |
| 转换成本 | 3 | 续约率 90% |
| 网络效应 | 2 | 用户基数有限 |
| 成本优势 | 4 | 规模化生产 |
| 监管壁垒 | 3 | 牌照壁垒 |

### 竞品对比 Peer Comparison
| 公司 | PE | 利润率 | 增速 |
|---|---|---|---|
| 公司A | 15 | 30% | 10% |
| 公司B | 18 | 25% | 8% |

## 4. 极限估值 + 10 年回本数学审判

### 周期/高 CapEx 双估值闸门
EV/FCF 与中周期估值。

### 名义 10 年回本测试
名义 10 年回本通过。

### 贴现 10 年回本测试
| 贴现率 r | EPS 所需 g | 判断 |
|---|---:|---|
| 10Y 国债 ×1 | 1% | 通过 |
| 10Y 国债 ×2 | 5% | 观察 |
| 8% | 8% | 观察 |
| 10% | 10% | 偏难 |

## 5. 致命风险排序 Risk Ranking
## 6. 物理增长极限 Growth Potential
## 7. 机构视角 + 机会成本
## 8. 仓位与风控

### Pre-Mortem
失败路径：增长低于预期。

### Action Matrix
| Action | Trigger type | Executable condition | Position/execution |
|---|---|---|---|
| Buy | valuation | N/A - current action is not Buy | No position |
| Add | price | Price < $8 and operating gates pass | Add 1% |
| Hold | operating | Revenue >= $10B | Hold current position |
| Reduce | valuation | Price >= $20 | Reduce to 3% |
| Sell | thesis-break | Thesis broken | Exit position |

## 9. 最终判决 Final Verdict

### Variant View
市场共识：普通好公司。我们的判断：价格不够好。

### 三原则扣问
| 原则 | 回答 |
|---|---|
| 持有 = 买入 | 是，愿意买 |
| 沉没成本不是成本，机会成本才是真成本 | 机会成本胜出 |
| 10 年回本测试 | 通过 |

### Confidence Boundary
AI 研究置信度与投资确定性不同；差异说明见首页 Researchability Record。

## Sources
- Company IR
"""
    bad_report = good_report.replace("| 10Y 国债 ×1 | 1% | 通过 |\n", "")
    bad_key_forces = good_report.replace("## 1. 华尔街式全景扫描 Overview\n\n### Key Forces", "## Key Forces")
    bad_earnings_update = good_report.replace("| 报告类型 | 常规报告 |", "| 报告类型 | 最新财报更新 |")
    bad_researchability = good_report.replace("| 信息丰富度 | A |", "| 信息丰富度 | C |").replace("| AI 研究置信度 | 高 |", "| AI 研究置信度 | 中 |")

    with tempfile.TemporaryDirectory() as tmp:
        cases = {
            "good.md": (good_report, False),
            "bad_discount.md": (bad_report, True),
            "bad_key_forces.md": (bad_key_forces, True),
            "bad_earnings_update.md": (bad_earnings_update, True),
            "bad_researchability.md": (bad_researchability, True),
        }
        for name, (content, should_error) in cases.items():
            path = Path(tmp) / name
            path.write_text(content, encoding="utf-8")
            errors = lint(path)
            if should_error and not errors:
                print(f"SELF-TEST FAIL: {name} should fail")
                return 1
            if not should_error and errors:
                print(f"SELF-TEST FAIL: {name} should pass")
                for error in errors:
                    print(f"- {error}")
                return 1

    print("SELF-TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint a wall-street equity research Markdown report.")
    parser.add_argument("report", nargs="?", type=Path, help="Path to the Markdown report to lint")
    parser.add_argument("--self-test", action="store_true", help="Run built-in lint rule regression tests")
    parser.add_argument("--fixtures", type=Path, help="Run fixture tests from a directory")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.fixtures:
        return run_fixture_tests(args.fixtures)

    if args.report is None:
        parser.error("report is required unless --self-test or --fixtures is used")

    if not args.report.exists():
        print(f"ERROR: report not found: {args.report}", file=sys.stderr)
        return 2
    if args.report.suffix.lower() not in {".md", ".markdown"}:
        print(f"ERROR: expected a Markdown report, got: {args.report}", file=sys.stderr)
        return 2

    errors = lint(args.report)
    if errors:
        print(f"FAIL {args.report}")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

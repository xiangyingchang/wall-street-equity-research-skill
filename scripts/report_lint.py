#!/usr/bin/env python3
"""Lint an Obsidian equity research report for structure and content discipline."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path


REQUIRED_PATTERNS = [
    ("default input statement", re.compile(r"默认输入|input_", re.I)),
    ("First-Page Verdict", re.compile(r"First-Page Verdict|首页结论|一页结论", re.I)),
    ("Evidence Ledger", re.compile(r"Evidence Ledger|证据台账|证据账本", re.I)),
    ("Final Verdict", re.compile(r"Final Verdict|最终判决|最终结论", re.I)),
    ("source links", re.compile(r"Source Links|Sources|来源链接|参考资料|参考来源|资料来源", re.I)),
    ("current price", re.compile(r"现价|当前价格|close price|regular-session|after-hours|盘后|收盘价", re.I)),
    ("latest filing or earnings", re.compile(r"最新财报|最新季报|最新年报|earnings release|10-K|10-Q|20-F|6-K|HKEX|公告", re.I)),
    ("10Y government yield", re.compile(r"10Y|10 年|10年|国债|Treasury", re.I)),
    ("earnings changed/unchanged", re.compile(r"本次财报改变了什么|改变了什么|没有改变什么|未改变什么", re.I)),
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


def normalize(text: str) -> str:
    return (
        text.replace("×", "x")
        .replace("Ｘ", "x")
        .replace("＊", "*")
        .replace("　", " ")
        .lower()
    )


def has_discount_table_row(section: str, row: str) -> bool:
    lines = [line.strip() for line in section.splitlines() if "|" in line]
    if row == "10y_x1":
        return any(
            re.search(r"\|\s*(?:10\s*y|10\s*年|国债)[^|\n]{0,30}(x|\*)\s*1\s*\|", normalize(line))
            for line in lines
        )
    if row == "10y_x2":
        return any(
            re.search(r"\|\s*(?:10\s*y|10\s*年|国债)[^|\n]{0,30}(x|\*)\s*2\s*\|", normalize(line))
            for line in lines
        )
    if row == "8":
        return any(re.search(r"\|\s*8\s*%\s*\|", normalize(line)) for line in lines)
    if row == "10":
        return any(re.search(r"\|\s*10\s*%\s*\|", normalize(line)) for line in lines)
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


def subsection_body(text: str, heading_regex: str) -> str:
    match = re.search(rf"^###\s+{heading_regex}.*$", text, re.M)
    if not match:
        return ""
    next_match = re.search(r"^###\s+", text[match.end() :], re.M)
    if not next_match:
        return text[match.end() :]
    return text[match.end() : match.end() + next_match.start()]


def table_data_rows(section: str) -> list[str]:
    rows = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        if re.match(r"^\|\s*:?-{2,}", stripped):
            continue
        rows.append(stripped)
    return rows


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


def lint_text(text: str) -> list[str]:
    errors: list[str] = []

    for label, pattern in REQUIRED_PATTERNS:
        if not pattern.search(text):
            errors.append(f"missing {label}")

    if re.match(r"\A---\s*\n.*?\n---\s*\n", text, re.S):
        errors.append("frontmatter must not appear in the report body")

    if re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b|待填|待补", text, re.I):
        errors.append("report contains unresolved placeholder text")

    sections = top_sections(text)
    tokens = [top_section_token(title) for title, _ in sections]
    contract_tokens = [token for token in tokens if token != "Sources"]
    if contract_tokens != EXPECTED_TOP_SECTIONS:
        errors.append(
            "top-level section order must be exactly First-Page Verdict -> Evidence Ledger -> ## 1. through ## 9."
        )
    if tokens.count("Sources") != 1 or tokens[-1:] != ["Sources"]:
        errors.append("Sources must appear exactly once after module 9")

    if re.search(r"^##\s+Key Forces\s*$", text, re.M):
        errors.append("Key Forces must be a subsection inside module 1, not a top-level section")

    module1 = section_body(text, r"1\.")
    module3 = section_body(text, r"3\.")
    module4 = section_body(text, r"4\.")
    module5 = section_body(text, r"5\.")
    module8 = section_body(text, r"8\.")
    module9 = section_body(text, r"9\.")

    for number, body in ((str(i), section_body(text, rf"{i}\.")) for i in range(1, 10)):
        if not body.strip():
            errors.append(f"module {number} must contain report content")

    evidence = section_body(text, r"Evidence Ledger")
    if len(table_data_rows(evidence)) < 2:
        errors.append("Evidence Ledger must contain a header and at least one data row")

    sources = section_body(text, r"Sources")
    if not re.search(r"https://[^\s)<>]+", sources):
        errors.append("Sources must contain at least one real HTTPS URL")
    if re.search(r"https://(?:example\.com|example\.org)", sources, re.I):
        errors.append("Sources must not use example.com/example.org placeholders")

    if not re.search(r"^###\s+Key Forces\b", module1, re.M):
        errors.append("module 1 must include '### Key Forces'")
    if not re.search(r"本次财报改变了什么", module1):
        errors.append("module 1 Key Forces must include '本次财报改变了什么'")
    if not re.search(r"本次财报(没有|未)改变什么|本次财报没有改变了什么", module1):
        errors.append("module 1 Key Forces must include '本次财报没有改变什么'")

    if re.search(r"网络效应|network\s+effect", module3, re.I):
        if not re.search(r"用户|DAU|MAU|活跃|user|audience", module3, re.I):
            errors.append("network-effects moat must include current user scale")
        if not re.search(r"同比|环比|增长|下降|变化|YoY|QoQ|change", module3, re.I):
            errors.append("network-effects moat must include period-over-period change")
        if not re.search(r"参与度|互动|时长|展示|价格|ARPU|转化|engagement|monetization", module3, re.I):
            errors.append("network-effects moat must include engagement or monetization metric")

    for label, pattern in [
        ("module 4 nominal 10-year payback", r"名义\s*10\s*年回本|名义十年回本"),
        ("module 4 discounted 10-year payback", r"贴现\s*10\s*年回本|贴现十年回本"),
        ("module 4 dual valuation", r"双估值|中周期|normalized|高\s*CapEx|EV/FCF"),
    ]:
        if not re.search(pattern, module4, re.I):
            errors.append(f"missing {label}")

    liquidity_match = re.search(r"流动性结论\s*[:：]\s*(不构成约束|构成约束)", module5)
    if not liquidity_match:
        errors.append("module 5 must state whether liquidity is a constraint")
    elif liquidity_match.group(1) == "构成约束":
        for label, pattern in [
            ("90-day average value traded", r"90\s*日[^\n]{0,30}成交额"),
            ("position value", r"仓位金额"),
            ("stress participation rate", r"压力参与率"),
            ("stress exit days", r"压力退出天数"),
        ]:
            if not re.search(pattern, module5, re.I):
                errors.append(f"liquidity-constrained report missing {label}")

    action_triggers = subsection_body(module8, r"Action Triggers|动作触发")
    if not action_triggers:
        errors.append("module 8 must include Action Triggers content")
    else:
        for label, pattern in [
            ("price trigger", r"价格|price"),
            ("valuation trigger", r"估值|PE|倍数|回报"),
            ("operating trigger", r"经营|营收|利润|EPS|FCF|用户|DAU|MAU"),
            ("thesis-break trigger", r"thesis|逻辑|护城河|失效|破坏"),
        ]:
            if not re.search(pattern, action_triggers, re.I):
                errors.append(f"Action Triggers missing {label}")
        if not re.search(r"\d", action_triggers):
            errors.append("Action Triggers must contain at least one quantified condition")

    if not re.search(r"^###\s+Pre-Mortem\b|^###\s+预演失败\b", module8, re.M):
        errors.append("module 8 must include '### Pre-Mortem'")
    if not re.search(r"###\s*Variant View", module9):
        errors.append("module 9 must include dedicated '### Variant View'")
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
        if not has_discount_table_row(module4, row)
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
    good_report = """> 默认输入：长期 3-10 年；机会成本=美国 10Y 国债 ×2。

## First-Page Verdict
现价 / 当前价格：$10。最新财报：earnings release。最终评级 | Buy

## Evidence Ledger
| 指标 | 值 |
|---|---|
| 美国 10Y 国债 | 4.5% |

## 1. 华尔街式全景扫描 Overview

### Key Forces
- 本次财报改变了什么：增长放慢。
- 本次财报没有改变什么：护城河仍在。

业务判断：广告商业化仍是主要价值驱动。

## 2. 财务剖析 Financial Autopsy
收入和利润保持增长，CapEx +19.1%，主要由于产能建设提速。

## 3. 护城河 Moat Analysis
网络效应：用户规模 10 亿，较上年增长 8%；参与度和 ARPU 继续提升。

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
流动性结论：不构成约束。

## 6. 物理增长极限 Growth Potential
TAM 和竞争格局支持中期增长，但需跟踪利润率。

## 7. 机构视角 + 机会成本
机会成本比较：美国 10Y 国债 ×2。

## 8. 仓位与风控
仓位与风险边界：当前仓位需受估值约束。

### Pre-Mortem
失败路径：增长低于预期。

### Action Triggers
价格 ≤ $8；估值低于 20x；经营增长低于 10% 时复核；thesis 逻辑破坏时卖出。

## 9. 最终判决 Final Verdict

### Variant View
市场共识：普通好公司。我们的判断：价格不够好。

### 三原则扣问
| 原则 | 回答 |
|---|---|
| 持有 = 买入 | 是，愿意买 |
| 沉没成本不是成本，机会成本才是真成本 | 机会成本胜出 |
| 10 年回本测试 | 通过 |

## Sources
- [Company IR](https://investor.example.invalid/earnings)
"""
    bad_report = good_report.replace("| 10Y 国债 ×1 | 1% | 通过 |\n", "")
    bad_key_forces = good_report.replace("## 1. 华尔街式全景扫描 Overview\n\n### Key Forces", "## Key Forces")
    bad_source = good_report.replace("https://investor.example.invalid/earnings", "")
    bad_duplicate = good_report.replace("## Sources\n", "## 9. Duplicate\nextra\n\n## Sources\n", 1)
    bad_liquidity = good_report.replace("流动性结论：不构成约束。", "流动性结论：构成约束。")
    bad_network = good_report.replace("用户规模 10 亿，较上年增长 8%；参与度和 ARPU 继续提升。", "护城河仍然强。")
    bad_placeholder = good_report.replace("业务判断：广告商业化仍是主要价值驱动。", "业务判断：TODO")

    with tempfile.TemporaryDirectory() as tmp:
        cases = {
            "good.md": (good_report, False),
            "bad_discount.md": (bad_report, True),
            "bad_key_forces.md": (bad_key_forces, True),
            "bad_source.md": (bad_source, True),
            "bad_duplicate.md": (bad_duplicate, True),
            "bad_liquidity.md": (bad_liquidity, True),
            "bad_network.md": (bad_network, True),
            "bad_placeholder.md": (bad_placeholder, True),
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

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
    "10.",
    "11.",
]


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
            "top-level section order must be First-Page Verdict -> Evidence Ledger -> ## 1. through ## 11."
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
    module4 = section_body(text, r"4\.")
    module10 = section_body(text, r"10\.")
    module11 = section_body(text, r"11\.")

    if not re.search(r"^###\s+Key Forces\b", module1, re.M):
        errors.append("module 1 must include '### Key Forces'")
    if not re.search(r"本次财报改变了什么", module1):
        errors.append("module 1 Key Forces must include '本次财报改变了什么'")
    if not re.search(r"本次财报(没有|未)改变什么|本次财报没有改变了什么", module1):
        errors.append("module 1 Key Forces must include '本次财报没有改变什么'")

    for label, pattern in [
        ("module 4 nominal 10-year payback", r"名义\s*10\s*年回本|名义十年回本"),
        ("module 4 discounted 10-year payback", r"贴现\s*10\s*年回本|贴现十年回本"),
        ("module 4 dual valuation", r"双估值|中周期|normalized|高\s*CapEx|EV/FCF"),
    ]:
        if not re.search(pattern, module4, re.I):
            errors.append(f"missing {label}")

    if not re.search(r"^###\s+Pre-Mortem\b|^###\s+预演失败\b", module10, re.M):
        errors.append("module 10 must include '### Pre-Mortem'")
    if not re.search(r"^###\s+Action Triggers\b|^###\s+动作触发", module10, re.M):
        errors.append("module 10 must include '### Action Triggers'")
    if not re.search(r"###\s*三原则扣问", module11):
        errors.append("module 11 must include dedicated '### 三原则扣问'")

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
        if not re.search(r"持有\s*[=＝]\s*买入[\s\S]{0,300}(是|愿意|通过)", module11):
            errors.append("Buy rating requires a positive hold-equals-buy answer in module 11")
        if not re.search(r"机会成本[\s\S]{0,300}(胜出|明显|通过|高于)", module11):
            errors.append("Buy rating requires opportunity-cost pass in module 11")
        if not re.search(r"10\s*年回本[\s\S]{0,300}(通过|可解释)", module11):
            errors.append("Buy rating requires 10-year payback pass in module 11")

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

## 2. 财务剖析 Financial Autopsy
CapEx +19.1%，主要由于产能建设提速。

## 3. 护城河 Moat Analysis

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

## 5. 流动性黑洞
## 6. 致命风险排序 Risk Ranking
## 7. 物理增长极限 Growth Potential
## 8. 真实到手收益 + 税收摩擦
## 9. 机构视角 + 机会成本
## 10. 仓位与风控

### Pre-Mortem
失败路径：增长低于预期。

### Action Triggers
买入 / 加仓 / 持有 / 减仓 / 卖出条件。

## 11. 最终判决 Final Verdict

### Variant View
市场共识：普通好公司。我们的判断：价格不够好。

### 三原则扣问
| 原则 | 回答 |
|---|---|
| 持有 = 买入 | 是，愿意买 |
| 沉没成本不是成本，机会成本才是真成本 | 机会成本胜出 |
| 10 年回本测试 | 通过 |

## Sources
- Company IR
"""
    bad_report = good_report.replace("| 10Y 国债 ×1 | 1% | 通过 |\n", "")
    bad_key_forces = good_report.replace("## 1. 华尔街式全景扫描 Overview\n\n### Key Forces", "## Key Forces")

    with tempfile.TemporaryDirectory() as tmp:
        cases = {
            "good.md": (good_report, False),
            "bad_discount.md": (bad_report, True),
            "bad_key_forces.md": (bad_key_forces, True),
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

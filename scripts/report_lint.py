#!/usr/bin/env python3
"""Lint an Obsidian equity research report for required contract sections."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path


REQUIRED_PATTERNS = [
    ("frontmatter", re.compile(r"\A---\s*\n.*?\n---\s*\n", re.S)),
    ("default input statement", re.compile(r"默认输入|input_", re.I)),
    ("First-Page Verdict", re.compile(r"First-Page Verdict|首页结论|一页结论", re.I)),
    ("Evidence Ledger", re.compile(r"Evidence Ledger|证据台账|证据账本", re.I)),
    ("Final Verdict", re.compile(r"Final Verdict|最终判决|最终结论", re.I)),
    ("source links", re.compile(r"Source Links|Sources|来源链接|参考资料|参考来源|资料来源", re.I)),
    ("current price", re.compile(r"现价|当前价格|close price|regular-session|after-hours|盘后|收盘价", re.I)),
    ("latest filing or earnings", re.compile(r"最新财报|最新季报|最新年报|earnings release|10-K|10-Q|20-F|6-K|HKEX|公告", re.I)),
    ("10Y government yield", re.compile(r"10Y|10 年|10年|国债|Treasury", re.I)),
    ("three-principle heading", re.compile(r"三原则扣问|三条投资纪律", re.I)),
    ("hold equals buy", re.compile(r"持有\s*[=＝]\s*买入|持有等于买入", re.I)),
    ("sunk cost discipline", re.compile(r"沉没成本|机会成本才是真成本|opportunity cost", re.I)),
    ("10-year payback discipline", re.compile(r"10\s*年回本|十年回本|10-year payback", re.I)),
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


def lint(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    for label, pattern in REQUIRED_PATTERNS:
        if not pattern.search(text):
            errors.append(f"missing {label}")

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

    for section_number in range(1, 12):
        if not re.search(rf"^##\s+{section_number}\.", text, re.M):
            errors.append(f"missing module heading '## {section_number}.'")

    if re.search(r"###\s*三原则扣问", text) is None:
        errors.append("missing dedicated '### 三原则扣问' heading")

    return errors


def self_test() -> int:
    good_report = """---
title: Test
---

> 默认输入：长期 3-10 年；机会成本=美国 10Y 国债 ×2。

## First-Page Verdict
现价 / 当前价格：$10。最新财报：earnings release。

## Evidence Ledger
| 指标 | 值 |
|---|---|
| 美国 10Y 国债 | 4.5% |

## 1. 华尔街式全景扫描 Overview
## 2. 财务剖析 Financial Autopsy
## 3. 护城河 Moat Analysis
## 4. 极限估值 + 10 年回本数学审判

### 贴现 10 年回本测试（四档）
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
## 11. 最终判决 Final Verdict

### 三原则扣问
| 原则 | 回答 |
|---|---|
| 持有 = 买入 | 不买 |
| 沉没成本不是成本，机会成本才是真成本 | 不胜出 |
| 10 年回本测试 | 不通过 |

## 资料来源
- Company IR
"""
    bad_report = good_report.replace("| 10Y 国债 ×1 | 1% | 通过 |\n", "")

    with tempfile.TemporaryDirectory() as tmp:
        good_path = Path(tmp) / "good.md"
        bad_path = Path(tmp) / "bad.md"
        good_path.write_text(good_report, encoding="utf-8")
        bad_path.write_text(bad_report, encoding="utf-8")

        good_errors = lint(good_path)
        bad_errors = lint(bad_path)

    if good_errors:
        print("SELF-TEST FAIL: valid sample did not pass")
        for error in good_errors:
            print(f"- {error}")
        return 1

    if not any("10Y x1 discount row" in error for error in bad_errors):
        print("SELF-TEST FAIL: invalid sample did not fail on missing 10Y x1 row")
        for error in bad_errors:
            print(f"- {error}")
        return 1

    print("SELF-TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint a wall-street equity research Markdown report.")
    parser.add_argument("report", nargs="?", type=Path, help="Path to the Markdown report to lint")
    parser.add_argument("--self-test", action="store_true", help="Run built-in lint rule regression tests")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if args.report is None:
        parser.error("report is required unless --self-test is used")

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

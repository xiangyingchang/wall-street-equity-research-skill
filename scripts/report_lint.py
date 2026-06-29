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


def frontmatter_verdict(text: str) -> str | None:
    match = re.search(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        return None
    verdict = re.search(r"^verdict:\s*(.+?)\s*$", match.group(1), re.I | re.M)
    if not verdict:
        return None
    return verdict.group(1).strip().strip("\"'")


def has_prior_report(text: str) -> bool:
    return bool(
        re.search(r"^previous_report:\s*\S+", text, re.I | re.M)
        or re.search(r"旧报告|上次报告|prior report|previous report", text, re.I)
    )


def has_prior_report_delta(text: str) -> bool:
    return bool(re.search(r"与.*(旧报告|上次报告).*差异|prior report.*delta|changes vs", text, re.I))


def buy_like_language_errors(text: str, verdict: str | None) -> list[str]:
    if not verdict or re.search(r"\bBuy\b", verdict, re.I):
        return []

    errors: list[str] = []
    risky_patterns = [
        ("可买区", re.compile(r"可买区")),
        ("可以买", re.compile(r"可以买")),
        ("主动买入", re.compile(r"主动\s*买入|主动\s*Buy", re.I)),
        ("建仓", re.compile(r"建仓")),
    ]
    guard = re.compile(
        r"观察仓|观察性|试探区|小仓观察|不构成\s*(主动\s*)?Buy|不是\s*(主动\s*)?Buy|not\s+a\s+Buy|observation",
        re.I,
    )

    for label, pattern in risky_patterns:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 120)
            end = min(len(text), match.end() + 120)
            context = text[start:end]
            if guard.search(context):
                continue
            line = text.count("\n", 0, match.start()) + 1
            errors.append(
                f"non-Buy verdict uses buy-like language '{label}' without observation-only qualifier near line {line}"
            )
    return errors


def lint(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    verdict = frontmatter_verdict(text)

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

    if has_prior_report(text) and not has_prior_report_delta(text):
        errors.append("missing prior-report delta section")

    errors.extend(buy_like_language_errors(text, verdict))

    return errors


def self_test() -> int:
    good_report = """---
title: Test
verdict: Watchlist
previous_report: old.md
---

> 默认输入：长期 3-10 年；机会成本=美国 10Y 国债 ×2。

## First-Page Verdict
现价 / 当前价格：$10。最新财报：earnings release。

## 与上次报告差异
| 项目 | 旧 | 新 |
|---|---:|---:|
| 评级 | Watchlist | Watchlist |

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
    non_buy_buy_language = good_report.replace(
        "## Evidence Ledger",
        "## Evidence Ledger\n\n| 价格区间 | 动作 |\n|---|---|\n| $10-12 | 可买区 |\n",
    )
    missing_delta = good_report.replace(
        """## 与上次报告差异
| 项目 | 旧 | 新 |
|---|---:|---:|
| 评级 | Watchlist | Watchlist |

""",
        "",
    )

    with tempfile.TemporaryDirectory() as tmp:
        good_path = Path(tmp) / "good.md"
        bad_path = Path(tmp) / "bad.md"
        non_buy_path = Path(tmp) / "non-buy.md"
        missing_delta_path = Path(tmp) / "missing-delta.md"
        good_path.write_text(good_report, encoding="utf-8")
        bad_path.write_text(bad_report, encoding="utf-8")
        non_buy_path.write_text(non_buy_buy_language, encoding="utf-8")
        missing_delta_path.write_text(missing_delta, encoding="utf-8")

        good_errors = lint(good_path)
        bad_errors = lint(bad_path)
        non_buy_errors = lint(non_buy_path)
        missing_delta_errors = lint(missing_delta_path)

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

    if not any("buy-like language" in error for error in non_buy_errors):
        print("SELF-TEST FAIL: non-Buy sample did not fail on buy-like language")
        for error in non_buy_errors:
            print(f"- {error}")
        return 1

    if not any("prior-report delta" in error for error in missing_delta_errors):
        print("SELF-TEST FAIL: prior-report sample did not fail on missing delta section")
        for error in missing_delta_errors:
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

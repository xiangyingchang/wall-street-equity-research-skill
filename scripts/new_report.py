#!/usr/bin/env python3
"""Create a new Obsidian equity report from the canonical template."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_DIR / "templates" / "full-report.md"


def render(template: str, values: dict[str, str]) -> str:
    text = template
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a report skeleton from templates/full-report.md.")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--verdict", default="TODO")
    parser.add_argument("--action", default="TODO")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.out.exists() and not args.force:
        raise SystemExit(f"ERROR: output exists, pass --force to overwrite: {args.out}")

    template = TEMPLATE.read_text(encoding="utf-8")
    report = render(
        template,
        {
            "ticker": args.ticker,
            "company": args.company,
            "market": args.market,
            "date": args.date,
            "verdict": args.verdict,
            "action": args.action,
        },
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

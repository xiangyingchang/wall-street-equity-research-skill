#!/usr/bin/env python3
"""Deterministic valuation math and action resolution.

This module does not fetch data. It turns explicitly supplied, auditable inputs
into reproducible IRR, reverse-expectation, and action-resolution outputs.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Any

getcontext().prec = 50

D = Decimal


def dec(value: str | int | float | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else D(str(value))


def q(value: Decimal, places: str = "0.0001") -> str:
    return str(value.quantize(D(places), rounding=ROUND_HALF_UP))


def annualized_return(total_multiple: Decimal, years: int) -> Decimal:
    if total_multiple <= 0 or years <= 0:
        raise ValueError("total_multiple and years must be positive")
    return total_multiple ** (D(1) / D(years)) - D(1)


def scenario_irr(
    *,
    current_price: Decimal,
    starting_eps: Decimal,
    eps_cagr: Decimal,
    exit_pe: Decimal,
    years: int,
    annual_dividend_per_share: Decimal = D(0),
    annual_dividend_yield: Decimal | None = None,
    share_count_cagr: Decimal | None = None,
    metric_mode: str = "eps",
) -> dict[str, str]:
    if current_price <= 0 or starting_eps <= 0 or exit_pe <= 0 or years <= 0:
        raise ValueError("price, EPS, exit PE, and years must be positive")
    if metric_mode not in {"eps", "net_income"}:
        raise ValueError("metric_mode must be eps or net_income")
    if metric_mode == "eps" and share_count_cagr not in {None, D(0)}:
        raise ValueError(
            "share_count_cagr cannot be supplied with EPS CAGR; buybacks/dilution are already embedded in per-share growth"
        )

    terminal_metric = starting_eps * (D(1) + eps_cagr) ** years
    if metric_mode == "net_income":
        if share_count_cagr is None:
            raise ValueError("net_income mode requires share_count_cagr")
        terminal_eps = terminal_metric / ((D(1) + share_count_cagr) ** years)
    else:
        terminal_eps = terminal_metric

    terminal_price = terminal_eps * exit_pe
    if annual_dividend_yield is not None:
        if annual_dividend_per_share != 0:
            raise ValueError("use either dividend_per_share or dividend_yield, not both")
        annual_dividend_per_share = current_price * annual_dividend_yield
    cumulative_dividends = annual_dividend_per_share * years
    ending_value = terminal_price + cumulative_dividends
    total_multiple = ending_value / current_price
    irr = annualized_return(total_multiple, years)

    return {
        "terminal_eps": q(terminal_eps),
        "terminal_price": q(terminal_price),
        "cumulative_dividends": q(cumulative_dividends),
        "ending_value": q(ending_value),
        "total_return_pct": q((total_multiple - D(1)) * D(100), "0.01"),
        "irr_pct": q(irr * D(100), "0.01"),
    }


def reverse_expectations(
    *,
    current_price: Decimal,
    starting_eps: Decimal,
    target_return: Decimal,
    exit_pe: Decimal,
    years: int,
    annual_dividend_per_share: Decimal = D(0),
) -> dict[str, str]:
    if min(current_price, starting_eps, exit_pe) <= 0 or years <= 0:
        raise ValueError("price, starting EPS, exit PE, and years must be positive")
    required_ending_value = current_price * (D(1) + target_return) ** years
    cumulative_dividends = annual_dividend_per_share * years
    required_terminal_price = required_ending_value - cumulative_dividends
    if required_terminal_price <= 0:
        raise ValueError("dividends exceed required ending value")
    required_terminal_eps = required_terminal_price / exit_pe
    required_eps_cagr = (required_terminal_eps / starting_eps) ** (D(1) / D(years)) - D(1)
    return {
        "required_ending_value": q(required_ending_value),
        "cumulative_dividends": q(cumulative_dividends),
        "required_terminal_price": q(required_terminal_price),
        "required_terminal_eps": q(required_terminal_eps),
        "required_eps_cagr_pct": q(required_eps_cagr * D(100), "0.01"),
    }


def resolve_action(payload: dict[str, Any]) -> dict[str, Any]:
    """Resolve explicit booleans; never infer facts from prose.

    Payload schema:
      current_action: optional report action
      rules: [{id, action, triggered, priority?}]

    Priorities default to SELL 50, REDUCE 40, ADD 30, BUY 20, HOLD 10.
    If no rule triggers, resolution is REVIEW. Conflicting same-priority actions
    also resolve to REVIEW.
    """
    priorities = {"SELL": 50, "REDUCE": 40, "ADD": 30, "BUY": 20, "HOLD": 10}
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules must be a non-empty list")
    evaluated: list[dict[str, Any]] = []
    triggered: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("each rule must be an object")
        action = str(rule.get("action", "")).upper()
        if action not in priorities:
            raise ValueError(f"unsupported action: {action}")
        if type(rule.get("triggered")) is not bool:
            raise ValueError(f"rule {rule.get('id')} triggered must be boolean")
        item = {
            "id": str(rule.get("id", "")),
            "action": action,
            "triggered": rule["triggered"],
            "priority": int(rule.get("priority", priorities[action])),
        }
        evaluated.append(item)
        if item["triggered"]:
            triggered.append(item)

    if not triggered:
        resolved = "REVIEW"
    else:
        top = max(item["priority"] for item in triggered)
        actions = {item["action"] for item in triggered if item["priority"] == top}
        resolved = next(iter(actions)) if len(actions) == 1 else "REVIEW"

    current = payload.get("current_action")
    matches = None if current is None else str(current).upper() == resolved
    return {
        "evaluated_rules": evaluated,
        "triggered_rule_ids": [item["id"] for item in triggered],
        "resolved_action": resolved,
        "reported_action": None if current is None else str(current).upper(),
        "reported_action_matches": matches,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    irr = sub.add_parser("irr")
    irr.add_argument("--current-price", required=True)
    irr.add_argument("--starting-eps", required=True)
    irr.add_argument("--eps-cagr", required=True, help="decimal, e.g. 0.08")
    irr.add_argument("--exit-pe", required=True)
    irr.add_argument("--years", type=int, required=True)
    irr.add_argument("--annual-dividend-per-share", default="0")
    irr.add_argument("--annual-dividend-yield")
    irr.add_argument("--share-count-cagr")
    irr.add_argument("--metric-mode", choices=["eps", "net_income"], default="eps")

    rev = sub.add_parser("reverse")
    rev.add_argument("--current-price", required=True)
    rev.add_argument("--starting-eps", required=True)
    rev.add_argument("--target-return", required=True, help="decimal, e.g. 0.094")
    rev.add_argument("--exit-pe", required=True)
    rev.add_argument("--years", type=int, required=True)
    rev.add_argument("--annual-dividend-per-share", default="0")

    resolve = sub.add_parser("resolve-action")
    resolve.add_argument("--input", required=True, help="JSON file path or '-' for stdin")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "irr":
        result = scenario_irr(
            current_price=dec(args.current_price),
            starting_eps=dec(args.starting_eps),
            eps_cagr=dec(args.eps_cagr),
            exit_pe=dec(args.exit_pe),
            years=args.years,
            annual_dividend_per_share=dec(args.annual_dividend_per_share),
            annual_dividend_yield=None if args.annual_dividend_yield is None else dec(args.annual_dividend_yield),
            share_count_cagr=None if args.share_count_cagr is None else dec(args.share_count_cagr),
            metric_mode=args.metric_mode,
        )
    elif args.command == "reverse":
        result = reverse_expectations(
            current_price=dec(args.current_price),
            starting_eps=dec(args.starting_eps),
            target_return=dec(args.target_return),
            exit_pe=dec(args.exit_pe),
            years=args.years,
            annual_dividend_per_share=dec(args.annual_dividend_per_share),
        )
    else:
        import sys
        text = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
        result = resolve_action(json.loads(text))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

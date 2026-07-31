#!/usr/bin/env python3
"""Deterministic valuation math, bridge calculation, and action evaluation.

This module never fetches data. It turns explicitly supplied, auditable inputs
into reproducible EPS bridges, IRR, reverse-expectation, and action outputs.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Any

_VALUATION_PREC = 50
_PRIORITIES = {"SELL": 50, "REDUCE": 40, "ADD": 30, "BUY": 20, "HOLD": 10}
_NUMERIC_OPERATORS = {"<", "<=", ">", ">=", "==", "!="}

D = Decimal


def dec(value: str | int | float | Decimal) -> Decimal:
    result = value if isinstance(value, Decimal) else D(str(value))
    if not result.is_finite():
        raise ValueError("numeric inputs must be finite")
    return result


def q(value: Decimal, places: str = "0.0001") -> str:
    return str(value.quantize(D(places), rounding=ROUND_HALF_UP))


def annualized_return(total_multiple: Decimal, years: int) -> Decimal:
    if total_multiple <= 0 or years <= 0:
        raise ValueError("total_multiple and years must be positive")
    return total_multiple ** (D(1) / D(years)) - D(1)


def scenario_eps_bridge(
    *,
    revenue: Decimal,
    operating_margin: Decimal,
    other_income: Decimal,
    tax_rate: Decimal,
    diluted_shares: Decimal,
) -> dict[str, str]:
    """Calculate a complete revenue-to-EPS bridge from explicit inputs."""
    for name, value in {
        "revenue": revenue,
        "operating_margin": operating_margin,
        "other_income": other_income,
        "tax_rate": tax_rate,
        "diluted_shares": diluted_shares,
    }.items():
        if not value.is_finite():
            raise ValueError(f"{name} must be finite")
    if revenue <= 0:
        raise ValueError("revenue must be positive")
    if diluted_shares <= 0:
        raise ValueError("diluted_shares must be positive")
    if tax_rate < 0 or tax_rate >= 1:
        raise ValueError("tax_rate must be in [0, 1)")

    with localcontext() as ctx:
        ctx.prec = _VALUATION_PREC
        operating_income = revenue * operating_margin
        pre_tax_income = operating_income + other_income
        net_income = pre_tax_income * (D(1) - tax_rate)
        eps = net_income / diluted_shares
        return {
            "revenue": q(revenue),
            "operating_margin_pct": q(operating_margin * D(100), "0.01"),
            "operating_income": q(operating_income),
            "other_income": q(other_income),
            "pre_tax_income": q(pre_tax_income),
            "tax_rate_pct": q(tax_rate * D(100), "0.01"),
            "net_income": q(net_income),
            "diluted_shares": q(diluted_shares),
            "eps": q(eps),
        }


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

    with localcontext() as ctx:
        ctx.prec = _VALUATION_PREC
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
    with localcontext() as ctx:
        ctx.prec = _VALUATION_PREC
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


def _resolve_evaluated(
    evaluated: list[dict[str, Any]], current_action: Any = None
) -> dict[str, Any]:
    triggered = [item for item in evaluated if item["triggered"]]
    if not triggered:
        resolved = "REVIEW"
    else:
        top = max(item["priority"] for item in triggered)
        actions = {item["action"] for item in triggered if item["priority"] == top}
        resolved = next(iter(actions)) if len(actions) == 1 else "REVIEW"

    current = None if current_action is None else str(current_action).upper()
    return {
        "evaluated_rules": evaluated,
        "triggered_rule_ids": [item["id"] for item in triggered],
        "resolved_action": resolved,
        "reported_action": current,
        "reported_action_matches": None if current is None else current == resolved,
    }


def resolve_action(payload: dict[str, Any]) -> dict[str, Any]:
    """Legacy resolver for explicit booleans.

    New full reports must use :func:`evaluate_action`, which calculates truth
    values from canonical facts. This function remains for backward compatibility.
    """
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules must be a non-empty list")
    evaluated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("each rule must be an object")
        rule_id = str(rule.get("id", "")).strip()
        if not rule_id or rule_id in seen_ids:
            raise ValueError("rule ids must be non-empty and unique")
        seen_ids.add(rule_id)
        action = str(rule.get("action", "")).upper()
        if action not in _PRIORITIES:
            raise ValueError(f"unsupported action: {action}")
        if type(rule.get("triggered")) is not bool:
            raise ValueError(f"rule {rule_id} triggered must be boolean")
        evaluated.append(
            {
                "id": rule_id,
                "action": action,
                "triggered": rule["triggered"],
                "priority": int(rule.get("priority", _PRIORITIES[action])),
            }
        )
    return _resolve_evaluated(evaluated, payload.get("current_action"))


def _try_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (str, int, float, Decimal)):
        return None
    try:
        result = dec(value)
    except (InvalidOperation, ValueError):
        return None
    return result


def _display_value(value: Any) -> Any:
    numeric = _try_decimal(value)
    if numeric is not None:
        return str(numeric)
    return value


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator not in _NUMERIC_OPERATORS:
        raise ValueError(f"unsupported operator: {operator}")
    left = _try_decimal(actual)
    right = _try_decimal(expected)
    if left is not None and right is not None:
        return {
            "<": left < right,
            "<=": left <= right,
            ">": left > right,
            ">=": left >= right,
            "==": left == right,
            "!=": left != right,
        }[operator]
    if operator not in {"==", "!="}:
        raise ValueError(f"operator {operator} requires numeric facts")
    if type(actual) is not type(expected) or not isinstance(actual, (str, bool)):
        raise ValueError("non-numeric equality requires matching string or boolean types")
    return actual == expected if operator == "==" else actual != expected


def evaluate_action(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate Action Matrix rules from canonical facts, then resolve action.

    Payload schema:
      current_action: optional report action
      facts: {Fact-ID: scalar}
      rules: [{id, action, logic, conditions, priority?}]
      conditions: [{fact, operator, value}] or [{fact, operator, value_fact}]
    """
    facts = payload.get("facts")
    rules = payload.get("rules")
    if not isinstance(facts, dict) or not facts:
        raise ValueError("facts must be a non-empty object")
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules must be a non-empty list")
    for fact_id, value in facts.items():
        if not isinstance(fact_id, str) or not fact_id.strip():
            raise ValueError("fact ids must be non-empty strings")
        if isinstance(value, (dict, list)) or value is None:
            raise ValueError(f"fact {fact_id} must be a scalar")

    evaluated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("each rule must be an object")
        rule_id = str(rule.get("id", "")).strip()
        if not rule_id or rule_id in seen_ids:
            raise ValueError("rule ids must be non-empty and unique")
        seen_ids.add(rule_id)
        action = str(rule.get("action", "")).upper()
        if action not in _PRIORITIES:
            raise ValueError(f"unsupported action: {action}")
        logic = str(rule.get("logic", "all")).lower()
        if logic not in {"all", "any"}:
            raise ValueError(f"rule {rule_id} logic must be all or any")
        conditions = rule.get("conditions")
        if not isinstance(conditions, list) or not conditions:
            raise ValueError(f"rule {rule_id} conditions must be a non-empty list")

        evaluated_conditions: list[dict[str, Any]] = []
        for index, condition in enumerate(conditions):
            if not isinstance(condition, dict):
                raise ValueError(f"rule {rule_id} condition {index} must be an object")
            fact_id = str(condition.get("fact", "")).strip()
            if fact_id not in facts:
                raise ValueError(f"rule {rule_id} references missing fact: {fact_id}")
            operator = str(condition.get("operator", "")).strip()
            has_value = "value" in condition
            has_value_fact = "value_fact" in condition
            if has_value == has_value_fact:
                raise ValueError(
                    f"rule {rule_id} condition {index} must define exactly one of value or value_fact"
                )
            if has_value_fact:
                expected_fact = str(condition["value_fact"]).strip()
                if expected_fact not in facts:
                    raise ValueError(
                        f"rule {rule_id} references missing expected fact: {expected_fact}"
                    )
                expected = facts[expected_fact]
            else:
                expected_fact = None
                expected = condition["value"]
            actual = facts[fact_id]
            result = _compare(actual, operator, expected)
            evaluated_conditions.append(
                {
                    "fact": fact_id,
                    "actual": _display_value(actual),
                    "operator": operator,
                    "expected": _display_value(expected),
                    "expected_fact": expected_fact,
                    "result": result,
                }
            )

        triggered = (
            all(item["result"] for item in evaluated_conditions)
            if logic == "all"
            else any(item["result"] for item in evaluated_conditions)
        )
        evaluated.append(
            {
                "id": rule_id,
                "action": action,
                "logic": logic,
                "conditions": evaluated_conditions,
                "triggered": triggered,
                "priority": int(rule.get("priority", _PRIORITIES[action])),
            }
        )

    result = _resolve_evaluated(evaluated, payload.get("current_action"))
    result["facts"] = {key: _display_value(value) for key, value in facts.items()}
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    bridge = sub.add_parser("eps-bridge")
    bridge.add_argument("--revenue", required=True)
    bridge.add_argument("--operating-margin", required=True, help="decimal, e.g. 0.35")
    bridge.add_argument("--other-income", default="0")
    bridge.add_argument("--tax-rate", required=True, help="decimal, e.g. 0.18")
    bridge.add_argument("--diluted-shares", required=True)

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

    evaluate = sub.add_parser("evaluate-action")
    evaluate.add_argument("--input", required=True, help="JSON file path or '-' for stdin")

    resolve = sub.add_parser("resolve-action")
    resolve.add_argument("--input", required=True, help="legacy JSON file path or '-' for stdin")
    return parser


def _read_json_input(path: str) -> dict[str, Any]:
    import sys

    text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("JSON input must be an object")
    return payload


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "eps-bridge":
        result = scenario_eps_bridge(
            revenue=dec(args.revenue),
            operating_margin=dec(args.operating_margin),
            other_income=dec(args.other_income),
            tax_rate=dec(args.tax_rate),
            diluted_shares=dec(args.diluted_shares),
        )
    elif args.command == "irr":
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
    elif args.command == "evaluate-action":
        result = evaluate_action(_read_json_input(args.input))
    else:
        result = resolve_action(_read_json_input(args.input))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

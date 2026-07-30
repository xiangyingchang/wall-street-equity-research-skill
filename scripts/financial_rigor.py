#!/usr/bin/env python3
"""Deterministic financial calculation and discrepancy checks.

Adapted from AI Berkshire's MIT-licensed financial_rigor.py. This local version
keeps only zero-dependency, report-contract checks and uses Decimal throughout.
See references/third-party-notices.md.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from decimal import Decimal, localcontext

from financial_formulas import PaybackError, solve_payback
from validation_common import classify_discrepancy, decimal, direct_discrepancy_percent, symmetric_spread_percent


ONE = Decimal("1")
HUNDRED = Decimal("100")


def print_verdict(difference: Decimal) -> str:
    verdict, guidance = classify_discrepancy(difference)
    print(f"Difference: {difference:.4f}%")
    print(f"Verdict: {verdict} — {guidance}")
    return verdict


def verify_market_cap(price: str, shares: str, reported: str, currency: str = "") -> str:
    with localcontext() as context:
        context.prec = 28
        calculated = decimal(price) * decimal(shares)
        reported_value = decimal(reported)
        difference = direct_discrepancy_percent(reported_value, calculated)
    print("Market-cap verification")
    print(f"Price: {decimal(price)} {currency}".rstrip())
    print(f"Shares: {decimal(shares)}")
    print(f"Calculated market cap: {calculated} {currency}".rstrip())
    print(f"Reported market cap: {reported_value} {currency}".rstrip())
    return print_verdict(difference)


def verify_valuation(args: argparse.Namespace) -> None:
    price = decimal(args.price)
    print("Valuation verification")
    print(f"Price: {price}")
    values = {
        "PE": args.eps,
        "PB": args.bvps,
        "P/FCF": args.fcf_per_share,
        "P/S": args.revenue_per_share,
    }
    for label, raw_value in values.items():
        if raw_value is None:
            continue
        value = decimal(raw_value)
        if value == 0:
            print(f"{label}: unavailable because denominator is zero")
        else:
            print(f"{label}: {price / value:.6f}x")
    if args.dividend is not None:
        print(f"Dividend yield: {decimal(args.dividend) / price * HUNDRED:.6f}%")


def cross_validate(field: str, values_json: str, unit: str = "") -> str:
    values = json.loads(values_json)
    if not isinstance(values, dict) or len(values) < 2:
        raise ValueError("--values must be a JSON object with at least two sources")
    parsed = {str(source): decimal(value) for source, value in values.items()}
    ordered = sorted(parsed.values())
    reference = ordered[0]
    differences = {source: direct_discrepancy_percent(reference, value) for source, value in parsed.items()}
    max_difference = symmetric_spread_percent(ordered)
    print(f"Cross-validation: {field}")
    print(f"Reference low/source base: {reference} {unit}".rstrip())
    for source, value in parsed.items():
        print(f"{source}: {value} {unit}; difference {differences[source]:.4f}%".rstrip())
    return print_verdict(max_difference)


def evaluate_expression(node: ast.AST, expression: str) -> Decimal:
    if isinstance(node, ast.Expression):
        return evaluate_expression(node.body, expression)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        literal = ast.get_source_segment(expression, node)
        return decimal(literal if literal is not None else node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = evaluate_expression(node.operand, expression)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left, right = evaluate_expression(node.left, expression), evaluate_expression(node.right, expression)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        return left / right
    raise ValueError("expression supports only numbers, +, -, *, /, and parentheses")


def calc(expression: str) -> Decimal:
    with localcontext() as context:
        context.prec = 50
        result = evaluate_expression(ast.parse(expression, mode="eval"), expression)
    print(f"{expression} = {result}")
    return result


def three_scenario(args: argparse.Namespace) -> None:
    price, eps = decimal(args.price), decimal(args.eps)
    print("Scenario | growth | target PE | target EPS | target price | return")
    for label, growth, multiple in zip(("Bull", "Base", "Bear"), args.growth, args.pe):
        future_eps = eps * (ONE + decimal(growth)) ** args.years
        target_price = future_eps * decimal(multiple)
        total_return = (target_price / price - ONE) * HUNDRED
        print(f"{label} | {decimal(growth) * HUNDRED:.2f}% | {decimal(multiple)}x | {future_eps:.6f} | {target_price:.6f} | {total_return:.2f}%")


def payback(args: argparse.Namespace) -> None:
    result = solve_payback(args.formula_id, args.multiple, args.discount_rate, args.years)
    if args.json:
        print(json.dumps(result.as_json_dict(), sort_keys=True))
        return
    print(f"Formula: {result.formula_id}")
    print(f"Multiple: {result.multiple}")
    print(f"Discount rate: {result.discount_rate}")
    print(f"Years: {result.years}")
    print(f"Required growth: {result.root} ({result.root * HUNDRED}%)")
    print(f"Modeled multiple: {result.modeled_multiple}")
    print(f"Absolute residual: {result.absolute_residual}")
    print(f"Relative residual: {result.relative_residual}")
    print(f"Iterations: {result.iterations}")
    print(f"Interval width: {result.interval_width}")
    print("Converged: yes")


def self_test() -> int:
    cases = [
        (Decimal("100"), Decimal("100.5"), "CONSISTENT"),
        (Decimal("100"), Decimal("103"), "RECONCILE"),
        (Decimal("100"), Decimal("106"), "BLOCK"),
    ]
    for expected, actual, verdict in cases:
        observed, _ = classify_discrepancy(direct_discrepancy_percent(expected, actual))
        if observed != verdict:
            print(f"SELF-TEST FAIL: expected {verdict}, got {observed}")
            return 1
    if calc("0.1 + 0.2") != Decimal("0.3"):
        print("SELF-TEST FAIL: Decimal calculation drift")
        return 1
    if calc("12345678901234567890.123456789 + 0.000000001") != Decimal("12345678901234567890.123456790"):
        print("SELF-TEST FAIL: decimal literal precision drift")
        return 1
    if cross_validate("range", '{"source-a": 100, "source-b": 106}') != "BLOCK":
        print("SELF-TEST FAIL: direct 100 versus 106 discrepancy must block")
        return 1
    if cross_validate("negative-range", '{"source-a": -100, "source-b": -105.1}') != "BLOCK":
        print("SELF-TEST FAIL: symmetric negative 100 versus 105.1 spread must block")
        return 1
    try:
        cross_validate("non-finite", '{"source-a": NaN, "source-b": 100}')
        print("SELF-TEST FAIL: non-finite JSON values must fail")
        return 1
    except ValueError:
        pass
    print("SELF-TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero-dependency Decimal financial rigor checks.")
    parser.add_argument("--self-test", action="store_true", help="run deterministic regression checks")
    commands = parser.add_subparsers(dest="command")
    market_cap = commands.add_parser("verify-market-cap")
    market_cap.add_argument("--price", required=True)
    market_cap.add_argument("--shares", required=True)
    market_cap.add_argument("--reported", required=True)
    market_cap.add_argument("--currency", default="")
    valuation = commands.add_parser("verify-valuation")
    valuation.add_argument("--price", required=True)
    valuation.add_argument("--eps")
    valuation.add_argument("--bvps")
    valuation.add_argument("--fcf-per-share")
    valuation.add_argument("--dividend")
    valuation.add_argument("--revenue-per-share")
    cross = commands.add_parser("cross-validate")
    cross.add_argument("--field", required=True)
    cross.add_argument("--values", required=True)
    cross.add_argument("--unit", default="")
    calculation = commands.add_parser("calc")
    calculation.add_argument("--expr", required=True)
    scenario = commands.add_parser("three-scenario")
    scenario.add_argument("--price", required=True)
    scenario.add_argument("--eps", required=True)
    scenario.add_argument("--growth", nargs=3, required=True)
    scenario.add_argument("--pe", nargs=3, required=True)
    scenario.add_argument("--years", type=int, default=3)
    payback_parser = commands.add_parser("payback")
    payback_parser.add_argument("--formula-id", required=True)
    payback_parser.add_argument("--multiple", required=True)
    payback_parser.add_argument("--discount-rate", default="0")
    payback_parser.add_argument("--years", type=int, default=10)
    payback_parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        if args.command == "verify-market-cap":
            return 0 if verify_market_cap(args.price, args.shares, args.reported, args.currency) != "BLOCK" else 1
        if args.command == "verify-valuation":
            verify_valuation(args)
        elif args.command == "cross-validate":
            return 0 if cross_validate(args.field, args.values, args.unit) != "BLOCK" else 1
        elif args.command == "calc":
            calc(args.expr)
        elif args.command == "three-scenario":
            three_scenario(args)
        elif args.command == "payback":
            payback(args)
        else:
            parser.print_help()
            return 2
    except (PaybackError, ValueError, ZeroDivisionError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

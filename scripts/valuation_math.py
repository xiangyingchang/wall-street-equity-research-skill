#!/usr/bin/env python3
"""Deterministic valuation math used by the legacy Reader report contract."""

from __future__ import annotations

import argparse
import json
from typing import Callable


def _solve_monotonic(target: float, value: Callable[[float], float]) -> float:
    """Solve a monotonic growth rate without pulling in a numerical package."""
    if target <= 0:
        raise ValueError("target must be positive")
    lo, hi = -0.999999, 1.0
    while value(hi) < target and hi < 100.0:
        hi = hi * 2.0 + 0.01
    if value(lo) > target or value(hi) < target:
        raise ValueError("target is outside the solvable growth range")
    for _ in range(160):
        mid = (lo + hi) / 2.0
        if value(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def payback_growth(
    multiple: float,
    *,
    years: int = 10,
    discount_rate: float = 0.0,
    first_period: int = 1,
) -> float:
    """Return the growth rate for discounted earnings payback.

    The legacy contract uses periods 1..10 for TTM EPS/FCF. Forward bases can
    pass ``first_period=0`` explicitly.
    """
    if multiple <= 0 or years <= 0 or first_period < 0:
        raise ValueError("multiple, years and first_period must be valid")
    if discount_rate <= -1:
        raise ValueError("discount_rate must be greater than -100%")

    def accumulated(growth: float) -> float:
        ratio = (1.0 + growth) / (1.0 + discount_rate)
        return sum(ratio**period for period in range(first_period, first_period + years))

    return _solve_monotonic(multiple, accumulated)


def terminal_price(starting_eps: float, eps_cagr: float, exit_pe: float, years: int) -> float:
    if starting_eps <= 0 or exit_pe <= 0 or years <= 0 or eps_cagr <= -1:
        raise ValueError("invalid terminal price inputs")
    return starting_eps * (1.0 + eps_cagr) ** years * exit_pe


def target_return_price(
    starting_eps: float,
    eps_cagr: float,
    exit_pe: float,
    years: int,
    target_return: float,
    dividend_yield: float = 0.0,
    *,
    dividend_mode: str = "reinvested_yield",
) -> float:
    """Return the price compatible with the stated target return.

    ``reinvested_yield`` treats the stated dividend yield as a compounded
    return component. ``none`` excludes dividends. The treatment is explicit
    so a report cannot silently mix price appreciation and total return.
    """
    if target_return <= -1 or dividend_yield <= -1:
        raise ValueError("target_return and dividend_yield must be greater than -100%")
    if dividend_mode == "reinvested_yield":
        dividend_factor = (1.0 + dividend_yield) ** years
    elif dividend_mode == "none":
        dividend_factor = 1.0
    else:
        raise ValueError(f"unsupported dividend_mode: {dividend_mode}")
    return terminal_price(starting_eps, eps_cagr, exit_pe, years) * dividend_factor / (1.0 + target_return) ** years


def total_return_irr(
    current_price: float,
    starting_eps: float,
    eps_cagr: float,
    exit_pe: float,
    years: int,
    dividend_yield: float = 0.0,
) -> float:
    if current_price <= 0:
        raise ValueError("current_price must be positive")
    terminal = terminal_price(starting_eps, eps_cagr, exit_pe, years)
    return (terminal / current_price) ** (1.0 / years) * (1.0 + dividend_yield) - 1.0


def _emit(payload: dict[str, float | int | str]) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    payback = subparsers.add_parser("payback")
    payback.add_argument("--multiple", type=float, required=True)
    payback.add_argument("--years", type=int, default=10)
    payback.add_argument("--discount-rate", type=float, default=0.0)
    payback.add_argument("--first-period", type=int, default=1)

    price = subparsers.add_parser("target-price")
    price.add_argument("--starting-eps", type=float, required=True)
    price.add_argument("--eps-cagr", type=float, required=True)
    price.add_argument("--exit-pe", type=float, required=True)
    price.add_argument("--years", type=int, required=True)
    price.add_argument("--target-return", type=float, required=True)
    price.add_argument("--dividend-yield", type=float, default=0.0)
    price.add_argument("--dividend-mode", choices=("reinvested_yield", "none"), default="reinvested_yield")

    irr = subparsers.add_parser("irr")
    irr.add_argument("--current-price", type=float, required=True)
    irr.add_argument("--starting-eps", type=float, required=True)
    irr.add_argument("--eps-cagr", type=float, required=True)
    irr.add_argument("--exit-pe", type=float, required=True)
    irr.add_argument("--years", type=int, required=True)
    irr.add_argument("--dividend-yield", type=float, default=0.0)

    args = parser.parse_args()
    if args.command == "payback":
        _emit({"growth": payback_growth(args.multiple, years=args.years, discount_rate=args.discount_rate, first_period=args.first_period)})
    elif args.command == "target-price":
        _emit({"terminal_price": terminal_price(args.starting_eps, args.eps_cagr, args.exit_pe, args.years), "target_price": target_return_price(args.starting_eps, args.eps_cagr, args.exit_pe, args.years, args.target_return, args.dividend_yield, dividend_mode=args.dividend_mode)})
    else:
        _emit({"irr": total_return_irr(args.current_price, args.starting_eps, args.eps_cagr, args.exit_pe, args.years, args.dividend_yield)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

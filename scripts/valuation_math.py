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


def earnings_reference_price(normalized_eps: float, reference_pe: float) -> float:
    if normalized_eps <= 0 or reference_pe <= 0:
        raise ValueError("normalized_eps and reference_pe must be positive")
    return normalized_eps * reference_pe


def cash_confirmation_price(normalized_fcf_per_share: float, cash_hurdle: float) -> float:
    if normalized_fcf_per_share <= 0 or cash_hurdle <= 0:
        raise ValueError("normalized_fcf_per_share and cash_hurdle must be positive")
    return normalized_fcf_per_share / cash_hurdle


def price_zones(
    normalized_eps: float,
    reference_pes: list[float],
    buy_pe: float,
    normalized_fcf_per_share: float,
    cash_hurdle: float,
    *,
    cash_confidence: str = "medium",
    target_return_price_value: float | None = None,
) -> dict[str, object]:
    """Build valuation reference and executable price gates.

    Reference PE bands describe valuation context. ``buy_pe`` and the cash
    hurdle are the executable gates. Conditional or low-confidence cash flow
    data still produces a calculated price, but the action status remains
    REVIEW instead of silently becoming a Buy.
    """
    if not reference_pes or buy_pe <= 0:
        raise ValueError("reference_pes must be non-empty and buy_pe must be positive")
    if target_return_price_value is not None and target_return_price_value <= 0:
        raise ValueError("target_return_price_value must be positive")
    if cash_confidence not in {"high", "medium", "conditional", "low", "unconfirmed"}:
        raise ValueError("unsupported cash_confidence")
    reference_prices = [
        {"pe": multiple, "price": earnings_reference_price(normalized_eps, multiple)}
        for multiple in reference_pes
    ]
    earnings_buy = earnings_reference_price(normalized_eps, buy_pe)
    cash_price = cash_confirmation_price(normalized_fcf_per_share, cash_hurdle)
    active_prices = [earnings_buy, cash_price]
    if target_return_price_value is not None:
        active_prices.append(target_return_price_value)
    joint_price = min(active_prices)
    executable = cash_confidence in {"high", "medium"}
    return {
        "earnings_reference_prices": reference_prices,
        "earnings_buy_price": earnings_buy,
        "target_return_price": target_return_price_value,
        "cash_confirmation_price": cash_price,
        "cash_confidence": cash_confidence,
        "joint_new_money_price": joint_price,
        "joint_action_status": "EXECUTABLE" if executable else "REVIEW_CASH_CONFIDENCE",
    }


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

    zones = subparsers.add_parser("price-zones")
    zones.add_argument("--normalized-eps", type=float, required=True)
    zones.add_argument("--reference-pes", required=True, help="comma-separated PE band, e.g. 12,15,18")
    zones.add_argument("--buy-pe", type=float, required=True)
    zones.add_argument("--normalized-fcf-per-share", type=float, required=True)
    zones.add_argument("--cash-hurdle", type=float, required=True)
    zones.add_argument("--cash-confidence", choices=("high", "medium", "conditional", "low", "unconfirmed"), default="medium")
    zones.add_argument("--target-return-price", type=float)

    args = parser.parse_args()
    if args.command == "payback":
        _emit({"growth": payback_growth(args.multiple, years=args.years, discount_rate=args.discount_rate, first_period=args.first_period)})
    elif args.command == "target-price":
        _emit({"terminal_price": terminal_price(args.starting_eps, args.eps_cagr, args.exit_pe, args.years), "target_price": target_return_price(args.starting_eps, args.eps_cagr, args.exit_pe, args.years, args.target_return, args.dividend_yield, dividend_mode=args.dividend_mode)})
    elif args.command == "irr":
        _emit({"irr": total_return_irr(args.current_price, args.starting_eps, args.eps_cagr, args.exit_pe, args.years, args.dividend_yield)})
    else:
        reference_pes = [float(item.strip()) for item in args.reference_pes.split(",") if item.strip()]
        _emit(price_zones(args.normalized_eps, reference_pes, args.buy_pe, args.normalized_fcf_per_share, args.cash_hurdle, cash_confidence=args.cash_confidence, target_return_price_value=args.target_return_price))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

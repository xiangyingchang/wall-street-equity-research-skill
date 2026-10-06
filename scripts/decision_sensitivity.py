"""Quantified Base-case decision sensitivity for v3.1 Bundles.

The qualitative sensitivity drivers explain *why* a variable matters. This
module answers the questions a reader actually acts on:

1. What value of each key assumption would make Base IRR equal the hurdle?
2. How far is that break-even from the Base assumption?
3. What happens to IRR and the valuation candidate when one input moves?

Every number is recomputed from the same Spec inputs and the same
``valuation_runtime`` engine used for scenario prices, so the Reader can never
show a sensitivity that disagrees with the Bundle.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any

from scripts.valuation_runtime import return_pair, scenario_eps_bridge

D = Decimal
_PREC = 50
# One-step shocks per role. Additive for ratios, additive multiple points for PE.
DEFAULT_STEPS = {
    "operating_margin": D("0.02"),
    "eps_cagr": D("0.02"),
    "exit_pe": D("2"),
}
ROLE_LABELS = {
    "operating_margin": "前瞻经营利润率",
    "eps_cagr": "长期 EPS 增长",
    "exit_pe": "退出市盈率",
}


def _q(value: Decimal, places: str = "0.0001") -> str:
    return str(value.quantize(D(places)))


def _valuation_candidate(gap: Decimal, reduce_gap: Decimal, review_band: Decimal) -> str:
    if gap > reduce_gap + review_band:
        return "REDUCE"
    if gap > max(D(0), reduce_gap - review_band):
        return "REVIEW"
    return "HOLD"


def _base_inputs(bundle: dict[str, Any]) -> dict[str, Decimal]:
    base = bundle["scenarios"]["base"]
    refs = base["assumption_refs"]
    assumptions = bundle["assumptions"]
    facts = bundle["facts"]

    def value(ref: str) -> Decimal:
        if ref.startswith("FACT-"):
            return D(str(facts[ref]["value"]))
        return D(str(assumptions[ref]["value"]))

    return {
        "revenue": D(str(base["revenue"]["forward_revenue"])),
        "operating_margin": value(refs["operating_margin"]),
        "other_income": value(refs["other_income"]),
        "tax_rate": value(refs["tax_rate"]),
        "diluted_shares": value(refs["diluted_shares"]),
        "eps_cagr": value(refs["eps_cagr"]),
        "exit_pe": value(refs["exit_pe"]),
        "dividend_yield": value(refs["dividend_yield"]),
        "current_price": D(str(facts[bundle["report"]["current_price_fact_id"]]["value"])),
        "target_return": D(str(bundle["target_return"])),
        "years": D(int(bundle["report"].get("return_years", 5))),
        "fx_rate": _fx_rate(bundle),
    }


def _fx_rate(bundle: dict[str, Any]) -> Decimal:
    fx = bundle.get("derived", {}).get("fx")
    return D(str(fx["rate"])) if fx else D(1)


def _irr(inputs: dict[str, Decimal]) -> Decimal:
    eps = scenario_eps_bridge(
        revenue=inputs["revenue"],
        operating_margin=inputs["operating_margin"],
        other_income=inputs["other_income"],
        tax_rate=inputs["tax_rate"],
        diluted_shares=inputs["diluted_shares"],
    )["eps"]
    result = return_pair(
        current_price=inputs["current_price"],
        starting_eps=D(eps) * inputs.get("fx_rate", D(1)),
        eps_cagr=inputs["eps_cagr"],
        exit_pe=inputs["exit_pe"],
        years=int(inputs["years"]),
        target_return=inputs["target_return"],
        annual_dividend_yield=inputs["dividend_yield"],
    )
    return D(result["irr"]["irr_pct"]) / D(100)


def _break_even(inputs: dict[str, Decimal]) -> dict[str, Decimal | None]:
    """Closed-form values that make Base IRR equal the hurdle, one input at a time."""
    with localcontext() as ctx:
        ctx.prec = _PREC
        price = inputs["current_price"]
        fx = inputs.get("fx_rate", D(1))
        years = int(inputs["years"])
        hurdle = inputs["target_return"]
        dividends = price * inputs["dividend_yield"] * years
        required_terminal_price = price * (D(1) + hurdle) ** years - dividends
        if required_terminal_price <= 0:
            return {"operating_margin": None, "eps_cagr": None, "exit_pe": None}
        start_eps = (
            (inputs["revenue"] * inputs["operating_margin"] + inputs["other_income"])
            * (D(1) - inputs["tax_rate"])
            / inputs["diluted_shares"]
            * fx
        )
        growth = (D(1) + inputs["eps_cagr"]) ** years
        required_terminal_eps = required_terminal_price / inputs["exit_pe"]

        eps_cagr = None
        if start_eps > 0:
            eps_cagr = (required_terminal_eps / start_eps) ** (D(1) / D(years)) - D(1)

        exit_pe = None
        if start_eps > 0:
            exit_pe = required_terminal_price / (start_eps * growth)

        required_start_eps = required_terminal_eps / growth
        margin = (
            required_start_eps / fx * inputs["diluted_shares"] / (D(1) - inputs["tax_rate"])
            - inputs["other_income"]
        ) / inputs["revenue"]
        return {"operating_margin": margin, "eps_cagr": eps_cagr, "exit_pe": exit_pe}


def compile_decision_sensitivity(bundle: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    inputs = _base_inputs(bundle)
    valuation = policy.get("valuation", {})
    reduce_gap = D(str(valuation.get("reduce_gap", "0.02")))
    review_band = D(str(valuation.get("review_band", "0.01")))
    hurdle = inputs["target_return"]
    base_irr = _irr(inputs)
    break_even = _break_even(inputs)

    rows = []
    for role, step in DEFAULT_STEPS.items():
        base_value = inputs[role]
        shocks = []
        for sign in (D(-1), D(1)):
            shocked = dict(inputs)
            shocked[role] = base_value + sign * step
            if role == "exit_pe" and shocked[role] <= 0:
                continue
            irr = _irr(shocked)
            shocks.append({
                "direction": "down" if sign < 0 else "up",
                "value": _q(shocked[role]),
                "irr": _q(irr),
                "valuation_candidate": _valuation_candidate(hurdle - irr, reduce_gap, review_band),
            })
        required = break_even[role]
        rows.append({
            "role": role,
            "label": ROLE_LABELS[role],
            "base_value": _q(base_value),
            "step": _q(step),
            "break_even_value": _q(required) if required is not None else None,
            "distance_to_break_even": _q(required - base_value) if required is not None else None,
            "shocks": shocks,
        })

    grid_steps = (-2, -1, 0, 1, 2)
    margin_values = [inputs["operating_margin"] + D(k) * DEFAULT_STEPS["operating_margin"] for k in grid_steps]
    pe_values = [inputs["exit_pe"] + D(k) * DEFAULT_STEPS["exit_pe"] for k in grid_steps]
    grid_rows = []
    for margin in margin_values:
        cells = []
        for pe in pe_values:
            if pe <= 0 or margin <= 0:
                cells.append(None)
                continue
            shocked = dict(inputs)
            shocked["operating_margin"], shocked["exit_pe"] = margin, pe
            irr = _irr(shocked)
            cells.append({"irr": _q(irr), "passes": bool(irr >= hurdle)})
        grid_rows.append({"operating_margin": _q(margin), "cells": cells})

    return {
        "schema_version": "decision-sensitivity-v2",
        "base_irr": _q(base_irr),
        "target_return": _q(hurdle),
        "base_valuation_candidate": _valuation_candidate(hurdle - base_irr, reduce_gap, review_band),
        "required_price_for_hurdle": bundle["scenarios"]["base"]["prices"]["target_return"],
        "drivers": rows,
        "grid": {"row_role": "operating_margin", "column_role": "exit_pe", "columns": [_q(x) for x in pe_values], "rows": grid_rows},
    }

#!/usr/bin/env python3
"""Canonical Decimal financial formulas and deterministic root solving."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, DecimalException, localcontext
import re
from typing import Any, Callable, Iterable, Mapping


DECIMAL_PRECISION = 50
CONVERGENCE_TOLERANCE = Decimal("1e-24")
MAX_BRACKET_EXPANSIONS = 256
MAX_BISECTION_ITERATIONS = 1024
ONE = Decimal("1")
TWO = Decimal("2")
ZERO = Decimal("0")
FISCAL_QUARTER = re.compile(r"FY(?P<year>[0-9]{4})-Q(?P<quarter>[1-4])\Z")


class PaybackError(ValueError):
    """Base error for canonical payback calculations."""


class PaybackDomainError(PaybackError):
    """Raised when formula inputs violate the public domain."""


class PaybackNonIdentifiableError(PaybackDomainError):
    """Raised when the requested formula cannot identify a unique growth root."""


class PaybackNoRootError(PaybackError):
    """Raised when no root exists in the required growth domain."""


class PaybackNonConvergenceError(PaybackError):
    """Raised when deterministic bracketing or bisection cannot converge."""


PaybackEvaluator = Callable[[Decimal, Decimal, int], Decimal]


def _payback_ttm(growth: Decimal, discount_rate: Decimal, years: int) -> Decimal:
    ratio = (ONE + growth) / (ONE + discount_rate)
    return sum((ratio**period for period in range(1, years + 1)), ZERO)


def _payback_forward(growth: Decimal, discount_rate: Decimal, years: int) -> Decimal:
    growth_base = ONE + growth
    discount_base = ONE + discount_rate
    return sum(
        (ONE if period == 1 else growth_base ** (period - 1)) / (discount_base**period)
        for period in range(1, years + 1)
    )


PAYBACK_FORMULA_REGISTRY: dict[str, PaybackEvaluator] = {
    "payback_ttm_v1": _payback_ttm,
    "payback_forward_v1": _payback_forward,
}

FORMULA_REGISTRY = {
    "sum_v1": "sum",
    "difference_v1": "difference",
    "product_v1": "product",
    "ratio_v1": "ratio",
    "ttm_sum_v1": "ttm_sum",
    "ttm_bridge_v1": "ttm_bridge",
    "payback_ttm_v1": "payback",
    "payback_forward_v1": "payback",
}


def _as_decimal(value: Decimal | str | int | float, name: str) -> Decimal:
    if isinstance(value, bool):
        raise PaybackDomainError(f"{name} must be a finite decimal number")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (DecimalException, TypeError, ValueError) as error:
        raise PaybackDomainError(f"{name} must be a finite decimal number") from error
    if not parsed.is_finite():
        raise PaybackDomainError(f"{name} must be a finite decimal number")
    return parsed


def _validate_inputs(
    formula_id: str,
    multiple: Decimal | str | int | float,
    discount_rate: Decimal | str | int | float,
    years: int,
) -> tuple[PaybackEvaluator, Decimal, Decimal]:
    try:
        formula = PAYBACK_FORMULA_REGISTRY[formula_id]
    except KeyError as error:
        supported = ", ".join(sorted(PAYBACK_FORMULA_REGISTRY))
        raise PaybackDomainError(f"unknown formula_id {formula_id!r}; expected one of: {supported}") from error
    parsed_multiple = _as_decimal(multiple, "multiple")
    parsed_rate = _as_decimal(discount_rate, "discount_rate")
    if parsed_multiple <= ZERO:
        raise PaybackDomainError("multiple must be greater than 0")
    if isinstance(years, bool) or not isinstance(years, int) or years <= 0:
        raise PaybackDomainError("years must be a positive integer")
    if parsed_rate <= -ONE:
        raise PaybackDomainError("discount_rate must be greater than -1")
    return formula, parsed_multiple, parsed_rate


def modeled_multiple(
    formula_id: str,
    growth: Decimal | str | int | float,
    discount_rate: Decimal | str | int | float,
    years: int,
) -> Decimal:
    """Evaluate a registered payback formula without solving for growth."""
    formula, _, parsed_rate = _validate_inputs(formula_id, ONE, discount_rate, years)
    parsed_growth = _as_decimal(growth, "growth")
    if parsed_growth <= -ONE:
        raise PaybackDomainError("growth must be greater than -1")
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        return +formula(parsed_growth, parsed_rate, years)


@dataclass(frozen=True)
class PaybackResult:
    formula_id: str
    multiple: Decimal
    discount_rate: Decimal
    years: int
    root: Decimal
    modeled_multiple: Decimal
    absolute_residual: Decimal
    relative_residual: Decimal
    iterations: int
    convergence: bool
    interval_width: Decimal

    def as_json_dict(self) -> dict[str, object]:
        """Return the CLI contract with every numeric field encoded as a string."""
        return {
            "formula_id": self.formula_id,
            "inputs": {
                "multiple": str(self.multiple),
                "discount_rate": str(self.discount_rate),
                "years": str(self.years),
            },
            "root": str(self.root),
            "modeled_multiple": str(self.modeled_multiple),
            "absolute_residual": str(self.absolute_residual),
            "relative_residual": str(self.relative_residual),
            "iterations": str(self.iterations),
            "interval_width": str(self.interval_width),
            "convergence": self.convergence,
        }


@dataclass(frozen=True)
class FormulaInput:
    name: str
    value: Decimal
    period: str | None = None
    role: str | None = None


@dataclass(frozen=True)
class FormulaResult:
    formula_id: str
    value: Decimal
    absolute_residual: Decimal | None = None
    relative_residual: Decimal | None = None

    def as_json_dict(self) -> dict[str, str]:
        result = {"formula_id": self.formula_id, "value": str(self.value)}
        if self.absolute_residual is not None:
            result["absolute_residual"] = str(self.absolute_residual)
        if self.relative_residual is not None:
            result["relative_residual"] = str(self.relative_residual)
        return result


def _formula_inputs(values: Iterable[FormulaInput | Mapping[str, Any]]) -> list[FormulaInput]:
    inputs: list[FormulaInput] = []
    for index, raw in enumerate(values):
        if isinstance(raw, FormulaInput):
            item = raw
        elif isinstance(raw, Mapping):
            name = raw.get("name")
            if not isinstance(name, str) or not name:
                raise PaybackDomainError(f"inputs[{index}].name must be nonempty")
            item = FormulaInput(
                name=name,
                value=_as_decimal(raw.get("value"), f"inputs[{index}].value"),
                period=raw.get("period"),
                role=raw.get("role"),
            )
        else:
            raise PaybackDomainError(f"inputs[{index}] must be a FormulaInput or mapping")
        if not item.name:
            raise PaybackDomainError(f"inputs[{index}].name must be nonempty")
        inputs.append(item)
    names = [item.name for item in inputs]
    if len(names) != len(set(names)):
        raise PaybackDomainError("formula input names must be unique")
    return inputs


def _named_inputs(inputs: list[FormulaInput], expected: set[str], formula_id: str) -> dict[str, Decimal]:
    actual = {item.name for item in inputs}
    if actual != expected:
        raise PaybackDomainError(
            f"{formula_id} inputs must be exactly: {', '.join(sorted(expected))}"
        )
    return {item.name: item.value for item in inputs}


def evaluate_formula(
    formula_id: str,
    values: Iterable[FormulaInput | Mapping[str, Any]],
) -> FormulaResult:
    """Evaluate one registered derived formula with exact Decimal arithmetic."""
    if formula_id not in FORMULA_REGISTRY:
        supported = ", ".join(sorted(FORMULA_REGISTRY))
        raise PaybackDomainError(f"unknown formula_id {formula_id!r}; expected one of: {supported}")
    inputs = _formula_inputs(values)
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        if formula_id in {"sum_v1", "product_v1"}:
            if len(inputs) < 2:
                raise PaybackDomainError(f"{formula_id} requires at least two inputs")
            if formula_id == "sum_v1":
                value = sum((item.value for item in inputs), ZERO)
            else:
                value = ONE
                for item in inputs:
                    value *= item.value
            return FormulaResult(formula_id, +value, ZERO, ZERO)
        if formula_id == "difference_v1":
            named = _named_inputs(inputs, {"minuend", "subtrahend"}, formula_id)
            return FormulaResult(formula_id, +(named["minuend"] - named["subtrahend"]), ZERO, ZERO)
        if formula_id == "ratio_v1":
            named = _named_inputs(inputs, {"numerator", "denominator"}, formula_id)
            if named["denominator"] == ZERO:
                raise PaybackDomainError("ratio_v1 denominator must not be zero")
            return FormulaResult(formula_id, +(named["numerator"] / named["denominator"]), ZERO, ZERO)
        if formula_id == "ttm_sum_v1":
            if len(inputs) != 4:
                raise PaybackDomainError("ttm_sum_v1 requires exactly four fiscal-quarter inputs")
            periods = [item.period for item in inputs]
            matches = [FISCAL_QUARTER.fullmatch(period) if isinstance(period, str) else None for period in periods]
            if any(match is None for match in matches):
                raise PaybackDomainError("ttm_sum_v1 periods must use FYyyyy-Qn syntax")
            ordinals = sorted(
                int(match.group("year")) * 4 + int(match.group("quarter")) - 1
                for match in matches
                if match is not None
            )
            if ordinals != list(range(ordinals[0], ordinals[0] + 4)):
                raise PaybackDomainError("ttm_sum_v1 periods must be four unique consecutive fiscal quarters")
            return FormulaResult(formula_id, +sum((item.value for item in inputs), ZERO), ZERO, ZERO)
        if formula_id == "ttm_bridge_v1":
            if len(inputs) != 3:
                raise PaybackDomainError("ttm_bridge_v1 requires exactly three inputs")
            roles = {item.role: item.value for item in inputs}
            expected_roles = {"fy", "current_ytd", "prior_ytd"}
            if set(roles) != expected_roles:
                raise PaybackDomainError(
                    "ttm_bridge_v1 roles must be exactly: current_ytd, fy, prior_ytd"
                )
            value = roles["fy"] + roles["current_ytd"] - roles["prior_ytd"]
            return FormulaResult(formula_id, +value, ZERO, ZERO)

        named = _named_inputs(inputs, {"multiple", "discount_rate", "years"}, formula_id)
        years = named["years"]
        if years != years.to_integral_value() or years <= ZERO:
            raise PaybackDomainError("payback years must be a positive integer")
        result = solve_payback(
            formula_id,
            named["multiple"],
            named["discount_rate"],
            int(years),
        )
        return FormulaResult(
            formula_id,
            result.root,
            result.absolute_residual,
            result.relative_residual,
        )


def solve_payback(
    formula_id: str,
    multiple: Decimal | str | int | float,
    discount_rate: Decimal | str | int | float = ZERO,
    years: int = 10,
) -> PaybackResult:
    """Solve a registered payback equation for growth greater than -1."""
    formula, target, rate = _validate_inputs(formula_id, multiple, discount_rate, years)
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION

        def equation(growth: Decimal) -> Decimal:
            return formula(growth, rate, years) - target

        if formula_id == "payback_forward_v1" and years == 1:
            raise PaybackNonIdentifiableError(
                "payback_forward_v1 is non-identifiable for years=1: "
                "modeled multiple is growth-independent"
            )

        lower = -ONE
        lower_value = equation(lower)
        if lower_value >= ZERO:
            raise PaybackNoRootError(
                f"no root for {formula_id}: modeled multiple at growth=-1 is not below target"
            )

        upper = ONE
        upper_value = equation(upper)
        expansions = 0
        while upper_value < ZERO and expansions < MAX_BRACKET_EXPANSIONS:
            upper = (upper + ONE) * TWO - ONE
            upper_value = equation(upper)
            expansions += 1
        if upper_value < ZERO:
            raise PaybackNonConvergenceError(
                f"failed to bracket root for {formula_id} after {MAX_BRACKET_EXPANSIONS} expansions"
            )

        for iteration in range(1, MAX_BISECTION_ITERATIONS + 1):
            midpoint = (lower + upper) / TWO
            midpoint_value = equation(midpoint)
            if midpoint_value < ZERO:
                lower = midpoint
            else:
                upper = midpoint
            interval_width = upper - lower
            absolute_residual = abs(midpoint_value)
            relative_residual = absolute_residual / target
            if (
                interval_width <= CONVERGENCE_TOLERANCE
                and absolute_residual <= CONVERGENCE_TOLERANCE
                and relative_residual <= CONVERGENCE_TOLERANCE
            ):
                modeled = midpoint_value + target
                return PaybackResult(
                    formula_id=formula_id,
                    multiple=target,
                    discount_rate=rate,
                    years=years,
                    root=+midpoint,
                    modeled_multiple=+modeled,
                    absolute_residual=+absolute_residual,
                    relative_residual=+relative_residual,
                    iterations=iteration,
                    convergence=True,
                    interval_width=+interval_width,
                )

    raise PaybackNonConvergenceError(
        f"root for {formula_id} did not satisfy interval and residual tolerances after "
        f"{MAX_BISECTION_ITERATIONS} iterations"
    )

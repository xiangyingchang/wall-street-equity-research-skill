#!/usr/bin/env python3
"""Deterministic valuation math, forecast bridges, and action evaluation.

This module never fetches data. It turns explicitly supplied, auditable inputs
into reproducible TTM derivations, revenue forecasts, EPS bridges, return pairs,
and decision outputs.
"""

from __future__ import annotations

import argparse
import copy
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Any

_VALUATION_PREC = 50
_PRIORITIES = {"SELL": 50, "REDUCE": 40, "ADD": 30, "BUY": 20, "HOLD": 10}
_NUMERIC_OPERATORS = {"<", "<=", ">", ">=", "==", "!="}
_CONFIDENCE_RANK = {
    "low": 1,
    "低": 1,
    "medium": 2,
    "中": 2,
    "中高": 2,
    "medium-high": 2,
    "high": 3,
    "高": 3,
}
_ALLOWED_VALUE_KINDS = {"FACT", "DERIVED", "MODEL"}

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


def _require_four_components(components: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(components, list) or len(components) != 4:
        raise ValueError(f"{label} must contain exactly four quarterly components")
    periods: set[str] = set()
    ids: set[str] = set()
    result: list[dict[str, Any]] = []
    for index, item in enumerate(components):
        if not isinstance(item, dict):
            raise ValueError(f"{label} component {index} must be an object")
        component_id = str(item.get("id", "")).strip()
        period = str(item.get("period", "")).strip()
        if not component_id or component_id in ids:
            raise ValueError(f"{label} component ids must be non-empty and unique")
        if not period or period in periods:
            raise ValueError(f"{label} periods must be non-empty and unique")
        value = dec(item.get("value"))
        ids.add(component_id)
        periods.add(period)
        result.append({"id": component_id, "period": period, "value": value})
    return result


def ttm_derive(payload: dict[str, Any]) -> dict[str, Any]:
    """Derive a four-quarter TTM sum or ratio from explicit components."""
    mode = str(payload.get("mode", "")).lower()
    derivation_id = str(payload.get("id", "")).strip()
    metric = str(payload.get("metric", "")).strip()
    if not derivation_id or not metric:
        raise ValueError("id and metric are required")
    with localcontext() as ctx:
        ctx.prec = _VALUATION_PREC
        if mode == "sum":
            components = _require_four_components(payload.get("components"), "components")
            total = sum((item["value"] for item in components), D(0))
            return {
                "id": derivation_id,
                "metric": metric,
                "mode": mode,
                "components": [
                    {"id": item["id"], "period": item["period"], "value": q(item["value"])}
                    for item in components
                ],
                "value": q(total),
            }
        if mode == "ratio":
            numerator = _require_four_components(payload.get("numerator"), "numerator")
            denominator = _require_four_components(payload.get("denominator"), "denominator")
            num_periods = {item["period"] for item in numerator}
            den_periods = {item["period"] for item in denominator}
            if num_periods != den_periods:
                raise ValueError("ratio numerator and denominator must cover the same four periods")
            numerator_total = sum((item["value"] for item in numerator), D(0))
            denominator_total = sum((item["value"] for item in denominator), D(0))
            if denominator_total == 0:
                raise ValueError("ratio denominator total cannot be zero")
            value = numerator_total / denominator_total
            return {
                "id": derivation_id,
                "metric": metric,
                "mode": mode,
                "numerator_components": [
                    {"id": item["id"], "period": item["period"], "value": q(item["value"])}
                    for item in numerator
                ],
                "denominator_components": [
                    {"id": item["id"], "period": item["period"], "value": q(item["value"])}
                    for item in denominator
                ],
                "numerator_total": q(numerator_total),
                "denominator_total": q(denominator_total),
                "value": q(value),
                "value_pct": q(value * D(100), "0.01"),
            }
    raise ValueError("mode must be sum or ratio")


def revenue_bridge(payload: dict[str, Any]) -> dict[str, Any]:
    """Calculate four forward revenue periods from auditable transformation modes."""
    scenario = str(payload.get("scenario", "")).strip()
    periods = payload.get("periods")
    if not scenario:
        raise ValueError("scenario is required")
    if not isinstance(periods, list) or len(periods) != 4:
        raise ValueError("periods must contain exactly four forward periods")
    seen_ids: set[str] = set()
    seen_periods: set[str] = set()
    calculated: dict[str, Decimal] = {}
    rows: list[dict[str, Any]] = []
    with localcontext() as ctx:
        ctx.prec = _VALUATION_PREC
        for index, item in enumerate(periods):
            if not isinstance(item, dict):
                raise ValueError(f"period {index} must be an object")
            bridge_id = str(item.get("id", "")).strip()
            period = str(item.get("period", "")).strip()
            mode = str(item.get("mode", "")).lower()
            if not bridge_id or bridge_id in seen_ids:
                raise ValueError("revenue bridge ids must be non-empty and unique")
            if not period or period in seen_periods:
                raise ValueError("revenue periods must be non-empty and unique")
            seen_ids.add(bridge_id)
            seen_periods.add(period)
            basis: dict[str, Any]
            if mode == "guide_midpoint":
                low = dec(item.get("low"))
                high = dec(item.get("high"))
                if low <= 0 or high < low:
                    raise ValueError(f"{bridge_id} has invalid guide range")
                if not str(item.get("source", "")).strip():
                    raise ValueError(f"{bridge_id} guide_midpoint requires source")
                value = (low + high) / D(2)
                basis = {"low": q(low), "high": q(high), "source": str(item["source"])}
            elif mode in {"yoy", "qoq"}:
                growth = dec(item.get("growth"))
                base_id = str(item.get("base_id", "")).strip()
                if "base_value" in item:
                    base = dec(item["base_value"])
                elif base_id and base_id in calculated:
                    base = calculated[base_id]
                else:
                    raise ValueError(f"{bridge_id} {mode} requires base_value or prior base_id")
                if base <= 0:
                    raise ValueError(f"{bridge_id} base revenue must be positive")
                value = base * (D(1) + growth)
                basis = {"base_id": base_id or None, "base_value": q(base), "growth": q(growth)}
            elif mode in {"explicit", "consensus"}:
                value = dec(item.get("value"))
                if value <= 0:
                    raise ValueError(f"{bridge_id} revenue must be positive")
                source = str(item.get("source", "")).strip()
                if not source:
                    raise ValueError(f"{bridge_id} {mode} requires source")
                if mode == "explicit" and not str(item.get("rationale", "")).strip():
                    raise ValueError(f"{bridge_id} explicit mode requires rationale")
                if mode == "consensus" and not str(item.get("as_of", "")).strip():
                    raise ValueError(f"{bridge_id} consensus mode requires as_of")
                basis = {
                    "source": source,
                    "rationale": item.get("rationale"),
                    "as_of": item.get("as_of"),
                }
            else:
                raise ValueError(
                    f"{bridge_id} mode must be guide_midpoint, yoy, qoq, explicit, or consensus"
                )
            calculated[bridge_id] = value
            rows.append(
                {
                    "id": bridge_id,
                    "period": period,
                    "mode": mode,
                    "revenue": q(value),
                    "basis": basis,
                }
            )
        total = sum(calculated.values(), D(0))
    return {"scenario": scenario, "periods": rows, "forward_revenue": q(total)}


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
    annual_dividend_yield: Decimal | None = None,
) -> dict[str, str]:
    if min(current_price, starting_eps, exit_pe) <= 0 or years <= 0:
        raise ValueError("price, starting EPS, exit PE, and years must be positive")
    if annual_dividend_yield is not None:
        if annual_dividend_per_share != 0:
            raise ValueError("use either dividend_per_share or dividend_yield, not both")
        annual_dividend_per_share = current_price * annual_dividend_yield
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


def return_pair(
    *,
    current_price: Decimal,
    starting_eps: Decimal,
    eps_cagr: Decimal,
    exit_pe: Decimal,
    years: int,
    target_return: Decimal,
    annual_dividend_per_share: Decimal = D(0),
    annual_dividend_yield: Decimal | None = None,
) -> dict[str, Any]:
    """Calculate IRR, reverse expectations, and target-return price from one assumption set."""
    irr = scenario_irr(
        current_price=current_price,
        starting_eps=starting_eps,
        eps_cagr=eps_cagr,
        exit_pe=exit_pe,
        years=years,
        annual_dividend_per_share=annual_dividend_per_share,
        annual_dividend_yield=annual_dividend_yield,
    )
    reverse = reverse_expectations(
        current_price=current_price,
        starting_eps=starting_eps,
        target_return=target_return,
        exit_pe=exit_pe,
        years=years,
        annual_dividend_per_share=annual_dividend_per_share,
        annual_dividend_yield=annual_dividend_yield,
    )
    with localcontext() as ctx:
        ctx.prec = _VALUATION_PREC
        terminal_eps = starting_eps * (D(1) + eps_cagr) ** years
        terminal_price = terminal_eps * exit_pe
        target_multiple = (D(1) + target_return) ** years
        if annual_dividend_yield is not None:
            denominator = target_multiple - annual_dividend_yield * years
            if denominator <= 0:
                raise ValueError("dividend yield makes target-return price denominator non-positive")
            target_price = terminal_price / denominator
            dividend_mode = {"mode": "yield", "value": q(annual_dividend_yield)}
        else:
            target_price = (terminal_price + annual_dividend_per_share * years) / target_multiple
            dividend_mode = {"mode": "per_share", "value": q(annual_dividend_per_share)}
    return {
        "assumptions": {
            "current_price": q(current_price),
            "starting_eps": q(starting_eps),
            "eps_cagr": q(eps_cagr),
            "exit_pe": q(exit_pe),
            "years": years,
            "target_return": q(target_return),
            "dividend": dividend_mode,
        },
        "irr": irr,
        "reverse": reverse,
        "target_return_price": q(target_price),
    }


def _resolve_evaluated(
    evaluated: list[dict[str, Any]], current_action: Any = None
) -> dict[str, Any]:
    triggered = [item for item in evaluated if item.get("triggered") is True]
    indeterminate = [item for item in evaluated if item.get("status") == "indeterminate"]
    highest_triggered = max((item["priority"] for item in triggered), default=None)
    highest_indeterminate = max((item["priority"] for item in indeterminate), default=None)
    if highest_indeterminate is not None and (
        highest_triggered is None or highest_indeterminate >= highest_triggered
    ):
        resolved = "REVIEW"
    elif not triggered:
        resolved = "REVIEW"
    else:
        top = max(item["priority"] for item in triggered)
        actions = {item["action"] for item in triggered if item["priority"] == top}
        resolved = next(iter(actions)) if len(actions) == 1 else "REVIEW"

    current = None if current_action is None else str(current_action).upper()
    return {
        "evaluated_rules": evaluated,
        "triggered_rule_ids": [item["id"] for item in triggered],
        "indeterminate_rule_ids": [item["id"] for item in indeterminate],
        "resolved_action": resolved,
        "reported_action": current,
        "reported_action_matches": None if current is None else current == resolved,
    }


def resolve_action(payload: dict[str, Any]) -> dict[str, Any]:
    """Legacy resolver for explicit booleans."""
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
                "status": "true" if rule["triggered"] else "false",
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


def _confidence_rank(value: Any) -> int:
    key = str(value).strip().casefold()
    if key not in _CONFIDENCE_RANK:
        raise ValueError(f"unsupported confidence: {value}")
    return _CONFIDENCE_RANK[key]


def _normalize_values(payload: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], bool]:
    if "values" in payload:
        raw = payload.get("values")
        if not isinstance(raw, dict) or not raw:
            raise ValueError("values must be a non-empty object")
        normalized: dict[str, dict[str, Any]] = {}
        for value_id, item in raw.items():
            if not isinstance(value_id, str) or not value_id.strip():
                raise ValueError("value ids must be non-empty strings")
            if not isinstance(item, dict):
                raise ValueError(f"value {value_id} must be an object")
            kind = str(item.get("kind", "")).upper()
            if kind not in _ALLOWED_VALUE_KINDS:
                raise ValueError(f"value {value_id} kind must be FACT, DERIVED, or MODEL")
            confidence = str(item.get("confidence", "")).strip()
            _confidence_rank(confidence)
            uncertainty = dec(item.get("uncertainty", "0"))
            if uncertainty < 0:
                raise ValueError(f"value {value_id} uncertainty cannot be negative")
            value = item.get("value")
            if isinstance(value, (dict, list)) or value is None:
                raise ValueError(f"value {value_id} must contain a scalar value")
            normalized[value_id] = {
                "value": value,
                "kind": kind,
                "confidence": confidence,
                "uncertainty": uncertainty,
            }
        return normalized, True
    facts = payload.get("facts")
    if not isinstance(facts, dict) or not facts:
        raise ValueError("facts or values must be a non-empty object")
    normalized = {}
    for fact_id, value in facts.items():
        if not isinstance(fact_id, str) or not fact_id.strip():
            raise ValueError("fact ids must be non-empty strings")
        if isinstance(value, (dict, list)) or value is None:
            raise ValueError(f"fact {fact_id} must be a scalar")
        normalized[fact_id] = {
            "value": value,
            "kind": "FACT",
            "confidence": "high",
            "uncertainty": D(0),
        }
    return normalized, False


def _thresholds(payload: dict[str, Any], strict: bool) -> dict[str, dict[str, Any]]:
    raw = payload.get("thresholds")
    if not strict:
        return {}
    if not isinstance(raw, dict) or not raw:
        raise ValueError("strict values mode requires a non-empty thresholds object")
    result: dict[str, dict[str, Any]] = {}
    required = {
        "value",
        "basis",
        "lookback",
        "confirmation",
        "tolerance",
        "minimum_confidence",
        "rationale",
    }
    for threshold_id, item in raw.items():
        if not isinstance(threshold_id, str) or not threshold_id.strip():
            raise ValueError("threshold ids must be non-empty strings")
        if not isinstance(item, dict) or not required <= set(item):
            raise ValueError(f"threshold {threshold_id} is missing required policy fields")
        value = dec(item["value"])
        tolerance = dec(item["tolerance"])
        confirmation = int(item["confirmation"])
        if tolerance < 0:
            raise ValueError(f"threshold {threshold_id} tolerance cannot be negative")
        if confirmation < 1:
            raise ValueError(f"threshold {threshold_id} confirmation must be >= 1")
        if not str(item["basis"]).strip() or not str(item["lookback"]).strip() or not str(
            item["rationale"]
        ).strip():
            raise ValueError(f"threshold {threshold_id} policy text cannot be empty")
        _confidence_rank(item["minimum_confidence"])
        result[threshold_id] = {
            "value": value,
            "basis": str(item["basis"]),
            "lookback": str(item["lookback"]),
            "confirmation": confirmation,
            "tolerance": tolerance,
            "minimum_confidence": str(item["minimum_confidence"]),
            "rationale": str(item["rationale"]),
        }
    return result


def evaluate_action(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate Action Matrix rules from canonical values and threshold policies."""
    values, strict = _normalize_values(payload)
    thresholds = _thresholds(payload, strict)
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
            value_key = "value_id" if strict else "fact"
            value_id = str(condition.get(value_key, "")).strip()
            if value_id not in values:
                raise ValueError(f"rule {rule_id} references missing value: {value_id}")
            operator = str(condition.get("operator", "")).strip()
            actual_record = values[value_id]
            actual = actual_record["value"]
            expected_id: str | None = None
            threshold_id: str | None = None
            policy: dict[str, Any] | None = None
            if strict:
                threshold_id = str(condition.get("threshold", "")).strip()
                if not threshold_id or threshold_id not in thresholds:
                    raise ValueError(
                        f"rule {rule_id} condition {index} must reference a registered threshold"
                    )
                policy = thresholds[threshold_id]
                expected = policy["value"]
            else:
                has_value = "value" in condition
                has_value_fact = "value_fact" in condition
                if has_value == has_value_fact:
                    raise ValueError(
                        f"rule {rule_id} condition {index} must define exactly one of value or value_fact"
                    )
                if has_value_fact:
                    expected_id = str(condition["value_fact"]).strip()
                    if expected_id not in values:
                        raise ValueError(
                            f"rule {rule_id} references missing expected fact: {expected_id}"
                        )
                    expected = values[expected_id]["value"]
                else:
                    expected = condition["value"]

            raw_result = _compare(actual, operator, expected)
            status = "true" if raw_result else "false"
            reason: str | None = None
            if strict and policy is not None:
                if _confidence_rank(actual_record["confidence"]) < _confidence_rank(
                    policy["minimum_confidence"]
                ):
                    status = "indeterminate"
                    reason = "value confidence below threshold policy minimum"
                left = _try_decimal(actual)
                right = _try_decimal(expected)
                if status != "indeterminate" and left is not None and right is not None:
                    denominator = max(abs(right), D("0.0000001"))
                    relative_distance = abs(left - right) / denominator
                    effective_tolerance = policy["tolerance"] + actual_record["uncertainty"]
                    if relative_distance <= effective_tolerance:
                        status = "indeterminate"
                        reason = "actual value is inside the threshold neutral band"
                if policy["confirmation"] > 1:
                    confirmation_id = str(condition.get("confirmation_value", "")).strip()
                    if not confirmation_id or confirmation_id not in values:
                        raise ValueError(
                            f"rule {rule_id} condition {index} requires confirmation_value"
                        )
                    confirmation_value = _try_decimal(values[confirmation_id]["value"])
                    if confirmation_value is None:
                        raise ValueError("confirmation_value must be numeric")
                    if confirmation_value < policy["confirmation"]:
                        status = "indeterminate"
                        reason = "confirmation requirement is not met"

            evaluated_conditions.append(
                {
                    "value_id": value_id,
                    "actual": _display_value(actual),
                    "operator": operator,
                    "expected": _display_value(expected),
                    "expected_id": expected_id,
                    "threshold_id": threshold_id,
                    "status": status,
                    "result": True if status == "true" else False if status == "false" else None,
                    "reason": reason,
                }
            )

        statuses = [item["status"] for item in evaluated_conditions]
        if logic == "all":
            if "false" in statuses:
                rule_status = "false"
            elif "indeterminate" in statuses:
                rule_status = "indeterminate"
            else:
                rule_status = "true"
        else:
            if "true" in statuses:
                rule_status = "true"
            elif "indeterminate" in statuses:
                rule_status = "indeterminate"
            else:
                rule_status = "false"
        evaluated.append(
            {
                "id": rule_id,
                "action": action,
                "logic": logic,
                "conditions": evaluated_conditions,
                "status": rule_status,
                "triggered": rule_status == "true",
                "priority": int(rule.get("priority", _PRIORITIES[action])),
            }
        )

    result = _resolve_evaluated(evaluated, payload.get("current_action"))
    result["values"] = {
        key: {
            "value": _display_value(item["value"]),
            "kind": item["kind"],
            "confidence": item["confidence"],
            "uncertainty": q(item["uncertainty"]),
        }
        for key, item in values.items()
    }
    result["thresholds"] = {
        key: {
            **{k: v for k, v in item.items() if k not in {"value", "tolerance"}},
            "value": q(item["value"]),
            "tolerance": q(item["tolerance"]),
        }
        for key, item in thresholds.items()
    }
    result["mode"] = "v2-threshold-policy" if strict else "legacy-facts"
    return result


def robustness(payload: dict[str, Any], shock: Decimal) -> dict[str, Any]:
    """Re-evaluate actions under +/- shocks to selected numeric values."""
    if shock <= 0:
        raise ValueError("shock must be positive")
    values, strict = _normalize_values(payload)
    if not strict:
        raise ValueError("robustness requires v2 values mode")
    sensitivity = payload.get("sensitivity_values")
    if not isinstance(sensitivity, list) or not sensitivity:
        raise ValueError("sensitivity_values must be a non-empty list")
    baseline = evaluate_action(payload)
    scenarios: list[dict[str, Any]] = []
    for value_id in sensitivity:
        if value_id not in values:
            raise ValueError(f"unknown sensitivity value: {value_id}")
        base = _try_decimal(values[value_id]["value"])
        if base is None:
            raise ValueError(f"sensitivity value {value_id} must be numeric")
        for direction, factor in [("down", D(1) - shock), ("up", D(1) + shock)]:
            shocked = copy.deepcopy(payload)
            shocked["values"][value_id]["value"] = str(base * factor)
            result = evaluate_action(shocked)
            scenarios.append(
                {
                    "value_id": value_id,
                    "direction": direction,
                    "shocked_value": q(base * factor),
                    "resolved_action": result["resolved_action"],
                }
            )
    stable = all(item["resolved_action"] == baseline["resolved_action"] for item in scenarios)
    return {
        "shock_pct": q(shock * D(100), "0.01"),
        "baseline_action": baseline["resolved_action"],
        "scenarios": scenarios,
        "stable": stable,
        "recommended_action": baseline["resolved_action"] if stable else "REVIEW",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    ttm = sub.add_parser("ttm-derive")
    ttm.add_argument("--input", required=True, help="JSON file path or '-' for stdin")

    revenue = sub.add_parser("revenue-bridge")
    revenue.add_argument("--input", required=True, help="JSON file path or '-' for stdin")

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
    rev.add_argument("--annual-dividend-yield")

    pair = sub.add_parser("return-pair")
    pair.add_argument("--current-price", required=True)
    pair.add_argument("--starting-eps", required=True)
    pair.add_argument("--eps-cagr", required=True)
    pair.add_argument("--exit-pe", required=True)
    pair.add_argument("--years", type=int, required=True)
    pair.add_argument("--target-return", required=True)
    pair.add_argument("--annual-dividend-per-share", default="0")
    pair.add_argument("--annual-dividend-yield")

    evaluate = sub.add_parser("evaluate-action")
    evaluate.add_argument("--input", required=True, help="JSON file path or '-' for stdin")

    robust = sub.add_parser("robustness")
    robust.add_argument("--input", required=True, help="JSON file path or '-' for stdin")
    robust.add_argument("--shock", required=True, help="decimal, e.g. 0.05")

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
    if args.command == "ttm-derive":
        result = ttm_derive(_read_json_input(args.input))
    elif args.command == "revenue-bridge":
        result = revenue_bridge(_read_json_input(args.input))
    elif args.command == "eps-bridge":
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
            annual_dividend_yield=None if args.annual_dividend_yield is None else dec(args.annual_dividend_yield),
        )
    elif args.command == "return-pair":
        result = return_pair(
            current_price=dec(args.current_price),
            starting_eps=dec(args.starting_eps),
            eps_cagr=dec(args.eps_cagr),
            exit_pe=dec(args.exit_pe),
            years=args.years,
            target_return=dec(args.target_return),
            annual_dividend_per_share=dec(args.annual_dividend_per_share),
            annual_dividend_yield=None if args.annual_dividend_yield is None else dec(args.annual_dividend_yield),
        )
    elif args.command == "evaluate-action":
        result = evaluate_action(_read_json_input(args.input))
    elif args.command == "robustness":
        result = robustness(_read_json_input(args.input), dec(args.shock))
    else:
        result = resolve_action(_read_json_input(args.input))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

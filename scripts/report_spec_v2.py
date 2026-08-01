from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Any

from scripts.valuation_runtime import revenue_bridge, return_pair, scenario_eps_bridge, ttm_derive

D = Decimal
PREC = 50
SCENARIOS = ("bear", "base", "bull")
CONFIDENCE = {"low": 1, "medium": 2, "high": 3}


class SpecError(ValueError):
    pass


def dec(value: Any) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else D(str(value))
    except Exception as exc:
        raise SpecError(f"invalid decimal: {value}") from exc
    if not result.is_finite():
        raise SpecError("numeric values must be finite")
    return result


def q(value: Decimal, places: str = "0.0001") -> str:
    return str(value.quantize(D(places), rounding=ROUND_HALF_UP))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SpecError(message)


def _fact(spec: dict[str, Any], fact_id: str) -> dict[str, Any]:
    facts = spec.get("facts", {})
    _require(fact_id in facts, f"undefined fact: {fact_id}")
    item = facts[fact_id]
    _require(isinstance(item, dict), f"fact {fact_id} must be an object")
    for field in ("value", "unit", "source", "tier", "confidence"):
        _require(field in item and str(item[field]).strip(), f"fact {fact_id} missing {field}")
    _require(str(item["confidence"]).lower() in CONFIDENCE, f"fact {fact_id} invalid confidence")
    uncertainty = dec(item.get("uncertainty", "0"))
    _require(uncertainty >= 0, f"fact {fact_id} uncertainty cannot be negative")
    return item


def _assumption(spec: dict[str, Any], assumption_id: str, scenario: str | None = None) -> dict[str, Any]:
    assumptions = spec.get("assumptions", {})
    _require(assumption_id in assumptions, f"undefined assumption: {assumption_id}")
    item = assumptions[assumption_id]
    _require(isinstance(item, dict), f"assumption {assumption_id} must be an object")
    scope = str(item.get("scope", "")).lower()
    _require(scope in {"global", *SCENARIOS}, f"assumption {assumption_id} invalid scope")
    if scenario is not None:
        _require(scope in {"global", scenario}, f"{scenario} cannot reference {scope} assumption {assumption_id}")
    for field in ("role", "rationale", "confidence"):
        _require(str(item.get(field, "")).strip(), f"assumption {assumption_id} missing {field}")
    _require(str(item["confidence"]).lower() in CONFIDENCE, f"assumption {assumption_id} invalid confidence")
    return item


def _value_from_ref(spec: dict[str, Any], reference: str, scenario: str | None = None) -> Decimal:
    if reference.startswith("FACT-"):
        return dec(_fact(spec, reference)["value"])
    if reference.startswith("ASM-"):
        item = _assumption(spec, reference, scenario)
        _require("value" in item, f"assumption {reference} has no scalar value")
        return dec(item["value"])
    raise SpecError(f"unsupported value reference: {reference}")


def _validate_revenue_period(spec: dict[str, Any], scenario: str, row: dict[str, Any]) -> dict[str, Any]:
    required = {"id", "period", "mode", "assumption_id"}
    _require(required <= set(row), f"{scenario} revenue row missing fields")
    assumption_id = str(row["assumption_id"])
    assumption = _assumption(spec, assumption_id, scenario)
    mode = str(row["mode"]).lower()
    _require(str(assumption.get("mode", "")).lower() == mode, f"{row['id']} mode mismatches {assumption_id}")
    payload: dict[str, Any] = {"id": row["id"], "period": row["period"], "mode": mode}
    if mode in {"guide_midpoint", "guide_high"}:
        _require("low" in assumption and "high" in assumption, f"{assumption_id} requires low/high")
        low, high = dec(assumption["low"]), dec(assumption["high"])
        _require(high >= low > 0, f"{assumption_id} invalid guide range")
        if mode == "guide_midpoint":
            payload.update({"low": str(low), "high": str(high), "source": assumption.get("source", assumption["rationale"])})
        else:
            payload.update({"mode": "explicit", "value": str(high), "source": assumption.get("source", assumption["rationale"]), "rationale": "guide high"})
    elif mode in {"yoy", "qoq"}:
        _require("growth" in assumption and "base_ref" in row, f"{row['id']} requires growth and base_ref")
        payload.update({"growth": str(dec(assumption["growth"])), "base_id": row["base_ref"]})
        if str(row["base_ref"]).startswith("FACT-"):
            payload["base_value"] = str(_value_from_ref(spec, row["base_ref"], scenario))
    elif mode in {"explicit", "consensus"}:
        _require("value" in assumption, f"{assumption_id} requires value")
        payload.update({"value": str(dec(assumption["value"])), "source": assumption.get("source", assumption["rationale"])})
        if mode == "explicit":
            payload["rationale"] = assumption["rationale"]
        else:
            _require(str(assumption.get("as_of", "")).strip(), f"{assumption_id} consensus requires as_of")
            payload["as_of"] = assumption["as_of"]
    else:
        raise SpecError(f"unsupported revenue mode: {mode}")
    return payload


def _payback_growth(price: Decimal, start_metric: Decimal, years: int, discount_rate: Decimal) -> Decimal:
    _require(price > 0 and start_metric > 0 and years > 0, "payback inputs must be positive")
    with localcontext() as ctx:
        ctx.prec = PREC
        def pv(g: Decimal) -> Decimal:
            return sum(start_metric * (D(1) + g) ** t / (D(1) + discount_rate) ** t for t in range(1, years + 1))
        low, high = D("-0.99"), D("5")
        _require(pv(high) >= price, "payback root not bracketed")
        for _ in range(240):
            mid = (low + high) / D(2)
            if pv(mid) >= price:
                high = mid
            else:
                low = mid
        return (low + high) / D(2)


def _compile_ttm(spec: dict[str, Any]) -> dict[str, Any]:
    series = spec.get("quarterly_series", {})
    required = {"eps", "revenue", "operating_income", "fcf"}
    _require(required <= set(series), "quarterly_series requires eps/revenue/operating_income/fcf")
    units: dict[str, str] = {}
    for name in ("eps", "revenue", "operating_income", "fcf"):
        ids = series[name]
        _require(isinstance(ids, list) and len(ids) == 4, f"{name} requires four fact IDs")
        observed = {str(_fact(spec, fact_id).get("unit", "")).strip() for fact_id in ids}
        _require(len(observed) == 1 and "" not in observed, f"{name} quarterly facts must use one explicit unit")
        units[name] = observed.pop()
    _require(
        len({units["revenue"], units["operating_income"], units["fcf"]}) == 1,
        "revenue/operating_income/fcf must use the same currency and scale",
    )
    current_price_id = str(spec.get("report", {}).get("current_price_fact_id", ""))
    if current_price_id:
        _require(
            str(_fact(spec, current_price_id).get("unit", "")).strip() == units["eps"],
            "current price and EPS must use the same per-share currency unit",
        )

    def components(name: str) -> list[dict[str, Any]]:
        ids = series[name]
        return [{"id": fid, "period": _fact(spec, fid).get("period", _fact(spec, fid).get("as_of", "")), "value": _fact(spec, fid)["value"]} for fid in ids]
    eps = ttm_derive({"id": "DERIVED-TTM-EPS", "metric": "TTM EPS", "mode": "sum", "components": components("eps")})
    eps["unit"] = units["eps"]
    rev = components("revenue")
    oi = components("operating_income")
    margin = ttm_derive({"id": "DERIVED-TTM-OP-MARGIN", "metric": "TTM operating margin", "mode": "ratio", "numerator": oi, "denominator": rev})
    margin["unit"] = "ratio"
    fcf = ttm_derive({"id": "DERIVED-TTM-FCF", "metric": "TTM FCF", "mode": "sum", "components": components("fcf")})
    fcf["unit"] = units["fcf"]
    return {"eps": eps, "operating_margin": margin, "fcf": fcf}


def _compile_scenario(spec: dict[str, Any], scenario: str, current_price: Decimal, target_return: Decimal) -> dict[str, Any]:
    scenarios = spec.get("scenarios", {})
    _require(scenario in scenarios, f"missing scenario: {scenario}")
    cfg = scenarios[scenario]
    rows = [_validate_revenue_period(spec, scenario, row) for row in cfg.get("revenue_periods", [])]
    revenue = revenue_bridge({"scenario": scenario, "periods": rows})
    refs = cfg.get("assumptions", {})
    roles = ("operating_margin", "tax_rate", "other_income", "diluted_shares", "eps_cagr", "exit_pe", "dividend_yield", "reference_multiple", "safety_margin")
    _require(set(roles) <= set(refs), f"{scenario} missing assumption roles")
    values = {role: _value_from_ref(spec, refs[role], scenario) for role in roles}
    eps = scenario_eps_bridge(
        revenue=dec(revenue["forward_revenue"]),
        operating_margin=values["operating_margin"],
        other_income=values["other_income"],
        tax_rate=values["tax_rate"],
        diluted_shares=values["diluted_shares"],
    )
    returns = return_pair(
        current_price=current_price,
        starting_eps=dec(eps["eps"]),
        eps_cagr=values["eps_cagr"],
        exit_pe=values["exit_pe"],
        years=int(spec.get("report", {}).get("return_years", 5)),
        target_return=target_return,
        annual_dividend_yield=values["dividend_yield"],
    )
    reference = dec(eps["eps"]) * values["reference_multiple"]
    target_price = dec(returns["target_return_price"])
    buy_price = target_price * (D(1) - values["safety_margin"])
    return {
        "revenue": revenue,
        "eps_bridge": eps,
        "returns": returns,
        "prices": {
            "forward_reference": q(reference),
            "target_return": q(target_price),
            "buy": q(buy_price),
            "safety_margin": q(values["safety_margin"]),
        },
        "assumption_refs": deepcopy(refs),
    }


def _bundle_value(bundle: dict[str, Any], reference: str) -> tuple[Decimal, str]:
    if reference.startswith("FACT-"):
        fact = bundle.get("facts", {}).get(reference)
        _require(isinstance(fact, dict), f"operating metric references undefined fact {reference}")
        return dec(fact.get("value")), str(fact.get("unit", ""))
    _require(reference.startswith("BUNDLE:/"), f"operating metric uses unsupported value_ref {reference}")
    current: Any = bundle
    parent: Any = None
    for raw in reference.removeprefix("BUNDLE:/").split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        _require(isinstance(current, dict) and part in current, f"operating metric references undefined bundle path {reference}")
        parent = current
        current = current[part]
    if isinstance(current, dict):
        _require("value" in current, f"operating metric bundle object has no value {reference}")
        return dec(current["value"]), str(current.get("unit", ""))
    unit = str(parent.get("unit", "")) if isinstance(parent, dict) else ""
    return dec(current), unit


def _metric_status(raw: dict[str, Any], bundle: dict[str, Any], index: int) -> dict[str, Any]:
    label = f"operating.metrics[{index}]"
    for field in ("metric_id", "label", "value_ref", "unit", "direction", "hold_threshold", "reduce_threshold", "tolerance", "uncertainty"):
        _require(str(raw.get(field, "")).strip(), f"{label} missing {field}")
    direction = str(raw["direction"]).lower()
    _require(direction in {"higher_is_better", "lower_is_better"}, f"{label} invalid direction")
    value, derived_unit = _bundle_value(bundle, str(raw["value_ref"]))
    declared_unit = str(raw["unit"]).strip()
    if derived_unit:
        _require(declared_unit == derived_unit, f"{label} unit {declared_unit} mismatches referenced value unit {derived_unit}")
    hold = dec(raw["hold_threshold"])
    reduce = dec(raw["reduce_threshold"])
    tolerance = dec(raw["tolerance"])
    uncertainty = dec(raw["uncertainty"])
    band = tolerance + uncertainty
    _require(tolerance >= 0 and uncertainty >= 0, f"{label} tolerance and uncertainty must be non-negative")
    if direction == "higher_is_better":
        _require(hold >= reduce, f"{label} higher_is_better requires hold_threshold >= reduce_threshold")
        near_hold = abs(value - hold) <= abs(hold) * band
        near_reduce = abs(value - reduce) <= abs(reduce) * band
        status = "review" if near_hold or near_reduce else ("reduce" if value < reduce else "hold" if value > hold else "review")
    else:
        _require(hold <= reduce, f"{label} lower_is_better requires hold_threshold <= reduce_threshold")
        near_hold = abs(value - hold) <= abs(hold) * band
        near_reduce = abs(value - reduce) <= abs(reduce) * band
        status = "review" if near_hold or near_reduce else ("reduce" if value > reduce else "hold" if value < hold else "review")

    confirmation_value = dec(raw.get("confirmation_periods", raw.get("confirmation", 1)))
    _require(confirmation_value == confirmation_value.to_integral_value() and confirmation_value >= 1, f"{label} confirmation_periods must be a positive integer")
    confirmation_periods = int(confirmation_value)
    confirmation_ref = str(raw.get("confirmation_ref", "")).strip()
    confirmation_actual: Decimal | None = None
    if confirmation_periods > 1:
        _require(confirmation_ref, f"{label} requires confirmation_ref when confirmation_periods > 1")
        confirmation_actual, _ = _bundle_value(bundle, confirmation_ref)
        _require(confirmation_actual >= 0 and confirmation_actual == confirmation_actual.to_integral_value(), f"{label} confirmation_ref must resolve to a non-negative integer")
        if status == "reduce" and confirmation_actual < confirmation_periods:
            status = "review"

    return {
        "metric_id": str(raw["metric_id"]),
        "label": str(raw["label"]),
        "value_ref": str(raw["value_ref"]),
        "value": q(value),
        "unit": declared_unit,
        "direction": direction,
        "hold_threshold": q(hold),
        "reduce_threshold": q(reduce),
        "tolerance": q(tolerance),
        "uncertainty": q(uncertainty),
        "confirmation_periods": confirmation_periods,
        "confirmation_ref": confirmation_ref or None,
        "confirmation_actual": q(confirmation_actual) if confirmation_actual is not None else None,
        "status": status,
    }


def _evaluate_operating_policy(policy: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    metrics = policy.get("metrics")
    if metrics is None:
        for field in ("metric", "hold_threshold", "reduce_threshold", "tolerance", "uncertainty", "confirmation"):
            _require(field in policy, f"operating policy missing {field}")
        _require(policy["metric"] == "ttm_fcf", "legacy operating policy requires ttm_fcf")
        metrics = [{
            "metric_id": "OP-TTM-FCF",
            "label": "TTM FCF",
            "value_ref": "BUNDLE:/derived/ttm/fcf/value",
            "unit": bundle["derived"]["ttm"]["fcf"].get("unit", ""),
            "direction": "higher_is_better",
            "hold_threshold": policy["hold_threshold"],
            "reduce_threshold": policy["reduce_threshold"],
            "tolerance": policy["tolerance"],
            "uncertainty": policy["uncertainty"],
            "confirmation_periods": policy["confirmation"],
        }]
        legacy = True
    else:
        _require(isinstance(metrics, list) and metrics, "operating.metrics must be a non-empty list")
        legacy = False
    metric_results = [_metric_status(raw, bundle, index) for index, raw in enumerate(metrics)]
    statuses = {item["status"] for item in metric_results}
    status = "reduce" if "reduce" in statuses else "review" if "review" in statuses else "hold"
    result: dict[str, Any] = {
        "aggregation": "any_reduce_then_review",
        "status": status,
        "metrics": metric_results,
    }
    if legacy:
        item = metric_results[0]
        result.update({
            "ttm_fcf": item["value"],
            "hold_threshold": item["hold_threshold"],
            "reduce_threshold": item["reduce_threshold"],
            "tolerance": item["tolerance"],
            "uncertainty": item["uncertainty"],
        })
    return result


def _portfolio_gate(spec: dict[str, Any], candidate: str, reason: str) -> tuple[str, str, dict[str, Any]]:
    required = bool(spec.get("decision_policy", {}).get("require_portfolio_context", False))
    raw = spec.get("portfolio_context")
    if not required and raw is None:
        return candidate, reason, {"required": False, "position_status": "not_provided", "complete": True, "gate": "not_required"}
    _require(isinstance(raw, dict), "portfolio_context must be an object")
    status = str(raw.get("position_status", "")).lower()
    _require(status in {"held", "not_held", "unknown"}, "portfolio_context.position_status must be held/not_held/unknown")
    for field in ("as_of", "source", "confidence"):
        _require(str(raw.get(field, "")).strip(), f"portfolio_context missing {field}")
    _require(str(raw["confidence"]).lower() in CONFIDENCE, "portfolio_context invalid confidence")

    current_weight = dec(raw["current_weight"]) if raw.get("current_weight") is not None else None
    target_weight = dec(raw["target_weight"]) if raw.get("target_weight") is not None else None
    for name, value in (("current_weight", current_weight), ("target_weight", target_weight)):
        if value is not None:
            _require(D(0) <= value <= D(1), f"portfolio_context.{name} must be between 0 and 1")

    complete = status == "not_held" or (status == "held" and current_weight is not None)
    gate = "passed"
    action = candidate
    gated_reason = reason
    if status == "not_held":
        action = "NOT_APPLICABLE"
        gated_reason = "no existing position"
        gate = "not_applicable"
    elif status == "unknown":
        action = "REVIEW"
        gated_reason = f"portfolio context unknown; research candidate is {candidate}"
        gate = "blocked_missing_position_status"
        complete = False
    elif candidate == "REDUCE" and (current_weight is None or target_weight is None or target_weight >= current_weight):
        action = "REVIEW"
        gated_reason = "portfolio weights do not support an executable reduce instruction"
        gate = "blocked_missing_reduce_target"
        complete = False

    context = {
        "required": required,
        "position_status": status,
        "as_of": str(raw["as_of"]),
        "source": str(raw["source"]),
        "confidence": str(raw["confidence"]).lower(),
        "current_weight": q(current_weight) if current_weight is not None else None,
        "target_weight": q(target_weight) if target_weight is not None else None,
        "tax_friction": str(raw.get("tax_friction", "unknown")),
        "constraints": str(raw.get("constraints", "")),
        "complete": complete,
        "gate": gate,
    }
    return action, gated_reason, context


def _evaluate_policy(spec: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    policy = spec.get("decision_policy", {})
    _require({"valuation", "operating", "thesis_break"} <= set(policy), "decision_policy requires valuation/operating/thesis_break")
    valuation = policy["valuation"]
    for field in ("reduce_gap", "review_band", "buy_below", "add_below"):
        _require(field in valuation, f"valuation policy missing {field}")
    _require(valuation["buy_below"] == "base.buy_price", "buy_below must use base.buy_price")
    _require(valuation["add_below"] == "base.buy_price", "add_below must use base.buy_price")
    current = dec(bundle["facts"][bundle["report"]["current_price_fact_id"]]["value"])
    target_return = dec(bundle["target_return"])
    base = bundle["scenarios"]["base"]
    base_irr = dec(base["returns"]["irr"]["irr_pct"]) / D(100)
    irr_gap = target_return - base_irr
    reduce_gap = dec(valuation["reduce_gap"])
    review_band = dec(valuation["review_band"])
    buy_price = dec(base["prices"]["buy"])
    target_price = dec(base["prices"]["target_return"])

    operating = _evaluate_operating_policy(policy["operating"], bundle)
    operating_status = operating["status"]

    thesis = policy["thesis_break"]
    _require("conditions" in thesis and isinstance(thesis["conditions"], list), "thesis_break requires conditions")
    thesis_broken = False
    thesis_results = []
    for condition in thesis["conditions"]:
        fid = condition["fact_id"]
        actual = dec(_fact(spec, fid)["value"])
        expected = dec(condition["value"])
        op = condition["operator"]
        result = {"<": actual < expected, "<=": actual <= expected, ">": actual > expected, ">=": actual >= expected}[op]
        thesis_results.append({
            "fact_id": fid,
            "label": str(condition.get("label", fid)),
            "unit": str(_fact(spec, fid).get("unit", "")),
            "actual": q(actual),
            "operator": op,
            "expected": q(expected),
            "result": result,
        })
    logic = thesis.get("logic", "all")
    thesis_broken = all(x["result"] for x in thesis_results) if logic == "all" else any(x["result"] for x in thesis_results)

    if thesis_broken:
        new_money = "DO_NOT_BUY"
    elif current <= buy_price and operating_status == "hold":
        new_money = "BUY"
    elif current <= target_price:
        new_money = "WATCH"
    else:
        new_money = "DO_NOT_BUY"

    if thesis_broken:
        candidate = "SELL"
        candidate_reason = "thesis-break policy triggered"
    elif irr_gap > reduce_gap + review_band:
        candidate = "REDUCE"
        candidate_reason = "base IRR materially below hurdle"
    elif irr_gap > max(D(0), reduce_gap - review_band):
        candidate = "REVIEW"
        candidate_reason = "valuation gap within review band"
    elif operating_status == "reduce":
        candidate = "REDUCE"
        candidate_reason = "operating policy triggered"
    elif operating_status == "review":
        candidate = "REVIEW"
        candidate_reason = "operating metric in explicit neutral band"
    else:
        candidate = "HOLD"
        candidate_reason = "valuation and operating policy support holding"

    shock = dec(policy.get("robustness_shock", "0.05"))
    shocked_actions = []
    for multiplier in (D(1) - shock, D(1) + shock):
        shocked_gap = target_return - base_irr * multiplier
        action = "REDUCE" if shocked_gap > reduce_gap + review_band else "REVIEW" if shocked_gap > max(D(0), reduce_gap - review_band) else candidate
        shocked_actions.append(action)
    stable = all(action == candidate for action in shocked_actions)
    if not stable and candidate not in {"SELL"}:
        candidate = "REVIEW"
        candidate_reason = "decision changes under configured robustness shock"

    existing, reason, portfolio = _portfolio_gate(spec, candidate, candidate_reason)

    return {
        "new_money_action": new_money,
        "existing_position_action": existing,
        "existing_position_candidate_action": candidate,
        "reason": reason,
        "candidate_reason": candidate_reason,
        "valuation": {
            "base_irr": q(base_irr),
            "target_return": q(target_return),
            "irr_gap": q(irr_gap),
            "reduce_gap": q(reduce_gap),
            "review_band": q(review_band),
        },
        "operating": operating,
        "portfolio_context": portfolio,
        "thesis_break": {"triggered": thesis_broken, "logic": logic, "conditions": thesis_results},
        "robustness": {"shock": q(shock), "stable": stable, "shocked_actions": shocked_actions},
    }


def compile_spec(spec: dict[str, Any]) -> dict[str, Any]:
    _require(spec.get("schema_version") == "report-spec-v2", "schema_version must be report-spec-v2")
    report = spec.get("report", {})
    for field in ("ticker", "company", "as_of", "currency", "current_price_fact_id", "target_return_assumption_id"):
        _require(str(report.get(field, "")).strip(), f"report missing {field}")
    current_price = _value_from_ref(spec, report["current_price_fact_id"])
    target_return = _value_from_ref(spec, report["target_return_assumption_id"])
    _require(current_price > 0 and target_return > 0, "price and target return must be positive")
    ttm = _compile_ttm(spec)
    scenarios = {name: _compile_scenario(spec, name, current_price, target_return) for name in SCENARIOS}
    payback_rates = report.get("payback_discount_rates", ["0", str(target_return)])
    payback = {
        str(rate): q(_payback_growth(current_price, dec(ttm["eps"]["value"]), int(report.get("payback_years", 10)), dec(rate)))
        for rate in payback_rates
    }
    bundle: dict[str, Any] = {
        "schema_version": "report-bundle-v2",
        "compiler_version": "2.0.0",
        "report": deepcopy(report),
        "facts": deepcopy(spec["facts"]),
        "target_return": q(target_return),
        "derived": {"ttm": ttm, "payback_required_growth": payback},
        "scenarios": scenarios,
        "narrative": deepcopy(spec.get("narrative", {})),
        "sources": deepcopy(spec.get("sources", [])),
    }
    bundle["decision"] = _evaluate_policy(spec, bundle)
    base_prices = scenarios["base"]["prices"]
    bundle["price_zones"] = [
        {"max": base_prices["buy"], "name": "安全边际买入区", "action": "BUY"},
        {"min": base_prices["buy"], "max": base_prices["target_return"], "name": "目标回报达标区", "action": "WATCH"},
        {"min": base_prices["target_return"], "max": base_prices["forward_reference"], "name": "回报不足观察区", "action": "DO_NOT_BUY"},
        {"min": base_prices["forward_reference"], "name": "估值偏高区", "action": "DO_NOT_BUY"},
    ]
    bundle["spec_hash"] = sha256(spec)
    without_hash = deepcopy(bundle)
    bundle["bundle_hash"] = sha256(without_hash)
    return bundle

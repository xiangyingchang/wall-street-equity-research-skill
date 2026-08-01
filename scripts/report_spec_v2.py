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
    def components(name: str) -> list[dict[str, Any]]:
        ids = series[name]
        _require(isinstance(ids, list) and len(ids) == 4, f"{name} requires four fact IDs")
        return [{"id": fid, "period": _fact(spec, fid).get("period", _fact(spec, fid).get("as_of", "")), "value": _fact(spec, fid)["value"]} for fid in ids]
    eps = ttm_derive({"id": "DERIVED-TTM-EPS", "metric": "TTM EPS", "mode": "sum", "components": components("eps")})
    rev = components("revenue")
    oi = components("operating_income")
    margin = ttm_derive({"id": "DERIVED-TTM-OP-MARGIN", "metric": "TTM operating margin", "mode": "ratio", "numerator": oi, "denominator": rev})
    fcf = ttm_derive({"id": "DERIVED-TTM-FCF", "metric": "TTM FCF", "mode": "sum", "components": components("fcf")})
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

    operating = policy["operating"]
    for field in ("metric", "hold_threshold", "reduce_threshold", "tolerance", "uncertainty", "confirmation"):
        _require(field in operating, f"operating policy missing {field}")
    _require(operating["metric"] == "ttm_fcf", "v2 currently requires ttm_fcf operating metric")
    fcf = dec(bundle["derived"]["ttm"]["fcf"]["value"])
    hold = dec(operating["hold_threshold"])
    reduce = dec(operating["reduce_threshold"])
    band = dec(operating["tolerance"]) + dec(operating["uncertainty"])
    _require(band >= 0, "operating tolerance + uncertainty must be non-negative")
    hold_indeterminate = abs(fcf - hold) <= abs(hold) * band
    reduce_indeterminate = abs(fcf - reduce) <= abs(reduce) * band
    operating_status = "review" if hold_indeterminate or reduce_indeterminate else ("reduce" if fcf < reduce else "hold")

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
        thesis_results.append({"fact_id": fid, "actual": q(actual), "operator": op, "expected": q(expected), "result": result})
    logic = thesis.get("logic", "all")
    thesis_broken = all(x["result"] for x in thesis_results) if logic == "all" else any(x["result"] for x in thesis_results)

    if current <= buy_price and operating_status == "hold":
        new_money = "BUY"
    elif current <= target_price:
        new_money = "WATCH"
    else:
        new_money = "DO_NOT_BUY"

    if thesis_broken:
        existing = "SELL"
        reason = "thesis-break policy triggered"
    elif irr_gap > reduce_gap + review_band:
        existing = "REDUCE"
        reason = "base IRR materially below hurdle"
    elif irr_gap > max(D(0), reduce_gap - review_band):
        existing = "REVIEW"
        reason = "valuation gap within review band"
    elif operating_status == "reduce":
        existing = "REDUCE"
        reason = "operating policy triggered"
    elif operating_status == "review":
        existing = "REVIEW"
        reason = "operating metric in explicit neutral band"
    else:
        existing = "HOLD"
        reason = "valuation and operating policy support holding"

    shock = dec(policy.get("robustness_shock", "0.05"))
    shocked_actions = []
    for multiplier in (D(1) - shock, D(1) + shock):
        shocked_gap = target_return - base_irr * multiplier
        action = "REDUCE" if shocked_gap > reduce_gap + review_band else "REVIEW" if shocked_gap > max(D(0), reduce_gap - review_band) else existing
        shocked_actions.append(action)
    stable = all(action == existing for action in shocked_actions)
    if not stable and existing not in {"SELL"}:
        existing = "REVIEW"
        reason = "decision changes under configured robustness shock"

    return {
        "new_money_action": new_money,
        "existing_position_action": existing,
        "reason": reason,
        "valuation": {
            "base_irr": q(base_irr),
            "target_return": q(target_return),
            "irr_gap": q(irr_gap),
            "reduce_gap": q(reduce_gap),
            "review_band": q(review_band),
        },
        "operating": {
            "ttm_fcf": q(fcf),
            "hold_threshold": q(hold),
            "reduce_threshold": q(reduce),
            "tolerance": q(dec(operating["tolerance"])),
            "uncertainty": q(dec(operating["uncertainty"])),
            "status": operating_status,
        },
        "thesis_break": {"triggered": thesis_broken, "conditions": thesis_results},
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

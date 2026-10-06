"""v3.2 decision-coherence layer: make every action surface say the same thing.

The valuation, the price ladder, the cash-flow escalation table, the triggers and the
first-page decision used to be compiled independently, so a report could say "new money:
WATCH" while the ladder said "trial position allowed" and the cash-flow trigger said
"cut the position cap". This module compiles one executable answer and fails closed on
contradictions. It is company-agnostic: every rule reads only spec/bundle structure.

Spec inputs
-----------
report.cash_valuation.decisive_basis / decisive_reason
    Which compiled basis (an earnings basis id, ``fcf`` or ``normalized_fcf``) decides
    whether full-size new money is justified.
decision_support.ladder_premises[tier_id].conditions[]
    Machine-checkable premise per tier. Each item is either
    ``{label, ref, unit?, operator, threshold}`` (evaluated now) or
    ``{label, status: "unknown", pending}`` (evidence not yet published).
    Tiers that allocate new money (position_max > 0) must declare at least one.
decision_support.cash_flow_escalation
    ``{counter_ref, levels: [{level, min_count, action, new_money_cap}]}``; the current
    level caps the executable position and the top level must agree with thesis_break.
decision_support.roic
    ``{years, operating_income_fact_ids, tax_rate_ref, invested_capital: [{label, sign, fact_ids}], interpretation}``.
decision_policy.price_ladder.cash_gate_waiver (optional)
    Explicit reason when majority-size tiers do not clear the hurdle on the decisive basis.

Outputs bundle["decision_coherence"] and annotates bundle["price_ladder"]["tiers"].
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from scripts.report_research_v21 import _claim, _json_pointer, _validate_text
from scripts.report_spec_v2 import SpecError

D = Decimal
OPERATORS = {">", ">=", "<", "<=", "==", "!="}
MAJORITY_POSITION = D("0.5")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SpecError(message)


def _dec(value: Any, label: str) -> Decimal:
    try:
        number = D(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SpecError(f"{label} must be a decimal") from exc
    _require(number.is_finite(), f"{label} must be finite")
    return number


def _q(value: Decimal, places: str = "0.0001") -> str:
    return str(value.quantize(D(places)))


def _lookup(spec: dict[str, Any], bundle: dict[str, Any], ref: Any, label: str, unit: Any = None) -> tuple[Any, str]:
    reference = str(ref or "").strip()
    if reference.startswith("FACT-"):
        fact = spec.get("facts", {}).get(reference)
        _require(isinstance(fact, dict), f"{label} references undefined fact {reference}")
        fact_unit = str(fact.get("unit", "")).strip()
        if unit:
            _require(str(unit).strip() == fact_unit, f"{label} unit {unit} mismatches fact unit {fact_unit}")
        return fact["value"], fact_unit
    if reference.startswith("ASM-"):
        item = spec.get("assumptions", {}).get(reference)
        _require(isinstance(item, dict), f"{label} references undefined assumption {reference}")
        return item["value"], "ratio"
    _require(reference.startswith("BUNDLE:/"), f"{label} requires FACT-, ASM- or BUNDLE:/ ref")
    value = _json_pointer(bundle, reference.removeprefix("BUNDLE:"))
    _require(value is not None and not isinstance(value, (dict, list)), f"{label} bundle path must resolve to a scalar")
    return value, str(unit or "").strip()


def _compare(actual: Any, operator: str, threshold: Any, label: str) -> bool:
    if operator in {"==", "!="} and not _is_number(actual):
        equal = str(actual) == str(threshold)
        return equal if operator == "==" else not equal
    left, right = _dec(actual, f"{label}.actual"), _dec(threshold, f"{label}.threshold")
    return {
        ">": left > right, ">=": left >= right, "<": left < right, "<=": left <= right,
        "==": left == right, "!=": left != right,
    }[operator]


def _is_number(value: Any) -> bool:
    try:
        return D(str(value)).is_finite()
    except (InvalidOperation, ValueError):
        return False


# ---------------------------------------------------------------- premises / tiers
def _premise_status(spec: dict[str, Any], bundle: dict[str, Any], tier: dict[str, Any], raw: Any) -> dict[str, Any]:
    label = f"decision_support.ladder_premises.{tier['tier_id']}.conditions"
    conditions = raw.get("conditions") if isinstance(raw, dict) else None
    if conditions is None:
        _require(D(str(tier["position_max"])) == 0, f"{label} required: tiers that allocate new money need machine-checkable premises")
        return {"status": "met", "conditions": []}
    _require(isinstance(conditions, list) and conditions, f"{label} must be a non-empty list")
    out = []
    for index, item in enumerate(conditions):
        item_label = f"{label}[{index}]"
        _require(isinstance(item, dict), f"{item_label} must be an object")
        name = _validate_text(item.get("label"), f"{item_label}.label", minimum=4)
        if str(item.get("status", "")).lower() == "unknown":
            pending = _validate_text(item.get("pending"), f"{item_label}.pending", minimum=4)
            out.append({"label": name, "status": "unknown", "pending": pending})
            continue
        operator = str(item.get("operator", ""))
        _require(operator in OPERATORS, f"{item_label}.operator must be one of {', '.join(sorted(OPERATORS))}")
        _require("threshold" in item, f"{item_label} requires threshold")
        actual, unit = _lookup(spec, bundle, item.get("ref"), item_label, item.get("unit"))
        result = _compare(actual, operator, item["threshold"], item_label)
        out.append({
            "label": name, "status": "met" if result else "unmet", "ref": str(item["ref"]), "unit": unit,
            "actual": str(actual), "operator": operator, "threshold": str(item["threshold"]),
        })
    statuses = {x["status"] for x in out}
    status = "unmet" if "unmet" in statuses else "unknown" if "unknown" in statuses else "met"
    return {"status": status, "conditions": out}


# ---------------------------------------------------------------- escalation
def _escalation(spec: dict[str, Any], bundle: dict[str, Any], raw: Any) -> dict[str, Any]:
    label = "decision_support.cash_flow_escalation"
    _require(isinstance(raw, dict), f"v3.2 requires {label} (consecutive negative cash-flow levels)")
    counter_ref = str(raw.get("counter_ref", "")).strip()
    counter_label = _validate_text(raw.get("counter_label"), f"{label}.counter_label", minimum=4)
    actual_raw, unit = _lookup(spec, bundle, counter_ref, f"{label}.counter_ref")
    _require(unit == "quarters", f"{label}.counter_ref must be a fact with unit 'quarters'")
    actual = _dec(actual_raw, f"{label}.counter_ref")
    levels = raw.get("levels")
    _require(isinstance(levels, list) and len(levels) >= 2, f"{label} requires at least two levels")
    out = []
    previous_count, previous_cap = D(0), D(1)
    for index, item in enumerate(levels):
        item_label = f"{label}.levels[{index}]"
        _require(isinstance(item, dict), f"{item_label} must be an object")
        count = _dec(item.get("min_count"), f"{item_label}.min_count")
        cap = _dec(item.get("new_money_cap"), f"{item_label}.new_money_cap")
        _require(count == count.to_integral_value() and count > previous_count, f"{item_label}.min_count must be integers strictly increasing from 1")
        _require(D(0) <= cap <= previous_cap, f"{item_label}.new_money_cap must be in [0, 1] and non-increasing")
        action = _validate_text(item.get("action"), f"{item_label}.action", minimum=6)
        out.append({"level": index + 1, "min_count": str(int(count)), "new_money_cap": _q(cap), "action": action})
        previous_count, previous_cap = count, cap
    _require(out[-1]["new_money_cap"] == _q(D(0)), f"{label} top level must stop all new money (new_money_cap 0)")
    current = 0
    for item in out:
        if actual >= D(item["min_count"]):
            current = item["level"]
    # The top level must coincide with the thesis-break counter threshold when both exist.
    for condition in spec.get("decision_policy", {}).get("thesis_break", {}).get("conditions", []):
        if str(condition.get("fact_id")) == counter_ref and str(condition.get("operator")) in {">=", ">"}:
            threshold = _dec(condition.get("value"), "thesis_break counter threshold")
            if str(condition.get("operator")) == ">":
                threshold += 1
            _require(D(out[-1]["min_count"]) == threshold,
                     f"{label} top level min_count {out[-1]['min_count']} must equal the thesis-break threshold {int(threshold)}")
    cap = D(out[current - 1]["new_money_cap"]) if current else D(1)
    return {"counter_ref": counter_ref, "counter_label": counter_label, "actual": str(int(actual)), "current_level": current, "new_money_cap": _q(cap), "levels": out}


# ---------------------------------------------------------------- ROIC
def _roic(spec: dict[str, Any], bundle: dict[str, Any], raw: Any) -> dict[str, Any]:
    label = "decision_support.roic"
    _require(isinstance(raw, dict), f"v3.2 requires {label} (return on invested capital and incremental ROIC)")
    years = raw.get("years")
    _require(isinstance(years, list) and len(years) >= 2, f"{label} requires at least two years")
    oi_ids = raw.get("operating_income_fact_ids")
    _require(isinstance(oi_ids, list) and len(oi_ids) == len(years), f"{label}.operating_income_fact_ids must align with years")
    tax_raw, _ = _lookup(spec, bundle, raw.get("tax_rate_ref"), f"{label}.tax_rate_ref")
    tax = _dec(tax_raw, f"{label}.tax_rate")
    _require(D(0) <= tax < D(1), f"{label}.tax_rate must be in [0, 1)")
    components = raw.get("invested_capital")
    _require(isinstance(components, list) and len(components) >= 2, f"{label}.invested_capital requires at least two components")
    units: set[str] = set()
    nopat, capital = [], []
    for year_index, year in enumerate(years):
        value, unit = _lookup(spec, bundle, oi_ids[year_index], f"{label}.operating_income[{year}]")
        units.add(unit)
        nopat.append(_dec(value, f"{label}.operating_income[{year}]") * (D(1) - tax))
        total = D(0)
        for c_index, component in enumerate(components):
            c_label = f"{label}.invested_capital[{c_index}]"
            _require(isinstance(component, dict), f"{c_label} must be an object")
            _validate_text(component.get("label"), f"{c_label}.label", minimum=2)
            sign = int(component.get("sign", 1))
            _require(sign in {1, -1}, f"{c_label}.sign must be 1 or -1")
            ids = component.get("fact_ids")
            _require(isinstance(ids, list) and len(ids) == len(years), f"{c_label}.fact_ids must align with years")
            c_value, c_unit = _lookup(spec, bundle, ids[year_index], f"{c_label}[{year}]")
            units.add(c_unit)
            total += sign * _dec(c_value, f"{c_label}[{year}]")
        _require(total > 0, f"{label} invested capital must be positive in {year}")
        capital.append(total)
    _require(len(units) == 1, f"{label} operating income and capital components must share one unit")
    rows = [
        {"year": str(year), "nopat": _q(n, "0.01"), "invested_capital": _q(c, "0.01"), "roic": _q(n / c)}
        for year, n, c in zip(years, nopat, capital)
    ]
    delta_capital = capital[-1] - capital[0]
    incremental = _q((nopat[-1] - nopat[0]) / delta_capital) if delta_capital > 0 else None
    method = _validate_text(raw.get("method"), f"{label}.method", minimum=12)
    return {
        "unit": units.pop(), "tax_rate": _q(tax), "method": method, "rows": rows,
        "components": [{"label": str(c["label"]), "sign": int(c.get("sign", 1))} for c in components],
        "incremental_roic": incremental, "incremental_from": str(years[0]), "incremental_to": str(years[-1]),
        "interpretation": _claim(raw.get("interpretation"), spec, bundle, f"{label}.interpretation", text_field="text"),
    }


# ---------------------------------------------------------------- main
def compile_decision_coherence(spec: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    cash = bundle["derived"]["cash_valuation"]
    ladder = bundle["price_ladder"]
    decision = bundle["decision"]
    support_raw = spec.get("decision_support", {})
    decisive = cash.get("decisive")
    _require(isinstance(decisive, dict), "v3.2 requires report.cash_valuation.decisive_basis (which basis decides full-size new money)")
    current = _dec(bundle["facts"][bundle["report"]["current_price_fact_id"]]["value"], "current price")
    target_return = _dec(bundle["target_return"], "target_return")
    decisive_row = next(row for row in cash["bases"] if row["basis_id"] == decisive["basis_id"])
    decisive_ps = _dec(decisive_row["per_share_price"], "decisive per-share value")

    # 1. tier premises, decisive yield at each tier's ceiling, cash gate for majority-size tiers
    premises_raw = support_raw.get("ladder_premises", {})
    waiver = str(spec["decision_policy"]["price_ladder"].get("cash_gate_waiver", "")).strip()
    gate_failures = []
    for tier in ladder["tiers"]:
        status = _premise_status(spec, bundle, tier, premises_raw.get(tier["tier_id"]))
        tier["premise_status"] = status["status"]
        tier["premise_conditions"] = status["conditions"]
        top = _dec(tier["ceiling"], "tier ceiling") if tier.get("ceiling") is not None else None
        tier["decisive_yield_at_ceiling"] = _q(decisive_ps / top) if top and top > 0 else None
        if top is not None and _dec(tier["position_min"], "position_min") >= MAJORITY_POSITION and decisive_ps / top < target_return - D("0.0001"):
            gate_failures.append(tier["tier_id"])
    if gate_failures:
        _require(len(waiver) >= 20, (
            f"price ladder tiers {', '.join(gate_failures)} allocate >= half the target position but the decisive basis "
            f"({decisive['label']}) does not clear the hurdle at their ceiling; lower their floors toward the decisive "
            f"confirmation price or state decision_policy.price_ladder.cash_gate_waiver"))

    # 2. escalation cap + executable tier
    escalation = _escalation(spec, bundle, support_raw.get("cash_flow_escalation"))
    price_index = next(i for i, tier in enumerate(ladder["tiers"]) if tier["current"])
    executable_index = None
    if not ladder.get("suspended"):
        for index in range(price_index, -1, -1):
            if ladder["tiers"][index]["premise_status"] == "met":
                executable_index = index
                break
    for index, tier in enumerate(ladder["tiers"]):
        tier["executable"] = index == executable_index
    tier_max = _dec(ladder["tiers"][executable_index]["position_max"], "position_max") if executable_index is not None else D(0)
    cap = _dec(escalation["new_money_cap"], "escalation cap")
    executable_max = min(tier_max, cap)
    blockers = []
    price_tier = ladder["tiers"][price_index]
    if ladder.get("suspended"):
        blockers.append("投资逻辑破坏条件已触发，阶梯暂停")
    for condition in price_tier["premise_conditions"]:
        if condition["status"] == "unmet":
            blockers.append(f"{condition['label']}（未满足）")
        elif condition["status"] == "unknown":
            blockers.append(f"{condition['label']}（待{condition['pending']}）")
    if cap < tier_max:
        blockers.append(f"现金流升级表第 {escalation['current_level']} 级限制新资金上限")

    # 3. cross-surface invariants
    new_money = decision["new_money_action"]
    watch_cap = _dec(ladder["watch_trial_cap"], "watch_trial_cap")
    if new_money == "DO_NOT_BUY":
        _require(executable_max == 0, "coherence: new money DO_NOT_BUY but the ladder still allows a position")
    if new_money == "WATCH":
        _require(executable_max <= watch_cap, "coherence: new money WATCH but executable position exceeds watch_trial_cap")
    if new_money == "BUY":
        _require(not price_tier["above_buy_price"], "coherence: new money BUY but current price sits in a tier above the buy price")
    triggers = bundle["decision_support"]["action_triggers"]
    for trigger in triggers:
        if trigger["category"] == "thesis_break":
            _require(trigger.get("existing_action") == "SELL", "coherence: thesis_break trigger must map existing positions to SELL")
        if trigger["category"] == "valuation":
            _require(trigger.get("existing_action") != "SELL", "coherence: valuation alone must never map existing positions to SELL")
    if escalation["current_level"]:
        _require(any(t["category"] == "cash_flow" for t in triggers), "coherence: active cash-flow escalation needs a cash_flow trigger")

    # 4. peers on an accounting basis must have a like-for-like own basis
    own_bases = {row.get("accounting_basis") for row in cash["bases"] if row["kind"] == "earnings"}
    for peer in bundle["decision_support"]["valuation"]["peers"]:
        if peer["format"] == "multiple" and peer["basis"] in {"reported", "adjusted"}:
            _require(peer["basis"] in own_bases, (
                f"peer {peer['name']} uses a {peer['basis']} multiple but cash_valuation has no earnings basis with "
                f"accounting_basis={peer['basis']}; compare like with like"))

    # 5. numbers in growth ceiling and opportunity-cost comparators
    research = bundle["research"]
    _require(bool(research["growth_limits"]["ceiling"].get("value_refs")),
             "v3.2 growth_limits.ceiling must bind at least one number (text_template + value_refs)")
    bound = sum(1 for item in research["opportunity_cost"]["comparators"] if item.get("value_refs"))
    _require(bound >= 2, "v3.2 opportunity_cost requires at least two comparators with bound numbers (claim_template + value_refs)")

    return {
        "schema_version": "decision-coherence-v1",
        "status": "PASS",
        "decisive": {**decisive, "per_share_price": decisive_row["per_share_price"]},
        "price_tier_id": price_tier["tier_id"],
        "price_tier_action": price_tier["action"],
        "executable_tier_id": ladder["tiers"][executable_index]["tier_id"] if executable_index is not None else None,
        "executable_position_max": _q(executable_max),
        "blockers": blockers,
        "cash_gate_waiver": waiver or None,
        "escalation": escalation,
        "roic": _roic(spec, bundle, support_raw.get("roic")),
        "current_price": _q(current, "0.01"),
    }

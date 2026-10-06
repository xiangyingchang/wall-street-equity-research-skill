"""v3.2 decision-support layer: the reader content that turns a valuation into instructions.

Everything here is validated fail-closed. Numbers in prose must be bound through
``text_template``/``value_refs`` (same rule as research v2.1); numbers in tables come
from facts or bundle paths and are formatted by the renderer.

Required blocks (spec["decision_support"]):
- valuation: cash_interpretation (claim) + peers[>=3] (Tier 2/3 market data allowed)
- scenario_premises: bull/base/bear 12-24 month operating premises
- financial_history: >=5 fiscal years (or >=3 with an explicit limitation) x >=3 metrics
- normalization: reported / adjusted / normalized bridge
- capex_balance: capex, rnd, balance_sheet, shareholder_return, sbc, shares (+ optional investments)
- ladder_premises: one operating premise per price-ladder tier
- action_triggers: price / valuation / operating / cash_flow / thesis_break
- pre_mortem: failure_path + analysis_error + >=2 early signals
- risk overlay: research.risks.items[] each carries probability / impact / action, >=5 items
- liquidity, review_checklist[>=3]
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from scripts.report_research_v21 import _claim, _json_pointer, _validate_text
from scripts.report_spec_v2 import SpecError

TRIGGER_CATEGORIES = ("price", "valuation", "operating", "cash_flow", "thesis_break")
LEVELS = ("low", "low_medium", "medium", "medium_high", "high", "very_high")
NORMALIZATION_LAYERS = ("reported", "adjusted", "normalized")
CAPEX_BALANCE_REQUIRED = ("capex", "rnd", "balance_sheet", "shareholder_return", "sbc", "shares")
CAPEX_BALANCE_ALLOWED = (*CAPEX_BALANCE_REQUIRED, "ppe", "investments", "other")
PEER_BASES = ("reported", "adjusted", "market")
EXISTING_ACTIONS = ("NONE", "REVIEW", "REDUCE", "SELL")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SpecError(message)


def _decimal(value: Any, label: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SpecError(f"{label} must be a decimal") from exc
    _require(number.is_finite(), f"{label} must be finite")
    return number


def _resolve(spec: dict[str, Any], bundle: dict[str, Any], ref: Any, label: str, unit: Any = None) -> dict[str, Any]:
    reference = str(ref or "").strip()
    if reference.startswith("FACT-"):
        fact = spec.get("facts", {}).get(reference)
        _require(isinstance(fact, dict), f"{label} references undefined fact {reference}")
        value_unit = str(fact.get("unit", "")).strip()
        if unit:
            _require(str(unit).strip() == value_unit, f"{label} unit {unit} mismatches fact unit {value_unit}")
        return {"ref": reference, "value": str(fact["value"]), "unit": value_unit, "period": str(fact.get("period", fact.get("as_of", "")))}
    _require(reference.startswith("BUNDLE:/"), f"{label} requires FACT- or BUNDLE:/ value_ref")
    value = _json_pointer(bundle, reference.removeprefix("BUNDLE:"))
    _require(not isinstance(value, (dict, list)) and value is not None, f"{label} bundle path must resolve to a scalar")
    _require(str(unit or "").strip(), f"{label} bundle value requires explicit unit")
    _decimal(value, label)
    return {"ref": reference, "value": str(value), "unit": str(unit).strip(), "period": ""}


def _peers(spec: dict[str, Any], bundle: dict[str, Any], raw: Any) -> list[dict[str, Any]]:
    _require(isinstance(raw, list) and len(raw) >= 3, "decision_support.valuation.peers requires at least three peers")
    sources = spec.get("sources", {})
    out = []
    for index, item in enumerate(raw):
        label = f"decision_support.valuation.peers[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        name = _validate_text(item.get("name"), f"{label}.name", minimum=2)
        metric = _validate_text(item.get("metric"), f"{label}.metric", minimum=2)
        value = _decimal(item.get("value"), f"{label}.value")
        source_id = str(item.get("source_id", ""))
        _require(source_id in sources, f"{label} references undefined source {source_id}")
        as_of = str(item.get("as_of", "")).strip()
        _require(as_of, f"{label} requires as_of")
        judgement = _validate_text(item.get("judgement"), f"{label}.judgement")
        fmt = str(item.get("format", "multiple"))
        _require(fmt in {"multiple", "percent", "number"}, f"{label}.format must be multiple/percent/number")
        basis = str(item.get("basis", "")).strip()
        _require(basis in PEER_BASES, f"{label}.basis must be one of {', '.join(PEER_BASES)} (accounting basis of the peer metric)")
        out.append({"name": name, "metric": metric, "value": str(value), "format": fmt, "basis": basis, "source_id": source_id, "as_of": as_of, "judgement": judgement})
    return out


def _history(spec: dict[str, Any], bundle: dict[str, Any], raw: Any) -> dict[str, Any]:
    _require(isinstance(raw, dict), "decision_support.financial_history must be an object")
    years = raw.get("years")
    _require(isinstance(years, list) and all(str(y).strip() for y in years), "financial_history requires years[]")
    limitation = str(raw.get("limitation", "")).strip()
    if len(years) < 5:
        _require(len(years) >= 3 and len(limitation) >= 12, "financial_history requires five fiscal years, or at least three with an explicit limitation")
    metrics = raw.get("metrics")
    _require(isinstance(metrics, list) and len(metrics) >= 3, "financial_history requires at least three metrics")
    out_metrics = []
    for index, item in enumerate(metrics):
        label = f"financial_history.metrics[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        name = _validate_text(item.get("label"), f"{label}.label", minimum=2)
        ids = item.get("fact_ids")
        _require(isinstance(ids, list) and len(ids) == len(years), f"{label}.fact_ids must align with years")
        _require(sum(1 for x in ids if x) >= 3, f"{label} requires at least three populated years")
        cells: list[dict[str, Any] | None] = []
        units = set()
        for year_index, fact_id in enumerate(ids):
            if not fact_id:
                cells.append(None)
                continue
            cell = _resolve(spec, bundle, fact_id, f"{label}[{years[year_index]}]")
            units.add(cell["unit"])
            cells.append(cell)
        _require(len(units) == 1, f"{label} facts must share one unit")
        out_metrics.append({"label": name, "unit": units.pop(), "cells": cells})
    interpretation = _claim(raw.get("interpretation"), spec, bundle, "financial_history.interpretation", text_field="text")
    return {"years": [str(y) for y in years], "metrics": out_metrics, "limitation": limitation or None, "interpretation": interpretation}


def _value_rows(spec: dict[str, Any], bundle: dict[str, Any], raw: Any, label: str, key: str, allowed: tuple[str, ...]) -> list[dict[str, Any]]:
    _require(isinstance(raw, list) and raw, f"{label} requires rows")
    out = []
    for index, item in enumerate(raw):
        row_label = f"{label}[{index}]"
        _require(isinstance(item, dict), f"{row_label} must be an object")
        kind = str(item.get(key, "")).strip()
        _require(kind in allowed, f"{row_label}.{key} must be one of {', '.join(allowed)}")
        name = _validate_text(item.get("label"), f"{row_label}.label", minimum=2)
        values = []
        for value_index, ref in enumerate(item.get("value_refs") or []):
            if isinstance(ref, dict):
                values.append({**_resolve(spec, bundle, ref.get("ref"), f"{row_label}.value_refs[{value_index}]", ref.get("unit")), "caption": str(ref.get("caption", "")).strip()})
            else:
                values.append({**_resolve(spec, bundle, ref, f"{row_label}.value_refs[{value_index}]"), "caption": ""})
        _require(values, f"{row_label} requires at least one value_ref")
        note = _claim(item.get("note"), spec, bundle, f"{row_label}.note", text_field="text")
        out.append({key: kind, "label": name, "values": values, "note": note})
    return out


def _risk_overlay(spec: dict[str, Any], bundle: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = spec.get("research", {}).get("risks", {}).get("items", [])
    _require(isinstance(raw_items, list) and len(raw_items) >= 5, "v3.2 risks require at least five ranked items")
    normalized = {item["rank"]: item for item in bundle["research"]["risks"]["items"]}
    out = []
    for index, raw in enumerate(raw_items):
        label = f"risks.items[{index}]"
        rank = int(raw.get("rank", index + 1))
        probability = str(raw.get("probability", "")).lower()
        impact = str(raw.get("impact", "")).lower()
        _require(probability in LEVELS, f"{label} requires probability in {', '.join(LEVELS)}")
        _require(impact in LEVELS, f"{label} requires impact in {', '.join(LEVELS)}")
        action = _validate_text(raw.get("action"), f"{label}.action")
        out.append({**normalized[rank], "probability": probability, "impact": impact, "action": action})
    return sorted(out, key=lambda x: x["rank"])


def compile_decision_support(spec: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    raw = spec.get("decision_support")
    _require(isinstance(raw, dict), "v3.2 requires decision_support")
    cash = bundle.get("derived", {}).get("cash_valuation")
    ladder = bundle.get("price_ladder")
    _require(isinstance(cash, dict), "v3.2 requires report.cash_valuation")
    _require(isinstance(ladder, dict), "v3.2 requires decision_policy.price_ladder")

    valuation = raw.get("valuation")
    _require(isinstance(valuation, dict), "decision_support.valuation must be an object")
    out: dict[str, Any] = {
        "valuation": {
            "cash_interpretation": _claim(valuation.get("cash_interpretation"), spec, bundle, "decision_support.valuation.cash_interpretation", text_field="text"),
            "peers": _peers(spec, bundle, valuation.get("peers")),
            "peer_interpretation": _claim(valuation.get("peer_interpretation"), spec, bundle, "decision_support.valuation.peer_interpretation", text_field="text"),
        }
    }

    premises = raw.get("scenario_premises")
    _require(isinstance(premises, dict), "decision_support.scenario_premises must be an object")
    out["scenario_premises"] = {
        name: _claim(premises.get(name), spec, bundle, f"decision_support.scenario_premises.{name}", text_field="text")
        for name in ("bull", "base", "bear")
    }

    out["financial_history"] = _history(spec, bundle, raw.get("financial_history"))

    normalization = _value_rows(spec, bundle, raw.get("normalization"), "decision_support.normalization", "layer", NORMALIZATION_LAYERS)
    _require({row["layer"] for row in normalization} == set(NORMALIZATION_LAYERS), "normalization must cover reported / adjusted / normalized")
    raw_rows = raw.get("normalization")
    other_refs = {v["ref"] for row in normalization if row["layer"] != "normalized" for v in row["values"]}
    for index, row in enumerate(normalization):
        if row["layer"] != "normalized":
            continue
        method = str(raw_rows[index].get("method", "")).strip()
        _require(len(method) >= 12, f"decision_support.normalization[{index}] normalized row requires method (how it differs from reported/adjusted)")
        own_refs = {v["ref"] for v in row["values"]}
        _require(not own_refs <= other_refs, f"decision_support.normalization[{index}] normalized row only repeats reported/adjusted values; it is not normalized")
        row["method"] = method
    out["normalization"] = normalization

    capex = _value_rows(spec, bundle, raw.get("capex_balance"), "decision_support.capex_balance", "category", CAPEX_BALANCE_ALLOWED)
    missing = set(CAPEX_BALANCE_REQUIRED) - {row["category"] for row in capex}
    _require(not missing, f"capex_balance missing categories: {', '.join(sorted(missing))}")
    out["capex_balance"] = capex

    ladder_premises = raw.get("ladder_premises")
    _require(isinstance(ladder_premises, dict), "decision_support.ladder_premises must be an object")
    tier_ids = [tier["tier_id"] for tier in ladder["tiers"]]
    _require(set(ladder_premises) == set(tier_ids), "ladder_premises must cover exactly every price-ladder tier")
    out["ladder_premises"] = {
        tier_id: _claim(ladder_premises[tier_id], spec, bundle, f"decision_support.ladder_premises.{tier_id}", text_field="text")
        for tier_id in tier_ids
    }

    triggers = raw.get("action_triggers")
    _require(isinstance(triggers, list) and triggers, "decision_support.action_triggers must be a non-empty list")
    normalized_triggers = []
    for index, item in enumerate(triggers):
        label = f"decision_support.action_triggers[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        category = str(item.get("category", ""))
        _require(category in TRIGGER_CATEGORIES, f"{label}.category must be one of {', '.join(TRIGGER_CATEGORIES)}")
        condition = _claim(item.get("condition"), spec, bundle, f"{label}.condition", text_field="text")
        action = _validate_text(item.get("action"), f"{label}.action", minimum=4)
        existing_action = str(item.get("existing_action", "")).upper()
        _require(existing_action in EXISTING_ACTIONS, f"{label}.existing_action must be one of {', '.join(EXISTING_ACTIONS)} (what the trigger means for an existing position)")
        normalized_triggers.append({"category": category, "condition": condition, "action": action, "existing_action": existing_action})
    missing = set(TRIGGER_CATEGORIES) - {x["category"] for x in normalized_triggers}
    _require(not missing, f"action_triggers missing categories: {', '.join(sorted(missing))}")
    out["action_triggers"] = sorted(normalized_triggers, key=lambda x: TRIGGER_CATEGORIES.index(x["category"]))

    pre_mortem = raw.get("pre_mortem")
    _require(isinstance(pre_mortem, dict), "decision_support.pre_mortem must be an object")
    signals = pre_mortem.get("early_signals")
    _require(isinstance(signals, list) and len(signals) >= 2, "pre_mortem requires at least two early_signals")
    out["pre_mortem"] = {
        "failure_path": _claim(pre_mortem.get("failure_path"), spec, bundle, "pre_mortem.failure_path", text_field="text"),
        "analysis_error": _claim(pre_mortem.get("analysis_error"), spec, bundle, "pre_mortem.analysis_error", text_field="text"),
        "early_signals": [_validate_text(x, f"pre_mortem.early_signals[{i}]") for i, x in enumerate(signals)],
    }

    out["risks"] = _risk_overlay(spec, bundle)
    out["liquidity"] = _claim(raw.get("liquidity"), spec, bundle, "decision_support.liquidity", text_field="text")
    checklist = raw.get("review_checklist")
    _require(isinstance(checklist, list) and len(checklist) >= 3, "decision_support.review_checklist requires at least three items")
    out["review_checklist"] = [_validate_text(x, f"review_checklist[{i}]") for i, x in enumerate(checklist)]
    out["quality"] = {
        "status": "PASS",
        "peers": len(out["valuation"]["peers"]),
        "history_years": len(out["financial_history"]["years"]),
        "risks": len(out["risks"]),
        "ladder_tiers": len(tier_ids),
        "trigger_categories": len({x["category"] for x in out["action_triggers"]}),
    }
    return out

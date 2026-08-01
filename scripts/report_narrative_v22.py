from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from scripts.report_research_v21 import _claim, _validate_refs, _validate_text
from scripts.report_spec_v2 import SpecError

THEME_CATEGORIES = {"business", "capital", "valuation"}
CASE_NAMES = ("bull_case", "base_case", "bear_case")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SpecError(message)


def _tokens(text: str) -> set[str]:
    return {x.casefold() for x in re.findall(r"[A-Za-z][A-Za-z0-9_-]+|[\u4e00-\u9fff]{2,}", text)}


def _entity_hits(text: str, entities: list[str]) -> list[str]:
    lowered = text.casefold()
    return [entity for entity in entities if entity.casefold() in lowered]


def _theme_overlap(a: str, b: str) -> float:
    left, right = _tokens(a), _tokens(b)
    return len(left & right) / max(1, min(len(left), len(right)))


def _normalize_theme(raw: Any, spec: dict[str, Any], bundle: dict[str, Any], index: int, entities: list[str]) -> dict[str, Any]:
    label = f"narrative.themes[{index}]"
    _require(isinstance(raw, dict), f"{label} must be an object")
    theme_id = str(raw.get("id", ""))
    _require(theme_id.startswith("THEME-"), f"{label}.id must use THEME-* format")
    category = str(raw.get("category", "")).lower()
    _require(category in THEME_CATEGORIES, f"{label}.category must be one of {sorted(THEME_CATEGORIES)}")
    title = _validate_text(raw.get("title"), f"{label}.title")
    thesis = _claim(raw.get("thesis"), spec, bundle, f"{label}.thesis", text_field="text")
    mechanism_raw = raw.get("mechanism")
    _require(isinstance(mechanism_raw, list) and len(mechanism_raw) >= 2, f"{label} requires at least two mechanism claims")
    mechanism = [_claim(item, spec, bundle, f"{label}.mechanism[{i}]") for i, item in enumerate(mechanism_raw)]
    counter_case = _claim(raw.get("counter_case"), spec, bundle, f"{label}.counter_case", text_field="text")
    implication = _validate_text(raw.get("investment_implication"), f"{label}.investment_implication")
    signals = raw.get("validation_signals")
    _require(isinstance(signals, list) and len(signals) >= 2, f"{label} requires at least two validation signals")
    normalized_signals = [_validate_text(x, f"{label}.validation_signals[{i}]") for i, x in enumerate(signals)]
    all_refs = [*thesis["evidence_refs"], *counter_case["evidence_refs"]]
    for item in mechanism:
        all_refs.extend(item["evidence_refs"])
    _require(any(x["role"] == "counter_evidence" for x in all_refs), f"{label} requires counter_evidence role")
    body = " ".join([title, thesis["text"], implication, *(x["claim"] for x in mechanism)])
    hits = _entity_hits(body, entities)
    _require(hits, f"{label} lacks company-specific entity")
    return {
        "id": theme_id,
        "category": category,
        "title": title,
        "thesis": thesis,
        "mechanism": mechanism,
        "counter_case": counter_case,
        "investment_implication": implication,
        "validation_signals": normalized_signals,
        "entity_hits": hits,
    }


def _normalize_case(raw: Any, spec: dict[str, Any], bundle: dict[str, Any], label: str) -> dict[str, Any]:
    _require(isinstance(raw, dict), f"{label} must be an object")
    thesis = _claim(raw.get("thesis"), spec, bundle, f"{label}.thesis", text_field="text")
    path = raw.get("value_ref")
    _require(isinstance(path, dict), f"{label}.value_ref must be an object")
    _require(str(path.get("path", "")).startswith("/"), f"{label}.value_ref must use JSON Pointer")
    _require(path.get("format") in {"money", "percent", "multiple", "number", "integer", "text"}, f"{label}.value_ref invalid format")
    # Bind the case value through the existing claim engine without allowing a hidden number.
    probe = {
        "text_template": "Case anchor: {anchor}",
        "value_refs": {"anchor": path},
        "evidence_refs": raw.get("evidence_refs", thesis["evidence_refs"]),
        "confidence": raw.get("confidence", thesis["confidence"]),
    }
    bound = _claim(probe, spec, bundle, f"{label}.value_binding", text_field="text")
    path_to_win = _validate_text(raw.get("path_to_win"), f"{label}.path_to_win")
    failure_signal = _validate_text(raw.get("failure_signal"), f"{label}.failure_signal")
    return {
        "thesis": thesis,
        "value_binding": bound,
        "path_to_win": path_to_win,
        "failure_signal": failure_signal,
    }


def compile_narrative_v22(spec: dict[str, Any], bundle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    entities = spec.get("company_entities")
    _require(isinstance(entities, list) and len(entities) >= 4, "company_entities requires at least four entries")
    entities = [str(x).strip() for x in entities if str(x).strip()]
    narrative = spec.get("narrative")
    _require(isinstance(narrative, dict), "v2.2 narrative must be an object")
    themes_raw = narrative.get("themes")
    _require(isinstance(themes_raw, list) and 3 <= len(themes_raw) <= 5, "narrative requires 3-5 themes")
    themes = [_normalize_theme(x, spec, bundle, i, entities) for i, x in enumerate(themes_raw)]
    ids = [x["id"] for x in themes]
    _require(len(ids) == len(set(ids)), "theme IDs must be unique")
    _require({x["category"] for x in themes} == THEME_CATEGORIES, "themes must cover business, capital, and valuation")
    for i, left in enumerate(themes):
        for right in themes[i + 1:]:
            _require(_theme_overlap(left["title"], right["title"]) < 0.75, f"themes are too repetitive: {left['id']} / {right['id']}")

    debate_raw = narrative.get("debate")
    _require(isinstance(debate_raw, dict), "narrative.debate must be an object")
    debate = {name: _normalize_case(debate_raw.get(name), spec, bundle, f"narrative.debate.{name}") for name in CASE_NAMES}
    debate["key_disagreement"] = _validate_text(debate_raw.get("key_disagreement"), "narrative.debate.key_disagreement")

    causal = narrative.get("financial_causal_bridge")
    _require(isinstance(causal, dict), "narrative.financial_causal_bridge must be an object")
    causal_out = {
        key: _claim(causal.get(key), spec, bundle, f"narrative.financial_causal_bridge.{key}", text_field="text")
        for key in ("operating_change", "cost_driver", "cash_flow_effect", "valuation_effect")
    }

    mirror_raw = narrative.get("mirror_test")
    _require(isinstance(mirror_raw, list) and len(mirror_raw) == 5, "mirror_test must contain exactly five statements")
    mirror = [_claim(item, spec, bundle, f"narrative.mirror_test[{i}]", text_field="text") for i, item in enumerate(mirror_raw)]

    counter_count = sum(
        1 for theme in themes for ref in [*theme["thesis"]["evidence_refs"], *theme["counter_case"]["evidence_refs"], *(r for m in theme["mechanism"] for r in m["evidence_refs"])]
        if ref["role"] == "counter_evidence"
    )
    bound_values = sum(len(x["thesis"].get("value_refs", {})) for x in themes)
    bound_values += sum(len(x["value_binding"].get("value_refs", {})) for x in debate.values() if isinstance(x, dict) and "value_binding" in x)
    quality = {
        "status": "PASS",
        "checks": {
            "themes_complete": {"status": "PASS", "count": len(themes)},
            "causal_chains_complete": {"status": "PASS", "steps": len(causal_out)},
            "adversarial_debate_complete": {"status": "PASS", "cases": 3},
            "company_specificity": {"status": "PASS", "entities": len({h for t in themes for h in t["entity_hits"]})},
            "counter_evidence_coverage": {"status": "PASS", "refs": counter_count},
            "mirror_test_complete": {"status": "PASS", "statements": len(mirror)},
            "narrative_redundancy": {"status": "PASS"},
            "numeric_argument_density": {"status": "PASS", "bound_values": bound_values},
        },
    }
    return {
        "themes": themes,
        "debate": debate,
        "financial_causal_bridge": causal_out,
        "mirror_test": mirror,
        "company_entities": entities,
    }, quality


def attach_narrative_v22(spec: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(bundle)
    narrative, quality = compile_narrative_v22(spec, out)
    out["narrative"] = narrative
    out["narrative_quality"] = quality
    return out

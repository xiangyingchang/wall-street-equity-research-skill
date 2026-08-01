from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from scripts.report_spec_v2 import SpecError, compile_spec, sha256

MODULES = (
    "overview",
    "financial_autopsy",
    "moat",
    "valuation",
    "risks",
    "growth_limits",
    "opportunity_cost",
    "positioning",
    "final_verdict",
)
CONFIDENCE = {"low", "medium", "high"}
SOURCE_FIELDS = {"title", "publisher", "date", "tier", "document_type", "locator", "scope"}
NUMERIC_PATTERN = re.compile(r"(?:[$€¥£]\s*\d|\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*[xX倍]|\b\d{3,}(?:\.\d+)?\b)")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SpecError(message)


def _walk_path(root: Any, path: str) -> Any:
    current = root
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise SpecError(f"undefined bundle path: {path}")
    return current


def _validate_text(text: Any, label: str) -> str:
    value = str(text or "").strip()
    _require(len(value) >= 12, f"{label} is too thin")
    _require(not NUMERIC_PATTERN.search(value), f"{label} contains unbound numeric content")
    return value


def _validate_refs(refs: Any, spec: dict[str, Any], bundle: dict[str, Any], label: str) -> list[str]:
    _require(isinstance(refs, list) and refs, f"{label} requires evidence_refs")
    result: list[str] = []
    sources = spec["sources"]
    facts = spec["facts"]
    for raw in refs:
        ref = str(raw)
        if ref.startswith("SRC-"):
            _require(ref in sources, f"{label} references undefined source {ref}")
        elif ref.startswith("FACT-"):
            _require(ref in facts, f"{label} references undefined fact {ref}")
        elif ref.startswith("BUNDLE:"):
            _walk_path(bundle, ref.removeprefix("BUNDLE:"))
        else:
            raise SpecError(f"{label} uses unsupported evidence ref {ref}")
        result.append(ref)
    return result


def _claim(item: Any, spec: dict[str, Any], bundle: dict[str, Any], label: str, *, text_field: str = "claim") -> dict[str, Any]:
    _require(isinstance(item, dict), f"{label} must be an object")
    text = _validate_text(item.get(text_field), f"{label}.{text_field}")
    refs = _validate_refs(item.get("evidence_refs"), spec, bundle, label)
    confidence = str(item.get("confidence", "")).lower()
    _require(confidence in CONFIDENCE, f"{label} invalid confidence")
    implication = _validate_text(item.get("implication"), f"{label}.implication") if "implication" in item else ""
    result = {text_field: text, "evidence_refs": refs, "confidence": confidence}
    if implication:
        result["implication"] = implication
    if "counter_evidence" in item:
        result["counter_evidence"] = _validate_text(item["counter_evidence"], f"{label}.counter_evidence")
    return result


def _validate_sources_and_facts(spec: dict[str, Any]) -> dict[str, Any]:
    sources = spec.get("sources")
    _require(isinstance(sources, dict) and sources, "v2.1 sources must be a non-empty object")
    normalized: dict[str, Any] = {}
    for source_id, source in sources.items():
        _require(str(source_id).startswith("SRC-"), f"invalid source ID: {source_id}")
        _require(isinstance(source, dict), f"source {source_id} must be an object")
        missing = SOURCE_FIELDS - set(source)
        _require(not missing, f"source {source_id} missing {', '.join(sorted(missing))}")
        _require(str(source["tier"]) in {"1", "2", "3", "Tier 1", "Tier 2", "Tier 3"}, f"source {source_id} invalid tier")
        _require(isinstance(source["scope"], list) and source["scope"], f"source {source_id} requires scope")
        normalized[source_id] = deepcopy(source)
    facts = spec.get("facts", {})
    for fact_id, fact in facts.items():
        source_ids = fact.get("source_ids")
        _require(isinstance(source_ids, list) and source_ids, f"fact {fact_id} requires source_ids")
        for source_id in source_ids:
            _require(source_id in sources, f"fact {fact_id} references undefined source {source_id}")
        if fact_id != spec.get("report", {}).get("current_price_fact_id"):
            tiers = {str(sources[source_id]["tier"]).replace("Tier ", "") for source_id in source_ids}
            _require("1" in tiers, f"critical fact {fact_id} requires a Tier 1 source")
    return normalized


def _validate_research(spec: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    research = spec.get("research")
    _require(isinstance(research, dict), "v2.1 research must be an object")
    missing = set(MODULES) - set(research)
    _require(not missing, f"research missing modules: {', '.join(sorted(missing))}")
    out: dict[str, Any] = {}

    overview = research["overview"]
    _require(isinstance(overview, dict), "overview must be an object")
    key_forces = overview.get("key_forces")
    _require(isinstance(key_forces, list) and len(key_forces) >= 3, "overview requires at least three key forces")
    out["overview"] = {
        "thesis": _claim(overview.get("thesis"), spec, bundle, "overview.thesis", text_field="text"),
        "key_forces": [_claim(x, spec, bundle, f"overview.key_forces[{i}]") for i, x in enumerate(key_forces)],
        "variant_view": _claim(overview.get("variant_view"), spec, bundle, "overview.variant_view", text_field="text"),
    }

    financial = research["financial_autopsy"]
    _require(isinstance(financial, dict), "financial_autopsy must be an object")
    out["financial_autopsy"] = {
        key: _claim(financial.get(key), spec, bundle, f"financial_autopsy.{key}", text_field="text")
        for key in ("revenue", "margin", "cash_flow", "one_offs")
    }

    moat = research["moat"]
    dims = moat.get("dimensions") if isinstance(moat, dict) else None
    _require(isinstance(dims, list) and len(dims) >= 4, "moat requires at least four dimensions")
    normalized_dims = []
    for i, item in enumerate(dims):
        _require(isinstance(item, dict), f"moat.dimensions[{i}] must be an object")
        score = int(item.get("score", 0))
        _require(1 <= score <= 5, f"moat.dimensions[{i}] score must be 1-5")
        normalized = _claim(item, spec, bundle, f"moat.dimensions[{i}]", text_field="claim")
        normalized.update({"name": _validate_text(item.get("name"), f"moat.dimensions[{i}].name"), "score": score})
        _require("counter_evidence" in normalized, f"moat.dimensions[{i}] requires counter_evidence")
        normalized_dims.append(normalized)
    trajectory = str(moat.get("trajectory", "")).lower()
    _require(trajectory in {"strengthening", "stable", "weakening"}, "moat trajectory invalid")
    out["moat"] = {"dimensions": normalized_dims, "trajectory": trajectory}

    valuation = research["valuation"]
    _require(isinstance(valuation, dict), "valuation must be an object")
    out["valuation"] = {
        key: _claim(valuation.get(key), spec, bundle, f"valuation.{key}", text_field="text")
        for key in ("base_case", "reverse_expectations", "payback_interpretation", "critical_assumption")
    }

    risks = research["risks"]
    risk_items = risks.get("items") if isinstance(risks, dict) else None
    _require(isinstance(risk_items, list) and len(risk_items) >= 3, "risks requires at least three items")
    normalized_risks = []
    for i, item in enumerate(risk_items):
        _require(isinstance(item, dict), f"risks.items[{i}] must be an object")
        normalized_risks.append({
            "rank": int(item.get("rank", i + 1)),
            "risk": _validate_text(item.get("risk"), f"risks.items[{i}].risk"),
            "mechanism": _validate_text(item.get("mechanism"), f"risks.items[{i}].mechanism"),
            "leading_indicators": [_validate_text(x, f"risks.items[{i}].leading_indicators") for x in item.get("leading_indicators", [])],
            "trigger": _validate_text(item.get("trigger"), f"risks.items[{i}].trigger"),
            "mitigant": _validate_text(item.get("mitigant"), f"risks.items[{i}].mitigant"),
            "evidence_refs": _validate_refs(item.get("evidence_refs"), spec, bundle, f"risks.items[{i}]"),
            "confidence": str(item.get("confidence", "medium")).lower(),
        })
    _require(all(x["leading_indicators"] for x in normalized_risks), "every risk requires leading indicators")
    out["risks"] = {"items": sorted(normalized_risks, key=lambda x: x["rank"])}

    growth = research["growth_limits"]
    _require(isinstance(growth, dict), "growth_limits must be an object")
    constraints = growth.get("constraints")
    _require(isinstance(constraints, list) and len(constraints) >= 2, "growth_limits requires at least two constraints")
    out["growth_limits"] = {
        "growth_engine": _claim(growth.get("growth_engine"), spec, bundle, "growth_limits.growth_engine", text_field="text"),
        "constraints": [_claim(x, spec, bundle, f"growth_limits.constraints[{i}]") for i, x in enumerate(constraints)],
        "ceiling": _claim(growth.get("ceiling"), spec, bundle, "growth_limits.ceiling", text_field="text"),
    }

    opportunity = research["opportunity_cost"]
    comparators = opportunity.get("comparators") if isinstance(opportunity, dict) else None
    _require(isinstance(comparators, list) and len(comparators) >= 3, "opportunity_cost requires at least three comparators")
    out["opportunity_cost"] = {
        "interpretation": _claim(opportunity.get("interpretation"), spec, bundle, "opportunity_cost.interpretation", text_field="text"),
        "comparators": [_claim(x, spec, bundle, f"opportunity_cost.comparators[{i}]") for i, x in enumerate(comparators)],
    }

    positioning = research["positioning"]
    _require(isinstance(positioning, dict), "positioning must be an object")
    out["positioning"] = {
        key: _claim(positioning.get(key), spec, bundle, f"positioning.{key}", text_field="text")
        for key in ("new_money", "existing_position", "portfolio_constraints", "execution")
    }

    final = research["final_verdict"]
    _require(isinstance(final, dict), "final_verdict must be an object")
    out["final_verdict"] = {
        key: _claim(final.get(key), spec, bundle, f"final_verdict.{key}", text_field="text")
        for key in ("summary", "hold_equals_buy", "opportunity_cost", "payback", "confidence_boundary", "falsification")
    }
    return out


def compile_spec_v21(spec: dict[str, Any]) -> dict[str, Any]:
    _require(spec.get("schema_version") == "report-spec-v2.1", "schema_version must be report-spec-v2.1")
    normalized_sources = _validate_sources_and_facts(spec)
    legacy = deepcopy(spec)
    legacy["schema_version"] = "report-spec-v2"
    legacy["sources"] = []
    legacy["narrative"] = {}
    bundle = compile_spec(legacy)
    bundle["schema_version"] = "report-bundle-v2.1"
    bundle["compiler_version"] = "2.1.0"
    bundle["source_registry"] = normalized_sources
    bundle["research"] = _validate_research(spec, bundle)
    bundle["spec_hash"] = sha256(spec)
    unhashed = deepcopy(bundle)
    unhashed.pop("bundle_hash", None)
    bundle["bundle_hash"] = sha256(unhashed)
    return bundle

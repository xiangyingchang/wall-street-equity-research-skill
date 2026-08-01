from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from scripts.report_research_v21 import MODULES, _claim, _require, _validate_refs, _validate_text

THEME_ID = re.compile(r"^THEME-[A-Z0-9][A-Z0-9_-]*$")
NODE_ID = re.compile(r"^(?:OBS|ARG|DRV)-[A-Z0-9][A-Z0-9_-]*$")
GENERIC_TITLES = {"business model", "financial performance", "valuation", "risk", "growth", "商业模式", "财务表现", "估值", "风险", "增长", "护城河"}
IMPORTANCE = {"high", "medium", "low"}
DIRECTIONS = {"positive", "negative", "mixed"}


def _id(raw: Any, label: str, pattern: re.Pattern[str]) -> str:
    value = str(raw or "").strip().upper()
    _require(bool(pattern.fullmatch(value)), f"{label} invalid ID: {value}")
    return value


def _short_text(raw: Any, label: str, minimum: int = 8) -> str:
    value = str(raw or "").strip()
    _require(len(value) >= minimum, f"{label} is too thin")
    return value


def _has_role(item: dict[str, Any], role: str) -> bool:
    return any(x.get("role") == role for x in item.get("evidence_refs", []))


def _node(raw: Any, spec: dict[str, Any], bundle: dict[str, Any], label: str, *, field: str = "text") -> dict[str, Any]:
    _require(isinstance(raw, dict), f"{label} must be object")
    prepared = deepcopy(raw)
    implication = prepared.pop("implication", None)
    item = _claim(prepared, spec, bundle, label, text_field=field)
    if implication is not None:
        item["implication"] = _short_text(implication, f"{label}.implication")
    return item


def _resolve_assumption_path(bundle: dict[str, Any], raw_path: str, label: str) -> str:
    _require(raw_path.startswith("/assumptions/"), f"{label} requires an assumption JSON Pointer")
    parts = [part for part in raw_path.split("/") if part]
    canonical_shape = len(parts) == 3 and parts[0] == "assumptions" and parts[-1] == "value"
    spec_shape = len(parts) == 4 and parts[:2] == ["assumptions", "scenario"] and parts[-1] == "value"
    _require(canonical_shape or spec_shape, f"{label} must use /assumptions/<ASM-ID>/value or /assumptions/scenario/<ASM-ID>/value")
    assumption_id = parts[-2]
    assumptions = bundle.get("assumptions", {})
    aliases = {
        "ASM-BASE-EPS-CAGR": "ASM-BASE-CAGR",
        "ASM-BEAR-EPS-CAGR": "ASM-BEAR-CAGR",
        "ASM-BULL-EPS-CAGR": "ASM-BULL-CAGR",
    }
    canonical_id = assumption_id if assumption_id in assumptions else aliases.get(assumption_id, assumption_id)
    _require(canonical_id in assumptions, f"{label} references undefined assumption {assumption_id}")
    _require("value" in assumptions[canonical_id], f"{label} assumption {canonical_id} has no scalar value")
    return f"/assumptions/{canonical_id}/value"


def compile_research_graph(spec: dict[str, Any], bundle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    graph = spec.get("research_graph")
    _require(isinstance(graph, dict), "v3 requires research_graph")
    themes = graph.get("themes")
    _require(isinstance(themes, list) and 3 <= len(themes) <= 5, "research_graph requires 3-5 themes")

    normalized_themes: list[dict[str, Any]] = []
    theme_ids: set[str] = set()
    observation_ids: set[str] = set()
    linked_modules: set[str] = set()

    for index, raw in enumerate(themes):
        label = f"research_graph.themes[{index}]"
        _require(isinstance(raw, dict), f"{label} must be object")
        theme_id = _id(raw.get("theme_id"), f"{label}.theme_id", THEME_ID)
        _require(theme_id not in theme_ids, f"duplicate theme ID: {theme_id}")
        theme_ids.add(theme_id)
        title = _validate_text(raw.get("title"), f"{label}.title")
        _require(title.casefold() not in GENERIC_TITLES, f"{label}.title is too generic")
        observations = raw.get("observations")
        _require(isinstance(observations, list) and len(observations) >= 2, f"{label} requires at least two observations")
        normalized_observations = []
        for obs_index, observation in enumerate(observations):
            obs_label = f"{label}.observations[{obs_index}]"
            _require(isinstance(observation, dict), f"{obs_label} must be object")
            obs_id = _id(observation.get("observation_id"), f"{obs_label}.observation_id", NODE_ID)
            _require(obs_id.startswith("OBS-") and obs_id not in observation_ids, f"duplicate or invalid observation ID: {obs_id}")
            observation_ids.add(obs_id)
            item = _node(observation, spec, bundle, obs_label)
            item["observation_id"] = obs_id
            normalized_observations.append(item)

        hypothesis = _node(raw.get("hypothesis"), spec, bundle, f"{label}.hypothesis")
        challenge = _node(raw.get("challenge"), spec, bundle, f"{label}.challenge")
        resolution = _node(raw.get("resolution"), spec, bundle, f"{label}.resolution")
        decision_impact = _node(raw.get("decision_impact"), spec, bundle, f"{label}.decision_impact")
        falsification = _node(raw.get("falsification"), spec, bundle, f"{label}.falsification")
        _require(_has_role(challenge, "counter_evidence"), f"{label}.challenge requires counter_evidence")
        _require(_has_role(resolution, "supports") and _has_role(resolution, "counter_evidence"), f"{label}.resolution must reconcile supports and counter_evidence")
        _require(any(x.get("ref", "").startswith("BUNDLE:") for x in decision_impact["evidence_refs"]), f"{label}.decision_impact requires Bundle evidence")
        module_links = [str(x) for x in raw.get("module_links", [])]
        _require(len(set(module_links)) >= 2, f"{label} requires at least two module_links")
        _require(set(module_links) <= set(MODULES), f"{label} contains unknown module link")
        linked_modules.update(module_links)
        normalized_themes.append({
            "theme_id": theme_id,
            "title": title,
            "core_question": _validate_text(raw.get("core_question"), f"{label}.core_question"),
            "observations": normalized_observations,
            "hypothesis": hypothesis,
            "challenge": challenge,
            "resolution": resolution,
            "decision_impact": decision_impact,
            "falsification": falsification,
            "module_links": module_links,
        })

    missing_modules = set(MODULES) - linked_modules
    _require(not missing_modules, f"research_graph themes do not cover modules: {', '.join(sorted(missing_modules))}")

    debate = graph.get("debate")
    _require(isinstance(debate, dict), "research_graph.debate is required")
    normalized_sides: dict[str, list[dict[str, Any]]] = {}
    side_ids: dict[str, set[str]] = {"bull": set(), "bear": set()}
    global_argument_ids: set[str] = set()
    for side in ("bull", "bear"):
        arguments = debate.get(side)
        _require(isinstance(arguments, list) and len(arguments) >= 3, f"debate.{side} requires at least three arguments")
        normalized = []
        for index, raw in enumerate(arguments):
            label = f"research_graph.debate.{side}[{index}]"
            _require(isinstance(raw, dict), f"{label} must be object")
            arg_id = _id(raw.get("argument_id"), f"{label}.argument_id", NODE_ID)
            _require(arg_id.startswith("ARG-") and arg_id not in global_argument_ids, f"duplicate or invalid argument ID: {arg_id}")
            global_argument_ids.add(arg_id)
            side_ids[side].add(arg_id)
            item = _node(raw, spec, bundle, label, field="claim")
            item["argument_id"] = arg_id
            normalized.append(item)
        normalized_sides[side] = normalized

    raw_adjudication = debate.get("adjudication")
    _require(isinstance(raw_adjudication, dict), "debate.adjudication is required")
    adjudication = _node(raw_adjudication, spec, bundle, "research_graph.debate.adjudication")
    accepted = {str(x).upper() for x in raw_adjudication.get("accepted_argument_ids", [])}
    discounted = {str(x).upper() for x in raw_adjudication.get("discounted_argument_ids", [])}
    _require(accepted and discounted and not (accepted & discounted), "adjudication IDs must be non-empty and disjoint")
    _require((accepted | discounted) <= global_argument_ids, "adjudication references undefined argument IDs")
    auto_discounted = global_argument_ids - accepted - discounted
    discounted.update(auto_discounted)
    _require(accepted & side_ids["bull"] and accepted & side_ids["bear"], "adjudication must accept points from both sides")
    adjudication.update({
        "accepted_argument_ids": sorted(accepted),
        "discounted_argument_ids": sorted(discounted),
        "auto_discounted_argument_ids": sorted(auto_discounted),
        "remaining_uncertainty": _validate_text(raw_adjudication.get("remaining_uncertainty"), "debate.adjudication.remaining_uncertainty"),
    })

    sensitivity = graph.get("sensitivity")
    drivers = sensitivity.get("drivers") if isinstance(sensitivity, dict) else None
    _require(isinstance(drivers, list) and len(drivers) >= 3, "sensitivity requires at least three drivers")
    normalized_drivers = []
    driver_ids: set[str] = set()
    high_count = 0
    for index, raw in enumerate(drivers):
        label = f"research_graph.sensitivity.drivers[{index}]"
        _require(isinstance(raw, dict), f"{label} must be object")
        driver_id = _id(raw.get("driver_id"), f"{label}.driver_id", NODE_ID)
        _require(driver_id.startswith("DRV-") and driver_id not in driver_ids, f"duplicate or invalid driver ID: {driver_id}")
        driver_ids.add(driver_id)
        importance = str(raw.get("importance", "")).lower()
        direction = str(raw.get("direction", "")).lower()
        _require(importance in IMPORTANCE and direction in DIRECTIONS, f"{label} invalid importance or direction")
        high_count += int(importance == "high")
        raw_assumption_path = str(raw.get("base_assumption_path", "")).strip()
        assumption_path = _resolve_assumption_path(bundle, raw_assumption_path, label)
        normalized_drivers.append({
            "driver_id": driver_id,
            "variable": _short_text(raw.get("variable"), f"{label}.variable"),
            "base_assumption_path": assumption_path,
            "declared_assumption_path": raw_assumption_path,
            "direction": direction,
            "importance": importance,
            "mechanism": _validate_text(raw.get("mechanism"), f"{label}.mechanism"),
            "upside_case": _validate_text(raw.get("upside_case"), f"{label}.upside_case"),
            "downside_case": _validate_text(raw.get("downside_case"), f"{label}.downside_case"),
            "decision_consequence": _validate_text(raw.get("decision_consequence"), f"{label}.decision_consequence"),
            "evidence_refs": _validate_refs(raw.get("evidence_refs"), spec, bundle, label),
        })
    _require(high_count >= 1, "sensitivity requires at least one high-importance driver")

    graph_out = {
        "themes": normalized_themes,
        "debate": {"bull": normalized_sides["bull"], "bear": normalized_sides["bear"], "adjudication": adjudication},
        "sensitivity": {"drivers": normalized_drivers},
    }
    quality = {
        "status": "PASS",
        "themes": len(normalized_themes),
        "observations": sum(len(x["observations"]) for x in normalized_themes),
        "bull_arguments": len(normalized_sides["bull"]),
        "bear_arguments": len(normalized_sides["bear"]),
        "classified_arguments": len(accepted | discounted),
        "auto_discounted_arguments": sorted(auto_discounted),
        "sensitivity_drivers": len(normalized_drivers),
        "high_importance_drivers": high_count,
        "module_links": sorted(linked_modules),
    }
    return deepcopy(graph_out), quality

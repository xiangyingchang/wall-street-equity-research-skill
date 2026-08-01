from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from scripts.report_research_v21 import _claim, _require, _validate_refs, _validate_text
from scripts.report_spec_v2 import SpecError

THEME_ID = re.compile(r"^THEME-[A-Z0-9][A-Z0-9_-]*$")
NODE_ID = re.compile(r"^(?:OBS|ARG|DRV)-[A-Z0-9][A-Z0-9_-]*$")
GENERIC_TITLES = {
    "business model", "financial performance", "valuation", "risk", "growth",
    "商业模式", "财务表现", "估值", "风险", "增长", "护城河",
}
IMPORTANCE = {"high", "medium", "low"}
DIRECTIONS = {"positive", "negative", "mixed"}


def _id(raw: Any, label: str, pattern: re.Pattern[str]) -> str:
    value = str(raw or "").strip().upper()
    _require(bool(pattern.fullmatch(value)), f"{label} invalid ID: {value}")
    return value


def _has_role(item: dict[str, Any], role: str) -> bool:
    return any(x.get("role") == role for x in item.get("evidence_refs", []))


def _graph_claim(raw: Any, spec: dict[str, Any], bundle: dict[str, Any], label: str, *, text_field: str = "text") -> dict[str, Any]:
    return _claim(raw, spec, bundle, label, text_field=text_field)


def compile_research_graph(spec: dict[str, Any], bundle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    graph = spec.get("research_graph")
    _require(isinstance(graph, dict), "v3 requires research_graph")
    themes = graph.get("themes")
    _require(isinstance(themes, list) and 3 <= len(themes) <= 5, "research_graph requires 3-5 themes")

    normalized_themes: list[dict[str, Any]] = []
    theme_ids: set[str] = set()
    observation_ids: set[str] = set()
    all_module_links: set[str] = set()

    for index, raw in enumerate(themes):
        label = f"research_graph.themes[{index}]"
        _require(isinstance(raw, dict), f"{label} must be object")
        theme_id = _id(raw.get("theme_id"), f"{label}.theme_id", THEME_ID)
        _require(theme_id not in theme_ids, f"duplicate theme ID: {theme_id}")
        theme_ids.add(theme_id)
        title = _validate_text(raw.get("title"), f"{label}.title")
        _require(title.casefold() not in GENERIC_TITLES, f"{label}.title is too generic")
        core_question = _validate_text(raw.get("core_question"), f"{label}.core_question")
        observations = raw.get("observations")
        _require(isinstance(observations, list) and len(observations) >= 2, f"{label} requires at least two observations")
        normalized_observations: list[dict[str, Any]] = []
        for obs_index, observation in enumerate(observations):
            obs_label = f"{label}.observations[{obs_index}]"
            _require(isinstance(observation, dict), f"{obs_label} must be object")
            obs_id = _id(observation.get("observation_id"), f"{obs_label}.observation_id", NODE_ID)
            _require(obs_id.startswith("OBS-"), f"{obs_label} must use OBS-* ID")
            _require(obs_id not in observation_ids, f"duplicate observation ID: {obs_id}")
            observation_ids.add(obs_id)
            item = _graph_claim(observation, spec, bundle, obs_label)
            item["observation_id"] = obs_id
            normalized_observations.append(item)

        hypothesis = _graph_claim(raw.get("hypothesis"), spec, bundle, f"{label}.hypothesis")
        challenge = _graph_claim(raw.get("challenge"), spec, bundle, f"{label}.challenge")
        _require(_has_role(challenge, "counter_evidence"), f"{label}.challenge requires counter_evidence")
        resolution = _graph_claim(raw.get("resolution"), spec, bundle, f"{label}.resolution")
        _require(_has_role(resolution, "supports") and _has_role(resolution, "counter_evidence"), f"{label}.resolution must reconcile supports and counter_evidence")
        decision_impact = _graph_claim(raw.get("decision_impact"), spec, bundle, f"{label}.decision_impact")
        _require(any(x.get("ref", "").startswith("BUNDLE:") for x in decision_impact["evidence_refs"]), f"{label}.decision_impact requires Bundle evidence")
        falsification = _graph_claim(raw.get("falsification"), spec, bundle, f"{label}.falsification")
        module_links = raw.get("module_links")
        _require(isinstance(module_links, list) and len(set(module_links)) >= 2, f"{label} requires at least two module_links")
        all_module_links.update(str(x) for x in module_links)

        normalized_themes.append({
            "theme_id": theme_id,
            "title": title,
            "core_question": core_question,
            "observations": normalized_observations,
            "hypothesis": hypothesis,
            "challenge": challenge,
            "resolution": resolution,
            "decision_impact": decision_impact,
            "falsification": falsification,
            "module_links": [str(x) for x in module_links],
        })

    debate = graph.get("debate")
    _require(isinstance(debate, dict), "research_graph.debate is required")
    normalized_sides: dict[str, list[dict[str, Any]]] = {}
    argument_ids: dict[str, set[str]] = {"bull": set(), "bear": set()}
    for side in ("bull", "bear"):
        arguments = debate.get(side)
        _require(isinstance(arguments, list) and len(arguments) >= 3, f"debate.{side} requires at least three arguments")
        normalized: list[dict[str, Any]] = []
        for index, raw in enumerate(arguments):
            label = f"research_graph.debate.{side}[{index}]"
            _require(isinstance(raw, dict), f"{label} must be object")
            arg_id = _id(raw.get("argument_id"), f"{label}.argument_id", NODE_ID)
            _require(arg_id.startswith("ARG-"), f"{label} must use ARG-* ID")
            _require(arg_id not in argument_ids[side], f"duplicate argument ID: {arg_id}")
            argument_ids[side].add(arg_id)
            item = _graph_claim(raw, spec, bundle, label, text_field="claim")
            item["argument_id"] = arg_id
            normalized.append(item)
        normalized_sides[side] = normalized

    adjudication_raw = debate.get("adjudication")
    _require(isinstance(adjudication_raw, dict), "debate.adjudication is required")
    adjudication = _graph_claim(adjudication_raw, spec, bundle, "research_graph.debate.adjudication")
    accepted = {str(x).upper() for x in adjudication_raw.get("accepted_argument_ids", [])}
    discounted = {str(x).upper() for x in adjudication_raw.get("discounted_argument_ids", [])}
    _require(accepted and discounted, "adjudication requires accepted and discounted argument IDs")
    known = argument_ids["bull"] | argument_ids["bear"]
    _require((accepted | discounted) <= known, "adjudication references undefined argument IDs")
    _require(bool(accepted & argument_ids["bull"]) and bool(accepted & argument_ids["bear"]), "adjudication must accept points from both sides")
    _require(bool(discounted & argument_ids["bull"]) or bool(discounted & argument_ids["bear"]), "adjudication must discount at least one argument")
    adjudication["accepted_argument_ids"] = sorted(accepted)
    adjudication["discounted_argument_ids"] = sorted(discounted)
    adjudication["remaining_uncertainty"] = _validate_text(adjudication_raw.get("remaining_uncertainty"), "debate.adjudication.remaining_uncertainty")

    sensitivity = graph.get("sensitivity")
    _require(isinstance(sensitivity, dict), "research_graph.sensitivity is required")
    drivers = sensitivity.get("drivers")
    _require(isinstance(drivers, list) and len(drivers) >= 3, "sensitivity requires at least three drivers")
    normalized_drivers: list[dict[str, Any]] = []
    high_count = 0
    driver_ids: set[str] = set()
    for index, raw in enumerate(drivers):
        label = f"research_graph.sensitivity.drivers[{index}]"
        _require(isinstance(raw, dict), f"{label} must be object")
        driver_id = _id(raw.get("driver_id"), f"{label}.driver_id", NODE_ID)
        _require(driver_id.startswith("DRV-"), f"{label} must use DRV-* ID")
        _require(driver_id not in driver_ids, f"duplicate driver ID: {driver_id}")
        driver_ids.add(driver_id)
        importance = str(raw.get("importance", "")).lower()
        direction = str(raw.get("direction", "")).lower()
        _require(importance in IMPORTANCE, f"{label} invalid importance")
        _require(direction in DIRECTIONS, f"{label} invalid direction")
        high_count += int(importance == "high")
        refs = _validate_refs(raw.get("evidence_refs"), spec, bundle, label)
        normalized_drivers.append({
            "driver_id": driver_id,
            "variable": _validate_text(raw.get("variable"), f"{label}.variable"),
            "base_assumption_path": str(raw.get("base_assumption_path", "")),
            "direction": direction,
            "importance": importance,
            "mechanism": _validate_text(raw.get("mechanism"), f"{label}.mechanism"),
            "upside_case": _validate_text(raw.get("upside_case"), f"{label}.upside_case"),
            "downside_case": _validate_text(raw.get("downside_case"), f"{label}.downside_case"),
            "decision_consequence": _validate_text(raw.get("decision_consequence"), f"{label}.decision_consequence"),
            "evidence_refs": refs,
        })
    _require(high_count >= 1, "sensitivity requires at least one high-importance driver")

    normalized_graph = {
        "themes": normalized_themes,
        "debate": {
            "bull": normalized_sides["bull"],
            "bear": normalized_sides["bear"],
            "adjudication": adjudication,
        },
        "sensitivity": {"drivers": normalized_drivers},
    }
    quality = {
        "status": "PASS",
        "themes": len(normalized_themes),
        "observations": sum(len(x["observations"]) for x in normalized_themes),
        "bull_arguments": len(normalized_sides["bull"]),
        "bear_arguments": len(normalized_sides["bear"]),
        "sensitivity_drivers": len(normalized_drivers),
        "high_importance_drivers": high_count,
        "module_links": sorted(all_module_links),
    }
    return deepcopy(normalized_graph), quality

from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any
from urllib.parse import urlsplit

from scripts.decision_sensitivity import compile_decision_sensitivity
from scripts.report_compiler_v21 import compile_report_v21
from scripts.report_decision_support_v32 import compile_decision_support
from scripts.report_decision_coherence_v32 import compile_decision_coherence
from scripts.report_research_graph_v3 import compile_research_graph
from scripts.report_spec_v2 import SpecError, _ttm_sum, sha256
from scripts.valuation_runtime import return_pair

COMPILER_VERSION = "3.2.0"


GENERIC_SOURCE = re.compile(
    r"^(?:broad\s+)?(?:equity\s+)?index\s+(?:reference|provider|factsheet)$"
    r"|^peer\s+(?:company\s+)?(?:public\s+)?(?:filings|investor\s+relations)$"
    r"|^(?:market|industry|company)\s+(?:source|data|website)$",
    re.IGNORECASE,
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SpecError(message)


def _validate_source_urls(spec: dict[str, Any]) -> int:
    sources = spec.get("sources")
    _require(isinstance(sources, dict) and sources, "v3.1 requires a non-empty source registry")
    try:
        report_date = date.fromisoformat(str(spec.get("report", {}).get("as_of", "")))
    except ValueError as exc:
        raise SpecError("report.as_of must be ISO YYYY-MM-DD") from exc
    for source_id, source in sources.items():
        _require(isinstance(source, dict), f"source {source_id} must be an object")
        for field in ("title", "publisher", "date", "document_type", "locator", "url"):
            _require(str(source.get(field, "")).strip(), f"source {source_id} missing {field}")
        for field in ("title", "publisher", "locator"):
            value = str(source[field]).strip()
            _require(not GENERIC_SOURCE.fullmatch(value), f"source {source_id} uses generic placeholder {field}: {value}")
        try:
            source_date = date.fromisoformat(str(source["date"]))
        except ValueError as exc:
            raise SpecError(f"source {source_id} date must be ISO YYYY-MM-DD") from exc
        _require(source_date <= report_date, f"source {source_id} date cannot be later than report.as_of")
        url = str(source["url"]).strip()
        parsed = urlsplit(url)
        _require(parsed.scheme == "https" and bool(parsed.hostname), f"source {source_id} requires a valid HTTPS url")
        _require(parsed.username is None and parsed.password is None, f"source {source_id} url cannot contain credentials")
        _require(not any(character.isspace() for character in url), f"source {source_id} url cannot contain whitespace")
    return len(sources)


def _validate_v31_contract(spec: dict[str, Any]) -> dict[str, Any]:
    _require(spec.get("schema_version") == "report-spec-v3.1", "v3 compiler requires schema_version report-spec-v3.1")
    report = spec.get("report")
    _require(isinstance(report, dict), "v3.1 requires report metadata")
    for field in ("tax_identity", "horizon"):
        _require(str(report.get(field, "")).strip(), f"v3.1 report missing {field}")
    source_count = _validate_source_urls(spec)
    policy = spec.get("decision_policy")
    _require(isinstance(policy, dict), "v3.1 requires decision_policy")
    _require(policy.get("require_portfolio_context") is True, "v3.1 requires decision_policy.require_portfolio_context=true")
    operating = policy.get("operating")
    _require(isinstance(operating, dict), "v3.1 requires decision_policy.operating")
    metrics = operating.get("metrics")
    _require(isinstance(metrics, list) and metrics, "v3.1 operating policy requires company-specific metrics[]")
    metric_ids = [str(item.get("metric_id", "")) for item in metrics if isinstance(item, dict)]
    _require(len(metric_ids) == len(metrics) and len(set(metric_ids)) == len(metric_ids), "v3.1 operating metric IDs must be present and unique")
    thesis_conditions = policy.get("thesis_break", {}).get("conditions")
    _require(isinstance(thesis_conditions, list) and thesis_conditions, "v3.1 requires thesis-break conditions")
    for index, condition in enumerate(thesis_conditions):
        _require(isinstance(condition, dict) and len(str(condition.get("label", "")).strip()) >= 4, f"v3.1 thesis-break condition {index} requires a human label")
    overview = spec.get("research", {}).get("overview", {})
    _require(isinstance(overview, dict) and isinstance(overview.get("business_model"), dict), "v3.1 overview requires business_model (how the company makes money)")
    _require(isinstance(overview.get("earnings_update"), dict), "v3.1 overview requires earnings_update (period / changed / unchanged)")
    _require(isinstance(spec.get("portfolio_context"), dict), "v3.1 requires explicit portfolio_context")
    _require(isinstance(report.get("cash_valuation"), dict), "v3.2 requires report.cash_valuation (three-basis cash valuation)")
    _require(isinstance(report["cash_valuation"].get("dividend"), dict), "v3.2 requires report.cash_valuation.dividend (after-tax dividend math)")
    _require(isinstance(policy.get("price_ladder"), dict), "v3.2 requires decision_policy.price_ladder (new-money price tiers)")
    _require(isinstance(spec.get("decision_support"), dict), "v3.2 requires decision_support (triggers, pre-mortem, history, bridges)")
    # The baseline also contains actuals: validate every series, not only the
    # optional cash-valuation override, before it drives a decision.
    for name in ("eps", "revenue", "operating_income", "fcf"):
        _ttm_sum(spec, spec.get("quarterly_series", {}).get(name), f"quarterly_series.{name}")
    prior_report = _validate_prior_report(spec)
    final = spec.get("research", {}).get("final_verdict", {})
    action_claims = [(f"final_verdict.{key}", final.get(key)) for key in ("summary", "hold_equals_buy")]
    action_claims.append(("research_graph.debate.adjudication",
                         spec.get("research_graph", {}).get("debate", {}).get("adjudication")))
    action_claims += [(f"research_graph.themes[{index}].decision_impact", item.get("decision_impact"))
                     for index, item in enumerate(spec.get("research_graph", {}).get("themes", []))]
    for label, claim in action_claims:
        _require(isinstance(claim, dict), f"{label} must be an action-bound claim")
        template = claim.get("text_template")
        refs = claim.get("value_refs", {})
        _require(isinstance(template, str) and isinstance(refs, dict),
                 f"{label} requires text_template with compiled action bindings; migrate static conclusions")
        _require(any(isinstance(ref, dict) and ref.get("path") == "/decision/new_money_action"
                     and ref.get("format") == "action" for ref in refs.values()),
                 f"{label} must bind the compiled new-money action with format action")
        for ref in refs.values():
            if isinstance(ref, dict) and ref.get("format") == "action":
                _require(ref.get("path") in {"/decision/new_money_action", "/decision/existing_position_action",
                                               "/decision/existing_position_candidate_action"},
                         f"{label} action binding must use a compiled decision action")
        # In these explicit conclusion fields, action words come from bindings,
        # while the author supplies company-specific reasons. This is a bounded
        # contract, not a claim to understand arbitrary prose.
        for field, text in (("text_template", template), ("implication", claim.get("implication", ""))):
            _require(not re.search(r"买入|减仓|卖出|暂不买|新增资金应回避|\b(?:BUY|SELL|REDUCE|DO_NOT_BUY)\b", str(text), re.I),
                     f"{label}.{field} contains an unbound action conclusion; use compiled action bindings")
    return {"source_urls": source_count, "operating_metrics": len(metrics), "prior_report": prior_report}


def _validate_prior_report(spec: dict[str, Any]) -> dict[str, Any]:
    raw = spec.get("prior_report_context")
    _require(isinstance(raw, dict), "v3.1 requires explicit prior_report_context")
    status = str(raw.get("status", "")).lower()
    _require(status in {"available", "not_available"}, "prior_report_context.status must be available/not_available")
    if status == "not_available":
        reason = str(raw.get("reason", "")).strip()
        _require(len(reason) >= 12, "prior_report_context not_available requires a concrete reason")
        return {"status": status, "reason": reason, "quality": "PASS"}

    required = (
        "path", "as_of", "previous_new_money_action", "previous_existing_position_action",
        "previous_base_irr_reported", "calculation_status", "rating_delta", "metric_delta",
        "thesis_delta", "methodology_delta",
    )
    for field in required:
        _require(str(raw.get(field, "")).strip(), f"prior_report_context missing {field}")
    try:
        prior_date = date.fromisoformat(str(raw["as_of"]))
        report_date = date.fromisoformat(str(spec.get("report", {}).get("as_of", "")))
    except ValueError as exc:
        raise SpecError("prior_report_context.as_of must be ISO YYYY-MM-DD") from exc
    _require(prior_date <= report_date, "prior_report_context.as_of cannot be later than report.as_of")
    calculation_status = str(raw["calculation_status"]).lower()
    _require(calculation_status in {"verified", "recalculated", "unverified"}, "prior_report_context invalid calculation_status")
    try:
        reported = Decimal(str(raw["previous_base_irr_reported"]))
        declared_recalculated = Decimal(str(raw["previous_base_irr_recalculated"])) if raw.get("previous_base_irr_recalculated") is not None else None
    except (InvalidOperation, ValueError) as exc:
        raise SpecError("prior_report_context IRR values must be finite decimals") from exc
    _require(reported.is_finite() and (declared_recalculated is None or declared_recalculated.is_finite()), "prior_report_context IRR values must be finite decimals")
    _require(reported > Decimal("-1") and (declared_recalculated is None or declared_recalculated > Decimal("-1")), "prior_report_context IRR values must be greater than -100%")
    _require(str(raw["previous_new_money_action"]) in {"BUY", "WATCH", "DO_NOT_BUY"}, "prior_report_context invalid previous_new_money_action")
    _require(str(raw["previous_existing_position_action"]) in {"HOLD", "REVIEW", "REDUCE", "SELL", "NOT_APPLICABLE"}, "prior_report_context invalid previous_existing_position_action")
    recalculated: Decimal | None = None
    recalculation_inputs: dict[str, Any] | None = None
    verification_reference: str | None = None
    if calculation_status == "recalculated":
        inputs = raw.get("recalculation_inputs")
        _require(isinstance(inputs, dict), "prior_report_context recalculated requires recalculation_inputs")
        input_fields = ("current_price", "starting_eps", "eps_cagr", "exit_pe", "years", "dividend_yield")
        for field in input_fields:
            _require(str(inputs.get(field, "")).strip(), f"prior_report_context.recalculation_inputs missing {field}")
        try:
            years_decimal = Decimal(str(inputs["years"]))
            _require(years_decimal == years_decimal.to_integral_value() and years_decimal >= 1, "prior report years must be a positive integer")
            target_assumption_id = spec["report"]["target_return_assumption_id"]
            target_return = Decimal(str(spec["assumptions"][target_assumption_id]["value"]))
            result = return_pair(
                current_price=Decimal(str(inputs["current_price"])),
                starting_eps=Decimal(str(inputs["starting_eps"])),
                eps_cagr=Decimal(str(inputs["eps_cagr"])),
                exit_pe=Decimal(str(inputs["exit_pe"])),
                years=int(years_decimal),
                target_return=target_return,
                annual_dividend_yield=Decimal(str(inputs["dividend_yield"])),
            )
            recalculated = Decimal(str(result["irr"]["irr_pct"])) / Decimal(100)
        except (InvalidOperation, ValueError, KeyError) as exc:
            raise SpecError(f"prior report IRR recalculation failed: {exc}") from exc
        if declared_recalculated is not None:
            _require(abs(declared_recalculated - recalculated) <= Decimal("0.00005"), "declared prior-report recalculated IRR mismatches runtime")
        recalculation_inputs = {field: str(inputs[field]) for field in input_fields}
    elif calculation_status == "verified":
        verification_reference = str(raw.get("verification_reference", "")).strip()
        _require(verification_reference, "prior_report_context verified requires verification_reference")
        recalculated = reported
    for field in ("rating_delta", "metric_delta", "thesis_delta", "methodology_delta"):
        _require(len(str(raw[field]).strip()) >= 12, f"prior_report_context.{field} is too thin")
    return {
        "status": status,
        "path": str(raw["path"]),
        "as_of": str(raw["as_of"]),
        "previous_new_money_action": str(raw["previous_new_money_action"]),
        "previous_existing_position_action": str(raw["previous_existing_position_action"]),
        "previous_base_irr_reported": str(reported),
        "previous_base_irr_recalculated": str(recalculated) if recalculated is not None else None,
        "calculation_status": calculation_status,
        "recalculation_inputs": recalculation_inputs,
        "verification_reference": verification_reference,
        "rating_delta": str(raw["rating_delta"]),
        "metric_delta": str(raw["metric_delta"]),
        "thesis_delta": str(raw["thesis_delta"]),
        "methodology_delta": str(raw["methodology_delta"]),
        "quality": "REVIEW" if calculation_status == "unverified" else "PASS",
    }


def compile_report_v3(spec: dict[str, Any]) -> dict[str, Any]:
    validated = _validate_v31_contract(spec)
    legacy_view = deepcopy(spec)
    legacy_view["schema_version"] = "report-spec-v2.1.1"
    bundle = compile_report_v21(legacy_view)
    try:
        bundle["decision_support"] = compile_decision_support(spec, bundle)
    except (ValueError, ArithmeticError, KeyError, TypeError) as exc:
        if isinstance(exc, SpecError):
            raise
        raise SpecError(f"decision support failed: {exc}") from exc
    try:
        bundle["decision_coherence"] = compile_decision_coherence(spec, bundle)
    except (ValueError, ArithmeticError, KeyError, TypeError, StopIteration) as exc:
        if isinstance(exc, SpecError):
            raise
        raise SpecError(f"decision coherence failed: {exc!r}") from exc
    graph, quality = compile_research_graph(spec, bundle)
    bundle["schema_version"] = "report-bundle-v3.1"
    bundle["compiler_version"] = COMPILER_VERSION
    bundle["input_schema_version"] = "report-spec-v3.1"
    bundle["portfolio_context"] = deepcopy(bundle["decision"]["portfolio_context"])
    bundle["prior_report_context"] = deepcopy(validated["prior_report"])
    bundle["research_graph"] = graph
    bundle["research_graph_quality"] = quality
    try:
        bundle["decision_sensitivity"] = compile_decision_sensitivity(bundle, spec["decision_policy"])
    except (ValueError, ArithmeticError, KeyError) as exc:
        raise SpecError(f"decision sensitivity failed: {exc}") from exc
    portfolio_quality = "PASS" if bundle["portfolio_context"]["complete"] else "REVIEW"
    prior_quality = bundle["prior_report_context"]["quality"]
    bundle["data_quality"] = {
        "status": "REVIEW" if "REVIEW" in {portfolio_quality, prior_quality} else "PASS",
        "source_urls": {"status": "PASS", "count": validated["source_urls"]},
        "ttm_units": {"status": "PASS"},
        "operating_metrics": {"status": "PASS", "count": validated["operating_metrics"]},
        "portfolio_context": {
            "status": portfolio_quality,
            "gate": bundle["portfolio_context"]["gate"],
        },
        "prior_report_context": {
            "status": prior_quality,
            "availability": bundle["prior_report_context"]["status"],
        },
    }
    bundle["spec_hash"] = sha256(spec)
    unhashed = deepcopy(bundle)
    unhashed.pop("bundle_hash", None)
    bundle["bundle_hash"] = sha256(unhashed)
    return bundle

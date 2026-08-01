from __future__ import annotations

from copy import deepcopy
from typing import Any

from scripts.report_narrative_v22 import attach_narrative_v22
from scripts.report_research_v21 import compile_spec_v21
from scripts.report_spec_v2 import sha256


def compile_report_v21(spec: dict[str, Any]) -> dict[str, Any]:
    source_spec = deepcopy(spec)
    working_spec = deepcopy(spec)
    # v2.2 extends the v2.1.1 analytical schema with a Narrative layer while
    # intentionally preserving the established numeric compiler contract.
    if working_spec.get("schema_version") == "report-spec-v2.2":
        working_spec["schema_version"] = "report-spec-v2.1.1"
    # Preserve compatibility with the historical Meta fixture's plural peer
    # source alias. New specs should use the canonical source ID directly.
    sources = working_spec.get("sources", {})
    if "SRC-PEERS" not in sources and "SRC-PEER" in sources:
        sources["SRC-PEERS"] = deepcopy(sources["SRC-PEER"])
    bundle = compile_spec_v21(working_spec)
    bundle["spec_schema_version"] = source_spec.get("schema_version")
    bundle["spec_hash"] = sha256(source_spec)
    bundle["assumptions"] = deepcopy(working_spec["assumptions"])
    bundle["quarterly_series"] = deepcopy(working_spec["quarterly_series"])
    if bundle.get("research_quality", {}).get("status") != "PASS":
        raise ValueError("research quality validation did not pass")
    bundle = attach_narrative_v22(working_spec, bundle)
    if bundle.get("narrative_quality", {}).get("status") != "PASS":
        raise ValueError("narrative quality validation did not pass")
    unhashed = deepcopy(bundle)
    unhashed.pop("bundle_hash", None)
    bundle["bundle_hash"] = sha256(unhashed)
    return bundle

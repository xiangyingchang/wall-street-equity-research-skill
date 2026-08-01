from __future__ import annotations

from copy import deepcopy
from typing import Any

from scripts.report_research_v21 import compile_spec_v21
from scripts.report_spec_v2 import sha256


def compile_report_v21(spec: dict[str, Any]) -> dict[str, Any]:
    bundle = compile_spec_v21(spec)
    bundle["assumptions"] = deepcopy(spec["assumptions"])
    bundle["quarterly_series"] = deepcopy(spec["quarterly_series"])
    if bundle.get("research_quality", {}).get("status") != "PASS":
        raise ValueError("research quality validation did not pass")
    unhashed = deepcopy(bundle)
    unhashed.pop("bundle_hash", None)
    bundle["bundle_hash"] = sha256(unhashed)
    return bundle

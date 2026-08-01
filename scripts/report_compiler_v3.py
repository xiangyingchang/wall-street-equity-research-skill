from __future__ import annotations

from copy import deepcopy
from typing import Any

from scripts.report_compiler_v21 import compile_report_v21
from scripts.report_research_graph_v3 import compile_research_graph
from scripts.report_spec_v2 import sha256


def compile_report_v3(spec: dict[str, Any]) -> dict[str, Any]:
    bundle = compile_report_v21(spec)
    graph, quality = compile_research_graph(spec, bundle)
    bundle["schema_version"] = "report-bundle-v3.0"
    bundle["compiler_version"] = "3.0.0"
    bundle["research_graph"] = graph
    bundle["research_graph_quality"] = quality
    unhashed = deepcopy(bundle)
    unhashed.pop("bundle_hash", None)
    bundle["bundle_hash"] = sha256(unhashed)
    return bundle

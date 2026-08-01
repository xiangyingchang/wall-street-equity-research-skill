from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path
from typing import Any, Iterable

D = Decimal
ID_RE = re.compile(r"\b(?:FACT|DERIVED|MODEL|ASM|THR|B|BR|REV|RUN)-[A-Z0-9][A-Z0-9_-]*\b", re.I)
BAD_RESULTS = {"todo", "fail", "failed", "未运行", "unknown", "unrun", "pending", "n/a"}


@dataclass(frozen=True)
class Finding:
    level: str
    message: str


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def decimal(raw: Any) -> Decimal | None:
    if raw is None or isinstance(raw, bool):
        return None
    text = str(raw).replace(",", "").replace("$", "").replace("¥", "").replace("€", "")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        value = D(match.group(0))
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def percent(raw: Any) -> Decimal | None:
    value = decimal(raw)
    return None if value is None else value / D(100) if "%" in str(raw) else value


def q(value: Decimal, places: str = "0.0001") -> str:
    return str(value.quantize(D(places), rounding=ROUND_HALF_UP))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_artifact(*, runtime_name: str, artifact_id: str, input_refs: list[str], inputs: dict[str, Any], outputs: dict[str, Any]) -> dict[str, Any]:
    if not runtime_name.strip():
        raise ValueError("runtime_name is required")
    if not re.fullmatch(r"RUN-[A-Z0-9][A-Z0-9_-]*", artifact_id, re.I):
        raise ValueError("artifact_id must use RUN-* format")
    if not isinstance(input_refs, list) or not all(isinstance(x, str) and x.strip() for x in input_refs):
        raise ValueError("input_refs must be non-empty IDs")
    result: dict[str, Any] = {
        "schema_version": "runtime-artifact-v1",
        "runtime_name": runtime_name.strip(),
        "artifact_id": artifact_id,
        "input_refs": input_refs,
        "inputs": inputs,
        "outputs": outputs,
    }
    result["artifact_hash"] = hashlib.sha256(canonical_json(result).encode()).hexdigest()
    return result


def scenario_value(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ["artifact_id", "scenario", "metric_value", "reference_multiple", "target_return_price", "safety_margin"]:
        if key not in payload:
            raise ValueError(f"missing required key: {key}")
    metric = D(str(payload["metric_value"]))
    multiple = D(str(payload["reference_multiple"]))
    target = D(str(payload["target_return_price"]))
    margin = D(str(payload["safety_margin"]))
    if metric <= 0 or multiple <= 0 or target <= 0 or margin < 0 or margin >= 1:
        raise ValueError("invalid scenario-value input")
    with localcontext() as ctx:
        ctx.prec = 50
        outputs = {
            "scenario": str(payload["scenario"]),
            "metric_value": q(metric),
            "reference_multiple": q(multiple),
            "forward_reference_value": q(metric * multiple),
            "target_return_price": q(target),
            "safety_margin": q(margin),
            "buy_price": q(target * (D(1) - margin)),
            "role": str(payload.get("role", "scenario")),
        }
    return build_artifact(
        runtime_name="scenario-value",
        artifact_id=str(payload["artifact_id"]),
        input_refs=[str(x) for x in payload.get("input_refs", [])],
        inputs={k: outputs[k] for k in ["scenario", "metric_value", "reference_multiple", "target_return_price", "safety_margin", "role"]},
        outputs=outputs,
    )


def tables(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines(); out: list[dict[str, Any]] = []; i = 0
    while i + 1 < len(lines):
        h, sep = lines[i].strip(), lines[i + 1].strip()
        if h.startswith("|") and sep.startswith("|") and re.fullmatch(r"\|?[\s:|-]+\|?", sep):
            headers = [x.strip() for x in h.strip("|").split("|")]; rows = []; j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = [x.strip() for x in lines[j].strip().strip("|").split("|")]
                if len(cells) == len(headers): rows.append(cells)
                j += 1
            out.append({"headers": headers, "rows": rows, "line": i + 1}); i = j
        else: i += 1
    return out


def find_table(all_tables: Iterable[dict[str, Any]], required: set[str]) -> dict[str, Any] | None:
    req = {norm(x) for x in required}
    return next((t for t in all_tables if req <= {norm(str(h)) for h in t["headers"]}), None)


def rows(table: dict[str, Any] | None) -> list[dict[str, str]]:
    if table is None: return []
    headers = [str(x) for x in table["headers"]]
    return [dict(zip(headers, [str(c) for c in row])) for row in table["rows"]]


def get(row: dict[str, str], name: str) -> str:
    target = norm(name)
    return next((v for k, v in row.items() if norm(k) == target), "")


def placeholder(value: str) -> bool:
    value = norm(value)
    return not value or value.startswith("todo") or value in {"-", "tbd", "placeholder"}


def refs(text: str) -> set[str]:
    found = {m.group(0).upper() for m in ID_RE.finditer(text)}
    return found - {"FACT-BASED", "MODEL-OUTPUT", "RUN-TIME"}


def quarter(raw: str) -> tuple[int, int] | None:
    text = raw.upper().replace("’", "'")
    for idx, pattern in enumerate([r"Q([1-4])\s*['-]?\s*(20\d{2})", r"(20\d{2})\s*Q([1-4])", r"Q([1-4])\s*['-]?\s*(\d{2})"]):
        m = re.search(pattern, text)
        if not m: continue
        if idx == 1: return int(m.group(1)), int(m.group(2))
        year = int(m.group(2)); return (year + 2000 if year < 100 else year), int(m.group(1))
    return None


def relerr(actual: Decimal, expected: Decimal) -> Decimal:
    return abs(actual - expected) / max(abs(expected), D("0.01"))


def artifact_path(base: Path | None, raw: str) -> Path | None:
    if base is None or placeholder(raw): return None
    p = Path(raw); return p if p.is_absolute() else base / p

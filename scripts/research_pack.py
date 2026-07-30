#!/usr/bin/env python3
"""Create and validate deterministic research-pack-v1 recovery checkpoints."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

from financial_formulas import (
    DECIMAL_PRECISION,
    FORMULA_REGISTRY,
    FormulaResult,
    PaybackError,
    evaluate_formula,
)


SCHEMA_VERSION = "research-pack-v1"
CHECKPOINT_ORDER = (
    "initialized",
    "sources_ready",
    "facts_ready",
    "valuation_locked",
    "matrix_ready",
    "draft_ready",
    "audit_passed",
)
TOP_LEVEL_KEYS = {
    "schema_version",
    "identity",
    "report",
    "previous_report",
    "sources",
    "facts",
    "derived_records",
    "valuation_basis",
    "action_matrix",
    "evidence_gates",
    "checkpoints",
}
SOURCE_INPUT_KEYS = {"url", "title", "publisher", "tier", "published_date"}
SOURCE_KEYS = {
    "source_id",
    "canonical_url",
    "title",
    "publisher",
    "tier",
    "published_date",
}
FACT_KEYS = {
    "fact_id",
    "field",
    "value_type",
    "value",
    "unit",
    "as_of",
    "source_ids",
}
DERIVED_RECORD_KEYS = {
    "id",
    "formula_id",
    "inputs",
    "computed",
    "reported",
    "rounding",
    "binding",
}
DERIVED_INPUT_BASE_KEYS = {"name", "kind"}
DERIVED_INPUT_KINDS = {"fact_ref", "derived_ref", "literal"}
VALUE_UNIT_KEYS = {"value", "unit"}
ROUNDING_KEYS = {"mode", "places"}
BINDING_KEYS = {"section", "label", "column"}
TTM_PERIOD = re.compile(r"FY(?P<year>[0-9]{4})-Q(?P<quarter>[1-4])\Z")
TTM_BRIDGE_ROLES = {"fy", "current_ytd", "prior_ytd"}
SUPPORTED_UNITS = {
    "USD": ("currency", 0),
    "USD_B": ("currency", 9),
    "shares": ("shares", 0),
    "shares_B": ("shares", 9),
    "USD/share": ("currency_per_share", 0),
    "ratio": ("ratio", 0),
    "x": ("multiple", 0),
    "year": ("time", 0),
}
REPORTED_UNITS = set(SUPPORTED_UNITS) | {"%"}
BASIS_KEYS = {"price", "shares"}
PRICE_KEYS = {"value", "currency", "kind", "market_date", "source_id"}
SHARES_KEYS = {"value", "as_of", "source_id"}
PRICE_KINDS = {"regular_close", "intraday", "pre_market", "after_hours"}
SOURCE_TIERS = {"Tier 1", "Tier 2", "Internal"}
FACT_TYPES = {"decimal", "date", "string"}
# Action Matrix entry schema (semantic gate, Batch 2C). Each entry must declare
# exactly these keys. `action` and `trigger_type` are casefolded against the
# canonical report vocabulary so the pack and the report's module 8 table stay
# in structural correspondence; `na` is the honest "not applicable" flag and is
# only permitted for Buy or Add.
ACTION_MATRIX_KEYS = {"action", "trigger_type", "condition", "execution", "na"}
ACTION_MATRIX_ACTIONS = {"buy", "add", "hold", "reduce", "sell"}
ACTION_MATRIX_TRIGGER_TYPES = {"price", "valuation", "operating", "thesis-break"}
ACTION_MATRIX_NA_ACTIONS = {"buy", "add"}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
SOURCE_ID_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
FORBIDDEN_TELEMETRY_KEYS = {
    "provider",
    "model",
    "token",
    "tokens",
    "finish_reason",
    "timing",
    "retry",
    "runtime",
    "latency",
    "duration",
    "started_at",
    "ended_at",
}
MISSING = object()


class ResearchPackError(Exception):
    """Base class for stable CLI failures."""


class InputError(ResearchPackError):
    """Invalid usage, file, or JSON input (exit 2)."""


class StateConflict(ResearchPackError):
    """A valid request conflicts with durable pack state (exit 1)."""


def canonical_json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    """Encode JSON deterministically without provider or runtime metadata."""
    if pretty:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    else:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return (text + "\n").encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def pack_lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


@contextmanager
def pack_write_lock(path: Path, *, timeout: float = 30.0):
    """Serialize cooperative skill writers for one research-pack path."""
    reject_symlink(path, "pack")
    lock_path = pack_lock_path(path)
    reject_symlink(lock_path, "pack lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        # Non-blocking acquire with a bounded retry loop instead of blocking
        # forever. fcntl.flock(LOCK_EX) without LOCK_NB can stall the whole
        # process if another writer is stuck, so poll until the timeout elapses
        # and raise a clear error rather than hanging indefinitely.
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if deadline is None:
                    time.sleep(0.1)
                    continue
                if time.monotonic() >= deadline:
                    raise StateConflict(
                        "pack lock timeout: another writer may be stuck"
                    ) from None
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _write_pack_atomic_unlocked(path: Path, pack: dict[str, Any]) -> bool:
    reject_symlink(path, "pack")
    payload = canonical_json_bytes(pack, pretty=True)
    if path.exists():
        try:
            if path.read_bytes() == payload:
                return False
        except OSError as error:
            raise InputError(f"cannot read pack before write: {path}: {error}") from error
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        return True
    except OSError as error:
        raise InputError(f"atomic pack write failed: {path}: {error}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_pack_atomic(
    path: Path,
    pack: dict[str, Any],
    *,
    lock_held: bool = False,
) -> bool:
    """Atomically replace path under the shared cooperative-writer lock."""
    if lock_held:
        return _write_pack_atomic_unlocked(path, pack)
    with pack_write_lock(path):
        return _write_pack_atomic_unlocked(path, pack)


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is not allowed: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key is not allowed: {key!r}")
        result[key] = value
    return result


def load_json_bytes(payload: bytes, label: str, source: Path | str) -> Any:
    try:
        text = payload.decode("utf-8")
        return json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except UnicodeError as error:
        raise InputError(f"{label} is not valid UTF-8: {source}: {error}") from error
    except json.JSONDecodeError as error:
        raise InputError(
            f"{label} is not valid JSON: {source}:{error.lineno}:{error.colno}: {error.msg}"
        ) from error
    except ValueError as error:
        raise InputError(f"{label} is not valid strict JSON: {source}: {error}") from error


def _load_json(path: Path, label: str) -> Any:
    reject_symlink(path, label)
    try:
        payload = path.read_bytes()
    except FileNotFoundError as error:
        raise InputError(f"{label} does not exist: {path}") from error
    except OSError as error:
        raise InputError(f"cannot read {label}: {path}: {error}") from error
    return load_json_bytes(payload, label, path)


def load_pack_bytes(payload: bytes, source: Path | str = "<pack-bytes>") -> dict[str, Any]:
    value = load_json_bytes(payload, "pack", source)
    if not isinstance(value, dict):
        raise InputError("pack root must be a JSON object")
    return value


def load_pack(path: Path) -> dict[str, Any]:
    reject_symlink(path, "pack")
    try:
        return load_pack_bytes(path.read_bytes(), path)
    except FileNotFoundError as error:
        raise InputError(f"pack does not exist: {path}") from error
    except OSError as error:
        raise InputError(f"cannot read pack: {path}: {error}") from error


def _require_exact_keys(
    value: Any,
    keys: set[str],
    label: str,
    issues: list[str],
) -> bool:
    if not isinstance(value, dict):
        issues.append(f"{label} must be an object")
        return False
    actual = set(value)
    missing = sorted(keys - actual)
    extra = sorted(actual - keys)
    if missing:
        issues.append(f"{label} missing keys: {', '.join(missing)}")
    if extra:
        issues.append(f"{label} has unknown keys: {', '.join(extra)}")
    return not missing and not extra


def _nonempty_string(value: Any, label: str, issues: list[str]) -> bool:
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{label} must be a nonempty string")
        return False
    return True


def reject_symlink(path: Path, label: str) -> None:
    if path.is_symlink():
        raise InputError(f"{label} path must not be a symlink: {path}")


def _canonical_date(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise InputError(f"{label} must be an ISO date string (YYYY-MM-DD)")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise InputError(f"{label} must be a valid ISO date (YYYY-MM-DD): {value!r}") from error
    if parsed.isoformat() != value:
        raise InputError(f"{label} must use canonical YYYY-MM-DD form: {value!r}")
    return value


def _date_issue(value: Any, label: str, issues: list[str]) -> None:
    try:
        _canonical_date(value, label)
    except InputError as error:
        issues.append(str(error))


def _canonical_decimal(value: Any, label: str, *, positive: bool = False) -> str:
    if not isinstance(value, str):
        raise InputError(f"{label} must be a Decimal encoded as a string")
    if value != value.strip() or not value:
        raise InputError(f"{label} must be a nonempty canonical Decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise InputError(f"{label} is not a valid Decimal string: {value!r}") from error
    if not parsed.is_finite():
        raise InputError(f"{label} must be finite")
    if positive and parsed <= 0:
        raise InputError(f"{label} must be positive")
    normalized = format(parsed, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if normalized in {"-0", ""}:
        normalized = "0"
    return normalized


def canonicalize_url(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise InputError("source.url must be a nonempty HTTPS URL")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise InputError("source.url must not contain ASCII control characters or DEL")
    if value != value.strip():
        raise InputError("source.url must not contain surrounding whitespace")
    separator = value.find("://")
    authority_end = len(value)
    if separator >= 0:
        for marker in "/?#":
            position = value.find(marker, separator + 3)
            if position >= 0:
                authority_end = min(authority_end, position)
        authority = value[separator + 3 : authority_end]
        if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in authority):
            raise InputError("source.url authority must not contain whitespace or control characters")
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        raise InputError(f"source.url is malformed: {value!r}") from error
    if parsed.scheme.lower() != "https":
        raise InputError("source.url must use HTTPS")
    if not parsed.hostname:
        raise InputError("source.url must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise InputError("source.url must not include user information")
    try:
        port = parsed.port
    except ValueError as error:
        raise InputError(f"source.url has an invalid port: {value!r}") from error

    dot_translation = str.maketrans({"。": ".", "．": ".", "｡": "."})
    normalized_hostname = parsed.hostname.translate(dot_translation).rstrip(".")
    if not normalized_hostname:
        raise InputError("source.url host must not be only DNS root dots")
    try:
        host = normalized_hostname.encode("idna").decode("ascii").translate(dot_translation).rstrip(".").lower()
    except UnicodeError as error:
        raise InputError(f"source.url host is invalid: {parsed.hostname!r}") from error
    if ":" in host:
        host = f"[{host}]"
    netloc = host if port in {None, 443} else f"{host}:{port}"
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    canonical = SplitResult("https", netloc, path, parsed.query, "")
    return urlunsplit(canonical)


def source_id(canonical_url: str) -> str:
    digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _canonical_source(raw: Any) -> dict[str, Any]:
    issues: list[str] = []
    if not _require_exact_keys(raw, SOURCE_INPUT_KEYS, "source", issues):
        raise InputError("; ".join(issues))
    assert isinstance(raw, dict)
    for key in ("title", "publisher"):
        _nonempty_string(raw[key], f"source.{key}", issues)
    if not isinstance(raw["tier"], str) or raw["tier"] not in SOURCE_TIERS:
        issues.append(f"source.tier must be one of: {', '.join(sorted(SOURCE_TIERS))}")
    published_date = raw["published_date"]
    if published_date is not None:
        try:
            published_date = _canonical_date(published_date, "source.published_date")
        except InputError as error:
            issues.append(str(error))
    if issues:
        raise InputError("; ".join(issues))
    canonical_url = canonicalize_url(raw["url"])
    identifier = source_id(canonical_url)
    return {
        "source_id": identifier,
        "canonical_url": canonical_url,
        "title": raw["title"].strip(),
        "publisher": raw["publisher"].strip(),
        "tier": raw["tier"],
        "published_date": published_date,
    }


def _canonical_fact(raw: Any) -> dict[str, Any]:
    issues: list[str] = []
    if not _require_exact_keys(raw, FACT_KEYS, "fact", issues):
        raise InputError("; ".join(issues))
    assert isinstance(raw, dict)
    fact_id = raw["fact_id"]
    if not isinstance(fact_id, str) or not IDENTIFIER.fullmatch(fact_id):
        issues.append("fact.fact_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}")
    _nonempty_string(raw["field"], "fact.field", issues)
    value_type = raw["value_type"]
    if not isinstance(value_type, str) or value_type not in FACT_TYPES:
        issues.append(f"fact.value_type must be one of: {', '.join(sorted(FACT_TYPES))}")
    value = raw["value"]
    try:
        if value_type == "decimal":
            value = _canonical_decimal(value, "fact.value")
        elif value_type == "date":
            value = _canonical_date(value, "fact.value")
        elif value_type == "string":
            if not isinstance(value, str) or not value:
                raise InputError("fact.value must be a nonempty string for value_type=string")
    except InputError as error:
        issues.append(str(error))
    unit = raw["unit"]
    if unit is not None and (not isinstance(unit, str) or not unit.strip()):
        issues.append("fact.unit must be null or a nonempty string")
    try:
        as_of = _canonical_date(raw["as_of"], "fact.as_of")
    except InputError as error:
        issues.append(str(error))
        as_of = raw["as_of"]
    references = raw["source_ids"]
    if not isinstance(references, list) or not references:
        issues.append("fact.source_ids must be a nonempty array")
        references = []
    elif any(not isinstance(item, str) or not SOURCE_ID_PATTERN.fullmatch(item) for item in references):
        issues.append("fact.source_ids entries must be canonical sha256 source IDs")
    if issues:
        raise InputError("; ".join(issues))
    return {
        "fact_id": fact_id,
        "field": raw["field"].strip(),
        "value_type": value_type,
        "value": value,
        "unit": unit.strip() if isinstance(unit, str) else None,
        "as_of": as_of,
        "source_ids": sorted(set(references)),
    }


def _derived_input_keys(formula_id: str, kind: str) -> set[str]:
    keys = set(DERIVED_INPUT_BASE_KEYS)
    if kind == "fact_ref":
        keys.add("fact_id")
    elif kind == "derived_ref":
        keys.add("derived_record_id")
    elif kind == "literal":
        keys.update({"value", "unit"})
    if formula_id == "ttm_sum_v1":
        keys.add("period")
    elif formula_id == "ttm_bridge_v1":
        keys.update({"role", "fiscal_year", "duration_quarters"})
    return keys


def _canonical_derived_input(raw: Any, formula_id: str, index: int) -> dict[str, Any]:
    label = f"derived record.inputs[{index}]"
    if not isinstance(raw, dict):
        raise InputError(f"{label} must be an object")
    kind = raw.get("kind")
    if not isinstance(kind, str) or kind not in DERIVED_INPUT_KINDS:
        raise InputError(f"{label}.kind must be one of: derived_ref, fact_ref, literal")
    issues: list[str] = []
    if not _require_exact_keys(raw, _derived_input_keys(formula_id, kind), label, issues):
        raise InputError("; ".join(issues))
    name = raw["name"]
    if not isinstance(name, str) or not IDENTIFIER.fullmatch(name):
        issues.append(f"{label}.name must be a canonical identifier")
    item: dict[str, Any] = {"name": name, "kind": kind}
    if kind == "fact_ref":
        reference = raw["fact_id"]
        if not isinstance(reference, str) or not IDENTIFIER.fullmatch(reference):
            issues.append(f"{label}.fact_id must be a canonical identifier")
        item["fact_id"] = reference
    elif kind == "derived_ref":
        reference = raw["derived_record_id"]
        if not isinstance(reference, str) or not IDENTIFIER.fullmatch(reference):
            issues.append(f"{label}.derived_record_id must be a canonical identifier")
        item["derived_record_id"] = reference
    else:
        try:
            value = _canonical_decimal(raw["value"], f"{label}.value")
        except InputError as error:
            issues.append(str(error))
            value = raw["value"]
        unit = raw["unit"]
        if not isinstance(unit, str) or unit not in SUPPORTED_UNITS:
            issues.append(f"{label}.unit must be a supported canonical unit")
        item.update({"value": value, "unit": unit})
    if formula_id == "ttm_sum_v1":
        period = raw["period"]
        if not isinstance(period, str) or not TTM_PERIOD.fullmatch(period):
            issues.append(f"{label}.period must use FYyyyy-Qn syntax")
        item["period"] = period
    elif formula_id == "ttm_bridge_v1":
        role = raw["role"]
        fiscal_year = raw["fiscal_year"]
        duration = raw["duration_quarters"]
        if not isinstance(role, str) or role not in TTM_BRIDGE_ROLES:
            issues.append(f"{label}.role must be one of: current_ytd, fy, prior_ytd")
        if isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int) or not 1900 <= fiscal_year <= 9999:
            issues.append(f"{label}.fiscal_year must be an integer from 1900 through 9999")
        if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= 4:
            issues.append(f"{label}.duration_quarters must be an integer from 1 through 4")
        item.update(
            {"role": role, "fiscal_year": fiscal_year, "duration_quarters": duration}
        )
    if issues:
        raise InputError("; ".join(issues))
    return item


def _canonical_value_unit(raw: Any, label: str, *, reported: bool = False) -> dict[str, str]:
    issues: list[str] = []
    if not _require_exact_keys(raw, VALUE_UNIT_KEYS, label, issues):
        raise InputError("; ".join(issues))
    assert isinstance(raw, dict)
    unit = raw["unit"]
    allowed_units = REPORTED_UNITS if reported else set(SUPPORTED_UNITS)
    if not isinstance(unit, str) or unit not in allowed_units:
        issues.append(f"{label}.unit must be a supported canonical unit")
    try:
        value = _canonical_decimal(raw["value"], f"{label}.value")
    except InputError as error:
        issues.append(str(error))
        value = raw["value"]
    if issues:
        raise InputError("; ".join(issues))
    return {"value": value, "unit": unit}


def _reported_from_computed(value: Decimal, computed_unit: str, reported_unit: str) -> Decimal:
    if computed_unit == reported_unit:
        return value
    if computed_unit == "ratio" and reported_unit == "%":
        return value * Decimal("100")
    if computed_unit == "%" and reported_unit == "ratio":
        return value / Decimal("100")
    raise InputError(
        f"unsupported computed/reported unit conversion: {computed_unit!r} -> {reported_unit!r}"
    )


def _unit_scale(unit: str) -> int:
    return SUPPORTED_UNITS[unit][1]


def _formula_unit_and_scale(formula_id: str, inputs: list[dict[str, Any]]) -> tuple[str, Decimal]:
    units = [item["unit"] for item in inputs]
    if any(unit not in SUPPORTED_UNITS for unit in units):
        raise InputError(f"{formula_id} uses an unsupported input unit")
    if formula_id in {"sum_v1", "difference_v1", "ttm_sum_v1", "ttm_bridge_v1"}:
        if len(set(units)) != 1:
            raise InputError(f"{formula_id} requires exactly identical input units")
        return units[0], Decimal("1")
    if formula_id == "ratio_v1":
        named = {item["name"]: item for item in inputs}
        numerator, denominator = named["numerator"], named["denominator"]
        numerator_dimension, denominator_dimension = (
            SUPPORTED_UNITS[numerator["unit"]][0],
            SUPPORTED_UNITS[denominator["unit"]][0],
        )
        if numerator_dimension == denominator_dimension:
            exponent = _unit_scale(numerator["unit"]) - _unit_scale(denominator["unit"])
            return "ratio", Decimal("10") ** exponent
        supported = {
            ("USD_B", "shares_B"): "USD/share",
            ("USD", "shares"): "USD/share",
        }
        output = supported.get((numerator["unit"], denominator["unit"]))
        if output is None:
            raise InputError(
                f"ratio_v1 unit algebra does not support {numerator['unit']} / {denominator['unit']}"
            )
        exponent = (
            _unit_scale(numerator["unit"])
            - _unit_scale(denominator["unit"])
            - _unit_scale(output)
        )
        return output, Decimal("10") ** exponent
    if formula_id == "product_v1":
        if len(inputs) != 2:
            raise InputError("product_v1 derived records require exactly two inputs")
        left, right = inputs
        if left["unit"] == "ratio":
            return right["unit"], Decimal("1")
        if right["unit"] == "ratio":
            return left["unit"], Decimal("1")
        supported = {
            frozenset(("USD/share", "shares_B")): "USD_B",
            frozenset(("USD/share", "shares")): "USD",
        }
        output = supported.get(frozenset((left["unit"], right["unit"])))
        if output is None:
            raise InputError(
                f"product_v1 unit algebra does not support {left['unit']} * {right['unit']}"
            )
        exponent = _unit_scale(left["unit"]) + _unit_scale(right["unit"]) - _unit_scale(output)
        return output, Decimal("10") ** exponent
    expected = {"multiple": "x", "discount_rate": "ratio", "years": "year"}
    actual = {item["name"]: item["unit"] for item in inputs}
    if actual != expected:
        raise InputError(
            "payback inputs must use multiple=x, discount_rate=ratio, years=year"
        )
    return "ratio", Decimal("1")


def _validate_literal(formula_id: str, item: dict[str, Any]) -> None:
    allowed = {("payback_ttm_v1", "years"), ("payback_forward_v1", "years")}
    if (formula_id, item["name"]) not in allowed or item["unit"] != "year":
        raise InputError(
            f"literal input is not allowed for {formula_id}.{item['name']}; only payback years=year is whitelisted"
        )
    value = Decimal(item["value"])
    if value <= 0 or value != value.to_integral_value():
        raise InputError("payback years literal must be a positive integer")


def _resolve_derived_record(
    pack: dict[str, Any],
    record_id: str,
    stack: tuple[str, ...] = (),
) -> dict[str, Any]:
    if record_id in stack:
        raise InputError("derived record cycle detected: " + " -> ".join((*stack, record_id)))
    raw = pack.get("derived_records", {}).get(record_id)
    if raw is None:
        raise StateConflict(f"derived record references undefined derived_record_id: {record_id}")
    record = _canonical_derived_shape(raw)
    if record["id"] != record_id:
        raise InputError(f"derived_records[{record_id!r}].id must equal its registry key")
    resolved_inputs: list[dict[str, Any]] = []
    for item in record["inputs"]:
        resolved = {key: value for key, value in item.items() if key not in {"fact_id", "derived_record_id", "kind"}}
        if item["kind"] == "fact_ref":
            fact_id = item["fact_id"]
            fact = pack.get("facts", {}).get(fact_id)
            if fact is None:
                raise StateConflict(f"derived record references undefined fact_id: {fact_id}")
            canonical_fact = _canonical_fact(fact)
            if canonical_fact["value_type"] != "decimal":
                raise InputError(f"derived fact_ref {fact_id!r} must resolve to value_type=decimal")
            if canonical_fact["unit"] not in SUPPORTED_UNITS:
                raise InputError(f"derived fact_ref {fact_id!r} uses unsupported unit {canonical_fact['unit']!r}")
            undefined_sources = sorted(set(canonical_fact["source_ids"]) - set(pack.get("sources", {})))
            if undefined_sources:
                raise StateConflict(
                    f"derived fact_ref {fact_id!r} references undefined source ID: {', '.join(undefined_sources)}"
                )
            resolved.update(
                {
                    "value": canonical_fact["value"],
                    "unit": canonical_fact["unit"],
                    "as_of": canonical_fact["as_of"],
                    "source_ids": canonical_fact["source_ids"],
                }
            )
        elif item["kind"] == "derived_ref":
            child = _resolve_derived_record(
                pack,
                item["derived_record_id"],
                (*stack, record_id),
            )
            resolved.update(
                {
                    "value": str(child["result"].value),
                    "unit": child["unit"],
                    "as_of": child["as_of"],
                    "source_ids": child["source_ids"],
                }
            )
        else:
            _validate_literal(record["formula_id"], item)
            resolved.update(
                {
                    "value": item["value"],
                    "unit": item["unit"],
                    "as_of": None,
                    "source_ids": [],
                }
            )
        resolved_inputs.append(resolved)
    names = [item["name"] for item in resolved_inputs]
    if len(names) != len(set(names)):
        raise InputError("formula input names must be unique")
    _validate_ttm_provenance(record["formula_id"], resolved_inputs)
    output_unit, scale = _formula_unit_and_scale(record["formula_id"], resolved_inputs)
    raw_result = evaluate_formula(record["formula_id"], resolved_inputs)
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        result = FormulaResult(
            raw_result.formula_id,
            +(raw_result.value * scale),
            raw_result.absolute_residual,
            raw_result.relative_residual,
        )
    if record["computed"]["unit"] != output_unit:
        raise InputError(
            f"{record['formula_id']} computed.unit must be {output_unit!r}, got {record['computed']['unit']!r}"
        )
    if Decimal(record["computed"]["value"]) != result.value:
        raise InputError(
            f"derived record {record_id!r} computed.value does not equal the resolved registered formula result: "
            f"declared {record['computed']['value']}, resolved {result.value}"
        )
    if Decimal(record["reported"]["value"]) != rounded_reported_value(record, result.value):
        raise InputError("derived record.reported.value does not equal declared conversion and rounding")
    dates = [item["as_of"] for item in resolved_inputs if item["as_of"] is not None]
    return {
        "record": record,
        "inputs": resolved_inputs,
        "result": result,
        "unit": output_unit,
        "as_of": max(dates) if dates else None,
        "source_ids": sorted(
            {source_id for item in resolved_inputs for source_id in item["source_ids"]}
        ),
    }


def _validate_ttm_provenance(formula_id: str, inputs: list[dict[str, Any]]) -> None:
    if formula_id == "ttm_sum_v1":
        if len(inputs) != 4:
            raise InputError("ttm_sum_v1 requires exactly four fiscal-quarter components")
        ordered: list[tuple[int, int, date]] = []
        for item in inputs:
            match = TTM_PERIOD.fullmatch(item["period"])
            assert match is not None
            ordinal = int(match.group("year")) * 4 + int(match.group("quarter")) - 1
            if item["as_of"] is None:
                raise InputError("ttm_sum_v1 financial components require as_of provenance")
            fiscal_year = int(match.group("year"))
            quarter = int(match.group("quarter"))
            as_of = date.fromisoformat(item["as_of"])
            if abs(fiscal_year - as_of.year) > 1:
                raise InputError(
                    "ttm_sum_v1 fiscal-quarter labels must be within one calendar year of as_of"
                )
            if quarter == 4 and as_of.year != fiscal_year:
                raise InputError(
                    "ttm_sum_v1 FYyyyy-Q4 period-end year must equal the declared fiscal year"
                )
            ordered.append((ordinal, fiscal_year, as_of))
        ordered.sort()
        ordinals = [item[0] for item in ordered]
        if ordinals != list(range(ordinals[0], ordinals[0] + 4)):
            raise InputError("ttm_sum_v1 periods must be four unique consecutive fiscal quarters")
        dates = [item[2] for item in ordered]
        if any(current >= following for current, following in zip(dates, dates[1:])):
            raise InputError("ttm_sum_v1 as_of dates must strictly increase with fiscal-quarter order")
        spacings = [(following - current).days for current, following in zip(dates, dates[1:])]
        if any(not 70 <= spacing <= 115 for spacing in spacings):
            raise InputError(
                "ttm_sum_v1 adjacent fiscal-quarter as_of dates must be 70-115 days apart"
            )
    elif formula_id == "ttm_bridge_v1":
        if len(inputs) != 3:
            raise InputError("ttm_bridge_v1 requires exactly three components")
        by_role = {item["role"]: item for item in inputs}
        if set(by_role) != TTM_BRIDGE_ROLES:
            raise InputError("ttm_bridge_v1 roles must be exactly: current_ytd, fy, prior_ytd")
        fy, current, prior = by_role["fy"], by_role["current_ytd"], by_role["prior_ytd"]
        if fy["duration_quarters"] != 4:
            raise InputError("ttm_bridge_v1 fy duration_quarters must be 4")
        if not 1 <= current["duration_quarters"] <= 3 or current["duration_quarters"] != prior["duration_quarters"]:
            raise InputError("ttm_bridge_v1 current/prior YTD durations must be equal and from 1 through 3")
        if fy["fiscal_year"] != prior["fiscal_year"] or current["fiscal_year"] != prior["fiscal_year"] + 1:
            raise InputError("ttm_bridge_v1 requires FY/prior in one fiscal year and current in the adjacent year")
        if any(item["as_of"] is None for item in (fy, current, prior)):
            raise InputError("ttm_bridge_v1 financial components require as_of provenance")
        fy_date = date.fromisoformat(fy["as_of"])
        current_date = date.fromisoformat(current["as_of"])
        prior_date = date.fromisoformat(prior["as_of"])
        if fy_date.year != fy["fiscal_year"]:
            raise InputError(
                "ttm_bridge_v1 annual FY period-end year must equal its declared fiscal_year"
            )
        for item, item_date in ((fy, fy_date), (current, current_date), (prior, prior_date)):
            if abs(item["fiscal_year"] - item_date.year) > 1:
                raise InputError(
                    "ttm_bridge_v1 fiscal years must be within one calendar year of component as_of"
                )
        if not prior_date < fy_date < current_date:
            raise InputError("ttm_bridge_v1 as_of ordering must be prior_ytd < fy < current_ytd")
        year_over_year_days = (current_date - prior_date).days
        if not 350 <= year_over_year_days <= 385:
            raise InputError(
                "ttm_bridge_v1 current/prior YTD as_of dates must be 350-385 days apart"
            )
        remaining_quarters = 4 - prior["duration_quarters"]
        prior_to_fy = (fy_date - prior_date).days
        fy_to_current = (current_date - fy_date).days
        prior_window = (13 * remaining_quarters * 7 - 35, 13 * remaining_quarters * 7 + 35)
        current_window = (
            13 * current["duration_quarters"] * 7 - 35,
            13 * current["duration_quarters"] * 7 + 35,
        )
        if not prior_window[0] <= prior_to_fy <= prior_window[1]:
            raise InputError(
                "ttm_bridge_v1 prior_ytd to FY spacing is incompatible with duration_quarters"
            )
        if not current_window[0] <= fy_to_current <= current_window[1]:
            raise InputError(
                "ttm_bridge_v1 FY to current_ytd spacing is incompatible with duration_quarters"
            )


def formula_result_for_record(pack: dict[str, Any], record_id: str) -> FormulaResult:
    return _resolve_derived_record(pack, record_id)["result"]


def rounded_reported_value(record: dict[str, Any], computed_value: Decimal) -> Decimal:
    converted = _reported_from_computed(
        computed_value,
        record["computed"]["unit"],
        record["reported"]["unit"],
    )
    quantum = Decimal("1").scaleb(-record["rounding"]["places"])
    return converted.quantize(quantum, rounding=ROUND_HALF_UP)


def _canonical_derived_shape(raw: Any) -> dict[str, Any]:
    issues: list[str] = []
    if not _require_exact_keys(raw, DERIVED_RECORD_KEYS, "derived record", issues):
        raise InputError("; ".join(issues))
    assert isinstance(raw, dict)
    identifier = raw["id"]
    formula_id = raw["formula_id"]
    if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
        issues.append("derived record.id must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}")
    if not isinstance(formula_id, str) or formula_id not in FORMULA_REGISTRY:
        issues.append("derived record.formula_id must name a registered formula")
    raw_inputs = raw["inputs"]
    inputs: list[dict[str, Any]] = []
    if not isinstance(raw_inputs, list) or not raw_inputs:
        issues.append("derived record.inputs must be a nonempty array")
    elif isinstance(formula_id, str) and formula_id in FORMULA_REGISTRY:
        for index, raw_input in enumerate(raw_inputs):
            try:
                inputs.append(_canonical_derived_input(raw_input, formula_id, index))
            except InputError as error:
                issues.append(str(error))
    try:
        computed = _canonical_value_unit(raw["computed"], "derived record.computed")
        reported = _canonical_value_unit(raw["reported"], "derived record.reported", reported=True)
    except InputError as error:
        issues.append(str(error))
        computed = raw["computed"]
        reported = raw["reported"]
    rounding = raw["rounding"]
    rounding_issues: list[str] = []
    if _require_exact_keys(rounding, ROUNDING_KEYS, "derived record.rounding", rounding_issues):
        assert isinstance(rounding, dict)
        if rounding["mode"] != "ROUND_HALF_UP":
            rounding_issues.append("derived record.rounding.mode must be ROUND_HALF_UP")
        if isinstance(rounding["places"], bool) or not isinstance(rounding["places"], int) or not 0 <= rounding["places"] <= 12:
            rounding_issues.append("derived record.rounding.places must be an integer from 0 through 12")
    issues.extend(rounding_issues)
    binding = raw["binding"]
    binding_issues: list[str] = []
    if _require_exact_keys(binding, BINDING_KEYS, "derived record.binding", binding_issues):
        assert isinstance(binding, dict)
        for key in sorted(BINDING_KEYS):
            _nonempty_string(binding[key], f"derived record.binding.{key}", binding_issues)
    issues.extend(binding_issues)
    if issues:
        raise InputError("; ".join(issues))
    assert isinstance(rounding, dict) and isinstance(binding, dict)
    return {
        "id": identifier,
        "formula_id": formula_id,
        "inputs": inputs,
        "computed": computed,
        "reported": reported,
        "rounding": {"mode": "ROUND_HALF_UP", "places": rounding["places"]},
        "binding": {key: binding[key].strip() for key in ("section", "label", "column")},
    }


def canonical_derived_record(raw: Any, pack: dict[str, Any]) -> dict[str, Any]:
    record = _canonical_derived_shape(raw)
    temporary = dict(pack)
    temporary["derived_records"] = dict(pack.get("derived_records", {}))
    temporary["derived_records"][record["id"]] = record
    try:
        return _resolve_derived_record(temporary, record["id"])["record"]
    except (InvalidOperation, PaybackError) as error:
        raise InputError(f"derived record formula is invalid: {error}") from error


def _canonical_basis(raw: Any) -> dict[str, Any]:
    issues: list[str] = []
    if not _require_exact_keys(raw, BASIS_KEYS, "valuation basis", issues):
        raise InputError("; ".join(issues))
    assert isinstance(raw, dict)
    if not _require_exact_keys(raw["price"], PRICE_KEYS, "valuation basis.price", issues):
        raise InputError("; ".join(issues))
    if not _require_exact_keys(raw["shares"], SHARES_KEYS, "valuation basis.shares", issues):
        raise InputError("; ".join(issues))
    price = raw["price"]
    shares = raw["shares"]
    assert isinstance(price, dict) and isinstance(shares, dict)
    try:
        price_value = _canonical_decimal(price["value"], "valuation basis.price.value", positive=True)
        shares_value = _canonical_decimal(shares["value"], "valuation basis.shares.value", positive=True)
        market_date = _canonical_date(price["market_date"], "valuation basis.price.market_date")
        shares_as_of = _canonical_date(shares["as_of"], "valuation basis.shares.as_of")
    except InputError as error:
        issues.append(str(error))
        price_value = price["value"]
        shares_value = shares["value"]
        market_date = price["market_date"]
        shares_as_of = shares["as_of"]
    currency = price["currency"]
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        issues.append("valuation basis.price.currency must be a three-letter uppercase code")
    if not isinstance(price["kind"], str) or price["kind"] not in PRICE_KINDS:
        issues.append(
            "valuation basis.price.kind must be one of: " + ", ".join(sorted(PRICE_KINDS))
        )
    for label, identifier in (
        ("valuation basis.price.source_id", price["source_id"]),
        ("valuation basis.shares.source_id", shares["source_id"]),
    ):
        if not isinstance(identifier, str) or not SOURCE_ID_PATTERN.fullmatch(identifier):
            issues.append(f"{label} must be a canonical sha256 source ID")
    if issues:
        raise InputError("; ".join(issues))
    return {
        "price": {
            "value": price_value,
            "currency": currency,
            "kind": price["kind"],
            "market_date": market_date,
            "source_id": price["source_id"],
        },
        "shares": {
            "value": shares_value,
            "as_of": shares_as_of,
            "source_id": shares["source_id"],
        },
    }


def _path_record(value: str | Path) -> dict[str, str]:
    try:
        path = Path(value)
    except TypeError as error:
        raise InputError("report path must be a string or path") from error
    reject_symlink(path, "report")
    text = os.fspath(path)
    if not text or text == ".":
        raise InputError("report path must be nonempty")
    return {"path": os.fspath(path.expanduser().resolve(strict=False))}


def _stage_payload(
    pack: dict[str, Any],
    stage: str,
    *,
    report_bytes: bytes | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "stage": stage,
        "schema_version": pack["schema_version"],
        "identity": pack["identity"],
        "report": pack["report"],
        "previous_report": pack["previous_report"],
    }
    index = CHECKPOINT_ORDER.index(stage)
    if index >= CHECKPOINT_ORDER.index("sources_ready"):
        payload["sources"] = pack["sources"]
    if index >= CHECKPOINT_ORDER.index("facts_ready"):
        payload["facts"] = pack["facts"]
    if index >= CHECKPOINT_ORDER.index("valuation_locked"):
        payload["valuation_basis"] = pack["valuation_basis"]
    if index >= CHECKPOINT_ORDER.index("matrix_ready"):
        payload.update(
            {
                "derived_records": pack["derived_records"],
                "action_matrix": pack["action_matrix"],
                "evidence_gates": pack["evidence_gates"],
            }
        )
    if index >= CHECKPOINT_ORDER.index("draft_ready"):
        if report_bytes is None:
            report_path = Path(pack["report"]["path"])
            try:
                report_bytes = report_path.read_bytes()
            except OSError as error:
                raise InputError(f"cannot hash report for {stage}: {report_path}: {error}") from error
        payload["report_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    return payload


def checkpoint_hash(
    pack: dict[str, Any],
    stage: str,
    *,
    report_bytes: bytes | None = None,
) -> str:
    return canonical_hash(_stage_payload(pack, stage, report_bytes=report_bytes))


def _clear_checkpoints(pack: dict[str, Any], first: str) -> None:
    start = CHECKPOINT_ORDER.index(first)
    for stage in CHECKPOINT_ORDER[start:]:
        pack["checkpoints"].pop(stage, None)


def build_initial_pack(
    *,
    ticker: str,
    market: str,
    report: str | Path,
    previous_report: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(ticker, str) or not isinstance(market, str):
        raise InputError("ticker and market must be strings")
    if not ticker.strip() or not market.strip():
        raise InputError("ticker and market must be nonempty")
    pack: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "identity": {"ticker": ticker.strip().upper(), "market": market.strip().upper()},
        "report": _path_record(report),
        "previous_report": _path_record(previous_report) if previous_report is not None else None,
        "sources": {},
        "facts": {},
        "derived_records": {},
        "valuation_basis": {"current": None, "revisions": []},
        "action_matrix": [],
        "evidence_gates": {},
        "checkpoints": {},
    }
    pack["checkpoints"]["initialized"] = {
        "upstream_hash": checkpoint_hash(pack, "initialized")
    }
    return pack


def initialize_pack(
    path: Path,
    *,
    ticker: str,
    market: str,
    report: str | Path,
    previous_report: str | Path | None = None,
) -> str:
    reject_symlink(path, "pack")
    pack = build_initial_pack(
        ticker=ticker,
        market=market,
        report=report,
        previous_report=previous_report,
    )
    with pack_write_lock(path):
        if path.exists():
            existing = load_pack(path)
            if existing == pack:
                return "UNCHANGED"
            raise StateConflict(f"pack already exists with different content: {path}")
        write_pack_atomic(path, pack, lock_held=True)
        return "CREATED"


def _source_issues(identifier: str, value: Any) -> list[str]:
    issues: list[str] = []
    label = f"sources[{identifier!r}]"
    if not _require_exact_keys(value, SOURCE_KEYS, label, issues):
        return issues
    assert isinstance(value, dict)
    if identifier != value["source_id"]:
        issues.append(f"{label}.source_id must equal its registry key")
    if not isinstance(identifier, str) or not SOURCE_ID_PATTERN.fullmatch(identifier):
        issues.append(f"{label} key must be a canonical sha256 source ID")
    try:
        canonical = canonicalize_url(value["canonical_url"])
        if canonical != value["canonical_url"]:
            issues.append(f"{label}.canonical_url is not canonical")
        if source_id(canonical) != identifier:
            issues.append(f"{label}.source_id does not match canonical_url")
    except InputError as error:
        issues.append(str(error).replace("source.url", f"{label}.canonical_url"))
    for key in ("title", "publisher"):
        _nonempty_string(value[key], f"{label}.{key}", issues)
    if not isinstance(value["tier"], str) or value["tier"] not in SOURCE_TIERS:
        issues.append(f"{label}.tier is invalid")
    if value["published_date"] is not None:
        _date_issue(value["published_date"], f"{label}.published_date", issues)
    return issues


def _fact_issues(identifier: str, value: Any) -> list[str]:
    try:
        canonical = _canonical_fact(value)
    except InputError as error:
        return [f"facts[{identifier!r}]: {error}"]
    issues: list[str] = []
    if identifier != canonical["fact_id"]:
        issues.append(f"facts[{identifier!r}].fact_id must equal its registry key")
    if canonical != value:
        issues.append(f"facts[{identifier!r}] is not in canonical form")
    return issues


def _derived_record_issues(identifier: str, value: Any, pack: dict[str, Any]) -> list[str]:
    try:
        canonical = _canonical_derived_shape(value)
        resolved = _resolve_derived_record(pack, identifier)
    except (InputError, StateConflict) as error:
        return [f"derived_records[{identifier!r}]: {error}"]
    issues: list[str] = []
    if identifier != canonical["id"]:
        issues.append(f"derived_records[{identifier!r}].id must equal its registry key")
    if canonical != value:
        issues.append(f"derived_records[{identifier!r}] is not in canonical form")
    if resolved["record"] != canonical:
        issues.append(f"derived_records[{identifier!r}] resolution is not canonical")
    return issues


def _forbidden_key_issues(value: Any, path: str = "pack") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if isinstance(key, str) and key.lower() in FORBIDDEN_TELEMETRY_KEYS:
                issues.append(f"forbidden telemetry key: {child_path}")
            issues.extend(_forbidden_key_issues(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(_forbidden_key_issues(child, f"{path}[{index}]"))
    return issues


def _valuation_reference_issues(
    basis: Any,
    label: str,
    sources: dict[str, Any],
) -> list[str]:
    try:
        canonical = _canonical_basis(basis)
    except InputError:
        return []
    return [
        f"{label} references undefined source ID: {identifier}"
        for identifier in sorted(
            {canonical["price"]["source_id"], canonical["shares"]["source_id"]} - set(sources)
        )
    ]


def _action_matrix_issues(entries: Any) -> list[str]:
    """Validate semantic Action Matrix entry schema (Batch 2C).

    Each entry must be a JSON object with exactly `action`, `trigger_type`,
    `condition`, `execution`, and `na`. `action` is one of Buy/Add/Hold/Reduce/
    Sell; `trigger_type` is one of price/valuation/operating/thesis-break;
    `condition` and `execution` are nonempty strings; `na` is a bool that is
    only true for Buy or Add. An empty array remains valid (deferred entries).
    """
    issues: list[str] = []
    if not isinstance(entries, list):
        issues.append("action_matrix must be an array of JSON objects")
        return issues
    for index, entry in enumerate(entries):
        label = f"action_matrix[{index}]"
        if not isinstance(entry, dict):
            issues.append(f"{label} must be an object")
            continue
        if not _require_exact_keys(entry, ACTION_MATRIX_KEYS, label, issues):
            continue
        action = str(entry["action"]).strip().casefold()
        trigger_type = str(entry["trigger_type"]).strip().casefold()
        if action not in ACTION_MATRIX_ACTIONS:
            issues.append(
                f"{label}.action must be one of: Buy, Add, Hold, Reduce, Sell"
            )
        if trigger_type not in ACTION_MATRIX_TRIGGER_TYPES:
            issues.append(
                f"{label}.trigger_type must be one of: price, valuation, operating, thesis-break"
            )
        _nonempty_string(entry["condition"], f"{label}.condition", issues)
        _nonempty_string(entry["execution"], f"{label}.execution", issues)
        if not isinstance(entry["na"], bool):
            issues.append(f"{label}.na must be a boolean")
        elif entry["na"] and action not in ACTION_MATRIX_NA_ACTIONS:
            issues.append(f"{label}.na may be true only for Buy or Add, not '{action}'")
    return issues


def schema_issues(
    pack: dict[str, Any],
    *,
    verify_checkpoint_hashes: bool = True,
    report_bytes: bytes | None = None,
) -> list[str]:
    issues: list[str] = _forbidden_key_issues(pack)
    if not _require_exact_keys(pack, TOP_LEVEL_KEYS, "pack", issues):
        return issues
    if pack["schema_version"] != SCHEMA_VERSION:
        issues.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if _require_exact_keys(pack["identity"], {"ticker", "market"}, "identity", issues):
        _nonempty_string(pack["identity"]["ticker"], "identity.ticker", issues)
        _nonempty_string(pack["identity"]["market"], "identity.market", issues)
    if _require_exact_keys(pack["report"], {"path"}, "report", issues):
        if _nonempty_string(pack["report"]["path"], "report.path", issues):
            report_path = Path(pack["report"]["path"])
            if not report_path.is_absolute():
                issues.append("report.path must be absolute")
            if report_path.is_symlink():
                issues.append("report.path must not be a symlink")
    if pack["previous_report"] is not None and _require_exact_keys(
        pack["previous_report"], {"path"}, "previous_report", issues
    ):
        if _nonempty_string(pack["previous_report"]["path"], "previous_report.path", issues):
            previous_path = Path(pack["previous_report"]["path"])
            if not previous_path.is_absolute():
                issues.append("previous_report.path must be absolute")
            if previous_path.is_symlink():
                issues.append("previous_report.path must not be a symlink")
    if not isinstance(pack["sources"], dict):
        issues.append("sources must be an object keyed by source ID")
    else:
        for identifier, source in sorted(pack["sources"].items()):
            issues.extend(_source_issues(identifier, source))
    if not isinstance(pack["facts"], dict):
        issues.append("facts must be an object keyed by fact ID")
    else:
        for identifier, fact in sorted(pack["facts"].items()):
            issues.extend(_fact_issues(identifier, fact))
            if isinstance(fact, dict) and isinstance(fact.get("source_ids"), list):
                for source_reference in fact["source_ids"]:
                    if isinstance(pack["sources"], dict) and source_reference not in pack["sources"]:
                        issues.append(
                            f"facts[{identifier!r}] references undefined source ID: {source_reference}"
                        )
    if not isinstance(pack["derived_records"], dict):
        issues.append("derived_records must be an object keyed by derived record ID")
    else:
        for identifier, record in sorted(pack["derived_records"].items()):
            issues.extend(_derived_record_issues(identifier, record, pack))
    if pack["evidence_gates"] != {}:
        issues.append("evidence_gates must be an empty object until its later batch")
    issues.extend(_action_matrix_issues(pack["action_matrix"]))
    valuation = pack["valuation_basis"]
    if _require_exact_keys(valuation, {"current", "revisions"}, "valuation_basis", issues):
        if valuation["current"] is not None:
            try:
                if _canonical_basis(valuation["current"]) != valuation["current"]:
                    issues.append("valuation_basis.current is not in canonical form")
            except InputError as error:
                issues.append(str(error))
            if isinstance(pack["sources"], dict):
                issues.extend(
                    _valuation_reference_issues(
                        valuation["current"],
                        "valuation_basis.current",
                        pack["sources"],
                    )
                )
        if not isinstance(valuation["revisions"], list):
            issues.append("valuation_basis.revisions must be an array")
        else:
            for index, revision in enumerate(valuation["revisions"]):
                label = f"valuation_basis.revisions[{index}]"
                if not _require_exact_keys(revision, {"old", "new", "reason"}, label, issues):
                    continue
                try:
                    old = _canonical_basis(revision["old"])
                    new = _canonical_basis(revision["new"])
                    if old != revision["old"] or new != revision["new"]:
                        issues.append(f"{label} is not in canonical form")
                except InputError as error:
                    issues.append(f"{label}: {error}")
                if isinstance(pack["sources"], dict):
                    issues.extend(
                        _valuation_reference_issues(revision["old"], f"{label}.old", pack["sources"])
                    )
                    issues.extend(
                        _valuation_reference_issues(revision["new"], f"{label}.new", pack["sources"])
                    )
                _nonempty_string(revision["reason"], f"{label}.reason", issues)
    checkpoints = pack["checkpoints"]
    if not isinstance(checkpoints, dict):
        issues.append("checkpoints must be an object")
    else:
        unknown = sorted(set(checkpoints) - set(CHECKPOINT_ORDER))
        if unknown:
            issues.append(f"checkpoints has unknown stages: {', '.join(unknown)}")
        seen_gap = False
        for stage in CHECKPOINT_ORDER:
            record = checkpoints.get(stage, MISSING)
            if record is MISSING:
                seen_gap = True
                continue
            if seen_gap:
                issues.append(f"checkpoint {stage} exists before its predecessor")
            checkpoint_keys = (
                {"upstream_hash", "manifest_sha256", "report_sha256", "pack_sha256"}
                if stage == "audit_passed"
                else {"upstream_hash"}
            )
            if not _require_exact_keys(record, checkpoint_keys, f"checkpoints.{stage}", issues):
                continue
            if stage == "audit_passed":
                for hash_key in ("manifest_sha256", "report_sha256", "pack_sha256"):
                    if not isinstance(record[hash_key], str) or not HASH_PATTERN.fullmatch(record[hash_key]):
                        issues.append(f"checkpoints.audit_passed.{hash_key} must be a SHA-256 hex digest")
            if not isinstance(record["upstream_hash"], str) or not HASH_PATTERN.fullmatch(
                record["upstream_hash"]
            ):
                issues.append(f"checkpoints.{stage}.upstream_hash must be a SHA-256 hex digest")
            elif verify_checkpoint_hashes:
                try:
                    expected = checkpoint_hash(pack, stage, report_bytes=report_bytes)
                except InputError as error:
                    issues.append(str(error))
                else:
                    if record["upstream_hash"] != expected:
                        issues.append(f"checkpoint {stage} is stale for its canonical upstream inputs")
    return issues


def _require_mutable_pack(path: Path) -> dict[str, Any]:
    pack = load_pack(path)
    issues = schema_issues(pack, verify_checkpoint_hashes=False)
    if issues:
        raise InputError("pack schema invalid: " + "; ".join(issues))
    return pack


def issues_exit_code(issues: list[str]) -> int:
    """Return 1 for valid-state conflicts and 2 for malformed pack structure."""
    state_markers = (
        "references undefined source ID",
        "is stale for its canonical upstream inputs",
        "exists before its predecessor",
    )
    return 1 if issues and all(any(marker in issue for marker in state_markers) for issue in issues) else 2


def add_source(pack: dict[str, Any], raw: Any) -> str:
    source = _canonical_source(raw)
    identifier = source["source_id"]
    existing = pack["sources"].get(identifier)
    if existing is not None:
        if existing == source:
            return "UNCHANGED"
        raise StateConflict(
            f"source metadata conflicts with existing canonical URL: {source['canonical_url']}"
        )
    pack["sources"][identifier] = source
    _clear_checkpoints(pack, "sources_ready")
    return "UPDATED"


def add_fact(pack: dict[str, Any], raw: Any) -> str:
    fact = _canonical_fact(raw)
    identifier = fact["fact_id"]
    existing = pack["facts"].get(identifier)
    if existing is not None:
        if existing == fact:
            return "UNCHANGED"
        raise StateConflict(f"fact ID conflicts with existing metadata: {identifier}")
    pack["facts"][identifier] = fact
    _clear_checkpoints(pack, "facts_ready")
    return "UPDATED"


def add_derived_record(pack: dict[str, Any], raw: Any) -> str:
    record = canonical_derived_record(raw, pack)
    identifier = record["id"]
    existing = pack["derived_records"].get(identifier)
    if existing is not None:
        if existing == record:
            return "UNCHANGED"
        raise StateConflict(f"derived record ID conflicts with existing metadata: {identifier}")
    pack["derived_records"][identifier] = record
    _clear_checkpoints(pack, "matrix_ready")
    return "UPDATED"


def _require_current_predecessors(pack: dict[str, Any], stage: str) -> None:
    index = CHECKPOINT_ORDER.index(stage)
    for predecessor in CHECKPOINT_ORDER[:index]:
        record = pack["checkpoints"].get(predecessor)
        if record is None:
            raise StateConflict(f"checkpoint {stage} requires predecessor {predecessor}")
        expected_predecessor = checkpoint_hash(pack, predecessor)
        if record != {"upstream_hash": expected_predecessor}:
            raise StateConflict(
                f"checkpoint {stage} requires CURRENT predecessor {predecessor}"
            )


def set_checkpoint(pack: dict[str, Any], stage: str) -> str:
    if stage not in CHECKPOINT_ORDER:
        raise InputError(f"unknown checkpoint: {stage}")
    if stage == "audit_passed":
        raise InputError("audit_passed can only be written by a successful Audit v5 verdict")
    _require_current_predecessors(pack, stage)
    if stage == "sources_ready" and not pack["sources"]:
        raise StateConflict("sources_ready requires at least one source")
    if stage == "facts_ready":
        if not pack["facts"]:
            raise StateConflict("facts_ready requires at least one fact")
        undefined = sorted(
            {
                identifier
                for fact in pack["facts"].values()
                for identifier in fact["source_ids"]
                if identifier not in pack["sources"]
            }
        )
        if undefined:
            raise StateConflict("facts_ready has undefined source IDs: " + ", ".join(undefined))
    if stage == "valuation_locked" and pack["valuation_basis"]["current"] is None:
        raise StateConflict("valuation_locked requires a valuation basis")
    expected = checkpoint_hash(pack, stage)
    existing = pack["checkpoints"].get(stage)
    if existing == {"upstream_hash": expected}:
        return "UNCHANGED"
    if existing is not None:
        _clear_checkpoints(pack, stage)
    pack["checkpoints"][stage] = {"upstream_hash": expected}
    return "UPDATED"


def mark_audit_passed(
    pack: dict[str, Any],
    *,
    manifest_sha256: str,
    report_sha256: str,
    pack_sha256: str,
    report_bytes: bytes,
) -> None:
    for label, value in (
        ("manifest_sha256", manifest_sha256),
        ("report_sha256", report_sha256),
        ("pack_sha256", pack_sha256),
    ):
        if not isinstance(value, str) or not HASH_PATTERN.fullmatch(value):
            raise InputError(f"audit_passed {label} must be a SHA-256 hex digest")
    expected_report = hashlib.sha256(report_bytes).hexdigest()
    if report_sha256 != expected_report:
        raise StateConflict("audit_passed report hash does not match the verified snapshot")
    draft = pack.get("checkpoints", {}).get("draft_ready")
    expected_draft = {"upstream_hash": checkpoint_hash(pack, "draft_ready", report_bytes=report_bytes)}
    if draft != expected_draft:
        raise StateConflict("audit_passed requires a CURRENT draft_ready snapshot")
    pack["checkpoints"]["audit_passed"] = {
        "upstream_hash": checkpoint_hash(pack, "audit_passed", report_bytes=report_bytes),
        "manifest_sha256": manifest_sha256,
        "report_sha256": report_sha256,
        "pack_sha256": pack_sha256,
    }


def lock_valuation(pack: dict[str, Any], raw: Any) -> str:
    basis = _canonical_basis(raw)
    undefined = sorted(
        {
            basis["price"]["source_id"],
            basis["shares"]["source_id"],
        }
        - set(pack["sources"])
    )
    if undefined:
        raise StateConflict("valuation basis has undefined source IDs: " + ", ".join(undefined))
    current = pack["valuation_basis"]["current"]
    if current is not None and current != basis:
        raise StateConflict("valuation basis is locked; use revise-valuation with a reason")
    if current is None:
        pack["valuation_basis"]["current"] = basis
    checkpoint_status = set_checkpoint(pack, "valuation_locked")
    if current == basis and checkpoint_status == "UNCHANGED":
        return "UNCHANGED"
    return "UPDATED"


def revise_valuation(pack: dict[str, Any], raw: Any, reason: str) -> str:
    if not isinstance(reason, str) or not reason.strip():
        raise InputError("revision reason must be nonempty")
    current = pack["valuation_basis"]["current"]
    if current is None or "valuation_locked" not in pack["checkpoints"]:
        raise StateConflict("cannot revise valuation before a basis is locked")
    _require_current_predecessors(pack, "valuation_locked")
    basis = _canonical_basis(raw)
    undefined = sorted(
        {
            basis["price"]["source_id"],
            basis["shares"]["source_id"],
        }
        - set(pack["sources"])
    )
    if undefined:
        raise StateConflict("valuation basis has undefined source IDs: " + ", ".join(undefined))
    if basis == current:
        return "UNCHANGED"
    pack["valuation_basis"]["revisions"].append(
        {"old": current, "new": basis, "reason": reason.strip()}
    )
    pack["valuation_basis"]["current"] = basis
    _clear_checkpoints(pack, "valuation_locked")
    return "UPDATED"


def status_payload(pack: dict[str, Any]) -> dict[str, Any]:
    issues = schema_issues(pack)
    stages = []
    first_incomplete: str | None = None
    for stage in CHECKPOINT_ORDER:
        record = pack.get("checkpoints", {}).get(stage) if isinstance(pack.get("checkpoints"), dict) else None
        if record is None:
            state = "MISSING"
        else:
            try:
                state = "CURRENT" if record.get("upstream_hash") == checkpoint_hash(pack, stage) else "STALE"
            except (AttributeError, InputError, KeyError, TypeError):
                state = "STALE"
        if first_incomplete is None and state != "CURRENT":
            first_incomplete = stage
        stages.append({"name": stage, "state": state})
    return {
        "schema_version": pack.get("schema_version"),
        "valid": not issues,
        "issues": issues,
        "checkpoints": stages,
        "next_checkpoint": first_incomplete,
    }


def _mutate_pack(path: Path, operation: Any) -> str:
    with pack_write_lock(path):
        pack = _require_mutable_pack(path)
        outcome = operation(pack)
        if outcome == "UNCHANGED":
            return outcome
        write_pack_atomic(path, pack, lock_held=True)
        return outcome


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage deterministic research-pack-v1 recovery checkpoints."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--pack", required=True, type=Path)
    init.add_argument("--ticker", required=True)
    init.add_argument("--market", required=True)
    init.add_argument("--report", required=True, type=Path)
    init.add_argument("--previous-report", type=Path)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--pack", required=True, type=Path)

    source_add = subparsers.add_parser("source-add")
    source_add.add_argument("--pack", required=True, type=Path)
    source_add.add_argument("--source", required=True, type=Path)

    fact_add = subparsers.add_parser("fact-add")
    fact_add.add_argument("--pack", required=True, type=Path)
    fact_add.add_argument("--fact", required=True, type=Path)

    derived_add = subparsers.add_parser("derived-add")
    derived_add.add_argument("--pack", required=True, type=Path)
    derived_add.add_argument("--record", required=True, type=Path)

    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint.add_argument("--pack", required=True, type=Path)
    checkpoint.add_argument("--name", required=True, choices=CHECKPOINT_ORDER[:-1])

    lock = subparsers.add_parser("valuation-lock")
    lock.add_argument("--pack", required=True, type=Path)
    lock.add_argument("--basis", required=True, type=Path)

    revise = subparsers.add_parser("revise-valuation")
    revise.add_argument("--pack", required=True, type=Path)
    revise.add_argument("--basis", required=True, type=Path)
    revise.add_argument("--reason", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--pack", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "init":
            outcome = initialize_pack(
                args.pack,
                ticker=args.ticker,
                market=args.market,
                report=args.report,
                previous_report=args.previous_report,
            )
            print(f"{outcome}: {args.pack}")
            return 0
        if args.command == "validate":
            pack = load_pack(args.pack)
            issues = schema_issues(pack)
            if issues:
                for issue in issues:
                    print(f"ERROR: {issue}", file=os.sys.stderr)
                return issues_exit_code(issues)
            print(f"VALID: {args.pack}")
            return 0
        if args.command == "status":
            pack = load_pack(args.pack)
            payload = status_payload(pack)
            print(canonical_json_bytes(payload, pretty=True).decode(), end="")
            return 0 if payload["valid"] else issues_exit_code(payload["issues"])
        if args.command == "source-add":
            raw = _load_json(args.source, "source")
            outcome = _mutate_pack(args.pack, lambda pack: add_source(pack, raw))
        elif args.command == "fact-add":
            raw = _load_json(args.fact, "fact")
            outcome = _mutate_pack(args.pack, lambda pack: add_fact(pack, raw))
        elif args.command == "derived-add":
            raw = _load_json(args.record, "derived record")
            outcome = _mutate_pack(args.pack, lambda pack: add_derived_record(pack, raw))
        elif args.command == "checkpoint":
            outcome = _mutate_pack(args.pack, lambda pack: set_checkpoint(pack, args.name))
        elif args.command == "valuation-lock":
            raw = _load_json(args.basis, "valuation basis")
            outcome = _mutate_pack(args.pack, lambda pack: lock_valuation(pack, raw))
        elif args.command == "revise-valuation":
            raw = _load_json(args.basis, "valuation basis")
            outcome = _mutate_pack(
                args.pack,
                lambda pack: revise_valuation(pack, raw, args.reason),
            )
        else:  # pragma: no cover - argparse owns command dispatch
            raise InputError(f"unsupported command: {args.command}")
        print(f"{outcome}: {args.pack}")
        return 0
    except StateConflict as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 1
    except InputError as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 2
    except (AttributeError, IndexError, KeyError, TypeError) as error:
        print(f"ERROR: malformed input type: {error}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

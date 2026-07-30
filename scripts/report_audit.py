#!/usr/bin/env python3
"""Manual-only report audit with a hashed manifest and provenance checks.

Adapted from AI Berkshire's MIT-licensed report_audit.py; see
references/third-party-notices.md. This tool never fetches data.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from financial_formulas import CONVERGENCE_TOLERANCE, PaybackError
from research_pack import (
    InputError as ResearchPackInputError,
    canonical_derived_record,
    canonical_hash as pack_canonical_hash,
    canonical_json_bytes as pack_canonical_json_bytes,
    checkpoint_hash,
    formula_result_for_record,
    load_json_bytes,
    load_pack_bytes,
    mark_audit_passed,
    pack_write_lock,
    rounded_reported_value,
    schema_issues,
    write_pack_atomic,
)

from validation_common import (
    ACTION_MATRIX_COLUMNS,
    classify_discrepancy,
    decimal,
    direct_discrepancy_percent,
    find_action_matrix_table,
    iter_markdown_tables,
    symmetric_spread_percent,
)


VERSION = 4
V5_VERSION = 5
MINIMUM_RATIO = Decimal("0.15")
AMOUNT = re.compile(r"^(?P<sign>[+-]?)(?P<currency>[$¥€£]?)(?P<postsign>[+-]?)(?P<number>(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?|\.\d+)(?P<suffix>%|[xX]|倍|万亿|亿(?:元|美元|港元)?|[BMT])?$", re.I)
PAREN_INNER = re.compile(r"^\((?P<inner>.+)\)(?P<suffix>%|[xX]|倍|万亿|亿(?:元|美元|港元)?|[BMT])$", re.I)
V5_AMOUNT = re.compile(r"^(?P<sign>[+-]?)(?P<currency>[$¥€£]?)(?P<postsign>[+-]?)(?P<number>(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?|\.\d+)(?P<suffix>%|[xX]|倍|/share|万亿|亿(?:元|美元|港元)?|[BMT])?$", re.I)
V5_PAREN_INNER = re.compile(r"^\((?P<inner>.+)\)(?P<suffix>%|[xX]|倍|/share|万亿|亿(?:元|美元|港元)?|[BMT])$", re.I)
EXCLUDED_HEADERS = ("date", "日期", "时间", "source", "来源", "层级", "tier", "口径", "basis", "判断", "judgment", "verdict", "说明", "description", "备注", "note", "可信度", "confidence")
OFFICIAL_HOSTS = ("sec.gov", "federalreserve.gov", "treasury.gov", "hkexnews.hk", "cninfo.com.cn", "sse.com.cn", "szse.cn", "nyse.com", "nasdaq.com")
TIER2_HOSTS = ("stockanalysis.com", "macrotrends.net", "finance.yahoo.com", "koyfin.com", "tikr.com", "aastocks.com", "eastmoney.com", "10jqka.com.cn")
REJECTED_HOSTS = ("reddit.com", "medium.com", "substack.com", "blogspot.", "wordpress.", "x.com", "twitter.com", "facebook.com")
CANONICAL_PORTFOLIO_HOST = "github.com"
CANONICAL_PORTFOLIO_PATH = "/xiangyingchang/portfolio-dashboard"
ALIASES = {
    "market_price": ("current price", "close price", "现价", "当前价格", "收盘价", "股价"),
    "market_cap": ("market cap", "市值"), "shares": ("shares outstanding", "share count", "total shares", "总股本", "稀释股数", "股本"),
    "revenue": ("revenue", "营业收入", "营收", "收入"), "net_income": ("net income", "净利润", "归母净利润"),
    "ttm_eps": ("ttm eps", "ttm每股收益"),
    "ttm_fcf_per_share": ("ttm fcf/share", "ttm fcf per share", "每股ttm fcf", "ttm每股自由现金流"),
    "eps": ("eps", "每股收益"), "fcf_per_share": ("fcf per share", "free cash flow per share", "每股自由现金流", "fcf/股"),
    "portfolio_weight": ("estimated portfolio weight", "portfolio weight", "估算组合权重", "组合权重"),
    "cash": ("cash", "现金", "现金及等价物"), "debt": ("debt", "债务", "有息负债"),
}
YIELD_ALIASES = ("10y government yield", "10y treasury yield", "10y treasury", "10年国债", "10 年国债", "10y国债", "美国10y国债", "us10ytreasury")
MANDATORY_SINGLE_FIELDS = (
    "market_price",
    "shares",
    "market_cap",
    "cash",
    "debt",
    "ttm_eps",
    "ttm_fcf_per_share",
    "government_yield",
    "government_yield_x2",
    "portfolio_weight",
)
MANDATORY_ALL_FIELDS = ("payback_eps", "payback_fcf", "payback_ev_fcf")
REQUIRED_RECOGNITION_FIELDS = (*MANDATORY_SINGLE_FIELDS, *MANDATORY_ALL_FIELDS)
COMPOSITE_LABEL_SEPARATOR = re.compile(r"[/／+＋&＆]|及|和|与|、")
DECISION_LABEL_HINT = re.compile(
    r"^(?:当前报价|current\s+quote)(?:\s*[（(].*[）)])?$",
    re.I,
)


def error(message: str) -> ValueError:
    return ValueError(message)


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def strict_json_identity(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return False
        return all(strict_json_identity(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            strict_json_identity(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return left == right


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _parse_numeric(
    text: str,
    amount_pattern: re.Pattern[str],
    parenthesized_pattern: re.Pattern[str],
) -> tuple[str, str] | None:
    value = re.sub(r"\s+", "", text.strip())
    if not value:
        return None
    negative = False
    if value.startswith("(") and value.endswith(")"):
        negative, value = True, value[1:-1]
    else:
        parenthesized = parenthesized_pattern.fullmatch(value)
        if parenthesized:
            negative = True
            value = f"{parenthesized.group('inner')}{parenthesized.group('suffix')}"
    match = amount_pattern.fullmatch(value)
    if not match:
        return None
    signs = f"{match.group('sign')}{match.group('postsign')}"
    if "+" in signs and "-" in signs:
        return None
    negative = negative or "-" in signs
    number = decimal(match.group("number"))
    if negative:
        number = -abs(number)
    unit = f"{match.group('currency') or ''}{match.group('suffix') or ''}"
    return str(number), unit


def parse_numeric(text: str) -> tuple[str, str] | None:
    """Parse the frozen manifest-v4 full-cell numeric grammar."""
    return _parse_numeric(text, AMOUNT, PAREN_INNER)


def parse_numeric_v5(text: str) -> tuple[str, str] | None:
    return _parse_numeric(text, V5_AMOUNT, V5_PAREN_INNER)


def canonical_report_unit(unit: str) -> str | None:
    normalized_unit = unit.replace("X", "x")
    return {
        "$": "USD",
        "$B": "USD_B",
        "$/share": "USD/share",
        "%": "%",
        "x": "x",
        "倍": "x",
    }.get(normalized_unit)


def eligible_header(header: str) -> bool:
    key = normalized(re.sub(r"[*`_]", "", header))
    return bool(key) and not any(token in key for token in EXCLUDED_HEADERS)


def payback_field(section: str, row_label: str, column: str) -> str | None:
    if not re.match(r"##\s*4\.", section, re.I):
        return None
    row, column_key = normalized(row_label), normalized(column)
    growth_column = any(token in column_key for token in ("所需g", "requiredg", "growth", "cagr", "年增速", "年化g")) or ("payback" in column_key and column_key.endswith("g"))
    if not growth_column:
        return None
    metric = column_key if any(token in column_key for token in ("eps", "fcf")) else row
    if "ev/fcf" in metric or "evfcf" in metric:
        return "payback_ev_fcf"
    if "fcf" in metric or "自由现金流" in metric:
        return "payback_fcf"
    if "eps" in metric or "每股收益" in metric:
        return "payback_eps"
    return None


def is_x2_yield(label: str) -> bool:
    value = normalized(label).replace("×", "x")
    return any(token in value for token in ("x2", "×2", "2x", "double"))


def classification_matches(section: str, row_label: str, column: str) -> list[str]:
    """Return all classifier matches in extraction precedence order."""
    payback = payback_field(section, row_label, column)
    if payback:
        return [payback]
    context, label = normalized(f"{row_label} {column}"), normalized(row_label)
    if any(normalized(alias) in label for alias in YIELD_ALIASES):
        return ["government_yield_x2" if is_x2_yield(row_label) else "government_yield"]
    matches = [
        field
        for field, aliases in ALIASES.items()
        if any(normalized(alias) in context for alias in aliases)
    ]
    return matches or ["other"]


def looks_like_unrecognized_decision_label(label: str) -> bool:
    """Conservatively flag mandatory-looking labels the classifier did not accept."""
    return bool(DECISION_LABEL_HINT.search(label))


def recognize_fields(report: str) -> dict[str, Any]:
    """Recognize mandatory field labels even when their value cells are placeholders."""
    recognized: dict[str, list[dict[str, Any]]] = {}
    unrecognized: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    for table in iter_markdown_tables(report):
        section = table["section"]
        in_decision_section = bool(
            re.match(r"##\s*4\.", section, re.I)
            or re.search(r"Evidence Ledger|证据台账|证据账本", section, re.I)
        )
        if not in_decision_section:
            continue
        headers = table["headers"]
        for row in table["rows"]:
            cells = row["cells"]
            row_label = re.sub(r"[*`_]", "", cells[0]).strip() if cells else ""
            row_fields: set[str] = set()
            row_candidates: set[str] = set()
            for column_index in range(1, max(len(cells), len(headers))):
                column = headers[column_index] if column_index < len(headers) else f"column-{column_index}"
                if not eligible_header(column):
                    continue
                matches = classification_matches(section, row_label, column)
                field = matches[0]
                if field in REQUIRED_RECOGNITION_FIELDS:
                    row_fields.add(field)
                    recognized.setdefault(field, []).append(
                        {
                            "line_number": row["line_number"],
                            "label": row_label,
                            "column": column,
                            "section": section,
                        }
                    )
                row_candidates.update(candidate for candidate in matches if candidate in REQUIRED_RECOGNITION_FIELDS)
            if len(row_candidates) > 1 and COMPOSITE_LABEL_SEPARATOR.search(row_label):
                ambiguous.append(
                    {
                        "line_number": row["line_number"],
                        "label": row_label,
                        "categories": sorted(row_candidates),
                        "section": section,
                    }
                )
            elif not row_fields and looks_like_unrecognized_decision_label(row_label):
                unrecognized.append(
                    {
                        "line_number": row["line_number"],
                        "label": row_label,
                        "section": section,
                    }
                )
    recognized_categories = [field for field in REQUIRED_RECOGNITION_FIELDS if field in recognized]
    missing = [field for field in REQUIRED_RECOGNITION_FIELDS if field not in recognized]
    return {
        "recognized_mandatory_categories": recognized_categories,
        "missing_required_categories": missing,
        "unrecognized_decision_label_rows": unrecognized,
        "ambiguous_decision_label_rows": ambiguous,
        "status": "PASS" if not missing and not unrecognized and not ambiguous else "FAIL",
    }


def extract_points(report: str) -> list[dict[str, Any]]:
    points = []
    for table in iter_markdown_tables(report):
        section, headers = table["section"], table["headers"]
        for row in table["rows"]:
            cells = row["cells"]
            row_label = re.sub(r"[*`_]", "", cells[0]).strip() if cells else ""
            for column_index, cell in enumerate(cells[1:], start=1):
                column = headers[column_index] if column_index < len(headers) else f"column-{column_index}"
                if not eligible_header(column):
                    continue
                parsed = parse_numeric(cell)
                if not parsed:
                    continue
                value, unit = parsed
                points.append({"field": classification_matches(section, row_label, column)[0], "label": row_label, "column": column, "reported_value": value, "unit": unit, "line_number": row["line_number"], "section": section})
    return points


def tier_policy(field: str) -> dict[str, Any]:
    if field == "portfolio_weight":
        return {"allowed_tiers": ["Internal"], "tier2_requires_secondary": False}
    market_or_yield = field in {"market_price", "government_yield", "government_yield_x2"}
    return {"allowed_tiers": ["Tier 1", "Tier 2"] if market_or_yield else ["Tier 1"], "tier2_requires_secondary": market_or_yield}


def build_manifest(report: str, ratio: Decimal) -> dict[str, Any]:
    if not MINIMUM_RATIO <= ratio <= Decimal("1"):
        raise error("ratio must be >= 0.15 and <= 1")
    points, report_sha256 = extract_points(report), hashlib.sha256(report.encode()).hexdigest()
    target = math.ceil(len(points) * float(ratio))
    selected: dict[tuple[int, str, str], dict[str, Any]] = {}
    for field in MANDATORY_SINGLE_FIELDS:
        candidates = [point for point in points if point["field"] == field]
        if candidates:
            point = min(candidates, key=lambda item: (item["line_number"], item["column"]))
            selected[(point["line_number"], point["label"], point["column"])] = point
    for point in points:
        if point["field"] in MANDATORY_ALL_FIELDS:
            selected[(point["line_number"], point["label"], point["column"])] = point
    for point in sorted(points, key=digest):
        if len(selected) >= target:
            break
        selected[(point["line_number"], point["label"], point["column"])] = point
    eligible_universe_ids = sorted(digest({"report_sha256": report_sha256, **point}) for point in points)
    items = []
    for point in sorted(selected.values(), key=lambda item: (item["line_number"], item["column"])):
        item = {**point, "required_tier_policy": tier_policy(point["field"])}
        item["id"] = digest({"report_sha256": report_sha256, **point})
        items.append(item)
    body = {"version": VERSION, "report_sha256": report_sha256, "requested_ratio": str(ratio), "actual_ratio": str(Decimal(len(items)) / Decimal(len(points))) if points else "0", "eligible_numeric_table_cells": len(points), "eligible_universe_ids": eligible_universe_ids, "items": items}
    return {**body, "manifest_sha256": digest(body)}


def _binding_cells(report: str, binding: dict[str, str]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for table in iter_markdown_tables(report):
        if table["section"] != binding["section"]:
            continue
        headers = table["headers"]
        column_indexes = [
            index for index, header in enumerate(headers) if header == binding["column"]
        ]
        for row in table["rows"]:
            cells = row["cells"]
            label = re.sub(r"[*`_]", "", cells[0]).strip() if cells else ""
            if label != binding["label"]:
                continue
            for column_index in column_indexes:
                if column_index < len(cells):
                    matches.append(
                        {
                            "raw": cells[column_index],
                            "line_number": row["line_number"],
                            "column_index": column_index,
                        }
                    )
    return matches


def _reject_symlink(path: Path, label: str) -> None:
    if path.is_symlink():
        raise error(f"{label} path must not be a symlink: {path}")


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _require_distinct_paths(paths: list[tuple[str, Path]]) -> None:
    seen: dict[Path, str] = {}
    for label, path in paths:
        resolved = _resolved(path)
        if resolved in seen:
            raise error(f"{label} path must be distinct from {seen[resolved]} path")
        seen[resolved] = label


@dataclass(frozen=True)
class AuditV5Snapshot:
    report_path: Path
    pack_path: Path
    report_bytes: bytes
    report: str
    pack_bytes: bytes
    pack: dict[str, Any]

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.report_path, Path) or not isinstance(self.pack_path, Path):
            raise error("AuditV5Snapshot paths must be Path instances")
        _reject_symlink(self.report_path, "report")
        _reject_symlink(self.pack_path, "pack")
        _require_distinct_paths([("report", self.report_path), ("pack", self.pack_path)])
        try:
            decoded_report = self.report_bytes.decode("utf-8")
        except (AttributeError, UnicodeError) as exc:
            raise error("AuditV5Snapshot report_bytes must be valid UTF-8 bytes") from exc
        if decoded_report != self.report:
            raise error("AuditV5Snapshot report text does not match report_bytes")
        parsed_pack = load_pack_bytes(self.pack_bytes, self.pack_path)
        if not strict_json_identity(parsed_pack, self.pack):
            raise error("AuditV5Snapshot parsed pack does not match pack_bytes")
        expected_report = Path(parsed_pack.get("report", {}).get("path", ""))
        if _resolved(self.report_path) != _resolved(expected_report):
            raise error("AuditV5Snapshot report path does not match the pack binding")

    @classmethod
    def load(cls, report_path: Path, pack_path: Path) -> "AuditV5Snapshot":
        _require_distinct_paths([("report", report_path), ("pack", pack_path)])
        _reject_symlink(report_path, "report")
        _reject_symlink(pack_path, "pack")
        report_bytes = report_path.read_bytes()
        pack_bytes = pack_path.read_bytes()
        try:
            report = report_bytes.decode("utf-8")
        except UnicodeError as exc:
            raise error(f"report is not valid UTF-8: {report_path}: {exc}") from exc
        pack = load_pack_bytes(pack_bytes, pack_path)
        expected_report = Path(pack.get("report", {}).get("path", ""))
        if _resolved(report_path) != _resolved(expected_report):
            raise error("--report does not match the report path bound by the pack")
        return cls(
            _resolved(report_path),
            _resolved(pack_path),
            report_bytes,
            report,
            pack_bytes,
            pack,
        )


@dataclass(frozen=True)
class AuditV5VerdictSnapshot:
    audit: AuditV5Snapshot
    manifest_path: Path
    manifest_bytes: bytes
    manifest: dict[str, Any]

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.audit.validate()
        if not isinstance(self.manifest_path, Path):
            raise error("AuditV5VerdictSnapshot manifest_path must be a Path")
        _reject_symlink(self.manifest_path, "manifest")
        _require_distinct_paths(
            [
                ("report", self.audit.report_path),
                ("pack", self.audit.pack_path),
                ("manifest", self.manifest_path),
            ]
        )
        parsed_manifest = load_json_bytes(
            self.manifest_bytes,
            "manifest",
            self.manifest_path,
        )
        if not strict_json_identity(parsed_manifest, self.manifest):
            raise error("AuditV5VerdictSnapshot parsed manifest does not match manifest_bytes")

    @classmethod
    def load(
        cls,
        report_path: Path,
        pack_path: Path,
        manifest_path: Path,
    ) -> "AuditV5VerdictSnapshot":
        _require_distinct_paths(
            [("report", report_path), ("pack", pack_path), ("manifest", manifest_path)]
        )
        _reject_symlink(manifest_path, "manifest")
        audit = AuditV5Snapshot.load(report_path, pack_path)
        manifest_bytes = manifest_path.read_bytes()
        manifest = load_json_bytes(manifest_bytes, "manifest", manifest_path)
        if not isinstance(manifest, dict):
            raise error("manifest must be an object")
        return cls(audit, _resolved(manifest_path), manifest_bytes, manifest)


def _require_current_draft_checkpoint(pack: dict[str, Any], report_bytes: bytes) -> None:
    for stage in ("initialized", "sources_ready", "facts_ready", "valuation_locked", "matrix_ready", "draft_ready"):
        record = pack.get("checkpoints", {}).get(stage)
        if record is None:
            raise error(f"pack checkpoint {stage} is required for Audit v5")
        if record != {"upstream_hash": checkpoint_hash(pack, stage, report_bytes=report_bytes)}:
            raise error(f"pack checkpoint {stage} is stale for Audit v5")


def _validate_v5_record(pack: dict[str, Any], record_id: str) -> None:
    record = pack["derived_records"][record_id]
    canonical = canonical_derived_record(record, pack)
    if canonical != record:
        raise error(f"derived record {record.get('id')!r} is not canonical")
    result = formula_result_for_record(pack, record_id)
    if Decimal(record["computed"]["value"]) != result.value:
        raise error(f"derived record {record['id']!r} computed value differs from formula")
    if record["formula_id"].startswith("payback_"):
        if result.absolute_residual is None or result.absolute_residual > CONVERGENCE_TOLERANCE:
            raise error(f"derived record {record['id']!r} payback absolute residual exceeds tolerance")
        if result.relative_residual is None or result.relative_residual > CONVERGENCE_TOLERANCE:
            raise error(f"derived record {record['id']!r} payback relative residual exceeds tolerance")
    rounded = rounded_reported_value(record, result.value)
    if Decimal(record["reported"]["value"]) != rounded:
        raise error(f"derived record {record['id']!r} reported value differs from declared rounding")


def _report_action_matrix_sets(report: str) -> tuple[set[str], set[str]] | None:
    """Extract the (actions, trigger_types) declared in the report's module 9
    Action Matrix table, or None when the table cannot be located.

    Uses the shared canonical single-table locator in validation_common so the
    audit and lint cannot drift on how the matrix table is found: exactly one
    `### Action Matrix` heading followed by one Markdown table whose header is
    the canonical four-column contract. This is a structural read, not a
    free-text condition parser.
    """
    table = find_action_matrix_table(report)
    if table is None:
        return None
    actions: set[str] = set()
    trigger_types: set[str] = set()
    for row in table["rows"]:
        cells = row["cells"]
        if len(cells) != len(ACTION_MATRIX_COLUMNS):
            continue
        action, trigger_type = (cell.strip() for cell in cells[:2])
        if action:
            actions.add(action.casefold())
        if trigger_type:
            trigger_types.add(trigger_type.casefold())
    return actions, trigger_types


def action_matrix_correspondence_issues(pack: dict[str, Any], report: str) -> list[str]:
    """Semantic Action Matrix cross-check (v5-only, Batch 2C).

    When the pack's `action_matrix` is non-empty, verify the report's module 9
    Action Matrix table is in structural correspondence with the pack entries:
    same action set and same trigger-type set, with no missing or extra actions.
    This is a structural correspondence check, not a free-text condition parser.
    A missing or malformed report table is reported as a correspondence failure.
    """
    entries = pack.get("action_matrix", [])
    if not entries:
        return []
    pack_actions = {
        str(entry["action"]).strip().casefold() for entry in entries
    }
    pack_trigger_types = {
        str(entry["trigger_type"]).strip().casefold() for entry in entries
    }
    report_sets = _report_action_matrix_sets(report)
    if report_sets is None:
        return [
            "pack action_matrix is non-empty but the report has no single "
            "canonical module 9 Action Matrix table to cross-check"
        ]
    report_actions, report_trigger_types = report_sets
    issues: list[str] = []
    missing_actions = sorted(pack_actions - report_actions)
    extra_actions = sorted(report_actions - pack_actions)
    if missing_actions:
        issues.append(
            "Action Matrix correspondence: report is missing actions present in "
            "the pack action_matrix: " + ", ".join(missing_actions)
        )
    if extra_actions:
        issues.append(
            "Action Matrix correspondence: report declares actions absent from "
            "the pack action_matrix: " + ", ".join(extra_actions)
        )
    missing_types = sorted(pack_trigger_types - report_trigger_types)
    extra_types = sorted(report_trigger_types - pack_trigger_types)
    if missing_types:
        issues.append(
            "Action Matrix correspondence: report is missing trigger types "
            "present in the pack action_matrix: " + ", ".join(missing_types)
        )
    if extra_types:
        issues.append(
            "Action Matrix correspondence: report declares trigger types absent "
            "from the pack action_matrix: " + ", ".join(extra_types)
        )
    return issues


def _build_v5_artifacts(
    snapshot: AuditV5Snapshot,
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    snapshot.validate()
    pack, report = snapshot.pack, snapshot.report
    issues = schema_issues(pack, report_bytes=snapshot.report_bytes)
    if issues:
        raise error("pack schema/checkpoint validation failed: " + "; ".join(issues))
    correspondence = action_matrix_correspondence_issues(pack, report)
    if correspondence:
        raise error("; ".join(correspondence))
    _require_current_draft_checkpoint(pack, snapshot.report_bytes)
    records = pack["derived_records"]
    if not records:
        raise error("Audit v5 requires at least one derived record")
    report_sha256 = hashlib.sha256(snapshot.report_bytes).hexdigest()
    base_pack = deepcopy(pack)
    base_pack["checkpoints"].pop("audit_passed", None)
    pack_input_sha256 = pack_canonical_hash(base_pack)
    items: list[dict[str, Any]] = []
    bound: set[tuple[str, str, str]] = set()
    for record_id in sorted(records):
        record = records[record_id]
        _validate_v5_record(pack, record_id)
        binding = record["binding"]
        binding_key = (binding["section"], binding["label"], binding["column"])
        if binding_key in bound:
            raise error("multiple derived records bind the same Markdown table cell")
        bound.add(binding_key)
        cells = _binding_cells(report, binding)
        if len(cells) != 1:
            raise error(
                f"derived record {record_id!r} binding must match exactly one Markdown table cell; "
                f"matched {len(cells)}"
            )
        parsed = parse_numeric_v5(cells[0]["raw"])
        if parsed is None:
            raise error(f"derived record {record_id!r} bound report cell is not an exact numeric value")
        value, raw_unit = parsed
        unit = canonical_report_unit(raw_unit)
        if Decimal(value) != Decimal(record["reported"]["value"]) or unit != record["reported"]["unit"]:
            raise error(f"derived record {record_id!r} bound report cell differs from pack reported value/unit")
        item_body = {
            "derived_record_id": record_id,
            "formula_id": record["formula_id"],
            "binding": binding,
            "record_sha256": digest(record),
            "cell_sha256": digest({"binding": binding, **cells[0]}),
            "reported_value": record["reported"]["value"],
            "reported_unit": record["reported"]["unit"],
        }
        item_id = digest(
            {
                "version": V5_VERSION,
                "report_sha256": report_sha256,
                "pack_input_sha256": pack_input_sha256,
                **item_body,
            }
        )
        items.append({"id": item_id, **item_body})
    audit_binding_sha256 = digest(
        {
            "version": V5_VERSION,
            "report_sha256": report_sha256,
            "pack_input_sha256": pack_input_sha256,
            "items": items,
        }
    )
    base_pack_sha256 = hashlib.sha256(
        pack_canonical_json_bytes(base_pack, pretty=True)
    ).hexdigest()
    final_pack = deepcopy(base_pack)
    mark_audit_passed(
        final_pack,
        manifest_sha256=audit_binding_sha256,
        report_sha256=report_sha256,
        pack_sha256=base_pack_sha256,
        report_bytes=snapshot.report_bytes,
    )
    final_pack_bytes = pack_canonical_json_bytes(final_pack, pretty=True)
    body = {
        "version": V5_VERSION,
        "report_sha256": report_sha256,
        "pack_sha256": hashlib.sha256(final_pack_bytes).hexdigest(),
        "pack_input_sha256": pack_input_sha256,
        "audit_binding_sha256": audit_binding_sha256,
        "items": items,
    }
    return {**body, "manifest_sha256": digest(body)}, final_pack, final_pack_bytes


def build_manifest_v5(snapshot: AuditV5Snapshot) -> dict[str, Any]:
    manifest, _, _ = _build_v5_artifacts(snapshot)
    return manifest


def results_template(manifest: dict[str, Any]) -> dict[str, Any]:
    results = []
    for item in manifest["items"]:
        result: dict[str, Any] = {"id": item["id"], "fresh_value": None, "source": {"name": "", "tier": "", "source_url": "", "authority_type": ""}, "reconciliation": False, "reconciliation_explanation": ""}
        if item["required_tier_policy"]["tier2_requires_secondary"]:
            result["secondary_source"] = {"name": "", "tier": "", "source_url": "", "authority_type": "", "value": None}
        results.append(result)
    return {"manifest_sha256": manifest["manifest_sha256"], "results": results}


def load_json(path: Path) -> Any:
    try:
        return load_json_bytes(path.read_bytes(), "JSON", path)
    except (OSError, ResearchPackInputError) as exc:
        raise error(f"invalid JSON in {path}: {exc}") from exc


def _stage_output(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    return temporary


def _restore_output(path: Path, existed: bool, payload: bytes | None) -> None:
    if not existed:
        path.unlink(missing_ok=True)
        return
    assert payload is not None
    temporary = _stage_output(path, payload)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_outputs_atomic(outputs: list[tuple[Path, bytes]]) -> None:
    originals: dict[Path, tuple[bool, bytes | None]] = {}
    staged: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    for path, _ in outputs:
        _reject_symlink(path, "output")
        originals[path] = (path.exists(), path.read_bytes() if path.exists() else None)
    try:
        for path, payload in outputs:
            staged.append((path, _stage_output(path, payload)))
        for path, temporary in staged:
            os.replace(temporary, path)
            committed.append(path)
        staged = []
    except OSError:
        for path in reversed(committed):
            existed, payload = originals[path]
            _restore_output(path, existed, payload)
        raise
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)


def write_manifest_atomic(path: Path, manifest: dict[str, Any]) -> None:
    payload = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
    write_outputs_atomic([(path, payload)])


def require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise error(f"{name} must be an object")
    return value


def host(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise error("source_url must be an https URL")
    return parsed.hostname.lower()


def approved_portfolio_source(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return False
    path = parsed.path.rstrip("/").casefold()
    return (
        parsed.hostname.casefold() == CANONICAL_PORTFOLIO_HOST
        and path == CANONICAL_PORTFOLIO_PATH
        and parsed.username is None
        and parsed.password is None
        and parsed.port is None
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    )


def source_valid(value: Any, allowed_tiers: list[str], name: str) -> dict[str, Any]:
    source = require_object(value, name)
    required, allowed = {"name", "tier", "source_url", "authority_type"}, {"name", "tier", "source_url", "authority_type", "issuer_domain", "value"}
    if not required.issubset(source) or not set(source).issubset(allowed) or not all(isinstance(source[key], str) and source[key].strip() for key in required):
        raise error(f"{name} requires name, tier, source_url, and authority_type")
    if source["tier"] not in allowed_tiers:
        raise error(f"{name}.tier must be one of {allowed_tiers}")
    source_host = host(source["source_url"])
    if any(blocked in source_host for blocked in REJECTED_HOSTS):
        raise error(f"{name} host is not an allowed evidence source")
    authority = source["authority_type"]
    if source["tier"] == "Tier 1":
        if authority in {"regulator", "exchange"} and not any(source_host == official or source_host.endswith(f".{official}") for official in OFFICIAL_HOSTS):
            raise error(f"{name} Tier 1 regulator/exchange host is not recognized")
        if authority == "company_ir":
            issuer = source.get("issuer_domain")
            if not isinstance(issuer, str) or not issuer.strip() or not (source_host == issuer.lower() or source_host.endswith(f".{issuer.lower()}")):
                raise error(f"{name} company_ir requires confirmed issuer_domain")
        if authority not in {"regulator", "exchange", "company_ir"}:
            raise error(f"{name} Tier 1 authority_type is invalid")
    elif source["tier"] == "Internal":
        if authority != "portfolio_system" or not approved_portfolio_source(source["source_url"]):
            raise error(f"{name} Internal source must be an approved portfolio system")
    elif authority != "tier2_vendor" or not any(source_host == vendor or source_host.endswith(f".{vendor}") for vendor in TIER2_HOSTS):
        raise error(f"{name} Tier 2 host or authority_type is invalid")
    return source


def normalized_vendor_domain(url: str) -> str:
    source_host = host(url)
    for domain in (*TIER2_HOSTS, *OFFICIAL_HOSTS):
        if source_host == domain or source_host.endswith(f".{domain}"):
            return domain
    parts = source_host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else source_host


def validate_manifest(manifest: Any) -> dict[str, Any]:
    manifest = require_object(manifest, "manifest")
    required = {"version", "report_sha256", "requested_ratio", "actual_ratio", "eligible_numeric_table_cells", "eligible_universe_ids", "items", "manifest_sha256"}
    if set(manifest) != required or manifest["version"] != VERSION or not isinstance(manifest["items"], list):
        raise error("manifest has an invalid shape")
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if digest(body) != manifest["manifest_sha256"]:
        raise error("manifest hash does not match its contents")
    return manifest


def validate_manifest_v5(manifest: Any) -> dict[str, Any]:
    manifest = require_object(manifest, "manifest")
    required = {
        "version",
        "report_sha256",
        "pack_sha256",
        "pack_input_sha256",
        "audit_binding_sha256",
        "items",
        "manifest_sha256",
    }
    if set(manifest) != required or manifest.get("version") != V5_VERSION:
        raise error("v5 manifest has an invalid shape")
    for key in (
        "report_sha256",
        "pack_sha256",
        "pack_input_sha256",
        "audit_binding_sha256",
        "manifest_sha256",
    ):
        if not isinstance(manifest[key], str) or not re.fullmatch(r"[0-9a-f]{64}", manifest[key]):
            raise error(f"v5 manifest {key} must be a SHA-256 hex digest")
    if not isinstance(manifest["items"], list) or not manifest["items"]:
        raise error("v5 manifest items must be a nonempty array")
    item_keys = {
        "id",
        "derived_record_id",
        "formula_id",
        "binding",
        "record_sha256",
        "cell_sha256",
        "reported_value",
        "reported_unit",
    }
    ids: list[str] = []
    record_ids: list[str] = []
    bindings: list[tuple[str, str, str]] = []
    for raw_item in manifest["items"]:
        item = require_object(raw_item, "v5 manifest item")
        if set(item) != item_keys:
            raise error("v5 manifest item has an invalid shape")
        if not isinstance(item["binding"], dict) or set(item["binding"]) != {"section", "label", "column"}:
            raise error("v5 manifest item binding has an invalid shape")
        ids.append(item["id"])
        record_ids.append(item["derived_record_id"])
        bindings.append(tuple(item["binding"][key] for key in ("section", "label", "column")))
    if len(ids) != len(set(ids)) or len(record_ids) != len(set(record_ids)):
        raise error("v5 manifest derived records and item IDs must be unique")
    if len(bindings) != len(set(bindings)):
        raise error("v5 manifest bindings must be unique")
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if digest(body) != manifest["manifest_sha256"]:
        raise error("v5 manifest hash does not match its contents")
    return manifest


def evaluate(manifest: Any, payload: Any, report: str) -> dict[str, Any]:
    manifest = validate_manifest(manifest)
    if hashlib.sha256(report.encode()).hexdigest() != manifest["report_sha256"]:
        return {"verdict": "BLOCK", "reason": "current report hash differs from manifest; re-extract"}
    expected = build_manifest(report, decimal(manifest["requested_ratio"]))
    if canonical(expected) != canonical(manifest):
        return {"verdict": "BLOCK", "reason": "manifest does not match reconstruction from current report"}
    if not manifest["eligible_numeric_table_cells"] or not manifest["items"]:
        return {"verdict": "BLOCK", "reason": "no eligible numeric Markdown table cells were extracted"}
    payload = require_object(payload, "results payload")
    if set(payload) != {"manifest_sha256", "results"} or payload["manifest_sha256"] != manifest["manifest_sha256"] or not isinstance(payload["results"], list):
        raise error("results must contain exactly manifest_sha256 and results")
    items = {item["id"]: item for item in manifest["items"]}
    results = [require_object(result, "result") for result in payload["results"]]
    ids = [result.get("id") for result in results]
    if len(ids) != len(set(ids)) or set(ids) != set(items):
        raise error("results must cover every manifest ID exactly once")
    outcomes, overall = [], "PASS"
    for result in results:
        item, policy = items[result["id"]], items[result["id"]]["required_tier_policy"]
        fresh = decimal(result.get("fresh_value"))
        source = source_valid(result.get("source"), policy["allowed_tiers"], "source")
        differences = [direct_discrepancy_percent(decimal(item["reported_value"]), fresh)]
        if source["tier"] == "Tier 2":
            secondary = source_valid(result.get("secondary_source"), ["Tier 1", "Tier 2"], "secondary_source")
            if normalized_vendor_domain(secondary["source_url"]) == normalized_vendor_domain(source["source_url"]):
                raise error("Tier 2 validation requires an independent secondary source")
            secondary_value = decimal(secondary.get("value"))
            differences.append(symmetric_spread_percent([fresh, secondary_value]))
            if not isinstance(result.get("reconciliation"), bool) or not isinstance(result.get("reconciliation_explanation"), str) or not result["reconciliation_explanation"].strip():
                raise error("Tier 2 validation requires boolean reconciliation and explanation")
        maximum = max(differences)
        classification, guidance = classify_discrepancy(maximum)
        status = "PASS" if classification == "CONSISTENT" or (classification == "RECONCILE" and result.get("reconciliation") is True and result.get("reconciliation_explanation", "").strip()) else "RECONCILE" if classification == "RECONCILE" else "BLOCK"
        overall = "BLOCK" if status == "BLOCK" else "RECONCILE_REQUIRED" if status == "RECONCILE" and overall != "BLOCK" else overall
        outcomes.append({"id": result["id"], "field": item["field"], "status": status, "max_difference_pct": str(maximum), "reason": guidance})
    return {"verdict": overall, "manifest_sha256": manifest["manifest_sha256"], "outcomes": outcomes}


def evaluate_v5(snapshot: AuditV5VerdictSnapshot) -> dict[str, Any]:
    snapshot.validate()
    audit = snapshot.audit
    manifest = validate_manifest_v5(snapshot.manifest)
    current_report_sha256 = hashlib.sha256(audit.report_bytes).hexdigest()
    if current_report_sha256 != manifest["report_sha256"]:
        return {"verdict": "BLOCK", "reason": "current report hash differs from v5 manifest; re-extract"}
    with pack_write_lock(audit.pack_path):
        try:
            on_disk_pack_bytes = audit.pack_path.read_bytes()
        except OSError as exc:
            return {"verdict": "BLOCK", "reason": f"cannot re-read pack before audit commit: {exc}"}
        if on_disk_pack_bytes != audit.pack_bytes:
            return {
                "verdict": "BLOCK",
                "reason": "pack changed concurrently after verdict snapshot; audit checkpoint not written",
            }
        base_pack = deepcopy(audit.pack)
        base_pack["checkpoints"].pop("audit_passed", None)
        if pack_canonical_hash(base_pack) != manifest["pack_input_sha256"]:
            return {"verdict": "BLOCK", "reason": "current canonical pack input hash differs from v5 manifest"}
        issues = schema_issues(audit.pack, report_bytes=audit.report_bytes)
        if issues:
            return {"verdict": "BLOCK", "reason": "pack schema/checkpoint validation failed: " + "; ".join(issues)}
        try:
            expected, completed_pack, completed_pack_bytes = _build_v5_artifacts(audit)
        except (InvalidOperation, PaybackError, ValueError, KeyError, TypeError) as exc:
            return {"verdict": "BLOCK", "reason": str(exc)}
        if canonical(expected) != canonical(manifest):
            return {"verdict": "BLOCK", "reason": "v5 manifest does not match current report and pack reconstruction"}
        already_persisted = "audit_passed" in audit.pack.get("checkpoints", {})
        if already_persisted and audit.pack_bytes != completed_pack_bytes:
            return {
                "verdict": "BLOCK",
                "reason": "persisted audit_passed pack bytes differ from the manifest-bound final pack",
            }
        outcomes = [
            {
                "id": item["id"],
                "derived_record_id": item["derived_record_id"],
                "formula_id": item["formula_id"],
                "status": "PASS",
            }
            for item in manifest["items"]
        ]
        outcome = {
            "verdict": "PASS",
            "manifest_sha256": manifest["manifest_sha256"],
            "outcomes": outcomes,
        }
        if not already_persisted:
            write_pack_atomic(audit.pack_path, completed_pack, lock_held=True)
        return outcome


def self_test() -> int:
    report = """## Evidence Ledger\n| Data | Value | Alt |\n|---|---:|---:|\n| Current price | $10 | $10 |\n| Revenue | ($0.80)B | -$0.80B |\n| US 10Y government yield | 4.5% | |\n| US 10Y government yield ×2 | 9.0% | |\n\n## 4. Valuation\n| Rate | EPS required g |\n|---|---:|\n| 10Y government yield ×1 | 5% |\n"""
    try:
        manifest = build_manifest(report, MINIMUM_RATIO)
        try:
            build_manifest(report, Decimal("0.14"))
            raise error("minimum ratio regression")
        except ValueError:
            pass
        fields = {item["field"] for item in manifest["items"]}
        if not manifest["eligible_numeric_table_cells"] or not {"government_yield", "government_yield_x2", "payback_eps"}.issubset(fields):
            raise error("table/yield classification regression")
        if {item["reported_value"] for item in extract_points(report) if item["field"] == "revenue"} != {"-0.80"}:
            raise error("currency accounting-negative regression")
        template = results_template(manifest)
        for result, item in zip(template["results"], manifest["items"]):
            result["fresh_value"] = item["reported_value"]
            result["source"] = {"name": "SEC", "tier": "Tier 1", "source_url": "https://www.sec.gov/Archives", "authority_type": "regulator"}
        if evaluate(manifest, template, report)["verdict"] != "PASS":
            raise error("pass regression")
        if evaluate(manifest, template, report + "\nchanged")["verdict"] != "BLOCK":
            raise error("stale report regression")
        if evaluate(build_manifest("## Evidence Ledger\n| A | B |\n|---|---|\n", MINIMUM_RATIO), {"manifest_sha256": "x", "results": []}, "## Evidence Ledger\n| A | B |\n|---|---|\n")["verdict"] != "BLOCK":
            raise error("empty extraction regression")
        with tempfile.TemporaryDirectory() as directory:
            malformed = Path(directory) / "malformed.json"
            malformed.write_text("{", encoding="utf-8")
            try:
                load_json(malformed)
                raise error("malformed JSON regression")
            except ValueError:
                pass
        print("SELF-TEST PASS")
        return 0
    except (ValueError, KeyError, TypeError) as exc:
        print(f"SELF-TEST FAIL: {exc}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic, manual-only report data audit.")
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    extract = commands.add_parser("extract", help="write a v4 manual manifest or pack-backed v5 manifest")
    extract.add_argument("--report", type=Path, required=True)
    extract.add_argument("--manifest-out", type=Path, required=True)
    extract.add_argument("--results-out", type=Path)
    extract.add_argument("--ratio")
    extract.add_argument("--pack", type=Path)
    verdict = commands.add_parser("verdict", help="validate results against the exact current report and manifest")
    verdict.add_argument("--report", type=Path, required=True)
    verdict.add_argument("--manifest", type=Path, required=True)
    verdict.add_argument("--results", type=Path)
    verdict.add_argument("--pack", type=Path)
    recognize = commands.add_parser("recognize", help="preflight mandatory decision-field labels without requiring numeric values")
    recognize.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.self_test:
            return self_test()
        if args.command == "extract":
            if args.pack is not None:
                if args.results_out is not None or args.ratio is not None:
                    raise error("pack-backed v5 extract is incompatible with --results-out and --ratio")
                _require_distinct_paths(
                    [("report", args.report), ("pack", args.pack), ("manifest-out", args.manifest_out)]
                )
                _reject_symlink(args.manifest_out, "manifest-out")
                snapshot = AuditV5Snapshot.load(args.report, args.pack)
                manifest = build_manifest_v5(snapshot)
                write_manifest_atomic(args.manifest_out, manifest)
                print(f"WROTE {args.manifest_out}: {len(manifest['items'])} pack-backed derived cells (v5)")
                return 0
            if args.results_out is None:
                raise error("v4 extract requires --results-out when --pack is not provided")
            _require_distinct_paths(
                [
                    ("report", args.report),
                    ("manifest-out", args.manifest_out),
                    ("results-out", args.results_out),
                ]
            )
            _reject_symlink(args.manifest_out, "manifest-out")
            _reject_symlink(args.results_out, "results-out")
            report = args.report.read_text(encoding="utf-8")
            manifest = build_manifest(report, decimal(args.ratio or "0.15"))
            manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            results_bytes = (
                json.dumps(results_template(manifest), ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8")
            write_outputs_atomic(
                [(args.manifest_out, manifest_bytes), (args.results_out, results_bytes)]
            )
            print(f"WROTE {args.manifest_out} and {args.results_out}: {len(manifest['items'])}/{manifest['eligible_numeric_table_cells']} eligible table cells ({Decimal(manifest['actual_ratio']):.2%})")
            return 0
        if args.command == "recognize":
            if args.report.suffix.lower() not in {".md", ".markdown"}:
                raise error(f"expected a Markdown report, got: {args.report}")
            outcome = recognize_fields(args.report.read_text(encoding="utf-8"))
            print(json.dumps(outcome, ensure_ascii=False, indent=2))
            return 0 if outcome["status"] == "PASS" else 1
        if args.command == "verdict":
            if args.pack is not None:
                if args.results is not None:
                    raise error("v5 verdict requires --pack and is incompatible with --results")
                snapshot = AuditV5VerdictSnapshot.load(args.report, args.pack, args.manifest)
                if snapshot.manifest.get("version") != V5_VERSION:
                    raise error(
                        f"manifest version {snapshot.manifest.get('version')} is incompatible with --pack; "
                        "use --results for v4 or re-extract with --pack for v5"
                    )
                outcome = evaluate_v5(snapshot)
            else:
                if args.results is not None:
                    _require_distinct_paths(
                        [
                            ("report", args.report),
                            ("manifest", args.manifest),
                            ("results", args.results),
                        ]
                    )
                manifest = load_json(args.manifest)
                if isinstance(manifest, dict) and manifest.get("version") == V5_VERSION:
                    raise error("v5 verdict requires --pack and is incompatible with --results")
                if args.results is None:
                    raise error("v4 verdict requires --results and is incompatible with --pack")
                if not isinstance(manifest, dict) or manifest.get("version") != VERSION:
                    found = manifest.get("version") if isinstance(manifest, dict) else None
                    raise error(
                        f"manifest version {found} is incompatible with --results; "
                        "use --pack for v5 or re-extract a v4 manifest for --results"
                    )
                report = args.report.read_text(encoding="utf-8")
                outcome = evaluate(manifest, load_json(args.results), report)
            print(json.dumps(outcome, ensure_ascii=False, indent=2))
            return 0 if outcome["verdict"] == "PASS" else 1
        parser.print_help()
        return 2
    except (OSError, ValueError, KeyError, TypeError, ResearchPackInputError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

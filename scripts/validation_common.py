"""Shared zero-dependency report validation primitives."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any, Iterator


ONE_PERCENT = Decimal("1")
FIVE_PERCENT = Decimal("5")
HUNDRED = Decimal("100")
TABLE_DELIMITER = re.compile(r"\|[\s:|-]+\|")


def iter_markdown_tables(text: str) -> Iterator[dict[str, Any]]:
    """Yield Markdown tables using the audit extractor's canonical traversal."""
    section, lines, index = "", text.splitlines(), 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("## "):
            section = line
        if not (
            line.startswith("|")
            and index + 1 < len(lines)
            and TABLE_DELIMITER.fullmatch(lines[index + 1].strip())
        ):
            index += 1
            continue
        headers = [cell.strip() for cell in line.strip("|").split("|")]
        heading_line_number = index + 1
        index += 2
        rows = []
        while index < len(lines) and lines[index].strip().startswith("|"):
            rows.append(
                {
                    "cells": [
                        cell.strip()
                        for cell in lines[index].strip().strip("|").split("|")
                    ],
                    "line_number": index + 1,
                }
            )
            index += 1
        yield {
            "section": section,
            "headers": headers,
            "heading_line_number": heading_line_number,
            "rows": rows,
        }


ACTION_MATRIX_COLUMNS = ["Action", "Trigger type", "Executable condition", "Position/execution"]
ACTION_MATRIX_NA_VALUE = re.compile(r"^(?:n\s*/?\s*a\b|not\s+applicable\b|不适用(?:\b|\s*[-:：]))", re.I)


def find_action_matrix_table(block: str) -> dict[str, Any] | None:
    """Locate the single canonical module 8 Action Matrix table in a block.

    The contract: exactly one `### Action Matrix` heading followed by one
    Markdown table whose header is the canonical four-column contract. Returns
    that table dict (as yielded by ``iter_markdown_tables``) or ``None`` when
    the heading count is not exactly one, the table count is not exactly one,
    or the header does not match. Shared by report_lint and report_audit so the
    two tools cannot drift on how the matrix table is located.
    """
    headings = list(re.finditer(r"^###\s+Action Matrix\s*$", block, re.M))
    if len(headings) != 1:
        return None
    tail = block[headings[0].end() :]
    next_heading = re.search(r"^#{1,6}\s+", tail, re.M)
    matrix_block = tail[: next_heading.start()] if next_heading else tail
    tables = list(iter_markdown_tables(matrix_block))
    if len(tables) != 1:
        return None
    table = tables[0]
    if table["headers"] != ACTION_MATRIX_COLUMNS:
        return None
    return table


def decimal(value: object) -> Decimal:
    """Parse a finite Decimal, including accounting parentheses."""
    if isinstance(value, bool):
        raise ValueError("boolean is not a numeric value")
    text = str(value).strip().replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"invalid numeric value: {value!r}") from error
    if not parsed.is_finite():
        raise ValueError(f"numeric value must be finite: {value!r}")
    return parsed


def direct_discrepancy_percent(base: Decimal, comparison: Decimal) -> Decimal:
    """Compare a report value to fresh authority using abs(report) denominator."""
    if base == 0:
        return Decimal("0") if comparison == 0 else Decimal("Infinity")
    return abs(base - comparison) / abs(base) * HUNDRED


def symmetric_spread_percent(values: list[Decimal]) -> Decimal:
    """Compare independent sources with range/minimum-absolute denominator."""
    if len(values) < 2:
        raise ValueError("symmetric spread requires at least two values")
    low, high = min(values), max(values)
    denominator = min(abs(value) for value in values)
    if low == high:
        return Decimal("0")
    if denominator == 0:
        return Decimal("Infinity")
    return abs(high - low) / denominator * HUNDRED


def classify_discrepancy(difference: Decimal) -> tuple[str, str]:
    """Classify the shared <=1%, >1%-5%, and >5% policy."""
    if difference <= ONE_PERCENT:
        return "CONSISTENT", "<=1%: consistent"
    if difference <= FIVE_PERCENT:
        return "RECONCILE", ">1%-5%: reconcile and explain"
    return "BLOCK", ">5%: block until Tier 1 verification"

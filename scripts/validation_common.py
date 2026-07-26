"""Shared zero-dependency numeric validation primitives."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


ONE_PERCENT = Decimal("1")
FIVE_PERCENT = Decimal("5")
HUNDRED = Decimal("100")


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

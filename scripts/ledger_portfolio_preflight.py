#!/usr/bin/env python3
"""Read-only Ledger portfolio snapshot for equity-research reports.

The script deliberately separates holdings facts from market-data facts. It
reads the authenticated Ledger ``/api/stocks`` endpoint, keeps only positive
holdings, and never writes or persists the bearer token.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


class LedgerPreflightError(RuntimeError):
    """Raised when a Ledger snapshot cannot be trusted."""


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _unwrap_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = None
        for key in ("data", "stocks", "items"):
            if key in payload:
                records = payload[key]
                break
    else:
        records = None
    if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
        raise LedgerPreflightError("Ledger /api/stocks returned an unexpected payload")
    return records


def _is_stale(timestamp: Any, now: datetime, max_age_hours: float) -> bool:
    if not timestamp:
        return False
    try:
        value = str(timestamp).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return now - parsed.astimezone(timezone.utc) > timedelta(hours=max_age_hours)


def extract_active_positions(
    payload: Any,
    *,
    now: datetime | None = None,
    max_price_age_hours: float = 72.0,
) -> tuple[list[dict[str, Any]], list[str], int]:
    """Normalize Ledger stocks and filter historical zero-quantity records."""
    records = _unwrap_list(payload)
    warnings: list[str] = []
    positions: list[dict[str, Any]] = []
    inactive_count = 0
    now = now or datetime.now(timezone.utc)

    for item in records:
        amount = _number(item.get("amount"))
        if amount is None:
            warnings.append(f"missing amount: {item.get('code', '<unknown>')}")
            continue
        if amount <= 0:
            inactive_count += 1
            continue

        code = str(item.get("code") or "").strip()
        current_price = _number(item.get("currentPrice"))
        if not code or current_price is None or current_price <= 0:
            warnings.append(f"incomplete active position: {code or '<unknown>'}")
            continue

        price_timestamp = item.get("priceUpdateTime") or item.get("updatedAt")
        if not price_timestamp:
            warnings.append(f"missing price timestamp: {code}")
        elif _is_stale(price_timestamp, now, max_price_age_hours):
            warnings.append(f"stale price timestamp: {code}")

        positions.append(
            {
                "code": code,
                "name": item.get("name"),
                "market": item.get("market"),
                "currency": item.get("currency"),
                "amount": amount,
                "current_price": current_price,
                "holding_value": amount * current_price,
                "price_timestamp": price_timestamp,
                "source": "Ledger /api/stocks",
            }
        )

    positions.sort(key=lambda item: item["holding_value"], reverse=True)
    return positions, warnings, inactive_count


def _validate_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LedgerPreflightError("Ledger base URL must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise LedgerPreflightError(
            "Ledger base URL must not contain embedded credentials; use LEDGER_AUTH_TOKEN"
        )
    if parsed.query or parsed.fragment:
        raise LedgerPreflightError("Ledger base URL must not contain query parameters or fragments")
    return base_url.rstrip("/") + "/"


def fetch_json(base_url: str, path: str, token: str, timeout: float) -> Any:
    url = urljoin(_validate_base_url(base_url), path.lstrip("/"))
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "wall-street-equity-research/ledger-preflight",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        if error.code in {401, 403}:
            raise LedgerPreflightError(
                f"Ledger authentication failed for {path} (HTTP {error.code}); "
                "set a fresh LEDGER_AUTH_TOKEN"
            ) from error
        raise LedgerPreflightError(f"Ledger request failed for {path} (HTTP {error.code})") from error
    except URLError as error:
        raise LedgerPreflightError(f"Ledger request failed for {path}: {error.reason}") from error

    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise LedgerPreflightError(f"Ledger returned non-JSON data for {path}") from error


def build_snapshot(
    stocks_payload: Any,
    *,
    base_url: str,
    retrieved_at: str | None = None,
    allocation_payload: Any | None = None,
    allocation_error: str | None = None,
    max_price_age_hours: float = 72.0,
) -> dict[str, Any]:
    positions, warnings, inactive_count = extract_active_positions(
        stocks_payload,
        max_price_age_hours=max_price_age_hours,
    )
    snapshot: dict[str, Any] = {
        "source": "Ledger",
        "endpoint": "/api/stocks",
        "base_url": base_url.rstrip("/"),
        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(),
        "active_position_count": len(positions),
        "inactive_record_count": inactive_count,
        "positions": positions,
        "warnings": warnings,
        "max_price_age_hours": max_price_age_hours,
    }
    if not positions:
        snapshot["warnings"].append(
            "Ledger returned no active positions; distinguish no holdings from an unverified snapshot"
        )
    if allocation_payload is not None:
        snapshot["allocation_endpoint"] = "/api/allocation"
        snapshot["allocation_snapshot"] = allocation_payload
        if isinstance(allocation_payload, dict) and allocation_payload.get("warning"):
            snapshot["warnings"].append(
                f"Ledger allocation warning: {allocation_payload['warning']}"
            )
    else:
        snapshot["allocation_status"] = "unavailable" if allocation_error else "not_requested"
        if allocation_error:
            snapshot["warnings"].append(f"Ledger allocation unavailable: {allocation_error}")
    return snapshot


def fetch_snapshot(
    base_url: str,
    token: str,
    timeout: float,
    include_allocation: bool,
    max_price_age_hours: float,
) -> dict[str, Any]:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    stocks_payload = fetch_json(base_url, "/api/stocks", token, timeout)
    allocation_payload = None
    allocation_error = None
    if include_allocation:
        try:
            allocation_payload = fetch_json(base_url, "/api/allocation", token, timeout)
        except LedgerPreflightError as error:
            allocation_error = str(error)
    return build_snapshot(
        stocks_payload,
        base_url=base_url,
        retrieved_at=retrieved_at,
        allocation_payload=allocation_payload,
        allocation_error=allocation_error,
        max_price_age_hours=max_price_age_hours,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LEDGER_API_BASE_URL", "http://localhost:3000"),
        help="Ledger API base URL (or LEDGER_API_BASE_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("LEDGER_AUTH_TOKEN", ""),
        help="Bearer token; prefer LEDGER_AUTH_TOKEN so it is not stored in shell history",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-price-age-hours", type=float, default=72.0)
    parser.add_argument("--include-allocation", action="store_true")
    args = parser.parse_args(argv)

    if not args.token:
        print(
            "Ledger authentication token is required. Set LEDGER_AUTH_TOKEN; "
            "the script never writes it to disk.",
            file=sys.stderr,
        )
        return 2

    try:
        snapshot = fetch_snapshot(
            args.base_url,
            args.token,
            args.timeout,
            args.include_allocation,
            args.max_price_age_hours,
        )
    except LedgerPreflightError as error:
        print(f"Ledger preflight failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

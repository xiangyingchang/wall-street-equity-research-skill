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
        if amount < 0:
            warnings.append(f"negative amount (short or data error): {item.get('code', '<unknown>')}")
            continue
        if amount == 0:
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


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _validate_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LedgerPreflightError("Ledger base URL must be an absolute http(s) URL")
    if parsed.scheme == "http" and (parsed.hostname or "") not in LOCAL_HOSTS:
        raise LedgerPreflightError(
            "Ledger base URL must use https unless it points to localhost; refusing to send the token in clear text"
        )
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
    snapshot["trusted"] = not snapshot["warnings"]
    return snapshot


MARKET_CURRENCY = {"US": "USD", "HK": "HKD", "CN": "CNY"}


def _normalize_code(code: Any, market: Any = None) -> tuple[str, str]:
    """Keep market identity; accept bare symbols and Hong Kong padding aliases."""
    symbol = str(code or "").strip().upper()
    listing_market = str(market or "").strip().upper()
    suffixes = {"US": "US", "HK": "HK", "CN": "CN", "SH": "CN", "SZ": "CN"}
    if "." in symbol:
        base, suffix = symbol.rsplit(".", 1)
        if suffix in suffixes:
            symbol, listing_market = base, suffixes[suffix]
    listing_market = suffixes.get(listing_market, listing_market)
    if not listing_market:
        listing_market = ("HK" if len(symbol) <= 5 else "CN") if symbol.isdigit() else "US"
    if symbol.isdigit() and listing_market == "HK":
        symbol = symbol.zfill(5)
    return symbol, listing_market


def portfolio_context_draft(
    snapshot: dict[str, Any],
    ticker: str,
    *,
    rates_payload: Any | None = None,
) -> dict[str, Any]:
    """Draft a Spec ``portfolio_context`` for one ticker.

    Weights are computed only when every input is verified: the snapshot is
    trusted, allocation net assets are present, and a Ledger exchange rate
    exists for the position currency. Target weight is never inferred; the
    user must state it. Anything unverified resolves to ``unknown`` so the
    compiler gates the executable action to REVIEW.
    """
    wanted = _normalize_code(ticker)
    matches = [item for item in snapshot.get("positions", []) if _normalize_code(item.get("code"), item.get("market")) == wanted]
    base = {
        "as_of": str(snapshot.get("retrieved_at", ""))[:10],
        "source": f"Ledger /api/stocks snapshot {snapshot.get('retrieved_at', '')}",
        "target_weight": None,
        "tax_friction": "unknown",
        "constraints": "目标权重需由用户确认；Ledger 仅提供大类配置目标。",
    }
    if not snapshot.get("trusted"):
        return {**base, "position_status": "unknown", "confidence": "low", "current_weight": None,
                "constraints": "Ledger 快照存在告警，持仓未验证：" + "；".join(snapshot.get("warnings", []))}
    if not matches:
        return {**base, "position_status": "not_held", "confidence": "high", "current_weight": None}
    if len(matches) > 1:
        return {**base, "position_status": "unknown", "confidence": "low", "current_weight": None,
                "constraints": "Ledger 中同一市场的股票有多条匹配记录，需核对后才能计算持仓。"}
    position = matches[0]
    allocation = snapshot.get("allocation_snapshot")
    net_assets = _number(allocation.get("netAssets")) if isinstance(allocation, dict) else None
    currency = str(position.get("currency") or MARKET_CURRENCY.get(str(position.get("market") or "").upper(), "")).upper()
    rate = D_ONE if currency == "CNY" else None
    if currency in {"USD", "HKD"} and isinstance(rates_payload, dict):
        rate = _number(rates_payload.get(f"{currency}_CNY"))
    if not net_assets or net_assets <= 0 or rate is None:
        return {**base, "position_status": "held", "confidence": "medium", "current_weight": None,
                "constraints": "已确认持仓，但缺少净资产或汇率，无法计算当前权重；目标权重需由用户确认。"}
    weight = position["holding_value"] * rate / net_assets
    return {**base, "position_status": "held", "confidence": "high", "current_weight": f"{weight:.4f}"}


D_ONE = 1.0


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
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-price-age-hours", type=float, default=72.0)
    parser.add_argument("--include-allocation", action="store_true")
    parser.add_argument("--ticker", help="also emit a portfolio_context draft for this ticker (implies --include-allocation)")
    args = parser.parse_args(argv)
    token = os.environ.get("LEDGER_AUTH_TOKEN", "")

    if not token:
        print(
            "Ledger authentication token is required. Set LEDGER_AUTH_TOKEN; "
            "the script never accepts it as an argument or writes it to disk.",
            file=sys.stderr,
        )
        return 2

    try:
        snapshot = fetch_snapshot(
            args.base_url,
            token,
            args.timeout,
            args.include_allocation or bool(args.ticker),
            args.max_price_age_hours,
        )
        if args.ticker:
            rates = None
            try:
                rates = fetch_json(args.base_url, "/api/exchange-rates", token, args.timeout)
            except LedgerPreflightError as error:
                snapshot["warnings"].append(f"Ledger exchange rates unavailable: {error}")
            snapshot["portfolio_context_draft"] = portfolio_context_draft(snapshot, args.ticker, rates_payload=rates)
    except LedgerPreflightError as error:
        print(f"Ledger preflight failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only Ledger portfolio snapshot for equity-research reports.

The default mode reads all active positions. The --all-active mode also
cross-checks current quotes and FX for every position; --ticker adds a
single-ticker portfolio-context draft. All modes use the durable read-only
research token in macOS Keychain first. Tokens are never printed or persisted.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


class LedgerPreflightError(RuntimeError):
    """Raised when a Ledger snapshot cannot be trusted."""


class LedgerAuthenticationError(LedgerPreflightError):
    """Raised when Ledger rejects an otherwise configured credential."""


DEFAULT_LEDGER_API_BASE_URL = "https://ledger-backend-hdxm.onrender.com"
DEFAULT_KEYCHAIN_SERVICE = "ledger-research-token"
RESEARCH_TOKEN_HEADER = "X-Ledger-Research-Token"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=5d&interval=1m"
SINA_QUOTE_URL = "https://hq.sinajs.cn/list={}"
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q={}"
OPEN_ER_FX_URL = "https://open.er-api.com/v6/latest/CNY"
FRANKFURTER_FX_URL = "https://api.frankfurter.dev/v2/rates?base=CNY&quotes=USD,HKD"
CURRENCY_API_FX_URL = "https://latest.currency-api.pages.dev/v1/currencies/cny.json"
NASDAQ_QUOTE_URL = "https://api.nasdaq.com/api/quote/{}/info?assetclass={}"
MAX_QUOTE_SOURCE_DIFFERENCE_PCT = 1.0


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
        for key in ("positions", "data", "stocks", "items"):
            if key in payload:
                records = payload[key]
                break
    else:
        records = None
    if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
        raise LedgerPreflightError("Ledger holdings endpoint returned an unexpected payload")
    return records


def _parse_timestamp(timestamp: Any, default_timezone=timezone.utc) -> datetime | None:
    if not timestamp:
        return None
    try:
        if hasattr(timestamp, "tzinfo") and hasattr(timestamp, "isoformat"):
            parsed = timestamp
        else:
            value = str(timestamp).replace("Z", "+00:00")
            parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=default_timezone)
    return parsed.astimezone(timezone.utc)


def _is_stale(timestamp: Any, now: datetime, max_age_hours: float) -> bool:
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return True
    return now.astimezone(timezone.utc) - parsed > timedelta(hours=max_age_hours)


def _is_future_dated(timestamp: Any, now: datetime, tolerance_minutes: float = 5.0) -> bool:
    parsed = _parse_timestamp(timestamp)
    return parsed is None or parsed - now.astimezone(timezone.utc) > timedelta(minutes=tolerance_minutes)


def _public_json(url: str, timeout: float) -> Any:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
        method="GET",
    )
    for attempt in range(2):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise LedgerPreflightError(f"public market-data request failed: {urlparse(url).netloc}") from error
        except (URLError, TimeoutError, OSError) as error:
            if attempt == 0:
                time.sleep(0.2)
                continue
            raise LedgerPreflightError(f"public market-data request failed: {urlparse(url).netloc}") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LedgerPreflightError(f"public market-data response was invalid: {urlparse(url).netloc}") from error


def fetch_yahoo_chart_quote(symbol: str, timeout: float = 10.0) -> dict[str, Any]:
    """Fetch the latest timestamped Yahoo chart price for one listed instrument."""
    url = YAHOO_CHART_URL.format(quote(symbol, safe=""))
    payload = _public_json(url, timeout)
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not isinstance(result, dict):
        raise LedgerPreflightError(f"Yahoo Finance returned no chart for {symbol}")
    timestamps = result.get("timestamp") or []
    quote_rows = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote_rows.get("close") or []
    for index in range(min(len(timestamps), len(closes)) - 1, -1, -1):
        price = _number(closes[index])
        if price is not None and price > 0:
            return {
                "symbol": symbol,
                "price": price,
                "currency": (result.get("meta") or {}).get("currency"),
                "timestamp": datetime.fromtimestamp(
                    int(timestamps[index]), timezone.utc
                ).isoformat(),
                "source": "Yahoo Finance chart",
            }
    meta = result.get("meta") or {}
    price = _number(meta.get("regularMarketPrice"))
    timestamp = meta.get("regularMarketTime")
    if price is None or price <= 0 or timestamp is None:
        raise LedgerPreflightError(f"Yahoo Finance returned no timestamped price for {symbol}")
    return {
        "symbol": symbol,
        "price": price,
        "currency": meta.get("currency"),
        "timestamp": datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat(),
        "source": "Yahoo Finance chart",
    }


def _yahoo_symbol(code: str, market: str) -> str:
    if market == "HK":
        if not code.isdigit():
            raise LedgerPreflightError(f"unsupported Hong Kong holding code: {code}")
        return f"{int(code):04d}.HK"
    if market == "CN":
        if not code.isdigit():
            raise LedgerPreflightError(f"unsupported China holding code: {code}")
        suffix = "SS" if code.startswith(("5", "6")) else "SZ"
        return f"{code}.{suffix}"
    if market == "US":
        return code
    raise LedgerPreflightError(f"unsupported stock market for {code}: {market or 'unknown'}")


def _sina_symbol(code: str, market: str) -> tuple[str, int]:
    if market == "HK" and code.isdigit():
        return f"hk{code.zfill(5)}", 6
    if market == "CN" and code.isdigit():
        return f"{'sh' if code.startswith(('5', '6')) else 'sz'}{code}", 3
    if market == "US":
        return f"gb_{code.lower()}", 1
    raise LedgerPreflightError(f"unsupported Sina quote symbol for {code}: {market or 'unknown'}")


def _market_timezone(market: str):
    zone_names = {"HK": "Asia/Hong_Kong", "CN": "Asia/Shanghai", "US": "America/New_York"}
    try:
        return ZoneInfo(zone_names[market])
    except (KeyError, ValueError) as error:
        raise LedgerPreflightError(f"unsupported quote timezone for market: {market}") from error


def _parse_local_market_timestamp(value: str, market: str) -> str:
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S"):
        try:
            parsed = datetime.strptime(value.strip(), fmt).replace(tzinfo=_market_timezone(market))
            return parsed.astimezone(timezone.utc).isoformat()
        except ValueError:
            continue
    raise LedgerPreflightError(f"quote provider returned an invalid timestamp for {market}")


def _parse_us_feed_timestamp(value: str, *, year: int | None = None, date_only_ok: bool = False) -> str | None:
    """Parse a US quote time with ET/EDT/EST, or a date-only Nasdaq trade date."""
    text = re.sub(r"\s+(?:ET|EDT|EST)$", "", value.strip(), flags=re.IGNORECASE)
    if text.lower().startswith("closed at "):
        text = text[9:].strip()
    formats = (
        "%b %d, %Y %I:%M %p",
        "%b %d, %Y %I:%M:%S %p",
        "%b %d %I:%M%p %Y",
        "%b %d %I:%M %p %Y",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt).replace(tzinfo=_market_timezone("US"))
            return parsed.astimezone(timezone.utc).isoformat()
        except ValueError:
            continue
    if date_only_ok:
        for fmt in ("%b %d, %Y", "%b %d %Y"):
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
    if year is not None:
        for fmt in ("%b %d %I:%M%p", "%b %d %I:%M %p"):
            try:
                parsed = datetime.strptime(f"{text} {year}", fmt + " %Y").replace(
                    tzinfo=_market_timezone("US")
                )
                return parsed.astimezone(timezone.utc).isoformat()
            except ValueError:
                continue
    return None


def fetch_sina_quote(code: str, market: str, timeout: float = 10.0) -> dict[str, Any]:
    """Fetch a second, independent quote used to check Yahoo chart prices."""
    symbol, price_index = _sina_symbol(code, market)
    request = Request(
        SINA_QUOTE_URL.format(symbol),
        headers={
            "Accept": "*/*",
            "Referer": "https://finance.sina.com.cn/",
            "User-Agent": "Mozilla/5.0",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("gb18030")
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError) as error:
        raise LedgerPreflightError(f"Sina quote request failed for {code}") from error
    match = re.search(r'="([^"]*)"', body)
    if not match:
        raise LedgerPreflightError(f"Sina returned no quote for {code}")
    fields = match.group(1).split(",")
    if len(fields) <= price_index:
        raise LedgerPreflightError(f"Sina returned an incomplete quote for {code}")
    price = _number(fields[price_index])
    if market != "US" and (price is None or price <= 0):
        raise LedgerPreflightError(f"Sina returned an invalid quote for {code}")
    if market == "HK":
        date_text, time_text = fields[-2], fields[-1]
    elif market == "CN":
        if len(fields) < 3:
            raise LedgerPreflightError(f"Sina returned no quote timestamp for {code}")
        date_text, time_text = fields[-4], fields[-3]
    else:
        # The GB feed's field 3 is the quote server's local clock (China time),
        # not the US trade time. Use the timestamp paired with the US last-sale
        # field; during a session this is commonly the pre-market/after-hours
        # trade. If it is absent, use the explicitly reported previous close.
        year = int(fields[29]) if len(fields) > 29 and fields[29].isdigit() else datetime.now(timezone.utc).year
        if len(fields) > 24:
            us_price = _number(fields[21])
            us_timestamp = _parse_us_feed_timestamp(fields[24], year=year)
            if us_price is not None and us_price > 0 and us_timestamp is not None:
                return {
                    "price": us_price,
                    "currency": MARKET_CURRENCY[market],
                    "timestamp": us_timestamp,
                    "source": "Sina Finance quote",
                    "symbol": symbol,
                }
        if len(fields) > 25:
            close_timestamp = _parse_us_feed_timestamp(fields[25], year=year)
            if price is not None and price > 0 and close_timestamp is not None:
                return {
                    "price": price,
                    "currency": MARKET_CURRENCY[market],
                    "timestamp": close_timestamp,
                    "source": "Sina Finance quote",
                    "symbol": symbol,
                }
        raise LedgerPreflightError(f"Sina returned no timestamped US quote for {code}")
    timestamp = _parse_local_market_timestamp(f"{date_text} {time_text}", market)
    return {
        "price": price,
        "currency": MARKET_CURRENCY[market],
        "timestamp": timestamp,
        "source": "Sina Finance quote",
        "symbol": symbol,
    }


def fetch_tencent_quote(code: str, market: str, timeout: float = 10.0) -> dict[str, Any]:
    """Fetch a timestamped quote from Tencent's public quote endpoint."""
    if market == "HK" and code.isdigit():
        symbol = f"r_hk{code.zfill(5)}"
    elif market == "CN" and code.isdigit():
        symbol = f"{'sh' if code.startswith(('5', '6')) else 'sz'}{code}"
    elif market == "US":
        symbol = f"us{code}"
    else:
        raise LedgerPreflightError(f"unsupported Tencent quote symbol for {code}: {market or 'unknown'}")
    request = Request(
        TENCENT_QUOTE_URL.format(quote(symbol, safe="")),
        headers={"Accept": "text/plain", "User-Agent": "Mozilla/5.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("gb18030")
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError) as error:
        raise LedgerPreflightError(f"Tencent quote request failed for {code}") from error
    match = re.search(r'="([^\"]*)"', body)
    if not match:
        raise LedgerPreflightError(f"Tencent returned no quote for {code}")
    fields = match.group(1).split("~")
    if len(fields) <= 30:
        raise LedgerPreflightError(f"Tencent returned an incomplete quote for {code}")
    price = _number(fields[3])
    if price is None or price <= 0:
        raise LedgerPreflightError(f"Tencent returned an invalid quote for {code}")
    timestamp = _parse_local_market_timestamp(fields[30], market)
    return {
        "price": price,
        "currency": MARKET_CURRENCY[market],
        "timestamp": timestamp,
        "source": "Tencent Finance quote",
        "symbol": symbol,
    }


def fetch_nasdaq_quote(code: str, market: str, timeout: float = 10.0) -> dict[str, Any]:
    """Fetch a US last-sale quote and date from Nasdaq's public quote API."""
    if market != "US":
        raise LedgerPreflightError(f"Nasdaq quote source does not cover {market} holdings")
    last_error: Exception | None = None
    for asset_class in ("stocks", "etf"):
        url = NASDAQ_QUOTE_URL.format(quote(code, safe=""), asset_class)
        request = Request(
            url,
            headers={
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.nasdaq.com",
                "Referer": "https://www.nasdaq.com/",
                "User-Agent": "Mozilla/5.0",
            },
            method="GET",
        )
        payload = None
        for attempt in range(2):
            try:
                with urlopen(request, timeout=timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as error:
                last_error = error
                if attempt == 0 and (error.code == 429 or 500 <= error.code < 600):
                    time.sleep(0.2)
                    continue
                break
            except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as error:
                last_error = error
                if attempt == 0:
                    time.sleep(0.2)
                    continue
                break
        if payload is None:
            continue
        data = payload.get("data") if isinstance(payload, dict) else None
        primary = data.get("primaryData") if isinstance(data, dict) else None
        if not isinstance(primary, dict):
            continue
        price_text = str(primary.get("lastSalePrice") or "").replace("$", "").replace(",", "").strip()
        price = _number(price_text)
        date_text = str(primary.get("lastTradeTimestamp") or "").strip()
        timestamp = _parse_us_feed_timestamp(date_text, date_only_ok=True)
        if timestamp is None:
            continue
        if price is None or price <= 0:
            continue
        return {
            "price": price,
            "currency": "USD",
            "timestamp": timestamp,
            "source": "Nasdaq last-sale summary",
            "symbol": code,
        }
    raise LedgerPreflightError(f"Nasdaq returned no timestamped quote for {code}") from last_error


def fetch_open_er_fx_rates(timeout: float = 10.0) -> dict[str, Any]:
    """Get an independent CNY-base FX snapshot from open.er-api.com."""
    payload = _public_json(OPEN_ER_FX_URL, timeout)
    raw_rates = payload.get("rates") if isinstance(payload, dict) else None
    if not isinstance(raw_rates, dict):
        raise LedgerPreflightError("open.er-api.com returned no FX rates")
    normalized: dict[str, Any] = {}
    for currency in ("USD", "HKD"):
        cny_to_currency = _number(raw_rates.get(currency))
        if cny_to_currency is None or cny_to_currency <= 0:
            raise LedgerPreflightError(f"open.er-api.com returned an invalid {currency} FX rate")
        normalized[f"{currency}_CNY"] = 1.0 / cny_to_currency
    timestamp_text = payload.get("time_last_update_utc")
    if not timestamp_text:
        raise LedgerPreflightError("open.er-api.com omitted the FX update time")
    try:
        normalized["timestamp"] = parsedate_to_datetime(timestamp_text).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError) as error:
        raise LedgerPreflightError("open.er-api.com returned an invalid FX update time") from error
    normalized["source"] = "open.er-api.com"
    return normalized


def fetch_frankfurter_fx_rates(timeout: float = 10.0) -> dict[str, Any]:
    """Get independent daily CNY-base FX rates from the Frankfurter API."""
    payload = _public_json(FRANKFURTER_FX_URL, timeout)
    if isinstance(payload, list):
        rows = payload
        date_text = min((str(row.get("date", "")) for row in rows if isinstance(row, dict)), default="")
        raw_rates = {
            str(row.get("quote", "")).upper(): row.get("rate")
            for row in rows
            if isinstance(row, dict)
        }
    elif isinstance(payload, dict):
        rows = []
        date_text = str(payload.get("date") or "")
        raw_rates = payload.get("rates")
    else:
        raw_rates = None
        date_text = ""
    if not isinstance(raw_rates, dict):
        raise LedgerPreflightError("Frankfurter returned no FX rates")
    normalized: dict[str, Any] = {}
    for currency in ("USD", "HKD"):
        cny_to_currency = _number(raw_rates.get(currency))
        if cny_to_currency is None or cny_to_currency <= 0:
            raise LedgerPreflightError(f"Frankfurter returned an invalid {currency} FX rate")
        normalized[f"{currency}_CNY"] = 1.0 / cny_to_currency
    if not date_text:
        raise LedgerPreflightError("Frankfurter omitted the FX update date")
    try:
        normalized["timestamp"] = datetime.fromisoformat(str(date_text)).replace(tzinfo=timezone.utc).isoformat()
    except ValueError as error:
        raise LedgerPreflightError("Frankfurter returned an invalid FX update date") from error
    normalized["source"] = "Frankfurter daily reference rates"
    return normalized


def fetch_currency_api_fx_rates(timeout: float = 10.0) -> dict[str, Any]:
    """Get a second independent daily CNY-base FX snapshot from currency-api."""
    payload = _public_json(CURRENCY_API_FX_URL, timeout)
    raw_rates = payload.get("cny") if isinstance(payload, dict) else None
    if not isinstance(raw_rates, dict):
        raise LedgerPreflightError("currency-api returned no CNY-base FX rates")
    normalized: dict[str, Any] = {}
    for currency in ("USD", "HKD"):
        cny_to_currency = _number(raw_rates.get(currency.lower()))
        if cny_to_currency is None or cny_to_currency <= 0:
            raise LedgerPreflightError(f"currency-api returned an invalid {currency} FX rate")
        normalized[f"{currency}_CNY"] = 1.0 / cny_to_currency
    date_text = payload.get("date")
    if not date_text:
        raise LedgerPreflightError("currency-api omitted the FX update date")
    try:
        normalized["timestamp"] = datetime.fromisoformat(str(date_text)).replace(tzinfo=timezone.utc).isoformat()
    except ValueError as error:
        raise LedgerPreflightError("currency-api returned an invalid FX update date") from error
    normalized["source"] = "currency-api daily rates"
    return normalized


def _crosscheck_fx_sources(
    currencies: set[str],
    *,
    now: datetime,
    max_age_hours: float,
    timeout: float,
    fetchers: list[tuple[str, Any]],
) -> dict[str, Any]:
    if not currencies:
        return {"rates": {}, "sources": [], "timestamps": [], "warnings": []}

    snapshots: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
        futures = {name: executor.submit(fetcher, timeout) for name, fetcher in fetchers}
        for name, future in futures.items():
            try:
                row = future.result()
                if not _is_stale(row.get("timestamp"), now, max_age_hours) and not _is_future_dated(row.get("timestamp"), now):
                    snapshots[name] = row
            except Exception:
                continue

    rates: dict[str, float] = {}
    used_sources: set[str] = set()
    used_timestamps: list[datetime] = []
    source_order = [name for name, _ in fetchers]
    warnings: list[str] = []
    for currency in sorted(currencies):
        valid: list[tuple[str, float, datetime]] = []
        for name in source_order:
            row = snapshots.get(name)
            rate = _number(row.get(f"{currency}_CNY")) if row else None
            timestamp = _parse_timestamp(row.get("timestamp")) if row else None
            if rate is not None and rate > 0 and timestamp is not None:
                valid.append((name, rate, timestamp))
        selected_pair = None
        for first_index, first in enumerate(valid):
            for second in valid[first_index + 1:]:
                difference_pct = abs(first[1] - second[1]) / first[1] * 100
                if difference_pct <= MAX_QUOTE_SOURCE_DIFFERENCE_PCT:
                    selected_pair = (first, second)
                    break
            if selected_pair:
                break
        if selected_pair is None:
            if len(valid) < 2:
                warnings.append(f"fewer than two fresh independent FX sources for {currency}")
            else:
                warnings.append(f"independent FX sources differ by more than 1% for {currency}")
            continue
        first, second = selected_pair
        rates[f"{currency}_CNY"] = first[1]
        used_sources.update((first[0], second[0]))
        used_timestamps.extend((first[2], second[2]))

    return {
        "rates": rates,
        "sources": [str(snapshots[name].get("source") or name) for name in source_order if name in used_sources],
        "timestamps": used_timestamps,
        "warnings": warnings,
    }


def build_stock_pool_weight_snapshot(
    positions: list[dict[str, Any]],
    *,
    ticker: str,
    now: datetime | None = None,
    max_quote_age_hours: float = 72.0,
    timeout: float = 10.0,
    yahoo_quote_fetcher=None,
    nasdaq_quote_fetcher=None,
    tencent_quote_fetcher=None,
    sina_quote_fetcher=None,
    reference_fx_fetcher=None,
    open_er_fx_fetcher=None,
    currency_api_fx_fetcher=None,
) -> dict[str, Any]:
    """Compute FX-normalized stock-pool weights only from fresh, cross-checked quotes."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    yahoo_quote_fetcher = yahoo_quote_fetcher or fetch_yahoo_chart_quote
    nasdaq_quote_fetcher = nasdaq_quote_fetcher or fetch_nasdaq_quote
    tencent_quote_fetcher = tencent_quote_fetcher or fetch_tencent_quote
    sina_quote_fetcher = sina_quote_fetcher or fetch_sina_quote
    reference_fx_fetcher = reference_fx_fetcher or fetch_frankfurter_fx_rates
    open_er_fx_fetcher = open_er_fx_fetcher or fetch_open_er_fx_rates
    currency_api_fx_fetcher = currency_api_fx_fetcher or fetch_currency_api_fx_rates
    warnings: list[str] = []
    if not positions:
        return {"status": "unavailable", "weight": None, "warnings": ["no active stocks for stock-pool weight"]}

    requests: list[tuple[int, str, str, str]] = []
    currencies: set[str] = set()
    output_positions: list[dict[str, Any]] = []
    for index, position in enumerate(positions):
        code, market = _normalize_code(position.get("code"), position.get("market"))
        currency = str(position.get("currency") or MARKET_CURRENCY.get(market, "")).upper()
        amount = _number(position.get("amount"))
        try:
            symbol = _yahoo_symbol(code, market)
            sina_symbol, _ = _sina_symbol(code, market)
        except LedgerPreflightError as error:
            warnings.append(str(error))
            output_positions.append({"code": code, "market": market, "amount": amount, "currency": currency, "status": "unsupported"})
            continue
        if (
            amount is None
            or amount <= 0
            or currency not in {"CNY", "HKD", "USD"}
            or currency != MARKET_CURRENCY.get(market)
        ):
            warnings.append(f"invalid stock-pool input: {code}")
            output_positions.append({"code": code, "market": market, "amount": amount, "currency": currency, "status": "invalid_input"})
            continue
        currencies.add(currency)
        requests.append((index, code, market, symbol))
        output_positions.append({"code": code, "market": market, "amount": amount, "currency": currency, "symbol": symbol})

    fx_snapshot = _crosscheck_fx_sources(
        currencies - {"CNY"},
        now=now,
        max_age_hours=max_quote_age_hours,
        timeout=timeout,
        fetchers=[
            ("Frankfurter daily reference rates", reference_fx_fetcher),
            ("open.er-api.com", open_er_fx_fetcher),
            ("currency-api daily rates", currency_api_fx_fetcher),
        ],
    )
    warnings.extend(fx_snapshot["warnings"])

    def fetch_pair(request_row: tuple[int, str, str, str]) -> tuple[int, dict[str, Any]]:
        index, code, market, symbol = request_row
        result: dict[str, Any] = {"code": code, "symbol": symbol, "status": "ok"}
        fetchers = {
            "Yahoo Finance chart": lambda: yahoo_quote_fetcher(symbol, timeout),
            "Nasdaq last-sale summary": lambda: nasdaq_quote_fetcher(code, market, timeout),
            "Tencent Finance quote": lambda: tencent_quote_fetcher(code, market, timeout),
            "Sina Finance quote": lambda: sina_quote_fetcher(code, market, timeout),
        }
        fetched: dict[str, dict[str, Any]] = {}
        failures: list[str] = []
        expected_currency = MARKET_CURRENCY.get(market, "")
        with ThreadPoolExecutor(max_workers=4) as provider_executor:
            provider_futures = {
                source: provider_executor.submit(fetcher)
                for source, fetcher in fetchers.items()
            }
            for source, future in provider_futures.items():
                try:
                    quote_row = future.result()
                    price = _number(quote_row.get("price"))
                    timestamp = quote_row.get("timestamp")
                    source_currency = str(quote_row.get("currency") or expected_currency).upper()
                    if price is None or price <= 0:
                        raise LedgerPreflightError(f"invalid {source} price for {code}")
                    if source_currency != expected_currency:
                        raise LedgerPreflightError(f"unexpected {source} currency for {code}: {source_currency}")
                    if _is_stale(timestamp, now, max_quote_age_hours):
                        raise LedgerPreflightError(f"stale quote from {source} for {code}")
                    if _is_future_dated(timestamp, now):
                        raise LedgerPreflightError(f"future-dated quote from {source} for {code}")
                    fetched[source] = {
                        "price": price,
                        "timestamp": str(timestamp),
                        "source": quote_row.get("source", source),
                    }
                except LedgerPreflightError as error:
                    failures.append(str(error))
                except Exception as error:  # Defensive boundary for upstream payload changes.
                    failures.append(f"{source} returned an unexpected response for {code}: {type(error).__name__}")

        quote_pairs = []
        source_order = (
            "Yahoo Finance chart",
            "Nasdaq last-sale summary",
            "Tencent Finance quote",
            "Sina Finance quote",
        )
        for first_index, first_source in enumerate(source_order):
            for second_source in source_order[first_index + 1:]:
                first = fetched.get(first_source)
                second = fetched.get(second_source)
                if not first or not second:
                    continue
                difference_pct = abs(first["price"] - second["price"]) / first["price"] * 100
                if difference_pct <= MAX_QUOTE_SOURCE_DIFFERENCE_PCT:
                    first_time = _parse_timestamp(first["timestamp"])
                    second_time = _parse_timestamp(second["timestamp"])
                    if first_time is None or second_time is None:
                        continue
                    # Prefer the most recent pair whose prices agree. This
                    # avoids selecting two matching prior-close quotes when
                    # two independent providers agree on a later trade.
                    pair_as_of = min(first_time, second_time)
                    quote_pairs.append((pair_as_of, -difference_pct, -first_index, -source_order.index(second_source), first, second, difference_pct))

        quote_pair = max(quote_pairs, default=None)

        if quote_pair is None:
            result["status"] = "unavailable"
            if len(fetched) >= 2:
                prices = ", ".join(f"{source}={row['price']}" for source, row in fetched.items())
                result["warning"] = f"independent quotes differ by more than 1% for {code}: {prices}"
            else:
                result["warning"] = "; ".join(failures) or f"two fresh independent quotes unavailable for {code}"
        else:
            pair_as_of, _, _, _, first, second, difference_pct = quote_pair
            result.update({
                "quote_timestamp": pair_as_of.isoformat(),
                "quote_sources": [first["source"], second["source"]],
                "source_difference_pct": difference_pct,
                "quote_observations": {
                    source: {"price": row["price"], "timestamp": row["timestamp"]}
                    for source, row in fetched.items()
                },
                "yahoo_price": fetched.get("Yahoo Finance chart", {}).get("price"),
                "nasdaq_price": fetched.get("Nasdaq last-sale summary", {}).get("price"),
                "tencent_price": fetched.get("Tencent Finance quote", {}).get("price"),
                "sina_price": fetched.get("Sina Finance quote", {}).get("price"),
                "selected_price": first["price"],
            })
        return index, result

    # Each quote task fans out to four providers. Cap the outer pool so that
    # one report cannot burst dozens of requests at a provider and trigger
    # avoidable rate limits or dropped connections.
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(requests)))) as executor:
        futures = [executor.submit(fetch_pair, request_row) for request_row in requests]
        for future in futures:
            index, quote_row = future.result()
            output_positions[index].update(quote_row)
            if quote_row.get("status") != "ok":
                warnings.append(quote_row.get("warning", f"quote unavailable: {quote_row['code']}"))

    quote_timestamps = [
        parsed
        for item in output_positions
        if item.get("status") == "ok"
        and (parsed := _parse_timestamp(item.get("quote_timestamp"))) is not None
    ]
    fx_timestamps = fx_snapshot["timestamps"]
    as_of_candidates = quote_timestamps + fx_timestamps
    as_of = min(as_of_candidates).isoformat() if as_of_candidates else None
    quote_range_start = min(quote_timestamps).date().isoformat() if quote_timestamps else None
    quote_range_end = max(quote_timestamps).date().isoformat() if quote_timestamps else None
    fx_as_of = min(fx_timestamps).date().isoformat() if fx_timestamps else None
    used_quote_sources = sorted({
        str(source)
        for item in output_positions
        for source in item.get("quote_sources", [])
    })

    if warnings or len(requests) != len(positions) or any(item.get("status") != "ok" for item in output_positions):
        return {
            "status": "unavailable",
            "basis": "stock_pool",
            "as_of": as_of,
            "quote_range_start": quote_range_start,
            "quote_range_end": quote_range_end,
            "fx_as_of": fx_as_of,
            "weight": None,
            "positions": output_positions,
            "quote_sources": used_quote_sources,
            "fx_sources": fx_snapshot["sources"],
            "warnings": warnings,
        }

    try:
        pool_value = Decimal("0")
        target_value: Decimal | None = None
        wanted = _normalize_code(ticker)
        for item in output_positions:
            amount = Decimal(str(item["amount"]))
            price = Decimal(str(item["selected_price"]))
            currency = item["currency"]
            rate = Decimal("1") if currency == "CNY" else Decimal(str(fx_snapshot["rates"][f"{currency}_CNY"]))
            value = amount * price * rate
            item["value_cny"] = str(value.quantize(Decimal("0.01")))
            pool_value += value
            if _normalize_code(item["code"], item.get("market")) == wanted:
                target_value = value
        if pool_value <= 0:
            raise LedgerPreflightError("stock-pool market value must be positive")
        weight = (target_value / pool_value).quantize(Decimal("0.000001")) if target_value is not None else None
    except (KeyError, InvalidOperation, TypeError, ZeroDivisionError) as error:
        return {
            "status": "unavailable",
            "basis": "stock_pool",
            "as_of": as_of,
            "quote_range_start": quote_range_start,
            "quote_range_end": quote_range_end,
            "fx_as_of": fx_as_of,
            "weight": None,
            "positions": output_positions,
            "quote_sources": used_quote_sources,
            "fx_sources": fx_snapshot["sources"],
            "warnings": [f"stock-pool calculation failed: {type(error).__name__}"],
        }
    return {
        "status": "verified" if weight is not None else "ticker_not_in_active_stock_pool",
        "ticker": ticker,
        "basis": "stock_pool",
        "as_of": as_of,
        "quote_range_start": quote_range_start,
        "quote_range_end": quote_range_end,
        "fx_as_of": fx_as_of,
        "weight": str(weight) if weight is not None else None,
        "position_value_cny": str(target_value.quantize(Decimal("0.01"))) if target_value is not None else None,
        "stock_pool_value_cny": str(pool_value.quantize(Decimal("0.01"))),
        "fx_sources": fx_snapshot["sources"],
        "quote_sources": used_quote_sources,
        "positions": output_positions,
        "warnings": [],
    }


def extract_active_positions(
    payload: Any,
    *,
    now: datetime | None = None,
    max_price_age_hours: float = 72.0,
    endpoint: str = "/api/stocks",
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
        if not code:
            warnings.append("active position is missing its stock code")
            continue

        current_price = _number(item.get("currentPrice"))
        if current_price is not None and current_price <= 0:
            current_price = None
        price_timestamp = item.get("priceUpdateTime") or item.get("updatedAt")
        if current_price is None:
            warnings.append(f"missing or invalid current price: {code}")
        elif not price_timestamp:
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
                "holding_value": amount * current_price if current_price is not None else None,
                "price_timestamp": price_timestamp,
                "source": str(item.get("source") or f"Ledger {endpoint}"),
            }
        )

    positions.sort(key=lambda item: item["holding_value"] or 0.0, reverse=True)
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
            "Ledger base URL must not contain embedded credentials; use the Keychain or LEDGER_AUTH_TOKEN"
        )
    if parsed.query or parsed.fragment:
        raise LedgerPreflightError("Ledger base URL must not contain query parameters or fragments")
    return base_url.rstrip("/") + "/"


def _fetch_json(
    base_url: str,
    path: str,
    headers: dict[str, str],
    timeout: float,
    *,
    credential_name: str,
) -> Any:
    url = urljoin(_validate_base_url(base_url), path.lstrip("/"))
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "wall-street-equity-research/ledger-preflight",
            **headers,
        },
        method="GET",
    )
    for attempt in range(2):
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            break
        except HTTPError as error:
            if error.code in {502, 503, 504} and attempt == 0:
                time.sleep(1)
                continue
            if error.code in {401, 403}:
                if credential_name == "research token":
                    raise LedgerAuthenticationError(
                        f"Ledger rejected the read-only research token for {path} (HTTP {error.code}); "
                        f"check the macOS Keychain item {DEFAULT_KEYCHAIN_SERVICE}"
                    ) from error
                raise LedgerAuthenticationError(
                    f"Ledger rejected the session token for {path} (HTTP {error.code}); refresh LEDGER_AUTH_TOKEN"
                ) from error
            raise LedgerPreflightError(f"Ledger request failed for {path} (HTTP {error.code})") from error
        except (URLError, TimeoutError) as error:
            if attempt == 0:
                time.sleep(1)
                continue
            reason = error.reason if isinstance(error, URLError) else "request timed out"
            raise LedgerPreflightError(f"Ledger request failed for {path} after retry: {reason}") from error
    else:  # pragma: no cover - the loop either breaks or raises
        raise LedgerPreflightError(f"Ledger request failed for {path}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise LedgerPreflightError(f"Ledger returned non-JSON data for {path}") from error


def fetch_json(base_url: str, path: str, token: str, timeout: float) -> Any:
    return _fetch_json(
        base_url,
        path,
        {"Authorization": f"Bearer {token}"},
        timeout,
        credential_name="session token",
    )


def fetch_research_json(base_url: str, path: str, token: str, timeout: float) -> Any:
    return _fetch_json(
        base_url,
        path,
        {RESEARCH_TOKEN_HEADER: token},
        timeout,
        credential_name="research token",
    )


def read_keychain_token(service: str = DEFAULT_KEYCHAIN_SERVICE) -> str | None:
    """Read a local secret without putting it in argv, shell history, or output."""
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    token = result.stdout.strip()
    return token or None


def build_snapshot(
    stocks_payload: Any,
    *,
    base_url: str,
    retrieved_at: str | None = None,
    allocation_payload: Any | None = None,
    allocation_error: str | None = None,
    max_price_age_hours: float = 72.0,
    endpoint: str = "/api/stocks",
) -> dict[str, Any]:
    positions, warnings, inactive_count = extract_active_positions(
        stocks_payload,
        max_price_age_hours=max_price_age_hours,
        endpoint=endpoint,
    )
    snapshot: dict[str, Any] = {
        "source": "Ledger",
        "endpoint": endpoint,
        "base_url": base_url.rstrip("/"),
        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(),
        "active_position_count": len(positions),
        "holdings_verified": bool(positions),
        "holdings_complete": bool(positions) and not any(
            warning.startswith(("missing amount:", "negative amount", "active position is missing its stock code"))
            for warning in warnings
        ),
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


def _research_net_assets_with_fresh_stock_quotes(
    snapshot: dict[str, Any],
    pool_snapshot: Any,
) -> tuple[Decimal | None, str | None]:
    """Replace Ledger's saved stock values with the independently checked live stock pool."""
    summary = snapshot.get("portfolio_summary_snapshot")
    if not isinstance(summary, dict) or not isinstance(pool_snapshot, dict):
        return None, None
    if pool_snapshot.get("status") != "verified" or not snapshot.get("holdings_complete"):
        return None, None
    if _parse_timestamp(pool_snapshot.get("as_of")) is None:
        return None, None

    components = summary.get("components")
    if not isinstance(components, dict):
        return None, None
    for component_name in ("cash", "options", "liabilities", "exchange_rates", "crypto"):
        component = components.get(component_name)
        if not isinstance(component, dict) or component.get("status") not in {"fresh", "not_applicable"}:
            return None, None
        if component.get("status") == "fresh" and _parse_timestamp(component.get("as_of")) is None:
            return None, None

    try:
        ledger_net_assets = Decimal(str(summary["net_assets_cny"]))
        fresh_stock_value = Decimal(str(pool_snapshot["stock_pool_value_cny"]))
        fx_rates = summary["fx_rates_cny"]
        if not ledger_net_assets.is_finite() or not fresh_stock_value.is_finite():
            return None, None

        saved_stock_value = Decimal("0")
        for position in snapshot.get("positions", []):
            _, market = _normalize_code(position.get("code"), position.get("market"))
            currency = MARKET_CURRENCY.get(market)
            if currency is None:
                return None, None
            amount = Decimal(str(position["amount"]))
            price = _number(position.get("current_price"))
            # Ledger's allocation calculation treats a missing currentPrice as zero.
            price_value = Decimal("0") if price is None else Decimal(str(price))
            rate_value = Decimal("1") if currency == "CNY" else Decimal(str(fx_rates[f"{currency}_CNY"]))
            saved_stock_value += amount * price_value * rate_value

        net_assets = ledger_net_assets - saved_stock_value + fresh_stock_value
        if net_assets <= 0:
            return None, None
        valuation_dates = [
            date
            for value in [
                pool_snapshot.get("as_of"),
                *(components.get(name, {}).get("as_of") for name in (
                    "cash", "options", "liabilities", "exchange_rates", "crypto"
                )),
            ]
            if (date := _parse_timestamp(value)) is not None
        ]
        valuation_as_of = min(valuation_dates).isoformat() if valuation_dates else None
        return net_assets, valuation_as_of
    except (KeyError, InvalidOperation, TypeError, ValueError, ArithmeticError):
        return None, None


def _portfolio_weight_blockers(summary: Any) -> list[str]:
    """Name the exact Ledger components that prevent a current net-asset weight."""
    if not isinstance(summary, dict):
        return ["Ledger没有返回净资产汇总"]
    components = summary.get("components")
    if not isinstance(components, dict):
        return ["Ledger没有返回净资产各项数据的新鲜度"]
    labels = {
        "cash": "现金",
        "options": "期权",
        "liabilities": "负债",
        "exchange_rates": "汇率",
        "crypto": "加密资产",
    }
    blockers: list[str] = []
    for key, label in labels.items():
        component = components.get(key)
        if not isinstance(component, dict):
            blockers.append(f"缺少{label}数据")
            continue
        status = str(component.get("status") or "missing")
        if status == "not_applicable":
            continue
        as_of = _parse_timestamp(component.get("as_of"))
        if status == "fresh":
            if as_of is None:
                blockers.append(f"{label}数据没有有效日期")
            continue
        date_text = as_of.date().isoformat() if as_of else "日期未知"
        if status == "stale":
            blockers.append(f"{label}数据已过期（日期 {date_text}）")
        else:
            blockers.append(f"{label}数据{ '缺少' if status == 'missing' else '不可用' }（日期 {date_text}）")
    try:
        net_assets = Decimal(str(summary.get("net_assets_cny")))
        if not net_assets.is_finite() or net_assets <= 0:
            blockers.append("Ledger没有提供有效的净资产合计")
    except (InvalidOperation, TypeError, ValueError):
        blockers.append("Ledger没有提供有效的净资产合计")
    return blockers


def portfolio_context_draft(
    snapshot: dict[str, Any],
    ticker: str,
    *,
    rates_payload: Any | None = None,
) -> dict[str, Any]:
    """Draft a Spec ``portfolio_context`` for one ticker.

    Holdings presence can be confirmed even when a saved quote is stale. A
    weight is computed only when the complete holdings snapshot, dated net-assets
    summary, fresh all-stock quotes, and non-stock valuation inputs are verified.
    Target weight is never inferred.
    """
    wanted = _normalize_code(ticker)
    matches = [item for item in snapshot.get("positions", []) if _normalize_code(item.get("code"), item.get("market")) == wanted]
    pool_snapshot = snapshot.get("stock_pool_weight_snapshot")
    pool_weight = None
    if (
        isinstance(pool_snapshot, dict)
        and pool_snapshot.get("status") == "verified"
        and _normalize_code(pool_snapshot.get("ticker")) == wanted
    ):
        pool_weight = _number(pool_snapshot.get("weight"))
    summary = snapshot.get("portfolio_summary_snapshot")
    source = f"Ledger {snapshot.get('endpoint', '/api/stocks')} snapshot {snapshot.get('retrieved_at', '')}"
    if isinstance(summary, dict):
        source += (
            f"; {summary.get('endpoint', '/api/research/portfolio-summary')} net-assets snapshot "
            f"{summary.get('retrieved_at', '')}"
        )
    base = {
        "as_of": str(snapshot.get("retrieved_at", ""))[:10],
        "source": source,
        "net_assets_as_of": (
            snapshot.get("portfolio_summary_snapshot", {}).get("valuation_as_of")
            if isinstance(snapshot.get("portfolio_summary_snapshot"), dict)
            else None
        ),
        "net_assets_freshness_status": (
            snapshot.get("portfolio_summary_snapshot", {}).get("freshness_status")
            if isinstance(snapshot.get("portfolio_summary_snapshot"), dict)
            else None
        ),
        "target_weight": None,
        "tax_friction": "unknown",
        "constraints": "目标权重需由用户确认；Ledger 仅提供大类配置目标。",
        "stock_pool_weight": f"{pool_weight:.4f}" if pool_weight is not None else None,
        "stock_pool_weight_as_of": pool_snapshot.get("as_of") if pool_weight is not None else None,
        "stock_pool_weight_quote_range_start": pool_snapshot.get("quote_range_start") if pool_weight is not None else None,
        "stock_pool_weight_quote_range_end": pool_snapshot.get("quote_range_end") if pool_weight is not None else None,
        "stock_pool_weight_fx_as_of": pool_snapshot.get("fx_as_of") if pool_weight is not None else None,
        "stock_pool_weight_source": (
            f"{ '、'.join(pool_snapshot.get('quote_sources') or []) } 两源交叉核对；"
            f"{ '、'.join(pool_snapshot.get('fx_sources') or []) } 两源汇率；按全部活跃股票市值折算人民币"
        ) if pool_weight is not None else None,
    }
    if not snapshot.get("holdings_verified", snapshot.get("trusted", False)):
        return {**base, "position_status": "unknown", "confidence": "low", "current_weight": None,
                "constraints": "Ledger 没有提供可验证的 active holdings，持仓未核验：" + "；".join(snapshot.get("warnings", []))}
    if len(matches) > 1:
        return {**base, "position_status": "unknown", "confidence": "low", "current_weight": None,
                "constraints": "Ledger 中同一市场的股票有多条匹配记录，需核对后才能计算持仓。"}
    if not matches:
        if not snapshot.get("holdings_complete", snapshot.get("trusted", False)):
            return {**base, "position_status": "unknown", "confidence": "low", "current_weight": None,
                    "constraints": "Ledger 持仓列表存在缺失或异常记录，不能确认是否持有该股票。"}
        return {**base, "position_status": "not_held", "confidence": "high", "current_weight": None}
    position = matches[0]

    if isinstance(summary, dict) and pool_weight is not None:
        adjusted_net_assets, summary_as_of = _research_net_assets_with_fresh_stock_quotes(
            snapshot,
            pool_snapshot,
        )
        target_values = [
            Decimal(str(item.get("value_cny")))
            for item in pool_snapshot.get("positions", [])
            if _normalize_code(item.get("code"), item.get("market")) == wanted
            and item.get("value_cny") is not None
        ]
        if adjusted_net_assets is not None and len(target_values) == 1:
            weight = target_values[0] / adjusted_net_assets
            if weight.is_finite() and Decimal("0") <= weight <= Decimal("1"):
                freshness = str(summary.get("freshness_status") or "unknown")
                confidence = "high" if freshness == "fresh" else "medium"
                date_text = str(summary_as_of or "未知")[:10]
                constraints = (
                    f"当前约占 Ledger 净资产 {weight * 100:.2f}%，净资产估值截至 {date_text}。"
                    "计算时已用本次双源核对的全部股票报价替换 Ledger 保存的股票市值；"
                    "现金、期权、加密资产、负债和汇率采用 Ledger 摘要。目标权重需由用户确认。"
                )
                return {
                    **base,
                    "position_status": "held",
                    "confidence": confidence,
                    "current_weight": f"{weight:.4f}",
                    "net_assets_as_of": summary_as_of,
                    "constraints": constraints,
                }

    allocation = snapshot.get("allocation_snapshot")
    net_assets = _number(allocation.get("netAssets")) if isinstance(allocation, dict) else None
    currency = str(position.get("currency") or MARKET_CURRENCY.get(str(position.get("market") or "").upper(), "")).upper()
    rate = D_ONE if currency == "CNY" else None
    if currency in {"USD", "HKD"} and isinstance(rates_payload, dict):
        rate = _number(rates_payload.get(f"{currency}_CNY"))
    if not snapshot.get("trusted") or not net_assets or net_assets <= 0 or rate is None:
        display_name = str(position.get("name") or position.get("code") or wanted)
        if pool_weight is not None:
            pool_pct = f"{pool_weight * 100:.2f}%"
            blockers = _portfolio_weight_blockers(summary)
            blocker_text = "；".join(blockers) if blockers else "净资产快照或股票持仓数据不完整"
            constraints = (
                f"按最新双源核对的股价计算，{display_name}占全部股票市值 {pool_pct}；这个比例只比较股票，"
                f"不含现金、期权、加密资产和负债。{display_name}占全部资产净值的比例无法计算（UNAVAILABLE），原因："
                f"{blocker_text}。请在 Ledger 更新列出的数据后重跑；目标权重也需单独确认。"
                "当前组合动作为复核（REVIEW），不能直接执行加仓或减仓。"
            )
        else:
            blockers = _portfolio_weight_blockers(summary)
            blocker_text = "；".join(blockers) if blockers else "Ledger没有可用于替换旧股票市值的净资产快照"
            constraints = (
                "已确认持仓，但没有两家独立来源核对全部活跃股票的最新报价，"
                f"因此无法计算{display_name}占全部股票市值的比例；"
                f"总资产净值比例也无法计算（UNAVAILABLE），原因：{blocker_text}。"
                "目标权重需单独确认。当前组合动作为复核（REVIEW），不能直接执行加仓或减仓。"
            )
        return {**base, "position_status": "held", "confidence": "medium", "current_weight": None,
                "constraints": constraints}
    if position.get("holding_value") is None:
        return {**base, "position_status": "held", "confidence": "medium", "current_weight": None,
                "constraints": "已确认持仓，但没有可用价格，无法计算当前权重；目标权重需由用户确认。"}
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


def fetch_research_snapshot(
    base_url: str,
    token: str,
    timeout: float,
    max_price_age_hours: float,
) -> dict[str, Any]:
    """Read all active positions through Ledger's durable, read-only endpoint."""
    payload = fetch_research_json(base_url, "/api/research/holdings", token, timeout)
    retrieved_at = payload.get("retrieved_at") if isinstance(payload, dict) else None
    snapshot = build_snapshot(
        payload,
        base_url=base_url,
        retrieved_at=retrieved_at,
        max_price_age_hours=max_price_age_hours,
        endpoint="/api/research/holdings",
    )
    snapshot["credential_source"] = "macOS Keychain read-only research token"
    try:
        snapshot["portfolio_summary_snapshot"] = fetch_research_json(
            base_url, "/api/research/portfolio-summary", token, timeout
        )
        snapshot["portfolio_summary_status"] = "available"
        snapshot["allocation_status"] = "available_with_read_only_research_token"
    except LedgerPreflightError as error:
        snapshot["portfolio_summary_status"] = "unavailable"
        snapshot["portfolio_summary_error"] = str(error)
        snapshot["allocation_status"] = "unavailable_with_read_only_research_token"
    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LEDGER_API_BASE_URL", DEFAULT_LEDGER_API_BASE_URL),
        help="Ledger API base URL (or LEDGER_API_BASE_URL)",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-price-age-hours", type=float, default=72.0)
    parser.add_argument("--include-allocation", action="store_true")
    parser.add_argument(
        "--all-active",
        action="store_true",
        help="read every active position and refresh cross-checked quotes for all of them",
    )
    parser.add_argument("--ticker", help="emit a portfolio_context draft for this ticker")
    args = parser.parse_args(argv)
    if args.all_active and args.ticker:
        parser.error("--all-active cannot be combined with --ticker")

    try:
        research_token = read_keychain_token()
        session_token = os.environ.get("LEDGER_AUTH_TOKEN", "")
        if research_token:
            try:
                snapshot = fetch_research_snapshot(
                    args.base_url, research_token, args.timeout, args.max_price_age_hours
                )
            except LedgerAuthenticationError:
                if not session_token:
                    raise
                snapshot = fetch_snapshot(
                    args.base_url,
                    session_token,
                    args.timeout,
                    args.include_allocation or bool(args.ticker),
                    args.max_price_age_hours,
                )
                snapshot["credential_source"] = "LEDGER_AUTH_TOKEN session fallback"
        elif session_token:
            snapshot = fetch_snapshot(
                args.base_url,
                session_token,
                args.timeout,
                args.include_allocation or bool(args.ticker),
                args.max_price_age_hours,
            )
            snapshot["credential_source"] = "LEDGER_AUTH_TOKEN session"
        else:
            print(
                "No Ledger credential found. Store the read-only token in macOS Keychain "
                f"under service '{DEFAULT_KEYCHAIN_SERVICE}'; session-only calls require LEDGER_AUTH_TOKEN.",
                file=sys.stderr,
            )
            return 2

        if args.ticker:
            snapshot["stock_pool_weight_snapshot"] = build_stock_pool_weight_snapshot(
                snapshot.get("positions", []),
                ticker=args.ticker,
                max_quote_age_hours=args.max_price_age_hours,
                timeout=min(args.timeout, 10.0),
            )
            rates = None
            if snapshot.get("allocation_snapshot") is not None:
                try:
                    rates = fetch_json(args.base_url, "/api/exchange-rates", session_token, args.timeout)
                except LedgerPreflightError as error:
                    snapshot["warnings"].append(f"Ledger exchange rates unavailable: {error}")
            snapshot["portfolio_context_draft"] = portfolio_context_draft(snapshot, args.ticker, rates_payload=rates)
        elif args.all_active and snapshot.get("positions"):
            first_position = snapshot["positions"][0]
            target = f"{first_position.get('code', '')}.{first_position.get('market', '')}".rstrip(".")
            snapshot["stock_pool_weight_snapshot"] = build_stock_pool_weight_snapshot(
                snapshot.get("positions", []),
                ticker=target,
                max_quote_age_hours=args.max_price_age_hours,
                timeout=min(args.timeout, 10.0),
            )
    except LedgerPreflightError as error:
        print(f"Ledger preflight failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

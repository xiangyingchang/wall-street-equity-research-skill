#!/usr/bin/env python3
"""Prefetch A-share filing, quote, financial, dividend, and valuation data.

This script is intentionally dependency-light. It uses public SSE, Tencent, and
Eastmoney endpoints, handles GBK and gzip quirks, and emits a single JSON blob
for the equity-research skill to use as an Evidence Ledger starting point.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


SSE_BULLETIN_URL = "https://query.sse.com.cn/security/stock/queryCompanyBulletin.do"
EASTMONEY_FIN_URL = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/"
EASTMONEY_DC_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="
CHINABOND_CZB_URL = "https://yield.chinabond.com.cn/cbweb-czb-web/czb/czbChartSearch"
DEFAULT_CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "wall-street-equity-research"


def request_text(url: str, *, headers: dict[str, str] | None = None, encoding: str = "utf-8") -> str:
    default_headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
    }
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
    return raw.decode(encoding, errors="replace")


def get_json(url: str, *, headers: dict[str, str] | None = None) -> dict:
    return json.loads(request_text(url, headers=headers))


def post_json(url: str, *, headers: dict[str, str] | None = None, data: bytes = b"") -> dict | list:
    default_headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=default_headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8", errors="replace"))


def sh_symbol(code: str) -> str:
    code = code.strip().upper()
    if code.startswith("SH"):
        return code
    if code.startswith("SZ"):
        return code
    if code.endswith(".SH"):
        return "SH" + code[:6]
    if code.endswith(".SZ"):
        return "SZ" + code[:6]
    if code.startswith(("0", "2", "3")):
        return "SZ" + code
    return "SH" + code


def numeric_code(code: str) -> str:
    m = re.search(r"(\d{6})", code)
    if not m:
        raise SystemExit(f"Cannot find 6-digit stock code in {code!r}")
    return m.group(1)


def tencent_key(code: str) -> str:
    n = numeric_code(code)
    if n.startswith(("5", "6", "9")):
        return "sh" + n
    return "sz" + n


def sse_announcements(code: str, begin: str, end: str) -> list[dict]:
    n = numeric_code(code)
    if not tencent_key(code).startswith("sh"):
        return []
    params = {
        "jsonCallBack": "cb",
        "isPagination": "true",
        "productId": n,
        "keyWord": "",
        "securityType": "0101,120100,020100,020200,120200",
        "reportType": "ALL",
        "beginDate": begin,
        "endDate": end,
        "pageHelp.pageSize": "200",
        "pageHelp.pageNo": "1",
        "pageHelp.beginPage": "1",
        "pageHelp.cacheSize": "1",
        "pageHelp.endPage": "5",
        "_": str(int(dt.datetime.now().timestamp() * 1000)),
    }
    url = SSE_BULLETIN_URL + "?" + urllib.parse.urlencode(params)
    text = request_text(
        url,
        headers={"Referer": "https://www.sse.com.cn/disclosure/listedinfo/announcement/"},
    )
    if text.startswith("cb(") and text.endswith(")"):
        text = text[3:-1]
    data = json.loads(text)
    rows = data.get("pageHelp", {}).get("data") or []
    wanted = []
    keywords = ("年度报告", "季度报告", "半年度报告", "利润分配", "权益分派", "分红回报")
    for row in rows:
        title = row.get("TITLE") or ""
        if any(k in title for k in keywords):
            url_path = row.get("URL") or ""
            wanted.append(
                {
                    "date": row.get("SSEDATE"),
                    "title": title,
                    "url": "https://www.sse.com.cn" + url_path if url_path.startswith("/") else url_path,
                    "type": row.get("BULLETIN_TYPE"),
                }
            )
    return wanted


def eastmoney_zyzb(code: str, type_: int) -> list[dict]:
    params = {"type": type_, "code": sh_symbol(code)}
    url = EASTMONEY_FIN_URL + "ZYZBAjaxNew?" + urllib.parse.urlencode(params)
    return get_json(url, headers={"Referer": "https://emweb.securities.eastmoney.com/"}).get("data") or []


def eastmoney_table(code: str, tab: str, count: int = 8) -> list[dict]:
    symbol = sh_symbol(code)
    headers = {
        "Referer": "https://emweb.securities.eastmoney.com/",
        "Accept-Encoding": "gzip",
    }
    params = {"companyType": 4, "reportDateType": 0, "code": symbol}
    date_url = EASTMONEY_FIN_URL + tab + "DateAjaxNew?" + urllib.parse.urlencode(params)
    dates_data = get_json(date_url, headers=headers).get("data") or []
    dates = ",".join((row.get("REPORT_DATE") or "")[:10] for row in dates_data[:count])
    data_params = {
        "companyType": 4,
        "reportDateType": 0,
        "reportType": 1,
        "dates": dates,
        "code": symbol,
    }
    data_url = EASTMONEY_FIN_URL + tab + "AjaxNew?" + urllib.parse.urlencode(data_params)
    return get_json(data_url, headers=headers).get("data") or []


def eastmoney_dividends(code: str, page_size: int = 10) -> list[dict]:
    n = numeric_code(code)
    params = {
        "sortColumns": "NOTICE_DATE",
        "sortTypes": "-1",
        "pageSize": str(page_size),
        "pageNumber": "1",
        "reportName": "RPT_SHAREBONUS_DET",
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{n}")',
        "source": "WEB",
        "client": "WEB",
    }
    url = EASTMONEY_DC_URL + "?" + urllib.parse.urlencode(params)
    result = get_json(url, headers={"Referer": "https://data.eastmoney.com/"}).get("result") or {}
    rows = result.get("data") or []
    keys = [
        "NOTICE_DATE",
        "REPORT_DATE",
        "IMPL_PLAN_PROFILE",
        "PRETAX_BONUS_RMB",
        "ASSIGN_PROGRESS",
        "EQUITY_RECORD_DATE",
        "EX_DIVIDEND_DATE",
        "TOTAL_SHARES",
        "BASIC_EPS",
    ]
    return [{k: row.get(k) for k in keys} for row in rows]


def tencent_quotes(codes: list[str]) -> dict[str, dict]:
    keys = [tencent_key(c) for c in codes]
    text = request_text(TENCENT_QUOTE_URL + ",".join(keys), encoding="gbk")
    quotes: dict[str, dict] = {}
    for line in text.splitlines():
        if not line.strip() or '="' not in line:
            continue
        body = line.split('="', 1)[1].rstrip('";')
        fields = body.split("~")
        if len(fields) < 50:
            continue
        code = fields[2]
        quotes[code] = {
            "name": fields[1],
            "code": code,
            "price": to_float(fields[3]),
            "prev_close": to_float(fields[4]),
            "open": to_float(fields[5]),
            "datetime": fields[30] if len(fields) > 30 else None,
            "change": to_float(fields[31]) if len(fields) > 31 else None,
            "change_pct": to_float(fields[32]) if len(fields) > 32 else None,
            "high": to_float(fields[33]) if len(fields) > 33 else None,
            "low": to_float(fields[34]) if len(fields) > 34 else None,
            "turnover_rate": to_float(fields[38]) if len(fields) > 38 else None,
            "pe_ttm": to_float(fields[39]) if len(fields) > 39 else None,
            "market_cap_yi": to_float(fields[45]) if len(fields) > 45 else None,
            "pb": to_float(fields[46]) if len(fields) > 46 else None,
            "high_52w": to_float(fields[47]) if len(fields) > 47 else None,
            "low_52w": to_float(fields[48]) if len(fields) > 48 else None,
            "volume_lot": to_float(fields[36]) if len(fields) > 36 else None,
            "amount_wan": to_float(fields[37]) if len(fields) > 37 else None,
            # Tencent's tail fields vary by market and can shift. Use
            # Eastmoney dividend records as the primary share-count source in
            # derived calculations; quote payload share fields are not stable
            # enough for valuation math.
            "total_shares": None,
            "float_shares": None,
        }
    return quotes


def to_float(value) -> float | None:
    try:
        if value in (None, "", "--"):
            return None
        return float(value)
    except Exception:
        return None


def by_report(rows: list[dict]) -> dict[str, dict]:
    return {row.get("REPORT_DATE_NAME"): row for row in rows if row.get("REPORT_DATE_NAME")}


def ttm(fin_quarter: list[dict], table: list[dict], field: str) -> float | None:
    data = by_report(table)
    try:
        return (
            float(data["2025年报"][field])
            + float(data["2026一季报"][field])
            - float(data["2025一季报"][field])
        )
    except Exception:
        return None


def ttm_metric(zy_quarter: list[dict], field: str) -> float | None:
    data = by_report(zy_quarter)
    try:
        return (
            float(data["2025年报"][field])
            + float(data["2026一季报"][field])
            - float(data["2025一季报"][field])
        )
    except Exception:
        return None


def solve_payback(multiple: float, r: float = 0.0) -> float | None:
    if not multiple or multiple <= 0:
        return None
    lo, hi = -0.9, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        value = sum(((1 + mid) / (1 + r)) ** t for t in range(1, 11))
        if value < multiple:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def cache_age_days(cache: dict) -> float | None:
    fetched_at = cache.get("fetched_at")
    if not fetched_at:
        return None
    try:
        ts = dt.datetime.fromisoformat(fetched_at)
    except ValueError:
        return None
    return (dt.datetime.now() - ts).total_seconds() / 86400


def cache_is_fresh(cache: dict, max_age_days: int) -> bool:
    age = cache_age_days(cache)
    return age is not None and age <= max_age_days


def read_json_file(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception:
        return None


def write_json_file(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_china_10y_yield() -> dict:
    data = post_json(
        CHINABOND_CZB_URL,
        headers={
            "Referer": "https://yield.chinabond.com.cn/cbweb-czb-web/czb/moreInfo?locale=cn_ZH&nameType=1",
            "Origin": "https://yield.chinabond.com.cn",
        },
    )
    if not isinstance(data, list) or not data:
        raise RuntimeError("Unexpected ChinaBond response shape")
    curve = data[0]
    series = curve.get("seriesData") or []
    ten_year = None
    for tenor, value in series:
        if abs(float(tenor) - 10.0) < 1e-9:
            ten_year = float(value)
            break
    if ten_year is None:
        raise RuntimeError("10Y point not found in ChinaBond curve")
    return {
        "value_pct": ten_year,
        "value_decimal": ten_year / 100,
        "worktime": curve.get("worktime"),
        "curve_name": curve.get("ycDefName"),
        "source": "ChinaBond / Ministry of Finance yield curve",
        "source_url": "https://yield.chinabond.com.cn/cbweb-czb-web/czb/moreInfo?locale=cn_ZH&nameType=1",
        "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
        "stale": False,
    }


def get_china_10y_yield(cache_days: int, refresh: bool = False) -> dict:
    cache_path = DEFAULT_CACHE_DIR / "china_10y_yield.json"
    cached = read_json_file(cache_path)
    if cached and not refresh and cache_is_fresh(cached, cache_days):
        cached = dict(cached)
        cached["cache_path"] = str(cache_path)
        cached["cache_age_days"] = cache_age_days(cached)
        cached["from_cache"] = True
        cached["stale"] = False
        return cached
    try:
        fresh = fetch_china_10y_yield()
        write_json_file(cache_path, fresh)
        fresh["cache_path"] = str(cache_path)
        fresh["cache_age_days"] = 0
        fresh["from_cache"] = False
        return fresh
    except Exception as exc:
        if cached:
            cached = dict(cached)
            cached["cache_path"] = str(cache_path)
            cached["cache_age_days"] = cache_age_days(cached)
            cached["from_cache"] = True
            cached["stale"] = True
            cached["refresh_error"] = str(exc)
            return cached
        return {
            "value_pct": 1.72,
            "value_decimal": 0.0172,
            "worktime": None,
            "source": "fallback placeholder",
            "source_url": None,
            "fetched_at": None,
            "cache_path": str(cache_path),
            "cache_age_days": None,
            "from_cache": False,
            "stale": True,
            "refresh_error": str(exc),
        }


def first_number(rows: list[dict], key: str) -> float | None:
    for row in rows:
        value = to_float(row.get(key))
        if value:
            return value
    return None


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def parse_dividend_per_share(dividend_row: dict | None) -> float | None:
    if not dividend_row:
        return None
    profile = dividend_row.get("IMPL_PLAN_PROFILE") or ""
    match = re.search(r"10派([0-9.]+)", profile)
    if match:
        return float(match.group(1)) / 10
    pretax_bonus = to_float(dividend_row.get("PRETAX_BONUS_RMB"))
    if pretax_bonus is not None:
        return pretax_bonus / 10
    return None


def build_peer_comparison(quotes: dict[str, dict], main_code: str, peer_codes: list[str]) -> list[dict]:
    ordered_codes = [numeric_code(main_code)] + [numeric_code(code) for code in peer_codes]
    rows = []
    for code in ordered_codes:
        quote = quotes.get(code)
        if not quote:
            rows.append({"code": code, "missing": True})
            continue
        rows.append(
            {
                "code": code,
                "name": quote.get("name"),
                "price": quote.get("price"),
                "change_pct": quote.get("change_pct"),
                "pe_ttm": quote.get("pe_ttm"),
                "pb": quote.get("pb"),
                "market_cap_yi": quote.get("market_cap_yi"),
                "turnover_rate": quote.get("turnover_rate"),
                "datetime": quote.get("datetime"),
                "missing": False,
            }
        )
    return rows


def build_summary(code: str, peer_codes: list[str], *, china_10y_cache_days: int = 30, refresh_china_10y: bool = False) -> dict:
    today = dt.date.today()
    begin = (today.replace(year=today.year - 1)).isoformat()
    end = today.isoformat()
    quote_codes = [code] + peer_codes
    quotes = tencent_quotes(quote_codes)
    n = numeric_code(code)
    quote = quotes.get(n) or {}

    zyzb_annual = eastmoney_zyzb(code, 1)
    zyzb_quarter = eastmoney_zyzb(code, 0)
    balance = eastmoney_table(code, "zcfzb")
    income = eastmoney_table(code, "lrb")
    cashflow = eastmoney_table(code, "xjllb")
    dividends = eastmoney_dividends(code)
    china_10y = get_china_10y_yield(china_10y_cache_days, refresh=refresh_china_10y)
    china_10y_r = float(china_10y.get("value_decimal") or 0.0172)

    q_zy = by_report(zyzb_quarter)
    q_bal = by_report(balance)
    q_inc = by_report(income)
    q_cf = by_report(cashflow)

    total_shares = first_number(dividends, "TOTAL_SHARES") or quote.get("total_shares")
    price = quote.get("price")
    eps_ttm = ttm_metric(zyzb_quarter, "EPSJB")
    revenue_ttm = ttm(zyzb_quarter, income, "TOTAL_OPERATE_INCOME")
    net_profit_ttm = ttm(zyzb_quarter, income, "PARENT_NETPROFIT")
    invest_income_ttm = ttm(zyzb_quarter, income, "INVEST_INCOME")
    joint_invest_income_ttm = ttm(zyzb_quarter, income, "INVEST_JOINT_INCOME")
    ocf_ttm = ttm(zyzb_quarter, cashflow, "NETCASH_OPERATE")
    capex_ttm = ttm(zyzb_quarter, cashflow, "CONSTRUCT_LONG_ASSET")
    fcf_ttm = ocf_ttm - capex_ttm if ocf_ttm is not None and capex_ttm is not None else None
    fcf_per_share = fcf_ttm / total_shares if fcf_ttm is not None and total_shares else None
    pe_ttm = price / eps_ttm if price and eps_ttm else quote.get("pe_ttm")
    p_fcf = price / fcf_per_share if price and fcf_per_share else None
    market_cap = price * total_shares if price and total_shares else None
    if not market_cap and quote.get("market_cap_yi"):
        market_cap = quote["market_cap_yi"] * 100_000_000

    latest_bal = q_bal.get("2026一季报") or q_bal.get("2025年报") or {}
    debt_fields = ["SHORT_LOAN", "NONCURRENT_LIAB_1YEAR", "LONG_LOAN", "BOND_PAYABLE"]
    interest_bearing_debt = sum(float(latest_bal.get(k) or 0) for k in debt_fields)
    cash = to_float(latest_bal.get("MONETARYFUNDS")) or 0
    ev = market_cap + interest_bearing_debt - cash if market_cap else None
    ev_fcf = ev / fcf_ttm if ev and fcf_ttm else None
    net_debt = interest_bearing_debt - cash if interest_bearing_debt is not None else None

    latest_dividend = dividends[0] if dividends else None
    dps = parse_dividend_per_share(latest_dividend)
    dividend_yield = dps / price if dps is not None and price else None

    invest_income_to_revenue = ratio(invest_income_ttm, revenue_ttm)
    invest_income_to_net_profit = ratio(invest_income_ttm, net_profit_ttm)
    is_equity_method_holding = bool(
        invest_income_to_revenue is not None
        and invest_income_to_net_profit is not None
        and invest_income_to_revenue >= 1.0
        and invest_income_to_net_profit >= 0.5
    )
    business_model_flags = {
        "equity_method_holding_company": is_equity_method_holding,
        "invest_income_to_revenue": invest_income_to_revenue,
        "invest_income_to_net_profit": invest_income_to_net_profit,
        "fcf_requires_deweighting": bool(is_equity_method_holding and fcf_ttm is not None),
        "notes": [],
    }
    if is_equity_method_holding:
        business_model_flags["notes"].append(
            "Investment income dominates revenue/profit; plain consolidated FCF should be deweighted and EPS/dividends/underlying investee quality should be emphasized."
        )

    manual_verification_notes = [
        "Spot-check latest annual and quarterly filings before final rating.",
        "Verify current quote timestamp and valuation multiples if market is open or delayed data matters.",
    ]
    if is_equity_method_holding:
        manual_verification_notes.append(
            "Manually verify major equity-method investees, ownership percentages, dividend pass-through, and investment-income sustainability from the annual report."
        )
    if not tencent_key(code).startswith("sh"):
        manual_verification_notes.append("Fetch CNINFO filing links manually for Shenzhen-listed companies.")

    payback = {}
    for name, multiple in [("pe_ttm", pe_ttm), ("p_fcf_ttm", p_fcf), ("ev_fcf_ttm", ev_fcf)]:
        if multiple:
            payback[name] = {
                "multiple": multiple,
                "nominal_g": solve_payback(multiple, 0.0),
                "r_china_10y_1": solve_payback(multiple, china_10y_r),
                "r_china_10y_2": solve_payback(multiple, china_10y_r * 2),
                "r_8pct": solve_payback(multiple, 0.08),
                "r_10pct": solve_payback(multiple, 0.10),
            }

    peer_comparison = build_peer_comparison(quotes, code, peer_codes)

    payload = {
        "meta": {
            "code": n,
            "symbol": sh_symbol(code),
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "notes": [
                "China 10Y yield is fetched from ChinaBond and cached locally for the configured cache window.",
                "SSE PDF links confirm Tier 1 filings for Shanghai-listed companies; text/table extraction depends on local PDF tooling and is not attempted here.",
                "For Shenzhen-listed companies, this script currently returns financial/quote/dividend data but not CNINFO filing links.",
            ],
        },
        "summary": {
            "company": {
                "code": n,
                "symbol": sh_symbol(code),
                "name": quote.get("name"),
            },
            "quote": {
                "price": price,
                "datetime": quote.get("datetime"),
                "change_pct": quote.get("change_pct"),
                "market_cap": market_cap,
                "market_cap_yi": quote.get("market_cap_yi"),
                "pe_ttm": pe_ttm,
                "pb": quote.get("pb"),
                "turnover_rate": quote.get("turnover_rate"),
                "high_52w": quote.get("high_52w"),
                "low_52w": quote.get("low_52w"),
                "source": "Tencent quote",
                "source_tier": "Tier 2",
            },
            "rates": {
                "china_10y_value_pct": china_10y.get("value_pct"),
                "china_10y_value_decimal": china_10y.get("value_decimal"),
                "china_10y_worktime": china_10y.get("worktime"),
                "china_10y_from_cache": china_10y.get("from_cache"),
                "china_10y_stale": china_10y.get("stale"),
                "opportunity_cost_china_10y_x2": china_10y_r * 2,
            },
            "ttm": {
                "revenue": revenue_ttm,
                "net_profit": net_profit_ttm,
                "eps": eps_ttm,
                "ocf": ocf_ttm,
                "capex": capex_ttm,
                "fcf": fcf_ttm,
                "fcf_per_share": fcf_per_share,
                "investment_income": invest_income_ttm,
                "joint_investment_income": joint_invest_income_ttm,
            },
            "balance": {
                "cash": cash,
                "interest_bearing_debt_approx": interest_bearing_debt,
                "net_debt_approx": net_debt,
                "ev_approx": ev,
            },
            "dividend": {
                "latest_plan": latest_dividend,
                "dps_pretax": dps,
                "dividend_yield": dividend_yield,
            },
            "valuation": {
                "pe_ttm": pe_ttm,
                "p_fcf_ttm": p_fcf,
                "ev_fcf_ttm": ev_fcf,
                "payback": payback,
            },
            "business_model_flags": business_model_flags,
            "manual_verification_notes": manual_verification_notes,
        },
        "rates": {
            "china_10y": china_10y,
        },
        "announcements": sse_announcements(code, begin, end),
        "quotes": quotes,
        "peer_comparison": peer_comparison,
        "financials": {
            "zyzb_annual": zyzb_annual[:8],
            "zyzb_quarter": zyzb_quarter[:8],
            "balance": balance[:5],
            "income": income[:5],
            "cashflow": cashflow[:5],
            "dividends": dividends[:10],
        },
        "derived": {
            "price": price,
            "total_shares": total_shares,
            "market_cap": market_cap,
            "eps_ttm": eps_ttm,
            "revenue_ttm": revenue_ttm,
            "net_profit_ttm": net_profit_ttm,
            "invest_income_ttm": invest_income_ttm,
            "joint_invest_income_ttm": joint_invest_income_ttm,
            "ocf_ttm": ocf_ttm,
            "capex_ttm": capex_ttm,
            "fcf_ttm": fcf_ttm,
            "fcf_per_share": fcf_per_share,
            "pe_ttm": pe_ttm,
            "p_fcf_ttm": p_fcf,
            "interest_bearing_debt_approx": interest_bearing_debt,
            "cash": cash,
            "ev_approx": ev,
            "ev_fcf_ttm": ev_fcf,
            "payback": payback,
        },
    }
    return payload


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code", help="A-share code, e.g. 600900 or SH600900")
    parser.add_argument("--peers", nargs="*", default=[], help="Peer A-share codes")
    parser.add_argument("--indent", type=int, default=2)
    parser.add_argument("--china-10y-cache-days", type=int, default=30, help="Refresh China 10Y yield cache after this many days")
    parser.add_argument("--refresh-china-10y", action="store_true", help="Force refresh China 10Y yield cache")
    args = parser.parse_args(argv)
    payload = build_summary(
        args.code,
        args.peers,
        china_10y_cache_days=args.china_10y_cache_days,
        refresh_china_10y=args.refresh_china_10y,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=args.indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

import sys
import unittest
import json
from http.client import RemoteDisconnected
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest import mock
from urllib.error import URLError


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ledger_portfolio_preflight import (  # noqa: E402
    LedgerPreflightError,
    _public_json,
    _crosscheck_fx_sources,
    _validate_base_url,
    build_snapshot,
    build_stock_pool_weight_snapshot,
    extract_active_positions,
    fetch_research_snapshot,
    fetch_currency_api_fx_rates,
    fetch_frankfurter_fx_rates,
    fetch_nasdaq_quote,
    fetch_research_json,
    fetch_sina_quote,
    fetch_tencent_quote,
    portfolio_context_draft,
    read_keychain_token,
)


class LedgerPortfolioPreflightTests(unittest.TestCase):
    def test_filters_zero_quantity_history_and_calculates_value(self):
        positions, warnings, inactive_count = extract_active_positions([
            {
                "code": "META",
                "name": "Meta",
                "market": "US",
                "currency": "USD",
                "amount": 10,
                "currentPrice": 688,
                "priceUpdateTime": "2026-08-02T00:00:00Z",
            },
            {"code": "CME", "amount": 0, "currentPrice": 200},
        ], now=datetime(2026, 8, 2, tzinfo=timezone.utc))

        self.assertEqual(inactive_count, 1)
        self.assertEqual(warnings, [])
        self.assertEqual(positions[0]["code"], "META")
        self.assertEqual(positions[0]["holding_value"], 6880)
        self.assertEqual(positions[0]["source"], "Ledger /api/stocks")

    def test_missing_timestamp_is_explicit_warning(self):
        positions, warnings, _ = extract_active_positions([
            {"code": "MU", "amount": 2, "currentPrice": 100},
        ])

        self.assertEqual(len(positions), 1)
        self.assertIn("missing price timestamp: MU", warnings)

    def test_stale_timestamp_is_explicit_warning(self):
        positions, warnings, _ = extract_active_positions(
            [{"code": "MU", "amount": 2, "currentPrice": 100, "priceUpdateTime": "2026-07-25T00:00:00Z"}],
            now=datetime(2026, 8, 2, tzinfo=timezone.utc),
            max_price_age_hours=72,
        )

        self.assertEqual(len(positions), 1)
        self.assertIn("stale price timestamp: MU", warnings)

    def test_active_position_survives_missing_price_for_holding_status(self):
        positions, warnings, _ = extract_active_positions([
            {"code": "MU", "amount": 2, "currentPrice": 0},
        ])

        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["amount"], 2)
        self.assertIsNone(positions[0]["current_price"])
        self.assertIsNone(positions[0]["holding_value"])
        self.assertIn("missing or invalid current price: MU", warnings)

    def test_snapshot_keeps_allocation_warning_and_provenance(self):
        snapshot = build_snapshot(
            [{"code": "META", "amount": 1, "currentPrice": 10, "updatedAt": "2026-08-02"}],
            base_url="http://localhost:3000",
            retrieved_at="2026-08-02T00:00:00+00:00",
            allocation_payload={"warning": "股票价格快照可能滞后"},
        )

        self.assertEqual(snapshot["source"], "Ledger")
        self.assertEqual(snapshot["endpoint"], "/api/stocks")
        self.assertEqual(snapshot["retrieved_at"], "2026-08-02T00:00:00+00:00")
        self.assertEqual(snapshot["allocation_endpoint"], "/api/allocation")
        self.assertIn("Ledger allocation warning: 股票价格快照可能滞后", snapshot["warnings"])

    def test_allocation_failure_does_not_drop_positions(self):
        snapshot = build_snapshot(
            [{"code": "META", "amount": 1, "currentPrice": 10}],
            base_url="http://localhost:3000",
            allocation_error="HTTP 503",
        )

        self.assertEqual(snapshot["active_position_count"], 1)
        self.assertEqual(snapshot["positions"][0]["code"], "META")
        self.assertEqual(snapshot["allocation_status"], "unavailable")
        self.assertIn("Ledger allocation unavailable: HTTP 503", snapshot["warnings"])

    def test_unexpected_payload_fails_closed(self):
        with self.assertRaises(LedgerPreflightError):
            extract_active_positions({"message": "not a stock list"})

    def test_base_url_rejects_embedded_credentials(self):
        with self.assertRaisesRegex(LedgerPreflightError, "embedded credentials"):
            _validate_base_url("https://user:password@example.com")

    def test_empty_active_snapshot_is_explicit(self):
        snapshot = build_snapshot([], base_url="http://localhost:3000")

        self.assertEqual(snapshot["active_position_count"], 0)
        self.assertIn("no active positions", snapshot["warnings"][0])


class LedgerSafetyAndDraftTests(unittest.TestCase):
    NOW = datetime(2026, 8, 2, tzinfo=timezone.utc)

    def _snapshot(self, stocks, allocation=None):
        from unittest import mock
        with mock.patch("ledger_portfolio_preflight.datetime") as fake:
            fake.now.return_value = self.NOW
            fake.fromisoformat = datetime.fromisoformat
            return build_snapshot(stocks, base_url="http://localhost:3000", allocation_payload=allocation)

    def test_remote_http_is_rejected(self):
        with self.assertRaises(LedgerPreflightError):
            _validate_base_url("http://ledger.example.com")
        self.assertEqual(_validate_base_url("https://ledger.example.com"), "https://ledger.example.com/")
        self.assertEqual(_validate_base_url("http://127.0.0.1:3000"), "http://127.0.0.1:3000/")

    def test_negative_amount_is_warned_not_hidden(self):
        positions, warnings, inactive = extract_active_positions([{"code": "META", "amount": -5, "currentPrice": 1}], now=self.NOW)
        self.assertEqual(positions, [])
        self.assertEqual(inactive, 0)
        self.assertTrue(any("negative amount" in item for item in warnings))

    def test_draft_computes_weight_only_when_verified(self):
        stocks = [{"code": "META", "currency": "USD", "amount": 10, "currentPrice": 700, "priceUpdateTime": "2026-08-01T00:00:00Z"}]
        snapshot = self._snapshot(stocks, allocation={"netAssets": 100000, "warning": ""})
        self.assertTrue(snapshot["trusted"])
        draft = portfolio_context_draft(snapshot, "META.US", rates_payload={"USD_CNY": 7.0})
        self.assertEqual(draft["position_status"], "held")
        self.assertEqual(draft["current_weight"], "0.4900")
        self.assertIsNone(draft["target_weight"])

    def test_draft_confirms_holding_when_quote_is_stale(self):
        stocks = [{"code": "META", "currency": "USD", "amount": 10, "currentPrice": 700}]
        snapshot = self._snapshot(stocks, allocation={"netAssets": 100000})
        self.assertFalse(snapshot["trusted"])
        draft = portfolio_context_draft(snapshot, "META", rates_payload={"USD_CNY": 7.0})
        self.assertEqual(draft["position_status"], "held")
        self.assertEqual(draft["confidence"], "medium")
        self.assertIsNone(draft["current_weight"])

    def test_draft_shows_stock_pool_weight_but_keeps_net_asset_weight_unknown(self):
        snapshot = self._snapshot([
            {"code": "00700", "market": "HK", "currency": "HKD", "amount": 100,
             "currentPrice": 474, "priceUpdateTime": "2026-09-06T00:00:00Z"},
        ])
        snapshot["stock_pool_weight_snapshot"] = {
            "status": "verified",
            "ticker": "00700.HK",
            "weight": "0.422628",
            "as_of": "2026-10-21T20:00:00+00:00",
        }

        draft = portfolio_context_draft(snapshot, "0700.HK")

        self.assertEqual(draft["position_status"], "held")
        self.assertIsNone(draft["current_weight"])
        self.assertEqual(draft["stock_pool_weight"], "0.4226")
        self.assertIn("不含现金", draft["constraints"])
        self.assertIn("占全部资产净值的比例无法计算（UNAVAILABLE）", draft["constraints"])

    def test_draft_revalues_the_full_stock_pool_before_calculating_net_asset_weight(self):
        snapshot = self._snapshot([
            {"code": "META", "market": "US", "currency": "USD", "amount": 10,
             "currentPrice": 600, "priceUpdateTime": "2026-07-20T00:00:00Z"},
            {"code": "AAPL", "market": "US", "currency": "USD", "amount": 10,
             "currentPrice": 100, "priceUpdateTime": "2026-07-20T00:00:00Z"},
        ])
        snapshot["portfolio_summary_snapshot"] = {
            "net_assets_cny": 100000,
            "valuation_as_of": "2026-08-01T00:00:00Z",
            "freshness_status": "stale",
            "components": {
                "stocks": {"status": "stale"},
                "cash": {"status": "fresh", "as_of": "2026-08-01T00:00:00Z"},
                "options": {"status": "not_applicable"},
                "liabilities": {"status": "not_applicable"},
                "exchange_rates": {"status": "fresh", "as_of": "2026-08-02T00:00:00Z"},
                "crypto": {"status": "not_applicable"},
            },
            "fx_rates_cny": {"USD_CNY": 7, "HKD_CNY": 0.9},
        }
        snapshot["stock_pool_weight_snapshot"] = {
            "status": "verified",
            "ticker": "META.US",
            "as_of": "2026-08-02T00:00:00Z",
            "weight": "0.769231",
            "stock_pool_value_cny": "91000.00",
            "positions": [
                {"code": "META", "market": "US", "value_cny": "70000.00"},
                {"code": "AAPL", "market": "US", "value_cny": "21000.00"},
            ],
        }

        draft = portfolio_context_draft(snapshot, "META.US")

        self.assertEqual(draft["position_status"], "held")
        self.assertEqual(draft["current_weight"], "0.4930")
        self.assertEqual(draft["confidence"], "medium")
        self.assertEqual(draft["net_assets_as_of"], "2026-08-01T00:00:00+00:00")
        self.assertIn("替换 Ledger 保存的股票市值", draft["constraints"])

    def test_stale_non_stock_snapshot_blocks_total_net_asset_weight(self):
        snapshot = self._snapshot([
            {"code": "META", "market": "US", "currency": "USD", "amount": 10,
             "currentPrice": 600, "priceUpdateTime": "2026-07-20T00:00:00Z"},
        ])
        snapshot["portfolio_summary_snapshot"] = {
            "net_assets_cny": 100000,
            "valuation_as_of": "2026-08-01T00:00:00Z",
            "freshness_status": "stale",
            "components": {
                "stocks": {"status": "stale"},
                "cash": {"status": "stale", "as_of": "2026-07-25T00:00:00Z"},
                "options": {"status": "not_applicable"},
                "liabilities": {"status": "stale", "as_of": "2025-02-16T09:16:32Z"},
                "exchange_rates": {"status": "fresh", "as_of": "2026-08-02T00:00:00Z"},
                "crypto": {"status": "not_applicable"},
            },
            "fx_rates_cny": {"USD_CNY": 7, "HKD_CNY": 0.9},
        }
        snapshot["stock_pool_weight_snapshot"] = {
            "status": "verified",
            "ticker": "META.US",
            "as_of": "2026-08-02T00:00:00Z",
            "weight": "1.000000",
            "stock_pool_value_cny": "70000.00",
            "positions": [{"code": "META", "market": "US", "value_cny": "70000.00"}],
        }

        draft = portfolio_context_draft(snapshot, "META.US")

        self.assertIsNone(draft["current_weight"])
        self.assertEqual(draft["stock_pool_weight"], "1.0000")
        self.assertIn("现金数据已过期（日期 2026-07-25）", draft["constraints"])
        self.assertIn("负债数据已过期（日期 2025-02-16）", draft["constraints"])

    def test_draft_stays_unknown_when_no_active_holdings_are_verified(self):
        snapshot = self._snapshot([], allocation={"netAssets": 100000})
        self.assertFalse(snapshot["holdings_verified"])
        draft = portfolio_context_draft(snapshot, "META", rates_payload={"USD_CNY": 7.0})
        self.assertEqual(draft["position_status"], "unknown")

    def test_absence_requires_a_complete_authenticated_holdings_list(self):
        snapshot = self._snapshot([
            {"code": "META", "currency": "USD", "amount": 1, "currentPrice": 700,
             "priceUpdateTime": "2026-08-01T00:00:00Z"},
            {"code": "UNKNOWN", "currentPrice": 10},
        ], allocation={"netAssets": 100000})
        self.assertTrue(snapshot["holdings_verified"])
        self.assertFalse(snapshot["holdings_complete"])
        draft = portfolio_context_draft(snapshot, "PDD")
        self.assertEqual(draft["position_status"], "unknown")

    def test_research_token_header_is_used_without_bearer_auth(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return b'{"positions": []}'

        with mock.patch("ledger_portfolio_preflight.urlopen", return_value=Response()) as open_url:
            payload = fetch_research_json(
                "https://ledger.example.com", "/api/research/holdings", "test-secret", 5
            )

        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("X-ledger-research-token"), "test-secret")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(payload, {"positions": []})

    def test_research_snapshot_uses_the_dedicated_summary_endpoint(self):
        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        with mock.patch(
            "ledger_portfolio_preflight.urlopen",
            side_effect=[
                Response({
                    "retrieved_at": "2026-08-02T00:00:00Z",
                    "positions": [{"code": "META", "market": "US", "currency": "USD", "amount": 1,
                                   "currentPrice": 700, "priceUpdateTime": "2026-08-02T00:00:00Z"}],
                }),
                Response({"net_assets_cny": 100000, "freshness_status": "fresh"}),
            ],
        ) as open_url:
            snapshot = fetch_research_snapshot(
                "https://ledger.example.com", "test-secret", 5, 72
            )

        self.assertEqual(snapshot["portfolio_summary_status"], "available")
        self.assertEqual(snapshot["portfolio_summary_snapshot"]["net_assets_cny"], 100000)
        requests = [call.args[0] for call in open_url.call_args_list]
        self.assertEqual(len(requests), 2)
        self.assertIn("/api/research/holdings", requests[0].full_url)
        self.assertIn("/api/research/portfolio-summary", requests[1].full_url)
        self.assertTrue(all(request.get_header("X-ledger-research-token") == "test-secret" for request in requests))

    def test_transient_research_timeout_retries_once(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return b'{"positions": []}'

        with mock.patch(
            "ledger_portfolio_preflight.urlopen",
            side_effect=[URLError("timed out"), Response()],
        ) as open_url, mock.patch("ledger_portfolio_preflight.time.sleep"):
            payload = fetch_research_json(
                "https://ledger.example.com", "/api/research/holdings", "test-secret", 5
            )

        self.assertEqual(open_url.call_count, 2)
        self.assertEqual(payload, {"positions": []})

    def test_keychain_reader_uses_service_lookup_without_printing_secret(self):
        completed = mock.Mock(returncode=0, stdout="test-secret\n", stderr="")
        with mock.patch("ledger_portfolio_preflight.sys.platform", "darwin"), mock.patch(
            "ledger_portfolio_preflight.subprocess.run", return_value=completed
        ) as run:
            token = read_keychain_token("ledger-research-token")

        self.assertEqual(token, "test-secret")
        self.assertEqual(
            run.call_args.args[0],
            ["security", "find-generic-password", "-s", "ledger-research-token", "-w"],
        )
        self.assertTrue(run.call_args.kwargs["capture_output"])

    def test_draft_not_held_and_missing_rate(self):
        stocks = [{"code": "PDD", "currency": "USD", "amount": 1, "currentPrice": 100, "priceUpdateTime": "2026-08-01T00:00:00Z"}]
        snapshot = self._snapshot(stocks, allocation={"netAssets": 1000})
        self.assertEqual(portfolio_context_draft(snapshot, "META", rates_payload={})["position_status"], "not_held")
        held = portfolio_context_draft(snapshot, "PDD", rates_payload={})
        self.assertEqual(held["position_status"], "held")
        self.assertIsNone(held["current_weight"])


class StockPoolWeightTests(unittest.TestCase):
    NOW = datetime(2026, 10, 22, 6, 40, tzinfo=timezone.utc)
    POSITIONS = [
        {"code": "00700", "market": "HK", "currency": "HKD", "amount": 100},
        {"code": "META", "market": "US", "currency": "USD", "amount": 1},
        {"code": "600519", "market": "CN", "currency": "CNY", "amount": 1},
    ]

    def _run(self, *, yahoo_prices=None, sina_prices=None, yahoo_fx=None, open_er_fx=None, quote_times_override=None):
        quote_times = {
            "0700.HK": "2026-10-22T06:23:00+00:00",
            "META": "2026-10-21T20:00:00+00:00",
            "600519.SS": "2026-10-22T06:23:00+00:00",
        }
        quote_times.update(quote_times_override or {})
        yahoo_prices = yahoo_prices or {"0700.HK": 382, "META": 697.52, "600519.SS": 1313.16}
        sina_prices = sina_prices or {"00700": 381.4, "META": 697.52, "600519": 1315}
        yahoo_fx = yahoo_fx or {
            "USD_CNY": 6.6736,
            "HKD_CNY": 0.851281,
            "timestamp": self.NOW.isoformat(),
            "source": "Yahoo FX test",
        }
        open_er_fx = open_er_fx or {
            "USD_CNY": 6.689276,
            "HKD_CNY": 0.852506,
            "timestamp": "2026-10-22T00:02:31+00:00",
            "source": "open.er-api test",
        }

        def yahoo_fetch(symbol, _timeout):
            return {"price": yahoo_prices[symbol], "timestamp": quote_times[symbol], "source": "Yahoo test"}

        def sina_fetch(code, _market, _timeout):
            return {"price": sina_prices[code], "timestamp": quote_times[{
                "00700": "0700.HK", "META": "META", "600519": "600519.SS"
            }[code]], "currency": {"00700": "HKD", "META": "USD", "600519": "CNY"}[code], "source": "Sina test"}

        def tencent_fetch(_code, _market, _timeout):
            raise LedgerPreflightError("Tencent intentionally unavailable in this test")

        def nasdaq_fetch(_code, _market, _timeout):
            raise LedgerPreflightError("Nasdaq intentionally unavailable in this test")

        def currency_api_fetch(_timeout):
            raise LedgerPreflightError("currency-api intentionally unavailable in this test")

        return build_stock_pool_weight_snapshot(
            self.POSITIONS,
            ticker="0700.HK",
            now=self.NOW,
            yahoo_quote_fetcher=yahoo_fetch,
            nasdaq_quote_fetcher=nasdaq_fetch,
            tencent_quote_fetcher=tencent_fetch,
            sina_quote_fetcher=sina_fetch,
            reference_fx_fetcher=lambda _timeout: yahoo_fx,
            open_er_fx_fetcher=lambda _timeout: open_er_fx,
            currency_api_fx_fetcher=currency_api_fetch,
        )

    def test_computes_cross_checked_fx_normalized_stock_pool_weight(self):
        snapshot = self._run()

        self.assertEqual(snapshot["status"], "verified")
        self.assertEqual(snapshot["ticker"], "0700.HK")
        self.assertEqual(snapshot["as_of"], "2026-10-21T20:00:00+00:00")
        target_value = Decimal("100") * Decimal("382") * Decimal("0.851281")
        other_value = Decimal("697.52") * Decimal("6.6736") + Decimal("1313.16")
        expected = (target_value / (target_value + other_value)).quantize(Decimal("0.000001"))
        self.assertEqual(snapshot["weight"], str(expected))
        self.assertIn("Yahoo FX test", snapshot["fx_sources"])
        self.assertIn("open.er-api test", snapshot["fx_sources"])

    def test_quote_disagreement_fails_closed(self):
        snapshot = self._run(sina_prices={"00700": 370, "META": 697.52, "600519": 1315})

        self.assertEqual(snapshot["status"], "unavailable")
        self.assertIsNone(snapshot["weight"])
        self.assertTrue(any("differ by more than 1%" in warning for warning in snapshot["warnings"]))

    def test_stale_quote_or_fx_disagreement_fails_closed(self):
        stale = self._run(quote_times_override={"META": "2026-10-18T00:00:00+00:00"})
        fx_mismatch = self._run(open_er_fx={
            "USD_CNY": 7.0,
            "HKD_CNY": 0.9,
            "timestamp": "2026-10-22T00:02:31+00:00",
            "source": "open.er-api test",
        })

        self.assertEqual(stale["status"], "unavailable")
        self.assertIsNone(stale["weight"])
        self.assertTrue(any("stale quote from Yahoo Finance chart for META" in warning for warning in stale["warnings"]))
        self.assertEqual(fx_mismatch["status"], "unavailable")
        self.assertIsNone(fx_mismatch["weight"])
        self.assertTrue(any("FX sources differ by more than 1%" in warning for warning in fx_mismatch["warnings"]))

    def test_yahoo_outage_falls_back_to_fresh_tencent_and_sina_quotes(self):
        def fail_yahoo(_symbol, _timeout):
            raise LedgerPreflightError("Yahoo endpoint unavailable")

        def fail_nasdaq(_code, _market, _timeout):
            raise LedgerPreflightError("Nasdaq intentionally unavailable in this test")

        def fail_currency_api(_timeout):
            raise LedgerPreflightError("currency-api intentionally unavailable in this test")

        def tencent_fetch(code, _market, _timeout):
            prices = {"00700": 381.7, "META": 697.52, "600519": 1315}
            symbols = {"00700": "0700.HK", "META": "META", "600519": "600519.SS"}
            return {
                "price": prices[code],
                "timestamp": "2026-10-22T06:30:00+00:00" if code != "META" else "2026-10-21T20:00:00+00:00",
                "currency": {"00700": "HKD", "META": "USD", "600519": "CNY"}[code],
                "source": "Tencent test",
                "symbol": symbols[code],
            }

        snapshot = build_stock_pool_weight_snapshot(
            self.POSITIONS,
            ticker="0700.HK",
            now=self.NOW,
            yahoo_quote_fetcher=fail_yahoo,
            nasdaq_quote_fetcher=fail_nasdaq,
            tencent_quote_fetcher=tencent_fetch,
            sina_quote_fetcher=lambda code, _market, _timeout: {
                "price": {"00700": 381.8, "META": 697.52, "600519": 1315}[code],
                "timestamp": "2026-10-22T06:31:00+00:00" if code != "META" else "2026-10-21T20:00:00+00:00",
                "currency": {"00700": "HKD", "META": "USD", "600519": "CNY"}[code],
                "source": "Sina test",
            },
            reference_fx_fetcher=lambda _timeout: {
                "USD_CNY": 6.6736,
                "HKD_CNY": 0.851281,
                "timestamp": "2026-10-22T00:00:00+00:00",
                "source": "Reference FX test",
            },
            open_er_fx_fetcher=lambda _timeout: {
                "USD_CNY": 6.689276,
                "HKD_CNY": 0.852506,
                "timestamp": "2026-10-22T00:02:31+00:00",
                "source": "Independent FX test",
            },
            currency_api_fx_fetcher=fail_currency_api,
        )

        self.assertEqual(snapshot["status"], "verified")
        self.assertEqual(snapshot["positions"][0]["quote_sources"], ["Tencent test", "Sina test"])
        self.assertGreater(float(snapshot["weight"]), 0)

    def test_prefers_the_latest_agreeing_quote_pair_over_matching_prior_closes(self):
        now = datetime(2026, 10, 22, 13, 0, tzinfo=timezone.utc)

        def quote(price, timestamp, source):
            return {"price": price, "currency": "USD", "timestamp": timestamp, "source": source}

        snapshot = build_stock_pool_weight_snapshot(
            [{"code": "META", "market": "US", "currency": "USD", "amount": 10}],
            ticker="META",
            now=now,
            yahoo_quote_fetcher=lambda *_: quote(100, "2026-10-22T12:00:00Z", "Yahoo close"),
            nasdaq_quote_fetcher=lambda *_: quote(98, "2026-10-22T12:50:00Z", "Nasdaq current"),
            tencent_quote_fetcher=lambda *_: quote(100, "2026-10-22T12:05:00Z", "Tencent close"),
            sina_quote_fetcher=lambda *_: quote(98, "2026-10-22T12:51:00Z", "Sina current"),
            reference_fx_fetcher=lambda *_: {
                "USD_CNY": 6.68,
                "timestamp": "2026-10-22T12:00:00Z",
                "source": "Reference FX",
            },
            open_er_fx_fetcher=lambda *_: {
                "USD_CNY": 6.68,
                "timestamp": "2026-10-22T12:01:00Z",
                "source": "Independent FX",
            },
            currency_api_fx_fetcher=lambda *_: (_ for _ in ()).throw(LedgerPreflightError("unused")),
        )

        self.assertEqual(snapshot["status"], "verified")
        self.assertEqual(snapshot["positions"][0]["quote_sources"], ["Nasdaq current", "Sina current"])
        self.assertEqual(snapshot["positions"][0]["selected_price"], 98)
        self.assertEqual(snapshot["positions"][0]["quote_timestamp"], "2026-10-22T12:50:00+00:00")

    def test_fx_pair_falls_back_when_the_preferred_source_is_unavailable(self):
        def unavailable(_timeout):
            raise LedgerPreflightError("primary FX source unavailable")

        def open_er(_timeout):
            return {
                "USD_CNY": 6.689276,
                "HKD_CNY": 0.852506,
                "timestamp": "2026-10-22T00:02:31+00:00",
            }

        def currency_api(_timeout):
            return {
                "USD_CNY": 1 / 0.14986,
                "HKD_CNY": 1 / 1.177,
                "timestamp": "2026-10-22T00:00:00+00:00",
            }

        result = _crosscheck_fx_sources(
            {"USD", "HKD"},
            now=self.NOW,
            max_age_hours=72,
            timeout=1,
            fetchers=[
                ("Frankfurter", unavailable),
                ("open.er-api.com", open_er),
                ("currency-api", currency_api),
            ],
        )

        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["sources"], ["open.er-api.com", "currency-api"])
        self.assertGreater(result["rates"]["USD_CNY"], 6.6)

    def test_future_dated_quotes_fail_closed(self):
        future_timestamp = "2026-10-22T14:00:00+00:00"
        future = self._run(quote_times_override={
            "0700.HK": future_timestamp,
            "META": future_timestamp,
            "600519.SS": future_timestamp,
        })

        self.assertEqual(future["status"], "unavailable")
        self.assertTrue(any("future-dated quote from Yahoo Finance chart" in warning for warning in future["warnings"]))


class PublicQuoteParserTests(unittest.TestCase):
    class Response:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return self.body.encode("gb18030")

    def test_sina_quote_parsers_use_market_price_and_timestamp_fields(self):
        hk = 'var hq_str_hk00700="TENCENT,腾讯控股,387.000,393.800,391.200,378.400,381.800,-12.000,-3.047,381.60001,381.79999,18290542349,47806497,0.000,0.000,656.353,378.400,2026/10/22,14:29";'
        cn = 'var hq_str_sh600519="贵州茅台,1303.210,1309.690,1319.090,1322.000,1296.000,1319.020,1319.800,3693533,4842953158.000,2026-10-22,14:51:36,00,";'
        us_fields = ["0"] * 36
        us_fields[0] = "苹果"
        us_fields[1] = "343.9900"
        us_fields[21] = "344.5000"
        us_fields[24] = "Oct 22 08:51AM EDT"
        us_fields[25] = "Oct 21 04:00PM EDT"
        us_fields[29] = "2026"
        us = 'var hq_str_gb_aapl="' + ",".join(us_fields) + '";'
        with mock.patch("ledger_portfolio_preflight.urlopen", side_effect=[
            self.Response(hk), self.Response(cn), self.Response(us)
        ]):
            hk_quote = fetch_sina_quote("00700", "HK")
            cn_quote = fetch_sina_quote("600519", "CN")
            us_quote = fetch_sina_quote("AAPL", "US")

        self.assertEqual(hk_quote["price"], 381.8)
        self.assertEqual(hk_quote["timestamp"], "2026-10-22T06:29:00+00:00")
        self.assertEqual(cn_quote["price"], 1319.09)
        self.assertEqual(cn_quote["timestamp"], "2026-10-22T06:51:36+00:00")
        self.assertEqual(us_quote["price"], 344.5)
        self.assertEqual(us_quote["timestamp"], "2026-10-22T12:51:00+00:00")

    def test_sina_us_quote_falls_back_to_explicit_last_close_not_server_clock(self):
        fields = ["0"] * 36
        fields[0] = "Apple"
        fields[1] = "343.9900"
        fields[21] = "0"
        fields[25] = "Oct 21 04:00PM EDT"
        fields[29] = "2026"
        body = 'var hq_str_gb_aapl="' + ",".join(fields) + '";'
        with mock.patch("ledger_portfolio_preflight.urlopen", return_value=self.Response(body)):
            quote = fetch_sina_quote("AAPL", "US")

        self.assertEqual(quote["price"], 343.99)
        self.assertEqual(quote["timestamp"], "2026-10-21T20:00:00+00:00")

    def test_public_json_retries_one_transient_disconnect_then_fails_closed(self):
        with mock.patch(
            "ledger_portfolio_preflight.urlopen",
            side_effect=[RemoteDisconnected("closed"), self.Response('{"ok":true}')],
        ) as open_url:
            payload = _public_json("https://rates.example.test/latest", 1.0)
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(open_url.call_count, 2)

        with mock.patch(
            "ledger_portfolio_preflight.urlopen",
            side_effect=[RemoteDisconnected("closed"), RemoteDisconnected("closed")],
        ):
            with self.assertRaisesRegex(LedgerPreflightError, "public market-data request failed"):
                _public_json("https://rates.example.test/latest", 1.0)

    def test_tencent_quote_parser_reads_timestamped_hong_kong_quote(self):
        fields = ["0"] * 36
        fields[3] = "380.4"
        fields[30] = "2026/10/22 14:51:28"
        body = 'v_r_hk00700="' + "~".join(fields) + '";'
        with mock.patch("ledger_portfolio_preflight.urlopen", return_value=self.Response(body)):
            quote = fetch_tencent_quote("00700", "HK")

        self.assertEqual(quote["price"], 380.4)
        self.assertEqual(quote["currency"], "HKD")
        self.assertEqual(quote["timestamp"], "2026-10-22T06:51:28+00:00")

    def test_nasdaq_quote_parser_uses_last_sale_and_trading_date(self):
        body = json.dumps({
            "data": {
                "primaryData": {
                    "lastSalePrice": "$78.72",
                    "lastTradeTimestamp": "Oct 22, 2026 8:51 AM ET",
                }
            }
        })
        with mock.patch("ledger_portfolio_preflight.urlopen", return_value=self.Response(body)):
            quote = fetch_nasdaq_quote("PDD", "US")

        self.assertEqual(quote["price"], 78.72)
        self.assertEqual(quote["currency"], "USD")
        self.assertEqual(quote["timestamp"], "2026-10-22T12:51:00+00:00")

    def test_nasdaq_quote_parser_keeps_date_only_timestamp_compatible(self):
        body = json.dumps({
            "data": {
                "primaryData": {
                    "lastSalePrice": "$78.72",
                    "lastTradeTimestamp": "Oct 21, 2026",
                }
            }
        })
        with mock.patch("ledger_portfolio_preflight.urlopen", return_value=self.Response(body)):
            quote = fetch_nasdaq_quote("PDD", "US")

        self.assertEqual(quote["timestamp"], "2026-10-21")

    def test_nasdaq_quote_retries_one_transient_network_failure(self):
        body = json.dumps({
            "data": {
                "primaryData": {
                    "lastSalePrice": "$77.07",
                    "lastTradeTimestamp": "Oct 22, 2026 8:51 AM ET",
                }
            }
        })
        with mock.patch(
            "ledger_portfolio_preflight.urlopen",
            side_effect=[URLError("temporary reset"), self.Response(body)],
        ) as open_url, mock.patch("ledger_portfolio_preflight.time.sleep"):
            quote = fetch_nasdaq_quote("PDD", "US")

        self.assertEqual(open_url.call_count, 2)
        self.assertEqual(quote["price"], 77.07)
        self.assertEqual(quote["timestamp"], "2026-10-22T12:51:00+00:00")

    def test_frankfurter_rates_are_inverted_to_foreign_currency_per_cny(self):
        payload = [
            {"date": "2026-10-21", "base": "CNY", "quote": "USD", "rate": 0.14979},
            {"date": "2026-10-21", "base": "CNY", "quote": "HKD", "rate": 1.1754},
        ]
        with mock.patch("ledger_portfolio_preflight._public_json", return_value=payload):
            rates = fetch_frankfurter_fx_rates()

        self.assertAlmostEqual(rates["USD_CNY"], 1 / 0.14979)
        self.assertAlmostEqual(rates["HKD_CNY"], 1 / 1.1754)
        self.assertEqual(rates["timestamp"], "2026-10-21T00:00:00+00:00")

    def test_currency_api_rates_are_inverted_to_foreign_currency_per_cny(self):
        payload = {"date": "2026-10-22", "cny": {"usd": 0.14986, "hkd": 1.177}}
        with mock.patch("ledger_portfolio_preflight._public_json", return_value=payload):
            rates = fetch_currency_api_fx_rates()

        self.assertAlmostEqual(rates["USD_CNY"], 1 / 0.14986)
        self.assertAlmostEqual(rates["HKD_CNY"], 1 / 1.177)
        self.assertEqual(rates["timestamp"], "2026-10-22T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()

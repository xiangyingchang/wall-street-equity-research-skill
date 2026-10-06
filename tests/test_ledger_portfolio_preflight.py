import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ledger_portfolio_preflight import (  # noqa: E402
    LedgerPreflightError,
    _validate_base_url,
    build_snapshot,
    extract_active_positions,
    portfolio_context_draft,
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

    def test_incomplete_active_position_is_not_silently_used(self):
        positions, warnings, _ = extract_active_positions([
            {"code": "MU", "amount": 2, "currentPrice": 0},
        ])

        self.assertEqual(positions, [])
        self.assertIn("incomplete active position: MU", warnings)

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

    def test_draft_is_unknown_when_snapshot_untrusted(self):
        stocks = [{"code": "META", "currency": "USD", "amount": 10, "currentPrice": 700}]
        snapshot = self._snapshot(stocks, allocation={"netAssets": 100000})
        self.assertFalse(snapshot["trusted"])
        draft = portfolio_context_draft(snapshot, "META", rates_payload={"USD_CNY": 7.0})
        self.assertEqual(draft["position_status"], "unknown")

    def test_draft_not_held_and_missing_rate(self):
        stocks = [{"code": "PDD", "currency": "USD", "amount": 1, "currentPrice": 100, "priceUpdateTime": "2026-08-01T00:00:00Z"}]
        snapshot = self._snapshot(stocks, allocation={"netAssets": 1000})
        self.assertEqual(portfolio_context_draft(snapshot, "META", rates_payload={})["position_status"], "not_held")
        held = portfolio_context_draft(snapshot, "PDD", rates_payload={})
        self.assertEqual(held["position_status"], "held")
        self.assertIsNone(held["current_weight"])


if __name__ == "__main__":
    unittest.main()

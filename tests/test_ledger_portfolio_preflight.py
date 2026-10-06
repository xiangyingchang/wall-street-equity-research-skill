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


if __name__ == "__main__":
    unittest.main()

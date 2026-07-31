from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


GOOD = """
# TEST Test — 华尔街式分析报告

## Evidence Ledger

| 数据项 | 数值 | 日期 | 来源/层级 | 口径 | 可信度 |
|---|---:|---|---|---|---|
| 当前价格 | $100 | 2026-07-31 | Tier 1 | close | 高 |
| TTM EPS | $5 | 2026-07-31 | Tier 1 | TTM | 高 |
| TTM PE | 20x | 2026-07-31 | calc | price/EPS | 高 |
| TTM FCF/share | $4 | 2026-07-31 | calc | TTM | 高 |
| FCF yield | 4% | 2026-07-31 | calc | FCF/share/price | 高 |

## 2. 财务剖析 Financial Autopsy

### One-off Adjustment Ledger

| Adjustment ID | Period | Item | Pre-tax/after-tax | Cash/non-cash | Repeatability | Per-share impact | Treatment | Source |
|---|---|---|---|---|---|---:|---|---|
| ADJ-1 | FY2026-Q2 | legal | pre-tax | cash | medium | $0.20 | exclude 50% | filing |

## 4. 极限估值 + 10 年回本数学审判

### Valuation Basis Registry

| Basis ID | Metric | Value | Period | Adjustments | Use |
|---|---|---:|---|---|---|
| EPS-BEAR | EPS/share | $4 | FY+1 | None | Bear |
| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-1 | Base |
| EPS-BULL | EPS/share | $6 | FY+1 | ADJ-1 | Bull |

### Scenario Valuation

| Scenario | Basis ID | Metric value | Multiple | Fair value | Safety margin | Buy price | Key assumptions |
|---|---|---:|---:|---:|---:|---:|---|
| Bear | EPS-BEAR | $4 | 15x | $60 | 20% | $48 | weak growth |
| Base | EPS-BASE | $5 | 20x | $100 | 15% | $85 | normal growth |
| Bull | EPS-BULL | $6 | 25x | $150 | 10% | $135 | strong growth |

### Capex / Owner Earnings Bridge

| Item | Value/range | Period | Evidence | Confidence |
|---|---:|---|---|---|
| Reported OCF | $100亿 | FY2026 | filing | High |
| Reported Capex | $50亿 | FY2026 | filing | High |
| Reported FCF | $50亿 | FY2026 | calc | High |
| Maintenance Capex | Unclear | FY2026 | no disclosure | Low |
| Growth Capex | Unclear | FY2026 | no disclosure | Low |
| Strategic / AI Capex | Unclear | FY2026 | no disclosure | Low |
| Owner Earnings / Normalized FCF | Unclear | FY2026 | no disclosure | Low |
"""


class ValuationConsistencyCliTests(unittest.TestCase):
    def run_check(self, text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "scripts/valuation_consistency.py", str(path)],
                check=False,
                text=True,
                capture_output=True,
            )

    def test_good_report_passes(self) -> None:
        result = self.run_check(GOOD)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bad_scenario_math_fails(self) -> None:
        result = self.run_check(GOOD.replace("| Base | EPS-BASE | $5 | 20x | $100 |", "| Base | EPS-BASE | $5 | 20x | $120 |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fair value", result.stdout)

    def test_unknown_basis_fails(self) -> None:
        result = self.run_check(GOOD.replace("| Bear | EPS-BEAR |", "| Bear | EPS-MISSING |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown Basis ID", result.stdout)

    def test_fcf_yield_reconciliation_fails(self) -> None:
        result = self.run_check(GOOD.replace("| FCF yield | 4% |", "| FCF yield | 2% |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FCF yield", result.stdout)

    def test_adjustment_reference_fails(self) -> None:
        result = self.run_check(GOOD.replace("| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-1 |", "| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-X |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown Adjustment ID", result.stdout)

    def test_scenario_metric_must_match_registered_basis(self) -> None:
        result = self.run_check(GOOD.replace("| Base | EPS-BASE | $5 | 20x | $100 |", "| Base | EPS-BASE | $50 | 2x | $100 |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match registered Basis", result.stdout)

    def test_bear_base_bull_ordering_fails(self) -> None:
        result = self.run_check(GOOD.replace("| Bear | EPS-BEAR | $4 | 15x | $60 | 20% | $48 |", "| Bear | EPS-BEAR | $4 | 30x | $120 | 20% | $96 |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Bear fair value exceeds Base", result.stdout)

    def test_buy_price_above_fair_value_fails(self) -> None:
        result = self.run_check(GOOD.replace("| Base | EPS-BASE | $5 | 20x | $100 | 15% | $85 |", "| Base | EPS-BASE | $5 | 20x | $100 | -10% | $110 |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("buy price exceeds fair value", result.stdout)

    def test_sub_one_percent_fcf_yield_reconciles(self) -> None:
        report = GOOD.replace("| 当前价格 | $100 |", "| 当前价格 | $1000 |").replace("| TTM PE | 20x |", "| TTM PE | 200x |").replace("| FCF yield | 4% |", "| FCF yield | 0.4% |")
        result = self.run_check(report)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_normalized_basis_requires_adjustment_bridge(self) -> None:
        result = self.run_check(GOOD.replace("| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-1 | Base |", "| EPS-BASE | normalized EPS/share | $5 | FY+1 | None | Base |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has no Adjustment ID bridge", result.stdout)


if __name__ == "__main__":
    unittest.main()

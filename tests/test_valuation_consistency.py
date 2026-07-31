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

### Canonical Fact Registry

| Fact ID | Metric | Value | Period/as-of | Source/Tier | Basis/Unit | Confidence |
|---|---|---:|---|---|---|---|
| FACT-PRICE | Current price | $100 | 2026-07-31 | Exchange / Tier 1 | USD/share | High |
| FACT-TTM-EPS | TTM EPS | $5 | TTM 2026-Q2 | Filing / Tier 1 | USD/share | High |
| FACT-TTM-FCF | TTM FCF/share | $4 | TTM 2026-Q2 | Filing / Tier 1 | USD/share | High |

## 2. 财务剖析 Financial Autopsy

### One-off Adjustment Ledger

| Adjustment ID | Period | Item | Pre-tax/after-tax | Cash/non-cash | Repeatability | Per-share impact | Treatment | Source |
|---|---|---|---|---|---|---:|---|---|
| ADJ-1 | FY2026-Q2 | legal | pre-tax | cash | medium | $0.20 | exclude 50% | filing |

## 4. 极限估值 + 10 年回本数学审判

### Scenario Assumption Registry

| Assumption ID | Scenario | Variable | Value | Period | Evidence/rationale | Confidence |
|---|---|---|---:|---|---|---|
| ASM-BEAR-MARGIN | Bear | Operating margin | 20% | Forward 12M | downside | Medium |
| ASM-BASE-MARGIN | Base | Operating margin | 25% | Forward 12M | base | Medium |
| ASM-BULL-MARGIN | Bull | Operating margin | 30% | Forward 12M | upside | Medium |

### Forward Revenue Bridge

| Revenue Bridge ID | Scenario | Period | Revenue | Growth/guide basis | Source/assumption ID |
|---|---|---|---:|---|---|
| REV-BEAR-Q1 | Bear | FY+1 Q1 | $25亿 | flat | ASM-BEAR-MARGIN |
| REV-BEAR-Q2 | Bear | FY+1 Q2 | $25亿 | flat | ASM-BEAR-MARGIN |
| REV-BEAR-Q3 | Bear | FY+1 Q3 | $25亿 | flat | ASM-BEAR-MARGIN |
| REV-BEAR-Q4 | Bear | FY+1 Q4 | $25亿 | flat | ASM-BEAR-MARGIN |
| REV-BASE-Q1 | Base | FY+1 Q1 | $25亿 | flat | ASM-BASE-MARGIN |
| REV-BASE-Q2 | Base | FY+1 Q2 | $25亿 | flat | ASM-BASE-MARGIN |
| REV-BASE-Q3 | Base | FY+1 Q3 | $25亿 | flat | ASM-BASE-MARGIN |
| REV-BASE-Q4 | Base | FY+1 Q4 | $25亿 | flat | ASM-BASE-MARGIN |
| REV-BULL-Q1 | Bull | FY+1 Q1 | $25亿 | flat | ASM-BULL-MARGIN |
| REV-BULL-Q2 | Bull | FY+1 Q2 | $25亿 | flat | ASM-BULL-MARGIN |
| REV-BULL-Q3 | Bull | FY+1 Q3 | $25亿 | flat | ASM-BULL-MARGIN |
| REV-BULL-Q4 | Bull | FY+1 Q4 | $25亿 | flat | ASM-BULL-MARGIN |

### Scenario EPS Bridge

| Bridge ID | Scenario | Revenue | Operating margin | Operating income | Other income/expense | Pre-tax income | Tax rate | Net income | Diluted shares | EPS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BR-BEAR | Bear | $100亿 | 20% | $20亿 | $0 | $20亿 | 20% | $16亿 | 4亿 | $4 |
| BR-BASE | Base | $100亿 | 25% | $25亿 | $0 | $25亿 | 20% | $20亿 | 4亿 | $5 |
| BR-BULL | Bull | $100亿 | 30% | $30亿 | $0 | $30亿 | 20% | $24亿 | 4亿 | $6 |

### Valuation Basis Registry

| Basis ID | Metric | Value | Period | Adjustments | Bridge ID | Use |
|---|---|---:|---|---|---|---|
| EPS-BEAR | EPS/share | $4 | FY+1 | None | BR-BEAR | Bear |
| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-1 | BR-BASE | Base |
| EPS-BULL | EPS/share | $6 | FY+1 | ADJ-1 | BR-BULL | Bull |

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

## 8. 仓位与风控

### Current Action Evaluation — Runtime Output

| Rule ID | Action | Logic | Runtime condition results | Triggered |
|---|---|---|---|---|
| hold | HOLD | all | FACT-TTM-EPS > 0 => true | true |

`python3 scripts/valuation_runtime.py evaluate-action --input action-evaluation.json`
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
        result = self.run_check(
            GOOD.replace("| Base | EPS-BASE | $5 | 20x | $100 |", "| Base | EPS-BASE | $5 | 20x | $120 |")
        )
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
        result = self.run_check(
            GOOD.replace(
                "| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-1 | BR-BASE |",
                "| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-X | BR-BASE |",
            )
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown Adjustment ID", result.stdout)

    def test_scenario_metric_must_match_registered_basis(self) -> None:
        result = self.run_check(
            GOOD.replace("| Base | EPS-BASE | $5 | 20x | $100 |", "| Base | EPS-BASE | $50 | 2x | $100 |")
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match registered Basis", result.stdout)

    def test_bear_base_bull_ordering_fails(self) -> None:
        result = self.run_check(
            GOOD.replace(
                "| Bear | EPS-BEAR | $4 | 15x | $60 | 20% | $48 |",
                "| Bear | EPS-BEAR | $4 | 30x | $120 | 20% | $96 |",
            )
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Bear fair value exceeds Base", result.stdout)

    def test_buy_price_above_fair_value_fails(self) -> None:
        result = self.run_check(
            GOOD.replace(
                "| Base | EPS-BASE | $5 | 20x | $100 | 15% | $85 |",
                "| Base | EPS-BASE | $5 | 20x | $100 | -10% | $110 |",
            )
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("buy price exceeds fair value", result.stdout)

    def test_sub_one_percent_fcf_yield_reconciles(self) -> None:
        report = (
            GOOD.replace("| 当前价格 | $100 |", "| 当前价格 | $1000 |")
            .replace("| TTM PE | 20x |", "| TTM PE | 200x |")
            .replace("| FCF yield | 4% |", "| FCF yield | 0.4% |")
        )
        result = self.run_check(report)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_normalized_basis_requires_adjustment_or_bridge(self) -> None:
        result = self.run_check(
            GOOD.replace(
                "| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-1 | BR-BASE | Base |",
                "| EPS-BASE | normalized EPS/share | $5 | FY+1 | None | N/A | Base |",
            )
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has no adjustment or scenario bridge", result.stdout)

    def test_eps_bridge_math_fails(self) -> None:
        result = self.run_check(
            GOOD.replace(
                "| BR-BASE | Base | $100亿 | 25% | $25亿 | $0 | $25亿 | 20% | $20亿 | 4亿 | $5 |",
                "| BR-BASE | Base | $100亿 | 25% | $25亿 | $0 | $25亿 | 20% | $20亿 | 4亿 | $2 |",
            )
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("EPS does not reconcile", result.stdout)

    def test_basis_must_match_bridge_eps(self) -> None:
        result = self.run_check(
            GOOD.replace(
                "| EPS-BASE | EPS/share | $5 | FY+1 | ADJ-1 | BR-BASE | Base |",
                "| EPS-BASE | EPS/share | $22 | FY+1 | ADJ-1 | BR-BASE | Base |",
            ).replace("| Base | EPS-BASE | $5 |", "| Base | EPS-BASE | $22 |")
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match Scenario EPS Bridge", result.stdout)

    def test_duplicate_fact_id_fails(self) -> None:
        duplicated = GOOD.replace(
            "| FACT-TTM-FCF | TTM FCF/share | $4 |",
            "| FACT-PRICE | TTM FCF/share | $4 |",
        )
        result = self.run_check(duplicated)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate Fact ID", result.stdout)

    def test_manual_triggered_table_fails(self) -> None:
        result = self.run_check(
            GOOD.replace(
                "| Rule ID | Action | Logic | Runtime condition results | Triggered |",
                "| Rule ID | Action | Current facts used | Triggered |",
            ).replace("| hold | HOLD | all | FACT-TTM-EPS > 0 => true | true |", "| hold | HOLD | analyst judgment | true |")
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("legacy manual Triggered", result.stdout)

    def test_legacy_resolve_action_command_fails(self) -> None:
        result = self.run_check(
            GOOD.replace("valuation_runtime.py evaluate-action", "valuation_runtime.py resolve-action")
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("legacy resolve-action", result.stdout)

    def test_forward_assumption_in_adjustment_ledger_fails(self) -> None:
        result = self.run_check(GOOD.replace("| legal |", "| Forward capex normalization assumption |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Scenario Assumption Registry", result.stdout)

    def test_undefined_four_point_five_quarter_run_rate_fails(self) -> None:
        result = self.run_check(GOOD + "\nBase revenue = Q2 revenue × 4.5 quarters.\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("quarter ×4.5", result.stdout)

    def test_revenue_bridge_must_reconcile_to_eps_bridge(self) -> None:
        result = self.run_check(GOOD.replace("| REV-BASE-Q4 | Base | FY+1 Q4 | $25亿 |", "| REV-BASE-Q4 | Base | FY+1 Q4 | $20亿 |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("summed Forward Revenue Bridge", result.stdout)

    def test_treasury_times_two_is_not_low_risk_asset(self) -> None:
        report = GOOD + """

| Asset | Expected return | Risk |
|---|---:|---|
| US 10Y Treasury ×2 | 9.4% | 极低 |
"""
        result = self.run_check(report)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required-return hurdle", result.stdout)


if __name__ == "__main__":
    unittest.main()

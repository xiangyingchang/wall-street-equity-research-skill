from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


GOOD = r"""
# TEST — 华尔街式分析报告

> 税务身份=中国大陆个人；股票最低目标回报=10Y Treasury ×2。

## First-Page Verdict

| 项目 | 结论 |
|---|---|
| 当前动作 | REVIEW |
| 当前价格是否值得重新买入 | 否 |

## Evidence Ledger

| 数据项 | 数值 | 日期 | 来源/层级 | 口径 | 可信度 |
|---|---:|---|---|---|---|
| 当前价格 | $549 | 2026-08-01 | Tier 2 | regular session | 中 |
| 总股本 | 25.4亿 | 2026-06-30 | Tier 1 | point-in-time shares outstanding | 高 |
| 市值 | $13,944.6亿 | 2026-08-01 | calc | price × point-in-time shares | 中 |
| TTM EPS | $26.55 | 2026-06-30 | calc | ttm-derive | 高 |
| TTM FCF/share | $14.76 | 2026-06-30 | calc | TTM | 中 |
| 10Y Treasury | 4.70% | 2026-08-01 | Tier 1 | yield | 高 |
| 10Y Treasury ×2 | 9.40% | 2026-08-01 | calc | hurdle | 高 |
| 估算组合权重 | 5.2% | 2026-08-01 | Internal | snapshot | 中 |

### Canonical Value Registry

| Value ID | Kind | Metric | Value | Period/as-of | Source/Tier | Basis/Unit | Confidence | Inputs/Formula |
|---|---|---|---:|---|---|---|---|---|
| FACT-Q3-EPS | FACT | Q3 EPS | 1.05 | Q3 2025 | Tier 1 | $/share | high | source |
| DERIVED-TTM-EPS | DERIVED | TTM EPS | 26.55 | Q3'25-Q2'26 | calc | $/share | high | ttm-derive: FACT-Q3-EPS + FACT-Q4-EPS + FACT-Q1-EPS + FACT-Q2-EPS |
| DERIVED-TTM-FCF | DERIVED | TTM FCF | 378.7 | Q3'25-Q2'26 | calc | $亿 | medium | ttm-derive |
| MODEL-BASE-VALUE | MODEL | Base fair value | 630 | Scenario | runtime | $/share | medium | EPS × multiple |

### TTM Derivation - Runtime Output

| Derivation ID | Metric | Mode | Component IDs | Component totals | Value | Runtime ref |
|---|---|---|---|---|---:|---|
| DERIV-TTM-EPS | TTM EPS | sum | FACT-Q3-EPS, FACT-Q4-EPS, FACT-Q1-EPS, FACT-Q2-EPS | 1.05+8.88+10.44+6.18 | 26.55 | `valuation_runtime.py ttm-derive --input ttm-eps.json` |
| DERIV-TTM-MARGIN | TTM operating margin | ratio | FACT-Q3-OI, FACT-Q4-OI, FACT-Q1-OI, FACT-Q2-OI / FACT-Q3-REV, FACT-Q4-REV, FACT-Q1-REV, FACT-Q2-REV | 869.27/2282.47 | 38.08% | `valuation_runtime.py ttm-derive --input ttm-margin.json` |

## 4. 估值

### Scenario Assumption Registry

| Assumption ID | Scenario | Variable | Value | Period | Evidence/rationale | Confidence |
|---|---|---|---:|---|---|---|
| ASM-BASE-REV | Base | Revenue growth | 12% | Forward | assumption | 中 |
| ASM-BULL-REV | Bull | Revenue growth | 15% | Forward | assumption | 低 |

### Revenue Forecast - Runtime Output

| Revenue Bridge ID | Scenario | Period | Mode | Base Value | Growth | Guide Low | Guide High | Revenue | Source/Assumption ID | Runtime ref |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| REV-BASE-Q3 | Base | Q3 2026 | guide_midpoint | N/A | N/A | 610 | 640 | 625 | Meta IR | `valuation_runtime.py revenue-bridge --input base.json` |
| REV-BASE-Q4 | Base | Q4 2026 | qoq | 625 | 9% | N/A | N/A | 681.25 | ASM-BASE-Q4 | `valuation_runtime.py revenue-bridge --input base.json` |
| REV-BASE-Q1 | Base | Q1 2027 | yoy | 563.11 | 12% | N/A | N/A | 630.6832 | ASM-BASE-REV | `valuation_runtime.py revenue-bridge --input base.json` |
| REV-BASE-Q2 | Base | Q2 2027 | yoy | 608.01 | 12% | N/A | N/A | 680.9712 | ASM-BASE-REV | `valuation_runtime.py revenue-bridge --input base.json` |
| REV-BULL-Q3 | Bull | Q3 2026 | guide_midpoint | N/A | N/A | 620 | 660 | 640 | Meta IR | `valuation_runtime.py revenue-bridge --input bull.json` |
| REV-BULL-Q4 | Bull | Q4 2026 | qoq | 640 | 12% | N/A | N/A | 716.8 | ASM-BULL-REV | `valuation_runtime.py revenue-bridge --input bull.json` |
| REV-BULL-Q1 | Bull | Q1 2027 | yoy | 563.11 | 15% | N/A | N/A | 647.5765 | ASM-BULL-REV | `valuation_runtime.py revenue-bridge --input bull.json` |
| REV-BULL-Q2 | Bull | Q2 2027 | yoy | 608.01 | 15% | N/A | N/A | 699.2115 | ASM-BULL-REV | `valuation_runtime.py revenue-bridge --input bull.json` |

### Return Pair - Runtime Output

| Scenario | Starting Basis ID | Starting EPS | EPS CAGR | Exit PE | Dividend assumption | Target return | 5-year IRR | Required terminal EPS | Required EPS CAGR | Target-return price | Runtime ref |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| Base | B-BASE | 30.71 | 6% | 18x | yield 0.5% | 9.4% | 6.54% | 47.03 | 8.90% | 479.71 | `valuation_runtime.py return-pair --current-price 549 ...` |

## 8. 仓位

### Threshold Policy Registry

| Threshold ID | Metric | Value | Basis | Lookback | Confirmation | Tolerance | Minimum confidence | Rationale |
|---|---|---:|---|---|---:|---:|---|---|
| THR-FCF-REDUCE | TTM FCF | 360 | historical distribution | 12 quarters | 2 | 5% | medium | sustained FCF deterioration |

### Action Matrix

| Action | Trigger type | Executable condition | Position/execution |
|---|---|---|---|
| Buy | valuation | N/A - current action is not Buy | No action |
| Add | price | MODEL-TARGET-PRICE > FACT-CURRENT-PRICE via THR-ADD | Review |
| Hold | operating | DERIVED-TTM-FCF >= THR-FCF-HOLD | Hold |
| Reduce | operating | DERIVED-TTM-FCF < THR-FCF-REDUCE | Reduce |
| Sell | thesis-break | DERIVED-CONSECUTIVE-BREACH >= THR-SELL | Sell |

### Current Action Evaluation - Runtime Output

| Runtime field | Result |
|---|---|
| Mode | v2-threshold-policy |
| Resolved action | REVIEW |
| Robustness stable | true |
| Runtime command | `python3 scripts/valuation_runtime.py evaluate-action --input action.json` |
| Robustness command | `python3 scripts/valuation_runtime.py robustness --input action.json --shock 0.05` |

### 价格区间摘要

| 价格区间 | 估值语境 | 推导来源 |
|---|---|---|
| $480 以下 | 目标回报买入区 | Return Pair |
| $480-630 | 观察区 | Return Pair + Forward reference |
| $630 以上 | 高估区 | Scenario |

## 9. Final

### Verification

| Check | Result |
|---|---|
| TTM derivation runtime | PASS |
| Revenue bridge runtime | PASS |
| EPS bridge runtime | PASS |
| Return pair runtime | PASS |
| Fact-based action evaluation | PASS |
| Action robustness | PASS |
| Valuation consistency | PASS |
| Input/decision consistency | PASS |
| Lint | PASS |
| Audit verdict | PASS |

`valuation_runtime.py return-pair`
`valuation_runtime.py robustness`
"""


class InputDecisionConsistencyTests(unittest.TestCase):
    def run_check(self, text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_text(text, encoding="utf-8")
            return subprocess.run([sys.executable, "scripts/input_decision_consistency.py", str(path)], text=True, capture_output=True, check=False)

    def test_good_report_passes(self):
        result = self.run_check(GOOD)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_model_output_cannot_be_fact(self):
        bad = GOOD.replace("| MODEL-BASE-VALUE | MODEL | Base fair value |", "| FACT-BASE-VALUE | FACT | Base fair value |")
        result = self.run_check(bad)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("model output", result.stdout)

    def test_yoy_revenue_must_reconcile(self):
        bad = GOOD.replace("| REV-BASE-Q1 | Base | Q1 2027 | yoy | 563.11 | 12% | N/A | N/A | 630.6832 |", "| REV-BASE-Q1 | Base | Q1 2027 | yoy | 563.11 | 12% | N/A | N/A | 700 |")
        result = self.run_check(bad)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("base × (1 + growth)", result.stdout)

    def test_naked_action_threshold_fails(self):
        result = self.run_check(GOOD.replace("DERIVED-TTM-FCF < THR-FCF-REDUCE", "DERIVED-TTM-FCF < 400"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("naked numeric threshold", result.stdout)

    def test_buy_zone_reduce_conflict_fails(self):
        bad = GOOD.replace("| 当前动作 | REVIEW |", "| 当前动作 | REDUCE |").replace("| $480 以下 | 目标回报买入区 |", "| $480-630 | 目标回报买入区 |")
        result = self.run_check(bad)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inside a buy zone", result.stdout)

    def test_verification_todo_fails(self):
        result = self.run_check(GOOD.replace("| Lint | PASS |", "| Lint | TODO |"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete", result.stdout)

    def test_weighted_average_market_cap_fails(self):
        bad = GOOD.replace("point-in-time shares outstanding", "diluted weighted-average shares").replace("price × point-in-time shares", "price × shares")
        result = self.run_check(bad)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("weighted-average", result.stdout)

    def test_separate_irr_reverse_commands_fail(self):
        result = self.run_check(GOOD + "\n`valuation_runtime.py irr --current-price 549`\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("separate irr/reverse", result.stdout)


if __name__ == "__main__":
    unittest.main()

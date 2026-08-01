from pathlib import Path
import json
import tempfile
import unittest

from scripts.report_integrity_v151 import build_artifact, scenario_value, validate_text


def valid_report() -> str:
    return r'''
# TEST

### Generation Manifest

| Field | Value |
|---|---|
| Skill version | 1.5.1 |
| Template schema | full-report-v1.5.1 |
| Git commit | abcdef123456 |
| Report ID | TEST-1 |
| Runtime artifacts directory | artifacts |

### Canonical Value Registry

| Value ID | Kind | Metric | Value | Period/as-of | Source/Tier | Basis/Unit | Confidence | Inputs/Formula |
|---|---|---|---:|---|---|---|---|---|
| FACT-PRICE | FACT | Current price | 100 | 2026-08-01 | Tier 2 | $/share | Medium | source |
| FACT-Q2-25-REV | FACT | Q2 2025 revenue | 100 | Q2 2025 | Tier 1 | $m | High | source |
| FACT-Q3-25-REV | FACT | Q3 2025 revenue | 110 | Q3 2025 | Tier 1 | $m | High | source |
| FACT-Q4-25-REV | FACT | Q4 2025 revenue | 120 | Q4 2025 | Tier 1 | $m | High | source |
| FACT-Q1-26-REV | FACT | Q1 2026 revenue | 130 | Q1 2026 | Tier 1 | $m | High | source |
| FACT-Q2-26-REV | FACT | Q2 2026 revenue | 140 | Q2 2026 | Tier 1 | $m | High | source |
| FACT-Q3-26-REV | FACT | Q3 2026 revenue | 150 | Q3 2026 | Tier 1 | $m | High | source |
| FACT-Q4-26-REV | FACT | Q4 2026 revenue | 160 | Q4 2026 | Tier 1 | $m | High | source |
| FACT-Q1-27-REV | FACT | Q1 2027 revenue | 170 | Q1 2027 | Tier 1 | $m | High | source |
| DERIVED-TTM-EPS | DERIVED | TTM EPS | 10 | Q3'25-Q2'26 | calculated | $/share | Medium | FACT-Q3-25-REV + FACT-Q4-25-REV + FACT-Q1-26-REV + FACT-Q2-26-REV |
| DERIVED-TTM-FCF | DERIVED | TTM FCF | 400 | Q3'25-Q2'26 | calculated | $m | Medium | FACT-Q3-25-REV + FACT-Q4-25-REV + FACT-Q1-26-REV + FACT-Q2-26-REV |
| MODEL-BASE-REFERENCE-VALUE | MODEL | Base forward reference value | 150 | Scenario | runtime | $/share | Medium | RUN-SCENARIO-BASE |
| MODEL-BASE-TARGET-RETURN-PRICE | MODEL | Base target-return price | 120 | Scenario | runtime | $/share | Medium | RUN-RETURN-BASE |
| FACT-SHARES-POINT | FACT | Point-in-time shares | 50 | 2026-08-01 | Tier 1 | shares | High | source |
| FACT-SHARES-WAVG | FACT | Weighted-average diluted shares | 49 | Q2 2026 | Tier 1 | shares | High | source |

### Scenario Assumption Registry

| Assumption ID | Scenario | Variable | Value | Scope | Mode | Base period | Forecast period | Input role | Evidence/rationale | Confidence |
|---|---|---|---:|---|---|---|---|---|---|---|
| ASM-BASE-Q3-REV | Base | Revenue growth | 10% | quarter | yoy | Q3 2025 | Q3 2026 | revenue growth | test | Medium |
| ASM-BASE-Q4-REV | Base | Revenue growth | 10% | quarter | yoy | Q4 2025 | Q4 2026 | revenue growth | test | Medium |
| ASM-BASE-Q1-REV | Base | Revenue growth | 10% | quarter | yoy | Q1 2026 | Q1 2027 | revenue growth | test | Medium |
| ASM-BASE-Q2-REV | Base | Revenue growth | 10% | quarter | yoy | Q2 2026 | Q2 2027 | revenue growth | test | Medium |
| ASM-BASE-MARGIN | Base | Operating margin | 20% | Forward 12M | explicit | - | Forward 12M | operating margin | test | Medium |
| ASM-BASE-TAX | Base | Tax rate | 20% | Forward 12M | explicit | - | Forward 12M | tax rate | test | Medium |
| ASM-BASE-SHARES | Base | Diluted shares | 50 | Forward 12M | explicit | - | Forward 12M | diluted shares | test | Medium |
| ASM-BASE-OTHER | Base | Other income | 0 | Forward 12M | explicit | - | Forward 12M | other income | test | Medium |
| ASM-BASE-CAGR | Base | EPS CAGR | 5% | 5Y | explicit | - | Year 5 | eps cagr | test | Medium |
| ASM-BASE-EXIT | Base | Exit PE | 15 | 5Y | explicit | - | Year 5 | exit pe | test | Medium |
| ASM-BASE-DIV | Base | Dividend yield | 1% | 5Y | explicit | - | Year 1-5 | dividend | test | Medium |
| ASM-TARGET-RETURN | All | Target return | 9% | 5Y | explicit | - | Year 1-5 | target return | test | Medium |
| ASM-BASE-REF-MULT | Base | Reference multiple | 15 | Forward 12M | explicit | - | Forward 12M | reference multiple | test | Medium |
| ASM-BASE-SAFETY | Base | Safety margin | 10% | current | explicit | - | current | safety margin | test | Medium |

### Threshold Policy Registry

| Threshold ID | Metric | Value | Basis | Lookback | Confirmation | Tolerance | Minimum confidence | Rationale |
|---|---|---:|---|---|---|---|---|---|
| THR-ADD-PRICE | Current price | 100 | MODEL-BASE-TARGET-RETURN-PRICE | current | 1 | 0% | Medium | add below price |
| THR-HOLD-FCF | TTM FCF | 350 | history | 4 quarters | 1 | 5% | Medium | hold threshold |
| THR-REDUCE-FCF | TTM FCF | 300 | history | 4 quarters | 1 | 5% | Medium | reduce threshold |
| THR-SELL-FCF | TTM FCF | 100 | thesis | 4 quarters | 2 | 0% | High | sell threshold |

### Revenue Forecast - Runtime Output

| Revenue Bridge ID | Scenario | Forecast period | Mode | Base period | Base Value ID | Growth/Value Assumption ID | Revenue | Runtime Artifact ID |
|---|---|---|---|---|---|---|---:|---|
| REV-BASE-Q3 | Base | Q3 2026 | yoy | Q3 2025 | FACT-Q3-25-REV | ASM-BASE-Q3-REV | 121 | RUN-REV-BASE |
| REV-BASE-Q4 | Base | Q4 2026 | yoy | Q4 2025 | FACT-Q4-25-REV | ASM-BASE-Q4-REV | 132 | RUN-REV-BASE |
| REV-BASE-Q1 | Base | Q1 2027 | yoy | Q1 2026 | FACT-Q1-26-REV | ASM-BASE-Q1-REV | 143 | RUN-REV-BASE |
| REV-BASE-Q2 | Base | Q2 2027 | yoy | Q2 2026 | FACT-Q2-26-REV | ASM-BASE-Q2-REV | 154 | RUN-REV-BASE |

### Scenario EPS Bridge - Runtime Output

| Bridge ID | Scenario | Revenue | Operating margin | Operating income | Other income/expense | Pre-tax income | Tax rate | Net income | Diluted shares | EPS | Input Assumption IDs | Runtime Artifact ID |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BR-BASE | Base | 550 | 20% | 110 | 0 | 110 | 20% | 88 | 50 | 1.76 | ASM-BASE-MARGIN, ASM-BASE-TAX, ASM-BASE-SHARES, ASM-BASE-OTHER | RUN-EPS-BASE |

### Valuation Basis Registry

| Basis ID | Metric | Value | Period | Adjustments | Bridge ID | Input Assumption IDs | Use |
|---|---|---:|---|---|---|---|---|
| B-BASE | EPS/share | 10 | Forward 12M | None | BR-BASE | ASM-BASE-MARGIN, ASM-BASE-TAX, ASM-BASE-SHARES, ASM-BASE-OTHER | Base |

### Scenario Valuation

| Scenario | Basis ID | Metric value | Reference multiple | Forward reference value | Target-return price | Safety margin | Buy price | Input Assumption IDs | Runtime Artifact ID |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| Base | B-BASE | 10 | 15 | 150 | 120 | 10% | 108 | ASM-BASE-REF-MULT, ASM-BASE-SAFETY | RUN-SCENARIO-BASE |

### Return Pair - Runtime Output

| Scenario | Starting Basis ID | Starting EPS | EPS CAGR | Exit PE | Years | Dividend assumption | Target return | 5-year IRR | Required terminal EPS | Required EPS CAGR | Target-return price | Input Assumption IDs | Runtime Artifact ID |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| Base | B-BASE | 10 | 5% | 15 | 5 | 1% yield | 9% | 5% | 15.00 | 8.447% | 120 | ASM-BASE-CAGR, ASM-BASE-EXIT, ASM-BASE-DIV, ASM-TARGET-RETURN | RUN-RETURN-BASE |

### Action Matrix

| Rule ID | Action | Trigger type | Executable condition | Position/execution |
|---|---|---|---|---|
| RULE-BUY | BUY | valuation | FACT-PRICE < THR-ADD-PRICE | buy |
| RULE-ADD | ADD | valuation | FACT-PRICE < THR-ADD-PRICE | add |
| RULE-HOLD | HOLD | operating | DERIVED-TTM-FCF >= THR-HOLD-FCF | hold |
| RULE-REDUCE | REDUCE | operating | DERIVED-TTM-FCF < THR-REDUCE-FCF | reduce |
| RULE-SELL | SELL | thesis | DERIVED-TTM-FCF < THR-SELL-FCF | sell |

### Current Action Evaluation - Runtime Output

| Rule ID | Action | Logic | Condition status | Triggered / indeterminate | Reason |
|---|---|---|---|---|---|
| RULE-BUY | BUY | all | false | false | price |
| RULE-ADD | ADD | all | false | false | price |
| RULE-HOLD | HOLD | all | true | true | fcf |
| RULE-REDUCE | REDUCE | all | false | false | fcf |
| RULE-SELL | SELL | all | false | false | fcf |

### Runtime Artifact Manifest

| Artifact ID | Runtime | Artifact file | Artifact hash | Report section | Status |
|---|---|---|---|---|---|
| RUN-REV-BASE | revenue-bridge | run-rev-base.json | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | Revenue Forecast | PASS |
| RUN-EPS-BASE | eps-bridge | run-eps-base.json | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb | EPS Bridge | PASS |
| RUN-SCENARIO-BASE | scenario-value | run-scenario-base.json | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc | Scenario Valuation | PASS |
| RUN-RETURN-BASE | return-pair | run-return-base.json | dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd | Return Pair | PASS |

### Point-in-Time Share Reconciliation

| Point-in-time shares ID | Point-in-time shares | As-of | Source/Tier | Weighted-average diluted shares | Difference | Market-cap basis |
|---|---:|---|---|---:|---:|---|
| FACT-SHARES-POINT | 50 | 2026-08-01 | Tier 1 | 49 | 1 | FACT-PRICE × FACT-SHARES-POINT |

### Verification

| Check | Result |
|---|---|
| Runtime artifact binding | PASS |
| Global ID graph | PASS |
| Revenue period semantics | PASS |
| Scenario valuation runtime | PASS |
'''


class RuntimeBindingTests(unittest.TestCase):
    def test_artifact_hash_is_deterministic(self):
        a = build_artifact(runtime_name="x", artifact_id="RUN-X", input_refs=["FACT-A"], inputs={"b": 2, "a": 1}, outputs={"z": 3})
        b = build_artifact(runtime_name="x", artifact_id="RUN-X", input_refs=["FACT-A"], inputs={"a": 1, "b": 2}, outputs={"z": 3})
        self.assertEqual(a["artifact_hash"], b["artifact_hash"])

    def test_scenario_value_uses_target_return_price_for_buy_price(self):
        result = scenario_value({
            "artifact_id": "RUN-SCENARIO-BASE", "scenario": "Base", "metric_value": "29.24",
            "reference_multiple": "20", "target_return_price": "456.67", "safety_margin": "0.10",
            "input_refs": ["B-BASE", "ASM-BASE-MULT", "ASM-BASE-SAFETY"],
        })
        self.assertEqual(result["outputs"]["forward_reference_value"], "584.8000")
        self.assertEqual(result["outputs"]["buy_price"], "411.0030")

    def test_valid_report_passes_without_artifact_file_check(self):
        self.assertEqual([x.message for x in validate_text(valid_report()) if x.level == "ERROR"], [])

    def test_wrong_return_pair_terminal_eps_fails(self):
        text = valid_report().replace("| Base | B-BASE | 10 | 5% | 15 | 5 | 1% yield | 9% | 5% | 15.00 | 8.447% |", "| Base | B-BASE | 10 | 5% | 15 | 5 | 1% yield | 9% | 5% | 12.00 | 8.447% |")
        self.assertTrue(any("required terminal EPS" in x.message for x in validate_text(text)))

    def test_wrong_scenario_multiplication_fails(self):
        text = valid_report().replace("| Base | B-BASE | 10 | 15 | 150 |", "| Base | B-BASE | 10 | 15 | 145 |")
        self.assertTrue(any("forward reference value" in x.message for x in validate_text(text)))

    def test_undefined_id_fails(self):
        text = valid_report().replace("FACT-PRICE < THR-ADD-PRICE", "FACT-PRICE < THR-MISSING", 1)
        self.assertTrue(any("undefined ID reference: THR-MISSING" in x.message for x in validate_text(text)))

    def test_action_rule_omission_fails(self):
        text = valid_report().replace("| RULE-ADD | ADD | all | false | false | price |\n", "")
        self.assertTrue(any("omits Matrix rule IDs: RULE-ADD" in x.message for x in validate_text(text)))

    def test_bad_yoy_base_period_fails(self):
        text = valid_report().replace("| REV-BASE-Q3 | Base | Q3 2026 | yoy | Q3 2025 |", "| REV-BASE-Q3 | Base | Q3 2026 | yoy | Q2 2026 |")
        self.assertTrue(any("YoY base period" in x.message for x in validate_text(text)))

    def test_forward_basis_adjustment_fails(self):
        text = valid_report().replace("| B-BASE | EPS/share | 10 | Forward 12M | None |", "| B-BASE | EPS/share | 10 | Forward 12M | ADJ-01 |")
        self.assertTrue(any("must not cite historical Adjustment" in x.message for x in validate_text(text)))

    def test_artifact_files_are_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            payload = build_artifact(runtime_name="revenue-bridge", artifact_id="RUN-REV-BASE", input_refs=["ASM-BASE-Q3-REV"], inputs={}, outputs={})
            (base / "run-rev-base.json").write_text(json.dumps(payload), encoding="utf-8")
            messages = [x.message for x in validate_text(valid_report(), artifacts_dir=base)]
            self.assertTrue(any("Runtime artifact file missing" in x for x in messages))
            self.assertTrue(any("hash mismatch for RUN-REV-BASE" in x for x in messages))


if __name__ == "__main__": unittest.main()

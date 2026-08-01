from __future__ import annotations

import hashlib, json, re
from decimal import Decimal
from pathlib import Path
from typing import Any

from scripts.integrity_common import (
    BAD_RESULTS, D, Finding, artifact_path, canonical_json, decimal, find_table,
    get, norm, percent, placeholder, quarter, refs, relerr, rows, tables,
)


def _err(items: list[Finding], message: str) -> None: items.append(Finding("ERROR", message))


def _require_tables(items: list[Finding], found: dict[str, Any | None]) -> None:
    for name, table in found.items():
        if table is None: _err(items, f"missing {name}")


def _roles(assumptions: dict[str, dict[str, str]], identifiers: set[str]) -> set[str]:
    return {norm(get(assumptions[x], "Input role")) for x in identifiers if x in assumptions}


def _check_required_roles(items: list[Finding], label: str, actual: set[str], required: set[str]) -> None:
    missing = [r for r in required if not any(r in x for x in actual)]
    if missing: _err(items, f"{label} missing assumptions for: {', '.join(missing)}")


def _load_artifacts(items: list[Finding], manifest: dict[str, dict[str, str]], base: Path | None) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for aid, row in manifest.items():
        if norm(get(row, "Status")) != "pass": _err(items, f"Runtime artifact {aid} status is not PASS")
        stated = get(row, "Artifact hash").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", stated): _err(items, f"Runtime artifact {aid} has invalid SHA-256 hash")
        if base is None: continue
        path = artifact_path(base, get(row, "Artifact file"))
        if path is None or not path.exists(): _err(items, f"Runtime artifact file missing for {aid}: {get(row, 'Artifact file')}"); continue
        try: payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc: _err(items, f"Runtime artifact {aid} cannot be read: {exc}"); continue
        if str(payload.get("artifact_id", "")).upper() != aid: _err(items, f"Runtime artifact file ID mismatch for {aid}")
        claimed = str(payload.get("artifact_hash", "")).lower(); body = dict(payload); body.pop("artifact_hash", None)
        calc = hashlib.sha256(canonical_json(body).encode()).hexdigest()
        if claimed != calc or stated != calc: _err(items, f"Runtime artifact hash mismatch for {aid}")
        else: loaded[aid] = payload
    return loaded


def _artifact_outputs(loaded: dict[str, dict[str, Any]], aid: str) -> dict[str, Any] | None:
    payload = loaded.get(aid.upper()); out = payload.get("outputs") if payload else None
    return out if isinstance(out, dict) else None


def _compare_num(items: list[Finding], label: str, report_raw: Any, artifact_raw: Any, *, pct: bool = False, tolerance: str = "0.002") -> None:
    left = percent(report_raw) if pct else decimal(report_raw); right = decimal(artifact_raw)
    if left is None or right is None or relerr(left, right) > D(tolerance): _err(items, f"runtime field mismatch: {label}")


def _bind_artifacts(items: list[Finding], loaded: dict[str, dict[str, Any]], found: dict[str, Any | None]) -> None:
    for row in rows(found["Scenario Valuation table"]):
        aid = get(row, "Runtime Artifact ID").upper(); out = _artifact_outputs(loaded, aid)
        if not out: continue
        for rf, of, pct in [
            ("Metric value", "metric_value", False), ("Reference multiple", "reference_multiple", False),
            ("Forward reference value", "forward_reference_value", False), ("Target-return price", "target_return_price", False),
            ("Safety margin", "safety_margin", True), ("Buy price", "buy_price", False),
        ]: _compare_num(items, f"Scenario {aid} {rf}", get(row, rf), out.get(of), pct=pct, tolerance="0.001")
    for row in rows(found["Return Pair table"]):
        aid = get(row, "Runtime Artifact ID").upper(); out = _artifact_outputs(loaded, aid)
        if not out: continue
        assumptions = out.get("assumptions", {}) if isinstance(out.get("assumptions"), dict) else {}
        irr = out.get("irr", {}) if isinstance(out.get("irr"), dict) else {}; rev = out.get("reverse", {}) if isinstance(out.get("reverse"), dict) else {}
        checks = [
            ("Starting EPS", assumptions.get("starting_eps"), False), ("EPS CAGR", assumptions.get("eps_cagr"), True),
            ("Exit PE", assumptions.get("exit_pe"), False), ("Years", assumptions.get("years"), False),
            ("Target return", assumptions.get("target_return"), True), ("5-year IRR", irr.get("irr_pct"), False),
            ("Required terminal EPS", rev.get("required_terminal_eps"), False), ("Required EPS CAGR", rev.get("required_eps_cagr_pct"), False),
            ("Target-return price", out.get("target_return_price"), False),
        ]
        for field, value, pct in checks: _compare_num(items, f"Return Pair {aid} {field}", get(row, field), value, pct=pct)
    for row in rows(found["EPS Bridge table"]):
        aid = get(row, "Runtime Artifact ID").upper(); out = _artifact_outputs(loaded, aid)
        if not out: continue
        for rf, of in {"Revenue":"revenue","Operating income":"operating_income","Other income/expense":"other_income","Pre-tax income":"pre_tax_income","Net income":"net_income","Diluted shares":"diluted_shares","EPS":"eps"}.items():
            _compare_num(items, f"EPS Bridge {aid} {rf}", get(row, rf), out.get(of))
        for rf, of in {"Operating margin":"operating_margin_pct","Tax rate":"tax_rate_pct"}.items():
            _compare_num(items, f"EPS Bridge {aid} {rf}", get(row, rf), out.get(of))
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows(found["Revenue Forecast table"]): grouped.setdefault(get(row, "Runtime Artifact ID").upper(), []).append(row)
    for aid, report_rows in grouped.items():
        out = _artifact_outputs(loaded, aid)
        if not out: continue
        periods = out.get("periods"); by_id = {str(x.get("id", "")).upper(): x for x in periods if isinstance(x, dict)} if isinstance(periods, list) else {}
        if not by_id: _err(items, f"Revenue artifact {aid} missing periods"); continue
        for row in report_rows:
            rid = get(row, "Revenue Bridge ID").upper(); item = by_id.get(rid)
            if item is None: _err(items, f"Revenue artifact {aid} missing row {rid}")
            else: _compare_num(items, f"Revenue Forecast {rid}", get(row, "Revenue"), item.get("revenue"))


def validate_text(text: str, *, artifacts_dir: Path | None = None, require_artifacts: bool = False) -> list[Finding]:
    items: list[Finding] = []; ts = tables(text)
    found = {
        "Generation Manifest": find_table(ts, {"Field","Value"}),
        "Canonical Value Registry v1.5.1": find_table(ts, {"Value ID","Kind","Metric","Value","Inputs/Formula"}),
        "expanded Scenario Assumption Registry v1.5.1": find_table(ts, {"Assumption ID","Scenario","Variable","Value","Scope","Mode","Base period","Forecast period","Input role","Evidence/rationale","Confidence"}),
        "Threshold Policy Registry": find_table(ts, {"Threshold ID","Metric","Value","Basis","Lookback","Confirmation","Tolerance","Minimum confidence","Rationale"}),
        "Revenue Forecast table": find_table(ts, {"Revenue Bridge ID","Scenario","Forecast period","Mode","Base period","Base Value ID","Growth/Value Assumption ID","Revenue","Runtime Artifact ID"}),
        "EPS Bridge table": find_table(ts, {"Bridge ID","Scenario","Revenue","Operating margin","Tax rate","Diluted shares","EPS","Input Assumption IDs","Runtime Artifact ID"}),
        "Valuation Basis Registry": find_table(ts, {"Basis ID","Metric","Value","Period","Adjustments","Bridge ID","Input Assumption IDs","Use"}),
        "Scenario Valuation table": find_table(ts, {"Scenario","Basis ID","Metric value","Reference multiple","Forward reference value","Target-return price","Safety margin","Buy price","Input Assumption IDs","Runtime Artifact ID"}),
        "Return Pair table": find_table(ts, {"Scenario","Starting Basis ID","Starting EPS","EPS CAGR","Exit PE","Years","Dividend assumption","Target return","5-year IRR","Required terminal EPS","Required EPS CAGR","Target-return price","Input Assumption IDs","Runtime Artifact ID"}),
        "complete Action Matrix": find_table(ts, {"Rule ID","Action","Trigger type","Executable condition","Position/execution"}),
        "Action Evaluation table": find_table(ts, {"Rule ID","Action","Logic","Condition status","Triggered / indeterminate","Reason"}),
        "Runtime Artifact Manifest": find_table(ts, {"Artifact ID","Runtime","Artifact file","Artifact hash","Report section","Status"}),
        "Point-in-Time Share Reconciliation table": find_table(ts, {"Point-in-time shares ID","Point-in-time shares","As-of","Source/Tier","Weighted-average diluted shares","Difference","Market-cap basis"}),
        "Verification table": find_table(ts, {"Check","Result"}),
    }
    _require_tables(items, found)
    gm = found["Generation Manifest"]
    if gm:
        fields = {norm(get(r,"Field")): get(r,"Value") for r in rows(gm)}
        for name in ["skill version","template schema","git commit","report id","runtime artifacts directory"]:
            if name not in fields or placeholder(fields[name]): _err(items, f"Generation Manifest missing {name}")
        if fields.get("skill version", "") != "1.5.1": _err(items, "Generation Manifest Skill version must be 1.5.1")
        if fields.get("template schema", "") != "full-report-v1.5.1": _err(items, "Generation Manifest Template schema must be full-report-v1.5.1")
    if require_artifacts and artifacts_dir is None: _err(items, "--artifacts-dir is required for final v1.5.1 validation")

    definitions: dict[str,str] = {}; defrows: dict[str,dict[str,str]] = {}
    def define(identifier: str, source: str, row: dict[str,str]) -> None:
        key = identifier.strip().upper()
        if placeholder(key): return
        if key in definitions: _err(items, f"duplicate ID definition: {key}")
        else: definitions[key] = source; defrows[key] = row
    for r in rows(found["Canonical Value Registry v1.5.1"]):
        vid = get(r,"Value ID"); define(vid,"value",r); prefix = vid.split("-",1)[0].upper(); kind = get(r,"Kind").upper()
        if prefix in {"FACT","DERIVED","MODEL"} and prefix != kind: _err(items, f"{vid} prefix does not match Kind {kind}")
        if prefix == "FACT" and re.search(r"fair value|reference value|target.return|buy price|stress price|irr", get(r,"Metric"), re.I): _err(items, f"model output cannot be FACT: {vid}")
    for key, col in [("expanded Scenario Assumption Registry v1.5.1","Assumption ID"),("Threshold Policy Registry","Threshold ID"),("Revenue Forecast table","Revenue Bridge ID"),("EPS Bridge table","Bridge ID"),("Valuation Basis Registry","Basis ID"),("Runtime Artifact Manifest","Artifact ID")]:
        for r in rows(found[key]): define(get(r,col),key,r)
    table_text = "\n".join(" | ".join(row) for t in ts for row in t["rows"])
    for ref in sorted(refs(table_text)):
        if ref not in definitions: _err(items, f"undefined ID reference: {ref}")
    for r in rows(found["Canonical Value Registry v1.5.1"]):
        vid = get(r,"Value ID").upper()
        if vid.startswith("DERIVED-"):
            inputs = refs(get(r,"Inputs/Formula"))
            if not inputs: _err(items, f"Derived value {vid} has no explicit input IDs")
            for x in inputs:
                if x not in definitions: _err(items, f"Derived value {vid} references undefined input {x}")

    assumptions = {get(r,"Assumption ID").upper():r for r in rows(found["expanded Scenario Assumption Registry v1.5.1"])}
    for aid, r in assumptions.items():
        for field in ["Scope","Mode","Forecast period","Input role","Evidence/rationale","Confidence"]:
            if placeholder(get(r,field)): _err(items, f"Assumption {aid} missing {field}")
    for r in rows(found["Revenue Forecast table"]):
        rid = get(r,"Revenue Bridge ID").upper(); mode = norm(get(r,"Mode")); fp = quarter(get(r,"Forecast period")); bp = quarter(get(r,"Base period")); aid = get(r,"Growth/Value Assumption ID").upper(); bvid = get(r,"Base Value ID").upper()
        if mode in {"yoy","qoq"}:
            if fp is None or bp is None: _err(items, f"Revenue {rid} {mode} requires parseable periods")
            elif mode == "yoy" and bp != (fp[0]-1,fp[1]): _err(items, f"Revenue {rid} YoY base period is not prior-year same quarter")
            elif mode == "qoq" and bp != ((fp[0]-1,4) if fp[1]==1 else (fp[0],fp[1]-1)): _err(items, f"Revenue {rid} QoQ base period is not previous quarter")
            if bvid not in definitions: _err(items, f"Revenue {rid} references undefined base Value ID {bvid}")
        if aid not in assumptions: _err(items, f"Revenue {rid} references undefined Assumption {aid}")
        else:
            a = assumptions[aid]
            if norm(get(a,"Mode")) != mode: _err(items, f"Revenue {rid} mode mismatches {aid}")
            if fp and quarter(get(a,"Forecast period")) and fp != quarter(get(a,"Forecast period")): _err(items, f"Revenue {rid} forecast period mismatches {aid}")
            if bp and quarter(get(a,"Base period")) and bp != quarter(get(a,"Base period")): _err(items, f"Revenue {rid} base period mismatches {aid}")
        if get(r,"Runtime Artifact ID").upper() not in definitions: _err(items, f"Revenue {rid} has undefined runtime artifact")

    for r in rows(found["EPS Bridge table"]):
        bid = get(r,"Bridge ID").upper(); used = refs(get(r,"Input Assumption IDs")); _check_required_roles(items, f"EPS Bridge {bid}", _roles(assumptions,used), {"operating margin","tax rate","diluted shares","other income"})
        if get(r,"Runtime Artifact ID").upper() not in definitions: _err(items, f"EPS Bridge {bid} has undefined runtime artifact")
    for r in rows(found["Valuation Basis Registry"]):
        bid = get(r,"Basis ID").upper()
        if "forward" in norm(get(r,"Period")):
            if norm(get(r,"Adjustments")) not in {"","none","n/a","na","无"}: _err(items, f"Forward Basis {bid} must not cite historical Adjustment IDs")
            if not refs(get(r,"Input Assumption IDs")): _err(items, f"Forward Basis {bid} has no Input Assumption IDs")
    for r in rows(found["Scenario Valuation table"]):
        name = get(r,"Scenario"); metric=decimal(get(r,"Metric value")); mult=decimal(get(r,"Reference multiple")); reference=decimal(get(r,"Forward reference value")); target=decimal(get(r,"Target-return price")); margin=percent(get(r,"Safety margin")); buy=decimal(get(r,"Buy price"))
        if None in {metric,mult,reference,target,margin,buy}: _err(items, f"Scenario {name} has unparseable numeric field")
        else:
            if relerr(reference,metric*mult)>D("0.002"): _err(items, f"Scenario {name} forward reference value mismatch")
            if relerr(buy,target*(D(1)-margin))>D("0.002"): _err(items, f"Scenario {name} buy price mismatch")
        _check_required_roles(items,f"Scenario {name}",_roles(assumptions,refs(get(r,"Input Assumption IDs"))),{"reference multiple","safety margin"})
    for r in rows(found["Return Pair table"]):
        name=get(r,"Scenario"); start=decimal(get(r,"Starting EPS")); years=decimal(get(r,"Years")); terminal=decimal(get(r,"Required terminal EPS")); cagr=percent(get(r,"Required EPS CAGR"))
        if None in {start,years,terminal,cagr}: _err(items, f"Return Pair {name} has unparseable terminal fields")
        elif relerr(terminal,start*(D(1)+cagr)**int(years))>D("0.005"): _err(items, f"Return Pair {name} required terminal EPS does not reconcile")
        _check_required_roles(items,f"Return Pair {name}",_roles(assumptions,refs(get(r,"Input Assumption IDs"))),{"eps cagr","exit pe","dividend","target return"})

    matrix = {get(r,"Rule ID"):r for r in rows(found["complete Action Matrix"]) if not placeholder(get(r,"Rule ID"))}
    evaluated = {get(r,"Rule ID"):r for r in rows(found["Action Evaluation table"]) if not placeholder(get(r,"Rule ID"))}
    for rid,r in matrix.items():
        if re.search(r"current action is not|N/A\s*[—-]",get(r,"Executable condition"),re.I): _err(items, f"Action rule {rid} may not be omitted")
    if set(matrix)!=set(evaluated):
        if set(matrix)-set(evaluated): _err(items, f"Action Evaluation omits Matrix rule IDs: {', '.join(sorted(set(matrix)-set(evaluated)))}")
        if set(evaluated)-set(matrix): _err(items, f"Action Evaluation contains undeclared rule IDs: {', '.join(sorted(set(evaluated)-set(matrix)))}")

    manifest={get(r,"Artifact ID").upper():r for r in rows(found["Runtime Artifact Manifest"])}; loaded=_load_artifacts(items,manifest,artifacts_dir)
    if loaded: _bind_artifacts(items,loaded,found)
    share_rows=rows(found["Point-in-Time Share Reconciliation table"])
    if not share_rows: _err(items,"Point-in-Time Share Reconciliation has no data row")
    for r in share_rows:
        for field in ["Point-in-time shares ID","Point-in-time shares","As-of","Source/Tier","Weighted-average diluted shares","Difference","Market-cap basis"]:
            if placeholder(get(r,field)): _err(items,f"Share reconciliation missing {field}")
    verification=rows(found["Verification table"])
    for r in verification:
        if any(x in norm(get(r,"Result")) for x in BAD_RESULTS): _err(items,f"Verification incomplete: {get(r,'Check')} = {get(r,'Result')}")
    seen={norm(get(r,"Check")) for r in verification}
    for required in ["runtime artifact binding","global id graph","revenue period semantics","scenario valuation runtime"]:
        if not any(required in x for x in seen): _err(items,f"Verification missing required check: {required}")
    return items

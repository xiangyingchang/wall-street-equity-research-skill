from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.meta_v21_factory import make_spec as _base_spec


def _pointer(ref: str) -> str:
    if not ref.startswith("BUNDLE:"):
        return ref
    raw = ref.removeprefix("BUNDLE:")
    if raw.startswith("derived.payback_required_growth."):
        raw = "derived.payback_required_growth"
    return "BUNDLE:/" + raw.replace(".", "/")


def _normalize_research(value: Any) -> None:
    if isinstance(value, dict):
        refs = value.get("evidence_refs")
        if isinstance(refs, list):
            value["evidence_refs"] = [
                {"ref": _pointer(str(ref.get("ref", ""))), "role": str(ref.get("role", "supports"))}
                if isinstance(ref, dict)
                else {"ref": _pointer(str(ref)), "role": "supports"}
                for ref in refs
            ]
        for child in value.values():
            _normalize_research(child)
    elif isinstance(value, list):
        for child in value:
            _normalize_research(child)


def make_spec() -> dict[str, Any]:
    spec = _base_spec()
    spec["schema_version"] = "report-spec-v2.1.1"
    for scope in ("shares", "current price"):
        if scope not in spec["sources"]["SRC-META-Q2-2026"]["scope"]:
            spec["sources"]["SRC-META-Q2-2026"]["scope"].append(scope)
    names = [
        "网络效应与关系链核心护城河能力",
        "数据资产与广告技术基础设施能力",
        "多边生态网络与产品分发协同能力",
        "资本实力与长期组织执行竞争能力",
    ]
    for item, name in zip(spec["research"]["moat"]["dimensions"], names):
        item["name"] = name
    for risk in spec["research"]["risks"]["items"]:
        risk["leading_indicators"] = [text if len(text) >= 12 else f"{text}并形成持续趋势。" for text in risk["leading_indicators"]]
    _normalize_research(spec["research"])

    valuation = spec["research"]["valuation"]["reverse_expectations"]
    valuation.pop("text", None)
    valuation["text_template"] = "当前价格对应 Base IRR 为 {base_irr}，低于目标回报 {target_return}，因此需要更强的经营兑现。"
    valuation["value_refs"] = {
        "base_irr": {"path": "/decision/valuation/base_irr", "format": "percent"},
        "target_return": {"path": "/decision/valuation/target_return", "format": "percent"},
    }

    new_money = spec["research"]["positioning"]["new_money"]
    new_money.pop("text", None)
    new_money["text_template"] = "新资金应等待 Base target-return price {target_price} 或更强的经营证据，而不是在当前价格主动买入。"
    new_money["value_refs"] = {
        "target_price": {"path": "/scenarios/base/prices/target_return", "format": "money"},
    }
    return spec


def write_spec(path: Path) -> None:
    path.write_text(json.dumps(make_spec(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_spec(args.output)

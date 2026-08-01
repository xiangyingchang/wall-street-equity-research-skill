from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.meta_v21_factory import make_spec as _base_spec


def make_spec() -> dict[str, Any]:
    spec = _base_spec()
    names = [
        "网络效应与关系链核心护城河能力",
        "数据资产与广告技术基础设施能力",
        "多边生态网络与产品分发协同能力",
        "资本实力与长期组织执行竞争能力",
    ]
    for item, name in zip(spec["research"]["moat"]["dimensions"], names):
        item["name"] = name
    return spec


def write_spec(path: Path) -> None:
    path.write_text(json.dumps(make_spec(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_spec(args.output)

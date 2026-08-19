"""批量创建国家 Tag（算法层）

为一个或多个 tag 生成：
  - history/countries/TAG - Name.txt  骨架
  - common/country_tags/00_countries.txt  条目行
  - 本地化 TAG 名称
只生成文本/行；写文件由调用方负责（原子写）。
"""

from __future__ import annotations

from typing import Dict, List


def country_history_skeleton(tag: str, name: str = "") -> str:
    """ini_tag 国家历史文件骨架。"""
    tag = tag.upper()
    return ("### {}\n".format(name or tag) +
            "{} = {{\n".format(tag) +
            "}\n")


def country_tag_line(tag: str, name: str) -> str:
    """返回 country_tags 行：TAG:0 "countries/Name.txt"。"""
    return '{}:0 "countries/{}.txt"'.format(tag.upper(), name or tag.upper())


def generate_country_bootstrap(countries: List[dict]) -> dict:
    """生成批量国家内容。

    countries: [{tag, name, file_name}]
    返回 {"histories": {file_name: text}, "tag_lines": [...], "loc": [...], "count"}
    """
    histories: Dict[str, str] = {}
    tag_lines = []
    locs: List[dict] = []
    for c in countries:
        tag = (c.get("tag") or "").strip().upper()
        if not tag:
            continue
        name = c.get("name") or tag
        file_name = c.get("file_name") or name
        histories.setdefault(file_name + ".txt", country_history_skeleton(tag, name))
        tag_lines.append(country_tag_line(tag, file_name))
        locs.append({"key": tag, "value": name})
    return {"histories": histories, "tag_lines": tag_lines, "loc": locs,
            "count": len(countries)}
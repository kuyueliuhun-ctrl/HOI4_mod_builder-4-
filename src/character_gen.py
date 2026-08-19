"""Character 生成器（算法层）

生成 characters 定义骨架（按国家 TAG 分组）+ 本地化。
"""

from __future__ import annotations

from typing import Dict, List


def generate_characters(groups: List[dict]) -> dict:
    """生成 characters 文件。

    groups: [{tag: str, characters: [{id, name_loc, portraits:[pic]}]}]
    """
    blocks = ["characters = {"]
    locs: List[dict] = []
    for g in groups:
        tag = (g.get("tag") or "").strip()
        if not tag:
            continue
        blocks.append("\t" + tag + " = {")
        for c in g.get("characters", []):
            cid = (c.get("id") or "").strip()
            if not cid:
                continue
            name_loc = c.get("name_loc") or (tag + "_" + cid)
            blocks.append("\t\t" + cid + " = {")
            blocks.append("\t\t\tname = " + name_loc)
            portraits = c.get("portraits") or [
                "gfx/interface/portraits/{}_civilian.dds".format(cid)]
            blocks.append("\t\t\tportraits = {")
            for i, p in enumerate(portraits):
                grp = ("army" if i % 3 == 1 else "navy" if i % 3 == 2 else "civilian")
                blocks.append("\t\t\t\t{} = {{ {} }}".format(grp, p))
            blocks.append("\t\t\t}")
            blocks.append("\t\t}")
            locs.append({"key": name_loc, "value": cid + " 姓名"})
            locs.append({"key": name_loc + "_desc", "value": cid + " 简介"})
        blocks.append("\t}")
    blocks.append("}")
    return {"text": "\n".join(blocks) + "\n", "loc": locs, "count": len(locs) // 2}
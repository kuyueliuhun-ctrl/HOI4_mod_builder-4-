"""意识形态生成器（算法层）

生成 ideologies 定义骨架（color 占位）+ 本地化。
"""

from __future__ import annotations

from typing import Dict, List


def generate_ideologies(ideologies: List[dict]) -> dict:
    """生成 ideologies 文件。

    ideologies: [{id, color: [r,g,b]|None}]
    """
    blocks = ["ideologies = {"]
    locs: List[dict] = []
    for it in ideologies:
        iid = (it.get("id") or "").strip()
        if not iid:
            continue
        blocks.append("\t" + iid + " = {")
        color = it.get("color") or [127, 127, 127]
        blocks.append("\t\tcolor = { %s %s %s }" % tuple(color))
        blocks.append("\t\twar_support = 0")
        blocks.append("\t\tcan_be_toppled = no")
        blocks.append("\t\tdynamic_faction_names = {")
        blocks.append("\t\t}")
        blocks.append("\t}")
        locs.append({"key": iid, "value": iid + " 意识形态名"})
        locs.append({"key": iid + "_desc", "value": iid + " 描述"})
    blocks.append("}")
    return {"text": "\n".join(blocks) + "\n", "loc": locs, "count": len(locs) // 2}
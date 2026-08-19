"""民族精神（ideas）生成器（算法层）

生成民族精神定义骨架 + 本地化占位（名称 + 描述）。
"""

from __future__ import annotations

from typing import Dict, List


def generate_ideas(ideas: List[dict]) -> dict:
    """生成 ideas 文件。

    ideas: [{id, picture, modifier: str|None}]
    返回 {"text", "loc": [{key,value}], "count"}
    """
    blocks = ["ideas = {"]
    locs: List[dict] = []
    for it in ideas:
        iid = (it.get("id") or "").strip()
        if not iid:
            continue
        pic = (it.get("picture") or "GFX_idea_" + iid).strip()
        blocks.append("\t" + iid + " = {")
        blocks.append("\t\tpicture = {}".format(pic))
        blocks.append("\t\tallowed = {")
        blocks.append("\t\t\talways = yes")
        blocks.append("\t\t}")
        blocks.append("\t\tcost = 0")
        if it.get("modifier"):
            blocks.append("\t\tmodifier = {")
            blocks.append("\t\t\t" + str(it["modifier"]).strip())
            blocks.append("\t\t}")
        blocks.append("\t}")
        locs.append({"key": iid, "value": iid + " 名称"})
        locs.append({"key": iid + "_desc", "value": iid + " 描述"})
    blocks.append("}")
    return {"text": "\n".join(blocks) + "\n", "loc": locs, "count": len(locs) // 2}
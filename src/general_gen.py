"""将领代码批量生成器（算法层）

在 Character 内生成 leader（将领/元帅）块骨架 + 本地化。
"""

from __future__ import annotations

from typing import Dict, List


def generate_leader_blocks(leaders: List[dict], character_id: str = "leader") -> dict:
    """生成将领 leader 块。

    leaders: [{name_loc, ideology, traits:[...]}]
    返回 {"text", "loc"}
    """
    blocks = []
    locs: List[dict] = []
    for i, l in enumerate(leaders):
        nloc = l.get("name_loc") or "{}_{}".format(character_id, i)
        blocks.append("\tleader = {")
        blocks.append("\t\tname = " + nloc)
        blocks.append("\t\tideology = " + (l.get("ideology") or "neutrality"))
        blocks.append("\t\ttraits = {")
        for t in l.get("traits", []):
            blocks.append("\t\t\t" + str(t))
        blocks.append("\t\t}")
        blocks.append("\t}")
        locs.append({"key": nloc, "value": nloc + " 将领名"})
        locs.append({"key": nloc + "_desc", "value": nloc + " 简介"})
    return {"text": "\n".join(blocks) + "\n", "loc": locs,
            "count": len(leaders)}
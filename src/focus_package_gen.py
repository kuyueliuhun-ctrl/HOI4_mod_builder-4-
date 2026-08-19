"""国策全套生成器（算法层）

从国策清单生成配套三件套文本：
  - 国策树定义骨架（focus .txt）
  - 本地化名称/描述占位
  - 图标 GFX spriteTypes（可选，从图标名+纹理）
注：光效 GFX 的补全由实体资源工作台承担。
"""

from __future__ import annotations

from typing import Dict, List, Optional


def generate_focus_tree(focuses: List[dict], tree_id: str = "PROJECT") -> dict:
    """生成国策树定义文本。

    focuses: [{id, x, y, icon, prerequisite:[id], mutually_exclusive:[id]}]
    """
    focus_tree_id = (tree_id or "PROJECT").strip()
    lines = ["focus_tree = {"]
    lines.append("\tid = " + focus_tree_id)
    lines.append("\tcountry = {")
    lines.append("\t\tfactor = 0")
    lines.append("\t}")
    lines.append("")
    lines.append("\tdefault = no")
    lines.append("")
    for f in focuses:
        fid = f.get("id") or ""
        if not fid:
            continue
        x = f.get("x", 0)
        y = f.get("y", 0)
        lines.append("\tfocus = {")
        lines.append("\t\tid = " + fid)
        if f.get("icon"):
            lines.append("\t\ticon = " + str(f["icon"]))
        prerequisite = f.get("prerequisite") or []
        mutex = f.get("mutually_exclusive") or []
        if prerequisite:
            lines.append("\t\tprerequisite = {")
            for p in prerequisite:
                lines.append("\t\t\tfocus = " + str(p))
            lines.append("\t\t}")
        if mutex:
            lines.append("\t\tmutually_exclusive = {")
            for p in mutex:
                lines.append("\t\t\tfocus = " + str(p))
            lines.append("\t\t}")
        lines.append("\t\tx = {}".format(x))
        lines.append("\t\ty = {}".format(y))
        lines.append("\t\tcost = 10")
        lines.append("\t}")
        lines.append("")
    lines.append("}")
    return {"text": "\n".join(lines) + "\n"}


def generate_loc(focuses: List[dict]) -> List[dict]:
    """为国策生成本地化占位（名称 + 描述）。"""
    locs: List[dict] = []
    for f in focuses:
        fid = f.get("id") or ""
        if not fid:
            continue
        locs.append({"key": fid, "value": (f.get("name") or (fid + " 名称"))})
        locs.append({"key": fid + "_desc", "value": (f.get("desc") or (fid + " 描述"))})
    return locs


def generate_icon_gfx(focuses: List[dict], texture_of: callable = None,
                      gfx_path: str = "gfx/interface/goals/{icon}.dds") -> str:
    """生成图标 spriteTypes 文本。texture_of(icon) 可选覆写纹理路径。"""
    out = ["spriteTypes = {"]
    seen = set()
    for f in focuses:
        icon = str(f.get("icon") or "").strip()
        if not icon or icon in seen:
            continue
        seen.add(icon)
        tex = texture_of(icon) if texture_of else gfx_path.format(icon=icon)
        out.append("\tspriteType = {")
        out.append('\t\tname = "{}"'.format(icon))
        out.append('\t\ttexturefile = "{}"'.format(tex))
        out.append("\t}")
    out.append("}")
    return "\n".join(out) + "\n"


def generate_package(focuses: List[dict], tree_id: str = "PROJECT",
                     with_icon_gfx: bool = True) -> dict:
    """生成全套（树 + 本地化 + 图标 GFX）。"""
    return {
        "tree": generate_focus_tree(focuses, tree_id),
        "loc": generate_loc(focuses),
        "count": sum(1 for f in focuses if f.get("id")),
    }
"""interface / gfx 批量注册（算法层）

对 interface/*.gfx 补写缺失的 SpriteType；对 *.gui 目前仅扫描（只读）。
复用 icon_ops.update_gfx_file 的单条写入语义。
"""

from __future__ import annotations

import os
from typing import Dict, List

from icon_ops import update_gfx_file


def register_sprites(gfx_path: str, sprites: Dict[str, str]) -> int:
    """批量注册 sprite → texture 到 gfx 文件（已有 sprite 名不覆盖，跳过）。

    返回实际新增条数（本次写入的）。注意 update_gfx_file 会整段重写并覆盖同名，
    因此这里先读出现有 sprite 名，跳过已存在的。
    """
    from icon_ops import update_gfx_file as _u  # noqa
    existing = _read_sprite_names(gfx_path)
    added = 0
    for name, texture in sprites.items():
        if name in existing:
            continue
        update_gfx_file(gfx_path, name, texture)
        existing.add(name)
        added += 1
    return added


def _read_sprite_names(gfx_path: str) -> set:
    import re
    names = set()
    if not os.path.isfile(gfx_path):
        return names
    try:
        with open(gfx_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except OSError:
        return names
    for m in re.finditer(r'name\s*=\s*"([^"]+)"', content):
        names.add(m.group(1))
    return names


def scan_gui_refs(mod_path: str) -> List[str]:
    """扫描 interface/*.gui 的文件（只读辅助，返回文件相对列表）。"""
    out = []
    base = os.path.join(mod_path, "interface")
    if not os.path.isdir(base):
        return out
    for root, _dirs, names in os.walk(base):
        for n in names:
            if n.lower().endswith(".gui"):
                out.append(os.path.relpath(os.path.join(root, n), mod_path).replace("\\", "/"))
    return out
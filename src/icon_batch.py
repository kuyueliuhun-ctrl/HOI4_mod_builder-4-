"""图标 GFX 批量注册（算法层）

扫描脚本文件（国策/理念/科技等）里全部实体的图标引用，
为「缺失且已存在对应贴图文件」的图标补写 SpriteType 注册，已有不改。
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from icon_ops import update_gfx_file

_IMG_EXTS = (".dds", ".png", ".jpg", ".jpeg", ".tga")


def _read_text(path):
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        return f.read()


def scan_icon_refs(mod_path: str, rel_file: str,
                   content_type: str = "focus") -> List[dict]:
    """扫描单个文件内实体 id → icon 引用。

    返回 [{id, icon}]（icon 去空）。
    """
    from entity_scanner import EntityScanner
    fp = os.path.join(mod_path, rel_file.replace("/", os.sep))
    if not os.path.isfile(fp):
        return []
    try:
        content = _read_text(fp)
        entities = EntityScanner._collect_file_entities(content_type, content, fp)
    except Exception:
        return []
    seen = set()
    out = []
    for e in entities:
        icon = (e.get("icon") or "").strip()
        eid = e.get("name") or ""
        if not icon or not eid:
            continue
        if (eid, icon) in seen:
            continue
        seen.add((eid, icon))
        out.append({"id": eid, "icon": icon})
    return out


def _search_dirs(mod_path: str, icon: str) -> List[str]:
    """在 mod 常见图标目录里搜索与 icon 同名/对应的贴图文件。"""
    from content_types import ICON_RULES, CONTENT_TYPES
    # 汇总所有类型 dirs
    dirs = []
    for c in CONTENT_TYPES:
        cfg = ICON_RULES.get(c[0]) or {}
        for d in cfg.get("dirs", []):
            if d not in dirs:
                dirs.append(d)
    if not dirs:
        dirs = ["gfx/interface/goals", "gfx/interface/decisions", "gfx/interface/ideas"]
    # 候选文件名：icon 名本身；去 GFX_ 前缀；去 _medium/_small 后缀
    candidates = [icon]
    short = icon
    if short.startswith("GFX_"):
        short = short[4:]
    for suffix in ("_medium", "_small", "_icon_medium", "_icon_small"):
        if short.endswith(suffix):
            short = short[: -len(suffix)]
            break
    for pref in ("GFX_", ""):
        candidates.append(pref + short)
    for d in dirs:
        base_dir = os.path.join(mod_path, d.replace("/", os.sep))
        if not os.path.isdir(base_dir):
            continue
        for cand in candidates:
            for ext in _IMG_EXTS:
                fp = os.path.join(base_dir, cand + ext)
                if os.path.isfile(fp):
                    return [os.path.join(d, cand + ext).replace("\\", "/"), cand + ext]
    return []


def build_sprite_index(mod_path: str, hoi4_path: str = "") -> set:
    """收集 mod+game 已注册的 sprite 名集合。"""
    from entity_resource_data import build_gfx_index
    return set(build_gfx_index(mod_path, hoi4_path).keys())


def register_missing_gfx(mod_path: str, rel_file: str,
                         content_type: str = "focus",
                         gfx_file: Optional[str] = None,
                         hoi4_path: str = "") -> Dict[str, object]:
    """为文件中缺失的图标补写 GFX 注册（已有不改）。

    返回 {"registered": int, "skipped_no_texture": int, "items": [...]}
    """
    from content_types import ICON_RULES
    cfg = (ICON_RULES.get(content_type) or {}).get("upload") or {}
    target_gfx = gfx_file or cfg.get("gfx_file") or "goals_mod.gfx"
    registered_index = build_sprite_index(mod_path, hoi4_path)

    refs = scan_icon_refs(mod_path, rel_file, content_type)
    registered = 0
    skipped = 0
    items = []
    for ref in refs:
        icon = ref["icon"]
        if icon in registered_index:
            continue  # 已有，不改
        found = _search_dirs(mod_path, icon)
        if not found:
            skipped += 1
            items.append({"id": ref["id"], "icon": icon, "action": "缺贴图，跳过"})
            continue
        texture_rel = found[0]
        update_gfx_file(os.path.join(mod_path, "interface", target_gfx),
                        icon, texture_rel)
        registered += 1
        items.append({"id": ref["id"], "icon": icon, "texture": texture_rel,
                      "action": "已注册"})
    return {"registered": registered, "skipped_no_texture": skipped, "items": items}


def register_missing_gfx_multi(mod_path: str, rel_files, hoi4_path: str = "") -> Dict[str, object]:
    """批量：对多个 (rel_file, content_type) 注册缺失 GFX。"""
    total = 0
    skipped = 0
    results = []
    for rel_file, content_type in rel_files:
        r = register_missing_gfx(mod_path, rel_file, content_type, hoi4_path=hoi4_path)
        total += r["registered"]
        skipped += r["skipped_no_texture"]
        results.append({"file": rel_file, **r})
    return {"registered": total, "skipped_no_texture": skipped, "results": results}
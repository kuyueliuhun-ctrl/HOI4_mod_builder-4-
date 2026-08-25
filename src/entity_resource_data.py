"""实体配套资源数据层（算法层）

为“实体配套资源工作台”提供数据：
  - 按文件/国家/目录收集可本地化、可上传图标的实体
  - 提取已有翻译（中/英）、图标引用、普通 GFX / 光效 GFX 注册情况
  - 只补缺失光效 GFX（已有不改）；本地化写入只写 mod
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

from write_utils import atomic_write_text

# 默认拥有“名称 + 描述”约定的类型（其余按实体实际 loc_keys 展示）
_DESC_TYPES = {
    "focus", "idea", "decision", "tech", "character",
    "country_leader", "advisor_assign", "ideology", "bookmark",
    "scripted_effects", "scripted_triggers", "script_enums", "mio", "equipment", "unit", "state", "idea_tag",
    "opinion_modifiers", "operations", "on_actions", "wargoal",
}


def _read_text(path):
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        return f.read()


def _iter_gfx_files(scope_path):
    """递归扫描 scope_path 下所有 .gfx 文件。"""
    if not scope_path or not os.path.isdir(scope_path):
        return
    for root, _dirs, names in os.walk(scope_path):
        for name in names:
            if name.lower().endswith(".gfx"):
                yield os.path.join(root, name)


def _parse_gfx_sprites(content):
    """从 gfx 文件中提取 sprite 名 → texturefile。"""
    out = {}
    for m in re.finditer(r"SpriteType\s*=\s*\{(.*?)\}", content, re.DOTALL | re.IGNORECASE):
        block = m.group(1)
        nm = re.search(r'name\s*=\s*"([^"]+)"', block)
        tx = re.search(r'texturefile\s*=\s*"([^"]+)"', block)
        if nm:
            out[nm.group(1)] = tx.group(1) if tx else ""
    return out


def build_gfx_index(mod_path: str, hoi4_path: str = "") -> Dict[str, dict]:
    """扫描 mod + 游戏 interface/gfx 下的全部 SpriteType。

    返回: {sprite_name: {"texture": 相对路径, "file": gfx文件路径, "exists": 贴图是否存在}}
    """
    index: Dict[str, dict] = {}
    for base in (mod_path, hoi4_path):
        for gfx_path in _iter_gfx_files(base):
            try:
                content = _read_text(gfx_path)
            except OSError:
                continue
            for name, texture in _parse_gfx_sprites(content).items():
                exists = False
                if texture:
                    full = os.path.join(base, texture.replace("/", os.sep))
                    exists = os.path.isfile(full)
                # mod 优先覆盖游戏同名 sprite
                index[name] = {"texture": texture, "file": gfx_path, "exists": exists}
    return index


def _icon_map_for_file(mod_path, rel_file, content_type):
    """扫描单个文件内实体 key → icon 的映射。"""
    from entity_scanner import EntityScanner
    fp = os.path.join(mod_path, rel_file.replace("/", os.sep))
    try:
        content = _read_text(fp)
    except OSError:
        return {}
    try:
        entities = EntityScanner._collect_file_entities(content_type, content, fp)
    except Exception:
        return {}
    return {e.get("name", ""): e.get("icon", "") for e in entities}


def collect_resource_items(mod_path: str, hoi4_path: str = "",
                           filepath: Optional[str] = None,
                           country: Optional[str] = None) -> List[dict]:
    """收集实体配套资源列表。

    参数：
        filepath  相对 mod 根目录的文件路径（如 common/national_focus/xxx.txt）
        country   国家 tag（按实体 country 字段或 key 前缀过滤）
    """
    from validation import collect_entity_keys
    from localisation_editor_data import load_effective_dict

    entities = collect_entity_keys(mod_path)
    if filepath:
        fp_norm = filepath.replace("\\", "/")
        entities = [e for e in entities if e.get("file") == fp_norm]
    if country:
        c = country.upper()
        entities = [e for e in entities
                    if (e.get("country") or "").upper() == c
                    or (e.get("key") or "").upper().startswith(c + "_")]

    chinese = load_effective_dict(mod_path, hoi4_path, "simp_chinese")
    english = load_effective_dict(mod_path, hoi4_path, "english")
    gfx_index = build_gfx_index(mod_path, hoi4_path)

    # 每个文件/类型只解析一次图标映射
    icon_cache = {}
    items = []
    for ent in entities:
        rel = ent.get("file", "")
        ctype = ent.get("type", "")
        cache_key = (rel, ctype)
        if cache_key not in icon_cache:
            icon_cache[cache_key] = _icon_map_for_file(mod_path, rel, ctype)
        icon = (icon_cache[cache_key].get(ent.get("key", "")) or "").strip()
        loc_keys = list(ent.get("loc_keys") or [ent.get("key", "")])
        base = ent.get("key", "")
        if ctype not in ("event", "super_event") and base:
            if base not in loc_keys:
                loc_keys.insert(0, base)
            desc = base + "_desc"
            if desc not in loc_keys:
                loc_keys.append(desc)

        tr = {"simp_chinese": {}, "english": {}}
        for k in loc_keys:
            tr["simp_chinese"][k] = chinese.get(k, "")
            tr["english"][k] = english.get(k, "")

        icon_info = gfx_index.get(icon) if icon else None
        shine_info = gfx_index.get(icon + "_shine") if icon else None
        items.append({
            "key": base,
            "type": ctype,
            "file": rel,
            "loc_keys": loc_keys,
            "translations": tr,
            "icon": icon,
            "icon_registered": bool(icon_info),
            "icon_file_exists": bool(icon_info and icon_info["exists"]),
            "icon_texture": (icon_info["texture"] if icon_info else ""),
            "shine_registered": bool(shine_info),
            "shine_gfx_file": (shine_info["file"] if shine_info else ""),
            "country": ent.get("country", ""),
        })
    items.sort(key=lambda x: (x["file"], x["key"]))
    return items


_SHINE_TEMPLATE = '''    SpriteType = {
        name = "{ICON}_shine"
        texturefile = "{TEXTURE}"
        effectFile = "gfx/FX/buttonstate.lua"
        animation = {{
            animationmaskfile = "{TEXTURE}"
            animationtexturefile = "gfx/interface/goals/shine_overlay.dds"
            animationrotation = -90.0
            animationlooping = no
            animationtime = 0.75
            animationdelay = 0
            animationblendmode = "add"
            animationtype = "scrolling"
            animationrotationoffset = {{ x = 0.0 y = 0.0 }}
            animationtexturescale = {{ x = 2.0 y = 1.0 }}
        }}
        animation = {{
            animationmaskfile = "{TEXTURE}"
            animationtexturefile = "gfx/interface/goals/shine_overlay.dds"
            animationrotation = 90.0
            animationlooping = no
            animationtime = 0.75
            animationdelay = 0
            animationblendmode = "add"
            animationtype = "scrolling"
            animationrotationoffset = {{ x = 0.0 y = 0.0 }}
            animationtexturescale = {{ x = 1.0 y = 1.0 }}
        }}
        legacy_lazy_load = no
        transparencecheck = yes
    }}'''


def default_shine_gfx_path(mod_path: str) -> str:
    """默认光效 GFX 文件（mod/interface/goals_shine_mod.gfx）。"""
    return os.path.join(mod_path, "interface", "goals_shine_mod.gfx")


def ensure_shine_gfx(mod_path: str, icon_name: str, icon_texture: str,
                     shine_gfx_path: Optional[str] = None) -> bool:
    """为图标补写缺失的光效 SpriteType（已有则跳过，不修改）。

    返回 True 表示本次实际写入；False 表示已存在或参数不足。
    """
    if not icon_name or not icon_texture:
        return False
    shine_name = icon_name + "_shine"
    index = build_gfx_index(mod_path)
    if shine_name in index:
        return False  # 已有光效，不改

    path = shine_gfx_path or default_shine_gfx_path(mod_path)
    block = _SHINE_TEMPLATE.replace("{ICON}", icon_name).replace("{TEXTURE}", icon_texture)
    content = ""
    if os.path.isfile(path):
        content = _read_text(path)
    if "spriteTypes = {" in content:
        # 在 spriteTypes 块的最后一个 } 前插入
        m = re.search(r"spriteTypes\s*=\s*\{", content)
        open_idx = m.end()
        close_idx = content.rfind("}")
        if close_idx <= open_idx:
            return False
        new_content = content[:close_idx].rstrip() + "\n" + block + "\n" + content[close_idx:]
    else:
        new_content = "spriteTypes = {\n" + block + "\n}\n"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    atomic_write_text(path, new_content, encoding="utf-8")
    return True


def save_loc_edits(mod_path: str, edits: List[dict]) -> int:
    """保存本地化编辑（只写 mod，不覆盖已有文件逻辑由调用方控制）。

    edits: [{"key": str, "value": str, "lang": "simp_chinese"|"english"}]
    返回成功写入条数。
    """
    from localisation_editor_data import (
        default_mod_loc_file, find_mod_file_for_key, upsert_loc_entry,
    )
    written = 0
    for edit in edits:
        key = (edit.get("key") or "").strip()
        lang = edit.get("lang") or "simp_chinese"
        target = find_mod_file_for_key(mod_path, key, lang) or default_mod_loc_file(mod_path, lang)
        if key and upsert_loc_entry(target, key, edit.get("value", ""), lang):
            written += 1
    return written
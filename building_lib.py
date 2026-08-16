"""建筑类型库与国家颜色（common/ 静态资源解析，GUI / 契约测试共用）

- 建筑类型：common/buildings/*.txt（mod 优先，游戏兜底，整树扫描）——
  `key = { ... }` 块；块内存在 `province_max` 视为省级建筑（可锚定地块），
  否则为州级建筑（写在州 buildings 顶层键）
- 国家颜色：common/countries/*.txt 的 `color = { r g b }`——
  支持 0-255 整数与 0-1 浮点两种写法；tag 取文件内 `country_tag = X`，
  无则用文件名（去扩展名）

均无 GUI 依赖、无写入，纯解析。
"""

from __future__ import annotations

import os
import re

from tree_node import parse_pdx_text_to_nodes


def _scan_files(mod_path, hoi4_path, subdir):
    """按 mod -> 游戏 顺序收集 common/<subdir>/*.txt 文件路径（去重）。"""
    out, seen = [], set()
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "common", subdir)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".txt"):
                continue
            fp = os.path.join(d, name)
            key = os.path.normcase(fp)
            if key not in seen:
                seen.add(key)
                out.append(fp)
    return out


def load_building_types(mod_path="", hoi4_path=""):
    """建筑类型列表。

    Returns:
        list[dict]: [{"key": str, "provincial": bool, "buildable": bool,
                      "icon_frame": int|None, "src": "mod"|"game"}, ...]
        src 记录定义来源（mod 与游戏的图标图集帧布局可能不同，
        图标需按来源选择对应 building_icon_strip.dds）
    """
    out = []
    for src, base in (("mod", mod_path), ("game", hoi4_path)):
        if not base:
            continue
        for fp in _scan_files(base, None, "buildings"):
            try:
                with open(fp, "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for node in parse_pdx_text_to_nodes(content):
                if node.node_type != "block":
                    continue
                if node.key == "buildings":
                    # 包裹层：buildings = { infrastructure = {...} ... }
                    for child in node.children:
                        if child.node_type == "block":
                            _collect_building(out, child, src)
                else:
                    # 无包裹层：infrastructure = {...} 直接是顶层
                    _collect_building(out, node, src)
    return out


def _has_province_max(node):
    """递归检测块内 province_max（部分 mod 嵌套在子块中）。"""
    for child in node.children:
        if child.node_type == "value" and child.key == "province_max":
            return True
        if child.node_type == "block" and _has_province_max(child):
            return True
    return False


def _collect_building(out, node, src="game"):
    """收集单个建筑定义（同名合并：mod 优先在前，属性取首个定义）。"""
    provincial = _has_province_max(node)
    icon_frame = _find_icon_frame(node)
    buildable = not _has_flag(node, "is_buildable", "no")
    modifiers = _collect_modifiers(node)
    for existing in out:
        if existing["key"] == node.key:
            # mod 定义优先：不覆盖已有属性（icon_frame 缺失时补全）
            existing["provincial"] = existing["provincial"] or provincial
            if existing.get("icon_frame") is None:
                existing["icon_frame"] = icon_frame
            if not existing.get("modifiers"):
                existing["modifiers"] = modifiers
            return
    out.append({"key": node.key, "provincial": provincial,
                "icon_frame": icon_frame, "buildable": buildable,
                "src": src, "modifiers": modifiers})


def _collect_modifiers(node):
    """递归收集 state_modifiers / country_modifiers 内的修饰键值对。

    Returns:
        list[dict]: [{"key": str, "value": float,
                      "scope": "state"|"country"}, ...]
        结构兼容 `{ modifiers = { key = val } }` 嵌套与直接 `{ key = val }`。
    """
    mods = []

    def walk(n):
        for c in n.children:
            if c.node_type != "block":
                continue
            if c.key in ("state_modifiers", "country_modifiers"):
                scope = "state" if c.key == "state_modifiers" else "country"
                for m in c.children:
                    if m.node_type == "block" and m.key == "modifiers":
                        for kv in m.children:
                            if kv.node_type == "value":
                                try:
                                    mods.append({"key": kv.key,
                                                 "value": float(kv.value),
                                                 "scope": scope})
                                except ValueError:
                                    pass
                    elif m.node_type == "value":
                        try:
                            mods.append({"key": m.key,
                                         "value": float(m.value),
                                         "scope": scope})
                        except ValueError:
                            pass
            else:
                walk(c)

    walk(node)
    return mods


def strip_frame_count(base):
    """解析 base 的 interface/*.gfx 中 GFX_buildings_strip 的 noOfFrames。

    建筑图集帧布局随版本/mod 不同（游戏 1426x46/31 帧、3350890356 mod
    1170x45/26 帧），帧宽 = strip 宽 / noOfFrames。
    找不到定义时回退 0。
    """
    if not base:
        return 0
    d = os.path.join(base, "interface")
    if not os.path.isdir(d):
        return 0
    for name in sorted(os.listdir(d)):
        if not name.lower().endswith(".gfx"):
            continue
        try:
            with open(os.path.join(d, name), "r", encoding="utf-8-sig",
                      errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        m = re.search(
            r'name\s*=\s*"GFX_buildings_strip"[\s\S]*?noOfFrames\s*=\s*(\d+)',
            content)
        if m:
            try:
                return max(1, int(m.group(1)))
            except ValueError:
                return 0
    return 0


def _find_icon_frame(node):
    """递归找 icon_frame（建筑图标在图集 building_icon_strip.dds 的帧号）。"""
    for child in node.children:
        if child.node_type == "value" and child.key == "icon_frame":
            try:
                return int(float(child.value))
            except ValueError:
                return None
        if child.node_type == "block":
            frame = _find_icon_frame(child)
            if frame is not None:
                return frame
    return None


def _has_flag(node, key, value):
    """递归检查是否存在 key = value（如 is_buildable = no）。"""
    for child in node.children:
        if (child.node_type == "value" and child.key == key
                and child.value.strip().lower() == value):
            return True
        if child.node_type == "block" and _has_flag(child, key, value):
            return True
    return False


def load_country_colors(mod_path="", hoi4_path=""):
    """国家标签 -> 颜色 (r, g, b) 0-255。

    tag 取文件内 country_tag（大写）；无则用文件名去扩展名。
    颜色支持 0-255 整数与 0-1 浮点两种写法。
    """
    out = {}
    for fp in _scan_files(mod_path, hoi4_path, "countries"):
        tag = os.path.splitext(os.path.basename(fp))[0]
        color = None
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        for node in parse_pdx_text_to_nodes(content):
            if node.node_type == "value" and node.key == "country_tag":
                tag = node.value.strip().strip('"')
            elif (node.node_type == "block" and node.key == "color"
                    and color is None):
                vals = []
                for c in node.children:
                    if c.node_type == "value":
                        # 裸值在 tree_node 中解析为 key（如 `51 204 51`）
                        raw = (c.key or "").strip()
                        try:
                            vals.append(float(raw))
                        except ValueError:
                            break
                if len(vals) >= 3:
                    color = _normalize_color(vals[0], vals[1], vals[2])
        if color is not None:
            out[tag.upper()] = color
    return out


def _normalize_color(r, g, b):
    """0-255 整数或 0-1 浮点 -> 0-255 整数。"""
    def _n(v):
        if v <= 1.0:
            return max(0, min(255, int(round(v * 255))))
        return max(0, min(255, int(round(v))))
    return (_n(r), _n(g), _n(b))


def country_color_for_tag(tag, colors):
    """按 tag 查国家颜色；未知返回 None。"""
    return colors.get((tag or "").upper())

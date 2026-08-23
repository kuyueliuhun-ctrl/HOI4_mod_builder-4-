# -*- coding: utf-8 -*-
"""三设计器共享槽位/升级数据层（算法层，无 Qt）

供 ship/plane/tank 设计器共用：
- 槽位解析（含引用式槽位、必装、可装类别、顺序）
- module_count_limit / default_modules 解析
- upgrades 定义加载（land/air/naval_upgrades.txt）
- 原型 upgrades 声明读取

本模块不依赖 ship/plane/tank_design，避免循环 import。
"""

from __future__ import annotations

import os
import re

from tree_node import parse_pdx_text_to_nodes


def _field_value(node, key):
    for c in node.children:
        if c.node_type == "value" and c.key == key:
            return c.value
    return None


def _block_children(node, key):
    for c in node.children:
        if c.node_type == "block" and c.key == key:
            return c
    return None


def parse_module_slots(node):
    """解析 module_slots 块节点为有序槽位列表。

    Returns:
        list[dict]: {slot, required, allowed:list[str], alias:str|None}
    """
    out = []
    if node is None:
        return out
    for c in node.children:
        if c.node_type == "value":
            # 引用式槽位：mid_2_custom_slot = mid_1_custom_slot
            out.append({
                "slot": c.key,
                "required": False,
                "allowed": [],
                "alias": c.value.strip() if c.value else None,
            })
        elif c.node_type == "block":
            required = _field_value(c, "required")
            allowed = []
            cat = _block_children(c, "allowed_module_categories")
            if cat is not None:
                for cc in cat.children:
                    if cc.node_type == "value":
                        allowed.append(cc.key)
            out.append({
                "slot": c.key,
                "required": str(required or "").strip().lower() == "yes",
                "allowed": allowed,
                "alias": None,
            })
    return out


def resolve_slots(archetype_slots, variant_override=None):
    """合并 archetype 与变体的槽位列表。

    - variant_override 为 None/空：使用 archetype_slots
    - variant_override 非空：以变体重定义为准
    - 引用式槽位（alias）复制被引用槽位的 required/allowed，保留 alias 标记
    返回 list[dict]：{slot, required, allowed, alias, is_alias}
    """
    if variant_override:
        slots = variant_override
    else:
        slots = archetype_slots or []
    result = []
    lookup = {s["slot"]: s for s in slots if s.get("alias") is None}
    for s in slots:
        item = dict(s)
        item["is_alias"] = bool(s.get("alias"))
        if s.get("alias") and s["alias"] in lookup:
            target = lookup[s["alias"]]
            item["required"] = target.get("required", False)
            item["allowed"] = list(target.get("allowed", []))
        result.append(item)
    return result


def parse_module_count_limits(equipment_node):
    """从装备节点解析 module_count_limit 列表。

    Returns:
        list[dict]: {category, count}
    """
    out = []
    for c in equipment_node.children:
        if c.node_type != "block" or c.key != "module_count_limit":
            continue
        category = _field_value(c, "category") or ""
        count = None
        # 常见写法 count < N：tree_node 可能解析为 value 空键 raw "count < N"
        for cc in c.children:
            if cc.node_type == "value":
                if cc.key == "count":
                    count = _to_int(cc.value)
                elif cc.key == "" and "<" in (cc.value or ""):
                    m = re.search(r"count\s*<\s*(\d+)", cc.value)
                    if m:
                        count = int(m.group(1))
        if category and count is not None:
            out.append({"category": category, "count": count})
    return out


def parse_default_modules(node):
    """解析 default_modules 块节点 → {slot: module_key}。"""
    out = {}
    block = _block_children(node, "default_modules")
    if block is None:
        return out
    for c in block.children:
        if c.node_type == "value":
            out[c.key] = c.value
    return out


def parse_upgrades_decl(node):
    """解析装备节点 upgrades 声明 → list[str]（裸键列表）。"""
    out = []
    block = _block_children(node, "upgrades")
    if block is None:
        return out
    for c in block.children:
        if c.node_type == "value":
            out.append(c.key or c.value)
    return out


_UPGRADE_CACHE = {}


def _iter_blocks(nodes):
    for n in nodes:
        if n.node_type != "block":
            continue
        yield n
        for sub in _iter_blocks(n.children):
            yield sub


def load_upgrade_definitions(hoi4_path="", mod_path=""):
    """加载 common/units/equipment/upgrades/{land,air,naval}_upgrades.txt。

    Returns:
        dict: upgrade_key -> {abbreviation, max_level, cost,
                              level_requirements: {level: str}}
    """
    key = (mod_path or "", hoi4_path or "")
    if key in _UPGRADE_CACHE:
        return _UPGRADE_CACHE[key]
    result = {}
    files = ("land_upgrades.txt", "air_upgrades.txt", "naval_upgrades.txt")
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "common", "units", "equipment", "upgrades")
        if not os.path.isdir(d):
            continue
        for fn in files:
            fp = os.path.join(d, fn)
            if not os.path.isfile(fp):
                continue
            try:
                with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            top_nodes = parse_pdx_text_to_nodes(content)
            # 升级定义通常被顶层 `upgrades = { ... }` 包裹，递归收集真定义块
            for node in _iter_blocks(top_nodes):
                if node.key == "upgrades":
                    continue
                if _field_value(node, "abbreviation") is None \
                        and _field_value(node, "max_level") is None \
                        and _block_children(node, "level_requirements") is None:
                    continue
                info = {
                    "abbreviation": _field_value(node, "abbreviation") or "",
                    "max_level": _to_int(_field_value(node, "max_level")) or 0,
                    "cost": _field_value(node, "cost") or "",
                    "level_requirements": {},
                }
                req = _block_children(node, "level_requirements")
                if req is not None:
                    for cc in req.children:
                        if cc.node_type == "block":
                            lv = _to_int(cc.key)
                            if lv is not None:
                                info["level_requirements"][lv] = cc.to_pdx().strip()
                result[node.key] = info
    _UPGRADE_CACHE[key] = result
    return result


def _to_int(val):
    if val is None:
        return None
    try:
        return int(str(val).strip())
    except Exception:
        return None

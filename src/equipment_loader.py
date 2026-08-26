"""通用装备数据加载器（船体/坦克底盘/飞机机体 + 模块 + 国家设计）。

ship_design / tank_design / plane_design 的 load_* 系列原本高度重复：
扫描 equipment 目录、过滤装备块、构建 info、archetype 继承、统计模块、
解析国家 create_equipment_variant。此处集中实现，三个设计模块只保留
差异参数与薄封装，降低循环复杂度/认知复杂度/嵌套深度并消除重复。
"""

import os
import re

from tree_node import parse_pdx_text_to_nodes

from oob_loader import _block_ranges, _node_field_value, _num
from designer_slots import (
    parse_module_slots, parse_module_count_limits,
    parse_default_modules, parse_upgrades_decl,
)


def _iter_blocks(nodes):
    """递归遍历节点树中的所有块（parse 只返回顶层，容器块需递归）。"""
    for n in nodes:
        if n.node_type != "block":
            continue
        yield n
        for sub in _iter_blocks(n.children):
            yield sub


def _node_block_children(node, key):
    """块节点的直接子块（缺失返回 None）。"""
    for c in node.children:
        if c.node_type == "block" and c.key == key:
            return c
    return None


def _is_equipment_node(node):
    """过滤出真正的装备块（含 abbreviation/is_archetype/module_slots/archetype）。"""
    return not (
        _node_field_value(node, "abbreviation") is None
        and _node_field_value(node, "is_archetype") is None
        and _node_block_children(node, "module_slots") is None
        and _node_field_value(node, "archetype") is None
        and _node_field_value(node, "module_slots") is None
    )


def _iter_equipment_files(base, rel_dir, file_filter):
    """按目录读取匹配文件，产出 (文件名, 文本)。目录/读取异常静默跳过。"""
    d = os.path.join(base, *rel_dir.split("/"))
    if not os.path.isdir(d):
        return
    try:
        names = sorted(os.listdir(d))
    except Exception:
        return
    for fn in names:
        if not file_filter(fn):
            continue
        try:
            with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                      errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        yield fn, content


def _build_equipment_info(node, stat_fields, extra_init=None):
    """单个装备块 → info dict（公共字段 + 槽位 + 默认模块 + 基础属性）。"""
    info = {
        "abbreviation": _node_field_value(node, "abbreviation") or "",
        "year": _num(_node_field_value(node, "year")),
        "parent": _node_field_value(node, "parent") or "",
        "archetype": _node_field_value(node, "archetype") or "",
        "is_archetype": False,
        "archetype_key": "",
        "module_slots": {},
        "module_slots_list": [],
        "module_count_limits": [],
        "upgrades_decl": [],
        "default_modules": {},
        "stats": {},
    }
    if extra_init:
        info.update(extra_init)

    is_arch = _node_field_value(node, "is_archetype")
    if is_arch is not None and str(is_arch).strip().lower() == "yes":
        info["is_archetype"] = True
        info["archetype_key"] = node.key

    slots = _node_block_children(node, "module_slots")
    if slots is not None:
        info["module_slots_list"] = parse_module_slots(slots)
        info["module_slots"] = {
            s["slot"]: {"required": s["required"], "allowed": s["allowed"]}
            for s in info["module_slots_list"]
        }
    else:
        info["module_slots"] = {"_inherit": True}
        info["module_slots_list"] = []

    info["module_count_limits"] = parse_module_count_limits(node)
    info["upgrades_decl"] = parse_upgrades_decl(node)
    defaults = _node_block_children(node, "default_modules")
    if defaults is not None:
        info["default_modules"] = parse_default_modules(node)
        if not info["default_modules"]:
            for c in defaults.children:
                if c.node_type == "value":
                    info["default_modules"][c.key] = c.value

    for f in stat_fields:
        v = _num(_node_field_value(node, f))
        if v is not None:
            info["stats"][f] = v
    return info


def _apply_archetype_inheritance(result, archetypes, extra_inherit=None):
    """变体继承 archetype 的槽位/默认模块/属性（及子类额外字段）。"""
    for key, info in result.items():
        arch_key = info.get("archetype") or info.get("parent") or ""
        arch = archetypes.get(arch_key)
        if arch is None and not info.get("is_archetype"):
            for ak, ai in archetypes.items():
                if key.startswith(ak):
                    arch = ai
                    arch_key = ak
                    break
        if arch is None:
            continue
        if info.get("module_slots") == {"_inherit": True}:
            info["module_slots"] = dict(arch.get("module_slots") or {})
            info["module_slots_list"] = list(
                arch.get("module_slots_list") or [])
            if not info.get("module_count_limits"):
                info["module_count_limits"] = list(
                    arch.get("module_count_limits") or [])
            if not info.get("upgrades_decl"):
                info["upgrades_decl"] = list(
                    arch.get("upgrades_decl") or [])
        if not info.get("is_archetype"):
            info["archetype_key"] = arch_key or info.get("archetype_key")
            for f, v in (arch.get("stats") or {}).items():
                info["stats"].setdefault(f, v)
            if not info.get("default_modules"):
                info["default_modules"] = dict(
                    arch.get("default_modules") or {})
        if extra_inherit is not None:
            extra_inherit(info, arch, arch_key)


def load_equipment_defs(mod_path, hoi4_path, cache, stat_fields,
                        file_filter, extra_init=None, extra_parse=None,
                        extra_inherit=None):
    """加载 equipment 目录下的装备定义（船体/底盘/机体）。"""
    key = (mod_path or "", hoi4_path or "")
    if key in cache:
        return cache[key]
    result = {}
    archetypes = {}
    for base in (hoi4_path, mod_path):
        if not base:
            continue
        for _fn, content in _iter_equipment_files(
                base, "common/units/equipment", file_filter):
            for node in _iter_blocks(parse_pdx_text_to_nodes(content)):
                if not _is_equipment_node(node):
                    continue
                info = _build_equipment_info(node, stat_fields, extra_init)
                if extra_parse is not None:
                    extra_parse(node, info)
                if info["is_archetype"]:
                    archetypes[node.key] = info
                result[node.key] = info
    _apply_archetype_inheritance(result, archetypes, extra_inherit)
    cache[key] = result
    return result


def _parse_stat_block(node, key):
    """解析 add_stats/multiply_stats 子块 → {字段: 数值}。"""
    out = {}
    blk = _node_block_children(node, key)
    if blk is None:
        return out
    for c in blk.children:
        if c.node_type == "value":
            v = _num(c.value)
            if v is not None:
                out[c.key] = v
    return out


def load_equipment_modules(mod_path, hoi4_path, cache, keyword):
    """加载 modules 目录下含指定关键词的模块。"""
    key = (mod_path or "", hoi4_path or "")
    if key in cache:
        return cache[key]
    result = {}
    for base in (hoi4_path, mod_path):
        if not base:
            continue
        for _fn, content in _iter_equipment_files(
                base, "common/units/equipment/modules",
                lambda fn: fn.lower().endswith(".txt")
                and keyword in fn.lower()):
            for node in _iter_blocks(parse_pdx_text_to_nodes(content)):
                if _node_field_value(node, "abbreviation") is None \
                        and _node_field_value(node, "category") is None:
                    continue
                result[node.key] = {
                    "abbreviation": _node_field_value(node, "abbreviation") or "",
                    "category": _node_field_value(node, "category") or "",
                    "add_stats": _parse_stat_block(node, "add_stats"),
                    "multiply_stats": _parse_stat_block(node, "multiply_stats"),
                }
    cache[key] = result
    return result


_TAG_RE = re.compile(r'^\s*([A-Z][A-Z0-9]{1,4})\s*=\s*\{', re.M)


def _tag_of(fn, content):
    """国家 TAG：文件名前缀优先，异常文件名回退内容里第一个 TAG = {。"""
    parts = (fn or "").split()
    first = parts[0].strip() if parts else ""
    if first.lower().endswith(".txt"):
        first = first[:-4]
    if re.fullmatch(r"[A-Z][A-Z0-9]{1,4}", first):
        return first
    for m in _TAG_RE.finditer(content):
        return m.group(1)
    return ""


def _field_re(seg, key):
    """块文本内取值：name = "..." 或 type = 裸标识符。"""
    m = re.search(r'\b' + re.escape(key) + r'\s*=\s*"([^"]*)"', seg)
    if m:
        return m.group(1)
    m = re.search(r'\b' + re.escape(key) + r'\s*=\s*([\w\.\:\-]+)', seg)
    return m.group(1) if m else ""


def _block_map(seg, block_name):
    """块文本内解析 `block_name = { slot = value ... }` → dict。"""
    out = {}
    for k, _d, s, e in _block_ranges(seg):
        if k != block_name:
            continue
        start = seg.find("{", s, e)
        if start < 0:
            break
        body = seg[start + 1:e]
        depth = 0
        cut = len(body)
        for i, ch in enumerate(body):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    cut = i
                    break
        for line in body[:cut].splitlines():
            m = re.match(r'\s*([\w\.\-]+)\s*=\s*([\w\.\-]+)\s*\}?\s*$', line)
            if m:
                out[m.group(1)] = m.group(2)
        break
    return out


def parse_equipment_variants(content, type_filter=None, block_name="upgrades"):
    """通用解析 create_equipment_variant 块（字符级，避免 parse 截断）。

    Args:
        content: 文件原文
        type_filter: 可调用 type -> bool；None 表示全部接收
        block_name: 模块块名（舰艇 upgrades / 飞机 modules）

    Returns:
        dict: {设计名: {"type": ..., "modules": {槽位: 模块}}}
        模块字段名统一为 "modules"（写回时按 block_name 处理）。
    """
    out = {}
    for key, _depth, start, end in _block_ranges(content):
        if key != "create_equipment_variant":
            continue
        seg = content[start:end]
        name = _field_re(seg, "name")
        typ = _field_re(seg, "type")
        if not name or not typ:
            continue
        if type_filter is not None:
            if isinstance(type_filter, (set, list, tuple)):
                if typ not in type_filter and not typ.startswith("ship_hull"):
                    continue
            elif not type_filter(typ):
                continue
        modules = _block_map(seg, block_name)
        if block_name == "upgrades":
            upgrades = dict(modules)
        else:
            upgrades = _block_map(seg, "upgrades")
        parent_raw = _field_re(seg, "parent_version")
        try:
            parent_version = int(parent_raw)
        except (TypeError, ValueError):
            parent_version = parent_raw or 0
        out[name] = {
            "type": typ,
            "modules": modules,
            "upgrades": upgrades,
            "design_team": _field_re(seg, "design_team") or "",
            "parent_version": parent_version,
            "obsolete": _field_re(seg, "obsolete") == "yes",
            "icon": _field_re(seg, "icon") or "",
        }
    return out


def load_equipment_variants(mod_path, hoi4_path, cache, known, type_filter,
                            tag_of=None):
    """加载 history/countries 下的 create_equipment_variant 设计。"""
    key = (mod_path or "", hoi4_path or "")
    if key in cache:
        return cache[key]
    if tag_of is None:
        tag_of = _tag_of
    result = {}
    for base in (hoi4_path, mod_path):
        if not base:
            continue
        for fn, content in _iter_equipment_files(
                base, "history/countries",
                lambda fn: fn.lower().endswith(".txt")):
            tag = tag_of(fn, content)
            if not tag:
                continue
            variants = parse_equipment_variants(
                content, type_filter, block_name="modules")
            if variants:
                result.setdefault(tag, {}).update(variants)
    cache[key] = result
    return result
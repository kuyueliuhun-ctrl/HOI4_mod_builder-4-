"""飞机设计（Plane Designer）数据层

解析/汇总/写回 HOI4 飞机设计：
  - 机体：common/units/equipment/plane_airframes.txt 等 airframe 文件
    （archetype 基础属性 + 变体 module_slots=inherit 继承 + derived_variant_name）
  - 模块：common/units/equipment/modules/00_plane_modules.txt
    （category + add_stats / multiply_stats）
  - 设计：history/countries/*.txt 的 create_equipment_variant
    （name/type/modules；type 为 airframe 键或其派生装备名）
  - 写回：modules 子块级替换 / 块插入 / 块删除 / 块改名（配合原子写）

属性为**基础值估算**（airframe 基础 + 模块 add/multiply 汇总，
未含科技/MIO 修正）。国家文件用字符级 _block_ranges 解析
（parse_pdx_text_to_nodes 在部分大文件会提前截断，如 GER）。
"""

import os
import re

from tree_node import parse_pdx_text_to_nodes
from oob_loader import _block_ranges
from ship_design import (
    _iter_blocks, _num, _node_field_value, _node_block_children,
    parse_equipment_variants, _block_map, _field_re,
    apply_variant_advanced,
)
from designer_slots import (
    parse_module_slots, parse_module_count_limits,
    parse_default_modules, parse_upgrades_decl,
)

# 参与解析的 airframe 文件（文件名含 airframe）
_AIRFRAME_FILES = ("plane_airframes.txt", "single_engine_airframe.txt",
                   "twin_engine_airframe.txt", "quad_engine_airframe.txt",
                   "intercontinental_bomber.txt", "x_plane_airframes.txt")

# airframe 基础/派生属性字段
_AIRFRAME_STAT_FIELDS = (
    "maximum_speed", "air_range", "air_agility", "air_defence", "air_attack",
    "air_ground_attack", "air_bombing", "naval_strike_attack",
    "naval_strike_targetting", "air_superiority", "reliability",
    "supply_consumption", "fuel_consumption", "manpower", "weight",
    "thrust", "build_cost_ic", "convert_cost_ic", "surface_detection",
    "sub_detection", "night_penalty", "mines_planting", "mines_sweeping",
)
# 模块 add/multiply 参与汇总的字段
_PLANE_MODULE_STAT_FIELDS = _AIRFRAME_STAT_FIELDS

# 槽位中文名
SLOT_LABELS = {
    "fixed_main_weapon_slot": "主武器",
    "fixed_auxiliary_weapon_slot_1": "辅助武器 1",
    "fixed_auxiliary_weapon_slot_2": "辅助武器 2",
    "fixed_auxiliary_weapon_slot_3": "辅助武器 3",
    "fixed_auxiliary_weapon_slot_4": "辅助武器 4",
    "engine_type_slot": "引擎",
    "special_type_slot_1": "特殊 1",
    "special_type_slot_2": "特殊 2",
    "special_type_slot_3": "特殊 3",
    "special_type_slot_4": "特殊 4",
    "special_type_slot_5": "特殊 5",
    "special_type_slot_6": "特殊 6",
    "special_type_slot_7": "特殊 7",
    "special_type_slot_8": "特殊 8",
}
# 模块类别中文名
CATEGORY_LABELS = {
    "plane_engine_type": "引擎",
    "twin_plane_engine_type": "双列引擎",
    "plane_special_module_small": "小型特殊",
    "plane_special_module_defense_turret": "自卫炮塔",
    "plane_special_module_electronics": "电子设备",
    "plane_weapon": "武器",
    "fighter_weapon": "战斗机武器",
    "cas_weapon": "对地武器",
    "nav_bomber_weapon": "海军轰炸武器",
    "kamikaze_bomber_weapon": "神风武器",
    "recon_camera": "侦察相机",
    "engine": "引擎",
    "defensive_turret": "防御炮塔",
    "bomb_bay": "炸弹舱",
    "special": "特殊",
    "air_radar": "机载雷达",
    "navigation": "导航",
}

# 显示字段 → 中文名
STAT_LABELS = {
    "maximum_speed": "最大速度",
    "air_range": "航程",
    "supply_consumption": "补给使用",
    "weight": "重量",
    "thrust": "推力",
    "air_defence": "空中防御",
    "air_attack": "对空攻击",
    "air_agility": "机动",
    "air_superiority": "空优",
    "naval_strike_attack": "对海攻击",
    "naval_strike_targetting": "对海瞄准",
    "air_ground_attack": "对地攻击",
    "air_bombing": "战略轰炸",
    "reliability": "可靠性",
    "fuel_consumption": "燃油使用",
    "surface_detection": "对海探测",
    "sub_detection": "对潜探测",
    "night_penalty": "夜间惩罚",
    "mines_planting": "布雷",
    "mines_sweeping": "扫雷",
    "build_cost_ic": "生产花费",
    "convert_cost_ic": "改装花费",
    "manpower": "人力",
}

# 舰型中文名（airframe 键前缀 → 中文）
PLANE_TYPE_LABELS = {
    "small_plane_airframe": "战斗机",
    "small_plane_cas_airframe": "攻击机",
    "cv_small_plane_airframe": "舰载战斗机",
    "cv_small_plane_cas_airframe": "舰载攻击机",
    "medium_plane_airframe": "战术轰炸机",
    "cv_medium_plane_airframe": "舰载轰炸机",
    "large_plane_airframe": "战略轰炸机",
    "naval_bomber_airframe": "海军轰炸机",
    "transport_plane_airframe": "运输机",
    "single_engine_airframe": "单发飞机",
    "twin_engine_airframe": "双发飞机",
    "quad_engine_airframe": "四发飞机",
    "rocket_interceptor_airframe": "火箭截击机",
    "jet_fighter_airframe": "喷气战斗机",
}


# ---------- 缓存 ----------

_AIRFRAMES_CACHE = {}
_PLANE_MODULES_CACHE = {}
_PLANE_VARIANTS_CACHE = {}


def load_plane_airframes(mod_path="", hoi4_path=""):
    """扫描 airframe 文件，返回 {airframe_key: 信息}。

    每个块含：abbreviation/year/parent/archetype/is_archetype/archetype_key/
    module_slots/default_modules/stats/derived_variant_name。
    变体的 module_slots=inherit 与 stats 从 archetype 继承。
    """
    key = (mod_path or "", hoi4_path or "")
    if key in _AIRFRAMES_CACHE:
        return _AIRFRAMES_CACHE[key]
    result = {}
    archetypes = {}
    # 覆盖顺序：先游戏后 mod → mod 覆盖游戏
    for base in (hoi4_path, mod_path):
        if not base:
            continue
        d = os.path.join(base, "common", "units", "equipment")
        if not os.path.isdir(d):
            continue
        try:
            names = sorted(os.listdir(d))
        except Exception:
            continue
        for fn in names:
            if not (fn.lower().endswith(".txt")
                    and (any(fn.lower() == af for af in _AIRFRAME_FILES)
                         or "airframe" in fn.lower())):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for node in _iter_blocks(parse_pdx_text_to_nodes(content)):
                if _node_field_value(node, "abbreviation") is None \
                        and _node_field_value(node, "is_archetype") is None \
                        and _node_block_children(node, "module_slots") is None \
                        and _node_field_value(node, "archetype") is None \
                        and _node_field_value(node, "module_slots") is None:
                    continue
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
                    "derived_variant_name":
                        _node_field_value(node, "derived_variant_name") or "",
                }
                is_arch = _node_field_value(node, "is_archetype")
                if is_arch is not None \
                        and str(is_arch).strip().lower() == "yes":
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
                for f in _AIRFRAME_STAT_FIELDS:
                    v = _num(_node_field_value(node, f))
                    if v is not None:
                        info["stats"][f] = v
                if info["is_archetype"]:
                    archetypes[node.key] = info
                result[node.key] = info
    # 变体继承
    for ak, info in result.items():
        arch_key = info.get("archetype") or info.get("parent") or ""
        arch = archetypes.get(arch_key)
        if arch is None and not info.get("is_archetype"):
            for ak2, ai in archetypes.items():
                if ak.startswith(ak2):
                    arch = ai
                    arch_key = ak2
                    break
        if arch is not None:
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
                    info["default_modules"] = \
                        dict(arch.get("default_modules") or {})
                if not info.get("derived_variant_name"):
                    info["derived_variant_name"] = \
                        arch.get("derived_variant_name") or ""
    _AIRFRAMES_CACHE[key] = result
    return result


def plane_derived_names(airframes):
    """airframe → 派生装备名集合（fighter_equipment_0 等）。"""
    return set(v.get("derived_variant_name") for v in airframes.values()
               if v.get("derived_variant_name"))


def plane_derived_map(airframes):
    """派生装备名 → airframe 键 反查表（UI 用于把 variant.type 映射回机体）。"""
    return {v["derived_variant_name"]: k
            for k, v in airframes.items()
            if v.get("derived_variant_name")}


def load_plane_modules(mod_path="", hoi4_path=""):
    """扫描 00_plane_modules.txt 的飞机模块。"""
    key = (mod_path or "", hoi4_path or "")
    if key in _PLANE_MODULES_CACHE:
        return _PLANE_MODULES_CACHE[key]
    result = {}
    # 覆盖顺序：先游戏后 mod → mod 覆盖游戏
    for base in (hoi4_path, mod_path):
        if not base:
            continue
        d = os.path.join(base, "common", "units", "equipment", "modules")
        if not os.path.isdir(d):
            continue
        try:
            names = sorted(os.listdir(d))
        except Exception:
            continue
        for fn in names:
            if not (fn.lower().endswith(".txt")
                    and "plane" in fn.lower()):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for node in _iter_blocks(parse_pdx_text_to_nodes(content)):
                if _node_field_value(node, "abbreviation") is None \
                        and _node_field_value(node, "category") is None:
                    continue
                add_stats = {}
                mult_stats = {}
                add = _node_block_children(node, "add_stats")
                if add is not None:
                    for c in add.children:
                        if c.node_type == "value":
                            v = _num(c.value)
                            if v is not None:
                                add_stats[c.key] = v
                mult = _node_block_children(node, "multiply_stats")
                if mult is not None:
                    for c in mult.children:
                        if c.node_type == "value":
                            v = _num(c.value)
                            if v is not None:
                                mult_stats[c.key] = v
                result[node.key] = {
                    "abbreviation": _node_field_value(node, "abbreviation") or "",
                    "category": _node_field_value(node, "category") or "",
                    "add_stats": add_stats,
                    "multiply_stats": mult_stats,
                }
    _PLANE_MODULES_CACHE[key] = result
    return result


def load_plane_variants(mod_path="", hoi4_path=""):
    """扫描 history/countries/*.txt 的飞机设计。

    Returns:
        dict: tag -> {设计名: {"type": airframe_key, "modules": {槽位: 模块}}}
        type 过滤：在 airframe 键集合、派生装备名集合，或含 "airframe"。
    """
    key = (mod_path or "", hoi4_path or "")
    if key in _PLANE_VARIANTS_CACHE:
        return _PLANE_VARIANTS_CACHE[key]
    airframes = load_plane_airframes(mod_path, hoi4_path)
    known = set(airframes.keys()) | plane_derived_names(airframes)
    result = {}
    # 覆盖顺序：先游戏后 mod → mod 覆盖游戏
    for base in (hoi4_path, mod_path):
        if not base:
            continue
        d = os.path.join(base, "history", "countries")
        if not os.path.isdir(d):
            continue
        try:
            names = sorted(os.listdir(d))
        except Exception:
            continue
        for fn in names:
            if not fn.lower().endswith(".txt"):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            from ship_design import _tag_of
            tag = _tag_of(fn, content)
            if not tag:
                continue
            variants = parse_equipment_variants(
                content,
                lambda t: t in known or "airframe" in t,
                block_name="modules")
            if variants:
                result.setdefault(tag, {}).update(variants)
    _PLANE_VARIANTS_CACHE[key] = result
    return result


# ---------- 属性汇总（基础值估算） ----------

def plane_design_stats(variant, airframe, modules=None):
    """飞机设计属性估算：airframe 基础 + 模块 add Σ + multiply 累积乘。

    未定义 airframe 时容错为空字典（统计归零，不崩溃）。
    """
    modules = modules or {}
    if airframe is None:
        airframe = {}
    stats = dict(airframe.get("stats") or {})
    slots = variant.get("modules") or {}
    mults = {}
    for _slot, mod_key in slots.items():
        mod = modules.get(mod_key) or {}
        for f, v in (mod.get("add_stats") or {}).items():
            if f in _PLANE_MODULE_STAT_FIELDS:
                stats[f] = stats.get(f, 0.0) + v
        for f, v in (mod.get("multiply_stats") or {}).items():
            if f in _PLANE_MODULE_STAT_FIELDS:
                mults[f] = mults.get(f, 1.0) * (1.0 + v)
    for f, m in mults.items():
        if f in stats and stats[f] is not None:
            stats[f] = stats[f] * m
    stats["cost"] = stats.get("build_cost_ic", 0.0)
    stats["convert_cost"] = stats.get("convert_cost_ic", 0.0)
    slot_defs = airframe.get("module_slots") or {}
    stats["slot_count"] = len(slot_defs)
    stats["empty_slots"] = sum(1 for s in slot_defs
                               if s not in slots and slot_defs[s].get("required"))
    return stats


# ---------- 写回（modules 块级替换，配合原子写） ----------

def _block_items_text(block_name, items, unit="\t\t"):
    """生成 `block_name = { slot = module ... }` 文本（缩进 2 级）。"""
    lines = [unit + block_name + " = {"]
    for slot, mod in items.items():
        lines.append(unit + "\t" + str(slot) + " = " + str(mod))
    lines.append(unit + "}")
    return "\n".join(lines)


def find_variant_block(content, name, type_key=None):
    """定位 create_equipment_variant 块（name + 可选 type 匹配）的字符范围。"""
    for key, _depth, start, end in _block_ranges(content):
        if key != "create_equipment_variant":
            continue
        seg = content[start:end]
        m = re.search(r'name\s*=\s*"([^"]*)"', seg)
        if not (m and m.group(1) == name):
            continue
        if type_key:
            from ship_design import _field_re
            if _field_re(seg, "type") != type_key:
                continue
        return start, end
    return None


def apply_variant_modules(content, name, modules, type_key=None):
    """替换 create_equipment_variant 块的 modules 子块。

    Returns:
        新 content；未找到块返回 None。
    """
    span = find_variant_block(content, name, type_key)
    if span is None:
        return None
    start, end = span
    block = content[start:end]
    new_mod = _block_items_text("modules", modules)
    lines = block.split("\n")
    out_lines = []
    replaced = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("modules = {"):
            depth = 0
            while i < len(lines):
                s = lines[i].strip()
                depth += s.count("{") - s.count("}")
                i += 1
                if depth <= 0:
                    break
            out_lines.append(new_mod)
            replaced = True
            continue
        out_lines.append(line)
        i += 1
    if not replaced:
        new_block = block.rstrip()
        if new_block.endswith("}"):
            new_block = new_block[:-1].rstrip() + "\n" + new_mod + "\n}"
        out_lines = [new_block]
    return content[:start] + "\n".join(out_lines) + content[end:]


def insert_variant(content, tag, variant_name, airframe_key, modules):
    """在 TAG 顶层块内插入 create_equipment_variant（modules 版）。"""
    ranges = [r for r in _block_ranges(content) if r[1] == 0]
    for key, _depth, start, end in ranges:
        if key == tag:
            body = ("\tcreate_equipment_variant = {\n"
                    "\t\tname = \"" + variant_name + "\"\n"
                    "\t\ttype = " + airframe_key + "\n"
                    + _block_items_text("modules", modules, "\t\t") + "\n"
                    "\t}\n")
            return content[:end - 1] + body + content[end - 1:]
    return None


def remove_variant(content, name, type_key=None):
    """删除 create_equipment_variant 块。"""
    span = find_variant_block(content, name, type_key)
    if span is None:
        return None
    start, end = span
    while start > 0 and content[start - 1] in " \t":
        start -= 1
    if start > 0 and content[start - 1] == "\n":
        start -= 1
    return content[:start] + content[end:]


def rename_variant(content, old_name, new_name, type_key=None):
    """重命名 create_equipment_variant 块的 name 字段。"""
    span = find_variant_block(content, old_name, type_key)
    if span is None:
        return None
    start, end = span
    seg = content[start:end]
    new_seg = re.sub(r'name\s*=\s*"' + re.escape(old_name) + r'"',
                     'name = "' + new_name + '"', seg, count=1)
    return content[:start] + new_seg + content[end:]


def plane_cn_name(key):
    """装备/模块中文名（本地化），无中文回退键。"""
    try:
        from gui_translator import get_translator
        cn = get_translator().translate_value(key)
        if cn and cn != key:
            return cn
    except Exception:
        pass
    return key


def plane_type_cn_name(airframe_key):
    """airframe 键 → 中文机型（如 small_plane_airframe_1 → 战斗机 I）。"""
    for prefix, cn in PLANE_TYPE_LABELS.items():
        if airframe_key.startswith(prefix):
            ver = airframe_key[len(prefix):].strip("_")
            if ver.isdigit():
                return cn + " " + {"1": "I", "2": "II", "3": "III",
                                   "4": "IV", "5": "V"}.get(ver, ver)
            return cn
    return airframe_key

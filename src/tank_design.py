"""装甲（坦克）设计（Tank Designer）数据层

解析/汇总/写回 HOI4 坦克设计：
  - 底盘：common/units/equipment/tank_chassis.txt 等 chassis 文件
    （archetype 基础属性 + 变体 module_slots=inherit 继承 + derived_variant_name）
  - 模块：common/units/equipment/modules/00_tank_modules.txt
    （category + add_stats / multiply_stats）
  - 设计：history/countries/*.txt 的 create_equipment_variant
    （name/type/modules；type 为 chassis 键或其派生装备名）
  - 写回：modules 子块级替换 / 块插入 / 块删除 / 块改名（配合原子写）

属性为**基础值估算**（chassis 基础 + 模块 add/multiply 汇总，
未含科技/MIO 修正）。国家文件用字符级 _block_ranges 解析。
"""

import os
import re

from tree_node import parse_pdx_text_to_nodes
from oob_loader import _block_ranges
from ship_design import (
    _iter_blocks, _num, _node_field_value, _node_block_children,
    parse_equipment_variants, apply_variant_advanced,
)
from plane_design import (
    _block_items_text, find_variant_block, apply_variant_modules,
    insert_variant, remove_variant, rename_variant,
)
from designer_slots import (
    parse_module_slots, parse_module_count_limits,
    parse_default_modules, parse_upgrades_decl,
)

# 参与解析的 chassis 文件
_TANK_FILES = (
    "tank_chassis.txt", "tank_light.txt", "tank_medium.txt",
    "tank_heavy.txt", "tank_modern.txt", "tank_super_heavy.txt",
    "tank_amphibious.txt", "x_tank_chassis.txt",
)

# 底盘基础/派生属性字段
_TANK_STAT_FIELDS = (
    "maximum_speed", "reliability", "supply_consumption", "soft_attack",
    "hard_attack", "ap_attack", "armor_value", "hardness", "breakthrough",
    "defense", "air_attack", "fuel_capacity", "fuel_consumption",
    "suppression", "recon", "entrenchment", "weight", "manpower",
    "build_cost_ic", "convert_cost_ic",
)
# 模块 add/multiply 参与汇总的字段
_TANK_MODULE_STAT_FIELDS = _TANK_STAT_FIELDS

# 槽位中文名
SLOT_LABELS = {
    "main_armament_slot": "主炮",
    "secondary_armament_slot": "副武器",
    "turret_type_slot": "炮塔",
    "suspension_type_slot": "悬挂",
    "armor_type_slot": "装甲",
    "engine_type_slot": "引擎",
    "special_type_slot_1": "特殊 1",
    "special_type_slot_2": "特殊 2",
    "special_type_slot_3": "特殊 3",
    "special_type_slot_4": "特殊 4",
    "lc_main_armament_slot": "轻炮主炮",
    "lc_secondary_armament_slot": "轻炮副炮",
}
# 模块类别中文名
CATEGORY_LABELS = {
    "tank_small_main_armament": "小型主炮",
    "tank_medium_main_armament": "中型主炮",
    "tank_light_turret_type": "轻型炮塔",
    "tank_medium_turret_type": "中型炮塔",
    "tank_suspension_type": "悬挂",
    "tank_non_tracked_suspension_type": "非履带悬挂",
    "tank_armor_type": "装甲",
    "tank_engine_type": "引擎",
    "tank_special_module": "特殊模块",
    "tank_radio_module": "电台模块",
    "tank_secondary_turret": "副炮塔",
    "tank_flamethrower": "火焰喷射器",
    "tank_weapon": "坦克武器",
    "tank_turret": "炮塔",
    "tank_suspension": "悬挂",
    "tank_armor": "装甲",
    "tank_engine": "引擎",
    "tank_special": "特殊",
    "tank_anti_air": "防空炮",
}

# 显示字段 → 中文名
STAT_LABELS = {
    "maximum_speed": "最大速度",
    "reliability": "可靠性",
    "supply_consumption": "补给使用",
    "soft_attack": "对人员杀伤",
    "hard_attack": "对装甲杀伤",
    "ap_attack": "穿甲深度",
    "hardness": "装甲率",
    "armor_value": "装甲厚度",
    "breakthrough": "突破",
    "defense": "防御",
    "air_attack": "对空攻击",
    "fuel_capacity": "燃油容量",
    "fuel_consumption": "燃油使用",
    "suppression": "镇压能力",
    "recon": "侦察",
    "entrenchment": "堑壕",
    "build_cost_ic": "生产花费",
    "convert_cost_ic": "改装花费",
    "manpower": "人力",
}

# 底盘中文名（chassis 键前缀 → 中文）
TANK_TYPE_LABELS = {
    "light_tank_chassis": "轻型坦克",
    "medium_tank_chassis": "中型坦克",
    "heavy_tank_chassis": "重型坦克",
    "super_heavy_tank_chassis": "超重型坦克",
    "modern_tank_chassis": "现代坦克",
    "amphibious_tank_chassis": "两栖坦克",
}


# ---------- 缓存 ----------

_TANKS_CACHE = {}
_TANK_MODULES_CACHE = {}
_TANK_VARIANTS_CACHE = {}


def load_tank_chassis(mod_path="", hoi4_path=""):
    """扫描 chassis 文件，返回 {chassis_key: 信息}。"""
    key = (mod_path or "", hoi4_path or "")
    if key in _TANKS_CACHE:
        return _TANKS_CACHE[key]
    result = {}
    archetypes = {}
    for base in (mod_path, hoi4_path):
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
                    and (any(fn.lower() == tf for tf in _TANK_FILES)
                         or "tank" in fn.lower() or "chassis" in fn.lower())):
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
                for f in _TANK_STAT_FIELDS:
                    v = _num(_node_field_value(node, f))
                    if v is not None:
                        info["stats"][f] = v
                if info["is_archetype"]:
                    archetypes[node.key] = info
                result[node.key] = info
    # 变体继承
    for ck, info in result.items():
        arch_key = info.get("archetype") or info.get("parent") or ""
        arch = archetypes.get(arch_key)
        if arch is None and not info.get("is_archetype"):
            for ak2, ai in archetypes.items():
                if ck.startswith(ak2):
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
    _TANKS_CACHE[key] = result
    return result


def tank_derived_names(chassis):
    """chassis → 派生装备名集合（light_tank_equipment_0 等）。"""
    return set(v.get("derived_variant_name") for v in chassis.values()
               if v.get("derived_variant_name"))


def tank_derived_map(chassis):
    """派生装备名 → chassis 键 反查表（UI 用于把 variant.type 映射回底盘）。"""
    return {v["derived_variant_name"]: k
            for k, v in chassis.items()
            if v.get("derived_variant_name")}


def load_tank_modules(mod_path="", hoi4_path=""):
    """扫描 00_tank_modules.txt 的坦克模块。"""
    key = (mod_path or "", hoi4_path or "")
    if key in _TANK_MODULES_CACHE:
        return _TANK_MODULES_CACHE[key]
    result = {}
    for base in (mod_path, hoi4_path):
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
                    and "tank" in fn.lower()):
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
    _TANK_MODULES_CACHE[key] = result
    return result


def load_tank_variants(mod_path="", hoi4_path=""):
    """扫描 history/countries/*.txt 的坦克设计。

    type 过滤：chassis 键集合 ∪ 派生装备名 ∪ 含 "chassis"。
    """
    key = (mod_path or "", hoi4_path or "")
    if key in _TANK_VARIANTS_CACHE:
        return _TANK_VARIANTS_CACHE[key]
    chassis = load_tank_chassis(mod_path, hoi4_path)
    known = set(chassis.keys()) | tank_derived_names(chassis)
    result = {}
    for base in (mod_path, hoi4_path):
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
                lambda t: t in known or "chassis" in t,
                block_name="modules")
            if variants:
                result.setdefault(tag, {}).update(variants)
    _TANK_VARIANTS_CACHE[key] = result
    return result


# ---------- 属性汇总（基础值估算） ----------

def tank_design_stats(variant, chassis, modules=None):
    """坦克设计属性估算：chassis 基础 + 模块 add Σ + multiply 累积乘。"""
    modules = modules or {}
    stats = dict(chassis.get("stats") or {})
    slots = variant.get("modules") or {}
    mults = {}
    for _slot, mod_key in slots.items():
        mod = modules.get(mod_key) or {}
        for f, v in (mod.get("add_stats") or {}).items():
            if f in _TANK_MODULE_STAT_FIELDS:
                stats[f] = stats.get(f, 0.0) + v
        for f, v in (mod.get("multiply_stats") or {}).items():
            if f in _TANK_MODULE_STAT_FIELDS:
                mults[f] = mults.get(f, 1.0) * (1.0 + v)
    for f, m in mults.items():
        if f in stats and stats[f] is not None:
            stats[f] = stats[f] * m
    stats["cost"] = stats.get("build_cost_ic", 0.0)
    stats["convert_cost"] = stats.get("convert_cost_ic", 0.0)
    slot_defs = chassis.get("module_slots") or {}
    stats["slot_count"] = len(slot_defs)
    stats["empty_slots"] = sum(1 for s in slot_defs
                               if s not in slots and slot_defs[s].get("required"))
    return stats


# 写回：复用 plane_design 的 modules 版函数（块级替换逻辑完全一致）
#   apply_variant_modules / insert_variant / remove_variant / rename_variant
#   已在 plane_design 导出，此处直接使用。


def tank_cn_name(key):
    """装备/模块中文名（本地化），无中文回退键。"""
    try:
        from gui_translator import get_translator
        cn = get_translator().translate_value(key)
        if cn and cn != key:
            return cn
    except Exception:
        pass
    return key


def tank_type_cn_name(chassis_key):
    """chassis 键 → 中文车型（如 light_tank_chassis_1 → 轻型坦克 I）。"""
    for prefix, cn in TANK_TYPE_LABELS.items():
        if chassis_key.startswith(prefix):
            ver = chassis_key[len(prefix):].strip("_")
            if ver.isdigit():
                return cn + " " + {"1": "I", "2": "II", "3": "III",
                                   "4": "IV", "5": "V"}.get(ver, ver)
            return cn
    return chassis_key

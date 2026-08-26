"""舰艇设计（Ship Designer）数据层

解析/汇总/写回 HOI4 舰艇设计：
  - 船体：common/units/equipment/ship_hull_*.txt（archetype 基础属性 +
    变体 module_slots 继承）
  - 模块：common/units/equipment/modules/00_ship_modules.txt
    （category + add_stats / multiply_stats）
  - 设计：history/countries/*.txt 的 create_equipment_variant
    （name/type/upgrades；type 含 ship_hull 者为舰艇设计）
  - 写回：upgrades 子块级替换 / 块插入 / 块删除（配合原子写）

属性为**基础值估算**（hull archetype 基础 + 模块 add/multiply 汇总，
未含科技/将领/MIO 修正）。
"""

import re

from oob_loader import _block_ranges, _node_field_value, _num
from equipment_loader import (
    _iter_blocks, _node_block_children, _field_re, _block_map,
    _tag_of, parse_equipment_variants,
    load_equipment_defs, load_equipment_modules, load_equipment_variants,
)


# 船体 archetype 基础属性字段
_HULL_STAT_FIELDS = (
    "lg_armor_piercing", "lg_attack", "hg_armor_piercing", "hg_attack",
    "torpedo_attack", "sub_attack", "anti_air_attack", "armor_value",
    "surface_detection", "sub_detection", "surface_visibility",
    "naval_speed", "reliability", "naval_range", "max_strength",
    "fuel_consumption", "build_cost_ic", "manpower",
    "naval_weather_penalty_factor", "naval_dominance_factor",
    "supply_consumption", "max_organisation", "sub_visibility",
    "hit_profile_mult",
)
# 模块 add_stats/multiply_stats 内参与汇总的字段
_MODULE_STAT_FIELDS = (
    "lg_attack", "lg_armor_piercing", "hg_attack", "hg_armor_piercing",
    "torpedo_attack", "sub_attack", "anti_air_attack", "armor_value",
    "naval_speed", "naval_range", "reliability", "surface_detection",
    "sub_detection", "surface_visibility", "sub_visibility",
    "fuel_consumption", "supply_consumption", "build_cost_ic",
    "max_strength", "manpower", "naval_mine_laying", "naval_mine_sweeping",
    "naval_weather_penalty_factor", "hit_profile_mult",
)
# 槽位中文名（固定槽）
SLOT_LABELS = {
    "fixed_ship_battery_slot": "主炮",
    "fixed_ship_anti_air_slot": "防空",
    "fixed_ship_fire_control_system_slot": "火控",
    "fixed_ship_radar_slot": "雷达",
    "fixed_ship_torpedo_slot": "鱼雷",
    "fixed_ship_engine_slot": "引擎",
    "fixed_ship_secondaries_slot": "副炮",
    "fixed_ship_armor_slot": "装甲",
    "fixed_ship_sonar_slot": "声呐",
    "front_1_custom_slot": "船头自定义 1",
    "front_2_custom_slot": "船头自定义 2",
    "mid_1_custom_slot": "舯部自定义 1",
    "mid_2_custom_slot": "舯部自定义 2",
    "mid_3_custom_slot": "舯部自定义 3",
    "rear_1_custom_slot": "艉部自定义 1",
    "rear_2_custom_slot": "艉部自定义 2",
}
# 模块类别中文名
CATEGORY_LABELS = {
    "ship_light_battery": "轻型炮组",
    "dp_light_battery": "双用途炮",
    "ship_heavy_battery": "重型炮组",
    "ship_anti_air": "防空炮",
    "ship_torpedo": "鱼雷",
    "light_ship_engine": "轻型引擎",
    "heavy_ship_engine": "重型引擎",
    "ship_radar": "雷达",
    "ship_sonar": "声呐",
    "ship_fire_control_system": "火控系统",
    "ship_depth_charge": "深水炸弹",
    "ship_mine_layer": "布雷",
    "ship_mine_warfare": "水雷战",
    "ship_seaplane_tender": "水上飞机",
    "ship_armor": "装甲",
    "ship_carrier_deck": "飞行甲板",
    "ship_carrier_launch_catapult": "弹射器",
    "ship_hangar": "机库",
    "ship_anti_air_dual_purpose": "双用途防空",
}

# 舰型中文名（hull 键前缀 → 中文）
HULL_TYPE_LABELS = {
    "ship_hull_light": "驱逐舰",
    "ship_hull_cruiser": "巡洋舰",
    "ship_hull_heavy": "战列舰",
    "ship_hull_pre_dreadnought": "前无畏舰",
    "ship_hull_super_heavy": "超重型战舰",
    "ship_hull_battlecruiser": "战列巡洋舰",
    "ship_hull_carrier": "航空母舰",
    "ship_hull_escort_carrier": "护航航母",
    "ship_hull_submarine": "潜艇",
    "ship_hull_repair": "维修舰",
    "ship_hull_support": "支援舰",
}


# ---------- 缓存 ----------

_HULLS_CACHE = {}
_MODULES_CACHE = {}
_VARIANTS_CACHE = {}


def _parse_ship_extra(node, info):
    ndf = _num(_node_field_value(node, "naval_dominance_factor"))
    if ndf is not None:
        info["naval_dominance_factor"] = ndf


def load_ship_hulls(mod_path="", hoi4_path=""):
    """扫描 equipment/ship_hull*.txt 的船体定义。

    Returns:
        dict: hull_key -> {abbreviation, year, parent, is_archetype,
              archetype_key, module_slots: {槽位: {required, allowed}},
              default_modules: {槽位: 模块}, stats: {字段: 值},
              naval_dominance_factor}
        变体的 module_slots=inherit 已解析为 archetype 的槽位表；
        stats 仅 archetype 有（变体继承 archetype）。
    """
    return load_equipment_defs(
        mod_path, hoi4_path, _HULLS_CACHE, _HULL_STAT_FIELDS,
        file_filter=lambda fn: fn.lower().startswith("ship_hull")
        and fn.lower().endswith(".txt"),
        extra_init={"naval_dominance_factor": None},
        extra_parse=_parse_ship_extra,
    )


def load_ship_modules(mod_path="", hoi4_path=""):
    """扫描 equipment/modules/ 下含 ship 的模块文件。

    Returns:
        dict: module_key -> {abbreviation, category,
              add_stats: {字段: 值}, multiply_stats: {字段: 值}}
    """
    return load_equipment_modules(mod_path, hoi4_path, _MODULES_CACHE, "ship")


def load_ship_variants(mod_path="", hoi4_path=""):
    """扫描 history/countries/*.txt 的舰艇设计。

    Returns:
        dict: tag -> {设计名: {"type": hull_key, "upgrades": {槽位: 模块}}}
        仅收录 type 在船体键集合中（含 light_cruiser_1 等非 ship_hull_ 前缀）
        或以 ship_hull 开头的设计；mod 覆盖游戏。
    """
    hull_keys = set(load_ship_hulls(mod_path, hoi4_path).keys())
    return load_equipment_variants(
        mod_path, hoi4_path, _VARIANTS_CACHE, hull_keys,
        lambda t: t in hull_keys or t.startswith("ship_hull"),
        tag_of=_tag_of,
    )



# ---------- 属性汇总（基础值估算） ----------

_STAT_LABELS = {
    "naval_speed": "最大速度",
    "naval_range": "最大航程",
    "max_organisation": "组织度",
    "max_strength": "HP",
    "reliability": "可靠性",
    "supply_consumption": "补给使用",
    "manpower": "人力",
    "lg_attack": "轻型火炮攻击",
    "lg_armor_piercing": "轻型穿甲深度",
    "hg_attack": "重型火炮攻击",
    "hg_armor_piercing": "重型穿甲深度",
    "torpedo_attack": "鱼雷攻击",
    "sub_attack": "深水炸弹",
    "armor_value": "装甲厚度",
    "anti_air_attack": "防空",
    "fuel_consumption": "燃油使用",
    "surface_visibility": "水面可见度",
    "surface_detection": "对海探测",
    "sub_visibility": "水下可见度",
    "sub_detection": "对潜探测",
    "naval_mine_laying": "布雷",
    "naval_mine_sweeping": "扫雷",
    "naval_weather_penalty_factor": "天气惩罚",
    "hit_profile_mult": "被弹系数",
    "build_cost_ic": "生产花费",
}


def ship_design_stats(variant, hull, modules=None):
    """舰艇设计属性估算：archetype 基础 + 模块 add Σ + multiply 累积乘。

    Args:
        variant: {"type": hull_key, "upgrades": {槽位: 模块}}
        hull: load_ship_hulls()[hull_key]
        modules: load_ship_modules() 结果

    Returns:
        dict: 统计字段名 -> 值（与 _STAT_LABELS 对应）；含 "cost" 生产花费
        与 "slot_count"/"empty_slots"。
    """
    modules = modules or {}
    stats = dict(hull.get("stats") or {})
    # 统一字段名：parse_equipment_variants 输出 "modules"；旧数据兼容 "upgrades"
    upgrades = variant.get("modules") or variant.get("upgrades") or {}
    mults = {}
    for slot, mod_key in upgrades.items():
        mod = modules.get(mod_key) or {}
        for f, v in (mod.get("add_stats") or {}).items():
            if f in _MODULE_STAT_FIELDS:
                stats[f] = stats.get(f, 0.0) + v
        for f, v in (mod.get("multiply_stats") or {}).items():
            if f in _MODULE_STAT_FIELDS:
                mults[f] = mults.get(f, 1.0) * (1.0 + v)
    for f, m in mults.items():
        if f in stats and stats[f] is not None:
            stats[f] = stats[f] * m
    # build_cost_ic 已在 add 循环计入（hull 基础 + 模块花费）
    stats["cost"] = stats.get("build_cost_ic", 0.0)
    slots = hull.get("module_slots") or {}
    stats["slot_count"] = len(slots)
    stats["empty_slots"] = sum(1 for s in slots
                               if s not in upgrades and slots[s].get("required"))
    return stats


# ---------- 写回（块级替换，配合原子写） ----------

def find_variant_block(content, name, type_key=None):
    """定位 create_equipment_variant 块（name + 可选 type 匹配）的字符范围。

    type_key 非空时要求块内 type 字段完全一致，避免同名舰/机/坦互相写错。
    """
    for key, _depth, start, end in _block_ranges(content):
        if key != "create_equipment_variant":
            continue
        seg = content[start:end]
        m = re.search(r'name\s*=\s*"([^"]*)"', seg)
        if not (m and m.group(1) == name):
            continue
        if type_key:
            typ = _field_re(seg, "type")
            if typ != type_key:
                continue
        return start, end
    return None


def _upgrades_text(upgrades, unit="\t\t"):
    """upgrades 块文本（缩进 2 级 tab，无值/空则返回空块）。"""
    lines = [unit + "upgrades = {"]
    for slot, mod in upgrades.items():
        lines.append(unit + "\t" + str(slot) + " = " + str(mod))
    lines.append(unit + "}")
    return "\n".join(lines)


def _modules_text(modules, unit="\t\t"):
    """modules 块文本（模块槽位）。"""
    lines = [unit + "modules = {"]
    for slot, mod in modules.items():
        lines.append(unit + "\t" + str(slot) + " = " + str(mod))
    lines.append(unit + "}")
    return "\n".join(lines)


def _advanced_field_text(key, value, unit="\t\t"):
    """高级字段单行文本；值等于默认/缺省时返回 None（由调用方移除）。"""
    if key == "design_team":
        if value:
            return unit + "design_team = " + str(value)
        return None
    if key == "parent_version":
        if value not in (None, "", 0) and str(value) != "0":
            return unit + "parent_version = " + str(value)
        return None
    if key == "obsolete":
        if value:
            return unit + "obsolete = yes"
        return None
    if key == "icon":
        if value:
            return unit + 'icon = "' + str(value) + '"'
        return None
    return None


def apply_variant_advanced(content, name, advanced, type_key=None):
    """块级替换 create_equipment_variant 的高级字段。

    支持 design_team / parent_version / obsolete / icon 四个简单字段。
    值为默认值时移除对应行；非默认且缺失时在 type 行后插入；
    其他字段（modules/upgrades/未知字段）原样保留。

    Returns:
        新 content；未找到块返回 None。
    """
    span = find_variant_block(content, name, type_key)
    if span is None:
        return None
    start, end = span
    block = content[start:end]
    lines = block.split("\n")
    for key in ("design_team", "parent_version", "obsolete", "icon"):
        value = advanced.get(key)
        line_text = _advanced_field_text(key, value)
        replaced = False
        for i, line in enumerate(lines):
            if line is None:
                continue
            stripped = line.strip()
            if stripped.startswith(key + " =") and not stripped.startswith(key + " = {"):
                lines[i] = line_text
                replaced = True
                break
        if not replaced and line_text is not None:
            insert_at = None
            for i, line in enumerate(lines):
                if line.strip().startswith("type ="):
                    insert_at = i + 1
                    break
            if insert_at is None:
                insert_at = max(0, len(lines) - 1)
            lines.insert(insert_at, line_text)
    lines = [line for line in lines if line is not None]
    return content[:start] + "\n".join(lines) + content[end:]


def apply_variant_upgrades(content, name, upgrades, type_key=None):
    """替换 create_equipment_variant 块的 upgrades 子块（升级加点）。

    Returns:
        新 content；未找到块返回 None。
    """
    span = find_variant_block(content, name, type_key)
    if span is None:
        return None
    start, end = span
    block = content[start:end]
    new_up = _upgrades_text(upgrades)
    lines = block.split("\n")
    out_lines = []
    replaced = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("upgrades = {"):
            depth = 0
            while i < len(lines):
                s2 = lines[i].strip()
                depth += s2.count("{") - s2.count("}")
                i += 1
                if depth <= 0:
                    break
            out_lines.append(new_up)
            replaced = True
            continue
        out_lines.append(line)
        i += 1
    if not replaced:
        new_block = block.rstrip()
        if new_block.endswith("}"):
            new_block = new_block[:-1].rstrip() + "\n" + new_up + "\n}"
        out_lines = [new_block]
    return content[:start] + "\n".join(out_lines) + content[end:]


def apply_variant_modules(content, name, modules, type_key=None):
    """替换 create_equipment_variant 块的 modules 子块（舰艇模块槽位）。

    Returns:
        新 content；未找到块返回 None。
    """
    span = find_variant_block(content, name, type_key)
    if span is None:
        return None
    start, end = span
    block = content[start:end]
    new_mod = _modules_text(modules)
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
                s2 = lines[i].strip()
                depth += s2.count("{") - s2.count("}")
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


def insert_variant(content, tag, variant_name, hull_key, upgrades):
    """在 TAG 顶层块内插入 create_equipment_variant。

    Returns:
        新 content；找不到 TAG 块返回 None。
    """
    ranges = [r for r in _block_ranges(content) if r[1] == 0]
    for key, _depth, start, end in ranges:
        if key == tag:
            body = ("\tcreate_equipment_variant = {\n"
                    "\t\tname = \"" + variant_name + "\"\n"
                    "\t\ttype = " + hull_key + "\n"
                    + _modules_text(upgrades, "\t\t") + "\n"
                    "\t}\n")
            return content[:end - 1] + body + content[end - 1:]
    return None


def remove_variant(content, name, type_key=None):
    """删除 create_equipment_variant 块。

    Returns:
        新 content；未找到返回 None。
    """
    span = find_variant_block(content, name, type_key)
    if span is None:
        return None
    start, end = span
    # 连带删除整行缩进与换行
    while start > 0 and content[start - 1] in " \t":
        start -= 1
    if start > 0 and content[start - 1] == "\n":
        start -= 1
    return content[:start] + content[end:]


def rename_variant(content, old_name, new_name, type_key=None):
    """重命名 create_equipment_variant 块的 name 字段。

    Returns:
        新 content；未找到块返回 None。
    """
    span = find_variant_block(content, old_name, type_key)
    if span is None:
        return None
    start, end = span
    seg = content[start:end]
    new_seg = re.sub(r'name\s*=\s*"' + re.escape(old_name) + r'"',
                     'name = "' + new_name + '"', seg, count=1)
    return content[:start] + new_seg + content[end:]


def ship_cn_name(key):
    """装备/模块中文名（本地化），无中文回退键。"""
    try:
        from gui_translator import get_translator
        cn = get_translator().translate_value(key)
        if cn and cn != key:
            return cn
    except Exception:
        pass
    return key


def hull_cn_name(hull_key):
    """船体键 → 中文舰型（如 ship_hull_light_1 → 驱逐舰 I）。"""
    for prefix, cn in HULL_TYPE_LABELS.items():
        if hull_key.startswith(prefix):
            ver = hull_key[len(prefix):].strip("_")
            if ver.isdigit():
                return cn + " " + {"1": "I", "2": "II", "3": "III",
                                   "4": "IV", "5": "V"}.get(ver, ver)
            return cn
    return hull_key

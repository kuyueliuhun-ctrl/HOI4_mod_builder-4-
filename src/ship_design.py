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

import os
import re

from tree_node import parse_pdx_text_to_nodes

from oob_loader import _block_ranges, _node_field_value, _num


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


def _iter_blocks(nodes):
    """递归遍历节点树中的所有块（parse 只返回顶层，容器块需递归）。"""
    for n in nodes:
        if n.node_type != "block":
            continue
        yield n
        for sub in _iter_blocks(n.children):
            yield sub


def _parse_slot_block(node):
    """module_slots 子块 → {槽位: {required, allowed: [类别]}}。"""
    out = {}
    for c in node.children:
        if c.node_type != "block":
            continue
        required = _node_field_value(c, "required")
        allowed = []
        cat = None
        for cc in c.children:
            if cc.node_type == "block" and cc.key == "allowed_module_categories":
                cat = cc
        if cat is not None:
            for cc in cat.children:
                if cc.node_type == "value":
                    allowed.append(cc.key)
        out[c.key] = {
            "required": str(required or "").strip().lower() == "yes",
            "allowed": allowed,
        }
    return out


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
    key = (mod_path or "", hoi4_path or "")
    if key in _HULLS_CACHE:
        return _HULLS_CACHE[key]
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
            if not (fn.lower().startswith("ship_hull")
                    and fn.lower().endswith(".txt")):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for node in _iter_blocks(parse_pdx_text_to_nodes(content)):
                # 文件内所有船体块（含 light_cruiser_1 等非 ship_hull_ 前缀键）；
                # 用特征过滤掉 can_be_produced/if/limit 等嵌套容器块
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
                    "default_modules": {},
                    "stats": {},
                    "naval_dominance_factor": None,
                }
                is_arch = _node_field_value(node, "is_archetype")
                if is_arch is not None and str(is_arch).strip().lower() == "yes":
                    info["is_archetype"] = True
                    info["archetype_key"] = node.key
                slots = _node_block_children(node, "module_slots")
                if slots is not None:
                    info["module_slots"] = _parse_slot_block(slots)
                else:
                    info["module_slots"] = {"_inherit": True}
                defaults = _node_block_children(node, "default_modules")
                if defaults is not None:
                    for c in defaults.children:
                        if c.node_type == "value":
                            info["default_modules"][c.key] = c.value
                for f in _HULL_STAT_FIELDS:
                    v = _num(_node_field_value(node, f))
                    if v is not None:
                        info["stats"][f] = v
                ndf = _num(_node_field_value(node, "naval_dominance_factor"))
                if ndf is not None:
                    info["naval_dominance_factor"] = ndf
                if info["is_archetype"]:
                    archetypes[node.key] = info
                result[node.key] = info
    # 变体继承：module_slots=inherit → archetype 槽位表；stats 从 archetype 补
    for hk, info in result.items():
        arch_key = info.get("archetype") or info.get("parent") or ""
        arch = archetypes.get(arch_key)
        if arch is None and not info.get("is_archetype"):
            # 变体自身的 archetype 字段可能未写；按前缀推断
            for ak, ai in archetypes.items():
                if hk.startswith(ak):
                    arch = ai
                    arch_key = ak
                    break
        if arch is not None:
            if info.get("module_slots") == {"_inherit": True}:
                info["module_slots"] = dict(arch.get("module_slots") or {})
            if not info.get("is_archetype"):
                info["archetype_key"] = arch_key or info.get("archetype_key")
                for f, v in (arch.get("stats") or {}).items():
                    info["stats"].setdefault(f, v)
                if not info.get("default_modules"):
                    info["default_modules"] = dict(arch.get("default_modules") or {})
    _HULLS_CACHE[key] = result
    return result


def _node_block_children(node, key):
    """块节点的直接子块（缺失返回 None）。"""
    for c in node.children:
        if c.node_type == "block" and c.key == key:
            return c
    return None


def load_ship_modules(mod_path="", hoi4_path=""):
    """扫描 equipment/modules/ 下含 ship 的模块文件。

    Returns:
        dict: module_key -> {abbreviation, category,
              add_stats: {字段: 值}, multiply_stats: {字段: 值}}
    """
    key = (mod_path or "", hoi4_path or "")
    if key in _MODULES_CACHE:
        return _MODULES_CACHE[key]
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
                    and "ship" in fn.lower()):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for node in _iter_blocks(parse_pdx_text_to_nodes(content)):
                # 只收带 abbreviation/category 的模块块
                # （排除 equipments/add_stats/multiply_stats 等容器块）
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
    _MODULES_CACHE[key] = result
    return result


_TAG_RE = re.compile(r'^\s*([A-Z][A-Z0-9]{1,4})\s*=\s*\{', re.M)


def load_ship_variants(mod_path="", hoi4_path=""):
    """扫描 history/countries/*.txt 的舰艇设计。

    Returns:
        dict: tag -> {设计名: {"type": hull_key, "upgrades": {槽位: 模块}}}
        仅收录 type 在船体键集合中（含 light_cruiser_1 等非 ship_hull_ 前缀）
        或以 ship_hull 开头的设计；mod 覆盖游戏。
    """
    key = (mod_path or "", hoi4_path or "")
    if key in _VARIANTS_CACHE:
        return _VARIANTS_CACHE[key]
    self_hull_keys = set(load_ship_hulls(mod_path, hoi4_path).keys())
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
            tag = _tag_of(fn, content)
            if not tag:
                continue
            variants = parse_equipment_variants(content, self_hull_keys)
            if variants:
                result.setdefault(tag, {}).update(variants)
    _VARIANTS_CACHE[key] = result
    return result


def _tag_of(fn, content):
    """国家 TAG：文件名前缀（"JAP - Japan.txt" → JAP、"AAA.txt" → AAA）优先，
    异常文件名回退内容里第一个 `TAG = {` 顶层块键。"""
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
    m = re.search(r'\b' + re.escape(key) + r'\s*=\s*([\w\.\-]+)', seg)
    return m.group(1) if m else ""


def _block_map(seg, block_name):
    """块文本内解析 `block_name = { slot = value ... }` → dict。

    用 _block_ranges 定位子块，再按行提取 `key = value`。
    兼容单行内联（行尾带闭合 `}`）与多行格式。
    """
    out = {}
    for k, _d, s, e in _block_ranges(seg):
        if k != block_name:
            continue
        sub = seg[s:e]
        for line in sub.splitlines():
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
        out[name] = {"type": typ, "modules": modules}
    return out


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

def find_variant_block(content, name):
    """定位 create_equipment_variant 块（name 匹配）的字符范围。

    Returns:
        (start, end) 或 None
    """
    for key, _depth, start, end in _block_ranges(content):
        if key != "create_equipment_variant":
            continue
        seg = content[start:end]
        m = re.search(r'name\s*=\s*"([^"]*)"', seg)
        if m and m.group(1) == name:
            return start, end
    return None


def _upgrades_text(upgrades, unit="\t\t"):
    """upgrades 块文本（缩进 2 级 tab，无值/空则返回空块）。"""
    lines = [unit + "upgrades = {"]
    for slot, mod in upgrades.items():
        lines.append(unit + "\t" + str(slot) + " = " + str(mod))
    lines.append(unit + "}")
    return "\n".join(lines)


def apply_variant_upgrades(content, name, upgrades):
    """替换 create_equipment_variant 块的 upgrades 子块。

    Args:
        content: 文件原文
        name: 设计名（块内 name 字段匹配）
        upgrades: {槽位: 模块键}

    Returns:
        新 content；未找到块返回 None。
    """
    span = find_variant_block(content, name)
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
            # 跳过旧 upgrades 块（含多行/单行）
            depth = 0
            while i < len(lines):
                s = lines[i].strip()
                depth += s.count("{") - s.count("}")
                i += 1
                if depth <= 0:
                    break
            out_lines.append(new_up)
            replaced = True
            continue
        out_lines.append(line)
        i += 1
    if not replaced:
        # 无 upgrades 块：在块内末尾（闭合 } 前）插入
        new_block = block.rstrip()
        if new_block.endswith("}"):
            new_block = new_block[:-1].rstrip() + "\n" + new_up + "\n}"
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
                    + _upgrades_text(upgrades, "\t\t") + "\n"
                    "\t}\n")
            return content[:end - 1] + body + content[end - 1:]
    return None


def remove_variant(content, name):
    """删除 create_equipment_variant 块。

    Returns:
        新 content；未找到返回 None。
    """
    span = find_variant_block(content, name)
    if span is None:
        return None
    start, end = span
    # 连带删除整行缩进与换行
    while start > 0 and content[start - 1] in " \t":
        start -= 1
    if start > 0 and content[start - 1] == "\n":
        start -= 1
    return content[:start] + content[end:]


def rename_variant(content, old_name, new_name):
    """重命名 create_equipment_variant 块的 name 字段。

    Returns:
        新 content；未找到块返回 None。
    """
    span = find_variant_block(content, old_name)
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

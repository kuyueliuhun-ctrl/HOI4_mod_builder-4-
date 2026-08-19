"""初始部队（OOB）文件数据模型

解析/序列化 history/units/*.txt 中的两类内容：
  - division_template 块：师编制（name/is_locked/regiments/support + 未知字段保留）
  - units 块：部队放置（division = { name/location/division_template/... }）

保存时按块字符范围替换，仅重写被编辑的块，其余文件内容原样保留。
"""

import os
import re

from tree_node import parse_pdx_text_to_nodes


# ---------- 轻量块扫描（与 workbench 相同的字符级定位） ----------

def _blank_pdx(text):
    """注释与引号字符串原地替换为空格（保持字符位置不变）。"""
    chars = list(text)
    n = len(chars)
    in_str = False
    i = 0
    while i < n:
        c = chars[i]
        if in_str:
            if c == '"':
                in_str = False
            chars[i] = ' '
            i += 1
            continue
        if c == '"':
            in_str = True
            chars[i] = ' '
            i += 1
            continue
        if c == '#':
            while i < n and chars[i] != '\n':
                chars[i] = ' '
                i += 1
            continue
        i += 1
    return ''.join(chars)


def _block_ranges(text):
    """返回所有 `key = {` 块的 (key, 深度, start, end)，start/end 为字符位置。

    end 为块闭合 `}` 之后的位置（即其后首个深度 <= 当前深度的块起点）。
    """
    clean = _blank_pdx(text)
    pattern = re.compile(r'(\{|\})|([\w\.\-]+)\s*=\s*\{')
    blocks = []
    depth = 0
    for m in pattern.finditer(clean):
        brace = m.group(1)
        if brace == "{":
            depth += 1
        elif brace == "}":
            depth -= 1
        else:
            blocks.append((m.group(2), depth, m.start()))
            depth += 1
    n = len(blocks)
    ends = [len(text)] * n
    stack = []
    for i in range(n - 1, -1, -1):
        depth = blocks[i][1]
        while stack and blocks[stack[-1]][1] > depth:
            stack.pop()
        if stack:
            ends[i] = blocks[stack[-1]][2]
        stack.append(i)
    return [(blocks[i][0], blocks[i][1], blocks[i][2], ends[i]) for i in range(n)]


# ---------- 数据类 ----------

class DivisionTemplate:
    """师编制模板。"""

    def __init__(self, name="", is_locked=None, regiments=None, support=None,
                 extra_lines=None, modified=False, raw_block=None):
        self.name = name
        self.is_locked = is_locked      # None / True / False
        self.regiments = regiments or []    # [(type, x, y)]
        self.support = support or []        # [(type, x, y)]
        self.extra_lines = extra_lines or []  # 未知字段原始行（保留缩进）
        self.modified = modified        # 是否被编辑过（未编辑的块原样写回）
        self.raw_block = raw_block      # 原始块文本（未编辑时保留注释/格式）

    def to_pdx(self, unit="\t", newline="\n"):
        """序列化为顶层 division_template = {...} 文本。"""
        t = unit
        lines = ["division_template = {",
                 f"{t}name = \"{self.name}\""]
        if self.is_locked is True:
            lines.append(f"{t}is_locked = yes")
        elif self.is_locked is False:
            lines.append(f"{t}is_locked = no")
        if self.regiments:
            lines.append(f"{t}regiments = {{")
            for typ, x, y in self.regiments:
                lines.append(f"{t}{t}{typ} = {{")
                lines.append(f"{t}{t}{t}x = {x}")
                lines.append(f"{t}{t}{t}y = {y}")
                lines.append(f"{t}{t}}}")
            lines.append(f"{t}}}")
        if self.support:
            lines.append(f"{t}support = {{")
            for typ, x, y in self.support:
                lines.append(f"{t}{t}{typ} = {{")
                lines.append(f"{t}{t}{t}x = {x}")
                lines.append(f"{t}{t}{t}y = {y}")
                lines.append(f"{t}{t}}}")
            lines.append(f"{t}}}")
        lines.extend(self.extra_lines)
        lines.append("}")
        return newline.join(lines)


class DivisionPlacement:
    """部队放置条目（units 块中的 division）。"""

    def __init__(self, name="", location=0, division_template="",
                 start_experience_factor=None, extra_lines=None,
                 modified=False, raw_block=None):
        self.name = name
        self.location = location
        self.division_template = division_template
        self.start_experience_factor = start_experience_factor
        self.extra_lines = extra_lines or []
        self.modified = modified
        self.raw_block = raw_block

    def to_pdx(self, unit="\t", newline="\n"):
        t = unit
        lines = [f"{t}division = {{",
                 f"{t}{t}name = \"{self.name}\"",
                 f"{t}{t}location = {self.location}",
                 f"{t}{t}division_template = \"{self.division_template}\""]
        if self.start_experience_factor is not None:
            lines.append(f"{t}{t}start_experience_factor = {self.start_experience_factor}")
        lines.extend(self.extra_lines)
        lines.append(f"{t}}}")
        return newline.join(lines)


# ---------- 解析 ----------

def _node_field_value(node, key):
    """块节点的直接子 value 字段值。"""
    for c in node.children:
        if c.node_type == "value" and c.key == key:
            return c.value
    return None


def _parse_xy_blocks(node):
    """解析 regiments/support 块，返回 [(type, x, y)]。"""
    out = []
    for child in node.children:
        if child.node_type != "block":
            continue
        typ = child.key
        try:
            x = int(_node_field_value(child, "x") or 0)
            y = int(_node_field_value(child, "y") or 0)
        except ValueError:
            continue
        out.append((typ, x, y))
    return out


def _needs_quote(value):
    """值是否为非裸标识符（含空格/引号/特殊字符）→ 需要双引号。"""
    return not re.fullmatch(r'[\w\.\-]+', value or "")


def _unknown_lines(node, indent=1):
    """返回块内未识别字段的重建文本行（缩进深度 = indent 级 tab）。

    Args:
        node: 块节点
        indent: 块内字段的缩进级数（模板=1，division 条目=2）
    """
    unit = "\t" * indent
    lines = []
    for c in node.children:
        known = c.key in ("name", "is_locked", "regiments", "support",
                          "location", "division_template",
                          "start_experience_factor")
        if not known and c.node_type == "value":
            v = c.value
            if _needs_quote(v):
                v = f'"{v}"'
            lines.append(f"{unit}{c.key} = {v}")
        elif not known and c.node_type == "block":
            lines.extend(c.to_pdx(indent).splitlines())
    return lines


def parse_division_templates(content):
    """解析文件中的全部 division_template 块。"""
    templates = []
    for key, _depth, start, end in _block_ranges(content):
        if key != "division_template":
            continue
        block = content[start:end]
        nodes = parse_pdx_text_to_nodes(block)
        if not nodes:
            continue
        node = nodes[0]
        name = _node_field_value(node, "name") or ""
        is_locked = _node_field_value(node, "is_locked")
        if is_locked is not None:
            is_locked = str(is_locked).strip().lower() == "yes"
        regiments, support = [], []
        for c in node.children:
            if c.node_type == "block":
                if c.key == "regiments":
                    regiments = _parse_xy_blocks(c)
                elif c.key == "support":
                    support = _parse_xy_blocks(c)
        tpl = DivisionTemplate(name, is_locked, regiments, support,
                               _unknown_lines(node, indent=1),
                               raw_block=block)
        templates.append(tpl)
    return templates


def parse_units(content):
    """解析文件中的 units 块（部队放置列表）。"""
    placements = []
    for key, _depth, start, end in _block_ranges(content):
        if key != "units":
            continue
        block = content[start:end]
        nodes = parse_pdx_text_to_nodes(block)
        if not nodes:
            continue
        for node in nodes[0].children:
            if node.node_type != "block" or node.key != "division":
                continue
            name = _node_field_value(node, "name") or ""
            try:
                location = int(float(_node_field_value(node, "location") or 0))
            except ValueError:
                location = 0
            div_tpl = _node_field_value(node, "division_template") or ""
            sef = _node_field_value(node, "start_experience_factor")
            if sef is not None:
                try:
                    sef = float(sef)
                except ValueError:
                    sef = None
            placements.append(DivisionPlacement(
                name, location, div_tpl, sef, _unknown_lines(node, indent=2)))
    return placements


# ---------- 兵种目录 ----------

# 营/装备属性字段（基础值估算用；字段缺失时值为 None）
_STAT_FIELDS = (
    "combat_width", "max_strength", "max_organisation", "maximum_speed",
    "manpower", "training_time", "suppression", "weight", "supply_consumption",
    "fuel_consumption", "reliability", "soft_attack", "hard_attack",
    "air_attack", "defense", "breakthrough", "armor", "piercing",
    "initiative", "recon", "org_regain", "experience_loss_factor",
)
_EQUIP_STAT_FIELDS = (
    "soft_attack", "hard_attack", "air_attack", "defense", "breakthrough",
    "armor", "piercing", "reliability",
)
# 地形适应性徽章使用的地形键（与游戏 terrain 块一致）
TERRAIN_KEYS = ("desert", "forest", "hills", "jungle", "marsh",
                "mountain", "plains", "urban")


def _num(v):
    """宽松数值转换：None/非数值 → None，其余 → float。"""
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _node_block(node, key):
    """块节点的直接子块。"""
    if node is None:
        return None
    for c in node.children:
        if c.node_type == "block" and c.key == key:
            return c
    return None


def _parse_need(node):
    """解析 need = { 装备 = 数量 } → {装备: 数量}。"""
    out = {}
    blk = _node_block(node, "need")
    if blk is None:
        return out
    for c in blk.children:
        if c.node_type == "value":
            n = _num(c.value)
            if n is not None:
                out[c.key] = n
    return out


def _parse_terrain(node):
    """解析 terrain 块 → {地形键: movement 修正}（仅收录 TERRAIN_KEYS）。"""
    out = {}
    for c in node.children:
        if c.node_type == "block" and c.key in TERRAIN_KEYS:
            mv = _num(_node_field_value(c, "movement"))
            if mv is not None:
                out[c.key] = mv
    return out


def load_sub_units(mod_path="", hoi4_path=""):
    """扫描 common/units/*.txt 的 sub_units 块。

    Returns:
        dict: type -> {abbreviation, group, support, sprite,
                       combat_width/max_strength/...（属性字段，缺失为 None）,
                       need: {装备: 数量}, terrain: {地形: movement}}
    """
    result = {}
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "common", "units")
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
            for node in parse_pdx_text_to_nodes(content):
                if node.node_type != "block" or node.key != "sub_units":
                    continue
                for sub in node.children:
                    if sub.node_type != "block":
                        continue
                    info = {
                        "abbreviation": _node_field_value(sub, "abbreviation") or "",
                        "sprite": _node_field_value(sub, "sprite") or "",
                        "group": _node_field_value(sub, "group") or "",
                        "support": False,
                        "need": _parse_need(sub),
                        "terrain": _parse_terrain(sub),
                    }
                    reg = _node_field_value(sub, "regimental")
                    if reg is not None:
                        info["support"] = str(reg).strip().lower() == "no"
                    for f in _STAT_FIELDS:
                        info[f] = _num(_node_field_value(sub, f))
                    result[sub.key] = info  # mod 覆盖游戏
    return result


# ---------- 装备攻击属性（战斗数据估算） ----------

_EQUIP_STATS_CACHE = {}


def _collect_equip_blocks(node, result, seen):
    """递归收集装备块（equipments = { ... } 包裹一层，部分 mod 直接顶层）。

    node 自身先作为候选（直接顶层写法），再递归子块。
    """
    info = {}
    for cc in node.children:
        if cc.node_type == "value" and cc.key in _EQUIP_STAT_FIELDS:
            v = _num(cc.value)
            if v is not None:
                info[cc.key] = v
    if info and node.key not in seen:
        seen.add(node.key)
        result[node.key] = info  # 首个变体（通常为基础变体 _0）
    for c in node.children:
        if c.node_type == "block":
            _collect_equip_blocks(c, result, seen)


def load_equipment_stats(mod_path="", hoi4_path=""):
    """扫描 common/units/equipment/*.txt 的装备块（如 infantry_equipment_1）。

    Returns:
        dict: 装备名 -> {soft_attack/hard_attack/.../reliability}（该装备
        定义中的直接字段；不追踪 parent 继承，基础值估算用）。
        按 (mod_path, hoi4_path) 缓存。
    """
    key = (mod_path or "", hoi4_path or "")
    if key in _EQUIP_STATS_CACHE:
        return _EQUIP_STATS_CACHE[key]
    result = {}
    seen = set()
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
            if not fn.lower().endswith(".txt"):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for node in parse_pdx_text_to_nodes(content):
                if node.node_type == "block":
                    _collect_equip_blocks(node, result, seen)
    _EQUIP_STATS_CACHE[key] = result
    return result


# ---------- 师编制属性汇总（基础值估算） ----------

def _main_need(need):
    """need 中数量最大的装备（主武器）。"""
    if not need:
        return None
    return max(need, key=lambda k: need[k])


def _find_equip(equip_stats, need_key):
    """装备类别键 → 装备定义：精确匹配 → `键_0` → 变体号最小的 `键_N`。"""
    if need_key in equip_stats:
        return equip_stats[need_key]
    base = need_key + "_0"
    if base in equip_stats:
        return equip_stats[base]
    best_key = None
    best_num = None
    for k in equip_stats:
        if k.startswith(need_key + "_"):
            try:
                num = int(k.rsplit("_", 1)[1])
            except (ValueError, IndexError):
                continue
            if best_num is None or num < best_num:
                best_num = num
                best_key = k
    if best_key is not None:
        return equip_stats[best_key]
    return None


def division_stats(tpl, sub_units=None, equip_stats=None):
    """按 HOI4 基础规则汇总师编制属性（基础值估算，未含科技/将领修正）。

    Args:
        tpl: DivisionTemplate
        sub_units: load_sub_units() 结果（营属性）
        equip_stats: load_equipment_stats() 结果（装备攻击属性回退）

    Returns:
        dict: width/manpower/speed/org/hp/org_regain/recon/suppression/
              weight/supply/fuel/training/soft/hard/air/defense/breakthrough/
              armor/piercing/initiative/reliability/equipment{装备:数量}/
              terrain{地形:平均movement}/counts{battalions,support}
    """
    sub_units = sub_units or {}
    equip_stats = equip_stats or {}
    stats = {f: 0.0 for f in (
        "width", "hp", "org_regain", "recon", "suppression", "weight",
        "supply", "fuel", "soft", "hard", "air", "defense", "breakthrough",
        "armor", "piercing", "initiative", "reliability_sum")}
    stats["manpower"] = 0
    stats["equipment"] = {}
    stats["terrain"] = {}          # 地形 -> [和, 计数]
    speeds = []
    orgs = []
    rels = []
    trainings = []
    n_items = 0

    items = [(typ, False) for typ, _x, _y in tpl.regiments]
    items += [(typ, True) for typ, _x, _y in tpl.support]

    for typ, _is_sup in items:
        info = sub_units.get(typ) or {}
        n_items += 1
        stats["width"] += info.get("combat_width") or 0
        stats["hp"] += info.get("max_strength") or 0
        stats["manpower"] += int(info.get("manpower") or 0)
        stats["org_regain"] += info.get("org_regain") or 0
        stats["recon"] += info.get("recon") or 0
        stats["suppression"] += info.get("suppression") or 0
        stats["weight"] += info.get("weight") or 0
        stats["supply"] += info.get("supply_consumption") or 0
        stats["fuel"] += info.get("fuel_consumption") or 0
        stats["initiative"] += info.get("initiative") or 0
        spd = info.get("maximum_speed")
        if spd:
            speeds.append(spd)
        org = info.get("max_organisation")
        if org:
            orgs.append(org)
        rel = info.get("reliability")
        if rel is not None:
            rels.append(rel)
        tr = info.get("training_time")
        if tr:
            trainings.append(tr)
        # 攻击类：营字段优先，缺失回退主装备基础值
        main_eq = _find_equip(equip_stats, _main_need(info.get("need") or {})) or {}
        for f, key in (("soft", "soft_attack"), ("hard", "hard_attack"),
                       ("air", "air_attack"), ("defense", "defense"),
                       ("breakthrough", "breakthrough"),
                       ("armor", "armor"), ("piercing", "piercing")):
            v = info.get(key)
            if v is None:
                v = main_eq.get(key) or 0
            stats[f] += v or 0
        # 装备需求聚合
        for eq, cnt in (info.get("need") or {}).items():
            stats["equipment"][eq] = stats["equipment"].get(eq, 0) + cnt
        # 地形 movement 聚合（加权计数，取平均）
        for t, mv in (info.get("terrain") or {}).items():
            acc = stats["terrain"].setdefault(t, [0.0, 0])
            acc[0] += mv
            acc[1] += 1

    stats["speed"] = min(speeds) if speeds else None
    stats["org"] = (sum(orgs) / len(orgs)) if orgs else 0.0
    stats["reliability"] = (sum(rels) / len(rels)) if rels else None
    stats["training"] = max(trainings) if trainings else 0
    stats["terrain"] = {t: (acc[0] / acc[1])
                        for t, acc in stats["terrain"].items()}
    stats["counts"] = {"battalions": len(tpl.regiments),
                       "support": len(tpl.support)}
    stats["items"] = n_items
    stats["reliability_sum"] = stats["reliability"]
    return stats


def detect_oob_kinds(content):
    """检测 OOB 文件内容包含的军种。

    Returns:
        dict: {"army": bool, "navy": bool, "air": bool}
        army = division_template / division；navy = ship / fleet / task_force；
        air = air_wings / air_wing。
    """
    kinds = {"army": False, "navy": False, "air": False}
    for key, _depth, _start, _end in _block_ranges(content):
        if key in ("division_template", "division"):
            kinds["army"] = True
        elif key in ("ship", "fleet", "task_force"):
            kinds["navy"] = True
        elif key in ("air_wings", "air_wing"):
            kinds["air"] = True
    return kinds


# OOB 专用设计器已覆盖的顶层块键（其余顶层块视为“其他内容”）
OOB_COVERED_TOP_KEYS = {
    "division_template", "units", "Units",
    "air_wings", "air_wing",
    "division", "ship", "fleet", "task_force",
}


def detect_oob_other_content(content):
    """检测 OOB 文件中未被专用设计器覆盖的顶层块键。

    例如 `instant_effect`、`add_equipment_to_stockpile`、
    `create_colonial_division_template` 等，均视为“其他内容”。

    Returns:
        list[str]: 未覆盖的顶层块键（去重、排序）；无则返回 []。
    """
    blocks = _block_ranges(content)
    if not blocks:
        return []
    min_depth = min(b[1] for b in blocks)
    keys = {key for key, depth, _s, _e in blocks
            if depth == min_depth and key not in OOB_COVERED_TOP_KEYS}
    return sorted(keys)


# ---------- 文件级管理 ----------

# 包含 load_oob 引用的常见目录（扫描顺序）
_LOAD_OOB_DIRS = (
    "common/scripted_effects",
    "common/decisions",
    "history/countries",
    "events",
)


def find_oob_country(mod_path, file_path):
    """定位初始部队文件对应的国家标签。

    TFR 等 mod 通过 `TAG = { ... load_oob = "文件名" }` 加载部队，
    因此扫描 mod 中引用该文件名的 load_oob，取包含该引用的最内层
    `key = {` 顶层块键名作为国家标签。

    Returns:
        str: 国家标签（大写），未找到返回 ""
    """
    base = os.path.splitext(os.path.basename(file_path))[0]
    if not mod_path or not os.path.isdir(mod_path):
        return ""
    pattern = re.compile(r'load_oob\s*=\s*"([^"]+)"')
    for rel in _LOAD_OOB_DIRS:
        d = os.path.join(mod_path, rel.replace("/", os.sep))
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
            for m in pattern.finditer(content):
                if m.group(1) != base:
                    continue
                tag = _enclosing_top_block_key(content, m.start())
                if tag:
                    return tag.upper()
    # 兜底：文件名前缀推断（APA_2020.txt -> APA）
    m = re.match(r'^([A-Z]{2,4})[_\d]', os.path.basename(file_path))
    if m:
        return m.group(1)
    return ""


def _block_close_pos(clean, brace_start):
    """从 `{` 位置精确配对到对应 `}` 的位置（基于去注释/引号文本）。"""
    depth = 0
    for i in range(brace_start, len(clean)):
        ch = clean[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
    return len(clean) - 1


def _enclosing_top_block_key(content, pos):
    """返回包含字符位置 pos 的最内层 `key = {` 块中、国家格式（2-4 大写字母）的键名。

    国家块可能嵌套在 effect 块内（如 USA_civil_war_outbreak_effect = { APA = {...} }），
    因此沿块树从外向内递归，第一个 TAG 格式的键即为国家标签。
    """
    clean = _blank_pdx(content)
    tag_pat = re.compile(r'^[A-Z]{2,4}$')
    blocks = _block_ranges(content)
    if not blocks:
        return ""
    top_depth = min(b[1] for b in blocks)
    tops = [b for b in blocks if b[1] == top_depth]

    def _search(s, e, depth):
        subs = [b for b in blocks
                if b[1] == depth + 1 and s < b[2] < e]
        for k, _d, bs, _approx_end in subs:
            be = _block_close_pos(clean, content.find('{', bs))
            if bs <= pos <= be:
                if tag_pat.match(k):
                    return k
                return _search(bs, be, depth + 1)
        return None

    for k, _d, s, _e in tops:
        be = _block_close_pos(clean, content.find('{', s))
        if s <= pos <= be:
            if tag_pat.match(k):
                return k
            hit = _search(s, be, top_depth)
            if hit:
                return hit
    return ""


class OobFile:
    """初始部队文件的加载与保存。"""

    def __init__(self, file_path):
        self.file_path = file_path
        # newline="" 保留原始换行（\r\n），否则读入时被转换为 \n，写回会丢失 CRLF
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            self.content = f.read()
        # 换行风格检测
        self.newline = "\r\n" if "\r\n" in self.content else "\n"
        self.templates = parse_division_templates(self.content)
        self.placements = parse_units(self.content)
        self.dirty = False
        # units 块原始文本与修改标记（未修改时原样写回，保留注释/格式）
        self._units_raw = ""
        self._units_modified = False
        for key, _depth, start, end in _block_ranges(self.content):
            if key == "units":
                self._units_raw = self.content[start:end]
                break

    # ---------- 模板 ----------

    def template_names(self):
        return [t.name for t in self.templates]

    def add_template(self, tpl):
        self.templates.append(tpl)
        self.dirty = True

    def remove_template(self, name):
        for i, t in enumerate(self.templates):
            if t.name == name:
                del self.templates[i]
                self.dirty = True
                return True
        return False

    def find_template(self, name):
        for t in self.templates:
            if t.name == name:
                return t
        return None

    def placements_for_template(self, name):
        return [p for p in self.placements if p.division_template == name]

    def mark_template_modified(self, tpl):
        """标记模板已被编辑（保存时重新序列化该块）。"""
        if tpl is not None:
            tpl.modified = True
        self.dirty = True

    # ---------- 放置 ----------

    def add_placement(self, placement):
        self.placements.append(placement)
        self._units_modified = True
        self.dirty = True

    def remove_placement(self, placement):
        if placement in self.placements:
            self.placements.remove(placement)
            self._units_modified = True
            self.dirty = True
            return True
        return False

    def mark_units_modified(self):
        """标记部队放置已被编辑（重命名等）。"""
        self._units_modified = True
        self.dirty = True

    # ---------- 保存 ----------

    def _indent_unit(self):
        """检测文件缩进单位（tab 或空格串）。"""
        unit = "\t"
        for line in self.content.splitlines():
            if not line.strip():
                continue
            m = re.match(r'^([ \t]+)', line)
            if m:
                indent = m.group(1)
                if indent.startswith("\t"):
                    return "\t"
                return indent
            break
        return unit

    def _trim_trailing_ws(self, text):
        """去掉编辑块在原文中紧随其后的空行/空白（避免替换后残留空行）。"""
        return re.sub(r'[ \t]*\n(?=\s*\n|$)', '\n', text, flags=re.M) if text else ""

    def save(self):
        """重写文件：替换被编辑的块，新增/删除对应块。"""
        content = self.content
        newline = self.newline
        unit = self._indent_unit()
        blocks = _block_ranges(content)

        existing = []   # 已存在的 division_template 块 (start, end)
        units_block = None
        for key, _depth, start, end in blocks:
            if key == "division_template":
                existing.append((start, end))
            elif key == "units":
                units_block = (start, end)
        existing.sort()

        # 按块内 name 字段匹配模板对象（块顺序可能与列表顺序不一致）
        used = set()
        pos_map = {}
        for start, end in existing:
            block_text = content[start:end]
            for t in self.templates:
                if id(t) in used:
                    continue
                if f'name = "{t.name}"' in block_text:
                    pos_map[start] = (t, end)
                    used.add(id(t))
                    break

        edits = []
        for start, end in existing:
            if start in pos_map:
                tpl, end_pos = pos_map[start]
                if tpl.modified or not tpl.raw_block:
                    text = tpl.to_pdx(unit, newline)
                else:
                    text = tpl.raw_block  # 未编辑：原样保留（注释/格式）
                edits.append((start, end_pos, text))
            else:
                edits.append((start, end, ""))  # 模板已被删除
        # 新增模板（文件内无对应块）
        appended = [t.to_pdx(unit, newline) for t in self.templates
                    if id(t) not in used]

        # units 块：重写 / 原样保留 / 移除 / 新增
        if units_block and not self._units_modified and self._units_raw:
            pass  # 未编辑：原样保留
        else:
            units_text = ""
            if self.placements:
                lines = ["units = {"]
                for p in self.placements:
                    lines.append(p.to_pdx(unit, newline))
                lines.append("}")
                units_text = newline.join(lines)
            if units_block:
                edits.append((units_block[0], units_block[1], units_text))
            elif self.placements:
                appended.append(units_text)

        # 应用编辑（从后往前，避免偏移）
        for start, end, text in sorted(edits, reverse=True):
            content = content[:start] + text + content[end:]

        # 追加新块（模板/units）
        if appended:
            block = newline.join(appended)
            if not content.endswith(newline):
                content += newline
            content = content.rstrip() + newline + newline + block + newline

        from write_utils import atomic_write_text
        atomic_write_text(self.file_path, content)
        self.content = content
        self.dirty = False
        return True

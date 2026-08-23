"""初始部队（OOB）文件数据模型

解析/序列化 history/units/*.txt 中的两类内容：
  - division_template 块：师编制（name/is_locked/regiments/support + 未知字段保留）
  - units 块：部队放置（division = { name/location/division_template/... }）

保存时按块字符范围替换，仅重写被编辑的块，其余文件内容原样保留。
"""

import os
import re

from tree_node import parse_pdx_text_to_nodes
from oob_stats import (
    _STAT_FIELDS,
    _SUB_KNOWN_SCALARS,
    _node_field_value,
    _num,
    _parse_need,
    _parse_terrain,
)


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
# 地形适应性徽章使用的地形键（与游戏 terrain 块一致）


def load_sub_units(mod_path="", hoi4_path=""):
    """扫描 common/units/*.txt 的 sub_units 块。

    Returns:
        dict: type -> {abbreviation, parent, group, support, sprite,
                       combat_width/max_strength/...（属性字段，缺失为 None）,
                       need: {装备: 数量},
                       terrain: {地形: movement},
                       terrain_full: {地形: {"movement","attack","defence"}},
                       others: {未列入属性表的其他标量字段: 原始值},
                       src: 定义源文件路径}
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
            fp = os.path.join(d, fn)
            try:
                with open(fp, "r", encoding="utf-8-sig",
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
                    terrain_full = _parse_terrain(sub)
                    info = {
                        "abbreviation": _node_field_value(sub, "abbreviation") or "",
                        "sprite": _node_field_value(sub, "sprite") or "",
                        "parent": _node_field_value(sub, "parent") or "",
                        "group": _node_field_value(sub, "group") or "",
                        "support": False,
                        "need": _parse_need(sub),
                        "terrain": {k: v["movement"]
                                    for k, v in terrain_full.items()
                                    if v.get("movement") is not None},
                        "terrain_full": terrain_full,
                        "others": {},
                        "src": fp,
                    }
                    reg = _node_field_value(sub, "regimental")
                    if reg is not None:
                        info["support"] = str(reg).strip().lower() == "no"
                    for f in _STAT_FIELDS:
                        info[f] = _num(_node_field_value(sub, f))
                    # 未列入表单的标量字段进入 others（保留未知键）
                    for c in sub.children:
                        if c.node_type == "value" and c.key not in _SUB_KNOWN_SCALARS:
                            info["others"][c.key] = str(c.value).strip()
                    result[sub.key] = info  # mod 覆盖游戏
    return result


# ---------- 装备攻击属性（战斗数据估算） ----------



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
    # 兜底：文件名前缀推断（APA_2020.txt -> APA；大小写放宽）
    m = re.match(r'^([A-Za-z]{2,4})[_\d]', os.path.basename(file_path))
    if m:
        return m.group(1).upper()
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
    tag_pat = re.compile(r'^[A-Za-z]{2,4}$')
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
        # division_names_group 块（组 id -> icon/order/is_name/generic/name…）
        self.names_groups = load_names_groups(self.content)
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

    # ---------- 命名组 ----------

    def names_group_ids(self):
        return sorted(self.names_groups)

    def set_names_group(self, group_id, fields):
        """更新 OobFile 内的命名组并标记 dirty（仅内存，保存时写回）。"""
        self.content = save_names_group(self.content, group_id, fields)
        self.names_groups = load_names_groups(self.content)
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


def _find_sub_unit_file(mod_path, hoi4_path, unit_id):
    """在 common/units/**/*.txt 中定位 unit_id 定义文件。"""
    for base in (mod_path, hoi4_path):
        d = os.path.join(base or '', 'common', 'units')
        if not os.path.isdir(d):
            continue
        for dp, _dirs, names in os.walk(d):
            for name in sorted(names):
                if not name.lower().endswith('.txt'):
                    continue
                fp = os.path.join(dp, name)
                try:
                    with open(fp, 'r', encoding='utf-8-sig', errors='ignore') as f:
                        content = f.read()
                except Exception:
                    continue
                if _find_block(content, unit_id) is not None:
                    return fp, content
    return None, None


def _find_block(content, key):
    """返回任意深度第一个 key 块 (start,end)。"""
    for k, _d, start, end in _block_ranges(content):
        if k == key:
            return start, end
    return None


def _format_scalar_value(value):
    """把 UI/参数值格式化为 PDX 标量文本（数值/裸标识符不引号，特殊串加引号）。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return repr(value) if isinstance(value, int) else ("%g" % value)
    text = str(value).strip()
    if text == "":
        return '""'
    if re.fullmatch(r'[+-]?(\d+(\.\d*)?|\.\d+)', text):
        return text
    return _quote_if_needed(text)


def _replace_scalar(block, key, value):
    """在 sub_unit 块内替换/插入一个标量字段，返回新块文本。"""
    raw = _format_scalar_value(value)
    if raw is None:
        return block
    pat = re.compile(r'(\b' + re.escape(key) + r'\s*=\s*)[^\n#]+')
    m = pat.search(block)
    if m:
        return block[:m.start()] + m.group(1) + raw + block[m.end():]
    # 插入到 sub_unit 块的闭合 } 前（避免误入内层 need 等块）
    return _insert_at_outer_close(
        block, "%s = %s" % (key, raw))


def _render_block_lines(key, items):
    """把键值/子项渲染为多行块文本（含 key = {...}）。"""
    lines = ["%s = {" % key]
    for k, v in items:
        raw = _format_scalar_value(v)
        if raw is not None:
            lines.append("\t%s = %s" % (k, raw))
    lines.append("}")
    return "\n".join(lines)


def _matching_brace(text, open_index):
    """在去注释/字符串后的文本中，从 open_index 配对到闭合 `}` 的位置。"""
    clean = _blank_pdx(text)
    depth = 0
    for i in range(open_index, len(clean)):
        ch = clean[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _outer_close(block):
    """sub_unit 块文本的最外层闭合 `}` 位置。"""
    idx = block.find('{')
    if idx < 0:
        return -1
    return _matching_brace(block, idx)


def _insert_at_outer_close(block, text):
    """把 text 插入 sub_unit 块最外层闭合 `}` 前，保留缩进风格。"""
    close = _outer_close(block)
    if close < 0:
        return block
    line_start = block.rfind('\n', 0, close)
    if line_start < 0:
        return block[:close] + text + block[close:]
    indent = block[line_start + 1:close]
    prefix = block[:line_start + 1]
    suffix = block[line_start + 1:]
    return prefix + indent + text + '\n' + suffix


def _replace_or_insert_sub_block(block, key, new_block_lines):
    """在 sub_unit 块内替换/插入一个子块；返回 (新块文本, 是否替换)。"""
    pattern = re.compile(r'\b' + re.escape(key) + r'\s*=\s*\{')
    m = pattern.search(block)
    if not m:
        # 不存在：插入到 sub_unit 块闭合 } 前
        return _insert_at_outer_close(block, new_block_lines), False
    # 从该处配对到闭合括号
    close = _matching_brace(block, m.end() - 1)
    if close < 0:
        return block, False
    return block[:m.start()] + new_block_lines + block[close + 1:], True


def _replace_terrain_entry(block, terrain_key, values):
    """替换/插入/删除一个地形子块（forest = {...}）。

    values: {"movement","attack","defence"}；全为空/None 时删除该地形块。
    """
    items = []
    for k in ("movement", "attack", "defence"):
        v = (values or {}).get(k)
        raw = _format_scalar_value(v)
        if raw not in (None, '""'):
            items.append((k, v))
    new_lines = _render_block_lines(terrain_key, items)
    pattern = re.compile(r'\b' + re.escape(terrain_key) + r'\s*=\s*\{')
    m = pattern.search(block)
    if not m:
        if not items:
            return block
        return _insert_at_outer_close(block, new_lines)
    close = _matching_brace(block, m.end() - 1)
    if close < 0:
        return block
    if not items:
        # 删除整块及可能的前置空白
        segment = block[m.start():close + 1]
        return block.replace(segment, "", 1)
    return block[:m.start()] + new_lines + block[close + 1:]


def save_sub_unit(mod_path, hoi4_path, unit_id, fields=None,
                  need=None, terrain=None, stats=None, others=None):
    """保存兵种（sub_unit）基础字段/need/terrain/属性/其他字段。

    fields: {字段: 字符串/数值} 标量（基本信息 group/parent/sprite 等）
    need: {装备: 数量}
    terrain: {地形: {"movement","attack","defence"}}
    stats: {22 属性字段: 数值/字符串}
    others: {其他标量字段: 字符串/数值}（未覆盖键，读写完整保留）
    """
    from state_build_ops import ensure_file_in_mod
    from write_utils import atomic_write_text
    fp, content = _find_sub_unit_file(mod_path, hoi4_path, unit_id)
    if fp is None:
        return None
    if not os.path.normcase(fp).startswith(os.path.normcase(mod_path or '')):
        rel = os.path.relpath(fp, hoi4_path).replace('\\', '/')
        fp, _ = ensure_file_in_mod(mod_path, hoi4_path, rel)
        with open(fp, 'r', encoding='utf-8-sig', errors='ignore') as f:
            content = f.read()
    span = _find_block(content, unit_id)
    if span is None:
        return None
    start, end = span
    block = content[start:end]

    # 合并所有标量更新：fields 优先（stat/others 同键不冲突）
    scalar_updates = {}
    for dct in (others, stats, fields):
        for k, v in (dct or {}).items():
            if v is not None:
                scalar_updates[k] = v
    for k, v in scalar_updates.items():
        block = _replace_scalar(block, k, v)

    if need is not None:
        need_lines = _render_block_lines("need", sorted(need.items()))
        block, _replaced = _replace_or_insert_sub_block(block, "need", need_lines)

    if terrain is not None:
        for terrain_key, values in terrain.items():
            block = _replace_terrain_entry(block, terrain_key, values)

    content = content[:start] + block + content[end:]
    atomic_write_text(fp, content)
    _clear_oob_caches()
    return fp


def _clear_oob_caches():
    # 兵种目前不缓存；装备统计有模块级缓存，写兵种后一并清理避免旧值残留
    cache = globals().get('_EQUIP_STATS_CACHE')
    if cache is not None:
        cache.clear()


# ---------- division_names_group（命名组） ----------

def _quote_if_needed(value):
    """数值/裸标识符原样；含空格或引号需求时加双引号。"""
    value = str(value).strip()
    if not value:
        return '""'
    if value.startswith('"') and value.endswith('"'):
        return value
    if re.match(r'^[A-Za-z_][\w\.\-]*$', value):
        return value
    return '"%s"' % value


def _parse_names_group(seg):
    """解析单个命名组块文本 → {字段: 值, blocks: {子块键: 原始文本}}。"""
    info = {"blocks": {}}
    block_map = {}
    for k, depth, s2, e2 in _block_ranges(seg):
        if depth == 1:
            block_map.setdefault(k, (s2, e2))
    for k, (s2, e2) in block_map.items():
        info["blocks"][k] = seg[s2:e2]
    try:
        nodes = parse_pdx_text_to_nodes(seg)
    except Exception:
        nodes = []
    if nodes:
        node = nodes[0]
        for c in node.children:
            if c.node_type == "value" and c.key not in block_map:
                info[c.key] = c.value
    return info


def load_names_groups(content):
    """解析 OOB 文件顶层 division_names_group 块。

    Returns:
        dict: {group_id: {"icon":..., "order":..., "is_name":...,
                          "generic":..., "name":..., "blocks": {...}}}
    """
    outer = None
    for key, depth, start, end in _block_ranges(content):
        if key == "division_names_group" and depth == 0:
            outer = (start, end)
            break
    if outer is None:
        return {}
    start, end = outer
    outer_block = content[start:end]
    groups = {}
    for key, depth, s2, e2 in _block_ranges(outer_block):
        if depth == 1:
            groups[key] = _parse_names_group(outer_block[s2:e2])
    return groups


def _render_sub_block_raw(sub_raw, indent):
    """把原始子块文本用树节点重新序列化到指定缩进，保留嵌套结构。"""
    try:
        nodes = parse_pdx_text_to_nodes(sub_raw or "")
        if nodes and nodes[0].node_type == "block":
            return nodes[0].to_pdx(indent)
    except Exception:
        pass
    # 兜底：无法解析时按行加缩进
    out = []
    for ln in (sub_raw or "").splitlines():
        if ln.strip():
            out.append("\t" * indent + ln.strip())
    return "\n".join(out)


def _render_names_group(group_id, fields):
    """序列化单个命名组块文本。

    若某字段同时存在 blocks（如 name = {…}），优先用块形式，避免重复输出。
    """
    blocks = fields.get("blocks") or {}
    lines = ["\t%s = {" % group_id]
    for key in ("icon", "order", "is_name", "generic", "name"):
        if key not in fields or key in blocks:
            continue
        value = fields[key]
        if key == "name":
            value = _quote_if_needed(value)
        else:
            value = str(value).strip()
        lines.append("\t\t%s = %s" % (key, value))
    # 未知/结构块（name = {…} 等）重新序列化，块级保留未编辑项
    for sub_key, sub_raw in blocks.items():
        rendered = _render_sub_block_raw(sub_raw, 2)
        if rendered:
            lines.append(rendered)
    lines.append("\t}")
    return "\n".join(lines)


def save_names_group(content, group_id, fields):
    """在 OOB 文件内容中新增/替换 division_names_group 内的命名组。

    Returns:
        str: 新 content；未找到/无法写入时返回原 content。
    """
    group_id = str(group_id).strip()
    if not group_id:
        return content
    new_group = _render_names_group(group_id, fields)
    outer = None
    for key, depth, start, end in _block_ranges(content):
        if key == "division_names_group" and depth == 0:
            outer = (start, end)
            break
    if outer is None:
        # 新建顶层块
        if content.rstrip():
            return content.rstrip() + "\n\ndivision_names_group = {\n" + new_group + "\n}\n"
        return "division_names_group = {\n" + new_group + "\n}\n"
    start, end = outer
    outer_block = content[start:end]
    # 查找已有组块
    group_range = None
    for key, depth, s2, e2 in _block_ranges(outer_block):
        if depth == 1 and key == group_id:
            group_range = (s2, e2)
            break
    if group_range is not None:
        gs, ge = group_range
        # 替换整行（含组块前缩进），避免 new_group 自带缩进造成双重缩进
        line_start = outer_block.rfind("\n", 0, gs) + 1
        return content[:start + line_start] + new_group + content[start + ge:]
    # 不存在：在 division_names_group 闭合 } 前插入
    # 找到外层块最后闭合大括号位置
    close_idx = outer_block.rfind("}")
    if close_idx == -1:
        return content
    inserted = outer_block[:close_idx] + "\n" + new_group + "\n" + outer_block[close_idx:]
    return content[:start] + inserted + content[end:]


# F5 兼容：统计/装备层已拆至 oob_stats，保持旧导入路径可用
from oob_stats import (  # noqa: E402,F401,F403
    _collect_equip_blocks,
    _find_equip,
    _main_need,
    division_stats,
    load_equipment_stats,
)

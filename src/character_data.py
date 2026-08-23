"""角色（Character）数据层（算法层）

解析 common/characters/*.txt 中的角色块。提供两套能力：
  - 旧版（兼容）：编辑 name / portraits（raw 文本），其余字段/角色块无损保留；
  - 新版（批 A，结构化）：portraits 槽位表 + roles 结构化条目（字段/traits/未知块），
    词条化编辑，round-trip 无损（拆行/块 → 结构化 → 序列化还原）。
  - 未知块（含 TFR 的 instance = { ... } 包装）以 {"key","raw"} 结构化保存，
    可由 ScriptBlockEditorDialog 编辑后写回。
写入纪律：保存一律走 write_utils.atomic_write_text。
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

_PORTRAIT_KEYS = ("civilian", "army", "navy", "female", "male", "political")

# 角色职责（role）类型 → 结构化字段清单（用于表单；未知字段仍按原行保留）
ROLE_FIELDS = {
    "country_leader": ["ideology", "expire", "id"],
    "advisor": ["slot", "idea_token", "cost"],
    "political_advisor": ["slot", "idea_token", "cost"],
    "corps_commander": ["skill", "attack_skill", "defense_skill", "logistics_skill"],
    "field_marshal": ["skill", "attack_skill", "defense_skill", "planning_skill", "logistics_skill"],
    "navy_leader": ["skill", "attack_skill", "defense_skill", "coordination_skill", "logistics_skill"],
    "army_leader": ["skill", "attack_skill", "defense_skill", "logistics_skill"],
    "air_leader": ["skill", "attack_skill", "defense_skill", "bombing_skill"],
    "unit_leader": ["skill"],
    "area_defense_leader": ["skill", "attack_skill", "defense_skill", "logistics_skill"],
    "governor": [],
}
ROLE_TYPES = tuple(ROLE_FIELDS.keys())


def split_char_blocks(content: str):
    """把 `characters = { ... }` 拆成 [头部文本, [角色块(str), ...], 尾部]。"""
    m = re.search(r"characters\s*=\s*\{", content)
    if not m:
        return content, [], ""
    brace = content.find("{", m.end() - 1)
    depth = 0
    i = brace
    n = len(content)
    while i < n:
        c = content[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    if i >= n:
        return content, [], ""
    inner = content[brace + 1:i]
    tail = content[i + 1:]
    blocks = _split_top_blocks(inner)
    header = content[:brace + 1] + "\n"
    return header, blocks, tail


_BLOCK_START = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{")
_LINE_KV = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(?:\"([^\"]*)\"|(\S+))\s*$")


def _split_top_blocks(inner: str) -> List[str]:
    blocks = []
    i = 0
    n = len(inner)
    while i < n:
        m = _BLOCK_START.search(inner, i)
        if not m:
            break
        brace = inner.find("{", m.end() - 1)
        depth = 0
        j = brace
        while j < n:
            cj = inner[j]
            if cj == "{":
                depth += 1
            elif cj == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            i = brace + 1
            continue
        blocks.append(inner[m.start():j + 1])
        i = j + 1
    return blocks


def _block_parts(block: str):
    """解析块 → (key, "block", inner) 或 (None, None, raw)。"""
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", block)
    if not m:
        return None, None, block
    key = m.group(1)
    brace = block.find("{")
    depth = 0
    i = brace
    while i < len(block):
        c = block[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return key, "block", block[brace + 1:i]
        i += 1
    return None, None, block


def _iter_inner_items(inner: str):
    """按顺序把内层拆成条目：
        ("line", key, value, quoted)  —— key=value 行
        ("raw_line", text)            —— 无法解析的行（原样保留）
        ("block", key, rawblock)      —— 子块
    """
    i = 0
    n = len(inner)
    while i < n:
        m = _BLOCK_START.search(inner, i)
        if not m:
            for ln in inner[i:].splitlines():
                ln = ln.strip()
                if not ln or ln.lstrip().startswith("#"):
                    continue
                mm = _LINE_KV.match(ln)
                if mm:
                    yield ("line", mm.group(1),
                           mm.group(2) if mm.group(2) is not None else mm.group(3),
                           mm.group(2) is not None)
                else:
                    yield ("raw_line", ln)
            return
        pre = inner[i:m.start()]
        for ln in pre.splitlines():
            ln = ln.strip()
            if not ln or ln.lstrip().startswith("#"):
                continue
            mm = _LINE_KV.match(ln)
            if mm:
                yield ("line", mm.group(1),
                       mm.group(2) if mm.group(2) is not None else mm.group(3),
                       mm.group(2) is not None)
            else:
                yield ("raw_line", ln)
        brace = inner.find("{", m.end() - 1)
        depth = 0
        j = brace
        while j < n:
            cj = inner[j]
            if cj == "{":
                depth += 1
            elif cj == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            i = brace + 1
            continue
        rawblock = inner[m.start():j + 1]
        yield ("block", m.group(1), rawblock)
        i = j + 1


def _name_from_block(block: str) -> str:
    m = re.search(r'name\s*=\s*"([^"]*)"', block)
    return m.group(1) if m else ""


# ---------- 肖像（结构化槽位） ----------

def _parse_slots(portraits_inner: str) -> list:
    """解析 portraits 内层 → [{"scope","size","texture"}, ...]。"""
    slots = []
    for sub in _split_top_blocks(portraits_inner or ""):
        key, kind, val = _block_parts(sub)
        if not key or kind != "block":
            continue
        for mm in re.finditer(r"([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(\S+)", val or ""):
            slots.append({"scope": key, "size": mm.group(1), "texture": mm.group(2)})
    return slots


def render_portraits_slots(slots: List[dict]) -> str:
    """把槽位表渲染为 portraits 内层文本（同 scope 合并为一个块）。"""
    by_scope = {}
    for s in slots:
        by_scope.setdefault(s["scope"], []).append(s)
    out = []
    for scope, items in by_scope.items():
        out.append("\t\t\t%s = {" % scope)
        for s in items:
            out.append("\t\t\t\t%s = %s" % (s["size"], s["texture"]))
        out.append("\t\t\t}")
    return "\n".join(out)


# ---------- roles（结构化条目） ----------

def parse_role_entry(raw_block: str) -> dict:
    key, kind, val = _block_parts(raw_block)
    items = list(_iter_inner_items(val or ""))
    traits = []
    for item in items:
        if item[0] == "block" and item[1] == "traits":
            _, _, tinner = _block_parts(item[2])
            traits = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", tinner or "")
    return {"role_type": key, "items": items, "traits": traits, "raw": raw_block}


def role_get_field(entry: dict, key: str) -> str:
    for item in entry["items"]:
        if item[0] == "line" and item[1] == key:
            return item[2]
    return ""


def role_set_field(entry: dict, key: str, value: str, quoted: Optional[bool] = None):
    replaced = False
    out = []
    for item in entry["items"]:
        if item[0] == "line" and item[1] == key:
            q = item[3] if quoted is None else quoted
            out.append(("line", key, value, q))
            replaced = True
        else:
            out.append(item)
    if not replaced:
        out.append(("line", key, value, bool(quoted)))
    entry["items"] = out


def role_del_field(entry: dict, key: str):
    entry["items"] = [it for it in entry["items"]
                      if not (it[0] == "line" and it[1] == key)]


def role_get_block(entry: dict, key: str) -> Optional[str]:
    for item in entry["items"]:
        if item[0] == "block" and item[1] == key:
            return item[2]
    return None


def _indent_block(raw: str, pad: str) -> str:
    lines = []
    for ln in raw.splitlines():
        s = ln.strip()
        if s:
            lines.append(pad + s)
    return "\n".join(lines) if lines else pad + (raw or "").strip()


def render_role_entry(entry: dict, indent: str = "\t\t") -> str:
    """序列化单个 role 条目（字段行 + traits + 其余块，按原顺序）。"""
    pad = indent + "\t"
    lines = [indent + entry["role_type"] + " = {"]
    have_traits = False
    for item in entry["items"]:
        kind = item[0]
        if kind == "line":
            _, key, value, quoted = item
            val = '"%s"' % value if quoted else str(value)
            lines.append("%s%s = %s" % (pad, key, val))
        elif kind == "raw_line":
            lines.append(pad + item[1])
        elif kind == "block":
            bkey = item[1]
            if bkey == "traits" and not have_traits:
                lines.append("%s%s = { %s }" % (pad, "traits", " ".join(entry["traits"])))
                have_traits = True
            else:
                lines.append(_indent_block(item[2], pad))
    if not have_traits and entry["traits"]:
        lines.append("%s%s = { %s }" % (pad, "traits", " ".join(entry["traits"])))
    lines.append(indent + "}")
    return "\n".join(lines)


def role_summary(entry: dict) -> str:
    parts = [entry["role_type"]]
    for k in ("ideology", "slot", "idea_token"):
        v = role_get_field(entry, k)
        if v:
            parts.append("%s=%s" % (k, v))
    return " · ".join(parts)


# ---------- 角色块解析 / 渲染 ----------

def parse_character_block(block: str) -> dict:
    """解析单个角色块。返回老键（兼容）+ 新键（结构化）。"""
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", block)
    cid = m.group(1) if m else ""
    inner = block[block.find("{") + 1:block.rfind("}")]

    items = list(_iter_inner_items(inner))
    name_loc = ""
    desc_loc = ""
    others_lines = []
    portraits_inner = ""
    portraits_slots = []
    roles = []
    role_entries = []
    others = []
    others_blocks = []
    unknown_blocks = []

    for item in items:
        kind = item[0]
        if kind == "line":
            key, value, quoted = item[1], item[2], item[3]
            if key == "name":
                name_loc = value
            elif key == "desc":
                desc_loc = value
            else:
                others_lines.append(("line", key, value, quoted))
        elif kind == "raw_line":
            others_lines.append(("raw_line", item[1]))
        elif kind == "block":
            key = item[1]
            raw = item[2]
            if key == "portraits":
                portraits_inner = item[2]
                _, _, pval = _block_parts(item[2])
                portraits_slots = _parse_slots(pval)
            elif key in ROLE_TYPES:
                roles.append(item[2])
                role_entries.append(parse_role_entry(item[2]))
            else:
                # 结构化未知块：key + 原始块文本，供 ScriptBlockEditorDialog 编辑。
                # instance = { ... } 等 TFR 包装块也走这里（不再视为只读）。
                entry = {"key": key, "raw": raw}
                unknown_blocks.append(entry)
                others_blocks.append(entry)
                others.append(raw)

    return {
        "id": cid, "name_loc": name_loc, "desc_loc": desc_loc,
        "portraits_inner": portraits_inner, "roles": roles,
        "others": others, "raw": block,
        "portraits_slots": portraits_slots,
        "role_entries": role_entries,
        "others_lines": others_lines,
        "others_blocks": others_blocks,
        "unknown_blocks": unknown_blocks,
    }


# ---------- 旧版渲染（兼容，保留原名） ----------

def _replace_portraits(raw: str, new_inner: str) -> str:
    m = re.search(r"portraits\s*=\s*\{", raw)
    if not m:
        nm = re.search(r'\n(\s*)name\s*=\s*"[^"]*"', raw)
        ins = nm.end() if nm else raw.find("{") + 1
        indent = "\t\t"
        new_block = ('\n' + indent + 'portraits = {\n'
                     + ''.join('\t\t\t' + ln + '\n' for ln in
                               (new_inner or "").splitlines())
                     + indent + '}')
        return raw[:ins] + new_block + raw[ins:]
    brace = raw.find("{", m.end() - 1)
    depth = 0
    j = brace
    while j < len(raw):
        c = raw[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    if depth != 0:
        return raw
    new_block = ('portraits = {\n'
                 + ''.join('\t\t\t' + ln + '\n' for ln in (new_inner or "").splitlines())
                 + '\t\t}')
    return raw[:m.start()] + new_block + raw[j + 1:]


def render_character_block(meta: dict, name_loc: Optional[str] = None,
                           portraits_inner: Optional[str] = None) -> str:
    """（旧版，兼容）基于原始块只替换 name / portraits，其余内容原样保留。"""
    raw = meta.get("raw") or ""
    if not raw.strip():
        return "\t{} = {{\n\t\tname = \"{}\"\n\t}}\n".format(meta["id"], meta["name_loc"])
    name_loc = meta["name_loc"] if name_loc is None else (name_loc or "")
    portraits_inner = meta["portraits_inner"] if portraits_inner is None else portraits_inner

    out = raw
    nm = re.search(r'name\s*=\s*"[^"]*"', out)
    if nm:
        out = out[:nm.start()] + 'name = "{}"'.format(name_loc) + out[nm.end():]
    else:
        brace = out.find("{")
        out = out[:brace + 1] + '\n\t\tname = "{}"'.format(name_loc) + out[brace + 1:]
    out = _replace_portraits(out, portraits_inner)
    return out


# ---------- 新版渲染（结构化） ----------

def _unknown_blocks_of_meta(meta):
    """兼容新版 structured list 与旧版 raw string 列表。"""
    ub = meta.get("unknown_blocks")
    if ub:
        return ub
    ob = meta.get("others_blocks") or []
    if ob:
        return ob
    return ub or []


def render_character_block_v2(meta: dict,
                              name_loc: Optional[str] = None,
                              portraits_slots: Optional[List[dict]] = None,
                              role_entries: Optional[List[dict]] = None) -> str:
    """（新版）按结构化数据序列化：基本信息 + 肖像槽位 + roles + 其余行/块。"""
    cid = meta["id"]
    name_loc = meta["name_loc"] if name_loc is None else (name_loc or "")
    slots = meta.get("portraits_slots") if portraits_slots is None else portraits_slots or []
    roles = meta.get("role_entries") if role_entries is None else role_entries or []

    lines = ["\t%s = {" % cid]
    lines.append('\t\tname = "%s"' % name_loc)
    if meta.get("desc_loc"):
        lines.append('\t\tdesc = "%s"' % meta.get("desc_loc"))
    if slots:
        lines.append("\t\tportraits = {")
        by_scope = {}
        for s in slots:
            by_scope.setdefault(s["scope"], []).append(s)
        for scope, items in by_scope.items():
            lines.append("\t\t\t%s = {" % scope)
            for s in items:
                lines.append("\t\t\t\t%s = %s" % (s["size"], s["texture"]))
            lines.append("\t\t\t}")
        lines.append("\t\t}")
    for entry in roles:
        lines.append(render_role_entry(entry))
    for item in meta.get("others_lines", []):
        if item[0] == "line":
            _, key, value, quoted = item
            val = '"%s"' % value if quoted else str(value)
            lines.append("\t\t%s = %s" % (key, val))
        else:
            lines.append("\t\t" + item[1])
    unknown_blocks = _unknown_blocks_of_meta(meta)
    for entry in unknown_blocks:
        if isinstance(entry, dict):
            raw = entry.get("raw") or ""
        else:
            raw = entry
        lines.append(_indent_block(raw, "\t\t"))
    lines.append("\t}")
    return "\n".join(lines)


def load_file(filepath: str):
    """读取角色文件 → (header, [meta], tail)。meta 含结构化字段。"""
    with open(filepath, "r", encoding="utf-8-sig", errors="ignore") as f:
        content = f.read()
    header, blocks, tail = split_char_blocks(content)
    metas = []
    for b in blocks:
        meta = parse_character_block(b)
        if meta["id"]:
            metas.append(meta)
    return header, metas, tail


def save_file(filepath: str, header: str, metas: List[dict], tail: str) -> int:
    """（旧版）写回角色文件（旧版渲染，roles raw 保留）。返回角色数。"""
    from write_utils import atomic_write_text
    body = "\n".join(render_character_block(m) for m in metas)
    text = header + body + ("\n" if body else "") + "}\n" + tail
    atomic_write_text(filepath, text, encoding="utf-8")
    return len(metas)


def save_file_v2(filepath: str, header: str, metas: List[dict], tail: str) -> int:
    """（新版）按结构化数据写回角色文件。返回角色数。"""
    from write_utils import atomic_write_text
    body = "\n".join(render_character_block_v2(m) for m in metas)
    text = header + body + ("\n" if body else "") + "}\n" + tail
    atomic_write_text(filepath, text, encoding="utf-8")
    return len(metas)


def find_char_file(mod_path: str, hoi4_path: str = "", char_id: Optional[str] = None):
    """定位角色所在文件（mod 优先）。"""
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "common", "characters")
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".txt"):
                continue
            fp = os.path.join(d, name)
            try:
                header, metas, tail = load_file(fp)
            except Exception:
                continue
            if char_id:
                if any(m["id"] == char_id for m in metas):
                    if os.path.normcase(fp).startswith(os.path.normcase(mod_path)) or base == mod_path:
                        return fp
            else:
                return fp
    return None
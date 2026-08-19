"""角色（Character）数据层（算法层）

解析 common/characters/*.txt 中的角色块，编辑 name / portraits，
保留角色内其余字段与角色块（country_leader/advisor/leader 等）不被破坏。
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

_PORTRAIT_KEYS = ("civilian", "army", "navy", "female", "male", "political")


def split_char_blocks(content: str):
    """把 `characters = { ... }` 拆成 [头部文本, [角色块(str), ...]]。"""
    # 定位 characters = { 的内层
    m = re.search(r"characters\s*=\s*\{", content)
    if not m:
        return content, []
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
        return content, []
    inner = content[brace + 1:i]
    tail = content[i + 1:]
    blocks = _split_top_blocks(inner)
    header = content[:brace + 1] + "\n"
    return header, blocks, tail


_BLOCK_START = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{")


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
    """解析角色块的内层成 (key, inner) 或 (key, value)。"""
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


def _name_from_block(block: str) -> str:
    m = re.search(r'name\s*=\s*"([^"]*)"', block)
    return m.group(1) if m else ""


def _value_from(inner: str, key: str) -> str:
    pat = re.compile(r'%s\s*=\s*"?([^"\s]+)"?' % re.escape(key))
    m = pat.search(inner)
    return m.group(1) if m else ""


def parse_character_block(block: str) -> dict:
    """解析单个角色块。返回 {id, name_loc, portraits_inner, roles:[raw块], others:[行]}。"""
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", block)
    cid = m.group(1) if m else ""
    inner = block[block.find("{") + 1:block.rfind("}")]
    name_loc = _name_from_block(inner)

    portraits_inner = ""
    roles = []
    others = []
    # 用 _split_top_blocks 处理内层子块
    for sub in _split_top_blocks(inner):
        key, kind, val = _block_parts(sub)
        if key is None:
            others.append(sub)
            continue
        if key == "portraits":
            portraits_inner = val
        elif key in ("country_leader", "advisor", "corps_commander",
                     "field_marshal", "navy_leader", "unit_leader",
                     "political_advisor", "army_leader", "air_leader"):
            roles.append(sub)
        else:
            others.append(sub)
    # 其余单行字段（如 ideology=... 在 country_leader 内已存；这里收集顶层单值）
    return {"id": cid, "name_loc": name_loc, "portraits_inner": portraits_inner,
            "roles": roles, "others": others, "raw": block}


def _replace_portraits(raw: str, new_inner: str) -> str:
    """在原始块内替换 portraits = { ... } 的整个块（保留其余内容）。"""
    m = re.search(r"portraits\s*=\s*\{", raw)
    if not m:
        # 无 portraits：在 name 行后插入
        nm = re.search(r'\n(\s*)name\s*=\s*"[^"]*"', raw)
        ins = m_index = None
        if nm:
            ins = nm.end()
            indent = "\t\t"
        else:
            brace = raw.find("{")
            ins = brace + 1
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
    """基于原始块只替换 name / portraits，其余内容原样保留。"""
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


def load_file(filepath: str):
    """读取角色文件 → (header, [meta], tail)。"""
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
    """把角色列表写回文件。返回角色数。"""
    from write_utils import atomic_write_text
    body = "\n".join(render_character_block(m) for m in metas)
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
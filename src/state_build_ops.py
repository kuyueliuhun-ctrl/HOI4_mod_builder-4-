"""州建筑/州类别/国家颜色写回（无 GUI 依赖，GUI / 契约测试共用）

写回策略（用户要求：编辑原版内容时自动落到 mod）：
- 目标文件在 mod 内 → 直接块级编辑（保留其余内容）
- 目标文件只在游戏本体 → **自动复制到 mod 同相对路径再编辑**
  （HOI4 的 state / countries 文件是整文件覆盖语义，复制全文安全；
  buildings 键名用引擎键名，如 anti_air_building / radar_station）

全部走 write_utils 原子写（BOM 拒绝 + 撤销快照）。
"""

from __future__ import annotations

import os
import re
import shutil

from state_edit_ops import find_state_block


def _read_utf8(path):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def ensure_file_in_mod(mod_path, hoi4_path, rel_path):
    """确保相对路径文件在 mod 内：原版则复制到 mod。

    Args:
        rel_path: 相对路径（如 history/states/1-France.txt）

    Returns:
        (mod_path_abs, copied): 文件在 mod 的绝对路径；
        copied=True 表示本次从游戏复制；两处都无返回 (None, False)
    """
    if not mod_path or not os.path.isdir(mod_path):
        return None, False
    mod_fp = os.path.join(mod_path, rel_path)
    if os.path.isfile(mod_fp):
        return mod_fp, False
    game_fp = None
    if hoi4_path:
        cand = os.path.join(hoi4_path, rel_path)
        if os.path.isfile(cand):
            game_fp = cand
    if game_fp is None:
        return None, False
    try:
        os.makedirs(os.path.dirname(mod_fp), exist_ok=True)
        shutil.copyfile(game_fp, mod_fp)
        return mod_fp, True
    except Exception:
        return None, False


def _state_file_for(mod_path, hoi4_path, state_id, state_data):
    """定位州所在文件（mod 优先），原版则复制到 mod。

    Returns:
        (abs_path, copied) 或 (None, False)
    """
    if state_data is not None:
        info = state_data.states.get(state_id)
        if info and info.get("src"):
            src = info["src"]
            if os.path.normcase(src).startswith(
                    os.path.normcase(mod_path)):
                return src, False
            rel = os.path.relpath(src, hoi4_path or "")
            if not rel.startswith(".."):
                return ensure_file_in_mod(mod_path, hoi4_path, rel)
    # 兜底：直接扫描 mod/游戏目录
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "history", "states")
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".txt"):
                continue
            fp = os.path.join(d, name)
            content = _read_utf8(fp)
            if content is None:
                continue
            if re.search(r"\bstate\s*=\s*\{[^}]*?\bid\s*=\s*%d\b" % state_id,
                         content):
                if os.path.normcase(fp).startswith(os.path.normcase(mod_path)):
                    return fp, False
                rel = os.path.relpath(fp, base)
                return ensure_file_in_mod(mod_path, hoi4_path, rel)
    return None, False


# ---------------------------------------------------------------- 块级编辑

def _find_block(content, start, key):
    """从 start 起找 `key = {` 块，返回 (块起点, 块内起点, 块终点) 或 None。"""
    m = re.search(r"\b%s\s*=\s*\{" % re.escape(key), content[start:])
    if not m:
        return None
    brace = start + m.end() - 1
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
                return (brace, brace + 1, i)
        i += 1
    return None


def _line_indent(text, pos):
    """取 pos 所在行行首缩进（tab/空格串）。"""
    line_start = text.rfind("\n", 0, pos) + 1
    m = re.match(r"[ \t]*", text[line_start:])
    return m.group(0)


def _edit_buildings(content, state_id, btype, level, pid=None):
    """在 state 块内编辑 buildings（纯文本块级，返回新内容或 None）。

    level <= 0 表示移除该建筑。pid 指定时写入/移除 `pid = { btype = level }`
    锚定块（省级建筑）；否则写顶层键（州级建筑）。
    """
    loc = find_state_block(content, state_id)
    if loc is None:
        return None
    start, end, inner_start, inner_end = loc
    block = content[inner_start:inner_end]
    hm = _find_block(block, 0, "history")
    if hm is None:
        # 无 history 块：在 id 行后插入 history = { buildings = {...} }
        idm = re.search(r"^(\s*id\s*=\s*\d+[^\r\n]*)", block, re.MULTILINE)
        if not idm:
            return None
        indent = _line_indent(block, idm.start())
        entry = _buildings_entry("\t", btype, level, pid)
        insert = ("\n" + indent + "\thistory = {\n"
                  + indent + "\t\tbuildings = {\n"
                  + indent + entry
                  + indent + "\t\t}\n"
                  + indent + "\t}")
        block = block[:idm.end()] + insert + block[idm.end():]
        return content[:inner_start] + block + content[inner_end:]

    h_start, h_inner, h_end = hm
    h_block = block[h_start:h_end + 1]
    bm = _find_block(h_block, 1, "buildings")
    if bm is None:
        # history 内插入 buildings 块
        indent = _line_indent(h_block, h_end)
        entry = _buildings_entry("\t" + indent, btype, level, pid)
        insert = ("\n" + indent + "\tbuildings = {\n"
                  + indent + entry
                  + indent + "\t}")
        new_h = h_block[:h_end] + insert + h_block[h_end:]
        block = block[:h_start] + new_h + block[h_end + 1:]
        return content[:inner_start] + block + content[inner_end:]

    b_start, b_inner, b_end = bm
    b_block = h_block[b_start:b_end + 1]
    inner = b_block[b_inner - b_start:b_end - b_start]
    if pid is not None:
        # 锚定块 pid = { ... }
        pm = re.search(r"^(\s*)%d\s*=\s*\{" % pid, inner, re.MULTILINE)
        if pm:
            p_brace = pm.end() - 1
            depth = 0
            i = p_brace
            n = len(inner)
            while i < n:
                c = inner[i]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        p_block = inner[pm.start():i + 1]
                        p_indent = pm.group(1)
                        inner2 = _set_key_line(
                            p_block, btype, level,
                            line_indent=p_indent + "\t",
                            line_anchored=False)
                        if re.match(r"^[ \t]*\d+\s*=\s*\{\s*\}\s*$",
                                    inner2):
                            # 键删光：整个 pid 块删除
                            inner = inner[:pm.start()] + inner[i + 1:]
                        else:
                            inner = (inner[:pm.start()] + inner2
                                     + inner[i + 1:])
                        break
                i += 1
        elif level > 0:
            indent = _line_indent(inner, len(inner))
            insert = ("\n" + indent + "\t%d = {\n" % pid
                      + indent + "\t\t%s = %d\n" % (btype, level)
                      + indent + "\t}\n" + indent)
            inner = inner.rstrip() + insert
        if inner != b_block[b_inner - b_start:b_end - b_start]:
            new_b = b_block[:b_inner - b_start] + inner \
                + b_block[b_end - b_start:]
            h_block = h_block[:b_start] + new_b + h_block[b_end + 1:]
            block = block[:h_start] + h_block + block[h_end + 1:]
            return content[:inner_start] + block + content[inner_end:]
        return None
    else:
        # 顶层键 btype = level
        inner2 = _set_key_line(inner, btype, level,
                               line_indent=_line_indent(inner, 0))
        if inner2 == inner:
            return None
        new_b = b_block[:b_inner - b_start] + inner2 \
            + b_block[b_end - b_start:]
        h_block = h_block[:b_start] + new_b + h_block[b_end + 1:]
        block = block[:h_start] + h_block + block[h_end + 1:]
        return content[:inner_start] + block + content[inner_end:]


def _set_key_line(block, key, level, line_indent="\t\t", line_anchored=True):
    """块内替换/插入/删除 `key = level`。返回新块。

    line_anchored=True 时按行首匹配（顶层键，避免误伤块内嵌套）；
    False 时块内任意位置匹配（单行锚定块 `10 = { naval_base = 3 }`）。
    """
    pattern = (r"^[ \t]*%s\s*=\s*[^\r\n]*" if line_anchored
               else r"\b%s\s*=\s*[^\r\n}]*") % re.escape(key)
    m = re.search(pattern, block, re.MULTILINE)
    if m:
        if level <= 0:
            return block[:m.start()] + block[m.end():]
        ind = re.match(r"[ \t]*", m.group(0)).group(0)
        return (block[:m.start()]
                + ind + "%s = %d" % (key, level)
                + block[m.end():])
    if level <= 0:
        return block
    insert = line_indent + "%s = %d\n" % (key, level)
    return block.rstrip() + "\n" + insert


def _buildings_entry(indent, btype, level, pid=None):
    """生成 buildings 块内的条目文本（含缩进）。"""
    if pid is not None:
        return ("%s%d = {\n%s\t%s = %d\n%s}\n"
                % (indent, pid, indent, btype, level, indent))
    return "%s%s = %d\n" % (indent, btype, level)


def set_state_building_in_content(content, state_id, btype, level, pid=None):
    """纯函数：state 文件内容中设置建筑（顶层或锚定地块）。"""
    return _edit_buildings(content, state_id, btype, level, pid)


def set_state_category_in_content(content, state_id, category):
    """纯函数：state 文件内容中设置 state_category（替换/插入）。"""
    loc = find_state_block(content, state_id)
    if loc is None:
        return None
    start, end, inner_start, inner_end = loc
    block = content[inner_start:inner_end]
    m = re.search(r"^([ \t]*)state_category\s*=\s*[^\r\n]*",
                  block, re.MULTILINE)
    if m:
        new_line = m.group(1) + "state_category = %s" % category
        block = block[:m.start()] + new_line + block[m.end():]
    else:
        idm = re.search(r"^(\s*id\s*=\s*\d+[^\r\n]*)", block, re.MULTILINE)
        if not idm:
            return None
        indent = _line_indent(block, idm.start())
        insert = "\n%sstate_category = %s" % (indent, category)
        block = block[:idm.end()] + insert + block[idm.end():]
    return content[:inner_start] + block + content[inner_end:]


def set_country_color_in_content(content, rgb):
    """纯函数：countries 文件内容中替换第一个 color 块为 { r g b }。"""
    loc = _find_block(content, 0, "color")
    if loc is None:
        return None
    c_start, c_inner, c_end = loc
    new_block = "{ %d %d %d }" % (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    return content[:c_start] + new_block + content[c_end + 1:]


# ---------------------------------------------------------------- 写回封装

def _atomic_write(fp, mod_path, content):
    from write_utils import atomic_write_text
    atomic_write_text(fp, content)
    return os.path.relpath(fp, mod_path)


def set_state_building(mod_path, hoi4_path, state_id, btype, level,
                       pid=None, state_data=None):
    """写回州建筑（自动确保文件在 mod 内）。

    Returns:
        (ok, message, rel_path): message in
        written / copied_written / not_found / no_mod
    """
    if not mod_path or not os.path.isdir(mod_path):
        return False, "no_mod", ""
    fp, copied = _state_file_for(mod_path, hoi4_path, state_id, state_data)
    if fp is None:
        return False, "not_found", ""
    content = _read_utf8(fp)
    if content is None:
        return False, "not_found", ""
    new_content = _edit_buildings(content, state_id, btype, level, pid)
    if new_content is None or new_content == content:
        return False, "not_found", ""
    rel = _atomic_write(fp, mod_path, new_content)
    return True, ("copied_written" if copied else "written"), rel


def set_state_category(mod_path, hoi4_path, state_id, category,
                       state_data=None):
    """写回州类别（自动确保文件在 mod 内）。"""
    if not mod_path or not os.path.isdir(mod_path):
        return False, "no_mod", ""
    fp, copied = _state_file_for(mod_path, hoi4_path, state_id, state_data)
    if fp is None:
        return False, "not_found", ""
    content = _read_utf8(fp)
    if content is None:
        return False, "not_found", ""
    new_content = set_state_category_in_content(content, state_id, category)
    if new_content is None or new_content == content:
        return False, "not_found", ""
    rel = _atomic_write(fp, mod_path, new_content)
    return True, ("copied_written" if copied else "written"), rel


def set_country_color(mod_path, hoi4_path, tag, rgb):
    """写回国家颜色（文件不在 mod 时自动复制到 mod）。

    tag -> 文件名：扫描 common/countries（mod→游戏）找 country_tag 匹配
    或文件名匹配。

    Returns:
        (ok, message, rel_path)
    """
    if not mod_path or not os.path.isdir(mod_path):
        return False, "no_mod", ""
    tag = (tag or "").strip().upper()
    if not tag:
        return False, "not_found", ""
    rel = _country_file_rel(mod_path, hoi4_path, tag)
    if rel is None:
        return False, "not_found", ""
    fp, copied = ensure_file_in_mod(mod_path, hoi4_path, rel)
    if fp is None:
        return False, "not_found", ""
    content = _read_utf8(fp)
    if content is None:
        return False, "not_found", ""
    new_content = set_country_color_in_content(content, rgb)
    if new_content is None or new_content == content:
        return False, "not_found", ""
    rel = _atomic_write(fp, mod_path, new_content)
    return True, ("copied_written" if copied else "written"), rel


def _country_file_rel(mod_path, hoi4_path, tag):
    """按 tag 定位 countries 文件相对路径（country_tag 匹配优先，再文件名）。"""
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "common", "countries")
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".txt"):
                continue
            if os.path.splitext(name)[0].upper() == tag:
                return os.path.join("common", "countries", name)
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".txt"):
                continue
            content = _read_utf8(os.path.join(d, name))
            if content and re.search(
                    r"\bcountry_tag\s*=\s*[\"']?%s[\"']?" % re.escape(tag),
                    content):
                return os.path.join("common", "countries", name)
    return None

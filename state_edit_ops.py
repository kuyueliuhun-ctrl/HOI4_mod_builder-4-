"""州归属编辑（无 GUI 依赖，GUI / 契约测试共用）

地图编辑界面的「涂色改归属」写回通道：
- 输入：mod 内 history/states/*.txt（只写 mod，不碰游戏本体文件）
- 定位：pid → 州 id（StateData.province_to_state）→ 所在文件 → state 块（括号配对）
- 写回：块内 history 块的 owner = TAG 替换（无 history/owner 则插入），
  保留文件其余内容；走 write_utils 原子写（BOM 拒绝 + 撤销快照）

限制：州定义位于游戏本体时（mod 未覆盖），本模块不写游戏文件，
返回 need_mod_copy=True 提示用户在 mod 中覆盖该州。
"""

from __future__ import annotations

import os
import re


def find_state_files(mod_path):
    """mod 内 history/states/*.txt 文件列表。"""
    base = os.path.join(mod_path, "history", "states")
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        if name.lower().endswith(".txt"):
            out.append(os.path.join(base, name))
    return out


def find_state_block(content, state_id):
    """在文件内容中定位 state = { ... } 块（括号配对）。

    Returns:
        (start, end, inner_start, inner_end) 或 None
        start/end 含花括号；inner 为块内文本区间
    """
    for m in re.finditer(r"\bstate\s*=\s*\{", content):
        start = m.end() - 1
        depth = 0
        i = start
        n = len(content)
        while i < n:
            c = content[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    idm = re.search(r"\bid\s*=\s*(\d+)",
                                    content[start + 1:i])
                    if idm and int(idm.group(1)) == state_id:
                        return (start, i, start + 1, i)
                    break
            i += 1
    return None


def set_state_owner_in_content(content, state_id, tag):
    """在 state 文件内容中设置指定州的 owner（块级替换，保留其余内容）。

    Args:
        content: 文件全文
        state_id: 州 id
        tag: 国家标签（自动大写）

    Returns:
        str: 新内容；未找到州时返回 None
    """
    tag = (tag or "").strip().upper()
    if not tag:
        return None
    loc = find_state_block(content, state_id)
    if loc is None:
        return None
    start, end, inner_start, inner_end = loc
    block = content[inner_start:inner_end]

    # 块内 history = { ... } 块
    hm = re.search(r"\bhistory\s*=\s*\{", block)
    if hm:
        h_start = hm.end() - 1
        depth = 0
        i = h_start
        n = len(block)
        while i < n:
            c = block[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    h_block = block[h_start:i + 1]
                    # owner 替换（保留原缩进）
                    om = re.search(r"^(\s*)owner\s*=\s*[^\r\n]*",
                                   h_block, re.MULTILINE)
                    if om:
                        indent = om.group(1)
                        new_h = (h_block[:om.start()]
                                 + indent + "owner = %s" % tag
                                 + h_block[om.end():])
                    else:
                        indent = hm.group(0).replace("history", "")
                        ind = re.search(r"^\s*", block[:hm.start()])
                        base_ind = ind.group(0) if ind else "\t"
                        new_h = (h_block[:-1] + "\n" + base_ind + "\t"
                                 + "owner = %s\n" % tag + h_block[-1:])
                    block = block[:h_start] + new_h + block[i + 1:]
                    break
            i += 1
    else:
        # 无 history 块：在块内 id 行后插入
        idm = re.search(r"^(\s*id\s*=\s*\d+[^\r\n]*)", block, re.MULTILINE)
        if not idm:
            return None
        indent = re.search(r"^\s*", idm.group(1)).group(0)
        insert = ("\n" + indent + "\thistory = {\n"
                  + indent + "\t\towner = %s\n" % tag
                  + indent + "\t}")
        block = block[:idm.end()] + insert + block[idm.end():]

    return content[:inner_start] + block + content[inner_end:]


def set_state_owner(mod_path, state_id, tag, state_data=None):
    """写回 mod 内州 owner（原子写 + 撤销快照）。

    Args:
        mod_path: mod 根目录
        state_id: 州 id
        tag: 国家标签
        state_data: StateData（可选；提供时用于校验州属于 mod 而非游戏）

    Returns:
        (ok, message, file_rel):
            ok=True: 已写入
            ok=False, message="not_in_mod": 州定义在游戏本体，mod 未覆盖
            ok=False, message="not_found": mod 内未找到该州块
    """
    if not mod_path or not os.path.isdir(mod_path):
        return False, "no_mod", ""
    for fp in find_state_files(mod_path):
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        new_content = set_state_owner_in_content(content, state_id, tag)
        if new_content is not None:
            if new_content == content:
                return True, "unchanged", os.path.relpath(fp, mod_path)
            from write_utils import atomic_write_text
            atomic_write_text(fp, new_content)
            return True, "written", os.path.relpath(fp, mod_path)
    # mod 内无该州：检查是否属于游戏本体
    if state_data is not None and state_data.states.get(state_id):
        return False, "not_in_mod", ""
    return False, "not_found", ""


def next_state_id(mod_path):
    """下一个可用州 id（mod 内现有州最大值 + 1）。"""
    max_id = 0
    for fp in find_state_files(mod_path):
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        for m in re.finditer(r"\bstate\s*=\s*\{[^}]*?\bid\s*=\s*(\d+)",
                             content):
            try:
                max_id = max(max_id, int(m.group(1)))
            except ValueError:
                pass
    return max_id + 1

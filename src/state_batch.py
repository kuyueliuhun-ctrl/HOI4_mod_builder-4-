"""州建筑/人力/资源批量写（算法层）

对多个州批量写建筑（复用 state_build_ops）、人力、资源。
只写 mod（原版文件自动复制到 mod）；原子写。
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

from write_utils import atomic_write_text


def _read_utf8(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except OSError:
        return None


def _state_blocks(content):
    """找到所有 `state = {` 块的 (起点, 内起点, 终点)。"""
    out = []
    start = 0
    while True:
        m = re.search(r"\bstate\s*=\s*\{", content[start:])
        if not m:
            break
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
                    out.append((brace, brace + 1, i))
                    break
            i += 1
        start = brace + 1
    return out


def _state_block_id(content, block):
    _start, _in, _end = block
    inner = content[_in:_end]
    m = re.search(r"\bid\s*=\s*(-?\d+)", inner)
    return m.group(1) if m else None


def _set_field(content, block, field, value):
    start, _in, end = block
    inner = content[start:end + 1]
    # 找 field = 的行
    pat = re.compile(r"(?m)^([ \t]*)" + re.escape(field) + r"\s*=\s*[^\n]*\n")
    m = pat.search(inner)
    indent = "  "
    if m:
        new_line = m.group(1) + "%s = %s\n" % (field, value)
        return content[: start + m.start()] + new_line + content[start + m.end():]
    # 未存在：在块闭合前插入
    close = content.rfind("}", start, end + 1)
    line_start = content.rfind("\n", start, close) + 1
    indent = "  "
    new_line = "\n" + indent + "%s = %s" % (field, value)
    return content[:close] + new_line + content[close:]


def set_field_for_states(content, field_values: Dict[str, str], field: str) -> str:
    """在 content 中对多个州设置顶层字段（如 manpower / resources）。"""
    result = content
    # 从后往前处理，避免位置偏移
    blocks = _state_blocks(result)
    ids = [_state_block_id(result, b) for b in blocks]
    for block, sid in reversed(list(zip(blocks, ids))):
        if sid in field_values:
            result = _set_field(result, block, field, field_values[sid])
    return result


def _state_path(mod_path, hoi4_path, state_id):
    from state_build_ops import _state_file_for, _read_utf8 as _r
    from state_loader import StateData
    data = None
    try:
        data = StateData.load(mod_path, hoi4_path)
    except Exception:
        data = None
    path, _copied = _state_file_for(mod_path, hoi4_path, int(state_id), data)
    return path


def batch_write(mod_path: str, hoi4_path: str = "",
                manpower: Optional[Dict[str, int]] = None,
                resources: Optional[Dict[str, Dict[str, int]]] = None,
                buildings: Optional[List[dict]] = None) -> dict:
    """批量写州字段。

    manpower:   {state_id: int}
    resources:  {state_id: {"oil": 1, ...}}
    buildings:  [{"state_id":.., "type":.., "level":.., "pid":..}]
    返回 {manpower: n, resources: n, buildings: n}
    """
    result = {"manpower": 0, "resources": 0, "buildings": 0}

    # 建筑：逐州复用 state_build_ops
    if buildings:
        from state_build_ops import set_state_building
        for b in buildings:
            try:
                set_state_building(mod_path, hoi4_path, int(b["state_id"]),
                                   b["type"], b["level"], b.get("pid"))
                result["buildings"] += 1
            except Exception:
                pass

    # 人力/资源：按文件聚合一次读写
    for field, mapping, counter in (
            ("manpower", manpower, "manpower"),
            ("resources", resources, "resources")):
        if not mapping:
            continue
        # 按州分组到文件
        by_file: Dict[str, Dict[str, str]] = {}
        for sid, val in mapping.items():
            path = _state_path(mod_path, hoi4_path, str(sid))
            if not path:
                continue
            if counter == "resources":
                # resources 值序列化
                inner = " ".join("%s = %s" % (k, v) for k, v in val.items())
                val_str = "{ " + inner + " }"
            else:
                val_str = str(val)
            by_file.setdefault(path, {})[str(sid)] = val_str
        for path, fvals in by_file.items():
            content = _read_utf8(path)
            if content is None:
                continue
            new_content = set_field_for_states(content, fvals, field)
            if new_content != content:
                atomic_write_text(path, new_content, encoding="utf-8")
                result[counter] += len(fvals)
    return result
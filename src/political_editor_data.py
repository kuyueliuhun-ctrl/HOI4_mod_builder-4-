"""政治类型（意识形态 / 民族精神 ideas）专用编辑纯函数（P2 ②）。

用于意识形态块与理念块的原位编辑：只替换已知字段/子块，其余内容（注释、
顺序、未知标量与未知子块）原样保留。不依赖 Qt，可单测。
"""

from __future__ import annotations

import re

from ai_loader_crud import _fields, _find_block_bounds
from oob_loader import _block_ranges


def block_inner_text(block_text):
    """提取 `key = { ... }` 的花括号内部文本（无外层尾巴）。"""
    start = block_text.find("{")
    if start < 0:
        return ""
    depth = 0
    end = -1
    for i, ch in enumerate(block_text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        return block_text[start + 1:]
    return block_text[start + 1:end]


def child_block_span(block_text, key):
    """在块文本中找直接子块 `key = { ... }`。

    Returns: (block_start, block_end, inner_start, inner_end) 相对 block_text；
    未找到返回 None。
    """
    try:
        for k, depth, start, end in _block_ranges(block_text):
            if depth != 1 or k != key:
                continue
            inner_s = block_text.find("{", start)
            if inner_s < 0:
                continue
            depth2 = 0
            inner_e = -1
            for i in range(inner_s, len(block_text)):
                ch = block_text[i]
                if ch == "{":
                    depth2 += 1
                elif ch == "}":
                    depth2 -= 1
                    if depth2 == 0:
                        inner_e = i
                        break
            if inner_e < 0:
                continue
            return start, end, inner_s, inner_e
    except Exception:
        pass
    return None


def replace_child_block(block_text, key, new_inner):
    """替换直接子块 `key = { ... }` 的内部文本；不存在则插入到父块开头后。"""
    span = child_block_span(block_text, key)
    if span:
        bs, _be, inner_s, inner_e = span
        return block_text[:inner_s + 1] + new_inner + block_text[inner_e:]
    # 不存在：插到父块第一个 { 之后
    brace = block_text.find("{")
    if brace < 0:
        return block_text
    lines = ["%s = {" % key]
    for line in (new_inner or "").splitlines():
        lines.append("\t" + line if line.strip() else "")
    lines.append("}")
    block = "\n\t".join(lines)
    return block_text[:brace + 1] + "\n" + block + block_text[brace + 1:]


def set_scalar_field(block_text, key, value):
    """替换直接子字段 `key = value`；不存在则插入到父块第一个 { 之后。"""
    quoted = str(value).replace('"', '\\"')
    new_text, n = re.subn(
        r"(\b%s\s*=\s*)[^\n#]+" % re.escape(key),
        lambda m: m.group(1) + quoted,
        block_text, count=1)
    if n == 0:
        brace = block_text.find("{")
        if brace >= 0:
            new_text = (block_text[:brace + 1]
                        + "\n\t%s = %s" % (key, quoted)
                        + block_text[brace + 1:])
    return new_text


def list_items_from_block(block_text):
    """从 `key = { ... }` 块提取列表项（引号剥离、保序）。"""
    inner = block_inner_text(block_text)
    out = []
    for line in inner.splitlines():
        line = line.strip().rstrip(",").strip()
        if not line:
            continue
        if line.startswith('"') and line.endswith('"') and len(line) >= 2:
            line = line[1:-1]
        out.append(line)
    return out


def join_list_block(items):
    """把列表项拼成块内部文本（每行一个，带引号）。"""
    lines = []
    for item in items or []:
        item = item.strip().strip('"')
        if item:
            lines.append('\t"%s"' % item)
    return "\n".join(lines)


def scalar_fields(block_text):
    """块内直接 `key = value` 字段（不含子块）。"""
    return _fields(block_text)


def replace_nested_block_text(content, entity_id, new_block_text,
                              wrapper_key=None, depth=1):
    """在文件全文 content 中替换 wrapper 内指定 id 的嵌套块整块文本。

    - wrapper_key 为 None 时匹配任意顶层 wrapper
    - depth = 实体块相对 wrapper 的深度（ideas 为 2，意识形态为 1）
    - new_block_text 需含 `key = { ... }` 外层
    返回替换后的全文；未找到则原样返回。
    """
    for wkey, wd, ws, we in _block_ranges(content):
        if wd != 0 or (wrapper_key and wkey != wrapper_key):
            continue
        wt = content[ws:we]
        for ekey, ed, es, _ee in _block_ranges(wt):
            if ed != depth or ekey != entity_id:
                continue
            bs, be = _find_block_bounds(content, ws + es)
            if bs < 0 or be <= bs:
                return content
            return content[:bs] + new_block_text + content[be:]
    return content


def insert_into_category(content, wrapper_key, category, new_block_text,
                         depth=2):
    """把新实体块插入 wrapper 内指定分类块（分类闭合括号前）。

    depth 为实体块相对 wrapper 的深度（ideas=2：wrapper → 分类块 → 实体）。
    """
    new_block_text = new_block_text.strip()
    if not new_block_text:
        return content
    for wkey, wd, ws, we in _block_ranges(content):
        if wd != 0 or wkey != wrapper_key:
            continue
        wt = content[ws:we]
        for ckey, cd, cs, _ce in _block_ranges(wt):
            if cd != depth - 1 or ckey != category:
                continue
            bs, be = _find_block_bounds(content, ws + cs)
            if bs < 0 or be <= bs:
                continue
            close = be - 1
            if close >= 0 and content[close] == "}":
                return (content[:close] + "\n\t" + new_block_text + "\n"
                        + content[close:])
    return content
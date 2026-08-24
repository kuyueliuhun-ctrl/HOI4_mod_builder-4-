"""嵌套实体块写回层（B3 复杂类型：wrapper → 实体块）。

提供在「顶层 wrapper 块内定位/替换/插入/删除/重命名/复制嵌套实体块」的
通用字符级操作。实体块通过 (parent_id, id_field, depth) 定位，避免同名
实体块跨父块冲突。
"""

from __future__ import annotations

import re

from oob_loader import _block_ranges
from ai_loader_crud import _fields, _find_block_bounds


def _nested_entity_bounds(content, entity_id, parent_id=None, id_field=None,
                          depth=1):
    """定位嵌套实体块，返回 (parent_bounds_abs, entity_bounds_abs) 或 None。"""
    for wkey, wd, ws, we in _block_ranges(content):
        if wd != 0:
            continue
        if parent_id and wkey != parent_id:
            continue
        wt = content[ws:we]
        for ekey, ed, es, ee in _block_ranges(wt):
            if ed != depth:
                continue
            bt = wt[es:ee]
            cand = _fields(bt).get(id_field) if id_field else None
            if not cand:
                cand = ekey
            if cand == entity_id:
                return (ws, we), (ws + es, ws + ee)
    return None


def replace_nested_block_fields(content, entity_id, fields, parent_id=None,
                                id_field=None, depth=1, quoted_fields=()):
    """替换嵌套实体内多个简单字段（保留未知子块；字段不存在则插入）。"""
    found = _nested_entity_bounds(content, entity_id, parent_id, id_field,
                                  depth)
    if not found:
        return content
    (_ps, _pe), (bs, be) = found
    block_text = content[bs:be]
    new_text = block_text
    for field, value in fields.items():
        quoted = '"%s"' % str(value).replace('"', '\\"') if field in quoted_fields else str(value)
        new_text, n = re.subn(
            r"(\b%s\s*=\s*)[^\n#]+" % re.escape(field),
            lambda m, _v=quoted: m.group(1) + _v,
            new_text, count=1)
        if n == 0:
            brace = new_text.find("{")
            if brace >= 0:
                new_text = (new_text[:brace + 1] + "\n\t%s = %s" % (field, quoted)
                            + new_text[brace + 1:])
    return content[:bs] + new_text + content[be:]


def delete_nested_block(content, entity_id, parent_id=None, id_field=None,
                        depth=1):
    """删除一个嵌套实体块，并尽量折叠多余空行。"""
    found = _nested_entity_bounds(content, entity_id, parent_id, id_field,
                                  depth)
    if not found:
        return content
    (_ps, _pe), (bs, _be) = found
    _tbs, tbe = _find_block_bounds(content, bs)
    before = content[:_tbs].rstrip()
    after = content[tbe:].lstrip("\n")
    if before and after:
        return before + "\n\n" + after
    return before + after


def _rename_block_text(block_text, entity_id, new_id, id_field):
    """对单个实体块文本执行重命名（改 id 字段或改块 key）。"""
    if id_field:
        new_text, n = re.subn(
            r"(\b%s\s*=\s*)[^\n#]+" % re.escape(id_field),
            lambda m: m.group(1) + new_id,
            block_text, count=1)
        if n == 0:
            brace = block_text.find("{")
            if brace >= 0:
                new_text = (block_text[:brace + 1] + "\n\t%s = %s" % (id_field, new_id)
                            + block_text[brace + 1:])
        return new_text
    eq = block_text.find("=")
    if eq < 0:
        return block_text
    prefix = block_text[:eq]
    new_prefix = re.sub(
        r"\b%s(\s*)$" % re.escape(entity_id), new_id + r"\1", prefix, count=1)
    return new_prefix + block_text[eq:]


def rename_nested_block(content, entity_id, new_id, parent_id=None,
                        id_field=None, depth=1):
    """重命名嵌套实体：id_field 存在时替换 id 字段，否则替换块 key。

    content 可以是完整文件（按 bounds 定位后拼接），也可以是单个实体块
    文本（fallback 直接重命名，供 duplicate 复用）。
    """
    found = _nested_entity_bounds(content, entity_id, parent_id, id_field,
                                  depth)
    if found:
        (_ps, _pe), (bs, be) = found
        renamed = _rename_block_text(content[bs:be], entity_id, new_id,
                                     id_field)
        return content[:bs] + renamed + content[be:]
    return _rename_block_text(content, entity_id, new_id, id_field)


def duplicate_nested_block(content, entity_id, new_id, parent_id=None,
                           id_field=None, depth=1):
    """复制嵌套实体块并重命名为 new_id，插到原块之后。"""
    found = _nested_entity_bounds(content, entity_id, parent_id, id_field,
                                  depth)
    if not found:
        return content
    (_ps, _pe), (bs, be) = found
    _tbs, tbe = _find_block_bounds(content, bs)
    block_text = content[bs:tbe]
    copied = rename_nested_block(block_text, entity_id, new_id,
                                 parent_id=None, id_field=id_field, depth=depth)
    return content[:tbe] + "\n" + copied + content[tbe:]


def insert_nested_block(content, entity_id, block_text, parent_id=None,
                        id_field=None, depth=1, after_id=None, indent="\t"):
    """插入嵌套实体块到父 wrapper 内。

    after_id 指定插到哪个实体块之后。depth>1 时插到 wrapper 内第一个
    depth-1 槽位块的闭合括号之前（如 ideas 的 country 槽）；depth==1 时
    插到父 wrapper 闭合括号之前。
    """
    block_text = block_text.strip()
    if not block_text:
        return content
    if after_id:
        found = _nested_entity_bounds(content, after_id, parent_id, id_field,
                                      depth)
        if found:
            (_ps, _pe), (bs, _be) = found
            _tbs, tbe = _find_block_bounds(content, bs)
            return content[:tbe] + "\n" + block_text + content[tbe:]
    for wkey, wd, ws, we in _block_ranges(content):
        if wd != 0:
            continue
        if parent_id and wkey != parent_id:
            continue
        wt = content[ws:we]
        if depth > 1:
            # 找第一个 depth-1 槽位块
            for sk, sd, ss, se in _block_ranges(wt):
                if sd == depth - 1:
                    brace = content.rfind("}", ws + ss, ws + se)
                    if brace >= 0:
                        return (content[:brace] + indent + block_text + "\n"
                                + content[brace:])
            continue
        has = any(ed == depth for _k, ed, _s, _e in _block_ranges(wt))
        if parent_id or has:
            brace = content.rfind("}", ws, we)
            if brace >= 0:
                return (content[:brace] + indent + block_text + "\n"
                        + content[brace:])
    return content
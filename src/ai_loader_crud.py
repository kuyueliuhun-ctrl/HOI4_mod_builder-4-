"""AI 内容写回层（F5 拆分自 ai_loader.py）。

只包含 CRUD / 块级写回 / 通用文本助手；读取与解析仍在 ai_loader.py。
调用方既可从 ai_loader 导入（尾部 re-export），也可直接 import ai_loader_crud。
"""

from __future__ import annotations

import os
import re

from oob_loader import _block_ranges
from tree_node import parse_pdx_text_to_nodes

def _node_value(node, key):
    for c in node.children:
        if c.node_type == "value" and c.key == key:
            return c.value
    return None



def _node_block(node, key):
    for c in node.children:
        if c.node_type == "block" and c.key == key:
            return c
    return None



def _fields(block_text):
    """返回块内直接 `key = value` 字段（不含子块）。

    block_text 可能包含外层 `name = { ... }`，此时先下沉到该块子节点。
    """
    out = {}
    try:
        nodes = parse_pdx_text_to_nodes(block_text)
        if len(nodes) == 1 and nodes[0].node_type == "block":
            nodes = nodes[0].children
        for node in nodes:
            if node.node_type == "value":
                out[node.key] = node.value
    except Exception:
        pass
    return out



def _child_blocks(block_text):
    """返回块内直接子块列表 [(key, start, end)]（相对 block_text）。"""
    out = []
    try:
        for key, depth, start, end in _block_ranges(block_text):
            if depth == 1:
                out.append((key, start, end))
    except Exception:
        pass
    return out



def _child_block_text(block_text, key):
    """返回块内指定 key 的直接子块原文；不存在返回 None。"""
    for k, start, end in _child_blocks(block_text):
        if k == key:
            return block_text[start:end]
    return None



def _inner_block_text(bt):
    """提取 `key = { ... }` 的花括号内部文本（兼容单行/多行/尾随外层 `}`）。"""
    start = bt.find("{")
    if start < 0:
        return ""
    depth = 0
    for i in range(start, len(bt)):
        c = bt[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return bt[start + 1:i]
    return bt[start + 1:]



def _values_in_block(block_text, key):
    """返回 `key = { ... }` 内的一级裸值列表（如国策 ID、区域 ID）。"""
    bt = _child_block_text(block_text, key)
    if not bt:
        return []
    inner = _inner_block_text(bt)
    clean = re.sub(r"#.*", "", inner)
    return re.findall(r"[A-Za-z0-9_][\w\.\-]*", clean)



def _map_values_in_block(block_text, key):
    """返回 `key = { ... }` 内 `name = count` 形式的 dict。"""
    bt = _child_block_text(block_text, key)
    if not bt:
        return {}
    inner = _inner_block_text(bt)
    clean = re.sub(r"#.*", "", inner)
    out = {}
    for m in re.finditer(r"([\w\.\-]+)\s*=\s*([^\s#}{]+)", clean):
        out[m.group(1)] = m.group(2)
    return out



def _find_block_bounds(text, start):
    """从块 key 的起始位置定位 `key = { ... }` 的精确 [start, end) 区间。"""
    eq = text.find("=", start)
    brace = text.find("{", eq)
    if brace < 0:
        return start, len(text)
    depth = 0
    for i in range(brace, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    return start, len(text)



def replace_ai_plan_focus_order(content, plan_id, ordered):
    """替换指定 AI 战略计划的 `ai_national_focuses` 列表。"""
    for key, depth, start, _end in _block_ranges(content):
        if depth != 0 or key != plan_id:
            continue
        plan_start, plan_end = _find_block_bounds(content, start)
        plan_text = content[plan_start:plan_end]
        for ck, cd, cs, _ce in _block_ranges(plan_text):
            if cd == 1 and ck == "ai_national_focuses":
                child_start, child_end = _find_block_bounds(content, plan_start + cs)
                lines = ["ai_national_focuses = {"]
                for fid in ordered:
                    lines.append("\t%s" % fid)
                lines.append("}")
                new_text = "\n".join(lines)
                return content[:child_start] + new_text + content[child_end:]
    return content



def replace_ai_strategy_entries(content, group_id, entries):
    """替换 AI 战略倾向组内的 `ai_strategy` 条目列表。

    entries: [{"type": str, "id": str, "value": str}, ...]
    """
    new_texts = []
    for e in entries:
        lines = ["ai_strategy = {"]
        for k in ("type", "id", "value"):
            lines.append("\t%s = %s" % (k, e.get(k, "")))
        lines.append("}")
        new_texts.append("\n".join(lines))

    for key, depth, start, _end in _block_ranges(content):
        if depth != 0 or key != group_id:
            continue
        group_start, group_end = _find_block_bounds(content, start)
        group_text = content[group_start:group_end]
        old_ranges = []
        for ck, cd, cs, _ce in _block_ranges(group_text):
            if cd == 1 and ck == "ai_strategy":
                cs_abs, ce_abs = _find_block_bounds(group_text, cs)
                old_ranges.append((cs_abs, ce_abs))
        old_ranges.sort()
        # 重建 group_text，替换旧 ai_strategy 块
        pieces = []
        pos = 0
        used = 0
        for os_, oe in old_ranges:
            pieces.append(group_text[pos:os_])
            if used < len(new_texts):
                pieces.append(new_texts[used])
                used += 1
            pos = oe
        pieces.append(group_text[pos:])
        # 如果新条目多于旧块，追加到末尾
        if used < len(new_texts):
            tail = "\n" + "\n".join(new_texts[used:])
            # 追加到 group_text 最后一个 `}` 之前
            close = pieces[-1].rfind("}")
            if close >= 0:
                pieces[-1] = pieces[-1][:close] + tail + pieces[-1][close:]
            else:
                pieces.append(tail)
        new_group = "".join(pieces)
        return content[:group_start] + new_group + content[group_end:]
    return content



def parse_ai_target_variant(target_text):
    """解析 `target_variant = { ... }` → {"type": str, "modules": {slot: mod}}。"""
    if not target_text:
        return {"type": "", "modules": {}}
    f = _fields(target_text)
    modules = _map_values_in_block(target_text, "modules")
    return {"type": f.get("type", ""), "modules": modules}



def replace_ai_equipment_target_variant(content, group_id, variant_id,
                                        variant_type, modules):
    """替换 AI 装备指定变体的 `target_variant` 块。"""
    lines = ["target_variant = {"]
    if variant_type:
        lines.append("\ttype = %s" % variant_type)
    lines.append("\tmodules = {")
    for slot, mod in modules.items():
        lines.append("\t\t%s = %s" % (slot, mod))
    lines.append("\t}")
    lines.append("}")
    new_text = "\n".join(lines)

    for key, depth, start, _end in _block_ranges(content):
        if depth != 0 or key != group_id:
            continue
        group_start, group_end = _find_block_bounds(content, start)
        group_text = content[group_start:group_end]
        for ck, cd, cs, _ce in _block_ranges(group_text):
            if cd == 1 and ck == variant_id:
                var_start, var_end = _find_block_bounds(content, group_start + cs)
                var_text = content[var_start:var_end]
                for tk, td, ts, _te in _block_ranges(var_text):
                    if td == 1 and tk == "target_variant":
                        child_start, child_end = _find_block_bounds(
                            content, var_start + ts)
                        return (content[:child_start] + new_text
                                + content[child_end:])
    return content



def replace_top_block_fields(content, block_id, fields, quoted_fields=()):
    """替换顶层块内多个简单字段（value 不自动加引号；quoted_fields 里的加引号）。"""
    for key, depth, start, _end in _block_ranges(content):
        if depth != 0 or key != block_id:
            continue
        block_start, block_end = _find_block_bounds(content, start)
        block_text = content[block_start:block_end]
        new_text = block_text
        for field, value in fields.items():
            quoted = '"%s"' % str(value).replace('"', '\\"') if field in quoted_fields else str(value)
            new_text, n = re.subn(
                r"(\b%s\s*=\s*)[^\n#]+" % re.escape(field),
                lambda m, _v=quoted: m.group(1) + _v,
                new_text, count=1)
            if n == 0:
                # 字段不存在：在块开头插入
                brace = new_text.find("{")
                if brace >= 0:
                    new_text = (new_text[:brace + 1] + "\n\t%s = %s" % (field, quoted)
                                + new_text[brace + 1:])
        return content[:block_start] + new_text + content[block_end:]
    return content



def replace_ai_template_target_template(content, role_id, target_id, target_template_text):
    """替换 AI 师模板中指定目标模板的 `target_template` 块。"""
    for key, depth, start, _end in _block_ranges(content):
        if depth != 0 or key != role_id:
            continue
        role_start, role_end = _find_block_bounds(content, start)
        role_text = content[role_start:role_end]
        for ck, cd, cs, _ce in _block_ranges(role_text):
            if cd == 1 and ck == target_id:
                tgt_start, tgt_end = _find_block_bounds(content, role_start + cs)
                tgt_text = content[tgt_start:tgt_end]
                for tk, td, ts, _te in _block_ranges(tgt_text):
                    if td == 1 and tk == "target_template":
                        child_start, child_end = _find_block_bounds(
                            content, tgt_start + ts)
                        return (content[:child_start] + target_template_text.strip()
                                + content[child_end:])
    return content



def replace_ai_plan_field(content, plan_id, field, value):
    """替换指定 AI 战略计划内的简单字段（name/desc 等，自动加引号）。"""
    for key, depth, start, _end in _block_ranges(content):
        if depth != 0 or key != plan_id:
            continue
        plan_start, plan_end = _find_block_bounds(content, start)
        plan_text = content[plan_start:plan_end]
        quoted = '"%s"' % value.replace('"', '\\"')
        new_plan, n = re.subn(
            r"(\b%s\s*=\s*)[^\n#]+" % re.escape(field),
            lambda m: m.group(1) + quoted,
            plan_text, count=1)
        if n:
            return content[:plan_start] + new_plan + content[plan_end:]
    return content



def _top_block(content, block_id):
    """返回顶层块 (start, end) 或 None。"""
    for key, depth, start, _end in _block_ranges(content):
        if depth == 0 and key == block_id:
            return _find_block_bounds(content, start)
    return None



def insert_top_block(content, block_text, after_id=None):
    """在顶层插入一个块；after_id 指定插到哪个块之后，否则追加到文件末尾。"""
    block_text = block_text.strip()
    if not block_text:
        return content
    if not block_text.endswith("\n"):
        block_text += "\n"
    if after_id:
        bounds = _top_block(content, after_id)
        if bounds:
            bs, be = bounds
            return content[:be] + "\n" + block_text + content[be:]
    if content.strip():
        return content.rstrip() + "\n\n" + block_text
    return block_text



def delete_top_block(content, block_id):
    """删除一个顶层块，并尽量折叠多余空行。"""
    bounds = _top_block(content, block_id)
    if bounds is None:
        return content
    bs, be = bounds
    before = content[:bs].rstrip()
    after = content[be:].lstrip("\n")
    if before and after:
        return before + "\n\n" + after
    return before + after



def rename_top_block(content, old_id, new_id):
    """重命名顶层块的 key。"""
    bounds = _top_block(content, old_id)
    if bounds is None:
        return content
    bs, be = bounds
    block_text = content[bs:be]
    eq = block_text.find("=")
    if eq < 0:
        return content
    prefix = block_text[:eq]
    new_prefix = re.sub(
        r"\b%s(\s*)$" % re.escape(old_id), new_id + r"\1", prefix, count=1)
    return content[:bs] + new_prefix + block_text[eq:] + content[be:]



def duplicate_top_block(content, block_id, new_id):
    """复制一个顶层块并重命名为 new_id。"""
    bounds = _top_block(content, block_id)
    if bounds is None:
        return content
    bs, be = bounds
    block_text = content[bs:be]
    new_text = rename_top_block(block_text, block_id, new_id)
    return insert_top_block(content, new_text, after_id=block_id)



def replace_top_block_child(content, parent_id, child_key, new_block_text):
    """替换顶层块 parent_id 内直接子块 child_key 的完整文本。"""
    bounds = _top_block(content, parent_id)
    if bounds is None:
        return content
    parent_start, parent_end = bounds
    parent_text = content[parent_start:parent_end]
    for ck, cd, cs, _ce in _block_ranges(parent_text):
        if cd == 1 and ck == child_key:
            child_start, child_end = _find_block_bounds(
                content, parent_start + cs)
            new_text = new_block_text.strip()
            return content[:child_start] + new_text + content[child_end:]
    return content


# ---------- AI 战略倾向 CRUD ----------


def insert_ai_strategy_group(content, group_id, entries=None):
    """新建 AI 战略倾向组。"""
    lines = ["%s = {" % group_id]
    for e in entries or [{"type": "", "id": "", "value": "1"}]:
        lines.append("\tai_strategy = {")
        lines.append("\t\ttype = %s" % e.get("type", ""))
        lines.append("\t\tid = %s" % e.get("id", ""))
        lines.append("\t\tvalue = %s" % e.get("value", "1"))
        lines.append("\t}")
    lines.append("}")
    return insert_top_block(content, "\n".join(lines))



def delete_ai_strategy_group(content, group_id):
    return delete_top_block(content, group_id)



def rename_ai_strategy_group(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)



def duplicate_ai_strategy_group(content, group_id, new_id):
    return duplicate_top_block(content, group_id, new_id)


# ---------- AI 科研权重 CRUD ----------


def insert_ai_focus(content, block_id, research=None):
    """新建 AI 科研权重块。"""
    lines = ["%s = {" % block_id, "\tresearch = {"]
    for tech, weight in (research or {}).items():
        lines.append("\t\t%s = %s" % (tech, weight))
    lines.append("\t}")
    lines.append("}")
    return insert_top_block(content, "\n".join(lines))



def delete_ai_focus(content, block_id):
    return delete_top_block(content, block_id)



def rename_ai_focus(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)



def duplicate_ai_focus(content, block_id, new_id):
    return duplicate_top_block(content, block_id, new_id)


# ---------- AI 区域 CRUD（areas = { ... } 内嵌套） ----------


def _areas_block_bounds(content):
    """定位顶层 `areas = { ... }` 的 (start, end)。"""
    for key, depth, start, _end in _block_ranges(content):
        if depth == 0 and key == "areas":
            return _find_block_bounds(content, start)
    return None



def insert_ai_area(content, area_id, strategic_regions=None):
    """在 areas 块内插入一个区域。"""
    regions = strategic_regions or []
    block_text = "%s = {\n\tstrategic_regions = {\n%s\n\t}\n}" % (
        area_id,
        "\n".join("\t\t%s" % r for r in regions))
    bounds = _areas_block_bounds(content)
    if bounds is None:
        return content.rstrip() + "\n\nareas = {\n\t" + block_text + "\n}\n"
    start, end = bounds
    # 插入到 areas 最后一个 `}` 之前
    inner = content[start:end]
    close = inner.rfind("}")
    return (content[:start + close]
            + ("\n\t" + block_text + "\n")
            + content[start + close:])



def delete_ai_area(content, area_id):
    bounds = _areas_block_bounds(content)
    if bounds is None:
        return content
    start, end = bounds
    areas_text = content[start:end]
    for key, depth, cs, _ce in _block_ranges(areas_text):
        if depth == 1 and key == area_id:
            as_, ae = _find_block_bounds(areas_text, cs)
            return content[:start + as_] + content[start + ae:]
    return content



def rename_ai_area(content, old_id, new_id):
    bounds = _areas_block_bounds(content)
    if bounds is None:
        return content
    start, end = bounds
    areas_text = content[start:end]
    for key, depth, cs, _ce in _block_ranges(areas_text):
        if depth == 1 and key == old_id:
            as_, ae = _find_block_bounds(areas_text, cs)
            block_text = areas_text[as_:ae]
            eq = block_text.find("=")
            if eq < 0:
                return content
            prefix = block_text[:eq]
            new_prefix = re.sub(
                r"\b%s(\s*)$" % re.escape(old_id), new_id + r"\1",
                prefix, count=1)
            return (content[:start + as_] + new_prefix
                    + block_text[eq:] + content[start + ae:])
    return content



def duplicate_ai_area(content, area_id, new_id):
    bounds = _areas_block_bounds(content)
    if bounds is None:
        return content
    start, end = bounds
    areas_text = content[start:end]
    for key, depth, cs, _ce in _block_ranges(areas_text):
        if depth == 1 and key == area_id:
            as_, ae = _find_block_bounds(areas_text, cs)
            block_text = areas_text[as_:ae]
            eq = block_text.find("=")
            if eq < 0:
                return content
            prefix = block_text[:eq]
            new_prefix = re.sub(
                r"\b%s(\s*)$" % re.escape(area_id), new_id + r"\1",
                prefix, count=1)
            new_text = new_prefix + block_text[eq:]
            return (content[:start + ae] + "\n\t" + new_text.strip()
                    + content[start + ae:])
    return content



def replace_ai_area_regions(content, area_id, regions):
    """替换 AI 区域内 strategic_regions 列表。"""
    bounds = _areas_block_bounds(content)
    if bounds is None:
        return content
    start, end = bounds
    areas_text = content[start:end]
    for key, depth, cs, _ce in _block_ranges(areas_text):
        if depth == 1 and key == area_id:
            as_, ae = _find_block_bounds(areas_text, cs)
            area_text = areas_text[as_:ae]
            for rk, rd, rs, _re in _block_ranges(area_text):
                if rd == 1 and rk == "strategic_regions":
                    rs_abs, re_abs = _find_block_bounds(area_text, rs)
                    lines = ["strategic_regions = {"]
                    for r in regions:
                        lines.append("\t%s" % r)
                    lines.append("}")
                    new_text = "\n".join(lines)
                    return (content[:start + as_ + rs_abs] + new_text
                            + content[start + as_ + re_abs:])
    return content



def replace_ai_area_block(content, area_id, new_block_text):
    """整体替换 AI 区域块（保留 areas 外层）。"""
    bounds = _areas_block_bounds(content)
    if bounds is None:
        return content
    start, end = bounds
    areas_text = content[start:end]
    for key, depth, cs, _ce in _block_ranges(areas_text):
        if depth == 1 and key == area_id:
            as_, ae = _find_block_bounds(areas_text, cs)
            return (content[:start + as_] + new_block_text.strip()
                    + content[start + ae:])
    return content



def replace_top_block_field(content, parent_id, field, value, quoted=False):
    """替换顶层块内简单字段的值（不存在则在块开头插入）。"""
    bounds = _top_block(content, parent_id)
    if bounds is None:
        return content
    parent_start, parent_end = bounds
    block_text = content[parent_start:parent_end]
    val = str(value).replace('"', '\\"') if quoted else str(value)
    if quoted:
        val = '"%s"' % val
    new_text, n = re.subn(
        r"(\b%s\s*=\s*)[^\n#]+" % re.escape(field), lambda m: m.group(1) + val,
        block_text, count=1)
    if n == 0:
        brace = new_text.find("{")
        if brace >= 0:
            new_text = (new_text[:brace + 1] + "\n\t%s = %s" % (field, val)
                        + new_text[brace + 1:])
    return content[:parent_start] + new_text + content[parent_end:]



def insert_ai_faction_theater(content, theater_id, name="", regions=None):
    lines = ["%s = {" % theater_id]
    if name:
        lines.append('\tname = "%s"' % name)
    lines.append("\tregions = {")
    for r in regions or []:
        lines.append("\t\t%s" % r)
    lines.append("\t}")
    lines.append("}")
    return insert_top_block(content, "\n".join(lines))



def delete_ai_faction_theater(content, theater_id):
    return delete_top_block(content, theater_id)



def rename_ai_faction_theater(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)



def duplicate_ai_faction_theater(content, theater_id, new_id):
    return duplicate_top_block(content, theater_id, new_id)



def replace_ai_region_list(content, theater_id, field, values):
    """替换 theater 内的 regions / preferred_countries 列表块。"""
    lines = ["%s = {" % field]
    for v in values:
        lines.append("\t%s" % v)
    lines.append("}")
    return replace_top_block_child(
        content, theater_id, field, "\n".join(lines))



def upsert_top_block_child(content, parent_id, child_key, new_block_text):
    """在顶层块内替换/追加一个子块（不存在则插入）。"""
    bounds = _top_block(content, parent_id)
    if bounds is None:
        return content
    parent_start, parent_end = bounds
    parent_text = content[parent_start:parent_end]
    for ck, cd, cs, _ce in _block_ranges(parent_text):
        if cd == 1 and ck == child_key:
            child_start, child_end = _find_block_bounds(
                content, parent_start + cs)
            new_text = new_block_text.strip()
            return content[:child_start] + new_text + content[child_end:]
    # 未找到：插入到父块最后一个 `}` 之前
    close = parent_text.rfind("}")
    if close < 0:
        return content
    new_text = new_block_text.strip()
    return (content[:parent_start + close]
            + "\n\t" + new_text + "\n"
            + content[parent_start + close:])


# ---------- AI 师模板 CRUD ----------


def insert_ai_template_role(content, role_id, role=""):
    lines = ["%s = {" % role_id]
    if role:
        lines.append("\trole = %s" % role)
    lines.append("}")
    return insert_top_block(content, "\n".join(lines))



def delete_ai_template_role(content, role_id):
    return delete_top_block(content, role_id)



def rename_ai_template_role(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)



def duplicate_ai_template_role(content, role_id, new_id):
    return duplicate_top_block(content, role_id, new_id)



def _role_block(content, role_id):
    return _top_block(content, role_id)



def insert_ai_template_target(content, role_id, target_id):
    """在角色块内插入一个目标模板块。"""
    bounds = _role_block(content, role_id)
    if bounds is None:
        return content
    start, end = bounds
    role_text = content[start:end]
    block_text = "%s = {\n\ttarget_template = { }\n}" % target_id
    close = role_text.rfind("}")
    if close < 0:
        return content
    return (content[:start + close] + "\n\t" + block_text + "\n"
            + content[start + close:])



def delete_ai_template_target(content, role_id, target_id):
    bounds = _role_block(content, role_id)
    if bounds is None:
        return content
    start, end = bounds
    role_text = content[start:end]
    for ck, cd, cs, _ce in _block_ranges(role_text):
        if cd == 1 and ck == target_id:
            as_, ae = _find_block_bounds(role_text, cs)
            return content[:start + as_] + content[start + ae:]
    return content



def rename_ai_template_target(content, role_id, old_id, new_id):
    bounds = _role_block(content, role_id)
    if bounds is None:
        return content
    start, end = bounds
    role_text = content[start:end]
    for ck, cd, cs, _ce in _block_ranges(role_text):
        if cd == 1 and ck == old_id:
            as_, ae = _find_block_bounds(role_text, cs)
            block_text = role_text[as_:ae]
            eq = block_text.find("=")
            if eq < 0:
                return content
            prefix = block_text[:eq]
            new_prefix = re.sub(
                r"\b%s(\s*)$" % re.escape(old_id), new_id + r"\1",
                prefix, count=1)
            return (content[:start + as_] + new_prefix + block_text[eq:]
                    + content[start + ae:])
    return content



def duplicate_ai_template_target(content, role_id, target_id, new_id):
    bounds = _role_block(content, role_id)
    if bounds is None:
        return content
    start, end = bounds
    role_text = content[start:end]
    for ck, cd, cs, _ce in _block_ranges(role_text):
        if cd == 1 and ck == target_id:
            as_, ae = _find_block_bounds(role_text, cs)
            block_text = role_text[as_:ae]
            eq = block_text.find("=")
            if eq < 0:
                return content
            prefix = block_text[:eq]
            new_prefix = re.sub(
                r"\b%s(\s*)$" % re.escape(target_id), new_id + r"\1",
                prefix, count=1)
            new_text = new_prefix + block_text[eq:]
            return (content[:start + ae] + "\n\t" + new_text.strip()
                    + content[start + ae:])
    return content



def replace_ai_template_target_field(content, role_id, target_id, field, value, quoted=False):
    """替换目标模板内简单字段。"""
    bounds = _role_block(content, role_id)
    if bounds is None:
        return content
    start, end = bounds
    role_text = content[start:end]
    for ck, cd, cs, _ce in _block_ranges(role_text):
        if cd == 1 and ck == target_id:
            as_, ae = _find_block_bounds(role_text, cs)
            block_text = role_text[as_:ae]
            val = str(value)
            if quoted:
                val = '"%s"' % val.replace('"', '\\"')
            new_text, n = re.subn(
                r"(\b%s\s*=\s*)[^\n#]+" % re.escape(field),
                lambda m: m.group(1) + val, block_text, count=1)
            if n == 0:
                brace = new_text.find("{")
                if brace >= 0:
                    new_text = (new_text[:brace + 1]
                                + "\n\t%s = %s" % (field, val)
                                + new_text[brace + 1:])
            return content[:start + as_] + new_text + content[start + ae:]
    return content


# ---------- AI 装备 CRUD ----------


def insert_ai_equipment_group(content, group_id, category="air"):
    lines = ["%s = {" % group_id, "\tcategory = %s" % category]
    lines.append("\troles = {")
    lines.append("\t}")  # roles stub
    lines.append("}")
    return insert_top_block(content, "\n".join(lines))



def delete_ai_equipment_group(content, group_id):
    return delete_top_block(content, group_id)



def rename_ai_equipment_group(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)



def duplicate_ai_equipment_group(content, group_id, new_id):
    return duplicate_top_block(content, group_id, new_id)



def _eq_group_block(content, group_id):
    return _top_block(content, group_id)



def insert_ai_equipment_variant(content, group_id, variant_id):
    bounds = _eq_group_block(content, group_id)
    if bounds is None:
        return content
    start, end = bounds
    group_text = content[start:end]
    block_text = "%s = {\n\ttarget_variant = {\n\t\tmodules = { }\n\t}\n}" % variant_id
    close = group_text.rfind("}")
    if close < 0:
        return content
    return (content[:start + close] + "\n\t" + block_text + "\n"
            + content[start + close:])



def delete_ai_equipment_variant(content, group_id, variant_id):
    bounds = _eq_group_block(content, group_id)
    if bounds is None:
        return content
    start, end = bounds
    group_text = content[start:end]
    for ck, cd, cs, _ce in _block_ranges(group_text):
        if cd == 1 and ck == variant_id:
            as_, ae = _find_block_bounds(group_text, cs)
            return content[:start + as_] + content[start + ae:]
    return content



def rename_ai_equipment_variant(content, group_id, old_id, new_id):
    bounds = _eq_group_block(content, group_id)
    if bounds is None:
        return content
    start, end = bounds
    group_text = content[start:end]
    for ck, cd, cs, _ce in _block_ranges(group_text):
        if cd == 1 and ck == old_id:
            as_, ae = _find_block_bounds(group_text, cs)
            block_text = group_text[as_:ae]
            eq = block_text.find("=")
            if eq < 0:
                return content
            prefix = block_text[:eq]
            new_prefix = re.sub(
                r"\b%s(\s*)$" % re.escape(old_id), new_id + r"\1",
                prefix, count=1)
            return (content[:start + as_] + new_prefix + block_text[eq:]
                    + content[start + ae:])
    return content



def duplicate_ai_equipment_variant(content, group_id, variant_id, new_id):
    bounds = _eq_group_block(content, group_id)
    if bounds is None:
        return content
    start, end = bounds
    group_text = content[start:end]
    for ck, cd, cs, _ce in _block_ranges(group_text):
        if cd == 1 and ck == variant_id:
            as_, ae = _find_block_bounds(group_text, cs)
            block_text = group_text[as_:ae]
            eq = block_text.find("=")
            if eq < 0:
                return content
            prefix = block_text[:eq]
            new_prefix = re.sub(
                r"\b%s(\s*)$" % re.escape(variant_id), new_id + r"\1",
                prefix, count=1)
            new_text = new_prefix + block_text[eq:]
            return (content[:start + ae] + "\n\t" + new_text.strip()
                    + content[start + ae:])
    return content



def replace_ai_equipment_variant_field(content, group_id, variant_id, field, value, quoted=False):
    """替换变体内简单字段（priority / history 等）。"""
    bounds = _eq_group_block(content, group_id)
    if bounds is None:
        return content
    start, end = bounds
    group_text = content[start:end]
    for ck, cd, cs, _ce in _block_ranges(group_text):
        if cd == 1 and ck == variant_id:
            as_, ae = _find_block_bounds(group_text, cs)
            block_text = group_text[as_:ae]
            val = str(value)
            if quoted:
                val = '"%s"' % val.replace('"', '\\"')
            new_text, n = re.subn(
                r"(\b%s\s*=\s*)[^\n#]+" % re.escape(field),
                lambda m: m.group(1) + val, block_text, count=1)
            if n == 0:
                brace = new_text.find("{")
                if brace >= 0:
                    new_text = (new_text[:brace + 1]
                                + "\n\t%s = %s" % (field, val)
                                + new_text[brace + 1:])
            return content[:start + as_] + new_text + content[start + ae:]
    return content



def replace_ai_equipment_allowed_modules(content, group_id, variant_id, modules):
    """替换变体内 allowed_modules 列表块。"""
    lines = ["allowed_modules = {"]
    for m in modules:
        lines.append("\t%s" % m)
    lines.append("}")
    return replace_or_upsert_nested_child(
        content, group_id, variant_id, "allowed_modules", "\n".join(lines))



def _nested_child_bounds(content, top_id, child_id):
    """返回顶层块 top_id 内直接子块 child_id 的 (start, end) 绝对区间。"""
    bounds = _top_block(content, top_id)
    if bounds is None:
        return None
    start, _end = bounds
    text = content[start:_end]
    for ck, cd, cs, _ce in _block_ranges(text):
        if cd == 1 and ck == child_id:
            cs_abs, ce_abs = _find_block_bounds(text, cs)
            return start + cs_abs, start + ce_abs
    return None



def replace_or_upsert_nested_child(content, top_id, child_id, key, new_text):
    """在 top_id > child_id 内替换/追加子块 key。"""
    nb = _nested_child_bounds(content, top_id, child_id)
    if nb is None:
        return content
    cstart, cend = nb
    child_text = content[cstart:cend]
    for ck, cd, cs, _ce in _block_ranges(child_text):
        if cd == 1 and ck == key:
            rs, re = _find_block_bounds(child_text, cs)
            return content[:cstart + rs] + new_text.strip() + content[cstart + re:]
    close = child_text.rfind("}")
    if close < 0:
        return content
    return (content[:cstart + close] + "\n\t" + new_text.strip() + "\n"
            + content[cstart + close:])


# ---------- AI 战略计划 CRUD ----------


def insert_ai_plan(content, plan_id, name="", desc=""):
    lines = ["%s = {" % plan_id]
    if name:
        lines.append('\tname = "%s"' % name)
    if desc:
        lines.append('\tdesc = "%s"' % desc)
    lines.append("\tai_national_focuses = {")
    lines.append("\t}")
    lines.append("}")
    return insert_top_block(content, "\n".join(lines))



def delete_ai_plan(content, plan_id):
    return delete_top_block(content, plan_id)



def rename_ai_plan(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)



def duplicate_ai_plan(content, plan_id, new_id):
    return duplicate_top_block(content, plan_id, new_id)


# ---------- AI 海军 CRUD ----------


def insert_ai_navy_goal(content, goal_id, objective_type="", min_priority="0", max_priority="0"):
    lines = ["%s = {" % goal_id]
    if objective_type:
        lines.append("\tobjective_type = %s" % objective_type)
    lines.append("\tmin_priority = %s" % min_priority)
    lines.append("\tmax_priority = %s" % max_priority)
    lines.append("}")
    return insert_top_block(content, "\n".join(lines))



def delete_ai_navy_goal(content, goal_id):
    return delete_top_block(content, goal_id)



def rename_ai_navy_goal(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)



def duplicate_ai_navy_goal(content, goal_id, new_id):
    return duplicate_top_block(content, goal_id, new_id)



def insert_ai_navy_fleet(content, fleet_id):
    lines = ["%s = {" % fleet_id,
             "\trequired_taskforces = {", "}", "}"]
    return insert_top_block(content, "\n".join(lines))



def delete_ai_navy_fleet(content, fleet_id):
    return delete_top_block(content, fleet_id)



def rename_ai_navy_fleet(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)



def duplicate_ai_navy_fleet(content, fleet_id, new_id):
    return duplicate_top_block(content, fleet_id, new_id)



def insert_ai_navy_taskforce(content, taskforce_id):
    lines = ["%s = {" % taskforce_id,
             "\tmission = {", "}",
             "\tmin_composition = {", "}",
             "\toptimal_composition = {", "}", "}"]
    return insert_top_block(content, "\n".join(lines))



def delete_ai_navy_taskforce(content, taskforce_id):
    return delete_top_block(content, taskforce_id)



def rename_ai_navy_taskforce(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)



def duplicate_ai_navy_taskforce(content, taskforce_id, new_id):
    return duplicate_top_block(content, taskforce_id, new_id)

__all__ = ['replace_ai_plan_focus_order', 'replace_ai_strategy_entries', 'parse_ai_target_variant', 'replace_ai_equipment_target_variant', 'replace_top_block_fields', 'replace_ai_template_target_template', 'replace_ai_plan_field', 'insert_top_block', 'delete_top_block', 'rename_top_block', 'duplicate_top_block', 'replace_top_block_child', 'insert_ai_strategy_group', 'delete_ai_strategy_group', 'rename_ai_strategy_group', 'duplicate_ai_strategy_group', 'insert_ai_focus', 'delete_ai_focus', 'rename_ai_focus', 'duplicate_ai_focus', 'insert_ai_area', 'delete_ai_area', 'rename_ai_area', 'duplicate_ai_area', 'replace_ai_area_regions', 'replace_ai_area_block', 'replace_top_block_field', 'insert_ai_faction_theater', 'delete_ai_faction_theater', 'rename_ai_faction_theater', 'duplicate_ai_faction_theater', 'replace_ai_region_list', 'upsert_top_block_child', 'insert_ai_template_role', 'delete_ai_template_role', 'rename_ai_template_role', 'duplicate_ai_template_role', 'insert_ai_template_target', 'delete_ai_template_target', 'rename_ai_template_target', 'duplicate_ai_template_target', 'replace_ai_template_target_field', 'insert_ai_equipment_group', 'delete_ai_equipment_group', 'rename_ai_equipment_group', 'duplicate_ai_equipment_group', 'insert_ai_equipment_variant', 'delete_ai_equipment_variant', 'rename_ai_equipment_variant', 'duplicate_ai_equipment_variant', 'replace_ai_equipment_variant_field', 'replace_ai_equipment_allowed_modules', 'replace_or_upsert_nested_child', 'insert_ai_plan', 'delete_ai_plan', 'rename_ai_plan', 'duplicate_ai_plan', 'insert_ai_navy_goal', 'delete_ai_navy_goal', 'rename_ai_navy_goal', 'duplicate_ai_navy_goal', 'insert_ai_navy_fleet', 'delete_ai_navy_fleet', 'rename_ai_navy_fleet', 'duplicate_ai_navy_fleet', 'insert_ai_navy_taskforce', 'delete_ai_navy_taskforce', 'rename_ai_navy_taskforce', 'duplicate_ai_navy_taskforce']

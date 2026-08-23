# -*- coding: utf-8 -*-
"""事件（Event）数据层（算法层，无 Qt）

解析/写回 HOI4 事件文件：
- 扫描 events/**/*.txt（mod 优先)
- 顶层 add_namespace 词条与 country_event/news_event 等事件块
- 提供事件实体摘要、CRUD、字段级写回与 option 第 N 个块替换
- 所有写回函数只做内容字符串变换，不直接写文件；保存由信号槽层编排
"""

from __future__ import annotations

import os
import re

from oob_loader import _block_ranges
from ai_loader import _find_block_bounds, insert_top_block

_EVENT_KEYS = (
    "country_event", "news_event", "state_event",
    "operative_leader_event", "dynamic_event", "unit_leader_event",
)

_COVERED_FIELDS = {
    "id", "title", "desc", "picture", "major", "is_triggered_only",
    "fire_only_once", "hidden",
    "mean_time_to_happen", "immediate", "after",
}

_COVERED_CHILD_KEYS = {
    "mean_time_to_happen", "immediate", "after", "option",
}


def _field_re(seg, key):
    m = re.search(r'\b' + re.escape(key) + r'\s*=\s*"([^"]*)"', seg)
    if m:
        return m.group(1)
    m = re.search(r'\b' + re.escape(key) + r'\s*=\s*([\w\.\-]+)', seg)
    return m.group(1) if m else ""


def _is_flag(seg, key):
    m = re.search(r'\b' + re.escape(key) + r'\s*=\s*(\S+)', seg)
    return bool(m and str(m.group(1)).strip().lower() == "yes")


def _count_options(seg):
    return sum(1 for k, _d, _s, _e in _block_ranges(seg) if k == "option")


def _child_block_text(seg, key):
    """返回块 seg 内直接子块 key 的完整原文；不存在返回 None。"""
    for k, depth, start, _end in _block_ranges(seg):
        if depth == 1 and k == key:
            return seg[start:_find_block_bounds(seg, start)[1]]
    return None


def _parse_option(seg):
    """解析单个 option 块。"""
    trigger = _child_block_text(seg, "trigger")
    ai_chance = _child_block_text(seg, "ai_chance")
    return {
        "name": _field_re(seg, "name"),
        "name_key": _field_re(seg, "name"),
        "trigger": trigger or "",
        "ai_chance": ai_chance or "",
        "effects": seg,
        "raw": seg,
        "count": _count_options(seg) and 1,
    }


def _other_fields(seg):
    """提取事件块内「表单未覆盖」的直接标量字段（保留原始值字符串）。"""
    covered = set(_COVERED_FIELDS) | set(_COVERED_CHILD_KEYS)
    out = []
    for m in re.finditer(r'(?m)^\t([\w\.\-]+)\s*=\s*("[^"]*"|[^\s#}{]+)\s*$', seg):
        key = m.group(1)
        if key in covered:
            continue
        value = m.group(2)
        out.append((key, value))
    return out


# ---------- 文件级其他字段（顶层常量/非事件标量键） ----------

_TOP_SCALAR_RE = re.compile(
    r'^\s*([@\w\.\-]+)\s*=\s*("[^"]*"|[^\r\n#}{]+)\s*(?:#.*)?$')


def _top_level_block_spans(content):
    """返回全部顶层 `key = { ... }` 块的 [start, end)。"""
    spans = []
    for key, depth, start, _end in _block_ranges(content):
        if depth == 0:
            spans.append(_find_block_bounds(content, start))
    return spans


def _in_span(spans, pos):
    return any(s <= pos < e for s, e in spans)


def parse_file_other_fields(content):
    """解析事件文件顶层 add_namespace / @常量 / 非事件标量键。

    返回 [(key, value)]，只收集事件块之外、非块头的直接标量行。
    """
    out = []
    spans = _top_level_block_spans(content)
    pos = 0
    for line in content.splitlines(True):
        start = pos
        pos += len(line)
        if _in_span(spans, start):
            continue
        m = _TOP_SCALAR_RE.match(line)
        if m:
            out.append((m.group(1), m.group(2).strip()))
    return out


def apply_file_other_fields(content, rows):
    """按 [(key, value)] 写回文件级其他字段；value 空字符串表示删除该行。

    顺序策略：已存在的行原位替换/删除，新增行追加到文件末尾；事件块内部不受影响。
    """
    pending = {}
    for key, value in (rows or []):
        key = str(key or "").strip()
        if not key:
            continue
        pending[key] = str(value or "").strip()

    orig_map = dict(parse_file_other_fields(content))
    spans = _top_level_block_spans(content)
    lines = content.splitlines(True)
    pos = 0
    out_lines = []
    for line in lines:
        start = pos
        pos += len(line)
        if _in_span(spans, start):
            out_lines.append(line)
            continue
        m = _TOP_SCALAR_RE.match(line)
        if m and m.group(1) in pending:
            key = m.group(1)
            value = pending.pop(key)
            if value == orig_map.get(key):
                out_lines.append(line)
                continue
            if value == "":
                continue
            ending = "\r\n" if line.endswith("\r\n") else \
                ("\n" if line.endswith("\n") else "")
            out_lines.append("%s = %s%s" % (key, value, ending))
        else:
            out_lines.append(line)

    result = "".join(out_lines)
    if pending:
        if result and not result.endswith("\n"):
            result += "\n"
        for key, value in pending.items():
            result += "%s = %s\n" % (key, value)
    return result


def parse_event_block(seg, fp, etype, namespaces=None):
    """解析单个事件块为完整实体 dict。"""
    mtth_seg = _child_block_text(seg, "mean_time_to_happen")
    immediate = _child_block_text(seg, "immediate") or ""
    after = _child_block_text(seg, "after") or ""
    options = []
    for key, depth, start, _end in _block_ranges(seg):
        if depth != 1 or key != "option":
            continue
        opt_seg = seg[start:_find_block_bounds(seg, start)[1]]
        options.append(_parse_option(opt_seg))
    ns = list(namespaces or [])
    eid = _field_re(seg, "id")
    return {
        "id": eid,
        "type": etype,
        "file": fp,
        "title": _field_re(seg, "title"),
        "desc": _field_re(seg, "desc"),
        "picture": _field_re(seg, "picture"),
        "major": _is_flag(seg, "major"),
        "is_triggered_only": _is_flag(seg, "is_triggered_only"),
        "fire_only_once": _is_flag(seg, "fire_only_once"),
        "hidden": _is_flag(seg, "hidden"),
        "option_count": _count_options(seg),
        "namespaces": ns,
        "namespace": ns[-1] if ns else "",
        "mean_time_to_happen": {
            "days": _field_re(mtth_seg, "days") if mtth_seg else "",
            "modifier": _child_block_text(mtth_seg, "modifier") if mtth_seg else "",
            "raw": mtth_seg or "",
        },
        "immediate": immediate,
        "after": after,
        "options": options,
        "fire_for_sender": _is_flag(seg, "fire_for_sender"),
        "minor_flavor": _field_re(seg, "minor_flavor"),
        "other_fields": _other_fields(seg),
        "raw": seg,
    }


def _scan_events(mod_path="", hoi4_path=""):
    """返回 mod/游戏 events 目录下全部 .txt 文件（mod 优先）。"""
    files = []
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "events")
        if not os.path.isdir(d):
            continue
        for dp, _dirs, names in os.walk(d):
            for n in sorted(names):
                if n.lower().endswith(".txt"):
                    fp = os.path.join(dp, n)
                    if os.path.normcase(fp).startswith(
                            os.path.normcase(mod_path or "")) \
                            and any(os.path.normcase(x) == os.path.normcase(fp)
                                    for x in files):
                        continue
                    files.append(fp)
    return files


def load_event_entities(mod_path="", hoi4_path=""):
    """扫描事件文件，返回 list[dict]（每个 dict 含解析与原始块）。"""
    out = []
    for fp in _scan_events(mod_path, hoi4_path):
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        namespaces = re.findall(r'add_namespace\s*=\s*([\w\.\-]+)', content)
        for key, depth, start, end in _block_ranges(content):
            if depth != 0 or key not in _EVENT_KEYS:
                continue
            seg = content[start:end]
            eid = _field_re(seg, "id")
            if not eid:
                continue
            out.append(parse_event_block(seg, fp, key, namespaces))
    return out


# ---------- 事件块定位 ----------

def _event_block(content, event_id):
    """定位 id == event_id 的顶层事件块，返回 [start, end) 或 None。"""
    for key, depth, start, _end in _block_ranges(content):
        if depth != 0 or key not in _EVENT_KEYS:
            continue
        seg = content[start:_find_block_bounds(content, start)[1]]
        if _field_re(seg, "id") == event_id:
            return _find_block_bounds(content, start)
    return None


def _replace_scalar_in_seg(seg, key, value, quoted=False):
    """在事件块 seg 内替换/插入一个直接标量字段。"""
    val = str(value)
    if quoted:
        val = '"%s"' % val.replace("\\", "\\\\").replace('"', '\\"')
    pat = re.compile(r'(\b%s\s*=\s*)(?:"[^"]*"|[^\r\n#}{]+)' % re.escape(key))
    if pat.search(seg):
        return pat.sub(lambda m: m.group(1) + val, seg, count=1)
    m = re.search(r'(\bid\s*=\s*[^\r\n#]+)', seg)
    if m:
        pos = m.end()
        return seg[:pos] + "\n\t%s = %s" % (key, val) + seg[pos:]
    brace = seg.find("{")
    if brace >= 0:
        pos = brace + 1
        return seg[:pos] + "\n\t%s = %s" % (key, val) + seg[pos:]
    return seg


def _replace_child_in_seg(seg, key, new_block_text, index=None):
    """替换/追加 seg 内的直接子块（index 指定第 N 个同名块）。"""
    new_text = new_block_text.strip()
    count = 0
    for ck, cd, cs, _ce in _block_ranges(seg):
        if cd == 1 and ck == key:
            if index is None or count == index:
                child_start, child_end = _find_block_bounds(seg, cs)
                return seg[:child_start] + new_text + seg[child_end:]
            count += 1
    if index is None or count == index:
        close = seg.rfind("}")
        if close >= 0:
            return seg[:close] + "\n\t" + new_text + "\n" + seg[close:]
    return None


def _remove_nth_child_in_seg(seg, key, index):
    """删除 seg 内第 N 个直接子块。"""
    count = 0
    for ck, cd, cs, _ce in _block_ranges(seg):
        if cd == 1 and ck == key:
            if count == index:
                child_start, child_end = _find_block_bounds(seg, cs)
                return seg[:child_start] + seg[child_end:]
            count += 1
    return seg


def _replace_mtth_modifier(seg, new_block_text):
    """替换 mean_time_to_happen 里的 modifier 子块。"""
    mtth = _child_block_text(seg, "mean_time_to_happen")
    if mtth is None:
        new_mtth = "mean_time_to_happen = {\n\t%s\n}" % new_block_text.strip()
        return _replace_child_in_seg(seg, "mean_time_to_happen", new_mtth)
    new_mtth = _replace_child_in_seg(mtth, "modifier", new_block_text)
    if new_mtth is None:
        new_mtth = mtth
    return _replace_child_in_seg(seg, "mean_time_to_happen", new_mtth, index=0)


def replace_nth_child(content, event_id, child_key, index, new_block_text):
    """替换事件块内第 N 个同名直接子块（用于 option 按索引定位）。"""
    bounds = _event_block(content, event_id)
    if bounds is None:
        return content
    start, end = bounds
    seg = content[start:end]
    new_seg = _replace_child_in_seg(seg, child_key, new_block_text, index=index)
    if new_seg is None:
        return content
    return content[:start] + new_seg + content[end:]


def remove_nth_child(content, event_id, child_key, index):
    """删除事件块内第 N 个同名直接子块。"""
    bounds = _event_block(content, event_id)
    if bounds is None:
        return content
    start, end = bounds
    seg = content[start:end]
    new_seg = _remove_nth_child_in_seg(seg, child_key, index)
    if new_seg == seg:
        return content
    return content[:start] + new_seg + content[end:]


def apply_event_edits(content, event_id, fields=None, blocks=None,
                      options=None, other_fields=None):
    """对事件块应用一批编辑，返回新内容。

    fields:      {key: (value, quoted)}；quoted 为 True 时写引号字符串
    blocks:      {block_key: full_block_text}（immediate/after/
                 mean_time_to_happen.modifier 等）
    options:     完整 option 块文本列表（含 `option = { ... }`），按序替换
    other_fields: [(key, raw_value)]；空字符串表示删除该行
    """
    bounds = _event_block(content, event_id)
    if bounds is None:
        return content
    start, end = bounds
    seg = content[start:end]

    for key, spec in (fields or {}).items():
        if isinstance(spec, (tuple, list)):
            value, quoted = spec[0], bool(spec[1]) if len(spec) > 1 else False
        else:
            value, quoted = spec, False
        seg = _replace_scalar_in_seg(seg, key, value, quoted=quoted)

    for key, text in (blocks or {}).items():
        if key == "mean_time_to_happen.modifier":
            seg = _replace_mtth_modifier(seg, text)
        elif key == "mean_time_to_happen.days":
            mtth = _child_block_text(seg, "mean_time_to_happen")
            if mtth is None:
                mtth = "mean_time_to_happen = {\n\tdays = %s\n}" % text
                seg = _replace_child_in_seg(seg, "mean_time_to_happen", mtth)
            else:
                mtth = _replace_scalar_in_seg(mtth, "days", text,
                                              quoted=False)
                seg = _replace_child_in_seg(seg, "mean_time_to_happen", mtth,
                                            index=0)
        else:
            changed = _replace_child_in_seg(seg, key, text)
            if changed is not None:
                seg = changed

    if options is not None:
        current_count = _count_options(seg)
        for i, opt_text in enumerate(options):
            opt_text = str(opt_text).strip()
            if opt_text and not opt_text.startswith("option"):
                opt_text = "option = {\n%s\n}" % opt_text
            if i < current_count:
                seg = _replace_child_in_seg(seg, "option", opt_text, index=i)
            else:
                seg = _replace_child_in_seg(seg, "option", opt_text)
                current_count += 1
        for i in range(current_count - 1, len(options) - 1, -1):
            seg = _remove_nth_child_in_seg(seg, "option", i)

    for key, raw_value in (other_fields or []):
        if not key:
            continue
        if raw_value == "":
            seg = re.sub(r'(?m)^\t%s\s*=.*$' % re.escape(key), "", seg)
        else:
            pat = re.compile(r'(?m)^(\t%s\s*=).*$' % re.escape(key))
            if pat.search(seg):
                seg = pat.sub(r"\1 " + raw_value, seg)
            else:
                seg = _replace_scalar_in_seg(seg, key, raw_value, quoted=False)

    return content[:start] + seg + content[end:]


# ---------- CRUD ----------

def _event_block_text(content, event_id):
    bounds = _event_block(content, event_id)
    if bounds is None:
        return None
    return content[bounds[0]:bounds[1]]


def delete_event(content, event_id):
    """删除指定 id 的事件块（顶层块内字段匹配）。"""
    bounds = _event_block(content, event_id)
    if bounds is None:
        return content
    bs, be = bounds
    before = content[:bs].rstrip()
    after = content[be:].lstrip("\n")
    if before and after:
        return before + "\n\n" + after
    return before + after


def rename_event(content, old_id, new_id):
    """重命名事件 id 字段。"""
    bounds = _event_block(content, old_id)
    if bounds is None:
        return content
    start, end = bounds
    seg = content[start:end]
    new_seg = _replace_scalar_in_seg(seg, "id", new_id, quoted=False)
    return content[:start] + new_seg + content[end:]


def duplicate_event(content, event_id, new_id):
    """复制事件块并换新 id。"""
    block_text = _event_block_text(content, event_id)
    if block_text is None:
        return content
    new_text = _replace_scalar_in_seg(block_text, "id", new_id, quoted=False)
    return insert_top_block(content, new_text, after_id=_EVENT_KEYS[0]
                            if not _top_key_of(content, event_id) else None)


def _top_key_of(content, event_id):
    bounds = _event_block(content, event_id)
    if bounds is None:
        return ""
    # 定位 block 开头的 key
    seg = content[bounds[0]:bounds[1]]
    m = re.match(r'\s*([\w\.\-]+)\s*=', seg)
    return m.group(1) if m else ""


def insert_event(content, event_id, event_type="country_event", namespace=""):
    """新建事件块。"""
    lines = ["%s = {" % event_type, "\tid = %s" % event_id]
    if namespace:
        lines.append("\tnamespace = %s" % namespace)
    lines.append("}")
    return insert_top_block(content, "\n".join(lines))
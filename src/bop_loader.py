"""力量平衡（Balance of Power）数据层

解析 HOI4 的 `common/bop/*.txt` 定义，并关联 `common/decisions/*.txt`
中对应决策分类下的动作（决议），供 BOP 专用工作台使用。

数据来源：
  - BOP 定义：common/bop/<TAG>.txt（mod 优先）
  - 动作列表：common/decisions/<TAG>.txt 等文件中 `category = <decision_category>`
    的顶层决议块

只读为主；保存 initial_value 时由调用方走 ensure_file_in_mod + 原子写。
"""

from __future__ import annotations

import os
import re

from tree_node import parse_pdx_text_to_nodes
from oob_loader import _block_ranges
from ai_loader import _find_block_bounds, _top_block


# ---------- 缓存 ----------

_BOP_CACHE = {}


def _clear_cache():
    _BOP_CACHE.clear()


def _node_value(node, key):
    """取块节点的直接 value 子节点值。"""
    for c in node.children:
        if c.node_type == "value" and c.key == key:
            return c.value
    return None


def _node_block(node, key):
    """取块节点的直接 block 子节点。"""
    for c in node.children:
        if c.node_type == "block" and c.key == key:
            return c
    return None


def _to_float(v, default=0.0):
    try:
        return float(str(v).replace('"', "").strip())
    except Exception:
        return default


def _parse_modifier(node):
    """modifier = { key = value ... } → dict。"""
    out = {}
    if node is None:
        return out
    for c in node.children:
        if c.node_type == "value":
            out[c.key] = _to_float(c.value)
    return out


def _parse_range(node):
    """range = { id/min/max/modifier/on_activate/on_deactivate }。"""
    return {
        "id": _node_value(node, "id") or "",
        "min": _to_float(_node_value(node, "min")),
        "max": _to_float(_node_value(node, "max")),
        "modifier": _parse_modifier(_node_block(node, "modifier")),
        "on_activate": _node_block(node, "on_activate"),
        "on_deactivate": _node_block(node, "on_deactivate"),
    }


def _parse_side(node):
    """side = { id/icon/range... }。"""
    ranges = []
    for c in node.children:
        if c.node_type == "block" and c.key == "range":
            ranges.append(_parse_range(c))
    return {
        "id": _node_value(node, "id") or "",
        "icon": _node_value(node, "icon") or "",
        "ranges": ranges,
    }


def parse_bop_file(content):
    """解析单个 BOP 文件文本，返回 BOP dict；无则 None。"""
    for node in parse_pdx_text_to_nodes(content):
        if node.node_type != "block":
            continue
        bop = {
            "id": node.key,
            "initial_value": _to_float(_node_value(node, "initial_value")),
            "left_side": _node_value(node, "left_side") or "",
            "right_side": _node_value(node, "right_side") or "",
            "decision_category": _node_value(node, "decision_category") or "",
            "ranges": [],
            "sides": [],
        }
        for c in node.children:
            if c.node_type != "block":
                continue
            if c.key == "range":
                bop["ranges"].append(_parse_range(c))
            elif c.key == "side":
                bop["sides"].append(_parse_side(c))
        return bop
    return None


def load_bop_definitions(mod_path, hoi4_path):
    """扫描 common/bop/*.txt（mod 优先），返回 {TAG: bop_dict}。"""
    cache_key = (mod_path or "", hoi4_path or "")
    if cache_key in _BOP_CACHE:
        return _BOP_CACHE[cache_key]
    out = {}
    for base, src in ((mod_path, "mod"), (hoi4_path, "game")):
        if not base or not os.path.isdir(base):
            continue
        d = os.path.join(base, "common", "bop")
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".txt"):
                continue
            tag = os.path.splitext(name)[0]
            if tag in out:
                continue  # mod 优先
            fp = os.path.join(d, name)
            try:
                with open(fp, "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            bop = parse_bop_file(content)
            if not bop:
                continue
            bop["tag"] = tag
            bop["file"] = fp
            bop["src"] = src
            bop["rel"] = os.path.join("common", "bop", name).replace("\\", "/")
            out[tag] = bop
    _BOP_CACHE[cache_key] = out
    return out


def _extract_delta_from_text(block_text):
    """从决议块文本中提取 BOP 数值变化（仅用于展示）。

    优先累加 `add_power_balance_value = { ... value = X }`；
    否则识别 `*_increase_effect` / `*_decrease_effect` 脚本效果名。
    """
    vals = []
    for m in re.finditer(
            r"add_power_balance_value\s*=\s*\{[^}]*?value\s*=\s*(-?[\d.]+)",
            block_text):
        try:
            vals.append(float(m.group(1)))
        except Exception:
            pass
    if vals:
        return sum(vals)
    if re.search(r"\b\w*_increase_effect\s*=\s*yes", block_text):
        return 1  # 方向：增加
    if re.search(r"\b\w*_decrease_effect\s*=\s*yes", block_text):
        return -1  # 方向：减少
    return None


def _parse_decision_action(key, block_text, loc_manager=None):
    """解析一个顶层决议块为动作 dict。"""
    name = ""
    if loc_manager is not None:
        try:
            name = loc_manager.get_name(key) or ""
        except Exception:
            name = ""
    cost = None
    nodes = parse_pdx_text_to_nodes(block_text)
    for node in nodes:
        if node.node_type != "block":
            continue
        cost_v = _node_value(node, "cost")
        if cost_v is not None:
            cost = str(cost_v).strip()
        break
    delta = _extract_delta_from_text(block_text)
    return {
        "key": key,
        "name": name or key,
        "cost": cost,
        "delta": delta,
        "raw": block_text,
    }


def load_bop_actions(mod_path, hoi4_path, decision_category,
                     loc_manager=None):
    """扫描决策文件，返回属于该 BOP 分类的动作列表（mod 优先去重）。

    原版决策结构：分类块 `ITA_balance_of_power_category = { ... }` 内部
    直接包含决议块，因此需要先定位深度 0 的分类块，再取其深度 1 子块。
    """
    if not decision_category:
        return []
    actions = []
    seen = set()
    for base in (mod_path, hoi4_path):
        if not base or not os.path.isdir(base):
            continue
        d = os.path.join(base, "common", "decisions")
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".txt"):
                continue
            fp = os.path.join(d, name)
            try:
                with open(fp, "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for key, depth, start, end in _block_ranges(content):
                if depth != 0 or key != decision_category:
                    continue
                cat_text = content[start:end]
                for k2, d2, s2, e2 in _block_ranges(cat_text):
                    if d2 != 1:
                        continue
                    if k2.startswith("DEBUG_"):
                        continue
                    block_text = cat_text[s2:e2]
                    if k2 in seen:
                        continue
                    action = _parse_decision_action(
                        k2, block_text, loc_manager)
                    if action:
                        action["file"] = fp
                        seen.add(k2)
                        actions.append(action)
    return actions


def find_active_range(bop, value):
    """返回当前值命中的 (side, range)；无命中返回 (None, None)。

    side 为 side dict（可能为 None 表示 BOP 顶层 range）。
    """
    for side in bop.get("sides", []):
        for rng in side.get("ranges", []):
            if rng["min"] <= value <= rng["max"]:
                return side, rng
    for rng in bop.get("ranges", []):
        if rng["min"] <= value <= rng["max"]:
            return None, rng
    return None, None


def _state_label(bop, value):
    """根据 BOP 当前值返回所在 side/range 的展示标签。"""
    side, rng = find_active_range(bop, value)
    if side is not None:
        return side.get("id", "") or (rng or {}).get("id", "")
    if rng is not None:
        return rng.get("id", "")
    return ""


# ---------- 保存写回（下沉自 BopEditorDialog） ----------

def _replace_bop_fields_in_content(content, replacements):
    """替换 BOP 顶层字段值；返回 (new_content, count)。"""
    new_content = content
    n = 0
    for field, val in replacements.items():
        if val is None:
            continue
        if field == "initial_value":
            pattern = r"(\binitial_value\s*=\s*)[-0-9.]+"
        else:
            pattern = r"(\b%s\s*=\s*)[^\s#]+" % re.escape(field)
        new_content, cnt = re.subn(
            pattern, lambda m: m.group(1) + str(val), new_content, count=1)
        n += cnt
    return new_content, n


def set_bop_initial_value(mod_path, hoi4_path, bop_id, value):
    """保存 BOP initial_value（自动确保文件在 mod 内）。

    Returns:
        dict: {ok, message, file, copied}
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("initial_value 必须为数值")
    return _set_bop_fields(mod_path, hoi4_path, bop_id,
                           {"initial_value": "%.4f" % value})


def set_bop_fields(mod_path, hoi4_path, bop_id, left_side=None,
                   right_side=None, decision_category=None):
    """保存 BOP 基础字段（可部分更新）。"""
    return _set_bop_fields(mod_path, hoi4_path, bop_id, {
        "left_side": left_side,
        "right_side": right_side,
        "decision_category": decision_category,
    })


def _set_bop_fields(mod_path, hoi4_path, bop_id, replacements):
    from state_build_ops import ensure_file_in_mod
    bops = load_bop_definitions(mod_path, hoi4_path)
    bop = (bops.get((bop_id or "").strip().upper())
           or bops.get(bop_id or ""))
    if bop is None:
        for b in bops.values():
            if b.get("id") == bop_id or b.get("tag") == bop_id:
                bop = b
                break
    if not bop:
        raise ValueError("未找到 BOP: %s" % bop_id)
    rel = bop.get("rel", "")
    fp, copied = ensure_file_in_mod(mod_path, hoi4_path, rel)
    if not fp:
        raise ValueError("无法定位 BOP 文件")
    with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
        content = f.read()
    new_content, n = _replace_bop_fields_in_content(content, replacements)
    if n == 0:
        raise ValueError("未找到任何可保存的 BOP 字段")
    from write_utils import atomic_write_text
    atomic_write_text(fp, new_content)
    _clear_cache()
    return {"ok": True, "message": "copied_written" if copied else "written",
            "file": rel, "copied": copied, "count": n}


def _find_top_block(content, key):
    """返回顶层块 key 的 (start, end)。"""
    for k, depth, start, end in _block_ranges(content):
        if depth == 0 and k == key:
            return start, end
    return None


def _replace_nested_scalar(seg, key, value):
    pat = re.compile(r'\b' + re.escape(key) + r'\s*=\s*[-0-9.]+')
    if pat.search(seg):
        return pat.sub('%s = %s' % (key, value), seg, count=1)
    return seg


def _update_bop_block(mod_path, hoi4_path, bop_id, updater):
    """定位 BOP 顶层块，调用 updater(block)->new_block，写回。"""
    from state_build_ops import ensure_file_in_mod
    from write_utils import atomic_write_text
    bops = load_bop_definitions(mod_path, hoi4_path)
    bop = (bops.get((bop_id or '').strip().upper())
           or bops.get(bop_id or ''))
    if bop is None:
        for b in bops.values():
            if b.get('id') == bop_id or b.get('tag') == bop_id:
                bop = b
                break
    if not bop:
        raise ValueError('未找到 BOP: %s' % bop_id)
    rel = bop.get('rel', '')
    fp, copied = ensure_file_in_mod(mod_path, hoi4_path, rel)
    with open(fp, 'r', encoding='utf-8-sig', errors='ignore') as f:
        content = f.read()
    span = _find_top_block(content, bop.get('id') or bop_id)
    if span is None:
        # 可能在文件中以 TAG 顶层块存在；按 rel 文件名前缀回退
        base = os.path.splitext(os.path.basename(rel))[0]
        span = _find_top_block(content, base)
    if span is None:
        raise ValueError('未定位到 BOP 块')
    start, end = span
    block = content[start:end]
    new_block = updater(block)
    atomic_write_text(fp, content[:start] + new_block + content[end:])
    _clear_cache()
    return {'ok': True, 'message': 'copied_written' if copied else 'written',
            'file': rel, 'copied': copied}


def _find_range_info(block, bop_id, range_id):
    """在 BOP 顶层块文本中定位指定 range（含 side 内嵌），返回区间信息。"""
    top = _top_block(block, bop_id)
    if top is None:
        return None
    top_start, top_end = top
    top_text = block[top_start:top_end]
    current_side = None
    for k, depth, bs, _be in _block_ranges(top_text):
        if depth == 1 and k == "side":
            s, e = _find_block_bounds(top_text, bs)
            seg = top_text[s:e]
            m = re.search(r"\bid\s*=\s*([^\s#]+)", seg)
            current_side = m.group(1) if m else ""
            continue
        if depth == 1 and k != "side":
            current_side = None
        if k == "range" and depth in (1, 2):
            abs_s = top_start + bs
            abs_e = _find_block_bounds(block, abs_s)[1]
            seg = block[abs_s:abs_e]
            if re.search(r"\bid\s*=\s*" + re.escape(range_id) + r"\b", seg):
                return {
                    "start": abs_s,
                    "end": abs_e,
                    "text": seg,
                    "side_id": current_side if depth == 2 else None,
                }
    return None


def _find_side_info(block, side_id):
    """在 BOP 顶层块文本中定位指定 side 块。"""
    for k, depth, bs, _be in _block_ranges(block):
        if depth == 1 and k == "side":
            s, e = _find_block_bounds(block, bs)
            seg = block[s:e]
            if re.search(r"\bid\s*=\s*" + re.escape(side_id) + r"\b", seg):
                return {"start": s, "end": e, "text": seg}
    return None


def _modifier_block_text(modifiers):
    """modifiers dict → `modifier = { ... }` 单行文本。"""
    body = " ".join("%s = %s" % (k, v) for k, v in (modifiers or {}).items())
    return "modifier = { " + body + " }"


def _replace_modifier_block(seg, modifiers):
    """替换/插入 range 段内的 modifier 子块。"""
    new_mod = _modifier_block_text(modifiers)
    for k, depth, bs, _be in _block_ranges(seg):
        if depth == 1 and k == "modifier":
            s, e = _find_block_bounds(seg, bs)
            return seg[:s] + new_mod.strip() + seg[e:]
    m = re.search(r"(\bid\s*=\s*[^\n]+)", seg)
    if m:
        pos = m.end()
        return seg[:pos] + "\n\t\t" + new_mod + seg[pos:]
    close = seg.rfind("}")
    if close >= 0:
        return seg[:close] + "\n\t\t" + new_mod + "\n\t" + seg[close:]
    return seg


def _insert_range_into_block(block, range_text, side_id=None):
    """把 range 块插入 BOP 块内：side_id 存在时进该 side，否则顶层。"""
    range_text = range_text.strip()
    if not range_text:
        return block
    if side_id:
        for k, depth, bs, _be in _block_ranges(block):
            if depth == 1 and k == "side":
                s, e = _find_block_bounds(block, bs)
                seg = block[s:e]
                m = re.search(r"\bid\s*=\s*([^\s#]+)", seg)
                if m and m.group(1) == side_id:
                    close = block.rfind("}", s, e)
                    if close < 0:
                        return block
                    return (block[:close] + "\n\t\t" + range_text
                            + "\n\t" + block[close:])
        return block
    close = block.rfind("}")
    if close < 0:
        return block
    return block[:close] + "\n\t" + range_text + "\n" + block[close:]


def set_bop_range(mod_path, hoi4_path, bop_id, range_id, min_v=None,
                  max_v=None, modifiers=None):
    """保存 BOP 指定 range 的 min/max（可选 modifiers）。"""
    def updater(block):
        info = _find_range_info(block, bop_id, range_id)
        if info is None:
            return block
        seg = info["text"]
        if min_v is not None:
            seg = _replace_nested_scalar(seg, "min", min_v)
        if max_v is not None:
            seg = _replace_nested_scalar(seg, "max", max_v)
        if modifiers is not None:
            seg = _replace_modifier_block(seg, modifiers)
        return block[:info["start"]] + seg + block[info["end"]:]
    return _update_bop_block(mod_path, hoi4_path, bop_id, updater)


def set_bop_range_modifiers(mod_path, hoi4_path, bop_id, range_id, modifiers):
    """保存 BOP 指定 range 的 modifier 子块键值（整体替换）。"""
    return set_bop_range(mod_path, hoi4_path, bop_id, range_id,
                         min_v=None, max_v=None, modifiers=modifiers)


def insert_bop_range(mod_path, hoi4_path, bop_id, range_text, side_id=None):
    """在 BOP 中新增 range 块（默认顶层；side_id 指定时嵌套进该 side）。"""
    def updater(block):
        return _insert_range_into_block(block, range_text, side_id)
    return _update_bop_block(mod_path, hoi4_path, bop_id, updater)


def delete_bop_range(mod_path, hoi4_path, bop_id, range_id):
    """删除 BOP 中指定 range 块（顶层或 side 内嵌）。"""
    def updater(block):
        info = _find_range_info(block, bop_id, range_id)
        if info is None:
            return block
        s, e = info["start"], info["end"]
        while s > 0 and block[s - 1] in " \t":
            s -= 1
        if s > 0 and block[s - 1] == "\n":
            s -= 1
        return block[:s] + block[e:]
    return _update_bop_block(mod_path, hoi4_path, bop_id, updater)


def set_bop_range_side(mod_path, hoi4_path, bop_id, range_id, side_id=None):
    """移动 range 块到指定 side（side_id=None 表示顶层）。"""
    def updater(block):
        info = _find_range_info(block, bop_id, range_id)
        if info is None:
            return block
        if info["side_id"] == side_id:
            return block
        seg = info["text"]
        s, e = info["start"], info["end"]
        while s > 0 and block[s - 1] in " \t":
            s -= 1
        if s > 0 and block[s - 1] == "\n":
            s -= 1
        clean = block[:s] + block[e:]
        return _insert_range_into_block(clean, seg, side_id)
    return _update_bop_block(mod_path, hoi4_path, bop_id, updater)


def set_bop_side_fields(mod_path, hoi4_path, bop_id, side_id, icon=None,
                        loc_key=None):
    """保存 BOP 指定 side 的 icon 与本地化键（id）。

    loc_key 变化时会同步 BOP 顶层 left_side/right_side 引用。
    """
    def updater(block):
        info = _find_side_info(block, side_id)
        if info is None:
            return block
        seg = info["text"]
        if loc_key is not None and loc_key != side_id:
            seg = re.sub(
                r"(\bid\s*=\s*)" + re.escape(side_id) + r"\b",
                lambda m: m.group(1) + loc_key,
                seg, count=1)
        if icon is not None:
            pat = re.compile(r"\bicon\s*=\s*[^\s#]+")
            if pat.search(seg):
                seg = pat.sub("icon = %s" % icon, seg, count=1)
            else:
                m = re.search(r"(\bid\s*=\s*[^\n]+)", seg)
                if m:
                    pos = m.end()
                    seg = seg[:pos] + "\n\t\ticon = %s" % icon + seg[pos:]
        new_block = block[:info["start"]] + seg + block[info["end"]:]
        if loc_key is not None and loc_key != side_id:
            new_block = re.sub(
                r"(\b(?:left_side|right_side)\s*=\s*)"
                + re.escape(side_id) + r"\b",
                lambda m: m.group(1) + loc_key,
                new_block)
        return new_block
    return _update_bop_block(mod_path, hoi4_path, bop_id, updater)


def _find_decision_file(mod_path, hoi4_path, category):
    """在 common/decisions 下找包含顶层 category 块的文件。"""
    for base in (mod_path, hoi4_path):
        d = os.path.join(base or '', 'common', 'decisions')
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith('.txt'):
                continue
            fp = os.path.join(d, name)
            try:
                with open(fp, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    content = f.read()
            except Exception:
                continue
            if _find_top_block(content, category) is not None:
                return fp, content
    return None, None


def insert_bop_decision(mod_path, hoi4_path, category, block_text, action_id=None):
    """在决策分类块内插入决议块。

    Returns:
        dict: {ok, message, file}
    """
    from state_build_ops import ensure_file_in_mod
    from write_utils import atomic_write_text
    fp, content = _find_decision_file(mod_path, hoi4_path, category)
    if fp is None:
        # 没有已有分类块：在 mod 中新建文件
        fp = os.path.join(mod_path, 'common', 'decisions',
                          (category or 'bop_actions') + '.txt')
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        content = category + ' = {\n}\n'
        created = True
    else:
        if os.path.normcase(fp).startswith(os.path.normcase(mod_path or '')):
            pass
        else:
            rel = os.path.relpath(fp, hoi4_path).replace('\\', '/')
            fp, _ = ensure_file_in_mod(mod_path, hoi4_path, rel)
            with open(fp, 'r', encoding='utf-8-sig', errors='ignore') as f:
                content = f.read()
        created = False
    span = _find_top_block(content, category)
    if span is None:
        # 新建文件时一定存在；若仍无则拼在末尾
        content = content.rstrip() + '\n' + category + ' = {\n}\n'
        span = _find_top_block(content, category)
    start, end = span
    block = content[start:end]
    # 在闭合 } 前插入
    if block.rstrip().endswith('}'):
        pos = block.rfind('}')
        indent = '\n\t' if not block_text[:1].isspace() else '\n'
        block = (block[:pos] + indent + block_text.rstrip()
                 + '\n' + block[pos:])
    content = content[:start] + block + content[end:]
    atomic_write_text(fp, content)
    _clear_cache()
    return {'ok': True, 'message': 'created' if created else 'written',
            'file': os.path.relpath(fp, mod_path).replace('\\', '/')}


def delete_bop_decision(mod_path, hoi4_path, category, action_id):
    """从决策分类块内删除指定 action_id 决议块。"""
    from state_build_ops import ensure_file_in_mod
    from write_utils import atomic_write_text
    fp, content = _find_decision_file(mod_path, hoi4_path, category)
    if fp is None:
        return {'ok': False, 'message': 'not_found', 'file': ''}
    if not os.path.normcase(fp).startswith(os.path.normcase(mod_path or '')):
        rel = os.path.relpath(fp, hoi4_path).replace('\\', '/')
        fp, _ = ensure_file_in_mod(mod_path, hoi4_path, rel)
        with open(fp, 'r', encoding='utf-8-sig', errors='ignore') as f:
            content = f.read()
    span = _find_top_block(content, category)
    if span is None:
        return {'ok': False, 'message': 'not_found', 'file': ''}
    start, end = span
    block = content[start:end]
    # 删除 action_id 顶层子块
    for k, depth, s2, e2 in _block_ranges(block):
        if depth == 1 and k == action_id:
            # 删除连同缩进
            while s2 > 0 and block[s2 - 1] in ' \t':
                s2 -= 1
            if s2 > 0 and block[s2 - 1] == '\n':
                s2 -= 1
            block = block[:s2] + block[e2:]
            content = content[:start] + block + content[end:]
            atomic_write_text(fp, content)
            _clear_cache()
            return {'ok': True, 'message': 'written',
                    'file': os.path.relpath(fp, mod_path).replace('\\', '/')}
    return {'ok': False, 'message': 'not_found', 'file': ''}


# ---------- 决议/动作字段写回 ----------

def _writable_decision_file(mod_path, hoi4_path, category):
    """返回决策文件 (abs_path, content, copied)；原版自动复制到 mod。"""
    from state_build_ops import ensure_file_in_mod
    fp, content = _find_decision_file(mod_path, hoi4_path, category)
    if fp is None:
        return None, None, False
    if not os.path.normcase(fp).startswith(os.path.normcase(mod_path or '')):
        rel = os.path.relpath(fp, hoi4_path).replace('\\', '/')
        fp, _copied = ensure_file_in_mod(mod_path, hoi4_path, rel)
        if not fp:
            return None, None, False
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        copied = _copied
    else:
        copied = False
    return fp, content, copied


def _action_bounds(content, category, action_id):
    """返回分类块内指定 action 块的精确 (start, end)。"""
    top = _top_block(content, category)
    if top is None:
        return None
    top_start, top_end = top
    top_text = content[top_start:top_end]
    for ck, cd, cs, _ce in _block_ranges(top_text):
        if cd == 1 and ck == action_id:
            return _find_block_bounds(content, top_start + cs)
    return None


def _replace_action_scalar(action_text, field, value):
    """替换 action 块内简单标量；不存在则在块开头插入。"""
    pat = re.compile(r"(\b%s\s*=\s*)[^\n#]+" % re.escape(field))
    if pat.search(action_text):
        return pat.sub(lambda m: m.group(1) + str(value), action_text, count=1)
    brace = action_text.find("{")
    if brace >= 0:
        return (action_text[:brace + 1] + "\n\t\t%s = %s" % (field, value)
                + action_text[brace + 1:])
    return action_text


def _replace_action_add_power_balance(action_text, value, bop_id=None):
    """更新 action 内全部 add_power_balance_value 的 value；无则创建。"""
    found = False
    for k, _depth, bs, _be in _block_ranges(action_text):
        if k != "add_power_balance_value":
            continue
        s, e = _find_block_bounds(action_text, bs)
        seg = _replace_nested_scalar(action_text[s:e], "value", value)
        action_text = action_text[:s] + seg + action_text[e:]
        found = True
    if found:
        return action_text
    if bop_id:
        block = ("add_power_balance_value = {\n"
                 "\t\t\tid = %s\n"
                 "\t\t\tvalue = %s\n"
                 "\t\t}" % (bop_id, value))
        for k, depth, bs, _be in _block_ranges(action_text):
            if depth == 1 and k == "complete_effect":
                s, e = _find_block_bounds(action_text, bs)
                close = action_text.rfind("}", s, e)
                if close >= 0:
                    return (action_text[:close] + "\n\t\t\t" + block.strip()
                            + action_text[close:])
        # 没有 complete_effect：在 action 开头新建
        brace = action_text.find("{")
        if brace >= 0:
            ce_text = ("complete_effect = {\n\t\t\t" + block.strip()
                       + "\n\t\t}")
            return (action_text[:brace + 1] + "\n\t\t" + ce_text
                    + action_text[brace + 1:])
    return action_text


def set_bop_action_fields(mod_path, hoi4_path, category, action_id,
                          cost=None, add_power_balance_value=None,
                          bop_id=None):
    """保存决议动作的 cost / add_power_balance_value 字段。

    全部走 ensure_file_in_mod + atomic_write_text。
    """
    from write_utils import atomic_write_text
    if cost is None and add_power_balance_value is None:
        return {"ok": False, "message": "no_fields", "file": ""}
    fp, content, copied = _writable_decision_file(
        mod_path, hoi4_path, category)
    if fp is None:
        return {"ok": False, "message": "not_found", "file": ""}
    bounds = _action_bounds(content, category, action_id)
    if bounds is None:
        return {"ok": False, "message": "action_not_found", "file": ""}
    start, end = bounds
    action_text = content[start:end]
    if cost is not None:
        action_text = _replace_action_scalar(action_text, "cost", cost)
    if add_power_balance_value is not None:
        action_text = _replace_action_add_power_balance(
            action_text, add_power_balance_value, bop_id)
    content = content[:start] + action_text + content[end:]
    atomic_write_text(fp, content)
    _clear_cache()
    return {"ok": True,
            "message": "copied_written" if copied else "written",
            "file": os.path.relpath(fp, mod_path or "").replace("\\", "/")}


def set_bop_action_block(mod_path, hoi4_path, category, action_id,
                         block_key, block_text):
    """替换/新增决议分类块内 action 的直接子块（效果/触发等）。"""
    from write_utils import atomic_write_text
    fp, content, copied = _writable_decision_file(
        mod_path, hoi4_path, category)
    if fp is None:
        return {"ok": False, "message": "not_found", "file": ""}
    bounds = _action_bounds(content, category, action_id)
    if bounds is None:
        return {"ok": False, "message": "action_not_found", "file": ""}
    start, end = bounds
    action_text = content[start:end]
    new_text = block_text.strip()
    found = False
    for k, depth, bs, _be in _block_ranges(action_text):
        if depth == 1 and k == block_key:
            s, e = _find_block_bounds(action_text, bs)
            action_text = action_text[:s] + new_text + action_text[e:]
            found = True
            break
    if not found:
        close = action_text.rfind("}")
        if close >= 0:
            action_text = (action_text[:close] + "\n\t\t" + new_text
                           + "\n\t" + action_text[close:])
    content = content[:start] + action_text + content[end:]
    atomic_write_text(fp, content)
    _clear_cache()
    return {"ok": True,
            "message": "copied_written" if copied else "written",
            "file": os.path.relpath(fp, mod_path or "").replace("\\", "/")}


def upsert_bop_localisation(mod_path, entries):
    """批量 upsert BOP 本地化词条（沿用现有链，写入默认 mod yml）。

    entries: {key: 中文文本}；空值跳过。
    Returns:
        int: 实际写入词条数。
    """
    if not mod_path:
        return 0
    from localisation_editor_data import default_mod_loc_file, upsert_loc_entry
    fp = default_mod_loc_file(mod_path)
    if not fp:
        return 0
    count = 0
    for key, val in (entries or {}).items():
        if not key or val is None or not str(val).strip():
            continue
        if upsert_loc_entry(fp, key, str(val)):
            count += 1
    return count

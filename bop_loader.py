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


def _state_label(bop, value):
    """根据 BOP 当前值返回所在 side/range 的展示标签。"""
    for side in bop.get("sides", []):
        for rng in side.get("ranges", []):
            if rng["min"] <= value <= rng["max"]:
                return side.get("id", "") or rng.get("id", "")
    for rng in bop.get("ranges", []):
        if rng["min"] <= value <= rng["max"]:
            return rng.get("id", "")
    return ""

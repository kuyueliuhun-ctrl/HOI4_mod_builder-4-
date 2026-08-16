"""HOI4 AI 内容数据层

统一解析 `common/ai_*` 下的 AI 脚本，供 AI 专用编辑器使用。

覆盖：
  - ai_strategy_plans    AI 战略计划（国策顺序等）
  - ai_strategy          AI 战略倾向（type/id/value 表）
  - ai_templates         AI 师模板（role + target_template）
  - ai_equipment         AI 装备设计（target_variant + allowed_modules）
  - ai_navy              海军目标/舰队/特遣队
  - ai_areas             战略区域分组
  - ai_focuses           科研权重
  - ai_faction_theaters  派系战区（regions + 条件）

所有读取均 mod 优先；写入由调用方走 ensure_file_in_mod + 原子写。
"""

from __future__ import annotations

import os
import re

from oob_loader import _block_ranges
from tree_node import parse_pdx_text_to_nodes


# ---------- 缓存 ----------

_AI_CACHE = {}


def _clear_cache():
    _AI_CACHE.clear()


# ---------- 基础解析辅助 ----------

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


def _scan_files(mod_path, hoi4_path, rel_dir, ext=".txt"):
    """扫描 mod/游戏下某个相对目录，返回文件绝对路径列表（mod 优先去重）。"""
    out = []
    seen = set()
    for base in (mod_path, hoi4_path):
        if not base or not os.path.isdir(base):
            continue
        d = os.path.join(base, rel_dir)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(ext):
                continue
            fp = os.path.join(d, name)
            real = os.path.realpath(fp)
            if real in seen:
                continue
            seen.add(real)
            out.append(fp)
    return out


def _read(fp):
    try:
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _cached(kind, mod_path, hoi4_path, loader):
    key = (kind, mod_path or "", hoi4_path or "")
    if key in _AI_CACHE:
        return _AI_CACHE[key]
    data = loader()
    _AI_CACHE[key] = data
    return data


# ---------- AI 战略计划 ----------

def parse_ai_plans(content):
    """解析 ai_strategy_plans/*.txt，返回 {plan_id: plan_dict}。"""
    plans = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        plans[key] = {
            "id": key,
            "name": f.get("name", ""),
            "desc": f.get("desc", ""),
            "allowed": _child_block_text(bt, "allowed"),
            "enable": _child_block_text(bt, "enable"),
            "abort": _child_block_text(bt, "abort"),
            "ai_national_focuses": _values_in_block(bt, "ai_national_focuses"),
            "focus_factors": _child_block_text(bt, "focus_factors"),
            "research": _child_block_text(bt, "research"),
            "ideas": _child_block_text(bt, "ideas"),
            "weight": _child_block_text(bt, "weight"),
            "raw": bt,
        }
    return plans


def load_ai_plans(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/ai_strategy_plans"):
            content = _read(fp)
            for pid, plan in parse_ai_plans(content).items():
                plan["file"] = fp
                plan["rel"] = os.path.relpath(fp, hoi4_path or mod_path or os.path.dirname(fp)).replace("\\", "/")
                out[pid] = plan
        return out
    return _cached("ai_plans", mod_path, hoi4_path, loader)


# ---------- AI 战略倾向 ----------

def parse_ai_strategies(content):
    """解析 ai_strategy/*.txt，返回 {group_id: group_dict}。"""
    groups = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        entries = []
        for ck, cs, ce in _child_blocks(bt):
            if ck != "ai_strategy":
                continue
            cf = _fields(bt[cs:ce])
            entries.append({
                "type": cf.get("type", ""),
                "id": cf.get("id", ""),
                "value": cf.get("value", ""),
            })
        groups[key] = {
            "id": key,
            "allowed": _child_block_text(bt, "allowed"),
            "enable": _child_block_text(bt, "enable"),
            "abort": _child_block_text(bt, "abort"),
            "strategies": entries,
            "raw": bt,
        }
    return groups


def load_ai_strategies(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/ai_strategy"):
            content = _read(fp)
            for gid, g in parse_ai_strategies(content).items():
                g["file"] = fp
                g["rel"] = os.path.relpath(fp, hoi4_path or mod_path or os.path.dirname(fp)).replace("\\", "/")
                out[gid] = g
        return out
    return _cached("ai_strategies", mod_path, hoi4_path, loader)


# ---------- AI 师模板 ----------

def parse_ai_templates(content):
    """解析 ai_templates/*.txt，返回 {role_id: role_dict}。"""
    roles = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        targets = []
        for ck, cs, ce in _child_blocks(bt):
            if ck in ("blocked_for", "available_for", "upgrade_prio"):
                continue
            cbt = bt[cs:ce]
            cf = _fields(cbt)
            targets.append({
                "id": ck,
                "upgrade_prio": _child_block_text(cbt, "upgrade_prio"),
                "target_template": _child_block_text(cbt, "target_template"),
                "replace_with": cf.get("replace_with", ""),
                "replace_at_match": cf.get("replace_at_match", ""),
                "target_min_match": cf.get("target_min_match", ""),
                "enable": _child_block_text(cbt, "enable"),
                "can_upgrade_in_field": _child_block_text(cbt, "can_upgrade_in_field"),
                "raw": cbt,
            })
        roles[key] = {
            "id": key,
            "blocked_for": _values_in_block(bt, "blocked_for"),
            "available_for": _values_in_block(bt, "available_for"),
            "role": f.get("role", ""),
            "upgrade_prio": _child_block_text(bt, "upgrade_prio"),
            "targets": targets,
            "raw": bt,
        }
    return roles


def load_ai_templates(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/ai_templates"):
            content = _read(fp)
            for rid, role in parse_ai_templates(content).items():
                role["file"] = fp
                role["rel"] = os.path.relpath(fp, hoi4_path or mod_path or os.path.dirname(fp)).replace("\\", "/")
                out[rid] = role
        return out
    return _cached("ai_templates", mod_path, hoi4_path, loader)


# ---------- AI 装备 ----------

def parse_ai_equipment(content):
    """解析 ai_equipment/*.txt，返回 {design_group: dict}。"""
    groups = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        variants = []
        for ck, cs, ce in _child_blocks(bt):
            if ck in ("category", "available_for", "blocked_for", "roles", "priority"):
                continue
            cbt = bt[cs:ce]
            cf = _fields(cbt)
            variants.append({
                "id": ck,
                "priority": _child_block_text(cbt, "priority"),
                "history": cf.get("history", ""),
                "target_variant": _child_block_text(cbt, "target_variant"),
                "allowed_modules": _child_block_text(cbt, "allowed_modules"),
                "raw": cbt,
            })
        groups[key] = {
            "id": key,
            "category": f.get("category", ""),
            "available_for": _values_in_block(bt, "available_for"),
            "blocked_for": _values_in_block(bt, "blocked_for"),
            "roles": _values_in_block(bt, "roles"),
            "priority": _child_block_text(bt, "priority"),
            "variants": variants,
            "raw": bt,
        }
    return groups


def load_ai_equipment(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/ai_equipment"):
            content = _read(fp)
            for gid, g in parse_ai_equipment(content).items():
                g["file"] = fp
                g["rel"] = os.path.relpath(fp, hoi4_path or mod_path or os.path.dirname(fp)).replace("\\", "/")
                out[gid] = g
        return out
    return _cached("ai_equipment", mod_path, hoi4_path, loader)


# ---------- AI 海军 ----------

def parse_ai_navy_goals(content):
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        out[key] = {
            "id": key,
            "objective_type": f.get("objective_type", ""),
            "available_for": _values_in_block(bt, "available_for"),
            "blocked_for": _values_in_block(bt, "blocked_for"),
            "min_priority": f.get("min_priority", ""),
            "max_priority": f.get("max_priority", ""),
            "raw": bt,
        }
    return out


def parse_ai_navy_fleets(content):
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        out[key] = {
            "id": key,
            "required_taskforces": _map_values_in_block(bt, "required_taskforces"),
            "optional_taskforces": _map_values_in_block(bt, "optional_taskforces"),
            "raw": bt,
        }
    return out


def parse_ai_navy_taskforces(content):
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        out[key] = {
            "id": key,
            "allowed": _child_block_text(bt, "allowed"),
            "ai_will_do": _child_block_text(bt, "ai_will_do"),
            "keep_updated": f.get("keep_updated", ""),
            "mission": _values_in_block(bt, "mission"),
            "min_composition": _map_values_in_block(bt, "min_composition"),
            "optimal_composition": _map_values_in_block(bt, "optimal_composition"),
            "raw": bt,
        }
    return out


def load_ai_navy(mod_path="", hoi4_path=""):
    def loader():
        return {
            "goals": _load_navy_goals(mod_path, hoi4_path),
            "fleets": _load_navy_fleets(mod_path, hoi4_path),
            "taskforces": _load_navy_taskforces(mod_path, hoi4_path),
        }
    return _cached("ai_navy", mod_path, hoi4_path, loader)


def _load_navy_goals(mod_path, hoi4_path):
    out = {}
    for fp in _scan_files(mod_path, hoi4_path, "common/ai_navy/goals"):
        for gid, g in parse_ai_navy_goals(_read(fp)).items():
            g["file"] = fp
            g["rel"] = os.path.relpath(fp, hoi4_path or mod_path or os.path.dirname(fp)).replace("\\", "/")
            out[gid] = g
    return out


def _load_navy_fleets(mod_path, hoi4_path):
    out = {}
    for fp in _scan_files(mod_path, hoi4_path, "common/ai_navy/fleet"):
        for fid, f in parse_ai_navy_fleets(_read(fp)).items():
            f["file"] = fp
            f["rel"] = os.path.relpath(fp, hoi4_path or mod_path or os.path.dirname(fp)).replace("\\", "/")
            out[fid] = f
    return out


def _load_navy_taskforces(mod_path, hoi4_path):
    out = {}
    for fp in _scan_files(mod_path, hoi4_path, "common/ai_navy/taskforce"):
        for tid, t in parse_ai_navy_taskforces(_read(fp)).items():
            t["file"] = fp
            t["rel"] = os.path.relpath(fp, hoi4_path or mod_path or os.path.dirname(fp)).replace("\\", "/")
            out[tid] = t
    return out


# ---------- AI 区域 ----------

def parse_ai_areas(content):
    """解析 ai_areas/*.txt，支持 `areas = { name = { strategic_regions = {...} } }`。"""
    areas = {}
    for key, depth, start, end in _block_ranges(content):
        if depth == 0 and key == "areas":
            bt = content[start:end]
            for ck, cs, ce in _child_blocks(bt):
                cbt = bt[cs:ce]
                areas[ck] = {
                    "id": ck,
                    "strategic_regions": _values_in_block(cbt, "strategic_regions"),
                    "raw": cbt,
                }
            break
    return areas


def load_ai_areas(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/ai_areas"):
            for aid, a in parse_ai_areas(_read(fp)).items():
                a["file"] = fp
                a["rel"] = os.path.relpath(fp, hoi4_path or mod_path or os.path.dirname(fp)).replace("\\", "/")
                out[aid] = a
        return out
    return _cached("ai_areas", mod_path, hoi4_path, loader)


# ---------- AI 科研权重 ----------

def parse_ai_focuses(content):
    """解析 ai_focuses/*.txt，返回 {block_id: {research: {tech: weight}}}。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        research = _map_values_in_block(bt, "research")
        out[key] = {
            "id": key,
            "research": research,
            "raw": bt,
        }
    return out


def load_ai_focuses(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/ai_focuses"):
            for bid, b in parse_ai_focuses(_read(fp)).items():
                b["file"] = fp
                b["rel"] = os.path.relpath(fp, hoi4_path or mod_path or os.path.dirname(fp)).replace("\\", "/")
                out[bid] = b
        return out
    return _cached("ai_focuses", mod_path, hoi4_path, loader)


# ---------- AI 派系战区 ----------

def parse_ai_faction_theaters(content):
    """解析 ai_faction_theaters/*.txt，返回 {theater_id: dict}。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        out[key] = {
            "id": key,
            "name": f.get("name", ""),
            "regions": _values_in_block(bt, "regions"),
            "cancel": _child_block_text(bt, "cancel"),
            "ai_will_do": _child_block_text(bt, "ai_will_do"),
            "can_skip_first_region": f.get("can_skip_first_region", ""),
            "preferred_countries": _values_in_block(bt, "preferred_countries"),
            "raw": bt,
        }
    return out


def load_ai_faction_theaters(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/ai_faction_theaters"):
            for tid, t in parse_ai_faction_theaters(_read(fp)).items():
                t["file"] = fp
                t["rel"] = os.path.relpath(fp, hoi4_path or mod_path or os.path.dirname(fp)).replace("\\", "/")
                out[tid] = t
        return out
    return _cached("ai_faction_theaters", mod_path, hoi4_path, loader)

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
from ai_loader_crud import (
    _child_block_text,
    _child_blocks,
    _fields,
    _find_block_bounds,
    _inner_block_text,
    _map_values_in_block,
    _node_block,
    _node_value,
    _values_in_block,
)


# ---------- 缓存 ----------

_AI_CACHE = {}


def _clear_cache():
    _AI_CACHE.clear()


# ---------- 基础解析辅助 ----------

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
            entry = {
                "type": cf.get("type", ""),
                "id": cf.get("id", ""),
                "value": cf.get("value", ""),
            }
            for extra in ("operation", "mission", "operation_target",
                          "mission_target", "num_operatives", "state"):
                entry[extra] = cf.get(extra, "")
            entries.append(entry)
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


# ---------- AI 态度 ----------

def parse_ai_attitudes(content):
    """解析 ai_attitudes/*.txt，返回 {id: {flag: value, ...}}。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_ai_attitudes(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/ai_attitudes"):
            for aid, a in parse_ai_attitudes(_read(fp)).items():
                a["file"] = fp
                a["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[aid] = a
        return out
    return _cached("ai_attitudes", mod_path, hoi4_path, loader)


def parse_ai_personalities(content):
    """解析 ai_personalities/*.txt：每个顶层块 = 一个 AI 人格（标量字段集）。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_ai_personalities(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/ai_personalities"):
            for pid, p in parse_ai_personalities(_read(fp)).items():
                p["file"] = fp
                p["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[pid] = p
        return out
    return _cached("ai_personalities", mod_path, hoi4_path, loader)


def parse_mio_ai_weights(content):
    """解析 mio_ai_weights/*.txt：每个顶层块 = 一个 MIO 权重（标量字段集）。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_mio_ai_weights(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/mio_ai_weights"):
            for wid, w in parse_mio_ai_weights(_read(fp)).items():
                w["file"] = fp
                w["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[wid] = w
        return out
    return _cached("mio_ai_weights", mod_path, hoi4_path, loader)


def parse_ai_peace(content):
    """解析 ai_peace/*.txt：每个顶层块 = 一个 AI 和平策略（标量字段集）。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_ai_peace(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/ai_peace"):
            for pid, p in parse_ai_peace(_read(fp)).items():
                p["file"] = fp
                p["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[pid] = p
        return out
    return _cached("ai_peace", mod_path, hoi4_path, loader)


def parse_special_projects(content):
    """解析 special_projects/*.txt：每个顶层块 = 一个特殊项目（标量字段集）。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_special_projects(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/special_projects"):
            for pid, p in parse_special_projects(_read(fp)).items():
                p["file"] = fp
                p["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[pid] = p
        return out
    return _cached("special_projects", mod_path, hoi4_path, loader)


def parse_unit_tags(content):
    """解析 unit_tags/*.txt：每个顶层块 = 一个部队标签（标量字段集）。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_unit_tags(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/unit_tags"):
            for uid, u in parse_unit_tags(_read(fp)).items():
                u["file"] = fp
                u["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[uid] = u
        return out
    return _cached("unit_tags", mod_path, hoi4_path, loader)


def parse_state_categories(content):
    """解析 state_category/*.txt：每个顶层块 = 一个州类别（标量字段集）。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_state_categories2(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/state_category"):
            for cid, c in parse_state_categories(_read(fp)).items():
                c["file"] = fp
                c["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[cid] = c
        return out
    return _cached("state_categories2", mod_path, hoi4_path, loader)


def parse_resources(content):
    """解析 resources/*.txt：每个顶层块 = 一个资源定义（标量字段集）。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_resources2(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/resources"):
            for rid, r in parse_resources(_read(fp)).items():
                r["file"] = fp
                r["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[rid] = r
        return out
    return _cached("resources2", mod_path, hoi4_path, loader)


def parse_equipment_groups(content):
    """解析 equipment_groups/*.txt：每个顶层块 = 一个装备组（标量字段集）。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_equipment_groups2(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/equipment_groups"):
            for gid, g in parse_equipment_groups(_read(fp)).items():
                g["file"] = fp
                g["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[gid] = g
        return out
    return _cached("equipment_groups2", mod_path, hoi4_path, loader)


def parse_script_constants(content):
    """解析 script_constants/*.txt：每个顶层块 = 一个常量（标量字段集）。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_script_constants(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/script_constants"):
            for cid, c in parse_script_constants(_read(fp)).items():
                c["file"] = fp
                c["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[cid] = c
        return out
    return _cached("script_constants", mod_path, hoi4_path, loader)


def parse_scripted_localisation(content):
    """解析 scripted_localisation/*.txt：每个顶层块 = 一条脚本化本地化。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_scripted_localisation(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/scripted_localisation"):
            for lid, l in parse_scripted_localisation(_read(fp)).items():
                l["file"] = fp
                l["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[lid] = l
        return out
    return _cached("scripted_localisation", mod_path, hoi4_path, loader)


def parse_technology_sharing(content):
    """解析 technology_sharing/*.txt：每个顶层块 = 一个科技共享组。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_technology_sharing(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/technology_sharing"):
            for tid, t in parse_technology_sharing(_read(fp)).items():
                t["file"] = fp
                t["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[tid] = t
        return out
    return _cached("technology_sharing", mod_path, hoi4_path, loader)


def parse_strategic_locations(content):
    """解析 strategic_locations/*.txt：每个顶层块 = 一个战略要地。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_strategic_locations(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/strategic_locations"):
            for sid, s in parse_strategic_locations(_read(fp)).items():
                s["file"] = fp
                s["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[sid] = s
        return out
    return _cached("strategic_locations", mod_path, hoi4_path, loader)


def parse_opinion_modifiers(content):
    """解析 opinion_modifiers/*.txt：每个顶层块 = 一个观点修正。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_opinion_modifiers(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/opinion_modifiers"):
            for mid, m in parse_opinion_modifiers(_read(fp)).items():
                m["file"] = fp
                m["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[mid] = m
        return out
    return _cached("opinion_modifiers", mod_path, hoi4_path, loader)


def parse_wargoals(content):
    """解析 wargoals/*.txt：每个顶层块 = 一个战争目标。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_wargoals(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/wargoals"):
            for wid, w in parse_wargoals(_read(fp)).items():
                w["file"] = fp
                w["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[wid] = w
        return out
    return _cached("wargoals", mod_path, hoi4_path, loader)


def parse_difficulty_settings(content):
    """解析 difficulty_settings/*.txt：每个顶层块 = 一个难度档。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_difficulty_settings(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/difficulty_settings"):
            for did, d in parse_difficulty_settings(_read(fp)).items():
                d["file"] = fp
                d["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[did] = d
        return out
    return _cached("difficulty_settings", mod_path, hoi4_path, loader)


def parse_game_rules(content):
    """解析 game_rules/*.txt：每个顶层块 = 一条游戏规则。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_game_rules(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/game_rules"):
            for gid, g in parse_game_rules(_read(fp)).items():
                g["file"] = fp
                g["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[gid] = g
        return out
    return _cached("game_rules", mod_path, hoi4_path, loader)


def parse_autonomous_states(content):
    """解析 autonomous_states/*.txt：每个顶层块 = 一个自治状态。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_autonomous_states(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/autonomous_states"):
            for aid, a in parse_autonomous_states(_read(fp)).items():
                a["file"] = fp
                a["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[aid] = a
        return out
    return _cached("autonomous_states", mod_path, hoi4_path, loader)


def parse_country_tag_aliases(content):
    """解析 country_tag_aliases/*.txt：每个顶层块 = 一个国家别名。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_country_tag_aliases(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/country_tag_aliases"):
            for aid, a in parse_country_tag_aliases(_read(fp)).items():
                a["file"] = fp
                a["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[aid] = a
        return out
    return _cached("country_tag_aliases", mod_path, hoi4_path, loader)


def parse_bookmarks(content):
    """解析 bookmarks/*.txt：每个顶层块 = 一个剧本。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_bookmarks(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/bookmarks"):
            for bid, b in parse_bookmarks(_read(fp)).items():
                b["file"] = fp
                b["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[bid] = b
        return out
    return _cached("bookmarks", mod_path, hoi4_path, loader)


def parse_modifiers(content):
    """解析 modifiers/*.txt：每个顶层块 = 一个修正类型定义。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        f["id"] = key
        f["raw"] = bt
        out[key] = f
    return out


def load_modifiers(mod_path="", hoi4_path=""):
    def loader():
        out = {}
        for fp in _scan_files(mod_path, hoi4_path, "common/modifiers"):
            for mid, m in parse_modifiers(_read(fp)).items():
                m["file"] = fp
                m["rel"] = os.path.relpath(
                    fp, hoi4_path or mod_path or os.path.dirname(fp)
                ).replace("\\", "/")
                out[mid] = m
        return out
    return _cached("modifiers", mod_path, hoi4_path, loader)


# ---------- 通用顶层块 loader 工厂（B2/B3 铺开） ----------


def _make_top_block_loader(folder, cache_key):
    """生成 (parse, load) 对：common/<folder> 下每个顶层块 = 标量字段集。"""

    def _parse(content):
        out = {}
        for key, depth, start, end in _block_ranges(content):
            if depth != 0:
                continue
            bt = content[start:end]
            f = _fields(bt)
            f["id"] = key
            f["raw"] = bt
            out[key] = f
        return out

    def _load(mod_path="", hoi4_path=""):
        def loader():
            out = {}
            for fp in _scan_files(mod_path, hoi4_path, folder):
                for eid, e in _parse(_read(fp)).items():
                    e["file"] = fp
                    e["rel"] = os.path.relpath(
                        fp, hoi4_path or mod_path or os.path.dirname(fp)
                    ).replace("\\", "/")
                    out[eid] = e
            return out
        return _cached(cache_key, mod_path, hoi4_path, loader)

    _parse.__name__ = "parse_" + cache_key
    _load.__name__ = "load_" + cache_key
    return _parse, _load


(parse_occupation_laws, load_occupation_laws) = _make_top_block_loader(
    "common/occupation_laws", "occupation_laws")
(parse_resistance_activity, load_resistance_activity) = _make_top_block_loader(
    "common/resistance_activity", "resistance_activity")
(parse_peace_conference, load_peace_conference) = _make_top_block_loader(
    "common/peace_conference", "peace_conference")
(parse_abilities, load_abilities) = _make_top_block_loader(
    "common/abilities", "abilities")
(parse_aces, load_aces) = _make_top_block_loader(
    "common/aces", "aces")
(parse_collections, load_collections) = _make_top_block_loader(
    "common/collections", "collections")
(parse_mtth, load_mtth) = _make_top_block_loader(
    "common/mtth", "mtth")
(parse_frontend, load_frontend) = _make_top_block_loader(
    "common/frontend", "frontend")


(parse_medals, load_medals) = _make_top_block_loader(
    "common/medals", "medals")
(parse_ribbons, load_ribbons) = _make_top_block_loader(
    "common/ribbons", "ribbons")
(parse_unit_medals, load_unit_medals) = _make_top_block_loader(
    "common/unit_medals", "unit_medals")
(parse_raids, load_raids) = _make_top_block_loader(
    "common/raids", "raids")
(parse_timed_activities, load_timed_activities) = _make_top_block_loader(
    "common/timed_activities", "timed_activities")
(parse_intelligence, load_intelligence) = _make_top_block_loader(
    "common/intelligence", "intelligence")
(parse_generation, load_generation) = _make_top_block_loader(
    "common/generation", "generation")
(parse_operation_phases, load_operation_phases) = _make_top_block_loader(
    "common/operation_phases", "operation_phases")


(parse_map_modes, load_map_modes) = _make_top_block_loader(
    "common/map_modes", "map_modes")
(parse_operation_tokens, load_operation_tokens) = _make_top_block_loader(
    "common/operation_tokens", "operation_tokens")
(parse_scripted_diplomatic_actions, load_scripted_diplomatic_actions) = _make_top_block_loader(
    "common/scripted_diplomatic_actions", "scripted_diplomatic_actions")
(parse_scorers, load_scorers) = _make_top_block_loader(
    "common/scorers", "scorers")
(parse_modifier_definitions, load_modifier_definitions) = _make_top_block_loader(
    "common/modifier_definitions", "modifier_definitions")
(parse_technology_tags, load_technology_tags) = _make_top_block_loader(
    "common/technology_tags", "technology_tags")


(parse_resistance_compliance, load_resistance_compliance) = _make_top_block_loader(
    "common/resistance_compliance", "resistance_compliance")
(parse_scripted_guis, load_scripted_guis) = _make_top_block_loader(
    "common/scripted_guis", "scripted_guis")
(parse_country_leader, load_country_leader) = _make_top_block_loader(
    "common/country_leader", "country_leader")
(parse_ideologies, load_ideologies) = _make_top_block_loader(
    "common/ideologies", "ideologies")


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


# ---------- 通用实体 CRUD 写回 ----------



from ai_loader_crud import *  # noqa: E402,F401,F403 (F5 re-export 兼容)
# 兼容旧调用方直接 `from ai_loader import _top_block` 等私有助手
from ai_loader_crud import (  # noqa: E402,F401,F403
    _areas_block_bounds,
    _eq_group_block,
    _find_block_bounds,
    _nested_child_bounds,
    _role_block,
    _top_block,
)

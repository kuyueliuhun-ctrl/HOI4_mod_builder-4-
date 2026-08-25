"""MIO（军事工业组织）数据层（算法层，无 Qt）。

解析 common/military_industrial_organization/ 下的：
  - organizations/*.txt   MIO 定义（icon/initial_trait/trait 树/加成）
  - policies/*.txt        方针定义（icon/条件/加成）

并提供写回辅助：字段替换、trait / policy 的增删改（复用
nested_block_crud 与 ai_loader_crud 的字符级块操作）。
"""

from __future__ import annotations

import os

from oob_loader import _block_ranges
from ai_loader_crud import (
    _child_block_text,
    _child_blocks,
    _fields,
    _inner_block_text,
    _values_in_block,
    insert_top_block,
    delete_top_block,
    rename_top_block,
    duplicate_top_block,
    replace_top_block_fields,
)
from nested_block_crud import (
    insert_nested_block,
    delete_nested_block,
    rename_nested_block,
    duplicate_nested_block,
    replace_nested_block_fields,
    _nested_entity_bounds,
)
from ai_loader_crud import _find_block_bounds

# ---------- 基础 ----------


def _scan_files(mod_path, hoi4_path, rel_dir, ext=".txt"):
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


def _rel(fp, hoi4_path, mod_path):
    base = hoi4_path or mod_path or os.path.dirname(fp)
    return os.path.relpath(fp, base).replace("\\", "/")


# ---------- 解析 ----------


def _parse_position(block_text):
    """从 position = { x=.. y=.. } 提取 (x, y)。"""
    pos = _child_block_text(block_text, "position")
    if not pos:
        return 0, 0
    f = _fields(pos)
    try:
        return int(f.get("x", 0)), int(f.get("y", 0))
    except (TypeError, ValueError):
        return 0, 0


def _parse_trait(block_text):
    """解析一个 trait = { ... } 块。"""
    f = _fields(block_text)
    x, y = _parse_position(block_text)
    parents = []
    for key in ("any_parent", "all_parents"):
        parents.extend(_values_in_block(block_text, key))
    return {
        "token": f.get("token", ""),
        "name": f.get("name", ""),
        "icon": f.get("icon", ""),
        "x": x,
        "y": y,
        "relative_position_id": f.get("relative_position_id", ""),
        "parents": parents,
        "equipment_bonus": _child_block_text(block_text, "equipment_bonus") or "",
        "production_bonus": _child_block_text(block_text, "production_bonus") or "",
        "raw": block_text,
    }


def parse_mio_organizations(content):
    """解析 organizations/*.txt，返回 {mio_id: dict}。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        traits = []
        initial_trait = None
        headers = []
        for ck, cs, ce in _child_blocks(bt):
            cbt = bt[cs:ce]
            if ck == "trait":
                t = _parse_trait(cbt)
                if t.get("token"):
                    traits.append(t)
            elif ck == "initial_trait":
                tf = _fields(cbt)
                initial_trait = {
                    "name": tf.get("name", ""),
                    "equipment_bonus": _child_block_text(cbt, "equipment_bonus") or "",
                    "production_bonus": _child_block_text(cbt, "production_bonus") or "",
                    "raw": cbt,
                }
            elif ck == "tree_header_text":
                hf = _fields(cbt)
                headers.append({
                    "text": hf.get("text", ""),
                    "x": hf.get("x", ""),
                })
        out[key] = {
            "id": key,
            "name": key,
            "icon": f.get("icon", ""),
            "allowed": _child_block_text(bt, "allowed") or "",
            "equipment_type": _values_in_block(bt, "equipment_type"),
            "research_categories": _values_in_block(bt, "research_categories"),
            "tree_headers": headers,
            "initial_trait": initial_trait,
            "traits": traits,
            "raw": bt,
        }
    return out


def load_mios(mod_path="", hoi4_path=""):
    """加载全部 MIO 组织（mod 优先）。"""
    folder = "common/military_industrial_organization/organizations"
    out = {}
    for fp in _scan_files(mod_path, hoi4_path, folder):
        for mid, m in parse_mio_organizations(_read(fp)).items():
            m["file"] = fp
            m["rel"] = _rel(fp, hoi4_path, mod_path)
            out[mid] = m
    return out


def parse_mio_policies(content):
    """解析 policies/*.txt，返回 {policy_id: dict}。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        out[key] = {
            "id": key,
            "name": key,
            "icon": f.get("icon", ""),
            "allowed": _child_block_text(bt, "allowed") or "",
            "available": _child_block_text(bt, "available") or "",
            "equipment_bonus": _child_block_text(bt, "equipment_bonus") or "",
            "production_bonus": _child_block_text(bt, "production_bonus") or "",
            "organization_modifier": _child_block_text(bt, "organization_modifier") or "",
            "raw": bt,
        }
    return out


def load_mio_policies(mod_path="", hoi4_path=""):
    """加载全部 MIO 方针（mod 优先）。"""
    folder = "common/military_industrial_organization/policies"
    out = {}
    for fp in _scan_files(mod_path, hoi4_path, folder):
        for pid, p in parse_mio_policies(_read(fp)).items():
            p["file"] = fp
            p["rel"] = _rel(fp, hoi4_path, mod_path)
            out[pid] = p
    return out


# ---------- 写回 ----------

def replace_mio_fields(content, mio_id, fields):
    """替换 MIO 顶层块内标量字段（icon 等）。"""
    return replace_top_block_fields(content, mio_id, fields)


def replace_initial_trait(content, mio_id, fields):
    """替换 MIO 的 initial_trait 块内字段（name 等）。"""
    return replace_nested_block_fields(
        content, "initial_trait", fields,
        parent_id=mio_id, id_field=None, depth=1)


def replace_trait_fields(content, mio_id, token, fields):
    """替换某个 trait 块内字段（按 token 定位）。"""
    return replace_nested_block_fields(
        content, token, fields,
        parent_id=mio_id, id_field="token", depth=1)


def insert_trait(content, mio_id, token, after_token=None):
    """在 MIO 内新增一个 trait 块。"""
    block_text = "trait = {\n\t\ttoken = %s\n\t\tname = %s\n\t}\n" % (token, token)
    return insert_nested_block(
        content, token, block_text, parent_id=mio_id,
        id_field="token", depth=1, after_id=after_token)


def delete_trait(content, mio_id, token):
    return delete_nested_block(
        content, token, parent_id=mio_id, id_field="token", depth=1)


def rename_trait(content, mio_id, old_token, new_token):
    return rename_nested_block(
        content, old_token, new_token,
        parent_id=mio_id, id_field="token", depth=1)


def duplicate_trait(content, mio_id, token, new_token):
    return duplicate_nested_block(
        content, token, new_token,
        parent_id=mio_id, id_field="token", depth=1)


def replace_policy_fields(content, policy_id, fields):
    return replace_top_block_fields(content, policy_id, fields)


def insert_policy(content, policy_id, after_id=None):
    return insert_top_block(
        content, "\n%s = {\n\t\n}\n" % policy_id, after_id=after_id)


def delete_policy(content, policy_id):
    return delete_top_block(content, policy_id)


def rename_policy(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)


def duplicate_policy(content, policy_id, new_id):
    return duplicate_top_block(content, policy_id, new_id)


def replace_trait_block(content, mio_id, token, new_block_text):
    """整体替换某个 trait 块（按 token 定位）。"""
    found = _nested_entity_bounds(content, token, mio_id, "token", 1)
    if not found:
        return content
    (_ps, _pe), (bs, _be) = found
    tbs, tbe = _find_block_bounds(content, bs)
    return content[:tbs] + new_block_text.strip() + content[tbe:]


def trait_to_pdx(token, name, icon, x, y, relative_position_id="",
                 parents=None, equipment_bonus="", production_bonus=""):
    """把 trait 表单序列化为 PDX 块文本。"""
    lines = ["trait = {",
             "\t\ttoken = %s" % token,
             "\t\tname = %s" % name]
    if icon:
        lines.append("\t\ticon = %s" % icon)
    lines.append("\t\tposition = { x = %s y = %s }" % (x, y))
    if relative_position_id:
        lines.append("\t\trelative_position_id = %s" % relative_position_id)
    if parents:
        lines.append("\t\tany_parent = { %s }" % " ".join(parents))
    for bonus, raw in (("equipment_bonus", equipment_bonus),
                       ("production_bonus", production_bonus)):
        raw = (raw or "").strip()
        if raw:
            if raw.startswith(bonus + " ="):
                lines.append(raw)
            else:
                lines.append("%s = {\n%s\n\t\t}" % (bonus, raw))
    lines.append("\t}")
    return "\n".join(lines)


def replace_policy_block(content, policy_id, new_block_text):
    """整体替换一个方针顶层块。"""
    for key, depth, start, _end in _block_ranges(content):
        if depth == 0 and key == policy_id:
            bs, be = _find_block_bounds(content, start)
            return content[:bs] + new_block_text.strip() + content[be:]
    return content


def policy_to_pdx(policy_id, icon="", allowed="", available="",
                  equipment_bonus="", production_bonus="",
                  organization_modifier=""):
    """把方针表单序列化为 PDX 块文本。"""
    lines = [policy_id + " = {"]
    if icon:
        lines.append("\ticon = %s" % icon)
    for name, raw in (("allowed", allowed), ("available", available),
                      ("equipment_bonus", equipment_bonus),
                      ("production_bonus", production_bonus),
                      ("organization_modifier", organization_modifier)):
        raw = (raw or "").strip()
        if not raw:
            continue
        if raw.startswith(name + " ="):
            lines.append(raw)
        else:
            lines.append("%s = {\n%s\n\t}" % (name, raw))
    lines.append("}")
    return "\n".join(lines)

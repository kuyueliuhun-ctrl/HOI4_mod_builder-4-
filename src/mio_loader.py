"""MIO（军事工业组织）数据层（算法层，无 Qt）。

解析 common/military_industrial_organization/ 下的：
  - organizations/*.txt   MIO 定义（icon/initial_trait/trait 树/加成）
  - policies/*.txt        方针定义（icon/条件/加成）

并提供写回辅助：字段替换、trait / policy 的增删改（复用
nested_block_crud 与 ai_loader_crud 的字符级块操作）。
"""

from __future__ import annotations

import os
import re

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
    # 游戏先、mod 后：后续 load_* 的 dict 赋值让 mod 覆盖游戏，实现 mod 优先。
    for base in (hoi4_path, mod_path):
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
    """返回 fp 相对 mod/游戏根的路径；文件属于哪个根就用哪个根。

    旧实现固定以 hoi4_path 为基准，当文件实际在 mod 内时会产出
    ../../../mods/... 的错误 rel，导致 ensure_file_in_mod 定位失败。
    """
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        try:
            rel = os.path.relpath(fp, base)
        except ValueError:
            continue
        if rel == "." or not rel.startswith(".."):
            return rel.replace("\\", "/")
    return os.path.basename(fp)


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


_PARENT_KEY_STOP = {"traits", "num_parents_needed",
                     "any_parent", "all_parents"}

_FILE_VAR_RE = re.compile(r"^\s*@([\w\.]+)\s*=\s*(-?[\d\.]+)", re.M)


def _resolve_int(value, variables=None):
    """把 PDX 数值解析为 int，支持 @文件变量 引用；失败返回 0。

    注：pdx 解析器会把 `@var` 的 @ 剥掉，故变量名按裸名也查一次。
    """
    text = str(value).strip().lstrip("@")
    variables = variables or {}
    if text in variables:
        text = str(variables[text]).strip().lstrip("@")
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return 0


def _parent_tokens_from_block(cbt):
    """从 any_parent/all_parents/mutually_exclusive 子块提取特质 token（去重、去键名）。

    兼容两种游戏语法：
    - 包裹式：any_parent = { traits = { a b } num_parents_needed = 1 }
    - 裸值式：mutually_exclusive = { a b }
    """
    text = cbt or ""
    m = re.search(r"traits\s*=\s*\{([^}]*)\}", text)
    if m:
        text = m.group(1)
    else:
        # 剥掉开头键名（`key = {` 之前的部分），取花括号内文本
        start = text.find("{")
        text = text[start + 1:] if start >= 0 else re.sub(r"#.*", "", text)
    toks = re.findall(r"[A-Za-z0-9_][\w\.\-]*", text)
    if not m:
        toks = [t for t in toks if t not in _PARENT_KEY_STOP]
    out = []
    for t in toks:
        if t not in out:
            out.append(t)
    return out


def _parse_trait(block_text, variables=None):
    """解析一个 trait = { ... } 块（variables 供 @文件变量 取值）。"""
    f = _fields(block_text)
    x, y = 0, 0
    pos_text = ""
    equipment_bonus = ""
    production_bonus = ""
    parents = []
    parent_blocks = {}
    mut_ex = []
    extra_blocks = []
    for ck, cs, _ce in _child_blocks(block_text):
        bs, be = _find_block_bounds(block_text, cs)
        cbt = block_text[bs:be].strip()
        if ck in ("any_parent", "all_parents"):
            for tok in _parent_tokens_from_block(cbt):
                if tok not in parents:
                    parents.append(tok)
            parent_blocks.setdefault(ck, []).append(cbt)
        elif ck == "mutually_exclusive":
            # 裸值式：mutually_exclusive = { other_token }
            # 复用父 token 提取器（兼容 traits = {} 包裹与裸值）
            for tok in _parent_tokens_from_block(cbt):
                if tok not in mut_ex:
                    mut_ex.append(tok)
            extra_blocks.append(cbt)
        elif ck == "position":
            pos_text = cbt
        elif ck == "equipment_bonus":
            equipment_bonus = cbt
        elif ck == "production_bonus":
            production_bonus = cbt
        elif cbt:
            extra_blocks.append(cbt)
    if pos_text:
        pf = _fields(pos_text)
        x = _resolve_int(pf.get("x", 0), variables)
        y = _resolve_int(pf.get("y", 0), variables)
    else:
        # 部分模组用裸 x = / y = 键代替 position 块
        x = _resolve_int(f.get("x", 0), variables)
        y = _resolve_int(f.get("y", 0), variables)
    return {
        "token": f.get("token", ""),
        "name": f.get("name", ""),
        "icon": f.get("icon", ""),
        "x": x,
        "y": y,
        "has_position": bool(pos_text) or "x" in f or "y" in f,
        "relative_position_id": f.get("relative_position_id", ""),
        "parents": parents,
        "parent_blocks": parent_blocks,
        "mutually_exclusive": mut_ex,
        "extra_blocks": extra_blocks,
        "equipment_bonus": equipment_bonus,
        "production_bonus": production_bonus,
        "raw": block_text,
    }


def parse_mio_organizations(content):
    """解析 organizations/*.txt，返回 {mio_id: dict}（支持 @文件变量）。"""
    variables = {m.group(1): m.group(2)
                 for m in _FILE_VAR_RE.finditer(content)}
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
            if ck in ("trait", "add_trait"):
                # add_trait 同样可携带完整定义（引用共享特质时常只有 token）
                t = _parse_trait(cbt, variables)
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
            "include": f.get("include", ""),
            "allowed": _child_block_text(bt, "allowed") or "",
            "equipment_type": _values_in_block(bt, "equipment_type"),
            "research_categories": _values_in_block(bt, "research_categories"),
            "tree_headers": headers,
            "initial_trait": initial_trait,
            "traits": traits,
            "raw": bt,
        }
    return out


def _merge_included_trait(base, local):
    """本地 trait 块覆盖继承块：非空字段覆盖，extra/parent 块并集。

    本地块未写 position/relative_position_id 时（覆盖场景常见），
    保留底组织的定位字段。
    """
    out = dict(base)
    local = dict(local)
    if not local.get("has_position"):
        for k in ("x", "y", "relative_position_id"):
            local.pop(k, None)
    for k, v in local.items():
        if k in ("extra_blocks", "parent_blocks", "raw", "has_position",
                 "mutually_exclusive"):
            continue
        if v in ("", None, [], {}):
            continue
        out[k] = v
    base_extra = list(base.get("extra_blocks") or [])
    out["extra_blocks"] = base_extra + [
        b for b in (local.get("extra_blocks") or []) if b not in base_extra]
    base_me = list(base.get("mutually_exclusive") or [])
    out["mutually_exclusive"] = base_me + [
        t for t in (local.get("mutually_exclusive") or []) if t not in base_me]
    pb = dict(base.get("parent_blocks") or {})
    for kk, vv in (local.get("parent_blocks") or {}).items():
        pb.setdefault(kk, [])
        for b in vv:
            if b not in pb[kk]:
                pb[kk].append(b)
    out["parent_blocks"] = pb
    if local.get("raw"):
        out["raw"] = local["raw"]
    return out


def resolve_includes(mios):
    """按游戏规则展开 include 继承：被 include 组织的特质树作为底，
    本地同名 trait 块按字段覆盖；initial_trait 缺失时继承。带环防护。"""
    resolved = {}

    def _resolve(org_id, stack):
        if org_id in resolved:
            return resolved[org_id]
        org = mios.get(org_id)
        if not org:
            return None
        traits = {}
        for t in org.get("traits") or []:
            if t.get("token"):
                traits[t["token"]] = dict(t)
        inc = org.get("include", "")
        if inc and inc != org_id and inc not in stack:
            base = _resolve(inc, stack | {org_id})
            if base:
                merged = {}
                for t in base.get("traits") or []:
                    if t.get("token"):
                        merged[t["token"]] = dict(t)
                for tok, lt in traits.items():
                    if tok in merged:
                        merged[tok] = _merge_included_trait(merged[tok], lt)
                    else:
                        merged[tok] = lt
                traits = merged
        out = dict(org)
        out["traits"] = list(traits.values())
        if not out.get("initial_trait") and inc and inc not in stack:
            base = resolved.get(inc)
            if base and base.get("initial_trait"):
                out["initial_trait"] = dict(base["initial_trait"])
        resolved[org_id] = out
        return out

    out = {}
    for org_id in mios:
        r = _resolve(org_id, set())
        if r:
            out[org_id] = r
    return out


def load_mios(mod_path="", hoi4_path=""):
    """加载全部 MIO 组织（mod 优先，include 继承已展开）。"""
    folder = "common/military_industrial_organization/organizations"
    out = {}
    for fp in _scan_files(mod_path, hoi4_path, folder):
        for mid, m in parse_mio_organizations(_read(fp)).items():
            m["file"] = fp
            m["rel"] = _rel(fp, hoi4_path, mod_path)
            out[mid] = m
    return resolve_includes(out)


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
                 parents=None, equipment_bonus="", production_bonus="",
                 extra_blocks=None):
    """把 trait 表单序列化为 PDX 块文本。

    extra_blocks 用于保留编辑器未直接展示的 trait 子块（如
    limit_to_equipment_type / mutually_exclusive / visible / available /
    organization_modifier / ai_will_do 等），避免整块重写时数据丢失。
    """
    lines = ["trait = {",
             "\t\ttoken = %s" % token,
             "\t\tname = %s" % name]
    if icon:
        lines.append("\t\ticon = %s" % icon)
    lines.append("\t\tposition = { x = %s y = %s }" % (x, y))
    if relative_position_id:
        lines.append("\t\trelative_position_id = %s" % relative_position_id)
    if parents:
        lines.append("\t\tany_parent = { traits = { %s } }"
                     % " ".join(parents))
    for bonus, raw in (("equipment_bonus", equipment_bonus),
                       ("production_bonus", production_bonus)):
        raw = (raw or "").strip()
        if raw:
            if raw.startswith(bonus + " ="):
                lines.append(raw)
            else:
                lines.append("%s = {\n%s\n\t\t}" % (bonus, raw))
    for raw in (extra_blocks or []):
        raw = (raw or "").strip()
        if not raw:
            continue
        raw_lines = raw.splitlines()
        if raw_lines:
            lines.append("\t\t" + raw_lines[0].strip())
        for line in raw_lines[1:]:
            lines.append(line.rstrip() if line.strip() else "")
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

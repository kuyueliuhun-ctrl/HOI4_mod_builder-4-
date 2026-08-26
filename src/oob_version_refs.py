"""OOB `version_name` 引用解析与设计联动检查（纯函数，无 Qt）。

背景：`history/units/*.txt` 的空军 `air_wings`、海军 `ship ... equipment`、
陆军 `force_equipment_variants` 里会用 `version_name = "设计名"` 引用
`create_equipment_variant` 的设计变体。编辑器保存时这些字段作为未知内容原样保留，
但此前没有任何代码把 `version_name` 解析出来与设计库比对/联动。

本模块提供：
- ``extract_version_refs``：从 OOB 文本提取全部 version_name 引用（含装备键/拥有者/数量/舰名）。
- ``check_version_name_links``：与 ship/tank/plane 设计库（tag -> {设计名: ...}）比对，
  输出 resolved / unresolved 清单，供一致性校验与改名联动使用。

不注册 MCP 工具（工具总数保持 178 不变），作为后端数据层。
"""

from __future__ import annotations

import os

from tree_node import parse_pdx_text_to_nodes

# 超大文件跳过解析（复用 CWT-lite 的超大门禁思路，防既有解析器性能问题）
MAX_PARSE_CHARS = 4_000_000


def _infer_kind(equipment_key):
    """由装备键推断设计器类型（plane/tank/ship/unknown）。"""
    k = (equipment_key or "").lower()
    if "airframe" in k:
        return "plane"
    if "hull" in k:
        return "ship"
    if "chassis" in k or "_equipment" in k or k.endswith("_equipment"):
        return "tank"
    return "unknown"


def _scalar(block, key):
    """块节点的直接标量字段值（无则 None）。"""
    for c in block.children:
        if c.node_type == "value" and c.key == key:
            return str(c.value).strip()
    return None


def _iter_blocks(nodes):
    """递归遍历全部块节点（air_wings/ship 可能嵌套在 fleet/task_force 下）。"""
    for n in nodes:
        if n.node_type == "block":
            yield n
            yield from _iter_blocks(n.children)


def _equipment_refs(container, ship_name=""):
    """容器块的直接子块即装备（equipment_key = {...}），提取带 version_name 的引用。

    container 可以是 air_wings 的 <id> 块、ship 的 equipment 块、
    或 force_equipment_variants 块。
    """
    refs = []
    for child in container.children:
        if child.node_type != "block":
            continue
        vn = _scalar(child, "version_name")
        if vn is None:
            continue
        refs.append({
            "kind": _infer_kind(child.key),
            "equipment": child.key,
            "version_name": vn,
            "owner": (_scalar(child, "owner") or "").strip().upper(),
            "amount": _scalar(child, "amount") or "",
            "ship_name": ship_name,
        })
    return refs


def extract_version_refs(content):
    """从 OOB 文本提取全部 version_name 引用。

    Returns:
        list[dict]: {"kind","equipment","version_name","owner","amount","ship_name"}
    """
    if not content or len(content) > MAX_PARSE_CHARS:
        return []
    nodes = parse_pdx_text_to_nodes(content)
    refs = []
    for block in _iter_blocks(nodes):
        if block.key == "air_wings":
            # air_wings = { <id> = { <equipment> = { ... } } }
            for wid in block.children:
                if wid.node_type == "block":
                    refs.extend(_equipment_refs(wid))
        elif block.key == "ship":
            name = _scalar(block, "name") or ""
            for c in block.children:
                if c.node_type == "block" and c.key == "equipment":
                    refs.extend(_equipment_refs(c, ship_name=name))
        elif block.key == "force_equipment_variants":
            refs.extend(_equipment_refs(block))
    return refs


def check_version_name_links(content, plane_designs, tank_designs, ship_designs):
    """比对 OOB 引用与设计库，返回 resolved/unresolved 清单。

    Args:
        content: OOB 文本
        plane_designs / tank_designs / ship_designs:
            对应 `load_plane_variants` / `load_tank_variants` / `load_ship_variants`
            的结果（tag -> {设计名: {...}}）；可为 {}。

    Returns:
        {"refs", "resolved", "unresolved", "count"}
    """
    designs = {
        "plane": plane_designs or {},
        "tank": tank_designs or {},
        "ship": ship_designs or {},
    }
    refs = extract_version_refs(content)
    resolved, unresolved = [], []
    for r in refs:
        pool = designs.get(r["kind"], {})
        owner = r["owner"]
        exists = bool(owner in pool and r["version_name"] in pool[owner])
        (resolved if exists else unresolved).append(r)
    return {"refs": refs, "resolved": resolved, "unresolved": unresolved,
            "count": len(refs)}


def version_refs_in_file(file_path):
    """便捷函数：读 OOB 文件并提取 version_name 引用（path 安全由调用方负责）。"""
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        content = f.read()
    return extract_version_refs(content)


def iter_oob_files(mod_path, game_path=None):
    """产出 (relpath, file_path)——mod 优先，同 relpath 去重（mod 覆盖游戏）。"""
    seen = set()
    for base in ((game_path or ""), mod_path or ""):
        d = os.path.join(base, "history", "units")
        if not os.path.isdir(d):
            continue
        for dp, _dirs, fns in os.walk(d):
            for fn in sorted(fns):
                if not fn.lower().endswith(".txt"):
                    continue
                fp = os.path.join(dp, fn)
                rel = os.path.relpath(fp, d).replace("\\", "/")
                if rel in seen:
                    continue
                seen.add(rel)
                yield rel, fp


def oob_refs_for_design(mod_path, game_path, kind, owner, design_name):
    """找 (kind, owner, design_name) 在 mod+game OOB 中的引用（含文件相对路径）。"""
    hits = []
    owner = (owner or "").strip().upper()
    for rel, fp in iter_oob_files(mod_path, game_path):
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
        for r in extract_version_refs(content):
            if r["kind"] == kind and r["owner"] == owner \
                    and r["version_name"] == design_name:
                hit = dict(r)
                hit["file"] = rel
                hits.append(hit)
    return hits


def rename_oob_version_refs(mod_path, kind, owner, old_name, new_name,
                            dry_run=True):
    """把 mod 内 history/units 中 (kind, owner) 的 version_name old→new。

    文本级精确替换 `version_name = "old"` 与 `version_name = old` 两种写法。
    Returns:
        {"dry_run", "count", "files"}
    """
    from write_utils import atomic_write_text
    owner = (owner or "").strip().upper()
    updated, total = [], 0
    for rel, fp in iter_oob_files(mod_path, None):
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
        refs = [r for r in extract_version_refs(content)
                if r["kind"] == kind and r["owner"] == owner
                and r["version_name"] == old_name]
        if not refs:
            continue
        new = content.replace('version_name = "%s"' % old_name,
                              'version_name = "%s"' % new_name)
        new = new.replace("version_name = %s" % old_name,
                          'version_name = "%s"' % new_name)
        if new == content:
            continue
        total += len(refs)
        if not dry_run:
            atomic_write_text(fp, new)
        updated.append(rel)
    return {"dry_run": dry_run, "count": total, "files": updated}

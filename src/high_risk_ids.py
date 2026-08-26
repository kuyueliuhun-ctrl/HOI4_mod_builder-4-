"""高危 id 清单（Scenario Forge 移植：识别易冲突/高风险 id）。

v1 规则：
1. 覆盖风险：mod 中定义的 focus/event/technology/idea/decision id 与 vanilla 同名定义
   → 直接覆盖原版语义，属高风险。
2. 保留字风险：id 使用 HOI4 脚本保留/常见作用域名（root/from/prev/this/...）。

返回按风险降序的 list[dict]：
    {"id","type","mod_file","reason","vanilla_file?"}
纯函数 + tree_node，无 Qt。
"""

from __future__ import annotations

import os

from tree_node import parse_pdx_text_to_nodes

import cwt_lite_rules as R

# HOI4 脚本常见作用域名/保留字（用作 id 时极易与脚本上下文冲突）
RESERVED_IDS = frozenset({
    "root", "from", "prev", "this", "ROOT", "FROM", "PREV", "THIS",
    "global", "event_target", "default", "hidden",
})

# 类型 → mod/vanilla 扫描目录
TYPE_DIRS = {
    "focus": "common/national_focus",
    "event": "events",
    "technology": "common/technologies",
    "idea": "common/ideas",
    "decision": "common/decisions",
}


def _scalar(block, key):
    for c in block.children:
        if c.node_type == "value" and c.key == key:
            return str(c.value).strip()
    return None


def _entity_ids(content, type_key):
    """从脚本文本提取常见类型实体 id（focus/event 用 id 字段，其余用块键）。"""
    ids = []
    try:
        nodes = parse_pdx_text_to_nodes(content)
    except Exception:
        return ids
    for block in R._iter_entity_blocks(nodes, type_key):
        if type_key in ("focus", "event"):
            v = _scalar(block, "id")
            if v:
                ids.append(v)
        elif type_key in ("technology", "idea", "decision"):
            ids.append(block.key)
    return ids


def _scan_dir(root, rel_dir):
    """扫描目录下所有 .txt，返回 {id: {"type", "file"}}（首个出现为准）。"""
    out = {}
    base = os.path.join(root, *rel_dir.split("/"))
    if not os.path.isdir(base):
        return out
    for dp, _dirs, fns in os.walk(base):
        for fn in sorted(fns):
            if not fn.lower().endswith(".txt"):
                continue
            fp = os.path.join(dp, fn)
            try:
                with open(fp, "r", encoding="utf-8-sig",
                          errors="replace") as f:
                    content = f.read()
            except Exception:
                continue
            rel_file = os.path.relpath(fp, root).replace("\\", "/")
            for type_key in TYPE_DIRS:
                if rel_dir != TYPE_DIRS[type_key]:
                    continue
                for id_ in _entity_ids(content, type_key):
                    if id_ not in out:
                        out[id_] = {"type": type_key, "file": rel_file}
    return out


def high_risk_ids(mod_path, game_path=None):
    """生成 mod 高危 id 清单。

    Returns:
        list[dict]: {"id","type","mod_file","reason","vanilla_file?"}
    """
    risks = []
    for type_key, rel_dir in TYPE_DIRS.items():
        mod_ids = _scan_dir(mod_path, rel_dir)
        vanilla_ids = _scan_dir(game_path, rel_dir) if game_path else {}
        for id_, info in mod_ids.items():
            if id_ in vanilla_ids:
                risks.append({
                    "id": id_, "type": type_key,
                    "mod_file": info["file"],
                    "reason": "覆盖风险：mod 与 vanilla 定义同名 id",
                    "vanilla_file": vanilla_ids[id_]["file"],
                })
            elif id_ in RESERVED_IDS:
                risks.append({
                    "id": id_, "type": type_key,
                    "mod_file": info["file"],
                    "reason": "保留字风险：id 为脚本常见作用域名/保留字",
                })
    risks.sort(key=lambda x: (x["reason"], x["type"], x["id"]))
    return risks
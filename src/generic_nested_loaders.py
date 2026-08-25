"""通用嵌套实体 loader 工厂（B3 复杂类型：wrapper → 实体块）。

对「文件含一个或多个顶层 wrapper 块，wrapper 内嵌实体块」的文件形态
（如 decisions 的分类→决议、ideas 的槽→理念、on_actions 的 on_X、
continuous_focus 的 focus 等），生成 (parse, load) 对。实体 id 默认取
实体块 key；continuous_focus 这类块 key 重复时可用 id_field 取块内
标量字段作为 id。
"""

from __future__ import annotations

import os

from oob_loader import _block_ranges
from ai_loader_crud import _fields


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
    import ai_loader as _al
    key = (kind, mod_path or "", hoi4_path or "")
    if key in _al._AI_CACHE:
        return _al._AI_CACHE[key]
    data = loader()
    _al._AI_CACHE[key] = data
    return data


def _make_nested_block_loader(folder, cache_key, entity_depth=1,
                              id_field=None, wrapper_keys=None,
                              file_mode=False):
    """生成 (parse, load) 对。

    entity_depth: 实体块相对 wrapper 的深度（1 = wrapper 直接子块）。
    id_field: 若设置，用块内该标量字段作为实体 id（缺省用块 key）。
    wrapper_keys: 若设置，只收集这些顶层 wrapper 内的实体。
    """

    def _parse(content):
        out = {}
        for wkey, wd, ws, we in _block_ranges(content):
            if wd != 0:
                continue
            if wrapper_keys and wkey not in wrapper_keys:
                continue
            wt = content[ws:we]
            for ekey, ed, es, ee in _block_ranges(wt):
                if ed != entity_depth:
                    continue
                bt = wt[es:ee]
                f = _fields(bt)
                if id_field:
                    eid = f.get(id_field)
                    if not eid:
                        continue
                else:
                    eid = ekey
                f["id"] = eid
                f["name"] = eid
                f["parent_id"] = wkey
                f["raw"] = bt
                out[eid] = f
        return out

    def _paths(mod_path, hoi4_path):
        if file_mode:
            out = []
            for base in (mod_path, hoi4_path):
                if not base:
                    continue
                fp = os.path.join(base, folder)
                if os.path.isfile(fp):
                    out.append(fp)
            seen, res = set(), []
            for fp in out:
                real = os.path.realpath(fp)
                if real in seen:
                    continue
                seen.add(real)
                res.append(fp)
            return res
        return _scan_files(mod_path, hoi4_path, folder)

    def _load(mod_path="", hoi4_path=""):
        def loader():
            out = {}
            for fp in _paths(mod_path, hoi4_path):
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


# ---------- 首批嵌套类型 ----------

(parse_on_actions, load_on_actions) = _make_nested_block_loader(
    "common/on_actions", "on_actions", entity_depth=1,
    wrapper_keys=("on_actions",))
(parse_continuous_focus, load_continuous_focus) = _make_nested_block_loader(
    "common/continuous_focus", "continuous_focus", entity_depth=1,
    id_field="id", wrapper_keys=("continuous_focus_palette",))
(parse_unit_leader_traits, load_unit_leader_traits) = _make_nested_block_loader(
    "common/unit_leader", "unit_leader_traits", entity_depth=1,
    wrapper_keys=("leader_traits",))
(parse_idea_tags, load_idea_tags) = _make_nested_block_loader(
    "common/idea_tags", "idea_tags", entity_depth=1,
    wrapper_keys=("idea_categories",))
(parse_ideas, load_ideas) = _make_nested_block_loader(
    "common/ideas", "ideas", entity_depth=2, wrapper_keys=("ideas",))
(parse_ideologies_detail, load_ideologies_detail) = _make_nested_block_loader(
    "common/ideologies", "ideologies_detail", entity_depth=1,
    wrapper_keys=("ideologies",))
(parse_decisions, load_decisions) = _make_nested_block_loader(
    "common/decisions", "decisions", entity_depth=1)
(parse_buildings, load_buildings) = _make_nested_block_loader(
    "common/buildings", "buildings", entity_depth=1,
    wrapper_keys=("buildings",))
(parse_terrain, load_terrain) = _make_nested_block_loader(
    "common/terrain/00_terrain.txt", "terrain", entity_depth=1,
    file_mode=True)


(parse_equipment_definitions, load_equipment_definitions) = _make_nested_block_loader(
    "common/units/equipment", "equipment_definitions", entity_depth=1)


def _make_grouped_nested_loader(folder, cache_key, wrapper_keys=None,
                                entity_depth=2):
    """生成带分类分组的嵌套 loader（wrapper → 分类块 → 实体块）。

    用于 ideas：实体 parent_id = 分类块 key（如 country / economic_laws），
    供专用 UI 按分类分组显示与 CRUD。
    """

    def _parse(content):
        out = {}
        for wkey, wd, ws, we in _block_ranges(content):
            if wd != 0:
                continue
            if wrapper_keys and wkey not in wrapper_keys:
                continue
            wt = content[ws:we]
            for ckey, cd, cs, ce in _block_ranges(wt):
                if cd != entity_depth - 1:
                    continue
                ct = wt[cs:ce]
                for ekey, ed, es, ee in _block_ranges(ct):
                    if ed != 1:
                        continue
                    bt = ct[es:ee]
                    f = _fields(bt)
                    f["id"] = ekey
                    f["name"] = ekey
                    f["parent_id"] = ckey
                    f["raw"] = bt
                    out[ekey] = f
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


(parse_ideas_grouped, load_ideas_grouped) = _make_grouped_nested_loader(
    "common/ideas", "ideas_grouped", wrapper_keys=("ideas",), entity_depth=2)

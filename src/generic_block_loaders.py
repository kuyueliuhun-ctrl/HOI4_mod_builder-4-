"""通用顶层块 loader 工厂（B2/B3 铺开，独立模块控制 ai_loader 行数预算）。

对「common/<目录>/*.txt 中每个顶层块 = 一组标量字段」的文件形态，
生成 (parse, load) 对。ai_loader 尾部 `from generic_block_loaders import *`
统一 re-export，调用方仍从 ai_loader 导入。
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


def _make_top_block_loader(folder, cache_key, file_mode=False):
    """生成 (parse, load) 对：每个顶层块 = 标量字段集。

    folder 为目录（common/<folder>/*.txt）或单个文件（common/xxx.txt）。
    """

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


(parse_dynamic_modifiers, load_dynamic_modifiers) = _make_top_block_loader(
    "common/dynamic_modifiers", "dynamic_modifiers")
(parse_operations, load_operations) = _make_top_block_loader(
    "common/operations", "operations")
(parse_scientist_traits, load_scientist_traits) = _make_top_block_loader(
    "common/scientist_traits", "scientist_traits")
(parse_combat_tactics, load_combat_tactics) = _make_top_block_loader(
    "common/combat_tactics.txt", "combat_tactics", file_mode=True)
(parse_triggered_modifiers, load_triggered_modifiers) = _make_top_block_loader(
    "common/triggered_modifiers.txt", "triggered_modifiers", file_mode=True)
(parse_event_modifiers, load_event_modifiers) = _make_top_block_loader(
    "common/event_modifiers.txt", "event_modifiers", file_mode=True)

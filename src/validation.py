"""mod 校验体系扩展：本地化缺失检测 + 国策引用完整性 + 一键修复

在 game_data 的「未知引用/重复 ID」校验之上，补充两类 modder 高频错误：

1. 本地化缺失：mod 中定义的实体（国策/事件/决议/理念/科技/角色等）没有
   对应的 l_simp_chinese 词条（mod 与游戏本地化都没有时判定缺失）
2. 国策引用悬空：prerequisite / mutually_exclusive 引用了不存在的国策

并支持一键修复：把缺失词条批量写入 mod 本地化文件（值取游戏英文原文，
无原文时用实体 id 占位），只写 mod、不碰游戏文件。
"""

import os
import re

# 常见字段/包装键黑名单：generic 实体提取可能把字段块误判为实体，予以过滤
_FIELD_BLACKLIST = {
    "types", "categories", "modifiers", "visible", "available", "bypass",
    "options", "option", "effect", "effects", "allowed", "requirements",
    "equipment", "range", "ranges", "side", "sides", "on_activate",
    "on_deactivate", "text", "trigger", "color", "frames", "name", "desc",
    "icon", "picture", "id", "priority", "cost", "days", "risk_chance",
    "experience", "factor", "modifier", "country_modifiers", "state_modifiers",
    "enable_for_controllers", "completion_reward", "hidden_effect",
    "ai_will_do", "search_filters", "mutually_exclusive", "prerequisite",
    "relative_position_id", "sound_effect", "sound_type", "frame", "type",
    "value", "values", "base", "default", "group", "sub_unit_categories",
    "technology_categories", "defined_text", "continuous_focus_palette",
    "difficulty_setting", "scientist_trait", "ability", "spawn_points",
    "building", "threshold", "margin", "local_building_slots", "movement_cost",
    "is_water", "naval_terrain", "minimum_seazone_dominance", "naval_mine_hit_chance",
    "strategic_bomber", "default_option", "reset_on_civilwar", "country",
    "position", "palette", "categories_color", "faction_names", "dynamic_faction_names",
}

_ENTITY_ID_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def _is_entity_key(key):
    """判断 key 是否可能是实体 id（过滤字段/包装键）。"""
    if not key or not isinstance(key, str):
        return False
    if not _ENTITY_ID_RE.fullmatch(key):
        return False
    if key in _FIELD_BLACKLIST:
        return False
    # 纯小写、短、无下划线 → 大概率是字段（如 visible / effect）
    if key.islower() and "_" not in key and len(key) <= 8:
        return False
    return True


# 实体型内容类型（跳过纯文件级/定义类类型）
_ENTITY_TYPES = {
    "character", "idea", "focus", "event", "decision", "tech", "state",
    "super_event", "bookmark", "country_history", "advisor_assign",
    "scripted", "mio", "equipment", "unit", "initial_oob", "special_project",
    "doctrine", "intelligence", "autonomy", "country_setup", "dynamic_modifier",
    "modifier_definition", "ai_strategy", "ai_division", "wargoal",
    "ideologies", "continuous_focus", "on_actions", "operations", "bop",
    "occupation_laws", "buildings", "resources", "names", "game_rules",
    "state_category", "technology_sharing", "technology_tags", "unit_tags",
    "unit_medals", "medals", "factions", "opinion_modifiers", "raids",
    "abilities", "aces", "scientist_traits", "intelligence_agency_upgrades",
    "difficulty_settings", "scripted_localisation", "scripted_guis",
    "resistance_compliance_modifiers", "timed_activities", "peace_conference",
    "modifier_type", "map_modes", "idea_tag", "country_leader",
    "country_tag_aliases", "strategic_locations", "collections", "scorers",
    "frontend", "profile_backgrounds", "profile_pictures", "mtth",
    "generation", "synchronized_dynamic_tokens", "operation_phases",
    "operation_tokens", "scripted_diplomatic_actions", "script_constants",
    "strategic_region", "supply_area", "map_terrain", "equipment_groups",
    "unit_leader", "ribbons", "resistance_activity", "ai_areas",
    "ai_equipment", "ai_faction_theaters", "ai_focuses", "ai_navy",
}


def collect_entity_keys(mod_path):
    """扫描 mod 全部实体 id（复用工作台实体提取）。

    Returns:
        list[dict]: [{key, type, country, file, loc_keys}, ...]
            loc_keys 为该实体需要本地化词条的 key 列表：
            国策/决议/理念等用实体 id 本身；事件类用块内 title/desc 引用的词条
            （事件 id 通常不需要词条，避免误报）。
    """
    try:
        from content_types import CONTENT_TYPES
        from entity_scanner import EntityScanner as WorkbenchDock
    except Exception:
        return []
    if not mod_path or not os.path.isdir(mod_path):
        return []
    entities = []
    seen = set()
    for c in CONTENT_TYPES:
        key = c[0]
        if key not in _ENTITY_TYPES:
            continue
        folders = c[3]
        ext = c[5]
        exts = [ext] if isinstance(ext, str) else list(ext or [])
        for rel in folders:
            if rel == ".":
                continue
            base = os.path.join(mod_path, rel.replace("/", os.sep))
            if not os.path.isdir(base):
                continue
            for root, _dirs, names in os.walk(base):
                for name in names:
                    if not name.lower().endswith(tuple(exts)):
                        continue
                    fp = os.path.join(root, name)
                    try:
                        content = WorkbenchDock._read_file(fp)
                    except Exception:
                        continue
                    if not content:
                        continue
                    try:
                        es = WorkbenchDock._collect_file_entities(key, content, fp)
                    except Exception:
                        es = []
                    for e in es:
                        ekey = e.get("name") or ""
                        if not _is_entity_key(ekey):
                            continue
                        dedup = (ekey, os.path.realpath(fp))
                        if dedup in seen:
                            continue
                        seen.add(dedup)
                        # 需要词条的 key：事件类取 title/desc 引用，其余取实体 id
                        loc_keys = [ekey]
                        if key in ("event", "super_event"):
                            loc_keys = []
                            fields = {}
                            try:
                                rng = e.get("range") or (-1, -1)
                                if rng[0] >= 0:
                                    fields = WorkbenchDock._top_level_fields(
                                        content[rng[0]:rng[1]])
                            except Exception:
                                pass
                            for fk in ("title", "desc"):
                                v = (fields.get(fk) or "").strip()
                                if v:
                                    loc_keys.append(v)
                        entities.append({
                            "key": ekey,
                            "type": key,
                            "country": (e.get("tags") or [""])[0] or "",
                            "file": os.path.relpath(fp, mod_path).replace(os.sep, "/"),
                            "loc_keys": loc_keys,
                        })
    return entities


def load_loc_keys(mod_path, hoi4_path):
    """加载 mod + 游戏的全部 l_simp_chinese 词条 key。"""
    from localization_mgr import load_loc_yml_dir
    keys = set()
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        loc_dir = os.path.join(base, "localisation", "simp_chinese")
        if os.path.isdir(loc_dir):
            try:
                cache = {}
                load_loc_yml_dir(loc_dir, cache)
                keys.update(cache)
            except Exception:
                pass
        # 兼容美式拼写 localization
        alt = os.path.join(base, "localisation", "localization")
        if os.path.isdir(alt):
            try:
                cache = {}
                load_loc_yml_dir(alt, cache)
                keys.update(cache)
            except Exception:
                pass
    return keys


def _load_loc_values(loc_dir):
    """加载目录下全部本地化 key->value。"""
    from localization_mgr import load_loc_yml_dir
    cache = {}
    if os.path.isdir(loc_dir):
        try:
            load_loc_yml_dir(loc_dir, cache)
        except Exception:
            pass
    return cache


def check_localisation_coverage(mod_path, hoi4_path):
    """本地化缺失检测。

    Returns:
        list[dict]: [{key, type, country, file, missing_keys, loc_keys}]
            实体任一需要词条的 key（loc_keys）在 mod 与游戏词条中都不存在时判定缺失。
    """
    entities = collect_entity_keys(mod_path)
    if not entities:
        return []
    loc = load_loc_keys(mod_path, hoi4_path)
    out = []
    for e in entities:
        miss = [k for k in e.get("loc_keys") or [] if k not in loc]
        if miss:
            item = dict(e)
            item["missing_keys"] = miss
            out.append(item)
    return out


def check_focus_references(mod_path):
    """国策引用完整性：prerequisite / mutually_exclusive 悬空引用。

    Returns:
        list[dict]: [{focus_id, file, missing: [ref,...]}, ...]
    """
    try:
        from entity_scanner import EntityScanner as WorkbenchDock
    except Exception:
        return []
    if not mod_path or not os.path.isdir(mod_path):
        return []
    all_ids = set()
    refs = []  # (focus_id, file_rel, [refs])
    base = os.path.join(mod_path, "common", "national_focus")
    if not os.path.isdir(base):
        return []
    for root, _dirs, names in os.walk(base):
        for name in names:
            if not name.lower().endswith(".txt"):
                continue
            fp = os.path.join(root, name)
            try:
                content = WorkbenchDock._read_file(fp)
            except Exception:
                continue
            data = WorkbenchDock._quick_focus_scan(content)
            rel = os.path.relpath(fp, mod_path).replace(os.sep, "/")
            for fid, node in data.items():
                all_ids.add(fid)
                refs.append((fid, rel, list(node["draw"]["prerequisite"])))
    problems = []
    for fid, rel, prereqs in refs:
        missing = [r for r in prereqs if r not in all_ids]
        if missing:
            problems.append({"focus_id": fid, "file": rel, "missing": missing})
    return problems


def fix_localisation_missing(mod_path, hoi4_path, missing):
    """一键补本地化：把缺失词条写入 mod 本地化文件。

    - 目标文件：mod/localisation/simp_chinese/validation_mod_l_simp_chinese.yml
    - 值优先取游戏英文原文，无原文时用实体 id 占位（提示后续翻译）
    - 只写 mod，不修改游戏文件

    Returns:
        (int, str): (写入条数, 目标文件路径)
    """
    if not mod_path or not os.path.isdir(mod_path):
        return 0, ""
    loc_dir = os.path.join(mod_path, "localisation", "simp_chinese")
    os.makedirs(loc_dir, exist_ok=True)
    target = os.path.join(loc_dir, "validation_mod_l_simp_chinese.yml")

    # 游戏英文原文（优先），供占位值使用
    english = {}
    if hoi4_path:
        english = _load_loc_values(os.path.join(hoi4_path, "localisation", "english"))

    # 读取目标文件现有词条，避免覆盖用户已翻译内容
    from localization_mgr import parse_loc_yml_file
    existing = {}
    if os.path.isfile(target):
        try:
            parse_loc_yml_file(target, existing)
        except Exception:
            existing = {}

    entries = {}
    for m in missing:
        for key in (m.get("missing_keys") or [m.get("key")]):
            if not key or key in existing:
                continue
            val = english.get(key) or key
            entries[key] = val

    if not entries:
        return 0, target

    lines = ["l_simp_chinese:"]
    for key in sorted(entries):
        val = entries[key]
        escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        lines.append(f' {key}: "{escaped}"')

    # 本地化 .yml 遵循 HOI4 惯例带 BOM（utf-8-sig），显式 allow_bom
    from write_utils import atomic_write_text
    atomic_write_text(target, "\n".join(lines) + "\n",
                      encoding="utf-8-sig", allow_bom=True)
    return len(entries), target

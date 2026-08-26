"""CWT-lite 类型规则校验（B3 批二⑤，纯解析/规则，无 Qt）。

内置常见 HOI4 类型的字段类型 catalog，用自研 PDX 解析（tree_node）检查
文件内实体块的直接标量字段是否符合预期类型；块字段出现在标量位置报红。
未知字段不报（避免误报）。真实 CWT 类型规则库（cwtools）未内置，此为轻量替代。
"""

from __future__ import annotations

import re

from tree_node import parse_pdx_text_to_nodes

# 类型 → 直接标量字段类型映射（缺失字段不报；unknown 标量不报）
RULE_CATALOG = {
    "focus": {
        "id": "string", "icon": "string", "x": "int", "y": "int",
        "cost": "var_number", "prerequisite": "block", "mutually_exclusive": "block",
        "available": "block", "bypass": "block", "cancel_if_invalid": "bool",
        "relative_position_id": "string", "will_claim_areas": "bool",
        "available_if_capitulated": "bool", "continue_if_invalid": "bool",
        "bypass_if_unavailable": "bool", "will_lead_to_war_with": "string",
        "cancelable": "bool", "completion_reward": "block",
        "complete_effect": "block", "continue_effect": "block",
        "select_effect": "block", "ai_will_do": "block",
        "search_filters": "block",
    },
    "idea": {
        "picture": "string", "cost": "var_int", "removal_cost": "var_int",
        "level": "var_int", "name": "string", "default": "bool",
        "cancel_if_invalid": "bool", "allowed": "block",
        "available": "block", "ai_will_do": "block", "modifiers": "block",
        "visible": "block",
    },
    "decision": {
        "icon": "string", "priority": "var_int", "days_remove": "var_int",
        "days_re_enable": "var_int", "fire_only_once": "bool",
        "custom_cost_text": "string", "cancel_if_not_visible": "bool",
        "is_good": "bool", "ai_hint_pp_cost": "var_int",
        "selectable_mission": "bool", "target_array": "string",
        "on_map_mode": "string", "war_with_on_remove": "string",
        "available": "block", "visible": "block", "cancel_trigger": "block",
        "target_trigger": "block", "target_root_trigger": "block",
        "custom_cost_trigger": "block", "complete_effect": "block",
        "remove_effect": "block", "ai_will_do": "block",
        "days_mission_active": "var_int", "news": "bool",
    },
    "event": {
        "id": "string", "title": "string", "desc": "string",
        "picture": "string", "is_triggered_only": "bool",
        "fire_only_once": "bool", "hidden": "bool", "major": "bool",
        "minor_flavor": "bool", "option": "block", "trigger": "block",
        "mean_time_to_happen": "block",
    },
    "state": {
        "id": "int", "name": "string", "provinces": "list_int",
        "state_category": "string", "manpower": "var_int",
        "buildings_max_level_factor": "var_number", "local_supplies": "var_number",
        "history": "block", "resources": "block", "buildings": "block",
    },
    "ideology": {
        "color": "list_int", "types": "block",
        "dynamic_faction_names": "list_string", "rules": "block",
        "modifiers": "block", "faction_modifiers": "block",
        "war_impact_on_world_tension": "var_number",
        "faction_impact_on_world_tension": "var_number",
        "ai_democratic": "bool", "ai_communist": "bool",
        "ai_neutral": "bool", "ai_fascist": "bool",
        "can_collaborate": "bool", "can_host_government_in_exile": "bool",
        "ai_ideology_wanted_units_factor": "var_number",
        "ai_give_core_state_control_threshold": "var_int",
    },
    "division_template": {
        "name": "string", "regiments": "block", "support": "block",
        "is_locked": "bool", "division_names_group": "string",
        "priority": "var_int", "template_counter": "var_int",
    },
    "character": {
        "name": "string", "portraits": "block", "country": "string",
        "roles": "block", "can_be_captured": "bool", "gender": "string",
    },
    "technology": {
        "start_year": "int", "cost": "var_int", "research_speed": "var_number",
        "research_cost": "var_number", "research_speed_factor": "var_number",
        "show_effect_as_desc": "bool", "xp_research_type": "string",
        "xp_boost_cost": "var_int", "xp_research_bonus": "var_number",
        "industrial_capacity_factory": "var_number",
        "industrial_capacity_dockyard": "var_number",
        "path": "block", "allow": "block", "effects": "block",
        "ai_will_do": "block", "can_research": "block", "folder": "string",
        "dependencies": "block", "categories": "block",
    },
    "building": {
        "icon": "string", "is_buildable": "bool", "can_be_damaged": "bool",
        "damage_chance": "var_number", "prerequisite": "block",
        "show_adjacency": "bool", "value": "var_number", "one_per_state": "bool",
        "base_cost": "var_int", "icon_frame": "var_int", "show_on_map": "var_int",
        "damage_factor": "var_number", "show_modifier": "bool",
        "spawn_point": "string", "infrastructure_construction_effect": "bool",
        "only_display_if_exists": "bool", "special_icon": "string",
        "always_shown": "bool", "disable_grow_animation": "bool",
        "per_level_extra_cost": "var_int", "disabled_in_dmz": "bool",
        "drawn_at_distance": "bool", "allied_build": "bool",
        "only_costal": "bool", "need_detection": "bool",
        "detecting_intel_type": "string", "hide_if_missing_tech": "bool",
    },
    "modifier": {
        "icon": "string", "is_percent": "bool", "is_equip": "bool",
        "is_good": "bool",
    },
    "opinion_modifier": {
        "opinion": "var_number", "decay": "var_number", "max_opinion": "var_number",
        "min_opinion": "var_number", "previous_opinion_effect": "var_number",
        "same_ideology": "var_number", "value": "var_number", "months": "var_int",
        "trade": "bool", "min_trust": "var_int", "days": "var_int",
        "max_trust": "var_int", "years": "var_int",
    },
    "wargoal": {
        "type": "string", "allowed_states": "block", "can_use": "block",
        "is_triggered_only": "bool", "expire": "var_number", "cost": "var_number",
        "days": "var_int", "threat": "var_number", "generate_base_cost": "var_int",
        "generate_per_state_cost": "var_int", "take_states_cost": "var_int",
        "war_name": "string", "take_states_limit": "var_int",
        "take_states_threat_factor": "var_number", "force_government_cost": "var_int",
        "puppet_cost": "var_int",
    },
    "operation": {
        "name": "string", "icon": "string", "map_icon": "string",
        "desc": "string", "prerequisite": "block", "cost": "var_number",
        "days": "var_int", "network_strength": "var_int", "operatives": "var_int",
        "risk_chance": "var_number", "priority": "var_int", "experience": "var_number",
        "outcome_extra_chance": "var_number", "cost_multiplier": "var_number",
        "prevent_captured_operative_to_die": "bool",
        "target_type": "string", "will_lead_to_war_with": "bool",
        "available": "block", "selectable": "block",
        "complete_effect": "block", "assets": "block",
        "start_equipment": "block",
    },
    "on_action": {
        "events": "block", "random_events": "block",
    },
    "strategic_region": {
        "id": "int", "name": "string", "provinces": "list_int",
        "weather": "block", "static_modifiers": "block",
        "naval_terrain": "string",
    },
    "supply_area": {
        "id": "int", "name": "string", "value": "var_int", "states": "list_int",
    },
    "occupation_law": {
        "icon": "string", "default": "bool", "movement_cost": "var_number",
        "compliance_gain": "var_number", "state_resistance_target": "var_number",
        "state_armed_force_friction": "var_number", "soft_cost": "var_number",
        "unlock": "string", "sound_effect": "string",
        "fallback_law": "string", "default_law": "bool",
        "starting_law": "bool", "missing_garrison_law": "bool",
    },
    "difficulty_setting": {
        "key": "string", "modifier": "string", "multiplier": "var_number",
    },
    "game_rule": {
        "name": "string", "group": "string", "default": "string",
        "required_dlc": "string", "desc": "string", "icon": "string",
        "option": "block",
    },
    "autonomous_state": {
        "name": "string", "hidden": "bool", "manpower": "var_number",
        "industry": "var_number", "foreign_manpower": "var_number",
        "foreign_industry": "var_number", "army": "var_number", "navy": "var_number",
        "air_force": "var_number", "min_autonomy": "var_number",
        "max_autonomy": "var_number", "id": "string", "is_puppet": "bool",
        "min_freedom_level": "var_number", "manpower_influence": "var_number",
        "use_overlord_color": "bool", "default": "bool",
        "peace_conference_initial_freedom": "var_number",
    },
    "dynamic_modifier": {
        "icon": "string", "visible": "block", "desc": "string",
        "hidden": "bool", "enable": "block", "remove_trigger": "block",
        "attacker_modifier": "bool",
    },
    "bookmark": {
        "name": "string", "start_date": "string", "date": "string",
        "event": "string", "picture": "string", "default": "bool",
        "popup": "string", "effects": "block", "desc": "string",
        "default_country": "string", "sort_unplayed_first": "bool",
    },
    "intelligence_agency": {
        "country": "string", "agency_name": "string", "logo": "string",
        "color": "list_int", "intelligence_funding": "int",
        "picture": "string", "names": "list_string",
        "default": "block", "available": "block",
    },
    # 顶层块即实体：内容为任意 effect/trigger 块，无可校验直接标量字段（仅类型识别/遍历）
    "scripted_effect": {},
    "scripted_trigger": {},
    "scripted_localisation": {
        "name": "string", "text": "block", "trigger": "block",
        "localization_key": "string",
    },
    # 整文件即实体（country 定义为 top-level 字段；country_history 为单国历史）
    "country": {
        "graphical_culture": "string", "graphical_culture_2d": "string",
    },
    "country_history": {
        "capital": "var_int", "set_research_slots": "var_int",
        "oob": "string", "set_technology": "block",
        "add_ideas": "string", "set_politics": "block",
        "add_war_support": "var_number",
        "add_equipment": "block", "add_equipment_to_stockpile": "block",
        "set_convoys": "var_int",
    },
    "state_category": {
        "local_building_slots": "var_int", "color": "list_int",
    },
    "terrain": {
        "color": "list_int", "movement_cost": "var_number",
        "combat_width": "var_int", "combat_support_width": "var_int",
        "is_water": "bool", "naval_terrain": "bool", "sound_type": "string",
        "match_value": "var_int", "minimum_seazone_dominance": "var_int",
        "attrition": "var_number", "supply_flow_penalty_factor": "var_number",
        "truck_attrition_factor": "var_number",
        "ai_terrain_importance_factor": "var_number",
        "naval_mine_hit_chance": "var_number", "sickness_chance": "var_number",
        "positioning": "var_number", "navy_visibility": "var_number",
        "enemy_army_bonus_air_superiority_factor": "var_number",
    },
    "resource": {
        "icon_frame": "var_int", "cic": "var_number", "convoys": "var_number",
    },
    "unit": {
        "sprite": "string", "priority": "var_int", "active": "bool",
        "map_icon_category": "string", "max_organisation": "var_number",
        "weight": "var_number", "supply_consumption": "var_number",
        "max_strength": "var_number", "ai_priority": "var_int",
        "group": "string", "manpower": "var_int",
        "default_morale": "var_number", "training_time": "var_int",
        "combat_width": "var_int", "abbreviation": "string",
        "breakthrough": "var_number", "can_be_parachuted": "bool",
        "suppression": "var_number", "soft_attack": "var_number",
        "regimental": "bool", "hard_attack": "var_number",
        "defense": "var_number", "affects_speed": "bool",
        "same_support_type": "string", "land_air_wing_size": "var_int",
        "transport": "string", "type": "string",
        "mega_carrier_air_wing_size": "var_int", "recon": "var_int",
        "special_forces": "bool", "armor_value": "var_number",
        "maximum_speed": "var_number", "is_artillery_brigade": "bool",
        "allow_in_army_hq": "bool", "allow_in_non_army_hq": "bool",
        "deployment_cost": "var_int", "carrier_air_wing_size": "var_int",
        "marines": "bool", "air_attack": "var_number",
        "critical_part_damage_chance_mult": "var_int",
        "hit_profile_mult": "var_number", "divisional": "bool",
        "entrenchment": "var_number",
        "own_equipment_fuel_consumption_mult": "var_number",
        "ap_attack": "var_number", "can_exfiltrate_from_coast": "bool",
        "submarine_carrier_air_wing_size": "var_int",
        "initiative": "var_number", "suppression_factor": "var_number",
        "equipment_capture_factor": "var_number", "cavalry": "bool",
        "reliability": "var_number", "supply_consumption_factor": "var_number",
        "casualty_trickleback": "var_number",
        "experience_loss_factor": "var_number", "reliability_factor": "var_number",
        "naval_strike_attack": "var_number", "hardness": "var_number",
        "mountaineers": "bool",
        "acclimatization_hot_climate_gain_factor": "var_int",
        "acclimatization_cold_climate_gain_factor": "var_int",
        "fuel_consumption_factor": "var_number",
        "division_3d_model_priority": "var_int", "rangers": "bool",
        "recovery": "var_number", "need": "block", "categories": "block",
    },
}

# wrapper → 实体 的常见类型（wrapper 内直接子块即实体；值可为多个候选键）
_WRAPPER_TYPES = {
    "character": ("characters",),
    "technology": ("technologies",),
    "building": ("buildings",),
    "modifier": ("modifiers",),
    "opinion_modifier": ("opinion_modifiers",),
    "wargoal": ("wargoal_types", "wargoals"),
    "operation": ("operations",),
    "on_action": ("on_actions",),
    "occupation_law": ("occupation_laws",),
    "difficulty_setting": ("difficulty_settings",),
    "game_rule": ("game_rules",),
    "autonomous_state": ("autonomous_states",),
    "dynamic_modifier": ("dynamic_modifiers",),
    "bookmark": ("bookmarks",),
    "intelligence_agency": ("intelligence_agencies",),
    "state_category": ("state_categories",),
    "terrain": ("categories",),
    "resource": ("resources",),
    "unit": ("sub_units",),
}

# 顶层块即实体（任意键）的类型：modifier 文件直接列修正块，operation/occupation_law/
# game_rule/dynamic_modifier/scripted_effect/scripted_trigger/scripted_localisation 同理
# （部分文件也可能用 wrapper，见 _WRAPPER_TYPES）
_TOP_LEVEL_ENTITY_TYPES = frozenset({
    "modifier", "dynamic_modifier", "operation",
    "occupation_law", "game_rule", "scripted_effect",
    "scripted_trigger", "scripted_localisation",
})

# 整文件即实体（无外层实体块）的类型，校验时直接检查顶层字段
_FILE_ENTITY_TYPES = frozenset({"country", "country_history"})

_TYPE_KEYS = tuple(RULE_CATALOG.keys())


_PATH_TYPE_RULES = (
    ("common/national_focus", "focus"),
    ("common/ideas", "idea"),
    ("common/decisions", "decision"),
    ("/events/", "event"),
    ("events/", "event"),
    ("history/states", "state"),
    ("common/ideologies", "ideology"),
    ("history/units", "division_template"),
    ("common/units", "unit"),
    ("common/characters", "character"),
    ("common/technologies", "technology"),
    ("common/buildings", "building"),
    ("common/modifiers", "modifier"),
    ("common/opinion_modifiers", "opinion_modifier"),
    ("common/wargoals", "wargoal"),
    ("common/operations", "operation"),
    ("common/on_actions", "on_action"),
    ("map/strategicregions", "strategic_region"),
    ("map/supplyareas", "supply_area"),
    ("common/occupation_laws", "occupation_law"),
    ("common/difficulty_settings", "difficulty_setting"),
    ("common/game_rules", "game_rule"),
    ("common/autonomous_states", "autonomous_state"),
    ("common/dynamic_modifiers", "dynamic_modifier"),
    ("common/bookmarks", "bookmark"),
    ("common/intelligence_agencies", "intelligence_agency"),
    ("common/scripted_effects", "scripted_effect"),
    ("common/scripted_triggers", "scripted_trigger"),
    ("common/scripted_localisation", "scripted_localisation"),
    ("common/countries", "country"),
    ("history/countries", "country_history"),
    ("common/state_category", "state_category"),
    ("common/terrain", "terrain"),
    ("common/resources", "resource"),
)


def infer_type(path):
    """从 mod 相对路径推断内容类型（无法推断返回 None）。"""
    p = (path or "").replace("\\", "/")
    for frag, typ in _PATH_TYPE_RULES:
        if frag in p:
            return typ
    return None


def _children_of_wrapper(nodes, wrapper_keys):
    """产出 wrapper 块内的直接子块（实体）。"""
    for node in nodes:
        if node.node_type != "block" or node.key not in wrapper_keys:
            continue
        for child in node.children:
            if child.node_type == "block":
                yield child


def _iter_special_entity_blocks(nodes, type_key):
    """pass 1：固定键顶层块 / 事件 / 国策树 / 理念 / 决议（category 包装）。"""
    fixed_top = {
        "state": "state",
        "strategic_region": "strategic_region",
        "supply_area": "supply_area",
        "autonomous_state": "autonomy_state",
        "intelligence_agency": "intelligence_agency",
        "division_template": "division_template",
    }.get(type_key)
    for child in nodes:
        if child.node_type != "block":
            continue
        if fixed_top and child.key == fixed_top:
            yield child
        elif type_key == "event" and (child.key.endswith("_event")
                                      or child.key == "event"):
            yield child
        elif type_key == "focus" and child.key == "focus_tree":
            for fc in child.children:
                if fc.node_type == "block" and fc.key == "focus":
                    yield fc
        elif type_key == "idea" and child.key == "ideas":
            for cat in child.children:
                if cat.node_type == "block":
                    for idea in cat.children:
                        if idea.node_type == "block":
                            yield idea
        elif type_key == "ideology" and child.key == "ideologies":
            for ideo in child.children:
                if ideo.node_type == "block":
                    yield ideo
        elif type_key == "decision":
            if child.key == "decisions":
                for cat in child.children:
                    if cat.node_type == "block":
                        for d in cat.children:
                            if d.node_type == "block":
                                yield d
            else:
                for d in child.children:
                    if d.node_type == "block":
                        yield d


def _iter_entity_blocks(nodes, type_key):
    """从顶层块列表（parse_pdx_text_to_nodes 返回值）中产出实体块节点。"""
    yield from _iter_special_entity_blocks(nodes, type_key)

    wrapper = _WRAPPER_TYPES.get(type_key)
    if wrapper:
        yield from _children_of_wrapper(nodes, wrapper)

    if type_key in _TOP_LEVEL_ENTITY_TYPES:
        for child in nodes:
            if child.node_type != "block":
                continue
            if wrapper and child.key in wrapper:
                continue
            yield child


def _is_script_ref(value):
    """容忍脚本变量/常量引用（@const、var_*、[表达式]），避免假红。"""
    s = str(value).strip()
    return s.startswith("@") or s.lower().startswith("var") or (
        "[" in s and "]" in s)


def _is_var_ident(value):
    """裸标识符视为脚本变量/常量名（含命名空间点号，如 global.x / CZE.var）。"""
    s = str(value).strip()
    if not s or s[0].isdigit():
        return False
    return all(c.isalnum() or c in "_." for c in s)


def _var_value_ok(value):
    """var_* 位：数字 / 脚本引用 / 裸标识符 / 点号数字（如 3.5.5 mod 写法）。"""
    s = str(value).strip()
    return (_is_script_ref(value) or _is_var_ident(value)
            or bool(re.fullmatch(r"\d+(\.\d+)+", s)))


def _type_ok(expected, value):
    if expected in ("int", "number"):
        try:
            if expected == "int":
                int(float(value))
            else:
                float(value)
            return True
        except Exception:
            return _is_script_ref(value)
    if expected in ("var_int", "var_number"):
        try:
            if expected == "var_int":
                int(float(value))
            else:
                float(value)
            return True
        except Exception:
            return _var_value_ok(value)
    if expected == "bool":
        return str(value).lower() in ("yes", "no", "true", "false")
    if expected == "string":
        return True
    # block / list_* 期望块：出现为标量即错；但空值 '' 是
    # `key =` 换行 `{` 的解析产物（块标记），不算错误。
    if expected in ("block", "list_int", "list_string"):
        return str(value).strip() == ""
    return False


# 超过该长度的文件跳过解析（自动生成大文件如 19 万行脚本本地化会卡死解析器，
# 属既有解析器性能问题；跳过避免冒烟挂起，改为黄色提示）。
MAX_PARSE_CHARS = 2_000_000


def _validate_children(children, rules, issues):
    """校验一组子节点的直接标量字段。"""
    for child in children:
        if child.node_type != "value":
            continue
        expected = rules.get(child.key)
        if expected is None:
            continue  # 未知字段不报，避免误报
        if not _type_ok(expected, child.value):
            issues.append({
                "severity": "red",
                "message": "字段 %s 期望 %s，实际值 %r" % (
                    child.key, expected, child.value),
            })


def validate_content(content, type_key):
    """校验脚本内容，返回 [{severity, message}]。"""
    rules = RULE_CATALOG.get(type_key)
    if rules is None:
        return [{"severity": "yellow", "message": "未知类型: %s" % type_key}]
    try:
        if len(content) > MAX_PARSE_CHARS:
            return [{"severity": "yellow",
                     "message": "文件过大（%d 字符）跳过解析" % len(content)}]
        nodes = parse_pdx_text_to_nodes(content)
    except Exception as e:
        return [{"severity": "red", "message": "解析失败: %s" % e}]
    issues = []
    if type_key in _FILE_ENTITY_TYPES:
        # 整文件即实体：country / country_history 的顶层字段直接校验
        _validate_children(nodes, rules, issues)
        return issues
    found = False
    for block in _iter_entity_blocks(nodes, type_key):
        found = True
        _validate_children(block.children, rules, issues)
    if not found:
        issues.append({"severity": "yellow",
                       "message": "未找到 %s 类型实体块" % type_key})
    return issues
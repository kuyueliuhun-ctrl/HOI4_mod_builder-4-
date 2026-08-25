"""CWT-lite 类型规则校验（B3 批二⑤，纯解析/规则，无 Qt）。

内置常见 HOI4 类型的字段类型 catalog，用自研 PDX 解析（tree_node）检查
文件内实体块的直接标量字段是否符合预期类型；块字段出现在标量位置报红。
未知字段不报（避免误报）。真实 CWT 类型规则库（cwtools）未内置，此为轻量替代。
"""

from __future__ import annotations

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
}

# 顶层块即实体（任意键）的类型：modifier 文件直接列修正块，operation/occupation_law/
# game_rule/dynamic_modifier 同理（部分文件也可能用 wrapper，见 _WRAPPER_TYPES）
_TOP_LEVEL_ENTITY_TYPES = frozenset({
    "modifier", "dynamic_modifier", "operation",
    "occupation_law", "game_rule",
})

_TYPE_KEYS = tuple(RULE_CATALOG.keys())


def infer_type(path):
    """从 mod 相对路径推断内容类型（无法推断返回 None）。"""
    p = (path or "").replace("\\", "/")
    if "common/national_focus" in p:
        return "focus"
    if "common/ideas" in p:
        return "idea"
    if "common/decisions" in p:
        return "decision"
    if "/events/" in p or p.startswith("events/"):
        return "event"
    if "history/states" in p:
        return "state"
    if "common/ideologies" in p:
        return "ideology"
    if "history/units" in p or "common/units" in p:
        return "division_template"
    if "common/characters" in p:
        return "character"
    if "common/technologies" in p:
        return "technology"
    if "common/buildings" in p:
        return "building"
    if "common/modifiers" in p:
        return "modifier"
    if "common/opinion_modifiers" in p:
        return "opinion_modifier"
    if "common/wargoals" in p:
        return "wargoal"
    if "common/operations" in p:
        return "operation"
    if "common/on_actions" in p:
        return "on_action"
    if "map/strategicregions" in p:
        return "strategic_region"
    if "map/supplyareas" in p:
        return "supply_area"
    if "common/occupation_laws" in p:
        return "occupation_law"
    if "common/difficulty_settings" in p:
        return "difficulty_setting"
    if "common/game_rules" in p:
        return "game_rule"
    if "common/autonomous_states" in p:
        return "autonomous_state"
    if "common/dynamic_modifiers" in p:
        return "dynamic_modifier"
    if "common/bookmarks" in p:
        return "bookmark"
    if "common/intelligence_agencies" in p:
        return "intelligence_agency"
    return None


def _children_of_wrapper(nodes, wrapper_keys):
    """产出 wrapper 块内的直接子块（实体）。"""
    for node in nodes:
        if node.node_type != "block" or node.key not in wrapper_keys:
            continue
        for child in node.children:
            if child.node_type == "block":
                yield child


def _iter_entity_blocks(nodes, type_key):
    """从顶层块列表（parse_pdx_text_to_nodes 返回值）中产出实体块节点。"""
    wrapper = _WRAPPER_TYPES.get(type_key)
    fixed_top = {
        "state": "state",
        "strategic_region": "strategic_region",
        "supply_area": "supply_area",
        "autonomous_state": "autonomy_state",
        "intelligence_agency": "intelligence_agency",
        "division_template": "division_template",
    }.get(type_key)
    # pass 1：固定键顶层块 / 事件 / 国策树 / 理念 / 决议（category 包装）
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
            # 顶层块即 category，其直接子块即 decision；
            # 若顶层块为 `decisions = {...}` 则多包一层 category。
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
    # pass 2：wrapper 型
    if wrapper:
        for child in _children_of_wrapper(nodes, wrapper):
            yield child
    # pass 3：顶层块即实体（跳过 wrapper 容器块，避免重复）
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
            return _is_script_ref(value) or _is_var_ident(value)
    if expected == "bool":
        return str(value).lower() in ("yes", "no", "true", "false")
    if expected == "string":
        return True
    # block / list_* 期望块：出现为标量即错；但空值 '' 是
    # `key =` 换行 `{` 的解析产物（块标记），不算错误。
    if expected in ("block", "list_int", "list_string"):
        return str(value).strip() == ""
    return False


def validate_content(content, type_key):
    """校验脚本内容，返回 [{severity, message}]。"""
    rules = RULE_CATALOG.get(type_key)
    if not rules:
        return [{"severity": "yellow", "message": "未知类型: %s" % type_key}]
    try:
        nodes = parse_pdx_text_to_nodes(content)
    except Exception as e:
        return [{"severity": "red", "message": "解析失败: %s" % e}]
    issues = []
    found = False
    for block in _iter_entity_blocks(nodes, type_key):
        found = True
        for child in block.children:
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
    if not found:
        issues.append({"severity": "yellow",
                       "message": "未找到 %s 类型实体块" % type_key})
    return issues
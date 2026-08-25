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
        "cost": "int", "prerequisite": "block", "mutually_exclusive": "block",
        "available": "block", "bypass": "block", "cancel_if_invalid": "bool",
        "relative_position_id": "string", "will_claim_areas": "bool",
        "completion_reward": "block", "complete_effect": "block",
        "continue_effect": "block", "select_effect": "block",
        "ai_will_do": "block", "search_filters": "block",
    },
    "idea": {
        "picture": "string", "cost": "int", "removal_cost": "int",
        "cancel_if_invalid": "bool", "allowed": "block",
        "available": "block", "ai_will_do": "block", "modifiers": "block",
        "visible": "block",
    },
    "decision": {
        "available": "block", "visible": "block", "cancel_trigger": "block",
        "custom_cost_trigger": "block", "complete_effect": "block",
        "remove_effect": "block", "ai_will_do": "block",
        "days_remove": "int", "days_mission_active": "int", "news": "bool",
    },
    "event": {
        "id": "string", "title": "block", "desc": "block",
        "picture": "string", "is_triggered_only": "bool",
        "fire_only_once": "bool", "hidden": "bool", "option": "block",
        "trigger": "block", "mean_time_to_happen": "block",
    },
    "state": {
        "id": "int", "name": "string", "provinces": "list_int",
        "state_category": "string", "manpower": "int",
        "history": "block", "resources": "block", "buildings": "block",
    },
    "ideology": {
        "color": "list_int", "types": "block",
        "dynamic_faction_names": "list_string", "rules": "block",
        "modifiers": "block", "faction_modifiers": "block",
        "war_impact_on_world_tension": "number",
        "faction_impact_on_world_tension": "number",
    },
    "division_template": {
        "name": "string", "regiments": "block", "support": "block",
        "is_locked": "bool", "division_names_group": "string",
    },
    "character": {
        "name": "string", "portraits": "block", "country": "string",
        "roles": "block",
    },
    "technology": {
        "start_year": "int", "cost": "int", "research_speed": "number",
        "path": "block", "allow": "block", "effects": "block",
        "ai_will_do": "block", "can_research": "block", "folder": "string",
        "dependencies": "block", "categories": "block",
    },
    "building": {
        "icon": "string", "is_buildable": "bool", "can_be_damaged": "bool",
        "damage_chance": "number", "prerequisite": "block",
        "show_adjacency": "bool", "value": "number", "one_per_state": "bool",
    },
    "modifier": {
        "icon": "string", "is_percent": "bool", "is_equip": "bool",
        "is_good": "bool",
    },
    "opinion_modifier": {
        "opinion": "number", "decay": "number", "max_opinion": "number",
        "min_opinion": "number", "previous_opinion_effect": "number",
        "same_ideology": "number",
    },
    "wargoal": {
        "type": "string", "allowed_states": "block", "can_use": "block",
        "is_triggered_only": "bool", "expire": "block", "cost": "number",
        "days": "int",
    },
    "operation": {
        "name": "string", "icon": "string", "prerequisite": "block",
        "cost": "number", "available": "block", "selectable": "block",
        "complete_effect": "block", "days": "int", "assets": "block",
        "start_equipment": "block",
    },
    "on_action": {
        "events": "block", "random_events": "block",
    },
    "strategic_region": {
        "id": "int", "name": "string", "provinces": "list_int",
        "weather": "block", "static_modifiers": "block",
    },
    "supply_area": {
        "id": "int", "name": "string", "value": "int", "states": "list_int",
    },
    "occupation_law": {
        "icon": "string", "default": "bool", "movement_cost": "number",
        "compliance_gain": "number", "state_resistance_target": "number",
        "state_armed_force_friction": "number", "soft_cost": "number",
        "unlock": "string",
    },
    "difficulty_setting": {
        "starting_equipment_factor": "number", "ai_equipment_factor": "number",
        "ai_training_factor": "number", "ai_templates_factor": "number",
        "ai_division_attack_factor": "number",
        "ai_division_defence_factor": "number",
        "ai_bonus_for_cheat": "bool",
    },
    "game_rule": {
        "name": "string", "group": "string", "default": "string",
        "option": "block",
    },
    "autonomous_state": {
        "name": "string", "hidden": "bool", "manpower": "number",
        "industry": "number", "foreign_manpower": "number",
        "foreign_industry": "number", "army": "number", "navy": "number",
        "air_force": "number", "min_autonomy": "number",
        "max_autonomy": "number",
    },
    "dynamic_modifier": {
        "icon": "string", "visible": "block", "desc": "string",
        "hidden": "bool",
    },
    "bookmark": {
        "name": "string", "start_date": "string", "event": "string",
        "picture": "string", "default": "bool", "popup": "string",
        "effects": "block",
    },
    "intelligence_agency": {
        "country": "string", "agency_name": "string", "logo": "string",
        "color": "list_int", "intelligence_funding": "int",
    },
}

# wrapper → 实体 的常见类型（wrapper 内直接子块即实体）
_WRAPPER_TYPES = {
    "character": "characters",
    "technology": "technologies",
    "building": "buildings",
    "modifier": "modifiers",
    "opinion_modifier": "opinion_modifiers",
    "wargoal": "wargoals",
    "operation": "operations",
    "on_action": "on_actions",
    "occupation_law": "occupation_laws",
    "difficulty_setting": "difficulty_settings",
    "game_rule": "game_rules",
    "autonomous_state": "autonomous_states",
    "dynamic_modifier": "dynamic_modifiers",
    "bookmark": "bookmarks",
    "intelligence_agency": "intelligence_agencies",
}

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


def _children_of_wrapper(nodes, wrapper_key):
    """产出 wrapper 块内的直接子块（实体）。"""
    for node in nodes:
        if node.node_type != "block" or node.key != wrapper_key:
            continue
        for child in node.children:
            if child.node_type == "block":
                yield child


def _iter_entity_blocks(nodes, type_key):
    """从顶层块列表（parse_pdx_text_to_nodes 返回值）中产出实体块节点。"""
    for child in nodes:
        if child.node_type != "block":
            continue
        if type_key == "focus" and child.key == "focus_tree":
            for fc in child.children:
                if fc.node_type == "block" and fc.key == "focus":
                    yield fc
        elif type_key == "idea" and child.key == "ideas":
            for cat in child.children:
                if cat.node_type == "block":
                    for idea in cat.children:
                        if idea.node_type == "block":
                            yield idea
        elif type_key == "decision" and child.key in ("decisions",):
            for d in child.children:
                if d.node_type == "block" and d.key == "decision":
                    yield d
        elif type_key == "event" and (child.key.endswith("_event")
                                      or child.key == "event"):
            yield child
        elif type_key == "state" and child.key == "state":
            yield child
        elif type_key == "ideology" and child.key == "ideologies":
            for ideo in child.children:
                if ideo.node_type == "block":
                    yield ideo
        elif type_key == "division_template" and child.key == "division_template":
            yield child
        elif type_key == "strategic_region" and child.key == "strategic_region":
            yield child
        elif type_key == "supply_area" and child.key == "supply_area":
            yield child
    # wrapper 型：复用通用遍历（循环结束后再扫一次，避免上面 return 结构）
    wrapper = _WRAPPER_TYPES.get(type_key)
    if wrapper:
        for child in _children_of_wrapper(nodes, wrapper):
            yield child


def _type_ok(expected, value):
    if expected == "int":
        try:
            int(float(value))
            return True
        except Exception:
            return False
    if expected == "number":
        try:
            float(value)
            return True
        except Exception:
            return False
    if expected == "bool":
        return str(value).lower() in ("yes", "no", "true", "false")
    if expected == "string":
        return True
    # block / list_* 期望块：出现为标量即错
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
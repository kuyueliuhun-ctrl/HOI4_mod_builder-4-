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
    return None


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
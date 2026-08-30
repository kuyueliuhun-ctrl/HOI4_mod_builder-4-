"""MCP 校验器：把踩坑索引中的正确范式固化为自动化拦截。

两类校验：
1. metadata：检查 MCP 工具注册表（名称/schema/description/正确范式字段）。
2. call：在 MCP tools/call 调用前拦截常见错误（缺必填/类型错/越界路径/未批准写操作）。

与文档的关系：
- 规则 ID MCPVAL-* 在 docs/MCP开发者指南.md §7.2 有说明；
- 踩坑分类见 docs/踩坑索引.md 第 8~11 节。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

# ══════════════════════════════════════════════════════════════
# 已知规则字典（与文档同步）
# ══════════════════════════════════════════════════════════════

GENERATOR_TOOLS = {
    "generate_ideas", "generate_ideologies", "generate_characters",
    "generate_generals", "generate_country_bootstrap",
    "generate_focus_package", "generate_event",
}

# 这些工具在 schema 中必须带 dry_run 参数（批量/结构操作正确范式）
DRY_RUN_SCHEMA_TOOLS = {
    "batch_fill_localisation", "batch_set_state_fields",
    "copy_country_files", "create_blank_overrides", "create_mod",
    "create_new_country_files", "generate_characters",
    "generate_country_bootstrap", "generate_event", "generate_focus_package",
    "generate_generals", "generate_ideas", "generate_ideologies",
    "import_unit_counters", "sync_plane_design", "sync_ship_design",
    "sync_tank_design",
}

AI_REQUIRED = {
    "ai_plan_create": ["id"],
    "ai_plan_update": ["id"],
    "ai_plan_delete": ["id"],
    "ai_plan_rename": ["id", "new"],
    "ai_plan_duplicate": ["id", "new"],
    "ai_strategy_create": ["id"],
    "ai_strategy_update": ["id"],
    "ai_strategy_delete": ["id"],
    "ai_strategy_rename": ["id", "new"],
    "ai_strategy_duplicate": ["id", "new"],
    "ai_ai_template_create": ["id"],
    "ai_ai_template_update": ["id"],
    "ai_ai_template_delete": ["id"],
    "ai_ai_template_rename": ["id", "new"],
    "ai_ai_template_duplicate": ["id", "new"],
    "ai_equipment_create": ["id"],
    "ai_equipment_update": ["id"],
    "ai_equipment_delete": ["id"],
    "ai_equipment_rename": ["id", "new"],
    "ai_equipment_duplicate": ["id", "new"],
    "ai_navy_create": ["id", "section"],
    "ai_navy_update": ["id", "section"],
    "ai_navy_delete": ["id", "section"],
    "ai_navy_rename": ["id", "section", "new"],
    "ai_navy_duplicate": ["id", "section", "new"],
    "ai_area_create": ["id"],
    "ai_area_update": ["id"],
    "ai_area_delete": ["id"],
    "ai_area_rename": ["id", "new"],
    "ai_area_duplicate": ["id", "new"],
    "ai_focus_create": ["id"],
    "ai_focus_update": ["id"],
    "ai_focus_delete": ["id"],
    "ai_focus_rename": ["id", "new"],
    "ai_focus_duplicate": ["id", "new"],
    "ai_theater_create": ["id"],
    "ai_theater_update": ["id"],
    "ai_theater_delete": ["id"],
    "ai_theater_rename": ["id", "new"],
    "ai_theater_duplicate": ["id", "new"],
}

# 这些属性名代表“mod 内相对路径”，调用时禁止绝对路径 / .. / 盘符
MOD_RELATIVE_PATH_PROPS = {"path", "output_dir", "target_path", "dirs"}

# 路径/文件名类属性，调用时同样禁止绝对路径 / .. / 盘符（但描述不强制写“相对路径”）
PATH_LIKE_PROPS = MOD_RELATIVE_PATH_PROPS | {"filename", "template_name"}

# 这些属性名允许绝对路径（但仍由 handler/path_safety 限制根）
ABSOLUTE_PATH_PROPS = {"absolute_path", "mod_folder_path", "mod_file_path"}


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str
    tool: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity,
                "tool": self.tool, "message": self.message}


# ══════════════════════════════════════════════════════════════
# Metadata 校验
# ══════════════════════════════════════════════════════════════

def _issue(code, severity, message, tool=""):
    return Issue(code, severity, message, tool)


def _check_metadata_required(schema, issues, tool_name):
    required = schema.get("required") or []
    props = schema.get("properties") or {}
    if not isinstance(required, list):
        issues.append(_issue("MCPVAL-REG-002", "error",
                             "required 必须是 list", tool_name))
        return
    for key in required:
        if key not in props:
            issues.append(_issue("MCPVAL-REG-003", "error",
                                 "required 包含未定义 property: %s" % key,
                                 tool_name))


def _check_description_pattern(tool, issues):
    desc = tool.get("description") or ""
    if tool["name"] == "create_mod":
        if "approved" not in desc or "dry_run" not in desc:
            issues.append(_issue("MCPVAL-DESC-001", "warning",
                                 "create_mod description 应包含 dry_run/approved 正确范式",
                                 tool["name"]))
    for path_prop in MOD_RELATIVE_PATH_PROPS:
        schema = tool.get("inputSchema") or {}
        prop = (schema.get("properties") or {}).get(path_prop)
        if not prop:
            continue
        pdesc = prop.get("description") or ""
        if "相对" not in pdesc:
            issues.append(_issue("MCPVAL-DESC-002", "warning",
                                 "%s 参数 description 应标注“mod 内相对路径”" % path_prop,
                                 tool["name"]))


def validate_tool_metadata(tool: dict[str, Any]) -> list[Issue]:
    """校验单个工具注册的 metadata/schema 正确范式。"""
    issues: list[Issue] = []
    name = tool.get("name", "")
    if not name:
        issues.append(_issue("MCPVAL-REG-001", "error", "工具名为空"))
        return issues
    if not tool.get("description", "").strip():
        issues.append(_issue("MCPVAL-REG-004", "error",
                             "description 为空", name))
    elif "TODO" in tool["description"] or "待补" in tool["description"]:
        issues.append(_issue("MCPVAL-REG-004", "warning",
                             "description 疑似 TODO/未完成", name))

    schema = tool.get("inputSchema") or {}
    if schema.get("type") != "object":
        issues.append(_issue("MCPVAL-REG-002", "error",
                             "inputSchema.type 必须为 object", name))
    if not isinstance(schema.get("properties"), dict):
        issues.append(_issue("MCPVAL-REG-002", "error",
                             "inputSchema.properties 必须为 dict", name))
    else:
        _check_metadata_required(schema, issues, name)

    if name in GENERATOR_TOOLS:
        examples = schema.get("examples")
        if not isinstance(examples, list) or not examples:
            issues.append(_issue("MCPVAL-EX-001", "error",
                                 "生成器工具必须附加非空 examples", name))

    if name in DRY_RUN_SCHEMA_TOOLS:
        props = schema.get("properties") or {}
        if "dry_run" not in props:
            issues.append(_issue("MCPVAL-DRYSCHEMA-001", "error",
                                 "dry_run 工具 schema 缺少 dry_run 属性", name))

    if name == "create_mod":
        props = schema.get("properties") or {}
        if "approved" not in props:
            issues.append(_issue("MCPVAL-APPROVE-001", "error",
                                 "create_mod schema 缺少 approved 属性", name))
        if "mod_folder_path" not in props:
            issues.append(_issue("MCPVAL-APPROVE-001", "error",
                                 "create_mod schema 缺少 mod_folder_path 属性", name))

    if name in AI_REQUIRED:
        required = list(schema.get("required") or [])
        if set(required) != set(AI_REQUIRED[name]):
            issues.append(_issue("MCPVAL-REG-005", "error",
                                 "AI %s required 应为 %s，实际 %s"
                                 % (name, AI_REQUIRED[name], required), name))

    _check_description_pattern(tool, issues)
    return issues


# ══════════════════════════════════════════════════════════════
# Call 校验
# ══════════════════════════════════════════════════════════════

def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _check_call_type(name: str, expected: str, value: Any,
                     issues: list[Issue], tool_name: str) -> None:
    if expected == "string" and isinstance(value, str):
        return
    if expected == "integer" and isinstance(value, int) and not isinstance(value, bool):
        return
    if expected == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
        return
    if expected == "boolean" and isinstance(value, bool):
        return
    if expected == "array" and isinstance(value, list):
        return
    if expected == "object" and isinstance(value, dict):
        return
    issues.append(_issue("MCPVAL-TYPE-001", "error",
                         "参数 %s 类型应为 %s，实际 %s" % (name, expected, _type_name(value)),
                         tool_name))


def _looks_absolute(p: Any) -> bool:
    if not isinstance(p, str) or not p:
        return False
    if p.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", p):
        return True
    return False


def _check_path_safety(tool: dict[str, Any], args: dict[str, Any],
                       issues: list[Issue]) -> None:
    schema = tool.get("inputSchema") or {}
    props = schema.get("properties") or {}
    for prop, prop_schema in props.items():
        if prop not in args or args[prop] is None:
            continue
        value = args[prop]
        expected = prop_schema.get("type", "")
        if prop in PATH_LIKE_PROPS:
            if expected == "array" and isinstance(value, list):
                values = value
            else:
                values = [value]
            for item in values:
                if not isinstance(item, str):
                    continue
                if _looks_absolute(item) or ".." in item.split("/") or ".." in item.split("\\"):
                    issues.append(_issue("MCPVAL-PATH-001", "error",
                                         "参数 %s 必须是 mod 内相对路径（拒绝绝对/..）：%r"
                                         % (prop, item), tool["name"]))


def validate_call(tool: dict[str, Any], args: dict[str, Any]) -> list[Issue]:
    """MCP tools/call 调用前校验：缺少必填/类型错/越界路径/未批准写操作。"""
    issues: list[Issue] = []
    name = tool.get("name", "")
    schema = tool.get("inputSchema") or {}
    props = schema.get("properties") or {}
    required = schema.get("required") or []
    args = args or {}

    for key in required:
        if key not in args or args[key] is None:
            issues.append(_issue("MCPVAL-REQ-001", "error",
                                 "缺少必填参数: %s" % key, name))

    for key, value in args.items():
        prop = props.get(key)
        if not prop or value is None:
            continue
        expected = prop.get("type")
        if expected:
            _check_call_type(key, expected, value, issues, name)

    # 高权限写操作：dry_run=false 时必须显式 approved=true
    if "dry_run" in props and args.get("dry_run") is False:
        has_approved = "approved" in props
        if has_approved and args.get("approved") is not True:
            issues.append(_issue("MCPVAL-APPROVE-001", "error",
                                 "dry_run=false 时须 approved=true", name))
    if name == "create_mod" and args.get("dry_run") is False:
        if args.get("approved") is not True:
            issues.append(_issue("MCPVAL-APPROVE-001", "error",
                                 "create_mod dry_run=false 时须 approved=true", name))

    _check_path_safety(tool, args, issues)
    return issues


# ══════════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════════

def validate_all_tools(core) -> list[Issue]:
    """遍历 build_tools(core) 返回全部 metadata 问题。"""
    from mcp_tools import build_tools
    issues: list[Issue] = []
    for tool in build_tools(core):
        issues.extend(validate_tool_metadata(tool))
    return issues


def format_issues(issues: list[Issue]) -> str:
    if not issues:
        return "MCP 校验通过：无问题。"
    lines = ["MCP 校验发现问题 %d 条：" % len(issues)]
    for it in issues:
        lines.append("[%s] %s %s — %s" % (
            it.severity.upper(), it.code, it.tool, it.message))
    return "\n".join(lines)
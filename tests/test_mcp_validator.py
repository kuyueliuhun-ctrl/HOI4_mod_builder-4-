"""MCP 校验器测试：正确范式自动化拦截。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


def _make_core():
    from api_server import ApiCore
    return ApiCore(mod_path=_mkdtemp("mcp_val_"), game_path="")


def _tool(name="t", description="测试工具", schema=None):
    return {"name": name, "description": description,
            "inputSchema": schema or {"type": "object", "properties": {}},
            "_handler": lambda args: {"ok": True}}


class MetadataValidatorTest(unittest.TestCase):
    def test_all_tools_metadata_clean(self):
        from mcp_tools import build_tools
        from mcp_validator import validate_all_tools
        core = _make_core()
        issues = validate_all_tools(core)
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(errors, [],
                         "当前工具注册表不应有 metadata error:\n%s" %
                         "\n".join(str(i) for i in issues))

    def test_nav_tools_metadata_clean(self):
        from mcp_tools import NAV_TOOLS_META
        from mcp_validator import validate_tool_metadata
        for name, desc, schema in NAV_TOOLS_META:
            issues = validate_tool_metadata(
                {"name": name, "description": desc, "inputSchema": schema})
            self.assertEqual([i for i in issues if i.severity == "error"], [],
                             name)

    def test_generator_missing_examples_detected(self):
        from mcp_validator import validate_tool_metadata
        t = _tool("generate_event", "生成事件（默认 dry_run）", {
            "type": "object",
            "properties": {"dry_run": {"type": "boolean"}},
        })
        issues = validate_tool_metadata(t)
        self.assertTrue(any(i.code == "MCPVAL-EX-001" for i in issues))

    def test_ai_required_mismatch_detected(self):
        from mcp_validator import validate_tool_metadata
        t = _tool("ai_plan_create", "新建AI 战略计划", {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        })
        issues = validate_tool_metadata(t)
        self.assertTrue(any(i.code == "MCPVAL-REG-005" for i in issues))

    def test_dry_run_schema_missing_detected(self):
        from mcp_validator import validate_tool_metadata
        t = _tool("generate_ideas", "生成理念（默认 dry_run）", {
            "type": "object",
            "properties": {"ideas": {"type": "array"}},
            "examples": [{}],
        })
        issues = validate_tool_metadata(t)
        self.assertTrue(any(i.code == "MCPVAL-DRYSCHEMA-001" for i in issues))


class CallValidatorTest(unittest.TestCase):
    def setUp(self):
        from mcp_tools import build_tools
        self.core = _make_core()
        self.tools = {t["name"]: t for t in build_tools(self.core)}

    def test_missing_required_rejected(self):
        from mcp_validator import validate_call
        tool = self.tools["get_entity"]
        issues = validate_call(tool, {"type": "focus"})
        self.assertTrue(any(i.code == "MCPVAL-REQ-001" for i in issues))

    def test_type_mismatch_rejected(self):
        from mcp_validator import validate_call
        tool = self.tools["get_state"]
        issues = validate_call(tool, {"state_id": "not-int"})
        self.assertTrue(any(i.code == "MCPVAL-TYPE-001" for i in issues))

    def test_path_escape_rejected(self):
        from mcp_validator import validate_call
        tool = self.tools["read_file"]
        issues = validate_call(tool, {"path": "E:/outside/evil.txt"})
        self.assertTrue(any(i.code == "MCPVAL-PATH-001" for i in issues))
        issues2 = validate_call(tool, {"path": "../escape.txt"})
        self.assertTrue(any(i.code == "MCPVAL-PATH-001" for i in issues2))

    def test_create_mod_without_approved_rejected(self):
        from mcp_validator import validate_call
        tool = self.tools["create_mod"]
        issues = validate_call(tool, {
            "name": "x", "folder_name": "y", "version": "1.0",
            "mod_folder_path": "E:/mods/y", "dry_run": False})
        self.assertTrue(any(i.code == "MCPVAL-APPROVE-001" for i in issues))

    def test_create_mod_dry_run_ok(self):
        from mcp_validator import validate_call
        tool = self.tools["create_mod"]
        issues = validate_call(tool, {
            "name": "x", "folder_name": "y", "version": "1.0",
            "mod_folder_path": "E:/mods/y", "dry_run": True})
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(errors, [])


class ServerInterceptionTest(unittest.TestCase):
    def test_builtin_tools_call_validates(self):
        from mcp_server import BuiltinMcpServer, _validated_invoke
        core = _make_core()
        server = BuiltinMcpServer(core)
        tool = next(t for t in server.all_tools if t["name"] == "read_file")
        args = {"path": "C:/Windows/win.ini"}
        with self.assertRaises(ValueError):
            _validated_invoke(tool, args)

    def test_invoke_tool_validates_nested_call(self):
        from mcp_server import BuiltinMcpServer
        core = _make_core()
        server = BuiltinMcpServer(core)
        invoke = next(t for t in server.all_tools if t["name"] == "invoke_tool")
        with self.assertRaises(ValueError):
            invoke["_handler"]({"name": "read_file",
                                "args": {"path": "/etc/passwd"}})


if __name__ == "__main__":
    unittest.main()
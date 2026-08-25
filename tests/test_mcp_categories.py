"""MCP A+B 分类方案测试（B3）。"""

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
    mod = _mkdtemp("mcp_cat_")
    return ApiCore(mod_path=mod, game_path="")


class CatalogAndCategoryTest(unittest.TestCase):
    def test_build_tools_and_catalog_counts(self):
        from mcp_tools import build_catalog, build_tools
        core = _make_core()
        tools = build_tools(core)
        self.assertGreaterEqual(len(tools), 176)  # 159 + 9 + 5 + 1 + 2（debug）
        catalog = build_catalog(core)
        self.assertEqual(len(catalog), len(tools) + 3)  # +3 导航
        names = {m["name"] for m in catalog}
        self.assertTrue({"list_tools_overview", "get_tool_schema",
                         "invoke_tool"} <= names)

    def test_categories_assigned(self):
        from mcp_tools import build_catalog, tool_category
        core = _make_core()
        cases = {
            "get_state": "states-map",
            "create_ship_design": "designers",
            "create_division_template": "oob",
            "ai_plan_create": "ai",
            "get_bop": "bop",
            "search_terms": "localisation",
            "health_check": "health",
            "convert_dds": "media",
            "generate_ideas": "generators",
            "create_mod": "project",
            "get_status": "core",
        }
        for name, cat in cases.items():
            self.assertEqual(tool_category(name), cat, name)
        cats = {m["category"] for m in build_catalog(core)}
        self.assertIn("nav", cats)

    def test_core_tools_subset_exposed(self):
        from mcp_tools import CORE_TOOLS
        self.assertGreaterEqual(len(CORE_TOOLS), 20)
        self.assertIn("get_status", CORE_TOOLS)
        self.assertIn("validate_mod", CORE_TOOLS)


class ExposureTest(unittest.TestCase):
    def test_default_exposes_core_and_nav_only(self):
        from mcp_server import BuiltinMcpServer, _exposed_names
        core = _make_core()
        server = BuiltinMcpServer(core)
        exposed = server.exposed_names
        # 默认：核心精选 + 导航（远小于 159）
        self.assertLess(len(exposed), 60)
        self.assertTrue({"list_tools_overview", "get_tool_schema",
                         "invoke_tool"} <= exposed)
        self.assertIn("get_status", exposed)
        # 隐藏工具默认不直接暴露
        self.assertNotIn("list_bop", exposed)
        self.assertNotIn("ai_plan_create", exposed)

    def test_whitelist_category_expands_exposure(self):
        from mcp_server import _exposed_names
        from mcp_tools import build_tools
        core = _make_core()
        all_tools = [t for t in build_tools(core)]
        old = os.environ.get("MCP_EXPOSE_CATEGORIES")
        try:
            os.environ["MCP_EXPOSE_CATEGORIES"] = "bop"
            names = _exposed_names(all_tools)
            self.assertIn("list_bop", names)
            self.assertIn("get_bop", names)
        finally:
            if old is None:
                os.environ.pop("MCP_EXPOSE_CATEGORIES", None)
            else:
                os.environ["MCP_EXPOSE_CATEGORIES"] = old

    def test_expose_all(self):
        from mcp_server import _exposed_names
        from mcp_tools import build_tools
        core = _make_core()
        all_tools = [t for t in build_tools(core)]
        old = os.environ.get("MCP_EXPOSE_CATEGORIES")
        try:
            os.environ["MCP_EXPOSE_CATEGORIES"] = "all"
            names = _exposed_names(all_tools)
            self.assertEqual(len(names), len(all_tools) + 3)
        finally:
            if old is None:
                os.environ.pop("MCP_EXPOSE_CATEGORIES", None)
            else:
                os.environ["MCP_EXPOSE_CATEGORIES"] = old

    def test_invoke_tool_calls_hidden_tool(self):
        from mcp_server import BuiltinMcpServer
        core = _make_core()
        server = BuiltinMcpServer(core)
        invoke = next(t for t in server.all_tools
                      if t["name"] == "invoke_tool")
        result = invoke["_handler"]({"name": "get_status", "args": {}})
        self.assertIsInstance(result, dict)
        self.assertIn("mod_path", result)
        # 隐藏工具经 invoke_tool 可调
        schema = next(t for t in server.all_tools
                      if t["name"] == "get_tool_schema")
        meta = schema["_handler"]({"name": "list_bop"})
        self.assertEqual(meta["name"], "list_bop")
        self.assertEqual(meta["category"], "bop")


class ResourcesAndPromptsTest(unittest.TestCase):
    def test_resources_and_prompts(self):
        from mcp_server import BuiltinMcpServer
        core = _make_core()
        server = BuiltinMcpServer(core)
        resources = server._list_resources()
        self.assertGreaterEqual(len(resources), 4)
        uris = {r["uri"] for r in resources}
        self.assertIn("hoi4://status", uris)
        self.assertIn("hoi4://tools/overview", uris)
        self.assertIn("hoi4://terms", uris)
        text = server._read_resource("hoi4://status")
        self.assertIn("mod_path", text)
        overview = server._read_resource("hoi4://tools/overview")
        self.assertIn("categories", overview)
        prompts = server._list_prompts()
        self.assertGreaterEqual(len(prompts), 3)
        names = {p["name"] for p in prompts}
        self.assertIn("validate_project", names)
        p = server._get_prompt("validate_project", {})
        self.assertIn("messages", p)
        self.assertEqual(p["messages"][0]["role"], "user")
        with self.assertRaises(ValueError):
            server._read_resource("hoi4://nope")
        with self.assertRaises(ValueError):
            server._get_prompt("nope", {})


if __name__ == "__main__":
    unittest.main()
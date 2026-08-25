"""B3 批二②：Agent 偏好持久化 + 工具审计日志测试。"""

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
    mod = _mkdtemp("agent_")
    return ApiCore(mod_path=mod, game_path="")


class AgentPreferenceTest(unittest.TestCase):
    def setUp(self):
        import api_core_ext.agent as agent_mod
        self._runtime = agent_mod._RUNTIME
        for n in ("agent_prefs.json", "tool_logs.jsonl"):
            p = os.path.join(self._runtime, n)
            if os.path.isfile(p):
                os.remove(p)

    def test_prefs_roundtrip(self):
        core = _make_core()
        r = core.set_agent_preference({"key": "lang", "value": "zh"})
        self.assertTrue(r["ok"])
        r = core.list_agent_preferences({})
        self.assertEqual(r["preferences"].get("lang"), "zh")
        r = core.delete_agent_preference({"key": "lang"})
        self.assertTrue(r["deleted"])
        r = core.list_agent_preferences({})
        self.assertNotIn("lang", r["preferences"])

    def test_tool_logs_query_export(self):
        core = _make_core()
        core.log_tool_call("get_status", {"x": 1}, ok=True)
        core.log_tool_call("list_bop", {"y": 2}, ok=False)
        r = core.query_tool_logs({})
        self.assertEqual(r["count"], 2)
        self.assertEqual(r["logs"][0]["tool"], "get_status")
        self.assertFalse(r["logs"][1]["ok"])
        r2 = core.query_tool_logs({"regex": "list_bop"})
        self.assertEqual(r2["count"], 1)
        r3 = core.export_tool_logs({})
        self.assertIn("list_bop", r3["text"])
        with self.assertRaises(ValueError):
            core.query_tool_logs({"regex": "["})


class AgentMcpRegistryTest(unittest.TestCase):
    def test_tools_registered_and_categorized(self):
        from mcp_tools import build_catalog, build_tools, tool_category
        core = _make_core()
        tools = build_tools(core)
        names = {t["name"] for t in tools}
        for n in ("list_agent_preferences", "set_agent_preference",
                  "delete_agent_preference", "query_tool_logs",
                  "export_tool_logs"):
            self.assertIn(n, names)
        self.assertEqual(tool_category("query_tool_logs"), "agent")
        cats = {m["category"] for m in build_catalog(core)}
        self.assertIn("agent", cats)


if __name__ == "__main__":
    unittest.main()
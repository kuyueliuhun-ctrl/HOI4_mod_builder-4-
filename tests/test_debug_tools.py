"""B3 批二④：调试启动预检 / 拉起测试。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


def _make_core():
    from api_server import ApiCore
    mod = _mkdtemp("debug_")
    return ApiCore(mod_path=mod, game_path="")


class DebugRunTest(unittest.TestCase):
    def test_preflight_no_game_not_green(self):
        core = _make_core()
        r = core.validate_hoi4_debug_run({})
        self.assertTrue(r["ok"])
        self.assertFalse(r["green"])
        self.assertIn("game_path", r["checks"])
        self.assertFalse(r["launched"] if "launched" in r else False)
        self.assertFalse(r["rchadow_available"])

    def test_launch_requires_green_and_approved(self):
        core = _make_core()
        # 预检不绿 → 即使 launch+approved 也不启动
        r = core.validate_hoi4_debug_run(
            {"launch": True, "approved": True})
        self.assertNotIn("launched", r)
        self.assertIn("预检未全绿", r["guidance"])

    def test_spawn_gated_by_approved(self):
        core = _make_core()
        launcher = os.path.join(_mkdtemp("dbg_launch_"), "launcher-settings.json")
        with open(launcher, "w", encoding="utf-8") as f:
            f.write("{}")
        fake_paths = {"game_path": "/fake", "exe": "/fake/hoi4.exe",
                      "document_path": "/fake/docs",
                      "launcher_settings": launcher,
                      "error_log_path": "/fake/logs/error.log"}
        calls = []
        with mock.patch.object(core, "_debug_paths", return_value=fake_paths), \
             mock.patch.object(core, "_spawn_debug",
                               side_effect=lambda exe: calls.append(exe) or True):
            # 未批准：不启动
            r1 = core.validate_hoi4_debug_run({"launch": True, "approved": False})
            self.assertIn("需显式 approved=true", r1["guidance"])
            self.assertEqual(calls, [])
            # 批准：启动
            r2 = core.validate_hoi4_debug_run({"launch": True, "approved": True})
            self.assertTrue(r2["launched"])
            self.assertEqual(calls, ["/fake/hoi4.exe"])

    def test_rchadow_unavailable(self):
        core = _make_core()
        r = core.launch_hoi4_debug_with_rchadow({})
        self.assertFalse(r["available"])
        self.assertIn("Rchadow", r["guidance"])

    def test_spawn_debug_nonexistent(self):
        core = _make_core()
        self.assertFalse(core._spawn_debug("/no/such/hoi4.exe"))


class DebugMcpRegistryTest(unittest.TestCase):
    def test_tools_registered_in_debug(self):
        from mcp_tools import build_tools, tool_category
        core = _make_core()
        names = {t["name"] for t in build_tools(core)}
        self.assertIn("validate_hoi4_debug_run", names)
        self.assertIn("launch_hoi4_debug_with_rchadow", names)
        self.assertEqual(tool_category("validate_hoi4_debug_run"), "debug")


if __name__ == "__main__":
    unittest.main()
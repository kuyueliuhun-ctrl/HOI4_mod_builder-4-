"""B3 批二⑤：CWT-lite 类型规则校验测试。"""

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


def _make_core(mod):
    from api_server import ApiCore
    return ApiCore(mod_path=mod, game_path="")


class CwtLiteRulesTest(unittest.TestCase):
    def test_validate_content_red_on_bad_type(self):
        from cwt_lite_rules import validate_content
        good = "focus_tree = {\n\tfocus = {\n\t\tid = a\n\t\tx = 1\n\t}\n}\n"
        issues = validate_content(good, "focus")
        self.assertFalse([i for i in issues if i["severity"] == "red"])
        bad = "focus_tree = {\n\tfocus = {\n\t\tid = a\n\t\tx = not_a_number\n\t}\n}\n"
        issues2 = validate_content(bad, "focus")
        self.assertTrue([i for i in issues2 if i["severity"] == "red"])

    def test_infer_type(self):
        from cwt_lite_rules import infer_type
        self.assertEqual(infer_type("common/national_focus/ger.txt"), "focus")
        self.assertEqual(infer_type("common/ideas/x.txt"), "idea")
        self.assertEqual(infer_type("history/states/1.txt"), "state")
        self.assertIsNone(infer_type("localisation/en.txt"))


class CwtLiteCoreTest(unittest.TestCase):
    def _mod_with_focus(self):
        mod = _mkdtemp("cwt_")
        d = os.path.join(mod, "common", "national_focus")
        os.makedirs(d)
        with open(os.path.join(d, "ger.txt"), "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n\tfocus = {\n\t\tid = a\n\t\tx = 1\n\t}\n}\n")
        return mod

    def test_validate_file_by_path(self):
        core = _make_core(self._mod_with_focus())
        r = core.validate_hoi4_file(
            {"path": "common/national_focus/ger.txt"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["type"], "focus")
        self.assertTrue(r["green"])
        self.assertEqual(r["red"], 0)

    def test_validate_project(self):
        core = _make_core(self._mod_with_focus())
        r = core.validate_hoi4_project({"max_files": 50})
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(r["counts"]["files"], 1)
        self.assertIn("CWT-lite", r["note"])

    def test_validate_content_bad(self):
        core = _make_core(self._mod_with_focus())
        r = core.validate_hoi4_file({
            "content": "focus_tree = {\n\tfocus = {\n\t\tx = nope\n\t}\n}\n",
            "type": "focus"})
        self.assertFalse(r["green"])
        self.assertGreater(r["red"], 0)


class CwtMcpRegistryTest(unittest.TestCase):
    def test_tools_registered_in_health(self):
        from mcp_tools import build_tools, tool_category
        core = _make_core(_mkdtemp("cwt_reg_"))
        names = {t["name"] for t in build_tools(core)}
        self.assertIn("validate_hoi4_file", names)
        self.assertIn("validate_hoi4_project", names)
        self.assertEqual(tool_category("validate_hoi4_file"), "health")


if __name__ == "__main__":
    unittest.main()
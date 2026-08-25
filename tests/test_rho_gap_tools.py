"""B3：补充 RHoiScribe 缺失能力测试（符号/解释/块级编辑/红黄绿/修复/环境发现）。"""

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


def _make_mod():
    mod = _mkdtemp("rho_")
    d = os.path.join(mod, "common", "national_focus")
    os.makedirs(d)
    with open(os.path.join(d, "ger.txt"), "w", encoding="utf-8") as f:
        f.write("""focus_tree = {
\tfocus = {
\t\tid = GER_anchluss
\t\tx = 0
\t\tcost = 10
\t}
}
""")
    d2 = os.path.join(mod, "common", "scripted_effects")
    os.makedirs(d2)
    with open(os.path.join(d2, "effects.txt"), "w", encoding="utf-8") as f:
        f.write("""my_effect = {
\thidden = yes
}
""")
    return mod


def _make_core(mod):
    from api_server import ApiCore
    return ApiCore(mod_path=mod, game_path="")


class ProjectSymbolsTest(unittest.TestCase):
    def test_scan_find_references_completion(self):
        from project_symbols import (
            find_definition, find_references, scan_workspace,
            suggest_completion,
        )
        mod = _make_mod()
        syms = scan_workspace(mod, keyword="GER")
        self.assertTrue(any(s["name"] == "GER_anchluss" and s["kind"] == "id"
                            for s in syms))
        self.assertTrue(any(s["name"] == "focus_tree" and s["kind"] == "block"
                            for s in scan_workspace(mod)))
        d = find_definition("GER_anchluss", mod)
        self.assertIsNotNone(d)
        self.assertEqual(d["kind"], "id")
        refs = find_references("GER_anchluss", mod)
        # 定义行被排除，引用可能为空（小样例无引用）
        self.assertIsInstance(refs, list)
        cands = suggest_completion("GER_", mod)
        self.assertTrue(any(c["name"] == "GER_anchluss" for c in cands))


class ApiCoreRhoGapTest(unittest.TestCase):
    def test_discover_environment(self):
        core = _make_core(_make_mod())
        r = core.discover_environment()
        self.assertIn("mod_path", r)
        self.assertIn("game_path", r)
        self.assertIn("error_log_path", r)

    def test_symbols_via_core(self):
        core = _make_core(_make_mod())
        r = core.list_workspace_symbols({"keyword": "GER"})
        self.assertTrue(r["ok"])
        self.assertGreater(r["count"], 0)
        d = core.find_definition({"name": "GER_anchluss"})
        self.assertIsNotNone(d["definition"])
        c = core.suggest_completion({"prefix": "GER_"})
        self.assertGreater(c["count"], 0)

    def test_explain_diagnostic(self):
        core = _make_core(_make_mod())
        r = core.explain_diagnostic(
            {"diagnostic": "duplicate id found for focus GER_anchluss"})
        self.assertTrue(r["ok"])
        self.assertIn("repair_guidance", r)
        self.assertTrue(any("duplicate" in g for g in r["repair_guidance"]))

    def test_edit_script_file_dry_run_and_apply(self):
        core = _make_core(_make_mod())
        rel = "common/scripted_effects/effects.txt"
        r = core.edit_script_file({
            "path": rel, "block": "my_effect", "action": "replace",
            "content": "\thidden = no\n", "dry_run": True,
        })
        self.assertTrue(r["ok"])
        self.assertTrue(r["dry_run"])
        self.assertTrue(r["changed"])
        # dry_run 不写盘
        with open(os.path.join(core.mod_path, *rel.split("/")),
                  encoding="utf-8") as f:
            self.assertIn("hidden = yes", f.read())
        r2 = core.edit_script_file({
            "path": rel, "block": "my_effect", "action": "replace",
            "content": "\thidden = no\n", "dry_run": False,
        })
        self.assertFalse(r2["dry_run"])
        with open(os.path.join(core.mod_path, *rel.split("/")),
                  encoding="utf-8") as f:
            self.assertIn("hidden = no", f.read())

    def test_validate_project_and_repair(self):
        mod = _make_mod()
        # 制造一个带 BOM 的 txt
        bom_file = os.path.join(mod, "common", "scripted_effects", "bom.txt")
        with open(bom_file, "wb") as f:
            f.write(b"\xef\xbb\xbffoo = {}\n")
        core = _make_core(mod)
        v = core.validate_project({})
        self.assertIn("red", v)
        self.assertIn("yellow", v)
        r = core.repair_project({"dry_run": True, "bom": True})
        rel = "common/scripted_effects/bom.txt"
        self.assertIn(rel, r["bom_remove"])
        r2 = core.repair_project({"dry_run": False, "bom": True})
        self.assertIn(rel, r2["applied"])
        with open(bom_file, "rb") as f:
            self.assertFalse(f.read(3).startswith(b"\xef\xbb\xbf"))


class McpRegistryRhoTest(unittest.TestCase):
    def test_new_tools_registered(self):
        from mcp_tools import build_catalog, build_tools, tool_category
        core = _make_core(_make_mod())
        tools = build_tools(core)
        names = {t["name"] for t in tools}
        self.assertGreaterEqual(len(tools), 168)  # 159 + 9
        for n in ("discover_environment", "list_workspace_symbols",
                  "find_definition", "find_references", "suggest_completion",
                  "explain_diagnostic", "edit_script_file",
                  "validate_project", "repair_project"):
            self.assertIn(n, names)
        self.assertEqual(tool_category("list_workspace_symbols"), "symbols")
        self.assertEqual(tool_category("edit_script_file"), "core")
        cats = {m["category"] for m in build_catalog(core)}
        self.assertIn("symbols", cats)


if __name__ == "__main__":
    unittest.main()
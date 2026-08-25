"""B3 批二③：程序化 GUI/GFX 资产生成测试。"""

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
    mod = _mkdtemp("gfx_")
    return ApiCore(mod_path=mod, game_path="")


class ProceduralAssetTest(unittest.TestCase):
    def test_generate_png(self):
        from procedural_assets import generate_asset_png
        mod = _mkdtemp("asset_")
        path = os.path.join(mod, "test.png")
        generate_asset_png(path, "test", size=(32, 32))
        self.assertTrue(os.path.isfile(path))
        self.assertGreater(os.path.getsize(path), 0)
        from PIL import Image
        with Image.open(path) as im:
            self.assertEqual(im.size, (32, 32))
            self.assertEqual(im.mode, "RGBA")


class GenerateGuiGfxAssetCoreTest(unittest.TestCase):
    def test_dry_run_no_write(self):
        core = _make_core()
        r = core.generate_gui_gfx_asset({"name": "my_icon", "dry_run": True})
        self.assertTrue(r["ok"])
        self.assertTrue(r["dry_run"])
        self.assertEqual(len(r["files"]), 2)
        self.assertEqual(r["sprite_name"], "GFX_my_icon")
        self.assertTrue(r["approved_required"])

    def test_requires_approved(self):
        core = _make_core()
        with self.assertRaises(ValueError):
            core.generate_gui_gfx_asset(
                {"name": "my_icon", "dry_run": False, "approved": False})

    def test_approved_writes_files(self):
        core = _make_core()
        r = core.generate_gui_gfx_asset({
            "name": "my_icon", "dry_run": False, "approved": True,
            "gui": True, "size": [32, 32],
            "output_root": "gfx/interface/procedural",
        })
        self.assertFalse(r["dry_run"])
        self.assertIn("GFX_my_icon", r["sprite_name"])
        self.assertGreaterEqual(len(r["written"]), 3)
        png = os.path.join(core.mod_path, "gfx/interface/procedural/my_icon.png")
        gfx = os.path.join(core.mod_path, "gfx/interface/procedural/my_icon.gfx")
        gui = os.path.join(core.mod_path, "interface/my_icon.gui")
        for p in (png, gfx, gui):
            self.assertTrue(os.path.isfile(p), p)
        with open(gfx, encoding="utf-8") as f:
            self.assertIn("GFX_my_icon", f.read())
        with open(gui, encoding="utf-8") as f:
            self.assertIn("GFX_my_icon", f.read())


class McpRegistryGfxTest(unittest.TestCase):
    def test_tool_registered_in_media(self):
        from mcp_tools import build_tools, tool_category
        core = _make_core()
        names = {t["name"] for t in build_tools(core)}
        self.assertIn("generate_gui_gfx_asset", names)
        self.assertEqual(tool_category("generate_gui_gfx_asset"), "media")


if __name__ == "__main__":
    unittest.main()
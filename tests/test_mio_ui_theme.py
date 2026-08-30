"""MIO UI 主题层测试（游戏美术路径解析 / 变体映射 / 组件回退渲染）。"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mkdtemp(prefix):
    import tempfile
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


def _mk_art(root, name, content=b"art"):
    d = os.path.join(root, "gfx", "interface",
                     "military_industrial_organization")
    os.makedirs(d, exist_ok=True)
    fp = os.path.join(d, name)
    with open(fp, "wb") as f:
        f.write(content)
    return fp


class ResolveArtPath(unittest.TestCase):
    """resolve_art_path：mod 优先、游戏回退、缺失返回空。"""

    def test_mod_priority(self):
        import mio_ui_theme as t
        mod = _mkdtemp("mio_art_mod_")
        game = _mkdtemp("mio_art_game_")
        _mk_art(mod, "mio_entry_bg.dds", b"mod")
        _mk_art(game, "mio_entry_bg.dds", b"game")
        got = t.resolve_art_path("mio_entry_bg.dds", mod, game)
        self.assertTrue(got.startswith(mod))

    def test_game_fallback(self):
        import mio_ui_theme as t
        game = _mkdtemp("mio_art_game2_")
        _mk_art(game, "mio_details_background_tank.dds")
        got = t.resolve_art_path("mio_details_background_tank.dds", "", game)
        self.assertTrue(got.startswith(game))

    def test_missing_returns_empty(self):
        import mio_ui_theme as t
        self.assertEqual(t.resolve_art_path("nope.dds", "", ""), "")


class DetailsVariant(unittest.TestCase):
    """details_variant_for：装备类型 → 插画变体。"""

    def test_mapping(self):
        import mio_ui_theme as t
        self.assertEqual(
            t.details_variant_for(["german_medium_tank_chassis"]),
            t.ART_DETAILS_PREFIX + "_tank.dds")
        self.assertEqual(
            t.details_variant_for(["gw_small_airframe"]),
            t.ART_DETAILS_PREFIX + "_plane.dds")
        self.assertEqual(
            t.details_variant_for(["ship_hull_heavy"]),
            t.ART_DETAILS_PREFIX + "_ship.dds")
        self.assertEqual(
            t.details_variant_for(["infantry_equipment"]),
            t.ART_DETAILS_PREFIX + "_factory.dds")
        self.assertEqual(
            t.details_variant_for([]),
            t.ART_DETAILS_PREFIX + ".dds")
        self.assertEqual(
            t.details_variant_for("artillery_equipment"),
            t.ART_DETAILS_PREFIX + "_factory.dds")


class ThemeAssets(unittest.TestCase):
    """调色板 / 主色按钮 / 缓存加载。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_art_overlay_keys(self):
        import mio_ui_theme as t
        for key in ("text", "shadow"):
            self.assertIn(key, t.ART_OVERLAY)

    def test_theme_tokens_used(self):
        import mio_ui_theme as t
        from theme import COLORS as C
        self.assertEqual(t.C, C)  # 主题与编辑器全局主题一致

    def test_load_art_pixmap_cache(self):
        import mio_ui_theme as t
        mod = _mkdtemp("mio_art_load_")
        # PNG 内容 + .dds 扩展名：Pillow 按内容解码（DdsLoader 同路径）
        _mk_art(mod, "mio_entry_bg.dds", self._png_bytes())
        pm1 = t.load_art_pixmap("mio_entry_bg.dds", mod, "")
        self.assertFalse(pm1.isNull())
        pm2 = t.load_art_pixmap("mio_entry_bg.dds", mod, "")
        self.assertIs(pm1, pm2)  # 命中内存缓存

    @staticmethod
    def _png_bytes():
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (8, 8), (22, 20, 17)).save(buf, format="PNG")
        return buf.getvalue()


class WidgetsFallback(unittest.TestCase):
    """组件在无素材环境下的回退渲染。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_banner_fallback(self):
        from mio_ui_theme import BannerWidget
        b = BannerWidget("", "")
        b.set_title("TEST_ORG")
        b.resize(400, 68)
        pm = b.grab()
        self.assertFalse(pm.isNull())

    def test_illustration_fallback(self):
        from mio_ui_theme import IllustrationHeader
        h = IllustrationHeader("", "")
        h.set_org("some_mio", ["medium_tank_chassis"], loc=lambda k: k)
        h.resize(600, 128)
        pm = h.grab()
        self.assertFalse(pm.isNull())

    def test_style_primary_button(self):
        from PyQt6.QtWidgets import QPushButton
        from mio_ui_theme import style_primary_button
        btn = QPushButton("方针")
        style_primary_button(btn)
        self.assertEqual(btn.property("class"), "primary")


class GfxRecursiveScan(unittest.TestCase):
    """scan_gfx_folder recursive：子目录 .gfx 也能进 gfx_map。"""

    def test_recursive_vs_flat(self):
        from gui_translator import scan_gfx_folder
        base = _mkdtemp("gfx_scan_")
        d = os.path.join(base, "interface", "mio")
        os.makedirs(d)
        with open(os.path.join(d, "a.gfx"), "w", encoding="utf-8") as f:
            f.write('spriteTypes = { spriteType = { name = "GFX_test_x" '
                    'texturefile = "gfx/a.dds" } }')
        flat = {}
        scan_gfx_folder(base, flat)
        self.assertNotIn("GFX_test_x", flat)
        rec = {}
        scan_gfx_folder(base, rec, recursive=True)
        self.assertIn("GFX_test_x", rec)


if __name__ == "__main__":
    unittest.main()

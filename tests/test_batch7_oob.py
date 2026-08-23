# -*- coding: utf-8 -*-
"""批次 7 定向测试：地形三项 / 兵种保存 / division_names_group / OOB 初始视野。

运行：python -X utf8 -m unittest tests.test_batch7_oob -v
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
SRC = os.path.join(PROJECT_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class Terrain3Test(unittest.TestCase):
    """地形三项（movement/attack/defence）解析与平均。"""

    def _make(self):
        mod = _mkdtemp("dsh_b7_terr_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "units")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "inf.txt"), "w", encoding="utf-8") as f:
            f.write("sub_units = {\n"
                    "\tinfantry = {\n"
                    "\t\tabbreviation = INF\n"
                    "\t\tcombat_width = 2\n"
                    "\t\tforest = { movement = 0.2 attack = -0.1 defence = 0.1 }\n"
                    "\t}\n"
                    "\tmotorized = {\n"
                    "\t\tabbreviation = MOT\n"
                    "\t\tcombat_width = 2\n"
                    "\t\tforest = { movement = 0.0 attack = 0.2 defence = 0.3 }\n"
                    "\t}\n"
                    "}\n")
        return mod

    def test_parse_terrain_three_keys(self):
        from oob_loader import _parse_terrain
        from tree_node import parse_pdx_text_to_nodes
        mod = self._make()
        with open(os.path.join(mod, "common", "units", "inf.txt"),
                  "r", encoding="utf-8-sig") as f:
            content = f.read()
        nodes = parse_pdx_text_to_nodes(content)
        sub = None
        for node in nodes:
            for c in node.children:
                if c.node_type == "block" and c.key == "infantry":
                    sub = c
        self.assertIsNotNone(sub)
        parsed = _parse_terrain(sub)
        self.assertEqual(parsed["forest"]["movement"], 0.2)
        self.assertEqual(parsed["forest"]["attack"], -0.1)
        self.assertEqual(parsed["forest"]["defence"], 0.1)

    def test_load_sub_units_terrain_full_and_avg_stats(self):
        from oob_loader import DivisionTemplate, division_stats, load_sub_units
        mod = self._make()
        units = load_sub_units(mod, "")
        inf = units["infantry"]
        self.assertEqual(inf["terrain_full"]["forest"]["movement"], 0.2)
        self.assertEqual(inf["terrain_full"]["forest"]["attack"], -0.1)
        self.assertEqual(inf["terrain_full"]["forest"]["defence"], 0.1)
        # 兼容：terrain 仍为 movement 映射
        self.assertEqual(inf["terrain"]["forest"], 0.2)

        tpl = DivisionTemplate(
            name="t", regiments=[("infantry", 0, 0), ("motorized", 1, 0)])
        st = division_stats(tpl, units, {})
        tf = st["terrain_full"]["forest"]
        self.assertAlmostEqual(tf["movement"], 0.1, places=6)
        self.assertAlmostEqual(tf["attack"], 0.05, places=6)
        self.assertAlmostEqual(tf["defence"], 0.2, places=6)


class SubUnitEditorTest(unittest.TestCase):
    """兵种（sub_unit）保存 roundtrip：fields/need/terrain/stats/others。"""

    def _make(self):
        mod = _mkdtemp("dsh_b7_sub_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "units")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "inf.txt"), "w", encoding="utf-8") as f:
            f.write("sub_units = {\n"
                    "\tinfantry = {\n"
                    "\t\tabbreviation = INF\n"
                    "\t\tgroup = infantry\n"
                    "\t\tsprite = Infantry\n"
                    "\t\tcombat_width = 2\n"
                    "\t\tmax_strength = 25\n"
                    "\t\tpriority = 600\n"
                    "\t\tneed = { infantry_equipment = 100 }\n"
                    "\t\tforest = { movement = 0.2 attack = -0.1 defence = 0.1 }\n"
                    "\t}\n"
                    "}\n")
        return mod

    def test_save_roundtrip(self):
        from oob_loader import load_sub_units, save_sub_unit
        mod = self._make()
        fp = save_sub_unit(
            mod, "", "infantry",
            fields={
                "group": "armor",
                "parent": "infantry_ww1",
                "sprite": "GFX_unit_x",
            },
            need={"infantry_equipment": 120, "support_equipment": 10},
            terrain={
                "forest": {"movement": -0.3, "attack": 0.1, "defence": 0.2},
                "hills": {"movement": 0.1, "attack": None, "defence": None},
            },
            stats={
                "combat_width": "3",
                "max_strength": "30",
                "maximum_speed": "4.5",
            },
            others={
                "priority": "700",
                "custom_flag": "yes",
            })
        self.assertIsNotNone(fp)
        info = load_sub_units(mod, "")["infantry"]
        self.assertEqual(info["group"], "armor")
        self.assertEqual(info["parent"], "infantry_ww1")
        self.assertEqual(info["sprite"], "GFX_unit_x")
        self.assertEqual(info["combat_width"], 3)
        self.assertEqual(info["max_strength"], 30)
        self.assertEqual(info["maximum_speed"], 4.5)
        self.assertEqual(info["need"]["infantry_equipment"], 120)
        self.assertEqual(info["need"]["support_equipment"], 10)
        self.assertEqual(info["terrain_full"]["forest"]["movement"], -0.3)
        self.assertEqual(info["terrain_full"]["forest"]["attack"], 0.1)
        self.assertEqual(info["terrain_full"]["forest"]["defence"], 0.2)
        self.assertIn("hills", info["terrain_full"])
        self.assertEqual(info["others"]["priority"], "700")
        self.assertEqual(info["others"]["custom_flag"], "yes")
        with open(fp, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("custom_flag = yes", content)


class NamesGroupTest(unittest.TestCase):
    """division_names_group 解析/保存，块级保留未编辑项。"""

    CONTENT = (
        "division_names_group = {\n"
        "\tGER_names = {\n"
        "\t\ticon = GFX_idea_old\n"
        "\t\torder = 3\n"
        "\t\tis_name = yes\n"
        "\t\tgeneric = no\n"
        "\t\tname = {\n"
        "\t\t\t\"1. Infanterie-Division\" = { is_name = yes }\n"
        "\t\t\t\"2. Infanterie-Division\" = { is_name = yes }\n"
        "\t\t}\n"
        "\t\tkeep_block = { foo = bar nested = { x = 1 } }\n"
        "\t}\n"
        "}\n"
    )

    def test_load_and_save_preserves_blocks(self):
        from oob_loader import load_names_groups, save_names_group
        groups = load_names_groups(self.CONTENT)
        self.assertIn("GER_names", groups)
        g = groups["GER_names"]
        self.assertEqual(g["icon"], "GFX_idea_old")
        self.assertEqual(g["order"], "3")
        self.assertEqual(g["is_name"], "yes")
        self.assertIn("name", g["blocks"])
        self.assertIn("keep_block", g["blocks"])

        fields = dict(g)
        fields["icon"] = "GFX_idea_new"
        fields["blocks"] = dict(g["blocks"])
        new_content = save_names_group(self.CONTENT, "GER_names", fields)
        reloaded = load_names_groups(new_content)["GER_names"]
        self.assertEqual(reloaded["icon"], "GFX_idea_new")
        self.assertEqual(reloaded["order"], "3")
        self.assertIn("name", reloaded["blocks"])
        self.assertIn("keep_block", reloaded["blocks"])
        self.assertIn("foo = bar", reloaded["blocks"]["keep_block"])

    def test_oob_file_parses_names_groups(self):
        from oob_loader import OobFile
        tmp = _mkdtemp("dsh_b7_oob_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = os.path.join(tmp, "units.txt")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(self.CONTENT)
        oob = OobFile(path)
        self.assertIn("GER_names", oob.names_groups)
        self.assertIn("GER_names", oob.names_group_ids())


class OobViewFocusTest(unittest.TestCase):
    """OOB 地编初始视野：showEvent 定位调用 + 最大连通区。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_map(self):
        from PyQt6.QtGui import QColor, QImage
        from map_loader import MapData
        mod = _mkdtemp("dsh_b7_map_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "map"), exist_ok=True)
        img = QImage(8, 8, QImage.Format.Format_RGB888)
        for y in range(8):
            for x in range(8):
                # 左半 pid1，右半 pid2 → 两块互不连通
                pid = 1 if x < 4 else 2
                img.setPixelColor(x, y, QColor(
                    (pid * 10) % 256, (pid * 20) % 256, (pid * 30) % 256))
        img.save(os.path.join(mod, "map", "provinces.bmp"), "BMP")
        with open(os.path.join(mod, "map", "definition.csv"), "w",
                  encoding="utf-8") as f:
            f.write("id;R;G;B;type;coastal;terrain;region\n")
            f.write("1;10;20;30;land;false;plains;1\n")
            f.write("2;20;40;60;land;false;plains;1\n")
        return mod, MapData(mod)

    def _stub_oob(self):
        class Tpl:
            name = "infantry_tpl"
            regiments = [("infantry",)]
        class Placement:
            def __init__(self, name, location, division_template,
                         start_experience_factor=None):
                self.name = name
                self.location = location
                self.division_template = division_template
                self.start_experience_factor = start_experience_factor
        class StubOob:
            file_path = "stub.oob"
            def __init__(self):
                self.templates = [Tpl()]
                self.placements = []
                self.modified = False
            def add_placement(self, p):
                self.placements.append(p)
            def remove_placement(self, p):
                self.placements.remove(p)
            def find_template(self, name):
                for t in self.templates:
                    if t.name == name:
                        return t
                return None
            def mark_units_modified(self):
                self.modified = True
            def save(self):
                pass
        return StubOob()

    def _make_large_map(self):
        """构造 pid1 大面积、pid2 小面积且被空白隔开的互不连通地图。"""
        from PyQt6.QtGui import QColor, QImage
        from map_loader import MapData
        mod = _mkdtemp("dsh_b7_map2_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "map"), exist_ok=True)
        img = QImage(8, 8, QImage.Format.Format_RGB888)
        img.fill(QColor(0, 0, 0))
        for y in range(8):
            for x in range(4):
                img.setPixelColor(x, y, QColor(10, 20, 30))   # pid1 大区
            for x in range(6, 8):
                img.setPixelColor(x, y, QColor(20, 40, 60))   # pid2 小区
        img.save(os.path.join(mod, "map", "provinces.bmp"), "BMP")
        with open(os.path.join(mod, "map", "definition.csv"), "w",
                  encoding="utf-8") as f:
            f.write("id;R;G;B;type;coastal;terrain;region\n")
            f.write("1;10;20;30;land;false;plains;1\n")
            f.write("2;20;40;60;land;false;plains;1\n")
        return mod, MapData(mod)

    def test_home_component_picks_largest_and_capital(self):
        from oob_map_editor import _home_component
        _mod, md = self._make_large_map()
        comps = _home_component(md, [1, 2], None)
        self.assertEqual(comps, [1], "无首都时应选最大连通区")
        comps_cap = _home_component(md, [1, 2], capital_pid=2)
        self.assertEqual(comps_cap, [2], "首都所在州优先（即使更小）")

    def test_show_event_triggers_initial_focus(self):
        from unittest.mock import patch
        from oob_map_editor import OobMapEditor
        mod, md = self._make_map()
        oob = self._stub_oob()
        dlg = OobMapEditor(oob, mod_path=mod, hoi4_path="")
        self.assertFalse(dlg._initial_focus_done)
        calls = []
        with patch.object(dlg, "_focus_region", return_value=[(1.0, 1.0)]):
            with patch.object(dlg.canvas, "fitInView",
                              side_effect=lambda *a, **k: calls.append((a, k))):
                dlg.show()
                self.app.processEvents()
        self.assertTrue(dlg._initial_focus_done)
        self.assertEqual(len(calls), 1, "showEvent 首次显示应调用 fitInView 定位")
        dlg.close()


if __name__ == "__main__":
    unittest.main()
# -*- coding: utf-8 -*-
"""批次 5：地图编辑器州字段完整表单测试。

覆盖：
- StateResTest：resources 解析（含裸值写法）/写回 roundtrip/空块删除
- StateVpNameTest：victory_points / manpower / name 解析写回 + 写回封装
- MapStatePanelSmokeTest：右侧表单加载、字段读写、保存调用链（原子写 + 本地化）
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
    """工作区内临时目录（与契约测试同策略）。"""
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class StateResTest(unittest.TestCase):
    """resources 解析 / 写回 roundtrip。"""

    STATE = (
        "state = {\n"
        "\tid = 1\n"
        "\tname = \"STATE_1\"\n"
        "\tmanpower = 100\n"
        "\tresources = {\n"
        "\t\tsteel = 6\n"
        "\t\tchromium = 3\n"
        "\t}\n"
        "\tstate_category = town\n"
        "\thistory = {\n"
        "\t\towner = FRA\n"
        "\t\tvictory_points = { 10 1 }\n"
        "\t}\n"
        "}\n"
    )

    def _load_state(self, content):
        from state_loader import StateData
        tmp = _mkdtemp("dsh_batch5_res_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        d = os.path.join(tmp, "history", "states")
        os.makedirs(d)
        with open(os.path.join(d, "1-x.txt"), "w", encoding="utf-8") as f:
            f.write(content)
        return StateData(tmp, "")

    def test_parse_resources_dict(self):
        sd = self._load_state(self.STATE)
        st = sd.states.get(1)
        self.assertIsNotNone(st)
        self.assertEqual(st["resources"], {"steel": 6, "chromium": 3})

    def test_parse_resources_bare_values(self):
        """tree_node 会把 `steel 6` 拆成 value 空值节点，需两两配对。"""
        content = self.STATE.replace(
            "steel = 6\n\t\tchromium = 3",
            "steel 6\n\t\tchromium 3")
        sd = self._load_state(content)
        st = sd.states.get(1)
        self.assertIsNotNone(st)
        self.assertEqual(st["resources"], {"steel": 6, "chromium": 3})

    def test_write_resources_roundtrip(self):
        from state_build_ops import set_state_resources_in_content
        c = set_state_resources_in_content(
            self.STATE, 1, {"steel": 8, "oil": 2})
        self.assertIn("steel = 8", c)
        self.assertIn("oil = 2", c)
        self.assertNotIn("chromium = 3", c)
        # 再解析回读
        sd = self._load_state(c)
        self.assertEqual(sd.states[1]["resources"],
                         {"steel": 8, "oil": 2})

    def test_write_resources_zero_removes_key(self):
        from state_build_ops import set_state_resources_in_content
        c = set_state_resources_in_content(
            self.STATE, 1, {"steel": 0, "chromium": 0})
        self.assertNotIn("resources", c)
        self.assertNotIn("steel =", c)

    def test_write_resources_no_block_inserts(self):
        from state_build_ops import set_state_resources_in_content
        bare = self.STATE.replace(
            "\tresources = {\n\t\tsteel = 6\n\t\tchromium = 3\n\t}\n", "")
        c = set_state_resources_in_content(bare, 1, {"aluminium": 4})
        sd = self._load_state(c)
        self.assertEqual(sd.states[1]["resources"], {"aluminium": 4})


class StateVpNameTest(unittest.TestCase):
    """victory_points / manpower / 州名 / 写回封装。"""

    STATE = (
        "state = {\n"
        "\tid = 2\n"
        "\tname = \"STATE_2\"\n"
        "\tmanpower = 5000\n"
        "\tstate_category = city\n"
        "\thistory = {\n"
        "\t\towner = GER\n"
        "\t\tvictory_points = { 10 2 11 1 }\n"
        "\t}\n"
        "}\n"
    )

    def _make_mod(self):
        mod = _mkdtemp("dsh_batch5_vp_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "history", "states")
        os.makedirs(d)
        fp = os.path.join(d, "2-x.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(self.STATE)
        return mod

    def test_parse_vp_name_manpower(self):
        from state_loader import StateData
        mod = self._make_mod()
        sd = StateData(mod, "")
        st = sd.states[2]
        self.assertEqual(st["victory_points"], [(10, 2), (11, 1)])
        self.assertEqual(st["name_key"], "STATE_2")
        self.assertEqual(st["manpower"], 5000)

    def test_write_content_functions(self):
        from state_build_ops import (
            set_state_victory_points_in_content,
            set_state_manpower_in_content,
            set_state_name_in_content,
        )
        c = set_state_victory_points_in_content(
            self.STATE, 2, [(20, 3), (30, 4)])
        self.assertIn("victory_points = { 20 3 30 4 }", c)
        c = set_state_manpower_in_content(c, 2, 8888)
        self.assertIn("manpower = 8888", c)
        c = set_state_name_in_content(c, 2, "STATE_99")
        self.assertIn('name = "STATE_99"', c)

    def test_vp_empty_removes_block(self):
        from state_build_ops import set_state_victory_points_in_content
        c = set_state_victory_points_in_content(self.STATE, 2, [])
        self.assertNotIn("victory_points", c)

    def test_wrappers_write_state_and_loc(self):
        from state_build_ops import (
            set_state_manpower, set_state_resources,
            set_state_victory_points, set_state_name,
        )
        mod = self._make_mod()
        ok, msg, rel = set_state_manpower(mod, "", 2, 12345)
        self.assertTrue(ok, msg)
        ok, msg, rel = set_state_resources(
            mod, "", 2, {"steel": 5, "oil": 2})
        self.assertTrue(ok, msg)
        ok, msg, rel = set_state_victory_points(
            mod, "", 2, [(20, 3)])
        self.assertTrue(ok, msg)
        ok, msg, rel = set_state_name(
            mod, "", 2, "STATE_2", "柏林")
        self.assertTrue(ok, msg)
        fp = os.path.join(mod, "history", "states", "2-x.txt")
        with open(fp, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("manpower = 12345", content)
        self.assertIn("steel = 5", content)
        self.assertIn("oil = 2", content)
        self.assertIn("victory_points = { 20 3 }", content)
        loc_fp = os.path.join(
            mod, "localisation", "simp_chinese",
            "generic_mod_l_simp_chinese.yml")
        self.assertTrue(os.path.isfile(loc_fp), "应生成默认 mod 本地化文件")
        with open(loc_fp, "r", encoding="utf-8-sig") as f:
            loc = f.read()
        self.assertIn("STATE_2", loc)
        self.assertIn("柏林", loc)


class MapStatePanelSmokeTest(unittest.TestCase):
    """右侧州信息表单 offscreen 冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from oob_map_editor import _MAP_CACHE, _STATE_CACHE
        _MAP_CACHE.clear()
        _STATE_CACHE.clear()

    def _make_env(self):
        """临时 mod：小地图 + 州文件（含 resources/VP）+ 类别/建筑/国家色。"""
        from PyQt6.QtGui import QColor, QImage
        mod = _mkdtemp("dsh_batch5_ui_")
        game = _mkdtemp("dsh_batch5_ui_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        for base in (mod, game):
            os.makedirs(os.path.join(base, "map"), exist_ok=True)
            os.makedirs(os.path.join(base, "history", "states"),
                        exist_ok=True)
            img = QImage(8, 8, QImage.Format.Format_RGB888)
            for y in range(8):
                for x in range(8):
                    pid = 1 if x < 4 else 2
                    img.setPixelColor(x, y, QColor(
                        (pid * 20) % 256, (pid * 40) % 256,
                        (pid * 60) % 256))
            img.save(os.path.join(base, "map", "provinces.bmp"), "BMP")
            with open(os.path.join(base, "map", "definition.csv"),
                      "w", encoding="utf-8") as f:
                f.write("id;R;G;B;type;coastal;terrain;region\n")
                f.write("1;20;40;60;land;false;plains;1\n")
                f.write("2;40;80;120;land;false;plains;1\n")
        # 州文件在 mod 内
        with open(os.path.join(mod, "history", "states", "1-x.txt"),
                  "w", encoding="utf-8") as f:
            f.write(
                "state = {\n"
                "\tid = 1\n"
                "\tname = \"STATE_1\"\n"
                "\tmanpower = 123456\n"
                "\tstate_category = town\n"
                "\tresources = {\n"
                "\t\tsteel = 12\n"
                "\t}\n"
                "\thistory = {\n"
                "\t\towner = GER\n"
                "\t\tvictory_points = { 10 2 }\n"
                "\t}\n"
                "\tprovinces = { 1 2 }\n"
                "}\n")
        os.makedirs(os.path.join(mod, "common", "state_category"),
                    exist_ok=True)
        with open(os.path.join(mod, "common", "state_category", "c.txt"),
                  "w", encoding="utf-8") as f:
            f.write("state_categories={\n"
                    "\ttown = {\n\t\tlocal_building_slots = 4\n\t}\n"
                    "\trural = {\n\t\tlocal_building_slots = 2\n\t}\n"
                    "}\n")
        os.makedirs(os.path.join(mod, "common", "buildings"), exist_ok=True)
        with open(os.path.join(mod, "common", "buildings", "b.txt"),
                  "w", encoding="utf-8") as f:
            f.write("buildings = {\n"
                    "\tinfrastructure = {\n\t\tvalue = 1\n\t}\n"
                    "\tnaval_base = {\n\t\tprovince_max = 10\n\t}\n"
                    "}\n")
        os.makedirs(os.path.join(mod, "common", "countries"), exist_ok=True)
        with open(os.path.join(mod, "common", "countries", "GER.txt"),
                  "w", encoding="utf-8") as f:
            f.write("color = { 51 204 51 }\n")
        # 中文本地化：州名/类别名
        loc_dir = os.path.join(mod, "localisation", "simp_chinese")
        os.makedirs(loc_dir, exist_ok=True)
        with open(os.path.join(loc_dir, "test_l_simp_chinese.yml"),
                  "w", encoding="utf-8-sig") as f:
            f.write("l_simp_chinese:\n"
                    " STATE_1: \"测试州\"\n"
                    " STATE_CATEGORY_town: \"城镇\"\n"
                    " STATE_CATEGORY_rural: \"乡村\"\n")
        return mod, game

    def test_form_loads_state_fields(self):
        from map_editor_dialog import MapEditorDialog
        mod, game = self._make_env()
        dlg = MapEditorDialog(mod_path=mod, game_path=game)
        dlg.show()
        self.app.processEvents()
        dlg._on_province_clicked(1, 0, 0)
        self.assertTrue(dlg.state_group.isEnabled())
        self.assertEqual(dlg.state_id_label.text(), "1")
        self.assertEqual(dlg.state_name_edit.text(), "STATE_1")
        self.assertEqual(dlg.state_name_cn_edit.text(), "测试州")
        self.assertEqual(dlg.state_category_combo.currentData(), "town")
        self.assertEqual(dlg.state_manpower_spin.value(), 123456)
        self.assertIn(("steel", "12"), dlg.state_resources_table.rows())
        self.assertIn(("10", "2"), dlg.state_vp_table.rows())
        # 建筑/归属/国家颜色按钮保留原样可用
        self.assertTrue(dlg.place_btn.isEnabled())
        self.assertTrue(dlg.owner_btn.isEnabled())
        self.assertTrue(dlg.color_btn.isEnabled())
        dlg.close()

    def test_save_state_fields_chain(self):
        from unittest.mock import patch
        from map_editor_dialog import MapEditorDialog
        mod, game = self._make_env()
        dlg = MapEditorDialog(mod_path=mod, game_path=game)
        dlg.show()
        self.app.processEvents()
        dlg._on_province_clicked(1, 0, 0)

        dlg.state_name_cn_edit.setText("新州名")
        dlg.state_manpower_spin.setValue(999)
        dlg.state_category_combo.setCurrentIndex(
            dlg.state_category_combo.findData("rural"))
        dlg.state_resources_table.set_data([("steel", "15"), ("oil", "3")])
        dlg.state_vp_table.set_data([("10", "5"), ("20", "8")])

        from PyQt6.QtWidgets import QMessageBox
        calls = []
        with patch.object(QMessageBox, "information",
                          side_effect=lambda *a, **k: calls.append(a) or None), \
             patch.object(QMessageBox, "critical",
                          side_effect=lambda *a, **k: calls.append(a) or None):
            dlg._save_state_fields()

        self.assertTrue(calls, "保存后应弹成功提示")
        fp = os.path.join(mod, "history", "states", "1-x.txt")
        with open(fp, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("state_category = rural", content)
        self.assertIn("manpower = 999", content)
        self.assertIn("steel = 15", content)
        self.assertIn("oil = 3", content)
        self.assertIn("victory_points = { 10 5 20 8 }", content)
        loc_file = os.path.join(
            mod, "localisation", "simp_chinese",
            "test_l_simp_chinese.yml")
        self.assertTrue(os.path.isfile(loc_file),
                        "应按 STATE_1 已有键写入现有本地化文件")
        with open(loc_file, "r", encoding="utf-8-sig") as f:
            loc = f.read()
        self.assertIn("STATE_1", loc)
        self.assertIn("新州名", loc)
        # StateData.reload() 后内存字段已刷新
        st = dlg.state_data.states[1]
        self.assertEqual(st["state_category"], "rural")
        self.assertEqual(st["manpower"], 999)
        self.assertEqual(st["resources"], {"steel": 15, "oil": 3})
        self.assertEqual(st["victory_points"], [(10, 5), (20, 8)])
        dlg.close()


if __name__ == "__main__":
    unittest.main()
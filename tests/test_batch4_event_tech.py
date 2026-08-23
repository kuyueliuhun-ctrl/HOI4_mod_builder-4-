# -*- coding: utf-8 -*-
"""批次 4：事件 + 科技专用编辑器数据层/UI 冒烟/路由定向测试。"""

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


def _event_content():
    return (
        "add_namespace = TST\n"
        "country_event = {\n"
        "\tid = TST.1\n"
        "\ttitle = TST_TITLE\n"
        "\tdesc = TST_DESC\n"
        "\tpicture = GFX_event_tst\n"
        "\tmajor = no\n"
        "\tis_triggered_only = yes\n"
        "\tfire_only_once = no\n"
        "\thidden = no\n"
        "\tminor_flavor = yes\n"
        "\tmean_time_to_happen = {\n"
        "\t\tdays = 30\n"
        "\t\tmodifier = {\n"
        "\t\t\tfactor = 0.5\n"
        "\t\t}\n"
        "\t}\n"
        "\timmediate = {\n"
        "\t\tset_country_flag = TST_FLAG\n"
        "\t}\n"
        "\tafter = {\n"
        "\t\thours = 24\n"
        "\t}\n"
        "\toption = {\n"
        "\t\tname = TST_OPT1\n"
        "\t\ttrigger = { has_war = no }\n"
        "\t\tai_chance = { factor = 1 }\n"
        "\t\tadd_political_power = 25\n"
        "\t}\n"
        "\toption = {\n"
        "\t\tname = TST_OPT2\n"
        "\t\tadd_stability = 0.1\n"
        "\t}\n"
        "}\n"
    )


def _event_content_with_unit():
    """含 unit_leader_event 与文件级顶层常量/非事件键的样例。"""
    return (
        "@WARLORD_SUPPORT_CIV_BASE_STEPS = 180\n"
        "some_top_key = yes\n"
        "add_namespace = TST\n"
        "country_event = {\n"
        "\tid = TST.1\n"
        "\ttitle = TST_TITLE\n"
        "\tdesc = TST_DESC\n"
        "\toption = { name = TST_OPT }\n"
        "}\n"
        "unit_leader_event = {\n"
        "\tid = TST.UL1\n"
        "\ttitle = TST_UL_TITLE\n"
        "\tdesc = TST_UL_DESC\n"
        "\toption = { name = TST_UL_OPT }\n"
        "}\n"
    )


def _tech_content():
    return (
        "technologies = {\n"
        "\tinfantry_weapons = {\n"
        "\t\tstart_year = 1936\n"
        "\t\tresearch_cost = 100\n"
        "\t\tcategories = { infantry_tech }\n"
        "\t\tfolder = { name = infantry_folder position = { x = 1 y = 2 } }\n"
        "\t\tpath = {\n"
        "\t\t\tleads_to_tech = infantry_weapons2\n"
        "\t\t\tresearch_cost_coeff = 0.9\n"
        "\t\t}\n"
        "\t\tenable_equipments = { infantry_equipment_0 }\n"
        "\t\tallow = { has_dlc = \"arms\" }\n"
        "\t\tai_will_do = { factor = 1 }\n"
        "\t\tpriority = 5\n"
        "\t\tspecial_project_specialization = special_project_01\n"
        "\t\tcategory_infantry_equipment = {\n"
        "\t\t\tinfantry_equipment = { soft_attack = 1 }\n"
        "\t\t}\n"
        "\t\tsub_technologies = { infantry_weapons_1 }\n"
        "\t}\n"
        "}\n"
    )


class Batch4EventDataTest(unittest.TestCase):
    """事件数据层：解析 / CRUD / 第 N 个 option 替换 roundtrip。"""

    def _make(self):
        mod = _mkdtemp("dsh_b4_evt_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "events")
        os.makedirs(d)
        with open(os.path.join(d, "test.txt"), "w", encoding="utf-8") as f:
            f.write(_event_content())
        return mod

    def test_parse_full_event(self):
        from event_data import load_event_entities
        mod = self._make()
        events = load_event_entities(mod, "")
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e["id"], "TST.1")
        self.assertEqual(e["type"], "country_event")
        self.assertEqual(e["title"], "TST_TITLE")
        self.assertEqual(e["desc"], "TST_DESC")
        self.assertTrue(e["is_triggered_only"])
        self.assertEqual(e["option_count"], 2)
        self.assertEqual(e["namespace"], "TST")
        self.assertEqual(e["mean_time_to_happen"]["days"], "30")
        self.assertIn("modifier", e["mean_time_to_happen"]["modifier"])
        self.assertIn("TST_FLAG", e["immediate"])
        self.assertIn("hours = 24", e["after"])
        self.assertEqual(len(e["options"]), 2)
        self.assertEqual(e["options"][0]["name"], "TST_OPT1")
        self.assertEqual(e["options"][1]["name"], "TST_OPT2")
        self.assertIn(("minor_flavor", "yes"), e["other_fields"])

    def test_option_nth_replace_roundtrip(self):
        from event_data import replace_nth_child
        content = _event_content()
        new_opt = "option = {\n\tname = TST_OPT2_NEW\n\tadd_stability = 0.2\n}"
        new_content = replace_nth_child(content, "TST.1", "option", 1, new_opt)
        self.assertIn("TST_OPT2_NEW", new_content)
        self.assertNotIn("TST_OPT2\n", new_content)
        # 第一个 option 保持不变
        self.assertIn("TST_OPT1", new_content)

    def test_parse_unit_leader_event(self):
        from event_data import load_event_entities
        mod = _mkdtemp("dsh_b4_evt_ul_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "events")
        os.makedirs(d)
        with open(os.path.join(d, "test.txt"), "w", encoding="utf-8") as f:
            f.write(_event_content_with_unit())
        events = load_event_entities(mod, "")
        self.assertEqual(len(events), 2)
        types = {e["type"] for e in events}
        self.assertIn("unit_leader_event", types)
        ul = next(e for e in events if e["type"] == "unit_leader_event")
        self.assertEqual(ul["id"], "TST.UL1")
        self.assertEqual(ul["title"], "TST_UL_TITLE")
        self.assertEqual(ul["namespace"], "TST")

    def test_file_other_fields_roundtrip(self):
        from event_data import (
            apply_file_other_fields, parse_file_other_fields,
        )
        content = _event_content_with_unit()
        rows = parse_file_other_fields(content)
        self.assertIn(("@WARLORD_SUPPORT_CIV_BASE_STEPS", "180"), rows)
        self.assertIn(("some_top_key", "yes"), rows)
        self.assertIn(("add_namespace", "TST"), rows)

        changes = list(rows)
        changes.append(("@WARLORD_SUPPORT_CIV_BASE_STEPS", "200"))
        changes.append(("some_top_key", ""))
        changes.append(("NEW_TOP_CONST", "42"))
        new_content = apply_file_other_fields(content, changes)
        self.assertIn("@WARLORD_SUPPORT_CIV_BASE_STEPS = 200", new_content)
        self.assertNotIn("some_top_key = yes", new_content)
        self.assertIn("NEW_TOP_CONST = 42", new_content)
        self.assertIn("add_namespace = TST", new_content)
        self.assertIn("country_event = {", new_content)
        self.assertIn("unit_leader_event = {", new_content)

    def test_crud_roundtrip(self):
        from event_data import (
            delete_event, duplicate_event, insert_event, rename_event,
        )
        content = _event_content()
        content = insert_event(content, "TST.2", "country_event", "TST")
        self.assertIn("country_event = {", content)
        self.assertIn("id = TST.2", content)
        content = rename_event(content, "TST.2", "TST.3")
        self.assertIn("id = TST.3", content)
        self.assertNotIn("id = TST.2\n", content)
        content = duplicate_event(content, "TST.3", "TST.4")
        self.assertIn("id = TST.4", content)
        content = delete_event(content, "TST.4")
        self.assertNotIn("id = TST.4", content)
        content = delete_event(content, "TST.3")
        content = delete_event(content, "TST.1")
        self.assertNotIn("country_event", content)


class Batch4EventEditorSmokeTest(unittest.TestCase):
    """事件编辑器 offscreen 冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make(self):
        mod = _mkdtemp("dsh_b4_evtui_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "events")
        os.makedirs(d)
        with open(os.path.join(d, "test.txt"), "w", encoding="utf-8") as f:
            f.write(_event_content())
        return mod

    def test_dialog_loads_and_filters(self):
        from event_editor_dialog import EventEditorDialog
        mod = self._make()
        dlg = EventEditorDialog(mod_path=mod)
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.sidebar.list.count(), 1)
        self.assertEqual(dlg.id_edit.text(), "TST.1")
        self.assertEqual(dlg.title_edit.text(), "TST_TITLE")
        self.assertEqual(dlg.options_label.text(), "2")
        dlg.filter_combo.setCurrentIndex(2)  # news_event
        self.app.processEvents()
        self.assertEqual(dlg.sidebar.list.count(), 0)
        dlg.close()

    def test_unit_leader_filter_and_file_fields_table(self):
        from event_editor_dialog import EventEditorDialog
        mod = _mkdtemp("dsh_b4_evtui_ul_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "events")
        os.makedirs(d)
        with open(os.path.join(d, "test.txt"), "w", encoding="utf-8") as f:
            f.write(_event_content_with_unit())
        dlg = EventEditorDialog(mod_path=mod)
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.sidebar.list.count(), 2)
        dlg.filter_combo.setCurrentIndex(3)  # unit_leader_event
        self.app.processEvents()
        self.assertEqual(dlg.sidebar.list.count(), 1)
        self.assertIn("unit_leader_event", dlg.sidebar.list.item(0).text())
        # 文件级其他字段表应加载顶层常量 / add_namespace
        rows = dlg.file_other_fields_table.rows()
        self.assertIn(("@WARLORD_SUPPORT_CIV_BASE_STEPS", "180"), rows)
        self.assertIn(("add_namespace", "TST"), rows)
        dlg.close()


class Batch4TechDataTest(unittest.TestCase):
    """科技数据层：解析 / 表单字段写回 roundtrip / CRUD。"""

    def _make(self):
        mod = _mkdtemp("dsh_b4_tech_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "technologies")
        os.makedirs(d)
        with open(os.path.join(d, "test.txt"), "w", encoding="utf-8") as f:
            f.write(_tech_content())
        return mod

    def test_parse_full_tech(self):
        from tech_data import load_tech_entities
        mod = self._make()
        techs = load_tech_entities(mod, "")
        self.assertIn("infantry_weapons", techs)
        t = techs["infantry_weapons"]
        self.assertEqual(t["start_year"], "1936")
        self.assertEqual(t["research_cost"], "100")
        self.assertEqual(t["folder"], "infantry_folder")
        self.assertEqual(t["position_x"], "1")
        self.assertEqual(t["position_y"], "2")
        self.assertEqual(t["categories"], ["infantry_tech"])
        self.assertEqual(t["path"][0]["leads_to_tech"], "infantry_weapons2")
        self.assertEqual(t["path"][0]["research_cost_coeff"], "0.9")
        self.assertEqual(t["enable_equipments"], ["infantry_equipment_0"])
        self.assertIn("has_dlc", t["allow"])
        self.assertIn("factor = 1", t["ai_will_do"])
        self.assertTrue(any(k.startswith("category_") for k, _v in t["category_blocks"]))

    def test_apply_tech_edits_roundtrip(self):
        from tech_data import apply_tech_edits
        content = _tech_content()
        new = apply_tech_edits(
            content, "infantry_weapons",
            fields={"start_year": "1939", "research_cost": "200"},
            categories=["infantry_tech", "new_category"],
            enable_equipments=["infantry_equipment_0", "infantry_equipment_1"],
            paths=[{"leads_to_tech": "infantry_weapons3",
                    "research_cost_coeff": "1.2"}],
            folder_position={"name": "artillery_folder", "x": 3, "y": 4},
        )
        self.assertIn("start_year = 1939", new)
        self.assertIn("research_cost = 200", new)
        self.assertIn("categories = { infantry_tech new_category }", new)
        self.assertIn("enable_equipments = { infantry_equipment_0", new)
        self.assertIn("infantry_weapons3", new)
        self.assertIn("name = artillery_folder", new)
        self.assertIn("x = 3", new)
        self.assertIn("y = 4", new)

    def test_crud_roundtrip(self):
        from tech_data import delete_tech, duplicate_tech, insert_tech, rename_tech
        content = _tech_content()
        content = insert_tech(content, "new_tech", folder="infantry_folder")
        self.assertIn("new_tech = {", content)
        content = rename_tech(content, "new_tech", "new_tech_2")
        self.assertIn("new_tech_2 = {", content)
        self.assertNotIn("new_tech = {", content)
        content = duplicate_tech(content, "new_tech_2", "new_tech_3")
        self.assertIn("new_tech_3 = {", content)
        content = delete_tech(content, "new_tech_3")
        content = delete_tech(content, "new_tech_2")
        self.assertNotIn("new_tech_2", content)


class Batch4TechEditorSmokeTest(unittest.TestCase):
    """科技编辑器 offscreen 冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make(self):
        mod = _mkdtemp("dsh_b4_techui_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "technologies")
        os.makedirs(d)
        with open(os.path.join(d, "test.txt"), "w", encoding="utf-8") as f:
            f.write(_tech_content())
        return mod

    def test_dialog_loads_and_tree_selects(self):
        from tech_editor_dialog import TechEditorDialog
        mod = self._make()
        dlg = TechEditorDialog(mod_path=mod)
        dlg.show()
        self.app.processEvents()
        # 兼容旧测试的隐藏 sidebar 数据同步
        self.assertEqual(dlg.sidebar.list.count(), 1)
        self.assertEqual(dlg.id_edit.text(), "infantry_weapons")
        self.assertEqual(dlg.start_year_edit.text(), "1936")
        self.assertEqual(dlg.tree.topLevelItemCount(), 1)
        self.assertEqual(dlg.tree.topLevelItem(0).childCount(), 1)
        self.assertEqual(dlg.categories_list.count(), 1)
        self.assertEqual(dlg.path_table.rowCount(), 1)
        dlg.close()


class Batch4TechDoubleClickOpenTest(unittest.TestCase):
    """画布双击联动：_open_tech_in_editor 打开专用编辑器并连接保存刷新。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_open_tech_editor_and_saved_refresh(self):
        from unittest.mock import patch
        from focus_view_ctrl import TechTreeControllerMixin
        tmp = _mkdtemp("dsh_b4_dbl_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        fp = os.path.join(tmp, "tech.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(_tech_content())

        calls = {}
        saved_callbacks = []
        fake_dlg = type("FakeTechDlg", (), {})()
        fake_dlg.saved = type("FakeSignal", (), {
            "connect": lambda self, cb: saved_callbacks.append(cb)
        })()

        class Dummy:
            _view_mode = "tech"
            _tech_data = {}
            _tech_files = {}
            _redraw_called = False
            _refresh_called = False

            def window(self):
                return self

            def _redraw_tech_tree(self):
                self._redraw_called = True

            def _refresh_tech_tree_after_save(self, file_path):
                self._refresh_called = True

        obj = Dummy()

        with patch("tech_editor_dialog.open_tech_editor",
                   return_value=fake_dlg) as mock_open, \
                patch("focus_view_ctrl._get_mod_path", return_value="MOD"), \
                patch("focus_view_ctrl._get_hoi4_path", return_value="HOI4"):
            TechTreeControllerMixin._open_tech_in_editor(obj, fp, "infantry_weapons")
        self.assertEqual(len(mock_open.call_args_list), 1)
        args, kwargs = mock_open.call_args_list[0]
        self.assertEqual(args[0], "MOD")
        self.assertEqual(args[1], "HOI4")
        self.assertEqual(kwargs["file_path"], fp)
        self.assertEqual(kwargs["tech_id"], "infantry_weapons")
        self.assertTrue(saved_callbacks, "保存后应连接画布刷新回调")

        # 触发保存回调：保存后应调用画布刷新
        saved_callbacks[0]()
        self.assertTrue(obj._refresh_called)


class Batch4WorkbenchRouteTest(unittest.TestCase):
    """工作台事件文件双击直开事件编辑器；app_routes 科技路由存在。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_event_file_double_click_emits_generic(self):
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import Qt
        from workbench import WorkbenchDock
        mod = _mkdtemp("dsh_b4_wbevt_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "events")
        os.makedirs(d)
        fp = os.path.join(d, "test.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(_event_content())
        wb = WorkbenchDock(mod_path=mod)
        wb._current_type = "event"
        received = []
        gallery = []
        wb.generic_file_selected.connect(lambda f, e: received.append((f, e)))
        wb.entity_gallery_requested.connect(lambda t, f: gallery.append((t, f)))
        it = QListWidgetItem("test.txt")
        it.setData(Qt.ItemDataRole.UserRole, fp)
        wb._on_file_double_clicked(it)
        self.assertEqual(len(received), 1)
        self.assertTrue(received[0][0].endswith("test.txt"))
        self.assertEqual(gallery, [])

    def test_app_route_has_tech_editor(self):
        from app_routes import find_route
        norm, route = find_route("E:/mod/common/technologies/00_tech.txt")
        self.assertIsNotNone(route, "common/technologies 应路由到科技专用编辑器")
        self.assertEqual(route[0], "common/technologies")


if __name__ == "__main__":
    unittest.main()
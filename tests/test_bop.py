"""契约测试：原子写 / 写入契约 / 导出前健康检查 / 写入纪律扫描

运行：
    python -m unittest discover -s tests -v
    （或 python tools/verify_contracts.py 一键运行全部契约）
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
    """工作区内临时目录（沙箱不允许写系统 %TEMP%）。

    契约测试统一在这里建临时目录，测试结束时由 addCleanup 清理。
    """
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class BopLoaderTest(unittest.TestCase):
    """力量平衡数据层：解析 common/bop + 关联决策分类动作。"""

    def _make_env(self):
        from bop_loader import _BOP_CACHE
        _BOP_CACHE.clear()
        mod = _mkdtemp("dsh_bop_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "bop"), exist_ok=True)
        os.makedirs(os.path.join(mod, "common", "decisions"), exist_ok=True)
        with open(os.path.join(mod, "common", "bop", "ITA.txt"),
                  "w", encoding="utf-8") as f:
            f.write("ITA_power_balance = {\n"
                    "\tinitial_value = 0.35\n"
                    "\tleft_side = ITA_grand_council_side\n"
                    "\tright_side = ITA_mussolini_side\n"
                    "\tdecision_category = ITA_balance_of_power_category\n"
                    "\trange = {\n"
                    "\t\tid = ITA_balance_range\n"
                    "\t\tmin = -0.10\n"
                    "\t\tmax = 0.10\n"
                    "\t\tmodifier = { }\n"
                    "\t}\n"
                    "\tside = {\n"
                    "\t\tid = ITA_grand_council_side\n"
                    "\t\ticon = GFX_bop_ITA_grand_council_side\n"
                    "\t\trange = {\n"
                    "\t\t\tid = ITA_grand_council_low_control_range\n"
                    "\t\t\tmin = -0.3\n"
                    "\t\t\tmax = -0.1\n"
                    "\t\t\tmodifier = { political_advisor_cost_factor = -0.1 }\n"
                    "\t\t}\n"
                    "\t}\n"
                    "}\n")
        with open(os.path.join(mod, "common", "decisions", "ITA.txt"),
                  "w", encoding="utf-8") as f:
            f.write("ITA_balance_of_power_category = {\n"
                    "\tDEBUG_debug_action = {\n"
                    "\t\tpriority = 1\n"
                    "\t\tcomplete_effect = { }\n"
                    "\t}\n"
                    "\tITA_bop_military_parade = {\n"
                    "\t\tcost = ITA_bop_generic_council_cost\n"
                    "\t\tcomplete_effect = { ITA_bop_very_low_increase_effect = yes }\n"
                    "\t}\n"
                    "\tITA_bop_slander_the_duce = {\n"
                    "\t\tcost = 25\n"
                    "\t\tcomplete_effect = { add_power_balance_value = { id = ITA_power_balance value = -0.1 } }\n"
                    "\t}\n"
                    "}\n")
        return mod

    def test_parse_bop_file(self):
        from bop_loader import parse_bop_file
        mod = self._make_env()
        with open(os.path.join(mod, "common", "bop", "ITA.txt"),
                  "r", encoding="utf-8-sig") as f:
            content = f.read()
        bop = parse_bop_file(content)
        self.assertIsNotNone(bop)
        self.assertEqual(bop["id"], "ITA_power_balance")
        self.assertAlmostEqual(bop["initial_value"], 0.35)
        self.assertEqual(bop["left_side"], "ITA_grand_council_side")
        self.assertEqual(bop["right_side"], "ITA_mussolini_side")
        self.assertEqual(len(bop["ranges"]), 1)
        self.assertEqual(len(bop["sides"]), 1)
        self.assertEqual(bop["sides"][0]["ranges"][0]["modifier"]
                         .get("political_advisor_cost_factor"), -0.1)

    def test_load_bop_actions_filters_debug(self):
        from bop_loader import load_bop_definitions, load_bop_actions
        mod = self._make_env()
        bop = load_bop_definitions(mod, "")["ITA"]
        acts = load_bop_actions(mod, "", bop["decision_category"])
        keys = [a["key"] for a in acts]
        self.assertIn("ITA_bop_military_parade", keys)
        self.assertIn("ITA_bop_slander_the_duce", keys)
        self.assertFalse(any(k.startswith("DEBUG_") for k in keys),
                         "应过滤 DEBUG 决议")
        by_key = {a["key"]: a for a in acts}
        self.assertEqual(by_key["ITA_bop_military_parade"]["delta"], 1)
        self.assertAlmostEqual(
            by_key["ITA_bop_slander_the_duce"]["delta"], -0.1, places=3)

    def test_find_active_range(self):
        from bop_loader import find_active_range
        mod = self._make_env()
        from bop_loader import load_bop_definitions
        bop = load_bop_definitions(mod, "")["ITA"]
        side, rng = find_active_range(bop, -0.2)
        self.assertIsNotNone(side)
        self.assertEqual(side["id"], "ITA_grand_council_side")
        self.assertEqual(rng["id"], "ITA_grand_council_low_control_range")
        side, rng = find_active_range(bop, 0.0)
        self.assertIsNone(side)
        self.assertEqual(rng["id"], "ITA_balance_range")


class BopEditorDialogSmokeTest(unittest.TestCase):
    """力量平衡专用编辑器冒烟（offscreen）：滑块/动作/保存。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from bop_loader import _BOP_CACHE
        _BOP_CACHE.clear()
        mod = _mkdtemp("dsh_boped_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "bop"), exist_ok=True)
        os.makedirs(os.path.join(mod, "common", "decisions"), exist_ok=True)
        with open(os.path.join(mod, "common", "bop", "ITA.txt"),
                  "w", encoding="utf-8") as f:
            f.write("ITA_power_balance = {\n"
                    "\tinitial_value = 0.35\n"
                    "\tleft_side = ITA_grand_council_side\n"
                    "\tright_side = ITA_mussolini_side\n"
                    "\tdecision_category = ITA_balance_of_power_category\n"
                    "\trange = { id = ITA_balance_range min = -0.10 max = 0.10 modifier = { } }\n"
                    "\tside = { id = ITA_grand_council_side icon = GFX_x\n"
                    "\t\trange = { id = r1 min = -0.3 max = -0.1 modifier = { } }\n"
                    "\t}\n"
                    "}\n")
        with open(os.path.join(mod, "common", "decisions", "ITA.txt"),
                  "w", encoding="utf-8") as f:
            f.write("ITA_balance_of_power_category = {\n"
                    "\tITA_bop_military_parade = {\n"
                    "\t\tcost = ITA_bop_generic_council_cost\n"
                    "\t\tcomplete_effect = { ITA_bop_very_low_increase_effect = yes }\n"
                    "\t}\n"
                    "\tITA_bop_slander_the_duce = {\n"
                    "\t\tcost = 25\n"
                    "\t\tcomplete_effect = { add_power_balance_value = { id = ITA_power_balance value = -0.1 } }\n"
                    "\t}\n"
                    "}\n")
        return mod

    def test_dialog_builds_and_saves(self):
        from unittest.mock import patch
        from PyQt6.QtWidgets import QMessageBox
        from bop_loader import load_bop_definitions
        from bop_editor_dialog import BopEditorDialog
        mod = self._make_env()
        bop = load_bop_definitions(mod, "")["ITA"]
        dlg = BopEditorDialog(bop, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(len(dlg.actions), 2, "应解析出 2 个非 DEBUG 动作")
        self.assertIsNotNone(dlg.slider)
        # 拖动滑块到 0.5 并保存
        dlg.slider.setValue(50)
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            dlg._save_initial_value()
        with open(os.path.join(mod, "common", "bop", "ITA.txt"),
                  "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("initial_value = 0.5000", content,
                      "保存应写回滑块对应 initial_value")
        dlg.close()

    def test_dialog_localizes_and_has_edit_controls(self):
        from bop_loader import load_bop_definitions
        from bop_editor_dialog import BopEditorDialog, _loc_text
        mod = self._make_env()
        loc_dir = os.path.join(mod, "localisation", "simp_chinese")
        os.makedirs(loc_dir, exist_ok=True)
        with open(os.path.join(loc_dir, "bop_l_simp_chinese.yml"),
                  "w", encoding="utf-8") as f:
            f.write("l_simp_chinese:\n"
                    " ITA_power_balance: \"国家权力平衡\"\n"
                    " ITA_grand_council_side: \"大议会\"\n"
                    " ITA_mussolini_side: \"墨索里尼\"\n"
                    " ITA_balance_range: \"平衡区间\"\n"
                    " ITA_bop_military_parade: \"£BoP_right_texticon 举行阅兵式\"\n"
                    " ITA_bop_slander_the_duce: \"诋毁领袖\"\n"
                    " MODIFIER_POLITICAL_ADVISOR_COST_FACTOR: \"政治顾问花费\"\n")
        bop = load_bop_definitions(mod, "")["ITA"]
        dlg = BopEditorDialog(bop, mod, "")
        dlg.show()
        self.app.processEvents()
        dlg.slider.setValue(-20)  # 命中大议会的低控制区间
        self.app.processEvents()
        self.assertEqual(dlg.status_label.text(), "当前状态：大议会",
                         "状态应显示本地化势力名")
        self.assertEqual(dlg.tabs.count(), 2, "应有动作/势力与修正两个页")
        self.assertEqual(_loc_text(dlg._loc, "ITA_bop_military_parade"),
                         "举行阅兵式", "动作名应去除 HOI4 图标 token 并显示中文")
        self.assertTrue(hasattr(dlg, "left_edit"))
        self.assertTrue(hasattr(dlg, "right_edit"))
        self.assertTrue(hasattr(dlg, "decision_edit"))
        dlg.close()

    def test_dialog_shows_current_modifiers(self):
        from bop_loader import load_bop_definitions
        from bop_editor_dialog import BopEditorDialog
        mod = self._make_env()
        loc_dir = os.path.join(mod, "localisation", "simp_chinese")
        os.makedirs(loc_dir, exist_ok=True)
        with open(os.path.join(loc_dir, "bop_l_simp_chinese.yml"),
                  "w", encoding="utf-8") as f:
            f.write("l_simp_chinese:\n"
                    " MODIFIER_POLITICAL_ADVISOR_COST_FACTOR: \"政治顾问花费\"\n")
        # 给大议会的低控制区间加修正
        bop_fp = os.path.join(mod, "common", "bop", "ITA.txt")
        with open(bop_fp, "w", encoding="utf-8") as f:
            f.write("ITA_power_balance = {\n"
                    "\tinitial_value = 0.35\n"
                    "\tleft_side = ITA_grand_council_side\n"
                    "\tright_side = ITA_mussolini_side\n"
                    "\tdecision_category = ITA_balance_of_power_category\n"
                    "\trange = { id = ITA_balance_range min = -0.10 max = 0.10 modifier = { } }\n"
                    "\tside = { id = ITA_grand_council_side icon = GFX_x\n"
                    "\t\trange = { id = r1 min = -0.3 max = -0.1 modifier = { political_advisor_cost_factor = -0.1 } }\n"
                    "\t}\n"
                    "}\n")
        bop = load_bop_definitions(mod, "")["ITA"]
        dlg = BopEditorDialog(bop, mod, "")
        dlg.show()
        self.app.processEvents()
        dlg.slider.setValue(-20)
        self.app.processEvents()
        self.assertIn("政治顾问花费", dlg.modifiers_label.text(),
                      "当前区间修正应显示本地化修饰名")
        self.assertIn("当前修正", dlg.modifiers_label.text())
        dlg.close()

    def test_save_changes_updates_basic_fields(self):
        from unittest.mock import patch
        from bop_loader import load_bop_definitions
        from bop_editor_dialog import BopEditorDialog
        mod = self._make_env()
        bop = load_bop_definitions(mod, "")["ITA"]
        dlg = BopEditorDialog(bop, mod, "")
        dlg.left_edit.setText("NEW_LEFT")
        dlg.right_edit.setText("NEW_RIGHT")
        dlg.decision_edit.setText("NEW_CAT")
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            dlg._save_changes()
        with open(os.path.join(mod, "common", "bop", "ITA.txt"),
                  "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("left_side = NEW_LEFT", content)
        self.assertIn("right_side = NEW_RIGHT", content)
        self.assertIn("decision_category = NEW_CAT", content)
        dlg.close()

    def test_edit_action_opens_tree_editor(self):
        from unittest.mock import patch
        from bop_loader import load_bop_definitions
        from bop_editor_dialog import BopEditorDialog
        mod = self._make_env()
        bop = load_bop_definitions(mod, "")["ITA"]
        dlg = BopEditorDialog(bop, mod, "")
        action = dlg.actions[0]
        with patch("bop_editor_dialog.BopEditorDialog._open_tree_editor_for_file") as m:
            dlg._edit_action(action)
        self.assertEqual(m.call_count, 1)
        self.assertEqual(m.call_args[0][0], action["file"])
        self.assertEqual(m.call_args[1]["entity_id"], action["key"])
        dlg.close()

    def test_edit_bop_file_opens_tree_editor(self):
        from unittest.mock import patch
        from bop_loader import load_bop_definitions
        from bop_editor_dialog import BopEditorDialog
        mod = self._make_env()
        bop = load_bop_definitions(mod, "")["ITA"]
        dlg = BopEditorDialog(bop, mod, "")
        with patch("bop_editor_dialog.BopEditorDialog._open_tree_editor_for_file") as m:
            dlg._edit_bop_file()
        self.assertEqual(m.call_count, 1)
        self.assertEqual(m.call_args[0][0], bop["file"])
        self.assertEqual(m.call_args[1]["entity_id"], bop["id"])
        dlg.close()


class BopWorkbenchRouteTest(unittest.TestCase):
    """力量平衡：文件模式/无文件模式双击应直达专用编辑器。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from workbench import WorkbenchDock
        mod = _mkdtemp("dsh_wbbop_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "bop"), exist_ok=True)
        path = os.path.join(mod, "common", "bop", "ITA.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("ITA_power_balance = {\n"
                    "\tinitial_value = 0.35\n"
                    "\tleft_side = A\n"
                    "\tright_side = B\n"
                    "\tdecision_category = C\n"
                    "}\n")
        wb = WorkbenchDock(mod_path=mod)
        wb._current_type = "bop"
        wb.show()
        self.app.processEvents()
        return wb, path

    def test_file_mode_double_click_opens_bop(self):
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import Qt
        wb, path = self._make_env()
        received = []
        gallery = []
        wb.generic_file_selected.connect(
            lambda fp, eid: received.append((fp, eid)))
        wb.entity_gallery_requested.connect(
            lambda t, fp: gallery.append((t, fp)))
        it = QListWidgetItem("ITA")
        it.setData(Qt.ItemDataRole.UserRole, path)
        wb._on_file_double_clicked(it)
        self.assertEqual(len(received), 1, "应请求打开 BOP 专用编辑器")
        self.assertEqual(gallery, [], "不得只进实体画廊")

    def test_nofile_entity_double_click_opens_bop(self):
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import Qt
        wb, path = self._make_env()
        wb.set_nofile_mode(True)
        received = []
        wb.generic_file_selected.connect(
            lambda fp, eid: received.append((fp, eid)))
        it = QListWidgetItem("ITA")
        it.setData(Qt.ItemDataRole.UserRole,
                   {"file": path, "key": "ITA_power_balance"})
        wb._on_entity_double_clicked(it)
        self.assertEqual(len(received), 1, "无文件模式双击 BOP 应请求打开编辑器")

    def test_open_tree_editor_routes_bop(self):
        from unittest.mock import MagicMock, patch
        from main_window import MyWindow
        mod = _mkdtemp("dsh_boproute_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "bop"), exist_ok=True)
        path = os.path.join(mod, "common", "bop", "ITA.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("ITA_power_balance = { initial_value = 0.35 }\n")
        fake = MagicMock()
        fake.settings = {"mod_path": mod, "HOI4_path": ""}
        with patch("bop_editor_dialog.open_bop_editor") as m:
            MyWindow._open_tree_editor(fake, path)
        m.assert_called_once()


class BopEditDataTest(unittest.TestCase):
    """BOP 区间/势力数据写回。"""

    def _make(self):
        mod = _mkdtemp("dsh_bopd_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "bop")
        os.makedirs(d)
        with open(os.path.join(d, "TST.txt"), "w", encoding="utf-8") as f:
            f.write("TST_power = {\n"
                    "\tinitial_value = 0.5\n"
                    "\trange = { id = TST_range min = 0 max = 1 }\n"
                    "\tside = { id = TST_side icon = GFX_old }\n"
                    "}\n")
        return mod

    def test_set_range_and_side(self):
        from bop_loader import set_bop_range, set_bop_side_fields, _clear_cache
        _clear_cache()
        mod = self._make()
        set_bop_range(mod, "", "TST_power", "TST_range", 0.2, 0.8)
        set_bop_side_fields(mod, "", "TST_power", "TST_side", "GFX_new")
        _clear_cache()
        from bop_loader import load_bop_definitions
        bops = load_bop_definitions(mod, "")
        bop = bops["TST"]
        # 简单断言写回文本
        fp = None
        import os, glob
        files = glob.glob(os.path.join(mod, "common", "bop", "TST.txt"))
        self.assertTrue(files)
        with open(files[0], "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("min = 0.2", content)
        self.assertIn("max = 0.8", content)
        self.assertIn("icon = GFX_new", content)


class BopDecisionCrudTest(unittest.TestCase):
    """BOP 决策增删。"""

    def _make(self):
        mod = _mkdtemp("dsh_bopdec_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "decisions")
        os.makedirs(d)
        with open(os.path.join(d, "TST.txt"), "w", encoding="utf-8") as f:
            f.write("TST_CAT = {\n"
                    "\told_action = {\n"
                    "\t\tcost = 10\n"
                    "\t}\n"
                    "}\n")
        return mod

    def test_insert_delete_decision(self):
        from bop_loader import insert_bop_decision, delete_bop_decision
        mod = self._make()
        r = insert_bop_decision(
            mod, "", "TST_CAT",
            "\tnew_action = {\n\t\tcost = 20\n\t}\n", "new_action")
        self.assertTrue(r["ok"])
        fp = os.path.join(mod, "common", "decisions", "TST.txt")
        with open(fp, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("new_action", content)
        r2 = delete_bop_decision(mod, "", "TST_CAT", "new_action")
        self.assertTrue(r2["ok"])
        with open(fp, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertNotIn("new_action", content)



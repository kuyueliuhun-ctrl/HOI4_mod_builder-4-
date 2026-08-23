# -*- coding: utf-8 -*-
"""批次 6：力量平衡（BOP）编辑增强完整表单测试。

覆盖：
  - BopEditTest：区间 / 势力 / 动作 CRUD 写回 roundtrip。
  - BopDialogLightSmokeTest：亮色无深色断言、表单读写、新建决议模板插入。
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


def _write_bop_env(mod):
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
                "\tside = {\n"
                "\t\tid = ITA_mussolini_side\n"
                "\t\ticon = GFX_bop_ITA_mussolini_side\n"
                "\t\trange = {\n"
                "\t\t\tid = ITA_mussolini_low_control_range\n"
                "\t\t\tmin = 0.1\n"
                "\t\t\tmax = 0.3\n"
                "\t\t}\n"
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


class BopEditTest(unittest.TestCase):
    """数据层：区间/势力/动作 CRUD roundtrip。"""

    def _make_env(self):
        from bop_loader import _BOP_CACHE
        _BOP_CACHE.clear()
        mod = _mkdtemp("dsh_batch6_bop_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        _write_bop_env(mod)
        return mod

    def _read(self, mod, rel):
        with open(os.path.join(mod, rel), "r", encoding="utf-8-sig") as f:
            return f.read()

    def test_range_crud_roundtrip(self):
        from bop_loader import (
            delete_bop_range, insert_bop_range, load_bop_definitions,
            set_bop_range, set_bop_range_modifiers, set_bop_range_side,
        )
        mod = self._make_env()
        bop = load_bop_definitions(mod, "")["ITA"]
        # 顶层区间 min/max + modifier 写回
        set_bop_range(mod, "", "ITA_power_balance", "ITA_balance_range",
                      -0.2, 0.2)
        set_bop_range_modifiers(mod, "", "ITA_power_balance",
                                "ITA_balance_range",
                                {"stability_factor": -0.05,
                                 "war_support_factor": 0.02})
        content = self._read(mod, "common/bop/ITA.txt")
        self.assertIn("min = -0.2", content)
        self.assertIn("max = 0.2", content)
        self.assertIn("stability_factor = -0.05", content)
        # side 内嵌区间移动归属 + 新增/删除
        set_bop_range_side(mod, "", "ITA_power_balance",
                           "ITA_balance_range", "ITA_grand_council_side")
        insert_bop_range(
            mod, "", "ITA_power_balance",
            "range = { id = BRAND_NEW_RANGE min = -0.5 max = -0.2 }",
            side_id="ITA_mussolini_side")
        delete_bop_range(mod, "", "ITA_power_balance",
                         "ITA_grand_council_low_control_range")
        content = self._read(mod, "common/bop/ITA.txt")
        # 移动后应位于大议会 side 内部
        self.assertIn("id = ITA_grand_council_side", content)
        self.assertIn("id = ITA_balance_range", content)
        self.assertIn("id = BRAND_NEW_RANGE", content)
        self.assertNotIn("ITA_grand_council_low_control_range", content)
        # 重新解析确认结构
        bop = load_bop_definitions(mod, "")["ITA"]
        grand = [s for s in bop["sides"]
                 if s["id"] == "ITA_grand_council_side"][0]
        mussolini = [s for s in bop["sides"]
                     if s["id"] == "ITA_mussolini_side"][0]
        rids = {r["id"] for r in grand["ranges"]}
        self.assertIn("ITA_balance_range", rids)
        self.assertIn("BRAND_NEW_RANGE",
                      {r["id"] for r in mussolini["ranges"]})

    def test_side_fields_roundtrip(self):
        from bop_loader import load_bop_definitions, set_bop_side_fields
        mod = self._make_env()
        set_bop_side_fields(
            mod, "", "ITA_power_balance", "ITA_grand_council_side",
            icon="GFX_NEW_ICON", loc_key="ITA_LEFT_NEW_SIDE")
        content = self._read(mod, "common/bop/ITA.txt")
        self.assertIn("icon = GFX_NEW_ICON", content)
        self.assertIn("id = ITA_LEFT_NEW_SIDE", content)
        self.assertIn("left_side = ITA_LEFT_NEW_SIDE", content)
        bop = load_bop_definitions(mod, "")["ITA"]
        self.assertEqual(bop["left_side"], "ITA_LEFT_NEW_SIDE")
        side = [s for s in bop["sides"]
                if s["id"] == "ITA_LEFT_NEW_SIDE"][0]
        self.assertEqual(side["icon"], "GFX_NEW_ICON")

    def test_action_crud_and_fields_roundtrip(self):
        from bop_loader import (
            delete_bop_decision, insert_bop_decision, load_bop_actions,
            load_bop_definitions, set_bop_action_block, set_bop_action_fields,
        )
        mod = self._make_env()
        bop = load_bop_definitions(mod, "")["ITA"]
        category = bop["decision_category"]
        # 新建决议模板文本
        block_text = (
            "ITA_bop_new_action = {\n"
            "\t\tcost = 40\n"
            "\t\tcomplete_effect = {\n"
            "\t\t\tadd_power_balance_value = { id = ITA_power_balance value = 0.1 }\n"
            "\t\t}\n"
            "\t}"
        )
        insert_bop_decision(mod, "", category, block_text)
        acts = load_bop_actions(mod, "", category)
        by_key = {a["key"]: a for a in acts}
        self.assertIn("ITA_bop_new_action", by_key)
        # 写回 cost / add_power_balance_value
        set_bop_action_fields(
            mod, "", category, "ITA_bop_new_action",
            cost=75, add_power_balance_value=-0.2,
            bop_id="ITA_power_balance")
        content = self._read(mod, "common/decisions/ITA.txt")
        self.assertIn("cost = 75", content)
        self.assertIn("value = -0.2", content)
        # 结构化块写回
        set_bop_action_block(mod, "", category, "ITA_bop_new_action",
                             "visible", "visible = { has_stability = 0.5 }")
        content = self._read(mod, "common/decisions/ITA.txt")
        self.assertIn("visible = { has_stability = 0.5 }", content)
        # 删除
        delete_bop_decision(mod, "", category, "ITA_bop_new_action")
        acts = load_bop_actions(mod, "", category)
        self.assertNotIn("ITA_bop_new_action", {a["key"] for a in acts})

    def test_localisation_upsert(self):
        from bop_loader import upsert_bop_localisation
        mod = self._make_env()
        n = upsert_bop_localisation(mod, {
            "ITA_power_balance": "国家权力平衡",
            "ITA_grand_council_side": "大议会",
        })
        self.assertEqual(n, 2)
        fp = os.path.join(mod, "localisation", "simp_chinese",
                          "generic_mod_l_simp_chinese.yml")
        self.assertTrue(os.path.isfile(fp))
        with open(fp, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("大议会", content)


class BopDialogLightSmokeTest(unittest.TestCase):
    """BOP 专用编辑器亮色冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from bop_loader import _BOP_CACHE
        _BOP_CACHE.clear()
        mod = _mkdtemp("dsh_batch6_dlg_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        _write_bop_env(mod)
        return mod

    def _make_dialog(self, mod):
        from bop_loader import load_bop_definitions
        from bop_editor_dialog import BopEditorDialog
        bop = load_bop_definitions(mod, "")["ITA"]
        return BopEditorDialog(bop, mod, "")

    def test_light_theme_no_dark_qss(self):
        dlg = self._make_dialog(self._make_env())
        dlg.show()
        self.app.processEvents()
        qss = dlg.styleSheet() or ""
        self.assertNotIn("#0a0a0a", qss)
        self.assertNotIn("#141210", qss)
        self.assertEqual(dlg.tabs.count(), 2,
                         "保留旧契约的两个页签（势力与修正 / 决议（动作））")
        dlg.close()

    def test_form_read_write(self):
        from unittest.mock import patch
        from PyQt6.QtWidgets import QMessageBox
        mod = self._make_env()
        dlg = self._make_dialog(mod)
        dlg.show()
        self.app.processEvents()
        dlg.slider.setValue(50)
        self.app.processEvents()
        self.assertAlmostEqual(dlg._current_value(), 0.5)
        dlg.left_edit.setText("NEW_LEFT")
        dlg.right_edit.setText("NEW_RIGHT")
        dlg.decision_edit.setText("NEW_CAT")
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            dlg._save_changes()
        with open(os.path.join(mod, "common", "bop", "ITA.txt"),
                  "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("initial_value = 0.5000", content)
        self.assertIn("left_side = NEW_LEFT", content)
        self.assertIn("decision_category = NEW_CAT", content)
        dlg.close()

    def test_new_decision_template_insertion(self):
        from unittest.mock import patch
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        mod = self._make_env()
        dlg = self._make_dialog(mod)
        dlg.show()
        self.app.processEvents()
        before = len(dlg.actions)
        with patch.object(QInputDialog, "getItem",
                          return_value=("限时活动（内置）", True)):
            dlg._new_decision()
        self.app.processEvents()
        self.assertEqual(len(dlg.actions), before + 1,
                         "新建决议应追加到动作列表")
        new_actions = [a for a in dlg.actions if a.get("new")]
        self.assertEqual(len(new_actions), 1)
        self.assertIn("add_power_balance_value",
                      new_actions[0].get("raw", ""))
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            dlg._save_changes()
        with open(os.path.join(mod, "common", "decisions", "ITA.txt"),
                  "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn(new_actions[0]["key"], content,
                      "新决议模板应保存进决策文件")
        dlg.close()


if __name__ == "__main__":
    unittest.main()
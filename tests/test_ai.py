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


class AiLoaderTest(unittest.TestCase):
    """AI 数据层：解析 plans/strategy/templates/equipment/navy/areas/focuses/theaters。"""

    def _make_env(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_ai_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)

        def w(rel, text):
            p = os.path.join(mod, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)

        w("common/ai_strategy_plans/GER.txt",
          "GER_historical = {\n"
          "\tname = \"German historical plan\"\n"
          "\tallowed = { original_tag = GER }\n"
          "\tai_national_focuses = { A B C }\n"
          "\tweight = { factor = 1.0 }\n"
          "}\n")
        w("common/ai_strategy/GER.txt",
          "GER_unit_production = {\n"
          "\tenable = { always = yes }\n"
          "\tai_strategy = { type = role_ratio id = infantry value = 75 }\n"
          "\tai_strategy = { type = unit_ratio id = capital_ship value = 15 }\n"
          "}\n")
        w("common/ai_templates/generic.txt",
          "infantry_generic = {\n"
          "\trole = infantry\n"
          "\tblocked_for = { GER JAP }\n"
          "\tinfantry_1 = {\n"
          "\t\ttarget_template = { regiments = { infantry = 6 } }\n"
          "\t\treplace_with = infantry_2\n"
          "\t}\n"
          "}\n")
        w("common/ai_equipment/GER.txt",
          "GER_fighter = {\n"
          "\tcategory = air\n"
          "\tavailable_for = { GER }\n"
          "\tbasic_fighter = {\n"
          "\t\ttarget_variant = { type = small_plane_airframe_1 modules = { } }\n"
          "\t\tallowed_modules = { engine_1_1x }\n"
          "\t}\n"
          "}\n")
        w("common/ai_navy/goals/goals_GER.txt",
          "GER_convoy_protection = {\n"
          "\tobjective_type = convoy_protection\n"
          "\tmin_priority = 3\n"
          "\tmax_priority = 8\n"
          "}\n")
        w("common/ai_navy/fleet/fleets_GER.txt",
          "GER_home_fleet = {\n"
          "\trequired_taskforces = { GER_StrikeForce_1 = 1 }\n"
          "}\n")
        w("common/ai_navy/taskforce/taskforces_GER.txt",
          "GER_StrikeForce_1 = {\n"
          "\tmission = { naval_strike }\n"
          "\tmin_composition = { destroyer = { amount = 1 } }\n"
          "}\n")
        w("common/ai_areas/default.txt",
          "areas = {\n"
          "\teurope = { strategic_regions = { 1 2 } }\n"
          "}\n")
        w("common/ai_focuses/GER.txt",
          "ai_focus_defense_GER = {\n"
          "\tresearch = { defensive = 5.0 radar_tech = 1.0 }\n"
          "}\n")
        w("common/ai_faction_theaters/ai_faction_theaters.txt",
          "western_europe = {\n"
          "\tname = theater_western_europe\n"
          "\tregions = { 1 2 3 }\n"
          "}\n")
        return mod

    def test_parse_ai_plans(self):
        from ai_loader import parse_ai_plans
        mod = self._make_env()
        with open(os.path.join(mod, "common", "ai_strategy_plans", "GER.txt"),
                  "r", encoding="utf-8") as f:
            plans = parse_ai_plans(f.read())
        self.assertIn("GER_historical", plans)
        self.assertEqual(plans["GER_historical"]["ai_national_focuses"],
                         ["A", "B", "C"])
        self.assertIn("original_tag = GER", plans["GER_historical"]["allowed"])

    def test_parse_ai_strategies(self):
        from ai_loader import parse_ai_strategies
        mod = self._make_env()
        with open(os.path.join(mod, "common", "ai_strategy", "GER.txt"),
                  "r", encoding="utf-8") as f:
            groups = parse_ai_strategies(f.read())
        self.assertIn("GER_unit_production", groups)
        self.assertEqual(len(groups["GER_unit_production"]["strategies"]), 2)
        self.assertEqual(
            groups["GER_unit_production"]["strategies"][0]["id"], "infantry")

    def test_parse_ai_templates_and_equipment(self):
        from ai_loader import parse_ai_templates, parse_ai_equipment
        mod = self._make_env()
        with open(os.path.join(mod, "common", "ai_templates", "generic.txt"),
                  "r", encoding="utf-8") as f:
            roles = parse_ai_templates(f.read())
        self.assertIn("infantry_generic", roles)
        self.assertEqual(roles["infantry_generic"]["role"], "infantry")
        self.assertEqual(roles["infantry_generic"]["blocked_for"], ["GER", "JAP"])
        self.assertEqual(roles["infantry_generic"]["targets"][0]["id"], "infantry_1")
        with open(os.path.join(mod, "common", "ai_equipment", "GER.txt"),
                  "r", encoding="utf-8") as f:
            eqs = parse_ai_equipment(f.read())
        self.assertIn("GER_fighter", eqs)
        self.assertEqual(eqs["GER_fighter"]["category"], "air")
        self.assertEqual(eqs["GER_fighter"]["variants"][0]["id"], "basic_fighter")

    def test_parse_ai_navy(self):
        from ai_loader import (
            parse_ai_navy_goals, parse_ai_navy_fleets, parse_ai_navy_taskforces)
        mod = self._make_env()
        with open(os.path.join(mod, "common", "ai_navy", "goals", "goals_GER.txt"),
                  "r", encoding="utf-8") as f:
            goals = parse_ai_navy_goals(f.read())
        self.assertEqual(goals["GER_convoy_protection"]["objective_type"],
                         "convoy_protection")
        with open(os.path.join(mod, "common", "ai_navy", "fleet", "fleets_GER.txt"),
                  "r", encoding="utf-8") as f:
            fleets = parse_ai_navy_fleets(f.read())
        self.assertEqual(fleets["GER_home_fleet"]["required_taskforces"],
                         {"GER_StrikeForce_1": "1"})
        with open(os.path.join(mod, "common", "ai_navy", "taskforce", "taskforces_GER.txt"),
                  "r", encoding="utf-8") as f:
            tfs = parse_ai_navy_taskforces(f.read())
        self.assertEqual(tfs["GER_StrikeForce_1"]["mission"], ["naval_strike"])

    def test_parse_ai_areas_focuses_theaters(self):
        from ai_loader import (
            parse_ai_areas, parse_ai_focuses, parse_ai_faction_theaters)
        mod = self._make_env()
        with open(os.path.join(mod, "common", "ai_areas", "default.txt"),
                  "r", encoding="utf-8") as f:
            areas = parse_ai_areas(f.read())
        self.assertEqual(areas["europe"]["strategic_regions"], ["1", "2"])
        with open(os.path.join(mod, "common", "ai_focuses", "GER.txt"),
                  "r", encoding="utf-8") as f:
            focuses = parse_ai_focuses(f.read())
        self.assertEqual(focuses["ai_focus_defense_GER"]["research"]["defensive"],
                         "5.0")
        with open(os.path.join(mod, "common", "ai_faction_theaters",
                               "ai_faction_theaters.txt"),
                  "r", encoding="utf-8") as f:
            theaters = parse_ai_faction_theaters(f.read())
        self.assertEqual(theaters["western_europe"]["regions"], ["1", "2", "3"])


class AiPlanEditorTest(unittest.TestCase):
    """AI 战略计划编辑器：写回与打开。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_aiplan_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "ai_strategy_plans"), exist_ok=True)
        path = os.path.join(mod, "common", "ai_strategy_plans", "GER.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("GER_historical = {\n"
                    "\tname = \"German historical plan\"\n"
                    "\tdesc = \"desc\"\n"
                    "\tallowed = { original_tag = GER }\n"
                    "\tai_national_focuses = { A B C }\n"
                    "}\n")
        return mod, path

    def test_replace_helpers(self):
        from ai_loader import replace_ai_plan_focus_order, replace_ai_plan_field
        content = ("GER_historical = {\n"
                   "\tname = \"x\"\n"
                   "\tai_national_focuses = { A B }\n"
                   "}\n")
        out = replace_ai_plan_focus_order(content, "GER_historical", ["C", "D"])
        self.assertIn("ai_national_focuses = {\n\tC\n\tD\n}", out)
        out2 = replace_ai_plan_field(content, "GER_historical", "name", "New")
        self.assertIn('name = "New"', out2)

    def test_dialog_save_writes_order_and_fields(self):
        from unittest.mock import patch
        from ai_loader import load_ai_plans
        from ai_plan_editor_dialog import AiPlanEditorDialog
        mod, path = self._make_env()
        plans = load_ai_plans(mod, "")
        dlg = AiPlanEditorDialog(plans, mod, "")
        dlg.show()
        self.app.processEvents()
        dlg._ordered = ["D", "A"]
        dlg.name_edit.setText("New Plan")
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            dlg._save()
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('name = "New Plan"', content)
        self.assertIn("ai_national_focuses = {\n\tD\n\tA\n}", content)
        dlg.close()

    def test_structured_weight_tables_sync(self):
        from ai_loader import load_ai_plans
        from ai_plan_editor_dialog import AiPlanEditorDialog
        mod, path = self._make_env()
        plans = load_ai_plans(mod, "")
        dlg = AiPlanEditorDialog(plans, mod, "")
        dlg.show()
        self.app.processEvents()
        dlg.research_table.set_rows([("infantry_weapons", "10")])
        dlg.weight_card.table.set_rows([("base", "1")])
        dlg._sync_structured_fields()
        self.assertIn("infantry_weapons = 10",
                      dlg._advanced_blocks["research"])
        self.assertIn("base = 1", dlg._advanced_blocks["weight"])
        dlg.close()

    def test_open_tree_editor_routes_ai_plan(self):
        from unittest.mock import MagicMock, patch
        from main_window import MyWindow
        mod, path = self._make_env()
        fake = MagicMock()
        fake.settings = {"mod_path": mod, "HOI4_path": ""}
        with patch("ai_plan_editor_dialog.open_ai_plan_editor") as m:
            MyWindow._open_tree_editor(fake, path)
        m.assert_called_once()


class AiStrategyEditorTest(unittest.TestCase):
    """AI 战略倾向编辑器：表格写回。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_aistrat_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "ai_strategy"), exist_ok=True)
        path = os.path.join(mod, "common", "ai_strategy", "GER.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("GER_unit_production = {\n"
                    "\tenable = { always = yes }\n"
                    "\tai_strategy = { type = role_ratio id = infantry value = 75 }\n"
                    "\tai_strategy = { type = unit_ratio id = capital_ship value = 15 }\n"
                    "}\n")
        return mod, path

    def test_replace_helper(self):
        from ai_loader import replace_ai_strategy_entries
        content = ("GER_unit_production = {\n"
                   "\tenable = { always = yes }\n"
                   "\tai_strategy = { type = role_ratio id = infantry value = 75 }\n"
                   "}\n")
        out = replace_ai_strategy_entries(
            content, "GER_unit_production",
            [{"type": "role_ratio", "id": "armor", "value": "10"}])
        self.assertIn("id = armor", out)
        self.assertNotIn("infantry", out)

    def test_operative_fields_roundtrip(self):
        from ai_loader import parse_ai_strategies, replace_ai_strategy_entries
        content = ("OP_GROUP = {\n"
                   "\tai_strategy = { type = operative_leader id = X value = 1 }\n"
                   "}\n")
        out = replace_ai_strategy_entries(
            content, "OP_GROUP",
            [{"type": "operative_leader", "id": "X", "value": "1",
              "operation": "intel", "mission_target": "FRA",
              "num_operatives": "2", "state": "10"}])
        parsed = parse_ai_strategies(out)["OP_GROUP"]["strategies"][0]
        self.assertEqual(parsed["operation"], "intel")
        self.assertEqual(parsed["mission_target"], "FRA")
        self.assertEqual(parsed["num_operatives"], "2")
        self.assertEqual(parsed["state"], "10")

    def test_dialog_save(self):
        from unittest.mock import patch
        from ai_loader import load_ai_strategies
        from ai_strategy_editor_dialog import AiStrategyEditorDialog
        mod, path = self._make_env()
        groups = load_ai_strategies(mod, "")
        dlg = AiStrategyEditorDialog(groups, mod, "")
        dlg.show()
        self.app.processEvents()
        # 修改第一行 id
        dlg.table.item(0, 1).setText("armor")
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            dlg._save()
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("id = armor", content)
        self.assertNotIn("id = infantry", content)
        dlg.close()


class AiTemplateEditorTest(unittest.TestCase):
    """AI 师模板：转换与写回。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_aitpl_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "ai_templates"), exist_ok=True)
        path = os.path.join(mod, "common", "ai_templates", "generic.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("infantry_generic = {\n"
                    "\trole = infantry\n"
                    "\tinfantry_1 = {\n"
                    "\t\ttarget_template = { regiments = { infantry = 6 } }\n"
                    "\t\treplace_with = infantry_2\n"
                    "\t}\n"
                    "}\n")
        return mod, path

    def test_conversions(self):
        from ai_template_editor_dialog import (
            _target_template_to_division_text, _division_template_to_target_text)
        from oob_loader import DivisionTemplate
        div = _target_template_to_division_text(
            "target_template = { regiments = { infantry = 6 } }")
        self.assertIn("division_template", div)
        self.assertIn('name = "ai_target"', div)

    def test_upgrade_cycle_detect(self):
        from ai_template_editor_dialog import (
            _division_template_to_target_text, find_upgrade_cycle)
        from oob_loader import DivisionTemplate
        role = {"targets": [
            {"id": "A", "replace_with": "B"},
            {"id": "B", "replace_with": "A"},
        ]}
        self.assertEqual(find_upgrade_cycle(role, "A"), ["A", "B", "A"])
        self.assertEqual(find_upgrade_cycle(role, "A")[0], "A")
        no_cycle = {"targets": [
            {"id": "A", "replace_with": "B"},
            {"id": "B", "replace_with": ""},
        ]}
        self.assertEqual(find_upgrade_cycle(no_cycle, "A"), [])
        tpl = DivisionTemplate(name="ai_target", regiments=[("infantry", 0, 0)])
        target = _division_template_to_target_text(tpl)
        self.assertIn("target_template = {", target)
        self.assertIn("infantry", target)

    def test_replace_helper(self):
        from ai_loader import replace_ai_template_target_template
        mod, path = self._make_env()
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        out = replace_ai_template_target_template(
            content, "infantry_generic", "infantry_1",
            "target_template = { regiments = { infantry = 9 } }")
        self.assertIn("infantry = 9", out)
        self.assertNotIn("infantry = 6", out)

    def test_dialog_lists_roles_and_targets(self):
        from ai_loader import load_ai_templates
        from ai_template_editor_dialog import AiTemplateEditorDialog
        mod, path = self._make_env()
        roles = load_ai_templates(mod, "")
        dlg = AiTemplateEditorDialog(roles, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.role_list.count(), 1)
        self.assertEqual(dlg.target_list.count(), 1)
        self.assertEqual(dlg._current_target, "infantry_1")
        dlg.close()

    def test_open_tree_editor_routes_ai_template(self):
        from unittest.mock import MagicMock, patch
        from main_window import MyWindow
        mod, path = self._make_env()
        fake = MagicMock()
        fake.settings = {"mod_path": mod, "HOI4_path": ""}
        with patch("ai_template_editor_dialog.open_ai_template_editor") as m:
            MyWindow._open_tree_editor(fake, path)
        m.assert_called_once()


class AiNavyEditorTest(unittest.TestCase):
    """AI 海军编辑器：表格与保存。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_ainavy_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "ai_navy", "goals"), exist_ok=True)
        os.makedirs(os.path.join(mod, "common", "ai_navy", "fleet"), exist_ok=True)
        os.makedirs(os.path.join(mod, "common", "ai_navy", "taskforce"), exist_ok=True)
        goal = os.path.join(mod, "common", "ai_navy", "goals", "goals_GER.txt")
        with open(goal, "w", encoding="utf-8") as f:
            f.write("GER_convoy_protection = {\n"
                    "\tobjective_type = convoy_protection\n"
                    "\tmin_priority = 3\n"
                    "\tmax_priority = 8\n"
                    "}\n")
        return mod, goal

    def test_dialog_rows_and_save_goals(self):
        from unittest.mock import patch
        from ai_loader import load_ai_navy
        from ai_navy_editor_dialog import AiNavyEditorDialog
        mod, goal = self._make_env()
        navy = load_ai_navy(mod, "")
        dlg = AiNavyEditorDialog(navy, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.goals_table.rowCount(), 1)
        dlg.goals_table.item(0, 2).setText("5")
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            dlg._save_goals()
        with open(goal, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("min_priority = 5", content)
        dlg.close()

    def test_open_tree_editor_routes_ai_navy(self):
        from unittest.mock import MagicMock, patch
        from main_window import MyWindow
        mod, goal = self._make_env()
        fake = MagicMock()
        fake.settings = {"mod_path": mod, "HOI4_path": ""}
        with patch("ai_navy_editor_dialog.open_ai_navy_editor") as m:
            MyWindow._open_tree_editor(fake, goal)
        m.assert_called_once()


class AiFactionTheaterTest(unittest.TestCase):
    """AI 派系战区：地图描边数据 + 列表对话框。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_aith_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "ai_faction_theaters"), exist_ok=True)
        path = os.path.join(mod, "common", "ai_faction_theaters",
                            "ai_faction_theaters.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("western_europe = {\n"
                    "\tname = theater_western_europe\n"
                    "\tregions = { 1 2 }\n"
                    "}\n")
        return mod, path

    def test_theater_outline_pixmap(self):
        import numpy as np
        from map_loader import MapData
        md = MapData.__new__(MapData)
        md.id_map = np.array([[1, 1, 0], [1, 2, 0]], dtype=np.int32)
        pm = md.theater_outline_pixmap([1])
        self.assertFalse(pm.isNull(), "红色描边图层应生成")

    def test_dialog_lists_theaters(self):
        from ai_faction_theater_editor_dialog import AiFactionTheaterEditorDialog
        from ai_loader import load_ai_faction_theaters
        mod, path = self._make_env()
        theaters = load_ai_faction_theaters(mod, "")
        dlg = AiFactionTheaterEditorDialog(theaters, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.sidebar.list.count(), 1)
        self.assertEqual(dlg.sidebar.width(), 300)
        dlg.close()

    def test_open_tree_editor_routes_faction_theater(self):
        from unittest.mock import MagicMock, patch
        from main_window import MyWindow
        mod, path = self._make_env()
        fake = MagicMock()
        fake.settings = {"mod_path": mod, "HOI4_path": ""}
        with patch("ai_faction_theater_editor_dialog.open_ai_faction_theater_list") as m:
            MyWindow._open_tree_editor(fake, path)
        m.assert_called_once()


class AiEquipmentEditorTest(unittest.TestCase):
    """AI 装备：解析与写回。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_aieq_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "ai_equipment"), exist_ok=True)
        path = os.path.join(mod, "common", "ai_equipment", "GER.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("GER_fighter = {\n"
                    "\tcategory = air\n"
                    "\tavailable_for = { GER }\n"
                    "\tbasic_fighter = {\n"
                    "\t\ttarget_variant = { type = small_plane_airframe_1 modules = { fixed_main_weapon_slot = light_mg_2x } }\n"
                    "\t}\n"
                    "}\n")
        return mod, path

    def test_parse_and_replace_target_variant(self):
        from ai_loader import parse_ai_target_variant, replace_ai_equipment_target_variant
        parsed = parse_ai_target_variant(
            "target_variant = { type = small_plane_airframe_1 modules = { fixed_main_weapon_slot = light_mg_2x } }")
        self.assertEqual(parsed["type"], "small_plane_airframe_1")
        self.assertEqual(parsed["modules"]["fixed_main_weapon_slot"], "light_mg_2x")
        mod, path = self._make_env()
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        out = replace_ai_equipment_target_variant(
            content, "GER_fighter", "basic_fighter", "small_plane_airframe_1",
            {"fixed_main_weapon_slot": "aircraft_cannon_1_1x"})
        self.assertIn("aircraft_cannon_1_1x", out)
        self.assertNotIn("light_mg_2x", out)

    def test_dialog_lists_groups_and_variants(self):
        from ai_loader import load_ai_equipment
        from ai_equipment_editor_dialog import AiEquipmentEditorDialog
        mod, path = self._make_env()
        groups = load_ai_equipment(mod, "")
        dlg = AiEquipmentEditorDialog(groups, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.group_list.count(), 1)
        self.assertEqual(dlg.variant_list.count(), 1)
        self.assertEqual(dlg._current_variant, "basic_fighter")
        variant = dlg._find_variant("basic_fighter")
        self.assertIsNotNone(variant)
        self.assertEqual(variant["id"], "basic_fighter")
        dlg.close()

    def test_open_tree_editor_routes_ai_equipment(self):
        from unittest.mock import MagicMock, patch
        from main_window import MyWindow
        mod, path = self._make_env()
        fake = MagicMock()
        fake.settings = {"mod_path": mod, "HOI4_path": ""}
        with patch("ai_equipment_editor_dialog.open_ai_equipment_editor") as m:
            MyWindow._open_tree_editor(fake, path)
        m.assert_called_once()


class AiWorkbenchRouteTest(unittest.TestCase):
    """AI 类型：文件模式/无文件模式双击直接走 generic_file_selected。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from workbench import WorkbenchDock
        mod = _mkdtemp("dsh_aiwb_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "ai_strategy_plans"), exist_ok=True)
        path = os.path.join(mod, "common", "ai_strategy_plans", "GER.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("GER_historical = {\n"
                    "\tname = \"German historical plan\"\n"
                    "\tai_national_focuses = { A B C }\n"
                    "}\n")
        wb = WorkbenchDock(mod_path=mod)
        wb._current_type = "ai_strategy_plans"
        wb.show()
        self.app.processEvents()
        return wb, path

    def test_file_mode_double_click_ai_direct(self):
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import Qt
        wb, path = self._make_env()
        received = []
        gallery = []
        wb.generic_file_selected.connect(
            lambda fp, eid: received.append((fp, eid)))
        wb.entity_gallery_requested.connect(
            lambda t, fp: gallery.append((t, fp)))
        it = QListWidgetItem("GER.txt")
        it.setData(Qt.ItemDataRole.UserRole, path)
        wb._on_file_double_clicked(it)
        self.assertEqual(len(received), 1, "AI 文件应直接请求打开")
        self.assertEqual(gallery, [], "AI 不应进实体画廊")

    def test_nofile_entity_double_click_ai_direct(self):
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import Qt
        wb, path = self._make_env()
        wb.set_nofile_mode(True)
        received = []
        wb.generic_file_selected.connect(
            lambda fp, eid: received.append((fp, eid)))
        it = QListWidgetItem("GER_historical")
        it.setData(Qt.ItemDataRole.UserRole,
                   {"file": path, "key": "GER_historical"})
        wb._on_entity_double_clicked(it)
        self.assertEqual(len(received), 1, "无文件模式 AI 实体应直接请求打开")


if __name__ == "__main__":
    unittest.main()


class AiCrudWriteTest(unittest.TestCase):
    """AI 数据层实体级 CRUD 写回。"""

    def test_strategy_crud(self):
        from ai_loader import (
            insert_ai_strategy_group, delete_ai_strategy_group,
            rename_ai_strategy_group, duplicate_ai_strategy_group)
        content = ("A = {\n"
                   "\tai_strategy = { type = role_ratio id = infantry value = 1 }\n"
                   "}\n")
        out = insert_ai_strategy_group(
            content, "B", [{"type": "role_ratio", "id": "armor", "value": "2"}])
        self.assertIn("B = {", out)
        out = delete_ai_strategy_group(out, "A")
        self.assertNotIn("A = {", out)
        out = insert_ai_strategy_group(
            content, "B", [{"type": "role_ratio", "id": "armor", "value": "2"}])
        out = rename_ai_strategy_group(out, "B", "C")
        self.assertIn("C = {", out)
        self.assertNotIn("B = {", out)
        out = duplicate_ai_strategy_group(out, "C", "D")
        self.assertIn("D = {", out)

    def test_focus_crud(self):
        from ai_loader import (
            insert_ai_focus, delete_ai_focus, rename_ai_focus,
            duplicate_ai_focus, replace_top_block_child)
        content = "A = {\n\tresearch = { tech1 = 1.0 }\n}\n"
        out = insert_ai_focus(content, "B", {"tech2": "2.0"})
        self.assertIn("B = {", out)
        out = delete_ai_focus(out, "A")
        self.assertNotIn("A = {", out)
        out = rename_ai_focus(out, "B", "C")
        self.assertIn("C = {", out)
        out = duplicate_ai_focus(out, "C", "D")
        self.assertIn("D = {", out)
        out = replace_top_block_child(
            out, "C", "research", "research = {\n\ttech9 = 9.0\n}")
        self.assertIn("tech9 = 9.0", out)

    def test_area_crud_and_replace(self):
        from ai_loader import (
            insert_ai_area, delete_ai_area, rename_ai_area,
            duplicate_ai_area, replace_ai_area_regions, replace_ai_area_block)
        content = "areas = {\n\teurope = { strategic_regions = { 1 2 } }\n}\n"
        out = insert_ai_area(content, "asia", ["3", "4"])
        self.assertIn("asia = {", out)
        self.assertIn("3", out)
        out = replace_ai_area_regions(out, "asia", ["5"])
        self.assertIn("5", out)
        self.assertNotIn("4", out)
        out = delete_ai_area(out, "europe")
        self.assertNotIn("europe = {", out)
        out = insert_ai_area(content, "asia", ["3"])
        out = rename_ai_area(out, "asia", "africa")
        self.assertIn("africa = {", out)
        self.assertNotIn("asia = {", out)
        out = duplicate_ai_area(out, "africa", "america")
        self.assertIn("america = {", out)
        out = replace_ai_area_block(out, "africa", "africa = { strategic_regions = { 99 } }")
        self.assertIn("99", out)

    def test_template_crud_and_replace(self):
        from ai_loader import (
            insert_ai_template_role, delete_ai_template_role,
            rename_ai_template_role, duplicate_ai_template_role,
            insert_ai_template_target, delete_ai_template_target,
            rename_ai_template_target, duplicate_ai_template_target,
            replace_ai_template_target_field, replace_ai_template_target_template)
        content = ("infantry_generic = {\n"
                   "\trole = infantry\n"
                   "\tinfantry_1 = {\n"
                   "\t\ttarget_template = { regiments = { infantry = 6 } }\n"
                   "\t\treplace_with = infantry_2\n"
                   "\t}\n"
                   "}\n")
        out = insert_ai_template_role(content, "armor_generic", "armor")
        self.assertIn("armor_generic = {", out)
        out = insert_ai_template_target(out, "infantry_generic", "infantry_2")
        self.assertIn("infantry_2 = {", out)
        out = replace_ai_template_target_field(
            out, "infantry_generic", "infantry_2", "target_min_match", "0.5")
        self.assertIn("target_min_match = 0.5", out)
        out = replace_ai_template_target_template(
            out, "infantry_generic", "infantry_2",
            "target_template = { regiments = { infantry = 9 } }")
        self.assertIn("infantry = 9", out)
        out = rename_ai_template_target(
            out, "infantry_generic", "infantry_2", "infantry_3")
        self.assertIn("infantry_3 = {", out)
        out = duplicate_ai_template_target(
            out, "infantry_generic", "infantry_3", "infantry_4")
        self.assertIn("infantry_4 = {", out)
        out = delete_ai_template_target(out, "infantry_generic", "infantry_4")
        self.assertNotIn("infantry_4 = {", out)
        out = rename_ai_template_role(out, "armor_generic", "armor_gen")
        self.assertIn("armor_gen = {", out)
        out = duplicate_ai_template_role(out, "infantry_generic", "infantry_gen2")
        self.assertIn("infantry_gen2 = {", out)
        out = delete_ai_template_role(out, "armor_gen")
        self.assertNotIn("armor_gen = {", out)

    def test_equipment_crud_and_replace(self):
        from ai_loader import (
            insert_ai_equipment_group, delete_ai_equipment_group,
            rename_ai_equipment_group, duplicate_ai_equipment_group,
            insert_ai_equipment_variant, delete_ai_equipment_variant,
            rename_ai_equipment_variant, duplicate_ai_equipment_variant,
            replace_ai_equipment_variant_field,
            replace_ai_equipment_allowed_modules,
            replace_ai_equipment_target_variant)
        content = ("GER = {\n"
                   "\tcategory = air\n"
                   "\tbasic = {\n"
                   "\t\ttarget_variant = { type = small_plane_airframe_1 modules = { } }\n"
                   "\t}\n"
                   "}\n")
        out = insert_ai_equipment_group(content, "ENG", "tank")
        self.assertIn("ENG = {", out)
        out = insert_ai_equipment_variant(out, "GER", "advanced")
        self.assertIn("advanced = {", out)
        out = replace_ai_equipment_variant_field(
            out, "GER", "advanced", "history", "h1")
        self.assertIn("history = h1", out)
        out = replace_ai_equipment_allowed_modules(
            out, "GER", "advanced", ["engine_1", "weapon_1"])
        self.assertIn("engine_1", out)
        out = replace_ai_equipment_target_variant(
            out, "GER", "advanced", "small_plane_airframe_2",
            {"slot": "mod"})
        self.assertIn("small_plane_airframe_2", out)
        out = rename_ai_equipment_variant(out, "GER", "advanced", "adv2")
        self.assertIn("adv2 = {", out)
        out = duplicate_ai_equipment_variant(out, "GER", "adv2", "adv3")
        self.assertIn("adv3 = {", out)
        out = delete_ai_equipment_variant(out, "GER", "adv3")
        self.assertNotIn("adv3 = {", out)
        out = rename_ai_equipment_group(out, "ENG", "ENG2")
        self.assertIn("ENG2 = {", out)
        out = duplicate_ai_equipment_group(out, "GER", "GER2")
        self.assertIn("GER2 = {", out)
        out = delete_ai_equipment_group(out, "ENG2")
        self.assertNotIn("ENG2 = {", out)

    def test_plan_crud_and_replace(self):
        from ai_loader import (
            insert_ai_plan, delete_ai_plan, rename_ai_plan,
            duplicate_ai_plan, replace_ai_plan_focus_order,
            upsert_top_block_child)
        content = ("GER = {\n"
                   "\tname = \"X\"\n"
                   "\tai_national_focuses = { A B }\n"
                   "}\n")
        out = insert_ai_plan(content, "ENG", "East", "d")
        self.assertIn("ENG = {", out)
        out = replace_ai_plan_focus_order(out, "ENG", ["C", "D"])
        self.assertIn("ai_national_focuses = {\n\tC\n\tD\n}", out)
        out = upsert_top_block_child(out, "ENG", "weight", "weight = { factor = 1.0 }")
        self.assertIn("factor = 1.0", out)
        out = delete_ai_plan(out, "GER")
        self.assertNotIn("GER = {", out)
        out = insert_ai_plan(content, "ENG", "East")
        out = rename_ai_plan(out, "ENG", "FRA")
        self.assertIn("FRA = {", out)
        out = duplicate_ai_plan(out, "FRA", "ITA")
        self.assertIn("ITA = {", out)

    def test_navy_crud(self):
        from ai_loader import (
            insert_ai_navy_goal, delete_ai_navy_goal, rename_ai_navy_goal,
            duplicate_ai_navy_goal, insert_ai_navy_fleet,
            insert_ai_navy_taskforce, delete_ai_navy_fleet,
            rename_ai_navy_taskforce)
        content = ("GER_convoy = {\n"
                   "\tobjective_type = convoy_protection\n"
                   "\tmin_priority = 3\n"
                   "\tmax_priority = 8\n"
                   "}\n")
        out = insert_ai_navy_goal(content, "GER_patrol", "patrol", "1", "5")
        self.assertIn("GER_patrol = {", out)
        out = rename_ai_navy_goal(out, "GER_patrol", "GER_escort")
        self.assertIn("GER_escort = {", out)
        out = duplicate_ai_navy_goal(out, "GER_escort", "GER_escort2")
        self.assertIn("GER_escort2 = {", out)
        out = delete_ai_navy_goal(out, "GER_convoy")
        self.assertNotIn("GER_convoy = {", out)
        out = insert_ai_navy_fleet(out, "GER_home")
        self.assertIn("GER_home = {", out)
        out = delete_ai_navy_fleet(out, "GER_home")
        self.assertNotIn("GER_home = {", out)
        out = insert_ai_navy_taskforce(out, "GER_tf")
        self.assertIn("GER_tf = {", out)
        out = rename_ai_navy_taskforce(out, "GER_tf", "GER_tf2")
        self.assertIn("GER_tf2 = {", out)

    def test_theater_crud_and_replace(self):
        from ai_loader import (
            insert_ai_faction_theater, delete_ai_faction_theater,
            rename_ai_faction_theater, duplicate_ai_faction_theater,
            replace_top_block_field, replace_ai_region_list,
            upsert_top_block_child)
        content = ("western = {\n"
                   "\tname = \"W\"\n"
                   "\tregions = { 1 2 }\n"
                   "}\n")
        out = insert_ai_faction_theater(content, "eastern", "East", ["3"])
        self.assertIn("eastern = {", out)
        out = replace_ai_region_list(out, "eastern", "regions", ["9"])
        self.assertIn("9", out)
        self.assertNotIn("3", out)
        out = replace_top_block_field(
            out, "eastern", "can_skip_first_region", "yes")
        self.assertIn("can_skip_first_region = yes", out)
        out = upsert_top_block_child(
            out, "eastern", "cancel", "cancel = { always = yes }")
        self.assertIn("always = yes", out)
        out = delete_ai_faction_theater(out, "western")
        self.assertNotIn("western = {", out)
        out = insert_ai_faction_theater(content, "eastern", "East")
        out = rename_ai_faction_theater(out, "eastern", "southern")
        self.assertIn("southern = {", out)
        out = duplicate_ai_faction_theater(out, "southern", "northern")
        self.assertIn("northern = {", out)


class AiSimpleEditorSmokeTest(unittest.TestCase):
    """简单 AI 专用编辑器：固定侧边栏、无横向滚动、打开与保存。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_aisimple_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)

        def w(rel, text):
            p = os.path.join(mod, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)

        w("common/ai_strategy/GER.txt",
          "GER = {\n"
          "\tallowed = { always = yes }\n"
          "\tai_strategy = { type = role_ratio id = infantry value = 75 }\n"
          "}\n")
        w("common/ai_areas/default.txt",
          "areas = {\n"
          "\teurope = { strategic_regions = { 1 2 } }\n"
          "}\n")
        w("common/ai_focuses/GER.txt",
          "ai_focus_defense_GER = {\n"
          "\tresearch = { defensive = 5.0 radar = 1.0 }\n"
          "}\n")
        w("common/ai_templates/generic.txt",
          "infantry_generic = {\n"
          "\trole = infantry\n"
          "\tinfantry_1 = {\n"
          "\t\ttarget_template = { regiments = { infantry = 6 } }\n"
          "\t\treplace_with = infantry_2\n"
          "\t}\n"
          "}\n")
        w("common/ai_equipment/GER.txt",
          "GER_fighter = {\n"
          "\tcategory = air\n"
          "\tbasic_fighter = {\n"
          "\t\ttarget_variant = { type = small_plane_airframe_1 modules = { } }\n"
          "\t\tallowed_modules = { engine_1_1x }\n"
          "\t}\n"
          "}\n")
        w("common/ai_strategy_plans/GER.txt",
          "GER_historical = {\n"
          "\tname = \"German historical plan\"\n"
          "\tallowed = { original_tag = GER }\n"
          "\tai_national_focuses = { A B C }\n"
          "}\n")
        w("common/ai_navy/goals/goals_GER.txt",
          "GER_convoy = {\n"
          "\tobjective_type = convoy_protection\n"
          "\tmin_priority = 3\n"
          "\tmax_priority = 8\n"
          "}\n")
        return mod

    def test_strategy_sidebar_fixed_no_horizontal_scroll(self):
        from ai_loader import load_ai_strategies
        from ai_strategy_editor_dialog import AiStrategyEditorDialog
        mod = self._make_env()
        groups = load_ai_strategies(mod, "")
        dlg = AiStrategyEditorDialog(groups, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.sidebar.width(), 300)
        self.assertEqual(dlg.sidebar.list.horizontalScrollBar().maximum(), 0)
        dlg.close()

    def test_area_editor_opens(self):
        from ai_loader import load_ai_areas
        from ai_area_editor_dialog import AiAreaEditorDialog
        mod = self._make_env()
        areas = load_ai_areas(mod, "")
        dlg = AiAreaEditorDialog(areas, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.regions_list.count(), 2)
        self.assertEqual(dlg.sidebar.width(), 300)
        dlg.close()

    def test_focus_editor_opens(self):
        from ai_loader import load_ai_focuses
        from ai_focus_editor_dialog import AiFocusEditorDialog
        mod = self._make_env()
        focuses = load_ai_focuses(mod, "")
        dlg = AiFocusEditorDialog(focuses, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.table.data().get("defensive"), "5.0")
        self.assertEqual(dlg.sidebar.width(), 300)
        dlg.close()

    def test_template_editor_opens(self):
        from ai_loader import load_ai_templates
        from ai_template_editor_dialog import AiTemplateEditorDialog
        mod = self._make_env()
        roles = load_ai_templates(mod, "")
        dlg = AiTemplateEditorDialog(roles, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.role_list.count(), 1)
        self.assertEqual(dlg.target_list.count(), 1)
        self.assertEqual(dlg.sidebar.width(), 300)
        self.assertEqual(dlg.target_list.horizontalScrollBar().maximum(), 0)
        dlg.close()

    def test_navy_editor_opens(self):
        from ai_loader import load_ai_navy
        from ai_navy_editor_dialog import AiNavyEditorDialog
        mod = self._make_env()
        navy = load_ai_navy(mod, "")
        dlg = AiNavyEditorDialog(navy, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.goals_table.rowCount(), 1)
        self.assertEqual(dlg.goals_sidebar.width(), 300)
        self.assertEqual(dlg.goals_sidebar.list.horizontalScrollBar().maximum(), 0)
        dlg.close()

    def test_plan_editor_opens(self):
        from ai_loader import load_ai_plans
        from ai_plan_editor_dialog import AiPlanEditorDialog
        mod = self._make_env()
        plans = load_ai_plans(mod, "")
        dlg = AiPlanEditorDialog(plans, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.sidebar.list.count(), 1)
        self.assertEqual(dlg.sidebar.width(), 300)
        self.assertEqual(dlg.name_edit.text(), "German historical plan")
        dlg.close()

    def test_equipment_editor_opens(self):
        from ai_loader import load_ai_equipment
        from ai_equipment_editor_dialog import AiEquipmentEditorDialog
        mod = self._make_env()
        groups = load_ai_equipment(mod, "")
        dlg = AiEquipmentEditorDialog(groups, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.group_list.count(), 1)
        self.assertEqual(dlg.variant_list.count(), 1)
        self.assertEqual(dlg.sidebar.width(), 300)
        self.assertEqual(dlg.variant_list.horizontalScrollBar().maximum(), 0)
        dlg.close()


class AiUiCommonTest(unittest.TestCase):
    """公共 UI 组件：高级块编辑器 roundtrip 与侧边栏约束。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_script_block_editor_roundtrip(self):
        from ai_ui_common import ScriptBlockEditorDialog
        dlg = ScriptBlockEditorDialog(
            "allowed = {\n\talways = yes\n\tnorway = { tag = NOR }\n}",
            block_key="allowed")
        text = dlg.get_block_text()
        self.assertIn("always = yes", text)
        self.assertIn("norway = {", text)
        dlg.close()

    def test_entity_sidebar_no_horizontal_scroll(self):
        from ai_ui_common import EntityListSidebar
        sb = EntityListSidebar("测试")
        sb.set_entities([("a", "A" * 500)])
        sb.show()
        self.app.processEvents()
        self.assertEqual(sb.width(), 300)
        self.assertEqual(sb.list.horizontalScrollBar().maximum(), 0)
        sb.close()




class AiAttitudesEditorTest(unittest.TestCase):
    """AI 态度：loader 与编辑器冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_aiatt_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "ai_attitudes"), exist_ok=True)
        path = os.path.join(mod, "common", "ai_attitudes", "GER.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("GER = {\n"
                    "\tuse_military_force = yes\n"
                    "\tjoin_faction = no\n"
                    "}\n")
        return mod, path

    def test_parse_and_editor(self):
        from ai_loader import load_ai_attitudes
        from ai_attitudes_editor_dialog import AiAttitudesEditorDialog
        mod, path = self._make_env()
        attitudes = load_ai_attitudes(mod, "")
        self.assertIn("GER", attitudes)
        self.assertEqual(attitudes["GER"].get("use_military_force"), "yes")
        dlg = AiAttitudesEditorDialog(attitudes, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.tab.sidebar.list.count(), 1)
        dlg.close()


if __name__ == "__main__":
    unittest.main()


class AiPersonalitiesEditorTest(unittest.TestCase):
    """AI 人格：loader 与编辑器冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_parse_and_editor(self):
        from ai_loader import _AI_CACHE, load_ai_personalities
        from ai_personalities_editor_dialog import AiPersonalitiesEditorDialog
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_aipers_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "ai_personalities"), exist_ok=True)
        path = os.path.join(mod, "common", "ai_personalities", "GER.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("GER_AGGRESSIVE = {\n"
                    "\twar_support = high\n"
                    "\trisk_tolerance = 0.8\n"
                    "}\n")
        personalities = load_ai_personalities(mod, "")
        self.assertIn("GER_AGGRESSIVE", personalities)
        dlg = AiPersonalitiesEditorDialog(personalities, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.tab.sidebar.list.count(), 1)
        dlg.close()


if __name__ == "__main__":
    unittest.main()


class MioAiWeightsEditorTest(unittest.TestCase):
    """MIO AI 权重：loader 与编辑器冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_parse_and_editor(self):
        from ai_loader import _AI_CACHE, load_mio_ai_weights
        from ai_mio_weights_editor_dialog import MioAiWeightsEditorDialog
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_aimio_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "mio_ai_weights"), exist_ok=True)
        path = os.path.join(mod, "common", "mio_ai_weights", "GER.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("GER_TANK = {\n"
                    "\tcategory = tank\n"
                    "\tweight = 5\n"
                    "}\n")
        weights = load_mio_ai_weights(mod, "")
        self.assertIn("GER_TANK", weights)
        dlg = MioAiWeightsEditorDialog(weights, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.tab.sidebar.list.count(), 1)
        dlg.close()


if __name__ == "__main__":
    unittest.main()


class AiPeaceEditorTest(unittest.TestCase):
    """AI 和平策略：loader 与编辑器冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_parse_and_editor(self):
        from ai_loader import _AI_CACHE, load_ai_peace
        from ai_peace_editor_dialog import AiPeaceEditorDialog
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_aipeace_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "ai_peace"), exist_ok=True)
        path = os.path.join(mod, "common", "ai_peace", "GER.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("GER_PEACE = {\n"
                    "\tpeace_action_type = white_peace\n"
                    "\tai_desire = 0.3\n"
                    "}\n")
        peace = load_ai_peace(mod, "")
        self.assertIn("GER_PEACE", peace)
        dlg = AiPeaceEditorDialog(peace, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.tab.sidebar.list.count(), 1)
        dlg.close()


if __name__ == "__main__":
    unittest.main()

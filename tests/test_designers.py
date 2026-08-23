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


class ShipDesignLoaderTest(unittest.TestCase):
    """舰艇设计数据层：船体/模块/设计解析 + 属性汇总 + 块级写回。"""

    def _make_env(self):
        """临时 mod：ship_hull 文件 + modules 文件 + countries 文件。"""
        from ship_design import load_ship_hulls, load_ship_modules, \
            load_ship_variants
        mod = _mkdtemp("dsh_ship_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        eq_dir = os.path.join(mod, "common", "units", "equipment")
        os.makedirs(eq_dir, exist_ok=True)
        with open(os.path.join(eq_dir, "ship_hull_light.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tship_hull_light = {\n'
                    '\t\tis_archetype = yes\n'
                    '\t\tmodule_slots = {\n'
                    '\t\t\tfixed_ship_battery_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { ship_light_battery }\n'
                    '\t\t\t}\n'
                    '\t\t\tfixed_ship_engine_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { light_ship_engine }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t\tdefault_modules = {\n'
                    '\t\t\tfixed_ship_engine_slot = light_ship_engine_1\n'
                    '\t\t}\n'
                    '\t\tnaval_speed = 32\n'
                    '\t\tnaval_range = 2000\n'
                    '\t\tmax_strength = 25\n'
                    '\t\tbuild_cost_ic = 400\n'
                    '\t\tnaval_dominance_factor = 20\n'
                    '\t}\n'
                    '\tship_hull_light_1 = {\n'
                    '\t\tarchetype = ship_hull_light\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t}\n'
                    '}\n')
        mod_dir = os.path.join(eq_dir, "modules")
        os.makedirs(mod_dir, exist_ok=True)
        with open(os.path.join(mod_dir, "00_ship_modules.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tship_light_battery_1 = {\n'
                    '\t\tabbreviation = "slb"\n'
                    '\t\tcategory = ship_light_battery\n'
                    '\t\tadd_stats = { lg_attack = 1 build_cost_ic = 90 }\n'
                    '\t\tmultiply_stats = { naval_speed = -0.02 }\n'
                    '\t}\n'
                    '\tlight_ship_engine_1 = {\n'
                    '\t\tabbreviation = "le1"\n'
                    '\t\tcategory = light_ship_engine\n'
                    '\t\tadd_stats = { fuel_consumption = 7 }\n'
                    '\t}\n'
                    '}\n')
        c_dir = os.path.join(mod, "history", "countries")
        os.makedirs(c_dir, exist_ok=True)
        with open(os.path.join(c_dir, "JAP - Japan.txt"),
                  "w", encoding="utf-8") as f:
            f.write('capital = 1\n'
                    'create_equipment_variant = {\n'
                    '\tname = "Test Destroyer"\n'
                    '\ttype = ship_hull_light_1\n'
                    '\tmodules = {\n'
                    '\t\tfixed_ship_battery_slot = ship_light_battery_1\n'
                    '\t}\n'
                    '}\n'
                    'create_equipment_variant = {\n'
                    '\tname = "Test Plane"\n'
                    '\ttype = fighter_equipment_0\n'
                    '}\n')
        return mod

    def test_load_ship_hulls(self):
        """equipments 包裹 + 变体 inherit 继承 archetype。"""
        from ship_design import load_ship_hulls
        mod = self._make_env()
        hulls = load_ship_hulls(mod, "")
        arch = hulls["ship_hull_light"]
        self.assertTrue(arch["is_archetype"])
        self.assertEqual(arch["stats"]["naval_speed"], 32.0)
        self.assertEqual(arch["stats"]["build_cost_ic"], 400.0)
        self.assertEqual(sorted(arch["module_slots"]),
                         ["fixed_ship_battery_slot", "fixed_ship_engine_slot"])
        self.assertTrue(arch["module_slots"]["fixed_ship_battery_slot"]["required"])
        v = hulls["ship_hull_light_1"]
        self.assertEqual(v["archetype_key"], "ship_hull_light")
        self.assertEqual(sorted(v["module_slots"]), sorted(arch["module_slots"]),
                         "inherit 应解析为 archetype 槽位表")
        self.assertEqual(v["stats"]["naval_speed"], 32.0, "基础属性继承")
        self.assertEqual(v["default_modules"]["fixed_ship_engine_slot"],
                         "light_ship_engine_1")

    def test_load_ship_modules(self):
        """模块 add/multiply 解析。"""
        from ship_design import load_ship_modules
        mod = self._make_env()
        mods = load_ship_modules(mod, "")
        b = mods["ship_light_battery_1"]
        self.assertEqual(b["category"], "ship_light_battery")
        self.assertEqual(b["add_stats"], {"lg_attack": 1.0, "build_cost_ic": 90.0})
        self.assertEqual(b["multiply_stats"], {"naval_speed": -0.02})
        self.assertEqual(mods["light_ship_engine_1"]["add_stats"],
                         {"fuel_consumption": 7.0})

    def test_load_ship_variants(self):
        """国家文件（展开式）+ 仅收 ship_hull 类型。"""
        from ship_design import load_ship_variants
        mod = self._make_env()
        variants = load_ship_variants(mod, "")
        self.assertEqual(list(variants.keys()), ["JAP"])
        v = variants["JAP"]["Test Destroyer"]
        self.assertEqual(v["type"], "ship_hull_light_1")
        self.assertEqual(v["modules"],
                         {"fixed_ship_battery_slot": "ship_light_battery_1"})
        self.assertNotIn("Test Plane", variants["JAP"], "非舰艇设计应过滤")

    def test_ship_design_stats(self):
        """hull 基础 + add Σ + multiply 乘 + cost。"""
        from ship_design import load_ship_hulls, load_ship_modules, \
            ship_design_stats
        mod = self._make_env()
        hulls = load_ship_hulls(mod, "")
        mods = load_ship_modules(mod, "")
        variant = {"type": "ship_hull_light_1",
                   "modules": {"fixed_ship_battery_slot": "ship_light_battery_1"}}
        st = ship_design_stats(variant, hulls["ship_hull_light_1"], mods)
        self.assertEqual(st["naval_speed"], 32.0 * (1 - 0.02),
                         "multiply 应作用于基础速度")
        self.assertEqual(st["lg_attack"], 1.0)
        self.assertEqual(st["naval_range"], 2000.0)
        self.assertEqual(st["cost"], 400.0 + 90.0, "hull + 模块花费")
        self.assertEqual(st["slot_count"], 2)
        self.assertEqual(st["empty_slots"], 1, "必装槽主炮未装 → 空 1")

    def test_variant_writeback(self):
        """apply/insert/remove/rename 块级写回（modules 块）。"""
        from ship_design import apply_variant_modules, apply_variant_upgrades, \
            insert_variant, remove_variant, rename_variant
        content = ('TAG = {\n'
                   '\tcreate_equipment_variant = {\n'
                   '\t\tname = "X"\n'
                   '\t\ttype = ship_hull_light_1\n'
                   '\t\tmodules = {\n'
                   '\t\t\tfixed_ship_battery_slot = ship_light_battery_1\n'
                   '\t\t}\n'
                   '\t}\n'
                   '}\n')
        new = apply_variant_modules(
            content, "X",
            {"fixed_ship_battery_slot": "ship_light_battery_2",
             "fixed_ship_engine_slot": "light_ship_engine_1"})
        self.assertIn("ship_light_battery_2", new)
        self.assertNotIn("ship_light_battery_1", new)
        self.assertIn("fixed_ship_engine_slot = light_ship_engine_1", new)
        self.assertEqual(apply_variant_modules(content, "NoSuch", {}), None)
        # 无 modules 块的插入
        plain = ('TAG = {\n\tcreate_equipment_variant = {\n'
                 '\t\tname = "Y"\n\t\ttype = ship_hull_light_1\n\t}\n}\n')
        new = apply_variant_modules(plain, "Y",
                                    {"fixed_ship_battery_slot": "slb_1"})
        self.assertIn("modules = {", new)
        self.assertIn("slb_1", new)
        # insert
        new = insert_variant(content, "TAG", "Z", "ship_hull_light_1",
                             {"fixed_ship_battery_slot": "slb_1"})
        self.assertIn('name = "Z"', new)
        self.assertIn("slb_1", new)
        # remove
        new = remove_variant(new, "Z")
        self.assertNotIn("Z", new)
        # rename
        new = rename_variant(content, "X", "X2")
        self.assertIn('name = "X2"', new)
        self.assertNotIn('name = "X"', new)
        # upgrades 块（升级加点）单独写回
        new = apply_variant_upgrades(
            content, "X", {"ship_engine_upgrade": 2})
        self.assertIn("upgrades = {", new)
        self.assertIn("ship_engine_upgrade = 2", new)


class ShipDesignDialogSmokeTest(unittest.TestCase):
    """舰艇设计器 offscreen 冒烟：打开/槽位/数据面板/选模块/保存写回。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from ship_design import _HULLS_CACHE, _MODULES_CACHE, _VARIANTS_CACHE
        mod = _mkdtemp("dsh_shipui_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        eq_dir = os.path.join(mod, "common", "units", "equipment")
        os.makedirs(os.path.join(eq_dir, "modules"), exist_ok=True)
        with open(os.path.join(eq_dir, "ship_hull_light.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tship_hull_light = {\n'
                    '\t\tis_archetype = yes\n'
                    '\t\tmodule_slots = {\n'
                    '\t\t\tfixed_ship_battery_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { ship_light_battery }\n'
                    '\t\t\t}\n'
                    '\t\t\tfixed_ship_engine_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { light_ship_engine }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t\tnaval_speed = 32\n'
                    '\t\tbuild_cost_ic = 400\n'
                    '\t\tnaval_dominance_factor = 20\n'
                    '\t}\n'
                    '\tship_hull_light_1 = {\n'
                    '\t\tarchetype = ship_hull_light\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t}\n'
                    '}\n')
        with open(os.path.join(eq_dir, "modules", "00_ship_modules.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tship_light_battery_1 = {\n'
                    '\t\tabbreviation = "slb"\n'
                    '\t\tcategory = ship_light_battery\n'
                    '\t\tadd_stats = { lg_attack = 1 build_cost_ic = 90 }\n'
                    '\t}\n'
                    '\tlight_ship_engine_1 = {\n'
                    '\t\tabbreviation = "le1"\n'
                    '\t\tcategory = light_ship_engine\n'
                    '\t\tadd_stats = { fuel_consumption = 7 }\n'
                    '\t}\n'
                    '}\n')
        c_dir = os.path.join(mod, "history", "countries")
        os.makedirs(c_dir, exist_ok=True)
        with open(os.path.join(c_dir, "JAP - Japan.txt"),
                  "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Test Destroyer"\n'
                    '\ttype = ship_hull_light_1\n'
                    '\tmodules = {\n'
                    '\t\tfixed_ship_battery_slot = ship_light_battery_1\n'
                    '\t}\n'
                    '}\n')
        _HULLS_CACHE.clear()
        _MODULES_CACHE.clear()
        _VARIANTS_CACHE.clear()
        return mod

    def test_open_slots_and_stats(self):
        """打开对话框：下拉/槽位/数据面板。"""
        from ship_design_dialog import ShipDesignDialog
        mod = self._make_env()
        dlg = ShipDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.country_combo.count(), 1)
        self.assertEqual(dlg.design_combo.count(), 1)
        self.assertEqual(dlg.current_name, "Test Destroyer")
        self.assertEqual(len(dlg._slot_buttons), 2)
        # 主炮已装（slb），引擎空必装（🔒）
        self.assertEqual(dlg._slot_buttons["fixed_ship_battery_slot"].text(), "slb")
        self.assertEqual(dlg._stat_labels["naval_speed"].text(), "32 kn")
        self.assertEqual(dlg._stat_labels["lg_attack"].text(), "1")
        self.assertIn("490", dlg.cost_label.text(), "400+90")
        dlg.close()

    def test_pick_module_and_save(self):
        """选模块 → 保存 → 文件内容写回。"""
        from unittest.mock import patch
        from ship_design_dialog import ShipDesignDialog
        mod = self._make_env()
        dlg = ShipDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        # 引擎槽选 light_ship_engine_1（绕过模态 exec，直接走内部逻辑）
        dlg.current_variant["modules"]["fixed_ship_engine_slot"] = "light_ship_engine_1"
        dlg._rebuild_editor()
        self.app.processEvents()
        self.assertEqual(dlg._slot_buttons["fixed_ship_engine_slot"].text(), "le1")
        with patch("ship_design_dialog.QMessageBox.information"), \
                patch("ship_design_dialog.QMessageBox.critical"):
            dlg._save()
        path = os.path.join(mod, "history", "countries", "JAP - Japan.txt")
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("fixed_ship_engine_slot = light_ship_engine_1", content)
        self.assertIn("ship_light_battery_1", content)
        dlg.close()

    def test_save_rename_and_new_design(self):
        """改名保存 + 新建设计插入。"""
        from unittest.mock import patch
        from ship_design_dialog import ShipDesignDialog
        mod = self._make_env()
        dlg = ShipDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        dlg.name_edit.setText("Renamed Destroyer")
        with patch("ship_design_dialog.QMessageBox.information"), \
                patch("ship_design_dialog.QMessageBox.critical"):
            dlg._save()
        path = os.path.join(mod, "history", "countries", "JAP - Japan.txt")
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn('name = "Renamed Destroyer"', content)
        self.assertNotIn('name = "Test Destroyer"', content)
        dlg.close()

    def test_save_original_copies_to_mod(self):
        """mod 无该国家文件时：保存自动复制游戏文件到 mod，不改游戏本体。"""
        from unittest.mock import patch
        from ship_design import _HULLS_CACHE, _MODULES_CACHE, _VARIANTS_CACHE
        from ship_design_dialog import ShipDesignDialog
        # mod 空目录，game 含国家文件
        mod = _mkdtemp("dsh_shipmod_")
        game = _mkdtemp("dsh_shipgame_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "units", "equipment", "modules"),
                    exist_ok=True)
        os.makedirs(os.path.join(game, "common", "units", "equipment"),
                    exist_ok=True)
        os.makedirs(os.path.join(game, "common", "units", "equipment", "modules"),
                    exist_ok=True)
        os.makedirs(os.path.join(game, "history", "countries"), exist_ok=True)
        # 船体/模块放游戏（mod 没有也不影响加载：mod+game 合并）
        with open(os.path.join(game, "common", "units", "equipment",
                               "ship_hull_light.txt"), "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tship_hull_light = {\n'
                    '\t\tis_archetype = yes\n'
                    '\t\tmodule_slots = {\n'
                    '\t\t\tfixed_ship_battery_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { ship_light_battery }\n'
                    '\t\t\t}\n'
                    '\t\t\tfixed_ship_engine_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { light_ship_engine }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t\tnaval_speed = 32\n'
                    '\t\tbuild_cost_ic = 400\n'
                    '\t}\n'
                    '\tship_hull_light_1 = {\n'
                    '\t\tarchetype = ship_hull_light\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t}\n'
                    '}\n')
        with open(os.path.join(game, "common", "units", "equipment", "modules",
                               "00_ship_modules.txt"), "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tlight_ship_engine_1 = {\n'
                    '\t\tabbreviation = "le1"\n'
                    '\t\tcategory = light_ship_engine\n'
                    '\t\tadd_stats = { fuel_consumption = 7 }\n'
                    '\t}\n'
                    '}\n')
        game_country = os.path.join(game, "history", "countries", "JAP - Japan.txt")
        with open(game_country, "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Test Destroyer"\n'
                    '\ttype = ship_hull_light_1\n'
                    '}\n')
        game_before = open(game_country, "r", encoding="utf-8-sig").read()
        _HULLS_CACHE.clear()
        _MODULES_CACHE.clear()
        _VARIANTS_CACHE.clear()
        dlg = ShipDesignDialog(mod, game)
        dlg.show()
        self.app.processEvents()
        # 加引擎模块后保存
        dlg.current_variant["modules"]["fixed_ship_engine_slot"] = "light_ship_engine_1"
        dlg._rebuild_editor()
        self.app.processEvents()
        with patch("ship_design_dialog.QMessageBox.information"), \
                patch("ship_design_dialog.QMessageBox.critical"):
            dlg._save()
        mod_country = os.path.join(mod, "history", "countries", "JAP - Japan.txt")
        self.assertTrue(os.path.isfile(mod_country),
                        "原版国家文件应自动复制到 mod")
        with open(mod_country, "r", encoding="utf-8-sig") as f:
            mod_content = f.read()
        self.assertIn("fixed_ship_engine_slot = light_ship_engine_1", mod_content)
        with open(game_country, "r", encoding="utf-8-sig") as f:
            game_after = f.read()
        self.assertEqual(game_after, game_before, "游戏本体文件不得被修改")
        dlg.close()

    def test_save_validation_disables_until_required_filled(self):
        """必装空槽未填时保存禁用，填满后放行。"""
        from ship_design_dialog import ShipDesignDialog
        mod = self._make_env()
        dlg = ShipDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        # 引擎必装空 → 禁用
        self.assertFalse(dlg.save_btn.isEnabled())
        self.assertIn("必装槽未填", dlg.save_validation_label.text())
        # 填引擎 → 放行
        dlg.current_variant["modules"]["fixed_ship_engine_slot"] = "light_ship_engine_1"
        dlg._rebuild_editor()
        self.app.processEvents()
        self.assertTrue(dlg.save_btn.isEnabled())
        self.assertIn("已填满", dlg.save_validation_label.text())
        dlg.close()


class PlaneDesignLoaderTest(unittest.TestCase):
    """飞机设计数据层：airframe/模块/设计解析 + 属性汇总 + modules 写回。"""

    def _make_env(self):
        """临时 mod：airframe + plane modules + countries（modules 块）。"""
        mod = _mkdtemp("dsh_plane_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        eq_dir = os.path.join(mod, "common", "units", "equipment")
        os.makedirs(os.path.join(eq_dir, "modules"), exist_ok=True)
        with open(os.path.join(eq_dir, "plane_airframes.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tsmall_plane_airframe = {\n'
                    '\t\tis_archetype = yes\n'
                    '\t\tmodule_slots = {\n'
                    '\t\t\tfixed_main_weapon_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { fighter_weapon }\n'
                    '\t\t\t}\n'
                    '\t\t\tengine_type_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { engine }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t\tdefault_modules = {\n'
                    '\t\t\tengine_type_slot = engine_1_1x\n'
                    '\t\t}\n'
                    '\t\tmaximum_speed = 400\n'
                    '\t\tair_range = 400\n'
                    '\t\tbuild_cost_ic = 4\n'
                    '\t}\n'
                    '\tsmall_plane_airframe_1 = {\n'
                    '\t\tabbreviation = "spf1"\n'
                    '\t\tarchetype = small_plane_airframe\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t\tderived_variant_name = fighter_equipment_1\n'
                    '\t\tmaximum_speed = 425\n'
                    '\t}\n'
                    '}\n')
        with open(os.path.join(eq_dir, "modules", "00_plane_modules.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tengine_1_1x = {\n'
                    '\t\tabbreviation = "eng"\n'
                    '\t\tcategory = engine\n'
                    '\t\tadd_stats = { thrust = 11 build_cost_ic = 12 fuel_consumption = 0.16 }\n'
                    '\t}\n'
                    '\tfighter_weapon_1 = {\n'
                    '\t\tabbreviation = "fw1"\n'
                    '\t\tcategory = fighter_weapon\n'
                    '\t\tadd_stats = { air_attack = 2 }\n'
                    '\t}\n'
                    '}\n')
        c_dir = os.path.join(mod, "history", "countries")
        os.makedirs(c_dir, exist_ok=True)
        with open(os.path.join(c_dir, "JAP - Japan.txt"),
                  "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Test Fighter"\n'
                    '\ttype = small_plane_airframe_1\n'
                    '\tmodules = {\n'
                    '\t\tfixed_main_weapon_slot = fighter_weapon_1\n'
                    '\t\tengine_type_slot = engine_1_1x\n'
                    '\t}\n'
                    '}\n'
                    'create_equipment_variant = {\n'
                    '\tname = "Test Ship"\n'
                    '\ttype = ship_hull_light_1\n'
                    '}\n')
        return mod

    def test_load_plane_airframes(self):
        from plane_design import load_plane_airframes
        mod = self._make_env()
        afs = load_plane_airframes(mod, "")
        arch = afs["small_plane_airframe"]
        self.assertTrue(arch["is_archetype"])
        self.assertEqual(arch["stats"]["maximum_speed"], 400.0)
        self.assertEqual(sorted(arch["module_slots"]),
                         ["engine_type_slot", "fixed_main_weapon_slot"])
        v = afs["small_plane_airframe_1"]
        self.assertEqual(v["archetype_key"], "small_plane_airframe")
        self.assertEqual(sorted(v["module_slots"]),
                         sorted(arch["module_slots"]), "inherit 继承")
        self.assertEqual(v["derived_variant_name"], "fighter_equipment_1")
        self.assertEqual(v["stats"]["maximum_speed"], 425.0, "变体属性优先")

    def test_load_plane_modules(self):
        from plane_design import load_plane_modules
        mod = self._make_env()
        mods = load_plane_modules(mod, "")
        self.assertEqual(mods["engine_1_1x"]["category"], "engine")
        self.assertEqual(mods["engine_1_1x"]["add_stats"],
                         {"thrust": 11.0, "build_cost_ic": 12.0,
                          "fuel_consumption": 0.16})
        self.assertEqual(mods["fighter_weapon_1"]["add_stats"],
                         {"air_attack": 2.0})

    def test_load_plane_variants(self):
        from plane_design import load_plane_variants
        mod = self._make_env()
        variants = load_plane_variants(mod, "")
        self.assertEqual(list(variants.keys()), ["JAP"])
        v = variants["JAP"]["Test Fighter"]
        self.assertEqual(v["type"], "small_plane_airframe_1")
        self.assertEqual(v["modules"],
                         {"fixed_main_weapon_slot": "fighter_weapon_1",
                          "engine_type_slot": "engine_1_1x"})
        self.assertNotIn("Test Ship", variants["JAP"], "非飞机设计应过滤")

    def test_plane_design_stats(self):
        from plane_design import load_plane_airframes, load_plane_modules, \
            plane_design_stats
        mod = self._make_env()
        afs = load_plane_airframes(mod, "")
        mods = load_plane_modules(mod, "")
        v = {"type": "small_plane_airframe_1",
             "modules": {"fixed_main_weapon_slot": "fighter_weapon_1",
                         "engine_type_slot": "engine_1_1x"}}
        st = plane_design_stats(v, afs["small_plane_airframe_1"], mods)
        self.assertEqual(st["maximum_speed"], 425.0)
        self.assertEqual(st["air_attack"], 2.0)
        self.assertEqual(st["thrust"], 11.0)
        self.assertEqual(st["cost"], 4.0 + 12.0, "airframe+引擎花费")
        self.assertEqual(st["slot_count"], 2)
        self.assertEqual(st["empty_slots"], 0)

    def test_plane_variant_writeback(self):
        """modules 块 apply/insert/remove/rename。"""
        from plane_design import apply_variant_modules, insert_variant, \
            remove_variant, rename_variant
        content = ('TAG = {\n'
                   '\tcreate_equipment_variant = {\n'
                   '\t\tname = "P"\n'
                   '\t\ttype = small_plane_airframe_1\n'
                   '\t\tmodules = {\n'
                   '\t\t\tfixed_main_weapon_slot = fighter_weapon_1\n'
                   '\t\t}\n'
                   '\t}\n'
                   '}\n')
        new = apply_variant_modules(
            content, "P",
            {"fixed_main_weapon_slot": "fighter_weapon_2",
             "engine_type_slot": "engine_2_1x"})
        self.assertIn("fighter_weapon_2", new)
        self.assertNotIn("fighter_weapon_1", new)
        self.assertIn("engine_type_slot = engine_2_1x", new)
        # 无 modules 块
        plain = ('TAG = {\n\tcreate_equipment_variant = {\n'
                 '\t\tname = "Q"\n\t\ttype = small_plane_airframe_1\n\t}\n}\n')
        new = apply_variant_modules(plain, "Q",
                                    {"fixed_main_weapon_slot": "fw1"})
        self.assertIn("modules = {", new)
        self.assertIn("fw1", new)
        # insert / remove / rename
        new = insert_variant(content, "TAG", "R", "small_plane_airframe_1",
                             {"fixed_main_weapon_slot": "fw1"})
        self.assertIn('name = "R"', new)
        new = remove_variant(new, "R")
        self.assertNotIn("R", new)
        new = rename_variant(content, "P", "P2")
        self.assertIn('name = "P2"', new)


class PlaneDesignDialogSmokeTest(unittest.TestCase):
    """飞机设计器 offscreen 冒烟：打开/槽位/数据面板/保存写回/原版落 mod。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from plane_design import _AIRFRAMES_CACHE, _PLANE_MODULES_CACHE, \
            _PLANE_VARIANTS_CACHE
        mod = _mkdtemp("dsh_planeui_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        eq_dir = os.path.join(mod, "common", "units", "equipment")
        os.makedirs(os.path.join(eq_dir, "modules"), exist_ok=True)
        with open(os.path.join(eq_dir, "plane_airframes.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tsmall_plane_airframe = {\n'
                    '\t\tis_archetype = yes\n'
                    '\t\tmodule_slots = {\n'
                    '\t\t\tfixed_main_weapon_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { fighter_weapon }\n'
                    '\t\t\t}\n'
                    '\t\t\tengine_type_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { engine }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t\tmaximum_speed = 400\n'
                    '\t\tbuild_cost_ic = 4\n'
                    '\t}\n'
                    '\tsmall_plane_airframe_1 = {\n'
                    '\t\tarchetype = small_plane_airframe\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t\tderived_variant_name = fighter_equipment_1\n'
                    '\t\tmaximum_speed = 425\n'
                    '\t}\n'
                    '}\n')
        with open(os.path.join(eq_dir, "modules", "00_plane_modules.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tengine_1_1x = {\n'
                    '\t\tabbreviation = "eng"\n'
                    '\t\tcategory = engine\n'
                    '\t\tadd_stats = { thrust = 11 build_cost_ic = 12 }\n'
                    '\t}\n'
                    '\tfighter_weapon_1 = {\n'
                    '\t\tabbreviation = "fw1"\n'
                    '\t\tcategory = fighter_weapon\n'
                    '\t\tadd_stats = { air_attack = 2 }\n'
                    '\t}\n'
                    '}\n')
        c_dir = os.path.join(mod, "history", "countries")
        os.makedirs(c_dir, exist_ok=True)
        with open(os.path.join(c_dir, "JAP - Japan.txt"),
                  "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Test Fighter"\n'
                    '\ttype = small_plane_airframe_1\n'
                    '\tmodules = {\n'
                    '\t\tfixed_main_weapon_slot = fighter_weapon_1\n'
                    '\t\tengine_type_slot = engine_1_1x\n'
                    '\t}\n'
                    '}\n')
        _AIRFRAMES_CACHE.clear()
        _PLANE_MODULES_CACHE.clear()
        _PLANE_VARIANTS_CACHE.clear()
        return mod

    def test_open_slots_and_stats(self):
        from plane_design_dialog import PlaneDesignDialog
        mod = self._make_env()
        dlg = PlaneDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.country_combo.count(), 1)
        self.assertEqual(dlg.design_combo.count(), 1)
        self.assertEqual(dlg.current_name, "Test Fighter")
        self.assertEqual(len(dlg._slot_buttons), 2)
        self.assertEqual(dlg._slot_buttons["fixed_main_weapon_slot"].text(), "fw1")
        self.assertEqual(dlg._stat_labels["maximum_speed"].text(), "425 km/h")
        self.assertEqual(dlg._stat_labels["air_attack"].text(), "2")
        self.assertIn("16", dlg.cost_label.text(), "4+12")
        dlg.close()

    def test_pick_module_and_save(self):
        from unittest.mock import patch
        from plane_design_dialog import PlaneDesignDialog
        mod = self._make_env()
        dlg = PlaneDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        dlg.current_variant["modules"]["engine_type_slot"] = "engine_1_1x"
        dlg._rebuild_editor()
        self.app.processEvents()
        self.assertEqual(dlg._slot_buttons["engine_type_slot"].text(), "eng")
        with patch("plane_design_dialog.QMessageBox.information"), \
                patch("plane_design_dialog.QMessageBox.critical"):
            dlg._save()
        path = os.path.join(mod, "history", "countries", "JAP - Japan.txt")
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("engine_type_slot = engine_1_1x", content)
        dlg.close()

    def test_save_original_copies_to_mod(self):
        """mod 无国家文件：保存自动复制游戏文件到 mod，不改游戏本体。"""
        from unittest.mock import patch
        from plane_design import _AIRFRAMES_CACHE, _PLANE_MODULES_CACHE, \
            _PLANE_VARIANTS_CACHE
        from plane_design_dialog import PlaneDesignDialog
        mod = _mkdtemp("dsh_planemod_")
        game = _mkdtemp("dsh_planegame_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        os.makedirs(os.path.join(game, "common", "units", "equipment", "modules"),
                    exist_ok=True)
        os.makedirs(os.path.join(game, "history", "countries"), exist_ok=True)
        with open(os.path.join(game, "common", "units", "equipment",
                               "plane_airframes.txt"), "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tsmall_plane_airframe = {\n'
                    '\t\tis_archetype = yes\n'
                    '\t\tmodule_slots = {\n'
                    '\t\t\tfixed_main_weapon_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { fighter_weapon }\n'
                    '\t\t\t}\n'
                    '\t\t\tengine_type_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { engine }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t\tmaximum_speed = 400\n'
                    '\t}\n'
                    '\tsmall_plane_airframe_1 = {\n'
                    '\t\tarchetype = small_plane_airframe\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t}\n'
                    '}\n')
        with open(os.path.join(game, "common", "units", "equipment", "modules",
                               "00_plane_modules.txt"), "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tfighter_weapon_1 = {\n'
                    '\t\tabbreviation = "fw1"\n'
                    '\t\tcategory = fighter_weapon\n'
                    '\t\tadd_stats = { air_attack = 2 }\n'
                    '\t}\n'
                    '}\n')
        game_country = os.path.join(game, "history", "countries", "JAP - Japan.txt")
        with open(game_country, "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Test Fighter"\n'
                    '\ttype = small_plane_airframe_1\n'
                    '}\n')
        game_before = open(game_country, "r", encoding="utf-8-sig").read()
        _AIRFRAMES_CACHE.clear()
        _PLANE_MODULES_CACHE.clear()
        _PLANE_VARIANTS_CACHE.clear()
        dlg = PlaneDesignDialog(mod, game)
        dlg.show()
        self.app.processEvents()
        dlg.current_variant["modules"]["fixed_main_weapon_slot"] = "fighter_weapon_1"
        dlg._rebuild_editor()
        self.app.processEvents()
        with patch("plane_design_dialog.QMessageBox.information"), \
                patch("plane_design_dialog.QMessageBox.critical"):
            dlg._save()
        mod_country = os.path.join(mod, "history", "countries", "JAP - Japan.txt")
        self.assertTrue(os.path.isfile(mod_country), "原版国家文件应复制到 mod")
        with open(mod_country, "r", encoding="utf-8-sig") as f:
            mod_content = f.read()
        self.assertIn("fixed_main_weapon_slot = fighter_weapon_1", mod_content)
        with open(game_country, "r", encoding="utf-8-sig") as f:
            game_after = f.read()
        self.assertEqual(game_after, game_before, "游戏本体不得被修改")
        dlg.close()


class TankDesignLoaderTest(unittest.TestCase):
    """坦克设计数据层：chassis/模块/设计解析 + 属性汇总 + modules 写回。"""

    def _make_env(self):
        """临时 mod：chassis + tank modules + countries（modules 块）。"""
        mod = _mkdtemp("dsh_tank_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        eq_dir = os.path.join(mod, "common", "units", "equipment")
        os.makedirs(os.path.join(eq_dir, "modules"), exist_ok=True)
        with open(os.path.join(eq_dir, "tank_chassis.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tlight_tank_chassis = {\n'
                    '\t\tis_archetype = yes\n'
                    '\t\tmodule_slots = {\n'
                    '\t\t\tmain_armament_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { tank_small_main_armament }\n'
                    '\t\t\t}\n'
                    '\t\t\tturret_type_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { tank_light_turret_type }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t\tmaximum_speed = 5\n'
                    '\t\tbuild_cost_ic = 2\n'
                    '\t}\n'
                    '\tlight_tank_chassis_1 = {\n'
                    '\t\tabbreviation = "lt1"\n'
                    '\t\tarchetype = light_tank_chassis\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t\tderived_variant_name = light_tank_equipment_1\n'
                    '\t\tmaximum_speed = 6\n'
                    '\t\tarmor_value = 15\n'
                    '\t}\n'
                    '}\n')
        with open(os.path.join(eq_dir, "modules", "00_tank_modules.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\ttank_small_cannon = {\n'
                    '\t\tabbreviation = "tsc"\n'
                    '\t\tcategory = tank_small_main_armament\n'
                    '\t\tadd_stats = { soft_attack = 8 hard_attack = 4 ap_attack = 20 }\n'
                    '\t}\n'
                    '\ttank_light_turret = {\n'
                    '\t\tabbreviation = "tlt"\n'
                    '\t\tcategory = tank_light_turret_type\n'
                    '\t\tadd_stats = { build_cost_ic = 3 }\n'
                    '\t}\n'
                    '}\n')
        c_dir = os.path.join(mod, "history", "countries")
        os.makedirs(c_dir, exist_ok=True)
        with open(os.path.join(c_dir, "JAP - Japan.txt"),
                  "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Test Tank"\n'
                    '\ttype = light_tank_chassis_1\n'
                    '\tmodules = {\n'
                    '\t\tmain_armament_slot = tank_small_cannon\n'
                    '\t\tturret_type_slot = tank_light_turret\n'
                    '\t}\n'
                    '}\n'
                    'create_equipment_variant = {\n'
                    '\tname = "Test Plane"\n'
                    '\ttype = small_plane_airframe_1\n'
                    '}\n')
        return mod

    def test_load_tank_chassis(self):
        from tank_design import load_tank_chassis
        mod = self._make_env()
        chassis = load_tank_chassis(mod, "")
        arch = chassis["light_tank_chassis"]
        self.assertTrue(arch["is_archetype"])
        self.assertEqual(arch["stats"]["maximum_speed"], 5.0)
        self.assertEqual(sorted(arch["module_slots"]),
                         ["main_armament_slot", "turret_type_slot"])
        v = chassis["light_tank_chassis_1"]
        self.assertEqual(v["archetype_key"], "light_tank_chassis")
        self.assertEqual(sorted(v["module_slots"]),
                         sorted(arch["module_slots"]), "inherit 继承")
        self.assertEqual(v["derived_variant_name"], "light_tank_equipment_1")
        self.assertEqual(v["stats"]["maximum_speed"], 6.0)
        self.assertEqual(v["stats"]["armor_value"], 15.0)

    def test_load_tank_modules(self):
        from tank_design import load_tank_modules
        mod = self._make_env()
        mods = load_tank_modules(mod, "")
        self.assertEqual(mods["tank_small_cannon"]["category"],
                         "tank_small_main_armament")
        self.assertEqual(mods["tank_small_cannon"]["add_stats"],
                         {"soft_attack": 8.0, "hard_attack": 4.0,
                          "ap_attack": 20.0})
        self.assertEqual(mods["tank_light_turret"]["add_stats"],
                         {"build_cost_ic": 3.0})

    def test_load_tank_variants(self):
        from tank_design import load_tank_variants
        mod = self._make_env()
        variants = load_tank_variants(mod, "")
        self.assertEqual(list(variants.keys()), ["JAP"])
        v = variants["JAP"]["Test Tank"]
        self.assertEqual(v["type"], "light_tank_chassis_1")
        self.assertEqual(v["modules"],
                         {"main_armament_slot": "tank_small_cannon",
                          "turret_type_slot": "tank_light_turret"})
        self.assertNotIn("Test Plane", variants["JAP"], "非坦克设计应过滤")

    def test_tank_design_stats(self):
        from tank_design import load_tank_chassis, load_tank_modules, \
            tank_design_stats
        mod = self._make_env()
        chassis = load_tank_chassis(mod, "")
        mods = load_tank_modules(mod, "")
        v = {"type": "light_tank_chassis_1",
             "modules": {"main_armament_slot": "tank_small_cannon",
                         "turret_type_slot": "tank_light_turret"}}
        st = tank_design_stats(v, chassis["light_tank_chassis_1"], mods)
        self.assertEqual(st["maximum_speed"], 6.0)
        self.assertEqual(st["soft_attack"], 8.0)
        self.assertEqual(st["hard_attack"], 4.0)
        self.assertEqual(st["ap_attack"], 20.0)
        self.assertEqual(st["armor_value"], 15.0)
        self.assertEqual(st["cost"], 2.0 + 3.0, "chassis+炮塔花费")
        self.assertEqual(st["slot_count"], 2)
        self.assertEqual(st["empty_slots"], 0)

    def test_tank_variant_writeback(self):
        """坦克复用 plane 的 modules 写回函数。"""
        from plane_design import apply_variant_modules, insert_variant, \
            remove_variant, rename_variant
        content = ('TAG = {\n'
                   '\tcreate_equipment_variant = {\n'
                   '\t\tname = "T"\n'
                   '\t\ttype = light_tank_chassis_1\n'
                   '\t\tmodules = {\n'
                   '\t\t\tmain_armament_slot = tank_small_cannon\n'
                   '\t\t}\n'
                   '\t}\n'
                   '}\n')
        new = apply_variant_modules(
            content, "T",
            {"main_armament_slot": "tank_small_cannon_2",
             "turret_type_slot": "tank_light_turret"})
        self.assertIn("tank_small_cannon_2", new)
        self.assertNotIn("tank_small_cannon\n", new)
        self.assertIn("turret_type_slot = tank_light_turret", new)
        new = insert_variant(content, "TAG", "U", "light_tank_chassis_1",
                             {"main_armament_slot": "tsc"})
        self.assertIn('name = "U"', new)
        new = remove_variant(new, "U")
        self.assertNotIn("U", new)
        new = rename_variant(content, "T", "T2")
        self.assertIn('name = "T2"', new)


class TankDesignDialogSmokeTest(unittest.TestCase):
    """坦克设计器 offscreen 冒烟：打开/槽位/数据面板/保存写回/原版落 mod。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from tank_design import _TANKS_CACHE, _TANK_MODULES_CACHE, \
            _TANK_VARIANTS_CACHE
        mod = _mkdtemp("dsh_tankui_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        eq_dir = os.path.join(mod, "common", "units", "equipment")
        os.makedirs(os.path.join(eq_dir, "modules"), exist_ok=True)
        with open(os.path.join(eq_dir, "tank_chassis.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tlight_tank_chassis = {\n'
                    '\t\tis_archetype = yes\n'
                    '\t\tmodule_slots = {\n'
                    '\t\t\tmain_armament_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { tank_small_main_armament }\n'
                    '\t\t\t}\n'
                    '\t\t\tturret_type_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { tank_light_turret_type }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t\tmaximum_speed = 5\n'
                    '\t\tbuild_cost_ic = 2\n'
                    '\t}\n'
                    '\tlight_tank_chassis_1 = {\n'
                    '\t\tarchetype = light_tank_chassis\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t\tmaximum_speed = 6\n'
                    '\t}\n'
                    '}\n')
        with open(os.path.join(eq_dir, "modules", "00_tank_modules.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\ttank_small_cannon = {\n'
                    '\t\tabbreviation = "tsc"\n'
                    '\t\tcategory = tank_small_main_armament\n'
                    '\t\tadd_stats = { soft_attack = 8 }\n'
                    '\t}\n'
                    '\ttank_light_turret = {\n'
                    '\t\tabbreviation = "tlt"\n'
                    '\t\tcategory = tank_light_turret_type\n'
                    '\t\tadd_stats = { build_cost_ic = 3 }\n'
                    '\t}\n'
                    '}\n')
        c_dir = os.path.join(mod, "history", "countries")
        os.makedirs(c_dir, exist_ok=True)
        with open(os.path.join(c_dir, "JAP - Japan.txt"),
                  "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Test Tank"\n'
                    '\ttype = light_tank_chassis_1\n'
                    '\tmodules = {\n'
                    '\t\tmain_armament_slot = tank_small_cannon\n'
                    '\t\tturret_type_slot = tank_light_turret\n'
                    '\t}\n'
                    '}\n')
        _TANKS_CACHE.clear()
        _TANK_MODULES_CACHE.clear()
        _TANK_VARIANTS_CACHE.clear()
        return mod

    def test_open_slots_and_stats(self):
        from tank_design_dialog import TankDesignDialog
        mod = self._make_env()
        dlg = TankDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.country_combo.count(), 1)
        self.assertEqual(dlg.design_combo.count(), 1)
        self.assertEqual(dlg.current_name, "Test Tank")
        self.assertEqual(len(dlg._slot_buttons), 2)
        self.assertEqual(dlg._slot_buttons["main_armament_slot"].text(), "tsc")
        self.assertEqual(dlg._stat_labels["maximum_speed"].text(), "6 km/h")
        self.assertEqual(dlg._stat_labels["soft_attack"].text(), "8")
        self.assertIn("5", dlg.cost_label.text(), "2+3")
        dlg.close()

    def test_pick_module_and_save(self):
        from unittest.mock import patch
        from tank_design_dialog import TankDesignDialog
        mod = self._make_env()
        dlg = TankDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        # 换主炮
        dlg.current_variant["modules"]["main_armament_slot"] = "tank_small_cannon"
        dlg._rebuild_editor()
        self.app.processEvents()
        with patch("tank_design_dialog.QMessageBox.information"), \
                patch("tank_design_dialog.QMessageBox.critical"):
            dlg._save()
        path = os.path.join(mod, "history", "countries", "JAP - Japan.txt")
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("main_armament_slot = tank_small_cannon", content)
        dlg.close()

    def test_save_original_copies_to_mod(self):
        """mod 无国家文件：保存自动复制游戏文件到 mod，不改游戏本体。"""
        from unittest.mock import patch
        from tank_design import _TANKS_CACHE, _TANK_MODULES_CACHE, \
            _TANK_VARIANTS_CACHE
        from tank_design_dialog import TankDesignDialog
        mod = _mkdtemp("dsh_tankmod_")
        game = _mkdtemp("dsh_tankgame_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        os.makedirs(os.path.join(game, "common", "units", "equipment", "modules"),
                    exist_ok=True)
        os.makedirs(os.path.join(game, "history", "countries"), exist_ok=True)
        with open(os.path.join(game, "common", "units", "equipment",
                               "tank_chassis.txt"), "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tlight_tank_chassis = {\n'
                    '\t\tis_archetype = yes\n'
                    '\t\tmodule_slots = {\n'
                    '\t\t\tmain_armament_slot = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { tank_small_main_armament }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t\tmaximum_speed = 5\n'
                    '\t}\n'
                    '\tlight_tank_chassis_1 = {\n'
                    '\t\tarchetype = light_tank_chassis\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t}\n'
                    '}\n')
        with open(os.path.join(game, "common", "units", "equipment", "modules",
                               "00_tank_modules.txt"), "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\ttank_small_cannon = {\n'
                    '\t\tabbreviation = "tsc"\n'
                    '\t\tcategory = tank_small_main_armament\n'
                    '\t\tadd_stats = { soft_attack = 8 }\n'
                    '\t}\n'
                    '}\n')
        game_country = os.path.join(game, "history", "countries", "JAP - Japan.txt")
        with open(game_country, "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Test Tank"\n'
                    '\ttype = light_tank_chassis_1\n'
                    '}\n')
        game_before = open(game_country, "r", encoding="utf-8-sig").read()
        _TANKS_CACHE.clear()
        _TANK_MODULES_CACHE.clear()
        _TANK_VARIANTS_CACHE.clear()
        dlg = TankDesignDialog(mod, game)
        dlg.show()
        self.app.processEvents()
        dlg.current_variant["modules"]["main_armament_slot"] = "tank_small_cannon"
        dlg._rebuild_editor()
        self.app.processEvents()
        with patch("tank_design_dialog.QMessageBox.information"), \
                patch("tank_design_dialog.QMessageBox.critical"):
            dlg._save()
        mod_country = os.path.join(mod, "history", "countries", "JAP - Japan.txt")
        self.assertTrue(os.path.isfile(mod_country), "原版国家文件应复制到 mod")
        with open(mod_country, "r", encoding="utf-8-sig") as f:
            mod_content = f.read()
        self.assertIn("main_armament_slot = tank_small_cannon", mod_content)
        with open(game_country, "r", encoding="utf-8-sig") as f:
            game_after = f.read()
        self.assertEqual(game_after, game_before, "游戏本体不得被修改")
        dlg.close()


class DesignerSlotsTest(unittest.TestCase):
    """三设计器共享槽位/升级数据层。"""

    def _nodes(self, text):
        from tree_node import parse_pdx_text_to_nodes
        return parse_pdx_text_to_nodes(text)

    def test_parse_module_slots_alias_and_required(self):
        from designer_slots import parse_module_slots
        nodes = self._nodes(
            "module_slots = {\n"
            "\tmain_slot = { required = yes allowed_module_categories = { a b } }\n"
            "\tsecond_slot = main_slot\n"
            "}\n")
        slots = parse_module_slots(nodes[0])
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0]["slot"], "main_slot")
        self.assertTrue(slots[0]["required"])
        self.assertEqual(slots[0]["allowed"], ["a", "b"])
        self.assertIsNone(slots[0]["alias"])
        self.assertEqual(slots[1]["slot"], "second_slot")
        self.assertEqual(slots[1]["alias"], "main_slot")

    def test_resolve_slots_copies_alias_definition(self):
        from designer_slots import resolve_slots
        slots = [
            {"slot": "main", "required": True, "allowed": ["x"], "alias": None},
            {"slot": "alias1", "required": False, "allowed": [], "alias": "main"},
        ]
        result = resolve_slots(slots)
        self.assertTrue(result[1]["required"])
        self.assertEqual(result[1]["allowed"], ["x"])
        self.assertTrue(result[1]["is_alias"])

    def test_parse_module_count_limits(self):
        from designer_slots import parse_module_count_limits
        nodes = self._nodes(
            "mod = {\n"
            "\tmodule_count_limit = { category = ship_radar count < 2 }\n"
            "\tmodule_count_limit = { category = ship_sonar count < 1 }\n"
            "}\n")
        limits = parse_module_count_limits(nodes[0])
        self.assertEqual(limits, [
            {"category": "ship_radar", "count": 2},
            {"category": "ship_sonar", "count": 1},
        ])

    def test_parse_default_modules_and_upgrades_decl(self):
        from designer_slots import parse_default_modules, parse_upgrades_decl
        nodes = self._nodes(
            "mod = {\n"
            "\tupgrades = { ship_torpedo_upgrade ship_engine_upgrade }\n"
            "\tdefault_modules = { fixed_ship_engine_slot = light_ship_engine_1 }\n"
            "}\n")
        node = nodes[0]
        self.assertEqual(parse_upgrades_decl(node),
                         ["ship_torpedo_upgrade", "ship_engine_upgrade"])
        self.assertEqual(parse_default_modules(node),
                         {"fixed_ship_engine_slot": "light_ship_engine_1"})

    def test_load_upgrade_definitions(self):
        from designer_slots import load_upgrade_definitions
        import tempfile
        tmp = _mkdtemp("upgrades_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        d = os.path.join(tmp, "common", "units", "equipment", "upgrades")
        os.makedirs(d)
        with open(os.path.join(d, "land_upgrades.txt"), "w", encoding="utf-8") as f:
            f.write("tank_nsb_engine_upgrade = {\n"
                    "\tabbreviation = eng\n"
                    "\tmax_level = 20\n"
                    "\tlevel_requirements = { 5 = { has_tech = engine_tech_1 } }\n"
                    "}\n")
        upgrades = load_upgrade_definitions("", tmp)
        self.assertIn("tank_nsb_engine_upgrade", upgrades)
        info = upgrades["tank_nsb_engine_upgrade"]
        self.assertEqual(info["abbreviation"], "eng")
        self.assertEqual(info["max_level"], 20)
        self.assertIn(5, info["level_requirements"])


class VariantTypeConflictTest(unittest.TestCase):
    """同名舰/机/坦变体写回时按 type 定位，避免互相写错。"""

    def test_ship_apply_upgrades_with_type_key(self):
        from ship_design import apply_variant_upgrades
        content = """create_equipment_variant = {
\tname = "SameName"
\ttype = ship_hull_light_1
\tupgrades = { fixed_ship_engine_slot = light_ship_engine_1 }
}
create_equipment_variant = {
\tname = "SameName"
\ttype = small_plane_airframe_1
\tmodules = { engine_type_slot = engine_1 }
}
"""
        new = apply_variant_upgrades(
            content, "SameName", {"fixed_ship_engine_slot": "light_ship_engine_3"},
            type_key="ship_hull_light_1")
        self.assertIsNotNone(new)
        # 第一块被改，第二块 modules 不变
        self.assertIn("light_ship_engine_3", new)
        self.assertIn("engine_type_slot = engine_1", new)
        # 用错误 type 找不到对应块
        none = apply_variant_upgrades(
            content, "SameName", {"x": "y"}, type_key="tank_chassis_1")
        self.assertIsNone(none)


class DerivedNameFallbackTest(unittest.TestCase):
    """派生装备名反查表（供 UI 把 variant.type 映射回机体/底盘）。"""

    def test_plane_derived_map(self):
        from plane_design import plane_derived_map
        airframes = {
            "small_plane_airframe_0": {"derived_variant_name": "fighter_equipment_0"},
            "small_plane_airframe_1": {"derived_variant_name": "fighter_equipment_1"},
        }
        m = plane_derived_map(airframes)
        self.assertEqual(m["fighter_equipment_0"], "small_plane_airframe_0")
        self.assertEqual(m["fighter_equipment_1"], "small_plane_airframe_1")

    def test_tank_derived_map(self):
        from tank_design import tank_derived_map
        chassis = {
            "light_tank_chassis_0": {"derived_variant_name": "light_tank_equipment_0"},
        }
        m = tank_derived_map(chassis)
        self.assertEqual(m["light_tank_equipment_0"], "light_tank_chassis_0")



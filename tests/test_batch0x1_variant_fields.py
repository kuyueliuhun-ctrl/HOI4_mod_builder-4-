"""§0.x-1：三设计器变体高级字段卡——数据层 roundtrip 测试。

覆盖 design_team / parent_version / obsolete / icon 四个高级字段：
从变体块解析 → 修改值 → 块级写回 → 重新解析后字段保留，且
modules/upgrades 等既有字段不变。
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
SRC = os.path.join(PROJECT_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


class VariantAdvancedFieldsTest(unittest.TestCase):
    """舰/机/坦设计器变体高级字段解析与写回 roundtrip。"""

    def _assert_roundtrip(self, module, content, name, expected_modules,
                          expected_upgrades, new_advanced):
        parsed = module.parse_equipment_variants(content, None, "modules")
        v = parsed[name]
        self.assertEqual(v["modules"], expected_modules)
        self.assertEqual(v["upgrades"], expected_upgrades)
        self.assertEqual(v["design_team"], "mio:OLD_TEAM")
        self.assertEqual(v["parent_version"], 2)
        self.assertTrue(v["obsolete"])
        self.assertEqual(v["icon"], "GFX_OLD_ICON")

        edited = dict(v)
        edited.update(new_advanced)
        new_content = module.apply_variant_advanced(
            content, name, edited, v["type"])
        self.assertIsNotNone(new_content)
        self.assertIn("design_team = " + new_advanced["design_team"],
                      new_content)
        self.assertIn("parent_version = " + str(new_advanced["parent_version"]),
                      new_content)
        self.assertIn("icon = \"" + new_advanced["icon"] + "\"",
                      new_content)
        if new_advanced["obsolete"]:
            self.assertIn("obsolete = yes", new_content)
        else:
            self.assertNotIn("obsolete", new_content)

        v2 = module.parse_equipment_variants(
            new_content, None, "modules")[name]
        self.assertEqual(v2["design_team"], new_advanced["design_team"])
        self.assertEqual(v2["parent_version"],
                         new_advanced["parent_version"])
        self.assertEqual(v2["obsolete"], new_advanced["obsolete"])
        self.assertEqual(v2["icon"], new_advanced["icon"])
        # 既有字段不受影响
        self.assertEqual(v2["modules"], expected_modules)
        self.assertEqual(v2["upgrades"], expected_upgrades)

    def test_ship_advanced_roundtrip(self):
        import ship_design
        content = (
            'JAP = {\n'
            '\tcreate_equipment_variant = {\n'
            '\t\tname = "Yamato"\n'
            '\t\ttype = ship_hull_heavy_1\n'
            '\t\tdesign_team = mio:OLD_TEAM\n'
            '\t\tparent_version = 2\n'
            '\t\tmodules = {\n'
            '\t\t\tfixed_ship_battery_slot = heavy_battery_1\n'
            '\t\t}\n'
            '\t\tupgrades = {\n'
            '\t\t\tship_engine_upgrade = 2\n'
            '\t\t}\n'
            '\t\tobsolete = yes\n'
            '\t\ticon = "GFX_OLD_ICON"\n'
            '\t}\n'
            '}\n')
        self._assert_roundtrip(
            ship_design, content, "Yamato",
            {"fixed_ship_battery_slot": "heavy_battery_1"},
            {"ship_engine_upgrade": "2"},
            {"design_team": "mio:JAP_NEW_TEAM",
             "parent_version": 3,
             "obsolete": False,
             "icon": "GFX_New_Icon"})

    def test_plane_advanced_roundtrip(self):
        import plane_design
        content = (
            'GER = {\n'
            '\tcreate_equipment_variant = {\n'
            '\t\tname = "Fw 190"\n'
            '\t\ttype = small_plane_airframe_1\n'
            '\t\tdesign_team = mio:OLD_TEAM\n'
            '\t\tparent_version = 2\n'
            '\t\tmodules = {\n'
            '\t\t\tfixed_main_weapon_slot = fighter_weapon_1\n'
            '\t\t\tengine_type_slot = engine_1_1x\n'
            '\t\t}\n'
            '\t\tupgrades = {\n'
            '\t\t\tplane_engine_upgrade = 1\n'
            '\t\t}\n'
            '\t\tobsolete = yes\n'
            '\t\ticon = "GFX_OLD_ICON"\n'
            '\t}\n'
            '}\n')
        self._assert_roundtrip(
            plane_design, content, "Fw 190",
            {"fixed_main_weapon_slot": "fighter_weapon_1",
             "engine_type_slot": "engine_1_1x"},
            {"plane_engine_upgrade": "1"},
            {"design_team": "mio:GER_NEW_TEAM",
             "parent_version": 7,
             "obsolete": True,
             "icon": "GFX_New_Plane"})

    def test_tank_advanced_roundtrip(self):
        import tank_design
        content = (
            'JAP = {\n'
            '\tcreate_equipment_variant = {\n'
            '\t\tname = "Type 92 Tankette"\n'
            '\t\ttype = light_tank_chassis_0\n'
            '\t\tdesign_team = mio:OLD_TEAM\n'
            '\t\tparent_version = 2\n'
            '\t\tmodules = {\n'
            '\t\t\tmain_armament_slot = tank_heavy_machine_gun\n'
            '\t\t\tturret_type_slot = tank_light_one_man_tank_turret\n'
            '\t\t}\n'
            '\t\tupgrades = {\n'
            '\t\t\ttank_nsb_engine_upgrade = 0\n'
            '\t\t}\n'
            '\t\tobsolete = yes\n'
            '\t\ticon = "GFX_OLD_ICON"\n'
            '\t}\n'
            '}\n')
        self._assert_roundtrip(
            tank_design, content, "Type 92 Tankette",
            {"main_armament_slot": "tank_heavy_machine_gun",
             "turret_type_slot": "tank_light_one_man_tank_turret"},
            {"tank_nsb_engine_upgrade": "0"},
            {"design_team": "mio:JAP_NEW_TEAM",
             "parent_version": 4,
             "obsolete": False,
             "icon": "GFX_New_Tank"})

    def test_missing_advanced_fields_defaults(self):
        """缺失高级字段时解析返回默认值；写回非默认值后不破坏其他字段。"""
        from ship_design import parse_equipment_variants, \
            apply_variant_advanced
        content = (
            'JAP = {\n'
            '\tcreate_equipment_variant = {\n'
            '\t\tname = "Minimal"\n'
            '\t\ttype = ship_hull_light_1\n'
            '\t\tmodules = { fixed_ship_battery_slot = slb_1 }\n'
            '\t}\n'
            '}\n')
        parsed = parse_equipment_variants(content, None, "modules")
        v = parsed["Minimal"]
        self.assertEqual(v["design_team"], "")
        self.assertEqual(v["parent_version"], 0)
        self.assertIs(v["obsolete"], False)
        self.assertEqual(v["icon"], "")
        new = apply_variant_advanced(
            content, "Minimal",
            {"design_team": "mio:JAP_NEW_TEAM",
             "parent_version": 5,
             "obsolete": True,
             "icon": "GFX_Minimal"},
            v["type"])
        v2 = parse_equipment_variants(new, None, "modules")["Minimal"]
        self.assertEqual(v2["design_team"], "mio:JAP_NEW_TEAM")
        self.assertEqual(v2["parent_version"], 5)
        self.assertTrue(v2["obsolete"])
        self.assertEqual(v2["icon"], "GFX_Minimal")
        self.assertEqual(v2["modules"], {"fixed_ship_battery_slot": "slb_1"})


if __name__ == "__main__":
    unittest.main()

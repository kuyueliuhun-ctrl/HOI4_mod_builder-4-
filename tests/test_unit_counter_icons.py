"""兵牌图标接标牌库测试（P2：解析器 + Qt 图标冒烟）。"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


class CounterResolverTest(unittest.TestCase):
    def _entry(self, unit_type):
        from unit_counter_library import _get_library, find_counter_entry
        return find_counter_entry(unit_type, lib=_get_library())

    def test_common_land_types(self):
        cases = {
            "infantry": "unit_infantry_icon",
            "motorized": "unit_motorized_icon",
            "mechanized": "unit_mechanized_icon",
            "cavalry": "unit_cavalry_icon",
            "marine": "unit_marine_icon",
            "mountaineers": "unit_mountain_icon",
            "paratrooper": "unit_paratroop_icon",
            "medium_armor": "unit_medium_tank_icon",
            "heavy_armor": "unit_heavy_armor_icon",
            "modern_armor": "unit_modern_armor_icon",
            "artillery": "unit_art_icon",
            "anti_tank": "unit_at_icon",
            "anti_air": "unit_anti_air_icon",
            "rocket_artillery": "unit_rocket_art_icon",
            "engineer": "unit_engineer_icon",
            "recon": "unit_recon_icon",
            "signal_company": "support_unit_signal_company_icon",
            "maintenance_company": "support_unit_maintenance_company_icon",
            "logistics_company": "support_unit_logistics_company_icon",
            "field_hospital": "support_unit_field_hospital_icon",
            "military_police": "support_unit_military_police_icon",
        }
        for typ, expected in cases.items():
            entry = self._entry(typ)
            self.assertIsNotNone(entry, "未解析兵种: %s" % typ)
            self.assertEqual(entry["name"], expected, "兵种 %s" % typ)

    def test_air_navy_and_hq(self):
        cases = {
            "fighter": "onmap_fighter",
            "cas": "onmap_cas",
            "battleship": "onmap_battleship",
            "destroyer": "onmap_destroyer",
            "submarine": "onmap_submarine",
            "hq_infantry": "support_unit_hq_icon",
        }
        for typ, expected in cases.items():
            entry = self._entry(typ)
            self.assertIsNotNone(entry, "未解析兵种: %s" % typ)
            self.assertEqual(entry["name"], expected, "兵种 %s" % typ)

    def test_unknown_type_returns_none(self):
        self.assertIsNone(self._entry("bus"))
        self.assertIsNone(self._entry("explosive_ammo"))
        self.assertIsNone(self._entry("totally_unknown_unit"))


class CounterIconSmokeTest(unittest.TestCase):
    def test_pixmap_and_icon(self):
        try:
            from PyQt6.QtWidgets import QApplication
            from unit_counter_icons import counter_pixmap, counter_qicon
        except Exception as e:  # noqa: BLE001
            self.skipTest("PyQt6 不可用: %s" % e)
        app = QApplication.instance() or QApplication([])
        pm = counter_pixmap("infantry", 32, 32)
        self.assertIsNotNone(pm)
        self.assertFalse(pm.isNull())
        icon = counter_qicon("infantry")
        self.assertIsNotNone(icon)
        self.assertFalse(icon.isNull())
        self.assertIsNone(counter_pixmap("totally_unknown_unit"))


if __name__ == "__main__":
    unittest.main()
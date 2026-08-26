"""OOB version_name 引用解析与设计联动检查测试。

纯函数测试 + 真实数据冒烟（guarded）。
"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

REAL_MOD = "/mnt/e/mods/3350890356"
REAL_GAME = "/mnt/e/SteamLibrary/steamapps/common/Hearts of Iron IV"


class OobVersionRefsTest(unittest.TestCase):
    def _sample(self):
        return (
            "units = {\n"
            "\tdivision = {\n"
            "\t\tforce_equipment_variants = {\n"
            "\t\t\tlight_tank_chassis_0 = { owner = AFG creator = FRA "
            "version_name = \"FT mod. 31\" }\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
            "air_wings = {\n"
            "\t267 = {\n"
            "\t\tsmall_plane_cas_airframe_0 = { owner = \"AFG\" amount = 28 "
            "creator = \"ENG\" version_name = \"Fairey Gordon\" }\n"
            "\t}\n"
            "}\n"
            "fleet = {\n"
            "\ttask_force = {\n"
            "\t\tship = { name = \"M111\" definition = destroyer equipment = {\n"
            "\t\t\tship_hull_light_1 = { amount = 1 owner = ALB "
            "version_name = \"Damen Stan 4207\" }\n"
            "\t\t} }\n"
            "\t}\n"
            "}\n"
        )

    def test_extract_all_kinds(self):
        from oob_version_refs import extract_version_refs
        refs = extract_version_refs(self._sample())
        self.assertEqual(len(refs), 3)
        by_equip = {r["equipment"]: r for r in refs}
        tank = by_equip["light_tank_chassis_0"]
        self.assertEqual(tank["kind"], "tank")
        self.assertEqual(tank["version_name"], "FT mod. 31")
        self.assertEqual(tank["owner"], "AFG")
        plane = by_equip["small_plane_cas_airframe_0"]
        self.assertEqual(plane["kind"], "plane")
        self.assertEqual(plane["version_name"], "Fairey Gordon")
        self.assertEqual(plane["amount"], "28")
        ship = by_equip["ship_hull_light_1"]
        self.assertEqual(ship["kind"], "ship")
        self.assertEqual(ship["ship_name"], "M111")
        self.assertEqual(ship["owner"], "ALB")

    def test_infer_kind(self):
        from oob_version_refs import _infer_kind
        self.assertEqual(_infer_kind("small_plane_airframe_0"), "plane")
        self.assertEqual(_infer_kind("ship_hull_light_1"), "ship")
        self.assertEqual(_infer_kind("medium_tank_chassis_0"), "tank")
        self.assertEqual(_infer_kind("infantry_equipment_1"), "tank")
        self.assertEqual(_infer_kind("motorized_equipment"), "tank")
        self.assertEqual(_infer_kind("something_else"), "unknown")

    def test_check_links(self):
        from oob_version_refs import check_version_name_links
        content = self._sample()
        plane = {"AFG": {"Fairey Gordon": {"type": "small_plane_cas_airframe_0"}}}
        tank = {"AFG": {"FT mod. 31": {"type": "light_tank_chassis_0"}}}
        ship = {"ALB": {"Damen Stan 4207": {"type": "ship_hull_light_1"}}}
        r = check_version_name_links(content, plane, tank, ship)
        self.assertEqual(r["count"], 3)
        self.assertEqual(len(r["resolved"]), 3)
        self.assertEqual(r["unresolved"], [])
        # 悬空：设计库缺该名
        r2 = check_version_name_links(content, {"AFG": {}}, {}, {})
        self.assertEqual(len(r2["unresolved"]), 3)

    def test_oversize_skipped(self):
        from oob_version_refs import MAX_PARSE_CHARS, extract_version_refs
        big = "a" * (MAX_PARSE_CHARS + 10)
        self.assertEqual(extract_version_refs(big), [])


class OobRefLinkageTest(unittest.TestCase):
    def _make_mod(self):
        import tempfile
        mod = tempfile.mkdtemp(prefix="oob_link_")
        d = os.path.join(mod, "history", "units")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "AFG_xxx.txt")
        content = (
            'air_wings = {\n'
            '\t267 = { small_plane_cas_airframe_0 = { owner = "AFG" '
            'amount = 28 creator = "ENG" version_name = "Old Name" } }\n'
            '}\n'
        )
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return mod, p

    def test_rename_oob_version_refs(self):
        from oob_version_refs import rename_oob_version_refs
        mod, p = self._make_mod()
        r = rename_oob_version_refs(mod, "plane", "AFG",
                                    "Old Name", "New Name", dry_run=True)
        self.assertEqual(r["count"], 1)
        self.assertEqual(r["files"], ["AFG_xxx.txt"])
        # 未 dry_run 真正落盘
        r2 = rename_oob_version_refs(mod, "plane", "AFG",
                                     "Old Name", "New Name", dry_run=False)
        self.assertEqual(r2["count"], 1)
        with open(p, encoding="utf-8") as f:
            out = f.read()
        self.assertIn('version_name = "New Name"', out)
        self.assertNotIn("Old Name", out)

    def test_oob_refs_for_design(self):
        from oob_version_refs import oob_refs_for_design
        mod, _p = self._make_mod()
        hits = oob_refs_for_design(mod, "", "plane", "AFG", "Old Name")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["file"], "AFG_xxx.txt")
        self.assertEqual(hits[0]["amount"], "28")
        # 无关 owner/name 不命中
        self.assertEqual(oob_refs_for_design(mod, "", "plane", "GER",
                                             "Old Name"), [])
        self.assertEqual(oob_refs_for_design(mod, "", "ship", "AFG",
                                             "Old Name"), [])


@unittest.skipUnless(os.path.isdir(REAL_MOD) or os.path.isdir(REAL_GAME),
                     "需要真实 mod/game 目录才运行")
class OobVersionRefsRealTest(unittest.TestCase):
    def test_real_oob_extract_and_link(self):
        """真实 OOB 文件提取 + 与设计库比对（不断言 0 悬空，仅验证链路可跑）。"""
        from oob_version_refs import check_version_name_links
        from plane_design import load_plane_variants
        from ship_design import load_ship_variants
        from tank_design import load_tank_variants
        found = False
        for base in (REAL_MOD, REAL_GAME):
            d = os.path.join(base, "history", "units")
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if not fn.lower().endswith(".txt"):
                    continue
                fp = os.path.join(d, fn)
                try:
                    with open(fp, "r", encoding="utf-8-sig",
                              errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue
                r = check_version_name_links(
                    content, load_plane_variants(base, ""),
                    load_tank_variants(base, ""), load_ship_variants(base, ""))
                if r["count"] > 0:
                    found = True
                    self.assertGreaterEqual(r["count"], 1)
                    self.assertEqual(len(r["resolved"]) + len(r["unresolved"]),
                                     r["count"])
                    break
            if found:
                break
        self.assertTrue(found, "真实 OOB 中未找到 version_name 引用")


if __name__ == "__main__":
    unittest.main()

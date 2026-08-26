# -*- coding: utf-8 -*-
"""P0 修复回归测试：覆盖顺序 / PDX 解析 / 接口路径安全 / 撤销 / OOB 保存。

不依赖 PyQt6，可在 WSL/CI 直接运行：
    python -m unittest tests.test_p0_fixes -v
"""

from __future__ import annotations

import os
import re
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


class ModVanillaOverrideOrderTest(unittest.TestCase):
    """mod 最后写入，覆盖游戏。"""

    def _write(self, base, rel, text):
        d = os.path.join(base, *rel.split("/"))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        with open(d, "w", encoding="utf-8") as f:
            f.write(text)

    def test_load_sub_units_mod_wins(self):
        from oob_loader import load_sub_units
        mod = _mkdtemp("p0_units_mod_")
        game = _mkdtemp("p0_units_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        self._write(mod, "common/units/00_units.txt",
                    'sub_units = {\n\tinfantry = {\n\t\tabbreviation = "MOD"\n\t}\n}\n')
        self._write(game, "common/units/00_units.txt",
                    'sub_units = {\n\tinfantry = {\n\t\tabbreviation = "GAME"\n\t}\n}\n')
        result = load_sub_units(mod, game)
        self.assertEqual(result["infantry"]["abbreviation"], "MOD")

    def test_load_ship_hulls_mod_wins(self):
        from ship_design import load_ship_hulls
        mod = _mkdtemp("p0_ship_mod_")
        game = _mkdtemp("p0_ship_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        self._write(mod, "common/units/equipment/ship_hull.txt",
                    'ship_hull_light = {\n\tabbreviation = "MOD"\n\tis_archetype = yes\n}\n')
        self._write(game, "common/units/equipment/ship_hull.txt",
                    'ship_hull_light = {\n\tabbreviation = "GAME"\n\tis_archetype = yes\n}\n')
        hulls = load_ship_hulls(mod, game)
        self.assertEqual(hulls["ship_hull_light"]["abbreviation"], "MOD")

    def test_load_tank_chassis_mod_wins(self):
        from tank_design import load_tank_chassis
        mod = _mkdtemp("p0_tank_mod_")
        game = _mkdtemp("p0_tank_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        self._write(mod, "common/units/equipment/tank_chassis.txt",
                    'light_tank_chassis = {\n\tabbreviation = "MOD"\n\tis_archetype = yes\n}\n')
        self._write(game, "common/units/equipment/tank_chassis.txt",
                    'light_tank_chassis = {\n\tabbreviation = "GAME"\n\tis_archetype = yes\n}\n')
        chassis = load_tank_chassis(mod, game)
        self.assertEqual(chassis["light_tank_chassis"]["abbreviation"], "MOD")

    def test_load_plane_airframes_mod_wins(self):
        from plane_design import load_plane_airframes
        mod = _mkdtemp("p0_plane_mod_")
        game = _mkdtemp("p0_plane_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        self._write(mod, "common/units/equipment/plane_airframe.txt",
                    'small_plane_airframe = {\n\tabbreviation = "MOD"\n\tis_archetype = yes\n}\n')
        self._write(game, "common/units/equipment/plane_airframe.txt",
                    'small_plane_airframe = {\n\tabbreviation = "GAME"\n\tis_archetype = yes\n}\n')
        airframes = load_plane_airframes(mod, game)
        self.assertEqual(airframes["small_plane_airframe"]["abbreviation"], "MOD")

    def test_load_upgrades_mod_wins(self):
        # load_upgrade_definitions(hoi4_path, mod_path) 参数顺序相反
        from designer_slots import load_upgrade_definitions
        mod = _mkdtemp("p0_upg_mod_")
        game = _mkdtemp("p0_upg_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        text = ('upgrades = {\n\tweapon1 = {\n\t\tabbreviation = "X"\n'
                '\t\tmax_level = 5\n\t}\n}\n')
        self._write(mod, "common/units/equipment/upgrades/land_upgrades.txt", text)
        self._write(game, "common/units/equipment/upgrades/land_upgrades.txt", text)
        # mod 版本改 max_level 后应覆盖游戏
        mod_text = text.replace('max_level = 5', 'max_level = 9')
        self._write(mod, "common/units/equipment/upgrades/land_upgrades.txt", mod_text)
        upg = load_upgrade_definitions(game, mod)
        self.assertEqual(upg["weapon1"]["max_level"], 9)


class PdxParserCorruptionTest(unittest.TestCase):
    """PDX 解析器不再静默损坏数据。"""

    def test_hash_inside_string_kept(self):
        from pdx_parser import parse_pdx_script
        d = parse_pdx_script('key = { color = "color #FFFFFF" }')
        self.assertEqual(d["key"]["color"], "color #FFFFFF")

    def test_unquoted_special_chars_kept(self):
        from pdx_parser import parse_pdx_script
        d = parse_pdx_script("key = { a = foo@bar:baz/x(y,z) }")
        self.assertEqual(d["key"]["a"], "foo@bar:baz/x(y,z)")

    def test_unterminated_quote_raises(self):
        from pdx_parser import parse_pdx_script
        with self.assertRaises(ValueError):
            parse_pdx_script('key = { name = "unterminated }')

    def test_extra_brace_raises(self):
        from pdx_parser import parse_pdx_script
        with self.assertRaises(ValueError):
            parse_pdx_script("key = { a = 1 } }")

    def test_missing_brace_raises(self):
        from pdx_parser import parse_pdx_script
        with self.assertRaises(ValueError):
            parse_pdx_script("key = { a = 1")

    def test_existing_operator_behavior_kept(self):
        from pdx_parser import parse_pdx_script
        d = parse_pdx_script("a = { x == 3 }")
        self.assertIn("x == 3", d["a"]["list"])


class PathSafetyTest(unittest.TestCase):
    """接口层路径/名字安全校验。"""

    def setUp(self):
        self.mod = _mkdtemp("p0_path_mod_")
        self.outside = _mkdtemp("p0_path_out_")
        self.addCleanup(shutil.rmtree, self.mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.outside, ignore_errors=True)

    def test_safe_join_rejects_escape(self):
        import path_safety
        for bad in ("../x", "a/../../x", "/etc/passwd", "C:/x"):
            with self.assertRaises(ValueError):
                path_safety.safe_join(self.mod, bad)

    def test_safe_join_accepts_mod_relative(self):
        import path_safety
        fp = path_safety.safe_join(self.mod, "common/ideas/a.txt")
        self.assertTrue(fp.startswith(os.path.realpath(self.mod) + os.sep))

    def test_validate_component_rejects_separators(self):
        import path_safety
        for bad in ("../x", "a/b", "a\\b", "C:x", "1abc"):
            with self.assertRaises(ValueError):
                path_safety.validate_component(bad, "name")

    def test_generators_filename_rejects_traversal(self):
        from api_core_ext.generators import GeneratorsMixin

        class G(GeneratorsMixin):
            def __init__(self, mod_path):
                self.mod_path = mod_path

            def _notify_change(self, path):
                pass

        g = G(self.mod)
        with self.assertRaises(ValueError):
            g._gen_files("ideas", {"filename": "../../pwn"}, {"text": "x"})

    def test_write_loc_entries_tag_rejects_traversal(self):
        from project_wizard import _write_loc_entries
        with self.assertRaises(ValueError):
            _write_loc_entries(self.mod, "../../pwn", {"KEY": "v"})

    def test_oob_path_rejects_traversal(self):
        from api_core_ext.designers import DesignersMixin
        import path_safety

        class D(DesignersMixin):
            def __init__(self, mod_path, game_path):
                self.mod_path = mod_path
                self.game_path = game_path

            def _safe_join(self, rel):
                try:
                    return path_safety.safe_join(self.mod_path, rel)
                except ValueError:
                    return None

        d = D(self.mod, self.outside)
        with self.assertRaises(ValueError):
            d._oob_read_path("../" + os.path.basename(self.outside) + "/x")
        with self.assertRaises(ValueError):
            d._oob_write_path("../" + os.path.basename(self.outside) + "/x")


class UndoManagerLosslessTest(unittest.TestCase):
    """撤销无损恢复 BOM/CRLF，失败不丢条目。"""

    def setUp(self):
        self.tmp = _mkdtemp("p0_undo_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_undo_restores_bom_and_crlf(self):
        from undo_mgr import FileUndoManager
        from write_utils import atomic_write_text
        p = os.path.join(self.tmp, "test.txt")
        original = b"\xef\xbb\xbfline1\r\nline2\r\n"
        with open(p, "wb") as f:
            f.write(original)
        m = FileUndoManager()
        m.before_write(p)
        atomic_write_text(p, "new\n", undo=False)
        path, ok = m.undo()
        self.assertTrue(ok)
        self.assertEqual(path, p)
        with open(p, "rb") as f:
            self.assertEqual(f.read(), original)

    def test_undo_failure_keeps_stack_entry(self):
        from undo_mgr import FileUndoManager
        p = os.path.join(self.tmp, "x.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("old")
        m = FileUndoManager()
        m.before_write(p)
        os.remove(p)
        os.makedirs(p)  # 让原子替换失败
        path, ok = m.undo()
        self.assertFalse(ok)
        self.assertEqual(path, p)
        self.assertTrue(m.can_undo(), "失败后应保留撤销条目")


class OobSaveCorruptionTest(unittest.TestCase):
    """OOB 保存不再丢外层 } / 不误删无 name 模板。"""

    def test_save_names_group_keeps_outer_brace(self):
        from oob_loader import save_names_group
        content = (
            "division_names_group = {\n"
            "\tTEST = {\n"
            "\t\tname = \"Test\"\n"
            "\t}\n"
            "}\n"
        )
        new = save_names_group(content, "TEST", {"name": "Test2", "icon": "GFX_foo"})
        self.assertEqual(new.count("{"), new.count("}"))
        self.assertTrue(new.rstrip().endswith("}"))

    def test_save_without_name_preserves_template(self):
        from oob_loader import OobFile
        tmp = _mkdtemp("p0_oob_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        p = os.path.join(tmp, "oob.txt")
        content = (
            "division_template = {\n"
            "\tregiments = {\n"
            "\t\tinfantry = {\n"
            "\t\t\tx = 0\n"
            "\t\t\ty = 0\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        ob = OobFile(p)
        ob.save()
        with open(p, encoding="utf-8") as f:
            out = f.read()
        self.assertNotIn('name = ""', out)
        self.assertEqual(out.count("division_template = {"), 1)


class P0FollowupSecurityTest(unittest.TestCase):
    """P0-3 收口项：analyze_error_log / import_unit_counters / create_mod。"""

    def _core(self, mod):
        from api_server import ApiCore
        return ApiCore(mod_path=mod, game_path="")

    def test_analyze_error_log_rejects_arbitrary_absolute(self):
        mod = _mkdtemp("p0_follow_")
        core = self._core(mod)
        with self.assertRaises(ValueError):
            core.analyze_error_log({"absolute_path": "/etc/passwd"})
        with self.assertRaises(ValueError):
            core.analyze_error_log({})

    def test_analyze_error_log_accepts_mod_relative(self):
        mod = _mkdtemp("p0_follow_")
        rel = "logs/error.log"
        p = os.path.join(mod, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write("ERROR: test\n")
        core = self._core(mod)
        r = core.analyze_error_log({"path": rel})
        self.assertTrue(r["ok"])

    def test_analyze_error_log_accepts_game_absolute(self):
        game = "/mnt/e/SteamLibrary/steamapps/common/Hearts of Iron IV"
        if not os.path.isdir(game):
            self.skipTest("无真实游戏目录")
        sample = os.path.join(game, "common/defines/00_defines.lua")
        if not os.path.isfile(sample):
            sample = os.path.join(game, "common/defines/00_defines.txt")
        if not os.path.isfile(sample):
            self.skipTest("无 game 样例文件")
        mod = _mkdtemp("p0_follow_")
        from api_server import ApiCore
        core = ApiCore(mod_path=mod, game_path=game)
        r = core.analyze_error_log({"absolute_path": sample})
        self.assertTrue(r["ok"])

    def test_import_unit_counters_output_dir_restricted(self):
        mod = _mkdtemp("p0_follow_")
        core = self._core(mod)
        with self.assertRaises(ValueError):
            core.import_unit_counters(
                {"output_dir": "/tmp/evil", "dry_run": True})
        with self.assertRaises(ValueError):
            core.import_unit_counters(
                {"output_dir": "../evil", "dry_run": True})
        r = core.import_unit_counters(
            {"output_dir": "unit_counter_library", "dry_run": True})
        self.assertTrue(r["ok"])
        self.assertTrue(r["dry_run"])

    def test_create_mod_gate_and_path_whitelist(self):
        mods_root = _mkdtemp("p0_mods_")
        current = os.path.join(mods_root, "current_mod")
        os.makedirs(current, exist_ok=True)
        core = self._core(current)
        base = {"name": "Test Mod", "folder_name": "test_mod",
                "version": "1.14.*",
                "mod_folder_path": os.path.join(mods_root, "new_mod"),
                "mod_file_path": os.path.join(mods_root, "new_mod"),
                "dry_run": True}
        r = core.create_mod(base)
        self.assertTrue(r["ok"])
        # 越界路径拒绝
        bad = dict(base)
        bad["mod_folder_path"] = "/tmp/evil"
        with self.assertRaises(ValueError):
            core.create_mod(bad)
        # 非 dry_run 必须 approved
        need_approve = dict(base)
        need_approve["dry_run"] = False
        with self.assertRaises(ValueError):
            core.create_mod(need_approve)
        # approved + 合法路径 → 真写，且写路径限在允许根内
        ok_write = dict(need_approve)
        ok_write["approved"] = True
        r = core.create_mod(ok_write)
        self.assertTrue(r["ok"])
        self.assertFalse(r["dry_run"])
        self.assertGreater(r["count"], 0)
        for f in r["files"]:
            self.assertTrue(f.startswith(mods_root), f)


if __name__ == "__main__":
    unittest.main()
